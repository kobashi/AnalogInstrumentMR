"""Generate the Kinetic Safety V4 hard-surface retopo candidate set.

The lever is generated separately by generate_hardsurface_lever_retopo_v3.py.
Every mesh in this file is built from a clean cage rather than a Boolean result
or a decimated high-poly mesh.
"""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_hardsurface_lever_prototype as hs
import generate_hardsurface_lever_retopo_v3 as retopo
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


ASSETS = (
    ("MeterRound", "meter.round", 5000),
    ("Toggle", "control.toggle", 5000),
    ("Rotary", "control.rotary", 5000),
    ("Button", "control.button", 5000),
    ("Lamp", "indicator.lamp", 5000),
    ("Throttle", "control.throttle", 5000),
    ("PowerSlider", "control.power_slider", 5000),
    ("StatusIndicator", "indicator.status", 5000),
    ("WindowMeter", "meter.window", 25000),
    ("WindowPanel", "panel.window", 25000),
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[item[0] for item in ASSETS],
    )
    parser.add_argument("--skip-previews", action="store_true")
    return parser.parse_args(args)


def materials():
    return {
        "graphite": hs.material(
            "MAT_Kinetic_V4_Graphite",
            (0.018, 0.026, 0.038, 1.0),
            0.62,
            0.40,
        ),
        "gunmetal": hs.material(
            "MAT_Kinetic_V4_Gunmetal",
            (0.11, 0.15, 0.18, 1.0),
            0.88,
            0.28,
        ),
        "cyan": hs.material(
            "MAT_Kinetic_V4_Cyan",
            (0.04, 0.40, 0.54, 1.0),
            0.18,
            0.22,
            emission=(0.08, 0.78, 1.0, 1.0),
        ),
    }


def root_for(key, type_id):
    root = bpy.data.objects.new(
        f"PF_Visual_{key}_KineticSafety_V4",
        None,
    )
    root.empty_display_type = "PLAIN_AXES"
    root["instrument_type_id"] = type_id
    root["theme_id"] = "kinetic-safety"
    root["unity_mount_axis"] = "+Z"
    root["modeling_method"] = "clean hard-surface retopo cage"
    root["quality_floor"] = "Lever_KineticSafety_HS_V3_Retopo"
    bpy.context.collection.objects.link(root)
    return root


def prism(name, width, height, chamfer, y_back, y_front, material, z=0.0):
    obj = retopo.clean_prism(
        name,
        hs.chamfered_outline(width, height, chamfer, z),
        y_back,
        y_front,
        material,
    )
    retopo.bevel(obj, min(chamfer * 0.24, 0.0032), 1)
    return obj


def shell(
    name,
    width,
    height,
    chamfer,
    recess_width,
    recess_height,
    recess_chamfer,
    depth,
    recess_depth,
    material,
):
    obj = retopo.recessed_shell(
        name,
        hs.chamfered_outline(width, height, chamfer),
        hs.chamfered_outline(
            recess_width,
            recess_height,
            recess_chamfer,
        ),
        0.0,
        -depth,
        -recess_depth,
        material,
    )
    retopo.bevel(obj, min(chamfer * 0.22, 0.0034), 2)
    return obj


def cylinder_y(name, radius, depth, outward, material, vertices=16):
    obj = hs.cylinder(
        name,
        radius,
        depth,
        (0.0, -outward, 0.0),
        material,
        vertices,
    )
    retopo.bevel(obj, min(radius * 0.08, 0.0012), 1)
    return obj


def cylinder_x(name, radius, depth, location, material, vertices=16):
    obj = retopo.cylinder_x(
        name,
        radius,
        depth,
        location,
        material,
        vertices,
    )
    retopo.bevel(obj, min(radius * 0.08, 0.0012), 1)
    return obj


def cylinder_z(name, radius, height, location, material, vertices=16):
    obj = retopo.cylinder_z(
        name,
        radius,
        height,
        location,
        material,
        vertices,
    )
    retopo.bevel(obj, min(radius * 0.08, 0.0012), 1)
    return obj


def attach(root, objects, name):
    result = common.join_objects(objects, name)
    result.parent = root
    return result


def parent_movable(objects, name, pivot_point, root):
    for obj in objects:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(
            location=False,
            rotation=True,
            scale=True,
        )
    return controls.parent_at_pivot(
        objects,
        name,
        pivot_point,
        root,
    )


