"""Theme 4 fastener access R4: Lever and Toggle back on P5's UV and surface.

321 failed two things on Quest, and both are mine.

The first is a repeat of the fault 317 caught on the meters and the rotary:
R1 re-ran `dress()` on Lever and Toggle, so `pack_into_regions` relaid every
island. Codex measured 5,569 of Lever's 6,408 common triangles and 2,012 of
Toggle's 2,772 with changed UV. On the Lever that takes the grip off P5's
diamond-knurl Normal patch, which is why the knurl stopped reading and the arm
and grip stopped looking like two parts. R4 copies the UV back off the P5 FBX,
triangle by triangle, matched on the set of three vertex positions.

The second is specific to R4's Toggle and it is a plain error in R1. R1 moved
the four screws 6 mm inwards and set their seat plane to a fixed y -0.0400,
having checked only that the driver path was clear. It never checked that the
seat landed on anything. Casting the driver axis at those positions finds the
shell's corner chamfer 11.09 mm behind the seat, with a normal 59 degrees off
the axis and 19.23 mm of surface height across one seat - the screws are
hanging in the air outside the base, exactly as the headset showed.

The shell is drafted 20 to 24 degrees, so no small spot-face can sit on that
flank; a land big enough would be the added boss 321.5 forbids. The only
surface on this instrument facing the driver is the shell's front face, so the
four screws go there, at the outermost symmetric pattern that keeps a whole
seat on flat material and an 8.2 mm clearance to the access cap, the stops and
the bearing bosses. That pattern was searched, not chosen: +/-0.0320,
+/-0.0327 at y -0.0400.
"""

import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_fastener_access_r1 as fa
from opus5_theme4_fastener_access_r1 import fastener_id
import opus5_theme4_fastener_access_r3 as r3

BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
P5 = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p5"

REFERENCE = {
    "Lever": f"{P5}/SM_Lever_MachinedErgonomics_V6_Opus5_P5.fbx",
    "Toggle": f"{P5}/SM_Toggle_MachinedErgonomics_V6_Opus5_P5.fbx",
}
TARGETS = tuple(REFERENCE)
SEAT_RADIUS = {"Lever": 0.0060, "Toggle": 0.0052}

# 321.4 / 321.5. Searched over the shell's front face for the outermost
# symmetric pattern whose whole seat lands on flat material facing the driver
# and whose 8.2 mm clearance clears the access cap, the stops and the bosses.
TOGGLE_PATTERN = (0.0320, 0.0327)
TOGGLE_FACE_Y = -0.0400
SEAT_GAP_TOLERANCE = 0.0001       # 321.6: 0 +/- 0.1 mm


def toggle_positions():
    a, b = TOGGLE_PATTERN
    return {f"screw_{int(sx)}_{int(sz)}": (round(sx * a, 5), round(sz * b, 5))
            for sx in (-1, 1) for sz in (-1, 1)}


def overrides_for(asset, rows):
    """R1's table for the lever; the searched front-face pattern for toggle."""
    if asset == "Toggle":
        return {("Toggle", name): (centre, TOGGLE_FACE_Y)
                for name, centre in toggle_positions().items()}
    return fa.fix_positions(asset, rows)


# ---------------------------------------------------------------------------
# 321.4 / 321.6: does the seat actually land on the base?
# ---------------------------------------------------------------------------

def static_tree(parts):
    tris = np.concatenate([t for name, t in parts.items()
                           if fa.fastener_id(name) is None])
    verts = [Vector(v) for tri in tris for v in tri]
    faces = [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(tris))]
    return BVHTree.FromPolygons(verts, faces)


