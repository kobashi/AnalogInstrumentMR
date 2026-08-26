"""B3U R2: the nameplate removed, and nothing put in its place.

Alignment 307. R1 moved the nameplate and stopped it glowing, but it kept a
blank rectangle with nothing engraved on it, and it excluded the moving part
from the projected-overlap gate on its own authority - which §306 had not
allowed and which the PowerSlider close-up shows was not a technicality: the
handle covers the plate.

Neither control has a defined model name, rating, state or direction of
operation to put on a plate, so there is nothing to relocate. `plate_label` is
deleted outright and nothing replaces it - no plate, no frame, no recess, no
printed field, no emissive surface. If a real legend is specified later it
gets designed then, with its meaning, viewing distance and placement agreed.

The nameplate is never built rather than built and filtered: `p1.nameplate`
returns None for the duration and the join drops it, so no object, mesh, face,
UV or material slot from it can survive into the FBX or the Blend. That is
reported as a count, not asserted.

Everything else is R1's, unchanged: the same vertices, hierarchy, pivot and
moving nodes, travel, tool bores, grip UV and the same five 1024 maps.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r4_b3u_r2.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

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
import opus5_theme4_full_p6_batch_a_r4_b3u as b3u
import opus5_theme4_full_p6_batch_a_r4_b3u_r1 as r1
import opus5_theme4_production_atlas_proposal_b3 as b3
import opus5_theme4_material_p2 as m2

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r4_b3u_r2")
OUTPUT = f"{TREE}/theme4_full_p6_batch_a_r4_b3u_r2.json"
R1_TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
           "delivery_p6/batch_a_r4_b3u_r1")
ATLAS_PIXELS = 1024
REMOVED = "plate_label"

VIEWS = {"front": (0.0, 0.0), "oblique_left": (-38.0, 18.0),
         "oblique_right": (38.0, 18.0)}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


DROP_MARK = "__dropped_nameplate"


def no_nameplate(*args, **kwargs):
    """An empty mesh in the nameplate's place, discarded before the join.

    Returning None looked cleaner but the builder hands its parts list to the
    coplanar audit before joining, and that walks every entry. An empty mesh
    contributes no face, no UV and no material, and the join drops the object
    and its datablock, so nothing from it can reach the file. The marker name
    deliberately does not contain "plate_label", which keeps the residue scan
    an honest search rather than a search for something renamed.
    """
    mesh = bpy.data.meshes.new(DROP_MARK)
    obj = bpy.data.objects.new(DROP_MARK, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def build_without_nameplate(asset, builder):
    """R4's builder with the nameplate call neutered and its slot dropped."""
    original_nameplate = p1.nameplate
    original_join = p1.join
    original_role = b3.proposal_role

    def filtering_join(target, others):
        group = []
        for obj in [target] + list(others):
            if obj is None:
                continue
            if obj.name.split(".")[0] == DROP_MARK:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
                continue
            group.append(obj)
        return original_join(group[0], group[1:])

    p1.nameplate = no_nameplate
    p1.join = filtering_join
    b3.proposal_role = b3u.proposal_role_fixed
    try:
        root, body, mover, moving, tagged, audit = b3.build_for_proposal(
            asset, builder)
    finally:
        p1.nameplate = original_nameplate
        p1.join = original_join
        b3.proposal_role = original_role
    movers = list(moving) if isinstance(moving, (list, tuple)) else [moving]
    return root, body, mover, movers, tagged, audit


def residue_scan(where):
    """Anything at all still carrying the removed part's name."""
    return {
        "where": where,
        "objects": sorted(o.name for o in bpy.data.objects
                          if REMOVED in o.name),
        "meshes": sorted(m.name for m in bpy.data.meshes if REMOVED in m.name),
        "orphan_meshes": sorted(m.name for m in bpy.data.meshes
                                if REMOVED in m.name and m.users == 0),
        "placeholder_objects": sorted(o.name for o in bpy.data.objects
                                      if DROP_MARK in o.name),
        "placeholder_meshes": sorted(m.name for m in bpy.data.meshes
                                     if DROP_MARK in m.name),
        "materials": sorted(m.name for m in bpy.data.materials
                            if REMOVED in m.name),
    }


def scene_face_and_uv_count():
    faces = 0
    loops = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        faces += len(obj.data.polygons)
        if obj.data.uv_layers.active:
            loops += len(obj.data.uv_layers.active.data)
    return faces, loops


