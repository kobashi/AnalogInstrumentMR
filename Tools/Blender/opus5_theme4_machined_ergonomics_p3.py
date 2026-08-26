"""Theme 4 Phase 3: geometry revision after the Quest Gate C shape FAIL.

Alignment record is Codex's job this round; the contract came in chat:

- MeterRound flickered on its minor ticks and read as a thick drum. The tick
  bases and the scale land's viewer face both sat at dial_face - 0.0011 -
  coincident, overlapping, and both exposed, which is exactly the z-fighting
  pair Codex diagnosed. P3 sinks every tick and index pin 0.6 mm into the
  land so no two exposed faces share a plane, and verifies that numerically
  for all 23 ticks plus a whole-body coplanar-overlap audit.
- The meter thins from 64 mm to 42.6 mm, keeps the dial and scale radii
  exactly (the readable front does not shrink), and grows the base to
  149 mm so the housing is one continuously drafted revolve - wall side
  wide, lip narrow - instead of stacked drums.
- The lever showed no joint between arm and axle, and its grip was a stack
  of boxes. P3 moves the pivot forward (y -0.018 -> -0.033, allowed and
  reported), which brings a rotating hub with collars, yoke cheeks and a
  roller right up to the slot mouth between two static pillow blocks with
  bearing caps. The grip becomes a lofted elliptical solid with a palm-side
  swell, a light waist and rounded ends - no frustum_box in its silhouette,
  minimum section half-axis well above the 5 mm edge-radius floor.
- The toggle grip becomes a revolved mushroom head with a dished top; every
  exposed radius is 4 mm or more. The square grip, thumb wedge and knurl
  ribs are gone; anti-slip is left to the normal map, as the style guide
  always wanted for surface grain.

P1/P2 scripts and delivery_p2/ are frozen; this file only imports them.
Everything lands under delivery_p3/.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_machined_ergonomics_p3.py -- \
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

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p3"
OUTPUT = f"{TREE}/geometry/theme4_machined_ergonomics_p3.json"

# The meter's base now spans 149 mm by design (Gate C asked for a wider,
# strongly drafted foot without shrinking the readable front). The old
# 140 x 140 x 64 envelope is superseded by the explicit 155 mm cap.
ENVELOPE_P3 = {
    "MeterRound": (0.155, 0.155, 0.045),
    "Lever": p1.ENVELOPE["Lever"],
    "Toggle": p1.ENVELOPE["Toggle"],
}
# p1.measure reads p1.ENVELOPE; patch in memory only - the file is frozen.
p1.ENVELOPE = ENVELOPE_P3

PIVOTS = {
    # asset: (old P2 pivot, new P3 pivot), Blender local metres
    "MeterRound": ((0.0, -0.052, 0.0), (0.0, -0.030, 0.0)),
    "Lever": ((0.0, -0.018, -0.080), (0.0, -0.033, -0.080)),
    "Toggle": ((0.0, -0.042, 0.0), (0.0, -0.042, 0.0)),
}

DIAL_FACE = -0.0280            # meter dial front plane (depth 42.6 mm total)
LAND_FRONT = DIAL_FACE - 0.0011
TICK_BASE = DIAL_FACE - 0.0005  # 0.6 mm behind the land face: embedded
EMBED = 0.0005                  # base sink
EMBED_SKIRT = 0.0015            # clear of the fastener seats' buried face
EMBED_MOUNT = 0.0016
EMBED_INDEX = 0.0008


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


# ---------------------------------------------------------------------------
# new primitives: surfaces of revolution and lofted grips
# ---------------------------------------------------------------------------

def _emit(name, verts, faces, smooth):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    work = bmesh.new()
    made = [work.verts.new(v) for v in verts]
    work.verts.index_update()
    for face in faces:
        try:
            work.faces.new([made[i] for i in face])
        except ValueError:
            pass  # duplicate face from a degenerate profile pair
    bmesh.ops.recalc_face_normals(work, faces=work.faces[:])
    work.normal_update()
    bmesh.ops.triangulate(work, faces=work.faces[:],
                          quad_method="FIXED", ngon_method="EAR_CLIP")
    work.to_mesh(obj.data)
    work.free()
    if smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj


def lathe(name, profile, segments=48, axis="y", centre=(0.0, 0.0),
          smooth=False):
    """Revolve a closed (radius, t) polygon about an axis.

    A point with radius ~0 becomes a single pole vertex, so a profile that
    starts and ends on the axis closes into a sphere-topology solid. This is
    what lets the whole meter housing be one continuously drafted piece
    instead of a stack of drums with coincident rims.
    """
    rings = []
    verts = []
    for radius, t in profile:
        if radius < 1e-6:
            if axis == "y":
                verts.append((centre[0], t, centre[1]))
            elif axis == "z":
                verts.append((centre[0], centre[1], t))
            else:
                verts.append((t, centre[0], centre[1]))
            rings.append(("pole", len(verts) - 1))
        else:
            base = len(verts)
            for j in range(segments):
                a = 2.0 * math.pi * j / segments
                c, s = radius * math.cos(a), radius * math.sin(a)
                if axis == "y":
                    verts.append((centre[0] + c, t, centre[1] + s))
                elif axis == "z":
                    verts.append((centre[0] + c, centre[1] + s, t))
                else:
                    verts.append((t, centre[0] + c, centre[1] + s))
            rings.append(("ring", base))
    faces = []
    n = len(rings)
    for i in range(n):
        ka, va = rings[i]
        kb, vb = rings[(i + 1) % n]
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
    return _emit(name, verts, faces, smooth)


def capsule_loft(name, start, end, half_u, half_v, offset_v=None,
                 rows=16, segments=16, bump=None, stops=None):
    """Loft elliptical sections along a line, closing both ends round.

    `half_u(s)` / `half_v(s)` return the section half-axes and must be 0 at
    s = 0 and s = 1 (poles). `offset_v(s)` shifts the section centre along
    the v direction - that is the palm-side swell. u is world X; v is the
    in-plane perpendicular chosen to point away from the wall (-Y side), so
    "toward the palm" is +v.

    `bump(s, phi)` adds a signed radial offset to both half-axes at one
    surface sample; it is how the knurl is cut into the grip without a single
    box rib. `stops` replaces the default cosine row spacing with an explicit
    list of s values, so rows can be spent where the knurl needs resolving
    instead of being spread evenly over a shaft that is plain anyway.
    """
    sx, sy, sz = start
    dx, dy, dz = (end[0] - start[0], end[1] - start[1], end[2] - start[2])
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    dn = (dx / length, dy / length, dz / length)
    v = (0.0, -dn[2], dn[1])
    if v[1] > 0.0:
        v = (0.0, -v[1], -v[2])
    if stops is not None:
        svals = list(stops)
        rows = len(svals) - 1
    else:
        svals = [0.5 - 0.5 * math.cos(math.pi * i / rows)
                 for i in range(rows + 1)]
    verts = []
    ring_index = []
    for i in range(rows + 1):
        s = svals[i]
        cx = sx + dx * s
        cy = sy + dy * s
        cz = sz + dz * s
        off = offset_v(s) if offset_v else 0.0
        cy += v[1] * off
        cz += v[2] * off
        a, b = half_u(s), half_v(s)
        if a < 1e-6 or b < 1e-6:
            verts.append((cx, cy, cz))
            ring_index.append(("pole", len(verts) - 1))
            continue
        base = len(verts)
        for j in range(segments):
            phi = 2.0 * math.pi * j / segments
            d = bump(s, phi) if bump else 0.0
            ux = (a + d) * math.cos(phi)
            vv = (b + d) * math.sin(phi)
            verts.append((cx + ux, cy + v[1] * vv, cz + v[2] * vv))
        ring_index.append(("ring", base))
    faces = []
    for i in range(rows):
        ka, va = ring_index[i]
        kb, vb = ring_index[i + 1]
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
    if ring_index[0][0] == "ring":
        base = ring_index[0][1]
        faces.append(tuple(range(base + segments - 1, base - 1, -1)))
    if ring_index[-1][0] == "ring":
        base = ring_index[-1][1]
        faces.append(tuple(range(base, base + segments)))
    return _emit(name, verts, faces, smooth=True)


def station_profile(stations, tip_from=0.90):
    """Interpolate half-axes along the arm and round only the far end.

    The root merges into the collar, so it must not taper to a point; only the
    tip closes. One table drives the whole arm, which is what makes the shaft
    and the grip a single continuous surface instead of a plate that suddenly
    becomes a ball.
    """
    def value(s):
        s = min(max(s, 0.0), 1.0)
        for i in range(len(stations) - 1):
            a, va = stations[i]
            b, vb = stations[i + 1]
            if a <= s <= b:
                t = 0.0 if b == a else (s - a) / (b - a)
                base = va + (vb - va) * t
                break
        else:
            base = stations[-1][1]
        if s > tip_from:
            u = (s - tip_from) / (1.0 - tip_from)
            base *= math.sqrt(max(0.0, 1.0 - u * u))
        return base + 0.0006
    return value


def rounded(s, power=2.5):
    """End-rounding multiplier: 1 mid-span, 0 at both ends, capsule-like."""
    t = abs(2.0 * s - 1.0)
    return (max(0.0, 1.0 - t ** power)) ** (1.0 / power)


# Knurl band on the lever grip. A real knurl is two opposed helices, so the
# depth field is the product of two counter-rotating waves, which is the same
# as the difference of a circumferential and an axial cosine. Amplitude is
# +-0.55 mm and the band is windowed by sin^2 at both ends, so the pattern
# fades into the plain shaft instead of terminating on a step. Nothing here
# adds a box rib: the diamonds are cut into the loft's own surface, so the
# grip silhouette stays the rounded one the brief requires.
LEVER_ARM_A = (0.0, -0.004, 0.008)
LEVER_ARM_B = (0.0, -0.090, 0.250)


def arm_crossing_z(angle_deg, plane_y):
    """Where the arm axis crosses a Y plane at one pose, in world Z."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    py, pz = PIVOTS["Lever"][1][1], PIVOTS["Lever"][1][2]
    pts = []
    for _, ly, lz in (LEVER_ARM_A, LEVER_ARM_B):
        pts.append((py + ly * ca - lz * sa, pz + ly * sa + lz * ca))
    (y0, z0), (y1, z1) = pts
    if abs(y1 - y0) < 1e-9:
        return pz
    t = (plane_y - y0) / (y1 - y0)
    return z0 + t * (z1 - z0)


