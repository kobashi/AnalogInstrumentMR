"""Production atlas proposal B1: dedicated normal regions for Theme 4.

Alignment 301. The P4 atlas is wired into the Unity materials but its Normal
map is flat everywhere except the pilot Lever's knurl patch, and no Batch A
part's UVs reach that patch. The result on Quest is a correct material with no
surface to show.

This is a *proposal*. It writes to its own folder and its own file names and
does not read, write or overwrite delivery_p4, so the frozen pilot atlas is
untouched and nothing in Batch A/B changes.

What it proposes:

  * 2048 instead of 1024, so a normal region can carry a pattern at a texel
    density the existing 1024 cannot.
  * The four role quadrants stay exactly where they are - body top-left,
    metal top-right, gasket bottom-left, readout bottom-right - so
    BaseColor, MetallicSmoothness and Emission keep the contract every theme
    already reads.
  * Inside two of those quadrants the Normal map gains named sub-regions:
      body/machined  a fine machined-face lay for housings and plates
      metal/grip     a tactile diamond for the Throttle and PowerSlider grips
      body/knurl     the pilot Lever's patch, carried forward unchanged in
                     position so an existing Lever UV still lands on knurl
    Everything else in the Normal map stays flat.

The comparison renders put the same geometry side by side with a flat normal
and with this one, at review distance and at an estimated Quest viewing
distance, so the question "does this actually show up" is answered by looking.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_production_atlas_proposal_b1.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_material_p2 as m2
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_delivery as bad
import opus5_theme4_full_p6_batch_a_r2 as r2

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r2/atlas_proposal")
OUTPUT = f"{TREE}/theme4_production_atlas_proposal_b1.json"
PREFIX = f"T_{THEME}_ProdB1_Atlas"
ATLAS = 2048
INSET = d2.QUADRANT_INSET

# Quadrant halves, then sub-regions inside them. u0, v0, u1, v1.
QUADRANT = {role: (cell[0] * 0.5, 1.0 - (cell[1] + 1) * 0.5,
                   cell[0] * 0.5 + 0.5, 1.0 - cell[1] * 0.5)
            for role, cell in d2.QUADRANTS.items()}


def _sub(quadrant, column, row):
    u0, v0, u1, v1 = QUADRANT[quadrant]
    du, dv = (u1 - u0) / 2.0, (v1 - v0) / 2.0
    return (u0 + column * du, v0 + row * dv,
            u0 + (column + 1) * du, v0 + (row + 1) * dv)


REGIONS = {
    # role surfaces keep their quadrant; the sub-regions below are where a
    # face goes when it wants relief.
    "body": _sub("body", 0, 0),
    "machined": _sub("body", 1, 0),
    "knurl": _sub("body", 0, 1),
    "body_spare": _sub("body", 1, 1),
    "metal": _sub("metal", 0, 0),
    "grip": _sub("metal", 1, 0),
    "metal_spare_a": _sub("metal", 0, 1),
    "metal_spare_b": _sub("metal", 1, 1),
    "gasket": QUADRANT["gasket"],
    "readout": QUADRANT["readout"],
}
SURFACE_ROLE = {"machined": "body", "knurl": "body", "body_spare": "body",
                "grip": "metal", "metal_spare_a": "metal",
                "metal_spare_b": "metal"}
RELIEF_REGIONS = ("machined", "grip", "knurl")


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def _tri(x):
    return 1.0 - 4.0 * np.abs(x - np.floor(x) - 0.5)


def machined_height(u, v):
    """A turned/brushed lay: fine circumferential arcs with a slow drift."""
    grid_u, grid_v = np.meshgrid(u, v)
    lay = 0.5 * (1.0 + np.cos(2.0 * math.pi * 210.0 * grid_v
                              + 1.1 * np.sin(2.0 * math.pi * 5.0 * grid_u)))
    grain = 0.28 * np.cos(2.0 * math.pi * 523.0 * grid_v + 2.1)
    return 0.55 * lay + 0.18 * grain


def grip_height(u, v):
    """A tactile diamond, coarser and deeper than the pilot's Lever knurl."""
    grid_u, grid_v = np.meshgrid(u, v)
    a = 42.0 * grid_u + 36.0 * grid_v
    b = 42.0 * grid_u - 36.0 * grid_v
    return 0.5 * (_tri(a) + _tri(b))


