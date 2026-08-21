"""Phase M2n2b1b: finish the adapter fixtures §174 found incomplete.

Alignment 174. §173 measured triangle counts and called that a polygon check,
kept one `measurement_valid` for every kind of number at once, matched objects
by the stem of a Blender-assigned name, and shipped fixtures that did not
exercise what they claimed - the reorder reordered only the source, the seam
was one quad with per-loop values rather than two faces sharing a vertex, and
nothing proved a hard edge was observable at all.

What changes here:

* the polygon surface itself is the gate. Every normalized triangle is assigned
  to the source-evaluated polygon that contains it, and boundary, internal
  diagonal, area, material, orientation and per-layer corner UV are compared.
  For a non-planar quad the diagonal Blender's own display triangulation chose
  must be the diagonal the explicit triangulation chose.
* geometry, face normal, split normal and each UV layer are separate
  measurements, each with its own expected / matched / coverage / scalar count
  / validity / max / RMS. A kind that was not measured reports `null`.
* objects carry an explicit `opus5_id`. Identity is asserted unique and the
  correspondence is made on it, never on a name or the stem of a name.
* the export copy reproduces the hierarchy rather than flattening it.
* fixtures assert their own premise: the reorder must really differ, the seam
  must really split a shared vertex, the hard edge must really carry two split
  normals at one position.
* every gate has a negative control that must fail it.

The `use_triangles` variants are diffed field by field into the JSON, and the
overall status is decided by the adopted setting alone.

No canonical source and none of the real-model staging is opened.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_fbx_adapter_completion.py -- \
      --project-root "$PWD" --mode build --staging /tmp/x
"""

import argparse
import copy as copy_module
import itertools
import json
import math
import random
import sys
import time
import traceback
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_toggle_fbx_handoff as toggle
from opus5_fbx_verifier_selftest_a3 import ERROR_SCALE, components
from opus5_fbx_verifier_selftest_a4 import solve_component
from opus5_fbx_verifier_selftest_a5 import (
    compare_uv_mesh,
    evidence_ambiguity,
    solve_with,
)


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/fbx_adapter_completion.json"
POSITION_BOUND_M = 1.0e-5
NORMAL_BOUND_DEG = 0.5
CORNER_TOLERANCE_M = 1.0e-4
AREA_RELATIVE_BOUND = 1.0e-6
# A copy under a duplicated hierarchy reaches the same world point through a
# different chain of float32 matrices, so "the same vertex" is the same to
# float32's relative epsilon (1.2e-7) times the coordinate, not bit for bit.
# At these sizes that is under 1e-7 m; 1e-6 m is a decade of headroom and still
# a hundredth of the smallest difference any gate cares about.
BOUNDS_BOUND_M = 1.0e-6
SNAP_TOLERANCE_M = 1.0e-6
KEY_DECIMALS = 9
# A local transform reaches the copy through a different float32 chain, same
# reasoning as BOUNDS_BOUND_M; rotations are order 1 and positions under a
# metre, so 1e-6 is a decade of headroom on either.
TRANSFORM_BOUND = 1.0e-6
SHUFFLE_SEEDS = (20260813, 90210, 7)
ADOPTED_VARIANT = "tri0"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--mode", required=True, choices=("build", "reimport", "probe", "report")
    )
    parser.add_argument("--staging", required=True)
    return parser.parse_args(args)


# --------------------------------------------------------------------------
# Fixture construction


def fresh():
    bpy.ops.wm.read_homefile(use_empty=True)
    root = bpy.data.objects.new("PF_Visual_Completion", None)
    bpy.context.collection.objects.link(root)
    root["opus5_id"] = "root"
    return root


def empty(name, parent, identity):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj["opus5_id"] = identity
    return obj


def mesh_object(name, parent, identity, verts, faces, uv_layers=()):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj["opus5_id"] = identity
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    for index, layer_name in enumerate(uv_layers):
        mesh.uv_layers.new(name=layer_name)
    return obj


def quad(half=0.1):
    verts = [
        (-half, 0.0, -half), (half, 0.0, -half),
        (half, 0.0, half), (-half, 0.0, half),
    ]
    return verts, [(0, 1, 2, 3)]


def plane(name, parent, identity, uv_layers=("UVMap",)):
    verts, faces = quad()
    obj = mesh_object(name, parent, identity, verts, faces, uv_layers)
    for index, layer in enumerate(obj.data.uv_layers):
        for loop_index, datum in enumerate(layer.data):
            datum.uv = (
                (loop_index % 4) / 4.0 + index * 0.1,
                (loop_index % 4) / 8.0 + index * 0.1,
            )
    return obj


def two_faces(name, parent, identity, lift=0.0, uv_layers=("UVMap",)):
    """Two quads sharing an edge, so a vertex is genuinely shared."""
    verts = [
        (-0.1, 0.0, -0.1), (0.0, 0.0, -0.1), (0.0, 0.0, 0.1), (-0.1, 0.0, 0.1),
        (0.1, lift, -0.1), (0.1, lift, 0.1),
    ]
    faces = [(0, 1, 2, 3), (1, 4, 5, 2)]
    return mesh_object(name, parent, identity, verts, faces, uv_layers)


# Individual fixtures ------------------------------------------------------


def f_parent_transform(root):
    outer = empty("outer", root, "outer")
    outer.location = (0.3, -0.15, 0.05)
    outer.rotation_euler = (0.2, 0.4, 0.1)
    inner = empty("inner", outer, "inner")
    inner.location = (-0.05, 0.02, 0.11)
    inner.rotation_euler = (0.0, 0.0, 0.7)
    obj = plane("under_parent", inner, "under_parent")
    return [obj]


def f_non_uniform_scale(root):
    obj = plane("scaled", root, "scaled")
    obj.scale = (1.7, 0.6, 1.15)
    return [obj]


def f_micro_rotation(root):
    obj = plane("micro_rotation", root, "micro_rotation")
    obj.rotation_euler = (0.0, math.radians(6.147170e-05), 0.0)
    return [obj]


def f_vertex_reorder(root):
    """The reorder happens on the export copy - see `shuffle_mesh_order`."""
    return [plane("reordered", root, "reordered")]


def f_uv_seam(root):
    """A real seam: the shared vertices carry different UVs on each face."""
    obj = two_faces("seam", root, "seam")
    layer = obj.data.uv_layers[0]
    for polygon in obj.data.polygons:
        for loop_index in polygon.loop_indices:
            vertex = obj.data.loops[loop_index].vertex_index
            side = 0.0 if polygon.index == 0 else 0.5
            layer.data[loop_index].uv = (side + 0.125 * vertex, 0.25 * vertex)
    return [obj]


def f_multi_uv(root):
    obj = plane("multi_uv", root, "multi_uv", uv_layers=("UVMap", "Second"))
    obj.data.uv_layers.active = obj.data.uv_layers["Second"]
    return [obj]


def f_multi_uv_render(root):
    """Active and render deliberately disagree, or render proves nothing."""
    obj = plane(
        "multi_uv_render", root, "multi_uv_render", uv_layers=("UVMap", "Second")
    )
    obj.data.uv_layers.active = obj.data.uv_layers["UVMap"]
    obj.data.uv_layers["Second"].active_render = True
    return [obj]


def f_no_uv(root):
    return [plane("no_uv", root, "no_uv", uv_layers=())]


def f_modifier(root):
    obj = plane("with_modifier", root, "with_modifier")
    modifier = obj.modifiers.new("subdivide", "SUBSURF")
    modifier.levels = 1
    modifier.render_levels = 1
    return [obj]


def f_hard_edge(root):
    """Smooth shading everywhere, one sharp edge: two normals at one vertex."""
    obj = two_faces("hard_edge", root, "hard_edge", lift=0.06)
    layer = obj.data.uv_layers[0]
    for loop_index, datum in enumerate(layer.data):
        datum.uv = (0.1 * loop_index, 0.05 * loop_index)
    obj.data.shade_smooth()
    for edge in obj.data.edges:
        pair = set(edge.vertices)
        if pair == {1, 2}:
            edge.use_edge_sharp = True
    obj.data.update()
    return [obj]


def f_non_planar_quad(root):
    obj = plane("non_planar", root, "non_planar")
    obj.data.vertices[2].co.y += 0.05
    obj.data.update()
    return [obj]


def fixtures():
    return [
        ("parent_transform", f_parent_transform, {}),
        ("non_uniform_scale", f_non_uniform_scale, {}),
        ("micro_rotation", f_micro_rotation, {}),
        ("vertex_reorder", f_vertex_reorder, {"shuffle_copy": True}),
        ("uv_seam", f_uv_seam, {"expect_seam": True}),
        ("multi_uv", f_multi_uv, {}),
        ("multi_uv_render", f_multi_uv_render, {}),
        ("no_uv", f_no_uv, {}),
        ("modifier", f_modifier, {}),
        ("hard_edge", f_hard_edge, {"expect_split_normals": True}),
        ("non_planar_quad", f_non_planar_quad, {"expect_non_planar": True}),
    ]


# --------------------------------------------------------------------------
# The export copy


def shuffle_mesh_order(mesh, seed=4242):
    """Renumber vertices and rotate loops without moving anything.

    The point of the reorder fixture is that source and export copy disagree
    on numbering, so a comparison that secretly relies on index order fails.
    """
    work = bmesh.new()
    work.from_mesh(mesh)
    work.verts.ensure_lookup_table()
    order = list(range(len(work.verts)))
    random.Random(seed).shuffle(order)
    for vertex, index in zip(work.verts, order):
        vertex.index = index
    work.verts.sort()
    work.to_mesh(mesh)
    work.free()
    mesh.update()


