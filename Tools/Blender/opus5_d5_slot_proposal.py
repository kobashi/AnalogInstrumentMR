"""D-5: open the ring only where the shaft sweeps, and measure what it costs.

Alignment 70.3. Enlarging the bore uniformly, necking the shaft, and moving the
ring bodily all failed - the first two never reach zero, the third reaches zero
only by taking the ring off the ball it retains. What none of them tried is that
the shaft does not cross the whole ring: rotating about X, its projection into
the plate plane stays near +Z, so it only ever crosses one narrow sector.

So the ring is rebuilt as a closed C-shaped sector that leaves that wedge open
and keeps material everywhere else, and the slot's half-angle is swept. Both
numbers that matter are measured at each width: whether the shaft still touches,
and how much of the ball's retaining overlap survives.

The replacement is a closed solid rather than a ring with faces deleted, because
the occupancy test is a point-in-mesh test and an open shell would answer it
wrongly.

Design-only: everything is built on throwaway in-memory geometry and no blend is
saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_slot_proposal.py -- \
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
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import opus5_brushup_review as brushup_review
import opus5_d5_option_sweep as sweep
import opus5_joint_contact_section as section


THEMES = sweep.THEMES
KEY = sweep.KEY
SLOT_HALF_ANGLES = (12.0, 18.0, 24.0, 30.0, 36.0)
SEGMENTS = 22
VERIFY_STEPS = 26
POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))
VIEWS = {"front": (0.0, 8.0), "oblique": (36.0, 26.0)}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append", choices=THEMES)
    return parser.parse_args(args)


def slotted_ring(name, inner, outer, y_back, y_front, half_angle, material):
    """The ring minus a wedge centred on +Z, as one closed solid.

    `arc_band` angles start at +Z and rotate toward +X, which is the same
    convention the shaft's projection follows, so the wedge to leave open is
    simply the sector around 0 degrees.
    """
    return brushup.arc_band(
        name,
        inner,
        outer,
        half_angle,
        360.0 - half_angle,
        y_back,
        y_front,
        material,
        segments=SEGMENTS,
    )


def replace_ring(scene, half_angle, inner, outer, ring_y):
    old = scene["ring"]
    material = old.data.materials[0] if old.data.materials else None
    parent = old.parent
    bpy.data.objects.remove(old, do_unlink=True)
    ring = slotted_ring(
        "toggle_ring_slotted", inner, outer, ring_y[0], ring_y[1], half_angle, material
    )
    ring.parent = parent
    bpy.context.view_layer.update()
    scene["ring"] = ring
    return ring


def render_states(scene, project_root, theme, tag, output_dir):
    review.configure_scene()
    rig = brushup_review.rig_from(scene["root"])
    rig = dict(rig, radius=rig["radius"] * 0.85, lens=76.0)
    pivot = scene["pivot"]
    base = pivot.rotation_euler.copy()
    images = {}
    try:
        for pose_name, angle in POSES:
            posed = base.copy()
            posed[0] = base[0] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            for view_name, view in VIEWS.items():
                path = output_dir / f"{KEY}_{theme}_d5_{tag}_{view_name}_{pose_name}.png"
                review.shot(
                    rig, rig["focus"], rig["radius"], view, rig["lens"], path
                )
                images[f"{view_name}_{pose_name}"] = str(
                    path.relative_to(project_root)
                )
            path = output_dir / f"{KEY}_{theme}_d5_{tag}_section_{pose_name}.png"
            section.section_shot({}, rig["focus"], 0.0, 0.075, path)
            images[f"section_{pose_name}"] = str(path.relative_to(project_root))
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return images


def survey_one(project_root, theme):
    scene = sweep.prepare(project_root, theme)
    ring_points = [
        scene["ring"].matrix_world @ v.co for v in scene["ring"].data.vertices
    ]
    inner = min(sweep.radial(p, scene["centre"]) for p in ring_points)
    outer = max(sweep.radial(p, scene["centre"]) for p in ring_points)
    ring_y = [min(p.y for p in ring_points), max(p.y for p in ring_points)]
    baseline_triangles = len(scene["ring"].data.polygons)
    baseline_bounds = pilot.world_bounds(pilot.meshes_under(scene["root"]))
    baseline = {
        "shaft": sweep.measure(scene, VERIFY_STEPS),
        "joint_occupied_fraction": (
            section.occupied_volume(scene["ring"], [scene["joint"]]) or {}
        ).get("occupied_fraction")
        if scene["joint"]
        else None,
        "ring_triangles": baseline_triangles,
        "ring_angular_coverage_deg": 360.0,
    }

    output_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_images = render_states(
        scene, project_root, theme, "axle_removed", output_dir
    )

    trials = {}
    best = None
    for half_angle in SLOT_HALF_ANGLES:
        trial_scene = sweep.prepare(project_root, theme)
        ring = replace_ring(trial_scene, half_angle, inner, outer, ring_y)
        shaft = sweep.measure(trial_scene, VERIFY_STEPS)
        joint_volume = (
            section.occupied_volume(ring, [trial_scene["joint"]])
            if trial_scene["joint"]
            else None
        )
        entry = {
            "slot_half_angle_deg": half_angle,
            "slot_total_angle_deg": half_angle * 2.0,
            "ring_angular_coverage_deg": round(360.0 - half_angle * 2.0, 3),
            "ring_triangles": len(ring.data.polygons),
            "shaft_contact": shaft["shaft_contact"],
            "ring_occupied_fraction": shaft["ring_occupied_fraction"],
            "joint_occupied_fraction": (joint_volume or {}).get("occupied_fraction"),
            "bounds_unchanged": pilot.world_bounds(
                pilot.meshes_under(trial_scene["root"])
            )
            == baseline_bounds,
        }
        trials[f"half_{half_angle:g}deg"] = entry
        clean = (
            entry["shaft_contact"]["samples_with_contact"] == 0
            and (entry["ring_occupied_fraction"] or 0.0) == 0.0
        )
        if clean and best is None:
            best = entry
            best_images = render_states(
                trial_scene, project_root, theme, f"slot_{half_angle:g}deg", output_dir
            )
            entry["images"] = best_images

    return {
        "theme": theme,
        "source": str(scene["source"].relative_to(project_root)),
        "saved_anything": False,
        "common_condition": "axle component removed (alignment 66.3 option B)",
        "ring_geometry": {
            "inner_radius": round(inner, 6),
            "outer_radius": round(outer, 6),
            "y": [round(v, 6) for v in ring_y],
            "slot_depth_is_full_ring_thickness": True,
            "slot_width_mm": round((outer - inner) * 1000.0, 3),
        },
        "baseline_axle_removed": baseline,
        "baseline_images": baseline_images,
        "slot_trials": trials,
        "smallest_clean_slot": best,
        "verify_sweep_samples": VERIFY_STEPS + 1,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    entries = [survey_one(project_root, theme) for theme in (args.themes or THEMES)]
    for entry in entries:
        best = entry["smallest_clean_slot"]
        print(
            f"[Opus5D5Slot] {entry['theme']}: baseline shaft occupied "
            f"{entry['baseline_axle_removed']['shaft']['ring_occupied_fraction']}, "
            f"joint {entry['baseline_axle_removed']['joint_occupied_fraction']}; "
            + (
                f"clean at +-{best['slot_half_angle_deg']} deg "
                f"(coverage {best['ring_angular_coverage_deg']} deg, "
                f"joint {best['joint_occupied_fraction']}, "
                f"ring tris {best['ring_triangles']})"
                if best
                else "no slot width reached zero"
            )
        )
    output = project_root / "ArtSource/Blender/BrushUp/Opus5/d5_slot_proposal.json"
    output.write_text(
        json.dumps(
            {
                "defect": "D-5",
                "note": (
                    "Design-only (alignment 70.3). The ring is rebuilt as a "
                    "closed C-shaped sector on throwaway geometry; no blend is "
                    "saved. The replacement is closed rather than a ring with "
                    "faces deleted so the point-in-mesh occupancy test stays "
                    "valid."
                ),
                "slot_half_angles_tried": list(SLOT_HALF_ANGLES),
                "themes": {entry["theme"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D5Slot] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
