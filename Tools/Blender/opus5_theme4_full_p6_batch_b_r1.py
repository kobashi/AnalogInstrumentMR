"""Theme 4 Phase 3 Batch B R1: the guard geometry Quest rejected in 311.

Batch B closed the full Unity gate in 310 and is frozen. 311 failed it on
shape: on hardware the guards win and the thing they guard loses. This module
rebuilds only that relationship and leaves pivot, motion axis and range, mount
plane, envelope and the frozen P4 atlas exactly where Batch B put them.

What changes, and the measurement that says it was wrong:

Rotary   the collar's front stood at y -0.0864 and the knob crown at -0.0828,
         so the crown was 3.6 mm *inside* a collar whose bore is 0.0472 and
         whose grip band only reaches 0.0418 - a 5.4 mm annulus, which no
         finger enters. The collar front moves back to the knob's own base
         plane, -0.0620, and the grip band comes out into the open.

Button   the guard ring reached y -0.0620, 19.0 mm proud of the bezel face,
         around a cap whose widest point is 30.8 mm across; the cap's shoulder
         sat 3.2 mm behind the guard rim, so the front view is a deep well
         with a dome at the bottom. Batch B also *reported* this backwards -
         `crown_below_guard_mm` was computed as -(crown - guard) and printed
         10.8 for a crown that is 10.8 mm proud. The guard front moves to
         -0.0524 and the field name is corrected.

Lamp     the lens is 60 mm across inside a 94 mm bezel: 40.7 % of the bezel
         disc, with a hood on top of that. The lens grows to 75.2 mm, the
         bezel keeps its outer radius so the shell and screws do not move, and
         the hood narrows from 118 to 96 degrees and sits inside the bezel's
         outer radius instead of outside the lens.

Status   the three wells share a symmetric centre spacing but carry three
         different widths, so the group ran -0.0824..+0.0884 - 6.0 mm off the
         base axis - and the widest well overhung the shell's *front face*
         (half width 0.0835 after the draft) by 4.9 mm, hanging over the
         taper. The wells become one size, the group centres on the base, and
         the hood widens to cover all three.

The Status change costs the "size identifies the lit segment" idea from Batch
B: with equal wells the dark-state cue is position and the ribs, not size.
That is a real trade against 311.5's "overhang 0" and is called out in the
JSON rather than hidden.

Usage: imported by opus5_theme4_full_p6_batch_b_r1_delivery.py.
"""

import math
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_full_p6_batch_b as bb

SHUT = bb.SHUT
EMBED = bb.EMBED
NEUTRAL = bb.NEUTRAL
CONTRACT = bb.CONTRACT
VALIDATOR_TOTAL = bb.VALIDATOR_TOTAL
TARGET_TOTAL = bb.TARGET_TOTAL

FINGER_DIAMETER = 0.016          # 311.2 / 311.3 finger pad proxy
FINGER_RADIUS = FINGER_DIAMETER / 2.0


# ---------------------------------------------------------------------------
# Rotary R1
# ---------------------------------------------------------------------------

ROTARY_COLLAR_Y_B = -0.0864      # Batch B, frozen: 3.6 mm proud of the crown
ROTARY_COLLAR_Y = -0.0620        # R1: back to the knob's own base plane


def build_rotary(material):
    """Batch B's rotary with the collar pulled back off the grip band.

    Nothing but `collar_y` moves. The knob profile, the flutes, the pivot,
    the bore, the graduations and the envelope are Batch B's. The collar is
    still 14.0 mm proud of the bezel face, so it still carries a sleeve that
    sweeps across the panel; what it no longer does is bury the flutes.
    """
    width, depth_env, height = bb.envelope_blender("Rotary")
    outer = 0.0755
    plate_y = -0.0150
    face_y = -0.0480
    collar_y = ROTARY_COLLAR_Y
    parts = []

    parts.append(bb.revolve("housing", [
        (0.0000, 0.0000),
        (outer * 0.88, 0.0000),
        (outer, -0.0120),
        (outer * 0.985, -0.0330),
        (outer * 0.86, face_y),
        (0.0530, face_y),
        (0.0530, collar_y),
        (0.0472, collar_y),
        (0.0472, face_y + 0.0026),
        (bb.ROTARY_BORE_R, face_y + 0.0026),
        (bb.ROTARY_BORE_R, plate_y - SHUT),
        (0.0000, plate_y - SHUT),
    ], segments=bb.ROTARY_HOUSING_SEG, axis="y", smooth=False))

    ring_inner, ring_outer = 0.0332, 0.0452
    for index in range(12):
        angle = -90.0 + 30.0 * index
        major = index % 3 == 0
        parts.append(p1.radial_tick(
            f"tick_{index}", angle,
            ring_inner if major else ring_inner + 0.0044, ring_outer,
            0.0034 if major else 0.0022,
            face_y + 0.0007,
            face_y - (0.0013 if major else 0.0010)))
    parts.append(p1.nameplate("plate_label", (0.0, -(outer - 0.0125)),
                              (0.0330, 0.0110), face_y - 0.0016, 0.0014))

    for index in range(3):
        angle = math.radians(90.0 + 120.0 * index)
        seat = outer * 0.90
        parts.append(p1.fastener(
            f"screw_{index}",
            (seat * math.cos(angle), seat * math.sin(angle)),
            -0.0090, 0.0062, 0.0046))
    parts.append(p1.register_step("register", (outer * 1.55, outer * 1.55),
                                  -EMBED, -0.0030, 0.0110))
    parts.append(p1.chamfer(p1.frustum_cyl(
        "plug_seat", -0.0230, -0.0270, 0.0074, 0.0066, segments=10,
        centre=(outer - 0.0130, 0.0)), 0.0008))

    audit = p3.coplanar_overlap_audit(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = "Rotary_body"
    body.data.name = "Rotary_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("knob_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, bb.ROTARY_PIVOT_Y, 0.0)
    pivot.rotation_mode = "XYZ"

    grip_lo, grip_hi = 4, 6
    knob = bb.revolve("knob", [
        (0.0000, 0.0170),
        (bb.ROTARY_SHAFT_R, 0.0170),
        (bb.ROTARY_SHAFT_R, -0.0038),
        (0.0402, -0.0052),
        (0.0418, -0.0086),
        (0.0418, -0.0148),
        (0.0402, -0.0170),
        (0.0356, -0.0186),
        (0.0212, -0.0202),
        (0.0000, -0.0208),
    ], segments=bb.ROTARY_KNOB_SEG, axis="y", smooth=False,
        radial=bb.flute_field(bb.ROTARY_FLUTES, 0.0032, (grip_lo, grip_hi)))
    index_mark = p1.chamfer(p1.frustum_box(
        "index_mark", -0.0196, -0.0220, (0.0040, 0.0210),
        (0.0033, 0.0186), centre=(0.0, 0.0088)), 0.0005)
    knob = p1.join(knob, [index_mark])
    knob.name = "knob"
    knob.data.name = "knob"
    p1.assign(knob, material)
    knob.parent = pivot

    crown_y = bb.ROTARY_PIVOT_Y - 0.0208
    audit["mechanism"] = {
        "shaft_radius_m": bb.ROTARY_SHAFT_R,
        "bore_radius_m": bb.ROTARY_BORE_R,
        "radial_clearance_mm": round(
            (bb.ROTARY_BORE_R - bb.ROTARY_SHAFT_R) * 1000, 2),
        "collar_front_y_m": collar_y,
        "collar_front_y_batch_b_m": ROTARY_COLLAR_Y_B,
        "collar_moved_back_mm": round(
            (collar_y - ROTARY_COLLAR_Y_B) * 1000.0, 2),
        "knob_crown_y_m": round(crown_y, 4),
        "crown_proud_of_collar_mm": round((collar_y - crown_y) * 1000.0, 2),
        "collar_proud_of_bezel_face_mm": round((face_y - collar_y) * 1000.0, 2),
        "flutes": bb.ROTARY_FLUTES,
        "flute_depth_m": 0.0032,
        "index_mark": "index_mark, readout role, on the crown",
        "graduations": 12,
        "misoperation": (
            "the collar is still 14.0 mm proud of the bezel face and carries a "
            "sleeve sweeping the panel; the knob is turned by fingertips in "
            "the flutes, which now stand in front of the collar instead of "
            "inside it"),
    }
    return body, pivot, [knob], audit


