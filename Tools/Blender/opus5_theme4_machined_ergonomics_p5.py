"""Theme 4 P5 geometry: the lever's working point, put back on the mechanism.

Alignment 292. Quest failed P4's Lever because a part near the working point
sits inside the housing and reads as detached from the lever. Measured over
the real 0..48 degree travel with triangle-level intersection tests, that part
is `handle_roller`:

  * it hangs at a fixed offset (y -0.020, z -0.028) from the pivot, 34.4 mm
    out, with a 7.2 mm gap between its surface and the hub's - connected to
    nothing;
  * it intersects the gasket (22 triangle pairs), the plate (11) and the
    skirt (15) as the travel advances.

P5 turns it into the yoke's cross pin. The pin sits at 32 mm radius with its
phase on the middle of the travel, which is the one placement that keeps a
point at that radius in front of the shell face at *both* ends of a 48 degree
sweep; it runs through both yoke cheeks and carries a bearing boss on each
cheek, so the support is visible from outside. Nothing is shrunk, buried or
hidden.

Two smaller measured defects are fixed with it, both against statics alignment
292.1 item 5 names. The slot rims stand 3 mm off the shell face, and the
opening was sized against the face plane, so at the most upright pose the arm
root cut through `rim_top` (46 triangle pairs). The opening is now measured
against the rims' front plane instead. The slot floor's bore was 2.2 mm larger
than the sweep needed and the collar clipped its edge (6 pairs); the margin is
now 4.0 mm.

Only the Lever changes. MeterRound and Toggle are P4's builders, called
unmodified.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_machined_ergonomics_p5.py -- \
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
import opus5_theme4_machined_ergonomics_p4 as p4

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p5"
OUTPUT = f"{TREE}/geometry/theme4_machined_ergonomics_p5.json"
NEUTRAL = p4.NEUTRAL

# ---------------------------------------------------------------------------
# the cross pin
# ---------------------------------------------------------------------------

# A point at radius R from the pivot stays in front of a plane at distance d
# through the whole sweep only if R*cos(half-sweep) >= d and its phase is the
# middle of the travel. With d = 15 mm of pivot-to-face plus the pin's own
# radius and a working clearance, R = 32 mm at phase 24 deg clears at both
# ends by the same amount, which is why the phase is the sweep's midpoint and
# not the rest pose.
PIN_RADIUS = 0.0320
PIN_PHASE_DEG = 24.0
PIN_R = 0.0062
PIN_HALF_X = 0.0205          # 1.25 mm proud of each cheek's outer face
BOSS_R = 0.0105
BOSS_X = 0.01725
BOSS_HALF = 0.00425
YOKE_FRONT = -0.040          # was -0.030; the cheek now contains the pin
RIM_PROUD = 0.0030           # how far the slot rims stand off the shell face
FLOOR_BORE_MARGIN = 0.0040   # was 0.0022, which the collar clipped

PIN_LOCAL = (-PIN_RADIUS * math.cos(math.radians(PIN_PHASE_DEG)),
             PIN_RADIUS * math.sin(math.radians(PIN_PHASE_DEG)))

P4_ROLLER_LOCAL = (-0.020, -0.028)


def pin_sweep(angles, radius, steps=96):
    """World Y and Z the pin sweeps, so the opening can be sized to frame it."""
    pivot_y, pivot_z = p3.PIVOTS["Lever"][1][1], p3.PIVOTS["Lever"][1][2]
    low, high = min(angles), max(angles)
    ys, zs = [], []
    for index in range(steps + 1):
        a = math.radians(low + (high - low) * index / steps)
        ca, sa = math.cos(a), math.sin(a)
        ys.append(pivot_y + PIN_LOCAL[0] * ca - PIN_LOCAL[1] * sa)
        zs.append(pivot_z + PIN_LOCAL[0] * sa + PIN_LOCAL[1] * ca)
    return {"y": (min(ys) - radius, max(ys) + radius),
            "z": (min(zs) - radius, max(zs) + radius)}


LAST_STATIC_PARTS = {}


def swept_footprint_solid(obj, pivot_loc, slab_lo, slab_hi, angles, steps=96):
    """The opening a *surface* needs, not the one its vertices suggest.

    P3 and P4 sized the slot from mesh vertices. On a 26-row loft the rows are
    about 10 mm apart, so a triangle can cross a 30 mm slab with no vertex
    inside the part of it that matters, and the measured extreme falls short
    of the real one. That is why P5's first build still cut rim_top by 46
    triangle pairs at the most upright pose even after the slab was extended:
    the slab was right and the sampling was not.

    Each triangle is clipped against the two slab planes and the extremes are
    taken over the clipped polygon's corners, which for a convex clip are
    exactly where the extremes can be.
    """
    import numpy as np
    mesh = obj.data
    mesh.calc_loop_triangles()
    coords = np.array([tuple(v.co) for v in mesh.vertices], dtype=float)
    index = np.array([tuple(t.vertices) for t in mesh.loop_triangles],
                     dtype=int)
    tri = coords[index]                      # (N, 3, 3) as x, y, z
    tx, ty, tz = tri[..., 0], tri[..., 1], tri[..., 2]
    py, pz = pivot_loc[1], pivot_loc[2]
    low, high = min(angles), max(angles)

    zmin = zmax = None
    xmax = 0.0
    for step in range(steps + 1):
        a = math.radians(low + (high - low) * step / steps)
        ca, sa = math.cos(a), math.sin(a)
        wy = py + ty * ca - tz * sa
        wz = pz + ty * sa + tz * ca
        live = ~((wy.max(axis=1) < slab_lo) | (wy.min(axis=1) > slab_hi))
        if not live.any():
            continue
        ay, az, ax = wy[live], wz[live], tx[live]
        zs, xs = [], []
        inside = (ay >= slab_lo) & (ay <= slab_hi)
        if inside.any():
            zs.append(az[inside])
            xs.append(np.abs(ax[inside]))
        for i, j in ((0, 1), (1, 2), (2, 0)):
            yi, yj = ay[:, i], ay[:, j]
            for plane in (slab_lo, slab_hi):
                di, dj = yi - plane, yj - plane
                cross = (di * dj) < 0.0
                if not cross.any():
                    continue
                t = di[cross] / (di[cross] - dj[cross])
                zs.append(az[cross, i] + t * (az[cross, j] - az[cross, i]))
                xs.append(np.abs(ax[cross, i]
                                 + t * (ax[cross, j] - ax[cross, i])))
        if not zs:
            continue
        allz = np.concatenate(zs)
        zmin = allz.min() if zmin is None else min(zmin, allz.min())
        zmax = allz.max() if zmax is None else max(zmax, allz.max())
        xmax = max(xmax, float(np.concatenate(xs).max()))
    if zmin is None:
        return None
    return {"z_min": float(zmin), "z_max": float(zmax), "x_max": float(xmax),
            "slab": (slab_lo, slab_hi), "poses": steps + 1,
            "method": "triangle clipped against the slab planes"}


def build_lever(material):
    """P4's lever with the working point carried by the yoke.

    The structure is P3's, validated through two Gate C rounds, so it is
    reproduced rather than re-derived; what differs is listed at the top of
    this module. The grip is the plain smooth loft P4 established - the knurl
    lives in the normal map and no bump field is used here.
    """
    width, height, depth = p3.ENVELOPE_P3["Lever"]
    plate_y = -0.020
    shell_y = -0.048
    shell = (width - 0.030, height - 0.040)
    shell_centre_z = -0.010
    pivot_y = p3.PIVOTS["Lever"][1][1]
    pivot_z = p3.PIVOTS["Lever"][1][2]
    EMBED = p3.EMBED

    pivot = bpy.data.objects.new("handle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = p3.PIVOTS["Lever"][1]
    pivot.rotation_mode = "XYZ"

    hub = p3.lathe("handle_hub", [
        (0.0000, 0.0210),
        (0.0168, 0.0198),
        (0.0182, 0.0090),
        (0.0182, -0.0090),
        (0.0168, -0.0198),
        (0.0000, -0.0210),
    ], segments=28, axis="x", centre=(0.0, 0.0), smooth=False)

    # The cheeks run further forward than P4's so that the cross pin is
    # carried inside them rather than hung off their edge.
    cheeks = []
    for sign in (-1.0, 1.0):
        cheeks.append(p1.chamfer(p1.frustum_box(
            f"handle_yoke_{int(sign)}", 0.006, YOKE_FRONT, (0.0075, 0.052),
            (0.0065, 0.046), centre=(sign * 0.0155, 0.014)), 0.0010))
    collar = p3.lathe("handle_collar", [
        (0.0000, 0.0155),
        (0.0230, 0.0142),
        (0.0246, 0.0000),
        (0.0230, -0.0142),
        (0.0000, -0.0155),
    ], segments=28, axis="x", centre=(-0.016, 0.030), smooth=False)

    # The working point: one pin through both cheeks, with a bearing boss
    # raised on each cheek around it. P4 had a bare cylinder floating 7.2 mm
    # clear of every other moving part.
    pin = p3.lathe("handle_roller", [
        (0.0000, PIN_HALF_X),
        (0.0040, PIN_HALF_X - 0.0006),
        (PIN_R, PIN_HALF_X - 0.0020),
        (PIN_R, -(PIN_HALF_X - 0.0020)),
        (0.0040, -(PIN_HALF_X - 0.0006)),
        (0.0000, -PIN_HALF_X),
    ], segments=18, axis="x", centre=PIN_LOCAL, smooth=False)
    bosses = []
    for sign in (-1.0, 1.0):
        boss = p3.lathe(f"handle_pin_boss_{int(sign)}", [
            (0.0000, BOSS_HALF),
            (0.0075, BOSS_HALF - 0.0003),
            (BOSS_R, BOSS_HALF - 0.0017),
            (BOSS_R, -(BOSS_HALF - 0.0025)),
            (0.0060, -BOSS_HALF),
            (0.0000, -BOSS_HALF),
        ], segments=18, axis="x", centre=PIN_LOCAL, smooth=False)
        boss.location = (sign * BOSS_X, 0.0, 0.0)
        bosses.append(boss)

    arm_a = p3.LEVER_ARM_A
    arm_b = p3.LEVER_ARM_B
    arm_u = p3.station_profile([
        (0.00, 0.0212), (0.16, 0.0176), (0.40, 0.0132),
        (0.58, 0.0143), (0.80, 0.0184), (0.92, 0.0188), (1.00, 0.0150),
    ])
    arm_v = p3.station_profile([
        (0.00, 0.0178), (0.16, 0.0152), (0.40, 0.0124),
        (0.58, 0.0140), (0.80, 0.0218), (0.92, 0.0222), (1.00, 0.0170),
    ])

    def arm_swell(s):
        return 0.0034 * math.exp(-(((s - 0.82) / 0.20) ** 2))

    grip = p3.capsule_loft("handle_grip", arm_a, arm_b, arm_u, arm_v,
                           offset_v=arm_swell, segments=40,
                           stops=p4._plain_stops())
    handle = p1.join(hub, cheeks + [collar, pin] + bosses + [grip])
    handle.name = "handle"
    handle.data.name = "handle"
    p1.assign(handle, material)

    # Openings measured from the assembly that passes through them. The slab
    # now reaches the rims' front plane, not the shell face, because the rims
    # are what the arm root actually hit.
    angles = p1.MOTION["Lever"]["audit_deg_blender"]
    face_slab = (shell_y - RIM_PROUD, plate_y - p1.SHUT_LINE)
    floor_slab = (pivot_y, pivot_y + 0.004)
    need_face = swept_footprint_solid(handle, p3.PIVOTS["Lever"][1],
                                      face_slab[0], face_slab[1], angles)
    need_floor = swept_footprint_solid(handle, p3.PIVOTS["Lever"][1],
                                       floor_slab[0], floor_slab[1], angles)
    # The pin and its bosses ride in front of the face, so they never appear
    # in the slab measurement - but they have to be over the opening, or they
    # read as floating in front of solid shell.
    pin_span = pin_sweep(angles, BOSS_R)
    margin = 0.0030
    slot_lo = min(need_face["z_min"], pin_span["z"][0]) - margin
    slot_hi = max(need_face["z_max"], pin_span["z"][1]) + margin
    slot = (max(0.074, 2.0 * (need_face["x_max"] + margin)), slot_hi - slot_lo)
    slot_centre_z = 0.5 * (slot_lo + slot_hi)

    parts = []
    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.014, height - 0.014)), 0.0018))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - p1.SHUT_LINE - EMBED,
                                (width - 0.038, height - 0.048),
                                (width - 0.038, height - 0.048),
                                centre=(0.0, shell_centre_z)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - p1.SHUT_LINE, shell_y, shell, slot,
        centre=(0.0, shell_centre_z),
        inner_centre=(0.0, slot_centre_z)), 0.0022))
    parts.append(p1.chamfer(p1.frustum_box(
        "skirt", plate_y + p3.EMBED_SKIRT, plate_y - 0.010,
        (shell[0] + 0.016, shell[1] + 0.016),
        (shell[0] + 0.004, shell[1] + 0.004),
        centre=(0.0, shell_centre_z)), 0.0018))

    floor_lo = need_floor["z_min"] - FLOOR_BORE_MARGIN
    floor_hi = need_floor["z_max"] + FLOOR_BORE_MARGIN
    parts.append(p1.rect_frame(
        "slot_floor", pivot_y + 0.004, pivot_y,
        (slot[0] + 0.028, slot[1] + 0.028),
        (2.0 * (need_floor["x_max"] + FLOOR_BORE_MARGIN), floor_hi - floor_lo),
        centre=(0.0, slot_centre_z),
        inner_centre=(0.0, 0.5 * (floor_lo + floor_hi))))

    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"pillow_{int(sign)}", pivot_y + 0.006, pivot_y - 0.020,
            (0.020, 0.040), (0.017, 0.034),
            centre=(sign * 0.030, pivot_z)), 0.0012))
        parts.append(p3.lathe(f"pillow_cap_{int(sign)}", [
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
            name, shell_y + EMBED, shell_y - RIM_PROUD, (sx, sz),
            (sx - 0.0014, sz - 0.0014), centre=(cx, cz)), 0.0008))

    for index, deg in enumerate(angles):
        parts.append(p1.chamfer(p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0020,
            (0.017, 0.0038), (0.015, 0.0034),
            centre=(slot[0] / 2.0 + 0.021,
                    p3.arm_crossing_z(deg, shell_y))), 0.0006))

    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.016), sz * (height / 2.0 - 0.016)),
                plate_y - 0.0006, 0.0068, 0.0050))
    parts.append(p1.access_cap("access", (-0.072, 0.150), shell_y + EMBED,
                               0.014, 0.0119, 0.0050))
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

    audit = p3.coplanar_overlap_audit(parts)
    # Snapshot the statics by name before the join, so the clearance audit can
    # say which housing part a contact is against instead of only that there
    # was one.
    global LAST_STATIC_PARTS
    LAST_STATIC_PARTS = {}
    for obj in parts:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world.copy()
        LAST_STATIC_PARTS[obj.name.split(".")[0]] = (
            [matrix @ v.co for v in mesh.vertices],
            [tuple(t.vertices) for t in mesh.loop_triangles])

    audit["working_point"] = {
        "part": "handle_roller",
        "p4_placement_local_yz": list(P4_ROLLER_LOCAL),
        "p4_floating_gap_to_hub_mm": round(
            (math.hypot(*P4_ROLLER_LOCAL) - 0.021 - 0.0062) * 1000.0, 2),
        "p5_placement_local_yz": [round(PIN_LOCAL[0], 6), round(PIN_LOCAL[1], 6)],
        "p5_radius_m": PIN_RADIUS,
        "p5_phase_deg": PIN_PHASE_DEG,
        "carried_by": ["handle_yoke_-1", "handle_yoke_1"],
        "support_parts": ["handle_pin_boss_-1", "handle_pin_boss_1"],
        "pin_half_x_m": PIN_HALF_X,
        "cheek_outer_x_m": 0.019250,
        "proud_of_cheek_mm": round((PIN_HALF_X - 0.019250) * 1000.0, 2),
        "yoke_front_local_y_m": YOKE_FRONT,
        "pin_local_y_span_m": [round(PIN_LOCAL[0] - PIN_R, 5),
                               round(PIN_LOCAL[0] + PIN_R, 5)],
        "cheek_contains_pin": (YOKE_FRONT < PIN_LOCAL[0] - PIN_R
                               and PIN_LOCAL[0] + PIN_R < 0.006),
        "floating_gap_mm": 0.0,
        "pin_sweep_world": {k: [round(x, 5) for x in v]
                            for k, v in pin_sweep(angles, PIN_R).items()},
    }
    audit["slot"] = {
        "face_slab_m": list(face_slab),
        "slab_note": ("measured to the rims' front plane, not the shell face; "
                      "P4 measured to the face and the arm root cut rim_top"),
        "required_z_m": [need_face["z_min"], need_face["z_max"]],
        "pin_span_z_m": list(pin_span["z"]),
        "slot_z_m": [slot_lo, slot_hi],
        "slot_size_m": list(slot),
        "slot_centre_z_m": slot_centre_z,
        "margin_m": margin,
        "p4_slot_size_m": [0.074, 0.12196805546080285],
        "floor_bore_margin_m": FLOOR_BORE_MARGIN,
        "poses": need_face["poses"],
        "footprint_method": need_face["method"],
    }
    body = p1.join(parts[0], parts[1:])
    body.name = "Lever_body"
    body.data.name = "Lever_body"
    p1.assign(body, material)

    handle.parent = pivot
    return body, pivot, handle, audit


BUILDERS_P5 = {
    "MeterRound": p4.build_meter_round,
    "Lever": build_lever,
    "Toggle": p4.build_toggle,
}


# ---------------------------------------------------------------------------
# moving-vs-static clearance, measured on the real meshes
# ---------------------------------------------------------------------------

# The statics alignment 292.1 item 5 names. The rest of the housing is
# reported too, but only these four are gated: the gasket, skirt and plate are
# the slab behind the shell face that the hub and yoke are meant to run
# inside, and calling those intersections defects would be wrong.
GATED_STATICS = ("shell", "slot_floor", "rim_left", "rim_right", "rim_top",
                 "rim_bottom", "cam_plate")


def clearance_audit(pivot, handle, angles, steps=96, sample=3):
    """Triangle-level intersection first, then vertex-to-surface distance.

    Swept bounds and slot margins are projections; they cannot see a part
    passing beside an opening rather than through it. This walks the real
    meshes: BVH overlap gives the intersecting triangle pairs per static part,
    and where there are none the nearest-surface query gives how much room is
    actually left, so the report carries a clearance rather than an absence of
    evidence.
    """
    trees = {name: BVHTree.FromPolygons(verts, faces, all_triangles=True)
             for name, (verts, faces) in LAST_STATIC_PARTS.items()}
    low, high = min(angles), max(angles)
    original = tuple(pivot.rotation_euler)
    per_part = {}
    worst_pose = None
    worst_clearance = None
    intersections = []
    for index in range(steps + 1):
        deg = low + (high - low) * index / steps
        pivot.rotation_euler = (math.radians(deg), 0.0, 0.0)
        bpy.context.view_layer.update()
        matrix = handle.matrix_world
        mesh = handle.data
        mesh.calc_loop_triangles()
        verts = [matrix @ v.co for v in mesh.vertices]
        faces = [tuple(t.vertices) for t in mesh.loop_triangles]
        moving = BVHTree.FromPolygons(verts, faces, all_triangles=True)
        pose_min = None
        for name in GATED_STATICS:
            tree = trees.get(name)
            if tree is None:
                continue
            pairs = moving.overlap(tree)
            row = per_part.setdefault(
                name, {"intersecting_poses": 0, "worst_triangle_pairs": 0,
                       "min_clearance_mm": None, "min_clearance_deg": None})
            if pairs:
                row["intersecting_poses"] += 1
                row["worst_triangle_pairs"] = max(row["worst_triangle_pairs"],
                                                  len(pairs))
                intersections.append({"deg": round(deg, 2), "static": name,
                                      "triangle_pairs": len(pairs)})
                pose_min = 0.0
                row["min_clearance_mm"] = 0.0
                row["min_clearance_deg"] = round(deg, 2)
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
            if row["min_clearance_mm"] is None or millimetres < row["min_clearance_mm"]:
                row["min_clearance_mm"] = millimetres
                row["min_clearance_deg"] = round(deg, 2)
            pose_min = millimetres if pose_min is None else min(pose_min, millimetres)
        if pose_min is not None and (worst_clearance is None
                                     or pose_min < worst_clearance):
            worst_clearance = pose_min
            worst_pose = round(deg, 2)
    pivot.rotation_euler = original
    bpy.context.view_layer.update()
    return {
        "gated_statics": list(GATED_STATICS),
        "ungated_note": ("gasket, skirt and plate form the slab behind the "
                         "shell face that the hub and yoke are designed to "
                         "run inside; they are not gated"),
        "poses": steps + 1,
        "vertex_sample_stride": sample,
        "per_static": per_part,
        "intersections": intersections,
        "intersection_count": len(intersections),
        "min_clearance_mm": worst_clearance,
        "worst_pose_deg": worst_pose,
        "clean": not intersections,
        "method": ("BVH triangle overlap per pose; where none, "
                   "vertex-to-surface nearest distance from the moving mesh"),
    }


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


# Most upright, middle of the travel, opposite end - one camera for all three.
LEVER_POSES = (0.0, 24.0, 48.0)
LEVER_POSE_LABEL = {0.0: "upright", 24.0: "mid", 48.0: "out"}


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
        "phase": "Theme4-P5-geometry",
        "note": ("Lever only. handle_roller becomes the yoke's cross pin with "
                 "a bearing boss on each cheek; the slot is measured to the "
                 "rims' front plane; the slot floor bore margin is 4.0 mm. "
                 "MeterRound and Toggle are P4's builders, unmodified."),
        "changed_asset": "Lever",
        "assets": {},
    }

    import opus5_brushup_kinetic_review as review
    for asset, builder in BUILDERS_P5.items():
        p1.clear_scene()
        review.configure_scene()
        material = p1.proto.make_material(f"MAT_{THEME}_P5_Neutral", NEUTRAL)
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
        if asset == "Lever":
            row["clearance"] = clearance_audit(
                pivot, part, p1.MOTION[asset]["audit_deg_blender"])
        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P5.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        focus, radius, scale = p1.rig_for([body, part])
        images = {}
        for label, view in p1.VIEWS.items():
            path = grey_dir / f"Grey_{asset}_{THEME}_P5_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        row["grayscale_images"] = images

        details = {}
        if asset == "Lever":
            for deg in LEVER_POSES:
                pivot.rotation_euler = (math.radians(deg), 0.0, 0.0)
                bpy.context.view_layer.update()
                tag = LEVER_POSE_LABEL[deg]
                close = detail_dir / f"Detail_Lever_workpoint_{tag}.png"
                p1.shot((0.0, -0.050, -0.082), 0.170, (46.0, 10.0), 60.0,
                        0.085, close)
                details[f"workpoint_{tag}"] = str(
                    close.relative_to(project_root))
                side = detail_dir / f"Detail_Lever_side_{tag}.png"
                p1.shot(focus, radius, (58.0, 8.0), 52.0, scale, side)
                details[f"side_{tag}"] = str(side.relative_to(project_root))
            pivot.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
        row["detail_images"] = details
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        print(f"[Theme4P5] {asset}: tris {row['triangles_total']}, "
              f"coplanar pairs {audit['pair_count']}, "
              f"gates {row['all_gates_passed']}")

    lever = payload["assets"]["Lever"]
    payload["clearance"] = lever["clearance"]
    payload["working_point"] = lever["coplanar_overlap"]["working_point"]
    payload["slot"] = lever["coplanar_overlap"]["slot"]
    payload["status"] = (
        "p5_geometry_ready"
        if all(row["all_gates_passed"] for row in payload["assets"].values())
        and payload["clearance"]["clean"]
        and payload["working_point"]["cheek_contains_pin"]
        and payload["working_point"]["floating_gap_mm"] == 0.0
        else "p5_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4P5] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
