"""Generate Forge Brass and Orbital Analog V4 hard-surface candidates.

Geometry comes from the validated Kinetic V4 clean-cage builders. Each theme
receives its own PBR palette and a topology-safe mechanical signature layer.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_hardsurface_kinetic_set_v4 as v4
import generate_hardsurface_lever_prototype as hs
import generate_hardsurface_lever_retopo_v3 as retopo
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


THEMES = {
    "ForgeBrass": {
        "id": "forge-brass",
        "folder": "ForgeBrass",
        "palette": {
            "graphite": ((0.045, 0.027, 0.015, 1.0), 0.72, 0.56),
            "gunmetal": ((0.34, 0.16, 0.045, 1.0), 0.92, 0.31),
            "accent": ((0.88, 0.35, 0.055, 1.0), 0.42, 0.24),
            "emission": (1.0, 0.48, 0.10, 1.0),
        },
    },
    "OrbitalAnalog": {
        "id": "orbital-analog",
        "folder": "OrbitalAnalog",
        "palette": {
            "graphite": ((0.012, 0.030, 0.052, 1.0), 0.48, 0.28),
            "gunmetal": ((0.18, 0.27, 0.34, 1.0), 0.76, 0.20),
            "accent": ((0.02, 0.38, 0.62, 1.0), 0.16, 0.16),
            "emission": (0.05, 0.78, 1.0, 1.0),
        },
    },
}

ASSETS = (
    ("Lever", "control.lever", 5000),
) + v4.ASSETS


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--themes",
        nargs="+",
        choices=tuple(THEMES),
        default=tuple(THEMES),
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[item[0] for item in ASSETS],
    )
    parser.add_argument("--skip-previews", action="store_true")
    return parser.parse_args(args)


def theme_materials(theme):
    palette = theme["palette"]
    base_color, metallic, roughness = palette["graphite"]
    metal_color, metal_metallic, metal_roughness = palette["gunmetal"]
    accent_color, accent_metallic, accent_roughness = palette["accent"]
    return {
        "graphite": hs.material(
            f"MAT_{theme['folder']}_V4_Housing",
            base_color,
            metallic,
            roughness,
        ),
        "gunmetal": hs.material(
            f"MAT_{theme['folder']}_V4_Metal",
            metal_color,
            metal_metallic,
            metal_roughness,
        ),
        "cyan": hs.material(
            f"MAT_{theme['folder']}_V4_Emission",
            accent_color,
            accent_metallic,
            accent_roughness,
            emission=palette["emission"],
        ),
    }


def theme_root(theme, key, type_id):
    root = bpy.data.objects.new(
        f"PF_Visual_{key}_{theme['folder']}_V4",
        None,
    )
    root.empty_display_type = "PLAIN_AXES"
    root["instrument_type_id"] = type_id
    root["theme_id"] = theme["id"]
    root["unity_mount_axis"] = "+Z"
    root["modeling_method"] = "clean hard-surface retopo cage"
    root["quality_floor"] = "Lever_KineticSafety_HS_V3_Retopo"
    bpy.context.collection.objects.link(root)
    return root


def bounds_for(root):
    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    return (
        min(point.x for point in points),
        max(point.x for point in points),
        min(point.y for point in points),
        max(point.z for point in points),
        min(point.z for point in points),
    )


def add_signature(root, key, theme, mats):
    if key == "Lever":
        return
    min_x, max_x, min_y, max_z, min_z = bounds_for(root)
    width = max_x - min_x
    height = max_z - min_z
    outward = abs(min_y) + max(width, height) * 0.006
    details = []
    if theme["id"] == "forge-brass":
        if key in ("WindowMeter", "WindowPanel"):
            return
        inset_x = width * 0.42
        inset_z = height * 0.42
        radius = max(0.0026, min(width, height) * 0.024)
        for index, (x, z) in enumerate(
            (
                (-inset_x, -inset_z),
                (inset_x, -inset_z),
                (-inset_x, inset_z),
                (inset_x, inset_z),
            )
        ):
            details.append(
                v4.fastener(
                    f"forge_signature_fastener_{index}",
                    x,
                    z,
                    outward,
                    mats["gunmetal"],
                    radius,
                )
            )
    else:
        bar_width = width * 0.44
        bar_height = max(0.0035, height * 0.012)
        for index, z in enumerate((-height * 0.40, height * 0.40)):
            details.append(
                v4.accent_bar(
                    f"orbital_signature_light_{index}",
                    bar_width,
                    bar_height,
                    0.0,
                    z,
                    outward,
                    mats["cyan"],
                )
            )
    signature = common.join_objects(details, "theme_signature")
    signature.parent = root


def build_lever(theme):
    root, meshes = retopo.build_retopo()
    mats = theme_materials(theme)
    root.name = f"PF_Visual_Lever_{theme['folder']}_V4"
    root["theme_id"] = theme["id"]
    root["quality_floor"] = "Lever_KineticSafety_HS_V3_Retopo"
    for obj in meshes:
        for slot in obj.material_slots:
            token = slot.material.name.lower() if slot.material else ""
            if "cyan" in token:
                slot.material = mats["cyan"]
            elif "gunmetal" in token:
                slot.material = mats["gunmetal"]
            else:
                slot.material = mats["graphite"]
    return (
        root,
        (0.0, -0.057, -0.025),
        (1.0, 0.0, 0.0),
        mats,
    )


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def generate_one(
    project_root,
    theme,
    key,
    type_id,
    triangle_budget,
    skip_previews,
):
    common.clean_scene()
    if key == "Lever":
        root, pivot_position, local_axis, mats = build_lever(theme)
    else:
        mats = theme_materials(theme)
        v4.materials = lambda: mats
        v4.root_for = lambda built_key, built_type: theme_root(
            theme,
            built_key,
            built_type,
        )
        root, pivot_position, local_axis = v4.BUILDERS[key]()
    add_signature(root, key, theme, mats)
    meshes = v4.meshes_under(root)
    common.apply_transforms(meshes)
    source_stats = retopo.topology_stats(meshes)
    if source_stats["non_manifold_edges"] != 0:
        raise RuntimeError(f"{theme['folder']}/{key}: non-manifold source")
    if source_stats["zero_area_faces"] != 0:
        raise RuntimeError(f"{theme['folder']}/{key}: degenerate source")

    source_dir = (
        project_root
        / "ArtSource/Blender/HardSurfacePrototype"
        / theme["folder"]
        / "V4"
    )
    model_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates"
        / theme["folder"]
        / "HardSurfacePrototype/V4"
    )
    source_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    if not skip_previews:
        controls.create_preview(
            meshes,
            0.0,
            source_dir
            / f"Preview_{key}_{theme['folder']}_HS_V4.png",
        )
        retopo.render_topology_preview(
            meshes,
            source_dir
            / f"Preview_{key}_{theme['folder']}_HS_V4_Topology.png",
        )
    save_blend(
        source_dir
        / f"BL_{key}_{theme['folder']}_HS_V4_Retopo.blend"
    )

    retopo.triangulate(meshes)
    final_stats = retopo.topology_stats(meshes)
    if final_stats["non_manifold_edges"] != 0:
        raise RuntimeError(f"{theme['folder']}/{key}: non-manifold final")
    if final_stats["zero_area_faces"] != 0:
        raise RuntimeError(f"{theme['folder']}/{key}: degenerate final")
    if final_stats["faces"] > triangle_budget:
        raise RuntimeError(
            f"{theme['folder']}/{key}: "
            f"{final_stats['faces']} > {triangle_budget}"
        )
    save_blend(
        source_dir
        / f"BL_{key}_{theme['folder']}_HS_V4_Triangulated.blend"
    )
    fbx_path = (
        model_dir
        / f"SM_{key}_{theme['folder']}_HS_V4_Retopo.fbx"
    )
    fbm_path = fbx_path.with_suffix(".fbm")
    if fbm_path.exists():
        shutil.rmtree(fbm_path)
    common.export_fbx(root, fbx_path)
    report = {
        "asset": f"{key}_{theme['folder']}_HS_V4_Retopo",
        "theme_id": theme["id"],
        "quality_floor": "Lever_KineticSafety_HS_V3_Retopo",
        "source_topology": source_stats,
        "triangulated_topology": final_stats,
        "triangle_budget": triangle_budget,
        "pivot": {
            "position": list(pivot_position),
            "local_axis": list(local_axis),
        },
        "fbx": str(fbx_path.relative_to(project_root)),
        "production_integrated": False,
    }
    (
        source_dir
        / f"{key}_{theme['folder']}_HS_V4_Retopo.report.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report))


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    only = set(args.only or ())
    for theme_name in args.themes:
        theme = THEMES[theme_name]
        for key, type_id, triangle_budget in ASSETS:
            if only and key not in only:
                continue
            generate_one(
                project_root,
                theme,
                key,
                type_id,
                triangle_budget,
                args.skip_previews,
            )


if __name__ == "__main__":
    main()
