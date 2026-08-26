"""Phase M2n8 pre-work: the three diagnostic sheets, and nothing else.

Alignment 215.1. Numbers have already settled why each model looks wrong; these
images are so the fix can be chosen by eye before any shape is committed.

* Round - the counterweight axis, with C0, C2, C3 alone and then together, each
  in its own colour. The three share a front plane at Y = -0.08050, which is
  what the headset and the Prefab Preview were both showing.
* Medium and Large - as delivered, then option A (secondary scale hidden, the
  primary ticks lifted clear of the cover ring, needle depth untouched), then
  option B (the same ticks, with the needle pulled back until it only just
  keeps its clearance).

Every offset that option A and B use is derived from the geometry, and the
clearances quoted are measured surface to surface afterwards, not assumed.

Nothing is saved. The revision Blends are opened read-only and edited only in
memory; the only files written are the images and one report.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n8_diagnostic_sheets.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_d3_solver_diagnostic as diag
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n3_review as m2n3r
import opus5_meter_m2n7_depth_revision as m2n7


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n8_diagnostic_sheets.json"
THEME = "KineticSafety"
GAP = 14
RING = "kinetic_v6_inner_armor_ring"
# Enough to read as "in front of" without opening a visible slot.
TICK_RING_CLEARANCE_M = 5.0e-4
COLOURS = {
    "needle": (0.86, 0.30, 0.22, 1.0),
    "primary": (0.25, 0.55, 0.90, 1.0),
    "secondary": (0.95, 0.78, 0.20, 1.0),
    "ring": (0.30, 0.72, 0.42, 1.0),
    "other": (0.34, 0.35, 0.37, 1.0),
    "C0": (0.90, 0.35, 0.25, 1.0),
    "C1": (0.95, 0.80, 0.25, 1.0),
    "C2": (0.30, 0.60, 0.92, 1.0),
    "C3": (0.35, 0.80, 0.45, 1.0),
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def flat_material(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = colour
        bsdf.inputs["Roughness"].default_value = 0.55
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
    return material


def paint(obj, key):
    obj.data.materials.clear()
    obj.data.materials.append(flat_material(f"M2n8_{key}", COLOURS[key]))


def role_of(name):
    if name.startswith("kinetic_tick_"):
        return "primary"
    if name.startswith("secondary_scale_"):
        return "secondary"
    if name == RING:
        return "ring"
    if name == "needle":
        return "needle"
    return "other"


def colour_scene():
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            paint(obj, role_of(obj.name))


def depth_span(obj):
    matrix = obj.matrix_world
    values = [(matrix @ vertex.co).y for vertex in obj.data.vertices]
    return min(values), max(values)


def move_y(obj, delta):
    matrix = obj.matrix_world
    inverse = matrix.inverted()
    for vertex in obj.data.vertices:
        world = matrix @ vertex.co
        world.y += delta
        vertex.co = inverse @ world
    obj.data.update()


def min_distance(first, second, tolerance=0.02):
    """Surface to surface, using the approved closest-pair routine."""
    import opus5_contact as contact

    a = m1.world_triangles(first)
    b = m1.world_triangles(second)
    pairs = contact.candidate_pairs(
        a, b, m1.trees(first)[0], m1.trees(second)[0], tolerance=tolerance
    )
    if not pairs:
        return None
    best = None
    for i, j in pairs:
        found = diag.closest_pair(a[i], b[j])
        if best is None or found[0] < best:
            best = found[0]
    return best


def sweep_min(root, pivot, mover, statics, poses):
    base = pivot.rotation_euler.copy()
    best = None
    try:
        for degrees in poses:
            pivot.rotation_euler[1] = base[1] + math.radians(degrees)
            bpy.context.view_layer.update()
            for static in statics:
                found = min_distance(mover, static)
                if found is not None and (best is None or found < best):
                    best = found
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return best


def rig_for(root, focus_radius_scale, focus=None):
    rig = m2n3r.rig_from(root)
    if focus is not None:
        rig = dict(rig, focus=focus)
    return dict(rig, radius=rig["radius"] * focus_radius_scale)


def shot(rig, view, path):
    review.shot(rig, rig["focus"], rig["radius"], view, rig["lens"], path)
    return path


def compose(rows, output_path, columns):
    tiles = [[review.load_rgba(path) for path in row] for row in rows]
    height, width = tiles[0][0].shape[:2]
    count = len(tiles)
    canvas = np.zeros(
        (count * height + (count - 1) * GAP, columns * width + (columns - 1) * GAP, 4),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for index, row in enumerate(tiles):
        # Blender's buffers run bottom-up; captions are placed from the top.
        top = (count - 1 - index) * (height + GAP)
        for column, tile in enumerate(row):
            canvas[top : top + height, column * (width + GAP) :
                   column * (width + GAP) + width] = tile
    return canvas, height, width


def label_rows(canvas, height, width, labels):
    for index, row in enumerate(labels):
        for column, (title, subtitle) in enumerate(row):
            left = column * (width + GAP) + 14
            top = index * (height + GAP) + 14
            review.draw_label(canvas, title, left, top)
            if subtitle:
                review.draw_label(
                    canvas, subtitle, left, top + 42, colour=(0.72, 0.78, 0.86)
                )


def split_needle(project_root):
    """Round's needle, as four separately coloured objects."""
    needle = bpy.data.objects["needle"]
    mesh = needle.data
    work = bmesh.new()
    work.from_mesh(mesh)
    work.verts.ensure_lookup_table()
    seen = set()
    groups = []
    for vertex in work.verts:
        if vertex.index in seen:
            continue
        stack = [vertex]
        group = set()
        while stack:
            current = stack.pop()
            if current.index in seen:
                continue
            seen.add(current.index)
            group.add(current.index)
            for edge in current.link_edges:
                stack.append(edge.other_vert(current))
        groups.append(group)
    groups.sort(key=len, reverse=True)
    made = []
    for index, group in enumerate(groups):
        piece = bmesh.new()
        mapping = {}
        for vertex_index in sorted(group):
            mapping[vertex_index] = piece.verts.new(work.verts[vertex_index].co)
        piece.verts.ensure_lookup_table()
        for face in work.faces:
            if all(vertex.index in group for vertex in face.verts):
                piece.faces.new([mapping[vertex.index] for vertex in face.verts])
        data = bpy.data.meshes.new(f"C{index}")
        piece.to_mesh(data)
        piece.free()
        obj = bpy.data.objects.new(f"C{index}", data)
        bpy.context.collection.objects.link(obj)
        obj.parent = needle.parent
        obj.matrix_world = needle.matrix_world.copy()
        paint(obj, f"C{index}")
        made.append(obj)
    work.free()
    bpy.data.objects.remove(needle, do_unlink=True)
    bpy.context.view_layer.update()
    return made


