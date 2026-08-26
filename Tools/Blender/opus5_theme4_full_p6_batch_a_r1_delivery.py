"""Batch A R1 delivery: the reduced Throttle through the frozen P4 atlas.

Alignment 296 / Gate B. Only the Throttle is rebuilt. The atlas, region
layout, packing and material wiring are Batch A's, which are P4's, so the four
maps are written by the P4 builder under P4's names and their SHA256 can be
compared with delivery_p4's directly.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r1_delivery.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_delivery_p4 as p4d
import opus5_theme4_material_p2 as m2
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_delivery as bad
import opus5_theme4_full_p6_batch_a_r1 as r1

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r1")
OUTPUT = f"{TREE}/theme4_full_p6_batch_a_r1_delivery.json"


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
    detail_dir = tree / "detail"
    for folder in (tree, review_dir, detail_dir):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    asset = "Throttle"
    root, body, mover, moving, tagged, audit = bad.build(
        asset, r1.build_throttle)
    for obj in (body, moving):
        m2.unwrap(obj)
    atlas, emissive = p4d.delivery_materials_p4(textures)
    rows = {}
    for obj in (body, moving):
        role_of_slot = [slot.material.name.rsplit("_", 1)[-1].lower()
                        for slot in obj.material_slots]
        counts, used = p4d.pack_into_regions(obj, role_of_slot,
                                             atlas, emissive)
        rows[obj.name] = {
            "role_face_counts": counts,
            "material_slots": [s.material.name for s in obj.material_slots],
            "submeshes": len(used),
        }
    bpy.context.view_layer.update()
    hits, closest = p4d.knurl_bleed_audit(
        [(f"{asset}:{obj.name}", obj) for obj in (body, moving)])

    measured = r1.measure_throttle(root, body, mover, moving)
    clearance = ba.motion_clearance_audit(mover, moving, asset)
    fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6A_R1.fbx"
    d2.export_fbx(root, fbx)

    review.configure_scene()
    focus, radius, scale = p1.rig_for([body, moving])
    images = {}
    for label, view in p1.VIEWS.items():
        path = review_dir / f"Delivery_{asset}_{THEME}_P6A_R1_{label}.png"
        p1.shot(focus, radius, view, 52.0, scale, path)
        images[label] = str(path.relative_to(project_root))
    details = {}
    for value, label in ba.pose_set(asset):
        ba.apply_pose(mover, asset, value)
        path = detail_dir / f"Detail_{asset}_material_{label}.png"
        p1.shot(focus, radius * 0.52, (44.0, 12.0), 60.0, scale * 0.52, path)
        details[f"motion_{label}"] = str(path.relative_to(project_root))
    ba.apply_pose(mover, asset, 0.0)

    submeshes = sum(r["submeshes"] for r in rows.values())
    row = dict(measured)
    row.update({
        "p6a_r1_fbx": str(fbx.relative_to(project_root)),
        "p6a_r1_fbx_sha256": m1.digest(fbx),
        "p6a_r1_fbx_bytes": fbx.stat().st_size,
        "objects": rows,
        "submeshes_total": submeshes,
        "max_material_slots_per_object": max(
            len(r["material_slots"]) for r in rows.values()),
        "coplanar_overlap": audit,
        "clearance": clearance,
        "images": images,
        "detail_images": details,
    })

    payload = {
        "phase": "Theme4-P6-BatchA-R1-delivery",
        "note": ("Throttle only, through the frozen P4 atlas. Batch A's other "
                 "three assets and P1-P5 are untouched."),
        "atlas_pixels": d2.ATLAS,
        "regions_uv": {role: list(box) for role, box in p4d.REGIONS.items()},
        "knurl_patch": knurl_stats,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "knurl_bleed": {
            "loops_inside_knurl_region": hits,
            "clean": not any(hits.values()),
            "nearest_uv_to_region_texels": round(closest * d2.ATLAS, 1)
            if closest is not None else None,
        },
        "budgets": {
            "triangle_budget_validator_total": r1.THROTTLE_BUDGET_TOTAL,
            "triangle_target_total": r1.TARGET_TOTAL,
            "renderer_budget": ba.CONTRACT["Throttle"]["renderer_budget"],
            "submesh_expected": 3,
            "shared_material_budget": 2,
        },
        "assets": {asset: row},
    }
    payload["shared_material_identities"] = sorted(
        {n for obj in rows.values() for n in obj["material_slots"]})
    payload["status"] = (
        "p6_batch_a_r1_delivery_ready"
        if row["triangles_total"] <= r1.TARGET_TOTAL
        and row["max_material_slots_per_object"] <= 2
        and len(payload["shared_material_identities"]) <= 2
        and submeshes == 3
        and row["renderers"] == 2
        and row["non_manifold_edges"] == 0
        and row["zero_area_faces"] == 0
        and all(row["gates"].values())
        and clearance["clean"]
        and payload["knurl_bleed"]["clean"]
        else "p6_batch_a_r1_delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchA-R1-Delivery] tris {row['triangles_total']}, renderers "
          f"{row['renderers']}, submeshes {submeshes}, slots "
          f"{row['max_material_slots_per_object']}, clearance "
          f"{clearance['clean']} min {clearance['min_clearance_mm']} mm")
    print(f"[BatchA-R1-Delivery] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
