"""Generate non-destructive Gemini-review-driven replacement candidates."""

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


THEMES = (
    {
        "folder": "OrbitalAnalog",
        "id": "orbital-analog",
        "housing": (0.018, 0.035, 0.060, 1.0),
        "face": (0.06, 0.22, 0.30, 1.0),
        "emissive": (0.12, 0.78, 1.0, 1.0),
    },
    {
        "folder": "ForgeBrass",
        "id": "forge-brass",
        "housing": (0.075, 0.045, 0.025, 1.0),
        "face": (0.42, 0.23, 0.075, 1.0),
        "emissive": (1.0, 0.62, 0.22, 1.0),
    },
    {
        "folder": "KineticSafety",
        "id": "kinetic-safety",
        "housing": (0.018, 0.026, 0.038, 1.0),
        "face": (0.18, 0.24, 0.28, 1.0),
        "emissive": (0.10, 0.72, 0.94, 1.0),
    },
)


ASSETS = (
    ("MeterRound", "meter.round", (0.1401, 0.1401, 0.0641), 5000, 4),
    ("Lever", "control.lever", (0.1801, 0.2561, 0.1001), 5000, 3),
    ("Toggle", "control.toggle", (0.1201, 0.1701, 0.0641), 5000, 2),
    ("Rotary", "control.rotary", (0.1501, 0.1501, 0.1021), 5000, 3),
    ("Button", "control.button", (0.1301, 0.1301, 0.0901), 5000, 2),
    ("Lamp", "indicator.lamp", (0.1401, 0.1101, 0.0821), 5000, 2),
    ("Throttle", "control.throttle", (0.2401, 0.3401, 0.1601), 5000, 3),
    (
        "PowerSlider",
        "control.power_slider",
        (0.1601, 0.3401, 0.0941),
        5000,
        3,
    ),
    (
        "StatusIndicator",
        "indicator.status",
        (0.1801, 0.1201, 0.0751),
        5000,
        4,
    ),
    ("WindowMeter", "meter.window", (1.2001, 0.7501, 0.1901), 25000, 4),
    ("WindowPanel", "panel.window", (1.6001, 0.9001, 0.2201), 25000, 4),
)


REVIEW_CHANGES = {
    "MeterRound": (
        "deeper stepped bezel",
        "six fasteners and double arc",
        "stronger needle hub silhouette",
    ),
    "Lever": (
        "bearing cover and guide",
        "five detent marks",
        "protected pivot clearance",
    ),
    "Toggle": (
        "hex-nut collar",
        "direction labels",
        "raised pivot without changing axis",
    ),
    "Rotary": (
        "stepped umbrella bezel",
        "radial scale",
        "grip-readable outer profile",
    ),
    "Button": (
        "visible travel gap",
        "double bezel",
        "emissive function mark",
    ),
    "Lamp": (
        "retaining cage",
        "internal LED structure",
        "lens edge protection",
    ),
    "Throttle": (
        "engine quadrant scale",
        "end stops and guarded track",
        "palm-grip emphasis",
    ),
    "PowerSlider": (
        "eleven-step scale",
        "mechanical end stops",
        "guided carriage track",
    ),
    "StatusIndicator": (
        "three independent SAFE/WARN/DANGER segments",
        "dark smoke housing",
        "shape-readable state separation",
    ),
    "WindowMeter": (
        "reinforced window frame",
        "deep layered dial",
        "large emissive needle",
    ),
    "WindowPanel": (
        "mechanical bulkhead frame",
        "central display field",
        "exposed status vane pivot",
    ),
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-previews", action="store_true")
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[asset[0] for asset in ASSETS],
        help="Generate only the selected asset keys.",
    )
    return parser.parse_args(args)


def simple_material(name, color, emissive=False):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Metallic"].default_value = 0.75 if not emissive else 0.25
        shader.inputs["Roughness"].default_value = 0.58 if not emissive else 0.28
        if emissive:
            shader.inputs["Emission Color"].default_value = color
            shader.inputs["Emission Strength"].default_value = 2.0
    return material


def find_material(token, fallback):
    for material in bpy.data.materials:
        if token.lower() in material.name.lower():
            return material
    return fallback


def cube(name, dimensions, location, material, bevel=0.0015):
    return controls.add_cube(
        name,
        dimensions,
        location,
        material,
        (0.125, 0.125),
        bevel,
    )


def cylinder(name, radius, depth, outward, material, vertices=12):
    result = common.add_cylinder(
        name,
        radius,
        depth,
        outward,
        vertices,
        material,
    )
    common.set_constant_uv(result, (0.625, 0.125))
    return result


