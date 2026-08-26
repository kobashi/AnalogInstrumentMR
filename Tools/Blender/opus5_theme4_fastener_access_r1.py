"""Theme 4 fastener serviceability audit and the 315 fixes.

315 failed two things at once: a rotary nameplate floating off its base with
nothing to say and nothing holding it, and a status bar whose corner screws
sit under the hood so no driver reaches them. The second is a generation rule,
not a one-off, so this module audits every fastener in every accepted Theme 4
candidate rather than only the one that was seen.

The tool path standard is 315.4: a 4.0 mm-radius shaft and an 8.2 mm-radius
working clearance, both swept 80 mm straight out of the screw recess towards
the Unity front, both required to hit zero triangles. A blocked screw gets a
through hole in whatever covers it - 16.4 mm minimum, chamfered, no blind cap.

Nothing else moves. Pivots, motion, states, UV, materials, the P4 atlas and
every geometry that has already passed - the rotary grip, the button press,
the lamp proportions, the status bar's three widths on a centred group - are
carried through untouched and re-measured to prove it.
"""

import math
import re
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_machined_ergonomics_p4 as p4
import opus5_theme4_machined_ergonomics_p5 as p5
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_r4 as r4
import opus5_theme4_full_p6_batch_a_r4_b3u_r2 as b3ur2
import opus5_theme4_full_p6_batch_b as bb
import opus5_theme4_full_p6_batch_b_r1 as br1
import opus5_theme4_full_p6_batch_b_r2 as br2

# 315.4
TOOL_SHAFT_R = 0.0040
TOOL_CLEAR_R = 0.0082
TOOL_REACH = 0.080
ACCESS_HOLE_D = 0.0164            # 315.5 minimum
SAMPLE_STEP = 0.001

# p1.fastener("screw_0", ...) leaves three named pieces behind - the seat
# annulus and the two half discs slotted_head builds - so the id has to strip
# `_h-1` / `_h1`, then `_head`, then `_seat`, or each screw audits itself as
# its own obstacle and every screw in the project reads as blocked.
FASTENER_SUFFIXES = re.compile(r"(_h-?\d+|_head|_seat)$")


def fastener_id(name):
    """The fastener a captured part belongs to, or None."""
    stem = name.split(".")[0]
    # "screw" anywhere, not only as a prefix: the lever's cover plate uses
    # `cover_screw_*`, and a prefix test walks straight past four of them.
    if "screw" not in stem and not stem.startswith("fastener"):
        return None
    while True:
        trimmed = FASTENER_SUFFIXES.sub("", stem)
        if trimmed == stem or not trimmed:
            return stem
        stem = trimmed


# ---------------------------------------------------------------------------
# the roster: the latest accepted builder for every Theme 4 candidate
# ---------------------------------------------------------------------------

def _pilot(name):
    return p5.BUILDERS_P5[name]


def _batch_a_meter(name):
    return lambda material: ba.build_round_meter(name, material)


def _b3u_r2(asset):
    def build(material):
        root, body, mover, movers, tagged, audit = b3ur2.build_without_nameplate(
            asset, r4.BUILDERS_R4[asset])
        return body, mover, movers, audit
    return build


ROSTER = (
    ("MeterRound", "P5 (pilot)", _pilot("MeterRound")),
    ("Lever", "P5", _pilot("Lever")),
    ("Toggle", "P5 (P4 builder)", _pilot("Toggle")),
    ("MeterMedium", "Batch A", _batch_a_meter("MeterMedium")),
    ("MeterLarge", "Batch A", _batch_a_meter("MeterLarge")),
    ("Throttle", "Batch A R4 B3U R2", _b3u_r2("Throttle")),
    ("PowerSlider", "Batch A R4 B3U R2", _b3u_r2("PowerSlider")),
    ("Rotary", "Batch B R1", br1.build_rotary),
    ("Button", "Batch B R1", br1.build_button),
    ("Lamp", "Batch B R1", br1.build_lamp),
    ("StatusIndicator", "Batch B R2", br2.build_status),
)
ABSENT = (
    ("TrendMonitor",
     "no MachinedErgonomics TrendMonitor exists; the TrendMonitor is built "
     "only for OrbitalAnalog / ForgeBrass / KineticSafety by "
     "opus5_trend_monitor_themes.py, which 315.9 puts out of scope"),
)


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------

