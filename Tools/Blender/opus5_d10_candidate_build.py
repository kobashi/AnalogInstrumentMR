"""Phase M2h: the ForgeBrass D5_D10 combined candidate.

Alignment 110.2. One edit, on one mesh datablock: the approved `seat_notch` is
cut into `ForgeBrass_toggle_v6_limit_stop_1` on a copy of the approved D-5
candidate. Nothing else in the file is touched, and the D-5 candidate itself is
not overwritten.

The source is pinned by hash. If the D-5 candidate on disk is not the revision
Codex approved, the run stops before it edits anything - a combined candidate
built on a different base would carry an approval it never earned.

Publishing reuses `opus5_publish.publish`: the guard decides whether anything
may be written, the Blend is staged and reopened before it is trusted, and the
report is promoted last as the commit marker. The audit runs on the staged file
rather than on memory, so what is certified is what will be promoted.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d10_candidate_build.py -- \
      --project-root "$PWD" [--trial-dir /tmp/somewhere]
"""

import argparse
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_baseline_contact_classification as m2f
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_candidate_build as m2e
import opus5_d5_faithful_slot_selection as m2c
import opus5_d10_limit_stop_design as m2g
import opus5_publish as publish


REPORT = "ArtSource/Blender/BrushUp/Opus5/d10_candidate_build_report.json"
REVISION = "D5_D10"
THEME = "ForgeBrass"
STOP = "ForgeBrass_toggle_v6_limit_stop_1"

# Alignment 110.2 pins the base revision by hash, not by filename.
SOURCE_SHA256 = "23fb15c5e31bfe2109dd3b363d4c750b6a8b09b055a442b6f2ef06bc49ef8fa4"

# Alignment 110.3-3, as approved in 110.1.
SEAT_HALF_WIDTH_MM = 6.4496
SEAT_FLOOR_Y_MM = -55.0568
SIDE_CLEARANCE_MM = 0.6
FLANK_DEPTH_MM = 9.0
EXPECTED_TRIANGLES = 134

POSES = m2g.POSES
RENDER_POSES = m2g.RENDER_POSES


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--trial-dir")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def candidate_path(project_root, trial_dir):
    name = f"BL_Toggle_{THEME}_V6_Opus5_{REVISION}_Retopo.blend"
    if trial_dir:
        return Path(trial_dir) / name
    return project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / name


def open_toggle(path):
    m1.open_blend(Path(path))
    root = next(
        obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_Toggle_")
    )
    return {
        "root": root,
        "pivot": bpy.data.objects["switch_pivot"],
        "switch": bpy.data.objects["switch"],
        "stop": bpy.data.objects[STOP],
        "other_stop": m2f.find(root, "limit_stop_0"),
        "ring": m2f.find(root, "retaining_ring"),
        "joint": m2f.find(root, "hemisphere"),
    }


def measure_seat(stop):
    """Read the seat back off the mesh instead of trusting the parameters."""
    points = [stop.matrix_world @ v.co for v in stop.data.vertices]
    floor = SEAT_FLOOR_Y_MM / 1000.0
    inside = [p for p in points if abs(p.y - floor) < 1e-6]
    flank = [p for p in points if p.y < floor - 1e-6]
    half_width = max((abs(p.x) for p in inside), default=None)
    return {
        "seat_floor_vertices": len(inside),
        "measured_floor_y_mm": (
            round(min(p.y for p in inside) * 1000.0, 4) if inside else None
        ),
        "measured_seat_half_width_mm": (
            round(half_width * 1000.0, 4) if half_width is not None else None
        ),
        "flank_vertices": len(flank),
        "measured_flank_front_y_mm": (
            round(min(p.y for p in flank) * 1000.0, 4) if flank else None
        ),
        "measured_flank_depth_mm": (
            round((max(p.y for p in points) - min(p.y for p in flank)) * 1000.0, 4)
            if flank
            else None
        ),
        "bounds_mm": {
            axis: [
                round(min(p[i] for p in points) * 1000.0, 4),
                round(max(p[i] for p in points) * 1000.0, 4),
            ]
            for i, axis in enumerate("xyz")
        },
    }


