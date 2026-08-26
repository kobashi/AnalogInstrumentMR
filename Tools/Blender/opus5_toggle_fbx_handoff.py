"""Phase M2i: FBX handoff for the three approved Toggle candidates.

Alignment 112.2. Exports the candidates, then proves the FBX by reading it back
in a clean Blender and re-running the checks that mattered on the Blend.

FBX bytes are not reproducible, so nothing here compares them. What is compared
is the model that comes back: inventory, hierarchy, transforms, materials,
triangles, bounds, custom properties, and - the part that actually matters -
the contact behaviour over the full 0 to 56 degree travel.

The round trip runs in a **separate** Blender process started with
`--factory-startup`, not merely in a reset scene inside this one, so nothing
this script did to its own session can flatter the result.

Three modes, run in order by `scripts/run-blender.sh`:

* `export`  - verify source hashes, write FBX and export reports into staging
* `verify`  - fresh process: re-import each FBX and write round-trip reports
* `promote` - check every gate against the two staged reports, then publish

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_toggle_fbx_handoff.py -- \
      --project-root "$PWD" --mode export --staging /tmp/opus5-fbx
"""

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_baseline_contact_classification as m2f
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_candidate_build as m2e
import opus5_d5_profile_preserving_slot as m2b
import opus5_d10_candidate_build as m2h
import opus5_d10_limit_stop_design as m2g
import opus5_publish as publish


HANDOFF = "ArtSource/Blender/BrushUp/Opus5/toggle_fbx_handoff.json"

# Alignment 112.2 pins every source by hash.
SOURCES = {
    "OrbitalAnalog": {
        "blend": "BL_Toggle_OrbitalAnalog_V6_Opus5_D5_Retopo.blend",
        "revision": "D5",
        "defects": ["D-5"],
        "sha256": "5859b498b15d67583518690859c512042fc3ad1950422ba032b3bebd8e85b251",
        "fbx": "SM_Toggle_OrbitalAnalog_V6_Opus5_D5.fbx",
        "slot_half_angle_deg": 17.0,
    },
    "ForgeBrass": {
        "blend": "BL_Toggle_ForgeBrass_V6_Opus5_D5_D10_Retopo.blend",
        "revision": "D5_D10",
        "defects": ["D-5", "D-10"],
        "sha256": "dad488540fd16db33c8fc6dff189ef6844e630e959eb8aea14ef734ab21ccb8a",
        "fbx": "SM_Toggle_ForgeBrass_V6_Opus5_D5_D10.fbx",
        "slot_half_angle_deg": 19.5,
    },
    "KineticSafety": {
        "blend": "BL_Toggle_KineticSafety_V6_Opus5_D5_Retopo.blend",
        "revision": "D5",
        "defects": ["D-5"],
        "sha256": "77ed6178f776a15a1c0a82928f12a510387e92d9cf80e62e91636dfcafeb6839",
        "fbx": "SM_Toggle_KineticSafety_V6_Opus5_D5.fbx",
        "slot_half_angle_deg": 22.0,
    },
}

MOTION = {
    "pivot": "switch_pivot",
    "movable": "switch",
    "axis": "X",
    "range_deg": [0.0, 56.0],
    "rest_deg": 0.0,
}
POSES = [56.0 * index / 26 for index in range(27)]

EXPORT_SETTINGS = {
    "use_selection": True,
    "object_types": {"EMPTY", "MESH"},
    "apply_unit_scale": True,
    "apply_scale_options": "FBX_SCALE_UNITS",
    "use_space_transform": True,
    "bake_space_transform": False,
    "axis_forward": "-Z",
    "axis_up": "Y",
    "use_mesh_modifiers": True,
    "mesh_smooth_type": "FACE",
    "use_triangles": True,
    "add_leaf_bones": False,
    "bake_anim": False,
    "path_mode": "STRIP",
    "embed_textures": False,
    "use_custom_props": True,
}

BOUNDS_TOLERANCE_M = 1.0e-6
# FBX stores vertex positions as single-precision floats. The largest
# coordinate in these models is about 0.09 m, so the format's own resolution is
# roughly 1e-5 mm; a depth that moves by less than 1e-4 mm across the round trip
# has not moved, it has been re-rounded. The smallest quantity any gate cares
# about is 0.05 mm, five hundred times larger.
ALLOWANCE_TOLERANCE_MM = 1.0e-4
ALLOWED_TOKENS = m2e.ALLOWED_PAIRS | {
    ("switch", "joint_socket"),
    ("hemisphere_joint", "joint_socket"),
    ("hemisphere_joint", "housing"),
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("export", "verify", "promote"))
    parser.add_argument("--staging", required=True)
    parser.add_argument("--trial", action="store_true")
    return parser.parse_args(args)