def export_copy(root, shuffle=False):
    """Duplicate the hierarchy, evaluated and explicitly triangulated.

    The copy keeps every intermediate empty and every local transform, so what
    is exported has the shape of the original and not a flattened version of
    it. `opus5_id` travels with each object; identity never depends on a name.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    holder = bpy.data.objects.new(f"{root.name}__export", None)
    bpy.context.collection.objects.link(holder)
    holder.matrix_world = root.matrix_world.copy()
    holder["opus5_id"] = root["opus5_id"]
    mapping = {root: holder}
    queue = list(root.children)
    while queue:
        obj = queue.pop(0)
        parent = mapping.get(obj.parent)
        if parent is None:
            queue.append(obj)
            continue
        if obj.type == "MESH":
            evaluated = obj.evaluated_get(depsgraph)
            mesh = bpy.data.meshes.new_from_object(
                evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
            )
            work = bmesh.new()
            work.from_mesh(mesh)
            # FIXED / EAR_CLIP, not the BEAUTY default: BEAUTY re-picks the
            # diagonal on its own criterion and on a square its tie-break
            # lands on the other one, so the exported surface stops being the
            # surface Blender displays. On a non-planar quad those are two
            # different surfaces, not two spellings of one.
            bmesh.ops.triangulate(
                work, faces=work.faces[:], quad_method="FIXED",
                ngon_method="EAR_CLIP",
            )
            work.to_mesh(mesh)
            work.free()
            mesh.update()
            if shuffle:
                shuffle_mesh_order(mesh)
            made = bpy.data.objects.new(f"{obj.name}__export", mesh)
        else:
            made = bpy.data.objects.new(f"{obj.name}__export", None)
        bpy.context.collection.objects.link(made)
        made.parent = parent
        made.matrix_parent_inverse = Matrix.Identity(4)
        made.matrix_local = obj.matrix_local.copy()
        made["opus5_id"] = obj["opus5_id"]
        mapping[obj] = made
        queue.extend(obj.children)
    bpy.context.view_layer.update()
    return holder


# --------------------------------------------------------------------------
# Measurement


def corner_normals(mesh):
    data = getattr(mesh, "corner_normals", None)
    if data is not None and len(data) == len(mesh.loops):
        return [Vector(item.vector) for item in data]
    return [Vector(loop.normal) for loop in mesh.loops]


def key_of(position):
    return tuple(round(value, KEY_DECIMALS) for value in position)


def triangle_area(corners):
    a, b, c = (Vector(corner) for corner in corners)
    return (b - a).cross(c - a).length / 2.0


def read_mesh(obj, root, mesh, matrix):
    normal_matrix = matrix.to_3x3().inverted_safe().transposed()
    mesh.calc_loop_triangles()
    try:
        mesh.calc_normals_split()
    except (AttributeError, RuntimeError):
        pass
    normals = corner_normals(mesh)
    positions = [list(matrix @ vertex.co) for vertex in mesh.vertices]

    def loop_payload(loop_index):
        loop = mesh.loops[loop_index]
        split = (normal_matrix @ normals[loop_index]).normalized()
        return {
            "position": positions[loop.vertex_index],
            "split_normal": [split.x, split.y, split.z],
            "uv": {
                layer.name: list(layer.data[loop_index].uv)
                for layer in mesh.uv_layers
            },
        }

    polygons = []
    for polygon in mesh.polygons:
        normal = (normal_matrix @ Vector(polygon.normal)).normalized()
        corners = [loop_payload(index) for index in polygon.loop_indices]
        polygons.append(
            {
                "corners": corners,
                "normal": [normal.x, normal.y, normal.z],
                "reported_area": polygon.area,
                "material": polygon.material_index,
                "loop_count": len(corners),
            }
        )
    triangles = []
    for triangle in mesh.loop_triangles:
        corners = [loop_payload(index) for index in triangle.loops]
        normal = (normal_matrix @ Vector(triangle.normal)).normalized()
        triangles.append(
            {
                "corners": corners,
                "face_normal": [normal.x, normal.y, normal.z],
                "material": triangle.material_index,
                "area": triangle_area([corner["position"] for corner in corners]),
            }
        )
    render = [layer.name for layer in mesh.uv_layers if layer.active_render]
    axes = list(zip(*positions)) if positions else [(), (), ()]
    return {
        "polygons": polygons,
        "triangles": triangles,
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "active_uv_layer": (
            mesh.uv_layers.active.name if mesh.uv_layers.active else None
        ),
        "render_uv_layer": render[0] if render else None,
        "vertex_order": positions,
        "loop_order": [loop.vertex_index for loop in mesh.loops],
        "bounds": {
            "min": [min(axis) for axis in axes] if positions else None,
            "max": [max(axis) for axis in axes] if positions else None,
        },
        "triangle_area_sum": sum(item["area"] for item in triangles),
        "root_relative_matrix": [list(row) for row in matrix],
    }


def read_object(obj, root, evaluated):
    matrix = root.matrix_world.inverted() @ obj.matrix_world
    if obj.type != "MESH":
        return {
            "type": obj.type,
            "root_relative_matrix": [list(row) for row in matrix],
            "local_matrix": [list(row) for row in obj.matrix_local],
        }
    if evaluated:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        target = obj.evaluated_get(depsgraph)
        mesh = target.to_mesh()
        payload = read_mesh(obj, root, mesh, matrix)
        target.to_mesh_clear()
    else:
        payload = read_mesh(obj, root, obj.data, matrix)
    payload["type"] = "MESH"
    payload["local_matrix"] = [list(row) for row in obj.matrix_local]
    return payload


def identity_of(obj):
    value = obj.get("opus5_id")
    return str(value) if value is not None else None


def read_scene(root, evaluated):
    """Keyed on the explicit identity, and it must be unique."""
    payload = {}
    for obj in [root] + list(root.children_recursive):
        identity = identity_of(obj)
        if identity is None:
            raise AssertionError(f"{obj.name}: no opus5_id")
        if identity in payload:
            raise AssertionError(f"duplicate opus5_id {identity!r}")
        entry = read_object(obj, root, evaluated)
        entry["parent"] = identity_of(obj.parent) if obj.parent else None
        payload[identity] = entry
    return payload


# --------------------------------------------------------------------------
# Gate 1: polygon surface -> normalized triangles


def make_snapper(tolerance=SNAP_TOLERANCE_M):
    """Identity of a point, to a stated tolerance rather than to the bit.

    The gate compares a mesh with a copy that arrived at the same world point
    through a different float32 matrix chain, so exact keys would split one
    vertex into two and report a boundary that never changed.
    """
    representatives = []

    def key(position):
        for index, rep in enumerate(representatives):
            if math.dist(rep, position) <= tolerance:
                return index
        representatives.append(tuple(position))
        return len(representatives) - 1

    return key, representatives


def edge_key(key, first, second):
    return tuple(sorted([key(first), key(second)]))


def internal_and_boundary(key, triangles):
    """Edges seen once bound the patch; edges seen twice are its diagonals."""
    counts = {}
    for corners in triangles:
        for index in range(3):
            pair = edge_key(key, corners[index], corners[(index + 1) % 3])
            counts[pair] = counts.get(pair, 0) + 1
    boundary = {pair for pair, count in counts.items() if count == 1}
    internal = {pair for pair, count in counts.items() if count > 1}
    return internal, boundary


def polygon_boundary(key, polygon):
    corners = [corner["position"] for corner in polygon["corners"]]
    return {
        edge_key(key, corners[index], corners[(index + 1) % len(corners)])
        for index in range(len(corners))
    }


def assign_to_polygons(key, polygons, triangles):
    """Every triangle belongs to exactly one source polygon."""
    membership = {}
    for index, polygon in enumerate(polygons):
        for corner in polygon["corners"]:
            membership.setdefault(key(corner["position"]), set()).add(index)
    assignment = []
    problems = []
    for position, triangle in enumerate(triangles):
        sets = [
            membership.get(key(corner["position"]), set())
            for corner in triangle["corners"]
        ]
        shared = set.intersection(*sets) if sets else set()
        if not shared:
            problems.append({"triangle": position, "reason": "no containing polygon"})
            assignment.append(None)
            continue
        if len(shared) > 1:
            # Two polygons sharing all three corners is not something these
            # meshes contain; if it ever happens the ambiguity is recorded
            # rather than silently resolved.
            oriented = [
                index
                for index in shared
                if dot(triangle["face_normal"], polygons[index]["normal"]) > 0.0
            ]
            if len(oriented) != 1:
                problems.append(
                    {"triangle": position, "reason": "ambiguous containment",
                     "candidates": sorted(shared)}
                )
                assignment.append(None)
                continue
            shared = set(oriented)
        assignment.append(next(iter(shared)))
    return assignment, problems


def dot(first, second):
    return sum(a * b for a, b in zip(first, second))


def polygon_surface_gate(source, normalized):
    """Boundary, diagonal, area, material, orientation and corner UV."""
    polygons = source["polygons"]
    triangles = normalized["triangles"]
    key, representatives = make_snapper()
    # Seed the snapper from the source polygons so the copy's points attach to
    # the source's representatives rather than the other way round.
    for polygon in polygons:
        for corner in polygon["corners"]:
            key(corner["position"])
    assignment, problems = assign_to_polygons(key, polygons, triangles)
    groups = {}
    for position, index in enumerate(assignment):
        if index is not None:
            groups.setdefault(index, []).append(position)

    source_internal = {}
    source_area = {}
    for index, polygon in enumerate(polygons):
        own_keys = {key(corner["position"]) for corner in polygon["corners"]}
        own = [
            item
            for item in source["triangles"]
            if {key(corner["position"]) for corner in item["corners"]} <= own_keys
        ]
        source_internal[index] = internal_and_boundary(
            key, [[corner["position"] for corner in item["corners"]] for item in own]
        )[0]
        source_area[index] = sum(item["area"] for item in own)

    findings = []
    diagonals = {}
    per_polygon_area = {}
    area_error = 0.0
    for index, polygon in enumerate(polygons):
        members = groups.get(index, [])
        expected = polygon["loop_count"] - 2
        if len(members) != expected:
            findings.append(
                {"polygon": index, "reason": "triangle count",
                 "expected": expected, "got": len(members)}
            )
            continue
        corners = [
            [corner["position"] for corner in triangles[position]["corners"]]
            for position in members
        ]
        internal, boundary = internal_and_boundary(key, corners)
        if boundary != polygon_boundary(key, polygon):
            findings.append({"polygon": index, "reason": "boundary changed"})
        if internal != source_internal[index]:
            findings.append(
                {"polygon": index, "reason": "diagonal differs from source display",
                 "source": named_edges(source_internal[index], representatives),
                 "normalized": named_edges(internal, representatives)}
            )
        if internal:
            diagonals[str(index)] = named_edges(internal, representatives)
        for position in members:
            triangle = triangles[position]
            if triangle["material"] != polygon["material"]:
                findings.append({"polygon": index, "reason": "material"})
            if dot(triangle["face_normal"], polygon["normal"]) <= 0.0:
                findings.append({"polygon": index, "reason": "orientation flipped"})
            for corner in triangle["corners"]:
                match = [
                    item
                    for item in polygon["corners"]
                    if key(item["position"]) == key(corner["position"])
                ]
                if not match:
                    findings.append({"polygon": index, "reason": "corner not on polygon"})
                    continue
                if not any(item["uv"] == corner["uv"] for item in match):
                    findings.append(
                        {"polygon": index, "reason": "corner uv",
                         "position": corner["position"]}
                    )
        # Per polygon, against the source's own display triangulation of that
        # same polygon. §175 compared the normalized triangles with a
        # recomputation of themselves, which no redistribution could fail; two
        # polygons drifting by equal and opposite amounts would have left the
        # total untouched and gone unreported.
        got = sum(triangles[position]["area"] for position in members)
        want = source_area.get(index, 0.0)
        gap = abs(got - want)
        area_error = max(area_error, gap)
        per_polygon_area[str(index)] = {
            "source": want, "normalized": got, "gap": gap
        }
        if gap > AREA_RELATIVE_BOUND * max(1.0, want):
            findings.append(
                {"polygon": index, "reason": "polygon area",
                 "source": want, "normalized": got, "gap": gap}
            )

    total_source = sum(item["area"] for item in source["triangles"])
    total_normalized = normalized["triangle_area_sum"]
    area_gap = abs(total_source - total_normalized)
    if area_gap > AREA_RELATIVE_BOUND * max(1.0, total_source):
        findings.append(
            {"polygon": None, "reason": "total surface area",
             "source": total_source, "normalized": total_normalized}
        )
    bounds_gap = None
    if source["bounds"]["min"] and normalized["bounds"]["min"]:
        bounds_gap = max(
            abs(a - b)
            for side in ("min", "max")
            for a, b in zip(source["bounds"][side], normalized["bounds"][side])
        )
        if bounds_gap > BOUNDS_BOUND_M:
            findings.append({"polygon": None, "reason": "bounds", "gap": bounds_gap})
    if source["uv_layers"] != normalized["uv_layers"]:
        findings.append({"polygon": None, "reason": "uv layer set changed"})
    return {
        "polygons": len(polygons),
        "triangles": len(triangles),
        "unassigned_triangles": sum(1 for item in assignment if item is None),
        "assignment_problems": problems,
        "surface_area_source": total_source,
        "surface_area_normalized": total_normalized,
        "surface_area_gap": area_gap,
        "reported_area_sum": sum(item["reported_area"] for item in polygons),
        "bounds_gap_m": bounds_gap,
        "internal_diagonals": diagonals,
        "per_polygon_area": per_polygon_area,
        "worst_polygon_area_gap": area_error,
        "findings": findings,
        "pass": not findings and not problems,
    }


def named_edges(edges, representatives):
    """Edge keys resolved back to coordinates, so a finding can be read."""
    return sorted(
        [list(representatives[first]), list(representatives[second])]
        for first, second in edges
    )


# --------------------------------------------------------------------------
# Gate 2-5: normalized -> reimport, one measurement kind at a time


def quantize(error):
    return int(round(error * ERROR_SCALE))


def kind_evidence(positions, face, splits):
    """One vector per kind, never one number for all three.

    §177 summed position, face normal and split normal into a single `over`
    and a single `error`, so a solution that traded position error against
    normal error looked identical to one that did not. Alignment 178 is right
    that this cannot answer "is each kind's evidence invariant".
    """
    position_error = sum(value / POSITION_BOUND_M for value in positions)
    face_error = face / NORMAL_BOUND_DEG
    split_error = sum(value / NORMAL_BOUND_DEG for value in splits)
    over = (
        sum(1 for value in positions if value > POSITION_BOUND_M),
        1 if face > NORMAL_BOUND_DEG else 0,
        sum(1 for value in splits if value > NORMAL_BOUND_DEG),
    )
    return {
        "over": over,
        "scaled": (
            quantize(position_error), quantize(face_error), quantize(split_error)
        ),
        "category": over + (
            quantize(position_error), quantize(face_error), quantize(split_error)
        ),
        "aggregate_over": sum(over),
        "aggregate_error": position_error + face_error + split_error,
    }


ALL_KINDS = ("position", "face_normal", "split_normal")


def pair_evidence(first, second, kinds=ALL_KINDS):
    """The cheapest corner permutation - and whether "the" is warranted.

    `kinds` names what the data actually carries. A kind that was never
    recorded contributes nothing to the cost and keeps its zero slot in the
    category vector; it is the caller's job to report it as unmeasured rather
    than as zero.

    Permutations are ranked on the quantized primary key the solver actually
    uses, because a difference below one quantum is not one the solver can
    see. If several permutations reach that key carrying different
    kind-separated evidence, the pair's evidence is not determined and that is
    reported as edge-internal ambiguity rather than resolved by argument order.
    """
    candidates = []
    for permutation in itertools.permutations(range(3)):
        positions = [
            math.dist(
                first["corners"][index]["position"],
                second["corners"][mapped]["position"],
            )
            for index, mapped in enumerate(permutation)
        ]
        if max(positions) > CORNER_TOLERANCE_M:
            continue
        face = (
            angle_between(first["face_normal"], second["face_normal"])
            if "face_normal" in kinds
            else 0.0
        )
        splits = (
            [
                angle_between(
                    first["corners"][index]["split_normal"],
                    second["corners"][mapped]["split_normal"],
                )
                for index, mapped in enumerate(permutation)
            ]
            if "split_normal" in kinds
            else [0.0, 0.0, 0.0]
        )
        evidence = kind_evidence(positions, face, splits)
        candidates.append(
            {
                "permutation": permutation,
                "positions": positions,
                "face": face,
                "splits": splits,
                "over": evidence["aggregate_over"],
                "error": evidence["aggregate_error"],
                "evidence": evidence,
                "primary": (
                    evidence["aggregate_over"], quantize(evidence["aggregate_error"])
                ),
            }
        )
    if not candidates:
        return None
    best_key = min(item["primary"] for item in candidates)
    at_optimum = [item for item in candidates if item["primary"] == best_key]
    categories = sorted({item["evidence"]["category"] for item in at_optimum})
    best = at_optimum[0]
    best["optimal_permutations"] = len(at_optimum)
    best["edge_categories"] = [list(category) for category in categories]
    best["edge_ambiguous"] = len(categories) > 1
    return best


def kind_separated_ambiguity(sources, targets, costs, category_of, objective):
    """A5's min / max count question, asked per kind-separated category.

    The primary objective and its tie-break multiplier are A5's, unchanged -
    only the category the counts are taken over is finer.
    """
    categories = sorted({category_of(pair) for pair in costs})
    findings = []
    solves = 0

    def count(pairs, category):
        return sum(1 for pair in pairs if category_of(pair) == category)

    for category in categories:
        def inside(pair, category=category):
            return category_of(pair) == category

        low_pairs, low_objective, _ = solve_with(
            sources, targets, costs, lambda pair: 1 if inside(pair) else 0
        )
        high_pairs, high_objective, _ = solve_with(
            sources, targets, costs, lambda pair: 0 if inside(pair) else 1
        )
        solves += 2
        if low_objective != objective or high_objective != objective:
            findings.append(
                {
                    "category": list(category),
                    "reason": "tie-break changed the canonical objective",
                    "low_objective": list(low_objective),
                    "high_objective": list(high_objective),
                }
            )
            continue
        low = count(low_pairs, category)
        high = count(high_pairs, category)
        if low != high:
            findings.append(
                {"category": list(category), "min_count": low, "max_count": high}
            )
    return findings, {"categories": len(categories), "solves": solves}


def centroid_buckets(triangles, size):
    index = {}
    for position, triangle in enumerate(triangles):
        centre = tuple(
            sum(corner["position"][axis] for corner in triangle["corners"]) / 3.0
            for axis in range(3)
        )
        key = tuple(int(math.floor(value / size)) for value in centre)
        index.setdefault(key, []).append(position)
    return index


def candidate_pairs(source, reimport):
    """Only pairs whose centroids are near enough to be matchable.

    Every pair the full double loop would have kept is kept: a corner may move
    by at most the match tolerance, so a centroid may move by at most the same,
    and one bucket of that size plus its 26 neighbours covers it. Small meshes
    are unaffected; a 900-triangle mesh is the difference between seconds and
    an hour.
    """
    index = centroid_buckets(reimport, CORNER_TOLERANCE_M)
    for i, triangle in enumerate(source):
        centre = tuple(
            sum(corner["position"][axis] for corner in triangle["corners"]) / 3.0
            for axis in range(3)
        )
        key = tuple(int(math.floor(value / CORNER_TOLERANCE_M)) for value in centre)
        found = set()
        for offsets in itertools.product((-1, 0, 1), repeat=3):
            shifted = tuple(value + delta for value, delta in zip(key, offsets))
            found.update(index.get(shifted, []))
        for j in sorted(found):
            yield i, j


def geometry_assignment(
    source, reimport, bucketed=False, kinds=ALL_KINDS, ambiguity_budget=None
):
    """A5's objective, then three ambiguity questions instead of one.

    aggregate  - could another optimum carry a different aggregate evidence
                 multiset? (what §177 asked)
    per kind   - could another optimum carry a different count of any
                 kind-separated category? (what §178.1.1 asks)
    per edge   - is any single pair's own evidence undetermined because two
                 corner permutations tie? (§178.1.2)
    """
    costs = {}
    detail = {}
    considered = (
        candidate_pairs(source, reimport)
        if bucketed
        else itertools.product(range(len(source)), range(len(reimport)))
    )
    for i, j in considered:
        first, second = source[i], reimport[j]
        if first["material"] != second["material"]:
            continue
        found = pair_evidence(first, second, kinds)
        if found is None:
            continue
        costs[(i, j)] = {"over": found["over"], "error": found["error"]}
        detail[(i, j)] = found
    pairs = []
    aggregate = []
    per_kind = []
    categories = 0
    solves = 0
    skipped = []
    for part in components(len(source), len(reimport), costs):
        local = {
            pair: value
            for pair, value in costs.items()
            if pair[0] in part["sources"] and pair[1] in part["targets"]
        }
        solved = solve_component(part["sources"], part["targets"], local)
        pairs.extend(solved["pairs"])
        if ambiguity_budget is not None and len(part["sources"]) > ambiguity_budget:
            # Not skipped quietly: the caller reports this component's
            # ambiguity as unevaluated, which is neither a pass nor a fail.
            skipped.append(
                {"sources": len(part["sources"]), "targets": len(part["targets"])}
            )
            continue
        findings, stats = evidence_ambiguity(
            part["sources"], part["targets"], local, solved
        )
        aggregate.extend(findings)
        if solved["pairs"]:
            kind_findings, kind_stats = kind_separated_ambiguity(
                part["sources"],
                part["targets"],
                local,
                lambda pair: detail[pair]["evidence"]["category"],
                solved["objective"],
            )
            per_kind.extend(kind_findings)
            categories += kind_stats["categories"]
            solves += stats["solves"] + kind_stats["solves"]
    edge = [
        {
            "pair": list(pair),
            "optimal_permutations": detail[pair]["optimal_permutations"],
            "categories": detail[pair]["edge_categories"],
        }
        for pair in sorted(detail)
        if detail[pair]["edge_ambiguous"]
    ]
    return {
        "pairs": sorted(pairs),
        "detail": detail,
        "measured_kinds": list(kinds),
        "ambiguity_evaluated": not skipped,
        "ambiguity_components_skipped": skipped,
        "aggregate_ambiguous": aggregate,
        "kind_separated_ambiguous": per_kind,
        "edge_ambiguous": edge,
        "kind_categories": categories,
        "ambiguity_solves": solves,
        "aggregate_evidence_multiset": sorted(
            (costs[pair]["over"], quantize(costs[pair]["error"])) for pair in pairs
        ),
        "kind_evidence_multiset": sorted(
            list(detail[pair]["evidence"]["category"]) for pair in pairs
        ),
        "kind_evidence_multiset_by_kind": {
            name: sorted(
                [
                    detail[pair]["evidence"]["over"][index],
                    detail[pair]["evidence"]["scaled"][index],
                ]
                for pair in pairs
            )
            for index, name in enumerate(("position", "face_normal", "split_normal"))
        },
    }


def as_uv_mesh(payload, layer):
    return [
        (
            tuple(
                (
                    tuple(corner["position"]),
                    tuple(corner["uv"][layer]) if layer else (0.0, 0.0),
                )
                for corner in triangle["corners"]
            ),
            triangle["material"],
        )
        for triangle in payload["triangles"]
    ]


def scalar_measurement(expected, values):
    """The whole multiset; max and RMS are derived from it, not instead of it.

    Two different error sequences can share a max and an RMS, so §175's
    `[max, RMS]` could not have detected a redistribution. What is stored and
    compared is every scalar. A number nobody measured is `null`, not zero.
    """
    matched = len(values)
    coverage = matched / expected if expected else 0.0
    valid = expected > 0 and matched == expected
    return {
        "expected": expected,
        "matched": matched,
        "coverage": coverage,
        "scalar_count": matched,
        "measurement_valid": valid,
        "multiset": sorted(round(value, 12) for value in values) if valid else None,
        "max": max(values) if valid and values else None,
        "rms": (
            math.sqrt(sum(value * value for value in values) / matched)
            if valid and matched
            else None
        ),
    }


def cross(first, second):
    return [
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    ]


def angle_between(first, second):
    """atan2 of the cross and the dot, not acos of the dot.

    `acos` is where small angles go to die: a vector's dot with itself lands a
    few ulp below 1.0 whenever its components are not exactly normalised, and
    `acos` turns an error of 1e-8 into an angle of 0.008 degrees. Every split
    normal figure §175 and §177 reported for identical vectors was that
    residue. The cross-product form is exact at zero - identical inputs give a
    cross of exactly zero - and stable everywhere else, and it needs no unit
    length to be correct.
    """
    return math.degrees(
        math.atan2(math.dist(cross(first, second), (0.0, 0.0, 0.0)),
                   dot(first, second))
    )


def kind_measurements(
    source, reimport, bucketed=False, kinds=ALL_KINDS, ambiguity_budget=None
):
    solved = geometry_assignment(
        source["triangles"],
        reimport["triangles"],
        bucketed=bucketed,
        kinds=kinds,
        ambiguity_budget=ambiguity_budget,
    )
    expected_tri = len(source["triangles"])
    positions = []
    faces = []
    splits = []
    for pair in solved["pairs"]:
        found = solved["detail"][pair]
        positions.extend(found["positions"])
        faces.append(found["face"])
        splits.extend(found["splits"])
    kinds = {
        "geometry": scalar_measurement(expected_tri * 3, positions),
        "face_normal": scalar_measurement(expected_tri, faces),
        "split_normal": scalar_measurement(expected_tri * 3, splits),
    }
    kinds["geometry"]["bound"] = POSITION_BOUND_M
    kinds["geometry"]["unit"] = "m"
    kinds["face_normal"]["bound"] = NORMAL_BOUND_DEG
    kinds["face_normal"]["unit"] = "deg"
    kinds["split_normal"]["bound"] = NORMAL_BOUND_DEG
    kinds["split_normal"]["unit"] = "deg"
    for kind in kinds.values():
        kind["pass"] = bool(
            kind["measurement_valid"]
            and kind["max"] is not None
            and kind["max"] <= kind["bound"]
        )
    assignment = {
        "expected_triangles": expected_tri,
        "matched_triangles": len(solved["pairs"]),
        "unmatched_source": expected_tri - len(solved["pairs"]),
        "unconsumed_reimport": len(reimport["triangles"]) - len(solved["pairs"]),
        "primary_objective": {
            "order": "cardinality, aggregate bound excess, aggregate quantized error",
            "aggregate_evidence_multiset": solved["aggregate_evidence_multiset"],
        },
        "kind_separated_evidence": {
            "vector": (
                "position_over, face_over, split_over, position_scaled, "
                "face_scaled, split_scaled"
            ),
            "categories": solved["kind_categories"],
            "multiset": solved["kind_evidence_multiset"],
            "by_kind": solved["kind_evidence_multiset_by_kind"],
        },
        "ambiguity_solves": solved["ambiguity_solves"],
        "measured_kinds": solved["measured_kinds"],
        "ambiguity_evaluated": solved["ambiguity_evaluated"],
        "ambiguity_components_skipped": solved["ambiguity_components_skipped"],
        "aggregate_ambiguous": solved["aggregate_ambiguous"],
        "kind_separated_ambiguous": solved["kind_separated_ambiguous"],
        "edge_ambiguous": solved["edge_ambiguous"],
        "pass": bool(
            solved["ambiguity_evaluated"]
            and not solved["aggregate_ambiguous"]
            and not solved["kind_separated_ambiguous"]
            and not solved["edge_ambiguous"]
            and len(solved["pairs"]) == expected_tri
            and len(reimport["triangles"]) == len(solved["pairs"])
        ),
    }
    uv = {}
    for layer in source["uv_layers"]:
        if layer not in reimport["uv_layers"]:
            uv[layer] = {"status": "layer_missing_after_reimport", "pass": False}
            continue
        result = compare_uv_mesh(
            as_uv_mesh(source, layer), as_uv_mesh(reimport, layer)
        )
        result["measurement_valid"] = (
            result.get("triangle_coverage") == 1.0
            and result.get("matched_triangles", 0) > 0
        )
        result["bound_ulp"] = 1.0
        if not result["measurement_valid"]:
            result["error_multiset"] = None
            result["over_bound"] = None
        uv[layer] = result
    return assignment, kinds, uv


# --------------------------------------------------------------------------
# Gate: shuffle invariance


def shuffled(payload, seed):
    rng = random.Random(seed)
    out = copy_module.deepcopy(payload)
    for triangle in out["triangles"]:
        turn = rng.randrange(3)
        triangle["corners"] = triangle["corners"][turn:] + triangle["corners"][:turn]
    rng.shuffle(out["triangles"])
    return out


def invariant_signature(source, reimport):
    assignment, kinds, uv = kind_measurements(source, reimport)
    matched = assignment["matched_triangles"]
    return {
        "pairs": matched,
        "coverage": round(matched / max(len(source["triangles"]), 1), 12),
        "unmatched_source": assignment["unmatched_source"],
        "unconsumed_reimport": assignment["unconsumed_reimport"],
        "ambiguity": {
            "aggregate": assignment["aggregate_ambiguous"],
            "kind_separated": assignment["kind_separated_ambiguous"],
            "edge": assignment["edge_ambiguous"],
        },
        "aggregate_evidence_multiset": (
            assignment["primary_objective"]["aggregate_evidence_multiset"]
        ),
        "kind_evidence_multiset": assignment["kind_separated_evidence"]["multiset"],
        "kind_evidence_by_kind": assignment["kind_separated_evidence"]["by_kind"],
        "error_multiset": {
            name: kind["multiset"] for name, kind in kinds.items()
        },
        "uv": {
            name: {
                "coverage": result.get("triangle_coverage"),
                "over_bound": result.get("over_bound"),
                "error_multiset": (
                    [round(value, 9) for value in result["error_multiset"]]
                    if result.get("error_multiset")
                    else result.get("error_multiset")
                ),
                "ambiguous": bool(result.get("ambiguous")),
            }
            for name, result in uv.items()
        },
    }


def shuffle_invariance(source, reimport):
    base = invariant_signature(source, reimport)
    findings = []
    for seed in SHUFFLE_SEEDS:
        again = invariant_signature(shuffled(source, seed), shuffled(reimport, seed + 1))
        if again != base:
            findings.append({"seed": seed, "signature": again})
    return {
        "seeds": list(SHUFFLE_SEEDS),
        "baseline": base,
        "findings": findings,
        "pass": not findings,
    }


# --------------------------------------------------------------------------
# Gate: the fixture must exercise what it claims


def split_normal_multiset(payload):
    """Distinct split normals per position - the hard edge's whole premise."""
    groups = {}
    for triangle in payload["triangles"]:
        for corner in triangle["corners"]:
            groups.setdefault(key_of(corner["position"]), set()).add(
                tuple(round(value, 6) for value in corner["split_normal"])
            )
    return {key: sorted(value) for key, value in groups.items()}