def torus(name, major, minor, outward, material):
    result = common.add_torus(name, major, minor, outward, material)
    common.set_constant_uv(result, (0.625, 0.125))
    return result


def vertical_cylinder(
    name,
    radius,
    height,
    location,
    material,
    vertices=20,
):
    return controls.add_vertical_cylinder(
        name,
        radius,
        height,
        location,
        vertices,
        material,
        (0.625, 0.125),
    )


def sphere(name, radius, location, material, segments=20, rings=10):
    return controls.add_sphere(
        name,
        radius,
        location,
        material,
        (0.375, 0.125),
        segments,
        rings,
    )


def bolt(name, x, z, outward, material, radius=0.0032):
    result = cylinder(name, radius, 0.0035, outward, material, 8)
    result.location.x = x
    result.location.z = z
    return result


def join_into(target, details, final_name):
    if not details:
        return target
    parent = target.parent
    result = common.join_objects([target] + details, final_name)
    result.parent = parent
    return result


def root_meshes(root):
    return [
        child
        for child in root.children_recursive
        if child.type == "MESH"
    ]


def find_root(key, theme):
    name = f"PF_Visual_{key}_{theme['folder']}"
    root = bpy.data.objects.get(name)
    if root is None:
        raise RuntimeError(f"Missing source root {name}")
    return root


def materials_for_existing(theme):
    opaque_fallback = simple_material(
        f"MAT_{theme['folder']}_Atlas_Refined",
        theme["housing"],
    )
    emissive_fallback = simple_material(
        f"MAT_{theme['folder']}_Emissive_Refined",
        theme["emissive"],
        emissive=True,
    )
    opaque = find_material("Atlas", opaque_fallback)
    emissive = find_material("Emissive", emissive_fallback)
    return opaque, emissive


def add_theme_signature(theme, key, details, opaque, emissive):
    if key in ("WindowMeter", "WindowPanel"):
        return
    if theme["id"] == "forge-brass":
        positions = ((-0.045, -0.045), (0.045, 0.045))
        for index, (x, z) in enumerate(positions):
            details.append(
                bolt(
                    f"forge_rivet_{index}",
                    x,
                    z,
                    0.052,
                    opaque,
                    0.0038,
                )
            )
    elif theme["id"] == "kinetic-safety":
        details.extend(
            (
                cube(
                    "kinetic_guard_left",
                    (0.009, 0.008, 0.070),
                    (-0.052, -0.052, 0.0),
                    emissive,
                    0.001,
                ),
                cube(
                    "kinetic_guard_right",
                    (0.009, 0.008, 0.070),
                    (0.052, -0.052, 0.0),
                    emissive,
                    0.001,
                ),
            )
        )
    else:
        details.extend(
            (
                cube(
                    "orbital_detail_left",
                    (0.005, 0.006, 0.060),
                    (-0.050, -0.051, 0.0),
                    emissive,
                    0.0008,
                ),
                cube(
                    "orbital_detail_right",
                    (0.005, 0.006, 0.060),
                    (0.050, -0.051, 0.0),
                    emissive,
                    0.0008,
                ),
            )
        )


