"""Theme 4 Phase 3 Batch B R1 delivery: the 311 guard fix, with the proof.

Every asset is built twice in this run - Batch B's frozen builder and R1's -
through the same material pipeline and rendered from the same camera frame,
which is derived once from the Batch B build and then reused. That is what
makes the before/after pairs and the silhouette overlays comparable rather
than merely adjacent.

Writes only to delivery_p6/batch_b_r1/**. delivery_p6/batch_b/** is read for
nothing but its builders; Batch A, Batch C, the three existing themes,
Assets/, Builds/, docs/ and git are untouched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_b_r1_delivery.py -- \
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
import opus5_theme4_full_p6_batch_b_r1 as r1

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_b_r1")
OUTPUT = f"{TREE}/theme4_full_p6_batch_b_r1.json"
FROZEN = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
          "delivery_p6/batch_b")

ROLE_RULES = (
    ("readout", ("tick_", "index_mark", "plate_label", "indicator_lens",
                 "status_")),
    ("gasket", ("gasket",)),
    ("metal", ("screw_", "bezel", "register", "plug_", "rib_", "well_",
               "hood", "button")),
)
GRID = 640

# The whole-instrument silhouette barely moves - the plate dominates it - so
# the overlay that carries the 311 signal is scoped to the guard and to the
# thing it guards.
GUARD_PARTS = {
    "Rotary": ("housing",),
    "Button": ("bezel",),
    "Lamp": ("bezel", "hood"),
    "StatusIndicator": ("well_safe", "well_warn", "well_danger", "rib_0",
                        "rib_1", "hood"),
}
FOCUS_VIEWS = {"front": (0.0, 0.0), "side": (78.0, 6.0),
               "oblique_right": (38.0, 18.0)}


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
    """Batch B's delivery build path, with the parts captured on the way in."""
    p1.clear_scene()
    review.configure_scene()
    roles = m2.make_materials()
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    original_join, original_assign = p1.join, p1.assign
    tagged, captured = {}, {}

    def tagging_join(target, others):
        for obj in [target] + list(others):
            stem = obj.name.split(".")[0]
            captured.setdefault(stem, []).append(r1.world_triangles(obj))
            role = role_for(obj.name)
            tagged[stem] = role
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
    parts = {name: np.concatenate(rows) for name, rows in captured.items()}
    return root, body, mover, movers, tagged, audit, parts


def dress(meshes, textures):
    """Unwrap onto the frozen P4 atlas and report the per-object packing."""
    for obj in meshes:
        m2.unwrap(obj)
    atlas, emissive = p4d.delivery_materials_p4(textures)
    rows = {}
    for obj in meshes:
        role_of_slot = [slot.material.name.rsplit("_", 1)[-1].lower()
                        for slot in obj.material_slots]
        counts, used = p4d.pack_into_regions(obj, role_of_slot, atlas,
                                             emissive)
        rows[obj.name] = {
            "role_face_counts": counts,
            "material_slots": [s.material.name for s in obj.material_slots],
            "submeshes": len(used),
        }
    bpy.context.view_layer.update()
    return rows


def render_views(meshes, focus, radius, scale, out_dir, prefix, project_root):
    images = {}
    for label, view in p1.VIEWS.items():
        path = out_dir / f"{prefix}_{label}.png"
        p1.shot(focus, radius, view, 52.0, scale, path)
        images[label] = str(path.relative_to(project_root))
    return images


def group_masks(parts, movers, asset, focus, half_extent):
    """Guard-only and subject-only masks, for the scoped overlays."""
    guard = np.concatenate([parts[name] for name in GUARD_PARTS[asset]
                            if name in parts])
    subject = np.concatenate([r1.world_triangles(obj) for obj in movers])
    out = {}
    for label, view in FOCUS_VIEWS.items():
        out[f"guard_{label}"] = r1.silhouette_mask(guard, view, focus,
                                                   half_extent, GRID)
        out[f"subject_{label}"] = r1.silhouette_mask(subject, view, focus,
                                                     half_extent, GRID)
    return out


