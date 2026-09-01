"""Build isolated 1K TrendMonitor housing PBR texture candidates.

The image-model swatches in ArtSource are design references, not shippable
textures.  This script removes their large-scale lighting, repeats only their
micro detail with mirrored boundaries, applies the approved theme palette, and
writes deterministic candidate maps outside production texture directories.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_v6_material_atlases as v6  # noqa: E402


SIZE = 1024
CANDIDATE_ID = "TrendMonitor_Texture_T1"
THEMES = {
    "OrbitalAnalog": {
        "base": (0.090, 0.120, 0.140),
        "metallic": 0.42,
        "smoothness": 0.48,
        "normal_strength": 0.25,
        "period_pixels": 128,
    },
    "ForgeBrass": {
        "base": (0.200, 0.160, 0.120),
        "metallic": 0.56,
        "smoothness": 0.34,
        "normal_strength": 0.30,
        "period_pixels": 128,
    },
    "KineticSafety": {
        "base": (0.110, 0.130, 0.140),
        "metallic": 0.28,
        "smoothness": 0.30,
        "normal_strength": 0.28,
        "period_pixels": 128,
    },
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def edge_error(array):
    horizontal = np.abs(array[:, 0].astype(np.int16) -
                        array[:, -1].astype(np.int16)).max()
    vertical = np.abs(array[0].astype(np.int16) -
                      array[-1].astype(np.int16)).max()
    return int(max(horizontal, vertical))


def periodic_detail(image):
    """Build a 1024 square detail field with a 128 px mirrored period."""
    patch = np.asarray(
        image.resize((65, 65), Image.Resampling.LANCZOS),
        dtype=np.uint8,
    )
    horizontal = np.concatenate((patch, patch[:, -2:0:-1]), axis=1)
    tile = np.concatenate((horizontal, horizontal[-2:0:-1]), axis=0)
    return Image.fromarray(np.tile(tile, (8, 8, 1)))


def wrap_box_blur(values, radius):
    result = np.zeros_like(values, dtype=np.float32)
    count = 0
    for y in range(-radius, radius + 1):
        for x in range(-radius, radius + 1):
            result += np.roll(np.roll(values, y, axis=0), x, axis=1)
            count += 1
    return result / count


def periodic_normal(image, strength):
    gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    height = np.clip((gray - wrap_box_blur(gray, 2)) * strength,
                     -0.16, 0.16)
    dx = (np.roll(height, -1, axis=1) -
          np.roll(height, 1, axis=1)) * 0.5
    dy = (np.roll(height, -1, axis=0) -
          np.roll(height, 1, axis=0)) * 0.5
    nx = -dx * 6.0
    ny = dy * 6.0
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack((
        nx / length * 0.5 + 0.5,
        ny / length * 0.5 + 0.5,
        nz / length * 0.5 + 0.5,
    ), axis=-1)


def build_theme(project_root, theme, settings):
    reference = (
        project_root / "ArtSource/Textures/TrendMonitorThemeT1/References" /
        f"REF_TrendMonitor_{theme}_Surface.png"
    )
    output = (
        project_root /
        "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/CandidateStaging" /
        CANDIDATE_ID / "Textures" / theme
    )
    output.mkdir(parents=True, exist_ok=True)

    source = Image.open(reference).convert("RGB")
    side = min(source.size)
    left = (source.width - side) // 2
    top = (source.height - side) // 2
    source = source.crop((left, top, left + side, top + side)).resize(
        (SIZE, SIZE), Image.Resampling.LANCZOS)
    detailed = periodic_detail(source)
    base = v6.normalize_swatch(
        detailed,
        settings["base"],
        detail_gain=0.055,
        radius=18.0,
        gain_scale=0.72,
    )
    normal = periodic_normal(detailed, settings["normal_strength"])

    luminance = np.asarray(
        detailed.convert("L").filter(ImageFilter.GaussianBlur(radius=1.8)),
        dtype=np.float32,
    ) / 255.0
    variation = np.clip(luminance - float(luminance.mean()), -0.10, 0.10)
    smoothness = np.clip(
        settings["smoothness"] - variation * 0.16,
        0.08,
        0.78,
    )
    metallic_smoothness = np.zeros((SIZE, SIZE, 4), dtype=np.float32)
    metallic_smoothness[:, :, 0] = settings["metallic"]
    metallic_smoothness[:, :, 3] = smoothness
    orm = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    orm[:, :, 0] = 1.0
    orm[:, :, 1] = 1.0 - smoothness
    orm[:, :, 2] = settings["metallic"]

    prefix = f"T_{theme}_V6_TrendMonitor_T1"
    paths = {
        "base_color": output / f"{prefix}_BaseColor.png",
        "normal": output / f"{prefix}_Normal.png",
        "metallic_smoothness":
            output / f"{prefix}_MetallicSmoothness.png",
        "orm": output / f"{prefix}_ORM.png",
    }
    v6.as_image(base).save(paths["base_color"], optimize=True)
    v6.as_image(normal).save(paths["normal"], optimize=True)
    v6.as_image(metallic_smoothness, "RGBA").save(
        paths["metallic_smoothness"], optimize=True)
    v6.as_image(orm).save(paths["orm"], optimize=True)

    map_rows = {
        role: {
            "path": str(path.relative_to(project_root)),
            "sha256": digest(path),
            "edge_error_8bit": edge_error(np.asarray(Image.open(path))),
        }
        for role, path in paths.items()
    }
    maximum_edge_error = max(
        row["edge_error_8bit"] for row in map_rows.values())
    luminance = (
        base[:, :, 0] * 0.2126 +
        base[:, :, 1] * 0.7152 +
        base[:, :, 2] * 0.0722
    )
    normal_xy = np.sqrt(
        np.square((normal[:, :, 0] - 0.5) * 2.0) +
        np.square((normal[:, :, 1] - 0.5) * 2.0)
    )
    return {
        "theme": theme,
        "reference": str(reference.relative_to(project_root)),
        "reference_sha256": digest(reference),
        "size": SIZE,
        "housing_only": True,
        "display_surface_textured": False,
        "readout_texture_changed": False,
        "settings": settings,
        "statistics": {
            "base_luminance_min": round(float(luminance.min()), 6),
            "base_luminance_mean": round(float(luminance.mean()), 6),
            "base_luminance_max": round(float(luminance.max()), 6),
            "normal_xy_mean": round(float(normal_xy.mean()), 6),
            "normal_xy_max": round(float(normal_xy.max()), 6),
            "maximum_edge_error_8bit": maximum_edge_error,
            "edge_error_limit_8bit": 10,
            "map_gate_pass": maximum_edge_error <= 10,
        },
        "maps": map_rows,
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    rows = [
        build_theme(project_root, theme, settings)
        for theme, settings in THEMES.items()
    ]
    report = {
        "schema": 1,
        "candidate_id": CANDIDATE_ID,
        "generator": str(Path(__file__).resolve().relative_to(project_root)),
        "image_model_references_are_non_shipping": True,
        "production_assets_modified": False,
        "themes": rows,
    }
    report_path = (
        project_root /
        "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/CandidateStaging" /
        CANDIDATE_ID / "trend_monitor_texture_t1.json"
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(report_path)


if __name__ == "__main__":
    main()
