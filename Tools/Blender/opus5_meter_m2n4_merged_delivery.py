"""Phase M2n4: deliver each meter as three renderers instead of thirty-odd.

Alignment 187.3. Unity accepted the M2n3 geometry and rejected its delivery
structure: 31 / 69 / 83 mesh objects become that many draw submissions, and at
48 placements that is thousands. The shapes are not touched. Only the export
copy is joined, by the role each part plays:

* `static_opaque`  - Body / Metal / Gasket, everything that does not move
* `static_readout` - the emissive readout parts
* `needle`         - the needle and its counterweight, still under
                     `needle_pivot`, so the +/-55 degree contract is unchanged

Three renderers per model, one under the budget of four.

What the merge must not change is checked rather than asserted. The union of
the unmerged triangles, with the one documented exception below, is built as an
explicit expectation and compared against the re-imported merged file with the
approved matcher: every triangle, every corner, every normal, every UV value.

The one exception is stated because it is real: objects that carried no UV
layer at all gain one, with (0, 0) on their corners, because a joined mesh has
a single set of layers. A missing UV channel already reads as (0, 0), so
nothing a shader sees changes - but the count of corners this affects is
measured and reported rather than waved past.

Clearance and contact are measured on the unmerged copy. The contact
classifier recognises the known pairs by object name, and after a join those
names no longer exist; running it on the merged copy would invent "new
contacts" out of renaming. The geometry is proven identical instead, which is
what the clearance contract is a property of.

The canonical Blends are opened read-only, hashed before and after, never
saved. Publishing writes only the candidate tree, under names that do not
collide with M2n3.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n4_merged_delivery.py -- \
      --project-root "$PWD" --mode export --staging /tmp/opus5-m2n4
"""

import argparse
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_fbx_adapter_completion as done
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n3_trial as trial
import opus5_publish as publish
import opus5_toggle_fbx_handoff as m2i


SUMMARY = "ArtSource/Blender/BrushUp/Opus5/meter_m2n4_merged_handoff.json"
RENDERER_BUDGET = 4
AMBIGUITY_BUDGET = 48
# The movable group keeps the name the motion contract already names, so
# `opus5_motion_object` and every gate that reads it stay true.
MOVABLE = "needle"
STATIC_OPAQUE = "static_opaque"
STATIC_READOUT = "static_readout"
READOUT_TOKEN = "Readout"


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


def merged_fbx_name(key):
    return m2n.SOURCES[key]["fbx"].replace(".fbx", "_Merged.fbx")


def candidate_report_path(project_root, key):
    stem = merged_fbx_name(key).replace("SM_", "").replace(".fbx", "")
    return project_root / m2l.REPORT_DIR / f"{stem}_m2n4_candidate.json"


def published_fbx_path(project_root, key):
    return m2l.theme_dir(project_root) / "staging/fbx" / merged_fbx_name(key)


# --------------------------------------------------------------------------
# Roles


def role_of(obj, movable_names):
    if obj.name in movable_names:
        return MOVABLE
    names = [material.name for material in obj.data.materials if material]
    if any(READOUT_TOKEN in name for name in names):
        return STATIC_READOUT
    return STATIC_OPAQUE


def classify(root, pivot_name, movable_names):
    groups = {MOVABLE: [], STATIC_READOUT: [], STATIC_OPAQUE: []}
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        groups[role_of(obj, movable_names)].append(obj)
    return groups


