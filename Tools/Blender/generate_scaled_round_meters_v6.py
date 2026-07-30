"""Generate medium and large V6 round meters without uniform scale-up.

The existing theme-specific round meter is used as the visual family seed.
Front dimensions are expanded by 2x/3x, while depth grows more slowly. Each
size receives additional structural layers and theme-specific service detail.
"""

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_hardsurface_kinetic_set_v4 as v4
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common
import generate_theme_hardsurface_v6 as v6
import generate_theme_silhouette_v5 as v5
import v6_theme_materials


THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
SIZES = {
    "MeterMedium": {
        "type_id": "meter.round.medium",
        "front_scale": 2.0,
        "depth_scale": 1.55,
        "scale_class": "Medium",
        "outer_radius": 0.135,
        "outward": 0.105,
    },
    "MeterLarge": {
        "type_id": "meter.round.large",
        "front_scale": 3.0,
        "depth_scale": 2.05,
        "scale_class": "Large",
        "outer_radius": 0.205,
        "outward": 0.145,
    },
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", choices=THEMES)
    parser.add_argument("--size", choices=tuple(SIZES))
    return parser.parse_args(args)


def scale_seed(root, front_scale, depth_scale):
    """Scale each root branch so pivots and moving children remain coherent."""
    world_scale = Matrix.Diagonal(
        (front_scale, depth_scale, front_scale, 1.0)
    )
    for child in list(root.children):
        child.matrix_world = world_scale @ child.matrix_world


def add_fasteners(root, mats, radius, outward, count, fastener_radius):
    for index in range(count):
        angle = math.tau * index / count + math.radians(22.5)
        fastener = v6.add_fastener(
            root,
            f"scale_fastener_{index:02d}",
            math.sin(angle) * radius,
            math.cos(angle) * radius,
            outward,
            mats["metal"],
            fastener_radius,
            10,
        )
        fastener["assembly_role"] = "perimeter fastener"


def add_secondary_scale(root, mats, radius, outward, count, major_every):
    for index in range(count):
        angle = math.radians(-132 + index * (264 / (count - 1)))
        major = index % major_every == 0
        mark = v4.accent_bar(
            f"secondary_scale_{index:02d}",
            0.0028 if major else 0.0015,
            0.012 if major else 0.0065,
            math.sin(angle) * radius,
            math.cos(angle) * radius,
            outward,
            mats["readout"],
        )
        mark.rotation_euler.y = angle
        mark.parent = root


def add_orbital_structure(root, mats, size_key, config):
    large = size_key == "MeterLarge"
    width = 0.510 if large else 0.340
    height = 0.420 if large else 0.280
    depth = 0.115 if large else 0.078
    recess_width = width - (0.085 if large else 0.060)
    recess_height = height - (0.082 if large else 0.058)
    frame = v4.shell(
        f"orbital_{size_key}_load_frame",
        width,
        height,
        0.036 if large else 0.024,
        recess_width,
        recess_height,
        0.022 if large else 0.016,
        depth,
        depth - 0.014,
        mats["body"],
    )
    frame.parent = root
    for side in (-1, 1):
        rail = v4.prism(
            f"orbital_{size_key}_service_rail_{side}",
            0.026 if large else 0.018,
            height * 0.62,
            0.005,
            -depth + 0.006,
            -depth - 0.014,
            mats["metal"],
        )
        rail.location.x = side * (width * 0.455)
        rail.parent = root
    segment_count = 5 if large else 3
    for index in range(segment_count):
        plate = v4.prism(
            f"orbital_{size_key}_data_segment_{index}",
            0.052 if large else 0.044,
            0.016 if large else 0.013,
            0.003,
            -depth - 0.010,
            -depth - 0.014,
            mats["readout"],
            -height * 0.405,
        )
        plate.location.x = (
            index - (segment_count - 1) * 0.5
        ) * (0.064 if large else 0.055)
        plate.parent = root


def add_forge_structure(root, mats, size_key, config):
    large = size_key == "MeterLarge"
    radius = config["outer_radius"]
    outward = config["outward"]
    cast_ring = v6.torus_y(
        f"forge_{size_key}_cast_retainer",
        radius,
        0.011 if large else 0.008,
        outward - 0.022,
        mats["body"],
        28 if large else 24,
        5,
    )
    cast_ring.parent = root
    inner_ring = v6.torus_y(
        f"forge_{size_key}_machined_seat",
        radius - (0.020 if large else 0.015),
        0.0055 if large else 0.004,
        outward,
        mats["metal"],
        28 if large else 24,
        4,
    )
    inner_ring.parent = root
    lug_count = 6 if large else 4
    for index in range(lug_count):
        angle = math.tau * index / lug_count
        lug = v4.prism(
            f"forge_{size_key}_mount_lug_{index}",
            0.052 if large else 0.038,
            0.046 if large else 0.034,
            0.009,
            0.0,
            -(0.085 if large else 0.060),
            mats["body"],
        )
        lug.location.x = math.sin(angle) * (radius + 0.018)
        lug.location.z = math.cos(angle) * (radius + 0.018)
        lug.rotation_euler.y = -angle
        lug.parent = root
    crown_count = 3 if large else 2
    for index in range(crown_count):
        crown = v4.cylinder_z(
            f"forge_{size_key}_pressure_port_{index}",
            0.016 if large else 0.012,
            0.036 if large else 0.026,
            (
                (index - (crown_count - 1) * 0.5)
                * (0.050 if large else 0.040),
                -0.030,
                radius + 0.038,
            ),
            mats["metal"],
            12,
        )
        crown.parent = root


def add_kinetic_structure(root, mats, size_key, config):
    large = size_key == "MeterLarge"
    width = 0.525 if large else 0.350
    height = width
    depth = 0.135 if large else 0.090
    armor = v4.shell(
        f"kinetic_{size_key}_armor_frame",
        width,
        height,
        0.060 if large else 0.040,
        width - (0.105 if large else 0.072),
        height - (0.105 if large else 0.072),
        0.033 if large else 0.022,
        depth,
        depth - 0.018,
        mats["body"],
    )
    armor.parent = root
    corner = width * 0.405
    for index, (x, z) in enumerate(
        ((-corner, -corner), (corner, -corner),
         (-corner, corner), (corner, corner))
    ):
        bumper = v4.prism(
            f"kinetic_{size_key}_corner_bumper_{index}",
            0.090 if large else 0.060,
            0.072 if large else 0.050,
            0.016 if large else 0.011,
            -depth + 0.012,
            -depth - 0.018,
            mats["metal"],
            z,
        )
        bumper.location.x = x
        bumper.parent = root
    vent_count = 7 if large else 5
    for index in range(vent_count):
        vent = v4.prism(
            f"kinetic_{size_key}_lower_vent_{index}",
            0.035 if large else 0.026,
            0.010 if large else 0.008,
            0.002,
            -depth - 0.008,
            -depth - 0.014,
            mats["gasket"],
            -height * 0.405,
        )
        vent.location.x = (
            index - (vent_count - 1) * 0.5
        ) * (0.050 if large else 0.038)
        vent.parent = root


THEME_STRUCTURE_BUILDERS = {
    "OrbitalAnalog": add_orbital_structure,
    "ForgeBrass": add_forge_structure,
    "KineticSafety": add_kinetic_structure,
}


def add_size_detail(root, mats, theme, size_key, config):
    large = size_key == "MeterLarge"
    radius = config["outer_radius"]
    outward = config["outward"]
    support_ring = v6.torus_y(
        f"{size_key}_secondary_bezel",
        radius - (0.030 if large else 0.022),
        0.0065 if large else 0.0045,
        outward,
        mats["metal"],
        28 if large else 24,
        4,
    )
    support_ring.parent = root
    gasket = v6.torus_y(
        f"{size_key}_glass_gasket",
        radius - (0.044 if large else 0.033),
        0.0035 if large else 0.0026,
        outward + 0.008,
        mats["gasket"],
        28 if large else 24,
        4,
    )
    gasket.parent = root
    add_fasteners(
        root,
        mats,
        radius - 0.008,
        outward - 0.030,
        12 if large else 8,
        0.0062 if large else 0.0045,
    )
    add_secondary_scale(
        root,
        mats,
        radius - (0.053 if large else 0.040),
        outward + 0.012,
        25 if large else 17,
        4,
    )
    THEME_STRUCTURE_BUILDERS[theme](
        root,
        mats,
        size_key,
        config,
    )


def meshes_under(root):
    return [obj for obj in root.children_recursive if obj.type == "MESH"]


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def generate_one(project_root, theme, size_key):
    config = SIZES[size_key]
    common.clean_scene()
    root, _, _ = v5.BUILDERS[(theme, "MeterRound")]()
    root.name = f"PF_Visual_{size_key}_{theme}_V6"
    root["instrument_type_id"] = config["type_id"]
    root["derived_from"] = "MeterRound V6 theme language"
    root["size_multiplier"] = config["front_scale"]
    root["depth_multiplier"] = config["depth_scale"]
    root["detail_policy"] = (
        "larger size adds frame layers, fasteners, secondary scale and "
        "theme-specific service structure"
    )
    mats = v5.materials(theme)
    gasket = bpy.data.materials.get(f"MAT_{theme}_V6_Gasket")
    if gasket is None:
        gasket = bpy.data.materials.new(f"MAT_{theme}_V6_Gasket")
    gasket["v6_material_role"] = "gasket"
    mats["gasket"] = gasket
    v6.DETAIL_BUILDERS[(theme, "MeterRound")](root, mats)
    scale_seed(
        root,
        config["front_scale"],
        config["depth_scale"],
    )
    add_size_detail(root, mats, theme, size_key, config)

    source_dir = (
        project_root / "ArtSource/Blender/ThemeHardSurfaceV6" / theme
    )
    retopo_path = source_dir / f"BL_{size_key}_{theme}_V6_Retopo.blend"
    save_blend(retopo_path)

    materials = v6_theme_materials.apply(
        project_root,
        theme,
        config["scale_class"],
    )
    v6_theme_materials.assign_special_roles(root, materials)
    meshes = meshes_under(root)
    z_values = [
        (obj.matrix_world @ Vector(corner)).z
        for obj in meshes
        for corner in obj.bound_box
    ]
    center_z = (min(z_values) + max(z_values)) * 0.5
    v6_theme_materials.set_emission_enabled(False)
    controls.create_preview(
        meshes,
        center_z,
        source_dir / f"Preview_{size_key}_{theme}_V6_MaterialOff.png",
    )
    v6_theme_materials.set_emission_enabled(True)
    controls.create_preview(
        meshes,
        center_z,
        source_dir / f"Preview_{size_key}_{theme}_V6_MaterialOn.png",
    )
    root["material_scale_class"] = config["scale_class"]
    material_path = (
        source_dir / f"BL_{size_key}_{theme}_V6_Material.blend"
    )
    save_blend(material_path)
    print(material_path)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    themes = (args.theme,) if args.theme else THEMES
    sizes = (args.size,) if args.size else tuple(SIZES)
    for theme in themes:
        for size_key in sizes:
            generate_one(project_root, theme, size_key)


if __name__ == "__main__":
    main()
