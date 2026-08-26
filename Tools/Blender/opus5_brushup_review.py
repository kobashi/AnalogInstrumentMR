"""Fixed-condition Before / After review for a brush-up candidate.

The Gate A reviewer (`opus5_button_glyph_review`) is tied to one defect and one
travel pose. This is the same idea written against a spec, so the remaining
archetypes can be reviewed without a new script each time (alignment 51.2): a
model contributes a view list and an optional detail rig, and everything else -
identical camera, lights, world, exposure, resolution, and a rig derived from
the *shipped* bounds and reused for the candidate - is fixed here.

Deriving the rig from the shipped model matters: a camera fitted to the
candidate's own bounds would frame away exactly the growth a reviewer is trying
to judge.

The script only reads blends; it never saves one. EEVEE is not byte-reproducible
(alignment 33), so compare the images and the parameters, not image bytes.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_brushup_review.py -- \
      --project-root "$PWD" --model KineticSafety/Lamp
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
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review


REFERENCE_LIGHT_SCALE = 0.170

# Trace key light: enough for a silhouette, far too little to make an opaque
# surface look lit, so anything readable in this cell is emitting.
EMISSIVE_ON_ENERGY = 0.020

def cell(name, label, view, dark=False, detail=False, pose=None):
    """One review frame. `pose` is a pivot angle in degrees, for movable models."""
    return {
        "name": name,
        "label": label,
        "view": view,
        "dark": dark,
        "detail": detail,
        "pose": pose,
    }


VIEWS = {
    "KineticSafety/Lamp": {
        "cells": (
            cell("lit_tq", "LIT 3-4", (32.0, 22.0)),
            cell("lit_side", "LIT SIDE", (86.0, 6.0)),
            cell("detail", "DETAIL LENS", (24.0, 12.0), detail=True),
            cell("dark_tq", "EMISSIVE", (32.0, 22.0), dark=True),
        ),
        # Close enough to read the bezel and cage against the lens without the
        # camera entering the side guards.
        "detail": {"focus": (0.0, -0.070, 0.004), "radius": 0.235, "lens": 118.0},
    },
    "KineticSafety/StatusIndicator": {
        "cells": (
            cell("lit_tq", "LIT 3-4", (32.0, 22.0)),
            cell("lit_side", "LIT SIDE", (86.0, 6.0)),
            cell("detail", "DETAIL END CELL", (26.0, 14.0), detail=True),
            cell("dark_tq", "EMISSIVE", (32.0, 22.0), dark=True),
        ),
        # Framed on the right-hand cell, which is the one the end rib closes.
        "detail": {"focus": (0.066, -0.072, 0.0), "radius": 0.215, "lens": 115.0},
    },
    "KineticSafety/MeterMedium": {
        "cells": (
            cell("lit_neutral", "LIT NEUTRAL 0", (18.0, 16.0), pose=0.0),
            cell("lit_minimum", "LIT MIN -55", (0.0, 4.0), pose=-55.0),
            cell("lit_maximum", "LIT MAX +55", (0.0, 4.0), pose=55.0),
            cell("detail", "DETAIL HUB", (10.0, 10.0), detail=True, pose=0.0),
            cell("dark_maximum", "EMISSIVE MAX", (0.0, 4.0), dark=True, pose=55.0),
        ),
        "detail": {"focus": (0.0, -0.118, 0.010), "radius": 0.210, "lens": 112.0},
    },
    "KineticSafety/Toggle": {
        "cells": (
            cell("lit_min", "LIT MIN 0", (34.0, 20.0), pose=0.0),
            cell("lit_neutral", "LIT MID 28", (34.0, 20.0), pose=28.0),
            cell("lit_max", "LIT MAX 56", (34.0, 20.0), pose=56.0),
            cell("detail", "DETAIL SOCKET", (38.0, 30.0), detail=True, pose=28.0),
            cell("dark_min", "EMISSIVE", (34.0, 20.0), dark=True, pose=0.0),
        ),
        # On the joint, but far enough back that a guard post does not fill the
        # frame: at 0.150 m the near post ate the whole cell.
        "detail": {"focus": (0.0, -0.068, 0.004), "radius": 0.205, "lens": 88.0},
    },
    "KineticSafety/Rotary": {
        "cells": (
            cell("lit_min", "LIT 0", (30.0, 22.0), pose=0.0),
            cell("lit_neutral", "LIT 180", (30.0, 22.0), pose=180.0),
            cell("lit_quarter", "LIT 22", (30.0, 22.0), pose=22.5),
            cell("detail", "DETAIL GRIP", (24.0, 14.0), detail=True, pose=22.5),
            cell("dark_min", "EMISSIVE", (30.0, 22.0), dark=True, pose=0.0),
        ),
        # Framed off-axis on the knob flank, which is where the ribs read.
        "detail": {"focus": (0.026, -0.086, 0.0), "radius": 0.150, "lens": 105.0},
    },
    "KineticSafety/PowerSlider": {
        "cells": (
            cell("lit_min", "LIT MIN -90MM", (28.0, 20.0), pose=-0.09),
            cell("lit_neutral", "LIT MID 0", (28.0, 20.0), pose=0.0),
            cell("lit_max", "LIT MAX +90MM", (28.0, 20.0), pose=0.09),
            cell("detail", "DETAIL INDEX", (46.0, 24.0), detail=True, pose=0.0),
            cell("dark_neutral", "EMISSIVE", (28.0, 20.0), dark=True, pose=0.0),
        ),
        # On the index finger where it reads against the scale strip.
        "detail": {"focus": (0.040, -0.082, 0.0), "radius": 0.230, "lens": 104.0},
    },
    "KineticSafety/WindowMeter": {
        "cells": (
            cell("lit_neutral", "LIT NEUTRAL 0", (18.0, 18.0), pose=0.0),
            cell("lit_minimum", "LIT MIN -55", (0.0, 6.0), pose=-55.0),
            cell("lit_maximum", "LIT MAX +55", (0.0, 6.0), pose=55.0),
            cell("detail", "DETAIL HUB", (12.0, 12.0), detail=True, pose=0.0),
            cell("dark_maximum", "EMISSIVE MAX", (0.0, 6.0), dark=True, pose=55.0),
        ),
        "detail": {"focus": (0.0, -0.190, -0.075), "radius": 0.470, "lens": 105.0},
    },
    "KineticSafety/WindowPanel": {
        "cells": (
            cell("lit_neutral", "LIT VANE 0", (22.0, 20.0), pose=0.0),
            cell("lit_minimum", "LIT VANE -42", (0.0, 8.0), pose=-42.0),
            cell("lit_maximum", "LIT VANE +42", (0.0, 8.0), pose=42.0),
            cell("detail", "DETAIL CAP", (34.0, 18.0), detail=True, pose=0.0),
            cell("dark_neutral", "EMISSIVE", (22.0, 20.0), dark=True, pose=0.0),
        ),
        "detail": {"focus": (0.470, -0.195, 0.020), "radius": 0.560, "lens": 108.0},
    },
    "KineticSafety/MeterLarge": {
        "cells": (
            cell("lit_neutral", "LIT NEUTRAL 0", (18.0, 16.0), pose=0.0),
            cell("lit_minimum", "LIT MIN -55", (0.0, 4.0), pose=-55.0),
            cell("lit_maximum", "LIT MAX +55", (0.0, 4.0), pose=55.0),
            cell("detail", "DETAIL HUB", (10.0, 10.0), detail=True, pose=0.0),
            cell("dark_maximum", "EMISSIVE MAX", (0.0, 4.0), dark=True, pose=55.0),
        ),
        "detail": {"focus": (0.0, -0.156, 0.015), "radius": 0.315, "lens": 112.0},
    },
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append", choices=tuple(VIEWS))
    parser.add_argument("--revision", default=brushup.REVISION)
    return parser.parse_args(args)


def rig_from(root):
    meshes = pilot.meshes_under(root)
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
        "focus": (0.0, (lows[1] + highs[1]) * 0.5, (lows[2] + highs[2]) * 0.5),
        "radius": extent * 2.0,
        "lens": 62.0,
        "light_scale": light_scale,
        # Lights sit further out for a larger model, so wattage tracks the
        # square of that distance (alignment 31.2).
        "energy_scale": (light_scale / REFERENCE_LIGHT_SCALE) ** 2,
        "extent": extent,
    }


# In the trace-lit cell an opaque surface tops out around 0.20 display (Gate A
# measured exactly that on three shipped Buttons), so anything past this is the
# readout emitting rather than a specular glint.
EMISSIVE_THRESHOLD = 0.5


def luminance_stats(path):
    """Peak, percentiles and lit area - not the mean.

    AgX maps scene black to about 0.0745 display, so a dark cell's mean is
    dominated by that floor and a small bright feature barely moves it.

    `emissive_pixels` is the reason this is measured at all: adding guards and
    bezels to an instrument can quietly eat the lit area, which on an MR display
    is the part that carries the information. A brush-up that improves the
    hardware read while shrinking the readout is a regression, and the only way
    to notice is to count it.
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
        "emissive_threshold": EMISSIVE_THRESHOLD,
        "emissive_pixels": int(np.count_nonzero(luma > EMISSIVE_THRESHOLD)),
    }


