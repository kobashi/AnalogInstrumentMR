"""Two layers: does it touch, and does it go in?

Alignment 84.1-84.3. The audits have been asking one question - "do these two
triangles intersect?" - and using the answer for two different purposes. A face
resting exactly on another face is a real observation, and so is a shaft buried
five millimetres inside a plate, but they are not the same finding and cannot
share a bucket.

So contact is reported in two layers.

* **Surface**: separated / tangent / crossing, per triangle pair, with the
  contact points and triangle indices kept. A zero-depth touch is `tangent` -
  recorded, not discarded, because clearance 0 is worth seeing.
* **Penetration**: how far one mesh reaches *inside* the other's material, in
  millimetres, with the vertex count and (optionally) a sampled volume.

Only the second layer carries a depth tolerance. 0.01 mm is an engineering
limit on penetration, not an epsilon for silencing surface intersections.

One correction underpins all of this. The previous plane test compared
`normal.dot(p) + offset` against `1e-9`, with `normal` **un-normalised** - so
the quantity scaled with triangle area and the threshold meant something
different on every mesh and every model size (alignment 84.1). Every signed
distance here is normalised and in metres, which is what makes a millimetre
tolerance mean the same thing on a 77 mm dial and a 1.2 m panel.
"""

import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree


# Surface classification: how close counts as "on the plane" rather than
# crossing it. Geometric, not an engineering limit - it exists so that an exact
# coincidence is not read as a crossing by floating point noise.
TANGENT_TOLERANCE_M = 1.0e-7

# Engineering limit on how far one part may reach inside another's material.
# Matches the tolerance measured on the PowerSlider sliding interface, where
# coincident faces put vertices 1-2 micrometres inside (alignment 69.1).
PENETRATION_TOLERANCE_MM = 0.01

# Candidate gathering only. Inflating the boxes costs a few extra pairs, which
# `classify` then rejects; using this same tree for measurement would swallow
# any intrusion shallower than the inflation (alignment 84.4).
BROAD_PHASE_EPSILON_M = 1.0e-5

SEPARATED = "separated"
TANGENT = "tangent"
CROSSING = "crossing"


def plane_of(triangle):
    """Unit normal and offset, so signed distances come out in metres."""
    normal = (triangle[1] - triangle[0]).cross(triangle[2] - triangle[0])
    length = normal.length
    if length < 1.0e-20:
        return None, None
    normal = normal / length
    return normal, -normal.dot(triangle[0])


def signed_distances(points, normal, offset):
    return [normal.dot(point) + offset for point in points]


def classify(first, second, tolerance=TANGENT_TOLERANCE_M):
    """`separated`, `tangent` or `crossing` for two triangles, in metres."""
    normal_b, offset_b = plane_of(second)
    normal_a, offset_a = plane_of(first)
    if normal_a is None or normal_b is None:
        return SEPARATED, []

    distance_a = signed_distances(first, normal_b, offset_b)
    if min(distance_a) > tolerance or max(distance_a) < -tolerance:
        return SEPARATED, []
    distance_b = signed_distances(second, normal_a, offset_a)
    if min(distance_b) > tolerance or max(distance_b) < -tolerance:
        return SEPARATED, []

    # Neither is wholly on one side. If nothing reaches past the plane by more
    # than the tolerance, the two are resting on each other, not crossing.
    crosses_a = max(distance_a) > tolerance and min(distance_a) < -tolerance
    crosses_b = max(distance_b) > tolerance and min(distance_b) < -tolerance
    points = _crossing_points(first, distance_a, second, normal_b) + _crossing_points(
        second, distance_b, first, normal_a
    )
    # Straddling each other's planes is necessary for a crossing but not
    # sufficient: two triangles far apart can each have vertices on both sides
    # of the other's plane. Without this, two bars merely resting edge on edge
    # came back as 64 crossings. A crossing has to produce a point that lies
    # inside the other triangle.
    # And a crossing leaves a segment, not a point. Two faces meeting along an
    # edge each have vertices on both sides of the other's plane and yield a
    # single shared point; passing through one another yields a segment of real
    # length inside both triangles. Four bar faces meeting edge on edge came
    # back as crossings until this was checked.
    span = 0.0
    for index, point in enumerate(points):
        for other in points[index + 1 :]:
            span = max(span, (point - other).length)
    if (
        crosses_a
        and crosses_b
        and span > tolerance
        and normal_a.cross(normal_b).length > tolerance
    ):
        return CROSSING, points
    if points or _within(distance_a, tolerance) or _within(distance_b, tolerance):
        return TANGENT, points
    return SEPARATED, []


def _within(distances, tolerance):
    return any(abs(value) <= tolerance for value in distances)


