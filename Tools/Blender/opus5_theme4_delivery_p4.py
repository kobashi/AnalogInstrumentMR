"""Theme 4 P4 delivery: normal-map knurl, and a needle gate that can fail.

Alignment 290. Two things change from P3 and nothing else does.

The Lever grip's diamond knurl is now a tangent-space normal map instead of
mesh displacement. Keeping the two-material contract means the pattern cannot
have a material of its own, so the body quadrant of the *Normal* atlas is
split in two: the top half carries the knurl, the bottom half stays flat, and
the Lever grip is the only UV island in the top half. The grip stays a body
surface - same colour, metallic and smoothness as every other housing face -
because both halves of the body quadrant hold the same body role values.
BaseColor, MetallicSmoothness and Emission therefore come out byte-identical
to P2's. Only the Normal map differs, and only inside one 512x256 block.

The MeterRound needle gate is rebuilt. P3 counted cyan pixels across every
review image, which the ticks alone satisfied, so a needle that drew nothing
passed. P4 renders the needle on its own with a transparent film at -115, 0
and +115 degrees and gates on the alpha coverage, on the distance from the
pivot to the farthest lit pixel against the distance the geometry predicts,
and on the blade being unbroken between the two.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_delivery_p4.py -- \
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
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_machined_ergonomics_p4 as p4
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_material_p2 as m2

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p4"
OUTPUT = f"{TREE}/theme4_delivery_p4.json"

# The grip is its own role only so that it can have its own slice of the
# atlas. It resolves to the metal surface values everywhere it matters, so
# BaseColor / MetallicSmoothness / Emission see no new role at all.
ROLE_RULES = (
    ("knurl", ("handle_grip",)),
    ("readout", ("tick_", "index_", "needle_", "plate_label")),
    ("gasket", ("gasket",)),
    ("metal", ("screw_", "cover_screw_", "blank", "plug_", "mount_", "access_",
               "collar", "cam_", "gland_", "boss_", "stop_", "detent_",
               "rim_", "pillow_", "handle_hub", "handle_yoke",
               "handle_collar", "handle_roller", "switch_hub",
               "switch_axle", "switch_collar")),
)
# The grip is a body-role surface and stays one. "knurl" exists only to
# give it a private slice of the atlas; it resolves to body everywhere
# colour, metallic, smoothness or emission is decided.
SURFACE_ROLE = {"knurl": "body"}

# Atlas regions in UV. The four quadrants are P2's; "body" and "knurl" are the
# two halves of the *body* quadrant, so the grip keeps the body role's colour,
# metallic and smoothness and only its normal differs. Nothing outside the
# body quadrant can be reached by the knurl however the packing rounds.
def _regions():
    rows = {}
    for role in ("metal", "gasket", "readout"):
        span = d2.quadrant_uv_range(role)
        rows[role] = (span["u"][0], span["v"][0], span["u"][1], span["v"][1])
    body = d2.quadrant_uv_range("body")
    mid = 0.5 * (body["v"][0] + body["v"][1])
    rows["body"] = (body["u"][0], body["v"][0], body["u"][1], mid)
    rows["knurl"] = (body["u"][0], mid, body["u"][1], body["v"][1])
    return rows


REGIONS = _regions()
INSET = d2.QUADRANT_INSET

# Knurl pattern. Counts are chosen for a roughly square 4.7 x 4.9 mm diamond
# on the real grip, and the count around the circumference is an integer so
# the pattern closes across the UV seam.
# The grip's mean circumference and the arm span the patch covers, used to
# turn texel gradients into real slopes. Both are re-measured from the built
# mesh and reported in the UV audit, so a drift here shows up as a number.
GRIP_CIRCUMFERENCE_M = 0.102
GRIP_SPAN_M = 0.1284
KNURL_AROUND = 24
KNURL_ALONG = 30
KNURL_FLANK_DEG = 32.0
# Arm parameter range the patch covers, and the window inside it. The window
# is zero at both ends, so grip faces outside the band clamp onto flat normal.
GRIP_S0, GRIP_S1 = 0.50, 1.00
BAND_S0, BAND_S1 = 0.585, 0.960


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def role_for(name):
    stem = name.split(".")[0]
    for role, prefixes in ROLE_RULES:
        for prefix in prefixes:
            if stem.startswith(prefix) or prefix in stem:
                return role
    return "body"


def palette_of(role):
    return m2.PALETTE[SURFACE_ROLE.get(role, role)]


# ---------------------------------------------------------------------------
# the knurl patch
# ---------------------------------------------------------------------------

def _tri(x):
    """Unit triangular wave in [-1, 1]."""
    return 1.0 - 4.0 * np.abs(x - np.floor(x) - 0.5)


def knurl_normal_block(width, height, island_u, island_v):
    """Tangent-space diamond knurl, phased to the island rather than the block.

    The island does not fill the block - the quadrant inset holds it off the
    edges - so the pattern is laid out in island coordinates and simply keeps
    running into the margin. That is what makes exactly KNURL_AROUND periods
    span the seam, which is what makes the seam invisible.
    """
    px = (np.arange(width) + 0.5) / width
    py = (np.arange(height) + 0.5) / height
    pu = (px - island_u[0]) / (island_u[1] - island_u[0])
    pv = (py - island_v[0]) / (island_v[1] - island_v[0])
    grid_u, grid_v = np.meshgrid(pu, pv)

    window = np.zeros_like(grid_v)
    inside = (grid_v >= 0.0) & (grid_v <= 1.0)
    band0 = (BAND_S0 - GRIP_S0) / (GRIP_S1 - GRIP_S0)
    band1 = (BAND_S1 - GRIP_S0) / (GRIP_S1 - GRIP_S0)
    t = (grid_v - band0) / (band1 - band0)
    lit = inside & (t >= 0.0) & (t <= 1.0)
    window[lit] = np.sin(np.pi * t[lit]) ** 2

    f1 = KNURL_AROUND * grid_u + KNURL_ALONG * grid_v
    f2 = KNURL_AROUND * grid_u - KNURL_ALONG * grid_v
    height_field = window * 0.5 * (_tri(f1) + _tri(f2))

    # Gradients converted to physical slope before they are scaled, because
    # the block is 512x256 for a patch that is very nearly square on the part.
    # Treating pixels as isotropic here would flatten the diamonds along one
    # axis by a factor of two.
    d_v, d_u = np.gradient(height_field)
    metres_x = GRIP_CIRCUMFERENCE_M / (abs(island_u[1] - island_u[0]) * width)
    metres_y = GRIP_SPAN_M / (abs(island_v[1] - island_v[0]) * height)
    slope_u = d_u / metres_x
    slope_v = d_v / metres_y
    scale = np.percentile(np.abs(np.stack([slope_u, slope_v])), 99.5)
    if scale > 1e-9:
        factor = math.tan(math.radians(KNURL_FLANK_DEG)) / scale
        slope_u = slope_u * factor
        slope_v = slope_v * factor
    normal = np.stack([-slope_u, -slope_v, np.ones_like(slope_u)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return normal * 0.5 + 0.5, height_field


def build_textures_p4(output_dir):
    """P2's four maps, with a knurl written into one block of the Normal."""
    atlas = d2.ATLAS
    half = atlas // 2
    base = np.zeros((atlas, atlas, 3), dtype=np.float32)
    normal = np.zeros((atlas, atlas, 3), dtype=np.float32)
    metallic = np.zeros((atlas, atlas, 3), dtype=np.float32)
    smoothness = np.zeros((atlas, atlas), dtype=np.float32)
    emission = np.zeros((atlas, atlas, 3), dtype=np.float32)
    # Quadrants first, exactly as P2 writes them.
    for role, (column, row) in d2.QUADRANTS.items():
        x0, y0 = column * half, row * half
        x1, y1 = x0 + half, y0 + half
        colour = m2.PALETTE[role]
        base[y0:y1, x0:x1] = [d2.srgb(colour[i]) for i in range(3)]
        normal[y0:y1, x0:x1] = [0.5, 0.5, 1.0]
        metallic[y0:y1, x0:x1, 0] = d2.SURFACE[role]["metallic"]
        smoothness[y0:y1, x0:x1] = d2.SURFACE[role]["smoothness"]
        if role == "readout":
            emission[y0:y1, x0:x1] = [
                d2.srgb(min(colour[i] * d2.EMISSION_STRENGTH, 1.0))
                for i in range(3)]

    # Then the knurl, into the Normal map only. Image row 0 is the top, and v
    # runs the other way, so the block's rows come from the region's v range.
    u0, v0, u1, v1 = REGIONS["knurl"]
    x0, x1 = int(round(u0 * atlas)), int(round(u1 * atlas))
    y0, y1 = int(round((1.0 - v1) * atlas)), int(round((1.0 - v0) * atlas))
    width, height = x1 - x0, y1 - y0
    island_u = ((u0 + INSET - u0) / (u1 - u0), (u1 - INSET - u0) / (u1 - u0))
    # v increases upward but the block's rows increase downward.
    island_v = ((v1 - INSET - v0) / (v1 - v0), (v0 + INSET - v0) / (v1 - v0))
    island_v = (1.0 - island_v[0], 1.0 - island_v[1])
    block, field = knurl_normal_block(width, height, island_u, island_v)
    normal[y0:y1, x0:x1] = block

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"T_{THEME}_P4_Atlas"
    paths = {
        "BaseColor": d2.write_png(output_dir / f"{prefix}_BaseColor.png", base),
        "Normal": d2.write_png(output_dir / f"{prefix}_Normal.png", normal),
        "MetallicSmoothness": d2.write_png(
            output_dir / f"{prefix}_MetallicSmoothness.png", metallic,
            alpha=smoothness),
        "Emission": d2.write_png(output_dir / f"{prefix}_Emission.png",
                                 emission),
    }
    stats = {
        "knurl_block_pixels": [x0, y0, x1, y1],
        "knurl_block_size": [width, height],
        "diamonds_around": KNURL_AROUND,
        "diamond_rows": KNURL_ALONG,
        "flank_degrees": KNURL_FLANK_DEG,
        "texels_per_diamond": [round(width / KNURL_AROUND, 2),
                               round(height / KNURL_ALONG, 2)],
        "non_flat_normal_texels": int(np.count_nonzero(
            np.abs(normal - np.array([0.5, 0.5, 1.0])).max(axis=-1) > 1.5 / 255.0)),
        "non_flat_texels_outside_block": int(_outside_block_non_flat(
            normal, x0, y0, x1, y1)),
        "height_field_extremes": [float(field.min()), float(field.max())],
    }
    return paths, stats


