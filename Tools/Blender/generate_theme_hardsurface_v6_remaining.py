"""Generate the remaining eight V6 hard-surface model families."""

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
import generate_theme_hardsurface_v6 as v6
import generate_theme_silhouette_v5 as v5
import generate_theme_silhouette_v5_remaining as v5r


ASSETS = v5r.ASSETS
THEMES = v5.THEMES


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-topology", action="store_true")
    parser.add_argument("--only", nargs="+", choices=tuple(ASSETS))
    return parser.parse_args(args)


SMALL_ENVELOPES = {
    "Toggle": (0.096, 0.132, 0.112, 0.132, 0.124, 0.146),
    "Rotary": (0.132, 0.132, 0.142, 0.142, 0.152, 0.152),
    "Button": (0.112, 0.112, 0.130, 0.130, 0.136, 0.136),
    "Lamp": (0.132, 0.092, 0.132, 0.118, 0.142, 0.116),
    "StatusIndicator": (0.180, 0.112, 0.180, 0.120, 0.184, 0.124),
}


def add_small_mounts(root, theme, key, mats):
    values = SMALL_ENVELOPES[key]
    if theme == "OrbitalAnalog":
        width, height = values[0], values[1]
        x_pos, z_pos = width * 0.41, height * 0.38
        outward, vertices = 0.024, 10
        radius = min(width, height) * 0.025
    elif theme == "ForgeBrass":
        width, height = values[2], values[3]
        x_pos, z_pos = width * 0.39, height * 0.39
        outward, vertices = 0.045, 6
        radius = min(width, height) * 0.032
    else:
        width, height = values[4], values[5]
        x_pos, z_pos = width * 0.40, height * 0.25
        outward, vertices = 0.065, 8
        radius = min(width, height) * 0.030
    for index, (x, z) in enumerate(
        ((-x_pos, -z_pos), (x_pos, -z_pos),
         (-x_pos, z_pos), (x_pos, z_pos))
    ):
        v6.add_fastener(
            root,
            f"{theme}_{key}_v6_mount_{index}",
            x,
            z,
            outward,
            mats["metal"],
            radius,
            vertices,
        )


def descendant_named(root, name):
    return next(
        (obj for obj in root.children_recursive if obj.name == name),
        None,
    )


def remove_mesh_descendants(parent):
    if parent is None:
        return
    for obj in list(parent.children_recursive):
        if obj.type == "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)


def remove_named_meshes(root, prefixes):
    for obj in list(root.children_recursive):
        if obj.type == "MESH" and obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def add_toggle_detail(root, theme, mats, pivot):
    add_small_mounts(root, theme, "Toggle", mats)
    remove_named_meshes(
        root,
        (
            "orbital_low_collar",
            "forge_hex_nut",
            "kinetic_armored_collar",
            "switch_axle",
        ),
    )
    movable = descendant_named(root, "switch")
    if theme == "OrbitalAnalog":
        joint_radius, ring_radius, ring_tube = 0.018, 0.018, 0.0032
        support_surface = 0.024
        mark_width = 0.028
    elif theme == "ForgeBrass":
        joint_radius, ring_radius, ring_tube = 0.023, 0.023, 0.0045
        support_surface = 0.050
        mark_width = 0.036
    else:
        joint_radius, ring_radius, ring_tube = 0.024, 0.024, 0.0050
        support_surface = 0.039
        mark_width = 0.040
    joint = v5.sphere(
        f"{theme}_toggle_v6_hemisphere_joint",
        joint_radius,
        pivot,
        mats["body"],
        16 if theme != "KineticSafety" else 10,
        8 if theme != "KineticSafety" else 5,
    )
    v5r.parent_keep_world(joint, movable)
    ring = v6.torus_y(
        f"{theme}_toggle_v6_fixed_retaining_ring",
        ring_radius,
        ring_tube,
        -pivot[1],
        mats["metal"],
        18 if theme != "KineticSafety" else 10,
        4,
    )
    ring.parent = root
    cup = v4.cylinder_y(
        f"{theme}_toggle_v6_joint_socket",
        joint_radius * 0.78,
        joint_radius * 0.70,
        -pivot[1] + joint_radius * 0.18,
        mats["metal"],
        16 if theme != "KineticSafety" else 10,
    )
    cup.parent = root
    for index, z in enumerate((-joint_radius * 1.55, joint_radius * 1.55)):
        stop = v4.prism(
            f"{theme}_toggle_v6_limit_stop_{index}",
            joint_radius * 1.10,
            joint_radius * 0.42,
            joint_radius * 0.12,
            -support_surface + 0.001,
            -support_surface - 0.008,
            mats["metal"],
            z,
        )
        stop.parent = root
    for index, z in enumerate((-0.050, 0.050)):
        mark = v4.prism(
            f"{theme}_toggle_v6_detent_{index}",
            mark_width,
            0.006,
            0.0014,
            -support_surface + 0.002,
            -support_surface - 0.002,
            mats["readout"],
            z,
        )
        mark.parent = root


