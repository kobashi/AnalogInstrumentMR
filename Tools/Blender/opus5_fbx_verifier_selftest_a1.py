"""Phase M2n2a1: close the duplicate-face counterexample.

Alignment 148.1. The previous matcher took the first candidate off a list for
each triangle key. Where two faces share a key - same corners, same material,
different UVs - which one it took depended on input order, so the same pair of
meshes passed in one order and failed in the other. Codex reproduced it; it is
a real defect, not a fixture artefact.

Here every face in a key group is matched by solving a one-to-one assignment
over the whole group, scoring each candidate pairing by its best corner
permutation. Coverage comes first, then the number of UV values outside the
float32 bound, then the total UV error. If two optimal assignments would give
different verdicts, that is `ambiguous` and fails; if they give the same
verdict and the same error multiset, they are equivalent and either may stand.

The quantised key is an index, not a decision. Neighbouring buckets are
searched, and a pairing is only admissible once the real corner distances are
inside the geometric tolerance.

The transform verifier gains a polar decomposition, because a rotation read off
the trace of a scale-normalised basis is not the rotation when the matrix also
shears.

Pure Python; no Blender data is involved. Nothing is published.

Usage::

    python3 Tools/Blender/opus5_fbx_verifier_selftest_a1.py --project-root "$PWD"
"""

import argparse
import itertools
import json
import math
import random
import time
import traceback
from pathlib import Path


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_verifier_self_test_a1.json"
PRIOR = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_verifier_self_test.json"

UV_ULP = 2.0 * (2.0 ** -23)
GEOMETRY_TOLERANCE = 1.0e-6
BUCKET = GEOMETRY_TOLERANCE
SHUFFLE_SEEDS = (1, 2, 3, 5, 8)


# --------------------------------------------------------------------------
# UV matcher


def bucket_key(position):
    return tuple(int(math.floor(value / BUCKET)) for value in position)


def group_key(triangle):
    """Index on the centroid, not on all three corners.

    Bucketing each corner separately and then shifting the whole triple by one
    offset was wrong: two matching triangles can have different corners on
    different sides of different boundaries, and no single shift recovers that.
    A centroid is one point, so its 26 neighbours really are its neighbours -
    and two triangles that match within the tolerance have centroids within it
    too. The bucket only proposes; `permutation_cost` decides on real distance.
    """
    corners, material = triangle
    centroid = tuple(
        sum(position[axis] for position, _ in corners) / 3.0 for axis in range(3)
    )
    return (bucket_key(centroid), material)


def neighbours(key):
    """The bucket and its 26 neighbours, so a boundary is not a wall."""
    centroid, material = key
    for offsets in itertools.product((-1, 0, 1), repeat=3):
        yield (
            tuple(value + delta for value, delta in zip(centroid, offsets)),
            material,
        )


def permutation_cost(first, second):
    """Best corner correspondence by geometry, then its UV cost."""
    best = None
    for permutation in itertools.permutations(range(3)):
        distance = max(
            math.dist(first[index][0], second[mapped][0])
            for index, mapped in enumerate(permutation)
        )
        if distance > GEOMETRY_TOLERANCE:
            continue
        over = 0
        error = 0.0
        for index, mapped in enumerate(permutation):
            for component in (0, 1):
                before = first[index][1][component]
                after = second[mapped][1][component]
                difference = abs(after - before)
                bound = UV_ULP * max(1.0, abs(before))
                if difference > bound:
                    over += 1
                error += difference / bound
        score = (over, error, distance)
        if best is None or score < best[0]:
            best = (score, permutation, over, error, distance)
    return best