def _outside_block_non_flat(normal, x0, y0, x1, y1):
    """Texels that carry relief anywhere the knurl block does not cover."""
    deviation = np.abs(normal - np.array([0.5, 0.5, 1.0])).max(axis=-1)
    mask = deviation > 1.5 / 255.0
    mask[y0:y1, x0:x1] = False
    return int(np.count_nonzero(mask))


# ---------------------------------------------------------------------------
# UVs: a controlled cylindrical map on the grip, region packing for the rest
# ---------------------------------------------------------------------------

def grip_cylindrical_uv(obj, role_of_slot):
    """Replace the grip's projected UVs with an explicit cylinder.

    smart_project cuts the grip into whatever islands the angle limit gives,
    at whatever orientation, which is fine for a flat map and useless for a
    pattern that has to run around the part at a known pitch. u is the angle
    about the arm axis and v is the position along it, so a diamond in the
    atlas is a diamond on the grip. Loops on the wrap face are shifted by one
    period rather than clamped, which is what keeps the seam from smearing
    the whole pattern across a single column of faces.
    """
    start = np.array(p3.LEVER_ARM_A, dtype=float)
    end = np.array(p3.LEVER_ARM_B, dtype=float)
    axis = end - start
    length = float(np.linalg.norm(axis))
    direction = axis / length
    e1 = np.array([1.0, 0.0, 0.0])
    e1 = e1 - direction * float(np.dot(e1, direction))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(direction, e1)

    work = bmesh.new()
    work.from_mesh(obj.data)
    layer = work.loops.layers.uv.active
    faces = 0
    radii = []
    span = []
    for face in work.faces:
        if role_of_slot[face.material_index] != "knurl":
            continue
        faces += 1
        raw = []
        for loop in face.loops:
            point = np.array(loop.vert.co, dtype=float) - start
            along = float(np.dot(point, direction))
            radial = point - along * direction
            radius = float(np.linalg.norm(radial))
            radii.append(radius)
            s = along / length
            span.append(s)
            angle = math.atan2(float(np.dot(radial, e2)),
                               float(np.dot(radial, e1)))
            raw.append(((angle / (2.0 * math.pi)) % 1.0, s))
        reference = min(u for u, _ in raw)
        fixed = [(u - 1.0 if u - reference > 0.5 else u) for u, _ in raw]
        if min(fixed) < 0.0:
            fixed = [u + 1.0 for u in fixed]
        for loop, u, (_, s) in zip(face.loops, fixed, raw):
            v = (s - GRIP_S0) / (GRIP_S1 - GRIP_S0)
            loop[layer].uv = (min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0))
    work.to_mesh(obj.data)
    work.free()
    return {
        "grip_faces": faces,
        "measured_mean_radius_m": round(float(np.mean(radii)), 5) if radii else None,
        "measured_circumference_m": round(2.0 * math.pi * float(np.mean(radii)), 5)
        if radii else None,
        "assumed_circumference_m": GRIP_CIRCUMFERENCE_M,
        "arm_length_m": round(length, 5),
        "patch_span_m": round((GRIP_S1 - GRIP_S0) * length, 5),
        "assumed_span_m": GRIP_SPAN_M,
        "s_range_seen": [round(min(span), 4), round(max(span), 4)] if span else None,
    }


