"""Phase M2m2b: capture the old failure, then bisect inside the bracket.

Alignment 138.1. Two jobs, in order, and the first is not skipped because the
second works.

First the old solver's failure is looked for directly: at offsets 0, 0.020 and
0.050 mm, on the same rebuilt geometry, `m2m1.pair_distance()` and the exact
closest-pair distance are recorded side by side. If the old path returns zero,
what made it do so - crossing or penetration, which direction, which object,
which triangle or vertex - is recorded. If it does not, that is written down as
`not_reproduced` rather than quietly replaced by the hypothesis that fitted.

Then the offset is solved by bisection inside the bracket the diagnostic
established, rebuilding from the approved B2P at every trial. The objective is
the exact surface distance; crossing and penetration are a separate hard fail
carrying their pair and reason, never folded into "distance zero". No
candidates, no measurement, or a non-finite value fails immediately.

The attempt JSON is written on every path, including failure, and a failure
publishes nothing.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_bracketed_build.py -- \
      --project-root "$PWD" [--trial-dir /tmp/somewhere]
"""

import argparse
import json
import math
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d3_clearance_supplement as m2m1
import opus5_d3_combined_build as m2m
import opus5_d3_exact_corrected_build as m2m2
import opus5_d3_solver_diagnostic as diag
import opus5_d5_candidate_build as m2e
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_d6_round_r3_validation as m2k3
import opus5_publish as publish


ATTEMPT = "ArtSource/Blender/BrushUp/Opus5/d3_bracketed_attempt.json"
AUDIT_39 = "ArtSource/Blender/BrushUp/Opus5/audit_39_with_r3_d3_b2p_d3p.json"
PREFIX = "d3p_bracketed"
MODELS = ("MeterMedium", "MeterLarge")
BRACKET_MM = (0.020, 0.050)
BRACKET_TOLERANCE_MM = 0.001
CAUSE_OFFSETS_MM = (0.0, 0.020, 0.050)
POSES = m2k.POSES


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append")
    parser.add_argument("--trial-dir")
    parser.add_argument("--skip-renders", action="store_true")
    parser.add_argument("--skip-39", action="store_true")
    return parser.parse_args(args)


def rebuilt(project_root, key, offset_mm, base_required=None):
    """Approved B2P plus this offset. Never the previous trial."""
    root, pivot = m2m.open_input(project_root, key)
    if base_required is None:
        base_required = (
            m2m.swept_radius(root, pivot)["swept_radius_m"]
            + m2m.CLEARANCE_MM[key] / 1000.0
        )
    required = base_required + offset_mm / 1000.0
    changes = m2m.retract_ticks(root, pivot, required)
    return root, pivot, required, base_required, changes


def hard_fail_check(root, pivot):
    """Crossing and penetration, kept apart from the distance objective."""
    base = pivot.rotation_euler.copy()
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    ticks = [obj for obj in pilot.meshes_under(root) if obj.name in m2m.ALLOWLIST]
    findings = []
    try:
        for degrees in POSES:
            pivot.rotation_euler[1] = base[1] + math.radians(degrees)
            bpy.context.view_layer.update()
            for mover in movable:
                mover_tris = m1.world_triangles(mover)
                mover_broad, mover_exact = m1.trees(mover)
                for tick in ticks:
                    tick_tris = m1.world_triangles(tick)
                    tick_broad, tick_exact = m1.trees(tick)
                    pairs = contact.candidate_pairs(
                        mover_tris, tick_tris, mover_broad, tick_broad
                    )
                    surface = contact.surface_contact(mover_tris, tick_tris, pairs)
                    if surface[contact.CROSSING]:
                        findings.append(
                            {
                                "pair": f"{mover.name} x {tick.name}",
                                "pose_deg": round(degrees, 4),
                                "reason": "surface crossing",
                                "count": len(surface[contact.CROSSING]),
                            }
                        )
                    for source, tree, way in (
                        (mover, tick_exact, "mover vertices in tick"),
                        (tick, mover_exact, "tick vertices in mover"),
                    ):
                        depth = contact.material_penetration(
                            [
                                source.matrix_world @ v.co
                                for v in source.data.vertices
                            ],
                            tree,
                        )
                        if depth["penetrating_vertices"]:
                            findings.append(
                                {
                                    "pair": f"{mover.name} x {tick.name}",
                                    "pose_deg": round(degrees, 4),
                                    "reason": "penetration",
                                    "direction": way,
                                    "vertices": depth["penetrating_vertices"],
                                    "deepest_mm": depth["deepest_intrusion_mm"],
                                }
                            )
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return findings