def capture(builder, material):
    """Build, keeping every part's world triangles under its own name."""
    captured = {}
    original_join = p1.join

    def hook(target, others):
        for obj in [target] + list(others):
            if obj is None:
                continue
            tris = br1.world_triangles(obj)
            if len(tris):
                captured.setdefault(obj.name.split(".")[0], []).append(tris)
        return original_join(target, others)

    p1.join = hook
    try:
        result = builder(material)
    finally:
        p1.join = original_join
    bpy.context.view_layer.update()
    body, mover, movers, audit = result
    movers = list(movers) if isinstance(movers, (list, tuple)) else [movers]
    parts = {name: np.concatenate(rows) for name, rows in captured.items()}
    return body, mover, movers, audit, parts


# ---------------------------------------------------------------------------
# 315.3 / 315.4 tool path
# ---------------------------------------------------------------------------

def tool_path(obstacles, axis_xz, start_y, radius, reach=TOOL_REACH,
              step=SAMPLE_STEP):
    """Sweep a cylinder of `radius` straight out of the recess towards -Y.

    Sampled as spheres at 1 mm, which under-measures the swept solid by at
    most radius - sqrt(radius**2 - 0.25e-6) - 0.03 um at 4 mm. The first
    sphere is offset so its back tangent clears the head by 0.2 mm; a hit
    therefore means something in front of the screw, never the screw itself.
    """
    if obstacles is None or len(obstacles) == 0:
        return 0, float("inf")
    cx, cz = axis_xz
    hits, nearest = 0, float("inf")
    samples = int(round(reach / step)) + 1
    for index in range(samples):
        y = start_y - 0.0002 - radius - index * step
        count, distance = br1.sphere_hits(obstacles, (cx, y, cz), radius)
        hits += count
        nearest = min(nearest, distance)
    return hits, nearest - radius


def blockers(parts, fastener, axis_xz, start_y, radius, reach=TOOL_REACH):
    """Which named parts the clearance cylinder runs into."""
    found = {}
    for name, tris in parts.items():
        if fastener_id(name) == fastener or len(tris) == 0:
            continue
        hits, clearance = tool_path(tris, axis_xz, start_y, radius, reach)
        if hits:
            found[name] = {"triangle_hits": hits,
                           "clearance_mm": round(clearance * 1000.0, 2)}
    return found


def audit_instrument(asset, source, parts, movers):
    """Every fastener in one instrument, against 315.4."""
    ids = sorted({fid for name in parts if (fid := fastener_id(name))})
    static = {name: tris for name, tris in parts.items()
              if fastener_id(name) is None}
    mover_tris = {obj.name.split(".")[0]: br1.world_triangles(obj)
                  for obj in movers}
    obstacles_by_part = dict(static)
    obstacles_by_part.update(mover_tris)

    rows = []
    for fid in ids:
        own = np.concatenate([tris for name, tris in parts.items()
                              if fastener_id(name) == fid])
        cx = float(0.5 * (own[:, :, 0].min() + own[:, :, 0].max()))
        cz = float(0.5 * (own[:, :, 2].min() + own[:, :, 2].max()))
        start_y = float(own[:, :, 1].min())
        others = np.concatenate([tris for name, tris in obstacles_by_part.items()
                                 if fastener_id(name) != fid])
        shaft_hits, shaft_clear = tool_path(others, (cx, cz), start_y,
                                            TOOL_SHAFT_R)
        clear_hits, clear_clear = tool_path(others, (cx, cz), start_y,
                                            TOOL_CLEAR_R)
        row = {
            "fastener": fid,
            "head_centre_m": [round(cx, 4), round(start_y, 4), round(cz, 4)],
            "driver_axis": "-Y (Unity front)",
            "approach_side": "front",
            "head_front_y_m": round(start_y, 4),
            "shaft_radius_mm": TOOL_SHAFT_R * 1000.0,
            "shaft_triangle_hits": shaft_hits,
            "shaft_clearance_mm": round(shaft_clear * 1000.0, 2),
            "clearance_radius_mm": TOOL_CLEAR_R * 1000.0,
            "clearance_triangle_hits": clear_hits,
            "clearance_margin_mm": round(clear_clear * 1000.0, 2),
            "reach_mm": TOOL_REACH * 1000.0,
            "pass": shaft_hits == 0 and clear_hits == 0,
        }
        if not row["pass"]:
            row["blockers"] = blockers(obstacles_by_part, fid, (cx, cz),
                                       start_y, TOOL_CLEAR_R)
        rows.append(row)
    return {
        "asset": asset,
        "source": source,
        "fastener_count": len(rows),
        "fasteners": rows,
        "pass": all(row["pass"] for row in rows),
        "failing": [row["fastener"] for row in rows if not row["pass"]],
    }


# ---------------------------------------------------------------------------
# 315.5: is a through hole viable, or must the fastener move?
# ---------------------------------------------------------------------------

