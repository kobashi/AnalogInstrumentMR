"""Batch A R4 B3U: the same geometry, carrying B3 UVs, for Unity.

Alignment 303. R4's geometry is frozen. The atlas proposal produced maps and
comparison renders but no asset that carries the UVs those maps are for, and
the R4 delivery FBX still holds the frozen P4 layout, so B3 could not be
imported at all. This pass changes no vertex: it re-packs the same meshes onto
the B3 regions and ships them.

What it proves rather than asserts:

  * geometry equivalence against the R4 delivery FBX, by re-importing both and
    comparing per-object triangles, bounds and the unique vertex positions.
    Vertex *counts* are compared after import with care - an FBX splits
    vertices on UV seams, so B3U legitimately imports with more of them than
    R4 does while every position is identical.
  * the B3 properties re-measured on the re-imported mesh, not on the mesh
    that was exported: seam placement, the pattern stopping at the ferrule,
    the physical pitch on both grips, and region bleed.

The same UV layout is baked at 2048 and at 1024 so Codex can compare them on
device; the estimated GPU cost of both is computed for ASTC 6x6 with mipmaps
over the four production maps. NormalFlat exists only for the A/B renders and
is excluded from that total.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r4_b3u.py -- \
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
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_r4 as r4
import opus5_theme4_production_atlas_proposal_b3 as b3
import opus5_theme4_material_p2 as m2

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r4_b3u")
OUTPUT = f"{TREE}/theme4_full_p6_batch_a_r4_b3u.json"
R4_TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
           "delivery_p6/batch_a_r4")

RESOLUTIONS = (2048, 1024)
PRODUCTION_MAPS = ("BaseColor", "Normal", "MetallicSmoothness", "Emission")
REVIEW_ONLY_MAPS = ("NormalFlat",)

# Named so a Unity importer can bind the four maps without guessing: one
# opaque material and one emissive, both carrying the B3 prefix that the
# texture files use.
OPAQUE_MATERIAL = f"MAT_{THEME}_B3_Opaque"
EMISSIVE_MATERIAL = f"MAT_{THEME}_B3_Emissive"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


# B3's machined rule matches by prefix, and "plate" also matches
# "plate_label". The nameplate is the only readout face on either control, so
# in B3 it was routed to the machined normal region and lost its emissive
# role - which is why a B3U built straight from B3 exports one material slot
# and no Emission binding at all. Alignment 303 item 7 forbids editing the
# proposal file, so the rule is corrected here and the defect is reported
# rather than silently absorbed: B3's own comparison images carry it.
RELIEF_EXEMPT_ROLES = ("readout", "gasket")
# Bound at import: the patch below replaces b3.proposal_role, so calling it
# through the module would recurse into this function.
_B3_PROPOSAL_ROLE = b3.proposal_role


def proposal_role_fixed(name, base_role):
    if base_role in RELIEF_EXEMPT_ROLES:
        return base_role
    return _B3_PROPOSAL_ROLE(name, base_role)


def build_atlas(output_dir, pixels):
    """B3's own builder at a chosen resolution.

    `b3.ATLAS` is a module constant and alignment 303 item 7 forbids editing
    the proposal file, so it is set for the duration of the call and put back.
    The region rectangles are in UV and therefore resolution independent,
    which is what makes one layout serve both sizes.
    """
    previous = b3.ATLAS
    prefix = b3.PREFIX
    b3.ATLAS = pixels
    b3.PREFIX = f"T_{THEME}_B3_{pixels}"
    try:
        paths, stats = b3.build_proposal(output_dir)
    finally:
        b3.ATLAS = previous
        b3.PREFIX = prefix
    return paths, stats


def astc_6x6_bytes(pixels, mipmaps=True):
    """Bytes for one ASTC 6x6 texture, counted block by block per level."""
    total = 0
    levels = []
    size = pixels
    while True:
        blocks = math.ceil(size / 6)
        level = blocks * blocks * 16
        levels.append({"size": size, "blocks": blocks, "bytes": level})
        total += level
        if size == 1 or not mipmaps:
            break
        size = max(1, size // 2)
    return total, levels


def memory_estimate():
    rows = {}
    for pixels in RESOLUTIONS:
        per_map, levels = astc_6x6_bytes(pixels)
        rows[str(pixels)] = {
            "format": "ASTC 6x6, mipmapped",
            "bytes_per_map": per_map,
            "mib_per_map": round(per_map / 1048576.0, 4),
            "production_maps": len(PRODUCTION_MAPS),
            "total_bytes": per_map * len(PRODUCTION_MAPS),
            "total_mib": round(per_map * len(PRODUCTION_MAPS) / 1048576.0, 4),
            "mip_levels": len(levels),
            "base_level_bytes": levels[0]["bytes"],
        }
    big, small = str(RESOLUTIONS[0]), str(RESOLUTIONS[1])
    rows["comparison"] = {
        "saving_bytes": rows[big]["total_bytes"] - rows[small]["total_bytes"],
        "saving_mib": round((rows[big]["total_bytes"]
                             - rows[small]["total_bytes"]) / 1048576.0, 4),
        "ratio": round(rows[big]["total_bytes"] / rows[small]["total_bytes"], 4),
        "excluded_from_production": list(REVIEW_ONLY_MAPS),
        "note": ("NormalFlat is only used for the A/B renders and is not "
                 "counted here"),
    }
    return rows


# ---------------------------------------------------------------------------
# materials and export
# ---------------------------------------------------------------------------

def b3_materials(textures, tag=""):
    """Two shared materials wired to the four production maps.

    Named for the importer's benefit: an opaque and an emissive, both on the
    B3 prefix the texture files carry, so nothing has to be matched by hand.
    """
    def wire(material, emissive):
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
        relief.image = d2.load_map(textures["Normal"], "Non-Color")
        mapper = tree.nodes.new("ShaderNodeNormalMap")
        tree.links.new(relief.outputs["Color"], mapper.inputs["Color"])
        tree.links.new(mapper.outputs["Normal"], bsdf.inputs["Normal"])
        if emissive:
            emit = tree.nodes.new("ShaderNodeTexImage")
            emit.image = d2.load_map(textures["Emission"], "sRGB")
            if "Emission Color" in bsdf.inputs:
                tree.links.new(emit.outputs["Color"],
                               bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = 1.0

    opaque = bpy.data.materials.new(OPAQUE_MATERIAL + tag)
    wire(opaque, False)
    emissive = bpy.data.materials.new(EMISSIVE_MATERIAL + tag)
    wire(emissive, True)
    return opaque, emissive


def swap_maps(objects, textures):
    """Point every image node at another resolution of the same layout."""
    seen = set()
    for obj in objects:
        for slot in obj.material_slots:
            material = slot.material
            if material is None or material.name in seen:
                continue
            seen.add(material.name)
            for node in material.node_tree.nodes:
                if node.type != "TEX_IMAGE" or node.image is None:
                    continue
                for name, path in textures.items():
                    if node.image.name.endswith(name) or name in node.image.name:
                        node.image = d2.load_map(
                            path, "sRGB" if name in ("BaseColor", "Emission")
                            else "Non-Color")
                        break


# ---------------------------------------------------------------------------
# verification on the re-imported FBX
# ---------------------------------------------------------------------------

def read_fbx(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    bpy.context.view_layer.update()
    rows = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        world = [matrix @ v.co for v in mesh.vertices]
        lo = [min(w[i] for w in world) for i in range(3)]
        hi = [max(w[i] for w in world) for i in range(3)]
        rows[obj.name.split(".")[0]] = {
            "triangles": len(mesh.loop_triangles),
            "vertices": len(mesh.vertices),
            "bounds_min": [round(v, 6) for v in lo],
            "bounds_max": [round(v, 6) for v in hi],
            "unique_positions": sorted(
                {tuple(round(c, 6) for c in w) for w in world}),
            "materials": [m.name if m else None for m in mesh.materials],
            "uv_layers": [layer.name for layer in mesh.uv_layers],
        }
    hierarchy = sorted(f"{o.name.split('.')[0]}<-"
                       f"{o.parent.name.split('.')[0] if o.parent else '-'}"
                       for o in bpy.data.objects)
    return rows, hierarchy


def compare_geometry(reference, candidate, ref_tree, cand_tree):
    """Per-object triangles, bounds and the largest vertex position difference.

    Unique positions are compared rather than the vertex arrays: an exporter
    splits a vertex wherever the UV seam runs, so the B3U file legitimately
    carries more vertex records than R4 for the same shape. Positions are the
    invariant.
    """
    rows = {}
    same = sorted(reference) == sorted(candidate)
    for name in sorted(reference):
        a = reference[name]
        b = candidate.get(name)
        if b is None:
            rows[name] = {"present": False}
            same = False
            continue
        delta = 0.0
        positions_match = a["unique_positions"] == b["unique_positions"]
        if not positions_match and len(a["unique_positions"]) == len(b["unique_positions"]):
            for pa, pb in zip(a["unique_positions"], b["unique_positions"]):
                delta = max(delta, max(abs(pa[i] - pb[i]) for i in range(3)))
        bounds_delta = max(
            max(abs(a["bounds_min"][i] - b["bounds_min"][i]) for i in range(3)),
            max(abs(a["bounds_max"][i] - b["bounds_max"][i]) for i in range(3)))
        row = {
            "present": True,
            "triangles": [a["triangles"], b["triangles"]],
            "triangles_equal": a["triangles"] == b["triangles"],
            "vertex_records": [a["vertices"], b["vertices"]],
            "unique_positions": [len(a["unique_positions"]),
                                 len(b["unique_positions"])],
            "unique_positions_identical": positions_match,
            "max_position_delta_m": round(delta, 9),
            "max_bounds_delta_m": round(bounds_delta, 9),
            "bounds_equal": bounds_delta <= 1e-6,
            "r4_materials": a["materials"],
            "b3u_materials": b["materials"],
        }
        if not (row["triangles_equal"] and positions_match
                and row["bounds_equal"]):
            same = False
        rows[name] = row
    return {
        "per_object": rows,
        "hierarchy_r4": ref_tree,
        "hierarchy_b3u": cand_tree,
        "hierarchy_equal": ref_tree == cand_tree,
        "geometry_identical": same and ref_tree == cand_tree,
        "method": ("both FBX re-imported; unique world positions compared, "
                   "since UV seams split vertex records without moving them"),
    }


def measure_b3_on_import(path, asset):
    """Seam, ferrule stop, physical pitch and bleed, from the imported mesh.

    Everything here is read back out of the file that ships, not out of the
    scene that made it, because the question alignment 303 item 6 asks is
    whether the UVs survived the round trip.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    bpy.context.view_layer.update()
    grip_part, region, start_p, end_p = {
        "Throttle": ("handle_grip", "grip_throttle",
                     r4._along(r4.THROTTLE_ARM_A, r4.THROTTLE_ARM_B,
                               r4.ARM_GRIP_START), r4.THROTTLE_ARM_B),
        "PowerSlider": ("slider_grip", "grip_slider",
                        r4.SLIDER_GRIP_A, r4.SLIDER_GRIP_B),
    }[asset]
    box = b3.REGIONS[region]
    inset = b3.INSET
    span_u = (box[2] - box[0]) - 2 * inset
    span_v = (box[3] - box[1]) - 2 * inset
    around, along = b3.GRIP_COUNTS[region]

    start = np.array(start_p, dtype=float)
    end = np.array(end_p, dtype=float)
    axis = end - start
    length = float(np.linalg.norm(axis))
    direction = axis / length

    bleed = {name: {} for name in b3.RELIEF_REGIONS}
    seam_loops = 0
    grip_loops = 0
    foreign_in_grip = 0
    non_grip_parts = 0
    radii = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        layer = mesh.uv_layers.active.data
        for polygon in mesh.polygons:
            centre = polygon.center
            point = np.array(centre, dtype=float) - start
            along_s = float(np.dot(point, direction)) / length
            radial = point - (along_s * length) * direction
            # the grip is the span the loft actually covers; anything
            # with UVs in the grip region but sitting before it is the rod
            # or the ferrule leaking into the pattern
            on_grip = (-0.04 <= along_s <= 1.04
                       and float(np.linalg.norm(radial)) < 0.045)
            for index in polygon.loop_indices:
                u, v = layer[index].uv
                for name in b3.RELIEF_REGIONS:
                    r = b3.REGIONS[name]
                    if r[0] <= u <= r[2] and r[1] <= v <= r[3]:
                        key = f"{asset}:{obj.name.split('.')[0]}"
                        bleed[name][key] = bleed[name].get(key, 0) + 1
                        if name == region:
                            grip_loops += 1
                            if not on_grip:
                                foreign_in_grip += 1
                            radii.append(float(np.linalg.norm(radial)))
                            local_u = (u - box[0] - inset) / span_u
                            if local_u <= 0.02 or local_u >= 0.98:
                                seam_loops += 1
    mean_r = float(np.mean(radii)) if radii else 0.0
    return {
        "grip_part": grip_part,
        "region": region,
        "loops_in_grip_region": grip_loops,
        "loops_in_grip_region_not_on_the_grip": foreign_in_grip,
        "pattern_stops_at_ferrule": foreign_in_grip == 0,
        "seam_loops_at_u_edges": seam_loops,
        "seam_present": seam_loops > 0,
        "seam_placement": "theta = pi, rear of the grip",
        "measured_mean_radius_m": round(mean_r, 5),
        "measured_axis_length_m": round(length, 5),
        "repeats": [around, along],
        "pitch_around_mm": round(2.0 * math.pi * mean_r / around * 1000.0, 3)
        if mean_r else None,
        "pitch_along_mm": round(length / along * 1000.0, 3),
        "target_pitch_mm": round(b3.GRIP_PITCH_TARGET_M * 1000.0, 2),
        "region_bleed": bleed,
    }