def add_rotary_detail(root, theme, mats, pivot):
    add_small_mounts(root, theme, "Rotary", mats)
    movable = descendant_named(root, "knob")
    remove_mesh_descendants(movable)
    if theme == "OrbitalAnalog":
        body = v4.cylinder_y(
            "orbital_rotary_v6_ribbed_dial",
            0.036,
            0.026,
            0.054,
            mats["body"],
            14,
        )
        crown = v4.prism(
            "orbital_rotary_v6_index_bridge",
            0.046,
            0.014,
            0.003,
            -0.067,
            -0.073,
            mats["metal"],
            0.010,
        )
        ring = v6.torus_y(
            "orbital_rotary_v6_scale_ring",
            0.052,
            0.0020,
            0.024,
            mats["metal"],
            20,
            3,
        )
        moving_parts = (body, crown)
        pointer_surface = 0.076
        stop_surface = 0.026
    elif theme == "ForgeBrass":
        body = v4.cylinder_y(
            "forge_rotary_v6_fluted_drum",
            0.039,
            0.030,
            0.071,
            mats["body"],
            12,
        )
        crown = v4.cylinder_y(
            "forge_rotary_v6_hub_cap",
            0.021,
            0.010,
            0.091,
            mats["metal"],
            8,
        )
        ring = v6.torus_y(
            "forge_rotary_v6_cast_ring",
            0.052,
            0.0035,
            0.050,
            mats["metal"],
            16,
            4,
        )
        moving_parts = (body, crown)
        pointer_surface = 0.098
        stop_surface = 0.052
    else:
        hub = v4.cylinder_y(
            "kinetic_rotary_v6_selector_hub",
            0.031,
            0.030,
            0.070,
            mats["body"],
            10,
        )
        wing = v4.prism(
            "kinetic_rotary_v6_selector_wing",
            0.072,
            0.020,
            0.005,
            -0.092,
            -0.105,
            mats["metal"],
        )
        ring = v6.torus_y(
            "kinetic_rotary_v6_armor_ring",
            0.054,
            0.0040,
            0.047,
            mats["metal"],
            10,
            4,
        )
        moving_parts = (hub, wing)
        pointer_surface = 0.108
        stop_surface = 0.051
    ring.parent = root
    for index, angle in enumerate((math.radians(-125), math.radians(125))):
        v6.add_fastener(
            root,
            f"{theme}_rotary_v6_limit_pin_{index}",
            math.sin(angle) * 0.052,
            math.cos(angle) * 0.052,
            stop_surface,
            mats["metal"],
            0.0038 if theme != "KineticSafety" else 0.0045,
            8,
        )
    for part in moving_parts:
        v5r.parent_keep_world(part, movable)
    pointer = v4.accent_bar(
        f"{theme}_rotary_v6_pointer",
        0.0035,
        0.022,
        0.0,
        0.017,
        pointer_surface,
        mats["readout"],
    )
    v5r.parent_keep_world(pointer, movable)


