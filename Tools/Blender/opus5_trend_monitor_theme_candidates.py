"""Trend Monitor T1 candidates: three themes that differ by skeleton.

The shipped three monitors are one shape with three parameter sets. Every one
of them is a rounded rectangular slab, a rounded rectangular bezel frame on
top of it, and a flat screen; Forge Brass adds a retaining ring and six lugs
and Kinetic Safety adds a shroud and four guards, but the skeleton underneath
is the same part list with different numbers. That is what this candidate
replaces.

The runtime contract does not move, and nothing here is allowed to make the
signal path theme-dependent:

* `display_surface` stays one flat quad, 0.368 x 0.188 m, normal local +Z,
  two triangles, at each theme's *existing* screen Z - 0.0400, 0.0530 and
  0.0570 - so the overlay lands exactly where it lands today
* object names stay `static_opaque`, `static_readout`, `display_surface`
* three renderers, two material roles, mount plane at local Z = 0

What changes is the instrument around the screen, at the level of what parts
exist rather than how big they are:

* Orbital Analog - one sealed shell with a stepped shoulder and no applied
  bezel at all. Nothing stands proud of the front face; the mounting register
  is on the back.
* Forge Brass - an octagonal cast body with a *wider* bolted flange behind it,
  so the flange reads outside the body's own silhouette, plus a separate
  screen retainer and six bolt bosses.
* Kinetic Safety - a square-cornered chassis carrying an external cage: four
  corner guard blocks, two side rails and a hood that overhangs the top of the
  screen. The cage does the retaining; there is no bezel frame.

The audit stage also answers a question the shipped report does not ask: with
the housing built as a solid slab and the screen embedded inside it at a lower
Z, is the screen actually visible from the front? T1 builds the surround as a
ring with a real opening and a separate back panel, and checks both by ray.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_trend_monitor_theme_candidates.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_toggle_fbx_handoff as toggle
import opus5_trend_monitor_prototype as p1
import opus5_trend_monitor_themes as production

TREE = "ArtSource/Blender/BrushUp/Opus5/TrendMonitorThemes/T1"
OUTPUT = f"{TREE}/trend_monitor_theme_candidates_t1.json"
PRODUCTION_REPORT = "ArtSource/Blender/BrushUp/Opus5/trend_monitor_themes.json"

# Frozen runtime contract, taken from the shipped report rather than retyped.
OPENING = production.OPENING            # (0.372, 0.192)
DISPLAY = production.DISPLAY            # (0.368, 0.188)
ENVELOPE_LIMIT = production.ENVELOPE_LIMIT
OPENING_MINIMUM = production.OPENING_MINIMUM
SCREEN_Z = {"OrbitalAnalog": 0.0400, "ForgeBrass": 0.0530,
            "KineticSafety": 0.0570}
THEME_ORDER = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
COLOURS = {theme: (production.THEMES[theme]["opaque_colour"],
                   production.THEMES[theme]["readout_colour"])
           for theme in THEME_ORDER}

# One camera for every theme and every stage, so the sheets compare.
FIXED_FOCUS = (0.0, 0.0, 0.030)
FIXED_RADIUS = 0.78
FIXED_LENS = 55.0
FIXED_SCALE = 0.30


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def octagon(width, height, chamfer):
    """A chamfered rectangle - Forge Brass's outline, not a rounded one."""
    hx, hy = width / 2.0, height / 2.0
    return [
        (hx, hy - chamfer), (hx - chamfer, hy),
        (-hx + chamfer, hy), (-hx, hy - chamfer),
        (-hx, -hy + chamfer), (-hx + chamfer, -hy),
        (hx - chamfer, -hy), (hx, -hy + chamfer),
    ]


def square_rect(width, height, radius=0.0020):
    """Kinetic Safety's outline: square enough to read as cut plate."""
    return p1.rounded_rectangle(width, height, radius, 1)


def rounded(width, height, radius, segments=p1.CORNER_SEGMENTS):
    return p1.rounded_rectangle(width, height, radius, segments)


