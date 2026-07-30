"""Generate the remaining eight V5 grayscale theme-specific model families."""

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
import generate_theme_silhouette_v5 as base


ASSETS = {
    "Toggle": ("control.toggle", 5000),
    "Rotary": ("control.rotary", 5000),
    "Button": ("control.button", 5000),
    "Lamp": ("indicator.lamp", 5000),
    "StatusIndicator": ("indicator.status", 5000),
    "Throttle": ("control.throttle", 5000),
    "PowerSlider": ("control.power_slider", 5000),
    "WindowMeter": ("meter.window", 25000),
}


def parent_keep_world(obj, parent):
    """Parent an already-positioned part without applying the parent's offset twice."""
    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world_matrix
    return obj


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-topology", action="store_true")
    parser.add_argument("--only", nargs="+", choices=tuple(ASSETS))
    return parser.parse_args(args)


def orbital_plate(root, key, type_id, mats, width, height):
    body = v4.prism(
        "orbital_thin_plate",
        width,
        height,
        min(width, height) * 0.075,
        0.0,
        -0.024,
        mats["body"],
    )
    parts = [body]
    for z in (-height * 0.43, height * 0.43):
        brow = v4.prism(
            "orbital_edge_brow",
            width * 0.62,
            height * 0.075,
            height * 0.025,
            -0.022,
            -0.038,
            mats["metal"],
            z,
        )
        parts.append(brow)
    base.attach(root, parts, "housing")


def forge_plate(root, key, type_id, mats, width, height):
    body = v4.prism(
        "forge_cast_plate",
        width,
        height,
        min(width, height) * 0.15,
        0.0,
        -0.040,
        mats["body"],
    )
    boss = v4.cylinder_y(
        "forge_central_boss",
        min(width, height) * 0.34,
        0.014,
        0.043,
        mats["metal"],
        20,
    )
    parts = [body, boss]
    for x in (-width * 0.39, width * 0.39):
        for z in (-height * 0.39, height * 0.39):
            lug = v4.prism(
                "forge_mount_lug",
                width * 0.12,
                height * 0.12,
                min(width, height) * 0.035,
                0.0,
                -0.045,
                mats["body"],
                z,
            )
            lug.location.x = x
            parts.append(lug)
    base.attach(root, parts, "housing")


def kinetic_plate(root, key, type_id, mats, width, height):
    body = v4.shell(
        "kinetic_armored_plate",
        width,
        height,
        min(width, height) * 0.11,
        width * 0.62,
        height * 0.68,
        min(width, height) * 0.07,
        0.046,
        0.039,
        mats["body"],
    )
    parts = [body]
    for x in (-width * 0.40, width * 0.40):
        guard = v4.prism(
            "kinetic_side_guard",
            width * 0.13,
            height * 0.68,
            min(width, height) * 0.045,
            -0.040,
            -0.065,
            mats["metal"],
        )
        guard.location.x = x
        parts.append(guard)
    base.attach(root, parts, "housing")


def build_toggle(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "Toggle", "control.toggle")
    if theme == "OrbitalAnalog":
        orbital_plate(root, "Toggle", "control.toggle", mats, 0.096, 0.132)
        pivot_point = (0.0, -0.046, 0.0)
        collar = v4.cylinder_y(
            "orbital_low_collar", 0.016, 0.016, 0.030,
            mats["metal"], 16,
        )
        collar.parent = root
        shaft_radius, shaft_height = 0.0042, 0.076
        grip = v4.prism(
            "orbital_flat_tip", 0.020, 0.018, 0.005,
            -0.043, -0.057, mats["body"], 0.066,
        )
    elif theme == "ForgeBrass":
        forge_plate(root, "Toggle", "control.toggle", mats, 0.112, 0.132)
        pivot_point = (0.0, -0.061, 0.0)
        collar = v4.cylinder_y(
            "forge_hex_nut", 0.024, 0.010, 0.052,
            mats["metal"], 6,
        )
        collar.parent = root
        shaft_radius, shaft_height = 0.006, 0.082
        grip = base.sphere(
            "forge_ball_tip", 0.014,
            (0.0, pivot_point[1], 0.078),
            mats["body"], 16, 8,
        )
    else:
        kinetic_plate(root, "Toggle", "control.toggle", mats, 0.124, 0.146)
        pivot_point = (0.0, -0.064, 0.0)
        collar = v4.cylinder_y(
            "kinetic_armored_collar", 0.025, 0.016, 0.052,
            mats["metal"], 8,
        )
        collar.parent = root
        shaft_radius, shaft_height = 0.007, 0.078
        grip = v4.prism(
            "kinetic_wedge_tip", 0.030, 0.028, 0.008,
            -0.058, -0.078, mats["body"], 0.070,
        )
    shaft = v4.cylinder_z(
        "switch_shaft",
        shaft_radius,
        shaft_height,
        (0.0, pivot_point[1], shaft_height * 0.46),
        mats["metal"],
        14,
    )
    axle = v4.cylinder_x(
        "switch_axle", shaft_radius * 1.5, 0.040,
        pivot_point, mats["metal"], 16,
    )
    pivot, switch = v4.parent_movable(
        [shaft, axle, grip], "switch", pivot_point, root,
    )
    pivot.name = "switch_pivot"
    switch.name = "switch"
    return root, pivot_point, (1.0, 0.0, 0.0)