def accent_bar(name, width, height, x, z, outward, material):
    obj = prism(
        name,
        width,
        height,
        min(width, height) * 0.22,
        -outward,
        -outward - 0.003,
        material,
        0.0,
    )
    obj.location.x = x
    obj.location.z = z
    return obj


def fastener(name, x, z, outward, material, radius=0.003):
    obj = cylinder_y(name, radius, 0.0024, outward, material, 10)
    obj.location.x = x
    obj.location.z = z
    return obj


def build_meter():
    mats = materials()
    root = root_for("MeterRound", "meter.round")
    housing = shell(
        "housing",
        0.150,
        0.150,
        0.014,
        0.116,
        0.116,
        0.009,
        0.050,
        0.043,
        mats["graphite"],
    )
    bezel = cylinder_y(
        "bezel",
        0.059,
        0.013,
        0.050,
        mats["gunmetal"],
        24,
    )
    dial = cylinder_y(
        "dial",
        0.050,
        0.004,
        0.063,
        mats["graphite"],
        32,
    )
    housing_parts = [housing, bezel]
    for index, (x, z) in enumerate(
        ((-0.061, -0.061), (0.061, -0.061),
         (-0.061, 0.061), (0.061, 0.061))
    ):
        housing_parts.append(
            fastener(
                f"fastener_{index}",
                x,
                z,
                0.052,
                mats["gunmetal"],
            )
        )
    attach(root, housing_parts, "housing")

    dial_parts = [dial]
    for index in range(21):
        t = index / 20
        angle = math.radians(-130.0 + 260.0 * t)
        major = index % 5 == 0
        radius = 0.041
        tick = accent_bar(
            f"tick_{index}",
            0.0023 if major else 0.0014,
            0.008 if major else 0.0045,
            math.sin(angle) * radius,
            math.cos(angle) * radius,
            0.066,
            mats["cyan"],
        )
        tick.rotation_euler.y = angle
        dial_parts.append(tick)
    attach(root, dial_parts, "dial")

    pivot_point = (0.0, -0.069, 0.0)
    blade = prism(
        "needle_blade",
        0.0035,
        0.040,
        0.001,
        -0.069,
        -0.072,
        mats["cyan"],
        0.020,
    )
    hub = cylinder_y(
        "needle_hub",
        0.0075,
        0.005,
        0.069,
        mats["gunmetal"],
        16,
    )
    pivot, needle = parent_movable(
        [blade, hub],
        "needle",
        pivot_point,
        root,
    )
    pivot.name = "needle_pivot"
    needle.name = "needle"
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_toggle():
    mats = materials()
    root = root_for("Toggle", "control.toggle")
    housing = shell(
        "housing",
        0.120,
        0.140,
        0.010,
        0.074,
        0.094,
        0.007,
        0.045,
        0.038,
        mats["graphite"],
    )
    collar = cylinder_y(
        "toggle_hex_collar",
        0.026,
        0.010,
        0.046,
        mats["gunmetal"],
        6,
    )
    guard_left = prism(
        "guard_left", 0.016, 0.100, 0.004,
        -0.043, -0.060, mats["graphite"],
    )
    guard_left.location.x = -0.045
    guard_right = guard_left.copy()
    guard_right.data = guard_left.data.copy()
    guard_right.name = "guard_right"
    guard_right.location.x = 0.045
    bpy.context.collection.objects.link(guard_right)
    marks = [
        accent_bar("off_mark", 0.026, 0.005, 0.0, -0.050, 0.061, mats["cyan"]),
        accent_bar("on_mark", 0.026, 0.005, 0.0, 0.050, 0.061, mats["cyan"]),
    ]
    attach(
        root,
        [housing, collar, guard_left, guard_right] + marks,
        "housing",
    )

    pivot_point = (0.0, -0.057, 0.0)
    shaft = cylinder_z(
        "switch_shaft",
        0.006,
        0.088,
        (0.0, pivot_point[1], 0.036),
        mats["gunmetal"],
        14,
    )
    axle = cylinder_x(
        "switch_axle",
        0.009,
        0.040,
        pivot_point,
        mats["gunmetal"],
        16,
    )
    grip = prism(
        "switch_tip",
        0.022,
        0.025,
        0.006,
        -0.050,
        -0.066,
        mats["graphite"],
        0.080,
    )
    pivot, switch = parent_movable(
        [shaft, axle, grip],
        "switch",
        pivot_point,
        root,
    )
    pivot.name = "switch_pivot"
    switch.name = "switch"
    pivot.rotation_euler.x = math.radians(-12.0)
    return root, pivot_point, (1.0, 0.0, 0.0)