def build_refined_meter(theme, opaque, emissive):
    root = new_root("MeterRound", "meter.round", theme)
    theme_id = theme["id"]
    housing_parts = [
        cylinder(
            "meter_body",
            0.068,
            0.036,
            0.018,
            opaque,
            32 if theme_id == "forge-brass" else 12,
        ),
        torus(
            "meter_outer_bezel",
            0.060,
            0.0052 if theme_id == "forge-brass" else 0.0042,
            0.041,
            opaque,
        ),
        torus(
            "meter_inner_bezel",
            0.052,
            0.0020,
            0.046,
            emissive,
        ),
    ]
    if theme_id == "forge-brass":
        housing_parts.extend(
            (
                cube(
                    "vintage_mount_left",
                    (0.020, 0.020, 0.030),
                    (-0.058, -0.021, -0.052),
                    opaque,
                    0.004,
                ),
                cube(
                    "vintage_mount_right",
                    (0.020, 0.020, 0.030),
                    (0.058, -0.021, -0.052),
                    opaque,
                    0.004,
                ),
            )
        )
        fastener_angles = (45, 135, 225, 315)
    elif theme_id == "kinetic-safety":
        housing_parts.extend(
            (
                cube(
                    "sf_guard_left",
                    (0.015, 0.026, 0.090),
                    (-0.061, -0.025, 0.0),
                    opaque,
                    0.004,
                ),
                cube(
                    "sf_guard_right",
                    (0.015, 0.026, 0.090),
                    (0.061, -0.025, 0.0),
                    opaque,
                    0.004,
                ),
                cube(
                    "sf_status_bar",
                    (0.058, 0.010, 0.006),
                    (0.0, -0.047, -0.057),
                    emissive,
                    0.0015,
                ),
            )
        )
        fastener_angles = (45, 135, 225, 315)
    else:
        housing_parts.extend(
            (
                torus(
                    "mr_projector_ring",
                    0.064,
                    0.0018,
                    0.026,
                    emissive,
                ),
                cube(
                    "mr_projector_base",
                    (0.072, 0.026, 0.018),
                    (0.0, -0.013, -0.060),
                    opaque,
                    0.004,
                ),
            )
        )
        fastener_angles = ()
    for index, angle in enumerate(fastener_angles):
        radians = math.radians(angle)
        housing_parts.append(
            bolt(
                f"meter_fastener_{index}",
                math.cos(radians) * 0.060,
                math.sin(radians) * 0.060,
                0.046,
                opaque,
                0.0028,
            )
        )
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    dial_parts = [
        cylinder(
            "dial_face",
            0.051,
            0.004,
            0.049,
            opaque,
            48,
        ),
        torus(
            "dial_scale_arc",
            0.043,
            0.0009,
            0.052,
            emissive,
        ),
    ]
    tick_count = 25 if theme_id == "forge-brass" else 21
    for index in range(tick_count):
        t = index / (tick_count - 1)
        angle = math.radians(-130 + t * 260)
        major = index % 4 == 0
        radius = 0.040 if major else 0.042
        tick = cube(
            f"dial_tick_{index}",
            (
                0.0024 if major else 0.0014,
                0.0026,
                0.009 if major else 0.0055,
            ),
            (
                math.sin(angle) * radius,
                -0.054,
                math.cos(angle) * radius,
            ),
            emissive,
            0.0003,
        )
        tick.rotation_euler[1] = angle
        dial_parts.append(tick)
    dial = common.join_objects(dial_parts, "dial")
    dial.parent = root

    pivot_point = (0.0, -0.057, 0.0)
    needle_parts = [
        cube(
            "needle_blade",
            (0.0032, 0.0030, 0.039),
            (0.0, -0.058, 0.0195),
            emissive,
            0.0006,
        ),
        cylinder(
            "needle_hub",
            0.0075,
            0.005,
            0.059,
            opaque,
            20,
        ),
        cube(
            "needle_tail",
            (0.0045, 0.0030, 0.012),
            (0.0, -0.058, -0.006),
            emissive,
            0.0005,
        ),
    ]
    pivot, needle = controls.parent_at_pivot(
        needle_parts,
        "needle",
        pivot_point,
        root,
    )
    pivot.name = "needle_pivot"
    needle.name = "needle"
    controls.set_smooth([housing, dial, needle])
    return root