def render_column(project_root, spec, blend, rig, tag, output_dir, label):
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    review.configure_scene()
    root = bpy.data.objects[brushup.SPECS[label]["root"]]
    if rig is None:
        rig = rig_from(root)
    theme, key = label.split("/")
    motion = brushup.SPECS[label].get("motion")
    pivot = bpy.data.objects[motion["pivot"]] if motion else None
    linear = bool(motion) and motion.get("kind") == "linear"
    rest = (
        (pivot.location if linear else pivot.rotation_euler).copy() if pivot else None
    )
    cells = {}
    scene = bpy.context.scene
    for item in spec["cells"]:
        frame = spec["detail"] if item["detail"] else rig
        shot_rig = dict(rig)
        world_colour = tuple(scene.world.color)
        if item["dark"]:
            shot_rig["energy_scale"] = rig["energy_scale"] * EMISSIVE_ON_ENERGY
            scene.world.color = (0.0, 0.0, 0.0)
        if item["pose"] is not None:
            brushup.pose_pivot(pivot, motion, rest, item["pose"])
        path = output_dir / f"{key}_{theme}_{tag}_{item['name']}.png"
        try:
            review.shot(
                shot_rig,
                frame["focus"],
                frame["radius"],
                item["view"],
                frame["lens"],
                path,
            )
        finally:
            scene.world.color = world_colour
            if pivot is not None:
                if linear:
                    pivot.location = rest
                else:
                    pivot.rotation_euler = rest
                bpy.context.view_layer.update()
        cells[item["name"]] = {
            "image": str(path.relative_to(project_root)),
            "luminance": luminance_stats(path),
        }
    return rig, cells