def ring(name, outer, inner, near_z, far_z, material):
    """p1.frame with the pairing it silently assumes actually checked.

    p1.frame walks `range(len(outer))` and indexes `inner` with the same
    counter, so an outer built with one corner-segment count and an inner
    built with another produces a ring stitched from the first N points of a
    longer outline - a front face that covers the opening instead of a hole.
    The first T1 build did exactly that on two themes and the screen was
    invisible from the front while every other measure passed.
    """
    if len(outer) != len(inner):
        raise SystemExit(
            f"[T1] {name}: frame outlines must have equal point counts, "
            f"got outer {len(outer)} and inner {len(inner)}")
    return p1.frame(name, outer, inner, near_z, far_z, material)


def opening_outline(segments):
    """The fixed opening, emitted with a matching corner-segment count."""
    return p1.rounded_rectangle(OPENING[0], OPENING[1], 0.0040, segments)


def box_outline(centre, size, radius=0.0):
    if radius <= 0.0:
        hx, hy = size[0] / 2.0, size[1] / 2.0
        return [(centre[0] + x, centre[1] + y)
                for x, y in ((hx, hy), (-hx, hy), (-hx, -hy), (hx, -hy))]
    return [(centre[0] + x, centre[1] + y)
            for x, y in p1.rounded_rectangle(size[0], size[1], radius, 2)]


# ---------------------------------------------------------------------------
# the three skeletons
# ---------------------------------------------------------------------------

def build_orbital_analog(opaque, readout):
    """One sealed shell. Nothing applied to the front, register on the back."""
    screen_z = SCREEN_Z["OrbitalAnalog"]
    body = rounded(0.4360, 0.2720, 0.0140)
    parts = [
        ("back_panel", p1.slab("back_panel", body, 0.0055, 0.0300, opaque)),
        ("surround_lower", ring(
            "surround_lower", body, opening_outline(p1.CORNER_SEGMENTS),
            0.0300, 0.0460, opaque)),
        # The shoulder: a second ring stepped in, so the shell reads as one
        # moulding drawn back towards the screen rather than a bezel laid on.
        ("surround_shoulder", ring(
            "surround_shoulder", rounded(0.4120, 0.2500, 0.0200),
            opening_outline(p1.CORNER_SEGMENTS), 0.0460, 0.0560, opaque)),
        # Mounting register on the back face, invisible from the room.
        # A plinth in front of the mount plane, not behind it: the contract
        # puts min Z at 0 and a register hanging to -0.004 breaks it.
        ("rear_plinth", p1.slab(
            "rear_plinth", rounded(0.4040, 0.2400, 0.0120),
            0.0000, 0.0055, opaque)),
    ]
    accent = [("accent_bar", p1.slab(
        "accent_bar", box_outline((0.0, -0.1080), (0.2600, 0.0090), 0.0035),
        0.0560, 0.0585, readout))]
    return parts, accent, screen_z, {
        "intent": ("one sealed moulded shell: a stepped shoulder draws the "
                   "front face back to the screen, so there is no applied "
                   "bezel and no part stands proud of the front"),
        "mounting": ("rear plinth at Z 0.000..0.0055, 32 mm inside the "
                     "shell outline, engaged by the panel cut-out; no "
                     "front fastener"),
        "maintainability": ("screen reached from the back after the register "
                            "is released; nothing to remove from the front"),
        "silhouette": "soft rounded rectangle, stepped shoulder, no protrusion",
    }


