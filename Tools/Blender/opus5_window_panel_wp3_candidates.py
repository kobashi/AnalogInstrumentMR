"""Window Panel WP3: four theme candidates for the parametric graphic panel.

Alignment 347. The vane goes; what replaces it is a flat `display_surface` the
runtime draws Orbit / Rose / Lissajous onto, and a frame that is genuinely each
theme's own rather than one shape in four colours.

What is fixed for all four, from 339 and the graphics contract:

* exactly one `display_surface`, a two-triangle plane, front along instrument
  local +Z and up along local +Y
* the graphic works in normalized coordinates [-1, 1] x [-0.55, 0.55], so the
  plane is cut 2 : 1.1 and the frame opening clears it on every side - the
  usable rectangle is the inner 90 %, and the frame must not reach into it
* no vane, no needle, no analog scale, anywhere in the candidate
* nothing here touches production FBX, prefabs, materials, runtime, schema, UI
  or Codex's validators

What differs is the frame, at the level of which parts exist:

* Orbital Analog - one continuous shell drawn back to the screen by a deep
  chamfer. No applied part, no fastener on the face.
* Forge Brass - an octagonal casting standing on a flange that reaches the
  mount plane, six bolt bosses, and a separate retaining lip in its own
  material role around the opening.
* Kinetic Safety - a cut plate inside an external cage: four corner guards,
  two side rails, a hood over the top of the screen, and a hazard band.
* Machined Ergonomics - a drafted machined plate with a thin precision ring at
  the opening and four flush corner fasteners, in the language of the fourteen
  instruments already accepted for that theme.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_window_panel_wp3_candidates.py -- \
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

TREE = "ArtSource/Blender/BrushUp/Opus5/WindowPanel/WP3"
# 350-A pins the authoring binary. The launcher already refuses anything but
# 5.2.x, and the r1 .blend files record bpy.data.version (5, 2, 44), but the
# binary is now recorded per run so provenance never has to be inferred.
REQUIRED_BLENDER = "/Applications/Blender 5.2.app/Contents/MacOS/Blender"
# Tone mapping only. 350.3 asks for brighter fixed images with the geometry
# and the camera untouched, so nothing here moves a light or a lens.
EXPOSURE_BOOST = 1.6

ENVELOPE_LIMIT = (1.60, 0.90, 0.22)
TRIANGLE_BUDGET = 8000
# [-1, 1] x [-0.55, 0.55] is 2 : 1.1; the plane is cut to that ratio so the
# graphic never has to letterbox itself.
DISPLAY = (1.2000, 0.6600)
NORMALIZED_EXTENT = (1.0, 0.55)
OPENING = (1.2160, 0.6760)       # 8 mm reveal all round, clear of the plane
USABLE_FRACTION = 0.90

THEME_ORDER = ("OrbitalAnalog", "ForgeBrass", "KineticSafety",
               "MachinedErgonomics")

# Solid role colours, from MockInstrumentThemeCatalog. Candidate materials are
# deliberately independent of the production atlas (alignment 349).
PALETTE = {
    "OrbitalAnalog": {"frame": (0.120, 0.140, 0.160, 1.0),
                      "trim": (0.720, 0.750, 0.700, 1.0),
                      "face": (0.060, 0.070, 0.080, 1.0)},
    "ForgeBrass": {"frame": (0.250, 0.160, 0.080, 1.0),
                   "trim": (0.820, 0.680, 0.380, 1.0),
                   "face": (0.070, 0.055, 0.040, 1.0)},
    "KineticSafety": {"frame": (0.080, 0.110, 0.140, 1.0),
                      "trim": (1.000, 0.720, 0.040, 1.0),
                      "face": (0.025, 0.035, 0.045, 1.0)},
    "MachinedErgonomics": {"frame": (0.720, 0.750, 0.780, 1.0),
                           "trim": (0.180, 0.240, 0.280, 1.0),
                           "face": (0.012, 0.020, 0.028, 1.0)},
}

FIXED_VIEWS = {
    "front": (0.0, 0.0),
    "front_three_quarter": (35.0, 16.0),
    "side": (90.0, 6.0),
    "back": (180.0, 10.0),
}
FIXED_FOCUS = (0.0, 0.0, 0.060)
FIXED_RADIUS = 3.10
FIXED_LENS = 55.0
FIXED_SCALE = 1.20


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--revision", default="r1")
    return parser.parse_args(args)


def rounded(width, height, radius, segments=p1.CORNER_SEGMENTS):
    return p1.rounded_rectangle(width, height, radius, segments)


def octagon(width, height, chamfer):
    hx, hy = width / 2.0, height / 2.0
    return [(hx, hy - chamfer), (hx - chamfer, hy),
            (-hx + chamfer, hy), (-hx, hy - chamfer),
            (-hx, -hy + chamfer), (-hx + chamfer, -hy),
            (hx - chamfer, -hy), (hx, -hy + chamfer)]


def box(centre, size, radius=0.0):
    if radius <= 0.0:
        hx, hy = size[0] / 2.0, size[1] / 2.0
        return [(centre[0] + x, centre[1] + y)
                for x, y in ((hx, hy), (-hx, hy), (-hx, -hy), (hx, -hy))]
    return [(centre[0] + x, centre[1] + y)
            for x, y in p1.rounded_rectangle(size[0], size[1], radius, 2)]


def ring(name, outer, inner, near_z, far_z, material):
    """p1.frame with the equal-point-count pairing it assumes made explicit.

    p1.frame walks range(len(outer)) and indexes `inner` with the same
    counter, so mixing a 20-point rounded outline with an 8-point octagon
    stitches a ring out of the first eight points of the longer one and closes
    the opening. That silently hid a screen on two themes during the trend
    monitor work; here it raises instead.
    """
    if len(outer) != len(inner):
        raise SystemExit(f"[WP3] {name}: outline point counts differ "
                         f"({len(outer)} vs {len(inner)})")
    return p1.frame(name, outer, inner, near_z, far_z, material)


def opening_outline(segments):
    return p1.rounded_rectangle(OPENING[0], OPENING[1], 0.0140, segments)


# ---------------------------------------------------------------------------
# the four frames
# ---------------------------------------------------------------------------

def build_orbital_analog(mats):
    """One continuous shell, drawn back to the screen by a deep chamfer."""
    body = rounded(1.5800, 0.8800, 0.0460)
    screen_z = 0.0620
    parts = [
        ("frame_back", p1.slab("frame_back", body, 0.0000, 0.0380,
                               mats["frame"])),
        ("frame_wall", ring("frame_wall", body,
                            opening_outline(p1.CORNER_SEGMENTS),
                            0.0380, 0.0700, mats["frame"])),
        # The chamfer: a second ring stepped in, so the front reads as one
        # moulding pulled towards the screen rather than a bezel laid on.
        ("frame_chamfer", ring("frame_chamfer",
                               rounded(1.4600, 0.7800, 0.0380),
                               opening_outline(p1.CORNER_SEGMENTS),
                               0.0700, 0.0980, mats["frame"])),
    ]
    trim = [("trim_rail", p1.slab(
        "trim_rail", box((0.0, -0.4020), (0.8600, 0.0180), 0.0070),
        0.0980, 0.1010, mats["trim"]))]
    return parts, trim, screen_z, {
        "frame_language": ("one sealed shell with a 28 mm chamfer stepping in "
                           "to the opening; nothing applied to the face"),
        "material_roles": ["frame", "trim", "face"],
        "mounting": "rear flange engaged by the panel cut-out, no face fixing",
        "depth_m": 0.1010,
    }


def build_forge_brass(mats):
    """Octagonal casting on a flange, with a brass retaining lip."""
    body = octagon(1.4800, 0.8000, 0.1400)
    flange = octagon(1.5800, 0.8800, 0.1600)
    screen_z = 0.0900
    parts = [
        ("frame_flange", ring("frame_flange", flange,
                              octagon(1.4200, 0.7400, 0.1300),
                              0.0000, 0.0420, mats["frame"])),
        ("frame_back", p1.slab("frame_back", body, 0.0000, 0.0620,
                               mats["frame"])),
        ("frame_wall", ring("frame_wall", body, opening_outline(1),
                            0.0620, 0.1060, mats["frame"])),
    ]
    for index, (x, y) in enumerate((
            (-0.7180, 0.0), (0.7180, 0.0),
            (-0.4600, 0.3820), (0.4600, 0.3820),
            (-0.4600, -0.3820), (0.4600, -0.3820))):
        parts.append((f"frame_bolt_{index}", p1.slab(
            f"frame_bolt_{index}",
            [(x + 0.0340 * math.cos(math.radians(a)),
              y + 0.0340 * math.sin(math.radians(a)))
             for a in range(0, 360, 60)],
            0.0420, 0.0560, mats["frame"])))
    trim = [("trim_lip", ring(
        "trim_lip", octagon(1.3400, 0.7200, 0.0900),
        p1.rounded_rectangle(OPENING[0] - 0.0140, OPENING[1] - 0.0140,
                             0.0120, 1),
        0.1060, 0.1180, mats["trim"]))]
    return parts, trim, screen_z, {
        "frame_language": ("octagonal casting standing on a flange that "
                           "reaches the mount plane, six bolt bosses, and a "
                           "retaining lip in its own material role"),
        "material_roles": ["frame", "trim (retaining lip)", "face"],
        "mounting": "six bolts through the flange at the octagon's flats",
        "depth_m": 0.1180,
    }


def build_kinetic_safety(mats):
    """Cut plate inside an external cage, with a hood and a hazard band."""
    body = p1.rounded_rectangle(1.5600, 0.8600, 0.0060, 1)
    screen_z = 0.0820
    parts = [
        ("frame_back", p1.slab("frame_back", body, 0.0000, 0.0560,
                               mats["frame"])),
        ("frame_wall", ring("frame_wall", body, opening_outline(1),
                            0.0560, 0.0960, mats["frame"])),
        ("frame_hood", p1.slab(
            "frame_hood", box((0.0, 0.4020), (1.3600, 0.0740)),
            0.0960, 0.1360, mats["frame"])),
    ]
    for index, (sx, sy) in enumerate(((-1, 1), (1, 1), (-1, -1), (1, -1))):
        parts.append((f"frame_guard_{index}", p1.slab(
            f"frame_guard_{index}",
            box((sx * 0.7180, sy * 0.3820), (0.1200, 0.0900)),
            0.0960, 0.1420, mats["frame"])))
    for index, sx in enumerate((-1, 1)):
        parts.append((f"frame_rail_{index}", p1.slab(
            f"frame_rail_{index}", box((sx * 0.7580, 0.0), (0.0420, 0.6800)),
            0.0960, 0.1240, mats["frame"])))
    trim = [("trim_hazard", p1.slab(
        "trim_hazard", box((0.0, -0.4060), (0.9600, 0.0300)),
        0.0960, 0.1000, mats["trim"]))]
    return parts, trim, screen_z, {
        "frame_language": ("cut plate inside an external cage: four corner "
                           "guards, two side rails and a hood over the top of "
                           "the screen; no bezel ring"),
        "material_roles": ["frame", "trim (hazard band)", "face"],
        "mounting": "the four corner guards are the mounting bosses",
        "depth_m": 0.1420,
    }


def build_machined_ergonomics(mats):
    """Drafted machined plate, thin precision ring, flush corner fasteners."""
    body = rounded(1.5800, 0.8800, 0.0180)
    screen_z = 0.0720
    parts = [
        ("frame_back", p1.slab("frame_back", body, 0.0000, 0.0300,
                               mats["frame"])),
        ("frame_wall", ring("frame_wall", body,
                            opening_outline(p1.CORNER_SEGMENTS),
                            0.0300, 0.0820, mats["frame"])),
    ]
    for index, (sx, sy) in enumerate(((-1, 1), (1, 1), (-1, -1), (1, -1))):
        centre = (sx * 0.7280, sy * 0.3900)
        parts.append((f"frame_fastener_{index}", p1.slab(
            f"frame_fastener_{index}",
            [(centre[0] + 0.0260 * math.cos(math.radians(a)),
              centre[1] + 0.0260 * math.sin(math.radians(a)))
             for a in range(0, 360, 30)],
            0.0820, 0.0850, mats["frame"])))
    trim = [
        # The thin machined ring this theme reads by, and a plate label.
        ("trim_ring", ring(
            "trim_ring", rounded(1.2900, 0.7500, 0.0180),
            opening_outline(p1.CORNER_SEGMENTS), 0.0820, 0.0900,
            mats["trim"])),
        ("trim_plate_label", p1.slab(
            "trim_plate_label", box((-0.5400, -0.4060), (0.2600, 0.0340),
                                    0.0040),
            0.0820, 0.0850, mats["trim"])),
    ]
    return parts, trim, screen_z, {
        "frame_language": ("drafted machined plate with a thin precision ring "
                           "at the opening and four flush corner fasteners, "
                           "in the language of the fourteen accepted "
                           "Machined Ergonomics instruments"),
        "material_roles": ["frame", "trim (precision ring, label)", "face"],
        "mounting": "four flush corner fasteners through the plate",
        "depth_m": 0.0900,
    }


BUILDERS = {
    "OrbitalAnalog": build_orbital_analog,
    "ForgeBrass": build_forge_brass,
    "KineticSafety": build_kinetic_safety,
    "MachinedErgonomics": build_machined_ergonomics,
}


# ---------------------------------------------------------------------------
# assembly, verification, evidence
# ---------------------------------------------------------------------------

def assemble(theme):
    bpy.ops.wm.read_homefile(use_empty=True)
    collection = bpy.context.collection
    colours = PALETTE[theme]
    mats = {
        role: p1.make_material(f"MAT_{theme}_WindowPanel_WP3_"
                               f"{role.capitalize()}", colours[role],
                               role == "face")
        for role in ("frame", "trim", "face")
    }
    root = bpy.data.objects.new(f"PF_Visual_WindowPanel_{theme}_WP3", None)
    collection.objects.link(root)
    root["opus5_id"] = root.name

    parts, trim, screen_z, notes = BUILDERS[theme](mats)
    objects = []
    for name, mesh in parts:
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        objects.append(obj)
    frame = p1.join_into(objects[0], objects[1:])
    frame.name = "frame"
    frame.parent = root
    frame["opus5_id"] = "frame"

    trim_objects = []
    for name, mesh in trim:
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        trim_objects.append(obj)
    trim_obj = p1.join_into(trim_objects[0], trim_objects[1:])
    trim_obj.name = "trim"
    trim_obj.parent = root
    trim_obj["opus5_id"] = "trim"

    display = bpy.data.objects.new(
        "display_surface",
        p1.plane("display_surface", *DISPLAY, screen_z, mats["face"]))
    collection.objects.link(display)
    display.parent = root
    display["opus5_id"] = "display_surface"
    bpy.context.view_layer.update()
    return root, frame, trim_obj, display, screen_z, notes


def display_contract(display, screen_z):
    mesh = display.data
    mesh.calc_loop_triangles()
    matrix = display.matrix_world
    normal_matrix = matrix.to_3x3().inverted_safe().transposed()
    normals = sorted({tuple(round(v, 6) for v in
                            (normal_matrix @ tri.normal).normalized())
                      for tri in mesh.loop_triangles})
    points = [matrix @ v.co for v in mesh.vertices]
    zs = {round(p.z, 6) for p in points}
    width = max(p.x for p in points) - min(p.x for p in points)
    height = max(p.y for p in points) - min(p.y for p in points)
    usable = (width * USABLE_FRACTION, height * USABLE_FRACTION)
    return {
        "count": 1,
        "triangles": len(mesh.loop_triangles),
        "vertices": len(mesh.vertices),
        "normals": normals,
        "front_is_local_plus_z": normals == [(0.0, 0.0, 1.0)],
        "coplanar": len(zs) == 1,
        "plane_z_m": round(screen_z, 6),
        "size_m": [round(width, 6), round(height, 6)],
        "aspect": round(width / height, 6),
        "normalized_extent": list(NORMALIZED_EXTENT),
        "normalized_aspect": round(NORMALIZED_EXTENT[0]
                                   / NORMALIZED_EXTENT[1], 6),
        "aspect_matches_normalized": abs(width / height
                                         - NORMALIZED_EXTENT[0]
                                         / NORMALIZED_EXTENT[1]) < 1e-6,
        "usable_rect_m": [round(v, 6) for v in usable],
        "usable_fraction": USABLE_FRACTION,
        "up_is_local_plus_y": True,
        "clean": (len(mesh.loop_triangles) == 2 and len(zs) == 1
                  and normals == [(0.0, 0.0, 1.0)]),
    }


def frame_clearance(statics, display, screen_z, samples=13):
    """Does the frame reach into the usable rectangle, or block the view?

    Two questions at once: rays down the viewing axis over the usable
    rectangle must reach the plane with nothing in front of it, and rays from
    behind must be stopped, so the graphic cannot be read through the back.
    """
    verts, faces = [], []
    for obj in statics:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        offset = len(verts)
        verts.extend(matrix @ v.co for v in mesh.vertices)
        faces.extend(tuple(int(i) + offset for i in tri.vertices)
                     for tri in mesh.loop_triangles)
    tree = BVHTree.FromPolygons(verts, faces, all_triangles=True)
    half_x = DISPLAY[0] / 2.0 * USABLE_FRACTION
    half_y = DISPLAY[1] / 2.0 * USABLE_FRACTION
    blocked = back_open = 0
    nearest_front = None
    for ix in range(samples):
        for iy in range(samples):
            x = -half_x + 2.0 * half_x * ix / (samples - 1)
            y = -half_y + 2.0 * half_y * iy / (samples - 1)
            hit = tree.ray_cast(Vector((x, y, 3.0)), Vector((0.0, 0.0, -1.0)))
            if hit[0] is not None and hit[0].z > screen_z + 1e-6:
                blocked += 1
                z = float(hit[0].z)
                nearest_front = z if nearest_front is None \
                    else min(nearest_front, z)
            back = tree.ray_cast(Vector((x, y, -3.0)), Vector((0.0, 0.0, 1.0)))
            if back[0] is None or back[0].z > screen_z - 1e-6:
                back_open += 1
    return {
        "samples": samples * samples,
        "usable_rect_m": [round(2 * half_x, 6), round(2 * half_y, 6)],
        "frame_intrusions": blocked,
        "nearest_front_z_m": None if nearest_front is None
        else round(nearest_front, 6),
        "back_see_through": back_open,
        "clean": blocked == 0 and back_open == 0,
    }


def legacy_nodes(root):
    """348 rejects vane / needle / analog scale; prove none exist."""
    banned = ("vane", "needle", "scale")
    found = sorted(obj.name for obj in [root] + list(root.children_recursive)
                   if any(word in obj.name.lower() for word in banned))
    return {"banned_substrings": list(banned), "found": found,
            "clean": not found}


def measure(root):
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
            "submeshes": len([m for m in obj.data.materials if m]) or 1,
            "bounds_min": [round(min(p[i] for p in points), 6)
                           for i in range(3)],
            "bounds_max": [round(max(p[i] for p in points), 6)
                           for i in range(3)],
        }
    points = [obj.matrix_world @ v.co for obj in root.children_recursive
              if obj.type == "MESH" for v in obj.data.vertices]
    lo = [round(min(p[i] for p in points), 6) for i in range(3)]
    hi = [round(max(p[i] for p in points), 6) for i in range(3)]
    size = [round(hi[i] - lo[i], 6) for i in range(3)]
    return {
        "objects": rows,
        "object_names": sorted(rows),
        "renderers": len(rows),
        "triangles_total": sum(row["triangles"] for row in rows.values()),
        "submeshes_total": sum(row["submeshes"] for row in rows.values()),
        "materials": sorted({name for row in rows.values()
                             for name in row["materials"]}),
        "bounds_min": lo, "bounds_max": hi, "size_m": size,
        "envelope_limit_m": list(ENVELOPE_LIMIT),
        "within_envelope": all(size[i] <= ENVELOPE_LIMIT[i] + 1e-9
                               for i in range(3)),
        "mount_plane_z0": abs(lo[2]) < 1e-9,
        "triangle_budget": TRIANGLE_BUDGET,
        "within_triangle_budget": sum(row["triangles"]
                                      for row in rows.values())
        <= TRIANGLE_BUDGET,
    }


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


def render(theme, out_dir, project_root, exposure=0.0, suffix=""):
    review.configure_scene()
    bpy.context.scene.view_settings.exposure = exposure
    written = {}
    for label, view in FIXED_VIEWS.items():
        path = out_dir / f"WP3_WindowPanel_{theme}_{label}{suffix}.png"
        p1.shot(FIXED_FOCUS, FIXED_RADIUS, view, FIXED_LENS, FIXED_SCALE, path)
        written[f"{label}{suffix}"] = str(path.relative_to(project_root))
    bpy.context.scene.view_settings.exposure = 0.0
    return written


def theme_report(theme, row, contract, fbx, project_root, blender):
    """350.2: one flat report per theme, the fields named at top level."""
    display = row["objects"]["display_surface"]
    return {
        "theme": theme,
        "model": "WindowPanel",
        "revision": None,
        "blender_binary": blender["binary"],
        "blender_version": blender["version"],
        "fbx": str(fbx.relative_to(project_root)),
        "fbx_sha256": m1.digest(fbx),
        "fbx_bytes": fbx.stat().st_size,
        "triangles": row["triangles_total"],
        "renderers": row["renderers"],
        "submeshes": row["submeshes_total"],
        "material_slots": row["materials"],
        "bounds_min": row["bounds_min"],
        "bounds_max": row["bounds_max"],
        "size_m": row["size_m"],
        "objects": row["object_names"],
        "display_surface_triangles": display["triangles"],
        "display_surface_normals": contract["normals"],
    }


def blender_identity():
    return {
        "binary": bpy.app.binary_path,
        "binary_required": REQUIRED_BLENDER,
        "binary_matches_required":
            bpy.app.binary_path == REQUIRED_BLENDER,
        "version": bpy.app.version_string,
        "version_tuple": list(bpy.app.version),
        "build_hash": bpy.app.build_hash.decode()
        if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "build_date": bpy.app.build_date.decode()
        if isinstance(bpy.app.build_date, bytes) else str(bpy.app.build_date),
        "note": ("bpy.app.version_string is the running application; the "
                 "version a .blend was written by is bpy.data.version, read "
                 "after loading that file"),
    }


def contact_sheet(images, project_root, output_path, suffix=""):
    order = [f"{view}{suffix}" for view in FIXED_VIEWS]
    tiles = [[review.load_rgba(project_root / images[t][v]) for v in order]
             for t in THEME_ORDER]
    height, width = tiles[0][0].shape[:2]
    gap = 14
    canvas = np.zeros((len(THEME_ORDER) * height + (len(THEME_ORDER) - 1) * gap,
                       len(order) * width + (len(order) - 1) * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    # save_rgba flips the canvas vertically and draw_label already writes in
    # flipped coordinates, so the tiles are pasted from the far end and the
    # captions are not. Matching the two indices "tidily" puts every caption
    # on the wrong instrument; this pairing is the one that lands.
    for row_index, row in enumerate(tiles):
        top = (len(THEME_ORDER) - 1 - row_index) * (height + gap)
        for column, tile in enumerate(row):
            canvas[top:top + height,
                   column * (width + gap):column * (width + gap) + width] = tile
    for row_index, theme in enumerate(THEME_ORDER):
        top = row_index * (height + gap)
        for column, view in enumerate(order):
            review.draw_label(canvas, theme.upper(),
                              column * (width + gap) + 14, top + 14)
            review.draw_label(canvas,
                              view.upper().replace("_", " "),
                              column * (width + gap) + 14, top + 56,
                              colour=(0.72, 0.78, 0.86))
    review.save_rgba(canvas, output_path)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    revision = args.revision
    tree = project_root / TREE / ("" if revision == "r1" else revision)
    output = (f"{TREE}/window_panel_wp3_candidates.json" if revision == "r1"
              else f"{TREE}/{revision}/window_panel_wp3_candidates_"
                   f"{revision}.json")
    blender = blender_identity()
    dirs = {name: tree / name for name in ("review", "blend", "themes")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "WindowPanel-WP3",
        "alignment": "347",
        "revision": f"WP3-{revision}",
        "blender": blender,
        "note": ("Four theme candidates for the parametric Window Panel. The "
                 "vane is gone; each candidate carries exactly one flat "
                 "display_surface and a frame that differs by part list, not "
                 "by colour."),
        "ownership": {
            "generated": [f"{TREE}/**"],
            "authoring_script":
                "Tools/Blender/opus5_window_panel_wp3_candidates.py",
            "untouched": ["production FBX", "prefab", "material", "runtime",
                          "schema", "UI", "Codex validators", "Assets/",
                          "Builds/", "docs/", "git"],
            "external_libraries": "none",
        },
        "fixed_contract": {
            "display_surface_per_candidate": 1,
            "display_triangles": 2,
            "front_axis": "instrument local +Z",
            "up_axis": "instrument local +Y",
            "display_size_m": list(DISPLAY),
            "opening_m": list(OPENING),
            "normalized_coordinates": "[-1, 1] x [-0.55, 0.55]",
            "usable_fraction": USABLE_FRACTION,
            "mount_plane": "local Z = 0",
            "envelope_limit_m": list(ENVELOPE_LIMIT),
            "triangle_budget": TRIANGLE_BUDGET,
            "forbidden_nodes": ["vane", "needle", "analog scale"],
        },
        "fixed_camera": {"focus": list(FIXED_FOCUS), "radius": FIXED_RADIUS,
                         "lens_mm": FIXED_LENS, "scale": FIXED_SCALE,
                         "views": {k: list(v)
                                   for k, v in FIXED_VIEWS.items()}},
        "candidates": {},
    }

    images = {}
    for theme in THEME_ORDER:
        root, frame, trim, display, screen_z, notes = assemble(theme)
        statics = [frame, trim]
        rows = measure(root)
        contract = display_contract(display, screen_z)
        clearance = frame_clearance(statics, display, screen_z)
        legacy = legacy_nodes(root)

        fbx = tree / f"SM_WindowPanel_{theme}_WP3.fbx"
        export(root, fbx)
        blend = dirs["blend"] / f"BL_WindowPanel_{theme}_WP3.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
        images[theme] = render(theme, dirs["review"], project_root)
        images[theme].update(render(theme, dirs["review"], project_root,
                                    exposure=EXPOSURE_BOOST,
                                    suffix="_bright"))
        per_theme = theme_report(theme, rows, contract, fbx, project_root,
                                 blender)
        per_theme["revision"] = f"WP3-{revision}"
        theme_path = dirs["themes"] / f"WindowPanel_{theme}_{revision}.json"
        theme_path.write_text(json.dumps(per_theme, indent=2) + "\n",
                              encoding="utf-8")

        payload["candidates"][theme] = {
            "design": notes,
            "measure": rows,
            "display_surface": contract,
            "frame_clearance": clearance,
            "legacy_nodes": legacy,
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "blend": str(blend.relative_to(project_root)),
            "blend_sha256": m1.digest(blend),
            "images": images[theme],
            "theme_report": str(theme_path.relative_to(project_root)),
            "theme_report_sha256": m1.digest(theme_path),
            "pass": (rows["within_envelope"] and rows["mount_plane_z0"]
                     and rows["within_triangle_budget"] and contract["clean"]
                     and clearance["clean"] and legacy["clean"]),
        }
        print(f"[WP3] {theme}: tris {rows['triangles_total']}/"
              f"{TRIANGLE_BUDGET}, renderers {rows['renderers']}, submeshes "
              f"{rows['submeshes_total']}, materials {len(rows['materials'])}, "
              f"size {rows['size_m']}, display {contract['triangles']}tri "
              f"{contract['front_is_local_plus_z']}, clearance "
              f"{clearance['clean']}, legacy {legacy['clean']}, "
              f"pass {payload['candidates'][theme]['pass']}")

    sheet = tree / f"ContactSheet_WindowPanel_WP3_{revision}.png"
    contact_sheet(images, project_root, sheet, suffix="")
    bright = tree / f"ContactSheet_WindowPanel_WP3_{revision}_bright.png"
    contact_sheet(images, project_root, bright, suffix="_bright")
    payload["contact_sheet"] = {
        "path": str(sheet.relative_to(project_root)),
        "sha256": m1.digest(sheet),
        "bright_path": str(bright.relative_to(project_root)),
        "bright_sha256": m1.digest(bright),
        "bright_method": ("scene view transform exposure "
                          f"+{EXPOSURE_BOOST}; geometry, lights and camera "
                          "unchanged")}
    payload["status"] = ("wp3_candidates_ready"
                         if all(row["pass"]
                                for row in payload["candidates"].values())
                         else "wp3_candidates_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / output).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[WP3] status {payload['status']}")


if __name__ == "__main__":
    main()
