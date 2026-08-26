"""Theme 4 Phase 1: measure the instruments we are about to re-author.

Read-only. Opens the V6 ProductionReady sources for meter.round, control.lever
and control.toggle and reports the authoring frame, the envelope, the pivot
placement and the movable hierarchy - so the Machined Ergonomics greybox is
built against measurements rather than against an assumption about which axis
is up and which way the instrument faces.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_reference_survey.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat

SOURCE_DIR = "ArtSource/Blender/ThemeHardSurfaceV6/{theme}"
BLEND = "BL_{asset}_{theme}_V6_ProductionReady.blend"
ASSETS = ("MeterRound", "Lever", "Toggle")
THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
OUTPUT = "ArtSource/Blender/BrushUp/Opus5/theme4_reference_survey.json"


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def root_of(objects):
    roots = [obj for obj in objects if obj.parent is None]
    return roots[0] if len(roots) == 1 else None


def world_bounds(objects):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            point = obj.matrix_world @ type(obj.matrix_world.to_translation())(corner)
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])
    if lo[0] == float("inf"):
        return None
    return {
        "min": [round(value, 6) for value in lo],
        "max": [round(value, 6) for value in hi],
        "size": [round(hi[i] - lo[i], 6) for i in range(3)],
    }


def survey(path):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    objects = list(bpy.data.objects)
    root = root_of(objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    triangles = 0
    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
    pivots = {}
    for obj in objects:
        if "pivot" in obj.name or "travel" in obj.name:
            local = obj.matrix_local.to_translation()
            world = obj.matrix_world.to_translation()
            pivots[obj.name] = {
                "type": obj.type,
                "parent": obj.parent.name if obj.parent else None,
                "children": sorted(child.name for child in obj.children),
                "local_translation": [round(value, 6) for value in local],
                "world_translation": [round(value, 6) for value in world],
                "rotation_mode": obj.rotation_mode,
            }
    return {
        "root": root.name if root else None,
        "root_scale": [round(value, 6) for value in root.scale] if root else None,
        "objects": sorted(obj.name for obj in objects),
        "mesh_objects": len(meshes),
        "materials": sorted({slot.material.name for obj in meshes
                             for slot in obj.material_slots if slot.material}),
        "triangles": triangles,
        "bounds_world": world_bounds(objects),
        "pivots": pivots,
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    payload = {"note": "read-only survey of the V6 sources; nothing is saved",
               "assets": {}}
    for asset in ASSETS:
        payload["assets"][asset] = {}
        for theme in THEMES:
            path = (project_root / SOURCE_DIR.format(theme=theme)
                    / BLEND.format(asset=asset, theme=theme))
            if not path.is_file():
                payload["assets"][asset][theme] = {"missing": str(path)}
                continue
            payload["assets"][asset][theme] = survey(path)
            print(f"[Theme4Survey] {asset} / {theme}: "
                  f"{payload['assets'][asset][theme]['triangles']} tris")
    payload["authoring_environment"] = blender_compat.provenance()
    out = project_root / OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[Theme4Survey] wrote {OUTPUT}")


if __name__ == "__main__":
    main()
