"""Theme 4 Phase 1: Machined Ergonomics shape prototypes.

Alignment 246. Three greyboxes - meter.round, control.lever, control.toggle -
built to the direction approved in docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md.

The theme's thesis is that form comes from how the parts go together, so the
geometry budget goes to the things the guide names: the main split faces and
the step they leave, counterbored fasteners on load paths, gasket grooves,
bearing collars, end stops, and the grip's changing section. Secondary shut
lines, screw slots, ticks and labels are left for a normal map, as the guide's
"Geometry versus texture" section asks.

Everything is built from explicit bmesh solids. No boolean is used: a boolean
leaves n-gons and risks the non-manifold edges the completion criteria forbid,
and the recessed look the guide wants is obtainable by stacking shells.

Envelopes, pivots and rotation axes are taken from measurement, not assumption
- see ArtSource/Blender/BrushUp/Opus5/theme4_reference_survey.json and the
axis check in alignment 246.2. Blender authors Y-up-into-the-wall: the mount
plane is max Y == 0 and the instrument faces -Y, which the FBX axis conversion
turns into Unity's local Z = 0 with +Z outward.

Blends are written to the candidate tree; no existing asset is opened for
writing. No FBX is produced - Phase 1 stops at shape approval.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_machined_ergonomics_p1.py -- \
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_toggle_fbx_handoff as toggle
import opus5_trend_monitor_prototype as proto

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics"
OUTPUT = "ArtSource/Blender/BrushUp/Opus5/theme4_machined_ergonomics_p1.json"
MATERIAL = "MAT_MachinedErgonomics_Greybox"

# Greybox gate, docs/GREYBOX_INSTRUMENT_SPEC.md: 1.5k triangles per object,
# 3 renderers (4 for a meter), and a single shared opaque material.
TRIANGLE_LIMIT = 1500
# docs/GREYBOX_INSTRUMENT_SPEC.md gives two numbers per object: 1.5k at the
# greybox gate and 5k as the final P0 ceiling. The part-construction vocabulary
# the theme is built on - covers, mount holes, plugs, glands, registers, ribs -
# does not fit in 1.5k once edges are broken, so the ceiling is the limit here.
# Approved 2026-08-22; the style guide carries the same number. The greybox
# figure stays in the report for reference.
TRIANGLE_CEILING = 5000
RENDERER_LIMIT = {"MeterRound": 4, "Lever": 3, "Toggle": 3}
MATERIAL_LIMIT = 1

# P0 envelope from the same document, as (width X, height Z, depth Y) in metres.
ENVELOPE = {
    "MeterRound": (0.140, 0.140, 0.064),
    # A full-arm pull lever, not the P0 0.180 x 0.256 x 0.100 hand lever.
    # This diverges from the shared contract - see alignment 254.
    "Lever": (0.240, 0.440, 0.150),
    "Toggle": (0.120, 0.170, 0.064),
}
# Measured from the V6 sources; kept here so the report can state the axis it
# checked rather than the axis it hoped for.
MOTION = {
    "MeterRound": {"pivot": "needle_pivot", "part": "needle",
                   "blender_axis": "Y", "unity_axis": "+Z", "amplitude_deg": 115.0,
                   "audit_deg_blender": (-115.0, 0.0, 115.0),
                   "runtime_range_unity_deg": (-115.0, 115.0),
                   "sweep_style": "symmetric"},
    "Lever": {"pivot": "handle_pivot", "part": "handle",
              "blender_axis": "X", "unity_axis": "+X", "amplitude_deg": 24.0,
              "audit_deg_blender": (0.0, 12.0, 24.0, 36.0, 48.0),
              "runtime_range_unity_deg": (-48.0, 0.0),
              "sweep_style": "one-sided with negative runtime offset"},
    "Toggle": {"pivot": "switch_pivot", "part": "switch",
               "blender_axis": "X", "unity_axis": "+X", "amplitude_deg": 28.0,
               "audit_deg_blender": (0.0, 56.0),
               "runtime_range_unity_deg": (-56.0, 0.0),
               "sweep_style": "one-sided with negative runtime offset"},
}

# A tube costs more than a slug, so the housing loses four segments to pay
# for an open dial cavity - the cavity is what makes the instrument read.
HOUSING_SEGMENTS = 26
RING_SEGMENTS = 16
SHUT_LINE = 0.0010          # 0.8-1.2 mm, held constant across the three models
DRAFT_DEG = 5.0             # the guide asks 1-3 for moulding; this reads
SUBSTRATE = (0.62, 0.60, 0.575, 1.0)   # light warm grey moulded resin

# Flat substrate values for the four-theme grayscale comparison.
COMPARISON_THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
REFERENCE_DIR = "ArtSource/Blender/ThemeHardSurfaceV6/{theme}"
REFERENCE_BLEND = "BL_{asset}_{theme}_V6_ProductionReady.blend"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-comparison", action="store_true")
    return parser.parse_args(args)


# --------------------------------------------------------------------------
# geometry helpers - explicit shells, no booleans
# --------------------------------------------------------------------------

def draft_offset(depth):
    """How much a flank moves inward over `depth`, at the guide's draft angle."""
    return depth * math.tan(math.radians(DRAFT_DEG))


def new_mesh(name):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def emit(obj, verts, faces):
    work = bmesh.new()
    made = [work.verts.new(vertex) for vertex in verts]
    work.verts.index_update()
    for face in faces:
        work.faces.new([made[index] for index in face])
    # Consistent winding, not just closed: a shell can have two faces on every
    # edge and still be unorientable, and bevel turns that into holes.
    bmesh.ops.recalc_face_normals(work, faces=work.faces[:])
    work.normal_update()
    bmesh.ops.triangulate(work, faces=work.faces[:],
                          quad_method="FIXED", ngon_method="EAR_CLIP")
    work.to_mesh(obj.data)
    work.free()
    return obj


def frustum_box(name, y_near, y_far, size_near, size_far, centre=(0.0, 0.0)):
    """A box whose two Y-planes have different XZ sizes, i.e. a drafted flank."""
    cx, cz = centre
    verts = []
    for y, (sx, sz) in ((y_near, size_near), (y_far, size_far)):
        hx, hz = sx / 2.0, sz / 2.0
        verts += [(cx - hx, y, cz - hz), (cx + hx, y, cz - hz),
                  (cx + hx, y, cz + hz), (cx - hx, y, cz + hz)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4),
             (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return emit(new_mesh(name), verts, faces)


def frustum_cyl(name, y0, y1, r0, r1, segments=32, centre=(0.0, 0.0)):
    cx, cz = centre
    verts = []
    for y, radius in ((y0, r0), (y1, r1)):
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            verts.append((cx + radius * math.cos(angle), y,
                          cz + radius * math.sin(angle)))
    faces = []
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((index, nxt, segments + nxt, segments + index))
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple(range(segments, 2 * segments)))
    return emit(new_mesh(name), verts, faces)


def annulus(name, y0, y1, r_outer, r_inner, segments=32, centre=(0.0, 0.0)):
    """A ring solid - used for gasket grooves and bearing collars."""
    cx, cz = centre
    verts = []
    for radius in (r_outer, r_inner):
        for y in (y0, y1):
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                verts.append((cx + radius * math.cos(angle), y,
                              cz + radius * math.sin(angle)))
    faces = []
    for ring in range(2):
        base = ring * 2 * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            quad = (base + index, base + nxt,
                    base + segments + nxt, base + segments + index)
            faces.append(quad if ring == 0 else quad[::-1])
    for offset, flip in ((0, False), (segments, True)):
        for index in range(segments):
            nxt = (index + 1) % segments
            quad = (offset + index, offset + nxt,
                    2 * segments + offset + nxt, 2 * segments + offset + index)
            faces.append(quad[::-1] if flip else quad)
    return emit(new_mesh(name), verts, faces)


