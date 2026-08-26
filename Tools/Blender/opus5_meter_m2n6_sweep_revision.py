"""Phase M2n6: a 230 degree sweep, a needle that stops short of the ticks, and
a front face that is unambiguously in front.

Alignment 199. Three changes, and nothing else:

1. the needle blade tip on Medium and Large is shortened by the smallest amount
   that clears all thirteen ticks over the full travel. The amount is measured,
   not assumed: a bisection on the tip radius, with the existing D-3 clearance
   floor as the acceptance test. Round is left alone - it already sweeps its
   whole scale without touching anything.
2. `kinetic_v6_zone_band` is deleted from Medium and Large.
3. whatever sits at the same depth as the needle's front face, near the axis,
   is recessed. Two surfaces at one depth is what z-fighting is, and the
   canonical models put the needle's front plane and the boss or bezel's front
   plane at exactly the same Y.

The recess moves the *static* part backwards rather than the needle forwards,
so the model's front bound is still the needle's and the bounds do not move.

Taper start, blade width, hub, root, counterweight, pivot, tick positions,
materials and UVs are untouched.

The canonical Blends are opened read-only and never saved. The revision is
written as a new Blend in the candidate tree, under a name of its own.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n6_sweep_revision.py -- \
      --project-root "$PWD" --mode build --staging /tmp/opus5-m2n6
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
import opus5_d3_solver_diagnostic as diag
import opus5_d5_candidate_build as m2e
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_handoff as m2n


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n6_sweep_revision.json"
REVISION = "M2n6"
# Alignment 199.1: one contract for every size, and the outermost tick sits
# within 0.17 degrees of it.
AMPLITUDE_DEG = 115.0
POSE_COUNT = 49
POSES = [
    -AMPLITUDE_DEG + 2.0 * AMPLITUDE_DEG * index / (POSE_COUNT - 1)
    for index in range(POSE_COUNT)
]
# Alignment 199.2: the size-scaled D-3 floors, unchanged.
CLEARANCE_FLOOR_MM = {"MeterRound": 0.700, "MeterMedium": 1.410, "MeterLarge": 2.110}
ZONE_BAND = "kinetic_v6_zone_band"
NEEDLE = "needle"
# Two front faces within this of each other read as one surface to a depth
# buffer, which is the flicker the headset showed.
COPLANAR_EPS_M = 5.0e-5
# Enough to separate them in a 24-bit depth buffer at arm's length without
# being visible as a step: a fifth of a millimetre.
RECESS_M = 2.0e-4
SEARCH_RADIUS_M = 0.02
# A static whose inner edge sits just past the needle's tip still shares the
# same screen pixels at a glancing angle, so the reach test is not exact.
REACH_MARGIN_M = 0.002


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


def revision_report(project_root, key):
    stem = m2n.SOURCES[key]["report"].replace(".json", "")
    return project_root / m2l.REPORT_DIR / f"{stem}_{REVISION}.json"


# --------------------------------------------------------------------------
# Measurement


def axis_frame(pivot):
    """Centre and the two axes the dial lives in: radial in XZ, depth in Y."""
    return pivot.matrix_world.translation.copy()


def radial(point, centre):
    return math.hypot(point.x - centre.x, point.z - centre.z)


def needle_extent(obj, centre):
    matrix = obj.matrix_world
    radii = [radial(matrix @ vertex.co, centre) for vertex in obj.data.vertices]
    return min(radii), max(radii)


def all_ticks(root):
    return sorted(
        obj.name for obj in pilot.meshes_under(root) if obj.name.startswith("kinetic_tick_")
    )


def tick_clearance(root, pivot, centre):
    """The approved D-3 measurement, over all thirteen ticks and the new travel.

    `diag.measure` walks the D-3 allow-list, which is the three ticks that
    phase cared about. Alignment 199.2 asks about all thirteen, because the
    wider sweep reaches ticks D-3 never had to think about.
    """
    previous_poses = diag.POSES
    previous_ticks = diag.m2m.ALLOWLIST
    diag.POSES = POSES
    diag.m2m.ALLOWLIST = tuple(all_ticks(root))
    try:
        return diag.measure(root, pivot, centre, SEARCH_RADIUS_M)
    finally:
        diag.POSES = previous_poses
        diag.m2m.ALLOWLIST = previous_ticks


def sweep_contacts(root, pivot):
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    statics = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name not in m2e.m2d.hierarchy(obj)
    ]
    return m2k.sweep_contacts(pivot, movable, statics, POSES), movable, statics


# --------------------------------------------------------------------------
# The three changes


def remove_zone_band(root):
    obj = bpy.data.objects.get(ZONE_BAND)
    if obj is None:
        return {"present": False, "removed": False}
    triangles = len(obj.data.loop_triangles) or (
        obj.data.calc_loop_triangles() or len(obj.data.loop_triangles)
    )
    vertices = len(obj.data.vertices)
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    return {
        "present": True,
        "removed": True,
        "vertices": vertices,
        "triangles": triangles,
    }


def shorten_tip(obj, centre, start_radius, target_radius):
    """Compress the blade beyond the taper start, leaving the taper start put.

    Each vertex keeps its depth and its offset across the blade; only the
    distance along the blade changes, and only past `start_radius`. The tip
    profile is preserved in shape, and the width at any fraction of the
    remaining length is what it was at that fraction before.
    """
    matrix = obj.matrix_world
    inverse = matrix.inverted()
    longest = max(
        radial(matrix @ vertex.co, centre) for vertex in obj.data.vertices
    )
    if longest <= start_radius:
        return 0.0
    scale = (target_radius - start_radius) / (longest - start_radius)
    for vertex in obj.data.vertices:
        world = matrix @ vertex.co
        distance = radial(world, centre)
        if distance <= start_radius:
            continue
        direction = Vector((world.x - centre.x, 0.0, world.z - centre.z))
        if direction.length == 0.0:
            continue
        direction.normalize()
        wanted = start_radius + (distance - start_radius) * scale
        moved = world - direction * (distance - wanted)
        vertex.co = inverse @ moved
    obj.data.update()
    return longest - target_radius


def front_of(obj):
    matrix = obj.matrix_world
    return min((matrix @ vertex.co).y for vertex in obj.data.vertices)


def recess_coplanar_fronts(root, pivot, centre, needle):
    """Push back anything sharing the needle's front plane near the axis."""
    needle_front = front_of(needle)
    reach = needle_extent(needle, centre)[1]
    moved = []
    survey = []
    for obj in pilot.meshes_under(root):
        if obj is needle or pivot.name in m2e.m2d.hierarchy(obj):
            continue
        front = front_of(obj)
        near = min(
            radial(obj.matrix_world @ vertex.co, centre)
            for vertex in obj.data.vertices
        )
        survey.append(
            {
                "object": obj.name,
                "front_m": round(front, 7),
                "depth_gap_mm": round((front - needle_front) * 1000.0, 5),
                "nearest_radius_mm": round(near * 1000.0, 4),
                "within_needle_reach": near <= reach + REACH_MARGIN_M,
            }
        )
        if abs(front - needle_front) > COPLANAR_EPS_M:
            continue
        if near > reach + REACH_MARGIN_M:
            continue
        obj.location.y += RECESS_M
        bpy.context.view_layer.update()
        moved.append(
            {
                "object": obj.name,
                "front_before_m": round(front, 7),
                "front_after_m": round(front_of(obj), 7),
                "nearest_radius_mm": round(near * 1000.0, 4),
            }
        )
    survey.sort(key=lambda row: abs(row["depth_gap_mm"]))
    return {
        "needle_front_m": round(needle_front, 7),
        "needle_reach_mm": round(reach * 1000.0, 4),
        "coplanar_epsilon_m": COPLANAR_EPS_M,
        "recess_m": RECESS_M,
        "recessed": moved,
        # The nearest few in depth, whether or not they were moved, so a
        # "nothing was coplanar" result can be read rather than trusted.
        "closest_in_depth": survey[:6],
    }