def build_forge_brass(opaque, readout):
    """Octagonal cast body on a wider bolted flange, with a screen retainer."""
    screen_z = SCREEN_Z["ForgeBrass"]
    body = octagon(0.4000, 0.2400, 0.0440)
    flange = octagon(0.4360, 0.2720, 0.0520)
    parts = [
        ("back_panel", p1.slab("back_panel", body, 0.0000, 0.0420, opaque)),
        # Wider than the body it carries, so the flange is outside the body's
        # own silhouette instead of being a thicker version of it.
        # Down to the mount plane: a flange bolted to the panel, not a plate
        # hanging in mid air off the side of the body, which is what the
        # first pass rendered.
        ("flange", ring(
            "flange", flange, octagon(0.3760, 0.2160, 0.0400),
            0.0000, 0.0480, opaque)),
        ("surround", ring(
            "surround", body, opening_outline(1), 0.0420, 0.0620, opaque)),
        ("retainer", ring(
            "retainer", octagon(0.3920, 0.2320, 0.0400),
            p1.rounded_rectangle(OPENING[0] + 0.0060, OPENING[1] + 0.0060,
                                 0.0040, 1),
            0.0620, 0.0690, opaque)),
    ]
    for index, (x, y) in enumerate((
            (-0.2020, 0.0), (0.2020, 0.0),
            (-0.1240, 0.1230), (0.1240, 0.1230),
            (-0.1240, -0.1230), (0.1240, -0.1230))):
        parts.append((f"bolt_boss_{index}", p1.slab(
            f"bolt_boss_{index}",
            [(x + 0.0110 * math.cos(math.radians(a)),
              y + 0.0110 * math.sin(math.radians(a)))
             for a in range(0, 360, 60)],
            0.0480, 0.0560, opaque)))
    accent = [
        (f"chart_slit_{index}", p1.slab(
            f"chart_slit_{index}",
            box_outline((offset, -0.1120), (0.0700, 0.0070), 0.0028),
            0.0690, 0.0710, readout))
        for index, offset in enumerate((-0.0900, 0.0, 0.0900))]
    return parts, accent, screen_z, {
        "intent": ("cast octagonal body bolted to a flange that is wider than "
                   "it: the perimeter is a separate structural part, read as "
                   "hardware rather than as a moulding"),
        "mounting": ("six bolt bosses through the flange at the octagon's "
                     "flats and corners"),
        "maintainability": ("screen released by lifting the retainer only; "
                            "the flange and its bolts stay in the panel"),
        "silhouette": ("octagonal, deepest of the three, flange standing "
                       "outside the body outline"),
    }


def build_kinetic_safety(opaque, readout):
    """Square-cornered chassis inside an external cage, with a hood."""
    screen_z = SCREEN_Z["KineticSafety"]
    body = square_rect(0.4280, 0.2640)
    parts = [
        ("back_panel", p1.slab("back_panel", body, 0.0000, 0.0460, opaque)),
        ("surround", ring(
            "surround", body, opening_outline(1), 0.0460, 0.0620, opaque)),
        # The cage: the guards and rails retain the screen, so there is no
        # bezel ring at all.
        # A visor: it starts at the surround and reaches forward past the
        # guards, so it shades the screen instead of reading as a lintel.
        ("hood", p1.slab(
            "hood", box_outline((0.0, 0.1140), (0.3760, 0.0360)),
            0.0620, 0.0810, opaque)),
    ]
    for index, (sx, sy) in enumerate(((-1, 1), (1, 1), (-1, -1), (1, -1))):
        parts.append((f"guard_{index}", p1.slab(
            f"guard_{index}",
            box_outline((sx * 0.1890, sy * 0.1120), (0.0500, 0.0340)),
            0.0620, 0.0810, opaque)))
    for index, sx in enumerate((-1, 1)):
        parts.append((f"rail_{index}", p1.slab(
            f"rail_{index}",
            box_outline((sx * 0.2060, 0.0), (0.0150, 0.1900)),
            0.0620, 0.0740, opaque)))
    accent = [("warning_stripe", p1.slab(
        "warning_stripe", box_outline((0.0, -0.1150), (0.1900, 0.0110)),
        0.0620, 0.0650, readout))]
    return parts, accent, screen_z, {
        "intent": ("flat cut-plate chassis inside an external cage: four "
                   "corner guards, two side rails and a hood over the top of "
                   "the screen do the retaining, and there is no bezel"),
        "mounting": ("the four corner guards are the mounting bosses; the "
                     "chassis is a plate behind them"),
        "maintainability": ("screen reached by removing two guards on one "
                            "side; hood and rails stay"),
        "silhouette": ("square corners, top hood overhang, four corner blocks "
                       "standing proud"),
    }