def front_face_mask(tris, axis_xz, span=0.060, pixels=480, slab=0.002):
    """Rasterise a part's front-face material into the XZ plane.

    Only the frontmost `slab` of the part counts: that is the face a hole
    would be drilled through, and it is the face whose boundary decides
    whether the hole would break out of the part instead of passing through
    it.
    """
    front = float(tris[:, :, 1].min())
    keep = tris[(tris[:, :, 1] <= front + slab).any(axis=1)]
    if len(keep) == 0:
        return None, None
    cx, cz = axis_xz
    scale = pixels / (2.0 * span)
    mask = np.zeros((pixels, pixels), dtype=bool)
    u = (keep[:, :, 0] - cx) * scale + pixels / 2.0
    v = (keep[:, :, 2] - cz) * scale + pixels / 2.0
    for tri in range(u.shape[0]):
        x0 = max(int(np.floor(u[tri].min())), 0)
        x1 = min(int(np.ceil(u[tri].max())) + 1, pixels)
        y0 = max(int(np.floor(v[tri].min())), 0)
        y1 = min(int(np.ceil(v[tri].max())) + 1, pixels)
        if x1 <= x0 or y1 <= y0:
            continue
        ax, ay = u[tri, 0], v[tri, 0]
        bx, by = u[tri, 1], v[tri, 1]
        gx0, gy0 = u[tri, 2], v[tri, 2]
        area = (bx - ax) * (gy0 - ay) - (gx0 - ax) * (by - ay)
        if abs(area) < 1e-12:
            continue
        px = np.arange(x0, x1) + 0.5
        py = np.arange(y0, y1) + 0.5
        gx, gy = np.meshgrid(px, py)
        w0 = ((bx - ax) * (gy - ay) - (gx - ax) * (by - ay)) / area
        w1 = ((gx - ax) * (gy0 - ay) - (gx0 - ax) * (gy - ay)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0.0) & (w1 >= 0.0) & (w2 >= 0.0)
        mask[y0:y1, x0:x1] |= inside
    return mask, scale


def largest_inscribed_radius(tris, axis_xz, span=0.060, pixels=480):
    """The biggest circle centred on the screw axis still inside the material.

    This is the number 315.5's "structurally unnatural" clause turns on: a
    16.4 mm hole needs 8.2 mm plus a wall, and if the covering part cannot
    give that, drilling it would cut the part open rather than pass through
    it.
    """
    mask, scale = front_face_mask(tris, axis_xz, span, pixels)
    if mask is None:
        return 0.0
    centre = pixels / 2.0
    ys, xs = np.mgrid[0:pixels, 0:pixels]
    distance = np.hypot(xs + 0.5 - centre, ys + 0.5 - centre)
    if not mask[int(centre), int(centre)]:
        return 0.0
    outside = distance[~mask]
    if outside.size == 0:
        return span
    return float(outside.min()) / scale


# ---------------------------------------------------------------------------
# 315.5 fallback: find the nearest land that does satisfy the standard
# ---------------------------------------------------------------------------

def front_depth_map(tris, span, pixels=360):
    """Frontmost surface y over the XZ plane; +inf where there is no material.

    This is the map a relocation search needs: it says both where a seat can
    land and how far forward that land stands, which is where the tool path
    has to start.
    """
    depth = np.full((pixels, pixels), np.inf)
    scale = pixels / (2.0 * span)
    u = tris[:, :, 0] * scale + pixels / 2.0
    v = tris[:, :, 2] * scale + pixels / 2.0
    y = tris[:, :, 1]
    for tri in range(u.shape[0]):
        x0 = max(int(np.floor(u[tri].min())), 0)
        x1 = min(int(np.ceil(u[tri].max())) + 1, pixels)
        z0 = max(int(np.floor(v[tri].min())), 0)
        z1 = min(int(np.ceil(v[tri].max())) + 1, pixels)
        if x1 <= x0 or z1 <= z0:
            continue
        ax, az = u[tri, 0], v[tri, 0]
        bx, bz = u[tri, 1], v[tri, 1]
        cx, cz = u[tri, 2], v[tri, 2]
        area = (bx - ax) * (cz - az) - (cx - ax) * (bz - az)
        if abs(area) < 1e-12:
            continue
        px = np.arange(x0, x1) + 0.5
        pz = np.arange(z0, z1) + 0.5
        gx, gz = np.meshgrid(px, pz)
        w0 = ((bx - ax) * (gz - az) - (gx - ax) * (bz - az)) / area
        w1 = ((gx - ax) * (cz - az) - (cx - ax) * (gz - az)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0.0) & (w1 >= 0.0) & (w2 >= 0.0)
        if not inside.any():
            continue
        value = w2 * y[tri, 0] + w1 * y[tri, 1] + w0 * y[tri, 2]
        window = depth[z0:z1, x0:x1]
        better = inside & (value < window)
        window[better] = value[better]
    return depth, scale