def find_shortening(root, pivot, centre, needle, floor_mm):
    """The least the tip has to give up, found by measurement."""
    start_radius, longest = needle_extent(needle, centre)
    # The taper start is where the blade leaves the hub; the hub's own radius
    # is the smallest radius the blade occupies.
    low, high = start_radius, longest
    attempts = []
    best = None
    # `bpy.ops.ed.undo` has no context to work in when Blender runs headless,
    # so the trial is undone by putting the coordinates back.
    original = [vertex.co.copy() for vertex in needle.data.vertices]

    def restore():
        for vertex, coordinate in zip(needle.data.vertices, original):
            vertex.co = coordinate
        needle.data.update()
        bpy.context.view_layer.update()

    for _ in range(7):
        middle = (low + high) / 2.0
        restore()
        removed = shorten_tip(needle, centre, start_radius, middle)
        worst, per_tick = tick_clearance(root, pivot, centre)
        # No worst pair means no tick came within the search radius at all,
        # which is 20 mm - an order above any floor. That is the cleanest
        # possible result, not a missing measurement.
        distance = worst["distance_mm"] if worst else None
        ok = distance is None or distance >= floor_mm
        attempts.append(
            {
                "tip_radius_mm": round(middle * 1000.0, 4),
                "removed_mm": round(removed * 1000.0, 4),
                "worst_tick_clearance_mm": distance,
                "worst_pair": worst["pair"] if worst else None,
                "worst_pose_deg": worst["pose_deg"] if worst else None,
                "meets_floor": ok,
            }
        )
        if ok:
            best = (middle, removed, worst, per_tick)
            low = middle
        else:
            high = middle
    restore()
    return best, attempts, start_radius, longest


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    staging.mkdir(parents=True, exist_ok=True)
    blender_compat.require_v6_pipeline()

    payload = {
        "phase": "M2n6",
        "note": (
            "230 degree sweep revision (alignment 199). Needle tip shortened "
            "by measurement on Medium and Large, zone band removed, front "
            "faces separated. Canonical Blends are read-only."
        ),
        "amplitude_deg": AMPLITUDE_DEG,
        "poses": POSE_COUNT,
        "clearance_floor_mm": CLEARANCE_FLOOR_MM,
    }
    started = time.perf_counter()
    try:
        before = {}
        results = {}
        # Attached now, so a model that raises later still leaves behind what
        # the models before it measured.
        payload["models"] = results
        for key, spec in m2n.SOURCES.items():
            begin = time.perf_counter()
            path = m2n.source_blend(project_root, key)
            digest = m1.digest(path)
            before[key] = {"blend": str(path.relative_to(project_root)), "sha256": digest}
            if digest != spec["sha256"]:
                raise SystemExit(f"[Opus5M2n6] {key}: source hash moved")
            m1.open_blend(path)
            root = bpy.data.objects[m2k.MODELS[key]["root"]]
            pivot = bpy.data.objects[m2n.MOTION["pivot"]]
            centre = axis_frame(pivot)
            needle = bpy.data.objects[NEEDLE]

            zone = remove_zone_band(root)
            hub_radius, reach_before = needle_extent(needle, centre)

            shortening = {"applied": False, "removed_mm": 0.0}
            attempts = []
            best = None
            if key != "MeterRound":
                best, attempts, hub_radius, reach_before = find_shortening(
                    root, pivot, centre, needle, CLEARANCE_FLOOR_MM[key]
                )
                # A failed search is data, not a reason to lose the run: the
                # attempts say what the clearance actually did as the tip came
                # in, which is the only way to see why it never cleared.
                shortening = {
                    "applied": best is not None,
                    "search_failed": best is None,
                    "removed_mm": 0.0,
                    "floor_mm": CLEARANCE_FLOOR_MM[key],
                    "attempts": attempts,
                }
            if key != "MeterRound" and best is not None:
                target, removed, _, _ = best
                shorten_tip(needle, centre, hub_radius, target)
                shortening = {
                    "applied": True,
                    "taper_start_radius_mm": round(hub_radius * 1000.0, 4),
                    "reach_before_mm": round(reach_before * 1000.0, 4),
                    "reach_after_mm": round(target * 1000.0, 4),
                    "removed_mm": round(removed * 1000.0, 4),
                    "removed_fraction_of_blade": round(
                        removed / (reach_before - hub_radius), 6
                    ),
                    "attempts": attempts,
                }
            if key != "MeterRound" and best is None:
                print(f"[Opus5M2n6] {key}: no tip radius met the floor; see attempts")

            depth = recess_coplanar_fronts(root, pivot, centre, needle)
            worst, per_tick = tick_clearance(root, pivot, centre)
            contacts, movable, statics = sweep_contacts(root, pivot)
            unresolved = sorted(
                label for label, entry in contacts.items() if not entry["clear"]
            )
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
            target_blend = revision_blend(project_root, key)
            target_blend.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(target_blend), copy=True)

            results[key] = {
                "model": key,
                "source": before[key],
                "revision_blend": str(target_blend.relative_to(project_root)),
                "revision_blend_sha256": m1.digest(target_blend),
                "zone_band": zone,
                "needle_shortening": shortening,
                "depth_ordering": depth,
                "sweep": {
                    "amplitude_deg": AMPLITUDE_DEG,
                    "poses": POSE_COUNT,
                    "contacting_pairs": {
                        label: {
                            "poses_in_contact": entry["poses_in_contact"],
                            "deepest_intrusion_mm": entry["deepest_intrusion_mm"],
                            "classification": entry["classification"],
                        }
                        for label, entry in sorted(contacts.items())
                        if not entry["clear"]
                    },
                    "unresolved_labels": unresolved,
                },
                "tick_clearance": {
                    "floor_mm": CLEARANCE_FLOOR_MM[key],
                    "worst": worst,
                    "per_tick": per_tick,
                    "meets_floor": bool(worst)
                    and worst["distance_mm"] >= CLEARANCE_FLOOR_MM[key],
                },
                "bounds": bounds,
                "triangles": triangles,
                "triangles_before": spec["triangles"],
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
            print(
                f"[Opus5M2n6] {key}: zone {zone['removed']}, tip -"
                f"{shortening['removed_mm']} mm, recessed "
                f"{len(depth['recessed'])}, worst tick "
                f"{worst['distance_mm'] if worst else None} mm, contacts "
                f"{len(unresolved)}, tris {triangles}"
            )
        payload["models"] = results
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
            f"[Opus5M2n6] status {payload.get('status')}, sources unchanged "
            f"{payload.get('sources_unchanged')}"
        )


if __name__ == "__main__":
    main()
