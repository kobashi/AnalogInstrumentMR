"""Theme 4 Phase 3 Batch C: WindowMeter, WindowPanel, TrendMonitor.

The three Machined Ergonomics instruments that were never built. 325 fixes
their runtime contract, their bounds and their budgets; everything else is the
language the eleven accepted instruments already established - a mount plate
with a gasket line, a drafted shell, thin machined rings rather than thick
lips, anodized metal on the service features, dark elastomer where a hand or a
seal lands, and a scale whose major and minor marks differ in length, width
and depth rather than only in spacing.

Two things here are new to this theme and are worth stating plainly.

The window instruments are the first at architectural size - 1.2 and 1.6 m
across - so the detail that reads at 0.15 m on a rotary knob is invisible on
them and the detail that reads at 2 m would look coarse on everything else.
The scale rings, the ring sections and the fastener sizes are therefore driven
from the instrument's own diameter rather than copied, and the flanks carry
their own secondary scales so a 1.2 m panel is not one dial and a lot of
blank.

The trend monitor is not an analog instrument at all: its `display_surface` is
a real flat plane that runtime numbers and a LineRenderer have to sit on. It
is a thin closed slab rather than a bare quad - an open quad's four edges are
all non-manifold and the gate counts them - and its front face is the plane,
carrying no glass, no curvature and no bezel geometry across it.
"""

import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_full_p6_batch_b as bb

SHUT = bb.SHUT
EMBED = bb.EMBED
NEUTRAL = bb.NEUTRAL
revolve = bb.revolve

VALIDATOR_TOTAL = 25000           # 325.5, the formal budget for these kinds

CONTRACT = {
    "WindowMeter": {
        "kind": "WindowMeter",
        "motion_target": "needle_pivot", "movable": "needle",
        "pivot": "needle_pivot", "moving": "needle",
        "meshes": ["WindowMeter_body", "needle"],
        "envelope_unity_xyz": (1.20, 0.75, 0.202),
        "renderer_budget": 4, "triangle_budget_total": VALIDATOR_TOTAL,
        "triangle_target_total": 8000,
        "unity_axis": "+Z", "blender_axis": "Y",
        "motion": "rotate", "amplitude_deg": 55.0, "offset_deg": 0.0,
        "unity_range_deg": (-55.0, 55.0),
        "blender_range_deg": (-55.0, 55.0),
    },
    "WindowPanel": {
        "kind": "WindowPanel",
        "motion_target": "vane_pivot", "movable": "vane",
        "pivot": "vane_pivot", "moving": "vane",
        "meshes": ["WindowPanel_body", "vane"],
        "envelope_unity_xyz": (1.60, 0.90, 0.22),
        "renderer_budget": 4, "triangle_budget_total": VALIDATOR_TOTAL,
        "triangle_target_total": 8000,
        "unity_axis": "+Z", "blender_axis": "Y",
        "motion": "rotate", "amplitude_deg": 42.0, "offset_deg": 0.0,
        "unity_range_deg": (-42.0, 42.0),
        "blender_range_deg": (-42.0, 42.0),
    },
    "TrendMonitor": {
        "kind": "TrendMonitor",
        "motion_target": "display_surface", "movable": "display_surface",
        "pivot": "display_surface", "moving": "display_surface",
        "meshes": ["TrendMonitor_body", "display_surface"],
        "envelope_unity_xyz": (0.44, 0.28, 0.10),
        "renderer_budget": 3, "triangle_budget_total": VALIDATOR_TOTAL,
        "triangle_target_total": 4000,
        "unity_axis": "+Z", "blender_axis": "Y",
        "motion": "none", "amplitude_deg": 0.0, "offset_deg": 0.0,
        "unity_range_deg": (0.0, 0.0), "blender_range_deg": (0.0, 0.0),
    },
}

# 325.4. Blender authors with the mount plane at max Y == 0 and the front at
# -Y; the import path turns -Y into Unity +Z and +Z into Unity +Y, which is
# the convention all eleven accepted instruments were measured against.
DISPLAY_MIN_M = (0.36, 0.18)
DISPLAY_NORMAL_BLENDER = (0.0, -1.0, 0.0)
DISPLAY_UP_BLENDER = (0.0, 0.0, 1.0)


