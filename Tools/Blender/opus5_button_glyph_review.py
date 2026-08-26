"""Gate A visual review for defect D-1: does the Button emit anything?

Renders the shipped Button and the D-1 candidate under identical cameras,
lights, world, exposure and resolution, in two lighting conditions and two
travel poses, and composes one contact sheet per theme.

The emissive-ON condition is the whole point of the defect: with the key lights
dropped to a trace the shipped Button goes completely dark, because it carries
no readout-role surface at all, while the candidate shows the restored glyph.
The neutral / full-travel pair shows the glyph riding the travel island without
entering the guide.

The camera is derived once from the *shipped* bounds and reused for the
candidate, so the two columns are framed identically even though the candidate
is 3 mm deeper.

The script only reads blends; it never saves one. EEVEE renders are not
byte-reproducible (alignment 33), so compare the images and the parameters, not
image bytes.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_button_glyph_review.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_button_glyph_candidate as candidate


KEY = "Button"
THEMES = candidate.THEMES
VIEW = (32.0, 22.0)

# The reference distance the review light energies were tuned at.
REFERENCE_LIGHT_SCALE = 0.170

# Trace key light: enough to read the silhouette, far too little to make an
# opaque surface look lit. Anything visible at this level is emitting.
EMISSIVE_ON_ENERGY = 0.020

CELLS = (
    ("lit_neutral", "LIT NEUTRAL", False, 0.0),
    ("dark_neutral", "EMISSIVE NEUTRAL", True, 0.0),
    ("dark_full", "EMISSIVE FULL 14MM", True, candidate.TRAVEL_METRES),
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append", choices=THEMES)
    parser.add_argument("--revision", default=candidate.REVISION)
    return parser.parse_args(args)


def root_of(theme):
    return bpy.data.objects[f"PF_Visual_{KEY}_{theme}_V6"]


def rig_from(root):
    meshes = candidate.gen.meshes_under(root)
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    lows = [min(point[i] for point in corners) for i in range(3)]
    highs = [max(point[i] for point in corners) for i in range(3)]
    extent = max(highs[i] - lows[i] for i in range(3))
    light_scale = extent * 0.5
    return {
        "focus": (
            0.0,
            (lows[1] + highs[1]) * 0.5,
            (lows[2] + highs[2]) * 0.5,
        ),
        "radius": extent * 2.0,
        "lens": 62.0,
        "light_scale": light_scale,
        # Lights sit further out for a larger model, so wattage tracks the
        # square of that distance (alignment 31.2).
        "energy_scale": (light_scale / REFERENCE_LIGHT_SCALE) ** 2,
        "extent": extent,
    }


def render_cell(rig, root, dark, travel_metres, path):
    travel = candidate.gen.descendant_named(root, "button_travel")
    base = travel.location.copy()
    scene = bpy.context.scene
    world_colour = tuple(scene.world.color)
    shot_rig = dict(rig)
    if dark:
        shot_rig["energy_scale"] = rig["energy_scale"] * EMISSIVE_ON_ENERGY
        scene.world.color = (0.0, 0.0, 0.0)
    try:
        travel.location = base + Vector((0.0, travel_metres, 0.0))
        bpy.context.view_layer.update()
        review.shot(
            shot_rig,
            rig["focus"],
            rig["radius"],
            VIEW,
            rig["lens"],
            path,
        )
    finally:
        travel.location = base
        scene.world.color = world_colour
        bpy.context.view_layer.update()


def luminance_stats(path):
    """Luminance summary of a render, so "it emits" is a number too.

    Mean is a poor summary here: AgX maps scene black to about 0.0745 display,
    so most of a dark frame sits on that floor and a bright but small glyph
    barely moves the average. Peak and the high percentiles are what separate an
    emitting surface from a specular glint, so both are reported and the caller
    thresholds the candidate against the brightest pixel the *shipped* model can
    produce under the same light.
    """
    pixels = review.load_rgba(path)
    luma = (
        0.2126 * pixels[..., 0] + 0.7152 * pixels[..., 1] + 0.0722 * pixels[..., 2]
    )
    return {
        "mean": round(float(np.mean(luma)), 6),
        "median": round(float(np.median(luma)), 6),
        "p99": round(float(np.percentile(luma, 99.0)), 6),
        "max": round(float(np.max(luma)), 6),
    }, luma


def render_column(project_root, theme, blend, rig, tag, output_dir):
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    review.configure_scene()
    root = root_of(theme)
    if rig is None:
        rig = rig_from(root)
    cells = {}
    for name, _, dark, travel_metres in CELLS:
        path = output_dir / f"{KEY}_{theme}_{tag}_{name}.png"
        render_cell(rig, root, dark, travel_metres, path)
        stats, luma = luminance_stats(path)
        cells[name] = {
            "image": str(path.relative_to(project_root)),
            "luminance": stats,
            "_luma": luma,
        }
    return rig, cells


def compose(paths, labels, output_path):
    tiles = [review.load_rgba(path) for path in paths]
    columns = len(CELLS)
    rows = len(tiles) // columns
    height, width = tiles[0].shape[:2]
    gap = review.CONTACT_GAP
    canvas = np.zeros(
        (
            rows * height + (rows - 1) * gap,
            columns * width + (columns - 1) * gap,
            4,
        ),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        row, column = divmod(index, columns)
        x = column * (width + gap)
        # Image buffers run bottom-up but `draw_label` places from the top, so
        # the tile and its label need the row counted from opposite ends -
        # otherwise every label lands on the wrong row.
        buffer_y = (rows - 1 - row) * (height + gap)
        label_y = row * (height + gap) + 18
        canvas[buffer_y : buffer_y + height, x : x + width] = tile
        review.draw_label(canvas, labels[index], x + 18, label_y)
    review.save_rgba(canvas, output_path)


def run_one(project_root, theme, revision):
    shipped = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{KEY}_{theme}_V6_Retopo.blend"
    )
    candidate_blend = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / theme
        / f"BL_{KEY}_{theme}_V6_Opus5_{revision}_Retopo.blend"
    )
    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    sheet_dir = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "contact_sheets"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_dir.mkdir(parents=True, exist_ok=True)

    # The rig comes from the shipped model and is then reused verbatim, so the
    # candidate cannot be flattered by a camera fitted to its own bounds.
    rig, baseline_cells = render_column(
        project_root, theme, shipped, None, "baseline", output_dir
    )
    _, candidate_cells = render_column(
        project_root, theme, candidate_blend, rig, f"opus5_{revision.lower()}", output_dir
    )

    sheet = sheet_dir / f"{KEY}_{theme}_{revision}_glyph.png"
    compose(
        [project_root / baseline_cells[name]["image"] for name, *_ in CELLS]
        + [project_root / candidate_cells[name]["image"] for name, *_ in CELLS],
        [f"BEFORE {label}" for _, label, *_ in CELLS]
        + [f"AFTER {label}" for _, label, *_ in CELLS],
        sheet,
    )

    # Threshold on the shipped model's own peak rather than on a constant: a
    # candidate pixel above it is brighter than anything the shipped Button can
    # produce under identical light, which is exactly the D-1 claim.
    emission = {}
    for name, _, dark, _ in CELLS:
        if not dark:
            continue
        threshold = baseline_cells[name]["luminance"]["max"]
        luma = candidate_cells[name]["_luma"]
        emission[name] = {
            "threshold": threshold,
            "threshold_source": "brightest pixel of the shipped model, same cell",
            "candidate_peak": candidate_cells[name]["luminance"]["max"],
            "candidate_pixels_above_threshold": int(np.count_nonzero(luma > threshold)),
            "candidate_fraction_above_threshold": round(
                float(np.count_nonzero(luma > threshold) / luma.size), 8
            ),
        }
    for cells in (baseline_cells, candidate_cells):
        for cell in cells.values():
            cell.pop("_luma", None)

    print(
        f"[Opus5ButtonD1Review] {theme}: "
        + ", ".join(
            f"{name} peak {baseline_cells[name]['luminance']['max']:.4f} -> "
            f"{candidate_cells[name]['luminance']['max']:.4f} "
            f"({emission[name]['candidate_pixels_above_threshold']} px above)"
            for name in emission
        )
    )
    return {
        "theme": theme,
        "revision": revision,
        "shipped_blend": str(shipped.relative_to(project_root)),
        "candidate_blend": str(candidate_blend.relative_to(project_root)),
        "contact_sheet": str(sheet.relative_to(project_root)),
        "view_azimuth_elevation": list(VIEW),
        "rig": {
            key: (list(value) if isinstance(value, tuple) else value)
            for key, value in rig.items()
        },
        "rig_source": "shipped model bounds, reused for the candidate",
        "emissive_on_energy_scale": EMISSIVE_ON_ENERGY,
        "cells": {name: label for name, label, *_ in CELLS},
        "baseline": baseline_cells,
        "candidate": candidate_cells,
        "emission_over_shipped": emission,
        "view_transform_note": (
            "AgX maps scene black to about 0.0745 display, so the median of a "
            "dark cell sits on that floor in both columns. Peak and the "
            "above-threshold count, not the mean, carry the comparison."
        ),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    themes = tuple(args.themes) if args.themes else THEMES
    entries = [run_one(project_root, theme, args.revision) for theme in themes]
    index = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / f"button_glyph_{args.revision.lower()}_review_index.json"
    )
    index.write_text(
        json.dumps(
            {
                "defect": "D-1",
                "revision": args.revision,
                "note": (
                    "Identical camera, lights, world, exposure and resolution "
                    "across every cell; the rig is derived from the shipped "
                    "model and reused for the candidate. EEVEE is not "
                    "byte-reproducible (alignment 33)."
                ),
                "themes": {entry["theme"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5ButtonD1Review] index -> {index.relative_to(project_root)}")


if __name__ == "__main__":
    main()
