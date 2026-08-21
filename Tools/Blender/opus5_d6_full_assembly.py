"""Phase M2k2: the same decision, on the whole assembly this time.

Alignment 122.2. M2k and M2k1 built the boss and the counterweight and left the
zone band out, so their "no new contact" covered part of the repair rather than
all of it. This builds all three parts from the production builder's own
formulas, on each model's real `needle_pivot`, and audits the adopted option
over the full sweep.

The zone band is not assumed to exist. The builder skips it when the dial does
not reach far enough to carry it, so the reach, the band's radii and the spec's
own part list are reported per size whether the band is built or not.

Every contact is given a settled classification. `new` is a finding, not a
default: the needle turning in its boss, the counterweight seated on it, the
hub inside the bearing stack, the closed D-9 blade case and the recorded D-3
endpoint ticks are each named.

Adopted, from alignment 122: Round takes `thin_and_shift`, Medium and Large
take `depth 0.7 mm`.

Read-only. No Blend is saved; M2k and M2k1 reports and images are untouched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d6_full_assembly.py -- \
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
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_candidate_build as m2e
import opus5_d5_faithful_slot_selection as m2c
import opus5_d6_bounded_correction as m2k1
import opus5_d6_repair_decision as m2k


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d6_full_assembly_validation.json"
PREFIX = "d6_full_assembly"

# Alignment 122's adopted directions, stated once.
ADOPTED = {
    "MeterRound": {"option": "thin_and_shift"},
    "MeterMedium": {"option": "depth_0.7mm"},
    "MeterLarge": {"option": "depth_0.7mm"},
}

POSES = m2k.POSES
KEY_POSES = m2k.KEY_POSES
VIEWS = m2k.VIEWS


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def under(obj, pivot):
    return pivot.name in m2e.m2d.hierarchy(obj)


def zone_band(root, key, geometry, centre, materials):
    """The builder's own band, with the numbers behind its own skip rule."""
    spec = brushup.SPECS[f"{m2k.THEME}/{key}"]
    pivot = geometry["pivot"]
    tick_back, tick_front = geometry["tick_y"]
    swept = max(
        math.hypot(
            (obj.matrix_world @ vertex.co).x - centre.x,
            (obj.matrix_world @ vertex.co).z - centre.z,
        )
        for obj in pilot.meshes_under(root)
        if under(obj, pivot)
        for vertex in obj.data.vertices
    )
    zone_inner = max(geometry["tick_radius"] * 0.885, swept + 0.0021)
    zone_outer = max(geometry["tick_radius"] * 0.945, zone_inner * 1.068)
    dial_reach = max(
        (
            math.hypot(
                (obj.matrix_world @ vertex.co).x - centre.x,
                (obj.matrix_world @ vertex.co).z - centre.z,
            )
            for obj in pilot.meshes_under(root)
            if not under(obj, pivot)
            for vertex in obj.data.vertices
            if tick_front - 0.002
            <= (obj.matrix_world @ vertex.co).y
            <= tick_back + 0.002
        ),
        default=0.0,
    )
    wanted = "zone" in spec.get("meter_parts", ("boss", "counterweight", "zone"))
    carried = dial_reach >= zone_outer
    facts = {
        "in_spec_meter_parts": wanted,
        "spec_meter_parts": list(
            spec.get("meter_parts", ("boss", "counterweight", "zone"))
        ),
        "swept_radius_mm": round(swept * 1000.0, 4),
        "tick_radius_mm": round(geometry["tick_radius"] * 1000.0, 4),
        "zone_inner_mm": round(zone_inner * 1000.0, 4),
        "zone_outer_mm": round(zone_outer * 1000.0, 4),
        "dial_reach_mm": round(dial_reach * 1000.0, 4),
        "dial_carries_band": carried,
        "built": wanted and carried,
        "skip_reason": (
            None
            if wanted and carried
            else (
                "not in this model's meter_parts"
                if not wanted
                else (
                    f"the dial reaches {dial_reach * 1000.0:.4f} mm, short of "
                    f"the band's outer radius {zone_outer * 1000.0:.4f} mm"
                )
            )
        ),
    }
    if not facts["built"]:
        return None, facts
    band = brushup.arc_band(
        "kinetic_v6_zone_band",
        zone_inner,
        zone_outer,
        29.0,
        59.0,
        tick_back,
        tick_front,
        materials["readout"],
        segments=12,
        centre_x=centre.x,
        centre_z=centre.z,
    )
    band.parent = root
    bpy.context.view_layer.update()
    return band, facts


def adopted_option(project_root, key):
    """Read the adopted parameters back out of the reports that set them."""
    if key == "MeterRound":
        correction = json.loads(
            (project_root / m2k1.OUTPUT).read_text()
        )
        return correction["round_options"]["thin_and_shift"]["parameters"]
    prior = json.loads((project_root / m2k1.M2K_REPORT).read_text())
    return prior["models"][key]["options"]["depth_0.7mm"]["parameters"]


def classify(mover, static):
    if mover.startswith("needle_") and "needle_boss" in static:
        return "intended: the needle turning in its bearing boss"
    if "counterweight" in mover and "needle_boss" in static:
        return "intended: counterweight seated on the boss"
    if mover == "needle_hub" and "polygon_bezel" in static:
        return "known: hub inside the bearing stack (Phase M1)"
    if mover == "needle_blade" and "polygon_bezel" in static:
        return "D-9 blade tangent (closed, alignment 92.1)"
    if mover.startswith("needle_") and "tick" in static:
        return "known D-3 endpoint tick"
    return "new"


