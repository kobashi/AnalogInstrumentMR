"""Theme 4 fastener access R2: delete the fifteen screws inside the housings.

316 accepted R1's nameplate deletion and its sixteen relocations, and ruled on
the fifteen that could not be relocated: MeterMedium and MeterLarge carry six
each and Rotary three whose heads sit inside the housing's solid of
revolution. A ray cast out of any of them crosses the housing surface an odd
number of times, so they are inside the material - invisible from every
direction, no tool path possible, and no fixing structure expressed. Widening
a land or thinning the rotary's collar would disturb silhouettes and a grip
that are already accepted, so the screws go instead.

R2 carries R1's two accepted changes forward unchanged and adds only the
deletions. Nothing else in any of these instruments moves, which is a claim
this module makes checkable: every part that is not a deleted screw is
compared to its R1 self by triangle count, bounds and centroid, so the
triangle delta can be shown to be the screws and nothing but the screws.
"""

import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_fastener_access_r1 as fa

# 316.1 / 316.2
REMOVED = {
    "MeterMedium": tuple(f"screw_{index}" for index in range(6)),
    "MeterLarge": tuple(f"screw_{index}" for index in range(6)),
    "Rotary": ("screw_0", "screw_1", "screw_2"),
}
DROP_FASTENER = "__dropped_fastener"


def dropped_names(asset):
    return set(REMOVED.get(asset, ()))


def install(asset, drop_nameplate=False, overrides=None,
            drop_fasteners=True):
    """R1's patches plus the R2 deletions, as one reversible install.

    A dropped fastener is never built: the wrapper hands back an empty
    placeholder instead of calling p1.fastener at all, so there is no seat and
    no head to leave behind, and the join hook removes the placeholder and its
    mesh datablock on the way past.
    """
    original_fastener = p1.fastener
    original_nameplate = p1.nameplate
    original_join = p1.join
    drop = dropped_names(asset) if drop_fasteners else set()
    table = dict(overrides or {})

    def placeholder(mark):
        mesh = bpy.data.meshes.new(mark)
        obj = bpy.data.objects.new(mark, mesh)
        bpy.context.collection.objects.link(obj)
        return obj

    def fastener(name, centre, y_face, radius, depth):
        if name in drop:
            return placeholder(DROP_FASTENER)
        key = (asset, name)
        if key in table:
            centre, y_face = table[key]
        return original_fastener(name, centre, y_face, radius, depth)

    def nameplate(name, *args, **kwargs):
        if drop_nameplate and asset == "Rotary" and name == "plate_label":
            return placeholder(fa.DROP_NAMEPLATE)
        return original_nameplate(name, *args, **kwargs)

    def join(target, others):
        group = []
        for obj in [target] + list(others):
            if obj is None:
                continue
            if obj.name.split(".")[0] in (DROP_FASTENER, fa.DROP_NAMEPLATE):
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
                continue
            group.append(obj)
        return original_join(group[0], group[1:])

    p1.fastener, p1.nameplate, p1.join = fastener, nameplate, join
    return original_fastener, original_nameplate, original_join


def restore(saved):
    p1.fastener, p1.nameplate, p1.join = saved


def residue(asset):
    """316.5: nothing of the deleted screws may survive anywhere in the file."""
    drop = dropped_names(asset)
    hits = {"objects": [], "meshes": [], "orphan_meshes": [], "materials": [],
            "placeholders": []}
    for name in drop:
        hits["objects"] += [o.name for o in bpy.data.objects if name in o.name]
        hits["meshes"] += [m.name for m in bpy.data.meshes if name in m.name]
        hits["orphan_meshes"] += [m.name for m in bpy.data.meshes
                                  if name in m.name and m.users == 0]
        hits["materials"] += [m.name for m in bpy.data.materials
                              if name in m.name]
    hits["placeholders"] = sorted(
        o.name for o in bpy.data.objects
        if DROP_FASTENER in o.name or fa.DROP_NAMEPLATE in o.name)
    hits["placeholder_meshes"] = sorted(
        m.name for m in bpy.data.meshes
        if DROP_FASTENER in m.name or fa.DROP_NAMEPLATE in m.name)
    for key in hits:
        hits[key] = sorted(set(hits[key]))
    hits["clean"] = not any(hits[key] for key in hits if key != "clean")
    return hits


def part_signature(parts):
    """Triangle count, bounds and centroid per part - the freeze evidence."""
    out = {}
    for name, tris in parts.items():
        flat = tris.reshape(-1, 3)
        out[name] = {
            "triangles": int(len(tris)),
            "min_m": [round(float(v), 5) for v in flat.min(axis=0)],
            "max_m": [round(float(v), 5) for v in flat.max(axis=0)],
            "centroid_m": [round(float(v), 5) for v in flat.mean(axis=0)],
        }
    return out


def signature_diff(before, after, ignore):
    """Which parts changed, deliberately or otherwise."""
    changed, missing, added = {}, [], []
    for name, row in before.items():
        if fa.fastener_id(name) in ignore:
            continue
        if name not in after:
            missing.append(name)
            continue
        if after[name] != row:
            changed[name] = {"r1": row, "r2": after[name]}
    for name in after:
        if name not in before:
            added.append(name)
    return {"changed": changed, "missing": sorted(missing),
            "added": sorted(added),
            "clean": not changed and not missing and not added}
