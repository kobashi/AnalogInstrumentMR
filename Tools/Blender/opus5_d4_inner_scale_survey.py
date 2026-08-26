"""D-4 design survey: where can Orbital Analog's inner scale go?

Alignment 59.2. The inner scale rings sit inside the circle the needle sweeps
*and* in the same depth band, so on Medium and Large the needle cuts through
them and on Round they miss by 24 micrometres. Radial retraction - the D-3 fix -
cannot help: the centre mark sits on the pivot, and moving the arcs outward
would land them on the tick ring.

This measures the depth stack, derives a proposal from it, and then *verifies*
the proposal in memory before proposing it: the shifted scene is re-swept, and
the numbers reported are measured on the proposal rather than predicted for it.

Nothing is saved. The shipped blends are opened read-only and no candidate blend
is written - alignment 59.2 asks for a proposal first, not a fix.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d4_inner_scale_survey.py -- \
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
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import opus5_brushup_review as brushup_review
import opus5_d3_needle_tick_audit as audit


THEME = "OrbitalAnalog"
KEYS = ("MeterRound", "MeterMedium", "MeterLarge")

# Same proportional targets as D-3 (alignment 59.1), now applied to depth.
CLEARANCE_MM = {"MeterRound": 0.7, "MeterMedium": 1.4, "MeterLarge": 2.1}

SCALE_TOKEN = "inner_scale"
POSES = (("minimum", -55.0), ("neutral", 0.0), ("maximum", 55.0))


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--key", dest="keys", action="append", choices=KEYS)
    return parser.parse_args(args)


def extent(obj, centre):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    radii = [math.hypot(p.x - centre.x, p.z - centre.z) for p in points]
    return {
        "y": [round(min(p.y for p in points), 6), round(max(p.y for p in points), 6)],
        "radius": [round(min(radii), 6), round(max(radii), 6)],
    }


def sweep_hits(root, pivot, needle, others, steps=44):
    """Exact contact and closest approach between the needle and `others`."""
    trees = {obj.name: pilot.bvh_for(obj) for obj in others}
    facts = {obj.name: {"intersects": False, "closest_mm": None} for obj in others}
    base = pivot.rotation_euler.copy()
    low, high = audit.SWEEP
    try:
        for index in range(steps + 1):
            angle = low + (high - low) * index / steps
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            tree, vertices, polygons = pilot.bvh_for(needle)
            nearest = BVHTree.FromPolygons(
                [tuple(v) for v in vertices], polygons, all_triangles=True
            )
            for obj in others:
                entry = facts[obj.name]
                other, other_vertices, other_polygons = trees[obj.name]
                hit = any(
                    pilot.triangle_contact_points(
                        [vertices[i] for i in polygons[mine]],
                        [other_vertices[i] for i in other_polygons[theirs]],
                    )
                    for mine, theirs in tree.overlap(other)
                )
                if hit:
                    entry["intersects"] = True
                    entry["closest_mm"] = 0.0
                    continue
                if entry["closest_mm"] == 0.0:
                    continue
                distances = [
                    distance
                    for _, _, _, distance in (
                        nearest.find_nearest(v) for v in other_vertices
                    )
                    if distance is not None
                ]
                if distances:
                    closest = round(min(distances) * 1000.0, 4)
                    if entry["closest_mm"] is None or closest < entry["closest_mm"]:
                        entry["closest_mm"] = closest
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return facts


def pair_contacts(movers, others):
    """Exact contact and closest approach for every mover/other pair.

    The inner scale is static in both states, so its relationship to the dial,
    the glass, the retainer and the housing does not depend on the needle's
    pose and needs no sweep - one measurement per pair is the whole answer.
    """
    other_trees = {obj.name: pilot.bvh_for(obj) for obj in others}
    result = {}
    for mover in movers:
        tree, vertices, polygons = pilot.bvh_for(mover)
        nearest = BVHTree.FromPolygons(
            [tuple(v) for v in vertices], polygons, all_triangles=True
        )
        for other in others:
            if other is mover:
                continue
            other_tree, other_vertices, other_polygons = other_trees[other.name]
            hits = 0
            for mine, theirs in tree.overlap(other_tree):
                if pilot.triangle_contact_points(
                    [vertices[i] for i in polygons[mine]],
                    [other_vertices[i] for i in other_polygons[theirs]],
                ):
                    hits += 1
            if hits:
                result[f"{mover.name} x {other.name}"] = {
                    "intersects": True,
                    "triangles": hits,
                    "closest_mm": 0.0,
                }
                continue
            distances = [
                distance
                for _, _, _, distance in (
                    nearest.find_nearest(v) for v in other_vertices
                )
                if distance is not None
            ]
            result[f"{mover.name} x {other.name}"] = {
                "intersects": False,
                "triangles": 0,
                "closest_mm": round(min(distances) * 1000.0, 4) if distances else None,
            }
    return result


def diff_contacts(before, after):
    """Split pairs into new / resolved / existing, so nothing is conflated."""
    was = {k for k, v in before.items() if v["intersects"]}
    now = {k for k, v in after.items() if v["intersects"]}
    return {
        "new": sorted(now - was),
        "resolved": sorted(was - now),
        "existing": sorted(was & now),
    }


def shift(obj, delta_y):
    for vertex in obj.data.vertices:
        world = obj.matrix_world @ vertex.co
        world.y += delta_y
        vertex.co = obj.matrix_world.inverted() @ world
    obj.data.update()


def render_state(root, pivot, rig, prefix, output_dir, project_root):
    images = {}
    base = pivot.rotation_euler.copy()
    try:
        for name, angle in POSES:
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            path = output_dir / f"{prefix}_{name}.png"
            review.shot(rig, rig["focus"], rig["radius"], (0.0, 4.0), rig["lens"], path)
            images[name] = str(path.relative_to(project_root))
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return images


def survey_one(project_root, key):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / THEME
        / f"BL_{key}_{THEME}_V6_Retopo.blend"
    )
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    review.configure_scene()
    root = bpy.data.objects[f"PF_Visual_{key}_{THEME}_V6"]
    pivot = bpy.data.objects[audit.PIVOT]
    needle = bpy.data.objects[audit.NEEDLE]
    centre = pivot.matrix_world.translation.copy()
    margin = CLEARANCE_MM[key] / 1000.0

    meshes = pilot.meshes_under(root)
    scales = [obj for obj in meshes if SCALE_TOKEN in obj.name]
    if not scales:
        raise RuntimeError(f"{key}: no {SCALE_TOKEN} meshes")
    needle_span = extent(needle, centre)
    swept_radius = max(
        audit.radial(needle.matrix_world @ v.co, centre) for v in needle.data.vertices
    )
    stack = {obj.name: extent(obj, centre) for obj in meshes if obj.name in {
        "housing", "dial", audit.NEEDLE
    } or SCALE_TOKEN in obj.name or "retainer" in obj.name or "glass" in obj.name}

    # The centre mark sits under the needle hub, so it cannot go behind the
    # needle without disappearing; it goes in front instead, reading as a hub
    # cap. The arcs go behind, where the needle passing in front of a dial mark
    # is the correct reading order.
    plan = {}
    for obj in scales:
        span = extent(obj, centre)
        if span["radius"][1] < swept_radius * 0.35:
            target_front = needle_span["y"][0] - margin
            delta = target_front - span["y"][1]
            placement = "in front of the needle (hub cap)"
        else:
            target_front = needle_span["y"][1] + margin
            delta = target_front - span["y"][0]
            placement = "behind the needle"
        plan[obj.name] = {
            "placement": placement,
            "delta_y_mm": round(delta * 1000.0, 4),
            "y_before": span["y"],
            "y_after": [round(span["y"][0] + delta, 6), round(span["y"][1] + delta, 6)],
            "radius": span["radius"],
        }

    # Alignment 64.1: the moved parts have to be measured against everything
    # they could newly touch, not only against the needle.
    statics = [obj for obj in meshes if obj is not needle and obj not in scales]
    before_hits = sweep_hits(root, pivot, needle, scales)
    before_needle = sweep_hits(root, pivot, needle, statics)
    before_static = pair_contacts(scales, statics + scales)
    before_bounds = pilot.world_bounds(meshes)

    output_dir = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    rig = brushup_review.rig_from(root)
    rig = dict(rig, radius=rig["radius"] * 0.92, lens=74.0)
    before_images = render_state(
        root, pivot, rig, f"{key}_{THEME}_d4_current", output_dir, project_root
    )

    for obj in scales:
        shift(obj, plan[obj.name]["delta_y_mm"] / 1000.0)

    after_hits = sweep_hits(root, pivot, needle, scales)
    after_needle = sweep_hits(root, pivot, needle, statics)
    after_static = pair_contacts(scales, statics + scales)
    after_bounds = pilot.world_bounds(pilot.meshes_under(root))
    after_images = render_state(
        root, pivot, rig, f"{key}_{THEME}_d4_proposed", output_dir, project_root
    )

    problems = []
    remaining = sorted(n for n, f in after_hits.items() if f["intersects"])
    if remaining:
        problems.append(f"proposal still intersects: {remaining}")
    short = sorted(
        (n, f["closest_mm"])
        for n, f in after_hits.items()
        if f["closest_mm"] is not None and f["closest_mm"] < CLEARANCE_MM[key] - 1e-6
    )
    if short:
        problems.append(f"below the {CLEARANCE_MM[key]} mm target: {short}")
    static_diff = diff_contacts(before_static, after_static)
    needle_diff = diff_contacts(
        {k: v for k, v in before_needle.items()},
        {k: v for k, v in after_needle.items()},
    )
    if static_diff["new"]:
        problems.append(f"the shift creates new contacts: {static_diff['new']}")
    if needle_diff["new"]:
        problems.append(
            f"the shift creates new needle contacts: {needle_diff['new']}"
        )
    if after_bounds != before_bounds:
        problems.append(f"bounds would move: {before_bounds} -> {after_bounds}")

    stat_after = source.stat()
    if (stat_before.st_mtime_ns, stat_before.st_size) != (
        stat_after.st_mtime_ns,
        stat_after.st_size,
    ):
        problems.append("source blend changed on disk")

    print(
        f"[Opus5D4Survey] {key}: shift "
        + ", ".join(
            f"{n.split('_')[-1]} {p['delta_y_mm']:+.2f} mm" for n, p in plan.items()
        )
        + f"; after: intersections {len(remaining)}, "
        f"closest {min((f['closest_mm'] for f in after_hits.values() if f['closest_mm']), default=None)} mm, "
        f"bounds unchanged {after_bounds == before_bounds}, "
        f"new static contacts {len(static_diff['new'])}, "
        f"new needle contacts {len(needle_diff['new'])}"
    )
    return {
        "model": f"{THEME}/{key}",
        "source": str(source.relative_to(project_root)),
        "saved_anything": False,
        "clearance_target_mm": CLEARANCE_MM[key],
        "needle": needle_span,
        "needle_swept_radius": round(swept_radius, 6),
        "depth_stack": stack,
        "proposal": plan,
        "needle_vs_inner_scale": {"before": before_hits, "after": after_hits},
        "inner_scale_vs_static": {
            "before": before_static,
            "after": after_static,
            "difference": static_diff,
        },
        "needle_vs_other_static": {
            "before": before_needle,
            "after": after_needle,
            # Diffed rather than listed: the shipped tick contacts are D-3 and
            # would otherwise read as contacts this proposal created.
            "difference": needle_diff,
        },
        "bounds_before": before_bounds,
        "bounds_after_proposal": after_bounds,
        "bounds_unchanged": after_bounds == before_bounds,
        "images_current": before_images,
        "images_proposed": after_images,
        "problems": problems,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    entries = [survey_one(project_root, key) for key in (args.keys or KEYS)]
    output = project_root / "ArtSource/Blender/BrushUp/Opus5/d4_inner_scale_survey.json"
    output.write_text(
        json.dumps(
            {
                "defect": "D-4",
                "note": (
                    "Read-only design survey (alignment 59.2). No blend is "
                    "saved. The proposal is applied in memory and re-measured, "
                    "so the 'after' numbers are measured rather than predicted."
                ),
                "clearance_target_mm": CLEARANCE_MM,
                "models": {entry["model"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D4Survey] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