def source_path(project_root, theme):
    return (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / theme
        / SOURCES[theme]["blend"]
    )


def fbx_path(project_root, theme):
    return (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / theme
        / "staging/fbx"
        / SOURCES[theme]["fbx"]
    )


def report_paths(project_root, theme):
    base = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "reports"
    stem = SOURCES[theme]["fbx"].replace("SM_", "").replace(".fbx", "")
    return {
        "export": base / f"{stem}_fbx_export.json",
        "round_trip": base / f"{stem}_fbx_round_trip.json",
    }


def name_of(obj):
    """FBX round trips can decorate names; compare on the stem."""
    return obj.name.split(".")[0]


def describe(root):
    """Everything gate 2 asks to be carried across the format boundary."""
    entries = {}
    for obj in [root] + list(root.children_recursive):
        entry = {
            "type": obj.type,
            "parent": name_of(obj.parent) if obj.parent else None,
            "matrix_local": [[round(v, 6) for v in row] for row in obj.matrix_local],
            "matrix_world": [[round(v, 6) for v in row] for row in obj.matrix_world],
        }
        if obj.type == "MESH":
            obj.data.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            entry.update(
                {
                    "vertices": len(obj.data.vertices),
                    "loop_triangles": len(obj.data.loop_triangles),
                    "materials": [
                        m.name.split(".")[0] if m else None for m in obj.data.materials
                    ],
                    "bounds": {
                        "min": [round(min(p[i] for p in points), 6) for i in range(3)],
                        "max": [round(max(p[i] for p in points), 6) for i in range(3)],
                    },
                }
            )
        entries[name_of(obj)] = entry
    return entries


def stamp(root, theme, source, sha):
    """Alignment 112.3-3. What the FBX has to be able to say for itself."""
    properties = {
        "opus5_source_path": str(source),
        "opus5_source_sha256": sha,
        "opus5_theme": theme,
        "opus5_revision": SOURCES[theme]["revision"],
        "opus5_defects": ",".join(SOURCES[theme]["defects"]),
        "opus5_motion_pivot": MOTION["pivot"],
        "opus5_motion_object": MOTION["movable"],
        "opus5_motion_axis": MOTION["axis"],
        "opus5_motion_range_deg": "0.0,56.0",
        "opus5_motion_rest_deg": "0.0",
        "opus5_slot_half_angle_deg": str(SOURCES[theme]["slot_half_angle_deg"]),
        "opus5_unit_scale": "1 unit = 1 metre",
        "opus5_axis": "Blender Z-up, exported -Z forward / Y up",
        "opus5_mount_plane": "max Y == 0",
    }
    for key, value in properties.items():
        root[key] = value
    return properties


def open_source(project_root, theme):
    path = source_path(project_root, theme)
    m1.open_blend(path)
    root = next(
        obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_Toggle_")
    )
    return path, root


def scene_handles(root):
    return {
        "root": root,
        "pivot": bpy.data.objects[MOTION["pivot"]],
        "switch": bpy.data.objects[MOTION["movable"]],
        "ring": m2f.find(root, "retaining_ring"),
        "joint": m2f.find(root, "hemisphere"),
        "stop": m2f.find(root, "limit_stop_1"),
    }


def motion_checks(scene, theme):
    """The checks that have to survive the format, not just the geometry."""
    ring, switch, pivot = scene["ring"], scene["switch"], scene["pivot"]
    centre = pivot.matrix_world.translation.copy()
    islands = m2e.islands_of(switch.data)
    facts = [m2e.island_facts(switch, island, centre) for island in islands]
    axle = [
        index
        for index, entry in enumerate(facts)
        if entry["longest_axis"] == "X" and entry["distance_from_pivot_mm"] < 30.0
    ]
    heights = m2b.section_heights(ring, centre)
    profile = m2b.lip_profile(
        ring, scene["joint"], centre, SOURCES[theme]["slot_half_angle_deg"], heights
    )
    switch_ring = m2g.sweep_pair(pivot, switch, ring, POSES)
    clear = all(
        entry["surface_crossing"] == 0 and entry["penetrating_vertices"] == 0
        for entry in switch_ring.values()
    )
    separation = min(
        (
            entry["minimum_separation_mm"]
            for entry in switch_ring.values()
            if entry["minimum_separation_mm"] is not None
        ),
        default=None,
    )
    result = {
        "switch_islands": len(islands),
        "axle_islands": axle,
        "ring_total_gap_deg": profile["coverage"]["total_gap_deg"],
        "expected_total_gap_deg": SOURCES[theme]["slot_half_angle_deg"] * 2.0,
        "switch_ring_clear": clear,
        "switch_ring_minimum_separation_mm": separation,
        "poses": len(POSES),
    }
    if theme == "ForgeBrass":
        stop_sweep = m2g.sweep_pair(pivot, switch, scene["stop"], POSES)
        rest = stop_sweep[0.0]
        result["seat"] = m2h.measure_seat(scene["stop"])
        result["stop_rest_separation_mm"] = rest["minimum_separation_mm"]
        result["stop_reentry_poses"] = sorted(
            pose
            for pose, entry in stop_sweep.items()
            if pose > 0.0
            and (entry["surface_crossing"] > 0 or entry["penetrating_vertices"] > 0)
        )
    return result


