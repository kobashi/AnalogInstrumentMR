"""Read-only sectioning of a persistent movable/static contact.

Alignment 64.2. The first Toggle survey answered "does contact reach past the
ring's outer edge?" and called the answer a bore fit. That criterion is too
weak: a block fully embedded in the ring would also pass it, and the field was
named `contact_is_inside_the_bore` while computing something else. This replaces
it with measurements that can actually tell the three cases apart:

* which movable object is doing the touching, separately rather than as one
  `switch x ring` pair;
* how far the movable geometry reaches past the bore's inner radius, which is
  what distinguishes a shaft turning in a hole from a solid overlap;
* how much of the static part's material is occupied, as a sampled volume and
  as a fraction of that part - a fit grazes, a stack overlaps a corner, an
  embedded block fills it;
* a true clip cutaway through the joint at three poses, not a
  part-hidden render.

The same frame is applied to the PowerSlider's `handle_bridge x rail` pair,
which alignment 64.3 asks to characterise the same way.

Read-only: no blend is saved and no candidate is written.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_joint_contact_section.py -- \
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review


CASES = {
    "KineticSafety/Toggle": {
        "root": "PF_Visual_Toggle_KineticSafety_V6",
        "pivot": "switch_pivot",
        "kind": "rotary",
        "axis": (1.0, 0.0, 0.0),
        "sweep": (0.0, 56.0),
        "poses": {"minimum": 0.0, "neutral": 28.0, "maximum": 56.0},
        "static": "KineticSafety_toggle_v6_fixed_retaining_ring",
        # The ring is a flat annulus in the plate, so its bore is about the
        # plate normal, not about the axis the switch turns on.
        "bore_axis": (0.0, 1.0, 0.0),
        "section_x": 0.0,
        "ortho_scale": 0.075,
    },
    "KineticSafety/PowerSlider": {
        "root": "PF_Visual_PowerSlider_KineticSafety_V6",
        "pivot": "slider_travel",
        "kind": "linear",
        "axis": (0.0, 0.0, 1.0),
        "sweep": (-0.09, 0.09),
        "poses": {"minimum": -0.09, "neutral": 0.0, "maximum": 0.09},
        "static": "kinetic_slider_rail",
        # The rail is a straight prism, not a bore; the "inner radius" reading
        # is meaningless for it and is reported as null.
        "bore_axis": None,
        "section_x": 0.042,
        "ortho_scale": 0.110,
    },
}

SAMPLE_STEPS = 26


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--case", dest="cases", action="append", choices=tuple(CASES))
    return parser.parse_args(args)


def pose(pivot, spec, base, value):
    axis = Vector(spec["axis"]).normalized()
    component = max(range(3), key=lambda index: abs(axis[index]))
    if spec["kind"] == "linear":
        location = base.copy()
        location[component] = base[component] + value
        pivot.location = location
    else:
        posed = base.copy()
        posed[component] = base[component] + math.radians(value)
        pivot.rotation_euler = posed
    bpy.context.view_layer.update()


def inside(tree, point, direction=Vector((0.987, 0.109, 0.119))):
    """Point-in-mesh by ray parity.

    The direction is deliberately not axis-aligned: a ray along +X through a
    prism whose faces are perpendicular to X hits edges and coplanar faces and
    miscounts.
    """
    crossings = 0
    origin = point.copy()
    for _ in range(64):
        location, _, _, _ = tree.ray_cast(origin, direction)
        if location is None:
            break
        crossings += 1
        origin = location + direction * 1e-6
    return crossings % 2 == 1


def occupied_volume(static_obj, movers, samples=SAMPLE_STEPS):
    """Sampled volume of static material occupied by the movable island.

    A grid is walked over the static part's bounds and each cell centre is
    tested for being inside both. This is an estimate, and the cell size is
    reported with it so the number is read as one.
    """
    corners = [static_obj.matrix_world @ Vector(c) for c in static_obj.bound_box]
    low = Vector((min(p[i] for p in corners) for i in range(3)))
    high = Vector((max(p[i] for p in corners) for i in range(3)))
    span = high - low
    if min(span) <= 0.0:
        return None
    static_tree, _, _ = pilot.bvh_for(static_obj)
    mover_trees = [pilot.bvh_for(obj)[0] for obj in movers]
    cell = Vector((span[i] / samples for i in range(3)))
    inside_static = 0
    inside_both = 0
    for ix in range(samples):
        for iy in range(samples):
            for iz in range(samples):
                point = Vector((
                    low.x + (ix + 0.5) * cell.x,
                    low.y + (iy + 0.5) * cell.y,
                    low.z + (iz + 0.5) * cell.z,
                ))
                if not inside(static_tree, point):
                    continue
                inside_static += 1
                if any(inside(tree, point) for tree in mover_trees):
                    inside_both += 1
    cell_volume = cell.x * cell.y * cell.z
    return {
        "grid": [samples, samples, samples],
        "cell_mm": [round(cell[i] * 1000.0, 4) for i in range(3)],
        "static_cells": inside_static,
        "occupied_cells": inside_both,
        "occupied_fraction": round(inside_both / inside_static, 6)
        if inside_static
        else None,
        "static_volume_mm3": round(inside_static * cell_volume * 1e9, 3),
        "occupied_volume_mm3": round(inside_both * cell_volume * 1e9, 3),
        "estimate": "grid-sampled, not exact",
    }


def cylindrical(point, centre, axis):
    offset = point - centre
    along = offset.dot(axis)
    return (offset - axis * along).length, along


def section_shot(rig, focus, section_x, ortho_scale, path):
    """Orthographic side view clipped at `section_x`: a real cutaway."""
    bpy.ops.object.camera_add(location=(section_x + 0.5, focus[1], focus[2]))
    camera = bpy.context.object
    camera.name = "Opus5SectionCamera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    camera.rotation_euler = (math.radians(90.0), 0.0, math.radians(90.0))
    # Everything nearer to the camera than the section plane is clipped away,
    # which is what turns a side elevation into a section.
    camera.data.clip_start = 0.5
    camera.data.clip_end = 2.0
    bpy.context.scene.camera = camera

    lights = []
    for name, offset, energy in (
        ("SectionKey", (0.30, -0.22, 0.26), 24.0),
        ("SectionFill", (0.30, 0.18, -0.10), 12.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = 0.4
        light = bpy.data.objects.new(name, data)
        light.location = (
            focus[0] + offset[0],
            focus[1] + offset[1],
            focus[2] + offset[2],
        )
        bpy.context.collection.objects.link(light)
        review.point_at(light, focus)
        lights.append(light)

    review.render_to(path)
    bpy.data.objects.remove(camera, do_unlink=True)
    for light in lights:
        bpy.data.objects.remove(light, do_unlink=True)


def survey(project_root, label):
    spec = CASES[label]
    theme, key = label.split("/")
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{key}_{theme}_V6_Retopo.blend"
    )
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    review.configure_scene()
    root = bpy.data.objects[spec["root"]]
    pivot = bpy.data.objects[spec["pivot"]]
    statics = [
        obj
        for obj in pilot.meshes_under(root)
        if obj.name == spec["static"] or obj.name.startswith(spec["static"] + ".")
    ]
    movers = [
        obj
        for obj in pilot.meshes_under(root)
        if _under(obj, pivot)
    ]
    centre = pivot.matrix_world.translation.copy()
    bore_axis = Vector(spec["bore_axis"]).normalized() if spec["bore_axis"] else None

    static_facts = {}
    for static_obj in statics:
        points = [static_obj.matrix_world @ v.co for v in static_obj.data.vertices]
        facts = {
            "world_bounds": {
                "min": [round(min(p[i] for p in points), 6) for i in range(3)],
                "max": [round(max(p[i] for p in points), 6) for i in range(3)],
            }
        }
        if bore_axis is not None:
            radii = [cylindrical(p, centre, bore_axis)[0] for p in points]
            facts["bore_inner_radius"] = round(min(radii), 6)
            facts["outer_radius"] = round(max(radii), 6)
        static_facts[static_obj.name] = facts

    base = (pivot.location if spec["kind"] == "linear" else pivot.rotation_euler).copy()
    low, high = spec["sweep"]
    per_object = {}
    try:
        for index in range(SAMPLE_STEPS + 1):
            value = low + (high - low) * index / SAMPLE_STEPS
            pose(pivot, spec, base, value)
            for static_obj in statics:
                static_tree, static_vertices, static_polygons = pilot.bvh_for(static_obj)
                for mover in movers:
                    tree, vertices, polygons = pilot.bvh_for(mover)
                    for mine, theirs in tree.overlap(static_tree):
                        points = pilot.triangle_contact_points(
                            [vertices[i] for i in polygons[mine]],
                            [static_vertices[i] for i in static_polygons[theirs]],
                        )
                        if not points:
                            continue
                        entry = per_object.setdefault(
                            f"{mover.name} x {static_obj.name}",
                            {
                                "samples": set(),
                                "contact_points": 0,
                                "radius_min": None,
                                "radius_max": None,
                                "past_bore_inner_mm": None,
                            },
                        )
                        entry["samples"].add(round(value, 6))
                        entry["contact_points"] += len(points)
                        if bore_axis is None:
                            continue
                        inner = static_facts[static_obj.name]["bore_inner_radius"]
                        for point in points:
                            radius, _ = cylindrical(point, centre, bore_axis)
                            entry["radius_min"] = (
                                radius
                                if entry["radius_min"] is None
                                else min(entry["radius_min"], radius)
                            )
                            entry["radius_max"] = (
                                radius
                                if entry["radius_max"] is None
                                else max(entry["radius_max"], radius)
                            )
                            past = (radius - inner) * 1000.0
                            entry["past_bore_inner_mm"] = (
                                past
                                if entry["past_bore_inner_mm"] is None
                                else max(entry["past_bore_inner_mm"], past)
                            )
    finally:
        if spec["kind"] == "linear":
            pivot.location = base
        else:
            pivot.rotation_euler = base
        bpy.context.view_layer.update()

    for entry in per_object.values():
        entry["sample_count"] = len(entry.pop("samples"))
        for name in ("radius_min", "radius_max", "past_bore_inner_mm"):
            if entry[name] is not None:
                entry[name] = round(entry[name], 6)

    # Volume is measured at the pose where the overlap is largest for a rotary
    # joint (full travel) and at rest for a linear one, both being the poses a
    # reviewer would look at.
    pose(pivot, spec, base, spec["poses"]["maximum" if spec["kind"] == "rotary" else "neutral"])
    volumes = {obj.name: occupied_volume(obj, movers) for obj in statics}
    if spec["kind"] == "linear":
        pivot.location = base
    else:
        pivot.rotation_euler = base
    bpy.context.view_layer.update()

    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    corners = [
        obj.matrix_world @ Vector(c)
        for obj in pilot.meshes_under(root)
        for c in obj.bound_box
    ]
    focus = (
        spec["section_x"],
        (min(p.y for p in corners) + max(p.y for p in corners)) * 0.5,
        (min(p.z for p in corners) + max(p.z for p in corners)) * 0.5,
    )
    images = {}
    try:
        for name, value in spec["poses"].items():
            pose(pivot, spec, base, value)
            path = output_dir / f"{key}_{theme}_section_{name}.png"
            section_shot(
                {}, focus, spec["section_x"], spec["ortho_scale"], path
            )
            images[name] = str(path.relative_to(project_root))
    finally:
        if spec["kind"] == "linear":
            pivot.location = base
        else:
            pivot.rotation_euler = base
        bpy.context.view_layer.update()

    stat_after = source.stat()
    print(
        f"[Opus5Section] {label}: "
        + "; ".join(
            f"{pair} samples {facts['sample_count']}, "
            f"past bore inner {facts['past_bore_inner_mm']} mm"
            for pair, facts in sorted(per_object.items())
        )
        + "; occupied "
        + ", ".join(
            f"{name} {v['occupied_fraction']}" if v else f"{name} n/a"
            for name, v in volumes.items()
        )
    )
    return {
        "case": label,
        "source": str(source.relative_to(project_root)),
        "saved_anything": False,
        "source_unchanged": (stat_before.st_mtime_ns, stat_before.st_size)
        == (stat_after.st_mtime_ns, stat_after.st_size),
        "motion": {"kind": spec["kind"], "sweep": list(spec["sweep"]),
                   "samples": SAMPLE_STEPS + 1},
        "static_parts": static_facts,
        "contact_by_object": dict(sorted(per_object.items())),
        "occupied_material": volumes,
        "section_images": images,
        "section_note": (
            "Orthographic side view with the near half clipped away at "
            f"x = {spec['section_x']}; this is a clip cutaway, not a "
            "part-hidden render."
        ),
    }


def _under(obj, parent):
    node = obj
    while node is not None:
        if node is parent:
            return True
        node = node.parent
    return False


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    entries = [survey(project_root, label) for label in (args.cases or CASES)]
    output = (
        project_root / "ArtSource/Blender/BrushUp/Opus5/joint_contact_sections.json"
    )
    output.write_text(
        json.dumps(
            {
                "note": (
                    "Read-only (alignment 64.2). No blend is saved. Contact is "
                    "reported per movable object; penetration is measured "
                    "against the static part's own bore radius where it has "
                    "one; occupied material is a grid-sampled estimate with "
                    "its cell size stated."
                ),
                "cases": {entry["case"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5Section] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
