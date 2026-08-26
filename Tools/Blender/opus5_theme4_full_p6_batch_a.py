"""Theme 4 Phase 3 Batch A geometry: MeterMedium, MeterLarge, Throttle, PowerSlider.

Alignment 295. The P5 pilot is frozen; this is the first production batch of
the fourth theme, and it reuses the pilot's vocabulary rather than its numbers.

Contract, measured rather than assumed (alignment 295.2 item 3). Envelopes and
renderer budgets come from InstrumentGreyboxSpecification; pivot names, motion
kinds, axes and ranges come from MockInstrumentFactory and MockInstrumentMotion;
the existing three themes' FBX were imported and measured for the shapes the
contract does not fix.

  MeterMedium  needle_pivot / needle          Unity +Z, -115..+115 deg
  MeterLarge   needle_pivot / needle          Unity +Z, -115..+115 deg
  Throttle     throttle_pivot / throttle_handle  Unity +X, -70..0 deg
  PowerSlider  slider_travel / slider_handle  Unity +Y, +-0.09 m

The throttle range is 70 degrees, not 35. `ThrottleMaximumAngleDegrees` is the
amplitude fed to `Mathf.Lerp(-amplitude, amplitude, value) + rotationOffset`
with an offset of -35, exactly as the Lever's 24 becomes -48..0. Alignment
295.2 item 5 first read it as a 35 degree range; Codex confirmed the runtime
against this measurement and corrected the item, so 70 degrees is the contract
here rather than a safe-side assumption. This is the same class of error
alignment 267 caught, and it is now checked against the runtime every time.

The meters are not scaled copies of the pilot. A 550 mm dial read from across
a room wants a larger face inside its bezel and a *thinner* body than a 149 mm
one, so the dial-to-outer ratio rises with size while the depth ratio falls,
and the tick count rises with the readable subdivision rather than with the
radius. Tick counts on the two controls come from the runtime's own detent
counts, so the scale beside the slot agrees with where the control stops.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_machined_ergonomics_p5 as p5

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a")
OUTPUT = f"{TREE}/geometry/theme4_full_p6_batch_a.json"
NEUTRAL = p3.NEUTRAL

lathe = p3.lathe
loft = p3.capsule_loft
stations = p3.station_profile

# ---------------------------------------------------------------------------
# the measured contract
# ---------------------------------------------------------------------------

# Blender authoring is (width X, depth Y, height Z) with the mount plane at
# max Y == 0 and -Y toward the viewer; Unity BoundsSize (x, y, z) is
# (width, height, depth).
CONTRACT = {
    "MeterMedium": {
        "kind": "RoundMeterMedium",
        "pivot": "needle_pivot", "moving": "needle",
        "envelope_unity_xyz": (0.36, 0.36, 0.145),
        "renderer_budget": 4, "triangle_budget_total": 25000,
        "per_object_cap": None,
        "unity_axis": "+Z", "blender_axis": "Y",
        "motion": "rotate", "amplitude_deg": 115.0, "offset_deg": 0.0,
        "unity_range_deg": (-115.0, 115.0), "blender_range_deg": (-115.0, 115.0),
        "existing_max_measured": (0.35, 0.35, 0.1317),
    },
    "MeterLarge": {
        "kind": "RoundMeterLarge",
        "pivot": "needle_pivot", "moving": "needle",
        "envelope_unity_xyz": (0.55, 0.55, 0.205),
        "renderer_budget": 4, "triangle_budget_total": 25000,
        "per_object_cap": None,
        "unity_axis": "+Z", "blender_axis": "Y",
        "motion": "rotate", "amplitude_deg": 115.0, "offset_deg": 0.0,
        "unity_range_deg": (-115.0, 115.0), "blender_range_deg": (-115.0, 115.0),
        "existing_max_measured": (0.525, 0.525, 0.1739),
    },
    "Throttle": {
        "kind": "ThrottleLever",
        "pivot": "throttle_pivot", "moving": "throttle_handle",
        "envelope_unity_xyz": (0.24, 0.34, 0.16),
        "renderer_budget": 3, "triangle_budget_total": 25000,
        "per_object_cap": 5000,
        "unity_axis": "+X", "blender_axis": "X",
        "motion": "rotate", "amplitude_deg": 35.0, "offset_deg": -35.0,
        "unity_range_deg": (-70.0, 0.0), "blender_range_deg": (0.0, 70.0),
        "detents": 6,
        "grip_centre_from_pivot_m": 0.225,
        "grip_interaction_size": (0.16, 0.075, 0.085),
        "existing_max_measured": (0.24, 0.34, 0.12),
    },
    "PowerSlider": {
        "kind": "PowerSlider",
        "pivot": "slider_travel", "moving": "slider_handle",
        "envelope_unity_xyz": (0.17, 0.34, 0.195),
        "renderer_budget": 3, "triangle_budget_total": 25000,
        "per_object_cap": 5000,
        "unity_axis": "+Y", "blender_axis": "Z",
        "motion": "translate", "travel_total_m": 0.18,
        "travel_half_m": 0.09,
        "unity_range_m": (-0.09, 0.09), "blender_range_m": (-0.09, 0.09),
        "detents": 11,
        "travel_origin_blender_z": 0.0,
        "existing_max_measured": (0.168, 0.34, 0.194),
    },
}

SHUT = p1.SHUT_LINE
EMBED = p3.EMBED
EMBED_SKIRT = p3.EMBED_SKIRT
EMBED_INDEX = p3.EMBED_INDEX


def envelope_blender(asset):
    """Unity (x, y, z) -> Blender (width X, depth Y, height Z)."""
    x, y, z = CONTRACT[asset]["envelope_unity_xyz"]
    return x, z, y


# ---------------------------------------------------------------------------
# Round meters: designed per size, not scaled
# ---------------------------------------------------------------------------

# Ratios, not multipliers. As the instrument grows the readable face should
# take more of the bezel and the body should get relatively thinner - a large
# wall gauge is a disc, not a drum. The pilot's MeterRound sat at
# dial/outer 0.685 and depth/outer 0.286; those are the small end of the
# family, and the two production sizes move away from them in both directions.
METER_DESIGN = {
    "MeterMedium": {
        "outer_r": 0.1780, "lip_r": 0.1505, "dial_r": 0.1380,
        "depth": 0.0862, "segments": 40,
        "marks": 33, "major_every": 2,
        "needle_tip_r": 0.1218, "needle_half_u": 0.0068, "needle_half_v": 0.0044,
        "tick_major_w": 0.0052, "tick_minor_w": 0.0034,
        "tick_len_major": 0.0210, "tick_len_minor": 0.0132,
        "boss_r": 0.0182, "collar_r": 0.0260,
    },
    "MeterLarge": {
        "outer_r": 0.2720, "lip_r": 0.2330, "dial_r": 0.2150,
        "depth": 0.1096, "segments": 48,
        "marks": 41, "major_every": 2,
        "needle_tip_r": 0.1910, "needle_half_u": 0.0092, "needle_half_v": 0.0058,
        "tick_major_w": 0.0072, "tick_minor_w": 0.0046,
        "tick_len_major": 0.0300, "tick_len_minor": 0.0186,
        "boss_r": 0.0252, "collar_r": 0.0360,
    },
}
METER_SWEEP_DEG = 230.0          # the -115..+115 the runtime drives


def tick_land_check(parts, land_front, tick_base, scale_inner, marks,
                    sweep_deg, widths):
    """The Gate C question, asked directly for this housing.

    p3.tick_plane_audit looks for a part called `scale_land`; the pilot had
    one, this housing revolves the land as part of the shell, so that audit
    finds nothing and returns nulls. The same property is measured here from
    the design values and from the mesh: no tick face may share the land's
    plane, and no two marks may overlap each other.

    Neighbouring marks trip p3's coplanar audit because it tests axis-aligned
    XZ boxes and radial spokes near vertical have overlapping boxes without
    touching. The angular test below is the exact one: two spokes are clear if
    their angular separation at the inner radius exceeds their half-widths.
    """
    ticks = [obj for obj in parts if obj.name.split(".")[0].startswith("tick_")]
    land_gaps = []
    for obj in ticks:
        for value in {round(v.co.y, 6) for v in obj.data.vertices}:
            land_gaps.append(abs(value - land_front))
    step_rad = math.radians(sweep_deg / (marks - 1))
    arc = step_rad * scale_inner
    widest = max(widths)
    return {
        "land_front_m": round(land_front, 6),
        "tick_base_m": round(tick_base, 6),
        "tick_base_behind_land_mm": round((tick_base - land_front) * 1000.0, 3),
        "marks": len(ticks),
        "min_tick_face_to_land_gap_mm": round(min(land_gaps) * 1000.0, 3)
        if land_gaps else None,
        "any_tick_coplanar_with_land": bool(
            land_gaps and min(land_gaps) < 1e-5),
        "neighbour_arc_at_inner_radius_mm": round(arc * 1000.0, 3),
        "widest_mark_mm": round(widest * 1000.0, 3),
        "neighbours_clear": arc > widest,
        "neighbour_margin_mm": round((arc - widest) * 1000.0, 3),
        "note": ("p3's coplanar pairs between adjacent ticks are axis-aligned "
                 "box overlaps between radial spokes, not real contacts; the "
                 "angular margin above is the exact test"),
    }


def build_round_meter(asset, material):
    """One lathed housing, sunk ticks, and a needle on an absolute depth ladder.

    Two pilot lessons are structural here. The housing is a single revolve so
    there are no coincident internal rims (alignment 290 flicker), and every
    tick base is sunk *into* the scale land rather than sharing its plane. The
    needle's depth is written as world Y values measured against the dial and
    the bearing collar, because P4's needle was lost behind the dial by an
    offset whose sign was wrong.
    """
    design = METER_DESIGN[asset]
    width, depth_env, height = envelope_blender(asset)
    depth = design["depth"]
    outer = design["outer_r"]
    lip = design["lip_r"]
    dial_r = design["dial_r"]

    dial_face = -(depth - 0.0300 if asset == "MeterLarge" else depth - 0.0240)
    land_front = dial_face - 0.0013
    tick_base = dial_face - 0.0006          # sunk 0.7 mm behind the land face
    scale_outer = dial_r - 0.0075
    scale_inner = scale_outer - design["tick_len_major"]
    minor_inner = scale_outer - design["tick_len_minor"]

    parts = []
    # Housing: rear register, drafted body, bezel lip, dial pan - one revolve.
    parts.append(lathe(f"{asset}_housing", [
        (0.0000, 0.0000),
        (outer * 0.86, 0.0000),
        (outer, -0.0130),
        (outer * 0.985, -depth * 0.62),
        (lip, -depth + 0.0090),
        (lip, -depth),
        (dial_r + 0.0065, -depth),
        (dial_r, -depth + 0.0075),
        (dial_r, land_front),
        (0.0000, land_front),
    ], segments=design["segments"], axis="y", centre=(0.0, 0.0), smooth=False))
    # Dial pan sits behind the land so the land is the only face at its plane.
    parts.append(lathe(f"{asset}_dial", [
        (0.0000, dial_face + 0.0034),
        (dial_r - 0.0022, dial_face + 0.0034),
        (dial_r - 0.0022, dial_face),
        (0.0000, dial_face),
    ], segments=design["segments"], axis="y", centre=(0.0, 0.0), smooth=False))

    marks = design["marks"]
    for index in range(marks):
        angle = -25.0 + METER_SWEEP_DEG * index / (marks - 1)
        major = index % design["major_every"] == 0
        parts.append(p1.radial_tick(
            f"tick_{index}", angle,
            scale_inner if major else minor_inner, scale_outer,
            design["tick_major_w"] if major else design["tick_minor_w"],
            tick_base,
            land_front - (0.0016 if major else 0.0012)))

    for sign in (-1.0, 1.0):
        angle = math.radians(90.0 + sign * 115.0)
        seat = scale_inner - design["tick_len_minor"] * 0.55
        parts.append(p1.chamfer(p1.frustum_cyl(
            f"index_{int(sign)}", dial_face + EMBED_INDEX, dial_face - 0.0022,
            design["tick_minor_w"] * 0.95, design["tick_minor_w"] * 0.78,
            segments=10,
            centre=(seat * math.cos(angle), seat * math.sin(angle))), 0.0005))

    # Bearing collar the needle boss runs in.
    collar_r = design["collar_r"]
    parts.append(lathe("collar", [
        (0.0000, dial_face + 0.0008),
        (collar_r, dial_face + 0.0008),
        (collar_r * 0.96, land_front - 0.0020),
        (collar_r * 0.66, land_front - 0.0048),
        (0.0000, land_front - 0.0048),
    ], segments=max(24, design["segments"] // 2), smooth=False))

    # Housing service features, sized to the instrument rather than copied.
    # The seat p1.fastener sinks behind its head scales with the head, and at
    # meter sizes that put the seat through the mount plane (+1.2 mm on the
    # medium, +2.2 mm on the large). The screws move onto the outer flange
    # band, where the head is still read from the front and the seat has
    # material behind it.
    ring = outer * 0.93
    for index in range(6):
        angle = math.radians(30.0 + 60.0 * index)
        parts.append(p1.fastener(
            f"screw_{index}",
            (ring * math.cos(angle), ring * math.sin(angle)),
            -0.0100, outer * 0.046, outer * 0.034))
    parts.append(p1.register_step("register", (outer * 1.52, outer * 1.52),
                                  -EMBED, -0.0034, outer * 0.09))
    parts.append(p1.cable_gland("gland", (0.0, -outer + outer * 0.16),
                                -depth * 0.16, outer * 0.058, outer * 0.13))
    parts.append(p1.blanking_plug("plug", (outer - outer * 0.115, 0.0),
                                  -depth * 0.14, outer * 0.048, outer * 0.023))
    parts.append(p1.nameplate("plate_label",
                              (0.0, -(scale_inner - design["tick_len_major"])),
                              (dial_r * 0.52, dial_r * 0.14),
                              dial_face - 0.0010, 0.0016))

    audit = p3.coplanar_overlap_audit(parts)
    audit["tick_planes"] = tick_land_check(
        parts, land_front, tick_base, scale_inner, marks, METER_SWEEP_DEG,
        (design["tick_major_w"], design["tick_minor_w"]))
    global STATIC_PARTS
    STATIC_PARTS = snapshot_statics(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = f"{asset}_body"
    body.data.name = f"{asset}_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("needle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, dial_face, 0.0)
    pivot.rotation_mode = "XYZ"

    # Absolute depth ladder, front is -Y. The blade sits in front of the dial
    # and in front of the collar; the boss covers the joint.
    collar_front = land_front - 0.0048
    blade_centre = collar_front - 0.0062
    boss_back = collar_front - 0.0022
    boss_front = boss_back - (0.0090 if asset == "MeterMedium" else 0.0120)
    local = blade_centre - pivot.location[1]
    blade = loft(
        "needle_blade",
        (0.0, 0.0, -design["needle_tip_r"] * 0.16),
        (0.0, 0.0, design["needle_tip_r"]),
        lambda s, d=design: d["needle_half_u"] * p3.rounded(s, 3.4)
        * (1.0 - 0.45 * s) + 0.0005,
        lambda s, d=design: d["needle_half_v"] * p3.rounded(s, 3.0)
        * (1.0 - 0.30 * s) + 0.0004,
        offset_v=lambda s, o=-local: o,
        rows=20, segments=16)
    b0 = boss_back - pivot.location[1]
    b1 = boss_front - pivot.location[1]
    boss = lathe("needle_boss", [
        (0.0000, b0),
        (design["boss_r"], b0),
        (design["boss_r"] * 0.98, b0 + (b1 - b0) * 0.36),
        (design["boss_r"] * 0.82, b0 + (b1 - b0) * 0.74),
        (design["boss_r"] * 0.44, b0 + (b1 - b0) * 0.93),
        (0.0000, b1),
    ], segments=max(20, design["segments"] // 2), axis="y", smooth=False)
    needle = p1.join(blade, [boss])
    needle.name = "needle"
    needle.data.name = "needle"
    p1.assign(needle, material)
    needle.parent = pivot

    audit["needle_depth"] = {
        "dial_face_m": round(dial_face, 5),
        "land_front_m": round(land_front, 5),
        "collar_front_m": round(collar_front, 5),
        "blade_centre_m": round(blade_centre, 5),
        "boss_m": [round(boss_back, 5), round(boss_front, 5)],
        "blade_in_front_of_dial": blade_centre < dial_face,
        "blade_clear_of_collar_mm": round((collar_front - blade_centre)
                                          * 1000.0, 3),
        "front_of_body_m": round(-depth, 5),
        "blade_inside_body": boss_front > -depth,
    }
    audit["design"] = {
        "outer_diameter_m": round(outer * 2.0, 4),
        "depth_m": depth,
        "dial_to_outer_ratio": round(dial_r / outer, 4),
        "depth_to_outer_ratio": round(depth / (outer * 2.0), 4),
        "pilot_dial_to_outer_ratio": 0.685,
        "pilot_depth_to_outer_ratio": 0.286,
        "marks": marks,
        "major_marks": len(range(0, marks, design["major_every"])),
        "sweep_deg": METER_SWEEP_DEG,
        "housing_segments": design["segments"],
        "not_uniform_scale": True,
    }
    return body, pivot, needle, audit


# ---------------------------------------------------------------------------
# Throttle: 70 degrees through a quadrant slot
# ---------------------------------------------------------------------------

THROTTLE_PIVOT = (0.0, -0.0340, -0.1080)
THROTTLE_ARM = 0.2250            # ThrottleGripCenterFromPivot magnitude
THROTTLE_RIM_PROUD = 0.0030
THROTTLE_PIN_RADIUS = 0.0300
THROTTLE_PIN_R = 0.0060
THROTTLE_PIN_HALF_X = 0.0200
THROTTLE_BOSS_R = 0.0100


GRIP_ROWS = 26


def plain_stops(rows=GRIP_ROWS):
    """capsule_loft's default cosine row spacing, stated explicitly."""
    return [0.5 - 0.5 * math.cos(math.pi * i / rows) for i in range(rows + 1)]