BUILDERS = {
    "OrbitalAnalog": build_orbital_analog,
    "ForgeBrass": build_forge_brass,
    "KineticSafety": build_kinetic_safety,
}


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def assemble(theme):
    bpy.ops.wm.read_homefile(use_empty=True)
    collection = bpy.context.collection
    opaque_colour, readout_colour = COLOURS[theme]
    opaque = p1.make_material(f"MAT_{theme}_Monitor_Solid_Opaque",
                              opaque_colour)
    readout = p1.make_material(f"MAT_{theme}_Monitor_Solid_Readout",
                               readout_colour, True)
    root = bpy.data.objects.new(production.root_name(theme), None)
    collection.objects.link(root)
    root["opus5_id"] = production.root_name(theme)

    parts, accent, screen_z, notes = BUILDERS[theme](opaque, readout)
    objects = []
    for name, mesh in parts:
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        objects.append(obj)
    static_opaque = p1.join_into(objects[0], objects[1:])
    static_opaque.name = "static_opaque"
    static_opaque.parent = root
    static_opaque["opus5_id"] = "static_opaque"

    accent_objects = []
    for name, mesh in accent:
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        accent_objects.append(obj)
    static_readout = p1.join_into(accent_objects[0], accent_objects[1:])
    static_readout.name = "static_readout"
    static_readout.parent = root
    static_readout["opus5_id"] = "static_readout"

    display = bpy.data.objects.new(
        "display_surface",
        p1.plane("display_surface", *DISPLAY, screen_z, opaque))
    collection.objects.link(display)
    display.parent = root
    display["opus5_id"] = "display_surface"
    bpy.context.view_layer.update()
    return root, static_opaque, static_readout, display, screen_z, notes


# ---------------------------------------------------------------------------
# self verification
# ---------------------------------------------------------------------------

def bvh_of(objects):
    verts, faces = [], []
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        offset = len(verts)
        verts.extend(matrix @ v.co for v in mesh.vertices)
        faces.extend(tuple(int(i) + offset for i in tri.vertices)
                     for tri in mesh.loop_triangles)
    return BVHTree.FromPolygons(verts, faces, all_triangles=True)


def visibility_probe(static_objects, display, screen_z, samples=9):
    """Is the screen reachable from the front, and opaque from the back?

    Cast the room-facing axis at points over the screen. The first surface a
    ray meets has to be the screen itself, not the housing: a screen embedded
    inside a solid slab measures as a perfect plane and is still invisible.
    The reverse ray has to meet the housing, so nothing shows through from
    behind.
    """
    tree = bvh_of(static_objects)
    hits = {"front_blocked": 0, "back_open": 0, "samples": 0,
            "front_blockers_min_z": None}
    step_x = DISPLAY[0] / 2.0 * 0.8
    step_y = DISPLAY[1] / 2.0 * 0.8
    for ix in (-1, 0, 1):
        for iy in (-1, 0, 1):
            x, y = ix * step_x, iy * step_y
            hits["samples"] += 1
            forward = tree.ray_cast(Vector((x, y, 0.60)),
                                    Vector((0.0, 0.0, -1.0)))
            if forward[0] is not None and forward[0].z > screen_z + 1e-6:
                hits["front_blocked"] += 1
                z = float(forward[0].z)
                hits["front_blockers_min_z"] = (
                    z if hits["front_blockers_min_z"] is None
                    else min(hits["front_blockers_min_z"], z))
            backward = tree.ray_cast(Vector((x, y, -0.60)),
                                     Vector((0.0, 0.0, 1.0)))
            if backward[0] is None or backward[0].z > screen_z - 1e-6:
                hits["back_open"] += 1
    hits["screen_visible_from_front"] = hits["front_blocked"] == 0
    hits["opaque_behind_screen"] = hits["back_open"] == 0
    hits["clean"] = (hits["screen_visible_from_front"]
                     and hits["opaque_behind_screen"])
    return hits


