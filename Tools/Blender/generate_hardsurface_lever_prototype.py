"""Generate a true hard-surface lever prototype for quality review."""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def material(name, color, metallic, roughness, emission=None):
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emission is not None:
        shader.inputs["Emission Color"].default_value = emission
        shader.inputs["Emission Strength"].default_value = 4.0
    else:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 58.0
        noise.inputs["Detail"].default_value = 3.0
        noise.inputs["Roughness"].default_value = 0.68
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.055
        bump.inputs["Distance"].default_value = 0.00045
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return result


def prism(name, outline, y_back, y_front, assigned_material):
    vertices = []
    for y in (y_back, y_front):
        vertices.extend((x, y, z) for x, z in outline)
    count = len(outline)
    faces = [
        tuple(range(count - 1, -1, -1)),
        tuple(range(count, count * 2)),
    ]
    for index in range(count):
        next_index = (index + 1) % count
        faces.append(
            (
                index,
                next_index,
                count + next_index,
                count + index,
            )
        )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    result = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(result)
    if assigned_material is not None:
        result.data.materials.append(assigned_material)
    return result


def chamfered_outline(width, height, chamfer, center_z=0.0):
    half_x = width * 0.5
    half_z = height * 0.5
    return [
        (-half_x + chamfer, center_z - half_z),
        (half_x - chamfer, center_z - half_z),
        (half_x, center_z - half_z + chamfer),
        (half_x, center_z + half_z - chamfer),
        (half_x - chamfer, center_z + half_z),
        (-half_x + chamfer, center_z + half_z),
        (-half_x, center_z + half_z - chamfer),
        (-half_x, center_z - half_z + chamfer),
    ]


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def boolean(target, cutter, operation, name):
    activate(target)
    modifier = target.modifiers.new(name, "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def bevel(obj, width, segments):
    activate(obj)
    modifier = obj.modifiers.new("Production Bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(18)
    modifier.miter_outer = "MITER_ARC"
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.ops.object.shade_smooth_by_angle()


def cylinder(
    name,
    radius,
    depth,
    location,
    assigned_material,
    vertices,
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type="NGON",
        location=location,
        rotation=(math.pi * 0.5, 0.0, 0.0),
    )
    result = bpy.context.object
    result.name = name
    if assigned_material is not None:
        result.data.materials.append(assigned_material)
    return result


def cylinder_x(
    name,
    radius,
    depth,
    location,
    assigned_material,
    vertices,
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type="NGON",
        location=location,
        rotation=(0.0, math.pi * 0.5, 0.0),
    )
    result = bpy.context.object
    result.name = name
    if assigned_material is not None:
        result.data.materials.append(assigned_material)
    return result


def cone_cutter(name, radius_outer, radius_inner, depth, x, y, z):
    bpy.ops.mesh.primitive_cone_add(
        vertices=32,
        radius1=radius_outer,
        radius2=radius_inner,
        depth=depth,
        end_fill_type="NGON",
        location=(x, y, z),
        rotation=(math.pi * 0.5, 0.0, 0.0),
    )
    result = bpy.context.object
    result.name = name
    return result


def cube_cutter(name, dimensions, location, rotation_y=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    result = bpy.context.object
    result.name = name
    result.dimensions = dimensions
    result.rotation_euler[1] = rotation_y
    activate(result)
    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )
    return result


def build_shell(graphite, gunmetal, cyan, high_poly):
    segments = 5 if high_poly else 2
    housing = prism(
        "housing",
        chamfered_outline(0.18, 0.14, 0.012),
        0.0,
        -0.050,
        graphite,
    )

    shoulder_outline = chamfered_outline(
        0.043,
        0.103,
        0.008,
    )
    for x in (-0.062, 0.062):
        shoulder = prism(
            "shoulder_union",
            [(px + x, pz) for px, pz in shoulder_outline],
            -0.036,
            -0.066,
            graphite,
        )
        boolean(housing, shoulder, "UNION", "Shoulder Union")

    recess = prism(
        "central_recess_cutter",
        chamfered_outline(0.084, 0.112, 0.009, 0.004),
        -0.039,
        -0.058,
        None,
    )
    boolean(housing, recess, "DIFFERENCE", "Central Recess")

    for row, z in enumerate((-0.044, -0.012, 0.020, 0.052)):
        cutter = cube_cutter(
            f"vent_cutter_{row}",
            (0.024, 0.020, 0.006),
            (0.063, -0.057, z),
            math.radians(-8),
        )
        boolean(housing, cutter, "DIFFERENCE", "Vent Slot")

    boss = cylinder_x(
        "trunnion_housing_union",
        0.022,
        0.074,
        (0.0, -0.057, -0.025),
        gunmetal,
        48 if high_poly else 24,
    )
    boolean(housing, boss, "UNION", "Trunnion Housing Union")
    bore = cylinder_x(
        "trunnion_bore_cutter",
        0.0115,
        0.090,
        (0.0, -0.057, -0.025),
        None,
        48 if high_poly else 24,
    )
    boolean(housing, bore, "DIFFERENCE", "Trunnion Bore")

    for index, (x, z) in enumerate(
        ((-0.073, -0.050), (0.073, -0.050),
         (-0.073, 0.050), (0.073, 0.050))
    ):
        countersink = cone_cutter(
            f"fastener_countersink_{index}",
            0.0065,
            0.0030,
            0.014,
            x,
            -0.047,
            z,
        )
        boolean(
            housing,
            countersink,
            "DIFFERENCE",
            "Countersunk Fastener",
        )

    bevel(
        housing,
        0.0038 if high_poly else 0.0028,
        segments,
    )

    insert = prism(
        "recess_insert",
        chamfered_outline(0.074, 0.102, 0.007, 0.004),
        -0.052,
        -0.058,
        gunmetal,
    )
    bevel(insert, 0.0018, 3 if high_poly else 1)
    fasteners = []
    for index, (x, z) in enumerate(
        ((-0.073, -0.050), (0.073, -0.050),
         (-0.073, 0.050), (0.073, 0.050))
    ):
        fastener = cylinder(
            f"fastener_head_{index}",
            0.0032,
            0.0024,
            (x, -0.055, z),
            gunmetal,
            24 if high_poly else 12,
        )
        bevel(fastener, 0.0005, 2 if high_poly else 1)
        fasteners.append(fastener)
    insert = common.join_objects(
        [insert] + fasteners,
        "recess_insert",
    )

    accent_parts = []
    for index, z in enumerate((-0.044, -0.012, 0.020, 0.052)):
        accent = prism(
            f"detent_light_{index}",
            chamfered_outline(0.018, 0.0045, 0.0015, z),
            -0.067,
            -0.071,
            cyan,
        )
        accent.location.x = 0.061
        accent_parts.append(accent)
    axis_witness = prism(
        "axis_witness_light",
        chamfered_outline(
            0.070,
            0.0045,
            0.0015,
            -0.025,
        ),
        -0.071,
        -0.074,
        cyan,
    )
    accent_parts.append(axis_witness)
    accents = common.join_objects(accent_parts, "housing_accents")
    return housing, insert, accents


def build_handle(graphite, gunmetal, cyan, high_poly):
    segments = 5 if high_poly else 2
    pivot_point = (0.0, -0.074, -0.025)
    shaft = controls.add_vertical_cylinder(
        "lever_shaft",
        0.0085,
        0.137,
        (0.0, pivot_point[1], 0.0435),
        32 if high_poly else 16,
        gunmetal,
        (0.625, 0.125),
    )
    bevel(shaft, 0.0008, 3 if high_poly else 1)

    grip_outline = [
        (-0.017, 0.092),
        (-0.024, 0.104),
        (-0.026, 0.151),
        (-0.019, 0.169),
        (0.019, 0.169),
        (0.026, 0.151),
        (0.024, 0.104),
        (0.017, 0.092),
    ]
    grip = prism(
        "palm_grip",
        grip_outline,
        -0.054,
        -0.094,
        graphite,
    )
    front_recess = prism(
        "grip_recess_cutter",
        chamfered_outline(0.027, 0.043, 0.006, 0.135),
        -0.092,
        -0.101,
        None,
    )
    boolean(grip, front_recess, "DIFFERENCE", "Grip Front Recess")
    for z in (0.111, 0.135, 0.159):
        side_groove = cube_cutter(
            "grip_side_groove",
            (0.060, 0.012, 0.0045),
            (0.0, -0.074, z),
        )
        boolean(grip, side_groove, "DIFFERENCE", "Grip Side Groove")
    bevel(grip, 0.0048 if high_poly else 0.0035, segments)

    axle = cylinder_x(
        "trunnion_axle",
        0.0105,
        0.068,
        (0.0, -0.057, -0.025),
        gunmetal,
        48 if high_poly else 24,
    )
    bevel(axle, 0.0013, 3 if high_poly else 1)
    handle = common.join_objects([shaft, grip, axle], "handle")

    grip_light = prism(
        "grip_light",
        chamfered_outline(0.025, 0.008, 0.002, 0.142),
        -0.095,
        -0.099,
        cyan,
    )
    handle.data.materials.append(cyan)
    combined = common.join_objects([handle, grip_light], "handle")
    pivot, combined = controls.parent_at_pivot(
        [combined],
        "handle",
        pivot_point,
        None,
    )
    pivot.name = "handle_pivot"
    combined.name = "handle"
    return pivot, combined


def build_model(high_poly):
    common.clean_scene()
    graphite = material(
        "MAT_HS_Graphite",
        (0.018, 0.026, 0.038, 1.0),
        0.62,
        0.40,
    )
    gunmetal = material(
        "MAT_HS_Gunmetal",
        (0.11, 0.15, 0.18, 1.0),
        0.88,
        0.28,
    )
    cyan = material(
        "MAT_HS_Cyan",
        (0.04, 0.40, 0.54, 1.0),
        0.18,
        0.22,
        emission=(0.08, 0.78, 1.0, 1.0),
    )
    root = bpy.data.objects.new(
        "PF_Visual_Lever_KineticSafety_HS_V2",
        None,
    )
    root["instrument_type_id"] = "control.lever"
    root["theme_id"] = "kinetic-safety"
    root["unity_mount_axis"] = "+Z"
    root["modeling_method"] = (
        "continuous hard-surface shell; exact booleans; "
        "production bevels; baked-ready high/low pair"
    )
    bpy.context.collection.objects.link(root)
    housing, insert, accents = build_shell(
        graphite,
        gunmetal,
        cyan,
        high_poly,
    )
    for obj in (housing, insert, accents):
        obj.parent = root
    pivot, handle = build_handle(
        graphite,
        gunmetal,
        cyan,
        high_poly,
    )
    pivot.parent = root
    return root, [housing, insert, accents, handle]


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def stats(meshes):
    common.apply_transforms(meshes)
    result = common.mesh_stats(meshes)
    result["modeling_method"] = "hard-surface high/low prototype"
    result["boolean_features"] = 11
    result["bevel_hierarchy_m"] = [0.0048, 0.0038, 0.0018, 0.0008]
    result["weighted_surface_shading"] = True
    return result


def main():
    args = parse_args()
    root_dir = Path(args.project_root).resolve()
    source_dir = (
        root_dir
        / "ArtSource/Blender/HardSurfacePrototype/KineticSafety"
    )
    model_dir = (
        root_dir
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/"
        "KineticSafety/HardSurfacePrototype"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    high_root, high_meshes = build_model(high_poly=True)
    controls.create_preview(
        high_meshes,
        0.050,
        source_dir / "Preview_Lever_KineticSafety_HS_V2_High.png",
    )
    high_stats = stats(high_meshes)
    save_blend(source_dir / "BL_Lever_KineticSafety_HS_V2_High.blend")

    low_root, low_meshes = build_model(high_poly=False)
    controls.create_preview(
        low_meshes,
        0.050,
        source_dir / "Preview_Lever_KineticSafety_HS_V2_Low.png",
    )
    low_stats = stats(low_meshes)
    save_blend(source_dir / "BL_Lever_KineticSafety_HS_V2_Low.blend")
    fbx_path = model_dir / "SM_Lever_KineticSafety_HS_V2.fbx"
    fbm_path = fbx_path.with_suffix(".fbm")
    if fbm_path.exists():
        shutil.rmtree(fbm_path)
    common.export_fbx(low_root, fbx_path)

    report = {
        "asset": "Lever_KineticSafety_HS_V2",
        "high": high_stats,
        "low": low_stats,
        "fbx": str(fbx_path.relative_to(root_dir)),
        "production_integrated": False,
    }
    (source_dir / "Lever_KineticSafety_HS_V2.report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
