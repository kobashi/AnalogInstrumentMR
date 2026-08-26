"""Phase M2m2: solve the tick offset against the distance that is contracted.

Alignment 134.1. M2m set the tick inner ends by a radial rule and came out
3.7 and 5.5 micrometres short of the proportional clearance, because the
closest approach is an oblique edge-to-edge pair, not a radial one. The fix is
not a different shape: it is solving for the quantity that was always the
contract.

Each iteration rebuilds from the approved B2P - never from the previous
attempt, which would compound the offset - retracts the three endpoint ticks to
a trial radius, and measures the exact triangle-to-triangle distance over the
whole travel. The trial radius grows by exactly the shortfall until the worst
pose clears the solver target.

The solver aims 20 micrometres above the contract and the saved file is
accepted at 10 above it. That band is for Blender's save and the float
conversion after it, not a relaxation: the contract itself is unchanged.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_exact_corrected_build.py -- \
      --project-root "$PWD" [--trial-dir /tmp/somewhere]
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
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
import opus5_d5_candidate_build as m2e
import opus5_d6_bounded_correction as m2k1
import opus5_d6_canonical_build as m2l
import opus5_d6_full_assembly as m2k2
import opus5_d6_repair_decision as m2k
import opus5_d6_round_r3_validation as m2k3
import opus5_publish as publish


AUDIT_39 = "ArtSource/Blender/BrushUp/Opus5/audit_39_with_r3_d3_b2p_d3p.json"
PREFIX = "d3p_corrected"
MODELS = ("MeterMedium", "MeterLarge")
OUTPUT_REVISION = "B2P_D3P"

GUARD_BAND_MM = 0.020
ACCEPT_BAND_MM = 0.010
MAX_ITERATIONS = 10
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


def output_blend(project_root, key, trial_dir):
    name = f"BL_{key}_{m2k.THEME}_V6_Opus5_{OUTPUT_REVISION}_Retopo.blend"
    return (
        (Path(trial_dir) / name)
        if trial_dir
        else (m2l.theme_dir(project_root) / name)
    )


def output_report(project_root, key, trial_dir):
    name = f"{key}_{m2k.THEME}_V6_Opus5_{OUTPUT_REVISION}.json"
    return (
        (Path(trial_dir) / name)
        if trial_dir
        else (project_root / m2l.REPORT_DIR / name)
    )


def worst_tick_distance(root, pivot, radius):
    """Exact surface distance to the three endpoint ticks, over the travel."""
    base = pivot.rotation_euler.copy()
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    ticks = [
        obj for obj in pilot.meshes_under(root) if obj.name in m2m.ALLOWLIST
    ]
    worst = None
    per_tick = {}
    try:
        for degrees in POSES:
            pivot.rotation_euler[1] = base[1] + math.radians(degrees)
            bpy.context.view_layer.update()
            for mover in movable:
                for tick in ticks:
                    distance, how = m2m1.pair_distance(mover, tick, radius)
                    if distance is None:
                        continue
                    millimetres = distance * 1000.0
                    label = f"{mover.name} x {tick.name}"
                    entry = per_tick.setdefault(label, {"minimum_mm": None})
                    if (
                        entry["minimum_mm"] is None
                        or millimetres < entry["minimum_mm"]
                    ):
                        entry.update(
                            {
                                "minimum_mm": round(millimetres, 6),
                                "pose_deg": round(degrees, 4),
                                "method": how,
                            }
                        )
                    if worst is None or millimetres < worst[0]:
                        worst = (millimetres, label, degrees)
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return worst, per_tick


def solve(project_root, key):
    """Grow the trial radius by the shortfall until the travel clears."""
    target = m2m.CLEARANCE_MM[key]
    solver_target = target + GUARD_BAND_MM
    search = max(target * 3.0 / 1000.0, m2m1.SEARCH_FLOOR_M)
    trail = []
    required = None
    for iteration in range(MAX_ITERATIONS):
        root, pivot = m2m.open_input(project_root, key)
        if required is None:
            sweep = m2m.swept_radius(root, pivot)
            required = sweep["swept_radius_m"] + target / 1000.0
            trail.append({"iteration": 0, "note": "radial start", "swept": sweep})
        changes = m2m.retract_ticks(root, pivot, required)
        worst, per_tick = worst_tick_distance(root, pivot, search)
        trail.append(
            {
                "iteration": iteration + 1,
                "trial_radius_mm": round(required * 1000.0, 6),
                "worst_mm": round(worst[0], 6) if worst else None,
                "worst_pair": worst[1] if worst else None,
                "worst_pose_deg": round(worst[2], 4) if worst else None,
                "solver_target_mm": solver_target,
                "shortfall_mm": (
                    round(solver_target - worst[0], 6) if worst else None
                ),
            }
        )
        if worst and worst[0] >= solver_target:
            return required, changes, worst, per_tick, trail
        if worst is None:
            break
        required += (solver_target - worst[0]) / 1000.0
    return required, None, None, None, trail


def build(project_root, key, required):
    root, pivot = m2m.open_input(project_root, key)
    reference = m2m.semantic(root)
    changes = m2m.retract_ticks(root, pivot, required)
    actual = m2m.semantic(root)
    return root, pivot, changes, m2m.allowlist_diff(reference, actual)


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    keys = args.models or list(MODELS)

    fixtures = m2m1.self_test()
    if not fixtures["all_passed"]:
        raise SystemExit("[Opus5D3P] distance self-test failed")
    print(f"[Opus5D3P] distance self-test: {fixtures['cases']} cases PASS")

    started = time.perf_counter()
    staging = Path(tempfile.mkdtemp(prefix="opus5-d3p-"))
    entries = {}
    try:
        for key in keys:
            begin = time.perf_counter()
            source = m2m.input_blend(project_root, key)
            source_sha = m1.digest(source)
            required, changes, worst, per_tick, trail = solve(project_root, key)
            if worst is None:
                raise SystemExit(f"[Opus5D3P] {key}: solver did not converge")

            root, pivot, changes, diff = build(project_root, key, required)
            staged = staging / f"{key}.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True)

            audited = m2m.audit(project_root, key, staged, required, True)
            m1.open_blend(staged)
            saved_root = bpy.data.objects[m2k.MODELS[key]["root"]]
            saved_pivot = bpy.data.objects["needle_pivot"]
            saved_worst, saved_per_tick = worst_tick_distance(
                saved_root,
                saved_pivot,
                max(m2m.CLEARANCE_MM[key] * 3.0 / 1000.0, m2m1.SEARCH_FLOOR_M),
            )
            accept = m2m.CLEARANCE_MM[key] + ACCEPT_BAND_MM

            problems = []
            if not audited["pass"]:
                problems.append("audit")
            if not diff["pass"]:
                problems.append("semantic diff outside the allowlist")
            if saved_worst is None or saved_worst[0] < accept:
                problems.append(
                    f"saved clearance {saved_worst[0] if saved_worst else None} "
                    f"mm below the accept floor {accept} mm"
                )

            entries[key] = {
                "model": f"{m2k.THEME}/{key}",
                "input_revision": "B2P",
                "output_revision": OUTPUT_REVISION,
                "input": str(source.relative_to(project_root)),
                "input_sha256": source_sha,
                "input_report_sha256": m1.digest(m2m.input_report(project_root, key)),
                "superseded": {
                    "revision": "B2P_D3",
                    "reason": (
                        "frozen as history; its clearance fell short by an "
                        "oblique edge-to-edge margin"
                    ),
                },
                "contract_mm": m2m.CLEARANCE_MM[key],
                "solver_target_mm": m2m.CLEARANCE_MM[key] + GUARD_BAND_MM,
                "accept_floor_mm": accept,
                "guard_band_note": (
                    "20 um for authoring stability, accepted at 10 above the "
                    "contract; the contract itself is unchanged"
                ),
                "solver_trail": trail,
                "final_required_radius_mm": round(required * 1000.0, 6),
                "tick_changes": changes,
                "vertices_moved_total": sum(
                    entry["vertices_moved"] for entry in changes.values()
                ),
                "semantic_diff": diff,
                "in_memory_worst": {
                    "minimum_mm": round(worst[0], 6),
                    "pair": worst[1],
                    "pose_deg": round(worst[2], 4),
                },
                "saved_worst": (
                    {
                        "minimum_mm": round(saved_worst[0], 6),
                        "pair": saved_worst[1],
                        "pose_deg": round(saved_worst[2], 4),
                        "meets_accept_floor": saved_worst[0] >= accept,
                        "meets_contract": saved_worst[0] >= m2m.CLEARANCE_MM[key],
                    }
                    if saved_worst
                    else None
                ),
                "saved_per_tick": saved_per_tick,
                "staged_sha256": m1.digest(staged),
                "audit": audited,
                "problems": problems,
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
            print(
                f"[Opus5D3P] {key}: {len(trail) - 1} iterations, radius "
                f"{round(required * 1000.0, 4)} mm, saved worst "
                f"{round(saved_worst[0], 6)} mm (contract "
                f"{m2m.CLEARANCE_MM[key]}, floor {accept}), moved "
                f"{entries[key]['vertices_moved_total']} verts, problems "
                f"{problems}"
            )

        staged_paths = {key: staging / f"{key}.blend" for key in keys}
        audit39 = (
            {"skipped": True}
            if args.skip_39
            else m2m.run_39(
                project_root,
                {
                    **staged_paths,
                    "MeterRound": m2m.output_blend(project_root, "MeterRound", None),
                },
                (Path(args.trial_dir) / "audit_39.json")
                if args.trial_dir
                else (project_root / AUDIT_39),
            )
        )
        print(f"[Opus5D3P] 39-model audit: {audit39}")

        for key in keys:
            if args.skip_renders or entries[key]["problems"]:
                continue
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
                        m1.open_blend(staged_paths[k])
                        or bpy.data.objects[m2k.MODELS[k]["root"]]
                    ),
                ),
            }

        for key in keys:
            entry = entries[key]
            current = m1.digest(m2m.input_blend(project_root, key))
            entry["input_sha256_at_publish"] = current
            problems = list(entry["problems"])
            if current != entry["input_sha256"]:
                problems.append("input changed between build and publish")
            if not args.skip_39 and not audit39.get("pass"):
                problems.append("39-model audit did not pass")
            record = publish.publish(
                output_blend(project_root, key, args.trial_dir),
                output_report(project_root, key, args.trial_dir),
                {
                    "phase": "M2m2",
                    "defects": ["D-3", "D-6"],
                    "object": key,
                    "theme": m2k.THEME,
                    "revision": OUTPUT_REVISION,
                    "note": (
                        "Tick offset solved against the exact surface distance "
                        "(alignment 134.1), rebuilt from B2P each iteration."
                    ),
                    "distance_self_test": fixtures,
                    "audit_39": audit39,
                    **{
                        name: value
                        for name, value in entry.items()
                        if name != "problems"
                    },
                    "authoring_environment": blender_compat.provenance(),
                },
                problems,
                trial_dir=args.trial_dir,
                save_blend=lambda path, k=key: shutil.copy2(
                    staging / f"{k}.blend", path
                ),
                reopen_blend=lambda path: m1.open_blend(path),
            )
            entry["publish"] = record
            print(
                f"[Opus5D3P] {key}: {record['mode']} - {record['reason']}"
                + (
                    f" sha {record['blend_sha256'][:12]}"
                    if record.get("blend_sha256")
                    else ""
                )
            )
        print(f"[Opus5D3P] total {round(time.perf_counter() - started, 1)}s")
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