def envelope_blender(asset):
    """Unity (x, y, z) -> Blender (width X, depth Y, height Z)."""
    x, y, z = CONTRACT[asset]["envelope_unity_xyz"]
    return x, z, y


def scale_arc(prefix, centre, sweep_deg, majors, minors_per_major,
              r_major_in, r_minor_in, r_out, w_major, w_minor,
              y_near, y_major_far, y_minor_far, up_deg=90.0):
    """A major/minor scale, unique in length, width and depth at once.

    Three differences rather than one: a minor mark is shorter, narrower and
    shallower than a major. On a 1.2 m instrument read from two metres, any
    one of those alone disappears.
    """
    parts = []
    total = majors * minors_per_major
    cx, cz = centre
    for index in range(total + 1):
        fraction = index / total
        angle = up_deg + sweep_deg * (fraction - 0.5)
        major = index % minors_per_major == 0
        tick = p1.radial_tick(
            f"tick_{index}", angle,
            r_major_in if major else r_minor_in, r_out,
            w_major if major else w_minor,
            y_near, y_major_far if major else y_minor_far)
        tick.location = (cx, 0.0, cz)
        parts.append(tick)
    return parts


def taper_blade(name, r0, r1, w0, w1, y_near, y_far, angle_deg=90.0,
                centre=(0.0, 0.0)):
    """A pointer that narrows towards its tip, as eight placed corners.

    frustum_box tapers in depth but not along its own length, and a needle
    that is the same width at the hub and at the tip reads as a bar. The
    corners are placed directly, the same way radial_tick does it.
    """
    angle = math.radians(angle_deg)
    ca, sa = math.cos(angle), math.sin(angle)
    cx, cz = centre
    verts = []
    for y in (y_near, y_far):
        for radius, half, side in ((r0, w0 / 2.0, -1.0), (r0, w0 / 2.0, 1.0),
                                   (r1, w1 / 2.0, 1.0), (r1, w1 / 2.0, -1.0)):
            verts.append((cx + radius * ca - side * half * sa, y,
                          cz + radius * sa + side * half * ca))
    faces = [(0, 1, 2, 3), (7, 6, 5, 4),
             (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return p3._emit(name, verts, faces, False)


# ---------------------------------------------------------------------------
# WindowMeter
# ---------------------------------------------------------------------------

WM_DIAL_R = 0.280                 # bezel bore
WM_RING_OUTER = 0.316
WM_FACE_Y = -0.0820
WM_DIAL_FACE = -0.1000            # dial floor, 18 mm proud of the shell face
WM_RING_FRONT = -0.1420
WM_PIVOT_Y = -0.1100


def build_window_meter(material):
    """A 1.2 m landscape meter: one deep dial, two flank scales.

    At this size a single centred dial leaves a quarter of a square metre of
    blank panel either side, so the flanks carry their own secondary scales
    and the service features are sized from the instrument rather than copied
    off a 0.15 m knob.
    """
    width, depth_env, height = envelope_blender("WindowMeter")
    plate_y = -0.0180
    face_y = WM_FACE_Y
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.020, height - 0.020)), 0.0026))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.044, height - 0.044),
                                (width - 0.044, height - 0.044)))
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - SHUT, face_y, (width - 0.016, height - 0.016),
        (width - 0.052, height - 0.052)), 0.0034))

    # Dial pan, then the thin ring that frames it.
    # The dial is a drum standing proud of the shell, not a well cut into it:
    # this family has no booleans, so a "recess" in a solid shell would leave
    # the needle inside the shell's own volume. The first build did exactly
    # that and the needle pushed out through the front face.
    parts.append(revolve("dial_pan", [
        (0.0000, face_y + 0.0030),
        (0.3025, face_y + 0.0030),
        (0.3025, WM_DIAL_FACE + 0.0056),
        (0.2985, WM_DIAL_FACE),
        (0.0000, WM_DIAL_FACE),
    ], segments=64, axis="y", smooth=False))
    parts.append(revolve("bezel_ring", [
        (WM_DIAL_R, face_y + 0.0030),
        (WM_DIAL_R, WM_RING_FRONT + 0.0055),
        (WM_DIAL_R + 0.0075, WM_RING_FRONT),
        (WM_RING_OUTER - 0.0075, WM_RING_FRONT),
        (WM_RING_OUTER, WM_RING_FRONT + 0.0055),
        (WM_RING_OUTER, face_y + 0.0030),
    ], segments=64, axis="y", smooth=False))

    parts.extend(scale_arc(
        "tick", (0.0, 0.0), 110.0, 11, 4,
        0.2060, 0.2340, 0.2680, 0.0090, 0.0046,
        WM_DIAL_FACE + EMBED, WM_DIAL_FACE - 0.0075,
        WM_DIAL_FACE - 0.0055))

    # Flank scales: the same major/minor rule, laid out linearly.
    for sign in (-1.0, 1.0):
        cx = sign * 0.4300
        parts.append(p1.chamfer(p1.frustum_box(
            f"scale_strip_{int(sign)}", face_y + EMBED, face_y - 0.0090,
            (0.1120, 0.5240), (0.1040, 0.5160), centre=(cx, 0.0300)), 0.0022))
        for index in range(13):
            major = index % 4 == 0
            z = 0.0300 - 0.2360 + 0.4720 * index / 12.0
            parts.append(p1.frustum_box(
                f"tick_flank_{int(sign)}_{index}",
                face_y - 0.0090 + EMBED, face_y - 0.0126 if major
                else face_y - 0.0112,
                (0.0700 if major else 0.0420, 0.0104 if major else 0.0062),
                (0.0680 if major else 0.0408, 0.0092 if major else 0.0054),
                centre=(cx - (0.0140 if major else 0.0280), z)))

    parts.append(p1.nameplate("plate_label", (-0.4300, -0.3180),
                              (0.2200, 0.0480), face_y - 0.0028, 0.0034))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * 0.5480, sz * 0.3230), face_y, 0.0120, 0.0090))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0044, 0.0180))

    audit = p3.coplanar_overlap_audit(parts)
    bpy.context.view_layer.update()
    body = p1.join(parts[0], parts[1:])
    body.name = "WindowMeter_body"
    body.data.name = "WindowMeter_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("needle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, WM_PIVOT_Y, 0.0)
    pivot.rotation_mode = "XYZ"

    blade = taper_blade("needle_blade", 0.0260, 0.2520, 0.0230, 0.0072,
                        0.0000, -0.0110)
    hub = revolve("needle_hub", [
        (0.0000, 0.0038),
        (0.0430, 0.0038),
        (0.0430, -0.0106),
        (0.0330, -0.0166),
        (0.0000, -0.0166),
    ], segments=32, axis="y", smooth=False)
    needle = p1.join(blade, [hub])
    needle.name = "needle"
    needle.data.name = "needle"
    p1.assign(needle, material)
    needle.parent = pivot

    audit["mechanism"] = {
        "dial_bore_m": WM_DIAL_R,
        "ring_outer_m": WM_RING_OUTER,
        "ring_section_mm": round((WM_RING_OUTER - WM_DIAL_R) * 1000.0, 1),
        "ring_proud_of_face_mm": round((face_y - WM_RING_FRONT) * 1000.0, 1),
        "dial_proud_of_face_mm": round((face_y - WM_DIAL_FACE) * 1000.0, 1),
        "needle_behind_ring_rim_mm": round(
            (WM_PIVOT_Y - 0.0110 - WM_RING_FRONT) * -1000.0, 1),
        "needle_length_mm": 252.0,
        "needle_tip_inside_bore_mm": round((WM_DIAL_R - 0.2520) * 1000.0, 1),
        "scale": {"sweep_deg": 110.0, "majors": 11, "minors_per_major": 4,
                  "major_longer_mm": round((0.2340 - 0.2060) * 1000.0, 1),
                  "major_wider_mm": round((0.0090 - 0.0046) * 1000.0, 1),
                  "major_deeper_mm": 2.0},
        "flank_scales": 2,
    }
    return body, pivot, [needle], audit


