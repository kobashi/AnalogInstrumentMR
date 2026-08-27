"""Audit connected mesh components in a production-ready Lever Blend.

Reports component winding, open boundaries, bounds and minimum separation.
This is read-only and is intended to distinguish grip, shaft and cap defects
before changing production geometry.
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat


def parse_args():
    raw = sys.argv
    raw = raw[raw.index("--") + 1 :] if "--" in raw else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(raw)


def connected_vertex_sets(mesh):
    adjacency = {vertex.index: set() for vertex in mesh.vertices}
    used = set()
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
        used.update((a, b))
    components = []
    while used:
        seed = min(used)
        stack = [seed]
        component = set()
        while stack:
            index = stack.pop()
            if index in component:
                continue
            component.add(index)
            stack.extend(adjacency[index] - component)
        used -= component
        components.append(component)
    return components


def component_report(mesh, vertex_indices):
    polygons = [
        polygon for polygon in mesh.polygons
        if set(polygon.vertices).issubset(vertex_indices)
    ]
    edge_face_count = {}
    volume = 0.0
    triangles = 0
    for polygon in polygons:
        vertices = list(polygon.vertices)
        for offset, first in enumerate(vertices):
            edge = tuple(sorted((first, vertices[(offset + 1) % len(vertices)])))
            edge_face_count[edge] = edge_face_count.get(edge, 0) + 1
        if len(vertices) >= 3:
            a = mesh.vertices[vertices[0]].co
            for index in range(1, len(vertices) - 1):
                b = mesh.vertices[vertices[index]].co
                c = mesh.vertices[vertices[index + 1]].co
                volume += a.dot(b.cross(c)) / 6.0
                triangles += 1
    coords = [mesh.vertices[index].co for index in vertex_indices]
    minimum = [min(co[axis] for co in coords) for axis in range(3)]
    maximum = [max(co[axis] for co in coords) for axis in range(3)]
    return {
        "vertices": len(vertex_indices),
        "faces": len(polygons),
        "triangles": triangles,
        "signed_volume": volume,
        "boundary_edges": sum(count == 1 for count in edge_face_count.values()),
        "nonmanifold_edges": sum(count != 2 for count in edge_face_count.values()),
        "bounds_min": minimum,
        "bounds_max": maximum,
        "centroid": [sum(co[axis] for co in coords) / len(coords) for axis in range(3)],
    }


def minimum_vertex_separation(mesh, first, second):
    return min(
        (mesh.vertices[a].co - mesh.vertices[b].co).length
        for a in first for b in second
    )


def inspect_mesh(obj):
    mesh = obj.data
    components = connected_vertex_sets(mesh)
    reports = [component_report(mesh, component) for component in components]
    separations = []
    for first in range(len(components)):
        for second in range(first + 1, len(components)):
            separations.append({
                "components": [first, second],
                "minimum_vertex_separation": minimum_vertex_separation(
                    mesh, components[first], components[second]
                ),
            })
    return {
        "name": obj.name,
        "parent": obj.parent.name if obj.parent else None,
        "matrix_determinant": obj.matrix_world.to_3x3().determinant(),
        "components": reports,
        "component_separations": separations,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    source = Path(args.source).resolve()
    if source.suffix.casefold() == ".fbx":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(source))
    else:
        bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects.get(args.root)
    if root is None:
        raise RuntimeError(f"Missing root: {args.root}")
    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    report = {
        "source": str(source),
        "root": args.root,
        "meshes": [inspect_mesh(obj) for obj in sorted(meshes, key=lambda item: item.name)],
        "authoring_environment": blender_compat.provenance(),
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
