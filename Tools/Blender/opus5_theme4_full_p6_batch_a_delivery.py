"""Theme 4 Phase 3 Batch A delivery: P4's atlas, unchanged, on new geometry.

Alignment 295.2 items 7, 8 and 10. The pilot's atlas is frozen, so it is
reused rather than re-authored: the four maps are written by the P4 builder
under P4's names and their SHA256 are compared with delivery_p4's, which makes
"unchanged" a measurement.

Batch A needs no new atlas region. The knurl patch in the body quadrant is
calibrated to the pilot Lever's grip circumference and arm axis; putting a
differently sized grip through it would scale the pattern wrongly, and a new
region would mean editing a frozen atlas. Every Batch A face therefore packs
into body, metal, gasket or readout, and the bleed audit reports zero loops in
the knurl region as a positive result rather than an accident.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_delivery.py -- \
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
import opus5_theme4_delivery_p4 as p4d
import opus5_theme4_material_p2 as m2
import opus5_theme4_full_p6_batch_a as ba

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a")
OUTPUT = f"{TREE}/theme4_full_p6_batch_a_delivery.json"

# P4's rules plus Batch A's part names. No "knurl" entry: see the module note.
ROLE_RULES = (
    ("readout", ("tick_", "index_", "needle_", "plate_label")),
    ("gasket", ("gasket",)),
    ("metal", ("screw_", "cover_screw_", "blank", "plug_", "plug", "mount_",
               "access_", "collar", "cam_", "gland_", "boss_", "stop_",
               "end_stop", "detent_", "rim_", "pillow_", "rail",
               "handle_hub", "handle_yoke", "handle_pin", "handle_collar",
               "handle_roller", "switch_hub", "switch_axle", "switch_collar",
               "slider_bearing", "slider_pin", "slider_jaw", "register")),
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def role_for(name):
    stem = name.split(".")[0]
    for role, prefixes in ROLE_RULES:
        for prefix in prefixes:
            if stem.startswith(prefix) or prefix in stem:
                return role
    return "body"


def build(asset, builder):
    p1.clear_scene()
    review.configure_scene()
    roles = m2.make_materials()
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    original_join, original_assign = p1.join, p1.assign
    tagged = {}

    def tagging_join(target, others):
        for obj in [target] + list(others):
            role = role_for(obj.name)
            tagged[obj.name.split(".")[0]] = role
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
        "phase": "Theme4-P6-BatchA-delivery",
        "note": ("P4's atlas and region layout, unchanged, on Batch A "
                 "geometry. No knurl region is used; see knurl_bleed."),
        "atlas_pixels": d2.ATLAS,
        "regions_uv": {role: list(box) for role, box in p4d.REGIONS.items()},
        "region_inset_uv": p4d.INSET,
        "surface": d2.SURFACE,
        "knurl_patch": knurl_stats,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "assets": {},
    }

    bleed_hits, bleed_nearest = {}, []
    for asset, builder in ba.BUILDERS_A.items():
        root, body, mover, moving, tagged, audit = build(asset, builder)
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
        bleed_hits.update(hits)
        if closest is not None:
            bleed_nearest.append(closest)

        measured = ba.measure_asset(asset, root, body, mover, moving)
        clearance = ba.motion_clearance_audit(mover, moving, asset)
        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6A.fbx"
        d2.export_fbx(root, fbx)

        review.configure_scene()
        focus, radius, scale = p1.rig_for([body, moving])
        images = {}
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Delivery_{asset}_{THEME}_P6A_{label}.png"
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

        row = dict(measured)
        row.update({
            "p6a_fbx": str(fbx.relative_to(project_root)),
            "p6a_fbx_sha256": m1.digest(fbx),
            "p6a_fbx_bytes": fbx.stat().st_size,
            "objects": rows,
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "coplanar_overlap": audit,
            "clearance": clearance,
            "images": images,
            "detail_images": details,
        })
        payload["assets"][asset] = row
        print(f"[BatchADelivery] {asset}: slots "
              f"{row['max_material_slots_per_object']}, tris "
              f"{row['triangles_total']}, clearance clean "
              f"{clearance['clean']} min {clearance['min_clearance_mm']} mm")

    nearest = min(bleed_nearest) if bleed_nearest else None
    foreign = {label: count for label, count in bleed_hits.items() if count}
    payload["knurl_bleed"] = {
        "loops_inside_knurl_region": bleed_hits,
        "objects_with_loops_inside": foreign,
        "nearest_uv_to_region_uv": round(nearest, 5)
        if nearest is not None else None,
        "nearest_uv_to_region_texels": round(nearest * d2.ATLAS, 1)
        if nearest is not None else None,
        "clean": not foreign,
        "note": ("Batch A uses no knurl region; zero loops inside it is the "
                 "expected result, and the margin says how far away the "
                 "nearest Batch A UV is"),
    }

    rows = [(asset, [(label, project_root / row["images"][label])
                     for label in ("front", "oblique_left",
                                   "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    grey = tree / f"ContactSheet_Theme4_{THEME}_P6A_grayscale.png"
    p1.comparison_sheet(rows, grey)
    colour = tree / f"ContactSheet_Theme4_{THEME}_P6A_colour.png"
    tiles = [review.load_rgba(project_root / row["images"][label])
             for _, row in payload["assets"].items()
             for label in ("front", "oblique_left", "oblique_right", "side")]
    height, width = tiles[0].shape[:2]
    gap = 16
    canvas = np.zeros((4 * height + 3 * gap, 4 * width + 3 * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        r, c = divmod(index, 4)
        top = (3 - r) * (height + gap)
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
    payload["status"] = (
        "p6_batch_a_delivery_ready"
        if payload["max_material_slots_any_object"] <= 2
        and len(payload["shared_material_identities"]) <= 2
        and all(row["non_manifold_edges"] == 0 and row["zero_area_faces"] == 0
                for row in payload["assets"].values())
        and all(all(row["gates"].values())
                for row in payload["assets"].values())
        and all(row["clearance"]["clean"]
                for row in payload["assets"].values())
        and payload["knurl_bleed"]["clean"]
        else "p6_batch_a_delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchADelivery] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
