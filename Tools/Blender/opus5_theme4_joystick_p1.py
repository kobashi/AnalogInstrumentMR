"""Theme 4 (Machined Ergonomics): a two-axis control stick, first prototype.

A new instrument type, so there is no source Blend to diff against. What the
model is judged by is written down here first - the constants below and the
`EXPECTED` table - and measured back from the generated scene afterwards
(alignment 236.1 / 236.7).

Construction follows the manufacturing vocabulary the theme guide asks for,
not styling: an anodised back plate bolted to the wall at its four corners, a
gasket shut line, a drafted moulded cover, a machined bezel that retains the
gimbal ball, an elastomer ball boot, a milled square gate that is the end stop,
a clamp collar on the shaft, and an over-moulded elastomer grip band on a resin
core with a single thumb rest.

Triangle and renderer budgets follow the existing Lever / Throttle deliveries,
measured from the production FBX (2 renderers: `<Asset>_body` under the root
and the moving part under a pivot Empty; 2,452-6,792 triangles in total).

Everything is explicit bmesh solids built from lofted rings. No boolean and no
hull, so there are no n-gon caps to split into zero-area triangles.

Blender authors Y-into-the-wall: the mount plane is max Y == 0 and the
instrument faces -Y, which the FBX conversion turns into Unity local Z = 0 with
+Z outward.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_joystick_p1.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_toggle_fbx_handoff as toggle

ASSET = "Joystick"
THEME = "MachinedErgonomics"
TREE = f"ArtSource/Blender/BrushUp/Opus5/{THEME}/{ASSET}"
TAG = "V6_Opus5_P1"
ROOT_NAME = f"PF_Visual_{ASSET}_{THEME}_V6"
BODY_NAME = f"{ASSET}_body"
PART_NAME = "stick"
PIVOT_NAME = "stick_pivot"      # outer gimbal ring, tilts about local X
GIMBAL_NAME = "stick_gimbal"    # inner gimbal ring, tilts about local Z
MATERIAL_NAME = f"MAT_{THEME}_{ASSET}_P1_Opaque"

# --------------------------------------------------------------------------
# budgets - measured from the shipped Lever / Throttle FBX of all four themes
# --------------------------------------------------------------------------

TRIANGLES_PER_OBJECT = 5000       # MACHINED_ERGONOMICS_STYLE_GUIDE.md runtime limit
TRIANGLES_TOTAL_REFERENCE = (2452, 6792)   # existing Lever/Throttle totals
RENDERERS = 2                     # every existing Lever/Throttle ships two
MATERIAL_LIMIT = 2                # shared materials per the style guide

# --------------------------------------------------------------------------
# datums and design intent
#
# Every depth is measured outward from the mount plane (d, metres) or outward
# from the gimbal centre (delta). Dimensions that depend on each other are
# derived here, not repeated as numbers further down.
# --------------------------------------------------------------------------

SHUT_LINE = 0.0010          # one shut-line width for the whole model
DRAFT_DEG = 2.0             # moulded cover flank, inside the guide's 1-3 deg
SINK = 0.0004               # every stacked shell sinks this far: no coplanar faces

PIVOT_D = 0.030             # gimbal centre, inside the housing
BALL_R = 0.021              # elastomer ball boot, centred on the pivot
BALL_GAP = 0.0012           # bezel seat clearance around the ball

PLATE_HALF, PLATE_N, PLATE_T = 0.062, 6.0, 0.008
COVER_HALF, COVER_N = 0.056, 4.0
COVER_BACK_D = PLATE_T + SHUT_LINE           # shut line between plate and cover
COVER_FRONT_D = 0.044
COVER_FILLET = 0.003
RECESS_R, RECESS_D = 0.0415, 0.040           # pocket the bezel sits in
BEZEL_R = RECESS_R - SHUT_LINE
BEZEL_TOP_D = 0.0472
CAVITY_R = BALL_R + 0.0015                   # the ball turns inside this

# Square gate. The collar's lower outer corner meets the gate wall at STOP_DEG
# on each axis. Runtime travel stays TRAVEL_DEG, so the stop is a real,
# visible limit with a margin, not a surface the stick rubs at full travel.
TRAVEL_DEG = 20.0
STOP_DEG = 22.0
COLLAR_R = 0.0120
COLLAR_LOW = 0.0360                          # delta of the collar's lower face
COLLAR_CHAMFER = 0.0006
# The chamfer's two corners are what can touch the gate; the gate is sized
# from whichever reaches further out at STOP_DEG, not from a sharp corner the
# part does not have (the first build stopped at 21 degrees because of this).
COLLAR_CORNERS = ((COLLAR_R - COLLAR_CHAMFER, COLLAR_LOW),
                  (COLLAR_R, COLLAR_LOW + COLLAR_CHAMFER))
# The collar tapers towards the grip. At a diagonal tilt more of a straight
# collar sinks below the gate's top edge and its upper part touched first;
# tapered, the lower corner is always the part that meets the gate.
COLLAR_TOP, COLLAR_TOP_R = 0.0451, COLLAR_R - 0.0025
GATE_TOP_DELTA = 0.032
GATE_CORNER_R = 0.006                        # end-mill radius left in the pocket
GATE_WALL = 0.0055
GATE_HALF = max(delta * math.sin(math.radians(STOP_DEG))
                + radius * math.cos(math.radians(STOP_DEG))
                for radius, delta in COLLAR_CORNERS)

# Boot neck: the one part of the stick outside the ball's sphere near the
# bezel. The bezel bore opens as a cone whose apex is the pivot, wide enough
# that the neck at the combined stop tilt still stays inside it.
BOOT_NECK = ((0.0062, 0.0215), (0.0060, 0.0235))
COMBINED_STOP_DEG = math.degrees(math.acos(
    math.cos(math.radians(STOP_DEG + 1.0)) ** 2))
BEZEL_CONE_DEG = (COMBINED_STOP_DEG + 2.0
                  + max(math.degrees(math.atan2(r, d)) for r, d in BOOT_NECK))
# The seat follows the offset sphere all the way to the bezel's underside; a
# vertical wall below the last seat ring cut inside the ball (first rebuild).
BEZEL_SEAT_BOTTOM_DEG = math.degrees(math.acos(
    (RECESS_D - SINK - PIVOT_D) / (BALL_R + BALL_GAP)))
BEZEL_SEAT_DEG = (57.0, BEZEL_SEAT_BOTTOM_DEG)

PLATE_BOLT_AT = 0.0515                       # on the diagonals: load path to the wall
BEZEL_SCREW_AT = 0.0350                      # on the axes, clear of the gate corners

# Grip sections: (delta, half-width X, half-depth +Z, half-depth -Z, n, z shift).
# -Z is the palm side, so the section is fuller there and the grip leans onto it.
GRIP_NECK = [
    (0.0448, 0.0108, 0.0108, 0.0108, 2.0, 0.0),
    (0.0500, 0.0122, 0.0118, 0.0128, 2.2, -0.0003),
    (0.0548, 0.0130, 0.0124, 0.0138, 2.3, -0.0006),
]
GRIP_BAND = [   # elastomer over-mould, 0.8 mm proud of the resin core
    (0.0543, 0.0138, 0.0132, 0.0146, 2.3, -0.0006),
    (0.0580, 0.0142, 0.0133, 0.0152, 2.3, -0.0008),
    (0.0680, 0.0146, 0.0133, 0.0160, 2.4, -0.0012),
    (0.0820, 0.0162, 0.0140, 0.0180, 2.5, -0.0020),
    (0.0960, 0.0170, 0.0144, 0.0190, 2.5, -0.0028),
    (0.1100, 0.0166, 0.0141, 0.0184, 2.5, -0.0034),
    (0.1230, 0.0158, 0.0134, 0.0172, 2.4, -0.0038),
    (0.1285, 0.0154, 0.0130, 0.0167, 2.4, -0.0039),
]
GRIP_HEAD = [
    (0.1280, 0.0146, 0.0122, 0.0159, 2.4, -0.0039),
    (0.1340, 0.0150, 0.0126, 0.0162, 2.4, -0.0039),
    (0.1400, 0.0150, 0.0126, 0.0160, 2.4, -0.0039),
    (0.1440, 0.0140, 0.0117, 0.0150, 2.4, -0.0039),
    (0.1465, 0.0120, 0.0100, 0.0128, 2.4, -0.0039),
    (0.1478, 0.0092, 0.0076, 0.0098, 2.4, -0.0039),
]
THUMB_TILT_DEG = 10.0       # top faces up and back, towards the palm side
THUMB_TILT_FROM = 0.1440    # sections at or above this delta follow the tilt
THUMB_DISH = 0.0008         # the one finger relief the guide allows

SEGMENTS = 48
STICK_SEGMENTS = 32

ROLE_COLOUR = {             # RGBA; alpha carries metallic for the preview shader
    "body": (0.62, 0.60, 0.575, 0.0),
    "metal": (0.34, 0.36, 0.39, 1.0),
    "gasket": (0.055, 0.057, 0.060, 0.0),
}

# Written before anything is measured: what a pass looks like, and what the
# failure that each check exists for would look like instead.
EXPECTED = {
    "stop_axis_deg": f"about {STOP_DEG} on each of the four axis directions; "
                     "no contact at all would mean the gate is not a stop",
    "stop_diagonal_deg": "about the same as the axis stop, because the gate is "
                         "square; a much smaller value means the corner radius "
                         "cuts the diagonal travel",
    "sweep_overlaps": "0 over the whole +-20 x +-20 runtime grid",
    "sweep_min_clearance_mm": "about 1 mm at full diagonal travel, collar to gate",
    "rest_mount_plane_max_y": "0.0 exactly (the back plate face)",
    "mesh_local_min_extent_mm": "tens of millimetres on every axis; 0 would repeat "
                                "the display-panel frame defect",
    "invisible_parts": "none; every named part has triangles reachable from the "
                       "front hemisphere",
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1:] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-render", action="store_true")
    return parser.parse_args(args)


# --------------------------------------------------------------------------
# rings and lofts
# --------------------------------------------------------------------------

def body_point(x, d, z):
    return (x, -d, z)


def superellipse(a, b_pos, b_neg, n, count, z_shift=0.0):
    """Points of |x/a|^n + |z/b|^n = 1, sampled by the same parameter for every
    ring, so a superellipse ring bridges to a circle (n = 2) quad for quad."""
    points = []
    for index in range(count):
        t = 2.0 * math.pi * (index + 0.5) / count
        c, s = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(c) ** (2.0 / n), c)
        b = b_pos if s >= 0.0 else b_neg
        z = b * math.copysign(abs(s) ** (2.0 / n), s) + z_shift
        points.append((x, z))
    return points


def circle(radius, count, centre=(0.0, 0.0)):
    return [(centre[0] + x, centre[1] + z)
            for x, z in superellipse(radius, radius, radius, 2.0, count)]


def rounded_square(half, corner, per_corner=5):
    """Straight sides with one tool radius per corner - a milled pocket."""
    points = []
    centre = half - corner
    for quadrant in range(4):
        cx = centre if quadrant in (0, 3) else -centre
        cz = centre if quadrant in (0, 1) else -centre
        start = quadrant * 90.0
        for step in range(per_corner + 1):
            angle = math.radians(start + 90.0 * step / per_corner)
            points.append((cx + corner * math.cos(angle),
                           cz + corner * math.sin(angle)))
    return points


def loft(name, rings, closed=False, cap_start=True, cap_end=True, apex=None):
    """Bridge rings of equal length into one closed shell.

    `rings` are lists of 3-D points. `closed` joins the last ring back to the
    first (a ring-shaped profile such as a bezel); otherwise the ends are
    capped, or the last ring closes to `apex` (a dish).
    """
    count = len(rings[0])
    if any(len(ring) != count for ring in rings):
        raise ValueError(f"{name}: rings differ in length")
    verts = [point for ring in rings for point in ring]
    faces = []
    spans = len(rings) if closed else len(rings) - 1
    for band in range(spans):
        lo = band * count
        hi = ((band + 1) % len(rings)) * count
        for index in range(count):
            nxt = (index + 1) % count
            faces.append((lo + index, lo + nxt, hi + nxt, hi + index))
    if not closed:
        if cap_start:
            faces.append(tuple(range(count - 1, -1, -1)))
        if apex is not None:
            verts.append(apex)
            tip = len(verts) - 1
            base = (len(rings) - 1) * count
            for index in range(count):
                faces.append((base + index, base + (index + 1) % count, tip))
        elif cap_end:
            base = (len(rings) - 1) * count
            faces.append(tuple(range(base, base + count)))
    return p1.emit(p1.new_mesh(name), verts, faces)


def lathe(name, profile, count, centre=(0.0, 0.0), origin_d=0.0, axis_sign=1.0):
    """Revolve (radius, depth) pairs around the outward axis."""
    rings = []
    for radius, depth in profile:
        rings.append([body_point(x, origin_d + axis_sign * depth, z)
                      for x, z in circle(radius, count, centre)])
    return loft(name, rings)


PARTS = []


def tag(obj, role, part):
    """Role colour on every corner and a part id on every face.

    The role decides the later join unit (alignment 236.7), so it is attached
    when the part is made, not inferred afterwards.
    """
    if part not in PARTS:
        PARTS.append(part)
    mesh = obj.data
    colours = mesh.color_attributes.new("role_color", "FLOAT_COLOR", "CORNER")
    value = ROLE_COLOUR[role]
    colours.data.foreach_set("color", value * len(mesh.loops))
    ids = mesh.attributes.new("part_id", "INT", "FACE")
    ids.data.foreach_set("value", [PARTS.index(part)] * len(mesh.polygons))
    obj["role"] = role
    return obj


def hardware(name, centre, seat_d, head_r, head_h, washer=True):
    """A socket cap screw, optionally on a washer, axis outward."""
    parts = []
    base = seat_d - SINK
    if washer:
        parts.append(tag(lathe(f"{name}_washer", [
            (head_r * 1.28, base), (head_r * 1.28, seat_d + 0.0008),
            (head_r * 1.20, seat_d + 0.0008 + 0.0002)], 16, centre), "metal",
            f"{name}_washer"))
        seat_d += 0.0008
    top = seat_d + head_h
    parts.append(tag(lathe(f"{name}_head", [
        (head_r, seat_d - SINK), (head_r, top - 0.0004),
        (head_r - 0.0004, top)], 16, centre), "metal", f"{name}_head"))
    parts.append(tag(lathe(f"{name}_socket", [
        (head_r * 0.46, top - SINK), (head_r * 0.46, top + 0.00012)],
        6, centre), "gasket", f"{name}_socket"))
    return parts


# --------------------------------------------------------------------------
# the instrument
# --------------------------------------------------------------------------

def build_body():
    parts = []
    N = SEGMENTS

    def se_ring(half, n, d):
        return [body_point(x, d, z) for x, z in superellipse(half, half, half, n, N)]

    def circle_ring(radius, d):
        return [body_point(x, d, z) for x, z in circle(radius, N)]

    # back plate, anodised: the part that carries the load into the wall
    parts.append(tag(loft("plate", [
        se_ring(PLATE_HALF, PLATE_N, 0.0),
        se_ring(PLATE_HALF, PLATE_N, PLATE_T - 0.0010),
        se_ring(PLATE_HALF - 0.0010, PLATE_N, PLATE_T),
    ]), "metal", "plate"))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts += hardware(f"plate_bolt_{int(sx)}{int(sz)}",
                              (sx * PLATE_BOLT_AT, sz * PLATE_BOLT_AT),
                              PLATE_T, 0.0036, 0.0026)

    # gasket: the dark line between plate and cover. It stands 0.4 mm proud
    # of the cover; tucked under the cover's edge no ray from the front
    # hemisphere reached it, and a shut line nobody can see is not a shut line.
    gasket_half = COVER_HALF + 0.0004
    parts.append(tag(loft("gasket", [
        se_ring(gasket_half, COVER_N, PLATE_T - SINK),
        se_ring(gasket_half, COVER_N, COVER_BACK_D + 0.0002),
    ]), "gasket", "gasket"))

    # moulded cover: drafted flank, a two-segment fillet onto the face, a
    # pocket for the bezel, and a cavity the ball turns in
    flank = COVER_FRONT_D - COVER_FILLET
    front_half = COVER_HALF - (flank - COVER_BACK_D) * math.tan(math.radians(DRAFT_DEG))
    rings = [se_ring(COVER_HALF, COVER_N, COVER_BACK_D),
             se_ring(front_half, COVER_N, flank)]
    centre_half = front_half - COVER_FILLET
    for degrees in (30.0, 60.0, 90.0):
        angle = math.radians(degrees)
        rings.append(se_ring(centre_half + COVER_FILLET * math.cos(angle), COVER_N,
                             flank + COVER_FILLET * math.sin(angle)))
    rings += [circle_ring(RECESS_R, COVER_FRONT_D),
              circle_ring(RECESS_R, RECESS_D),
              circle_ring(CAVITY_R, RECESS_D),
              circle_ring(CAVITY_R, COVER_BACK_D + 0.003)]
    parts.append(tag(loft("cover", rings), "body", "cover"))

    # machined bezel: sits in the pocket. Below, a spherical seat retains the
    # ball with BALL_GAP all round; above, a countersink cone from the pivot
    # lets the boot neck through at full travel.
    top_delta = BEZEL_TOP_D - PIVOT_D
    cone = math.radians(BEZEL_CONE_DEG)
    seat_r = BALL_R + BALL_GAP
    profile = [(BEZEL_R, RECESS_D - SINK),
               (BEZEL_R, BEZEL_TOP_D - 0.0008),
               (BEZEL_R - 0.0008, BEZEL_TOP_D),
               (top_delta * math.tan(cone), BEZEL_TOP_D)]
    for degrees in (BEZEL_CONE_DEG,) + BEZEL_SEAT_DEG:
        angle = math.radians(degrees)
        profile.append((seat_r * math.sin(angle), PIVOT_D + seat_r * math.cos(angle)))
    parts.append(tag(loft("bezel", [circle_ring(r, d) for r, d in profile],
                          closed=True), "metal", "bezel"))
    for index, (sx, sz) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
        parts += hardware(f"bezel_screw_{index}",
                          (sx * BEZEL_SCREW_AT, sz * BEZEL_SCREW_AT),
                          BEZEL_TOP_D, 0.0026, 0.0020, washer=False)

    # milled square gate: the end stop, standing on the bezel
    top_d = PIVOT_D + GATE_TOP_DELTA
    outer_half = GATE_HALF + GATE_WALL
    outer_corner = GATE_CORNER_R + GATE_WALL

    def gate_ring(half, corner, d):
        return [body_point(x, d, z) for x, z in rounded_square(half, corner)]

    parts.append(tag(loft("gate", [
        gate_ring(outer_half, outer_corner, BEZEL_TOP_D - SINK),
        gate_ring(outer_half, outer_corner, top_d - 0.0008),
        gate_ring(outer_half - 0.0008, outer_corner - 0.0008, top_d),
        gate_ring(GATE_HALF + 0.0008, GATE_CORNER_R + 0.0008, top_d),
        gate_ring(GATE_HALF, GATE_CORNER_R, top_d - 0.0008),
        gate_ring(GATE_HALF, GATE_CORNER_R, BEZEL_TOP_D - SINK),
    ], closed=True), "metal", "gate"))

    body = p1.join(parts[0], parts[1:])
    body.name = BODY_NAME
    body.data.name = BODY_NAME
    return body


def build_stick():
    """Built in the pivot's frame: origin at the gimbal centre, outward -Y."""
    parts = []
    N = STICK_SEGMENTS

    # elastomer ball boot, carried past the equator so no edge of it can
    # swing into view at full diagonal travel
    profile = [(BALL_R * math.sin(math.radians(phi)),
                BALL_R * math.cos(math.radians(phi)))
               for phi in (100, 88, 76, 64, 52, 41, 31, 23, 17)]
    profile += list(BOOT_NECK)
    parts.append(tag(lathe("boot", profile, N), "gasket", "boot"))

    # shaft and clamp collar, one turned part
    parts.append(tag(lathe("collar", [
        (0.0055, 0.0225), (0.0055, COLLAR_LOW)] + list(COLLAR_CORNERS) + [
        (COLLAR_TOP_R + COLLAR_CHAMFER, COLLAR_TOP - COLLAR_CHAMFER),
        (COLLAR_TOP_R, COLLAR_TOP)], N), "metal", "collar"))
    # A set screw sits in its tapped hole, flush. Standing proud it was the
    # first thing to hit the gate, 2 degrees before the collar.
    screw_delta = 0.0405
    low_r, low_d = COLLAR_CORNERS[1]
    high_r, high_d = COLLAR_TOP_R + COLLAR_CHAMFER, COLLAR_TOP - COLLAR_CHAMFER
    face_r = low_r + (high_r - low_r) * (screw_delta - low_d) / (high_d - low_d)
    screw = p1.axis_cyl("collar_set_screw", face_r - 0.0010, face_r + 0.0001,
                        0.0017, (-screw_delta, 0.0), segments=10)
    parts.append(tag(screw, "gasket", "collar_set_screw"))

    def grip_ring(section):
        delta, a, b_pos, b_neg, n, shift = section
        ring = []
        for x, z in superellipse(a, b_pos, b_neg, n, N, shift):
            lift = delta
            if delta >= THUMB_TILT_FROM:
                lift += z * math.tan(math.radians(THUMB_TILT_DEG))
            ring.append((x, -lift, z))
        return ring

    parts.append(tag(loft("grip_neck", [grip_ring(s) for s in GRIP_NECK]),
                     "body", "grip_neck"))
    parts.append(tag(loft("grip_band", [grip_ring(s) for s in GRIP_BAND]),
                     "gasket", "grip_band"))
    top = GRIP_HEAD[-1]
    apex_delta = top[0] - THUMB_DISH + top[5] * math.tan(math.radians(THUMB_TILT_DEG))
    parts.append(tag(loft("grip_head", [grip_ring(s) for s in GRIP_HEAD],
                          apex=(0.0, -apex_delta, top[5])), "body", "grip_head"))

    stick = p1.join(parts[0], parts[1:])
    stick.name = PART_NAME
    stick.data.name = PART_NAME
    return stick