def allowance_regression(scene):
    root, pivot = scene["root"], scene["pivot"]
    movable, static = m2e.movable_and_static(root, pivot)
    out = {}
    for mover in movable:
        for other in static:
            allowed = any(
                mover_token in name_of(mover) and static_token in name_of(other)
                for mover_token, static_token in ALLOWED_TOKENS
            )
            entry = m2e.sweep_pair(pivot, mover, other, POSES)
            out[f"{name_of(mover)} x {name_of(other)}"] = {
                "surface_crossing": entry["surface_crossing"],
                "penetrating_vertices": entry["penetrating_vertices"],
                "deepest_intrusion_mm": entry["deepest_intrusion_mm"],
                "clear": entry["clear"],
                "named_allowance": allowed,
            }
    return out


def do_export(project_root, staging):
    staging.mkdir(parents=True, exist_ok=True)
    results = {}
    for theme, spec in SOURCES.items():
        path = source_path(project_root, theme)
        actual = m1.digest(path)
        if actual != spec["sha256"]:
            raise SystemExit(
                f"[Opus5FbxHandoff] {theme}: source hash mismatch, nothing "
                f"written ({actual} != {spec['sha256']})"
            )
    for theme, spec in SOURCES.items():
        begin = time.perf_counter()
        path, root = open_source(project_root, theme)
        scene = scene_handles(root)
        properties = stamp(root, theme, path.relative_to(project_root), spec["sha256"])
        inventory = describe(root)
        motion = motion_checks(scene, theme)
        allowances = allowance_regression(scene)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in [root] + list(root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = root
        target = staging / spec["fbx"]
        bpy.ops.export_scene.fbx(filepath=str(target), **EXPORT_SETTINGS)
        if not target.is_file():
            raise SystemExit(f"[Opus5FbxHandoff] {theme}: export wrote nothing")

        results[theme] = {
            "theme": theme,
            "revision": spec["revision"],
            "defects": spec["defects"],
            "source": str(path.relative_to(project_root)),
            "source_sha256": spec["sha256"],
            "fbx": spec["fbx"],
            "fbx_sha256": m1.digest(target),
            "fbx_bytes": target.stat().st_size,
            "export_settings": {
                key: sorted(value) if isinstance(value, set) else value
                for key, value in EXPORT_SETTINGS.items()
            },
            "custom_properties": properties,
            "inventory": inventory,
            "motion": motion,
            "allowance_regression": allowances,
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
            "authoring_environment": blender_compat.provenance(),
        }
        print(
            f"[Opus5FbxHandoff] export {theme}: {len(inventory)} objects, "
            f"gap {motion['ring_total_gap_deg']} deg, clear "
            f"{motion['switch_ring_clear']}, {target.stat().st_size} bytes"
        )
    (staging / "export.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )


def do_verify(project_root, staging):
    exported = json.loads((staging / "export.json").read_text())
    results = {}
    for theme, spec in SOURCES.items():
        begin = time.perf_counter()
        bpy.ops.wm.read_homefile(use_empty=True)
        target = staging / spec["fbx"]
        bpy.ops.import_scene.fbx(filepath=str(target))
        root = next(
            obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_Toggle_")
        )
        scene = scene_handles(root)
        inventory = describe(root)
        properties = {
            key: root.get(key) for key in exported[theme]["custom_properties"]
        }
        motion = motion_checks(scene, theme)
        allowances = allowance_regression(scene)
        results[theme] = {
            "theme": theme,
            "fbx": spec["fbx"],
            "fbx_sha256": m1.digest(target),
            "reimported_in": "separate Blender process started with --factory-startup",
            "inventory": inventory,
            "custom_properties": properties,
            "motion": motion,
            "allowance_regression": allowances,
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
            "authoring_environment": blender_compat.provenance(),
        }
        print(
            f"[Opus5FbxHandoff] verify {theme}: {len(inventory)} objects, "
            f"gap {motion['ring_total_gap_deg']} deg, clear "
            f"{motion['switch_ring_clear']}"
        )
    (staging / "round_trip.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )


def compare(exported, imported):
    """Gate 8: the model that comes back is the model that went out."""
    before, after = exported["inventory"], imported["inventory"]
    missing = sorted(set(before) - set(after))
    extra = sorted(set(after) - set(before))
    changed = {}
    for name in sorted(set(before) & set(after)):
        first, second = before[name], after[name]
        difference = {}
        for key in ("type", "parent", "vertices", "loop_triangles", "materials"):
            if first.get(key) != second.get(key):
                difference[key] = [first.get(key), second.get(key)]
        for side in ("min", "max"):
            a = (first.get("bounds") or {}).get(side)
            b = (second.get("bounds") or {}).get(side)
            if a and b and any(
                abs(a[i] - b[i]) > BOUNDS_TOLERANCE_M for i in range(3)
            ):
                difference[f"bounds_{side}"] = [a, b]
        world_a = first.get("matrix_world")
        world_b = second.get("matrix_world")
        if world_a and world_b and any(
            abs(world_a[r][c] - world_b[r][c]) > 1e-5
            for r in range(4)
            for c in range(4)
        ):
            difference["matrix_world"] = [world_a, world_b]
        if difference:
            changed[name] = difference

    properties = {
        key: [value, imported["custom_properties"].get(key)]
        for key, value in exported["custom_properties"].items()
        if imported["custom_properties"].get(key) != value
    }
    motion_before, motion_after = exported["motion"], imported["motion"]
    allowance_changes = {
        label: [entry["deepest_intrusion_mm"], imported["allowance_regression"][label]["deepest_intrusion_mm"]]
        for label, entry in exported["allowance_regression"].items()
        if label in imported["allowance_regression"]
        and imported["allowance_regression"][label]["deepest_intrusion_mm"]
        > entry["deepest_intrusion_mm"] + ALLOWANCE_TOLERANCE_MM
    }
    new_contacts = [
        label
        for label, entry in imported["allowance_regression"].items()
        if not entry["clear"]
        and not entry["named_allowance"]
        and (
            label not in exported["allowance_regression"]
            or exported["allowance_regression"][label]["clear"]
        )
    ]

    gates = {
        "inventory_identical": {
            "missing": missing, "extra": extra, "changed": changed,
            "pass": not missing and not extra and not changed,
        },
        "custom_properties_restored": {
            "differences": properties, "pass": not properties,
        },
        "no_axle_component": {
            "islands": motion_after["switch_islands"],
            "axle_islands": motion_after["axle_islands"],
            "pass": not motion_after["axle_islands"],
        },
        "ring_opening_preserved": {
            "expected_deg": motion_after["expected_total_gap_deg"],
            "measured_deg": motion_after["ring_total_gap_deg"],
            "pass": abs(
                motion_after["ring_total_gap_deg"]
                - motion_after["expected_total_gap_deg"]
            )
            <= 1.0,
        },
        "switch_ring_clear_over_travel": {
            "clear": motion_after["switch_ring_clear"],
            "minimum_separation_mm": motion_after["switch_ring_minimum_separation_mm"],
            "blend_minimum_separation_mm": motion_before[
                "switch_ring_minimum_separation_mm"
            ],
            "poses": motion_after["poses"],
            "pass": motion_after["switch_ring_clear"],
        },
        "regression": {
            "new_contacts": new_contacts,
            "worsened_allowances": allowance_changes,
            "tolerance_mm": ALLOWANCE_TOLERANCE_MM,
            "tolerance_reason": (
                "single-precision FBX vertex storage; observed re-rounding is "
                "about 3e-6 mm"
            ),
            "largest_observed_change_mm": max(
                (
                    round(
                        imported["allowance_regression"][label][
                            "deepest_intrusion_mm"
                        ]
                        - entry["deepest_intrusion_mm"],
                        9,
                    )
                    for label, entry in exported["allowance_regression"].items()
                    if label in imported["allowance_regression"]
                ),
                default=0.0,
            ),
            "pass": not new_contacts and not allowance_changes,
        },
    }
    if "seat" in motion_after:
        seat = motion_after["seat"]
        gates["seat_preserved"] = {
            "seat_half_width_mm": seat["measured_seat_half_width_mm"],
            "seat_floor_y_mm": seat["measured_floor_y_mm"],
            "rest_separation_mm": motion_after["stop_rest_separation_mm"],
            "reentry_poses": motion_after["stop_reentry_poses"],
            "pass": (
                seat["measured_seat_half_width_mm"] is not None
                and abs(seat["measured_seat_half_width_mm"] - m2h.SEAT_HALF_WIDTH_MM)
                <= 0.001
                and abs(seat["measured_floor_y_mm"] - m2h.SEAT_FLOOR_Y_MM) <= 0.001
                and motion_after["stop_rest_separation_mm"] is not None
                and 0.0 <= motion_after["stop_rest_separation_mm"] <= 0.10
                and not motion_after["stop_reentry_poses"]
            ),
        }
    return gates


def do_promote(project_root, staging, trial):
    exported = json.loads((staging / "export.json").read_text())
    imported = json.loads((staging / "round_trip.json").read_text())

    themes = {}
    problems = []
    for theme in SOURCES:
        gates = compare(exported[theme], imported[theme])
        failures = [name for name, entry in gates.items() if not entry["pass"]]
        problems.extend(f"{theme}: {name}" for name in failures)
        themes[theme] = {
            "export": exported[theme],
            "round_trip": imported[theme],
            "gates": gates,
            "pass": not failures,
        }
        print(f"[Opus5FbxHandoff] {theme}: {{'gates': {not failures}}} {failures}")

    # Every canonical target has to move together under --trial. Redirecting
    # only the commit marker let a trial run publish the FBX and the reports
    # into the project while leaving nothing to certify them.
    if trial:
        bay = Path(staging) / "promote"
        bay.mkdir(parents=True, exist_ok=True)
        targets = {theme: bay / SOURCES[theme]["fbx"] for theme in SOURCES}
        reports = {
            theme: {
                kind: bay / path.name
                for kind, path in report_paths(project_root, theme).items()
            }
            for theme in SOURCES
        }
        handoff_path = bay / "toggle_fbx_handoff.json"
    else:
        targets = {theme: fbx_path(project_root, theme) for theme in SOURCES}
        reports = {theme: report_paths(project_root, theme) for theme in SOURCES}
        handoff_path = project_root / HANDOFF
    existing = any(path.exists() for path in targets.values()) or any(
        path.exists() for paths in reports.values() for path in paths.values()
    )
    decision = publish.publish_guard(existing, handoff_path.exists(), problems, trial)
    record = dict(decision)

    if decision["may_write_blend"]:
        for theme in SOURCES:
            targets[theme].parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staging / SOURCES[theme]["fbx"], targets[theme])
            promoted = m1.digest(targets[theme])
            if promoted != exported[theme]["fbx_sha256"]:
                raise publish.PublishFailed(
                    f"{theme}: promoted FBX does not match what was verified"
                )
            themes[theme]["promoted_fbx_sha256"] = promoted
            for kind, path in reports[theme].items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(
                        themes[theme]["export" if kind == "export" else "round_trip"],
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
                    "phase": "M2i",
                    "note": (
                        "FBX handoff for the three approved Toggle candidates "
                        "(alignment 112.2). FBX bytes are not compared; the "
                        "re-imported model is."
                    ),
                    "publish": record,
                    "round_trip_process": (
                        "separate Blender started with --factory-startup"
                    ),
                    "motion_contract": MOTION,
                    "export_settings": {
                        key: sorted(value) if isinstance(value, set) else value
                        for key, value in EXPORT_SETTINGS.items()
                    },
                    "themes": {
                        theme: {
                            "source": entry["export"]["source"],
                            "source_sha256": entry["export"]["source_sha256"],
                            "revision": entry["export"]["revision"],
                            "defects": entry["export"]["defects"],
                            "fbx": str(
                                fbx_path(project_root, theme).relative_to(project_root)
                            ),
                            "fbx_sha256": entry["export"]["fbx_sha256"],
                            "fbx_bytes": entry["export"]["fbx_bytes"],
                            "reports": {
                                kind: str(path.relative_to(project_root))
                                for kind, path in report_paths(
                                    project_root, theme
                                ).items()
                            },
                            "gates": {
                                name: gate["pass"]
                                for name, gate in entry["gates"].items()
                            },
                            "pass": entry["pass"],
                        }
                        for theme, entry in themes.items()
                    },
                    "problems": problems,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(f"[Opus5FbxHandoff] {record['mode']}: {record['reason']}")


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    if args.mode == "promote":
        do_promote(project_root, staging, args.trial)
        return
    blender_compat.require_v6_pipeline()
    if args.mode == "export":
        do_export(project_root, staging)
    else:
        do_verify(project_root, staging)


if __name__ == "__main__":
    main()
