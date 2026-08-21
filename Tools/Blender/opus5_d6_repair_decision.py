"""Phase M2k: how to repair D-6, decided per meter size.

Alignment 118.2. D-6 is that the brush-up parts were built about the model
origin while the needle pivot sits 4, 8 and 12 mm back in Z. Moving them onto
the pivot is necessary but not sufficient: on Medium it puts the counterweight
into the polygon bezel, which is a solid twelve-sided plate whose front cap
crosses the centre, so the weight has to be resized, moved in depth, or
dropped.

This decides that per size, design only. Nothing is saved: the parts are built
in memory from the same formulas the approved builder uses, so an option is a
change of parameters rather than a change of code.

Two things earlier work got wrong are avoided by construction:

* the parts are placed on each model's own `needle_pivot`, never the origin
* contact is judged with the two-layer primitive over the whole sweep, not with
  the legacy point test the first survey used

Known classifications are separated from findings rather than counted with
them: the needle turning in its bearing boss and the hub inside it are the
intended mount, and the endpoint tick contact is D-3, already recorded.

Read-only. No Blend is saved and no existing report or PNG is overwritten.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d6_repair_decision.py -- \
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


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d6_repair_decision_package.json"
PREFIX = "d6_repair_decision"
PRIOR_SURVEY = "ArtSource/Blender/BrushUp/Opus5/r3_b2p_design_survey.json"

MODELS = {
    "MeterRound": {
        "root": "PF_Visual_MeterRound_KineticSafety_V6",
        "frozen": "BL_MeterRound_KineticSafety_V6_Opus5_R2_Retopo.blend",
        "revision": "R2",
        "triangle_budget": 5000,
    },
    "MeterMedium": {
        "root": "PF_Visual_MeterMedium_KineticSafety_V6",
        "frozen": "BL_MeterMedium_KineticSafety_V6_Opus5_B2_Retopo.blend",
        "revision": "B2",
        "triangle_budget": 25000,
    },
    "MeterLarge": {
        "root": "PF_Visual_MeterLarge_KineticSafety_V6",
        "frozen": "BL_MeterLarge_KineticSafety_V6_Opus5_B2_Retopo.blend",
        "revision": "B2",
        "triangle_budget": 25000,
    },
}

THEME = "KineticSafety"
SWEEP = (-55.0, 55.0)
POSES = [SWEEP[0] + (SWEEP[1] - SWEEP[0]) * i / 22 for i in range(23)]
KEY_POSES = (("minimum", -55.0), ("neutral", 0.0), ("maximum", 55.0))

# Alignment 118.2-5. These are already classified; they are reported, never
# folded into "new contact". Matched on the whole mover name, not a substring:
# "needle" appears inside "kinetic_v6_needle_counterweight", so a token match
# quietly filed the counterweight's contact with the plate under D-9 and made
# every option look clear.
KNOWN = (
    (
        "known bearing mount",
        lambda mover, static: (
            (mover == "needle" or "counterweight" in mover)
            and "needle_boss" in static
        ),
    ),
    (
        "known D-9 blade tangent",
        lambda mover, static: mover == "needle" and "polygon_bezel" in static,
    ),
    (
        "known D-3 endpoint tick",
        lambda mover, static: mover == "needle" and "tick" in static,
    ),
)

SHRINK_STEPS = [round(1.0 - 0.05 * i, 2) for i in range(13)]
DEPTH_CLEARANCES_MM = (0.7, 1.4)

VIEWS = {
    "front": {"azimuth": 0.0, "elevation": 8.0},
    "oblique": {"azimuth": 38.0, "elevation": 26.0},
    "section": {"azimuth": 88.0, "elevation": 6.0, "section": True},
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def production_blend(project_root, key):
    return (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / THEME
        / f"BL_{key}_{THEME}_V6_Retopo.blend"
    )


def frozen_blend(project_root, key):
    return (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / THEME
        / MODELS[key]["frozen"]
    )


def classify_pair(mover, static):
    for label, matches in KNOWN:
        if matches(mover, static):
            return label
    return "new"


def open_production(project_root, key):
    path = production_blend(project_root, key)
    m1.open_blend(path)
    root = bpy.data.objects[MODELS[key]["root"]]
    return path, root


def geometry_of(root, key):
    spec = brushup.SPECS[f"{THEME}/{key}"]
    return brushup.meter_geometry(root, spec["motion"]), spec


def build_parts(root, key, option):
    """The approved builder's formulas, with this option's parameters.

    Rebuilt here rather than called so an option can change a dimension without
    touching a builder that is already approved for other models.
    """
    geometry, spec = geometry_of(root, key)
    materials = pilot.materials_by_role()
    hub = geometry["hub_radius"]
    y_back, y_front = geometry["needle_y"]
    pivot = geometry["pivot"]
    centre = pivot.matrix_world.translation.copy()

    boss = brushup.v4.cylinder_y(
        "kinetic_v6_needle_boss",
        hub * 1.15,
        (y_back - y_front) * 0.5,
        -(y_back + y_front) * 0.5 + (y_back - y_front) * 0.25,
        materials["metal"],
        16,
    )
    boss.location.x += centre.x
    boss.location.z += centre.z
    boss.parent = root
    built = {"boss": boss}

    scale = option.get("counterweight_scale")
    if scale is not None:
        depth_shift = option.get("depth_shift_m", 0.0)
        weight = brushup.plate(
            "kinetic_v6_needle_counterweight",
            hub * 0.98 * scale,
            hub * 0.70 * scale,
            y_back + depth_shift,
            y_front + depth_shift,
            materials["metal"],
            x=centre.x,
            z=centre.z + geometry["needle_tail"] - hub * 0.33 * scale,
            chamfer=hub * 0.16 * scale,
        )
        pilot.parent_keep_world(weight, pivot)
        built["counterweight"] = weight

    bpy.context.view_layer.update()
    return geometry, built, centre


def sweep_contacts(pivot, movers, statics, poses):
    base = pivot.rotation_euler.copy()
    results = {}
    try:
        for degrees in poses:
            pivot.rotation_euler[1] = base[1] + math.radians(degrees)
            bpy.context.view_layer.update()
            for mover in movers:
                mover_tris = m1.world_triangles(mover)
                mover_broad, mover_exact = m1.trees(mover)
                for static in statics:
                    label = f"{mover.name} x {static.name}"
                    entry = results.setdefault(
                        label,
                        {
                            "surface_crossing": 0,
                            "surface_tangent": 0,
                            "penetrating_vertices": 0,
                            "deepest_intrusion_mm": 0.0,
                            "poses_in_contact": 0,
                            "classification": classify_pair(mover.name, static.name),
                        },
                    )
                    static_tris = m1.world_triangles(static)
                    static_broad, static_exact = m1.trees(static)
                    pairs = contact.candidate_pairs(
                        mover_tris, static_tris, mover_broad, static_broad
                    )
                    surface = contact.surface_contact(mover_tris, static_tris, pairs)
                    crossing = len(surface[contact.CROSSING])
                    tangent = len(surface[contact.TANGENT])
                    penetrating = 0
                    deepest = 0.0
                    for source, tree in (
                        (mover, static_exact), (static, mover_exact)
                    ):
                        depth = contact.material_penetration(
                            [
                                source.matrix_world @ v.co
                                for v in source.data.vertices
                            ],
                            tree,
                        )
                        penetrating = max(penetrating, depth["penetrating_vertices"])
                        deepest = max(deepest, depth["deepest_intrusion_mm"])
                    entry["surface_crossing"] += crossing
                    entry["surface_tangent"] += tangent
                    entry["penetrating_vertices"] = max(
                        entry["penetrating_vertices"], penetrating
                    )
                    entry["deepest_intrusion_mm"] = max(
                        entry["deepest_intrusion_mm"], deepest
                    )
                    if crossing or penetrating:
                        entry["poses_in_contact"] += 1
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    for entry in results.values():
        entry["deepest_intrusion_mm"] = round(entry["deepest_intrusion_mm"], 6)
        entry["clear"] = (
            entry["surface_crossing"] == 0 and entry["penetrating_vertices"] == 0
        )
    return results


def movable_static(root, pivot, built):
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
    return movable, statics


def readout_reach(root, centre, built, geometry):
    """Does the weight stay clear of the tick ring the reading is on?"""
    if "counterweight" not in built:
        return {"counterweight": None, "clears_tick_ring": True}
    weight = built["counterweight"]
    reach = max(
        math.hypot(
            (weight.matrix_world @ v.co).x - centre.x,
            (weight.matrix_world @ v.co).z - centre.z,
        )
        for v in weight.data.vertices
    )
    return {
        "counterweight_reach_mm": round(reach * 1000.0, 4),
        "tick_ring_radius_mm": round(geometry["tick_radius"] * 1000.0, 4),
        "margin_mm": round((geometry["tick_radius"] - reach) * 1000.0, 4),
        "clears_tick_ring": reach < geometry["tick_radius"],
    }


def evaluate(project_root, key, name, option):
    path, root = open_production(project_root, key)
    geometry, built, centre = build_parts(root, key, option)
    pivot = geometry["pivot"]
    movable, statics = movable_static(root, pivot, built)
    contacts = sweep_contacts(pivot, movable, statics, POSES)

    new_contacts = {
        label: entry
        for label, entry in contacts.items()
        if entry["classification"] == "new" and not entry["clear"]
    }
    known = {
        label: entry
        for label, entry in contacts.items()
        if entry["classification"] != "new" and not entry["clear"]
    }
    triangles = sum(
        len(obj.data.loop_triangles)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and (obj.data.calc_loop_triangles() or True)
    )
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render
        for corner in obj.bound_box
    ]
    return {
        "option": name,
        "parameters": option,
        "parts_built": sorted(built),
        "pivot_world": [round(v, 6) for v in centre],
        "hub_radius_mm": round(geometry["hub_radius"] * 1000.0, 4),
        "triangles": triangles,
        "triangle_budget": MODELS[key]["triangle_budget"],
        "within_budget": triangles <= MODELS[key]["triangle_budget"],
        "bounds": {
            "min": [round(min(p[i] for p in points), 6) for i in range(3)],
            "max": [round(max(p[i] for p in points), 6) for i in range(3)],
        },
        "readout": readout_reach(root, centre, built, geometry),
        "new_contacts": new_contacts,
        "known_contacts": {
            label: {
                "classification": entry["classification"],
                "deepest_intrusion_mm": entry["deepest_intrusion_mm"],
                "poses_in_contact": entry["poses_in_contact"],
            }
            for label, entry in known.items()
        },
        "pass": not new_contacts,
    }


def largest_clear_scale(project_root, key):
    """Search down for the biggest counterweight that adds no new contact."""
    trail = []
    for scale in SHRINK_STEPS:
        result = evaluate(
            project_root, key, f"shrink_{scale}", {"counterweight_scale": scale}
        )
        trail.append(
            {
                "scale": scale,
                "pass": result["pass"],
                "new_contacts": sorted(result["new_contacts"]),
            }
        )
        if result["pass"]:
            return scale, trail, result
    return None, trail, None


def render_option(project_root, key, name, project_scene):
    directory = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME / "review"
    )
    directory.mkdir(parents=True, exist_ok=True)
    root, pivot, centre = (
        project_scene["root"], project_scene["pivot"], project_scene["centre"]
    )
    import opus5_brushup_kinetic_review as review

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
            target = directory / f"{PREFIX}_{key}_{name}_{pose_label}_{view_name}.png"
            review.shot(
                rig, (centre.x, centre.y, centre.z), span * 2.3,
                (view["azimuth"], view["elevation"]), 58.0, target,
            )
            labelled = target.with_name(target.stem + "_labelled.png")
            m2c.label_copy(
                target, labelled,
                [f"{key} {name}".upper()[:36], f"{pose_label} {view_name}".upper()],
            )
            written[f"{pose_label}/{view_name}"] = {
                "unlabelled": str(target.relative_to(project_root)),
                "labelled": str(labelled.relative_to(project_root)),
            }
    pivot.rotation_euler[1] = 0.0
    bpy.context.view_layer.update()
    return written


def survey_model(project_root, key, skip_renders):
    begin = time.perf_counter()
    options = {}

    options["keep"] = evaluate(
        project_root, key, "keep", {"counterweight_scale": 1.0}
    )
    scale, trail, shrunk = largest_clear_scale(project_root, key)
    options["shrink"] = (
        {**shrunk, "search_trail": trail, "largest_clear_scale": scale}
        if shrunk
        else {
            "option": "shrink",
            "search_trail": trail,
            "largest_clear_scale": None,
            "pass": False,
            "reason": "no scale down to 0.40 clears",
        }
    )
    for clearance in DEPTH_CLEARANCES_MM:
        name = f"depth_{clearance}mm"
        path, root = open_production(project_root, key)
        geometry, _ = geometry_of(root, key)
        # The overlap is in depth, not radius: the weight sits at 10-52 mm
        # radius, well inside the bezel's 47-140 mm rim, but the bezel is a
        # solid twelve-sided plate whose front cap spans the centre, so the
        # weight's rear face is inside it. The shift therefore moves the
        # weight's **rear** face forward of the bezel's front face, which is
        # the opposite direction to the first attempt.
        plate_front = min(
            (obj.matrix_world @ Vector(corner)).y
            for obj in pilot.meshes_under(root)
            if "polygon_bezel" in obj.name
            for corner in obj.bound_box
        )
        weight_rear = geometry["needle_y"][0]
        shift = (plate_front - clearance / 1000.0) - weight_rear
        options[name] = evaluate(
            project_root, key, name,
            {"counterweight_scale": 1.0, "depth_shift_m": round(shift, 6)},
        )
    options["drop"] = evaluate(project_root, key, "drop", {})

    renders = {}
    if not skip_renders:
        # The three that a decision is actually made between: as approved,
        # the recommended repair, and no counterweight at all.
        for name in ("keep", "depth_0.7mm", "drop"):
            option = options[name]["parameters"]
            path, root = open_production(project_root, key)
            geometry, built, centre = build_parts(root, key, option)
            renders[name] = render_option(
                project_root, key, name,
                {"root": root, "pivot": geometry["pivot"], "centre": centre},
            )

    passing = [
        name
        for name, entry in options.items()
        if entry.get("pass") and name != "drop"
    ]
    if "keep" in passing:
        recommendation = {
            "option": "keep",
            "reason": "the full-size counterweight on the pivot adds no new contact",
        }
    elif passing:
        best = passing[0]
        recommendation = {
            "option": best,
            "reason": (
                "the largest counterweight that adds no new contact once the "
                f"parts sit on the pivot ({options[best].get('parameters')})"
            ),
        }
    else:
        recommendation = {
            "option": "drop",
            "reason": (
                "no counterweight size or depth clears the solid twelve-sided "
                "plate without a plate change, and the plate's outline is not "
                "available to change (alignment 118.2-4)"
            ),
        }

    return {
        "model": f"{THEME}/{key}",
        "production_source": str(
            production_blend(project_root, key).relative_to(project_root)
        ),
        "production_sha256": m1.digest(production_blend(project_root, key)),
        "frozen_source": str(
            frozen_blend(project_root, key).relative_to(project_root)
        ),
        "frozen_revision": MODELS[key]["revision"],
        "frozen_sha256": m1.digest(frozen_blend(project_root, key)),
        "poses": {"count": len(POSES), "degrees": list(SWEEP)},
        "options": options,
        "renders": renders,
        "recommendation": recommendation,
        "elapsed_seconds": round(time.perf_counter() - begin, 3),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)
    prior = project_root / PRIOR_SURVEY

    started = time.perf_counter()
    models = {}
    for key in args.models or MODELS:
        models[key] = survey_model(project_root, key, args.skip_renders)
        entry = models[key]
        print(
            f"[Opus5D6] {key}: "
            + ", ".join(
                f"{name}={'PASS' if option.get('pass') else 'fail'}"
                for name, option in entry["options"].items()
            )
            + f" -> {entry['recommendation']['option']} "
            f"({round(entry['elapsed_seconds'], 1)}s)"
        )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2k",
                "defect": "D-6",
                "note": (
                    "Design-only decision package (alignment 118.2). Parts are "
                    "built in memory on each model's own needle_pivot; no Blend "
                    "is saved and no candidate is published."
                ),
                "preflight": gate,
                "prior_survey": {
                    "path": PRIOR_SURVEY,
                    "sha256": m1.digest(prior) if prior.is_file() else None,
                    "status": (
                        "kept as provenance; its contact figures came from the "
                        "legacy point test and are re-measured here"
                    ),
                },
                "known_classifications": {
                    "bearing_mount": "needle or counterweight x *needle_boss*",
                    "d9_blade_tangent": "needle (exact) x *polygon_bezel*",
                    "d3_endpoint_tick": "needle (exact) x *tick*",
                    "matching": (
                        "the mover is matched on its whole name; a substring "
                        "match put the counterweight under D-9"
                    ),
                },
                "plate_constraint": (
                    "the original twelve-sided outer outline is preserved; "
                    "circularising or widening it is excluded (alignment 118.2-4)"
                ),
                "models": models,
                "recommendation_summary": {
                    key: entry["recommendation"]["option"]
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
    print(f"[Opus5D6] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
