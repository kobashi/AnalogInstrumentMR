"""Before and after: the shipped meter against the refined one.

The production baseline (`*_V6_ProductionReady.blend`) and the M2n8 revision,
under one camera, one light rig, one exposure and one needle pose, with the
same clay on both. The rig comes from the baseline and is reused unchanged, so
the only thing that differs between the two columns is the model.

Clay rather than the authored materials, for the reason the M2n3 sheets gave:
the baseline carries the V6 atlas material at 0.8 albedo and the candidates the
V5 set at 0.105 to 0.32, so rendering them as authored compares paint, not form.

Blends are read, never saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_baseline_vs_m2n8.py -- --project-root "$PWD"
"""

import argparse
import json
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
import opus5_meter_m2n8_revision as m2n8


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_baseline_vs_m2n8.json"
THEME = "KineticSafety"
GAP = 16


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def render(blend, key, tag, rig, output_dir):
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    materials = m2n3r.scene_materials()
    meshes = sum(1 for obj in bpy.data.objects if obj.type == "MESH")
    m2n3r.strip_existing_rig()
    m2n3r.apply_clay()
    review.configure_scene()
    m2n3r.set_neutral(m2n3r.find_root(key))
    written = {}
    for name, view, scale in (("front", (0.0, 6.0), 1.0), ("oblique", (38.0, 22.0), 0.55)):
        path = output_dir / f"Preview_{key}_BeforeAfter_{tag}_{name}.png"
        review.shot(rig, rig["focus"], rig["radius"] * scale, view, rig["lens"], path)
        written[name] = path
    return written, {"authored_materials": materials, "meshes": meshes}


def assemble(rows, labels, output_path):
    tiles = [[review.load_rgba(path) for path in row] for row in rows]
    height, width = tiles[0][0].shape[:2]
    canvas = np.zeros(
        (len(tiles) * height + (len(tiles) - 1) * GAP, 2 * width + GAP, 4),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for index, row in enumerate(tiles):
        top = (len(tiles) - 1 - index) * (height + GAP)
        for column, tile in enumerate(row):
            canvas[top : top + height, column * (width + GAP) :
                   column * (width + GAP) + width] = tile
    for index, row in enumerate(labels):
        for column, (title, subtitle) in enumerate(row):
            left = column * (width + GAP) + 16
            top = index * (height + GAP) + 16
            review.draw_label(canvas, title, left, top)
            review.draw_label(canvas, subtitle, left, top + 44,
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
    payload = {"phase": "before-after", "sheets": {}}
    for key in m2n.SOURCES:
        baseline = m2n3r.baseline_blend(project_root, key)
        refined = m2n8.revision_blend(project_root, key)
        bpy.ops.wm.open_mainfile(filepath=str(baseline), load_ui=False)
        rig = m2n3r.rig_from(m2n3r.find_root(key))
        before, before_facts = render(baseline, key, "baseline", rig, output_dir)
        after, after_facts = render(refined, key, "m2n8", rig, output_dir)
        sheet = sheet_dir / f"ContactSheet_{key}_Baseline_vs_M2n8.png"
        assemble(
            [[before["front"], after["front"]], [before["oblique"], after["oblique"]]],
            [
                [("BEFORE PRODUCTION", "FRONT"), ("AFTER M2N8", "FRONT")],
                [("BEFORE PRODUCTION", "OBLIQUE"), ("AFTER M2N8", "OBLIQUE")],
            ],
            sheet,
        )
        payload["sheets"][key] = {
            "path": str(sheet),
            "sha256": m1.digest(sheet),
            "baseline_blend": str(baseline.relative_to(project_root)),
            "refined_blend": str(refined.relative_to(project_root)),
            "baseline": before_facts,
            "refined": after_facts,
        }
        print(f"[BeforeAfter] {key}: {sheet.name}")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
