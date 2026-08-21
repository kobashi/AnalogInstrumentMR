"""Phase M2n2b1: calibrate the adapter on scenes whose answers are known.

Alignment 162.1 / 166. M2n2b's world-difference figure was meaningless because
the adapter fed the matcher data it had never been tested on: vertices paired
by sort order, one UV layer, and no statement about which frame or which mesh
evaluation the numbers came from. Before any of that touches a canonical
source again, it is calibrated here against small scenes built for the purpose.

Every measurement is made root-relative - `inverse(root.matrix_world) @
obj.matrix_world` - so an axis conversion applied on export and undone on
import cannot masquerade as a moved part. Corners are paired by geometry, never
by index, and both the face normal and the split (loop) normal are compared.
Every UV layer is read by name, not just the active one.

No canonical Blend is opened. The scenes, the FBX and the re-import all live in
a temporary directory, and only the fixture JSON is kept.

Modes:

* `build`    - make each scene, measure it raw and evaluated, export the FBX
* `reimport` - fresh process: read each FBX back and measure it
* `report`   - compare against expectations and write the fixture JSON

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_fbx_adapter_calibration.py -- \
      --project-root "$PWD" --mode build --staging /tmp/x
"""

import argparse
import itertools
import json
import math
import sys
import time
import traceback
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_meter_fbx_handoff as m2n


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/fbx_adapter_calibration.json"
POSITION_BOUND_M = 1.0e-5
NORMAL_BOUND_DEG = 0.5
UV_ULP = 2.0 * (2.0 ** -23)
CORNER_TOLERANCE_M = 1.0e-4


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("build", "reimport", "report"))
    parser.add_argument("--staging", required=True)
    return parser.parse_args(args)


# --------------------------------------------------------------------------
# Scene construction


def fresh():
    bpy.ops.wm.read_homefile(use_empty=True)
    root = bpy.data.objects.new("PF_Visual_Calibration", None)
    bpy.context.collection.objects.link(root)
    return root


def plane(name, root, size=0.2, uv_layers=("UVMap",), seam=False):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = root
    half = size / 2.0
    verts = [
        (-half, 0.0, -half), (half, 0.0, -half),
        (half, 0.0, half), (-half, 0.0, half),
    ]
    faces = [(0, 1, 2, 3)]
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    for index, layer_name in enumerate(uv_layers):
        layer = mesh.uv_layers.new(name=layer_name)
        for loop_index, datum in enumerate(layer.data):
            base = (loop_index % 4) / 4.0
            offset = 0.5 if (seam and index == 0 and loop_index >= 2) else 0.0
            datum.uv = (base + offset + index * 0.1, base * 0.5 + index * 0.1)
    return obj


def build_scenes():
    """Each case is one scene with one thing different about it."""
    cases = {}

    def case(name, make):
        root = fresh()
        made = make(root)
        bpy.context.view_layer.update()
        cases[name] = {"root": root, "objects": made}
        return cases[name]

    return [
        ("parent_transform", lambda root: _parent_transform(root)),
        ("non_uniform_scale", lambda root: _scaled(root)),
        ("micro_rotation", lambda root: _micro_rotation(root)),
        ("vertex_reorder", lambda root: _plain(root)),
        ("uv_seam", lambda root: _seam(root)),
        ("multi_uv", lambda root: _multi_uv(root)),
        ("no_uv", lambda root: _no_uv(root)),
        ("modifier", lambda root: _modifier(root)),
        ("split_normal", lambda root: _split_normal(root)),
    ]


def _plain(root):
    return [plane("plain", root)]


def _parent_transform(root):
    holder = bpy.data.objects.new("holder", None)
    bpy.context.collection.objects.link(holder)
    holder.parent = root
    holder.location = (0.3, -0.15, 0.05)
    holder.rotation_euler = (0.2, 0.4, 0.1)
    obj = plane("under_parent", root)
    obj.parent = holder
    return [obj]


def _scaled(root):
    obj = plane("scaled", root)
    obj.scale = (1.7, 0.6, 1.15)
    return [obj]


def _micro_rotation(root):
    obj = plane("micro_rotation", root)
    obj.rotation_euler = (0.0, math.radians(6.147170e-05), 0.0)
    return [obj]


def _seam(root):
    return [plane("seam", root, seam=True)]


def _multi_uv(root):
    obj = plane("multi_uv", root, uv_layers=("UVMap", "Second"))
    obj.data.uv_layers.active = obj.data.uv_layers["Second"]
    return [obj]


def _no_uv(root):
    obj = plane("no_uv", root, uv_layers=())
    return [obj]


def _modifier(root):
    obj = plane("with_modifier", root)
    modifier = obj.modifiers.new("subdivide", "SUBSURF")
    modifier.levels = 1
    modifier.render_levels = 1
    return [obj]