# ---------------------------------------------------------------------------
# WindowPanel
# ---------------------------------------------------------------------------

WP_FACE_Y = -0.0900
WP_FIELD_FACE = -0.1080           # field floor, 18 mm proud of the shell face
WP_RING_FRONT = -0.1360
WP_PIVOT_Y = -0.1200
WP_PIVOT_Z = -0.1500


def build_window_panel(material):
    """A 1.6 m information field with a single swinging vane.

    The field is a recess rather than a raised pad, so the vane runs inside
    the panel and the rails either side stand proud of it - a hand sliding
    along the hull meets the rail, not the vane.
    """
    width, depth_env, height = envelope_blender("WindowPanel")
    plate_y = -0.0200
    face_y = WP_FACE_Y
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.024, height - 0.024)), 0.0030))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.052, height - 0.052),
                                (width - 0.052, height - 0.052)))
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - SHUT, face_y, (width - 0.018, height - 0.018),
        (width - 0.060, height - 0.060)), 0.0038))

    # The field: a floor set back from the shell face, and a thin frame ring
    # standing proud of it.
    field = (1.1600, 0.5600)
    field_centre = (0.0, 0.0560)
    # Raised pad, not a cut recess - same reason as the window meter's drum.
    parts.append(p1.chamfer(p1.frustum_box(
        "field_pan", face_y + 0.0030, WP_FIELD_FACE,
        (field[0] + 0.0120, field[1] + 0.0120), (field[0], field[1]),
        centre=field_centre), 0.0026))
    parts.append(p1.chamfer(p1.rect_frame(
        "field_ring", face_y + 0.0030, WP_RING_FRONT,
        (field[0] + 0.0560, field[1] + 0.0560), (field[0], field[1]),
        centre=field_centre), 0.0030))

    parts.extend(scale_arc(
        "tick", (0.0, WP_PIVOT_Z), 84.0, 7, 4,
        0.3040, 0.3300, 0.3620, 0.0110, 0.0056,
        WP_FIELD_FACE + EMBED, WP_FIELD_FACE - 0.0085,
        WP_FIELD_FACE - 0.0062))

    # Datum bar under the arc, and two indicator wells on the flanks of the
    # field so a 1.6 m panel is not one pointer and a lot of nothing.
    parts.append(p1.chamfer(p1.frustum_box(
        "datum_bar", WP_FIELD_FACE + EMBED, WP_FIELD_FACE - 0.0070,
        (0.7400, 0.0180), (0.7320, 0.0150),
        centre=(0.0, WP_PIVOT_Z + 0.3900)), 0.0026))
    for sign in (-1.0, 1.0):
        cx = sign * 0.4400
        parts.append(p1.chamfer(p1.rect_frame(
            f"well_{int(sign)}", WP_FIELD_FACE + EMBED, WP_FIELD_FACE - 0.0090,
            (0.2000, 0.1300), (0.1640, 0.0940),
            centre=(cx, 0.1400)), 0.0026))
        for index in range(9):
            z = 0.1400 - 0.0360 + 0.0720 * index / 8.0
            major = index % 4 == 0
            parts.append(p1.frustum_box(
                f"tick_well_{int(sign)}_{index}",
                WP_FIELD_FACE + EMBED,
                WP_FIELD_FACE - (0.0072 if major else 0.0058),
                (0.0620 if major else 0.0380, 0.0090 if major else 0.0052),
                (0.0604 if major else 0.0370, 0.0080 if major else 0.0046),
                centre=(cx - (0.0430 if major else 0.0550), z)))

    # Guard rails, where the runtime contract puts them.
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"rail_{int(sign)}", face_y + EMBED, face_y - 0.0420,
            (0.0480, 0.7200), (0.0400, 0.7120),
            centre=(sign * 0.7000, 0.0)), 0.0044))

    parts.append(p1.nameplate("plate_label", (0.0, -0.3620),
                              (0.3200, 0.0640), face_y - 0.0032, 0.0038))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}", (sx * 0.7440, sz * 0.3940),
                face_y, 0.0130, 0.0100))
    # Between the field ring at 0.608 and the rail at 0.676, so the head sits
    # on open shell face rather than under something.
    for sx in (-1.0, 1.0):
        parts.append(p1.fastener(
            f"screw_mid_{int(sx)}", (sx * 0.6400, 0.0), face_y, 0.0130,
            0.0100))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0048, 0.0210))

    audit = p3.coplanar_overlap_audit(parts)
    bpy.context.view_layer.update()
    body = p1.join(parts[0], parts[1:])
    body.name = "WindowPanel_body"
    body.data.name = "WindowPanel_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("vane_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, WP_PIVOT_Y, WP_PIVOT_Z)
    pivot.rotation_mode = "XYZ"

    blade = taper_blade("vane_blade", 0.0320, 0.2960, 0.0340, 0.0110,
                        0.0000, -0.0130)
    hub = revolve("vane_hub", [
        (0.0000, 0.0044),
        (0.0520, 0.0044),
        (0.0520, -0.0124),
        (0.0400, -0.0196),
        (0.0000, -0.0196),
    ], segments=32, axis="y", smooth=False)
    vane = p1.join(blade, [hub])
    vane.name = "vane"
    vane.data.name = "vane"
    p1.assign(vane, material)
    vane.parent = pivot

    audit["mechanism"] = {
        "field_opening_m": list(field),
        "field_proud_of_face_mm": round((face_y - WP_FIELD_FACE) * 1000.0, 1),
        "vane_behind_ring_rim_mm": round(
            (WP_PIVOT_Y - 0.0130 - WP_RING_FRONT) * -1000.0, 1),
        "field_ring_section_mm": 28.0,
        "vane_length_mm": 296.0,
        "vane_pivot_xz_m": [0.0, WP_PIVOT_Z],
        "scale": {"sweep_deg": 84.0, "majors": 7, "minors_per_major": 4,
                  "major_longer_mm": round((0.3300 - 0.3040) * 1000.0, 1),
                  "major_wider_mm": round((0.0110 - 0.0056) * 1000.0, 1),
                  "major_deeper_mm": 2.3},
        "guard_rails": 2,
        "indicator_wells": 2,
    }
    return body, pivot, [vane], audit


