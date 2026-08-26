"""Phase M2n8: rebuild the scale, and make every visible surface belong to one part.

Alignment 219.1.

Medium and Large stop carrying two scales. The secondary ring of 17 and 25
marks goes, and the thirteen primary ticks are not stretched or trimmed into
place - they are rebuilt from one rule, sized from the meter, and placed inside
the cover ring's opening so nothing has to intersect anything. The ring itself
comes towards the viewer by the distance the needle can spare, which is what
shortened the needle's protrusion from 5.6 / 7.7 mm to about 3.2 / 3.7 mm.

Round keeps its shape. What changes is that the counterweight and the blade
stop being two meshes sharing one front plane: a union welds them into a single
surface, materials intact, so there is no longer a pair of coincident faces for
a depth buffer to argue about. The two decorative rings keep their hidden
overlap and lose their share of that plane.

The canonical and M2n7 Blends are opened read-only and never written. The
revision is saved under its own name.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n8_revision.py -- \
      --project-root "$PWD" --mode build
"""

import argparse
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
import opus5_brushup_kinetic_pilot as pilot
import opus5_contact_migration_m1 as m1
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n7_depth_revision as m2n7
import opus5_meter_m2n8_diagnostic_sheets as sheets


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/meter_m2n8_revision.json"
REVISION = "M2n8"
RING = "kinetic_v6_inner_armor_ring"
NEEDLE = "needle"
# Alignment 219.1.4: the tick's outer end stops this far inside the ring.
RING_CLEARANCE_M = 5.0e-4
# One rule for every size, taken from Round: its ticks are 13.9% of the
# needle's reach long and about 3.1% of it across.
TICK_LENGTH_FRACTION = 0.139
TICK_WIDTH_FRACTION = 0.031
MAJOR_EVERY = 3
MAJOR_WIDTH = 1.6
ANGLES = [
    -115.1705, -94.6803, -74.8485, -55.598, -36.8053, -18.3241, 0.0,
    18.3241, 36.8053, 55.598, 74.8485, 94.6803, 115.1705,
]
RECESS_M = 2.0e-4
POSES = (-115.0, -57.5, 0.0, 57.5, 115.0)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--mode", required=True, choices=("build",))
    return parser.parse_args(args)


def revision_blend(project_root, key):
    name = m2n.SOURCES[key]["blend"].replace(
        "_Retopo.blend", f"_{REVISION}_Retopo.blend"
    )
    return m2l.theme_dir(project_root) / name


def radial_span(obj, centre):
    matrix = obj.matrix_world
    values = [
        math.hypot((matrix @ v.co).x - centre.x, (matrix @ v.co).z - centre.z)
        for v in obj.data.vertices
    ]
    return min(values), max(values)


