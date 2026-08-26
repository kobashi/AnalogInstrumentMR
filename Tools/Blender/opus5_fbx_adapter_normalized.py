"""Phase M2n2b1a: measure what is exported, not what happens to be in the file.

Alignment 168.1 / 170 / 172. The previous adapter measured the source as
Blender happened to triangulate it and compared that with whatever the FBX
exporter chose, so two identical planes disagreed on every triangle. The fix is
to stop guessing: a temporary copy is evaluated, explicitly triangulated, and
then that same copy is both measured and exported. Nothing downstream has to
re-derive a triangulation.

Four snapshots are kept apart - source raw, source evaluated, the
export-normalized copy, and the re-import - so a difference can be attributed
to the modifier stack, to the triangulation, or to the format, rather than to
all three at once.

Coverage decides whether a number means anything. Where nothing was compared,
max and RMS are `null` and `measurement_valid` is false; a zero that nobody
measured is not evidence, which is the mistake alignment 168 caught twice.

Corners are paired by the mesh-wide assignment A5 proved, never by index.

No canonical source and none of the real-model staging is opened.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_fbx_adapter_normalized.py -- \
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
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_fbx_adapter_calibration as cal
import opus5_meter_fbx_handoff as m2n
from opus5_fbx_verifier_selftest_a3 import MinCostMaxFlow


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/fbx_adapter_normalized.json"
POSITION_BOUND_M = 1.0e-5
NORMAL_BOUND_DEG = 0.5
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
# Scenes


def scenes():
    """Each case isolates one thing the format might change."""
    return [
        ("parent_transform", cal._parent_transform),
        ("non_uniform_scale", cal._scaled),
        ("micro_rotation", cal._micro_rotation),
        ("vertex_reorder", _reordered),
        ("uv_seam", cal._seam),
        ("multi_uv", cal._multi_uv),
        ("multi_uv_render", _multi_uv_render),
        ("no_uv", cal._no_uv),
        ("modifier", cal._modifier),
        ("hard_edge", _hard_edge),
        ("non_planar_quad", _non_planar),
    ]


def _reordered(root):
    """A real reorder: the same surface with its vertices renumbered."""
    obj = cal.plane("reordered", root)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    mesh.verts.ensure_lookup_table()
    for vertex in mesh.verts:
        vertex.index = (vertex.index + 2) % len(mesh.verts)
    mesh.verts.sort()
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    return [obj]


def _multi_uv_render(root):
    """Active and render deliberately disagree.

    In `cal._multi_uv` the render layer is still the first one, so a report
    that the render layer survived says nothing about the exporter. Here the
    two flags point at different layers, which is the only arrangement that
    can distinguish them.
    """
    obj = cal.plane("multi_uv_render", root, uv_layers=("UVMap", "Second"))
    obj.data.uv_layers.active = obj.data.uv_layers["UVMap"]
    obj.data.uv_layers["Second"].active_render = True
    return [obj]


def _hard_edge(root):
    obj = cal.plane("hard_edge", root)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    result = bmesh.ops.extrude_face_region(mesh, geom=mesh.faces[:])
    moved = [g for g in result["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(mesh, vec=Vector((0.0, 0.08, 0.0)), verts=moved)
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    obj.data.shade_smooth()
    for edge in obj.data.edges:
        edge.use_edge_sharp = True
    return [obj]


def _non_planar(root):
    obj = cal.plane("non_planar", root)
    obj.data.vertices[2].co.y += 0.05
    obj.data.update()
    return [obj]


# --------------------------------------------------------------------------
# Snapshots


def triangulated_copy(root):
    """Evaluated, explicitly triangulated, and the thing that gets exported."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    holder = bpy.data.objects.new(f"{root.name}_export", None)
    bpy.context.collection.objects.link(holder)
    holder.matrix_world = root.matrix_world.copy()
    made = []
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(
            evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
        )
        copy = bpy.data.objects.new(obj.name, mesh)
        bpy.context.collection.objects.link(copy)
        copy.matrix_world = obj.matrix_world.copy()
        copy.parent = holder
        copy.matrix_parent_inverse = holder.matrix_world.inverted()
        work = bmesh.new()
        work.from_mesh(mesh)
        bmesh.ops.triangulate(work, faces=work.faces[:])
        work.to_mesh(mesh)
        work.free()
        mesh.update()
        made.append(copy)
    bpy.context.view_layer.update()
    return holder, made


