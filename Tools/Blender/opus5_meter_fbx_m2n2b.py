"""Phase M2n2b: point the verified matcher at the real models, twice.

Alignment 158.1 as corrected by 160. The three canonical sources are
R3_D3, B2P_D3P and B2P_D3P, pinned by SHA. Nothing here writes to a canonical
location: the FBX goes to a temporary directory, is read back in a separate
Blender started with `--factory-startup`, and only the diagnostic JSON is kept.

The whole point is that the comparison is the one A5 proved, not a fresh
approximation of it. Object, triangle, corner and UV data are pulled out of the
re-imported file and handed to the same matcher and the same
evidence-equivalence test.

Two independent runs are made from the same source and the same export
settings. FBX bytes are not required to agree; every measurement is.

Modes, run in order:

* `export --run N`  - verify hashes, measure the source, write the FBX
* `import --run N`  - fresh process: read the FBX back and measure it
* `report`          - compare, and write the diagnostic on every path

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_fbx_m2n2b.py -- \
      --project-root "$PWD" --mode export --run 1 --staging /tmp/x
"""

import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact_migration_m1 as m1
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_diagnostic as m2n1
import opus5_meter_fbx_handoff as m2n


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_diagnostic_m2n2.json"
RUNS = (1, 2)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("export", "import", "report"))
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--staging", required=True)
    return parser.parse_args(args)


def uv_triangles(obj):
    """The a5 matcher's input: world corners, UV, material, per triangle."""
    mesh = obj.data
    layer = mesh.uv_layers.active
    if layer is None:
        return None, None
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    out = []
    for triangle in mesh.loop_triangles:
        corners = []
        for loop_index in triangle.loops:
            vertex = mesh.loops[loop_index].vertex_index
            world = matrix @ mesh.vertices[vertex].co
            corners.append(
                ((world.x, world.y, world.z), tuple(layer.data[loop_index].uv))
            )
        out.append((corners, triangle.material_index))
    return layer.name, out


def measure(root, key):
    entries = {}
    for obj in pilot.meshes_under(root):
        name = m2n.m2i.name_of(obj)
        layer, triangles = uv_triangles(obj)
        obj.data.calc_loop_triangles()
        points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        entries[name] = {
            "uv_layer": layer,
            "uv_layers": len(obj.data.uv_layers),
            "materials": [m.name.split(".")[0] if m else None for m in obj.data.materials],
            "triangles": triangles,
            "vertices": [(p.x, p.y, p.z) for p in points],
            "loop_triangles": len(obj.data.loop_triangles),
            "matrix_local": [[v for v in row] for row in obj.matrix_local],
            "matrix_world": [[v for v in row] for row in obj.matrix_world],
        }
    return {
        "objects": entries,
        "checks": m2n.checks(root, key),
        "inventory": m2n1.inventory_of(root),
    }