def add_button_detail(root, theme, mats):
    add_small_mounts(root, theme, "Button", mats)
    travel = descendant_named(root, "button_travel")
    remove_mesh_descendants(travel)
    if theme == "OrbitalAnalog":
        gasket = v4.prism(
            "orbital_button_v6_gasket",
            0.082,
            0.062,
            0.011,
            -0.038,
            -0.045,
            mats["body"],
        )
        gasket.parent = root
        cap = v4.prism(
            "orbital_button_v6_integrated_cap",
            0.070,
            0.050,
            0.010,
            -0.043,
            -0.062,
            mats["body"],
        )
        face = v4.prism(
            "orbital_button_v6_face",
            0.052,
            0.032,
            0.007,
            -0.060,
            -0.066,
            mats["metal"],
        )
        for x in (-0.043, 0.043):
            guard = v4.prism(
                "orbital_button_v6_side_guard",
                0.012,
                0.070,
                0.003,
                -0.022,
                -0.051,
                mats["metal"],
            )
            guard.location.x = x
            guard.parent = root
        moving_parts = (cap, face)
    elif theme == "ForgeBrass":
        gasket = v6.torus_y(
            "forge_button_v6_plunger_gasket",
            0.038,
            0.0025,
            0.057,
            mats["body"],
            14,
            3,
        )
        gasket.parent = root
        cap = v4.cylinder_y(
            "forge_button_v6_octagonal_plunger",
            0.038,
            0.030,
            0.069,
            mats["body"],
            8,
        )
        face = v4.cylinder_y(
            "forge_button_v6_inset_face",
            0.026,
            0.009,
            0.088,
            mats["metal"],
            12,
        )
        ring = v6.torus_y(
            "forge_button_v6_retainer",
            0.043,
            0.0040,
            0.054,
            mats["metal"],
            16,
            4,
        )
        ring.parent = root
        moving_parts = (cap, face)
    else:
        gasket = v4.prism(
            "kinetic_button_v6_gasket",
            0.090,
            0.064,
            0.012,
            -0.060,
            -0.070,
            mats["body"],
        )
        gasket.parent = root
        cap = v4.prism(
            "kinetic_button_v6_wedge_plunger",
            0.078,
            0.052,
            0.011,
            -0.067,
            -0.089,
            mats["body"],
        )
        face = v4.prism(
            "kinetic_button_v6_armored_face",
            0.052,
            0.028,
            0.006,
            -0.087,
            -0.095,
            mats["metal"],
        )
        for x in (-0.052, 0.052):
            guard = v4.prism(
                "kinetic_button_v6_guard",
                0.018,
                0.090,
                0.005,
                -0.044,
                -0.079,
                mats["metal"],
            )
            guard.location.x = x
            guard.parent = root
        moving_parts = (cap, face)
    for part in moving_parts:
        v5r.parent_keep_world(part, travel)


def add_lamp_detail(root, theme, mats):
    add_small_mounts(root, theme, "Lamp", mats)
    if theme == "OrbitalAnalog":
        gasket = v4.prism(
            "orbital_lamp_v6_lens_gasket",
            0.084,
            0.034,
            0.008,
            -0.046,
            -0.053,
            mats["body"],
        )
        gasket.parent = root
        socket = v4.prism(
            "orbital_lamp_v6_integrated_socket",
            0.092,
            0.042,
            0.009,
            -0.025,
            -0.049,
            mats["metal"],
        )
        socket.parent = root
        for z in (-0.024, 0.024):
            louver = v4.prism(
                "orbital_lamp_v6_louver",
                0.090,
                0.007,
                0.0015,
                -0.055,
                -0.060,
                mats["metal"],
                z,
            )
            louver.parent = root
    elif theme == "ForgeBrass":
        gasket = v6.torus_y(
            "forge_lamp_v6_lens_gasket",
            0.034,
            0.0028,
            0.070,
            mats["body"],
            14,
            3,
        )
        gasket.parent = root
        socket = v4.cylinder_y(
            "forge_lamp_v6_socket_throat",
            0.035,
            0.030,
            0.058,
            mats["metal"],
            16,
        )
        socket.parent = root
        ring = v6.torus_y(
            "forge_lamp_v6_cage_ring",
            0.040,
            0.0040,
            0.061,
            mats["metal"],
            16,
            4,
        )
        ring.parent = root
    else:
        gasket = v4.prism(
            "kinetic_lamp_v6_lens_gasket",
            0.078,
            0.040,
            0.009,
            -0.062,
            -0.072,
            mats["body"],
        )
        gasket.parent = root
        socket = v4.prism(
            "kinetic_lamp_v6_integrated_socket",
            0.086,
            0.050,
            0.010,
            -0.046,
            -0.068,
            mats["metal"],
        )
        socket.parent = root
        cross = v4.prism(
            "kinetic_lamp_v6_cross_guard",
            0.105,
            0.014,
            0.003,
            -0.066,
            -0.083,
            mats["metal"],
        )
        cross.parent = root


