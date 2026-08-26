"""Toggle: the same delivery normalisation the meters went through.

Alignment 234. The D-5 Toggle candidates ship thirteen mesh objects, which is
the structure Unity rejected the meters for. The shapes are not touched; only
the export copy is joined, by the role each part plays:

* `static_opaque`  - housing, mounts, retaining ring, joint socket, limit stops
* `static_readout` - the two detents
* `switch`         - the switch and its hemisphere joint, still under
                     `switch_pivot`, so the motion contract is unchanged

Three renderers. The movable group is entirely opaque here - unlike the meter's
needle, which had to keep an emissive half - so after slot normalisation each
renderer carries one material and the model ships three submeshes.

Everything the merge must not change is checked rather than asserted: the union
of the unmerged triangles is built as an explicit expectation and compared with
the re-imported file using the approved matcher.

The candidate Blends are opened read-only and never saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_toggle_delivery_normalization.py -- \
      --project-root "$PWD" --mode export --staging /tmp/opus5-toggle
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
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact_migration_m1 as m1
import opus5_fbx_adapter_completion as done
import opus5_meter_m2n4_merged_delivery as m2n4
import opus5_publish as publish
import opus5_toggle_fbx_handoff as toggle


SUMMARY = "ArtSource/Blender/BrushUp/Opus5/toggle_delivery_normalization.json"
REVISION = "N1"
PIVOT = "switch_pivot"
MOVABLE = "switch"
STATIC_OPAQUE = "static_opaque"
STATIC_READOUT = "static_readout"
READOUT_TOKEN = "Readout"
RENDERER_BUDGET = 4
SUBMESH_BUDGET = 4
AMBIGUITY_BUDGET = 48

SOURCES = {
    "KineticSafety": {
        "blend": "ArtSource/Blender/BrushUp/Opus5/KineticSafety/BL_Toggle_KineticSafety_V6_Opus5_D5_Retopo.blend",
        "sha256": "77ed6178f776a15a",
        "root": "PF_Visual_Toggle_KineticSafety_V6",
        "fbx": "SM_Toggle_KineticSafety_V6_Opus5_D5_Merged_Slots.fbx",
        "triangles": 2168,
    },
    "ForgeBrass": {
        "blend": "ArtSource/Blender/BrushUp/Opus5/ForgeBrass/BL_Toggle_ForgeBrass_V6_Opus5_D5_D10_Retopo.blend",
        "sha256": "dad488540fd16db3",
        "root": "PF_Visual_Toggle_ForgeBrass_V6",
        "fbx": "SM_Toggle_ForgeBrass_V6_Opus5_D5_D10_Merged_Slots.fbx",
        "triangles": 2354,
    },
    "OrbitalAnalog": {
        "blend": "ArtSource/Blender/BrushUp/Opus5/OrbitalAnalog/BL_Toggle_OrbitalAnalog_V6_Opus5_D5_Retopo.blend",
        "sha256": "5859b498b15d6758",
        "root": "PF_Visual_Toggle_OrbitalAnalog_V6",
        "fbx": "SM_Toggle_OrbitalAnalog_V6_Opus5_D5_Merged_Slots.fbx",
        "triangles": 2032,
    },
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


def published_fbx(project_root, theme):
    return (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / theme
        / "staging/fbx"
        / SOURCES[theme]["fbx"]
    )


def candidate_report(project_root, theme):
    stem = SOURCES[theme]["fbx"].replace("SM_", "").replace(".fbx", "")
    return (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / theme
        / "reports"
        / f"{stem}_candidate.json"
    )


def role_of(obj, movable_names):
    if obj.name in movable_names:
        return MOVABLE
    names = [material.name for material in obj.data.materials if material]
    if any(READOUT_TOKEN in name for name in names):
        return STATIC_READOUT
    return STATIC_OPAQUE


def classify(root, pivot):
    """Anything under the pivot moves; the rest splits by material role."""
    movable = {
        obj.name
        for obj in pilot.meshes_under(root)
        if pivot.name in [parent.name for parent in ancestry(obj)]
    }
    groups = {MOVABLE: [], STATIC_READOUT: [], STATIC_OPAQUE: []}
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        groups[role_of(obj, movable)].append(obj)
    return groups, sorted(movable)


def ancestry(obj):
    chain = []
    current = obj.parent
    while current is not None:
        chain.append(current)
        current = current.parent
    return chain


def merge_groups(root, groups, pivot):
    """Three objects: two static, one still hanging off the pivot."""
    made = {}
    for name in (STATIC_OPAQUE, STATIC_READOUT):
        members = groups[name]
        if not members:
            continue
        target = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        bpy.context.collection.objects.link(target)
        target.parent = root
        target.matrix_parent_inverse = Matrix.Identity(4)
        target.matrix_local = Matrix.Identity(4)
        target["opus5_id"] = name
        made[name] = m2n4.join_into(target, members)
    movable = groups[MOVABLE]
    if movable:
        target = next(
            (obj for obj in movable if obj.name == MOVABLE), movable[0]
        )
        target.parent = pivot
        made[MOVABLE] = m2n4.join_into(
            target, [obj for obj in movable if obj is not target]
        )
        made[MOVABLE].name = MOVABLE
        made[MOVABLE]["opus5_id"] = MOVABLE
    bpy.context.view_layer.update()
    return made


def role_slots(theme, role):
    """One slot per role. The switch is entirely opaque on this model."""
    base = f"MAT_{theme}_V5_"
    if role == STATIC_READOUT:
        return [f"{base}Readout"]
    return [f"{base}Body"]


def find_material(name):
    for material in bpy.data.materials:
        if material.name.split(".")[0] == name:
            return material
    raise SystemExit(f"[Opus5ToggleN1] no material named {name}")


def normalize_slots(obj, theme, role):
    mesh = obj.data
    before = [material.name for material in mesh.materials if material]
    wanted = role_slots(theme, role)
    moved = [0 for _ in mesh.polygons]
    mesh.materials.clear()
    for name in wanted:
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
                name.split(".")[0]
                for name in before
                if name.split(".")[0] not in {a.split(".")[0] for a in after}
            }
        ),
    }


def expectation_for(unmerged, members, layers, theme, role, slot_names):
    """Translate each object's own slots onto the single slot of its role.

    `expected_union` looks a triangle's material index up in the object's slot
    list, so the list has to be as long as the object's original one - `housing`
    carries Body and Metal, and a one-entry table cannot answer for index 1.
    """
    wanted = role_slots(theme, role)
    slots = {
        name: [wanted[0]] * max(len(slot_names.get(name, [])), 1)
        for name in members
    }
    return m2n4.expected_union(unmerged, members, layers, slots, wanted)


def do_export(project_root, staging):
    staging.mkdir(parents=True, exist_ok=True)
    payload = {"models": {}}
    for theme, spec in SOURCES.items():
        begin = time.perf_counter()
        source = project_root / spec["blend"]
        digest = m1.digest(source)
        if not digest.startswith(spec["sha256"]):
            raise SystemExit(f"[Opus5ToggleN1] {theme}: source hash moved")
        m1.open_blend(source)
        root = bpy.data.objects[spec["root"]]
        pivot = bpy.data.objects[PIVOT]
        for obj in [root] + list(root.children_recursive):
            obj["opus5_id"] = obj.name
        before_objects = sum(1 for _ in pilot.meshes_under(root))
        evaluated = done.read_scene(root, evaluated=True)

        holder = done.export_copy(root)
        unmerged = done.read_scene(holder, evaluated=False)
        surface = all(
            done.polygon_surface_gate(evaluated[identity], entry)["pass"]
            for identity, entry in unmerged.items()
            if entry["type"] == "MESH"
        )
        m2n4.trial.rename_onto_originals(root, holder, "__export")
        exported_root = bpy.data.objects[spec["root"]]
        pivot = bpy.data.objects[PIVOT]
        slot_names = {
            obj.name: [m.name for m in obj.data.materials if m]
            for obj in exported_root.children_recursive
            if obj.type == "MESH"
        }
        groups, movable_names = classify(exported_root, pivot)
        membership = {
            role: sorted(obj.name for obj in members)
            for role, members in groups.items()
        }
        made = merge_groups(exported_root, groups, pivot)
        slots = {role: normalize_slots(obj, theme, role) for role, obj in made.items()}
        restored = {}
        expectation = {}
        for role, obj in made.items():
            layers = [layer.name for layer in obj.data.uv_layers]
            wanted = expectation_for(
                unmerged, membership[role], layers, theme, role, slot_names
            )
            restored[role] = m2n4.restore_split_normals(exported_root, obj, wanted)
            expectation[role] = wanted

        merged = done.read_scene(exported_root, evaluated=False)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in [exported_root] + list(exported_root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = exported_root
        settings = dict(toggle.EXPORT_SETTINGS)
        settings["use_triangles"] = False
        settings["mesh_smooth_type"] = "EDGE"
        target = staging / spec["fbx"]
        bpy.ops.export_scene.fbx(filepath=str(target), **settings)

        payload["models"][theme] = {
            "theme": theme,
            "source": spec["blend"],
            "source_sha256": digest,
            "objects_before": before_objects,
            "membership": membership,
            "movable_under_pivot": movable_names,
            "renderers": sorted(made),
            "slots": slots,
            "split_normals_restored": restored,
            "unmerged_surface_gate_all_passed": surface,
            "expectation": expectation,
            "merged": m2n4.trial.strip_polygons(merged),
            "fbx": spec["fbx"],
            "fbx_sha256": m1.digest(target),
            "fbx_bytes": target.stat().st_size,
            "export_settings": {
                name: sorted(value) if isinstance(value, set) else value
                for name, value in settings.items()
            },
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
        }
        print(
            f"[Opus5ToggleN1] export {theme}: {before_objects} -> "
            f"{len(made)} renderers, "
            f"{sum(len(row['after']) for row in slots.values())} submeshes, "
            f"{target.stat().st_size} bytes"
        )
    (staging / "export.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def do_reimport(project_root, staging):
    exported = json.loads((staging / "export.json").read_text())
    payload = {}
    for theme, spec in SOURCES.items():
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(staging / spec["fbx"]))
        roots = [
            obj
            for obj in bpy.data.objects
            if obj.parent is None and str(obj.get("opus5_id", "")) == spec["root"]
        ]
        if len(roots) != 1:
            raise AssertionError(f"{theme}: {len(roots)} roots")
        root = roots[0]
        scene = done.read_scene(root, evaluated=False)
        renderers = sorted(
            identity for identity, entry in scene.items() if entry["type"] == "MESH"
        )
        slots = {}
        for identity in renderers:
            obj = next(o for o in bpy.data.objects if o.get("opus5_id") == identity)
            slots[identity] = [m.name.split(".")[0] for m in obj.data.materials if m]
        payload[theme] = {
            "fbx_sha256": m1.digest(staging / spec["fbx"]),
            "renderers": renderers,
            "renderer_count": len(renderers),
            "material_slots": slots,
            "submesh_total": sum(len(value) for value in slots.values()),
            "reimport": m2n4.trial.strip_polygons(scene),
        }
        print(
            f"[Opus5ToggleN1] reimport {theme}: {len(renderers)} renderers, "
            f"{payload[theme]['submesh_total']} submeshes"
        )
    (staging / "reimport.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def do_report(project_root, staging):
    payload = {
        "phase": "Toggle-N1",
        "note": (
            "Delivery normalisation only (alignment 234). Shapes untouched; "
            "the export copy is joined by role. Candidate Blends are "
            "read-only and nothing active is written."
        ),
        "renderer_budget": RENDERER_BUDGET,
        "submesh_budget": SUBMESH_BUDGET,
        "production_approval": False,
    }
    started = time.perf_counter()
    try:
        exported = json.loads((staging / "export.json").read_text())["models"]
        imported = json.loads((staging / "reimport.json").read_text())
        models = {}
        for theme, spec in SOURCES.items():
            before = exported[theme]
            after = imported[theme]
            evidence = {}
            for role, wanted in before["expectation"].items():
                if role not in after["reimport"]:
                    evidence[role] = {"status": "missing", "pass": False}
                    continue
                evidence[role] = m2n4.role_evidence(wanted, after["reimport"][role])
            triangles = sum(
                len(after["reimport"][role]["triangles"]) for role in after["renderers"]
            )
            movable_ok = (
                MOVABLE in after["renderers"]
                and after["reimport"][MOVABLE]["parent"] == PIVOT
            )
            gates = {
                "renderer_budget": {
                    "before": before["objects_before"],
                    "measured": after["renderer_count"],
                    "budget": RENDERER_BUDGET,
                    "names": after["renderers"],
                    "pass": after["renderer_count"] <= RENDERER_BUDGET,
                },
                "submesh_budget": {
                    "measured": after["submesh_total"],
                    "budget": SUBMESH_BUDGET,
                    "slots": after["material_slots"],
                    "pass": after["submesh_total"] <= SUBMESH_BUDGET,
                },
                "triangles": {
                    "measured": triangles,
                    "expected": spec["triangles"],
                    "pass": triangles == spec["triangles"],
                },
                "geometry_uv_normals_unchanged": {
                    "roles": {role: row["pass"] for role, row in evidence.items()},
                    "detail": evidence,
                    "pass": all(row["pass"] for row in evidence.values()),
                },
                "motion_contract": {
                    "pivot": PIVOT,
                    "movable_renderer": MOVABLE,
                    "movable_before": before["movable_under_pivot"],
                    "pass": movable_ok,
                },
                "material_roles": {
                    "slots": after["material_slots"],
                    "collapsed": {
                        role: row["collapsed"] for role, row in before["slots"].items()
                    },
                    "pass": all(
                        (READOUT_TOKEN in name) == (role == STATIC_READOUT)
                        for role, names in after["material_slots"].items()
                        for name in names
                    ),
                },
                "unmerged_surface_gate": {
                    "pass": before["unmerged_surface_gate_all_passed"]
                },
            }
            failures = [name for name, gate in gates.items() if not gate["pass"]]
            models[theme] = {
                "fbx": spec["fbx"],
                "staged_sha256": before["fbx_sha256"],
                "fbx_bytes": before["fbx_bytes"],
                "source": spec["blend"],
                "source_sha256": before["source_sha256"],
                "renderers": after["renderers"],
                "renderer_count": after["renderer_count"],
                "submesh_total": after["submesh_total"],
                "triangles": triangles,
                "membership_counts": {
                    role: len(members) for role, members in before["membership"].items()
                },
                "gates": gates,
                "failing_gates": failures,
                "pass": not failures,
            }
            print(
                f"  {theme}: {before['objects_before']} -> "
                f"{after['renderer_count']} renderers, "
                f"{after['submesh_total']} submeshes, pass={not failures} {failures}"
            )
        payload["models"] = models
        payload["all_passed"] = all(model["pass"] for model in models.values())
        if payload["all_passed"]:
            for theme, model in models.items():
                source = staging / SOURCES[theme]["fbx"]
                target = published_fbx(project_root, theme)
                report_path = candidate_report(project_root, theme)
                report = {
                    "phase": "Toggle-N1",
                    "theme": theme,
                    "delivery": "three renderers, one slot per role",
                    "status": "candidate_handoff_approved",
                    "production_approval": False,
                    "supersedes_delivery_of": "D-5 candidate (13 renderers, 15 submeshes)",
                    "source": model["source"],
                    "source_sha256": model["source_sha256"],
                    "fbx": model["fbx"],
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
        (project_root / SUMMARY).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(f"[Opus5ToggleN1] status {payload.get('status')}")


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
