"""Theme 4 Phase 3 Batch C R1 delivery: WindowMeter only.

Writes only to delivery_p6/batch_c_r1/**. WindowPanel and TrendMonitor are not
rebuilt for export; their Batch C digests are re-measured and recorded, and
their fasteners are re-measured in-session because 326.3 asks for all fourteen.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_c_r1_delivery.py -- \
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
import opus5_theme4_fastener_access_r2 as r2
import opus5_theme4_fastener_access_r3 as r3
import opus5_theme4_fastener_access_r4 as r4

THEME = "MachinedErgonomics"
BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
TREE = f"{BASE}/batch_c_r1"
BATCH_C = f"{BASE}/batch_c"
OUTPUT = f"{TREE}/theme4_full_p6_batch_c_r1.json"
TARGET = "WindowMeter"


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
        positions = row["unique_positions"]
        out[name] = {
            "triangles": row["triangles"], "vertices": row["vertices"],
            "bounds_min": row["bounds_min"], "bounds_max": row["bounds_max"],
            "position_digest": hashlib.sha256(
                repr(positions).encode("utf-8")).hexdigest(),
            "materials": row["materials"],
        }
    return {"objects": out, "hierarchy": hierarchy}


def build(asset, moved):
    saved = cr1.install(asset) if moved else None
    try:
        root, body, mover, movers, audit, parts, tagged = bcd.build(
            asset, bc.BUILDERS_C[asset])
    finally:
        if saved is not None:
            cr1.restore(saved)
    return root, body, mover, movers, audit, parts, tagged


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in ("review", "closeup", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P6-BatchC-R1",
        "alignment": "326",
        "note": ("WindowMeter's screw_-1_-1 moved 12.5 mm off the nameplate "
                 "onto flat panel, and the seating gate rebuilt so a "
                 "penetration pass can no longer overwrite a seating fail. "
                 "Nothing else is rebuilt for export."),
        "frozen_trees": [BATCH_C],
        "defects_from_326": {
            "geometry": ("WindowMeter screw_-1_-1 seat spread 6.2 mm: the "
                         "inner 4 mm of a 12 mm seat lay on the nameplate, "
                         "whose left edge is x -0.5398 and which stands "
                         "6.2 mm proud of the shell face"),
            "validator": ("seating_audit merged seat_probe and "
                          "penetration_probe with dict.update, and both "
                          "return a key called `clean`, so the penetration "
                          "verdict replaced the seating one"),
        },
        "moved": {f"{asset}:{name}": list(centre)
                  for (asset, name), centre in cr1.MOVED.items()},
        "assets": {},
        "carried_unchanged": {},
    }

    batch_c = json.loads(
        (project_root / f"{BATCH_C}/theme4_full_p6_batch_c.json").read_text())

    # --- the two instruments R1 does not touch
    for asset in cr1.CARRIED:
        row = batch_c["assets"][asset]
        fbx = project_root / row["fbx"]
        blend = project_root / row["blend"]
        _, _, _, movers, _, parts, _ = build(asset, moved=False)
        seating = cr1.seating_audit(parts, asset)
        payload["carried_unchanged"][asset] = {
            "regenerated_for_export": False,
            "fbx": row["fbx"], "sha256_now": m1.digest(fbx),
            "sha256_in_batch_c_json": row["fbx_sha256"],
            "matches": m1.digest(fbx) == row["fbx_sha256"],
            "blend_matches": m1.digest(blend) == row["blend_sha256"],
            "fastener_seating": seating,
        }

    # --- the reference build, then the corrected one
    reference = r3.read_reference(project_root / cr1.UV_REFERENCE[TARGET])
    _, body0, _, movers0, _, parts0, _ = build(TARGET, moved=False)
    before_signature = r2.part_signature(parts0)
    before_seating = cr1.seating_audit(parts0, TARGET)

    root, body, mover, movers, audit, parts, tagged = build(TARGET, moved=True)
    meshes = [body] + [obj for obj in movers if obj is not None]
    packing = bcd.dress(meshes, textures)
    shifts = r4.screw_offsets(parts0, parts)
    offsets = [("common", (0.0, 0.0, 0.0))] + [(name, shift)
                                               for name, shift in shifts]
    copied, verified = {}, {}
    for obj in meshes:
        key = r3.object_key(obj.name)
        if key not in reference:
            copied[obj.name] = {"error": "no reference object", "clean": False}
            continue
        copied[obj.name] = r4.copy_uv_multi(obj, reference[key], offsets)
        verified[obj.name] = r4.verify_uv_multi(obj, reference[key], offsets)
    bpy.context.view_layer.update()

    measured = bc.measure_asset(TARGET, root, body, mover, movers)
    statics = bc.bb.snapshot_statics([body])
    clearance = bc.clearance_audit(TARGET, mover, movers, statics, steps=144)
    exact = bc.coplanar_overlap_exact(meshes)
    pointer = bc.pointer_audit(TARGET, mover, movers, [body], steps=144)
    seating = cr1.seating_audit(parts, TARGET)
    uv = bcd.uv_finite(meshes)
    after_signature = r2.part_signature(parts)
    freeze = r2.signature_diff(before_signature, after_signature,
                               {"screw_-1_-1"})

    fbx = tree / f"SM_{TARGET}_{THEME}_V6_Opus5_P6C_R1.fbx"
    d2.export_fbx(root, fbx)
    blend = dirs["blend"] / f"{TARGET}_{THEME}_P6C_R1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)

    review.configure_scene()
    focus, radius, scale = p1.rig_for(meshes)
    images = {}
    for label, view in p1.VIEWS.items():
        path = dirs["review"] / f"R1_{TARGET}_{label}.png"
        p1.shot(focus, radius, view, 52.0, scale, path)
        images[label] = str(path.relative_to(project_root))
    moved_xz = cr1.MOVED[(TARGET, "screw_-1_-1")]
    # Framed to hold the moved screw, the nameplate it used to overlap and
    # the panel edge in one shot: a tighter frame shows the nameplate filling
    # the view and proves nothing.
    close_focus = (moved_xz[0] + 0.090, bc.WM_FACE_Y, moved_xz[1] + 0.005)
    for label, view in (("front", (0.0, 0.0)), ("oblique", (32.0, 18.0)),
                        ("grazing", (72.0, 6.0))):
        path = dirs["closeup"] / f"R1_{TARGET}_screw_{label}.png"
        p1.shot(close_focus, 0.300, view, 58.0, 0.150, path)
        images[f"screw_closeup_{label}"] = str(path.relative_to(project_root))

    r1_signature = signature_from_fbx(fbx)
    c_signature = signature_from_fbx(
        project_root / batch_c["assets"][TARGET]["fbx"])
    same_objects = set(r1_signature["objects"]) == set(c_signature["objects"])
    needle_identical = (
        r1_signature["objects"].get("needle", {}).get("position_digest")
        == c_signature["objects"].get("needle", {}).get("position_digest"))
    triangles_same = all(
        r1_signature["objects"][name]["triangles"]
        == c_signature["objects"][name]["triangles"]
        for name in r1_signature["objects"] if name in c_signature["objects"])

    payload["assets"][TARGET] = dict(measured)
    payload["assets"][TARGET].update({
        "fbx": str(fbx.relative_to(project_root)),
        "fbx_sha256": m1.digest(fbx), "fbx_bytes": fbx.stat().st_size,
        "blend": str(blend.relative_to(project_root)),
        "part_roles": tagged, "objects_packing": packing,
        "submeshes_total": sum(r["submeshes"] for r in packing.values()),
        "max_material_slots_per_object": max(
            len(r["material_slots"]) for r in packing.values()),
        "uv": uv,
        "uv_copy": copied, "uv_verify": verified,
        "uv_offsets": [{"fastener": name,
                        "shift_m": [round(v, 8) for v in shift]}
                       for name, shift in shifts],
        "coplanar_overlap_bounding_box": audit,
        "coplanar_overlap_exact": exact,
        "motion_clearance": clearance,
        "pointer_audit": pointer,
        "fastener_seating": seating,
        "fastener_seating_before_r1": before_seating,
        "frozen_parts_vs_batch_c": freeze,
        "signature_r1": r1_signature,
        "signature_batch_c": c_signature,
        "geometry_vs_batch_c": {
            "same_objects": same_objects,
            "triangles_identical": triangles_same,
            "needle_position_digest_identical": needle_identical,
            "only_moved_screw_differs": freeze["clean"],
        },
        "images": images,
    })

    payload["textures"] = {}
    for name, path in textures.items():
        here = m1.digest(path)
        candidate = project_root / BATCH_C / path.name
        payload["textures"][name] = {
            "path": str(path.relative_to(project_root)), "sha256": here,
            "matches_batch_c": candidate.exists()
            and m1.digest(candidate) == here}

    all_rows = {TARGET: seating}
    for asset in cr1.CARRIED:
        all_rows[asset] = payload["carried_unchanged"][asset][
            "fastener_seating"]
    payload["fastener_census"] = {
        "total": sum(row["count"] for row in all_rows.values()),
        "per_asset": {asset: row["count"] for asset, row in all_rows.items()},
        "seat_clean": all(row["seat_clean"] for row in all_rows.values()),
        "penetration_clean": all(row["penetration_clean"]
                                 for row in all_rows.values()),
        "clean": all(row["clean"] for row in all_rows.values()),
    }

    uv_totals = {key: sum(row[key] for row in verified.values())
                 for key in ("triangles", "compared", "uv_changed",
                             "unmatched", "position_mismatch",
                             "duplicate_match")}
    payload["gate"] = {
        "fasteners_total": payload["fastener_census"]["total"],
        "fastener_clean": payload["fastener_census"]["clean"],
        "seat_and_penetration_kept_apart": True,
        "uv_totals": uv_totals,
        "uv_changed_zero": uv_totals["uv_changed"] == 0
        and uv_totals["unmatched"] == 0
        and uv_totals["position_mismatch"] == 0
        and uv_totals["duplicate_match"] == 0,
        "only_moved_screw_differs": freeze["clean"],
        "measure_gates": all(measured["gates"].values()),
        "coplanar_exact_zero": exact["pair_count"] == 0,
        "motion_clean": clearance.get("clean"),
        "motion_poses": clearance.get("poses"),
        "pointer_clean": pointer["clean"],
        "carried_digests_match": all(
            row["matches"] and row["blend_matches"]
            for row in payload["carried_unchanged"].values()),
        "atlas_matches_batch_c": all(row["matches_batch_c"]
                                     for row in payload["textures"].values()),
    }
    gate = payload["gate"]
    payload["status"] = (
        "p6_batch_c_r1_ready"
        if gate["fastener_clean"] and gate["uv_changed_zero"]
        and gate["only_moved_screw_differs"] and gate["measure_gates"]
        and gate["coplanar_exact_zero"] and gate["motion_clean"]
        and gate["pointer_clean"] and gate["carried_digests_match"]
        and gate["atlas_matches_batch_c"]
        else "p6_batch_c_r1_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchC-R1] status {payload['status']}; "
          f"{json.dumps(payload['fastener_census'])}")


if __name__ == "__main__":
    main()