def add_status_detail(root, theme, mats):
    add_small_mounts(root, theme, "StatusIndicator", mats)
    if theme == "OrbitalAnalog":
        for z in (-0.034, 0.0, 0.034):
            bridge = v4.prism(
                "orbital_status_v6_lens_bridge",
                0.142,
                0.005,
                0.0015,
                -0.045,
                -0.058,
                mats["metal"],
                z - 0.017,
            )
            bridge.parent = root
        for x in (-0.078, 0.078):
            rail = v4.prism(
                "orbital_status_v6_end_rail",
                0.010,
                0.092,
                0.0025,
                -0.022,
                -0.056,
                mats["metal"],
            )
            rail.location.x = x
            rail.parent = root
    elif theme == "ForgeBrass":
        manifold = v4.cylinder_x(
            "forge_status_v6_manifold",
            0.008,
            0.145,
            (0.0, -0.052, -0.042),
            mats["metal"],
            14,
        )
        manifold.parent = root
        for x in (-0.055, 0.0, 0.055):
            riser = v4.prism(
                "forge_status_v6_socket_riser",
                0.009,
                0.036,
                0.002,
                -0.050,
                -0.064,
                mats["metal"],
                -0.021,
            )
            riser.location.x = x
            riser.parent = root
            retaining_ring = v6.torus_y(
                "forge_status_v6_lens_retainer",
                0.022,
                0.0030,
                0.079,
                mats["metal"],
                14,
                4,
            )
            retaining_ring.location.x = x
            retaining_ring.parent = root
    else:
        for x in (-0.028, 0.028):
            divider = v4.prism(
                "kinetic_status_v6_lens_divider",
                0.008,
                0.082,
                0.002,
                -0.068,
                -0.083,
                mats["metal"],
            )
            divider.location.x = x
            divider.parent = root
        for z in (-0.050, 0.050):
            brace = v4.prism(
                "kinetic_status_v6_brace",
                0.168,
                0.012,
                0.003,
                -0.044,
                -0.081,
                mats["metal"],
                z,
            )
            brace.parent = root


def add_throttle_mounts(root, theme, mats):
    if theme == "OrbitalAnalog":
        positions = ((-0.075, -0.135), (0.075, -0.135),
                     (-0.075, 0.135), (0.075, 0.135))
        outward, radius, vertices = 0.024, 0.0040, 10
    elif theme == "ForgeBrass":
        positions = tuple(
            (math.sin(math.radians(i * 60)) * 0.096,
             math.cos(math.radians(i * 60)) * 0.096)
            for i in range(6)
        )
        outward, radius, vertices = 0.051, 0.0048, 8
    else:
        positions = ((-0.096, -0.135), (0.096, -0.135),
                     (-0.096, 0.135), (0.096, 0.135))
        outward, radius, vertices = 0.080, 0.0055, 8
    for index, (x, z) in enumerate(positions):
        v6.add_fastener(
            root, f"{theme}_throttle_v6_bolt_{index}",
            x, z, outward, mats["metal"], radius, vertices,
        )


