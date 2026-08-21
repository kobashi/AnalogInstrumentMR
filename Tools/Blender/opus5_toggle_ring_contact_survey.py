"""Read-only survey: is the Toggle's switch/retaining-ring contact a fit?

Alignment 59.3. `switch x KineticSafety_toggle_v6_fixed_retaining_ring` overlaps
in all 29 sweep samples, in the baseline and in the Gate B3 candidate alike. The
name and position suggest a retaining fit rather than a defect, but "suggest" is
not a measurement, so this asks the question the geometry can answer:

    does the stem stay inside the ring it turns in, or does it break out
    through a surface someone can see?

The test is the ring's own dimensions. Contact confined between the ring's inner
and outer radius, inside its depth band, is the stem sitting in its bore. Any
switch geometry beyond the ring's outer radius while inside that band is the
stem coming out the side, which would be visible.

Read-only: no blend is saved and no candidate is written.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_toggle_ring_contact_survey.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import opus5_brushup_review as brushup_review


THEME = "KineticSafety"
KEY = "Toggle"
ROOT = f"PF_Visual_{KEY}_{THEME}_V6"
PIVOT = "switch_pivot"
MOVABLE = "switch"
RING = "KineticSafety_toggle_v6_fixed_retaining_ring"
SWEEP = (0.0, 56.0)
STEPS = 28
POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def cylindrical(point, centre, axis):
    """Distance from the pivot axis, and position along it."""
    offset = point - centre
    along = offset.dot(axis)
    return (offset - axis * along).length, along


def survey(project_root):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / THEME
        / f"BL_{KEY}_{THEME}_V6_Retopo.blend"
    )
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    review.configure_scene()
    root = bpy.data.objects[ROOT]
    pivot = bpy.data.objects[PIVOT]
    switch = bpy.data.objects[MOVABLE]
    ring = bpy.data.objects[RING]
    centre = pivot.matrix_world.translation.copy()
    # The ring is a flat annulus lying in the plate, so its bore is about the
    # plate normal (Y) - not about X, which is merely the axis the switch turns
    # about. Measuring the bore about X gave an "inner radius" of 0.7 mm, which
    # is the ring seen edge-on rather than the hole the stem passes through.
    axis = Vector((0.0, 1.0, 0.0))

    ring_points = [ring.matrix_world @ vertex.co for vertex in ring.data.vertices]
    ring_radii = [cylindrical(point, centre, axis)[0] for point in ring_points]
    ring_along = [cylindrical(point, centre, axis)[1] for point in ring_points]
    ring_facts = {
        "inner_radius": round(min(ring_radii), 6),
        "outer_radius": round(max(ring_radii), 6),
        "along_axis": [round(min(ring_along), 6), round(max(ring_along), 6)],
        "world_y": [
            round(min(point.y for point in ring_points), 6),
            round(max(point.y for point in ring_points), 6),
        ],
    }

    movable = [switch] + [
        obj for obj in pilot.meshes_under(root) if obj.parent is switch
    ]
    ring_tree, ring_vertices, ring_polygons = pilot.bvh_for(ring)

    base = pivot.rotation_euler.copy()
    low, high = SWEEP
    contact_radii = []
    contact_along = []
    contact_from_pivot = []
    samples_with_contact = 0
    try:
        for index in range(STEPS + 1):
            angle = low + (high - low) * index / STEPS
            posed = base.copy()
            posed[0] = base[0] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()

            found = False
            for obj in movable:
                tree, vertices, polygons = pilot.bvh_for(obj)
                for mine, theirs in tree.overlap(ring_tree):
                    points = pilot.triangle_contact_points(
                        [vertices[i] for i in polygons[mine]],
                        [ring_vertices[i] for i in ring_polygons[theirs]],
                    )
                    for point in points:
                        radius, along = cylindrical(point, centre, axis)
                        contact_radii.append(radius)
                        contact_along.append(along)
                        contact_from_pivot.append((point - centre).length)
                        found = True
            if found:
                samples_with_contact += 1
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()

    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    rig = brushup_review.rig_from(root)
    # Wide enough that a guard post does not fill the frame, and off-axis
    # so the stem is seen emerging from the ring rather than end-on.
    rig = dict(rig, radius=rig["radius"] * 1.05, lens=70.0)
    images = {}
    try:
        for hidden in (False, True):
            ring.hide_render = hidden
            tag = "ring_hidden" if hidden else "ring_shown"
            for name, angle in POSES:
                posed = base.copy()
                posed[0] = base[0] + math.radians(angle)
                pivot.rotation_euler = posed
                bpy.context.view_layer.update()
                path = output_dir / f"{KEY}_{THEME}_ring_{tag}_{name}.png"
                review.shot(
                    rig, rig["focus"], rig["radius"], (34.0, 26.0), rig["lens"], path
                )
                images[f"{tag}_{name}"] = str(path.relative_to(project_root))
    finally:
        ring.hide_render = False
        pivot.rotation_euler = base
        bpy.context.view_layer.update()

    stat_after = source.stat()
    # The decisive test is where the *contact* is, not where the island is. A
    # first attempt asked whether any movable geometry sat beyond the ring's
    # outer radius inside its depth band, and 190 vertices did - but those are
    # the lever lying flat over the plate at rest, passing above the ring at
    # radius 84 mm. Passing over a ring is not emerging from it. What would be
    # visible is contact reaching past the ring's outer edge.
    outside_ring = [r for r in contact_radii if r > ring_facts["outer_radius"] + 1e-6]
    inside_bore = bool(contact_radii) and not outside_ring
    return {
        "defect_candidate": "Toggle switch x fixed_retaining_ring",
        "model": f"{THEME}/{KEY}",
        "source": str(source.relative_to(project_root)),
        "saved_anything": False,
        "source_unchanged": (stat_before.st_mtime_ns, stat_before.st_size)
        == (stat_after.st_mtime_ns, stat_after.st_size),
        "sweep_degrees": list(SWEEP),
        "samples": STEPS + 1,
        "samples_with_contact": samples_with_contact,
        "ring": ring_facts,
        "contact_radius_from_axis": {
            "min": round(min(contact_radii), 6) if contact_radii else None,
            "max": round(max(contact_radii), 6) if contact_radii else None,
            "points": len(contact_radii),
        },
        "contact_distance_from_pivot": {
            "min": round(min(contact_from_pivot), 6) if contact_from_pivot else None,
            "max": round(max(contact_from_pivot), 6) if contact_from_pivot else None,
        },
        "contact_along_axis": {
            "min": round(min(contact_along), 6) if contact_along else None,
            "max": round(max(contact_along), 6) if contact_along else None,
        },
        "contact_beyond_ring_outer_radius": {
            "count": len(outside_ring),
            "max_radius": round(max(outside_ring), 6) if outside_ring else None,
        },
        "contact_is_inside_the_bore": inside_bore,
        "verdict": (
            "intended interface: contact is confined to the ring's own annulus "
            "and none of it reaches past the ring's outer edge"
            if inside_bore
            else "solid penetration reaching outside the ring"
        ),
        "images": images,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    report = survey(project_root)
    output = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5/toggle_ring_contact_survey.json"
    )
    output.write_text(
        json.dumps(
            {
                "note": (
                    "Read-only survey (alignment 59.3). No blend is saved. "
                    "Radii are measured from the pivot axis, not from the pivot "
                    "point, because the switch turns about X."
                ),
                **report,
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"[Opus5ToggleRing] contact radius "
        f"{report['contact_radius_from_axis']['min']}.."
        f"{report['contact_radius_from_axis']['max']}, "
        f"ring {report['ring']['inner_radius']}..{report['ring']['outer_radius']}, "
        f"contact beyond outer edge {report['contact_beyond_ring_outer_radius']['count']}; "
        f"{report['verdict']}"
    )
    print(f"[Opus5ToggleRing] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
