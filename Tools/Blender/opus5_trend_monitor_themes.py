"""Trend Monitor across three themes, from the approved Orbital Analog shape.

Alignment 232. The display contract does not move: mount plane at local Z = 0,
the screen its own flat object facing local +Z, an opening of at least
0.36 x 0.18 m, a 16 mm recess behind the bezel, an envelope inside
0.44 x 0.28 x 0.10 m, three renderers and two material roles.

What each theme is allowed to change is the instrument around that screen, and
it changes by form rather than by colour:

* Orbital Analog - the approved P1, untouched: thin charcoal slab, quiet
  rounded bezel, four small corner fasteners, the cyan accent bar it already
  carries.
* Forge Brass - a deeper cast housing with a heavy radius, and a separate
  retaining frame standing proud of the bezel with six lugs clamping it down.
  The frame reads as brass by being a distinct part, not a distinct material:
  the role count stays at two.
* Kinetic Safety - a graphite shroud that steps out past the body, and a thick
  guarded bezel with four squared corner guards.

Nothing is exported that Unity should not receive: no collider, no animation,
no camera, no light, no glass, and nothing baked into the screen.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_trend_monitor_themes.py -- \
      --project-root "$PWD" --mode build
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
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_toggle_fbx_handoff as toggle
import opus5_trend_monitor_prototype as p1


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/trend_monitor_themes.json"
TREE = "ArtSource/Blender/BrushUp/Opus5/{theme}/TrendMonitor"
# Fixed for every theme, from alignment 231.6 / 232.
OPENING = (0.372, 0.192)
DISPLAY = (0.368, 0.188)
DISPLAY_RECESS = 0.016
ENVELOPE_LIMIT = (0.44, 0.28, 0.10)
OPENING_MINIMUM = (0.36, 0.18)

THEMES = {
    "OrbitalAnalog": {
        "body": (0.436, 0.272),
        "body_depth": 0.050,
        "corner_radius": 0.014,
        "bezel_inset": 0.014,
        "bezel_depth": 0.006,
        "opaque_colour": (0.055, 0.058, 0.063, 1.0),
        "readout_colour": (0.030, 0.115, 0.135, 1.0),
        "fasteners": {"at": (0.191, 0.105), "radius": 0.006, "height": 0.004},
        "readout_bars": [(0.260, 0.009, -0.108)],
        "readout_height": 0.0025,
    },
    "ForgeBrass": {
        "body": (0.436, 0.272),
        "body_depth": 0.062,
        "corner_radius": 0.020,
        "bezel_inset": 0.026,
        "bezel_depth": 0.007,
        "opaque_colour": (0.075, 0.062, 0.048, 1.0),
        "readout_colour": (0.145, 0.090, 0.028, 1.0),
        # A retaining frame standing proud of the bezel, held by six lugs.
        "retaining_frame": {"inset": 0.012, "depth": 0.005, "width": 0.010},
        "lugs": {
            "at": [
                (-0.120, 0.126), (0.120, 0.126), (-0.120, -0.126), (0.120, -0.126),
                (-0.198, 0.0), (0.198, 0.0),
            ],
            "size": (0.030, 0.016),
            "height": 0.006,
        },
        # Chart-recorder slits rather than one bar.
        "readout_bars": [
            (0.070, 0.007, -0.112), (0.070, 0.007, -0.112), (0.070, 0.007, -0.112)
        ],
        "readout_offsets_x": [-0.090, 0.0, 0.090],
        "readout_height": 0.002,
    },
    "KineticSafety": {
        "body": (0.428, 0.264),
        "body_depth": 0.055,
        "corner_radius": 0.010,
        "bezel_inset": 0.010,
        "bezel_depth": 0.010,
        "opaque_colour": (0.048, 0.050, 0.052, 1.0),
        "readout_colour": (0.190, 0.105, 0.012, 1.0),
        # A shroud stepping out past the body, and squared corner guards.
        "shroud": {"outset": 0.006, "depth": 0.008},
        "guards": {
            "at": (0.196, 0.116), "size": (0.044, 0.030), "height": 0.008,
        },
        "readout_bars": [(0.120, 0.010, -0.107)],
        "readout_height": 0.003,
    },
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("build",))
    return parser.parse_args(args)


def root_name(theme):
    return f"PF_Visual_TrendMonitor_{theme}_V6"


def blend_path(project_root, theme):
    return (
        project_root
        / TREE.format(theme=theme)
        / f"BL_TrendMonitor_{theme}_V6_Opus5_P1_Retopo.blend"
    )


def fbx_path(project_root, theme):
    return (
        project_root
        / TREE.format(theme=theme)
        / f"SM_TrendMonitor_{theme}_V6_Opus5_P1.fbx"
    )


def rounded_box(centre, size, radius, near_z, far_z, material, name):
    outline = [
        (centre[0] + x, centre[1] + y)
        for x, y in p1.rounded_rectangle(size[0], size[1], radius, 2)
    ]
    return p1.slab(name, outline, near_z, far_z, material)


def build_theme(theme, spec):
    bpy.ops.wm.read_homefile(use_empty=True)
    collection = bpy.context.collection
    opaque = p1.make_material(
        f"MAT_{theme}_Monitor_Solid_Opaque", spec["opaque_colour"]
    )
    readout = p1.make_material(
        f"MAT_{theme}_Monitor_Solid_Readout", spec["readout_colour"], True
    )
    root = bpy.data.objects.new(root_name(theme), None)
    collection.objects.link(root)
    root["opus5_id"] = root_name(theme)

    body = spec["body"]
    depth = spec["body_depth"]
    radius = spec["corner_radius"]
    parts = []

    housing = bpy.data.objects.new(
        "housing",
        p1.slab(
            "housing",
            p1.rounded_rectangle(body[0], body[1], radius, p1.CORNER_SEGMENTS),
            0.0, depth, opaque,
        ),
    )
    collection.objects.link(housing)

    front = depth
    shroud = spec.get("shroud")
    if shroud:
        # Steps out past the body, so the silhouette is a hood rather than a
        # thicker slab.
        piece = bpy.data.objects.new(
            "shroud",
            p1.frame(
                "shroud",
                p1.rounded_rectangle(
                    body[0] + shroud["outset"] * 2, body[1] + shroud["outset"] * 2,
                    radius + shroud["outset"], p1.CORNER_SEGMENTS,
                ),
                p1.rounded_rectangle(
                    body[0] - 0.030, body[1] - 0.030, radius, p1.CORNER_SEGMENTS
                ),
                front, front + shroud["depth"], opaque,
            ),
        )
        collection.objects.link(piece)
        parts.append(piece)
        front += shroud["depth"]

    bezel_outer = p1.rounded_rectangle(
        body[0] - spec["bezel_inset"] * 2, body[1] - spec["bezel_inset"] * 2,
        max(radius - spec["bezel_inset"], 0.004), p1.CORNER_SEGMENTS,
    )
    bezel_inner = p1.rounded_rectangle(*OPENING, radius * 0.5, p1.CORNER_SEGMENTS)
    bezel_front = front + spec["bezel_depth"]
    bezel = bpy.data.objects.new(
        "bezel",
        p1.frame("bezel", bezel_outer, bezel_inner, front, bezel_front, opaque),
    )
    collection.objects.link(bezel)
    parts.append(bezel)

    top = bezel_front
    retaining = spec.get("retaining_frame")
    if retaining:
        outer = p1.rounded_rectangle(
            body[0] - retaining["inset"] * 2, body[1] - retaining["inset"] * 2,
            max(radius - retaining["inset"], 0.004), p1.CORNER_SEGMENTS,
        )
        inner = p1.rounded_rectangle(
            body[0] - (retaining["inset"] + retaining["width"]) * 2,
            body[1] - (retaining["inset"] + retaining["width"]) * 2,
            max(radius - retaining["inset"] - retaining["width"], 0.003),
            p1.CORNER_SEGMENTS,
        )
        piece = bpy.data.objects.new(
            "retaining_frame",
            p1.frame(
                "retaining_frame", outer, inner,
                bezel_front, bezel_front + retaining["depth"], opaque,
            ),
        )
        collection.objects.link(piece)
        parts.append(piece)
        top = bezel_front + retaining["depth"]

    for spot in spec.get("lugs", {}).get("at", []):
        lug = spec["lugs"]
        piece = bpy.data.objects.new(
            "lug",
            rounded_box(spot, lug["size"], 0.004, top, top + lug["height"], opaque, "lug"),
        )
        collection.objects.link(piece)
        parts.append(piece)

    guards = spec.get("guards")
    if guards:
        for sign_x in (-1.0, 1.0):
            for sign_y in (-1.0, 1.0):
                piece = bpy.data.objects.new(
                    "guard",
                    rounded_box(
                        (sign_x * guards["at"][0], sign_y * guards["at"][1]),
                        guards["size"], 0.005,
                        bezel_front, bezel_front + guards["height"], opaque, "guard",
                    ),
                )
                collection.objects.link(piece)
                parts.append(piece)

    fasteners = spec.get("fasteners")
    if fasteners:
        for sign_x in (-1.0, 1.0):
            for sign_y in (-1.0, 1.0):
                outline = [
                    (
                        sign_x * fasteners["at"][0]
                        + fasteners["radius"] * math.cos(math.radians(a)),
                        sign_y * fasteners["at"][1]
                        + fasteners["radius"] * math.sin(math.radians(a)),
                    )
                    for a in range(0, 360, 45)
                ]
                piece = bpy.data.objects.new(
                    "fastener",
                    p1.slab(
                        "fastener", outline, bezel_front,
                        bezel_front + fasteners["height"], opaque,
                    ),
                )
                collection.objects.link(piece)
                parts.append(piece)

    static_opaque = p1.join_into(housing, parts)
    static_opaque.name = "static_opaque"
    static_opaque.parent = root
    static_opaque["opus5_id"] = "static_opaque"

    bars = []
    offsets = spec.get("readout_offsets_x", [0.0] * len(spec["readout_bars"]))
    for index, (width, height, centre_y) in enumerate(spec["readout_bars"]):
        bar = bpy.data.objects.new(
            "readout_bar",
            rounded_box(
                (offsets[index], centre_y), (width, height), min(height / 2.4, 0.0035),
                bezel_front, bezel_front + spec["readout_height"], readout, "readout_bar",
            ),
        )
        collection.objects.link(bar)
        bars.append(bar)
    strip = p1.join_into(bars[0], bars[1:])
    strip.name = "static_readout"
    strip.parent = root
    strip["opus5_id"] = "static_readout"

    screen_z = bezel_front - DISPLAY_RECESS
    # The screen takes the opaque role, not the accent one. Sharing the accent
    # material turned Kinetic Safety's whole display orange, which is the
    # opposite of "accent on a small area of the body" - and the traces Codex
    # draws are what should light the screen, not the screen itself.
    display = bpy.data.objects.new(
        "display_surface", p1.plane("display_surface", *DISPLAY, screen_z, opaque)
    )
    collection.objects.link(display)
    display.parent = root
    display["opus5_id"] = "display_surface"
    bpy.context.view_layer.update()
    return root, display, screen_z


def check_contract(report, theme):
    bounds = report["bounds"]
    size = [round(bounds["max"][i] - bounds["min"][i], 6) for i in range(3)]
    rows = {
        "envelope_m": size,
        "envelope_within_limit": all(
            size[i] <= ENVELOPE_LIMIT[i] + 1e-9 for i in range(3)
        ),
        "opening_m": list(OPENING),
        "opening_at_least_minimum": (
            OPENING[0] >= OPENING_MINIMUM[0] and OPENING[1] >= OPENING_MINIMUM[1]
        ),
        "mount_plane_z0": abs(bounds["min"][2]) < 1e-9,
        # `measure` returns tuples; comparing them with a list of lists is
        # always false and would have reported a healthy screen as failing.
        "display_normal_plus_z": [list(n) for n in report["display_normals"]]
        == [[0.0, 0.0, 1.0]],
        "display_recess_m": DISPLAY_RECESS,
        "renderers": len(report["objects"]),
        "renderers_within_limit": len(report["objects"]) <= 3,
        "material_roles": sorted(
            {
                "readout" if "Readout" in name else "opaque"
                for row in report["objects"].values()
                for name in row["materials"]
            }
        ),
        "triangles": report["triangles_total"],
        "triangles_within_target": report["triangles_total"] <= 5000,
        "object_names": sorted(report["objects"]),
        "object_names_expected": sorted(report["objects"])
        == ["display_surface", "static_opaque", "static_readout"],
    }
    rows["pass"] = all(
        rows[key]
        for key in (
            "envelope_within_limit", "opening_at_least_minimum", "mount_plane_z0",
            "display_normal_plus_z", "renderers_within_limit",
            "triangles_within_target", "object_names_expected",
        )
    ) and len(rows["material_roles"]) <= 2
    return rows


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


def render_theme(theme, root, output_dir):
    review.configure_scene()
    focus = (0.0, 0.0, 0.03)
    written = {}
    for name, view in p1.VIEWS.items():
        path = output_dir / f"Preview_TrendMonitor_{theme}_P1_{name}.png"
        p1.shot(focus, 0.78, view, 55.0, 0.30, path)
        written[name] = path
    return written


def comparison_sheet(images, project_root, output_path):
    order = ["front", "oblique_left", "oblique_right", "side"]
    themes = list(THEMES)
    tiles = [[review.load_rgba(images[t][v]) for v in order] for t in themes]
    height, width = tiles[0][0].shape[:2]
    gap = 14
    canvas = np.zeros(
        (len(themes) * height + (len(themes) - 1) * gap,
         len(order) * width + (len(order) - 1) * gap, 4),
        dtype=np.float32,
    )
    canvas[..., 3] = 1.0
    for row_index, row in enumerate(tiles):
        top = (len(themes) - 1 - row_index) * (height + gap)
        for column, tile in enumerate(row):
            canvas[top : top + height, column * (width + gap) :
                   column * (width + gap) + width] = tile
    for row_index, theme in enumerate(themes):
        for column, view in enumerate(order):
            review.draw_label(
                canvas, theme.upper(), column * (width + gap) + 14,
                row_index * (height + gap) + 14,
            )
            review.draw_label(
                canvas, view.upper().replace("_", " "),
                column * (width + gap) + 14, row_index * (height + gap) + 56,
                colour=(0.72, 0.78, 0.86),
            )
    review.save_rgba(canvas, output_path)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    payload = {
        "phase": "TrendMonitor-themes",
        "note": (
            "Three themes from the approved Orbital Analog P1 (alignment "
            "232). The display contract is identical across all three; the "
            "instrument around it differs by form, not by colour alone."
        ),
        "fixed_contract": {
            "mount_plane": "local Z = 0",
            "display_normal": "local +Z",
            "origin": "mount centre, scale (1, 1, 1)",
            "opening_m": list(OPENING),
            "display_m": list(DISPLAY),
            "display_recess_m": DISPLAY_RECESS,
            "envelope_limit_m": list(ENVELOPE_LIMIT),
            "objects": ["static_opaque", "static_readout", "display_surface"],
        },
        "themes": {},
    }
    images = {}
    for theme, spec in THEMES.items():
        root, display, screen_z = build_theme(theme, spec)
        report = p1.measure(root, display)
        blend = blend_path(project_root, theme)
        blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
        fbx = export(root, fbx_path(project_root, theme))
        output_dir = project_root / TREE.format(theme=theme) / "review"
        output_dir.mkdir(parents=True, exist_ok=True)
        images[theme] = render_theme(theme, root, output_dir)
        payload["themes"][theme] = {
            "root": root_name(theme),
            "blend": str(blend.relative_to(project_root)),
            "blend_sha256": m1.digest(blend),
            "fbx": str(fbx.relative_to(project_root)),
            "fbx_sha256": m1.digest(fbx),
            "fbx_bytes": fbx.stat().st_size,
            "blender_version": bpy.app.version_string,
            "screen_z_m": round(screen_z, 6),
            "objects": report["objects"],
            "triangles_total": report["triangles_total"],
            "bounds": report["bounds"],
            "display_normals": report["display_normals"],
            "contract": check_contract(report, theme),
            "images": {
                name: str(path.relative_to(project_root))
                for name, path in images[theme].items()
            },
        }
        print(
            f"[TrendMonitorThemes] {theme}: {report['triangles_total']} tris, "
            f"contract pass {payload['themes'][theme]['contract']['pass']}"
        )
    sheet_dir = project_root / "ArtSource/Blender/BrushUp/Opus5/OrbitalAnalog/contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    sheet = sheet_dir / "ContactSheet_TrendMonitor_AllThemes_P1.png"
    comparison_sheet(images, project_root, sheet)
    payload["comparison_sheet"] = str(sheet.relative_to(project_root))
    payload["comparison_sheet_sha256"] = m1.digest(sheet)
    payload["all_pass"] = all(
        row["contract"]["pass"] for row in payload["themes"].values()
    )
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[TrendMonitorThemes] all_pass {payload['all_pass']}, sheet {sheet.name}")


if __name__ == "__main__":
    main()
