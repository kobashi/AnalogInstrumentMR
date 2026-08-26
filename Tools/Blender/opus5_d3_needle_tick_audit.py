"""Read-only D-3 survey: does the needle reach the tick ring on any meter?

`docs/V6_KNOWN_DEFECTS.md` D-3 was found on two Kinetic Safety meters. Alignment
56.1 asks the prior question before any fix is designed: is this the shared
meter generator or one theme's dial, and what clearance would actually be
needed?

So this sweeps all nine meters - Round / Medium / Large across the three themes
- and reports three things per tick:

* whether the needle really intersects it, by exact triangle-triangle test over
  the sweep rather than by bounding volumes (alignment 8.2);
* the closest approach in millimetres, so a tick that merely grazes is
  distinguishable from one that is comfortably clear;
* how far the tick's inner end would have to retract to leave a stated margin
  outside the needle's swept circle.

The last one is the number a fix needs, and it is deliberately expressed as a
retraction of the tick rather than a shortening of the needle: the needle's
length is the reading, and changing it changes what the instrument says.

Nothing is written except the report. No blend is saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_needle_tick_audit.py -- \
      --project-root "$PWD" --output <report.json>
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot


THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
KEYS = ("MeterRound", "MeterMedium", "MeterLarge")

PIVOT = "needle_pivot"
NEEDLE = "needle"
SWEEP = (-55.0, 55.0)
STEPS = 44

# The clearance a fix should leave between the needle's swept circle and the
# inner end of a tick. Stated here rather than buried in the numbers so Codex
# can change it and re-read the required retraction straight off the report.
TARGET_MARGIN_MM = 0.8


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--theme", action="append", choices=THEMES)
    parser.add_argument("--key", dest="keys", action="append", choices=KEYS)
    parser.add_argument("--margin-mm", type=float, default=TARGET_MARGIN_MM)
    parser.add_argument(
        "--substitute", action="append", metavar="THEME/KEY=PATH",
        help=(
            "Audit a candidate blend in place of the shipped one. The "
            "substitution is recorded in the report so a candidate result is "
            "never mistaken for a production one."
        ),
    )
    return parser.parse_args(args)


def tree_for(obj):
    return pilot.bvh_for(obj)


def _under(obj, parent):
    node = obj
    while node is not None:
        if node is parent:
            return True
        node = node.parent
    return False


def radial(point, centre):
    return math.hypot(point.x - centre.x, point.z - centre.z)


def audit_one(project_root, theme, key, margin_mm, source=None):
    source = source or (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{key}_{theme}_V6_Retopo.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{key}_{theme}_V6"]
    pivot = bpy.data.objects[PIVOT]
    needle = bpy.data.objects[NEEDLE]
    centre = pivot.matrix_world.translation.copy()

    # Dial marks are found by role, not by name: the three themes call their
    # ticks `kinetic_tick`, `orbital_tick` and `forge_tick`, and two of them
    # carry a second readout ring (`orbital_v6_inner_scale`,
    # `secondary_scale_*`) that the needle can reach just as easily.
    marks = [
        obj
        for obj in pilot.meshes_under(root)
        if obj is not needle
        and not _under(obj, pivot)
        and any(
            pilot.material_role_of(material) == "readout"
            for material in obj.data.materials
            if material is not None
        )
    ]
    if not marks:
        raise RuntimeError(f"{theme}/{key}: no static readout marks")

    # The needle turns about the pivot, so its reach is a circle: the largest
    # radius of any needle vertex, invariant under the sweep.
    needle_mesh = needle.data
    needle_mesh.calc_loop_triangles()
    swept_radius = max(
        radial(needle.matrix_world @ vertex.co, centre)
        for vertex in needle_mesh.vertices
    )

    tick_facts = {}
    for tick in marks:
        points = [tick.matrix_world @ vertex.co for vertex in tick.data.vertices]
        radii = [radial(point, centre) for point in points]
        angles = [
            math.degrees(math.atan2(point.x - centre.x, point.z - centre.z))
            for point in points
        ]
        tick_facts[tick.name] = {
            "angle_degrees": round(sum(angles) / len(angles), 3),
            "inner_radius": round(min(radii), 6),
            "outer_radius": round(max(radii), 6),
            "reaches_inside_swept_circle_mm": round(
                (swept_radius - min(radii)) * 1000.0, 4
            ),
            "closest_approach_mm": None,
            "intersects": False,
            "intersecting_samples": 0,
            "max_contact_triangles": 0,
            "required_retraction_mm": round(
                max(0.0, (swept_radius + margin_mm / 1000.0) - min(radii)) * 1000.0,
                4,
            ),
        }

    tick_trees = {tick.name: tree_for(tick) for tick in marks}
    base = pivot.rotation_euler.copy()
    low, high = SWEEP
    try:
        for index in range(STEPS + 1):
            angle = low + (high - low) * index / STEPS
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()

            needle_tree, needle_vertices, needle_polygons = tree_for(needle)
            nearest = BVHTree.FromPolygons(
                [tuple(vertex) for vertex in needle_vertices],
                needle_polygons,
                all_triangles=True,
            )
            for tick in marks:
                facts = tick_facts[tick.name]
                other, other_vertices, other_polygons = tick_trees[tick.name]
                hits = 0
                for mine, theirs in needle_tree.overlap(other):
                    first = [needle_vertices[i] for i in needle_polygons[mine]]
                    second = [other_vertices[i] for i in other_polygons[theirs]]
                    if pilot.triangle_contact_points(first, second):
                        hits += 1
                if hits:
                    facts["intersects"] = True
                    facts["intersecting_samples"] += 1
                    facts["max_contact_triangles"] = max(
                        facts["max_contact_triangles"], hits
                    )
                    facts["closest_approach_mm"] = 0.0
                    continue
                if facts["closest_approach_mm"] == 0.0:
                    continue
                distances = []
                for vertex in other_vertices:
                    location, _, _, distance = nearest.find_nearest(vertex)
                    if location is not None:
                        distances.append(distance)
                if distances:
                    closest = round(min(distances) * 1000.0, 4)
                    if (
                        facts["closest_approach_mm"] is None
                        or closest < facts["closest_approach_mm"]
                    ):
                        facts["closest_approach_mm"] = closest
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()

    offenders = sorted(
        name for name, facts in tick_facts.items() if facts["intersects"]
    )
    return {
        "model": f"{theme}/{key}",
        "source": str(source.relative_to(project_root)),
        "sweep_degrees": list(SWEEP),
        "samples": STEPS + 1,
        "needle_swept_radius": round(swept_radius, 6),
        "mark_count": len(marks),
        "intersecting_marks": offenders,
        "worst_required_retraction_mm": round(
            max(
                (
                    tick_facts[name]["required_retraction_mm"]
                    for name in offenders
                ),
                default=0.0,
            ),
            4,
        ),
        "marks": dict(sorted(tick_facts.items())),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    substitutions = dict(item.split("=", 1) for item in (args.substitute or []))
    models = {}
    for theme in args.theme or THEMES:
        for key in args.keys or KEYS:
            label = f"{theme}/{key}"
            override = (
                project_root / substitutions[label]
                if label in substitutions
                else None
            )
            entry = audit_one(project_root, theme, key, args.margin_mm, override)
            models[entry["model"]] = entry
            print(
                f"[Opus5D3Audit] {entry['model']}: swept r "
                f"{entry['needle_swept_radius']:.4f}, "
                f"{len(entry['intersecting_marks'])}/{entry['mark_count']} marks hit"
                + (
                    f", retract {entry['worst_required_retraction_mm']} mm"
                    if entry["intersecting_marks"]
                    else ""
                )
            )

    affected = sorted(
        label for label, entry in models.items() if entry["intersecting_marks"]
    )
    themes_affected = sorted({label.split("/")[0] for label in affected})
    keys_affected = sorted({label.split("/")[1] for label in affected})
    report = {
        "defect": "D-3",
        "note": (
            "Read-only survey (alignment 56.1). No blend is modified. "
            "`required_retraction_mm` is how far a tick's inner end would have "
            "to move outward to clear the needle's swept circle by the stated "
            "margin; the needle is deliberately left alone because its length "
            "is the reading."
        ),
        "target_margin_mm": args.margin_mm,
        "substituted_sources": dict(sorted(substitutions.items())),
        "all_sources_are_production": not substitutions,
        "models_audited": len(models),
        "models_affected": affected,
        "themes_affected": themes_affected,
        "keys_affected": keys_affected,
        "shared_across_all_themes": len(themes_affected) == len(THEMES),
        "models": models,
        "authoring_environment": blender_compat.provenance(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"[Opus5D3Audit] {len(affected)}/{len(models)} affected; "
        f"themes {themes_affected or 'none'}; keys {keys_affected or 'none'} "
        f"-> {output}"
    )


if __name__ == "__main__":
    main()
