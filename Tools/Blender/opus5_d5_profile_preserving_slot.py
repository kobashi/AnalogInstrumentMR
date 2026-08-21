"""Phase M2b: can the slot be cut from the shipped ring instead of rebuilt?

Alignment 98.3. Phase M2a proved the `arc_band` stand-in loses the production
cross-section and facet count, so every retention figure measured on it
describes the stand-in. This cuts the sector out of the production mesh itself
with an EXACT Boolean and asks whether the surfaces outside the cut survive.

Two measurement bugs from M2a are fixed here, both found by Codex in 98.2:

* A gap that straddles azimuth 0 was reported as two runs, so a 36 deg opening
  read as 18.49 deg. Runs are now joined circularly.
* Coverage multiplied a sample count by the nominal step even though the slot
  boundary samples are not on that step, overstating it by up to 1.5 deg.
  Coverage is now integrated over angular intervals.

Lip overlap is also no longer read from one mid-depth section. It is measured
at every profile change point and just inside both ends of the ring's depth
band, and the retained sector's minimum is taken across all of them - a
profiled ring's worst section is not its middle.

Per 98.1 the lip figure is a mechanical-plausibility geometry proxy for an MR
visual asset. It is not a retention-force guarantee and is not written as one.

Read-only. No Blend is saved and no existing report is modified.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_profile_preserving_slot.py -- \
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
import opus5_contact_migration_m1 as m1
import opus5_d5_toggle_axle_proposal as splitter


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d5_profile_preserving_slot_survey.json"
SLOT_SURVEY = "ArtSource/Blender/BrushUp/Opus5/d5_slot_proposal.json"

AZIMUTH_STEP_DEG = 0.25
# A ray sent exactly along a cut plane lies inside that face and reports a
# grazing hit at an arbitrary radius. Exactly on the cut there is no material,
# so such a hit is discarded rather than believed.
GRAZING_COSINE = 1e-3
SEARCH_STEP_DEG = 0.5
SEARCH_FLOOR_DEG = 4.0
CUT_MARGIN_MM = 1.0
DEVIATION_LIMIT_MM = 0.01
LIP_RATIO_FLOOR = 0.95
LIP_DROP_LIMIT_MM = 0.10
POSES = [56.0 * index / 26 for index in range(27)]
PROXY_POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append")
    return parser.parse_args(args)


def azimuth_of(point, centre):
    return math.degrees(math.atan2(point.x - centre.x, point.z - centre.z)) % 360.0


def signed_from_zero(degrees):
    """Azimuth as -180..180 so the sector across 0 is a single interval."""
    return degrees - 360.0 if degrees > 180.0 else degrees


def tree_of(obj):
    from mathutils.bvhtree import BVHTree

    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    return BVHTree.FromPolygons(
        [tuple(matrix @ vertex.co) for vertex in obj.data.vertices],
        [tuple(t.vertices) for t in obj.data.loop_triangles],
        all_triangles=True,
        epsilon=0.0,
    )


def mesh_health(obj):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.edges.ensure_lookup_table()
    mesh.faces.ensure_lookup_table()
    boundary = sum(1 for edge in mesh.edges if len(edge.link_faces) < 2)
    non_manifold = sum(1 for edge in mesh.edges if len(edge.link_faces) > 2)
    degenerate = sum(1 for face in mesh.faces if face.calc_area() <= 1e-12)
    volume = mesh.calc_volume(signed=True)
    mesh.free()
    obj.data.calc_loop_triangles()
    return {
        "boundary_edges": boundary,
        "non_manifold_edges": non_manifold,
        "degenerate_faces": degenerate,
        "closed": boundary == 0 and non_manifold == 0,
        "normals_outward": volume > 0.0,
        "signed_volume_mm3": round(volume * 1e9, 4),
        "loop_triangles": len(obj.data.loop_triangles),
        "material_slots": [m.name if m else None for m in obj.data.materials],
    }


def wedge_cutter(centre, half_angle, reach, low, high):
    """A closed prism spanning the sector to be removed, centred on azimuth 0."""
    mesh = bpy.data.meshes.new("opus5_slot_cutter")
    obj = bpy.data.objects.new("opus5_slot_cutter", mesh)
    bpy.context.collection.objects.link(obj)
    arc = [-half_angle + 2.0 * half_angle * i / 8 for i in range(9)]
    rim = [
        (
            centre.x + reach * math.sin(math.radians(a)),
            centre.z + reach * math.cos(math.radians(a)),
        )
        for a in arc
    ]
    verts = [(centre.x, low, centre.z), (centre.x, high, centre.z)]
    verts += [(x, low, z) for x, z in rim]
    verts += [(x, high, z) for x, z in rim]
    count = len(rim)
    faces = []
    for i in range(count - 1):
        lower_a, lower_b = 2 + i, 2 + i + 1
        upper_a, upper_b = 2 + count + i, 2 + count + i + 1
        faces.append((0, lower_b, lower_a))
        faces.append((1, upper_a, upper_b))
        faces.append((lower_a, lower_b, upper_b, upper_a))
    faces.append((0, 2, 2 + count, 1))
    faces.append((0, 1, 2 + count + count - 1, 2 + count - 1))
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    return obj


def cut_slot(ring, centre, half_angle):
    """Remove the sector from the production mesh. Returns a new object."""
    points = [ring.matrix_world @ vertex.co for vertex in ring.data.vertices]
    reach = max(math.hypot(p.x - centre.x, p.z - centre.z) for p in points) * 1.5
    low = min(p.y for p in points) - 0.01
    high = max(p.y for p in points) + 0.01
    cutter = wedge_cutter(centre, half_angle, reach, low, high)
    # Without this the Boolean appends an empty slot for the cutter's own
    # (absent) material and the result no longer matches production.
    for material in ring.data.materials:
        cutter.data.materials.append(material)

    cut = ring.copy()
    cut.data = ring.data.copy()
    cut.name = f"{ring.name}_slotted"
    bpy.context.collection.objects.link(cut)
    modifier = cut.modifiers.new("slot", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.object = cutter
    modifier.solver = "EXACT"
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(cut.evaluated_get(depsgraph))
    cut.modifiers.remove(modifier)
    old = cut.data
    cut.data = baked
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.context.view_layer.update()
    return cut


def surface_deviation(cut, production, centre, half_angle):
    """Nearest-surface distance for geometry away from the cut, both ways.

    Topology changed, so vertex indices mean nothing here; only distance to the
    other surface does (alignment 98.3-2).
    """
    production_tree = tree_of(production)
    cut_tree = tree_of(cut)
    points = [production.matrix_world @ v.co for v in production.data.vertices]
    outer = max(math.hypot(p.x - centre.x, p.z - centre.z) for p in points)
    margin_deg = math.degrees((CUT_MARGIN_MM / 1000.0) / max(outer, 1e-9))

    def away_from_cut(point):
        signed = abs(signed_from_zero(azimuth_of(point, centre)))
        return signed > half_angle + margin_deg

    forward = []
    for vertex in cut.data.vertices:
        world = cut.matrix_world @ vertex.co
        if not away_from_cut(world):
            continue
        _, _, _, distance = production_tree.find_nearest(world)
        forward.append(distance or 0.0)
    backward = []
    for world in points:
        if not away_from_cut(world):
            continue
        _, _, _, distance = cut_tree.find_nearest(world)
        backward.append(distance or 0.0)
    return {
        "cut_margin_mm": CUT_MARGIN_MM,
        "margin_deg": round(margin_deg, 4),
        "slotted_to_production": {
            "samples": len(forward),
            "max_mm": round(max(forward) * 1000.0, 8) if forward else None,
        },
        "production_to_slotted": {
            "samples": len(backward),
            "max_mm": round(max(backward) * 1000.0, 8) if backward else None,
        },
        "max_deviation_mm": round(
            max(max(forward, default=0.0), max(backward, default=0.0)) * 1000.0, 8
        ),
    }


def section_heights(ring, centre):
    """Profile change points, plus just inside both ends of the depth band."""
    points = [ring.matrix_world @ v.co for v in ring.data.vertices]
    values = sorted({round(p.y, 7) for p in points})
    low, high = values[0], values[-1]
    # The band ends are moved inside so the ray does not run along the end cap,
    # but every interior profile change point is kept exactly where it is - a
    # chamfer close to an end is still a section that has to be measured
    # (alignment 98.3-5).
    inset = max((high - low) * 0.02, 1e-5)
    heights = {round(low + inset, 7), round(high - inset, 7)}
    heights.update(v for v in values if low < v < high)
    return sorted(heights)


def lip_profile(ring, joint, centre, half_angle=None, heights=None):
    """Lip overlap over azimuth, taking the ring's tightest section per azimuth.

    The ball is a body of revolution about the ring axis, so what stops it
    leaving is the ring's smallest aperture anywhere along its depth against the
    ball's widest radius - not the ring and the ball compared at one shared
    height. For a profiled ring the tightest section is not the middle one
    (alignment 98.2-5), so every profile change point and both band ends are
    measured and the minimum radius per azimuth is taken across all of them.
    """
    ring_tree = tree_of(ring)
    heights = heights if heights is not None else section_heights(ring, centre)
    ball_radius = max(
        math.hypot(
            (joint.matrix_world @ vertex.co).x - centre.x,
            (joint.matrix_world @ vertex.co).z - centre.z,
        )
        for vertex in joint.data.vertices
    )

    azimuths = [i * AZIMUTH_STEP_DEG for i in range(int(360.0 / AZIMUTH_STEP_DEG))]
    if half_angle is not None:
        for edge in (half_angle, 360.0 - half_angle):
            azimuths.extend([edge - 0.01, edge, edge + 0.01])
    azimuths = sorted({round(v % 360.0, 4) for v in azimuths})

    grazing = {}
    per_section_radius = {str(height): {} for height in heights}
    tightest = {}
    overlaps = {}
    for degrees in azimuths:
        angle = math.radians(degrees)
        direction = Vector((math.sin(angle), 0.0, math.cos(angle)))
        best = None
        for height in heights:
            origin = Vector((centre.x, height, centre.z))
            _, normal, _, radius = ring_tree.ray_cast(origin, direction)
            if normal is not None and abs(normal.dot(direction)) < GRAZING_COSINE:
                radius = None
                grazing[degrees] = grazing.get(degrees, 0) + 1
            per_section_radius[str(height)][degrees] = (
                round(radius, 7) if radius is not None else None
            )
            if radius is not None and (best is None or radius < best[0]):
                best = (radius, height)
        if best is None:
            tightest[degrees] = None
            overlaps[degrees] = None
            continue
        tightest[degrees] = {"radius": round(best[0], 7), "section_y": best[1]}
        overlaps[degrees] = round((ball_radius - best[0]) * 1000.0, 6)

    retaining = {
        degrees: value is not None and value > 0.0
        for degrees, value in overlaps.items()
    }
    values = [v for v in overlaps.values() if v is not None and v > 0.0]
    minimum = min(values) if values else None
    worst_azimuth = (
        min((d for d, v in overlaps.items() if v == minimum), default=None)
        if minimum is not None
        else None
    )
    per_section_minimum = {}
    for height in heights:
        radii = [r for r in per_section_radius[str(height)].values() if r is not None]
        per_section_minimum[str(height)] = {
            "present_azimuths": len(radii),
            "max_inner_radius": round(max(radii), 7) if radii else None,
            "lip_overlap_at_widest_mm": (
                round((ball_radius - max(radii)) * 1000.0, 6) if radii else None
            ),
        }
    return {
        "ball_max_radius": round(ball_radius, 7),
        "sections_measured": len(heights),
        "section_heights_y": heights,
        "azimuth_step_deg": AZIMUTH_STEP_DEG,
        "azimuths_sampled": len(azimuths),
        "boundary_samples_added": half_angle is not None,
        "grazing_hits_discarded": {
            "azimuths": len(grazing),
            "cosine_limit": GRAZING_COSINE,
            "detail": {str(k): v for k, v in sorted(grazing.items())},
        },
        "min_lip_overlap_mm": minimum,
        "worst_azimuth_deg": worst_azimuth,
        "worst_section_y": (
            tightest[worst_azimuth]["section_y"] if worst_azimuth is not None else None
        ),
        "governing_sections": sorted(
            {
                entry["section_y"]
                for entry in tightest.values()
                if entry is not None
            }
        ),
        "per_section": per_section_minimum,
        "coverage": integrate_coverage(azimuths, retaining),
        "lip_overlap_by_azimuth": overlaps,
    }


def integrate_coverage(azimuths, retaining):
    """Angular measure, not a sample count, with 0 deg joined (alignment 98.2)."""
    ordered = sorted(azimuths)
    covered = 0.0
    gap_runs = []
    current = None
    for index, degrees in enumerate(ordered):
        following = ordered[(index + 1) % len(ordered)]
        width = (following - degrees) % 360.0
        if width <= 0.0:
            width = 360.0
        here, there = retaining[degrees], retaining[following]
        covered += width if here and there else (width * 0.5 if here or there else 0.0)
        if not here:
            current = width if current is None else current + width
        elif current is not None:
            gap_runs.append(current)
            current = None
    if current is not None:
        # The run that was still open wraps into the one that opened the list.
        if gap_runs and not retaining[ordered[0]]:
            gap_runs[0] += current
        else:
            gap_runs.append(current)
    return {
        "coverage_deg": round(covered, 4),
        "total_gap_deg": round(360.0 - covered, 4),
        "largest_gap_deg": round(max(gap_runs), 4) if gap_runs else 0.0,
        "gap_runs": len(gap_runs),
        "method": "angular intervals, circular; not a sample count",
    }


def self_test_coverage():
    """The 98.2 bugs, as cases that fail if either comes back.

    Tolerance is the sampling quantisation itself: each gap edge can land up to
    one step away from the true boundary, so a gap with two edges can be off by
    two steps and no more.
    """
    def sector(half, step=AZIMUTH_STEP_DEG, boundary=True):
        azimuths = [i * step for i in range(int(360.0 / step))]
        if boundary:
            for edge in (half, 360.0 - half):
                azimuths.extend([edge - 0.01, edge, edge + 0.01])
        azimuths = sorted({round(v % 360.0, 4) for v in azimuths})
        return azimuths, {
            d: abs(signed_from_zero(d)) > half for d in azimuths
        }

    cases = []
    for half in (4.0, 18.0, 24.0, 90.0):
        azimuths, retaining = sector(half)
        cases.append((f"sector across 0, half {half}", azimuths, retaining,
                      2.0 * half, 2.0 * half, 1))
    plain = [i * AZIMUTH_STEP_DEG for i in range(int(360.0 / AZIMUTH_STEP_DEG))]
    cases.append((
        "sector 100-130, no wrap", plain,
        {d: not (100.0 <= d <= 130.0) for d in plain}, 30.0, 30.0, 1,
    ))
    cases.append((
        "two gaps, one wraps", plain,
        {
            d: not (abs(signed_from_zero(d)) <= 10.0 or 100.0 <= d <= 130.0)
            for d in plain
        },
        50.0, 30.0, 2,
    ))
    cases.append(("full ring", plain, {d: True for d in plain}, 0.0, 0.0, 0))

    results = []
    for name, azimuths, retaining, total, largest, runs in cases:
        measured = integrate_coverage(azimuths, retaining)
        slack = AZIMUTH_STEP_DEG * 2.0 * max(runs, 1)
        passed = (
            abs(measured["total_gap_deg"] - total) <= slack
            and abs(measured["largest_gap_deg"] - largest) <= AZIMUTH_STEP_DEG * 2.0
            and measured["gap_runs"] == runs
        )
        results.append(
            {
                "case": name,
                "expected_total_gap_deg": total,
                "measured_total_gap_deg": measured["total_gap_deg"],
                "expected_largest_gap_deg": largest,
                "measured_largest_gap_deg": measured["largest_gap_deg"],
                "expected_gap_runs": runs,
                "measured_gap_runs": measured["gap_runs"],
                "tolerance_deg": round(slack, 4),
                "passed": passed,
            }
        )
    return {
        "cases": len(results),
        "all_passed": all(item["passed"] for item in results),
        "detail": results,
    }


def toggle_scene(project_root, theme):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_Toggle_{theme}_V6_Retopo.blend"
    )
    m1.open_blend(source)
    root = bpy.data.objects[f"PF_Visual_Toggle_{theme}_V6"]
    pivot = bpy.data.objects["switch_pivot"]
    switch = bpy.data.objects["switch"]
    ring = next(
        o for o in pilot.meshes_under(root) if "retaining_ring" in o.name.lower()
    )
    joint = next(o for o in pilot.meshes_under(root) if "hemisphere" in o.name.lower())
    centre = pivot.matrix_world.translation.copy()

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
    return {
        "source": source,
        "pivot": pivot,
        "ring": ring,
        "joint": joint,
        "centre": centre,
        "movers": pieces,
        "axle_removed": axle,
    }


def clear_over_poses(scene, ring):
    pairs = m1.sweep_pairs(
        scene["pivot"], scene["movers"], [ring], scene["centre"], 0.026,
        POSES, rotate_axis=0,
    )
    crossing = sum(entry["surface_crossing"] for entry in pairs.values())
    penetrating = sum(entry["penetrating_vertices"] for entry in pairs.values())
    deepest = max(
        (entry["deepest_intrusion_mm"] for entry in pairs.values()), default=0.0
    )
    return {
        "poses": len(POSES),
        "pair_labels": sorted(pairs),
        "surface_crossing": crossing,
        "penetrating_vertices": penetrating,
        "deepest_intrusion_mm": round(deepest, 6),
        "verdicts": {label: entry["verdict"] for label, entry in pairs.items()},
        "clear": crossing == 0 and penetrating == 0,
        "pairs": pairs,
    }


def search_minimum_slot(project_root, theme, start_half_angle):
    """Step down from the approved slot until the sweep stops being clear."""
    trail = []
    smallest = None
    half = start_half_angle
    while half >= SEARCH_FLOOR_DEG:
        scene = toggle_scene(project_root, theme)
        cut = cut_slot(scene["ring"], scene["centre"], half)
        scene["ring"].hide_viewport = True
        cut.parent = scene["ring"].parent
        bpy.context.view_layer.update()
        health = mesh_health(cut)
        result = clear_over_poses(scene, cut)
        trail.append(
            {
                "half_angle_deg": round(half, 3),
                "clear": result["clear"],
                "surface_crossing": result["surface_crossing"],
                "penetrating_vertices": result["penetrating_vertices"],
                "closed": health["closed"],
            }
        )
        if not (result["clear"] and health["closed"]):
            break
        smallest = round(half, 3)
        half -= SEARCH_STEP_DEG
    return smallest, trail


def survey_theme(project_root, theme, start_half_angle):
    smallest, trail = search_minimum_slot(project_root, theme, start_half_angle)
    half = smallest if smallest is not None else start_half_angle

    scene = toggle_scene(project_root, theme)
    ring, joint, centre = scene["ring"], scene["joint"], scene["centre"]
    heights = section_heights(ring, centre)
    baseline_health = mesh_health(ring)
    baseline_lip = lip_profile(ring, joint, centre, None, heights)

    cut = cut_slot(ring, centre, half)
    deviation = surface_deviation(cut, ring, centre, half)
    cut_health = mesh_health(cut)
    ring.hide_viewport = True
    cut.parent = ring.parent
    bpy.context.view_layer.update()
    slot_lip = lip_profile(cut, joint, centre, half, heights)
    sweep = clear_over_poses(scene, cut)

    proxy_by_pose = {}
    for label, degrees in PROXY_POSES:
        scene["pivot"].rotation_euler[0] = math.radians(degrees)
        bpy.context.view_layer.update()
        measured = lip_profile(cut, joint, centre, half, heights)
        proxy_by_pose[label] = {
            "degrees": degrees,
            "ball_max_radius": measured["ball_max_radius"],
            "min_lip_overlap_mm": measured["min_lip_overlap_mm"],
            "worst_section_y": measured["worst_section_y"],
            "coverage_deg": measured["coverage"]["coverage_deg"],
        }
    scene["pivot"].rotation_euler[0] = 0.0
    bpy.context.view_layer.update()

    base_min = baseline_lip["min_lip_overlap_mm"] or 0.0
    slot_min = slot_lip["min_lip_overlap_mm"] or 0.0
    worst_gap = slot_lip["coverage"]["total_gap_deg"]
    contract = {
        "profile_preservation": {
            "limit_mm": DEVIATION_LIMIT_MM,
            "measured_mm": deviation["max_deviation_mm"],
            "pass": deviation["max_deviation_mm"] <= DEVIATION_LIMIT_MM,
        },
        "collision": {
            "requirement": "27 poses, crossing 0 and penetrating vertices 0",
            "surface_crossing": sweep["surface_crossing"],
            "penetrating_vertices": sweep["penetrating_vertices"],
            "pass": sweep["clear"],
        },
        "lip_proxy": {
            "baseline_mm": round(base_min, 6),
            "slotted_mm": round(slot_min, 6),
            "ratio": round(slot_min / base_min, 6) if base_min else None,
            "drop_mm": round(base_min - slot_min, 6),
            "pass": (
                base_min > 0.0
                and slot_min / base_min >= LIP_RATIO_FLOOR
                and (base_min - slot_min) <= LIP_DROP_LIMIT_MM
            ),
        },
        "intended_opening": {
            "reported_half_angle_deg": half,
            "expected_total_gap_deg": round(half * 2.0, 4),
            "measured_total_gap_deg": round(worst_gap, 4),
            "difference_deg": round(abs(worst_gap - half * 2.0), 4),
            "pass": abs(worst_gap - half * 2.0) <= 1.0,
        },
        "mesh_health": {
            "closed": cut_health["closed"],
            "normals_outward": cut_health["normals_outward"],
            "degenerate_faces": cut_health["degenerate_faces"],
            "pass": (
                cut_health["closed"]
                and cut_health["normals_outward"]
                and cut_health["degenerate_faces"] == 0
            ),
        },
    }
    contract["all_pass"] = all(item["pass"] for item in contract.values())

    return {
        "source": str(scene["source"].relative_to(project_root)),
        "sha256": m1.digest(scene["source"]),
        "axle_component_removed": scene["axle_removed"],
        "start_half_angle_deg": start_half_angle,
        "smallest_clear_half_angle_deg": smallest,
        "search_step_deg": SEARCH_STEP_DEG,
        "search_trail": trail,
        "triangles": {
            "production_ring": baseline_health["loop_triangles"],
            "slotted_ring": cut_health["loop_triangles"],
            "delta": cut_health["loop_triangles"] - baseline_health["loop_triangles"],
        },
        "material_slots": {
            "production": baseline_health["material_slots"],
            "slotted": cut_health["material_slots"],
            "preserved": baseline_health["material_slots"]
            == cut_health["material_slots"],
        },
        "mesh_health": {"production": baseline_health, "slotted": cut_health},
        "surface_deviation": deviation,
        "lip_overlap": {"production": baseline_lip, "slotted": slot_lip},
        "proxy_by_pose": proxy_by_pose,
        "collision_sweep": {
            key: value for key, value in sweep.items() if key != "pairs"
        },
        "provisional_contract": contract,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)
    survey = json.loads((project_root / SLOT_SURVEY).read_text())
    angles = {
        theme: (payload.get("smallest_clean_slot") or {}).get("slot_half_angle_deg")
        for theme, payload in survey["themes"].items()
    }

    coverage_test = self_test_coverage()
    if not coverage_test["all_passed"]:
        failed = [item["case"] for item in coverage_test["detail"] if not item["passed"]]
        raise SystemExit(f"[Opus5SlotM2b] coverage self-test failed: {failed}")
    print(f"[Opus5SlotM2b] coverage self-test: {coverage_test['cases']} cases PASS")

    started = time.perf_counter()
    themes = {}
    for theme in args.themes or angles:
        begin = time.perf_counter()
        themes[theme] = survey_theme(project_root, theme, angles[theme])
        entry = themes[theme]
        print(
            f"[Opus5SlotM2b] {theme}: smallest clear +-"
            f"{entry['smallest_clear_half_angle_deg']} deg, deviation "
            f"{entry['surface_deviation']['max_deviation_mm']} mm, lip "
            f"{entry['provisional_contract']['lip_proxy']['baseline_mm']} -> "
            f"{entry['provisional_contract']['lip_proxy']['slotted_mm']} mm, "
            f"contract {entry['provisional_contract']['all_pass']}, "
            f"{round(time.perf_counter() - begin, 1)}s"
        )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2b",
                "note": (
                    "Read-only feasibility (alignment 98.3). The slot is cut "
                    "from the production mesh with an EXACT Boolean; arc_band "
                    "is not used. No Blend is saved."
                ),
                "proxy_status": (
                    "lip overlap is a mechanical-plausibility geometry proxy "
                    "for an MR visual asset, not a retention-force guarantee "
                    "(alignment 98.1)"
                ),
                "preflight": gate,
                "coverage_self_test": coverage_test,
                "start_half_angles": angles,
                "themes": themes,
                "contract_summary": {
                    theme: entry["provisional_contract"]["all_pass"]
                    for theme, entry in themes.items()
                },
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5SlotM2b] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