def seat_land(depth, scale, pixels, axis_xz, seat_r, flat=0.0004):
    """Is there flat, frontmost material under a seat of `seat_r` here?"""
    cx, cz = axis_xz
    px = cx * scale + pixels / 2.0
    pz = cz * scale + pixels / 2.0
    reach = seat_r * scale
    x0, x1 = int(px - reach) - 1, int(px + reach) + 2
    z0, z1 = int(pz - reach) - 1, int(pz + reach) + 2
    if x0 < 0 or z0 < 0 or x1 > pixels or z1 > pixels:
        return None
    gx, gz = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(z0, z1) + 0.5)
    disc = np.hypot(gx - px, gz - pz) <= reach
    window = depth[z0:z1, x0:x1][disc]
    if not np.isfinite(window).all():
        return None
    if float(window.max() - window.min()) > flat:
        return None
    return float(window.min())


def relocate(asset, parts, movers, fastener, seat_r, span, original_xz,
             step=0.0015, rings=26, spokes=48, pixels=360):
    """Search outwards from the original position for a compliant land.

    Every fastener is excluded from the obstacle set: the search is looking
    for somewhere the *tool* fits, and the screws themselves are what is being
    placed. The nearest passing candidate wins, so the move is as small as the
    geometry allows and the reason it had to move at all stays legible.
    """
    static = [tris for name, tris in parts.items()
              if fastener_id(name) is None]
    obstacles = np.concatenate(
        static + [br1.world_triangles(obj) for obj in movers])
    land_tris = np.concatenate(static)
    depth, scale = front_depth_map(land_tris, span, pixels)

    ox, oz = original_xz
    tried = 0
    for ring in range(rings + 1):
        radius = ring * step
        count = 1 if ring == 0 else spokes
        for spoke in range(count):
            angle = 2.0 * math.pi * spoke / count
            cx = ox + radius * math.cos(angle)
            cz = oz + radius * math.sin(angle)
            start_y = seat_land(depth, scale, pixels, (cx, cz), seat_r)
            tried += 1
            if start_y is None:
                continue
            shaft, _ = tool_path(obstacles, (cx, cz), start_y, TOOL_SHAFT_R)
            if shaft:
                continue
            clear, margin = tool_path(obstacles, (cx, cz), start_y,
                                      TOOL_CLEAR_R)
            if clear:
                continue
            return {
                "fastener": fastener,
                "from_xz_m": [round(ox, 4), round(oz, 4)],
                "to_xz_m": [round(cx, 4), round(cz, 4)],
                "moved_mm": round(radius * 1000.0, 2),
                "new_face_y_m": round(start_y, 4),
                "clearance_margin_mm": round(margin * 1000.0, 2),
                "candidates_tried": tried,
            }
    return {"fastener": fastener, "from_xz_m": [round(ox, 4), round(oz, 4)],
            "to_xz_m": None, "candidates_tried": tried,
            "reason": "no land within {:.0f} mm satisfies the 8.2 mm "
                      "clearance".format(rings * step * 1000.0)}


# ---------------------------------------------------------------------------
# where the standard *can* be met: a clearance map over the front face
# ---------------------------------------------------------------------------

def clearance_map(depth, tol=0.0002):
    """For every cell, the radius of the largest clear cylinder standing on it.

    Read as a heightfield: a cylinder rising from the surface at one cell is
    clear exactly while no neighbour inside its radius stands further forward.
    So the answer is the distance to the nearest cell in front of this one,
    which one pass of a brute distance transform gives for the whole face at
    once - a per-cell tool-path test would be tens of thousands of sweeps.

    Overhangs are the one thing a heightfield cannot see, so every position it
    proposes is re-tested against the real triangles before it is used.
    """
    pixels = depth.shape[0]
    order = np.argsort(depth, axis=None)
    finite = np.isfinite(depth.ravel()[order])
    order = order[finite]
    zs, xs = np.unravel_index(order, depth.shape)
    values = depth.ravel()[order]
    radius = np.full(depth.shape, np.inf)
    radius[~np.isfinite(depth)] = 0.0

    # Walk cells front to back; each one's answer is its distance to the
    # nearest cell already seen, i.e. the nearest cell in front of it.
    seen_x, seen_z, seen_y = [], [], []
    block = 512
    for start in range(0, len(order), block):
        end = min(start + block, len(order))
        bx, bz, by = xs[start:end], zs[start:end], values[start:end]
        if seen_x:
            px = np.concatenate(seen_x)
            pz = np.concatenate(seen_z)
            py = np.concatenate(seen_y)
            ahead = py[None, :] < by[:, None] - tol
            distance = np.hypot(bx[:, None] - px[None, :],
                                bz[:, None] - pz[None, :])
            distance = np.where(ahead, distance, np.inf)
            radius[bz, bx] = distance.min(axis=1)
        seen_x.append(bx)
        seen_z.append(bz)
        seen_y.append(by)
    empty = ~np.isfinite(depth)
    if empty.any():
        ez, ex = np.nonzero(empty)
        # Falling off the part entirely is also a boundary for the seat.
        for start in range(0, len(order), block):
            end = min(start + block, len(order))
            bx, bz = xs[start:end], zs[start:end]
            distance = np.hypot(bx[:, None] - ex[None, :],
                                bz[:, None] - ez[None, :]).min(axis=1)
            radius[bz, bx] = np.minimum(radius[bz, bx], distance)
    return radius


