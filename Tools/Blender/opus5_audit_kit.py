"""Shared audit kit: the three things the per-batch audits kept getting wrong.

Across §290-§350 every gate failure was found by a person looking through a
headset or by Codex re-deriving a number - never by the JSON the generators
were already producing. Reading back why, three causes account for all of it.

1. **Verdicts were composed by luck.** Batch C's seating audit merged two
   probe dictionaries with `dict.update`, both carried a key called `clean`,
   and the second silently replaced the first: a screw whose seat was 6.2 mm
   off reported clean. `Verdict` here makes that impossible - a probe returns
   measurements and a boolean under its own name, and the composite is the
   explicit AND of every contributor, with the contributors kept.

2. **Checks only ever ran on the instrument that had just been complained
   about.** The buried screws existed from Batch A onward and were found in
   §315 only because a tool-path audit was written for one instrument. The
   checks here take a re-imported FBX and need no generator, so the whole
   shipped family can be swept in one pass.

3. **Two metrics cried wolf every run.** p3's coplanar audit compares
   axis-aligned boxes and reports 4 to 12 tick-to-tick pairs on assets that
   are fine; front silhouette IoU sits at 0.93-0.96 whatever the shape. Both
   had to be explained away in every report, which is how a real signal gets
   lost. This kit uses the separating-axis test only, and does not carry IoU.

Nothing here writes to, or imports from, a frozen generator.
"""

import hashlib
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))


PASS = "PASS"
FAIL = "FAIL"
REVIEW = "REVIEW"
NOT_APPLICABLE = "N/A"
VERDICT_VALUES = (PASS, FAIL, REVIEW, NOT_APPLICABLE)


def script_digests(paths):
    """SHA-256 of every audit script that produced a report.

    A report that cannot say which version of the audit produced it cannot be
    re-derived. §360 asked for this and it costs nothing.
    """
    digests = {}
    for path in paths:
        path = Path(path)
        digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(sorted(digests.items()))


class Tally:
    """A four-value count that states its population and its N/A reasons.

    §360 rejected the sentence "all 20 models pass" for a check that had run
    on nine of them. The arithmetic is now enforced rather than written by
    hand: every subject in the declared population lands in exactly one
    bucket, and `to_dict` refuses to serialise a tally that does not add up.

    Two rules the buckets encode. A check that did not run is never PASS. A
    check that *should* be able to judge a subject and cannot - a moving part
    whose kind of motion the check does not implement - is REVIEW, not N/A;
    N/A is only for subjects the check has no business judging.
    """

    def __init__(self, check, population):
        self.check = check
        self.population = int(population)
        self.buckets = {value: [] for value in VERDICT_VALUES}
        self.reasons = {}
        self.seen = set()

    def record(self, subject, verdict, reason=None):
        if verdict not in VERDICT_VALUES:
            raise SystemExit(f"[audit] {self.check}: '{verdict}' is not one "
                             f"of {VERDICT_VALUES}")
        # §362: the arithmetic added up while two different models shared one
        # subject string, and the same name sat in PASS and in N/A at once.
        # Counting the population is not enough - each subject must be named
        # once, so a second registration is refused whatever bucket it wants.
        if subject in self.seen:
            raise SystemExit(
                f"[audit] {self.check}: subject '{subject}' recorded twice; "
                "subjects must be unique, so two revisions of one model may "
                "not share a name")
        self.seen.add(subject)
        self.buckets[verdict].append(subject)
        if reason is not None:
            self.reasons.setdefault(reason, []).append(subject)
        return self

    def count(self, verdict):
        return len(self.buckets[verdict])

    def to_dict(self):
        counted = sum(len(v) for v in self.buckets.values())
        if counted != self.population:
            raise SystemExit(
                f"[audit] {self.check}: {counted} subjects recorded against "
                f"a declared population of {self.population}; a tally may "
                "not silently drop or double count a subject")
        return {
            "check": self.check,
            "population": self.population,
            "counts": {value: len(self.buckets[value])
                       for value in VERDICT_VALUES},
            "subjects": {value: list(self.buckets[value])
                         for value in VERDICT_VALUES},
            "reasons": {reason: list(subjects)
                        for reason, subjects in sorted(self.reasons.items())},
        }