def finish(obj, material):
    """Smooth shading with split normals kept at real edges, box UVs, one
    material. UVs are planar per face (alignment 236.8): enough for UV0 to
    exist and the atlas pass to take over later."""
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.set_sharp_from_angle(angle=math.radians(35.0))
    uv = obj.data.uv_layers.new(name="UVMap")
    for polygon in obj.data.polygons:
        axis = max(range(3), key=lambda i: abs(polygon.normal[i]))
        u_axis, v_axis = [(1, 2), (0, 2), (0, 1)][axis]
        for loop_index in polygon.loop_indices:
            co = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv = (co[u_axis] * 4.0 + 0.5, co[v_axis] * 4.0 + 0.5)


def preview_material():
    material = bpy.data.materials.new(MATERIAL_NAME)
    material.use_nodes = True
    tree = material.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    attribute = tree.nodes.new("ShaderNodeAttribute")
    attribute.attribute_type = "GEOMETRY"
    attribute.attribute_name = "role_color"
    tree.links.new(attribute.outputs["Color"], bsdf.inputs["Base Color"])
    tree.links.new(attribute.outputs["Alpha"], bsdf.inputs["Metallic"])
    bsdf.inputs["Roughness"].default_value = 0.46
    return material


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------

def world_array(obj):
    count = len(obj.data.vertices)
    local = np.empty(count * 3, dtype=np.float64)
    obj.data.vertices.foreach_get("co", local)
    local = local.reshape(count, 3)
    matrix = np.array(obj.matrix_world, dtype=np.float64)
    return local @ matrix[:3, :3].T + matrix[:3, 3]


