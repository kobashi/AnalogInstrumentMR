"""Fixtures for the two-layer contact primitive.

Alignment 84.3. Every case is built from closed meshes at known geometry, so
the expected answer is arithmetic rather than opinion, and the two layers are
asserted separately: a pair can be surface-`tangent` and penetration-`clear`,
or surface-`separated` and fully penetrating - the containment case is exactly
that, and it is why one layer was never enough.

The scale case builds the same configuration at 1x and 2x and asserts the
millimetre classification is unchanged, which is what the normalised signed
distance buys (alignment 84.1).

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_contact_fixtures.py -- \
      --output <report.json>
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bmesh
import bpy
import math
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact as contact


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--evidence",
        help=(
            "Repo path to update when every case passes. Alignment 86.4: the "
            "fixture result is evidence for the re-audit, so it is only "
            "written on a full pass."
        ),
    )
    return parser.parse_args(args)


def bar(name, dimensions, location, rotation=(0.0, 0.0, 0.0)):
    """A closed rectangular prism, scaled then rotated then placed.

    The order matters and got this wrong once: baking the translation into the
    vertices and *then* setting `rotation_euler` rotates about the object
    origin, which swings the bar around the world origin instead of spinning it
    in place. Everything is baked here, in the right order.
    """
    obj = cube(name, 1.0, (0.0, 0.0, 0.0))
    rotator = Euler(rotation, "XYZ").to_matrix()
    for vertex in obj.data.vertices:
        scaled = Vector(
            (
                vertex.co.x * dimensions[0],
                vertex.co.y * dimensions[1],
                vertex.co.z * dimensions[2],
            )
        )
        vertex.co = rotator @ scaled + Vector(location)
    obj.data.update()
    return obj


def cube(name, size, location):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    box = bmesh.new()
    bmesh.ops.create_cube(box, size=size)
    bmesh.ops.translate(box, verts=box.verts, vec=Vector(location))
    box.to_mesh(mesh)
    box.free()
    return obj


def triangles_of(obj):
    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    return [
        [matrix @ obj.data.vertices[index].co for index in triangle.vertices]
        for triangle in obj.data.loop_triangles
    ]


def tree_of(obj, epsilon):
    """Broad-phase trees are inflated; measurement trees must not be.

    Alignment 84.4. The first version built both from one tree at 1e-5, and a
    10 micrometre inflation swallowed the 5 and 20 micrometre intrusions these
    fixtures exist to measure - `find_nearest` returned 0. Candidate gathering
    and measurement are separate jobs and get separate trees.
    """
    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    vertices = [tuple(matrix @ vertex.co) for vertex in obj.data.vertices]
    polygons = [tuple(t.vertices) for t in obj.data.loop_triangles]
    return BVHTree.FromPolygons(
        vertices, polygons, all_triangles=True, epsilon=epsilon
    )


def world_vertices(obj):
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def measure(a, b):
    """Both layers for one pair of closed meshes."""
    tri_a, tri_b = triangles_of(a), triangles_of(b)
    broad_a = tree_of(a, contact.BROAD_PHASE_EPSILON_M)
    broad_b = tree_of(b, contact.BROAD_PHASE_EPSILON_M)
    exact_a = tree_of(a, 0.0)
    exact_b = tree_of(b, 0.0)
    pairs = contact.candidate_pairs(tri_a, tri_b, broad_a, broad_b)
    surface = contact.surface_contact(tri_a, tri_b, pairs)
    # Both directions: whichever mesh has vertices inside the other, the
    # deepest reading is the penetration. Testing one way only misses the case
    # where the small part is the one doing the intruding.
    into_b = contact.material_penetration(world_vertices(a), exact_b)
    into_a = contact.material_penetration(world_vertices(b), exact_a)
    penetration = {
        key: max(into_b[key], into_a[key])
        for key in (
            "boundary_vertices",
            "within_tolerance_vertices",
            "penetrating_vertices",
            "raw_parity_hits",
            "deepest_intrusion_mm",
        )
    }
    crossing = len(surface[contact.CROSSING])
    overlap = None
    if crossing and not penetration["raw_parity_hits"]:
        # Sample the *intersection* of the two bounding boxes, not their union.
        # Over the union the grid was 4 mm wide across a 4 mm overlap and
        # stepped straight over it, reporting no shared volume where there is
        # plenty.
        points_a, points_b = world_vertices(a), world_vertices(b)
        low = [
            max(min(p[i] for p in points_a), min(p[i] for p in points_b))
            for i in range(3)
        ]
        high = [
            min(max(p[i] for p in points_a), max(p[i] for p in points_b))
            for i in range(3)
        ]
        if all(high[i] > low[i] for i in range(3)):
            overlap = contact.sampled_overlap(low, high, exact_a, exact_b)
    return {
        "candidate_pairs": len(pairs),
        "surface": {
            "separated": surface[contact.SEPARATED],
            "tangent": len(surface[contact.TANGENT]),
            "crossing": crossing,
        },
        "penetration": dict(penetration, a_into_b=into_b, b_into_a=into_a),
        "sampled_overlap": overlap,
        "verdict": contact.verdict(
            penetration, crossing, overlap, len(surface[contact.TANGENT])
        ),
    }


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)


def case_separation():
    clear_scene()
    a = cube("a", 0.02, (0.0, 0.0, 0.0))
    b = cube("b", 0.02, (0.1, 0.0, 0.0))
    return measure(a, b), {
        "candidate_pairs": 0,
        "tangent": 0,
        "surface_crossing": 0,
        "penetrating_vertices": 0,
        "boundary_vertices": 0,
        "verdict": "clear",
    }


def case_face_touch():
    clear_scene()
    a = cube("a", 0.02, (0.0, 0.0, 0.0))
    b = cube("b", 0.02, (0.02, 0.0, 0.0))
    return measure(a, b), {
        "tangent_at_least": 1,
        "surface_crossing": 0,
        "penetrating_vertices": 0,
        "verdict": "tangent_or_within_tolerance",
    }


def case_edge_touch():
    clear_scene()
    a = cube("a", 0.02, (0.0, 0.0, 0.0))
    b = cube("b", 0.02, (0.02, 0.02, 0.0))
    return measure(a, b), {
        "tangent_at_least": 1,
        "surface_crossing": 0,
        "penetrating_vertices": 0,
        "verdict": "tangent_or_within_tolerance",
    }


def case_vertex_touch():
    clear_scene()
    a = cube("a", 0.02, (0.0, 0.0, 0.0))
    b = cube("b", 0.02, (0.02, 0.02, 0.02))
    return measure(a, b), {
        "tangent_at_least": 1,
        "surface_crossing": 0,
        "penetrating_vertices": 0,
        "verdict": "tangent_or_within_tolerance",
    }


def case_coplanar_slide():
    clear_scene()
    a = cube("a", 0.02, (0.0, 0.0, 0.0))
    b = cube("b", 0.02, (0.02, 0.005, 0.0))
    return measure(a, b), {
        "tangent_at_least": 1,
        "surface_crossing": 0,
        "penetrating_vertices": 0,
        "verdict": "tangent_or_within_tolerance",
    }


def intruding_pair(scale, depth_m):
    """A small block whose end sits `depth_m` inside a larger one.

    Equal cubes were tried first and were the wrong fixture: their intruding
    vertices land exactly on the other cube's side faces, where inside/outside
    is genuinely undefined. Making the intruder smaller puts those vertices
    strictly in the interior, which is what the depth is meant to measure.
    """
    big = 0.02 * scale
    small = 0.006 * scale
    a = cube("a", big, (0.0, 0.0, 0.0))
    b = cube("b", small, (big / 2 - depth_m + small / 2, 0.0, 0.0))
    return a, b


def case_shallow_intrusion():
    clear_scene()
    # 5 micrometres in: reported, but inside the engineering tolerance.
    a, b = intruding_pair(1.0, 0.000005)
    return measure(a, b), {
        "surface_crossing_at_least": 1,
        "depth_between_mm": [0.004, 0.006],
        "verdict": "tangent_or_within_tolerance",
    }


def case_deep_intrusion():
    clear_scene()
    a, b = intruding_pair(1.0, 0.00002)
    return measure(a, b), {
        "surface_crossing_at_least": 1,
        "depth_between_mm": [0.019, 0.021],
        "verdict": "penetration",
    }


def case_oblique_crossing():
    clear_scene()
    a = cube("a", 0.02, (0.0, 0.0, 0.0))
    b = cube("b", 0.02, (0.012, 0.008, 0.006))
    b.rotation_euler = (0.4, 0.3, 0.2)
    bpy.context.view_layer.update()
    return measure(a, b), {
        "surface_crossing_at_least": 1,
        "penetrating_vertices_at_least": 1,
        "verdict": "penetration",
    }


def case_containment():
    """Fully inside, no surface crossing at all - the case one layer misses."""
    clear_scene()
    a = cube("a", 0.004, (0.0, 0.0, 0.0))
    b = cube("b", 0.05, (0.0, 0.0, 0.0))
    return measure(a, b), {
        "candidate_pairs": 0,
        "surface_crossing": 0,
        "penetrating_vertices_at_least": 1,
        "verdict": "penetration",
    }


def case_scale_invariance():
    clear_scene()
    a, b = intruding_pair(1.0, 0.00002)
    small = measure(a, b)
    clear_scene()
    # Same 20 micrometre intrusion on geometry twice the size: the millimetre
    # classification must not move.
    a, b = intruding_pair(2.0, 0.00002)
    large = measure(a, b)
    return {"at_1x": small, "at_2x": large}, {
        "same_verdict": small["verdict"] == large["verdict"],
        "verdict": "penetration",
        "depth_between_mm": [0.019, 0.021],
    }


def case_vertex_free_cross():
    """Two prisms crossing with neither one's vertices inside the other.

    Alignment 86.3. Vertex-depth alone reads `clear` here even though the two
    genuinely share volume, which is why the surface layer's crossing count and
    the sampled overlap both feed the verdict.
    """
    clear_scene()
    a = bar("a", (0.100, 0.004, 0.004), (0.0, 0.0, 0.0))
    b = bar("b", (0.004, 0.004, 0.100), (0.0, 0.0, 0.0))
    return measure(a, b), {
        "surface_crossing_at_least": 1,
        "penetrating_vertices": 0,
        "sampled_overlap_positive": True,
        "verdict": "penetration_unquantified",
    }


def case_reverse_vertex_to_face():
    """A static vertex touching the middle of a mover face, both orders.

    Alignment 88.1: the one-way proximity pass only asked about the mover's own
    vertices, so this configuration - where the touching vertex belongs to the
    other mesh and lands nowhere near a mover vertex or centroid - was never
    presented to the classifier.
    """
    clear_scene()
    plate = bar("plate", (0.060, 0.060, 0.004), (0.0, 0.0, 0.0))
    # Corner of the small block resting on the plate's top face, away from any
    # plate vertex.
    block = bar("block", (0.008, 0.008, 0.008), (0.011, 0.007, 0.002 + 0.004))
    forward = measure(plate, block)
    reverse = measure(block, plate)
    return {"forward": forward, "reverse": reverse}, {
        "order_invariant": True,
        "tangent_at_least": 1,
        "surface_crossing": 0,
        "verdict": "tangent_or_within_tolerance",
    }


def case_interior_edge_to_edge():
    """Two edges meeting at their middles, not at endpoints or centroids."""
    clear_scene()
    half_diagonal = 0.010 * math.sqrt(2.0) / 2.0
    lower = bar(
        "lower",
        (0.120, 0.010, 0.010),
        (0.0, 0.0, -half_diagonal),
        (math.radians(45.0), 0.0, 0.0),
    )
    upper = bar(
        "upper",
        (0.010, 0.120, 0.010),
        (0.0, 0.0, half_diagonal),
        (0.0, math.radians(45.0), 0.0),
    )
    bpy.context.view_layer.update()
    return measure(lower, upper), {
        "tangent_at_least": 1,
        "surface_crossing": 0,
        "penetrating_vertices": 0,
        "verdict": "tangent_or_within_tolerance",
    }


def case_verdict_crossing_no_depth():
    """Pure verdict: a crossing with nothing measured must not pass."""
    penetration = {
        "boundary_vertices": 0,
        "within_tolerance_vertices": 0,
        "penetrating_vertices": 0,
        "raw_parity_hits": 0,
        "deepest_intrusion_mm": 0.0,
    }
    return {
        "grid_zero": contact.verdict(penetration, 1, {"cells_in_both": 0}),
        "grid_missing": contact.verdict(penetration, 1, None),
    }, {"both": "penetration_unquantified"}


def case_verdict_boundary_only():
    penetration = {
        "boundary_vertices": 1,
        "within_tolerance_vertices": 0,
        "penetrating_vertices": 0,
        "raw_parity_hits": 1,
        "deepest_intrusion_mm": 0.00005,
    }
    return {
        "grid_zero": contact.verdict(penetration, 1, {"cells_in_both": 0}),
        "grid_missing": contact.verdict(penetration, 1, None),
    }, {"both": "penetration_unquantified"}


def case_verdict_within_tolerance():
    penetration = {
        "boundary_vertices": 0,
        "within_tolerance_vertices": 2,
        "penetrating_vertices": 0,
        "raw_parity_hits": 2,
        "deepest_intrusion_mm": 0.006,
    }
    return {
        "grid_zero": contact.verdict(penetration, 1, {"cells_in_both": 0}),
        "grid_missing": contact.verdict(penetration, 1, None),
    }, {"both": "tangent_or_within_tolerance"}


CASES = {
    "clear_separation": case_separation,
    "face_touch_zero_depth": case_face_touch,
    "edge_touch_zero_depth": case_edge_touch,
    "vertex_touch_zero_depth": case_vertex_touch,
    "coplanar_sliding_contact": case_coplanar_slide,
    "shallow_intrusion_0p005mm": case_shallow_intrusion,
    "intrusion_0p020mm": case_deep_intrusion,
    "oblique_crossing": case_oblique_crossing,
    "containment_no_surface_crossing": case_containment,
    "reverse_vertex_to_face_touch": case_reverse_vertex_to_face,
    "interior_edge_to_edge_touch": case_interior_edge_to_edge,
    "verdict_crossing_no_depth": case_verdict_crossing_no_depth,
    "verdict_boundary_only": case_verdict_boundary_only,
    "verdict_within_tolerance": case_verdict_within_tolerance,
    "vertex_free_cross_penetration": case_vertex_free_cross,
    "scale_invariance_1x_vs_2x": case_scale_invariance,
}


def check(name, measured, expected):
    """Assert the evidence, not just the verdict (alignment 86.4)."""
    if "both" in expected:
        return all(value == expected["both"] for value in measured.values())
    if expected.get("order_invariant"):
        forward, reverse = measured["forward"], measured["reverse"]
        if forward["surface"] != reverse["surface"]:
            return False
        if forward["verdict"] != reverse["verdict"]:
            return False
        measured = forward
    if name == "scale_invariance_1x_vs_2x":
        low, high = expected["depth_between_mm"]
        return (
            expected["same_verdict"]
            and measured["at_1x"]["verdict"] == expected["verdict"]
            and all(
                low <= side["penetration"]["deepest_intrusion_mm"] <= high
                for side in (measured["at_1x"], measured["at_2x"])
            )
        )
    surface = measured["surface"]
    penetration = measured["penetration"]
    checks = [
        ("candidate_pairs", lambda v: measured["candidate_pairs"] == v),
        ("tangent", lambda v: surface["tangent"] == v),
        ("tangent_at_least", lambda v: surface["tangent"] >= v),
        ("surface_crossing", lambda v: surface["crossing"] == v),
        ("surface_crossing_at_least", lambda v: surface["crossing"] >= v),
        ("penetrating_vertices", lambda v: penetration["penetrating_vertices"] == v),
        (
            "penetrating_vertices_at_least",
            lambda v: penetration["penetrating_vertices"] >= v,
        ),
        ("boundary_vertices", lambda v: penetration["boundary_vertices"] == v),
        (
            "depth_between_mm",
            lambda v: v[0] <= penetration["deepest_intrusion_mm"] <= v[1],
        ),
        (
            "sampled_overlap_positive",
            lambda v: bool((measured.get("sampled_overlap") or {}).get("cells_in_both"))
            == v,
        ),
    ]
    for key, test in checks:
        if key in expected and not test(expected[key]):
            return False
    return measured["verdict"] == expected["verdict"]


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    results = {}
    started = time.perf_counter()
    for name, builder in CASES.items():
        measured, expected = builder()
        passed = check(name, measured, expected)
        results[name] = {
            "measured": measured,
            "expected": expected,
            "passed": passed,
        }
        print(f"[Opus5ContactFixture] {name}: {'PASS' if passed else 'FAIL'}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "note": (
                    "Closed-mesh fixtures for the two-layer contact primitive "
                    "(alignment 84.3). Surface and penetration are asserted "
                    "separately; the containment case has no surface crossing "
                    "at all and full penetration."
                ),
                "tangent_tolerance_m": contact.TANGENT_TOLERANCE_M,
                "penetration_tolerance_mm": contact.PENETRATION_TOLERANCE_MM,
                "cases": results,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "candidate_filter": (
                    "BVHTree.overlap on inflated trees, plus a two-way "
                    "find_nearest_range coarse filter with an exact "
                    "triangle-triangle distance narrow phase (alignment 88.1)"
                ),
                "all_passed": all(case["passed"] for case in results.values()),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5ContactFixture] -> {output}")
    if not all(case["passed"] for case in results.values()):
        raise SystemExit("contact fixtures failed")
    if args.evidence:
        evidence = Path(args.evidence)
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(output.read_text(), encoding="utf-8")
        print(f"[Opus5ContactFixture] evidence -> {evidence}")


if __name__ == "__main__":
    main()
