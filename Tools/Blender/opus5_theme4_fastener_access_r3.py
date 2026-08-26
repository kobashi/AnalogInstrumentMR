"""Theme 4 fastener access R3: put the surviving UVs back where R1 had them.

317 accepted R2's geometry and failed its UV gate, and the failure is mine to
own: R2 explained the changed pixels as "atlas repacking", but the four atlas
PNGs are byte-identical to R1's. What actually moved was the mesh UV, because
R2 re-ran unwrap and pack_into_regions on a mesh that had just lost fifteen
screws, and the packer laid the remaining islands out afresh. That repaints
every machined surface on three instruments for no reason connected to the
task, which is exactly what 315.6 froze.

R3 keeps R2's geometry to the vertex and restores the UV by copying it off the
reference FBX, matched the way 317.2 asks: object name, then a one-to-one
correspondence between triangles by their three vertex positions, never by
face or loop order. Positions are matched through a KD-tree against the
reference's own position clusters rather than by rounding, because the
reference has been through float32 in the FBX and a rounding boundary would
split a pair that is 1e-8 apart.

The reference is R1's FBX where R1 shipped one. R1 did not export the meters -
it changed nothing on them - so for those the reference is the accepted Batch A
delivery FBX, which is the same pre-deletion UV and is named per instrument in
the JSON rather than assumed.
"""

import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.kdtree import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

POSITION_TOLERANCE = 2.0e-5       # 0.02 mm, far under any vertex spacing
BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"

# 317.2. Rotary has an R1 FBX; the meters were never re-exported by R1
# because R1 did not touch them, so their pre-deletion UV lives in the
# accepted Batch A delivery.
REFERENCE = {
    "Rotary": (f"{BASE}/fastener_access_r1/"
               "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R1.fbx",
               "fastener_access_r1"),
    "MeterMedium": (f"{BASE}/batch_a/"
                    "SM_MeterMedium_MachinedErgonomics_V6_Opus5_P6A.fbx",
                    "batch_a (R1 did not re-export the meters)"),
    "MeterLarge": (f"{BASE}/batch_a/"
                   "SM_MeterLarge_MachinedErgonomics_V6_Opus5_P6A.fbx",
                   "batch_a (R1 did not re-export the meters)"),
}
TARGETS = tuple(REFERENCE)


def object_key(name):
    return name.split(".")[0]


