"""Phase M2e: the isolated D-5 candidate Blends.

Alignment 104.2. Everything up to here was read-only. This one writes: three
candidate Blends that fix D-5 and nothing else, built from the production
baselines, published under new names beside them.

Two edits per theme, both in place so the runtime contract survives:

* The legacy axle connected component is deleted from the `switch` mesh
  itself. Earlier phases split `switch` into `switch_component_*` objects to
  study it; a candidate that shipped those would rename the movable object and
  break the motion contract, so here the island is removed from the datablock
  and the object keeps its name, parent, transform and materials.
* The ring keeps its object entirely - only its mesh datablock is swapped for
  the approved EXACT Boolean result.

Nothing else is touched. No investigation leftovers, no hidden originals, no
new objects of any kind.

The joint-ring overlap is audited separately and reported as the named
allowance approved in 104.1, never folded into the collision result.

Publishing follows the transaction from `opus5_publish`: the guard decides
whether anything may be written at all, the Blends are staged and verified by
reopening them, and the report is written last as the commit marker. The guard
itself is reused rather than reimplemented; only the promotion loop differs,
because this phase publishes three Blends against one report.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_candidate_build.py -- \
      --project-root "$PWD" [--trial-dir /tmp/somewhere]
"""

import argparse
import json
import math
import shutil
import sys
import tempfile
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
import opus5_d5_faithful_slot_selection as m2c
import opus5_d5_joint_ring_allowance as m2d
import opus5_d5_profile_preserving_slot as m2b
import opus5_publish as publish


REPORT = "ArtSource/Blender/BrushUp/Opus5/d5_candidate_build_report.json"
REVISION = "D5"

ADOPTED = {"OrbitalAnalog": 17.0, "ForgeBrass": 19.5, "KineticSafety": 22.0}

# Alignment 104.3-3. The floors are M2c's measured closest approach; the slack
# is the measurement tolerance, not a licence to come closer.
SEPARATION_FLOOR_MM = {
    "OrbitalAnalog": 0.295772,
    "ForgeBrass": 0.372812,
    "KineticSafety": 0.311540,
}
SEPARATION_TOLERANCE_MM = 0.01
POSES = [56.0 * index / 26 for index in range(27)]
KEY_POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))
ALLOWED_PAIRS = {("hemisphere_joint", "fixed_retaining_ring")}