def all_triangles(root):
    for obj in root.children_recursive:
        if obj.type != "MESH":
            continue
        for polygon in obj.data.polygons:
            if len(polygon.vertices) != 3:
                return False
    return True


def snapshot(root, evaluated):
    """measure_scene plus the render UV layer, which alignment 172 asks for.

    The active layer and the render layer are two independent flags and the
    exporter does not have to treat them alike, so both are read by name.
    """
    payload = cal.measure_scene(root, evaluated=evaluated)
    for obj in root.children_recursive:
        if obj.type != "MESH" or obj.name not in payload:
            continue
        render = [
            layer.name for layer in obj.data.uv_layers if layer.active_render
        ]
        payload[obj.name]["render_uv_layer"] = render[0] if render else None
    return payload


# --------------------------------------------------------------------------
# Matching


def assign(source, reimport):
    """Mesh-wide one-to-one triangle assignment, A5's solver."""
    costs = {}
    for i, first in enumerate(source):
        for j, second in enumerate(reimport):
            if first["material"] != second["material"]:
                continue
            best = None
            for permutation in itertools.permutations(range(3)):
                distance = max(
                    math.dist(
                        first["corners"][index]["position"],
                        second["corners"][mapped]["position"],
                    )
                    for index, mapped in enumerate(permutation)
                )
                if best is None or distance < best[0]:
                    best = (distance, permutation)
            if best and best[0] <= CORNER_TOLERANCE_M:
                costs[(i, j)] = {"distance": best[0], "permutation": best[1]}
    if not costs:
        return [], len(source), len(reimport)
    scale = 10 ** 9
    size = len(source) + len(reimport) + 2
    source_node = len(source) + len(reimport)
    sink = source_node + 1
    flow = MinCostMaxFlow(size)
    for i in range(len(source)):
        flow.add(source_node, i, 1, 0)
    for j in range(len(reimport)):
        flow.add(len(source) + j, sink, 1, 0)
    index_of = {}
    for (i, j), value in costs.items():
        index_of[(i, j)] = len(flow.edges)
        flow.add(i, len(source) + j, 1, int(round(value["distance"] * scale)))
    flow.run(source_node, sink)
    pairs = [
        (i, j, costs[(i, j)]["permutation"])
        for (i, j), index in index_of.items()
        if flow.edges[index][1] == 0
    ]
    return pairs, len(source) - len(pairs), len(reimport) - len(pairs)


