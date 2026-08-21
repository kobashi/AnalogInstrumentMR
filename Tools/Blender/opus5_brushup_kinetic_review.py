"""Fixed-camera review renders for the Opus 5 Kinetic Safety brush-up pilot.

Renders the shot list the brush-up handoff requires, for the production
baseline and for the Opus 5 candidate, using identical cameras, lights, world,
exposure and resolution so the two are directly comparable. Then it composes a
Before / After contact sheet per shot.

The script only reads blends; it never saves one.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_brushup_kinetic_review.py -- \
      --project-root "$PWD"
"""

import argparse
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_hardsurface_lever_prototype as hs
import opus5_brushup_kinetic_pilot as pilot
import v6_theme_materials


THEME = "KineticSafety"
RESOLUTION = 900
CONTACT_GAP = 16
LABEL_SCALE = 5

# Fixed per-object camera rigs. These are constants rather than bounds-derived
# values so the baseline and the candidate are framed identically even though
# their bounds differ.
RIGS = {
    "MeterRound": {
        "focus": (0.0, -0.040, 0.0),
        "radius": 0.360,
        "lens": 62.0,
        "light_scale": 0.170,
        # The close-up stays outside the model and uses a long lens, otherwise
        # the camera sits between the guards and clips into the housing.
        "pivot_focus": (0.0, -0.070, 0.006),
        "pivot_radius": 0.320,
        "pivot_lens": 125.0,
        "pivot_view": (34.0, 7.0),
    },
    "Lever": {
        "focus": (0.0, -0.045, 0.050),
        "radius": 0.560,
        "lens": 60.0,
        "light_scale": 0.260,
        # A pure side view is blocked by the shoulder and the guide rib, so the
        # bearing close-up looks down into the recess instead.
        "pivot_focus": (0.0, -0.058, -0.018),
        "pivot_radius": 0.440,
        "pivot_lens": 125.0,
        "pivot_view": (46.0, 24.0),
        "pose_focus": (0.0, -0.080, 0.045),
        "pose_radius": 0.750,
        "pose_lens": 55.0,
    },
    "Throttle": {
        "focus": (0.0, -0.060, 0.000),
        "radius": 0.760,
        "lens": 58.0,
        "light_scale": 0.360,
        "pivot_focus": (0.0, -0.088, -0.104),
        "pivot_radius": 0.520,
        "pivot_lens": 125.0,
        "pivot_view": (54.0, 20.0),
        "pose_focus": (0.0, -0.140, 0.000),
        "pose_radius": 1.050,
        "pose_lens": 52.0,
    },
}

VIEWS = {
    "front_three_quarter": (32.0, 22.0),
    "opposite_three_quarter": (-38.0, -18.0),
    "side_profile": (90.0, 0.0),
}

# A 5x7 bitmap font for contact sheet labels. `draw_label` silently advances
# past any character that is missing, so a label with an unlisted glyph loses
# letters rather than failing - add the glyph here instead of dropping the word.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10001", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--object",
        dest="object_key",
        choices=tuple(RIGS),
        action="append",
    )
    parser.add_argument("--revision", default="R1")
    return parser.parse_args(args)


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera_position(focus, radius, azimuth_degrees, elevation_degrees):
    azimuth = math.radians(azimuth_degrees)
    elevation = math.radians(elevation_degrees)
    return (
        focus[0] + radius * math.sin(azimuth) * math.cos(elevation),
        focus[1] - radius * math.cos(azimuth) * math.cos(elevation),
        focus[2] + radius * math.sin(elevation),
    )


