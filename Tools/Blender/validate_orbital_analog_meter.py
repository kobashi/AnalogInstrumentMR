"""Validate the generated Orbital Analog round-meter .blend and Unity FBX."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def assert_close_vector(actual, expected, tolerance=0.00001):
    if any(abs(a - e) > tolerance for a, e in zip(actual, expected)):
        raise RuntimeError(f"Expected {expected}, got {tuple(actual)}")


def triangle_count(objects):
    total = 0
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        total += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    return total


def bounds_in_blender_axes(objects):
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    minimum = Vector(
        (
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        )
    )
    maximum = Vector(
        (
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        )
    )
    return minimum, maximum


def validate_scene(label):
    root = bpy.data.objects.get("PF_Visual_MeterRound_OrbitalAnalog")
    housing = bpy.data.objects.get("housing")
    dial = bpy.data.objects.get("dial")
    pivot = bpy.data.objects.get("needle_pivot")
    needle = bpy.data.objects.get("needle")
    required = (root, housing, dial, pivot, needle)
    if any(obj is None for obj in required):
        missing = [
            name
            for name in (
                "PF_Visual_MeterRound_OrbitalAnalog",
                "housing",
                "dial",
                "needle_pivot",
                "needle",
            )
            if bpy.data.objects.get(name) is None
        ]
        raise RuntimeError(f"{label}: missing objects {missing}")

    assert_close_vector(root.location, (0.0, 0.0, 0.0))
    assert_close_vector(root.scale, (1.0, 1.0, 1.0))
    assert_close_vector(root.rotation_euler, (0.0, 0.0, 0.0))
    if housing.parent != root or dial.parent != root or pivot.parent != root:
        raise RuntimeError(f"{label}: invalid root hierarchy")
    if needle.parent != pivot:
        raise RuntimeError(f"{label}: needle must be parented to needle_pivot")

    meshes = [housing, dial, needle]
    for obj in meshes:
        if obj.type != "MESH" or not obj.data.uv_layers:
            raise RuntimeError(f"{label}: {obj.name} requires a UV-mapped mesh")
    triangles = triangle_count(meshes)
    if triangles > 1500:
        raise RuntimeError(f"{label}: triangle budget exceeded: {triangles}")

    material_names = {
        slot.material.name
        for obj in meshes
        for slot in obj.material_slots
        if slot.material is not None
    }
    if len(material_names) > 2:
        raise RuntimeError(f"{label}: shared material budget exceeded: {material_names}")

    minimum, maximum = bounds_in_blender_axes(meshes)
    unity_bounds = (
        maximum.x - minimum.x,
        maximum.z - minimum.z,
        maximum.y - minimum.y,
    )
    limits = (0.14001, 0.14001, 0.06401)
    if any(value > limit for value, limit in zip(unity_bounds, limits)):
        raise RuntimeError(f"{label}: Unity bounds exceeded: {unity_bounds}")

    return {
        "label": label,
        "triangles": triangles,
        "mesh_objects": len(meshes),
        "materials": sorted(material_names),
        "unity_bounds_m": [round(value, 6) for value in unity_bounds],
        "hierarchy": {
            "root": root.name,
            "static": [housing.name, dial.name],
            "pivot": pivot.name,
            "movable": needle.name,
        },
    }


def main():
    args = parse_args()
    root = Path(args.project_root).resolve()
    blend_path = (
        root
        / "ArtSource/Blender/OrbitalAnalog/BL_MeterRound_OrbitalAnalog.blend"
    )
    fbx_path = (
        root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models/"
        "SM_MeterRound_OrbitalAnalog.fbx"
    )
    texture_dir = (
        root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Textures"
    )

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    blend_result = validate_scene("blend")
    if bpy.data.cameras or bpy.data.lights:
        raise RuntimeError("Source blend must not retain preview cameras or lights")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=False)
    fbx_result = validate_scene("fbx-roundtrip")

    expected_textures = (
        "T_OrbitalAnalog_Atlas_BaseColor.png",
        "T_OrbitalAnalog_Atlas_Normal.png",
        "T_OrbitalAnalog_Atlas_MetallicSmoothness.png",
        "T_OrbitalAnalog_Atlas_Emission.png",
    )
    for filename in expected_textures:
        path = texture_dir / filename
        if not path.is_file():
            raise RuntimeError(f"Missing texture: {path}")

    result = {
        "blend": blend_result,
        "fbx_roundtrip": fbx_result,
        "textures": list(expected_textures),
        "status": "PASS",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