def build_refined_lever(theme, opaque, emissive):
    root = new_root("Lever", "control.lever", theme)
    theme_id = theme["id"]
    pivot_point = (0.0, -0.070, -0.025)
    housing_parts = [
        cube(
            "lever_backplate",
            (0.18, 0.045, 0.14),
            (0.0, -0.0225, 0.0),
            opaque,
            0.006 if theme_id != "forge-brass" else 0.009,
        ),
        torus(
            "lever_bearing",
            0.029,
            0.005,
            -pivot_point[1],
            opaque,
        ),
        torus(
            "lever_bearing_inner",
            0.020,
            0.0018,
            -pivot_point[1] - 0.003,
            emissive,
        ),
    ]
    housing_parts[-2].location.z = pivot_point[2]
    housing_parts[-1].location.z = pivot_point[2]
    if theme_id == "forge-brass":
        housing_parts.extend(
            (
                cube(
                    "vintage_gate_left",
                    (0.018, 0.020, 0.118),
                    (-0.067, -0.045, 0.0),
                    opaque,
                    0.006,
                ),
                cube(
                    "vintage_gate_right",
                    (0.018, 0.020, 0.118),
                    (0.067, -0.045, 0.0),
                    opaque,
                    0.006,
                ),
            )
        )
    elif theme_id == "kinetic-safety":
        housing_parts.extend(
            (
                cube(
                    "sf_shoulder_left",
                    (0.034, 0.030, 0.092),
                    (-0.064, -0.042, -0.004),
                    opaque,
                    0.007,
                ),
                cube(
                    "sf_shoulder_right",
                    (0.034, 0.030, 0.092),
                    (0.064, -0.042, -0.004),
                    opaque,
                    0.007,
                ),
                cube(
                    "sf_gate_light",
                    (0.010, 0.008, 0.102),
                    (0.058, -0.060, 0.006),
                    emissive,
                    0.002,
                ),
            )
        )
    else:
        housing_parts.extend(
            (
                torus(
                    "mr_base_projection",
                    0.058,
                    0.0015,
                    0.050,
                    emissive,
                ),
                cube(
                    "mr_base_pedestal",
                    (0.076, 0.024, 0.024),
                    (0.0, -0.034, -0.057),
                    opaque,
                    0.005,
                ),
            )
        )
    for index in range(5):
        housing_parts.append(
            cube(
                f"lever_detent_{index}",
                (0.014, 0.006, 0.0035),
                (0.066, -0.054, -0.055 + index * 0.0275),
                emissive,
                0.0006,
            )
        )
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    handle_parts = [
        vertical_cylinder(
            "handle_shaft",
            0.0075 if theme_id == "forge-brass" else 0.009,
            0.135,
            (0.0, pivot_point[1], 0.0425),
            opaque,
            20,
        ),
        cylinder(
            "handle_axle_cap",
            0.018,
            0.010,
            -pivot_point[1] + 0.006,
            opaque,
            24,
        ),
    ]
    handle_parts[-1].location.z = pivot_point[2]
    if theme_id == "forge-brass":
        handle_parts.extend(
            (
                sphere(
                    "vintage_grip",
                    0.026,
                    (0.0, pivot_point[1], 0.137),
                    emissive,
                    24,
                    12,
                ),
                torus(
                    "vintage_grip_collar",
                    0.014,
                    0.0025,
                    -pivot_point[1],
                    opaque,
                ),
            )
        )
        handle_parts[-1].location.z = 0.111
    elif theme_id == "kinetic-safety":
        handle_parts.extend(
            (
                cube(
                    "sf_palm_grip",
                    (0.046, 0.040, 0.070),
                    (0.0, pivot_point[1], 0.128),
                    opaque,
                    0.009,
                ),
                cube(
                    "sf_grip_light",
                    (0.026, 0.006, 0.008),
                    (0.0, pivot_point[1] - 0.022, 0.132),
                    emissive,
                    0.002,
                ),
            )
        )
    else:
        handle_parts.extend(
            (
                cube(
                    "mr_light_grip",
                    (0.034, 0.028, 0.076),
                    (0.0, pivot_point[1], 0.130),
                    emissive,
                    0.010,
                ),
                torus(
                    "mr_grip_halo",
                    0.021,
                    0.0015,
                    -pivot_point[1] + 0.015,
                    emissive,
                ),
            )
        )
        handle_parts[-1].location.z = 0.132
    pivot, handle = controls.parent_at_pivot(
        handle_parts,
        "handle",
        pivot_point,
        root,
    )
    pivot.name = "handle_pivot"
    handle.name = "handle"
    controls.set_smooth([housing, handle])
    return root


def build_refined_status(theme, opaque, emissive):
    root = new_root("StatusIndicator", "indicator.status", theme)
    theme_id = theme["id"]
    housing_parts = [
        cube(
            "status_housing",
            (0.18, 0.045, 0.12),
            (0.0, -0.0225, 0.0),
            opaque,
            0.010 if theme_id == "forge-brass" else 0.007,
        ),
        cube(
            "status_recess",
            (0.164, 0.014, 0.076),
            (0.0, -0.051, 0.0),
            opaque,
            0.006,
        ),
    ]
    if theme_id == "forge-brass":
        for x in (-0.076, 0.076):
            for z in (-0.047, 0.047):
                housing_parts.append(
                    bolt(
                        "vintage_status_rivet",
                        x,
                        z,
                        0.052,
                        opaque,
                        0.004,
                    )
                )
    elif theme_id == "kinetic-safety":
        housing_parts.extend(
            (
                cube(
                    "sf_guard_top",
                    (0.174, 0.020, 0.014),
                    (0.0, -0.057, 0.052),
                    opaque,
                    0.004,
                ),
                cube(
                    "sf_guard_bottom",
                    (0.174, 0.020, 0.014),
                    (0.0, -0.057, -0.052),
                    opaque,
                    0.004,
                ),
                cube(
                    "sf_header_light",
                    (0.078, 0.008, 0.005),
                    (0.0, -0.068, 0.049),
                    emissive,
                    0.001,
                ),
            )
        )
    else:
        housing_parts.extend(
            (
                torus(
                    "mr_status_projector",
                    0.054,
                    0.0015,
                    0.052,
                    emissive,
                ),
                cube(
                    "mr_status_base",
                    (0.082, 0.020, 0.018),
                    (0.0, -0.034, -0.051),
                    opaque,
                    0.004,
                ),
            )
        )
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root

    indicator = bpy.data.objects.new("indicator", None)
    indicator.parent = root
    bpy.context.collection.objects.link(indicator)
    for index, name in enumerate(
        ("status_safe", "status_warn", "status_danger")
    ):
        x = -0.055 + index * 0.055
        if theme_id == "forge-brass":
            segment = cylinder(
                name,
                0.020,
                0.012,
                0.063,
                emissive,
                28,
            )
            segment.location.x = x
        elif theme_id == "kinetic-safety":
            segment = cube(
                name,
                (0.044, 0.018, 0.052),
                (x, -0.064, 0.0),
                emissive,
                0.008,
            )
        else:
            segment = cube(
                name,
                (0.038, 0.009, 0.064),
                (x, -0.060, 0.006),
                emissive,
                0.012,
            )
        segment.parent = indicator
    return root


