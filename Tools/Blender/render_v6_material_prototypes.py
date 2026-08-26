"""Render all V6 objects with the shared PBR material prototypes."""

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_orbital_analog_controls as controls
import v6_theme_materials


THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
OBJECTS = (
    "MeterRound",
    "MeterMedium",
    "MeterLarge",
    "Lever",
    "Toggle",
    "Rotary",
    "Button",
    "Lamp",
    "Throttle",
    "PowerSlider",
    "StatusIndicator",
    "WindowMeter",
    "WindowPanel",
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--object", dest="object_key", choices=OBJECTS)
    parser.add_argument("--theme", choices=THEMES)
    parser.add_argument(
        "--source-dir",
        default=None,
        help=(
            "Read the Retopo blend from here instead of "
            "ArtSource/Blender/ThemeHardSurfaceV6/<Theme>. Used to run a "
            "brush-up candidate through this stage."
        ),
    )
    parser.add_argument(
        "--source-suffix",
        default="_Retopo",
        help="Filename suffix of the input blend, e.g. _Opus5_R2_Retopo.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Write the Material blend and previews here instead of the "
            "production source directory. Use this for every candidate run."
        ),
    )
    return parser.parse_args(args)


def theme_source_dir(project_root, theme, override=None):
    if override is not None:
        return Path(override)
    return project_root / "ArtSource/Blender/ThemeHardSurfaceV6" / theme


def render_one(
    project_root,
    theme,
    key,
    source_dir=None,
    output_dir=None,
    source_suffix="_Retopo",
):
    source_dir = theme_source_dir(project_root, theme, source_dir)
    output_dir = source_dir if output_dir is None else Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(
        filepath=str(source_dir / f"BL_{key}_{theme}_V6{source_suffix}.blend")
    )
    root = bpy.data.objects.get(f"PF_Visual_{key}_{theme}_V6")
    if root is None:
        raise RuntimeError(f"{theme}/{key}: root not found")
    scale_class = (
        "Large"
        if key in ("MeterLarge", "WindowMeter", "WindowPanel")
        else "Medium"
        if key == "MeterMedium"
        else "Standard"
    )
    materials = v6_theme_materials.apply(
        project_root,
        theme,
        scale_class,
    )
    v6_theme_materials.assign_special_roles(root, materials)
    meshes = [
        obj for obj in root.children_recursive if obj.type == "MESH"
    ]
    z_values = [
        (obj.matrix_world @ Vector(corner)).z
        for obj in meshes
        for corner in obj.bound_box
    ]
    center_z = (min(z_values) + max(z_values)) * 0.5
    v6_theme_materials.set_emission_enabled(False)
    output_off = (
        output_dir / f"Preview_{key}_{theme}_V6_MaterialOff.png"
    )
    controls.create_preview(meshes, center_z, output_off)
    v6_theme_materials.set_emission_enabled(True)
    output_on = (
        output_dir / f"Preview_{key}_{theme}_V6_MaterialOn.png"
    )
    controls.create_preview(meshes, center_z, output_on)
    root["material_pass"] = "V6 shared PBR atlas prototype"
    atlas_suffix = "_Large" if scale_class == "Large" else ""
    root["material_atlas"] = f"T_{theme}_V6_Atlas{atlas_suffix}"
    root["material_scale_class"] = scale_class
    blend_path = output_dir / f"BL_{key}_{theme}_V6_Material.blend"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    blend_path.with_suffix(".blend1").unlink(missing_ok=True)
    print(output_off)
    print(output_on)


def main():
    blender_compat.require_v6_pipeline()
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    objects = (args.object_key,) if args.object_key else OBJECTS
    themes = (args.theme,) if args.theme else THEMES
    for theme in themes:
        for key in objects:
            render_one(
                project_root,
                theme,
                key,
                args.source_dir,
                args.output_dir,
                args.source_suffix,
            )


if __name__ == "__main__":
    main()
