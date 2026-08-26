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

# Swatch tuning.
#
# The high-pass and relief radii below are absolute pixel values that were
# chosen against the shipped repeat counts, where one tile is 171 px. Raising a
# repeat count shrinks the tile without moving these radii, so the detail is
# filtered away instead of getting finer: at 16 repeats the tile is 32 px and an
# 18 px high-pass leaves almost nothing. Setting a `*_tiles` divisor makes the
# corresponding radius scale with the tile instead.
#
# These defaults reproduce the shipped atlases byte for byte. Keep it that way:
# `verify_v6_atlas_equivalence.py` is the regression gate.
DEFAULT_TUNING = {
    "high_pass_radius_px": 18.0,
    "high_pass_radius_tiles": None,
    "relief_radius_px": 2.2,
    "relief_radius_tiles": None,
    "smoothness_radius_px": 1.2,
    "smoothness_radius_tiles": None,
    "base_gain_scale": 1.0,
    "smoothness_gain_scale": 1.0,
    "normal_strength_scale": 1.0,
}

# `readout` is the dial graphic, not a tiling material: it is authored once per
# quadrant and repeats = 1 is part of the readout contract, not a tuning knob.
TILING_ROLES = ("body", "metal", "gasket")

# Repeat counts chosen on Quest 3, 2026-08-10. Standard profile B beat A on
# grain fineness and beat BT, whose stronger edge response risked temporal
# shimmer (docs/OPUS5_CODEX_ALIGNMENT.md 18.3). Medium retained its shipped
# profile because Fine was indistinguishable at 1 m and showed no shimmer
# (section 43). Large retained its shipped 1K profile because neither 2K
# candidate showed a visible benefit at 2 m (section 33.3). All adopted profiles
# use the default swatch tuning.
#
# This is deliberately not the DETAIL_PROFILES default. Flipping the default is
# the same change as updating the shipped textures, which is still gated, and it
# would make `verify_v6_atlas_equivalence.py` fail by design - that gate compares
# against the sheets built with 3/5/3. When the production texture update is
# approved, change DETAIL_PROFILES and re-baseline the gate in the same commit.
ADOPTED_REPEATS = {
    "Standard": {"body": 16, "metal": 21, "gasket": 16},
    "Medium": {"body": 5, "metal": 8, "gasket": 5},
    "Large": {"body": 8, "metal": 12, "gasket": 7},
}

# CLI flag per tuning key. All default to None so `--adopted` can tell "not
# given" from "given a value that equals the default" and reject the former's
# opposite outright.
TUNING_ARGUMENTS = (
    ("high_pass_radius_tiles", "--high-pass-radius-tiles"),
    ("relief_radius_tiles", "--relief-radius-tiles"),
    ("smoothness_radius_tiles", "--smoothness-radius-tiles"),
    ("base_gain_scale", "--base-gain-scale"),
    ("smoothness_gain_scale", "--smoothness-gain-scale"),
    ("normal_strength_scale", "--normal-strength-scale"),
)


def tile_size_for(size, repeats):
    """The tile edge `mirrored_detail_swatch` will use for one quadrant."""
    half = size // 2
    if repeats <= 1:
        return half
    return max(24, half // repeats)


def resolve_radius(tuning, absolute_key, tiles_key, tile_size):
    divisor = tuning.get(tiles_key)
    if divisor is None:
        return tuning[absolute_key]
    return max(2.0, tile_size / divisor)


def parse_repeats(text):
    """`body=16,metal=21,gasket=16` -> dict, merged onto the profile."""
    overrides = {}
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        role, separator, value = item.partition("=")
        role = role.strip()
        if not separator:
            raise argparse.ArgumentTypeError(
                f"expected role=count, got {item!r}"
            )
        if role == "readout":
            raise argparse.ArgumentTypeError(
                "readout carries the dial graphic, not a tiling material; its "
                "repeat count is fixed at 1 and cannot be overridden"
            )
        if role not in TILING_ROLES:
            raise argparse.ArgumentTypeError(
                f"unknown role {role!r}; expected one of {', '.join(TILING_ROLES)}"
            )
        try:
            count = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"{role}: expected an integer repeat count, got {value!r}"
            ) from None
        if count < 1:
            raise argparse.ArgumentTypeError(
                f"{role}: repeat count must be at least 1, got {count}"
            )
        if role in overrides:
            raise argparse.ArgumentTypeError(f"{role}: given twice")
        overrides[role] = count
    if not overrides:
        raise argparse.ArgumentTypeError("no repeat overrides were given")
    return overrides


