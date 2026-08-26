"""Theme 4 P5 delivery: P4's atlas and packing, on the corrected lever.

Alignment 292. Nothing about the material contract changes in P5, so nothing
about it is re-authored here: the textures, the region layout, the grip's
cylindrical UV, the two delivery materials and the needle gate are P4's,
imported and called. Only the Lever's geometry differs, and only the Lever's
review images and clearance figures should differ with it.

The four atlas maps are written by P4's builder under P4's names, so their
SHA256 can be compared directly with delivery_p4's and the "byte-identical"
claim alignment 292.1 item 2 asks for is a comparison rather than an
assertion.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_delivery_p5.py -- \
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
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_machined_ergonomics_p5 as p5
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_delivery_p4 as p4d
import opus5_theme4_material_p2 as m2

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p5"
OUTPUT = f"{TREE}/theme4_delivery_p5.json"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    review_dir = tree / "review"
    needle_dir = tree / "needle"
    detail_dir = tree / "detail"
    for folder in (tree, review_dir, needle_dir, detail_dir):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P5-delivery",
        "note": ("P4's atlas, regions, packing, materials and needle gate, "
                 "unchanged, on P5 geometry. Only the Lever differs."),
        "atlas_pixels": d2.ATLAS,
        "regions_uv": {role: list(box) for role, box in p4d.REGIONS.items()},
        "region_inset_uv": p4d.INSET,
        "region_surface_source": {"knurl": "body"},
        "surface": d2.SURFACE,
        "knurl_patch": knurl_stats,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "assets": {},
    }

    bleed_hits, bleed_nearest = {}, []
    for asset, builder in p5.BUILDERS_P5.items():
        root, body, pivot, part, tagged, audit = p4d.build(asset, builder)
        for obj in (body, part):
            m2.unwrap(obj)
        atlas, emissive = p4d.delivery_materials_p4(textures)
        rows = {}
        grip_uv = None
        for obj in (body, part):
            role_of_slot = [slot.material.name.rsplit("_", 1)[-1].lower()
                            for slot in obj.material_slots]
            if "knurl" in role_of_slot:
                grip_uv = p4d.grip_cylindrical_uv(obj, role_of_slot)
            counts, used = p4d.pack_into_regions(obj, role_of_slot,
                                                 atlas, emissive)
            rows[obj.name] = {
                "role_face_counts": counts,
                "material_slots": [s.material.name for s in obj.material_slots],
                "submeshes": len(used),
            }
        bpy.context.view_layer.update()
        hits, closest = p4d.knurl_bleed_audit(
            [(f"{asset}:{obj.name}", obj) for obj in (body, part)])
        bleed_hits.update(hits)
        if closest is not None:
            bleed_nearest.append(closest)

        scan = p1.sweep_scan(pivot, body, part, p1.MOTION[asset])
        measured = p1.measure(asset, root, body, pivot, part, scan)
        measured["pose_bounds"] = p1.pose_bounds(pivot, body, part,
                                                 p1.MOTION[asset], scan)
        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P5.fbx"
        d2.export_fbx(root, fbx)

        review.configure_scene()
        focus, radius, scale = p1.rig_for([body, part])
        images = {}
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Delivery_{asset}_{THEME}_P5_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))

        row = {
            "p5_fbx": str(fbx.relative_to(project_root)),
            "p5_fbx_sha256": m1.digest(fbx),
            "p5_fbx_bytes": fbx.stat().st_size,
            "objects": rows,
            "renderers": 2,
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "triangles_per_object": measured["triangles_per_object"],
            "non_manifold_edges": measured["non_manifold_edges"],
            "zero_area_faces": measured["zero_area_faces"],
            "rest_bounds_whd": measured["measured_width_height_depth"],
            "within_envelope": measured["within_envelope"],
            "mount_plane_max_y": measured["mount_plane_max_y"],
            "motion": measured["motion"],
            "runtime_motion_clearance": measured["runtime_motion_clearance"],
            "collider_union_unity":
                measured["pose_bounds"]["collider_union_unity"],
            "coplanar_overlap": audit,
            "images": images,
        }
        if asset == "MeterRound":
            row["needle_gate"] = p4d.needle_isolation_gate(
                body, pivot, part, focus, radius, scale, needle_dir,
                project_root)
        if asset == "Lever":
            row["grip_uv"] = grip_uv
            details = {}
            for deg in p5.LEVER_POSES:
                pivot.rotation_euler = (math.radians(deg), 0.0, 0.0)
                bpy.context.view_layer.update()
                tag = p5.LEVER_POSE_LABEL[deg]
                close = detail_dir / f"Detail_Lever_workpoint_{tag}_material.png"
                p1.shot((0.0, -0.050, -0.082), 0.170, (46.0, 10.0), 60.0,
                        0.085, close)
                details[f"workpoint_{tag}"] = str(
                    close.relative_to(project_root))
            pivot.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            grip = (0.0, p3.PIVOTS["Lever"][1][1] - 0.076,
                    p3.PIVOTS["Lever"][1][2] + 0.208)
            knurl = detail_dir / "Detail_Lever_knurl_normal.png"
            p1.shot(grip, 0.150, (34.0, 12.0), 125.0, 0.072, knurl)
            details["knurl_normal"] = str(knurl.relative_to(project_root))
            row["detail_images"] = details
        payload["assets"][asset] = row
        print(f"[Theme4DeliveryP5] {asset}: slots "
              f"{row['max_material_slots_per_object']}, clearance "
              f"{measured['runtime_motion_clearance']['clearance_mm']} mm")

    nearest = min(bleed_nearest) if bleed_nearest else None
    foreign = {label: count for label, count in bleed_hits.items()
               if count and label != "Lever:handle"}
    payload["knurl_bleed"] = {
        "loops_inside_knurl_region": bleed_hits,
        "objects_other_than_lever_handle_with_loops_inside": foreign,
        "nearest_foreign_uv_to_region_uv": round(nearest, 5)
        if nearest is not None else None,
        "nearest_foreign_uv_to_region_texels": round(nearest * d2.ATLAS, 1)
        if nearest is not None else None,
        "clean": not foreign,
    }

    rows = [(asset, [(label, project_root / row["images"][label])
                     for label in ("front", "oblique_left",
                                   "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    grey = tree / f"ContactSheet_Theme4_{THEME}_P5_grayscale.png"
    p1.comparison_sheet(rows, grey)
    colour = tree / f"ContactSheet_Theme4_{THEME}_P5_colour.png"
    tiles = [review.load_rgba(project_root / row["images"][label])
             for _, row in payload["assets"].items()
             for label in ("front", "oblique_left", "oblique_right", "side")]
    height, width = tiles[0].shape[:2]
    gap = 16
    canvas = np.zeros((3 * height + 2 * gap, 4 * width + 3 * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        r, c = divmod(index, 4)
        top = (2 - r) * (height + gap)
        canvas[top:top + height,
               c * (width + gap):c * (width + gap) + width] = tile
    review.save_rgba(canvas, colour)
    payload["contact_sheets"] = {
        "colour": {"path": str(colour.relative_to(project_root)),
                   "sha256": m1.digest(colour)},
        "grayscale": {"path": str(grey.relative_to(project_root)),
                      "sha256": m1.digest(grey)},
    }
    payload["shared_material_identities"] = sorted(
        {n for row in payload["assets"].values()
         for obj in row["objects"].values() for n in obj["material_slots"]})
    payload["max_material_slots_any_object"] = max(
        row["max_material_slots_per_object"]
        for row in payload["assets"].values())
    payload["needle_gate"] = payload["assets"]["MeterRound"]["needle_gate"]
    payload["status"] = (
        "p5_delivery_ready"
        if payload["max_material_slots_any_object"] <= 2
        and len(payload["shared_material_identities"]) <= 2
        and all(row["non_manifold_edges"] == 0 and row["zero_area_faces"] == 0
                for row in payload["assets"].values())
        and all(t <= 5000 for row in payload["assets"].values()
                for t in row["triangles_per_object"].values())
        and payload["needle_gate"]["all_poses_pass"]
        and payload["knurl_bleed"]["clean"]
        and knurl_stats["non_flat_texels_outside_block"] == 0
        else "p5_delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4DeliveryP5] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