# ---------------------------------------------------------------------------
# TrendMonitor
# ---------------------------------------------------------------------------

TM_FACE_Y = -0.0460               # shell front face
TM_BEZEL_FRONT = -0.0640
TM_DISPLAY_FRONT = -0.0520        # the plane runtime content sits on
TM_DISPLAY_BACK = -0.0480
TM_DISPLAY = (0.3720, 0.1900)     # 325.4 floor is 0.36 x 0.18
TM_BEZEL_OPENING = (0.3800, 0.1980)


def build_trend_monitor(material):
    """A flat display in a machined bezel, and nothing in front of it.

    `display_surface` is a thin closed slab rather than a bare quad: an open
    quad's four edges are every one of them non-manifold and the gate counts
    them. Its front face is the plane - one rectangle, no glass over it, no
    bezel geometry crossing it, and 6.0 mm of clear opening all round so a
    LineRenderer drawn to the plane's own extents cannot reach the frame.
    """
    width, depth_env, height = envelope_blender("TrendMonitor")
    plate_y = -0.0120
    face_y = TM_FACE_Y
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.010, height - 0.010)), 0.0016))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.026, height - 0.026),
                                (width - 0.026, height - 0.026)))
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - SHUT, face_y, (width - 0.012, height - 0.012),
        (width - 0.036, height - 0.036)), 0.0022))

    # The well the display sits in, then the bezel that frames it. The well
    # floor is behind the display's own back face, so nothing of the housing
    # shows through the 6 mm gap around the plane.
    parts.append(p1.chamfer(p1.frustum_box(
        "display_well", face_y + 0.0140, TM_DISPLAY_BACK - 0.0030,
        (TM_BEZEL_OPENING[0] + 0.0100, TM_BEZEL_OPENING[1] + 0.0100),
        (TM_BEZEL_OPENING[0], TM_BEZEL_OPENING[1])), 0.0018))
    parts.append(p1.chamfer(p1.rect_frame(
        "bezel", face_y + EMBED, TM_BEZEL_FRONT,
        (width - 0.042, height - 0.042), TM_BEZEL_OPENING), 0.0024))

    # The bezel covers the whole shell face, so every service feature and
    # every screw lives on the bezel's own bands. The side bands are 12 mm
    # wide and take nothing; the top and bottom are 23 mm and take a 12.4 mm
    # seat with 5 mm to spare.
    band_z = 0.1090
    for index in range(4):
        parts.append(p1.frustum_box(
            f"vent_{index}", TM_BEZEL_FRONT + EMBED, TM_BEZEL_FRONT - 0.0026,
            (0.0120, 0.0104), (0.0110, 0.0094),
            centre=(-0.0600 + 0.0190 * index, band_z)))
    parts.append(p1.access_cap("access", (0.0750, -band_z),
                               TM_BEZEL_FRONT + EMBED,
                               0.0080, 0.0066, 0.0030))
    parts.append(p1.nameplate("plate_label", (-0.0300, -band_z),
                              (0.1180, 0.0160), TM_BEZEL_FRONT - 0.0018,
                              0.0020))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}", (sx * 0.1500, sz * band_z),
                TM_BEZEL_FRONT, 0.0062, 0.0046))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0030, 0.0110))

    audit = p3.coplanar_overlap_audit(parts)
    bpy.context.view_layer.update()
    body = p1.join(parts[0], parts[1:])
    body.name = "TrendMonitor_body"
    body.data.name = "TrendMonitor_body"
    p1.assign(body, material)

    display = p1.frustum_box(
        "display_surface", TM_DISPLAY_BACK, TM_DISPLAY_FRONT,
        (TM_DISPLAY[0], TM_DISPLAY[1]), (TM_DISPLAY[0], TM_DISPLAY[1]))
    display.name = "display_surface"
    display.data.name = "display_surface"
    p1.assign(display, material)

    audit["mechanism"] = {
        "display_surface_is_own_mesh": True,
        "display_size_m": list(TM_DISPLAY),
        "display_minimum_m": list(DISPLAY_MIN_M),
        "display_meets_minimum": (TM_DISPLAY[0] >= DISPLAY_MIN_M[0]
                                  and TM_DISPLAY[1] >= DISPLAY_MIN_M[1]),
        "display_front_plane_y_m": TM_DISPLAY_FRONT,
        "display_normal_blender": list(DISPLAY_NORMAL_BLENDER),
        "display_up_blender": list(DISPLAY_UP_BLENDER),
        "display_normal_unity": "+Z",
        "display_up_unity": "+Y",
        "display_thickness_mm": round(
            (TM_DISPLAY_FRONT - TM_DISPLAY_BACK) * -1000.0, 2),
        "closed_slab_not_open_quad": (
            "an open quad's four edges are all non-manifold; a 4 mm closed "
            "slab keeps the same single flat front plane and passes the gate"),
        "bezel_opening_m": list(TM_BEZEL_OPENING),
        "clear_margin_each_side_mm": [
            round((TM_BEZEL_OPENING[0] - TM_DISPLAY[0]) * 500.0, 2),
            round((TM_BEZEL_OPENING[1] - TM_DISPLAY[1]) * 500.0, 2)],
        "display_behind_bezel_rim_mm": round(
            (TM_DISPLAY_FRONT - TM_BEZEL_FRONT) * 1000.0, 2),
        "glass": "none",
    }
    return body, display, [display], audit