# M2c's view keys carry a pose in their name, which would collide with the pose
# this phase renders at and produce filenames naming two different poses. The
# geometry is the same; only the naming is fixed.
CANDIDATE_VIEWS = {
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
    parser.add_argument("--trial-dir")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def candidate_path(project_root, theme, trial_dir):
    name = f"BL_Toggle_{theme}_V6_Opus5_{REVISION}_Retopo.blend"
    if trial_dir:
        return Path(trial_dir) / theme / name
    return project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / name


def islands_of(mesh_data):
    """Connected vertex components, without copying the object."""
    mesh = bmesh.new()
    mesh.from_mesh(mesh_data)
    mesh.verts.ensure_lookup_table()
    seen = set()
    islands = []
    for vertex in mesh.verts:
        if vertex.index in seen:
            continue
        stack, island = [vertex], set()
        while stack:
            current = stack.pop()
            if current.index in island:
                continue
            island.add(current.index)
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other.index not in island:
                    stack.append(other)
        seen |= island
        islands.append(island)
    mesh.free()
    return islands


def island_facts(obj, island, centre):
    points = [
        obj.matrix_world @ obj.data.vertices[index].co for index in sorted(island)
    ]
    span = [
        [min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)
    ]
    lengths = [span[i][1] - span[i][0] for i in range(3)]
    longest = max(range(3), key=lambda i: lengths[i])
    return {
        "vertices": len(island),
        "bounds": {
            axis: [round(span[i][0], 6), round(span[i][1], 6)]
            for i, axis in enumerate("xyz")
        },
        "longest_axis": "XYZ"[longest],
        "length_mm": [round(value * 1000.0, 3) for value in lengths],
        "distance_from_pivot_mm": round(
            min((p - centre).length for p in points) * 1000.0, 3
        ),
    }


def remove_axle_in_place(switch, centre):
    """Delete the axle island from `switch`, keeping the object itself."""
    islands = islands_of(switch.data)
    facts = [island_facts(switch, island, centre) for island in islands]
    axial = [
        index for index, entry in enumerate(facts) if entry["longest_axis"] == "X"
    ]
    if not axial:
        return {"removed": False, "reason": "no X-dominant island", "islands": facts}
    axle = min(axial, key=lambda index: facts[index]["distance_from_pivot_mm"])
    remaining = [index for index in range(len(islands)) if index != axle]
    shaft = max(remaining, key=lambda index: facts[index]["length_mm"][2])

    mesh = bmesh.new()
    mesh.from_mesh(switch.data)
    mesh.verts.ensure_lookup_table()
    doomed = [v for v in mesh.verts if v.index in islands[axle]]
    bmesh.ops.delete(mesh, geom=doomed, context="VERTS")
    mesh.to_mesh(switch.data)
    mesh.free()
    switch.data.update()
    bpy.context.view_layer.update()

    return {
        "removed": True,
        "axle_island": axle,
        "shaft_island": shaft,
        "grip_islands": [i for i in remaining if i != shaft],
        "islands_before": facts,
        "vertices_removed": len(islands[axle]),
        "islands_after": len(islands_of(switch.data)),
    }


def cut_ring_in_place(ring, centre, half_angle):
    """Swap the ring's mesh datablock for the Boolean result. Object untouched."""
    before = {
        "name": ring.name,
        "parent": ring.parent.name if ring.parent else None,
        "matrix_world": [[round(v, 9) for v in row] for row in ring.matrix_world],
        "materials": [m.name if m else None for m in ring.data.materials],
        "health": m2b.mesh_health(ring),
    }
    cut = m2b.cut_slot(ring, centre, half_angle)
    deviation = m2b.surface_deviation(cut, ring, centre, half_angle)
    old = ring.data
    ring.data = cut.data
    bpy.data.objects.remove(cut, do_unlink=True)
    bpy.data.meshes.remove(old)
    bpy.context.view_layer.update()
    after = {
        "name": ring.name,
        "parent": ring.parent.name if ring.parent else None,
        "matrix_world": [[round(v, 9) for v in row] for row in ring.matrix_world],
        "materials": [m.name if m else None for m in ring.data.materials],
        "health": m2b.mesh_health(ring),
    }
    return {
        "slot_half_angle_deg": half_angle,
        "before": before,
        "after": after,
        "surface_deviation": deviation,
        "object_identity_preserved": (
            before["name"] == after["name"]
            and before["parent"] == after["parent"]
            and before["matrix_world"] == after["matrix_world"]
            and before["materials"] == after["materials"]
        ),
    }


def inventory(root):
    entries = {}
    for obj in [root] + list(root.children_recursive):
        entry = {
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "matrix_world": [[round(v, 9) for v in row] for row in obj.matrix_world],
            "hide_viewport": obj.hide_viewport,
            "hide_render": obj.hide_render,
        }
        if obj.type == "MESH":
            obj.data.calc_loop_triangles()
            points = [obj.matrix_world @ v.co for v in obj.data.vertices]
            entry.update(
                {
                    "vertices": len(obj.data.vertices),
                    "loop_triangles": len(obj.data.loop_triangles),
                    "materials": [m.name if m else None for m in obj.data.materials],
                    "bounds": {
                        "min": [round(min(p[i] for p in points), 6) for i in range(3)],
                        "max": [round(max(p[i] for p in points), 6) for i in range(3)],
                    },
                }
            )
        entries[obj.name] = entry
    return entries


def inventory_delta(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = {}
    for name in sorted(set(before) & set(after)):
        first, second = before[name], after[name]
        difference = {
            key: [first.get(key), second.get(key)]
            for key in ("vertices", "loop_triangles", "materials", "parent")
            if first.get(key) != second.get(key)
        }
        if difference:
            changed[name] = difference
    return {"added": added, "removed": removed, "changed": changed}


def movable_and_static(root, pivot):
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2d.hierarchy(obj)
    ]
    static = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name not in m2d.hierarchy(obj)
    ]
    return movable, static


def pair_is_allowed(mover, static):
    for mover_token, static_token in ALLOWED_PAIRS:
        if mover_token in mover.name and static_token in static.name:
            return True
    return False


