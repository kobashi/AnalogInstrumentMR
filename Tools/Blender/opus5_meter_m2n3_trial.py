"""Phase M2n3: one practical handoff trial for the three approved meters.

Alignment 182. The approved export-normalized path from M2n2b1 is connected to
the existing meter handoff, thinly: the evaluated mesh is copied with every
data layer, triangulated explicitly with `FIXED / EAR_CLIP`, exported with
`use_triangles=False`, and the hierarchy, custom properties and an explicit
`opus5_id` travel with it. Nothing new is invented here - the surface gate, the
per-kind measurements and the per-layer UV comparison are the ones already
approved, and the motion, clearance, bounds and inventory gates are the ones
the handoff already had.

The three canonical Blends are opened read-only and never saved. Their hashes
are checked before anything is opened and again after everything is done.

This trial stops at a staging FBX and a report. Nothing is promoted, nothing is
published, and no Unity asset is touched.

Modes, in order:

* `export`   - verify hashes, build the normalized copy, write the FBX
* `reimport` - fresh process: read each FBX back and measure it
* `report`   - run every gate and write the trial report

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n3_trial.py -- \
      --project-root "$PWD" --mode export --staging /tmp/opus5-m2n3
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_fbx_adapter_completion as done
import opus5_meter_fbx_handoff as m2n
import opus5_toggle_fbx_handoff as m2i


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n3_trial.json"
AMBIGUITY_BUDGET = 48


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


def source_hashes(project_root):
    rows = {}
    for key, spec in m2n.SOURCES.items():
        blend = m2n.source_blend(project_root, key)
        report = m2n.source_report(project_root, key)
        rows[key] = {
            "blend": str(blend.relative_to(project_root)),
            "blend_sha256": m1.digest(blend),
            "blend_matches_alignment_140": m1.digest(blend) == spec["sha256"],
            "report": str(report.relative_to(project_root)),
            "report_sha256": m1.digest(report),
        }
    return rows


def strip_polygons(scene):
    """The surface gate has already run; the polygons need not be carried."""
    for entry in scene.values():
        if entry.get("type") == "MESH":
            entry["polygon_loop_counts"] = sorted(
                {len(item["corners"]) for item in entry["polygons"]}
            )
            entry.pop("polygons")
            entry.pop("vertex_order")
    return scene


def uv_layer_report(scene):
    """Names, order and which layer is primary - the transport invariant."""
    rows = {}
    for identity, entry in scene.items():
        if entry.get("type") != "MESH":
            continue
        layers = entry["uv_layers"]
        rows[identity] = {
            "layers": layers,
            "count": len(layers),
            "primary": layers[0] if layers else None,
            "active": entry["active_uv_layer"],
            "render": entry["render_uv_layer"],
        }
    return rows


def rename_onto_originals(root, holder, suffix):
    """Delete the source objects, then give the copies their names back.

    The copy is what is exported, so it has to carry the names every existing
    gate and the Unity prefab refer to. The Blend is never saved, so removing
    the originals from this session's memory changes nothing on disk.
    """
    originals = [root] + list(root.children_recursive)
    copies = [holder] + list(holder.children_recursive)
    names = {}
    for obj in copies:
        names[obj] = obj.name[: -len(suffix)] if obj.name.endswith(suffix) else obj.name
    for obj in originals:
        bpy.data.objects.remove(obj, do_unlink=True)
    for obj, name in names.items():
        obj.name = name
    bpy.context.view_layer.update()
    return holder


def do_export(project_root, staging):
    staging.mkdir(parents=True, exist_ok=True)
    before = source_hashes(project_root)
    for key, row in before.items():
        if not row["blend_matches_alignment_140"]:
            raise SystemExit(f"[Opus5M2n3] {key}: source hash moved, nothing written")

    results = {}
    for key, spec in m2n.SOURCES.items():
        begin = time.perf_counter()
        path = m2n.source_blend(project_root, key)
        m1.open_blend(path)
        root = bpy.data.objects[m2k.MODELS[key]["root"]]
        properties = m2n.stamp(root, key, path.relative_to(project_root), spec["sha256"])
        for obj in [root] + list(root.children_recursive):
            # An explicit identity that survives the format, assigned from the
            # name it already had. It is an id from here on, not a name.
            obj["opus5_id"] = obj.name
        source_checks = m2n.checks(root, key)
        inventory = m2i.describe(root)
        evaluated = done.read_scene(root, evaluated=True)
        authoring = uv_layer_report(evaluated)

        holder = done.export_copy(root)
        # export_copy carries the identity; the handoff stamp lives on the
        # root as well and has to travel with it or the round trip loses every
        # opus5_* property.
        for name, value in properties.items():
            holder[name] = value
        normalized = done.read_scene(holder, evaluated=False)
        surface = {}
        for identity, entry in normalized.items():
            if entry["type"] != "MESH":
                continue
            gate = done.polygon_surface_gate(evaluated[identity], entry)
            surface[identity] = {
                "polygons": gate["polygons"],
                "triangles": gate["triangles"],
                "unassigned_triangles": gate["unassigned_triangles"],
                "surface_area_gap": gate["surface_area_gap"],
                "worst_polygon_area_gap": gate["worst_polygon_area_gap"],
                "bounds_gap_m": gate["bounds_gap_m"],
                "findings": gate["findings"][:4],
                "pass": gate["pass"],
            }

        rename_onto_originals(root, holder, "__export")
        exported_root = bpy.data.objects[m2k.MODELS[key]["root"]]
        copy_checks = m2n.checks(exported_root, key)
        copy_inventory = m2i.describe(exported_root)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in [exported_root] + list(exported_root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = exported_root
        settings = dict(m2n.EXPORT_SETTINGS)
        settings["use_triangles"] = False
        # FACE smoothing writes a per-polygon smoothing group and lets the
        # importer re-derive the creases from it. On the +/-60 degree ticks
        # that lost twelve of the mesh's split normals to averaging, which the
        # split-normal gate measured as 0.89 degrees. EDGE writes the edge
        # sharpness itself, which is the quantity that was being lost.
        settings["mesh_smooth_type"] = "EDGE"
        target = staging / spec["fbx"]
        bpy.ops.export_scene.fbx(filepath=str(target), **settings)
        if not target.is_file():
            raise SystemExit(f"[Opus5M2n3] {key}: export wrote nothing")

        results[key] = {
            "model": key,
            "revision": spec["revision"],
            "source": before[key],
            "fbx": spec["fbx"],
            "fbx_sha256": m1.digest(target),
            "fbx_bytes": target.stat().st_size,
            "export_settings": {
                name: sorted(value) if isinstance(value, set) else value
                for name, value in settings.items()
            },
            "custom_properties": properties,
            "inventory": inventory,
            "inventory_of_export_copy": copy_inventory,
            "checks": source_checks,
            "checks_of_export_copy": copy_checks,
            "polygon_surface": surface,
            "authoring_uv": authoring,
            "normalized": strip_polygons(normalized),
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
            "authoring_environment": blender_compat.provenance(),
        }
        print(
            f"[Opus5M2n3] export {key}: {len(inventory)} objects, tris "
            f"{source_checks['triangles']}, surface gate "
            f"{sum(1 for row in surface.values() if row['pass'])}/{len(surface)}, "
            f"{target.stat().st_size} bytes"
        )

    after = source_hashes(project_root)
    payload = {
        "source_hashes_before": before,
        "source_hashes_after": after,
        "sources_unchanged": before == after,
        "models": results,
    }
    (staging / "export.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def do_reimport(project_root, staging):
    exported = json.loads((staging / "export.json").read_text())
    payload = {}
    for key, spec in m2n.SOURCES.items():
        begin = time.perf_counter()
        bpy.ops.wm.read_homefile(use_empty=True)
        target = staging / spec["fbx"]
        bpy.ops.import_scene.fbx(filepath=str(target))
        roots = [
            obj
            for obj in bpy.data.objects
            if obj.parent is None and str(obj.get("opus5_id", "")).startswith("PF_Visual_")
        ]
        if len(roots) != 1:
            raise AssertionError(f"{key}: {len(roots)} objects claim the root identity")
        root = roots[0]
        scene = done.read_scene(root, evaluated=False)
        payload[key] = {
            "model": key,
            "fbx_sha256": m1.digest(target),
            "reimported_in": "separate Blender process started with --factory-startup",
            "inventory": m2i.describe(root),
            "custom_properties": {
                name: root.get(name)
                for name in exported["models"][key]["custom_properties"]
            },
            "checks": m2n.checks(root, key),
            "authoring_uv": uv_layer_report(scene),
            "reimport": strip_polygons(scene),
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
        }
        print(
            f"[Opus5M2n3] reimport {key}: tris "
            f"{payload[key]['checks']['triangles']}, clearance "
            f"{payload[key]['checks']['worst_tick_clearance']['distance_mm']} mm"
        )
    (staging / "reimport.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------
# Gates


def evidence_gates(exported, imported):
    """The M2n2b1 measurements, on the real models."""
    normalized = exported["normalized"]
    reimport = imported["reimport"]
    rows = {}
    for identity, entry in normalized.items():
        if entry["type"] != "MESH":
            continue
        back = reimport.get(identity)
        if back is None:
            rows[identity] = {"status": "missing after reimport", "pass": False}
            continue
        assignment, kinds, uv = done.kind_measurements(
            entry, back, bucketed=True, ambiguity_budget=AMBIGUITY_BUDGET
        )
        layers_equal = entry["uv_layers"] == back["uv_layers"]
        rows[identity] = {
            "status": "compared",
            "assignment": {
                "expected_triangles": assignment["expected_triangles"],
                "matched_triangles": assignment["matched_triangles"],
                "unmatched_source": assignment["unmatched_source"],
                "unconsumed_reimport": assignment["unconsumed_reimport"],
                "ambiguity_evaluated": assignment["ambiguity_evaluated"],
                "aggregate_ambiguous": assignment["aggregate_ambiguous"],
                "kind_separated_ambiguous": assignment["kind_separated_ambiguous"],
                "edge_ambiguous": assignment["edge_ambiguous"],
                "pass": assignment["pass"],
            },
            "measurements": {
                name: {key: value for key, value in kind.items() if key != "multiset"}
                for name, kind in kinds.items()
            },
            "uv_layers": [entry["uv_layers"], back["uv_layers"]],
            "uv_layer_names_preserved": layers_equal,
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
                and layers_equal
            ),
        }
    return rows


def bounds_full_precision(exported, imported):
    """The same bounds, unrounded.

    The inventory gate compares values already rounded to 1e-6 m against a
    tolerance of exactly 1e-6 m, so a pair that straddles one rounding step
    reads as exceeding it. This measures the same quantity from the snapshots
    at full precision. It is reported beside the legacy gate, not instead of
    it - the legacy verdict stands as it is.
    """
    worst = 0.0
    worst_at = None
    rows = {}
    for identity, entry in exported["normalized"].items():
        if entry["type"] != "MESH":
            continue
        back = imported["reimport"].get(identity)
        if back is None or not entry["bounds"]["min"]:
            continue
        gap = max(
            abs(a - b)
            for side in ("min", "max")
            for a, b in zip(entry["bounds"][side], back["bounds"][side])
        )
        rows[identity] = gap
        if gap > worst:
            worst, worst_at = gap, identity
    return {
        "worst_difference_m": worst,
        "worst_difference_mm": worst * 1000.0,
        "worst_at": worst_at,
        "objects": len(rows),
        "note": "root-relative bounds from the snapshots, no rounding applied",
    }


def primary_uv_first(exported, imported):
    findings = []
    for identity, row in exported["authoring_uv"].items():
        after = imported["authoring_uv"].get(identity, {})
        if row["count"] == 0:
            continue
        if row["primary"] != after.get("primary"):
            findings.append(
                {"object": identity, "reason": "primary layer changed",
                 "before": row["primary"], "after": after.get("primary")}
            )
    return {
        "objects_with_uv": sum(
            1 for row in exported["authoring_uv"].values() if row["count"]
        ),
        "findings": findings,
        "pass": not findings,
    }


def selection_metadata(exported, imported):
    """Recorded, not gated - alignment 174.2 and 182.2.5."""
    rows = {}
    for identity, row in exported["authoring_uv"].items():
        after = imported["authoring_uv"].get(identity, {})
        if row["count"] == 0:
            continue
        if row["active"] != after.get("active") or row["render"] != after.get("render"):
            rows[identity] = {
                "active": [row["active"], after.get("active")],
                "render": [row["render"], after.get("render")],
            }
    return {
        "changed": rows,
        "observed_behavior": "reset_to_first_layer",
        "counted_in_transport_gate": False,
    }


def do_report(project_root, staging):
    payload = {
        "phase": "M2n3",
        "note": (
            "One practical handoff trial (alignment 182). The canonical "
            "Blends are opened read-only and never saved. Nothing is "
            "promoted, published, or copied into Unity."
        ),
        "export_path": (
            "evaluated copy with all data layers, FIXED / EAR_CLIP explicit "
            "triangulation, use_triangles=False, hierarchy and custom "
            "properties preserved, explicit opus5_id"
        ),
    }
    started = time.perf_counter()
    try:
        exported = json.loads((staging / "export.json").read_text())
        imported = json.loads((staging / "reimport.json").read_text())
        payload["source_hashes_before"] = exported["source_hashes_before"]
        payload["source_hashes_after"] = exported["source_hashes_after"]
        payload["sources_unchanged"] = exported["sources_unchanged"]
        models = {}
        for key in m2n.SOURCES:
            before = exported["models"][key]
            after = imported[key]
            gates = m2n.compare(key, before, after)
            # The legacy UV gate hashes the *active* layer only, and the
            # format does not carry which layer is active. It is kept as a
            # record and replaced by the per-layer comparison below, which is
            # the transport invariant alignment 174.2 settled on.
            legacy_uv = gates.pop("uv_preserved")
            surface = before["polygon_surface"]
            evidence = evidence_gates(before, after)
            gates["polygon_surface"] = {
                "objects": len(surface),
                "failing": [name for name, row in surface.items() if not row["pass"]],
                "worst_surface_area_gap": max(
                    (row["surface_area_gap"] for row in surface.values()), default=0.0
                ),
                "pass": all(row["pass"] for row in surface.values()),
            }
            gates["export_copy_measures_as_source"] = {
                "triangles": [
                    before["checks"]["triangles"],
                    before["checks_of_export_copy"]["triangles"],
                ],
                "clearance_mm": [
                    before["checks"]["worst_tick_clearance"]["distance_mm"],
                    before["checks_of_export_copy"]["worst_tick_clearance"][
                        "distance_mm"
                    ],
                ],
                "bounds": [
                    before["checks"]["bounds"],
                    before["checks_of_export_copy"]["bounds"],
                ],
                "pass": (
                    before["checks"]["triangles"]
                    == before["checks_of_export_copy"]["triangles"]
                    and before["checks"]["bounds"]
                    == before["checks_of_export_copy"]["bounds"]
                ),
            }
            gates["position_normal_uv_evidence"] = {
                "objects": len(evidence),
                "failing": [name for name, row in evidence.items() if not row["pass"]],
                "pass": all(row["pass"] for row in evidence.values()),
            }
            gates["primary_uv_is_first_layer"] = primary_uv_first(before, after)
            measured_bounds = bounds_full_precision(before, after)
            failures = [name for name, gate in gates.items() if not gate["pass"]]
            models[key] = {
                "fbx": str((staging / m2n.SOURCES[key]["fbx"]).resolve()),
                "fbx_sha256": before["fbx_sha256"],
                "fbx_bytes": before["fbx_bytes"],
                "gates": gates,
                "failing_gates": failures,
                "per_object_evidence": evidence,
                "polygon_surface_detail": surface,
                "legacy_active_uv_hash": dict(
                    legacy_uv,
                    note=(
                        "recorded only: this hashes the active layer, and the "
                        "format does not carry which layer is active"
                    ),
                ),
                "uv_selection_metadata": selection_metadata(before, after),
                "bounds_full_precision": measured_bounds,
                "pass": not failures,
            }
        payload["models"] = models
        payload["all_passed"] = (
            payload["sources_unchanged"]
            and all(model["pass"] for model in models.values())
        )
        payload["status"] = "trial_complete" if payload["all_passed"] else "trial_failed"
        payload["promoted"] = False
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / OUTPUT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(
            f"[Opus5M2n3] sources unchanged "
            f"{payload.get('sources_unchanged')}, status {payload.get('status')}"
        )
        for key, model in (payload.get("models") or {}).items():
            print(f"  {key}: pass={model['pass']} {model['failing_gates']}")


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    if args.mode != "report":
        blender_compat.require_v6_pipeline()
    if args.mode == "export":
        do_export(project_root, staging)
    elif args.mode == "reimport":
        do_reimport(project_root, staging)
    else:
        do_report(project_root, staging)


if __name__ == "__main__":
    main()
