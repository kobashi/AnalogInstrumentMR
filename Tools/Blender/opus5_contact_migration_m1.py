"""Phase M1: run the old contact test and the new two-layer one side by side.

Alignment 90.1-90.3. The new primitive is approved at fixture level, but nothing
is known yet about how much it moves the conclusions already drawn from the old
one. So neither replaces the other here: both run over the same poses, on the
same scenes, and every pair is reported with what each said and whether the
conclusion changes.

Four systems, chosen because they fail in different ways:

* the three Kinetic Safety meters, where a needle sits in a solid plate (D-9);
* D-3's needle against the endpoint ticks, baseline and fixed candidate;
* D-5's switch against its retaining ring, with and without the legacy axle;
* the PowerSlider sliding interface, whose 1-2 micrometre readings decide
  whether the named allowance still means what it claims.

Read-only. No Blend, candidate or existing audit JSON is written; the only
output is the migration table.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_contact_migration_m1.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
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
import opus5_d5_toggle_axle_proposal as splitter


FIXTURE_REPORT = "ArtSource/Blender/BrushUp/Opus5/contact_fixture_report.json"
OUTPUT = "ArtSource/Blender/BrushUp/Opus5/contact_migration_m1.json"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--system", dest="systems", action="append")
    return parser.parse_args(args)


def preflight(project_root):
    """Refuse to run on an unproven primitive or a different Blender."""
    report = project_root / FIXTURE_REPORT
    if not report.is_file():
        raise SystemExit(f"fixture report missing: {report}")
    payload = json.loads(report.read_text())
    if not payload.get("all_passed"):
        raise SystemExit("fixture report says the primitive is not passing")
    recorded = payload.get("authoring_environment", {})
    current = blender_compat.provenance()
    for key in ("blender_version", "blender"):
        if key in recorded and key in current and recorded[key] != current[key]:
            raise SystemExit(
                f"fixture report was produced on a different environment: "
                f"{key} {recorded[key]!r} != {current[key]!r}"
            )
    return {"fixture_report": FIXTURE_REPORT, "all_passed": True}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def open_blend(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)


def world_triangles(obj):
    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    return [
        [matrix @ obj.data.vertices[i].co for i in triangle.vertices]
        for triangle in obj.data.loop_triangles
    ]


def trees(obj):
    """(inflated for candidates, exact for measurement)."""
    from mathutils.bvhtree import BVHTree

    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    vertices = [tuple(matrix @ vertex.co) for vertex in obj.data.vertices]
    polygons = [tuple(t.vertices) for t in obj.data.loop_triangles]
    return (
        BVHTree.FromPolygons(
            vertices, polygons, all_triangles=True,
            epsilon=contact.BROAD_PHASE_EPSILON_M,
        ),
        BVHTree.FromPolygons(vertices, polygons, all_triangles=True, epsilon=0.0),
    )


def blank_pair():
    return {
        "legacy_contact_poses": 0,
        "legacy_contact_points": 0,
        "surface_tangent": 0,
        "surface_crossing": 0,
        "mover_triangles": set(),
        "static_triangles": set(),
        "radius_min": None,
        "radius_max": None,
        "outside_bearing": False,
        "boundary_vertices": 0,
        "within_tolerance_vertices": 0,
        "penetrating_vertices": 0,
        "deepest_intrusion_mm": 0.0,
    }


def finish_pair(entry):
    entry["mover_triangles"] = sorted(entry["mover_triangles"])[:12]
    entry["static_triangles"] = sorted(entry["static_triangles"])[:12]
    for key in ("radius_min", "radius_max"):
        if entry[key] is not None:
            entry[key] = round(entry[key], 6)
    entry["deepest_intrusion_mm"] = round(entry["deepest_intrusion_mm"], 6)
    entry["verdict"] = contact.verdict(
        {
            "boundary_vertices": entry["boundary_vertices"],
            "within_tolerance_vertices": entry["within_tolerance_vertices"],
            "penetrating_vertices": entry["penetrating_vertices"],
            "raw_parity_hits": (
                entry["boundary_vertices"]
                + entry["within_tolerance_vertices"]
                + entry["penetrating_vertices"]
            ),
            "deepest_intrusion_mm": entry["deepest_intrusion_mm"],
        },
        entry["surface_crossing"],
        None if entry["surface_crossing"] else {"cells_in_both": 0},
        entry["surface_tangent"],
    )
    entry["legacy_conclusion"] = (
        "contact" if entry["legacy_contact_poses"] else "no contact"
    )
    entry["delta"], entry["delta_reason"] = classify_delta(entry)
    return entry


def classify_delta(entry):
    legacy_contact = bool(entry["legacy_contact_poses"])
    verdict = entry["verdict"]
    if legacy_contact and verdict == "penetration":
        return "unchanged", "both call it a real intrusion"
    if legacy_contact and verdict == "penetration_unquantified":
        return (
            "unchanged",
            "still a failure, now flagged as an overlap with no measurable depth",
        )
    if legacy_contact and verdict == "tangent_or_within_tolerance":
        return (
            "weakened",
            "the old test counted this as contact; it is a touch or a "
            "within-tolerance intrusion, not a penetration",
        )
    if legacy_contact and verdict == "clear":
        return "invalidated", "the old test reported contact where there is none"
    if not legacy_contact and verdict in ("penetration", "penetration_unquantified"):
        return "strengthened", "the old test missed a real intrusion"
    if not legacy_contact and verdict == "tangent_or_within_tolerance":
        return "strengthened", "a clearance-0 touch the old test did not report"
    return "unchanged", "neither reports contact"


def sweep_pairs(pivot, movers, statics, centre, bearing, poses, rotate_axis=1,
                linear=False):
    """Both tests over the same poses. Returns {pair label: entry}."""
    results = {}
    base = (pivot.location if linear else pivot.rotation_euler).copy()
    try:
        for value in poses:
            posed = base.copy()
            posed[rotate_axis] = base[rotate_axis] + (
                value if linear else math.radians(value)
            )
            if linear:
                pivot.location = posed
            else:
                pivot.rotation_euler = posed
            bpy.context.view_layer.update()

            for mover in movers:
                mover_tris = world_triangles(mover)
                mover_broad, mover_exact = trees(mover)
                for static in statics:
                    static_tris = world_triangles(static)
                    static_broad, static_exact = trees(static)
                    label = f"{mover.name} x {static.name}"
                    entry = results.setdefault(label, blank_pair())

                    # Legacy: BVH overlap plus the old point test.
                    legacy_tree, legacy_v, legacy_p = pilot.bvh_for(mover)
                    other_tree, other_v, other_p = pilot.bvh_for(static)
                    legacy_hits = 0
                    for mine, theirs in legacy_tree.overlap(other_tree):
                        if pilot.triangle_contact_points(
                            [legacy_v[i] for i in legacy_p[mine]],
                            [other_v[i] for i in other_p[theirs]],
                        ):
                            legacy_hits += 1
                    if legacy_hits:
                        entry["legacy_contact_poses"] += 1
                        entry["legacy_contact_points"] += legacy_hits

                    # New: two layers.
                    pairs = contact.candidate_pairs(
                        mover_tris, static_tris, mover_broad, static_broad
                    )
                    surface = contact.surface_contact(mover_tris, static_tris, pairs)
                    entry["surface_tangent"] += len(surface[contact.TANGENT])
                    entry["surface_crossing"] += len(surface[contact.CROSSING])
                    for group in (surface[contact.TANGENT], surface[contact.CROSSING]):
                        for hit in group:
                            entry["mover_triangles"].add(hit["mover_triangle"])
                            entry["static_triangles"].add(hit["static_triangle"])
                            for point in hit["points"]:
                                vector = Vector(point)
                                radius = math.hypot(
                                    vector.x - centre.x, vector.z - centre.z
                                )
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
                                if (vector - centre).length > bearing:
                                    entry["outside_bearing"] = True

                    for source, tree in (
                        (mover, static_exact),
                        (static, mover_exact),
                    ):
                        depth = contact.material_penetration(
                            [
                                source.matrix_world @ vertex.co
                                for vertex in source.data.vertices
                            ],
                            tree,
                        )
                        for key in (
                            "boundary_vertices",
                            "within_tolerance_vertices",
                            "penetrating_vertices",
                        ):
                            entry[key] = max(entry[key], depth[key])
                        entry["deepest_intrusion_mm"] = max(
                            entry["deepest_intrusion_mm"],
                            depth["deepest_intrusion_mm"],
                        )
    finally:
        if linear:
            pivot.location = base
        else:
            pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return {label: finish_pair(entry) for label, entry in results.items()}


def meters(project_root):
    """System 1: the needle against the solid polygon plate, D-9's evidence."""
    entries = {}
    for key in ("MeterRound", "MeterMedium", "MeterLarge"):
        source = (
            project_root
            / "ArtSource/Blender/ThemeHardSurfaceV6/KineticSafety"
            / f"BL_{key}_KineticSafety_V6_Retopo.blend"
        )
        open_blend(source)
        root = bpy.data.objects[f"PF_Visual_{key}_KineticSafety_V6"]
        pivot = bpy.data.objects["needle_pivot"]
        needle = bpy.data.objects["needle"]
        plate = bpy.data.objects["kinetic_polygon_bezel"]
        centre = pivot.matrix_world.translation.copy()
        hub = max(
            abs((needle.matrix_world @ vertex.co).x - centre.x)
            for vertex in needle.data.vertices
        )
        poses = [-55.0 + 110.0 * index / 22 for index in range(23)]

        joined = sweep_pairs(pivot, [needle], [plate], centre, hub * 1.7, poses)
        pieces = splitter.components_of(needle)
        for piece in pieces:
            pilot.parent_keep_world(piece, pivot)
        needle.hide_viewport = True
        bpy.context.view_layer.update()
        facts = {p.name: splitter.describe(p, centre) for p in pieces}
        blade = max(pieces, key=lambda p: facts[p.name]["length_mm"][2])
        components = sweep_pairs(pivot, pieces, [plate], centre, hub * 1.7, poses)

        entries[f"KineticSafety/{key}"] = {
            "source": str(source.relative_to(project_root)),
            "sha256": digest(source),
            "kind": "production baseline",
            "poses": {"count": len(poses), "degrees": [poses[0], poses[-1]]},
            "bearing_radius": round(hub * 1.7, 6),
            "component_facts": facts,
            "blade_component": blade.name,
            "joined": joined,
            "components": components,
            "d9_evidence": {
                "blade_penetrating_vertices": components.get(
                    f"{blade.name} x kinetic_polygon_bezel", {}
                ).get("penetrating_vertices", 0),
                "blade_verdict": components.get(
                    f"{blade.name} x kinetic_polygon_bezel", {}
                ).get("verdict"),
                "hub_verdicts": {
                    label: entry["verdict"]
                    for label, entry in components.items()
                    if not label.startswith(blade.name)
                },
            },
        }
    return entries


