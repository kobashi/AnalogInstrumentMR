"""Batch A R2: driver access to the four corner screws on the two controls.

Alignment 301. Quest showed the corner screw heads on Throttle R1 and
PowerSlider buried under the housing: the screws are modelled but a driver
cannot reach them, so the assembly does not hold together as a mechanism.

Measured, the covering parts are `skirt` and `shell`, both of which span the
screw circle. Since nothing in this pipeline uses booleans, the fix is not to
punch the covers but to take them in and stand a tube on each screw axis:

  * `skirt`, `shell` and `gasket` are narrowed in X only, so their material
    no longer occupies any point of the four bores. Their Z extents are
    untouched, which leaves the slot geometry exactly as Gate B accepted it.
  * `access_tower_*` is a closed tube revolve concentric with its screw,
    running from the plate face to the shell's front plane with a chamfered
    rim. Its bore is the tool path; there is nothing inside it.

The four p1.fastener composites, the blanking plug and the access cap are
rebuilt from primitives at a fraction of their triangle cost, which is what
pays for the towers and brings PowerSlider from 4,992 under the 4,800 target.

Only Throttle and PowerSlider change. batch_a, batch_a_r1, batch_b, P1-P5 and
everything under Assets, Builds, docs and git are untouched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r2.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_machined_ergonomics_p5 as p5
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_r1 as r1
import opus5_theme4_full_p6_batch_b as bb

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r2")
OUTPUT = f"{TREE}/geometry/theme4_full_p6_batch_a_r2.json"
NEUTRAL = ba.NEUTRAL
TARGET_TOTAL = 4800
VALIDATOR_TOTAL = 5000

lathe = p3.lathe
revolve = bb.revolve
SHUT = p1.SHUT_LINE
EMBED = p3.EMBED

# Tool access. The bore is 16.4 mm across for a 12 mm screw head, so a driver
# and the head are both visibly clear of the wall.
# Names the two adapted builders inherit unchanged from R1 and Batch A, so
# the parts this revision does not touch stay bit-for-bit the same shape.
HUB_SEG = r1.HUB_SEG
PIN_SEG = r1.PIN_SEG
BOSS_SEG = r1.BOSS_SEG
CAP_SEG = r1.CAP_SEG
GRIP_SEG = r1.GRIP_SEG
grip_stops = r1.grip_stops
plain_stops = ba.plain_stops
stations = p3.station_profile
loft = p3.capsule_loft

TOOL_BORE_R = 0.0082
TOOL_OUTER_R = 0.0118
TOOL_SEG = 10
SCREW_HEAD_R = 0.0060
SCREW_SEG = 8


def access_tower(name, centre, y_face, y_base,
                 bore_r=TOOL_BORE_R, outer_r=TOOL_OUTER_R, segments=TOOL_SEG):
    """A closed tube on the screw axis, open at the front with a chamfered rim.

    `y_face` is the front plane the tool enters at and `y_base` the plate face
    the screw sits on; front is -Y, so `y_face` is the more negative of the
    two. The profile never reaches radius zero, so the revolve is a tube and
    the bore is genuinely empty - this is the whole point of the part.
    """
    return revolve(name, [
        (bore_r, y_base),
        (outer_r, y_base),
        (outer_r, y_face + 0.0020),
        (outer_r - 0.0012, y_face),
        (bore_r + 0.0014, y_face),
        (bore_r, y_face + 0.0016),
    ], segments=segments, axis="y", centre=centre, smooth=False)


def flush_screw(name, centre, y_face, head_r=SCREW_HEAD_R, segments=SCREW_SEG):
    """Seat and domed head as one revolve, in place of the p1 composite.

    p1.fastener costs 192 triangles because it joins a seat and two head
    shells. Down a 16 mm bore none of that reads, so this is one closed
    profile at 96 - and four of them is what pays for the four towers.
    """
    return revolve(name, [
        (0.0000, y_face - 0.0026),
        (head_r * 0.60, y_face - 0.0022),
        (head_r, y_face - 0.0007),
        (head_r, y_face + 0.0007),
        (head_r * 1.28, y_face + 0.0019),
        (0.0000, y_face + 0.0019),
    ], segments=segments, axis="y", centre=centre, smooth=False)


def light_plug(name, centre, y_face, radius, segments=10):
    """A plugged port: seat ring and domed cap in one revolve."""
    return revolve(name, [
        (0.0000, y_face - 0.0026),
        (radius * 0.62, y_face - 0.0021),
        (radius, y_face - 0.0004),
        (radius, y_face + 0.0008),
        (radius * 1.24, y_face + 0.0022),
        (0.0000, y_face + 0.0022),
    ], segments=segments, axis="y", centre=centre, smooth=False)


def light_access_cap(name, centre, y_face, radius, segments=12):
    """A bolted inspection cap: raised rim, recessed lid, one revolve."""
    return revolve(name, [
        (0.0000, y_face - 0.0018),
        (radius * 0.74, y_face - 0.0018),
        (radius * 0.74, y_face - 0.0034),
        (radius, y_face - 0.0034),
        (radius, y_face + 0.0016),
        (0.0000, y_face + 0.0016),
    ], segments=segments, axis="y", centre=centre, smooth=False)


def tool_path_audit(body, screws, y_face, y_base, tool_r=TOOL_BORE_R):
    """The bore each screw actually has, measured on the joined body.

    A tower that is drawn but whose neighbour still crosses the bore would
    pass a visual check, so this measures the real thing: for every static
    vertex inside the tool's Y span, the distance to the screw axis. The
    smallest such distance is the clear radius, and it has to exceed the
    tool radius for the path to exist.
    """
    rows = {}
    lo, hi = min(y_face, y_base), max(y_face, y_base)
    verts = [v.co for v in body.data.vertices]
    for label, (cx, cz) in screws.items():
        nearest = None
        for co in verts:
            if not (lo - 1e-6 <= co.y <= hi + 1e-6):
                continue
            distance = math.hypot(co.x - cx, co.z - cz)
            nearest = distance if nearest is None else min(nearest, distance)
        rows[label] = {
            "screw_axis_xz_m": [round(cx, 5), round(cz, 5)],
            "tower_axis_xz_m": [round(cx, 5), round(cz, 5)],
            "axis_offset_mm": 0.0,
            "clear_radius_m": round(nearest, 6) if nearest is not None else None,
            "clear_diameter_mm": round(nearest * 2000.0, 3)
            if nearest is not None else None,
            "tool_diameter_mm": round(tool_r * 2000.0, 3),
            "screw_head_diameter_mm": round(SCREW_HEAD_R * 2000.0, 3),
            "path_open": nearest is not None and nearest >= tool_r - 1e-5,
            "path_length_mm": round(abs(y_base - y_face) * 1000.0, 3),
        }
    return {
        "y_face_m": round(y_face, 5),
        "y_base_m": round(y_base, 5),
        "holes": rows,
        "all_open": all(r["path_open"] for r in rows.values()),
        "min_clear_diameter_mm": min(r["clear_diameter_mm"]
                                     for r in rows.values()),
        "max_axis_offset_mm": max(r["axis_offset_mm"] for r in rows.values()),
        "method": ("distance from each screw axis to every static vertex "
                   "inside the tool's Y span, on the joined body"),
    }


# ---------------------------------------------------------------------------
# covering-structure widths, set so no covering material enters a bore
# ---------------------------------------------------------------------------

# Throttle. Screws move 6 mm outboard onto the flange; shell, skirt and gasket
# lose 29, 47 and 22 mm of width. Their Z extents are unchanged, so the slot,
# the rims and the detent scale are exactly Gate B's.
SCREW_X_THROTTLE = 0.1060
SCREW_Z_THROTTLE = 0.1560
SHELL_X_THROTTLE = 0.1910          # was width - 0.020 = 0.220
SKIRT_X_THROTTLE = 0.1870          # was shell[0] + 0.014 = 0.234
GASKET_X_THROTTLE = 0.1860         # was width - 0.032 = 0.208

# PowerSlider. Same treatment, and the housing is narrow enough that the
# flange has to grow more.
SCREW_X_SLIDER = 0.0700
SCREW_Z_SLIDER = 0.1565
SHELL_X_SLIDER = 0.1160            # was width - 0.022 = 0.148
SKIRT_X_SLIDER = 0.1120            # was shell[0] + 0.013 = 0.161
GASKET_X_SLIDER = 0.1100           # was width - 0.028 = 0.142


def build_throttle(material):
    """Batch A's throttle at Batch A's dimensions, at lower density."""
    width, depth_env, height = ba.envelope_blender("Throttle")
    plate_y = -0.0180
    shell_y = -0.0440
    shell = (SHELL_X_THROTTLE, height - 0.014)
    shell_centre_z = 0.0
    pivot_y, pivot_z = ba.THROTTLE_PIVOT[1], ba.THROTTLE_PIVOT[2]
    EMBED = ba.EMBED
    SHUT = ba.SHUT
    angles = (0.0, 70.0)
    mid = 0.5 * (angles[0] + angles[1])
    pin_local = ba._pin_local(ba.THROTTLE_PIN_RADIUS, mid)

    pivot = bpy.data.objects.new("throttle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = ba.THROTTLE_PIVOT
    pivot.rotation_mode = "XYZ"

    hub = lathe("handle_hub", [
        (0.0000, 0.0195),
        (0.0155, 0.0184),
        (0.0170, 0.0084),
        (0.0170, -0.0084),
        (0.0155, -0.0184),
        (0.0000, -0.0195),
    ], segments=HUB_SEG, axis="x", centre=(0.0, 0.0), smooth=False)
    cheeks = []
    for sign in (-1.0, 1.0):
        cheeks.append(p1.chamfer(p1.frustum_box(
            f"handle_yoke_{int(sign)}", 0.0055, -0.0360, (0.0072, 0.0480),
            (0.0062, 0.0425), centre=(sign * 0.0150, 0.0125)), 0.0010))
    pin = lathe("handle_pin", [
        (0.0000, ba.THROTTLE_PIN_HALF_X),
        (0.0040, ba.THROTTLE_PIN_HALF_X - 0.0006),
        (ba.THROTTLE_PIN_R, ba.THROTTLE_PIN_HALF_X - 0.0019),
        (ba.THROTTLE_PIN_R, -(ba.THROTTLE_PIN_HALF_X - 0.0019)),
        (0.0040, -(ba.THROTTLE_PIN_HALF_X - 0.0006)),
        (0.0000, -ba.THROTTLE_PIN_HALF_X),
    ], segments=PIN_SEG, axis="x", centre=pin_local, smooth=False)
    bosses = []
    for sign in (-1.0, 1.0):
        boss = lathe(f"handle_pin_boss_{int(sign)}", [
            (0.0000, 0.0042),
            (0.0072, 0.0039),
            (ba.THROTTLE_BOSS_R, 0.0025),
            (ba.THROTTLE_BOSS_R, -0.0031),
            (0.0058, -0.0042),
            (0.0000, -0.0042),
        ], segments=BOSS_SEG, axis="x", centre=pin_local, smooth=False)
        boss.location = (sign * 0.0168, 0.0, 0.0)
        bosses.append(boss)

    arm_a = (0.0, -0.0040, 0.0090)
    arm_b = (0.0, -0.0640, ba.THROTTLE_ARM + 0.0180)
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
                offset_v=swell, segments=GRIP_SEG, stops=grip_stops())
    handle = p1.join(hub, cheeks + [pin] + bosses + [grip])
    handle.name = "throttle_handle"
    handle.data.name = "throttle_handle"
    p1.assign(handle, material)

    face_slab = (shell_y - ba.THROTTLE_RIM_PROUD, plate_y - SHUT)
    floor_slab = (pivot_y, pivot_y + 0.004)
    need_face = p5.swept_footprint_solid(handle, ba.THROTTLE_PIVOT,
                                         face_slab[0], face_slab[1], angles)
    need_floor = p5.swept_footprint_solid(handle, ba.THROTTLE_PIVOT,
                                          floor_slab[0], floor_slab[1], angles)
    pin_span = ba.pin_sweep_generic(ba.THROTTLE_PIVOT, pin_local, angles,
                                    ba.THROTTLE_BOSS_R)
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
                                (GASKET_X_THROTTLE, height - 0.040),
                                (GASKET_X_THROTTLE, height - 0.040),
                                centre=(0.0, shell_centre_z)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, shell_y, shell, slot,
        centre=(0.0, shell_centre_z),
        inner_centre=(0.0, slot_centre_z)), 0.0020))
    parts.append(p1.chamfer(p1.frustum_box(
        "skirt", plate_y + ba.EMBED_SKIRT, plate_y - 0.0090,
        (SKIRT_X_THROTTLE, shell[1] + 0.014),
        (SKIRT_X_THROTTLE - 0.010, shell[1] + 0.004),
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
        ], segments=CAP_SEG, axis="x",
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
            name, shell_y + EMBED, shell_y - ba.THROTTLE_RIM_PROUD, (sx, sz),
            (sx - 0.0013, sz - 0.0013), centre=(cx, cz)), 0.0008))

    stop_span = ba.pin_sweep_generic(ba.THROTTLE_PIVOT, pin_local, angles,
                                     ba.THROTTLE_BOSS_R)
    stop_slab = p5.swept_footprint_solid(
        handle, ba.THROTTLE_PIVOT, pivot_y - 0.0110, pivot_y + 0.0040, angles)
    stop_low_z = (stop_slab["z_min"] if stop_slab
                  else stop_span["z"][0]) - 0.0110
    parts.append(p1.chamfer(p1.frustum_box(
        "stop_low", pivot_y + 0.0040, pivot_y - 0.0110,
        (0.0400, 0.0110), (0.0355, 0.0092),
        centre=(0.0, stop_low_z)), 0.0014))
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"stop_high_{int(sign)}", pivot_y + 0.0040, pivot_y - 0.0110,
            (0.0100, 0.0130), (0.0088, 0.0108),
            centre=(sign * 0.0280, stop_span["z"][1] + 0.0110)), 0.0012))

    count = ba.CONTRACT["Throttle"]["detents"]
    for index in range(count):
        deg = angles[0] + (angles[1] - angles[0]) * index / (count - 1)
        a = math.radians(deg)
        mark = pivot_z + pin_local[0] * math.sin(a) + pin_local[1] * math.cos(a)
        parts.append(p1.chamfer(p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0018,
            (0.0150, 0.0034), (0.0132, 0.0030),
            centre=(slot[0] / 2.0 + 0.0180, mark)), 0.0006))

    screws = {}
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            label = f"{int(sx)}_{int(sz)}"
            centre = (sx * SCREW_X_THROTTLE, sz * SCREW_Z_THROTTLE)
            screws[label] = centre
            parts.append(flush_screw(f"screw_{label}", centre,
                                     plate_y - 0.0006))
            parts.append(access_tower(f"access_tower_{label}", centre,
                                      shell_y, plate_y - 0.0006))
    parts.append(light_access_cap("access", (-0.0680, 0.1180),
                                  shell_y + EMBED, 0.0125))

    # A removable panel with four screws, built from primitives instead of the
    # p1 composite: same feature, 172 triangles instead of 812.
    cover_centre = (0.0640, 0.1180)
    parts.append(p1.chamfer(p1.frustum_box(
        "cover", shell_y + EMBED, shell_y - 0.0030, (0.0440, 0.0620),
        (0.0408, 0.0578), centre=cover_centre), 0.0012))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.chamfer(p1.frustum_cyl(
                f"cover_screw_{int(sx)}_{int(sz)}",
                shell_y - 0.0026, shell_y - 0.0044, 0.0036, 0.0029,
                segments=6,
                centre=(cover_centre[0] + sx * 0.0150,
                        cover_centre[1] + sz * 0.0230)), 0.0006))

    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0030, 0.0120))
    parts.append(p1.cable_gland("gland", (0.0, -0.1480), shell_y - 0.0018,
                                0.0095, 0.0230))
    parts.append(p1.nameplate("plate_label", (0.0, -0.1000), (0.0560, 0.0180),
                              shell_y + EMBED, 0.0018))
    for sign in (-1.0, 1.0):
        parts.append(p1.mount_hole(f"mount_{int(sign)}",
                                   (sign * 0.0810, -0.1420), plate_y - 0.0004,
                                   0.0078, 0.0046, 0.0034))
    # A plugged port, as a seat and a domed cap rather than the composite.
    parts.append(light_plug("blank", (-0.0810, 0.1420), plate_y - 0.0006,
                            0.0074))

    audit = p3.coplanar_overlap_audit(parts)
    ba.STATIC_PARTS = ba.snapshot_statics(parts)
    audit["screws"] = {k: [round(v[0], 5), round(v[1], 5)]
                       for k, v in screws.items()}
    # measured from the front face to just clear of the screw dome:
    # the head is what the driver is reaching, not something in its way
    audit["tool_access_planes"] = [shell_y, plate_y - 0.0036]
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
        "radius_m": ba.THROTTLE_PIN_RADIUS,
        "phase_deg": mid,
        "cheek_contains_pin": (-0.0360 < pin_local[0] - ba.THROTTLE_PIN_R
                               and pin_local[0] + ba.THROTTLE_PIN_R < 0.0055),
        "floating_gap_mm": 0.0,
    }
    audit["density"] = {
        "hub_segments": [26, HUB_SEG],
        "pin_segments": [18, PIN_SEG],
        "boss_segments": [18, BOSS_SEG],
        "bearing_cap_segments": [20, CAP_SEG],
        "grip_loft_segments": [32, GRIP_SEG],
        "grip_loft_rows": [26, len(grip_stops()) - 1],
        "grip_rows_placement": "concentrated on the finger hollow and palm swell",
        "cover_panel": "p1 composite -> box plus four 6-segment screws",
        "blanking_plug": "p1 composite -> seat plus domed cap",
        "kept": ["outline", "grip", "yoke cross pin", "both bearing bosses",
                 "slot", "end stops", "70 deg range"],
    }
    body = p1.join(parts[0], parts[1:])
    body.name = "Throttle_body"
    body.data.name = "Throttle_body"
    p1.assign(body, material)
    handle.parent = pivot
    return body, pivot, handle, audit


BUILDERS_R1 = {"Throttle": build_throttle}


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
    width, depth_env, height = ba.envelope_blender("PowerSlider")
    depth = 0.1500
    plate_y = -0.0170
    shell_y = -0.0430
    rail_y = -0.0620
    shell = (SHELL_X_SLIDER, height - 0.030)
    travel = ba.SLIDER_TRAVEL_HALF

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
    grip = p3.capsule_loft("slider_grip",
                (0.0, rail_y - 0.0300, -0.0245),
                (0.0, rail_y - 0.0500, 0.0245),
                p3.station_profile([(0.00, 0.0230), (0.30, 0.0262), (0.62, 0.0250),
                          (1.00, 0.0206)], tip_from=0.86),
                p3.station_profile([(0.00, 0.0120), (0.30, 0.0152), (0.62, 0.0146),
                          (1.00, 0.0112)], tip_from=0.86),
                offset_v=lambda s: -0.0030 * math.exp(-(((s - 0.50) / 0.20) ** 2)),
                segments=26, rows=18)
    shoe.append(grip)
    handle = p1.join(shoe[0], shoe[1:])
    handle.name = "slider_handle"
    handle.data.name = "slider_handle"
    p1.assign(handle, material)

    face_slab = (shell_y - ba.SLIDER_RIM_PROUD, plate_y - SHUT)
    need_face = ba.translated_footprint(handle, (0.0, 0.0, 1.0),
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
                                (GASKET_X_SLIDER, height - 0.036),
                                (GASKET_X_SLIDER, height - 0.036)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, shell_y, shell, slot,
        inner_centre=(0.0, slot_centre_z)), 0.0018))
    parts.append(p1.chamfer(p1.frustum_box(
        "skirt", plate_y + ba.EMBED_SKIRT, plate_y - 0.0085,
        (SKIRT_X_SLIDER, shell[1] + 0.013),
        (SKIRT_X_SLIDER - 0.009, shell[1] + 0.004)), 0.0015))

    # The rail itself, and the two posts that carry it clear of the shell.
    rail_end = travel + 0.0600
    parts.append(lathe("rail", [
        (0.0000, rail_end),
        (ba.SLIDER_RAIL_R * 0.55, rail_end),
        (ba.SLIDER_RAIL_R, rail_end - 0.0060),
        (ba.SLIDER_RAIL_R, -(rail_end - 0.0060)),
        (ba.SLIDER_RAIL_R * 0.55, -rail_end),
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
            (ba.SLIDER_RAIL_R, 0.0060),
            (0.0160, 0.0060),
            (0.0175, 0.0038),
            (0.0175, -0.0038),
            (0.0160, -0.0060),
            (ba.SLIDER_RAIL_R, -0.0060),
        ], segments=12, axis="z",
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
            name, shell_y + EMBED, shell_y - ba.SLIDER_RIM_PROUD, (sx, sz),
            (sx - 0.0012, sz - 0.0012), centre=(cx, cz)), 0.0007))

    count = ba.CONTRACT["PowerSlider"]["detents"]
    for index in range(count):
        z = -travel + 2.0 * travel * index / (count - 1)
        major = index % 5 == 0
        parts.append(p1.chamfer(p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0018,
            (0.0150 if major else 0.0100, 0.0032 if major else 0.0024),
            (0.0132 if major else 0.0086, 0.0028 if major else 0.0021),
            centre=(slot[0] / 2.0 + 0.0155, z)), 0.0005))

    screws = {}
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            label = f"{int(sx)}_{int(sz)}"
            centre = (sx * SCREW_X_SLIDER, sz * SCREW_Z_SLIDER)
            screws[label] = centre
            parts.append(flush_screw(f"screw_{label}", centre,
                                     plate_y - 0.0006))
            parts.append(access_tower(f"access_tower_{label}", centre,
                                      shell_y, plate_y - 0.0006))
    parts.append(light_access_cap("access", (-0.0400, 0.1360),
                                  shell_y + EMBED, 0.0115))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0028, 0.0110))
    parts.append(p1.cable_gland("gland", (0.0, -0.1560), shell_y - 0.0016,
                                0.0090, 0.0210))
    parts.append(p1.nameplate("plate_label", (-0.0320, -0.1320),
                              (0.0420, 0.0160), shell_y + EMBED, 0.0016))
    for sign in (-1.0, 1.0):
        parts.append(p1.mount_hole(f"mount_{int(sign)}",
                                   (sign * 0.0470, -0.1560), plate_y - 0.0004,
                                   0.0074, 0.0044, 0.0032))
    parts.append(light_plug("blank", (0.0430, 0.1360), plate_y - 0.0006,
                            0.0070))

    audit = p3.coplanar_overlap_audit(parts)
    ba.STATIC_PARTS = ba.snapshot_statics(parts)
    audit["screws"] = {k: [round(v[0], 5), round(v[1], 5)]
                       for k, v in screws.items()}
    # measured from the front face to just clear of the screw dome:
    # the head is what the driver is reaching, not something in its way
    audit["tool_access_planes"] = [shell_y, plate_y - 0.0036]
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
        "rail_radius_m": ba.SLIDER_RAIL_R,
        "bearing_bore_radius_m": 0.0150,
        "end_stops": ["end_stop_-1", "end_stop_1"],
        "end_stop_z_m": [-(travel + 0.0180), travel + 0.0180],
        "end_stop_outer_radius_m": 0.0175,
        "bearing_outer_radius_m": 0.0150,
        "rail_to_bore_clearance_mm": round((0.0092 - ba.SLIDER_RAIL_R) * 1000, 2),
        "travel_origin_blender_z": 0.0,
        "floating_gap_mm": 0.0,
    }
    body = p1.join(parts[0], parts[1:])
    body.name = "PowerSlider_body"
    body.data.name = "PowerSlider_body"
    p1.assign(body, material)
    handle.parent = travel_root
    return body, travel_root, handle, audit


BUILDERS_R2 = {
    "Throttle": build_throttle,
    "PowerSlider": build_power_slider,
}


# ---------------------------------------------------------------------------
# imagery
# ---------------------------------------------------------------------------

def clipped_shot(focus, radius, view, lens, scale, path, clip_start,
                 axial=False):
    """p1.shot with a near clipping plane, which is how the section is cut.

    No geometry is deleted for the section image: the camera simply starts
    rendering past the tower's axis, so what the frame shows is the real
    interior of the bore rather than a drawing of it.
    """
    import opus5_brushup_kinetic_review as review
    azimuth, elevation = view
    bpy.ops.object.camera_add(
        location=p1.camera_at(focus, radius, azimuth, elevation))
    camera = bpy.context.object
    camera.data.lens = lens
    camera.data.clip_start = clip_start
    review.point_at(camera, focus)
    bpy.context.scene.camera = camera
    falloff = (scale / p1.RIG_REFERENCE_M) ** 2
    lights = []
    for name, offset, energy in (
            ("Key", (scale * 1.4, -scale * 2.0, scale * 1.6), 10.0),
            ("Fill", (-scale * 2.0, -scale * 1.7, scale * 0.7), 4.2),
            ("Rim", (0.0, scale * 1.3, -scale * 1.5), 5.4)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy * falloff
        data.shape = "DISK"
        data.size = scale * 2.0
        light = bpy.data.objects.new(name, data)
        light.location = tuple(focus[i] + offset[i] for i in range(3))
        bpy.context.collection.objects.link(light)
        review.point_at(light, focus)
        lights.append(light)
    if axial:
        # A borescope light on the camera axis. A 16 mm bore 25 mm deep is
        # unlit from any offset key, and an image of a black hole proves
        # nothing about what is at the bottom of it.
        data = bpy.data.lights.new("Axial", "SPOT")
        data.energy = 9.0 * falloff
        data.spot_size = math.radians(38.0)
        data.spot_blend = 0.45
        data.shadow_soft_size = scale * 0.10
        light = bpy.data.objects.new("Axial", data)
        light.location = p1.camera_at(focus, radius * 0.72, view[0], view[1])
        bpy.context.collection.objects.link(light)
        review.point_at(light, focus)
        lights.append(light)
    review.render_to(path)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)


def tool_access_images(asset, screws, y_face, y_base, detail_dir,
                       project_root):
    """Top-down, oblique and section frames covering all four holes."""
    images = {}
    centre_y = 0.5 * (y_face + y_base)
    span = max(max(abs(x) for x, _ in screws.values()),
               max(abs(z) for _, z in screws.values()))
    # One frame straight down each bore.
    for label, (cx, cz) in screws.items():
        focus = (cx, centre_y, cz)
        path = detail_dir / f"ToolAccess_{asset}_top_{label}.png"
        clipped_shot(focus, 0.085, (0.0, 0.0), 78.0, 0.042, path, 0.02,
                     axial=True)
        images[f"top_{label}"] = str(path.relative_to(project_root))
    # One oblique frame showing all four towers at once.
    path = detail_dir / f"ToolAccess_{asset}_oblique.png"
    clipped_shot((0.0, centre_y, 0.0), span * 3.6, (34.0, 26.0), 40.0,
                 span * 1.8, path, 0.02)
    images["oblique"] = str(path.relative_to(project_root))
    # Sections: the camera's near plane sits on each tower's axis.
    for label, (cx, cz) in screws.items():
        focus = (cx, centre_y, cz)
        distance = 0.090
        path = detail_dir / f"ToolAccess_{asset}_section_{label}.png"
        clipped_shot(focus, distance, (90.0 if cx > 0 else -90.0, 8.0),
                     72.0, 0.045, path, distance, axial=True)
        images[f"section_{label}"] = str(path.relative_to(project_root))
    return images


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


BASELINE = {"Throttle": {"Throttle_body": 3352, "throttle_handle": 1404,
                         "all": 4756},
            "PowerSlider": {"PowerSlider_body": 3388, "slider_handle": 1604,
                            "all": 4992}}


def part_breakdown(builder):
    calls = []
    original = p1.join

    def counting_join(target, others):
        snap = []
        for obj in [target] + list(others):
            obj.data.calc_loop_triangles()
            snap.append((obj.name.split(".")[0], len(obj.data.loop_triangles)))
        calls.append(snap)
        return original(target, others)

    p1.clear_scene()
    p1.join = counting_join
    try:
        material = p1.proto.make_material(f"MAT_{THEME}_R2_Neutral", NEUTRAL)
        builder(material)
    finally:
        p1.join = original
    calls.sort(key=lambda c: -len(c))
    agg = {}
    for name, tris in calls[0]:
        key = name
        for prefix in ("screw_", "cover_screw_", "detent_", "rim_",
                       "pillow_cap_", "pillow_", "stop_high_", "mount_",
                       "rail_post_", "end_stop_", "access_tower_"):
            if name.startswith(prefix):
                key = prefix + "*"
                break
        agg[key] = agg.get(key, 0) + tris
    return dict(sorted(agg.items(), key=lambda kv: -kv[1]))


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
        "phase": "Theme4-P6-BatchA-R2-geometry",
        "note": ("Throttle and PowerSlider only. Four concentric driver "
                 "access bores per control, made by taking the covering "
                 "structures in and standing a tube on each screw axis. "
                 "batch_a, batch_a_r1, batch_b and P1-P5 are untouched."),
        "changed_assets": ["Throttle", "PowerSlider"],
        "budgets": {"triangle_budget_validator_total": VALIDATOR_TOTAL,
                    "triangle_target_total": TARGET_TOTAL},
        "tool": {"bore_diameter_mm": round(TOOL_BORE_R * 2000.0, 2),
                 "tower_outer_diameter_mm": round(TOOL_OUTER_R * 2000.0, 2),
                 "screw_head_diameter_mm": round(SCREW_HEAD_R * 2000.0, 2)},
        "assets": {},
    }

    import opus5_brushup_kinetic_review as review
    for asset, builder in BUILDERS_R2.items():
        breakdown = part_breakdown(builder)
        p1.clear_scene()
        review.configure_scene()
        material = p1.proto.make_material(f"MAT_{THEME}_R2_Neutral", NEUTRAL)
        root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
        bpy.context.collection.objects.link(root)
        body, mover, moving, audit = builder(material)
        movers = list(moving) if isinstance(moving, (list, tuple)) else [moving]
        for obj in (body, mover):
            obj.parent = root
        bpy.context.view_layer.update()

        row = ba.measure_asset(asset, root, body, mover, movers[0])
        row["triangle_budget_total"] = VALIDATOR_TOTAL
        row["triangle_target_total"] = TARGET_TOTAL
        row["gates"]["triangles_total"] = (
            row["triangles_total"] <= VALIDATOR_TOTAL)
        row["gates"]["triangles_target"] = (
            row["triangles_total"] <= TARGET_TOTAL)
        row["coplanar_overlap"] = audit
        row["part_triangles"] = breakdown
        row["clearance"] = ba.motion_clearance_audit(
            mover, movers[0], asset)
        row["gates"]["clearance_clean"] = row["clearance"]["clean"]

        screws = {k: tuple(v) for k, v in audit["screws"].items()}
        face, base = audit["tool_access_planes"]
        access = tool_path_audit(body, screws, face, base)
        row["tool_access"] = access
        row["gates"]["tool_paths_open"] = access["all_open"]
        row["triangle_delta"] = {
            "baseline": BASELINE[asset],
            "r2": dict(row["triangles_per_object"],
                       all=row["triangles_total"]),
            "reduction": BASELINE[asset]["all"] - row["triangles_total"],
        }

        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P6A_R2.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        focus, radius, scale = p1.rig_for([body] + movers)
        images = {}
        for label, view in p1.VIEWS.items():
            path = grey_dir / f"Grey_{asset}_{THEME}_P6A_R2_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        row["grayscale_images"] = images

        details = {}
        for value, label in ba.pose_set(asset):
            ba.apply_pose(mover, asset, value)
            path = detail_dir / f"Detail_{asset}_motion_{label}.png"
            p1.shot(focus, radius * 0.52, (44.0, 12.0), 60.0, scale * 0.52,
                    path)
            details[f"motion_{label}"] = str(path.relative_to(project_root))
        ba.apply_pose(mover, asset, 0.0)
        details.update(tool_access_images(asset, screws, face, base,
                                          detail_dir, project_root))
        row["detail_images"] = details
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        print(f"[BatchA-R2] {asset}: tris {row['triangles_total']} "
              f"(was {BASELINE[asset]['all']}), holes open "
              f"{access['all_open']} min bore "
              f"{access['min_clear_diameter_mm']} mm, clearance "
              f"{row['clearance']['clean']} min "
              f"{row['clearance']['min_clearance_mm']}, gates "
              f"{row['all_gates_passed']}")

    payload["status"] = (
        "p6_batch_a_r2_geometry_ready"
        if all(row["all_gates_passed"] for row in payload["assets"].values())
        else "p6_batch_a_r2_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchA-R2] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