def build_rotary():
    mats = materials()
    root = root_for("Rotary", "control.rotary")
    housing = shell(
        "housing",
        0.150,
        0.150,
        0.013,
        0.116,
        0.116,
        0.009,
        0.048,
        0.041,
        mats["graphite"],
    )
    bezel = cylinder_y(
        "knob_bezel",
        0.050,
        0.012,
        0.049,
        mats["gunmetal"],
        20,
    )
    details = [housing, bezel]
    for index in range(9):
        angle = math.radians(-120 + 30 * index)
        details.append(
            accent_bar(
                f"rotary_tick_{index}",
                0.003,
                0.010,
                math.sin(angle) * 0.061,
                math.cos(angle) * 0.061,
                0.063,
                mats["cyan"],
            )
        )
        details[-1].rotation_euler.y = angle
    attach(root, details, "housing")

    pivot_point = (0.0, -0.061, 0.0)
    knob = cylinder_y(
        "knob",
        0.036,
        0.030,
        0.061,
        mats["graphite"],
        16,
    )
    grip_ribs = [knob]
    for index in range(8):
        angle = math.radians(index * 45)
        rib = prism(
            f"knob_rib_{index}",
            0.004,
            0.016,
            0.001,
            -0.091,
            -0.095,
            mats["gunmetal"],
            0.0,
        )
        rib.location.x = math.sin(angle) * 0.027
        rib.location.z = math.cos(angle) * 0.027
        rib.rotation_euler.y = angle
        grip_ribs.append(rib)
    pointer = accent_bar(
        "knob_pointer",
        0.004,
        0.024,
        0.0,
        0.018,
        0.096,
        mats["cyan"],
    )
    grip_ribs.append(pointer)
    pivot, knob = parent_movable(
        grip_ribs,
        "knob",
        pivot_point,
        root,
    )
    pivot.name = "knob_pivot"
    knob.name = "knob"
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_button():
    mats = materials()
    root = root_for("Button", "control.button")
    housing = shell(
        "housing",
        0.130,
        0.130,
        0.012,
        0.092,
        0.092,
        0.010,
        0.046,
        0.040,
        mats["graphite"],
    )
    bezel = cylinder_y(
        "button_bezel",
        0.048,
        0.012,
        0.047,
        mats["gunmetal"],
        20,
    )
    attach(root, [housing, bezel], "housing")

    travel = bpy.data.objects.new("button_travel", None)
    travel.location = (0.0, -0.062, 0.0)
    travel.parent = root
    bpy.context.collection.objects.link(travel)
    cap = cylinder_y(
        "button",
        0.038,
        0.020,
        0.062,
        mats["graphite"],
        16,
    )
    cap.parent = travel
    glyph = accent_bar(
        "button_glyph",
        0.030,
        0.007,
        0.0,
        0.0,
        0.084,
        mats["cyan"],
    )
    glyph.parent = travel
    return root, tuple(travel.location), (0.0, 1.0, 0.0)


def build_lamp():
    mats = materials()
    root = root_for("Lamp", "indicator.lamp")
    housing = shell(
        "housing",
        0.140,
        0.110,
        0.012,
        0.104,
        0.074,
        0.008,
        0.045,
        0.038,
        mats["graphite"],
    )
    cage = [
        housing,
        cylinder_y(
            "lamp_retainer",
            0.040,
            0.012,
            0.046,
            mats["gunmetal"],
            20,
        ),
    ]
    for x in (-0.047, 0.047):
        rail = prism(
            "lamp_guard",
            0.010,
            0.078,
            0.003,
            -0.047,
            -0.065,
            mats["graphite"],
        )
        rail.location.x = x
        cage.append(rail)
    attach(root, cage, "housing")
    indicator = bpy.data.objects.new("indicator", None)
    indicator.parent = root
    bpy.context.collection.objects.link(indicator)
    lens = cylinder_y(
        "indicator_lens",
        0.032,
        0.016,
        0.059,
        mats["cyan"],
        24,
    )
    lens.parent = indicator
    return root, (0.0, -0.059, 0.0), (0.0, 0.0, 0.0)


