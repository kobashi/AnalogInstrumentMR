"""Generate the V5 grayscale theme-silhouette study.

This pass deliberately shares only envelopes, mount plane and pivot contracts.
Visible geometry is authored independently for each theme.
"""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_hardsurface_kinetic_set_v4 as v4
import generate_hardsurface_lever_retopo_v3 as retopo
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


THEMES = {
    "OrbitalAnalog": "orbital-analog",
    "ForgeBrass": "forge-brass",
    "KineticSafety": "kinetic-safety",
}
ASSETS = {
    "MeterRound": ("meter.round", 5000),
    "Lever": ("control.lever", 5000),
    "WindowPanel": ("panel.window", 25000),
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-topology", action="store_true")
    return parser.parse_args(args)


def grayscale_material(name, value, metallic, roughness, emission=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (value, value, value, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (
        value,
        value,
        value,
        1.0,
    )
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emission > 0.0:
        shader.inputs["Emission Color"].default_value = (
            value,
            value,
            value,
            1.0,
        )
        shader.inputs["Emission Strength"].default_value = emission
    return material


def materials(theme):
    return {
        "body": grayscale_material(
            f"MAT_{theme}_V5_Body",
            0.105,
            0.58,
            0.48,
        ),
        "metal": grayscale_material(
            f"MAT_{theme}_V5_Metal",
            0.32,
            0.88,
            0.23,
        ),
        "readout": grayscale_material(
            f"MAT_{theme}_V5_Readout",
            0.78,
            0.16,
            0.20,
            1.2,
        ),
    }


def root_for(theme, key, type_id):
    root = bpy.data.objects.new(
        f"PF_Visual_{key}_{theme}_V5",
        None,
    )
    root["instrument_type_id"] = type_id
    root["theme_id"] = THEMES[theme]
    root["unity_mount_axis"] = "+Z"
    root["art_pass"] = "V5 grayscale silhouette study"
    root["shared_visible_geometry"] = False
    bpy.context.collection.objects.link(root)
    return root


def attach(root, objects, name):
    result = common.join_objects(objects, name)
    result.parent = root
    return result


def sphere(name, radius, location, material, segments=16, rings=8):
    return controls.add_sphere(
        name,
        radius,
        location,
        material,
        (0.125, 0.125),
        segments,
        rings,
    )


def meter_needle(root, mats, pivot_point, length, width):
    needle = v4.prism(
        "needle",
        width,
        length,
        min(width * 0.28, 0.002),
        pivot_point[1],
        pivot_point[1] - 0.004,
        mats["readout"],
        pivot_point[2] + length * 0.45,
    )
    hub = v4.cylinder_y(
        "needle_hub",
        width * 2.4,
        0.007,
        abs(pivot_point[1]),
        mats["metal"],
        16,
    )
    hub.location.z = pivot_point[2]
    pivot, movable = v4.parent_movable(
        [needle, hub],
        "needle",
        pivot_point,
        root,
    )
    pivot.name = "needle_pivot"
    movable.name = "needle"
    return pivot


def build_orbital_meter():
    theme = "OrbitalAnalog"
    mats = materials(theme)
    root = root_for(theme, "MeterRound", "meter.round")
    body = v4.prism(
        "orbital_thin_console",
        0.154,
        0.112,
        0.010,
        0.0,
        -0.024,
        mats["body"],
    )
    upper = v4.prism(
        "orbital_upper_brow",
        0.112,
        0.018,
        0.005,
        -0.022,
        -0.037,
        mats["metal"],
        0.053,
    )
    lower = v4.prism(
        "orbital_lower_pedestal",
        0.084,
        0.016,
        0.005,
        -0.022,
        -0.039,
        mats["metal"],
        -0.055,
    )
    for x in (-0.074, 0.074):
        wing = v4.prism(
            "orbital_side_wing",
            0.014,
            0.074,
            0.004,
            -0.020,
            -0.036,
            mats["metal"],
        )
        wing.location.x = x
        body = attach(root, [body, wing], "housing")
    attach(root, [body, upper, lower], "housing")
    bezel = v4.cylinder_y(
        "orbital_deep_bezel",
        0.054,
        0.018,
        0.030,
        mats["metal"],
        28,
    )
    dial = v4.cylinder_y(
        "orbital_dial",
        0.045,
        0.005,
        0.048,
        mats["body"],
        32,
    )
    attach(root, [bezel, dial], "dial")
    for index in range(17):
        angle = math.radians(-125 + index * (250 / 16))
        tick = v4.accent_bar(
            f"orbital_tick_{index}",
            0.0012 if index % 4 else 0.0020,
            0.005 if index % 4 else 0.009,
            math.sin(angle) * 0.039,
            math.cos(angle) * 0.039,
            0.050,
            mats["readout"],
        )
        tick.rotation_euler.y = angle
        tick.parent = root
    pivot_point = (0.0, -0.051, -0.004)
    meter_needle(root, mats, pivot_point, 0.040, 0.0028)
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_forge_meter():
    theme = "ForgeBrass"
    mats = materials(theme)
    root = root_for(theme, "MeterRound", "meter.round")
    body = v4.cylinder_y(
        "forge_cast_body",
        0.071,
        0.040,
        0.021,
        mats["body"],
        28,
    )
    rim_outer = v4.cylinder_y(
        "forge_stepped_rim",
        0.063,
        0.014,
        0.054,
        mats["metal"],
        28,
    )
    rim_inner = v4.cylinder_y(
        "forge_glass_retainer",
        0.052,
        0.007,
        0.068,
        mats["body"],
        32,
    )
    parts = [body, rim_outer, rim_inner]
    for x in (-0.048, 0.048):
        foot = v4.prism(
            "forge_mount_foot",
            0.026,
            0.030,
            0.007,
            0.0,
            -0.035,
            mats["body"],
            -0.065,
        )
        foot.location.x = x
        parts.append(foot)
    crown = v4.cylinder_z(
        "forge_pressure_union",
        0.012,
        0.028,
        (0.0, -0.021, 0.076),
        mats["metal"],
        12,
    )
    parts.append(crown)
    attach(root, parts, "housing")
    for index in range(21):
        angle = math.radians(-130 + index * 13)
        tick = v4.accent_bar(
            f"forge_tick_{index}",
            0.0016 if index % 5 else 0.0028,
            0.005 if index % 5 else 0.010,
            math.sin(angle) * 0.043,
            math.cos(angle) * 0.043,
            0.071,
            mats["readout"],
        )
        tick.rotation_euler.y = angle
        tick.parent = root
    pivot_point = (0.0, -0.072, -0.004)
    meter_needle(root, mats, pivot_point, 0.043, 0.0034)
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_kinetic_meter():
    theme = "KineticSafety"
    mats = materials(theme)
    root = root_for(theme, "MeterRound", "meter.round")
    body = v4.shell(
        "kinetic_armored_body",
        0.154,
        0.154,
        0.018,
        0.112,
        0.112,
        0.011,
        0.052,
        0.044,
        mats["body"],
    )
    parts = [body]
    for x in (-0.066, 0.066):
        guard = v4.prism(
            "kinetic_meter_guard",
            0.022,
            0.110,
            0.006,
            -0.045,
            -0.071,
            mats["metal"],
        )
        guard.location.x = x
        parts.append(guard)
    for z in (-0.066, 0.066):
        brace = v4.prism(
            "kinetic_meter_brace",
            0.090,
            0.014,
            0.004,
            -0.048,
            -0.072,
            mats["metal"],
            z,
        )
        parts.append(brace)
    attach(root, parts, "housing")
    bezel = v4.cylinder_y(
        "kinetic_polygon_bezel",
        0.052,
        0.016,
        0.069,
        mats["body"],
        12,
    )
    bezel.parent = root
    for index in range(13):
        angle = math.radians(-120 + index * 20)
        tick = v4.accent_bar(
            f"kinetic_tick_{index}",
            0.0024,
            0.008 if index % 3 else 0.013,
            math.sin(angle) * 0.043,
            math.cos(angle) * 0.043,
            0.076,
            mats["readout"],
        )
        tick.rotation_euler.y = angle
        tick.parent = root
    pivot_point = (0.0, -0.077, -0.004)
    meter_needle(root, mats, pivot_point, 0.042, 0.0042)
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_orbital_lever():
    theme = "OrbitalAnalog"
    mats = materials(theme)
    root = root_for(theme, "Lever", "control.lever")
    back = v4.shell(
        "orbital_recessed_slot",
        0.126,
        0.220,
        0.010,
        0.052,
        0.174,
        0.007,
        0.030,
        0.026,
        mats["body"],
    )
    rails = [back]
    for x in (-0.050, 0.050):
        rail = v4.prism(
            "orbital_fairing",
            0.013,
            0.176,
            0.004,
            -0.027,
            -0.041,
            mats["metal"],
        )
        rail.location.x = x
        rails.append(rail)
    attach(root, rails, "housing")
    # The axle centre sits on the recessed housing face so that half of the
    # trunnion is buried in the console rather than hovering in front of it.
    pivot_point = (0.0, -0.026, -0.074)
    for x in (-0.026, 0.026):
        socket = v4.cylinder_x(
            "orbital_trunnion_socket",
            0.014,
            0.018,
            (x, pivot_point[1], pivot_point[2]),
            mats["body"],
            16,
        )
        socket.parent = root
    shaft = v4.cylinder_z(
        "orbital_slender_shaft",
        0.0055,
        0.150,
        (0.0, pivot_point[1], -0.004),
        mats["metal"],
        14,
    )
    axle = v4.cylinder_x(
        "orbital_hidden_trunnion",
        0.009,
        0.042,
        pivot_point,
        mats["metal"],
        16,
    )
    grip = v4.prism(
        "orbital_control_yoke",
        0.054,
        0.030,
        0.009,
        -0.040,
        -0.061,
        mats["body"],
        0.084,
    )
    readout = v4.accent_bar(
        "orbital_grip_index",
        0.030,
        0.004,
        0.0,
        0.084,
        0.062,
        mats["readout"],
    )
    pivot, handle = v4.parent_movable(
        [shaft, axle, grip, readout],
        "handle",
        pivot_point,
        root,
    )
    pivot.name = "handle_pivot"
    handle.name = "handle"
    return root, pivot_point, (1.0, 0.0, 0.0)


def build_forge_lever():
    theme = "ForgeBrass"
    mats = materials(theme)
    root = root_for(theme, "Lever", "control.lever")
    body = v4.cylinder_y(
        "forge_cast_lever_plate",
        0.078,
        0.040,
        0.022,
        mats["body"],
        20,
    )
    body.scale.z = 1.18
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bearing = v4.cylinder_y(
        "forge_exposed_bearing",
        0.030,
        0.026,
        0.052,
        mats["metal"],
        24,
    )
    bearing.location.z = -0.034
    parts = [body, bearing]
    for x in (-0.052, 0.052):
        lug = v4.prism(
            "forge_cast_lug",
            0.024,
            0.038,
            0.008,
            0.0,
            -0.043,
            mats["body"],
            -0.070,
        )
        lug.location.x = x
        parts.append(lug)
    attach(root, parts, "housing")
    # The bearing front is y=-0.065; placing the axle centre on that plane
    # leaves half of the axle visibly exposed and half captured by the boss.
    pivot_point = (0.0, -0.065, -0.034)
    shaft = v4.cylinder_z(
        "forge_solid_shaft",
        0.008,
        0.142,
        (0.0, pivot_point[1], 0.037),
        mats["metal"],
        16,
    )
    axle = v4.cylinder_x(
        "forge_axle",
        0.012,
        0.064,
        pivot_point,
        mats["metal"],
        18,
    )
    ball = sphere(
        "forge_ball_grip",
        0.027,
        (0.0, pivot_point[1], 0.122),
        mats["body"],
        20,
        10,
    )
    collar = v4.cylinder_z(
        "forge_grip_collar",
        0.013,
        0.020,
        (0.0, pivot_point[1], 0.096),
        mats["metal"],
        16,
    )
    pivot, handle = v4.parent_movable(
        [shaft, axle, ball, collar],
        "handle",
        pivot_point,
        root,
    )
    pivot.name = "handle_pivot"
    handle.name = "handle"
    return root, pivot_point, (1.0, 0.0, 0.0)


def build_kinetic_lever():
    theme = "KineticSafety"
    root, meshes = retopo.build_retopo()
    mats = materials(theme)
    root.name = "PF_Visual_Lever_KineticSafety_V5"
    root["art_pass"] = "V5 grayscale silhouette study"
    root["shared_visible_geometry"] = False
    for obj in meshes:
        for slot in obj.material_slots:
            token = slot.material.name.lower() if slot.material else ""
            if "cyan" in token:
                slot.material = mats["readout"]
            elif "gunmetal" in token:
                slot.material = mats["metal"]
            else:
                slot.material = mats["body"]
    return root, (0.0, -0.050, -0.025), (1.0, 0.0, 0.0)


def panel_vane(root, mats, pivot_point, style):
    if style == "orbital":
        vane = v4.prism(
            "vane",
            0.54,
            0.032,
            0.008,
            pivot_point[1],
            pivot_point[1] - 0.018,
            mats["readout"],
            pivot_point[2],
        )
    elif style == "forge":
        vane = v4.prism(
            "vane",
            0.060,
            0.430,
            0.014,
            pivot_point[1],
            pivot_point[1] - 0.026,
            mats["metal"],
            pivot_point[2] + 0.205,
        )
    else:
        vane = v4.prism(
            "vane",
            0.042,
            0.460,
            0.010,
            pivot_point[1],
            pivot_point[1] - 0.025,
            mats["metal"],
            pivot_point[2] + 0.215,
        )
    hub = v4.cylinder_y(
        "vane_hub",
        0.048 if style != "orbital" else 0.036,
        0.024,
        abs(pivot_point[1]),
        mats["body"],
        20,
    )
    hub.location.z = pivot_point[2]
    pivot, movable = v4.parent_movable(
        [vane, hub],
        "vane",
        pivot_point,
        root,
    )
    pivot.name = "vane_pivot"
    movable.name = "vane"


def build_orbital_panel():
    theme = "OrbitalAnalog"
    mats = materials(theme)
    root = root_for(theme, "WindowPanel", "panel.window")
    back = v4.shell(
        "orbital_thin_bulkhead",
        1.60,
        0.82,
        0.040,
        1.42,
        0.64,
        0.028,
        0.080,
        0.069,
        mats["body"],
    )
    parts = [back]
    for x in (-0.735, 0.735):
        spine = v4.prism(
            "orbital_vertical_spine",
            0.045,
            0.650,
            0.012,
            -0.070,
            -0.108,
            mats["metal"],
        )
        spine.location.x = x
        parts.append(spine)
    for z in (-0.335, 0.335):
        brow = v4.prism(
            "orbital_console_brow",
            1.20,
            0.040,
            0.012,
            -0.070,
            -0.112,
            mats["metal"],
            z,
        )
        parts.append(brow)
    attach(root, parts, "housing")
    display = v4.prism(
        "orbital_display",
        1.18,
        0.42,
        0.030,
        -0.107,
        -0.124,
        mats["body"],
        0.020,
    )
    display.parent = root
    for z in (0.140, 0.055, -0.030):
        trace = v4.accent_bar(
            "orbital_dense_trace",
            0.82,
            0.009,
            0.0,
            z,
            0.123,
            mats["readout"],
        )
        trace.parent = root
    pivot_point = (0.0, -0.124, -0.205)
    panel_vane(root, mats, pivot_point, "orbital")
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_forge_panel():
    theme = "ForgeBrass"
    mats = materials(theme)
    root = root_for(theme, "WindowPanel", "panel.window")
    back = v4.shell(
        "forge_cast_bulkhead",
        1.60,
        0.90,
        0.090,
        1.30,
        0.62,
        0.055,
        0.150,
        0.128,
        mats["body"],
    )
    parts = [back]
    for x in (-0.655, 0.655):
        pipe = v4.cylinder_z(
            "forge_exposed_pipe",
            0.034,
            0.650,
            (x, -0.155, 0.0),
            mats["metal"],
            16,
        )
        parts.append(pipe)
        for z in (-0.260, 0.260):
            collar = v4.cylinder_z(
                "forge_pipe_collar",
                0.047,
                0.035,
                (x, -0.155, z),
                mats["body"],
                16,
            )
            parts.append(collar)
    attach(root, parts, "housing")
    display = v4.prism(
        "forge_recessed_nameplate",
        1.00,
        0.44,
        0.055,
        -0.148,
        -0.176,
        mats["metal"],
        0.025,
    )
    display.parent = root
    pivot_point = (0.0, -0.176, -0.205)
    panel_vane(root, mats, pivot_point, "forge")
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_kinetic_panel():
    theme = "KineticSafety"
    mats = materials(theme)
    root = root_for(theme, "WindowPanel", "panel.window")
    back = v4.shell(
        "kinetic_armored_bulkhead",
        1.60,
        0.90,
        0.065,
        1.30,
        0.62,
        0.040,
        0.140,
        0.118,
        mats["body"],
    )
    parts = [back]
    for x in (-0.690, 0.690):
        guard = v4.prism(
            "kinetic_side_guard",
            0.105,
            0.720,
            0.026,
            -0.114,
            -0.184,
            mats["metal"],
        )
        guard.location.x = x
        parts.append(guard)
    for z in (-0.360, 0.360):
        brace = v4.prism(
            "kinetic_cross_guard",
            1.24,
            0.082,
            0.020,
            -0.116,
            -0.180,
            mats["metal"],
            z,
        )
        parts.append(brace)
    for index, angle in enumerate((-18.0, 18.0)):
        diagonal = v4.prism(
            f"kinetic_diagonal_{index}",
            0.060,
            0.580,
            0.014,
            -0.112,
            -0.170,
            mats["metal"],
        )
        diagonal.rotation_euler.y = math.radians(angle)
        parts.append(diagonal)
    attach(root, parts, "housing")
    display = v4.prism(
        "kinetic_recessed_display",
        1.02,
        0.42,
        0.035,
        -0.172,
        -0.194,
        mats["body"],
        0.020,
    )
    display.parent = root
    for index, z in enumerate((0.145, 0.045, -0.055)):
        bar = v4.accent_bar(
            f"kinetic_status_bar_{index}",
            0.68 - index * 0.10,
            0.014,
            -0.08 + index * 0.06,
            z,
            0.193,
            mats["readout"],
        )
        bar.parent = root
    pivot_point = (0.0, -0.194, -0.205)
    panel_vane(root, mats, pivot_point, "kinetic")
    return root, pivot_point, (0.0, 1.0, 0.0)


BUILDERS = {
    ("OrbitalAnalog", "MeterRound"): build_orbital_meter,
    ("ForgeBrass", "MeterRound"): build_forge_meter,
    ("KineticSafety", "MeterRound"): build_kinetic_meter,
    ("OrbitalAnalog", "Lever"): build_orbital_lever,
    ("ForgeBrass", "Lever"): build_forge_lever,
    ("KineticSafety", "Lever"): build_kinetic_lever,
    ("OrbitalAnalog", "WindowPanel"): build_orbital_panel,
    ("ForgeBrass", "WindowPanel"): build_forge_panel,
    ("KineticSafety", "WindowPanel"): build_kinetic_panel,
}


def meshes_under(root):
    return [obj for obj in root.children_recursive if obj.type == "MESH"]


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def generate_one(project_root, theme, key, skip_topology):
    common.clean_scene()
    type_id, budget = ASSETS[key]
    root, pivot_position, local_axis = BUILDERS[(theme, key)]()
    meshes = meshes_under(root)
    common.apply_transforms(meshes)
    source_stats = retopo.topology_stats(meshes)
    if source_stats["non_manifold_edges"]:
        raise RuntimeError(f"{theme}/{key}: non-manifold source")
    if source_stats["zero_area_faces"]:
        raise RuntimeError(f"{theme}/{key}: degenerate source")
    source_dir = (
        project_root
        / "ArtSource/Blender/ThemeSilhouetteV5"
        / theme
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates"
        / theme
        / "ThemeSilhouetteV5"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    preview = source_dir / f"Preview_{key}_{theme}_V5_Grayscale.png"
    controls.create_preview(meshes, 0.0, preview)
    if not skip_topology:
        retopo.render_topology_preview(
            meshes,
            source_dir / f"Preview_{key}_{theme}_V5_Topology.png",
        )
    save_blend(source_dir / f"BL_{key}_{theme}_V5_Retopo.blend")
    retopo.triangulate(meshes)
    final_stats = retopo.topology_stats(meshes)
    if final_stats["non_manifold_edges"]:
        raise RuntimeError(f"{theme}/{key}: non-manifold final")
    if final_stats["zero_area_faces"]:
        raise RuntimeError(f"{theme}/{key}: degenerate final")
    if final_stats["faces"] > budget:
        raise RuntimeError(
            f"{theme}/{key}: {final_stats['faces']} > {budget}"
        )
    save_blend(
        source_dir / f"BL_{key}_{theme}_V5_Triangulated.blend"
    )
    fbx_path = model_dir / f"SM_{key}_{theme}_V5_Grayscale.fbx"
    if fbx_path.with_suffix(".fbm").exists():
        shutil.rmtree(fbx_path.with_suffix(".fbm"))
    common.export_fbx(root, fbx_path)
    report = {
        "asset": f"{key}_{theme}_V5_Grayscale",
        "type_id": type_id,
        "theme_id": THEMES[theme],
        "art_pass": "grayscale silhouette",
        "shared_visible_geometry": False,
        "source_topology": source_stats,
        "triangulated_topology": final_stats,
        "triangle_budget": budget,
        "pivot": {
            "position": list(pivot_position),
            "local_axis": list(local_axis),
        },
        "production_integrated": False,
    }
    (
        source_dir / f"{key}_{theme}_V5.report.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report))


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    for theme in THEMES:
        for key in ASSETS:
            generate_one(
                project_root,
                theme,
                key,
                args.skip_topology,
            )


if __name__ == "__main__":
    main()
