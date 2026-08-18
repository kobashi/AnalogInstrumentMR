"""Generate Orbital Analog lever, toggle, rotary, button and lamp assets."""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_orbital_analog_meter as common


THEME_ID = "orbital-analog"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def create_root(name, type_id):
    root = bpy.data.objects.new(name, None)
    root.empty_display_type = "PLAIN_AXES"
    root["instrument_type_id"] = type_id
    root["theme_id"] = THEME_ID
    root["unity_mount_axis"] = "+Z"
    bpy.context.collection.objects.link(root)
    return root


def add_cube(name, dimensions, location, material, uv, bevel=0.001):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel > 0:
        common.apply_bevel(obj, bevel)
    common.set_constant_uv(obj, uv)
    return obj


def add_vertical_cylinder(
    name,
    radius,
    height,
    location,
    vertices,
    material,
    uv,
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=height,
        end_fill_type="NGON",
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    common.set_constant_uv(obj, uv)
    return obj


def add_sphere(name, radius, location, material, uv, segments=12, rings=6):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    common.set_constant_uv(obj, uv)
    return obj


def set_smooth(objects):
    for obj in objects:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_smooth_by_angle()
        obj.select_set(False)


def parent_at_pivot(objects, name, pivot, root):
    joined = common.join_objects(objects, name)
    bpy.context.scene.cursor.location = pivot
    bpy.context.view_layer.objects.active = joined
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    pivot_object = bpy.data.objects.new(f"{name}_pivot", None)
    pivot_object.empty_display_type = "ARROWS"
    pivot_object.empty_display_size = 0.012
    pivot_object.location = pivot
    pivot_object.parent = root
    bpy.context.collection.objects.link(pivot_object)
    joined.parent = pivot_object
    joined.location = (0.0, 0.0, 0.0)
    joined.rotation_euler = (0.0, 0.0, 0.0)
    joined.scale = (1.0, 1.0, 1.0)
    return pivot_object, joined


def build_lever(opaque, emissive):
    root = create_root("PF_Visual_Lever_OrbitalAnalog", "control.lever")
    housing_parts = [
        add_cube(
            "housing_plate",
            (0.18, 0.05, 0.14),
            (0.0, -0.025, 0.0),
            opaque,
            (0.125, 0.125),
            0.002,
        ),
        add_cube(
            "housing_left_rail",
            (0.018, 0.010, 0.115),
            (-0.069, -0.056, 0.0),
            opaque,
            (0.625, 0.125),
            0.0015,
        ),
        add_cube(
            "housing_right_rail",
            (0.018, 0.010, 0.115),
            (0.069, -0.056, 0.0),
            opaque,
            (0.625, 0.125),
            0.0015,
        ),
    ]
    collar = common.add_cylinder(
        "housing_collar", 0.030, 0.012, 0.061, 20, opaque
    )
    collar.location.z = -0.025
    common.set_constant_uv(collar, (0.625, 0.125))
    housing_parts.append(collar)
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    pivot = (0.0, -0.070, -0.025)
    shaft = add_vertical_cylinder(
        "handle_shaft",
        0.008,
        0.145,
        (0.0, -0.070, 0.0475),
        12,
        opaque,
        (0.875, 0.125),
    )
    grip = add_sphere(
        "handle_grip",
        0.025,
        (0.0, -0.070, 0.145),
        emissive,
        (0.375, 0.125),
        12,
        6,
    )
    handle_pivot, handle = parent_at_pivot(
        [shaft, grip], "handle", pivot, root
    )
    handle_pivot.name = "handle_pivot"
    set_smooth([housing, handle])
    return {
        "root": root,
        "meshes": [housing, handle],
        "pivot": handle_pivot,
        "movable": handle,
        "center_z": 0.045,
    }


def build_toggle(opaque, emissive):
    root = create_root("PF_Visual_Toggle_OrbitalAnalog", "control.toggle")
    housing_parts = [
        add_cube(
            "housing_plate",
            (0.12, 0.036, 0.14),
            (0.0, -0.018, 0.0),
            opaque,
            (0.125, 0.125),
            0.0018,
        )
    ]
    collar = common.add_cylinder(
        "housing_collar", 0.025, 0.012, 0.046, 16, opaque
    )
    common.set_constant_uv(collar, (0.625, 0.125))
    housing_parts.append(collar)
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    pivot = (0.0, -0.054, 0.0)
    shaft = add_vertical_cylinder(
        "switch_shaft",
        0.006,
        0.067,
        (0.0, -0.054, 0.0335),
        10,
        opaque,
        (0.875, 0.125),
    )
    tip = add_sphere(
        "switch_tip",
        0.010,
        (0.0, -0.054, 0.071),
        emissive,
        (0.375, 0.125),
        10,
        5,
    )
    switch_pivot, switch = parent_at_pivot(
        [shaft, tip], "switch", pivot, root
    )
    switch_pivot.name = "switch_pivot"
    set_smooth([housing, switch])
    return {
        "root": root,
        "meshes": [housing, switch],
        "pivot": switch_pivot,
        "movable": switch,
        "center_z": 0.015,
    }


def build_rotary(opaque, emissive):
    root = create_root("PF_Visual_Rotary_OrbitalAnalog", "control.rotary")
    housing_parts = [
        add_cube(
            "housing_plate",
            (0.15, 0.04, 0.15),
            (0.0, -0.020, 0.0),
            opaque,
            (0.125, 0.125),
            0.002,
        )
    ]
    collar = common.add_annulus(
        "housing_collar",
        outer_radius=0.061,
        inner_radius=0.0525,
        depth=0.014,
        outward_depth=0.045,
        segments=24,
        material=opaque,
    )
    common.set_constant_uv(collar, (0.625, 0.125))
    housing_parts.append(collar)
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    pivot_position = (0.0, -0.065, 0.0)
    knob_body = common.add_cylinder(
        "knob_body", 0.052, 0.045, 0.0675, 20, opaque
    )
    bpy.context.view_layer.objects.active = knob_body
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    common.set_constant_uv(knob_body, (0.125, 0.125))
    index = add_cube(
        "knob_index",
        (0.007, 0.004, 0.036),
        (0.0, -0.0915, 0.026),
        emissive,
        (0.375, 0.125),
        0.0007,
    )
    knob_pivot, knob = parent_at_pivot(
        [knob_body, index], "knob", pivot_position, root
    )
    knob_pivot.name = "knob_pivot"
    set_smooth([housing, knob])
    return {
        "root": root,
        "meshes": [housing, knob],
        "pivot": knob_pivot,
        "movable": knob,
        "center_z": 0.0,
    }


def build_button(opaque, emissive):
    root = create_root("PF_Visual_Button_OrbitalAnalog", "control.button")
    housing_parts = [
        add_cube(
            "housing_plate",
            (0.13, 0.04, 0.13),
            (0.0, -0.020, 0.0),
            opaque,
            (0.125, 0.125),
            0.002,
        )
    ]
    guard = common.add_annulus(
        "housing_guard",
        outer_radius=0.052,
        inner_radius=0.0435,
        depth=0.015,
        outward_depth=0.0475,
        segments=20,
        material=opaque,
    )
    common.set_constant_uv(guard, (0.625, 0.125))
    housing_parts.append(guard)
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    button = common.add_cylinder(
        "button", 0.041, 0.036, 0.066, 20, emissive
    )
    common.set_constant_uv(button, (0.375, 0.125))
    bpy.context.scene.cursor.location = (0.0, -0.066, 0.0)
    bpy.context.view_layer.objects.active = button
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    button_travel = bpy.data.objects.new("button_travel", None)
    button_travel.empty_display_type = "ARROWS"
    button_travel.empty_display_size = 0.012
    button_travel.location = (0.0, -0.066, 0.0)
    button_travel.parent = root
    bpy.context.collection.objects.link(button_travel)
    button.parent = button_travel
    button.location = (0.0, 0.0, 0.0)
    set_smooth([housing, button])
    return {
        "root": root,
        "meshes": [housing, button],
        "pivot": button_travel,
        "movable": button,
        "center_z": 0.0,
    }


def build_lamp(opaque, emissive):
    root = create_root("PF_Visual_Lamp_OrbitalAnalog", "indicator.lamp")
    housing_parts = [
        add_cube(
            "housing_plate",
            (0.14, 0.036, 0.11),
            (0.0, -0.018, 0.0),
            opaque,
            (0.125, 0.125),
            0.002,
        )
    ]
    cage = common.add_annulus(
        "housing_cage",
        outer_radius=0.041,
        inner_radius=0.033,
        depth=0.016,
        outward_depth=0.045,
        segments=16,
        material=opaque,
    )
    common.set_constant_uv(cage, (0.625, 0.125))
    housing_parts.append(cage)
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    indicator = add_sphere(
        "indicator",
        1.0,
        (0.0, -0.057, 0.0),
        emissive,
        (0.375, 0.125),
        16,
        8,
    )
    indicator.scale = (0.032, 0.020, 0.032)
    bpy.context.view_layer.objects.active = indicator
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    indicator.parent = root
    set_smooth([housing, indicator])
    return {
        "root": root,
        "meshes": [housing, indicator],
        "pivot": None,
        "movable": indicator,
        "center_z": 0.0,
    }


ASSETS = (
    {
        "key": "Lever",
        "type_id": "control.lever",
        "builder": build_lever,
        "limits": (0.18001, 0.25601, 0.10001),
    },
    {
        "key": "Toggle",
        "type_id": "control.toggle",
        "builder": build_toggle,
        "limits": (0.12001, 0.17001, 0.06401),
    },
    {
        "key": "Rotary",
        "type_id": "control.rotary",
        "builder": build_rotary,
        "limits": (0.15001, 0.15001, 0.10201),
    },
    {
        "key": "Button",
        "type_id": "control.button",
        "builder": build_button,
        "limits": (0.13001, 0.13001, 0.09001),
    },
    {
        "key": "Lamp",
        "type_id": "indicator.lamp",
        "builder": build_lamp,
        "limits": (0.14001, 0.11001, 0.08201),
    },
)


def create_preview(meshes, center_z, output_path):
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    extent_x = max(point.x for point in points) - min(point.x for point in points)
    extent_z = max(point.z for point in points) - min(point.z for point in points)
    maximum = max(extent_x, extent_z)
    target = (0.0, -0.025, center_z)
    bpy.ops.object.camera_add(
        location=(
            maximum * 0.65,
            -maximum * 2.25,
            center_z + maximum * 0.52,
        )
    )
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.data.lens = 58

    def point_at(obj, target_point):
        direction = Vector(target_point) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    point_at(camera, target)
    bpy.context.scene.camera = camera
    lights = []
    for name, location, energy, size in (
        (
            "Key",
            (maximum, -maximum * 1.2, center_z + maximum),
            5.5,
            maximum,
        ),
        (
            "Fill",
            (-maximum, -maximum, center_z + maximum * 0.2),
            2.2,
            maximum,
        ),
        (
            "Rim",
            (0.0, maximum * 0.4, center_z + maximum),
            3.5,
            maximum * 0.75,
        ),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        bpy.context.collection.objects.link(light)
        point_at(light, target)
        lights.append(light)

    scene = bpy.context.scene
    scene.world.color = (0.012, 0.016, 0.022)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(output_path)
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)


def generate_asset(asset, project_root, base_image):
    common.clean_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    opaque = common.create_material(base_image)
    emissive = common.create_emissive_material(base_image)
    built = asset["builder"](opaque, emissive)
    meshes = built["meshes"]
    common.apply_transforms(meshes)
    stats = common.mesh_stats(meshes)
    stats.update(
        {
            "asset": f"{asset['key']}_OrbitalAnalog",
            "instrument_type_id": asset["type_id"],
            "theme_id": THEME_ID,
            "unity_mount_axis": "+Z",
            "greybox_triangle_budget": 1500,
            "renderer_budget": 3,
            "material_budget": 2,
            "colliders": 0,
            "realtime_lights": 0,
            "pivot": built["pivot"].name if built["pivot"] else None,
            "movable": built["movable"].name,
        }
    )
    if stats["triangles"] > 1500:
        raise RuntimeError(f"{asset['key']} triangle budget exceeded: {stats}")
    if stats["mesh_objects"] > 3 or stats["materials"] > 2:
        raise RuntimeError(f"{asset['key']} renderer/material budget exceeded: {stats}")
    if any(
        value > limit
        for value, limit in zip(stats["unity_bounds_m"], asset["limits"])
    ):
        raise RuntimeError(f"{asset['key']} bounds exceeded: {stats}")

    source_dir = project_root / "ArtSource/Blender/OrbitalAnalog"
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    preview_path = source_dir / f"Preview_{asset['key']}_OrbitalAnalog.png"
    create_preview(meshes, built["center_z"], preview_path)

    blend_path = source_dir / f"BL_{asset['key']}_OrbitalAnalog.blend"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    backup = blend_path.with_suffix(".blend1")
    if backup.exists():
        backup.unlink()

    fbx_path = model_dir / f"SM_{asset['key']}_OrbitalAnalog.fbx"
    copied_texture_dir = model_dir / f"SM_{asset['key']}_OrbitalAnalog.fbm"
    if copied_texture_dir.exists():
        shutil.rmtree(copied_texture_dir)
    common.export_fbx(built["root"], fbx_path)
    report_path = source_dir / f"BL_{asset['key']}_OrbitalAnalog.report.json"
    report_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    texture_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Textures"
    )
    texture_dir.mkdir(parents=True, exist_ok=True)
    common.clean_scene()
    _, images = common.build_texture_atlas(texture_dir)
    base_image = images["base_color"]
    for asset in ASSETS:
        generate_asset(asset, project_root, base_image)


if __name__ == "__main__":
    main()
