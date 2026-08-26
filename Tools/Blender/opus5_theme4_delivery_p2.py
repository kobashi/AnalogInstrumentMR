"""Theme 4 P2 pilot delivery: role UVs into atlas quadrants, two materials.

Alignment 281. The P1 FBX carry a single greybox material, so the four roles
designed in alignment 276 never reach Unity. This pass keeps the geometry
exactly as Codex validated it and changes only what the delivery contract
covers: UVs, material indices, material slots and the textures behind them.

Quadrant layout and channel packing are the ones
Tools/Textures/build_v6_material_atlases.py already uses - body top-left,
metal top-right, gasket bottom-left, readout bottom-right, metallic in R and
smoothness in A - so a Unity importer set up for the existing three themes
reads these the same way.

The maps are flat per quadrant. A greybox has no surface detail to bake, and
inventing some here would misrepresent what the pilot actually is.

Geometry transport is verified against the P1 Blend itself: vertex positions,
normals and triangle indices are read from it before the P2 build and compared
afterwards, so "unchanged" is a measurement rather than a claim.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_delivery_p2.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_material_p2 as p2
import opus5_toggle_fbx_handoff as toggle

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics"
DELIVERY = "delivery_p2"
# Inside the delivery root, as alignment 281.1 lists it. It had been
# written a level up, so the directory Codex audits did not contain the
# report that describes it.
OUTPUT = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
          "delivery_p2/theme4_delivery_p2.json")
PHASE1 = "ArtSource/Blender/BrushUp/Opus5/theme4_machined_ergonomics_p1.json"
ATLAS = 1024

# Same quadrant assignment as the V6 atlas builder. Column/row are in image
# space with row 0 at the top, which is why the v ranges are mirrored.
QUADRANTS = {"body": (0, 0), "metal": (1, 0), "gasket": (0, 1), "readout": (1, 1)}
# A margin inside each quadrant so bilinear sampling cannot pull a neighbour in.
QUADRANT_INSET = 0.006

ATLAS_MATERIAL = f"MAT_{THEME}_P2_Atlas"
EMISSIVE_MATERIAL = f"MAT_{THEME}_P2_Emissive"
OPAQUE_ROLES = ("body", "metal", "gasket")

# metallic and smoothness per role, from the finish approved in alignment 277.2
SURFACE = {
    "body": {"metallic": 0.00, "smoothness": 0.48},
    "metal": {"metallic": 0.22, "smoothness": 0.51},
    "gasket": {"metallic": 0.00, "smoothness": 0.22},
    "readout": {"metallic": 0.00, "smoothness": 0.60},
}
EMISSION_STRENGTH = 1.6


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def quadrant_uv_range(role):
    column, row = QUADRANTS[role]
    return {
        "u": [round(column * 0.5, 4), round(column * 0.5 + 0.5, 4)],
        "v": [round(1.0 - (row + 1) * 0.5, 4), round(1.0 - row * 0.5, 4)],
    }


def srgb(value):
    value = float(np.clip(value, 0.0, 1.0))
    return (12.92 * value if value <= 0.0031308
            else 1.055 * value ** (1.0 / 2.4) - 0.055)


def read_phase1_meshes(project_root, report):
    """Vertex positions, normals and triangle indices from the P1 Blend."""
    stored = {}
    for asset, row in report["assets"].items():
        bpy.ops.wm.open_mainfile(filepath=str(project_root / row["blend"]),
                                 load_ui=False)
        stored[asset] = {}
        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue
            mesh = obj.data
            mesh.calc_loop_triangles()
            stored[asset][obj.name] = {
                "positions": [tuple(round(c, 7) for c in v.co)
                              for v in mesh.vertices],
                "normals": [tuple(round(c, 5) for c in v.normal)
                            for v in mesh.vertices],
                "triangles": [tuple(t.vertices) for t in mesh.loop_triangles],
            }
    return stored


def compare_meshes(before, after):
    rows = {}
    for name, prior in before.items():
        now = after.get(name)
        if now is None:
            rows[name] = {"present": False}
            continue
        rows[name] = {
            "present": True,
            "vertex_count": len(now["positions"]),
            "positions_identical": now["positions"] == prior["positions"],
            "normals_identical": now["normals"] == prior["normals"],
            "triangles_identical": now["triangles"] == prior["triangles"],
        }
    return rows


def snapshot(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    return {
        "positions": [tuple(round(c, 7) for c in v.co) for v in mesh.vertices],
        "normals": [tuple(round(c, 5) for c in v.normal) for v in mesh.vertices],
        "triangles": [tuple(t.vertices) for t in mesh.loop_triangles],
    }


def load_map(path, colorspace):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = colorspace
    return image


def delivery_materials(textures):
    """Two materials that actually sample the atlas.

    Wiring the maps matters for more than looks: with a flat colour per
    material the review images cannot show whether the UVs landed in the right
    quadrant, which is the one thing this delivery has to demonstrate.
    """
    base = load_map(textures["BaseColor"], "sRGB")
    packed = load_map(textures["MetallicSmoothness"], "Non-Color")
    glow = load_map(textures["Emission"], "sRGB")

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
        if emissive:
            emit = tree.nodes.new("ShaderNodeTexImage")
            emit.image = glow
            if "Emission Color" in bsdf.inputs:
                tree.links.new(emit.outputs["Color"],
                               bsdf.inputs["Emission Color"])
                bsdf.inputs["Emission Strength"].default_value = 1.0

    atlas = bpy.data.materials.new(ATLAS_MATERIAL)
    wire(atlas, False)
    emissive = bpy.data.materials.new(EMISSIVE_MATERIAL)
    wire(emissive, True)
    return atlas, emissive


def pack_into_quadrants(obj, role_of_slot, atlas, emissive):
    """Scale each face's UVs into its role quadrant and collapse to 2 slots."""
    work = bmesh.new()
    work.from_mesh(obj.data)
    layer = work.loops.layers.uv.active
    counts = {}
    faces = {}
    for face in work.faces:
        role = role_of_slot[face.material_index]
        counts[role] = counts.get(role, 0) + 1
        column, row = QUADRANTS[role]
        u0 = column * 0.5 + QUADRANT_INSET
        v0 = (1.0 - (row + 1) * 0.5) + QUADRANT_INSET
        span = 0.5 - QUADRANT_INSET * 2.0
        for loop in face.loops:
            uv = loop[layer].uv
            uv.x = u0 + min(max(uv.x, 0.0), 1.0) * span
            uv.y = v0 + min(max(uv.y, 0.0), 1.0) * span
        faces[face.index] = 0 if role in OPAQUE_ROLES else 1
    work.to_mesh(obj.data)
    work.free()

    obj.data.materials.clear()
    obj.data.materials.append(atlas)
    obj.data.materials.append(emissive)
    for polygon in obj.data.polygons:
        polygon.material_index = faces[polygon.index]
    # Drop any slot nothing draws into and renumber, so the slot count and the
    # submesh count agree. The needle is entirely readout and was keeping an
    # empty opaque slot, which Unity would carry as a zero-triangle submesh.
    used = sorted({polygon.material_index for polygon in obj.data.polygons})
    if len(used) < len(obj.data.materials):
        remap = {old: new for new, old in enumerate(used)}
        keep = [obj.data.materials[index] for index in used]
        # capture before clearing: clearing the slots resets every polygon's
        # material_index, so reading it afterwards gives zeros
        indices = [remap[polygon.material_index] for polygon in obj.data.polygons]
        obj.data.materials.clear()
        for material in keep:
            obj.data.materials.append(material)
        for polygon, index in zip(obj.data.polygons, indices):
            polygon.material_index = index
        used = sorted(set(indices))
    return counts, used