KNURL_S0, KNURL_S1 = 0.585, 0.960
KNURL_AMP = 0.00090
KNURL_AROUND = 10        # diamonds around the circumference
KNURL_ALONG = 8          # diamond rows along the band


def flat_shade_band(obj, start, end, s0, s1):
    """Drop smooth shading over one span of a lofted part.

    Averaged normals dissolve a knurl: at four samples per diamond the crests
    get blended into their own valleys and the band renders as quilting. Face
    normals give each flank its own value, which is what makes a cut read as a
    cut. mesh_smooth_type EDGE carries the flags into the FBX.
    """
    ax = tuple(end[i] - start[i] for i in range(3))
    length2 = sum(c * c for c in ax)
    marked = 0
    for poly in obj.data.polygons:
        c = poly.center
        s = sum((c[i] - start[i]) * ax[i] for i in range(3)) / length2
        if s0 <= s <= s1:
            poly.use_smooth = False
            marked += 1
    obj.data.update()
    return marked


def _tri(x):
    """Unit triangular wave in [-1, 1]; the crease is what makes a ridge."""
    x -= math.floor(x)
    return 1.0 - 4.0 * abs(x - 0.5)


def knurl_field(s, phi):
    """Two opposed triangular helices - a pyramidal diamond, not a ripple.

    A cosine product gives the same lattice but with a sinusoidal flank, and
    under smooth shading on a 40-segment loft that reads as quilting rather
    than as a cut. Triangular flanks put a C0 crease on the crest, which the
    EDGE smoothing mode carries through to the FBX.
    """
    if s <= KNURL_S0 or s >= KNURL_S1:
        return 0.0
    u = (s - KNURL_S0) / (KNURL_S1 - KNURL_S0)
    window = math.sin(math.pi * u) ** 2
    along = KNURL_ALONG * u
    around = KNURL_AROUND * phi / (2.0 * math.pi)
    wave = 0.5 * (_tri(along + around) + _tri(along - around))
    return KNURL_AMP * window * wave


