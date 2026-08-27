"""Build isolated meter candidates without duplicate cover-ring scales.

Some MeterMedium and MeterLarge sources contain a second scale family named
``secondary_scale_*``.  Those marks sit in front of the glass gasket / cover
ring, while the theme's normal dial scale remains behind the needle.  The
result reads as markings printed on the cover and duplicates the dial scale.

This script removes only that second family from copies of Retopo sources.  By
default it reads the shipped sources, but ``--source-dir`` and
``--source-suffix`` allow an already-approved revision (for example D3_D4) to
be used as the immutable input.  It never writes to the input source.  The run
fails unless the expected component counts and the complete inventory of every
retained object are unchanged.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/meter_cover_scale_cleanup.py -- \
      --project-root "$PWD" --theme ForgeBrass \
      --output-dir /private/tmp/forge-glass-cleanup
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat


DEFAULT_THEME = "OrbitalAnalog"
REVISION = "Codex_G1"
TARGETS = {
    "MeterMedium": 17,
    "MeterLarge": 25,
}
REMOVE_PREFIX = "secondary_scale_"
PRIMARY_TICKS = {
    "OrbitalAnalog": ("orbital_tick_", 17),
    "ForgeBrass": ("forge_tick_", 21),
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--theme", choices=tuple(PRIMARY_TICKS), default=DEFAULT_THEME
    )
    parser.add_argument(
        "--source-dir",
        help="source directory relative to project root, or an absolute path",
    )
    parser.add_argument(
        "--source-suffix",
        default="_Retopo",
        help="filename suffix after V6 and before .blend (default: _Retopo)",
    )
    parser.add_argument("--object", dest="object_key", choices=tuple(TARGETS))
    parser.add_argument("--revision", default=REVISION)
    return parser.parse_args(args)


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def rounded_matrix(matrix):
    return [[round(value, 9) for value in row] for row in matrix]


def object_fingerprint(obj):
    entry = {
        "type": obj.type,
        "parent": obj.parent.name if obj.parent else None,
        "matrix_local": rounded_matrix(obj.matrix_local),
        "matrix_world": rounded_matrix(obj.matrix_world),
    }
    if obj.type == "MESH":
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        entry.update(
            {
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "materials": [
                    slot.material.name if slot.material else None
                    for slot in obj.material_slots
                ],
                "bounds": {
                    "min": [
                        round(min(point[axis] for point in points), 9)
                        for axis in range(3)
                    ],
                    "max": [
                        round(max(point[axis] for point in points), 9)
                        for axis in range(3)
                    ],
                },
            }
        )
    return entry


def inventory():
    return {
        obj.name: object_fingerprint(obj)
        for obj in sorted(bpy.context.scene.objects, key=lambda item: item.name)
    }


def source_path(project_root, source_dir, source_suffix, theme, key):
    directory = (
        Path(source_dir)
        if source_dir
        else Path("ArtSource/Blender/ThemeHardSurfaceV6") / theme
    )
    if not directory.is_absolute():
        directory = project_root / directory
    return directory / f"BL_{key}_{theme}_V6{source_suffix}.blend"


def build_one(
    project_root, output_dir, source_dir, source_suffix, theme, key, revision
):
    source = source_path(project_root, source_dir, source_suffix, theme, key)
    if not source.is_file():
        raise RuntimeError(f"{key}: input source not found: {source}")
    stat_before = source.stat()
    sha_before = digest(source)
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)

    root_name = f"PF_Visual_{key}_{theme}_V6"
    root = bpy.data.objects.get(root_name)
    pivot = bpy.data.objects.get("needle_pivot")
    needle = bpy.data.objects.get("needle")
    if root is None or pivot is None or needle is None:
        raise RuntimeError(f"{key}: root / needle_pivot / needle contract missing")

    before = inventory()
    removable = sorted(
        obj.name
        for obj in root.children_recursive
        if obj.type == "MESH" and obj.name.startswith(REMOVE_PREFIX)
    )
    expected = TARGETS[key]
    if len(removable) != expected:
        raise RuntimeError(
            f"{key}: expected {expected} {REMOVE_PREFIX} objects, got {removable}"
        )
    expected_names = [f"{REMOVE_PREFIX}{index:02d}" for index in range(expected)]
    if removable != expected_names:
        raise RuntimeError(
            f"{key}: secondary scale names changed: {removable} != {expected_names}"
        )

    primary_prefix, primary_count = PRIMARY_TICKS[theme]
    primary = sorted(
        obj.name
        for obj in root.children_recursive
        if obj.type == "MESH" and obj.name.startswith(primary_prefix)
    )
    if len(primary) != primary_count:
        raise RuntimeError(
            f"{key}: expected {primary_count} primary dial ticks, got {primary}"
        )

    for name in removable:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.context.view_layer.update()

    after = inventory()
    retained_before = {
        name: value for name, value in before.items() if name not in removable
    }
    if after != retained_before:
        changed = sorted(
            name
            for name in set(after) | set(retained_before)
            if after.get(name) != retained_before.get(name)
        )
        raise RuntimeError(f"{key}: retained object inventory changed: {changed}")
    if any(name.startswith(REMOVE_PREFIX) for name in after):
        raise RuntimeError(f"{key}: a secondary scale object remains")

    root["cover_scale_cleanup"] = revision
    root["cover_scale_removed"] = expected
    root["cover_scale_policy"] = "dial markings only; cover ring unmarked"

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"BL_{key}_{theme}_V6_{revision}_Retopo.blend"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(target), compress=True, copy=True)
    target.with_suffix(".blend1").unlink(missing_ok=True)

    stat_after = source.stat()
    sha_after = digest(source)
    if (stat_after.st_size, stat_after.st_mtime_ns, sha_after) != (
        stat_before.st_size,
        stat_before.st_mtime_ns,
        sha_before,
    ):
        raise RuntimeError(f"{key}: input source changed during candidate build")

    return {
        "theme": theme,
        "object": key,
        "revision": revision,
        "source": str(source),
        "source_sha256": sha_before,
        "candidate": str(target),
        "candidate_sha256": digest(target),
        "removed": removable,
        "removed_count": len(removable),
        "primary_dial_ticks_retained": primary,
        "primary_dial_tick_count": len(primary),
        "retained_inventory_unchanged": True,
        "input_source_unchanged": True,
        "root": root_name,
        "pivot": pivot.name,
        "needle": needle.name,
    }


def main():
    blender_compat.require_v6_pipeline()
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    keys = (args.object_key,) if args.object_key else tuple(TARGETS)
    report = {
        "status": "PASS",
        "purpose": "remove duplicate cover-ring markings; retain dial scale",
        "results": [
            build_one(
                project_root,
                output_dir,
                args.source_dir,
                args.source_suffix,
                args.theme,
                key,
                args.revision,
            )
            for key in keys
        ],
        "authoring_environment": blender_compat.provenance(),
    }
    report_path = output_dir / "meter_cover_scale_cleanup.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