def uv_multiset(payload, layer):
    groups = {}
    for triangle in payload["triangles"]:
        for corner in triangle["corners"]:
            groups.setdefault(key_of(corner["position"]), set()).add(
                tuple(round(value, 9) for value in corner["uv"][layer])
            )
    return {key: sorted(value) for key, value in groups.items()}


def premise_gate(name, options, raw, normalized, reimport):
    findings = []
    detail = {}
    if options.get("shuffle_copy"):
        detail["source_loop_order"] = raw["loop_order"]
        detail["normalized_loop_order"] = normalized["loop_order"]
        detail["order_differs"] = (
            raw["loop_order"] != normalized["loop_order"]
            or raw["vertex_order"] != normalized["vertex_order"]
        )
        if not detail["order_differs"]:
            findings.append("source and export copy share their vertex/loop order")
    if options.get("expect_seam"):
        layer = normalized["uv_layers"][0]
        groups = uv_multiset(normalized, layer)
        split = {k: v for k, v in groups.items() if len(v) > 1}
        detail["seam_positions"] = len(split)
        detail["seam_layer"] = layer
        if not split:
            findings.append("no shared vertex carries two UVs; this is not a seam")
        else:
            after = uv_multiset(reimport, layer) if reimport else {}
            kept = {k: v for k, v in after.items() if len(v) > 1}
            detail["seam_positions_after_reimport"] = len(kept)
            detail["seam_multiset_preserved"] = (
                sorted(len(v) for v in split.values())
                == sorted(len(v) for v in kept.values())
            )
            if not detail["seam_multiset_preserved"]:
                findings.append("seam split count changed across the round trip")
    if options.get("expect_split_normals"):
        groups = split_normal_multiset(normalized)
        multi = {k: v for k, v in groups.items() if len(v) > 1}
        detail["positions_with_multiple_split_normals"] = len(multi)
        detail["split_normal_counts"] = sorted(len(v) for v in groups.values())
        if not multi:
            findings.append(
                "no position carries two split normals; the hard edge is not observable"
            )
        else:
            after = split_normal_multiset(reimport) if reimport else {}
            detail["split_normal_counts_after_reimport"] = sorted(
                len(v) for v in after.values()
            )
            if detail["split_normal_counts"] != detail["split_normal_counts_after_reimport"]:
                findings.append("split normal multiset changed across the round trip")
    if options.get("expect_non_planar"):
        polygon = raw["polygons"][0]
        corners = [Vector(corner["position"]) for corner in polygon["corners"]]
        normal = Vector(polygon["normal"])
        offset = -normal.dot(corners[0])
        deviation = max(abs(normal.dot(corner) + offset) for corner in corners)
        detail["planarity_deviation_m"] = deviation
        if deviation <= 1.0e-9:
            findings.append("the quad is planar; it tests nothing about a diagonal")
    return {"detail": detail, "findings": findings, "pass": not findings}