def build_rotary(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "Rotary", "control.rotary")
    if theme == "OrbitalAnalog":
        orbital_plate(root, "Rotary", "control.rotary", mats, 0.132, 0.132)
        pivot_point = (0.0, -0.048, 0.0)
        knob = v4.cylinder_y(
            "orbital_umbrella_knob", 0.034, 0.020, 0.048,
            mats["body"], 20,
        )
        crown = v4.cylinder_y(
            "orbital_knob_crown", 0.025, 0.010, 0.068,
            mats["metal"], 20,
        )
        socket = v4.cylinder_y(
            "orbital_knob_socket", 0.027, 0.022, 0.033,
            mats["metal"], 20,
        )
        socket.parent = root
        knob_parts = [knob, crown]
        tick_count = 11
        scale_surface = 0.023
        pointer_surface = 0.072
    elif theme == "ForgeBrass":
        forge_plate(root, "Rotary", "control.rotary", mats, 0.142, 0.142)
        pivot_point = (0.0, -0.066, 0.0)
        knob = v4.cylinder_y(
            "forge_handwheel_hub", 0.033, 0.026, 0.063,
            mats["metal"], 18,
        )
        knob_parts = [knob]
        for index in range(6):
            angle = math.radians(index * 60)
            lobe = base.sphere(
                f"forge_knob_lobe_{index}",
                0.011,
                (
                    math.sin(angle) * 0.034,
                    -0.084,
                    math.cos(angle) * 0.034,
                ),
                mats["body"],
                12,
                6,
            )
            knob_parts.append(lobe)
        tick_count = 9
        scale_surface = 0.049
        pointer_surface = 0.076
    else:
        kinetic_plate(root, "Rotary", "control.rotary", mats, 0.152, 0.152)
        pivot_point = (0.0, -0.067, 0.0)
        knob = v4.cylinder_y(
            "kinetic_armored_knob", 0.040, 0.032, 0.067,
            mats["body"], 10,
        )
        crown = v4.cylinder_y(
            "kinetic_knob_inset", 0.027, 0.010, 0.098,
            mats["metal"], 10,
        )
        socket = v4.cylinder_y(
            "kinetic_knob_socket", 0.034, 0.020, 0.050,
            mats["metal"], 10,
        )
        socket.parent = root
        knob_parts = [knob, crown]
        tick_count = 7
        scale_surface = 0.045
        pointer_surface = 0.102
    for index in range(tick_count):
        angle = math.radians(-120 + 240 * index / (tick_count - 1))
        tick = v4.accent_bar(
            f"rotary_tick_{index}", 0.0025, 0.009,
            math.sin(angle) * 0.055,
            math.cos(angle) * 0.055,
            scale_surface,
            mats["readout"],
        )
        tick.rotation_euler.y = angle
        tick.parent = root
    pointer = v4.accent_bar(
        "knob_pointer", 0.0035, 0.024, 0.0, 0.018,
        pointer_surface, mats["readout"],
    )
    knob_parts.append(pointer)
    pivot, movable = v4.parent_movable(
        knob_parts, "knob", pivot_point, root,
    )
    pivot.name = "knob_pivot"
    movable.name = "knob"
    return root, pivot_point, (0.0, 1.0, 0.0)