def validate(project_root, key):
    begin = time.perf_counter()
    option = adopted_option(project_root, key)
    path, root = m2k.open_production(project_root, key)
    geometry, built, centre = m2k1.build_parts(root, key, option)
    materials = pilot.materials_by_role()
    band, band_facts = zone_band(root, key, geometry, centre, materials)
    if band is not None:
        built["zone_band"] = band

    pieces, component_facts = m2k1.needle_components(root, centre)
    pivot = geometry["pivot"]
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and under(obj, pivot)
    ]
    statics = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and not under(obj, pivot)
    ]
    contacts = m2k.sweep_contacts(pivot, movable, statics, POSES)
    classified = {}
    for label, entry in contacts.items():
        if entry["clear"]:
            continue
        mover, static = label.split(" x ")
        classified[label] = {**entry, "classification": classify(mover, static)}
    new_contacts = sorted(
        label
        for label, entry in classified.items()
        if entry["classification"] == "new"
    )

    inventory = m2e.inventory(root)
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
    triangles = sum(
        len(obj.data.loop_triangles)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and (obj.data.calc_loop_triangles() or True)
    )
    envelope = m2k1.envelope_row(key, bounds)
    spec = brushup.SPECS[f"{m2k.THEME}/{key}"]
    return {
        "model": f"{m2k.THEME}/{key}",
        "adopted_option": ADOPTED[key]["option"],
        "parameters": option,
        "source": str(
            m2k.production_blend(project_root, key).relative_to(project_root)
        ),
        "source_sha256": m1.digest(m2k.production_blend(project_root, key)),
        "pivot_world": [round(v, 6) for v in centre],
        "parts_built": sorted(built),
        "zone_band": band_facts,
        "needle_components": component_facts,
        "materials": {
            name: [m.name if m else None for m in obj.data.materials]
            for name, obj in built.items()
        },
        "hierarchy": {
            name: m2e.m2d.hierarchy(obj) for name, obj in built.items()
        },
        "inventory_objects": len(inventory),
        "triangles": triangles,
        "triangle_budget": m2k.MODELS[key]["triangle_budget"],
        "within_budget": triangles <= m2k.MODELS[key]["triangle_budget"],
        "bounds": bounds,
        "envelope": envelope,
        "readout": m2k.readout_reach(root, centre, built, geometry),
        "motion_contract": {
            "pivot": spec["motion"]["pivot"],
            "axis": list(spec["motion"]["axis"]),
            "sweep_deg": list(spec["motion"]["sweep"]),
            "poses": len(POSES),
        },
        "contacts": classified,
        "new_contacts": new_contacts,
        "pass": (
            not new_contacts
            and envelope["within_envelope"]
            and triangles <= m2k.MODELS[key]["triangle_budget"]
        ),
        "elapsed_seconds": round(time.perf_counter() - begin, 3),
    }


def render(project_root, key):
    directory = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / m2k.THEME / "review"
    )
    directory.mkdir(parents=True, exist_ok=True)
    import opus5_brushup_kinetic_review as review

    option = adopted_option(project_root, key)
    path, root = m2k.open_production(project_root, key)
    geometry, built, centre = m2k1.build_parts(root, key, option)
    band, _ = zone_band(root, key, geometry, centre, pilot.materials_by_role())
    pivot = geometry["pivot"]
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
            target = directory / f"{PREFIX}_{key}_{pose_label}_{view_name}.png"
            review.shot(
                rig, (centre.x, centre.y, centre.z), span * 2.3,
                (view["azimuth"], view["elevation"]), 58.0, target,
            )
            labelled = target.with_name(target.stem + "_labelled.png")
            m2c.label_copy(
                target, labelled,
                [
                    f"{key} full assembly".upper()[:36],
                    f"{pose_label} {view_name}".upper(),
                ],
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

    started = time.perf_counter()
    models = {}
    for key in args.models or ADOPTED:
        models[key] = validate(project_root, key)
        entry = models[key]
        print(
            f"[Opus5D6f] {key} ({entry['adopted_option']}): parts "
            f"{entry['parts_built']}, zone band built "
            f"{entry['zone_band']['built']}, new {entry['new_contacts']}, "
            f"margin {entry['envelope']['margin_mm']} mm, tris "
            f"{entry['triangles']}/{entry['triangle_budget']}, "
            f"pass={entry['pass']} ({round(entry['elapsed_seconds'], 1)}s)"
        )
        if not args.skip_renders:
            models[key]["renders"] = render(project_root, key)

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2k2",
                "defect": "D-6",
                "note": (
                    "Full-assembly validation (alignment 122.2). All three "
                    "brush-up parts are built on the real needle_pivot from "
                    "the production builder's formulas; no Blend is saved and "
                    "the M2k / M2k1 outputs are untouched."
                ),
                "preflight": gate,
                "adopted": ADOPTED,
                "classification_scheme": [
                    "intended: the needle turning in its bearing boss",
                    "intended: counterweight seated on the boss",
                    "known: hub inside the bearing stack (Phase M1)",
                    "D-9 blade tangent (closed, alignment 92.1)",
                    "known D-3 endpoint tick",
                    "new",
                ],
                "models": models,
                "summary": {
                    key: {
                        "pass": entry["pass"],
                        "zone_band_built": entry["zone_band"]["built"],
                        "new_contacts": entry["new_contacts"],
                    }
                    for key, entry in models.items()
                },
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D6f] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
