"""Phase M1b: the coverage Phase M1 left out.

Alignment 92.3. M1 audited D-3 on Medium and Large but not Round, and D-5 only
on Kinetic Safety and only in two of its three states - so "unchanged across
D-3" and "unchanged across D-5" were claims wider than the evidence. This adds
exactly the missing cells, in the same schema, without touching the M1 report.

* MeterRound's D-3 pair, baseline and published D3 candidate, against the
  0.7 mm contract.
* D-5 across all three themes in three states: shipped with the legacy axle,
  the shaft alone after the axle component is removed, and the smallest clean
  slot from the approved design survey - rebuilt in memory, never saved.

For the slot state the ring's sampled occupied fraction is reported alongside
the new two-layer result, because that is the number the slot proposal was
argued on and the two have not been compared before.

Read-only. No Blend is written and no existing report is modified.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_contact_migration_m1b.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_toggle_axle_proposal as splitter
import opus5_joint_contact_section as section


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/contact_migration_m1b.json"
SLOT_SURVEY = "ArtSource/Blender/BrushUp/Opus5/d5_slot_proposal.json"
DELTA_KEYS = ("unchanged", "weakened", "strengthened", "invalidated")


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def round_d3(project_root):
    """The D-3 cell M1 skipped: MeterRound, baseline and D3 candidate."""
    entries = {}
    poses = [-55.0 + 110.0 * index / 22 for index in range(23)]
    for kind, source in (
        (
            "production baseline",
            project_root
            / "ArtSource/Blender/ThemeHardSurfaceV6/KineticSafety"
            / "BL_MeterRound_KineticSafety_V6_Retopo.blend",
        ),
        (
            "D3 candidate",
            project_root
            / "ArtSource/Blender/BrushUp/Opus5/KineticSafety"
            / "BL_MeterRound_KineticSafety_V6_Opus5_D3_Retopo.blend",
        ),
    ):
        if not source.is_file():
            entries[f"KineticSafety/MeterRound [{kind}]"] = {"missing": str(source)}
            continue
        m1.open_blend(source)
        root = bpy.data.objects["PF_Visual_MeterRound_KineticSafety_V6"]
        pivot = bpy.data.objects["needle_pivot"]
        needle = bpy.data.objects["needle"]
        centre = pivot.matrix_world.translation.copy()
        hub = max(
            abs((needle.matrix_world @ vertex.co).x - centre.x)
            for vertex in needle.data.vertices
        )
        endpoints = [
            obj
            for obj in pilot.meshes_under(root)
            if obj.name in ("kinetic_tick_3", "kinetic_tick_9")
        ]
        entries[f"KineticSafety/MeterRound [{kind}]"] = {
            "source": str(source.relative_to(project_root)),
            "sha256": m1.digest(source),
            "kind": kind,
            "poses": {"count": len(poses), "degrees": [poses[0], poses[-1]]},
            "clearance_contract_mm": 0.7,
            "pairs": m1.sweep_pairs(
                pivot, [needle], endpoints, centre, hub * 1.7, poses
            ),
        }
    return entries


def ring_occupancy(ring, movers):
    volume = section.occupied_volume(ring, movers)
    if volume is None:
        return None
    return {
        "occupied_fraction": volume["occupied_fraction"],
        "occupied_volume_mm3": volume["occupied_volume_mm3"],
        "static_volume_mm3": volume["static_volume_mm3"],
        "grid": volume["grid"],
        "cell_mm": volume["cell_mm"],
        "estimate": volume["estimate"],
    }


def toggle_states(project_root, theme, slot_half_angle):
    """D-5 in three states for one theme, all in memory."""
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_Toggle_{theme}_V6_Retopo.blend"
    )
    poses = [56.0 * index / 26 for index in range(27)]
    states = {}

    for kind in ("legacy axle present", "axle component removed", "slot proposal"):
        m1.open_blend(source)
        root = bpy.data.objects[f"PF_Visual_Toggle_{theme}_V6"]
        pivot = bpy.data.objects["switch_pivot"]
        switch = bpy.data.objects["switch"]
        ring = next(
            obj
            for obj in pilot.meshes_under(root)
            if "retaining_ring" in obj.name.lower()
        )
        joint = next(
            (
                obj
                for obj in pilot.meshes_under(root)
                if "hemisphere" in obj.name.lower()
            ),
            None,
        )
        centre = pivot.matrix_world.translation.copy()
        movers = [switch]
        attribution = None

        if kind != "legacy axle present":
            pieces = splitter.components_of(switch)
            for piece in pieces:
                pilot.parent_keep_world(piece, pivot)
            facts = {p.name: splitter.describe(p, centre) for p in pieces}
            axle = min(
                (name for name, f in facts.items() if f["longest_axis"] == "X"),
                key=lambda name: facts[name]["distance_from_pivot_mm"],
            )
            shaft = max(pieces, key=lambda p: facts[p.name]["length_mm"][2])
            grip = next(
                (p for p in pieces if p.name not in (axle, shaft.name)), None
            )
            doomed = bpy.data.objects[axle]
            pieces = [p for p in pieces if p is not doomed]
            bpy.data.objects.remove(doomed, do_unlink=True)
            switch.hide_viewport = True
            bpy.context.view_layer.update()
            movers = pieces
            attribution = {
                "axle_component_removed": axle,
                "shaft_component": shaft.name,
                "grip_component": grip.name if grip else None,
                "component_facts": facts,
            }

        if kind == "slot proposal":
            points = [
                ring.matrix_world @ vertex.co for vertex in ring.data.vertices
            ]
            inner = min(
                math.hypot(p.x - centre.x, p.z - centre.z) for p in points
            )
            outer = max(
                math.hypot(p.x - centre.x, p.z - centre.z) for p in points
            )
            y_low = min(p.y for p in points)
            y_high = max(p.y for p in points)
            material = ring.data.materials[0] if ring.data.materials else None
            parent = ring.parent
            bpy.data.objects.remove(ring, do_unlink=True)
            ring = brushup.arc_band(
                "toggle_ring_slotted",
                inner,
                outer,
                slot_half_angle,
                360.0 - slot_half_angle,
                y_low,
                y_high,
                material,
                segments=22,
                centre_x=centre.x,
                centre_z=centre.z,
            )
            ring.parent = parent
            bpy.context.view_layer.update()

        pairs = m1.sweep_pairs(
            pivot, movers, [ring], centre, 0.026, poses, rotate_axis=0
        )
        states[kind] = {
            "poses": {"count": len(poses), "degrees": [poses[0], poses[-1]]},
            "slot_half_angle_deg": slot_half_angle if kind == "slot proposal" else None,
            "component_attribution": attribution,
            "pairs": pairs,
            "ring_occupied_by_movers": ring_occupancy(ring, movers),
            "ring_occupied_by_joint": ring_occupancy(ring, [joint]) if joint else None,
            "shaft_ring_clear": all(
                entry["verdict"] in ("clear", "tangent_or_within_tolerance")
                for label, entry in pairs.items()
            ),
        }
    return {
        "source": str(source.relative_to(project_root)),
        "sha256": m1.digest(source),
        "states": states,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)

    survey_path = project_root / SLOT_SURVEY
    survey = json.loads(survey_path.read_text())
    slot_angles = {
        theme: (entry.get("smallest_clean_slot") or {}).get("slot_half_angle_deg")
        for theme, entry in survey["themes"].items()
    }

    started = time.perf_counter()
    timings = {}

    begin = time.perf_counter()
    d3 = round_d3(project_root)
    timings["meterround_d3"] = round(time.perf_counter() - begin, 3)
    print(f"[Opus5MigrationM1b] meterround_d3: {timings['meterround_d3']}s")

    d5 = {}
    for theme, angle in slot_angles.items():
        begin = time.perf_counter()
        d5[theme] = toggle_states(project_root, theme, angle)
        timings[f"d5_{theme}"] = round(time.perf_counter() - begin, 3)
        print(
            f"[Opus5MigrationM1b] d5_{theme} (slot +-{angle} deg): "
            f"{timings[f'd5_{theme}']}s"
        )

    deltas = {key: 0 for key in DELTA_KEYS}
    for model in d3.values():
        for entry in model.get("pairs", {}).values():
            deltas[entry["delta"]] += 1
    for theme in d5.values():
        for state in theme["states"].values():
            for entry in state["pairs"].values():
                deltas[entry["delta"]] += 1

    coverage = {
        "d3_models_audited": sorted(d3),
        "d3_models_from_m1": ["KineticSafety/MeterMedium", "KineticSafety/MeterLarge"],
        "d5_themes_audited": sorted(d5),
        "d5_states_per_theme": [
            "legacy axle present",
            "axle component removed",
            "slot proposal",
        ],
    }

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M1b",
                "note": (
                    "Read-only completion of Phase M1 (alignment 92.3). The M1 "
                    "report is not modified; the slot state is rebuilt in "
                    "memory and never saved."
                ),
                "preflight": gate,
                "slot_survey": {
                    "path": SLOT_SURVEY,
                    "sha256": m1.digest(survey_path),
                    "smallest_clean_slot_half_angle_deg": slot_angles,
                },
                "tolerances": {
                    "tangent_m": contact.TANGENT_TOLERANCE_M,
                    "penetration_mm": contact.PENETRATION_TOLERANCE_MM,
                    "boundary_mm": contact.BOUNDARY_TOLERANCE_MM,
                    "broad_phase_m": contact.BROAD_PHASE_EPSILON_M,
                },
                "coverage": coverage,
                "meterround_d3": d3,
                "d5_by_theme": d5,
                "delta_summary": deltas,
                "elapsed_seconds": {
                    **timings,
                    "total": round(time.perf_counter() - started, 3),
                },
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5MigrationM1b] deltas {deltas} -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
