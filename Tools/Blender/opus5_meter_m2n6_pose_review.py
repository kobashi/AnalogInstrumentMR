"""Phase M2n6: five poses, two views, the delivered shape against the revision.

Alignment 201.2. The numbers say the shortened needle clears every tick; these
images are for the question numbers cannot answer - whether a needle 16.4 per
cent shorter still reads as pointing at the scale.

One rig per model, derived from the delivered shape and reused for the
revision, so the only difference between the two columns is the model. One clay
material on both, for the same reason the M2n3 sheets used one: the point is
form, not paint.

Rows are normalized 0 / 0.25 / 0.5 / 0.75 / 1, mapped onto -115 to +115
degrees. Columns are delivered front, revision front, delivered oblique,
revision oblique.

Blends are read, never saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n6_pose_review.py -- \
      --project-root "$PWD"
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
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n3_review as m2n3r
import opus5_meter_m2n6_sweep_revision as m2n6


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_{tag}_pose_review.json"
THEME = "KineticSafety"
FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
VIEWS = {"front": (0.0, 6.0), "oblique": (38.0, 22.0)}
GAP = 14


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--revision", default="M2n6", choices=("M2n6", "M2n7"))
    return parser.parse_args(args)


def pose_angle(fraction):
    return -m2n6.AMPLITUDE_DEG + 2.0 * m2n6.AMPLITUDE_DEG * fraction


def set_pose(degrees):
    pivot = bpy.data.objects[m2n.MOTION["pivot"]]
    pivot.rotation_mode = "XYZ"
    pivot.rotation_euler[1] = math.radians(degrees)
    bpy.context.view_layer.update()


def render_variant(blend, key, tag, rig, output_dir):
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    m2n3r.strip_existing_rig()
    m2n3r.apply_clay()
    review.configure_scene()
    written = {}
    for fraction in FRACTIONS:
        set_pose(pose_angle(fraction))
        for label, view in VIEWS.items():
            radius = rig["radius"] * (
                m2n3r.DETAIL_RADIUS_SCALE if label == "oblique" else 1.0
            )
            path = (
                output_dir
                / f"Preview_{key}_{THEME}_V6_{tag}_{label}_{int(fraction * 100):03d}.png"
            )
            review.shot(rig, rig["focus"], radius, view, rig["lens"], path)
            written[(fraction, label)] = path
    return written


def compose(delivered, revision, output_path, tag):
    """Five rows of poses, four columns: two views for each of two shapes."""
    order = [
        (fraction, label, source)
        for fraction in FRACTIONS
        for label in VIEWS
        for source in (delivered, revision)
    ]
    tiles = [review.load_rgba(source[(fraction, label)]) for fraction, label, source in order]
    height, width = tiles[0].shape[:2]
    columns, rows = 4, len(FRACTIONS)
    canvas = np.zeros(
        (rows * height + (rows - 1) * GAP, columns * width + (columns - 1) * GAP, 4),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    captions = []
    for index, tile in enumerate(tiles):
        row, column = divmod(index, columns)
        # Blender buffers run bottom-up; the labels are placed from the top.
        top = (rows - 1 - row) * (height + GAP)
        left = column * (width + GAP)
        canvas[top : top + height, left : left + width] = tile
        fraction, label, source = order[index]
        captions.append(
            (
                left + 14,
                row * (height + GAP) + 14,
                f"{tag.upper() if source is revision else 'M2N5'} {label.upper()}",
                f"POSE {fraction:.2f} = {pose_angle(fraction):+.0f} DEG",
            )
        )
    for left, top, title, subtitle in captions:
        review.draw_label(canvas, title, left, top)
        review.draw_label(canvas, subtitle, left, top + 42, colour=(0.72, 0.78, 0.86))
    review.save_rgba(canvas, output_path)


def main():
    args = parse_args()
    tag = args.revision
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    sheet_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "contact_sheets"
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "M2n6",
        "note": (
            "Delivered (M2n5 geometry) against the M2n6 revision, five poses, "
            "two views, one rig and one clay material for both."
        ),
        "poses": {f"{f:.2f}": pose_angle(f) for f in FRACTIONS},
        "views": VIEWS,
        "models": {},
    }
    for key in m2n.SOURCES:
        delivered_blend = m2n.source_blend(project_root, key)
        revision_blend = m2l.theme_dir(project_root) / m2n.SOURCES[key][
            "blend"
        ].replace("_Retopo.blend", f"_{tag}_Retopo.blend")
        bpy.ops.wm.open_mainfile(filepath=str(delivered_blend), load_ui=False)
        rig = m2n3r.rig_from(bpy.data.objects[m2k.MODELS[key]["root"]])
        delivered = render_variant(delivered_blend, key, "m2n5", rig, output_dir)
        revision = render_variant(revision_blend, key, tag.lower(), rig, output_dir)
        sheet = sheet_dir / f"ContactSheet_{key}_{THEME}_V6_{tag}_poses.png"
        compose(delivered, revision, sheet, tag)
        payload["models"][key] = {
            "delivered_blend": str(delivered_blend.relative_to(project_root)),
            "revision_blend": str(revision_blend.relative_to(project_root)),
            "rig": {name: value for name, value in rig.items() if name != "bounds"},
            "contact_sheet": str(sheet.relative_to(project_root)),
            "images": len(delivered) + len(revision),
        }
        print(f"[Opus5M2n6Review] {key}: {sheet.name}")

    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT.format(tag=tag.lower())).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
