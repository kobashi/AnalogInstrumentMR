"""Phase M2n2a5: decide evidence equivalence without enumerating optima.

Alignment 156.1. Forbidding one chosen edge at a time and looking at the single
matching that comes back is not a proof. When the restricted graph has several
optima of its own, the solver may hand back one whose evidence matches the
baseline and the differing one is never seen. Codex's 4x4 case does exactly
that: five optimal matchings, two distinct evidence multisets, and the
edge-forbidding test reports no ambiguity at all.

So the question is asked directly instead. For each evidence category - a
distinct `(over_bound, scaled_error)` pair among the component's edges - the
smallest and largest number of times that category can appear in an optimal
matching is computed, by solving twice more with the category count as a
tie-break below the canonical objective. If any category can vary, two optimal
matchings differ in evidence and the result is ambiguous; if none can, every
optimum carries the same evidence and they are equivalent.

The tie-break weight is derived, not chosen: the primary cost is multiplied by
one more than the largest possible matching, so a single unit of primary
objective always outweighs any achievable category count.

Pure Python; nothing is published.

Usage::

    python3 Tools/Blender/opus5_fbx_verifier_selftest_a5.py --project-root "$PWD"
"""

import argparse
import itertools
import json
import random
import time
import traceback
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from opus5_fbx_verifier_selftest_a3 import (  # noqa: E402
    ERROR_SCALE,
    MinCostMaxFlow,
    build_graph,
    components,
    stress_fixture,
)
from opus5_fbx_verifier_selftest_a4 import (  # noqa: E402
    brute_force,
    cost,
    mesh_fixtures,
    solve_component,
    solver_fixtures,
)


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_verifier_self_test_a5.json"
SEEDS = tuple(range(1, 21))
CORPUS_SEED = 20260813
CORPUS_SIZE = 1000


def scaled_costs(costs):
    return {
        pair: int(round(value["error"] * ERROR_SCALE))
        for pair, value in costs.items()
    }


def solve_with(sources, targets, costs, extra):
    """One solve whose cost is the primary objective plus a tie-break."""
    scaled = scaled_costs(costs)
    weight = sum(scaled.values()) + 1
    limit = min(len(sources), len(targets))
    multiplier = limit + 1
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
    index_of = {}
    for pair, value in costs.items():
        if pair[0] not in left or pair[1] not in right:
            continue
        primary = value["over"] * weight + scaled[pair]
        index_of[pair] = len(flow.edges)
        flow.add(
            left[pair[0]],
            right[pair[1]],
            1,
            primary * multiplier + extra(pair),
        )
    flow.run(source_node, sink_node)
    pairs = [pair for pair, index in index_of.items() if flow.edges[index][1] == 0]
    objective = (
        len(pairs),
        sum(costs[pair]["over"] for pair in pairs),
        sum(scaled[pair] for pair in pairs),
    )
    evidence = sorted((costs[pair]["over"], scaled[pair]) for pair in pairs)
    return pairs, objective, evidence


def evidence_ambiguity(sources, targets, costs, solved):
    """Can any evidence category appear a different number of times?"""
    if not solved["pairs"]:
        return [], {"categories": 0, "solves": 0}
    scaled = scaled_costs(costs)
    categories = sorted({(costs[pair]["over"], scaled[pair]) for pair in costs})
    findings = []
    solves = 0
    for category in categories:
        def inside(pair, category=category):
            return (costs[pair]["over"], scaled[pair]) == category

        _, low_objective, low_evidence = solve_with(
            sources, targets, costs, lambda pair: 1 if inside(pair) else 0
        )
        _, high_objective, high_evidence = solve_with(
            sources, targets, costs, lambda pair: 0 if inside(pair) else 1
        )
        solves += 2
        if low_objective != solved["objective"] or high_objective != solved["objective"]:
            # A tie-break must never move the primary objective; if it did, the
            # derivation of the multiplier is wrong and that is worth failing on.
            findings.append(
                {
                    "category": list(category),
                    "reason": "tie-break changed the canonical objective",
                    "low_objective": list(low_objective),
                    "high_objective": list(high_objective),
                }
            )
            continue
        low = sum(1 for item in low_evidence if item == category)
        high = sum(1 for item in high_evidence if item == category)
        if low != high:
            findings.append(
                {
                    "category": list(category),
                    "min_count": low,
                    "max_count": high,
                }
            )
    return findings, {"categories": len(categories), "solves": solves}


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
    categories = 0
    extra_solves = 0
    for part in parts:
        local = {
            pair: value
            for pair, value in costs.items()
            if pair[0] in part["sources"] and pair[1] in part["targets"]
        }
        solved = solve_component(part["sources"], part["targets"], local)
        pairs.extend(solved["pairs"])
        findings, stats = evidence_ambiguity(
            part["sources"], part["targets"], local, solved
        )
        ambiguous.extend(findings)
        categories += stats["categories"]
        extra_solves += stats["solves"]
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
        "error_multiset": sorted(round(costs[pair]["error"], 9) for pair in pairs),
        "components": len(parts),
        "evidence_categories": categories,
        "ambiguity_solves": extra_solves,
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


def counterexample_4x4():
    table = {
        (0, 0): (0, 0), (0, 1): (0, 3), (0, 2): (1, 3), (0, 3): (1, 0),
        (1, 0): (0, 0), (1, 1): (1, 3), (1, 2): (1, 3), (1, 3): (1, 2),
        (2, 0): (1, 1), (2, 1): (0, 0), (2, 2): (1, 2), (2, 3): (0, 2),
        (3, 0): (0, 3), (3, 1): (0, 0), (3, 2): (1, 0), (3, 3): (0, 2),
    }
    return {
        "case": "alignment 156: 4x4, five optima, two evidence multisets",
        "sources": [0, 1, 2, 3],
        "targets": [0, 1, 2, 3],
        "costs": {pair: cost(over, error) for pair, (over, error) in table.items()},
        "expected_optima": 5,
        "expected_distinct_evidence": 2,
        "expected_ambiguous": True,
    }