def restore_split_normals(root, obj, expectation):
    """Give the joined mesh back the shading its parts had.

    A join bakes each object's transform into its vertices, and Blender then
    derives new normals from the baked geometry. A flat face survives that
    exactly, but a smooth-shaded vertex normal is an average, and averaging
    does not commute with an anisotropic transform - the plus/minus 60 degree
    ticks carry a (2.0, 1.55, 2.0) scale and came out up to 7.9 degrees away.
    Writing them as custom data before the join did not help, because the join
    recomputes; so they are written afterwards, taken from the parts
    themselves and matched by position alone, so no normal influences which
    corner it is compared with.
    """
    mesh = obj.data
    mesh.calc_loop_triangles()
    snapshot = done.read_mesh(
        obj, root, mesh, root.matrix_world.inverted() @ obj.matrix_world
    )
    # Position alone decides which corner is which. Material is deliberately
    # left out: a join may keep two slots for one material, so the index a
    # triangle carries is about slot order, and no normal is allowed to
    # influence the pairing that is about to set normals.
    def flat(triangles):
        return [dict(item, material=0) for item in triangles]

    solved = done.geometry_assignment(
        flat(expectation["triangles"]), flat(snapshot["triangles"]),
        bucketed=True, kinds=("position",),
    )
    if len(solved["pairs"]) != len(expectation["triangles"]):
        raise AssertionError(
            f"{obj.name}: matched {len(solved['pairs'])} of "
            f"{len(expectation['triangles'])} triangles; normals not restored"
        )
    matrix = root.matrix_world.inverted() @ obj.matrix_world
    back = matrix.to_3x3().inverted_safe().transposed().inverted_safe()
    normals = [None] * len(mesh.loops)
    for source_index, target_index, permutation in (
        (i, j, solved["detail"][(i, j)]["permutation"]) for i, j in solved["pairs"]
    ):
        triangle = mesh.loop_triangles[target_index]
        wanted = expectation["triangles"][source_index]["corners"]
        for corner_index, mapped in enumerate(permutation):
            loop = triangle.loops[mapped]
            normals[loop] = (
                back @ Vector(wanted[corner_index]["split_normal"])
            ).normalized()
    missing = sum(1 for value in normals if value is None)
    if missing:
        raise AssertionError(f"{obj.name}: {missing} loops without a normal")
    mesh.normals_split_custom_set([tuple(value) for value in normals])
    mesh.update()
    return len(normals)


def pin_split_normals(obj):
    """Freeze the shading the part already has, before its scale is baked.

    A join bakes each object's transform into its vertices. A flat face's
    normal survives that exactly, but a smooth-shaded vertex normal is an
    average, and averaging does not commute with an anisotropic transform:
    the plus/minus 60 degree ticks carry a (2.0, 1.55, 2.0) scale and their
    recomputed normals came out up to 7.9 degrees from where they were.
    Writing the current normals as custom data pins them, so the join carries
    them through instead of deriving new ones.
    """
    mesh = obj.data
    normals = [tuple(vector) for vector in done.corner_normals(mesh)]
    if not normals:
        return 0
    mesh.normals_split_custom_set(normals)
    mesh.update()
    return len(normals)


