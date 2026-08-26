"""Independent cylindrical tool-path audit for Theme 4 Batch A R3.

The delivery generator checks the distance from the screw axis to vertices in
the tool span.  That is useful evidence, but a large triangle can cross the
tool cylinder while all of its vertices remain outside it.  This audit casts
parallel rays across the complete driver cross-section against the delivered
body mesh, so any face blocking the straight insertion path is detected.

Run Blender with one R3 .blend file loaded, then pass the matching asset name::

    blender file.blend --background --python this_script.py -- \
        --asset Throttle --output report.json
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SPECS = {
    "Throttle": {
        "body": "Throttle_body",
        "screw_x": 0.0975,
        "screw_z": 0.1505,
        "path_start_y": -0.0440,
        "path_end_y": -0.0216,
        "required_radius_m": 0.0082,
    },
    "PowerSlider": {
        "body": "PowerSlider_body",
        "screw_x": 0.0620,
        "screw_z": 0.1430,
        "path_start_y": -0.0430,
        "path_end_y": -0.0206,
        "required_radius_m": 0.0082,
    },
}


def arguments():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", choices=sorted(SPECS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--angular-samples", type=int, default=96)
    parser.add_argument("--radial-rings", type=int, default=8)
    parser.add_argument("--required-radius-mm", type=float)
    return parser.parse_args(raw)


def world_bvh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    matrix = evaluated.matrix_world
    vertices = [matrix @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=True)
    evaluated.to_mesh_clear()
    return tree


def sample_offsets(radius, rings, angles):
    yield 0.0, 0.0, 0, 0
    for ring in range(1, rings + 1):
        # Keep the outer samples just inside the required cylinder.  A hit at
        # 99.5% radius means the nominal tool cannot pass with useful margin.
        radial = radius * 0.995 * ring / rings
        count = max(12, round(angles * ring / rings))
        for index in range(count):
            angle = 2.0 * math.pi * index / count
            yield radial * math.cos(angle), radial * math.sin(angle), ring, index


def main():
    args = arguments()
    spec = SPECS[args.asset]
    required_radius = (args.required_radius_mm / 1000.0
                       if args.required_radius_mm is not None
                       else spec["required_radius_m"])
    body = bpy.data.objects.get(spec["body"])
    if body is None or body.type != "MESH":
        raise RuntimeError(f"Missing mesh {spec['body']}")

    tree = world_bvh(body)
    start_y = spec["path_start_y"] - 0.00005
    end_y = spec["path_end_y"] + 0.00005
    distance = end_y - start_y
    direction = Vector((0.0, 1.0, 0.0))
    holes = {}
    total_rays = 0

    for sx in (-1, 1):
        for sz in (-1, 1):
            centre_x = sx * spec["screw_x"]
            centre_z = sz * spec["screw_z"]
            hits = []
            tested = 0
            for offset_x, offset_z, ring, index in sample_offsets(
                    required_radius, args.radial_rings,
                    args.angular_samples):
                origin = Vector((centre_x + offset_x, start_y,
                                 centre_z + offset_z))
                location, normal, face_index, hit_distance = tree.ray_cast(
                    origin, direction, distance)
                tested += 1
                total_rays += 1
                if location is not None:
                    hits.append({
                        "ring": ring,
                        "sample": index,
                        "offset_x_mm": round(offset_x * 1000.0, 6),
                        "offset_z_mm": round(offset_z * 1000.0, 6),
                        "hit_y_m": round(location.y, 9),
                        "distance_mm": round(hit_distance * 1000.0, 6),
                        "face_index": face_index,
                        "normal": [round(value, 6) for value in normal],
                    })
            label = f"{sx}_{sz}"
            holes[label] = {
                "axis_xz_m": [centre_x, centre_z],
                "rays_tested": tested,
                "blocking_hits": hits,
                "open": not hits,
            }

    report = {
        "asset": args.asset,
        "blend": bpy.data.filepath,
        "method": "parallel BVH ray grid over 99.5% of required driver cylinder",
        "required_radius_mm": required_radius * 1000.0,
        "path_y_m": [spec["path_start_y"], spec["path_end_y"]],
        "angular_samples": args.angular_samples,
        "radial_rings": args.radial_rings,
        "total_rays": total_rays,
        "holes": holes,
        "all_open": all(hole["open"] for hole in holes.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "asset": args.asset,
        "all_open": report["all_open"],
        "total_rays": total_rays,
        "hit_count": sum(len(hole["blocking_hits"])
                         for hole in holes.values()),
        "output": str(args.output),
    }))
    if not report["all_open"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
