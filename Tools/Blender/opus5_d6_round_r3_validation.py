"""Phase M2k3: Round on the R2 lineage, which is where R3 has to start.

Alignment 124.2. M2k2 gave Round the generic meter brush-up - a boss, a
counterweight and a zone band added to the shipped dial. Alignment 76.2 says
Round R3 continues R2's `brush_up_meter_round` rebuild instead, which deletes
the solid twelve-sided bezel and the flat dial and puts back a sunken dial pan,
a stepped bezel ring, an inner retainer, re-seated ticks, a dial arc and a
tapered needle whose counterweight is part of the needle. Those are different
models, so M2k2's Round numbers do not describe R3.

This reproduces the R2 rebuild from the production baseline - the frozen R2
Blend is read for its hashes only, never edited - and asks the question that
matters: after that rebuild, is D-6 still there? The answer decides whether any
depth or thickness correction is needed at all, and nothing is added
speculatively: no generic boss, no zone band, no thin-and-shift unless the
measurement calls for one.

Read-only. No Blend is saved; R2, M2k, M2k1 and M2k2 outputs are untouched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d6_round_r3_validation.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_candidate_build as m2e
import opus5_d5_faithful_slot_selection as m2c
import opus5_d6_bounded_correction as m2k1
import opus5_d6_repair_decision as m2k


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d6_round_r3_validation.json"
PREFIX = "d6_round_r3"
KEY = "MeterRound"
ROOT = "PF_Visual_MeterRound_KineticSafety_V6"
FROZEN_R2 = "BL_MeterRound_KineticSafety_V6_Opus5_R2_Retopo.blend"
R2_REPORT = "MeterRound_KineticSafety_V6_Opus5_R2.json"

ENVELOPE_M = m2k1.ENVELOPE_DEPTH_M[KEY]
BUDGET = 5000
POSES = m2k.POSES
KEY_POSES = m2k.KEY_POSES
VIEWS = m2k.VIEWS


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def theme_dir(project_root):
    return project_root / "ArtSource/Blender/BrushUp/Opus5" / m2k.THEME


def rebuild_r2(project_root):
    """R2's own builder, run on the production baseline."""
    path, root = m2k.open_production(project_root, KEY)
    materials = pilot.materials_by_role()
    result = pilot.brush_up_meter_round(root, materials)
    bpy.context.view_layer.update()
    return path, root, result


def triangles_by_object(root):
    out = {}
    for obj in pilot.meshes_under(root):
        if obj.hide_render:
            continue
        obj.data.calc_loop_triangles()
        out[obj.name] = len(obj.data.loop_triangles)
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def compare_to_r2(counts, r2_report):
    expected = r2_report["triangles_by_object_after"]
    missing = sorted(set(expected) - set(counts))
    extra = sorted(set(counts) - set(expected))
    differing = {
        name: [expected[name], counts[name]]
        for name in sorted(set(expected) & set(counts))
        if expected[name] != counts[name]
    }
    total = sum(counts.values())
    return {
        "r2_total_triangles": r2_report["triangles"],
        "rebuilt_total_triangles": total,
        "missing_objects": missing,
        "extra_objects": extra,
        "differing_counts": differing,
        "matches_r2": not missing and not extra and not differing,
    }


def classify(mover, static):
    if "needle" in mover and "boss" in static:
        return "intended: the needle turning in its bearing boss"
    if "needle" in mover and "hub" in static:
        return "intended: needle on its hub"
    if "needle" in mover and "tick" in static:
        return "known D-3 endpoint tick"
    if "needle" in mover and "polygon_bezel" in static:
        return "D-9 blade tangent (closed, alignment 92.1)"
    return "new"


def audit(root):
    pivot = bpy.data.objects["needle_pivot"]
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    statics = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name not in m2e.m2d.hierarchy(obj)
    ]
    contacts = m2k.sweep_contacts(pivot, movable, statics, POSES)
    classified = {}
    for label, entry in contacts.items():
        if entry["clear"]:
            continue
        mover, static = label.split(" x ")
        classified[label] = {**entry, "classification": classify(mover, static)}
    return (
        [obj.name for obj in movable],
        [obj.name for obj in statics],
        classified,
        sorted(
            label
            for label, entry in classified.items()
            if entry["classification"] == "new"
        ),
    )