def pack_into_regions(obj, role_of_slot, atlas, emissive):
    """P2's quadrant packing, with the metal quadrant split into two regions."""
    work = bmesh.new()
    work.from_mesh(obj.data)
    layer = work.loops.layers.uv.active
    counts = {}
    faces = {}
    for face in work.faces:
        role = role_of_slot[face.material_index]
        counts[role] = counts.get(role, 0) + 1
        u0, v0, u1, v1 = REGIONS[role]
        for loop in face.loops:
            uv = loop[layer].uv
            uv.x = (u0 + INSET) + min(max(uv.x, 0.0), 1.0) * (u1 - u0 - 2 * INSET)
            uv.y = (v0 + INSET) + min(max(uv.y, 0.0), 1.0) * (v1 - v0 - 2 * INSET)
        faces[face.index] = 0 if role != "readout" else 1
    work.to_mesh(obj.data)
    work.free()

    obj.data.materials.clear()
    obj.data.materials.append(atlas)
    obj.data.materials.append(emissive)
    for polygon in obj.data.polygons:
        polygon.material_index = faces[polygon.index]
    used = sorted({polygon.material_index for polygon in obj.data.polygons})
    if len(used) < len(obj.data.materials):
        remap = {old: new for new, old in enumerate(used)}
        keep = [obj.data.materials[index] for index in used]
        indices = [remap[polygon.material_index] for polygon in obj.data.polygons]
        obj.data.materials.clear()
        for material in keep:
            obj.data.materials.append(material)
        for polygon, index in zip(obj.data.polygons, indices):
            polygon.material_index = index
        used = sorted(set(indices))
    return counts, used