def _split_normal(root):
    obj = plane("split_normal", root)
    obj.data.shade_smooth()
    return [obj]


# --------------------------------------------------------------------------
# Measurement


def root_relative(root, obj):
    return root.matrix_world.inverted() @ obj.matrix_world


def read(obj, root, evaluated):
    """Corners, normals and every UV layer, in the root's frame."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = obj.evaluated_get(depsgraph) if evaluated else obj
    mesh = target.to_mesh() if evaluated else obj.data
    mesh.calc_loop_triangles()
    try:
        mesh.calc_normals_split()
    except (AttributeError, RuntimeError):
        pass
    matrix = root_relative(root, obj)
    normal_matrix = matrix.to_3x3().inverted_safe().transposed()
    triangles = []
    for triangle in mesh.loop_triangles:
        corners = []
        for loop_index in triangle.loops:
            loop = mesh.loops[loop_index]
            position = matrix @ mesh.vertices[loop.vertex_index].co
            split = (normal_matrix @ Vector(loop.normal)).normalized()
            corners.append(
                {
                    "position": [position.x, position.y, position.z],
                    "split_normal": [split.x, split.y, split.z],
                    "uv": {
                        layer.name: list(layer.data[loop_index].uv)
                        for layer in mesh.uv_layers
                    },
                }
            )
        face = (normal_matrix @ Vector(triangle.normal)).normalized()
        triangles.append(
            {"corners": corners, "face_normal": [face.x, face.y, face.z],
             "material": triangle.material_index}
        )
    payload = {
        "triangles": triangles,
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "active_uv_layer": (
            mesh.uv_layers.active.name if mesh.uv_layers.active else None
        ),
        "loop_triangles": len(mesh.loop_triangles),
        "root_relative_matrix": [[v for v in row] for row in matrix],
    }
    if evaluated:
        target.to_mesh_clear()
    return payload


def measure_scene(root, evaluated):
    return {
        obj.name: read(obj, root, evaluated)
        for obj in root.children_recursive
        if obj.type == "MESH"
    }


# --------------------------------------------------------------------------
# Comparison


def match_triangles(source, reimport):
    """Pair triangles by geometry alone, one to one."""
    pool = list(range(len(reimport)))
    pairs = []
    unmatched = []
    for index, triangle in enumerate(source):
        best = None
        for position in pool:
            other = reimport[position]
            if other["material"] != triangle["material"]:
                continue
            for permutation in itertools.permutations(range(3)):
                distance = max(
                    math.dist(
                        triangle["corners"][i]["position"],
                        other["corners"][mapped]["position"],
                    )
                    for i, mapped in enumerate(permutation)
                )
                if best is None or distance < best[0]:
                    best = (distance, position, permutation)
        if best is None or best[0] > CORNER_TOLERANCE_M:
            unmatched.append(index)
            continue
        pool.remove(best[1])
        pairs.append((index, best[1], best[2], best[0]))
    return pairs, unmatched, pool


def angle_between(first, second):
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(first, second))))
    return math.degrees(math.acos(dot))


def compare(source, reimport):
    rows = {}
    for name in sorted(set(source) | set(reimport)):
        first = source.get(name)
        second = reimport.get(name)
        if first is None or second is None:
            rows[name] = {"status": "missing on one side", "pass": False}
            continue
        pairs, unmatched, leftover = match_triangles(
            first["triangles"], second["triangles"]
        )
        position_max = 0.0
        position_total = 0.0
        face_max = 0.0
        split_max = 0.0
        count = 0
        uv_max = {}
        for i, j, permutation, _ in pairs:
            a = first["triangles"][i]
            b = second["triangles"][j]
            face_max = max(face_max, angle_between(a["face_normal"], b["face_normal"]))
            for index, mapped in enumerate(permutation):
                ca = a["corners"][index]
                cb = b["corners"][mapped]
                distance = math.dist(ca["position"], cb["position"])
                position_max = max(position_max, distance)
                position_total += distance * distance
                count += 1
                split_max = max(
                    split_max, angle_between(ca["split_normal"], cb["split_normal"])
                )
                for layer, value in ca["uv"].items():
                    if layer not in cb["uv"]:
                        uv_max.setdefault(layer, {"missing": True, "max": None})
                        continue
                    other = cb["uv"][layer]
                    worst = max(
                        abs(other[k] - value[k]) / (UV_ULP * max(1.0, abs(value[k])))
                        for k in (0, 1)
                    )
                    entry = uv_max.setdefault(layer, {"missing": False, "max": 0.0})
                    entry["max"] = max(entry["max"] or 0.0, worst)
        rows[name] = {
            "status": "compared",
            "expected_triangles": len(first["triangles"]),
            "matched_triangles": len(pairs),
            "unmatched_source": len(unmatched),
            "unconsumed_reimport": len(leftover),
            "coverage": len(pairs) / max(len(first["triangles"]), 1),
            "corners_compared": count,
            "max_position_difference_m": position_max,
            "max_position_difference_um": position_max * 1e6,
            "rms_position_difference_m": (
                math.sqrt(position_total / count) if count else 0.0
            ),
            "max_face_normal_deg": face_max,
            "max_split_normal_deg": split_max,
            "uv_layers": [first["uv_layers"], second["uv_layers"]],
            "active_uv_layer": [first["active_uv_layer"], second["active_uv_layer"]],
            "uv_worst_ulp": {k: v["max"] for k, v in uv_max.items()},
            "uv_missing_layers": [k for k, v in uv_max.items() if v["missing"]],
            "root_relative_matrix_max_diff": max(
                abs(first["root_relative_matrix"][r][c]
                    - second["root_relative_matrix"][r][c])
                for r in range(4)
                for c in range(4)
            ),
            "pass": (
                not unmatched
                and not leftover
                and position_max <= POSITION_BOUND_M
                and face_max <= NORMAL_BOUND_DEG
                and split_max <= NORMAL_BOUND_DEG
                and all(
                    (value["max"] or 0.0) <= 1.0 and not value["missing"]
                    for value in uv_max.values()
                )
            ),
        }
    return rows


# --------------------------------------------------------------------------
# Modes


def do_build(staging):
    staging.mkdir(parents=True, exist_ok=True)
    payload = {}
    for name, make in build_scenes():
        root = fresh()
        make(root)
        bpy.context.view_layer.update()
        raw = measure_scene(root, evaluated=False)
        evaluated = measure_scene(root, evaluated=True)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in [root] + list(root.children_recursive):
            obj.select_set(True)
        bpy.context.view_layer.objects.active = root
        target = staging / f"{name}.fbx"
        bpy.ops.export_scene.fbx(filepath=str(target), **m2n.EXPORT_SETTINGS)
        payload[name] = {
            "fbx": str(target),
            "fbx_sha256": m1.digest(target),
            "raw": raw,
            "evaluated": evaluated,
        }
        print(f"[Opus5Adapter] build {name}: {len(raw)} meshes")
    (staging / "source.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def do_reimport(staging):
    source = json.loads((staging / "source.json").read_text())
    payload = {}
    for name in source:
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(staging / f"{name}.fbx"))
        root = next(
            obj for obj in bpy.data.objects if obj.name.startswith("PF_Visual_")
        )
        payload[name] = measure_scene(root, evaluated=False)
        print(f"[Opus5Adapter] reimport {name}: {len(payload[name])} meshes")
    (staging / "reimport.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


def do_report(project_root, staging):
    payload = {
        "phase": "M2n2b1",
        "note": (
            "Adapter calibration on purpose-built scenes (alignment 162.1, "
            "166). No canonical source is opened; nothing is published."
        ),
        "frame": "root-relative: inverse(root.matrix_world) @ obj.matrix_world",
        "bounds": {
            "position_m": POSITION_BOUND_M,
            "normal_deg": NORMAL_BOUND_DEG,
            "uv_ulp": 1.0,
            "corner_match_tolerance_m": CORNER_TOLERANCE_M,
        },
    }
    started = time.perf_counter()
    try:
        source = json.loads((staging / "source.json").read_text())
        reimport = json.loads((staging / "reimport.json").read_text())
        cases = {}
        for name, entry in source.items():
            against = "evaluated" if name == "modifier" else "raw"
            rows = compare(entry[against], reimport.get(name, {}))
            cases[name] = {
                "compared_against": against,
                "fbx_sha256": entry["fbx_sha256"],
                "objects": rows,
                "pass": all(row["pass"] for row in rows.values()),
            }
        payload["cases"] = cases
        payload["all_passed"] = all(case["pass"] for case in cases.values())
        payload["status"] = "complete" if payload["all_passed"] else "fixture failure"
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / OUTPUT
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        cases = payload.get("cases", {})
        print(
            f"[Opus5Adapter] {len(cases)} cases, all_passed="
            f"{payload.get('all_passed')}, status {payload.get('status')}"
        )
        for name, case in cases.items():
            if case["pass"]:
                continue
            for obj, row in case["objects"].items():
                if row.get("pass"):
                    continue
                print(
                    f"  FAIL {name}/{obj}: coverage {row.get('coverage')} "
                    f"pos {row.get('max_position_difference_um')} um "
                    f"face {row.get('max_face_normal_deg')} deg "
                    f"split {row.get('max_split_normal_deg')} deg "
                    f"uv {row.get('uv_worst_ulp')} layers {row.get('uv_layers')}"
                )


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    if args.mode != "report":
        blender_compat.require_v6_pipeline()
    if args.mode == "build":
        do_build(staging)
    elif args.mode == "reimport":
        do_reimport(staging)
    else:
        do_report(project_root, staging)


if __name__ == "__main__":
    main()
