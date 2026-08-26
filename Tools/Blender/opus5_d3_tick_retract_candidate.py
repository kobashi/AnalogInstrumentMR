"""D-3 fix candidate: retract the endpoint ticks out of the needle's sweep.

Alignment 59.1. The two dial marks nearest the sweep stops dip inside the circle
the needle sweeps, so at minimum and maximum - the two poses an instrument is
most often read at - the needle cuts through them. The fix moves those marks'
inner ends outward; the needle's length, its pivot and the +-55 degree sweep are
all left alone, because the needle's length is what the instrument says.

Two things make this safe to do to shipped meshes:

* only vertices inside the required radius move, and they move radially, so the
  tick keeps its angle, its width, its outer end and its triangle count;
* the required radius is measured per model rather than tabulated, and the
  clearance target scales 0.7 / 1.4 / 2.1 mm across Round / Medium / Large -
  the clearances Forge Brass, the one theme with no contact at all, already
  achieves (alignment 59.1).

Every model is re-swept after the edit and the run fails unless the contact is
gone and the measured clearance meets the target. Output goes to the Opus 5
candidate tree; the shipped blend is never written.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_tick_retract_candidate.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_publish as publishing
import opus5_d3_needle_tick_audit as audit


REVISION = "D3"

# Alignment 59.1: proportional to the model, matching what Forge Brass - the
# theme with no contact anywhere - already measures at each scale.
CLEARANCE_MM = {"MeterRound": 0.7, "MeterMedium": 1.4, "MeterLarge": 2.1}

# Forge Brass is clear at all three scales and is deliberately not touched.
TARGETS = tuple(
    f"{theme}/{key}"
    for theme in ("KineticSafety", "OrbitalAnalog")
    for key in ("MeterRound", "MeterMedium", "MeterLarge")
)

# D-3 is the tick ring. Orbital's inner scale rings are inside the sweep for a
# different reason and on a different axis; they are D-4 and are left alone.
TICK_TOKEN = "tick"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append", choices=TARGETS)
    parser.add_argument("--revision", default=REVISION)
    return parser.parse_args(args)


def sweep_contact(root, pivot, needle, marks, steps=44):
    """Exact contact and closest approach for each mark over the whole sweep."""
    trees = {mark.name: pilot.bvh_for(mark) for mark in marks}
    facts = {
        mark.name: {"intersects": False, "samples": 0, "closest_mm": None}
        for mark in marks
    }
    base = pivot.rotation_euler.copy()
    low, high = audit.SWEEP
    try:
        for index in range(steps + 1):
            angle = low + (high - low) * index / steps
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            needle_tree, needle_vertices, needle_polygons = pilot.bvh_for(needle)
            nearest = BVHTree.FromPolygons(
                [tuple(vertex) for vertex in needle_vertices],
                needle_polygons,
                all_triangles=True,
            )
            for mark in marks:
                entry = facts[mark.name]
                other, other_vertices, other_polygons = trees[mark.name]
                hit = False
                for mine, theirs in needle_tree.overlap(other):
                    first = [needle_vertices[i] for i in needle_polygons[mine]]
                    second = [other_vertices[i] for i in other_polygons[theirs]]
                    if pilot.triangle_contact_points(first, second):
                        hit = True
                        break
                if hit:
                    entry["intersects"] = True
                    entry["samples"] += 1
                    entry["closest_mm"] = 0.0
                    continue
                if entry["closest_mm"] == 0.0:
                    continue
                distances = [
                    distance
                    for _, _, _, distance in (
                        nearest.find_nearest(vertex) for vertex in other_vertices
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


def retract(mark, centre, required_radius):
    """Push a mark's inner vertices out to `required_radius`, radially.

    Angle and height are preserved and no vertex is added or removed, so the
    mark keeps its outer end, its width, its orientation and its triangle
    count - it is shortened from the inside, nothing else.
    """
    matrix = mark.matrix_world
    inverse = matrix.inverted()
    moved = 0
    before = []
    after = []
    for vertex in mark.data.vertices:
        world = matrix @ vertex.co
        radius = math.hypot(world.x - centre.x, world.z - centre.z)
        before.append(radius)
        if radius >= required_radius or radius < 1e-9:
            after.append(radius)
            continue
        scale = required_radius / radius
        world.x = centre.x + (world.x - centre.x) * scale
        world.z = centre.z + (world.z - centre.z) * scale
        vertex.co = inverse @ world
        after.append(required_radius)
        moved += 1
    mark.data.update()
    return {
        "vertices_moved": moved,
        "inner_radius_before": round(min(before), 6),
        "inner_radius_after": round(min(after), 6),
        "outer_radius_before": round(max(before), 6),
        "outer_radius_after": round(max(after), 6),
    }


def run_one(project_root, label, revision):
    theme, key = label.split("/")
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{key}_{theme}_V6_Retopo.blend"
    )
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{key}_{theme}_V6"]
    pivot = bpy.data.objects[audit.PIVOT]
    needle = bpy.data.objects[audit.NEEDLE]
    centre = pivot.matrix_world.translation.copy()
    margin = CLEARANCE_MM[key] / 1000.0

    ticks = [
        obj
        for obj in pilot.meshes_under(root)
        if TICK_TOKEN in obj.name.lower() and not audit._under(obj, pivot)
    ]
    if not ticks:
        raise RuntimeError(f"{label}: no tick marks")

    swept_radius = max(
        audit.radial(needle.matrix_world @ vertex.co, centre)
        for vertex in needle.data.vertices
    )
    required = swept_radius + margin

    before = sweep_contact(root, pivot, needle, ticks)
    # Retract exactly the marks that do not already meet the target, whether
    # they intersect (0.0 mm) or merely graze it. Orbital Round is the second
    # case and is included on purpose (alignment 59.1).
    targets = sorted(
        name
        for name, facts in before.items()
        if facts["closest_mm"] is not None and facts["closest_mm"] < CLEARANCE_MM[key]
    )
    baseline_triangles = {
        obj.name: len(obj.data.polygons) for obj in pilot.meshes_under(root)
    }
    baseline_vertices = {
        obj.name: len(obj.data.vertices) for obj in pilot.meshes_under(root)
    }
    baseline_bounds = pilot.world_bounds(pilot.meshes_under(root))

    edits = {}
    for name in targets:
        edits[name] = retract(bpy.data.objects[name], centre, required)

    after = sweep_contact(root, pivot, needle, ticks)

    problems = []
    still_hitting = sorted(
        name for name, facts in after.items() if facts["intersects"]
    )
    if still_hitting:
        problems.append(f"still intersecting after retraction: {still_hitting}")
    short = sorted(
        (name, facts["closest_mm"])
        for name, facts in after.items()
        if facts["closest_mm"] is not None
        and facts["closest_mm"] < CLEARANCE_MM[key] - 1e-6
    )
    if short:
        problems.append(f"below the {CLEARANCE_MM[key]} mm target: {short}")

    meshes = pilot.meshes_under(root)
    for obj in meshes:
        if len(obj.data.polygons) != baseline_triangles[obj.name]:
            problems.append(f"triangle count changed: {obj.name}")
        if len(obj.data.vertices) != baseline_vertices[obj.name]:
            problems.append(f"vertex count changed: {obj.name}")
    untouched = sorted(set(baseline_triangles) - set(targets))
    if audit.NEEDLE in targets:
        problems.append("the needle was edited; only ticks may move")
    bounds = pilot.world_bounds(meshes)
    if bounds != baseline_bounds:
        problems.append(f"bounds moved: {baseline_bounds} -> {bounds}")
    problems.extend(pilot.forbidden_datablocks())

    stat_after = source.stat()
    if (stat_before.st_mtime_ns, stat_before.st_size) != (
        stat_after.st_mtime_ns,
        stat_after.st_size,
    ):
        problems.append("source blend changed on disk")

    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme
    blend = candidate_dir / f"BL_{key}_{theme}_V6_Opus5_{revision}_Retopo.blend"
    report_path = (
        candidate_dir / "reports" / f"{key}_{theme}_V6_Opus5_{revision}.json"
    )
    report = {
        "defect": "D-3",
        "model": label,
        "revision": revision,
        "source_blend": str(source.relative_to(project_root)),
        "candidate_blend": str(blend.relative_to(project_root)),
        "clearance_target_mm": CLEARANCE_MM[key],
        "needle_swept_radius": round(swept_radius, 6),
        "required_inner_radius": round(required, 6),
        "needle_unchanged": True,
        "pivot_unchanged": True,
        "sweep_degrees": list(audit.SWEEP),
        "marks_retracted": targets,
        "marks_untouched": untouched,
        "edits": edits,
        "contact_before": before,
        "contact_after": after,
        "bounds": bounds,
        "problems": problems,
        "authoring_environment": blender_compat.provenance(),
    }
    # Alignment 73.4: never replace a published revision, never leave a report
    # behind for a run that failed, and publish blend and report together.
    report["publish"] = publishing.publish(
        blend,
        report_path,
        report,
        problems,
        save_blend=pilot.save_blend,
        reopen_blend=lambda path: bpy.ops.wm.open_mainfile(
            filepath=str(path), load_ui=False
        ),
    )
    if problems:
        raise RuntimeError(f"{label}: " + "; ".join(problems))

    worst = min(
        (facts["closest_mm"] for facts in after.values() if facts["closest_mm"]),
        default=None,
    )
    print(
        f"[Opus5D3Fix] {label}: retracted {len(targets)} of {len(ticks)} ticks "
        f"to r >= {required:.4f}, closest now {worst} mm "
        f"(target {CLEARANCE_MM[key]} mm), intersections 0"
    )
    return report


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    models = tuple(args.models) if args.models else TARGETS
    reports = [run_one(project_root, label, args.revision) for label in models]
    summary = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / f"d3_tick_retract_{args.revision.lower()}_summary.json"
    )
    summary.write_text(
        json.dumps(
            {
                "defect": "D-3",
                "revision": args.revision,
                "clearance_target_mm": CLEARANCE_MM,
                "themes_untouched": ["ForgeBrass"],
                "models": {
                    report["model"]: {
                        "marks_retracted": report["marks_retracted"],
                        "required_inner_radius": report["required_inner_radius"],
                        "edits": report["edits"],
                        "intersections_after": sorted(
                            name
                            for name, facts in report["contact_after"].items()
                            if facts["intersects"]
                        ),
                    }
                    for report in reports
                },
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D3Fix] summary -> {summary.relative_to(project_root)}")


if __name__ == "__main__":
    main()