def knurl_bleed_audit(objects):
    """Every loop UV against the knurl block, for every object of every asset.

    The claim the contract asks to be proved is negative - that nothing but
    the Lever grip reads the knurl - so it is measured as a count of foreign
    loops inside the block plus the clearance of the nearest one, rather than
    asserted from the packing code being correct.
    """
    u0, v0, u1, v1 = REGIONS["knurl"]
    inside = {}
    nearest = None
    for label, obj in objects:
        mesh = obj.data
        layer = mesh.uv_layers.active.data
        hits = 0
        for loop_uv in layer:
            u, v = loop_uv.uv
            if u0 <= u <= u1 and v0 <= v <= v1:
                hits += 1
            else:
                distance = max(u0 - u, u - u1, v0 - v, v - v1)
                nearest = distance if nearest is None else min(nearest, distance)
        inside[label] = hits
    return inside, nearest


# ---------------------------------------------------------------------------
# materials: the normal map is wired this time
# ---------------------------------------------------------------------------

def delivery_materials_p4(textures):
    """P2's two materials, plus the Normal input they never had.

    P2 and P3 wired BaseColor, MetallicSmoothness and Emission but left the
    Normal map unconnected, so no review image either pass produced could have
    shown a normal-mapped detail. With the knurl living in that map, leaving
    it unconnected would mean shipping a pattern nobody had looked at.
    """
    base = d2.load_map(textures["BaseColor"], "sRGB")
    packed = d2.load_map(textures["MetallicSmoothness"], "Non-Color")
    bumps = d2.load_map(textures["Normal"], "Non-Color")
    glow = d2.load_map(textures["Emission"], "sRGB")

    def wire(material, emissive):
        material.use_nodes = True
        tree = material.node_tree
        bsdf = tree.nodes.get("Principled BSDF")
        colour = tree.nodes.new("ShaderNodeTexImage")
        colour.image = base
        tree.links.new(colour.outputs["Color"], bsdf.inputs["Base Color"])
        surface = tree.nodes.new("ShaderNodeTexImage")
        surface.image = packed
        tree.links.new(surface.outputs["Color"], bsdf.inputs["Metallic"])
        invert = tree.nodes.new("ShaderNodeMath")
        invert.operation = "SUBTRACT"
        invert.inputs[0].default_value = 1.0
        tree.links.new(surface.outputs["Alpha"], invert.inputs[1])
        tree.links.new(invert.outputs["Value"], bsdf.inputs["Roughness"])
        relief = tree.nodes.new("ShaderNodeTexImage")
        relief.image = bumps
        mapper = tree.nodes.new("ShaderNodeNormalMap")
        mapper.inputs["Strength"].default_value = 1.0
        tree.links.new(relief.outputs["Color"], mapper.inputs["Color"])
        tree.links.new(mapper.outputs["Normal"], bsdf.inputs["Normal"])
        if emissive:
            emit = tree.nodes.new("ShaderNodeTexImage")
            emit.image = glow
            if "Emission Color" in bsdf.inputs:
                tree.links.new(emit.outputs["Color"],
                               bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = 1.0

    atlas = bpy.data.materials.new(f"MAT_{THEME}_P4_Atlas")
    wire(atlas, False)
    emissive = bpy.data.materials.new(f"MAT_{THEME}_P4_Emissive")
    wire(emissive, True)
    return atlas, emissive


# ---------------------------------------------------------------------------
# the needle gate that P3 did not have
# ---------------------------------------------------------------------------

NEEDLE_POSES = (-115.0, 0.0, 115.0)
NEEDLE_MIN_PIXELS = 400
NEEDLE_MIN_REACH = 0.80          # of the reach the geometry predicts
NEEDLE_MAX_BREAK_PX = 4.0


def _front_camera(focus, radius):
    bpy.ops.object.camera_add(location=p1.camera_at(focus, radius, 0.0, 0.0))
    camera = bpy.context.object
    camera.data.lens = 52.0
    review.point_at(camera, focus)
    bpy.context.scene.camera = camera
    return camera


def _pixel_of(camera, point):
    scene = bpy.context.scene
    ndc = world_to_camera_view(scene, camera, Vector(point))
    return (ndc.x * scene.render.resolution_x,
            ndc.y * scene.render.resolution_y)


def needle_isolation_gate(body, pivot, needle, focus, radius, scale,
                          out_dir, project_root):
    """Render the needle alone and measure it, one pose at a time.

    A transparent film makes the mask exact: alpha is coverage, so nothing has
    to be thresholded against a backdrop colour that AgX has already moved.
    The reach test compares the farthest lit pixel with where the blade tip
    actually projects, and the continuity test walks the line between the
    pivot and that pixel, so a needle drawn as a detached sliver fails even
    though its pixel count would pass.
    """
    scene = bpy.context.scene
    rows = {}
    images = {}
    original_film = scene.render.film_transparent
    for degrees in NEEDLE_POSES:
        pivot.rotation_euler = (0.0, math.radians(degrees), 0.0)
        bpy.context.view_layer.update()

        label = f"{int(degrees):+d}"
        full = out_dir / f"Needle_{THEME}_P4_pose{label}.png"
        p1.shot(focus, radius, (0.0, 0.0), 52.0, scale, full)
        images[f"pose{label}"] = str(full.relative_to(project_root))

        matrix = needle.matrix_world
        blade = [matrix @ v.co for v in needle.data.vertices
                 if (v.co.x ** 2 + v.co.z ** 2) ** 0.5 > 0.012]
        tip = max(blade, key=lambda w: w.x * w.x + w.z * w.z)

        scene.render.film_transparent = True
        body.hide_render = True
        camera = _front_camera(focus, radius)
        mask = out_dir / f"NeedleMask_{THEME}_P4_pose{label}.png"
        review.render_to(mask)
        pivot_px = _pixel_of(camera, pivot.matrix_world.translation)
        tip_px = _pixel_of(camera, tip)
        bpy.data.objects.remove(camera, do_unlink=True)
        body.hide_render = False
        scene.render.film_transparent = original_film
        images[f"mask{label}"] = str(mask.relative_to(project_root))

        pixels = review.load_rgba(mask)[..., 3]
        lit = pixels > 0.5
        count = int(np.count_nonzero(lit))
        ys, xs = np.nonzero(lit)
        row = {
            "lit_pixels": count,
            "pivot_pixel": [round(pivot_px[0], 1), round(pivot_px[1], 1)],
            "predicted_tip_pixel": [round(tip_px[0], 1), round(tip_px[1], 1)],
        }
        if count:
            reach = np.sqrt((xs - pivot_px[0]) ** 2 + (ys - pivot_px[1]) ** 2)
            far = int(np.argmax(reach))
            predicted = math.hypot(tip_px[0] - pivot_px[0],
                                   tip_px[1] - pivot_px[1])
            row["measured_reach_px"] = round(float(reach[far]), 1)
            row["predicted_reach_px"] = round(predicted, 1)
            row["reach_ratio"] = round(float(reach[far]) / predicted, 3) \
                if predicted > 1e-6 else 0.0
            # continuity along the line from the pivot to the farthest pixel
            end = (float(xs[far]), float(ys[far]))
            steps = 96
            worst = 0.0
            height, width = lit.shape
            for index in range(steps + 1):
                t = index / steps
                px = pivot_px[0] + (end[0] - pivot_px[0]) * t
                py = pivot_px[1] + (end[1] - pivot_px[1]) * t
                window = 5
                x0 = max(0, int(px) - window); x1 = min(width, int(px) + window + 1)
                y0 = max(0, int(py) - window); y1 = min(height, int(py) + window + 1)
                patch = lit[y0:y1, x0:x1]
                if not patch.any():
                    worst = max(worst, float(window))
                    continue
                py_i, px_i = np.nonzero(patch)
                distance = np.min(np.sqrt((px_i + x0 - px) ** 2
                                          + (py_i + y0 - py) ** 2))
                worst = max(worst, float(distance))
            row["worst_break_px"] = round(worst, 2)
        else:
            row.update({"measured_reach_px": 0.0, "predicted_reach_px": 0.0,
                        "reach_ratio": 0.0, "worst_break_px": 9999.0})
        row["passes"] = (row["lit_pixels"] >= NEEDLE_MIN_PIXELS
                         and row["reach_ratio"] >= NEEDLE_MIN_REACH
                         and row["worst_break_px"] <= NEEDLE_MAX_BREAK_PX)
        rows[label] = row

    pivot.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    return {
        "poses": rows,
        "thresholds": {"min_lit_pixels": NEEDLE_MIN_PIXELS,
                       "min_reach_ratio": NEEDLE_MIN_REACH,
                       "max_break_px": NEEDLE_MAX_BREAK_PX},
        "method": ("needle rendered alone on a transparent film; alpha is the "
                   "mask, so no cyan threshold is involved"),
        "p3_gate_defect": ("P3 counted cyan pixels over whole review images, "
                           "which the ticks satisfied on their own"),
        "all_poses_pass": all(row["passes"] for row in rows.values()),
        "images": images,
    }


# ---------------------------------------------------------------------------

def build(asset, builder):
    p1.clear_scene()
    review.configure_scene()
    roles = m2.make_materials()
    # An authoring-only identity. It carries the body palette and is
    # collapsed into the same delivery slot as every other opaque role, but
    # it has to be a distinct material here because the role a face packs
    # into is read back from its material name.
    knurl = bpy.data.materials.new(f"MAT_{THEME}_Knurl")
    knurl.use_nodes = True
    knurl_bsdf = knurl.node_tree.nodes.get("Principled BSDF")
    if knurl_bsdf is not None:
        knurl_bsdf.inputs["Base Color"].default_value = palette_of("knurl")
    roles["knurl"] = knurl
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    original_join, original_assign = p1.join, p1.assign
    tagged = {}

    def tagging_join(target, others):
        for obj in [target] + list(others):
            role = role_for(obj.name)
            tagged[obj.name.split(".")[0]] = role
            obj.data.materials.clear()
            obj.data.materials.append(roles[role])
        return original_join(target, others)

    p1.join = tagging_join
    p1.assign = lambda obj, material: None
    try:
        body, pivot, part, audit = builder(roles["body"])
    finally:
        p1.join, p1.assign = original_join, original_assign
    for obj in (body, pivot):
        obj.parent = root
    bpy.context.view_layer.update()
    return root, body, pivot, part, tagged, audit


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    review_dir = tree / "review"
    needle_dir = tree / "needle"
    detail_dir = tree / "detail"
    for folder in (tree, review_dir, needle_dir, detail_dir):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P4-delivery",
        "note": ("Knurl moved from mesh to the Normal atlas, in one 512x256 "
                 "block of the *body* quadrant that only the Lever grip's UV "
                 "island reaches. The grip keeps the body role's colour, "
                 "metallic and smoothness; BaseColor, MetallicSmoothness and "
                 "Emission stay byte-identical to P2."),
        "atlas_pixels": d2.ATLAS,
        "regions_uv": {role: list(box) for role, box in REGIONS.items()},
        "region_inset_uv": INSET,
        "region_surface_source": {"knurl": "body"},
        "surface": d2.SURFACE,
        "knurl_patch": knurl_stats,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "assets": {},
    }

    bleed_hits, bleed_nearest = {}, []
    for asset, builder in p4.BUILDERS_P4.items():
        root, body, pivot, part, tagged, audit = build(asset, builder)
        for obj in (body, part):
            m2.unwrap(obj)
        atlas, emissive = delivery_materials_p4(textures)
        rows = {}
        grip_uv = None
        for obj in (body, part):
            role_of_slot = [slot.material.name.rsplit("_", 1)[-1].lower()
                            for slot in obj.material_slots]
            if "knurl" in role_of_slot:
                grip_uv = grip_cylindrical_uv(obj, role_of_slot)
            counts, used = pack_into_regions(obj, role_of_slot, atlas, emissive)
            rows[obj.name] = {
                "role_face_counts": counts,
                "material_slots": [s.material.name for s in obj.material_slots],
                "submeshes": len(used),
            }
        bpy.context.view_layer.update()
        # Measured now, while these objects still exist: clear_scene() frees
        # them before the next asset is built.
        hits, closest = knurl_bleed_audit(
            [(f"{asset}:{obj.name}", obj) for obj in (body, part)])
        bleed_hits.update(hits)
        if closest is not None:
            bleed_nearest.append(closest)

        scan = p1.sweep_scan(pivot, body, part, p1.MOTION[asset])
        measured = p1.measure(asset, root, body, pivot, part, scan)
        measured["pose_bounds"] = p1.pose_bounds(pivot, body, part,
                                                 p1.MOTION[asset], scan)
        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P4.fbx"
        d2.export_fbx(root, fbx)

        review.configure_scene()
        focus, radius, scale = p1.rig_for([body, part])
        images = {}
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Delivery_{asset}_{THEME}_P4_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))

        row = {
            "p4_fbx": str(fbx.relative_to(project_root)),
            "p4_fbx_sha256": m1.digest(fbx),
            "p4_fbx_bytes": fbx.stat().st_size,
            "objects": rows,
            "renderers": 2,
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "triangles_per_object": measured["triangles_per_object"],
            "non_manifold_edges": measured["non_manifold_edges"],
            "zero_area_faces": measured["zero_area_faces"],
            "rest_bounds_whd": measured["measured_width_height_depth"],
            "within_envelope": measured["within_envelope"],
            "mount_plane_max_y": measured["mount_plane_max_y"],
            "motion": measured["motion"],
            "runtime_motion_clearance": measured["runtime_motion_clearance"],
            "collider_union_unity":
                measured["pose_bounds"]["collider_union_unity"],
            "coplanar_overlap": audit,
            "images": images,
        }
        if asset == "MeterRound":
            row["needle_gate"] = needle_isolation_gate(
                body, pivot, part, focus, radius, scale, needle_dir,
                project_root)
        if asset == "Lever":
            row["grip_uv"] = grip_uv
            grip = (0.0, p3.PIVOTS["Lever"][1][1] - 0.076,
                    p3.PIVOTS["Lever"][1][2] + 0.208)
            path = detail_dir / f"Detail_{asset}_knurl_normal.png"
            p1.shot(grip, 0.150, (34.0, 12.0), 125.0, 0.072, path)
            row["detail_images"] = {
                "knurl_normal": str(path.relative_to(project_root))}
            wide = detail_dir / f"Detail_{asset}_grip_wide.png"
            p1.shot(grip, 0.230, (30.0, 16.0), 62.0, 0.115, wide)
            row["detail_images"]["grip_wide"] = str(
                wide.relative_to(project_root))
        if asset == "Toggle":
            axis_y = p3.PIVOTS["Toggle"][1][1]
            path = detail_dir / f"Detail_{asset}_axle_material.png"
            p1.shot((0.0, axis_y - 0.004, 0.0), 0.115, (16.0, 14.0), 74.0,
                    0.057, path)
            row["detail_images"] = {
                "axle": str(path.relative_to(project_root))}
        payload["assets"][asset] = row
        print(f"[Theme4DeliveryP4] {asset}: slots "
              f"{row['max_material_slots_per_object']}, clearance "
              f"{measured['runtime_motion_clearance']['clearance_mm']} mm")

    inside = bleed_hits
    nearest = min(bleed_nearest) if bleed_nearest else None
    foreign = {label: count for label, count in inside.items()
               if count and label != "Lever:handle"}
    payload["knurl_bleed"] = {
        "loops_inside_knurl_region": inside,
        "objects_other_than_lever_handle_with_loops_inside": foreign,
        "nearest_foreign_uv_to_region_uv": round(nearest, 5)
        if nearest is not None else None,
        "nearest_foreign_uv_to_region_texels": round(nearest * d2.ATLAS, 1)
        if nearest is not None else None,
        "clean": not foreign,
    }

    rows = [(asset, [(label, project_root / row["images"][label])
                     for label in ("front", "oblique_left",
                                   "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    grey = tree / f"ContactSheet_Theme4_{THEME}_P4_grayscale.png"
    p1.comparison_sheet(rows, grey)
    colour = tree / f"ContactSheet_Theme4_{THEME}_P4_colour.png"
    tiles = [review.load_rgba(project_root / row["images"][label])
             for _, row in payload["assets"].items()
             for label in ("front", "oblique_left", "oblique_right", "side")]
    height, width = tiles[0].shape[:2]
    gap = 16
    canvas = np.zeros((3 * height + 2 * gap, 4 * width + 3 * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        r, c = divmod(index, 4)
        top = (2 - r) * (height + gap)
        canvas[top:top + height,
               c * (width + gap):c * (width + gap) + width] = tile
    review.save_rgba(canvas, colour)
    payload["contact_sheets"] = {
        "colour": {"path": str(colour.relative_to(project_root)),
                   "sha256": m1.digest(colour)},
        "grayscale": {"path": str(grey.relative_to(project_root)),
                      "sha256": m1.digest(grey)},
    }
    payload["shared_material_identities"] = sorted(
        {n for row in payload["assets"].values()
         for obj in row["objects"].values() for n in obj["material_slots"]})
    payload["max_material_slots_any_object"] = max(
        row["max_material_slots_per_object"]
        for row in payload["assets"].values())
    payload["needle_gate"] = payload["assets"]["MeterRound"]["needle_gate"]
    payload["status"] = (
        "p4_delivery_ready"
        if payload["max_material_slots_any_object"] <= 2
        and len(payload["shared_material_identities"]) <= 2
        and all(row["non_manifold_edges"] == 0 and row["zero_area_faces"] == 0
                for row in payload["assets"].values())
        and all(t <= 5000 for row in payload["assets"].values()
                for t in row["triangles_per_object"].values())
        and payload["needle_gate"]["all_poses_pass"]
        and payload["knurl_bleed"]["clean"]
        and knurl_stats["non_flat_texels_outside_block"] == 0
        else "p4_delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4DeliveryP4] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