def random_graph(rng, size):
    costs = {}
    for i in range(size):
        for j in range(size):
            if rng.random() < 0.7:
                costs[(i, j)] = cost(rng.randint(0, 1), float(rng.randint(0, 3)))
    return list(range(size)), list(range(size)), costs


def run_corpus(count):
    rng = random.Random(CORPUS_SEED)
    mismatches = []
    largest = 0
    started = time.perf_counter()
    for index in range(count):
        size = 3 if index % 2 == 0 else 4
        sources, targets, costs = random_graph(rng, size)
        if not costs:
            continue
        solved = solve_component(sources, targets, costs)
        findings, _ = evidence_ambiguity(sources, targets, costs, solved)
        oracle = brute_force(sources, targets, costs)
        largest = max(largest, oracle["optima"])
        if bool(findings) != oracle["ambiguous"]:
            mismatches.append(
                {
                    "index": index,
                    "size": size,
                    "oracle_ambiguous": oracle["ambiguous"],
                    "solver_ambiguous": bool(findings),
                    "costs": {
                        f"{k[0]},{k[1]}": [v["over"], v["error"]]
                        for k, v in costs.items()
                    },
                }
            )
    return {
        "seed": CORPUS_SEED,
        "graphs": count,
        "sizes": [3, 4],
        "edge_probability": 0.7,
        "largest_optima_seen": largest,
        "mismatches": mismatches,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "pass": not mismatches,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--corpus", type=int, default=CORPUS_SIZE)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    payload = {
        "phase": "M2n2a5",
        "note": (
            "Evidence-equivalence closure (alignment 156.1). Pure fixtures; "
            "nothing is published."
        ),
        "ambiguity_rule": (
            "per evidence category, the minimum and maximum number of times it "
            "can appear in an optimal matching; any category that can vary "
            "means two optima differ in evidence"
        ),
        "tie_break_derivation": (
            "primary cost is multiplied by min(|L|,|R|) + 1 before the 0/1 "
            "indicator, so one unit of primary objective always outweighs any "
            "achievable category count"
        ),
        "seeds": len(SEEDS),
    }
    started = time.perf_counter()
    try:
        fixtures = solver_fixtures() + [counterexample_4x4()]
        rows = []
        for fixture in fixtures:
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
                findings, stats = evidence_ambiguity(
                    sources, targets, costs, solved
                )
                results.append(
                    {
                        "objective": solved["objective"],
                        "ambiguous": bool(findings),
                        "categories": stats["categories"],
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
            expected_distinct = fixture.get("expected_distinct_evidence")
            rows.append(
                {
                    "case": fixture["case"],
                    "expected_optima": fixture["expected_optima"],
                    "oracle_optima": oracle["optima"],
                    "expected_distinct_evidence": expected_distinct,
                    "oracle_distinct_evidence": oracle["distinct_evidence"],
                    "expected_ambiguous": fixture["expected_ambiguous"],
                    "oracle_ambiguous": oracle["ambiguous"],
                    "solver_ambiguous": first["ambiguous"],
                    "objective": list(first["objective"]),
                    "evidence_categories": first["categories"],
                    "stable_across_seeds": stable,
                    "passed": (
                        oracle["optima"] == fixture["expected_optima"]
                        and (
                            expected_distinct is None
                            or oracle["distinct_evidence"] == expected_distinct
                        )
                        and oracle["ambiguous"] == fixture["expected_ambiguous"]
                        and first["ambiguous"] == fixture["expected_ambiguous"]
                        and list(first["objective"]) == list(oracle["objective"])
                        and stable
                    ),
                }
            )

        corpus = run_corpus(args.corpus)

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
        stress_result = compare_uv_mesh(list(source), list(reimport))
        stress = {
            "triangles": len(source),
            "elapsed_seconds": stress_result["elapsed_seconds"],
            "coverage": stress_result["triangle_coverage"],
            "evidence_categories": stress_result["evidence_categories"],
            "ambiguity_solves": stress_result["ambiguity_solves"],
            "passed": stress_result["pass"]
            and stress_result["triangle_coverage"] == 1.0,
        }

        payload["solver_oracle"] = {
            "cases": len(rows),
            "all_passed": all(row["passed"] for row in rows),
            "detail": rows,
        }
        payload["corpus"] = corpus
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
            and corpus["pass"]
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
        corpus = payload.get("corpus", {})
        uv = payload.get("uv_matcher", {})
        stress = payload.get("stress", {})
        print(
            f"[Opus5VerifyA5] solver {oracle.get('cases')} all_passed="
            f"{oracle.get('all_passed')}, corpus {corpus.get('graphs')} "
            f"mismatches {len(corpus.get('mismatches', []))}, uv "
            f"{uv.get('cases')} all_passed={uv.get('all_passed')}, stress "
            f"{stress.get('passed')} ({stress.get('elapsed_seconds')}s), status "
            f"{payload.get('status')}"
        )
        for row in oracle.get("detail", []):
            if not row["passed"]:
                print(
                    f"  SOLVER FAIL {row['case']}: optima {row['oracle_optima']}"
                    f"/{row['expected_optima']} distinct "
                    f"{row['oracle_distinct_evidence']} ambiguous oracle="
                    f"{row['oracle_ambiguous']} solver={row['solver_ambiguous']}"
                )
        for row in uv.get("detail", []):
            if not row["passed"]:
                print(f"  UV FAIL {row['case']}")


if __name__ == "__main__":
    main()