def ticks(project_root):
    """System 2: D-3, baseline against the published D3 candidate."""
    entries = {}
    for key in ("MeterMedium", "MeterLarge"):
        for kind, source in (
            (
                "production baseline",
                project_root
                / "ArtSource/Blender/ThemeHardSurfaceV6/KineticSafety"
                / f"BL_{key}_KineticSafety_V6_Retopo.blend",
            ),
            (
                "D3 candidate",
                project_root
                / "ArtSource/Blender/BrushUp/Opus5/KineticSafety"
                / f"BL_{key}_KineticSafety_V6_Opus5_D3_Retopo.blend",
            ),
        ):
            if not source.is_file():
                continue
            open_blend(source)
            root = bpy.data.objects[f"PF_Visual_{key}_KineticSafety_V6"]
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
            poses = [-55.0 + 110.0 * index / 22 for index in range(23)]
            entries[f"KineticSafety/{key} [{kind}]"] = {
                "source": str(source.relative_to(project_root)),
                "sha256": digest(source),
                "kind": kind,
                "poses": {"count": len(poses), "degrees": [poses[0], poses[-1]]},
                "clearance_contract_mm": {"MeterMedium": 1.4, "MeterLarge": 2.1}[key],
                "pairs": sweep_pairs(
                    pivot, [needle], endpoints, centre, hub * 1.7, poses
                ),
            }
    return entries


