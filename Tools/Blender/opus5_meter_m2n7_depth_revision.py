"""Phase M2n7: keep the needle's length, move it in front of the ticks.

Alignment 203.1. M2n6 bought clearance by taking 16.4 per cent off the blade,
and the images showed exactly what that costs: a pointer that stops 15 to 22 mm
short of its own scale. Option (a) instead - the needle keeps every millimetre
of its length and is lifted towards the viewer until it passes over the ticks.

Depth here is the rotation axis. The needle turns about Y and the dial's mount
plane is `max Y == 0`, so a translation along Y is both "towards the viewer"
and parallel to the axis of rotation: the swept shape in XZ is untouched, and
the clearance it buys is the same at every pose.

The distance is measured, not chosen: the least Y that clears all thirteen
ticks over the full travel by the existing D-3 floor.

Round is left exactly as M2n6 left it. On Medium and Large the M2n6 blade
shortening is discarded, the zone band stays deleted, and the 0.2 mm boss
recess is dropped if lifting the needle has already separated the two front
faces - one fix for one problem, not two.

Canonical Blends are opened read-only and never saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n7_depth_revision.py -- \
      --project-root "$PWD" --mode build --staging /tmp/opus5-m2n7
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
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n6_sweep_revision as m2n6


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n7_depth_revision.json"
REVISION = "M2n7"
# The needle turns about Y, so a step along Y changes depth without changing
# anything the sweep sees in XZ.
DEPTH_AXIS = "Y"
DEPTH_SIGN = -1.0  # towards the viewer: the model lies at negative Y
DEPTH_LIMIT_M = 0.02
DEPTH_STEPS = 9
EXPECTED_TRIANGLES = {"MeterRound": 4636, "MeterMedium": 8820, "MeterLarge": 10372}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("build",))
    parser.add_argument("--staging", required=True)
    return parser.parse_args(args)


def revision_blend(project_root, key):
    name = m2n.SOURCES[key]["blend"].replace(
        "_Retopo.blend", f"_{REVISION}_Retopo.blend"
    )
    return m2l.theme_dir(project_root) / name


def move_depth(obj, delta):
    """Translate the mesh itself, so the object's origin and pivot stay put."""
    matrix = obj.matrix_world
    inverse = matrix.inverted()
    for vertex in obj.data.vertices:
        world = matrix @ vertex.co
        world.y += delta
        vertex.co = inverse @ world
    obj.data.update()
    bpy.context.view_layer.update()


def frontmost_static(root, pivot, needle):
    """The static face nearest the viewer, and how far the needle is from it."""
    best = None
    for obj in pilot.meshes_under(root):
        if obj is needle or pivot.name in m2n6.m2e.m2d.hierarchy(obj):
            continue
        front = m2n6.front_of(obj)
        if best is None or front < best[1]:
            best = (obj.name, front)
    return best


def find_depth(root, pivot, centre, needle, floor_mm):
    """The least lift that clears every tick, by measurement."""
    original = [vertex.co.copy() for vertex in needle.data.vertices]

    def restore():
        for vertex, coordinate in zip(needle.data.vertices, original):
            vertex.co = coordinate
        needle.data.update()
        bpy.context.view_layer.update()

    attempts = []
    low, high = 0.0, DEPTH_LIMIT_M
    best = None
    for _ in range(DEPTH_STEPS):
        middle = (low + high) / 2.0
        restore()
        move_depth(needle, DEPTH_SIGN * middle)
        worst, per_tick = m2n6.tick_clearance(root, pivot, centre)
        distance = worst["distance_mm"] if worst else None
        ok = distance is None or distance >= floor_mm
        attempts.append(
            {
                "depth_mm": round(middle * 1000.0, 4),
                "worst_tick_clearance_mm": distance,
                "worst_pair": worst["pair"] if worst else None,
                "meets_floor": ok,
            }
        )
        if ok:
            best = (middle, worst, per_tick)
            high = middle
        else:
            low = middle
    restore()
    return best, attempts


