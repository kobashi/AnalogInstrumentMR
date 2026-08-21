"""Fixed-condition renders of atlas variants for one model scale class.

Codex alignment 28.1-3 and 35.2: the variants have to be shown with camera,
lighting, object transform and material tuning held fixed, and every number a
reviewer needs has to come out of the run itself. An index that was hand-edited
after generation is not a handoff artifact - re-running the script would erase
it - so grain, tile floor, UV density, control identity and the contact sheet
mapping are all produced here (alignment 37.2).

The renders themselves are not byte-reproducible: EEVEE varies by up to 1/255
between identical runs. Compare parameters and the index contract, not image
bytes.

Read-only with respect to production.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_atlas_variant_review.py -- \
      --project-root "$PWD" --scale-class Medium
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_uv_atlas_pass as uv_pass
import v6_theme_materials


THEME = "KineticSafety"
VIEW = (30.0, 18.0)
CONTACT_GAP = 16
TILE_FLOOR_PIXELS = 24
MAPS = ("BaseColor", "Normal", "MetallicSmoothness", "ORM", "Emission")
SUFFIX = {"Standard": "", "Medium": "_Medium", "Large": "_Large"}

# MeterRound's light_scale, the distance the review energies were tuned at.
REFERENCE_LIGHT_SCALE = 0.170

PRESETS = {
    "Large": {
        "keys": ("MeterLarge", "WindowMeter", "WindowPanel"),
        "target": 300.0,
        "atlas_pixels": 2048,
        "variants": (
            "Large_Control_1K",
            "Large_2K_SameRepeats",
            "Large_2K_FinerRepeats",
        ),
        "control_variant": "Large_Control_1K",
        "note": (
            "Large 1K/2K comparison. Control keeps the shipped sheet size and "
            "repeats; SameRepeats doubles the sheet at the same physical grain; "
            "FinerRepeats additionally triples the repeat counts."
        ),
        "uv_note": (
            "1K at 150 tx/m and 2K at 300 tx/m give byte-identical UVs, so the "
            "1K control is rendered with the same UV as the 2K variants."
        ),
        "source_caveat": (
            "T_KineticSafety_V6_Source.png is 1254x1254 and the 2K builder "
            "upsamples it to 2048. The 2K variants carry upsampled procedural "
            "detail, not native 2K source detail."
        ),
        "memory_caveat": (
            "The 20 MiB / 80 MiB figures in large_1k_2k_comparison.json are "
            "uncompressed RGBA32 for five maps with no mipmaps. They bound the "
            "ratio, not device memory. Measure the Quest figure from the maps "
            "URP actually keeps resident, at the real ASTC block size, with "
            "mipmaps."
        ),
    },
    "Medium": {
        "keys": ("MeterMedium",),
        "target": 520.0,
        "atlas_pixels": 1024,
        "variants": ("Medium_Control", "Medium_Fine"),
        "control_variant": "Medium_Control",
        "note": (
            "Medium repeat comparison at the shipped 1K sheet and 520 tx/m. "
            "Control is the shipped Medium profile; Fine applies the repeat "
            "counts adopted for Standard. Neither 2K nor the BT tuning is in "
            "scope (alignment 35.2)."
        ),
        "uv_note": (
            "Both variants share one UV layout: only the atlas differs, so the "
            "measured density applies to each of them unchanged."
        ),
        "source_caveat": (
            "T_KineticSafety_V6_Source.png is 1254x1254 and is resized to the "
            "1024 sheet before generation. Both variants share that source, so "
            "this compares tiling frequency only; neither carries more source "
            "information than the other."
        ),
        "memory_caveat": None,
    },
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--scale-class", default="Large", choices=tuple(PRESETS))
    parser.add_argument("--key", dest="keys", action="append")
    parser.add_argument("--variant", dest="variants", action="append")
    return parser.parse_args(args)


def model_rig(root):
    """Frame from the production bounds.

    Derived once per model and reused for every variant. The shape is identical
    across variants, so this is the same framing by construction rather than by
    constants that have to be kept in step.
    """
    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    lows = [min(point[index] for point in corners) for index in range(3)]
    highs = [max(point[index] for point in corners) for index in range(3)]
    focus = (0.0, (lows[1] + highs[1]) * 0.5, (lows[2] + highs[2]) * 0.5)
    extent = max(highs[index] - lows[index] for index in (0, 2))
    light_scale = extent * 0.5
    return {
        "focus": focus,
        "radius": extent * 2.1,
        "lens": 58.0,
        "light_scale": light_scale,
        # Keep irradiance comparable to the pilot rigs: the lights sit further
        # away for a large fixture, so without this a 1.6 m panel receives about
        # 4.5% of the light a MeterRound does and every variant renders black.
        "energy_scale": (light_scale / REFERENCE_LIGHT_SCALE) ** 2,
        "extent": extent,
    }


def variant_facts(manifest, sheet_pixels, class_target, class_atlas_pixels):
    """Repeats, tile size, swatch cell width and tile-floor status."""
    target = class_target * sheet_pixels / class_atlas_pixels
    roles = {}
    for role in ("body", "metal", "gasket"):
        repeats = manifest["detail_repeats"][role]
        tile = manifest["tile_pixels"][role]
        roles[role] = {
            "repeats": repeats,
            "tile_pixels": tile,
            # The builder floors the tile at 24 px, so a role can ask for more
            # repeats than the sheet can express. Report what it actually got.
            "effective_repeats": round((sheet_pixels // 2) / tile, 1),
            "at_tile_floor": tile == TILE_FLOOR_PIXELS,
            # One swatch cell's physical width, not the full translational
            # period: `mirrored_detail_swatch` flips alternate cells, so the
            # pattern only repeats identically every 2 tiles (alignment 47.1).
            # It must come from `tile`, not from `quadrant / repeats`. The
            # builder tiles across the full `sheet_pixels // 2` quadrant, while
            # the 0.46 UV window only describes the narrower region the UVs
            # sample out of it; dividing that window by the repeats understated
            # this by ~9%, and much further at the tile floor, where the
            # requested repeats are not what the sheet delivers.
            "grain_mm": round(tile / target * 1000.0),
        }
    return {
        "sheet_pixels": sheet_pixels,
        "target_texels_per_metre": target,
        "roles": roles,
    }


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def control_identity(project_root, scale_class, texture_dir):
    """Does the control variant reproduce the shipped atlas byte for byte?"""
    active = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes"
        / THEME
        / "Textures/ThemeMaterialV6"
    )
    suffix = SUFFIX[scale_class]
    per_map = {}
    for name in MAPS:
        filename = f"T_{THEME}_V6_Atlas{suffix}_{name}.png"
        shipped, candidate = active / filename, texture_dir / filename
        per_map[name] = (
            shipped.is_file()
            and candidate.is_file()
            and file_hash(shipped) == file_hash(candidate)
        )
    return {
        "all_maps_identical": all(per_map.values()),
        "per_map": per_map,
    }


def compose_contact_sheet(images, output_path):
    tiles = [review.load_rgba(path) for path in images]
    height = max(tile.shape[0] for tile in tiles)
    width = sum(tile.shape[1] for tile in tiles) + CONTACT_GAP * (len(tiles) - 1)
    canvas = np.zeros((height, width, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    cursor = 0
    for tile in tiles:
        canvas[: tile.shape[0], cursor : cursor + tile.shape[1]] = tile
        cursor += tile.shape[1] + CONTACT_GAP
    output_path.parent.mkdir(parents=True, exist_ok=True)
    review.save_rgba(canvas, output_path)


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    scale_class = args.scale_class
    preset = PRESETS[scale_class]
    target = preset["target"]
    atlas_pixels = preset["atlas_pixels"]
    variants = tuple(args.variants or preset["variants"])
    keys = tuple(args.keys or preset["keys"])

    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME
    texture_root = candidate_dir / "textures"
    review_dir = candidate_dir / "review" / scale_class.lower()
    sheet_dir = candidate_dir / "contact_sheets"

    index = {}
    models = {}
    variant_report = {}
    contact_sheets = {}

    for key in keys:
        source = (
            project_root
            / "ArtSource/Blender/ThemeHardSurfaceV6"
            / THEME
            / f"BL_{key}_{THEME}_V6_Retopo.blend"
        )
        rendered = []
        for variant in variants:
            bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
            review.configure_scene()
            root = bpy.data.objects[f"PF_Visual_{key}_{THEME}_V6"]
            materials = v6_theme_materials.apply(project_root, THEME, scale_class)
            v6_theme_materials.assign_special_roles(root, materials)
            entries = uv_pass.apply(root, scale_class, target, atlas_pixels)

            if key not in models:
                density = uv_pass.summarise(root, atlas_pixels)
                models[key] = {
                    "target_texels_per_metre": target,
                    "atlas_pixels": atlas_pixels,
                    "density_median": density["median"],
                    "density_range": [density["lowest"], density["highest"]],
                    "spread_ratio": density["spread_ratio"],
                    "clamped_parts": sum(
                        1 for entry in entries if entry["clamped"]
                    ),
                    "note": (
                        "One UV layout serves every variant, so this applies to "
                        "each of them unchanged."
                    ),
                }

            texture_dir = texture_root / variant / THEME
            opaque, emissive = uv_pass.build_runtime_materials(
                project_root, THEME, scale_class, texture_dir
            )
            uv_pass.assign_runtime_materials(root, opaque, emissive)
            uv_pass.set_emission_enabled(True, THEME)

            rig = model_rig(root)
            path = (
                review_dir
                / f"Preview_{key}_{THEME}_{scale_class}_{variant}.png"
            )
            review.shot(rig, rig["focus"], rig["radius"], VIEW, rig["lens"], path)
            rendered.append(path)

            manifest = json.loads(
                (
                    texture_dir
                    / f"T_{THEME}_V6_Atlas{SUFFIX[scale_class]}.manifest.json"
                ).read_text()
            )
            if variant not in variant_report:
                facts = variant_facts(
                    manifest, manifest["size"], target, atlas_pixels
                )
                facts["texture_dir"] = str(texture_dir.relative_to(project_root))
                if variant == preset["control_variant"]:
                    facts["reproduces_active_atlas"] = control_identity(
                        project_root, scale_class, texture_dir
                    )
                variant_report[variant] = facts
            index[path.name] = {"model": key, "variant": variant}
            print(f"[Opus5AtlasReview] {path.name}")

        sheet = sheet_dir / f"ContactSheet_{key}_{THEME}_{scale_class}Atlas.png"
        compose_contact_sheet(rendered, sheet)
        contact_sheets[key] = {
            "path": str(sheet.relative_to(project_root)),
            "order_left_to_right": list(variants),
        }
        print(f"[Opus5AtlasReview] {sheet.name}")

    report = {
        "scale_class": scale_class,
        "note": preset["note"],
        "reproducibility": (
            "EEVEE renders are not byte-reproducible; identical runs differ by "
            "up to 1/255. Verify this handoff from the parameters and the index "
            "contract, not from image bytes."
        ),
        "view_azimuth_elevation": list(VIEW),
        "fixed_across_variants": [
            "shape",
            "UV layout",
            "camera position, lens and framing",
            "light positions, sizes and energies",
            "object transform",
            "material setup and emission strength",
        ],
        "uv": {
            "target_texels_per_metre": target,
            "atlas_pixels": atlas_pixels,
            "note": preset["uv_note"],
        },
        "source_resolution_caveat": preset["source_caveat"],
        "control_variant": preset["control_variant"],
        "variants": variant_report,
        "models": models,
        "images": index,
        "contact_sheets": contact_sheets,
        "authoring_environment": blender_compat.provenance(),
    }
    if preset["memory_caveat"]:
        report["memory_caveat"] = preset["memory_caveat"]

    report_path = (
        candidate_dir / f"reports/{scale_class.lower()}_atlas_review_index.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"[Opus5AtlasReview] {len(index)} images, "
        f"{len(contact_sheets)} contact sheets, index at {report_path}"
    )


if __name__ == "__main__":
    main()