STATIC_PARTS = {}


def translated_footprint(obj, axis, span, slab_lo, slab_hi, steps=128):
    """The opening a *sliding* part needs, by the same triangle clip.

    The rotation version was what P5 needed; a slider poses by translation, so
    the clip runs over positions instead of angles. Vertices would under-report
    here for exactly the reason they did there.
    """
    import numpy as np
    mesh = obj.data
    mesh.calc_loop_triangles()
    coords = np.array([tuple(v.co) for v in mesh.vertices], dtype=float)
    index = np.array([tuple(t.vertices) for t in mesh.loop_triangles], dtype=int)
    tri = coords[index]
    ax = np.array(axis, dtype=float)
    zmin = zmax = None
    xmax = 0.0
    for step in range(steps + 1):
        offset = span[0] + (span[1] - span[0]) * step / steps
        moved = tri + ax * offset
        wy, wz, wx = moved[..., 1], moved[..., 2], moved[..., 0]
        live = ~((wy.max(axis=1) < slab_lo) | (wy.min(axis=1) > slab_hi))
        if not live.any():
            continue
        ay, az, axx = wy[live], wz[live], wx[live]
        zs, xs = [], []
        inside = (ay >= slab_lo) & (ay <= slab_hi)
        if inside.any():
            zs.append(az[inside]); xs.append(np.abs(axx[inside]))
        for i, j in ((0, 1), (1, 2), (2, 0)):
            yi, yj = ay[:, i], ay[:, j]
            for plane in (slab_lo, slab_hi):
                di, dj = yi - plane, yj - plane
                cross = (di * dj) < 0.0
                if not cross.any():
                    continue
                t = di[cross] / (di[cross] - dj[cross])
                zs.append(az[cross, i] + t * (az[cross, j] - az[cross, i]))
                xs.append(np.abs(axx[cross, i]
                                 + t * (axx[cross, j] - axx[cross, i])))
        if not zs:
            continue
        allz = np.concatenate(zs)
        zmin = allz.min() if zmin is None else min(zmin, allz.min())
        zmax = allz.max() if zmax is None else max(zmax, allz.max())
        xmax = max(xmax, float(np.concatenate(xs).max()))
    if zmin is None:
        return None
    return {"z_min": float(zmin), "z_max": float(zmax), "x_max": float(xmax),
            "slab": (slab_lo, slab_hi), "positions": steps + 1,
            "method": "triangle clipped against the slab planes, per position"}


