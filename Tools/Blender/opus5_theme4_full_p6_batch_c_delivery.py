"""Theme 4 Phase 3 Batch C delivery: the three instruments 325 asks for.

Writes only to delivery_p6/batch_c/**. The P4 atlas is rebuilt into this tree
by the same deterministic generator the accepted deliveries used and its
digests are compared with theirs, so "not overwritten" is a measurement rather
than a promise. Nothing is registered anywhere: no prefab, no enum, no
catalog, no Resources.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_c_delivery.py -- \
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
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_delivery_p4 as p4d
import opus5_theme4_material_p2 as m2
import opus5_theme4_full_p6_batch_c as bc
import opus5_theme4_full_p6_batch_b_r1 as br1
import opus5_theme4_fastener_access_r4 as r4

THEME = "MachinedErgonomics"
BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
TREE = f"{BASE}/batch_c"
OUTPUT = f"{TREE}/theme4_full_p6_batch_c.json"
ATLAS_REFERENCE = (f"{BASE}/fastener_access_r4", f"{BASE}/fastener_access_r3",
                   f"{BASE}/batch_b")

ROLE_RULES = (
    ("readout", ("tick_", "index_", "plate_label", "needle", "vane",
                 "display_surface", "datum_bar")),
    ("gasket", ("gasket",)),
    ("metal", ("screw_", "bezel", "field_ring", "register", "rail_",
               "well_", "vent_", "access", "scale_strip", "display_well")),
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
    original_join, original_assign = p1.join, p1.assign
    captured, tagged, parts_live = {}, {}, []

    def hook(target, others):
        for obj in [target] + list(others):
            if obj is None:
                continue
            stem = obj.name.split(".")[0]
            captured.setdefault(stem, []).append(br1.world_triangles(obj))
            role = role_for(obj.name)
            tagged[stem] = role
            obj.data.materials.clear()
            obj.data.materials.append(roles[role])
        return original_join(target, others)

    def assign(obj, material):
        if not obj.data.materials:
            role = role_for(obj.name)
            tagged[obj.name.split(".")[0]] = role
            obj.data.materials.append(roles[role])

    p1.join, p1.assign = hook, assign
    try:
        body, mover, movers, audit = builder(roles["body"])
    finally:
        p1.join, p1.assign = original_join, original_assign
    movers = list(movers) if isinstance(movers, (list, tuple)) else [movers]
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    body.parent = root
    if mover is not None and mover is not body:
        mover.parent = root
    bpy.context.view_layer.update()
    parts = {name: np.concatenate(rows) for name, rows in captured.items()}
    return root, body, mover, movers, audit, parts, tagged


def dress(meshes, textures):
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


def uv_finite(meshes):
    """325.8 wants the UV recorded as finite, so it is measured, not assumed."""
    out = {}
    for obj in meshes:
        mesh = obj.data
        layer = mesh.uv_layers.active
        bad = 0
        lo = [math.inf, math.inf]
        hi = [-math.inf, -math.inf]
        for datum in layer.data:
            u, v = datum.uv
            if not (math.isfinite(u) and math.isfinite(v)):
                bad += 1
                continue
            lo[0], lo[1] = min(lo[0], u), min(lo[1], v)
            hi[0], hi[1] = max(hi[0], u), max(hi[1], v)
        out[obj.name] = {
            "loops": len(layer.data), "non_finite": bad,
            "uv_min": [round(v, 6) for v in lo] if bad < len(layer.data)
            else None,
            "uv_max": [round(v, 6) for v in hi] if bad < len(layer.data)
            else None,
            "finite": bad == 0,
        }
    return out


def display_audit(parts, display):
    """325.4: the plane runtime content has to sit on, measured."""
    tris = br1.world_triangles(display)
    front = float(tris[:, :, 1].min())
    face = tris[(tris[:, :, 1] <= front + 1e-6).all(axis=1)]
    xs = (float(face[:, :, 0].min()), float(face[:, :, 0].max()))
    zs = (float(face[:, :, 2].min()), float(face[:, :, 2].max()))
    opening = parts["bezel"]
    inner = opening.reshape(-1, 3)
    bezel_front = float(opening[:, :, 1].min())
    return {
        "front_plane_y_m": round(front, 5),
        "front_face_triangles": int(len(face)),
        "size_m": [round(xs[1] - xs[0], 5), round(zs[1] - zs[0], 5)],
        "minimum_m": list(bc.DISPLAY_MIN_M),
        "meets_minimum": (xs[1] - xs[0] >= bc.DISPLAY_MIN_M[0] - 1e-9
                          and zs[1] - zs[0] >= bc.DISPLAY_MIN_M[1] - 1e-9),
        "extent_x_m": [round(xs[0], 5), round(xs[1], 5)],
        "extent_z_m": [round(zs[0], 5), round(zs[1], 5)],
        "normal_blender": list(bc.DISPLAY_NORMAL_BLENDER),
        "up_blender": list(bc.DISPLAY_UP_BLENDER),
        "normal_unity": "+Z", "up_unity": "+Y",
        "single_plane": len({round(float(v), 6)
                             for v in face[:, :, 1].ravel()}) == 1,
        "bezel_front_y_m": round(bezel_front, 5),
        "behind_bezel_rim_mm": round((front - bezel_front) * 1000.0, 2),
        "inside_bezel_rim": front > bezel_front,
        "glass_meshes": 0,
    }


def seating_audit(parts, asset):
    """The R4 discipline, carried forward: does every screw land on metal?"""
    tree = r4.static_tree(parts)
    rows = {}
    for name in sorted({r4.fastener_id(n) for n in parts
                        if r4.fastener_id(n)}):
        frame = r4.fastener_frame(parts, name)
        if frame is None:
            continue
        cx, front_y, cz = frame
        seat_r = {"WindowMeter": 0.0120, "WindowPanel": 0.0130,
                  "TrendMonitor": 0.0062}[asset]
        probe = r4.seat_probe(tree, (cx, cz), front_y + 0.0005, seat_r)
        probe.update(r4.penetration_probe(tree, (cx, cz), front_y + 0.0005,
                                          0.0012))
        probe["head_centre_m"] = [round(cx, 5), round(front_y, 5),
                                  round(cz, 5)]
        rows[name] = probe
    return {"fasteners": rows,
            "clean": all(row.get("clean") for row in rows.values())}


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in
            ("review", "motion", "display", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P6-BatchC",
        "alignment": "325",
        "note": ("WindowMeter, WindowPanel and TrendMonitor. Nothing is "
                 "registered: no prefab, no enum, no catalog, no Resources. "
                 "The eleven accepted instruments, R1-R4, the P4 atlas, "
                 "Assets, Builds, docs and the three existing themes are "
                 "read-only here."),
        "authoring_convention": {
            "mount_plane": "Blender max Y == 0",
            "front": "Blender -Y, which the import path turns into Unity +Z",
            "up": "Blender +Z, which the import path turns into Unity +Y",
            "root_scale": 1.0,
            "unity_import_root_rotation_x_deg": -90.0,
        },
        "contract": {asset: {
            "kind": row["kind"],
            "motion_target": row["motion_target"], "movable": row["movable"],
            "motion": row["motion"], "unity_axis": row["unity_axis"],
            "amplitude_deg": row["amplitude_deg"],
            "unity_range_deg": list(row["unity_range_deg"]),
            "envelope_unity_xyz": list(row["envelope_unity_xyz"]),
            "renderer_budget": row["renderer_budget"],
            "triangle_budget_total": row["triangle_budget_total"],
            "triangle_target_total": row["triangle_target_total"],
        } for asset, row in bc.CONTRACT.items()},
        "assets": {},
    }

    for asset, builder in bc.BUILDERS_C.items():
        root, body, mover, movers, audit, parts, tagged = build(asset, builder)
        meshes = [body] + [obj for obj in movers if obj is not None]
        packing = dress(meshes, textures)
        measured = bc.measure_asset(asset, root, body, mover, movers)
        statics = bc.bb.snapshot_statics([body])
        clearance = bc.clearance_audit(asset, mover, movers, statics,
                                       steps=144)
        exact = bc.coplanar_overlap_exact(meshes)
        pointer = bc.pointer_audit(asset, mover, movers, [body], steps=144)
        seating = seating_audit(parts, asset)
        uv = uv_finite(meshes)

        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6C.fbx"
        d2.export_fbx(root, fbx)
        blend = dirs["blend"] / f"{asset}_{THEME}_P6C.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)

        review.configure_scene()
        focus, radius, scale = p1.rig_for(meshes)
        images = {}
        for label, view in p1.VIEWS.items():
            path = dirs["review"] / f"BatchC_{asset}_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        for value, label in bc.pose_set(asset):
            bc.apply_pose(mover, asset, value)
            path = dirs["motion"] / f"Motion_{asset}_{label}.png"
            p1.shot(focus, radius, (0.0, 0.0), 52.0, scale, path)
            images[f"pose_{label}"] = str(path.relative_to(project_root))
        bc.apply_pose(mover, asset, 0.0)

        row = dict(measured)
        row.update({
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "blend": str(blend.relative_to(project_root)),
            "blend_sha256": m1.digest(blend),
            "part_roles": tagged,
            "objects_packing": packing,
            "submeshes_total": sum(r["submeshes"] for r in packing.values()),
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in packing.values()),
            "uv": uv,
            "coplanar_overlap_bounding_box": audit,
            "coplanar_overlap_exact": exact,
            "coplanar_note": (
                "p3's audit compares axis-aligned boxes in XZ, which is "
                "conservative on a scale arc: the two accepted round meters "
                "carry 6 and 10 tick-to-tick pairs for the same reason. The "
                "exact column runs a separating-axis test on the triangles "
                "themselves and is the one that has to be zero."),
            "motion_clearance": clearance,
            "pointer_audit": pointer,
            "fastener_seating": seating,
            "mechanism": audit.get("mechanism"),
            "images": images,
        })

        if asset == "TrendMonitor":
            display = movers[0]
            row["display_surface"] = display_audit(parts, display)
            # 325.9: the surface alone, then the housing behind it, from the
            # same camera, so front/back and up/down are visible rather than
            # asserted.
            stages = {}
            saved = body.hide_render
            for stage, hide in (("display_only", True),
                                ("composed", False)):
                body.hide_render = hide
                bpy.context.view_layer.update()
                for label, view in (("front", (0.0, 0.0)),
                                    ("oblique", (34.0, 20.0)),
                                    ("above", (0.0, 62.0)),
                                    ("below", (0.0, -52.0)),
                                    ("behind", (180.0, 8.0))):
                    path = (dirs["display"]
                            / f"Display_{stage}_{label}.png")
                    p1.shot(focus, radius, view, 52.0, scale, path)
                    stages[f"{stage}_{label}"] = str(
                        path.relative_to(project_root))
            body.hide_render = saved
            bpy.context.view_layer.update()
            path = dirs["display"] / "Display_closeup.png"
            p1.shot((0.0, bc.TM_DISPLAY_FRONT, 0.0), 0.30, (18.0, 12.0), 58.0,
                    0.16, path)
            stages["closeup"] = str(path.relative_to(project_root))
            row["display_images"] = stages

        payload["assets"][asset] = row
        print(f"[BatchC] {asset}: tris {row['triangles_total']}/"
              f"{bc.CONTRACT[asset]['triangle_target_total']}, renderers "
              f"{row['renderers']}/{row['renderer_budget']}, submeshes "
              f"{row['submeshes_total']}, slots "
              f"{row['max_material_slots_per_object']}, gates "
              f"{all(row['gates'].values())}, coplanar exact "
              f"{exact['pair_count']}, clearance {clearance.get('clean')} "
              f"min {clearance.get('min_clearance_mm')}, seats "
              f"{seating['clean']}")

    payload["textures"] = {}
    for name, path in textures.items():
        here = m1.digest(path)
        matches = {}
        for folder in ATLAS_REFERENCE:
            candidate = project_root / folder / path.name
            matches[folder.rsplit("/", 1)[-1]] = (
                candidate.exists() and m1.digest(candidate) == here)
        payload["textures"][name] = {
            "path": str(path.relative_to(project_root)), "sha256": here,
            "bytes": path.stat().st_size,
            "matches_accepted_trees": matches}
    payload["knurl_patch"] = knurl_stats
    payload["new_atlas_region_required"] = False

    rows = [(asset, [(label, project_root / row["images"][label])
                     for label in ("front", "oblique_left",
                                   "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    sheet = tree / f"ContactSheet_Theme4_{THEME}_P6C.png"
    p1.comparison_sheet(rows, sheet)
    payload["contact_sheet"] = {"path": str(sheet.relative_to(project_root)),
                                "sha256": m1.digest(sheet)}
    payload["shared_material_identities"] = sorted(
        {n for row in payload["assets"].values()
         for obj in row["objects_packing"].values()
         for n in obj["material_slots"]})

    payload["gate"] = {
        "all_measure_gates": all(all(row["gates"].values())
                                 for row in payload["assets"].values()),
        "coplanar_exact_zero": all(
            row["coplanar_overlap_exact"]["pair_count"] == 0
            for row in payload["assets"].values()),
        "motion_clean": all(row["motion_clearance"].get("clean")
                            for row in payload["assets"].values()),
        "motion_poses": {asset: row["motion_clearance"].get("poses")
                         for asset, row in payload["assets"].items()},
        "pointer_clean": all(row["pointer_audit"]["clean"]
                             for row in payload["assets"].values()),
        "fastener_seating_clean": all(row["fastener_seating"]["clean"]
                                      for row in payload["assets"].values()),
        "uv_finite": all(entry["finite"] for row in payload["assets"].values()
                         for entry in row["uv"].values()),
        "shared_materials": len(payload["shared_material_identities"]),
        "slots_within_two": all(row["max_material_slots_per_object"] <= 2
                                for row in payload["assets"].values()),
        "display_ok": payload["assets"]["TrendMonitor"]["display_surface"][
            "meets_minimum"],
        "display_single_plane": payload["assets"]["TrendMonitor"][
            "display_surface"]["single_plane"],
        "atlas_untouched": all(
            all(row["matches_accepted_trees"].values())
            for row in payload["textures"].values()),
        "targets": {asset: row["triangles_total"]
                    <= bc.CONTRACT[asset]["triangle_target_total"]
                    for asset, row in payload["assets"].items()},
    }
    gate = payload["gate"]
    payload["status"] = (
        "p6_batch_c_ready"
        if gate["all_measure_gates"] and gate["coplanar_exact_zero"]
        and gate["motion_clean"] and gate["pointer_clean"]
        and gate["fastener_seating_clean"] and gate["uv_finite"]
        and gate["shared_materials"] <= 2 and gate["slots_within_two"]
        and gate["display_ok"] and gate["display_single_plane"]
        and gate["atlas_untouched"] and all(gate["targets"].values())
        else "p6_batch_c_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchC] status {payload['status']}")


if __name__ == "__main__":
    main()