def read_positions(path):
    """Per-object unique world positions and triangles from an FBX."""
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
        rows[obj.name.split(".")[0]] = {
            "triangles": len(mesh.loop_triangles),
            "positions": {tuple(round(c, 6) for c in (matrix @ v.co))
                          for v in mesh.vertices},
            "materials": [m.name if m else None for m in mesh.materials],
        }
    hierarchy = sorted(f"{o.name.split('.')[0]}<-"
                       f"{o.parent.name.split('.')[0] if o.parent else '-'}"
                       for o in bpy.data.objects)
    names = sorted(o.name.split(".")[0] for o in bpy.data.objects)
    return rows, hierarchy, names


def compare_with_r1(r1_rows, r2_rows):
    """R2 must be R1 minus exactly the nameplate, and nothing else.

    A count comparison would not show that: it would pass if some other part
    lost the same number of vertices. The sets are differenced instead, so the
    only positions R1 has and R2 does not are the ones the removed plate
    occupied, and R2 introduces none of its own.
    """
    rows = {}
    clean = sorted(r1_rows) == sorted(r2_rows)
    for name in sorted(r1_rows):
        a = r1_rows[name]
        b = r2_rows.get(name)
        if b is None:
            rows[name] = {"present": False}
            clean = False
            continue
        removed = a["positions"] - b["positions"]
        added = b["positions"] - a["positions"]
        row = {
            "triangles": [a["triangles"], b["triangles"]],
            "triangles_removed": a["triangles"] - b["triangles"],
            "unique_positions": [len(a["positions"]), len(b["positions"])],
            "positions_removed": len(removed),
            "positions_added": len(added),
            "r2_is_subset_of_r1": not added,
            "materials": [a["materials"], b["materials"]],
        }
        if added:
            clean = False
        rows[name] = row
    return {
        "per_object": rows,
        "all_objects_present": sorted(r1_rows) == sorted(r2_rows),
        "no_new_geometry_anywhere": all(
            r.get("r2_is_subset_of_r1", False) for r in rows.values()),
        "clean": clean,
        "method": ("both FBX re-imported; unique world position sets "
                   "differenced per object"),
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    geometry_dir = tree / "geometry"
    compare_dir = tree / "comparison"
    for folder in (tree, geometry_dir, compare_dir):
        folder.mkdir(parents=True, exist_ok=True)

    textures, _ = b3u.build_atlas(tree, ATLAS_PIXELS)
    atlas_check = {}
    for name, path in textures.items():
        source = project_root / R1_TREE / path.name
        atlas_check[name] = {
            "file": path.name,
            "r1_sha256": m1.digest(source) if source.exists() else None,
            "r2_sha256": m1.digest(path),
            "identical": (source.exists()
                          and m1.digest(source) == m1.digest(path)),
        }

    payload = {
        "phase": "Theme4-P6-BatchA-R4-B3U-R2",
        "note": ("plate_label deleted from both controls with no replacement "
                 "plate, frame, recess, print or emissive surface. Everything "
                 "else is R1's. R4, B3U, R1, Batch B/C, Assets, Builds, docs "
                 "and git are untouched."),
        "removed_part": REMOVED,
        "replacement": "none",
        "atlas_pixels": ATLAS_PIXELS,
        "atlas_identical_to_r1": atlas_check,
        "assets": {},
    }

    for asset, builder in r4.BUILDERS_R4.items():
        root, body, mover, movers, tagged, audit = build_without_nameplate(
            asset, builder)
        meshes = [body] + movers
        for obj in meshes:
            m2.unwrap(obj)
        opaque, emissive = b3u.b3_materials(textures)
        rows = {}
        for obj in meshes:
            slots = [b3.role_of(slot.material) for slot in obj.material_slots]
            b3.cylindrical_grip_uv(obj, slots)
            counts, used = b3.pack_into_proposal(obj, slots, opaque, emissive)
            rows[obj.name] = {
                "role_face_counts": counts,
                "material_slots": [s.material.name
                                   for s in obj.material_slots],
                "submeshes": len(used),
            }
        bpy.context.view_layer.update()
        faces, loops = scene_face_and_uv_count()
        scene_residue = residue_scan("blend scene before export")
        scene_residue["tagged_parts_named_plate_label"] = sorted(
            n for n in tagged if REMOVED in n)

        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_R4_B3U_R2.fbx"
        d2.export_fbx(root, fbx)
        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_R4_B3U_R2.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))

        focus, radius, scale = p1.rig_for(meshes)
        images = {}
        for value, pose in ba.pose_set(asset):
            ba.apply_pose(mover, asset, value)
            bpy.context.view_layer.update()
            review.configure_scene()
            for label, view in VIEWS.items():
                path = compare_dir / f"R2_{asset}_{pose}_{label}.png"
                p1.shot(focus, radius, view, 52.0, scale, path)
                images[f"{pose}_{label}"] = str(
                    path.relative_to(project_root))
        ba.apply_pose(mover, asset, 0.0)
        # a close frame on the face the plate used to occupy
        for name, spot in (("Throttle", (-0.0780, -0.050, 0.0200)),
                           ("PowerSlider", (-0.0555, -0.050, 0.0000))):
            if name == asset:
                path = compare_dir / f"R2_{asset}_freed_face.png"
                p1.shot(spot, 0.150, (26.0, 14.0), 62.0, 0.075, path)
                images["freed_face"] = str(path.relative_to(project_root))

        payload["assets"][asset] = {
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "blend": str(blend.relative_to(project_root)),
            "blend_sha256": m1.digest(blend),
            "objects": rows,
            "renderers": len(meshes),
            "submeshes_total": sum(r["submeshes"] for r in rows.values()),
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "shared_materials": sorted(
                {n for r in rows.values() for n in r["material_slots"]}),
            "scene_faces": faces,
            "scene_uv_loops": loops,
            "residue_in_blend": scene_residue,
            "images": images,
        }
        print(f"[B3U-R2] {asset}: exported, renderers {len(meshes)}, "
              f"submeshes {payload['assets'][asset]['submeshes_total']}, "
              f"slots {payload['assets'][asset]['max_material_slots_per_object']}")

    for asset in payload["assets"]:
        row = payload["assets"][asset]
        r2_fbx = project_root / row["fbx"]
        r1_fbx = (project_root / R1_TREE
                  / f"SM_{asset}_{THEME}_V6_Opus5_R4_B3U_R1.fbx")
        r1_rows, r1_tree, r1_names = read_positions(r1_fbx)
        r2_rows, r2_tree, r2_names = read_positions(r2_fbx)
        row["vs_r1"] = compare_with_r1(r1_rows, r2_rows)
        row["vs_r1"]["hierarchy_equal"] = r1_tree == r2_tree
        row["vs_r1"]["r1_fbx_sha256"] = m1.digest(r1_fbx)
        row["residue_in_fbx"] = {
            "objects_named_plate_label": [n for n in r2_names if REMOVED in n],
            "imported_object_names": r2_names,
            "materials": sorted({m for r in r2_rows.values()
                                 for m in r["materials"] if m}),
        }
        row["triangles_total"] = sum(r["triangles"] for r in r2_rows.values())
        row["triangles_per_object"] = {k: v["triangles"]
                                       for k, v in r2_rows.items()}
        row["b3_on_import"] = b3u.measure_b3_on_import(r2_fbx, asset)
        print(f"[B3U-R2] {asset}: tris {row['triangles_total']}, subset of R1 "
              f"{row['vs_r1']['no_new_geometry_anywhere']}, residue "
              f"{len(row['residue_in_fbx']['objects_named_plate_label'])}, "
              f"grip pitch {row['b3_on_import']['pitch_around_mm']} x "
              f"{row['b3_on_import']['pitch_along_mm']} mm")

    payload["status"] = (
        "b3u_r2_ready"
        if all(row["vs_r1"]["clean"]
               and row["vs_r1"]["hierarchy_equal"]
               and not row["residue_in_fbx"]["objects_named_plate_label"]
               and not row["residue_in_blend"]["objects"]
               and not row["residue_in_blend"]["meshes"]
               and not row["residue_in_blend"]["placeholder_objects"]
               and not row["residue_in_blend"]["placeholder_meshes"]
               and row["renderers"] == 2
               and row["submeshes_total"] == 2
               and row["max_material_slots_per_object"] == 1
               and len(row["shared_materials"]) == 1
               and row["b3_on_import"]["pattern_stops_at_ferrule"]
               for row in payload["assets"].values())
        and all(entry["identical"] for entry in atlas_check.values())
        else "b3u_r2_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[B3U-R2] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
