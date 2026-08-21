"""Phase M2n2a3: fix the solver itself, and check it against an oracle.

Alignment 152.1. The previous matcher's min-cost routine never built a residual
network: it relaxed forward edges only, with no negative reverse edge to undo a
choice, and its augmentation overwrote `match_left` instead of inverting an
alternating path. On Codex's 2x2 case - S0-T0=100, S0-T1=101, S1-T0=0 - it
returned a single pair and did not even reach maximum cardinality.

This replaces it with a textbook min-cost max-flow over a residual graph, and
then checks it the only way a solver should be checked: against brute-force
enumeration of every matching on graphs small enough to enumerate.

The lexicographic objective is no longer a guessed constant. Cardinality is
maximised first; among maximum matchings the over-bound count is minimised;
among those the UV error is minimised. The weight separating the last two is
derived per component from the sum of that component's own scaled errors, so
"one over-bound outweighs any amount of within-bound error" is arithmetic
rather than hope.

Pure Python; nothing is published.

Usage::

    python3 Tools/Blender/opus5_fbx_verifier_selftest_a3.py --project-root "$PWD"
"""

import argparse
import itertools
import json
import math
import random
import time
import traceback
from pathlib import Path


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_verifier_self_test_a3.json"
UV_ULP = 2.0 * (2.0 ** -23)
GEOMETRY_TOLERANCE = 1.0e-6
BUCKET = GEOMETRY_TOLERANCE
SEEDS = tuple(range(1, 21))
ERROR_SCALE = 10 ** 9


class MinCostMaxFlow:
    """Successive shortest paths over a residual network.

    Bellman-Ford is used rather than Dijkstra because the residual graph
    carries negative reverse edges by construction; the graph has no negative
    cycle, so the relaxation terminates. Each augmentation pushes one unit, so
    a bipartite matching needs at most min(|L|, |R|) of them, giving
    O(min(|L|,|R|) * V * E).
    """

    def __init__(self, size):
        self.size = size
        self.edges = []
        self.graph = [[] for _ in range(size)]

    def add(self, source, target, capacity, cost):
        self.graph[source].append(len(self.edges))
        self.edges.append([target, capacity, cost])
        self.graph[target].append(len(self.edges))
        self.edges.append([source, 0, -cost])

    def run(self, source, sink):
        flow = 0
        total = 0
        augmentations = 0
        while True:
            distance = [math.inf] * self.size
            previous = [-1] * self.size
            distance[source] = 0
            for _ in range(self.size):
                changed = False
                for node in range(self.size):
                    if distance[node] == math.inf:
                        continue
                    for index in self.graph[node]:
                        target, capacity, cost = self.edges[index]
                        if capacity <= 0:
                            continue
                        if distance[node] + cost < distance[target]:
                            distance[target] = distance[node] + cost
                            previous[target] = index
                            changed = True
                if not changed:
                    break
            if distance[sink] == math.inf:
                break
            node = sink
            while node != source:
                index = previous[node]
                self.edges[index][1] -= 1
                self.edges[index ^ 1][1] += 1
                node = self.edges[index ^ 1][0]
            flow += 1
            total += distance[sink]
            augmentations += 1
        return flow, total, augmentations


def solve_component(sources, targets, costs):
    """Maximum cardinality first, then over-bound, then error - exactly."""
    if not sources or not targets:
        return [], 0, 0, 0
    scaled = {
        pair: int(round(value["error"] * ERROR_SCALE)) for pair, value in costs.items()
    }
    # Proven, not assumed: no set of within-bound errors in this component can
    # add up to one over-bound, because the weight is their total plus one.
    weight = sum(scaled.values()) + 1
    size = len(sources) + len(targets) + 2
    source_node = len(sources) + len(targets)
    sink_node = source_node + 1
    flow = MinCostMaxFlow(size)
    left = {node: index for index, node in enumerate(sources)}
    right = {node: len(sources) + index for index, node in enumerate(targets)}
    for node in sources:
        flow.add(source_node, left[node], 1, 0)
    for node in targets:
        flow.add(right[node], sink_node, 1, 0)
    edge_index = {}
    for (i, j), value in costs.items():
        if i not in left or j not in right:
            continue
        edge_index[(i, j)] = len(flow.edges)
        flow.add(left[i], right[j], 1, value["over"] * weight + scaled[(i, j)])
    matched, total, augmentations = flow.run(source_node, sink_node)
    pairs = [
        pair for pair, index in edge_index.items() if flow.edges[index][1] == 0
    ]
    return pairs, total, matched, augmentations