def compose(paths, labels, columns, output_path):
    tiles = [review.load_rgba(path) for path in paths]
    rows = len(tiles) // columns
    height, width = tiles[0].shape[:2]
    gap = review.CONTACT_GAP
    canvas = np.zeros(
        (rows * height + (rows - 1) * gap, columns * width + (columns - 1) * gap, 4),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        row, column = divmod(index, columns)
        x = column * (width + gap)
        # Image buffers run bottom-up but `draw_label` places from the top, so
        # the tile and its label count rows from opposite ends.
        canvas[
            (rows - 1 - row) * (height + gap) : (rows - 1 - row) * (height + gap)
            + height,
            x : x + width,
        ] = tile
        review.draw_label(canvas, labels[index], x + 18, row * (height + gap) + 18)
    review.save_rgba(canvas, output_path)


def run_one(project_root, label, revision):
    spec = VIEWS[label]
    theme, key = label.split("/")
    shipped = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{key}_{theme}_V6_Retopo.blend"
    )
    candidate = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / theme
        / f"BL_{key}_{theme}_V6_Opus5_{revision}_Retopo.blend"
    )
    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    sheet_dir = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "contact_sheets"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_dir.mkdir(parents=True, exist_ok=True)

    rig, baseline = render_column(
        project_root, spec, shipped, None, "baseline", output_dir, label
    )
    _, candidate_cells = render_column(
        project_root,
        spec,
        candidate,
        rig,
        f"opus5_{revision.lower()}",
        output_dir,
        label,
    )

    sheet = sheet_dir / f"{key}_{theme}_{revision}_brushup.png"
    compose(
        [project_root / baseline[item["name"]]["image"] for item in spec["cells"]]
        + [
            project_root / candidate_cells[item["name"]]["image"]
            for item in spec["cells"]
        ],
        [f"BEFORE {item['label']}" for item in spec["cells"]]
        + [f"AFTER {item['label']}" for item in spec["cells"]],
        len(spec["cells"]),
        sheet,
    )
    lit_area = {
        name: {
            "baseline": baseline[name]["luminance"]["emissive_pixels"],
            "candidate": candidate_cells[name]["luminance"]["emissive_pixels"],
            "delta": (
                candidate_cells[name]["luminance"]["emissive_pixels"]
                - baseline[name]["luminance"]["emissive_pixels"]
            ),
        }
        for name in (item["name"] for item in spec["cells"] if item["dark"])
    }
    print(
        f"[Opus5BrushUpReview] {label}: {sheet.relative_to(project_root)}; "
        + ", ".join(
            f"{name} lit area {value['baseline']} -> {value['candidate']} "
            f"({value['delta']:+d})"
            for name, value in lit_area.items()
        )
    )
    return {
        "emissive_lit_area": lit_area,
        "model": label,
        "revision": revision,
        "shipped_blend": str(shipped.relative_to(project_root)),
        "candidate_blend": str(candidate.relative_to(project_root)),
        "contact_sheet": str(sheet.relative_to(project_root)),
        "rig": {
            name: (list(value) if isinstance(value, tuple) else value)
            for name, value in rig.items()
        },
        "rig_source": "shipped model bounds, reused for the candidate",
        "detail_rig": spec.get("detail"),
        "emissive_on_energy_scale": EMISSIVE_ON_ENERGY,
        "cells": {
            item["name"]: {
                "label": item["label"],
                "view_azimuth_elevation": list(item["view"]),
                "dark": item["dark"],
                "detail_rig": item["detail"],
                "pose_degrees": item["pose"],
            }
            for item in spec["cells"]
        },
        "baseline": baseline,
        "candidate": candidate_cells,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    models = tuple(args.models) if args.models else tuple(VIEWS)
    entries = [run_one(project_root, label, args.revision) for label in models]
    index = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / f"brushup_{args.revision.lower()}_review_index.json"
    )
    index.write_text(
        json.dumps(
            {
                "revision": args.revision,
                "note": (
                    "Identical camera, lights, world, exposure and resolution "
                    "across every cell; the rig is derived from the shipped "
                    "model and reused for the candidate. EEVEE is not "
                    "byte-reproducible (alignment 33)."
                ),
                "models": {entry["model"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5BrushUpReview] index -> {index.relative_to(project_root)}")


if __name__ == "__main__":
    main()
