"""Theme 4 Phase 2: material and UV design. No geometry is re-authored.

Alignment 272.1. The Phase 1 greybox carries one flat material; this pass
assigns the four authoring roles the style guide names - body, metal, gasket,
readout - to the parts that already exist, proposes a 1 K atlas layout, and
measures what the proposal costs in texel density and atlas occupancy.

Nothing about the shape changes. The Phase 1 builders are imported and run
unmodified; only `join` is wrapped, to give each part its role material before
the parts are merged, and `assign` is silenced so the single-material call at
the end of each builder does not undo that. The report re-measures triangles,
bounds and pivots against the Phase 1 figures and fails if any of them moved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_material_p2.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_theme4_machined_ergonomics_p1 as p1

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics"
OUTPUT = "ArtSource/Blender/BrushUp/Opus5/theme4_material_p2.json"
PHASE1 = "ArtSource/Blender/BrushUp/Opus5/theme4_machined_ergonomics_p1.json"
ATLAS = 1024
# Fraction of the sheet the islands may occupy; the rest is gutter.
ATLAS_BUDGET = 0.85

# Authoring roles, per alignment 272.1(1). Delivery collapses body / metal /
# gasket into one opaque material and leaves readout emissive - 272.1(2).
DELIVERY = {"body": "opaque", "metal": "opaque", "gasket": "opaque",
            "readout": "emissive"}

# Linear base colours. The guide asks for a light warm resin body, an anodised
# machined accent and a dark elastomer grip; these values are chosen so the
# three separate in grayscale as well as in hue - alignment 272.1(5).
PALETTE = {
    "body": (0.620, 0.600, 0.575, 1.0),
    "metal": (0.300, 0.312, 0.332, 1.0),
    "gasket": (0.085, 0.085, 0.092, 1.0),
    "readout": (0.300, 0.880, 0.950, 1.0),
}

# Name prefixes to authoring role. Everything unmatched is body, which is the
# moulded shell the theme is mostly made of.
ROLE_RULES = (
    ("readout", ("tick_", "index_", "needle_", "plate_label")),
    ("gasket", ("gasket", "_knurl_")),
    ("metal", ("screw_", "cover_screw_", "blank", "plug_", "mount_", "access_",
               "bezel", "collar", "cam_", "handle_roller", "switch_hub",
               "switch_bolt", "switch_ear", "gland_", "boss_", "stop_",
               "detent_", "rim_", "front_flange", "rear_flange")),
)


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


def make_materials():
    materials = {}
    for role, colour in PALETTE.items():
        material = bpy.data.materials.new(f"MAT_{THEME}_{role.capitalize()}")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = colour
            bsdf.inputs["Roughness"].default_value = {
                "body": 0.52, "metal": 0.49, "gasket": 0.78, "readout": 0.40,
            }[role]
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = (
                    0.22 if role == "metal" else 0.0)
            if role == "readout" and "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = colour
                bsdf.inputs["Emission Strength"].default_value = 1.6
        materials[role] = material
    return materials


def unwrap(obj):
    """Angle-based projection, packed into the atlas square.

    A greybox has no seams authored into it, so the proposal is a projection
    rather than a hand cut. What the report records is what that projection
    costs: island margin, texel density and how much of the sheet it uses.
    """
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.003,
                             scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def uv_stats(obj):
    """Per-role UV area, world area and the texel density that implies."""
    work = bmesh.new()
    work.from_mesh(obj.data)
    layer = work.loops.layers.uv.active
    slots = [slot.material.name if slot.material else None
             for slot in obj.material_slots]
    rows = {}
    for face in work.faces:
        name = slots[face.material_index] if face.material_index < len(slots) else None
        role = (name or "").rsplit("_", 1)[-1].lower()
        corners = [loop[layer].uv for loop in face.loops]
        uv_area = 0.0
        for index in range(1, len(corners) - 1):
            a, b, c = corners[0], corners[index], corners[index + 1]
            uv_area += abs((b.x - a.x) * (c.y - a.y)
                           - (c.x - a.x) * (b.y - a.y)) / 2.0
        row = rows.setdefault(role, {"faces": 0, "uv_area": 0.0, "world_area": 0.0})
        row["faces"] += 1
        row["uv_area"] += uv_area
        row["world_area"] += face.calc_area()
    work.free()
    for role, row in rows.items():
        row["uv_area"] = round(row["uv_area"], 6)
        row["world_area"] = round(row["world_area"], 6)
        row["atlas_occupancy_pct"] = round(row["uv_area"] * 100.0, 3)
        row["texels_per_metre"] = (
            round(math_sqrt(row["uv_area"] * ATLAS * ATLAS / row["world_area"]), 1)
            if row["world_area"] > 0 else None)
    return rows


def math_sqrt(value):
    return value ** 0.5


def grayscale_stats(path):
    tile = review.load_rgba(path)
    lum = 0.2126 * tile[..., 0] + 0.7152 * tile[..., 1] + 0.0722 * tile[..., 2]
    hist, edges = np.histogram(lum, bins=512, range=(0.0, 1.0))
    background = (edges[hist.argmax()] + edges[hist.argmax() + 1]) / 2.0
    subject = lum[np.abs(lum - background) > 0.02]
    if subject.size < 100:
        return None
    p5, p95 = np.percentile(subject, [5, 95])
    return {"mean": round(float(subject.mean()), 4),
            "p5": round(float(p5), 4), "p95": round(float(p95), 4),
            "contrast": round(float(p95 - p5), 4)}


def luma(colour):
    return round(0.2126 * colour[0] + 0.7152 * colour[1] + 0.0722 * colour[2], 4)


def role_swatches(output_path):
    """Four slabs, one per role, under the look-dev rig.

    A whole-instrument histogram cannot say whether two roles separate; it
    mixes every surface angle together. Four flat samples under one light can,
    and that is the question Codex asked in alignment 274.2.
    """
    p1.clear_scene()
    review.configure_scene()
    # after the clear, not before: clearing frees every datablock
    materials = make_materials()
    order = ["gasket", "metal", "body", "readout"]
    for index, role in enumerate(order):
        slab = p1.chamfer(p1.frustum_box(
            f"swatch_{role}", 0.0, -0.012, (0.058, 0.058), (0.056, 0.056),
            centre=((index - 1.5) * 0.066, 0.0)), 0.0012)
        slab.data.materials.clear()
        slab.data.materials.append(materials[role])
    bpy.context.view_layer.update()
    slabs = {obj.name.replace("swatch_", ""): obj
             for obj in bpy.data.objects if obj.type == "MESH"}
    focus, radius, scale = p1.rig_for(list(slabs.values()))
    # keep the camera so the samples can be placed by projection rather than by
    # slicing the frame into equal bands - the rig adds margin, and the bands
    # put the two outer swatches on the backdrop
    bpy.ops.object.camera_add(location=p1.camera_at(focus, radius, 0.0, 0.0))
    camera = bpy.context.object
    camera.data.lens = 52.0
    review.point_at(camera, focus)
    bpy.context.scene.camera = camera
    p1.shot(focus, radius, (0.0, 0.0), 52.0, scale, output_path)

    from bpy_extras.object_utils import world_to_camera_view
    tile = review.load_rgba(output_path)
    lum = 0.2126 * tile[..., 0] + 0.7152 * tile[..., 1] + 0.0722 * tile[..., 2]
    height, width = lum.shape
    rows = {}
    for role in order:
        obj = slabs[role]
        # the slabs were built with their vertices offset and their origins
        # left at zero, so the object translation is the same point for all
        # four; use the vertex centroid instead
        centroid = sum((obj.matrix_world @ v.co for v in obj.data.vertices),
                       Vector((0.0, 0.0, 0.0))) / len(obj.data.vertices)
        ndc = world_to_camera_view(bpy.context.scene, camera, centroid)
        px = int(ndc.x * width)
        # the image buffer runs bottom-up
        py = int(ndc.y * height)
        half = max(4, int(width * 0.018))
        band = lum[max(0, py - half):py + half, max(0, px - half):px + half]
        rows[role] = round(float(band.mean()), 4) if band.size else None
    gaps = {}
    ordered = sorted(rows.items(), key=lambda kv: kv[1])
    for index in range(len(ordered) - 1):
        gaps[f"{ordered[index][0]}->{ordered[index + 1][0]}"] = round(
            ordered[index + 1][1] - ordered[index][1], 4)
    return {"measured_luma": rows, "order": [name for name, _ in ordered],
            "gaps": gaps, "weakest_gap": min(gaps.values()) if gaps else None}


def build(asset, builder):
    """Run the Phase 1 builder unchanged, tagging each part with its role.

    The materials are created after the scene is cleared, not before: clearing
    loads factory settings and frees every datablock, which invalidated the
    material references the first time round.
    """
    p1.clear_scene()
    review.configure_scene()
    materials = make_materials()
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)

    original_join, original_assign = p1.join, p1.assign
    tagged = {}

    def tagging_join(target, others):
        for obj in [target] + list(others):
            role = role_for(obj.name)
            tagged[obj.name.split(".")[0]] = role
            obj.data.materials.clear()
            obj.data.materials.append(materials[role])
        return original_join(target, others)

    p1.join = tagging_join
    p1.assign = lambda obj, material: None
    try:
        body, pivot, part = builder(materials["body"])
    finally:
        p1.join, p1.assign = original_join, original_assign
    for obj in (body, pivot):
        obj.parent = root
    bpy.context.view_layer.update()
    return root, body, pivot, part, tagged, materials


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    phase1 = json.loads((project_root / PHASE1).read_text())
    tree = project_root / TREE
    review_dir = tree / "lookdev"
    sheet_dir = tree / "contact_sheets"
    for folder in (review_dir, sheet_dir):
        folder.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "Theme4-P2-material",
        "note": ("Material and UV design only. Geometry, pivots, bounds and "
                 "triangle counts are unchanged from Phase 1 and are "
                 "re-measured here to prove it. No FBX is produced."),
        "authoring_roles": list(PALETTE),
        "delivery_normalisation": DELIVERY,
        "atlas_pixels": ATLAS,
        "palette_linear": {role: list(colour) for role, colour in PALETTE.items()},
        "palette_luma": {role: luma(colour) for role, colour in PALETTE.items()},
        "assets": {},
    }
    separations = sorted(payload["palette_luma"].items(), key=lambda kv: kv[1])
    payload["palette_grayscale_order"] = [name for name, _ in separations]
    payload["palette_grayscale_gaps"] = {
        f"{separations[i][0]}->{separations[i + 1][0]}":
            round(separations[i + 1][1] - separations[i][1], 4)
        for i in range(len(separations) - 1)
    }

    swatch_path = review_dir / f"Swatches_{THEME}_P2_roles.png"
    p1.clear_scene()
    payload["role_swatches"] = role_swatches(swatch_path)
    payload["role_swatches"]["image"] = str(swatch_path.relative_to(project_root))

    fronts = {}
    for asset, builder in (("MeterRound", p1.build_meter_round),
                           ("Lever", p1.build_lever),
                           ("Toggle", p1.build_toggle)):
        root, body, pivot, part, tagged, materials = build(asset, builder)
        for obj in (body, part):
            unwrap(obj)

        before = phase1["assets"][asset]
        health = {obj.name: p1.mesh_health(obj) for obj in (body, part)}
        bounds = p1.world_bounds([body, part])
        unchanged = {
            "triangles": {name: row["triangles"] for name, row in health.items()},
            "triangles_match_phase1": (
                {name: row["triangles"] for name, row in health.items()}
                == before["triangles_per_object"]),
            "rest_bounds": bounds,
            "rest_bounds_match_phase1": all(
                abs(bounds["size"][i] - before["bounds_blender"]["size"][i]) < 1e-6
                for i in range(3)),
            "pivot_local": [round(v, 6) for v in pivot.location],
            "pivot_matches_phase1": all(
                abs(pivot.location[i] - before["motion"]["pivot_local"][i]) < 1e-6
                for i in range(3)),
            "comparison_tolerance_m": 1e-6,
        }

        roles_used = sorted({role for role in tagged.values()})
        slots = {obj.name: [slot.material.name for slot in obj.material_slots]
                 for obj in (body, part)}
        delivery_slots = {
            obj.name: sorted({DELIVERY[name.rsplit("_", 1)[-1].lower()]
                              for name in names})
            for obj, names in ((body, slots[body.name]), (part, slots[part.name]))
        }
        images = {}
        focus, radius, scale = p1.rig_for([body, part])
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Lookdev_{asset}_{THEME}_P2_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        fronts[asset] = review_dir / f"Lookdev_{asset}_{THEME}_P2_front.png"

        payload["assets"][asset] = {
            "geometry_unchanged": unchanged,
            "part_roles": dict(sorted(tagged.items())),
            "roles_used": roles_used,
            "authoring_material_slots": slots,
            "delivery_materials_per_object": delivery_slots,
            "delivery_shared_materials": sorted(
                {value for values in delivery_slots.values() for value in values}),
            "uv": {obj.name: uv_stats(obj) for obj in (body, part)},
            "lookdev_images": images,
            "grayscale": grayscale_stats(fronts[asset]),
        }
        print(f"[Theme4P2] {asset}: roles {roles_used}, "
              f"geometry unchanged "
              f"{unchanged['triangles_match_phase1'] and unchanged['rest_bounds_match_phase1']}")

    # One shared 1 K sheet for the theme: each object gets a share of the
    # area proportional to its own surface area, which is what makes texel
    # density uniform. Shelf-packed left to right, top to bottom.
    surfaces = []
    for asset, row in payload["assets"].items():
        for obj, roles in row["uv"].items():
            surfaces.append((asset, obj,
                             sum(r["world_area"] for r in roles.values())))
    total_area = sum(entry[2] for entry in surfaces)
    density = math_sqrt(ATLAS * ATLAS * ATLAS_BUDGET / total_area)
    cursor_x = cursor_y = shelf = 0.0
    layout = {}
    for asset, obj, area in sorted(surfaces, key=lambda e: -e[2]):
        side = math_sqrt(area * ATLAS_BUDGET / total_area)
        if cursor_x + side > 1.0:
            cursor_x, cursor_y, shelf = 0.0, cursor_y + shelf, 0.0
        layout[f"{asset}/{obj}"] = {
            "rect_uv": [round(cursor_x, 5), round(cursor_y, 5),
                        round(side, 5), round(side, 5)],
            "world_area_m2": round(area, 6),
            "sheet_share_pct": round(side * side * 100.0, 3),
        }
        cursor_x += side
        shelf = max(shelf, side)
    payload["atlas_layout"] = {
        "sheet_pixels": ATLAS,
        "island_budget_pct": ATLAS_BUDGET * 100.0,
        "total_surface_area_m2": round(total_area, 6),
        "uniform_texel_density_per_metre": round(density, 1),
        "uniform_texels_per_mm": round(density / 1000.0, 3),
        "area_fits_budget": True,
        "naive_shelf_rows_used": round(cursor_y + shelf, 4),
        "naive_shelf_pack_fits": (cursor_y + shelf) <= 1.0,
        "indicative_placements": layout,
        "note": ("The area fits the island budget exactly; the shelf pack "
                 "above is only indicative and overflows because the dominant "
                 "object exceeds one shelf row. A real packer is delivery "
                 "work. The Blend still carries a per-object 0-1 unwrap - "
                 "packing it would change the FBX Codex has validated."),
    }
    role_area = {}
    for row in payload["assets"].values():
        for roles in row["uv"].values():
            for role, stats in roles.items():
                role_area[role] = role_area.get(role, 0.0) + stats["world_area"]
    payload["atlas_layout"]["role_share_pct"] = {
        role: round(area / total_area * 100.0, 2)
        for role, area in sorted(role_area.items())
    }
    # A uniform density spends the sheet on the body, which carries three
    # quarters of the surface and needs the least resolution. The readout is
    # where numerals and units land, and at the uniform figure they would be
    # unreadable, so it gets a disproportionate share.
    readout_area = role_area.get("readout", 0.0)
    boosted = 0.08
    payload["atlas_layout"]["readout_allocation"] = {
        "area_share_of_surface_pct": round(readout_area / total_area * 100.0, 2),
        "uniform_texels_per_mm": round(density / 1000.0, 3),
        "proposed_sheet_share_pct": round(boosted * 100.0, 1),
        "proposed_texels_per_mm": round(
            math_sqrt(boosted * ATLAS * ATLAS / readout_area) / 1000.0, 3)
        if readout_area > 0 else None,
        "reason": ("numerals, units and fine labels sit on the readout role. "
                   "At the uniform density they are below one texel per "
                   "millimetre and cannot be read; the scale ticks are already "
                   "geometry for the same reason (alignment 265.1)."),
    }
    payload["atlas_layout"]["role_triangles"] = {}
    for row in payload["assets"].values():
        for roles in row["uv"].values():
            for role, stats in roles.items():
                payload["atlas_layout"]["role_triangles"][role] = (
                    payload["atlas_layout"]["role_triangles"].get(role, 0)
                    + stats["faces"])

    # Grayscale sheet: the roles have to separate on value, not only on hue.
    rows = [(asset, [(label, project_root / row["lookdev_images"][label])
                     for label in ("front", "oblique_left", "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    sheet = sheet_dir / f"ContactSheet_Theme4_{THEME}_P2_material_grayscale.png"
    p1.comparison_sheet(rows, sheet)
    payload["grayscale_contact_sheet"] = str(sheet.relative_to(project_root))

    payload["geometry_unchanged_all"] = all(
        row["geometry_unchanged"]["triangles_match_phase1"]
        and row["geometry_unchanged"]["rest_bounds_match_phase1"]
        and row["geometry_unchanged"]["pivot_matches_phase1"]
        for row in payload["assets"].values())
    payload["delivery_shared_materials_max"] = max(
        len(row["delivery_shared_materials"]) for row in payload["assets"].values())
    payload["status"] = ("p2_material_proposal"
                         if payload["geometry_unchanged_all"] else "geometry_drifted")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4P2] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