def build_throttle():
    mats = materials()
    root = root_for("Throttle", "control.throttle")
    housing = shell(
        "housing",
        0.240,
        0.340,
        0.018,
        0.188,
        0.286,
        0.013,
        0.060,
        0.052,
        mats["graphite"],
    )
    housing_parts = [housing]
    for x in (-0.088, 0.088):
        rail = prism(
            "throttle_guard",
            0.028,
            0.280,
            0.007,
            -0.052,
            -0.078,
            mats["graphite"],
        )
        rail.location.x = x
        housing_parts.append(rail)
    for index in range(7):
        housing_parts.append(
            accent_bar(
                f"throttle_scale_{index}",
                0.018,
                0.004,
                0.067,
                -0.126 + index * 0.042,
                0.080,
                mats["cyan"],
            )
        )
    for z in (-0.142, 0.142):
        housing_parts.append(
            prism(
                "throttle_stop",
                0.070,
                0.018,
                0.004,
                -0.074,
                -0.092,
                mats["gunmetal"],
                z,
            )
        )
    attach(root, housing_parts, "housing")

    pivot_point = (0.0, -0.080, -0.112)
    axle = cylinder_x(
        "throttle_axle",
        0.018,
        0.112,
        pivot_point,
        mats["gunmetal"],
        20,
    )
    arms = []
    for x in (-0.038, 0.038):
        arm = prism(
            "throttle_arm",
            0.014,
            0.215,
            0.004,
            -0.073,
            -0.090,
            mats["gunmetal"],
            -0.004,
        )
        arm.location.x = x
        arms.append(arm)
    grip = prism(
        "throttle_grip",
        0.118,
        0.056,
        0.012,
        -0.068,
        -0.108,
        mats["graphite"],
        0.120,
    )
    grip_light = accent_bar(
        "throttle_grip_light",
        0.064,
        0.007,
        0.0,
        0.128,
        0.110,
        mats["cyan"],
    )
    pivot, handle = parent_movable(
        [axle] + arms + [grip, grip_light],
        "throttle_handle",
        pivot_point,
        root,
    )
    pivot.name = "throttle_pivot"
    handle.name = "throttle_handle"
    return root, pivot_point, (1.0, 0.0, 0.0)


def build_slider():
    mats = materials()
    root = root_for("PowerSlider", "control.power_slider")
    housing = shell(
        "housing",
        0.160,
        0.340,
        0.015,
        0.118,
        0.292,
        0.010,
        0.052,
        0.045,
        mats["graphite"],
    )
    housing_parts = [housing]
    for x in (-0.038, 0.038):
        rail = prism(
            "slider_rail",
            0.012,
            0.264,
            0.003,
            -0.047,
            -0.065,
            mats["gunmetal"],
        )
        rail.location.x = x
        housing_parts.append(rail)
    for index in range(11):
        housing_parts.append(
            accent_bar(
                f"slider_scale_{index}",
                0.014,
                0.0035,
                0.060,
                -0.130 + index * 0.026,
                0.069,
                mats["cyan"],
            )
        )
    for z in (-0.148, 0.148):
        housing_parts.append(
            prism(
                "slider_stop",
                0.104,
                0.016,
                0.004,
                -0.061,
                -0.078,
                mats["gunmetal"],
                z,
            )
        )
    attach(root, housing_parts, "housing")

    travel = bpy.data.objects.new("slider_travel", None)
    travel.location = (0.0, -0.074, 0.0)
    travel.parent = root
    bpy.context.collection.objects.link(travel)
    carriage = prism(
        "slider_handle",
        0.110,
        0.050,
        0.010,
        -0.068,
        -0.100,
        mats["graphite"],
    )
    carriage.parent = travel
    grip = prism(
        "slider_grip",
        0.080,
        0.018,
        0.005,
        -0.099,
        -0.116,
        mats["gunmetal"],
    )
    grip.parent = travel
    light = accent_bar(
        "slider_light",
        0.056,
        0.005,
        0.0,
        0.0,
        0.117,
        mats["cyan"],
    )
    light.parent = travel
    return root, tuple(travel.location), (0.0, 0.0, 1.0)