def compare(source, reimport):
    rows = {}
    for name in sorted(set(source) | set(reimport)):
        first = source.get(name)
        second = reimport.get(name)
        if first is None or second is None:
            rows[name] = {
                "status": "missing on one side",
                "measurement_valid": False,
                "pass": False,
            }
            continue
        pairs, unmatched, leftover = assign(
            first["triangles"], second["triangles"]
        )
        expected = len(first["triangles"])
        coverage = len(pairs) / expected if expected else 0.0
        position_max = None
        position_total = 0.0
        face_max = None
        split_max = None
        count = 0
        uv = {}
        for i, j, permutation in pairs:
            a = first["triangles"][i]
            b = second["triangles"][j]
            angle = cal.angle_between(a["face_normal"], b["face_normal"])
            face_max = angle if face_max is None else max(face_max, angle)
            for index, mapped in enumerate(permutation):
                ca = a["corners"][index]
                cb = b["corners"][mapped]
                distance = math.dist(ca["position"], cb["position"])
                position_max = (
                    distance if position_max is None else max(position_max, distance)
                )
                position_total += distance * distance
                count += 1
                split = cal.angle_between(ca["split_normal"], cb["split_normal"])
                split_max = split if split_max is None else max(split_max, split)
                for layer, value in ca["uv"].items():
                    entry = uv.setdefault(layer, {"missing": False, "worst": 0.0})
                    if layer not in cb["uv"]:
                        entry["missing"] = True
                        continue
                    other = cb["uv"][layer]
                    worst = max(
                        abs(other[k] - value[k])
                        / (cal.UV_ULP * max(1.0, abs(value[k])))
                        for k in (0, 1)
                    )
                    entry["worst"] = max(entry["worst"], worst)
        valid = count > 0 and coverage == 1.0
        rows[name] = {
            "status": "compared",
            "expected_triangles": expected,
            "matched_triangles": len(pairs),
            "unmatched_source": unmatched,
            "unconsumed_reimport": leftover,
            "triangle_coverage": coverage,
            "corners_compared": count,
            "measurement_valid": valid,
            "max_position_difference_m": position_max if valid else None,
            "max_position_difference_um": (
                position_max * 1e6 if valid and position_max is not None else None
            ),
            "rms_position_difference_m": (
                math.sqrt(position_total / count) if valid and count else None
            ),
            "max_face_normal_deg": face_max if valid else None,
            "max_split_normal_deg": split_max if valid else None,
            "uv_layers": [first["uv_layers"], second["uv_layers"]],
            "active_uv_layer": [first["active_uv_layer"], second["active_uv_layer"]],
            "active_uv_preserved": (
                first["active_uv_layer"] == second["active_uv_layer"]
            ),
            "render_uv_layer": [
                first.get("render_uv_layer"),
                second.get("render_uv_layer"),
            ],
            "render_uv_preserved": (
                first.get("render_uv_layer") == second.get("render_uv_layer")
            ),
            "uv_worst_ulp": (
                {k: v["worst"] for k, v in uv.items()} if valid else None
            ),
            "uv_missing_layers": [k for k, v in uv.items() if v["missing"]],
            "pass": (
                valid
                and not unmatched
                and not leftover
                and position_max is not None
                and position_max <= POSITION_BOUND_M
                and (face_max or 0.0) <= NORMAL_BOUND_DEG
                and (split_max or 0.0) <= NORMAL_BOUND_DEG
                and first["uv_layers"] == second["uv_layers"]
                and first["active_uv_layer"] == second["active_uv_layer"]
                and first.get("render_uv_layer") == second.get("render_uv_layer")
                and all(v["worst"] <= 1.0 and not v["missing"] for v in uv.values())
            ),
        }
    return rows


# --------------------------------------------------------------------------
# Modes


def do_build(staging):
    staging.mkdir(parents=True, exist_ok=True)
    payload = {}
    for name, make in scenes():
        for triangles in (True, False):
            root = cal.fresh()
            make(root)
            bpy.context.view_layer.update()
            raw = snapshot(root, evaluated=False)
            evaluated = snapshot(root, evaluated=True)
            holder, made = triangulated_copy(root)
            normalized = snapshot(holder, evaluated=False)
            assert all_triangles(holder), f"{name}: export copy is not triangulated"
            bpy.ops.object.select_all(action="DESELECT")
            for obj in [holder] + list(holder.children_recursive):
                obj.select_set(True)
            bpy.context.view_layer.objects.active = holder
            settings = dict(m2n.EXPORT_SETTINGS)
            settings["use_triangles"] = triangles
            target = staging / f"{name}__tri{int(triangles)}.fbx"
            bpy.ops.export_scene.fbx(filepath=str(target), **settings)
            payload.setdefault(name, {})[f"tri{int(triangles)}"] = {
                "fbx": str(target),
                "fbx_sha256": m1.digest(target),
                "use_triangles": triangles,
                "raw": raw,
                "evaluated": evaluated,
                "normalized": normalized,
            }
        print(f"[Opus5Normalized] build {name}: both use_triangles settings")
    (staging / "source.json").write_text(json.dumps(payload) + "\n", encoding="utf-8")


