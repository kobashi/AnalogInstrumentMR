"""Phase M2n2b2: can the legacy staging answer the M2n2b1 gates? Read only.

Alignment 180. The ten §165.2 originals are not modified, no canonical Blend is
opened, and no FBX is re-exported. The six existing FBX are imported into a
factory-startup file to observe what came back; that is the only Blender work.

Three questions, kept apart:

* does the old snapshot schema even carry the evidence each M2n2b1 gate needs?
  Each field is `available_and_valid`, `available_but_legacy_semantics` or
  `missing`. Nothing is inferred from the FBX to fill a gap in the JSON.
* of what it does carry, what survives re-judging under the new matcher and
  the new validity rule?
* the two runs' FBX differ byte for byte. That is not a geometry difference
  until geometry says so, so both are re-imported and compared as meshes.

An old FBX re-imported gives a reimport-side snapshot and nothing more. With no
source-evaluated polygons and no export-normalized snapshot in the legacy data,
surface preservation and split-normal preservation cannot be decided at all,
and are reported as missing rather than assumed.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_m2n2b2_readonly_diagnostic.py -- \
      --project-root "$PWD" --mode reimport --staging /tmp/x
"""

import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_fbx_adapter_completion as done


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_d3_fbx_diagnostic_m2n2b2.json"
STAGING_BASE = (
    "/private/tmp/claude-501/-Users-kblab-Documents-AnalogInstrumentMR/"
    "9095cedd-b389-4100-b424-90860fcdc34c/scratchpad"
)
# Alignment 165.2, copied here so the check is against the record rather than
# against whatever happens to be on disk.
ORIGINALS = {
    "m2n2b_r1/MeterRound_run1.fbx": (
        199052, "2fd3a83ca22b10d87dbda46215bd4152847f71614f33a3c1087826d6bdbdb46b"
    ),
    "m2n2b_r1/MeterMedium_run1.fbx": (
        418796, "eb4077a9e917a6bb5daf848796be16e21b971caa16d88503a4d442bd17ad76b2"
    ),
    "m2n2b_r1/MeterLarge_run1.fbx": (
        490396, "23b4f8aff682640f0cc115fd703de153501c2aeb4da285c1ba125754fbebd91e"
    ),
    "m2n2b_r2/MeterRound_run2.fbx": (
        199052, "97830c18079972f3c8e190564d1bfa2554422bdeae478e41d33282deea707750"
    ),
    "m2n2b_r2/MeterMedium_run2.fbx": (
        418796, "a6b694d5144dd0f3b0eca0fc45ff9b382fe73a8dc40a2b1cbe5775be1f98a1d1"
    ),
    "m2n2b_r2/MeterLarge_run2.fbx": (
        490396, "7c605cb05467d38559eafaabc05777683e07e05989964ea91bfae4ea05ea2825"
    ),
    "m2n2b_r1/source_run1.json": (
        3473446, "039f58ed481d20836e85b429933762f154e9872165dcece4a3ed2e03fe2f16a3"
    ),
    "m2n2b_r1/import_run1.json": (
        3626110, "355638b947ebc912ae23cb77477887690c10de567062e08ef89393f4f40c98cb"
    ),
    "m2n2b_r2/source_run2.json": (
        3473446, "261409c5a1f4283b8beaa0a77b488ef29a50e0d253f5b6bb7d4b60a8110ed023"
    ),
    "m2n2b_r2/import_run2.json": (
        3626110, "3061584c7f57c31f901a014515da06d1e3230df288f2fd03e8fc494e34e6c5b8"
    ),
}
MODELS = ("MeterRound", "MeterMedium", "MeterLarge")
RUNS = (1, 2)
# Above this a component's min / max count solves stop being cheap. Nothing is
# quietly skipped: the object records that ambiguity was not evaluated and the
# result cannot count as evidence either way.
AMBIGUITY_BUDGET = 48


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("reimport", "report"))
    parser.add_argument("--staging", required=True)
    return parser.parse_args(args)


def original(name):
    return Path(STAGING_BASE) / name


