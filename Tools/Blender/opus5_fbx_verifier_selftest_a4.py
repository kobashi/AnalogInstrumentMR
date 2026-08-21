"""Phase M2n2a4: compare optima on the objective, not on an encoded scalar.

Alignment 154.1. A3's ambiguity test compared the encoded cost of the base
solve with the encoded cost of a solve that had one edge removed. Those two
runs derive their over-bound weight from their own edge sets, so the numbers
are not on the same scale and equality between them means nothing. Codex's
2x2 case makes it concrete: matchings with evidence (1,0)+(0,10) and
(1,5)+(0,5) share the objective (2 matched, 1 over-bound, error 10) and must be
reported ambiguous, but the encoded totals differ and A3 sees no tie at all.

So `solve_component` now returns the objective itself - cardinality,
over-bound total, scaled error total - together with the evidence multiset, and
every comparison is made on that tuple. The encoding stays an implementation
detail of one solve and never crosses between runs.

Two fixture debts from A3 are also paid: the case called "two optima with
different evidence" had only one optimum, so the rule it claimed to fix was
never exercised; and the mesh set had silently dropped `cross-bucket: one edge
over bound`.

Pure Python; nothing is published.

Usage::

    python3 Tools/Blender/opus5_fbx_verifier_selftest_a4.py --project-root "$PWD"
"""

import argparse
import itertools
import json
import math
import random
import time
import traceback
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from opus5_fbx_verifier_selftest_a3 import (  # noqa: E402
    BUCKET,
    ERROR_SCALE,
    GEOMETRY_TOLERANCE,
    UV_ULP,
    MinCostMaxFlow,
    base_triangle,
    bucket_key,
    build_graph,
    centroid_of,
    components,
    stress_fixture,
    UV_A,
    UV_B,
)


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_verifier_self_test_a4.json"
SEEDS = tuple(range(1, 21))


def solve_component(sources, targets, costs):
    """Returns the objective itself, not just an encoding of it.

    The encoded cost still orders the flow correctly inside this one solve, but
    it is derived from this edge set and is meaningless against another. What
    leaves the function is `(cardinality, over_bound, scaled_error)` plus the
    evidence multiset, and every caller compares those.
    """
    if not sources or not targets or not costs:
        return {
            "pairs": [],
            "objective": (0, 0, 0),
            "evidence": [],
            "augmentations": 0,
        }
    scaled = {
        pair: int(round(value["error"] * ERROR_SCALE)) for pair, value in costs.items()
    }
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
    _, _, augmentations = flow.run(source_node, sink_node)
    pairs = [pair for pair, index in edge_index.items() if flow.edges[index][1] == 0]
    evidence = sorted((costs[pair]["over"], scaled[pair]) for pair in pairs)
    objective = (
        len(pairs),
        sum(costs[pair]["over"] for pair in pairs),
        sum(scaled[pair] for pair in pairs),
    )
    return {
        "pairs": pairs,
        "objective": objective,
        "evidence": evidence,
        "augmentations": augmentations,
    }


def ambiguity(sources, targets, costs, solved):
    """Is there an equally optimal matching whose evidence differs?"""
    findings = []
    for pair in solved["pairs"]:
        restricted = {k: v for k, v in costs.items() if k != pair}
        other = solve_component(sources, targets, restricted)
        if other["objective"] == solved["objective"] and (
            other["evidence"] != solved["evidence"]
        ):
            findings.append(
                {
                    "forbidden_edge": list(pair),
                    "alternative_evidence": other["evidence"],
                }
            )
    return findings


def brute_force(sources, targets, costs):
    """Every matching, with the same objective the solver reports."""
    scaled = {
        pair: int(round(value["error"] * ERROR_SCALE)) for pair, value in costs.items()
    }
    best = None
    optima = []
    for size in range(min(len(sources), len(targets)), -1, -1):
        for chosen_sources in itertools.combinations(sources, size):
            for chosen_targets in itertools.permutations(targets, size):
                pairs = list(zip(chosen_sources, chosen_targets))
                if any(pair not in costs for pair in pairs):
                    continue
                objective = (
                    -len(pairs),
                    sum(costs[pair]["over"] for pair in pairs),
                    sum(scaled[pair] for pair in pairs),
                )
                if best is None or objective < best:
                    best = objective
                    optima = [pairs]
                elif objective == best:
                    optima.append(pairs)
        if best is not None:
            break
    evidence = [
        sorted((costs[pair]["over"], scaled[pair]) for pair in matching)
        for matching in optima
    ]
    distinct = {tuple(item) for item in evidence}
    return {
        "objective": None if best is None else (-best[0], best[1], best[2]),
        "optima": len(optima),
        "distinct_evidence": len(distinct),
        "ambiguous": len(distinct) > 1,
    }