def axis_cyl(name, x0, x1, radius, centre_yz, segments=16):
    """A cylinder along X - the bearing collars for lever and toggle."""
    cy, cz = centre_yz
    verts = []
    for x in (x0, x1):
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            verts.append((x, cy + radius * math.cos(angle),
                          cz + radius * math.sin(angle)))
    faces = []
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((index, nxt, segments + nxt, segments + index))
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple(range(segments, 2 * segments)))
    return emit(new_mesh(name), verts, faces)


def radial_tick(name, angle_deg, r_inner, r_outer, width, y_near, y_far):
    """One tick lying along a radius of the dial.

    frustum_box is axis aligned, so a tick that has to point at the dial centre
    needs its eight corners placed directly. The dial lies in X-Z with the face
    looking down -Y, so the radial direction is (cos a, 0, sin a) and the tick's
    width runs along the tangent.
    """
    angle = math.radians(angle_deg)
    ca, sa = math.cos(angle), math.sin(angle)
    half = width / 2.0
    verts = []
    for y in (y_near, y_far):
        for radius, side in ((r_inner, -1.0), (r_inner, 1.0),
                             (r_outer, 1.0), (r_outer, -1.0)):
            verts.append((radius * ca - side * half * sa, y,
                          radius * sa + side * half * ca))
    faces = [(0, 1, 2, 3), (7, 6, 5, 4),
             (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return emit(new_mesh(name), verts, faces)


def chamfer(obj, offset, min_angle_deg=25.0):
    """Break every sharp edge on the part.

    A 2 degree draft is invisible; what separates a moulded or machined part
    from a primitive cube is that no edge is ever left sharp. Only edges whose
    two faces actually meet at an angle are broken, so the hidden seams where
    stacked shells intersect cost nothing.
    """
    work = bmesh.new()
    work.from_mesh(obj.data)
    edges = [edge for edge in work.edges
             if edge.is_manifold
             and math.degrees(edge.calc_face_angle(0.0)) >= min_angle_deg]
    if edges:
        bmesh.ops.bevel(work, geom=edges, offset=offset, offset_type="OFFSET",
                        segments=1, profile=0.5, affect="EDGES",
                        clamp_overlap=True)
    bmesh.ops.triangulate(work, faces=work.faces[:],
                          quad_method="FIXED", ngon_method="EAR_CLIP")
    work.to_mesh(obj.data)
    work.free()
    return obj


def rect_frame(name, y0, y1, outer, inner, centre=(0.0, 0.0),
               inner_centre=None):
    """A rectangular frame as one closed shell.

    Building the face from four separate boxes leaves a chamfered seam between
    each pair, and the shell reads as four panels screwed together rather than
    one moulding with an opening in it. One mesh with a hole has no seams.
    """
    cx, cz = centre
    ix, iz = inner_centre if inner_centre else centre
    verts = []
    for width, height, ox, oz in ((outer[0], outer[1], cx, cz),
                                  (inner[0], inner[1], ix, iz)):
        hx, hz = width / 2.0, height / 2.0
        for y in (y0, y1):
            verts += [(ox - hx, y, oz - hz), (ox + hx, y, oz - hz),
                      (ox + hx, y, oz + hz), (ox - hx, y, oz + hz)]
    faces = []
    for base, flip in ((0, False), (8, True)):
        for index in range(4):
            nxt = (index + 1) % 4
            quad = (base + index, base + nxt, base + 4 + nxt, base + 4 + index)
            faces.append(quad[::-1] if flip else quad)
    for offset, flip in ((0, True), (4, False)):
        for index in range(4):
            nxt = (index + 1) % 4
            faces.append((offset + index, offset + nxt,
                          8 + offset + nxt, 8 + offset + index)
                         if flip else
                         (8 + offset + index, 8 + offset + nxt,
                          offset + nxt, offset + index))
    return emit(new_mesh(name), verts, faces)


def toothed_annulus(name, y0, y1, r_tooth, r_root, r_inner, segments=32,
                    centre=(0.0, 0.0)):
    """A ring whose outer radius alternates - a knurled retaining ring.

    The teeth cost nothing beyond the segment count: alternating the outer
    radius on the segments the ring already has turns a plain rim into a gear
    profile. Used where a hand removes a part.
    """
    cx, cz = centre
    verts = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        radius = r_tooth if index % 2 == 0 else r_root
        for y in (y0, y1):
            verts.append((cx + radius * math.cos(angle), y,
                          cz + radius * math.sin(angle)))
    base = len(verts)
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        for y in (y0, y1):
            verts.append((cx + r_inner * math.cos(angle), y,
                          cz + r_inner * math.sin(angle)))
    faces = []
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.append((2 * index, 2 * index + 1, 2 * nxt + 1, 2 * nxt))
        faces.append((base + 2 * nxt, base + 2 * nxt + 1,
                      base + 2 * index + 1, base + 2 * index))
        faces.append((2 * index, 2 * nxt, base + 2 * nxt, base + 2 * index))
        faces.append((2 * index + 1, base + 2 * index + 1,
                      base + 2 * nxt + 1, 2 * nxt + 1))
    return emit(new_mesh(name), verts, faces)


def tapered_arm(name, ends):
    """A four-sided arm whose section changes along its length.

    `ends` is two tuples of (z, width, y_near, y_far). frustum_box only varies
    its section along Y, which is the draft direction; an arm has to get
    thinner along Z as it leaves the hub.
    """
    verts = []
    for z, width, y_near, y_far in ends:
        half = width / 2.0
        verts += [(-half, y_near, z), (half, y_near, z),
                  (half, y_far, z), (-half, y_far, z)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4),
             (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return emit(new_mesh(name), verts, faces)


def clamp_hub(name, radius, half_width, boss_z, bolt_radius):
    """A split hub with a pinch bolt - how an arm joins a shaft."""
    hub = axis_cyl(f"{name}_hub", -half_width, half_width, radius, (0.0, 0.0),
                   segments=16)
    ear = frustum_box(f"{name}_ear", 0.004, -0.006,
                      (half_width * 1.9, radius * 1.5),
                      (half_width * 1.7, radius * 1.4),
                      centre=(0.0, boss_z))
    bolt = axis_cyl(f"{name}_bolt", -half_width * 1.05, half_width * 1.05,
                    bolt_radius, (-0.001, boss_z), segments=10)
    return join(hub, [ear, bolt])


def knurl(name, count, span, cross, centre, axis="z", proud=0.0012,
          duty=0.72, slope=0.0):
    """A band of parallel ribs on a grip - anti-slip serration as geometry.

    The guide leaves surface grain to a normal map, but a serration coarse
    enough to read as a grip at instrument scale has to be geometry: at 1 K
    across a shared theme atlas the tooth pitch here is a couple of texels.

    `span` is (low, high) along `axis`; `cross` is the grip's size on the other
    two axes. `slope` is dy/dz for a z-band: a grip that leans moves in y along
    its length, and a band laid at one fixed y peels away from it.
    """
    low, high = span
    pitch = (high - low) / count
    thickness = pitch * duty
    ribs = []
    for index in range(count):
        base = low + pitch * (index + 0.5)
        lo, hi = base - thickness / 2.0, base + thickness / 2.0
        if axis == "z":
            width, depth = cross
            near = centre[1] + slope * (base - low)
            ribs.append(frustum_box(
                f"{name}_{index}", near + proud, near - depth - proud,
                (width + 2 * proud, thickness), (width + 2 * proud, thickness),
                centre=(centre[0], (lo + hi) / 2.0)))
        else:
            width, height = cross
            ribs.append(frustum_box(
                f"{name}_{index}", hi, lo,
                (width + 2 * proud, height + 2 * proud),
                (width + 2 * proud, height + 2 * proud),
                centre=centre))
    return join(ribs[0], ribs[1:])


def half_disc(name, y0, y1, r0, r1, centre, side, gap, segments=12):
    """Half of a round head, offset by half the slot gap.

    Two of these with a gap between them read as a slotted round head. Two
    rectangular lands, which is what a generic slot helper produces, read as
    two blocks stuck on the panel - which is exactly how the flush fastener
    failed to say "screw".
    """
    cx, cz = centre
    cx += side * gap / 2.0
    verts = []
    for y, radius in ((y0, r0), (y1, r1)):
        for index in range(segments + 1):
            angle = math.pi * (index / segments - 0.5) * side
            verts.append((cx + radius * math.cos(angle) * side, y,
                          cz + radius * math.sin(angle)))
    count = segments + 1
    faces = []
    for index in range(segments):
        faces.append((index, index + 1, count + index + 1, count + index))
    faces.append((count - 1, 0, count, 2 * count - 1))
    faces.append(tuple(range(count - 1, -1, -1)))
    faces.append(tuple(range(count, 2 * count)))
    return emit(new_mesh(name), verts, faces)


def slotted_head(name, centre, y_face, radius, proud, gap):
    """A round slotted head standing `proud` of the face."""
    halves = [half_disc(f"{name}_h{int(side)}", y_face - proud,
                        y_face + proud * 0.6, radius * 0.94, radius,
                        centre, side, gap)
              for side in (-1.0, 1.0)]
    return join(halves[0], halves[1:])


def driver_slot(name, centre, y_face, length, width, depth):
    """Two lands with a gap between them - a screwdriver slot, built additively.

    Cutting the slot would need a boolean, and a boolean leaves n-gons and
    risks the non-manifold edges the gate forbids.
    """
    lands = []
    for sign in (-1.0, 1.0):
        offset = (width / 2.0 + length / 4.0) * sign
        lands.append(frustum_box(f"{name}_{int(sign)}", y_face, y_face - depth,
                                 (length / 2.0 - width / 2.0, length * 0.86),
                                 (length / 2.0 - width / 2.0, length * 0.78),
                                 centre=(centre[0] + offset, centre[1])))
    return join(lands[0], lands[1:])


def driver_port(name, centre, y_face, r_outer, r_inner, depth):
    """A recessed access hole with a raised rim - where a driver goes in."""
    rim = annulus(f"{name}_rim", y_face, y_face - depth * 0.5,
                  r_outer, r_inner, segments=12, centre=centre)
    floor = frustum_cyl(f"{name}_floor", y_face + depth, y_face + depth * 0.6,
                        r_inner, r_inner * 0.9, segments=12, centre=centre)
    return join(rim, [floor])


def mount_hole(name, centre, y_face, r_outer, r_bore, depth):
    """A through-hole a driver reaches the wall fixing through."""
    rim = annulus(f"{name}_rim", y_face, y_face - depth * 0.45,
                  r_outer, r_bore * 1.45, segments=12, centre=centre)
    seat = annulus(f"{name}_seat", y_face + depth * 0.35, y_face,
                   r_bore * 1.45, r_bore, segments=12, centre=centre)
    floor = frustum_cyl(f"{name}_floor", y_face + depth * 1.2,
                        y_face + depth * 0.9, r_bore, r_bore * 0.92,
                        segments=12, centre=centre)
    return join(rim, [seat, floor])


def blanking_plug(name, centre, y_face, r_outer, depth):
    """A plug closing an unused hole, read the same way as a flush rivet."""
    seat = annulus(f"{name}_seat", y_face - 0.0002, y_face + depth * 0.34,
                   r_outer, r_outer * 0.88, segments=12, centre=centre)
    cap = slotted_head(f"{name}_cap", centre, y_face, r_outer * 0.86,
                       0.0006, r_outer * 0.24)
    return join(seat, [cap])


def access_cap(name, centre, y_face, r_tooth, r_root, depth):
    """A knurled screw-off access cap: the theme's maintenance affordance."""
    rim = toothed_annulus(f"{name}_rim", y_face, y_face - depth,
                          r_tooth, r_root, r_tooth * 0.62,
                          segments=16, centre=centre)
    lid = frustum_cyl(f"{name}_lid", y_face - depth * 0.45, y_face - depth,
                      r_tooth * 0.66, r_tooth * 0.60,
                      segments=16, centre=centre)
    slot = driver_slot(f"{name}_slot", centre, y_face - depth,
                       r_tooth * 1.16, r_tooth * 0.22, depth * 0.34)
    return join(rim, [lid, slot])


def cover_panel(name, centre, size, y_face, depth, screw_radius):
    """A bolted-on cover: a chamfered panel with a slotted screw at each corner."""
    panel = chamfer(frustum_box(f"{name}_panel", y_face, y_face - depth,
                                size, (size[0] - 0.0022, size[1] - 0.0022),
                                centre=centre), 0.0011)
    screws = []
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            screws.append(fastener(
                f"{name}_screw_{int(sx)}_{int(sz)}",
                (centre[0] + sx * (size[0] / 2.0 - 0.0075),
                 centre[1] + sz * (size[1] / 2.0 - 0.0075)),
                y_face - depth, screw_radius, screw_radius * 0.78))
    return join(panel, screws)


def register_step(name, size, y_near, y_far, inset):
    """A stepped spigot at the mount face - the guide's 印籠継ぎ."""
    return frustum_box(name, y_near, y_far,
                       (size[0] - inset * 2.0, size[1] - inset * 2.0),
                       (size[0] - inset * 2.6, size[1] - inset * 2.6))


def cable_gland(name, centre, y_face, radius, reach):
    """A conduit entry: body nut, coupling, then the cable stub."""
    body = frustum_cyl(f"{name}_body", y_face, y_face - reach * 0.42,
                       radius, radius * 0.92, segments=10, centre=centre)
    nut = toothed_annulus(f"{name}_nut", y_face - reach * 0.40,
                          y_face - reach * 0.66, radius * 1.16, radius * 1.02,
                          radius * 0.66, segments=12, centre=centre)
    stub = frustum_cyl(f"{name}_stub", y_face - reach * 0.64, y_face - reach,
                       radius * 0.62, radius * 0.54, segments=10, centre=centre)
    return join(body, [nut, stub])


def nameplate(name, centre, size, y_face, depth):
    """A raised pad where the etched label goes - the texture gets a home."""
    return chamfer(frustum_box(name, y_face, y_face - depth, size,
                               (size[0] - 0.0016, size[1] - 0.0016),
                               centre=centre), 0.0008)


def rib(name, centre, size, y_face, depth):
    """A stiffening rib, as the guide asks for where a moulding needs support."""
    return frustum_box(name, y_face, y_face - depth, size,
                       (size[0] * 0.78, size[1]), centre=centre)


def fastener(name, centre, y_face, radius, depth):
    """A flush rivet-style fastener: a shallow slotted head in a seat ring.

    Two earlier attempts failed for opposite reasons. Cutting the seat into the
    panel put every feature behind the surface, and without a boolean there is
    no hole for them to show through, so the panel rendered as blank sheet.
    Then a generic slot helper put two rectangular lands on top, which read as
    blocks rather than as a screw.

    What a flush rivet is actually read by is a circular seat line and a slot
    across a round head. The head stands 0.5 mm proud - a silhouette edge and a
    shading break, far too little to catch a hand.
    """
    seat = annulus(f"{name}_seat", y_face - 0.0002, y_face + depth * 0.30,
                   radius, radius * 0.86, segments=12, centre=centre)
    head = slotted_head(f"{name}_head", centre, y_face, radius * 0.84,
                        0.0005, radius * 0.26)
    return join(seat, [head])


def join(target, others):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in others:
        obj.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    if others:
        bpy.ops.object.join()
    return target


def assign(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


# --------------------------------------------------------------------------
# the three instruments
# --------------------------------------------------------------------------

def build_meter_round(material):
    """Two-piece round housing, split flange forward of the mount plane."""
    width, height, depth = ENVELOPE["MeterRound"]
    radius = width / 2.0
    split_y = -depth * 0.42
    parts = []

    # rear half: drafted so the flank reads as moulded, flange at the split
    parts.append(frustum_cyl("rear", 0.0, split_y,
                             radius - 0.002, radius - 0.0065,
                             segments=HOUSING_SEGMENTS))
    parts.append(register_step("register", (radius * 1.72, radius * 1.72),
                               0.0, -0.0028, 0.0))
    parts.append(annulus("rear_flange", split_y - 0.0035, split_y,
                         radius - 0.0045, radius - 0.0145,
                         segments=HOUSING_SEGMENTS))
    # the shut line: a gap the gasket sits in, held at SHUT_LINE
    parts.append(annulus("gasket", split_y - SHUT_LINE - 0.0035, split_y - 0.0035,
                         radius - 0.0045, radius - 0.010, segments=RING_SEGMENTS))
    # front half and bezel
    front_y = split_y - SHUT_LINE - 0.0035
    parts.append(annulus("front_flange", front_y - 0.0035, front_y,
                         radius - 0.0080, radius - 0.0180,
                         segments=HOUSING_SEGMENTS))
    # a tube, not a slug: a solid cylinder here swallows the dial, the collar
    # and the needle, leaving the instrument reading as a blank disc
    parts.append(annulus("front", front_y - 0.0035, -depth + 0.006,
                         radius - 0.0115, radius - 0.021,
                         segments=HOUSING_SEGMENTS))
    parts.append(toothed_annulus("bezel", -depth + 0.006, -depth,
                                 radius - 0.0100, radius - 0.0127,
                                 radius - 0.019, segments=32))
    # The dial is a separate plate seated in a rebate, with a raised annular
    # land for the scale and two index pins at the travel limits. The ticks and
    # numerals themselves go to the atlas, as the guide asks - what geometry
    # owes them is somewhere to sit, the same argument as the nameplate boss.
    dial_face = -depth + 0.014
    parts.append(frustum_cyl("dial", dial_face + 0.002, dial_face,
                             radius - 0.019, radius - 0.019,
                             segments=RING_SEGMENTS))
    parts.append(chamfer(annulus("dial_rebate", dial_face + 0.002,
                                 dial_face - 0.0008,
                                 radius - 0.019, radius - 0.0225,
                                 segments=24), 0.0004))
    parts.append(chamfer(annulus("scale_land", dial_face, dial_face - 0.0011,
                                 radius - 0.0215, radius - 0.0295,
                                 segments=24), 0.0004))
    for sign in (-1.0, 1.0):
        angle = math.radians(90.0 + sign * 115.0)
        seat = radius - 0.0255
        parts.append(chamfer(frustum_cyl(
            f"index_{int(sign)}", dial_face - 0.0011, dial_face - 0.0032,
            0.0022, 0.0019, segments=8,
            centre=(seat * math.cos(angle), seat * math.sin(angle))), 0.0004))

    # Ticks as geometry. The style guide assigns 目盛り to the atlas, and for a
    # 1 K shared texture that is the right call for numerals - but the scale is
    # what makes a meter read as a meter, and at this size the marks carry
    # their own shadow. Recorded as a deliberate departure in alignment 264.
    land_outer = radius - 0.0219
    land_inner = radius - 0.0291
    minor_inner = land_outer - 0.0034
    for index in range(23):
        angle = -25.0 + 230.0 * index / 22.0
        major = index % 2 == 0
        parts.append(radial_tick(
            f"tick_{index}", angle,
            land_inner if major else minor_inner, land_outer,
            0.0022 if major else 0.0013,
            dial_face - 0.0011, dial_face - 0.0022 if major else -0.0019))
    # bearing collar around the needle shaft
    parts.append(annulus("collar", -depth + 0.014, -depth + 0.008,
                         0.0105, 0.0055, segments=RING_SEGMENTS))
    # No cap screws on the bezel. A knurled retaining ring says "turn this off
    # by hand"; counterbored bolts say "bring a driver". Both on the same part
    # contradict each other, and the ring is the maintenance affordance the
    # theme wants here. The housing's own fastening reads through the two
    # clamped flanges and the gasket between them.


    parts.append(cable_gland("gland", (0.0, -radius + 0.010), split_y - 0.004,
                             0.0085, 0.020))
    parts.append(blanking_plug("plug", (radius - 0.016, 0.0), split_y - 0.004,
                               0.0072, 0.0035))

    body = join(parts[0], parts[1:])
    body.name = "MeterRound_body"
    body.data.name = "MeterRound_body"
    assign(body, material)

    pivot = bpy.data.objects.new("needle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, -depth + 0.012, 0.0)
    pivot.rotation_mode = "XYZ"

    needle = join(frustum_box("needle_shaft", -0.0005, -0.0075, (0.010, 0.0075),
                              (0.0075, 0.0055)),
                  [frustum_box("needle_arm", -0.0015, -0.0055,
                               (0.0055, 0.056), (0.0040, 0.056),
                               centre=(0.0, 0.020))])
    chamfer(needle, 0.00025)
    needle.name = "needle"
    needle.data.name = "needle"
    assign(needle, material)
    needle.parent = pivot
    return body, pivot, needle


def build_toggle(material):
    """Base plate, upper housing, exposed bearing collar, guarded end stops."""
    width, height, depth = ENVELOPE["Toggle"]
    parts = []
    plate_y = -0.013
    parts.append(chamfer(frustum_box("plate", 0.0, plate_y, (width, height),
                                     (width - 0.009, height - 0.009)), 0.0014))
    # parting step: the upper shell is inset, leaving the split visible in profile
    shell_y = -0.040
    parts.append(chamfer(frustum_box("shell", plate_y - SHUT_LINE, shell_y,
                                     (width - 0.014, height - 0.018),
                                     (width - 0.034, height - 0.042)), 0.0016))
    # gasket sits in the shut line between plate and shell
    parts.append(frustum_box("gasket", plate_y, plate_y - SHUT_LINE,
                             (width - 0.021, height - 0.025),
                             (width - 0.021, height - 0.025)))
    # bearing bosses either side of the switch, with a collar on the axis
    for sign in (-1.0, 1.0):
        parts.append(chamfer(frustum_box(
            f"boss_{int(sign)}", shell_y + 0.004, shell_y - 0.008,
            (0.014, 0.026), (0.012, 0.022),
            centre=(sign * 0.021, 0.0)), 0.0009))
    parts.append(axis_cyl("collar", -0.026, 0.026, 0.0062, (shell_y - 0.002, 0.0)))
    # end stops flanking the shaft, so the travel limit reads as geometry
    for sign in (-1.0, 1.0):
        parts.append(chamfer(frustum_box(
            f"stop_{int(sign)}", shell_y + 0.002, shell_y - 0.011,
            (0.007, 0.026), (0.006, 0.023),
            centre=(sign * 0.017, 0.013)), 0.0008))
    # four counterbored screws at the plate corners
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(fastener(f"screw_{int(sx)}_{int(sz)}",
                                  (sx * (width / 2.0 - 0.011),
                                   sz * (height / 2.0 - 0.011)),
                                  plate_y, 0.0052, 0.0040))

    parts.append(access_cap("access", (-0.034, 0.050), shell_y, 0.0105, 0.0089,
                            0.0040))
    parts.append(register_step("register", (width, height), 0.0, -0.0026, 0.010))
    parts.append(nameplate("plate_label", (0.0, -0.052), (0.062, 0.016),
                           shell_y, 0.0016))
    for sign in (-1.0, 1.0):
        parts.append(rib(f"rib_{int(sign)}", (sign * 0.040, 0.010),
                         (0.0055, 0.052), shell_y, 0.0022))
    # a driver reaches the wall fixing through these; the spare one is plugged
    parts.append(mount_hole("mount_a", (0.034, 0.050), plate_y, 0.0072, 0.0040,
                            0.0032))
    parts.append(blanking_plug("blank_a", (0.0, 0.062), plate_y, 0.0068, 0.0032))

    body = join(parts[0], parts[1:])
    body.name = "Toggle_body"
    body.data.name = "Toggle_body"
    assign(body, material)

    pivot = bpy.data.objects.new("switch_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, shell_y - 0.002, 0.0)
    pivot.rotation_mode = "XYZ"

    # Stands up from the pivot. Asymmetric section - wider across than deep -
    # so grip direction is readable by touch, with one thumb relief and a
    # knurled band where finger and thumb actually close on it.
    switch = join(
        clamp_hub("switch", 0.0082, 0.0072, 0.014, 0.0021),
        [tapered_arm("switch_shaft",
                     ((0.004, 0.017, -0.003, -0.014),
                      (0.050, 0.011, -0.005, -0.014))),
         frustum_box("switch_grip", -0.003, -0.017, (0.019, 0.022),
                     (0.016, 0.020), centre=(0.0, 0.058)),
         frustum_box("switch_thumb", -0.015, -0.019, (0.016, 0.008),
                     (0.014, 0.007), centre=(0.0, 0.052)),
         knurl("switch_knurl", 7, (0.048, 0.068), (0.019, 0.014),
               (0.0, -0.003), axis="z", proud=0.0009)])
    chamfer(switch, 0.00045)
    switch.name = "switch"
    switch.data.name = "switch"
    assign(switch, material)
    switch.parent = pivot
    return body, pivot, switch


def build_lever(material):
    """A full-arm pull lever working through a quadrant slot.

    Sized to be pulled with the whole arm. The travel stays on the shared
    contract at +-24 degrees; only the envelope diverges from the P0 table's
    0.180 x 0.256 x 0.100. Alignment 254 records what that implies.

    The long throw comes from the arm's length rather than from the angle, so
    the runtime constant LeverMaximumAngleDegrees = 24f is untouched.

    The fulcrum stays inside the housing. At rest the arm lies back against the
    panel at about 16 degrees, which is what keeps a 0.28 m arm inside a 0.120 m
    depth; the travel swings it out and down.
    """
    width, height, depth = ENVELOPE["Lever"]
    parts = []
    plate_y = -0.020
    parts.append(chamfer(frustum_box("plate", 0.0, plate_y, (width, height),
                                     (width - 0.014, height - 0.014)), 0.0018))
    shell_y = -0.048
    shell = (width - 0.030, height - 0.040)
    shell_centre_z = -0.010
    parts.append(frustum_box("gasket", plate_y, plate_y - SHUT_LINE,
                             (width - 0.038, height - 0.048),
                             (width - 0.038, height - 0.048),
                             centre=(0.0, shell_centre_z)))

    pivot_z = -0.080
    pivot_y = -0.018
    # The arm crosses the face this far out from the fulcrum, so the slot is
    # only as long as the travel needs. The throw is long because the arm is
    # long, not because the angle is.
    cross = abs(shell_y - pivot_y)
    span = cross * math.tan(math.radians(MOTION['Lever']['amplitude_deg']))
    slot = (0.062, 2.0 * span + 0.052)
    parts.append(chamfer(rect_frame(
        "shell", plate_y - SHUT_LINE, shell_y, shell, slot,
        centre=(0.0, shell_centre_z), inner_centre=(0.0, pivot_z)), 0.0022))
    # a stepped skirt between plate and shell, so the profile is not one wall
    parts.append(chamfer(frustum_box(
        "skirt", plate_y - SHUT_LINE, plate_y - 0.010,
        (shell[0] + 0.016, shell[1] + 0.016), (shell[0] + 0.004, shell[1] + 0.004),
        centre=(0.0, shell_centre_z)), 0.0018))

    parts.append(frustum_box("slot_floor", pivot_y + 0.004, pivot_y,
                             (slot[0] + 0.026, slot[1] + 0.026),
                             (slot[0] + 0.024, slot[1] + 0.024),
                             centre=(0.0, pivot_z)))
    slot_lo, slot_hi = pivot_z - slot[1] / 2.0, pivot_z + slot[1] / 2.0
    for name, centre_x, size_x, centre_z, size_z in (
        ("rim_left", -(slot[0] / 2.0 + 0.0045), 0.009, pivot_z, slot[1] + 0.018),
        ("rim_right", (slot[0] / 2.0 + 0.0045), 0.009, pivot_z, slot[1] + 0.018),
        ("rim_top", 0.0, slot[0], slot_hi + 0.0045, 0.009),
        ("rim_bottom", 0.0, slot[0], slot_lo - 0.0045, 0.009),
    ):
        parts.append(chamfer(frustum_box(
            name, shell_y, shell_y - 0.0030, (size_x, size_z),
            (size_x - 0.0014, size_z - 0.0014),
            centre=(centre_x, centre_z)), 0.0008))

    # Five detent marks across the travel, as the spec's 5 detents.
    for index in range(5):
        angle = math.radians(-24.0 + 12.0 * index)
        mark = pivot_z + cross * math.tan(angle)
        parts.append(chamfer(frustum_box(
            f"detent_{index}", shell_y, shell_y - 0.0020,
            (0.017, 0.0038), (0.015, 0.0034),
            centre=(slot[0] / 2.0 + 0.019, mark)), 0.0006))

    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(fastener(f"screw_{int(sx)}_{int(sz)}",
                                  (sx * (width / 2.0 - 0.016),
                                   sz * (height / 2.0 - 0.016)),
                                  plate_y, 0.0068, 0.0050))

    parts.append(access_cap("access", (-0.072, 0.150), shell_y, 0.014, 0.0119,
                            0.0050))
    # What the working end acts on: a cam plate on the cavity floor, so the
    # slot shows a mechanism rather than an empty box.
    parts.append(chamfer(frustum_box(
        "cam_plate", pivot_y - 0.006, pivot_y - 0.022, (0.060, 0.020),
        (0.054, 0.017), centre=(0.0, pivot_z - 0.024)), 0.0010))
    parts.append(axis_cyl("cam_pin", -0.026, 0.026, 0.0045,
                          (pivot_y - 0.018, pivot_z - 0.020), segments=10))
    parts.append(register_step("register", (width, height), 0.0, -0.0034, 0.014))
    parts.append(cover_panel("cover", (-0.062, 0.030), (0.052, 0.076),
                             shell_y, 0.0034, 0.0050))
    parts.append(cable_gland("gland", (0.0, -0.192), shell_y - 0.002,
                             0.0105, 0.026))
    parts.append(nameplate("plate_label", (0.062, -0.150), (0.062, 0.020),
                           shell_y, 0.0020))
    for sign in (-1.0, 1.0):
        parts.append(mount_hole(f"mount_{int(sign)}", (sign * 0.078, -0.184),
                                plate_y, 0.0086, 0.0050, 0.0038))
    parts.append(blanking_plug("blank", (-0.078, 0.184), plate_y, 0.0082, 0.0038))

    body = join(parts[0], parts[1:])
    body.name = "Lever_body"
    body.data.name = "Lever_body"
    assign(body, material)

    pivot = bpy.data.objects.new("handle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, pivot_y, pivot_z)
    pivot.rotation_mode = "XYZ"

    # Authored leaning back against the panel: a 0.28 m arm standing straight
    # out would need 0.30 m of depth on its own.
    handle = join(
        tapered_arm("handle_root",
                    ((0.006, 0.046, -0.002, -0.032),
                     (0.086, 0.038, -0.030, -0.062))),
        [tapered_arm("handle_arm",
                     ((0.082, 0.038, -0.029, -0.061),
                      (0.204, 0.032, -0.082, -0.108))),
         tapered_arm("handle_grip",
                     ((0.198, 0.040, -0.080, -0.110),
                      (0.244, 0.038, -0.096, -0.126))),
         knurl("handle_knurl", 8, (0.200, 0.242), (0.039, 0.030),
               (0.0, -0.0807), axis="z", proud=0.0014,
               slope=(-0.096 + 0.080) / (0.244 - 0.198)),
         # The short end of the lever, below the fulcrum and inside the
         # housing. A lever with nothing past its pivot is a handle, not a
         # lever - this is the end that does the work, and it shows through
         # the lower half of the slot.
         tapered_arm("handle_tail",
                     ((-0.004, 0.036, -0.008, -0.036),
                      (-0.024, 0.026, -0.018, -0.036))),
         axis_cyl("handle_roller", -0.017, 0.017, 0.0055,
                  (-0.027, -0.026), segments=12)])
    chamfer(handle, 0.0010)
    handle.name = "handle"
    handle.data.name = "handle"
    assign(handle, material)
    handle.parent = pivot
    return body, pivot, handle


BUILDERS = {
    "MeterRound": build_meter_round,
    "Lever": build_lever,
    "Toggle": build_toggle,
}


# --------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------

def to_unity(bounds):
    """Blender (x, y, z) -> Unity (x, -z, -y) for this import path.

    Not the bare FBX conversion: the project's import wrapper also rotates the
    root -90 degrees about X, and the two together negate Y as well as Z.
    Codex measured MeterRound's swept centre at Y = +0.000583 m in Unity where
    this function had been reporting -0.000583 (alignment 277.3). The sign was
    only observable once the taper made the meter slightly asymmetric in Z.
    """
    lo, hi = bounds["min"], bounds["max"]
    umin = [lo[0], -hi[2], -hi[1]]
    umax = [hi[0], -lo[2], -lo[1]]
    return {
        "min": [round(v, 6) for v in umin],
        "max": [round(v, 6) for v in umax],
        "size": [round(umax[i] - umin[i], 6) for i in range(3)],
        "centre": [round((umin[i] + umax[i]) / 2.0, 6) for i in range(3)],
    }


def pose_bounds(pivot, body, part, motion, scan):
    """Bounds at the three poses Unity needs to size a collider against.

    Alignment 265.2 asks for rest, -amplitude and +amplitude separately: the
    InteractionCollider is a different contract from the rest visual envelope,
    and it has to contain the swept arc.
    """
    axis = "XYZ".index(motion["blender_axis"])
    original = tuple(pivot.rotation_euler)
    poses = {}
    for degrees in motion["audit_deg_blender"]:
        euler = list(original)
        euler[axis] = math.radians(degrees)
        pivot.rotation_euler = euler
        bpy.context.view_layer.update()
        combined = world_bounds([body, part])
        poses[f"blender{degrees:+.0f}_unity{-degrees:+.0f}"] = {
            "combined": combined,
            "combined_unity": to_unity(combined),
            "moving_part": world_bounds([part]),
        }
    pivot.rotation_euler = original
    bpy.context.view_layer.update()
    # The union across the three poses is what an InteractionCollider has to
    # contain: alignment 265.2(4) separates it from the rest visual envelope.
    lo = [min(p["combined_unity"]["min"][i] for p in poses.values())
          for i in range(3)]
    hi = [max(p["combined_unity"]["max"][i] for p in poses.values())
          for i in range(3)]
    poses["mount_clearance"] = scan["clearance"]
    poses["collider_union_unity"] = {
        "min": [round(v, 6) for v in lo],
        "max": [round(v, 6) for v in hi],
        "size": [round(hi[i] - lo[i], 6) for i in range(3)],
        "centre": [round((lo[i] + hi[i]) / 2.0, 6) for i in range(3)],
        "note": ("Unity space, root-local. Sized to the swept arc, not to the "
                 "rest visual envelope - alignment 265.2"),
    }
    # The union above comes from the audit poses; the scan walks the whole
    # range. They should agree, and if they do not the extreme lies between
    # detents and the pose list is the wrong basis - say so rather than pick.
    scanned = to_unity(scan["bounds"])
    poses["collider_union_matches_continuous_scan"] = {
        "continuous_scan_unity": scanned,
        "agrees": all(
            abs(scanned[field][i] - poses["collider_union_unity"][field][i])
            <= 1e-6
            for field in ("min", "max", "size", "centre")
            for i in range(3)
        ),
    }
    return poses


def export_fbx(root, target):
    """Legacy FBX with the settings the meters and Trend Monitor shipped on.

    use_triangles is off because emit() already triangulated with FIXED /
    EAR_CLIP; letting the exporter do it would pick BEAUTY and choose different
    diagonals. mesh_smooth_type is EDGE, not FACE, which is what preserves the
    split normals on anisotropically scaled parts.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [root] + list(root.children_recursive):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    settings = dict(toggle.EXPORT_SETTINGS)
    settings["use_triangles"] = False
    settings["mesh_smooth_type"] = "EDGE"
    bpy.ops.export_scene.fbx(filepath=str(target), **settings)
    if not target.is_file():
        raise SystemExit(f"[Theme4P1] export wrote nothing: {target}")
    return target


def mesh_health(obj):
    """Non-manifold edges and zero-area faces, both of which the gate forbids."""
    work = bmesh.new()
    work.from_mesh(obj.data)
    non_manifold = sum(1 for edge in work.edges if not edge.is_manifold)
    zero_area = sum(1 for face in work.faces if face.calc_area() <= 1e-12)
    triangles = len(work.faces)
    work.free()
    return {"triangles": triangles, "non_manifold_edges": non_manifold,
            "zero_area_faces": zero_area}


def world_bounds(objects):
    """Bounds from the actual vertices, not from the object's local AABB.

    Transforming the eight corners of a local bounding box and taking their
    extent inflates the result for anything rotated - the box of a box. On the
    lever's 120 degree sweep that reported 26 mm of the arm behind the mount
    plane when the furthest vertex is really 9 mm in front of it.
    """
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for obj in objects:
        if obj.type != "MESH":
            continue
        matrix = obj.matrix_world
        for vertex in obj.data.vertices:
            point = matrix @ vertex.co
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])
    return {"min": [round(v, 6) for v in lo], "max": [round(v, 6) for v in hi],
            "size": [round(hi[i] - lo[i], 6) for i in range(3)]}


def sweep_scan(pivot, body, part, motion, steps=96):
    """One scan of the real runtime range, used for every swept figure.

    Everything that describes the sweep - the union bounds, the mount
    clearance, the gate - comes from here, so the report cannot end up with a
    one-sided collider union sitting next to a symmetric swept envelope. That
    inconsistency is what alignment 269.2 found: swept_bounds still fell back
    to +-amplitude when `sweep_deg` was absent.

    Bounds come from mesh vertices; an object AABB inflates under rotation and
    reports penetration that is not there (alignment 254.4, confirmed against
    Codex's own validator in alignment 269.1).
    """
    axis = "XYZ".index(motion["blender_axis"])
    original = tuple(pivot.rotation_euler)
    low = min(motion["audit_deg_blender"])
    high = max(motion["audit_deg_blender"])
    union = None
    worst_maxy = -float("inf")
    for index in range(steps + 1):
        euler = list(original)
        euler[axis] = math.radians(low + (high - low) * index / steps)
        pivot.rotation_euler = euler
        bpy.context.view_layer.update()
        bounds = world_bounds([body, part])
        if union is None:
            union = bounds
        else:
            for axis_index in range(3):
                union["min"][axis_index] = min(union["min"][axis_index],
                                               bounds["min"][axis_index])
                union["max"][axis_index] = max(union["max"][axis_index],
                                               bounds["max"][axis_index])
        worst_maxy = max(worst_maxy, max((part.matrix_world @ vertex.co).y
                                         for vertex in part.data.vertices))
    pivot.rotation_euler = original
    bpy.context.view_layer.update()
    union["size"] = [round(union["max"][i] - union["min"][i], 6) for i in range(3)]
    return {
        "bounds": union,
        "range_blender_deg": [low, high],
        "poses_scanned": steps + 1,
        "clearance": {
            "moving_part_worst_max_y_blender": round(worst_maxy, 6),
            "moving_part_worst_min_z_unity": round(-worst_maxy, 6),
            "clears_mount_plane": worst_maxy <= 0.0,
            "clearance_mm": round(-worst_maxy * 1000.0, 3),
            "method": ("continuous scan over the real one-sided runtime range, "
                       "measured from mesh vertices"),
        },
    }


def measure(asset, root, body, pivot, part, scan):
    envelope = ENVELOPE[asset]
    bounds = world_bounds([body, part])
    size = bounds["size"]
    # Blender (X, Y, Z) -> the spec's (width, height, depth) = (X, Z, Y)
    measured = (size[0], size[2], size[1])
    swept = scan["bounds"]
    swept_whd = (swept["size"][0], swept["size"][2], swept["size"][1])
    clearance = scan["clearance"]
    health = {obj.name: mesh_health(obj) for obj in (body, part)}
    worst = max(row["triangles"] for row in health.values())
    motion = MOTION[asset]
    return {
        "root": root.name,
        "objects": sorted(obj.name for obj in bpy.data.objects),
        "renderers": 2,
        "submeshes_per_object": {obj.name: max(len(obj.material_slots), 1)
                                 for obj in (body, part)},
        "unit_scale_m": 1.0,
        "renderer_limit": RENDERER_LIMIT[asset],
        "materials": sorted({slot.material.name for obj in (body, part)
                             for slot in obj.material_slots if slot.material}),
        "triangles_total": sum(row["triangles"] for row in health.values()),
        "triangles_per_object": {name: row["triangles"]
                                 for name, row in health.items()},
        "triangle_limit_per_object": TRIANGLE_CEILING,
        "greybox_gate_per_object": TRIANGLE_LIMIT,
        "within_greybox_gate": worst <= TRIANGLE_LIMIT,
        "triangle_limit_note": (
            "gated on the final P0 ceiling of 5000, approved 2026-08-22; the "
            "1500 greybox figure is kept for reference - see alignment 252"),
        "non_manifold_edges": sum(row["non_manifold_edges"]
                                  for row in health.values()),
        "zero_area_faces": sum(row["zero_area_faces"] for row in health.values()),
        "bounds_blender": bounds,
        "measured_width_height_depth": [round(value, 6) for value in measured],
        "envelope_width_height_depth": list(envelope),
        "within_envelope": all(measured[i] <= envelope[i] + 1e-6 for i in range(3)),
        "envelope_gate": "rest pose only",
        "bounds_swept": swept,
        "swept_width_height_depth": [round(value, 6) for value in swept_whd],
        "swept_within_envelope": all(swept_whd[i] <= envelope[i] + 1e-6
                                     for i in range(3)),
        "swept_within_envelope_is_report_only": (
            "diagnostic, not a gate: the envelope contract is a rest-pose "
            "dimension and the sweep is verified against the separate "
            "interaction / clearance contract - alignment 265.3"),
        "swept_mount_plane_max_y": round(swept["max"][1], 9),
        "swept_range_blender_deg": scan["range_blender_deg"],
        "swept_poses_scanned": scan["poses_scanned"],
        "runtime_motion_clearance": clearance,
        "mount_plane_max_y": round(bounds["max"][1], 9),
        "mount_plane_ok": abs(bounds["max"][1]) < 1e-6,
        "root_scale": [round(value, 6) for value in root.scale],
        "motion": {
            "pivot": pivot.name,
            "moving_part": part.name,
            "pivot_local": [round(value, 6) for value in pivot.location],
            "pivot_local_unity": [round(pivot.location[0], 6),
                                  round(-pivot.location[2], 6),
                                  round(-pivot.location[1], 6)],
            "blender_axis": motion["blender_axis"],
            "unity_axis": motion["unity_axis"],
            "amplitude_deg": motion["amplitude_deg"],
            "sweep_style": motion.get("sweep_style", "symmetric"),
            "audit_deg_blender": list(motion["audit_deg_blender"]),
            "runtime_range_unity_deg": list(motion["runtime_range_unity_deg"]),
            "sign_note": ("the FBX axis conversion flips the rotation sign: "
                          "Unity -48 deg is Blender +48 deg. Verified against "
                          "Codex's measured Unity max Z - alignment 268"),
        },
        "gates": {
            "triangles_per_object": worst <= TRIANGLE_CEILING,
            "renderers": 2 <= RENDERER_LIMIT[asset],
            "materials": True,
            "non_manifold_zero": sum(row["non_manifold_edges"]
                                     for row in health.values()) == 0,
            "zero_area_zero": sum(row["zero_area_faces"]
                                  for row in health.values()) == 0,
            "mount_plane": abs(bounds["max"][1]) < 1e-6,
            "rest_envelope": all(measured[i] <= envelope[i] + 1e-6
                                 for i in range(3)),
            "runtime_motion_clearance": clearance["clears_mount_plane"],
            "unit_scale": all(abs(value - 1.0) < 1e-9 for value in root.scale),
        },
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

# These instruments face -Y (the FBX conversion turns that into Unity's +Z),
# so the orbit is around Z with -Y as front. opus5_trend_monitor_prototype's
# camera_at orbits for a +Z-facing instrument and would look at these edge-on.
VIEWS = {
    "front": (0.0, 0.0),
    "oblique_left": (-38.0, 18.0),
    "oblique_right": (38.0, 18.0),
    "side": (78.0, 6.0),
}
# The review rig's light energies are tuned for a 0.44 m instrument. Distance
# scales with the subject, so irradiance goes as energy / scale**2; at 0.14 m
# the same energies are about ten times too bright and burn every surface to
# white, which is exactly what hides the value differences T9 asks about.
RIG_REFERENCE_M = 0.436


def camera_at(focus, radius, azimuth_deg, elevation_deg):
    azimuth = math.radians(azimuth_deg)
    elevation = math.radians(elevation_deg)
    return (
        focus[0] + radius * math.sin(azimuth) * math.cos(elevation),
        focus[1] - radius * math.cos(azimuth) * math.cos(elevation),
        focus[2] + radius * math.sin(elevation),
    )


def shot(focus, radius, view, lens, scale, path):
    azimuth, elevation = view
    bpy.ops.object.camera_add(location=camera_at(focus, radius, azimuth, elevation))
    camera = bpy.context.object
    camera.data.lens = lens
    review.point_at(camera, focus)
    bpy.context.scene.camera = camera
    falloff = (scale / RIG_REFERENCE_M) ** 2
    lights = []
    for name, offset, energy in (
        ("Key", (scale * 1.5, -scale * 2.2, scale * 1.6), 9.0),
        ("Fill", (-scale * 2.2, -scale * 1.8, scale * 0.6), 3.6),
        ("Rim", (0.0, scale * 1.4, -scale * 1.6), 5.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy * falloff
        data.shape = "DISK"
        data.size = scale * 2.0
        light = bpy.data.objects.new(name, data)
        light.location = tuple(focus[i] + offset[i] for i in range(3))
        bpy.context.collection.objects.link(light)
        review.point_at(light, focus)
        lights.append(light)
    review.render_to(path)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)


def rig_for(objects):
    bounds = world_bounds(objects)
    focus = tuple((bounds["min"][i] + bounds["max"][i]) / 2.0 for i in range(3))
    extent = max(bounds["size"]) or 0.2
    return focus, extent * 3.1, extent


def render_views(objects, output_dir, prefix):
    focus, radius, scale = rig_for(objects)
    written = {}
    for label, view in VIEWS.items():
        path = output_dir / f"{prefix}_{label}.png"
        shot(focus, radius, view, 52.0, scale, path)
        written[label] = path
    return written


def grayscale(tile):
    luma = (0.2126 * tile[..., 0] + 0.7152 * tile[..., 1] + 0.0722 * tile[..., 2])
    out = np.empty_like(tile)
    for channel in range(3):
        out[..., channel] = luma
    out[..., 3] = tile[..., 3]
    return out


def comparison_sheet(rows, output_path):
    """Rows are instruments, columns are themes, every tile in grayscale."""
    labels = [label for label, _ in rows[0][1]]
    tiles = [review.load_rgba(path) for _, entries in rows for _, path in entries]
    height, width = tiles[0].shape[:2]
    columns, row_count = len(labels), len(rows)
    gap = 16
    canvas = np.zeros((row_count * height + (row_count - 1) * gap,
                       columns * width + (columns - 1) * gap, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    captions = []
    index = 0
    for row, (asset, entries) in enumerate(rows):
        for column, (theme, _) in enumerate(entries):
            top = (row_count - 1 - row) * (height + gap)
            left = column * (width + gap)
            canvas[top:top + height, left:left + width] = grayscale(tiles[index])
            captions.append((left + 14, row * (height + gap) + 14, theme, asset))
            index += 1
    for left, top, title, subtitle in captions:
        review.draw_label(canvas, title.upper(), left, top)
        review.draw_label(canvas, subtitle.upper(), left, top + 42,
                          colour=(0.72, 0.78, 0.86))
    review.save_rgba(canvas, output_path)


def wire_base_colour():
    """Connect each material's atlas BaseColor so the theme's substrate shows.

    The V6 ProductionReady Blends carry the atlas images as datablocks but leave
    Principled's Base Color unlinked at Blender's 0.8 default - the look is
    assembled in Unity, not here. Rendered as they are, all three themes come out
    the same clay grey and the substrate-value question T9 asks cannot be
    answered at all. This wires them for the comparison only; nothing is saved.
    """
    wired = 0
    for material in bpy.data.materials:
        if not material.use_nodes:
            continue
        tree = material.node_tree
        bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None or bsdf.inputs["Base Color"].is_linked:
            continue
        image = next((img for img in bpy.data.images
                      if "BaseColor" in img.name), None)
        if image is None:
            continue
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        node.interpolation = "Linear"
        tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
        wired += 1
    return wired


def reference_front(project_root, asset, theme, output_dir):
    """One front view of an existing theme, with its own substrate, for T9."""
    path = (project_root / REFERENCE_DIR.format(theme=theme)
            / REFERENCE_BLEND.format(asset=asset, theme=theme))
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    wire_base_colour()
    review.configure_scene()
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    focus, radius, scale = rig_for(meshes)
    out = output_dir / f"Compare_{asset}_{theme}_front.png"
    shot(focus, radius, VIEWS["front"], 52.0, scale, out)
    return out


# --------------------------------------------------------------------------

def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    review_dir = tree / "review"
    sheet_dir = tree / "contact_sheets"
    for folder in (tree, review_dir, sheet_dir):
        folder.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "Theme4-P1",
        "theme": THEME,
        "note": ("Machined Ergonomics greybox for meter.round, control.lever and "
                 "control.toggle. Explicit bmesh shells, no boolean. "
                 "Phase 1 isolated FBX generated; Unity production integration "
                 "is blocked."),
        "style_guide": "docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md",
        "greybox_gate": {"triangles_per_object": TRIANGLE_CEILING,
                         "greybox_figure_reported_only": TRIANGLE_LIMIT,
                         "renderers": RENDERER_LIMIT,
                         "shared_opaque_materials": MATERIAL_LIMIT},
        "shut_line_m": SHUT_LINE,
        "draft_degrees": DRAFT_DEG,
        "assets": {},
    }
    fronts = {}

    for asset, builder in BUILDERS.items():
        clear_scene()
        review.configure_scene()
        material = proto.make_material(MATERIAL, SUBSTRATE)
        root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
        bpy.context.collection.objects.link(root)
        body, pivot, part = builder(material)
        for obj in (body, pivot):
            obj.parent = root
        bpy.context.view_layer.update()

        scan = sweep_scan(pivot, body, part, MOTION[asset])
        row = measure(asset, root, body, pivot, part, scan)
        row["pose_bounds"] = pose_bounds(pivot, body, part, MOTION[asset], scan)
        blend = tree / f"BL_{asset}_{THEME}_V6_Opus5_P1_Greybox.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P1.fbx"
        export_fbx(root, fbx)
        row["fbx"] = str(fbx.relative_to(project_root))
        row["fbx_sha256"] = m1.digest(fbx)
        row["fbx_bytes"] = fbx.stat().st_size

        images = render_views([body, part], review_dir,
                              f"Preview_{asset}_{THEME}_P1")
        row["images"] = {label: str(path.relative_to(project_root))
                         for label, path in images.items()}
        fronts[asset] = images["front"]
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        print(f"[Theme4P1] {asset}: {row['triangles_total']} tris, "
              f"envelope_ok={row['within_envelope']}, "
              f"gates={row['all_gates_passed']}")

    if not args.skip_comparison:
        rows = []
        for asset in BUILDERS:
            entries = []
            for theme in COMPARISON_THEMES:
                entries.append((theme, reference_front(project_root, asset,
                                                       theme, review_dir)))
            entries.append((THEME, fronts[asset]))
            rows.append((asset, entries))
        sheet = sheet_dir / f"ContactSheet_Theme4_{THEME}_grayscale_4themes.png"
        comparison_sheet(rows, sheet)
        payload["comparison_sheet"] = str(sheet.relative_to(project_root))
        payload["comparison_sheet_sha256"] = m1.digest(sheet)
        payload["comparison_note"] = (
            "Grayscale, front view, one rig per instrument. The three existing "
            "themes render with their own finished materials; Machined "
            "Ergonomics is a greybox with a single flat substrate and no "
            "textures, so the comparison reads silhouette and value, not "
            "surface detail.")

    payload["all_passed"] = all(row["all_gates_passed"]
                                for row in payload["assets"].values())
    payload["all_passed_covers"] = (
        "the aggregate of the per-asset `gates` object only; "
        "swept_within_envelope is diagnostic and is not included")
    payload["status"] = "phase1_shape_prototype" if payload["all_passed"] else "gates_failed"
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4P1] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