def positive(text):
    value = float(text)
    if not value > 0.0:
        raise argparse.ArgumentTypeError(f"expected a positive value, got {value}")
    return value


def non_negative(text):
    value = float(text)
    if value < 0.0:
        raise argparse.ArgumentTypeError(
            f"expected a value of at least 0, got {value}"
        )
    return value


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--size", type=int, default=1024)
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Write the sheets here instead of the active Unity texture path. "
            "Use this for every experiment; the default overwrites production."
        ),
    )
    parser.add_argument("--theme", action="append", choices=tuple(THEMES))
    parser.add_argument(
        "--scale-class", action="append", choices=tuple(DETAIL_PROFILES)
    )
    parser.add_argument(
        "--repeats",
        type=parse_repeats,
        default=None,
        help="Override repeat counts, e.g. body=16,metal=21,gasket=16.",
    )
    parser.add_argument(
        "--adopted",
        action="store_true",
        help=(
            "Use the repeat counts adopted on Quest for the requested scale "
            "class instead of the shipped profile. Requires --scale-class and "
            "cannot be combined with --repeats."
        ),
    )
    for key, flag in TUNING_ARGUMENTS:
        parser.add_argument(
            flag,
            dest=key,
            type=positive if key.endswith("_tiles") else non_negative,
            default=None,
        )
    return parser.parse_args()


def explicit_tuning_arguments(args):
    """Tuning flags the caller actually passed, default-valued or not."""
    return [flag for key, flag in TUNING_ARGUMENTS if getattr(args, key) is not None]


def tuning_from_args(args):
    tuning = dict(DEFAULT_TUNING)
    for key, _ in TUNING_ARGUMENTS:
        value = getattr(args, key)
        if value is not None:
            tuning[key] = value
    return tuning


def as_float(image):
    return np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0


def as_image(array, mode="RGB"):
    """Pack a float array into an 8-bit image.

    The mode is inferred from the array shape rather than passed to
    `Image.fromarray`: that parameter is deprecated and is removed in Pillow 13.
    Inference gives the same result for the shapes used here - (h, w, 3) is RGB
    and (h, w, 4) is RGBA - and the mode check below keeps the caller's intent
    explicit rather than silently accepting a mismatched array.
    """
    values = np.clip(array * 255.0 + 0.5, 0, 255).astype(np.uint8)
    image = Image.fromarray(values)
    if image.mode != mode:
        raise ValueError(
            f"expected {mode} from array shape {values.shape}, got {image.mode}"
        )
    return image


def normalize_swatch(image, target, detail_gain, radius=18.0, gain_scale=1.0):
    source = as_float(image)
    blurred = as_float(image.filter(ImageFilter.GaussianBlur(radius=radius)))
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
    result += high_frequency * detail_gain * gain_scale
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