def _point_in_triangle(point, triangle, normal, epsilon=1.0e-12):
    total = 0.0
    for index in range(3):
        edge = triangle[(index + 1) % 3] - triangle[index]
        if edge.cross(point - triangle[index]).dot(normal) < -epsilon:
            return False
        total += 1.0
    return total == 3.0


def _crossing_points(triangle, distances, other, other_normal):
    points = []
    for index in range(3):
        following = (index + 1) % 3
        here, there = distances[index], distances[following]
        if here * there > 0.0:
            continue
        if abs(here - there) < 1.0e-20:
            continue
        ratio = here / (here - there)
        point = triangle[index].lerp(triangle[following], ratio)
        if _point_in_triangle(point, other, other_normal):
            points.append(point)
    return points


def _closest_on_segment(point, start, end):
    edge = end - start
    length = edge.length_squared
    if length < 1.0e-24:
        return start
    ratio = max(0.0, min(1.0, (point - start).dot(edge) / length))
    return start + edge * ratio


def point_triangle_distance(point, triangle):
    normal, offset = plane_of(triangle)
    if normal is not None:
        projected = point - normal * (normal.dot(point) + offset)
        if _point_in_triangle(projected, triangle, normal):
            return (point - projected).length
    return min(
        (point - _closest_on_segment(point, triangle[i], triangle[(i + 1) % 3])).length
        for i in range(3)
    )


def segment_segment_distance(p0, p1, q0, q1):
    """Closest approach of two segments, including the parallel case."""
    u, v, w = p1 - p0, q1 - q0, p0 - q0
    a, b, c = u.dot(u), u.dot(v), v.dot(v)
    d, e = u.dot(w), v.dot(w)
    denominator = a * c - b * b
    if denominator < 1.0e-24:
        s = 0.0
        t = (e / c) if c > 1.0e-24 else 0.0
    else:
        s = (b * e - c * d) / denominator
        t = (a * e - b * d) / denominator
    s = max(0.0, min(1.0, s))
    t = max(0.0, min(1.0, t))
    return ((p0 + u * s) - (q0 + v * t)).length


def triangle_distance(first, second):
    """Minimum distance between two triangles, 0 if they intersect."""
    if classify(first, second)[0] == CROSSING:
        return 0.0
    best = min(
        min(point_triangle_distance(point, second) for point in first),
        min(point_triangle_distance(point, first) for point in second),
    )
    for i in range(3):
        for j in range(3):
            best = min(
                best,
                segment_segment_distance(
                    first[i],
                    first[(i + 1) % 3],
                    second[j],
                    second[(j + 1) % 3],
                ),
            )
    return best


def candidate_pairs(
    mover_triangles,
    static_triangles,
    mover_tree,
    static_tree,
    tolerance=BROAD_PHASE_EPSILON_M,
):
    """Every pair whose triangles come within `tolerance`, in either direction.

    Alignment 88.1. `BVHTree.overlap` returns nothing for boxes meeting along
    an edge or at a corner, and the first proximity pass only queried the
    mover's own vertices and centroids - so a static vertex touching the middle
    of a mover face, or two edges meeting away from their endpoints, were both
    invisible, and the answer depended on which mesh was passed first.

    So the pass runs both ways and the narrow test is a real triangle-triangle
    distance rather than a handful of sample points. `find_nearest_range` is
    the coarse filter: it only returns triangles whose surface is already
    within the query radius, so the exact distance is evaluated on a short
    list, not on the full product.
    """
    pairs = set(mover_tree.overlap(static_tree))

    def sweep(source, source_tree, other, other_tree, flip):
        for index, triangle in enumerate(source):
            centroid = (triangle[0] + triangle[1] + triangle[2]) / 3.0
            radius = max((vertex - centroid).length for vertex in triangle) + tolerance
            for hit in other_tree.find_nearest_range(centroid, radius):
                candidate = hit[2]
                if candidate is None:
                    continue
                if triangle_distance(triangle, other[candidate]) <= tolerance:
                    pairs.add((candidate, index) if flip else (index, candidate))

    sweep(mover_triangles, mover_tree, static_triangles, static_tree, False)
    sweep(static_triangles, static_tree, mover_triangles, mover_tree, True)
    return sorted(pairs)


def surface_contact(mover_triangles, static_triangles, pairs):
    """Bucket every candidate pair, keeping triangle indices and points."""
    result = {SEPARATED: 0, TANGENT: [], CROSSING: []}
    for mine, theirs in pairs:
        bucket, points = classify(mover_triangles[mine], static_triangles[theirs])
        if bucket is SEPARATED or bucket == SEPARATED:
            result[SEPARATED] += 1
            continue
        result[bucket].append(
            {
                "mover_triangle": mine,
                "static_triangle": theirs,
                "points": [tuple(round(value, 8) for value in p) for p in points],
            }
        )
    return result


