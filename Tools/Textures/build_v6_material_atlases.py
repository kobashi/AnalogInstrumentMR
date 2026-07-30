"""Build Quest-friendly V6 PBR atlases from the theme texture sources."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps


THEMES = {
    "OrbitalAnalog": {
        "colors": (
            (0.52, 0.55, 0.56),
            (0.45, 0.49, 0.51),
            (0.055, 0.065, 0.070),
            (0.10, 0.68, 0.78),
        ),
        "metallic": (0.08, 0.92, 0.00, 0.04),
        "smoothness": (0.38, 0.70, 0.16, 0.62),
        "normal_strength": (1.4, 1.8, 2.4, 1.2),
    },
    "ForgeBrass": {
        "colors": (
            (0.115, 0.095, 0.070),
            (0.21, 0.16, 0.085),
            (0.075, 0.080, 0.082),
            (0.78, 0.28, 0.025),
        ),
        "metallic": (0.72, 0.94, 0.78, 0.02),
        "smoothness": (0.22, 0.56, 0.30, 0.58),
        "normal_strength": (2.8, 2.2, 1.9, 1.3),
    },
    "KineticSafety": {
        "colors": (
            (0.035, 0.070, 0.105),
            (0.075, 0.095, 0.115),
            (0.025, 0.028, 0.030),
            (0.02, 0.62, 0.76),
        ),
        "metallic": (0.24, 0.90, 0.00, 0.02),
        "smoothness": (0.30, 0.52, 0.12, 0.66),
        "normal_strength": (2.5, 1.9, 4.0, 1.1),
    },
}

QUADRANTS = (
    (0, 0, "body"),
    (1, 0, "metal"),
    (0, 1, "gasket"),
    (1, 1, "readout"),
)

DETAIL_PROFILES = {
    "Standard": {
        "suffix": "",
        "repeats": {
            "body": 3,
            "metal": 5,
            "gasket": 3,
            "readout": 1,
        },
    },
    "Medium": {
        "suffix": "_Medium",
        "repeats": {
            "body": 5,
            "metal": 8,
            "gasket": 5,
            "readout": 1,
        },
    },
    "Large": {
        "suffix": "_Large",
        "repeats": {
            "body": 8,
            "metal": 12,
            "gasket": 7,
            "readout": 1,
        },
    },
}

BASE_DETAIL_GAIN = {
    "body": 0.08,
    "metal": 0.055,
    "gasket": 0.10,
    "readout": 0.035,
}

SMOOTHNESS_DETAIL_GAIN = {
    "body": 0.10,
    "metal": 0.07,
    "gasket": 0.12,
    "readout": 0.04,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args()


def as_float(image):
    return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def as_image(array, mode="RGB"):
    values = np.clip(array * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(values, mode)


def normalize_swatch(image, target, detail_gain):
    source = as_float(image)
    blurred = as_float(image.filter(ImageFilter.GaussianBlur(radius=18)))
    high_frequency = source - blurred
    luminance = (
        source[:, :, 0] * 0.2126
        + source[:, :, 1] * 0.7152
        + source[:, :, 2] * 0.0722
    )
    luminance -= float(luminance.mean())
    modulation = np.clip(luminance * 0.20, -0.075, 0.075)
    target_color = np.asarray(target, dtype=np.float32)[None, None, :]
    result = target_color * (1.0 + modulation[:, :, None])
    result += high_frequency * detail_gain
    return np.clip(result, 0.0, 1.0)


def mirrored_detail_swatch(image, repeats):
    if repeats <= 1:
        return image.copy()
    tile_width = max(24, image.width // repeats)
    tile_height = max(24, image.height // repeats)
    tile = image.resize(
        (tile_width, tile_height),
        Image.Resampling.LANCZOS,
    )
    result = Image.new("RGB", image.size)
    for row, y in enumerate(range(0, image.height, tile_height)):
        for column, x in enumerate(range(0, image.width, tile_width)):
            patch = tile
            if column % 2:
                patch = ImageOps.mirror(patch)
            if row % 2:
                patch = ImageOps.flip(patch)
            result.paste(patch, (x, y))
    return result


def normal_from_swatch(image, strength):
    gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    blurred = np.asarray(
        image.convert("L").filter(ImageFilter.GaussianBlur(radius=2.2)),
        dtype=np.float32,
    ) / 255.0
    height = np.clip((gray - blurred) * strength, -0.20, 0.20)
    dy, dx = np.gradient(height)
    nx = -dx * 7.0
    ny = dy * 7.0
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack(
        (
            nx / length * 0.5 + 0.5,
            ny / length * 0.5 + 0.5,
            nz / length * 0.5 + 0.5,
        ),
        axis=-1,
    )


def build_theme_variant(
    project_root,
    theme,
    config,
    size,
    source,
    profile_name,
    profile,
):
    source_path = (
        project_root
        / "ArtSource/Textures/ThemeMaterialV6"
        / theme
        / f"T_{theme}_V6_Source.png"
    )
    output_dir = (
        project_root
        / "Assets/MatsuMotoMeterAR/Content/Themes"
        / theme
        / "Textures/ThemeMaterialV6"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    half = size // 2
    base = np.zeros((size, size, 3), dtype=np.float32)
    normal = np.zeros((size, size, 3), dtype=np.float32)
    metallic_smoothness = np.zeros((size, size, 4), dtype=np.float32)
    orm = np.zeros((size, size, 3), dtype=np.float32)
    emission = np.zeros((size, size, 3), dtype=np.float32)

    for index, (column, row, role) in enumerate(QUADRANTS):
        x0, y0 = column * half, row * half
        x1, y1 = x0 + half, y0 + half
        crop = source.crop((x0, y0, x1, y1))
        detailed = mirrored_detail_swatch(
            crop,
            profile["repeats"][role],
        )
        normalized = normalize_swatch(
            detailed,
            config["colors"][index],
            BASE_DETAIL_GAIN[role],
        )
        base[y0:y1, x0:x1] = normalized
        normal[y0:y1, x0:x1] = normal_from_swatch(
            detailed,
            config["normal_strength"][index],
        )
        detail = np.asarray(
            detailed.convert("L").filter(
                ImageFilter.GaussianBlur(radius=1.2)
            ),
            dtype=np.float32,
        ) / 255.0
        detail = np.clip(detail - float(detail.mean()), -0.12, 0.12)
        metallic = config["metallic"][index]
        smoothness = np.clip(
            config["smoothness"][index]
            - detail * SMOOTHNESS_DETAIL_GAIN[role],
            0.04,
            0.92,
        )
        metallic_smoothness[y0:y1, x0:x1, 0] = metallic
        metallic_smoothness[y0:y1, x0:x1, 3] = smoothness
        orm[y0:y1, x0:x1, 0] = 1.0
        orm[y0:y1, x0:x1, 1] = 1.0 - smoothness
        orm[y0:y1, x0:x1, 2] = metallic
        if index == 3:
            emission[y0:y1, x0:x1] = normalized

    prefix = f"T_{theme}_V6_Atlas{profile['suffix']}"
    outputs = {
        "base_color": output_dir / f"{prefix}_BaseColor.png",
        "normal": output_dir / f"{prefix}_Normal.png",
        "metallic_smoothness": (
            output_dir / f"{prefix}_MetallicSmoothness.png"
        ),
        "orm": output_dir / f"{prefix}_ORM.png",
        "emission": output_dir / f"{prefix}_Emission.png",
    }
    as_image(base).save(outputs["base_color"], optimize=True)
    as_image(normal).save(outputs["normal"], optimize=True)
    as_image(metallic_smoothness, "RGBA").save(
        outputs["metallic_smoothness"],
        optimize=True,
    )
    as_image(orm).save(outputs["orm"], optimize=True)
    as_image(emission).save(outputs["emission"], optimize=True)

    manifest = {
        "theme": theme,
        "source": str(source_path.relative_to(project_root)),
        "size": size,
        "model_scale_class": profile_name,
        "detail_repeats": profile["repeats"],
        "quadrants": [role for _, _, role in QUADRANTS],
        "packing": {
            "metallic_smoothness": "R=metallic, A=smoothness",
            "orm": "R=ambient occlusion, G=roughness, B=metallic",
        },
        "outputs": {
            key: str(path.relative_to(project_root))
            for key, path in outputs.items()
        },
    }
    manifest_path = output_dir / f"{prefix}.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_theme(project_root, theme, config, size):
    source_path = (
        project_root
        / "ArtSource/Textures/ThemeMaterialV6"
        / theme
        / f"T_{theme}_V6_Source.png"
    )
    source = Image.open(source_path).convert("RGB").resize(
        (size, size),
        Image.Resampling.LANCZOS,
    )
    return [
        build_theme_variant(
            project_root,
            theme,
            config,
            size,
            source,
            profile_name,
            profile,
        )
        for profile_name, profile in DETAIL_PROFILES.items()
    ]


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    for theme, config in THEMES.items():
        for manifest in build_theme(
            project_root,
            theme,
            config,
            args.size,
        ):
            print(manifest)


if __name__ == "__main__":
    main()
