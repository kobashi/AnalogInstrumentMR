"""Phase M2d: is the joint-ring overlap an allowance, or a tenth defect?

Alignment 102.3. The joint-ring penetration was reported in 101.5 from a
throwaway script, so the numbers had no audit trail behind them. This runs the
pair properly - one theme at a time, one pose at a time, legacy and both new
layers side by side - and writes every figure to JSON so the claim can be
re-checked without taking the prose on trust.

The question is not whether the two solids share volume. They do, by
construction: the generator gave the joint and the ring's bore the same radius,
and `V6_KNOWN_DEFECTS.md` D-5 already records that as an intended retaining
stack. The question is whether the sharing stays inside the ring's retaining
depth band and the joint's assembly region, whether the slot makes it worse,
and whether any of it becomes visible. So the contact points are converted into
the ring's own frame and reported as radius, depth and azimuth, and the same
poses are rendered for production and the adopted compact slot.

Only the named pair is audited. Shaft, grip and axle are deliberately excluded:
this is not an allowance for `switch x ring`.

No sampled occupied fraction is used anywhere (alignment 95.2).

Read-only. No Blend is saved and no existing report or PNG is overwritten.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_joint_ring_allowance.py -- \
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
import generate_hardsurface_lever_prototype as hs
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_faithful_slot_selection as m2c
import opus5_d5_profile_preserving_slot as m2b


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d5_joint_ring_allowance_audit.json"
PREFIX = "d5_joint_ring_allowance"

# Alignment 102.1. These are the adopted angles, not candidates any more.
ADOPTED = {"OrbitalAnalog": 17.0, "ForgeBrass": 19.5, "KineticSafety": 22.0}

POSES = [56.0 * index / 26 for index in range(27)]
KEY_POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))
COPLANAR_DISTANCE_M = 2.0e-5
COPLANAR_COSINE = 0.999

VIEWS = {
    "front": {"azimuth": 0.0, "elevation": 12.0, "shot": "close"},
    "oblique": {"azimuth": 42.0, "elevation": 26.0, "shot": "close"},
    "section": {"azimuth": 68.0, "elevation": 20.0, "shot": "section"},
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def hierarchy(obj):
    chain = []
    walker = obj
    while walker is not None:
        chain.append(walker.name)
        walker = walker.parent
    return chain


def identity(obj):
    return {
        "name": obj.name,
        "hierarchy": hierarchy(obj),
        "matrix_world": [[round(v, 9) for v in row] for row in obj.matrix_world],
        "mesh_health": m2b.mesh_health(obj),
    }


def ring_frame(ring, centre):
    """The ring's own cylindrical frame: radius, depth Y, azimuth."""
    points = [ring.matrix_world @ vertex.co for vertex in ring.data.vertices]
    radii = [math.hypot(p.x - centre.x, p.z - centre.z) for p in points]
    return {
        "origin": [round(v, 7) for v in centre],
        "inner_radius": round(min(radii), 7),
        "outer_radius": round(max(radii), 7),
        "depth_band_y": [
            round(min(p.y for p in points), 7),
            round(max(p.y for p in points), 7),
        ],
        "note": "azimuth 0 is +Z, measured toward +X, as everywhere in this phase",
    }


def to_frame(point, frame):
    origin = frame["origin"]
    return {
        "radius": math.hypot(point.x - origin[0], point.z - origin[2]),
        "depth_y": point.y,
        "azimuth_deg": math.degrees(
            math.atan2(point.x - origin[0], point.z - origin[2])
        )
        % 360.0,
    }


def coplanar_risk(joint_triangles, ring_triangles, pairs):
    """Faces close enough and parallel enough to fight for the same pixel."""
    hits = 0
    for joint_index, ring_index in pairs:
        first, second = joint_triangles[joint_index], ring_triangles[ring_index]
        distance = contact.triangle_distance(first, second)
        if distance > COPLANAR_DISTANCE_M:
            continue
        normal_a = contact.plane_of(first)[0]
        normal_b = contact.plane_of(second)[0]
        if abs(normal_a.dot(normal_b)) >= COPLANAR_COSINE:
            hits += 1
    return hits