def build_tick(name, centre, angle_deg, inner, outer, half_width, front, back,
               material, parent, collection):
    """One tick: a slab lying in the dial plane, built where it belongs."""
    angle = math.radians(angle_deg)
    radial = Vector((math.sin(angle), 0.0, math.cos(angle)))
    across = Vector((math.cos(angle), 0.0, -math.sin(angle)))
    corners = []
    for distance in (inner, outer):
        for side in (-half_width, half_width):
            corners.append(
                Vector((centre.x, 0.0, centre.z)) + radial * distance + across * side
            )
    verts = []
    for depth in (front, back):
        for corner in (corners[0], corners[1], corners[3], corners[2]):
            verts.append((corner.x, depth, corner.z))
    faces = [
        (0, 1, 2, 3), (7, 6, 5, 4),
        (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    return obj


def rebuild_scale(root, centre, key):
    """Thirteen ticks, one rule, inside the ring's opening."""
    ring = bpy.data.objects[RING]
    needle = bpy.data.objects[NEEDLE]
    reach = radial_span(needle, centre)[1]
    ring_inner = radial_span(ring, centre)[0]

    old = [obj for obj in bpy.data.objects if obj.name.startswith("kinetic_tick_")]
    material = old[0].data.materials[0]
    front, back = sheets.depth_span(old[0])
    secondary = [
        obj.name for obj in list(bpy.data.objects)
        if obj.name.startswith("secondary_scale_")
    ]
    parent = old[0].parent
    collection = old[0].users_collection[0]
    removed_ticks = len(old)
    for obj in old:
        bpy.data.objects.remove(obj, do_unlink=True)
    for name in secondary:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    half_width = reach * TICK_WIDTH_FRACTION / 2.0 * MAJOR_WIDTH
    # A slab's outer corners sit further out than its centre line, and the
    # corner is what would touch the ring.
    limit = ring_inner - RING_CLEARANCE_M
    outer = math.sqrt(max(limit * limit - half_width * half_width, 0.0))
    length = reach * TICK_LENGTH_FRACTION
    inner = outer - length
    half_width = reach * TICK_WIDTH_FRACTION / 2.0
    made = []
    for index, angle in enumerate(ANGLES):
        major = index % MAJOR_EVERY == 0
        made.append(
            build_tick(
                f"kinetic_tick_{index}", centre, angle, inner, outer,
                half_width * (MAJOR_WIDTH if major else 1.0),
                front, back, material, parent, collection,
            )
        )
    bpy.context.view_layer.update()
    return {
        "removed_ticks": removed_ticks,
        "removed_secondary": len(secondary),
        "built": len(made),
        "needle_reach_mm": round(reach * 1000.0, 4),
        "ring_inner_radius_mm": round(ring_inner * 1000.0, 4),
        "tick_outer_mm": round(outer * 1000.0, 4),
        "tick_inner_mm": round(inner * 1000.0, 4),
        "tick_length_mm": round(length * 1000.0, 4),
        "tick_half_width_mm": round(half_width * 1000.0, 4),
        "major_every": MAJOR_EVERY,
        "depth_y_m": [round(front, 6), round(back, 6)],
        "angles_deg": ANGLES,
    }, made


def bring_ring_forward(root, pivot, needle, ring):
    gap = sheets.sweep_min(root, pivot, needle, [ring], POSES)
    if gap is None or gap <= RING_CLEARANCE_M:
        return {"moved_mm": 0.0, "needle_ring_min_mm": round((gap or 0.0) * 1000.0, 4)}
    forward = gap - RING_CLEARANCE_M
    sheets.move_y(ring, -forward)
    bpy.context.view_layer.update()
    return {
        "moved_mm": round(forward * 1000.0, 4),
        "needle_ring_min_mm": round(
            (sheets.sweep_min(root, pivot, needle, [ring], POSES) or 0.0) * 1000.0, 4
        ),
    }


def split_preserving_materials():
    """Separate the needle's shells, keeping every slot and face assignment.

    The diagnostic splitter paints each shell so it can be told apart in a
    render. That is exactly wrong for a revision that has to keep its material
    roles, so this one copies the slot list and each face's index instead.
    """
    needle = bpy.data.objects[NEEDLE]
    source = needle.data
    slots = [material for material in source.materials]
    work = bmesh.new()
    work.from_mesh(source)
    work.verts.ensure_lookup_table()
    seen = set()
    groups = []
    for vertex in work.verts:
        if vertex.index in seen:
            continue
        stack = [vertex]
        group = set()
        while stack:
            current = stack.pop()
            if current.index in seen:
                continue
            seen.add(current.index)
            group.add(current.index)
            for edge in current.link_edges:
                stack.append(edge.other_vert(current))
        groups.append(group)
    groups.sort(key=len, reverse=True)
    made = []
    for index, group in enumerate(groups):
        piece = bmesh.new()
        mapping = {}
        for vertex_index in sorted(group):
            mapping[vertex_index] = piece.verts.new(work.verts[vertex_index].co)
        piece.verts.ensure_lookup_table()
        for face in work.faces:
            if not all(vertex.index in group for vertex in face.verts):
                continue
            new_face = piece.faces.new([mapping[v.index] for v in face.verts])
            new_face.material_index = face.material_index
        data = bpy.data.meshes.new(f"C{index}")
        piece.to_mesh(data)
        piece.free()
        for material in slots:
            data.materials.append(material)
        obj = bpy.data.objects.new(f"C{index}", data)
        needle.users_collection[0].objects.link(obj)
        obj.parent = needle.parent
        obj.matrix_world = needle.matrix_world.copy()
        made.append(obj)
    work.free()
    bpy.data.objects.remove(needle, do_unlink=True)
    bpy.context.view_layer.update()
    return made


def weld_needle(root):
    """Round: one surface where two used to share a plane.

    C2 (counterweight) and C3 (blade) both presented a front face at
    Y = -0.08050 over the same radii. A union removes the pair: what is left is
    one skin, with each face keeping the material it had. C0 and C1 are
    decoration and may keep their hidden overlap, so they only step back out of
    that plane.
    """
    pieces = split_preserving_materials()
    by_name = {obj.name: obj for obj in pieces}
    blade = by_name["C3"]
    counterweight = by_name["C2"]
    modifier = blade.modifiers.new("M2n8Union", "BOOLEAN")
    modifier.operation = "UNION"
    modifier.object = counterweight
    modifier.solver = "EXACT"
    modifier.material_mode = "TRANSFER"
    bpy.context.view_layer.objects.active = blade
    bpy.ops.object.modifier_apply(modifier="M2n8Union")
    bpy.data.objects.remove(counterweight, do_unlink=True)
    # The union leaves n-gons, and Blender's own display triangulation of a
    # concave n-gon is not the one the exporter's FIXED / EAR_CLIP pass
    # chooses - the disagreement alignment 175.2 was about. Triangulating here
    # means the file already holds the surface that will ship.
    work = bmesh.new()
    work.from_mesh(blade.data)
    bmesh.ops.triangulate(
        work, faces=work.faces[:], quad_method="FIXED", ngon_method="EAR_CLIP"
    )
    work.to_mesh(blade.data)
    work.free()
    blade.data.update()
    for name in ("C0", "C1"):
        sheets.move_y(by_name[name], RECESS_M)
    bpy.context.view_layer.update()

    # Back to one object called `needle`, which every gate downstream expects.
    remaining = [obj for obj in (blade, by_name["C0"], by_name["C1"])]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in remaining:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = blade
    bpy.ops.object.join()
    blade.name = NEEDLE
    blade["opus5_id"] = NEEDLE
    bpy.context.view_layer.update()
    return blade


def radial_span_overlap_candidates(obj, centre):
    """How often two front-facing triangles at one depth share a radius band.

    Alignment 221.1: this is NOT a count of coplanar overlaps and must not be
    read as one. Any flat face tessellated into triangles produces neighbours
    whose radial spans touch, so a healthy surface scores well above zero -
    Medium and Large score 7 with nothing wrong. It is kept only as a coarse
    signal; the question that actually matters is whether two *different*
    connected components present a front face at the same depth over the same
    radii, and that is answered by `component_front_depths` below.
    """
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    normal_matrix = matrix.to_3x3().inverted_safe().transposed()
    groups = {}
    for triangle in mesh.loop_triangles:
        normal = (normal_matrix @ triangle.normal).normalized()
        if normal.y > -0.9:
            continue
        points = [matrix @ mesh.vertices[v].co for v in triangle.vertices]
        depth = round(min(point.y for point in points), 6)
        radii = [
            math.hypot(point.x - centre.x, point.z - centre.z) for point in points
        ]
        groups.setdefault(depth, []).append((min(radii), max(radii)))
    overlaps = 0
    for depth, spans in groups.items():
        spans.sort()
        for index in range(len(spans) - 1):
            if spans[index][1] > spans[index + 1][0] + 1.0e-6:
                overlaps += 1
    return {
        "front_depths": sorted(groups),
        "radial_span_overlap_candidates": overlaps,
        "note": (
            "not a coplanar-overlap count; adjacent triangles of one flat "
            "face are included. See component_front_depths."
        ),
    }


def component_front_depths(obj, centre):
    """The gate that matters: do two shells share a front plane and a radius?

    This is the check that found the Round flicker and the one that shows it
    gone. Two connected components counted as sharing only if their front
    faces sit within 5e-5 m of each other *and* their radial spans overlap.
    """
    mesh = obj.data
    matrix = obj.matrix_world
    work = bmesh.new()
    work.from_mesh(mesh)
    work.verts.ensure_lookup_table()
    seen = set()
    groups = []
    for vertex in work.verts:
        if vertex.index in seen:
            continue
        stack = [vertex]
        group = set()
        while stack:
            current = stack.pop()
            if current.index in seen:
                continue
            seen.add(current.index)
            group.add(current.index)
            for edge in current.link_edges:
                stack.append(edge.other_vert(current))
        groups.append(group)
    groups.sort(key=len, reverse=True)
    rows = []
    for index, group in enumerate(groups):
        points = [matrix @ work.verts[i].co for i in group]
        radii = [
            math.hypot(point.x - centre.x, point.z - centre.z) for point in points
        ]
        rows.append(
            {
                "component": f"K{index}",
                "vertices": len(group),
                "front_y_m": round(min(point.y for point in points), 6),
                "radius_mm": [round(min(radii) * 1000.0, 3), round(max(radii) * 1000.0, 3)],
            }
        )
    work.free()
    shared = []
    for first in range(len(rows)):
        for second in range(first + 1, len(rows)):
            a, b = rows[first], rows[second]
            if abs(a["front_y_m"] - b["front_y_m"]) > 5.0e-5:
                continue
            if a["radius_mm"][1] < b["radius_mm"][0] or b["radius_mm"][1] < a["radius_mm"][0]:
                continue
            shared.append([a["component"], b["component"]])
    return {
        "components": rows,
        "components_sharing_front_plane_and_radius": shared,
        "pass": not shared,
    }


def report_model(root, pivot, centre, key):
    needle = bpy.data.objects[NEEDLE]
    ring = bpy.data.objects.get(RING)
    ticks = [obj for obj in bpy.data.objects if obj.name.startswith("kinetic_tick_")]
    dial = bpy.data.objects.get("kinetic_polygon_bezel") or bpy.data.objects.get(
        "kinetic_v6_dial_pan"
    )
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render
        for corner in obj.bound_box
    ]
    triangles = sum(
        len(obj.data.loop_triangles)
        for obj in pilot.meshes_under(root)
        if not obj.hide_render and (obj.data.calc_loop_triangles() or True)
    )
    row = {
        "objects": sum(1 for obj in pilot.meshes_under(root)),
        "triangles": triangles,
        "ticks": len(ticks),
        "secondary_scale": sum(
            1 for obj in bpy.data.objects if obj.name.startswith("secondary_scale_")
        ),
        "needle_reach_mm": round(radial_span(needle, centre)[1] * 1000.0, 4),
        "needle_front_m": round(sheets.depth_span(needle)[0], 6),
        "pivot_world": [round(value, 6) for value in centre],
        "materials": sorted(
            {
                material.name.split(".")[0]
                for obj in pilot.meshes_under(root)
                for material in obj.data.materials
                if material
            }
        ),
        "bounds": {
            "min": [round(min(p[i] for p in points), 6) for i in range(3)],
            "max": [round(max(p[i] for p in points), 6) for i in range(3)],
        },
        "needle_radial_span_signal": radial_span_overlap_candidates(needle, centre),
        "component_front_depths": component_front_depths(needle, centre),
    }
    if ticks:
        row["needle_tick_min_mm"] = round(
            (sheets.sweep_min(root, pivot, needle, ticks, POSES) or 0.0) * 1000.0, 4
        )
    if ring is not None and ticks:
        values = [sheets.min_distance(obj, ring) for obj in ticks]
        values = [value for value in values if value is not None]
        row["tick_ring_min_mm"] = round(min(values) * 1000.0, 4) if values else None
        row["tick_ring_radial_clearance_mm"] = round(
            (radial_span(ring, centre)[0] - max(radial_span(obj, centre)[1] for obj in ticks))
            * 1000.0, 4
        )
        row["needle_front_minus_ring_front_mm"] = round(
            (sheets.depth_span(ring)[0] - sheets.depth_span(needle)[0]) * 1000.0, 4
        )
    if dial is not None and ticks:
        values = [sheets.min_distance(obj, dial) for obj in ticks]
        values = [value for value in values if value is not None]
        row["tick_dial_min_mm"] = round(min(values) * 1000.0, 4) if values else None
    return row


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    payload = {
        "phase": "M2n8",
        "note": (
            "Scale rebuilt on one rule for Medium and Large; Round's blade and "
            "counterweight welded so no two faces share a front plane "
            "(alignment 219.1). M2n7 and canonical Blends are read-only."
        ),
        "design_rule": {
            "tick_length_fraction_of_reach": TICK_LENGTH_FRACTION,
            "tick_width_fraction_of_reach": TICK_WIDTH_FRACTION,
            "major_every": MAJOR_EVERY,
            "major_width_multiplier": MAJOR_WIDTH,
            "ring_clearance_m": RING_CLEARANCE_M,
            "angles_deg": ANGLES,
        },
        "models": {},
    }
    started = time.perf_counter()
    try:
        before = {}
        for key in m2n.SOURCES:
            canonical = m2n.source_blend(project_root, key)
            previous = m2n7.revision_blend(project_root, key)
            before[key] = {
                "canonical_sha256": m1.digest(canonical),
                "m2n7_sha256": m1.digest(previous),
            }
            bpy.ops.wm.open_mainfile(filepath=str(previous), load_ui=False)
            root = bpy.data.objects[m2k.MODELS[key]["root"]]
            pivot = bpy.data.objects[m2n.MOTION["pivot"]]
            centre = pivot.matrix_world.translation.copy()
            row = {"source": before[key]}
            if key == "MeterRound":
                weld_needle(root)
                row["round_weld"] = {
                    "welded": ["C2", "C3"],
                    "recessed_mm": round(RECESS_M * 1000.0, 4),
                    "recessed": ["C0", "C1"],
                }
            else:
                row["scale_rebuild"], _ = rebuild_scale(root, centre, key)
                row["ring_forward"] = bring_ring_forward(
                    root, pivot, bpy.data.objects[NEEDLE], bpy.data.objects[RING]
                )
            row.update(report_model(root, pivot, centre, key))
            target = revision_blend(project_root, key)
            bpy.ops.wm.save_as_mainfile(filepath=str(target), copy=True)
            row["revision_blend"] = str(target.relative_to(project_root))
            row["revision_blend_sha256"] = m1.digest(target)
            payload["models"][key] = row
            print(
                f"[Opus5M2n8] {key}: ticks {row['ticks']}, secondary "
                f"{row['secondary_scale']}, tris {row['triangles']}, "
                f"shared front planes "
                f"{row['component_front_depths']['components_sharing_front_plane_and_radius']}"
            )
        payload["sources_unchanged"] = all(
            m1.digest(m2n.source_blend(project_root, key)) == before[key]["canonical_sha256"]
            and m1.digest(m2n7.revision_blend(project_root, key)) == before[key]["m2n7_sha256"]
            for key in before
        )
        payload["status"] = "revision_built"
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        (project_root / OUTPUT).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(
            f"[Opus5M2n8] status {payload.get('status')}, sources unchanged "
            f"{payload.get('sources_unchanged')}"
        )


if __name__ == "__main__":
    main()
