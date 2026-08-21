"""Phase M2a: how much ball does the slotted ring still hold?

Alignment 96.3. The slot's collision clearance is settled, but "retention" has
only ever been argued from a sampled occupied fraction, and Phase M1c showed
that figure moves by up to 0.39 with the grid. So retention is redefined here
in terms a ring and a ball actually have.

A retaining ring holds a ball by overhanging it: where the ring's inner edge
sits at a smaller radius than the ball's surface at that height, the ball
cannot pass. That gives three measurements with different standing:

* **lip overlap depth** - direct mechanical retention. How far the ring
  overhangs the ball, per azimuth, in millimetres. A ball escapes where this
  reaches zero.
* **angular coverage** - a proxy. Retention resists pull-out in the directions
  it covers; a gap says nothing about the covered directions but bounds which
  way the joint could leave.
* **covered fraction seen from the front** - visual only. It says how the part
  reads, not what it holds.

A Boolean intersection volume is attempted as an auxiliary figure and is only
reported when both meshes are closed and manifold - and never as a pass/fail on
its own (alignment 96.3-4).

Read-only. No Blend is saved and no existing report is modified.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_retention_metric_survey.py -- \
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
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact_migration_m1 as m1
import opus5_d5_toggle_axle_proposal as splitter


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d5_retention_metric_survey.json"
SLOT_SURVEY = "ArtSource/Blender/BrushUp/Opus5/d5_slot_proposal.json"

# Half a degree everywhere, and the slot edges exactly, so the worst azimuth is
# never one the sampler stepped over.
AZIMUTH_STEP_DEG = 0.5


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append")
    return parser.parse_args(args)


def mesh_health(obj):
    """Closed, manifold and consistently wound? Decides what may be measured."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.edges.ensure_lookup_table()
    boundary = sum(1 for edge in mesh.edges if len(edge.link_faces) < 2)
    non_manifold = sum(1 for edge in mesh.edges if len(edge.link_faces) > 2)
    volume = mesh.calc_volume(signed=True)
    mesh.free()
    return {
        "boundary_edges": boundary,
        "non_manifold_edges": non_manifold,
        "closed": boundary == 0 and non_manifold == 0,
        "signed_volume_mm3": round(volume * 1e9, 4),
        "normals_outward": volume > 0.0,
    }


def radial_profile(obj, centre, axis_y, azimuths):
    """First surface radius outward from the axis, per azimuth. None = no material."""
    from mathutils.bvhtree import BVHTree

    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    tree = BVHTree.FromPolygons(
        [tuple(matrix @ vertex.co) for vertex in obj.data.vertices],
        [tuple(t.vertices) for t in obj.data.loop_triangles],
        all_triangles=True,
        epsilon=0.0,
    )
    profile = {}
    for degrees in azimuths:
        angle = math.radians(degrees)
        direction = Vector((math.sin(angle), 0.0, math.cos(angle)))
        origin = Vector((centre.x, axis_y, centre.z))
        location, _, _, distance = tree.ray_cast(origin, direction)
        profile[round(degrees, 3)] = None if location is None else distance
    return profile


def sphere_radius_in_band(obj, centre, low, high):
    """The ball's largest radius inside the ring's depth band."""
    radii = [
        math.hypot(
            (obj.matrix_world @ vertex.co).x - centre.x,
            (obj.matrix_world @ vertex.co).z - centre.z,
        )
        for vertex in obj.data.vertices
        if low <= (obj.matrix_world @ vertex.co).y <= high
    ]
    return max(radii) if radii else None


def boolean_intersection_volume(ring, joint):
    """Auxiliary only. Returns None if it cannot be computed cleanly."""
    try:
        copy = ring.copy()
        copy.data = ring.data.copy()
        bpy.context.collection.objects.link(copy)
        modifier = copy.modifiers.new("intersect", "BOOLEAN")
        modifier.operation = "INTERSECT"
        modifier.object = joint
        modifier.solver = "EXACT"
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = copy.evaluated_get(depsgraph)
        mesh = bmesh.new()
        mesh.from_mesh(evaluated.to_mesh())
        boundary = sum(1 for edge in mesh.edges if len(edge.link_faces) < 2)
        volume = mesh.calc_volume(signed=True)
        mesh.free()
        evaluated.to_mesh_clear()
        bpy.data.objects.remove(copy, do_unlink=True)
        if boundary:
            return {"available": False, "reason": "boolean result is not closed"}
        return {
            "available": True,
            "volume_mm3": round(abs(volume) * 1e9, 4),
            "solver": "EXACT",
            "status": "auxiliary; never a pass/fail on its own",
        }
    except Exception as error:  # noqa: BLE001 - reported, not raised
        return {"available": False, "reason": str(error)}