def brute_force(sources, targets, costs):
    """Every matching, for graphs small enough that every matching is cheap."""
    best = None
    optima = []
    for size in range(min(len(sources), len(targets)), -1, -1):
        for chosen_sources in itertools.combinations(sources, size):
            for chosen_targets in itertools.permutations(targets, size):
                pairs = list(zip(chosen_sources, chosen_targets))
                if any(pair not in costs for pair in pairs):
                    continue
                over = sum(costs[pair]["over"] for pair in pairs)
                error = sum(costs[pair]["error"] for pair in pairs)
                key = (-len(pairs), over, round(error, 9))
                if best is None or key < best:
                    best = key
                    optima = [pairs]
                elif key == best:
                    optima.append(pairs)
        if best is not None:
            break
    return best, optima


# --------------------------------------------------------------------------
# Geometry and UV


def bucket_key(position):
    return tuple(int(math.floor(value / BUCKET)) for value in position)


def centroid_of(triangle):
    corners, _ = triangle
    return tuple(
        sum(position[axis] for position, _ in corners) / 3.0 for axis in range(3)
    )


def edge_cost(first, second):
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
        key = (over, error)
        if best is None or key < (best["over"], best["error"]):
            best = {"over": over, "error": error, "distance": distance}
    return best


def build_graph(source, reimport):
    index = {}
    for position, triangle in enumerate(reimport):
        index.setdefault(
            (bucket_key(centroid_of(triangle)), triangle[1]), []
        ).append(position)
    costs = {}
    for i, first in enumerate(source):
        key = bucket_key(centroid_of(first))
        candidates = set()
        for offsets in itertools.product((-1, 0, 1), repeat=3):
            shifted = tuple(value + delta for value, delta in zip(key, offsets))
            candidates.update(index.get((shifted, first[1]), []))
        for j in sorted(candidates):
            found = edge_cost(first, reimport[j])
            if found is not None:
                costs[(i, j)] = found
    return costs


def components(source_count, target_count, costs):
    parent = list(range(source_count + target_count))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for i, j in costs:
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