def build_representative(key, type_id, theme):
    opaque = simple_material(
        f"MAT_{theme['folder']}_Atlas_Refined",
        theme["housing"],
    )
    emissive = simple_material(
        f"MAT_{theme['folder']}_Emissive_Refined",
        theme["emissive"],
        emissive=True,
    )
    if key == "MeterRound":
        return build_refined_meter(theme, opaque, emissive)
    if key == "Lever":
        return build_refined_lever(theme, opaque, emissive)
    if key == "StatusIndicator":
        return build_refined_status(theme, opaque, emissive)
    raise RuntimeError(f"Unsupported representative asset {key}")


def refine_existing(key, theme):
    root = find_root(key, theme)
    opaque, emissive = materials_for_existing(theme)
    housing = bpy.data.objects.get("housing")
    if housing is None:
        raise RuntimeError(f"{theme['folder']}/{key}: missing housing")
    details = []

    if key == "MeterRound":
        details.extend(
            (
                torus("bezel_outer_step", 0.060, 0.0026, 0.048, opaque),
                torus("bezel_inner_arc", 0.049, 0.0015, 0.050, emissive),
            )
        )
        for index, angle in enumerate(range(0, 360, 60)):
            radians = math.radians(angle)
            details.append(
                bolt(
                    f"bezel_fastener_{index}",
                    math.cos(radians) * 0.061,
                    math.sin(radians) * 0.061,
                    0.049,
                    opaque,
                    0.0027,
                )
            )
    elif key == "Lever":
        pivot = bpy.data.objects.get("handle_pivot")
        if pivot is None:
            raise RuntimeError(
                f"{theme['folder']}/{key}: missing handle_pivot"
            )
        pivot_position = pivot.matrix_world.translation
        bearing_cover = torus(
            "lever_bearing_cover",
            0.026,
            0.0038,
            -pivot_position.y,
            opaque,
        )
        bearing_cover.location.x = pivot_position.x
        bearing_cover.location.z = pivot_position.z
        details.extend(
            (
                bearing_cover,
                cube(
                    "lever_gate",
                    (0.060, 0.006, 0.155),
                    (0.0, -0.055, 0.0),
                    opaque,
                    0.002,
                ),
            )
        )
        for index in range(5):
            details.append(
                cube(
                    f"lever_detent_{index}",
                    (0.014, 0.005, 0.004),
                    (0.065, -0.060, -0.060 + index * 0.030),
                    emissive,
                    0.0006,
                )
            )
    elif key == "Toggle":
        details.extend(
            (
                cylinder("toggle_hex_nut", 0.026, 0.006, 0.050, opaque, 6),
                torus("toggle_spring_collar", 0.017, 0.0025, 0.055, opaque),
                cube(
                    "toggle_off_mark",
                    (0.026, 0.004, 0.006),
                    (0.0, -0.057, -0.052),
                    emissive,
                    0.0008,
                ),
                cube(
                    "toggle_on_mark",
                    (0.026, 0.004, 0.006),
                    (0.0, -0.057, 0.052),
                    emissive,
                    0.0008,
                ),
            )
        )
    elif key == "Rotary":
        details.extend(
            (
                torus("rotary_step_outer", 0.058, 0.0035, 0.052, opaque),
                torus("rotary_step_inner", 0.045, 0.0020, 0.057, emissive),
            )
        )
        for index in range(9):
            angle = math.radians(-120 + index * 30)
            details.append(
                cube(
                    f"rotary_tick_{index}",
                    (0.005, 0.004, 0.014),
                    (
                        math.sin(angle) * 0.062,
                        -0.058,
                        math.cos(angle) * 0.062,
                    ),
                    emissive,
                    0.0006,
                )
            )
    elif key == "Button":
        details.extend(
            (
                torus("button_outer_bezel", 0.050, 0.0035, 0.048, opaque),
                torus("button_travel_gap", 0.039, 0.0018, 0.056, emissive),
            )
        )
    elif key == "Lamp":
        details.extend(
            (
                torus("lamp_retaining_ring", 0.042, 0.0030, 0.055, opaque),
                cube(
                    "lamp_cage_left",
                    (0.007, 0.008, 0.070),
                    (-0.043, -0.056, 0.0),
                    opaque,
                    0.001,
                ),
                cube(
                    "lamp_cage_right",
                    (0.007, 0.008, 0.070),
                    (0.043, -0.056, 0.0),
                    opaque,
                    0.001,
                ),
            )
        )
    elif key == "Throttle":
        for index in range(6):
            details.append(
                cube(
                    f"throttle_scale_{index}",
                    (0.014, 0.006, 0.005),
                    (0.097, -0.075, -0.105 + index * 0.042),
                    emissive,
                    0.0007,
                )
            )
        details.extend(
            (
                cube(
                    "throttle_cutoff_stop",
                    (0.052, 0.018, 0.018),
                    (0.0, -0.071, -0.132),
                    opaque,
                    0.003,
                ),
                cube(
                    "throttle_full_stop",
                    (0.052, 0.018, 0.018),
                    (0.0, -0.071, 0.132),
                    opaque,
                    0.003,
                ),
            )
        )
    elif key == "PowerSlider":
        for index in range(11):
            details.append(
                cube(
                    f"slider_scale_{index}",
                    (0.018, 0.005, 0.0035),
                    (0.058, -0.058, -0.135 + index * 0.027),
                    emissive,
                    0.0005,
                )
            )
        details.extend(
            (
                cube(
                    "slider_end_stop_top",
                    (0.110, 0.018, 0.018),
                    (0.0, -0.061, 0.151),
                    opaque,
                    0.003,
                ),
                cube(
                    "slider_end_stop_bottom",
                    (0.110, 0.018, 0.018),
                    (0.0, -0.061, -0.151),
                    opaque,
                    0.003,
                ),
            )
        )

    add_theme_signature(theme, key, details, opaque, emissive)
    housing = join_into(housing, details, "housing")
    housing.parent = root
    return root