def normal_from_swatch(image, strength, radius=2.2):
    gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    blurred = np.asarray(
        image.convert("L").filter(ImageFilter.GaussianBlur(radius=radius)),
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
    tuning=None,
    output_root=None,
):
    tuning = DEFAULT_TUNING if tuning is None else tuning
    source_path = (
        project_root
        / "ArtSource/Textures/ThemeMaterialV6"
        / theme
        / f"T_{theme}_V6_Source.png"
    )
    output_dir = (
        Path(output_root) / theme
        if output_root is not None
        else project_root
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
        repeats = profile["repeats"][role]
        tile = tile_size_for(size, repeats)
        detailed = mirrored_detail_swatch(crop, repeats)
        normalized = normalize_swatch(
            detailed,
            config["colors"][index],
            BASE_DETAIL_GAIN[role],
            resolve_radius(
                tuning, "high_pass_radius_px", "high_pass_radius_tiles", tile
            ),
            tuning["base_gain_scale"],
        )
        base[y0:y1, x0:x1] = normalized
        normal[y0:y1, x0:x1] = normal_from_swatch(
            detailed,
            config["normal_strength"][index] * tuning["normal_strength_scale"],
            resolve_radius(
                tuning, "relief_radius_px", "relief_radius_tiles", tile
            ),
        )
        detail = np.asarray(
            detailed.convert("L").filter(
                ImageFilter.GaussianBlur(
                    radius=resolve_radius(
                        tuning,
                        "smoothness_radius_px",
                        "smoothness_radius_tiles",
                        tile,
                    )
                )
            ),
            dtype=np.float32,
        ) / 255.0
        detail = np.clip(detail - float(detail.mean()), -0.12, 0.12)
        metallic = config["metallic"][index]
        smoothness = np.clip(
            config["smoothness"][index]
            - detail
            * SMOOTHNESS_DETAIL_GAIN[role]
            * tuning["smoothness_gain_scale"],
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

    def describe(path):
        try:
            return str(Path(path).relative_to(project_root))
        except ValueError:
            return str(path)

    manifest = {
        "theme": theme,
        "source": describe(source_path),
        "size": size,
        "model_scale_class": profile_name,
        "detail_repeats": profile["repeats"],
        "tile_pixels": {
            role: tile_size_for(size, profile["repeats"][role])
            for _, _, role in QUADRANTS
        },
        "swatch_tuning": tuning,
        "quadrants": [role for _, _, role in QUADRANTS],
        "packing": {
            "metallic_smoothness": "R=metallic, A=smoothness",
            "orm": "R=ambient occlusion, G=roughness, B=metallic",
        },
        "outputs": {key: describe(path) for key, path in outputs.items()},
    }
    manifest_path = output_dir / f"{prefix}.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_theme(
    project_root,
    theme,
    config,
    size,
    tuning=None,
    output_root=None,
    scale_classes=None,
    repeats_override=None,
):
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
    manifests = []
    for profile_name, profile in DETAIL_PROFILES.items():
        if scale_classes and profile_name not in scale_classes:
            continue
        if repeats_override:
            profile = dict(profile)
            profile["repeats"] = {**profile["repeats"], **repeats_override}
        manifests.append(
            build_theme_variant(
                project_root,
                theme,
                config,
                size,
                source,
                profile_name,
                profile,
                tuning,
                output_root,
            )
        )
    return manifests


def resolve_repeats(args):
    if not args.adopted:
        return args.repeats
    if args.repeats:
        raise SystemExit("--adopted and --repeats cannot be combined")
    if not args.output_dir:
        raise SystemExit(
            "--adopted requires --output-dir; without it the adopted sheets "
            "would overwrite the active Unity textures"
        )
    explicit = explicit_tuning_arguments(args)
    if explicit:
        raise SystemExit(
            "--adopted reproduces the profile validated on Quest, which fixes "
            "the swatch tuning as well as the repeat counts; remove "
            + ", ".join(explicit)
        )
    classes = args.scale_class or []
    unknown = [name for name in classes if name not in ADOPTED_REPEATS]
    if len(classes) != 1 or unknown:
        raise SystemExit(
            "--adopted needs exactly one --scale-class with an adopted value; "
            f"available: {', '.join(sorted(ADOPTED_REPEATS))}"
        )
    return dict(ADOPTED_REPEATS[classes[0]])


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    tuning = tuning_from_args(args)
    repeats_override = resolve_repeats(args)
    output_root = Path(args.output_dir).resolve() if args.output_dir else None
    themes = args.theme or list(THEMES)
    for theme in themes:
        for manifest in build_theme(
            project_root,
            theme,
            THEMES[theme],
            args.size,
            tuning,
            output_root,
            args.scale_class,
            repeats_override,
        ):
            print(manifest)


if __name__ == "__main__":
    main()