def add_throttle_detail(root, theme, mats, pivot):
    add_throttle_mounts(root, theme, mats)
    if theme == "OrbitalAnalog":
        strip_x, y_back, y_front = 0.071, -0.022, -0.050
        mark_y_back, mark_y_front = -0.047, -0.052
        stop_y_back, stop_y_front = -0.024, -0.054
    elif theme == "ForgeBrass":
        strip_x, y_back, y_front = 0.078, -0.035, -0.052
        mark_y_back, mark_y_front = -0.049, -0.054
        stop_y_back, stop_y_front = -0.036, -0.057
    else:
        strip_x, y_back, y_front = 0.105, -0.044, -0.081
        mark_y_back, mark_y_front = -0.077, -0.083
        stop_y_back, stop_y_front = -0.046, -0.084
    strip = v4.prism(
        f"{theme}_throttle_v6_scale_strip",
        0.026,
        0.250,
        0.005,
        y_back,
        y_front,
        mats["metal"],
    )
    strip.location.x = strip_x
    strip.parent = root
    for index, z in enumerate(
        (-0.100, -0.066, -0.033, 0.0, 0.033, 0.066, 0.100)
    ):
        mark = v4.prism(
            f"{theme}_throttle_v6_mark_{index}",
            0.018 if index not in (0, 6) else 0.024,
            0.005,
            0.0012,
            mark_y_back,
            mark_y_front,
            mats["readout"],
            z,
        )
        mark.location.x = strip_x
        mark.parent = root
    for index, z in enumerate((-0.118, 0.118)):
        stop = v4.prism(
            f"{theme}_throttle_v6_limit_stop_{index}",
            0.048,
            0.022,
            0.005,
            stop_y_back,
            stop_y_front,
            mats["body"],
            z,
        )
        stop.location.x = -strip_x * 0.55
        stop.parent = root