def verify_originals():
    rows = {}
    for name, (size, digest) in ORIGINALS.items():
        path = original(name)
        if not path.exists():
            rows[name] = {"present": False, "matches_record": False}
            continue
        actual_size = path.stat().st_size
        actual_digest = m1.digest(path)
        rows[name] = {
            "present": True,
            "recorded_bytes": size,
            "actual_bytes": actual_size,
            "recorded_sha256": digest,
            "actual_sha256": actual_digest,
            "matches_record": actual_size == size and actual_digest == digest,
        }
    return {
        "checked": len(rows),
        "matching": sum(1 for row in rows.values() if row["matches_record"]),
        "files": rows,
        "pass": all(row["matches_record"] for row in rows.values()),
    }


# --------------------------------------------------------------------------
# Reimport of the existing FBX - observation only


def snapshot_existing(path):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    roots = [
        obj
        for obj in bpy.data.objects
        if obj.parent is None and obj.name.startswith("PF_Visual_")
    ]
    if len(roots) != 1:
        raise AssertionError(f"{path.name}: {len(roots)} roots")
    root = roots[0]
    payload = {}
    for obj in [root] + list(root.children_recursive):
        entry = done.read_object(obj, root, evaluated=False)
        entry["parent"] = obj.parent.name if obj.parent else None
        if entry["type"] == "MESH":
            # The polygons are reimport-side only and there is nothing on the
            # source side to compare them with, so only their shape is kept.
            entry["polygon_loop_counts"] = sorted(
                {len(item["corners"]) for item in entry["polygons"]}
            )
            entry["polygon_count"] = len(entry["polygons"])
            entry.pop("polygons")
            entry.pop("vertex_order")
        payload[obj.name] = entry
    return {
        "root": root.name,
        "custom_properties": {
            key: str(root[key]) for key in root.keys() if key.startswith("opus5_")
        },
        "objects": payload,
    }