def build_status():
    mats = materials()
    root = root_for("StatusIndicator", "indicator.status")
    housing = shell(
        "housing",
        0.180,
        0.120,
        0.012,
        0.150,
        0.082,
        0.008,
        0.048,
        0.041,
        mats["graphite"],
    )
    housing_parts = [housing]
    for z in (-0.050, 0.050):
        housing_parts.append(
            prism(
                "status_guard",
                0.170,
                0.012,
                0.003,
                -0.045,
                -0.061,
                mats["gunmetal"],
                z,
            )
        )
    attach(root, housing_parts, "housing")
    indicator = bpy.data.objects.new("indicator", None)
    indicator.parent = root
    bpy.context.collection.objects.link(indicator)
    for index, name in enumerate(
        ("status_safe", "status_warn", "status_danger")
    ):
        x = -0.054 + index * 0.054
        surround = prism(
            f"{name}_surround",
            0.046,
            0.064,
            0.007,
            -0.043,
            -0.058,
            mats["gunmetal"],
        )
        surround.location.x = x
        surround.parent = indicator
        lens = prism(
            name,
            0.034,
            0.050,
            0.006,
            -0.058,
            -0.065,
            mats["cyan"],
        )
        lens.location.x = x
        lens.parent = indicator
    return root, (0.0, -0.058, 0.0), (0.0, 0.0, 0.0)


def build_window_meter():
    mats = materials()
    root = root_for("WindowMeter", "meter.window")
    housing = shell(
        "housing",
        1.20,
        0.75,
        0.045,
        1.04,
        0.59,
        0.030,
        0.105,
        0.090,
        mats["graphite"],
    )
    frame_parts = [housing]
    for x in (-0.525, 0.525):
        rail = prism(
            "window_meter_side",
            0.080,
            0.610,
            0.018,
            -0.090,
            -0.135,
            mats["gunmetal"],
        )
        rail.location.x = x
        frame_parts.append(rail)
    for index, (x, z) in enumerate(
        ((-0.545, -0.330), (0.545, -0.330),
         (-0.545, 0.330), (0.545, 0.330))
    ):
        frame_parts.append(
            fastener(
                f"window_fastener_{index}",
                x,
                z,
                0.138,
                mats["gunmetal"],
                0.012,
            )
        )
    attach(root, frame_parts, "housing")
    dial = cylinder_y(
        "dial",
        0.285,
        0.025,
        0.137,
        mats["gunmetal"],
        40,
    )
    dial.parent = root
    for index in range(25):
        t = index / 24
        angle = math.radians(-130 + 260 * t)
        tick = accent_bar(
            f"window_tick_{index}",
            0.010 if index % 6 else 0.018,
            0.042 if index % 6 else 0.070,
            math.sin(angle) * 0.235,
            math.cos(angle) * 0.235,
            0.165,
            mats["cyan"],
        )
        tick.rotation_euler.y = angle
        tick.parent = root
    pivot_point = (0.0, -0.170, -0.075)
    needle = prism(
        "needle",
        0.020,
        0.430,
        0.005,
        -0.169,
        -0.184,
        mats["cyan"],
        0.140,
    )
    hub = cylinder_y(
        "needle_hub",
        0.044,
        0.020,
        0.169,
        mats["graphite"],
        20,
    )
    hub.location.z = pivot_point[2]
    pivot, needle = parent_movable(
        [needle, hub],
        "needle",
        pivot_point,
        root,
    )
    pivot.name = "needle_pivot"
    needle.name = "needle"
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_window_panel():
    mats = materials()
    root = root_for("WindowPanel", "panel.window")
    housing = shell(
        "housing",
        1.60,
        0.90,
        0.060,
        1.38,
        0.68,
        0.040,
        0.135,
        0.115,
        mats["graphite"],
    )
    frame_parts = [housing]
    for x in (-0.690, 0.690):
        rail = prism(
            "panel_side_structure",
            0.105,
            0.720,
            0.024,
            -0.112,
            -0.170,
            mats["gunmetal"],
        )
        rail.location.x = x
        frame_parts.append(rail)
    for z in (-0.365, 0.365):
        rail = prism(
            "panel_cross_structure",
            1.250,
            0.075,
            0.020,
            -0.112,
            -0.164,
            mats["gunmetal"],
            z,
        )
        frame_parts.append(rail)
    for index, (x, z) in enumerate(
        ((-0.735, -0.390), (0.735, -0.390),
         (-0.735, 0.390), (0.735, 0.390))
    ):
        frame_parts.append(
            fastener(
                f"panel_fastener_{index}",
                x,
                z,
                0.173,
                mats["gunmetal"],
                0.014,
            )
        )
    attach(root, frame_parts, "housing")
    display = prism(
        "display_field",
        1.160,
        0.500,
        0.030,
        -0.168,
        -0.190,
        mats["gunmetal"],
        0.025,
    )
    display.parent = root
    for index, z in enumerate((0.170, 0.070, -0.030)):
        trace = accent_bar(
            f"display_trace_{index}",
            0.82 - index * 0.12,
            0.012,
            -0.06 + index * 0.05,
            z,
            0.192,
            mats["cyan"],
        )
        trace.parent = root
    pivot_point = (0.0, -0.196, -0.185)
    vane = prism(
        "vane",
        0.030,
        0.400,
        0.007,
        -0.195,
        -0.214,
        mats["cyan"],
        0.015,
    )
    hub = cylinder_y(
        "vane_hub",
        0.040,
        0.022,
        0.195,
        mats["graphite"],
        20,
    )
    hub.location.z = pivot_point[2]
    pivot, vane = parent_movable(
        [vane, hub],
        "vane",
        pivot_point,
        root,
    )
    pivot.name = "vane_pivot"
    vane.name = "vane"
    return root, pivot_point, (0.0, 1.0, 0.0)