def coplanar_with_display(static_objects, display, tol=1.2e-4):
    """Z-facing faces sharing the screen's plane and covering the same pixels."""
    mesh = display.data
    mesh.calc_loop_triangles()
    plane_z = float(display.matrix_world.translation.z
                    + mesh.vertices[0].co.z)
    pairs = 0
    for obj in static_objects:
        other = obj.data
        other.calc_loop_triangles()
        matrix = obj.matrix_world
        for tri in other.loop_triangles:
            normal = (matrix.to_3x3() @ tri.normal).normalized()
            if abs(normal.z) < 0.999:
                continue
            points = [matrix @ other.vertices[i].co for i in tri.vertices]
            z = sum(p.z for p in points) / 3.0
            if abs(z - plane_z) > tol:
                continue
            xs = [p.x for p in points]
            ys = [p.y for p in points]
            if (min(max(xs), DISPLAY[0] / 2.0)
                    - max(min(xs), -DISPLAY[0] / 2.0) > 1e-6
                    and min(max(ys), DISPLAY[1] / 2.0)
                    - max(min(ys), -DISPLAY[1] / 2.0) > 1e-6):
                pairs += 1
    return {"coplanar_faces_over_display": pairs, "clean": pairs == 0,
            "display_plane_z": round(plane_z, 6), "tolerance_m": tol}


def protrusion_probe(static_objects, display, screen_z):
    """Nothing may stand in front of the screen inside the opening."""
    inside = 0
    lowest = None
    for obj in static_objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        for tri in mesh.loop_triangles:
            points = [matrix @ mesh.vertices[i].co for i in tri.vertices]
            if all(abs(p.x) <= DISPLAY[0] / 2.0 and abs(p.y) <= DISPLAY[1] / 2.0
                   and p.z > screen_z + 1e-6 for p in points):
                inside += 1
                z = min(p.z for p in points)
                lowest = z if lowest is None else min(lowest, z)
    return {"faces_in_front_of_display": inside,
            "nearest_front_z": None if lowest is None else round(lowest, 6),
            "clean": inside == 0}


def silhouette(objects, pixels=512, span=0.24):
    """Front-projection mask, for the pairwise silhouette comparison."""
    mask = np.zeros((pixels, pixels), dtype=bool)
    scale = pixels / (2.0 * span)
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        for tri in mesh.loop_triangles:
            points = [matrix @ mesh.vertices[i].co for i in tri.vertices]
            u = [p.x * scale + pixels / 2.0 for p in points]
            v = [p.y * scale + pixels / 2.0 for p in points]
            x0 = max(int(min(u)), 0)
            x1 = min(int(max(u)) + 1, pixels)
            y0 = max(int(min(v)), 0)
            y1 = min(int(max(v)) + 1, pixels)
            if x1 <= x0 or y1 <= y0:
                continue
            area = ((u[1] - u[0]) * (v[2] - v[0])
                    - (u[2] - u[0]) * (v[1] - v[0]))
            if abs(area) < 1e-12:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5,
                                 np.arange(y0, y1) + 0.5)
            w0 = ((u[1] - u[0]) * (gy - v[0])
                  - (gx - u[0]) * (v[1] - v[0])) / area
            w1 = ((gx - u[0]) * (v[2] - v[0])
                  - (u[2] - u[0]) * (gy - v[0])) / area
            w2 = 1.0 - w0 - w1
            mask[y0:y1, x0:x1] |= (w0 >= 0.0) & (w1 >= 0.0) & (w2 >= 0.0)
    return mask


