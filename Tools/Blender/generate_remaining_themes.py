"""Generate Forge Brass and Kinetic Safety Blender/FBX reference assets."""

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


THEMES = (
    {
        "id": "forge-brass",
        "folder": "ForgeBrass",
        "suffix": "ForgeBrass",
        "palette": {
            "housing": (0.055, 0.040, 0.026, 1.0),
            "focus": (0.82, 0.25, 0.035, 1.0),
            "accent": (0.48, 0.27, 0.075, 1.0),
            "face": (0.70, 0.59, 0.33, 1.0),
            "dial": (0.026, 0.019, 0.012, 1.0),
            "tick": (0.88, 0.74, 0.42, 1.0),
            "rim": (0.34, 0.19, 0.055, 1.0),
        },
    },
    {
        "id": "kinetic-safety",
        "folder": "KineticSafety",
        "suffix": "KineticSafety",
        "palette": {
            "housing": (0.022, 0.036, 0.050, 1.0),
            "focus": (1.0, 0.20, 0.015, 1.0),
            "accent": (0.92, 0.58, 0.025, 1.0),
            "face": (0.52, 0.60, 0.64, 1.0),
            "dial": (0.012, 0.022, 0.030, 1.0),
            "tick": (1.0, 0.70, 0.055, 1.0),
            "rim": (0.16, 0.20, 0.23, 1.0),
        },
    },
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def build_texture_atlas(theme, texture_dir):
    size = common.ATLAS_SIZE
    palette = theme["palette"]
    base = np.zeros((size, size, 4), dtype=np.float32)
    base[:, :, :] = palette["housing"]
    base[0:256, 256:512, :] = palette["focus"]
    base[0:256, 512:768, :] = palette["accent"]
    base[0:256, 768:1024, :] = palette["face"]

    yy, xx = np.ogrid[:size, :size]
    cx = cy = 768
    dx = xx - cx
    dy = yy - cy
    radius = np.sqrt(dx * dx + dy * dy)
    dial = radius <= 238
    base[dial] = palette["dial"]
    base[(radius >= 224) & (radius <= 238)] = palette["rim"]

    marks = np.zeros((size, size), dtype=bool)
    start = math.radians(220)
    end = math.radians(-40)
    for index in range(41):
        angle = start + (end - start) * (index / 40)
        outer = 214
        inner = 177 if index % 5 == 0 else 197
        for radial in np.linspace(inner, outer, max(2, outer - inner)):
            px = int(round(cx + math.cos(angle) * radial))
            py = int(round(cy + math.sin(angle) * radial))
            thickness = 2 if index % 5 == 0 else 1
            marks[
                max(0, py - thickness) : min(size, py + thickness + 1),
                max(0, px - thickness) : min(size, px + thickness + 1),
            ] = True

    angle_field = np.arctan2(dy, dx)
    normalized = np.mod(angle_field - end, math.pi * 2)
    active = normalized <= np.mod(start - end, math.pi * 2)
    arcs = ((radius >= 157) & (radius <= 160) & active) | (
        (radius >= 142) & (radius <= 144) & active
    )
    base[marks | arcs] = palette["tick"]

    if theme["id"] == "kinetic-safety":
        stripe = dial & (((xx + yy) // 18) % 2 == 0) & (radius > 218)
        base[stripe] = palette["focus"]

    emission = np.zeros_like(base)
    emission[:, :, 3] = 1.0
    emission[marks | arcs] = tuple(value * 0.62 for value in palette["tick"][:3]) + (1.0,)
    emission[0:256, 256:512, :] = tuple(
        value * 0.55 for value in palette["focus"][:3]
    ) + (1.0,)

    normal = np.zeros_like(base)
    normal[:, :, :] = (0.5, 0.5, 1.0, 1.0)
    mask = np.zeros_like(base)
    mask[:, :, :] = (0.72, 0.0, 0.0, 0.24)
    mask[dial] = (0.0, 0.0, 0.0, 0.18)
    mask[0:256, 256:512, :] = (0.35, 0.0, 0.0, 0.28)

    prefix = f"T_{theme['suffix']}_Atlas"
    paths = {
        "base_color": texture_dir / f"{prefix}_BaseColor.png",
        "normal": texture_dir / f"{prefix}_Normal.png",
        "metallic_smoothness": texture_dir / f"{prefix}_MetallicSmoothness.png",
        "emission": texture_dir / f"{prefix}_Emission.png",
    }
    images = {
        "base_color": common.save_rgba_image(
            f"{prefix}_BaseColor", base, paths["base_color"]
        ),
        "normal": common.save_rgba_image(
            f"{prefix}_Normal", normal, paths["normal"], "Non-Color"
        ),
        "metallic_smoothness": common.save_rgba_image(
            f"{prefix}_MetallicSmoothness",
            mask,
            paths["metallic_smoothness"],
            "Non-Color",
        ),
        "emission": common.save_rgba_image(
            f"{prefix}_Emission", emission, paths["emission"], "Non-Color"
        ),
    }
    return paths, images


def create_materials(theme, base_image):
    opaque = common.create_material(base_image)
    opaque.name = f"MAT_{theme['suffix']}_Atlas"
    emissive = common.create_emissive_material(base_image)
    emissive.name = f"MAT_{theme['suffix']}_Emissive"
    return opaque, emissive


def add_static_decor(theme, key, housing, root, opaque):
    parts = [housing]
    if theme["id"] == "forge-brass":
        positions = {
            "Lever": ((-0.073, -0.056), (0.073, -0.056)),
            "Toggle": ((-0.047, -0.055), (0.047, -0.055)),
            "Rotary": ((-0.058, -0.058), (0.058, 0.058)),
            "Button": ((-0.050, -0.050), (0.050, 0.050)),
            "Lamp": ((-0.055, -0.038), (0.055, 0.038)),
        }[key]
        for x, z in positions:
            rivet = common.add_cylinder(
                "housing_rivet", 0.0034, 0.0025, 0.043, 8, opaque
            )
            rivet.location.x = x
            rivet.location.z = z
            common.set_constant_uv(rivet, (0.625, 0.125))
            parts.append(rivet)
    else:
        guard_specs = {
            "Lever": (
                ((0.0, -0.061, -0.057), (0.140, 0.010, 0.016)),
                ((0.0, -0.061, 0.057), (0.140, 0.010, 0.016)),
            ),
            "Toggle": (
                ((-0.050, -0.045, 0.0), (0.012, 0.010, 0.105)),
                ((0.050, -0.045, 0.0), (0.012, 0.010, 0.105)),
            ),
            "Rotary": (
                ((-0.058, -0.050, 0.0), (0.015, 0.012, 0.110)),
                ((0.058, -0.050, 0.0), (0.015, 0.012, 0.110)),
            ),
            "Button": (
                ((-0.050, -0.050, 0.0), (0.014, 0.012, 0.095)),
                ((0.050, -0.050, 0.0), (0.014, 0.012, 0.095)),
            ),
            "Lamp": (
                ((0.0, -0.047, -0.041), (0.095, 0.012, 0.012)),
                ((0.0, -0.047, 0.041), (0.095, 0.012, 0.012)),
            ),
        }[key]
        for index, (location, dimensions) in enumerate(guard_specs):
            guard = controls.add_cube(
                f"housing_guard_{index}",
                dimensions,
                location,
                opaque,
                (0.625, 0.125),
                0.0015,
            )
            parts.append(guard)

    joined = common.join_objects(parts, "housing")
    joined.parent = root
    return joined


def decorate_meter(theme, housing, root, opaque):
    parts = [housing]
    if theme["id"] == "forge-brass":
        ring = common.add_torus(
            "housing_brass_step", 0.0515, 0.0026, 0.043, opaque
        )
        common.set_constant_uv(ring, (0.625, 0.125))
        parts.append(ring)
    else:
        for index, (x, z) in enumerate(
            ((-0.051, -0.051), (0.051, -0.051), (-0.051, 0.051), (0.051, 0.051))
        ):
            guard = controls.add_cube(
                f"housing_corner_guard_{index}",
                (0.026, 0.010, 0.014),
                (x, -0.038, z),
                opaque,
                (0.625, 0.125),
                0.0015,
            )
            guard.rotation_euler.y = math.radians(45 if x * z > 0 else -45)
            parts.append(guard)
    joined = common.join_objects(parts, "housing")
    joined.parent = root
    return joined


def save_asset(
    theme,
    key,
    root,
    meshes,
    project_root,
    stats,
    center_z=0.0,
):
    source_dir = project_root / f"ArtSource/Blender/{theme['folder']}"
    model_dir = (
        project_root
        / f"Assets/MatsuMotoMeterAR/Content/Themes/{theme['folder']}/Models"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    preview = source_dir / f"Preview_{key}_{theme['suffix']}.png"
    controls.create_preview(meshes, center_z, preview)
    blend = source_dir / f"BL_{key}_{theme['suffix']}.blend"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    backup = blend.with_suffix(".blend1")
    if backup.exists():
        backup.unlink()
    fbx = model_dir / f"SM_{key}_{theme['suffix']}.fbx"
    copied = model_dir / f"SM_{key}_{theme['suffix']}.fbm"
    if copied.exists():
        shutil.rmtree(copied)
    common.export_fbx(root, fbx)
    report = source_dir / f"BL_{key}_{theme['suffix']}.report.json"
    report.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


def generate_meter(theme, project_root, base_image, texture_paths):
    common.clean_scene()
    opaque, emissive = create_materials(theme, base_image)
    original_root = common.ROOT_NAME
    common.ROOT_NAME = f"PF_Visual_MeterRound_{theme['suffix']}"
    try:
        root, housing, dial, pivot, needle = common.build_meter(opaque, emissive)
    finally:
        common.ROOT_NAME = original_root
    root["theme_id"] = theme["id"]
    housing = decorate_meter(theme, housing, root, opaque)
    meshes = [housing, dial, needle]
    common.apply_transforms(meshes)
    stats = common.mesh_stats(meshes)
    stats.update(
        {
            "asset": f"MeterRound_{theme['suffix']}",
            "instrument_type_id": "meter.round",
            "theme_id": theme["id"],
            "unity_mount_axis": "+Z",
            "pivot": pivot.name,
            "movable": needle.name,
            "greybox_triangle_budget": 1500,
            "renderer_budget": 4,
            "material_budget": 2,
            "colliders": 0,
            "realtime_lights": 0,
            "textures": {
                key: str(path.relative_to(project_root))
                for key, path in texture_paths.items()
            },
        }
    )
    validate_stats(stats, (0.14001, 0.14001, 0.06401))
    save_asset(theme, "MeterRound", root, meshes, project_root, stats)


def generate_control(theme, asset, project_root, base_image):
    common.clean_scene()
    opaque, emissive = create_materials(theme, base_image)
    controls.THEME_ID = theme["id"]
    built = asset["builder"](opaque, emissive)
    root = built["root"]
    root.name = f"PF_Visual_{asset['key']}_{theme['suffix']}"
    root["theme_id"] = theme["id"]
    housing = add_static_decor(
        theme, asset["key"], built["meshes"][0], root, opaque
    )
    meshes = [housing, built["movable"]]
    common.apply_transforms(meshes)
    stats = common.mesh_stats(meshes)
    stats.update(
        {
            "asset": f"{asset['key']}_{theme['suffix']}",
            "instrument_type_id": asset["type_id"],
            "theme_id": theme["id"],
            "unity_mount_axis": "+Z",
            "pivot": built["pivot"].name if built["pivot"] else None,
            "movable": built["movable"].name,
            "greybox_triangle_budget": 1500,
            "renderer_budget": 3,
            "material_budget": 2,
            "colliders": 0,
            "realtime_lights": 0,
        }
    )
    validate_stats(stats, asset["limits"])
    save_asset(
        theme,
        asset["key"],
        root,
        meshes,
        project_root,
        stats,
        built["center_z"],
    )


def validate_stats(stats, limits):
    if stats["triangles"] > stats["greybox_triangle_budget"]:
        raise RuntimeError(f"Triangle budget exceeded: {stats}")
    if stats["mesh_objects"] > stats["renderer_budget"]:
        raise RuntimeError(f"Renderer budget exceeded: {stats}")
    if stats["materials"] > stats["material_budget"]:
        raise RuntimeError(f"Material budget exceeded: {stats}")
    if any(
        value > limit for value, limit in zip(stats["unity_bounds_m"], limits)
    ):
        raise RuntimeError(f"Bounds exceeded: {stats}")


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    for theme in THEMES:
        texture_dir = (
            project_root
            / f"Assets/MatsuMotoMeterAR/Content/Themes/{theme['folder']}/Textures"
        )
        texture_dir.mkdir(parents=True, exist_ok=True)
        common.clean_scene()
        texture_paths, images = build_texture_atlas(theme, texture_dir)
        base_image = images["base_color"]
        generate_meter(theme, project_root, base_image, texture_paths)
        for asset in controls.ASSETS:
            generate_control(theme, asset, project_root, base_image)


if __name__ == "__main__":
    main()