def toggle_ring(project_root):
    """System 3: D-5, with the legacy axle and with it removed."""
    entries = {}
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6/KineticSafety"
        / "BL_Toggle_KineticSafety_V6_Retopo.blend"
    )
    poses = [56.0 * index / 26 for index in range(27)]
    for kind in ("with legacy axle", "axle component removed"):
        open_blend(source)
        root = bpy.data.objects["PF_Visual_Toggle_KineticSafety_V6"]
        pivot = bpy.data.objects["switch_pivot"]
        switch = bpy.data.objects["switch"]
        ring = bpy.data.objects["KineticSafety_toggle_v6_fixed_retaining_ring"]
        centre = pivot.matrix_world.translation.copy()
        movers = [switch]
        if kind == "axle component removed":
            pieces = splitter.components_of(switch)
            for piece in pieces:
                pilot.parent_keep_world(piece, pivot)
            facts = {p.name: splitter.describe(p, centre) for p in pieces}
            axle = min(
                (name for name, f in facts.items() if f["longest_axis"] == "X"),
                key=lambda name: facts[name]["distance_from_pivot_mm"],
            )
            doomed = bpy.data.objects[axle]
            pieces = [p for p in pieces if p is not doomed]
            bpy.data.objects.remove(doomed, do_unlink=True)
            switch.hide_viewport = True
            bpy.context.view_layer.update()
            movers = pieces
        entries[f"KineticSafety/Toggle [{kind}]"] = {
            "source": str(source.relative_to(project_root)),
            "sha256": digest(source),
            "kind": kind,
            "poses": {"count": len(poses), "degrees": [poses[0], poses[-1]]},
            "pairs": sweep_pairs(
                pivot, movers, [ring], centre, 0.026, poses, rotate_axis=0
            ),
        }
    return entries