def only(objects, keep):
    for obj in objects:
        obj.hide_render = obj.name not in keep


def round_sheet(project_root, output_dir):
    key = "MeterRound"
    bpy.ops.wm.open_mainfile(
        filepath=str(m2n7.revision_blend(project_root, key)), load_ui=False
    )
    m2n3r.strip_existing_rig()
    root = bpy.data.objects[m2n7.m2k.MODELS[key]["root"]]
    pivot = bpy.data.objects[m2n.MOTION["pivot"]]
    centre = pivot.matrix_world.translation.copy()
    pieces = split_needle(project_root)
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj not in pieces:
            obj.hide_render = True
    review.configure_scene()
    # A tight rig on the axis: the shared front plane is a few millimetres wide.
    rig = m2n3r.rig_from(root)
    rig = dict(rig, focus=(centre.x, centre.y - 0.004, centre.z), radius=0.075,
               lens=95.0, light_scale=0.030,
               energy_scale=(0.030 / m2n3r.REFERENCE_LIGHT_SCALE) ** 2)
    states = [
        ("C0", {"C0"}), ("C2", {"C2"}), ("C3", {"C3"}),
        ("C0+C2+C3", {"C0", "C2", "C3"}),
    ]
    rows = []
    labels = []
    written = []
    for name, keep in states:
        only(pieces, keep)
        row = []
        for view_name, view in (("front", (0.0, 4.0)), ("oblique", (52.0, 26.0))):
            path = output_dir / f"Preview_MeterRound_M2n8_round_{name.replace('+','_')}_{view_name}.png"
            shot(rig, view, path)
            row.append(path)
            written.append(path)
        rows.append(row)
        labels.append([(f"ROUND {name}", "FRONT"), (f"ROUND {name}", "OBLIQUE")])
    canvas, height, width = compose(rows, None, 2)
    label_rows(canvas, height, width, labels)
    sheet = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / "contact_sheets"
        / "ContactSheet_MeterRound_M2n8_cause.png"
    )
    review.save_rgba(canvas, sheet)
    return sheet, written