def parse_args_main():
    return parse_args()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    geometry_dir = tree / "geometry"
    compare_dir = tree / "comparison"
    for folder in (tree, geometry_dir, compare_dir):
        folder.mkdir(parents=True, exist_ok=True)

    atlases = {}
    atlas_stats = {}
    for pixels in RESOLUTIONS:
        paths, stats = build_atlas(tree, pixels)
        atlases[pixels] = paths
        atlas_stats[str(pixels)] = stats

    payload = {
        "phase": "Theme4-P6-BatchA-R4-B3U",
        "note": ("UV handoff only. R4 geometry is unchanged and frozen; these "
                 "files carry the same meshes on the B3 layout so B3 can be "
                 "imported. R4, P4, the B3 proposal, Batch B, Assets, Builds, "
                 "docs and git are untouched."),
        "regions_uv": {name: [round(c, 6) for c in box]
                       for name, box in b3.REGIONS.items()},
        "relief_regions": list(b3.RELIEF_REGIONS),
        "grip_counts": {k: list(v) for k, v in b3.GRIP_COUNTS.items()},
        "materials": {"opaque": OPAQUE_MATERIAL, "emissive": EMISSIVE_MATERIAL,
                      "shared_material_budget": 2,
                      "map_binding": {name: f"T_{THEME}_B3_<size>_{name}.png"
                                      for name in PRODUCTION_MAPS}},
        "resolutions": list(RESOLUTIONS),
        "atlas_stats": atlas_stats,
        "textures": {str(pixels): {name: {
            "path": str(path.relative_to(project_root)),
            "sha256": m1.digest(path),
            "bytes": path.stat().st_size,
            "production": name in PRODUCTION_MAPS}
            for name, path in paths.items()}
            for pixels, paths in atlases.items()},
        "b3_defect_corrected_here": {
            "rule": "machined prefix \"plate\" also matched \"plate_label\"",
            "effect_in_b3": ("the nameplate was routed to the machined "
                             "normal region and lost its readout role, so a "
                             "B3 build has no emissive material at all"),
            "fix_here": ("readout and gasket are exempt from relief "
                         "promotion; the proposal file itself is unchanged"),
        },
        "gpu_memory_estimate": memory_estimate(),
        "assets": {},
    }

    exported = {}
    for asset, builder in r4.BUILDERS_R4.items():
        original_role = b3.proposal_role
        b3.proposal_role = proposal_role_fixed
        try:
            root, body, mover, moving, tagged, audit = b3.build_for_proposal(
                asset, builder)
        finally:
            b3.proposal_role = original_role
        movers = list(moving) if isinstance(moving, (list, tuple)) else [moving]
        meshes = [body] + movers
        for obj in meshes:
            m2.unwrap(obj)
        opaque, emissive = b3_materials(atlases[RESOLUTIONS[0]])
        rows = {}
        grip_uv = {}
        for obj in meshes:
            slots = [b3.role_of(slot.material) for slot in obj.material_slots]
            grip_uv.update(b3.cylindrical_grip_uv(obj, slots))
            counts, used = b3.pack_into_proposal(obj, slots, opaque, emissive)
            rows[obj.name] = {
                "role_face_counts": counts,
                "material_slots": [s.material.name
                                   for s in obj.material_slots],
                "submeshes": len(used),
            }
        bpy.context.view_layer.update()

        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6A_R4_B3U.fbx"
        d2.export_fbx(root, fbx)
        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P6A_R4_B3U.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        exported[asset] = fbx

        focus, radius, scale = p1.rig_for(meshes)
        images = {}
        for pixels in RESOLUTIONS:
            swap_maps(meshes, atlases[pixels])
            bpy.context.view_layer.update()
            review.configure_scene()
            near = compare_dir / f"Detail_{asset}_{pixels}_close.png"
            p1.shot(focus, radius * 0.46, (36.0, 16.0), 62.0, scale * 0.46,
                    near)
            images[f"close_{pixels}"] = str(near.relative_to(project_root))
            far = compare_dir / f"Detail_{asset}_{pixels}_quest080.png"
            p1.shot(focus, b3.QUEST_VIEW_DISTANCE_M, (24.0, 12.0), 40.0,
                    scale, far)
            images[f"quest080_{pixels}"] = str(far.relative_to(project_root))
        swap_maps(meshes, atlases[RESOLUTIONS[0]])

        payload["assets"][asset] = {
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "blend": str(blend.relative_to(project_root)),
            "blend_sha256": m1.digest(blend),
            "objects": rows,
            "submeshes_total": sum(r["submeshes"] for r in rows.values()),
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "grip_uv_at_build": grip_uv,
            "images": images,
        }
        print(f"[B3U] {asset}: exported, slots "
              f"{payload['assets'][asset]['max_material_slots_per_object']}, "
              f"submeshes {payload['assets'][asset]['submeshes_total']}")

    for asset, fbx in exported.items():
        reference = project_root / R4_TREE / (
            f"SM_{asset}_{THEME}_V6_Opus5_P6A_R4.fbx")
        ref_rows, ref_tree = read_fbx(reference)
        cand_rows, cand_tree = read_fbx(fbx)
        comparison = compare_geometry(ref_rows, cand_rows, ref_tree, cand_tree)
        comparison["reference_fbx"] = str(reference.relative_to(project_root))
        comparison["reference_sha256"] = m1.digest(reference)
        row = payload["assets"][asset]
        row["geometry_equivalence"] = comparison
        row["b3_on_import"] = measure_b3_on_import(fbx, asset)
        row["motion_contract"] = {
            "motion_target": ba.CONTRACT[asset]["pivot"],
            "movable": ba.CONTRACT[asset]["moving"],
            "unity_axis": ba.CONTRACT[asset]["unity_axis"],
            "unity_range": list(ba.CONTRACT[asset].get("unity_range_deg")
                                or ba.CONTRACT[asset].get("unity_range_m")),
            "nodes_present": all(
                any(name in entry for entry in comparison["hierarchy_b3u"])
                for name in (ba.CONTRACT[asset]["pivot"],
                             ba.CONTRACT[asset]["moving"])),
        }
        print(f"[B3U] {asset}: geometry identical "
              f"{comparison['geometry_identical']}, pattern stops at ferrule "
              f"{row['b3_on_import']['pattern_stops_at_ferrule']}, pitch "
              f"{row['b3_on_import']['pitch_around_mm']} x "
              f"{row['b3_on_import']['pitch_along_mm']} mm")

    payload["status"] = (
        "b3u_ready"
        if all(row["geometry_equivalence"]["geometry_identical"]
               and row["b3_on_import"]["pattern_stops_at_ferrule"]
               and row["b3_on_import"]["seam_present"]
               and row["motion_contract"]["nodes_present"]
               and row["max_material_slots_per_object"] <= 2
               for row in payload["assets"].values())
        else "b3u_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[B3U] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
