"""Phase M2k1: the correction M2k needed, and Round's envelope problem.

Alignment 120.3. Two things in M2k have to be put right before any candidate is
built, and one of them changes the answer for one size.

* M2k's prose said bounds were unchanged. Its own report says otherwise: the
  depth shift moves minimum Y by exactly the shift. Corrected here, with the
  Unity depth envelope alongside, because that is what the number is for.
* M2k reported `needle x kinetic_polygon_bezel` under one label carrying one
  depth. The joined `needle` holds two components with different standings -
  the blade, which Phase M1 settled as tangent, and the hub, which sits inside
  its bearing by design. They are separated here so a hub depth never rides on
  a blade label again.

With the envelope applied, Medium and Large's `depth 0.7 mm` fits and Round's
does not: Round's shipped model already uses all but 1.0 mm of its 0.082 m
depth, and the repair needs 4.2 mm. So Round gets its own comparison, and the
envelope is treated as fixed rather than as something to widen.

Read-only, design only. No Blend is saved. M2k's report and its 162 PNG are
left exactly as they are, errors included, as the history they are.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d6_bounded_correction.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_candidate_build as m2e
import opus5_d5_faithful_slot_selection as m2c
import opus5_d5_profile_preserving_slot as m2b
import opus5_d6_repair_decision as m2k


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d6_repair_bounded_correction.json"
PREFIX = "d6_round_option"
M2K_REPORT = "ArtSource/Blender/BrushUp/Opus5/d6_repair_decision_package.json"

# Assets/MatsuMotoMeterAR/Editor/RefinedModelReplacementValidator.cs, quoted so
# the number a proposal is judged against is visible next to the judgement.
ENVELOPE_DEPTH_M = {
    "MeterRound": 0.082,
    "MeterMedium": 0.145,
    "MeterLarge": 0.205,
}
ENVELOPE_SOURCE = (
    "Assets/MatsuMotoMeterAR/Editor/RefinedModelReplacementValidator.cs, "
    "MockInstrumentKind default / RoundMeterMedium / RoundMeterLarge"
)

CLEARANCE_MM = 0.7
ROUND_MARGIN_MM = 0.5

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


def depth_of(bounds):
    """Blender min Y becomes Unity +Z depth; max Y is 0 by the mount contract."""
    return abs(bounds["min"][1])


def envelope_row(key, bounds):
    depth = depth_of(bounds)
    limit = ENVELOPE_DEPTH_M[key]
    return {
        "blender_min_y_m": round(bounds["min"][1], 6),
        "unity_depth_m": round(depth, 6),
        "envelope_depth_m": limit,
        "margin_mm": round((limit - depth) * 1000.0, 4),
        "within_envelope": depth <= limit,
    }


def build_parts(root, key, option):
    """M2k's builder plus a thickness knob.

    Kept here rather than added to M2k so that script, and therefore its
    published report, stays exactly as it was reviewed.
    """
    import opus5_brushup_archetype as brushup

    geometry, spec = m2k.geometry_of(root, key)
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
        shift = option.get("depth_shift_m", 0.0)
        rear = y_back + shift
        front = (
            rear - option["thickness_m"]
            if option.get("thickness_m")
            else y_front + shift
        )
        weight = brushup.plate(
            "kinetic_v6_needle_counterweight",
            hub * 0.98 * scale,
            hub * 0.70 * scale,
            rear,
            front,
            materials["metal"],
            x=centre.x,
            z=centre.z + geometry["needle_tail"] - hub * 0.33 * scale,
            chamfer=hub * 0.16 * scale,
        )
        pilot.parent_keep_world(weight, pivot)
        built["counterweight"] = weight

    bpy.context.view_layer.update()
    return geometry, built, centre


def needle_components(root, centre):
    """Split the joined needle so the hub's depth stops riding on the blade."""
    needle = bpy.data.objects["needle"]
    islands = m2e.islands_of(needle.data)
    facts = [m2e.island_facts(needle, island, centre) for island in islands]
    blade = max(range(len(islands)), key=lambda i: facts[i]["length_mm"][2])
    roles = {i: ("blade" if i == blade else "hub") for i in range(len(islands))}
    pieces = {}
    for index, island in enumerate(islands):
        piece = needle.copy()
        piece.data = needle.data.copy()
        piece.name = f"needle_{roles[index]}"
        bpy.context.collection.objects.link(piece)
        mesh = bmesh.new()
        mesh.from_mesh(piece.data)
        mesh.verts.ensure_lookup_table()
        bmesh.ops.delete(
            mesh,
            geom=[v for v in mesh.verts if v.index not in island],
            context="VERTS",
        )
        mesh.to_mesh(piece.data)
        mesh.free()
        piece.data.update()
        piece.parent = needle.parent
        piece.matrix_world = needle.matrix_world.copy()
        pieces[roles[index]] = piece
    needle.hide_render = True
    needle.hide_viewport = True
    bpy.context.view_layer.update()
    return pieces, {roles[i]: facts[i] for i in range(len(facts))}


