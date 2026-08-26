"""Phase M2n: FBX handoff for the three approved meters.

Alignment 140.1. Same shape as the Toggle handoff: export the approved
candidates, then prove the FBX by reading it back in a separate Blender started
with `--factory-startup` and re-running the checks that decided the shape.

FBX bytes are not reproducible and are not compared. The re-imported model is:
inventory, hierarchy, transforms, materials, UVs, triangles, bounds, custom
properties, the motion contract, and - the part the last several phases were
about - the exact surface clearance to the endpoint ticks over the full travel.

Three modes, run in order:

* `export`  - verify source and report hashes, write FBX and export reports
* `verify`  - fresh process: re-import each FBX and write round-trip reports
* `promote` - check every gate, then publish FBX first and the summary last

A failure leaves the attempt JSON and publishes nothing.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_fbx_handoff.py -- \
      --project-root "$PWD" --mode export --staging /tmp/opus5-meter-fbx
"""

import argparse
import json
import math
import shutil
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
import opus5_d3_exact_corrected_build as m2m2
import opus5_d3_solver_diagnostic as diag
import opus5_d5_candidate_build as m2e
import opus5_d6_bounded_correction as m2k1
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_publish as publish
import opus5_toggle_fbx_handoff as m2i


HANDOFF = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_handoff.json"
ATTEMPT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_attempt.json"

# Alignment 140 pins every source by hash.
SOURCES = {
    "MeterRound": {
        "revision": "R3_D3",
        "included": ["D-6", "D-3"],
        "blend": "BL_MeterRound_KineticSafety_V6_Opus5_R3_D3_Retopo.blend",
        "report": "MeterRound_KineticSafety_V6_Opus5_R3_D3.json",
        "sha256": "4bc590d446a3cb70888956530a674013e50617ad00f14faa60d8f5767987219f",
        "fbx": "SM_MeterRound_KineticSafety_V6_Opus5_R3_D3.fbx",
        "triangles": 4636,
        "floor_mm": 0.700,
        "source_clearance_mm": 2.499998,
    },
    "MeterMedium": {
        "revision": "B2P_D3P",
        "included": ["D-6", "D-3"],
        "blend": "BL_MeterMedium_KineticSafety_V6_Opus5_B2P_D3P_Retopo.blend",
        "report": "MeterMedium_KineticSafety_V6_Opus5_B2P_D3P.json",
        "sha256": "98bff1c03307cd97f4b1b9eeced801850f8c76cfcb8483c01ff57704ee9888c4",
        "fbx": "SM_MeterMedium_KineticSafety_V6_Opus5_B2P_D3P.fbx",
        "triangles": 8920,
        "floor_mm": 1.410,
        "source_clearance_mm": 1.420018,
    },
    "MeterLarge": {
        "revision": "B2P_D3P",
        "included": ["D-6", "D-3"],
        "blend": "BL_MeterLarge_KineticSafety_V6_Opus5_B2P_D3P_Retopo.blend",
        "report": "MeterLarge_KineticSafety_V6_Opus5_B2P_D3P.json",
        "sha256": "965336a40bb28b8b19672b15fdba60d5f08de94935cecac8ffce2c6f8e28e266",
        "fbx": "SM_MeterLarge_KineticSafety_V6_Opus5_B2P_D3P.fbx",
        "triangles": 10472,
        "floor_mm": 2.110,
        "source_clearance_mm": 2.120095,
    },
}

MOTION = {
    "pivot": "needle_pivot",
    "movable": "needle",
    "axis": "Y",
    "range_deg": [-55.0, 55.0],
    "rest_deg": 0.0,
}
POSES = m2k.POSES
EXPORT_SETTINGS = m2i.EXPORT_SETTINGS


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("export", "verify", "promote"))
    parser.add_argument("--staging", required=True)
    parser.add_argument("--trial", action="store_true")
    return parser.parse_args(args)


def source_blend(project_root, key):
    return m2l.theme_dir(project_root) / SOURCES[key]["blend"]


def source_report(project_root, key):
    return project_root / m2l.REPORT_DIR / SOURCES[key]["report"]


def fbx_path(project_root, key):
    return (
        m2l.theme_dir(project_root) / "staging/fbx" / SOURCES[key]["fbx"]
    )


def report_paths(project_root, key):
    base = project_root / m2l.REPORT_DIR
    stem = SOURCES[key]["fbx"].replace("SM_", "").replace(".fbx", "")
    return {
        "export": base / f"{stem}_fbx_export.json",
        "round_trip": base / f"{stem}_fbx_round_trip.json",
    }