def ring_profile(ring, joint, centre):
    """Facet count, cross-section richness and concentricity with the ball.

    The slot is rebuilt with `arc_band`, so whether that rebuild is a faithful
    slot of the shipped ring or only a stand-in has to be on the record next to
    the numbers measured on it.
    """
    points = [ring.matrix_world @ vertex.co for vertex in ring.data.vertices]
    azimuths = sorted(
        {
            round(math.degrees(math.atan2(p.x - centre.x, p.z - centre.z)) % 360.0, 3)
            for p in points
        }
    )
    radii = sorted(
        {round(math.hypot(p.x - centre.x, p.z - centre.z), 6) for p in points}
    )
    joint_points = [joint.matrix_world @ vertex.co for vertex in joint.data.vertices]

    def middle(values, index):
        return (min(v[index] for v in values) + max(v[index] for v in values)) * 0.5

    return {
        "vertices": len(points),
        "distinct_azimuths": len(azimuths),
        "azimuth_step_deg": (
            round(azimuths[1] - azimuths[0], 3) if len(azimuths) > 1 else None
        ),
        "distinct_radii": len(radii),
        "cross_section": (
            "profiled" if len(radii) > 4 else "rectangular"
        ),
        "concentric_with_ball_mm": [
            round((middle(points, i) - middle(joint_points, i)) * 1000.0, 4)
            for i in (0, 2)
        ],
    }


def measure_state(ring, joint, centre, slot_half_angle=None):
    ring_points = [ring.matrix_world @ vertex.co for vertex in ring.data.vertices]
    low = min(point.y for point in ring_points)
    high = max(point.y for point in ring_points)
    mid = (low + high) * 0.5
    ball_radius = sphere_radius_in_band(joint, centre, low, high)

    azimuths = [
        index * AZIMUTH_STEP_DEG
        for index in range(int(360.0 / AZIMUTH_STEP_DEG))
    ]
    if slot_half_angle is not None:
        # The slot edges themselves, and a hair either side of them.
        for edge in (slot_half_angle, 360.0 - slot_half_angle):
            azimuths.extend([edge - 0.01, edge, edge + 0.01])
    azimuths = sorted(set(round(value % 360.0, 3) for value in azimuths))

    profile = radial_profile(ring, centre, mid, azimuths)
    covered = {}
    overlaps = []
    for degrees, radius in profile.items():
        if radius is None or ball_radius is None:
            covered[degrees] = None
            continue
        overlap_mm = (ball_radius - radius) * 1000.0
        covered[degrees] = round(overlap_mm, 6)
        if overlap_mm > 0.0:
            overlaps.append((overlap_mm, degrees))

    retaining = [degrees for degrees, value in covered.items() if value and value > 0.0]
    worst = min(overlaps) if overlaps else None
    gaps = sorted(
        degrees for degrees, value in covered.items() if not value or value <= 0.0
    )
    return {
        "ring_depth_band_y": [round(low, 6), round(high, 6)],
        "measured_at_y": round(mid, 6),
        "ball_radius_in_band": round(ball_radius, 6) if ball_radius else None,
        "azimuth_step_deg": AZIMUTH_STEP_DEG,
        "azimuths_sampled": len(azimuths),
        "slot_edges_sampled": slot_half_angle is not None,
        "direct_mechanical_retention": {
            "min_lip_overlap_mm": round(worst[0], 6) if worst else None,
            "worst_azimuth_deg": worst[1] if worst else None,
            "meaning": "how far the ring overhangs the ball; 0 is an escape path",
        },
        "proxy_angular_coverage": {
            "retaining_azimuths": len(retaining),
            "coverage_deg": round(len(retaining) * AZIMUTH_STEP_DEG, 3),
            "largest_gap_deg": largest_gap(gaps),
            "meaning": "which directions are held; a proxy, not the hold itself",
        },
        "visual_coverage": {
            "ring_present_fraction": round(
                sum(1 for value in profile.values() if value is not None)
                / max(len(profile), 1),
                6,
            ),
            "meaning": "how the part reads from the front; not a mechanical figure",
        },
        "lip_overlap_by_azimuth": covered,
    }


def largest_gap(gaps):
    if not gaps:
        return 0.0
    runs = []
    start = previous = gaps[0]
    for degrees in gaps[1:]:
        if degrees - previous <= AZIMUTH_STEP_DEG + 1e-6:
            previous = degrees
            continue
        runs.append(previous - start + AZIMUTH_STEP_DEG)
        start = previous = degrees
    runs.append(previous - start + AZIMUTH_STEP_DEG)
    return round(max(runs), 3)