# Statics whose intersection with the moving assembly is a defect. The gasket,
# skirt and plate form the slab behind the shell face that hubs and shoes are
# designed to run inside, so they are reported but not gated - the same
# distinction alignment 292 settled for the pilot.
GATED_PREFIXES = ("shell", "slot_floor", "rim_", "stop_", "end_stop",
                  "rail", "cam_plate", "detent_", "pillow_")


def motion_clearance_audit(mover, moving, asset, steps=128, sample=3):
    """Triangle overlap first, then vertex-to-surface distance, per pose.

    Rotation and translation are both driven from the runtime contract rather
    than from a convenient guess: the throttle walks its real 0..70 degrees and
    the slider its real +-0.09 m, over more poses than alignment 295.2 asks
    for, because the cheapest way to miss a collision is to sample its ends.
    """
    row = CONTRACT[asset]
    gate_all = asset.startswith("Meter")
    trees = {name: BVHTree.FromPolygons(verts, faces, all_triangles=True)
             for name, (verts, faces) in STATIC_PARTS.items()
             if gate_all or name.startswith(GATED_PREFIXES)}
    rotate = row["motion"] == "rotate"
    if rotate:
        low, high = row["blender_range_deg"]
        axis_index = "XYZ".index(row["blender_axis"])
    else:
        low, high = row["blender_range_m"]
    original_rot = tuple(mover.rotation_euler)
    original_loc = tuple(mover.location)

    per_part = {}
    intersections = []
    worst_clearance = None
    worst_pose = None
    for step in range(steps + 1):
        value = low + (high - low) * step / steps
        if rotate:
            euler = list(original_rot)
            euler[axis_index] = math.radians(value)
            mover.rotation_euler = euler
        else:
            mover.location = (original_loc[0], original_loc[1],
                              original_loc[2] + value)
        bpy.context.view_layer.update()
        matrix = moving.matrix_world
        mesh = moving.data
        mesh.calc_loop_triangles()
        verts = [matrix @ v.co for v in mesh.vertices]
        faces = [tuple(t.vertices) for t in mesh.loop_triangles]
        bvh = BVHTree.FromPolygons(verts, faces, all_triangles=True)
        pose_min = None
        for name, tree in trees.items():
            entry = per_part.setdefault(
                name, {"intersecting_poses": 0, "worst_triangle_pairs": 0,
                       "min_clearance_mm": None, "at_pose": None})
            pairs = bvh.overlap(tree)
            if pairs:
                entry["intersecting_poses"] += 1
                entry["worst_triangle_pairs"] = max(
                    entry["worst_triangle_pairs"], len(pairs))
                entry["min_clearance_mm"] = 0.0
                entry["at_pose"] = round(value, 4)
                intersections.append({"pose": round(value, 4), "static": name,
                                      "triangle_pairs": len(pairs)})
                pose_min = 0.0
                continue
            nearest = None
            for point in verts[::sample]:
                hit = tree.find_nearest(point)
                if hit[0] is None:
                    continue
                distance = (hit[0] - point).length
                nearest = distance if nearest is None else min(nearest, distance)
            if nearest is None:
                continue
            millimetres = round(nearest * 1000.0, 3)
            if (entry["min_clearance_mm"] is None
                    or millimetres < entry["min_clearance_mm"]):
                entry["min_clearance_mm"] = millimetres
                entry["at_pose"] = round(value, 4)
            pose_min = millimetres if pose_min is None else min(pose_min,
                                                               millimetres)
        if pose_min is not None and (worst_clearance is None
                                     or pose_min < worst_clearance):
            worst_clearance = pose_min
            worst_pose = round(value, 4)
    mover.rotation_euler = original_rot
    mover.location = original_loc
    bpy.context.view_layer.update()
    return {
        "motion": row["motion"],
        "range": list(row["blender_range_deg"] if rotate
                      else row["blender_range_m"]),
        "unit": "deg" if rotate else "m",
        "poses": steps + 1,
        "gated_statics": sorted(trees),
        "ungated_note": ("meters gate every static - the needle should clear "
                         "all of them. Controls exclude plate, gasket and "
                         "skirt, the slab behind the shell face the moving "
                         "assembly is designed to run inside"),
        "gate_scope": "all statics" if gate_all else "housing shell family",
        "vertex_sample_stride": sample,
        "per_static": per_part,
        "intersections": intersections,
        "intersection_count": len(intersections),
        "min_clearance_mm": worst_clearance,
        "worst_pose": worst_pose,
        "clean": not intersections,
        "method": ("BVH triangle overlap per pose; where none, "
                   "vertex-to-surface nearest distance from the moving mesh"),
    }


