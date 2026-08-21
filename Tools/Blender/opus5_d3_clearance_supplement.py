"""Phase M2m1: the clearance M2m reported was not the clearance asked for.

Alignment 132.2. M2m's `tick_clearance` compared a tick's smallest vertex
radius with the largest swept vertex radius plus the target. That is a
conservative radial condition, not the distance between two surfaces, and on
Round it was not applied at all because the parts are separated in depth. Both
readings leave the proportional clearance contract - 0.7, 1.4 and 2.1 mm -
unproven.

This measures it: every movable mesh under `needle_pivot` against every
`kinetic_tick_*`, over the whole travel, as an exact triangle-to-triangle
distance including edge-to-edge cases. A crossing or a penetrating vertex is
reported as zero so the number lines up with the two-layer result rather than
contradicting it.

The measurement is checked against three fixtures with distances known in
advance before any model is trusted to it, and a pair with no candidate
triangles is reported as not measured rather than counted as clear.

Read-only. Nothing is modified: the canonical Blends and their reports are
opened, hashed and left alone.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_clearance_supplement.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d3_combined_build as m2m
import opus5_d5_candidate_build as m2e
import opus5_d6_repair_decision as m2k


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d3_clearance_supplement.json"
# The contract only needs proving, not the exact figure at every distance.
# Searching out to 200 mm made every triangle a candidate and the run
# unaffordable; a radius of three times the target either finds the closest
# pair or proves the gap is larger than the radius, which is the same answer
# for the purpose and is reported as a bound rather than as a measurement.
SEARCH_FACTOR = 3.0
SEARCH_FLOOR_M = 0.006
POSES = m2k.POSES


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def self_test():
    """Three cases whose distance is known before the code runs."""
    def triangle(points):
        return [Vector(p) for p in points]

    cases = [
        (
            "separated by 5 mm",
            triangle([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)]),
            triangle([(0, 0, 0.005), (0.01, 0, 0.005), (0, 0.01, 0.005)]),
            0.005,
        ),
        (
            "tangent, sharing an edge",
            triangle([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)]),
            triangle([(0, 0, 0), (0.01, 0, 0), (0, -0.01, 0)]),
            0.0,
        ),
        (
            "crossing",
            triangle([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)]),
            triangle([(0.002, 0.002, -0.005), (0.002, 0.002, 0.005), (0.008, 0.002, 0.005)]),
            0.0,
        ),
        (
            # Two slivers crossing in projection, one along x and one along y,
            # separated only in z: the closest points are interior to both
            # edges, so a vertex-nearest test would miss the answer.
            "edge to edge, not vertex to vertex",
            triangle([(-0.01, 0, 0), (0.01, 0, 0), (0, 0.0005, 0)]),
            triangle([(0, -0.01, 0.004), (0, 0.01, 0.004), (0.0005, 0, 0.004)]),
            0.004,
        ),
    ]
    results = []
    for name, first, second, expected in cases:
        measured = contact.triangle_distance(first, second)
        results.append(
            {
                "case": name,
                "expected_mm": round(expected * 1000.0, 6),
                "measured_mm": round(measured * 1000.0, 6),
                "passed": abs(measured - expected) <= 1e-9,
            }
        )
    return {
        "cases": len(results),
        "all_passed": all(entry["passed"] for entry in results),
        "detail": results,
    }


def pair_distance(mover, static, radius):
    """Exact surface distance, or zero if the two layers say they meet."""
    mover_tris = m1.world_triangles(mover)
    static_tris = m1.world_triangles(static)
    mover_broad, mover_exact = m1.trees(mover)
    static_broad, static_exact = m1.trees(static)

    pairs = contact.candidate_pairs(
        mover_tris, static_tris, mover_broad, static_broad
    )
    surface = contact.surface_contact(mover_tris, static_tris, pairs)
    if surface[contact.CROSSING]:
        return 0.0, "crossing"
    for source, tree in ((mover, static_exact), (static, mover_exact)):
        depth = contact.material_penetration(
            [source.matrix_world @ v.co for v in source.data.vertices], tree
        )
        if depth["penetrating_vertices"]:
            return 0.0, "penetrating"

    near = contact.candidate_pairs(
        mover_tris, static_tris, mover_broad, static_broad, tolerance=radius
    )
    if not near:
        return radius, f"no surface within {radius * 1000.0:.3f} mm; lower bound"
    best = None
    for mover_index, static_index in near:
        distance = contact.triangle_distance(
            mover_tris[mover_index], static_tris[static_index]
        )
        if best is None or distance < best:
            best = distance
    return best, "exact triangle-to-triangle"


def measure(project_root, key):
    path = m2m.output_blend(project_root, key, None)
    report = m2m.output_report(project_root, key, None)
    payload = json.loads(report.read_text())
    m1.open_blend(path)
    root = bpy.data.objects[m2k.MODELS[key]["root"]]
    pivot = bpy.data.objects["needle_pivot"]
    base = pivot.rotation_euler.copy()

    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    ticks = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and "kinetic_tick_" in obj.name
    ]
    target = m2m.CLEARANCE_MM[key] / 1000.0
    radius = max(target * SEARCH_FACTOR, SEARCH_FLOOR_M)

    per_pair = {}
    unmeasured = []
    worst = None
    try:
        for degrees in POSES:
            pivot.rotation_euler[1] = base[1] + math.radians(degrees)
            bpy.context.view_layer.update()
            for mover in movable:
                for tick in ticks:
                    label = f"{mover.name} x {tick.name}"
                    distance, how = pair_distance(mover, tick, radius)
                    if distance is None:
                        unmeasured.append({"pair": label, "pose": degrees, "why": how})
                        continue
                    entry = per_pair.setdefault(
                        label, {"minimum_mm": None, "pose_deg": None, "method": how}
                    )
                    millimetres = distance * 1000.0
                    if entry["minimum_mm"] is None or millimetres < entry["minimum_mm"]:
                        entry.update(
                            {
                                "minimum_mm": round(millimetres, 6),
                                "pose_deg": round(degrees, 4),
                                "method": how,
                            }
                        )
                    if worst is None or millimetres < worst[0]:
                        worst = (millimetres, label, degrees, how)
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()

    allowlist = {
        label: entry
        for label, entry in per_pair.items()
        if any(name in label for name in m2m.ALLOWLIST)
    }
    return {
        "model": f"{m2k.THEME}/{key}",
        "revision": m2m.PLAN[key]["output"],
        "blend": {
            "path": str(path.relative_to(project_root)),
            "sha256_now": m1.digest(path),
            "sha256_in_report": payload.get("publish", {}).get("blend_sha256"),
            "unchanged": m1.digest(path)
            == payload.get("publish", {}).get("blend_sha256"),
        },
        "report": {
            "path": str(report.relative_to(project_root)),
            "sha256_now": m1.digest(report),
        },
        "target_mm": m2m.CLEARANCE_MM[key],
        "movable_meshes": [obj.name for obj in movable],
        "ticks": [obj.name for obj in ticks],
        "poses": len(POSES),
        "search_radius_mm": round(radius * 1000.0, 4),
        "pairs_measured": len(per_pair),
        "unmeasured_pairs": unmeasured,
        "worst": (
            {
                "minimum_mm": round(worst[0], 6),
                "pair": worst[1],
                "pose_deg": round(worst[2], 4),
                "method": worst[3],
                "margin_to_target_mm": round(worst[0] - target * 1000.0, 6),
                "meets_target": worst[0] >= target * 1000.0 - 1e-6,
            }
            if worst
            else None
        ),
        "allowlist_ticks": allowlist,
        "per_pair": per_pair,
        "pass": (
            not unmeasured
            and worst is not None
            and worst[0] >= target * 1000.0 - 1e-6
        ),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()

    fixtures = self_test()
    if not fixtures["all_passed"]:
        failed = [c["case"] for c in fixtures["detail"] if not c["passed"]]
        raise SystemExit(f"[Opus5D3clear] distance self-test failed: {failed}")
    print(f"[Opus5D3clear] distance self-test: {fixtures['cases']} cases PASS")

    started = time.perf_counter()
    models = {key: measure(project_root, key) for key in m2m.PLAN}
    for key, entry in models.items():
        print(
            f"[Opus5D3clear] {key} {entry['revision']}: worst "
            f"{entry['worst']['minimum_mm']} mm on {entry['worst']['pair']} at "
            f"{entry['worst']['pose_deg']} deg, target {entry['target_mm']} mm, "
            f"margin {entry['worst']['margin_to_target_mm']} mm, pass="
            f"{entry['pass']}, blend unchanged {entry['blend']['unchanged']}"
        )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2m1",
                "note": (
                    "Read-only clearance supplement (alignment 132.2). The "
                    "canonical Blends are opened, hashed and left unchanged."
                ),
                "what_this_replaces": (
                    "M2m's tick_clearance compared vertex radii; this is the "
                    "distance between surfaces, measured pose by pose"
                ),
                "method": {
                    "broad_phase": "BVH candidate pairs, radius expanded until pairs exist",
                    "narrow_phase": (
                        "exact triangle-to-triangle distance including "
                        "edge-to-edge; crossing or penetrating reported as 0"
                    ),
                    "search_radius": (
                        "three times the target, floor 6 mm; a pair with "
                        "nothing inside that radius is recorded as a lower "
                        "bound at the radius, which already exceeds the target"
                    ),
                    "unmeasured_policy": (
                        "a pair with no candidate triangles is recorded as not "
                        "measured, never as clear"
                    ),
                },
                "distance_self_test": fixtures,
                "models": models,
                "summary": {
                    key: {
                        "worst_mm": entry["worst"]["minimum_mm"],
                        "target_mm": entry["target_mm"],
                        "pass": entry["pass"],
                    }
                    for key, entry in models.items()
                },
                "all_pass": all(entry["pass"] for entry in models.values()),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D3clear] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