# --------------------------------------------------------------------------
# Negative controls


def move_corner(payload, delta):
    out = copy_module.deepcopy(payload)
    out["triangles"][0]["corners"][0]["position"][1] += delta
    return out


def shift_uv(payload, layer, ulps):
    out = copy_module.deepcopy(payload)
    unit = 2.0 * (2.0 ** -23)
    for triangle in out["triangles"][:1]:
        value = triangle["corners"][0]["uv"][layer]
        value[0] += ulps * unit * max(1.0, abs(value[0]))
    return out


def drop_triangle(payload):
    out = copy_module.deepcopy(payload)
    out["triangles"] = out["triangles"][:-1]
    return out


def flip_normals(payload):
    out = copy_module.deepcopy(payload)
    for triangle in out["triangles"]:
        triangle["face_normal"] = [-value for value in triangle["face_normal"]]
    return out


def swap_diagonal(payload, source):
    """Re-triangulate the source quad on the other diagonal.

    The quad lives in the source snapshot; the normalized snapshot's polygons
    are already triangles, so the corners have to come from the source or this
    control silently changes nothing.
    """
    out = copy_module.deepcopy(payload)
    polygon = copy_module.deepcopy(source["polygons"][0])
    corners = polygon["corners"]
    if len(corners) != 4:
        raise AssertionError("the diagonal control needs a quad to re-split")
    out["triangles"] = [
        {
            "corners": [corners[1], corners[2], corners[3]],
            "face_normal": polygon["normal"],
            "material": polygon["material"],
            "area": triangle_area(
                [corners[index]["position"] for index in (1, 2, 3)]
            ),
        },
        {
            "corners": [corners[1], corners[3], corners[0]],
            "face_normal": polygon["normal"],
            "material": polygon["material"],
            "area": triangle_area(
                [corners[index]["position"] for index in (1, 3, 0)]
            ),
        },
    ]
    out["triangle_area_sum"] = sum(item["area"] for item in out["triangles"])
    return out