def do_reimport(staging):
    staging.mkdir(parents=True, exist_ok=True)
    payload = {}
    for run in RUNS:
        for model in MODELS:
            name = f"m2n2b_r{run}/{model}_run{run}.fbx"
            path = original(name)
            payload.setdefault(f"run{run}", {})[model] = snapshot_existing(path)
            print(f"[Opus5M2n2b2] reimport run{run} {model}")
    (staging / "new_reimport.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------
# Schema sufficiency


def legacy_documents():
    documents = {}
    for run in RUNS:
        documents[f"run{run}"] = {
            "source": json.loads(
                original(f"m2n2b_r{run}/source_run{run}.json").read_text()
            ),
            "import": json.loads(
                original(f"m2n2b_r{run}/import_run{run}.json").read_text()
            ),
        }
    return documents


def schema_matrix(documents):
    """What each M2n2b1 gate would need, against what the old schema holds."""
    sample = documents["run1"]
    counts = {}
    for model in MODELS:
        source = sample["source"][model]["source"]["objects"]
        reimport = sample["import"][model]["reimport"]["objects"]
        counts[model] = {
            "objects": len(source),
            "source_with_triangle_payload": sum(
                1 for item in source.values() if item["triangles"] is not None
            ),
            "reimport_with_triangle_payload": sum(
                1 for item in reimport.values() if item["triangles"] is not None
            ),
            "source_uv_layer_counts": sorted(
                {item["uv_layers"] for item in source.values()}
            ),
            "reimport_uv_layer_counts": sorted(
                {item["uv_layers"] for item in reimport.values()}
            ),
        }
    return {
        "object_counts": counts,
        "fields": {
            "polygon_surface": {
                "needs": "source evaluated polygons and an export-normalized copy",
                "legacy_field": None,
                "status": "missing",
                "note": (
                    "the old snapshot stores loop triangles only. Boundary, "
                    "diagonal, per-polygon area and orientation cannot be "
                    "recovered from a triangle list, and re-deriving a "
                    "triangulation is what alignment 167 got wrong"
                ),
            },
            "position": {
                "needs": "triangle corners, matched by the A5 assignment",
                "legacy_field": "objects[name].triangles[i][0][k][0]",
                "status": "available_and_valid",
                "note": (
                    "only for objects that carry a triangle payload; the rest "
                    "have a vertex list in index order and nothing else"
                ),
            },
            "position_without_triangles": {
                "needs": "geometric correspondence",
                "legacy_field": "objects[name].vertices",
                "status": "available_but_legacy_semantics",
                "note": (
                    "index-order correspondence, which is the assumption "
                    "alignment 161 showed to be wrong when it holds by luck"
                ),
            },
            "face_normal": {
                "needs": "per-triangle normal",
                "legacy_field": None,
                "status": "missing",
            },
            "split_normal": {
                "needs": "per-corner normal",
                "legacy_field": None,
                "status": "missing",
                "note": "no normal of any kind was captured in the old schema",
            },
            "uv_per_layer": {
                "needs": "every layer by name, every corner value",
                "legacy_field": "objects[name].triangles[i][0][k][1]",
                "status": "available_but_legacy_semantics",
                "note": (
                    "one layer only, and the capture keyed on the active "
                    "layer, so an object whose active layer was unset has no "
                    "UV evidence at all on the source side"
                ),
            },
            "uv_layer_names": {
                "needs": "the layer list and its order",
                "legacy_field": "objects[name].uv_layer / uv_layers",
                "status": "available_but_legacy_semantics",
                "note": "a count and the active name; not the list of names",
            },
            "material": {
                "needs": "per-triangle material index and the slot names",
                "legacy_field": "objects[name].materials, triangles[i][1]",
                "status": "available_and_valid",
            },
            "hierarchy_parent_topology": {
                "needs": "(identity, parent, type) on both sides",
                "legacy_field": "inventory[name].type / parent",
                "status": "available_and_valid",
            },
            "transform": {
                "needs": "local and root-relative matrices, scalar by scalar",
                "legacy_field": "inventory[name].matrix_local / matrix_world",
                "status": "available_and_valid",
                "note": "world, not root-relative; the roots are at identity",
            },
            "identity": {
                "needs": "an explicit id that does not depend on a name",
                "legacy_field": "object name",
                "status": "available_but_legacy_semantics",
                "note": "legacy_name_identity; not equivalent evidence",
            },
            "export_normalized_snapshot": {
                "needs": "the mesh that was exported, measured as exported",
                "legacy_field": None,
                "status": "missing",
            },
            "validity_and_ambiguity": {
                "needs": "coverage and evidence per kind",
                "legacy_field": None,
                "status": "available_and_valid",
                "note": "computable wherever a triangle payload exists",
            },
        },
    }


def linkage(documents):
    rows = {}
    for run in RUNS:
        key = f"run{run}"
        source = documents[key]["source"]
        imported = documents[key]["import"]
        for model in MODELS:
            path = original(f"m2n2b_r{run}/{model}_run{run}.fbx")
            actual = m1.digest(path)
            declared_source = source[model]["fbx_sha256"]
            declared_import = imported[model]["fbx_sha256"]
            rows[f"{key}/{model}"] = {
                "source_json_declares": declared_source,
                "import_json_declares": declared_import,
                "file_on_disk": actual,
                "source_fbx_path": source[model]["fbx"],
                "path_points_at_this_run": f"_run{run}.fbx" in source[model]["fbx"],
                "consistent": declared_source == declared_import == actual,
            }
    return {
        "rows": rows,
        "pass": all(row["consistent"] for row in rows.values()),
        "note": (
            "run1 and run2 FBX differ byte for byte by design; that is not "
            "read as a geometry difference anywhere in this report"
        ),
    }


# --------------------------------------------------------------------------
# What can still be judged from the legacy data


def as_new_mesh(legacy_triangles):
    """The old payload is already A5's shape, minus every normal."""
    return [
        {
            "corners": [
                {
                    "position": list(corner[0]),
                    "split_normal": None,
                    "uv": {"UVMap": list(corner[1])},
                }
                for corner in triangle[0]
            ],
            "face_normal": None,
            "material": triangle[1],
            "area": done.triangle_area([corner[0] for corner in triangle[0]]),
        }
        for triangle in legacy_triangles
    ]


def position_uv_only(source, reimport):
    """Position and UV, with the normal kinds reported as never measured."""
    solved = done.geometry_assignment(
        source, reimport, kinds=("position",), ambiguity_budget=AMBIGUITY_BUDGET
    )
    positions = []
    for pair in solved["pairs"]:
        positions.extend(solved["detail"][pair]["positions"])
    expected = len(source) * 3
    geometry = done.scalar_measurement(expected, positions)
    geometry["bound"] = done.POSITION_BOUND_M
    geometry["unit"] = "m"
    geometry["pass"] = bool(
        geometry["measurement_valid"]
        and geometry["max"] is not None
        and geometry["max"] <= geometry["bound"]
    )
    absent = {
        "expected": len(source),
        "matched": 0,
        "coverage": 0.0,
        "scalar_count": 0,
        "measurement_valid": False,
        "multiset": None,
        "max": None,
        "rms": None,
        "pass": False,
        "reason": "the legacy schema captured no normals",
    }
    uv = done.compare_uv_mesh(
        [
            (
                tuple(
                    (tuple(corner["position"]), tuple(corner["uv"]["UVMap"]))
                    for corner in triangle["corners"]
                ),
                triangle["material"],
            )
            for triangle in source
        ],
        [
            (
                tuple(
                    (tuple(corner["position"]), tuple(corner["uv"]["UVMap"]))
                    for corner in triangle["corners"]
                ),
                triangle["material"],
            )
            for triangle in reimport
        ],
    )
    return {
        "geometry": geometry,
        "face_normal": dict(absent),
        "split_normal": dict(absent, expected=len(source) * 3),
        "uv_UVMap": uv,
        "assignment": {
            "matched_triangles": len(solved["pairs"]),
            "expected_triangles": len(source),
            "unconsumed_reimport": len(reimport) - len(solved["pairs"]),
            "aggregate_ambiguous": solved["aggregate_ambiguous"],
            "kind_separated_ambiguous": solved["kind_separated_ambiguous"],
            "edge_ambiguous": solved["edge_ambiguous"],
            "ambiguity_evaluated": solved["ambiguity_evaluated"],
            "ambiguity_components_skipped": solved["ambiguity_components_skipped"],
            "measured_kinds": solved["measured_kinds"],
        },
    }


def corner_keys(key, triangles):
    return {key(corner[0]) for triangle in triangles for corner in triangle[0]}


def edge_keys(key, triangles):
    found = set()
    for triangle in triangles:
        points = [key(corner[0]) for corner in triangle[0]]
        for index in range(3):
            found.add(tuple(sorted([points[index], points[(index + 1) % 3]])))
    return found


def triangulation_agreement(source, reimport):
    """Same surface, or the same surface cut differently?

    A coverage figure on its own does not say why triangles failed to pair.
    If both sides carry the same corner positions but not the same edges, the
    two triangulated one surface along different diagonals - which is the
    defect M2n2b1 was built to prevent, seen here in the existing staging.
    """
    # Snapped to a tolerance, not rounded to a decimal: the round trip moves a
    # position by ~1e-8 m, which a fixed decimal key can push across a
    # boundary and report as a different vertex. Seeded from the source so the
    # reimport attaches to the source's representatives.
    key, _ = done.make_snapper()
    for triangle in source:
        for corner in triangle[0]:
            key(corner[0])
    corners_source = corner_keys(key, source)
    corners_reimport = corner_keys(key, reimport)
    edges_source = edge_keys(key, source)
    edges_reimport = edge_keys(key, reimport)
    return {
        "corner_positions": [len(corners_source), len(corners_reimport)],
        "corner_positions_equal": corners_source == corners_reimport,
        "edges": [len(edges_source), len(edges_reimport)],
        "edges_equal": edges_source == edges_reimport,
        "edges_shared": len(edges_source & edges_reimport),
        "edges_only_source": len(edges_source - edges_reimport),
        "same_surface_different_diagonals": (
            corners_source == corners_reimport and edges_source != edges_reimport
        ),
    }


def relative_transform_check(before, after):
    """The same difference, scaled by the coefficient it sits on.

    A 4x4 matrix holds rotation coefficients and a translation in metres in
    one array, so a single absolute bound over all sixteen scalars compares
    unlike quantities. This is reported next to the gate, not as the gate: the
    gate is the one alignment 179 approved.
    """
    worst = 0.0
    worst_object = None
    for identity in sorted(set(before) & set(after)):
        for field in ("local_matrix", "root_relative_matrix"):
            for row_a, row_b in zip(before[identity][field], after[identity][field]):
                for a, b in zip(row_a, row_b):
                    relative = abs(a - b) / max(1.0, abs(a), abs(b))
                    if relative > worst:
                        worst, worst_object = relative, f"{identity}.{field}"
    return {
        "worst_relative_difference": worst,
        "worst_at": worst_object,
        "float32_relative_epsilon": 2.0 ** -23,
        "within_float32_epsilon": worst <= 2.0 ** -23,
        "epsilon_multiple": worst / (2.0 ** -23),
        "note": (
            "analysis only; the approved gate is the absolute one above and "
            "its verdict stands as reported"
        ),
    }


def legacy_reanalysis(documents):
    models = {}
    for run in RUNS:
        key = f"run{run}"
        for model in MODELS:
            source = documents[key]["source"][model]["source"]
            imported = documents[key]["import"][model]["reimport"]
            rows = {}
            for name, entry in sorted(source["objects"].items()):
                back = imported["objects"].get(name)
                if back is None:
                    rows[name] = {"status": "missing after reimport", "pass": False}
                    continue
                if entry["triangles"] is None or back["triangles"] is None:
                    rows[name] = {
                        "status": "no triangle payload on one side",
                        "source_has_payload": entry["triangles"] is not None,
                        "reimport_has_payload": back["triangles"] is not None,
                        "source_uv": [entry["uv_layers"], entry["uv_layer"]],
                        "reimport_uv": [back["uv_layers"], back["uv_layer"]],
                        "measurement_valid": False,
                        "pass": False,
                    }
                    continue
                measured = position_uv_only(
                    as_new_mesh(entry["triangles"]), as_new_mesh(back["triangles"])
                )
                measured["status"] = "compared"
                measured["triangulation"] = triangulation_agreement(
                    entry["triangles"], back["triangles"]
                )
                measured["pass"] = bool(
                    measured["geometry"]["pass"]
                    and measured["uv_UVMap"].get("pass")
                    and not measured["assignment"]["aggregate_ambiguous"]
                    and not measured["assignment"]["kind_separated_ambiguous"]
                    and not measured["assignment"]["edge_ambiguous"]
                )
                rows[name] = measured
            inventory_source = {
                name: {
                    "type": item["type"],
                    "parent": item["parent"],
                    "local_matrix": item["matrix_local"],
                    "root_relative_matrix": item["matrix_world"],
                }
                for name, item in source["inventory"].items()
            }
            inventory_import = {
                name: {
                    "type": item["type"],
                    "parent": item["parent"],
                    "local_matrix": item["matrix_local"],
                    "root_relative_matrix": item["matrix_world"],
                }
                for name, item in imported["inventory"].items()
            }
            topology_source = sorted(
                (name, item["parent"], item["type"])
                for name, item in inventory_source.items()
            )
            topology_import = sorted(
                (name, item["parent"], item["type"])
                for name, item in inventory_import.items()
            )
            models[f"{key}/{model}"] = {
                "identity_source": "legacy_name_identity",
                "objects": rows,
                "objects_compared": sum(
                    1 for row in rows.values() if row.get("status") == "compared"
                ),
                "objects_without_payload": sum(
                    1
                    for row in rows.values()
                    if row.get("status") == "no triangle payload on one side"
                ),
                "hierarchy": {
                    "parent_topology_preserved": topology_source == topology_import,
                    "transform": done.transform_measurement(
                        inventory_source, inventory_import
                    ),
                    "transform_relative_analysis": relative_transform_check(
                        inventory_source, inventory_import
                    ),
                },
                "same_surface_different_diagonals": sum(
                    1
                    for row in rows.values()
                    if row.get("triangulation", {}).get(
                        "same_surface_different_diagonals"
                    )
                ),
                "materials_match": all(
                    source["objects"][name]["materials"]
                    == imported["objects"][name]["materials"]
                    for name in source["objects"]
                    if name in imported["objects"]
                ),
            }
    return models


# --------------------------------------------------------------------------
# run1 against run2, as meshes rather than as bytes


def compare_runs(new_snapshots):
    models = {}
    for model in MODELS:
        first = new_snapshots["run1"][model]["objects"]
        second = new_snapshots["run2"][model]["objects"]
        rows = {}
        for name, entry in sorted(first.items()):
            if entry["type"] != "MESH":
                continue
            back = second.get(name)
            if back is None:
                rows[name] = {"status": "absent in run2", "pass": False}
                continue
            assignment, kinds, uv = done.kind_measurements(
                entry, back, bucketed=True, ambiguity_budget=AMBIGUITY_BUDGET
            )
            rows[name] = {
                "status": "compared",
                "triangles": len(entry["triangles"]),
                "assignment": {
                    "matched_triangles": assignment["matched_triangles"],
                    "unmatched_source": assignment["unmatched_source"],
                    "unconsumed_reimport": assignment["unconsumed_reimport"],
                    "aggregate_ambiguous": assignment["aggregate_ambiguous"],
                    "kind_separated_ambiguous": assignment["kind_separated_ambiguous"],
                    "edge_ambiguous": assignment["edge_ambiguous"],
                    "ambiguity_evaluated": assignment["ambiguity_evaluated"],
                    "ambiguity_components_skipped": (
                        assignment["ambiguity_components_skipped"]
                    ),
                },
                "measurements": {
                    name: {
                        key: value
                        for key, value in kind.items()
                        if key != "multiset"
                    }
                    for name, kind in kinds.items()
                },
                "uv_layers": [entry["uv_layers"], back["uv_layers"]],
                "uv": {
                    layer: {
                        "coverage": result.get("triangle_coverage"),
                        "over_bound": result.get("over_bound"),
                        "ambiguous": result.get("ambiguous"),
                        "pass": result.get("pass"),
                    }
                    for layer, result in uv.items()
                },
                "pass": bool(
                    assignment["pass"]
                    and all(kind["pass"] for kind in kinds.values())
                    and all(result.get("pass") for result in uv.values())
                ),
            }
        models[model] = {
            "objects": rows,
            "meshes_compared": len(rows),
            "identical": all(row.get("pass") for row in rows.values()),
            "fbx_bytes_equal": False,
        }
    return models


def do_report(project_root, staging):
    payload = {
        "phase": "M2n2b2",
        "note": (
            "Read-only applicability diagnostic of the alignment 165.2 "
            "staging. No canonical Blend is opened, no FBX is re-exported, "
            "and none of the ten originals is modified."
        ),
        "scope": [
            "verify the ten originals against the recorded size and SHA",
            "map the legacy schema onto the M2n2b1 gates",
            "re-judge what the legacy data can still support",
            "compare the two runs as meshes, never as bytes",
        ],
    }
    started = time.perf_counter()
    try:
        payload["originals"] = verify_originals()
        documents = legacy_documents()
        payload["schema_sufficiency"] = schema_matrix(documents)
        payload["sha_linkage"] = linkage(documents)
        payload["legacy_reanalysis"] = legacy_reanalysis(documents)
        snapshots = json.loads((staging / "new_reimport.json").read_text())
        payload["reimport_snapshot"] = {
            "provenance": "legacy source -> old FBX -> new reimport snapshot",
            "limits": (
                "reimport side only. Without source evaluated polygons and "
                "an export-normalized snapshot, surface preservation and "
                "split-normal preservation are not decided here and are not "
                "marked passed"
            ),
            "polygon_loop_counts": {
                f"run{run}/{model}": sorted(
                    {
                        count
                        for entry in snapshots[f"run{run}"][model]["objects"].values()
                        if entry["type"] == "MESH"
                        for count in entry["polygon_loop_counts"]
                    }
                )
                for run in RUNS
                for model in MODELS
            },
            "custom_properties": {
                model: snapshots["run1"][model]["custom_properties"]
                for model in MODELS
            },
        }
        payload["run_comparison"] = compare_runs(snapshots)
        undecidable = [
            name
            for name, value in payload["schema_sufficiency"]["fields"].items()
            if value["status"] == "missing"
        ]
        payload["undecidable_gates"] = undecidable
        payload["read_only_reanalysis"] = "complete"
        payload["status"] = (
            "insufficient_evidence" if undecidable else "read_only_reanalysis_complete"
        )
        payload["status_reason"] = (
            "the analysis itself ran to completion; the legacy schema cannot "
            "answer " + ", ".join(undecidable) + ", so it is not sufficient "
            "for the M2n2b1 gate set"
        ) if undecidable else "every gate had the evidence it needs"
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / OUTPUT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        originals = payload.get("originals", {})
        print(
            f"[Opus5M2n2b2] originals {originals.get('matching')}/"
            f"{originals.get('checked')}, status {payload.get('status')}"
        )
        for name, model in (payload.get("run_comparison") or {}).items():
            print(
                f"  run1 vs run2 {name}: {model['meshes_compared']} meshes, "
                f"identical={model['identical']}"
            )
        for name, model in (payload.get("legacy_reanalysis") or {}).items():
            print(
                f"  legacy {name}: compared {model['objects_compared']}, "
                f"no payload {model['objects_without_payload']}, "
                f"re-cut {model['same_surface_different_diagonals']}, "
                f"topology {model['hierarchy']['parent_topology_preserved']}, "
                f"transform {model['hierarchy']['transform']['pass']}"
            )


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    if args.mode == "reimport":
        blender_compat.require_v6_pipeline()
        do_reimport(staging)
    else:
        do_report(project_root, staging)


if __name__ == "__main__":
    main()
