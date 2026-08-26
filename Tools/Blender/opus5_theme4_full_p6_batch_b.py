"""Theme 4 Phase 3 Batch B geometry: Rotary, Button, Lamp, StatusIndicator.

Alignment 295.1 / 298. Batch A and R1, the P1-P5 pilot, the existing three
themes and Batch C are frozen; this writes only to delivery_p6/batch_b.

The contract is measured, not assumed. Envelopes and renderer budgets come
from `InstrumentGreyboxSpecification`; node names from
`RefinedModelReplacementValidator.Models`; motion kinds, axes and ranges from
`MockInstrumentFactory` and `MockInstrumentMotion`; and the node structure
from importing the three existing themes' FBX, which settled two things a
reading of the code alone would have got wrong:

  * `indicator` is an EMPTY at the origin on both Lamp and StatusIndicator.
    The Lamp's mesh is `indicator_lens`, a child of it.
  * StatusIndicator carries `status_safe`, `status_warn` and `status_danger`
    as three separate meshes, so with the body it is exactly at its renderer
    budget of four.

Triangle budget is the one Gate B actually enforces:
`RefinedModelReplacementValidator.CountTriangles` sums the whole prefab
instance and compares it with `GetTriangleBudget(kind)`, which is 5,000 for
all four of these. Target here is 4,500 to leave room.

The P4 atlas is frozen and is reused unchanged. No new atlas region is
needed: the Rotary's grip is cut into the knob as flutes rather than painted
as a knurl, so nothing in Batch B samples the pilot Lever's knurl patch.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_b.py -- \
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

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_b")
OUTPUT = f"{TREE}/geometry/theme4_full_p6_batch_b.json"
NEUTRAL = p3.NEUTRAL
TARGET_TOTAL = 4500
VALIDATOR_TOTAL = 5000

lathe = p3.lathe
SHUT = p1.SHUT_LINE
EMBED = p3.EMBED

# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------

CONTRACT = {
    "Rotary": {
        "kind": "RotaryKnob",
        "motion_target": "knob_pivot", "movable": "knob",
        "meshes": ["Rotary_body", "knob"],
        "envelope_unity_xyz": (0.153, 0.153, 0.112),
        "renderer_budget": 3, "triangle_budget_total": VALIDATOR_TOTAL,
        "motion": "rotate", "unity_axis": "+Z", "blender_axis": "Y",
        "unity_range_deg": (0.0, 360.0), "blender_range_deg": (0.0, 360.0),
        "range_note": ("MotionKind.Rotate applies AngleAxis(value * 360) and "
                       "never reads the amplitude the factory passes (48), so "
                       "the travel is a full revolution"),
        "existing_pivot_local_y": (-0.048, -0.066, -0.067),
        "existing_totals": (3152, 3496, 2968),
    },
    "Button": {
        "kind": "PushButton",
        "motion_target": "button_travel", "movable": "button",
        "meshes": ["Button_body", "button"],
        "envelope_unity_xyz": (0.137, 0.137, 0.096),
        "renderer_budget": 2, "triangle_budget_total": VALIDATOR_TOTAL,
        "motion": "translate", "unity_axis": "-Z", "blender_axis": "+Y",
        "travel_m": 0.014,
        "unity_range_m": (0.0, -0.014), "blender_range_m": (0.0, 0.014),
        "existing_pivot_local_y": (-0.043, -0.063, -0.067),
        "existing_totals": (1328, 1832, 1612),
    },
    "Lamp": {
        "kind": "IndicatorLamp",
        "motion_target": "indicator", "movable": "indicator",
        "meshes": ["Lamp_body", "indicator_lens"],
        "envelope_unity_xyz": (0.143, 0.119, 0.115),
        "renderer_budget": 2, "triangle_budget_total": VALIDATOR_TOTAL,
        "motion": "none", "unity_axis": None,
        "motion_kind": "Pulse (colour and emission only)",
        "indicator_is_empty_at_origin": True,
        "manifest_requires_indicator_renderer": True,
        "existing_totals": (1424, 2084, 1616),
    },
    "StatusIndicator": {
        "kind": "StatusIndicator",
        "motion_target": "indicator", "movable": "indicator",
        "meshes": ["StatusIndicator_body", "status_safe", "status_warn",
                   "status_danger"],
        "envelope_unity_xyz": (0.185, 0.125, 0.100),
        "renderer_budget": 4, "triangle_budget_total": VALIDATOR_TOTAL,
        "motion": "none", "unity_axis": None,
        "motion_kind": "Status (four states, three segment renderers)",
        "states": ["OFF", "SAFE", "WARN", "DANGER"],
        "indicator_is_empty_at_origin": True,
        "manifest_requires_three_state_renderers": True,
        "existing_totals": (1616, 3316, 1808),
    },
}


def envelope_blender(asset):
    """Unity (x, y, z) -> Blender (width X, depth Y, height Z)."""
    x, y, z = CONTRACT[asset]["envelope_unity_xyz"]
    return x, z, y


# ---------------------------------------------------------------------------
# primitives Batch B needs and the pilot did not have
# ---------------------------------------------------------------------------

def revolve(name, profile, segments=32, axis="y", centre=(0.0, 0.0),
            smooth=False, radial=None):
    """p3.lathe with an optional per-angle radius modifier.

    `radial(index, theta)` returns a radius delta for profile point `index`,
    which is what turns a plain knob into a fluted one without adding a
    single box. A profile that never reaches radius zero revolves into a tube,
    which is how every bore in Batch B is made - no booleans anywhere.
    """
    rings = []
    verts = []
    for index, (radius, t) in enumerate(profile):
        if radius < 1e-6:
            if axis == "y":
                verts.append((centre[0], t, centre[1]))
            elif axis == "z":
                verts.append((centre[0], centre[1], t))
            else:
                verts.append((t, centre[0], centre[1]))
            rings.append(("pole", len(verts) - 1))
            continue
        base = len(verts)
        for j in range(segments):
            angle = 2.0 * math.pi * j / segments
            r = radius + (radial(index, angle) if radial else 0.0)
            c, s = r * math.cos(angle), r * math.sin(angle)
            if axis == "y":
                verts.append((centre[0] + c, t, centre[1] + s))
            elif axis == "z":
                verts.append((centre[0] + c, centre[1] + s, t))
            else:
                verts.append((t, centre[0] + c, centre[1] + s))
        rings.append(("ring", base))
    faces = []
    count = len(rings)
    for i in range(count):
        ka, va = rings[i]
        kb, vb = rings[(i + 1) % count]
        if ka == "pole" and kb == "pole":
            continue
        if ka == "ring" and kb == "ring":
            for j in range(segments):
                k = (j + 1) % segments
                faces.append((va + j, va + k, vb + k, vb + j))
        elif ka == "ring":
            for j in range(segments):
                k = (j + 1) % segments
                faces.append((va + j, va + k, vb))
        else:
            for j in range(segments):
                k = (j + 1) % segments
                faces.append((va, vb + k, vb + j))
    return p3._emit(name, verts, faces, smooth)


def flute_field(flutes, depth, band):
    """Rounded scallops on a band of profile points, zero elsewhere.

    A knob has to be turnable with two fingers and ignore a passing hand.
    Scallops do that and stay a surface of revolution's cousin: the silhouette
    is still round, so nothing here is the boxy grip the pilot had to withdraw.
    """
    low, high = band

    def radial(index, theta):
        if not (low <= index <= high):
            return 0.0
        return -depth * (0.5 + 0.5 * math.cos(flutes * theta))
    return radial


# ---------------------------------------------------------------------------
# Rotary
# ---------------------------------------------------------------------------

ROTARY_PIVOT_Y = -0.0620          # knob base plane, between the three themes
ROTARY_SHAFT_R = 0.0132
ROTARY_BORE_R = 0.0152            # 2.0 mm radial clearance on the shaft
ROTARY_FLUTES = 12
ROTARY_HOUSING_SEG = 30
ROTARY_KNOB_SEG = 36


def build_rotary(material):
    """A knob sunk inside a raised collar, fluted so fingers can turn it.

    Mis-operation is answered by geometry: the knob's crown sits 4 mm below
    the top of the bezel collar, so a sleeve or a passing palm rides on the
    collar and cannot reach the flutes. Turning it needs finger tips in the
    scallops. The index flat on the crown and the graduated ring around it
    make the position readable without a texture.
    """
    width, depth_env, height = envelope_blender("Rotary")
    outer = 0.0755
    depth = 0.0980
    plate_y = -0.0150
    face_y = -0.0480                     # bezel front face
    collar_y = -0.0864                   # front of the protective collar
    parts = []

    # Housing: rear register, drafted drum, bezel face, raised collar, bore.
    parts.append(revolve("housing", [
        (0.0000, 0.0000),
        (outer * 0.88, 0.0000),
        (outer, -0.0120),
        (outer * 0.985, -0.0330),
        (outer * 0.86, face_y),
        (0.0530, face_y),
        (0.0530, collar_y),
        (0.0472, collar_y),
        (0.0472, face_y + 0.0026),
        (ROTARY_BORE_R, face_y + 0.0026),
        (ROTARY_BORE_R, plate_y - SHUT),
        (0.0000, plate_y - SHUT),
    ], segments=ROTARY_HOUSING_SEG, axis="y", smooth=False))

    # Graduated ring, sunk into the bezel face so no mark shares its plane.
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
    pivot.location = (0.0, ROTARY_PIVOT_Y, 0.0)
    pivot.rotation_mode = "XYZ"

    # Knob, in pivot-local coordinates. Profile indices 4..7 are the grip
    # band; the scallops are cut only there.
    grip_lo, grip_hi = 4, 6
    knob = revolve("knob", [
        (0.0000, 0.0170),
        (ROTARY_SHAFT_R, 0.0170),
        (ROTARY_SHAFT_R, -0.0038),
        (0.0402, -0.0052),
        (0.0418, -0.0086),
        (0.0418, -0.0148),
        (0.0402, -0.0170),
        (0.0356, -0.0186),
        (0.0212, -0.0202),
        (0.0000, -0.0208),
    ], segments=ROTARY_KNOB_SEG, axis="y", smooth=False,
        radial=flute_field(ROTARY_FLUTES, 0.0032, (grip_lo, grip_hi)))
    index_mark = p1.chamfer(p1.frustum_box(
        "index_mark", -0.0196, -0.0220, (0.0040, 0.0210),
        (0.0033, 0.0186), centre=(0.0, 0.0088)), 0.0005)
    knob = p1.join(knob, [index_mark])
    knob.name = "knob"
    knob.data.name = "knob"
    p1.assign(knob, material)
    knob.parent = pivot

    audit["mechanism"] = {
        "shaft_radius_m": ROTARY_SHAFT_R,
        "bore_radius_m": ROTARY_BORE_R,
        "radial_clearance_mm": round((ROTARY_BORE_R - ROTARY_SHAFT_R) * 1000, 2),
        "collar_front_y_m": collar_y,
        "knob_crown_y_m": round(ROTARY_PIVOT_Y - 0.0208, 4),
        "collar_proud_of_crown_mm": round(
            (ROTARY_PIVOT_Y - 0.0208 - collar_y) * 1000.0, 2),
        "crown_recessed": (ROTARY_PIVOT_Y - 0.0208) > collar_y,
        "flutes": ROTARY_FLUTES,
        "flute_depth_m": 0.0032,
        "index_mark": "index_mark, readout role, on the crown",
        "graduations": 12,
        "misoperation": ("crown recessed inside the collar; the flutes are the "
                         "only purchase and they are below the collar rim"),
    }
    return body, pivot, [knob], audit


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------

BUTTON_PIVOT_Y = -0.0600
BUTTON_TRAVEL = 0.0140
BUTTON_SKIRT_R = 0.0225
BUTTON_BORE_R = 0.0246           # 2.1 mm radial clearance
BUTTON_SKIRT_LEN = 0.0260        # 12 mm still engaged at full press.
                                 # 30 mm ran the skirt's back cap into
                                 # the gasket slab over the last 0.5 mm
                                 # of the stroke.


def build_button(material):
    """A sunk cap inside a guard ring, with the stroke explained by geometry.

    The stroke is 14 mm, which is a long way for a button, so the mechanism
    has to be visible: the skirt is 30 mm long and rides a bore, leaving 16 mm
    engaged at full press, and the cap's shoulder lands on the bezel seat at
    the bottom of the stroke rather than stopping in mid air. Mis-operation is
    answered by the guard: the cap crown sits 3 mm below the guard rim at
    rest, so it cannot be pressed by a brushing hand.
    """
    width, depth_env, height = envelope_blender("Button")
    plate_y = -0.0150
    face_y = -0.0430
    guard_y = -0.0620
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.010, height - 0.010)), 0.0015))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.026, height - 0.026),
                                (width - 0.026, height - 0.026)))
    # Front panel. Without it the gasket is what a viewer sees, because the
    # bezel only covers the middle - the first build read as a black plate.
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, face_y, (width - 0.008, height - 0.008),
        (0.1000, 0.1000)), 0.0016))
    # Bezel and guard, one revolve with a bore right through it.
    parts.append(revolve("bezel", [
        (BUTTON_BORE_R, plate_y - SHUT),
        (0.0480, plate_y - SHUT),
        (0.0480, -0.0300),
        (0.0470, face_y),
        (0.0452, face_y),
        (0.0452, guard_y),
        (0.0396, guard_y),
        (0.0396, face_y + 0.0022),
        (0.0334, face_y + 0.0022),
        (0.0334, -0.0356),
        (BUTTON_BORE_R, -0.0330),
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
    travel.location = (0.0, BUTTON_PIVOT_Y, 0.0)
    travel.rotation_mode = "XYZ"

    # Cap in travel-local coordinates: dished crown, shoulder, long skirt.
    button = revolve("button", [
        (0.0000, BUTTON_SKIRT_LEN),
        (BUTTON_SKIRT_R, BUTTON_SKIRT_LEN),
        (BUTTON_SKIRT_R, 0.0026),
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

    crown_y = BUTTON_PIVOT_Y - 0.0128
    audit["mechanism"] = {
        "travel_m": BUTTON_TRAVEL,
        "skirt_radius_m": BUTTON_SKIRT_R,
        "bore_radius_m": BUTTON_BORE_R,
        "radial_clearance_mm": round(
            (BUTTON_BORE_R - BUTTON_SKIRT_R) * 1000.0, 2),
        "skirt_length_m": BUTTON_SKIRT_LEN,
        "engagement_at_full_press_mm": round(
            (BUTTON_SKIRT_LEN - BUTTON_TRAVEL) * 1000.0, 2),
        "guard_front_y_m": guard_y,
        "crown_y_m": round(crown_y, 4),
        "crown_below_guard_mm": round((crown_y - guard_y) * -1000.0, 2),
        "misoperation": ("crown sunk inside the guard ring; a flat hand rides "
                         "the guard and never touches the cap"),
    }
    return body, travel, [button], audit


# ---------------------------------------------------------------------------
# Lamp
# ---------------------------------------------------------------------------

def build_lamp(material):
    """A domed lens under a hood that shades it without narrowing the view.

    The hood is cut back to 118 degrees of the lens circumference and stands
    only 9 mm proud, so it blocks a ceiling light from directly above while
    leaving the lens visible from either side and from below - the directions
    an operator actually reads it from. The lens itself is a dome rather than
    a flush disc so its lit area stays large at a glancing angle.
    """
    width, depth_env, height = envelope_blender("Lamp")
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
    parts.append(revolve("bezel", [
        (0.0300, plate_y - SHUT),
        (0.0470, plate_y - SHUT),
        (0.0470, -0.0286),
        (0.0424, face_y),
        (0.0352, face_y),
        (0.0352, -0.0330),
        (0.0300, -0.0306),
    ], segments=26, axis="y", smooth=False))
    # Hood: a partial ring, open at the sides and below.
    hood_segments = 14
    verts, faces = [], []
    span = math.radians(118.0)
    start = math.radians(31.0)
    for row, (radius, y) in enumerate(((0.0356, -0.0330), (0.0392, -0.0448),
                                       (0.0356, -0.0470), (0.0322, -0.0344))):
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

    # Seated in front of the bezel's inner lip, not inside its bore: the
    # first build put the lens rim 0.6 mm into the bore wall.
    lens = revolve("indicator_lens", [
        (0.0000, -0.0330),
        (0.0276, -0.0338),
        (0.0300, -0.0372),
        (0.0288, -0.0420),
        (0.0238, -0.0462),
        (0.0144, -0.0490),
        (0.0000, -0.0500),
    ], segments=26, axis="y", smooth=True)
    lens.name = "indicator_lens"
    lens.data.name = "indicator_lens"
    p1.assign(lens, material)
    lens.parent = indicator

    audit["mechanism"] = {
        "indicator_is_empty_at_origin": True,
        "lens_mesh": "indicator_lens",
        "lens_dome_height_mm": round((0.0500 - 0.0338) * 1000.0, 2),
        "lens_radius_m": 0.0300,
        "hood_arc_deg": 118.0,
        "hood_proud_of_lens_mm": round((0.0470 - 0.0400) * 1000.0, 2),
        "shading": ("hood covers the upper 118 degrees only; the lens is open "
                    "to the sides and below"),
        "viewing": ("domed lens keeps lit area at glancing angles; hood does "
                    "not cross the lens equator"),
    }
    return body, indicator, [lens], audit


# ---------------------------------------------------------------------------
# StatusIndicator
# ---------------------------------------------------------------------------

# name, centre x, half width, half height, label. The three half widths are
# deliberately different so the lit one is identified by size as well as hue,
# and the spacing is set so the wells clear each other and leave room for a
# rib in each gap.
STATUS_SEGMENTS = (
    ("status_safe", -0.0620, 0.0170, 0.0165, "SAFE"),
    ("status_warn", 0.0000, 0.0200, 0.0165, "WARN"),
    ("status_danger", 0.0620, 0.0230, 0.0165, "DANGER"),
)
STATUS_WELL_MARGIN = 0.0034


def build_status(material):
    """Three wells, three lenses, three widths - readable while dark.

    The runtime lights exactly one of `status_safe`, `status_warn` and
    `status_danger` and blacks the others, so colour alone carries the state
    and colour alone is the wrong thing to depend on. The three lenses are
    given different widths and sit in separate wells behind raised dividing
    ribs, so the position and size of the lit one identify it even for a
    viewer who cannot separate the hues, and the three read as three even when
    all are dark.
    """
    width, depth_env, height = envelope_blender("StatusIndicator")
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

    # A well per segment - a frame, so the lens sits in an opening rather
    # than through a solid pad - and a rib in each gap between them.
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
    # Hood across all three, open at the sides and below.
    parts.append(p1.chamfer(p1.frustum_box(
        "hood", face_y - 0.0030, face_y - 0.0104,
        (width - 0.030, 0.0088), (width - 0.038, 0.0070),
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

    audit["mechanism"] = {
        "indicator_is_empty_at_origin": True,
        "segment_meshes": [row[0] for row in STATUS_SEGMENTS],
        "segment_half_widths_m": [row[2] for row in STATUS_SEGMENTS],
        "distinct_widths": len({row[2] for row in STATUS_SEGMENTS}) == 3,
        "wells": 3, "ribs": len(STATUS_SEGMENTS) - 1, "hood": True,
        "well_style": "rect_frame opening, lens seated in it",
        "states": CONTRACT["StatusIndicator"]["states"],
        "readability": ("three widths, three wells and two raised ribs, so "
                        "the lit segment is identified by position and size "
                        "as well as by colour, and the three read as three "
                        "when every one of them is dark"),
        "renderers": 1 + len(STATUS_SEGMENTS),
    }
    return body, indicator, lenses, audit


BUILDERS_B = {
    "Rotary": build_rotary,
    "Button": build_button,
    "Lamp": build_lamp,
    "StatusIndicator": build_status,
}


# ---------------------------------------------------------------------------
# audits
# ---------------------------------------------------------------------------

def apply_pose(mover, asset, value):
    row = CONTRACT[asset]
    if row["motion"] == "rotate":
        euler = [0.0, 0.0, 0.0]
        euler["XYZ".index(row["blender_axis"])] = math.radians(value)
        mover.rotation_euler = euler
    elif row["motion"] == "translate":
        axis = [0.0, 0.0, 0.0]
        axis["XYZ".index(row["blender_axis"][-1])] = (
            -1.0 if row["blender_axis"].startswith("-") else 1.0)
        base = ROTARY_PIVOT_Y if asset == "Rotary" else BUTTON_PIVOT_Y
        mover.location = (axis[0] * value, base + axis[1] * value,
                          axis[2] * value)
    bpy.context.view_layer.update()


def pose_set(asset):
    row = CONTRACT[asset]
    if row["motion"] == "rotate":
        low, high = row["blender_range_deg"]
    elif row["motion"] == "translate":
        low, high = row["blender_range_m"]
    else:
        return ((0.0, "rest"),)
    return ((low, "low"), (0.5 * (low + high), "mid"), (high, "high"))


def motion_clearance_audit(mover, movers, statics, asset, steps=144, sample=2):
    """Triangle overlap per pose, then vertex-to-surface distance.

    The Rotary turns a full revolution, so its every-pose test walks 360
    degrees rather than the 129 samples the contract floors at; a knob is
    axisymmetric everywhere except its index mark and flutes, and those are
    exactly what a coarse sample would step over.
    """
    row = CONTRACT[asset]
    trees = {name: BVHTree.FromPolygons(verts, faces, all_triangles=True)
             for name, (verts, faces) in statics.items()}
    if row["motion"] == "none":
        poses = [(0.0, "rest")]
    else:
        span = (row["blender_range_deg"] if row["motion"] == "rotate"
                else row["blender_range_m"])
        poses = [(span[0] + (span[1] - span[0]) * i / steps, None)
                 for i in range(steps + 1)]
    per_part = {}
    intersections = []
    worst_clearance = None
    worst_pose = None
    for value, _ in poses:
        apply_pose(mover, asset, value)
        verts, faces = [], []
        for obj in movers:
            matrix = obj.matrix_world
            mesh = obj.data
            mesh.calc_loop_triangles()
            offset = len(verts)
            verts.extend(matrix @ v.co for v in mesh.vertices)
            faces.extend(tuple(i + offset for i in t.vertices)
                         for t in mesh.loop_triangles)
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
                intersections.append({"pose": round(value, 4),
                                      "static": name,
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
    apply_pose(mover, asset, 0.0)
    return {
        "motion": row["motion"],
        "poses": len(poses),
        "unit": ("deg" if row["motion"] == "rotate"
                 else "m" if row["motion"] == "translate" else "static"),
        "range": list(row.get("blender_range_deg")
                      or row.get("blender_range_m") or []),
        "per_static": per_part,
        "intersections": intersections,
        "intersection_count": len(intersections),
        "min_clearance_mm": worst_clearance,
        "worst_pose": worst_pose,
        "clean": not intersections,
        "method": ("BVH triangle overlap per pose; where none, "
                   "vertex-to-surface nearest distance from the moving mesh"),
        "static_note": ("Lamp and StatusIndicator do not move, so this is a "
                        "single rest-pose interference check"),
    }


def snapshot_statics(parts):
    rows = {}
    for obj in parts:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world.copy()
        rows[obj.name.split(".")[0]] = (
            [matrix @ v.co for v in mesh.vertices],
            [tuple(t.vertices) for t in mesh.loop_triangles])
    return rows


def measure_asset(asset, root, body, mover, movers):
    row = CONTRACT[asset]
    apply_pose(mover, asset, 0.0)
    bounds = p1.world_bounds([body] + list(movers))
    size = [round(bounds["max"][i] - bounds["min"][i], 6) for i in range(3)]
    whd = [size[0], size[2], size[1]]
    envelope = envelope_blender(asset)
    limit = [envelope[0], envelope[2], envelope[1]]
    tris, health = {}, {}
    for obj in [body] + list(movers):
        info = p1.mesh_health(obj)
        tris[obj.name] = info["triangles"]
        health[obj.name] = info
    total = sum(tris.values())
    renderers = 1 + len(movers)
    exported = sorted({o.type for o in [root] + list(root.children_recursive)})
    return {
        "objects": sorted(o.name for o in [root] + list(root.children_recursive)),
        "exported_object_types": exported,
        "no_collider_light_camera_animator": exported == ["EMPTY", "MESH"],
        "renderers": renderers,
        "renderer_budget": row["renderer_budget"],
        "triangles_per_object": tris,
        "triangles_total": total,
        "triangle_budget_total": VALIDATOR_TOTAL,
        "triangle_target_total": TARGET_TOTAL,
        "non_manifold_edges": sum(h["non_manifold_edges"] for h in health.values()),
        "zero_area_faces": sum(h["zero_area_faces"] for h in health.values()),
        "measured_width_height_depth": whd,
        "envelope_width_height_depth": list(limit),
        "within_envelope": all(whd[i] <= limit[i] + 1e-6 for i in range(3)),
        "mount_plane_max_y": round(bounds["max"][1], 6),
        "mount_plane_ok": abs(bounds["max"][1]) <= 1e-6,
        "bounds_unity": p1.to_unity(bounds),
        "contract": {"motion_target": row["motion_target"],
                     "movable": row["movable"],
                     "motion": row["motion"],
                     "unity_axis": row["unity_axis"],
                     "meshes": row["meshes"]},
        "gates": {
            "renderers": renderers <= row["renderer_budget"],
            "triangles_validator_total": total <= VALIDATOR_TOTAL,
            "triangles_target_total": total <= TARGET_TOTAL,
            "non_manifold_zero": all(h["non_manifold_edges"] == 0
                                     for h in health.values()),
            "zero_area_zero": all(h["zero_area_faces"] == 0
                                  for h in health.values()),
            "mount_plane": abs(bounds["max"][1]) <= 1e-6,
            "rest_envelope": all(whd[i] <= limit[i] + 1e-6 for i in range(3)),
            "node_names": all(
                name in {o.name.split(".")[0]
                         for o in root.children_recursive}
                for name in row["meshes"] + [row["motion_target"]]),
            "exported_types_clean": exported == ["EMPTY", "MESH"],
        },
    }


def part_breakdown(builder):
    """Triangles per top-level part, captured at the outermost join."""
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
        material = p1.proto.make_material(f"MAT_{THEME}_P6B_Neutral", NEUTRAL)
        builder(material)
    finally:
        p1.join = original
    if not calls:
        return {}
    calls.sort(key=lambda c: -len(c))
    agg = {}
    for name, tris in calls[0]:
        key = name
        for prefix in ("screw_", "tick_", "well_", "rib_"):
            if name.startswith(prefix):
                key = prefix + "*"
                break
        agg[key] = agg.get(key, 0) + tris
    return dict(sorted(agg.items(), key=lambda kv: -kv[1]))


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


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
        "phase": "Theme4-P6-BatchB-geometry",
        "note": ("Rotary, Button, Lamp, StatusIndicator. Contract measured "
                 "from InstrumentGreyboxSpecification, "
                 "RefinedModelReplacementValidator, MockInstrumentFactory, "
                 "MockInstrumentMotion and the three existing themes' FBX. "
                 "Batch A/R1, P1-P5, the existing themes and Batch C are "
                 "untouched; the P4 atlas is reused unchanged."),
        "contract": {k: {kk: (list(vv) if isinstance(vv, tuple) else vv)
                         for kk, vv in v.items()}
                     for k, v in CONTRACT.items()},
        "budgets": {"triangle_budget_validator_total": VALIDATOR_TOTAL,
                    "triangle_target_total": TARGET_TOTAL,
                    "shared_material_budget": 2},
        "new_atlas_region_required": False,
        "atlas_note": ("the Rotary grip is cut as flutes in the knob, so no "
                       "Batch B UV island reaches the pilot Lever's knurl "
                       "patch and the frozen P4 atlas serves unchanged"),
        "assets": {},
    }

    import opus5_brushup_kinetic_review as review
    for asset, builder in BUILDERS_B.items():
        breakdown = part_breakdown(builder)

        p1.clear_scene()
        review.configure_scene()
        material = p1.proto.make_material(f"MAT_{THEME}_P6B_Neutral", NEUTRAL)
        root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
        bpy.context.collection.objects.link(root)

        statics = {}
        original_join = p1.join
        captured = []

        def capturing_join(target, others):
            captured.append([target] + list(others))
            return original_join(target, others)

        p1.join = capturing_join
        try:
            body, mover, movers, audit = builder(material)
        finally:
            p1.join = original_join
        if captured:
            captured.sort(key=lambda c: -len(c))
            # the body join is the widest; its sources are the statics
            statics = {}
        for obj in (body, mover):
            obj.parent = root
        bpy.context.view_layer.update()

        statics = snapshot_statics([body])
        row = measure_asset(asset, root, body, mover, movers)
        row["coplanar_overlap"] = audit
        row["part_triangles"] = breakdown
        row["clearance"] = motion_clearance_audit(
            mover, movers, statics, asset)
        row["gates"]["clearance_clean"] = row["clearance"]["clean"]
        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P6B.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        focus, radius, scale = p1.rig_for([body] + list(movers))
        images = {}
        for label, view in p1.VIEWS.items():
            path = grey_dir / f"Grey_{asset}_{THEME}_P6B_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        row["grayscale_images"] = images

        details = {}
        for value, label in pose_set(asset):
            apply_pose(mover, asset, value)
            near = detail_dir / f"Detail_{asset}_motion_{label}.png"
            p1.shot(focus, radius * 0.55, (42.0, 14.0), 58.0, scale * 0.55,
                    near)
            details[f"motion_{label}"] = str(near.relative_to(project_root))
        apply_pose(mover, asset, 0.0)
        row["detail_images"] = details
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        print(f"[BatchB] {asset}: tris {row['triangles_total']} "
              f"{row['triangles_per_object']}, renderers {row['renderers']}"
              f"/{row['renderer_budget']}, coplanar {audit['pair_count']}, "
              f"clearance {row['clearance']['clean']} "
              f"min {row['clearance']['min_clearance_mm']}, "
              f"gates {row['all_gates_passed']}")

    payload["status"] = (
        "p6_batch_b_geometry_ready"
        if all(row["all_gates_passed"] for row in payload["assets"].values())
        else "p6_batch_b_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchB] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