def rename_layer(payload, old, new):
    out = copy_module.deepcopy(payload)
    out["uv_layers"] = [new if name == old else name for name in out["uv_layers"]]
    for group in ("triangles", "polygons"):
        for item in out.get(group, []):
            for corner in item["corners"]:
                if old in corner["uv"]:
                    corner["uv"][new] = corner["uv"].pop(old)
    return out


def rotated(vector, degrees):
    angle = math.radians(degrees)
    return [
        vector[0],
        vector[1] * math.cos(angle) - vector[2] * math.sin(angle),
        vector[1] * math.sin(angle) + vector[2] * math.cos(angle),
    ]


def angle_for_scaled(target, weight, bound):
    """Find the angle whose quantized contribution is exactly `target`.

    An angle comes out of `acos`, so no decimal choice makes a normal error
    match a position error exactly. What the solver compares is the quantized
    integer, not the float, so the search is for the angle that lands on that
    integer - and if it does not land exactly, the control says so instead of
    passing on an approximation.
    """
    reference = [0.0, 1.0, 0.0]

    def scaled_of(degrees):
        return quantize(
            weight * angle_between(reference, rotated(reference, degrees)) / bound
        )

    low, high = 0.0, 1.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if scaled_of(middle) < target:
            low = middle
        else:
            high = middle
    for candidate in (high, low, (low + high) / 2.0):
        if scaled_of(candidate) == target:
            return candidate, True
    return high, False


def synthetic_triangle(positions, face_normal, split_normals, material=0):
    corners = [
        {"position": list(position), "split_normal": list(normal), "uv": {}}
        for position, normal in zip(positions, split_normals)
    ]
    return {
        "corners": corners,
        "face_normal": list(face_normal),
        "material": material,
        "area": triangle_area([corner["position"] for corner in corners]),
    }


def synthetic_mesh(triangles):
    return {"triangles": triangles, "uv_layers": [], "polygons": []}


def normal_trade_case(degrees):
    """Two optima with the same aggregate evidence but different kinds.

    Every triangle sits on the same corners, so no position error exists
    anywhere. One diagonal of the matching pays its cost entirely in face
    normal, the other entirely in split normal, and the same angle is used for
    both - so the aggregate error is bit-identical and only a kind-separated
    category can tell the two optima apart. This is the case §177's single
    aggregate category could not have detected.
    """
    base = [(0.0, 0.0, 0.0), (0.05, 0.0, 0.0), (0.0, 0.0, 0.05)]
    straight = [0.0, 1.0, 0.0]
    turned = rotated(straight, degrees)
    return (
        synthetic_mesh(
            [
                synthetic_triangle(base, straight, [straight] * 3),
                synthetic_triangle(base, turned, [turned, straight, straight]),
            ]
        ),
        synthetic_mesh(
            [
                synthetic_triangle(base, turned, [straight] * 3),
                synthetic_triangle(base, straight, [turned, straight, straight]),
            ]
        ),
    )


def permutation_trade_case(step):
    """One pair, two corner permutations, same primary cost, different kinds.

    The first two corners are a hair apart and their split normals are swapped
    with them, so pairing corner to corner costs position error while swapping
    them costs split normal error. The angle is searched for so the two land
    on the same quantized cost; the caller checks that it did.
    """
    near = [(0.0, 0.0, 0.0), (0.0, step, 0.0), (0.05, 0.0, 0.0)]
    straight = [0.0, 1.0, 0.0]
    target = quantize(2.0 * step / POSITION_BOUND_M)
    degrees, exact = angle_for_scaled(target, 2.0, NORMAL_BOUND_DEG)
    turned = rotated(straight, degrees)
    source = synthetic_mesh(
        [synthetic_triangle(near, straight, [straight, turned, straight])]
    )
    swapped = [near[1], near[0], near[2]]
    reimport = synthetic_mesh(
        [synthetic_triangle(swapped, straight, [straight, turned, straight])]
    )
    return source, reimport, exact, target, degrees


