"""Generate the Orbital Analog round-meter Blender pilot and Unity FBX.

Run from the repository root:
  blender --background --factory-startup \
    --python Tools/Blender/generate_orbital_analog_meter.py -- \
    --project-root "$PWD"

Blender authoring axes follow the conventional Z-up workflow:
  X = right, Z = up, -Y = outward from the mounting plane.
The FBX export converts them to Unity:
  X = right, Y = up, +Z = outward.
"""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ASSET_NAME = "MeterRound_OrbitalAnalog"
ROOT_NAME = "PF_Visual_MeterRound_OrbitalAnalog"
ATLAS_SIZE = 1024
PIVOT_DEPTH = 0.041


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def save_rgba_image(name, pixels, path, colorspace="sRGB"):
    image = bpy.data.images.new(
        name,
        width=ATLAS_SIZE,
        height=ATLAS_SIZE,
        alpha=True,
        float_buffer=False,
    )
    image.colorspace_settings.name = colorspace
    image.pixels.foreach_set(pixels.astype(np.float32).ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    return image


def build_texture_atlas(texture_dir):
    size = ATLAS_SIZE
    base = np.zeros((size, size, 4), dtype=np.float32)
    base[:, :, :] = (0.018, 0.022, 0.026, 1.0)
    base[0:256, 256:512, :] = (0.78, 0.36, 0.055, 1.0)
    base[0:256, 512:768, :] = (0.20, 0.16, 0.095, 1.0)
    base[0:256, 768:1024, :] = (0.58, 0.54, 0.39, 1.0)

    yy, xx = np.ogrid[:size, :size]
    cx = cy = 768
    dx = xx - cx
    dy = yy - cy
    radius = np.sqrt(dx * dx + dy * dy)
    dial = radius <= 238
    base[dial] = (0.014, 0.019, 0.022, 1.0)
    base[(radius >= 225) & (radius <= 238)] = (0.22, 0.17, 0.09, 1.0)

    tick_mask = np.zeros((size, size), dtype=bool)
    start = math.radians(220)
    end = math.radians(-40)
    for index in range(41):
        t = index / 40
        angle = start + (end - start) * t
        outer = 214
        inner = 178 if index % 5 == 0 else 197
        samples = max(2, outer - inner)
        for radial in np.linspace(inner, outer, samples):
            px = int(round(cx + math.cos(angle) * radial))
            py = int(round(cy + math.sin(angle) * radial))
            thickness = 2 if index % 5 == 0 else 1
            tick_mask[
                max(0, py - thickness) : min(size, py + thickness + 1),
                max(0, px - thickness) : min(size, px + thickness + 1),
            ] = True
    arc_mask = np.zeros((size, size), dtype=bool)
    angle_field = np.arctan2(dy, dx)
    normalized_angle = np.mod(angle_field - end, math.pi * 2)
    active_arc = normalized_angle <= np.mod(start - end, math.pi * 2)
    arc_mask |= (radius >= 158) & (radius <= 160) & active_arc
    arc_mask |= (radius >= 143) & (radius <= 144) & active_arc

    highlight_mask = (
        dial
        & (dx + dy > 90)
        & (dx + dy < 125)
        & (radius > 55)
    )
    base[highlight_mask] = (0.030, 0.038, 0.041, 1.0)
    base[arc_mask] = (0.36, 0.31, 0.18, 1.0)
    base[tick_mask] = (0.78, 0.70, 0.43, 1.0)

    emission = np.zeros_like(base)
    emission[:, :, 3] = 1.0
    emission[arc_mask] = (0.12, 0.085, 0.025, 1.0)
    emission[tick_mask] = (0.52, 0.37, 0.09, 1.0)
    emission[0:256, 256:512, :] = (0.30, 0.105, 0.01, 1.0)

    normal = np.zeros_like(base)
    normal[:, :, :] = (0.5, 0.5, 1.0, 1.0)

    mask = np.zeros_like(base)
    mask[:, :, :] = (0.76, 0.0, 0.0, 0.26)
    mask[dial] = (0.0, 0.0, 0.0, 0.20)
    mask[0:256, 256:512, :] = (0.42, 0.0, 0.0, 0.30)

    paths = {
        "base_color": texture_dir / "T_OrbitalAnalog_Atlas_BaseColor.png",
        "normal": texture_dir / "T_OrbitalAnalog_Atlas_Normal.png",
        "metallic_smoothness": (
            texture_dir / "T_OrbitalAnalog_Atlas_MetallicSmoothness.png"
        ),
        "emission": texture_dir / "T_OrbitalAnalog_Atlas_Emission.png",
    }
    images = {
        "base_color": save_rgba_image(
            "T_OrbitalAnalog_Atlas_BaseColor", base, paths["base_color"]
        ),
        "normal": save_rgba_image(
            "T_OrbitalAnalog_Atlas_Normal", normal, paths["normal"], "Non-Color"
        ),
        "metallic_smoothness": save_rgba_image(
            "T_OrbitalAnalog_Atlas_MetallicSmoothness",
            mask,
            paths["metallic_smoothness"],
            "Non-Color",
        ),
        "emission": save_rgba_image(
            "T_OrbitalAnalog_Atlas_Emission",
            emission,
            paths["emission"],
            "Non-Color",
        ),
    }
    return paths, images


def create_material(base_image):
    material = bpy.data.materials.new("MAT_OrbitalAnalog_Atlas")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    coordinates = nodes.new("ShaderNodeUVMap")
    coordinates.uv_map = "UVMap"
    texture.image = base_image
    texture.interpolation = "Linear"
    shader.inputs["Metallic"].default_value = 0.35
    shader.inputs["Roughness"].default_value = 0.54
    links.new(coordinates.outputs["UV"], texture.inputs["Vector"])
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def create_emissive_material(base_image):
    material = bpy.data.materials.new("MAT_OrbitalAnalog_Emissive")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texture = nodes.new("ShaderNodeTexImage")
    coordinates = nodes.new("ShaderNodeUVMap")
    coordinates.uv_map = "UVMap"
    texture.image = base_image
    texture.interpolation = "Linear"
    shader.inputs["Metallic"].default_value = 0.20
    shader.inputs["Roughness"].default_value = 0.45
    emission_color = shader.inputs.get("Emission Color")
    emission_strength = shader.inputs.get("Emission Strength")
    links.new(coordinates.outputs["UV"], texture.inputs["Vector"])
    links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    if emission_color is not None:
        links.new(texture.outputs["Color"], emission_color)
    if emission_strength is not None:
        emission_strength.default_value = 0.55
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def apply_bevel(obj, width):
    modifier = obj.modifiers.new("Edge Softening", "BEVEL")
    modifier.width = width
    modifier.segments = 1
    modifier.limit_method = "ANGLE"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def set_constant_uv(obj, point):
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active.data
    for loop in uv_layer:
        loop.uv = point


def remap_uv(obj, offset, scale):
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active.data
    for loop in uv_layer:
        loop.uv = (
            offset[0] + loop.uv.x * scale[0],
            offset[1] + loop.uv.y * scale[1],
        )


def map_cylinder_cap_uv(obj, radius):
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv_layer = mesh.uv_layers.active.data
    for polygon in mesh.polygons:
        if abs(polygon.normal.z) > 0.9:
            for loop_index in polygon.loop_indices:
                vertex = mesh.vertices[mesh.loops[loop_index].vertex_index]
                uv_layer[loop_index].uv = (
                    0.75 + (vertex.co.x / radius) * 0.235,
                    0.75 + (vertex.co.y / radius) * 0.235,
                )
        else:
            for loop_index in polygon.loop_indices:
                uv_layer[loop_index].uv = (0.875, 0.875)


def add_cylinder(
    name,
    radius,
    depth,
    outward_depth,
    vertices,
    material,
    fill_type="NGON",
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type=fill_type,
        location=(0.0, -outward_depth, 0.0),
        rotation=(math.radians(90), 0.0, 0.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def add_torus(name, major_radius, minor_radius, outward_depth, material):
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        major_segments=24,
        minor_segments=4,
        location=(0.0, -outward_depth, 0.0),
        rotation=(math.radians(90), 0.0, 0.0),
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def add_annulus(
    name,
    outer_radius,
    inner_radius,
    depth,
    outward_depth,
    segments,
    material,
):
    front_y = -outward_depth - depth * 0.5
    back_y = -outward_depth + depth * 0.5
    vertices = []
    faces = []
    for index in range(segments):
        angle = math.pi * 2 * index / segments
        cosine = math.cos(angle)
        sine = math.sin(angle)
        vertices.extend(
            (
                (outer_radius * cosine, front_y, outer_radius * sine),
                (outer_radius * cosine, back_y, outer_radius * sine),
                (inner_radius * cosine, front_y, inner_radius * sine),
                (inner_radius * cosine, back_y, inner_radius * sine),
            )
        )
    for index in range(segments):
        current = index * 4
        following = ((index + 1) % segments) * 4
        faces.extend(
            (
                (current, following, following + 1, current + 1),
                (current + 2, current + 3, following + 3, following + 2),
                (current, current + 2, following + 2, following),
                (current + 1, following + 1, following + 3, current + 3),
            )
        )
    mesh = bpy.data.meshes.new(f"ME_{name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(material)
    bpy.context.collection.objects.link(obj)
    return obj


def join_objects(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = name
    joined.data.name = f"ME_{name}"
    return joined


def build_meter(material, emissive_material):
    root = bpy.data.objects.new(ROOT_NAME, None)
    root.empty_display_type = "PLAIN_AXES"
    root["instrument_type_id"] = "meter.round"
    root["theme_id"] = "orbital-analog"
    root["unity_mount_axis"] = "+Z"
    bpy.context.collection.objects.link(root)

    housing_parts = []
    back = add_cylinder("housing_back", 0.070, 0.026, 0.013, 32, material)
    apply_bevel(back, 0.0013)
    set_constant_uv(back, (0.125, 0.125))
    housing_parts.append(back)

    rim_base = add_annulus(
        "housing_rim_base",
        outer_radius=0.063,
        inner_radius=0.056,
        depth=0.012,
        outward_depth=0.032,
        segments=32,
        material=material,
    )
    set_constant_uv(rim_base, (0.125, 0.125))
    housing_parts.append(rim_base)

    torus = add_torus("housing_bezel", 0.0585, 0.0042, 0.039, material)
    set_constant_uv(torus, (0.625, 0.125))
    housing_parts.append(torus)

    for x, z in ((-0.048, -0.048), (0.048, -0.048), (-0.048, 0.048), (0.048, 0.048)):
        screw = add_cylinder(
            "housing_screw",
            0.0031,
            0.0022,
            0.0282,
            8,
            material,
        )
        screw.location.x = x
        screw.location.z = z
        apply_bevel(screw, 0.00035)
        set_constant_uv(screw, (0.625, 0.125))
        housing_parts.append(screw)

    housing = join_objects(housing_parts, "housing")
    housing.parent = root

    dial = add_cylinder(
        "dial",
        0.0545,
        0.0028,
        0.0335,
        32,
        material,
        fill_type="TRIFAN",
    )
    map_cylinder_cap_uv(dial, 0.0545)
    dial.parent = root

    pivot = bpy.data.objects.new("needle_pivot", None)
    pivot.empty_display_type = "ARROWS"
    pivot.empty_display_size = 0.012
    pivot.location = (0.0, -PIVOT_DEPTH, 0.0)
    pivot.parent = root
    bpy.context.collection.objects.link(pivot)

    bpy.ops.mesh.primitive_cube_add(
        location=(0.0, -PIVOT_DEPTH, 0.019),
        scale=(0.0018, 0.00075, 0.024),
    )
    blade = bpy.context.object
    blade.name = "needle_blade"
    blade.data.materials.append(emissive_material)
    apply_bevel(blade, 0.00045)
    set_constant_uv(blade, (0.375, 0.125))

    hub = add_cylinder(
        "needle_hub",
        0.007,
        0.0032,
        PIVOT_DEPTH + 0.0002,
        16,
        emissive_material,
    )
    set_constant_uv(hub, (0.375, 0.125))

    needle = join_objects([blade, hub], "needle")
    bpy.context.scene.cursor.location = (0.0, -PIVOT_DEPTH, 0.0)
    bpy.context.view_layer.objects.active = needle
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    world_matrix = needle.matrix_world.copy()
    needle.parent = pivot
    needle.matrix_world = world_matrix

    for obj in (housing, dial, needle):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_smooth_by_angle()
        obj.select_set(False)

    return root, housing, dial, pivot, needle


def apply_transforms(mesh_objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.select_all(action="DESELECT")


def mesh_stats(mesh_objects):
    triangles = 0
    for obj in mesh_objects:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()

    points = []
    for obj in mesh_objects:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    min_point = Vector(
        (
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        )
    )
    max_point = Vector(
        (
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        )
    )
    # Convert Blender X/Z/-Y envelope to Unity X/Y/Z.
    unity_size = (
        max_point.x - min_point.x,
        max_point.z - min_point.z,
        max_point.y - min_point.y,
    )
    return {
        "triangles": triangles,
        "mesh_objects": len(mesh_objects),
        "materials": len(
            {
                slot.material.name
                for obj in mesh_objects
                for slot in obj.material_slots
                if slot.material is not None
            }
        ),
        "material_slots": sum(len(obj.material_slots) for obj in mesh_objects),
        "unity_bounds_m": [round(value, 6) for value in unity_size],
        "blender_bounds_min_m": [round(value, 6) for value in min_point],
        "blender_bounds_max_m": [round(value, 6) for value in max_point],
    }


def create_preview(material, output_path):
    bpy.ops.object.camera_add(location=(0.105, -0.29, 0.085))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.data.lens = 58

    def point_at(obj, target):
        direction = Vector(target) - obj.location
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    point_at(camera, (0.0, -0.025, 0.0))
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("Key", (0.16, -0.20, 0.20), 5.5, 0.18),
        ("Fill", (-0.16, -0.10, 0.08), 2.2, 0.16),
        ("Rim", (0.02, 0.04, 0.18), 3.5, 0.12),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        light.location = location
        bpy.context.collection.objects.link(light)
        point_at(light, (0.0, -0.025, 0.0))

    world = bpy.context.scene.world
    world.color = (0.012, 0.016, 0.022)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output_path)
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.ops.render.render(write_still=True)

    for obj in [camera] + [bpy.data.objects.get(name) for name in ("Key", "Fill", "Rim")]:
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)


def export_fbx(root, output_path):
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(
        filepath=str(output_path),
        use_selection=True,
        object_types={"EMPTY", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        use_space_transform=True,
        bake_space_transform=False,
        axis_forward="-Z",
        axis_up="Y",
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_triangles=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="STRIP",
        embed_textures=False,
    )


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    source_dir = project_root / "ArtSource/Blender/OrbitalAnalog"
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models"
    )
    texture_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Textures"
    )
    for directory in (source_dir, model_dir, texture_dir):
        directory.mkdir(parents=True, exist_ok=True)

    clean_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    texture_paths, images = build_texture_atlas(texture_dir)
    material = create_material(images["base_color"])
    emissive_material = create_emissive_material(images["base_color"])
    root, housing, dial, pivot, needle = build_meter(material, emissive_material)
    mesh_objects = [housing, dial, needle]
    apply_transforms(mesh_objects)

    stats = mesh_stats(mesh_objects)
    stats.update(
        {
            "asset": ASSET_NAME,
            "instrument_type_id": "meter.round",
            "theme_id": "orbital-analog",
            "unity_mount_axis": "+Z",
            "unity_needle_axis": "+Z",
            "needle_range_degrees": [-55, 55],
            "greybox_triangle_budget": 1500,
            "final_triangle_budget": 5000,
            "renderer_budget": 4,
            "material_budget": 2,
            "colliders": 0,
            "realtime_lights": 0,
            "textures": {key: str(path.relative_to(project_root)) for key, path in texture_paths.items()},
        }
    )

    if stats["triangles"] > stats["greybox_triangle_budget"]:
        raise RuntimeError(f"Triangle budget exceeded: {stats['triangles']}")
    if stats["mesh_objects"] > stats["renderer_budget"]:
        raise RuntimeError(f"Renderer budget exceeded: {stats['mesh_objects']}")
    if stats["materials"] > stats["material_budget"]:
        raise RuntimeError(f"Material budget exceeded: {stats['materials']}")
    bounds = stats["unity_bounds_m"]
    limits = (0.14001, 0.14001, 0.06401)
    if any(value > limit for value, limit in zip(bounds, limits)):
        raise RuntimeError(f"Bounds exceeded: {bounds}")

    preview_path = source_dir / "Preview_MeterRound_OrbitalAnalog.png"
    create_preview(material, preview_path)

    blend_path = source_dir / "BL_MeterRound_OrbitalAnalog.blend"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    backup_path = blend_path.with_suffix(".blend1")
    if backup_path.exists():
        backup_path.unlink()

    fbx_path = model_dir / "SM_MeterRound_OrbitalAnalog.fbx"
    copied_texture_dir = model_dir / "SM_MeterRound_OrbitalAnalog.fbm"
    if copied_texture_dir.exists():
        shutil.rmtree(copied_texture_dir)
    export_fbx(root, fbx_path)

    report_path = source_dir / "BL_MeterRound_OrbitalAnalog.report.json"
    report_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
