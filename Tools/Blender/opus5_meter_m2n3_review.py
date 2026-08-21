"""Phase M2n3: fixed-condition baseline / candidate renders for the meters.

Alignment 182.3. The production baseline and the refined candidate are rendered
under one camera, one light rig, one world, one exposure and one needle pose,
so the only thing that differs between the two images is the model. The rig is
derived from the *baseline* bounds and reused unchanged for the candidate: a
rig fitted to each model separately would reframe the shot and make a smaller
part look identical to a larger one.

Two views per model: a front overview, and an oblique detail at the bezel and
needle where the brush-up actually changed something.

The script only reads blends. It never saves one, and it writes only new files
under `review/` and `contact_sheets/`.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n3_review.py -- --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_handoff as m2n


THEME = "KineticSafety"
BASELINE_DIR = "ArtSource/Blender/ThemeHardSurfaceV6/KineticSafety"
OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n3_review.json"
# Azimuth, elevation. The overview is straight on; the detail looks across the
# bezel from the side, which is where the needle-to-tick clearance reads.
VIEWS = {
    "overview_front": (0.0, 6.0),
    "detail_oblique": (38.0, 22.0),
}
DETAIL_RADIUS_SCALE = 0.52
REFERENCE_LIGHT_SCALE = 0.170
GAP = 18


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def baseline_blend(project_root, key):
    return (
        project_root
        / BASELINE_DIR
        / f"BL_{key}_{THEME}_V6_ProductionReady.blend"
    )


def find_root(key):
    name = m2k.MODELS[key]["root"]
    if name in bpy.data.objects:
        return bpy.data.objects[name]
    roots = [
        obj
        for obj in bpy.data.objects
        if obj.parent is None and obj.name.startswith("PF_Visual_")
    ]
    if len(roots) != 1:
        raise AssertionError(f"{key}: {len(roots)} roots in this file")
    return roots[0]


def rig_from(root):
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render
        for corner in obj.bound_box
    ]
    lows = [min(point[i] for point in corners) for i in range(3)]
    highs = [max(point[i] for point in corners) for i in range(3)]
    extent = max(highs[i] - lows[i] for i in range(3))
    return {
        "focus": (
            (lows[0] + highs[0]) * 0.5,
            (lows[1] + highs[1]) * 0.5,
            (lows[2] + highs[2]) * 0.5,
        ),
        "radius": extent * 2.05,
        "lens": 62.0,
        "light_scale": extent * 0.5,
        # Lights sit at a multiple of the model size, so wattage has to follow
        # the square of that distance or the small meter arrives blown out and
        # the large one dark. The reference is the pilot rig that framed
        # MeterRound.
        "energy_scale": (extent * 0.5 / REFERENCE_LIGHT_SCALE) ** 2,
        "extent": extent,
        "bounds": {
            "min": [round(value, 6) for value in lows],
            "max": [round(value, 6) for value in highs],
        },
    }


def scene_materials():
    return sorted({material.name.split(".")[0] for material in bpy.data.materials})


def apply_clay():
    """One material on everything, both sides.

    The production baseline carries the V6 atlas material at 0.8 albedo and the
    candidates still carry the V5 set at 0.105 to 0.32, so rendering them as
    authored compares paint, not form - the baseline blows out and the
    candidate does not. The material sets are reported separately; these images
    are about silhouette, depth and how the parts read.
    """
    clay = bpy.data.materials.new("Opus5M2n3Clay")
    clay.use_nodes = True
    bsdf = clay.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.34, 0.35, 0.37, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.52
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(clay)
    return clay.name


def strip_existing_rig():
    """Lights or cameras saved in the file would break "one rig, both sides"."""
    removed = 0
    for obj in list(bpy.data.objects):
        if obj.type in {"LIGHT", "CAMERA"}:
            bpy.data.objects.remove(obj, do_unlink=True)
            removed += 1
    return removed


def set_neutral(root):
    """Every meter shares one motion contract, so one pose function does."""
    pivot = bpy.data.objects.get(m2n.MOTION["pivot"])
    if pivot is None:
        return False
    pivot.rotation_mode = "AXIS_ANGLE"
    pivot.rotation_axis_angle = (0.0, 0.0, 1.0, 0.0)
    bpy.context.view_layer.update()
    return True


def render_variant(blend, key, tag, rig, output_dir):
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    materials = scene_materials()
    meshes = sum(1 for obj in bpy.data.objects if obj.type == "MESH")
    removed = strip_existing_rig()
    apply_clay()
    review.configure_scene()
    root = find_root(key)
    posed = set_neutral(root)
    written = {}
    for label, view in VIEWS.items():
        radius = rig["radius"] * (
            DETAIL_RADIUS_SCALE if label.startswith("detail") else 1.0
        )
        path = output_dir / f"Preview_{key}_{THEME}_V6_M2n3_{tag}_{label}.png"
        review.shot(rig, rig["focus"], radius, view, rig["lens"], path)
        written[label] = path
    return written, {
        "needle_posed": posed,
        "authored_materials": materials,
        "meshes": meshes,
        "pre_existing_lights_or_cameras_removed": removed,
        "bounds": rig_from(root)["bounds"],
    }


def compose(pairs, labels, output_path):
    """Baseline left, candidate right, one row per view."""
    tiles = [[review.load_rgba(path) for path in row] for row in pairs]
    height, width = tiles[0][0].shape[:2]
    canvas = np.zeros(
        (
            len(tiles) * height + (len(tiles) - 1) * GAP,
            2 * width + GAP,
            4,
        ),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for row_index, row in enumerate(tiles):
        # Blender's buffers run bottom-up while the labels are placed from the
        # top, so the first row has to be written to the last band or the
        # images and their captions end up on opposite rows.
        top = (len(tiles) - 1 - row_index) * (height + GAP)
        for column_index, tile in enumerate(row):
            left = column_index * (width + GAP)
            canvas[top : top + height, left : left + width] = tile
    for index, (title, subtitle) in enumerate(labels):
        row_index, column_index = divmod(index, 2)
        left = column_index * (width + GAP) + 18
        top = row_index * (height + GAP) + 18
        review.draw_label(canvas, title, left, top)
        review.draw_label(canvas, subtitle, left, top + 46, colour=(0.72, 0.78, 0.86))
    review.save_rgba(canvas, output_path)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    sheet_dir = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "contact_sheets"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "M2n3",
        "note": (
            "Fixed-condition baseline / candidate renders (alignment 182.3). "
            "One rig per model, derived from the baseline and reused for the "
            "candidate. Blends are read, never saved."
        ),
        "conditions": {
            "material": (
                "one clay material on every mesh, both sides; the authored "
                "material sets differ in albedo and are reported per model"
            ),
            "resolution": review.RESOLUTION,
            "engine": "BLENDER_EEVEE",
            "view_transform": "AgX - Medium High Contrast",
            "world_colour": [0.012, 0.016, 0.022],
            "views": VIEWS,
            "pose": "needle at rest, 0 degrees",
            "rig_source": "baseline bounds, reused unchanged for the candidate",
        },
        "models": {},
    }
    for key in m2n.SOURCES:
        baseline = baseline_blend(project_root, key)
        candidate = m2n.source_blend(project_root, key)
        bpy.ops.wm.open_mainfile(filepath=str(baseline), load_ui=False)
        rig = rig_from(find_root(key))
        baseline_images, baseline_facts = render_variant(
            baseline, key, "baseline", rig, output_dir
        )
        candidate_images, candidate_facts = render_variant(
            candidate, key, "candidate", rig, output_dir
        )
        sheet = sheet_dir / f"ContactSheet_{key}_{THEME}_V6_M2n3.png"
        compose(
            [
                [baseline_images[label], candidate_images[label]]
                for label in VIEWS
            ],
            [
                pair
                for label in VIEWS
                for pair in (
                    ("BASELINE", label.replace("_", " ").upper()),
                    (
                        f"CANDIDATE {m2n.SOURCES[key]['revision'].replace('_', ' ')}",
                        label.replace("_", " ").upper(),
                    ),
                )
            ],
            sheet,
        )
        payload["models"][key] = {
            "baseline_blend": str(baseline.relative_to(project_root)),
            "candidate_blend": str(candidate.relative_to(project_root)),
            "rig": {
                name: value for name, value in rig.items() if name != "bounds"
            },
            "baseline": baseline_facts,
            "candidate": candidate_facts,
            "images": {
                "baseline": {
                    label: str(path.relative_to(project_root))
                    for label, path in baseline_images.items()
                },
                "candidate": {
                    label: str(path.relative_to(project_root))
                    for label, path in candidate_images.items()
                },
            },
            "contact_sheet": str(sheet.relative_to(project_root)),
        }
        print(f"[Opus5M2n3Review] {key}: {sheet.name}")

    payload["authoring_environment"] = blender_compat.provenance()
    output = project_root / OUTPUT
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
