"""Why do the joined-needle and split-component sweeps disagree?

Alignment 82.2. On MeterLarge the component sweep reported the blade touching
`kinetic_polygon_bezel` out to 118.7 mm and outside the bearing, while the
joined-needle sweep of the same source over the same poses reported only a hub
contact at 29.7-30.2 mm, inside it. Both cannot be true, and until they agree
no motion gate built on either is worth anything.

So both are run here in one pass, on one scene, at identical poses and with
identical world transforms, and every contact is kept with the triangle indices
that produced it. Whichever way the discrepancy falls, the triangle indices say
where to look.

Read-only: components are split onto throwaway copies and no blend is saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_joined_vs_component_audit.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_d5_toggle_axle_proposal as components


THEME = "KineticSafety"
KEYS = ("MeterRound", "MeterMedium", "MeterLarge")
PLATE = "kinetic_polygon_bezel"
SWEEP = (-55.0, 55.0)
STEPS = 22


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--key", dest="keys", action="append", choices=KEYS)
    return parser.parse_args(args)


def radial(point, centre):
    return math.hypot(point.x - centre.x, point.z - centre.z)


def measure(pivot, movers, static_obj, centre, bearing, steps=STEPS):
    """Contact per mover, keeping the triangle indices that produced it."""
    static_tree, static_vertices, static_polygons = pilot.bvh_for(static_obj)
    base = pivot.rotation_euler.copy()
    low, high = SWEEP
    facts = {}
    try:
        for index in range(steps + 1):
            angle = low + (high - low) * index / steps
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            for mover in movers:
                tree, vertices, polygons = pilot.bvh_for(mover)
                for mine, theirs in tree.overlap(static_tree):
                    points = pilot.triangle_contact_points(
                        [vertices[i] for i in polygons[mine]],
                        [static_vertices[i] for i in static_polygons[theirs]],
                    )
                    if not points:
                        continue
                    entry = facts.setdefault(
                        mover.name,
                        {
                            "poses": set(),
                            "radius_min": None,
                            "radius_max": None,
                            "outside_bearing": False,
                            "mover_triangles": set(),
                            "static_triangles": set(),
                        },
                    )
                    entry["poses"].add(round(angle, 3))
                    entry["mover_triangles"].add(mine)
                    entry["static_triangles"].add(theirs)
                    for point in points:
                        radius = radial(point, centre)
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
                        if (point - centre).length > bearing:
                            entry["outside_bearing"] = True
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    for entry in facts.values():
        entry["pose_count"] = len(entry.pop("poses"))
        entry["mover_triangle_count"] = len(entry["mover_triangles"])
        entry["static_triangles"] = sorted(entry.pop("static_triangles"))[:12]
        entry["mover_triangles"] = sorted(entry.pop("mover_triangles"))[:12]
        for field in ("radius_min", "radius_max"):
            if entry[field] is not None:
                entry[field] = round(entry[field], 6)
    return facts


def survey_one(project_root, key):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / THEME
        / f"BL_{key}_{THEME}_V6_Retopo.blend"
    )
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{key}_{THEME}_V6"]
    pivot = bpy.data.objects["needle_pivot"]
    needle = bpy.data.objects["needle"]
    plate = bpy.data.objects[PLATE]
    centre = pivot.matrix_world.translation.copy()
    hub = max(
        abs((needle.matrix_world @ vertex.co).x - centre.x)
        for vertex in needle.data.vertices
    )
    bearing = hub * 1.7

    joined = measure(pivot, [needle], plate, centre, bearing)

    # Split *after* the joined measurement, in the same scene, so both use the
    # same plate object and the same pivot.
    pieces = components.components_of(needle)
    for piece in pieces:
        pilot.parent_keep_world(piece, pivot)
    bpy.context.view_layer.update()
    split = measure(pivot, pieces, plate, centre, bearing)

    joined_entry = joined.get(needle.name)
    union = {
        "radius_min": min(
            (e["radius_min"] for e in split.values() if e["radius_min"] is not None),
            default=None,
        ),
        "radius_max": max(
            (e["radius_max"] for e in split.values() if e["radius_max"] is not None),
            default=None,
        ),
        "outside_bearing": any(e["outside_bearing"] for e in split.values()),
        "mover_triangle_count": sum(
            e["mover_triangle_count"] for e in split.values()
        ),
    }
    agree = bool(
        joined_entry
        and union["radius_min"] is not None
        and abs(joined_entry["radius_min"] - union["radius_min"]) < 1e-6
        and abs(joined_entry["radius_max"] - union["radius_max"]) < 1e-6
        and joined_entry["outside_bearing"] == union["outside_bearing"]
    )
    return {
        "model": f"{THEME}/{key}",
        "source": str(source.relative_to(project_root)),
        "saved_anything": False,
        "bearing_radius": round(bearing, 6),
        "needle_triangles": len(needle.data.polygons),
        "component_triangles": {
            piece.name: len(piece.data.polygons) for piece in pieces
        },
        "joined": joined,
        "components": split,
        "component_union": union,
        "agree": agree,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    entries = [survey_one(project_root, key) for key in (args.keys or KEYS)]
    for entry in entries:
        joined = entry["joined"].get("needle")
        union = entry["component_union"]
        print(
            f"[Opus5JoinVsSplit] {entry['model']}: joined "
            f"{(joined or {}).get('radius_min')}..{(joined or {}).get('radius_max')} "
            f"outside={(joined or {}).get('outside_bearing')} | components "
            f"{union['radius_min']}..{union['radius_max']} "
            f"outside={union['outside_bearing']} | agree={entry['agree']}"
        )
    output = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5/joined_vs_component_audit.json"
    )
    output.write_text(
        json.dumps(
            {
                "note": (
                    "Read-only (alignment 82.2). Both sweeps run on one scene "
                    "at identical poses; triangle indices are kept so a "
                    "disagreement can be located."
                ),
                "models": {entry["model"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5JoinVsSplit] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