def build_button(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "Button", "control.button")
    if theme == "OrbitalAnalog":
        orbital_plate(root, "Button", "control.button", mats, 0.112, 0.112)
        travel_position = (0.0, -0.043, 0.0)
        guide = v4.prism(
            "orbital_button_guide", 0.078, 0.056, 0.009,
            -0.022, -0.050, mats["metal"],
        )
        guide.parent = root
        cap = v4.prism(
            "button", 0.068, 0.046, 0.010,
            -0.043, -0.059, mats["body"],
        )
        glyph_surface = 0.058
    elif theme == "ForgeBrass":
        forge_plate(root, "Button", "control.button", mats, 0.130, 0.130)
        travel_position = (0.0, -0.063, 0.0)
        guide = v4.cylinder_y(
            "forge_button_guide", 0.044, 0.024, 0.048,
            mats["metal"], 20,
        )
        guide.parent = root
        cap = v4.cylinder_y(
            "button", 0.038, 0.025, 0.063,
            mats["body"], 20,
        )
        dome = base.sphere(
            "forge_mushroom_cap", 0.032,
            (0.0, -0.091, 0.0), mats["body"], 20, 10,
        )
        glyph_surface = 0.112
    else:
        kinetic_plate(root, "Button", "control.button", mats, 0.136, 0.136)
        travel_position = (0.0, -0.067, 0.0)
        guide = v4.cylinder_y(
            "kinetic_button_guide", 0.049, 0.022, 0.052,
            mats["metal"], 8,
        )
        guide.parent = root
        cap = v4.cylinder_y(
            "button", 0.042, 0.028, 0.067,
            mats["body"], 8,
        )
        dome = None
        glyph_surface = 0.080
    travel = bpy.data.objects.new("button_travel", None)
    travel.location = travel_position
    travel.parent = root
    bpy.context.collection.objects.link(travel)
    parent_keep_world(cap, travel)
    if theme == "ForgeBrass":
        parent_keep_world(dome, travel)
    glyph = v4.accent_bar(
        "button_glyph", 0.030, 0.006, 0.0, 0.0,
        glyph_surface, mats["readout"],
    )
    parent_keep_world(glyph, travel)
    return root, travel_position, (0.0, 1.0, 0.0)


def build_lamp(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "Lamp", "indicator.lamp")
    indicator = bpy.data.objects.new("indicator", None)
    indicator.parent = root
    bpy.context.collection.objects.link(indicator)
    if theme == "OrbitalAnalog":
        orbital_plate(root, "Lamp", "indicator.lamp", mats, 0.132, 0.092)
        lens = v4.prism(
            "indicator_lens", 0.078, 0.028, 0.010,
            -0.042, -0.058, mats["readout"],
        )
        for x in (-0.050, 0.050):
            retainer = v4.prism(
                "orbital_lens_clip", 0.010, 0.052, 0.003,
                -0.022, -0.061, mats["metal"],
            )
            retainer.location.x = x
            retainer.parent = root
    elif theme == "ForgeBrass":
        forge_plate(root, "Lamp", "indicator.lamp", mats, 0.132, 0.118)
        lens = base.sphere(
            "indicator_lens", 0.034,
            (0.0, -0.080, 0.0), mats["readout"], 20, 10,
        )
        cage = v4.cylinder_y(
            "forge_lens_retainer", 0.043, 0.020, 0.055,
            mats["metal"], 20,
        )
        cage.parent = root
    else:
        kinetic_plate(root, "Lamp", "indicator.lamp", mats, 0.142, 0.116)
        lens = v4.prism(
            "indicator_lens", 0.072, 0.034, 0.010,
            -0.063, -0.078, mats["readout"],
        )
        lens.rotation_euler.y = math.radians(-16)
        for x in (-0.050, 0.050):
            guard = v4.prism(
                "kinetic_lamp_guard", 0.012, 0.080, 0.004,
                -0.044, -0.081, mats["metal"],
            )
            guard.location.x = x
            guard.parent = root
    lens.parent = indicator
    return root, (0.0, lens.location.y, 0.0), (0.0, 0.0, 0.0)


