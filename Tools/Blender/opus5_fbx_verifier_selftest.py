"""Phase M2n2a: finish the verifier before pointing it at anything real.

Alignment 146.1. M2n's UV gate failed for reasons that had nothing to do with
UVs, and its transform gate collapsed rotation, scale and shear into a single
metre-shaped number. Both were my implementation. This builds the two
verifiers against fixtures whose answers are known in advance, and nothing
else: no canonical Blend is opened, no FBX is written, nothing is published.

The UV matcher pairs triangles by geometry, not by index. FBX may reorder
loops, renumber vertices and split them at seams, so index identity proves
nothing. Triangles are consumed one-to-one from a multiset keyed on their
corner positions and material, the corner correspondence inside a matched pair
is the permutation with the smallest geometric error, and anything left
unconsumed - or any pair that ends up comparing no values at all - is a
failure rather than a silent pass.

The transform verifier reports translation, rotation, scale and shear
separately, in their own units, because a dimensionless basis coefficient is
not a distance.

Runs under plain Python; it needs no Blender data.

Usage::

    python3 Tools/Blender/opus5_fbx_verifier_selftest.py --project-root "$PWD"
"""

import argparse
import itertools
import json
import math
import sys
import time
import traceback
from pathlib import Path


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_verifier_self_test.json"

# Alignment 142: one float32 unit in the last place, relative to the value.
UV_ULP = 2.0 * (2.0 ** -23)
# Corner positions are matched, not measured; this only has to be tight enough
# to keep distinct corners apart and loose enough to survive float32 storage.
GEOMETRY_TOLERANCE = 1.0e-6


# --------------------------------------------------------------------------
# UV matcher


def corner_key(position):
    return tuple(round(value / GEOMETRY_TOLERANCE) for value in position)


def triangle_key(triangle):
    """Identity that survives reordering: sorted corners plus material."""
    corners, material = triangle
    return (
        tuple(sorted(corner_key(position) for position, _ in corners)),
        material,
    )


def geometric_error(first, second, permutation):
    total = 0.0
    for index, mapped in enumerate(permutation):
        a = first[index][0]
        b = second[mapped][0]
        total += sum((a[i] - b[i]) ** 2 for i in range(3))
    return math.sqrt(total)


def best_permutation(first, second):
    """The corner correspondence geometry implies, and whether it is unique."""
    scored = sorted(
        (
            (geometric_error(first, second, permutation), permutation)
            for permutation in itertools.permutations(range(3))
        ),
        key=lambda item: item[0],
    )
    best, runner_up = scored[0], scored[1]
    ambiguous = abs(runner_up[0] - best[0]) <= GEOMETRY_TOLERANCE
    return best[1], best[0], ambiguous


def compare_uv_mesh(source, reimport):
    """Order-independent UV comparison with one-to-one consumption."""
    if source is None and reimport is None:
        return {"status": "absent_on_both", "pass": True}
    if source is None or reimport is None:
        present = source if source is not None else reimport
        return {
            "status": "layer_on_one_side_only",
            "side": "source" if source is not None else "reimport",
            "triangles": len(present),
            "pass": False,
        }

    pool = {}
    for triangle in reimport:
        pool.setdefault(triangle_key(triangle), []).append(triangle)

    matched = 0
    compared = 0
    over = 0
    ambiguous = 0
    worst = None
    total = 0.0
    unmatched_source = []
    for triangle in source:
        key = triangle_key(triangle)
        candidates = pool.get(key)
        if not candidates:
            unmatched_source.append(key)
            continue
        partner = candidates.pop()
        if not candidates:
            pool.pop(key, None)
        matched += 1
        permutation, error, is_ambiguous = best_permutation(
            triangle[0], partner[0]
        )
        if is_ambiguous:
            ambiguous += 1
        for index, mapped in enumerate(permutation):
            for component in (0, 1):
                before = triangle[0][index][1][component]
                after = partner[0][mapped][1][component]
                difference = abs(after - before)
                bound = UV_ULP * max(1.0, abs(before))
                compared += 1
                total += difference * difference
                if difference > bound:
                    over += 1
                if worst is None or difference > worst["difference"]:
                    worst = {
                        "difference": difference,
                        "bound": bound,
                        "before": before,
                        "after": after,
                    }
    leftover = sum(len(values) for values in pool.values())
    expected = len(source)
    return {
        "status": "compared",
        "expected_triangles": expected,
        "matched_triangles": matched,
        "unmatched_source_triangles": len(unmatched_source),
        "unconsumed_reimport_triangles": leftover,
        "triangle_coverage": (matched / expected) if expected else 0.0,
        "expected_scalars": expected * 6,
        "compared_scalars": compared,
        "scalar_coverage": (compared / (expected * 6)) if expected else 0.0,
        "ambiguous_corner_matches": ambiguous,
        "max_abs_difference": worst["difference"] if worst else 0.0,
        "bound_at_worst": worst["bound"] if worst else None,
        "worst_before_after": (
            [worst["before"], worst["after"]] if worst else None
        ),
        "rms": math.sqrt(total / compared) if compared else 0.0,
        "over_bound": over,
        "pass": (
            expected > 0
            and matched == expected
            and not unmatched_source
            and leftover == 0
            and compared == expected * 6
            and over == 0
            and ambiguous == 0
        ),
    }


