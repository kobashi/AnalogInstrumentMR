"""Constant-density atlas UV pass for the Opus 5 brush-up candidates.

The production path (`export_v6_replacement_candidates.atlas_remap_and_collapse`)
unwraps every object with ``scale_to_bounds=True`` and then stretches the result
across the whole role quadrant. A 4.7 mm index mark and a 340 mm console
therefore both cover the full quadrant, so the tiling detail baked into that
quadrant appears at physical sizes that differ by up to 59x inside one model.

This pass keeps the atlas exactly as it is - same 1024 px sheet, same four role
quadrants, same palette, same role boundaries, same two runtime materials - and
only changes where each part lands inside its quadrant:

* every part is scaled to one shared texels-per-metre target, so the shared
  material has the same grain everywhere;
* each part occupies a sub-rectangle of its quadrant instead of the whole
  quadrant, positioned by a deterministic hash of its name so parts of the same
  role do not all sample the identical patch;
* a part too large to reach the target at quadrant scale is clamped and
  reported, rather than silently stretched.

Nothing here writes to production. Candidates land next to the R2 blends.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_uv_atlas_pass.py -- \
      --project-root "$PWD" --revision R2
"""

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import export_v6_replacement_candidates as export
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import v6_theme_materials


ATLAS_PIXELS = 1024

# Texels per metre, per model scale class.
#
# The ceiling is set by the largest single island that still has to fit inside
# one 0.46 quadrant of a 1024 px sheet. Measured over all 39 models
# (`opus5_uv_atlas_audit_all.py`): Standard reaches 700 and Medium 520 with
# nothing clamped, but the 1.2-1.6 m Window fixtures cannot exceed ~160 tx/m on
# their console bodies, so a Large target of 360 clamped 13 parts and left a
# 2.3x spread inside single models. 150 is what the class can actually hold
# uniformly.
#
# That arithmetic suggested the Large class had outgrown a shared 1K sheet, and
# a 2K candidate at 300 tx/m was built and tested. On Quest at 2 m neither the
# extra resolution nor a three times finer grain was distinguishable from this
# 1K control, so 150 on a 1K sheet is the adopted value, not a stopgap
# (docs/OPUS5_CODEX_ALIGNMENT.md 33.3). Revisit only with a native 2K+ source.
TARGET_TEXELS_PER_METRE = {
    "Standard": 700.0,
    "Medium": 520.0,
    "Large": 150.0,
}

ISLAND_MARGIN = 0.02


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--revision", default="R2")
    parser.add_argument(
        "--object", dest="object_key", choices=tuple(pilot.PILOT), action="append"
    )
    parser.add_argument("--scale-class", default="Standard")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--compare-atlas", nargs="+", default=None)
    return parser.parse_args(args)


def unwrap(obj):
    """Project without stretching to bounds, so island scale stays comparable."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(66.0),
        island_margin=ISLAND_MARGIN,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=False,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def polygon_uv_area(polygon, uv_layer):
    points = [uv_layer.data[index].uv for index in polygon.loop_indices]
    total = 0.0
    for index in range(1, len(points) - 1):
        first = points[index] - points[0]
        second = points[index + 1] - points[0]
        total += abs(first.x * second.y - first.y * second.x) * 0.5
    return total


def polygon_roles(obj):
    """Role per polygon *index*.

    Indices rather than polygon references: `smart_project` toggles edit mode,
    which invalidates any Python references held across the call.
    """
    materials = list(obj.data.materials)
    gasket = any(token in obj.name.lower() for token in pilot.GASKET_TOKENS)
    roles = []
    for polygon in obj.data.polygons:
        material = (
            materials[polygon.material_index]
            if polygon.material_index < len(materials)
            else None
        )
        roles.append("gasket" if gasket else export.material_role(material))
    return roles


def role_groups(obj):
    groups = {}
    for index, role in enumerate(polygon_roles(obj)):
        groups.setdefault(role, []).append(obj.data.polygons[index])
    return groups


def deterministic_offset(name, role, extent_u, extent_v):
    """A stable position for this part's sub-rectangle inside its quadrant."""
    digest = hashlib.sha256(f"{name}/{role}".encode("utf-8")).digest()
    free_u = max(0.0, 1.0 - extent_u)
    free_v = max(0.0, 1.0 - extent_v)
    return (
        free_u * (digest[0] / 255.0),
        free_v * (digest[1] / 255.0),
    )