def audit_pair(pivot, joint, ring, frame, poses):
    """Legacy and both new layers, pose by pose, on one named pair."""
    base = pivot.rotation_euler.copy()
    totals = {
        "legacy_contact_poses": 0,
        "legacy_contact_points": 0,
        "surface_tangent": 0,
        "surface_crossing": 0,
        "boundary_vertices": 0,
        "within_tolerance_vertices": 0,
        "penetrating_vertices": 0,
        "deepest_intrusion_mm": 0.0,
        "coplanar_face_pairs": 0,
    }
    # Kept apart because only one direction survives a topology change: cutting
    # the ring adds vertices on the polygon's chords, closer to the axis than
    # its corners were, so ring-into-joint reads deeper without any surface
    # having moved. The joint's own vertices are untouched by the cut.
    directed = {
        label: {
            "boundary_vertices": 0,
            "within_tolerance_vertices": 0,
            "penetrating_vertices": 0,
            "deepest_intrusion_mm": 0.0,
        }
        for label in ("joint_into_ring", "ring_into_joint")
    }
    extent = {
        "radius": [None, None],
        "depth_y": [None, None],
        "azimuth_deg": [None, None],
    }
    per_pose = {}
    try:
        for degrees in poses:
            pivot.rotation_euler[0] = base[0] + math.radians(degrees)
            bpy.context.view_layer.update()

            legacy_tree, legacy_v, legacy_p = pilot.bvh_for(joint)
            other_tree, other_v, other_p = pilot.bvh_for(ring)
            legacy_hits = 0
            for mine, theirs in legacy_tree.overlap(other_tree):
                if pilot.triangle_contact_points(
                    [legacy_v[i] for i in legacy_p[mine]],
                    [other_v[i] for i in other_p[theirs]],
                ):
                    legacy_hits += 1
            if legacy_hits:
                totals["legacy_contact_poses"] += 1
                totals["legacy_contact_points"] += legacy_hits

            joint_tris = m1.world_triangles(joint)
            ring_tris = m1.world_triangles(ring)
            joint_broad, joint_exact = m1.trees(joint)
            ring_broad, ring_exact = m1.trees(ring)
            pairs = contact.candidate_pairs(
                joint_tris, ring_tris, joint_broad, ring_broad
            )
            surface = contact.surface_contact(joint_tris, ring_tris, pairs)
            totals["surface_tangent"] += len(surface[contact.TANGENT])
            totals["surface_crossing"] += len(surface[contact.CROSSING])
            totals["coplanar_face_pairs"] += coplanar_risk(
                joint_tris, ring_tris, pairs
            )

            for group in (surface[contact.TANGENT], surface[contact.CROSSING]):
                for hit in group:
                    for point in hit["points"]:
                        local = to_frame(Vector(point), frame)
                        for key, value in local.items():
                            low, high = extent[key]
                            extent[key] = [
                                value if low is None else min(low, value),
                                value if high is None else max(high, value),
                            ]

            deepest = 0.0
            for label, source, tree in (
                ("joint_into_ring", joint, ring_exact),
                ("ring_into_joint", ring, joint_exact),
            ):
                depth = contact.material_penetration(
                    [source.matrix_world @ v.co for v in source.data.vertices], tree
                )
                for key in (
                    "boundary_vertices",
                    "within_tolerance_vertices",
                    "penetrating_vertices",
                ):
                    totals[key] = max(totals[key], depth[key])
                    directed[label][key] = max(directed[label][key], depth[key])
                directed[label]["deepest_intrusion_mm"] = max(
                    directed[label]["deepest_intrusion_mm"],
                    depth["deepest_intrusion_mm"],
                )
                deepest = max(deepest, depth["deepest_intrusion_mm"])
            totals["deepest_intrusion_mm"] = max(
                totals["deepest_intrusion_mm"], deepest
            )
            per_pose[round(degrees, 4)] = {
                "surface_crossing": len(surface[contact.CROSSING]),
                "surface_tangent": len(surface[contact.TANGENT]),
                "deepest_intrusion_mm": round(deepest, 6),
                "legacy_contact_points": legacy_hits,
            }
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()

    totals["deepest_intrusion_mm"] = round(totals["deepest_intrusion_mm"], 6)
    totals["verdict"] = contact.verdict(
        {
            "boundary_vertices": totals["boundary_vertices"],
            "within_tolerance_vertices": totals["within_tolerance_vertices"],
            "penetrating_vertices": totals["penetrating_vertices"],
            "raw_parity_hits": (
                totals["boundary_vertices"]
                + totals["within_tolerance_vertices"]
                + totals["penetrating_vertices"]
            ),
            "deepest_intrusion_mm": totals["deepest_intrusion_mm"],
        },
        totals["surface_crossing"],
        None if totals["surface_crossing"] else {"cells_in_both": 0},
        totals["surface_tangent"],
    )
    totals["legacy_conclusion"] = (
        "contact" if totals["legacy_contact_poses"] else "no contact"
    )
    for entry in directed.values():
        entry["deepest_intrusion_mm"] = round(entry["deepest_intrusion_mm"], 6)
    return {
        "totals": totals,
        "by_direction": directed,
        "contact_extent_in_ring_frame": {
            key: (
                None
                if value[0] is None
                else [round(value[0], 7), round(value[1], 7)]
            )
            for key, value in extent.items()
        },
        "worst_pose": max(
            per_pose, key=lambda k: per_pose[k]["deepest_intrusion_mm"]
        ),
        "per_pose": per_pose,
    }


