"""Gate A candidates for defect D-1: the Button themes emit nothing.

`docs/V6_KNOWN_DEFECTS.md` D-1 - the V6 detail pass clears every mesh under
`button_travel` and rebuilds the island from body and metal only, so V5's
`button_glyph` never comes back and all three Button themes ship with no
readout-role surface at all. `generate_theme_hardsurface_v6_remaining` now
rebuilds it behind `restore_glyph`, off by default so the production path is
unchanged (alignment 5.3, 49.2).

This script generates the candidates through that same production builder
rather than hand-editing a shipped Retopo blend, so the candidate is exactly
what production will emit once the stop gate opens. It generates each Button
twice - with and without the flag - and reports the difference, which is how it
shows the glyph is the *only* change.

Every candidate is written under `ArtSource/Blender/BrushUp/Opus5/<Theme>/`.
Production Retopo, ProductionReady, Unity FBX, prefab, material, texture and
`.meta` are never touched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_button_glyph_candidate.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_hardsurface_lever_retopo_v3 as retopo
import generate_orbital_analog_meter as common
import generate_theme_hardsurface_v6_remaining as gen
import generate_theme_silhouette_v5 as v5
import generate_theme_silhouette_v5_remaining as v5r
import opus5_publish as publishing
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot


KEY = "Button"
REVISION = "D1"
THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")

# docs/OPUS5_3D_MODEL_BRUSHUP_HANDOFF.md line 159: "14 mm押下でguideへ不自然に
# 貫通しない". The travel empty moves inward, and outward is -Y.
TRAVEL_METRES = 0.014
TRAVEL_SAMPLES = 29

TRIANGLE_BUDGET = 5_000
MATERIAL_BUDGET = 2

# The static parts the plunger passes through by construction. Contact with
# these is an interface, not a defect; contact with anything else is.
INTERFACE_TOKENS = ("guide", "gasket")

# The author scene carries two material sets - `v5r.BUILDERS` makes one and the
# V6 detail pass makes another - so names arrive as both `MAT_X_V5_Body` and
# `MAT_X_V5_Body.001`. That is how production already generates, and the atlas
# pass keys on the role suffix, so the contract is checked on roles rather than
# on the raw datablock count.
# `gasket` is assigned from the object-name token, not from a material, so it
# is a role the author scene legitimately carries alongside the three above.
AUTHOR_ROLES = {"body", "metal", "gasket", "readout"}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append", choices=THEMES)
    parser.add_argument("--revision", default=REVISION)
    return parser.parse_args(args)


def build(theme, restore_glyph):
    """One Button, through the production builder and detail pass."""
    common.clean_scene()
    root, pivot_position, local_axis = v5r.BUILDERS[KEY](theme)
    root.name = f"PF_Visual_{KEY}_{theme}_V6"
    root["art_pass"] = "V6 hybrid hard-surface prototype"
    root["quality_floor"] = "V4 hard-surface retopo"
    root["mechanical_rules"] = (
        "flush fasteners, supported marks, visible pivots and fitted joints"
    )
    root["assembly_policy"] = (
        "gaskets, seams, bushings, stops and supports explain construction"
    )
    mats = v5.materials(theme)
    gen.add_detail(root, theme, KEY, mats, pivot_position, restore_glyph)
    meshes = gen.meshes_under(root)
    common.apply_transforms(meshes)
    return root, meshes, pivot_position, local_axis


def hierarchy(root):
    def node(obj):
        return {
            "name": obj.name,
            "type": obj.type,
            "children": [node(child) for child in sorted(
                obj.children, key=lambda item: item.name
            )],
        }

    return node(root)


def travel_audit(root, travel):
    """Sweep 0..14 mm and record which part pairs actually penetrate.

    `BVHTree.overlap` is a broad phase only, so every pair it returns is run
    through the exact triangle-triangle test before it is counted (alignment
    8.2).

    The result is deliberately reported per pair rather than as one number.
    Some overlaps are interfaces the design intends (the plunger slides through
    its guide bore and its gasket) and some are pre-existing in the shipped V6
    geometry; neither is Gate A's business. What Gate A must show is that
    restoring the glyph introduces no pair the baseline did not already have,
    so the caller diffs this against the same audit run on the baseline.
    """
    movable = [obj for obj in gen.meshes_under(root) if _under(obj, travel)]
    statics = [obj for obj in gen.meshes_under(root) if not _under(obj, travel)]
    if not movable:
        raise RuntimeError("no mesh under button_travel")

    static_trees = []
    for obj in statics:
        tree, vertices, polygons = pilot.bvh_for(obj)
        static_trees.append((obj.name, tree, vertices, polygons))

    base = travel.location.copy()
    pairs = {}
    try:
        for index in range(TRAVEL_SAMPLES):
            depth = TRAVEL_METRES * index / (TRAVEL_SAMPLES - 1)
            travel.location = base + Vector((0.0, depth, 0.0))
            bpy.context.view_layer.update()

            for obj in movable:
                tree, vertices, polygons = pilot.bvh_for(obj)
                for name, other, other_vertices, other_polygons in static_trees:
                    hits = 0
                    for mine, theirs in tree.overlap(other):
                        first = [vertices[i] for i in polygons[mine]]
                        second = [
                            other_vertices[i] for i in other_polygons[theirs]
                        ]
                        if pilot.triangle_contact_points(first, second):
                            hits += 1
                    if not hits:
                        continue
                    label = f"{obj.name} x {name}"
                    entry = pairs.setdefault(
                        label,
                        {
                            "interface": any(
                                token in name.lower() for token in INTERFACE_TOKENS
                            ),
                            "samples": 0,
                            "max_triangles": 0,
                            "first_travel_mm": round(depth * 1000.0, 3),
                        },
                    )
                    entry["samples"] += 1
                    entry["max_triangles"] = max(entry["max_triangles"], hits)
    finally:
        travel.location = base
        bpy.context.view_layer.update()

    return {
        "travel_mm": round(TRAVEL_METRES * 1000.0, 3),
        "samples": TRAVEL_SAMPLES,
        "movable_meshes": sorted(obj.name for obj in movable),
        "static_meshes": sorted(obj.name for obj in statics),
        "interface_pairs": {
            label: entry
            for label, entry in sorted(pairs.items())
            if entry["interface"]
        },
        "non_interface_pairs": {
            label: entry
            for label, entry in sorted(pairs.items())
            if not entry["interface"]
        },
    }


def _under(obj, parent):
    node = obj
    while node is not None:
        if node is parent:
            return True
        node = node.parent
    return False


def glyph_clearance(root, travel):
    """How far the glyph stays clear of the guide across the whole travel.

    Reported as a distance rather than only as a contact count so a future
    change that merely grazes the guide is visible before it starts failing.
    """
    glyph = next(
        (obj for obj in gen.meshes_under(root) if obj.name.startswith("button_glyph")),
        None,
    )
    if glyph is None:
        return None
    guides = [
        obj
        for obj in gen.meshes_under(root)
        if "guide" in obj.name.lower()
    ]
    if not guides:
        return {"guides": [], "note": "no guide mesh in this theme"}

    base = travel.location.copy()
    worst = None
    try:
        for index in range(TRAVEL_SAMPLES):
            depth = TRAVEL_METRES * index / (TRAVEL_SAMPLES - 1)
            travel.location = base + Vector((0.0, depth, 0.0))
            bpy.context.view_layer.update()
            back = max(
                (glyph.matrix_world @ Vector(corner)).y for corner in glyph.bound_box
            )
            front = min(
                min(
                    (guide.matrix_world @ Vector(corner)).y
                    for corner in guide.bound_box
                )
                for guide in guides
            )
            # Outward is -Y: the glyph is clear while its rearmost point is
            # still outward of the guide's frontmost point.
            gap = front - back
            if worst is None or gap < worst[0]:
                worst = (gap, depth)
    finally:
        travel.location = base
        bpy.context.view_layer.update()

    return {
        "guides": sorted(obj.name for obj in guides),
        "min_clearance_mm": round(worst[0] * 1000.0, 4),
        "at_travel_mm": round(worst[1] * 1000.0, 3),
    }


def measure(theme, restore_glyph):
    root, meshes, pivot_position, local_axis = build(theme, restore_glyph)
    source_stats = retopo.topology_stats(meshes)
    triangulated, per_object = pilot.triangulated_stats(meshes)
    roles = pilot.material_role_summary(meshes)
    materials = sorted({
        material.name
        for obj in meshes
        for material in obj.data.materials
        if material is not None
    })
    travel = gen.descendant_named(root, "button_travel")
    return root, {
        "theme": theme,
        "restore_glyph": restore_glyph,
        "root": root.name,
        "hierarchy": hierarchy(root),
        "meshes": sorted(obj.name for obj in meshes),
        "triangles": triangulated["faces"],
        "triangles_by_object": dict(sorted(per_object.items())),
        "source_topology": source_stats,
        "triangulated_topology": triangulated,
        "materials": materials,
        "material_roles": roles,
        "bounds": pilot.world_bounds(meshes),
        "pivot": {
            "authored_position": [round(value, 9) for value in pivot_position],
            "local_axis": [round(value, 9) for value in local_axis],
            "travel_empty": pilot.pivot_state(travel),
        },
        "root_properties": {
            key: root[key] for key in sorted(root.keys()) if not key.startswith("_")
        },
    }, travel


def shipped_inventory(project_root, theme):
    """Mesh inventory and triangle counts of the Retopo blend on disk.

    "The production path is unchanged" is worth more as a measurement than as
    an assertion: the baseline build below has to reproduce what actually
    shipped, not merely what the flag-off code path happens to emit today.
    Opening the blend also proves the file was not written by this run.
    """
    path = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{KEY}_{theme}_V6_Retopo.blend"
    )
    if not path.is_file():
        raise FileNotFoundError(path)
    before = path.stat()
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{KEY}_{theme}_V6"]
    meshes = gen.meshes_under(root)
    _, per_object = pilot.triangulated_stats(meshes)
    after = path.stat()
    if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
        raise RuntimeError(f"{path} changed while being read")
    return {
        "blend": str(path.relative_to(project_root)),
        "mtime_ns": after.st_mtime_ns,
        "size_bytes": after.st_size,
        "meshes": sorted(obj.name for obj in meshes),
        "triangles_by_object": dict(sorted(per_object.items())),
        "material_roles": pilot.material_role_summary(meshes),
    }


def run_one(project_root, theme, revision):
    blender_compat.require_v6_pipeline()

    shipped = shipped_inventory(project_root, theme)

    # Baseline first: the same builder with the flag off has to reproduce the
    # shipped defect, or the comparison below means nothing.
    baseline_root, baseline, baseline_travel = measure(theme, False)
    baseline["travel_audit"] = travel_audit(baseline_root, baseline_travel)
    root, candidate, travel = measure(theme, True)

    candidate["travel_audit"] = travel_audit(root, travel)
    candidate["glyph_clearance"] = glyph_clearance(root, travel)

    added = sorted(set(candidate["meshes"]) - set(baseline["meshes"]))
    removed = sorted(set(baseline["meshes"]) - set(candidate["meshes"]))
    changed = sorted(
        name
        for name in set(baseline["triangles_by_object"])
        & set(candidate["triangles_by_object"])
        if baseline["triangles_by_object"][name]
        != candidate["triangles_by_object"][name]
    )

    failures = []
    if baseline["meshes"] != shipped["meshes"]:
        failures.append(
            "flag-off build does not reproduce the shipped blend: "
            f"{sorted(set(baseline['meshes']) ^ set(shipped['meshes']))}"
        )
    shipped_triangle_diff = sorted(
        name
        for name in set(shipped["triangles_by_object"])
        & set(baseline["triangles_by_object"])
        if shipped["triangles_by_object"][name]
        != baseline["triangles_by_object"][name]
    )
    if shipped_triangle_diff:
        failures.append(
            f"flag-off triangles differ from the shipped blend: "
            f"{shipped_triangle_diff}"
        )
    if "readout" in shipped["material_roles"]:
        failures.append("the shipped blend already has a readout role")
    if added != ["button_glyph"] or removed or changed:
        failures.append(
            f"candidate differs beyond the glyph: added {added}, "
            f"removed {removed}, retopologised {changed}"
        )
    if "readout" in baseline["material_roles"]:
        failures.append("baseline already has a readout role; D-1 does not apply")
    if "readout" not in candidate["material_roles"]:
        failures.append("candidate still has no readout role")
    if candidate["triangles"] > TRIANGLE_BUDGET:
        failures.append(
            f"{candidate['triangles']} triangles > {TRIANGLE_BUDGET}"
        )
    extra_roles = set(candidate["material_roles"]) - AUTHOR_ROLES
    if extra_roles:
        failures.append(f"unexpected author roles: {sorted(extra_roles)}")
    runtime = runtime_material_count(candidate["material_roles"])
    if runtime > MATERIAL_BUDGET:
        failures.append(f"runtime materials {runtime} > {MATERIAL_BUDGET}")
    if candidate["source_topology"]["non_manifold_edges"]:
        failures.append("non-manifold source")
    if candidate["source_topology"]["zero_area_faces"]:
        failures.append("degenerate source")
    if candidate["triangulated_topology"]["zero_area_faces"]:
        failures.append("degenerate after triangulation")
    # Gate A must not make travel worse. Pairs the baseline already has are
    # pre-existing V6 geometry and are reported, not failed, so they stay
    # visible for Gate B/C instead of being silently blessed here.
    def pair_set(report):
        audit = report["travel_audit"]
        return set(audit["interface_pairs"]) | set(audit["non_interface_pairs"])

    new_pairs = sorted(pair_set(candidate) - pair_set(baseline))
    pre_existing = sorted(
        label
        for label in candidate["travel_audit"]["non_interface_pairs"]
        if label in pair_set(baseline)
    )
    if new_pairs:
        failures.append(f"restoring the glyph adds contact pairs: {new_pairs}")
    glyph_pairs = sorted(
        label for label in pair_set(candidate) if label.startswith("button_glyph")
    )
    if glyph_pairs:
        failures.append(f"the glyph itself contacts: {glyph_pairs}")
    clearance = candidate["glyph_clearance"]
    if clearance and clearance.get("min_clearance_mm", 1.0) <= 0.0:
        failures.append(
            f"glyph enters the guide (min clearance "
            f"{clearance['min_clearance_mm']} mm)"
        )

    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme
    blend = candidate_dir / f"BL_{KEY}_{theme}_V6_Opus5_{revision}_Retopo.blend"
    report_path = (
        candidate_dir / "reports" / f"{KEY}_{theme}_V6_Opus5_{revision}.json"
    )

    report = {
        "defect": "D-1",
        "key": KEY,
        "theme": theme,
        "revision": revision,
        "generator": (
            "generate_theme_hardsurface_v6_remaining.add_detail("
            "restore_glyph=True)"
        ),
        "production_path_touched": False,
        "shipped_production_blend": shipped,
        "candidate_blend": str(blend.relative_to(project_root)),
        "difference_from_baseline": {
            "meshes_added": added,
            "meshes_removed": removed,
            "meshes_retopologised": changed,
            "triangles_baseline": baseline["triangles"],
            "triangles_candidate": candidate["triangles"],
            "roles_baseline": sorted(baseline["material_roles"]),
            "roles_candidate": sorted(candidate["material_roles"]),
            "travel_pairs_added": new_pairs,
        },
        # Out of Gate A's scope but recorded rather than dropped: these overlaps
        # are in the shipped V6 geometry with or without the glyph.
        "pre_existing_non_interface_overlaps": {
            label: candidate["travel_audit"]["non_interface_pairs"][label]
            for label in pre_existing
        },
        "author_material_duplicates": sorted(
            name for name in candidate["materials"] if "." in name.rsplit("_", 1)[-1]
        ),
        "baseline": baseline,
        "candidate": candidate,
        "runtime_material_count": runtime,
        "triangle_budget": TRIANGLE_BUDGET,
        "failures": failures,
        "authoring_environment": blender_compat.provenance(),
    }

    # Alignment 73.4: never replace a published revision, never leave a report
    # behind for a run that failed, and publish blend and report together.
    report["publish"] = publishing.publish(
        blend,
        report_path,
        report,
        failures,
        save_blend=pilot.save_blend,
        reopen_blend=lambda path: bpy.ops.wm.open_mainfile(
            filepath=str(path), load_ui=False
        ),
    )
    if failures:
        raise RuntimeError(f"{theme}/{KEY}: " + "; ".join(failures))
    print(
        f"[Opus5ButtonD1] {theme}: {candidate['triangles']} tris "
        f"(+{candidate['triangles'] - baseline['triangles']}), "
        f"roles {'+'.join(sorted(candidate['material_roles']))}, "
        f"runtime {runtime}, "
        f"guide clearance {clearance['min_clearance_mm']} mm, "
        f"new travel pairs {len(new_pairs)}, "
        f"pre-existing {len(pre_existing)}"
    )
    return report


def runtime_material_count(roles):
    """body/metal/gasket collapse onto the opaque atlas; readout is emissive."""
    opaque = any(role in roles for role in ("body", "metal", "gasket"))
    emissive = "readout" in roles
    return int(opaque) + int(emissive)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    themes = tuple(args.themes) if args.themes else THEMES
    reports = [run_one(project_root, theme, args.revision) for theme in themes]
    summary = (
        project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / f"button_glyph_{args.revision.lower()}_summary.json"
    )
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(
        json.dumps(
            {
                "defect": "D-1",
                "revision": args.revision,
                "themes": {
                    report["theme"]: {
                        "triangles": report["candidate"]["triangles"],
                        "triangles_added": (
                            report["candidate"]["triangles"]
                            - report["baseline"]["triangles"]
                        ),
                        "roles": sorted(report["candidate"]["material_roles"]),
                        "runtime_materials": report["runtime_material_count"],
                        "min_guide_clearance_mm": report["candidate"][
                            "glyph_clearance"
                        ]["min_clearance_mm"],
                        "travel_pairs_added": report["difference_from_baseline"][
                            "travel_pairs_added"
                        ],
                        "pre_existing_non_interface_overlaps": sorted(
                            report["pre_existing_non_interface_overlaps"]
                        ),
                    }
                    for report in reports
                },
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5ButtonD1] summary -> {summary.relative_to(project_root)}")


if __name__ == "__main__":
    main()