def build_status(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "StatusIndicator", "indicator.status")
    indicator = bpy.data.objects.new("indicator", None)
    indicator.parent = root
    bpy.context.collection.objects.link(indicator)
    if theme == "OrbitalAnalog":
        orbital_plate(
            root, "StatusIndicator", "indicator.status",
            mats, 0.180, 0.112,
        )
        carrier = v4.prism(
            "orbital_status_carrier", 0.154, 0.092, 0.009,
            -0.022, -0.047, mats["metal"],
        )
        carrier.parent = root
        for index, name in enumerate(
            ("status_safe", "status_warn", "status_danger")
        ):
            bar = v4.prism(
                name, 0.132, 0.020, 0.006,
                -0.043, -0.055, mats["readout"],
                0.034 - index * 0.034,
            )
            bar.parent = indicator
    elif theme == "ForgeBrass":
        forge_plate(
            root, "StatusIndicator", "indicator.status",
            mats, 0.180, 0.120,
        )
        for index, name in enumerate(
            ("status_safe", "status_warn", "status_danger")
        ):
            jewel = base.sphere(
                name, 0.022,
                (-0.055 + index * 0.055, -0.078, 0.0),
                mats["readout"], 18, 9,
            )
            jewel.parent = indicator
            socket = v4.cylinder_y(
                f"{name}_socket", 0.027, 0.025, 0.052,
                mats["metal"], 18,
            )
            socket.location.x = -0.055 + index * 0.055
            socket.parent = root
    else:
        kinetic_plate(
            root, "StatusIndicator", "indicator.status",
            mats, 0.184, 0.124,
        )
        carrier = v4.prism(
            "kinetic_status_carrier", 0.166, 0.098, 0.011,
            -0.044, -0.070, mats["metal"],
        )
        carrier.parent = root
        for index, name in enumerate(
            ("status_safe", "status_warn", "status_danger")
        ):
            bar = v4.prism(
                name, 0.040, 0.078, 0.009,
                -0.065, -0.080, mats["readout"],
            )
            bar.location.x = -0.056 + index * 0.056
            bar.rotation_euler.y = math.radians(-14)
            bar.parent = indicator
    return root, (0.0, -0.065, 0.0), (0.0, 0.0, 0.0)


def build_throttle(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "Throttle", "control.throttle")
    if theme == "OrbitalAnalog":
        orbital_plate(root, "Throttle", "control.throttle", mats, 0.190, 0.320)
        for x in (-0.054, 0.054):
            rail = v4.prism(
                "orbital_quadrant_rail", 0.010, 0.240, 0.003,
                -0.022, -0.048, mats["metal"],
            )
            rail.location.x = x
            rail.parent = root
        pivot_point = (0.0, -0.048, -0.112)
        arm_width, grip_width = 0.010, 0.086
        grip_height = 0.036
    elif theme == "ForgeBrass":
        body = v4.cylinder_y(
            "forge_engine_quadrant", 0.118, 0.050, 0.026,
            mats["body"], 24,
        )
        body.scale.z = 1.32
        bpy.context.view_layer.objects.active = body
        body.select_set(True)
        bpy.ops.object.transform_apply(
            location=False, rotation=False, scale=True,
        )
        body.parent = root
        pivot_point = (0.0, -0.051, -0.105)
        arm_width, grip_width = 0.014, 0.120
        grip_height = 0.046
    else:
        kinetic_plate(
            root, "Throttle", "control.throttle",
            mats, 0.240, 0.340,
        )
        for x in (-0.086, 0.086):
            guard = v4.prism(
                "kinetic_throttle_guard", 0.026, 0.280, 0.007,
                -0.044, -0.080, mats["metal"],
            )
            guard.location.x = x
            guard.parent = root
        pivot_point = (0.0, -0.080, -0.112)
        arm_width, grip_width = 0.016, 0.126
        grip_height = 0.058
    axle = v4.cylinder_x(
        "throttle_axle", 0.016, 0.105,
        pivot_point, mats["metal"], 18,
    )
    for x in (-0.044, 0.044):
        bearing = v4.cylinder_x(
            f"{theme}_throttle_bearing",
            0.024,
            0.020,
            (x, pivot_point[1], pivot_point[2]),
            mats["body"],
            18 if theme != "KineticSafety" else 10,
        )
        bearing.parent = root
    arms = [axle]
    for x in (-0.034, 0.034):
        arm = v4.prism(
            "throttle_arm", arm_width, 0.205, 0.004,
            pivot_point[1], pivot_point[1] - 0.016,
            mats["metal"], -0.008,
        )
        arm.location.x = x
        arms.append(arm)
    if theme == "ForgeBrass":
        grip = v4.cylinder_x(
            "throttle_handle", grip_height * 0.48, grip_width,
            (0.0, pivot_point[1], 0.112), mats["body"], 18,
        )
    else:
        grip = v4.prism(
            "throttle_handle", grip_width, grip_height,
            grip_height * 0.20,
            pivot_point[1] - 0.005,
            pivot_point[1] - 0.040,
            mats["body"], 0.112,
        )
    arms.append(grip)
    pivot, movable = v4.parent_movable(
        arms, "throttle_handle", pivot_point, root,
    )
    pivot.name = "throttle_pivot"
    movable.name = "throttle_handle"
    return root, pivot_point, (1.0, 0.0, 0.0)