def inside_mesh(tree, point, direction=Vector((0.987, 0.109, 0.119))):
    """Point-in-mesh by ray parity, on a deliberately non-axis-aligned ray."""
    crossings = 0
    origin = point.copy()
    for _ in range(64):
        location, _, _, _ = tree.ray_cast(origin, direction)
        if location is None:
            break
        crossings += 1
        origin = location + direction * 1.0e-6
    return crossings % 2 == 1


# A vertex the ray-parity test calls "inside" but which sits on the surface is
# a boundary point, not an intrusion. Naming them apart is the whole point of
# separating the layers (alignment 86.2).
BOUNDARY_TOLERANCE_MM = 0.0001


def material_penetration(mover_vertices, static_tree):
    """How far the mover reaches into the static part, by vertex class."""
    boundary = 0
    within = 0
    penetrating = 0
    deepest = 0.0
    for point in mover_vertices:
        if not inside_mesh(static_tree, point):
            continue
        _, _, _, distance = static_tree.find_nearest(point)
        depth_mm = (distance or 0.0) * 1000.0
        if depth_mm <= BOUNDARY_TOLERANCE_MM:
            boundary += 1
        elif depth_mm <= PENETRATION_TOLERANCE_MM:
            within += 1
        else:
            penetrating += 1
        deepest = max(deepest, depth_mm)
    return {
        "boundary_vertices": boundary,
        "within_tolerance_vertices": within,
        "penetrating_vertices": penetrating,
        "raw_parity_hits": boundary + within + penetrating,
        "deepest_intrusion_mm": round(deepest, 6),
    }


def sampled_overlap(bounds_low, bounds_high, tree_a, tree_b, samples=24):
    """Is there volume in both? A fallback for crossings with no inside vertex."""
    span = [bounds_high[i] - bounds_low[i] for i in range(3)]
    if min(span) <= 0.0:
        return None
    step = [span[i] / samples for i in range(3)]
    hits = 0
    for ix in range(samples):
        for iy in range(samples):
            for iz in range(samples):
                point = Vector((
                    bounds_low[0] + (ix + 0.5) * step[0],
                    bounds_low[1] + (iy + 0.5) * step[1],
                    bounds_low[2] + (iz + 0.5) * step[2],
                ))
                if inside_mesh(tree_a, point) and inside_mesh(tree_b, point):
                    hits += 1
    return {
        "grid": samples,
        "cells_in_both": hits,
        "cell_volume_mm3": round(step[0] * step[1] * step[2] * 1e9, 6),
        "overlap_volume_mm3": round(hits * step[0] * step[1] * step[2] * 1e9, 6),
        "estimate": "grid-sampled, not exact",
    }


def verdict(penetration, crossing_count, overlap=None, tangent_count=0):
    """Combine both layers. Never `clear` while an unmeasured overlap exists.

    Alignment 86.3: two crossing prisms can share volume with neither one's
    vertices inside the other, so a verdict taken from vertex depth alone reads
    `clear` on a genuine interpenetration. When the surface layer says crossing
    and no vertex depth explains it, the sampled overlap decides, and if that
    cannot be computed the answer is a failure, not a pass.
    """
    if penetration["penetrating_vertices"]:
        return "penetration"
    # `penetration_unquantified` is for overlaps with *no depth at all* to
    # judge - not for shallow ones. A 5 micrometre intrusion has shared volume
    # and a measured depth inside tolerance; calling that unquantified would
    # fail the very case the tolerance exists for.
    # Alignment 88.2. A grid that found nothing is not proof that nothing is
    # there - a finite sample can step over a thin overlap, as this one did on
    # the crossing-prisms fixture until the grid was moved onto the AABB
    # intersection. So a crossing with no *measured* depth fails regardless of
    # what the grid says. Boundary vertices sit at depth 0 and measure nothing,
    # so they do not count as a quantified depth either.
    if penetration["within_tolerance_vertices"]:
        return "tangent_or_within_tolerance"
    if crossing_count:
        return "penetration_unquantified"
    # A tangent surface contact is still a contact: two edges meeting at a
    # point put no vertex inside anything, so a verdict taken from vertex
    # classes alone called it `clear`.
    if penetration["boundary_vertices"] or tangent_count:
        return "tangent_or_within_tolerance"
    return "clear"


def penetration_verdict(depth_mm, tolerance_mm=PENETRATION_TOLERANCE_MM):
    """Depth-only verdict, kept for callers that have no surface layer."""
    if depth_mm <= 0.0:
        return "clear"
    if depth_mm <= tolerance_mm:
        return "tangent_or_within_tolerance"
    return "penetration"
