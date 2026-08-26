"""Theme 4 P3 delivery: same atlas contract as P2, on the revised geometry.

Alignment 281.2's quadrant layout and channel packing are unchanged - body
top-left, metal top-right, gasket bottom-left, readout bottom-right, metallic
in R and smoothness in A - so nothing downstream has to learn a new convention.
Only the shapes moved.

Role assignment gains the P3 part names: the lathed housing, the hub, yoke
cheeks and collar that now make the lever's joint visible, and the revolved
toggle head. The P2 scripts and delivery_p2/ are untouched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_delivery_p3.py -- \
      --project-root "$PWD"
"""

import argparse
import json
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
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_material_p2 as m2

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p3"
OUTPUT = f"{TREE}/theme4_delivery_p3.json"

# P3 part names added to the P2 rules. Everything unmatched is body.
ROLE_RULES = (
    ("readout", ("tick_", "index_", "needle_", "plate_label")),
    ("gasket", ("gasket",)),
    ("metal", ("screw_", "cover_screw_", "blank", "plug_", "mount_", "access_",
               "collar", "cam_", "gland_", "boss_", "stop_", "detent_",
               "rim_", "pillow_", "handle_hub", "handle_yoke",
               "handle_collar", "handle_roller", "switch_hub")),
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
    materials = m2.make_materials()
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    original_join, original_assign = p1.join, p1.assign
    tagged = {}

    def tagging_join(target, others):
        for obj in [target] + list(others):
            role = role_for(obj.name)
            tagged[obj.name.split(".")[0]] = role
            obj.data.materials.clear()
            obj.data.materials.append(materials[role])
        return original_join(target, others)

    p1.join = tagging_join
    p1.assign = lambda obj, material: None
    try:
        body, pivot, part, audit = builder(materials["body"])
    finally:
        p1.join, p1.assign = original_join, original_assign
    for obj in (body, pivot):
        obj.parent = root
    bpy.context.view_layer.update()
    return root, body, pivot, part, tagged, audit


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    review_dir = tree / "review"
    for folder in (tree, review_dir):
        folder.mkdir(parents=True, exist_ok=True)
    textures = d2.build_textures(tree)

    payload = {
        "phase": "Theme4-P3-delivery",
        "note": ("P3 geometry through the P2 atlas contract. Quadrants, "
                 "channels and the two delivery materials are unchanged."),
        "atlas_pixels": d2.ATLAS,
        "quadrants": {role: {"column_row": list(cell),
                             "uv_range": d2.quadrant_uv_range(role)}
                      for role, cell in d2.QUADRANTS.items()},
        "quadrant_inset_uv": d2.QUADRANT_INSET,
        "surface": d2.SURFACE,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "assets": {},
    }

    for asset, builder in p3.BUILDERS_P3.items():
        root, body, pivot, part, tagged, audit = build(asset, builder)
        for obj in (body, part):
            m2.unwrap(obj)
        atlas, emissive = d2.delivery_materials(textures)
        rows = {}
        for obj in (body, part):
            role_of_slot = [slot.material.name.rsplit("_", 1)[-1].lower()
                            for slot in obj.material_slots]
            counts, used = d2.pack_into_quadrants(obj, role_of_slot,
                                                  atlas, emissive)
            rows[obj.name] = {
                "role_face_counts": counts,
                "material_slots": [s.material.name for s in obj.material_slots],
                "submeshes": len(used),
            }
        bpy.context.view_layer.update()

        scan = p1.sweep_scan(pivot, body, part, p1.MOTION[asset])
        measured = p1.measure(asset, root, body, pivot, part, scan)
        measured["pose_bounds"] = p1.pose_bounds(pivot, body, part,
                                                 p1.MOTION[asset], scan)
        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P3.fbx"
        d2.export_fbx(root, fbx)

        review.configure_scene()
        focus, radius, scale = p1.rig_for([body, part])
        images = {}
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Delivery_{asset}_{THEME}_P3_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))

        payload["assets"][asset] = {
            "p3_fbx": str(fbx.relative_to(project_root)),
            "p3_fbx_sha256": m1.digest(fbx),
            "p3_fbx_bytes": fbx.stat().st_size,
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
        print(f"[Theme4DeliveryP3] {asset}: slots "
              f"{payload['assets'][asset]['max_material_slots_per_object']}, "
              f"clearance "
              f"{measured['runtime_motion_clearance']['clearance_mm']} mm")

    rows = [(asset, [(label, project_root / row["images"][label])
                     for label in ("front", "oblique_left",
                                   "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    grey = tree / f"ContactSheet_Theme4_{THEME}_P3_grayscale.png"
    p1.comparison_sheet(rows, grey)
    colour = tree / f"ContactSheet_Theme4_{THEME}_P3_colour.png"
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
    payload["status"] = (
        "p3_delivery_ready"
        if payload["max_material_slots_any_object"] <= 2
        and len(payload["shared_material_identities"]) <= 2
        and all(row["non_manifold_edges"] == 0 and row["zero_area_faces"] == 0
                for row in payload["assets"].values())
        else "p3_delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4DeliveryP3] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