class Verdict:
    """An AND that cannot lose a contributor to a name collision."""

    def __init__(self, name):
        self.name = name
        self.checks = {}

    def add(self, check, measurements, ok, verdict=None, note=None):
        if check in self.checks:
            raise SystemExit(f"[audit] {self.name}: duplicate check '{check}'; "
                             "a verdict may not be overwritten")
        if verdict is None:
            verdict = PASS if ok else FAIL
        if verdict not in VERDICT_VALUES:
            raise SystemExit(f"[audit] {self.name}: '{verdict}' is not one "
                             f"of {VERDICT_VALUES}")
        entry = {"measurements": measurements, "pass": bool(ok),
                 "verdict": verdict}
        if note is not None:
            entry["note"] = note
        self.checks[check] = entry
        return self

    def failing(self):
        return sorted(k for k, v in self.checks.items()
                      if v["verdict"] == FAIL)

    def needing_review(self):
        return sorted(k for k, v in self.checks.items()
                      if v["verdict"] == REVIEW)

    def to_dict(self):
        return {
            "subject": self.name,
            "checks": self.checks,
            "checks_run": sorted(self.checks),
            "verdicts": {name: entry["verdict"]
                         for name, entry in sorted(self.checks.items())},
            "counts": {value: sum(1 for entry in self.checks.values()
                                  if entry["verdict"] == value)
                       for value in VERDICT_VALUES},
            "failing": self.failing(),
            "needing_review": self.needing_review(),
            "pass": not self.failing(),
        }