def survey_theme(project_root, theme, slot_half_angle):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_Toggle_{theme}_V6_Retopo.blend"
    )
    states = {}
    for state in ("production ring", "slot proposal"):
        m1.open_blend(source)
        root = bpy.data.objects[f"PF_Visual_Toggle_{theme}_V6"]
        pivot = bpy.data.objects["switch_pivot"]
        ring = next(
            o for o in pilot.meshes_under(root) if "retaining_ring" in o.name.lower()
        )
        joint = next(
            o for o in pilot.meshes_under(root) if "hemisphere" in o.name.lower()
        )
        centre = pivot.matrix_world.translation.copy()
        health = {"ring": mesh_health(ring), "joint": mesh_health(joint)}

        if state == "slot proposal":
            points = [ring.matrix_world @ v.co for v in ring.data.vertices]
            inner = min(math.hypot(p.x - centre.x, p.z - centre.z) for p in points)
            outer = max(math.hypot(p.x - centre.x, p.z - centre.z) for p in points)
            y_low = min(p.y for p in points)
            y_high = max(p.y for p in points)
            material = ring.data.materials[0] if ring.data.materials else None
            parent = ring.parent
            bpy.data.objects.remove(ring, do_unlink=True)
            ring = brushup.arc_band(
                "toggle_ring_slotted", inner, outer, slot_half_angle,
                360.0 - slot_half_angle, y_low, y_high, material,
                segments=22, centre_x=centre.x, centre_z=centre.z,
            )
            ring.parent = parent
            bpy.context.view_layer.update()
            health["ring"] = mesh_health(ring)

        measured = measure_state(
            ring, joint, centre,
            slot_half_angle if state == "slot proposal" else None,
        )
        measured["mesh_health"] = health
        measured["ring_profile"] = ring_profile(ring, joint, centre)
        measured["boolean_intersection"] = (
            boolean_intersection_volume(ring, joint)
            if health["ring"]["closed"] and health["joint"]["closed"]
            else {"available": False, "reason": "a mesh is not closed"}
        )
        states[state] = measured
    baseline = states["production ring"]["ring_profile"]
    slotted = states["slot proposal"]["ring_profile"]
    return {
        "source": str(source.relative_to(project_root)),
        "sha256": m1.digest(source),
        "slot_half_angle_deg": slot_half_angle,
        "states": states,
        "reconstruction_fidelity": {
            "faithful": (
                baseline["distinct_radii"] == slotted["distinct_radii"]
                and baseline["azimuth_step_deg"] == slotted["azimuth_step_deg"]
            ),
            "baseline_cross_section": baseline["cross_section"],
            "rebuilt_cross_section": slotted["cross_section"],
            "baseline_azimuth_step_deg": baseline["azimuth_step_deg"],
            "rebuilt_azimuth_step_deg": slotted["azimuth_step_deg"],
            "consequence": (
                "the rebuilt ring is a stand-in: it shares the inner radius, so "
                "the minimum lip overlap carries over, but its section and facet "
                "count differ - mean overlap, Boolean volume and the theme's "
                "silhouette do not"
            ),
        },
    }


def contract_proposal(themes):
    """A contract in units that mean something, not yet applied."""
    worst_slot = min(
        (
            entry["states"]["slot proposal"]["direct_mechanical_retention"][
                "min_lip_overlap_mm"
            ]
            or 0.0
        )
        for entry in themes.values()
    )
    worst_baseline = min(
        (
            entry["states"]["production ring"]["direct_mechanical_retention"][
                "min_lip_overlap_mm"
            ]
            or 0.0
        )
        for entry in themes.values()
    )
    worst_coverage = min(
        entry["states"]["slot proposal"]["proxy_angular_coverage"]["coverage_deg"]
        for entry in themes.values()
    )
    return {
        "status": "proposed, not applied; awaiting Codex approval",
        "primary": {
            "metric": "min lip overlap depth over all retaining azimuths",
            "measured_baseline_mm": round(worst_baseline, 4),
            "measured_slot_mm": round(worst_slot, 4),
            "proposed_floor_mm": round(worst_baseline * 0.75, 4),
            "physical_meaning": (
                "the ring must overhang the ball by at least this much "
                "somewhere it is present, or the ball has a path out"
            ),
            "safety_margin": (
                "75% of what the shipped ring already achieves, so the "
                "contract cannot be met by a ring weaker than production"
            ),
        },
        "secondary": {
            "metric": "retaining angular coverage",
            "measured_slot_deg": worst_coverage,
            "proposed_floor_deg": 270.0,
            "physical_meaning": (
                "the ball is held in at least three quarters of the "
                "directions it could leave by"
            ),
            "status": "proxy; supports the primary, never replaces it",
        },
        "excluded": {
            "metric": "sampled occupied fraction",
            "reason": (
                "grid-dependent by up to 0.39 on the same geometry "
                "(alignment 95.2); not a quantity"
            ),
        },
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

    started = time.perf_counter()
    themes = {}
    for theme in args.themes or angles:
        themes[theme] = survey_theme(project_root, theme, angles[theme])
        slot = themes[theme]["states"]["slot proposal"]
        base = themes[theme]["states"]["production ring"]
        print(
            f"[Opus5Retention] {theme}: lip overlap "
            f"{base['direct_mechanical_retention']['min_lip_overlap_mm']} -> "
            f"{slot['direct_mechanical_retention']['min_lip_overlap_mm']} mm, "
            f"coverage {base['proxy_angular_coverage']['coverage_deg']} -> "
            f"{slot['proxy_angular_coverage']['coverage_deg']} deg"
        )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2a",
                "note": (
                    "Read-only (alignment 96.3). Retention is measured as lip "
                    "overlap depth and angular coverage; the sampled occupied "
                    "fraction is deliberately absent. No Blend is saved."
                ),
                "preflight": gate,
                "slot_half_angles": angles,
                "themes": themes,
                "acceptance_contract_proposal": contract_proposal(themes),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5Retention] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