def slider(project_root):
    """System 4: the PowerSlider sliding interface behind the named allowance."""
    source = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5/KineticSafety"
        / "BL_PowerSlider_KineticSafety_V6_Opus5_B4_Retopo.blend"
    )
    if not source.is_file():
        return {}
    open_blend(source)
    root = bpy.data.objects["PF_Visual_PowerSlider_KineticSafety_V6"]
    pivot = bpy.data.objects["slider_travel"]
    bridge = bpy.data.objects["KineticSafety_slider_v6_handle_bridge"]
    rails = [
        obj for obj in pilot.meshes_under(root) if obj.name.startswith("kinetic_slider_rail")
    ]
    centre = pivot.matrix_world.translation.copy()
    poses = [-0.09 + 0.18 * index / 36 for index in range(37)]
    return {
        "KineticSafety/PowerSlider [B4 candidate]": {
            "source": str(source.relative_to(project_root)),
            "sha256": digest(source),
            "kind": "B4 candidate",
            "poses": {"count": len(poses), "travel_m": [poses[0], poses[-1]]},
            "allowance": "allowed_interface_pairs, volume limit 0.005, depth 0.01 mm",
            "pairs": sweep_pairs(
                pivot, [bridge], rails, centre, 0.0, poses, rotate_axis=2, linear=True
            ),
        }
    }


SYSTEMS = {
    "meters": meters,
    "d3_ticks": ticks,
    "d5_toggle_ring": toggle_ring,
    "powerslider": slider,
}


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = preflight(project_root)

    started = time.perf_counter()
    systems = {}
    timings = {}
    for name in args.systems or SYSTEMS:
        begin = time.perf_counter()
        systems[name] = SYSTEMS[name](project_root)
        timings[name] = round(time.perf_counter() - begin, 3)
        print(f"[Opus5MigrationM1] {name}: {timings[name]}s")

    deltas = {}
    for system in systems.values():
        for model in system.values():
            groups = [model.get("pairs", {}), model.get("joined", {}), model.get("components", {})]
            for group in groups:
                for entry in group.values():
                    deltas[entry["delta"]] = deltas.get(entry["delta"], 0) + 1

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M1",
                "note": (
                    "Read-only (alignment 90.1). The legacy test and the new "
                    "two-layer test run side by side over the same poses; "
                    "nothing is replaced and no Blend or existing audit is "
                    "written."
                ),
                "preflight": gate,
                "tolerances": {
                    "tangent_m": contact.TANGENT_TOLERANCE_M,
                    "penetration_mm": contact.PENETRATION_TOLERANCE_MM,
                    "boundary_mm": contact.BOUNDARY_TOLERANCE_MM,
                    "broad_phase_m": contact.BROAD_PHASE_EPSILON_M,
                },
                "systems": systems,
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
    print(f"[Opus5MigrationM1] deltas {deltas} -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