def seat_probe(tree, centre_xz, face_y, seat_r, rings=16):
    """Cast the driver axis over the whole seat and report what it lands on.

    Sampling the centre alone would have passed R1's toggle: the ray does hit
    the shell there, 11 mm further back. The ring is what shows the seat is
    lying across a 59-degree chamfer rather than sitting on a face.
    """
    cx, cz = centre_xz
    hits, normals, misses = [], [], 0
    for index in range(rings + 1):
        angle = 2.0 * math.pi * index / rings
        radius = 0.0 if index == 0 else seat_r
        origin = Vector((cx + radius * math.cos(angle), -0.30,
                         cz + radius * math.sin(angle)))
        location, normal, _, _ = tree.ray_cast(origin, Vector((0.0, 1.0, 0.0)))
        if location is None:
            misses += 1
            continue
        hits.append(float(location.y))
        normals.append(float(normal.y))
    if not hits:
        return {"surface_hit": False, "clean": False}
    spread = max(hits) - min(hits)
    gap = hits[0] - face_y
    return {
        "surface_hit": True,
        "ray_misses": misses,
        "surface_y_m": round(hits[0], 5),
        "seat_face_y_m": round(face_y, 5),
        "gap_mm": round(gap * 1000.0, 3),
        "seat_surface_spread_mm": round(spread * 1000.0, 3),
        "surface_normal_y": round(normals[0], 4),
        "normal_off_axis_deg": round(
            math.degrees(math.acos(min(1.0, abs(normals[0])))), 2),
        "clean": (misses == 0 and abs(gap) <= SEAT_GAP_TOLERANCE
                  and spread <= SEAT_GAP_TOLERANCE
                  and abs(normals[0]) >= 0.999),
    }


def penetration_probe(tree, centre_xz, face_y, seat_depth):
    """Does the seat's rear come out the back of what it is screwed into?"""
    cx, cz = centre_xz
    rear = face_y + seat_depth
    origin = Vector((cx, 0.30, cz))
    location, _, _, _ = tree.ray_cast(origin, Vector((0.0, -1.0, 0.0)))
    if location is None:
        return {"back_surface_found": False, "penetration_mm": None,
                "clean": False}
    back = float(location.y)
    through = rear - back
    return {"back_surface_found": True,
            "seat_rear_y_m": round(rear, 5),
            "back_surface_y_m": round(back, 5),
            "embedment_mm": round((rear - face_y) * 1000.0, 3),
            "penetration_mm": round(max(0.0, through) * 1000.0, 3),
            "clean": through <= 0.0}


# ---------------------------------------------------------------------------
# 321.2 / 321.3: UV from P5, common faces in place and screws by their own id
# ---------------------------------------------------------------------------

def copy_uv_multi(obj, reference, offsets, tolerance=r3.POSITION_TOLERANCE):
    """Copy P5's UV, trying the identity first and then each screw's offset.

    A relocated screw is the same geometry translated, so adding the vector
    from its new head centre to its P5 one puts its triangles exactly on the
    P5 originals. That is 321.3's "fastener ID plus local triangle
    correspondence", done as a position match so face and loop order still do
    not matter. Every reference triangle may be consumed once, which is what
    makes a duplicate match detectable rather than silently overwriting.
    """
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    tree = reference["tree"]
    table = reference["triangles"]
    uv_layer = mesh.uv_layers.active
    consumed = {}
    stats = {"triangles": len(mesh.loop_triangles), "by_offset": {},
             "unmatched": 0, "duplicate": 0, "uv_changed_before": 0}

    for tri in mesh.loop_triangles:
        base = [matrix @ mesh.vertices[int(v)].co for v in tri.vertices]
        matched = None
        for label, offset in offsets:
            shift = Vector(offset)
            ids, missing = [], False
            for point in base:
                _, index, distance = tree.find(point + shift)
                if index is None or distance > tolerance:
                    missing = True
                    break
                ids.append(index)
            if missing:
                continue
            key = tuple(sorted(ids))
            entries = table.get(key)
            if not entries or len(entries) > 1:
                continue
            if consumed.get(key):
                stats["duplicate"] += 1
                continue
            matched = (label, ids, entries[0], key)
            break
        if matched is None:
            stats["unmatched"] += 1
            continue
        label, ids, entry, key = matched
        consumed[key] = True
        stats["by_offset"][label] = stats["by_offset"].get(label, 0) + 1
        differed = False
        for cluster, loop in zip(ids, tri.loops):
            target = entry["uv"][cluster]
            current = tuple(uv_layer.data[loop].uv)
            if abs(current[0] - target[0]) > 1e-6 \
                    or abs(current[1] - target[1]) > 1e-6:
                differed = True
            uv_layer.data[loop].uv = target
        if differed:
            stats["uv_changed_before"] += 1
    stats["clean"] = stats["unmatched"] == 0 and stats["duplicate"] == 0
    return stats