def seat_gate(stop, shaft_half_width_mm):
    measured = measure_seat(stop)
    health = m2e.m2b.mesh_health(stop)
    checks = {
        "seat_half_width": (
            measured["measured_seat_half_width_mm"] is not None
            and abs(measured["measured_seat_half_width_mm"] - SEAT_HALF_WIDTH_MM)
            <= 0.001
        ),
        "seat_floor_y": (
            measured["measured_floor_y_mm"] is not None
            and abs(measured["measured_floor_y_mm"] - SEAT_FLOOR_Y_MM) <= 0.001
        ),
        "side_clearance": (
            measured["measured_seat_half_width_mm"] is not None
            and abs(
                (measured["measured_seat_half_width_mm"] - shaft_half_width_mm)
                - SIDE_CLEARANCE_MM
            )
            <= 0.01
        ),
        "flank_depth": (
            measured["measured_flank_depth_mm"] is not None
            and abs(measured["measured_flank_depth_mm"] - FLANK_DEPTH_MM) <= 0.001
        ),
        "triangles": health["loop_triangles"] == EXPECTED_TRIANGLES,
    }
    return {
        **measured,
        "shaft_half_width_mm": shaft_half_width_mm,
        "expected": {
            "seat_half_width_mm": SEAT_HALF_WIDTH_MM,
            "seat_floor_y_mm": SEAT_FLOOR_Y_MM,
            "side_clearance_mm": SIDE_CLEARANCE_MM,
            "flank_depth_mm": FLANK_DEPTH_MM,
            "loop_triangles": EXPECTED_TRIANGLES,
        },
        "loop_triangles": health["loop_triangles"],
        "checks": checks,
        "pass": all(checks.values()),
    }


def health_gate(stop, before):
    health = m2e.m2b.mesh_health(stop)
    after = m2g.facts_of(stop)
    return {
        "closed": health["closed"],
        "normals_outward": health["normals_outward"],
        "degenerate_faces": health["degenerate_faces"],
        "identity": {
            "name": [before["name"], after["name"]],
            "parent": [before["parent"], after["parent"]],
            "matrix_world_equal": before["matrix_world"] == after["matrix_world"],
            "materials": [before["materials"], after["materials"]],
        },
        "pass": (
            health["closed"]
            and health["normals_outward"]
            and health["degenerate_faces"] == 0
            and before["name"] == after["name"]
            and before["parent"] == after["parent"]
            and before["matrix_world"] == after["matrix_world"]
            and before["materials"] == after["materials"]
        ),
    }


def contact_gate(scene):
    measured = m2g.sweep_pair(
        scene["pivot"], scene["switch"], scene["stop"], POSES
    )
    rest = measured[0.0]
    reentry = sorted(
        pose
        for pose, entry in measured.items()
        if pose > 0.0
        and (entry["surface_crossing"] > 0 or entry["penetrating_vertices"] > 0)
    )
    separation = rest["minimum_separation_mm"]
    return {
        "per_pose": measured,
        "rest_separation_mm": separation,
        "band_mm": list(m2g.REST_SEPARATION_BAND_MM),
        "rest_surface_crossing": rest["surface_crossing"],
        "rest_penetrating_vertices": rest["penetrating_vertices"],
        "reentry_poses": reentry,
        "pass": (
            rest["surface_crossing"] == 0
            and rest["penetrating_vertices"] == 0
            and separation is not None
            and m2g.REST_SEPARATION_BAND_MM[0]
            <= separation
            <= m2g.REST_SEPARATION_BAND_MM[1]
            and not reentry
        ),
    }


def regression_gate(scene, source_regression):
    components = m2g.component_sweep(scene, POSES)
    current = m2g.regression(scene, POSES)
    new_contacts = [
        label
        for label, entry in current.items()
        if not entry["clear"]
        and not entry["named_allowance"]
        and (label not in source_regression or source_regression[label]["clear"])
    ]
    worsened = [
        label
        for label, entry in current.items()
        if label in source_regression
        and entry["deepest_intrusion_mm"]
        > source_regression[label]["deepest_intrusion_mm"] + 1e-6
    ]
    ring_pairs = {
        label: entry
        for label, entry in current.items()
        if "retaining_ring" in label and label.startswith("switch x")
    }
    return {
        "components": components,
        "components_clear": all(entry["clear"] for entry in components.values()),
        "new_contacts": new_contacts,
        "worsened_pairs": worsened,
        "d5_ring_pairs_clear": all(entry["clear"] for entry in ring_pairs.values()),
        "named_allowances": {
            label: {
                "source_mm": source_regression[label]["deepest_intrusion_mm"],
                "candidate_mm": entry["deepest_intrusion_mm"],
            }
            for label, entry in current.items()
            if entry["named_allowance"] and label in source_regression
        },
        "pass": (
            all(entry["clear"] for entry in components.values())
            and not new_contacts
            and not worsened
            and all(entry["clear"] for entry in ring_pairs.values())
        ),
    }