def build_slider(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "PowerSlider", "control.power_slider")
    if theme == "OrbitalAnalog":
        orbital_plate(
            root, "PowerSlider", "control.power_slider",
            mats, 0.132, 0.330,
        )
        slot = v4.prism(
            "orbital_fader_slot", 0.030, 0.250, 0.008,
            -0.026, -0.044, mats["metal"],
        )
        slot.parent = root
        carriage = v4.prism(
            "orbital_slider_carriage", 0.052, 0.052, 0.007,
            -0.040, -0.054, mats["metal"],
        )
        travel_position = (0.0, -0.050, 0.0)
        handle = v4.prism(
            "slider_handle", 0.080, 0.032, 0.008,
            -0.050, -0.068, mats["body"],
        )
    elif theme == "ForgeBrass":
        forge_plate(
            root, "PowerSlider", "control.power_slider",
            mats, 0.168, 0.340,
        )
        for x in (-0.038, 0.038):
            rod = v4.cylinder_z(
                "forge_slider_rod", 0.008, 0.250,
                (x, -0.070, 0.0), mats["metal"], 14,
            )
            rod.parent = root
        for z in (-0.135, 0.135):
            end_stop = v4.prism(
                "forge_slider_end_stop", 0.120, 0.038, 0.010,
                -0.038, -0.084, mats["body"], z,
            )
            end_stop.parent = root
        travel_position = (0.0, -0.080, 0.0)
        handle = v4.cylinder_x(
            "slider_handle", 0.018, 0.110,
            (0.0, -0.080, 0.0), mats["body"], 16,
        )
    else:
        kinetic_plate(
            root, "PowerSlider", "control.power_slider",
            mats, 0.168, 0.340,
        )
        for x in (-0.042, 0.042):
            rail = v4.prism(
                "kinetic_slider_rail", 0.015, 0.270, 0.004,
                -0.044, -0.076, mats["metal"],
            )
            rail.location.x = x
            rail.parent = root
        travel_position = (0.0, -0.082, 0.0)
        carriage = v4.prism(
            "kinetic_slider_carriage", 0.088, 0.042, 0.009,
            -0.070, -0.092, mats["metal"],
        )
        handle = v4.prism(
            "slider_handle", 0.118, 0.052, 0.012,
            -0.082, -0.112, mats["body"],
        )
    travel = bpy.data.objects.new("slider_travel", None)
    travel.location = travel_position
    travel.parent = root
    bpy.context.collection.objects.link(travel)
    if theme in ("OrbitalAnalog", "KineticSafety"):
        parent_keep_world(carriage, travel)
    parent_keep_world(handle, travel)
    return root, travel_position, (0.0, 0.0, 1.0)


def window_needle(root, mats, pivot_point, length, width):
    needle = v4.prism(
        "needle", width, length, min(width * 0.25, 0.006),
        pivot_point[1], pivot_point[1] - 0.016,
        mats["readout"], pivot_point[2] + length * 0.45,
    )
    hub = v4.cylinder_y(
        "window_needle_hub", width * 2.4, 0.022,
        abs(pivot_point[1]), mats["metal"], 20,
    )
    hub.location.z = pivot_point[2]
    pivot, movable = v4.parent_movable(
        [needle, hub], "needle", pivot_point, root,
    )
    pivot.name = "needle_pivot"
    movable.name = "needle"