def write_png(path, array, alpha=None):
    """Write an exact 8-bit PNG through Blender's image API.

    Pillow is not available inside Blender - the existing atlas builder runs
    under the system interpreter - so the maps are written here instead. The
    image is tagged Non-Color and the values are already encoded, so what is
    stored is exactly what this function was handed. Blender's buffer runs
    bottom-up, hence the flip.
    """
    height, width = array.shape[:2]
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[..., :3] = array[..., :3]
    if alpha is not None:
        rgba[..., 3] = alpha
    rgba = np.flipud(rgba)
    image = bpy.data.images.new(path.stem, width=width, height=height,
                                alpha=True, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    image.pixels = rgba.reshape(-1).tolist()
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    return path


def build_textures(output_dir):
    half = ATLAS // 2
    base = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    normal = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    metallic = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    smoothness = np.zeros((ATLAS, ATLAS), dtype=np.float32)
    emission = np.zeros((ATLAS, ATLAS, 3), dtype=np.float32)
    for role, (column, row) in QUADRANTS.items():
        x0, y0 = column * half, row * half
        x1, y1 = x0 + half, y0 + half
        colour = p2.PALETTE[role]
        base[y0:y1, x0:x1] = [srgb(colour[index]) for index in range(3)]
        normal[y0:y1, x0:x1] = [0.5, 0.5, 1.0]
        metallic[y0:y1, x0:x1, 0] = SURFACE[role]["metallic"]
        smoothness[y0:y1, x0:x1] = SURFACE[role]["smoothness"]
        if role == "readout":
            emission[y0:y1, x0:x1] = [
                srgb(min(colour[index] * EMISSION_STRENGTH, 1.0))
                for index in range(3)]
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"T_{THEME}_P2_Atlas"
    return {
        "BaseColor": write_png(output_dir / f"{prefix}_BaseColor.png", base),
        "Normal": write_png(output_dir / f"{prefix}_Normal.png", normal),
        "MetallicSmoothness": write_png(
            output_dir / f"{prefix}_MetallicSmoothness.png", metallic,
            alpha=smoothness),
        "Emission": write_png(output_dir / f"{prefix}_Emission.png", emission),
    }


def export_fbx(root, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [root] + list(root.children_recursive):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    settings = dict(toggle.EXPORT_SETTINGS)
    settings["use_triangles"] = False
    settings["mesh_smooth_type"] = "EDGE"
    bpy.ops.export_scene.fbx(filepath=str(target), **settings)
    if not target.is_file():
        raise SystemExit(f"[Theme4DeliveryP2] export wrote nothing: {target}")
    return target


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    phase1 = json.loads((project_root / PHASE1).read_text())
    tree = project_root / TREE / DELIVERY
    review_dir = tree / "review"
    for folder in (tree, review_dir):
        folder.mkdir(parents=True, exist_ok=True)

    before = read_phase1_meshes(project_root, phase1)
    textures = build_textures(tree)

    payload = {
        "phase": "Theme4-P2-delivery",
        "note": ("Pilot delivery: role UVs packed into the V6 atlas quadrants "
                 "and two shared materials. Geometry is transported unchanged "
                 "from the P1 Blends and verified vertex by vertex. Not a "
                 "production atlas pack - alignment 281.2."),
        "atlas_pixels": ATLAS,
        "quadrants": {role: {"column_row": list(cell),
                             "uv_range": quadrant_uv_range(role)}
                      for role, cell in QUADRANTS.items()},
        "quadrant_inset_uv": QUADRANT_INSET,
        "channel_convention": ("MetallicSmoothness: metallic in R, smoothness "
                               "in A; Emission carries the readout quadrant "
                               "only - same as build_v6_material_atlases"),
        "maps_are_flat_per_quadrant": True,
        "surface": SURFACE,
        "delivery_materials": {"opaque": ATLAS_MATERIAL,
                               "emissive": EMISSIVE_MATERIAL},
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "assets": {},
    }

    fronts = {}
    for asset, builder in (("MeterRound", p1.build_meter_round),
                           ("Lever", p1.build_lever),
                           ("Toggle", p1.build_toggle)):
        root, body, pivot, part, tagged, materials = p2.build(asset, builder)
        for obj in (body, part):
            p2.unwrap(obj)
        atlas, emissive = delivery_materials(textures)
        rows = {}
        for obj in (body, part):
            role_of_slot = [slot.material.name.rsplit("_", 1)[-1].lower()
                            for slot in obj.material_slots]
            counts, used = pack_into_quadrants(obj, role_of_slot, atlas, emissive)
            rows[obj.name] = {
                "role_face_counts": counts,
                "material_slots": [slot.material.name
                                   for slot in obj.material_slots],
                "submeshes": len(used),
            }
        bpy.context.view_layer.update()

        after = {obj.name: snapshot(obj) for obj in (body, part)}
        transport = compare_meshes(before[asset], after)
        source = phase1["assets"][asset]

        fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_P2.fbx"
        export_fbx(root, fbx)

        review.configure_scene()
        images = {}
        focus, radius, scale = p1.rig_for([body, part])
        for label, view in p1.VIEWS.items():
            path = review_dir / f"Delivery_{asset}_{THEME}_P2_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        fronts[asset] = review_dir / f"Delivery_{asset}_{THEME}_P2_front.png"

        payload["assets"][asset] = {
            "source_p1_fbx": source["fbx"],
            "source_p1_fbx_sha256": source["fbx_sha256"],
            "p2_fbx": str(fbx.relative_to(project_root)),
            "p2_fbx_sha256": m1.digest(fbx),
            "p2_fbx_bytes": fbx.stat().st_size,
            "objects": rows,
            "renderers": 2,
            "max_material_slots_per_object": max(
                len(row["material_slots"]) for row in rows.values()),
            "geometry_transport": transport,
            "geometry_transport_identical": all(
                row.get("positions_identical") and row.get("normals_identical")
                and row.get("triangles_identical") for row in transport.values()),
            "triangles_phase1": source["triangles_per_object"],
            "pivot_local": source["motion"]["pivot_local"],
            "images": images,
        }
        print(f"[Theme4DeliveryP2] {asset}: slots "
              f"{payload['assets'][asset]['max_material_slots_per_object']}, "
              f"transport identical "
              f"{payload['assets'][asset]['geometry_transport_identical']}")

    sheets = {}
    rows = [(asset, [(label, project_root / row["images"][label])
                     for label in ("front", "oblique_left", "oblique_right", "side")])
            for asset, row in payload["assets"].items()]
    grey = tree / f"ContactSheet_Theme4_{THEME}_P2_delivery_grayscale.png"
    p1.comparison_sheet(rows, grey)
    sheets["grayscale"] = str(grey.relative_to(project_root))
    colour = tree / f"ContactSheet_Theme4_{THEME}_P2_delivery_colour.png"
    colour_rows = [review.load_rgba(project_root / row["images"][label])
                   for _, row in payload["assets"].items()
                   for label in ("front", "oblique_left", "oblique_right", "side")]
    height, width = colour_rows[0].shape[:2]
    gap = 16
    canvas = np.zeros((3 * height + 2 * gap, 4 * width + 3 * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(colour_rows):
        row_index, column = divmod(index, 4)
        top = (2 - row_index) * (height + gap)
        canvas[top:top + height, column * (width + gap):
               column * (width + gap) + width] = tile
    review.save_rgba(canvas, colour)
    sheets["colour"] = str(colour.relative_to(project_root))
    payload["contact_sheets"] = {name: {"path": path,
                                        "sha256": m1.digest(project_root / path)}
                                 for name, path in sheets.items()}

    payload["shared_material_identities"] = sorted(
        {name for row in payload["assets"].values()
         for obj in row["objects"].values() for name in obj["material_slots"]})
    payload["all_transport_identical"] = all(
        row["geometry_transport_identical"] for row in payload["assets"].values())
    payload["max_material_slots_any_object"] = max(
        row["max_material_slots_per_object"] for row in payload["assets"].values())
    payload["status"] = ("p2_delivery_ready"
                         if payload["all_transport_identical"]
                         and payload["max_material_slots_any_object"] <= 2
                         and len(payload["shared_material_identities"]) <= 2
                         else "delivery_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4DeliveryP2] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
