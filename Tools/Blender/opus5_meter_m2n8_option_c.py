"""Phase M2n8 pre-work, second pass: option C, and a Round sheet that is not empty.

Alignment 217. Two corrections to the last attempt.

Option C stops trying to stack every part in depth. The ticks and the ring are
separated where they actually overlap - in radius - by trimming the tick's
outer end back from the ring's inner face. The ring then stays where it is, and
is only brought towards the viewer if the needle has room for it, measured over
the travel rather than assumed.

The Round sheet is rendered with the rig that has always worked on this model,
not a hand-tuned close-up rig that put the subject outside the frame. The pivot
is projected into the image, the crop is taken around that pixel, and every
panel is checked for non-background content before the sheet is assembled.

Nothing is saved but the images and one report.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n8_option_c.py -- --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n3_review as m2n3r
import opus5_meter_m2n7_depth_revision as m2n7
import opus5_meter_m2n8_diagnostic_sheets as sheets


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n8_option_c.json"
THEME = "KineticSafety"
RING = sheets.RING
RADIAL_CLEARANCE_M = 5.0e-4
RING_FORWARD_CLEARANCE_M = 5.0e-4
POSES = (-115.0, -57.5, 0.0, 57.5, 115.0)
CROP = 460
GAP = 14


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def radial_of(obj, centre):
    matrix = obj.matrix_world
    values = [
        math.hypot((matrix @ v.co).x - centre.x, (matrix @ v.co).z - centre.z)
        for v in obj.data.vertices
    ]
    return min(values), max(values)


def trim_outer(obj, centre, limit):
    """Pull vertices past `limit` back to it, leaving the inner end alone."""
    matrix = obj.matrix_world
    inverse = matrix.inverted()
    moved = 0
    for vertex in obj.data.vertices:
        world = matrix @ vertex.co
        distance = math.hypot(world.x - centre.x, world.z - centre.z)
        if distance <= limit:
            continue
        direction = (
            (world.x - centre.x) / distance, (world.z - centre.z) / distance
        )
        world.x = centre.x + direction[0] * limit
        world.z = centre.z + direction[1] * limit
        vertex.co = inverse @ world
        moved += 1
    obj.data.update()
    return moved


def shot_and_project(rig, view, path, point):
    """Render, and say where a world point landed in the image."""
    azimuth, elevation = view
    camera, lights = review.build_rig(
        rig, rig["focus"], rig["radius"], azimuth, elevation, rig["lens"]
    )
    scene = bpy.context.scene
    projected = world_to_camera_view(scene, camera, point)
    review.render_to(path)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)
    width = scene.render.resolution_x
    height = scene.render.resolution_y
    return (
        int(round(projected.x * width)),
        int(round((1.0 - projected.y) * height)),
    )


def crop_around(path, pixel, size=CROP):
    image = review.load_rgba(path)
    height, width = image.shape[:2]
    # The buffer runs bottom-up; the projected pixel is measured from the top.
    row = height - pixel[1]
    top = max(0, min(height - size, row - size // 2))
    left = max(0, min(width - size, pixel[0] - size // 2))
    return image[top : top + size, left : left + size]


def has_subject(tile):
    """Is anything but the background in this panel?"""
    luma = tile[..., :3].mean(axis=2)
    background = float(np.median(luma))
    return float((luma > background + 0.05).mean())


def option_c(project_root, key, output_dir):
    bpy.ops.wm.open_mainfile(
        filepath=str(m2n7.revision_blend(project_root, key)), load_ui=False
    )
    m2n3r.strip_existing_rig()
    root = bpy.data.objects[m2n7.m2k.MODELS[key]["root"]]
    pivot = bpy.data.objects[m2n.MOTION["pivot"]]
    centre = pivot.matrix_world.translation.copy()
    needle = bpy.data.objects["needle"]
    ring = bpy.data.objects[RING]
    ticks = [
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name.startswith("kinetic_tick_")
    ]
    removed = [
        obj.name for obj in list(bpy.data.objects)
        if obj.type == "MESH" and obj.name.startswith("secondary_scale_")
    ]
    for name in removed:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.context.view_layer.update()

    ring_inner = radial_of(ring, centre)[0]
    limit = ring_inner - RADIAL_CLEARANCE_M
    before = max(radial_of(obj, centre)[1] for obj in ticks)
    trimmed = sum(trim_outer(obj, centre, limit) for obj in ticks)
    bpy.context.view_layer.update()
    after = max(radial_of(obj, centre)[1] for obj in ticks)

    row = {
        "secondary_removed": len(removed),
        "ring_inner_radius_mm": round(ring_inner * 1000.0, 4),
        "tick_outer_before_mm": round(before * 1000.0, 4),
        "tick_outer_after_mm": round(after * 1000.0, 4),
        "tick_outer_trim_mm": round((before - after) * 1000.0, 4),
        "vertices_moved": trimmed,
        "tick_ring_radial_clearance_mm": round((ring_inner - after) * 1000.0, 4),
    }
    row["tick_ring_min_3d_mm"] = round(
        (min(
            value for value in (sheets.min_distance(obj, ring) for obj in ticks)
            if value is not None
        ) or 0.0) * 1000.0, 4
    )
    # Can the ring come forward? Only as far as the needle allows, over travel.
    needle_front = sheets.depth_span(needle)[0]
    ring_front = sheets.depth_span(ring)[0]
    gap = sheets.sweep_min(root, pivot, needle, [ring], POSES)
    row["needle_ring_min_3d_before_mm"] = round((gap or 0.0) * 1000.0, 4)
    forward = 0.0
    if gap is not None and gap > RING_FORWARD_CLEARANCE_M:
        forward = gap - RING_FORWARD_CLEARANCE_M
        sheets.move_y(ring, -forward)
        bpy.context.view_layer.update()
    row["ring_moved_forward_mm"] = round(forward * 1000.0, 4)
    row["needle_ring_min_3d_after_mm"] = round(
        (sheets.sweep_min(root, pivot, needle, [ring], POSES) or 0.0) * 1000.0, 4
    )
    row["needle_front_minus_ring_front_mm"] = round(
        (sheets.depth_span(ring)[0] - sheets.depth_span(needle)[0]) * 1000.0, 4
    )
    row["needle_tick_min_3d_mm"] = round(
        (sheets.sweep_min(root, pivot, needle, ticks, POSES) or 0.0) * 1000.0, 4
    )
    dial = bpy.data.objects.get("kinetic_v6_dial_pan") or bpy.data.objects.get(
        "kinetic_polygon_bezel"
    )
    if dial is not None:
        row["dial_object"] = dial.name
        row["dial_ring_min_mm"] = round(
            (sheets.min_distance(dial, ring) or 0.0) * 1000.0, 4
        )
        values = [sheets.min_distance(dial, obj) for obj in ticks]
        values = [value for value in values if value is not None]
        row["dial_tick_min_mm"] = round(min(values) * 1000.0, 4) if values else None

    sheets.colour_scene()
    review.configure_scene()
    rig = m2n3r.rig_from(root)
    images = []
    for name, view, scale in (("front", (0.0, 6.0), 1.0), ("oblique", (40.0, 24.0), 0.5)):
        path = output_dir / f"Preview_{key}_M2n8_optionC_{name}.png"
        review.shot(dict(rig, radius=rig["radius"] * scale), rig["focus"],
                    rig["radius"] * scale, view, rig["lens"], path)
        images.append(path)
    return row, images


def round_sheet(project_root, output_dir):
    """The proven whole-model rig, cropped around the projected pivot."""
    key = "MeterRound"
    bpy.ops.wm.open_mainfile(
        filepath=str(m2n7.revision_blend(project_root, key)), load_ui=False
    )
    m2n3r.strip_existing_rig()
    root = bpy.data.objects[m2n7.m2k.MODELS[key]["root"]]
    pivot = bpy.data.objects[m2n.MOTION["pivot"]]
    point = pivot.matrix_world.translation.copy()
    pieces = sheets.split_needle(project_root)
    hidden = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj not in pieces:
            obj.hide_render = True
            hidden.append(obj.name)
    review.configure_scene()
    rig = m2n3r.rig_from(root)
    rig = dict(rig, radius=rig["radius"] * 0.5)
    states = [("C0", {"C0"}), ("C2", {"C2"}), ("C3", {"C3"}),
              ("C0+C2+C3", {"C0", "C2", "C3"})]
    tiles = []
    coverage = {}
    for name, keep in states:
        sheets.only(pieces, keep)
        row = []
        for view_name, view in (("front", (0.0, 6.0)), ("oblique", (44.0, 26.0))):
            path = output_dir / f"Preview_MeterRound_M2n8c_{name.replace('+','_')}_{view_name}.png"
            pixel = shot_and_project(rig, view, path, point)
            tile = crop_around(path, pixel)
            coverage[f"{name}/{view_name}"] = round(has_subject(tile), 5)
            row.append(tile)
        tiles.append(row)
    return tiles, coverage, [name for name, _ in states]


def assemble(tiles, labels, output_path):
    height, width = tiles[0][0].shape[:2]
    rows, columns = len(tiles), len(tiles[0])
    canvas = np.zeros(
        (rows * height + (rows - 1) * GAP, columns * width + (columns - 1) * GAP, 4),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for index, row in enumerate(tiles):
        top = (rows - 1 - index) * (height + GAP)
        for column, tile in enumerate(row):
            left = column * (width + GAP)
            canvas[top : top + height, left : left + width] = tile
    for index, row in enumerate(labels):
        for column, (title, subtitle) in enumerate(row):
            left = column * (width + GAP) + 12
            top = index * (height + GAP) + 12
            review.draw_label(canvas, title, left, top)
            if subtitle:
                review.draw_label(canvas, subtitle, left, top + 40,
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
        "phase": "M2n8-prework-C",
        "note": (
            "Option C (radial clearance) and a cropped Round cause sheet "
            "(alignment 217). Diagnostic copies only; nothing is saved."
        ),
        "sheets": {},
    }
    for key in ("MeterMedium", "MeterLarge"):
        row, images = option_c(project_root, key, output_dir)
        tiles = [[review.load_rgba(path) for path in images]]
        sheet = sheet_dir / f"ContactSheet_{key}_M2n8_optionC.png"
        assemble(
            tiles,
            [[("OPTION C", f"T-R {row['tick_ring_radial_clearance_mm']}MM RADIAL"),
              ("OPTION C", f"N-R {row['needle_ring_min_3d_after_mm']}MM")]],
            sheet,
        )
        payload["sheets"][key] = {
            "path": str(sheet), "sha256": m1.digest(sheet), "measurements": row
        }
        print(f"[Opus5M2n8C] {key}: {sheet.name} trim {row['tick_outer_trim_mm']} mm")

    tiles, coverage, states = round_sheet(project_root, output_dir)
    sheet = sheet_dir / "ContactSheet_MeterRound_M2n8_cause.png"
    assemble(
        tiles,
        [[(f"ROUND {name}", "FRONT"), (f"ROUND {name}", "OBLIQUE")] for name in states],
        sheet,
    )
    payload["sheets"]["MeterRound"] = {
        "path": str(sheet),
        "sha256": m1.digest(sheet),
        "panel_subject_fraction": coverage,
        "all_panels_have_subject": all(value > 0.005 for value in coverage.values()),
    }
    print(f"[Opus5M2n8C] Round: {sheet.name} coverage {coverage}")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