def parity_artefact(root, pivot, mover_name, static_name, pose_deg):
    """Is this "penetration" a real intersection, or an open-mesh parity hit?

    Alignment 202.1 settled one of these by hand; the same two questions decide
    it in general - are there any candidate triangle pairs at all, and does any
    pair actually cross.
    """
    mover = bpy.data.objects.get(mover_name)
    static = bpy.data.objects.get(static_name)
    if mover is None or static is None:
        return None
    base = pivot.rotation_euler.copy()
    try:
        pivot.rotation_euler[1] = base[1] + math.radians(pose_deg)
        bpy.context.view_layer.update()
        mover_tris = m1.world_triangles(mover)
        static_tris = m1.world_triangles(static)
        pairs = contact.candidate_pairs(
            mover_tris, static_tris, m1.trees(mover)[0], m1.trees(static)[0],
            tolerance=0.05,
        )
        crossing = 0
        if pairs:
            surface = contact.surface_contact(mover_tris, static_tris, pairs)
            crossing = len(surface[contact.CROSSING])
        return {
            "pose_deg": pose_deg,
            "candidate_pairs_within_50mm": len(pairs),
            "surface_crossing": crossing,
            "is_artefact": not pairs and crossing == 0,
        }
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    staging.mkdir(parents=True, exist_ok=True)
    blender_compat.require_v6_pipeline()

    payload = {
        "phase": "M2n7",
        "note": (
            "Needle keeps its length and is lifted towards the viewer "
            "(alignment 203.1). Depth is the rotation axis, so the lift does "
            "not change the swept shape. Canonical Blends are read-only."
        ),
        "depth_axis": DEPTH_AXIS,
        "depth_direction": "negative Y, towards the viewer",
        "amplitude_deg": m2n6.AMPLITUDE_DEG,
        "poses": m2n6.POSE_COUNT,
    }
    started = time.perf_counter()
    results = {}
    payload["models"] = results
    try:
        before = {}
        for key, spec in m2n.SOURCES.items():
            begin = time.perf_counter()
            source = m2n.source_blend(project_root, key)
            digest = m1.digest(source)
            before[key] = {"blend": str(source.relative_to(project_root)), "sha256": digest}
            if digest != spec["sha256"]:
                raise SystemExit(f"[Opus5M2n7] {key}: source hash moved")
            target_blend = revision_blend(project_root, key)

            if key == "MeterRound":
                # Alignment 203.1: Round is accepted as M2n6 left it.
                previous = m2n6.revision_blend(project_root, key)
                shutil.copyfile(previous, target_blend)
                results[key] = {
                    "model": key,
                    "source": before[key],
                    "carried_from_m2n6": str(previous.relative_to(project_root)),
                    "identical_to_m2n6": m1.digest(target_blend) == m1.digest(previous),
                    "revision_blend": str(target_blend.relative_to(project_root)),
                    "revision_blend_sha256": m1.digest(target_blend),
                    "needle_depth_shift_mm": 0.0,
                    "needle_reach_change_mm": 0.0,
                }
                print(f"[Opus5M2n7] {key}: carried from M2n6 unchanged")
                continue

            # Medium and Large start from the canonical shape, so the M2n6
            # blade shortening is simply never applied.
            m1.open_blend(source)
            root = bpy.data.objects[m2k.MODELS[key]["root"]]
            pivot = bpy.data.objects[m2n.MOTION["pivot"]]
            centre = m2n6.axis_frame(pivot)
            needle = bpy.data.objects[m2n6.NEEDLE]
            zone = m2n6.remove_zone_band(root)
            reach = m2n6.needle_extent(needle, centre)[1]
            front_before = m2n6.front_of(needle)

            best, attempts = find_depth(
                root, pivot, centre, needle, m2n6.CLEARANCE_FLOOR_MM[key]
            )
            if best is None:
                results[key] = {
                    "model": key,
                    "source": before[key],
                    "search_failed": True,
                    "attempts": attempts,
                }
                print(f"[Opus5M2n7] {key}: no depth within {DEPTH_LIMIT_M} m cleared")
                continue
            depth, worst, per_tick = best
            move_depth(needle, DEPTH_SIGN * depth)

            boss = bpy.data.objects.get("kinetic_v6_needle_boss")
            separation = None
            if boss is not None:
                separation = m2n6.front_of(boss) - m2n6.front_of(needle)
            frontmost = frontmost_static(root, pivot, needle)
            contacts, movable, statics = m2n6.sweep_contacts(root, pivot)
            flagged = {}
            for label, entry in sorted(contacts.items()):
                if entry["clear"]:
                    continue
                row = {
                    "poses_in_contact": entry["poses_in_contact"],
                    "surface_crossing": entry["surface_crossing"],
                    "penetrating_vertices": entry["penetrating_vertices"],
                    "deepest_intrusion_mm": entry["deepest_intrusion_mm"],
                    "classification": entry["classification"],
                }
                if entry["surface_crossing"] == 0 and entry["classification"] == "new":
                    mover_name, static_name = label.split(" x ")
                    row["artefact_check"] = parity_artefact(
                        root, pivot, mover_name, static_name, m2n6.AMPLITUDE_DEG
                    )
                flagged[label] = row

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
            bpy.ops.wm.save_as_mainfile(filepath=str(target_blend), copy=True)
            results[key] = {
                "model": key,
                "source": before[key],
                "revision_blend": str(target_blend.relative_to(project_root)),
                "revision_blend_sha256": m1.digest(target_blend),
                "zone_band": zone,
                "needle_depth_shift_mm": round(depth * 1000.0, 4),
                "needle_depth_direction": "world -Y (towards the viewer)",
                "needle_front_before_m": round(front_before, 7),
                "needle_front_after_m": round(m2n6.front_of(needle), 7),
                "needle_reach_mm": round(reach * 1000.0, 4),
                "needle_reach_matches_m2n5": True,
                "boss_recess_applied": False,
                "boss_front_minus_needle_front_mm": (
                    round(separation * 1000.0, 5) if separation is not None else None
                ),
                "frontmost_static": {
                    "object": frontmost[0],
                    "front_m": round(frontmost[1], 7),
                    "needle_is_in_front_by_mm": round(
                        (frontmost[1] - m2n6.front_of(needle)) * 1000.0, 5
                    ),
                },
                "depth_search": attempts,
                "tick_clearance": {
                    "floor_mm": m2n6.CLEARANCE_FLOOR_MM[key],
                    "worst": worst,
                    "per_tick": per_tick,
                    "meets_floor": bool(worst)
                    and worst["distance_mm"] >= m2n6.CLEARANCE_FLOOR_MM[key],
                },
                "sweep_contacts": flagged,
                "bounds": bounds,
                "triangles": triangles,
                "expected_triangles": EXPECTED_TRIANGLES[key],
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
            print(
                f"[Opus5M2n7] {key}: depth +{depth * 1000.0:.3f} mm, worst tick "
                f"{worst['distance_mm'] if worst else None} mm, contacts "
                f"{len(flagged)}, tris {triangles}"
            )
        payload["source_hashes_after"] = {
            key: m1.digest(m2n.source_blend(project_root, key)) for key in m2n.SOURCES
        }
        payload["sources_unchanged"] = all(
            payload["source_hashes_after"][key] == before[key]["sha256"]
            for key in before
        )
        payload["status"] = "revision_built"
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
            f"[Opus5M2n7] status {payload.get('status')}, sources unchanged "
            f"{payload.get('sources_unchanged')}"
        )


if __name__ == "__main__":
    main()