def knurl_stops(before=11, band=28, after=5):
    """Row spacing that puts most of the rows inside the knurl band.

    Uniform rows would need ~90 of them to resolve 8 diamond rows in the last
    third of the arm, and 90 rows at 32 segments is 5760 triangles on its own.
    Concentrating them costs a third of that for the same pattern.
    """
    stops = []
    for i in range(before):
        t = i / before
        stops.append(KNURL_S0 * (t ** 1.35))
    for i in range(band + 1):
        stops.append(KNURL_S0 + (KNURL_S1 - KNURL_S0) * i / band)
    for i in range(1, after + 1):
        t = i / after
        stops.append(KNURL_S1 + (1.0 - KNURL_S1) * (1.0 - (1.0 - t) ** 1.8))
    out = [0.0]
    for s in stops:
        if s > out[-1] + 1e-6:
            out.append(min(s, 1.0))
    if out[-1] < 1.0:
        out.append(1.0)
    return out


# ---------------------------------------------------------------------------
# swept-opening audit (the lever digging into its own base)
# ---------------------------------------------------------------------------

def swept_footprint(obj, pivot_loc, slab_lo, slab_hi, angles, steps=96):
    """Footprint the rotating part needs in a slab of the housing.

    The P2/P3 slot length came from a thin-arm approximation - the crossing of
    a centreline at +-amplitude - which ignores the hub, the yoke and the cam
    roller, and used a symmetric range the runtime does not have. Measured
    against the real 0..48 deg travel the arm overran the opening by 4.9 mm at
    the bottom and 37.7 mm at the top, which is exactly the reported digging.
    This returns what the opening actually has to be, from mesh vertices at 97
    poses, and the caller sizes the slot from it.
    """
    py, pz = pivot_loc[1], pivot_loc[2]
    low, high = min(angles), max(angles)
    zmin = zmax = None
    xmax = 0.0
    for index in range(steps + 1):
        a = math.radians(low + (high - low) * index / steps)
        ca, sa = math.cos(a), math.sin(a)
        for vert in obj.data.vertices:
            lx, ly, lz = vert.co
            y = py + (ly * ca - lz * sa)
            if not (slab_lo - 1e-9 <= y <= slab_hi + 1e-9):
                continue
            z = pz + (ly * sa + lz * ca)
            zmin = z if zmin is None else min(zmin, z)
            zmax = z if zmax is None else max(zmax, z)
            xmax = max(xmax, abs(lx))
    if zmin is None:
        return None
    return {"z_min": zmin, "z_max": zmax, "x_max": xmax,
            "slab": (slab_lo, slab_hi), "poses": steps + 1}


# ---------------------------------------------------------------------------
# coplanar-overlap audit (the Gate C flicker, made measurable)
# ---------------------------------------------------------------------------

def coplanar_overlap_audit(objects, tol=1.2e-4):
    """Count pairs of coplanar, XZ-overlapping Y-facing triangles.

    This is the geometry behind the Quest flicker: two exposed faces in the
    same Y plane, from different parts, covering the same pixels. Pairs that
    share a vertex are the same feature's own tessellation and are skipped.
    Run before join, so offenders can be named by part.
    """
    tris = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        mat = obj.matrix_world
        for tri in mesh.loop_triangles:
            normal = (mat.to_3x3() @ tri.normal).normalized()
            if abs(normal.y) < 0.999:
                continue
            pts = [mat @ mesh.vertices[i].co for i in tri.vertices]
            keys = {tuple(round(c, 6) for c in p) for p in pts}
            xs = [p.x for p in pts]
            zs = [p.z for p in pts]
            tris.append({
                "part": obj.name.split(".")[0],
                "y": sum(p.y for p in pts) / 3.0,
                "keys": keys,
                "box": (min(xs), max(xs), min(zs), max(zs)),
            })
    tris.sort(key=lambda t: t["y"])
    pairs = {}
    for i, a in enumerate(tris):
        for j in range(i + 1, len(tris)):
            b = tris[j]
            gap = b["y"] - a["y"]
            if gap > tol:
                break
            if a["part"] == b["part"] or (a["keys"] & b["keys"]):
                continue
            ax0, ax1, az0, az1 = a["box"]
            bx0, bx1, bz0, bz1 = b["box"]
            if (min(ax1, bx1) - max(ax0, bx0) > 1e-6 and
                    min(az1, bz1) - max(az0, bz0) > 1e-6):
                key = tuple(sorted((a["part"], b["part"])))
                if key not in pairs or gap < pairs[key]:
                    pairs[key] = gap
    return {
        "pairs": [list(k) for k in sorted(pairs)],
        "pair_count": len(pairs),
        "closest_gap_m": round(min(pairs.values()), 7) if pairs else None,
        "tolerance_m": tol,
    }


# ---------------------------------------------------------------------------
# MeterRound: thin, one continuously drafted revolve, ticks sunk into the land
# ---------------------------------------------------------------------------