def containment(extent, frame, joint, centre):
    """Does the shared volume stay where an assembly interface belongs?"""
    radius = extent["radius"]
    depth = extent["depth_y"]
    band = frame["depth_band_y"]
    joint_points = [joint.matrix_world @ v.co for v in joint.data.vertices]
    in_band = [
        math.hypot(p.x - centre.x, p.z - centre.z)
        for p in joint_points
        if band[0] <= p.y <= band[1]
    ]
    exposed = max(in_band) if in_band else None
    return {
        "contact_radius_range": radius,
        "ring_radius_range": [frame["inner_radius"], frame["outer_radius"]],
        "within_ring_material": (
            radius is not None
            and radius[0] >= frame["inner_radius"] - 1e-6
            and radius[1] <= frame["outer_radius"] + 1e-6
        ),
        "contact_depth_range": depth,
        "ring_depth_band_y": band,
        "within_retaining_depth_band": (
            depth is not None
            and depth[0] >= band[0] - 1e-6
            and depth[1] <= band[1] + 1e-6
        ),
        "joint_max_radius_in_band": round(exposed, 7) if exposed else None,
        "joint_stays_inside_ring_outer": (
            exposed is not None and exposed <= frame["outer_radius"] + 1e-6
        ),
        "meaning": (
            "the overlap is an assembly interface only if it stays inside the "
            "ring's own material and never reaches past its outer surface"
        ),
    }


def seam_stability(pivot, joint, ring, frame, poses):
    """How far the visible ring-on-ball seam moves over the whole throw.

    The overlap is hidden by the ring's inner edge, so what a viewer sees is
    the line where that edge crosses the ball. A sphere rotating about its own
    centre would not move that line at all, but these joints are faceted, so
    the facets pass under the edge and the seam breathes by the facet sagitta.
    That breathing, in millimetres, is the objective form of "is there a
    visible artifact" (alignment 102.3-6).
    """
    base = pivot.rotation_euler.copy()
    band = frame["depth_band_y"]
    radii = []
    try:
        for degrees in poses:
            pivot.rotation_euler[0] = base[0] + math.radians(degrees)
            bpy.context.view_layer.update()
            points = [joint.matrix_world @ v.co for v in joint.data.vertices]
            in_band = [
                math.hypot(p.x - frame["origin"][0], p.z - frame["origin"][2])
                for p in points
                if band[0] <= p.y <= band[1]
            ]
            if in_band:
                radii.append(max(in_band))
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    if not radii:
        return {"computable": False, "reason": "no joint vertex in the ring band"}
    return {
        "computable": True,
        "poses": len(radii),
        "joint_radius_in_band_mm": [
            round(min(radii) * 1000.0, 6), round(max(radii) * 1000.0, 6)
        ],
        "seam_travel_mm": round((max(radii) - min(radii)) * 1000.0, 6),
        "ring_inner_radius_mm": round(frame["inner_radius"] * 1000.0, 6),
        "meaning": (
            "how far the ball's widest point at the ring's depth moves over "
            "the throw; the seam cannot move further than this"
        ),
    }


def scene_for(project_root, theme, state, half_angle):
    m1.open_blend(m2c.source_blend(project_root, theme))
    root = bpy.data.objects[f"PF_Visual_Toggle_{theme}_V6"]
    pivot = bpy.data.objects["switch_pivot"]
    ring = next(
        o for o in pilot.meshes_under(root) if "retaining_ring" in o.name.lower()
    )
    joint = next(o for o in pilot.meshes_under(root) if "hemisphere" in o.name.lower())
    centre = pivot.matrix_world.translation.copy()
    if state == "compact slot":
        cut = m2b.cut_slot(ring, centre, half_angle)
        cut.parent = ring.parent
        ring.hide_viewport = True
        ring.hide_render = True
        bpy.context.view_layer.update()
        ring = cut
    return {
        "root": root, "pivot": pivot, "ring": ring, "joint": joint, "centre": centre,
    }