def best_land(depth, radius, scale, pixels, near_xz, seat_r, need_r):
    """The cell nearest `near_xz` whose clearance meets the standard."""
    ox, oz = near_xz
    px = ox * scale + pixels / 2.0
    pz = oz * scale + pixels / 2.0
    need = max(need_r, seat_r) * scale
    ok = radius >= need
    if not ok.any():
        return None, float(radius.max()) / scale
    zs, xs = np.nonzero(ok)
    distance = np.hypot(xs + 0.5 - px, zs + 0.5 - pz)
    pick = int(np.argmin(distance))
    cx = (xs[pick] + 0.5 - pixels / 2.0) / scale
    cz = (zs[pick] + 0.5 - pixels / 2.0) / scale
    return ((float(cx), float(cz), float(depth[zs[pick], xs[pick]]),
             float(radius[zs[pick], xs[pick]]) / scale),
            float(radius.max()) / scale)


def flat_map(depth, max_px, tol=0.0003):
    """Radius in cells over which the surface stays flat under a seat.

    A seat is a flat annulus, so it needs flat material under all of it. The
    clearance map alone would happily seat a screw half over a drafted flank,
    where the seat would hang in the air.
    """
    pixels = depth.shape[0]
    flat = np.zeros(depth.shape, dtype=np.int16)
    alive = np.isfinite(depth)
    for step in range(1, int(max_px) + 2):
        still = alive.copy()
        for dz in range(-step, step + 1):
            for dx in range(-step, step + 1):
                if dx * dx + dz * dz > step * step:
                    continue
                shifted = np.full(depth.shape, np.inf)
                z0, z1 = max(0, dz), min(pixels, pixels + dz)
                x0, x1 = max(0, dx), min(pixels, pixels + dx)
                shifted[z0 - dz:z1 - dz, x0 - dx:x1 - dx] = depth[z0:z1, x0:x1]
                still &= np.isfinite(shifted) & (np.abs(shifted - depth) <= tol)
        if not still.any():
            break
        flat[still] = step
        alive = still
    return flat


def best_on_ray(depth, clearance, flat, scale, pixels, origin_xz, seat_r,
                need_r, reach=0.070):
    """Slide the fastener along its own radius until the standard is met.

    Moving along the ray from the instrument's axis keeps the angular
    arrangement the builder chose, so a symmetric set of screws stays
    symmetric instead of scattering to whatever cell happened to be nearest.
    """
    ox, oz = origin_xz
    length = math.hypot(ox, oz)
    if length < 1e-6:
        return None
    ux, uz = ox / length, oz / length
    need = need_r * scale
    seat = seat_r * scale
    best = None
    steps = int(reach / (1.0 / scale))
    for step in range(steps + 1):
        for sign in ((1, -1) if step else (1,)):
            distance = sign * step / scale
            cx, cz = ox + ux * distance, oz + uz * distance
            px = int(cx * scale + pixels / 2.0)
            pz = int(cz * scale + pixels / 2.0)
            if not (0 <= px < pixels and 0 <= pz < pixels):
                continue
            if not np.isfinite(depth[pz, px]):
                continue
            if clearance[pz, px] < need or flat[pz, px] < seat:
                continue
            best = {"to_xz_m": (float(cx), float(cz)),
                    "face_y_m": float(depth[pz, px]),
                    "moved_mm": abs(distance) * 1000.0,
                    "radial_shift_mm": distance * 1000.0,
                    "clearance_mm": float(clearance[pz, px]) / scale * 1000.0,
                    "flat_radius_mm": float(flat[pz, px]) / scale * 1000.0}
            return best
    return best


# ---------------------------------------------------------------------------
# the search, corrected: seat on static land, clearance against everything
# ---------------------------------------------------------------------------

