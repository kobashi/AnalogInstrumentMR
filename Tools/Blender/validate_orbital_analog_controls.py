"""Validate Orbital Analog control .blend files and Unity FBX round-trips."""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ASSETS = (
    {
        "key": "Lever",
        "root": "PF_Visual_Lever_OrbitalAnalog",
        "meshes": ("housing", "handle"),
        "pivot": "handle_pivot",
        "movable": "handle",
        "limits": (0.18001, 0.25601, 0.10001),
        "motion_axis": "Blender X / Unity X",
        "motion_range": "±32°",
    },
    {
        "key": "Toggle",
        "root": "PF_Visual_Toggle_OrbitalAnalog",
        "meshes": ("housing", "switch"),
        "pivot": "switch_pivot",
        "movable": "switch",
        "limits": (0.12001, 0.17001, 0.06401),
        "motion_axis": "Blender X / Unity X",
        "motion_range": "±28°",
    },
    {
        "key": "Rotary",
        "root": "PF_Visual_Rotary_OrbitalAnalog",
        "meshes": ("housing", "knob"),
        "pivot": "knob_pivot",
        "movable": "knob",
        "limits": (0.15001, 0.15001, 0.10201),
        "motion_axis": "Blender Y / Unity Z",
        "motion_range": "continuous",
    },
    {
        "key": "Button",
        "root": "PF_Visual_Button_OrbitalAnalog",
        "meshes": ("housing", "button"),
        "pivot": "button_travel",
        "movable": "button",
        "limits": (0.13001, 0.13001, 0.09001),
        "motion_axis": "Blender +Y / Unity -Z",
        "motion_range": "14 mm",
    },
    {
        "key": "Lamp",
        "root": "PF_Visual_Lamp_OrbitalAnalog",
        "meshes": ("housing", "indicator"),
        "pivot": None,
        "movable": "indicator",
        "limits": (0.14001, 0.11001, 0.08201),
        "motion_axis": None,
        "motion_range": None,
    },
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def assert_identity(obj, label):
    vectors = (
        ("location", obj.location, (0.0, 0.0, 0.0)),
        ("rotation", obj.rotation_euler, (0.0, 0.0, 0.0)),
        ("scale", obj.scale, (1.0, 1.0, 1.0)),
    )
    for field, actual, expected in vectors:
        if any(abs(a - e) > 0.00001 for a, e in zip(actual, expected)):
            raise RuntimeError(
                f"{label}: {obj.name} {field} expected {expected}, got {tuple(actual)}"
            )


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


def unity_bounds(objects):
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    extent = (
        max(point.x for point in points) - min(point.x for point in points),
        max(point.z for point in points) - min(point.z for point in points),
        max(point.y for point in points) - min(point.y for point in points),
    )
    return tuple(round(value, 6) for value in extent)


def validate_scene(asset, label):
    names = (asset["root"], *asset["meshes"], asset["pivot"])
    missing = [
        name for name in names if name and bpy.data.objects.get(name) is None
    ]
    if missing:
        raise RuntimeError(f"{label}: missing objects {missing}")

    root = bpy.data.objects[asset["root"]]
    meshes = [bpy.data.objects[name] for name in asset["meshes"]]
    pivot = bpy.data.objects.get(asset["pivot"]) if asset["pivot"] else None
    movable = bpy.data.objects[asset["movable"]]
    assert_identity(root, label)

    housing = bpy.data.objects["housing"]
    if housing.parent != root:
        raise RuntimeError(f"{label}: housing must be parented to root")
    if pivot:
        if pivot.parent != root or movable.parent != pivot:
            raise RuntimeError(f"{label}: invalid movable hierarchy")
    elif movable.parent != root:
        raise RuntimeError(f"{label}: static indicator must be parented to root")

    for obj in meshes:
        if obj.type != "MESH" or not obj.data.uv_layers:
            raise RuntimeError(f"{label}: {obj.name} requires a UV-mapped mesh")
    triangles = triangle_count(meshes)
    if triangles > 1500:
        raise RuntimeError(f"{label}: triangle budget exceeded: {triangles}")
    if len(meshes) > 3:
        raise RuntimeError(f"{label}: renderer budget exceeded: {len(meshes)}")

    materials = sorted(
        {
            slot.material.name
            for obj in meshes
            for slot in obj.material_slots
            if slot.material is not None
        }
    )
    if len(materials) > 2:
        raise RuntimeError(f"{label}: material budget exceeded: {materials}")

    bounds = unity_bounds(meshes)
    if any(value > limit for value, limit in zip(bounds, asset["limits"])):
        raise RuntimeError(f"{label}: Unity rest bounds exceeded: {bounds}")

    return {
        "label": label,
        "triangles": triangles,
        "mesh_objects": len(meshes),
        "materials": materials,
        "unity_rest_bounds_m": list(bounds),
        "hierarchy": {
            "root": root.name,
            "static": [housing.name],
            "pivot": pivot.name if pivot else None,
            "movable": movable.name,
        },
        "motion_axis": asset["motion_axis"],
        "motion_range": asset["motion_range"],
    }


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(collection):
            collection.remove(block)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    source_dir = project_root / "ArtSource/Blender/OrbitalAnalog"
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models"
    )
    results = {}

    for asset in ASSETS:
        blend_path = source_dir / f"BL_{asset['key']}_OrbitalAnalog.blend"
        fbx_path = model_dir / f"SM_{asset['key']}_OrbitalAnalog.fbx"
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
        blend = validate_scene(asset, "blend")
        if bpy.data.cameras or bpy.data.lights:
            raise RuntimeError(
                f"{asset['key']}: source blend retains preview cameras or lights"
            )

        clear_scene()
        bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=False)
        fbx = validate_scene(asset, "fbx-roundtrip")
        results[asset["key"]] = {
            "blend": blend,
            "fbx_roundtrip": fbx,
            "status": "PASS",
        }

    texture_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Textures"
    )
    expected_textures = (
        "T_OrbitalAnalog_Atlas_BaseColor.png",
        "T_OrbitalAnalog_Atlas_Normal.png",
        "T_OrbitalAnalog_Atlas_MetallicSmoothness.png",
        "T_OrbitalAnalog_Atlas_Emission.png",
    )
    for filename in expected_textures:
        if not (texture_dir / filename).is_file():
            raise RuntimeError(f"Missing texture: {texture_dir / filename}")

    print(
        json.dumps(
            {
                "assets": results,
                "textures": list(expected_textures),
                "status": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