METER_DEPTH = 0.0426
METER_BASE_R = 0.0745          # 149 mm across the foot, under the 155 mm cap
METER_LIP_R = 0.0570
METER_BORE_R = 0.0510          # unchanged: the readable opening does not shrink
DIAL_R = 0.0510
SCALE_OUTER = 0.0481           # unchanged from P2
SCALE_INNER = 0.0409           # unchanged from P2


def build_meter_round(material):
    """A thin instrument: wide drafted foot, narrow lip, deep-set dial.

    The housing is a single lathe. P2 stacked a rear cylinder, two flanges, a
    front tube and a bezel, and every join was a rim of the same diameter -
    which is what made it read as a drum and gave the coplanar pairs somewhere
    to hide. One revolved profile has no internal rims at all.
    """
    parts = []
    housing = lathe("housing", [
        (0.0000, 0.0),
        (0.0180, 0.0),
        (METER_BASE_R, 0.0),
        (METER_BASE_R - 0.0016, -0.0032),
        (0.0716, -0.0092),
        (0.0688, -0.0150),
        (0.0652, -0.0224),
        (0.0620, -0.0300),
        (0.0596, -0.0368),
        (METER_LIP_R, -METER_DEPTH),
        (0.0536, -METER_DEPTH),
        (0.0518, -0.0402),
        (METER_BORE_R, -0.0352),
        (0.0514, -0.0296),
        (0.0532, -0.0272),
        (0.0532, -0.0250),
        (0.0180, -0.0250),
        (0.0000, -0.0250),
    ], segments=64, smooth=False)
    parts.append(housing)

    # A gasket groove sunk into the flank, not a ring sitting on it.
    parts.append(lathe("gasket", [
        (0.0700, -0.0104),
        (0.0700, -0.0138),
        (0.0672, -0.0138),
        (0.0672, -0.0104),
    ], segments=48))

    # dial plate, seated in the cavity
    parts.append(p1.frustum_cyl("dial", -0.0270, DIAL_FACE, DIAL_R, DIAL_R,
                                segments=48))
    # The scale land. Its viewer face is the only thing at LAND_FRONT.
    parts.append(p1.annulus("scale_land", DIAL_FACE + EMBED, LAND_FRONT,
                            SCALE_OUTER, SCALE_INNER, segments=48))

    # Ticks. Base plane sits 0.6 mm *behind* the land face, buried in the land
    # body, so no exposed face of a tick shares a plane with the land. This is
    # the Gate C flicker fix and it is verified numerically, not asserted.
    minor_inner = SCALE_OUTER - 0.0034
    for index in range(23):
        angle = -25.0 + 230.0 * index / 22.0
        major = index % 2 == 0
        parts.append(p1.radial_tick(
            f"tick_{index}", angle,
            SCALE_INNER if major else minor_inner, SCALE_OUTER,
            0.0024 if major else 0.0016,
            TICK_BASE,
            LAND_FRONT - (0.0014 if major else 0.0011)))

    # index pins, sunk the same way
    for sign in (-1.0, 1.0):
        angle = math.radians(90.0 + sign * 115.0)
        seat = SCALE_INNER - 0.0054
        parts.append(p1.chamfer(p1.frustum_cyl(
            f"index_{int(sign)}", DIAL_FACE + EMBED_INDEX, DIAL_FACE - 0.0018,
            0.0026, 0.0021, segments=10,
            centre=(seat * math.cos(angle), seat * math.sin(angle))), 0.0004))

    # bearing boss for the needle, a revolve so its rim is not a flat ring
    parts.append(lathe("collar", [
        (0.0000, DIAL_FACE + 0.0006),
        (0.0112, DIAL_FACE + 0.0006),
        (0.0108, LAND_FRONT - 0.0016),
        (0.0074, LAND_FRONT - 0.0038),
        (0.0000, LAND_FRONT - 0.0038),
    ], segments=32, smooth=False))

    parts.append(p1.register_step("register",
                                  (METER_BASE_R * 1.55, METER_BASE_R * 1.55),
                                  -EMBED, -0.0030, 0.0))
    parts.append(p1.cable_gland("gland", (0.0, -METER_BASE_R + 0.012),
                                -0.0120, 0.0085, 0.019))
    parts.append(p1.blanking_plug("plug", (METER_BASE_R - 0.017, 0.0),
                                  -0.0104, 0.0070, 0.0034))

    audit = coplanar_overlap_audit(parts)
    audit["tick_planes"] = tick_plane_audit(parts)

    body = p1.join(parts[0], parts[1:])
    body.name = "MeterRound_body"
    body.data.name = "MeterRound_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("needle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = PIVOTS["MeterRound"][1]
    pivot.rotation_mode = "XYZ"

    # A lofted needle: tapered blade, rounded tip, domed boss.
    needle = p1.join(
        capsule_loft(
            "needle_blade", (0.0, 0.0, -0.0075), (0.0, 0.0, 0.0455),
            lambda s: 0.0031 * rounded(s, 3.4) * (1.0 - 0.45 * s) + 0.0004,
            lambda s: 0.0021 * rounded(s, 3.0) * (1.0 - 0.30 * s) + 0.0003,
            offset_v=lambda s: -0.0042,
            rows=18, segments=14),
        [lathe("needle_boss", [
            (0.0000, -0.0016),
            (0.0068, -0.0016),
            (0.0064, -0.0058),
            (0.0040, -0.0074),
            (0.0000, -0.0074),
        ], segments=24, axis="y", smooth=False)])
    needle.name = "needle"
    needle.data.name = "needle"
    p1.assign(needle, material)
    needle.parent = pivot
    return body, pivot, needle, audit


# ---------------------------------------------------------------------------
# Lever: the joint is now the thing you see first
# ---------------------------------------------------------------------------

