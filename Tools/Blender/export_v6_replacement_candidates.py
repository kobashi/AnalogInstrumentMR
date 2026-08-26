"""Export production-staging FBX files from the V6 material review blends.

The review blends use four semantic material roles.  Before export this script
unwraps every mesh into the matching quadrant of the shared 2x2 theme atlas,
then collapses the material slots to the two-material runtime contract:
opaque atlas and emissive atlas.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_orbital_analog_meter as common


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

QUADRANTS = {
    "body": (0.02, 0.52),
    "metal": (0.52, 0.52),
    "gasket": (0.02, 0.02),
    "readout": (0.52, 0.02),
}
QUADRANT_SCALE = 0.46

MOVABLE_GROUPS = {
    "MeterRound": (("needle_pivot", "needle"),),
    "MeterMedium": (("needle_pivot", "needle"),),
    "MeterLarge": (("needle_pivot", "needle"),),
    "Lever": (("handle_pivot", "handle"),),
    "Toggle": (("switch_pivot", "switch"),),
    "Rotary": (("knob_pivot", "knob"),),
    "Button": (("button_travel", "button"),),
    "Lamp": (("indicator", "indicator_lens"),),
    "Throttle": (("throttle_pivot", "throttle_handle"),),
    "PowerSlider": (("slider_travel", "slider_handle"),),
    "StatusIndicator": (
        ("status_safe", "status_safe"),
        ("status_warn", "status_warn"),
        ("status_danger", "status_danger"),
    ),
    "WindowMeter": (("needle_pivot", "needle"),),
    "WindowPanel": (("vane_pivot", "vane"),),
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", choices=THEMES)
    parser.add_argument("--object", dest="object_key", choices=OBJECTS)
    parser.add_argument(
        "--source-dir",
        default=None,
        help=(
            "Read the Material blend from here instead of "
            "ArtSource/Blender/ThemeHardSurfaceV6/<Theme>."
        ),
    )
    parser.add_argument(
        "--blend-output-dir",
        default=None,
        help=(
            "Write the ProductionReady blend here instead of over the "
            "production source. Use this for every candidate run."
        ),
    )
    parser.add_argument(
        "--fbx-output-dir",
        default=None,
        help=(
            "Write the FBX and its report here instead of "
            "Assets/.../RefinedCandidates/<Theme>/ThemeHardSurfaceV6Material."
        ),
    )
    parser.add_argument(
        "--name-suffix",
        default="",
        help=(
            "Appended to the ProductionReady blend and FBX stems, so a "
            "candidate never collides with a production filename."
        ),
    )
    return parser.parse_args(args)


def material_role(material):
    if material is None:
        return "body"
    explicit = material.get("v6_material_role")
    if explicit in QUADRANTS:
        return explicit
    name = material.name.lower()
    if "readout" in name or "emissive" in name:
        return "readout"
    if "gasket" in name:
        return "gasket"
    if "metal" in name:
        return "metal"
    return "body"


def smart_unwrap(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(66.0),
        island_margin=0.02,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=True,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def atlas_remap_and_collapse(obj, opaque, emissive):
    original_materials = list(obj.data.materials)
    roles = [
        material_role(
            original_materials[polygon.material_index]
            if polygon.material_index < len(original_materials)
            else None
        )
        for polygon in obj.data.polygons
    ]
    smart_unwrap(obj)
    uv_layer = obj.data.uv_layers.active
    if uv_layer is None:
        raise RuntimeError(f"{obj.name}: smart unwrap did not create UVs")

    for polygon, role in zip(obj.data.polygons, roles):
        offset_u, offset_v = QUADRANTS[role]
        for loop_index in polygon.loop_indices:
            uv = uv_layer.data[loop_index].uv
            uv.x = offset_u + max(0.0, min(1.0, uv.x)) * QUADRANT_SCALE
            uv.y = offset_v + max(0.0, min(1.0, uv.y)) * QUADRANT_SCALE

    uses_emission = any(role == "readout" for role in roles)
    obj.data.materials.clear()
    obj.data.materials.append(opaque)
    if uses_emission:
        obj.data.materials.append(emissive)
    for polygon, role in zip(obj.data.polygons, roles):
        polygon.material_index = 1 if role == "readout" else 0


def triangulate(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def is_descendant_of(obj, ancestor):
    current = obj
    while current is not None:
        if current == ancestor:
            return True
        current = current.parent
    return False


def consolidate_material_slots(obj):
    original = list(obj.data.materials)
    unique = []
    old_to_new = {}
    for index, material in enumerate(original):
        try:
            new_index = unique.index(material)
        except ValueError:
            new_index = len(unique)
            unique.append(material)
        old_to_new[index] = new_index
    for polygon in obj.data.polygons:
        polygon.material_index = old_to_new[polygon.material_index]
    obj.data.materials.clear()
    for material in unique:
        obj.data.materials.append(material)


def restore_runtime_material_indices(obj):
    materials = list(obj.data.materials)
    opaque = next(
        (
            material
            for material in materials
            if material is not None
            and "Emissive" not in material.name
        ),
        None,
    )
    emissive = next(
        (
            material
            for material in materials
            if material is not None
            and "Emissive" in material.name
        ),
        None,
    )
    if opaque is None:
        raise RuntimeError(f"{obj.name}: opaque runtime material is missing")
    uv_layer = obj.data.uv_layers.active
    if uv_layer is None:
        raise RuntimeError(f"{obj.name}: atlas UV layer is missing")

    emission_faces = []
    for polygon in obj.data.polygons:
        coordinates = [
            uv_layer.data[loop_index].uv
            for loop_index in polygon.loop_indices
        ]
        center_u = sum(uv.x for uv in coordinates) / len(coordinates)
        center_v = sum(uv.y for uv in coordinates) / len(coordinates)
        emission_faces.append(center_u >= 0.5 and center_v < 0.5)

    obj.data.materials.clear()
    obj.data.materials.append(opaque)
    if any(emission_faces):
        if emissive is None:
            raise RuntimeError(
                f"{obj.name}: emissive atlas faces lost their material"
            )
        obj.data.materials.append(emissive)
    for polygon, is_emissive in zip(
        obj.data.polygons,
        emission_faces,
    ):
        polygon.material_index = 1 if is_emissive else 0


def join_meshes(objects, name, parent):
    if not objects:
        raise RuntimeError(f"{name}: no meshes to combine")
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.matrix_world = world
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = name
    joined.data.name = f"ME_{name}"
    world = joined.matrix_world.copy()
    joined.parent = parent
    joined.matrix_world = world
    bpy.ops.object.select_all(action="DESELECT")
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    bpy.ops.object.transform_apply(
        location=False,
        rotation=True,
        scale=True,
    )
    consolidate_material_slots(joined)
    restore_runtime_material_indices(joined)
    return joined


def combine_runtime_renderers(root, key):
    source_meshes = [
        child for child in root.children_recursive if child.type == "MESH"
    ]
    claimed_names = set()
    group_specs = []
    for anchor_name, result_name in MOVABLE_GROUPS[key]:
        anchor = bpy.data.objects.get(anchor_name)
        if anchor is None or not is_descendant_of(anchor, root):
            raise RuntimeError(f"{key}: missing movable anchor {anchor_name}")
        group = [
            mesh
            for mesh in source_meshes
            if is_descendant_of(mesh, anchor)
        ]
        claimed_names.update(mesh.name for mesh in group)
        parent = anchor if anchor.type != "MESH" else anchor.parent
        group_specs.append((group, result_name, parent))

    static_meshes = [
        mesh for mesh in source_meshes if mesh.name not in claimed_names
    ]
    combined = []
    for group, result_name, parent in group_specs:
        combined.append(join_meshes(group, result_name, parent))
    if static_meshes:
        combined.insert(
            0,
            join_meshes(static_meshes, f"{key}_body", root),
        )
    return combined


def placeholder_materials(theme):
    opaque = bpy.data.materials.get(f"MAT_{theme}_V6_Atlas")
    if opaque is None:
        opaque = bpy.data.materials.new(f"MAT_{theme}_V6_Atlas")
    emissive = bpy.data.materials.get(f"MAT_{theme}_V6_Emissive")
    if emissive is None:
        emissive = bpy.data.materials.new(f"MAT_{theme}_V6_Emissive")
    return opaque, emissive


def export_one(
    project_root,
    theme,
    key,
    source_dir=None,
    blend_output_dir=None,
    fbx_output_dir=None,
    name_suffix="",
):
    source_dir = (
        Path(source_dir)
        if source_dir is not None
        else project_root / "ArtSource/Blender/ThemeHardSurfaceV6" / theme
    )
    source_path = source_dir / f"BL_{key}_{theme}_V6_Material.blend"
    bpy.ops.wm.open_mainfile(filepath=str(source_path))
    root = bpy.data.objects.get(f"PF_Visual_{key}_{theme}_V6")
    if root is None:
        raise RuntimeError(f"{theme}/{key}: V6 visual root was not found")

    opaque, emissive = placeholder_materials(theme)
    meshes = [
        child for child in root.children_recursive if child.type == "MESH"
    ]
    for mesh in meshes:
        atlas_remap_and_collapse(mesh, opaque, emissive)
        triangulate(mesh)
    meshes = combine_runtime_renderers(root, key)

    root["replacement_stage"] = "V6 production candidate"
    root["runtime_material_contract"] = "opaque + emissive"
    root["atlas_uv_contract"] = "body TL, metal TR, gasket BL, readout BR"

    blend_dir = (
        Path(blend_output_dir) if blend_output_dir is not None else source_dir
    )
    blend_dir.mkdir(parents=True, exist_ok=True)
    prepared_blend = (
        blend_dir
        / f"BL_{key}_{theme}_V6{name_suffix}_ProductionReady.blend"
    )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(prepared_blend), compress=True)
    prepared_blend.with_suffix(".blend1").unlink(missing_ok=True)

    output_dir = (
        Path(fbx_output_dir)
        if fbx_output_dir is not None
        else project_root
        / "Assets/MatsuMotoMeterAR/Content/RefinedCandidates"
        / theme
        / "ThemeHardSurfaceV6Material"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    fbx_path = output_dir / f"SM_{key}_{theme}_V6{name_suffix}_Material.fbx"
    common.export_fbx(root, fbx_path)

    def describe(path):
        try:
            return str(Path(path).relative_to(project_root))
        except ValueError:
            return str(path)

    triangles = sum(
        len(mesh.data.polygons) for mesh in meshes
    )
    report = {
        "theme": theme,
        "object": key,
        "source": describe(source_path),
        "prepared_blend": describe(prepared_blend),
        "fbx": describe(fbx_path),
        "triangles": triangles,
        "renderers": len(meshes),
        "material_slots": ["opaque", "emissive"],
        "atlas_quadrants": QUADRANTS,
        "production_integrated": False,
        "authoring_environment": blender_compat.provenance(),
    }
    report_path = output_dir / f"SM_{key}_{theme}_V6{name_suffix}_Material.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report))


def main():
    blender_compat.require_v6_pipeline()
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    themes = (args.theme,) if args.theme else THEMES
    objects = (args.object_key,) if args.object_key else OBJECTS
    for theme in themes:
        for key in objects:
            export_one(
                project_root,
                theme,
                key,
                args.source_dir,
                args.blend_output_dir,
                args.fbx_output_dir,
                args.name_suffix,
            )


if __name__ == "__main__":
    main()
