"""Measure texel density of the current V6 production UV path.

``export_v6_replacement_candidates.smart_unwrap`` unwraps every mesh with
``scale_to_bounds=True`` *before* the runtime renderers are joined, so each
object's islands are stretched to fill the whole UV square and are then remapped
into a role quadrant. A 3 mm fastener and a 154 mm housing therefore both cover
the full quadrant, and the tiling detail baked into that quadrant appears at
completely different physical sizes from part to part.

This script reproduces that path on a copy and reports texels per metre so the
size of the problem is measured rather than asserted. It writes nothing except
its JSON report and never touches production assets.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_uv_density_audit.py -- \
      --project-root "$PWD" --output <report.json>
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import export_v6_replacement_candidates as export
import opus5_brushup_kinetic_pilot as pilot


ATLAS_PIXELS = 1024


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--revision", default="R2")
    parser.add_argument("--baseline", action="store_true")
    return parser.parse_args(args)


def polygon_uv_area(mesh, polygon, uv_layer):
    points = [uv_layer.data[index].uv for index in polygon.loop_indices]
    total = 0.0
    for index in range(1, len(points) - 1):
        first = points[index] - points[0]
        second = points[index + 1] - points[0]
        total += abs(first.x * second.y - first.y * second.x) * 0.5
    return total


def audit_object(obj):
    """Texels per metre for every face, after the production unwrap."""
    export.smart_unwrap(obj)
    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    scale = obj.matrix_world.to_scale()
    if any(abs(value - 1.0) > 1e-6 for value in scale):
        raise RuntimeError(f"{obj.name}: unapplied scale would skew the audit")
    densities = []
    for polygon in mesh.polygons:
        area = polygon.area
        if area <= 1e-12:
            continue
        uv_area = polygon_uv_area(mesh, polygon, uv_layer)
        if uv_area <= 1e-12:
            continue
        # The quadrant remap multiplies UVs by QUADRANT_SCALE inside a
        # 1024 px atlas, so texel area is (uv_area * scale^2 * pixels^2).
        texel_area = uv_area * (export.QUADRANT_SCALE * ATLAS_PIXELS) ** 2
        densities.append((texel_area / area) ** 0.5)
    if not densities:
        return None
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    extent = max(
        max(point[index] for point in corners) - min(point[index] for point in corners)
        for index in range(3)
    )
    return {
        "object": obj.name,
        "faces": len(densities),
        "longest_extent_m": round(extent, 5),
        "texels_per_metre_min": round(min(densities), 1),
        "texels_per_metre_median": round(statistics.median(densities), 1),
        "texels_per_metre_max": round(max(densities), 1),
    }


def audit_model(source, root_name):
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[root_name]
    entries = []
    for obj in list(root.children_recursive):
        if obj.type != "MESH":
            continue
        entry = audit_object(obj)
        if entry is not None:
            entries.append(entry)
    medians = [entry["texels_per_metre_median"] for entry in entries]
    return {
        "root": root_name,
        "objects": sorted(entries, key=lambda item: item["texels_per_metre_median"]),
        "median_texels_per_metre": round(statistics.median(medians), 1),
        "lowest_object_median": round(min(medians), 1),
        "highest_object_median": round(max(medians), 1),
        "spread_ratio": round(max(medians) / max(min(medians), 1e-6), 1),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    report = {
        "note": (
            "Texels per metre under the current production unwrap "
            "(smart_project with scale_to_bounds=True, then remapped into a "
            "0.46 role quadrant of a 1024 px atlas). A spread_ratio far above "
            "1.0 means the shared tiling detail appears at different physical "
            "sizes on different parts of the same model."
        ),
        "atlas_pixels": ATLAS_PIXELS,
        "quadrant_scale": export.QUADRANT_SCALE,
        "models": {},
    }
    for key, spec in pilot.PILOT.items():
        if args.baseline:
            source = (
                project_root
                / "ArtSource/Blender/ThemeHardSurfaceV6"
                / pilot.THEME
                / f"BL_{key}_{pilot.THEME}_V6_Retopo.blend"
            )
        else:
            source = (
                project_root
                / "ArtSource/Blender/BrushUp/Opus5"
                / pilot.THEME
                / f"BL_{key}_{pilot.THEME}_V6_Opus5_{args.revision}_Retopo.blend"
            )
        report["models"][key] = audit_model(source, spec["root"])

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for key, model in report["models"].items():
        print(
            f"[UVAudit] {key}: median {model['median_texels_per_metre']} tx/m, "
            f"range {model['lowest_object_median']}..."
            f"{model['highest_object_median']}, spread x{model['spread_ratio']}"
        )


if __name__ == "__main__":
    main()
