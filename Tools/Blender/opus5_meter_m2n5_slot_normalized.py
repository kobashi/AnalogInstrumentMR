"""Phase M2n5: one slot per role, so a renderer is one draw submission.

Alignment 189. M2n4 got each meter down to three renderers, but a renderer
submits once per submesh and the joined meshes still carried the source's
duplicate material datablocks - `Body` and `Body.001` are one material by every
name that matters, and they were costing a submission each. Round shipped 7,
Medium and Large 9.

Here the slots are normalised by role on the export copy:

* `static_opaque`  - one slot; Body, Metal and Gasket all map to the same
                     candidate V6 opaque material in Unity
* `static_readout` - one slot
* `needle`         - two, and deliberately so: its Readout faces are emissive
                     and its Metal faces are not, and collapsing those would
                     change how the needle looks

Four submissions per model at most. Nothing else moves: same geometry, same UVs,
same restored normals, same triangle count, bounds, pivot, clearance and custom
properties as M2n4, from the same read-only canonical Blends.

The report carries the fields the existing Unity validator reads - `fbx`,
`staged_sha256`, `gates.triangles.measured`, the renderer and submesh budgets -
alongside the evidence M2n4 already produced, so nothing has to be extended on
the Unity side to consume it.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n5_slot_normalized.py -- \
      --project-root "$PWD" --mode export --staging /tmp/opus5-m2n5
"""

import argparse
import json
import shutil
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
import opus5_meter_m2n3_trial as trial
import opus5_meter_m2n4_merged_delivery as m2n4
import opus5_publish as publish
import opus5_toggle_fbx_handoff as m2i


SUMMARY = "ArtSource/Blender/BrushUp/Opus5/meter_m2n5_slot_normalized_handoff.json"
SUBMESH_BUDGET = 4
# One entry per slot the role is allowed to keep, named by the material's base
# name. The needle keeps two because its two halves are not the same Unity
# role; everything static collapses to one.
ROLE_SLOTS = {
    m2n4.STATIC_OPAQUE: ["MAT_KineticSafety_V5_Body"],
    m2n4.STATIC_READOUT: ["MAT_KineticSafety_V5_Readout"],
    m2n4.MOVABLE: ["MAT_KineticSafety_V5_Readout", "MAT_KineticSafety_V5_Metal"],
}


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


def delivered_fbx_name(key):
    return m2n.SOURCES[key]["fbx"].replace(".fbx", "_Merged_Slots.fbx")


def candidate_report_path(project_root, key):
    stem = delivered_fbx_name(key).replace("SM_", "").replace(".fbx", "")
    return project_root / m2l.REPORT_DIR / f"{stem}_m2n5_candidate.json"


def published_fbx_path(project_root, key):
    return m2l.theme_dir(project_root) / "staging/fbx" / delivered_fbx_name(key)


def base_name(name):
    return name.split(".")[0]


def target_slot(role, material_name):
    """Which of the role's slots this material belongs in."""
    wanted = ROLE_SLOTS[role]
    if role == m2n4.MOVABLE:
        readout = m2n4.READOUT_TOKEN in base_name(material_name)
        return wanted[0] if readout else wanted[1]
    return wanted[0]


def find_material(name):
    for material in bpy.data.materials:
        if base_name(material.name) == name:
            return material
    raise SystemExit(f"[Opus5M2n5] no material named {name} in this file")


def normalize_slots(obj, role):
    """Collapse the role's slots, keeping which face is which Unity role."""
    mesh = obj.data
    before = [material.name for material in mesh.materials if material]
    mapping = {}
    for index, material in enumerate(mesh.materials):
        if material is None:
            continue
        mapping[index] = ROLE_SLOTS[role].index(target_slot(role, material.name))
    # The indices are plain integers, so they can be rewritten before the slot
    # list shrinks under them.
    moved = [mapping[polygon.material_index] for polygon in mesh.polygons]
    mesh.materials.clear()
    for name in ROLE_SLOTS[role]:
        mesh.materials.append(find_material(name))
    for polygon, index in zip(mesh.polygons, moved):
        polygon.material_index = index
    mesh.update()
    after = [material.name for material in mesh.materials if material]
    return {
        "before": before,
        "after": after,
        "collapsed": sorted(
            {
                base_name(name)
                for name in before
                if base_name(name) not in {base_name(item) for item in after}
            }
        ),
    }