def bvh_of(obj):
    return BVHTree.FromPolygons([tuple(v) for v in world_array(obj)],
                                [tuple(p.vertices) for p in obj.data.polygons],
                                epsilon=0.0)


def pose(pivot, gimbal, pitch, yaw):
    pivot.rotation_euler = (math.radians(pitch), 0.0, 0.0)
    gimbal.rotation_euler = (0.0, 0.0, math.radians(yaw))
    bpy.context.view_layer.update()


def contact(body_tree, stick):
    return len(body_tree.overlap(bvh_of(stick)))


def clearance(body_tree, stick):
    best = float("inf")
    for vertex in world_array(stick):
        hit = body_tree.find_nearest(Vector(vertex))
        if hit[0] is not None:
            best = min(best, hit[3])
    return best


def sweep(body, pivot, gimbal, stick, step=2.5):
    """Every pose on the runtime grid: overlaps must be zero everywhere.

    A neutral pose that looks right is not evidence (knowhow 6), so the grid
    covers both axes together, corners included.
    """
    body_tree = bvh_of(body)
    ticks = int(round(2 * TRAVEL_DEG / step))
    worst = {"clearance_mm": float("inf")}
    overlaps = 0
    union_lo, union_hi = [float("inf")] * 3, [float("-inf")] * 3
    for i in range(ticks + 1):
        for j in range(ticks + 1):
            pitch = -TRAVEL_DEG + i * step
            yaw = -TRAVEL_DEG + j * step
            pose(pivot, gimbal, pitch, yaw)
            hits = contact(body_tree, stick)
            overlaps += hits
            gap = clearance(body_tree, stick)
            if gap < worst["clearance_mm"]:
                worst = {"clearance_mm": gap, "pitch_deg": pitch, "yaw_deg": yaw}
            points = world_array(stick)
            for axis in range(3):
                union_lo[axis] = min(union_lo[axis], float(points[:, axis].min()))
                union_hi[axis] = max(union_hi[axis], float(points[:, axis].max()))
    pose(pivot, gimbal, 0.0, 0.0)
    worst["clearance_mm"] = round(worst["clearance_mm"] * 1000.0, 3)
    return {
        "grid_step_deg": step,
        "poses": (ticks + 1) ** 2,
        "overlapping_triangle_pairs": overlaps,
        "min_vertex_clearance": worst,
        "clearance_method": ("stick vertices to the nearest body surface; a proxy "
                             "for the gap, while the overlap count is the gate"),
        "stick_swept_bounds_blender": {
            "min": [round(v, 6) for v in union_lo],
            "max": [round(v, 6) for v in union_hi]},
    }