BUILDERS_C = {
    "WindowMeter": build_window_meter,
    "WindowPanel": build_window_panel,
    "TrendMonitor": build_trend_monitor,
}


# ---------------------------------------------------------------------------
# audits, on Batch B's implementations with this batch's contract
# ---------------------------------------------------------------------------

class contract_scope:
    """Lend Batch C's rows and budgets to Batch B's validated audit code."""

    def __init__(self, asset):
        self.asset = asset

    def __enter__(self):
        self.saved = (bb.VALIDATOR_TOTAL, bb.TARGET_TOTAL,
                      bb.CONTRACT.get(self.asset))
        bb.CONTRACT[self.asset] = CONTRACT[self.asset]
        bb.VALIDATOR_TOTAL = CONTRACT[self.asset]["triangle_budget_total"]
        bb.TARGET_TOTAL = CONTRACT[self.asset]["triangle_target_total"]
        return self

    def __exit__(self, *exc):
        bb.VALIDATOR_TOTAL, bb.TARGET_TOTAL, previous = self.saved
        if previous is None:
            bb.CONTRACT.pop(self.asset, None)
        else:
            bb.CONTRACT[self.asset] = previous
        return False


def measure_asset(asset, root, body, mover, movers):
    with contract_scope(asset):
        return bb.measure_asset(asset, root, body, mover, movers)