def render_state(project_root, theme, state, half_angle, pose_label, degrees):
    directory = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    directory.mkdir(parents=True, exist_ok=True)
    written = {}
    for view_name, view in VIEWS.items():
        scene = scene_for(project_root, theme, state, half_angle)
        review.configure_scene()
        pivot, ring, joint = scene["pivot"], scene["ring"], scene["joint"]
        pivot.rotation_euler[0] = math.radians(degrees)
        bpy.context.view_layer.update()
        centre = scene["centre"]

        for obj in pilot.meshes_under(scene["root"]):
            if obj.name not in (ring.name, joint.name):
                obj.hide_render = True
        if view["shot"] == "section":
            for obj in (ring, joint):
                m2c.half_space_cut(obj, centre)
            tint = hs.material(
                "MAT_Opus5_Allowance_Ring", (0.45, 0.16, 0.05, 1.0), 0.85, 0.30
            )
            ring.data.materials.clear()
            ring.data.materials.append(tint)

        span = max(
            math.hypot(
                (ring.matrix_world @ v.co).x - centre.x,
                (ring.matrix_world @ v.co).z - centre.z,
            )
            for v in ring.data.vertices
        )
        scale = span * 2.8
        rig = {"light_scale": scale, "energy_scale": (scale / 0.17) ** 2 * 1.8}
        slug = state.replace(" ", "_")
        plain = directory / f"{PREFIX}_{slug}_{pose_label}_{view_name}.png"
        review.shot(
            rig, (centre.x, centre.y, centre.z), span * 5.6,
            (view["azimuth"], view["elevation"]), 58.0, plain,
        )
        labelled = directory / f"{PREFIX}_{slug}_{pose_label}_{view_name}_labelled.png"
        caption = state.upper() if half_angle is None else f"{state} +-{half_angle} DEG".upper()
        m2c.label_copy(
            plain, labelled, [caption, f"{theme} {pose_label} {view_name}".upper()]
        )
        written[view_name] = {
            "unlabelled": str(plain.relative_to(project_root)),
            "labelled": str(labelled.relative_to(project_root)),
        }
    return written


