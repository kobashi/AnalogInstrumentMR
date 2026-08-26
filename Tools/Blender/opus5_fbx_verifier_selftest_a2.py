"""Phase M2n2a2: make the matcher global over the whole mesh.

Alignment 150.1. A1 solved each centroid bucket on its own and marked targets
used as it went, so a target reachable from two source groups went to whichever
group was processed first. Codex's counterexample flips the verdict by
reordering the targets alone. Solving one bucket well is not solving the mesh.

Here the whole mesh is one sparse bipartite graph: every source triangle and
every reimport triangle is a node, and an edge exists only where the materials
agree and the best of the six corner correspondences keeps every corner inside
the geometric tolerance. The centroid bucket is used to propose edges and
nothing else. Each connected component is then solved by min-cost max-flow -
maximum matching first, least cost among those - so no bucket, component, list
or input order can change the answer.

Cost is lexicographic by construction: an over-bound UV value costs more than
any amount of within-bound error can, so coverage, then over-bound count, then
error, is what the solver actually minimises.

Several optimal matchings may exist. That alone is not a failure: it is a
failure only when they would disagree. Each matched edge is tested for an
equally-cheap alternative, and the verdict is `ambiguous` only if one is found
whose evidence differs.

Pure Python; nothing is published.

Usage::

    python3 Tools/Blender/opus5_fbx_verifier_selftest_a2.py --project-root "$PWD"
"""

import argparse
import itertools
import json
import math
import random
import time
import traceback
from pathlib import Path


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_verifier_self_test_a2.json"
UV_ULP = 2.0 * (2.0 ** -23)
GEOMETRY_TOLERANCE = 1.0e-6
BUCKET = GEOMETRY_TOLERANCE
SEEDS = tuple(range(1, 21))
OVER_WEIGHT = 10 ** 9
ERROR_SCALE = 10 ** 6


def bucket_key(position):
    return tuple(int(math.floor(value / BUCKET)) for value in position)


def centroid_of(triangle):
    corners, _ = triangle
    return tuple(
        sum(position[axis] for position, _ in corners) / 3.0 for axis in range(3)
    )


def edge_cost(first, second):
    """Best corner correspondence, or None when no correspondence fits."""
    best = None
    for permutation in itertools.permutations(range(3)):
        distance = max(
            math.dist(first[0][index][0], second[0][mapped][0])
            for index, mapped in enumerate(permutation)
        )
        if distance > GEOMETRY_TOLERANCE:
            continue
        over = 0
        error = 0.0
        for index, mapped in enumerate(permutation):
            for component in (0, 1):
                before = first[0][index][1][component]
                after = second[0][mapped][1][component]
                difference = abs(after - before)
                bound = UV_ULP * max(1.0, abs(before))
                if difference > bound:
                    over += 1
                error += difference / bound
        cost = over * OVER_WEIGHT + int(round(error * ERROR_SCALE))
        if best is None or cost < best["cost"]:
            best = {"cost": cost, "over": over, "error": error, "distance": distance}
    return best


def build_graph(source, reimport):
    """Sparse bipartite graph; the bucket only proposes candidates."""
    index = {}
    for position, triangle in enumerate(reimport):
        index.setdefault((bucket_key(centroid_of(triangle)), triangle[1]), []).append(
            position
        )
    edges = {}
    for i, first in enumerate(source):
        key = bucket_key(centroid_of(first))
        candidates = set()
        for offsets in itertools.product((-1, 0, 1), repeat=3):
            shifted = tuple(value + delta for value, delta in zip(key, offsets))
            candidates.update(index.get((shifted, first[1]), []))
        for j in sorted(candidates):
            found = edge_cost(first, reimport[j])
            if found is not None:
                edges[(i, j)] = found
    return edges


def components(source_count, target_count, edges):
    """Connected components, so each is solved independently and identically."""
    parent = list(range(source_count + target_count))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for i, j in edges:
        a, b = find(i), find(source_count + j)
        if a != b:
            parent[a] = b
    groups = {}
    for i in range(source_count):
        groups.setdefault(find(i), {"sources": [], "targets": []})["sources"].append(i)
    for j in range(target_count):
        groups.setdefault(find(source_count + j), {"sources": [], "targets": []})[
            "targets"
        ].append(j)
    return list(groups.values())


