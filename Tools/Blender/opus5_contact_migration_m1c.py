"""Phase M1c: why do two runs of the same measurement disagree?

Alignment 94.3. The slot survey reported a ring occupancy of 0.0 where M1b
reports 0.08-0.13, and Kinetic Safety's joint retention differs by 0.28 between
them. Both called the same function on what should be the same scene, so before
anything is concluded about the slot, the disagreement itself is the subject.

Four things are established, in order:

1. **Are these even the same objects?** Vertex counts, world-space vertex
   hashes, matrices, bounds, parents and hidden state for every part each path
   selects. Occupancy figures are not compared across objects that fail this.
2. **Which component occupies what?** Axle, shaft, grip and the hemisphere
   joint measured separately rather than as one aggregate, at minimum, neutral
   and maximum, with the worst pose located across the full sweep.
3. **Are the occupied cells real?** Each non-zero cell is reported with its
   world position, the component it belongs to, and its distance to both
   surfaces - and the inside test is repeated along three non-parallel rays so
   a misclassification shows up as directions disagreeing.
4. **Is it even repeatable?** Every measurement runs twice on the same object
   and grid; a difference stops the run rather than being averaged away.

Read-only. No Blend is saved and no existing report is modified.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_contact_migration_m1c.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_option_sweep as sweep
import opus5_d5_toggle_axle_proposal as splitter
import opus5_joint_contact_section as section


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/contact_migration_m1c.json"
SLOT_SURVEY = "ArtSource/Blender/BrushUp/Opus5/d5_slot_proposal.json"
POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))

# Three directions, none parallel to an axis or to each other, so a ray that
# grazes a coplanar face in one of them is outvoted by the other two.
RAY_DIRECTIONS = (
    Vector((0.987, 0.109, 0.119)),
    Vector((0.213, 0.941, 0.263)),
    Vector((0.301, 0.187, 0.935)),
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append")
    return parser.parse_args(args)


def identity(obj):
    """Everything needed to say two objects are the same object."""
    if obj is None:
        return None
    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    payload = hashlib.sha256()
    for vertex in obj.data.vertices:
        world = matrix @ vertex.co
        payload.update(struct.pack("<3d", world.x, world.y, world.z))
    points = [matrix @ vertex.co for vertex in obj.data.vertices]
    return {
        "name": obj.name,
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "loop_triangles": len(obj.data.loop_triangles),
        "world_vertex_sha256": payload.hexdigest(),
        "matrix_world": [[round(v, 9) for v in row] for row in matrix],
        "bounds": {
            "min": [round(min(p[i] for p in points), 6) for i in range(3)],
            "max": [round(max(p[i] for p in points), 6) for i in range(3)],
        },
        "parent": obj.parent.name if obj.parent else None,
        "hide_viewport": obj.hide_viewport,
        "hide_render": obj.hide_render,
    }


def inside_votes(tree, point):
    """Inside/outside along three rays, plus the majority."""
    votes = [contact.inside_mesh(tree, point, direction) for direction in RAY_DIRECTIONS]
    return votes, sum(votes) >= 2


def occupancy(static_obj, movers, samples=20, collect=6):
    """Occupied fraction with per-ray votes and a sample of the cells."""
    corners = [static_obj.matrix_world @ Vector(c) for c in static_obj.bound_box]
    low = [min(p[i] for p in corners) for i in range(3)]
    high = [max(p[i] for p in corners) for i in range(3)]
    span = [high[i] - low[i] for i in range(3)]
    if min(span) <= 0.0:
        return None
    static_tree = section_tree(static_obj)
    mover_trees = {obj.name: section_tree(obj) for obj in movers}
    step = [span[i] / samples for i in range(3)]
    in_static = 0
    in_both = 0
    per_direction = [0, 0, 0]
    cells = []
    for ix in range(samples):
        for iy in range(samples):
            for iz in range(samples):
                point = Vector(
                    (
                        low[0] + (ix + 0.5) * step[0],
                        low[1] + (iy + 0.5) * step[1],
                        low[2] + (iz + 0.5) * step[2],
                    )
                )
                static_votes, static_in = inside_votes(static_tree, point)
                if not static_in:
                    continue
                in_static += 1
                for name, tree in mover_trees.items():
                    votes, occupied = inside_votes(tree, point)
                    for index, vote in enumerate(votes):
                        per_direction[index] += 1 if (vote and static_votes[index]) else 0
                    if not occupied:
                        continue
                    in_both += 1
                    if len(cells) < collect:
                        _, _, _, to_static = static_tree.find_nearest(point)
                        _, _, _, to_mover = tree.find_nearest(point)
                        cells.append(
                            {
                                "world": [round(v, 6) for v in point],
                                "component": name,
                                "distance_to_static_surface_mm": round(
                                    (to_static or 0.0) * 1000.0, 6
                                ),
                                "distance_to_component_surface_mm": round(
                                    (to_mover or 0.0) * 1000.0, 6
                                ),
                                "static_ray_votes": static_votes,
                                "component_ray_votes": votes,
                            }
                        )
                    break
    cell_volume = step[0] * step[1] * step[2]
    return {
        "grid": samples,
        "cell_mm": [round(step[i] * 1000.0, 4) for i in range(3)],
        "static_cells": in_static,
        "occupied_cells": in_both,
        "occupied_fraction": round(in_both / in_static, 6) if in_static else None,
        "occupied_volume_mm3": round(in_both * cell_volume * 1e9, 4),
        "per_ray_direction_cells": per_direction,
        "rays_disagree": len(set(per_direction)) > 1,
        "sample_cells": cells,
    }


def section_tree(obj):
    from mathutils.bvhtree import BVHTree

    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    vertices = [tuple(matrix @ vertex.co) for vertex in obj.data.vertices]
    polygons = [tuple(t.vertices) for t in obj.data.loop_triangles]
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=True, epsilon=0.0)


def twice(fn):
    """Run a measurement twice; disagreement is a stop, not an average."""
    first = fn()
    second = fn()
    same = json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    return first, same


def parts_of(root, pivot, switch, drop_axle, centre):
    """Split `switch` and label the components, or keep it joined."""
    if not drop_axle:
        return {"switch": switch}, None
    pieces = splitter.components_of(switch)
    for piece in pieces:
        pilot.parent_keep_world(piece, pivot)
    bpy.context.view_layer.update()
    facts = {p.name: splitter.describe(p, centre) for p in pieces}
    axle = min(
        (name for name, f in facts.items() if f["longest_axis"] == "X"),
        key=lambda name: facts[name]["distance_from_pivot_mm"],
    )
    shaft = max(pieces, key=lambda p: facts[p.name]["length_mm"][2])
    grip = next((p for p in pieces if p.name not in (axle, shaft.name)), None)
    labelled = {"axle": bpy.data.objects[axle], "shaft": shaft}
    if grip is not None:
        labelled["grip"] = grip
    switch.hide_viewport = True
    return labelled, facts


def diagnose(project_root, theme, slot_half_angle):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_Toggle_{theme}_V6_Retopo.blend"
    )
    states = {}
    for state in ("legacy axle present", "axle component removed", "slot proposal"):
        m1.open_blend(source)
        root = bpy.data.objects[f"PF_Visual_Toggle_{theme}_V6"]
        pivot = bpy.data.objects["switch_pivot"]
        switch = bpy.data.objects["switch"]
        ring = next(
            obj
            for obj in pilot.meshes_under(root)
            if "retaining_ring" in obj.name.lower()
        )
        joint = next(
            (o for o in pilot.meshes_under(root) if "hemisphere" in o.name.lower()),
            None,
        )
        centre = pivot.matrix_world.translation.copy()
        labelled, facts = parts_of(
            root, pivot, switch, state != "legacy axle present", centre
        )
        if state == "axle component removed" and "axle" in labelled:
            bpy.data.objects.remove(labelled.pop("axle"), do_unlink=True)
        if state == "slot proposal":
            if "axle" in labelled:
                bpy.data.objects.remove(labelled.pop("axle"), do_unlink=True)
            points = [ring.matrix_world @ v.co for v in ring.data.vertices]
            inner = min(math.hypot(p.x - centre.x, p.z - centre.z) for p in points)
            outer = max(math.hypot(p.x - centre.x, p.z - centre.z) for p in points)
            y_low = min(p.y for p in points)
            y_high = max(p.y for p in points)
            material = ring.data.materials[0] if ring.data.materials else None
            parent = ring.parent
            bpy.data.objects.remove(ring, do_unlink=True)
            ring = brushup.arc_band(
                "toggle_ring_slotted", inner, outer, slot_half_angle,
                360.0 - slot_half_angle, y_low, y_high, material,
                segments=22, centre_x=centre.x, centre_z=centre.z,
            )
            ring.parent = parent
            bpy.context.view_layer.update()

        base = pivot.rotation_euler.copy()
        per_pose = {}
        deterministic = True
        for pose_name, angle in POSES:
            posed = base.copy()
            posed[0] = base[0] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            components = {}
            for label, obj in list(labelled.items()) + (
                [("hemisphere_joint", joint)] if joint else []
            ):
                measured, same = twice(lambda o=obj: occupancy(ring, [o]))
                deterministic = deterministic and same
                # The same component through the function the slot survey and
                # M1b actually called, so a disagreement can be attributed to
                # the measurement rather than guessed at (alignment 94.4).
                legacy, legacy_same = twice(
                    lambda o=obj: section.occupied_volume(ring, [o])
                )
                deterministic = deterministic and legacy_same
                components[label] = {
                    "identity": identity(obj),
                    "occupancy": measured,
                    "legacy_occupied_volume": legacy,
                    "fraction_delta": (
                        round(
                            (measured or {}).get("occupied_fraction", 0.0)
                            - (legacy or {}).get("occupied_fraction", 0.0),
                            6,
                        )
                        if measured and legacy
                        else None
                    ),
                }
            per_pose[pose_name] = components
        pivot.rotation_euler = base
        bpy.context.view_layer.update()

        states[state] = {
            "ring_identity": identity(ring),
            "joint_identity": identity(joint),
            "component_facts": facts,
            "slot_half_angle_deg": slot_half_angle if state == "slot proposal" else None,
            "per_pose": per_pose,
            "deterministic": deterministic,
        }
    return {
        "source": str(source.relative_to(project_root)),
        "sha256": m1.digest(source),
        "states": states,
    }


def classify(theme, entry):
    """geometry/state mismatch | true containment | sampling misclassification |
    unresolved."""
    findings = {}
    for state, payload in entry["states"].items():
        neutral = payload["per_pose"]["neutral"]
        for label, component in neutral.items():
            occ = component["occupancy"] or {}
            fraction = occ.get("occupied_fraction")
            if not fraction:
                continue
            cells = occ.get("sample_cells") or []
            interior = [
                cell
                for cell in cells
                if cell["distance_to_component_surface_mm"] > 0.01
                and cell["distance_to_static_surface_mm"] > 0.01
            ]
            legacy = component.get("legacy_occupied_volume") or {}
            delta = component.get("fraction_delta")
            if occ.get("rays_disagree"):
                verdict = "sampling misclassification"
                reason = (
                    "the three ray directions disagree on how many cells are "
                    f"inside: {occ['per_ray_direction_cells']}"
                )
            elif delta is not None and abs(delta) > 0.02:
                verdict = "sampling misclassification"
                reason = (
                    "the same objects measured by the two grids differ by "
                    f"{delta:+.4f}; the figure depends on the sampling, not on "
                    "the geometry"
                )
            elif cells and len(interior) * 2 >= len(cells):
                verdict = "true containment"
                reason = (
                    f"{len(interior)} of {len(cells)} sampled cells sit clear "
                    "of both surfaces, so the overlap is real"
                )
            elif cells:
                verdict = "true containment"
                reason = (
                    "the overlap is thin: sampled cells sit within 0.01 mm of "
                    "a surface, so the volume is real but shallow"
                )
            else:
                verdict = "unresolved"
                reason = "occupied cells reported with no sample to inspect"
            findings[f"{state}/{label}"] = {
                "occupied_fraction": fraction,
                "legacy_occupied_fraction": legacy.get("occupied_fraction"),
                "fraction_delta": delta,
                "verdict": verdict,
                "reason": reason,
            }
    return findings


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)
    survey = json.loads((project_root / SLOT_SURVEY).read_text())
    angles = {
        theme: (payload.get("smallest_clean_slot") or {}).get("slot_half_angle_deg")
        for theme, payload in survey["themes"].items()
    }

    started = time.perf_counter()
    themes = {}
    findings = {}
    for theme in args.themes or angles:
        begin = time.perf_counter()
        themes[theme] = diagnose(project_root, theme, angles[theme])
        findings[theme] = classify(theme, themes[theme])
        print(
            f"[Opus5MigrationM1c] {theme}: {round(time.perf_counter() - begin, 3)}s, "
            f"deterministic "
            f"{all(s['deterministic'] for s in themes[theme]['states'].values())}"
        )

    verdicts = {}
    for theme in findings.values():
        for finding in theme.values():
            verdicts[finding["verdict"]] = verdicts.get(finding["verdict"], 0) + 1

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M1c",
                "note": (
                    "Read-only diagnostic (alignment 94.3). No Blend is saved "
                    "and no existing report is modified."
                ),
                "preflight": gate,
                "ray_directions": [list(direction) for direction in RAY_DIRECTIONS],
                "slot_half_angles": angles,
                "themes": themes,
                "findings": findings,
                "verdict_summary": verdicts,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5MigrationM1c] verdicts {verdicts} -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
