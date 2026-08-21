"""D-5 revised proposal: sweep the two candidate fixes and measure the limit.

Alignment 68.2. Removing the legacy axle is the common baseline, but it leaves
7-9% of the ring's material occupied by the shaft, which is not a bore fit. Two
fixes were asked for:

* A - enlarge the ring's bore / change its inner profile;
* B - neck or taper the shaft near the pivot.

Rather than argue about which should work, each is swept over its parameter and
measured: contact count and occupied ring volume over the whole 0-56 degree
travel, in all three themes. A third option - moving the ring along the plate
normal - is measured as well, because if A and B both bottom out the proposal
has to say what would actually work rather than only what does not.

Design-only: all edits are made to throwaway copies in memory and no blend is
saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_option_sweep.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_d5_toggle_axle_proposal as d5
import opus5_joint_contact_section as section


THEMES = d5.THEMES
KEY = d5.KEY
SWEEP = d5.SWEEP
SEARCH_STEPS = 13
VERIFY_STEPS = 26
TARGET_CLEARANCE_MM = 0.7


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append", choices=THEMES)
    return parser.parse_args(args)


def radial(point, centre):
    return math.hypot(point.x - centre.x, point.z - centre.z)


def contact_over_sweep(pivot, movers, static_obj, steps):
    static_tree, static_vertices, static_polygons = pilot.bvh_for(static_obj)
    base = pivot.rotation_euler.copy()
    low, high = SWEEP
    samples = 0
    points = 0
    try:
        for index in range(steps + 1):
            angle = low + (high - low) * index / steps
            posed = base.copy()
            posed[0] = base[0] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            hits = 0
            for mover in movers:
                tree, vertices, polygons = pilot.bvh_for(mover)
                for mine, theirs in tree.overlap(static_tree):
                    hits += len(
                        pilot.triangle_contact_points(
                            [vertices[i] for i in polygons[mine]],
                            [static_vertices[i] for i in static_polygons[theirs]],
                        )
                    )
            if hits:
                samples += 1
                points += hits
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return {"samples_with_contact": samples, "contact_points": points}


def enlarge_bore(ring, centre, new_inner):
    """Option A: push the ring's inner vertices out to `new_inner`."""
    axis = Vector((0.0, 1.0, 0.0))
    matrix = ring.matrix_world
    inverse = matrix.inverted()
    moved = 0
    for vertex in ring.data.vertices:
        world = matrix @ vertex.co
        radius = radial(world, centre)
        if radius >= new_inner or radius < 1e-9:
            continue
        scale = new_inner / radius
        world.x = centre.x + (world.x - centre.x) * scale
        world.z = centre.z + (world.z - centre.z) * scale
        vertex.co = inverse @ world
        moved += 1
    ring.data.update()
    return moved


def neck_shaft(shaft, pivot_point, factor, reach):
    """Option B: shrink the shaft's cross-section within `reach` of the pivot.

    The shaft runs along Z, so its cross-section is the XY offset from its own
    axis; scaling that thins the stem without shortening the lever.
    """
    matrix = shaft.matrix_world
    inverse = matrix.inverted()
    moved = 0
    for vertex in shaft.data.vertices:
        world = matrix @ vertex.co
        along = world.z - pivot_point.z
        if abs(along) > reach:
            continue
        world.x = pivot_point.x + (world.x - pivot_point.x) * factor
        world.y = pivot_point.y + (world.y - pivot_point.y) * factor
        vertex.co = inverse @ world
        moved += 1
    shaft.data.update()
    return moved


def move_ring(ring, delta_y):
    matrix = ring.matrix_world
    inverse = matrix.inverted()
    for vertex in ring.data.vertices:
        world = matrix @ vertex.co
        world.y += delta_y
        vertex.co = inverse @ world
    ring.data.update()


def prepare(project_root, theme):
    """Open the Toggle, split `switch`, drop the axle. Returns the scene parts."""
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{KEY}_{theme}_V6_Retopo.blend"
    )
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{KEY}_{theme}_V6"]
    pivot = bpy.data.objects[d5.PIVOT]
    switch = bpy.data.objects[d5.MOVABLE]
    ring = next(
        obj
        for obj in pilot.meshes_under(root)
        if d5.RING_TOKEN in obj.name.lower()
    )
    joint = next(
        (obj for obj in pilot.meshes_under(root) if "hemisphere" in obj.name.lower()),
        None,
    )
    centre = pivot.matrix_world.translation.copy()

    pieces = d5.components_of(switch)
    for piece in pieces:
        pilot.parent_keep_world(piece, pivot)
    bpy.context.view_layer.update()
    facts = {piece.name: d5.describe(piece, centre) for piece in pieces}
    axle = min(
        (name for name, f in facts.items() if f["longest_axis"] == "X"),
        key=lambda name: facts[name]["distance_from_pivot_mm"],
    )
    # Filter first, remove second: `bpy.data.objects.remove` invalidates the
    # Python object, so reading `.name` off it afterwards raises.
    doomed = bpy.data.objects[axle]
    pieces = [piece for piece in pieces if piece is not doomed]
    bpy.data.objects.remove(doomed, do_unlink=True)
    switch.hide_viewport = True
    shaft = max(pieces, key=lambda p: facts[p.name]["length_mm"][2])
    movers = pieces + ([joint] if joint else [])
    return {
        "source": source,
        "root": root,
        "pivot": pivot,
        "ring": ring,
        "joint": joint,
        "shaft": shaft,
        "movers": movers,
        "pieces": pieces,
        "centre": centre,
        "removed_axle": axle,
        "axle_triangles": facts[axle]["triangles"],
    }