def objective(root, pivot, centre, radius):
    """Exact worst surface distance. Anything unmeasurable is a failure."""
    worst, per_tick = diag.measure(root, pivot, centre, radius)
    if worst is None:
        return None, per_tick, "no candidate triangle pair was found"
    value = worst["distance_mm"]
    if not math.isfinite(value):
        return None, per_tick, f"non-finite distance {value}"
    return worst, per_tick, None


def capture_cause(project_root, key, radius):
    """Old reading and new reading, on the same geometry, at three offsets."""
    rows = []
    base_required = None
    for offset in CAUSE_OFFSETS_MM:
        root, pivot, required, base_required, _ = rebuilt(
            project_root, key, offset, base_required
        )
        centre = pivot.matrix_world.translation.copy()
        movable = [
            obj
            for obj in pilot.meshes_under(root)
            if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
        ]
        ticks = [
            obj for obj in pilot.meshes_under(root) if obj.name in m2m.ALLOWLIST
        ]
        base = pivot.rotation_euler.copy()
        zeros = []
        old_worst = None
        try:
            for degrees in POSES:
                pivot.rotation_euler[1] = base[1] + math.radians(degrees)
                bpy.context.view_layer.update()
                for mover in movable:
                    for tick in ticks:
                        old, how = m2m1.pair_distance(mover, tick, radius)
                        if old is None:
                            continue
                        millimetres = old * 1000.0
                        if old_worst is None or millimetres < old_worst[0]:
                            old_worst = (millimetres, f"{mover.name} x {tick.name}", degrees, how)
                        if millimetres <= 0.0:
                            zeros.append(
                                {
                                    "pair": f"{mover.name} x {tick.name}",
                                    "pose_deg": round(degrees, 4),
                                    "old_reason": how,
                                }
                            )
        finally:
            pivot.rotation_euler = base
            bpy.context.view_layer.update()
        new_worst, _, failure = objective(root, pivot, centre, radius)
        rows.append(
            {
                "offset_mm": offset,
                "old_pair_distance_worst_mm": (
                    round(old_worst[0], 6) if old_worst else None
                ),
                "old_worst_pair": old_worst[1] if old_worst else None,
                "old_worst_pose_deg": round(old_worst[2], 4) if old_worst else None,
                "old_reason": old_worst[3] if old_worst else None,
                "old_zero_returns": zeros,
                "new_exact_worst_mm": new_worst["distance_mm"] if new_worst else None,
                "new_worst_pair": new_worst["pair"] if new_worst else None,
                "new_feature": new_worst["feature"] if new_worst else None,
                "objective_failure": failure,
            }
        )
    reproduced = any(row["old_zero_returns"] for row in rows)
    return {
        "rows": rows,
        "zero_return_reproduced": reproduced,
        "conclusion": (
            "the old path returned zero on this geometry; the recorded reason "
            "is the cause"
            if reproduced
            else "not_reproduced: the old path did not return zero here, so "
            "the earlier hypothesis is not confirmed and is not recorded as "
            "the cause"
        ),
    }