def read_reference(path):
    """Import an FBX and index every triangle by its three vertex positions.

    Returns, per object: the position clusters and their KD-tree, and a map
    from a sorted triple of cluster ids to the triangle's per-cluster UV.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    bpy.context.view_layer.update()
    rows = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        matrix = obj.matrix_world
        world = [matrix @ vertex.co for vertex in mesh.vertices]

        clusters, cluster_of = [], {}
        for index, point in enumerate(world):
            key = tuple(round(value, 6) for value in point)
            if key not in cluster_of:
                cluster_of[key] = len(clusters)
                clusters.append(key)
            cluster_of[index] = cluster_of[key]
        tree = KDTree(len(clusters))
        for index, point in enumerate(clusters):
            tree.insert(point, index)
        tree.balance()

        uv_layer = mesh.uv_layers.active
        triangles, duplicates = {}, 0
        for tri in mesh.loop_triangles:
            ids = tuple(cluster_of[int(v)] for v in tri.vertices)
            key = tuple(sorted(ids))
            entry = {
                "uv": {cluster: tuple(uv_layer.data[loop].uv)
                       for cluster, loop in zip(ids, tri.loops)},
                "material_index": int(tri.material_index),
            }
            if key in triangles:
                duplicates += 1
                triangles[key].append(entry)
            else:
                triangles[key] = [entry]
        rows[object_key(obj.name)] = {
            "clusters": clusters,
            "tree": tree,
            "triangles": triangles,
            "duplicate_keys": duplicates,
            "triangle_count": len(mesh.loop_triangles),
            "materials": [m.name if m else None for m in mesh.materials],
        }
    return rows


def copy_uv(obj, reference, tolerance=POSITION_TOLERANCE):
    """Copy the reference UV onto every triangle of `obj` that matches one.

    Nothing here looks at face or loop order: a triangle is found by the set
    of its three vertex positions, and within that triangle each loop takes
    the UV of the reference vertex sitting at the same place.
    """
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    tree = reference["tree"]
    table = reference["triangles"]
    uv_layer = mesh.uv_layers.active

    stats = {"triangles": len(mesh.loop_triangles), "matched": 0,
             "unmatched_triangle": 0, "unmatched_vertex": 0,
             "ambiguous": 0, "loops_written": 0, "uv_changed_before": 0,
             "material_index_mismatch": 0, "reused_reference": 0}
    used = {}
    for tri in mesh.loop_triangles:
        ids, missing = [], False
        for vertex in tri.vertices:
            point = matrix @ mesh.vertices[int(vertex)].co
            _, index, distance = tree.find(point)
            if index is None or distance > tolerance:
                missing = True
                break
            ids.append(index)
        if missing:
            stats["unmatched_vertex"] += 1
            continue
        key = tuple(sorted(ids))
        entries = table.get(key)
        if not entries:
            stats["unmatched_triangle"] += 1
            continue
        if len(entries) > 1:
            stats["ambiguous"] += 1
            continue
        entry = entries[0]
        used[key] = used.get(key, 0) + 1
        if used[key] > 1:
            stats["reused_reference"] += 1
        if int(tri.material_index) != entry["material_index"]:
            stats["material_index_mismatch"] += 1
        for cluster, loop in zip(ids, tri.loops):
            target = entry["uv"][cluster]
            current = tuple(uv_layer.data[loop].uv)
            if abs(current[0] - target[0]) > 1e-6 \
                    or abs(current[1] - target[1]) > 1e-6:
                stats["uv_changed_before"] += 1
            uv_layer.data[loop].uv = target
            stats["loops_written"] += 1
        stats["matched"] += 1
    stats["clean"] = (stats["unmatched_triangle"] == 0
                      and stats["unmatched_vertex"] == 0
                      and stats["ambiguous"] == 0
                      and stats["reused_reference"] == 0
                      and stats["matched"] == stats["triangles"])
    return stats


def verify_uv(obj, reference, tolerance=POSITION_TOLERANCE):
    """Re-measure: how many triangles still differ from the reference UV."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    tree = reference["tree"]
    table = reference["triangles"]
    uv_layer = mesh.uv_layers.active
    out = {"triangles": len(mesh.loop_triangles), "compared": 0,
           "uv_changed": 0, "position_mismatch": 0, "unmatched": 0,
           "duplicate_match": 0, "max_uv_delta": 0.0}
    seen = {}
    for tri in mesh.loop_triangles:
        ids, missing = [], False
        for vertex in tri.vertices:
            point = matrix @ mesh.vertices[int(vertex)].co
            _, index, distance = tree.find(point)
            if index is None or distance > tolerance:
                missing = True
                break
            ids.append(index)
        if missing:
            out["position_mismatch"] += 1
            continue
        key = tuple(sorted(ids))
        entries = table.get(key)
        if not entries:
            out["unmatched"] += 1
            continue
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1 or len(entries) > 1:
            out["duplicate_match"] += 1
            continue
        entry = entries[0]
        differs = False
        for cluster, loop in zip(ids, tri.loops):
            target = entry["uv"][cluster]
            current = tuple(uv_layer.data[loop].uv)
            delta = max(abs(current[0] - target[0]),
                        abs(current[1] - target[1]))
            out["max_uv_delta"] = max(out["max_uv_delta"], delta)
            if delta > 1e-6:
                differs = True
        out["compared"] += 1
        if differs:
            out["uv_changed"] += 1
    out["max_uv_delta"] = round(out["max_uv_delta"], 9)
    out["clean"] = (out["uv_changed"] == 0 and out["position_mismatch"] == 0
                    and out["unmatched"] == 0 and out["duplicate_match"] == 0
                    and out["compared"] == out["triangles"])
    return out
