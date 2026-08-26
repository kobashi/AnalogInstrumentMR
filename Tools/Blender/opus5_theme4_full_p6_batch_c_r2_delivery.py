"""Theme 4 Phase 3 Batch C R2 delivery: the two window instruments only.

Writes only to delivery_p6/batch_c_r2/**. TrendMonitor is not rebuilt at all -
329 says Codex is fixing its orientation and overlay on the Unity side and the
FBX must not be corrected twice - so its Batch C digest is recorded and left
alone.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_c_r2_delivery.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
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
import opus5_theme4_full_p6_batch_a_r4_b3u as b3u
import opus5_theme4_full_p6_batch_c as bc
import opus5_theme4_full_p6_batch_c_delivery as bcd
import opus5_theme4_full_p6_batch_c_r1 as cr1
import opus5_theme4_full_p6_batch_c_r2 as c2
import opus5_theme4_fastener_access_r2 as far2
import opus5_theme4_fastener_access_r3 as r3
import opus5_theme4_fastener_access_r4 as r4

THEME = "MachinedErgonomics"
BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
TREE = f"{BASE}/batch_c_r2"
BATCH_C = f"{BASE}/batch_c"
BATCH_C_R1 = f"{BASE}/batch_c_r1"
OUTPUT = f"{TREE}/theme4_full_p6_batch_c_r2.json"

# The version each instrument is measured against: whatever was accepted last.
PREVIOUS = {
    "WindowMeter": (f"{BATCH_C_R1}/"
                    "SM_WindowMeter_MachinedErgonomics_V6_Opus5_P6C_R1.fbx",
                    "batch_c_r1"),
    "WindowPanel": (f"{BATCH_C}/"
                    "SM_WindowPanel_MachinedErgonomics_V6_Opus5_P6C.fbx",
                    "batch_c"),
}
UNTOUCHED = ("TrendMonitor",)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def signature_from_fbx(path):
    rows, hierarchy = b3u.read_fbx(path)
    out = {}
    for name, row in rows.items():
        out[name] = {
            "triangles": row["triangles"], "vertices": row["vertices"],
            "bounds_min": row["bounds_min"], "bounds_max": row["bounds_max"],
            "position_digest": hashlib.sha256(
                repr(row["unique_positions"]).encode("utf-8")).hexdigest(),
            "materials": row["materials"],
        }
    return {"objects": out, "hierarchy": hierarchy}


def uv_carry(obj, reference):
    """Copy the previous UV onto every triangle that still exists.

    The scale changes, so some triangles are new and have no previous UV to
    inherit; those keep what pack_into_regions gave them. The point of the
    pass is that a surface which did not change does not get repainted, which
    is the fault 317 caught, and the count of triangles that could not be
    carried is reported rather than buried.
    """
    stats = r4.copy_uv_multi(obj, reference, [("common", (0.0, 0.0, 0.0))])
    carried = stats["by_offset"].get("common", 0)
    return {
        "triangles": stats["triangles"],
        "carried_from_previous": carried,
        "new_in_r2": stats["triangles"] - carried,
        "duplicate": stats["duplicate"],
        "uv_changed_before_carry": stats["uv_changed_before"],
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in
            ("review", "motion", "closeup", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P6-BatchC-R2",
        "alignment": "329",
        "note": ("WindowMeter and WindowPanel only. Their motion and scale go "
                 "to -115..+115 degrees, 230 total, to match the RoundMeter "
                 "range Codex is moving the runtime amplitude to. "
                 "TrendMonitor is untouched here: 329 puts its orientation "
                 "and overlay on the Unity side and says not to correct the "
                 "FBX twice."),
        "frozen_trees": [BATCH_C, BATCH_C_R1],
        "contract_change": {
            asset: {
                "amplitude_deg_before": bc.CONTRACT[asset]["amplitude_deg"],
                "amplitude_deg_after": c2.CONTRACT[asset]["amplitude_deg"],
                "unity_range_deg_before": list(
                    bc.CONTRACT[asset]["unity_range_deg"]),
                "unity_range_deg_after": list(
                    c2.CONTRACT[asset]["unity_range_deg"]),
                "scale_sweep_deg": c2.SWEEP_DEG,
                "major_ticks": c2.MAJOR_INTERVALS + 1,
                "minors_per_major": c2.MINORS_PER_MAJOR,
            } for asset in c2.BUILDERS_C2},
        "assets": {},
        "untouched": {},
    }

    batch_c = json.loads(
        (project_root / f"{BATCH_C}/theme4_full_p6_batch_c.json").read_text())
    for asset in UNTOUCHED:
        row = batch_c["assets"][asset]
        fbx = project_root / row["fbx"]
        payload["untouched"][asset] = {
            "regenerated": False,
            "reason": ("329: Codex is normalising its display axes in Unity; "
                       "correcting the FBX as well would be a double fix"),
            "fbx": row["fbx"], "sha256_now": m1.digest(fbx),
            "sha256_in_batch_c_json": row["fbx_sha256"],
            "matches": m1.digest(fbx) == row["fbx_sha256"],
        }

    for asset, builder in c2.BUILDERS_C2.items():
        previous_path, previous_tree = PREVIOUS[asset]
        reference = r3.read_reference(project_root / previous_path)

        root, body, mover, movers, audit, parts, tagged = bcd.build(
            asset, builder)
        meshes = [body] + [obj for obj in movers if obj is not None]
        packing = bcd.dress(meshes, textures)
        carry = {}
        for obj in meshes:
            key = r3.object_key(obj.name)
            if key in reference:
                carry[obj.name] = uv_carry(obj, reference[key])
        bpy.context.view_layer.update()

        measured = c2.measure_asset(asset, root, body, mover, movers)
        statics = bc.bb.snapshot_statics([body])
        clearance = c2.clearance_audit(asset, mover, movers, statics,
                                       steps=144)
        exact = bc.coplanar_overlap_exact(meshes)
        pointer = c2.pointer_audit(asset, mover, movers, [body], steps=144)
        alignment = c2.pose_alignment(asset, mover, movers)
        seating = cr1.seating_audit(parts, asset)
        uv = bcd.uv_finite(meshes)

        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P6C_R2.fbx"
        d2.export_fbx(root, fbx)
        blend = dirs["blend"] / f"{asset}_{THEME}_P6C_R2.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)

        review.configure_scene()
        focus, radius, scale = p1.rig_for(meshes)
        images = {}
        for label, view in p1.VIEWS.items():
            path = dirs["review"] / f"R2_{asset}_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        for value, label in c2.pose_set(asset):
            c2.apply_pose(mover, asset, value)
            for view_label, view in (("front", (0.0, 0.0)),
                                     ("oblique_left", (-34.0, 18.0)),
                                     ("oblique_right", (34.0, 18.0))):
                path = dirs["motion"] / f"Pose_{asset}_{label}_{view_label}.png"
                p1.shot(focus, radius, view, 52.0, scale, path)
                images[f"pose_{label}_{view_label}"] = str(
                    path.relative_to(project_root))
        c2.apply_pose(mover, asset, 0.0)
        centre_z = (0.0 if asset == "WindowMeter" else c2.WP_PIVOT_Z)
        span = (0.34 if asset == "WindowMeter" else 0.32)
        for label, view in (("front", (0.0, 0.0)), ("oblique", (28.0, 16.0))):
            path = dirs["closeup"] / f"Scale_{asset}_{label}.png"
            p1.shot((0.0, bc.WM_FACE_Y if asset == "WindowMeter"
                     else bc.WP_FACE_Y, centre_z), span * 2.2, view, 56.0,
                    span, path)
            images[f"scale_closeup_{label}"] = str(
                path.relative_to(project_root))

        signature = signature_from_fbx(fbx)
        previous_signature = signature_from_fbx(project_root / previous_path)
        geometry_diff = {
            "previous_tree": previous_tree,
            "previous_fbx": previous_path,
            "same_objects": set(signature["objects"])
            == set(previous_signature["objects"]),
            "hierarchy_identical": signature["hierarchy"]
            == previous_signature["hierarchy"],
            "triangles": {name: {
                "r2": signature["objects"][name]["triangles"],
                "previous": previous_signature["objects"]
                .get(name, {}).get("triangles"),
            } for name in signature["objects"]},
            "mover_position_digest_identical": (
                signature["objects"].get(c2.CONTRACT[asset]["movable"], {})
                .get("position_digest")
                == previous_signature["objects"]
                .get(c2.CONTRACT[asset]["movable"], {})
                .get("position_digest")),
        }

        payload["assets"][asset] = dict(measured)
        payload["assets"][asset].update({
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx), "fbx_bytes": fbx.stat().st_size,
            "blend": str(blend.relative_to(project_root)),
            "part_roles": tagged, "objects_packing": packing,
            "submeshes_total": sum(r["submeshes"] for r in packing.values()),
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in packing.values()),
            "uv": uv, "uv_carry": carry,
            "coplanar_overlap_bounding_box": audit,
            "coplanar_overlap_exact": exact,
            "motion_clearance": clearance,
            "pointer_audit": pointer,
            "pose_alignment": alignment,
            "fastener_seating": seating,
            "mechanism": audit.get("mechanism"),
            "geometry_vs_previous": geometry_diff,
            "images": images,
        })
        print(f"[BatchC-R2] {asset}: tris {measured['triangles_total']}, "
              f"sweep {c2.SWEEP_DEG}, poses {clearance.get('poses')}, "
              f"clearance {clearance.get('clean')} min "
              f"{clearance.get('min_clearance_mm')}, coplanar exact "
              f"{exact['pair_count']}, pointer {pointer['clean']}, "
              f"alignment {alignment['clean']}, seats {seating['clean']}")

    payload["textures"] = {}
    for name, path in textures.items():
        here = m1.digest(path)
        candidate = project_root / BATCH_C / path.name
        payload["textures"][name] = {
            "path": str(path.relative_to(project_root)), "sha256": here,
            "matches_batch_c": candidate.exists()
            and m1.digest(candidate) == here}

    payload["gate"] = {
        "sweep_deg": c2.SWEEP_DEG,
        "measure_gates": all(all(row["gates"].values())
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
        "poses_on_major_ticks": all(row["pose_alignment"]["clean"]
                                    for row in payload["assets"].values()),
        "fastener_seating_clean": all(row["fastener_seating"]["clean"]
                                      for row in payload["assets"].values()),
        "uv_finite": all(entry["finite"] for row in payload["assets"].values()
                         for entry in row["uv"].values()),
        "node_names_kept": all(
            row["contract"]["motion_target"]
            == bc.CONTRACT[asset]["motion_target"]
            and row["contract"]["movable"] == bc.CONTRACT[asset]["movable"]
            for asset, row in payload["assets"].items()),
        "mount_plane_zero": all(row["mount_plane_ok"]
                                for row in payload["assets"].values()),
        "within_envelope": all(row["within_envelope"]
                               for row in payload["assets"].values()),
        "slots_within_two": all(row["max_material_slots_per_object"] <= 2
                                for row in payload["assets"].values()),
        "atlas_matches_batch_c": all(row["matches_batch_c"]
                                     for row in payload["textures"].values()),
        "trend_monitor_untouched": all(
            row["matches"] for row in payload["untouched"].values()),
        "targets": {asset: row["triangles_total"]
                    <= c2.CONTRACT[asset]["triangle_target_total"]
                    for asset, row in payload["assets"].items()},
    }
    gate = payload["gate"]
    payload["status"] = (
        "p6_batch_c_r2_ready"
        if gate["measure_gates"] and gate["coplanar_exact_zero"]
        and gate["motion_clean"] and gate["pointer_clean"]
        and gate["poses_on_major_ticks"] and gate["fastener_seating_clean"]
        and gate["uv_finite"] and gate["node_names_kept"]
        and gate["mount_plane_zero"] and gate["within_envelope"]
        and gate["slots_within_two"] and gate["atlas_matches_batch_c"]
        and gate["trend_monitor_untouched"] and all(gate["targets"].values())
        else "p6_batch_c_r2_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchC-R2] status {payload['status']}")


if __name__ == "__main__":
    main()