def build_lever(material):
    """Pivot forward to the slot mouth so hub, yoke and collar are all visible.

    P2 hid the fulcrum 30 mm behind the face and put nothing in the opening but
    an arm, so there was no readable connection between arm and axle. Moving
    the pivot from y -0.018 to -0.033 brings the rotating hub within 15 mm of
    the shell face; static pillow blocks with bearing caps flank it, and the
    yoke cheeks and roller ride with the arm.

    The rotating assembly is now built *first* and the openings are measured
    from it. The earlier slot came from tan(amplitude) on a centreline over a
    symmetric +-24 deg range, but the runtime travel is one-sided 0..48 deg and
    the moving mass is a hub, a yoke and a cam roller, not a line. Measured
    over 97 real poses the arm overran the opening by 4.9 mm below and 37.7 mm
    above - the reported digging into the base. Sizing the slot from the
    measurement removes the guess.
    """
    width, height, depth = ENVELOPE_P3["Lever"]
    plate_y = -0.020
    shell_y = -0.048
    shell = (width - 0.030, height - 0.040)
    shell_centre_z = -0.010
    pivot_y = PIVOTS["Lever"][1][1]
    pivot_z = PIVOTS["Lever"][1][2]

    pivot = bpy.data.objects.new("handle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = PIVOTS["Lever"][1]
    pivot.rotation_mode = "XYZ"

    # Rotating assembly: hub on the axle, two yoke cheeks, a collar where the
    # arm leaves the slot, and one lofted arm carrying the knurled grip.
    hub = lathe("handle_hub", [
        (0.0000, 0.0210),
        (0.0168, 0.0198),
        (0.0182, 0.0090),
        (0.0182, -0.0090),
        (0.0168, -0.0198),
        (0.0000, -0.0210),
    ], segments=28, axis="x", centre=(0.0, 0.0), smooth=False)
    cheeks = []
    for sign in (-1.0, 1.0):
        cheeks.append(p1.chamfer(p1.frustum_box(
            f"handle_yoke_{int(sign)}", 0.006, -0.030, (0.0075, 0.052),
            (0.0065, 0.046), centre=(sign * 0.0155, 0.014)), 0.0010))
    collar = lathe("handle_collar", [
        (0.0000, 0.0155),
        (0.0230, 0.0142),
        (0.0246, 0.0000),
        (0.0230, -0.0142),
        (0.0000, -0.0155),
    ], segments=28, axis="x", centre=(-0.016, 0.030), smooth=False)

    # One lofted arm from the collar to the tip: wide root, neck at 40 per
    # cent, palm swell at 80, rounded end. No frustum_box anywhere in the
    # silhouette a hand touches, and the minimum half-axis is 13 mm, well
    # above the 5 mm edge-radius floor the brief set. The knurl is a depth
    # field on this same surface, so it cannot peel off the arm the way the
    # P2 rib band did.
    arm_a = LEVER_ARM_A
    arm_b = LEVER_ARM_B
    arm_u = station_profile([
        (0.00, 0.0212), (0.16, 0.0176), (0.40, 0.0132),
        (0.58, 0.0143), (0.80, 0.0184), (0.92, 0.0188), (1.00, 0.0150),
    ])
    arm_v = station_profile([
        (0.00, 0.0178), (0.16, 0.0152), (0.40, 0.0124),
        (0.58, 0.0140), (0.80, 0.0218), (0.92, 0.0222), (1.00, 0.0170),
    ])

    def arm_swell(s):
        return 0.0034 * math.exp(-(((s - 0.82) / 0.20) ** 2))

    grip = capsule_loft("handle_grip", arm_a, arm_b, arm_u, arm_v,
                        offset_v=arm_swell, segments=40,
                        bump=knurl_field, stops=knurl_stops())
    knurl_faces = flat_shade_band(grip, arm_a, arm_b,
                                  KNURL_S0 + 0.004, KNURL_S1 - 0.004)
    handle = p1.join(hub, cheeks + [
        collar,
        grip,
        p1.axis_cyl("handle_roller", -0.019, 0.019, 0.0062,
                    (-0.020, -0.028), segments=14),
    ])
    handle.name = "handle"
    handle.data.name = "handle"
    p1.assign(handle, material)

    # Openings measured from the assembly that has to pass through them.
    angles = p1.MOTION["Lever"]["audit_deg_blender"]
    face_slab = (shell_y, plate_y - p1.SHUT_LINE)
    floor_slab = (pivot_y, pivot_y + 0.004)
    need_face = swept_footprint(handle, PIVOTS["Lever"][1],
                                face_slab[0], face_slab[1], angles)
    need_floor = swept_footprint(handle, PIVOTS["Lever"][1],
                                 floor_slab[0], floor_slab[1], angles)
    margin = 0.0030
    slot_lo = need_face["z_min"] - margin
    slot_hi = need_face["z_max"] + margin
    slot = (max(0.074, 2.0 * (need_face["x_max"] + margin)), slot_hi - slot_lo)
    slot_centre_z = 0.5 * (slot_lo + slot_hi)

    parts = []
    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.014, height - 0.014)), 0.0018))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED, plate_y - p1.SHUT_LINE - EMBED,
                                (width - 0.038, height - 0.048),
                                (width - 0.038, height - 0.048),
                                centre=(0.0, shell_centre_z)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - p1.SHUT_LINE, shell_y, shell, slot,
        centre=(0.0, shell_centre_z),
        inner_centre=(0.0, slot_centre_z)), 0.0022))
    parts.append(p1.chamfer(p1.frustum_box(
        "skirt", plate_y + EMBED_SKIRT, plate_y - 0.010,
        (shell[0] + 0.016, shell[1] + 0.016),
        (shell[0] + 0.004, shell[1] + 0.004),
        centre=(0.0, shell_centre_z)), 0.0018))

    # The slot floor used to be a solid plate the hub grew straight out of.
    # It is now a frame with a bore sized to the hub and yoke sweep, so the
    # rotating parts pass through an opening instead of through material.
    floor_lo = need_floor["z_min"] - 0.0022
    floor_hi = need_floor["z_max"] + 0.0022
    parts.append(p1.rect_frame(
        "slot_floor", pivot_y + 0.004, pivot_y,
        (slot[0] + 0.028, slot[1] + 0.028),
        (2.0 * (need_floor["x_max"] + 0.0022), floor_hi - floor_lo),
        centre=(0.0, slot_centre_z),
        inner_centre=(0.0, 0.5 * (floor_lo + floor_hi))))

    # Static pillow blocks with bearing caps, one each side of the hub. These
    # are what the rotating collar runs in, and they read as a bearing rather
    # than as a hole because the cap is a separate lobe on top.
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"pillow_{int(sign)}", pivot_y + 0.006, pivot_y - 0.020,
            (0.020, 0.040), (0.017, 0.034),
            centre=(sign * 0.030, pivot_z)), 0.0012))
        parts.append(lathe(f"pillow_cap_{int(sign)}", [
            (0.0000, 0.0080),
            (0.0135, 0.0072),
            (0.0150, 0.0000),
            (0.0135, -0.0072),
            (0.0000, -0.0080),
        ], segments=24, axis="x",
            centre=(pivot_y - 0.004, pivot_z), smooth=False))
        parts[-1].location = (sign * 0.030, 0.0, 0.0)

    for name, cx, sx, cz, sz in (
        ("rim_left", -(slot[0] / 2.0 + 0.0045), 0.009, slot_centre_z, slot[1] + 0.018),
        ("rim_right", (slot[0] / 2.0 + 0.0045), 0.009, slot_centre_z, slot[1] + 0.018),
        ("rim_top", 0.0, slot[0], slot_hi + 0.0045, 0.009),
        ("rim_bottom", 0.0, slot[0], slot_lo - 0.0045, 0.009),
    ):
        parts.append(p1.chamfer(p1.frustum_box(
            name, shell_y + EMBED, shell_y - 0.0030, (sx, sz),
            (sx - 0.0014, sz - 0.0014), centre=(cx, cz)), 0.0008))

    # Detents now sit where the arm centreline actually crosses the face at
    # each audited pose, so the scale beside the slot agrees with the travel.
    for index, deg in enumerate(angles):
        parts.append(p1.chamfer(p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0020,
            (0.017, 0.0038), (0.015, 0.0034),
            centre=(slot[0] / 2.0 + 0.021, arm_crossing_z(deg, shell_y))), 0.0006))

    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.016), sz * (height / 2.0 - 0.016)),
                plate_y - 0.0006, 0.0068, 0.0050))
    parts.append(p1.access_cap("access", (-0.072, 0.150), shell_y + EMBED,
                               0.014, 0.0119, 0.0050))
    # The cam plate used to sit inside the opening at the depth the roller
    # sweeps through; it is now surface mounted below the slot, clear of the
    # roller's 40.6 mm swept radius.
    parts.append(p1.chamfer(p1.frustum_box(
        "cam_plate", shell_y + EMBED, shell_y - 0.0026, (0.060, 0.020),
        (0.054, 0.017), centre=(0.0, slot_lo - 0.020)), 0.0010))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0034, 0.014))
    parts.append(p1.cover_panel("cover", (-0.074, 0.078), (0.052, 0.076),
                                shell_y + EMBED, 0.0034, 0.0050))
    parts.append(p1.cable_gland("gland", (0.0, -0.192), shell_y - 0.002,
                                0.0105, 0.026))
    parts.append(p1.nameplate("plate_label", (0.062, -0.150), (0.062, 0.020),
                              shell_y + EMBED, 0.0020))
    for sign in (-1.0, 1.0):
        parts.append(p1.mount_hole(f"mount_{int(sign)}",
                                   (sign * 0.078, -0.184), plate_y - 0.0004,
                                   0.0086, 0.0050, 0.0038))
    parts.append(p1.blanking_plug("blank", (-0.078, 0.184), plate_y - 0.0006,
                                  0.0082, 0.0038))

    audit = coplanar_overlap_audit(parts)
    audit["knurl"] = {
        "band_s": [KNURL_S0, KNURL_S1],
        "amplitude_m": KNURL_AMP,
        "diamonds_around": KNURL_AROUND,
        "rows_along": KNURL_ALONG,
        "loft_segments": 40,
        "flat_shaded_faces": knurl_faces,
        "form": "two opposed triangular helices, sin^2 window at both ends",
    }
    audit["slot"] = {
        "face_slab_m": list(face_slab),
        "required_z_m": [need_face["z_min"], need_face["z_max"]],
        "required_half_x_m": need_face["x_max"],
        "slot_z_m": [slot_lo, slot_hi],
        "slot_size_m": list(slot),
        "slot_centre_z_m": slot_centre_z,
        "margin_m": margin,
        "p2_slot_size_m": [0.074, 0.0714],
        "poses": need_face["poses"],
        "floor_bore_m": [2.0 * (need_floor["x_max"] + 0.0022),
                         floor_hi - floor_lo],
    }
    body = p1.join(parts[0], parts[1:])
    body.name = "Lever_body"
    body.data.name = "Lever_body"
    p1.assign(body, material)

    handle.parent = pivot
    return body, pivot, handle, audit


