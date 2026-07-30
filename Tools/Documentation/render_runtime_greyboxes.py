"""Render code-derived review images for runtime-only instrument greyboxes.

Run with:
  blender --background --factory-startup --python \
    Tools/Documentation/render_runtime_greyboxes.py -- \
    --output-dir docs/review_assets/runtime_greyboxes
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


THEMES = {
    "OrbitalAnalog": {
        "housing": (0.12, 0.14, 0.16, 1.0),
        "face": (0.72, 0.75, 0.70, 1.0),
        "dark": (0.06, 0.07, 0.08, 1.0),
        "primary": (0.90, 0.12, 0.06, 1.0),
        "warning": (1.00, 0.48, 0.04, 1.0),
        "ready": (0.10, 0.95, 0.45, 1.0),
    },
    "ForgeBrass": {
        "housing": (0.25, 0.16, 0.08, 1.0),
        "face": (0.82, 0.68, 0.38, 1.0),
        "dark": (0.07, 0.055, 0.04, 1.0),
        "primary": (0.76, 0.24, 0.08, 1.0),
        "warning": (1.00, 0.55, 0.08, 1.0),
        "ready": (0.32, 0.88, 0.48, 1.0),
    },
    "KineticSafety": {
        "housing": (0.08, 0.11, 0.14, 1.0),
        "face": (0.62, 0.69, 0.72, 1.0),
        "dark": (0.025, 0.035, 0.045, 1.0),
        "primary": (1.00, 0.25, 0.035, 1.0),
        "warning": (1.00, 0.72, 0.04, 1.0),
        "ready": (0.08, 1.00, 0.58, 1.0),
    },
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(args)


def material(name, rgba, metallic=0.25, roughness=0.42, emission=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission
            bsdf.inputs["Emission Strength"].default_value = 1.8
        else:
            bsdf.inputs["Emission"].default_value = emission
            bsdf.inputs["Emission Strength"].default_value = 1.8
    return mat


def add_bevel(obj, width):
    modifier = obj.modifiers.new("Review bevel", "BEVEL")
    modifier.width = width
    modifier.segments = 2
    modifier.limit_method = "ANGLE"


def cube(name, size, pos, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=pos)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        add_bevel(obj, bevel)
    obj.data.materials.append(mat)
    return obj


def uv_sphere(name, size, pos, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=32, ring_count=16, location=pos
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = (size[0] * 0.5, size[1] * 0.5, size[2] * 0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def cylinder_y(name, diameter, depth, pos, mat):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48,
        radius=diameter * 0.5,
        depth=depth,
        location=pos,
        rotation=(math.radians(90), 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    add_bevel(obj, min(0.012, depth * 0.18))
    return obj


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def theme_materials(theme_name):
    palette = THEMES[theme_name]
    result = {}
    for key, color in palette.items():
        result[key] = material(
            f"{theme_name}_{key}",
            color,
            metallic=0.45 if key in ("housing", "face") else 0.15,
            roughness=0.36 if key == "face" else 0.48,
            emission=color if key in ("ready", "warning", "primary") else None,
        )
    return result


def build_status_indicator(theme_name, mats):
    housing_depth = {
        "ForgeBrass": 0.050,
        "KineticSafety": 0.044,
        "OrbitalAnalog": 0.044,
    }[theme_name]
    lens = {
        "ForgeBrass": (0.068, 0.038, 0.068),
        "KineticSafety": (0.120, 0.035, 0.045),
        "OrbitalAnalog": (0.090, 0.038, 0.060),
    }[theme_name]
    cube(
        "Status Housing",
        (0.18, housing_depth, 0.12),
        (0.0, -housing_depth * 0.5, 0.0),
        mats["housing"],
        0.008,
    )
    uv_sphere(
        "RGB Status Lens",
        lens,
        (0.0, -(housing_depth + 0.006), 0.0),
        mats["ready"],
    )
    return 0.18


def build_window_meter(theme_name, mats):
    housing_depth = {
        "ForgeBrass": 0.11,
        "KineticSafety": 0.10,
        "OrbitalAnalog": 0.065,
    }[theme_name]
    cube(
        "Window Meter Housing",
        (1.20, housing_depth, 0.75),
        (0.0, -housing_depth * 0.5, 0.0),
        mats["housing"],
        0.025,
    )
    dial_depth = 0.028
    dial_y = -(housing_depth + dial_depth * 0.5)
    if theme_name == "KineticSafety":
        cube(
            "Guarded Dial Recess",
            (0.72, dial_depth, 0.58),
            (0.0, dial_y, 0.0),
            mats["dark"],
            0.035,
        )
    else:
        cylinder_y(
            "Deep Circular Dial",
            0.66,
            dial_depth,
            (0.0, dial_y, 0.0),
            mats["dark"],
        )
    needle_mat = (
        mats["warning"] if theme_name == "KineticSafety" else mats["primary"]
    )
    needle_y = -(housing_depth + dial_depth + 0.010)
    cube(
        "Window Needle",
        (0.026, 0.014, 0.48),
        (0.0, needle_y, 0.16),
        needle_mat,
        0.005,
    )
    uv_sphere(
        "Window Needle Hub",
        (0.075, 0.045, 0.075),
        (0.0, needle_y - 0.004, -0.08),
        mats["face"],
    )
    return 1.20


def build_window_panel(theme_name, mats):
    housing_depth = {
        "ForgeBrass": 0.14,
        "KineticSafety": 0.13,
        "OrbitalAnalog": 0.08,
    }[theme_name]
    base_mat = mats["dark"] if theme_name == "OrbitalAnalog" else mats["housing"]
    cube(
        "Recessed Hull Information Field",
        (1.60, housing_depth, 0.90),
        (0.0, -housing_depth * 0.5, 0.0),
        base_mat,
        0.028,
    )
    guard_mat = mats["warning"] if theme_name == "KineticSafety" else mats["face"]
    guard_width = 0.035 if theme_name == "OrbitalAnalog" else 0.075
    guard_y = -(housing_depth + 0.045)
    for x in (-0.70, 0.70):
        cube(
            "Frame Rail",
            (guard_width, 0.05, 0.72),
            (x, guard_y, 0.0),
            guard_mat,
            0.010,
        )
    vane_mat = mats["primary"] if theme_name == "OrbitalAnalog" else mats["warning"]
    vane_y = -(housing_depth + 0.058)
    cube(
        "Panel Status Vane",
        (0.035, 0.018, 0.50),
        (0.0, vane_y, 0.07),
        vane_mat,
        0.006,
    )
    return 1.60


def look_at(obj, point):
    direction = Vector(point) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_render(max_width):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.world.color = (0.012, 0.015, 0.020)
    world = scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.012,
        0.016,
        0.023,
        1.0,
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.32

    bpy.ops.object.light_add(type="AREA", location=(-2.6, -3.2, 3.5))
    key = bpy.context.object
    key.data.energy = 850
    key.data.shape = "DISK"
    key.data.size = 3.0
    look_at(key, (0.0, 0.0, 0.0))

    bpy.ops.object.light_add(type="AREA", location=(2.8, -1.8, 0.8))
    fill = bpy.context.object
    fill.data.energy = 520
    fill.data.size = 2.4
    look_at(fill, (0.0, 0.0, 0.0))

    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.8, 2.2))
    rim = bpy.context.object
    rim.data.energy = 700
    rim.data.size = 2.2
    look_at(rim, (0.0, -0.1, 0.0))

    bpy.ops.object.camera_add(location=(2.25, -4.2, 1.7))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max_width * 1.33
    look_at(camera, (0.0, -0.03, 0.0))
    scene.camera = camera

    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.image_settings.color_depth = "8"


def render_asset(output_dir, asset, theme_name):
    clear_scene()
    mats = theme_materials(theme_name)
    if asset == "StatusIndicator":
        max_width = build_status_indicator(theme_name, mats)
    elif asset == "WindowMeter":
        max_width = build_window_meter(theme_name, mats)
    else:
        max_width = build_window_panel(theme_name, mats)
    setup_render(max_width)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"Preview_{asset}_{theme_name}.png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {path}")


def main():
    args = parse_args()
    output_dir = os.path.abspath(args.output_dir)
    for asset in ("StatusIndicator", "WindowMeter", "WindowPanel"):
        for theme_name in THEMES:
            render_asset(output_dir, asset, theme_name)


if __name__ == "__main__":
    main()
