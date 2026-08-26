"""Combined D3 + D4 candidate for the Orbital Analog meters.

Alignment 66.2. The tick retraction (D-3) and the inner-scale depth move (D-4)
touch the same three models, so they are combined into one candidate rather
than left as two branches off the shipped baseline: the approved D3 candidate is
the *input*, and D-4 is applied on top of it.

Both clearances are then re-measured together on the result, because satisfying
each fix separately is not the same as satisfying both at once.

Output goes to the Opus 5 candidate tree. The shipped blends and the D3
candidates are opened read-only and never rewritten.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_d4_combined_candidate.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_review as brushup_review
import opus5_brushup_kinetic_review as review
import opus5_d3_needle_tick_audit as audit
import opus5_d3_tick_retract_candidate as d3
import opus5_publish as publishing
import opus5_d4_inner_scale_survey as d4


THEME = d4.THEME
KEYS = d4.KEYS
REVISION = "D3_D4"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--key", dest="keys", action="append", choices=KEYS)
    parser.add_argument("--revision", default=REVISION)
    return parser.parse_args(args)


def snapshot(root):
    meshes = pilot.meshes_under(root)
    return {
        "meshes": sorted(obj.name for obj in meshes),
        "triangles_by_object": {
            obj.name: len(obj.data.polygons) for obj in sorted(
                meshes, key=lambda item: item.name
            )
        },
        "vertices_by_object": {
            obj.name: len(obj.data.vertices) for obj in sorted(
                meshes, key=lambda item: item.name
            )
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


def run_one(project_root, key, revision):
    source = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / f"BL_{key}_{THEME}_V6_Opus5_D3_Retopo.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(f"D3 candidate missing: {source}")
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    review.configure_scene()
    root = bpy.data.objects[f"PF_Visual_{key}_{THEME}_V6"]
    pivot = bpy.data.objects[audit.PIVOT]
    needle = bpy.data.objects[audit.NEEDLE]
    centre = pivot.matrix_world.translation.copy()
    margin = d4.CLEARANCE_MM[key] / 1000.0

    meshes = pilot.meshes_under(root)
    scales = [obj for obj in meshes if d4.SCALE_TOKEN in obj.name]
    statics = [obj for obj in meshes if obj is not needle and obj not in scales]
    ticks = [obj for obj in meshes if d3.TICK_TOKEN in obj.name.lower()]

    before = snapshot(root)
    swept_radius = max(
        audit.radial(needle.matrix_world @ v.co, centre) for v in needle.data.vertices
    )
    needle_span = d4.extent(needle, centre)

    before_scale_static = d4.pair_contacts(scales, statics + scales)
    before_ticks = d4.sweep_hits(root, pivot, needle, ticks)
    before_scales = d4.sweep_hits(root, pivot, needle, scales)

    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    rig = brushup_review.rig_from(root)
    rig = dict(rig, radius=rig["radius"] * 0.92, lens=74.0)
    before_images = d4.render_state(
        root, pivot, rig, f"{key}_{THEME}_d3_input", output_dir, project_root
    )

    plan = {}
    for obj in scales:
        span = d4.extent(obj, centre)
        if span["radius"][1] < swept_radius * 0.35:
            delta = (needle_span["y"][0] - margin) - span["y"][1]
            placement = "in front of the needle (hub cap)"
        else:
            delta = (needle_span["y"][1] + margin) - span["y"][0]
            placement = "behind the needle"
        plan[obj.name] = {
            "placement": placement,
            "delta_y_mm": round(delta * 1000.0, 4),
            "y_before": span["y"],
            "y_after": [round(span["y"][0] + delta, 6), round(span["y"][1] + delta, 6)],
        }
        d4.shift(obj, delta)

    after = snapshot(root)
    after_scale_static = d4.pair_contacts(scales, statics + scales)
    after_ticks = d4.sweep_hits(root, pivot, needle, ticks)
    after_scales = d4.sweep_hits(root, pivot, needle, scales)
    after_images = d4.render_state(
        root, pivot, rig, f"{key}_{THEME}_d3_d4", output_dir, project_root
    )
    static_diff = d4.diff_contacts(before_scale_static, after_scale_static)

    problems = []
    tick_hits = sorted(n for n, f in after_ticks.items() if f["intersects"])
    if tick_hits:
        problems.append(f"D-3 clearance lost: {tick_hits}")
    tick_short = sorted(
        (n, f["closest_mm"])
        for n, f in after_ticks.items()
        if f["closest_mm"] is not None and f["closest_mm"] < d4.CLEARANCE_MM[key] - 1e-6
    )
    if tick_short:
        problems.append(f"tick clearance below target: {tick_short}")
    scale_hits = sorted(n for n, f in after_scales.items() if f["intersects"])
    if scale_hits:
        problems.append(f"D-4 clearance not met: {scale_hits}")
    scale_short = sorted(
        (n, f["closest_mm"])
        for n, f in after_scales.items()
        if f["closest_mm"] is not None and f["closest_mm"] < d4.CLEARANCE_MM[key] - 1e-6
    )
    if scale_short:
        problems.append(f"inner scale clearance below target: {scale_short}")
    if static_diff["new"]:
        problems.append(f"new static contacts: {static_diff['new']}")
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
        problems.append("D3 candidate changed on disk")

    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME
    blend = candidate_dir / f"BL_{key}_{THEME}_V6_Opus5_{revision}_Retopo.blend"
    report_path = (
        candidate_dir / "reports" / f"{key}_{THEME}_V6_Opus5_{revision}.json"
    )
    report = {
        "model": f"{THEME}/{key}",
        "revision": revision,
        "included_revisions": ["D3", "D4"],
        "input_blend": str(source.relative_to(project_root)),
        "input_is_the_approved_d3_candidate": True,
        "candidate_blend": str(blend.relative_to(project_root)),
        "clearance_target_mm": d4.CLEARANCE_MM[key],
        "needle_swept_radius": round(swept_radius, 6),
        "d4_plan": plan,
        "d3_tick_clearance": {"before": before_ticks, "after": after_ticks},
        "d4_inner_scale_clearance": {"before": before_scales, "after": after_scales},
        "inner_scale_vs_static": {
            "before": before_scale_static,
            "after": after_scale_static,
            "difference": static_diff,
        },
        "unchanged": {
            "triangles_by_object": before["triangles_by_object"] == after["triangles_by_object"],
            "vertices_by_object": before["vertices_by_object"] == after["vertices_by_object"],
            "bounds": before["bounds"] == after["bounds"],
            "hierarchy": before["hierarchy"] == after["hierarchy"],
            "material_roles": before["material_roles"] == after["material_roles"],
            "root_properties": before["root_properties"] == after["root_properties"],
        },
        "bounds": after["bounds"],
        "images_d3_input": before_images,
        "images_d3_d4": after_images,
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

    worst_tick = min(
        (f["closest_mm"] for f in after_ticks.values() if f["closest_mm"]), default=None
    )
    worst_scale = min(
        (f["closest_mm"] for f in after_scales.values() if f["closest_mm"]), default=None
    )
    print(
        f"[Opus5D3D4] {THEME}/{key}: tick clearance {worst_tick} mm, "
        f"inner scale clearance {worst_scale} mm "
        f"(target {d4.CLEARANCE_MM[key]}), new static contacts "
        f"{len(static_diff['new'])}, bounds unchanged {report['unchanged']['bounds']}"
    )
    return report


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    reports = [
        run_one(project_root, key, args.revision) for key in (args.keys or KEYS)
    ]
    summary = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / f"d3_d4_combined_{args.revision.lower()}_summary.json"
    )
    summary.write_text(
        json.dumps(
            {
                "revision": args.revision,
                "included_revisions": ["D3", "D4"],
                "note": (
                    "D-4 applied on top of the approved D3 candidate rather "
                    "than as a second branch off the shipped baseline "
                    "(alignment 66.2)."
                ),
                "models": {
                    report["model"]: {
                        "candidate_blend": report["candidate_blend"],
                        "d4_plan": report["d4_plan"],
                        "unchanged": report["unchanged"],
                        "new_static_contacts": report["inner_scale_vs_static"][
                            "difference"
                        ]["new"],
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
    print(f"[Opus5D3D4] summary -> {summary.relative_to(project_root)}")


if __name__ == "__main__":
    main()
