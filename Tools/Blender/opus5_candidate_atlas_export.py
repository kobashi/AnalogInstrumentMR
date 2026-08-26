"""Candidate FBX carrying the constant-density UV, per model scale class.

Codex alignment 26/28/39: an atlas comparison needs a candidate FBX because the
active FBX carries the old production UV and cannot reproduce the density the
Blender review ran at. The shape is production's - these models were not brushed
up - so the only thing that is candidate about the export is the UV.

One FBX serves every atlas variant of its class: the atlas differs, the UV does
not. For Large that also holds across sheet sizes, because `opus5_uv_atlas_pass`
only ever sees the ratio `target / atlas_pixels` (verified in
`reports/large_uv_hash_identity.json`).

The production exporter is deliberately left alone (alignment 5.3 keeps the UV
pass a reference implementation), so this reuses its helpers rather than adding
a mode to it.

Nothing under `Assets/` or `ArtSource/Blender/ThemeHardSurfaceV6/` is written.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_candidate_atlas_export.py -- \
      --project-root "$PWD" --scale-class Medium
"""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import export_v6_replacement_candidates as export
import generate_orbital_analog_meter as common
import opus5_uv_atlas_pass as uv_pass
import v6_theme_materials


THEME = "KineticSafety"

PRESETS = {
    "Large": {
        "keys": ("MeterLarge", "WindowMeter", "WindowPanel"),
        "target": 300.0,
        "atlas_pixels": 2048,
    },
    "Medium": {
        "keys": ("MeterMedium",),
        "target": 520.0,
        "atlas_pixels": 1024,
    },
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--scale-class", default="Large", choices=tuple(PRESETS))
    parser.add_argument("--key", dest="keys", action="append")
    return parser.parse_args(args)


def uv_fingerprint(meshes):
    """Same recipe the round-trip verifier uses, so the two are comparable."""
    digest = hashlib.sha256()
    for obj in sorted(meshes, key=lambda item: item.name):
        digest.update(obj.name.encode("utf-8"))
        uv_layer = obj.data.uv_layers.active
        if uv_layer is None:
            continue
        for item in uv_layer.data:
            digest.update(struct.pack("<2f", item.uv[0], item.uv[1]))
    return digest.hexdigest()


def export_one(project_root, key, scale_class, target, atlas_pixels, output_dir):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / THEME
        / f"BL_{key}_{THEME}_V6_Retopo.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(source)

    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{key}_{THEME}_V6"]

    materials = v6_theme_materials.apply(project_root, THEME, scale_class)
    v6_theme_materials.assign_special_roles(root, materials)

    meshes_before = [
        obj for obj in root.children_recursive if obj.type == "MESH"
    ]
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes_before
        for corner in obj.bound_box
    ]
    bounds = {
        "min": [round(min(p[i] for p in corners), 6) for i in range(3)],
        "max": [round(max(p[i] for p in corners), 6) for i in range(3)],
    }

    entries = uv_pass.apply(root, scale_class, target, atlas_pixels)
    density = uv_pass.summarise(root, atlas_pixels)

    opaque, emissive = export.placeholder_materials(THEME)
    uv_pass.assign_runtime_materials(root, opaque, emissive)
    for obj in list(root.children_recursive):
        if obj.type == "MESH":
            export.triangulate(obj)
    combined = export.combine_runtime_renderers(root, key)

    root["replacement_stage"] = (
        f"Opus 5 {scale_class} atlas comparison candidate"
    )
    root["candidate_shape_source"] = str(source.relative_to(project_root))
    root["candidate_shape_is_production"] = True
    root["candidate_uv_pass"] = "opus5_uv_atlas_pass constant density"
    root["candidate_atlas_pixels"] = atlas_pixels
    root["candidate_target_texels_per_metre"] = target
    root["runtime_material_contract"] = "opaque + emissive"
    root["atlas_uv_contract"] = "body TL, metal TR, gasket BL, readout BR"

    output_dir.mkdir(parents=True, exist_ok=True)
    fbx_path = output_dir / f"SM_{key}_{THEME}_V6_Opus5_{scale_class}UV.fbx"
    common.export_fbx(root, fbx_path, use_custom_props=True)

    triangles = sum(len(mesh.data.polygons) for mesh in combined)
    clamped = [entry for entry in entries if entry["clamped"]]
    return {
        "object": key,
        "theme": THEME,
        "scale_class": scale_class,
        "shape_source": str(source.relative_to(project_root)),
        "shape_is_production_unmodified": True,
        "candidate_difference": "UV only (constant-density atlas UV pass)",
        "atlas_pixels": atlas_pixels,
        "target_texels_per_metre": target,
        "uv_is_shared_across_atlas_variants": True,
        "fbx": str(fbx_path.relative_to(project_root)),
        "triangles": triangles,
        "renderers": len(combined),
        "mesh_names": sorted(mesh.name for mesh in combined),
        "uv_hash": uv_fingerprint(combined),
        "material_slots": ["opaque", "emissive"],
        "bounds": bounds,
        "density_median": density["median"],
        "density_range": [density["lowest"], density["highest"]],
        "spread_ratio": density["spread_ratio"],
        "clamped_parts": len(clamped),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    scale_class = args.scale_class
    preset = PRESETS[scale_class]
    target = preset["target"]
    atlas_pixels = preset["atlas_pixels"]
    output_dir = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / f"staging/{scale_class.lower()}_fbx"
    )
    models = {}
    for key in args.keys or preset["keys"]:
        models[key] = export_one(
            project_root, key, scale_class, target, atlas_pixels, output_dir
        )
        entry = models[key]
        print(
            f"[Opus5CandidateFBX] {key}: {entry['triangles']} tris, "
            f"{entry['renderers']} renderers, "
            f"density {entry['density_range'][0]}..{entry['density_range'][1]} tx/m, "
            f"{entry['clamped_parts']} clamped"
        )

    report = {
        "note": (
            "Candidate FBX for the atlas comparison of one scale class. The "
            "shape is production's, unmodified; only the UV is candidate. One "
            "FBX serves every atlas variant of the class because the atlas "
            "differs and the UV does not."
        ),
        "scale_class": scale_class,
        "atlas_pixels": atlas_pixels,
        "target_texels_per_metre": target,
        "models": models,
        "authoring_environment": blender_compat.provenance(),
    }
    report_path = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / f"reports/{scale_class.lower()}_candidate_fbx.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