def build_window_meter(theme):
    mats = base.materials(theme)
    root = base.root_for(theme, "WindowMeter", "meter.window")
    if theme == "OrbitalAnalog":
        housing = v4.shell(
            "orbital_window_console", 1.20, 0.70, 0.035,
            1.08, 0.58, 0.026, 0.085, 0.072, mats["body"],
        )
        housing.parent = root
        for x in (-0.515, 0.515):
            wing = v4.prism(
                "orbital_window_wing", 0.050, 0.530, 0.014,
                -0.070, -0.112, mats["metal"],
            )
            wing.location.x = x
            wing.parent = root
        radius, sides, outward = 0.260, 40, 0.118
        pivot_point = (0.0, -0.133, -0.065)
    elif theme == "ForgeBrass":
        housing = v4.cylinder_y(
            "forge_window_cast_body", 0.355, 0.125, 0.064,
            mats["body"], 32,
        )
        housing.scale.x = 1.45
        bpy.context.view_layer.objects.active = housing
        housing.select_set(True)
        bpy.ops.object.transform_apply(
            location=False, rotation=False, scale=True,
        )
        housing.parent = root
        for x in (-0.470, 0.470):
            foot = v4.prism(
                "forge_window_mount", 0.120, 0.180, 0.035,
                0.0, -0.110, mats["body"], -0.285,
            )
            foot.location.x = x
            foot.parent = root
        radius, sides, outward = 0.285, 40, 0.142
        pivot_point = (0.0, -0.157, -0.070)
    else:
        housing = v4.shell(
            "kinetic_window_armor", 1.20, 0.75, 0.050,
            1.00, 0.55, 0.035, 0.120, 0.102, mats["body"],
        )
        housing.parent = root
        for x in (-0.525, 0.525):
            guard = v4.prism(
                "kinetic_window_guard", 0.090, 0.600, 0.022,
                -0.102, -0.165, mats["metal"],
            )
            guard.location.x = x
            guard.parent = root
        radius, sides, outward = 0.270, 12, 0.170
        pivot_point = (0.0, -0.185, -0.075)
    dial = v4.cylinder_y(
        "dial", radius, 0.030, outward, mats["body"], sides,
    )
    dial.parent = root
    count = 25 if theme != "KineticSafety" else 15
    for index in range(count):
        angle = math.radians(-130 + 260 * index / (count - 1))
        tick = v4.accent_bar(
            f"window_tick_{index}",
            0.010 if index % 5 else 0.018,
            0.038 if index % 5 else 0.060,
            math.sin(angle) * radius * 0.82,
            math.cos(angle) * radius * 0.82,
            outward + 0.014,
            mats["readout"],
        )
        tick.rotation_euler.y = angle
        tick.parent = root
    window_needle(root, mats, pivot_point, radius * 1.45, 0.020)
    return root, pivot_point, (0.0, 1.0, 0.0)


BUILDERS = {
    "Toggle": build_toggle,
    "Rotary": build_rotary,
    "Button": build_button,
    "Lamp": build_lamp,
    "StatusIndicator": build_status,
    "Throttle": build_throttle,
    "PowerSlider": build_slider,
    "WindowMeter": build_window_meter,
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
    root, pivot_position, local_axis = BUILDERS[key](theme)
    meshes = meshes_under(root)
    common.apply_transforms(meshes)
    source_stats = retopo.topology_stats(meshes)
    if source_stats["non_manifold_edges"]:
        raise RuntimeError(f"{theme}/{key}: non-manifold source")
    if source_stats["zero_area_faces"]:
        raise RuntimeError(f"{theme}/{key}: degenerate source")
    source_dir = (
        project_root / "ArtSource/Blender/ThemeSilhouetteV5" / theme
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates"
        / theme
        / "ThemeSilhouetteV5"
    )
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
        raise RuntimeError(f"{theme}/{key}: over budget")
    save_blend(source_dir / f"BL_{key}_{theme}_V5_Triangulated.blend")
    fbx_path = model_dir / f"SM_{key}_{theme}_V5_Grayscale.fbx"
    fbx_path.parent.mkdir(parents=True, exist_ok=True)
    if fbx_path.with_suffix(".fbm").exists():
        shutil.rmtree(fbx_path.with_suffix(".fbm"))
    common.export_fbx(root, fbx_path)
    report = {
        "asset": f"{key}_{theme}_V5_Grayscale",
        "type_id": type_id,
        "theme_id": base.THEMES[theme],
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
    only = set(args.only or ())
    for theme in base.THEMES:
        for key in ASSETS:
            if only and key not in only:
                continue
            generate_one(
                project_root, theme, key, args.skip_topology,
            )


if __name__ == "__main__":
    main()
