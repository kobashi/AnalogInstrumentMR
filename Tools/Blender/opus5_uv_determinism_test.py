"""Pin down the determinism of the constant-density atlas UV pass.

Codex review item 5.3: the pass places each part's sub-rectangle inside its role
quadrant using a hash of the object name, so two properties have to be held by a
test rather than by assumption.

1. Determinism. Running the pass twice on the same source must produce byte
   identical UVs. If it does not, candidate atlases and staging FBX stop being
   reproducible.
2. Rename isolation. Renaming one object must move only that object's
   sub-rectangle. Everything else must keep its UVs exactly. This is the price
   of hashing the name, and the report records how far a renamed part moves so
   the consequence is visible rather than surprising.

Exits non-zero if either property fails. Read-only: no blend is saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_uv_determinism_test.py -- \
      --project-root "$PWD" --output <report.json>
"""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_pilot as pilot
import opus5_uv_atlas_pass as uv_pass


RENAME_SUFFIX = "_uvtest"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--revision", default="R2")
    parser.add_argument("--output", required=True)
    return parser.parse_args(args)


def uv_state(root):
    """UV bounds per (object, role) plus a hash over every coordinate.

    Keyed by role, not just by object: the pass places one sub-rectangle per
    role group, so a mesh carrying both metal and body faces legitimately spans
    two quadrants and a per-object bounding box would report a meaningless
    union of them.
    """
    digest = hashlib.sha256()
    rects = {}
    for obj in sorted(root.children_recursive, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        uv_layer = obj.data.uv_layers.active
        if uv_layer is None:
            continue
        roles = uv_pass.polygon_roles(obj)
        by_role = {}
        for polygon, role in zip(obj.data.polygons, roles):
            for index in polygon.loop_indices:
                by_role.setdefault(role, []).append(tuple(uv_layer.data[index].uv))
        digest.update(obj.name.encode("utf-8"))
        for index in range(len(uv_layer.data)):
            u, v = uv_layer.data[index].uv
            # The float32 bit pattern, not a formatted string: the test claims
            # the UVs are byte identical, so it has to hash the bytes.
            digest.update(struct.pack("<2f", u, v))
        for role, coordinates in by_role.items():
            rects[f"{obj.name}/{role}"] = [
                round(min(u for u, _ in coordinates), 6),
                round(min(v for _, v in coordinates), 6),
                round(max(u for u, _ in coordinates), 6),
                round(max(v for _, v in coordinates), 6),
            ]
    return digest.hexdigest(), rects


def run_pass(source, root_name, scale_class, rename=None):
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[root_name]
    renamed_from = None
    if rename is not None:
        target = bpy.data.objects[rename]
        renamed_from = target.name
        target.name = f"{renamed_from}{RENAME_SUFFIX}"
    uv_pass.apply(root, scale_class)
    digest, rects = uv_state(root)
    return digest, rects, renamed_from


def pick_rename_target(source, root_name):
    """First static mesh whose name carries no gasket token.

    A gasket token in the name decides the material role, so renaming one of
    those would change more than the hash and would not isolate the property
    under test.
    """
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[root_name]
    for obj in sorted(root.children_recursive, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        if any(token in obj.name.lower() for token in pilot.GASKET_TOKENS):
            continue
        return obj.name
    raise RuntimeError(f"{root_name}: no rename target without a gasket token")


def check_one(source, root_name, scale_class):
    first_digest, first_rects, _ = run_pass(source, root_name, scale_class)
    second_digest, second_rects, _ = run_pass(source, root_name, scale_class)

    failures = []
    if first_digest != second_digest:
        differing = sorted(
            name
            for name in first_rects
            if first_rects.get(name) != second_rects.get(name)
        )
        failures.append(
            "repeated runs produced different UVs; first differing objects: "
            + ", ".join(differing[:5])
        )

    rename_failures = []
    target = pick_rename_target(source, root_name)
    _, renamed_rects, renamed_from = run_pass(
        source, root_name, scale_class, rename=target
    )
    renamed_key = f"{renamed_from}{RENAME_SUFFIX}"

    # Compare the two key sets symmetrically, mapping only the renamed object's
    # keys across. A role group that appears or disappears anywhere else is a
    # failure, which a one-directional walk over the "before" keys would miss.
    def remap(key):
        object_name, _, role = key.partition("/")
        return f"{renamed_key}/{role}" if object_name == renamed_from else key

    expected_keys = {remap(key) for key in first_rects}
    actual_keys = set(renamed_rects)
    if expected_keys != actual_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        rename_failures.append(
            "rename changed the set of role groups; "
            f"missing {missing[:5]}, unexpected {extra[:5]}"
        )

    moved = []
    for key, rect in first_rects.items():
        if key.partition("/")[0] == renamed_from:
            continue
        if renamed_rects.get(key) != rect:
            moved.append(key)
    if moved:
        rename_failures.append(
            "renaming one object moved others: " + ", ".join(sorted(moved)[:5])
        )

    shifts = {}
    for key, rect in first_rects.items():
        object_name, _, role = key.partition("/")
        if object_name != renamed_from:
            continue
        after = renamed_rects.get(f"{renamed_key}/{role}")
        if after is None:
            rename_failures.append(f"renamed object lost its {role} group")
            continue
        shifts[role] = [
            round(after[0] - rect[0], 6),
            round(after[1] - rect[1], 6),
        ]

    # Guard against a vacuous pass: if the new name happened to hash into the
    # same cell, the run proves nothing about rename sensitivity.
    if shifts and not any(
        shift[0] or shift[1] for shift in shifts.values()
    ):
        rename_failures.append(
            f"renaming '{renamed_from}' moved no sub-rectangle, so this sample "
            "does not exercise the hash placement; pick a different target"
        )

    failures.extend(rename_failures)
    return {
        "root": root_name,
        "scale_class": scale_class,
        "uv_hash": first_digest,
        "repeat_run_identical": first_digest == second_digest,
        # Counted per (object, role), not per object: one mesh with metal and
        # body faces contributes two sub-rectangles in two quadrants.
        "sub_rects": len(first_rects),
        "rename_isolation": {
            "renamed_object": renamed_from,
            "sub_rect_shift_by_role": shifts,
            "other_objects_unchanged": not moved,
            # Every rename-related property, not just "nothing else moved":
            # the summary line counts this so a key-set or zero-shift failure
            # cannot be reported as an isolated pass.
            "passed": not (moved or rename_failures),
        },
        "failures": failures,
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    candidate_dir = project_root / "ArtSource/Blender/BrushUp/Opus5" / pilot.THEME

    models = {}
    failures = []
    for key, spec in pilot.PILOT.items():
        source = (
            candidate_dir
            / f"BL_{key}_{pilot.THEME}_V6_Opus5_{args.revision}_Retopo.blend"
        )
        if not source.is_file():
            failures.append(f"{key}: missing {source.name}")
            continue
        result = check_one(source, spec["root"], "Standard")
        models[key] = result
        failures.extend(f"{key}: {item}" for item in result["failures"])

    report = {
        "note": (
            "Determinism and rename isolation of the constant-density atlas UV "
            "pass. The sub-rectangle origin inside each role quadrant comes "
            "from a SHA-256 of '<object name>/<role>', so renaming a part "
            "changes where it samples the shared tiling detail. That is by "
            "design and harmless for a tiling material, but it means object "
            "renames are a UV change and should be reviewed as one."
        ),
        "revision": args.revision,
        "models": models,
        "failures": failures,
        "authoring_environment": blender_compat.provenance(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        f"[UVDeterminism] {len(models)} models, "
        f"{sum(1 for m in models.values() if m['repeat_run_identical'])} "
        f"reproducible, "
        f"{sum(1 for m in models.values() if m['rename_isolation']['passed'])} "
        f"rename-isolated, {len(failures)} failures"
    )
    for key, model in models.items():
        rename = model["rename_isolation"]
        shifts = ", ".join(
            f"{role} {value}" for role, value in sorted(rename["sub_rect_shift_by_role"].items())
        )
        print(
            f"  {key}: hash {model['uv_hash'][:12]}, "
            f"{model['sub_rects']} sub-rects, "
            f"rename '{rename['renamed_object']}' moved {shifts}"
        )
    for failure in failures:
        print(f"  FAIL {failure}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