def translated_slots(slot_names, members, role):
    """The same per-object slot lists, renamed to the slot they now land in."""
    return {
        name: [target_slot(role, material) for material in slot_names[name]]
        for name in members
    }


def do_export(project_root, staging):
    staging.mkdir(parents=True, exist_ok=True)
    before = trial.source_hashes(project_root)
    for key, row in before.items():
        if not row["blend_matches_alignment_140"]:
            raise SystemExit(f"[Opus5M2n5] {key}: source hash moved, nothing written")

    results = {}
    for key, spec in m2n.SOURCES.items():
        begin = time.perf_counter()
        path = m2n.source_blend(project_root, key)
        m1.open_blend(path)
        root = bpy.data.objects[m2k.MODELS[key]["root"]]
        properties = m2n.stamp(root, key, path.relative_to(project_root), spec["sha256"])
        for obj in [root] + list(root.children_recursive):
            obj["opus5_id"] = obj.name
        evaluated = done.read_scene(root, evaluated=True)

        holder = done.export_copy(root)
        for name, value in properties.items():
            holder[name] = value
        unmerged = done.read_scene(holder, evaluated=False)
        surface = all(
            done.polygon_surface_gate(evaluated[identity], entry)["pass"]
            for identity, entry in unmerged.items()
            if entry["type"] == "MESH"
        )

        trial.rename_onto_originals(root, holder, "__export")
        exported_root = bpy.data.objects[m2k.MODELS[key]["root"]]
        unmerged_checks = m2n.checks(exported_root, key)
        unmerged_inventory = m2i.describe(exported_root)
        pivot = bpy.data.objects[m2n.MOTION["pivot"]]
        slot_names = {
            obj.name: [material.name for material in obj.data.materials if material]
            for obj in exported_root.children_recursive
            if obj.type == "MESH"
        }
        groups = m2n4.classify(
            exported_root, pivot.name, set(unmerged_checks["movable_meshes"])
        )
        membership = {
            role: sorted(obj.name for obj in members)
            for role, members in groups.items()
        }
        made = m2n4.merge_groups(exported_root, groups, pivot)

        slots = {role: normalize_slots(obj, role) for role, obj in made.items()}
        restored = {}
        expectation = {}
        for role, obj in made.items():
            layers = [layer.name for layer in obj.data.uv_layers]
            wanted = m2n4.expected_union(
                unmerged,
                membership[role],
                layers,
                translated_slots(slot_names, membership[role], role),
                slots[role]["after"],
            )
            restored[role] = m2n4.restore_split_normals(exported_root, obj, wanted)
            expectation[role] = wanted

        merged_scene = done.read_scene(exported_root, evaluated=False)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in [exported_root] + list(exported_root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = exported_root
        settings = dict(m2n.EXPORT_SETTINGS)
        settings["use_triangles"] = False
        settings["mesh_smooth_type"] = "EDGE"
        target = staging / delivered_fbx_name(key)
        bpy.ops.export_scene.fbx(filepath=str(target), **settings)
        if not target.is_file():
            raise SystemExit(f"[Opus5M2n5] {key}: export wrote nothing")

        results[key] = {
            "model": key,
            "revision": spec["revision"],
            "source": before[key],
            "fbx": delivered_fbx_name(key),
            "fbx_sha256": m1.digest(target),
            "fbx_bytes": target.stat().st_size,
            "export_settings": {
                name: sorted(value) if isinstance(value, set) else value
                for name, value in settings.items()
            },
            "custom_properties": properties,
            "membership": membership,
            "renderers": sorted(made),
            "slots": slots,
            "submeshes": {role: len(row["after"]) for role, row in slots.items()},
            "split_normals_restored_after_join": restored,
            "unmerged_checks": unmerged_checks,
            "unmerged_inventory": unmerged_inventory,
            "unmerged_surface_gate_all_passed": surface,
            "expectation": expectation,
            "merged": trial.strip_polygons(merged_scene),
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
            "authoring_environment": blender_compat.provenance(),
        }
        print(
            f"[Opus5M2n5] export {key}: {len(made)} renderers, "
            f"{sum(len(row['after']) for row in slots.values())} submeshes, "
            f"tris {unmerged_checks['triangles']}, {target.stat().st_size} bytes"
        )

    payload = {
        "source_hashes_before": before,
        "source_hashes_after": trial.source_hashes(project_root),
        "models": results,
    }
    payload["sources_unchanged"] = (
        payload["source_hashes_before"] == payload["source_hashes_after"]
    )
    (staging / "export.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def do_reimport(project_root, staging):
    exported = json.loads((staging / "export.json").read_text())
    payload = {}
    for key in m2n.SOURCES:
        bpy.ops.wm.read_homefile(use_empty=True)
        target = staging / delivered_fbx_name(key)
        bpy.ops.import_scene.fbx(filepath=str(target))
        roots = [
            obj
            for obj in bpy.data.objects
            if obj.parent is None
            and str(obj.get("opus5_id", "")).startswith("PF_Visual_")
        ]
        if len(roots) != 1:
            raise AssertionError(f"{key}: {len(roots)} roots")
        root = roots[0]
        scene = done.read_scene(root, evaluated=False)
        renderers = sorted(
            identity for identity, entry in scene.items() if entry["type"] == "MESH"
        )
        submeshes = {
            identity: len(
                {triangle["material"] for triangle in scene[identity]["triangles"]}
            )
            for identity in renderers
        }
        slots = {
            identity: [
                material.name.split(".")[0]
                for material in bpy.data.objects[
                    next(
                        obj.name
                        for obj in bpy.data.objects
                        if obj.get("opus5_id") == identity
                    )
                ].data.materials
                if material
            ]
            for identity in renderers
        }
        payload[key] = {
            "model": key,
            "fbx_sha256": m1.digest(target),
            "reimported_in": "separate Blender process started with --factory-startup",
            "renderers": renderers,
            "renderer_count": len(renderers),
            "material_slots": slots,
            "submesh_slots": {name: len(value) for name, value in slots.items()},
            "distinct_material_indices_used": submeshes,
            "inventory": m2i.describe(root),
            "custom_properties": {
                name: root.get(name)
                for name in exported["models"][key]["custom_properties"]
            },
            "reimport": trial.strip_polygons(scene),
        }
        print(
            f"[Opus5M2n5] reimport {key}: {len(renderers)} renderers, "
            f"{sum(len(value) for value in slots.values())} submeshes"
        )
    (staging / "reimport.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


def do_report(project_root, staging):
    payload = {
        "phase": "M2n5",
        "note": (
            "Slot-normalised delivery (alignment 189). Three renderers and at "
            "most four submeshes per model, from the same geometry, UVs and "
            "restored normals as M2n4. Canonical Blends are read-only."
        ),
        "renderer_budget": m2n4.RENDERER_BUDGET,
        "submesh_budget": SUBMESH_BUDGET,
        "production_approval": False,
    }
    started = time.perf_counter()
    try:
        exported = json.loads((staging / "export.json").read_text())
        imported = json.loads((staging / "reimport.json").read_text())
        payload["source_hashes_before"] = exported["source_hashes_before"]
        payload["source_hashes_after"] = trial.source_hashes(project_root)
        payload["sources_unchanged"] = (
            payload["source_hashes_before"] == payload["source_hashes_after"]
        )
        models = {}
        for key in m2n.SOURCES:
            before = exported["models"][key]
            after = imported[key]
            evidence = {
                role: m2n4.role_evidence(expectation, after["reimport"][role])
                for role, expectation in before["expectation"].items()
                if role in after["reimport"]
            }
            merged_triangles = sum(
                len(after["reimport"][role]["triangles"]) for role in after["renderers"]
            )
            merged_bounds = {
                side: [
                    (min if side == "min" else max)(
                        after["reimport"][role]["bounds"][side][axis]
                        for role in after["renderers"]
                    )
                    for axis in range(3)
                ]
                for side in ("min", "max")
            }
            source_bounds = before["unmerged_checks"]["bounds"]
            bounds_gap = max(
                abs(a - b)
                for side in ("min", "max")
                for a, b in zip(merged_bounds[side], source_bounds[side])
            )
            submesh_total = sum(after["submesh_slots"].values())
            movable_present = m2n4.MOVABLE in after["renderers"]
            gates = {
                "renderer_budget": {
                    "renderers": after["renderer_count"],
                    "budget": m2n4.RENDERER_BUDGET,
                    "names": after["renderers"],
                    "pass": after["renderer_count"] <= m2n4.RENDERER_BUDGET,
                },
                "submesh_budget": {
                    "measured": submesh_total,
                    "budget": SUBMESH_BUDGET,
                    "per_renderer": after["submesh_slots"],
                    "slots": after["material_slots"],
                    "pass": submesh_total <= SUBMESH_BUDGET,
                },
                "triangles": {
                    "measured": merged_triangles,
                    "expected": m2n.SOURCES[key]["triangles"],
                    "pass": merged_triangles == m2n.SOURCES[key]["triangles"],
                },
                "triangles_unchanged": {
                    "unmerged": before["unmerged_checks"]["triangles"],
                    "expected": m2n.SOURCES[key]["triangles"],
                    "merged": merged_triangles,
                    "pass": (
                        merged_triangles
                        == before["unmerged_checks"]["triangles"]
                        == m2n.SOURCES[key]["triangles"]
                    ),
                },
                "geometry_uv_normals_unchanged": {
                    "roles": {role: row["pass"] for role, row in evidence.items()},
                    "detail": evidence,
                    "pass": all(row["pass"] for row in evidence.values()),
                },
                "bounds_unchanged": {
                    "unmerged": source_bounds,
                    "merged": merged_bounds,
                    "worst_difference_m": bounds_gap,
                    "pass": bounds_gap <= m2i.BOUNDS_TOLERANCE_M,
                },
                "motion_contract": {
                    "pivot": m2n.MOTION["pivot"],
                    "movable_renderer": m2n4.MOVABLE,
                    "range_deg": m2n.MOTION["range_deg"],
                    "unmerged_movable_meshes": before["unmerged_checks"][
                        "movable_meshes"
                    ],
                    "pass": (
                        movable_present
                        and after["reimport"][m2n4.MOVABLE]["parent"]
                        == m2n.MOTION["pivot"]
                    ),
                },
                "custom_properties_restored": {
                    "differences": {
                        name: [value, after["custom_properties"].get(name)]
                        for name, value in before["custom_properties"].items()
                        if after["custom_properties"].get(name) != value
                    },
                    "pass": all(
                        after["custom_properties"].get(name) == value
                        for name, value in before["custom_properties"].items()
                    ),
                },
                "material_roles": {
                    "slots": after["material_slots"],
                    "collapsed": {
                        role: row["collapsed"] for role, row in before["slots"].items()
                    },
                    "needle_keeps_both_roles": sorted(
                        after["material_slots"].get(m2n4.MOVABLE, [])
                    )
                    == sorted(
                        base_name(name) for name in ROLE_SLOTS[m2n4.MOVABLE]
                    ),
                    "pass": (
                        all(
                            (m2n4.READOUT_TOKEN in name)
                            == (role == m2n4.STATIC_READOUT)
                            for role, names in after["material_slots"].items()
                            if role != m2n4.MOVABLE
                            for name in names
                        )
                        and sorted(after["material_slots"].get(m2n4.MOVABLE, []))
                        == sorted(
                            base_name(name) for name in ROLE_SLOTS[m2n4.MOVABLE]
                        )
                    ),
                },
                "unmerged_surface_gate": {
                    "pass": before["unmerged_surface_gate_all_passed"],
                },
            }
            failures = [name for name, gate in gates.items() if not gate["pass"]]
            models[key] = {
                "fbx": delivered_fbx_name(key),
                "staged_sha256": before["fbx_sha256"],
                "fbx_bytes": before["fbx_bytes"],
                "renderers": after["renderers"],
                "renderer_count": after["renderer_count"],
                "submeshes": after["submesh_slots"],
                "submesh_total": submesh_total,
                "membership_counts": {
                    role: len(members) for role, members in before["membership"].items()
                },
                "triangles": merged_triangles,
                "bounds": merged_bounds,
                "motion_contract": m2n.MOTION,
                "tick_clearance_measured_on_unmerged": before["unmerged_checks"][
                    "worst_tick_clearance"
                ],
                "new_contacts_on_unmerged": before["unmerged_checks"]["new_contacts"],
                "uv_corners_filled_with_zero": {
                    role: value["corners_filled_with_zero_uv"]
                    for role, value in before["expectation"].items()
                },
                "gates": gates,
                "failing_gates": failures,
                "pass": not failures,
            }
            print(
                f"  {key}: {after['renderer_count']} renderers, "
                f"{submesh_total} submeshes, pass={not failures} {failures}"
            )
        payload["models"] = models
        payload["all_passed"] = payload["sources_unchanged"] and all(
            model["pass"] for model in models.values()
        )

        if payload["all_passed"]:
            for key, model in models.items():
                source = staging / delivered_fbx_name(key)
                target = published_fbx_path(project_root, key)
                report_path = candidate_report_path(project_root, key)
                report = {
                    "phase": "M2n5",
                    "model": key,
                    "revision": m2n.SOURCES[key]["revision"],
                    "delivery": "three renderers, one slot per role",
                    "status": "candidate_handoff_approved",
                    "production_approval": False,
                    "supersedes_delivery_of": "M2n4 (same geometry, 7/9/9 submeshes)",
                    "source": payload["source_hashes_before"][key],
                    "settings": exported["models"][key]["export_settings"],
                    "membership": exported["models"][key]["membership"],
                    # Alignment 189.2: the fields the existing Unity validator
                    # reads, beside the evidence rather than instead of it.
                    "fbx": model["fbx"],
                    "fbx_candidate_path": str(
                        target.relative_to(project_root)
                    ),
                    "staged_sha256": model["staged_sha256"],
                    "gates": model["gates"],
                    "authoring_environment": blender_compat.provenance(),
                }

                def save(destination, origin=source):
                    shutil.copyfile(origin, destination)

                def reopen(destination, origin=source):
                    if m1.digest(destination) != m1.digest(origin):
                        raise publish.PublishFailed(f"{destination.name}: mismatch")

                record = publish.publish(
                    target, report_path, report, problems=[],
                    save_blend=save, reopen_blend=reopen,
                )
                model["published"] = {
                    "fbx": str(target.relative_to(project_root)),
                    "fbx_sha256": m1.digest(target),
                    "fbx_bytes": target.stat().st_size,
                    "report": str(report_path.relative_to(project_root)),
                    "report_sha256": m1.digest(report_path),
                    "publish": record,
                }
                print(f"  published {target.name} ({target.stat().st_size} bytes)")
            payload["status"] = "candidate_handoff_published"
        else:
            payload["status"] = "gates_failed_nothing_published"
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / SUMMARY
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(
            f"[Opus5M2n5] status {payload.get('status')}, sources unchanged "
            f"{payload.get('sources_unchanged')}"
        )


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