def pairwise_iou(masks):
    rows = {}
    names = list(masks)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = masks[names[i]], masks[names[j]]
            union = int(np.count_nonzero(a | b))
            inter = int(np.count_nonzero(a & b))
            rows[f"{names[i]}|{names[j]}"] = round(inter / union, 4) if union \
                else None
    return rows


def audit_production(project_root):
    """Read-only audit of what ships today, from its own published report."""
    report = json.loads((project_root / PRODUCTION_REPORT).read_text())
    rows = {}
    for theme, entry in report["themes"].items():
        measure = entry.get("measure") or entry
        objects = measure["objects"]
        display = objects["display_surface"]
        opaque = objects["static_opaque"]
        screen_z = display["bounds_min"][2]
        rows[theme] = {
            "triangles_total": measure["triangles_total"],
            "per_object": {name: row["triangles"]
                           for name, row in objects.items()},
            "renderers": len(objects),
            "material_roles": sorted({
                "readout" if "Readout" in name else "opaque"
                for row in objects.values() for name in row["materials"]}),
            "envelope_m": [round(measure["bounds"]["max"][i]
                                 - measure["bounds"]["min"][i], 6)
                           for i in range(3)],
            "screen_z_m": screen_z,
            "display_normals": measure["display_normals"],
            "housing_z_range_m": [opaque["bounds_min"][2],
                                  opaque["bounds_max"][2]],
            "screen_inside_housing_z_span": (
                opaque["bounds_min"][2] < screen_z < opaque["bounds_max"][2]),
        }
    rows["_shape_family"] = {
        "single_builder": "opus5_trend_monitor_themes.build_theme",
        "shared_skeleton": ["rounded rectangle housing slab",
                            "rounded rectangle bezel frame", "flat screen"],
        "per_theme_differences": {
            theme: sorted(k for k in production.THEMES[theme]
                          if k in ("shroud", "retaining_frame", "lugs",
                                   "guards", "fasteners"))
            for theme in THEME_ORDER},
        "finding": ("all three are the same part list with different scalars; "
                    "the optional extras are additions to one skeleton, not "
                    "different skeletons"),
    }
    return rows


# ---------------------------------------------------------------------------
# renders and report
# ---------------------------------------------------------------------------

STAGE_VIEWS = {
    "front": (0.0, 0.0),
    "oblique_left": (-38.0, 18.0),
    "oblique_right": (38.0, 18.0),
    "side": (78.0, 6.0),
}


def render_stages(theme, root, static_objects, display, out_dir, project_root):
    """Fixed camera; the display alone and then the housing composed with it."""
    review.configure_scene()
    written = {}
    for label, view in STAGE_VIEWS.items():
        path = out_dir / f"T1_TrendMonitor_{theme}_{label}.png"
        p1.shot(FIXED_FOCUS, FIXED_RADIUS, view, FIXED_LENS, FIXED_SCALE, path)
        written[label] = str(path.relative_to(project_root))
    saved = [obj.hide_render for obj in static_objects]
    for obj in static_objects:
        obj.hide_render = True
    bpy.context.view_layer.update()
    for label, view in (("front", (0.0, 0.0)), ("oblique", (34.0, 18.0))):
        path = out_dir / f"T1_TrendMonitor_{theme}_display_only_{label}.png"
        p1.shot(FIXED_FOCUS, FIXED_RADIUS, view, FIXED_LENS, FIXED_SCALE, path)
        written[f"display_only_{label}"] = str(path.relative_to(project_root))
    for obj, value in zip(static_objects, saved):
        obj.hide_render = value
    bpy.context.view_layer.update()
    for label, view in (("front", (0.0, 0.0)), ("oblique", (34.0, 18.0))):
        path = out_dir / f"T1_TrendMonitor_{theme}_composed_{label}.png"
        p1.shot(FIXED_FOCUS, FIXED_RADIUS, view, FIXED_LENS, FIXED_SCALE, path)
        written[f"composed_{label}"] = str(path.relative_to(project_root))
    return written