def masks_for(meshes, focus, half_extent):
    tris = np.concatenate([r1.world_triangles(obj) for obj in meshes])
    return {label: r1.silhouette_mask(tris, view, focus, half_extent, GRID)
            for label, view in p1.VIEWS.items()}


def proxy_sphere(name, centre, radius, colour):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=centre,
                                         segments=32, ring_count=16)
    obj = bpy.context.object
    obj.name = name
    material = bpy.data.materials.new(f"REVIEW_{name}")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = colour
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = colour
            bsdf.inputs["Emission Strength"].default_value = 0.9
    obj.data.materials.append(material)
    return obj


PROXY_COLOUR = (0.95, 0.42, 0.10, 1.0)


def rotary_proxy_images(finger, focus, radius, scale, out_dir, prefix,
                        project_root):
    spheres = [proxy_sphere(f"finger_{label}",
                            row["proxy_centre_m"], r1.FINGER_RADIUS,
                            PROXY_COLOUR)
               for label, row in finger["sides"].items()]
    bpy.context.view_layer.update()
    images = {}
    for label, view in (("front", (0.0, 0.0)), ("oblique", (34.0, 20.0)),
                        ("top", (0.0, 62.0))):
        path = out_dir / f"{prefix}_proxy_{label}.png"
        p1.shot(focus, radius, view, 52.0, scale, path)
        images[f"proxy_{label}"] = str(path.relative_to(project_root))
    for obj in spheres:
        bpy.data.objects.remove(obj, do_unlink=True)
    return images


def button_proxy_images(finger, travel, focus, radius, scale, out_dir, prefix,
                        project_root):
    images = {}
    for label, value in (("rest", 0.0), ("pressed", bb.BUTTON_TRAVEL)):
        bb.apply_pose(travel, "Button", value)
        bpy.context.view_layer.update()
        sphere = proxy_sphere(f"finger_{label}",
                              finger["poses"][label]["proxy_centre_m"],
                              r1.FINGER_RADIUS, PROXY_COLOUR)
        bpy.context.view_layer.update()
        for view_label, view in (("side", (78.0, 4.0)), ("oblique", (34.0, 20.0))):
            path = out_dir / f"{prefix}_proxy_{label}_{view_label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[f"proxy_{label}_{view_label}"] = str(
                path.relative_to(project_root))
        bpy.data.objects.remove(sphere, do_unlink=True)
    bb.apply_pose(travel, "Button", 0.0)
    bpy.context.view_layer.update()
    return images


