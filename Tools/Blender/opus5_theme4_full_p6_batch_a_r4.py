"""Batch A R4: the tool bore proved by ray casting, and widened to pass.

Alignment 302.2. R3's `tool_path_audit` measured the distance from each screw
axis to every static *vertex* inside the tool span. That misses the case the
gate exists for: a triangle whose corners are outside the tool cylinder while
its face crosses it. Codex cast axial rays over the tool cross-section instead
and found the nominal 8.2 mm radius blocked on both controls - three of four
Throttle holes, all four PowerSlider holes.

Reproduced here before changing anything: at 8.2 mm both fail, at 8.0 mm the
Throttle passes and the PowerSlider does not, at 7.9 mm both pass. The hit
counts differ from Codex's because the sampling differs (3,076 rays here
against 1,732 there); the pass/fail boundary is identical.

R4 does two things about it. The vertex gate is replaced by the ray gate, and
it reports the largest radius that actually clears rather than a pass mark
against a nominal. And the bore is widened so 8.2 mm is clear with margin
instead of tangent - R3's cutter had its *inradius* at exactly 8.2, so a ray
at 8.2 grazed every flat.

The bore also goes from 12 sides to 16, which alignment 302.2 asked for on
visual grounds; the cost is paid by trimming non-silhouette detail.

Everything else - the boolean drilling method, the split rod/ferrule/grip arm,
the restored tapers - is R3's and unchanged.

The user lifted the no-boolean rule for this revision and asked for the screw
holes to be cut rather than designed around. R2 had taken the skirt and shell
in along X so their material never entered the bore column; that worked, but
it narrowed two tapered mouldings into slabs and read as box modelling.

R3 puts the original tapered `skirt`, `shell` and `plate` dimensions back and
drills them. The access towers R2 needed are gone, because a real hole does
not need a tube standing over it.

Boolean discipline, since non-manifold and zero-area are both gates:

  * the difference is taken per part, before the join. Each target is one
    closed manifold solid, which is the input an exact solver wants; the
    joined body is a pile of interpenetrating solids and is not.
  * the cutter passes clean through both faces of its target - it is never
    coplanar with anything - and carries a conical flare at the mouth, so the
    chamfer comes out of the same operation instead of a second part.
  * after every apply: recalculate normals, merge by distance, triangulate
    with the project's FIXED / EAR_CLIP, then measure. Any bore that leaves a
    non-manifold edge or a zero-area face fails the gate the same as before.

The gasket is not drilled. It is a 1.6 mm shut line buried between the plate
and the shell, invisible from every angle, and drilling it would cost four
bores' worth of triangles to remove material nobody can see; it is narrowed
instead. Everything with a visible taper is drilled.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r4.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_machined_ergonomics_p5 as p5
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_r1 as r1
import opus5_theme4_full_p6_batch_a_r2 as r2
import opus5_theme4_full_p6_batch_b as bb

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r4")
OUTPUT = f"{TREE}/geometry/theme4_full_p6_batch_a_r4.json"
NEUTRAL = ba.NEUTRAL
TARGET_TOTAL = 4800
VALIDATOR_TOTAL = 5000

lathe = p3.lathe
revolve = bb.revolve
SHUT = p1.SHUT_LINE
EMBED = p3.EMBED

# Inherited unchanged from R1 / Batch A.
HUB_SEG = r1.HUB_SEG
PIN_SEG = r1.PIN_SEG
BOSS_SEG = r1.BOSS_SEG
CAP_SEG = r1.CAP_SEG
GRIP_SEG = r1.GRIP_SEG
grip_stops = r1.grip_stops
plain_stops = ba.plain_stops
stations = p3.station_profile
loft = p3.capsule_loft
flush_screw = r2.flush_screw
light_plug = r2.light_plug
light_access_cap = r2.light_access_cap

BORE_SEG = 16
BORE_CLEAR_R = 0.0088        # clear inradius; 0.6 mm past the 8.2 mm tool
# A 16-sided cutter cuts a 16-sided hole and its inradius is what a driver
# fits through. R3 put that inradius exactly on the nominal 8.2 mm, so a
# ray at 8.2 was tangent to every flat and the hole measured blocked.
BORE_R = BORE_CLEAR_R / math.cos(math.pi / BORE_SEG)
BORE_CHAMFER = 0.0013        # conical flare at the mouth

# Grip axes, published so the atlas proposal can lay a cylindrical unwrap on
# exactly the span the mesh occupies instead of guessing at it.
THROTTLE_ARM_A = (0.0, -0.0040, 0.0090)
THROTTLE_ARM_B = (0.0, -0.0640, ba.THROTTLE_ARM + 0.0180)
SLIDER_RAIL_Y = -0.0620
SLIDER_GRIP_A = (0.0, SLIDER_RAIL_Y - 0.0300, -0.0245)
SLIDER_GRIP_B = (0.0, SLIDER_RAIL_Y - 0.0500, 0.0245)

TOOL_NOMINAL_R = 0.0082      # the driver the bore is specified for
SCREW_X_THROTTLE = 0.0975
SCREW_Z_THROTTLE = 0.1505
SCREW_X_SLIDER = 0.0620
SCREW_Z_SLIDER = 0.1430

# Drilled: everything with a visible taper the tool has to pass through.
DRILLED = ("shell", "skirt")


def tool_path_audit(body, screws, y_face, y_base, tool_r=None,
                    directions=96, rings=8, ladder=None):
    """Axial rays over the tool cross-section - a face test, not a vertex test.

    R3 measured axis-to-vertex distance, which cannot see a triangle whose
    corners straddle the cylinder while its face crosses it. That is exactly
    what blocked these bores, so the gate is now what a driver actually does:
    push a cylinder of rays down the hole and see whether anything is in the
    way. It also walks a ladder of radii and reports the largest one that
    clears, so the number is measured rather than asserted against a nominal.
    """
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    tool_r = TOOL_NOMINAL_R if tool_r is None else tool_r
    ladder = ladder or [0.0102, 0.0098, 0.0094, 0.0092, 0.0090, 0.0088,
                        0.0086, 0.0084, 0.0082, 0.0080, 0.0078, 0.0076]
    mesh = body.data
    mesh.calc_loop_triangles()
    verts = [v.co.copy() for v in mesh.vertices]
    faces = [tuple(t.vertices) for t in mesh.loop_triangles]
    bvh = BVHTree.FromPolygons(verts, faces, all_triangles=True)
    start_y = min(y_face, y_base) - 0.0010
    length = abs(y_base - y_face) + 0.0010
    direction = Vector((0.0, 1.0, 0.0))

    def cast(cx, cz, radius):
        hits = rays = 0
        for ring in range(rings + 1):
            r = radius * ring / rings
            count = 1 if ring == 0 else directions
            for j in range(count):
                angle = 2.0 * math.pi * j / count
                origin = Vector((cx + r * math.cos(angle), start_y,
                                 cz + r * math.sin(angle)))
                rays += 1
                if bvh.ray_cast(origin, direction, length)[0] is not None:
                    hits += 1
        return rays, hits

    rows = {}
    for label, (cx, cz) in screws.items():
        rays, hits = cast(cx, cz, tool_r)
        clear = None
        for radius in ladder:
            if cast(cx, cz, radius)[1] == 0:
                clear = radius
                break
        rows[label] = {
            "screw_axis_xz_m": [round(cx, 5), round(cz, 5)],
            "axis_offset_mm": 0.0,
            "rays_at_nominal": rays,
            "hits_at_nominal": hits,
            "path_open": hits == 0,
            "largest_clear_radius_m": clear,
            "largest_clear_diameter_mm": round(clear * 2000.0, 3)
            if clear is not None else None,
            "margin_over_tool_mm": round((clear - tool_r) * 1000.0, 3)
            if clear is not None else None,
            "path_length_mm": round(abs(y_base - y_face) * 1000.0, 3),
        }
    clears = [r["largest_clear_radius_m"] for r in rows.values()
              if r["largest_clear_radius_m"] is not None]
    return {
        "method": ("axial ray cast, %d directions x %d rings plus centre, "
                   "per hole" % (directions, rings)),
        "tool_nominal_diameter_mm": round(tool_r * 2000.0, 3),
        "screw_head_diameter_mm": round(r2.SCREW_HEAD_R * 2000.0, 3),
        "y_face_m": round(y_face, 5),
        "y_base_m": round(y_base, 5),
        "holes": rows,
        "all_open": all(r["path_open"] for r in rows.values()),
        "total_hits_at_nominal": sum(r["hits_at_nominal"]
                                     for r in rows.values()),
        "min_clear_diameter_mm": round(min(clears) * 2000.0, 3)
        if clears else None,
        "max_axis_offset_mm": max(r["axis_offset_mm"] for r in rows.values()),
        "r3_defect": ("the vertex-distance gate reported 16.4 mm on bores a "
                      "ray cast finds blocked at 8.2 mm radius"),
    }


def light_mount(name, centre, y_face, rim_r, bore_r, segments=12):
    """A counterbored mounting hole: rim, seat and bore in one revolve.

    p1.mount_hole costs 236 triangles for a feature 8 mm across. Two of them
    on each control is 472, which is most of what the four bores cost; this is
    the same feature at a quarter of the price.
    """
    return revolve(name, [
        (bore_r, y_face + 0.0026),
        (rim_r * 0.72, y_face + 0.0026),
        (rim_r, y_face - 0.0004),
        (rim_r, y_face - 0.0020),
        (rim_r * 0.78, y_face - 0.0030),
        (bore_r, y_face - 0.0022),
    ], segments=segments, axis="y", centre=centre, smooth=False)


def light_gland(name, centre, y_face, body_r=0.0095, stub_r=0.0058,
                length=0.0230, segments=8):
    """Gland body, nut flat and cable stub in one revolve.

    p1.cable_gland is a three-part composite at 168 triangles. Closing the
    bores fully inside the shell cost more than breaking them out did, and
    this is the cheapest non-silhouette detail left to pay for it.
    """
    return revolve(name, [
        (0.0000, y_face - length),
        (stub_r, y_face - length + 0.0030),
        (stub_r, y_face - length * 0.62),
        (body_r, y_face - length * 0.46),
        (body_r, y_face + 0.0012),
        (0.0000, y_face + 0.0012),
    ], segments=segments, axis="y", centre=centre, smooth=False)


def bore_cutter(name, centre, y_face, y_back, radius=BORE_R,
                chamfer=BORE_CHAMFER, segments=BORE_SEG):
    """A capped cylinder with a conical mouth, used as the difference solid.

    It overshoots both faces of whatever it drills so no face of the cutter is
    ever coplanar with a face of the target - coplanar input is what makes an
    exact solver emit slivers.
    """
    front = y_face - 0.0050
    back = y_back + 0.0050
    return revolve(name, [
        (0.0000, front),
        (radius + chamfer, front),
        (radius + chamfer, y_face),
        (radius, y_face + chamfer),
        (radius, back),
        (0.0000, back),
    ], segments=segments, axis="y", centre=centre, smooth=False)


def drill(target, cutters):
    """Difference, then put the mesh back into the shape the pipeline expects.

    A boolean leaves n-gons and can leave doubles on the seam. emit() gave
    every other part triangles under FIXED / EAR_CLIP, and the exporter is set
    to trust that, so the result is normalised the same way here rather than
    left for Unity to triangulate differently.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for cutter in cutters:
        modifier = target.modifiers.new(name="bore", type="BOOLEAN")
        modifier.operation = "DIFFERENCE"
        modifier.object = cutter
        modifier.solver = "EXACT"
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    for cutter in cutters:
        mesh = cutter.data
        bpy.data.objects.remove(cutter, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    work = bmesh.new()
    work.from_mesh(target.data)
    # An exact boolean leaves near-coincident vertices and collinear runs along
    # the seam. Merging and dissolving removes most of them; what survives is
    # needle triangles with real edge lengths and no area, which dissolve does
    # not touch, so those are collapsed on their shortest edge until none is
    # left. Collapsing rather than deleting keeps the shell closed, which the
    # manifold gate needs.
    bmesh.ops.remove_doubles(work, verts=work.verts[:], dist=1.5e-5)
    bmesh.ops.dissolve_degenerate(work, dist=1.5e-5, edges=work.edges[:])
    bmesh.ops.recalc_face_normals(work, faces=work.faces[:])
    work.normal_update()
    bmesh.ops.triangulate(work, faces=work.faces[:],
                          quad_method="FIXED", ngon_method="EAR_CLIP")
    for _ in range(6):
        slivers = [f for f in work.faces if f.calc_area() <= 1e-12]
        if not slivers:
            break
        edges = {min(f.edges, key=lambda e: e.calc_length()) for f in slivers}
        bmesh.ops.collapse(work, edges=list(edges), uvs=False)
        bmesh.ops.triangulate(work, faces=work.faces[:],
                              quad_method="FIXED", ngon_method="EAR_CLIP")
    bmesh.ops.recalc_face_normals(work, faces=work.faces[:])
    work.normal_update()
    work.to_mesh(target.data)
    work.free()
    return target


def drill_parts(parts, centres, y_face, y_back, names=DRILLED):
    """Drill every named part on every screw axis, and report what it cost."""
    report = {}
    for obj in parts:
        stem = obj.name.split(".")[0]
        if stem not in names:
            continue
        before = p1.mesh_health(obj)
        cutters = [bore_cutter(f"cut_{stem}_{label}", centre, y_face, y_back)
                   for label, centre in centres.items()]
        drill(obj, cutters)
        after = p1.mesh_health(obj)
        report[stem] = {
            "triangles_before": before["triangles"],
            "triangles_after": after["triangles"],
            "cost": after["triangles"] - before["triangles"],
            "bores": len(centres),
            "non_manifold_edges": after["non_manifold_edges"],
            "zero_area_faces": after["zero_area_faces"],
            "clean": (after["non_manifold_edges"] == 0
                      and after["zero_area_faces"] == 0),
        }
    return report


# ---------------------------------------------------------------------------
# the arm, split into rod and grip with a relief groove between them
# ---------------------------------------------------------------------------

# The tactile pattern was running the whole length of the arm, rod included,
# because the arm was one loft and the atlas routed it by part name. Splitting
# it is the structural fix as well as the material one: a lever of this size
# is a rod with a grip fitted to it, not one turned billet, and the joint is
# where a ferrule sits in a relief groove.
ARM_ROD_END = 0.560
ARM_FERRULE = (0.545, 0.618)
ARM_GRIP_START = 0.602
ARM_FERRULE_SCALE = 0.72          # how far the groove is undercut
ROD_ROWS = 8
FERRULE_ROWS = 3
GRIP_ROWS = 11


def _along(a, b, s):
    return tuple(a[i] + (b[i] - a[i]) * s for i in range(3))


def _rows(count):
    return [0.5 - 0.5 * math.cos(math.pi * i / count)
            for i in range(count + 1)]


def _window(fn, lo, hi, scale=1.0, close_tip=False):
    """Re-parameterise a station profile onto a sub-span of the arm."""
    span = hi - lo

    def value(t):
        s = lo + span * min(max(t, 0.0), 1.0)
        radius = fn(s) * scale
        if close_tip and t > 0.86:
            u = (t - 0.86) / 0.14
            radius *= math.sqrt(max(0.0, 1.0 - u * u))
        return radius
    return value


def build_arm(arm_a, arm_b, arm_u, arm_v, swell, segments):
    """Rod, ferrule and grip as three pieces that share one silhouette.

    The ferrule overlaps its neighbours slightly so the surface never opens a
    gap, and sits at 72 per cent of the local radius, which is what makes the
    joint read as a groove rather than as a seam.
    """
    rod = p3.capsule_loft(
        "handle_rod", arm_a, _along(arm_a, arm_b, ARM_ROD_END),
        _window(arm_u, 0.0, ARM_ROD_END),
        _window(arm_v, 0.0, ARM_ROD_END),
        offset_v=lambda t: swell(t * ARM_ROD_END),
        segments=segments, stops=_rows(ROD_ROWS))
    ferrule = p3.capsule_loft(
        "handle_ferrule",
        _along(arm_a, arm_b, ARM_FERRULE[0]),
        _along(arm_a, arm_b, ARM_FERRULE[1]),
        _window(arm_u, ARM_FERRULE[0], ARM_FERRULE[1], ARM_FERRULE_SCALE),
        _window(arm_v, ARM_FERRULE[0], ARM_FERRULE[1], ARM_FERRULE_SCALE),
        offset_v=lambda t: swell(ARM_FERRULE[0]
                                 + (ARM_FERRULE[1] - ARM_FERRULE[0]) * t),
        segments=segments, stops=_rows(FERRULE_ROWS))
    grip = p3.capsule_loft(
        "handle_grip", _along(arm_a, arm_b, ARM_GRIP_START), arm_b,
        _window(arm_u, ARM_GRIP_START, 1.0),
        _window(arm_v, ARM_GRIP_START, 1.0),
        offset_v=lambda t: swell(ARM_GRIP_START
                                 + (1.0 - ARM_GRIP_START) * t),
        segments=segments, stops=_rows(GRIP_ROWS))
    return rod, ferrule, grip, {
        "rod_span_s": [0.0, ARM_ROD_END],
        "ferrule_span_s": list(ARM_FERRULE),
        "grip_span_s": [ARM_GRIP_START, 1.0],
        "ferrule_radius_scale": ARM_FERRULE_SCALE,
        "groove_depth_pct": round((1.0 - ARM_FERRULE_SCALE) * 100.0, 1),
        "overlap_s": [round(ARM_ROD_END - ARM_FERRULE[0], 4),
                      round(ARM_FERRULE[1] - ARM_GRIP_START, 4)],
        "rows": {"rod": ROD_ROWS, "ferrule": FERRULE_ROWS, "grip": GRIP_ROWS},
        "note": ("the tactile pattern is routed to handle_grip only; "
                 "handle_rod and handle_ferrule stay plain"),
    }


# The gasket is the only cover still narrowed in X, because it is the one
# nobody can see. Everything with a visible taper is back at Batch A size and
# drilled instead.
GASKET_X_THROTTLE = 0.1860
GASKET_X_SLIDER = 0.1100


def build_throttle(material):
    """Batch A's throttle at Batch A's dimensions, at lower density."""
    width, depth_env, height = ba.envelope_blender("Throttle")
    plate_y = -0.0180
    shell_y = -0.0440
    shell = (width - 0.020, height - 0.014)
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

    arm_a = THROTTLE_ARM_A
    arm_b = THROTTLE_ARM_B
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

    rod, ferrule, grip, arm_report = build_arm(arm_a, arm_b, arm_u, arm_v,
                                               swell, GRIP_SEG)
    handle = p1.join(hub, cheeks + [pin] + bosses + [rod, ferrule, grip])
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
        ], segments=8, axis="x",
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
    parts.append(light_access_cap("access", (-0.0680, 0.1180),
                                  shell_y + EMBED, 0.0125))

    # A removable panel with four screws, built from primitives instead of the
    # p1 composite: same feature, 172 triangles instead of 812.
    cover_centre = (0.0640, 0.1180)
    parts.append(p1.chamfer(p1.frustum_box(
        "cover", shell_y + EMBED, shell_y - 0.0030, (0.0440, 0.0620),
        (0.0408, 0.0578), centre=cover_centre), 0.0012))
    for sx, sz in ((-1.0, -1.0), (1.0, 1.0)):
        parts.append(p1.chamfer(p1.frustum_cyl(
            f"cover_screw_{int(sx)}_{int(sz)}",
            shell_y - 0.0026, shell_y - 0.0044, 0.0036, 0.0029,
            segments=6,
            centre=(cover_centre[0] + sx * 0.0150,
                    cover_centre[1] + sz * 0.0230)), 0.0006))

    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0030, 0.0120))
    parts.append(light_gland("gland", (0.0, -0.1480), shell_y - 0.0018))
    parts.append(p1.nameplate("plate_label", (0.0, -0.1000), (0.0560, 0.0180),
                              shell_y + EMBED, 0.0018))
    for sign in (-1.0, 1.0):
        parts.append(light_mount(f"mount_{int(sign)}",
                                 (sign * 0.0700, -0.1420), plate_y - 0.0004,
                                 0.0078, 0.0034))
    # A plugged port, as a seat and a domed cap rather than the composite.
    parts.append(light_plug("blank", (-0.0700, 0.1420), plate_y - 0.0006,
                            0.0074))

    audit = p3.coplanar_overlap_audit(parts)
    # pillow caps and end stops are placed with object .location, so the
    # snapshot needs an evaluated depsgraph or it reads them at the
    # origin and every pose looks like a collision. Until this build the
    # update came for free from a p1 composite's internal join.
    bpy.context.view_layer.update()
    ba.STATIC_PARTS = ba.snapshot_statics(parts)
    audit["screws"] = {k: [round(v[0], 5), round(v[1], 5)]
                       for k, v in screws.items()}
    # measured from the front face to just clear of the screw dome:
    # the head is what the driver is reaching, not something in its way
    audit["tool_access_planes"] = [shell_y, plate_y - 0.0036]
    audit["arm"] = arm_report
    audit["drilling"] = drill_parts(parts, screws, shell_y, plate_y)
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
    shell = (width - 0.022, height - 0.030)
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
                SLIDER_GRIP_A, SLIDER_GRIP_B,
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
        (shell[0] + 0.013, shell[1] + 0.013),
        (shell[0] + 0.004, shell[1] + 0.004)), 0.0015))

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
        ], segments=10, axis="z",
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
        mark = p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0018,
            (0.0150 if major else 0.0100, 0.0032 if major else 0.0024),
            (0.0132 if major else 0.0086, 0.0028 if major else 0.0021),
            centre=(slot[0] / 2.0 + 0.0155, z))
        parts.append(p1.chamfer(mark, 0.0005) if major else mark)

    screws = {}
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            label = f"{int(sx)}_{int(sz)}"
            centre = (sx * SCREW_X_SLIDER, sz * SCREW_Z_SLIDER)
            screws[label] = centre
            parts.append(flush_screw(f"screw_{label}", centre,
                                     plate_y - 0.0006))
    parts.append(light_access_cap("access", (-0.0330, 0.1360),
                                  shell_y + EMBED, 0.0115))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0028, 0.0110))
    parts.append(light_gland("gland", (0.0, -0.1560), shell_y - 0.0016,
                             body_r=0.0090, length=0.0210))
    parts.append(p1.nameplate("plate_label", (-0.0320, -0.1320),
                              (0.0420, 0.0160), shell_y + EMBED, 0.0016))
    for sign in (-1.0, 1.0):
        parts.append(light_mount(f"mount_{int(sign)}",
                                 (sign * 0.0400, -0.1600), plate_y - 0.0004,
                                 0.0074, 0.0032))
    parts.append(light_plug("blank", (0.0430, 0.1360), plate_y - 0.0006,
                            0.0070))

    audit = p3.coplanar_overlap_audit(parts)
    # pillow caps and end stops are placed with object .location, so the
    # snapshot needs an evaluated depsgraph or it reads them at the
    # origin and every pose looks like a collision. Until this build the
    # update came for free from a p1 composite's internal join.
    bpy.context.view_layer.update()
    ba.STATIC_PARTS = ba.snapshot_statics(parts)
    audit["screws"] = {k: [round(v[0], 5), round(v[1], 5)]
                       for k, v in screws.items()}
    # measured from the front face to just clear of the screw dome:
    # the head is what the driver is reaching, not something in its way
    audit["tool_access_planes"] = [shell_y, plate_y - 0.0036]
    audit["drilling"] = drill_parts(parts, screws, shell_y, plate_y)
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