def snapshot_statics(parts):
    """World-space triangles per static part, captured before the join."""
    rows = {}
    for obj in parts:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world.copy()
        rows[obj.name.split(".")[0]] = (
            [matrix @ v.co for v in mesh.vertices],
            [tuple(t.vertices) for t in mesh.loop_triangles])
    return rows


def pin_sweep_generic(pivot_loc, local_yz, angles, radius, steps=96):
    """World Y and Z a point at `local_yz` sweeps about the pivot's X axis."""
    py, pz = pivot_loc[1], pivot_loc[2]
    low, high = min(angles), max(angles)
    ys, zs = [], []
    for index in range(steps + 1):
        a = math.radians(low + (high - low) * index / steps)
        ca, sa = math.cos(a), math.sin(a)
        ys.append(py + local_yz[0] * ca - local_yz[1] * sa)
        zs.append(pz + local_yz[0] * sa + local_yz[1] * ca)
    return {"y": (min(ys) - radius, max(ys) + radius),
            "z": (min(zs) - radius, max(zs) + radius)}


def _pin_local(radius, phase_deg):
    a = math.radians(phase_deg)
    return (-radius * math.cos(a), radius * math.sin(a))


def build_throttle(material):
    """A 70 degree quadrant lever with the working point on the yoke.

    Every structural decision here is a pilot finding applied at a new size.
    The opening is measured against the rims' front plane with a triangle
    clip, not against the shell face with vertices, because that is what let
    P4's arm cut its own rim. The cross pin sits at the middle of the travel
    so it stays in front of the face at both ends, and it runs through both
    yoke cheeks with a raised boss on each - the pilot's cure for a floating
    working point. End stops and the bearing are geometry, not implied.
    """
    width, depth_env, height = envelope_blender("Throttle")
    depth = 0.1300
    plate_y = -0.0180
    shell_y = -0.0440
    shell = (width - 0.020, height - 0.014)
    shell_centre_z = 0.0
    pivot_y, pivot_z = THROTTLE_PIVOT[1], THROTTLE_PIVOT[2]
    angles = (0.0, 70.0)
    mid = 0.5 * (angles[0] + angles[1])
    pin_local = _pin_local(THROTTLE_PIN_RADIUS, mid)

    pivot = bpy.data.objects.new("throttle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = THROTTLE_PIVOT
    pivot.rotation_mode = "XYZ"

    hub = lathe("handle_hub", [
        (0.0000, 0.0195),
        (0.0155, 0.0184),
        (0.0170, 0.0084),
        (0.0170, -0.0084),
        (0.0155, -0.0184),
        (0.0000, -0.0195),
    ], segments=26, axis="x", centre=(0.0, 0.0), smooth=False)
    cheeks = []
    for sign in (-1.0, 1.0):
        cheeks.append(p1.chamfer(p1.frustum_box(
            f"handle_yoke_{int(sign)}", 0.0055, -0.0360, (0.0072, 0.0480),
            (0.0062, 0.0425), centre=(sign * 0.0150, 0.0125)), 0.0010))
    pin = lathe("handle_pin", [
        (0.0000, THROTTLE_PIN_HALF_X),
        (0.0040, THROTTLE_PIN_HALF_X - 0.0006),
        (THROTTLE_PIN_R, THROTTLE_PIN_HALF_X - 0.0019),
        (THROTTLE_PIN_R, -(THROTTLE_PIN_HALF_X - 0.0019)),
        (0.0040, -(THROTTLE_PIN_HALF_X - 0.0006)),
        (0.0000, -THROTTLE_PIN_HALF_X),
    ], segments=18, axis="x", centre=pin_local, smooth=False)
    bosses = []
    for sign in (-1.0, 1.0):
        boss = lathe(f"handle_pin_boss_{int(sign)}", [
            (0.0000, 0.0042),
            (0.0072, 0.0039),
            (THROTTLE_BOSS_R, 0.0025),
            (THROTTLE_BOSS_R, -0.0031),
            (0.0058, -0.0042),
            (0.0000, -0.0042),
        ], segments=18, axis="x", centre=pin_local, smooth=False)
        boss.location = (sign * 0.0168, 0.0, 0.0)
        bosses.append(boss)

    # Arm and grip. The section is asymmetric - deeper on the palm side - and
    # there is exactly one finger hollow, at 0.62 along the arm, so the hand
    # finds the same place every time without a row of ridges to catch on.
    arm_a = (0.0, -0.0040, 0.0090)
    arm_b = (0.0, -0.0640, THROTTLE_ARM + 0.0180)
    arm_u = stations([(0.00, 0.0195), (0.18, 0.0150), (0.46, 0.0116),
                      (0.62, 0.0128), (0.80, 0.0186), (0.92, 0.0192),
                      (1.00, 0.0152)])
    arm_v = stations([(0.00, 0.0165), (0.18, 0.0132), (0.46, 0.0106),
                      (0.62, 0.0122), (0.80, 0.0214), (0.92, 0.0220),
                      (1.00, 0.0168)])

    def swell(s):
        finger = -0.0026 * math.exp(-(((s - 0.62) / 0.055) ** 2))
        palm = 0.0032 * math.exp(-(((s - 0.84) / 0.18) ** 2))
        return finger + palm

    grip = loft("handle_grip", arm_a, arm_b, arm_u, arm_v,
                offset_v=swell, segments=32, stops=plain_stops())
    handle = p1.join(hub, cheeks + [pin] + bosses + [grip])
    handle.name = "throttle_handle"
    handle.data.name = "throttle_handle"
    p1.assign(handle, material)

    face_slab = (shell_y - THROTTLE_RIM_PROUD, plate_y - SHUT)
    floor_slab = (pivot_y, pivot_y + 0.004)
    need_face = p5.swept_footprint_solid(handle, THROTTLE_PIVOT,
                                         face_slab[0], face_slab[1], angles)
    need_floor = p5.swept_footprint_solid(handle, THROTTLE_PIVOT,
                                          floor_slab[0], floor_slab[1], angles)
    pin_span = pin_sweep_generic(THROTTLE_PIVOT, pin_local, angles,
                                    THROTTLE_BOSS_R)
    margin = 0.0032
    slot_lo = min(need_face["z_min"], pin_span["z"][0]) - margin
    slot_hi = max(need_face["z_max"], pin_span["z"][1]) + margin
    slot = (max(0.062, 2.0 * (need_face["x_max"] + margin)), slot_hi - slot_lo)
    slot_centre_z = 0.5 * (slot_lo + slot_hi)

    parts = []
    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.012, height - 0.012)), 0.0016))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.032, height - 0.040),
                                (width - 0.032, height - 0.040),
                                centre=(0.0, shell_centre_z)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, shell_y, shell, slot,
        centre=(0.0, shell_centre_z),
        inner_centre=(0.0, slot_centre_z)), 0.0020))
    parts.append(p1.chamfer(p1.frustum_box(
        "skirt", plate_y + EMBED_SKIRT, plate_y - 0.0090,
        (shell[0] + 0.014, shell[1] + 0.014),
        (shell[0] + 0.004, shell[1] + 0.004),
        centre=(0.0, shell_centre_z)), 0.0016))
    floor_lo = need_floor["z_min"] - 0.0070
    floor_hi = need_floor["z_max"] + 0.0070
    parts.append(p1.rect_frame(
        "slot_floor", pivot_y + 0.0040, pivot_y,
        (slot[0] + 0.024, slot[1] + 0.024),
        (2.0 * (need_floor["x_max"] + 0.0070), floor_hi - floor_lo),
        centre=(0.0, slot_centre_z),
        inner_centre=(0.0, 0.5 * (floor_lo + floor_hi))))

    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"pillow_{int(sign)}", pivot_y + 0.0055, pivot_y - 0.0185,
            (0.0185, 0.0370), (0.0155, 0.0315),
            centre=(sign * 0.0330, pivot_z)), 0.0011))
        cap = lathe(f"pillow_cap_{int(sign)}", [
            (0.0068, 0.0058),
            (0.0092, 0.0058),
            (0.0104, 0.0038),
            (0.0104, -0.0038),
            (0.0092, -0.0058),
            (0.0068, -0.0058),
        ], segments=20, axis="x",
            centre=(pivot_y - 0.0035, pivot_z), smooth=False)
        cap.location = (sign * 0.0330, 0.0, 0.0)
        parts.append(cap)

    for name, cx, sx, cz, sz in (
        ("rim_left", -(slot[0] / 2.0 + 0.0042), 0.0084, slot_centre_z,
         slot[1] + 0.0168),
        ("rim_right", (slot[0] / 2.0 + 0.0042), 0.0084, slot_centre_z,
         slot[1] + 0.0168),
        ("rim_top", 0.0, slot[0], slot_hi + 0.0042, 0.0084),
        ("rim_bottom", 0.0, slot[0], slot_lo - 0.0042, 0.0084),
    ):
        parts.append(p1.chamfer(p1.frustum_box(
            name, shell_y + EMBED, shell_y - THROTTLE_RIM_PROUD, (sx, sz),
            (sx - 0.0013, sz - 0.0013), centre=(cx, cz)), 0.0008))

    # End stops. A pad proud of the face cannot work at the 0 degree end: the
    # arm sweeps over the whole quadrant there, so anything standing off the
    # face gets cut. Both stops sit at slot-floor depth instead. The 70 degree
    # end is clear of every moving part, so it takes one full-width abutment;
    # the 0 degree end is under the arm, so it takes two outboard blocks that
    # the pin boss shoulders meet, clear of the arm's width.
    stop_span = pin_sweep_generic(THROTTLE_PIVOT, pin_local, angles,
                                  THROTTLE_BOSS_R)
    stop_slab = p5.swept_footprint_solid(
        handle, THROTTLE_PIVOT, pivot_y - 0.0110, pivot_y + 0.0040, angles)
    stop_low_z = (stop_slab["z_min"] if stop_slab else stop_span["z"][0]) - 0.0110
    parts.append(p1.chamfer(p1.frustum_box(
        "stop_low", pivot_y + 0.0040, pivot_y - 0.0110,
        (0.0400, 0.0110), (0.0355, 0.0092),
        centre=(0.0, stop_low_z)), 0.0014))
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"stop_high_{int(sign)}", pivot_y + 0.0040, pivot_y - 0.0110,
            (0.0100, 0.0130), (0.0088, 0.0108),
            centre=(sign * 0.0280, stop_span["z"][1] + 0.0110)), 0.0012))

    # Detent scale, one mark per runtime detent.
    count = CONTRACT["Throttle"]["detents"]
    for index in range(count):
        deg = angles[0] + (angles[1] - angles[0]) * index / (count - 1)
        a = math.radians(deg)
        mark = pivot_z + pin_local[0] * math.sin(a) + pin_local[1] * math.cos(a)
        parts.append(p1.chamfer(p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0018,
            (0.0150, 0.0034), (0.0132, 0.0030),
            centre=(slot[0] / 2.0 + 0.0180, mark)), 0.0006))

    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.0140), sz * (height / 2.0 - 0.0140)),
                plate_y - 0.0006, 0.0060, 0.0044))
    parts.append(p1.access_cap("access", (-0.0740, 0.1180), shell_y + EMBED,
                               0.0125, 0.0106, 0.0044))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0030, 0.0120))
    parts.append(p1.cover_panel("cover", (0.0700, 0.1180), (0.0440, 0.0620),
                                shell_y + EMBED, 0.0030, 0.0044))
    parts.append(p1.cable_gland("gland", (0.0, -0.1480), shell_y - 0.0018,
                                0.0095, 0.0230))
    parts.append(p1.nameplate("plate_label", (0.0, -0.1000), (0.0560, 0.0180),
                              shell_y + EMBED, 0.0018))
    for sign in (-1.0, 1.0):
        parts.append(p1.mount_hole(f"mount_{int(sign)}",
                                   (sign * 0.0880, -0.1420), plate_y - 0.0004,
                                   0.0078, 0.0046, 0.0034))
    parts.append(p1.blanking_plug("blank", (-0.0880, 0.1420), plate_y - 0.0006,
                                  0.0074, 0.0034))

    audit = p3.coplanar_overlap_audit(parts)
    global STATIC_PARTS
    STATIC_PARTS = snapshot_statics(parts)
    audit["slot"] = {
        "face_slab_m": list(face_slab),
        "required_z_m": [need_face["z_min"], need_face["z_max"]],
        "pin_span_z_m": list(pin_span["z"]),
        "slot_z_m": [slot_lo, slot_hi],
        "slot_size_m": list(slot),
        "margin_m": margin,
        "footprint_method": need_face["method"],
        "range_deg": list(angles),
    }
    audit["working_point"] = {
        "part": "handle_pin",
        "carried_by": ["handle_yoke_-1", "handle_yoke_1"],
        "support_parts": ["handle_pin_boss_-1", "handle_pin_boss_1"],
        "local_yz": [round(v, 6) for v in pin_local],
        "radius_m": THROTTLE_PIN_RADIUS,
        "phase_deg": mid,
        "proud_of_cheek_mm": round((THROTTLE_PIN_HALF_X - 0.0186) * 1000.0, 2),
        "cheek_contains_pin": (-0.0360 < pin_local[0] - THROTTLE_PIN_R
                               and pin_local[0] + THROTTLE_PIN_R < 0.0055),
        "floating_gap_mm": 0.0,
    }
    body = p1.join(parts[0], parts[1:])
    body.name = "Throttle_body"
    body.data.name = "Throttle_body"
    p1.assign(body, material)
    handle.parent = pivot
    return body, pivot, handle, audit