def load_fbx(path):
    """Import one FBX into an empty file and return its mesh objects."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    bpy.context.view_layer.update()
    return [obj for obj in bpy.data.objects if obj.type == "MESH"]


def world_triangles(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    return [[matrix @ mesh.vertices[int(i)].co for i in tri.vertices]
            for tri in mesh.loop_triangles], [
        (matrix.to_3x3() @ tri.normal).normalized()
        for tri in mesh.loop_triangles]


def scene_bvh(objects):
    verts, faces = [], []
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        offset = len(verts)
        verts.extend(matrix @ v.co for v in mesh.vertices)
        faces.extend(tuple(int(i) + offset for i in tri.vertices)
                     for tri in mesh.loop_triangles)
    return BVHTree.FromPolygons(verts, faces, all_triangles=True)


# ---------------------------------------------------------------------------
# check: geometry that no viewer can ever see
# ---------------------------------------------------------------------------

def buried_geometry(objects, epsilon=2.0e-4, budget=None):
    """Triangles whose own outward direction is blocked by other geometry.

    A closed solid standing in the open has every face visible from somewhere,
    so a face whose outward ray immediately meets more material is inside
    something. That is what the meters' and the rotary's screws were - 192
    triangles each, sealed inside the housing, invisible from every direction
    and unreachable by any tool. Finding them needed a bespoke tool-path audit
    written after a headset review; this finds the same class from the shipped
    FBX alone, with no knowledge of part names.
    """
    tree = scene_bvh(objects)
    rows = {}
    for obj in objects:
        tris, normals = world_triangles(obj)
        blocked = 0
        depth_sum = 0.0
        limit = len(tris) if budget is None else min(len(tris), budget)
        for index in range(limit):
            centroid = (tris[index][0] + tris[index][1] + tris[index][2]) / 3.0
            direction = normals[index]
            if direction.length < 1e-9:
                continue
            origin = centroid + direction * epsilon
            hit = tree.ray_cast(origin, direction)
            if hit[0] is not None:
                blocked += 1
                depth_sum += float(hit[3])
        fraction = blocked / limit if limit else 0.0
        rows[obj.name.split(".")[0]] = {
            "triangles": len(tris),
            "sampled": limit,
            "outward_ray_blocked": blocked,
            "blocked_fraction": round(fraction, 6),
            "mean_blocked_depth_mm": round(depth_sum / blocked * 1000.0, 3)
            if blocked else None,
        }
    return rows


def buried_clusters(objects, threshold=0.98):
    """Whole connected components that are sealed inside other geometry.

    A blocked-fraction on a joined mesh is diluted: one buried screw inside a
    6,000 triangle body is 3 %. Splitting into connected components and asking
    the question per component is what makes a sealed part show up as 100 %.
    """
    tree = scene_bvh(objects)
    findings = []
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        parent = list(range(len(mesh.vertices)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for edge in mesh.edges:
            union(int(edge.vertices[0]), int(edge.vertices[1]))
        groups = {}
        for tri in mesh.loop_triangles:
            groups.setdefault(find(int(tri.vertices[0])), []).append(tri)
        for root, tris in groups.items():
            blocked = 0
            for tri in tris:
                points = [matrix @ mesh.vertices[int(i)].co
                          for i in tri.vertices]
                centroid = (points[0] + points[1] + points[2]) / 3.0
                direction = (matrix.to_3x3() @ tri.normal).normalized()
                if direction.length < 1e-9:
                    continue
                if tree.ray_cast(centroid + direction * 2.0e-4,
                                 direction)[0] is not None:
                    blocked += 1
            fraction = blocked / len(tris)
            if fraction >= threshold:
                points = [matrix @ mesh.vertices[int(i)].co
                          for tri in tris for i in tri.vertices]
                findings.append({
                    "object": obj.name.split(".")[0],
                    "triangles": len(tris),
                    "blocked_fraction": round(fraction, 6),
                    "centre_m": [round(sum(p[i] for p in points)
                                       / len(points), 5) for i in range(3)],
                    "size_m": [round(max(p[i] for p in points)
                                     - min(p[i] for p in points), 5)
                               for i in range(3)],
                })
    return findings


# ---------------------------------------------------------------------------
# check: coplanar overlap, by the separating-axis test only
# ---------------------------------------------------------------------------

def _overlap_2d(a, b):
    for polygon in (a, b):
        count = len(polygon)
        for index in range(count):
            x0, y0 = polygon[index]
            x1, y1 = polygon[(index + 1) % count]
            axis = (-(y1 - y0), x1 - x0)
            length = math.hypot(*axis)
            if length < 1e-12:
                continue
            axis = (axis[0] / length, axis[1] / length)
            spans = []
            for other in (a, b):
                values = [axis[0] * px + axis[1] * py for px, py in other]
                spans.append((min(values), max(values)))
            if spans[0][1] <= spans[1][0] + 1e-9 \
                    or spans[1][1] <= spans[0][0] + 1e-9:
                return False
    return True


def coplanar_overlap(objects, axis=2, tol=1.2e-4):
    """Faces of different objects sharing a plane and covering the same area.

    p3's version compares axis-aligned boxes, which is right for rectangular
    parts and wrong for a scale arc: adjacent ticks at different angles have
    overlapping boxes and disjoint triangles, and the two accepted round
    meters carry 6 and 10 such pairs to this day. Only the real overlap is
    reported here, so a non-zero count means something.
    """
    other = [i for i in range(3) if i != axis]
    faces = []
    for obj in objects:
        tris, normals = world_triangles(obj)
        for points, normal in zip(tris, normals):
            if abs(normal[axis]) < 0.999:
                continue
            faces.append({
                "object": obj.name.split(".")[0],
                "level": sum(p[axis] for p in points) / 3.0,
                "sign": 1 if normal[axis] > 0.0 else -1,
                "keys": {tuple(round(c, 6) for c in p) for p in points},
                "poly": [(p[other[0]], p[other[1]]) for p in points],
            })
    faces.sort(key=lambda row: row["level"])
    pairs = {}
    for index, a in enumerate(faces):
        for j in range(index + 1, len(faces)):
            b = faces[j]
            gap = b["level"] - a["level"]
            if gap > tol:
                break
            if a["object"] == b["object"] or (a["keys"] & b["keys"]):
                continue
            if _overlap_2d(a["poly"], b["poly"]):
                key = tuple(sorted((a["object"], b["object"])))
                facing = "same" if a["sign"] == b["sign"] else "back_to_back"
                bucket = pairs.setdefault(key, {})
                bucket[facing] = min(bucket.get(facing, gap), gap)
    fighting = {k: v["same"] for k, v in pairs.items() if "same" in v}
    contact = {k: v["back_to_back"] for k, v in pairs.items()
               if "same" not in v}
    return {"pairs": [list(k) for k in sorted(pairs)],
            "pair_count": len(pairs),
            # Two coplanar faces pointing the same way fight for the pixel.
            # Two pointing away from each other are a contact seam - one part
            # seated flush on another - and the far side is backface culled.
            # Only the first is a rendering defect; the second is hidden
            # surface worth knowing about but not worth rejecting a model for.
            "z_fighting_pairs": [list(k) for k in sorted(fighting)],
            "z_fighting_count": len(fighting),
            "contact_seam_pairs": [list(k) for k in sorted(contact)],
            "contact_seam_count": len(contact),
            "closest_gap_m": round(min(
                g for v in pairs.values() for g in v.values()), 7)
            if pairs else None,
            "method": "separating-axis test on triangles",
            "axis": "XYZ"[axis]}


# ---------------------------------------------------------------------------
# check: the display plane contract
# ---------------------------------------------------------------------------

def display_plane(objects, name="display_surface", front_axis=2,
                  front_sign=1.0, expect_triangles=2):
    """The contract every panel with a screen has to meet.

    Counted, not assumed: exactly one such object, flat, the stated number of
    triangles, a single outward normal along the front axis, and opaque
    material behind it so the graphic cannot be read from the back.
    """
    found = [obj for obj in objects if obj.name.split(".")[0] == name]
    if len(found) != 1:
        return {"count": len(found), "clean": False,
                "reason": "expected exactly one display surface"}
    display = found[0]
    tris, normals = world_triangles(display)
    unique = sorted({tuple(round(v, 6) for v in n) for n in normals})
    expected = tuple(front_sign if i == front_axis else 0.0 for i in range(3))
    # The graphic lives on the faces that point at the viewer. A two triangle
    # plane is nothing but those; §325 allowed a closed slab, whose other five
    # sides are edges and back and say nothing about the contract. Judging the
    # whole object read the slab's five other normals as failures.
    front = [tri for tri, normal in zip(tris, normals)
             if all(abs(normal[i] - expected[i]) < 1.0e-3 for i in range(3))]
    levels = {round(p[front_axis], 6) for tri in front for p in tri}
    statics = [obj for obj in objects if obj is not display]
    behind = None
    if front and statics:
        tree = scene_bvh(statics)
        points = [p for tri in front for p in tri]
        centre = Vector((sum(p.x for p in points) / len(points),
                         sum(p.y for p in points) / len(points),
                         sum(p.z for p in points) / len(points)))
        back = Vector(tuple(-v for v in expected))
        behind = tree.ray_cast(centre + back * 2.0e-4, back)[0] is not None
    return {
        "count": 1,
        "triangles": len(tris),
        "triangles_expected": expect_triangles,
        "normals": [list(n) for n in unique],
        "front_axis": "XYZ"[front_axis],
        "front_sign": front_sign,
        "front_facing_triangles": len(front),
        "front_face_coplanar": bool(front) and len(levels) == 1,
        "plane_level_m": round(next(iter(levels)), 6) if len(levels) == 1
        else None,
        "opaque_behind": behind,
        "clean": (len(tris) == expect_triangles and bool(front)
                  and len(levels) == 1 and behind is not False),
    }


# ---------------------------------------------------------------------------
# check: is a seat actually resting on a surface
# ---------------------------------------------------------------------------

SEAT_TOLERANCE_M = 1.0e-4
NORMAL_TOLERANCE_DEG = 0.1


def seat_probe(tree, centre, face_level, seat_radius, front_axis=1,
               front_sign=-1.0, rings=16):
    """Cast the service axis over the whole seat, not just its centre.

    §326's window meter screw had a centre gap of zero and a 6.2 mm step
    across the ring, because the inner 4 mm of the seat lay on the nameplate.
    A centre-only probe reports that as perfect. The ring is the measurement.
    """
    axes = [i for i in range(3) if i != front_axis]
    direction = [0.0, 0.0, 0.0]
    direction[front_axis] = -front_sign
    direction = Vector(direction)
    levels, normals, misses = [], [], 0
    for index in range(rings + 1):
        angle = 2.0 * math.pi * index / rings
        radius = 0.0 if index == 0 else seat_radius
        origin = [0.0, 0.0, 0.0]
        origin[axes[0]] = centre[0] + radius * math.cos(angle)
        origin[axes[1]] = centre[1] + radius * math.sin(angle)
        origin[front_axis] = front_sign * 0.60
        hit = tree.ray_cast(Vector(origin), direction)
        if hit[0] is None:
            misses += 1
            continue
        levels.append(float(hit[0][front_axis]))
        normals.append(float(hit[1][front_axis]))
    if not levels:
        return {"surface_hit": False}, False
    spread = max(levels) - min(levels)
    gap = levels[0] - face_level
    off_axis = math.degrees(math.acos(min(1.0, abs(normals[0]))))
    measurements = {
        "surface_hit": True,
        "ray_misses": misses,
        "surface_level_m": round(levels[0], 6),
        "seat_face_level_m": round(face_level, 6),
        "gap_mm": round(gap * 1000.0, 3),
        "seat_surface_spread_mm": round(spread * 1000.0, 3),
        "normal_off_axis_deg": round(off_axis, 3),
        "rings": rings,
    }
    ok = (misses == 0
          and abs(gap) <= SEAT_TOLERANCE_M
          and spread <= SEAT_TOLERANCE_M
          and off_axis <= NORMAL_TOLERANCE_DEG)
    return measurements, ok


def penetration_probe(tree, centre, face_level, embedment, front_axis=1,
                      front_sign=-1.0):
    """Does the seat's rear come out the far side of what it is fixed to?"""
    axes = [i for i in range(3) if i != front_axis]
    origin = [0.0, 0.0, 0.0]
    origin[axes[0]], origin[axes[1]] = centre
    origin[front_axis] = -front_sign * 0.60
    direction = [0.0, 0.0, 0.0]
    direction[front_axis] = front_sign
    hit = tree.ray_cast(Vector(origin), Vector(direction))
    if hit[0] is None:
        return {"back_surface_found": False}, False
    back = float(hit[0][front_axis])
    rear = face_level - front_sign * embedment
    through = (rear - back) * -front_sign
    return {
        "back_surface_found": True,
        "back_surface_level_m": round(back, 6),
        "seat_rear_level_m": round(rear, 6),
        "embedment_mm": round(embedment * 1000.0, 3),
        "penetration_mm": round(max(0.0, through) * 1000.0, 3),
    }, through <= 0.0


