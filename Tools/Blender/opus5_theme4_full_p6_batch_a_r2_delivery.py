"""Batch A R2 delivery: the two revised controls through the frozen P4 atlas.

Alignment 301. Geometry only changed; the atlas, region layout, packing and
materials are P4's and are compared byte for byte. The separate production
atlas proposal lives in its own script and its own folder and does not touch
anything here.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r2_delivery.py -- \
      --project-root "$PWD"
"""

import argparse
import json
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
import opus5_theme4_delivery_p4 as p4d
import opus5_theme4_material_p2 as m2
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_delivery as bad
import opus5_theme4_full_p6_batch_a_r2 as r2

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r2")
OUTPUT = f"{TREE}/theme4_full_p6_batch_a_r2_delivery.json"


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

    payload = {
        "phase": "Theme4-P6-BatchA-R2-delivery",
        "note": ("Throttle and PowerSlider with driver access, through the "
                 "frozen P4 atlas. MeterMedium, MeterLarge, Batch B and "
                 "P1-P5 are untouched."),
        "atlas_pixels": d2.ATLAS,
        "regions_uv": {role: list(box) for role, box in p4d.REGIONS.items()},
        "knurl_patch": knurl_stats,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "budgets": {"triangle_budget_validator_total": r2.VALIDATOR_TOTAL,
                    "triangle_target_total": r2.TARGET_TOTAL},
        "assets": {},
    }

    bleed_hits, bleed_nearest = {}, []
    for asset, builder in r2.BUILDERS_R2.items():
        root, body, mover, moving, tagged, audit = bad.build(asset, builder)
        movers = list(moving) if isinstance(moving, (list, tuple)) else [moving]
        meshes = [body] + movers
        for obj in meshes:
            m2.unwrap(obj)
        atlas, emissive = p4d.delivery_materials_p4(textures)
        rows = {}
        for obj in meshes:
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
            [(f"{asset}:{obj.name}", obj) for obj in meshes])
        bleed_hits.update(hits)
        if closest is not None:
            bleed_nearest.append(closest)

        measured = ba.measure_asset(asset, root, body, mover, movers[0])
        measured["triangle_budget_total"] = r2.VALIDATOR_TOTAL
        measured["triangle_target_total"] = r2.TARGET_TOTAL
        measured["gates"]["triangles_total"] = (
            measured["triangles_total"] <= r2.VALIDATOR_TOTAL)
        measured["gates"]["triangles_target"] = (
            measured["triangles_total"] <= r2.TARGET_TOTAL)
        clearance = ba.motion_clearance_audit(mover, movers[0], asset)
        screws = {k: tuple(v) for k, v in audit["screws"].items()}
        face, base = audit["tool_access_planes"]
        access = r2.tool_path_audit(body, screws, face, base)
        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6A_R2.fbx"
        d2.export_fbx(root, fbx)

        review.configure_scene()
        focus, radius, scale = p1.rig_for(meshes)
        images = {}
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Delivery_{asset}_{THEME}_P6A_R2_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        details = {}
        for value, label in ba.pose_set(asset):
            ba.apply_pose(mover, asset, value)
            path = detail_dir / f"Detail_{asset}_material_{label}.png"
            p1.shot(focus, radius * 0.52, (44.0, 12.0), 60.0, scale * 0.52,
                    path)
            details[f"motion_{label}"] = str(path.relative_to(project_root))
        ba.apply_pose(mover, asset, 0.0)
        details.update(r2.tool_access_images(asset, screws, face, base,
                                             detail_dir, project_root))

        submeshes = sum(r["submeshes"] for r in rows.values())
        row = dict(measured)
        row.update({
            "p6a_r2_fbx": str(fbx.relative_to(project_root)),
            "p6a_r2_fbx_sha256": m1.digest(fbx),
            "p6a_r2_fbx_bytes": fbx.stat().st_size,
            "objects": rows,
            "submeshes_total": submeshes,
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "coplanar_overlap": audit,
            "clearance": clearance,
            "tool_access": access,
            "images": images,
            "detail_images": details,
        })
        row["gates"]["clearance_clean"] = clearance["clean"]
        row["gates"]["tool_paths_open"] = access["all_open"]
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        print(f"[BatchA-R2-Delivery] {asset}: tris {row['triangles_total']}, "
              f"renderers {row['renderers']}, submeshes {submeshes}, slots "
              f"{row['max_material_slots_per_object']}, bore "
              f"{access['min_clear_diameter_mm']} mm, clearance "
              f"{clearance['clean']}")

    nearest = min(bleed_nearest) if bleed_nearest else None
    foreign = {label: count for label, count in bleed_hits.items() if count}
    payload["knurl_bleed"] = {
        "loops_inside_knurl_region": bleed_hits,
        "objects_with_loops_inside": foreign,
        "nearest_uv_to_region_texels": round(nearest * d2.ATLAS, 1)
        if nearest is not None else None,
        "clean": not foreign,
    }

    rows = [(asset, [(label, project_root / row["images"][label])
                     for label in ("front", "oblique_left",
                                   "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    grey = tree / f"ContactSheet_Theme4_{THEME}_P6A_R2_grayscale.png"
    p1.comparison_sheet(rows, grey)
    colour = tree / f"ContactSheet_Theme4_{THEME}_P6A_R2_colour.png"
    tiles = [review.load_rgba(project_root / row["images"][label])
             for _, row in payload["assets"].items()
             for label in ("front", "oblique_left", "oblique_right", "side")]
    height, width = tiles[0].shape[:2]
    gap = 16
    canvas = np.zeros((2 * height + gap, 4 * width + 3 * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        r, c = divmod(index, 4)
        top = (1 - r) * (height + gap)
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
    payload["status"] = (
        "p6_batch_a_r2_delivery_ready"
        if all(row["all_gates_passed"] for row in payload["assets"].values())
        and len(payload["shared_material_identities"]) <= 2
        and payload["knurl_bleed"]["clean"]
        else "p6_batch_a_r2_delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchA-R2-Delivery] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
