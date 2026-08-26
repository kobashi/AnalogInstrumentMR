"""Phase M2l: the canonical R3 and B2P candidates.

Alignment 126.2. Three Blends, built from the production baselines with the
designs settled in M2k2 and M2k3 and nothing else.

* Round R3 reproduces R2's `brush_up_meter_round` rebuild. No generic boss,
  counterweight or zone band, and no thin-and-shift: M2k3 established there is
  nothing left for D-6 to act on once the solid twelve-sided bezel is gone.
  Before it is published, a semantic fingerprint - world vertices, polygon
  indices, transform, parent and material slots, per object - is compared with
  the frozen R2. A mismatch stops the publish rather than being explained away
  (alignment 126.1).
* Medium and Large B2P take the full generic assembly with the counterweight
  shifted forward by 6.125 and 7.875 mm, and the shift is read back off the
  saved object rather than trusted from the parameter.

The frozen R2 is opened read-only for fingerprinting and reference rendering.
It is never edited and never saved - which is what M2k3 should have said.

Publishing uses `opus5_publish`'s guard: unique staging, reopen and verify,
Blends first, reports last as the commit marker. There is no force path.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d6_canonical_build.py -- \
      --project-root "$PWD" [--trial-dir /tmp/somewhere]
"""

import argparse
import hashlib
import json
import math
import shutil
import struct
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
import opus5_d6_full_assembly as m2k2
import opus5_d6_repair_decision as m2k
import opus5_d6_round_r3_validation as m2k3
import opus5_publish as publish


REPORT_DIR = "ArtSource/Blender/BrushUp/Opus5/KineticSafety/reports"
PREFIX = "d6_canonical"

