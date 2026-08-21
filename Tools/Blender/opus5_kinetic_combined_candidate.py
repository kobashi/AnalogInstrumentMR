"""Combined brush-up + D3 candidate for the Kinetic Safety meters.

Alignment 68.4. MeterRound carries the R2 pilot brush-up and Medium / Large
carry the B2 brush-up; all three also need the D-3 tick retraction. Rather than
leaving two branches off the shipped baseline, the approved brush-up candidate
is the *input* and D-3 is applied on top of it.

The retraction is recomputed on the combined scene rather than replayed. The
brush-up hung a counterweight off the pivot, so the circle the movable island
sweeps is a property of the combined model - measuring it on the shipped needle
alone would be measuring the wrong model.

Output goes to the Opus 5 candidate tree. The shipped blends and the brush-up
candidates are opened read-only and never rewritten.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_kinetic_combined_candidate.py -- \
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
import opus5_brushup_kinetic_review as review
import opus5_brushup_review as brushup_review
import opus5_d3_needle_tick_audit as audit
import opus5_d3_tick_retract_candidate as d3
import opus5_publish as publishing
import opus5_d4_inner_scale_survey as d4


THEME = "KineticSafety"
# The brush-up revision each meter already has approved.
INPUTS = {"MeterRound": "R2", "MeterMedium": "B2", "MeterLarge": "B2"}
REVISION = "D3"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--key", dest="keys", action="append", choices=tuple(INPUTS))
    return parser.parse_args(args)


def under(obj, parent):
    node = obj
    while node is not None:
        if node is parent:
            return True
        node = node.parent
    return False


def run_one(project_root, key):
    input_revision = INPUTS[key]
    combined_revision = f"{input_revision}_{REVISION}"
    source = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / f"BL_{key}_{THEME}_V6_Opus5_{input_revision}_Retopo.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(f"brush-up candidate missing: {source}")
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    review.configure_scene()
    root = bpy.data.objects[f"PF_Visual_{key}_{THEME}_V6"]
    pivot = bpy.data.objects[audit.PIVOT]
    centre = pivot.matrix_world.translation.copy()
    margin = d3.CLEARANCE_MM[key] / 1000.0

    meshes = pilot.meshes_under(root)
    movable = [obj for obj in meshes if under(obj, pivot)]
    ticks = [
        obj
        for obj in meshes
        if d3.TICK_TOKEN in obj.name.lower() and not under(obj, pivot)
    ]
    if not ticks:
        raise RuntimeError(f"{key}: no tick marks")

    # The swept circle belongs to the whole movable island, counterweight
    # included, not to the shipped needle alone.
    swept_radius = max(
        audit.radial(obj.matrix_world @ vertex.co, centre)
        for obj in movable
        for vertex in obj.data.vertices
    )
    required = swept_radius + margin

    before = combined_snapshot(root)
    before_ticks = island_sweep(root, pivot, movable, ticks)

    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    rig = brushup_review.rig_from(root)
    rig = dict(rig, radius=rig["radius"] * 0.92, lens=74.0)
    before_images = d4.render_state(
        root, pivot, rig, f"{key}_{THEME}_{input_revision.lower()}_input",
        output_dir, project_root,
    )

    targets = sorted(
        name
        for name, facts in before_ticks.items()
        if facts["closest_mm"] is not None
        and facts["closest_mm"] < d3.CLEARANCE_MM[key]
    )
    edits = {
        name: d3.retract(bpy.data.objects[name], centre, required)
        for name in targets
    }

    after = combined_snapshot(root)
    after_ticks = island_sweep(root, pivot, movable, ticks)
    after_images = d4.render_state(
        root, pivot, rig, f"{key}_{THEME}_{combined_revision.lower()}",
        output_dir, project_root,
    )

    problems = []
    hits = sorted(name for name, f in after_ticks.items() if f["intersects"])
    if hits:
        problems.append(f"tick contact remains: {hits}")
    short = sorted(
        (name, f["closest_mm"])
        for name, f in after_ticks.items()
        if f["closest_mm"] is not None
        and f["closest_mm"] < d3.CLEARANCE_MM[key] - 1e-6
    )
    if short:
        problems.append(f"below the {d3.CLEARANCE_MM[key]} mm target: {short}")
    for field in ("meshes", "triangles_by_object", "vertices_by_object", "bounds",
                  "hierarchy", "material_roles", "root_properties"):
        if before[field] != after[field]:
            problems.append(f"{field} changed")
    problems.extend(pilot.forbidden_datablocks())
    stat_after = source.stat()
    if (stat_before.st_mtime_ns, stat_before.st_size) != (
        stat_after.st_mtime_ns,
        stat_after.st_size,
    ):
        problems.append("input candidate changed on disk")

    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME
    blend = (
        candidate_dir
        / f"BL_{key}_{THEME}_V6_Opus5_{combined_revision}_Retopo.blend"
    )
    report_path = (
        candidate_dir / "reports"
        / f"{key}_{THEME}_V6_Opus5_{combined_revision}.json"
    )
    report = {
        "model": f"{THEME}/{key}",
        "revision": combined_revision,
        "included_revisions": [input_revision, REVISION],
        "input_blend": str(source.relative_to(project_root)),
        "input_is_the_approved_brushup_candidate": True,
        "candidate_blend": str(blend.relative_to(project_root)),
        "clearance_target_mm": d3.CLEARANCE_MM[key],
        "swept_radius_from_movable_island": round(swept_radius, 6),
        "required_inner_radius": round(required, 6),
        "marks_retracted": targets,
        "edits": edits,
        "tick_clearance": {"before": before_ticks, "after": after_ticks},
        "unchanged": {
            field: before[field] == after[field]
            for field in (
                "meshes", "triangles_by_object", "vertices_by_object",
                "bounds", "hierarchy", "material_roles", "root_properties",
            )
        },
        "bounds": after["bounds"],
        "images_input": before_images,
        "images_combined": after_images,
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
        raise RuntimeError(f"{THEME}/{key}: " + "; ".join(problems))

    worst = min(
        (f["closest_mm"] for f in after_ticks.values() if f["closest_mm"]),
        default=None,
    )
    print(
        f"[Opus5KineticCombined] {THEME}/{key} ({combined_revision}): "
        f"swept r {swept_radius:.4f}, retracted {len(targets)} ticks, "
        f"clearance {worst} mm (target {d3.CLEARANCE_MM[key]}), contacts 0, "
        f"bounds unchanged {report['unchanged']['bounds']}"
    )
    return report


def combined_snapshot(root):
    meshes = pilot.meshes_under(root)
    return {
        "meshes": sorted(obj.name for obj in meshes),
        "triangles_by_object": {
            obj.name: len(obj.data.polygons)
            for obj in sorted(meshes, key=lambda item: item.name)
        },
        "vertices_by_object": {
            obj.name: len(obj.data.vertices)
            for obj in sorted(meshes, key=lambda item: item.name)
        },
        "bounds": pilot.world_bounds(meshes),
        "hierarchy": {
            obj.name: (obj.parent.name if obj.parent else None)
            for obj in sorted(root.children_recursive, key=lambda item: item.name)
        },
        "material_roles": pilot.material_role_summary(meshes),
        "root_properties": {
            key: root[key] for key in sorted(root.keys()) if not key.startswith("_")
        },
    }


def island_sweep(root, pivot, movable, marks, steps=44):
    """Closest approach between the whole movable island and each mark."""
    from mathutils.bvhtree import BVHTree

    mark_trees = {obj.name: pilot.bvh_for(obj) for obj in marks}
    facts = {obj.name: {"intersects": False, "closest_mm": None} for obj in marks}
    base = pivot.rotation_euler.copy()
    low, high = audit.SWEEP
    try:
        for index in range(steps + 1):
            angle = low + (high - low) * index / steps
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            island = [pilot.bvh_for(obj) for obj in movable]
            nearest = [
                BVHTree.FromPolygons(
                    [tuple(v) for v in vertices], polygons, all_triangles=True
                )
                for _, vertices, polygons in island
            ]
            for obj in marks:
                entry = facts[obj.name]
                other, other_vertices, other_polygons = mark_trees[obj.name]
                hit = False
                for tree, vertices, polygons in island:
                    for mine, theirs in tree.overlap(other):
                        if pilot.triangle_contact_points(
                            [vertices[i] for i in polygons[mine]],
                            [other_vertices[i] for i in other_polygons[theirs]],
                        ):
                            hit = True
                            break
                    if hit:
                        break
                if hit:
                    entry["intersects"] = True
                    entry["closest_mm"] = 0.0
                    continue
                if entry["closest_mm"] == 0.0:
                    continue
                for tree in nearest:
                    distances = [
                        distance
                        for _, _, _, distance in (
                            tree.find_nearest(v) for v in other_vertices
                        )
                        if distance is not None
                    ]
                    if not distances:
                        continue
                    closest = round(min(distances) * 1000.0, 4)
                    if entry["closest_mm"] is None or closest < entry["closest_mm"]:
                        entry["closest_mm"] = closest
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return facts


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    reports = [run_one(project_root, key) for key in (args.keys or INPUTS)]
    summary = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5/kinetic_combined_summary.json"
    )
    summary.write_text(
        json.dumps(
            {
                "theme": THEME,
                "note": (
                    "D-3 applied on top of each approved brush-up candidate "
                    "(alignment 68.4). The swept radius is measured on the "
                    "combined movable island, counterweight included."
                ),
                "models": {
                    report["model"]: {
                        "included_revisions": report["included_revisions"],
                        "candidate_blend": report["candidate_blend"],
                        "marks_retracted": report["marks_retracted"],
                        "swept_radius": report["swept_radius_from_movable_island"],
                        "unchanged": report["unchanged"],
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
    print(f"[Opus5KineticCombined] summary -> {summary.relative_to(project_root)}")


if __name__ == "__main__":
    main()