# --------------------------------------------------------------------------
# Mesh comparison


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
        solved = solve_component(part["sources"], part["targets"], local)
        augmentations += solved["augmentations"]
        pairs.extend(solved["pairs"])
        ambiguous.extend(
            ambiguity(part["sources"], part["targets"], local, solved)
        )
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
# Fixtures


def cost(over, error):
    return {"over": over, "error": error, "distance": 0.0}


def solver_fixtures():
    return [
        {
            "case": "alignment 152: greedy takes S0-T0 and strands S1",
            "sources": [0, 1],
            "targets": [0, 1],
            "costs": {
                (0, 0): cost(0, 100.0),
                (0, 1): cost(0, 101.0),
                (1, 0): cost(0, 0.0),
            },
            "expected_optima": 1,
            "expected_ambiguous": False,
        },
        {
            "case": "augmenting path needs a reassignment",
            "sources": [0, 1, 2],
            "targets": [0, 1, 2],
            "costs": {
                (0, 0): cost(0, 1.0),
                (1, 0): cost(0, 2.0),
                (1, 1): cost(0, 3.0),
                (2, 1): cost(0, 4.0),
                (2, 2): cost(0, 5.0),
            },
            "expected_optima": 1,
            "expected_ambiguous": False,
        },
        {
            "case": "no perfect matching exists",
            "sources": [0, 1],
            "targets": [0],
            "costs": {(0, 0): cost(0, 1.0), (1, 0): cost(0, 2.0)},
            "expected_optima": 1,
            "expected_ambiguous": False,
        },
        {
            "case": "same cardinality, different over-bound counts",
            "sources": [0, 1],
            "targets": [0, 1],
            "costs": {
                (0, 0): cost(1, 0.0),
                (0, 1): cost(0, 5.0),
                (1, 0): cost(0, 0.0),
                (1, 1): cost(1, 0.0),
            },
            "expected_optima": 1,
            "expected_ambiguous": False,
        },
        {
            "case": "same over-bound, different error",
            "sources": [0, 1],
            "targets": [0, 1],
            "costs": {
                (0, 0): cost(0, 9.0),
                (0, 1): cost(0, 1.0),
                (1, 0): cost(0, 1.0),
                (1, 1): cost(0, 9.0),
            },
            # 9+9 against 1+1: the anti-diagonal is strictly cheaper, so there
            # is one optimum, not two. The case still does its job - the
            # solver has to prefer the cheaper matching - but the count was
            # my expectation, and it was wrong.
            "expected_optima": 1,
            "expected_ambiguous": False,
        },
        {
            "case": "two optima, identical evidence",
            "sources": [0, 1],
            "targets": [0, 1],
            "costs": {
                (0, 0): cost(0, 2.0),
                (0, 1): cost(0, 2.0),
                (1, 0): cost(0, 2.0),
                (1, 1): cost(0, 2.0),
            },
            "expected_optima": 2,
            "expected_ambiguous": False,
        },
        {
            # Alignment 154: same objective (2, 1, error 10), different
            # evidence. A3 compared encoded totals from two differently
            # weighted solves and saw no tie here at all.
            "case": "two optima, same objective, different evidence",
            "sources": [0, 1],
            "targets": [0, 1],
            "costs": {
                (0, 0): cost(1, 0.0),
                (0, 1): cost(1, 5.0),
                (1, 0): cost(0, 5.0),
                (1, 1): cost(0, 10.0),
            },
            "expected_optima": 2,
            "expected_ambiguous": True,
        },
    ]


