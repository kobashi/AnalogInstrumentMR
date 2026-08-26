"""Trend Monitor, Orbital Analog: the instrument body, and nothing that moves.

Alignment 230.1. Codex draws the traces; this is the thing they are drawn on -
a housing, a bezel, and a display surface recessed far enough behind it that no
depth buffer has to choose between them.

The contract this file has to keep (alignment 230.2):

* mount plane at local Z = 0, the display facing local +Z, origin at the centre
  of the mount, scale (1, 1, 1)
* envelope within 0.44 x 0.28 x 0.10 m, display opening at least 0.36 x 0.18 m
* three renderers at most, two material roles, no collider, no moving part
* `display_surface` its own object, so Unity can find the screen without
  guessing which face it is

Nothing is baked into the display: no graph, no numbers, no legend, no channel
colour. The screen is a flat, unbroken plane with its normal along +Z.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_trend_monitor_prototype.py -- \
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


THEME = "OrbitalAnalog"
BLEND = "ArtSource/Blender/BrushUp/Opus5/OrbitalAnalog/BL_TrendMonitor_OrbitalAnalog_V6_Opus5_P1_Retopo.blend"
OUTPUT = "ArtSource/Blender/BrushUp/Opus5/trend_monitor_prototype.json"
ROOT = "PF_Visual_TrendMonitor_OrbitalAnalog_V6"

# Every dimension in metres, and every one of them inside alignment 230.2.
# The opening is nearly as wide as the body, so the body takes as much of the
# envelope as it is allowed: that is what buys a bezel rail wide enough to
# carry anything, and a housing margin outside it.
BODY = (0.436, 0.272)
BODY_DEPTH = 0.050
BEZEL_DEPTH = 0.006
BEZEL_INSET = 0.014
OPENING = (0.372, 0.192)
DISPLAY = (0.368, 0.188)
# The screen sits this far behind the bezel's front face. Far enough that it
# reads as recessed and nothing can co-plane with the frame.
DISPLAY_RECESS = 0.016
CORNER_RADIUS = 0.014
CORNER_SEGMENTS = 4
# Fasteners sit on the bezel rail's corners and stand proud of it. Buried in
# the housing margin they were geometrically present and visually absent.
FASTENER_RADIUS = 0.006
FASTENER_DEPTH = 0.004
FASTENER_AT = (0.191, 0.105)
# Likewise the readout: a raised bar on the bezel's bottom rail. An inset one
# would need a pocket cut into the bezel, and without it the bar simply sits
# inside solid material where nothing can see it.
READOUT = (0.260, 0.009)
READOUT_HEIGHT = 0.0025
READOUT_CENTRE_Y = -0.108


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def rounded_rectangle(width, height, radius, segments):
    """Outline points, counter-clockwise, with rounded corners."""
    half_x = width / 2.0 - radius
    half_y = height / 2.0 - radius
    points = []
    for corner_x, corner_y, start in (
        (half_x, half_y, 0.0), (-half_x, half_y, 90.0),
        (-half_x, -half_y, 180.0), (half_x, -half_y, 270.0),
    ):
        for step in range(segments + 1):
            angle = math.radians(start + 90.0 * step / segments)
            points.append(
                (corner_x + radius * math.cos(angle),
                 corner_y + radius * math.sin(angle))
            )
    return points


def slab(name, outline, near_z, far_z, material):
    """A closed prism between two Z planes, from one outline."""
    mesh = bpy.data.meshes.new(name)
    work = bmesh.new()
    lower = [work.verts.new((x, y, near_z)) for x, y in outline]
    upper = [work.verts.new((x, y, far_z)) for x, y in outline]
    count = len(outline)
    for index in range(count):
        work.faces.new(
            (lower[index], lower[(index + 1) % count],
             upper[(index + 1) % count], upper[index])
        )
    work.faces.new(list(reversed(lower)))
    work.faces.new(upper)
    bmesh.ops.triangulate(
        work, faces=work.faces[:], quad_method="FIXED", ngon_method="EAR_CLIP"
    )
    work.normal_update()
    work.to_mesh(mesh)
    work.free()
    mesh.materials.append(material)
    return mesh


def frame(name, outer, inner, near_z, far_z, material):
    """A closed ring between two outlines - the bezel."""
    mesh = bpy.data.meshes.new(name)
    work = bmesh.new()
    count = len(outer)
    outer_low = [work.verts.new((x, y, near_z)) for x, y in outer]
    outer_high = [work.verts.new((x, y, far_z)) for x, y in outer]
    inner_low = [work.verts.new((x, y, near_z)) for x, y in inner]
    inner_high = [work.verts.new((x, y, far_z)) for x, y in inner]
    for index in range(count):
        nxt = (index + 1) % count
        work.faces.new((outer_low[index], outer_low[nxt], outer_high[nxt], outer_high[index]))
        work.faces.new((inner_high[index], inner_high[nxt], inner_low[nxt], inner_low[index]))
        work.faces.new((outer_high[index], outer_high[nxt], inner_high[nxt], inner_high[index]))
        work.faces.new((inner_low[index], inner_low[nxt], outer_low[nxt], outer_low[index]))
    bmesh.ops.triangulate(
        work, faces=work.faces[:], quad_method="FIXED", ngon_method="EAR_CLIP"
    )
    work.normal_update()
    work.to_mesh(mesh)
    work.free()
    mesh.materials.append(material)
    return mesh


def plane(name, width, height, z, material):
    """The screen: one flat quad, normal along +Z."""
    mesh = bpy.data.meshes.new(name)
    half_x, half_y = width / 2.0, height / 2.0
    mesh.from_pydata(
        [(-half_x, -half_y, z), (half_x, -half_y, z),
         (half_x, half_y, z), (-half_x, half_y, z)],
        [], [(0, 1, 2, 3)],
    )
    mesh.validate()
    mesh.update()
    work = bmesh.new()
    work.from_mesh(mesh)
    bmesh.ops.triangulate(work, faces=work.faces[:], quad_method="FIXED")
    work.to_mesh(mesh)
    work.free()
    mesh.materials.append(material)
    return mesh


def make_material(name, colour, emissive=False):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = colour
        bsdf.inputs["Roughness"].default_value = 0.34 if emissive else 0.58
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
    return material


def join_into(target, others):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in others:
        obj.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    bpy.context.view_layer.update()
    return target


def build():
    bpy.ops.wm.read_homefile(use_empty=True)
    collection = bpy.context.collection
    opaque = make_material("MAT_OrbitalAnalog_Monitor_Solid_Opaque", (0.055, 0.058, 0.063, 1.0))
    readout = make_material(
        "MAT_OrbitalAnalog_Monitor_Solid_Readout", (0.030, 0.115, 0.135, 1.0), True
    )

    root = bpy.data.objects.new(ROOT, None)
    collection.objects.link(root)
    root["opus5_id"] = ROOT

    body_outline = rounded_rectangle(*BODY, CORNER_RADIUS, CORNER_SEGMENTS)
    housing = bpy.data.objects.new(
        "housing", slab("housing", body_outline, 0.0, BODY_DEPTH, opaque)
    )
    collection.objects.link(housing)

    bezel_outer = rounded_rectangle(
        BODY[0] - BEZEL_INSET * 2, BODY[1] - BEZEL_INSET * 2,
        CORNER_RADIUS - BEZEL_INSET, CORNER_SEGMENTS,
    )
    bezel_inner = rounded_rectangle(*OPENING, CORNER_RADIUS * 0.5, CORNER_SEGMENTS)
    bezel = bpy.data.objects.new(
        "bezel",
        frame("bezel", bezel_outer, bezel_inner, BODY_DEPTH, BODY_DEPTH + BEZEL_DEPTH, opaque),
    )
    collection.objects.link(bezel)

    fasteners = []
    for sign_x in (-1.0, 1.0):
        for sign_y in (-1.0, 1.0):
            outline = [
                (
                    sign_x * FASTENER_AT[0] + FASTENER_RADIUS * math.cos(math.radians(a)),
                    sign_y * FASTENER_AT[1] + FASTENER_RADIUS * math.sin(math.radians(a)),
                )
                for a in range(0, 360, 45)
            ]
            piece = bpy.data.objects.new(
                "fastener",
                slab(
                    "fastener", outline,
                    BODY_DEPTH + BEZEL_DEPTH,
                    BODY_DEPTH + BEZEL_DEPTH + FASTENER_DEPTH, opaque,
                ),
            )
            collection.objects.link(piece)
            fasteners.append(piece)

    static_opaque = join_into(housing, [bezel] + fasteners)
    static_opaque.name = "static_opaque"
    static_opaque.parent = root
    static_opaque["opus5_id"] = "static_opaque"

    strip = bpy.data.objects.new(
        "static_readout",
        slab(
            "static_readout",
            rounded_rectangle(*READOUT, 0.0035, 2),
            BODY_DEPTH + BEZEL_DEPTH,
            BODY_DEPTH + BEZEL_DEPTH + READOUT_HEIGHT,
            readout,
        ),
    )
    collection.objects.link(strip)
    strip.location = (0.0, READOUT_CENTRE_Y, 0.0)
    strip.parent = root
    strip["opus5_id"] = "static_readout"

    screen_z = BODY_DEPTH + BEZEL_DEPTH - DISPLAY_RECESS
    display = bpy.data.objects.new(
        "display_surface", plane("display_surface", *DISPLAY, screen_z, readout)
    )
    collection.objects.link(display)
    display.parent = root
    display["opus5_id"] = "display_surface"
    bpy.context.view_layer.update()
    return root, static_opaque, strip, display, screen_z


def measure(root, display):
    rows = {}
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        rows[obj.name] = {
            "triangles": len(obj.data.loop_triangles),
            "vertices": len(obj.data.vertices),
            "materials": [m.name for m in obj.data.materials if m],
            "bounds_min": [round(min(p[i] for p in points), 6) for i in range(3)],
            "bounds_max": [round(max(p[i] for p in points), 6) for i in range(3)],
        }
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in root.children_recursive
        if obj.type == "MESH"
        for corner in obj.bound_box
    ]
    mesh = display.data
    mesh.calc_loop_triangles()
    normal_matrix = display.matrix_world.to_3x3().inverted_safe().transposed()
    normals = {
        tuple(round(v, 6) for v in (normal_matrix @ t.normal).normalized())
        for t in mesh.loop_triangles
    }
    return {
        "objects": rows,
        "triangles_total": sum(row["triangles"] for row in rows.values()),
        "bounds": {
            "min": [round(min(p[i] for p in points), 6) for i in range(3)],
            "max": [round(max(p[i] for p in points), 6) for i in range(3)],
        },
        "display_normals": sorted(normals),
        "display_size_m": list(DISPLAY),
        "display_opening_m": list(OPENING),
        "display_recess_from_bezel_m": DISPLAY_RECESS,
    }


VIEWS = {
    "front": (0.0, 0.0),
    "oblique_left": (-38.0, 18.0),
    "oblique_right": (38.0, 18.0),
    "side": (78.0, 6.0),
}


def camera_at(focus, radius, azimuth_deg, elevation_deg):
    """This instrument faces +Z, so the orbit is around Y with +Z as front."""
    azimuth = math.radians(azimuth_deg)
    elevation = math.radians(elevation_deg)
    return (
        focus[0] + radius * math.sin(azimuth) * math.cos(elevation),
        focus[1] + radius * math.sin(elevation),
        focus[2] + radius * math.cos(azimuth) * math.cos(elevation),
    )


def shot(focus, radius, view, lens, scale, path):
    azimuth, elevation = view
    bpy.ops.object.camera_add(location=camera_at(focus, radius, azimuth, elevation))
    camera = bpy.context.object
    camera.data.lens = lens
    review.point_at(camera, focus)
    bpy.context.scene.camera = camera
    lights = []
    for name, offset, energy in (
        ("Key", (scale * 1.5, scale * 1.6, scale * 2.2), 9.0),
        ("Fill", (-scale * 2.2, scale * 0.6, scale * 1.8), 3.6),
        ("Rim", (0.0, -scale * 1.4, -scale * 1.6), 5.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = scale * 2.0
        light = bpy.data.objects.new(name, data)
        light.location = (
            focus[0] + offset[0], focus[1] + offset[1], focus[2] + offset[2]
        )
        bpy.context.collection.objects.link(light)
        review.point_at(light, focus)
        lights.append(light)
    review.render_to(path)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)


def contact_sheet(paths, labels, output_path):
    tiles = [review.load_rgba(path) for path in paths]
    height, width = tiles[0].shape[:2]
    gap = 16
    canvas = np.zeros((2 * height + gap, 2 * width + gap, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        row, column = divmod(index, 2)
        top = (1 - row) * (height + gap)
        canvas[top : top + height, column * (width + gap) :
               column * (width + gap) + width] = tile
    for index, label in enumerate(labels):
        row, column = divmod(index, 2)
        review.draw_label(
            canvas, label, column * (width + gap) + 16, row * (height + gap) + 16
        )
    review.save_rgba(canvas, output_path)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    root, static_opaque, strip, display, screen_z = build()
    report = measure(root, display)

    blend = project_root / BLEND
    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)

    review.configure_scene()
    focus = (0.0, 0.0, BODY_DEPTH * 0.5)
    radius = 0.78
    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    images = []
    for name, view in VIEWS.items():
        path = output_dir / f"Preview_TrendMonitor_{THEME}_P1_{name}.png"
        shot(focus, radius, view, 55.0, 0.30, path)
        images.append(path)
    sheet_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    sheet = sheet_dir / f"ContactSheet_TrendMonitor_{THEME}_P1.png"
    contact_sheet(images, [name.upper().replace("_", " ") for name in VIEWS], sheet)

    payload = {
        "phase": "TrendMonitor-P1",
        "theme": THEME,
        "blend": str(blend.relative_to(project_root)),
        "blend_sha256": m1.digest(blend),
        "blender_version": bpy.app.version_string,
        "root": ROOT,
        "renderers": sorted(
            obj.name for obj in root.children_recursive if obj.type == "MESH"
        ),
        "screen_z_m": round(screen_z, 6),
        "contact_sheet": str(sheet.relative_to(project_root)),
        "contact_sheet_sha256": m1.digest(sheet),
        "images": [str(path.relative_to(project_root)) for path in images],
        "contract": {
            "envelope_limit_m": [0.44, 0.28, 0.10],
            "display_opening_minimum_m": [0.36, 0.18],
            "mount_plane": "local Z = 0",
            "display_normal": "local +Z",
            "origin": "mount centre, scale (1, 1, 1)",
        },
    }
    payload.update(report)
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"[TrendMonitor] {len(payload['renderers'])} renderers, "
        f"{payload['triangles_total']} triangles, bounds {payload['bounds']}"
    )
    print(f"[TrendMonitor] display normals {payload['display_normals']}")


if __name__ == "__main__":
    main()