def knurl_height(u, v):
    """The pilot Lever's pattern, carried forward at the same counts."""
    grid_u, grid_v = np.meshgrid(u, v)
    window = np.sin(math.pi * np.clip(grid_v, 0.0, 1.0)) ** 2
    a = 24.0 * grid_u + 30.0 * grid_v
    b = 24.0 * grid_u - 30.0 * grid_v
    return window * 0.5 * (_tri(a) + _tri(b))


def normal_from_height(field, flank_deg):
    d_v, d_u = np.gradient(field)
    scale = np.percentile(np.abs(np.stack([d_u, d_v])), 99.5)
    if scale > 1e-9:
        factor = math.tan(math.radians(flank_deg)) / scale
        d_u, d_v = d_u * factor, d_v * factor
    normal = np.stack([-d_u, -d_v, np.ones_like(d_u)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return normal * 0.5 + 0.5


def pixel_box(region):
    u0, v0, u1, v1 = region
    return (int(round(u0 * ATLAS)), int(round((1.0 - v1) * ATLAS)),
            int(round(u1 * ATLAS)), int(round((1.0 - v0) * ATLAS)))


def build_proposal(output_dir):
    base = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    normal = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    metallic = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    smoothness = np.zeros((ATLAS, ATLAS), dtype=np.float32)
    emission = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    half = ATLAS // 2
    for role, (column, row) in d2.QUADRANTS.items():
        x0, y0 = column * half, row * half
        x1, y1 = x0 + half, y0 + half
        colour = m2.PALETTE[role]
        base[y0:y1, x0:x1] = [d2.srgb(colour[i]) for i in range(3)]
        normal[y0:y1, x0:x1] = [0.5, 0.5, 1.0]
        metallic[y0:y1, x0:x1, 0] = d2.SURFACE[role]["metallic"]
        smoothness[y0:y1, x0:x1] = d2.SURFACE[role]["smoothness"]
        if role == "readout":
            emission[y0:y1, x0:x1] = [
                d2.srgb(min(colour[i] * d2.EMISSION_STRENGTH, 1.0))
                for i in range(3)]

    stats = {}
    for name, maker, flank in (("machined", machined_height, 7.0),
                               ("grip", grip_height, 22.0),
                               ("knurl", knurl_height, 32.0)):
        x0, y0, x1, y1 = pixel_box(REGIONS[name])
        width, height = x1 - x0, y1 - y0
        u = (np.arange(width) + 0.5) / width
        v = (np.arange(height) + 0.5) / height
        block = normal_from_height(maker(u, v), flank)
        normal[y0:y1, x0:x1] = block
        stats[name] = {
            "region_uv": [round(c, 6) for c in REGIONS[name]],
            "pixels": [x0, y0, x1, y1],
            "size_px": [width, height],
            "flank_degrees": flank,
            "surface_role": SURFACE_ROLE.get(name, name),
        }

    deviation = np.abs(normal - np.array([0.5, 0.5, 1.0])).max(axis=-1)
    relief = deviation > 1.5 / 255.0
    outside = relief.copy()
    for name in RELIEF_REGIONS:
        x0, y0, x1, y1 = pixel_box(REGIONS[name])
        outside[y0:y1, x0:x1] = False
    stats["relief_texels_total"] = int(np.count_nonzero(relief))
    stats["relief_texels_outside_declared_regions"] = int(
        np.count_nonzero(outside))

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "BaseColor": d2.write_png(output_dir / f"{PREFIX}_BaseColor.png", base),
        "Normal": d2.write_png(output_dir / f"{PREFIX}_Normal.png", normal),
        "MetallicSmoothness": d2.write_png(
            output_dir / f"{PREFIX}_MetallicSmoothness.png", metallic,
            alpha=smoothness),
        "Emission": d2.write_png(output_dir / f"{PREFIX}_Emission.png",
                                 emission),
        "NormalFlat": d2.write_png(
            output_dir / f"{PREFIX}_Normal_Flat.png",
            np.tile(np.array([0.5, 0.5, 1.0], dtype=np.float32),
                    (ATLAS, ATLAS, 1))),
    }
    return paths, stats


# ---------------------------------------------------------------------------
# routing Batch A R2 parts to the proposed regions
# ---------------------------------------------------------------------------

# Which named parts want relief. Everything else keeps its plain role region,
# so the proposal is additive rather than a repaint.
RELIEF_RULES = (
    ("grip", ("handle_grip", "slider_grip")),
    ("machined", ("plate", "shell", "skirt", "slot_floor", "rail",
                  "rail_post", "cover", "hood")),
)


def proposal_role(name, base_role):
    stem = name.split(".")[0]
    for region, prefixes in RELIEF_RULES:
        for prefix in prefixes:
            if stem.startswith(prefix):
                return region
    return base_role


def build_for_proposal(asset, builder):
    """Batch A's build with the proposal's regions as authoring roles.

    The region a face ends up in is read back from its material name, so the
    promotion has to happen when the material is assigned - doing it after the
    join, as the first attempt did, left every face in its plain role region
    and the comparison would have shown nothing on either side.
    """
    p1.clear_scene()
    review.configure_scene()
    roles = m2.make_materials()
    for extra in RELIEF_REGIONS:
        material = bpy.data.materials.new(
            f"MAT_{THEME}_{extra.capitalize()}")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = m2.PALETTE[
                SURFACE_ROLE[extra]]
        roles[extra] = material
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    original_join, original_assign = p1.join, p1.assign
    tagged = {}

    def tagging_join(target, others):
        for obj in [target] + list(others):
            stem = obj.name.split(".")[0]
            role = proposal_role(stem, bad.role_for(stem))
            tagged[stem] = role
            obj.data.materials.clear()
            obj.data.materials.append(roles[role])
        return original_join(target, others)

    p1.join = tagging_join
    p1.assign = lambda obj, material: None
    try:
        body, mover, moving, audit = builder(roles["body"])
    finally:
        p1.join, p1.assign = original_join, original_assign
    for obj in (body, mover):
        obj.parent = root
    bpy.context.view_layer.update()
    return root, body, mover, moving, tagged, audit


def pack_into_proposal(obj, role_of_slot, atlas, emissive):
    work = bmesh.new()
    work.from_mesh(obj.data)
    layer = work.loops.layers.uv.active
    counts = {}
    faces = {}
    for face in work.faces:
        role = role_of_slot[face.material_index]
        counts[role] = counts.get(role, 0) + 1
        u0, v0, u1, v1 = REGIONS[role]
        for loop in face.loops:
            uv = loop[layer].uv
            uv.x = (u0 + INSET) + min(max(uv.x, 0.0), 1.0) * (u1 - u0 - 2 * INSET)
            uv.y = (v0 + INSET) + min(max(uv.y, 0.0), 1.0) * (v1 - v0 - 2 * INSET)
        faces[face.index] = 0 if role != "readout" else 1
    work.to_mesh(obj.data)
    work.free()
    obj.data.materials.clear()
    obj.data.materials.append(atlas)
    obj.data.materials.append(emissive)
    for polygon in obj.data.polygons:
        polygon.material_index = faces[polygon.index]
    used = sorted({polygon.material_index for polygon in obj.data.polygons})
    if len(used) < len(obj.data.materials):
        remap = {old: new for new, old in enumerate(used)}
        keep = [obj.data.materials[i] for i in used]
        indices = [remap[p.material_index] for p in obj.data.polygons]
        obj.data.materials.clear()
        for material in keep:
            obj.data.materials.append(material)
        for polygon, index in zip(obj.data.polygons, indices):
            polygon.material_index = index
        used = sorted(set(indices))
    return counts, used


def region_bleed_audit(objects):
    """Which declared relief region every loop lands in, and the margins."""
    rows = {name: {} for name in RELIEF_REGIONS}
    margins = {name: None for name in RELIEF_REGIONS}
    for label, obj in objects:
        layer = obj.data.uv_layers.active.data
        for name in RELIEF_REGIONS:
            u0, v0, u1, v1 = REGIONS[name]
            hits = 0
            nearest = None
            for loop_uv in layer:
                u, v = loop_uv.uv
                if u0 <= u <= u1 and v0 <= v <= v1:
                    hits += 1
                else:
                    distance = max(u0 - u, u - u1, v0 - v, v - v1)
                    nearest = distance if nearest is None else min(nearest,
                                                                   distance)
            rows[name][label] = hits
            if nearest is not None:
                margins[name] = (nearest if margins[name] is None
                                 else min(margins[name], nearest))
    return {
        "loops_per_region": rows,
        "nearest_outside_uv": {k: (round(v, 6) if v is not None else None)
                               for k, v in margins.items()},
        "nearest_outside_texels": {
            k: (round(v * ATLAS, 1) if v is not None else None)
            for k, v in margins.items()},
    }


def wire(material, textures, normal_key, emissive):
    material.use_nodes = True
    tree = material.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    colour = tree.nodes.new("ShaderNodeTexImage")
    colour.image = d2.load_map(textures["BaseColor"], "sRGB")
    tree.links.new(colour.outputs["Color"], bsdf.inputs["Base Color"])
    packed = tree.nodes.new("ShaderNodeTexImage")
    packed.image = d2.load_map(textures["MetallicSmoothness"], "Non-Color")
    tree.links.new(packed.outputs["Color"], bsdf.inputs["Metallic"])
    invert = tree.nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    tree.links.new(packed.outputs["Alpha"], invert.inputs[1])
    tree.links.new(invert.outputs["Value"], bsdf.inputs["Roughness"])
    relief = tree.nodes.new("ShaderNodeTexImage")
    relief.image = d2.load_map(textures[normal_key], "Non-Color")
    mapper = tree.nodes.new("ShaderNodeNormalMap")
    tree.links.new(relief.outputs["Color"], mapper.inputs["Color"])
    tree.links.new(mapper.outputs["Normal"], bsdf.inputs["Normal"])
    if emissive:
        emit = tree.nodes.new("ShaderNodeTexImage")
        emit.image = d2.load_map(textures["Emission"], "sRGB")
        if "Emission Color" in bsdf.inputs:
            tree.links.new(emit.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 1.0


def materials_for(textures, normal_key, tag):
    atlas = bpy.data.materials.new(f"MAT_{THEME}_ProdB1_Atlas_{tag}")
    wire(atlas, textures, normal_key, False)
    emissive = bpy.data.materials.new(f"MAT_{THEME}_ProdB1_Emissive_{tag}")
    wire(emissive, textures, normal_key, True)
    return atlas, emissive


# A Quest 3 eye buffer is about 2064 px across roughly 96 degrees, so a
# 0.24 m instrument at 0.8 m subtends about 370 px. The Quest-distance frame
# is rendered at that scale rather than at review resolution, which is the
# only honest way to ask whether the relief survives.
QUEST_VIEW_DISTANCE_M = 0.80
QUEST_PIXELS_PER_METRE_AT_080 = 1540


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    compare_dir = tree / "comparison"
    for folder in (tree, compare_dir):
        folder.mkdir(parents=True, exist_ok=True)
    textures, stats = build_proposal(tree)

    payload = {
        "phase": "Theme4-ProductionAtlas-Proposal-B1",
        "status_note": ("proposal only; delivery_p4 is not read, written or "
                        "overwritten and Batch A/B ship unchanged"),
        "atlas_pixels": ATLAS,
        "previous_atlas_pixels": d2.ATLAS,
        "quadrants_unchanged": {role: list(box)
                                for role, box in QUADRANT.items()},
        "regions_uv": {name: [round(c, 6) for c in box]
                       for name, box in REGIONS.items()},
        "relief_regions": list(RELIEF_REGIONS),
        "surface_role_of_region": SURFACE_ROLE,
        "relief_rules": {region: list(prefixes)
                         for region, prefixes in RELIEF_RULES},
        "normal_regions": stats,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "quest_assumption": {
            "distance_m": QUEST_VIEW_DISTANCE_M,
            "pixels_per_metre": QUEST_PIXELS_PER_METRE_AT_080,
            "basis": ("Quest 3 eye buffer ~2064 px over ~96 deg; a 0.24 m "
                      "instrument at 0.8 m subtends ~370 px"),
        },
        "assets": {},
    }

    bleed = {"loops_per_region": {name: {} for name in RELIEF_REGIONS},
             "nearest_outside_texels": {}}
    for asset, builder in r2.BUILDERS_R2.items():
        root, body, mover, moving, tagged, audit = build_for_proposal(
            asset, builder)
        movers = list(moving) if isinstance(moving, (list, tuple)) else [moving]
        meshes = [body] + movers
        for obj in meshes:
            m2.unwrap(obj)
        rows = {}
        atlas_on, emissive_on = materials_for(textures, "Normal", "on")
        for obj in meshes:
            slots = [slot.material.name.rsplit("_", 1)[-1].lower()
                     for slot in obj.material_slots]
            counts, used = pack_into_proposal(obj, slots, atlas_on,
                                              emissive_on)
            rows[obj.name] = {
                "role_face_counts": counts,
                "submeshes": len(used),
                "promoted_regions": sorted(
                    {r for r in counts if r in RELIEF_REGIONS}),
            }
        bpy.context.view_layer.update()
        measured = region_bleed_audit(
            [(f"{asset}:{obj.name}", obj) for obj in meshes])
        for name in RELIEF_REGIONS:
            bleed["loops_per_region"][name].update(
                measured["loops_per_region"][name])
            value = measured["nearest_outside_texels"][name]
            if value is not None:
                current = bleed["nearest_outside_texels"].get(name)
                bleed["nearest_outside_texels"][name] = (
                    value if current is None else min(current, value))

        review.configure_scene()
        focus, radius, scale = p1.rig_for(meshes)
        images = {}
        for tag, normal_key in (("relief", "Normal"), ("flat", "NormalFlat")):
            atlas_m, emissive_m = materials_for(textures, normal_key, tag)
            for obj in meshes:
                keep = len(obj.data.materials)
                obj.data.materials.clear()
                obj.data.materials.append(atlas_m)
                if keep > 1:
                    obj.data.materials.append(emissive_m)
            bpy.context.view_layer.update()
            path = compare_dir / f"Compare_{asset}_{tag}.png"
            p1.shot(focus, radius * 0.46, (36.0, 16.0), 62.0, scale * 0.46,
                    path)
            images[f"close_{tag}"] = str(path.relative_to(project_root))
            quest = compare_dir / f"Quest080_{asset}_{tag}.png"
            p1.shot(focus, QUEST_VIEW_DISTANCE_M, (24.0, 12.0), 40.0, scale,
                    quest)
            images[f"quest_{tag}"] = str(quest.relative_to(project_root))
        payload["assets"][asset] = {"objects": rows, "images": images}
        print(f"[AtlasProposalB1] {asset}: regions "
              f"{sorted({r for v in rows.values() for r in v['promoted_regions']})}")

    payload["region_bleed"] = bleed
    payload["status"] = (
        "proposal_ready"
        if stats["relief_texels_outside_declared_regions"] == 0
        else "proposal_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[AtlasProposalB1] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