def stamp(root, key, source, sha):
    properties = {
        "opus5_model": key,
        "opus5_theme": m2k.THEME,
        "opus5_revision": SOURCES[key]["revision"],
        "opus5_included_revisions": ",".join(SOURCES[key]["included"]),
        "opus5_source_path": str(source),
        "opus5_source_sha256": sha,
        "opus5_defect_d3_clearance_mm": str(m2m.CLEARANCE_MM[key]),
        "opus5_motion_pivot": MOTION["pivot"],
        "opus5_motion_object": MOTION["movable"],
        "opus5_motion_axis": MOTION["axis"],
        "opus5_motion_range_deg": "-55.0,55.0",
        "opus5_motion_rest_deg": "0.0",
        "opus5_unit_scale": "1 unit = 1 metre",
        "opus5_axis": "Blender Z-up, exported -Z forward / Y up",
        "opus5_mount_plane": "max Y == 0",
    }
    for name, value in properties.items():
        root[name] = value
    return properties


def uv_hash(root):
    import hashlib
    import struct

    digest = hashlib.sha256()
    for obj in sorted(pilot.meshes_under(root), key=lambda o: m2i.name_of(o)):
        layer = obj.data.uv_layers.active
        if layer is None:
            continue
        digest.update(m2i.name_of(obj).encode())
        for datum in layer.data:
            digest.update(struct.pack("<2d", datum.uv[0], datum.uv[1]))
    return digest.hexdigest()


def checks(root, key):
    """Motion, clearance and contact, on whatever model is currently open."""
    pivot = bpy.data.objects[MOTION["pivot"]]
    centre = pivot.matrix_world.translation.copy()
    radius = max(m2m.CLEARANCE_MM[key] * 3.0 / 1000.0, m2m1.SEARCH_FLOOR_M)
    worst, per_tick = diag.measure(root, pivot, centre, radius)

    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    statics = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name not in m2e.m2d.hierarchy(obj)
    ]
    contacts = m2k.sweep_contacts(pivot, movable, statics, POSES)
    unresolved = []
    for label, entry in contacts.items():
        if entry["clear"]:
            continue
        mover, static = label.split(" x ")
        kind = (
            "intended: the needle turning in its bearing boss"
            if "boss" in static
            else "known: hub inside the bearing stack"
            if "polygon_bezel" in static
            else "known D-3 endpoint tick"
            if "tick" in static
            else "new"
        )
        if kind == "new":
            unresolved.append(label)

    points = [
        obj.matrix_world @ Vector(corner)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render
        for corner in obj.bound_box
    ]
    bounds = {
        "min": [round(min(p[i] for p in points), 6) for i in range(3)],
        "max": [round(max(p[i] for p in points), 6) for i in range(3)],
    }
    triangles = sum(
        len(obj.data.loop_triangles)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and (obj.data.calc_loop_triangles() or True)
    )
    return {
        "pivot_world": [round(v, 6) for v in centre],
        "motion_contract": MOTION,
        "poses": len(POSES),
        "movable_meshes": [m2i.name_of(obj) for obj in movable],
        "static_meshes": len(statics),
        "worst_tick_clearance": worst,
        "per_tick": per_tick,
        "new_contacts": unresolved,
        "triangles": triangles,
        "expected_triangles": SOURCES[key]["triangles"],
        "bounds": bounds,
        "envelope": m2k1.envelope_row(key, bounds),
        "uv_sha256": uv_hash(root),
        "materials": sorted(
            {
                material.name.split(".")[0]
                for obj in pilot.meshes_under(root)
                for material in obj.data.materials
                if material
            }
        ),
    }