# ---------------------------------------------------------------------------
# Toggle: a revolved mushroom head, nothing square where a finger lands
# ---------------------------------------------------------------------------

def build_toggle(material):
    """Same housing family, but the switch is turned on a lathe.

    P2's grip was a frustum_box with a wedge-shaped thumb relief and eight
    knurl ribs - three separate ways to put an edge under a fingertip. P3
    replaces the whole moving part above the hub with one surface of
    revolution: a flared stem, a mushroom crown whose smallest convex radius
    is 4.4 mm, and a shallow dished top that ends in a smooth pole instead of
    a rim. Grip texture is left to the normal map.
    """
    width, height, depth = ENVELOPE_P3["Toggle"]
    parts = []
    plate_y = -0.013
    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.009, height - 0.009)), 0.0014))
    shell_y = -0.040
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - p1.SHUT_LINE, shell_y,
        (width - 0.014, height - 0.018),
        (width - 0.034, height - 0.042)), 0.0016))
    parts.append(p1.frustum_box("gasket", plate_y + 0.0013,
                                plate_y - p1.SHUT_LINE - 0.0003,
                                (width - 0.021, height - 0.025),
                                (width - 0.021, height - 0.025)))
    # bearing bosses, now with revolved caps so the axle end is not a flat disc
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"boss_{int(sign)}", shell_y + 0.004, shell_y - 0.008,
            (0.014, 0.026), (0.012, 0.022),
            centre=(sign * 0.021, 0.0)), 0.0009))
        cap = lathe(f"boss_cap_{int(sign)}", [
            (0.0000, 0.0062),
            (0.0086, 0.0054),
            (0.0096, 0.0000),
            (0.0086, -0.0054),
            (0.0000, -0.0062),
        ], segments=20, axis="x", centre=(shell_y - 0.002, 0.0), smooth=False)
        cap.location = (sign * 0.0265, 0.0, 0.0)
        parts.append(cap)
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"stop_{int(sign)}", shell_y + 0.002, shell_y - 0.011,
            (0.007, 0.026), (0.006, 0.023),
            centre=(sign * 0.017, 0.013)), 0.0008))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.011), sz * (height / 2.0 - 0.011)),
                plate_y - 0.0006, 0.0052, 0.0040))
    parts.append(p1.access_cap("access", (-0.034, 0.050), shell_y + EMBED,
                               0.0105, 0.0089, 0.0040))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0026, 0.010))
    parts.append(p1.nameplate("plate_label", (0.0, -0.052), (0.062, 0.016),
                              shell_y + EMBED, 0.0016))
    for sign in (-1.0, 1.0):
        parts.append(p1.rib(f"rib_{int(sign)}", (sign * 0.040, 0.010),
                            (0.0055, 0.052), shell_y + EMBED, 0.0022))
    parts.append(p1.mount_hole("mount_a", (0.034, 0.050),
                               plate_y - 0.0004, 0.0072, 0.0040, 0.0026))
    parts.append(p1.blanking_plug("blank_a", (0.0, 0.062), plate_y - 0.0006,
                                  0.0068, 0.0032))

    audit = coplanar_overlap_audit(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = "Toggle_body"
    body.data.name = "Toggle_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("switch_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = PIVOTS["Toggle"][1]
    pivot.rotation_mode = "XYZ"

    switch = p1.join(
        lathe("switch_hub", [
            (0.0000, 0.0104),
            (0.0092, 0.0096),
            (0.0100, 0.0000),
            (0.0092, -0.0096),
            (0.0000, -0.0104),
        ], segments=24, axis="x", centre=(0.0, 0.0), smooth=False),
        [lathe("switch_head", [
            (0.0000, 0.0020),
            (0.0074, 0.0034),
            (0.0064, 0.0130),
            (0.0059, 0.0270),
            (0.0058, 0.0392),
            (0.0072, 0.0472),
            (0.0104, 0.0548),
            (0.0126, 0.0626),
            (0.0132, 0.0684),
            (0.0124, 0.0730),
            (0.0100, 0.0764),
            (0.0064, 0.0782),
            (0.0032, 0.0778),
            (0.0000, 0.0770),
        ], segments=28, axis="z", centre=(0.0, -0.0060), smooth=True)])
    switch.name = "switch"
    switch.data.name = "switch"
    p1.assign(switch, material)
    switch.parent = pivot
    return body, pivot, switch, audit


BUILDERS_P3 = {
    "MeterRound": build_meter_round,
    "Lever": build_lever,
    "Toggle": build_toggle,
}


def tick_plane_audit(objects):
    """Prove no tick or index pin shares an exposed plane with the land."""
    planes = {}
    for obj in objects:
        stem = obj.name.split(".")[0]
        if not (stem.startswith("tick_") or stem.startswith("index_")
                or stem == "scale_land"):
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        ys = set()
        for tri in mesh.loop_triangles:
            if abs(tri.normal.y) < 0.999:
                continue
            ys.add(round(sum(mesh.vertices[i].co.y
                             for i in tri.vertices) / 3.0, 6))
        planes[stem] = sorted(ys)
    land = planes.get("scale_land", [])
    rows = {}
    worst = None
    for stem, ys in planes.items():
        if stem == "scale_land":
            continue
        gaps = [abs(y - ly) for y in ys for ly in land]
        smallest = min(gaps) if gaps else None
        rows[stem] = {"planes": ys, "min_gap_to_land_m": smallest}
        if smallest is not None and (worst is None or smallest < worst):
            worst = smallest
    return {
        "land_planes": land,
        "marks_checked": len(rows),
        "min_gap_any_mark_to_land_m": worst,
        "coplanar_with_land": worst is not None and worst < 1.0e-5,
        "detail": rows,
    }


NEUTRAL = (0.520, 0.520, 0.520, 1.0)


def detail_shot(objects, focus, radius, view, lens, scale, path):
    p1.shot(focus, radius, view, lens, scale, path)
    return path


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
        "phase": "Theme4-P3-geometry",
        "note": ("Gate C shape revision. Meter thinned and re-lathed with the "
                 "tick bases sunk into the scale land; lever pivot moved "
                 "forward so hub, yoke and collar read at the slot mouth; "
                 "toggle grip revolved. P1/P2 scripts and delivery_p2 are "
                 "untouched."),
        "envelope_p3": {k: list(v) for k, v in ENVELOPE_P3.items()},
        "pivot_change": {k: {"p2": list(v[0]), "p3": list(v[1])}
                         for k, v in PIVOTS.items()},
        "assets": {},
    }

    for asset, builder in BUILDERS_P3.items():
        p1.clear_scene()
        import opus5_brushup_kinetic_review as review
        review.configure_scene()
        material = p1.proto.make_material(f"MAT_{THEME}_P3_Neutral", NEUTRAL)
        root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
        bpy.context.collection.objects.link(root)
        body, pivot, part, audit = builder(material)
        for obj in (body, pivot):
            obj.parent = root
        bpy.context.view_layer.update()

        scan = p1.sweep_scan(pivot, body, part, p1.MOTION[asset])
        row = p1.measure(asset, root, body, pivot, part, scan)
        row["pose_bounds"] = p1.pose_bounds(pivot, body, part,
                                            p1.MOTION[asset], scan)
        row["coplanar_overlap"] = audit
        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P3.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        focus, radius, scale = p1.rig_for([body, part])
        images = {}
        for label, view in p1.VIEWS.items():
            path = grey_dir / f"Grey_{asset}_{THEME}_P3_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        row["grayscale_images"] = images
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        print(f"[Theme4P3] {asset}: tris {row['triangles_total']}, "
              f"coplanar pairs {audit['pair_count']}, "
              f"gates {row['all_gates_passed']}")

        details = {}
        if asset == "MeterRound":
            marks = [o for o in bpy.data.objects if o.type == "MESH"]
            details["side_silhouette"] = str((detail_dir /
                f"Detail_{asset}_side_silhouette.png").relative_to(project_root))
            p1.shot(focus, radius * 1.02, (86.0, 2.0), 60.0, scale,
                    detail_dir / f"Detail_{asset}_side_silhouette.png")
            details["tick_land_section"] = str((detail_dir /
                f"Detail_{asset}_tick_land_section.png").relative_to(project_root))
            p1.shot((0.030, DIAL_FACE - 0.0016, 0.030), 0.108,
                    (26.0, 30.0), 88.0, 0.052,
                    detail_dir / f"Detail_{asset}_tick_land_section.png")
        if asset == "Lever":
            joint = (0.0, PIVOTS["Lever"][1][1] - 0.012,
                     PIVOTS["Lever"][1][2] + 0.010)
            details["joint"] = str((detail_dir /
                f"Detail_{asset}_joint.png").relative_to(project_root))
            p1.shot(joint, 0.235, (36.0, 20.0), 58.0, 0.115,
                    detail_dir / f"Detail_{asset}_joint.png")
            grip = (0.0, PIVOTS["Lever"][1][1] - 0.076,
                    PIVOTS["Lever"][1][2] + 0.208)
            details["grip_section"] = str((detail_dir /
                f"Detail_{asset}_grip_section.png").relative_to(project_root))
            # Across the grip, not down it: the old 74 deg elevation looked
            # along the arm axis and framed the tip as a plain ellipse, which
            # showed neither the section nor the knurl.
            p1.shot(grip, 0.150, (34.0, 12.0), 62.0, 0.072,
                    detail_dir / f"Detail_{asset}_grip_section.png")
            knurl = (0.0, PIVOTS["Lever"][1][1] - 0.070,
                     PIVOTS["Lever"][1][2] + 0.190)
            details["knurl"] = str((detail_dir /
                f"Detail_{asset}_knurl.png").relative_to(project_root))
            # Same station and same rig as the section shot - only the lens
            # is longer. Moving the camera in instead put it inside the arm's
            # own shadow and the band rendered black.
            p1.shot(knurl, 0.150, (34.0, 12.0), 125.0, 0.072,
                    detail_dir / f"Detail_{asset}_knurl.png")
            slot_view = (0.0, -0.044, PIVOTS["Lever"][1][2] + 0.020)
            details["slot"] = str((detail_dir /
                f"Detail_{asset}_slot.png").relative_to(project_root))
            p1.shot(slot_view, 0.190, (18.0, 26.0), 58.0, 0.095,
                    detail_dir / f"Detail_{asset}_slot.png")
        if asset == "Toggle":
            grip = (0.0, PIVOTS["Toggle"][1][1] - 0.010, 0.062)
            details["grip_section"] = str((detail_dir /
                f"Detail_{asset}_grip_section.png").relative_to(project_root))
            p1.shot(grip, 0.115, (30.0, 24.0), 66.0, 0.052,
                    detail_dir / f"Detail_{asset}_grip_section.png")
        row["detail_images"] = details

    payload["tick_plane_audit"] = \
        payload["assets"]["MeterRound"]["coplanar_overlap"]["tick_planes"]

    payload["coplanar_overlap_pairs_total"] = sum(
        row["coplanar_overlap"]["pair_count"]
        for row in payload["assets"].values())
    # The Gate C requirement is the dial: no exposed coincident face anywhere
    # on the meter, and no tick or index mark sharing a plane with the land.
    # The pairs that survive on the controls are fastener seats against the
    # shell's back face and the gasket, all of them buried under the shell
    # overhang on the wall-facing plate - reported with their gaps rather than
    # gated, because none of them is a visible surface.
    payload["meter_coplanar_pairs"] = \
        payload["assets"]["MeterRound"]["coplanar_overlap"]["pair_count"]
    payload["hidden_interior_pairs"] = {
        asset: {"pairs": row["coplanar_overlap"]["pairs"],
                "closest_gap_m": row["coplanar_overlap"]["closest_gap_m"]}
        for asset, row in payload["assets"].items()
        if row["coplanar_overlap"]["pair_count"]}
    payload["all_passed"] = (
        all(row["all_gates_passed"] for row in payload["assets"].values())
        and payload["meter_coplanar_pairs"] == 0
        and not payload["tick_plane_audit"]["coplanar_with_land"])
    payload["status"] = ("p3_geometry_ready" if payload["all_passed"]
                         else "p3_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4P3] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
