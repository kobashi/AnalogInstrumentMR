"""Phase M2f: what are the other four contacts, actually?

Alignment 106.3. The D-5 candidate resolved `switch x fixed_retaining_ring`
and left four families of contact behind that were already in the production
baseline. None of them can be classified from an object name or from a depth
figure, so this audits them: pose by pose, component by component, and against
the code that generated the parts.

The visual question is settled the only way it can be for opaque solids. Two
surfaces that cross draw a seam; two solids where one is wholly inside the
other draw nothing. So every contact point is tested for enclosure inside the
other meshes of the model, and a contact whose every point is buried inside an
opaque neighbour cannot appear in any render from any angle.

Read-only. No Blend is saved, no existing report or PNG is overwritten, and
neither production nor the D-5 candidate is modified.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_baseline_contact_classification.py -- \
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
import opus5_d5_candidate_build as m2e
import opus5_d5_faithful_slot_selection as m2c
import opus5_d5_joint_ring_allowance as m2d


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/baseline_contact_classification_report.json"
PREFIX = "baseline_contact"

POSES = [56.0 * index / 26 for index in range(27)]
KEY_POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))

# Alignment 106.3. Named by token so the same table covers all three themes.
PAIRS = {
    "switch x joint_socket": {
        "mover": "switch", "static": "joint_socket",
        "themes": ("OrbitalAnalog", "ForgeBrass", "KineticSafety"),
    },
    "hemisphere_joint x joint_socket": {
        "mover": "hemisphere", "static": "joint_socket",
        "themes": ("OrbitalAnalog", "ForgeBrass", "KineticSafety"),
    },
    "switch x limit_stop_1": {
        "mover": "switch", "static": "limit_stop_1",
        "themes": ("ForgeBrass",),
    },
    "hemisphere_joint x housing": {
        "mover": "hemisphere", "static": "housing",
        "themes": ("ForgeBrass",),
    },
}

# The generator, quoted rather than paraphrased, so intent is read off the code
# that made the parts (alignment 106.3-4).
GENERATOR = {
    "file": "Tools/Blender/generate_theme_hardsurface_v6_remaining.py",
    "function": "add_toggle_detail",
    "hemisphere_joint": "v5.sphere(radius=joint_radius, at pivot), parented to `switch`",
    "fixed_retaining_ring": "v6.torus_y(major=ring_radius, tube=ring_tube); ring_radius == joint_radius in every theme",
    "joint_socket": "v4.cylinder_y(radius=joint_radius * 0.78, depth=joint_radius * 0.70, at -pivot.y + joint_radius * 0.18)",
    "limit_stop_i": "v4.prism(joint_radius * 1.10 x 0.42 x 0.12) at z = +-joint_radius * 1.55, spanning -support_surface + 0.001 to -0.008",
    "radii": {
        "OrbitalAnalog": {"joint": 0.018, "ring": 0.018, "tube": 0.0032, "support_surface": 0.024},
        "ForgeBrass": {"joint": 0.023, "ring": 0.023, "tube": 0.0045, "support_surface": 0.050},
        "KineticSafety": {"joint": 0.024, "ring": 0.024, "tube": 0.0050, "support_surface": 0.039},
    },
    "reading": (
        "the socket's radius is 78% of the ball's and it sits behind the "
        "pivot, so by construction it is built inside the ball rather than "
        "around it; the stops sit at 1.55 ball radii out along Z, which is "
        "where a lever reaches at the end of its travel"
    ),
}

VIEWS = {
    "front": {"azimuth": 0.0, "elevation": 15.0, "shot": "model"},
    "oblique": {"azimuth": 40.0, "elevation": 28.0, "shot": "ring"},
    "section": {"azimuth": 68.0, "elevation": 20.0, "shot": "section", "energy_boost": 1.6},
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def find(root, token):
    return next(
        (o for o in pilot.meshes_under(root) if token.lower() in o.name.lower()), None
    )


def local_bounds(points, obj):
    inverse = obj.matrix_world.inverted()
    local = [inverse @ point for point in points]
    return {
        "min": [round(min(p[i] for p in local), 6) for i in range(3)],
        "max": [round(max(p[i] for p in local), 6) for i in range(3)],
    }


def enclosure(points, meshes, exclude):
    """Which opaque neighbours bury these contact points.

    An intersection seam between two opaque solids is drawn wherever both
    surfaces are exposed. If every point of the seam sits inside a third solid,
    nothing of it can reach a pixel - so this is the visibility test, not a
    judgement about whether the overlap is tidy.
    """
    trees = {
        obj.name: m1.trees(obj)[1]
        for obj in meshes
        if obj.name not in exclude
    }
    buried = 0
    by_mesh = {}
    for point in points:
        hosts = [
            name
            for name, tree in trees.items()
            if contact.inside_mesh(tree, point)
        ]
        if hosts:
            buried += 1
            for name in hosts:
                by_mesh[name] = by_mesh.get(name, 0) + 1
    return {
        "points_tested": len(points),
        "points_inside_another_mesh": buried,
        "fully_buried": bool(points) and buried == len(points),
        "hosts": dict(sorted(by_mesh.items(), key=lambda kv: -kv[1])),
    }


def containment(mover, static):
    """Is one solid wholly inside the other? Vertex parity, both ways."""
    mover_tree = m1.trees(mover)[1]
    static_tree = m1.trees(static)[1]
    static_inside = sum(
        1
        for v in static.data.vertices
        if contact.inside_mesh(mover_tree, static.matrix_world @ v.co)
    )
    mover_inside = sum(
        1
        for v in mover.data.vertices
        if contact.inside_mesh(static_tree, mover.matrix_world @ v.co)
    )
    return {
        "static_vertices": len(static.data.vertices),
        "static_vertices_inside_mover": static_inside,
        "static_wholly_inside_mover": static_inside == len(static.data.vertices),
        "mover_vertices": len(mover.data.vertices),
        "mover_vertices_inside_static": mover_inside,
        "mover_wholly_inside_static": mover_inside == len(mover.data.vertices),
    }


def component_attribution(switch, centre):
    """shaft / grip / axle, by the same rule the candidate build used."""
    islands = m2e.islands_of(switch.data)
    facts = [m2e.island_facts(switch, island, centre) for island in islands]
    axial = [i for i, f in enumerate(facts) if f["longest_axis"] == "X"]
    axle = (
        min(axial, key=lambda i: facts[i]["distance_from_pivot_mm"])
        if axial and min(facts[i]["distance_from_pivot_mm"] for i in axial) < 30.0
        else None
    )
    remaining = [i for i in range(len(islands)) if i != axle]
    shaft = max(remaining, key=lambda i: facts[i]["length_mm"][2]) if remaining else None
    roles = {}
    for index in range(len(islands)):
        roles[index] = (
            "production axle" if index == axle
            else "shaft" if index == shaft
            else "grip"
        )
    return islands, facts, roles


def sweep(pivot, mover, static, poses, model_meshes, switch_islands=None):
    base = pivot.rotation_euler.copy()
    per_pose = {}
    per_pose_points = []
    points = []
    all_triangles = set()
    component_hits = {}
    try:
        for degrees in poses:
            pivot.rotation_euler[0] = base[0] + math.radians(degrees)
            bpy.context.view_layer.update()
            mover_tris = m1.world_triangles(mover)
            static_tris = m1.world_triangles(static)
            mover_broad, mover_exact = m1.trees(mover)
            static_broad, static_exact = m1.trees(static)

            near = contact.candidate_pairs(
                mover_tris, static_tris, mover_broad, static_broad,
                tolerance=m2c.SEPARATION_SEARCH_M,
            )
            separation = None
            for mover_index, static_index in near:
                distance = contact.triangle_distance(
                    mover_tris[mover_index], static_tris[static_index]
                )
                if separation is None or distance < separation:
                    separation = distance

            pairs = contact.candidate_pairs(
                mover_tris, static_tris, mover_broad, static_broad
            )
            surface = contact.surface_contact(mover_tris, static_tris, pairs)
            crossing = len(surface[contact.CROSSING])
            tangent = len(surface[contact.TANGENT])
            here = []
            triangles = set()
            pose_triangles = set()
            for group in (surface[contact.TANGENT], surface[contact.CROSSING]):
                for hit in group:
                    triangles.add(hit["mover_triangle"])
                    pose_triangles.add(hit["mover_triangle"])
                    here.extend(Vector(p) for p in hit["points"])
            points.extend(here)

            if switch_islands is not None and triangles:
                loops = mover.data.loop_triangles
                for index in triangles:
                    vertex = loops[index].vertices[0]
                    for island_index, island in enumerate(switch_islands):
                        if vertex in island:
                            component_hits[island_index] = (
                                component_hits.get(island_index, 0) + 1
                            )
                            break

            penetrating = 0
            deepest = 0.0
            for source, tree in ((mover, static_exact), (static, mover_exact)):
                depth = contact.material_penetration(
                    [source.matrix_world @ v.co for v in source.data.vertices], tree
                )
                penetrating = max(penetrating, depth["penetrating_vertices"])
                deepest = max(deepest, depth["deepest_intrusion_mm"])

            all_triangles |= pose_triangles
            per_pose_points.append(here)
            per_pose[round(degrees, 4)] = {
                "surface_crossing": crossing,
                "surface_tangent": tangent,
                "penetrating_vertices": penetrating,
                "deepest_intrusion_mm": round(deepest, 6),
                "minimum_separation_mm": (
                    round(separation * 1000.0, 6) if separation is not None else None
                ),
                "in_contact": crossing > 0 or penetrating > 0,
            }
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()

    touching = [pose for pose, entry in per_pose.items() if entry["in_contact"]]
    worst = max(per_pose, key=lambda k: per_pose[k]["deepest_intrusion_mm"])
    return {
        "per_pose": per_pose,
        "contact_pose_range_deg": (
            [min(touching), max(touching)] if touching else None
        ),
        "poses_in_contact": len(touching),
        "continuous_over_travel": len(touching) == len(poses),
        "worst_pose_deg": worst,
        "worst": per_pose[worst],
        "component_hits": component_hits,
        "contact_points": points,
        "contact_triangles": sorted(all_triangles),
        "per_pose_points": per_pose_points,
    }


TOUCH_TOLERANCE_MM = 0.05
SEAM_TRAVEL_LIMIT_MM = 0.25


def breakthrough(mover, static, points):
    """Does the mover come out the far side of the static part?

    Depth alone cannot answer this, and neither can a fixed idea of which way
    is "through": the ball sits in front of the housing while the shaft runs
    behind the socket. So the test is symmetric - the mover breaks through only
    if it has material on **both** sides of the static part within the contact
    footprint. Material on one side plus material inside is seating.
    """
    if not points:
        return {"computable": False, "reason": "no contact points"}
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]

    def within(point):
        return (
            low[0] - 1e-4 <= point.x <= high[0] + 1e-4
            and low[2] - 1e-4 <= point.z <= high[2] + 1e-4
        )

    static_y = [
        (static.matrix_world @ v.co).y
        for v in static.data.vertices
        if within(static.matrix_world @ v.co)
    ]
    if not static_y:
        return {"computable": False, "reason": "no static vertex under the footprint"}
    back, front = min(static_y), max(static_y)
    behind = sum(
        1
        for v in mover.data.vertices
        if within(mover.matrix_world @ v.co)
        and (mover.matrix_world @ v.co).y < back - 1e-6
    )
    ahead = sum(
        1
        for v in mover.data.vertices
        if within(mover.matrix_world @ v.co)
        and (mover.matrix_world @ v.co).y > front + 1e-6
    )
    return {
        "computable": True,
        "static_thickness_mm": round((front - back) * 1000.0, 6),
        "static_y_span": [round(back, 6), round(front, 6)],
        "mover_vertices_behind": behind,
        "mover_vertices_ahead": ahead,
        "breaks_through": behind > 0 and ahead > 0,
        "meaning": "material on both sides of the static part, not merely deep in it",
    }


def seam_travel(per_pose_points):
    """How far the visible seam moves over the travel.

    The centroid alone is misleading: the intersection of a faceted sphere with
    a flat panel keeps the same circle while its sample points slide around it,
    which moves the mean without moving anything a viewer could see. The extent
    of the region is what a viewer sees, so the verdict uses how far the
    region's own bounds move, and the centroid is reported beside it.
    """
    frames = [points for points in per_pose_points if points]
    if len(frames) < 2:
        return {"computable": False, "poses_with_contact": len(frames)}
    centroids = [
        Vector(
            (
                sum(p.x for p in points) / len(points),
                sum(p.y for p in points) / len(points),
                sum(p.z for p in points) / len(points),
            )
        )
        for points in frames
    ]
    centroid_travel = max(
        (first - second).length
        for index, first in enumerate(centroids)
        for second in centroids[index + 1 :]
    )
    extremes = [
        [
            [min(p[axis] for p in points) for axis in range(3)],
            [max(p[axis] for p in points) for axis in range(3)],
        ]
        for points in frames
    ]
    bounds_travel = max(
        max(
            abs(first[side][axis] - second[side][axis])
            for side in (0, 1)
            for axis in range(3)
        )
        for index, first in enumerate(extremes)
        for second in extremes[index + 1 :]
    )
    return {
        "computable": True,
        "poses_with_contact": len(frames),
        "centroid_travel_mm": round(centroid_travel * 1000.0, 6),
        "bounds_travel_mm": round(bounds_travel * 1000.0, 6),
        "limit_mm": SEAM_TRAVEL_LIMIT_MM,
        "stable": bounds_travel * 1000.0 <= SEAM_TRAVEL_LIMIT_MM,
    }


def faceting_amplitude(obj, triangle_indices, centre):
    """How far the faces that actually touch dip below their own vertices.

    A seam between a faceted sphere and a flat panel breathes by exactly this
    much as the facets rotate under the edge, with nothing sliding. Two things
    have to be right for the figure to mean that. It is measured only on the
    triangles that take part in the contact, so a hemisphere's flat cap does
    not swamp it; and it is measured about the **rotation centre**, not the
    mesh's own centroid, because a hemisphere's centroid is not where its
    sphere's centre is.

    The figure is therefore only meaningful for a mover that is a body of
    revolution about that centre. For a lever it is not, and no verdict here
    uses it for one.
    """
    if not triangle_indices:
        return {"computable": False, "reason": "no contact triangles"}
    obj.data.calc_loop_triangles()
    matrix = obj.matrix_world
    loops = obj.data.loop_triangles
    worst = 0.0
    counted = 0
    for index in triangle_indices:
        if index >= len(loops):
            continue
        corners = [matrix @ obj.data.vertices[i].co for i in loops[index].vertices]
        normal, offset = contact.plane_of(corners)
        if normal is None:
            continue
        # `plane_of` returns offset as -n.v0, matching `signed_distances`, so
        # the distance from a point to the plane adds the offset rather than
        # subtracting it.
        plane_distance = abs(normal.dot(centre) + offset)
        vertex_distance = max((corner - centre).length for corner in corners)
        worst = max(worst, vertex_distance - plane_distance)
        counted += 1
    return {
        "computable": True,
        "contact_triangles": counted,
        "amplitude_mm": round(worst * 1000.0, 6),
        "measured_about": [round(v, 6) for v in centre],
        "meaning": (
            "the sagitta of the faces in contact about the rotation centre; a "
            "seam cannot be steadier than this without the mesh being smoother"
        ),
    }


def classify(pair_name, measured, enclosed, contained, static, mover):
    if measured["contact_pose_range_deg"] is None:
        return {
            "verdict": "named allowance candidate",
            "reason": "no contact anywhere in the sweep",
        }
    if enclosed["fully_buried"]:
        hosts = ", ".join(enclosed["hosts"])
        return {
            "verdict": "named allowance candidate",
            "reason": (
                "every contact point is inside another opaque mesh "
                f"({hosts}), so no part of this intersection can be drawn; "
                "it is an internal assembly overlap"
            ),
        }
    if contained["static_wholly_inside_mover"]:
        return {
            "verdict": "named allowance candidate",
            "reason": (
                f"{static.name} lies wholly inside {mover.name}, so the pair "
                "has no exposed seam at all"
            ),
        }
    deepest = measured["worst"]["deepest_intrusion_mm"]
    broke = measured["breakthrough"]
    travel = measured["seam_travel"]
    if broke.get("breaks_through"):
        return {
            "verdict": "defect candidate",
            "reason": (
                f"{mover.name} has material on both sides of {static.name} "
                f"({broke['mover_vertices_behind']} behind and "
                f"{broke['mover_vertices_ahead']} ahead of a "
                f"{broke['static_thickness_mm']} mm section)"
            ),
        }
    if not measured["continuous_over_travel"]:
        if deepest <= TOUCH_TOLERANCE_MM:
            return {
                "verdict": "named allowance candidate",
                "reason": (
                    "contact is limited to "
                    f"{measured['contact_pose_range_deg']} deg and never "
                    f"exceeds {deepest} mm, which is a stop being touched"
                ),
            }
        return {
            "verdict": "defect candidate",
            "reason": (
                "contact is limited to "
                f"{measured['contact_pose_range_deg']} deg, but the mover is "
                f"{deepest} mm inside the stop at its deepest and the seam is "
                "not hidden; a stop that is sunk into rather than touched"
            ),
        }
    faceting = measured["faceting"].get("amplitude_mm")
    if (
        travel.get("computable")
        and faceting is not None
        and travel["bounds_travel_mm"] <= faceting + 0.01
    ):
        return {
            "verdict": "named allowance candidate",
            "reason": (
                "present at every pose with no breakthrough of a "
                f"{broke.get('static_thickness_mm')} mm section, and the seam's "
                f"extent moves {travel['bounds_travel_mm']} mm against the "
                f"mover's own faceting of {faceting} mm - the seam is not "
                "sliding, the facets are turning under it; this is the "
                "standard approved for the joint-ring pair in alignment 104.1"
            ),
        }
    if travel.get("stable"):
        return {
            "verdict": "named allowance candidate",
            "reason": (
                "present at every pose but with no breakthrough of a "
                f"{broke.get('static_thickness_mm')} mm section and a seam "
                f"whose extent moves {travel['bounds_travel_mm']} mm over the "
                "whole travel; this is the standard already approved for the "
                "joint-ring pair in alignment 104.1"
            ),
        }
    return {
        "verdict": "defect candidate",
        "reason": (
            "exposed at every pose and the seam's extent moves "
            f"{travel.get('bounds_travel_mm')} mm over the travel, more than "
            f"the mover's own faceting of {faceting} mm, so the parts are "
            "moving through each other rather than the facets turning"
        ),
    }


def audit(project_root, theme, state, path, requested):
    m1.open_blend(path)
    root = next(
        obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_Toggle_")
    )
    pivot = bpy.data.objects["switch_pivot"]
    switch = bpy.data.objects["switch"]
    centre = pivot.matrix_world.translation.copy()
    meshes = [o for o in pilot.meshes_under(root) if not o.hide_render]
    islands, facts, roles = component_attribution(switch, centre)

    results = {}
    for pair_name in requested:
        spec = PAIRS[pair_name]
        mover = find(root, spec["mover"])
        static = find(root, spec["static"])
        if mover is None or static is None:
            results[pair_name] = {"missing": [spec["mover"], spec["static"]]}
            continue
        measured = sweep(
            pivot, mover, static, POSES, meshes,
            islands if mover is switch else None,
        )
        points = measured.pop("contact_points")
        measured["seam_travel"] = seam_travel(measured.pop("per_pose_points"))
        measured["breakthrough"] = breakthrough(mover, static, points)
        measured["faceting"] = faceting_amplitude(
            mover, measured.pop("contact_triangles"), centre
        )
        enclosed = enclosure(points, meshes, {mover.name, static.name})
        contained = containment(mover, static)
        results[pair_name] = {
            "mover": mover.name,
            "static": static.name,
            "static_parent": static.parent.name if static.parent else None,
            "mover_parent": mover.parent.name if mover.parent else None,
            **measured,
            "component_attribution": (
                {
                    roles[index]: count
                    for index, count in measured["component_hits"].items()
                }
                if mover is switch
                else None
            ),
            "contact_bounds_local": {
                mover.name: local_bounds(points, mover) if points else None,
                static.name: local_bounds(points, static) if points else None,
            },
            "enclosure": enclosed,
            "containment": contained,
            "classification": classify(
                pair_name, measured, enclosed, contained, static, mover
            ),
        }
    return {
        "state": state,
        "path": str(path.relative_to(project_root)),
        "sha256": m1.digest(path),
        "switch_components": {roles[i]: facts[i] for i in range(len(facts))},
        "pairs": results,
    }


def render_states(project_root, theme, states, extra_poses):
    directory = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    directory.mkdir(parents=True, exist_ok=True)
    poses = list(KEY_POSES) + [
        (f"worst_{int(round(value))}", value)
        for value in sorted(set(extra_poses))
        if all(abs(value - known) > 1e-6 for _, known in KEY_POSES)
    ]
    written = {}
    for state, path in states.items():
        for pose_label, degrees in poses:
            for view_name, view in VIEWS.items():
                m1.open_blend(path)
                review.configure_scene()
                root = next(
                    o for o in bpy.data.objects
                    if o.name.startswith("PF_Visual_Toggle_")
                )
                shot_state = {
                    "root": root,
                    "pivot": bpy.data.objects["switch_pivot"],
                    "ring": find(root, "retaining_ring"),
                    "joint": find(root, "hemisphere"),
                }
                shot_view = dict(view)
                shot_view["pose"] = degrees
                target = (
                    directory
                    / f"{PREFIX}_{state}_{pose_label}_{view_name}.png"
                )
                m2c.render_view(shot_state, theme, shot_view, target)
                labelled = target.with_name(target.stem + "_labelled.png")
                m2c.label_copy(
                    target, labelled,
                    [
                        f"{state} {pose_label}".upper(),
                        f"{theme} {view_name}".upper(),
                    ],
                )
                written[f"{state}/{pose_label}/{view_name}"] = {
                    "unlabelled": str(target.relative_to(project_root)),
                    "labelled": str(labelled.relative_to(project_root)),
                }
    return written


def compare_states(production, candidate):
    out = {}
    for pair_name, before in production["pairs"].items():
        after = candidate["pairs"].get(pair_name)
        if after is None or "missing" in before or "missing" in after:
            continue
        out[pair_name] = {
            "deepest_intrusion_mm": [
                before["worst"]["deepest_intrusion_mm"],
                after["worst"]["deepest_intrusion_mm"],
            ],
            "poses_in_contact": [
                before["poses_in_contact"], after["poses_in_contact"]
            ],
            "surface_crossing_at_worst": [
                before["worst"]["surface_crossing"],
                after["worst"]["surface_crossing"],
            ],
            "fully_buried": [
                before["enclosure"]["fully_buried"],
                after["enclosure"]["fully_buried"],
            ],
            "not_worsened": (
                after["worst"]["deepest_intrusion_mm"]
                <= before["worst"]["deepest_intrusion_mm"] + 1e-6
                and after["poses_in_contact"] <= before["poses_in_contact"]
                and after["enclosure"]["fully_buried"]
                >= before["enclosure"]["fully_buried"]
            ),
        }
    return out


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)

    started = time.perf_counter()
    themes = {}
    for theme in args.themes or ("OrbitalAnalog", "ForgeBrass", "KineticSafety"):
        begin = time.perf_counter()
        requested = [
            name for name, spec in PAIRS.items() if theme in spec["themes"]
        ]
        states = {
            "production": m2c.source_blend(project_root, theme),
            "candidate": m2e.candidate_path(project_root, theme, None),
        }
        audited = {
            state: audit(project_root, theme, state, path, requested)
            for state, path in states.items()
        }
        comparison = compare_states(audited["production"], audited["candidate"])
        worst_poses = [
            entry["worst_pose_deg"]
            for state in audited.values()
            for entry in state["pairs"].values()
            if "worst_pose_deg" in entry
        ]
        renders = (
            {}
            if args.skip_renders
            else render_states(project_root, theme, states, worst_poses)
        )
        themes[theme] = {
            "generator": {
                **GENERATOR,
                "theme_radii": GENERATOR["radii"][theme],
            },
            "states": audited,
            "production_vs_candidate": comparison,
            "renders": renders,
            "elapsed_seconds": round(time.perf_counter() - begin, 3),
        }
        verdicts = {
            name: entry["classification"]["verdict"]
            for name, entry in audited["candidate"]["pairs"].items()
            if "classification" in entry
        }
        print(f"[Opus5Baseline] {theme}: {verdicts} | {round(time.perf_counter() - begin, 1)}s")

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2f",
                "note": (
                    "Read-only classification of the four baseline contacts "
                    "left after D-5 (alignment 106.3). Nothing is saved and "
                    "no existing report or PNG is overwritten."
                ),
                "preflight": gate,
                "pairs_audited": PAIRS,
                "poses": {"count": len(POSES), "degrees": [POSES[0], POSES[-1]]},
                "themes": themes,
                "verdict_summary": {
                    theme: {
                        name: entry["classification"]["verdict"]
                        for name, entry in payload["states"]["candidate"][
                            "pairs"
                        ].items()
                        if "classification" in entry
                    }
                    for theme, payload in themes.items()
                },
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5Baseline] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