def verify_uv_multi(obj, reference, offsets, tolerance=r3.POSITION_TOLERANCE):
    """Re-measure the same correspondence and count anything still different."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    tree = reference["tree"]
    table = reference["triangles"]
    uv_layer = mesh.uv_layers.active
    seen = {}
    out = {"triangles": len(mesh.loop_triangles), "compared": 0,
           "uv_changed": 0, "unmatched": 0, "position_mismatch": 0,
           "duplicate_match": 0, "max_uv_delta": 0.0, "by_offset": {}}
    for tri in mesh.loop_triangles:
        base = [matrix @ mesh.vertices[int(v)].co for v in tri.vertices]
        matched = None
        any_position = False
        for label, offset in offsets:
            shift = Vector(offset)
            ids, missing = [], False
            for point in base:
                _, index, distance = tree.find(point + shift)
                if index is None or distance > tolerance:
                    missing = True
                    break
                ids.append(index)
            if missing:
                continue
            any_position = True
            key = tuple(sorted(ids))
            entries = table.get(key)
            if not entries:
                continue
            if len(entries) > 1 or seen.get(key):
                out["duplicate_match"] += 1
                matched = "dup"
                break
            seen[key] = True
            matched = (label, ids, entries[0])
            break
        if matched == "dup":
            continue
        if matched is None:
            if any_position:
                out["unmatched"] += 1
            else:
                out["position_mismatch"] += 1
            continue
        label, ids, entry = matched
        out["by_offset"][label] = out["by_offset"].get(label, 0) + 1
        out["compared"] += 1
        differs = False
        for cluster, loop in zip(ids, tri.loops):
            target = entry["uv"][cluster]
            current = tuple(uv_layer.data[loop].uv)
            delta = max(abs(current[0] - target[0]),
                        abs(current[1] - target[1]))
            out["max_uv_delta"] = max(out["max_uv_delta"], delta)
            if delta > 1e-6:
                differs = True
        if differs:
            out["uv_changed"] += 1
    out["max_uv_delta"] = round(out["max_uv_delta"], 9)
    out["clean"] = (out["uv_changed"] == 0 and out["unmatched"] == 0
                    and out["position_mismatch"] == 0
                    and out["duplicate_match"] == 0
                    and out["compared"] == out["triangles"])
    return out


# ---------------------------------------------------------------------------
# 321.7: interference over the real runtime range
# ---------------------------------------------------------------------------

def fastener_frame(parts, fastener):
    """Unrounded head centre and front plane for one fastener.

    The audit's `head_centre_m` is rounded to 0.1 mm for reporting, and an
    offset built from two of those can be 0.1 mm out - five times the position
    tolerance, which is what made the lever's two relocated screws fail to
    match while the toggle's four, whose rounding happened to cancel, matched
    fine.
    """
    tris = [t for name, t in parts.items() if fastener_id(name) == fastener]
    if not tris:
        return None
    stacked = np.concatenate(tris)
    return (float(0.5 * (stacked[:, :, 0].min() + stacked[:, :, 0].max())),
            float(stacked[:, :, 1].min()),
            float(0.5 * (stacked[:, :, 2].min() + stacked[:, :, 2].max())))


def screw_offsets(pristine_parts, current_parts):
    """The exact vector from each moved screw back onto its P5 original."""
    out = []
    names = sorted({fastener_id(name) for name in current_parts
                    if fastener_id(name)})
    for name in names:
        before = fastener_frame(pristine_parts, name)
        after = fastener_frame(current_parts, name)
        if before is None or after is None:
            continue
        shift = tuple(before[i] - after[i] for i in range(3))
        if max(abs(v) for v in shift) < 1e-7:
            continue
        out.append((name, shift))
    return out


def bvh_from_triangles(tris, quantum=1e-6):
    """A BVH from a triangle soup, welded back into indexed topology first.

    Feeding FromPolygons three fresh vertices per triangle produces a tree
    that reports overlaps between parts that are nowhere near each other -
    the lever's handle against its own back plate, thousands of pairs a pose.
    Batch B's audit builds from mesh vertices and index triangles, and welding
    the soup the same way is what makes this agree with it.
    """
    lookup, verts, faces = {}, [], []
    for tri in tris:
        face = []
        for point in tri:
            key = tuple(int(round(float(c) / quantum)) for c in point)
            index = lookup.get(key)
            if index is None:
                index = len(verts)
                lookup[key] = index
                verts.append(Vector((float(point[0]), float(point[1]),
                                     float(point[2]))))
            face.append(index)
        if len(set(face)) == 3:
            faces.append(tuple(face))
    return BVHTree.FromPolygons(verts, faces, all_triangles=True)


def static_parts(parts, movers):
    """Everything captured that is not part of the moving assembly."""
    stems = {obj.name.split(".")[0] for obj in movers if obj is not None}
    out = {}
    for name, tris in parts.items():
        base = name.split(".")[0]
        if base in stems or any(base.startswith(f"{stem}_") for stem in stems):
            continue
        out[name] = tris
    return out


# These instruments are built without booleans, so parts interpenetrate by
# construction: the lever's hub passes through the plate, its pin sits inside
# the pillow bearings, the toggle's head lives inside the shell and its shaft
# runs in the bearing bores, and the stops are what the throw lands on. P5's
# own audit gated a named subset for exactly that reason, and its list is
# reused here rather than re-derived. The toggle never had one, so its
# designed contacts are named here and everything else is gated.
GATED_EXCLUDE = {
    "Lever": None,                 # use P5's positive list instead
    "Toggle": ("shell", "boss_-1", "boss_1", "boss_cap_-1", "boss_cap_1",
               "stop_-1", "stop_1"),
}
GATED_INCLUDE = {
    "Lever": ("shell", "slot_floor", "rim_left", "rim_right", "rim_top",
              "rim_bottom", "cam_plate"),
}


def gated_names(asset, statics):
    include = GATED_INCLUDE.get(asset)
    if include is not None:
        return tuple(name for name in statics if name in include)
    exclude = GATED_EXCLUDE.get(asset) or ()
    return tuple(name for name in statics if name not in exclude)


def motion_interference(pivot, movers, statics, asset, steps=96, sample=3):
    """Walk the runtime range and look for triangles actually touching.

    The pilot instruments have no Batch A/B contract row, so the range comes
    from p1.MOTION - the same table the P3/P4/P5 audits used - and the sweep
    is 96 steps, which is the 97 poses 321.7 asks for on the lever.
    """
    motion = p1.MOTION[asset]
    axis = motion["blender_axis"]
    low, high = 0.0, max(abs(v) for v in motion["audit_deg_blender"])
    # Statics are the captured parts minus the ones joined into the mover:
    # per part, so a contact can be named. Testing against the joined body
    # instead reports one anonymous number, and testing against the whole part
    # list reports the mover against itself at every pose.
    trees = {name: bvh_from_triangles(tris) for name, tris in statics.items()}
    original = tuple(pivot.rotation_euler)
    worst = None
    overlaps = {}
    poses = 0
    for index in range(steps + 1):
        degrees = low + (high - low) * index / steps
        euler = [0.0, 0.0, 0.0]
        euler["XYZ".index(axis)] = math.radians(degrees)
        pivot.rotation_euler = euler
        bpy.context.view_layer.update()
        poses += 1
        verts, faces = [], []
        for obj in movers:
            if obj is None:
                continue
            mesh = obj.data
            mesh.calc_loop_triangles()
            matrix = obj.matrix_world
            offset = len(verts)
            verts.extend(matrix @ v.co for v in mesh.vertices)
            faces.extend(tuple(int(i) + offset for i in tri.vertices)
                         for tri in mesh.loop_triangles)
        mover_tree = BVHTree.FromPolygons(verts, faces, all_triangles=True)
        for name, tree in trees.items():
            hits = mover_tree.overlap(tree)
            if hits:
                overlaps[name] = overlaps.get(name, 0) + len(hits)
        if index % sample == 0:
            for name, tree in trees.items():
                for point in verts[::7]:
                    location, _, _, distance = tree.find_nearest(point)
                    if location is None:
                        continue
                    if worst is None or distance < worst[0]:
                        worst = (distance, name, round(degrees, 2))
    pivot.rotation_euler = original
    bpy.context.view_layer.update()
    gated = gated_names(asset, statics)
    gated_hits = {name: count for name, count in overlaps.items()
                  if name in gated}
    return {
        "poses": poses,
        "gated_statics": list(gated),
        "gated_basis": ("P5's own GATED_STATICS list"
                        if asset in GATED_INCLUDE else
                        "everything except the designed contacts "
                        + ", ".join(GATED_EXCLUDE.get(asset) or ())),
        "gated_intersecting_parts": gated_hits,
        "gated_clean": not gated_hits,
        "range_blender_deg": [low, high],
        "runtime_range_unity_deg": list(motion["runtime_range_unity_deg"]),
        "intersecting_parts_all": overlaps,
        "designed_contacts_note": (
            "non-zero entries outside the gated set are the pass-throughs "
            "these boolean-free greyboxes are built with, and they are "
            "identical in the P5 state measured in the same run"),
        "min_clearance_mm": None if worst is None else round(worst[0] * 1000, 3),
        "min_clearance_part": None if worst is None else worst[1],
        "min_clearance_pose_deg": None if worst is None else worst[2],
        "clean": not gated_hits,
    }


# ---------------------------------------------------------------------------
# 321.6: does the lever grip's UV land on P5's knurl patch?
# ---------------------------------------------------------------------------

def patch_reference(obj, grip_tris, patch, transforms=None,
                    tolerance=r3.POSITION_TOLERANCE):
    """How much of the grip's UV sits inside the atlas knurl region.

    The grip is one part inside a joined mesh, so its triangles are found by
    position rather than by name, and then their loops are tested against the
    region box p4d publishes. A grip that has been repacked reads as a low
    number here long before anyone puts the headset on.
    """
    # The handle's parts are authored in pivot-local coordinates and only
    # become world coordinates once the object is parented, so the captured
    # triangles and the joined mesh can be a pivot translation apart. Both
    # candidate frames are tried and the one that matches is reported.
    candidates = list(transforms or [Vector((0.0, 0.0, 0.0))])
    key_sets = []
    for shift in candidates:
        key_sets.append({
            tuple(sorted(tuple(round(float(v[i]) + shift[i], 5)
                               for i in range(3)) for v in tri))
            for tri in grip_tris})
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    uv_layer = mesh.uv_layers.active
    u0, v0, u1, v1 = patch
    inside = outside = 0
    bounds = [1e9, 1e9, -1e9, -1e9]
    found = 0
    chosen = None
    for index, keys in enumerate(key_sets):
        hits = 0
        for tri in mesh.loop_triangles:
            key = tuple(sorted(
                tuple(round(float(c), 5)
                      for c in (matrix @ mesh.vertices[int(v)].co))
                for v in tri.vertices))
            if key in keys:
                hits += 1
        if hits:
            chosen = index
            break
    keys = key_sets[chosen] if chosen is not None else set()
    for tri in mesh.loop_triangles:
        key = tuple(sorted(
            tuple(round(float(c), 5)
                  for c in (matrix @ mesh.vertices[int(v)].co))
            for v in tri.vertices))
        if key not in keys:
            continue
        found += 1
        for loop in tri.loops:
            u, v = uv_layer.data[loop].uv
            bounds[0] = min(bounds[0], u)
            bounds[1] = min(bounds[1], v)
            bounds[2] = max(bounds[2], u)
            bounds[3] = max(bounds[3], v)
            if u0 - 1e-6 <= u <= u1 + 1e-6 and v0 - 1e-6 <= v <= v1 + 1e-6:
                inside += 1
            else:
                outside += 1
    total = inside + outside
    return {
        "frame_used": ("captured" if chosen == 0 else
                       "pivot-shifted" if chosen == 1 else "none matched"),
        "grip_triangles_in_reference": len(keys),
        "grip_triangles_found": found,
        "loops": total,
        "loops_inside_patch": inside,
        "loops_outside_patch": outside,
        "fraction_inside": round(inside / total, 6) if total else None,
        "patch_uv": [round(v, 6) for v in patch],
        "grip_uv_bounds": [round(v, 6) for v in bounds] if total else None,
        "clean": total > 0 and outside == 0,
    }
