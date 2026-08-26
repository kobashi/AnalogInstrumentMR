"""Phase M2n1: what the FBX gates were actually objecting to.

Alignment 142.1. M2n failed two gates and left neither their detail nor the
export and round-trip JSON behind, so the numbers in 141 cannot be re-checked
by anyone but me. This runs the same export and re-import into a temporary
directory, publishes nothing, and writes everything it saw - on every path,
including failure.

The two gates are examined rather than relaxed:

* UV. A double-precision hash of float32 storage can only ever disagree. Here
  each object reports its layer, loop count, the largest and RMS difference,
  which loop was worst and what it held before and after, against the bound
  float32 can actually promise: 2 * 2^-23 * max(1, |u|, |v|). Corners are
  matched by a topology-aware signature built from the 3D corner positions, so
  a reordered loop is not mistaken for a moved UV.
* Inventory. Every object is compared field by field, including the local and
  world matrices M2n never checked, with the tolerance stated next to the
  measurement. Medium's difference is named, not guessed at.

Read-only. No FBX, canonical report, handoff summary or PNG is published, and
the existing attempt JSON is referenced by hash rather than overwritten.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_fbx_diagnostic.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
import json
import math
import struct
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact_migration_m1 as m1
import opus5_d3_solver_diagnostic as diag
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_handoff as m2n


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_diagnostic.json"
PRIOR_ATTEMPT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_attempt.json"

# Alignment 142.1-3.
PINNED_REPORT_SHA = {
    "MeterRound": "1aeaad4e17369f414ca63e32fb45ff61fa9a00b0846990fa12df536878bd33ec",
    "MeterMedium": "9639b6f3f424a7ab3c159a59e7c81af3dfffbbc1c36446cc3bee825dfdb4deee",
    "MeterLarge": "a13eb9e66ee9c5616b0e5e1956f38a6fb4265a3681d4b0d4efc3680338afcaa1",
}

# float32 has 24 bits of significand; a value round-tripped through it can move
# by one unit in the last place either way.
UV_ULP = 2.0 * (2.0 ** -23)
# Positions travel through the same storage and an axis conversion, so the
# matrix bound is the same relative step applied to the largest coordinate a
# meter reaches (about 0.3 m), rounded up.
MATRIX_TOLERANCE = 1.0e-6


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append")
    return parser.parse_args(args)


def corner_signature(obj):
    """Per-corner UV, keyed by where the corner is in space.

    FBX may reorder loops. Keying on the corner's 3D position rather than its
    index means a reordering shows up as the same multiset, while a UV that
    genuinely moved still shows up as a difference.
    """
    mesh = obj.data
    layer = mesh.uv_layers.active
    if layer is None:
        return None, None
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    entries = {}
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex = mesh.loops[loop_index].vertex_index
            world = matrix @ mesh.vertices[vertex].co
            key = (
                round(world.x, 6), round(world.y, 6), round(world.z, 6)
            )
            entries.setdefault(key, []).append(
                (round(layer.data[loop_index].uv[0], 12),
                 round(layer.data[loop_index].uv[1], 12))
            )
    for key in entries:
        entries[key].sort()
    return layer.name, entries


def compare_uv(source, reimported):
    """Per object: how far each UV moved, against what float32 can promise."""
    rows = {}
    for name in sorted(set(source) | set(reimported)):
        first, second = source.get(name), reimported.get(name)
        if first is None or second is None:
            rows[name] = {
                "status": "missing on one side",
                "in_source": first is not None,
                "in_reimport": second is not None,
                "pass": False,
            }
            continue
        layer_a, corners_a = first
        layer_b, corners_b = second
        if corners_a is None or corners_b is None:
            rows[name] = {"status": "no uv layer", "pass": corners_a == corners_b}
            continue
        missing = sorted(set(corners_a) - set(corners_b))
        extra = sorted(set(corners_b) - set(corners_a))
        worst = None
        total = 0.0
        count = 0
        over = 0
        for key in set(corners_a) & set(corners_b):
            values_a, values_b = corners_a[key], corners_b[key]
            if len(values_a) != len(values_b):
                over += 1
                continue
            for (ua, va), (ub, vb) in zip(values_a, values_b):
                for before, after in ((ua, ub), (va, vb)):
                    difference = abs(after - before)
                    bound = UV_ULP * max(1.0, abs(before))
                    total += difference * difference
                    count += 1
                    if difference > bound:
                        over += 1
                    if worst is None or difference > worst["difference"]:
                        worst = {
                            "difference": difference,
                            "bound": bound,
                            "corner": list(key),
                            "before": before,
                            "after": after,
                        }
        rows[name] = {
            "layer": [layer_a, layer_b],
            "corners": [len(corners_a), len(corners_b)],
            "corners_missing": len(missing),
            "corners_extra": len(extra),
            "values_compared": count,
            "max_abs_difference": worst["difference"] if worst else 0.0,
            "float32_bound_at_worst": worst["bound"] if worst else None,
            "worst_corner": worst["corner"] if worst else None,
            "worst_before_after": (
                [worst["before"], worst["after"]] if worst else None
            ),
            "rms": math.sqrt(total / count) if count else 0.0,
            "over_bound": over,
            "pass": not missing and not extra and over == 0,
        }
    return rows


def inventory_of(root):
    entries = {}
    for obj in [root] + list(root.children_recursive):
        entry = {
            "type": obj.type,
            "parent": m2n.m2i.name_of(obj.parent) if obj.parent else None,
            "matrix_local": [[v for v in row] for row in obj.matrix_local],
            "matrix_world": [[v for v in row] for row in obj.matrix_world],
        }
        if obj.type == "MESH":
            obj.data.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            entry.update(
                {
                    "mesh": obj.data.name.split(".")[0],
                    "vertices": len(obj.data.vertices),
                    "loop_triangles": len(obj.data.loop_triangles),
                    "materials": [
                        m.name.split(".")[0] if m else None
                        for m in obj.data.materials
                    ],
                    "bounds_min": [min(p[i] for p in points) for i in range(3)],
                    "bounds_max": [max(p[i] for p in points) for i in range(3)],
                }
            )
        entries[m2n.m2i.name_of(obj)] = entry
    return entries


def compare_inventory(source, reimported):
    missing = sorted(set(source) - set(reimported))
    extra = sorted(set(reimported) - set(source))
    differing = {}
    for name in sorted(set(source) & set(reimported)):
        first, second = source[name], reimported[name]
        fields = {}
        for key in ("type", "parent", "mesh", "vertices", "loop_triangles", "materials"):
            if first.get(key) != second.get(key):
                fields[key] = {"before": first.get(key), "after": second.get(key)}
        for key in ("matrix_local", "matrix_world"):
            a, b = first.get(key), second.get(key)
            if not a or not b:
                continue
            worst = max(
                abs(a[r][c] - b[r][c]) for r in range(4) for c in range(4)
            )
            if worst > MATRIX_TOLERANCE:
                fields[key] = {
                    "max_abs_difference": worst,
                    "tolerance": MATRIX_TOLERANCE,
                    "before": a,
                    "after": b,
                }
        for key in ("bounds_min", "bounds_max"):
            a, b = first.get(key), second.get(key)
            if not a or not b:
                continue
            worst = max(abs(a[i] - b[i]) for i in range(3))
            if worst > MATRIX_TOLERANCE:
                fields[key] = {
                    "max_abs_difference": worst,
                    "tolerance": MATRIX_TOLERANCE,
                    "before": a,
                    "after": b,
                }
        if fields:
            differing[name] = fields
    return {
        "missing_objects": missing,
        "extra_objects": extra,
        "differing_objects": differing,
        "matrix_tolerance": MATRIX_TOLERANCE,
        "pass": not missing and not extra and not differing,
    }


def gather(root, key):
    uvs = {}
    for obj in pilot.meshes_under(root):
        uvs[m2n.m2i.name_of(obj)] = corner_signature(obj)
    return {
        "inventory": inventory_of(root),
        "uv": uvs,
        "checks": m2n.checks(root, key),
    }


def run(project_root, keys, staging):
    models = {}
    for key in keys:
        begin = time.perf_counter()
        blend = m2n.source_blend(project_root, key)
        report = m2n.source_report(project_root, key)
        blend_sha = m1.digest(blend)
        report_sha = m1.digest(report)
        entry = {
            "model": key,
            "source_blend": str(blend.relative_to(project_root)),
            "source_blend_sha256": blend_sha,
            "source_blend_sha_matches_pin": blend_sha == m2n.SOURCES[key]["sha256"],
            "source_report": str(report.relative_to(project_root)),
            "source_report_sha256": report_sha,
            "source_report_sha_matches_pin": report_sha == PINNED_REPORT_SHA[key],
        }
        if not (
            entry["source_blend_sha_matches_pin"]
            and entry["source_report_sha_matches_pin"]
        ):
            entry["status"] = "source hash mismatch; nothing measured"
            models[key] = entry
            continue

        m1.open_blend(blend)
        root = bpy.data.objects[m2k.MODELS[key]["root"]]
        m2n.stamp(root, key, blend.relative_to(project_root), blend_sha)
        source_side = gather(root, key)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in [root] + list(root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = root
        target = staging / m2n.SOURCES[key]["fbx"]
        bpy.ops.export_scene.fbx(filepath=str(target), **m2n.EXPORT_SETTINGS)
        entry["fbx_sha256"] = m1.digest(target)
        entry["fbx_bytes"] = target.stat().st_size

        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(target))
        imported_root = next(
            obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_")
        )
        import_side = gather(imported_root, key)

        entry.update(
            {
                "inventory_diff": compare_inventory(
                    source_side["inventory"], import_side["inventory"]
                ),
                "uv_diff": compare_uv(source_side["uv"], import_side["uv"]),
                "motion": {
                    "source": {
                        field: source_side["checks"][field]
                        for field in ("pivot_world", "motion_contract", "poses", "movable_meshes")
                    },
                    "reimported": {
                        field: import_side["checks"][field]
                        for field in ("pivot_world", "motion_contract", "poses", "movable_meshes")
                    },
                    "pass": (
                        source_side["checks"]["pivot_world"]
                        == import_side["checks"]["pivot_world"]
                        and source_side["checks"]["movable_meshes"]
                        == import_side["checks"]["movable_meshes"]
                    ),
                },
                "clearance": {
                    "source": source_side["checks"]["worst_tick_clearance"],
                    "reimported": import_side["checks"]["worst_tick_clearance"],
                    "floor_mm": m2n.SOURCES[key]["floor_mm"],
                    "pass": (
                        import_side["checks"]["worst_tick_clearance"] is not None
                        and import_side["checks"]["worst_tick_clearance"][
                            "distance_mm"
                        ]
                        >= m2n.SOURCES[key]["floor_mm"]
                    ),
                },
                "new_contacts": import_side["checks"]["new_contacts"],
                "triangles": [
                    source_side["checks"]["triangles"],
                    import_side["checks"]["triangles"],
                ],
                "status": "measured",
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
        )
        uv_failures = [
            name for name, row in entry["uv_diff"].items() if not row["pass"]
        ]
        entry["uv_failures"] = uv_failures
        print(
            f"[Opus5MeterDiag] {key}: inventory "
            f"{entry['inventory_diff']['pass']}, uv failures {len(uv_failures)}, "
            f"clearance {entry['clearance']['reimported']['distance_mm']} mm, "
            f"new contacts {len(entry['new_contacts'])}"
        )
        models[key] = entry
    return models


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    prior = project_root / PRIOR_ATTEMPT
    run_id = uuid.uuid4().hex[:12]
    payload = {
        "phase": "M2n1",
        "run_id": run_id,
        "note": (
            "Read-only FBX gate diagnostic (alignment 142.1). Nothing is "
            "published; the export and re-import happen in a temporary "
            "directory."
        ),
        "prior_attempt": {
            "path": PRIOR_ATTEMPT,
            "sha256": m1.digest(prior) if prior.is_file() else None,
            "content": (
                json.loads(prior.read_text()) if prior.is_file() else None
            ),
            "handling": "referenced by hash; not overwritten",
        },
        "m2n_gate_detail": (
            "not_persisted: the four gate failures reported in 141 were never "
            "written to disk and are not reconstructed here from memory"
        ),
        "pinned_report_sha256": PINNED_REPORT_SHA,
        "uv_bound_rule": "2 * 2^-23 * max(1, |value|), per float32 storage",
        "matrix_tolerance": MATRIX_TOLERANCE,
        "models": {},
    }
    started = time.perf_counter()
    staging = Path(tempfile.mkdtemp(prefix="opus5-meter-diag-"))
    try:
        payload["models"] = run(
            project_root, args.models or list(m2n.SOURCES), staging
        )
        payload["status"] = "complete"
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        import shutil

        payload["report_sha_recheck"] = {
            key: m1.digest(m2n.source_report(project_root, key))
            for key in m2n.SOURCES
        }
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / OUTPUT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        shutil.rmtree(staging, ignore_errors=True)
        print(f"[Opus5MeterDiag] {payload.get('status')} -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
