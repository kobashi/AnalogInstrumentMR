"""Validate Forge Brass and Kinetic Safety .blend/FBX asset round-trips."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_orbital_analog_controls as validation


THEMES = (
    ("ForgeBrass", "forge-brass"),
    ("KineticSafety", "kinetic-safety"),
)

ASSETS = (
    {
        "key": "MeterRound",
        "meshes": ("housing", "dial", "needle"),
        "pivot": "needle_pivot",
        "movable": "needle",
        "limits": (0.14001, 0.14001, 0.06401),
        "motion_axis": "Blender Y / Unity Z",
        "motion_range": "±55°",
    },
    {
        "key": "Lever",
        "meshes": ("housing", "handle"),
        "pivot": "handle_pivot",
        "movable": "handle",
        "limits": (0.18001, 0.25601, 0.10001),
        "motion_axis": "Blender X / Unity X",
        "motion_range": "±32°",
    },
    {
        "key": "Toggle",
        "meshes": ("housing", "switch"),
        "pivot": "switch_pivot",
        "movable": "switch",
        "limits": (0.12001, 0.17001, 0.06401),
        "motion_axis": "Blender X / Unity X",
        "motion_range": "±28°",
    },
    {
        "key": "Rotary",
        "meshes": ("housing", "knob"),
        "pivot": "knob_pivot",
        "movable": "knob",
        "limits": (0.15001, 0.15001, 0.10201),
        "motion_axis": "Blender Y / Unity Z",
        "motion_range": "continuous",
    },
    {
        "key": "Button",
        "meshes": ("housing", "button"),
        "pivot": "button_travel",
        "movable": "button",
        "limits": (0.13001, 0.13001, 0.09001),
        "motion_axis": "Blender +Y / Unity -Z",
        "motion_range": "14 mm",
    },
    {
        "key": "Lamp",
        "meshes": ("housing", "indicator"),
        "pivot": None,
        "movable": "indicator",
        "limits": (0.14001, 0.11001, 0.08201),
        "motion_axis": None,
        "motion_range": None,
    },
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    results = {}
    for suffix, theme_id in THEMES:
        source_dir = project_root / f"ArtSource/Blender/{suffix}"
        model_dir = (
            project_root
            / f"Assets/MatsuMotoMeterAR/Content/Themes/{suffix}/Models"
        )
        theme_results = {}
        for source in ASSETS:
            asset = dict(source)
            asset["root"] = f"PF_Visual_{asset['key']}_{suffix}"
            blend_path = source_dir / f"BL_{asset['key']}_{suffix}.blend"
            fbx_path = model_dir / f"SM_{asset['key']}_{suffix}.fbx"

            bpy.ops.wm.open_mainfile(filepath=str(blend_path))
            root = bpy.data.objects.get(asset["root"])
            if root is None or root.get("theme_id") != theme_id:
                raise RuntimeError(
                    f"{suffix}/{asset['key']}: invalid root theme metadata"
                )
            blend = validation.validate_scene(asset, "blend")
            if bpy.data.cameras or bpy.data.lights:
                raise RuntimeError(
                    f"{suffix}/{asset['key']}: preview camera/light retained"
                )

            validation.clear_scene()
            bpy.ops.import_scene.fbx(filepath=str(fbx_path), use_anim=False)
            fbx = validation.validate_scene(asset, "fbx-roundtrip")
            theme_results[asset["key"]] = {
                "blend": blend,
                "fbx_roundtrip": fbx,
                "status": "PASS",
            }

        texture_dir = (
            project_root
            / f"Assets/MatsuMotoMeterAR/Content/Themes/{suffix}/Textures"
        )
        for map_name in (
            "BaseColor",
            "Normal",
            "MetallicSmoothness",
            "Emission",
        ):
            path = texture_dir / f"T_{suffix}_Atlas_{map_name}.png"
            if not path.is_file():
                raise RuntimeError(f"Missing texture: {path}")
        results[suffix] = theme_results

    print(json.dumps({"themes": results, "status": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
