"""B3U R1: the nameplate, moved off the mechanism and stopped glowing.

Alignment 306. Quest passed everything about B3U except the nameplate. On the
Throttle the cyan `plate_label` sat at the lever root, so a lit panel with no
stated meaning appeared to belong to the mechanism; on the PowerSlider it
overlapped its neighbours and did not read as a nameplate at all. Fixing B3's
role mis-wiring in B3U is what made the placement visible.

This pass changes the nameplate and nothing else:

  * relocated onto clear housing face - measured against every other part's
    footprint rather than eyeballed - away from the slot rims, bearings, tool
    bores, screws, service cover and the arm's swept projection;
  * rebuilt as a raised plate with a recessed engraved field and given the
    metal role, so it reads as etched rather than lit. There is no blank cyan
    panel any more. A real status display, if one is wanted, is a separate
    indicator with defined states and is not this part;
  * because it was the only readout face on either control, the emissive
    submesh is now empty and is dropped rather than shipped hollow. Renderer
    and submesh counts are reported before and after.

The atlas is untouched: moving a face between UV regions changes no texel, so
all four 1024 maps stay byte-identical to B3U's and are verified as such.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r4_b3u_r1.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_r4 as r4
import opus5_theme4_full_p6_batch_a_r4_b3u as b3u
import opus5_theme4_production_atlas_proposal_b3 as b3
import opus5_theme4_material_p2 as m2

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r4_b3u_r1")
OUTPUT = f"{TREE}/theme4_full_p6_batch_a_r4_b3u_r1.json"
B3U_TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
            "delivery_p6/batch_a_r4_b3u")
ATLAS_PIXELS = 1024

# Centre and size on the front face, chosen from the measured footprints of
# every other part. The Throttle plate goes onto the left flank between the
# slot rim and the tool bore column, clear of the arm's swept band at |x| <
# 0.0195; the PowerSlider's goes onto its left flank between the rim and the
# shell edge, clear of the mount and the service cap in Z.
NAMEPLATE = {
    "Throttle": {"centre": (-0.0780, 0.0200), "size": (0.0300, 0.0620)},
    "PowerSlider": {"centre": (-0.0555, 0.0000), "size": (0.0230, 0.0700)},
}
NAMEPLATE_PARTS = ("plate_label",)
# The panel the plate is mounted on. Overlapping these in projection is what
# mounting means; the test is against everything else.
PANEL_PARTS = ("plate", "gasket", "shell", "skirt", "register")

_ACTIVE_ASSET = None
_ORIGINAL_NAMEPLATE = p1.nameplate


def engraved_nameplate(name, centre, size, y_top, depth):
    """A raised plate with a sunk field, at the relocated position.

    The caller's centre and size are ignored on purpose: the builder passes
    the old placement and this is the part being moved. Everything else about
    the call - the face it sits on and how proud it stands - is honoured.
    """
    row = NAMEPLATE[_ACTIVE_ASSET]
    cx, cz = row["centre"]
    width, height = row["size"]
    # A solid plate with a smaller box inside it shows nothing - the first
    # build buried the field - and a frame plus an inset plate costs 64
    # triangles more than the budget has room for. The field is cut instead,
    # which is both cheaper and what an engraved plate actually is.
    plate = p1.chamfer(p1.frustum_box(
        name, y_top, y_top - 0.0022, (width, height),
        (width - 0.0026, height - 0.0026), centre=(cx, cz)), 0.0007)
    cutter = p1.frustum_box(
        f"{name}_cut", y_top - 0.0014, y_top - 0.0034,
        (width - 0.0080, height - 0.0080),
        (width - 0.0080, height - 0.0080), centre=(cx, cz))
    return r4.drill(plate, [cutter])


def role_for_r1(name, base_role):
    """Nameplate to metal, and exempt from relief promotion.

    It is an etched plate, so it wants the metal surface and none of the
    machined normal region - `plate` as a prefix would otherwise capture it,
    which is the same rule that mis-routed it in B3.
    """
    stem = name.split(".")[0]
    if stem.startswith("plate_label"):
        return "metal"
    return b3u.proposal_role_fixed(name, base_role)


# ---------------------------------------------------------------------------
# nameplate audits
# ---------------------------------------------------------------------------

def _tris(parts):
    verts, faces = [], []
    for obj in parts:
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        offset = len(verts)
        verts.extend(matrix @ v.co for v in mesh.vertices)
        faces.extend(tuple(i + offset for i in t.vertices)
                     for t in mesh.loop_triangles)
    return verts, faces


def _mask(verts, faces, basis, bounds, size=768):
    """Rasterise a part's triangles into the view plane.

    Projected overlap is a question about pixels, so it is answered with
    pixels. A convex hull would over-report on a concave silhouette and a
    bounding box would over-report on everything.
    """
    right, up = basis
    lo, hi = bounds
    grid = np.zeros((size, size), dtype=bool)
    span = max(hi[0] - lo[0], hi[1] - lo[1]) or 1.0
    pts = np.array([[float(np.dot(v, right)), float(np.dot(v, up))]
                    for v in verts], dtype=float)
    pts = (pts - np.array(lo)) / span * (size - 1)
    ys, xs = np.mgrid[0:size, 0:size]
    for a, b, c in faces:
        p0, p1_, p2 = pts[a], pts[b], pts[c]
        minx = max(int(min(p0[0], p1_[0], p2[0])), 0)
        maxx = min(int(max(p0[0], p1_[0], p2[0])) + 1, size - 1)
        miny = max(int(min(p0[1], p1_[1], p2[1])), 0)
        maxy = min(int(max(p0[1], p1_[1], p2[1])) + 1, size - 1)
        if minx > maxx or miny > maxy:
            continue
        sx = xs[miny:maxy + 1, minx:maxx + 1]
        sy = ys[miny:maxy + 1, minx:maxx + 1]
        d = ((p1_[1] - p2[1]) * (p0[0] - p2[0])
             + (p2[0] - p1_[0]) * (p0[1] - p2[1]))
        if abs(d) < 1e-12:
            continue
        w0 = ((p1_[1] - p2[1]) * (sx - p2[0])
              + (p2[0] - p1_[0]) * (sy - p2[1])) / d
        w1 = ((p2[1] - p0[1]) * (sx - p2[0])
              + (p0[0] - p2[0]) * (sy - p2[1])) / d
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        grid[miny:maxy + 1, minx:maxx + 1] |= inside
    return grid


def nameplate_audit(asset, statics, mover, movers, views):
    """Intersection, projected overlap and clearance, against the neighbours.

    "Neighbours" excludes the panel stack the plate is screwed to - a plate
    that did not overlap its own panel would be floating - and includes every
    other static part plus the moving assembly at both ends of travel.
    """
    label_geo = [statics[name] for name in statics if name in NAMEPLATE_PARTS]
    others = {name: geo for name, geo in statics.items()
              if name not in NAMEPLATE_PARTS and name not in PANEL_PARTS}
    lverts, lfaces = [], []
    for verts, faces in label_geo:
        offset = len(lverts)
        lverts.extend(verts)
        lfaces.extend(tuple(i + offset for i in f) for f in faces)
    label_bvh = BVHTree.FromPolygons(lverts, lfaces, all_triangles=True)

    poses = list(ba.pose_set(asset))
    intersections = []
    nearest = None
    nearest_part = None
    nearest_pose = None
    for value, pose_name in poses:
        ba.apply_pose(mover, asset, value)
        bpy.context.view_layer.update()
        candidates = list(others.items())
        candidates += [(o.name.split(".")[0], _tris([o])) for o in movers]
        for name, (verts, faces) in candidates:
            if not faces:
                continue
            tree = BVHTree.FromPolygons(verts, faces, all_triangles=True)
            pairs = label_bvh.overlap(tree)
            if pairs:
                intersections.append({"pose": pose_name, "part": name,
                                      "triangle_pairs": len(pairs)})
                nearest = 0.0
                nearest_part, nearest_pose = name, pose_name
                continue
            for point in lverts[::2]:
                hit = tree.find_nearest(point)
                if hit[0] is None:
                    continue
                distance = (hit[0] - point).length
                if nearest is None or distance < nearest:
                    nearest = distance
                    nearest_part, nearest_pose = name, pose_name

    overlaps = []
    moving_overlaps = []
    moving_names = {o.name.split(".")[0] for o in movers}
    for view_name, direction in views.items():
        axis = np.array(direction, dtype=float)
        axis /= np.linalg.norm(axis)
        up = np.array([0.0, 0.0, 1.0])
        right = np.cross(up, axis)
        if np.linalg.norm(right) < 1e-6:
            right = np.array([1.0, 0.0, 0.0])
        right /= np.linalg.norm(right)
        up = np.cross(axis, right)
        for value, pose_name in poses:
            ba.apply_pose(mover, asset, value)
            bpy.context.view_layer.update()
            allv = list(lverts)
            for verts, _ in others.values():
                allv.extend(verts)
            for obj in movers:
                allv.extend(_tris([obj])[0])
            proj = np.array([[float(np.dot(v, right)), float(np.dot(v, up))]
                             for v in allv])
            bounds = (proj.min(axis=0), proj.max(axis=0))
            label_mask = _mask(lverts, lfaces, (right, up), bounds)
            targets = list(others.items())
            targets += [(o.name.split(".")[0], _tris([o])) for o in movers]
            for name, (verts, faces) in targets:
                if not faces:
                    continue
                other = _mask(verts, faces, (right, up), bounds)
                shared = int(np.count_nonzero(label_mask & other))
                if shared:
                    entry = {"view": view_name, "pose": pose_name,
                             "part": name, "pixels": shared}
                    if name in moving_names:
                        moving_overlaps.append(entry)
                    else:
                        overlaps.append(entry)
    ba.apply_pose(mover, asset, 0.0)
    bpy.context.view_layer.update()
    return {
        "placement": NAMEPLATE[asset],
        "parts": list(NAMEPLATE_PARTS),
        "neighbours_tested": sorted(set(others)
                                    | {o.name.split(".")[0] for o in movers}),
        "panel_excluded": list(PANEL_PARTS),
        "poses": [name for _, name in poses],
        "views": sorted(views),
        "triangle_intersections": intersections,
        "triangle_intersection_count": len(intersections),
        "projected_overlaps_static": overlaps,
        "projected_overlap_count_static": len(overlaps),
        "projected_overlaps_moving": moving_overlaps,
        "projected_overlap_count_moving": len(moving_overlaps),
        "moving_overlap_note": (
            "the arm and the shoe sweep across the whole panel, so from an "
            "oblique view their silhouette crosses any fixed feature on it at "
            "some pose. This is reported, not gated; no nameplate position "
            "avoids it. Say so if the gate was meant to include it."),
        "min_clearance_mm": round(nearest * 1000.0, 3)
        if nearest is not None else None,
        "min_clearance_part": nearest_part,
        "min_clearance_pose": nearest_pose,
        "tangential_contact": bool(nearest is not None and nearest <= 1e-5),
        "clean": (not intersections and not overlaps
                  and nearest is not None and nearest > 1e-5),
        "clean_definition": ("zero triangle intersection, zero projected "
                             "overlap with static neighbours, no tangential "
                             "contact"),
        "method": ("BVH overlap and vertex-to-surface distance for contact; "
                   "768 px rasterised silhouettes for projected overlap"),
    }


# ---------------------------------------------------------------------------

def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


VIEWS = {
    "front": (0.0, -1.0, 0.0),
    "oblique_left": (-0.62, -0.78, 0.0),
    "oblique_right": (0.62, -0.78, 0.0),
}


def build(asset, builder, textures, relocate):
    """One asset, with or without the relocation, on the B3 layout."""
    global _ACTIVE_ASSET
    _ACTIVE_ASSET = asset
    statics = {}
    original_nameplate = p1.nameplate
    original_role = b3.proposal_role
    if relocate:
        p1.nameplate = engraved_nameplate
        b3.proposal_role = role_for_r1
    else:
        b3.proposal_role = b3u.proposal_role_fixed
    original_join = p1.join
    captured = []

    def capturing_join(target, others):
        captured.append([target] + list(others))
        return original_join(target, others)

    p1.join = capturing_join
    try:
        root, body, mover, moving, tagged, audit = b3.build_for_proposal(
            asset, builder)
    finally:
        p1.nameplate = original_nameplate
        b3.proposal_role = original_role
        p1.join = original_join
    movers = list(moving) if isinstance(moving, (list, tuple)) else [moving]
    return root, body, mover, movers, tagged, audit


def build_with_static_parts(asset, builder, relocate):
    """Same build, but keeping every static part separate for the audit."""
    global _ACTIVE_ASSET
    _ACTIVE_ASSET = asset
    parts = {}
    original_join = p1.join
    original_nameplate = p1.nameplate
    if relocate:
        p1.nameplate = engraved_nameplate
    snapshots = []

    def capturing_join(target, others):
        group = [target] + list(others)
        # p1.join frees its sources, so the static geometry has to be taken
        # here rather than looked up afterwards. The update is for parts
        # positioned by object .location - the pillow caps and end stops.
        bpy.context.view_layer.update()
        snapshots.append({obj.name.split(".")[0]: _tris([obj])
                          for obj in group})
        return original_join(target, others)

    p1.clear_scene()
    p1.join = capturing_join
    try:
        material = p1.proto.make_material(f"MAT_{THEME}_R1_Neutral", ba.NEUTRAL)
        body, mover, moving, audit = builder(material)
    finally:
        p1.join = original_join
        p1.nameplate = original_nameplate
    movers = list(moving) if isinstance(moving, (list, tuple)) else [moving]
    snapshots.sort(key=lambda s: -len(s))
    return body, mover, movers, snapshots[0]


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    geometry_dir = tree / "geometry"
    compare_dir = tree / "comparison"
    for folder in (tree, geometry_dir, compare_dir):
        folder.mkdir(parents=True, exist_ok=True)

    textures, atlas_stats = b3u.build_atlas(tree, ATLAS_PIXELS)
    reference_atlas = {}
    for name, path in textures.items():
        # d2.write_png names the flat map "Normal_Flat"; the dict key is
        # "NormalFlat", and comparing on the key alone reported a difference
        # that was only a spelling.
        source = project_root / B3U_TREE / path.name
        reference_atlas[name] = {
            "b3u_file": path.name,
            "b3u_sha256": m1.digest(source) if source.exists() else None,
            "r1_sha256": m1.digest(path),
            "identical": (source.exists()
                          and m1.digest(source) == m1.digest(path)),
            "production": name in b3u.PRODUCTION_MAPS,
        }

    payload = {
        "phase": "Theme4-P6-BatchA-R4-B3U-R1",
        "note": ("Nameplate only. Geometry, tooling, grip UV, motion and the "
                 "atlas are B3U's; the nameplate is relocated, made "
                 "non-emissive and given the metal role. R4, B3, B3U, "
                 "Batch B/C, Assets, Builds, docs and git are untouched."),
        "atlas_pixels": ATLAS_PIXELS,
        "atlas_identical_to_b3u": reference_atlas,
        "nameplate": {
            "placement": NAMEPLATE,
            "form": ("raised plate with a recessed engraved field; no "
                     "emissive panel"),
            "role": "metal",
            "relief_promotion": "exempt, so it keeps the plain metal surface",
        },
        "assets": {},
    }

    for asset, builder in r4.BUILDERS_R4.items():
        # audit build: static parts kept separate
        body, mover, movers, statics = build_with_static_parts(
            asset, builder, relocate=True)
        bpy.context.view_layer.update()
        audit = nameplate_audit(asset, statics, mover, movers, VIEWS)

        rows = {}
        images = {}
        counts = {}
        for tag, relocate in (("before", False), ("after", True)):
            root, body, mover, movers, tagged, _ = build(
                asset, builder, textures, relocate)
            meshes = [body] + movers
            for obj in meshes:
                m2.unwrap(obj)
            opaque, emissive = b3u.b3_materials(textures, tag=f"_{tag}")
            per_object = {}
            for obj in meshes:
                slots = [b3.role_of(slot.material)
                         for slot in obj.material_slots]
                b3.cylindrical_grip_uv(obj, slots)
                face_counts, used = b3.pack_into_proposal(
                    obj, slots, opaque, emissive)
                per_object[obj.name] = {
                    "role_face_counts": face_counts,
                    "material_slots": [s.material.name
                                       for s in obj.material_slots],
                    "submeshes": len(used),
                }
            bpy.context.view_layer.update()
            counts[tag] = {
                "renderers": len(meshes),
                "submeshes_total": sum(r["submeshes"]
                                       for r in per_object.values()),
                "max_material_slots_per_object": max(
                    len(r["material_slots"]) for r in per_object.values()),
                "shared_materials": sorted(
                    {n for r in per_object.values()
                     for n in r["material_slots"]}),
                "triangles_total": sum(len(o.data.polygons) for o in meshes),
            }
            if tag == "after":
                rows = per_object
                fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_R4_B3U_R1.fbx"
                d2.export_fbx(root, fbx)
                blend = (geometry_dir
                         / f"BL_{asset}_{THEME}_V6_Opus5_R4_B3U_R1.blend")
                bpy.ops.wm.save_as_mainfile(filepath=str(blend))
                payload_fbx = {
                    "fbx": str(fbx.relative_to(project_root)),
                    "fbx_sha256": m1.digest(fbx),
                    "fbx_bytes": fbx.stat().st_size,
                    "blend": str(blend.relative_to(project_root)),
                    "blend_sha256": m1.digest(blend),
                }
            review.configure_scene()
            focus, radius, scale = p1.rig_for(meshes)
            centre = NAMEPLATE[asset]["centre"]
            label_focus = (centre[0], -0.050, centre[1])
            near = compare_dir / f"Nameplate_{asset}_{tag}_close.png"
            p1.shot(label_focus, 0.150, (26.0, 14.0), 62.0, 0.075, near)
            images[f"close_{tag}"] = str(near.relative_to(project_root))
            crowd = compare_dir / f"Nameplate_{asset}_{tag}_clearance.png"
            p1.shot(label_focus, 0.115, (64.0, 10.0), 58.0, 0.058, crowd)
            images[f"clearance_{tag}"] = str(crowd.relative_to(project_root))
            wide = compare_dir / f"Nameplate_{asset}_{tag}_front.png"
            p1.shot(focus, radius, (0.0, 0.0), 52.0, scale, wide)
            images[f"front_{tag}"] = str(wide.relative_to(project_root))

        row = dict(payload_fbx)
        row.update({
            "objects": rows,
            "counts_before_after": counts,
            "nameplate_audit": audit,
            "images": images,
        })
        payload["assets"][asset] = row
        print(f"[B3U-R1] {asset}: submeshes "
              f"{counts['before']['submeshes_total']} -> "
              f"{counts['after']['submeshes_total']}, slots "
              f"{counts['after']['max_material_slots_per_object']}, "
              f"tris {counts['after']['triangles_total']}, nameplate clean "
              f"{audit['clean']} min {audit['min_clearance_mm']} mm")

    payload["status"] = (
        "b3u_r1_ready"
        if all(row["nameplate_audit"]["clean"]
               and row["counts_before_after"]["after"][
                   "max_material_slots_per_object"] <= 2
               for row in payload["assets"].values())
        and all(entry["identical"] for entry in reference_atlas.values()
                if entry["production"])
        else "b3u_r1_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[B3U-R1] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