def compare_uv_mesh(source, reimport):
    if source is None and reimport is None:
        return {"status": "absent_on_both", "pass": True}
    if source is None or reimport is None:
        return {"status": "layer_on_one_side_only", "pass": False}

    started = time.perf_counter()
    costs = build_graph(source, reimport)
    parts = components(len(source), len(reimport), costs)
    pairs = []
    ambiguous = []
    largest = 0
    augmentations = 0
    for part in parts:
        local = {
            pair: value
            for pair, value in costs.items()
            if pair[0] in part["sources"] and pair[1] in part["targets"]
        }
        largest = max(largest, len(part["sources"]) + len(part["targets"]))
        chosen, total, matched, steps = solve_component(
            part["sources"], part["targets"], local
        )
        augmentations += steps
        pairs.extend(chosen)
        signature = sorted(
            (local[pair]["over"], round(local[pair]["error"], 9)) for pair in chosen
        )
        # Forbidding one chosen edge at a time is enough: any different optimal
        # matching must omit at least one edge this one uses, so it is found by
        # the run that forbids that edge.
        for pair in chosen:
            restricted = {k: v for k, v in local.items() if k != pair}
            other, other_total, other_matched, _ = solve_component(
                part["sources"], part["targets"], restricted
            )
            if other_matched == matched and other_total == total:
                other_signature = sorted(
                    (local[p]["over"], round(local[p]["error"], 9)) for p in other
                )
                if other_signature != signature:
                    ambiguous.append(list(pair))
    matched = len(pairs)
    over = sum(costs[pair]["over"] for pair in pairs)
    error = sum(costs[pair]["error"] for pair in pairs)
    return {
        "status": "compared",
        "expected_triangles": len(source),
        "matched_triangles": matched,
        "unmatched_source": len(source) - matched,
        "unconsumed_reimport": len(reimport) - matched,
        "triangle_coverage": matched / len(source) if source else 0.0,
        "over_bound": over,
        "normalised_uv_error": round(error, 9),
        "error_multiset": sorted(round(costs[pair]["error"], 9) for pair in pairs),
        "nodes": len(source) + len(reimport),
        "edges": len(costs),
        "components": len(parts),
        "largest_component": largest,
        "augmentations": augmentations,
        "solver": "min-cost max-flow over a residual network (SSP, Bellman-Ford)",
        "complexity": "O(min(|L|,|R|) * V * E) per component",
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


# --------------------------------------------------------------------------
# Solver fixtures


def solver_fixtures():
    def cost(over, error):
        return {"over": over, "error": error, "distance": 0.0}

    return [
        (
            "alignment 152: greedy takes S0-T0 and strands S1",
            [0, 1],
            [0, 1],
            {(0, 0): cost(0, 100.0), (0, 1): cost(0, 101.0), (1, 0): cost(0, 0.0)},
        ),
        (
            "augmenting path needs a reassignment",
            [0, 1, 2],
            [0, 1, 2],
            {
                (0, 0): cost(0, 1.0),
                (1, 0): cost(0, 2.0),
                (1, 1): cost(0, 3.0),
                (2, 1): cost(0, 4.0),
                (2, 2): cost(0, 5.0),
            },
        ),
        (
            "no perfect matching exists",
            [0, 1],
            [0],
            {(0, 0): cost(0, 1.0), (1, 0): cost(0, 2.0)},
        ),
        (
            "same cardinality, different over-bound counts",
            [0, 1],
            [0, 1],
            {
                (0, 0): cost(1, 0.0),
                (0, 1): cost(0, 5.0),
                (1, 0): cost(0, 0.0),
                (1, 1): cost(1, 0.0),
            },
        ),
        (
            "same over-bound, different error",
            [0, 1],
            [0, 1],
            {
                (0, 0): cost(0, 9.0),
                (0, 1): cost(0, 1.0),
                (1, 0): cost(0, 1.0),
                (1, 1): cost(0, 9.0),
            },
        ),
        (
            "two optima with identical evidence",
            [0, 1],
            [0, 1],
            {
                (0, 0): cost(0, 2.0),
                (0, 1): cost(0, 2.0),
                (1, 0): cost(0, 2.0),
                (1, 1): cost(0, 2.0),
            },
        ),
        (
            "two optima with different evidence",
            [0, 1],
            [0, 1],
            {
                (0, 0): cost(0, 1.0),
                (0, 1): cost(0, 3.0),
                (1, 0): cost(0, 3.0),
                (1, 1): cost(0, 1.0),
            },
        ),
    ]


# --------------------------------------------------------------------------
# Mesh fixtures reused from A2


def face(positions, uvs, material=0):
    return ([(positions[i], uvs[i]) for i in range(3)], material)


def base_triangle(offset, uv, material=0):
    x, y, z = offset
    return face([(x, y, z), (x + 1.0, y, z), (x, y + 1.0, z)], uv, material)


UV_A = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
UV_B = [(0.5, 0.5), (0.9, 0.5), (0.5, 0.9)]


def mesh_fixtures():
    far = BUCKET * 50.0
    s1 = base_triangle((0.0, 0.0, 0.0), UV_A)
    s2 = base_triangle((far, 0.0, 0.0), UV_A)
    shared = base_triangle((far, 0.0, 0.0), UV_A)
    only_s1 = base_triangle((0.0, 0.0, 0.0), UV_A)
    a = base_triangle((0.0, 0.0, 0.0), UV_A)
    b = base_triangle((0.0, 0.0, 0.0), UV_B)
    moved = base_triangle(
        (0.0, 0.0, 0.0), [(0.5 + UV_ULP * 40.0, 0.5), (0.9, 0.5), (0.5, 0.9)]
    )
    edge = BUCKET * 10.0
    inside = base_triangle((edge - 4e-7, 0.0, 0.0), UV_A)
    across = base_triangle((edge + 4e-7, 0.0, 0.0), UV_A)
    beyond = base_triangle((edge + 5e-6, 0.0, 0.0), UV_A)

    cases = []
    for source in ([s1, s2], [s2, s1]):
        for target in ([shared, only_s1], [only_s1, shared]):
            cases.append(("cross-bucket contention", source, target, True))
    for source in ([a, b], [b, a]):
        for target in ([a, b], [b, a]):
            cases.append(("coincident duplicate faces", source, target, True))
    cases += [
        ("cross-bucket: only the shared target", [s1, s2], [shared], False),
        (
            "cross-bucket: material mismatch",
            [s1, s2],
            [base_triangle((far, 0.0, 0.0), UV_A, material=1), only_s1],
            False,
        ),
        (
            "cross-bucket: beyond tolerance",
            [s1, s2],
            [base_triangle((far + 5e-6, 0.0, 0.0), UV_A), only_s1],
            False,
        ),
        ("duplicate: one uv beyond bound", [a, b], [a, moved], False),
        ("duplicate missing on reimport", [a, b], [a], False),
        ("duplicate extra on reimport", [a], [a, b], False),
        ("across a bucket boundary, within tolerance", [inside], [across], True),
        ("same neighbourhood, beyond tolerance", [inside], [beyond], False),
    ]
    return cases


def stress_fixture(count=120):
    source, reimport = [], []
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
        "phase": "M2n2a3",
        "note": (
            "Solver correctness closure (alignment 152.1). Pure fixtures; "
            "nothing is published."
        ),
        "solver": "min-cost max-flow over a residual network, successive shortest paths",
        "complexity": "O(min(|L|,|R|) * V * E) per component",
        "lexicographic": (
            "cardinality by max-flow; over-bound weighted above the sum of the "
            "component's own scaled errors plus one, so the ordering is proven "
            "per component rather than assumed from a constant"
        ),
        "error_scale": ERROR_SCALE,
        "seeds": len(SEEDS),
    }
    started = time.perf_counter()
    try:
        solver_rows = []
        for name, sources, targets, costs in solver_fixtures():
            pairs, total, matched, steps = solve_component(sources, targets, costs)
            best, optima = brute_force(sources, targets, costs)
            over = sum(costs[pair]["over"] for pair in pairs)
            error = sum(costs[pair]["error"] for pair in pairs)
            actual = (-len(pairs), over, round(error, 9))
            solver_rows.append(
                {
                    "case": name,
                    "oracle_optimum": list(best) if best else None,
                    "oracle_optima_count": len(optima),
                    "solver_result": list(actual),
                    "solver_pairs": [list(pair) for pair in sorted(pairs)],
                    "augmentations": steps,
                    "passed": best is not None and actual == tuple(best),
                }
            )

        mesh_rows = []
        for name, source, target, expected in mesh_fixtures():
            results = []
            for seed in SEEDS:
                rng = random.Random(seed)
                a, b = list(source), list(target)
                rng.shuffle(a)
                rng.shuffle(b)
                results.append(compare_uv_mesh(a, b))
            first = results[0]
            stable = all(
                (
                    entry["pass"],
                    entry.get("matched_triangles"),
                    entry.get("over_bound"),
                    entry.get("error_multiset"),
                    entry.get("unmatched_source"),
                )
                == (
                    first["pass"],
                    first.get("matched_triangles"),
                    first.get("over_bound"),
                    first.get("error_multiset"),
                    first.get("unmatched_source"),
                )
                for entry in results
            )
            mesh_rows.append(
                {
                    "case": name,
                    "expected_pass": expected,
                    "measured_pass": first["pass"],
                    "stable_across_seeds": stable,
                    "passed": first["pass"] == expected and stable,
                    "detail": first,
                }
            )

        source, reimport = stress_fixture()
        stress_first = compare_uv_mesh(list(source), list(reimport))
        rng = random.Random(99)
        a, b = list(source), list(reimport)
        rng.shuffle(a)
        rng.shuffle(b)
        stress_second = compare_uv_mesh(a, b)
        stress = {
            "triangles": len(source),
            "elapsed_seconds": stress_first["elapsed_seconds"],
            "coverage": stress_first["triangle_coverage"],
            "order_invariant": (
                stress_first["pass"] == stress_second["pass"]
                and stress_first["error_multiset"] == stress_second["error_multiset"]
            ),
            "passed": (
                stress_first["pass"]
                and stress_first["triangle_coverage"] == 1.0
                and stress_first["error_multiset"] == stress_second["error_multiset"]
            ),
        }

        payload["solver_oracle"] = {
            "cases": len(solver_rows),
            "all_passed": all(row["passed"] for row in solver_rows),
            "detail": solver_rows,
        }
        payload["uv_matcher"] = {
            "cases": len(mesh_rows),
            "all_passed": all(row["passed"] for row in mesh_rows),
            "detail": mesh_rows,
        }
        payload["stress"] = stress
        payload["ambiguity_rule"] = (
            "each chosen edge is forbidden in turn; any different optimal "
            "matching must omit at least one edge the chosen one uses, so it "
            "is reached by the run that forbids that edge"
        )
        payload["status"] = (
            "complete"
            if payload["solver_oracle"]["all_passed"]
            and payload["uv_matcher"]["all_passed"]
            and stress["passed"]
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
        oracle = payload.get("solver_oracle", {})
        uv = payload.get("uv_matcher", {})
        stress = payload.get("stress", {})
        print(
            f"[Opus5VerifyA3] solver {oracle.get('cases')} all_passed="
            f"{oracle.get('all_passed')}, uv {uv.get('cases')} all_passed="
            f"{uv.get('all_passed')}, stress {stress.get('passed')} "
            f"({stress.get('triangles')} tris, {stress.get('elapsed_seconds')}s), "
            f"status {payload.get('status')}"
        )
        for row in oracle.get("detail", []):
            if not row["passed"]:
                print(
                    f"  SOLVER FAIL {row['case']}: oracle "
                    f"{row['oracle_optimum']} solver {row['solver_result']}"
                )
        for row in uv.get("detail", []):
            if not row["passed"]:
                print(
                    f"  UV FAIL {row['case']}: expected {row['expected_pass']} "
                    f"got {row['measured_pass']} stable={row['stable_across_seeds']}"
                )


if __name__ == "__main__":
    main()