def stop_angles(body, pivot, gimbal, stick):
    """Walk outward until the stick first touches the body."""
    body_tree = bvh_of(body)
    directions = {"+pitch": (1, 0), "-pitch": (-1, 0), "+yaw": (0, 1),
                  "-yaw": (0, -1), "+pitch+yaw": (1, 1), "-pitch-yaw": (-1, -1)}
    found = {}
    for label, (sp, sy) in directions.items():
        angle = TRAVEL_DEG
        found[label] = None
        while angle <= 32.0 + 1e-9:
            pose(pivot, gimbal, sp * angle, sy * angle)
            if contact(body_tree, stick):
                found[label] = round(angle, 2)
                break
            angle += 0.25
    pose(pivot, gimbal, 0.0, 0.0)
    return found


VIEW_DIRECTIONS = [Vector(v).normalized() for v in (
    (0.0, -1.0, 0.0), (0.6, -1.0, 0.0), (-0.6, -1.0, 0.0),
    (0.0, -1.0, 0.6), (0.0, -1.0, -0.6))]


def visibility(objects):
    """Which parts can be seen at all from the front hemisphere.

    A part that is present but never reachable by a ray is a defect (the
    buried knob ring): its triangles are spent where nobody looks.
    """
    verts, polys, owner = [], [], []
    for obj in objects:
        base = len(verts)
        verts += [tuple(v) for v in world_array(obj)]
        ids = obj.data.attributes["part_id"].data
        for polygon in obj.data.polygons:
            polys.append(tuple(base + v for v in polygon.vertices))
            owner.append((obj, polygon.index, ids[polygon.index].value))
    tree = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
    seen, total = {}, {}
    for obj, index, part_id in owner:
        polygon = obj.data.polygons[index]
        matrix = obj.matrix_world
        centre = matrix @ polygon.center
        normal = (matrix.to_3x3() @ polygon.normal).normalized()
        name = PARTS[part_id]
        total[name] = total.get(name, 0) + 1
        for direction in VIEW_DIRECTIONS:
            if normal.dot(direction) <= 0.0:
                continue
            hit = tree.ray_cast(centre + normal * 1e-5, direction)
            if hit[0] is None:
                seen[name] = seen.get(name, 0) + 1
                break
    rows = {name: {"triangles": total[name], "visible": seen.get(name, 0)}
            for name in total}
    hidden = sum(row["triangles"] - row["visible"] for row in rows.values())
    return {
        "parts": rows,
        "parts_never_visible": sorted(n for n, r in rows.items() if r["visible"] == 0),
        "hidden_triangle_fraction": round(hidden / max(sum(total.values()), 1), 4),
        "views": [list(map(lambda v: round(v, 3), d)) for d in VIEW_DIRECTIONS],
    }