def scale_sheet(project_root, key, output_dir):
    """Delivered, option A and option B, front and oblique."""
    measurements = {}
    written = []
    rows = []
    labels = []
    for state in ("current", "A", "B"):
        bpy.ops.wm.open_mainfile(
            filepath=str(m2n7.revision_blend(project_root, key)), load_ui=False
        )
        m2n3r.strip_existing_rig()
        root = bpy.data.objects[m2n7.m2k.MODELS[key]["root"]]
        pivot = bpy.data.objects[m2n.MOTION["pivot"]]
        needle = bpy.data.objects["needle"]
        ring = bpy.data.objects[RING]
        ticks = [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and obj.name.startswith("kinetic_tick_")
        ]
        secondary = [
            obj
            for obj in bpy.data.objects
            if obj.type == "MESH" and obj.name.startswith("secondary_scale_")
        ]
        row = {"state": state}
        if state != "current":
            for obj in secondary:
                obj.hide_render = True
            # The room comes from the ring, not the ticks. Lifting the ticks
            # forward instead drives them straight into the needle, which is
            # already the frontmost thing here - measured at 0.0 mm.
            ring_front = depth_span(ring)[0]
            tick_back = max(depth_span(obj)[1] for obj in ticks)
            recess = (tick_back - ring_front) + TICK_RING_CLEARANCE_M
            move_y(ring, recess)
            bpy.context.view_layer.update()
            row["ring_recess_mm"] = round(recess * 1000.0, 4)
        if state == "B":
            # Pull the needle back until it only just keeps the D-3 floor.
            floor = m2n7.m2n6.CLEARANCE_FLOOR_MM[key] / 1000.0
            poses = (-115.0, -57.5, 0.0, 57.5, 115.0)
            measured = sweep_min(root, pivot, needle, ticks, poses)
            if measured is not None and measured > floor:
                pull = measured - floor
                move_y(needle, pull)
                bpy.context.view_layer.update()
                row["needle_pulled_back_mm"] = round(pull * 1000.0, 4)
        poses = (-115.0, -57.5, 0.0, 57.5, 115.0)
        row["needle_to_tick_min_mm"] = round(
            (sweep_min(root, pivot, needle, ticks, poses) or 0.0) * 1000.0, 4
        )
        visible_ticks = [obj for obj in ticks if not obj.hide_render]
        gaps = [min_distance(obj, ring) for obj in visible_ticks]
        gaps = [value for value in gaps if value is not None]
        row["tick_to_ring_min_mm"] = round(min(gaps) * 1000.0, 4) if gaps else None
        row["needle_in_front_of_ring_mm"] = round(
            (depth_span(ring)[0] - depth_span(needle)[0]) * 1000.0, 4
        )
        measurements[state] = row

        colour_scene()
        review.configure_scene()
        rig = m2n3r.rig_from(root)
        images = []
        for view_name, view, scale in (
            ("front", (0.0, 6.0), 1.0), ("oblique", (40.0, 24.0), 0.5)
        ):
            path = output_dir / f"Preview_{key}_M2n8_{state}_{view_name}.png"
            shot(dict(rig, radius=rig["radius"] * scale), view, path)
            images.append(path)
            written.append(path)
        rows.append(images)
        title = {"current": "CURRENT M2N7", "A": "OPTION A", "B": "OPTION B"}[state]
        labels.append(
            [
                (title, f"N-T {row['needle_to_tick_min_mm']}MM"),
                (title, f"T-R {row['tick_to_ring_min_mm']}MM"),
            ]
        )
    canvas, height, width = compose(rows, None, 2)
    label_rows(canvas, height, width, labels)
    sheet = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / "contact_sheets"
        / f"ContactSheet_{key}_M2n8_options.png"
    )
    review.save_rgba(canvas, sheet)
    return sheet, written, measurements


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    (project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "contact_sheets").mkdir(
        parents=True, exist_ok=True
    )
    payload = {
        "phase": "M2n8-prework",
        "note": (
            "Diagnostic sheets only (alignment 215.1). Revision Blends are "
            "opened read-only and edited in memory; nothing is saved."
        ),
        "colours": {key: list(value) for key, value in COLOURS.items()},
        "sheets": {},
    }
    sheet, _ = round_sheet(project_root, output_dir)
    payload["sheets"]["MeterRound"] = {
        "path": str(sheet),
        "sha256": m1.digest(sheet),
        "states": ["C0", "C2", "C3", "C0+C2+C3"],
    }
    print(f"[Opus5M2n8Sheets] Round: {sheet.name}")
    for key in ("MeterMedium", "MeterLarge"):
        sheet, _, measurements = scale_sheet(project_root, key, output_dir)
        payload["sheets"][key] = {
            "path": str(sheet),
            "sha256": m1.digest(sheet),
            "measurements": measurements,
        }
        print(f"[Opus5M2n8Sheets] {key}: {sheet.name}")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