def do_reimport(staging):
    source = json.loads((staging / "source.json").read_text())
    payload = {}
    for name, variants in source.items():
        payload[name] = {}
        for key, entry in variants.items():
            bpy.ops.wm.read_homefile(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=entry["fbx"])
            root = next(
                obj
                for obj in bpy.data.objects
                if obj.name.startswith("PF_Visual_") and obj.parent is None
            )
            payload[name][key] = snapshot(root, evaluated=False)
        print(f"[Opus5Normalized] reimport {name}")
    (staging / "reimport.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )


def do_report(project_root, staging):
    payload = {
        "phase": "M2n2b1a",
        "note": (
            "Export-normalized adapter fixtures (alignment 168.1 / 170 / 172). "
            "No canonical source and no real-model staging is opened; nothing "
            "is published."
        ),
        "snapshots": ["raw", "evaluated", "normalized", "reimport"],
        "frame": "root-relative",
        "matcher": "A5 mesh-wide one-to-one assignment on triangle corners",
        "validity_rule": (
            "coverage below 100% or zero corners compared reports null and "
            "measurement_valid=false; an unmeasured zero is not evidence"
        ),
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
        for name, variants in source.items():
            entry = {}
            for key, data in variants.items():
                rows = compare(data["normalized"], reimport[name][key])
                entry[key] = {
                    "use_triangles": data["use_triangles"],
                    "fbx_sha256": data["fbx_sha256"],
                    "objects": rows,
                    "pass": all(row["pass"] for row in rows.values()),
                }
            # The copies keep Blender's `.001` suffix because the originals
            # are still in the scene, so the three snapshots are keyed on the
            # stem rather than on the object name as stored.
            def stem(name):
                return name.split(".")[0]

            raw_by_stem = {
                stem(k): v for k, v in variants["tri1"]["raw"].items()
            }
            evaluated_by_stem = {
                stem(k): v for k, v in variants["tri1"]["evaluated"].items()
            }
            entry["normalized_vs_raw_triangles"] = {
                stem(obj): [
                    len(raw_by_stem[stem(obj)]["triangles"])
                    if stem(obj) in raw_by_stem
                    else None,
                    len(evaluated_by_stem[stem(obj)]["triangles"])
                    if stem(obj) in evaluated_by_stem
                    else None,
                    len(value["triangles"]),
                ]
                for obj, value in variants["tri1"]["normalized"].items()
            }
            cases[name] = entry
        payload["cases"] = cases
        payload["use_triangles_choice"] = {
            key: sum(1 for case in cases.values() if case[key]["pass"])
            for key in ("tri0", "tri1")
        }
        payload["all_passed"] = all(
            case["tri1"]["pass"] or case["tri0"]["pass"] for case in cases.values()
        )
        payload["status"] = (
            "complete"
            if all(case["tri1"]["pass"] and case["tri0"]["pass"] for case in cases.values())
            else "fixture failure"
        )
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
            f"[Opus5Normalized] {len(cases)} cases, choice "
            f"{payload.get('use_triangles_choice')}, status {payload.get('status')}"
        )
        for name, case in cases.items():
            for key in ("tri1", "tri0"):
                if case[key]["pass"]:
                    continue
                for obj, row in case[key]["objects"].items():
                    if row.get("pass"):
                        continue
                    print(
                        f"  FAIL {name}/{key}/{obj}: cov {row.get('triangle_coverage')} "
                        f"valid {row.get('measurement_valid')} pos "
                        f"{row.get('max_position_difference_um')} um uv "
                        f"{row.get('uv_worst_ulp')} layers {row.get('uv_layers')} "
                        f"active {row.get('active_uv_layer')} "
                        f"render {row.get('render_uv_layer')}"
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