def solve_group(sources, targets):
    """One-to-one assignment over a whole key group, order-independent."""
    costs = {}
    for i, source in enumerate(sources):
        for j, target in enumerate(targets):
            found = permutation_cost(source[0], target[0])
            if found is not None:
                costs[(i, j)] = found

    best = None
    equivalents = 0
    size = min(len(sources), len(targets))
    for chosen in itertools.permutations(range(len(targets)), len(sources)):
        pairs = [(i, j) for i, j in enumerate(chosen) if (i, j) in costs]
        if len(pairs) != len(sources):
            continue
        over = sum(costs[pair][2] for pair in pairs)
        error = sum(costs[pair][3] for pair in pairs)
        signature = (over, round(error, 12))
        score = (-len(pairs), over, error)
        if best is None or score < best[0]:
            best = (score, pairs, signature)
            equivalents = 1
        elif score == best[0]:
            equivalents += 1
            if signature != best[2]:
                return None, "ambiguous: equally optimal assignments disagree"
    if best is None:
        return None, "no admissible assignment"
    return {
        "pairs": best[1],
        "over_bound": best[2][0],
        "uv_error": best[2][1],
        "equivalent_optima": equivalents,
        "matched": len(best[1]),
        "sources": len(sources),
        "targets": len(targets),
    }, None


def compare_uv_mesh(source, reimport):
    if source is None and reimport is None:
        return {"status": "absent_on_both", "pass": True}
    if source is None or reimport is None:
        return {
            "status": "layer_on_one_side_only",
            "side": "source" if source is not None else "reimport",
            "pass": False,
        }

    pool = {}
    for index, triangle in enumerate(reimport):
        pool.setdefault(group_key(triangle), []).append(index)

    used = set()
    matched = 0
    over = 0
    error = 0.0
    problems = []
    handled = set()
    for index, triangle in enumerate(source):
        key = group_key(triangle)
        if key in handled:
            continue
        handled.add(key)
        sources = [t for t in source if group_key(t) == key]
        candidate_indices = []
        for neighbour in neighbours(key):
            candidate_indices.extend(pool.get(neighbour, []))
        candidate_indices = sorted(set(candidate_indices) - used)
        targets = [reimport[i] for i in candidate_indices]
        solved, failure = solve_group(sources, targets)
        if failure:
            problems.append({"key_group": len(sources), "reason": failure})
            continue
        matched += solved["matched"]
        over += solved["over_bound"]
        error += solved["uv_error"]
        used.update(candidate_indices[j] for _, j in solved["pairs"])

    expected = len(source)
    leftover = len(reimport) - len(used)
    return {
        "status": "compared",
        "expected_triangles": expected,
        "matched_triangles": matched,
        "unconsumed_reimport_triangles": leftover,
        "triangle_coverage": (matched / expected) if expected else 0.0,
        "expected_scalars": expected * 6,
        "compared_scalars": matched * 6,
        "scalar_coverage": (matched / expected) if expected else 0.0,
        "over_bound": over,
        "normalised_uv_error": round(error, 12),
        "problems": problems,
        "pass": (
            expected > 0
            and matched == expected
            and leftover == 0
            and over == 0
            and not problems
        ),
    }


# --------------------------------------------------------------------------
# Transform


def transpose(matrix):
    return [[matrix[c][r] for c in range(3)] for r in range(3)]


def matmul3(a, b):
    return [
        [sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)]
        for r in range(3)
    ]


def inverse3(matrix):
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(determinant) < 1e-18:
        raise ValueError("singular basis")
    return [
        [(e * i - f * h) / determinant, (c * h - b * i) / determinant, (b * f - c * e) / determinant],
        [(f * g - d * i) / determinant, (a * i - c * g) / determinant, (c * d - a * f) / determinant],
        [(d * h - e * g) / determinant, (b * g - a * h) / determinant, (a * e - b * d) / determinant],
    ]


def polar(basis):
    """Split into orthogonal rotation and symmetric stretch, iteratively."""
    rotation = [row[:] for row in basis]
    for _ in range(64):
        inverse_transpose = transpose(inverse3(rotation))
        nxt = [
            [0.5 * (rotation[r][c] + inverse_transpose[r][c]) for c in range(3)]
            for r in range(3)
        ]
        delta = max(
            abs(nxt[r][c] - rotation[r][c]) for r in range(3) for c in range(3)
        )
        rotation = nxt
        if delta < 1e-15:
            break
    stretch = matmul3(transpose(rotation), basis)
    reconstruction = matmul3(rotation, stretch)
    residual = max(
        abs(reconstruction[r][c] - basis[r][c]) for r in range(3) for c in range(3)
    )
    trace = sum(rotation[c][c] for c in range(3))
    cosine = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
    return {
        "rotation_deg": math.degrees(math.acos(cosine)),
        "stretch_diagonal": [stretch[c][c] for c in range(3)],
        "stretch_off_diagonal_max": max(
            abs(stretch[r][c]) for r in range(3) for c in range(3) if r != c
        ),
        "reconstruction_residual": residual,
    }