def new_root(key, type_id, theme):
    root = bpy.data.objects.new(
        f"PF_Visual_{key}_{theme['folder']}",
        None,
    )
    root.empty_display_type = "PLAIN_AXES"
    root["instrument_type_id"] = type_id
    root["theme_id"] = theme["id"]
    root["unity_mount_axis"] = "+Z"
    root["refinement_source"] = "Gemini review 2026-07-29"
    bpy.context.collection.objects.link(root)
    return root


def build_status(theme, opaque, emissive):
    root = new_root("StatusIndicator", "indicator.status", theme)
    housing_parts = [
        cube(
            "status_housing",
            (0.18, 0.045, 0.12),
            (0.0, -0.0225, 0.0),
            opaque,
            0.006,
        ),
        cube(
            "status_recess",
            (0.166, 0.012, 0.082),
            (0.0, -0.050, 0.0),
            opaque,
            0.004,
        ),
    ]
    if theme["id"] == "forge-brass":
        for x in (-0.074, 0.074):
            for z in (-0.046, 0.046):
                housing_parts.append(
                    bolt("status_rivet", x, z, 0.052, opaque, 0.0035)
                )
    elif theme["id"] == "kinetic-safety":
        housing_parts.extend(
            (
                cube(
                    "status_guard_top",
                    (0.174, 0.014, 0.012),
                    (0.0, -0.056, 0.052),
                    emissive,
                    0.002,
                ),
                cube(
                    "status_guard_bottom",
                    (0.174, 0.014, 0.012),
                    (0.0, -0.056, -0.052),
                    emissive,
                    0.002,
                ),
            )
        )
    housing = common.join_objects(housing_parts, "housing")
    housing.parent = root
    indicator = bpy.data.objects.new("indicator", None)
    indicator.parent = root
    bpy.context.collection.objects.link(indicator)
    state_nodes = []
    for index, name in enumerate(
        ("status_safe", "status_warn", "status_danger")
    ):
        segment = cube(
            name,
            (0.045, 0.015, 0.052),
            (-0.055 + index * 0.055, -0.061, 0.0),
            emissive,
            0.007 if theme["id"] == "forge-brass" else 0.003,
        )
        segment.parent = indicator
        state_nodes.append(segment)
    return root