def sweep_pair(pivot, mover, static, poses):
    base = pivot.rotation_euler.copy()
    crossing = tangent = penetrating = 0
    deepest = 0.0
    separation = None
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
            crossing += len(surface[contact.CROSSING])
            tangent += len(surface[contact.TANGENT])
            for source, tree in (
                (mover, static_exact), (static, mover_exact)
            ):
                depth = contact.material_penetration(
                    [source.matrix_world @ v.co for v in source.data.vertices], tree
                )
                penetrating = max(penetrating, depth["penetrating_vertices"])
                deepest = max(deepest, depth["deepest_intrusion_mm"])
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return {
        "surface_crossing": crossing,
        "surface_tangent": tangent,
        "penetrating_vertices": penetrating,
        "deepest_intrusion_mm": round(deepest, 6),
        "minimum_separation_mm": (
            round(separation * 1000.0, 6) if separation is not None else None
        ),
        "clear": crossing == 0 and penetrating == 0,
    }


def island_regression(root, pivot, poses):
    """Every movable mesh against every static mesh, one pass."""
    movable, static = movable_and_static(root, pivot)
    results = {}
    for mover in movable:
        for other in static:
            label = f"{mover.name} x {other.name}"
            results[label] = sweep_pair(pivot, mover, other, poses)
            results[label]["named_allowance"] = pair_is_allowed(mover, other)
    return {
        "movable_meshes": [obj.name for obj in movable],
        "static_meshes": [obj.name for obj in static],
        "pairs": results,
    }


def open_and_prepare(path):
    m1.open_blend(Path(path))
    root = next(
        obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_Toggle_")
    )
    return {
        "root": root,
        "pivot": bpy.data.objects["switch_pivot"],
        "switch": bpy.data.objects["switch"],
        "ring": next(
            o
            for o in pilot.meshes_under(root)
            if "retaining_ring" in o.name.lower()
        ),
        "joint": next(
            o for o in pilot.meshes_under(root) if "hemisphere" in o.name.lower()
        ),
    }


def build_one(project_root, theme, half_angle):
    """Make the candidate in memory and return everything needed to judge it."""
    source = m2c.source_blend(project_root, theme)
    scene = open_and_prepare(source)
    root, pivot = scene["root"], scene["pivot"]
    centre = pivot.matrix_world.translation.copy()
    before = inventory(root)

    axle = remove_axle_in_place(scene["switch"], centre)
    ring_edit = cut_ring_in_place(scene["ring"], centre, half_angle)
    after = inventory(root)

    return {
        "source": str(source.relative_to(project_root)),
        "source_sha256": m1.digest(source),
        "slot_half_angle_deg": half_angle,
        "axle_removal": axle,
        "ring_edit": ring_edit,
        "inventory_before": before,
        "inventory_after": after,
        "inventory_delta": inventory_delta(before, after),
    }


def audit_candidate(project_root, theme, path, half_angle, build):
    """Alignment 104.3, items 2 to 6, on the saved candidate."""
    scene = open_and_prepare(path)
    root, pivot = scene["root"], scene["pivot"]
    ring, joint, switch = scene["ring"], scene["joint"], scene["switch"]
    centre = pivot.matrix_world.translation.copy()

    islands = islands_of(switch.data)
    facts = [island_facts(switch, island, centre) for island in islands]
    leftovers = sorted(
        obj.name
        for obj in bpy.data.objects
        if "_component_" in obj.name or obj.name.endswith("_slotted")
    )
    hidden = sorted(
        obj.name
        for obj in pilot.meshes_under(root)
        if obj.hide_render or obj.hide_viewport
    )

    structure = {
        "switch_islands": len(islands),
        "island_facts": facts,
        "axle_islands_remaining": [
            index for index, entry in enumerate(facts)
            if entry["longest_axis"] == "X"
            and entry["distance_from_pivot_mm"] < 1.0
        ],
        "switch_object_name": switch.name,
        "switch_parent": switch.parent.name if switch.parent else None,
        "investigation_leftovers": leftovers,
        "hidden_meshes": hidden,
        "pass": (
            switch.name == "switch"
            and (switch.parent.name if switch.parent else None) == "switch_pivot"
            and not leftovers
            and not hidden
            and len(islands) == len(build["axle_removal"]["islands_before"]) - 1
        ),
    }

    switch_ring = sweep_pair(pivot, switch, ring, POSES)
    floor = SEPARATION_FLOOR_MM[theme] - SEPARATION_TOLERANCE_MM
    collision = {
        "pair": f"{switch.name} x {ring.name}",
        **switch_ring,
        "separation_floor_mm": SEPARATION_FLOOR_MM[theme],
        "tolerance_mm": SEPARATION_TOLERANCE_MM,
        "pass": (
            switch_ring["clear"]
            and switch_ring["minimum_separation_mm"] is not None
            and switch_ring["minimum_separation_mm"] >= floor
        ),
    }

    frame = m2d.ring_frame(ring, centre)
    heights = m2b.section_heights(ring, centre)
    proxy = m2c.lip_by_pose(ring, joint, centre, pivot, half_angle, heights)
    health = m2b.mesh_health(ring)
    gap = proxy["neutral"]["total_gap_deg"]
    ring_contract = {
        "surface_deviation_mm": build["ring_edit"]["surface_deviation"][
            "max_deviation_mm"
        ],
        "silhouette_assembly_proxy_by_pose": proxy,
        "mesh_health": health,
        "opening": {
            "expected_total_gap_deg": round(half_angle * 2.0, 4),
            "measured_total_gap_deg": gap,
            "difference_deg": round(abs(gap - half_angle * 2.0), 4),
        },
        "pass": (
            build["ring_edit"]["surface_deviation"]["max_deviation_mm"]
            <= m2b.DEVIATION_LIMIT_MM
            and health["closed"]
            and health["normals_outward"]
            and health["degenerate_faces"] == 0
            and abs(gap - half_angle * 2.0) <= 1.0
            and build["ring_edit"]["object_identity_preserved"]
        ),
    }

    allowance_audit = m2d.audit_pair(pivot, joint, ring, frame, POSES)
    allowance = {
        "pair": f"{joint.name} x {ring.name}",
        "status": (
            "intentional visual assembly overlap; not collision-free and not "
            "a retention-force claim (alignment 104.1)"
        ),
        "totals": allowance_audit["totals"],
        "by_direction": allowance_audit["by_direction"],
        "contact_extent_in_ring_frame": allowance_audit[
            "contact_extent_in_ring_frame"
        ],
        "containment": m2d.containment(
            allowance_audit["contact_extent_in_ring_frame"], frame, joint, centre
        ),
    }

    regression = island_regression(root, pivot, POSES)
    return scene, structure, collision, ring_contract, allowance, regression