def join_into(target, members):
    """One `join`, with the target's transform as the destination frame."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in members:
        obj.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    bpy.context.view_layer.update()
    return target


def merge_groups(root, groups, pivot):
    """Three objects out of many, with world geometry left where it was."""
    made = {}
    for name in (STATIC_OPAQUE, STATIC_READOUT):
        members = groups[name]
        if not members:
            continue
        mesh = bpy.data.meshes.new(name)
        target = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(target)
        target.parent = root
        target.matrix_parent_inverse = Matrix.Identity(4)
        # Identity under an identity root, so the joined local coordinates are
        # the world coordinates the parts already had.
        target.matrix_local = Matrix.Identity(4)
        target["opus5_id"] = name
        made[name] = join_into(target, members)
    movable = groups[MOVABLE]
    if movable:
        target = next(
            (obj for obj in movable if obj.name.startswith(MOVABLE)), movable[0]
        )
        others = [obj for obj in movable if obj is not target]
        target.parent = pivot
        made[MOVABLE] = join_into(target, others)
        made[MOVABLE].name = MOVABLE
        made[MOVABLE]["opus5_id"] = MOVABLE
    bpy.context.view_layer.update()
    return made


# --------------------------------------------------------------------------
# The expectation the merge has to meet


def expected_union(scene, members, layers, slots, merged_slots):
    """Every triangle of the group, with the joined mesh's UV layer set.

    A corner from an object that had no such layer is (0, 0) here, which is
    the value a joined mesh gives it and the value a missing channel already
    reads as. Stated up front so the comparison can be exact.

    Material indices are per object, and a join renumbers them into one slot
    list, so the index is translated through the material's own name. Comparing
    the raw index would reject two thirds of the triangles for having been
    renumbered - which is a fact about slot order, not about geometry.
    """
    triangles = []
    filled = 0
    for name in members:
        entry = scene[name]
        own = slots.get(name) or []
        for triangle in entry["triangles"]:
            corners = []
            for corner in triangle["corners"]:
                uv = {}
                for layer in layers:
                    if layer in corner["uv"]:
                        uv[layer] = list(corner["uv"][layer])
                    else:
                        uv[layer] = [0.0, 0.0]
                        filled += 1
                corners.append(
                    {
                        "position": list(corner["position"]),
                        "split_normal": list(corner["split_normal"]),
                        "uv": uv,
                    }
                )
            index = triangle["material"]
            material = own[index] if index < len(own) else None
            if material is None or material not in merged_slots:
                raise AssertionError(
                    f"{name}: material slot {index} has no place in the join"
                )
            triangles.append(
                {
                    "corners": corners,
                    "face_normal": list(triangle["face_normal"]),
                    "material": merged_slots.index(material),
                    "area": triangle["area"],
                }
            )
    return {
        "triangles": triangles,
        "uv_layers": list(layers),
        "active_uv_layer": layers[0] if layers else None,
        "render_uv_layer": layers[0] if layers else None,
        "corners_filled_with_zero_uv": filled,
    }


def bounds_of(scene, members):
    points = [
        corner["position"]
        for name in members
        for triangle in scene[name]["triangles"]
        for corner in triangle["corners"]
    ]
    if not points:
        return None
    return {
        "min": [min(point[axis] for point in points) for axis in range(3)],
        "max": [max(point[axis] for point in points) for axis in range(3)],
    }


# --------------------------------------------------------------------------
# Modes


def do_export(project_root, staging):
    staging.mkdir(parents=True, exist_ok=True)
    before = trial.source_hashes(project_root)
    for key, row in before.items():
        if not row["blend_matches_alignment_140"]:
            raise SystemExit(f"[Opus5M2n4] {key}: source hash moved, nothing written")

    results = {}
    for key, spec in m2n.SOURCES.items():
        begin = time.perf_counter()
        path = m2n.source_blend(project_root, key)
        m1.open_blend(path)
        root = bpy.data.objects[m2k.MODELS[key]["root"]]
        properties = m2n.stamp(root, key, path.relative_to(project_root), spec["sha256"])
        for obj in [root] + list(root.children_recursive):
            obj["opus5_id"] = obj.name
        source_checks = m2n.checks(root, key)
        evaluated = done.read_scene(root, evaluated=True)

        holder = done.export_copy(root)
        for name, value in properties.items():
            holder[name] = value
        unmerged = done.read_scene(holder, evaluated=False)
        surface = {
            identity: done.polygon_surface_gate(evaluated[identity], entry)["pass"]
            for identity, entry in unmerged.items()
            if entry["type"] == "MESH"
        }

        trial.rename_onto_originals(root, holder, "__export")
        exported_root = bpy.data.objects[m2k.MODELS[key]["root"]]
        unmerged_checks = m2n.checks(exported_root, key)
        unmerged_inventory = m2i.describe(exported_root)
        pivot = bpy.data.objects[m2n.MOTION["pivot"]]
        movable_names = set(unmerged_checks["movable_meshes"])
        slot_names = {
            obj.name: [material.name for material in obj.data.materials if material]
            for obj in exported_root.children_recursive
            if obj.type == "MESH"
        }
        empty_slots = sorted(name for name, own in slot_names.items() if not own)
        if empty_slots:
            raise SystemExit(
                f"[Opus5M2n4] {key}: no material slot on {empty_slots[:3]}"
            )
        pinned = {
            obj.name: pin_split_normals(obj)
            for obj in exported_root.children_recursive
            if obj.type == "MESH"
        }
        groups = classify(exported_root, pivot.name, movable_names)
        membership = {
            role: sorted(obj.name for obj in members)
            for role, members in groups.items()
        }
        made = merge_groups(exported_root, groups, pivot)

        merged_slots_pre = {
            role: [material.name for material in obj.data.materials if material]
            for role, obj in made.items()
        }
        restored = {}
        for role, obj in made.items():
            layers = [layer.name for layer in obj.data.uv_layers]
            wanted = expected_union(
                unmerged, membership[role], layers, slot_names,
                merged_slots_pre[role],
            )
            restored[role] = restore_split_normals(exported_root, obj, wanted)

        merged_scene = done.read_scene(exported_root, evaluated=False)
        merged_slots = {
            role: [material.name for material in obj.data.materials if material]
            for role, obj in made.items()
        }
        expectation = {}
        for role, members in membership.items():
            if not members:
                continue
            layers = merged_scene[role]["uv_layers"]
            expectation[role] = expected_union(
                unmerged, members, layers, slot_names, merged_slots[role]
            )

        bpy.ops.object.select_all(action="DESELECT")
        for obj in [exported_root] + list(exported_root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = exported_root
        settings = dict(m2n.EXPORT_SETTINGS)
        settings["use_triangles"] = False
        settings["mesh_smooth_type"] = "EDGE"
        target = staging / merged_fbx_name(key)
        bpy.ops.export_scene.fbx(filepath=str(target), **settings)
        if not target.is_file():
            raise SystemExit(f"[Opus5M2n4] {key}: export wrote nothing")

        results[key] = {
            "model": key,
            "revision": spec["revision"],
            "source": before[key],
            "fbx": merged_fbx_name(key),
            "fbx_sha256": m1.digest(target),
            "fbx_bytes": target.stat().st_size,
            "export_settings": {
                name: sorted(value) if isinstance(value, set) else value
                for name, value in settings.items()
            },
            "custom_properties": properties,
            "membership": membership,
            "renderers": sorted(made),
            "material_slots": {
                role: [
                    material.name.split(".")[0]
                    for material in obj.data.materials
                    if material
                ]
                for role, obj in made.items()
            },
            "material_slots_exact": merged_slots,
            "split_normals_pinned": {
                "objects": len(pinned),
                "corners": sum(pinned.values()),
            },
            "split_normals_restored_after_join": restored,
            "unmerged_checks": unmerged_checks,
            "unmerged_inventory": unmerged_inventory,
            "unmerged_surface_gate_all_passed": all(surface.values()),
            "unmerged_bounds_by_role": {
                role: bounds_of(unmerged, members)
                for role, members in membership.items()
                if members
            },
            "expectation": expectation,
            "merged": trial.strip_polygons(merged_scene),
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
            "authoring_environment": blender_compat.provenance(),
        }
        print(
            f"[Opus5M2n4] export {key}: {len(unmerged_inventory)} objects -> "
            f"{len(made)} renderers, tris {unmerged_checks['triangles']}, "
            f"{target.stat().st_size} bytes"
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
        target = staging / merged_fbx_name(key)
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
        renderers = [
            identity for identity, entry in scene.items() if entry["type"] == "MESH"
        ]
        payload[key] = {
            "model": key,
            "fbx_sha256": m1.digest(target),
            "reimported_in": "separate Blender process started with --factory-startup",
            "renderers": sorted(renderers),
            "renderer_count": len(renderers),
            "inventory": m2i.describe(root),
            "custom_properties": {
                name: root.get(name)
                for name in exported["models"][key]["custom_properties"]
            },
            "reimport": trial.strip_polygons(scene),
        }
        print(
            f"[Opus5M2n4] reimport {key}: {len(renderers)} renderers, "
            f"{sum(len(scene[name]['triangles']) for name in renderers)} triangles"
        )
    (staging / "reimport.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


def role_evidence(expected, actual):
    assignment, kinds, uv = done.kind_measurements(
        expected, actual, bucketed=True, ambiguity_budget=AMBIGUITY_BUDGET
    )
    return {
        "expected_triangles": assignment["expected_triangles"],
        "matched_triangles": assignment["matched_triangles"],
        "unmatched_source": assignment["unmatched_source"],
        "unconsumed_reimport": assignment["unconsumed_reimport"],
        "ambiguity_evaluated": assignment["ambiguity_evaluated"],
        "assignment_pass": assignment["pass"],
        "measurements": {
            name: {key: value for key, value in kind.items() if key != "multiset"}
            for name, kind in kinds.items()
        },
        "uv": {
            layer: {
                "coverage": result.get("triangle_coverage"),
                "over_bound": result.get("over_bound"),
                "pass": result.get("pass"),
            }
            for layer, result in uv.items()
        },
        "uv_layers": [expected["uv_layers"], actual["uv_layers"]],
        "pass": bool(
            assignment["pass"]
            and all(kind["pass"] for kind in kinds.values())
            and all(result.get("pass") for result in uv.values())
            and expected["uv_layers"] == actual["uv_layers"]
        ),
    }


def do_report(project_root, staging):
    payload = {
        "phase": "M2n4",
        "note": (
            "Merged delivery (alignment 187.3). Shapes untouched; the export "
            "copy is joined by role so each model ships three renderers. "
            "Canonical Blends are read-only and never saved."
        ),
        "renderer_budget": RENDERER_BUDGET,
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
                role: role_evidence(expectation, after["reimport"][role])
                for role, expectation in before["expectation"].items()
                if role in after["reimport"]
            }
            merged_triangles = sum(
                len(after["reimport"][role]["triangles"]) for role in after["renderers"]
            )
            merged_bounds = {
                "min": [
                    min(
                        after["reimport"][role]["bounds"]["min"][axis]
                        for role in after["renderers"]
                    )
                    for axis in range(3)
                ],
                "max": [
                    max(
                        after["reimport"][role]["bounds"]["max"][axis]
                        for role in after["renderers"]
                    )
                    for axis in range(3)
                ],
            }
            source_bounds = before["unmerged_checks"]["bounds"]
            bounds_gap = max(
                abs(a - b)
                for side in ("min", "max")
                for a, b in zip(merged_bounds[side], source_bounds[side])
            )
            movable_present = MOVABLE in after["renderers"]
            gates = {
                "renderer_budget": {
                    "renderers": after["renderer_count"],
                    "budget": RENDERER_BUDGET,
                    "names": after["renderers"],
                    "pass": after["renderer_count"] <= RENDERER_BUDGET,
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
                    "movable_renderer": MOVABLE,
                    "movable_present_under_pivot": (
                        movable_present
                        and after["reimport"][MOVABLE]["parent"]
                        == m2n.MOTION["pivot"]
                    ),
                    "range_deg": m2n.MOTION["range_deg"],
                    "unmerged_movable_meshes": before["unmerged_checks"][
                        "movable_meshes"
                    ],
                    "pass": (
                        movable_present
                        and after["reimport"][MOVABLE]["parent"]
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
                    "slots": before["material_slots"],
                    "pass": all(
                        (READOUT_TOKEN in name) == (role == STATIC_READOUT)
                        for role, names in before["material_slots"].items()
                        if role != MOVABLE
                        for name in names
                    ),
                },
                "unmerged_surface_gate": {
                    "pass": before["unmerged_surface_gate_all_passed"],
                },
            }
            failures = [name for name, gate in gates.items() if not gate["pass"]]
            models[key] = {
                "staged_fbx": str((staging / merged_fbx_name(key)).resolve()),
                "fbx": merged_fbx_name(key),
                "fbx_sha256": before["fbx_sha256"],
                "fbx_bytes": before["fbx_bytes"],
                "renderers": after["renderers"],
                "renderer_count": after["renderer_count"],
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
            print(f"  {key}: renderers {after['renderer_count']}, pass={not failures} {failures}")
        payload["models"] = models
        payload["all_passed"] = payload["sources_unchanged"] and all(
            model["pass"] for model in models.values()
        )

        if payload["all_passed"]:
            for key, model in models.items():
                source = staging / merged_fbx_name(key)
                target = published_fbx_path(project_root, key)
                report_path = candidate_report_path(project_root, key)
                report = {
                    "phase": "M2n4",
                    "model": key,
                    "revision": m2n.SOURCES[key]["revision"],
                    "delivery": "merged: three renderers by role",
                    "status": "candidate_handoff_approved",
                    "production_approval": False,
                    "supersedes_delivery_of": "M2n3 (same geometry, 31/69/83 renderers)",
                    "source": payload["source_hashes_before"][key],
                    "settings": exported["models"][key]["export_settings"],
                    "membership": exported["models"][key]["membership"],
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
            f"[Opus5M2n4] status {payload.get('status')}, sources unchanged "
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