# ---------------------------------------------------------------------------
# check: can a driver reach the fastener
# ---------------------------------------------------------------------------

TOOL_SHAFT_R = 0.0040
TOOL_CLEAR_R = 0.0082
TOOL_REACH = 0.080


def _sphere_hits(tris, centre, radius):
    count, nearest = 0, float("inf")
    for points in tris:
        closest = _closest_on_triangle(points, centre)
        distance = (closest - centre).length
        nearest = min(nearest, distance)
        if distance < radius:
            count += 1
    return count, nearest


def _closest_on_triangle(points, point):
    a, b, c = points
    ab, ac, ap = b - a, c - a, point - a
    d1, d2 = ab.dot(ap), ac.dot(ap)
    if d1 <= 0 and d2 <= 0:
        return a
    bp = point - b
    d3, d4 = ab.dot(bp), ac.dot(bp)
    if d3 >= 0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0 <= d1 and d3 <= 0:
        return a + ab * (d1 / (d1 - d3))
    cp = point - c
    d5, d6 = ab.dot(cp), ac.dot(cp)
    if d6 >= 0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0 <= d2 and d6 <= 0:
        return a + ac * (d2 / (d2 - d6))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        return b + (c - b) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))
    denominator = va + vb + vc
    return a + ab * (vb / denominator) + ac * (vc / denominator)