def production_reference(project_root, theme):
    scene = open_and_prepare(m2c.source_blend(project_root, theme))
    pivot, ring, joint = scene["pivot"], scene["ring"], scene["joint"]
    centre = pivot.matrix_world.translation.copy()
    frame = m2d.ring_frame(ring, centre)
    audited = m2d.audit_pair(pivot, joint, ring, frame, POSES)
    regression = island_regression(scene["root"], pivot, POSES)
    return {
        "source_sha256": m1.digest(m2c.source_blend(project_root, theme)),
        "joint_ring": audited["by_direction"],
        "regression": regression,
    }


def compare(reference, allowance, regression):
    forward = "joint_into_ring"
    deepest = [
        reference["joint_ring"][forward]["deepest_intrusion_mm"],
        allowance["by_direction"][forward]["deepest_intrusion_mm"],
    ]
    new_contacts = []
    for label, entry in regression["pairs"].items():
        if entry["clear"] or entry["named_allowance"]:
            continue
        baseline = reference["regression"]["pairs"].get(label)
        if baseline is None or baseline["clear"]:
            new_contacts.append(label)
    resolved = [
        label
        for label, entry in reference["regression"]["pairs"].items()
        if not entry["clear"]
        and not entry["named_allowance"]
        and regression["pairs"].get(label, {}).get("clear")
    ]
    return {
        "joint_into_ring_deepest_mm": deepest,
        "allowance_not_worsened": deepest[1] <= deepest[0] + 1e-6,
        "new_contacts": new_contacts,
        "resolved_contacts": resolved,
        "pass": not new_contacts and deepest[1] <= deepest[0] + 1e-6,
    }


def render_pair(project_root, theme, path, label, half_angle):
    directory = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    directory.mkdir(parents=True, exist_ok=True)
    import opus5_brushup_kinetic_review as review

    written = {}
    for pose_label, degrees in KEY_POSES:
        for view_name, view in CANDIDATE_VIEWS.items():
            scene = open_and_prepare(path)
            review.configure_scene()
            state = {
                "root": scene["root"], "pivot": scene["pivot"],
                "ring": scene["ring"], "joint": scene["joint"],
            }
            shot_view = dict(view)
            shot_view["pose"] = degrees
            target = (
                directory
                / f"d5_candidate_{label}_{pose_label}_{view_name}.png"
            )
            m2c.render_view(state, theme, shot_view, target)
            labelled = target.with_name(target.stem + "_labelled.png")
            caption = (
                label.upper()
                if half_angle is None
                else f"{label} +-{half_angle} DEG".upper()
            )
            m2c.label_copy(
                target, labelled,
                [caption, f"{theme} {pose_label} {view_name}".upper()],
            )
            written[f"{pose_label}/{view_name}"] = {
                "unlabelled": str(target.relative_to(project_root)),
                "labelled": str(labelled.relative_to(project_root)),
            }
    return written