def remap_object(obj, target_texels, atlas_pixels=ATLAS_PIXELS):
    uv_layer = obj.data.uv_layers.active
    if uv_layer is None:
        raise RuntimeError(f"{obj.name}: unwrap produced no UV layer")
    target_uv_per_metre = target_texels / (export.QUADRANT_SCALE * atlas_pixels)

    entries = []
    for role, polygons in role_groups(obj).items():
        area_3d = sum(polygon.area for polygon in polygons)
        area_uv = sum(polygon_uv_area(polygon, uv_layer) for polygon in polygons)
        if area_3d <= 1e-12 or area_uv <= 1e-12:
            continue
        current = math.sqrt(area_uv / area_3d)
        scale = target_uv_per_metre / current

        coordinates = [
            uv_layer.data[index].uv
            for polygon in polygons
            for index in polygon.loop_indices
        ]
        min_u = min(uv.x for uv in coordinates)
        min_v = min(uv.y for uv in coordinates)
        extent_u = (max(uv.x for uv in coordinates) - min_u) * scale
        extent_v = (max(uv.y for uv in coordinates) - min_v) * scale

        clamped = False
        largest = max(extent_u, extent_v)
        if largest > 1.0:
            # Too big to reach the target inside one quadrant: fit instead of
            # stretching, and say so in the report.
            scale /= largest
            extent_u /= largest
            extent_v /= largest
            clamped = True

        offset_u, offset_v = deterministic_offset(obj.name, role, extent_u, extent_v)
        quadrant_u, quadrant_v = export.QUADRANTS[role]
        for uv in coordinates:
            uv.x = quadrant_u + (
                offset_u + (uv.x - min_u) * scale
            ) * export.QUADRANT_SCALE
            uv.y = quadrant_v + (
                offset_v + (uv.y - min_v) * scale
            ) * export.QUADRANT_SCALE

        achieved = target_texels / max(largest, 1.0)
        entries.append(
            {
                "object": obj.name,
                "role": role,
                "faces": len(polygons),
                "texels_per_metre": round(achieved, 1),
                "clamped": clamped,
            }
        )
    return entries


def measure_density(obj, atlas_pixels=ATLAS_PIXELS):
    uv_layer = obj.data.uv_layers.active
    densities = []
    for polygon in obj.data.polygons:
        area = polygon.area
        if area <= 1e-12:
            continue
        uv_area = polygon_uv_area(polygon, uv_layer)
        if uv_area <= 1e-12:
            continue
        texel_area = uv_area * atlas_pixels**2
        densities.append(math.sqrt(texel_area / area))
    return densities


def apply(root, scale_class="Standard", target=None, atlas_pixels=ATLAS_PIXELS):
    """Unwrap and remap every mesh under ``root``. Returns per-part entries.

    ``target`` and ``atlas_pixels`` only ever appear as the ratio
    ``target / atlas_pixels``: UVs are normalised, so a 2K sheet at twice the
    texel target produces exactly the same UV layout as a 1K sheet at the base
    target. That is what makes a resolution-only comparison possible without
    re-unwrapping.
    """
    if target is None:
        target = TARGET_TEXELS_PER_METRE[scale_class]
    entries = []
    for obj in list(root.children_recursive):
        if obj.type != "MESH":
            continue
        unwrap(obj)
        entries.extend(remap_object(obj, target, atlas_pixels))
    return entries