def tool_path(obstacles, centre, start_level, radius, front_axis=1,
              front_sign=-1.0, reach=TOOL_REACH, step=0.001):
    """Sweep a cylinder straight out of the recess and count what it meets.

    Sampled as spheres at 1 mm. The first sample stands 0.2 mm clear of the
    head so a fastener never blocks its own path.
    """
    axes = [i for i in range(3) if i != front_axis]
    hits, nearest = 0, float("inf")
    for index in range(int(round(reach / step)) + 1):
        offset = 0.0002 + radius + index * step
        point = [0.0, 0.0, 0.0]
        point[axes[0]], point[axes[1]] = centre
        point[front_axis] = start_level + front_sign * offset
        count, distance = _sphere_hits(obstacles, Vector(point), radius)
        hits += count
        nearest = min(nearest, distance)
    return {"radius_mm": round(radius * 1000.0, 2),
            "reach_mm": round(reach * 1000.0, 1),
            "triangle_hits": hits,
            "clearance_mm": round((nearest - radius) * 1000.0, 2)}, hits == 0


# ---------------------------------------------------------------------------
# check: does the moving part stay clear across its runtime range
# ---------------------------------------------------------------------------

def pose_interference(mover, statics, axis, low_deg, high_deg, steps=144,
                      pivot=None):
    """Walk the real range and look for triangles actually touching.

    Batch A, B and C each grew their own copy of this, and none of them could
    be run against a shipped FBX. Here the mover is an object in the imported
    file and the range comes from the caller, so a candidate can be checked
    without its generator.
    """
    if pivot is None:
        pivot = Vector((0.0, 0.0, 0.0))
    tree = scene_bvh(statics)
    mesh = mover.data
    mesh.calc_loop_triangles()
    matrix = mover.matrix_world
    rest = [matrix @ v.co for v in mesh.vertices]
    faces = [tuple(int(i) for i in tri.vertices)
             for tri in mesh.loop_triangles]
    index = "XYZ".index(axis)
    worst = None
    intersecting = 0
    for step in range(steps + 1):
        fraction = step / steps if steps else 0.0
        degrees = low_deg + (high_deg - low_deg) * fraction
        rotation = Matrix.Rotation(math.radians(degrees), 4, axis)
        moved = [pivot + (rotation @ (point - pivot)) for point in rest]
        bvh = BVHTree.FromPolygons(moved, faces, all_triangles=True)
        if bvh.overlap(tree):
            intersecting += 1
        for point in moved[::7]:
            hit = tree.find_nearest(point)
            if hit[0] is None:
                continue
            distance = (hit[0] - point).length
            if worst is None or distance < worst[0]:
                worst = (distance, round(degrees, 3))
    return {
        "poses": steps + 1,
        "range_deg": [low_deg, high_deg],
        "axis": axis,
        "intersecting_poses": intersecting,
        "min_clearance_mm": None if worst is None
        else round(worst[0] * 1000.0, 3),
        "min_clearance_pose_deg": None if worst is None else worst[1],
    }, intersecting == 0


