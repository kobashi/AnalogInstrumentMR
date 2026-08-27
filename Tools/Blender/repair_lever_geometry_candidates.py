"""Repair the two accepted Lever geometry defects in isolated candidates.

Kinetic Safety reverses only inward connected shells in ``handle`` and adds a
thin top cap.  Orbital Analog bridges the visible shaft-to-grip gap with a
short collar.  Added geometry is merged into the existing handle renderer, so
the runtime hierarchy, pivot and renderer count remain unchanged.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_orbital_analog_meter as common


SPECS = {
    "KineticSafety": {
        "root": "PF_Visual_Lever_KineticSafety_V6",
        "candidate": "Lever_KineticSafety_G2",
    },
    "OrbitalAnalog": {
        "root": "PF_Visual_Lever_OrbitalAnalog_V6",
        "candidate": "Lever_OrbitalAnalog_G2",
    },
}


def parse_args():
    raw = sys.argv
    raw = raw[raw.index("--") + 1 :] if "--" in raw else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", required=True, choices=tuple(SPECS))
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--integrate", action="store_true")
    return parser.parse_args(raw)


def vertex_components(mesh):
    adjacency = {vertex.index: set() for vertex in mesh.vertices}
    remaining = set()
    for edge in mesh.edges:
        first, second = edge.vertices
        adjacency[first].add(second)
        adjacency[second].add(first)
        remaining.update((first, second))
    components = []
    while remaining:
        stack = [min(remaining)]
        found = set()
        while stack:
            index = stack.pop()
            if index in found:
                continue
            found.add(index)
            stack.extend(adjacency[index] - found)
        remaining -= found
        components.append(found)
    return components


def component_volume(mesh, vertices):
    volume = 0.0
    for polygon in mesh.polygons:
        indices = list(polygon.vertices)
        if not set(indices).issubset(vertices) or len(indices) < 3:
            continue
        anchor = mesh.vertices[indices[0]].co
        for index in range(1, len(indices) - 1):
            second = mesh.vertices[indices[index]].co
            third = mesh.vertices[indices[index + 1]].co
            volume += anchor.dot(second.cross(third)) / 6.0
    return volume


def reverse_inward_components(obj):
    mesh = obj.data
    components = vertex_components(mesh)
    negative = [
        component for component in components
        if component_volume(mesh, component) < -1e-12
    ]
    if not negative:
        return []
    work = bmesh.new()
    work.from_mesh(mesh)
    work.verts.ensure_lookup_table()
    faces = [
        face for face in work.faces
        if any(all(vertex.index in component for vertex in face.verts) for component in negative)
    ]
    bmesh.ops.reverse_faces(work, faces=faces)
    work.to_mesh(mesh)
    work.free()
    mesh.update()
    return [
        {
            "vertices": len(component),
            "signed_volume_before": component_volume_before,
        }
        for component, component_volume_before in (
            (component, component_volume(mesh, component) * -1.0)
            for component in negative
        )
    ]


def closest_points(mesh, first, second):
    first_index, second_index, distance = min(
        (
            (
                a,
                b,
                (mesh.vertices[a].co - mesh.vertices[b].co).length,
            )
            for a in first for b in second
        ),
        key=lambda item: item[2],
    )
    return mesh.vertices[first_index].co.copy(), mesh.vertices[second_index].co.copy(), distance


def append_cylinder(obj, start, end, radius, segments=24, elliptical_scale=None):
    mesh = obj.data
    old_polygon_count = len(mesh.polygons)
    direction = end - start
    length = direction.length
    if length <= 1e-6:
        raise RuntimeError("Cannot create a zero-length connector")
    transform = (
        Matrix.Translation((start + end) * 0.5)
        @ direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    )
    if elliptical_scale is not None:
        transform @= Matrix.Diagonal(
            (elliptical_scale[0], elliptical_scale[1], 1.0, 1.0)
        )
    work = bmesh.new()
    work.from_mesh(mesh)
    existing_faces = set(work.faces)
    created = bmesh.ops.create_cone(
        work,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=length,
    )
    bmesh.ops.transform(
        work,
        matrix=transform,
        verts=[element for element in created["verts"]],
    )
    new_faces = [face for face in work.faces if face not in existing_faces]
    for face in new_faces:
        face.material_index = 0
    work.to_mesh(mesh)
    work.free()
    mesh.update()

    uv_layer = mesh.uv_layers.active
    if uv_layer is not None:
        for polygon in mesh.polygons[old_polygon_count:]:
            for loop_index in polygon.loop_indices:
                uv_layer.data[loop_index].uv = (0.25, 0.75)
    return {
        "start": list(start),
        "end": list(end),
        "length": length,
        "radius": radius,
        "triangles_added": segments * 4 - 4,
    }


def add_kinetic_cap(handle):
    # A shallow elliptical service cap closes the upper grip opening while
    # remaining inside the existing X/Y envelope.
    return append_cylinder(
        handle,
        Vector((0.0, -0.024, 0.1925)),
        Vector((0.0, -0.024, 0.1955)),
        0.018,
        segments=32,
        elliptical_scale=(1.35, 1.0),
    )


def add_orbital_connector(handle):
    components = vertex_components(handle.data)
    if len(components) < 3:
        raise RuntimeError("Orbital handle no longer has expected shaft/grip components")
    shaft = components[0]
    grip = max(components[2:], key=len)
    first, second, gap = closest_points(handle.data, shaft, grip)
    direction = (second - first).normalized()
    connector = append_cylinder(
        handle,
        first - direction * 0.002,
        second + direction * 0.002,
        radius=0.0065,
        segments=24,
    )
    connector["original_gap"] = gap
    return connector


def mesh_stats(root):
    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return {
        "renderers": len(meshes),
        "triangles": triangles,
        "materials": len({
            material.name
            for obj in meshes
            for material in obj.data.materials
            if material is not None
        }),
    }


def render_review(root, path, focus=None, view=(1.7, -3.1, 1.4)):
    render_objects = (
        [focus]
        if focus is not None
        else [obj for obj in root.children_recursive if obj.type == "MESH"]
    )
    points = [obj.matrix_world @ Vector(corner) for obj in render_objects
              for corner in obj.bound_box]
    centre = sum(points, Vector()) / len(points)
    extent = max((point - centre).length for point in points)
    camera_location = centre + Vector(tuple(extent * value for value in view))
    bpy.ops.object.camera_add(location=camera_location)
    camera = bpy.context.object
    camera.data.lens = 62
    camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera
    lights = []
    for location, energy, size in (
        (centre + Vector((0.20, -0.28, 0.25)), 5.5, 0.22),
        (centre + Vector((-0.18, -0.12, 0.12)), 2.2, 0.18),
        (centre + Vector((0.02, 0.12, 0.24)), 3.5, 0.16),
    ):
        data = bpy.data.lights.new("ReviewLight", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new("ReviewLight", data)
        light.location = location
        light.rotation_euler = (centre - location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.collection.objects.link(light)
        lights.append(light)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    scene.world.color = (0.02, 0.02, 0.02)
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    source = Path(args.source).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = SPECS[args.theme]

    bpy.ops.wm.open_mainfile(filepath=str(source))
    root = bpy.data.objects.get(spec["root"])
    if root is None:
        raise RuntimeError(f"Missing {spec['root']}")
    handle = next(
        obj for obj in root.children_recursive
        if obj.type == "MESH" and obj.name.casefold() == "handle"
    )
    before = mesh_stats(root)
    render_review(root, output_dir / f"{spec['candidate']}_Before.png")
    render_review(
        root,
        output_dir / f"{spec['candidate']}_Detail_Before.png",
        focus=handle,
        view=(3.0, -1.4, 1.6),
    )

    changes = []
    if args.theme == "KineticSafety":
        reversed_components = reverse_inward_components(handle)
        if len(reversed_components) != 1:
            raise RuntimeError(
                f"Expected one inward Kinetic component, got {len(reversed_components)}"
            )
        changes.append({"reverse_inward_components": reversed_components})
        changes.append({"top_cap": add_kinetic_cap(handle)})
    else:
        changes.append({"shaft_grip_connector": add_orbital_connector(handle)})

    after = mesh_stats(root)
    if before["renderers"] != after["renderers"]:
        raise RuntimeError("Repair changed renderer count")
    if before["materials"] != after["materials"]:
        raise RuntimeError("Repair changed material count")

    render_review(root, output_dir / f"{spec['candidate']}_After.png")
    render_review(
        root,
        output_dir / f"{spec['candidate']}_Detail_After.png",
        focus=handle,
        view=(3.0, -1.4, 1.6),
    )
    blend_path = output_dir / f"BL_{spec['candidate']}.blend"
    fbx_path = output_dir / f"SM_{spec['candidate']}.fbx"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    blend_path.with_suffix(".blend1").unlink(missing_ok=True)
    common.export_fbx(root, fbx_path)

    production_blend = (
        project_root / "ArtSource/Blender/ThemeHardSurfaceV6" / args.theme
        / f"BL_Lever_{args.theme}_V6_ProductionReady.blend"
    )
    production_fbx = (
        project_root / "Assets/MatsuMotoMeterAR/Content/Themes" / args.theme
        / "Models" / f"SM_Lever_{args.theme}.fbx"
    )
    if args.integrate:
        bpy.ops.wm.save_as_mainfile(filepath=str(production_blend), compress=True)
        production_blend.with_suffix(".blend1").unlink(missing_ok=True)
        common.export_fbx(root, production_fbx)

    report = {
        "status": "CANDIDATE",
        "theme": args.theme,
        "source": str(source),
        "candidate_blend": str(blend_path),
        "candidate_fbx": str(fbx_path),
        "production_integrated": args.integrate,
        "production_blend": str(production_blend.relative_to(project_root)),
        "production_fbx": str(production_fbx.relative_to(project_root)),
        "before": before,
        "after": after,
        "changes": changes,
        "unchanged_contracts": [
            "root hierarchy", "handle_pivot", "renderer count", "material count"
        ],
        "authoring_environment": blender_compat.provenance(),
    }
    report_path = output_dir / f"{spec['candidate']}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