# ---------------------------------------------------------------------------
# Button R1
# ---------------------------------------------------------------------------

BUTTON_GUARD_Y_B = -0.0620       # Batch B, frozen: 19.0 mm proud of the face
BUTTON_GUARD_Y = -0.0524         # R1: 9.4 mm proud


def build_button(material):
    """Batch B's button with the guard ring cut down by 9.6 mm.

    Travel, `button_travel`, `button`, the skirt, the bore and the bezel's
    outer wall are Batch B's. Only the guard step's front plane moves. At full
    press the cap's shoulder is still proud of the guard rim, so the cap never
    disappears into the ring at either end of the stroke.
    """
    width, depth_env, height = bb.envelope_blender("Button")
    plate_y = -0.0150
    face_y = -0.0430
    guard_y = BUTTON_GUARD_Y
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.010, height - 0.010)), 0.0015))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.026, height - 0.026),
                                (width - 0.026, height - 0.026)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, face_y, (width - 0.008, height - 0.008),
        (0.1000, 0.1000)), 0.0016))
    parts.append(bb.revolve("bezel", [
        (bb.BUTTON_BORE_R, plate_y - SHUT),
        (0.0480, plate_y - SHUT),
        (0.0480, -0.0300),
        (0.0470, face_y),
        (0.0452, face_y),
        (0.0452, guard_y),
        (0.0396, guard_y),
        (0.0396, face_y + 0.0022),
        (0.0334, face_y + 0.0022),
        (0.0334, -0.0356),
        (bb.BUTTON_BORE_R, -0.0330),
    ], segments=28, axis="y", smooth=False))
    parts.append(p1.nameplate("plate_label", (0.0, -(height / 2.0 - 0.0135)),
                              (0.0380, 0.0120), plate_y - 0.0017, 0.0014))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.0125), sz * (height / 2.0 - 0.0125)),
                plate_y - 0.0015, 0.0058, 0.0042))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0028, 0.0105))

    audit = p3.coplanar_overlap_audit(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = "Button_body"
    body.data.name = "Button_body"
    p1.assign(body, material)

    travel = bpy.data.objects.new("button_travel", None)
    bpy.context.collection.objects.link(travel)
    travel.location = (0.0, bb.BUTTON_PIVOT_Y, 0.0)
    travel.rotation_mode = "XYZ"

    button = bb.revolve("button", [
        (0.0000, bb.BUTTON_SKIRT_LEN),
        (bb.BUTTON_SKIRT_R, bb.BUTTON_SKIRT_LEN),
        (bb.BUTTON_SKIRT_R, 0.0026),
        (0.0294, -0.0010),
        (0.0308, -0.0052),
        (0.0300, -0.0092),
        (0.0246, -0.0122),
        (0.0150, -0.0128),
        (0.0072, -0.0112),
        (0.0000, -0.0104),
    ], segments=26, axis="y", smooth=False)
    button.name = "button"
    button.data.name = "button"
    p1.assign(button, material)
    button.parent = travel

    crown_y = bb.BUTTON_PIVOT_Y - 0.0128
    shoulder_y = bb.BUTTON_PIVOT_Y - 0.0052        # widest point of the cap
    audit["mechanism"] = {
        "travel_m": bb.BUTTON_TRAVEL,
        "skirt_radius_m": bb.BUTTON_SKIRT_R,
        "bore_radius_m": bb.BUTTON_BORE_R,
        "radial_clearance_mm": round(
            (bb.BUTTON_BORE_R - bb.BUTTON_SKIRT_R) * 1000.0, 2),
        "skirt_length_m": bb.BUTTON_SKIRT_LEN,
        "engagement_at_full_press_mm": round(
            (bb.BUTTON_SKIRT_LEN - bb.BUTTON_TRAVEL) * 1000.0, 2),
        "guard_front_y_m": guard_y,
        "guard_front_y_batch_b_m": BUTTON_GUARD_Y_B,
        "guard_lowered_mm": round((guard_y - BUTTON_GUARD_Y_B) * 1000.0, 2),
        "guard_proud_of_bezel_face_mm": round((face_y - guard_y) * 1000.0, 2),
        "crown_y_m": round(crown_y, 4),
        "crown_proud_of_guard_rest_mm": round(
            (guard_y - crown_y) * 1000.0, 2),
        "crown_proud_of_guard_pressed_mm": round(
            (guard_y - (crown_y + bb.BUTTON_TRAVEL)) * 1000.0, 2),
        "shoulder_proud_of_guard_rest_mm": round(
            (guard_y - shoulder_y) * 1000.0, 2),
        "shoulder_proud_of_guard_pressed_mm": round(
            (guard_y - (shoulder_y + bb.BUTTON_TRAVEL)) * 1000.0, 2),
        "batch_b_report_defect": (
            "Batch B printed `crown_below_guard_mm` 10.8 from "
            "-(crown - guard); the crown was 10.8 mm *proud*, not below, and "
            "the docstring's '3 mm below the guard rim' was wrong too"),
        "misoperation": (
            "the guard ring is 9.4 mm proud of the bezel face and 8.8 mm "
            "clear of the cap's widest point, so it still fences a sliding "
            "hand off the cap's flank; a deliberate press comes down the axis"),
    }
    return body, travel, [button], audit


# ---------------------------------------------------------------------------
# Lamp R1
# ---------------------------------------------------------------------------

LAMP_LENS_R_B = 0.0300
LAMP_LENS_R = 0.0376
LAMP_BEZEL_OUTER = 0.0470        # unchanged: shell, screws and plate hold
LAMP_HOOD_ARC_B = 118.0
LAMP_HOOD_ARC = 96.0


def build_lamp(material):
    """Batch B's lamp with the lens made the subject and the ring the frame.

    The bezel's outer radius does not move, so the shell, the screws and the
    envelope are Batch B's. What moves is the bezel's *bore and lip*, outward
    from 0.0300 / 0.0352 to 0.0376 / 0.0402, and the lens with them; the hood
    follows the lens out and narrows, and now sits inside the bezel's outer
    radius rather than standing proud of it.
    """
    width, depth_env, height = bb.envelope_blender("Lamp")
    plate_y = -0.0140
    face_y = -0.0400
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.010, height - 0.010)), 0.0014))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.024, height - 0.022),
                                (width - 0.024, height - 0.022)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, face_y, (width - 0.008, height - 0.008),
        (0.0980, 0.0980)), 0.0016))
    parts.append(bb.revolve("bezel", [
        (LAMP_LENS_R, plate_y - SHUT),
        (LAMP_BEZEL_OUTER, plate_y - SHUT),
        (LAMP_BEZEL_OUTER, -0.0286),
        (0.0446, face_y),
        (0.0402, face_y),
        (0.0402, -0.0332),
        (LAMP_LENS_R, -0.0308),
    ], segments=26, axis="y", smooth=False))

    hood_segments = 14
    verts, faces = [], []
    span = math.radians(LAMP_HOOD_ARC)
    start = math.radians(90.0 - LAMP_HOOD_ARC / 2.0)
    for row, (radius, y) in enumerate(((0.0410, -0.0332), (0.0446, -0.0450),
                                       (0.0410, -0.0472), (0.0392, -0.0346))):
        for j in range(hood_segments + 1):
            a = start + span * j / hood_segments
            verts.append((radius * math.cos(a), y, radius * math.sin(a)))
    stride = hood_segments + 1
    for row in range(3):
        for j in range(hood_segments):
            a0 = row * stride + j
            faces.append((a0, a0 + 1, a0 + stride + 1, a0 + stride))
    for j in range(hood_segments):
        faces.append((3 * stride + j, 3 * stride + j + 1, j + 1, j))
    for a, b in ((0, 3 * stride), (hood_segments, 4 * stride - 1)):
        faces.append((a, a + stride, a + 2 * stride, b))
    parts.append(p3._emit("hood", verts, faces, False))

    parts.append(p1.nameplate("plate_label", (0.0, -(height / 2.0 - 0.0130)),
                              (0.0420, 0.0110), plate_y - 0.0017, 0.0014))
    for sx in (-1.0, 1.0):
        parts.append(p1.fastener(
            f"screw_{int(sx)}",
            (sx * (width / 2.0 - 0.0120), height / 2.0 - 0.0130),
            plate_y - 0.0015, 0.0056, 0.0040))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0026, 0.0100))

    audit = p3.coplanar_overlap_audit(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = "Lamp_body"
    body.data.name = "Lamp_body"
    p1.assign(body, material)

    indicator = bpy.data.objects.new("indicator", None)
    bpy.context.collection.objects.link(indicator)
    indicator.location = (0.0, 0.0, 0.0)
    indicator.rotation_mode = "XYZ"

    # Seated 0.4 mm in front of the bezel lip's front plane, so no face of the
    # lens shares a plane with the bezel.
    lens = bb.revolve("indicator_lens", [
        (0.0000, -0.0336),
        (0.0346, -0.0344),
        (LAMP_LENS_R, -0.0378),
        (0.0361, -0.0424),
        (0.0298, -0.0464),
        (0.0180, -0.0491),
        (0.0000, -0.0500),
    ], segments=26, axis="y", smooth=True)
    lens.name = "indicator_lens"
    lens.data.name = "indicator_lens"
    p1.assign(lens, material)
    lens.parent = indicator

    lens_disc = math.pi * LAMP_LENS_R ** 2
    bezel_disc = math.pi * LAMP_BEZEL_OUTER ** 2
    audit["mechanism"] = {
        "indicator_is_empty_at_origin": True,
        "lens_mesh": "indicator_lens",
        "lens_radius_m": LAMP_LENS_R,
        "lens_radius_batch_b_m": LAMP_LENS_R_B,
        "lens_dome_height_mm": round((0.0500 - 0.0344) * 1000.0, 2),
        "bezel_outer_radius_m": LAMP_BEZEL_OUTER,
        "bezel_ring_width_front_mm": round(
            (LAMP_BEZEL_OUTER - LAMP_LENS_R) * 1000.0, 2),
        "lens_share_of_bezel_disc": round(lens_disc / bezel_disc, 4),
        "lens_share_of_bezel_disc_batch_b": round(
            (LAMP_LENS_R_B ** 2) / (LAMP_BEZEL_OUTER ** 2), 4),
        "hood_arc_deg": LAMP_HOOD_ARC,
        "hood_arc_deg_batch_b": LAMP_HOOD_ARC_B,
        "hood_outer_radius_m": 0.0446,
        "hood_inner_radius_m": 0.0392,
        "hood_inside_bezel_outer": 0.0446 < LAMP_BEZEL_OUTER,
        "hood_clear_of_lens_mm": round((0.0392 - LAMP_LENS_R) * 1000.0, 2),
        "lens_proud_of_hood_mm": round((0.0500 - 0.0472) * 1000.0, 2),
        "shading": ("hood covers the upper 96 degrees only; the lens is open "
                    "to the sides and below"),
    }
    return body, indicator, [lens], audit


# ---------------------------------------------------------------------------
# StatusIndicator R1
# ---------------------------------------------------------------------------

# name, centre x, half width, half height, label. R1 gives the three wells one
# size and one spacing so the group centres on the base; the dark-state cue is
# position between the two ribs, not width. Batch B's three widths are kept
# here only so the JSON can quote what changed.
STATUS_SEGMENTS_B = bb.STATUS_SEGMENTS
STATUS_SEGMENTS = (
    ("status_safe", -0.0560, 0.0195, 0.0165, "SAFE"),
    ("status_warn", 0.0000, 0.0195, 0.0165, "WARN"),
    ("status_danger", 0.0560, 0.0195, 0.0165, "DANGER"),
)
STATUS_WELL_MARGIN = bb.STATUS_WELL_MARGIN
STATUS_HOOD_WIDTH = 0.1620       # Batch B: width - 0.030 = 0.1550


def build_status(material):
    """Batch B's status bar with the well group squared onto the base.

    Only the well/lens sizes, their centres and the hood's width move. The
    plate, gasket, shell, ribs-by-construction, nameplate, screws, register,
    the `indicator` empty and the SAFE / WARN / DANGER order and renderer
    split are Batch B's.
    """
    width, depth_env, height = bb.envelope_blender("StatusIndicator")
    plate_y = -0.0130
    face_y = -0.0380
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.010, height - 0.009)), 0.0014))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.024, height - 0.022),
                                (width - 0.024, height - 0.022)))
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - SHUT, face_y, (width - 0.006, height - 0.014),
        (width - 0.018, height - 0.026)), 0.0016))

    edges = []
    for name, cx, hw, hh, _ in STATUS_SEGMENTS:
        outer_w = 2.0 * (hw + STATUS_WELL_MARGIN)
        outer_h = 2.0 * (hh + STATUS_WELL_MARGIN)
        parts.append(p1.chamfer(p1.rect_frame(
            f"well_{name.split('_')[1]}", face_y + EMBED, face_y - 0.0034,
            (outer_w, outer_h),
            (2.0 * hw + 0.0052, 2.0 * hh + 0.0052),
            centre=(cx, 0.0)), 0.0010))
        edges.append((cx - outer_w / 2.0, cx + outer_w / 2.0))
    for index in range(len(edges) - 1):
        gap_lo, gap_hi = edges[index][1], edges[index + 1][0]
        centre = 0.5 * (gap_lo + gap_hi)
        thickness = min(0.0062, (gap_hi - gap_lo) - 0.0040)
        parts.append(p1.chamfer(p1.frustum_box(
            f"rib_{index}", face_y + EMBED, face_y - 0.0086,
            (thickness, 2.0 * 0.0165 + 0.0128),
            (thickness - 0.0012, 2.0 * 0.0165 + 0.0102),
            centre=(centre, 0.0)), 0.0012))
    parts.append(p1.chamfer(p1.frustum_box(
        "hood", face_y - 0.0030, face_y - 0.0104,
        (STATUS_HOOD_WIDTH, 0.0088), (STATUS_HOOD_WIDTH - 0.008, 0.0070),
        centre=(0.0, 0.0170 + 0.0102)), 0.0012))

    parts.append(p1.nameplate("plate_label", (0.0, -(height / 2.0 - 0.0125)),
                              (0.0520, 0.0106), plate_y - 0.0019, 0.0013))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.0115), sz * (height / 2.0 - 0.0115)),
                plate_y - 0.0015, 0.0052, 0.0038))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0026, 0.0100))

    audit = p3.coplanar_overlap_audit(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = "StatusIndicator_body"
    body.data.name = "StatusIndicator_body"
    p1.assign(body, material)

    indicator = bpy.data.objects.new("indicator", None)
    bpy.context.collection.objects.link(indicator)
    indicator.location = (0.0, 0.0, 0.0)
    indicator.rotation_mode = "XYZ"

    lenses = []
    for name, cx, hw, hh, _ in STATUS_SEGMENTS:
        lens = p1.chamfer(p1.frustum_box(
            name, face_y - 0.0006, face_y - 0.0074,
            (2.0 * hw, 2.0 * hh), (2.0 * hw - 0.0068, 2.0 * hh - 0.0068),
            centre=(cx, 0.0)), 0.0022)
        lens.name = name
        lens.data.name = name
        p1.assign(lens, material)
        lens.parent = indicator
        lenses.append(lens)

    group_lo = min(e[0] for e in edges)
    group_hi = max(e[1] for e in edges)
    audit["mechanism"] = {
        "indicator_is_empty_at_origin": True,
        "segment_meshes": [row[0] for row in STATUS_SEGMENTS],
        "segment_centres_m": [row[1] for row in STATUS_SEGMENTS],
        "segment_centres_batch_b_m": [row[1] for row in STATUS_SEGMENTS_B],
        "segment_half_widths_m": [row[2] for row in STATUS_SEGMENTS],
        "segment_half_widths_batch_b_m": [row[2] for row in STATUS_SEGMENTS_B],
        "well_group_x_m": [round(group_lo, 4), round(group_hi, 4)],
        "well_group_centre_mm": round(
            0.5 * (group_lo + group_hi) * 1000.0, 3),
        "hood_width_m": STATUS_HOOD_WIDTH,
        "hood_width_batch_b_m": round(width - 0.030, 4),
        "wells": 3, "ribs": len(STATUS_SEGMENTS) - 1, "hood": True,
        "states": CONTRACT["StatusIndicator"]["states"],
        "renderers": 1 + len(STATUS_SEGMENTS),
        "readability_trade": (
            "Batch B identified the lit segment by width as well as hue. "
            "311.5 asks for zero overhang past the base, and three different "
            "widths on a symmetric spacing cannot also be a symmetric group, "
            "so R1 makes the wells one size and leaves position between the "
            "two ribs as the non-colour cue. If the width coding was "
            "load-bearing, this is the line to reject."),
    }
    return body, indicator, lenses, audit


BUILDERS_B1 = {
    "Rotary": build_rotary,
    "Button": build_button,
    "Lamp": build_lamp,
    "StatusIndicator": build_status,
}


# ---------------------------------------------------------------------------
# evidence: geometry readers
# ---------------------------------------------------------------------------

def world_triangles(obj):
    """(N, 3, 3) world-space triangles for a mesh object."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = np.array(obj.matrix_world.transposed(), dtype=np.float64)
    verts = np.empty((len(mesh.vertices), 3), dtype=np.float64)
    mesh.vertices.foreach_get("co", verts.ravel())
    homogeneous = np.hstack([verts, np.ones((len(verts), 1))])
    world = (homogeneous @ matrix)[:, :3]
    index = np.empty((len(mesh.loop_triangles), 3), dtype=np.int64)
    mesh.loop_triangles.foreach_get("vertices", index.ravel())
    return world[index]


def capture_parts(builder, material):
    """Build, snapshotting every part's world triangles before the join."""
    captured = {}
    original_join = p1.join

    def hook(target, others):
        for obj in [target] + list(others):
            stem = obj.name.split(".")[0]
            captured.setdefault(stem, []).append(world_triangles(obj))
        return original_join(target, others)

    p1.join = hook
    try:
        body, mover, movers, audit = builder(material)
    finally:
        p1.join = original_join
    bpy.context.view_layer.update()
    return body, mover, movers, audit, {
        name: np.concatenate(rows) for name, rows in captured.items()}


# ---------------------------------------------------------------------------
# evidence: 311.2 / 311.3 finger proxy
# ---------------------------------------------------------------------------

def _closest_on_triangles(tris, point):
    """Closest point on each triangle to `point`; Ericson's region test."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac, ap = b - a, c - a, point - a
    d1 = np.einsum("ij,ij->i", ab, ap)
    d2 = np.einsum("ij,ij->i", ac, ap)
    bp = point - b
    d3 = np.einsum("ij,ij->i", ab, bp)
    d4 = np.einsum("ij,ij->i", ac, bp)
    cp = point - c
    d5 = np.einsum("ij,ij->i", ab, cp)
    d6 = np.einsum("ij,ij->i", ac, cp)
    vc = d1 * d4 - d3 * d2
    vb = d5 * d2 - d1 * d6
    va = d3 * d6 - d5 * d4
    denom = va + vb + vc
    safe = np.where(np.abs(denom) < 1e-20, 1.0, denom)
    v = np.clip(vb / safe, 0.0, 1.0)
    w = np.clip(vc / safe, 0.0, 1.0)
    out = a + v[:, None] * ab + w[:, None] * ac

    def edge(p0, dvec, t):
        return p0 + np.clip(t, 0.0, 1.0)[:, None] * dvec

    region_a = (d1 <= 0) & (d2 <= 0)
    region_b = (d3 >= 0) & (d4 <= d3)
    region_c = (d6 >= 0) & (d5 <= d6)
    ab_edge = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    ac_edge = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    bc_edge = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    out = np.where(bc_edge[:, None],
                   edge(b, c - b, (d4 - d3) / np.where(
                       np.abs((d4 - d3) + (d5 - d6)) < 1e-20, 1.0,
                       (d4 - d3) + (d5 - d6))), out)
    out = np.where(ac_edge[:, None],
                   edge(a, ac, d2 / np.where(np.abs(d2 - d6) < 1e-20, 1.0,
                                             d2 - d6)), out)
    out = np.where(ab_edge[:, None],
                   edge(a, ab, d1 / np.where(np.abs(d1 - d3) < 1e-20, 1.0,
                                             d1 - d3)), out)
    out = np.where(region_c[:, None], c, out)
    out = np.where(region_b[:, None], b, out)
    out = np.where(region_a[:, None], a, out)
    return out


def sphere_hits(tris, centre, radius):
    """Triangles of `tris` that the sphere intersects, and the nearest surface.

    The second return is the distance from the sphere's *centre* to the
    nearest triangle, so clearance is that minus the radius and contact is
    that equal to the radius.
    """
    centre = np.asarray(centre, dtype=np.float64)
    closest = _closest_on_triangles(tris, centre)
    distance = np.linalg.norm(closest - centre, axis=1)
    return int(np.count_nonzero(distance < radius)), float(distance.min())


FINGER_LENGTH = 0.040             # the finger behind the pad, not just the pad


def capsule_hits(tris, tip, direction, length=FINGER_LENGTH,
                 radius=FINGER_RADIUS, step=0.001):
    """A 16 mm finger: the pad sphere swept `length` back along -direction.

    Sampled at 1 mm, which over-reports clearance by at most
    radius - sqrt(radius**2 - (step/2)**2) = 0.016 mm. A bare sphere cannot
    fail a guard whose bore is 79 mm wide, so the finger behind the pad is
    what makes the test mean anything.
    """
    tip = np.asarray(tip, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    direction = direction / np.linalg.norm(direction)
    count, nearest = 0, float("inf")
    samples = int(round(length / step)) + 1
    for index in range(samples):
        centre = tip - direction * (index * step)
        hits, distance = sphere_hits(tris, centre, radius)
        count += hits
        nearest = min(nearest, distance)
    return count, nearest


def seat_capsule(tris, origin, direction, reach, steps=40):
    """Push the finger in along `direction` until its pad touches `tris`."""
    origin = np.asarray(origin, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    direction = direction / np.linalg.norm(direction)
    _, far = sphere_hits(tris, origin + direction * float(reach),
                         FINGER_RADIUS)
    if far >= FINGER_RADIUS:
        return origin, float("inf")
    lo, hi = 0.0, float(reach)
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        _, distance = sphere_hits(tris, origin + direction * mid,
                                  FINGER_RADIUS)
        if distance < FINGER_RADIUS:
            hi = mid
        else:
            lo = mid
    tip = origin + direction * lo
    _, distance = sphere_hits(tris, tip, FINGER_RADIUS)
    return tip, float(distance)


def seat_proxy(tris, origin, direction, reach, radius, steps=44):
    """Slide a sphere in from `origin` along `direction` until it touches.

    `origin` is outside the surface and `origin + direction * reach` is inside
    it, so the touching offset is the boundary between the two and bisection
    finds it. The proxy is placed where a finger pad would actually land
    rather than at an assumed radius, which is what caught the rotary's flute
    valleys: at theta 0 the flank is a valley, 3.2 mm under the crest.
    """
    origin = np.asarray(origin, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    direction = direction / np.linalg.norm(direction)
    _, far = sphere_hits(tris, origin + direction * float(reach), radius)
    if far >= radius:
        return origin, float("inf")          # the sweep never reaches it
    lo, hi = 0.0, float(reach)               # lo clear, hi inside
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        _, distance = sphere_hits(tris, origin + direction * mid, radius)
        if distance < radius:
            hi = mid
        else:
            lo = mid
    centre = origin + direction * lo
    _, distance = sphere_hits(tris, centre, radius)
    return centre, float(distance)


def rotary_finger_audit(body, knob, collar_y=None):
    """311.2: a 16 mm finger pad on each flank of the knob.

    The proxy is placed touching the flute crests, at the mid height of the
    grip band, on -X and +X. It has to clear the collar entirely.
    """
    collar_y = ROTARY_COLLAR_Y if collar_y is None else collar_y
    body_tris = world_triangles(body)
    knob_tris = world_triangles(knob)
    grip_lo_y = bb.ROTARY_PIVOT_Y - 0.0148
    grip_hi_y = bb.ROTARY_PIVOT_Y - 0.0086
    grip_mid_y = 0.5 * (grip_lo_y + grip_hi_y)
    crest_r = 0.0418

    sides = {}
    for label, sign in (("left", -1.0), ("right", 1.0)):
        # Come in from outside on the flank and stop on the knob's surface,
        # whatever the flute phase at that angle happens to be.
        centre, knob_gap = seat_proxy(
            knob_tris, (sign * (crest_r + 4.0 * FINGER_RADIUS), grip_mid_y, 0.0),
            (-sign, 0.0, 0.0), 4.0 * FINGER_RADIUS, FINGER_RADIUS)
        body_count, body_gap = sphere_hits(body_tris, centre, FINGER_RADIUS)
        knob_count, _ = sphere_hits(knob_tris, centre, FINGER_RADIUS)
        finger_count, finger_gap = capsule_hits(body_tris, centre,
                                                (-sign, 0.0, 0.0))
        sides[label] = {
            "finger_triangle_intersections": finger_count,
            "finger_clearance_to_guard_mm": round(
                (finger_gap - FINGER_RADIUS) * 1000.0, 2),
            "proxy_centre_m": [round(float(v), 4) for v in centre],
            "proxy_seated_radius_m": round(float(abs(centre[0])), 4),
            "guard_triangle_intersections": body_count,
            "clearance_to_guard_mm": round(
                (body_gap - FINGER_RADIUS) * 1000.0, 2),
            "contact_gap_to_knob_mm": round(
                (knob_gap - FINGER_RADIUS) * 1000.0, 3),
            "touches_knob": abs(knob_gap - FINGER_RADIUS) <= 0.0004,
            "knob_triangle_intersections": knob_count,
        }

    # Grippable side height: the axial run of knob surface at radius >= the
    # flute valley that stands in front of the collar's front plane.
    valley_r = crest_r - 0.0032
    radial = np.linalg.norm(knob_tris[:, :, [0, 2]], axis=2)
    side_y = knob_tris[:, :, 1][radial >= valley_r]
    proud = side_y[side_y <= collar_y]
    return {
        "proxy_diameter_mm": FINGER_DIAMETER * 1000.0,
        "collar_front_y_m": collar_y,
        "collar_bore_radius_m": 0.0472,
        "grip_band_y_m": [round(grip_hi_y, 4), round(grip_lo_y, 4)],
        "grip_band_crest_radius_m": crest_r,
        "grip_band_valley_radius_m": round(valley_r, 4),
        "annulus_collar_to_crest_mm": round((0.0472 - crest_r) * 1000.0, 2),
        "grippable_side_height_mm": round(
            (float(side_y.max()) - float(side_y.min())) * 1000.0, 2),
        "grippable_side_height_proud_of_collar_mm": round(
            (collar_y - float(proud.min())) * 1000.0, 2)
        if proud.size else 0.0,
        "sides": sides,
        "finger_length_mm": FINGER_LENGTH * 1000.0,
        "clean": all(row["guard_triangle_intersections"] == 0
                     and row["finger_triangle_intersections"] == 0
                     and row["touches_knob"] for row in sides.values()),
    }


def button_finger_audit(body, button, travel, guard_y=None):
    """311.3: a 16 mm finger pad on the press axis, at rest and pressed."""
    guard_y = BUTTON_GUARD_Y if guard_y is None else guard_y
    body_tris = world_triangles(body)
    poses = {}
    for label, value in (("rest", 0.0), ("pressed", bb.BUTTON_TRAVEL)):
        bb.apply_pose(travel, "Button", value)
        bpy.context.view_layer.update()
        cap_tris = world_triangles(button)
        crown_y = float(cap_tris[:, :, 1].min())
        # Down the press axis from 60 mm out, stopping on the cap - the crown
        # is dished, so the contact is the dish rim, not the axis point.
        centre, cap_gap = seat_proxy(
            cap_tris, (0.0, crown_y - 0.0600, 0.0), (0.0, 1.0, 0.0),
            0.0600, FINGER_RADIUS)
        guard_count, guard_gap = sphere_hits(body_tris, centre, FINGER_RADIUS)
        cap_count, _ = sphere_hits(cap_tris, centre, FINGER_RADIUS)
        poses[label] = {
            "crown_y_m": round(crown_y, 4),
            "proxy_centre_m": [0.0, round(float(centre[1]), 4), 0.0],
            "pad_stands_proud_of_crown_mm": round(
                (crown_y - float(centre[1])) * 1000.0, 2),
            "guard_triangle_intersections": guard_count,
            "clearance_to_guard_mm": round(
                (guard_gap - FINGER_RADIUS) * 1000.0, 2),
            "contact_gap_to_cap_mm": round(
                (cap_gap - FINGER_RADIUS) * 1000.0, 3),
            "touches_cap": abs(cap_gap - FINGER_RADIUS) <= 0.0004,
            "cap_triangle_intersections": cap_count,
        }
    # Off-axis approaches, which is how a finger actually arrives: the pad
    # comes in from below at 30 / 45 / 60 degrees to the press axis with the
    # rest of the finger behind it.
    bb.apply_pose(travel, "Button", 0.0)
    bpy.context.view_layer.update()
    cap_tris = world_triangles(button)
    crown_y = float(cap_tris[:, :, 1].min())
    oblique = {}
    for degrees in (0.0, 30.0, 45.0, 60.0):
        angle = math.radians(degrees)
        direction = np.array([0.0, math.cos(angle), math.sin(angle)])
        origin = np.array([0.0, crown_y, 0.0]) - direction * 0.0600
        tip, gap = seat_capsule(cap_tris, origin, direction, 0.0600)
        if not math.isfinite(gap):
            oblique[f"{int(degrees)}deg"] = {"reaches_cap": False}
            continue
        count, nearest = capsule_hits(body_tris, tip, direction)
        oblique[f"{int(degrees)}deg"] = {
            "reaches_cap": True,
            "tip_m": [round(float(v), 4) for v in tip],
            "guard_triangle_intersections": count,
            "clearance_to_guard_mm": round(
                (nearest - FINGER_RADIUS) * 1000.0, 2),
        }

    # What the guard actually costs the cap: how much of it stands in front
    # of the guard rim. This is the number that moved, and the one that
    # matches what the headset showed - a 16 mm pad on a 79 mm bore was never
    # physically blocked at either guard height.
    exposure = {}
    for label, value in (("rest", 0.0), ("pressed", bb.BUTTON_TRAVEL)):
        bb.apply_pose(travel, "Button", value)
        bpy.context.view_layer.update()
        tris = world_triangles(button)
        front = float(tris[:, :, 1].min())
        radial = np.linalg.norm(tris[:, :, [0, 2]], axis=2)
        flank = tris[:, :, 1][radial >= 0.0200]
        exposure[label] = {
            "cap_front_y_m": round(front, 4),
            "cap_proud_of_guard_mm": round((guard_y - front) * 1000.0, 2),
            "cap_flank_proud_of_guard_mm": round(
                (guard_y - float(flank.min())) * 1000.0, 2),
        }
    bb.apply_pose(travel, "Button", 0.0)
    bpy.context.view_layer.update()

    return {
        "proxy_diameter_mm": FINGER_DIAMETER * 1000.0,
        "finger_length_mm": FINGER_LENGTH * 1000.0,
        "guard_front_y_m": guard_y,
        "guard_inner_radius_m": 0.0396,
        "guard_proud_of_bezel_face_mm": round((-0.0430 - guard_y) * 1000.0, 2),
        "travel_mm": bb.BUTTON_TRAVEL * 1000.0,
        "poses": poses,
        "oblique_approach": oblique,
        "cap_exposure": exposure,
        "finding": (
            "a 16 mm pad on the press axis clears a 79 mm bore at both guard "
            "heights, so 311.3's axial test passes on Batch B too; what "
            "changed is the cap's exposure in front of the guard rim, 10.8 mm "
            "to 20.4 mm at rest"),
        "clean": all(row["guard_triangle_intersections"] == 0
                     and row["touches_cap"] for row in poses.values())
        and all(row.get("reaches_cap") and
                row.get("guard_triangle_intersections") == 0
                for row in oblique.values())
        and exposure["rest"]["cap_proud_of_guard_mm"]
        >= round((-0.0430 - guard_y) * 1000.0, 2),
    }


# ---------------------------------------------------------------------------
# evidence: orthographic id / depth raster, for visible area and silhouettes
# ---------------------------------------------------------------------------

def view_basis(view):
    """The camera basis p1.camera_at builds, as (forward, right, up)."""
    azimuth, elevation = math.radians(view[0]), math.radians(view[1])
    camera = np.array([math.sin(azimuth) * math.cos(elevation),
                       -math.cos(azimuth) * math.cos(elevation),
                       math.sin(elevation)])
    forward = -camera / np.linalg.norm(camera)
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(forward, world_up)
    if np.linalg.norm(right) < 1e-9:
        right = np.array([1.0, 0.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    return forward, right, up


def id_raster(groups, view, focus, half_extent, grid=640):
    """Orthographic z-buffer over `groups`; returns the winning group index.

    -1 is empty. One pixel is `2 * half_extent / grid` metres square, which is
    what turns a pixel count into an area.
    """
    forward, right, up = view_basis(view)
    focus = np.asarray(focus, dtype=np.float64)
    ids = np.full((grid, grid), -1, dtype=np.int16)
    depth = np.full((grid, grid), np.inf, dtype=np.float64)
    scale = grid / (2.0 * half_extent)

    for index, (_, tris) in enumerate(groups):
        if tris is None or len(tris) == 0:
            continue
        local = tris - focus
        u = np.einsum("ijk,k->ij", local, right) * scale + grid / 2.0
        v = np.einsum("ijk,k->ij", local, up) * scale + grid / 2.0
        d = np.einsum("ijk,k->ij", local, forward)
        for tri in range(u.shape[0]):
            x0 = max(int(np.floor(u[tri].min())), 0)
            x1 = min(int(np.ceil(u[tri].max())) + 1, grid)
            y0 = max(int(np.floor(v[tri].min())), 0)
            y1 = min(int(np.ceil(v[tri].max())) + 1, grid)
            if x1 <= x0 or y1 <= y0:
                continue
            ax, ay = u[tri, 0], v[tri, 0]
            bx, by = u[tri, 1], v[tri, 1]
            cx, cy = u[tri, 2], v[tri, 2]
            area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay)
            if abs(area) < 1e-12:
                continue
            px = np.arange(x0, x1) + 0.5
            py = np.arange(y0, y1) + 0.5
            gx, gy = np.meshgrid(px, py)
            w0 = ((bx - ax) * (gy - ay) - (gx - ax) * (by - ay)) / area
            w1 = ((gx - ax) * (cy - ay) - (cx - ax) * (gy - ay)) / area
            w2 = 1.0 - w0 - w1
            inside = (w0 >= 0.0) & (w1 >= 0.0) & (w2 >= 0.0)
            if not inside.any():
                continue
            z = w2 * d[tri, 0] + w1 * d[tri, 1] + w0 * d[tri, 2]
            window_d = depth[y0:y1, x0:x1]
            window_i = ids[y0:y1, x0:x1]
            better = inside & (z < window_d)
            window_d[better] = z[better]
            window_i[better] = index
    return ids


def visible_areas(groups, view, focus, half_extent, grid=640):
    ids = id_raster(groups, view, focus, half_extent, grid)
    pixel_mm2 = (2.0 * half_extent / grid * 1000.0) ** 2
    counts = {name: int(np.count_nonzero(ids == index))
              for index, (name, _) in enumerate(groups)}
    return ids, {name: round(count * pixel_mm2, 2)
                 for name, count in counts.items()}, counts


def silhouette_mask(tris, view, focus, half_extent, grid=640):
    return id_raster([("x", tris)], view, focus, half_extent, grid) >= 0


def save_overlay(before, after, path):
    """Batch B in red, R1 in green, both in grey; PNG through the p1 writer."""
    import opus5_brushup_kinetic_review as review
    grid = before.shape[0]
    canvas = np.zeros((grid, grid, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    canvas[..., :3] = 0.07
    both = before & after
    canvas[before & ~after] = (0.86, 0.16, 0.18, 1.0)
    canvas[after & ~before] = (0.20, 0.82, 0.34, 1.0)
    canvas[both] = (0.62, 0.62, 0.62, 1.0)
    review.save_rgba(np.flipud(canvas), path)


# ---------------------------------------------------------------------------
# evidence: 311.4 lamp proportion, 311.5 status overhang
# ---------------------------------------------------------------------------

LAMP_VIEWS = {"front": (0.0, 0.0), "oblique_left": (-38.0, 18.0),
              "oblique_right": (38.0, 18.0)}


def lamp_proportion_audit(parts, lens, focus, half_extent, grid=640,
                          lens_radius=None, bezel_radius=None):
    """311.4: is the lens or the guard the subject, from front and obliques."""
    guard = np.concatenate([parts[name] for name in ("bezel", "hood")])
    rest = np.concatenate([tris for name, tris in parts.items()
                           if name not in ("bezel", "hood")])
    lens_tris = world_triangles(lens)
    groups = [("lens", lens_tris), ("guard", guard), ("body", rest)]

    rows = {}
    for label, view in LAMP_VIEWS.items():
        ids, areas, counts = visible_areas(groups, view, focus, half_extent,
                                           grid)
        lens_alone = silhouette_mask(lens_tris, view, focus, half_extent, grid)
        occluded = int(np.count_nonzero(lens_alone & (ids == 1)))
        lit = counts["lens"]
        rows[label] = {
            "visible_area_mm2": areas,
            "lens_over_guard": round(lit / counts["guard"], 3)
            if counts["guard"] else None,
            "lens_share_of_instrument": round(
                lit / max(sum(counts.values()), 1), 4),
            "lens_outline_px": int(np.count_nonzero(lens_alone)),
            "lens_outline_px_hidden_by_guard": occluded,
            "lens_outline_hidden_pct": round(
                100.0 * occluded / max(int(np.count_nonzero(lens_alone)), 1),
                2),
        }
    return {
        "views": rows,
        "lens_radius_m": LAMP_LENS_R if lens_radius is None else lens_radius,
        "bezel_outer_radius_m": (LAMP_BEZEL_OUTER if bezel_radius is None
                                 else bezel_radius),
        "clean": all(row["lens_over_guard"] is not None
                     and row["lens_over_guard"] > 1.0
                     and row["lens_outline_hidden_pct"] < 5.0
                     for row in rows.values()),
    }


def status_alignment_audit(parts, lenses, focus, half_extent, grid=640):
    """311.5: base, frame and lens numbers, and front-projection overhang."""

    def extent(tris, axis):
        return float(tris[:, :, axis].min()), float(tris[:, :, axis].max())

    shell = parts["shell"]
    plate = parts["plate"]
    # The shell's front face, which is what the wells actually stand on: the
    # frontmost 0.3 mm of it, after the draft and the chamfer.
    front_y = float(shell[:, :, 1].min())
    near = shell.reshape(-1, 3)
    near = near[near[:, 1] <= front_y + 0.0003]
    face_x = (float(near[:, 0].min()), float(near[:, 0].max()))
    face_z = (float(near[:, 2].min()), float(near[:, 2].max()))
    plate_x = extent(plate, 0)

    frame_names = [n for n in parts
                   if n.startswith(("well_", "rib_")) or n == "hood"]
    frame = np.concatenate([parts[n] for n in frame_names])
    frame_x = extent(frame, 0)
    frame_z = extent(frame, 2)

    rows = {}
    for name in sorted(frame_names):
        lo, hi = extent(parts[name], 0)
        rows[name] = {
            "x_m": [round(lo, 4), round(hi, 4)],
            "centre_mm": round(0.5 * (lo + hi) * 1000.0, 3),
            "margin_to_shell_face_left_mm": round((lo - face_x[0]) * 1000.0, 2),
            "margin_to_shell_face_right_mm": round((face_x[1] - hi) * 1000.0, 2),
        }
    for lens in lenses:
        tris = world_triangles(lens)
        lo, hi = extent(tris, 0)
        zlo, zhi = extent(tris, 2)
        rows[lens.name] = {
            "x_m": [round(lo, 4), round(hi, 4)],
            "centre_mm": round(0.5 * (lo + hi) * 1000.0, 3),
            "z_centre_mm": round(0.5 * (zlo + zhi) * 1000.0, 3),
            "margin_to_shell_face_left_mm": round((lo - face_x[0]) * 1000.0, 2),
            "margin_to_shell_face_right_mm": round((face_x[1] - hi) * 1000.0, 2),
        }

    # Front-projection overhang, rasterised: frame pixels that fall outside
    # the base's own front silhouette.
    view = (0.0, 0.0)
    base = np.concatenate([plate, shell])
    base_mask = silhouette_mask(base, view, focus, half_extent, grid)
    # Not the shell's silhouette - the shell is drafted, so its silhouette is
    # the *back* of it. The wells stand on the front face, so that rectangle
    # is what they may not hang off, and it is 12 mm narrower.
    corners = np.array([[face_x[0], front_y, face_z[0]],
                        [face_x[1], front_y, face_z[0]],
                        [face_x[1], front_y, face_z[1]],
                        [face_x[0], front_y, face_z[1]]])
    face_quad = np.array([corners[[0, 1, 2]], corners[[0, 2, 3]]])
    face_mask = silhouette_mask(face_quad, view, focus, half_extent, grid)
    frame_mask = silhouette_mask(frame, view, focus, half_extent, grid)
    lens_mask = silhouette_mask(
        np.concatenate([world_triangles(o) for o in lenses]),
        view, focus, half_extent, grid)
    pixel_mm2 = (2.0 * half_extent / grid * 1000.0) ** 2
    outside_plate = int(np.count_nonzero(frame_mask & ~base_mask))
    outside_shell = int(np.count_nonzero(frame_mask & ~face_mask))
    lens_outside = int(np.count_nonzero(lens_mask & ~face_mask))

    return {
        "shell_front_face_x_m": [round(face_x[0], 4), round(face_x[1], 4)],
        "shell_front_face_z_m": [round(face_z[0], 4), round(face_z[1], 4)],
        "plate_x_m": [round(plate_x[0], 4), round(plate_x[1], 4)],
        "frame_group_x_m": [round(frame_x[0], 4), round(frame_x[1], 4)],
        "frame_group_z_m": [round(frame_z[0], 4), round(frame_z[1], 4)],
        "frame_group_centre_mm": round(
            0.5 * (frame_x[0] + frame_x[1]) * 1000.0, 3),
        "frame_margin_left_mm": round((frame_x[0] - face_x[0]) * 1000.0, 2),
        "frame_margin_right_mm": round((face_x[1] - frame_x[1]) * 1000.0, 2),
        "parts": rows,
        "shell_silhouette_note": (
            "overhang is measured against the shell's front face rectangle, not its drafted silhouette"),
        "front_projection_overhang_past_shell_face_mm2": round(
            outside_shell * pixel_mm2, 2),
        "front_projection_overhang_past_plate_mm2": round(
            outside_plate * pixel_mm2, 2),
        "lens_overhang_past_shell_face_mm2": round(
            lens_outside * pixel_mm2, 2),
        "clean": outside_shell == 0 and outside_plate == 0
        and lens_outside == 0,
    }