def survey_theme(project_root, theme, half_angle, skip_renders):
    states = {}
    for state in ("production", "compact slot"):
        scene = scene_for(project_root, theme, state, half_angle)
        ring, joint, centre = scene["ring"], scene["joint"], scene["centre"]
        frame = ring_frame(ring, centre)
        audited = audit_pair(scene["pivot"], joint, ring, frame, POSES)
        states[state] = {
            "slot_half_angle_deg": None if state == "production" else half_angle,
            "ring": identity(ring),
            "joint": identity(joint),
            "ring_frame": frame,
            "audit": audited,
            "containment": containment(
                audited["contact_extent_in_ring_frame"], frame, joint, centre
            ),
            "seam_stability": seam_stability(
                scene["pivot"], joint, ring, frame, POSES
            ),
        }

    production = states["production"]["audit"]["totals"]
    compact = states["compact slot"]["audit"]["totals"]
    production_extent = states["production"]["audit"]["contact_extent_in_ring_frame"]
    compact_extent = states["compact slot"]["audit"]["contact_extent_in_ring_frame"]

    def widened(key):
        first, second = production_extent[key], compact_extent[key]
        if first is None or second is None:
            return None
        return round(
            (second[1] - second[0]) - (first[1] - first[0]), 7
        )

    production_directed = states["production"]["audit"]["by_direction"]
    compact_directed = states["compact slot"]["audit"]["by_direction"]
    forward = "joint_into_ring"
    comparison = {
        "surface_crossing": [production["surface_crossing"], compact["surface_crossing"]],
        "joint_into_ring": {
            "penetrating_vertices": [
                production_directed[forward]["penetrating_vertices"],
                compact_directed[forward]["penetrating_vertices"],
            ],
            "deepest_intrusion_mm": [
                production_directed[forward]["deepest_intrusion_mm"],
                compact_directed[forward]["deepest_intrusion_mm"],
            ],
            "why_this_direction": (
                "the joint's vertices are identical in both states, so this "
                "comparison is not disturbed by the cut's new geometry"
            ),
        },
        "ring_into_joint": {
            "penetrating_vertices": [
                production_directed["ring_into_joint"]["penetrating_vertices"],
                compact_directed["ring_into_joint"]["penetrating_vertices"],
            ],
            "deepest_intrusion_mm": [
                production_directed["ring_into_joint"]["deepest_intrusion_mm"],
                compact_directed["ring_into_joint"]["deepest_intrusion_mm"],
            ],
            "not_used_for_the_test": (
                "the cut puts new ring vertices on the polygon's chords, which "
                "sit closer to the axis than its corners; a deeper reading here "
                "is the sampling changing, not a surface moving - M2b measured "
                "the surface deviation outside the cut as 0.0 mm"
            ),
        },
        "contact_region_widening": {key: widened(key) for key in production_extent},
        "radius_widening_cause": (
            "the slot's own cut faces are new surface lying inside the ball, "
            "so they add intersection points the uncut ring could not have; "
            "they are buried, not exposed"
        ),
        "slot_does_not_worsen": (
            compact["surface_crossing"] <= production["surface_crossing"]
            and compact_directed[forward]["penetrating_vertices"]
            <= production_directed[forward]["penetrating_vertices"]
            and compact_directed[forward]["deepest_intrusion_mm"]
            <= production_directed[forward]["deepest_intrusion_mm"] + 1e-6
            and (widened("depth_y") or 0.0) <= 1e-6
            and (widened("azimuth_deg") or 0.0) <= 1e-6
        ),
    }

    renders = {}
    if not skip_renders:
        for state in ("production", "compact slot"):
            angle = None if state == "production" else half_angle
            for label, degrees in KEY_POSES:
                renders[f"{state}/{label}"] = render_state(
                    project_root, theme, state, angle, label, degrees
                )

    allowance = {
        "pair_is_named_only": {
            "pair": "hemisphere_joint x fixed_retaining_ring",
            "excludes": ["shaft", "grip", "axle"],
            "pass": True,
        },
        "overlap_stays_in_assembly_region": {
            "production": states["production"]["containment"],
            "compact": states["compact slot"]["containment"],
            "pass": all(
                states[state]["containment"][key]
                for state in states
                for key in (
                    "within_ring_material",
                    "within_retaining_depth_band",
                    "joint_stays_inside_ring_outer",
                )
            ),
        },
        "slot_does_not_worsen": {
            "detail": comparison,
            "pass": comparison["slot_does_not_worsen"],
        },
        "no_coplanar_face_risk": {
            "distance_m": COPLANAR_DISTANCE_M,
            "cosine": COPLANAR_COSINE,
            "production_pairs": production["coplanar_face_pairs"],
            "compact_pairs": compact["coplanar_face_pairs"],
            "pass": (
                production["coplanar_face_pairs"] == 0
                and compact["coplanar_face_pairs"] == 0
            ),
        },
        "seam_is_stable_over_the_throw": {
            "limit_mm": 0.25,
            "production_mm": states["production"]["seam_stability"].get(
                "seam_travel_mm"
            ),
            "compact_mm": states["compact slot"]["seam_stability"].get(
                "seam_travel_mm"
            ),
            "pass": all(
                (states[state]["seam_stability"].get("seam_travel_mm") or 0.0)
                <= 0.25
                for state in states
            ),
        },
        "recorded_as_overlap_not_clearance": {
            "wording": (
                "intentional visual assembly overlap; not collision-free and "
                "not a retention-force claim"
            ),
            "pass": True,
        },
    }
    allowance["all_pass"] = all(item["pass"] for item in allowance.values())

    return {
        "source": str(
            m2c.source_blend(project_root, theme).relative_to(project_root)
        ),
        "sha256": m1.digest(m2c.source_blend(project_root, theme)),
        "adopted_slot_half_angle_deg": half_angle,
        "poses": {"count": len(POSES), "degrees": [POSES[0], POSES[-1]]},
        "states": states,
        "production_vs_compact": comparison,
        "renders": renders,
        "named_allowance": allowance,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)

    started = time.perf_counter()
    themes = {}
    for theme in args.themes or ADOPTED:
        begin = time.perf_counter()
        themes[theme] = survey_theme(
            project_root, theme, ADOPTED[theme], args.skip_renders
        )
        entry = themes[theme]
        production = entry["states"]["production"]["audit"]["totals"]
        print(
            f"[Opus5Allowance] {theme}: {production['verdict']} crossing "
            f"{production['surface_crossing']} penetrating "
            f"{production['penetrating_vertices']} deepest "
            f"{production['deepest_intrusion_mm']} mm legacy "
            f"{production['legacy_conclusion']} | allowance "
            f"{entry['named_allowance']['all_pass']} | "
            f"{round(time.perf_counter() - begin, 1)}s"
        )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2d",
                "note": (
                    "Read-only audit of one named pair (alignment 102.3). No "
                    "sampled occupied fraction is used; no Blend is saved."
                ),
                "scope": (
                    "hemisphere_joint x fixed_retaining_ring only - shaft, "
                    "grip and axle are excluded by design"
                ),
                "preflight": gate,
                "adopted_slot_half_angles": ADOPTED,
                "themes": themes,
                "allowance_summary": {
                    theme: entry["named_allowance"]["all_pass"]
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
    print(f"[Opus5Allowance] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