def run_audits(asset, body, mover, movers, parts, focus, half_extent,
               variant):
    """The 311 shape audits, run identically on Batch B and on R1."""
    if asset == "Rotary":
        collar = (r1.ROTARY_COLLAR_Y_B if variant == "batch_b"
                  else r1.ROTARY_COLLAR_Y)
        return {"finger_proxy": r1.rotary_finger_audit(body, movers[0],
                                                       collar_y=collar)}
    if asset == "Button":
        guard = (r1.BUTTON_GUARD_Y_B if variant == "batch_b"
                 else r1.BUTTON_GUARD_Y)
        return {"finger_proxy": r1.button_finger_audit(body, movers[0], mover,
                                                       guard_y=guard)}
    if asset == "Lamp":
        lens_r = 0.0300 if variant == "batch_b" else r1.LAMP_LENS_R
        return {"lens_proportion": r1.lamp_proportion_audit(
            parts, movers[0], focus, half_extent, GRID,
            lens_radius=lens_r, bezel_radius=0.0470)}
    return {"alignment": r1.status_alignment_audit(parts, movers, focus,
                                                   half_extent, GRID)}


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in
            ("review", "before", "proxy", "overlay", "state", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P6-BatchB-R1",
        "alignment": "311",
        "note": ("Guard geometry only. Pivot, motion axis and range, mount "
                 "plane, envelope and the frozen P4 atlas are Batch B's. "
                 "delivery_p6/batch_b is frozen and was read for its builders "
                 "alone."),
        "frozen_tree": FROZEN,
        "changes": {
            "Rotary": ("collar front y -0.0864 -> -0.0620; the knob crown "
                       "goes from 3.6 mm inside the collar to 20.8 mm proud"),
            "Button": ("guard front y -0.0620 -> -0.0524; the guard drops "
                       "from 19.0 to 9.4 mm proud of the bezel face"),
            "Lamp": ("lens radius 0.0300 -> 0.0376 with the bezel bore and "
                     "lip out to match; hood 118 -> 96 deg and inside the "
                     "bezel's outer radius"),
            "StatusIndicator": ("three wells to one size on a symmetric "
                                "spacing; hood 0.1550 -> 0.1620 so it covers "
                                "all three"),
        },
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
        "finger_proxy_diameter_mm": r1.FINGER_DIAMETER * 1000.0,
        "assets": {},
    }

    bleed_hits, bleed_nearest = {}, []
    for asset in bb.BUILDERS_B:
        # --- before: Batch B, same materials, and the camera frame is fixed
        # here so both halves of every pair share it.
        root, body, mover, movers, _, _, parts = build(
            asset, bb.BUILDERS_B[asset])
        meshes = [body] + list(movers)
        dress(meshes, textures)
        focus, radius, scale = p1.rig_for(meshes)
        half_extent = radius * 0.34
        before_measured = bb.measure_asset(asset, root, body, mover, movers)
        before_audits = run_audits(asset, body, mover, movers, parts, focus,
                                   half_extent, "batch_b")
        before_images = render_views(meshes, focus, radius, scale,
                                     dirs["before"], f"Before_{asset}",
                                     project_root)
        before_masks = masks_for(meshes, focus, half_extent)
        before_groups = group_masks(parts, movers, asset, focus, half_extent)

        # --- after: R1
        root, body, mover, movers, tagged, audit, parts = build(
            asset, r1.BUILDERS_B1[asset])
        meshes = [body] + list(movers)
        rows = dress(meshes, textures)
        hits, closest = p4d.knurl_bleed_audit(
            [(f"{asset}:{obj.name}", obj) for obj in meshes])
        bleed_hits.update(hits)
        if closest is not None:
            bleed_nearest.append(closest)
        measured = bb.measure_asset(asset, root, body, mover, movers)
        statics = bb.snapshot_statics([body])
        clearance = bb.motion_clearance_audit(mover, movers, statics, asset)
        after_audits = run_audits(asset, body, mover, movers, parts, focus,
                                  half_extent, "r1")

        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6B_R1.fbx"
        d2.export_fbx(root, fbx)
        blend = dirs["blend"] / f"{asset}_{THEME}_P6B_R1.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)

        review.configure_scene()
        images = render_views(meshes, focus, radius, scale, dirs["review"],
                              f"R1_{asset}", project_root)
        after_masks = masks_for(meshes, focus, half_extent)
        after_groups = group_masks(parts, movers, asset, focus, half_extent)
        overlays = {}
        for label in p1.VIEWS:
            path = dirs["overlay"] / f"Overlay_{asset}_{label}.png"
            r1.save_overlay(before_masks[label], after_masks[label], path)
            overlays[label] = str(path.relative_to(project_root))
        for label in after_groups:
            path = dirs["overlay"] / f"Overlay_{asset}_{label}.png"
            r1.save_overlay(before_groups[label], after_groups[label], path)
            overlays[label] = str(path.relative_to(project_root))

        proxies = {}
        if asset == "Rotary":
            proxies = rotary_proxy_images(
                after_audits["finger_proxy"], focus, radius, scale,
                dirs["proxy"], f"R1_{asset}", project_root)
        elif asset == "Button":
            proxies = button_proxy_images(
                after_audits["finger_proxy"], mover, focus, radius, scale,
                dirs["proxy"], f"R1_{asset}", project_root)

        details = {}
        for value, label in bb.pose_set(asset):
            bb.apply_pose(mover, asset, value)
            path = dirs["proxy"] / f"Motion_{asset}_{label}.png"
            p1.shot(focus, radius * 0.62, (42.0, 14.0), 58.0, scale * 0.62,
                    path)
            details[f"motion_{label}"] = str(path.relative_to(project_root))
        bb.apply_pose(mover, asset, 0.0)
        bpy.context.view_layer.update()

        submeshes = sum(r["submeshes"] for r in rows.values())
        row = dict(measured)
        row.update({
            "r1_fbx": str(fbx.relative_to(project_root)),
            "r1_fbx_sha256": m1.digest(fbx),
            "r1_fbx_bytes": fbx.stat().st_size,
            "r1_blend": str(blend.relative_to(project_root)),
            "objects": rows,
            "submeshes_total": submeshes,
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "coplanar_overlap": audit,
            "clearance": clearance,
            "images": images,
            "before_images": before_images,
            "overlay_images": overlays,
            "overlay_legend": ("Batch B only in red, R1 only in green, both "
                               "in grey; `guard_*` is the guard or well "
                               "frame alone and `subject_*` is the knob, cap, "
                               "lens or lenses alone, same camera as the "
                               "matching render"),
            "proxy_images": proxies,
            "motion_images": details,
            "shape_audit_r1": after_audits,
            "shape_audit_batch_b": before_audits,
            "batch_b_reference": {
                "triangles_total": before_measured["triangles_total"],
                "renderers": before_measured["renderers"],
                "bounds_size_unity": before_measured.get("bounds_size_unity"),
            },
        })

        if asset == "StatusIndicator":
            palette = {}
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
                palette[name] = material
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
                path = dirs["state"] / f"State_{asset}_{state}.png"
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
        shape = [v.get("clean") for v in after_audits.values()]
        print(f"[BatchB-R1] {asset}: tris {row['triangles_total']} "
              f"(was {before_measured['triangles_total']}), renderers "
              f"{row['renderers']}/{row['renderer_budget']}, submeshes "
              f"{submeshes}, slots {row['max_material_slots_per_object']}, "
              f"clearance {clearance['clean']} min "
              f"{clearance['min_clearance_mm']}, shape {shape}")

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
    grey = tree / f"ContactSheet_Theme4_{THEME}_P6B_R1_grayscale.png"
    p1.comparison_sheet(rows, grey)
    pairs = tree / f"ContactSheet_Theme4_{THEME}_P6B_R1_before_after.png"
    tiles = []
    for asset, row in payload["assets"].items():
        for source in ("before_images", "images"):
            for label in ("front", "oblique_right", "side"):
                tiles.append(review.load_rgba(project_root / row[source][label]))
    height, width = tiles[0].shape[:2]
    gap = 16
    columns = 6
    rows_n = len(tiles) // columns
    canvas = np.zeros((rows_n * height + (rows_n - 1) * gap,
                       columns * width + (columns - 1) * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        r, c = divmod(index, columns)
        top = (rows_n - 1 - r) * (height + gap)
        canvas[top:top + height,
               c * (width + gap):c * (width + gap) + width] = tile
    review.save_rgba(canvas, pairs)
    payload["contact_sheets"] = {
        "grayscale": {"path": str(grey.relative_to(project_root)),
                      "sha256": m1.digest(grey)},
        "before_after": {"path": str(pairs.relative_to(project_root)),
                         "sha256": m1.digest(pairs),
                         "layout": ("per instrument: Batch B front / oblique "
                                    "right / side, then R1's three, same "
                                    "camera and same materials")},
    }
    payload["shared_material_identities"] = sorted(
        {n for row in payload["assets"].values()
         for obj in row["objects"].values() for n in obj["material_slots"]})

    shape_clean = all(
        all(v.get("clean") for v in row["shape_audit_r1"].values())
        for row in payload["assets"].values())
    payload["shape_gates_clean"] = shape_clean
    payload["status"] = (
        "p6_batch_b_r1_ready"
        if shape_clean
        and all(row["max_material_slots_per_object"] <= 2
                for row in payload["assets"].values())
        and len(payload["shared_material_identities"]) <= 2
        and all(all(row["gates"].values())
                for row in payload["assets"].values())
        and all(row["clearance"]["clean"]
                for row in payload["assets"].values())
        and payload["knurl_bleed"]["clean"]
        else "p6_batch_b_r1_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchB-R1] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
