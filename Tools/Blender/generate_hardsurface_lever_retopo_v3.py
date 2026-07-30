"""Generate a clean retopologized low-poly cage for the HS lever."""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_hardsurface_lever_prototype as hs
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def mesh_object(name, vertices, faces, assigned_material):
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    result = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(result)
    if assigned_material is not None:
        result.data.materials.append(assigned_material)
    return result


def clean_prism(name, outline, y_back, y_front, assigned_material):
    count = len(outline)
    center_x = sum(x for x, _ in outline) / count
    center_z = sum(z for _, z in outline) / count
    vertices = []
    for y in (y_back, y_front):
        vertices.extend((x, y, z) for x, z in outline)
    vertices.extend(
        (
            (center_x, y_back, center_z),
            (center_x, y_front, center_z),
        )
    )
    back_center = count * 2
    front_center = back_center + 1
    faces = []
    for index in range(count):
        next_index = (index + 1) % count
        faces.extend(
            (
                (index, next_index, count + next_index, count + index),
                (back_center, next_index, index),
                (front_center, count + index, count + next_index),
            )
        )
    return mesh_object(name, vertices, faces, assigned_material)


def recessed_shell(
    name,
    outer,
    inner,
    y_back,
    y_front,
    y_recess,
    assigned_material,
):
    count = len(outer)
    if len(inner) != count:
        raise ValueError("Outer and inner loops must have equal vertex counts.")
    vertices = []
    vertices.extend((x, y_back, z) for x, z in outer)
    vertices.extend((x, y_front, z) for x, z in outer)
    vertices.extend((x, y_front, z) for x, z in inner)
    vertices.extend((x, y_recess, z) for x, z in inner)
    vertices.extend(
        (
            (0.0, y_back, 0.0),
            (0.0, y_recess, 0.004),
        )
    )
    outer_back = 0
    outer_front = count
    inner_front = count * 2
    inner_recess = count * 3
    back_center = count * 4
    recess_center = back_center + 1
    faces = []
    for index in range(count):
        next_index = (index + 1) % count
        faces.extend(
            (
                (
                    outer_back + index,
                    outer_back + next_index,
                    outer_front + next_index,
                    outer_front + index,
                ),
                (
                    outer_front + index,
                    outer_front + next_index,
                    inner_front + next_index,
                    inner_front + index,
                ),
                (
                    inner_front + index,
                    inner_front + next_index,
                    inner_recess + next_index,
                    inner_recess + index,
                ),
                (
                    back_center,
                    outer_back + next_index,
                    outer_back + index,
                ),
                (
                    recess_center,
                    inner_recess + index,
                    inner_recess + next_index,
                ),
            )
        )
    return mesh_object(name, vertices, faces, assigned_material)