def linear_interference(mover, statics, axis, low_m, high_m, steps=48,
                        offset_m=0.0):
    """The same question for a part that slides instead of turning.

    Two shipped instruments declare `motion: translate` - PowerSlider, which
    travels +-0.09 m on its rail, and Button, which presses 0.014 m into its
    housing. The rotational sweep could judge neither, and both were being
    counted as "no moving part" alongside Lamp. That is the silence §360
    asked to stop: a moving instrument no check covers is a gap, not a pass
    and not a non-subject. Lamp, whose contract says `motion: none`, is a
    genuine non-subject and stays N/A.

    `offset_m` displaces the mover's rest geometry along the travel axis and
    exists so the A2 fixture can manufacture a known interference; leave it
    at zero for a real audit.
    """
    tree = scene_bvh(statics)
    mesh = mover.data
    mesh.calc_loop_triangles()
    matrix = mover.matrix_world
    index = "XYZ".index(axis)
    shift = Vector(tuple(offset_m if i == index else 0.0 for i in range(3)))
    rest = [(matrix @ v.co) + shift for v in mesh.vertices]
    faces = [tuple(int(i) for i in tri.vertices)
             for tri in mesh.loop_triangles]
    worst = None
    intersecting = 0
    for step in range(steps + 1):
        fraction = step / steps if steps else 0.0
        travel = low_m + (high_m - low_m) * fraction
        delta = Vector(tuple(travel if i == index else 0.0
                             for i in range(3)))
        moved = [point + delta for point in rest]
        bvh = BVHTree.FromPolygons(moved, faces, all_triangles=True)
        if bvh.overlap(tree):
            intersecting += 1
        for point in moved[::7]:
            hit = tree.find_nearest(point)
            if hit[0] is None:
                continue
            distance = (hit[0] - point).length
            if worst is None or distance < worst[0]:
                worst = (distance, round(travel, 5))
    return {
        "poses": steps + 1,
        "motion": "translate",
        "range_m": [low_m, high_m],
        "axis": axis,
        "mutation_offset_m": offset_m,
        "intersecting_poses": intersecting,
        "min_clearance_mm": None if worst is None
        else round(worst[0] * 1000.0, 3),
        "min_clearance_travel_m": None if worst is None else worst[1],
    }, intersecting == 0