def render_state(project_root, label, opener):
    directory = theme_dir(project_root) / "review"
    directory.mkdir(parents=True, exist_ok=True)
    import opus5_brushup_kinetic_review as review

    root = opener()
    pivot = bpy.data.objects["needle_pivot"]
    centre = pivot.matrix_world.translation.copy()
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render
        for corner in obj.bound_box
    ]
    span = max(
        max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)
    )
    written = {}
    for pose_label, degrees in KEY_POSES:
        pivot.rotation_euler[1] = math.radians(degrees)
        bpy.context.view_layer.update()
        for view_name, view in VIEWS.items():
            review.configure_scene()
            scale = span * 0.85
            rig = {"light_scale": scale, "energy_scale": (scale / 0.17) ** 2}
            target = directory / f"{PREFIX}_{label}_{pose_label}_{view_name}.png"
            review.shot(
                rig, (centre.x, centre.y, centre.z), span * 2.3,
                (view["azimuth"], view["elevation"]), 58.0, target,
            )
            labelled = target.with_name(target.stem + "_labelled.png")
            m2c.label_copy(
                target, labelled,
                [f"ROUND {label}".upper()[:36], f"{pose_label} {view_name}".upper()],
            )
            written[f"{pose_label}/{view_name}"] = {
                "unlabelled": str(target.relative_to(project_root)),
                "labelled": str(labelled.relative_to(project_root)),
            }
    pivot.rotation_euler[1] = 0.0
    bpy.context.view_layer.update()
    return written


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)

    production = m2k.production_blend(project_root, KEY)
    frozen = theme_dir(project_root) / FROZEN_R2
    r2_report_path = theme_dir(project_root) / "reports" / R2_REPORT
    r2_report = json.loads(r2_report_path.read_text())

    started = time.perf_counter()
    path, root, result = rebuild_r2(project_root)
    pivot = bpy.data.objects["needle_pivot"]
    centre = pivot.matrix_world.translation.copy()
    counts = triangles_by_object(root)
    fidelity = compare_to_r2(counts, r2_report)

    movable, statics, contacts, new_contacts = audit(root)
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render
        for corner in obj.bound_box
    ]
    bounds = {
        "min": [round(min(p[i] for p in points), 6) for i in range(3)],
        "max": [round(max(p[i] for p in points), 6) for i in range(3)],
    }
    envelope = m2k1.envelope_row(KEY, bounds)
    total = sum(counts.values())

    needle = bpy.data.objects["needle"]
    islands = m2e.islands_of(needle.data)
    needle_facts = [m2e.island_facts(needle, island, centre) for island in islands]

    d6_present = bool(new_contacts)
    verdict = {
        "d6_present_after_r2_rebuild": d6_present,
        "correction_needed": d6_present,
        "reason": (
            "the R2 rebuild removes the solid twelve-sided bezel that the "
            "generic counterweight was hitting, and its counterweight is part "
            "of the needle rather than a separate plate, so there is nothing "
            "left for D-6 to act on"
            if not d6_present
            else "new contacts remain; a minimal correction to R2's shape is needed"
        ),
    }

    renders = {}
    if not args.skip_renders:
        renders["production"] = render_state(
            project_root,
            "production",
            lambda: (m2k.open_production(project_root, KEY)[1]),
        )
        renders["frozen_r2"] = render_state(
            project_root,
            "frozen_r2",
            lambda: (m1.open_blend(frozen) or bpy.data.objects[ROOT]),
        )
        renders["proposed_r3"] = render_state(
            project_root,
            "proposed_r3",
            lambda: rebuild_r2(project_root)[1],
        )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2k3",
                "defect": "D-6",
                "model": f"{m2k.THEME}/{KEY}",
                "note": (
                    "Round on the R2 lineage (alignment 124.2). The rebuild is "
                    "reproduced from the production baseline; the frozen R2 "
                    "Blend is hashed, never edited. No Blend is saved."
                ),
                "preflight": gate,
                "sources": {
                    "production": {
                        "path": str(production.relative_to(project_root)),
                        "sha256": m1.digest(production),
                    },
                    "frozen_r2": {
                        "path": str(frozen.relative_to(project_root)),
                        "sha256": m1.digest(frozen),
                        "used_as": "reference only; not opened for editing",
                    },
                    "r2_report": {
                        "path": str(r2_report_path.relative_to(project_root)),
                        "sha256": m1.digest(r2_report_path),
                    },
                },
                "rebuild": {
                    "builder": "opus5_brushup_kinetic_pilot.brush_up_meter_round",
                    "result": result,
                    "generic_parts_added": [
                        name
                        for name in ("needle_boss", "needle_counterweight", "zone_band")
                        if any(name in obj for obj in counts)
                    ],
                },
                "fidelity_to_r2": fidelity,
                "triangles_by_object": counts,
                "triangles": total,
                "triangle_budget": BUDGET,
                "within_budget": total <= BUDGET,
                "pivot_world": [round(v, 6) for v in centre],
                "needle_components": needle_facts,
                "bounds": bounds,
                "envelope": envelope,
                "motion_contract": {
                    "pivot": "needle_pivot",
                    "axis": [0.0, 1.0, 0.0],
                    "sweep_deg": [-55.0, 55.0],
                    "poses": len(POSES),
                },
                "movable_meshes": movable,
                "static_meshes": statics,
                "contacts": contacts,
                "new_contacts": new_contacts,
                "verdict": verdict,
                "renders": renders,
                "pass": (
                    not new_contacts
                    and envelope["within_envelope"]
                    and total <= BUDGET
                    and fidelity["matches_r2"]
                ),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"[Opus5RoundR3] triangles {total}/{BUDGET}, matches R2 "
        f"{fidelity['matches_r2']}, new {new_contacts}, depth "
        f"{envelope['unity_depth_m']} m margin {envelope['margin_mm']} mm, "
        f"D-6 present {d6_present}"
    )
    print(f"[Opus5RoundR3] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