def synthetic_normal_case(offsets):
    """Two triangles whose only difference is a shift along one axis.

    Built at these sizes so every distance is an exact float: with the shift
    at a quarter of the position bound, the four pair costs are 0, d, d and
    2d, which gives two matchings of identical total cost carrying different
    evidence. That is the situation an ambiguity test exists for.
    """
    base = [(0.0, 0.0, 0.0), (0.05, 0.0, 0.0), (0.0, 0.0, 0.05)]
    normal = [0.0, 1.0, 0.0]
    triangles = []
    for offset in offsets:
        corners = [
            {
                "position": [x, y + offset, z],
                "split_normal": list(normal),
                "uv": {},
            }
            for x, y, z in base
        ]
        triangles.append(
            {
                "corners": corners,
                "face_normal": list(normal),
                "material": 0,
                "area": triangle_area([corner["position"] for corner in corners]),
            }
        )
    return {"triangles": triangles, "uv_layers": [], "polygons": []}


def perturb_transform(scene, delta):
    out = copy_module.deepcopy(scene)
    identity = sorted(out)[-1]
    out[identity]["local_matrix"][0][3] += delta
    out[identity]["root_relative_matrix"][0][3] += delta
    return out


def cancelling_areas(payload, delta):
    """Two polygons off by equal and opposite amounts; the total is untouched.

    The stored areas are what moves, not the corners, so containment, boundary
    and diagonal all still hold and the only gate that can catch this is the
    per-polygon comparison.
    """
    out = copy_module.deepcopy(payload)
    out["triangles"][0]["area"] += delta
    out["triangles"][-1]["area"] -= delta
    return out


def negative_controls(cases, scenes):
    """Each gate must be shown to fail on data built to fail it."""
    plain = cases["non_uniform_scale"]
    quad_case = cases["non_planar_quad"]
    results = {}

    normalized = plain["normalized"]
    reimport = plain["reimport"]

    moved = move_corner(reimport, 1.0e-3)
    _, kinds, _ = kind_measurements(normalized, moved)
    results["geometry_moved_1mm"] = {
        "gate": "geometry",
        "expected": "fail",
        "measurement": kinds["geometry"],
        "pass": not kinds["geometry"]["pass"],
    }

    # 20 um is over the 10 um bound but well under the 100 um match
    # tolerance, so the pair still matches and it is the bound that fails -
    # otherwise this control would only be re-testing coverage collapse.
    nudged_geometry = move_corner(reimport, 2.0e-5)
    _, kinds, _ = kind_measurements(normalized, nudged_geometry)
    results["geometry_moved_20um_still_matched"] = {
        "gate": "geometry",
        "expected": "fail on the bound, at full coverage",
        "measurement": kinds["geometry"],
        "pass": (
            not kinds["geometry"]["pass"]
            and kinds["geometry"]["measurement_valid"] is True
            and kinds["geometry"]["coverage"] == 1.0
            and kinds["geometry"]["max"] is not None
            and kinds["geometry"]["max"] > POSITION_BOUND_M
        ),
    }

    dropped = drop_triangle(reimport)
    _, kinds, _ = kind_measurements(normalized, dropped)
    results["coverage_triangle_dropped"] = {
        "gate": "validity",
        "expected": "fail with null numbers",
        "measurement": kinds["geometry"],
        "pass": (
            not kinds["geometry"]["pass"]
            and kinds["geometry"]["measurement_valid"] is False
            and kinds["geometry"]["max"] is None
            and kinds["geometry"]["rms"] is None
        ),
    }

    flipped = flip_normals(reimport)
    _, kinds, _ = kind_measurements(normalized, flipped)
    results["face_normal_flipped"] = {
        "gate": "face_normal",
        "expected": "fail",
        "measurement": kinds["face_normal"],
        "pass": not kinds["face_normal"]["pass"],
    }

    layer = normalized["uv_layers"][0]
    nudged = shift_uv(reimport, layer, 4.0)
    _, _, uv = kind_measurements(normalized, nudged)
    results["uv_shifted_4_ulp"] = {
        "gate": "uv",
        "expected": "fail",
        "measurement": {
            "over_bound": uv[layer].get("over_bound"),
            "pass": uv[layer].get("pass"),
        },
        "pass": not uv[layer].get("pass"),
    }

    renamed = rename_layer(reimport, layer, "Renamed")
    _, _, uv = kind_measurements(normalized, renamed)
    results["uv_layer_renamed"] = {
        "gate": "uv_layer_names",
        "expected": "fail",
        "measurement": {"status": uv[layer].get("status")},
        "pass": not uv[layer].get("pass"),
    }

    swapped = swap_diagonal(quad_case["normalized"], quad_case["evaluated"])
    gate = polygon_surface_gate(quad_case["evaluated"], swapped)
    results["diagonal_swapped"] = {
        "gate": "polygon_surface",
        "expected": "fail",
        "measurement": {"findings": gate["findings"][:2]},
        "pass": not gate["pass"],
    }

    moved_surface = move_corner(plain["normalized"], 5.0e-3)
    gate = polygon_surface_gate(plain["evaluated"], moved_surface)
    results["polygon_surface_corner_moved"] = {
        "gate": "polygon_surface",
        "expected": "fail",
        "measurement": {"findings": gate["findings"][:2],
                        "problems": gate["assignment_problems"][:2]},
        "pass": not gate["pass"],
    }

    step = POSITION_BOUND_M / 4.0
    ambiguous_case = synthetic_normal_case([0.0, step])
    against = synthetic_normal_case([0.0, -step])
    assignment, _, _ = kind_measurements(ambiguous_case, against)
    results["position_ambiguity_detected"] = {
        "gate": "assignment_ambiguity",
        "expected": "two equal-cost matchings whose position evidence differs",
        "note": (
            "every triangle carries the same normals here; only position "
            "moves, so this control is named for what it actually varies"
        ),
        "measurement": {
            "aggregate_evidence_multiset": (
                assignment["primary_objective"]["aggregate_evidence_multiset"]
            ),
            "kind_evidence_multiset": (
                assignment["kind_separated_evidence"]["multiset"]
            ),
            "aggregate_ambiguous": assignment["aggregate_ambiguous"],
            "kind_separated_ambiguous": assignment["kind_separated_ambiguous"],
        },
        "pass": (
            bool(assignment["aggregate_ambiguous"])
            and bool(assignment["kind_separated_ambiguous"])
            and not assignment["pass"]
        ),
    }

    traded_source, traded_reimport = normal_trade_case(0.2)
    assignment, _, _ = kind_measurements(traded_source, traded_reimport)
    results["normal_kind_ambiguity_detected"] = {
        "gate": "assignment_ambiguity_kind_separated",
        "expected": (
            "identical aggregate evidence, different face / split evidence: "
            "only the kind-separated category can see it"
        ),
        "measurement": {
            "aggregate_evidence_multiset": (
                assignment["primary_objective"]["aggregate_evidence_multiset"]
            ),
            "kind_evidence_multiset": (
                assignment["kind_separated_evidence"]["multiset"]
            ),
            "by_kind": assignment["kind_separated_evidence"]["by_kind"],
            "aggregate_ambiguous": assignment["aggregate_ambiguous"],
            "kind_separated_ambiguous": assignment["kind_separated_ambiguous"],
        },
        "pass": (
            not assignment["aggregate_ambiguous"]
            and bool(assignment["kind_separated_ambiguous"])
            and not assignment["pass"]
        ),
    }

    edge_source, edge_reimport, exact, target, degrees = permutation_trade_case(
        POSITION_BOUND_M / 4.0
    )
    assignment, _, _ = kind_measurements(edge_source, edge_reimport)
    results["edge_permutation_ambiguity_detected"] = {
        "gate": "assignment_ambiguity_within_pair",
        "expected": "one pair, two tied permutations, different kind evidence",
        "measurement": {
            "search_hit_the_quantum_exactly": exact,
            "target_scaled": target,
            "angle_deg": degrees,
            "edge_ambiguous": assignment["edge_ambiguous"],
        },
        "pass": exact and bool(assignment["edge_ambiguous"]) and not assignment["pass"],
    }

    same = synthetic_normal_case([0.0, 0.0])
    assignment, _, _ = kind_measurements(same, synthetic_normal_case([0.0, 0.0]))
    results["ambiguity_equivalent_optima_pass"] = {
        "gate": "assignment_ambiguity",
        "expected": "several matchings, identical evidence in every kind",
        "measurement": {
            "kind_evidence_multiset": (
                assignment["kind_separated_evidence"]["multiset"]
            ),
            "aggregate_ambiguous": assignment["aggregate_ambiguous"],
            "kind_separated_ambiguous": assignment["kind_separated_ambiguous"],
            "edge_ambiguous": assignment["edge_ambiguous"],
        },
        "pass": (
            not assignment["aggregate_ambiguous"]
            and not assignment["kind_separated_ambiguous"]
            and not assignment["edge_ambiguous"]
            and assignment["pass"]
        ),
    }

    scene = scenes["parent_transform"]
    changed = transform_measurement(scene, perturb_transform(scene, 1.0e-3))
    results["transform_local_changed"] = {
        "gate": "hierarchy_transform",
        "expected": "fail on the bound",
        "measurement": {
            "local_max": changed["measurements"]["local"]["max"],
            "root_max": changed["measurements"]["root_relative"]["max"],
        },
        "pass": not changed["pass"],
    }

    missing = copy_module.deepcopy(scene)
    missing.pop(sorted(missing)[-1])
    short = transform_measurement(scene, missing)
    results["transform_object_missing"] = {
        "gate": "hierarchy_transform",
        "expected": "fail with null numbers",
        "measurement": {
            "objects": [short["objects_compared"], short["objects_expected"]],
            "local": short["measurements"]["local"],
        },
        "pass": (
            not short["pass"]
            and short["measurements"]["local"]["measurement_valid"] is False
            and short["measurements"]["local"]["max"] is None
            and short["measurements"]["local"]["rms"] is None
        ),
    }

    two_polygons = cases["hard_edge"]
    cancelled = cancelling_areas(two_polygons["normalized"], 1.0e-4)
    gate = polygon_surface_gate(two_polygons["evaluated"], cancelled)
    reasons = [item["reason"] for item in gate["findings"]]
    results["per_polygon_area_cancelling"] = {
        "gate": "polygon_surface_per_polygon_area",
        "expected": "per-polygon area fails while the total still agrees",
        "measurement": {
            "reasons": reasons,
            "per_polygon_area": gate["per_polygon_area"],
            "surface_area_gap": gate["surface_area_gap"],
        },
        "pass": (
            not gate["pass"]
            and reasons.count("polygon area") >= 2
            and "total surface area" not in reasons
        ),
    }

    still = invariant_signature(normalized, reimport)
    broken = invariant_signature(normalized, moved)
    results["shuffle_signature_is_sensitive"] = {
        "gate": "shuffle_invariance",
        "expected": "signatures differ",
        "measurement": {"baseline_pairs": still["pairs"], "broken_pairs": broken["pairs"]},
        "pass": still != broken,
    }
    return results


