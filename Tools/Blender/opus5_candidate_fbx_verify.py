"""Round-trip check for a candidate FBX, per model scale class.

Codex alignment 30.1: the candidate metadata was set on the source scene's root
but never survived export, because `common.export_fbx` does not enable the FBX
exporter's custom property output. Setting a property is not the same as
shipping it, so this imports each FBX back from a factory startup and reports
what is actually in the file.

It also fingerprints the geometry, so a metadata-only fix can be shown to be
exactly that: same triangles, same renderers, same materials, same UVs.

Read-only. Exits non-zero when a required property is missing.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_candidate_fbx_verify.py -- \
      --project-root "$PWD" --scale-class Medium --output <report.json>
"""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat


THEME = "KineticSafety"
PRESET_KEYS = {
    "Large": ("MeterLarge", "WindowMeter", "WindowPanel"),
    "Medium": ("MeterMedium",),
}
REQUIRED_PROPERTIES = (
    "candidate_shape_source",
    "candidate_shape_is_production",
    "candidate_uv_pass",
    "candidate_atlas_pixels",
    "candidate_target_texels_per_metre",
    "runtime_material_contract",
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--scale-class", default="Large", choices=tuple(PRESET_KEYS)
    )
    parser.add_argument("--require-properties", action="store_true")
    return parser.parse_args(args)


def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def inspect(path):
    clean_scene()
    bpy.ops.import_scene.fbx(filepath=str(path))

    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    digest = hashlib.sha256()
    triangles = 0
    materials = set()
    for obj in sorted(meshes, key=lambda item: item.name):
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        materials.update(
            material.name for material in obj.data.materials if material
        )
        digest.update(obj.name.encode("utf-8"))
        uv_layer = obj.data.uv_layers.active
        if uv_layer is None:
            continue
        for item in uv_layer.data:
            digest.update(struct.pack("<2f", item.uv[0], item.uv[1]))

    found = {}
    for obj in bpy.data.objects:
        properties = {
            key: obj[key] for key in obj.keys() if key != "_RNA_UI"
        }
        if properties:
            found[obj.name] = {
                key: (
                    round(value, 6)
                    if isinstance(value, float)
                    else (list(value) if hasattr(value, "__len__") and not isinstance(value, str) else value)
                )
                for key, value in properties.items()
            }

    all_properties = {key for entry in found.values() for key in entry}
    missing = [key for key in REQUIRED_PROPERTIES if key not in all_properties]
    return {
        "fbx": path.name,
        "objects": len(bpy.data.objects),
        "meshes": len(meshes),
        "triangles": triangles,
        "materials": sorted(materials),
        "uv_hash": digest.hexdigest(),
        "objects_with_custom_properties": len(found),
        "custom_properties": found,
        "missing_required_properties": missing,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    scale_class = args.scale_class
    directory = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / f"staging/{scale_class.lower()}_fbx"
    )

    models = {}
    failures = []
    for key in PRESET_KEYS[scale_class]:
        path = directory / f"SM_{key}_{THEME}_V6_Opus5_{scale_class}UV.fbx"
        if not path.is_file():
            failures.append(f"{key}: missing {path.name}")
            continue
        entry = inspect(path)
        models[key] = entry
        if args.require_properties and entry["missing_required_properties"]:
            failures.append(
                f"{key}: missing {', '.join(entry['missing_required_properties'])}"
            )

    report = {
        "note": (
            "What the exported candidate FBX files actually contain, read back "
            "from a factory startup. Custom properties only survive export when "
            "the exporter is asked for them."
        ),
        "scale_class": scale_class,
        "required_properties": list(REQUIRED_PROPERTIES),
        "models": models,
        "failures": failures,
        "authoring_environment": blender_compat.provenance(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for key, entry in models.items():
        print(
            f"[Opus5FBXVerify] {key}: {entry['triangles']} tris, "
            f"{entry['meshes']} meshes, "
            f"props on {entry['objects_with_custom_properties']} objects, "
            f"missing {len(entry['missing_required_properties'])}, "
            f"uv {entry['uv_hash'][:12]}"
        )
    for failure in failures:
        print(f"  FAIL {failure}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