PLAN = {
    "MeterRound": {
        "revision": "R3",
        "lineage": "R2 faithful rebuild",
        "triangles": 4636,
        "reference_blend": "BL_MeterRound_KineticSafety_V6_Opus5_R2_Retopo.blend",
    },
    "MeterMedium": {
        "revision": "B2P",
        "lineage": "full generic assembly, counterweight depth 0.7 mm",
        "triangles": 8920,
        "reference_blend": None,
    },
    "MeterLarge": {
        "revision": "B2P",
        "lineage": "full generic assembly, counterweight depth 0.7 mm",
        "triangles": 10472,
        "reference_blend": None,
    },
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
    return parser.parse_args(args)


def theme_dir(project_root):
    return project_root / "ArtSource/Blender/BrushUp/Opus5" / m2k.THEME


def candidate_path(project_root, key, trial_dir):
    name = (
        f"BL_{key}_{m2k.THEME}_V6_Opus5_{PLAN[key]['revision']}_Retopo.blend"
    )
    return (Path(trial_dir) / name) if trial_dir else (theme_dir(project_root) / name)


def report_path(project_root, key, trial_dir):
    name = f"{key}_{m2k.THEME}_V6_Opus5_{PLAN[key]['revision']}.json"
    return (
        (Path(trial_dir) / name)
        if trial_dir
        else (project_root / REPORT_DIR / name)
    )


def fingerprint(root):
    """What "the same model" means, per object, in a form that can be compared.

    Renders cannot show this - they differ by sampling - and a triangle count
    cannot either. Vertices, topology, placement, parentage and material slots
    can (alignment 126.1).
    """
    entries = {}
    for obj in sorted(
        [root] + list(root.children_recursive), key=lambda o: o.name
    ):
        entry = {
            "type": obj.type,
            "parent": obj.parent.name if obj.parent else None,
            "matrix_world": [[round(v, 9) for v in row] for row in obj.matrix_world],
        }
        if obj.type == "MESH":
            matrix = obj.matrix_world
            digest = hashlib.sha256()
            for vertex in obj.data.vertices:
                world = matrix @ vertex.co
                digest.update(struct.pack("<3d", world.x, world.y, world.z))
            topology = hashlib.sha256()
            for polygon in obj.data.polygons:
                topology.update(struct.pack("<i", len(polygon.vertices)))
                for index in polygon.vertices:
                    topology.update(struct.pack("<i", index))
            obj.data.calc_loop_triangles()
            entry.update(
                {
                    "vertices": len(obj.data.vertices),
                    "polygons": len(obj.data.polygons),
                    "loop_triangles": len(obj.data.loop_triangles),
                    "world_vertex_sha256": digest.hexdigest(),
                    "polygon_index_sha256": topology.hexdigest(),
                    "materials": [m.name if m else None for m in obj.data.materials],
                }
            )
        entries[obj.name] = entry
    return entries


def compare_fingerprints(reference, actual):
    missing = sorted(set(reference) - set(actual))
    extra = sorted(set(actual) - set(reference))
    differing = {}
    for name in sorted(set(reference) & set(actual)):
        first, second = reference[name], actual[name]
        difference = {
            key: [first.get(key), second.get(key)]
            for key in (
                "type", "parent", "matrix_world", "vertices", "polygons",
                "loop_triangles", "world_vertex_sha256", "polygon_index_sha256",
                "materials",
            )
            if first.get(key) != second.get(key)
        }
        if difference:
            differing[name] = difference
    return {
        "missing_objects": missing,
        "extra_objects": extra,
        "differing_objects": differing,
        "identical": not missing and not extra and not differing,
    }


def build(project_root, key):
    """The adopted design for this model, in memory."""
    path, root = m2k.open_production(project_root, key)
    if key == "MeterRound":
        result = pilot.brush_up_meter_round(root, pilot.materials_by_role())
        bpy.context.view_layer.update()
        return path, root, {"builder": "brush_up_meter_round", "result": result}

    option = m2k2.adopted_option(project_root, key)
    geometry, built, centre = m2k1.build_parts(root, key, option)
    band, band_facts = m2k2.zone_band(
        root, key, geometry, centre, pilot.materials_by_role()
    )
    if band is not None:
        built["zone_band"] = band
    weight = built["counterweight"]
    points = [weight.matrix_world @ v.co for v in weight.data.vertices]
    return path, root, {
        "builder": "generic assembly (boss, counterweight, zone band)",
        "option": option,
        "zone_band": band_facts,
        "counterweight_world_y": [
            round(min(p.y for p in points), 6),
            round(max(p.y for p in points), 6),
        ],
        "counterweight_rear_y_m": round(max(p.y for p in points), 6),
        "applied_shift_mm": round(
            (max(p.y for p in points) - geometry["needle_y"][0]) * 1000.0, 4
        ),
        "requested_shift_mm": round(option.get("depth_shift_m", 0.0) * 1000.0, 4),
    }


def audit(project_root, key, path):
    """Everything gate 5 asks, on the saved file."""
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
        "inventory": m2e.inventory(root),
        "pivot_world": [round(v, 6) for v in centre],
        "motion_contract": {
            "pivot": "needle_pivot",
            "axis": [0.0, 1.0, 0.0],
            "sweep_deg": [-55.0, 55.0],
            "poses": len(POSES),
        },
        "triangles": triangles,
        "triangle_budget": m2k.MODELS[key]["triangle_budget"],
        "expected_triangles": PLAN[key]["triangles"],
        "bounds": bounds,
        "envelope": envelope,
        "movable_meshes": [obj.name for obj in movable],
        "static_meshes": [obj.name for obj in statics],
        "contacts": classified,
        "new_contacts": new_contacts,
        "pass": (
            not new_contacts
            and envelope["within_envelope"]
            and triangles == PLAN[key]["triangles"]
            and triangles <= m2k.MODELS[key]["triangle_budget"]
        ),
    }


