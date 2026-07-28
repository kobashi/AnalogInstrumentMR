"""Generate themed throttle and power-slider Blender and FBX assets."""

import argparse
import json
import shutil
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


THEMES = (
    ("OrbitalAnalog", "orbital-analog"),
    ("ForgeBrass", "forge-brass"),
    ("KineticSafety", "kinetic-safety"),
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def material(name):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (0.12, 0.14, 0.16, 1.0)
    return result


def cube(name, size, location, mat, uv=(0.125, 0.125), bevel=0.0015):
    return controls.add_cube(name, size, location, mat, uv, bevel)


def cylinder(name, radius, depth, outward, mat, uv=(0.625, 0.125)):
    result = common.add_cylinder(name, radius, depth, outward, 16, mat)
    common.set_constant_uv(result, uv)
    return result


def join(parts, name, root):
    result = common.join_objects(parts, name)
    result.parent = root
    return result


def theme_static_parts(theme, kind, opaque, emissive):
    if kind == "Throttle":
        parts = [
            cube("housing_plate", (0.24, 0.060, 0.30), (0, -0.030, 0), opaque),
            cube("slot_left", (0.012, 0.012, 0.22), (-0.032, -0.067, 0.015), opaque),
            cube("slot_right", (0.012, 0.012, 0.22), (0.032, -0.067, 0.015), opaque),
            cube("detent_scale", (0.010, 0.008, 0.23), (0.087, -0.066, 0.015), emissive),
        ]
        if theme == "ForgeBrass":
            for x in (-0.095, 0.095):
                for z in (-0.125, 0.125):
                    rivet = cylinder("housing_rivet", 0.004, 0.004, 0.064, opaque)
                    rivet.location.x = x
                    rivet.location.z = z
                    parts.append(rivet)
        elif theme == "KineticSafety":
            parts.extend(
                (
                    cube("guard_left", (0.020, 0.020, 0.27), (-0.105, -0.071, 0), opaque),
                    cube("guard_right", (0.020, 0.020, 0.27), (0.105, -0.071, 0), opaque),
                )
            )
        else:
            parts.extend(
                (
                    cube("rail_left", (0.014, 0.014, 0.26), (-0.092, -0.069, 0), opaque),
                    cube("rail_right", (0.014, 0.014, 0.26), (0.092, -0.069, 0), opaque),
                )
            )
        collar = cylinder("housing_collar", 0.038, 0.018, 0.077, opaque)
        collar.location.z = -0.105
        parts.append(collar)
        return parts

    parts = [
        cube("housing_plate", (0.16, 0.050, 0.34), (0, -0.025, 0), opaque),
        cube("slot_left", (0.012, 0.014, 0.25), (-0.027, -0.057, 0), opaque),
        cube("slot_right", (0.012, 0.014, 0.25), (0.027, -0.057, 0), opaque),
        cube("power_scale", (0.012, 0.009, 0.27), (0.060, -0.057, 0), emissive),
    ]
    if theme == "ForgeBrass":
        parts.extend(
            (
                cylinder("top_rivet", 0.004, 0.004, 0.055, opaque),
                cylinder("bottom_rivet", 0.004, 0.004, 0.055, opaque),
            )
        )
        parts[-2].location.z = 0.145
        parts[-1].location.z = -0.145
    elif theme == "KineticSafety":
        parts.extend(
            (
                cube("guard_top", (0.135, 0.018, 0.018), (0, -0.059, 0.151), opaque),
                cube("guard_bottom", (0.135, 0.018, 0.018), (0, -0.059, -0.151), opaque),
            )
        )
    else:
        parts.extend(
            (
                cube("frame_left", (0.014, 0.014, 0.30), (-0.067, -0.057, 0), opaque),
                cube("frame_right", (0.014, 0.014, 0.30), (0.067, -0.057, 0), opaque),
            )
        )
    return parts


def build_throttle(theme, suffix, opaque, emissive):
    root = controls.create_root(
        f"PF_Visual_Throttle_{suffix}", "control.throttle"
    )
    root["theme_id"] = theme
    housing = join(
        theme_static_parts(suffix, "Throttle", opaque, emissive),
        "housing",
        root,
    )
    pivot_point = (0.0, -0.086, -0.105)
    shaft = controls.add_vertical_cylinder(
        "throttle_shaft",
        0.011,
        0.205,
        (0.0, -0.086, -0.0025),
        12,
        opaque,
        (0.875, 0.125),
    )
    crossbar = cube(
        "throttle_grip",
        (0.105, 0.034, 0.045),
        (0.0, -0.086, 0.122),
        emissive,
        (0.375, 0.125),
        0.006,
    )
    pivot, handle = controls.parent_at_pivot(
        [shaft, crossbar], "throttle_handle", pivot_point, root
    )
    pivot.name = "throttle_pivot"
    controls.set_smooth([housing, handle])
    return root, [housing, handle], pivot, handle, 0.01


def build_slider(theme, suffix, opaque, emissive):
    root = controls.create_root(
        f"PF_Visual_PowerSlider_{suffix}", "control.power_slider"
    )
    root["theme_id"] = theme
    housing = join(
        theme_static_parts(suffix, "PowerSlider", opaque, emissive),
        "housing",
        root,
    )
    carriage = cube(
        "slider_carriage",
        (0.085, 0.022, 0.055),
        (0.0, -0.065, 0.0),
        opaque,
        (0.875, 0.125),
        0.005,
    )
    grip = cube(
        "slider_grip",
        (0.115, 0.024, 0.022),
        (0.0, -0.082, 0.0),
        emissive,
        (0.375, 0.125),
        0.005,
    )
    travel, movable = controls.parent_at_pivot(
        [carriage, grip], "slider_handle", (0.0, -0.065, 0.0), root
    )
    travel.name = "slider_travel"
    controls.set_smooth([housing, movable])
    return root, [housing, movable], travel, movable, 0.0


def save(project_root, suffix, key, root, meshes, pivot, movable, center_z):
    source_dir = project_root / f"ArtSource/Blender/{suffix}"
    model_dir = (
        project_root
        / f"Assets/MatsuMotoMeterAR/Content/Themes/{suffix}/Models"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    stats = common.mesh_stats(meshes)
    stats.update(
        {
            "asset": f"{key}_{suffix}",
            "instrument_type_id": (
                "control.throttle"
                if key == "Throttle"
                else "control.power_slider"
            ),
            "theme_id": root["theme_id"],
            "unity_mount_axis": "+Z",
            "pivot": pivot.name,
            "movable": movable.name,
            "greybox_triangle_budget": 1500,
            "renderer_budget": 3,
            "material_budget": 2,
            "colliders": 0,
            "realtime_lights": 0,
        }
    )
    if stats["triangles"] > 1500 or stats["mesh_objects"] > 3:
        raise RuntimeError(f"Asset budget exceeded: {stats}")
    limits = (0.24001, 0.34001, 0.16001) if key == "Throttle" else (
        0.16001,
        0.34001,
        0.10001,
    )
    if any(value > limit for value, limit in zip(stats["unity_bounds_m"], limits)):
        raise RuntimeError(f"Asset bounds exceeded: {stats}")

    controls.create_preview(meshes, center_z, source_dir / f"Preview_{key}_{suffix}.png")
    bpy.context.preferences.filepaths.save_version = 0
    blend = source_dir / f"BL_{key}_{suffix}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    blend.with_suffix(".blend1").unlink(missing_ok=True)
    fbx = model_dir / f"SM_{key}_{suffix}.fbx"
    fbm = fbx.with_suffix(".fbm")
    if fbm.exists():
        shutil.rmtree(fbm)
    common.export_fbx(root, fbx)
    (source_dir / f"BL_{key}_{suffix}.report.json").write_text(
        json.dumps(stats, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(stats, indent=2))


def main():
    project_root = Path(parse_args().project_root).resolve()
    for suffix, theme_id in THEMES:
        for key, builder in (
            ("Throttle", build_throttle),
            ("PowerSlider", build_slider),
        ):
            common.clean_scene()
            opaque = material(f"MAT_{suffix}_Atlas")
            emissive = material(f"MAT_{suffix}_Emissive")
            root, meshes, pivot, movable, center_z = builder(
                theme_id, suffix, opaque, emissive
            )
            common.apply_transforms(meshes)
            save(
                project_root,
                suffix,
                key,
                root,
                meshes,
                pivot,
                movable,
                center_z,
            )


if __name__ == "__main__":
    main()