# --------------------------------------------------------------------------
# Relative transform


def multiply(a, b):
    return [
        [sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)]
        for r in range(4)
    ]


def inverse_rigid_general(matrix):
    """General 4x4 inverse by Gauss-Jordan; the fixtures include shear."""
    size = 4
    augmented = [list(row) + [1.0 if i == j else 0.0 for j in range(size)]
                 for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda r: abs(augmented[r][column]))
        if abs(augmented[pivot][column]) < 1e-15:
            raise ValueError("singular matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * other
                for value, other in zip(augmented[row], augmented[column])
            ]
    return [row[size:] for row in augmented]


def decompose(source, reimport):
    """Split what changed into translation, rotation, scale and shear."""
    relative = multiply(inverse_rigid_general(source), reimport)
    translation = [relative[i][3] for i in range(3)]
    basis = [[relative[r][c] for c in range(3)] for r in range(3)]
    columns = [[basis[r][c] for r in range(3)] for c in range(3)]
    scales = [math.sqrt(sum(v * v for v in column)) for column in columns]
    unit = [
        [value / scale if scale > 1e-15 else 0.0 for value in column]
        for column, scale in zip(columns, scales)
    ]
    shear = [
        sum(unit[0][i] * unit[1][i] for i in range(3)),
        sum(unit[0][i] * unit[2][i] for i in range(3)),
        sum(unit[1][i] * unit[2][i] for i in range(3)),
    ]
    trace = sum(unit[c][c] for c in range(3))
    cosine = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
    return {
        "translation_m": translation,
        "translation_norm_m": math.sqrt(sum(v * v for v in translation)),
        "translation_norm_um": math.sqrt(sum(v * v for v in translation)) * 1e6,
        "scale_ratios": scales,
        "scale_max_deviation": max(abs(scale - 1.0) for scale in scales),
        "rotation_deg": math.degrees(math.acos(cosine)),
        "shear_residual": max(abs(value) for value in shear),
        "classification": None,
    }


def classify(parts):
    """Name the dominant effect so a basis wobble is never read as a distance.

    The noise case is tested first on purpose. A skew-symmetric coefficient of
    1.07e-6 is a real rotation - about 6.1e-5 degrees - so the pure-rotation
    branch matches it before anything else gets a look. Ordering it first is
    what separates "the basis wobbled in storage" from "the part turned".
    """
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
    if parts["shear_residual"] > 1e-9 and parts["translation_norm_m"] < 1e-9:
        return "shear"
    return "composite"


# --------------------------------------------------------------------------
# Fixtures


def triangle(corners, material=0):
    return (corners, material)


def uv_fixtures():
    base = [
        triangle(
            [
                ((0.0, 0.0, 0.0), (0.0, 0.0)),
                ((1.0, 0.0, 0.0), (1.0, 0.0)),
                ((0.0, 1.0, 0.0), (0.0, 1.0)),
            ]
        ),
        triangle(
            [
                ((1.0, 0.0, 0.0), (1.0, 0.0)),
                ((1.0, 1.0, 0.0), (1.0, 1.0)),
                ((0.0, 1.0, 0.0), (0.0, 1.0)),
            ]
        ),
    ]

    def copy_with(index, corner, uv):
        clone = [(list(t[0]), t[1]) for t in base]
        corners = clone[index][0]
        corners[corner] = (corners[corner][0], uv)
        return [triangle(list(t[0]), t[1]) for t in clone]

    reordered = list(reversed(base))
    rotated_corners = [
        triangle([t[0][1], t[0][2], t[0][0]], t[1]) for t in base
    ]
    seam = base + [
        triangle(
            [
                ((1.0, 0.0, 0.0), (0.0, 0.5)),
                ((2.0, 0.0, 0.0), (1.0, 0.5)),
                ((1.0, 1.0, 0.0), (0.0, 1.0)),
            ]
        )
    ]
    duplicate = base + [base[0]]
    within = copy_with(0, 1, (1.0 + UV_ULP * 0.5, 0.0))
    over = copy_with(0, 1, (1.0 + UV_ULP * 40.0, 0.0))
    swapped = [
        triangle(
            [
                (base[0][0][0][0], (0.0, 1.0)),
                (base[0][0][1][0], (0.0, 0.0)),
                (base[0][0][2][0], (1.0, 0.0)),
            ]
        ),
        base[1],
    ]

    return [
        ("loop order reversed", base, reordered, True),
        ("corner order rotated within each triangle", base, rotated_corners, True),
        ("uv seam: same position, two different uvs", seam, list(reversed(seam)), True),
        ("coincident duplicate face", duplicate, list(reversed(duplicate)), True),
        ("float32 rounding within bound", base, within, True),
        ("uv moved beyond bound", base, over, False),
        ("layer missing on one side", base, None, False),
        ("uvs misassigned between corners", base, swapped, False),
        ("triangle missing from reimport", base, base[:1], False),
        ("extra triangle in reimport", base, base + [seam[2]], False),
    ]