def mesh_frame(obj):
    """Bounds in the mesh's own frame - what a runtime reading mesh.bounds sees.

    Checking root-local alone missed a display panel whose mesh-local Y extent
    was 0 (knowhow 1). The stick is authored in the pivot frame, the body in
    the root frame; both must have real extent on every axis.
    """
    co = np.array([v.co for v in obj.data.vertices])
    size = co.max(axis=0) - co.min(axis=0)
    return {"size_blender_m": [round(float(v), 6) for v in size],
            "min_extent_mm": round(float(size.min()) * 1000.0, 3)}


def roles_present(obj):
    colours = obj.data.color_attributes["role_color"].data
    found = set()
    for item in colours:
        for role, value in ROLE_COLOUR.items():
            if all(abs(item.color[i] - value[i]) < 1e-4 for i in range(4)):
                found.add(role)
    return sorted(found)


def round_trip(fbx, expected):
    """Re-import the FBX and compare what Unity will be handed."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), axis_forward="-Z", axis_up="Y")
    rows = {}
    for obj in bpy.data.objects:
        row = {"type": obj.type,
               "parent": obj.parent.name if obj.parent else None}
        if obj.type == "MESH":
            obj.data.calc_loop_triangles()
            row["triangles"] = len(obj.data.loop_triangles)
            points = world_array(obj)
            row["min"] = [round(float(v), 5) for v in points.min(axis=0)]
            row["max"] = [round(float(v), 5) for v in points.max(axis=0)]
            row["uv_layers"] = len(obj.data.uv_layers)
            row["materials"] = [s.material.name for s in obj.material_slots if s.material]
        rows[obj.name] = row
    mismatches = []
    for name, want in expected.items():
        got = rows.get(name)
        if got is None:
            mismatches.append(f"{name}: missing")
            continue
        for key, value in want.items():
            have = got.get(key)
            if isinstance(value, list):
                if any(abs(a - b) > 1e-4 for a, b in zip(value, have)):
                    mismatches.append(f"{name}.{key}: {have} != {value}")
            elif have != value:
                mismatches.append(f"{name}.{key}: {have} != {value}")
    return {"objects": rows, "mismatches": mismatches}


def verdict(ok, review_only=False):
    if ok is None:
        return "N/A"
    if ok:
        return "PASS"
    return "REVIEW" if review_only else "FAIL"


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

POSES = {
    "rest": (0.0, 0.0),
    "pitch_plus20": (TRAVEL_DEG, 0.0),
    "yaw_plus20": (0.0, TRAVEL_DEG),
    "corner_20_20": (TRAVEL_DEG, TRAVEL_DEG),
}


def render_set(objects, pivot, gimbal, output_dir):
    prefix = f"Preview_{ASSET}_{THEME}_P1"
    written = {}
    focus, radius, scale = p1.rig_for(objects)
    for label, view in p1.VIEWS.items():
        path = output_dir / f"{prefix}_{label}.png"
        p1.shot(focus, radius, view, 52.0, scale, path)
        written[label] = path
    for label, (pitch, yaw) in POSES.items():
        if label == "rest":
            continue
        pose(pivot, gimbal, pitch, yaw)
        path = output_dir / f"{prefix}_{label}.png"
        p1.shot(focus, radius, p1.VIEWS["oblique_right"], 52.0, scale, path)
        written[label] = path
    pose(pivot, gimbal, 0.0, 0.0)
    return written


def contact_sheet(images, output_path, columns=4):
    labels = list(images)
    tiles = [review.load_rgba(images[label]) for label in labels]
    height, width = tiles[0].shape[:2]
    rows = math.ceil(len(tiles) / columns)
    gap = 16
    canvas = np.zeros((rows * height + (rows - 1) * gap,
                       columns * width + (columns - 1) * gap, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, (label, tile) in enumerate(zip(labels, tiles)):
        row, column = divmod(index, columns)
        top = (rows - 1 - row) * (height + gap)
        left = column * (width + gap)
        canvas[top:top + height, left:left + width] = tile
    for index, label in enumerate(labels):
        row, column = divmod(index, columns)
        review.draw_label(canvas, label.upper().replace("_", " "),
                          column * (width + gap) + 14, row * (height + gap) + 14)
    review.save_rgba(canvas, output_path)


# --------------------------------------------------------------------------

def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    review_dir = tree / "review"
    report_dir = tree / "reports"
    for folder in (tree, review_dir, report_dir):
        folder.mkdir(parents=True, exist_ok=True)

    p1.clear_scene()
    review.configure_scene()
    material = preview_material()
    root = bpy.data.objects.new(ROOT_NAME, None)
    bpy.context.collection.objects.link(root)
    body = build_body()
    body.parent = root
    pivot = bpy.data.objects.new(PIVOT_NAME, None)
    pivot.location = (0.0, -PIVOT_D, 0.0)
    pivot.parent = root
    gimbal = bpy.data.objects.new(GIMBAL_NAME, None)
    gimbal.parent = pivot
    for empty in (pivot, gimbal):
        empty.empty_display_type = "ARROWS"
        empty.empty_display_size = 0.02
        bpy.context.collection.objects.link(empty)
    stick = build_stick()
    stick.parent = gimbal
    for obj in (body, stick):
        finish(obj, material)
    bpy.context.view_layer.update()

    health = {obj.name: p1.mesh_health(obj) for obj in (body, stick)}
    rest = p1.world_bounds([body, stick])
    size = rest["size"]
    totals = sum(row["triangles"] for row in health.values())
    sweep_row = sweep(body, pivot, gimbal, stick)
    stops = stop_angles(body, pivot, gimbal, stick)
    seen = visibility([body, stick])
    frames = {obj.name: mesh_frame(obj) for obj in (body, stick)}
    materials = sorted({s.material.name for o in (body, stick)
                        for s in o.material_slots if s.material})

    axis_stops = [stops[k] for k in ("+pitch", "-pitch", "+yaw", "-yaw")]
    diagonal_stops = [stops[k] for k in ("+pitch+yaw", "-pitch-yaw")]
    gates = {
        "triangles_per_object": verdict(
            max(r["triangles"] for r in health.values()) <= TRIANGLES_PER_OBJECT),
        "triangles_total_within_existing_range": verdict(
            TRIANGLES_TOTAL_REFERENCE[0] <= totals <= TRIANGLES_TOTAL_REFERENCE[1]),
        "renderers": verdict(len([o for o in (body, stick) if o.type == "MESH"])
                             == RENDERERS),
        "materials": verdict(len(materials) <= MATERIAL_LIMIT),
        "non_manifold_zero": verdict(
            sum(r["non_manifold_edges"] for r in health.values()) == 0),
        "zero_area_zero": verdict(
            sum(r["zero_area_faces"] for r in health.values()) == 0),
        "mount_plane": verdict(abs(rest["max"][1]) < 1e-9),
        "unit_scale": verdict(all(abs(v - 1.0) < 1e-9 for v in root.scale)),
        "sweep_no_overlap": verdict(sweep_row["overlapping_triangle_pairs"] == 0),
        "end_stop_axis": verdict(all(s is not None and TRAVEL_DEG < s <= STOP_DEG + 2.0
                                     for s in axis_stops)),
        "end_stop_diagonal": verdict(all(s is not None and TRAVEL_DEG < s
                                         for s in diagonal_stops)),
        "every_part_visible": verdict(not seen["parts_never_visible"]),
        "mesh_local_extent": verdict(all(f["min_extent_mm"] > 1.0
                                         for f in frames.values())),
        # No control.joystick row exists in GREYBOX_INSTRUMENT_SPEC.md yet, so
        # the envelope and the travel are proposals for Codex, not a pass.
        "envelope_contract": "N/A",
        "motion_contract": "REVIEW",
    }

    row = {
        "asset": ASSET,
        "type_id_proposed": "control.joystick",
        "theme": THEME,
        "phase": "Theme4 Joystick P1 (shape prototype)",
        "style_guide": "docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md",
        "expected_before_measurement": EXPECTED,
        "hierarchy": {
            ROOT_NAME: [BODY_NAME, PIVOT_NAME],
            PIVOT_NAME: [GIMBAL_NAME],
            GIMBAL_NAME: [PART_NAME],
        },
        "renderers": RENDERERS,
        "materials": materials,
        "material_roles_authoring": {obj.name: roles_present(obj) for obj in (body, stick)},
        "triangles_per_object": {n: r["triangles"] for n, r in health.items()},
        "triangles_total": totals,
        "triangles_total_existing_range": list(TRIANGLES_TOTAL_REFERENCE),
        "non_manifold_edges": sum(r["non_manifold_edges"] for r in health.values()),
        "zero_area_faces": sum(r["zero_area_faces"] for r in health.values()),
        "rest_bounds_blender": rest,
        "rest_width_height_depth_m": [size[0], size[2], size[1]],
        "rest_bounds_unity": p1.to_unity(rest),
        "mesh_local_frames": frames,
        "motion": {
            "pivot_local_blender": [round(v, 6) for v in pivot.location],
            "pivot_local_unity": [round(pivot.location[0], 6),
                                  round(-pivot.location[2], 6),
                                  round(-pivot.location[1], 6)],
            "axes": {PIVOT_NAME: {"blender_axis": "X", "unity_axis": "X"},
                     GIMBAL_NAME: {"blender_axis": "Z", "unity_axis": "Y"}},
            "travel_deg": [-TRAVEL_DEG, TRAVEL_DEG],
            "designed_stop_deg": STOP_DEG,
            "sign_note": ("the FBX conversion flips rotation signs as it does for "
                          "the Lever (alignment 268); Codex should confirm both "
                          "axes in Unity before a runtime range is fixed"),
        },
        "sweep": sweep_row,
        "stop_angles_deg": stops,
        "visibility": seen,
        "design_intent": {
            "gate_half_m": round(GATE_HALF, 6),
            "gate_corner_radius_m": GATE_CORNER_R,
            "collar_radius_m": COLLAR_R,
            "collar_lower_face_delta_m": COLLAR_LOW,
            "ball_radius_m": BALL_R,
            "ball_seat_gap_m": BALL_GAP,
            "bezel_cone_half_angle_deg": round(BEZEL_CONE_DEG, 3),
            "combined_stop_tilt_deg": round(COMBINED_STOP_DEG, 3),
            "shut_line_m": SHUT_LINE,
            "draft_deg": DRAFT_DEG,
            "grip_belly_width_depth_mm": [round(2 * GRIP_BAND[4][1] * 1000, 1),
                                          round((GRIP_BAND[4][2] + GRIP_BAND[4][3]) * 1000, 1)],
            "grip_length_mm": round((GRIP_HEAD[-1][0] - GRIP_NECK[0][0]) * 1000, 1),
        },
        "gates": gates,
    }

    blend = tree / f"BL_{ASSET}_{THEME}_{TAG}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    row["blend"] = str(blend.relative_to(project_root))
    row["blend_sha256"] = m1.digest(blend)

    if not args.skip_render:
        images = render_set([body, stick], pivot, gimbal, review_dir)
        sheet = tree / f"ContactSheet_{ASSET}_{THEME}_P1.png"
        contact_sheet(images, sheet)
        row["images"] = {k: str(v.relative_to(project_root)) for k, v in images.items()}
        row["contact_sheet"] = str(sheet.relative_to(project_root))

    fbx = tree / f"SM_{ASSET}_{THEME}_{TAG}.fbx"
    fbx.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [root] + list(root.children_recursive):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    settings = dict(toggle.EXPORT_SETTINGS)
    settings.update(use_triangles=False, mesh_smooth_type="EDGE", colors_type="NONE")
    bpy.ops.export_scene.fbx(filepath=str(fbx), **settings)
    row["fbx"] = str(fbx.relative_to(project_root))
    row["fbx_sha256"] = m1.digest(fbx)

    expected = {
        ROOT_NAME: {"type": "EMPTY", "parent": None},
        PIVOT_NAME: {"type": "EMPTY", "parent": ROOT_NAME},
        GIMBAL_NAME: {"type": "EMPTY", "parent": PIVOT_NAME},
        BODY_NAME: {"type": "MESH", "parent": ROOT_NAME,
                    "triangles": health[BODY_NAME]["triangles"],
                    "min": p1.world_bounds([body])["min"],
                    "max": p1.world_bounds([body])["max"]},
        PART_NAME: {"type": "MESH", "parent": GIMBAL_NAME,
                    "triangles": health[PART_NAME]["triangles"],
                    "min": p1.world_bounds([stick])["min"],
                    "max": p1.world_bounds([stick])["max"]},
    }
    trip = round_trip(fbx, expected)
    row["fbx_round_trip"] = trip
    gates["fbx_round_trip"] = verdict(not trip["mismatches"])
    gates["fbx_no_extra_objects"] = verdict(set(trip["objects"]) == set(expected))

    counts = {}
    for value in gates.values():
        counts[value] = counts.get(value, 0) + 1
    row["gate_counts"] = counts
    row["status"] = ("fail" if counts.get("FAIL") else
                     "review" if counts.get("REVIEW") else "pass")
    row["authoring_environment"] = blender_compat.provenance()
    report = report_dir / f"{ASSET}_{THEME}_P1.report.json"
    report.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    print(f"[Theme4Joystick] {totals} tris "
          f"({row['triangles_per_object']}), stops {stops}, "
          f"sweep overlaps {sweep_row['overlapping_triangle_pairs']}, "
          f"min gap {sweep_row['min_vertex_clearance']}, gates {counts}")
    print(f"[Theme4Joystick] wrote {report.relative_to(project_root)}")
    if counts.get("FAIL"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