def contact_sheet(images, project_root, output_path):
    order = ["front", "oblique_left", "oblique_right", "side"]
    tiles = [[review.load_rgba(project_root / images[t][v]) for v in order]
             for t in THEME_ORDER]
    height, width = tiles[0][0].shape[:2]
    gap = 14
    canvas = np.zeros((len(THEME_ORDER) * height + (len(THEME_ORDER) - 1) * gap,
                       len(order) * width + (len(order) - 1) * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for row_index, row in enumerate(tiles):
        top = (len(THEME_ORDER) - 1 - row_index) * (height + gap)
        for column, tile in enumerate(row):
            canvas[top:top + height,
                   column * (width + gap):column * (width + gap) + width] = tile
    for row_index, theme in enumerate(THEME_ORDER):
        for column, view in enumerate(order):
            review.draw_label(canvas, theme.upper(),
                              column * (width + gap) + 14,
                              row_index * (height + gap) + 14)
            review.draw_label(canvas, view.upper().replace("_", " "),
                              column * (width + gap) + 14,
                              row_index * (height + gap) + 56,
                              colour=(0.72, 0.78, 0.86))
    review.save_rgba(canvas, output_path)


def export(root, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [root] + list(root.children_recursive):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    settings = dict(toggle.EXPORT_SETTINGS)
    settings["use_triangles"] = False
    settings["mesh_smooth_type"] = "EDGE"
    bpy.ops.export_scene.fbx(filepath=str(target), **settings)
    return target


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in ("review", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)

    baseline = audit_production(project_root)
    payload = {
        "phase": "TrendMonitor-themes-T1",
        "gate": "A candidate",
        "note": ("Three theme-specific skeletons replacing one parameterised "
                 "shape. The runtime contract is held fixed: display size, "
                 "normal, screen Z, object names, renderer and role counts "
                 "are the shipped values."),
        "scope": {
            "targets": list(THEME_ORDER),
            "isolated_root": TREE,
            "script": "Tools/Blender/opus5_trend_monitor_theme_candidates.py",
            "untouched": ["Assets/", "Builds/", "docs/",
                          "existing ArtSource delivery", "production FBX",
                          "prefab", "material", "runtime code", "git"],
            "external_addons": "none",
        },
        "frozen_runtime_contract": {
            "display_m": list(DISPLAY), "opening_m": list(OPENING),
            "display_normal": "local +Z", "up": "local +Y",
            "mount_plane": "local Z = 0",
            "screen_z_m": SCREEN_Z,
            "screen_z_source": "shipped per-theme value, held unchanged",
            "object_names": ["static_opaque", "static_readout",
                             "display_surface"],
            "renderers": 3, "material_roles": 2,
            "max_inputs": 4,
            "signal_path_theme_independent": True,
        },
        "production_audit": baseline,
        "themes": {},
    }

    masks, images = {}, {}
    for theme in THEME_ORDER:
        root, static_opaque, static_readout, display, screen_z, notes = \
            assemble(theme)
        statics = [static_opaque, static_readout]
        measure = p1.measure(root, display)
        contract = production.check_contract(measure, theme)
        visibility = visibility_probe(statics, display, screen_z)
        coplanar = coplanar_with_display(statics, display)
        protrusion = protrusion_probe(statics, display, screen_z)
        masks[theme] = silhouette([static_opaque, static_readout, display])

        fbx = tree / f"SM_TrendMonitor_{theme}_V6_Opus5_T1.fbx"
        export(root, fbx)
        blend = dirs["blend"] / f"BL_TrendMonitor_{theme}_V6_Opus5_T1.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
        images[theme] = render_stages(theme, root, statics, display,
                                      dirs["review"], project_root)

        before = baseline[theme]
        payload["themes"][theme] = {
            "design": notes,
            "measure": measure,
            "contract": contract,
            "visibility": visibility,
            "display_coplanar": coplanar,
            "display_protrusion": protrusion,
            "screen_z_m": screen_z,
            "screen_z_unchanged": abs(screen_z - before["screen_z_m"]) < 1e-9,
            "budget_vs_production": {
                "triangles_before": before["triangles_total"],
                "triangles_after": measure["triangles_total"],
                "triangle_delta": measure["triangles_total"]
                - before["triangles_total"],
                "renderers_before": before["renderers"],
                "renderers_after": len(measure["objects"]),
                "material_roles_before": before["material_roles"],
                "material_roles_after": contract["material_roles"],
                "envelope_before_m": before["envelope_m"],
                "envelope_after_m": contract["envelope_m"],
            },
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "blend": str(blend.relative_to(project_root)),
            "images": images[theme],
        }
        source_report = tree / f"SM_TrendMonitor_{theme}_V6_Opus5_T1.json"
        source_payload = {
            "theme": theme,
            "model": "TrendMonitor",
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx),
            "triangles": measure["triangles_total"],
            "renderers": len(measure["objects"]),
            "material_slots": ["opaque", "readout"],
            "bounds_space": "unity_xyz",
            "candidate": {
                "triangles": measure["triangles_total"],
                "bounds": measure["bounds"],
            },
            "gates": {
                "triangles": {"measured": measure["triangles_total"]},
                "submesh_budget": {"measured": 3, "budget": 3},
            },
        }
        source_report.write_text(
            json.dumps(source_payload, indent=2) + "\n", encoding="utf-8")
        payload["themes"][theme]["source_report"] = str(
            source_report.relative_to(project_root))
        print(f"[T1] {theme}: tris {measure['triangles_total']} "
              f"(was {before['triangles_total']}), renderers "
              f"{len(measure['objects'])}, roles "
              f"{contract['material_roles']}, contract {contract['pass']}, "
              f"screen visible {visibility['screen_visible_from_front']}, "
              f"opaque behind {visibility['opaque_behind_screen']}, "
              f"coplanar {coplanar['coplanar_faces_over_display']}, "
              f"protrusion {protrusion['faces_in_front_of_display']}")

    sheet = tree / "ContactSheet_TrendMonitor_T1.png"
    contact_sheet(images, project_root, sheet)
    payload["contact_sheet"] = {"path": str(sheet.relative_to(project_root)),
                                "sha256": m1.digest(sheet)}
    payload["silhouette_iou"] = {
        "pairs": pairwise_iou(masks),
        "note": ("reported as a measurement, not a gate: the formal threshold "
                 "is not set until a baseline exists for shapes agreed to be "
                 "correct"),
        "production_pairs": None,
    }
    # The same measurement on what ships today, so the T1 numbers have
    # something to be compared against. Built in memory only; nothing on disk
    # is read or written for this.
    production_masks = {}
    for theme in THEME_ORDER:
        root, display, _ = production.build_theme(theme,
                                                  production.THEMES[theme])
        production_masks[theme] = silhouette(
            [obj for obj in root.children_recursive if obj.type == "MESH"])
    payload["silhouette_iou"]["production_pairs"] = pairwise_iou(
        production_masks)

    payload["self_check"] = {
        "contract_pass": all(row["contract"]["pass"]
                             for row in payload["themes"].values()),
        "screen_z_unchanged": all(row["screen_z_unchanged"]
                                  for row in payload["themes"].values()),
        "screen_visible": all(row["visibility"]["clean"]
                              for row in payload["themes"].values()),
        "display_coplanar_zero": all(row["display_coplanar"]["clean"]
                                     for row in payload["themes"].values()),
        "no_protrusion": all(row["display_protrusion"]["clean"]
                             for row in payload["themes"].values()),
        "renderers_three": all(row["budget_vs_production"]["renderers_after"]
                               == 3 for row in payload["themes"].values()),
        "roles_two": all(len(row["budget_vs_production"]
                             ["material_roles_after"]) <= 2
                         for row in payload["themes"].values()),
    }
    payload["status"] = ("t1_candidate_ready"
                         if all(payload["self_check"].values())
                         else "t1_candidate_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[T1] status {payload['status']}")


if __name__ == "__main__":
    main()