def add_slider_detail(root, theme, mats):
    if theme == "OrbitalAnalog":
        width, bolt_x, surface = 0.132, 0.052, 0.024
        bolt_surface = 0.024
        strip_x, y_back, y_front = 0.052, -0.022, -0.046
        mark_back, mark_front = -0.043, -0.048
        bridge_width = 0.056
        bridge_height = 0.060
        bridge_back, bridge_front = -0.048, -0.066
        post_radius = 0.006
        post_x_positions = (-0.018, 0.018)
    elif theme == "ForgeBrass":
        width, bolt_x, surface = 0.168, 0.065, 0.045
        bolt_surface = 0.045
        strip_x, y_back, y_front = 0.060, -0.038, -0.074
        mark_back, mark_front = -0.071, -0.076
        bridge_width = 0.092
        bridge_height = 0.070
        bridge_back, bridge_front = -0.062, -0.092
        post_radius = 0.009
        post_x_positions = (-0.026, 0.026)
    else:
        width, bolt_x, surface = 0.168, 0.067, 0.065
        # Corner bolts sit on the outer shell, not the deeper side guards.
        bolt_surface = 0.046
        strip_x, y_back, y_front = 0.062, -0.044, -0.078
        mark_back, mark_front = -0.075, -0.080
        bridge_width = 0.082
        bridge_height = 0.086
        bridge_back, bridge_front = -0.076, -0.108
        post_radius = 0.008
        post_x_positions = (-0.025, 0.025)
    for index, (x, z) in enumerate(
        ((-bolt_x, -0.145), (bolt_x, -0.145),
         (-bolt_x, 0.145), (bolt_x, 0.145))
    ):
        radius = width * 0.027
        fastener_depth = max(radius * 0.65, 0.0024)
        washer = v6.torus_y(
            f"{theme}_slider_v6_bolt_washer_{index}",
            radius * 1.42,
            radius * 0.22,
            bolt_surface + radius * 0.22,
            mats["metal"],
            10,
            3,
        )
        washer.location.x = x
        washer.location.z = z
        washer.parent = root
        v6.add_fastener(
            root,
            f"{theme}_slider_v6_bolt_{index}",
            x,
            z,
            bolt_surface + fastener_depth * 0.5,
            mats["metal"],
            radius,
            8,
        )
    strip = v4.prism(
        f"{theme}_slider_v6_scale_strip",
        0.024,
        0.270,
        0.004,
        y_back,
        y_front,
        mats["metal"],
    )
    strip.location.x = strip_x
    strip.parent = root
    for index in range(11):
        mark = v4.prism(
            f"{theme}_slider_v6_mark_{index}",
            0.016 if index % 5 else 0.021,
            0.0038,
            0.0010,
            mark_back,
            mark_front,
            mats["readout"],
            -0.125 + index * 0.025,
        )
        mark.location.x = strip_x
        mark.parent = root
    travel = descendant_named(root, "slider_travel")
    bridge = v4.prism(
        f"{theme}_slider_v6_handle_bridge",
        bridge_width,
        bridge_height,
        min(bridge_width, bridge_height) * 0.14,
        bridge_back,
        bridge_front,
        mats["metal"],
    )
    v5r.parent_keep_world(bridge, travel)
    post_back_outward = surface - 0.003
    post_front_outward = abs(bridge_front) + 0.004
    post_depth = post_front_outward - post_back_outward
    post_outward = (
        post_front_outward + post_back_outward
    ) * 0.5
    for index, x in enumerate(post_x_positions):
        post = v4.cylinder_y(
            f"{theme}_slider_v6_grip_support_post_{index}",
            post_radius,
            post_depth,
            post_outward,
            mats["metal"],
            12,
        )
        post.location.x = x
        v5r.parent_keep_world(post, travel)
    coupler = v4.prism(
        f"{theme}_slider_v6_carriage_coupler",
        bridge_width * 0.42,
        bridge_height * 0.72,
        min(bridge_width, bridge_height) * 0.10,
        -surface + 0.003,
        bridge_front + 0.004,
        mats["metal"],
    )
    v5r.parent_keep_world(coupler, travel)
    shoe_y_back = -surface + 0.004
    shoe_y_front = -surface - 0.020
    for x in (-0.033, 0.033):
        shoe = v4.prism(
            f"{theme}_slider_v6_carriage_shoe",
            0.018,
            0.038,
            0.004,
            shoe_y_back,
            shoe_y_front,
            mats["metal"],
        )
        shoe.location.x = x
        v5r.parent_keep_world(shoe, travel)


def add_window_meter_detail(root, theme, mats):
    if theme == "OrbitalAnalog":
        gasket_radius, gasket_surface, gasket_segments = 0.267, 0.128, 28
        ring = v6.torus_y(
            "orbital_window_meter_v6_retainer",
            0.278, 0.008, 0.132, mats["metal"], 32, 4,
        )
        bolt_x, bolt_z, surface = 0.515, 0.225, 0.112
        vertices = 10
    elif theme == "ForgeBrass":
        gasket_radius, gasket_surface, gasket_segments = 0.298, 0.152, 24
        ring = v6.torus_y(
            "forge_window_meter_v6_flange",
            0.310, 0.010, 0.156, mats["metal"], 28, 4,
        )
        bolt_x, bolt_z, surface = 0.385, 0.205, 0.126
        vertices = 8
    else:
        gasket_radius, gasket_surface, gasket_segments = 0.282, 0.180, 12
        ring = v6.torus_y(
            "kinetic_window_meter_v6_armor_ring",
            0.294, 0.011, 0.184, mats["metal"], 12, 4,
        )
        bolt_x, bolt_z, surface = 0.525, 0.225, 0.165
        vertices = 8
    gasket = v6.torus_y(
        f"{theme}_window_meter_v6_glass_gasket",
        gasket_radius,
        0.005,
        gasket_surface,
        mats["body"],
        gasket_segments,
        3,
    )
    gasket.parent = root
    ring.parent = root
    for index, (x, z) in enumerate(
        ((-bolt_x, -bolt_z), (bolt_x, -bolt_z),
         (-bolt_x, bolt_z), (bolt_x, bolt_z))
    ):
        v6.add_fastener(
            root,
            f"{theme}_window_meter_v6_bolt_{index}",
            x,
            z,
            surface,
            mats["metal"],
            0.012,
            vertices,
        )
    if theme == "KineticSafety":
        for z in (-0.310, 0.310):
            brace = v4.prism(
                "kinetic_window_meter_v6_cross_brace",
                0.90,
                0.050,
                0.012,
                -0.102,
                -0.166,
                mats["metal"],
                z,
            )
            brace.parent = root


