"""Regression gate: the atlas builder's defaults must reproduce what shipped.

`build_v6_material_atlases.py` gained a staging output option and tile-relative
tuning parameters so that repeat counts can be raised without the fixed pixel
radii filtering the detail away. Those parameters default to the values the
shipped sheets were built with, and this script is what holds them there: it
rebuilds every theme/scale-class/map into a temporary directory and compares the
result pixel by pixel against the active Unity textures.

Exits non-zero on any difference. PNG encoder differences are tolerated;
pixel differences are not.

Usage::

    .venv-textures/bin/python Tools/Textures/verify_v6_atlas_equivalence.py \
      --project-root "$PWD"
"""

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_v6_material_atlases as builder


MAPS = ("BaseColor", "Normal", "MetallicSmoothness", "ORM", "Emission")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--size", type=int, default=1024)
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    shipped_root = project_root / "Assets/MatsuMotoMeterAR/Content/Themes"

    with tempfile.TemporaryDirectory() as staging:
        staging = Path(staging)
        for theme in builder.THEMES:
            builder.build_theme(
                project_root,
                theme,
                builder.THEMES[theme],
                args.size,
                builder.DEFAULT_TUNING,
                staging,
            )

        compared = 0
        identical = 0
        failures = []
        for theme in builder.THEMES:
            for profile in builder.DETAIL_PROFILES.values():
                for name in MAPS:
                    filename = (
                        f"T_{theme}_V6_Atlas{profile['suffix']}_{name}.png"
                    )
                    shipped = (
                        shipped_root
                        / theme
                        / "Textures/ThemeMaterialV6"
                        / filename
                    )
                    rebuilt = staging / theme / filename
                    if not shipped.is_file():
                        failures.append(f"{filename}: no shipped sheet")
                        continue
                    if not rebuilt.is_file():
                        failures.append(f"{filename}: not rebuilt")
                        continue
                    compared += 1
                    if hashlib.sha256(
                        shipped.read_bytes()
                    ).hexdigest() == hashlib.sha256(
                        rebuilt.read_bytes()
                    ).hexdigest():
                        identical += 1
                        continue
                    left = np.asarray(Image.open(shipped)).astype(np.int32)
                    right = np.asarray(Image.open(rebuilt)).astype(np.int32)
                    if left.shape != right.shape:
                        failures.append(
                            f"{filename}: shape {left.shape} vs {right.shape}"
                        )
                        continue
                    delta = int(np.abs(left - right).max())
                    if delta:
                        failures.append(
                            f"{filename}: max pixel delta {delta}"
                        )

    print(
        f"[AtlasEquivalence] {compared} sheets compared, "
        f"{identical} byte-identical, "
        f"{compared - identical - len(failures)} pixel-identical, "
        f"{len(failures)} failing"
    )
    for failure in failures:
        print(f"  FAIL {failure}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