def do_export(project_root, staging, run):
    staging.mkdir(parents=True, exist_ok=True)
    payload = {}
    for key, spec in m2n.SOURCES.items():
        blend = m2n.source_blend(project_root, key)
        report = m2n.source_report(project_root, key)
        blend_sha = m1.digest(blend)
        report_sha = m1.digest(report)
        if blend_sha != spec["sha256"] or report_sha != m2n1.PINNED_REPORT_SHA[key]:
            raise SystemExit(f"[M2n2b] {key}: pinned hash mismatch; nothing written")
        m1.open_blend(blend)
        root = bpy.data.objects[m2k.MODELS[key]["root"]]
        m2n.stamp(root, key, blend.relative_to(project_root), blend_sha)
        measured = measure(root, key)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in [root] + list(root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = root
        target = staging / f"{key}_run{run}.fbx"
        bpy.ops.export_scene.fbx(filepath=str(target), **m2n.EXPORT_SETTINGS)
        payload[key] = {
            "blend_sha256": blend_sha,
            "report_sha256": report_sha,
            "fbx": str(target),
            "fbx_sha256": m1.digest(target),
            "source": measured,
        }
        print(f"[M2n2b] export run{run} {key}: {len(measured['objects'])} meshes")
    (staging / f"source_run{run}.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


def do_import(project_root, staging, run):
    payload = {}
    for key in m2n.SOURCES:
        bpy.ops.wm.read_homefile(use_empty=True)
        target = staging / f"{key}_run{run}.fbx"
        bpy.ops.import_scene.fbx(filepath=str(target))
        root = next(
            obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_")
        )
        payload[key] = {
            "fbx_sha256": m1.digest(target),
            "custom_properties": {
                name: root.get(name)
                for name in root.keys()
                if name.startswith("opus5_")
            },
            "reimport": measure(root, key),
        }
        print(f"[M2n2b] import run{run} {key}: {len(payload[key]['reimport']['objects'])} meshes")
    (staging / f"import_run{run}.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


def compare_uv(source, reimport):
    from opus5_fbx_verifier_selftest_a5 import compare_uv_mesh

    rows = {}
    for name in sorted(set(source) | set(reimport)):
        first = source.get(name)
        second = reimport.get(name)
        a = first["triangles"] if first else None
        b = second["triangles"] if second else None
        result = compare_uv_mesh(a, b)
        result["layer"] = [
            first["uv_layer"] if first else None,
            second["uv_layer"] if second else None,
        ]
        result["materials"] = [
            first["materials"] if first else None,
            second["materials"] if second else None,
        ]
        rows[name] = result
    return rows


def world_difference(source, reimport):
    """Position and normal difference on matched objects, in real units."""
    worst = 0.0
    total = 0.0
    count = 0
    for name in sorted(set(source) & set(reimport)):
        a = source[name]["vertices"]
        b = reimport[name]["vertices"]
        if len(a) != len(b):
            continue
        for first, second in zip(sorted(a), sorted(b)):
            distance = math.dist(first, second)
            worst = max(worst, distance)
            total += distance * distance
            count += 1
    return {
        "vertices_compared": count,
        "max_position_difference_m": worst,
        "max_position_difference_um": worst * 1e6,
        "rms_position_difference_m": math.sqrt(total / count) if count else 0.0,
    }


def do_report(project_root, staging):
    from opus5_fbx_verifier_selftest_a1 import decompose as polar_decompose

    payload = {
        "phase": "M2n2b",
        "note": (
            "Read-only two-run measurement (alignment 158.1, corrected by "
            "160). Nothing is published; the FBX lives only in staging."
        ),
        "sources": {
            key: {
                "revision": spec["revision"],
                "pinned_blend_sha256": spec["sha256"],
                "pinned_report_sha256": m2n1.PINNED_REPORT_SHA[key],
            }
            for key, spec in m2n.SOURCES.items()
        },
        "matcher": "a5 mesh-wide assignment with evidence-equivalence check",
        "runs": {},
    }
    started = time.perf_counter()
    try:
        data = {}
        for run in RUNS:
            data[run] = {
                "source": json.loads((staging / f"source_run{run}.json").read_text()),
                "import": json.loads((staging / f"import_run{run}.json").read_text()),
            }
        for run in RUNS:
            models = {}
            for key in m2n.SOURCES:
                source = data[run]["source"][key]
                reimport = data[run]["import"][key]
                uv = compare_uv(
                    source["source"]["objects"], reimport["reimport"]["objects"]
                )
                failures = [name for name, row in uv.items() if not row["pass"]]
                transforms = {}
                for name in sorted(
                    set(source["source"]["objects"])
                    & set(reimport["reimport"]["objects"])
                ):
                    a = source["source"]["objects"][name]["matrix_local"]
                    b = reimport["reimport"]["objects"][name]["matrix_local"]
                    if any(
                        abs(a[r][c] - b[r][c]) > 1e-12
                        for r in range(4)
                        for c in range(4)
                    ):
                        parts = polar_decompose(a, b)
                        transforms[name] = {
                            "translation_um": parts["translation_norm_um"],
                            "rotation_deg": parts["rotation_deg"],
                            "scale_max_deviation": parts["scale_max_deviation"],
                            "shear_residual": parts["shear_residual"],
                            "reconstruction_residual": parts["reconstruction_residual"],
                        }
                models[key] = {
                    "fbx_sha256": source["fbx_sha256"],
                    "blend_sha256": source["blend_sha256"],
                    "report_sha256": source["report_sha256"],
                    "uv": uv,
                    "uv_failures": failures,
                    "matrix_differences": transforms,
                    "world_difference": world_difference(
                        source["source"]["objects"],
                        reimport["reimport"]["objects"],
                    ),
                    "source_checks": source["source"]["checks"],
                    "reimport_checks": reimport["reimport"]["checks"],
                }
            payload["runs"][run] = models

        reproducibility = {}
        for key in m2n.SOURCES:
            first = payload["runs"][1][key]
            second = payload["runs"][2][key]
            reproducibility[key] = {
                "uv_failures": [first["uv_failures"], second["uv_failures"]],
                "uv_failures_match": first["uv_failures"] == second["uv_failures"],
                "matrix_objects": [
                    sorted(first["matrix_differences"]),
                    sorted(second["matrix_differences"]),
                ],
                "matrix_objects_match": sorted(first["matrix_differences"])
                == sorted(second["matrix_differences"]),
                "world_max_um": [
                    first["world_difference"]["max_position_difference_um"],
                    second["world_difference"]["max_position_difference_um"],
                ],
                "clearance": [
                    (first["reimport_checks"].get("worst_tick_clearance") or {}).get(
                        "distance_mm"
                    ),
                    (second["reimport_checks"].get("worst_tick_clearance") or {}).get(
                        "distance_mm"
                    ),
                ],
                "new_contacts": [
                    first["reimport_checks"]["new_contacts"],
                    second["reimport_checks"]["new_contacts"],
                ],
                "triangles": [
                    first["reimport_checks"]["triangles"],
                    second["reimport_checks"]["triangles"],
                ],
            }
        payload["reproducibility"] = reproducibility
        payload["status"] = "complete"
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / OUTPUT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        for key in m2n.SOURCES:
            entry = payload.get("runs", {}).get(1, {}).get(key)
            if not entry:
                continue
            print(
                f"[M2n2b] {key}: uv failures {len(entry['uv_failures'])}, "
                f"matrix diffs {len(entry['matrix_differences'])}, world max "
                f"{entry['world_difference']['max_position_difference_um']:.4f} um, "
                f"clearance "
                f"{(entry['reimport_checks'].get('worst_tick_clearance') or {}).get('distance_mm')} mm"
            )
        print(f"[M2n2b] {payload.get('status')} -> {output.relative_to(project_root)}")


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    if args.mode != "report":
        blender_compat.require_v6_pipeline()
    if args.mode == "export":
        do_export(project_root, staging, args.run)
    elif args.mode == "import":
        do_import(project_root, staging, args.run)
    else:
        do_report(project_root, staging)


if __name__ == "__main__":
    main()