def add_detail(root, theme, key, mats, pivot):
    if key == "Toggle":
        add_toggle_detail(root, theme, mats, pivot)
    elif key == "Rotary":
        add_rotary_detail(root, theme, mats, pivot)
    elif key == "Button":
        add_button_detail(root, theme, mats)
    elif key == "Lamp":
        add_lamp_detail(root, theme, mats)
    elif key == "StatusIndicator":
        add_status_detail(root, theme, mats)
    elif key == "Throttle":
        add_throttle_detail(root, theme, mats, pivot)
    elif key == "PowerSlider":
        add_slider_detail(root, theme, mats)
    elif key == "WindowMeter":
        add_window_meter_detail(root, theme, mats)


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
    root, pivot_position, local_axis = v5r.BUILDERS[key](theme)
    root.name = f"PF_Visual_{key}_{theme}_V6"
    root["art_pass"] = "V6 hybrid hard-surface prototype"
    root["quality_floor"] = "V4 hard-surface retopo"
    root["mechanical_rules"] = (
        "flush fasteners, supported marks, visible pivots and fitted joints"
    )
    root["assembly_policy"] = (
        "gaskets, seams, bushings, stops and supports explain construction"
    )
    mats = v5.materials(theme)
    add_detail(root, theme, key, mats, pivot_position)
    meshes = meshes_under(root)
    common.apply_transforms(meshes)
    source_stats = retopo.topology_stats(meshes)
    if source_stats["non_manifold_edges"]:
        raise RuntimeError(f"{theme}/{key}: non-manifold source")
    if source_stats["zero_area_faces"]:
        raise RuntimeError(f"{theme}/{key}: degenerate source")

    source_dir = (
        project_root / "ArtSource/Blender/ThemeHardSurfaceV6" / theme
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates"
        / theme
        / "ThemeHardSurfaceV6"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    controls.create_preview(
        meshes,
        0.0,
        source_dir / f"Preview_{key}_{theme}_V6_Grayscale.png",
    )
    if not skip_topology:
        retopo.render_topology_preview(
            meshes,
            source_dir / f"Preview_{key}_{theme}_V6_Topology.png",
        )
    save_blend(source_dir / f"BL_{key}_{theme}_V6_Retopo.blend")
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
        source_dir / f"BL_{key}_{theme}_V6_Triangulated.blend"
    )
    fbx_path = model_dir / f"SM_{key}_{theme}_V6_Grayscale.fbx"
    if fbx_path.with_suffix(".fbm").exists():
        shutil.rmtree(fbx_path.with_suffix(".fbm"))
    common.export_fbx(root, fbx_path)
    report = {
        "asset": f"{key}_{theme}_V6_Grayscale",
        "type_id": type_id,
        "theme_id": THEMES[theme],
        "art_pass": "V6 hybrid hard-surface prototype",
        "quality_floor": "V4 hard-surface retopo",
        "mechanical_rules": (
            "flush fasteners, supported marks, visible pivots and fitted joints"
        ),
        "assembly_policy": (
            "gaskets, seams, bushings, stops and supports"
        ),
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
        source_dir / f"{key}_{theme}_V6.report.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report))


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    only = set(args.only or ())
    for theme in THEMES:
        for key in ASSETS:
            if only and key not in only:
                continue
            generate_one(
                project_root,
                theme,
                key,
                args.skip_topology,
            )


if __name__ == "__main__":
    main()