def aperture(plate_obj, radius, centre):
    """Open the solid cap where the weight sweeps, keeping the outer outline."""
    points = [plate_obj.matrix_world @ v.co for v in plate_obj.data.vertices]
    low = min(p.y for p in points) - 0.01
    high = max(p.y for p in points) + 0.01
    mesh = bpy.data.meshes.new("opus5_aperture_cutter")
    cutter = bpy.data.objects.new("opus5_aperture_cutter", mesh)
    bpy.context.collection.objects.link(cutter)
    segments = 24
    rim = [
        (
            centre.x + radius * math.cos(2.0 * math.pi * i / segments),
            centre.z + radius * math.sin(2.0 * math.pi * i / segments),
        )
        for i in range(segments)
    ]
    verts = [(x, low, z) for x, z in rim] + [(x, high, z) for x, z in rim]
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j, segments + i))
    faces.append(tuple(range(segments - 1, -1, -1)))
    faces.append(tuple(range(segments, segments * 2)))
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    for material in plate_obj.data.materials:
        cutter.data.materials.append(material)

    modifier = plate_obj.modifiers.new("aperture", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.object = cutter
    modifier.solver = "EXACT"
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(plate_obj.evaluated_get(depsgraph))
    plate_obj.modifiers.remove(modifier)
    old = plate_obj.data
    plate_obj.data = baked
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.context.view_layer.update()


def outer_outline(plate_obj, centre):
    """The twelve-sided rim, so a proposal can be shown not to have touched it."""
    points = [plate_obj.matrix_world @ v.co for v in plate_obj.data.vertices]
    outer = max(math.hypot(p.x - centre.x, p.z - centre.z) for p in points)
    corners = sorted(
        {
            round(
                math.degrees(math.atan2(p.x - centre.x, p.z - centre.z)) % 360.0, 2
            )
            for p in points
            if math.hypot(p.x - centre.x, p.z - centre.z) > outer - 1e-5
        }
    )
    radii = sorted(
        math.hypot(p.x - centre.x, p.z - centre.z) for p in points
    )
    return {
        "outer_radius_mm": round(outer * 1000.0, 4),
        "inner_radius_mm": round(radii[0] * 1000.0, 4),
        "rim_vertices_at_outer": len(corners),
        "loop_triangles": len(plate_obj.data.loop_triangles),
    }


def evaluate(project_root, key, name, option, split_needle=True):
    """One proposal, measured the way M2k should have measured it."""
    path, root = m2k.open_production(project_root, key)
    geometry, built, centre = build_parts(root, key, option)
    plate_obj = next(
        obj for obj in pilot.meshes_under(root) if "polygon_bezel" in obj.name
    )
    outline_before = outer_outline(plate_obj, centre)
    if option.get("aperture_radius_m"):
        aperture(plate_obj, option["aperture_radius_m"], centre)
    outline_after = outer_outline(plate_obj, centre)

    parts = {}
    facts = {}
    if split_needle:
        parts, facts = needle_components(root, centre)

    pivot = geometry["pivot"]
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
        if "counterweight" in mover and "needle_boss" in static:
            kind = "intended: counterweight seated on the boss"
        elif mover.startswith("needle_") and "needle_boss" in static:
            # SPECS records "needle x kinetic_v6_needle_boss" as the needle
            # turning in the boss. Splitting the needle must not turn half of
            # that intended pair into a finding.
            kind = "intended: the needle turning in its bearing boss"
        elif mover == "needle_hub" and "polygon_bezel" in static:
            kind = "known: hub inside the bearing stack (Phase M1)"
        elif mover == "needle_blade" and "polygon_bezel" in static:
            kind = "D-9 blade tangent (closed, alignment 92.1)"
        elif mover == "needle_blade" and "tick" in static:
            kind = "known D-3 endpoint tick"
        else:
            kind = "new"
        classified[label] = {**entry, "kind": kind}

    new_contacts = {
        label: entry for label, entry in classified.items() if entry["kind"] == "new"
    }
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
    boss_radius = geometry["hub_radius"] * 1.15
    return {
        "option": name,
        "parameters": option,
        "bounds": bounds,
        "envelope": envelope_row(key, bounds),
        "triangles": triangles,
        "triangle_budget": m2k.MODELS[key]["triangle_budget"],
        "within_budget": triangles <= m2k.MODELS[key]["triangle_budget"],
        "plate_outline": {
            "before": outline_before,
            "after": outline_after,
            "outer_rim_unchanged": (
                outline_before["rim_vertices_at_outer"]
                == outline_after["rim_vertices_at_outer"]
                and abs(
                    outline_before["outer_radius_mm"]
                    - outline_after["outer_radius_mm"]
                )
                <= 1e-4
            ),
            "plate_triangle_delta": (
                outline_after["loop_triangles"] - outline_before["loop_triangles"]
            ),
            "see_through_ring_mm": (
                round(
                    (option["aperture_radius_m"] - boss_radius) * 1000.0, 4
                )
                if option.get("aperture_radius_m")
                else None
            ),
        },
        "needle_components": facts,
        "contacts": classified,
        "new_contacts": sorted(new_contacts),
        "readout": m2k.readout_reach(root, centre, built, geometry),
        "pass": (
            not new_contacts
            and envelope_row(key, bounds)["within_envelope"]
            and triangles <= m2k.MODELS[key]["triangle_budget"]
        ),
    }


def round_options(project_root):
    """Round has 1.0 mm of depth to play with, so the shift cannot be free."""
    path, root = m2k.open_production(project_root, "MeterRound")
    geometry, _ = m2k.geometry_of(root, "MeterRound")
    y_back, y_front = geometry["needle_y"]
    plate_obj = next(
        obj for obj in pilot.meshes_under(root) if "polygon_bezel" in obj.name
    )
    plate_front = min(
        (plate_obj.matrix_world @ Vector(c)).y for c in plate_obj.bound_box
    )
    weight_rear_target = plate_front - CLEARANCE_MM / 1000.0
    shift = weight_rear_target - y_back
    # The deepest the weight may reach and still leave the stated margin.
    allowed_front = -(ENVELOPE_DEPTH_M["MeterRound"] - ROUND_MARGIN_MM / 1000.0)
    thickness = weight_rear_target - allowed_front

    centre = geometry["pivot"].matrix_world.translation.copy()
    reach = None
    _, built, _ = build_parts(root, "MeterRound", {"counterweight_scale": 1.0})
    reach = max(
        math.hypot(
            (built["counterweight"].matrix_world @ v.co).x - centre.x,
            (built["counterweight"].matrix_world @ v.co).z - centre.z,
        )
        for v in built["counterweight"].data.vertices
    )

    return {
        "thin_and_shift": {
            "counterweight_scale": 1.0,
            "depth_shift_m": round(shift, 6),
            "thickness_m": round(thickness, 6),
        },
        "drop": {},
        "plate_aperture": {
            "counterweight_scale": 1.0,
            "aperture_radius_m": round(reach + CLEARANCE_MM / 1000.0, 6),
        },
    }


def render_option(project_root, key, name, option):
    directory = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / m2k.THEME / "review"
    )
    directory.mkdir(parents=True, exist_ok=True)
    import opus5_brushup_kinetic_review as review

    path, root = m2k.open_production(project_root, key)
    geometry, built, centre = build_parts(root, key, option)
    if option.get("aperture_radius_m"):
        plate_obj = next(
            obj for obj in pilot.meshes_under(root) if "polygon_bezel" in obj.name
        )
        aperture(plate_obj, option["aperture_radius_m"], centre)
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
            target = directory / f"{PREFIX}_{name}_{pose_label}_{view_name}.png"
            review.shot(
                rig, (centre.x, centre.y, centre.z), span * 2.3,
                (view["azimuth"], view["elevation"]), 58.0, target,
            )
            labelled = target.with_name(target.stem + "_labelled.png")
            m2c.label_copy(
                target, labelled,
                [f"ROUND {name}".upper()[:36], f"{pose_label} {view_name}".upper()],
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
    prior = json.loads((project_root / M2K_REPORT).read_text())

    started = time.perf_counter()

    # 120.3-1: the correction, straight from M2k's own numbers.
    corrected = {}
    for key, model in prior["models"].items():
        rows = {}
        for name in ("keep", "depth_0.7mm", "depth_1.4mm", "drop"):
            rows[name] = {
                "bounds": model["options"][name]["bounds"],
                **envelope_row(key, model["options"][name]["bounds"]),
            }
        corrected[key] = {
            "rows": rows,
            "m2k_claim": "bounds unchanged",
            "correction": (
                "minimum Y moves by exactly the depth shift; the claim was "
                "wrong and its own report shows it"
            ),
        }
        print(
            f"[Opus5D6c] {key}: keep depth {rows['keep']['unity_depth_m']} m, "
            f"proposed {rows['depth_0.7mm']['unity_depth_m']} m, envelope "
            f"{rows['depth_0.7mm']['envelope_depth_m']} m, margin "
            f"{rows['depth_0.7mm']['margin_mm']} mm, within "
            f"{rows['depth_0.7mm']['within_envelope']}"
        )

    # 120.3-2: Medium and Large re-audited with the components separated.
    reaudit = {}
    for key in ("MeterMedium", "MeterLarge"):
        option = prior["models"][key]["options"]["depth_0.7mm"]["parameters"]
        reaudit[key] = evaluate(project_root, key, "depth_0.7mm", option)
        print(
            f"[Opus5D6c] {key} re-audit: pass={reaudit[key]['pass']} "
            f"new={reaudit[key]['new_contacts']} margin "
            f"{reaudit[key]['envelope']['margin_mm']} mm"
        )

    # 120.3-3: Round, inside its own envelope.
    options = round_options(project_root)
    round_results = {}
    for name, option in options.items():
        round_results[name] = evaluate(project_root, "MeterRound", name, option)
        entry = round_results[name]
        print(
            f"[Opus5D6c] Round {name}: pass={entry['pass']} "
            f"depth {entry['envelope']['unity_depth_m']} m margin "
            f"{entry['envelope']['margin_mm']} mm new={entry['new_contacts']}"
        )

    renders = {}
    if not args.skip_renders:
        for name, option in options.items():
            renders[name] = render_option(project_root, "MeterRound", name, option)

    passing = [name for name, entry in round_results.items() if entry["pass"]]
    keeping = [name for name in passing if name != "drop"]
    recommendation = (
        {
            "option": keeping[0],
            "reason": (
                "the only proposal that keeps the counterweight, stays inside "
                f"the {ENVELOPE_DEPTH_M['MeterRound']} m envelope and adds no "
                "new contact"
            ),
        }
        if keeping
        else {
            "option": "drop" if "drop" in passing else None,
            "reason": (
                "no proposal keeps the counterweight within Round's envelope"
            ),
        }
    )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2k1",
                "defect": "D-6",
                "note": (
                    "Bounded correction to M2k (alignment 120.3). Design only; "
                    "no Blend is saved and M2k's report and PNG are untouched."
                ),
                "preflight": gate,
                "corrects": {
                    "report": M2K_REPORT,
                    "sha256": m1.digest(project_root / M2K_REPORT),
                    "items": [
                        "119.5 claimed bounds unchanged; they are not",
                        "119.5 reported hub depth under a blade tangent label",
                    ],
                },
                "envelope_source": ENVELOPE_SOURCE,
                "envelope_depth_m": ENVELOPE_DEPTH_M,
                "bounds_correction": corrected,
                "medium_large_reaudit": reaudit,
                "round_options": round_results,
                "round_renders": renders,
                "recommendation": {"MeterRound": recommendation},
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5D6c] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