def problems_of(entry):
    failures = []
    for key in ("structure", "collision", "ring_contract", "comparison"):
        if not entry[key]["pass"]:
            failures.append(key)
    return failures


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    report_path = (
        Path(args.trial_dir) / "d5_candidate_build_report.json"
        if args.trial_dir
        else project_root / REPORT
    )
    themes = args.themes or list(ADOPTED)
    blends = {theme: candidate_path(project_root, theme, args.trial_dir) for theme in themes}

    started = time.perf_counter()
    staging = Path(tempfile.mkdtemp(prefix="opus5-d5-candidate-"))
    entries = {}
    problems = []
    try:
        for theme in themes:
            begin = time.perf_counter()
            half = ADOPTED[theme]
            reference = production_reference(project_root, theme)
            build = build_one(project_root, theme, half)

            staged = staging / f"{theme}.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True)
            if not staged.is_file():
                raise publish.PublishFailed(f"{theme}: nothing was staged")

            scene, structure, collision, ring_contract, allowance, regression = (
                audit_candidate(project_root, theme, staged, half, build)
            )
            comparison = compare(reference, allowance, regression)
            entries[theme] = {
                **build,
                "candidate": str(
                    blends[theme].relative_to(project_root)
                    if not args.trial_dir
                    else blends[theme]
                ),
                "staged_sha256": m1.digest(staged),
                "structure": structure,
                "collision": collision,
                "ring_contract": ring_contract,
                "joint_ring_named_allowance": allowance,
                "island_regression": regression,
                # Kept in the report so the comparison can be re-checked
                # without rerunning the production side (alignment 102.2).
                "production_reference": reference,
                "comparison": comparison,
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
            failures = problems_of(entries[theme])
            problems.extend(f"{theme}: {name}" for name in failures)
            print(
                f"[Opus5D5Build] {theme}: structure {structure['pass']} "
                f"collision {collision['pass']} (sep "
                f"{collision['minimum_separation_mm']} mm) ring "
                f"{ring_contract['pass']} compare {comparison['pass']} | "
                f"{round(time.perf_counter() - begin, 1)}s"
            )

        decision = publish.publish_guard(
            any(path.exists() for path in blends.values()),
            report_path.exists(),
            problems,
            args.trial_dir,
        )
        record = dict(decision)

        # Rendered from staging, before anything is promoted, so a failure here
        # cannot leave published Blends behind without their report.
        if not args.skip_renders and decision["may_write_blend"]:
            for theme in themes:
                entries[theme]["renders"] = {
                    "production": render_pair(
                        project_root, theme,
                        m2c.source_blend(project_root, theme), "production", None,
                    ),
                    "candidate": render_pair(
                        project_root, theme, staging / f"{theme}.blend",
                        "candidate", ADOPTED[theme],
                    ),
                }

        if decision["may_write_blend"]:
            promoted = {}
            for theme in themes:
                target = blends[theme]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staging / f"{theme}.blend", target)
                m1.open_blend(target)
                promoted[theme] = m1.digest(target)
                if promoted[theme] != entries[theme]["staged_sha256"]:
                    raise publish.PublishFailed(
                        f"{theme}: promoted blend does not match what was verified"
                    )
                entries[theme]["candidate_sha256"] = promoted[theme]
            record["promoted"] = promoted

        if decision["may_write_report"]:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(
                    {
                        "phase": "M2e",
                        "revision": REVISION,
                        "note": (
                            "Isolated D-5 candidates (alignment 104.2). The "
                            "axle island is deleted from the switch mesh and "
                            "the ring's datablock is replaced; no other object "
                            "is touched and production is not overwritten."
                        ),
                        "publish": record,
                        "adopted_slot_half_angles": ADOPTED,
                        "themes": entries,
                        "gate_summary": {
                            theme: not problems_of(entry)
                            for theme, entry in entries.items()
                        },
                        "problems": problems,
                        "elapsed_seconds": round(time.perf_counter() - started, 3),
                        "authoring_environment": blender_compat.provenance(),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        print(
            f"[Opus5D5Build] {record['mode']}: {record['reason']} -> "
            f"{report_path if args.trial_dir else report_path.relative_to(project_root)}"
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
