"""Phase M2n8: the same delivery path as M2n5, pointed at the M2n8 shapes.

Alignment 221.2. Nothing about how a meter is delivered changes here - the
export-normalized copy, the join by role, the slot normalisation and every gate
are M2n5's, reused as they are. All that differs is which Blend they read and
what the results are called.

The canonical Blends are not the source this time; the M2n8 revisions are. Both
are hashed anyway: the revision because it is what was exported, and the
canonical three because alignment 205.1 asks for proof they did not move.

The extra measurements alignment 205.1 lists - finite UVs, no degenerate
triangles, no NaN, no negative scale, the needle's reach and depth after the
round trip, the zone band's absence - are read off the re-imported snapshot the
M2n5 path already writes. No new validator is built for them.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n8_delivery.py -- \
      --project-root "$PWD" --mode export --staging /tmp/opus5-m2n8-fbx
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_d6_canonical_build as m2l
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n5_slot_normalized as m2n5
import opus5_meter_m2n7_depth_revision as m2n7
import opus5_meter_m2n8_revision as m2n8


SUMMARY = "ArtSource/Blender/BrushUp/Opus5/meter_m2n8_handoff.json"
REVISION = "M2n8"
# M2n8 rebuilt the scale, so the budget is what M2n8 measured.
EXPECTED_TRIANGLES = {
    "MeterRound": 4640, "MeterMedium": 6096, "MeterLarge": 6880,
}
# Alignment 140, kept here so "the canonical Blends did not move" is checked
# against the record rather than against whatever the patched table now says.
CANONICAL = {key: spec["sha256"] for key, spec in m2n.SOURCES.items()}
CANONICAL_BLEND = {key: spec["blend"] for key, spec in m2n.SOURCES.items()}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--mode", required=True, choices=("export", "reimport", "report")
    )
    parser.add_argument("--staging", required=True)
    return parser.parse_args(args)


def canonical_hashes(project_root):
    return {
        key: m1.digest(m2l.theme_dir(project_root) / name)
        for key, name in CANONICAL_BLEND.items()
    }


def point_at_revision(project_root):
    """Redirect the M2n5 delivery at the M2n8 Blends, and rename its outputs."""
    rows = {}
    for key in m2n.SOURCES:
        blend = m2n8.revision_blend(project_root, key)
        if not blend.is_file():
            raise SystemExit(f"[Opus5M2n8Fbx] missing revision blend: {blend}")
        digest = m1.digest(blend)
        m2n.SOURCES[key]["blend"] = blend.name
        m2n.SOURCES[key]["sha256"] = digest
        m2n.SOURCES[key]["fbx"] = m2n.SOURCES[key]["fbx"].replace(
            ".fbx", f"_{REVISION}.fbx"
        )
        m2n.SOURCES[key]["triangles"] = EXPECTED_TRIANGLES[key]
        rows[key] = {"blend": str(blend.relative_to(project_root)), "sha256": digest}
    m2n5.SUMMARY = "ArtSource/Blender/BrushUp/Opus5/meter_m2n8_delivery_report.json"

    def report_path(root, key):
        stem = m2n5.delivered_fbx_name(key).replace("SM_", "").replace(".fbx", "")
        return root / m2l.REPORT_DIR / f"{stem}_m2n8_candidate.json"

    m2n5.candidate_report_path = report_path
    return rows


def snapshot_health(scene):
    """Finite, non-degenerate, in-range - read off the re-imported snapshot."""
    uv_min = uv_max = None
    non_finite = 0
    degenerate = 0
    triangles = 0
    for entry in scene.values():
        if entry.get("type") != "MESH":
            continue
        for triangle in entry["triangles"]:
            triangles += 1
            points = [corner["position"] for corner in triangle["corners"]]
            for corner in triangle["corners"]:
                for value in corner["position"] + corner["split_normal"]:
                    if not math.isfinite(value):
                        non_finite += 1
                for values in corner["uv"].values():
                    for value in values:
                        if not math.isfinite(value):
                            non_finite += 1
                            continue
                        uv_min = value if uv_min is None else min(uv_min, value)
                        uv_max = value if uv_max is None else max(uv_max, value)
            if _area(points) <= 0.0:
                degenerate += 1
    return {
        "triangles": triangles,
        "non_finite_values": non_finite,
        "degenerate_triangles": degenerate,
        "uv_min": uv_min,
        "uv_max": uv_max,
        "uv_finite": non_finite == 0,
    }


def _area(points):
    a, b, c = (tuple(point) for point in points)
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    cross = [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    ]
    return math.sqrt(sum(value * value for value in cross)) / 2.0


def negative_scale(scene):
    """A mirrored transform shows up as a negative determinant."""
    flipped = []
    for identity, entry in scene.items():
        matrix = entry.get("root_relative_matrix")
        if matrix is None:
            continue
        basis = [row[:3] for row in matrix[:3]]
        determinant = (
            basis[0][0] * (basis[1][1] * basis[2][2] - basis[1][2] * basis[2][1])
            - basis[0][1] * (basis[1][0] * basis[2][2] - basis[1][2] * basis[2][0])
            + basis[0][2] * (basis[1][0] * basis[2][1] - basis[1][1] * basis[2][0])
        )
        if determinant < 0.0:
            flipped.append({"object": identity, "determinant": determinant})
    return flipped


def needle_after_round_trip(scene):
    """Reach measured from the pivot, which is where reach means anything.

    The pivot is offset from the root origin, so a radius taken about the
    origin is a different quantity and would not be comparable with the
    revision's own figures.
    """
    entry = scene.get("needle")
    if entry is None:
        return {"present": False}
    pivot = scene.get(m2n.MOTION["pivot"])
    centre = (
        (pivot["root_relative_matrix"][0][3], pivot["root_relative_matrix"][2][3])
        if pivot
        else (0.0, 0.0)
    )
    points = [
        corner["position"]
        for triangle in entry["triangles"]
        for corner in triangle["corners"]
    ]
    return {
        "present": True,
        "measured_from": "needle_pivot",
        "pivot_xz": [round(value, 6) for value in centre],
        "reach_mm": round(
            max(
                math.hypot(point[0] - centre[0], point[2] - centre[1])
                for point in points
            )
            * 1000.0,
            4,
        ),
        "front_m": round(min(point[1] for point in points), 7),
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    if args.mode != "report":
        blender_compat.require_v6_pipeline()
    canonical_before = canonical_hashes(project_root)
    revisions = point_at_revision(project_root)

    if args.mode == "export":
        m2n5.do_export(project_root, staging)
        return
    if args.mode == "reimport":
        m2n5.do_reimport(project_root, staging)
        return

    started = time.perf_counter()
    m2n5.do_report(project_root, staging)
    delivered = json.loads(
        (project_root / m2n5.SUMMARY).read_text()
    )
    imported = json.loads((staging / "reimport.json").read_text())
    payload = {
        "phase": "M2n8",
        "note": (
            "M2n5 delivery path, M2n8 shapes (alignment 205.1). No new "
            "validator; the extra checks are read off the re-imported "
            "snapshot the same path already writes."
        ),
        "revision_blends": revisions,
        "canonical_blend_sha256_before": canonical_before,
        "canonical_blend_sha256_after": canonical_hashes(project_root),
        "delivery_report": m2n5.SUMMARY,
        "delivery_status": delivered.get("status"),
        "models": {},
    }
    payload["canonical_unchanged"] = all(
        payload["canonical_blend_sha256_after"][key] == CANONICAL[key]
        for key in CANONICAL
    )
    for key in m2n.SOURCES:
        scene = imported[key]["reimport"]
        model = delivered.get("models", {}).get(key, {})
        health = snapshot_health(scene)
        payload["models"][key] = {
            "fbx": model.get("fbx"),
            "staged_sha256": model.get("staged_sha256"),
            "published": model.get("published"),
            "renderers": model.get("renderers"),
            "submeshes": model.get("submeshes"),
            "submesh_total": model.get("submesh_total"),
            "triangles": model.get("triangles"),
            "expected_triangles": EXPECTED_TRIANGLES[key],
            "bounds": model.get("bounds"),
            "failing_gates": model.get("failing_gates"),
            "snapshot_health": health,
            "negative_scale_objects": negative_scale(scene),
            "needle_after_round_trip": needle_after_round_trip(scene),
            "zone_band_absent": "kinetic_v6_zone_band" not in scene,
        }
    payload["all_passed"] = bool(
        payload["canonical_unchanged"]
        and delivered.get("all_passed")
        and all(
            row["snapshot_health"]["non_finite_values"] == 0
            and row["snapshot_health"]["degenerate_triangles"] == 0
            and not row["negative_scale_objects"]
            and row["zone_band_absent"]
            and row["triangles"] == row["expected_triangles"]
            for row in payload["models"].values()
        )
    )
    payload["status"] = (
        "candidate_handoff_published" if payload["all_passed"] else "gates_failed"
    )
    payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / SUMMARY).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[Opus5M2n8Fbx] status {payload['status']}, canonical unchanged "
        f"{payload['canonical_unchanged']}"
    )
    for key, row in payload["models"].items():
        print(
            f"  {key}: {row['renderers']} / {row['submesh_total']} submeshes, "
            f"tris {row['triangles']}, needle reach "
            f"{row['needle_after_round_trip'].get('reach_mm')} mm, "
            f"failing {row['failing_gates']}"
        )


if __name__ == "__main__":
    main()