BUILDERS = {
    "MeterRound": build_meter,
    "Toggle": build_toggle,
    "Rotary": build_rotary,
    "Button": build_button,
    "Lamp": build_lamp,
    "Throttle": build_throttle,
    "PowerSlider": build_slider,
    "StatusIndicator": build_status,
    "WindowMeter": build_window_meter,
    "WindowPanel": build_window_panel,
}


def meshes_under(root):
    return [obj for obj in root.children_recursive if obj.type == "MESH"]


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def generate_one(project_root, key, type_id, triangle_budget, skip_previews):
    common.clean_scene()
    root, pivot_position, local_axis = BUILDERS[key]()
    meshes = meshes_under(root)
    common.apply_transforms(meshes)
    source_stats = retopo.topology_stats(meshes)
    if source_stats["non_manifold_edges"] != 0:
        raise RuntimeError(f"{key}: non-manifold source: {source_stats}")
    if source_stats["zero_area_faces"] != 0:
        raise RuntimeError(f"{key}: degenerate source: {source_stats}")

    source_dir = (
        project_root
        / "ArtSource/Blender/HardSurfacePrototype/KineticSafety/V4"
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/"
        "KineticSafety/HardSurfacePrototype/V4"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    if not skip_previews:
        controls.create_preview(
            meshes,
            0.0,
            source_dir / f"Preview_{key}_KineticSafety_HS_V4.png",
        )
        retopo.render_topology_preview(
            meshes,
            source_dir / f"Preview_{key}_KineticSafety_HS_V4_Topology.png",
        )
    save_blend(
        source_dir / f"BL_{key}_KineticSafety_HS_V4_Retopo.blend"
    )

    retopo.triangulate(meshes)
    triangulated_stats = retopo.topology_stats(meshes)
    if triangulated_stats["non_manifold_edges"] != 0:
        raise RuntimeError(f"{key}: non-manifold final: {triangulated_stats}")
    if triangulated_stats["zero_area_faces"] != 0:
        raise RuntimeError(f"{key}: degenerate final: {triangulated_stats}")
    if triangulated_stats["faces"] > triangle_budget:
        raise RuntimeError(
            f"{key}: triangle budget exceeded: "
            f"{triangulated_stats['faces']} > {triangle_budget}"
        )
    save_blend(
        source_dir / f"BL_{key}_KineticSafety_HS_V4_Triangulated.blend"
    )
    fbx_path = model_dir / f"SM_{key}_KineticSafety_HS_V4_Retopo.fbx"
    fbm_path = fbx_path.with_suffix(".fbm")
    if fbm_path.exists():
        shutil.rmtree(fbm_path)
    common.export_fbx(root, fbx_path)

    report = {
        "asset": f"{key}_KineticSafety_HS_V4_Retopo",
        "quality_floor": "Lever_KineticSafety_HS_V3_Retopo",
        "source_topology": source_stats,
        "triangulated_topology": triangulated_stats,
        "triangle_budget": triangle_budget,
        "pivot": {
            "position": list(pivot_position),
            "local_axis": list(local_axis),
        },
        "fbx": str(fbx_path.relative_to(project_root)),
        "production_integrated": False,
    }
    (
        source_dir / f"{key}_KineticSafety_HS_V4_Retopo.report.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report))


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    only = set(args.only or ())
    for key, type_id, triangle_budget in ASSETS:
        if only and key not in only:
            continue
        generate_one(
            project_root,
            key,
            type_id,
            triangle_budget,
            args.skip_previews,
        )


if __name__ == "__main__":
    main()