# ---------------------------------------------------------------------------
# PowerSlider: 0.18 m of vertical travel on a real rail
# ---------------------------------------------------------------------------

SLIDER_TRAVEL_HALF = 0.0900
SLIDER_RIM_PROUD = 0.0028
SLIDER_RAIL_R = 0.0075


def build_power_slider(material):
    """A shoe that wraps a rail, not a knob floating over a groove.

    `slider_travel` sits at Blender z = 0 in all three existing themes, which
    is what makes the runtime's symmetric +-0.09 m land centred, so it is
    treated as contract and the geometry is built around it. The moving
    assembly is a shoe with two rail jaws, a bearing pad and the grip; the
    static side is a rail with end stops the shoe runs onto. The slot is sized
    from the shoe's real travel plus the rims' proud height, by the same
    triangle clip the pilot needed.
    """
    width, depth_env, height = envelope_blender("PowerSlider")
    depth = 0.1500
    plate_y = -0.0170
    shell_y = -0.0430
    rail_y = -0.0620
    shell = (width - 0.022, height - 0.030)
    travel = SLIDER_TRAVEL_HALF

    travel_root = bpy.data.objects.new("slider_travel", None)
    bpy.context.collection.objects.link(travel_root)
    travel_root.location = (0.0, 0.0, 0.0)
    travel_root.rotation_mode = "XYZ"

    # Moving shoe. `lathe` with axis="z" takes centre as (x, y) and the
    # profile's t as the Z coordinate; P6's first build passed the rail's Y
    # into t and left the centre at the origin, which put the bearing on the
    # mount plane and made it intersect the rail at every position. The shoe
    # is a C around the rail: a bored bearing ring on the rail, two cross pins
    # out to the jaws, the jaws reaching back past the rail on both sides, and
    # the body and grip entirely in front of it. Nothing but the bore is near
    # the rail, and the bore never touches it.
    shoe = []
    shoe.append(lathe("slider_bearing", [
        (0.0092, 0.0100),
        (0.0132, 0.0100),
        (0.0150, 0.0064),
        (0.0150, -0.0064),
        (0.0132, -0.0100),
        (0.0092, -0.0100),
    ], segments=22, axis="z", centre=(0.0, rail_y), smooth=False))
    for sign in (-1.0, 1.0):
        shoe.append(lathe(f"slider_pin_{int(sign)}", [
            (0.0000, sign * 0.0140),
            (0.0028, sign * 0.0146),
            (0.0040, sign * 0.0158),
            (0.0040, sign * 0.0248),
            (0.0028, sign * 0.0258),
            (0.0000, sign * 0.0262),
        ], segments=14, axis="x", centre=(rail_y, 0.0), smooth=False))
        shoe.append(p1.chamfer(p1.frustum_box(
            f"slider_jaw_{int(sign)}", rail_y + 0.0090, rail_y - 0.0200,
            (0.0100, 0.0330), (0.0090, 0.0295),
            centre=(sign * 0.0250, 0.0)), 0.0014))
    shoe.append(p1.chamfer(p1.frustum_box(
        "slider_body", rail_y - 0.0200, rail_y - 0.0330,
        (0.0620, 0.0430), (0.0560, 0.0380),
        centre=(0.0, 0.0)), 0.0022))

    # Grip: asymmetric, one thumb hollow on the front face, no ridge rows.
    grip = loft("slider_grip",
                (0.0, rail_y - 0.0300, -0.0245),
                (0.0, rail_y - 0.0500, 0.0245),
                stations([(0.00, 0.0230), (0.30, 0.0262), (0.62, 0.0250),
                          (1.00, 0.0206)], tip_from=0.86),
                stations([(0.00, 0.0120), (0.30, 0.0152), (0.62, 0.0146),
                          (1.00, 0.0112)], tip_from=0.86),
                offset_v=lambda s: -0.0030 * math.exp(-(((s - 0.50) / 0.20) ** 2)),
                segments=26, rows=18)
    shoe.append(grip)
    handle = p1.join(shoe[0], shoe[1:])
    handle.name = "slider_handle"
    handle.data.name = "slider_handle"
    p1.assign(handle, material)

    face_slab = (shell_y - SLIDER_RIM_PROUD, plate_y - SHUT)
    need_face = translated_footprint(handle, (0.0, 0.0, 1.0),
                                     (-travel, travel),
                                     face_slab[0], face_slab[1])
    # The shoe rides the rail entirely in front of the shell, so nothing
    # crosses the face slab and the clip returns nothing. The opening is not
    # therefore unnecessary: without it the rail and its posts would stand on
    # a flat panel and the track would not read as a track. It is sized to
    # frame the shoe's whole travel instead, the same way the pilot sized the
    # lever slot to frame a pin that also rode in front of the face.
    coords = [v.co for v in handle.data.vertices]
    swept = {
        "z_min": min(c.z for c in coords) - travel,
        "z_max": max(c.z for c in coords) + travel,
        "x_max": max(abs(c.x) for c in coords),
        "source": "moving assembly local bounds swept over the full travel",
    }
    if need_face is not None:
        swept["z_min"] = min(swept["z_min"], need_face["z_min"])
        swept["z_max"] = max(swept["z_max"], need_face["z_max"])
        swept["x_max"] = max(swept["x_max"], need_face["x_max"])
    margin = 0.0032
    slot_lo = swept["z_min"] - margin
    slot_hi = swept["z_max"] + margin
    slot = (max(0.050, 2.0 * (swept["x_max"] * 0.62 + margin)),
            slot_hi - slot_lo)
    slot_centre_z = 0.5 * (slot_lo + slot_hi)

    parts = []
    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.011, height - 0.011)), 0.0015))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.028, height - 0.036),
                                (width - 0.028, height - 0.036)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, shell_y, shell, slot,
        inner_centre=(0.0, slot_centre_z)), 0.0018))
    parts.append(p1.chamfer(p1.frustum_box(
        "skirt", plate_y + EMBED_SKIRT, plate_y - 0.0085,
        (shell[0] + 0.013, shell[1] + 0.013),
        (shell[0] + 0.004, shell[1] + 0.004)), 0.0015))

    # The rail itself, and the two posts that carry it clear of the shell.
    rail_end = travel + 0.0600
    parts.append(lathe("rail", [
        (0.0000, rail_end),
        (SLIDER_RAIL_R * 0.55, rail_end),
        (SLIDER_RAIL_R, rail_end - 0.0060),
        (SLIDER_RAIL_R, -(rail_end - 0.0060)),
        (SLIDER_RAIL_R * 0.55, -rail_end),
        (0.0000, -rail_end),
    ], segments=18, axis="z", centre=(0.0, rail_y), smooth=False))
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"rail_post_{int(sign)}", shell_y + EMBED, rail_y - 0.0060,
            (0.0300, 0.0210), (0.0250, 0.0180),
            centre=(0.0, sign * (rail_end - 0.0170))), 0.0016))
        # End stop: the collar the shoe runs onto, on the rail itself.
        # Larger in radius than the bearing ring, so the ring is what it
        # stops, and inboard of the jaws in X so the jaws pass it.
        stop = lathe(f"end_stop_{int(sign)}", [
            (SLIDER_RAIL_R, 0.0060),
            (0.0160, 0.0060),
            (0.0175, 0.0038),
            (0.0175, -0.0038),
            (0.0160, -0.0060),
            (SLIDER_RAIL_R, -0.0060),
        ], segments=18, axis="z",
            centre=(0.0, rail_y), smooth=False)
        stop.location = (0.0, 0.0, sign * (travel + 0.0180))
        parts.append(stop)

    for name, cx, sx, cz, sz in (
        ("rim_left", -(slot[0] / 2.0 + 0.0040), 0.0080, slot_centre_z,
         slot[1] + 0.0160),
        ("rim_right", (slot[0] / 2.0 + 0.0040), 0.0080, slot_centre_z,
         slot[1] + 0.0160),
        ("rim_top", 0.0, slot[0], slot_hi + 0.0040, 0.0080),
        ("rim_bottom", 0.0, slot[0], slot_lo - 0.0040, 0.0080),
    ):
        parts.append(p1.chamfer(p1.frustum_box(
            name, shell_y + EMBED, shell_y - SLIDER_RIM_PROUD, (sx, sz),
            (sx - 0.0012, sz - 0.0012), centre=(cx, cz)), 0.0007))

    count = CONTRACT["PowerSlider"]["detents"]
    for index in range(count):
        z = -travel + 2.0 * travel * index / (count - 1)
        major = index % 5 == 0
        parts.append(p1.chamfer(p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0018,
            (0.0150 if major else 0.0100, 0.0032 if major else 0.0024),
            (0.0132 if major else 0.0086, 0.0028 if major else 0.0021),
            centre=(slot[0] / 2.0 + 0.0155, z)), 0.0005))

    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.0125), sz * (height / 2.0 - 0.0135)),
                plate_y - 0.0006, 0.0056, 0.0042))
    parts.append(p1.access_cap("access", (-0.0520, 0.1360), shell_y + EMBED,
                               0.0115, 0.0098, 0.0042))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0028, 0.0110))
    parts.append(p1.cable_gland("gland", (0.0, -0.1560), shell_y - 0.0016,
                                0.0090, 0.0210))
    parts.append(p1.nameplate("plate_label", (-0.0480, -0.1320),
                              (0.0420, 0.0160), shell_y + EMBED, 0.0016))
    for sign in (-1.0, 1.0):
        parts.append(p1.mount_hole(f"mount_{int(sign)}",
                                   (sign * 0.0620, -0.1560), plate_y - 0.0004,
                                   0.0074, 0.0044, 0.0032))
    parts.append(p1.blanking_plug("blank", (0.0540, 0.1360), plate_y - 0.0006,
                                  0.0070, 0.0032))

    audit = p3.coplanar_overlap_audit(parts)
    global STATIC_PARTS
    STATIC_PARTS = snapshot_statics(parts)
    audit["slot"] = {
        "face_slab_m": list(face_slab),
        "crosses_face_slab": need_face is not None,
        "required_z_m": [swept["z_min"], swept["z_max"]],
        "required_half_x_m": swept["x_max"],
        "sizing_source": swept["source"],
        "slot_z_m": [slot_lo, slot_hi],
        "slot_size_m": list(slot),
        "margin_m": margin,
        "travel_half_m": travel,
    }
    audit["working_point"] = {
        "part": "slider_bearing",
        "carried_by": ["slider_body"],
        "support_parts": ["slider_jaw_-1", "slider_jaw_1",
                          "slider_pin_-1", "slider_pin_1"],
        "rail_radius_m": SLIDER_RAIL_R,
        "bearing_bore_radius_m": 0.0150,
        "end_stops": ["end_stop_-1", "end_stop_1"],
        "end_stop_z_m": [-(travel + 0.0180), travel + 0.0180],
        "end_stop_outer_radius_m": 0.0175,
        "bearing_outer_radius_m": 0.0150,
        "rail_to_bore_clearance_mm": round((0.0092 - SLIDER_RAIL_R) * 1000, 2),
        "travel_origin_blender_z": 0.0,
        "floating_gap_mm": 0.0,
    }
    body = p1.join(parts[0], parts[1:])
    body.name = "PowerSlider_body"
    body.data.name = "PowerSlider_body"
    p1.assign(body, material)
    handle.parent = travel_root
    return body, travel_root, handle, audit