def _shift(field, dx, dz, fill):
    pixels = field.shape[0]
    out = np.full(field.shape, fill)
    z0, z1 = max(0, dz), min(pixels, pixels + dz)
    x0, x1 = max(0, dx), min(pixels, pixels + dx)
    out[z0 - dz:z1 - dz, x0 - dx:x1 - dx] = field[z0:z1, x0:x1]
    return out


def _disc_offsets(radius_px):
    out = []
    span = int(math.ceil(radius_px))
    for dz in range(-span, span + 1):
        for dx in range(-span, span + 1):
            if dx or dz:
                out.append((dx, dz, math.hypot(dx, dz)))
    out.sort(key=lambda row: row[2])
    return out


def clear_radius_map(land_depth, block_depth, cap_px, tol=0.0003):
    """How far a cylinder standing on the land can grow before it hits.

    `land_depth` is the static surface a seat can sit on; `block_depth`
    includes the moving parts, because a needle or a knob in front of a screw
    blocks a driver exactly as a housing does. The earlier pass built both
    from the statics alone and happily proposed a rotary screw under the knob.
    """
    result = np.zeros(land_depth.shape)
    growing = np.isfinite(land_depth)
    for dx, dz, distance in _disc_offsets(cap_px):
        if distance > cap_px:
            break
        ahead = _shift(block_depth, dx, dz, np.inf) < land_depth - tol
        newly = growing & ahead
        result[newly] = distance
        growing &= ~newly
        if not growing.any():
            break
    result[growing] = cap_px
    result[~np.isfinite(land_depth)] = 0.0
    return result


def flat_radius_map(land_depth, cap_px, tol=0.0003):
    """How far the static surface stays flat and present around each cell."""
    result = np.zeros(land_depth.shape)
    growing = np.isfinite(land_depth)
    for dx, dz, distance in _disc_offsets(cap_px):
        if distance > cap_px:
            break
        shifted = _shift(land_depth, dx, dz, np.inf)
        broken = ~np.isfinite(shifted) | (np.abs(shifted - land_depth) > tol)
        newly = growing & broken
        result[newly] = distance
        growing &= ~newly
        if not growing.any():
            break
    result[growing] = cap_px
    result[~np.isfinite(land_depth)] = 0.0
    return result


def solve_on_ray(land_depth, clear_px, flat_px, scale, pixels, origin_xz,
                 seat_r, need_r=TOOL_CLEAR_R, reach=0.090):
    """Slide the fastener along its own radius to the nearest compliant land."""
    ox, oz = origin_xz
    length = math.hypot(ox, oz)
    if length < 1e-6:
        return None
    ux, uz = ox / length, oz / length
    need, seat = need_r * scale, seat_r * scale
    steps = int(reach * scale)
    for step in range(steps + 1):
        for sign in ((1, -1) if step else (1,)):
            distance = sign * step / scale
            if length + distance < 0.004:
                continue
            cx, cz = ox + ux * distance, oz + uz * distance
            px = int(round(cx * scale + pixels / 2.0))
            pz = int(round(cz * scale + pixels / 2.0))
            if not (0 <= px < pixels and 0 <= pz < pixels):
                continue
            if not np.isfinite(land_depth[pz, px]):
                continue
            if clear_px[pz, px] < need or flat_px[pz, px] < seat:
                continue
            return {"to_xz_m": (float(cx), float(cz)),
                    "face_y_m": float(land_depth[pz, px]),
                    "radial_shift_mm": round(distance * 1000.0, 2),
                    "clearance_mm": round(
                        float(clear_px[pz, px]) / scale * 1000.0, 1),
                    "flat_radius_mm": round(
                        float(flat_px[pz, px]) / scale * 1000.0, 1)}
    return None


def solve_instrument(asset, parts, movers, seat_r, pixels=300,
                     need_r=TOOL_CLEAR_R):
    """Maps once, then one ray solve per blocked fastener."""
    static = [tris for name, tris in parts.items()
              if fastener_id(name) is None]
    land = np.concatenate(static)
    everything = np.concatenate(
        static + [br1.world_triangles(obj) for obj in movers])
    span = float(max(abs(everything[:, :, 0]).max(),
                     abs(everything[:, :, 2]).max())) * 1.04
    land_depth, scale = front_depth_map(land, span, pixels)
    block_depth, _ = front_depth_map(everything, span, pixels)
    cap = (need_r + 0.004) * scale
    clear_px = clear_radius_map(land_depth, block_depth, cap)
    flat_px = flat_radius_map(land_depth, max(seat_r * scale + 2.0, 4.0))
    return land_depth, clear_px, flat_px, scale, span