def summarise(root, atlas_pixels=ATLAS_PIXELS):
    per_object = {}
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        densities = measure_density(obj, atlas_pixels)
        if densities:
            per_object[obj.name] = round(statistics.median(densities), 1)
    medians = list(per_object.values())
    return {
        "per_object_median_texels_per_metre": dict(
            sorted(per_object.items(), key=lambda item: item[1])
        ),
        "median": round(statistics.median(medians), 1),
        "lowest": round(min(medians), 1),
        "highest": round(max(medians), 1),
        "spread_ratio": round(max(medians) / max(min(medians), 1e-6), 2),
    }


def production_remap(root):
    """Reproduce the current production UV exactly, quadrant offsets included.

    This has to place every polygon in its own role quadrant, not just apply the
    quadrant scale: the offsets are what decide whether a readout face lands on
    the emissive part of the sheet at all.
    """
    for obj in list(root.children_recursive):
        if obj.type != "MESH":
            continue
        roles = polygon_roles(obj)
        export.smart_unwrap(obj)
        uv_layer = obj.data.uv_layers.active
        for polygon, role in zip(obj.data.polygons, roles):
            offset_u, offset_v = export.QUADRANTS[role]
            for index in polygon.loop_indices:
                uv = uv_layer.data[index].uv
                uv.x = offset_u + max(0.0, min(1.0, uv.x)) * export.QUADRANT_SCALE
                uv.y = offset_v + max(0.0, min(1.0, uv.y)) * export.QUADRANT_SCALE


def production_baseline(root):
    """Density under the current production unwrap."""
    production_remap(root)
    return summarise(root)