def build_window_meter(theme, opaque, emissive):
    root = new_root("WindowMeter", "meter.window", theme)
    frame_depth = 0.085 if theme["id"] == "orbital-analog" else 0.105
    frame_parts = [
        cube(
            "window_meter_back",
            (1.20, frame_depth, 0.75),
            (0.0, -frame_depth * 0.5, 0.0),
            opaque,
            0.018,
        ),
        cube(
            "window_meter_top_rail",
            (1.12, 0.030, 0.055),
            (0.0, -frame_depth - 0.015, 0.325),
            emissive,
            0.012,
        ),
        cube(
            "window_meter_bottom_rail",
            (1.12, 0.030, 0.055),
            (0.0, -frame_depth - 0.015, -0.325),
            emissive,
            0.012,
        ),
        torus(
            "window_meter_dial_ring",
            0.315,
            0.010,
            frame_depth + 0.048,
            emissive,
        ),
    ]
    for x in (-0.54, 0.54):
        for z in (-0.31, 0.31):
            frame_parts.append(
                bolt("window_meter_fastener", x, z, frame_depth + 0.034, opaque, 0.012)
            )
    housing = common.join_objects(frame_parts, "housing")
    housing.parent = root
    dial = cylinder(
        "dial",
        0.295,
        0.028,
        frame_depth + 0.030,
        opaque,
        48,
    )
    dial.parent = root
    pivot_point = (0.0, -frame_depth - 0.055, -0.075)
    needle_part = cube(
        "needle",
        (0.030, 0.016, 0.440),
        (0.0, pivot_point[1], 0.145),
        emissive,
        0.006,
    )
    hub = cylinder(
        "window_needle_hub",
        0.046,
        0.020,
        frame_depth + 0.060,
        opaque,
        20,
    )
    hub.location.z = pivot_point[2]
    pivot, needle = controls.parent_at_pivot(
        [needle_part, hub],
        "needle",
        pivot_point,
        root,
    )
    pivot.name = "needle_pivot"
    needle.name = "needle"
    return root


def build_window_panel(theme, opaque, emissive):
    root = new_root("WindowPanel", "panel.window", theme)
    depth = 0.105 if theme["id"] == "orbital-analog" else 0.135
    frame_parts = [
        cube(
            "panel_back",
            (1.60, depth, 0.90),
            (0.0, -depth * 0.5, 0.0),
            opaque,
            0.025,
        ),
        cube(
            "panel_left_structure",
            (0.105, 0.045, 0.78),
            (-0.70, -depth - 0.022, 0.0),
            emissive,
            0.018,
        ),
        cube(
            "panel_right_structure",
            (0.105, 0.045, 0.78),
            (0.70, -depth - 0.022, 0.0),
            emissive,
            0.018,
        ),
        cube(
            "panel_upper_duct",
            (1.25, 0.040, 0.070),
            (0.0, -depth - 0.020, 0.355),
            emissive,
            0.014,
        ),
        cube(
            "panel_lower_duct",
            (1.25, 0.040, 0.070),
            (0.0, -depth - 0.020, -0.355),
            emissive,
            0.014,
        ),
    ]
    for x in (-0.72, 0.72):
        for z in (-0.36, 0.36):
            frame_parts.append(
                bolt("panel_fastener", x, z, depth + 0.046, opaque, 0.013)
            )
    housing = common.join_objects(frame_parts, "housing")
    housing.parent = root
    display = cube(
        "display_field",
        (1.08, 0.020, 0.48),
        (0.0, -depth - 0.052, 0.02),
        emissive,
        0.018,
    )
    display.parent = root
    pivot_point = (0.0, -depth - 0.072, -0.185)
    vane_part = cube(
        "vane",
        (0.036, 0.018, 0.43),
        (0.0, pivot_point[1], 0.030),
        opaque,
        0.007,
    )
    pivot = bpy.data.objects.new("vane_pivot", None)
    pivot.empty_display_type = "ARROWS"
    pivot.location = pivot_point
    pivot.parent = root
    bpy.context.collection.objects.link(pivot)
    vane_part.parent = pivot
    vane_part.location = (0.0, 0.0, 0.215)
    vane_part.name = "vane"
    return root