def measure(scene, steps=SEARCH_STEPS):
    contact = contact_over_sweep(
        scene["pivot"], scene["pieces"], scene["ring"], steps
    )
    volume = section.occupied_volume(scene["ring"], scene["pieces"])
    return {
        "shaft_contact": contact,
        "ring_occupied_fraction": (volume or {}).get("occupied_fraction"),
    }


def survey_one(project_root, theme):
    scene = prepare(project_root, theme)
    ring_points = [
        scene["ring"].matrix_world @ v.co for v in scene["ring"].data.vertices
    ]
    inner = min(radial(p, scene["centre"]) for p in ring_points)
    outer = max(radial(p, scene["centre"]) for p in ring_points)
    ring_y = [
        round(min(p.y for p in ring_points), 6),
        round(max(p.y for p in ring_points), 6),
    ]
    shaft_points = [
        scene["shaft"].matrix_world @ v.co for v in scene["shaft"].data.vertices
    ]
    shaft_y = [
        round(min(p.y for p in shaft_points), 6),
        round(max(p.y for p in shaft_points), 6),
    ]

    baseline = measure(scene)
    results = {"axle_removed_only": baseline}

    # Option A: enlarge the bore, up to just short of the outer edge.
    option_a = {}
    for fraction in (0.4, 0.6, 0.8, 0.95):
        scene_a = prepare(project_root, theme)
        target = inner + (outer - inner) * fraction
        moved = enlarge_bore(scene_a["ring"], scene_a["centre"], target)
        option_a[f"inner_radius_{round(target, 5)}"] = dict(
            measure(scene_a), vertices_moved=moved
        )

    # Option B: neck the shaft near the pivot, down to a quarter section.
    option_b = {}
    for factor in (0.75, 0.5, 0.25):
        scene_b = prepare(project_root, theme)
        moved = neck_shaft(
            scene_b["shaft"], scene_b["centre"], factor, outer * 1.2
        )
        option_b[f"section_x{factor}"] = dict(
            measure(scene_b), vertices_moved=moved
        )

    # Option C, beyond the two asked for: take the ring out of the shaft's own
    # depth band. Reported because A and B may not reach zero.
    option_c = {}
    for delta in (0.004, 0.008, 0.012):
        scene_c = prepare(project_root, theme)
        move_ring(scene_c["ring"], delta)
        option_c[f"ring_inboard_{round(delta * 1000, 1)}mm"] = measure(scene_c)

    return {
        "theme": theme,
        "source": str(scene["source"].relative_to(project_root)),
        "saved_anything": False,
        "removed_axle_component": scene["removed_axle"],
        "axle_triangles": scene["axle_triangles"],
        "ring": {
            "inner_radius": round(inner, 6),
            "outer_radius": round(outer, 6),
            "y": ring_y,
        },
        "shaft_y": shaft_y,
        "shaft_sits_inside_ring_depth_band": (
            shaft_y[0] < ring_y[1] and shaft_y[1] > ring_y[0]
        ),
        "baseline_axle_removed": baseline,
        "option_a_enlarge_bore": option_a,
        "option_b_neck_shaft": option_b,
        "option_c_move_ring_inboard": option_c,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    entries = [survey_one(project_root, theme) for theme in (args.themes or THEMES)]
    for entry in entries:
        print(
            f"[Opus5D5Sweep] {entry['theme']}: baseline occupied "
            f"{entry['baseline_axle_removed']['ring_occupied_fraction']}; "
            + "; ".join(
                f"{name} best occupied "
                f"{min((v['ring_occupied_fraction'] for v in option.values() if v['ring_occupied_fraction'] is not None), default=None)}"
                for name, option in (
                    ("A", entry["option_a_enlarge_bore"]),
                    ("B", entry["option_b_neck_shaft"]),
                    ("C", entry["option_c_move_ring_inboard"]),
                )
            )
        )
    output = project_root / "ArtSource/Blender/BrushUp/Opus5/d5_option_sweep.json"
    output.write_text(
        json.dumps(
            {
                "defect": "D-5",
                "note": (
                    "Design-only parameter sweep (alignment 68.2). Every edit "
                    "is made to throwaway in-memory geometry; no blend is "
                    "saved. Axle removal is the common baseline for all three "
                    "options."
                ),
                "target_clearance_mm": TARGET_CLEARANCE_MM,
                "search_sweep_samples": SEARCH_STEPS + 1,
                "themes": {entry["theme"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D5Sweep] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