def decompose(source, reimport):
    from opus5_fbx_verifier_selftest import inverse_rigid_general, multiply

    relative = multiply(inverse_rigid_general(source), reimport)
    translation = [relative[i][3] for i in range(3)]
    basis = [[relative[r][c] for c in range(3)] for r in range(3)]
    parts = polar(basis)
    parts.update(
        {
            "translation_m": translation,
            "translation_norm_m": math.sqrt(sum(v * v for v in translation)),
            "translation_norm_um": math.sqrt(sum(v * v for v in translation)) * 1e6,
            "scale_max_deviation": max(
                abs(value - 1.0) for value in parts["stretch_diagonal"]
            ),
            "shear_residual": parts["stretch_off_diagonal_max"],
        }
    )
    return parts


def classify(parts):
    if (
        parts["translation_norm_m"] < 1e-7
        and parts["rotation_deg"] < 1e-3
        and parts["scale_max_deviation"] < 1e-6
        and parts["shear_residual"] < 1e-6
    ):
        return "identity within float noise"
    if parts["translation_norm_m"] > 1e-9 and parts["rotation_deg"] < 1e-6 and (
        parts["scale_max_deviation"] < 1e-9 and parts["shear_residual"] < 1e-9
    ):
        return "pure translation"
    if parts["rotation_deg"] > 1e-6 and parts["scale_max_deviation"] < 1e-9 and (
        parts["shear_residual"] < 1e-9 and parts["translation_norm_m"] < 1e-9
    ):
        return "pure rotation"
    if parts["scale_max_deviation"] > 1e-9 and parts["shear_residual"] < 1e-9 and (
        parts["rotation_deg"] < 1e-6 and parts["translation_norm_m"] < 1e-9
    ):
        return "non-uniform scale"
    if (
        parts["shear_residual"] > 1e-9
        and parts["translation_norm_m"] < 1e-9
        and parts["rotation_deg"] < 1e-6
    ):
        return "shear"
    return "composite"


# --------------------------------------------------------------------------
# Fixtures


def face(positions, uvs, material=0):
    return ([(positions[i], uvs[i]) for i in range(3)], material)


def duplicate_fixtures():
    """The counterexample Codex found, in every input order."""
    positions = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    uv_a = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    uv_b = [(0.5, 0.5), (0.9, 0.5), (0.5, 0.9)]
    a = face(positions, uv_a)
    b = face(positions, uv_b)
    moved = face(positions, [(0.5 + UV_ULP * 40.0, 0.5), (0.9, 0.5), (0.5, 0.9)])
    cases = []
    for source in ([a, b], [b, a]):
        for target in ([a, b], [b, a]):
            cases.append(
                (
                    "coincident duplicate faces, different uvs, "
                    f"source {'AB' if source[0] is a else 'BA'} vs "
                    f"reimport {'AB' if target[0] is a else 'BA'}",
                    source,
                    target,
                    True,
                )
            )
    cases.append(("duplicate: one uv moved beyond bound", [a, b], [a, moved], False))
    cases.append(("duplicate missing on reimport", [a, b], [a], False))
    cases.append(("duplicate extra on reimport", [a], [a, b], False))
    return cases