def do_export(project_root, staging):
    staging.mkdir(parents=True, exist_ok=True)
    for key, spec in SOURCES.items():
        actual = m1.digest(source_blend(project_root, key))
        if actual != spec["sha256"]:
            raise SystemExit(
                f"[Opus5MeterFbx] {key}: source hash mismatch, nothing written"
            )
    results = {}
    for key, spec in SOURCES.items():
        begin = time.perf_counter()
        path = source_blend(project_root, key)
        m1.open_blend(path)
        root = bpy.data.objects[m2k.MODELS[key]["root"]]
        properties = stamp(root, key, path.relative_to(project_root), spec["sha256"])
        inventory = m2i.describe(root)
        measured = checks(root, key)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in [root] + list(root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = root
        target = staging / spec["fbx"]
        bpy.ops.export_scene.fbx(filepath=str(target), **EXPORT_SETTINGS)
        if not target.is_file():
            raise SystemExit(f"[Opus5MeterFbx] {key}: export wrote nothing")

        results[key] = {
            "model": key,
            "revision": spec["revision"],
            "included_revisions": spec["included"],
            "source": str(path.relative_to(project_root)),
            "source_sha256": spec["sha256"],
            "source_report": str(
                source_report(project_root, key).relative_to(project_root)
            ),
            "source_report_sha256": m1.digest(source_report(project_root, key)),
            "fbx": spec["fbx"],
            "fbx_sha256": m1.digest(target),
            "fbx_bytes": target.stat().st_size,
            "export_settings": {
                name: sorted(value) if isinstance(value, set) else value
                for name, value in EXPORT_SETTINGS.items()
            },
            "custom_properties": properties,
            "inventory": inventory,
            "checks": measured,
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
            "authoring_environment": blender_compat.provenance(),
        }
        print(
            f"[Opus5MeterFbx] export {key}: {len(inventory)} objects, tris "
            f"{measured['triangles']}, clearance "
            f"{measured['worst_tick_clearance']['distance_mm']} mm, "
            f"{target.stat().st_size} bytes"
        )
    (staging / "export.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )


def do_verify(project_root, staging):
    exported = json.loads((staging / "export.json").read_text())
    results = {}
    for key, spec in SOURCES.items():
        begin = time.perf_counter()
        bpy.ops.wm.read_homefile(use_empty=True)
        target = staging / spec["fbx"]
        bpy.ops.import_scene.fbx(filepath=str(target))
        root = next(
            obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_")
        )
        results[key] = {
            "model": key,
            "fbx": spec["fbx"],
            "fbx_sha256": m1.digest(target),
            "reimported_in": "separate Blender process started with --factory-startup",
            "inventory": m2i.describe(root),
            "custom_properties": {
                name: root.get(name)
                for name in exported[key]["custom_properties"]
            },
            "checks": checks(root, key),
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
            "authoring_environment": blender_compat.provenance(),
        }
        print(
            f"[Opus5MeterFbx] verify {key}: tris "
            f"{results[key]['checks']['triangles']}, clearance "
            f"{results[key]['checks']['worst_tick_clearance']['distance_mm']} mm"
        )
    (staging / "round_trip.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )


def compare(key, exported, imported):
    spec = SOURCES[key]
    before, after = exported["inventory"], imported["inventory"]
    # m2i.compare expects the Toggle report's `motion` block; this phase keeps
    # its checks under `checks`, so the inventory is compared directly.
    missing = sorted(set(before) - set(after))
    extra = sorted(set(after) - set(before))
    changed = {}
    for name in sorted(set(before) & set(after)):
        first, second = before[name], after[name]
        difference = {
            field: [first.get(field), second.get(field)]
            for field in (
                "type", "parent", "vertices", "loop_triangles", "materials"
            )
            if first.get(field) != second.get(field)
        }
        for side in ("min", "max"):
            a = (first.get("bounds") or {}).get(side)
            b = (second.get("bounds") or {}).get(side)
            if a and b and any(
                abs(a[i] - b[i]) > m2i.BOUNDS_TOLERANCE_M for i in range(3)
            ):
                difference[f"bounds_{side}"] = [a, b]
        if difference:
            changed[name] = difference
    inventory = {
        "missing": missing,
        "extra": extra,
        "changed": changed,
        "pass": not missing and not extra and not changed,
    }
    properties = {
        name: [value, imported["custom_properties"].get(name)]
        for name, value in exported["custom_properties"].items()
        if imported["custom_properties"].get(name) != value
    }
    source_checks, import_checks = exported["checks"], imported["checks"]
    clearance = import_checks["worst_tick_clearance"]
    gates = {
        "inventory_identical": inventory,
        "custom_properties_restored": {
            "differences": properties, "pass": not properties
        },
        "triangles": {
            "expected": spec["triangles"],
            "measured": import_checks["triangles"],
            "pass": import_checks["triangles"] == spec["triangles"],
        },
        "uv_preserved": {
            "source": source_checks["uv_sha256"],
            "reimported": import_checks["uv_sha256"],
            "pass": source_checks["uv_sha256"] == import_checks["uv_sha256"],
        },
        "materials": {
            "source": source_checks["materials"],
            "reimported": import_checks["materials"],
            "pass": source_checks["materials"] == import_checks["materials"],
        },
        "motion_contract": {
            "pivot_world": [
                source_checks["pivot_world"], import_checks["pivot_world"]
            ],
            "movable": [
                source_checks["movable_meshes"], import_checks["movable_meshes"]
            ],
            "poses": import_checks["poses"],
            "pass": (
                source_checks["pivot_world"] == import_checks["pivot_world"]
                and source_checks["movable_meshes"]
                == import_checks["movable_meshes"]
                and import_checks["poses"] == len(POSES)
            ),
        },
        "envelope": {
            "source": source_checks["envelope"],
            "reimported": import_checks["envelope"],
            "pass": import_checks["envelope"]["within_envelope"],
        },
        "tick_clearance": {
            "floor_mm": spec["floor_mm"],
            "source_mm": spec["source_clearance_mm"],
            "reimported_mm": clearance["distance_mm"] if clearance else None,
            "difference_from_source_mm": (
                round(clearance["distance_mm"] - spec["source_clearance_mm"], 6)
                if clearance
                else None
            ),
            "pair": clearance["pair"] if clearance else None,
            "pose_deg": clearance["pose_deg"] if clearance else None,
            "feature": clearance["feature"] if clearance else None,
            "pass": bool(clearance) and clearance["distance_mm"] >= spec["floor_mm"],
        },
        "no_new_contact": {
            "new_contacts": import_checks["new_contacts"],
            "pass": not import_checks["new_contacts"],
        },
    }
    return gates


def do_promote(project_root, staging, trial):
    exported = json.loads((staging / "export.json").read_text())
    imported = json.loads((staging / "round_trip.json").read_text())
    themes = {}
    problems = []
    for key in SOURCES:
        gates = compare(key, exported[key], imported[key])
        failures = [
            name
            for name, gate in gates.items()
            if not (gate["pass"] if isinstance(gate, dict) else gate)
        ]
        problems.extend(f"{key}: {name}" for name in failures)
        themes[key] = {
            "export": exported[key],
            "round_trip": imported[key],
            "gates": gates,
            "pass": not failures,
        }
        print(f"[Opus5MeterFbx] {key}: pass={not failures} {failures}")

    targets = {key: fbx_path(project_root, key) for key in SOURCES}
    reports = {key: report_paths(project_root, key) for key in SOURCES}
    if trial:
        bay = Path(staging) / "promote"
        bay.mkdir(parents=True, exist_ok=True)
        targets = {key: bay / SOURCES[key]["fbx"] for key in SOURCES}
        reports = {
            key: {kind: bay / path.name for kind, path in value.items()}
            for key, value in reports.items()
        }
        handoff_path = bay / "meter_d3_fbx_handoff.json"
    else:
        handoff_path = project_root / HANDOFF

    existing = any(path.exists() for path in targets.values()) or any(
        path.exists() for value in reports.values() for path in value.values()
    )
    decision = publish.publish_guard(existing, handoff_path.exists(), problems, trial)
    record = dict(decision)

    if decision["may_write_blend"]:
        for key in SOURCES:
            current = m1.digest(source_blend(project_root, key))
            if current != SOURCES[key]["sha256"]:
                raise publish.PublishFailed(f"{key}: source changed before publish")
            targets[key].parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staging / SOURCES[key]["fbx"], targets[key])
            promoted = m1.digest(targets[key])
            if promoted != exported[key]["fbx_sha256"]:
                raise publish.PublishFailed(f"{key}: promoted FBX does not match")
            themes[key]["promoted_fbx_sha256"] = promoted
            for kind, path in reports[key].items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(
                        themes[key]["export" if kind == "export" else "round_trip"],
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

    if decision["may_write_report"]:
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(
            json.dumps(
                {
                    "phase": "M2n",
                    "note": (
                        "FBX handoff for the three approved meters (alignment "
                        "140.1). FBX bytes are not compared; the re-imported "
                        "model is."
                    ),
                    "publish": record,
                    "round_trip_process": (
                        "separate Blender started with --factory-startup"
                    ),
                    "motion_contract": MOTION,
                    "export_settings": {
                        name: sorted(value) if isinstance(value, set) else value
                        for name, value in EXPORT_SETTINGS.items()
                    },
                    "models": {
                        key: {
                            "source": entry["export"]["source"],
                            "source_sha256": entry["export"]["source_sha256"],
                            "source_report_sha256": entry["export"][
                                "source_report_sha256"
                            ],
                            "revision": entry["export"]["revision"],
                            "fbx": str(
                                fbx_path(project_root, key).relative_to(project_root)
                            ),
                            "fbx_sha256": entry["export"]["fbx_sha256"],
                            "fbx_bytes": entry["export"]["fbx_bytes"],
                            "reports": {
                                kind: str(path.relative_to(project_root))
                                for kind, path in report_paths(
                                    project_root, key
                                ).items()
                            },
                            "gates": {
                                name: (
                                    gate["pass"]
                                    if isinstance(gate, dict)
                                    else gate
                                )
                                for name, gate in entry["gates"].items()
                            },
                            "pass": entry["pass"],
                        }
                        for key, entry in themes.items()
                    },
                    "problems": problems,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"[Opus5MeterFbx] {record['mode']}: {record['reason']}")


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    blender_compat.require_v6_pipeline()
    try:
        if args.mode == "export":
            do_export(project_root, staging)
        elif args.mode == "verify":
            do_verify(project_root, staging)
        else:
            do_promote(project_root, staging, args.trial)
    except Exception:
        (project_root / ATTEMPT).write_text(
            json.dumps(
                {
                    "phase": "M2n",
                    "mode": args.mode,
                    "status": "exception",
                    "traceback": traceback.format_exc(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()