# ---------------------------------------------------------------------------
# check: did the UV of unchanged faces survive a regeneration
# ---------------------------------------------------------------------------

def uv_carry(candidate_objects, reference_objects, tolerance=2.0e-5):
    """Compare UV face by face, matched on the three vertex positions.

    §317 and §321 were the same fault twice: re-running the packer on a mesh
    that had lost or gained a part relaid every island, repainting surfaces
    nobody had touched. Face and loop order are never used, because an
    exporter is free to change both.
    """
    reference = {}
    for obj in reference_objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        layer = mesh.uv_layers.active
        table = reference.setdefault(obj.name.split(".")[0], {})
        for tri in mesh.loop_triangles:
            points = [matrix @ mesh.vertices[int(i)].co for i in tri.vertices]
            key = tuple(sorted(tuple(round(c, 5) for c in p) for p in points))
            table[key] = {
                tuple(round(c, 5) for c in point):
                    tuple(layer.data[loop].uv)
                for point, loop in zip(points, tri.loops)}

    totals = {"triangles": 0, "matched": 0, "unmatched": 0, "uv_changed": 0,
              "max_uv_delta": 0.0}
    for obj in candidate_objects:
        name = obj.name.split(".")[0]
        table = reference.get(name)
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        layer = mesh.uv_layers.active
        for tri in mesh.loop_triangles:
            totals["triangles"] += 1
            if table is None:
                totals["unmatched"] += 1
                continue
            points = [matrix @ mesh.vertices[int(i)].co for i in tri.vertices]
            key = tuple(sorted(tuple(round(c, 5) for c in p) for p in points))
            entry = table.get(key)
            if entry is None:
                totals["unmatched"] += 1
                continue
            totals["matched"] += 1
            differs = False
            for point, loop in zip(points, tri.loops):
                target = entry.get(tuple(round(c, 5) for c in point))
                if target is None:
                    continue
                current = tuple(layer.data[loop].uv)
                delta = max(abs(current[0] - target[0]),
                            abs(current[1] - target[1]))
                totals["max_uv_delta"] = max(totals["max_uv_delta"], delta)
                if delta > tolerance:
                    differs = True
            if differs:
                totals["uv_changed"] += 1
    totals["max_uv_delta"] = round(totals["max_uv_delta"], 9)
    return totals, totals["uv_changed"] == 0