BUILDERS_A = {
    "MeterMedium": lambda m: build_round_meter("MeterMedium", m),
    "MeterLarge": lambda m: build_round_meter("MeterLarge", m),
    "Throttle": build_throttle,
    "PowerSlider": build_power_slider,
}


# ---------------------------------------------------------------------------

def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def pose_set(asset):
    """End, middle, end - the three the contract wants a close-up of."""
    row = CONTRACT[asset]
    if row["motion"] == "rotate":
        low, high = row["blender_range_deg"]
    else:
        low, high = row["blender_range_m"]
    return ((low, "low"), (0.5 * (low + high), "mid"), (high, "high"))


def apply_pose(mover, asset, value):
    row = CONTRACT[asset]
    if row["motion"] == "rotate":
        euler = [0.0, 0.0, 0.0]
        euler["XYZ".index(row["blender_axis"])] = math.radians(value)
        mover.rotation_euler = euler
    else:
        mover.location = (0.0, 0.0, value)
    bpy.context.view_layer.update()


def measure_asset(asset, root, body, mover, moving):
    """Envelope, mount plane, triangles and mesh health, from vertices."""
    row = CONTRACT[asset]
    apply_pose(mover, asset, 0.0 if row["motion"] == "translate"
               else (0.0 if asset.startswith("Meter") else 0.0))
    bounds = p1.world_bounds([body, moving])
    size = [round(bounds["max"][i] - bounds["min"][i], 6) for i in range(3)]
    whd = [size[0], size[2], size[1]]
    envelope = envelope_blender(asset)
    limit = [envelope[0], envelope[2], envelope[1]]
    tris = {}
    health = {}
    for obj in (body, moving):
        info = p1.mesh_health(obj)
        tris[obj.name] = info["triangles"]
        health[obj.name] = info
    total = sum(tris.values())
    cap = row["per_object_cap"]
    return {
        "objects": [body.name, mover.name, moving.name],
        "renderers": 2,
        "renderer_budget": row["renderer_budget"],
        "triangles_per_object": tris,
        "triangles_total": total,
        "triangle_budget_total": row["triangle_budget_total"],
        "per_object_cap": cap,
        "non_manifold_edges": sum(h["non_manifold_edges"]
                                  for h in health.values()),
        "zero_area_faces": sum(h["zero_area_faces"] for h in health.values()),
        "measured_width_height_depth": whd,
        "envelope_width_height_depth": list(limit),
        "within_envelope": all(whd[i] <= limit[i] + 1e-6 for i in range(3)),
        "mount_plane_max_y": round(bounds["max"][1], 6),
        "mount_plane_ok": abs(bounds["max"][1]) <= 1e-6,
        "bounds_unity": p1.to_unity(bounds),
        "contract": {
            "pivot": row["pivot"], "moving": row["moving"],
            "unity_axis": row["unity_axis"], "motion": row["motion"],
            "unity_range": list(row.get("unity_range_deg")
                                or row.get("unity_range_m")),
            "blender_range": list(row.get("blender_range_deg")
                                  or row.get("blender_range_m")),
        },
        "gates": {
            "renderers": 2 <= row["renderer_budget"],
            "triangles_total": total <= row["triangle_budget_total"],
            "triangles_per_object": (cap is None
                                     or all(v <= cap for v in tris.values())),
            "non_manifold_zero": all(h["non_manifold_edges"] == 0
                                     for h in health.values()),
            "zero_area_zero": all(h["zero_area_faces"] == 0
                                  for h in health.values()),
            "mount_plane": abs(bounds["max"][1]) <= 1e-6,
            "rest_envelope": all(whd[i] <= limit[i] + 1e-6 for i in range(3)),
        },
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    geometry_dir = tree / "geometry"
    grey_dir = tree / "review_grayscale"
    detail_dir = tree / "detail"
    for folder in (geometry_dir, grey_dir, detail_dir):
        folder.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "Theme4-P6-BatchA-geometry",
        "note": ("Phase 3 Batch A. Contract measured from "
                 "InstrumentGreyboxSpecification, MockInstrumentFactory, "
                 "MockInstrumentMotion and the three existing themes' FBX. "
                 "P1-P5 and the existing themes are untouched."),
        "contract": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv)
                         for kk, vv in v.items()}
                     for k, v in CONTRACT.items()},
        "throttle_range_note": ("70 degrees, from amplitude 35 with offset "
                                "-35 through Lerp(-a, a, v) + offset; "
                                "confirmed against the runtime by Codex"),
        "assets": {},
    }

    import opus5_brushup_kinetic_review as review
    for asset, builder in BUILDERS_A.items():
        p1.clear_scene()
        review.configure_scene()
        material = p1.proto.make_material(f"MAT_{THEME}_P6_Neutral", NEUTRAL)
        root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
        bpy.context.collection.objects.link(root)
        body, mover, moving, audit = builder(material)
        for obj in (body, mover):
            obj.parent = root
        bpy.context.view_layer.update()

        row = measure_asset(asset, root, body, mover, moving)
        row["coplanar_overlap"] = audit
        row["clearance"] = motion_clearance_audit(mover, moving, asset)
        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P6A.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        focus, radius, scale = p1.rig_for([body, moving])
        images = {}
        for label, view in p1.VIEWS.items():
            path = grey_dir / f"Grey_{asset}_{THEME}_P6A_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        row["grayscale_images"] = images

        details = {}
        for value, label in pose_set(asset):
            apply_pose(mover, asset, value)
            near = detail_dir / f"Detail_{asset}_motion_{label}.png"
            p1.shot(focus, radius * 0.52, (44.0, 12.0), 60.0, scale * 0.52,
                    near)
            details[f"motion_{label}"] = str(near.relative_to(project_root))
            wide = detail_dir / f"Detail_{asset}_pose_{label}.png"
            p1.shot(focus, radius, (58.0, 8.0), 52.0, scale, wide)
            details[f"pose_{label}"] = str(wide.relative_to(project_root))
        apply_pose(mover, asset, 0.0)
        row["detail_images"] = details
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        clearance = row["clearance"]
        print(f"[BatchA] {asset}: tris {row['triangles_total']} "
              f"({row['triangles_per_object']}), coplanar "
              f"{audit['pair_count']}, clearance clean "
              f"{clearance['clean'] if clearance else 'n/a'} "
              f"min {clearance['min_clearance_mm'] if clearance else '-'} mm, "
              f"gates {row['all_gates_passed']}")

    payload["coplanar_overlap_pairs_total"] = sum(
        row["coplanar_overlap"]["pair_count"]
        for row in payload["assets"].values())
    payload["status"] = (
        "p6_batch_a_geometry_ready"
        if all(row["all_gates_passed"] for row in payload["assets"].values())
        and all(row["clearance"] is None or row["clearance"]["clean"]
                for row in payload["assets"].values())
        else "p6_batch_a_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchA] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