def build_runtime_materials(project_root, theme, scale_class, texture_dir=None):
    """The two runtime materials, sampled through the mesh UV.

    ``v6_theme_materials`` samples the atlas with a BOX projection on Generated
    coordinates, which is not what Unity does: production bakes the quadrant
    into the mesh UV and collapses to opaque + emissive. Previews built the old
    way cannot predict the shipped look, so the comparison renders use this
    instead.
    """
    profile = v6_theme_materials.SCALE_PROFILES[scale_class]
    if texture_dir is None:
        texture_dir = (
            Path(project_root)
            / "Assets/MatsuMotoMeterAR/Content/Themes"
            / theme
            / "Textures/ThemeMaterialV6"
        )
    texture_dir = Path(texture_dir)
    prefix = f"T_{theme}_V6_Atlas{profile['texture_suffix']}"
    images = {
        "base": v6_theme_materials.load_image(
            texture_dir / f"{prefix}_BaseColor.png"
        ),
        "normal": v6_theme_materials.load_image(
            texture_dir / f"{prefix}_Normal.png", non_color=True
        ),
        "packed": v6_theme_materials.load_image(
            texture_dir / f"{prefix}_MetallicSmoothness.png", non_color=True
        ),
        "emission": v6_theme_materials.load_image(
            texture_dir / f"{prefix}_Emission.png"
        ),
    }

    def build(name, emissive):
        material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        uv = nodes.new("ShaderNodeUVMap")

        def texture(image):
            node = nodes.new("ShaderNodeTexImage")
            node.image = image
            node.projection = "FLAT"
            node.extension = "CLIP"
            node.interpolation = "Linear"
            links.new(uv.outputs["UV"], node.inputs["Vector"])
            return node

        base = texture(images["base"])
        normal = texture(images["normal"])
        packed = texture(images["packed"])
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = profile["normal_strength"]
        separate = nodes.new("ShaderNodeSeparateColor")
        roughness = nodes.new("ShaderNodeMath")
        roughness.operation = "SUBTRACT"
        roughness.inputs[0].default_value = 1.0

        links.new(base.outputs["Color"], shader.inputs["Base Color"])
        links.new(normal.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
        links.new(packed.outputs["Color"], separate.inputs["Color"])
        links.new(separate.outputs["Red"], shader.inputs["Metallic"])
        links.new(packed.outputs["Alpha"], roughness.inputs[1])
        links.new(roughness.outputs["Value"], shader.inputs["Roughness"])
        if emissive:
            emission = texture(images["emission"])
            colour = v6_theme_materials.input_named(
                shader, "Emission Color", "Emission"
            )
            strength = v6_theme_materials.input_named(shader, "Emission Strength")
            if colour is not None:
                links.new(emission.outputs["Color"], colour)
            if strength is not None:
                strength.default_value = v6_theme_materials.EMISSION_STRENGTH[theme]
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        material["v6_material_role"] = "readout" if emissive else "body"
        return material

    tag = texture_dir.name
    return build(f"MAT_{theme}_V6_AtlasUV_{tag}", False), build(
        f"MAT_{theme}_V6_AtlasUV_{tag}_Emissive", True
    )


def assign_runtime_materials(root, opaque, emissive):
    """Collapse to opaque + emissive using the same rule as production."""
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        uv_layer = obj.data.uv_layers.active
        flags = []
        for polygon in obj.data.polygons:
            coordinates = [
                uv_layer.data[index].uv for index in polygon.loop_indices
            ]
            centre_u = sum(uv.x for uv in coordinates) / len(coordinates)
            centre_v = sum(uv.y for uv in coordinates) / len(coordinates)
            flags.append(centre_u >= 0.5 and centre_v < 0.5)
        obj.data.materials.clear()
        obj.data.materials.append(opaque)
        if any(flags):
            obj.data.materials.append(emissive)
        for polygon, is_emissive in zip(obj.data.polygons, flags):
            polygon.material_index = 1 if is_emissive else 0


def set_emission_enabled(enabled, theme):
    for material in bpy.data.materials:
        if not material.name.endswith("_Emissive") or "AtlasUV" not in material.name:
            continue
        shader = next(
            (
                node
                for node in material.node_tree.nodes
                if node.type == "BSDF_PRINCIPLED"
            ),
            None,
        )
        if shader is None:
            continue
        strength = v6_theme_materials.input_named(shader, "Emission Strength")
        if strength is not None:
            strength.default_value = (
                v6_theme_materials.EMISSION_STRENGTH[theme] if enabled else 0.0
            )


def render_atlas_comparison(project_root, key, revision, scale_class, labels):
    """Same shape, same constant-density UV, different atlas detail frequency."""
    spec = pilot.PILOT[key]
    rig = review.RIGS[key]
    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / pilot.THEME
    source = (
        candidate_dir
        / f"BL_{key}_{pilot.THEME}_V6_Opus5_{revision}_Retopo.blend"
    )
    variants = [("ThemeMaterialV6", None)] + [
        (
            f"Repeats{label}",
            candidate_dir / "textures" / f"Repeats{label}" / pilot.THEME,
        )
        for label in labels
    ]
    written = {}
    for tag, texture_dir in variants:
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
        review.configure_scene()
        root = bpy.data.objects[spec["root"]]
        apply(root, scale_class)
        opaque, emissive = build_runtime_materials(
            project_root, pilot.THEME, scale_class, texture_dir
        )
        assign_runtime_materials(root, opaque, emissive)
        review.set_pose(root, key, spec["labelled_poses"]["neutral"])
        set_emission_enabled(True, pilot.THEME)
        path = (
            candidate_dir
            / "review"
            / f"Preview_{key}_{pilot.THEME}_V6_Atlas_{tag}.png"
        )
        review.shot(
            rig,
            rig["focus"],
            rig["radius"],
            review.VIEWS["front_three_quarter"],
            rig["lens"],
            path,
        )
        written[tag] = path
    for tag, path in written.items():
        if tag == "ThemeMaterialV6":
            continue
        review.contact_sheet(
            written["ThemeMaterialV6"],
            path,
            candidate_dir
            / "contact_sheets"
            / f"ContactSheet_{key}_{pilot.THEME}_V6_AtlasDetail_{tag}.png",
        )
    print(f"[Opus5AtlasUV] {key}: rendered {len(written)} atlas variants")


def render_comparison(project_root, key, revision, scale_class):
    """Production UV versus constant-density UV, on the same R2 shape."""
    spec = pilot.PILOT[key]
    rig = review.RIGS[key]
    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / pilot.THEME
    source = (
        candidate_dir
        / f"BL_{key}_{pilot.THEME}_V6_Opus5_{revision}_Retopo.blend"
    )
    written = {}
    for tag, prepare in (
        ("ProductionUV", lambda root: production_baseline(root)),
        ("ConstantUV", lambda root: apply(root, scale_class)),
    ):
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
        review.configure_scene()
        root = bpy.data.objects[spec["root"]]
        prepare(root)
        opaque, emissive = build_runtime_materials(
            project_root, pilot.THEME, scale_class
        )
        assign_runtime_materials(root, opaque, emissive)
        review.set_pose(root, key, spec["labelled_poses"]["neutral"])
        for label, enabled in (("emissive_off", False), ("emissive_on", True)):
            set_emission_enabled(enabled, pilot.THEME)
            path = (
                candidate_dir
                / "review"
                / f"Preview_{key}_{pilot.THEME}_V6_AtlasUV_{tag}_{label}.png"
            )
            review.shot(
                rig,
                rig["focus"],
                rig["radius"],
                review.VIEWS["front_three_quarter"],
                rig["lens"],
                path,
            )
            written.setdefault(label, {})[tag] = path
    for label, pair in written.items():
        review.contact_sheet(
            pair["ProductionUV"],
            pair["ConstantUV"],
            candidate_dir
            / "contact_sheets"
            / f"ContactSheet_{key}_{pilot.THEME}_V6_AtlasUV_{label}.png",
        )
    print(f"[Opus5AtlasUV] {key}: rendered {len(written)} UV comparisons")


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def run_one(project_root, key, revision, scale_class):
    spec = pilot.PILOT[key]
    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / pilot.THEME
    source = (
        candidate_dir
        / f"BL_{key}_{pilot.THEME}_V6_Opus5_{revision}_Retopo.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(source)

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    before = production_baseline(bpy.data.objects[spec["root"]])

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[spec["root"]]
    entries = apply(root, scale_class)
    after = summarise(root)

    output = (
        candidate_dir
        / f"BL_{key}_{pilot.THEME}_V6_Opus5_{revision}_AtlasUV.blend"
    )
    save_blend(output)

    clamped = [entry for entry in entries if entry["clamped"]]
    report = {
        "source": str(source.relative_to(project_root)),
        "candidate": str(output.relative_to(project_root)),
        "scale_class": scale_class,
        "target_texels_per_metre": TARGET_TEXELS_PER_METRE[scale_class],
        "atlas_pixels": ATLAS_PIXELS,
        "quadrant_scale": export.QUADRANT_SCALE,
        "unchanged": [
            "atlas layout (2x2 role quadrants) and quadrant offsets",
            "theme palette and role boundaries",
            "texture count and 1024 px sheet size",
            "two shared runtime materials (opaque + emissive)",
        ],
        "density_production_path": before,
        "density_constant_path": after,
        "clamped_parts": clamped,
        "parts": entries,
        "authoring_environment": blender_compat.provenance(),
    }
    report_path = (
        candidate_dir
        / "reports"
        / f"{key}_{pilot.THEME}_V6_Opus5_{revision}_AtlasUV.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"[Opus5AtlasUV] {key}: spread x{before['spread_ratio']} -> "
        f"x{after['spread_ratio']} "
        f"({before['lowest']}..{before['highest']} -> "
        f"{after['lowest']}..{after['highest']} tx/m), "
        f"{len(clamped)} clamped"
    )
    return report


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    for key in args.object_key or list(pilot.PILOT):
        run_one(project_root, key, args.revision, args.scale_class)
        if args.render:
            render_comparison(
                project_root, key, args.revision, args.scale_class
            )
        if args.compare_atlas:
            render_atlas_comparison(
                project_root,
                key,
                args.revision,
                args.scale_class,
                args.compare_atlas,
            )


if __name__ == "__main__":
    main()