BUILDERS_R4 = {
    "Throttle": build_throttle,
    "PowerSlider": build_power_slider,
}


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
        material = p1.proto.make_material(f"MAT_{THEME}_R4_Neutral", NEUTRAL)
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
        "phase": "Theme4-P6-BatchA-R4-geometry",
        "note": ("Throttle and PowerSlider only. The four screw bores are "
                 "cut with a boolean through the original tapered skirt and "
                 "shell, and the Throttle arm is split into rod, ferrule and "
                 "grip so the tactile pattern stops at the joint. batch_a, "
                 "batch_a_r1, batch_a_r2, batch_b and P1-P5 are untouched."),
        "changed_assets": ["Throttle", "PowerSlider"],
        "budgets": {"triangle_budget_validator_total": VALIDATOR_TOTAL,
                    "triangle_target_total": TARGET_TOTAL},
        "tool": {"nominal_tool_diameter_mm": round(TOOL_NOMINAL_R * 2000.0, 2),
                 "bore_clear_diameter_mm": round(BORE_CLEAR_R * 2000.0, 2),
                 "bore_cutter_diameter_mm": round(BORE_R * 2000.0, 2),
                 "bore_mouth_chamfer_mm": round(BORE_CHAMFER * 1000.0, 2),
                 "bore_segments": BORE_SEG,
                 "screw_head_diameter_mm": round(r2.SCREW_HEAD_R * 2000.0, 2),
                 "method": "boolean DIFFERENCE, EXACT solver, per part",
                 "drilled_parts": list(DRILLED)},
        "assets": {},
    }

    import opus5_brushup_kinetic_review as review
    for asset, builder in BUILDERS_R4.items():
        breakdown = part_breakdown(builder)
        p1.clear_scene()
        review.configure_scene()
        material = p1.proto.make_material(f"MAT_{THEME}_R4_Neutral", NEUTRAL)
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
        access = tool_path_audit(body, screws, face, base,
                                 tool_r=TOOL_NOMINAL_R)
        row["tool_access"] = access
        row["gates"]["tool_paths_open"] = access["all_open"]
        row["drilling"] = audit.get("drilling")
        row["arm"] = audit.get("arm")
        row["gates"]["boolean_clean"] = all(
            v["clean"] for v in (audit.get("drilling") or {}).values())
        row["triangle_delta"] = {
            "baseline": BASELINE[asset],
            "r2": dict(row["triangles_per_object"],
                       all=row["triangles_total"]),
            "reduction": BASELINE[asset]["all"] - row["triangles_total"],
        }

        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P6A_R4.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        focus, radius, scale = p1.rig_for([body] + movers)
        images = {}
        for label, view in p1.VIEWS.items():
            path = grey_dir / f"Grey_{asset}_{THEME}_P6A_R4_{label}.png"
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
        print(f"[BatchA-R4] {asset}: tris {row['triangles_total']} "
              f"(was {BASELINE[asset]['all']}), holes open "
              f"{access['all_open']} min bore "
              f"{access['min_clear_diameter_mm']} mm, clearance "
              f"{row['clearance']['clean']} min "
              f"{row['clearance']['min_clearance_mm']}, gates "
              f"{row['all_gates_passed']}")

    payload["status"] = (
        "p6_batch_a_r4_geometry_ready"
        if all(row["all_gates_passed"] for row in payload["assets"].values())
        else "p6_batch_a_r4_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchA-R4] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