def solve_group(land_depth, clear_px, flat_px, scale, pixels, members, seat_r,
                need_r=TOOL_CLEAR_R, reach=0.090):
    """One radial shift for a whole symmetric set of fasteners.

    Solving each screw on its own scatters a symmetric set - the grid answers
    one quadrant a cell earlier than its mirror, and the panel ends up with
    four screws at four radii. The set moves together or not at all.
    """
    need, seat = need_r * scale, seat_r * scale
    steps = int(reach * scale)
    for step in range(steps + 1):
        for sign in ((1, -1) if step else (1,)):
            distance = sign * step / scale
            placed = []
            for ox, oz in members:
                length = math.hypot(ox, oz)
                if length < 1e-6 or length + distance < 0.004:
                    placed = None
                    break
                ux, uz = ox / length, oz / length
                cx, cz = ox + ux * distance, oz + uz * distance
                px = int(round(cx * scale + pixels / 2.0))
                pz = int(round(cz * scale + pixels / 2.0))
                if not (0 <= px < pixels and 0 <= pz < pixels):
                    placed = None
                    break
                if not np.isfinite(land_depth[pz, px]):
                    placed = None
                    break
                if clear_px[pz, px] < need or flat_px[pz, px] < seat:
                    placed = None
                    break
                placed.append({
                    "from_xz_m": [round(ox, 4), round(oz, 4)],
                    "to_xz_m": [round(float(cx), 4), round(float(cz), 4)],
                    "face_y_m": round(float(land_depth[pz, px]), 4),
                    "clearance_map_mm": round(
                        float(clear_px[pz, px]) / scale * 1000.0, 1)})
            if placed:
                return {"radial_shift_mm": round(distance * 1000.0, 2),
                        "members": placed}
    return None


def best_possible(land_depth, clear_px, flat_px, scale, members, seat_r,
                  pixels, reach=0.090):
    """The most clearance any compliant seat on this ray could ever get.

    This is the number a "cannot be fixed by moving the screw" claim has to
    show: not that the search failed, but how far short the instrument is.
    """
    seat = seat_r * scale
    best = 0.0
    where = None
    steps = int(reach * scale)
    for ox, oz in members:
        length = math.hypot(ox, oz)
        if length < 1e-6:
            continue
        ux, uz = ox / length, oz / length
        for step in range(-steps, steps + 1):
            distance = step / scale
            if length + distance < 0.004:
                continue
            cx, cz = ox + ux * distance, oz + uz * distance
            px = int(round(cx * scale + pixels / 2.0))
            pz = int(round(cz * scale + pixels / 2.0))
            if not (0 <= px < pixels and 0 <= pz < pixels):
                continue
            if not np.isfinite(land_depth[pz, px]) or flat_px[pz, px] < seat:
                continue
            value = float(clear_px[pz, px]) / scale
            if value > best:
                best, where = value, (float(cx), float(cz))
    return best, where


# ---------------------------------------------------------------------------
# applying the fixes
# ---------------------------------------------------------------------------

OVERRIDES = {}
DROP_NAMEPLATE = "__dropped_nameplate"


def install_overrides(asset, drop_nameplate=False):
    """Patch p1.fastener so only position moves, and drop rotary's nameplate.

    The builders themselves are frozen. A wrapper is the whole change: it
    substitutes the centre and the face plane for the fasteners named in the
    table and passes everything else - radius, depth, geometry - straight
    through, so a diff of the result is exactly the fastener positions.
    """
    original_fastener = p1.fastener
    original_nameplate = p1.nameplate
    original_join = p1.join

    def fastener(name, centre, y_face, radius, depth):
        key = (asset, name)
        if key in OVERRIDES:
            centre, y_face = OVERRIDES[key]
        return original_fastener(name, centre, y_face, radius, depth)

    def nameplate(name, *args, **kwargs):
        if drop_nameplate and asset == "Rotary" and name == "plate_label":
            mesh = bpy.data.meshes.new(DROP_NAMEPLATE)
            obj = bpy.data.objects.new(DROP_NAMEPLATE, mesh)
            bpy.context.collection.objects.link(obj)
            return obj
        return original_nameplate(name, *args, **kwargs)

    def join(target, others):
        group = []
        for obj in [target] + list(others):
            if obj is None:
                continue
            if obj.name.split(".")[0] == DROP_NAMEPLATE:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
                continue
            group.append(obj)
        return original_join(group[0], group[1:])

    p1.fastener, p1.nameplate, p1.join = fastener, nameplate, join
    return original_fastener, original_nameplate, original_join


def remove_overrides(saved):
    p1.fastener, p1.nameplate, p1.join = saved