def render_states(project_root, states):
    directory = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    directory.mkdir(parents=True, exist_ok=True)
    written = {}
    for label, path in states.items():
        scene = open_toggle(path)
        # The state is already in the name; repeating it in the note gave
        # captions that read "COMBINED D5 D10 D5 D10".
        written[label] = m2g.render_option(
            project_root, f"combined_{label}", scene, ""
        )
    return written


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    source = m2e.candidate_path(project_root, THEME, None)
    production = m2c.source_blend(project_root, THEME)
    report_path = (
        Path(args.trial_dir) / "d10_candidate_build_report.json"
        if args.trial_dir
        else project_root / REPORT
    )
    target = candidate_path(project_root, args.trial_dir)

    source_sha = m1.digest(source)
    if source_sha != SOURCE_SHA256:
        raise SystemExit(
            f"[Opus5D10Build] source is not the approved D-5 candidate: "
            f"{source_sha} != {SOURCE_SHA256}"
        )

    started = time.perf_counter()

    # The source's own numbers, for the comparison the gates are stated against.
    scene = open_toggle(source)
    centre = scene["pivot"].matrix_world.translation.copy()
    envelope = m2g.shaft_envelope(scene["switch"], centre)
    shaft_half_width_mm = round(envelope["x"][1] * 1000.0, 4)
    stop_before = m2g.facts_of(scene["stop"])
    inventory_before = m2e.inventory(scene["root"])
    source_regression = m2g.regression(scene, POSES)

    # One edit.
    m2g.notch_seat(
        scene["stop"], SEAT_HALF_WIDTH_MM / 1000.0, SEAT_FLOOR_Y_MM / 1000.0
    )
    inventory_after = m2e.inventory(scene["root"])

    staging = Path(tempfile.mkdtemp(prefix="opus5-d10-"))
    try:
        staged = staging / "candidate.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True)
        if not staged.is_file():
            raise publish.PublishFailed("nothing was staged")

        # Everything below is measured on the file, not on memory.
        scene = open_toggle(staged)
        delta = m2e.inventory_delta(inventory_before, inventory_after)
        difference_gate = {
            "added": delta["added"],
            "removed": delta["removed"],
            "changed": sorted(delta["changed"]),
            "pass": (
                not delta["added"]
                and not delta["removed"]
                and sorted(delta["changed"]) == [STOP]
            ),
        }
        seat = seat_gate(scene["stop"], shaft_half_width_mm)
        health = health_gate(scene["stop"], stop_before)
        contacts = contact_gate(scene)
        regression = regression_gate(scene, source_regression)

        # Every object reference dies the moment a render loads another file,
        # so everything read off the scene is turned into plain data first.
        stop_after = m2g.facts_of(scene["stop"])
        staged_sha = m1.digest(staged)

        gates = {
            "difference_is_one_object": difference_gate,
            "seat_parameters": seat,
            "stop_mesh_health": health,
            "contact_over_travel": contacts,
            "regression": regression,
        }
        problems = [name for name, entry in gates.items() if not entry["pass"]]

        renders = {}
        if not args.skip_renders and not problems:
            renders = render_states(
                project_root,
                {
                    "production": production,
                    "d5": source,
                    "d5_d10": staged,
                },
            )

        report = {
            "phase": "M2h",
            "revision": REVISION,
            "defects": ["D-5", "D-10"],
            "note": (
                "Combined candidate (alignment 110.2). The approved seat_notch "
                "is applied to one mesh datablock on a copy of the approved "
                "D-5 candidate; nothing else is edited and no existing "
                "artifact is overwritten."
            ),
            "source": {
                "path": str(source.relative_to(project_root)),
                "sha256": source_sha,
                "pinned_sha256": SOURCE_SHA256,
                "matches_approved_revision": True,
            },
            "production_baseline": {
                "path": str(production.relative_to(project_root)),
                "sha256": m1.digest(production),
            },
            "staged_sha256": staged_sha,
            "shaft_envelope_mm": {
                axis: [
                    round(envelope[axis][0] * 1000.0, 4),
                    round(envelope[axis][1] * 1000.0, 4),
                ]
                for axis in "xyz"
            },
            "stop_before": stop_before,
            "stop_after": stop_after,
            "gates": gates,
            "problems": problems,
            "renders": renders,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "authoring_environment": blender_compat.provenance(),
        }

        record = publish.publish(
            target,
            report_path,
            report,
            problems,
            trial_dir=args.trial_dir,
            save_blend=lambda path: shutil.copy2(staged, path),
            reopen_blend=lambda path: open_toggle(path),
        )
        print(
            f"[Opus5D10Build] gates "
            f"{ {name: entry['pass'] for name, entry in gates.items()} }"
        )
        print(
            f"[Opus5D10Build] rest separation {contacts['rest_separation_mm']} mm, "
            f"triangles {seat['loop_triangles']}, {record['mode']}: "
            f"{record['reason']}"
        )
        if record.get("blend_sha256"):
            promoted = m1.digest(target)
            print(
                f"[Opus5D10Build] promoted {promoted[:12]} "
                f"(staged {record['blend_sha256'][:12]}, match "
                f"{promoted == record['blend_sha256']})"
            )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
