"""Non-destructive Blender 5.2 open/export smoke test for a V6 source file."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common
import v6_theme_materials


THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-root")
    parser.add_argument("--render-preview", action="store_true")
    return parser.parse_args(args)


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_material_preview(source, expected_root, output_path):
    theme = next(
        (candidate for candidate in THEMES if f"_{candidate}_V6" in expected_root),
        None,
    )
    if theme is None:
        raise RuntimeError(f"Could not resolve theme from {expected_root}")
    prefix = "PF_Visual_"
    suffix = f"_{theme}_V6"
    key = expected_root[len(prefix) : -len(suffix)]
    retopo_source = source.parent / f"BL_{key}_{theme}_V6_Retopo.blend"
    if not retopo_source.is_file():
        raise FileNotFoundError(retopo_source)

    bpy.ops.wm.open_mainfile(filepath=str(retopo_source), load_ui=False)
    blender_compat.require_v6_pipeline()
    root = bpy.data.objects.get(expected_root)
    if root is None:
        raise RuntimeError(f"Material preview root was not found: {expected_root}")
    scale_class = (
        "Large"
        if key in ("MeterLarge", "WindowMeter", "WindowPanel")
        else "Medium"
        if key == "MeterMedium"
        else "Standard"
    )
    project_root = Path(__file__).resolve().parents[2]
    materials = v6_theme_materials.apply(project_root, theme, scale_class)
    v6_theme_materials.assign_special_roles(root, materials)
    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    world_corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    center_z = (
        min(point.z for point in world_corners)
        + max(point.z for point in world_corners)
    ) * 0.5
    v6_theme_materials.set_emission_enabled(True)
    controls.create_preview(meshes, center_z, output_path)


def main():
    args = parse_args()
    source = Path(args.source).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    blender_compat.require_v6_pipeline()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    blender_compat.require_v6_pipeline()

    roots = [
        obj
        for obj in bpy.data.objects
        if obj.name.startswith("PF_Visual_") and obj.parent is None
    ]
    if args.expected_root:
        root = bpy.data.objects.get(args.expected_root)
        if root is None:
            raise RuntimeError(f"Expected root was not found: {args.expected_root}")
    elif len(roots) == 1:
        root = roots[0]
    else:
        raise RuntimeError(
            f"Expected one PF_Visual_ root, found {[item.name for item in roots]}"
        )

    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{root.name}: no mesh descendants")
    for mesh in meshes:
        mesh.data.calc_loop_triangles()

    world_corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    bounds_min = [min(point[index] for point in world_corners) for index in range(3)]
    bounds_max = [max(point[index] for point in world_corners) for index in range(3)]
    root_name = root.name
    object_count = len(list(root.children_recursive)) + 1
    mesh_count = len(meshes)
    triangle_count = sum(len(obj.data.loop_triangles) for obj in meshes)
    material_slot_count = sum(len(obj.data.materials) for obj in meshes)

    output_dir.mkdir(parents=True, exist_ok=True)
    fbx_path = output_dir / f"{source.stem}.smoke.fbx"
    common.export_fbx(root, fbx_path)
    preview_path = None
    if args.render_preview:
        preview_path = output_dir / f"{source.stem}.smoke.png"
        render_material_preview(source, root_name, preview_path)
    report = {
        "status": "PASS",
        "source": str(source),
        "source_sha256": file_sha256(source),
        "root": root_name,
        "objects": object_count,
        "meshes": mesh_count,
        "triangles": triangle_count,
        "material_slots": material_slot_count,
        "bounds_min": bounds_min,
        "bounds_max": bounds_max,
        "fbx": str(fbx_path),
        "fbx_sha256": file_sha256(fbx_path),
        "preview": str(preview_path) if preview_path else None,
        "preview_sha256": file_sha256(preview_path) if preview_path else None,
        "authoring_environment": blender_compat.provenance(),
    }
    report_path = output_dir / f"{source.stem}.smoke.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