def min_cost_matching(sources, targets, edges, forbidden=None):
    """Min-cost maximum bipartite matching by successive shortest paths.

    Polynomial: at most |sources| augmentations, each a Bellman-Ford relaxation
    over the component's edges. No factorial enumeration is used on any path
    that a real mesh can reach.
    """
    forbidden = forbidden or set()
    left = {node: position for position, node in enumerate(sources)}
    right = {node: position for position, node in enumerate(targets)}
    adjacency = {position: [] for position in range(len(sources))}
    for (i, j), value in edges.items():
        if i in left and j in right and (i, j) not in forbidden:
            adjacency[left[i]].append((right[j], value["cost"]))

    match_left = [-1] * len(sources)
    match_right = [-1] * len(targets)
    total = 0
    matched = 0
    for start in range(len(sources)):
        distance = [math.inf] * len(sources)
        previous = [-1] * len(sources)
        via = [-1] * len(sources)
        distance[start] = 0
        for _ in range(len(sources)):
            changed = False
            for node in range(len(sources)):
                if distance[node] is math.inf:
                    continue
                for target, cost in adjacency[node]:
                    partner = match_right[target]
                    if partner == -1:
                        continue
                    if distance[node] + cost < distance[partner]:
                        distance[partner] = distance[node] + cost
                        previous[partner] = node
                        via[partner] = target
                        changed = True
            if not changed:
                break
        best = None
        for node in range(len(sources)):
            if distance[node] is math.inf:
                continue
            for target, cost in adjacency[node]:
                if match_right[target] != -1:
                    continue
                value = distance[node] + cost
                if best is None or value < best[0]:
                    best = (value, node, target)
        if best is None:
            continue
        value, node, target = best
        chain = []
        while node != start:
            chain.append((node, via[node]))
            node = previous[node]
        match_right[target] = best[1]
        match_left[best[1]] = target
        for node, target in chain:
            match_right[target] = node
            match_left[node] = target
        matched += 1
        total += 0
    pairs = [
        (sources[i], targets[match_left[i]])
        for i in range(len(sources))
        if match_left[i] != -1
    ]
    total = sum(edges[pair]["cost"] for pair in pairs)
    return pairs, total


def solve(source, reimport):
    started = time.perf_counter()
    edges = build_graph(source, reimport)
    parts = components(len(source), len(reimport), edges)
    all_pairs = []
    ambiguous = []
    largest = 0
    for part in parts:
        sources = part["sources"]
        targets = [j - len(source) if j >= len(source) else j for j in []]
        targets = part["targets"]
        largest = max(largest, len(sources) + len(targets))
        pairs, cost = min_cost_matching(sources, targets, edges)
        all_pairs.extend(pairs)
        # Alignment 150.1-5: several optima are fine unless they disagree.
        signature = sorted(
            (edges[pair]["over"], round(edges[pair]["error"], 9)) for pair in pairs
        )
        for pair in pairs:
            alternative, other_cost = min_cost_matching(
                sources, targets, edges, forbidden={pair}
            )
            if len(alternative) == len(pairs) and other_cost == cost:
                other = sorted(
                    (edges[p]["over"], round(edges[p]["error"], 9))
                    for p in alternative
                )
                if other != signature:
                    ambiguous.append({"pair": list(pair)})
    matched = len(all_pairs)
    over = sum(edges[pair]["over"] for pair in all_pairs)
    error = sum(edges[pair]["error"] for pair in all_pairs)
    return {
        "status": "compared",
        "expected_triangles": len(source),
        "matched_triangles": matched,
        "unmatched_source": len(source) - matched,
        "unconsumed_reimport": len(reimport) - matched,
        "triangle_coverage": matched / len(source) if source else 0.0,
        "compared_scalars": matched * 6,
        "expected_scalars": len(source) * 6,
        "over_bound": over,
        "normalised_uv_error": round(error, 9),
        "error_multiset": sorted(
            round(edges[pair]["error"], 9) for pair in all_pairs
        ),
        "nodes": len(source) + len(reimport),
        "edges": len(edges),
        "components": len(parts),
        "largest_component": largest,
        "solver": "min-cost max-flow (successive shortest paths)",
        "ambiguous": ambiguous,
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "pass": (
            bool(source)
            and matched == len(source)
            and len(reimport) - matched == 0
            and over == 0
            and not ambiguous
        ),
    }