def bisect(project_root, key, radius):
    target = m2m2.SOLVER_TARGET_MM[key] if hasattr(m2m2, "SOLVER_TARGET_MM") else (
        m2m.CLEARANCE_MM[key] + m2m2.GUARD_BAND_MM
    )
    low, high = BRACKET_MM
    trail = []
    base_required = None
    best = None
    for step in range(24):
        for offset in ((low, "low"), (high, "high")) if step == 0 else ((
            (low + high) * 0.5, "mid"
        ),):
            value, side = offset
            root, pivot, required, base_required, _ = rebuilt(
                project_root, key, value, base_required
            )
            centre = pivot.matrix_world.translation.copy()
            worst, per_tick, failure = objective(root, pivot, centre, radius)
            if failure:
                return None, trail, f"objective failed at {value} mm: {failure}"
            trail.append(
                {
                    "step": step,
                    "side": side,
                    "offset_mm": round(value, 6),
                    "required_radius_mm": round(required * 1000.0, 6),
                    "distance_mm": worst["distance_mm"],
                    "pair": worst["pair"],
                    "pose_deg": worst["pose_deg"],
                    "feature": worst["feature"],
                }
            )
            if worst["distance_mm"] >= target:
                if best is None or value < best["offset_mm"]:
                    best = {
                        "offset_mm": value,
                        "required_radius_mm": required,
                        "distance_mm": worst["distance_mm"],
                    }
                high = value
            else:
                low = value
        if high - low <= BRACKET_TOLERANCE_MM:
            break
    if best is None:
        return None, trail, "no offset in the bracket reached the solver target"
    return best, trail, None


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    keys = args.models or list(MODELS)
    attempt_path = (
        (Path(args.trial_dir) / "d3_bracketed_attempt.json")
        if args.trial_dir
        else (project_root / ATTEMPT)
    )
    payload = {
        "phase": "M2m2b",
        "note": (
            "Cause capture and bracketed bisection (alignment 138.1). This "
            "file is written on every path; a failure publishes nothing."
        ),
        "bracket_mm": list(BRACKET_MM),
        "bracket_tolerance_mm": BRACKET_TOLERANCE_MM,
        "models": {},
    }
    started = time.perf_counter()
    staging = Path(tempfile.mkdtemp(prefix="opus5-d3p-bracket-"))
    entries = {}
    try:
        fixtures = diag.fixture_check()
        payload["closest_point_self_test"] = fixtures
        if not fixtures["all_passed"]:
            payload["status"] = "self-test failed"
            return

        for key in keys:
            begin = time.perf_counter()
            radius = max(
                m2m.CLEARANCE_MM[key] * 3.0 / 1000.0, m2m1.SEARCH_FLOOR_M
            )
            source = m2m.input_blend(project_root, key)
            model = {
                "input": str(source.relative_to(project_root)),
                "input_sha256": m1.digest(source),
                "input_report_sha256": m1.digest(m2m.input_report(project_root, key)),
                "contract_mm": m2m.CLEARANCE_MM[key],
                "solver_target_mm": m2m.CLEARANCE_MM[key] + m2m2.GUARD_BAND_MM,
                "accept_floor_mm": m2m.CLEARANCE_MM[key] + m2m2.ACCEPT_BAND_MM,
            }
            model["cause_capture"] = capture_cause(project_root, key, radius)
            best, trail, failure = bisect(project_root, key, radius)
            model.update({"solver_trail": trail, "solver_failure": failure})
            if best is None:
                model["status"] = "solver failed"
                payload["models"][key] = model
                continue

            root, pivot, required, _, changes = rebuilt(
                project_root, key, best["offset_mm"]
            )
            reference_root, reference_pivot = m2m.open_input(project_root, key)
            reference = m2m.semantic(reference_root)
            root, pivot, required, _, changes = rebuilt(
                project_root, key, best["offset_mm"]
            )
            diff = m2m.allowlist_diff(reference, m2m.semantic(root))
            hard = hard_fail_check(root, pivot)

            staged = staging / f"{key}.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True)
            audited = m2m.audit(project_root, key, staged, required, True)

            m1.open_blend(staged)
            saved_root = bpy.data.objects[m2k.MODELS[key]["root"]]
            saved_pivot = bpy.data.objects["needle_pivot"]
            saved_centre = saved_pivot.matrix_world.translation.copy()
            saved_worst, saved_per_tick, saved_failure = objective(
                saved_root, saved_pivot, saved_centre, radius
            )
            floor = model["accept_floor_mm"]
            problems = []
            if not audited["pass"]:
                problems.append("audit")
            if not diff["pass"]:
                problems.append("semantic diff outside the allowlist")
            if hard:
                problems.append("crossing or penetration on an allowlist tick")
            if saved_failure or saved_worst is None:
                problems.append(f"saved objective failed: {saved_failure}")
            elif saved_worst["distance_mm"] < floor:
                problems.append(
                    f"saved {saved_worst['distance_mm']} mm below floor {floor} mm"
                )

            model.update(
                {
                    "chosen_offset_mm": best["offset_mm"],
                    "final_required_radius_mm": round(required * 1000.0, 6),
                    "tick_changes": changes,
                    "vertices_moved_total": sum(
                        entry["vertices_moved"] for entry in changes.values()
                    ),
                    "semantic_diff": diff,
                    "hard_fail_findings": hard,
                    "saved_worst": saved_worst,
                    "saved_per_tick": saved_per_tick,
                    "staged_sha256": m1.digest(staged),
                    "audit": audited,
                    "problems": problems,
                    "status": "measured",
                    "elapsed_seconds": round(time.perf_counter() - begin, 3),
                }
            )
            payload["models"][key] = model
            entries[key] = model
            print(
                f"[Opus5D3brk] {key}: offset {best['offset_mm']:.6f} mm, saved "
                f"{saved_worst['distance_mm'] if saved_worst else None} mm "
                f"(floor {floor}), moved {model['vertices_moved_total']}, "
                f"cause {model['cause_capture']['zero_return_reproduced']}, "
                f"problems {problems}"
            )

        publishable = [
            key for key in keys if key in entries and not entries[key]["problems"]
        ]
        audit39 = {"skipped": True}
        if publishable and not args.skip_39:
            audit39 = m2m.run_39(
                project_root,
                {
                    **{key: staging / f"{key}.blend" for key in publishable},
                    "MeterRound": m2m.output_blend(project_root, "MeterRound", None),
                },
                (Path(args.trial_dir) / "audit_39.json")
                if args.trial_dir
                else (project_root / AUDIT_39),
            )
        payload["audit_39"] = audit39

        for key in publishable:
            if not args.skip_renders:
                entries[key]["renders"] = {
                    "input_b2p": m2k3.render_state(
                        project_root, f"{PREFIX}_{key}_b2p",
                        lambda k=key: (
                            m1.open_blend(m2m.input_blend(project_root, k))
                            or bpy.data.objects[m2k.MODELS[k]["root"]]
                        ),
                    ),
                    "failed_b2p_d3": m2k3.render_state(
                        project_root, f"{PREFIX}_{key}_b2p_d3",
                        lambda k=key: (
                            m1.open_blend(m2m.output_blend(project_root, k, None))
                            or bpy.data.objects[m2k.MODELS[k]["root"]]
                        ),
                    ),
                    "proposed_b2p_d3p": m2k3.render_state(
                        project_root, f"{PREFIX}_{key}_b2p_d3p",
                        lambda k=key: (
                            m1.open_blend(staging / f"{k}.blend")
                            or bpy.data.objects[m2k.MODELS[k]["root"]]
                        ),
                    ),
                }
            current = m1.digest(m2m.input_blend(project_root, key))
            entries[key]["input_sha256_at_publish"] = current
            problems = list(entries[key]["problems"])
            if current != entries[key]["input_sha256"]:
                problems.append("input changed between build and publish")
            if not args.skip_39 and not audit39.get("pass"):
                problems.append("39-model audit did not pass")
            record = publish.publish(
                m2m2.output_blend(project_root, key, args.trial_dir),
                m2m2.output_report(project_root, key, args.trial_dir),
                {
                    "phase": "M2m2b",
                    "defects": ["D-3", "D-6"],
                    "object": key,
                    "theme": m2k.THEME,
                    "revision": m2m2.OUTPUT_REVISION,
                    "note": (
                        "Offset solved by bisection inside the diagnostic's "
                        "bracket (alignment 138.1); rebuilt from B2P at every "
                        "trial."
                    ),
                    "closest_point_self_test": fixtures,
                    "audit_39": audit39,
                    **{k: v for k, v in entries[key].items() if k != "problems"},
                    "authoring_environment": blender_compat.provenance(),
                },
                problems,
                trial_dir=args.trial_dir,
                save_blend=lambda path, k=key: shutil.copy2(
                    staging / f"{k}.blend", path
                ),
                reopen_blend=lambda path: m1.open_blend(path),
            )
            entries[key]["publish"] = record
            payload["models"][key]["publish"] = record
            print(f"[Opus5D3brk] {key}: {record['mode']} - {record['reason']}")
        payload["status"] = "complete"
    except Exception:  # noqa: BLE001 - recorded, then the attempt file is written
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        attempt_path.parent.mkdir(parents=True, exist_ok=True)
        attempt_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        shutil.rmtree(staging, ignore_errors=True)
        print(f"[Opus5D3brk] {payload.get('status')} -> {attempt_path}")


if __name__ == "__main__":
    main()