def bevel(obj, width, segments=1):
    hs.activate(obj)
    modifier = obj.modifiers.new("Retopo Bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(24)
    modifier.miter_outer = "MITER_ARC"
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.ops.object.shade_smooth_by_angle()


def cylinder_x(name, radius, depth, location, assigned_material, vertices=16):
    return hs.cylinder_x(
        name,
        radius,
        depth,
        location,
        assigned_material,
        vertices,
    )


def cylinder_z(name, radius, depth, location, assigned_material, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        end_fill_type="TRIFAN",
        location=location,
    )
    result = bpy.context.object
    result.name = name
    if assigned_material is not None:
        result.data.materials.append(assigned_material)
    return result


def build_retopo():
    common.clean_scene()
    graphite = hs.material(
        "MAT_Retopo_Graphite",
        (0.018, 0.026, 0.038, 1.0),
        0.62,
        0.40,
    )
    gunmetal = hs.material(
        "MAT_Retopo_Gunmetal",
        (0.11, 0.15, 0.18, 1.0),
        0.88,
        0.28,
    )
    cyan = hs.material(
        "MAT_Retopo_Cyan",
        (0.04, 0.40, 0.54, 1.0),
        0.18,
        0.22,
        emission=(0.08, 0.78, 1.0, 1.0),
    )

    root = bpy.data.objects.new(
        "PF_Visual_Lever_KineticSafety_HS_V3",
        None,
    )
    root["instrument_type_id"] = "control.lever"
    root["theme_id"] = "kinetic-safety"
    root["unity_mount_axis"] = "+Z"
    root["modeling_method"] = "manual topology retopo cage"
    bpy.context.collection.objects.link(root)

    outer = hs.chamfered_outline(0.18, 0.14, 0.012)
    inner = hs.chamfered_outline(0.086, 0.112, 0.009, 0.004)
    housing = recessed_shell(
        "housing",
        outer,
        inner,
        0.0,
        -0.050,
        -0.041,
        graphite,
    )
    bevel(housing, 0.0028, 2)

    shoulders = []
    for x in (-0.062, 0.062):
        outline = [
            (px + x, pz)
            for px, pz in hs.chamfered_outline(
                0.040,
                0.100,
                0.007,
            )
        ]
        shoulder = clean_prism(
            "shoulder",
            outline,
            -0.044,
            -0.066,
            graphite,
        )
        bevel(shoulder, 0.0022, 1)
        shoulders.append(shoulder)

    trunnion_left = cylinder_x(
        "trunnion_left",
        0.020,
        0.024,
        (-0.025, -0.050, -0.025),
        gunmetal,
        20,
    )
    trunnion_right = cylinder_x(
        "trunnion_right",
        0.020,
        0.024,
        (0.025, -0.050, -0.025),
        gunmetal,
        20,
    )
    bevel(trunnion_left, 0.0012, 1)
    bevel(trunnion_right, 0.0012, 1)
    housing = common.join_objects(
        [housing] + shoulders + [trunnion_left, trunnion_right],
        "housing",
    )
    housing.parent = root

    insert = clean_prism(
        "recess_insert",
        hs.chamfered_outline(0.074, 0.102, 0.007, 0.004),
        -0.042,
        -0.047,
        gunmetal,
    )
    bevel(insert, 0.0015, 1)
    fasteners = []
    for index, (x, z) in enumerate(
        ((-0.073, -0.043), (0.073, -0.043),
         (-0.073, 0.043), (0.073, 0.043))
    ):
        fastener = hs.cylinder(
            f"fastener_{index}",
            0.0030,
            0.0022,
            (x, -0.053, z),
            gunmetal,
            10,
        )
        fasteners.append(fastener)
    insert = common.join_objects([insert] + fasteners, "recess_insert")
    insert.parent = root

    accents = []
    for index, z in enumerate((-0.044, -0.012, 0.020, 0.052)):
        accent = clean_prism(
            f"detent_light_{index}",
            hs.chamfered_outline(0.018, 0.0045, 0.0015, z),
            -0.064,
            -0.069,
            cyan,
        )
        accent.location.x = 0.061
        accents.append(accent)
    accents = common.join_objects(accents, "housing_accents")
    accents.parent = root

    # The pivot centre coincides with the housing's front face. This embeds
    # half of the axle cross-section in the armored bearing structure.
    pivot_point = (0.0, -0.050, -0.025)
    shaft = cylinder_z(
        "lever_shaft",
        0.0085,
        0.137,
        (0.0, pivot_point[1], 0.0435),
        gunmetal,
        16,
    )
    bevel(shaft, 0.0007, 1)
    axle = cylinder_x(
        "trunnion_axle",
        0.0120,
        0.080,
        pivot_point,
        gunmetal,
        20,
    )
    bevel(axle, 0.0008, 1)
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
    grip = clean_prism(
        "palm_grip",
        grip_outline,
        -0.054,
        -0.094,
        graphite,
    )
    bevel(grip, 0.0032, 2)
    grip_inset = clean_prism(
        "grip_inset",
        hs.chamfered_outline(0.027, 0.043, 0.006, 0.135),
        -0.094,
        -0.097,
        gunmetal,
    )
    bevel(grip_inset, 0.0010, 1)
    grip_light = clean_prism(
        "grip_light",
        hs.chamfered_outline(0.025, 0.008, 0.002, 0.142),
        -0.098,
        -0.101,
        cyan,
    )
    handle = common.join_objects(
        [shaft, axle, grip, grip_inset, grip_light],
        "handle",
    )
    pivot, handle = controls.parent_at_pivot(
        [handle],
        "handle",
        pivot_point,
        root,
    )
    pivot.name = "handle_pivot"
    handle.name = "handle"
    return root, [housing, insert, accents, handle]


def topology_stats(meshes):
    totals = {
        "vertices": 0,
        "edges": 0,
        "faces": 0,
        "triangles": 0,
        "quads": 0,
        "ngons": 0,
        "non_manifold_edges": 0,
        "zero_area_faces": 0,
    }
    for obj in meshes:
        mesh = obj.data
        totals["vertices"] += len(mesh.vertices)
        totals["edges"] += len(mesh.edges)
        totals["faces"] += len(mesh.polygons)
        for polygon in mesh.polygons:
            if polygon.loop_total == 3:
                totals["triangles"] += 1
            elif polygon.loop_total == 4:
                totals["quads"] += 1
            else:
                totals["ngons"] += 1
            if polygon.area <= 1e-12:
                totals["zero_area_faces"] += 1
        bm = bmesh.new()
        bm.from_mesh(mesh)
        totals["non_manifold_edges"] += sum(
            1 for edge in bm.edges if not edge.is_manifold
        )
        bm.free()
    return totals


def triangulate(meshes):
    for obj in meshes:
        hs.activate(obj)
        modifier = obj.modifiers.new("Deterministic Triangulation", "TRIANGULATE")
        modifier.quad_method = "BEAUTY"
        modifier.ngon_method = "BEAUTY"
        modifier.keep_custom_normals = True
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def render_topology_preview(meshes, output_path):
    wire_material = hs.material(
        "MAT_Topology_Wire",
        (0.005, 0.015, 0.020, 1.0),
        0.0,
        0.45,
        emission=(0.02, 0.70, 0.90, 1.0),
    )
    duplicates = []
    for source in meshes:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.name = f"{source.name}_topology"
        duplicate.parent = None
        duplicate.matrix_world = source.matrix_world.copy()
        duplicate.data.materials.clear()
        duplicate.data.materials.append(wire_material)
        bpy.context.collection.objects.link(duplicate)
        modifier = duplicate.modifiers.new(
            "Topology Wire",
            "WIREFRAME",
        )
        modifier.thickness = 0.00028
        modifier.use_even_offset = True
        duplicates.append(duplicate)
    controls.create_preview(
        meshes + duplicates,
        0.050,
        output_path,
    )
    for duplicate in duplicates:
        bpy.data.objects.remove(duplicate, do_unlink=True)


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    source_dir = (
        project_root
        / "ArtSource/Blender/HardSurfacePrototype/KineticSafety"
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/"
        "KineticSafety/HardSurfacePrototype"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    root, meshes = build_retopo()
    common.apply_transforms(meshes)
    source_stats = topology_stats(meshes)
    controls.create_preview(
        meshes,
        0.050,
        source_dir / "Preview_Lever_KineticSafety_HS_V3_Retopo.png",
    )
    render_topology_preview(
        meshes,
        source_dir /
        "Preview_Lever_KineticSafety_HS_V3_Topology.png",
    )
    save_blend(
        source_dir / "BL_Lever_KineticSafety_HS_V3_Retopo.blend"
    )

    triangulate(meshes)
    triangulated_stats = topology_stats(meshes)
    if triangulated_stats["non_manifold_edges"] != 0:
        raise RuntimeError(
            f"Non-manifold result: {triangulated_stats}"
        )
    if triangulated_stats["zero_area_faces"] != 0:
        raise RuntimeError(
            f"Degenerate result: {triangulated_stats}"
        )
    if triangulated_stats["faces"] > 5000:
        raise RuntimeError(
            f"Triangle target exceeded: {triangulated_stats}"
        )
    save_blend(
        source_dir / "BL_Lever_KineticSafety_HS_V3_Triangulated.blend"
    )
    fbx_path = model_dir / "SM_Lever_KineticSafety_HS_V3_Retopo.fbx"
    fbm_path = fbx_path.with_suffix(".fbm")
    if fbm_path.exists():
        shutil.rmtree(fbm_path)
    common.export_fbx(root, fbx_path)

    report = {
        "asset": "Lever_KineticSafety_HS_V3_Retopo",
        "source_topology": source_stats,
        "triangulated_topology": triangulated_stats,
        "pivot": {
            "position": [0.0, -0.050, -0.025],
            "local_axis": [1.0, 0.0, 0.0],
        },
        "fbx": str(fbx_path.relative_to(project_root)),
        "production_integrated": False,
    }
    (
        source_dir / "Lever_KineticSafety_HS_V3_Retopo.report.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