def boundary_fixtures():
    """A quantisation edge must not decide anything on its own."""
    edge = BUCKET * 10.0
    inside = face(
        [(edge - 4e-7, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
    )
    across = face(
        [(edge + 4e-7, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
    )
    far = face(
        [(edge + 5e-6, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)],
    )
    return [
        ("across a bucket boundary but within tolerance", [inside], [across], True),
        ("same neighbourhood but beyond tolerance", [inside], [far], False),
    ]


def transform_fixtures():
    from opus5_fbx_verifier_selftest import transform_fixtures as base

    rows = []
    for name, source, target, expected in base():
        if name == "shear":
            # Under polar decomposition a shear is not rotation-free: it is a
            # rotation composed with a symmetric stretch, and the rotation is
            # real. The earlier trace-based verifier reported 0 degrees here
            # and called it "shear", which is why 148 declined to accept that
            # rotation figure. The mathematics is right; the expectation was
            # mine and it was wrong.
            expected = "composite"
            name = "pure shear matrix (polar: rotation + stretch)"
        rows.append((name, source, target, expected))
    shear_then_rotate = [
        [0.9998476951563913, -0.017452406437283512, 0.01, 0.0],
        [0.017452406437283512, 0.9998476951563913, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    identity = [
        [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]
    ]
    rows.append(
        ("rotation combined with shear", identity, shear_then_rotate, "composite")
    )
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))

    payload = {
        "phase": "M2n2a1",
        "note": (
            "Duplicate-face counterexample closure (alignment 148.1). Pure "
            "fixtures; no Blend, FBX or canonical artefact is touched."
        ),
        "prior_self_test": PRIOR,
        "assignment": (
            "global one-to-one over each key group; coverage first, "
            "over-bound count second, normalised UV error third"
        ),
        "shuffle_seeds": list(SHUFFLE_SEEDS),
        "uv_bound_rule": "2 * 2^-23 * max(1, |value|)",
        "geometry_tolerance_m": GEOMETRY_TOLERANCE,
    }
    started = time.perf_counter()
    try:
        cases = duplicate_fixtures() + boundary_fixtures()
        rows = []
        for name, source, target, expected in cases:
            verdicts = []
            for seed in SHUFFLE_SEEDS:
                rng = random.Random(seed)
                shuffled_source = list(source)
                shuffled_target = list(target)
                rng.shuffle(shuffled_source)
                rng.shuffle(shuffled_target)
                verdicts.append(compare_uv_mesh(shuffled_source, shuffled_target))
            stable = all(
                entry["pass"] == verdicts[0]["pass"]
                and entry.get("over_bound") == verdicts[0].get("over_bound")
                for entry in verdicts
            )
            rows.append(
                {
                    "case": name,
                    "expected_pass": expected,
                    "measured_pass": verdicts[0]["pass"],
                    "stable_across_seeds": stable,
                    "passed": verdicts[0]["pass"] == expected and stable,
                    "detail": verdicts[0],
                }
            )
        payload["uv_matcher"] = {
            "cases": len(rows),
            "all_passed": all(row["passed"] for row in rows),
            "detail": rows,
        }

        transform_rows = []
        for name, source, target, expected in transform_fixtures():
            parts = decompose(source, target)
            parts["classification"] = classify(parts)
            transform_rows.append(
                {
                    "case": name,
                    "expected_classification": expected,
                    "measured_classification": parts["classification"],
                    "reconstruction_residual": parts["reconstruction_residual"],
                    "passed": (
                        parts["classification"] == expected
                        and parts["reconstruction_residual"] < 1e-12
                    ),
                    "detail": parts,
                }
            )
        payload["transform_decomposition"] = {
            "method": "polar decomposition, rotation from the orthogonal factor",
            "cases": len(transform_rows),
            "all_passed": all(row["passed"] for row in transform_rows),
            "detail": transform_rows,
        }
        payload["status"] = (
            "complete"
            if payload["uv_matcher"]["all_passed"]
            and payload["transform_decomposition"]["all_passed"]
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
        tf = payload.get("transform_decomposition", {})
        print(
            f"[Opus5VerifyA1] uv {uv.get('cases')} all_passed="
            f"{uv.get('all_passed')}, transform {tf.get('cases')} all_passed="
            f"{tf.get('all_passed')}, status {payload.get('status')}"
        )
        for row in uv.get("detail", []):
            if not row["passed"]:
                print(
                    f"  UV FAIL {row['case']}: expected {row['expected_pass']} "
                    f"got {row['measured_pass']} stable={row['stable_across_seeds']}"
                )
        for row in tf.get("detail", []):
            if not row["passed"]:
                print(
                    f"  TF FAIL {row['case']}: expected "
                    f"{row['expected_classification']} got "
                    f"{row['measured_classification']} residual "
                    f"{row['reconstruction_residual']}"
                )


if __name__ == "__main__":
    main()
