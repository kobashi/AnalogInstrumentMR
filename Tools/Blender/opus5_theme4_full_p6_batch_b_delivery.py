"""Theme 4 Phase 3 Batch B delivery: the frozen P4 atlas on Batch B geometry.

Alignment 295.1 / 298. The pilot atlas is reused unchanged and its SHA256 are
compared with delivery_p4's, so "frozen" is a measurement. No Batch B UV
island reaches the Lever's knurl patch, which the bleed audit reports as a
count rather than an assumption.

StatusIndicator's four states are rendered from one fixed camera by swapping
review-only materials onto `status_safe`, `status_warn` and `status_danger`
*after* the FBX is exported, so what ships still carries exactly the two
shared delivery materials.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_b_delivery.py -- \
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
import opus5_theme4_full_p6_batch_b as bb

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_b")
OUTPUT = f"{TREE}/theme4_full_p6_batch_b_delivery.json"

ROLE_RULES = (
    ("readout", ("tick_", "index_mark", "plate_label", "indicator_lens",
                 "status_")),
    ("gasket", ("gasket",)),
    ("metal", ("screw_", "bezel", "register", "plug_", "rib_", "well_",
               "hood", "button")),
)
# Every Batch B face lands in body / metal / gasket / readout; nothing is
# routed to the pilot's knurl region.


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

    def tagging_assign(obj, material):
        if not obj.data.materials:
            role = role_for(obj.name)
            tagged[obj.name.split(".")[0]] = role
            obj.data.materials.append(roles[role])

    p1.join = tagging_join
    p1.assign = tagging_assign
    try:
        body, mover, movers, audit = builder(roles["body"])
    finally:
        p1.join, p1.assign = original_join, original_assign
    for obj in (body, mover):
        obj.parent = root
    bpy.context.view_layer.update()
    return root, body, mover, movers, tagged, audit


def state_materials():
    """Review-only materials for the four StatusIndicator states."""
    made = {}
    for name, colour, emit in (
            ("state_off", (0.035, 0.037, 0.042, 1.0), 0.0),
            ("state_on", (0.300, 0.880, 0.950, 1.0), 2.2)):
        material = bpy.data.materials.new(f"REVIEW_{name}")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = colour
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = colour
                bsdf.inputs["Emission Strength"].default_value = emit
        made[name] = material
    return made


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    review_dir = tree / "review"
    detail_dir = tree / "detail"
    state_dir = tree / "state"
    for folder in (tree, review_dir, detail_dir, state_dir):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P6-BatchB-delivery",
        "note": ("Rotary, Button, Lamp, StatusIndicator through the frozen P4 "
                 "atlas. Batch A/R1, P1-P5, the existing themes and Batch C "
                 "are untouched."),
        "atlas_pixels": d2.ATLAS,
        "regions_uv": {role: list(box) for role, box in p4d.REGIONS.items()},
        "knurl_patch": knurl_stats,
        "new_atlas_region_required": False,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "budgets": {"triangle_budget_validator_total": bb.VALIDATOR_TOTAL,
                    "triangle_target_total": bb.TARGET_TOTAL,
                    "shared_material_budget": 2},
        "assets": {},
    }

    bleed_hits, bleed_nearest = {}, []
    for asset, builder in bb.BUILDERS_B.items():
        root, body, mover, movers, tagged, audit = build(asset, builder)
        meshes = [body] + list(movers)
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

        measured = bb.measure_asset(asset, root, body, mover, movers)
        statics = bb.snapshot_statics([body])
        clearance = bb.motion_clearance_audit(mover, movers, statics, asset)
        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6B.fbx"
        d2.export_fbx(root, fbx)

        review.configure_scene()
        focus, radius, scale = p1.rig_for(meshes)
        images = {}
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Delivery_{asset}_{THEME}_P6B_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        details = {}
        for value, label in bb.pose_set(asset):
            bb.apply_pose(mover, asset, value)
            path = detail_dir / f"Detail_{asset}_material_{label}.png"
            p1.shot(focus, radius * 0.55, (42.0, 14.0), 58.0, scale * 0.55,
                    path)
            details[f"motion_{label}"] = str(path.relative_to(project_root))
        bb.apply_pose(mover, asset, 0.0)

        submeshes = sum(r["submeshes"] for r in rows.values())
        row = dict(measured)
        row.update({
            "p6b_fbx": str(fbx.relative_to(project_root)),
            "p6b_fbx_sha256": m1.digest(fbx),
            "p6b_fbx_bytes": fbx.stat().st_size,
            "objects": rows,
            "submeshes_total": submeshes,
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "coplanar_overlap": audit,
            "clearance": clearance,
            "images": images,
            "detail_images": details,
        })

        if asset == "StatusIndicator":
            # After export: the shipped FBX keeps the two delivery materials.
            palette = state_materials()
            saved = {obj.name: [s.material for s in obj.material_slots]
                     for obj in movers}
            states = {}
            for index, state in enumerate(("OFF", "SAFE", "WARN", "DANGER")):
                for position, obj in enumerate(movers):
                    lit = index > 0 and position == index - 1
                    obj.data.materials.clear()
                    obj.data.materials.append(
                        palette["state_on" if lit else "state_off"])
                bpy.context.view_layer.update()
                path = state_dir / f"State_{asset}_{state}.png"
                p1.shot(focus, radius, (0.0, 0.0), 52.0, scale, path)
                states[state] = str(path.relative_to(project_root))
            for obj in movers:
                obj.data.materials.clear()
                for material in saved[obj.name]:
                    obj.data.materials.append(material)
            row["state_images"] = states
            row["state_render_note"] = (
                "review-only materials applied after export; the FBX carries "
                "the two delivery materials only")

        payload["assets"][asset] = row
        print(f"[BatchBDelivery] {asset}: tris {row['triangles_total']}, "
              f"renderers {row['renderers']}/{row['renderer_budget']}, "
              f"submeshes {submeshes}, slots "
              f"{row['max_material_slots_per_object']}, clearance "
              f"{clearance['clean']} min {clearance['min_clearance_mm']}")

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
    grey = tree / f"ContactSheet_Theme4_{THEME}_P6B_grayscale.png"
    p1.comparison_sheet(rows, grey)
    colour = tree / f"ContactSheet_Theme4_{THEME}_P6B_colour.png"
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
    payload["status"] = (
        "p6_batch_b_delivery_ready"
        if all(row["max_material_slots_per_object"] <= 2
               for row in payload["assets"].values())
        and len(payload["shared_material_identities"]) <= 2
        and all(all(row["gates"].values())
                for row in payload["assets"].values())
        and all(row["clearance"]["clean"]
                for row in payload["assets"].values())
        and payload["knurl_bleed"]["clean"]
        else "p6_batch_b_delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchBDelivery] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
