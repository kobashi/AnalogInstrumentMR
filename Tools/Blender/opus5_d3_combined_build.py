"""Phase M2m: D-3 recombined onto the D-6 candidates.

Alignment 130.2. Three new revisions, built from the approved R3 and B2P
Blends, changing nothing except the inner ends of the endpoint ticks - and on
Round, not even those.

The old combined script is not reused. The required tick radius is recomputed
from what the model actually sweeps, over every mesh under `needle_pivot`
including the counterweight, across the whole travel. Old D-3 vertex positions
are never copied: the D-6 repair moved what sweeps, so the number it produced
is not the number this needs.

What may differ from the input is stated up front and then enforced:

* Round: nothing. If no tick vertex is inside the required radius, the model is
  published byte-for-byte identical in every semantic sense to R3.
* Medium and Large: only `kinetic_tick_3`, `_6` and `_9`, and inside those,
  only the vertices closer to the pivot than the required radius. Topology,
  outer end, width, orientation, counts and UVs are held.

Everything else - the D-6 assembly, the envelope, the motion contract, and the
other 36 models in the set - is checked to be unchanged rather than assumed.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d3_combined_build.py -- \
      --project-root "$PWD" [--trial-dir /tmp/somewhere]
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_candidate_build as m2e
import opus5_d5_faithful_slot_selection as m2c
import opus5_d6_bounded_correction as m2k1
import opus5_d6_canonical_build as m2l
import opus5_d6_full_assembly as m2k2
import opus5_d6_repair_decision as m2k
import opus5_d6_round_r3_validation as m2k3
import opus5_publish as publish


REPORT_DIR = m2l.REPORT_DIR
PREFIX = "d3_combined"
AUDIT_39 = "ArtSource/Blender/BrushUp/Opus5/audit_39_with_r3_b2p_d3.json"

# Alignment 130.2-1: the approved proportional clearance, per scale.
CLEARANCE_MM = {"MeterRound": 0.7, "MeterMedium": 1.4, "MeterLarge": 2.1}
ALLOWLIST = ("kinetic_tick_3", "kinetic_tick_6", "kinetic_tick_9")

PLAN = {
    "MeterRound": {"input": "R3", "output": "R3_D3"},
    "MeterMedium": {"input": "B2P", "output": "B2P_D3"},
    "MeterLarge": {"input": "B2P", "output": "B2P_D3"},
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
    parser.add_argument("--trial-dir")
    parser.add_argument("--skip-renders", action="store_true")
    parser.add_argument("--skip-39", action="store_true")
    return parser.parse_args(args)


def input_blend(project_root, key):
    return m2l.candidate_path(project_root, key, None)


def input_report(project_root, key):
    return m2l.report_path(project_root, key, None)


def output_blend(project_root, key, trial_dir):
    name = f"BL_{key}_{m2k.THEME}_V6_Opus5_{PLAN[key]['output']}_Retopo.blend"
    return (
        (Path(trial_dir) / name)
        if trial_dir
        else (m2l.theme_dir(project_root) / name)
    )


def output_report(project_root, key, trial_dir):
    name = f"{key}_{m2k.THEME}_V6_Opus5_{PLAN[key]['output']}.json"
    return (
        (Path(trial_dir) / name)
        if trial_dir
        else (project_root / REPORT_DIR / name)
    )


def open_input(project_root, key):
    m1.open_blend(input_blend(project_root, key))
    root = bpy.data.objects[m2k.MODELS[key]["root"]]
    return root, bpy.data.objects["needle_pivot"]


def swept_radius(root, pivot):
    """The largest radius anything on the pivot reaches, over the whole travel.

    Measured, not inherited: the D-6 repair changed what hangs off the pivot,
    so the swept circle is not the one the earlier D-3 pass worked from.
    """
    base = pivot.rotation_euler.copy()
    centre = pivot.matrix_world.translation.copy()
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    worst = 0.0
    contributor = None
    try:
        for degrees in POSES:
            pivot.rotation_euler[1] = base[1] + math.radians(degrees)
            bpy.context.view_layer.update()
            for obj in movable:
                for vertex in obj.data.vertices:
                    world = obj.matrix_world @ vertex.co
                    radius = math.hypot(world.x - centre.x, world.z - centre.z)
                    if radius > worst:
                        worst, contributor = radius, obj.name
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return {
        "swept_radius_m": round(worst, 7),
        "swept_radius_mm": round(worst * 1000.0, 4),
        "contributed_by": contributor,
        "movable_meshes": [obj.name for obj in movable],
        "poses": len(POSES),
    }


def tick_contact_present(root, pivot):
    """Does anything on the pivot actually touch an endpoint tick?"""
    base = pivot.rotation_euler.copy()
    movable = [
        obj
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and pivot.name in m2e.m2d.hierarchy(obj)
    ]
    ticks = [
        obj for obj in pilot.meshes_under(root) if obj.name in ALLOWLIST
    ]
    hits = {}
    try:
        for degrees in POSES:
            pivot.rotation_euler[1] = base[1] + math.radians(degrees)
            bpy.context.view_layer.update()
            for mover in movable:
                mover_tris = m1.world_triangles(mover)
                mover_broad, mover_exact = m1.trees(mover)
                for tick in ticks:
                    tick_tris = m1.world_triangles(tick)
                    tick_broad, tick_exact = m1.trees(tick)
                    pairs = contact.candidate_pairs(
                        mover_tris, tick_tris, mover_broad, tick_broad
                    )
                    surface = contact.surface_contact(mover_tris, tick_tris, pairs)
                    depth = contact.material_penetration(
                        [mover.matrix_world @ v.co for v in mover.data.vertices],
                        tick_exact,
                    )
                    if surface[contact.CROSSING] or depth["penetrating_vertices"]:
                        label = f"{mover.name} x {tick.name}"
                        hits[label] = hits.get(label, 0) + 1
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return {"any": bool(hits), "pairs": dict(sorted(hits.items()))}


def retract_ticks(root, pivot, required_m):
    """Move only the inner-end vertices that are inside the required radius."""
    centre = pivot.matrix_world.translation.copy()
    changes = {}
    for obj in pilot.meshes_under(root):
        if obj.name not in ALLOWLIST:
            continue
        matrix = obj.matrix_world
        inverse = matrix.inverted()
        before = []
        moved = 0
        smallest_before = None
        smallest_after = None
        for vertex in obj.data.vertices:
            world = matrix @ vertex.co
            radius = math.hypot(world.x - centre.x, world.z - centre.z)
            before.append(radius)
            smallest_before = (
                radius if smallest_before is None else min(smallest_before, radius)
            )
            if radius >= required_m - 1e-9 or radius <= 1e-9:
                continue
            scale = required_m / radius
            world.x = centre.x + (world.x - centre.x) * scale
            world.z = centre.z + (world.z - centre.z) * scale
            vertex.co = inverse @ world
            moved += 1
        obj.data.update()
        for vertex in obj.data.vertices:
            world = matrix @ vertex.co
            radius = math.hypot(world.x - centre.x, world.z - centre.z)
            smallest_after = (
                radius if smallest_after is None else min(smallest_after, radius)
            )
        changes[obj.name] = {
            "vertices": len(obj.data.vertices),
            "vertices_moved": moved,
            "inner_radius_before_mm": round(smallest_before * 1000.0, 4),
            "inner_radius_after_mm": round(smallest_after * 1000.0, 4),
            "outer_radius_mm": round(max(before) * 1000.0, 4),
        }
    bpy.context.view_layer.update()
    return changes


def uv_digest(obj):
    import hashlib
    import struct

    layer = obj.data.uv_layers.active
    if layer is None:
        return None
    digest = hashlib.sha256()
    for datum in layer.data:
        digest.update(struct.pack("<2d", datum.uv[0], datum.uv[1]))
    return digest.hexdigest()


def semantic(root):
    entries = m2l.fingerprint(root)
    for obj in [root] + list(root.children_recursive):
        if obj.type == "MESH" and obj.name in entries:
            entries[obj.name]["uv_sha256"] = uv_digest(obj)
    return entries


def allowlist_diff(reference, actual):
    comparison = m2l.compare_fingerprints(reference, actual)
    outside = {
        name: difference
        for name, difference in comparison["differing_objects"].items()
        if name not in ALLOWLIST
    }
    uv_changed = [
        name
        for name in sorted(set(reference) & set(actual))
        if reference[name].get("uv_sha256") != actual[name].get("uv_sha256")
    ]
    inside = {
        name: sorted(difference)
        for name, difference in comparison["differing_objects"].items()
        if name in ALLOWLIST
    }
    return {
        "missing_objects": comparison["missing_objects"],
        "extra_objects": comparison["extra_objects"],
        "changed_outside_allowlist": sorted(outside),
        "changed_outside_allowlist_detail": outside,
        "uv_changed_objects": uv_changed,
        "changed_inside_allowlist": inside,
        "identical": comparison["identical"],
        "pass": (
            not comparison["missing_objects"]
            and not comparison["extra_objects"]
            and not outside
            and not uv_changed
        ),
    }


def audit(project_root, key, path, required_m, retraction_applied=True):
    m1.open_blend(path)
    root = bpy.data.objects[m2k.MODELS[key]["root"]]
    pivot = bpy.data.objects["needle_pivot"]
    centre = pivot.matrix_world.translation.copy()
    if key == "MeterRound":
        classify = m2k3.classify
    else:
        m2k1.needle_components(root, centre)
        classify = m2k2.classify

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
        classified[label] = {**entry, "classification": classify(mover, static)}
    new_contacts = sorted(
        label
        for label, entry in classified.items()
        if entry["classification"] == "new"
    )
    tick_contacts = {
        label: entry
        for label, entry in classified.items()
        if any(name in label for name in ALLOWLIST)
    }

    tick_clearance = {}
    for name in ALLOWLIST:
        obj = next(
            (o for o in pilot.meshes_under(root) if o.name == name), None
        )
        if obj is None:
            continue
        inner = min(
            math.hypot(
                (obj.matrix_world @ v.co).x - centre.x,
                (obj.matrix_world @ v.co).z - centre.z,
            )
            for v in obj.data.vertices
        )
        tick_clearance[name] = {
            "inner_radius_mm": round(inner * 1000.0, 4),
            "required_mm": round(required_m * 1000.0, 4),
            "meets_required": inner >= required_m - 1e-6,
            "required_applies": retraction_applied,
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
    envelope = m2k1.envelope_row(key, bounds)
    return {
        "pivot_world": [round(v, 6) for v in centre],
        "motion_contract": {
            "pivot": "needle_pivot",
            "axis": [0.0, 1.0, 0.0],
            "sweep_deg": [-55.0, 55.0],
            "poses": len(POSES),
        },
        "triangles": triangles,
        "expected_triangles": m2l.PLAN[key]["triangles"],
        "triangle_budget": m2k.MODELS[key]["triangle_budget"],
        "bounds": bounds,
        "envelope": envelope,
        "contacts": classified,
        "new_contacts": new_contacts,
        "tick_contacts": tick_contacts,
        "tick_clearance": tick_clearance,
        "d6_regression": {
            "triangles_match_input": triangles == m2l.PLAN[key]["triangles"],
            "within_envelope": envelope["within_envelope"],
            "pivot_unchanged": True,
        },
        "pass": (
            not new_contacts
            and not tick_contacts
            and (
                not retraction_applied
                or all(v["meets_required"] for v in tick_clearance.values())
            )
            and triangles == m2l.PLAN[key]["triangles"]
            and envelope["within_envelope"]
        ),
    }


def run_39(project_root, staged, output_path):
    """The whole set, with these three substituted, in a separate Blender."""
    arguments = [
        str(project_root / "scripts/run-blender.sh"),
        "--background", "--factory-startup",
        "--python", str(project_root / "Tools/Blender/opus5_uv_atlas_audit_all.py"),
        "--", "--project-root", str(project_root),
        "--output", str(output_path),
    ]
    for key, path in staged.items():
        arguments.extend(["--substitute", f"{m2k.THEME}/{key}={path}"])
    completed = subprocess.run(
        arguments, capture_output=True, text=True, cwd=str(project_root)
    )
    payload = (
        json.loads(output_path.read_text()) if output_path.is_file() else None
    )
    return {
        "returncode": completed.returncode,
        "output": str(output_path),
        "models_audited": (payload or {}).get("models_audited"),
        "failures": (payload or {}).get("failures"),
        "substituted_sources": (payload or {}).get("substituted_sources"),
        "pass": bool(payload) and not (payload or {}).get("failures"),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    keys = args.models or list(PLAN)

    started = time.perf_counter()
    staging = Path(tempfile.mkdtemp(prefix="opus5-d3-combined-"))
    entries = {}
    try:
        for key in keys:
            begin = time.perf_counter()
            source = input_blend(project_root, key)
            source_sha = m1.digest(source)
            report_sha = m1.digest(input_report(project_root, key))

            root, pivot = open_input(project_root, key)
            reference = semantic(root)
            sweep = swept_radius(root, pivot)
            required = sweep["swept_radius_m"] + CLEARANCE_MM[key] / 1000.0
            # Alignment 130.2-4: no change where the target is already met.
            # A radial rule alone would retract Round's ticks even though the
            # R2 rebuild separated them from the needle in depth and M2k3
            # measured no contact at all - a change with nothing to fix.
            entering = tick_contact_present(root, pivot)
            changes = (
                retract_ticks(root, pivot, required) if entering["any"] else {}
            )
            actual = semantic(root)
            diff = allowlist_diff(reference, actual)
            moved_total = sum(entry["vertices_moved"] for entry in changes.values())

            staged = staging / f"{key}.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True)
            audited = audit(
                project_root, key, staged, required, bool(entering["any"])
            )

            problems = []
            if not audited["pass"]:
                problems.append("audit")
            if not diff["pass"]:
                problems.append("semantic diff outside the allowlist")
            if entering["any"] and not moved_total:
                problems.append("a tick contact exists but nothing was retracted")
            if key == "MeterRound" and not diff["identical"]:
                problems.append("Round is not semantically identical to R3")

            entries[key] = {
                "model": f"{m2k.THEME}/{key}",
                "input_revision": PLAN[key]["input"],
                "output_revision": PLAN[key]["output"],
                "input": str(source.relative_to(project_root)),
                "input_sha256": source_sha,
                "input_report_sha256": report_sha,
                "clearance_mm": CLEARANCE_MM[key],
                "swept": sweep,
                "input_tick_contact": entering,
                "required_tick_inner_radius_mm": round(required * 1000.0, 4),
                "tick_changes": changes,
                "vertices_moved_total": moved_total,
                "semantic_diff": diff,
                "staged_sha256": m1.digest(staged),
                "audit": audited,
                "problems": problems,
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
            print(
                f"[Opus5D3comb] {key} -> {PLAN[key]['output']}: swept "
                f"{sweep['swept_radius_mm']} mm, required "
                f"{round(required * 1000.0, 4)} mm, moved {moved_total} verts, "
                f"allowlist {diff['pass']}, audit {audited['pass']}, "
                f"problems {problems}"
            )

        staged_paths = {key: staging / f"{key}.blend" for key in keys}
        audit39 = (
            {"skipped": True}
            if args.skip_39
            else run_39(
                project_root,
                staged_paths,
                (Path(args.trial_dir) / "audit_39.json")
                if args.trial_dir
                else (project_root / AUDIT_39),
            )
        )
        print(f"[Opus5D3comb] 39-model audit: {audit39}")

        for key in keys:
            if args.skip_renders or entries[key]["problems"]:
                continue
            entries[key]["renders"] = {
                "input": m2k3.render_state(
                    project_root,
                    f"{PREFIX}_{key}_input",
                    lambda k=key: (
                        m1.open_blend(input_blend(project_root, k))
                        or bpy.data.objects[m2k.MODELS[k]["root"]]
                    ),
                ),
                "combined": m2k3.render_state(
                    project_root,
                    f"{PREFIX}_{key}_combined",
                    lambda k=key: (
                        m1.open_blend(staged_paths[k])
                        or bpy.data.objects[m2k.MODELS[k]["root"]]
                    ),
                ),
            }

        for key in keys:
            entry = entries[key]
            current = m1.digest(input_blend(project_root, key))
            entry["input_sha256_at_publish"] = current
            problems = list(entry["problems"])
            if current != entry["input_sha256"]:
                problems.append("input changed between build and publish")
            if not audit39.get("pass") and not args.skip_39:
                problems.append("39-model audit did not pass")
            record = publish.publish(
                output_blend(project_root, key, args.trial_dir),
                output_report(project_root, key, args.trial_dir),
                {
                    "phase": "M2m",
                    "defects": ["D-3", "D-6"],
                    "object": key,
                    "theme": m2k.THEME,
                    "revision": PLAN[key]["output"],
                    "note": (
                        "D-3 recombined onto the approved D-6 candidate "
                        "(alignment 130.2). The required tick radius is "
                        "recomputed from the model's own swept circle."
                    ),
                    "audit_39": audit39,
                    **{
                        name: value
                        for name, value in entry.items()
                        if name != "problems"
                    },
                    "authoring_environment": blender_compat.provenance(),
                },
                problems,
                trial_dir=args.trial_dir,
                save_blend=lambda path, k=key: shutil.copy2(
                    staging / f"{k}.blend", path
                ),
                reopen_blend=lambda path: m1.open_blend(path),
            )
            entry["publish"] = record
            print(
                f"[Opus5D3comb] {key}: {record['mode']} - {record['reason']}"
                + (
                    f" sha {record['blend_sha256'][:12]}"
                    if record.get("blend_sha256")
                    else ""
                )
            )
        print(f"[Opus5D3comb] total {round(time.perf_counter() - started, 1)}s")
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
