"""D-5 design proposal: which part of `switch` is inside the retaining ring?

Alignment 66.3. The V5 builder joins `switch_shaft`, `switch_axle` and the grip
into one `switch` mesh, and the V6 detail pass then asks
`remove_named_meshes(..., "switch_axle")` - which matches nothing, because no
object by that name survives the join. The legacy axle therefore stays inside
the ring the V6 pass builds around it.

Before proposing a removal, this measures which *connected component* of the
joined mesh actually touches the ring. The joined mesh's components are the
shaft, the axle and the grip, so splitting it separates a legacy leftover from
the lever the toggle needs. That distinction decides whether removing the axle
fixes D-5 or only part of it.

Read-only: components are split on throwaway copies and no blend is saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_toggle_axle_proposal.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_joint_contact_section as section


THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
KEY = "Toggle"
PIVOT = "switch_pivot"
MOVABLE = "switch"
RING_TOKEN = "retaining_ring"
SWEEP = (0.0, 56.0)
STEPS = 26


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append", choices=THEMES)
    return parser.parse_args(args)


def components_of(obj):
    """Split a joined mesh into connected components, on a throwaway copy."""
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.matrix_world = obj.matrix_world.copy()
    copy.parent = None
    bpy.context.collection.objects.link(copy)

    mesh = bmesh.new()
    mesh.from_mesh(copy.data)
    mesh.verts.ensure_lookup_table()
    seen = set()
    islands = []
    for vertex in mesh.verts:
        if vertex.index in seen:
            continue
        stack = [vertex]
        island = set()
        while stack:
            current = stack.pop()
            if current.index in island:
                continue
            island.add(current.index)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other.index not in island:
                    stack.append(other)
        seen |= island
        islands.append(island)
    mesh.free()

    pieces = []
    for index, island in enumerate(islands):
        piece = copy.copy()
        piece.data = copy.data.copy()
        piece.name = f"{obj.name}_component_{index}"
        bpy.context.collection.objects.link(piece)
        inner = bmesh.new()
        inner.from_mesh(piece.data)
        inner.verts.ensure_lookup_table()
        doomed = [v for v in inner.verts if v.index not in island]
        bmesh.ops.delete(inner, geom=doomed, context="VERTS")
        inner.to_mesh(piece.data)
        inner.free()
        piece.data.update()
        pieces.append(piece)
    bpy.data.objects.remove(copy, do_unlink=True)
    return pieces


def describe(obj, centre):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    span = [
        [round(min(p[i] for p in points), 6), round(max(p[i] for p in points), 6)]
        for i in range(3)
    ]
    lengths = [span[i][1] - span[i][0] for i in range(3)]
    longest = max(range(3), key=lambda i: lengths[i])
    return {
        "vertices": len(obj.data.vertices),
        "triangles": len(obj.data.polygons),
        "bounds": {"x": span[0], "y": span[1], "z": span[2]},
        "longest_axis": "XYZ"[longest],
        "length_mm": [round(l * 1000.0, 3) for l in lengths],
        "distance_from_pivot_mm": round(
            min((p - centre).length for p in points) * 1000.0, 3
        ),
    }


def sweep_contact(pivot, movers, ring, steps=STEPS):
    ring_tree, ring_vertices, ring_polygons = pilot.bvh_for(ring)
    facts = {obj.name: {"samples": 0, "contact_points": 0} for obj in movers}
    base = pivot.rotation_euler.copy()
    low, high = SWEEP
    try:
        for index in range(steps + 1):
            angle = low + (high - low) * index / steps
            posed = base.copy()
            posed[0] = base[0] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            for obj in movers:
                tree, vertices, polygons = pilot.bvh_for(obj)
                hits = 0
                for mine, theirs in tree.overlap(ring_tree):
                    hits += len(
                        pilot.triangle_contact_points(
                            [vertices[i] for i in polygons[mine]],
                            [ring_vertices[i] for i in ring_polygons[theirs]],
                        )
                    )
                if hits:
                    facts[obj.name]["samples"] += 1
                    facts[obj.name]["contact_points"] += hits
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return facts


def survey_one(project_root, theme):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{KEY}_{theme}_V6_Retopo.blend"
    )
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{KEY}_{theme}_V6"]
    pivot = bpy.data.objects[PIVOT]
    switch = bpy.data.objects[MOVABLE]
    rings = [
        obj for obj in pilot.meshes_under(root) if RING_TOKEN in obj.name.lower()
    ]
    if not rings:
        raise RuntimeError(f"{theme}: no {RING_TOKEN} mesh")
    ring = rings[0]
    centre = pivot.matrix_world.translation.copy()

    pieces = components_of(switch)
    for piece in pieces:
        pilot.parent_keep_world(piece, pivot)
    bpy.context.view_layer.update()

    facts = {piece.name: describe(piece, centre) for piece in pieces}
    switch.hide_viewport = True
    contact = sweep_contact(pivot, pieces, ring)
    for name, entry in contact.items():
        facts[name]["contact_samples"] = entry["samples"]
        facts[name]["contact_points"] = entry["contact_points"]

    # The axle is the component whose longest extent is along X: the shaft runs
    # along Z and the grip sits at the far end of it.
    axle = sorted(
        (name for name, f in facts.items() if f["longest_axis"] == "X"),
        key=lambda name: facts[name]["distance_from_pivot_mm"],
    )
    contacting = sorted(
        name for name, f in facts.items() if f["contact_points"]
    )
    # Does removing the axle actually fix it? Measure, do not assume: keep the
    # other components, drop the axle, and re-measure contact and the volume of
    # ring material occupied. Section 65.4 measured 32.9% with the axle in.
    residual = None
    if axle:
        keep = [p for p in pieces if p.name != axle[0]]
        doomed = next(p for p in pieces if p.name == axle[0])
        bpy.data.objects.remove(doomed, do_unlink=True)
        pieces = keep
        residual_contact = sweep_contact(pivot, pieces, ring)
        volume = section.occupied_volume(ring, pieces)
        residual = {
            "removed_component": axle[0],
            "removed_triangles": facts[axle[0]]["triangles"],
            "contact": {
                name: entry
                for name, entry in residual_contact.items()
                if entry["contact_points"]
            },
            "occupied_material_after_removal": volume,
        }

    stat_after = source.stat()
    for piece in pieces:
        bpy.data.objects.remove(piece, do_unlink=True)

    return {
        "theme": theme,
        "source": str(source.relative_to(project_root)),
        "source_unchanged": (stat_before.st_mtime_ns, stat_before.st_size)
        == (stat_after.st_mtime_ns, stat_after.st_size),
        "ring": ring.name,
        "switch_triangles": len(switch.data.polygons),
        "components": facts,
        "axle_candidates": axle,
        "components_contacting_ring": contacting,
        "axle_is_the_only_contact": bool(axle) and contacting == axle[:1],
        "with_axle_removed": residual,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    entries = [survey_one(project_root, theme) for theme in (args.themes or THEMES)]
    for entry in entries:
        print(
            f"[Opus5D5] {entry['theme']}: {len(entry['components'])} components, "
            f"axle {entry['axle_candidates']}, "
            f"contacting {entry['components_contacting_ring']}, "
            f"axle-only {entry['axle_is_the_only_contact']}, "
            f"after removal: contact {list((entry['with_axle_removed'] or {}).get('contact', {}))}, "
            f"occupied {((entry['with_axle_removed'] or {}).get('occupied_material_after_removal') or {}).get('occupied_fraction')}"
        )
    output = (
        project_root / "ArtSource/Blender/BrushUp/Opus5/d5_toggle_axle_proposal.json"
    )
    output.write_text(
        json.dumps(
            {
                "defect": "D-5",
                "note": (
                    "Read-only (alignment 66.3). Components are split on "
                    "throwaway copies; no blend is saved and no candidate is "
                    "written. Contact is measured per component so a legacy "
                    "leftover can be told apart from the lever itself."
                ),
                "themes": {entry["theme"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D5] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