def compare_uv_mesh(source, reimport):
    if source is None and reimport is None:
        return {"status": "absent_on_both", "pass": True}
    if source is None or reimport is None:
        return {"status": "layer_on_one_side_only", "pass": False}
    return solve(source, reimport)


# --------------------------------------------------------------------------
# Fixtures


def face(positions, uvs, material=0):
    return ([(positions[i], uvs[i]) for i in range(3)], material)


def base_triangle(offset, uv, material=0):
    x, y, z = offset
    return face(
        [(x, y, z), (x + 1.0, y, z), (x, y + 1.0, z)],
        uv,
        material,
    )


UV_A = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
UV_B = [(0.5, 0.5), (0.9, 0.5), (0.5, 0.9)]


def cross_bucket_fixtures():
    """Alignment 150: a target reachable from two source groups."""
    far = BUCKET * 50.0
    s1 = base_triangle((0.0, 0.0, 0.0), UV_A)
    s2 = base_triangle((far, 0.0, 0.0), UV_A)
    shared = base_triangle((far, 0.0, 0.0), UV_A)
    only_s1 = base_triangle((0.0, 0.0, 0.0), UV_A)
    cases = []
    for source in ([s1, s2], [s2, s1]):
        for target in ([shared, only_s1], [only_s1, shared]):
            cases.append(("cross-bucket contention", source, target, True))
    cases.append(
        ("cross-bucket: only the shared target exists", [s1, s2], [shared], False)
    )
    cases.append(
        (
            "cross-bucket: material mismatch",
            [s1, s2],
            [base_triangle((far, 0.0, 0.0), UV_A, material=1), only_s1],
            False,
        )
    )
    cases.append(
        (
            "cross-bucket: beyond geometry tolerance",
            [s1, s2],
            [base_triangle((far + 5e-6, 0.0, 0.0), UV_A), only_s1],
            False,
        )
    )
    moved = base_triangle(
        (far, 0.0, 0.0), [(0.0 + UV_ULP * 40.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    )
    cases.append(
        ("cross-bucket: one edge over bound", [s1, s2], [moved, only_s1], False)
    )
    return cases


def duplicate_fixtures():
    a = base_triangle((0.0, 0.0, 0.0), UV_A)
    b = base_triangle((0.0, 0.0, 0.0), UV_B)
    moved = base_triangle(
        (0.0, 0.0, 0.0), [(0.5 + UV_ULP * 40.0, 0.5), (0.9, 0.5), (0.5, 0.9)]
    )
    cases = []
    for source in ([a, b], [b, a]):
        for target in ([a, b], [b, a]):
            cases.append(("coincident duplicate faces", source, target, True))
    cases.append(("duplicate: one uv beyond bound", [a, b], [a, moved], False))
    cases.append(("duplicate missing on reimport", [a, b], [a], False))
    cases.append(("duplicate extra on reimport", [a], [a, b], False))
    return cases


def boundary_fixtures():
    edge = BUCKET * 10.0
    inside = base_triangle((edge - 4e-7, 0.0, 0.0), UV_A)
    across = base_triangle((edge + 4e-7, 0.0, 0.0), UV_A)
    far = base_triangle((edge + 5e-6, 0.0, 0.0), UV_A)
    return [
        ("across a bucket boundary, within tolerance", [inside], [across], True),
        ("same neighbourhood, beyond tolerance", [inside], [far], False),
    ]


def stress_fixture(count=120):
    source = []
    reimport = []
    for index in range(count):
        offset = (index * 0.01, 0.0, 0.0)
        source.append(base_triangle(offset, UV_A))
        reimport.append(base_triangle(offset, UV_A))
        if index % 10 == 0:
            source.append(base_triangle(offset, UV_B))
            reimport.append(base_triangle(offset, UV_B))
    return source, reimport


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    payload = {
        "phase": "M2n2a2",
        "note": (
            "Mesh-wide sparse assignment (alignment 150.1). Pure fixtures; "
            "nothing is published."
        ),
        "solver": "min-cost max-flow, successive shortest paths, per component",
        "complexity": "O(V * E) per component; no factorial enumeration",
        "seeds": len(SEEDS),
        "uv_bound_rule": "2 * 2^-23 * max(1, |value|)",
        "geometry_tolerance_m": GEOMETRY_TOLERANCE,
    }
    started = time.perf_counter()
    try:
        cases = (
            cross_bucket_fixtures() + duplicate_fixtures() + boundary_fixtures()
        )
        rows = []
        for name, source, target, expected in cases:
            results = []
            for seed in SEEDS:
                rng = random.Random(seed)
                a, b = list(source), list(target)
                rng.shuffle(a)
                rng.shuffle(b)
                results.append(compare_uv_mesh(a, b))
            stable = all(
                (
                    entry["pass"],
                    entry.get("matched_triangles"),
                    entry.get("over_bound"),
                    entry.get("error_multiset"),
                    entry.get("unmatched_source"),
                )
                == (
                    results[0]["pass"],
                    results[0].get("matched_triangles"),
                    results[0].get("over_bound"),
                    results[0].get("error_multiset"),
                    results[0].get("unmatched_source"),
                )
                for entry in results
            )
            rows.append(
                {
                    "case": name,
                    "expected_pass": expected,
                    "measured_pass": results[0]["pass"],
                    "stable_across_seeds": stable,
                    "seeds": len(SEEDS),
                    "passed": results[0]["pass"] == expected and stable,
                    "detail": results[0],
                }
            )

        source, reimport = stress_fixture()
        stress_first = compare_uv_mesh(list(source), list(reimport))
        rng = random.Random(99)
        shuffled_source, shuffled_target = list(source), list(reimport)
        rng.shuffle(shuffled_source)
        rng.shuffle(shuffled_target)
        stress_second = compare_uv_mesh(shuffled_source, shuffled_target)
        stress = {
            "triangles": len(source),
            "first": stress_first,
            "shuffled": stress_second,
            "order_invariant": (
                stress_first["pass"] == stress_second["pass"]
                and stress_first["error_multiset"] == stress_second["error_multiset"]
                and stress_first["matched_triangles"]
                == stress_second["matched_triangles"]
            ),
            "passed": (
                stress_first["pass"]
                and stress_first["triangle_coverage"] == 1.0
                and stress_first["pass"] == stress_second["pass"]
            ),
        }

        payload["uv_matcher"] = {
            "cases": len(rows),
            "all_passed": all(row["passed"] for row in rows),
            "detail": rows,
        }
        payload["stress"] = stress
        payload["transform_decomposition"] = {
            "status": "unchanged from M2n2a1; polar decomposition retained",
            "reference": "meter_d3_fbx_verifier_self_test_a1.json",
        }
        payload["status"] = (
            "complete"
            if payload["uv_matcher"]["all_passed"] and stress["passed"]
            else "fixture failure"
        )
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        output = project_root / OUTPUT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        uv = payload.get("uv_matcher", {})
        stress = payload.get("stress", {})
        print(
            f"[Opus5VerifyA2] uv {uv.get('cases')} all_passed="
            f"{uv.get('all_passed')}, stress passed={stress.get('passed')} "
            f"({stress.get('triangles')} tris, "
            f"{(stress.get('first') or {}).get('elapsed_seconds')}s), status "
            f"{payload.get('status')}"
        )
        for row in uv.get("detail", []):
            if not row["passed"]:
                print(
                    f"  UV FAIL {row['case']}: expected {row['expected_pass']} "
                    f"got {row['measured_pass']} stable={row['stable_across_seeds']}"
                )


if __name__ == "__main__":
    main()