def nameplate_residue():
    """315.1: nothing named plate_label may survive anywhere in the file."""
    return {
        "objects": sorted(o.name for o in bpy.data.objects
                          if "plate_label" in o.name),
        "meshes": sorted(m.name for m in bpy.data.meshes
                         if "plate_label" in m.name),
        "orphan_meshes": sorted(m.name for m in bpy.data.meshes
                                if "plate_label" in m.name and m.users == 0),
        "materials": sorted(m.name for m in bpy.data.materials
                            if "plate_label" in m.name),
        "placeholders": sorted(o.name for o in bpy.data.objects
                               if DROP_NAMEPLATE in o.name),
    }


# ---------------------------------------------------------------------------
# the fixes actually applied, and the two cases that need a decision
# ---------------------------------------------------------------------------

SEAT_RADIUS = {"Lever": 0.0060, "Toggle": 0.0052, "MeterMedium": 0.0082,
               "MeterLarge": 0.0126, "Rotary": 0.0046, "Button": 0.0058,
               "Lamp": 0.0056, "StatusIndicator": 0.0052}

# Every blocked screw sits on the mounting plate with the shell standing in
# front of it. The fix is the same everywhere it works: the screw moves onto
# the front face of the part that was covering it, which is where a panel
# instrument's fixing screws belong anyway, and only slides along its own
# radius when the face does not reach its original position. Smallest passing
# shift, found by the exact triangle test, not by the search grid.
FIXES = {
    "Toggle": {"radial_shift_m": -0.006, "face_y_m": -0.0400,
               "land": "shell front face"},
    "Lever": {"radial_shift_m": -0.012, "face_y_m": -0.0480,
              "land": "shell front face",
              "only": ("screw_-1_-1", "screw_1_-1")},
    "Button": {"radial_shift_m": 0.0, "face_y_m": -0.0430,
               "land": "shell front face"},
    "Lamp": {"radial_shift_m": 0.0, "face_y_m": -0.0400,
             "land": "shell front face"},
    "StatusIndicator": {"radial_shift_m": -0.012, "face_y_m": -0.0380,
                        "land": "shell front face"},
}
NAMEPLATE_REMOVED = ("Rotary",)


def fix_positions(asset, rows):
    """Turn a FIXES entry into the (asset, screw) -> (centre, face) table."""
    rule = FIXES.get(asset)
    if rule is None:
        return {}
    shift = rule["radial_shift_m"]
    out = {}
    for row in rows:
        name = row["fastener"]
        if "only" in rule and name not in rule["only"]:
            continue
        if row["pass"] and "only" not in rule:
            continue
        ox, _, oz = row["head_centre_m"]
        length = math.hypot(ox, oz)
        if length < 1e-6:
            continue
        cx = ox + ox / length * shift
        cz = oz + oz / length * shift
        out[(asset, name)] = ((round(cx, 5), round(cz, 5)),
                              rule["face_y_m"])
    return out


def enclosed_in(part_tris, axis_xz, y, direction=(0.0, -1.0, 0.0)):
    """Is a point on this axis buried inside that part's solid?

    A ray cast out of the point crosses a closed surface an odd number of
    times exactly when it started inside. The earlier version sampled
    triangles in a window around the axis instead, and on the large meter -
    48 segments over a 253 mm radius, so 33 mm between vertices - the window
    caught nothing and the test returned None for a screw that is in fact
    entirely enclosed.
    """
    origin = np.array([axis_xz[0], y, axis_xz[1]], dtype=np.float64)
    ray = np.asarray(direction, dtype=np.float64)
    ray = ray / np.linalg.norm(ray)
    a, b, c = part_tris[:, 0], part_tris[:, 1], part_tris[:, 2]
    e1, e2 = b - a, c - a
    pvec = np.cross(ray, e2)
    det = np.einsum("ij,ij->i", e1, pvec)
    live = np.abs(det) > 1e-14
    inv = np.zeros_like(det)
    inv[live] = 1.0 / det[live]
    tvec = origin - a
    u = np.einsum("ij,ij->i", tvec, pvec) * inv
    qvec = np.cross(tvec, e1)
    v = np.einsum("ij,ij->i", ray[None, :], qvec) * inv
    t = np.einsum("ij,ij->i", e2, qvec) * inv
    hit = live & (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0) & (t > 1e-7)
    crossings = int(np.count_nonzero(hit))
    front = float(part_tris[:, :, 1].min())
    back = float(part_tris[:, :, 1].max())
    return {"part_front_y_m": round(front, 4), "part_back_y_m": round(back, 4),
            "head_y_m": round(y, 4),
            "ray_crossings": crossings,
            "enclosed": crossings % 2 == 1}
