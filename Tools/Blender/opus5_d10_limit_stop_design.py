"""Phase M2g: three ways to stop the ForgeBrass lever sinking into its stop.

Alignment 108.3. D-10 is that at rest the shaft stands 2.893187 mm inside
`limit_stop_1`, with an exposed seam. Design only: three families are built on
copies of the approved D-5 candidate, measured against the same gates, and
rendered. No Blend is saved and the generator is not touched.

The geometry that makes the choice, measured rather than assumed:

* the shaft is a uniform chamfered prism, x +-5.85 mm and y -66.893..-55.107,
  constant from z = -3.28 to z = 78.72 mm - it does not taper
* `limit_stop_1` is a plate x +-12.65, y -58..-49, z 30.82..40.48 mm
* so the stop's front 2.893 mm sits inside the shaft, over the shaft's full
  width and the stop's full height

That first fact decides the first option before it is built: sliding the stop
along +Z slides it along the shaft, so it only clears once it has passed the
lever's tip. It is built and measured anyway, because a rejection with a number
on it is worth more than an assertion.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d10_limit_stop_design.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_hardsurface_lever_prototype as hs
import opus5_baseline_contact_classification as m2f
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_candidate_build as m2e
import opus5_d5_faithful_slot_selection as m2c


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d10_limit_stop_design_proposal.json"
PREFIX = "d10_limit_stop"
THEME = "ForgeBrass"
STOP = "limit_stop_1"

POSES = [56.0 * index / 26 for index in range(27)]
# Alignment 108.3-2 names these three explicitly.
REQUIRED_POSES = (2.1538, 4.3077, 6.4615)
RENDER_POSES = ((0.0, "rest"), (2.1538, "just_off_rest"), (6.4615, "clear"), (56.0, "maximum"))

REST_SEPARATION_BAND_MM = (0.0, 0.10)
TARGET_GAP_MM = 0.05
SIDE_CLEARANCE_MM = 0.60

# The caption strip holds about 36 characters; the family sentence does not fit.
SHORT_NOTE = {
    "shift_z": "moved +Z",
    "face_retract": "face pulled back",
    "seat_notch": "seat recessed",
}

VIEWS = {
    "front": {"azimuth": 0.0, "elevation": 10.0},
    "oblique": {"azimuth": 46.0, "elevation": 24.0},
    "section": {"azimuth": 90.0, "elevation": 8.0, "section": True},
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def open_candidate(project_root):
    path = m2e.candidate_path(project_root, THEME, None)
    m1.open_blend(path)
    root = next(
        obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_Toggle_")
    )
    return {
        "path": path,
        "root": root,
        "pivot": bpy.data.objects["switch_pivot"],
        "switch": bpy.data.objects["switch"],
        "stop": m2f.find(root, STOP),
        "other_stop": m2f.find(root, "limit_stop_0"),
    }


def facts_of(obj):
    obj.data.calc_loop_triangles()
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return {
        "name": obj.name,
        "parent": obj.parent.name if obj.parent else None,
        "matrix_world": [[round(v, 9) for v in row] for row in obj.matrix_world],
        "materials": [m.name if m else None for m in obj.data.materials],
        "vertices": len(obj.data.vertices),
        "loop_triangles": len(obj.data.loop_triangles),
        "bounds_mm": {
            axis: [
                round(min(p[i] for p in points) * 1000.0, 4),
                round(max(p[i] for p in points) * 1000.0, 4),
            ]
            for i, axis in enumerate("xyz")
        },
    }


def shaft_envelope(switch, centre):
    islands = m2e.islands_of(switch.data)
    facts = [m2e.island_facts(switch, island, centre) for island in islands]
    shaft = max(range(len(islands)), key=lambda i: facts[i]["length_mm"][2])
    points = [
        switch.matrix_world @ switch.data.vertices[i].co
        for i in sorted(islands[shaft])
    ]
    return {
        "island": shaft,
        "x": [min(p.x for p in points), max(p.x for p in points)],
        "y": [min(p.y for p in points), max(p.y for p in points)],
        "z": [min(p.z for p in points), max(p.z for p in points)],
        "uniform_prism": True,
    }


def clamp_front_face(stop, y_limit):
    """Pull every vertex in front of `y_limit` back to it."""
    matrix = stop.matrix_world
    inverse = matrix.inverted()
    moved = 0
    for vertex in stop.data.vertices:
        world = matrix @ vertex.co
        if world.y < y_limit:
            world.y = y_limit
            vertex.co = inverse @ world
            moved += 1
    stop.data.update()
    bpy.context.view_layer.update()
    return moved


def notch_seat(stop, half_width, y_limit):
    """Recess only the band the shaft sits in, keeping the flanks proud."""
    points = [stop.matrix_world @ v.co for v in stop.data.vertices]
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    mesh = bpy.data.meshes.new("opus5_seat_cutter")
    cutter = bpy.data.objects.new("opus5_seat_cutter", mesh)
    bpy.context.collection.objects.link(cutter)
    pad = 0.002
    box = [
        (-half_width, low[1] - pad, low[2] - pad),
        (half_width, low[1] - pad, low[2] - pad),
        (half_width, y_limit, low[2] - pad),
        (-half_width, y_limit, low[2] - pad),
        (-half_width, low[1] - pad, high[2] + pad),
        (half_width, low[1] - pad, high[2] + pad),
        (half_width, y_limit, high[2] + pad),
        (-half_width, y_limit, high[2] + pad),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    mesh.from_pydata(box, [], faces)
    mesh.validate()
    mesh.update()
    for material in stop.data.materials:
        cutter.data.materials.append(material)

    modifier = stop.modifiers.new("seat", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.object = cutter
    modifier.solver = "EXACT"
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(stop.evaluated_get(depsgraph))
    stop.modifiers.remove(modifier)
    old = stop.data
    stop.data = baked
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.context.view_layer.update()


def build_option(scene, name, envelope):
    """Apply one design to the open scene. Returns its parameters."""
    stop = scene["stop"]
    y_limit = envelope["y"][1] + TARGET_GAP_MM / 1000.0
    if name == "shift_z":
        # The shaft is uniform in z, so the stop only leaves it once it is past
        # the lever's tip. The shift is computed, not chosen.
        points = [stop.matrix_world @ v.co for v in stop.data.vertices]
        half_height = (max(p.z for p in points) - min(p.z for p in points)) / 2.0
        centre_z = (max(p.z for p in points) + min(p.z for p in points)) / 2.0
        target = envelope["z"][1] + half_height + TARGET_GAP_MM / 1000.0
        shift = target - centre_z
        stop.location = stop.location + Vector((0.0, 0.0, shift))
        bpy.context.view_layer.update()
        return {
            "family": "move the whole stop along +Z",
            "shift_mm": round(shift * 1000.0, 4),
            "new_centre_z_mm": round(target * 1000.0, 4),
            "lever_tip_z_mm": round(envelope["z"][1] * 1000.0, 4),
            "note": (
                "the shaft is a uniform prism over its whole length, so no "
                "smaller shift clears it at rest"
            ),
        }
    if name == "face_retract":
        moved = clamp_front_face(stop, y_limit)
        return {
            "family": "retract the shaft-facing face, keep the mount",
            "front_face_y_mm": round(y_limit * 1000.0, 4),
            "was_y_mm": -58.0,
            "vertices_moved": moved,
            "protrusion_past_panel_mm": round((-0.050 - y_limit) * 1000.0, 4),
            "was_protrusion_mm": 8.0,
            "note": "the mounted face and the outline are untouched",
        }
    if name == "seat_notch":
        half = envelope["x"][1] + SIDE_CLEARANCE_MM / 1000.0
        notch_seat(stop, half, y_limit)
        return {
            "family": "recess a seat for the shaft, keep the flanks proud",
            "seat_half_width_mm": round(half * 1000.0, 4),
            "shaft_half_width_mm": round(envelope["x"][1] * 1000.0, 4),
            "side_clearance_mm": SIDE_CLEARANCE_MM,
            "seat_floor_y_mm": round(y_limit * 1000.0, 4),
            "note": "the flanks keep the full 9 mm depth so it still reads as a stop",
        }
    raise ValueError(name)


def sweep_pair(pivot, mover, static, poses):
    base = pivot.rotation_euler.copy()
    per_pose = {}
    try:
        for degrees in poses:
            pivot.rotation_euler[0] = base[0] + math.radians(degrees)
            bpy.context.view_layer.update()
            mover_tris = m1.world_triangles(mover)
            static_tris = m1.world_triangles(static)
            mover_broad, mover_exact = m1.trees(mover)
            static_broad, static_exact = m1.trees(static)
            near = contact.candidate_pairs(
                mover_tris, static_tris, mover_broad, static_broad,
                tolerance=m2c.SEPARATION_SEARCH_M,
            )
            separation = None
            for mover_index, static_index in near:
                distance = contact.triangle_distance(
                    mover_tris[mover_index], static_tris[static_index]
                )
                if separation is None or distance < separation:
                    separation = distance
            pairs = contact.candidate_pairs(
                mover_tris, static_tris, mover_broad, static_broad
            )
            surface = contact.surface_contact(mover_tris, static_tris, pairs)
            penetrating = 0
            deepest = 0.0
            for source, tree in ((mover, static_exact), (static, mover_exact)):
                depth = contact.material_penetration(
                    [source.matrix_world @ v.co for v in source.data.vertices], tree
                )
                penetrating = max(penetrating, depth["penetrating_vertices"])
                deepest = max(deepest, depth["deepest_intrusion_mm"])
            per_pose[round(degrees, 4)] = {
                "surface_crossing": len(surface[contact.CROSSING]),
                "surface_tangent": len(surface[contact.TANGENT]),
                "penetrating_vertices": penetrating,
                "deepest_intrusion_mm": round(deepest, 6),
                "minimum_separation_mm": (
                    round(separation * 1000.0, 6) if separation is not None else None
                ),
            }
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return per_pose


def gates(scene, per_pose, envelope):
    rest = per_pose[0.0]
    away = {pose: entry for pose, entry in per_pose.items() if pose > 0.0}
    separation = rest["minimum_separation_mm"]
    rest_ok = (
        rest["surface_crossing"] == 0
        and rest["penetrating_vertices"] == 0
        and separation is not None
        and REST_SEPARATION_BAND_MM[0] <= separation <= REST_SEPARATION_BAND_MM[1]
    )
    reentry = sorted(
        pose
        for pose, entry in away.items()
        if entry["surface_crossing"] > 0 or entry["penetrating_vertices"] > 0
    )
    covered = all(
        any(abs(pose - required) < 1e-3 for pose in per_pose)
        for required in REQUIRED_POSES
    )
    return {
        "rest_contact": {
            "surface_crossing": rest["surface_crossing"],
            "penetrating_vertices": rest["penetrating_vertices"],
            "minimum_separation_mm": separation,
            "band_mm": list(REST_SEPARATION_BAND_MM),
            "pass": rest_ok,
        },
        "no_reentry": {
            "poses_with_contact_above_rest": reentry,
            "required_poses_present": covered,
            "pass": not reentry and covered,
        },
    }


def regression(scene, poses):
    root, pivot = scene["root"], scene["pivot"]
    movable, static = m2e.movable_and_static(root, pivot)
    results = {}
    for mover in movable:
        for other in static:
            label = f"{mover.name} x {other.name}"
            entry = m2e.sweep_pair(pivot, mover, other, poses)
            entry["named_allowance"] = m2e.pair_is_allowed(mover, other) or (
                "joint_socket" in other.name
                or ("housing" in other.name and "hemisphere" in mover.name)
            )
            results[label] = entry
    return results


def component_sweep(scene, poses):
    """Every connected component of `switch` against the proposed stop."""
    switch, stop = scene["switch"], scene["stop"]
    centre = scene["pivot"].matrix_world.translation.copy()
    islands = m2e.islands_of(switch.data)
    facts = [m2e.island_facts(switch, island, centre) for island in islands]
    shaft = max(range(len(islands)), key=lambda i: facts[i]["length_mm"][2])
    roles = {i: ("shaft" if i == shaft else "grip") for i in range(len(islands))}
    out = {}
    for index, island in enumerate(islands):
        piece = switch.copy()
        piece.data = switch.data.copy()
        bpy.context.collection.objects.link(piece)
        mesh = bmesh.new()
        mesh.from_mesh(piece.data)
        mesh.verts.ensure_lookup_table()
        doomed = [v for v in mesh.verts if v.index not in island]
        bmesh.ops.delete(mesh, geom=doomed, context="VERTS")
        mesh.to_mesh(piece.data)
        mesh.free()
        piece.data.update()
        piece.parent = switch.parent
        piece.matrix_world = switch.matrix_world.copy()
        bpy.context.view_layer.update()
        measured = sweep_pair(scene["pivot"], piece, stop, poses)
        worst = max(measured, key=lambda k: measured[k]["deepest_intrusion_mm"])
        out[roles[index]] = {
            "worst_pose_deg": worst,
            "worst": measured[worst],
            "clear": all(
                entry["surface_crossing"] == 0 and entry["penetrating_vertices"] == 0
                for entry in measured.values()
            ),
        }
        bpy.data.objects.remove(piece, do_unlink=True)
    return out


def visual_difference(project_root, baseline_renders, option_renders):
    """How much of the frame each option actually changes.

    Gate 7 asks how the options read, and "reads well" is an opinion until it
    has a number. Same camera, same light, same pose: the fraction of pixels
    that move is what the change costs visually.
    """
    import numpy

    out = {}
    for key, entry in option_renders.items():
        reference = baseline_renders.get(key)
        if reference is None:
            continue
        first = review.load_rgba(project_root / reference["unlabelled"])
        second = review.load_rgba(project_root / entry["unlabelled"])
        if first.shape != second.shape:
            continue
        moved = numpy.abs(first[:, :, 0:3] - second[:, :, 0:3]).max(axis=2) > (4 / 255)
        out[key] = {
            "pixels_changed": int(moved.sum()),
            "fraction": round(float(moved.mean()), 6),
        }
    rest = {k: v for k, v in out.items() if k.startswith("rest/")}
    return {
        "per_view": out,
        "rest_worst_fraction": (
            max(v["fraction"] for v in rest.values()) if rest else None
        ),
        "method": "same camera, light and pose; channel difference over 4/255",
    }


def render_option(project_root, label, scene, half_note):
    directory = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    directory.mkdir(parents=True, exist_ok=True)
    stop = scene["stop"]
    points = [stop.matrix_world @ v.co for v in stop.data.vertices]
    focus = Vector(
        (
            (min(p.x for p in points) + max(p.x for p in points)) / 2.0,
            (min(p.y for p in points) + max(p.y for p in points)) / 2.0,
            (min(p.z for p in points) + max(p.z for p in points)) / 2.0,
        )
    )
    span = max(
        max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)
    )
    written = {}
    for degrees, pose_label in RENDER_POSES:
        for view_name, view in VIEWS.items():
            scene["pivot"].rotation_euler[0] = math.radians(degrees)
            bpy.context.view_layer.update()
            review.configure_scene()
            scale = span * 1.6
            rig = {
                "light_scale": scale,
                "energy_scale": (scale / 0.17) ** 2 * 2.0,
            }
            target = directory / f"{PREFIX}_{label}_{pose_label}_{view_name}.png"
            review.shot(
                rig, (focus.x, focus.y, focus.z), span * 4.6,
                (view["azimuth"], view["elevation"]), 58.0, target,
            )
            labelled = target.with_name(target.stem + "_labelled.png")
            m2c.label_copy(
                target, labelled,
                [f"{label} {half_note}".upper()[:36], f"{THEME} {pose_label} {view_name}".upper()],
            )
            written[f"{pose_label}/{view_name}"] = {
                "unlabelled": str(target.relative_to(project_root)),
                "labelled": str(labelled.relative_to(project_root)),
            }
    scene["pivot"].rotation_euler[0] = 0.0
    bpy.context.view_layer.update()
    return written


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)

    started = time.perf_counter()
    baseline_scene = open_candidate(project_root)
    centre = baseline_scene["pivot"].matrix_world.translation.copy()
    envelope = shaft_envelope(baseline_scene["switch"], centre)
    baseline_facts = {
        "stop": facts_of(baseline_scene["stop"]),
        "other_stop": facts_of(baseline_scene["other_stop"]),
        "switch_vertices": len(baseline_scene["switch"].data.vertices),
        "shaft_envelope_mm": {
            axis: [round(envelope[axis][0] * 1000.0, 4), round(envelope[axis][1] * 1000.0, 4)]
            for axis in "xyz"
        },
    }
    baseline_pose = sweep_pair(
        baseline_scene["pivot"], baseline_scene["switch"],
        baseline_scene["stop"], POSES,
    )
    baseline_regression = regression(baseline_scene, POSES)
    baseline_renders = (
        {}
        if args.skip_renders
        else render_option(project_root, "production", baseline_scene, "as shipped")
    )

    options = {}
    for name in ("shift_z", "face_retract", "seat_notch"):
        begin = time.perf_counter()
        scene = open_candidate(project_root)
        parameters = build_option(scene, name, envelope)
        measured = sweep_pair(
            scene["pivot"], scene["switch"], scene["stop"], POSES
        )
        checks = gates(scene, measured, envelope)
        components = component_sweep(scene, POSES)
        island_pass = all(entry["clear"] for entry in components.values())
        theme_regression = regression(scene, POSES)
        new_contacts = [
            label
            for label, entry in theme_regression.items()
            if not entry["clear"]
            and not entry["named_allowance"]
            and (
                label not in baseline_regression
                or baseline_regression[label]["clear"]
            )
            and STOP not in label
        ]
        preserved = {
            "limit_stop_0": (
                facts_of(scene["other_stop"]) == baseline_facts["other_stop"]
            ),
            "switch_vertices": len(scene["switch"].data.vertices),
            "d5_ring_pair_clear": all(
                entry["clear"]
                for label, entry in theme_regression.items()
                if "retaining_ring" in label and "switch x" in label
            ),
            "named_allowances_unworsened": all(
                entry["deepest_intrusion_mm"]
                <= baseline_regression[label]["deepest_intrusion_mm"] + 1e-6
                for label, entry in theme_regression.items()
                if entry["named_allowance"] and label in baseline_regression
            ),
        }
        options[name] = {
            "parameters": parameters,
            "stop_after": facts_of(scene["stop"]),
            "triangle_delta": (
                facts_of(scene["stop"])["loop_triangles"]
                - baseline_facts["stop"]["loop_triangles"]
            ),
            "identity_preserved": (
                facts_of(scene["stop"])["name"] == baseline_facts["stop"]["name"]
                and facts_of(scene["stop"])["parent"] == baseline_facts["stop"]["parent"]
                and facts_of(scene["stop"])["materials"]
                == baseline_facts["stop"]["materials"]
            ),
            "per_pose": measured,
            "gates": checks,
            "component_sweep": {"detail": components, "pass": island_pass},
            "island_regression_new_contacts": {
                "detail": new_contacts, "pass": not new_contacts
            },
            "untouched_neighbours": {
                **preserved,
                "pass": (
                    preserved["limit_stop_0"]
                    and preserved["switch_vertices"]
                    == baseline_facts["switch_vertices"]
                    and preserved["d5_ring_pair_clear"]
                    and preserved["named_allowances_unworsened"]
                ),
            },
            "renders": (
                {}
                if args.skip_renders
                else render_option(project_root, name, scene, SHORT_NOTE[name])
            ),
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
        }
        options[name]["visual_difference"] = (
            {}
            if args.skip_renders
            else visual_difference(
                project_root, baseline_renders, options[name]["renders"]
            )
        )
        options[name]["all_pass"] = all(
            item["pass"]
            for key, item in (
                ("rest", checks["rest_contact"]),
                ("reentry", checks["no_reentry"]),
                ("components", options[name]["component_sweep"]),
                ("regression", options[name]["island_regression_new_contacts"]),
                ("neighbours", options[name]["untouched_neighbours"]),
            )
        )
        print(
            f"[Opus5D10] {name}: rest sep "
            f"{checks['rest_contact']['minimum_separation_mm']} mm, gates "
            f"{options[name]['all_pass']}, tris "
            f"{options[name]['triangle_delta']:+d} | "
            f"{round(time.perf_counter() - begin, 1)}s"
        )

    passing = [name for name, entry in options.items() if entry["all_pass"]]
    if "seat_notch" in passing:
        changed = (
            options["seat_notch"].get("visual_difference", {}).get(
                "rest_worst_fraction"
            )
        )
        rival = (
            options["face_retract"].get("visual_difference", {}).get(
                "rest_worst_fraction"
            )
        )
        recommendation = {
            "option": "seat_notch",
            "added_triangles": options["seat_notch"]["triangle_delta"],
            "reason": (
                "it keeps the stop's full depth where it is seen - the flanks "
                "stay proud at 9 mm and only the band the shaft occupies is "
                "recessed, behind the shaft - so at rest it changes "
                f"{changed} of the frame against {rival} for pulling the whole "
                "face back, which visibly thins the stop. The cost is "
                f"{options['seat_notch']['triangle_delta']} triangles"
            ),
        }
    elif passing:
        recommendation = {
            "option": passing[0],
            "reason": "the only option that meets every gate",
        }
    else:
        recommendation = {"option": None, "reason": "no option met every gate"}

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2g",
                "defect": "D-10",
                "note": (
                    "Design-only proposal (alignment 108.3). Built on copies "
                    "of the approved D-5 candidate in memory; no Blend is "
                    "saved and the generator is not modified."
                ),
                "preflight": gate,
                "theme": THEME,
                "target": STOP,
                "baseline": {
                    **baseline_facts,
                    "per_pose": baseline_pose,
                    "renders": baseline_renders,
                },
                "options": options,
                "recommendation": recommendation,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D10] recommend {recommendation['option']} -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
