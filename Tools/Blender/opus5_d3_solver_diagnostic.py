"""Phase M2m2a: why the tick offset stopped buying clearance.

Alignment 136.1. The solver assumed surface distance answers a radial offset
with slope one. That holds while the closest pair is a radial vertex-face
contact and fails the moment an oblique edge-to-edge pair takes over. Rather
than raise the iteration limit, this measures the response curve directly.

Eight offsets are tried independently - each one rebuilt from the approved
B2P, never from the previous attempt - and at each the closest pair is recorded
with both closest points, the separation split into radial, tangential and
depth components about the pivot, and the feature that produced it. That says
whether the curve rises, where it flattens, and which component stops moving.

Read-only. Nothing is published: no Blend, no report, no PNG, no 39-model
audit. The diagnostic JSON is written on every path, including failure.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_solver_diagnostic.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
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
import opus5_d5_candidate_build as m2e
import opus5_d6_repair_decision as m2k


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d3_exact_solver_diagnostic.json"
MODELS = ("MeterMedium", "MeterLarge")
OFFSETS_MM = (0.0, 0.005, 0.010, 0.020, 0.050, 0.100, 0.200, 0.500)
SOLVER_TARGET_MM = {"MeterMedium": 1.420, "MeterLarge": 2.120}
POSES = m2k.POSES


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append")
    return parser.parse_args(args)


def point_triangle_closest(point, triangle):
    """Same result as `contact.point_triangle_distance`, plus where it lands."""
    normal, offset = contact.plane_of(triangle)
    if normal is not None:
        projected = point - normal * (normal.dot(point) + offset)
        if contact._point_in_triangle(projected, triangle, normal):
            return (point - projected).length, projected
    best = None
    for index in range(3):
        landing = contact._closest_on_segment(
            point, triangle[index], triangle[(index + 1) % 3]
        )
        distance = (point - landing).length
        if best is None or distance < best[0]:
            best = (distance, landing)
    return best


def segment_segment_closest(p0, p1, q0, q1):
    """Same result as `contact.segment_segment_distance`, plus both points."""
    u, v, w = p1 - p0, q1 - q0, p0 - q0
    a, b, c = u.dot(u), u.dot(v), v.dot(v)
    d, e = u.dot(w), v.dot(w)
    denominator = a * c - b * b
    if denominator < 1e-18:
        s, t = 0.0, (e / c if c > 1e-18 else 0.0)
    else:
        s = (b * e - c * d) / denominator
        t = (a * e - b * d) / denominator
    s = max(0.0, min(1.0, s))
    t = max(0.0, min(1.0, t))
    first, second = p0 + u * s, q0 + v * t
    return (first - second).length, first, second


def closest_pair(first, second):
    """Distance plus both closest points and which feature produced them.

    Crossing triangles are asked about first. Enumerating vertex-face and
    edge-edge features finds the closest *disjoint* features, which for two
    triangles that actually intersect is not zero - the crossing fixture caught
    exactly that.
    """
    if contact.triangle_distance(first, second) <= 0.0:
        centroid_a = (first[0] + first[1] + first[2]) / 3.0
        centroid_b = (second[0] + second[1] + second[2]) / 3.0
        return 0.0, centroid_a, centroid_b, "crossing"
    best = None
    for index, point in enumerate(first):
        distance, landing = point_triangle_closest(point, second)
        if best is None or distance < best[0]:
            best = (distance, point.copy(), landing.copy(), f"vertex_a{index}_face_b")
    for index, point in enumerate(second):
        distance, landing = point_triangle_closest(point, first)
        if best is None or distance < best[0]:
            best = (distance, landing.copy(), point.copy(), f"vertex_b{index}_face_a")
    for i in range(3):
        for j in range(3):
            distance, on_a, on_b = segment_segment_closest(
                first[i], first[(i + 1) % 3], second[j], second[(j + 1) % 3]
            )
            if best is None or distance < best[0]:
                best = (distance, on_a.copy(), on_b.copy(), f"edge_a{i}_edge_b{j}")
    return best


def decompose(point_a, point_b, centre):
    """Split the gap into radial, tangential and depth about the pivot."""
    gap = point_b - point_a
    mid = (point_a + point_b) * 0.5
    radial = Vector((mid.x - centre.x, 0.0, mid.z - centre.z))
    if radial.length < 1e-12:
        radial = Vector((1.0, 0.0, 0.0))
    radial.normalize()
    tangential = Vector((-radial.z, 0.0, radial.x))
    depth = Vector((0.0, 1.0, 0.0))
    return {
        "radial_mm": round(gap.dot(radial) * 1000.0, 6),
        "tangential_mm": round(gap.dot(tangential) * 1000.0, 6),
        "depth_mm": round(gap.dot(depth) * 1000.0, 6),
        "dominant": max(
            (
                ("radial", abs(gap.dot(radial))),
                ("tangential", abs(gap.dot(tangential))),
                ("depth", abs(gap.dot(depth))),
            ),
            key=lambda item: item[1],
        )[0],
    }


def measure(root, pivot, centre, radius):
    """Worst pair over the travel, with everything needed to explain it."""
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
                mover_tris = m1.world_triangles(mover)
                mover_broad, mover_exact = m1.trees(mover)
                for tick in ticks:
                    tick_tris = m1.world_triangles(tick)
                    tick_broad, tick_exact = m1.trees(tick)
                    near = contact.candidate_pairs(
                        mover_tris, tick_tris, mover_broad, tick_broad,
                        tolerance=radius,
                    )
                    if not near:
                        continue
                    for mover_index, tick_index in near:
                        found = closest_pair(
                            mover_tris[mover_index], tick_tris[tick_index]
                        )
                        record = {
                            "distance_mm": round(found[0] * 1000.0, 6),
                            "pair": f"{mover.name} x {tick.name}",
                            "pose_deg": round(degrees, 4),
                            "mover_triangle": mover_index,
                            "tick_triangle": tick_index,
                            "closest_on_mover": [round(v, 7) for v in found[1]],
                            "closest_on_tick": [round(v, 7) for v in found[2]],
                            "feature": found[3],
                            "components": decompose(found[1], found[2], centre),
                        }
                        key = tick.name
                        if (
                            key not in per_tick
                            or record["distance_mm"] < per_tick[key]["distance_mm"]
                        ):
                            per_tick[key] = record
                        if worst is None or record["distance_mm"] < worst["distance_mm"]:
                            worst = record
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return worst, per_tick


def fixture_check():
    """The distance fixtures, plus the closest points and feature they imply."""
    def triangle(points):
        return [Vector(p) for p in points]

    cases = [
        (
            "separated by 5 mm",
            triangle([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)]),
            triangle([(0, 0, 0.005), (0.01, 0, 0.005), (0, 0.01, 0.005)]),
            0.005,
            "vertex",
        ),
        (
            "tangent, sharing an edge",
            triangle([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)]),
            triangle([(0, 0, 0), (0.01, 0, 0), (0, -0.01, 0)]),
            0.0,
            None,
        ),
        (
            "crossing",
            triangle([(0, 0, 0), (0.01, 0, 0), (0, 0.01, 0)]),
            triangle(
                [(0.002, 0.002, -0.005), (0.002, 0.002, 0.005), (0.008, 0.002, 0.005)]
            ),
            0.0,
            None,
        ),
        (
            # Two hairline slivers whose projections cross, with every apex
            # moved off the other's line. Fat triangles in parallel planes
            # cannot test this: there the 4 mm is reached by a whole family of
            # feature pairs at once, so the expected feature is ambiguous
            # rather than the measurement wrong - which is what the previous
            # two attempts here actually showed.
            "edge to edge, not vertex to vertex",
            triangle([(-0.01, 0, 0), (0.01, 0, 0), (0, 0.00001, 0)]),
            triangle(
                [
                    (0.002, -0.01, 0.004),
                    (0.002, 0.01, 0.004),
                    (0.00201, 0.005, 0.004),
                ]
            ),
            0.004,
            "edge",
        ),
    ]
    results = []
    for name, first, second, expected, feature in cases:
        distance, point_a, point_b, kind = closest_pair(first, second)
        results.append(
            {
                "case": name,
                "expected_mm": round(expected * 1000.0, 6),
                "measured_mm": round(distance * 1000.0, 6),
                "expected_feature": feature,
                "measured_feature": kind,
                "separation_matches": abs(distance - expected) <= 1e-9,
                "feature_matches": feature is None or kind.startswith(feature),
                "passed": abs(distance - expected) <= 1e-9
                and (feature is None or kind.startswith(feature)),
            }
        )
    return {
        "cases": len(results),
        "all_passed": all(entry["passed"] for entry in results),
        "detail": results,
    }


def sweep_model(project_root, key):
    target = m2m.CLEARANCE_MM[key]
    radius = max(target * 3.0 / 1000.0, m2m1.SEARCH_FLOOR_M)
    source = m2m.input_blend(project_root, key)
    entry = {
        "model": f"{m2k.THEME}/{key}",
        "input": str(source.relative_to(project_root)),
        "input_sha256": m1.digest(source),
        "input_report_sha256": m1.digest(m2m.input_report(project_root, key)),
        "contract_mm": target,
        "solver_target_mm": SOLVER_TARGET_MM[key],
        "offsets_mm": list(OFFSETS_MM),
        "points": [],
    }
    base_required = None
    for offset in OFFSETS_MM:
        begin = time.perf_counter()
        root, pivot = m2m.open_input(project_root, key)
        centre = pivot.matrix_world.translation.copy()
        if base_required is None:
            base_required = (
                m2m.swept_radius(root, pivot)["swept_radius_m"] + target / 1000.0
            )
        required = base_required + offset / 1000.0
        m2m.retract_ticks(root, pivot, required)
        worst, per_tick = measure(root, pivot, centre, radius)
        entry["points"].append(
            {
                "offset_mm": offset,
                "required_radius_mm": round(required * 1000.0, 6),
                "worst": worst,
                "per_tick": per_tick,
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
        )
        print(
            f"[Opus5D3diag] {key} offset {offset:.3f} mm -> "
            f"{worst['distance_mm'] if worst else None} mm, "
            f"{worst['feature'] if worst else '-'}, dominant "
            f"{worst['components']['dominant'] if worst else '-'}"
        )

    distances = [
        point["worst"]["distance_mm"] if point["worst"] else None
        for point in entry["points"]
    ]
    usable = [d for d in distances if d is not None]
    monotone = all(
        usable[i] <= usable[i + 1] + 1e-9 for i in range(len(usable) - 1)
    )
    bracket = None
    for index in range(len(entry["points"]) - 1):
        low, high = distances[index], distances[index + 1]
        if low is None or high is None:
            continue
        if low < SOLVER_TARGET_MM[key] <= high:
            bracket = {
                "lower_offset_mm": entry["points"][index]["offset_mm"],
                "lower_distance_mm": low,
                "upper_offset_mm": entry["points"][index + 1]["offset_mm"],
                "upper_distance_mm": high,
            }
            break
    entry.update(
        {
            "response": dict(zip(OFFSETS_MM, distances)),
            "monotone_non_decreasing": monotone,
            "bracket": bracket,
            "reaches_target_by_0.5mm": bool(usable) and usable[-1] >= SOLVER_TARGET_MM[key],
            "plateau_value_mm": max(usable) if usable else None,
            "dominant_at_largest_offset": (
                entry["points"][-1]["worst"]["components"]["dominant"]
                if entry["points"][-1]["worst"]
                else None
            ),
            "feature_at_largest_offset": (
                entry["points"][-1]["worst"]["feature"]
                if entry["points"][-1]["worst"]
                else None
            ),
            "dominant_pair_changes": sorted(
                {
                    point["worst"]["pair"]
                    for point in entry["points"]
                    if point["worst"]
                }
            ),
            "status": "measured",
        }
    )
    return entry


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    output = project_root / OUTPUT

    payload = {
        "phase": "M2m2a",
        "note": (
            "Read-only solver response diagnostic (alignment 136.1). No Blend, "
            "report, PNG or 39-model audit is produced."
        ),
        "models": {},
    }
    started = time.perf_counter()
    try:
        fixtures = fixture_check()
        payload["closest_point_self_test"] = fixtures
        if not fixtures["all_passed"]:
            payload["status"] = "self-test failed"
            return
        for key in args.models or MODELS:
            try:
                payload["models"][key] = sweep_model(project_root, key)
            except Exception:  # noqa: BLE001 - recorded, then re-raised path ends
                payload["models"][key] = {
                    "status": "exception",
                    "traceback": traceback.format_exc(),
                }
        payload["status"] = "complete"
    finally:
        # Alignment 136.1-1: written on every path, including failure.
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"[Opus5D3diag] {payload.get('status')} -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
