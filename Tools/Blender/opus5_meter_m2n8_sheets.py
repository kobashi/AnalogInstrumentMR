"""Phase M2n8: M2n7 against M2n8, in the models' own materials.

Alignment 219.2. The whole-model render path, which has always worked, with one
rig per model reused for both revisions. No diagnostic colours: the point now is
how the meter reads, so it is rendered as authored. The close-up row is cropped
from the same front image rather than shot with a second rig.

Blends are read, never saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n8_sheets.py -- --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n3_review as m2n3r
import opus5_meter_m2n7_depth_revision as m2n7
import opus5_meter_m2n8_revision as m2n8


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n8_sheets.json"
THEME = "KineticSafety"
GAP = 14
CROP = 430


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def render_pair(blend, key, tag, rig, output_dir):
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    m2n3r.strip_existing_rig()
    review.configure_scene()
    pivot = bpy.data.objects[m2n.MOTION["pivot"]]
    pivot.rotation_mode = "XYZ"
    pivot.rotation_euler[1] = 0.0
    bpy.context.view_layer.update()
    written = {}
    for name, view, scale in (("front", (0.0, 6.0), 1.0), ("oblique", (40.0, 24.0), 0.55)):
        path = output_dir / f"Preview_{key}_M2n8sheet_{tag}_{name}.png"
        review.shot(rig, rig["focus"], rig["radius"] * scale, view, rig["lens"], path)
        written[name] = path
    return written


def centre_crop(path, size=CROP):
    image = review.load_rgba(path)
    height, width = image.shape[:2]
    top = (height - size) // 2
    left = (width - size) // 2
    return image[top : top + size, left : left + size]


def assemble(rows, labels, output_path):
    height = max(tile.shape[0] for row in rows for tile in row)
    width = max(tile.shape[1] for row in rows for tile in row)
    canvas = np.zeros(
        (len(rows) * height + (len(rows) - 1) * GAP, 2 * width + GAP, 4),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for index, row in enumerate(rows):
        top = (len(rows) - 1 - index) * (height + GAP)
        for column, tile in enumerate(row):
            left = column * (width + GAP)
            canvas[top : top + tile.shape[0], left : left + tile.shape[1]] = tile
    for index, row in enumerate(labels):
        for column, (title, subtitle) in enumerate(row):
            left = column * (width + GAP) + 14
            top = index * (height + GAP) + 14
            review.draw_label(canvas, title, left, top)
            if subtitle:
                review.draw_label(canvas, subtitle, left, top + 42,
                                  colour=(0.72, 0.78, 0.86))
    review.save_rgba(canvas, output_path)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    sheet_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "contact_sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": "M2n8",
        "note": (
            "M2n7 against M2n8 in the models' own materials (alignment 219.2). "
            "One rig per model; the close-up row is cropped from the front "
            "image. Blends are read, never saved."
        ),
        "sheets": {},
    }
    for key in m2n.SOURCES:
        previous = m2n7.revision_blend(project_root, key)
        current = m2n8.revision_blend(project_root, key)
        bpy.ops.wm.open_mainfile(filepath=str(previous), load_ui=False)
        rig = m2n3r.rig_from(bpy.data.objects[m2k.MODELS[key]["root"]])
        before = render_pair(previous, key, "m2n7", rig, output_dir)
        after = render_pair(current, key, "m2n8", rig, output_dir)
        rows = [
            [review.load_rgba(before["front"]), review.load_rgba(after["front"])],
            [review.load_rgba(before["oblique"]), review.load_rgba(after["oblique"])],
            [centre_crop(before["front"]), centre_crop(after["front"])],
        ]
        labels = [
            [("M2N7", "FRONT"), ("M2N8", "FRONT")],
            [("M2N7", "OBLIQUE"), ("M2N8", "OBLIQUE")],
            [("M2N7", "AXIS CROP"), ("M2N8", "AXIS CROP")],
        ]
        sheet = sheet_dir / f"ContactSheet_{key}_M2n7_vs_M2n8.png"
        assemble(rows, labels, sheet)
        payload["sheets"][key] = {
            "path": str(sheet),
            "sha256": m1.digest(sheet),
            "m2n7_blend": str(previous.relative_to(project_root)),
            "m2n8_blend": str(current.relative_to(project_root)),
        }
        print(f"[Opus5M2n8Sheets] {key}: {sheet.name}")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