def build_new(key, type_id, theme):
    opaque = simple_material(
        f"MAT_{theme['folder']}_Atlas_Refined",
        theme["housing"],
    )
    emissive = simple_material(
        f"MAT_{theme['folder']}_Emissive_Refined",
        theme["emissive"],
        emissive=True,
    )
    if key == "StatusIndicator":
        return build_status(theme, opaque, emissive)
    if key == "WindowMeter":
        return build_window_meter(theme, opaque, emissive)
    if key == "WindowPanel":
        return build_window_panel(theme, opaque, emissive)
    raise RuntimeError(f"Unsupported new asset {key}")


def validate_and_report(
    root,
    key,
    type_id,
    theme,
    limits,
    triangle_budget,
    renderer_budget,
):
    meshes = root_meshes(root)
    common.apply_transforms(meshes)
    stats = common.mesh_stats(meshes)
    stats.update(
        {
            "asset": f"{key}_{theme['folder']}_Refined",
            "instrument_type_id": type_id,
            "theme_id": theme["id"],
            "unity_mount_axis": "+Z",
            "final_triangle_budget": triangle_budget,
            "renderer_budget": renderer_budget,
            "material_budget": 2,
            "colliders": 0,
            "realtime_lights": 0,
            "review_source": "Gemini review 2026-07-29",
            "review_changes": REVIEW_CHANGES[key],
        }
    )
    if stats["triangles"] > triangle_budget:
        raise RuntimeError(f"{key}: triangle budget exceeded: {stats}")
    if stats["mesh_objects"] > renderer_budget:
        raise RuntimeError(f"{key}: renderer budget exceeded: {stats}")
    if stats["materials"] > 2:
        raise RuntimeError(f"{key}: material budget exceeded: {stats}")
    if any(
        value > limit
        for value, limit in zip(stats["unity_bounds_m"], limits)
    ):
        raise RuntimeError(f"{key}: bounds exceeded: {stats}")
    if stats["blender_bounds_max_m"][1] > 0.001:
        raise RuntimeError(f"{key}: extends behind mount plane: {stats}")
    return meshes, stats


def save_candidate(
    project_root,
    key,
    theme,
    root,
    meshes,
    stats,
    skip_previews,
):
    source_dir = (
        project_root
        / "ArtSource/Blender/Refined"
        / theme["folder"]
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates"
        / theme["folder"]
        / "Models"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    if not skip_previews:
        controls.create_preview(
            meshes,
            0.0,
            source_dir
            / f"Preview_{key}_{theme['folder']}_Refined.png",
        )
    root["refinement_source"] = "Gemini review 2026-07-29"
    blend_path = (
        source_dir
        / f"BL_{key}_{theme['folder']}_Refined.blend"
    )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    blend_path.with_suffix(".blend1").unlink(missing_ok=True)
    fbx_path = (
        model_dir
        / f"SM_{key}_{theme['folder']}_Refined.fbx"
    )
    fbm_path = fbx_path.with_suffix(".fbm")
    if fbm_path.exists():
        shutil.rmtree(fbm_path)
    common.export_fbx(root, fbx_path)
    report_path = (
        source_dir
        / f"BL_{key}_{theme['folder']}_Refined.report.json"
    )
    report_path.write_text(
        json.dumps(stats, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "asset": stats["asset"],
                "triangles": stats["triangles"],
                "renderers": stats["mesh_objects"],
                "bounds": stats["unity_bounds_m"],
                "status": "PASS",
            }
        )
    )


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    for theme in THEMES:
        for (
            key,
            type_id,
            limits,
            triangle_budget,
            renderer_budget,
        ) in ASSETS:
            if args.only and key not in args.only:
                continue
            if key in ("MeterRound", "Lever", "StatusIndicator"):
                common.clean_scene()
                root = build_representative(
                    key,
                    type_id,
                    theme,
                )
            elif key in ("WindowMeter", "WindowPanel"):
                common.clean_scene()
                root = build_new(key, type_id, theme)
            else:
                source = (
                    project_root
                    / "ArtSource/Blender"
                    / theme["folder"]
                    / f"BL_{key}_{theme['folder']}.blend"
                )
                if not source.is_file():
                    raise FileNotFoundError(source)
                bpy.ops.wm.open_mainfile(filepath=str(source))
                root = refine_existing(key, theme)
            meshes, stats = validate_and_report(
                root,
                key,
                type_id,
                theme,
                limits,
                triangle_budget,
                renderer_budget,
            )
            save_candidate(
                project_root,
                key,
                theme,
                root,
                meshes,
                stats,
                args.skip_previews,
            )


if __name__ == "__main__":
    main()