def clearance_audit(asset, mover, movers, statics, steps=144):
    """325.7 wants 129 poses or more on the windows; this walks 145."""
    if CONTRACT[asset]["motion"] == "none":
        return {"poses": 1, "clean": True, "min_clearance_mm": None,
                "note": "display kind: the surface does not move"}
    with contract_scope(asset):
        return bb.motion_clearance_audit(mover, movers, statics, asset,
                                         steps=steps)


def pose_set(asset):
    row = CONTRACT[asset]
    if row["motion"] != "rotate":
        return ((0.0, "rest"),)
    low, high = row["blender_range_deg"]
    return ((low, "min"), (0.5 * (low + high), "mid"), (high, "max"))


def apply_pose(mover, asset, value):
    with contract_scope(asset):
        bb.apply_pose(mover, asset, value)


# ---------------------------------------------------------------------------
# coplanar overlap, exactly
# ---------------------------------------------------------------------------

def _overlap_2d(a, b):
    """Separating-axis test on two convex polygons in XZ."""
    for polygon in (a, b):
        count = len(polygon)
        for index in range(count):
            x0, z0 = polygon[index]
            x1, z1 = polygon[(index + 1) % count]
            axis = (-(z1 - z0), x1 - x0)
            length = math.hypot(*axis)
            if length < 1e-12:
                continue
            axis = (axis[0] / length, axis[1] / length)
            spans = []
            for other in (a, b):
                values = [axis[0] * px + axis[1] * pz for px, pz in other]
                spans.append((min(values), max(values)))
            if spans[0][1] <= spans[1][0] + 1e-9 \
                    or spans[1][1] <= spans[0][0] + 1e-9:
                return False
    return True