def build_rig(rig, focus, radius, azimuth, elevation, lens):
    bpy.ops.object.camera_add(
        location=camera_position(focus, radius, azimuth, elevation)
    )
    camera = bpy.context.object
    camera.name = "Opus5ReviewCamera"
    camera.data.lens = lens
    point_at(camera, focus)
    bpy.context.scene.camera = camera

    scale = rig["light_scale"]
    # Light positions scale with the model, so wattage has to scale with the
    # square of that distance or a large fixture arrives underlit. The pilot
    # rigs leave this at 1.0 and are unaffected.
    energy_scale = rig.get("energy_scale", 1.0)
    lights = []
    for name, offset, energy, size in (
        ("Key", (scale * 1.6, -scale * 2.2, scale * 2.0), 9.0, scale * 2.2),
        ("Fill", (-scale * 2.4, -scale * 1.7, scale * 0.4), 3.6, scale * 2.6),
        ("Rim", (0.0, scale * 1.1, scale * 2.2), 5.5, scale * 1.6),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy * energy_scale
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        light.location = (
            focus[0] + offset[0],
            focus[1] + offset[1],
            focus[2] + offset[2],
        )
        bpy.context.collection.objects.link(light)
        point_at(light, focus)
        lights.append(light)
    return camera, lights


def configure_scene():
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Opus5ReviewWorld")
    scene.world.use_nodes = False
    scene.world.color = (0.012, 0.016, 0.022)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def render_to(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def shot(rig, focus, radius, view, lens, path):
    azimuth, elevation = view
    camera, lights = build_rig(rig, focus, radius, azimuth, elevation, lens)
    render_to(path)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)


def set_pose(root, key, angle_degrees):
    spec = pilot.PILOT[key]
    pivot = bpy.data.objects[spec["pivot"]]
    axis = Vector(spec["axis"]).normalized()
    pivot.rotation_mode = "AXIS_ANGLE"
    pivot.rotation_axis_angle = (
        math.radians(angle_degrees),
        axis.x,
        axis.y,
        axis.z,
    )
    bpy.context.view_layer.update()


def add_wireframe(root):
    wire = hs.material(
        "MAT_Opus5_Review_Wire",
        (0.005, 0.015, 0.020, 1.0),
        0.0,
        0.45,
        emission=(0.02, 0.70, 0.90, 1.0),
    )
    duplicates = []
    for source in [
        obj for obj in root.children_recursive if obj.type == "MESH"
    ]:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.parent = None
        duplicate.matrix_world = source.matrix_world.copy()
        duplicate.data.materials.clear()
        duplicate.data.materials.append(wire)
        bpy.context.collection.objects.link(duplicate)
        modifier = duplicate.modifiers.new("Review Wire", "WIREFRAME")
        modifier.thickness = 0.00028
        modifier.use_even_offset = True
        duplicates.append(duplicate)
    return duplicates


def render_set(project_root, blend_path, key, tag, output_dir):
    spec = pilot.PILOT[key]
    rig = RIGS[key]
    bpy.ops.wm.open_mainfile(filepath=str(blend_path), load_ui=False)
    configure_scene()
    root = bpy.data.objects[spec["root"]]
    focus = rig["focus"]
    radius = rig["radius"]
    lens = rig["lens"]
    poses = spec["labelled_poses"]

    written = {}

    def name_for(label):
        return output_dir / f"Preview_{key}_{THEME}_V6_{tag}_{label}.png"

    set_pose(root, key, poses["neutral"])
    for label, view in VIEWS.items():
        path = name_for(f"grayscale_{label}")
        shot(rig, focus, radius, view, lens, path)
        written[f"grayscale_{label}"] = path

    pose_focus = rig.get("pose_focus", focus)
    pose_radius = rig.get("pose_radius", radius)
    pose_lens = rig.get("pose_lens", lens)
    for label, angle in (
        ("pose_minimum", poses["minimum"]),
        ("pose_neutral", poses["neutral"]),
        ("pose_maximum", poses["maximum"]),
    ):
        set_pose(root, key, angle)
        path = name_for(label)
        shot(
            rig,
            pose_focus,
            pose_radius,
            VIEWS["side_profile"],
            pose_lens,
            path,
        )
        written[label] = path

    for label, angle in (
        ("pivot_closeup_minimum", poses["minimum"]),
        ("pivot_closeup_maximum", poses["maximum"]),
    ):
        set_pose(root, key, angle)
        path = name_for(label)
        shot(
            rig,
            rig["pivot_focus"],
            rig["pivot_radius"],
            rig["pivot_view"],
            rig["pivot_lens"],
            path,
        )
        written[label] = path

    set_pose(root, key, poses["neutral"])
    duplicates = add_wireframe(root)
    path = name_for("topology")
    shot(rig, focus, radius, VIEWS["front_three_quarter"], lens, path)
    written["topology"] = path
    for duplicate in duplicates:
        bpy.data.objects.remove(duplicate, do_unlink=True)

    materials = v6_theme_materials.apply(project_root, THEME, "Standard")
    v6_theme_materials.assign_special_roles(root, materials)
    for label, enabled in (("pbr_emissive_off", False), ("pbr_emissive_on", True)):
        v6_theme_materials.set_emission_enabled(enabled)
        path = name_for(label)
        shot(rig, focus, radius, VIEWS["front_three_quarter"], lens, path)
        written[label] = path

    # Quest reading distance: the same frame at 128 px and 64 px shows whether
    # the silhouette and the readout still separate at 1-3 m.
    scene = bpy.context.scene
    v6_theme_materials.set_emission_enabled(True)
    for label, size in (("readability_128", 128), ("readability_064", 64)):
        scene.render.resolution_x = size
        scene.render.resolution_y = size
        path = name_for(label)
        shot(rig, focus, radius, VIEWS["front_three_quarter"], lens, path)
        written[label] = path
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    return written


# ---------------------------------------------------------------------------
# Contact sheet composition
# ---------------------------------------------------------------------------


def load_rgba(path):
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = image.size
    buffer = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    bpy.data.images.remove(image)
    return buffer.reshape(height, width, 4)


def save_rgba(array, path):
    height, width = array.shape[:2]
    # A byte buffer keeps the sheet at 8 bits per channel; a float buffer writes
    # a 16-bit PNG and triples the size for no review benefit.
    image = bpy.data.images.new(path.stem, width, height, alpha=True, float_buffer=False)
    image.colorspace_settings.name = "sRGB"
    image.pixels.foreach_set(array.reshape(-1).astype(np.float32))
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def draw_label(array, text, origin_x, origin_y, colour=(1.0, 1.0, 1.0)):
    """Blit a 5x7 bitmap label. Image rows run bottom-up in Blender."""
    height = array.shape[0]
    cursor = origin_x
    for character in text.upper():
        glyph = GLYPHS.get(character)
        if glyph is None:
            cursor += 6 * LABEL_SCALE
            continue
        for row_index, row in enumerate(glyph):
            for column_index, cell in enumerate(row):
                if cell != "1":
                    continue
                x0 = cursor + column_index * LABEL_SCALE
                # Row 0 of the buffer is the bottom of the image, so the top
                # glyph row has to land on the highest buffer row.
                y_start = height - origin_y - (row_index + 1) * LABEL_SCALE
                array[
                    y_start : y_start + LABEL_SCALE,
                    x0 : x0 + LABEL_SCALE,
                    0:3,
                ] = colour
                array[
                    y_start : y_start + LABEL_SCALE,
                    x0 : x0 + LABEL_SCALE,
                    3,
                ] = 1.0
        cursor += 6 * LABEL_SCALE
    return array


def contact_sheet(before_path, after_path, output_path):
    before = load_rgba(before_path)
    after = load_rgba(after_path)
    height = max(before.shape[0], after.shape[0])
    width = before.shape[1] + CONTACT_GAP + after.shape[1]
    canvas = np.zeros((height, width, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    canvas[: before.shape[0], : before.shape[1]] = before
    canvas[
        : after.shape[0],
        before.shape[1] + CONTACT_GAP :,
    ] = after
    draw_label(canvas, "BEFORE", 18, 18)
    draw_label(canvas, "AFTER", before.shape[1] + CONTACT_GAP + 18, 18)
    save_rgba(canvas, output_path)


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    keys = args.object_key or list(RIGS)
    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME
    review_dir = candidate_dir / "review"
    sheet_dir = candidate_dir / "contact_sheets"

    for key in keys:
        baseline = (
            project_root
            / "ArtSource/Blender/ThemeHardSurfaceV6"
            / THEME
            / f"BL_{key}_{THEME}_V6_Retopo.blend"
        )
        candidate = (
            candidate_dir
            / f"BL_{key}_{THEME}_V6_Opus5_{args.revision}_Retopo.blend"
        )
        for path in (baseline, candidate):
            if not path.is_file():
                raise FileNotFoundError(path)

        before = render_set(project_root, baseline, key, "Baseline", review_dir)
        after = render_set(
            project_root,
            candidate,
            key,
            f"Opus5_{args.revision}",
            review_dir,
        )
        for label in sorted(before):
            contact_sheet(
                before[label],
                after[label],
                sheet_dir
                / f"ContactSheet_{key}_{THEME}_V6_Opus5_{args.revision}_{label}.png",
            )
        print(f"[Opus5Review] {key}: {len(before)} shots, {len(before)} contact sheets")


if __name__ == "__main__":
    main()