def mesh_fixtures():
    far = BUCKET * 50.0
    s1 = base_triangle((0.0, 0.0, 0.0), UV_A)
    s2 = base_triangle((far, 0.0, 0.0), UV_A)
    shared = base_triangle((far, 0.0, 0.0), UV_A)
    only_s1 = base_triangle((0.0, 0.0, 0.0), UV_A)
    a = base_triangle((0.0, 0.0, 0.0), UV_A)
    b = base_triangle((0.0, 0.0, 0.0), UV_B)
    moved_dup = base_triangle(
        (0.0, 0.0, 0.0), [(0.5 + UV_ULP * 40.0, 0.5), (0.9, 0.5), (0.5, 0.9)]
    )
    moved_cross = base_triangle(
        (far, 0.0, 0.0), [(0.0 + UV_ULP * 40.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
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
        # Alignment 154: restored; A3 dropped it.
        (
            "cross-bucket: one edge over bound",
            [s1, s2],
            [moved_cross, only_s1],
            False,
        ),
        ("duplicate: one uv beyond bound", [a, b], [a, moved_dup], False),
        ("duplicate missing on reimport", [a, b], [a], False),
        ("duplicate extra on reimport", [a], [a, b], False),
        ("across a bucket boundary, within tolerance", [inside], [across], True),
        ("same neighbourhood, beyond tolerance", [inside], [beyond], False),
    ]
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    payload = {
        "phase": "M2n2a4",
        "note": (
            "Ambiguity and fixture closure (alignment 154.1). Pure fixtures; "
            "nothing is published."
        ),
        "comparison_rule": (
            "optima are compared on (cardinality, over_bound, scaled_error) "
            "and their evidence multiset; the encoded cost never crosses "
            "between solves"
        ),
        "solver": "min-cost max-flow over a residual network (unchanged from a3)",
        "seeds": len(SEEDS),
    }
    started = time.perf_counter()
    try:
        solver_rows = []
        for fixture in solver_fixtures():
            results = []
            for seed in SEEDS:
                rng = random.Random(seed)
                sources = list(fixture["sources"])
                targets = list(fixture["targets"])
                rng.shuffle(sources)
                rng.shuffle(targets)
                items = list(fixture["costs"].items())
                rng.shuffle(items)
                costs = dict(items)
                solved = solve_component(sources, targets, costs)
                found = ambiguity(sources, targets, costs, solved)
                results.append(
                    {
                        "objective": solved["objective"],
                        "evidence": solved["evidence"],
                        "ambiguous": bool(found),
                    }
                )
            oracle = brute_force(
                fixture["sources"], fixture["targets"], fixture["costs"]
            )
            first = results[0]
            stable = all(
                entry["objective"] == first["objective"]
                and entry["ambiguous"] == first["ambiguous"]
                for entry in results
            )
            solver_rows.append(
                {
                    "case": fixture["case"],
                    "expected_optima": fixture["expected_optima"],
                    "oracle_optima": oracle["optima"],
                    "oracle_distinct_evidence": oracle["distinct_evidence"],
                    "oracle_objective": list(oracle["objective"] or []),
                    "solver_objective": list(first["objective"]),
                    "expected_ambiguous": fixture["expected_ambiguous"],
                    "oracle_ambiguous": oracle["ambiguous"],
                    "solver_ambiguous": first["ambiguous"],
                    "stable_across_seeds": stable,
                    "passed": (
                        oracle["optima"] == fixture["expected_optima"]
                        and oracle["ambiguous"] == fixture["expected_ambiguous"]
                        and first["ambiguous"] == fixture["expected_ambiguous"]
                        and list(first["objective"]) == list(oracle["objective"])
                        and stable
                    ),
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

            def signature(entry):
                return (
                    entry["pass"],
                    entry.get("matched_triangles"),
                    entry.get("over_bound"),
                    entry.get("error_multiset"),
                    entry.get("unmatched_source"),
                    bool(entry.get("ambiguous")),
                )

            stable = all(signature(entry) == signature(first) for entry in results)
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
        payload["polar_transform"] = {
            "status": "unchanged; retained from a1",
            "reference": "meter_d3_fbx_verifier_self_test_a1.json",
        }
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
            f"[Opus5VerifyA4] solver {oracle.get('cases')} all_passed="
            f"{oracle.get('all_passed')}, uv {uv.get('cases')} all_passed="
            f"{uv.get('all_passed')}, stress {stress.get('passed')}, status "
            f"{payload.get('status')}"
        )
        for row in oracle.get("detail", []):
            if not row["passed"]:
                print(
                    f"  SOLVER FAIL {row['case']}: optima "
                    f"{row['oracle_optima']}/{row['expected_optima']} ambiguous "
                    f"oracle={row['oracle_ambiguous']} solver="
                    f"{row['solver_ambiguous']} expected="
                    f"{row['expected_ambiguous']} stable={row['stable_across_seeds']}"
                )
        for row in uv.get("detail", []):
            if not row["passed"]:
                print(
                    f"  UV FAIL {row['case']}: expected {row['expected_pass']} "
                    f"got {row['measured_pass']} stable={row['stable_across_seeds']}"
                )


if __name__ == "__main__":
    main()