def coplanar_overlap_exact(objects, tol=1.2e-4):
    """p3's audit with the real triangle overlap instead of its bounding box.

    p3 compares axis-aligned boxes in XZ, which is right for the rectangular
    parts it was written for and conservative for a scale arc: two adjacent
    ticks at different angles have overlapping boxes and disjoint triangles.
    The two accepted round meters carry 6 and 10 such pairs for that reason.
    This runs the separating-axis test on the triangles themselves, so a pair
    it reports is two faces that really do cover the same pixels.
    """
    tris = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        for tri in mesh.loop_triangles:
            normal = (matrix.to_3x3() @ tri.normal).normalized()
            if abs(normal.y) < 0.999:
                continue
            points = [matrix @ mesh.vertices[i].co for i in tri.vertices]
            tris.append({
                "part": obj.name.split(".")[0],
                "y": sum(p.y for p in points) / 3.0,
                "keys": {tuple(round(c, 6) for c in p) for p in points},
                "poly": [(p.x, p.z) for p in points],
            })
    tris.sort(key=lambda row: row["y"])
    pairs = {}
    for index, a in enumerate(tris):
        for j in range(index + 1, len(tris)):
            b = tris[j]
            gap = b["y"] - a["y"]
            if gap > tol:
                break
            if a["part"] == b["part"] or (a["keys"] & b["keys"]):
                continue
            if _overlap_2d(a["poly"], b["poly"]):
                key = tuple(sorted((a["part"], b["part"])))
                if key not in pairs or gap < pairs[key]:
                    pairs[key] = gap
    return {"pairs": [list(k) for k in sorted(pairs)],
            "pair_count": len(pairs),
            "closest_gap_m": round(min(pairs.values()), 7) if pairs else None,
            "tolerance_m": tol,
            "method": "separating-axis test on the triangles themselves"}


def pointer_audit(asset, mover, movers, statics_objects, steps=144):
    """325.7 on the pointer itself: flicker, double scale and protrusion.

    Coplanar overlap between the pointer and any static part is checked at
    every pose, not only at rest, because a needle that shares a plane with a
    tick only where it passes over it would pass a rest-only test.
    """
    row = CONTRACT[asset]
    if row["motion"] != "rotate":
        return {"poses": 0, "clean": True,
                "note": "display kind: no pointer"}
    low, high = row["blender_range_deg"]
    worst = None
    offenders = {}
    poses = 0
    for index in range(steps + 1):
        value = low + (high - low) * index / steps
        apply_pose(mover, asset, value)
        poses += 1
        report = coplanar_overlap_exact(list(statics_objects) + list(movers))
        for pair in report["pairs"]:
            if row["movable"] in pair:
                key = tuple(pair)
                offenders[str(key)] = offenders.get(str(key), 0) + 1
        if report["pairs"] and (worst is None
                                or report["pair_count"] > worst):
            worst = report["pair_count"]
    apply_pose(mover, asset, 0.0)
    return {"poses": poses, "pointer_coplanar_pairs": offenders,
            "clean": not offenders}