def render(project_root, key, label, opener):
    directory = theme_dir(project_root) / "review"
    directory.mkdir(parents=True, exist_ok=True)
    import opus5_brushup_kinetic_review as review

    root = opener()
    pivot = bpy.data.objects["needle_pivot"]
    centre = pivot.matrix_world.translation.copy()
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
            target = (
                directory / f"{PREFIX}_{key}_{label}_{pose_label}_{view_name}.png"
            )
            review.shot(
                rig, (centre.x, centre.y, centre.z), span * 2.3,
                (view["azimuth"], view["elevation"]), 58.0, target,
            )
            labelled = target.with_name(target.stem + "_labelled.png")
            m2c.label_copy(
                target, labelled,
                [
                    f"{key} {label}".upper()[:36],
                    f"{pose_label} {view_name}".upper(),
                ],
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
    keys = args.models or list(PLAN)

    started = time.perf_counter()
    staging = Path(tempfile.mkdtemp(prefix="opus5-d6-canonical-"))
    entries = {}
    try:
        for key in keys:
            begin = time.perf_counter()
            production = m2k.production_blend(project_root, key)
            source_sha_before = m1.digest(production)

            path, root, made = build(project_root, key)
            actual = fingerprint(root)

            lineage = {"reference": None}
            if PLAN[key]["reference_blend"]:
                frozen = theme_dir(project_root) / PLAN[key]["reference_blend"]
                frozen_sha = m1.digest(frozen)
                # Re-made after the reference is opened, because opening a Blend
                # discards everything built in the previous scene.
                m1.open_blend(frozen)
                reference = fingerprint(bpy.data.objects[m2k.MODELS[key]["root"]])
                path, root, made = build(project_root, key)
                actual = fingerprint(root)
                lineage = {
                    "reference": str(frozen.relative_to(project_root)),
                    "reference_sha256": frozen_sha,
                    "handling": (
                        "opened read-only for reference rendering and "
                        "fingerprinting; never edited or saved"
                    ),
                    "semantic_fingerprint": compare_fingerprints(reference, actual),
                }

            staged = staging / f"{key}.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(staged), copy=True)
            if not staged.is_file():
                raise publish.PublishFailed(f"{key}: nothing was staged")

            audited = audit(project_root, key, staged)
            problems = []
            if not audited["pass"]:
                problems.append("audit")
            if lineage["reference"] and not lineage["semantic_fingerprint"][
                "identical"
            ]:
                problems.append("semantic fingerprint differs from the frozen R2")
            if m1.digest(production) != source_sha_before:
                problems.append("production source changed during the run")

            entries[key] = {
                "model": f"{m2k.THEME}/{key}",
                "revision": PLAN[key]["revision"],
                "lineage": PLAN[key]["lineage"],
                "source": str(production.relative_to(project_root)),
                "source_sha256": source_sha_before,
                "build": made,
                "reference_lineage": lineage,
                "staged_sha256": m1.digest(staged),
                "audit": audited,
                "problems": problems,
                "elapsed_seconds": round(time.perf_counter() - begin, 3),
            }
            print(
                f"[Opus5D6canon] {key} {PLAN[key]['revision']}: tris "
                f"{audited['triangles']}/{PLAN[key]['triangles']}, new "
                f"{audited['new_contacts']}, margin "
                f"{audited['envelope']['margin_mm']} mm, fingerprint "
                f"{lineage.get('semantic_fingerprint', {}).get('identical')}, "
                f"problems {problems}"
            )

        for key in keys:
            if args.skip_renders or entries[key]["problems"]:
                continue
            entries[key]["renders"] = {
                "production": render(
                    project_root, key, "production",
                    lambda k=key: m2k.open_production(project_root, k)[1],
                ),
                "candidate": render(
                    project_root, key, "candidate",
                    lambda k=key: (
                        m1.open_blend(staging / f"{k}.blend")
                        or bpy.data.objects[m2k.MODELS[k]["root"]]
                    ),
                ),
            }

        for key in keys:
            entry = entries[key]
            # Alignment 126.2-1 asks for this immediately before the publish.
            # M2l checked it right after the audit and then rendered every
            # model first, which is not the same moment (alignment 128.1).
            current = m1.digest(m2k.production_blend(project_root, key))
            entry["source_sha256_at_publish"] = current
            if current != entry["source_sha256"]:
                entry["problems"] = entry["problems"] + [
                    "production source changed between build and publish"
                ]
            record = publish.publish(
                candidate_path(project_root, key, args.trial_dir),
                report_path(project_root, key, args.trial_dir),
                {
                    "phase": "M2l",
                    "defect": "D-6",
                    "object": key,
                    "theme": m2k.THEME,
                    "revision": PLAN[key]["revision"],
                    "note": (
                        "Canonical candidate (alignment 126.2). Built from the "
                        "production baseline with the design settled in M2k2 "
                        "and M2k3; the production generator is not modified."
                    ),
                    **{
                        name: value
                        for name, value in entry.items()
                        if name != "problems"
                    },
                    "authoring_environment": blender_compat.provenance(),
                },
                entry["problems"],
                trial_dir=args.trial_dir,
                save_blend=lambda path, k=key: shutil.copy2(
                    staging / f"{k}.blend", path
                ),
                reopen_blend=lambda path: m1.open_blend(path),
            )
            entry["publish"] = record
            print(
                f"[Opus5D6canon] {key}: {record['mode']} - {record['reason']}"
                + (
                    f" sha {record['blend_sha256'][:12]}"
                    if record.get("blend_sha256")
                    else ""
                )
            )
        print(
            f"[Opus5D6canon] total {round(time.perf_counter() - started, 1)}s"
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