# --------------------------------------------------------------------------
# Modes


def do_build(staging):
    staging.mkdir(parents=True, exist_ok=True)
    payload = {}
    for name, make, options in fixtures():
        payload[name] = {"options": options, "variants": {}}
        for triangles in (True, False):
            root = fresh()
            make(root)
            bpy.context.view_layer.update()
            raw = read_scene(root, evaluated=False)
            evaluated = read_scene(root, evaluated=True)
            holder = export_copy(root, shuffle=options.get("shuffle_copy", False))
            normalized = read_scene(holder, evaluated=False)
            for identity, entry in normalized.items():
                if entry["type"] == "MESH":
                    assert all(
                        len(item["corners"]) == 3 for item in entry["polygons"]
                    ), f"{name}/{identity}: export copy is not triangulated"
            bpy.ops.object.select_all(action="DESELECT")
            for obj in [holder] + list(holder.children_recursive):
                obj.select_set(True)
            bpy.context.view_layer.objects.active = holder
            settings = dict(toggle.EXPORT_SETTINGS)
            settings["use_triangles"] = triangles
            target = staging / f"{name}__tri{int(triangles)}.fbx"
            bpy.ops.export_scene.fbx(filepath=str(target), **settings)
            payload[name]["variants"][f"tri{int(triangles)}"] = {
                "fbx": str(target),
                "fbx_sha256": m1.digest(target),
                "use_triangles": triangles,
                "raw": raw,
                "evaluated": evaluated,
                "normalized": normalized,
            }
        print(f"[Opus5Completion] build {name}")
    (staging / "source.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def do_reimport(staging):
    source = json.loads((staging / "source.json").read_text())
    payload = {}
    for name, case in source.items():
        payload[name] = {}
        for key, entry in case["variants"].items():
            bpy.ops.wm.read_homefile(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=entry["fbx"])
            roots = [
                obj
                for obj in bpy.data.objects
                if obj.parent is None and identity_of(obj) == "root"
            ]
            if len(roots) != 1:
                raise AssertionError(
                    f"{name}/{key}: {len(roots)} objects claim the root identity"
                )
            payload[name][key] = read_scene(roots[0], evaluated=False)
        print(f"[Opus5Completion] reimport {name}")
    (staging / "reimport.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


UV_SETTING_WORDS = ("uv", "texture coordinate", "tangent", "layer", "map")


def uv_setting_candidates():
    """Bounded probe over every FBX operator property, not a guessed subset.

    The full identifier list is recorded as well, so "no native setting" is
    backed by the enumeration it came from rather than asserted.
    """
    found = {}
    examined = {}
    for operator, label in (
        (bpy.ops.export_scene.fbx, "export"),
        (bpy.ops.import_scene.fbx, "import"),
    ):
        rna = operator.get_rna_type()
        names = []
        for prop in rna.properties:
            if prop.identifier in {"rna_type", "filepath", "directory", "files"}:
                continue
            names.append(prop.identifier)
            text = f"{prop.identifier} {prop.name} {prop.description}".lower()
            if any(word in text for word in UV_SETTING_WORDS):
                found.setdefault(label, {})[prop.identifier] = {
                    "type": prop.type,
                    "name": prop.name,
                    "description": prop.description,
                    "default": getattr(prop, "default", None),
                }
        examined[label] = sorted(names)
    return found, examined


def do_probe(staging):
    """Does any native setting carry the active / render UV selection?"""
    candidates, examined = uv_setting_candidates()
    trials = []
    export_flags = [
        name
        for name, value in candidates.get("export", {}).items()
        if value["type"] == "BOOLEAN"
    ]
    for identity, builder in (
        ("multi_uv", f_multi_uv),
        ("multi_uv_render", f_multi_uv_render),
    ):
        for flag in [None] + export_flags[:6]:
            for value in (True, False) if flag else (None,):
                root = fresh()
                builder(root)
                bpy.context.view_layer.update()
                holder = export_copy(root)
                before = read_scene(holder, evaluated=False)[identity]
                bpy.ops.object.select_all(action="DESELECT")
                for obj in [holder] + list(holder.children_recursive):
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = holder
                settings = dict(toggle.EXPORT_SETTINGS)
                settings["use_triangles"] = False
                if flag:
                    settings[flag] = value
                target = staging / f"probe_{identity}_{flag}_{value}.fbx"
                bpy.ops.export_scene.fbx(filepath=str(target), **settings)
                bpy.ops.wm.read_homefile(use_empty=True)
                bpy.ops.import_scene.fbx(filepath=str(target))
                back = next(
                    obj for obj in bpy.data.objects if identity_of(obj) == identity
                )
                mesh = back.data
                render = [
                    layer.name for layer in mesh.uv_layers if layer.active_render
                ]
                trials.append(
                    {
                        "fixture": identity,
                        "setting": flag,
                        "value": value,
                        "source_layers": before["uv_layers"],
                        "source_active": before["active_uv_layer"],
                        "source_render": before["render_uv_layer"],
                        "reimport_layers": [l.name for l in mesh.uv_layers],
                        "reimport_active": (
                            mesh.uv_layers.active.name if mesh.uv_layers.active else None
                        ),
                        "reimport_render": render[0] if render else None,
                    }
                )
    def carries(trial):
        """Only a selection that was not already the first layer is evidence."""
        first = trial["source_layers"][0] if trial["source_layers"] else None
        active_informative = trial["source_active"] != first
        render_informative = trial["source_render"] != first
        return bool(
            (active_informative and trial["reimport_active"] == trial["source_active"])
            or (
                render_informative
                and trial["reimport_render"] == trial["source_render"]
            )
        )

    carried = [trial for trial in trials if carries(trial)]
    informative = [
        trial
        for trial in trials
        if trial["source_active"] != trial["source_layers"][0]
        or trial["source_render"] != trial["source_layers"][0]
    ]
    payload = {
        "note": (
            "In-process reimport into an empty file; the strict fixture path "
            "still reimports in a separate process."
        ),
        "candidate_settings": candidates,
        "examined_properties": examined,
        "examined_property_counts": {k: len(v) for k, v in examined.items()},
        "trials": trials,
        "informative_trials": len(informative),
        "settings_that_carry_the_selection": carried,
        "native_setting_found": bool(carried),
    }
    (staging / "probe.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")
    print(
        f"[Opus5Completion] probe {len(trials)} trials, native setting "
        f"{'found' if carried else 'not found'}"
    )


def hierarchy_of(scene):
    return sorted(
        (identity, entry.get("parent"), entry["type"]) for identity, entry in scene.items()
    )


def transform_measurement(before, after):
    """Parent topology says who hangs off whom; this says where they sit.

    §175 compared only `(identity, parent, type)`, so a local transform could
    change without the hierarchy gate noticing. Both matrices are compared
    scalar by scalar, and a scalar that was not compared is not counted.
    """
    shared = sorted(set(before) & set(after))
    expected = len(before) * 32
    local = []
    root_relative = []
    by_object = {}
    for identity in shared:
        first, second = before[identity], after[identity]
        own = {}
        for field, sink in (
            ("local_matrix", local), ("root_relative_matrix", root_relative)
        ):
            values = [
                abs(a - b)
                for row_a, row_b in zip(first[field], second[field])
                for a, b in zip(row_a, row_b)
            ]
            sink.extend(values)
            own[field] = max(values) if values else None
        by_object[identity] = own
    measurement = {
        "local": scalar_measurement(len(before) * 16, local),
        "root_relative": scalar_measurement(len(before) * 16, root_relative),
    }
    for entry in measurement.values():
        entry["bound"] = TRANSFORM_BOUND
        entry["unit"] = "matrix scalar"
        entry["pass"] = bool(
            entry["measurement_valid"]
            and entry["max"] is not None
            and entry["max"] <= TRANSFORM_BOUND
        )
        # A 16-scalar multiset per object is noise in a report; the maxima per
        # object below carry the same information at readable length.
        entry.pop("multiset", None)
    return {
        "objects_expected": len(before),
        "objects_compared": len(shared),
        "scalars_expected": expected,
        "measurements": measurement,
        "by_object": by_object,
        "pass": bool(
            len(shared) == len(before)
            and all(entry["pass"] for entry in measurement.values())
        ),
    }


def compare_variant(case_name, options, entry, reimport):
    objects = {}
    for identity, normalized in entry["normalized"].items():
        if normalized["type"] != "MESH":
            continue
        source = entry["evaluated"].get(identity)
        raw = entry["raw"].get(identity)
        back = reimport.get(identity)
        if source is None or back is None:
            objects[identity] = {
                "status": "missing on one side",
                "pass": False,
            }
            continue
        surface = polygon_surface_gate(source, normalized)
        assignment, kinds, uv = kind_measurements(normalized, back)
        invariance = shuffle_invariance(normalized, back)
        premise = premise_gate(case_name, options, raw, normalized, back)
        layers_equal = normalized["uv_layers"] == back["uv_layers"]
        objects[identity] = {
            "status": "compared",
            "polygon_surface": surface,
            "assignment": assignment,
            "measurements": kinds,
            "uv_layers_by_name": uv,
            "shuffle_invariance": invariance,
            "premise": premise,
            "uv_layer_names": [normalized["uv_layers"], back["uv_layers"]],
            "uv_layer_names_preserved": layers_equal,
            "selection_flags": {
                "active": [normalized["active_uv_layer"], back["active_uv_layer"]],
                "render": [normalized["render_uv_layer"], back["render_uv_layer"]],
                "active_preserved": (
                    normalized["active_uv_layer"] == back["active_uv_layer"]
                ),
                "render_preserved": (
                    normalized["render_uv_layer"] == back["render_uv_layer"]
                ),
                "counted_in_transport_invariant": False,
            },
            "pass": bool(
                surface["pass"]
                and assignment["pass"]
                and all(kind["pass"] for kind in kinds.values())
                and all(result.get("pass") for result in uv.values())
                and invariance["pass"]
                and premise["pass"]
                and layers_equal
            ),
        }
    hierarchy = {
        "source": hierarchy_of(entry["raw"]),
        "normalized": hierarchy_of(entry["normalized"]),
        "reimport": hierarchy_of(reimport),
    }
    hierarchy["parent_topology_preserved"] = (
        hierarchy["source"] == hierarchy["normalized"] == hierarchy["reimport"]
    )
    hierarchy["identities_unique"] = len(set(entry["normalized"])) == len(
        entry["normalized"]
    )
    hierarchy["transform"] = {
        "source_to_normalized": transform_measurement(
            entry["raw"], entry["normalized"]
        ),
        "normalized_to_reimport": transform_measurement(
            entry["normalized"], reimport
        ),
    }
    hierarchy["preserved"] = bool(
        hierarchy["parent_topology_preserved"]
        and all(item["pass"] for item in hierarchy["transform"].values())
    )
    return {
        "use_triangles": entry["use_triangles"],
        "fbx_sha256": entry["fbx_sha256"],
        "hierarchy": hierarchy,
        "objects": objects,
        "pass": bool(
            hierarchy["preserved"]
            and hierarchy["identities_unique"]
            and objects
            and all(row["pass"] for row in objects.values())
        ),
    }


def variant_diff(first, second):
    """Field-by-field, so the adoption argument is in the file, not the prose."""
    def strip(entry):
        out = copy_module.deepcopy(entry)
        out.pop("fbx_sha256", None)
        out.pop("use_triangles", None)
        for row in out.get("objects", {}).values():
            for result in row.get("uv_layers_by_name", {}).values():
                result.pop("elapsed_seconds", None)
        return out

    left, right = strip(first), strip(second)
    differences = []

    def walk(path, a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                walk(f"{path}.{key}", a.get(key), b.get(key))
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for index, (x, y) in enumerate(zip(a, b)):
                walk(f"{path}[{index}]", x, y)
        elif a != b:
            differences.append({"path": path.lstrip("."), "tri1": a, "tri0": b})

    walk("", left, right)
    return {
        "compared": "every field of the per-variant result except the FBX hash",
        "identical": not differences,
        "differences": differences[:20],
        "difference_count": len(differences),
        "fbx_sha256_equal": first["fbx_sha256"] == second["fbx_sha256"],
    }


def do_report(project_root, staging):
    payload = {
        "phase": "M2n2b1b",
        "note": (
            "Adapter fixture completion (alignment 174). No canonical source "
            "and no real-model staging is opened; nothing is published."
        ),
        "frame": "root-relative",
        "identity": "explicit opus5_id custom property; no name or stem matching",
        "snapshots": ["raw", "evaluated", "normalized", "reimport"],
        "gates": [
            "polygon_surface", "geometry", "face_normal", "split_normal",
            "uv_per_layer", "uv_layer_names", "hierarchy", "shuffle_invariance",
            "fixture_premise",
        ],
        "validity_rule": (
            "each measurement kind carries its own expected / matched / "
            "coverage / scalar_count; anything short of full coverage reports "
            "null, because an unmeasured zero is not evidence"
        ),
        "bounds": {
            "position_m": POSITION_BOUND_M,
            "normal_deg": NORMAL_BOUND_DEG,
            "uv_ulp": 1.0,
            "corner_match_tolerance_m": CORNER_TOLERANCE_M,
            "area_relative": AREA_RELATIVE_BOUND,
            "bounds_m": BOUNDS_BOUND_M,
        },
        "adopted_variant": ADOPTED_VARIANT,
    }
    started = time.perf_counter()
    try:
        source = json.loads((staging / "source.json").read_text())
        reimport = json.loads((staging / "reimport.json").read_text())
        probe = {}
        probe_path = staging / "probe.json"
        if probe_path.exists():
            probe = json.loads(probe_path.read_text())
        cases = {}
        control_input = {}
        control_scenes = {}
        for name, case in source.items():
            entry = {}
            for key, variant in case["variants"].items():
                entry[key] = compare_variant(
                    name, case["options"], variant, reimport[name][key]
                )
            entry["variant_diff"] = variant_diff(entry["tri1"], entry["tri0"])
            entry["options"] = case["options"]
            cases[name] = entry
            chosen = case["variants"][ADOPTED_VARIANT]
            mesh_id = next(
                identity
                for identity, item in chosen["normalized"].items()
                if item["type"] == "MESH"
            )
            control_input[name] = {
                "evaluated": chosen["evaluated"][mesh_id],
                "normalized": chosen["normalized"][mesh_id],
                "reimport": reimport[name][ADOPTED_VARIANT][mesh_id],
            }
            control_scenes[name] = chosen["normalized"]
        payload["cases"] = cases
        payload["negative_controls"] = negative_controls(
            control_input, control_scenes
        )
        payload["use_triangles"] = {
            "variants": {"tri1": True, "tri0": False},
            "all_variant_results_identical": all(
                case["variant_diff"]["identical"] for case in cases.values()
            ),
            "fbx_bytes_identical": all(
                case["variant_diff"]["fbx_sha256_equal"] for case in cases.values()
            ),
            "adopted": ADOPTED_VARIANT,
            "adopted_value": False,
            "measured_fact": (
                "every field of both variants' results is identical; only the "
                "FBX bytes differ"
            ),
            "reason": (
                "not that True would change the surface - the export copy is "
                "already triangle-only, so this fixture set cannot show that. "
                "False disables a redundant exporter triangulation path, which "
                "leaves one splitter in the pipeline instead of two and keeps "
                "the responsibility inside Blender where it was measured"
            ),
            "status_source": "the adopted variant alone",
        }
        payload["multi_uv_contract"] = {
            "probe": probe,
            "native_setting_found": probe.get("native_setting_found"),
            "adopted": (
                "transport + authoring invariant (alignment 174.2)"
                if probe and not probe.get("native_setting_found")
                else "undecided: probe missing or a native setting exists"
            ),
            "transport_invariant": [
                "uv layer count", "uv layer names", "uv layer order",
                "every corner value of every layer",
            ],
            "authoring_invariant": [
                "source active / render layer recorded in this report",
                "primary UV must be the first layer",
                "reimported selection flags are not transport evidence",
            ],
            "observed_representation_behavior": "reset_to_first_layer",
        }
        contract_settled = bool(
            probe
            and probe.get("native_setting_found") is False
            and payload["multi_uv_contract"]["adopted"].startswith("transport")
        )
        payload["status_conditions"] = {
            "adopted_variant_all_fixtures_pass": all(
                case[ADOPTED_VARIANT]["pass"] for case in cases.values()
            ),
            "negative_controls_all_fail_as_intended": all(
                item["pass"] for item in payload["negative_controls"].values()
            ),
            "uv_probe_ran_and_contract_settled": contract_settled,
        }
        payload["all_passed"] = all(payload["status_conditions"].values())
        payload["status"] = (
            "complete"
            if payload["all_passed"]
            else (
                "contract undecided"
                if not contract_settled
                and payload["status_conditions"]["adopted_variant_all_fixtures_pass"]
                and payload["status_conditions"][
                    "negative_controls_all_fail_as_intended"
                ]
                else "fixture failure"
            )
        )
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / OUTPUT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        cases = payload.get("cases", {})
        print(
            f"[Opus5Completion] {len(cases)} cases, adopted {ADOPTED_VARIANT}, "
            f"all_passed={payload.get('all_passed')}, "
            f"status {payload.get('status')}"
        )
        for name, control in (payload.get("negative_controls") or {}).items():
            if not control["pass"]:
                print(f"  CONTROL DID NOT FAIL {name}: {control['gate']}")
        for name, case in cases.items():
            variant = case[ADOPTED_VARIANT]
            if variant["pass"]:
                continue
            if not variant["hierarchy"]["preserved"]:
                print(f"  FAIL {name}: hierarchy")
            for identity, row in variant["objects"].items():
                if row.get("pass"):
                    continue
                print(f"  FAIL {name}/{identity}:")
                if not row["polygon_surface"]["pass"]:
                    print(f"     surface {row['polygon_surface']['findings'][:2]}")
                for kind, value in row["measurements"].items():
                    if not value["pass"]:
                        print(
                            f"     {kind} valid={value['measurement_valid']} "
                            f"cov={value['coverage']} max={value['max']}"
                        )
                for layer, value in row["uv_layers_by_name"].items():
                    if not value.get("pass"):
                        print(f"     uv[{layer}] {value.get('status')} "
                              f"over={value.get('over_bound')}")
                if not row["shuffle_invariance"]["pass"]:
                    print(f"     shuffle {row['shuffle_invariance']['findings'][:1]}")
                if not row["premise"]["pass"]:
                    print(f"     premise {row['premise']['findings']}")
                if not row["uv_layer_names_preserved"]:
                    print(f"     layer names {row['uv_layer_names']}")


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    if args.mode != "report":
        blender_compat.require_v6_pipeline()
    if args.mode == "build":
        do_build(staging)
    elif args.mode == "reimport":
        do_reimport(staging)
    elif args.mode == "probe":
        do_probe(staging)
    else:
        do_report(project_root, staging)


if __name__ == "__main__":
    main()