def transform_fixtures():
    def matrix(rows):
        return [list(row) for row in rows]

    identity = matrix(
        [(1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]
    )
    translated = matrix(
        [(1, 0, 0, 0.25), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]
    )
    angle = math.radians(3.0)
    rotated = matrix(
        [
            (math.cos(angle), -math.sin(angle), 0, 0),
            (math.sin(angle), math.cos(angle), 0, 0),
            (0, 0, 1, 0),
            (0, 0, 0, 1),
        ]
    )
    scaled = matrix(
        [(1.02, 0, 0, 0), (0, 0.98, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]
    )
    sheared = matrix(
        [(1, 0.01, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)]
    )
    composite = multiply(multiply(translated, rotated), scaled)
    noisy = matrix(
        [
            (1, 1.0728836343787407e-06, 0, 0),
            (-1.0728836343787407e-06, 1, 0, 0),
            (0, 0, 1, 0),
            (0, 0, 0, 1),
        ]
    )
    return [
        ("pure translation", identity, translated, "pure translation"),
        ("pure rotation", identity, rotated, "pure rotation"),
        ("non-uniform scale", identity, scaled, "non-uniform scale"),
        ("shear", identity, sheared, "shear"),
        ("composite", identity, composite, "composite"),
        (
            "identity with near-zero basis noise, as seen on MeterLarge",
            identity,
            noisy,
            "identity within float noise",
        ),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    payload = {
        "phase": "M2n2a",
        "note": (
            "Verifier fixtures only (alignment 146.1). No canonical Blend is "
            "opened, no FBX is written, nothing is published."
        ),
        "uv_bound_rule": "2 * 2^-23 * max(1, |value|)",
        "geometry_tolerance_m": GEOMETRY_TOLERANCE,
    }
    started = time.perf_counter()
    try:
        uv_rows = []
        for name, source, reimport, expected in uv_fixtures():
            measured = compare_uv_mesh(source, reimport)
            uv_rows.append(
                {
                    "case": name,
                    "expected_pass": expected,
                    "measured_pass": measured["pass"],
                    "passed": measured["pass"] == expected,
                    "detail": measured,
                }
            )
        transform_rows = []
        for name, source, reimport, expected in transform_fixtures():
            parts = decompose(source, reimport)
            parts["classification"] = classify(parts)
            transform_rows.append(
                {
                    "case": name,
                    "expected_classification": expected,
                    "measured_classification": parts["classification"],
                    "passed": parts["classification"] == expected,
                    "detail": parts,
                }
            )
        payload["uv_matcher"] = {
            "cases": len(uv_rows),
            "all_passed": all(row["passed"] for row in uv_rows),
            "detail": uv_rows,
        }
        payload["transform_decomposition"] = {
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
            f"[Opus5Verify] uv {uv.get('cases')} cases "
            f"all_passed={uv.get('all_passed')}, transform {tf.get('cases')} "
            f"cases all_passed={tf.get('all_passed')}, status "
            f"{payload.get('status')}"
        )
        for row in uv.get("detail", []):
            if not row["passed"]:
                print(f"  UV FAIL {row['case']}: {row['detail'].get('status')}")
        for row in tf.get("detail", []):
            if not row["passed"]:
                print(
                    f"  TF FAIL {row['case']}: expected "
                    f"{row['expected_classification']} got "
                    f"{row['measured_classification']}"
                )


if __name__ == "__main__":
    main()
