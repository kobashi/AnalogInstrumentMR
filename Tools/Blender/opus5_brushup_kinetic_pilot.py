"""Opus 5 brush-up pilot for the Kinetic Safety V6 Retopo sources.

The script is non-destructive. It opens one production ``*_Retopo.blend`` as a
read-only baseline, rebuilds the detail islands that the brush-up brief targets,
re-validates the runtime contract, and writes a candidate blend plus a measured
JSON report into the Opus 5 candidate workspace.

It never writes to ``ArtSource/Blender/ThemeHardSurfaceV6`` and never touches
any Unity asset.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_brushup_kinetic_pilot.py -- \
      --project-root "$PWD" --object Lever

Every geometric change below is authored against the frozen contract:

* root name, root custom properties and motion hierarchy are preserved
* ``needle_pivot`` / ``handle_pivot`` / ``throttle_pivot`` transforms are byte
  identical to the baseline
* no material is created; the four semantic roles resolve through the existing
  ``MAT_KineticSafety_V5_{Body,Metal,Readout}`` names, and gasket-role parts are
  named with the tokens ``v6_theme_materials.assign_special_roles`` looks for
* the visual envelope may shrink but never grows past the baseline bounds
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_hardsurface_kinetic_set_v4 as v4
import generate_hardsurface_lever_prototype as hs
import generate_hardsurface_lever_retopo_v3 as retopo
import generate_orbital_analog_controls as controls
import generate_orbital_analog_meter as common


THEME = "KineticSafety"
REVISION = "R1"
MOUNT_PLANE_TOLERANCE = 0.001

# Runtime motion contract, expressed in Blender space.
#
# ``MockInstrumentMotion.ApplyState`` computes
# ``Lerp(-amplitude, amplitude, value) + rotationOffsetDegrees`` about the
# pivot's local axis.  ``OrbitalAnalogVisualFactory`` configures the V6 theme
# visuals with:
#
#   Meter    axis Vector3.forward, amplitude 55, offset   0  ->  [-55, +55]
#   Lever    axis Vector3.right,   amplitude 24, offset -24  ->  [-48,   0]
#   Throttle axis Vector3.right,   amplitude 35, offset -35  ->  [-70,   0]
#
# The lever and throttle sweeps are therefore one-sided.  The sweep has to run
# *out of* the mount plane (Blender -Y): the opposite sign drives the baseline
# lever handle 91 mm behind the mount plane, which neither the mount-plane check
# nor Quest acceptance would have survived.  ``motion_samples`` uses the outward
# sign; ``motion_samples_mirrored`` records the opposite sign so the reviewer can
# confirm the direction on the Unity side without another Blender pass.
PILOT = {
    "MeterRound": {
        "root": "PF_Visual_MeterRound_KineticSafety_V6",
        "pivot": "needle_pivot",
        "movable": "needle",
        "axis": (0.0, 1.0, 0.0),
        "triangle_budget": 5000,
        "sweep": (-55.0, 55.0),
        "sweep_steps": 22,
        "labelled_poses": {"minimum": -55.0, "neutral": 0.0, "maximum": 55.0},
        "interface_radius": 0.016,
    },
    "Lever": {
        "root": "PF_Visual_Lever_KineticSafety_V6",
        "pivot": "handle_pivot",
        "movable": "handle",
        "axis": (1.0, 0.0, 0.0),
        "triangle_budget": 5000,
        "sweep": (0.0, 48.0),
        "sweep_steps": 24,
        "labelled_poses": {"minimum": 0.0, "neutral": 24.0, "maximum": 48.0},
        # The axle is 80 mm long and lives inside the trunnion bore, so overlaps
        # closer than this to the pivot are the bearing fit, not a defect.
        "interface_radius": 0.045,
    },
    "Throttle": {
        "root": "PF_Visual_Throttle_KineticSafety_V6",
        "pivot": "throttle_pivot",
        "movable": "throttle_handle",
        "axis": (1.0, 0.0, 0.0),
        "triangle_budget": 5000,
        "sweep": (0.0, 70.0),
        "sweep_steps": 28,
        "labelled_poses": {"minimum": 0.0, "neutral": 35.0, "maximum": 70.0},
        # The axle is 105 mm long and is carried by bearings at x = +-44 mm.
        "interface_radius": 0.058,
    },
}

ROOT_PROPERTY_CONTRACT = (
    "instrument_type_id",
    "theme_id",
    "unity_mount_axis",
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--object",
        dest="object_key",
        choices=tuple(PILOT),
        action="append",
        help="Pilot object; repeat to run several. Defaults to all three.",
    )
    parser.add_argument("--revision", default=REVISION)
    return parser.parse_args(args)


# ---------------------------------------------------------------------------
# Mesh construction helpers
# ---------------------------------------------------------------------------


def _finalise(name, vertices, faces, material):
    # A face that repeats a vertex index is not a face. from_pydata accepts it
    # and bmesh's normal recalculation then spins forever on the result, so the
    # builders' shared-corner cases are filtered here rather than in each caller.
    faces = [face for face in faces if len(set(face)) == len(face)]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def weld_degenerate(obj, distance=1.0e-6):
    """Merge vertices the bevel collapsed onto each other.

    Beveling the slotted console leaves one corner where three vertices land on
    the same point, which triangulates into a zero-area face. A 1 micron weld
    removes it without touching anything the modelling actually placed. This is
    mesh hygiene, not a Decimate pass.
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance)
    bmesh.ops.dissolve_degenerate(bm, dist=distance, edges=bm.edges)
    collapsed = [
        face
        for face in bm.faces
        if len({vertex.index for vertex in face.verts}) != len(face.verts)
        or face.calc_area() <= 1e-12
    ]
    if collapsed:
        bmesh.ops.delete(bm, geom=collapsed, context="FACES_ONLY")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return obj


def revolve_y(name, profile, material, segments=20):
    """Revolve a closed ``(radius, y)`` profile around the Blender Y axis.

    The result is a quad-only manifold tube, which is what the ring, bezel and
    retainer parts need in order to keep a clean bevel highlight without a
    Boolean or a Decimate pass.
    """
    count = len(profile)
    vertices = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        for radius, y in profile:
            vertices.append((radius * sin_a, y, radius * cos_a))
    faces = []
    for index in range(segments):
        next_index = (index + 1) % segments
        for point in range(count):
            next_point = (point + 1) % count
            faces.append(
                (
                    index * count + point,
                    next_index * count + point,
                    next_index * count + next_point,
                    index * count + next_point,
                )
            )
    return _finalise(name, vertices, faces, material)


def revolve_x(name, profile, material, centre, segments=16, flip=False):
    """Revolve a closed ``(radius, x)`` profile around a Blender X axis."""
    centre_x, centre_y, centre_z = centre
    direction = -1.0 if flip else 1.0
    count = len(profile)
    vertices = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        for radius, offset in profile:
            vertices.append(
                (
                    centre_x + offset * direction,
                    centre_y + radius * cos_a,
                    centre_z + radius * sin_a,
                )
            )
    faces = []
    for index in range(segments):
        next_index = (index + 1) % segments
        for point in range(count):
            next_point = (point + 1) % count
            faces.append(
                (
                    index * count + point,
                    next_index * count + point,
                    next_index * count + next_point,
                    index * count + next_point,
                )
            )
    return _finalise(name, vertices, faces, material)


def arc_plate_x(
    name,
    centre_yz,
    inner_radius,
    outer_radius,
    start_degrees,
    end_degrees,
    x_min,
    x_max,
    material,
    steps=10,
):
    """Build an arc-shaped plate lying in a Blender YZ plane.

    ``phi = 0`` points along +Z and a positive ``phi`` sweeps toward -Y, which
    matches the outward handle travel of the lever and throttle pivots.
    """
    centre_y, centre_z = centre_yz
    vertices = []
    for index in range(steps + 1):
        t = index / steps
        phi = math.radians(start_degrees + (end_degrees - start_degrees) * t)
        sin_p, cos_p = math.sin(phi), math.cos(phi)
        outer = (centre_y - outer_radius * sin_p, centre_z + outer_radius * cos_p)
        inner = (centre_y - inner_radius * sin_p, centre_z + inner_radius * cos_p)
        vertices.extend(
            (
                (x_min, outer[0], outer[1]),
                (x_max, outer[0], outer[1]),
                (x_max, inner[0], inner[1]),
                (x_min, inner[0], inner[1]),
            )
        )
    faces = []
    for index in range(steps):
        base = index * 4
        nxt = base + 4
        for corner in range(4):
            following = (corner + 1) % 4
            faces.append(
                (
                    base + corner,
                    base + following,
                    nxt + following,
                    nxt + corner,
                )
            )
    last = steps * 4
    faces.append((3, 2, 1, 0))
    faces.append((last + 0, last + 1, last + 2, last + 3))
    return _finalise(name, vertices, faces, material)


def tapered_blade(name, outline, y_back, y_front, material):
    """A fan-capped prism from an explicit ``(x, z)`` outline."""
    return retopo.clean_prism(name, outline, y_back, y_front, material)


def small_prism(name, width, height, y_back, y_front, material, z=0.0, chamfer=None):
    """A chamfered prism without the bevel pass.

    ``v4.prism`` always applies a bevel modifier, which doubles the triangle
    count. Marks and teeth a few millimetres across gain nothing from it, and
    the pilot budget is tight, so they are built with the chamfer alone.
    """
    outline = (
        hs.chamfered_outline(width, height, chamfer, z)
        if chamfer
        else [
            (-width * 0.5, z - height * 0.5),
            (width * 0.5, z - height * 0.5),
            (width * 0.5, z + height * 0.5),
            (-width * 0.5, z + height * 0.5),
        ]
    )
    return retopo.clean_prism(name, outline, y_back, y_front, material)


def _loft_strip(outer_indices, outer_points, inner_indices, inner_points):
    """Triangle strip between two open polylines with different vertex counts.

    Both polylines keep every one of their own vertices, so the console outline
    and the pocket outline stay bit-identical to the baseline; only the faces
    between them are re-tessellated.
    """

    def parameters(points):
        lengths = [0.0]
        for index in range(1, len(points)):
            lengths.append(lengths[-1] + (points[index] - points[index - 1]).length)
        total = lengths[-1] or 1.0
        return [value / total for value in lengths]

    outer_t = parameters(outer_points)
    inner_t = parameters(inner_points)
    faces = []
    i = j = 0
    while i < len(outer_indices) - 1 or j < len(inner_indices) - 1:
        take_outer = j >= len(inner_indices) - 1 or (
            i < len(outer_indices) - 1 and outer_t[i + 1] <= inner_t[j + 1]
        )
        if take_outer:
            faces.append(
                (outer_indices[i], outer_indices[i + 1], inner_indices[j])
            )
            i += 1
        else:
            faces.append(
                (outer_indices[i], inner_indices[j + 1], inner_indices[j])
            )
            j += 1
    return faces


def slotted_console_shell(
    name,
    outer,
    pocket,
    slot_edge,
    y_back,
    y_front,
    y_recess,
    material,
    recess_centre_z=0.0,
):
    """A recessed console shell whose pocket opens through one outer edge.

    ``retopo.recessed_shell`` needs the pocket loop to stay strictly inside the
    outer loop, so it cannot express a lever slot. Here the pocket loop is
    allowed to touch the outer loop along ``slot_edge`` (an index pair into
    ``outer``); those two vertices are shared, the front band is lofted around
    the remaining perimeter, and the outer wall along the slot only descends to
    the recess floor.
    """
    slot_right, slot_left = slot_edge
    shared = {}
    vertices = []

    def add(point):
        vertices.append(point)
        return len(vertices) - 1

    back = [add(Vector((x, y_back, z))) for x, z in outer]
    pocket_front = []
    for index, (x, z) in enumerate(pocket):
        pocket_front.append(add(Vector((x, y_front, z))))
    pocket_recess = [add(Vector((x, y_recess, z))) for x, z in pocket]

    # The two slot corners on the outer edge are shared with the pocket loop.
    slot_pocket = [
        index
        for index, (x, z) in enumerate(pocket)
        if any(
            abs(x - outer[corner][0]) < 1e-9 and abs(z - outer[corner][1]) < 1e-9
            for corner in slot_edge
        )
    ]
    if len(slot_pocket) != 2:
        raise RuntimeError(f"{name}: slot corners were not found on the pocket loop")
    corner_pocket = {}
    for corner in slot_edge:
        match = next(
            index
            for index in slot_pocket
            if abs(pocket[index][0] - outer[corner][0]) < 1e-9
            and abs(pocket[index][1] - outer[corner][1]) < 1e-9
        )
        corner_pocket[corner] = match
        shared[corner] = pocket_front[match]
    right_pocket = corner_pocket[slot_right]
    left_pocket = corner_pocket[slot_left]

    front = []
    for index, (x, z) in enumerate(outer):
        if index in shared:
            front.append(shared[index])
        else:
            front.append(add(Vector((x, y_front, z))))

    back_centre = add(Vector((0.0, y_back, 0.0)))
    recess_centre = add(Vector((0.0, y_recess, recess_centre_z)))

    faces = []
    count = len(outer)
    for index in range(count):
        following = (index + 1) % count
        faces.append((back_centre, back[following], back[index]))
        if (index, following) == (slot_right, slot_left):
            # The slot: the outer wall only descends to the recess floor.
            faces.append(
                (
                    back[index],
                    back[following],
                    pocket_recess[left_pocket],
                    pocket_recess[right_pocket],
                )
            )
            continue
        if following == slot_right:
            # The recess-floor vertex sits on this wall's trailing edge, so the
            # face is split there rather than left as a T-junction.
            faces.append(
                (
                    back[index],
                    back[following],
                    pocket_recess[right_pocket],
                    front[index],
                )
            )
            faces.append(
                (front[index], pocket_recess[right_pocket], front[following])
            )
            continue
        if index == slot_left:
            faces.append(
                (
                    back[index],
                    back[following],
                    front[following],
                    pocket_recess[left_pocket],
                )
            )
            faces.append(
                (pocket_recess[left_pocket], front[following], front[index])
            )
            continue
        faces.append((back[index], back[following], front[following], front[index]))

    pocket_count = len(pocket)
    slot_top = tuple(sorted(slot_pocket))
    for index in range(pocket_count):
        following = (index + 1) % pocket_count
        faces.append(
            (recess_centre, pocket_recess[index], pocket_recess[following])
        )
        if (index, following) == slot_top or (following, index) == slot_top:
            continue  # open through the outer edge
        faces.append(
            (
                pocket_front[index],
                pocket_front[following],
                pocket_recess[following],
                pocket_recess[index],
            )
        )

    outer_path = list(range(slot_left, count)) + list(range(0, slot_right + 1))
    pocket_path = []
    cursor = left_pocket
    while True:
        pocket_path.append(cursor)
        if cursor == right_pocket:
            break
        cursor = (cursor + 1) % pocket_count
    # The pocket path starts and ends on the shared slot corners, which are the
    # same vertices as the outer path's ends. Feeding them to the loft would
    # emit triangles with a repeated index; dropping them makes the strip a fan
    # at each corner and still covers every boundary edge, because the shared
    # vertex closes both chains.
    inner_path = pocket_path[1:-1]
    faces.extend(
        _loft_strip(
            [front[index] for index in outer_path],
            [vertices[front[index]] for index in outer_path],
            [pocket_front[index] for index in inner_path],
            [vertices[pocket_front[index]] for index in inner_path],
        )
    )
    return _finalise(name, [tuple(point) for point in vertices], faces, material)


def parent_keep_world(obj, parent):
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world
    return obj


def materials_by_role():
    roles = {}
    for suffix, role in (
        ("_V5_Body", "body"),
        ("_V5_Metal", "metal"),
        ("_V5_Readout", "readout"),
    ):
        prefix = f"MAT_{THEME}{suffix}"
        match = next(
            (
                material
                for material in bpy.data.materials
                if material.name == prefix
                or material.name.startswith(prefix + ".")
            ),
            None,
        )
        if match is None:
            raise RuntimeError(f"Baseline material is missing: {prefix}")
        roles[role] = match
    # Gasket has no Retopo-stage material of its own. `v6_theme_materials`
    # re-assigns it from the object name at the Material stage, so gasket parts
    # carry the body material here and a gasket token in their name.
    roles["gasket"] = roles["body"]
    return roles


def remove_objects(names):
    removed = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        removed.append(name)
        bpy.data.objects.remove(obj, do_unlink=True)
    return removed


def remove_prefixed(prefix):
    targets = [obj.name for obj in bpy.data.objects if obj.name.startswith(prefix)]
    return remove_objects(targets)


def rebuild_movable(objects, name, pivot_object):
    """Join ``objects`` and hang them off an existing, untouched pivot empty."""
    for obj in objects:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    joined = common.join_objects(objects, name)
    bpy.context.scene.cursor.location = pivot_object.matrix_world.translation
    bpy.context.view_layer.objects.active = joined
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
    joined.parent = pivot_object
    joined.location = (0.0, 0.0, 0.0)
    joined.rotation_euler = (0.0, 0.0, 0.0)
    joined.scale = (1.0, 1.0, 1.0)
    joined.name = name
    joined.data.name = f"ME_{name}"
    return joined


# ---------------------------------------------------------------------------
# MeterRound
# ---------------------------------------------------------------------------


def brush_up_meter_round(root, mats):
    """Give the dial a real sunken depth and a readable needle.

    Baseline: the 12-gon bezel's flat front face *was* the dial, the ticks sat on
    that same plane and the needle floated 0-4 mm above it, so nothing read as
    depth. The rebuild sinks a dial pan behind a stepped bezel ring and lifts the
    needle onto a two-step hub.
    """
    changes = []
    removed = remove_objects(
        [
            "kinetic_polygon_bezel",
            "kinetic_v6_glass_gasket",
            "kinetic_v6_inner_armor_ring",
            "needle",
        ]
    )
    removed += remove_prefixed("kinetic_tick_")
    changes.append(f"removed flat-dial islands: {', '.join(sorted(removed))}")

    pan = v4.cylinder_y(
        "kinetic_v6_dial_pan",
        0.0468,
        0.0280,
        0.0585,
        mats["body"],
        24,
    )
    pan.parent = root
    changes.append(
        "added kinetic_v6_dial_pan: dial face recessed to y=-0.0725, "
        "8.0 mm behind the bezel lip"
    )

    bezel_profile = [
        (0.0472, -0.0450),
        (0.0472, -0.0742),
        (0.0494, -0.0805),
        (0.0530, -0.0805),
        (0.0552, -0.0772),
        (0.0552, -0.0450),
    ]
    bezel = revolve_y(
        "kinetic_v6_bezel_ring",
        bezel_profile,
        mats["metal"],
        24,
    )
    bezel.parent = root
    changes.append(
        "added kinetic_v6_bezel_ring: chamfered stepped ring, front face "
        "y=-0.0805 (baseline frontmost was -0.081)"
    )

    retainer_profile = [
        (0.0448, -0.0725),
        (0.0448, -0.0768),
        (0.0470, -0.0768),
        (0.0470, -0.0725),
    ]
    retainer = revolve_y(
        "kinetic_v6_inner_retainer",
        retainer_profile,
        mats["metal"],
        24,
    )
    retainer.parent = root
    changes.append(
        "added kinetic_v6_inner_retainer: separates dial layer from bezel layer"
    )

    gasket_profile = [
        (0.0452, -0.0708),
        (0.0452, -0.0742),
        (0.0472, -0.0742),
        (0.0472, -0.0708),
    ]
    gasket = revolve_y(
        "kinetic_v6_glass_gasket",
        gasket_profile,
        mats["gasket"],
        24,
    )
    gasket.parent = root
    changes.append(
        "rebuilt kinetic_v6_glass_gasket as a seated square-section seal "
        "(gasket role via name token)"
    )

    for index in range(13):
        angle = math.radians(-120 + index * 20)
        major = index % 3 == 0
        tick = v4.accent_bar(
            f"kinetic_tick_{index}",
            0.0030 if major else 0.0019,
            0.0115 if major else 0.0068,
            math.sin(angle) * 0.0405,
            math.cos(angle) * 0.0405,
            0.0715,
            mats["readout"],
        )
        tick.rotation_euler.y = angle
        tick.parent = root
    changes.append(
        "re-seated 13 ticks onto the recessed dial face (y=-0.0715..-0.0745, "
        "2.5 mm under the needle) and widened the five majors"
    )

    arc = revolve_y(
        "kinetic_v6_dial_arc",
        [
            (0.0330, -0.0725),
            (0.0330, -0.0742),
            (0.0352, -0.0742),
            (0.0352, -0.0725),
        ],
        mats["readout"],
        24,
    )
    arc.parent = root
    changes.append("added kinetic_v6_dial_arc: inner emissive arc band")

    pivot = bpy.data.objects["needle_pivot"]
    pivot_y = pivot.location.y
    pivot_z = pivot.location.z
    blade_outline = [
        (-0.0036, 0.0),
        (-0.0018, 0.0330),
        (-0.0010, 0.0420),
        (0.0010, 0.0420),
        (0.0018, 0.0330),
        (0.0036, 0.0),
    ]
    blade = tapered_blade(
        "needle_blade",
        [(x, z + pivot_z) for x, z in blade_outline],
        pivot_y,
        pivot_y - 0.0035,
        mats["readout"],
    )
    retopo.bevel(blade, 0.0004, 1)
    # The tail has to clear the 11.8 mm hub to read as a counterweight rather
    # than a chip in the hub silhouette, so it runs out to 20 mm with a paddle.
    tail_outline = [
        (-0.0026, 0.0),
        (-0.0030, -0.0120),
        (-0.0052, -0.0152),
        (-0.0042, -0.0200),
        (0.0042, -0.0200),
        (0.0052, -0.0152),
        (0.0030, -0.0120),
        (0.0026, 0.0),
    ]
    tail = tapered_blade(
        "needle_counterweight",
        [(x, z + pivot_z) for x, z in tail_outline],
        pivot_y,
        pivot_y - 0.0035,
        mats["metal"],
    )
    retopo.bevel(tail, 0.0005, 1)
    hub = v4.cylinder_y(
        "needle_hub",
        0.0118,
        0.0060,
        0.0765,
        mats["metal"],
        16,
    )
    hub.location.z = pivot_z
    cap = v4.cylinder_y(
        "needle_hub_cap",
        0.0054,
        0.0030,
        0.0790,
        mats["metal"],
        12,
    )
    cap.location.z = pivot_z
    rebuild_movable([blade, tail, hub, cap], "needle", pivot)
    changes.append(
        "rebuilt needle: tapered blade (3.6 mm root taper), metal "
        "counterweight tail and a two-step hub (r=11.8 mm / 5.4 mm)"
    )
    return changes


# ---------------------------------------------------------------------------
# Lever
# ---------------------------------------------------------------------------


def brush_up_lever(root, mats):
    """Explain the bearing and the detent direction without moving the pivot.

    The baseline had bearing covers but no cap or bushing, and the only index
    marks ran vertically up the housing face - across the sweep rather than
    along it. The sweep happens in the YZ plane, so the new index is an arc
    quadrant centred on ``handle_pivot``.
    """
    changes = []
    pivot = bpy.data.objects["handle_pivot"]
    pivot_y = pivot.location.y
    pivot_z = pivot.location.z
    changes.extend(rebuild_lever_slot(root, mats))

    # A bolted collar rather than a solid disc: the inner radius clears the
    # 12 mm axle so the cap never intersects the moving island.
    cap_profile = [
        (0.0140, -0.0030),
        (0.0248, -0.0030),
        (0.0248, 0.0022),
        (0.0196, 0.0062),
        (0.0140, 0.0062),
    ]
    for side, x, flip in ((0, -0.0325, True), (1, 0.0325, False)):
        cap = revolve_x(
            f"kinetic_v6_bearing_cap_{side}",
            cap_profile,
            mats["metal"],
            (x, pivot_y, pivot_z),
            16,
            flip,
        )
        cap.parent = root
        outward = x + (0.0067 if not flip else -0.0067)
        for index in range(3):
            angle = math.radians(index * 120)
            bolt = v4.cylinder_x(
                f"kinetic_v6_bearing_cap_bolt_{side}_{index}",
                0.0026,
                0.0034,
                (
                    outward,
                    pivot_y + math.cos(angle) * 0.0212,
                    pivot_z + math.sin(angle) * 0.0212,
                ),
                mats["metal"],
                8,
            )
            bolt.parent = root
    changes.append(
        "added kinetic_v6_bearing_cap_0/1 (bolted collar, 14 mm bore) with "
        "three seated bolts each: the trunnion now reads as a serviceable "
        "bearing instead of an extruded boss"
    )

    # The baseline already carries kinetic_v6_bearing_washer_* on the trunnions,
    # and "washer" is one of the gasket tokens, so the gasket role at the pivot
    # is kept rather than duplicated.

    quadrant = arc_plate_x(
        "kinetic_v6_detent_quadrant",
        (pivot_y, pivot_z),
        0.0480,
        0.0600,
        -6.0,
        54.0,
        0.0275,
        0.0325,
        mats["metal"],
        12,
    )
    quadrant.parent = root
    changes.append(
        "added kinetic_v6_detent_quadrant: arc plate in the plane of travel, "
        "-6 deg to +54 deg, clear of the housing recess floor at y=-0.041"
    )

    for index in range(5):
        phi = math.radians(index * 12.0)
        # 61.2 mm keeps the outermost tooth corner at y = -0.1005 at the far end
        # of the arc, just inside the baseline envelope of -0.101.
        radius = 0.0612
        centre_y = pivot_y - radius * math.sin(phi)
        centre_z = pivot_z + radius * math.cos(phi)
        major = index in (0, 2, 4)
        height = 0.0080 if major else 0.0055
        # A trapezoid rather than a chamfered block: at close range a row of
        # equal boxes reads as greebling, a tapered rack reads as a detent.
        tooth = tapered_blade(
            f"kinetic_v6_detent_tooth_{index}",
            [
                (-0.0030, -height * 0.5),
                (0.0030, -height * 0.5),
                (0.0030, height * 0.16),
                (0.0018, height * 0.5),
                (-0.0018, height * 0.5),
                (-0.0030, height * 0.16),
            ],
            -0.0030,
            0.0030,
            mats["metal"],
        )
        tooth.rotation_euler.x = phi
        tooth.location = (0.0300, centre_y, centre_z)
        tooth.parent = root

        index_mark = small_prism(
            f"kinetic_v6_detent_index_{index}",
            0.0016,
            0.0062 if major else 0.0040,
            -0.0018,
            0.0018,
            mats["readout"],
        )
        index_mark.rotation_euler.x = phi
        index_mark.location = (0.0338, centre_y, centre_z)
        index_mark.parent = root
    changes.append(
        "added five detent teeth plus emissive index marks at 0/12/24/36/48 "
        "deg, matching the five normalized lever detents"
    )

    for side, x in ((0, -0.0620), (1, 0.0620)):
        rib = v4.prism(
            f"kinetic_v6_slot_guide_{side}",
            0.0090,
            0.0620,
            0.0022,
            -0.0660,
            -0.0716,
            mats["metal"],
            0.0180,
        )
        rib.location.x = x
        rib.parent = root
    changes.append(
        "added kinetic_v6_slot_guide_0/1: guide ribs standing 5.6 mm proud of "
        "the shoulders so the travel slot reads in grayscale"
    )

    # Guide lips sitting exactly on the new slot edges. They start above
    # z = -8 mm so the 12 mm axle, which sweeps up to z = -13 mm, stays clear.
    for side, x in ((0, -0.0165), (1, 0.0165)):
        rail = v4.prism(
            f"kinetic_v6_handle_channel_{side}",
            0.0080,
            0.0780,
            0.0018,
            -0.0420,
            -0.0565,
            mats["metal"],
            0.0310,
        )
        rail.location.x = x
        rail.parent = root
    changes.append(
        "added kinetic_v6_handle_channel_0/1: guide lips flush with the slot "
        "edges (x = +-12.5 mm), running from the insert plate over the console "
        "top band"
    )
    return changes


SLOT_HALF_WIDTH = 0.0125


def rebuild_lever_slot(root, mats):
    """Give the lever shaft a real slot in the console and in the insert plate.

    The baseline shaft (r = 8.5 mm) passes straight through ``recess_insert``
    over its whole length and through the console front band at z = 0.060..0.070
    with nothing cut away. The shaft cannot be shortened - that would change the
    interaction envelope - so both plates are rebuilt with an opening.

    Every outline vertex of the baseline console is reproduced exactly, so the
    silhouette is unchanged apart from the 25 x 10 mm notch in the top band.
    """
    changes = []
    remove_objects(["housing", "recess_insert"])

    outer = hs.chamfered_outline(0.18, 0.14, 0.012)
    # Two extra vertices on the top edge define the slot mouth. The bottom edge
    # gains two as well so the lofted front band stays evenly proportioned.
    outer = [
        outer[0],
        (-0.026, -0.070),
        (0.026, -0.070),
        outer[1],
        outer[2],
        outer[3],
        outer[4],
        (SLOT_HALF_WIDTH, 0.070),
        (-SLOT_HALF_WIDTH, 0.070),
        outer[5],
        outer[6],
        outer[7],
    ]
    inner = hs.chamfered_outline(0.086, 0.112, 0.009, 0.004)
    pocket = [
        inner[0],
        inner[1],
        inner[2],
        inner[3],
        inner[4],
        (SLOT_HALF_WIDTH, 0.060),
        (SLOT_HALF_WIDTH, 0.070),
        (-SLOT_HALF_WIDTH, 0.070),
        (-SLOT_HALF_WIDTH, 0.060),
        inner[5],
        inner[6],
        inner[7],
    ]
    shell = slotted_console_shell(
        "housing",
        outer,
        pocket,
        (7, 8),
        0.0,
        -0.050,
        -0.041,
        mats["body"],
        recess_centre_z=0.004,
    )
    retopo.bevel(shell, 0.0028, 1)
    weld_degenerate(shell)

    parts = [shell]
    for x in (-0.062, 0.062):
        outline = [
            (px + x, pz) for px, pz in hs.chamfered_outline(0.040, 0.100, 0.007)
        ]
        shoulder = retopo.clean_prism("shoulder", outline, -0.044, -0.066, mats["body"])
        retopo.bevel(shoulder, 0.0022, 1)
        parts.append(shoulder)
    for x in (-0.025, 0.025):
        trunnion = v4.cylinder_x(
            "trunnion",
            0.020,
            0.024,
            (x, -0.050, -0.025),
            mats["metal"],
            20,
        )
        parts.append(trunnion)
    housing = common.join_objects(parts, "housing")
    weld_degenerate(housing)
    housing.parent = root
    changes.append(
        "rebuilt housing with a 25 x 10 mm shaft slot through the top band "
        "(pocket now opens at the outer edge, floor stays at y=-0.041). All "
        "baseline outline vertices, shoulders and trunnions are reproduced"
    )

    plate_parts = []
    for side, sign in ((0, -1.0), (1, 1.0)):
        outline = [
            (sign * SLOT_HALF_WIDTH, -0.047),
            (sign * 0.030, -0.047),
            (sign * 0.037, -0.040),
            (sign * 0.037, 0.048),
            (sign * 0.030, 0.055),
            (sign * SLOT_HALF_WIDTH, 0.055),
        ]
        if sign < 0:
            outline.reverse()
        cheek = retopo.clean_prism(
            f"recess_insert_cheek_{side}",
            outline,
            -0.042,
            -0.047,
            mats["metal"],
        )
        retopo.bevel(cheek, 0.0015, 1)
        plate_parts.append(cheek)
    bridge = retopo.clean_prism(
        "recess_insert_bridge",
        [
            (-0.0145, -0.047),
            (0.0145, -0.047),
            (0.0145, -0.0395),
            (-0.0145, -0.0395),
        ],
        -0.042,
        -0.047,
        mats["metal"],
    )
    plate_parts.append(bridge)
    for index, (x, z) in enumerate(
        ((-0.073, -0.043), (0.073, -0.043), (-0.073, 0.043), (0.073, 0.043))
    ):
        plate_parts.append(
            hs.cylinder(
                f"fastener_{index}",
                0.0030,
                0.0022,
                (x, -0.053, z),
                mats["metal"],
                10,
            )
        )
    insert = common.join_objects(plate_parts, "recess_insert")
    weld_degenerate(insert)
    insert.parent = root
    changes.append(
        "rebuilt recess_insert as a slotted plate: two cheeks at "
        "x = +-12.5..37 mm plus a bridge below the axle sweep, so the shaft no "
        "longer passes through solid material"
    )
    return changes


def _torus_x(name, major_radius, minor_radius, location, material, major=12, minor=4):
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        major_segments=major,
        minor_segments=minor,
        location=location,
        rotation=(0.0, math.radians(90.0), 0.0),
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    torus = bpy.context.object
    torus.name = name
    torus.data.materials.append(material)
    return torus


# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------


def brush_up_throttle(root, mats):
    """Contour the palm grip and explain the quadrant, without moving the box.

    The palm grip keeps its baseline envelope (0.126 x 0.058, y -0.085..-0.120,
    z centred on 0.112) because the controller grip pose is matched to it.
    """
    changes = []
    pivot = bpy.data.objects["throttle_pivot"]
    pivot_y = pivot.location.y
    pivot_z = pivot.location.z

    removed = remove_objects(["throttle_handle"])
    changes.append(f"rebuilt movable island: {', '.join(removed)}")

    axle = v4.cylinder_x(
        "throttle_axle",
        0.0160,
        0.1050,
        (0.0, pivot_y, pivot_z),
        mats["metal"],
        18,
    )
    parts = [axle]

    arm_outline = [
        (-0.0130, -0.1105),
        (-0.0130, -0.0700),
        (-0.0092, -0.0300),
        (-0.0078, 0.0600),
        (-0.0086, 0.0945),
        (0.0086, 0.0945),
        (0.0078, 0.0600),
        (0.0092, -0.0300),
        (0.0130, -0.0700),
        (0.0130, -0.1105),
    ]
    for side, x in ((0, -0.0340), (1, 0.0340)):
        arm = tapered_blade(
            f"throttle_fork_arm_{side}",
            arm_outline,
            pivot_y,
            pivot_y - 0.0160,
            mats["metal"],
        )
        retopo.bevel(arm, 0.0016, 1)
        arm.location.x = x
        parts.append(arm)

        web = small_prism(
            f"throttle_arm_web_{side}",
            0.0044,
            0.1600,
            pivot_y - 0.0160,
            pivot_y - 0.0198,
            mats["metal"],
            -0.0140,
            chamfer=0.0011,
        )
        web.location.x = x
        parts.append(web)
    changes.append(
        "replaced the two constant-width arms with tapered fork arms plus a "
        "raised centre web, so the load path from the axle reads at 1-3 m"
    )

    cross = small_prism(
        "throttle_fork_brace",
        0.0800,
        0.0140,
        pivot_y - 0.0020,
        pivot_y - 0.0150,
        mats["metal"],
        -0.0300,
        chamfer=0.0032,
    )
    parts.append(cross)
    changes.append("added throttle_fork_brace tying the two fork arms together")

    grip_outline = [
        (-0.0480, 0.0830),
        (-0.0620, 0.0930),
        (-0.0630, 0.1180),
        (-0.0540, 0.1400),
        (-0.0330, 0.1410),
        (0.0330, 0.1410),
        (0.0540, 0.1400),
        (0.0630, 0.1180),
        (0.0620, 0.0930),
        (0.0480, 0.0830),
    ]
    grip = tapered_blade(
        "throttle_palm_grip",
        grip_outline,
        pivot_y - 0.0050,
        pivot_y - 0.0330,
        mats["body"],
    )
    retopo.bevel(grip, 0.0042, 1)
    parts.append(grip)

    palm = tapered_blade(
        "throttle_palm_crown",
        [
            (-0.0500, 0.0910),
            (-0.0560, 0.1000),
            (-0.0560, 0.1300),
            (-0.0470, 0.1370),
            (0.0470, 0.1370),
            (0.0560, 0.1300),
            (0.0560, 0.1000),
            (0.0500, 0.0910),
        ],
        pivot_y - 0.0330,
        pivot_y - 0.0385,
        mats["body"],
    )
    # The crown is only 5.5 mm deep, so the bevel has to stay well under half
    # that or it collapses the side band into zero-area faces.
    retopo.bevel(palm, 0.0014, 1)
    parts.append(palm)
    changes.append(
        "contoured the palm grip into a waisted body plus a crowned palm "
        "face, keeping the baseline grip box (y -0.085..-0.120, z 0.083..0.141)"
    )

    for index, z in enumerate((0.0985, 0.1090, 0.1195, 0.1300)):
        insert = small_prism(
            f"throttle_grip_gasket_insert_{index}",
            0.0880,
            0.0056,
            pivot_y - 0.0360,
            pivot_y - 0.0400,
            mats["gasket"],
            z,
            chamfer=0.0014,
        )
        parts.append(insert)
    changes.append(
        "added four anti-slip grip inserts (gasket role via name token) "
        "standing 1.5 mm proud of the palm crown, front face still at the "
        "baseline y=-0.120"
    )

    index_bar = small_prism(
        "throttle_grip_readout_index",
        0.0180,
        0.0060,
        pivot_y - 0.0330,
        pivot_y - 0.0372,
        mats["readout"],
        0.0870,
        chamfer=0.0014,
    )
    index_bar.location.x = 0.0480
    parts.append(index_bar)
    changes.append(
        "added throttle_grip_readout_index pointing at the quadrant scale"
    )
    rebuild_movable(parts, "throttle_handle", pivot)

    # The baseline end stops reach y=-0.084, which puts the 32 mm axle inside
    # the lower block at every angle of travel. They are rebuilt 21.5 mm
    # shallower so the shaft clears them by 1.5 mm.
    remove_objects(
        [
            "KineticSafety_throttle_v6_limit_stop_0",
            "KineticSafety_throttle_v6_limit_stop_1",
        ]
    )
    for index, z in enumerate((-0.1180, 0.1180)):
        stop = v4.prism(
            f"KineticSafety_throttle_v6_limit_stop_{index}",
            0.0480,
            0.0220,
            0.0050,
            -0.0460,
            -0.0625,
            mats["body"],
            z,
        )
        stop.location.x = -0.05775
        stop.parent = root
    changes.append(
        "rebuilt KineticSafety_throttle_v6_limit_stop_0/1 to y=-0.046..-0.0625: "
        "the baseline blocks reached y=-0.084 and the throttle axle passed "
        "through the lower one at every angle"
    )

    for side, x in ((0, -0.0650), (1, 0.0650)):
        pedestal = v4.prism(
            f"kinetic_v6_throttle_pedestal_{side}",
            0.0300,
            0.0700,
            0.0060,
            -0.0440,
            -0.0980,
            mats["metal"],
            pivot_z,
        )
        pedestal.location.x = x
        pedestal.parent = root
    changes.append(
        "added kinetic_v6_throttle_pedestal_0/1: the axle now lands on a "
        "visible support instead of floating off the plate"
    )

    for side, x in ((0, -0.0300), (1, 0.0300)):
        bushing = _torus_x(
            f"kinetic_v6_throttle_bushing_{side}",
            0.0205,
            0.0036,
            (x, pivot_y, pivot_z),
            mats["gasket"],
            10,
            3,
        )
        bushing.parent = root
    changes.append(
        "added kinetic_v6_throttle_bushing_0/1 (gasket role) around the axle"
    )

    for side, x_min, x_max in ((0, -0.0600, -0.0500), (1, 0.0500, 0.0600)):
        slot = arc_plate_x(
            f"kinetic_v6_throttle_quadrant_{side}",
            (pivot_y, pivot_z),
            0.0420,
            0.0580,
            -8.0,
            38.0,
            x_min,
            x_max,
            mats["metal"],
            10,
        )
        slot.parent = root
    changes.append(
        "added kinetic_v6_throttle_quadrant_0/1: arc slot cheeks in the plane "
        "of travel that show the sweep direction from either side"
    )

    for index, z in enumerate((-0.1180, 0.1180)):
        block = small_prism(
            f"kinetic_v6_throttle_end_block_{index}",
            0.0280,
            0.0125,
            -0.0770,
            -0.0845,
            mats["readout"],
            z,
            chamfer=0.0028,
        )
        block.location.x = 0.1050
        block.parent = root
    changes.append(
        "added CUTOFF/FULL end blocks on the quadrant scale so the travel "
        "limits read before the labels are textured"
    )

    strip = v4.prism(
        "kinetic_v6_throttle_scale_strip_left",
        0.0260,
        0.2500,
        0.0050,
        -0.0440,
        -0.0810,
        mats["metal"],
    )
    strip.location.x = -0.1050
    strip.parent = root
    for index, z in enumerate((-0.1180, -0.0660, 0.0, 0.0660, 0.1180)):
        mark = small_prism(
            f"kinetic_v6_throttle_mark_left_{index}",
            0.0240 if index in (0, 4) else 0.0180,
            0.0090 if index in (0, 4) else 0.0050,
            -0.0770,
            -0.0836,
            mats["readout"],
            z,
            chamfer=0.0012,
        )
        mark.location.x = -0.1050
        mark.parent = root
    changes.append(
        "mirrored the quadrant scale onto the left cheek: the baseline scale "
        "existed on the +X side only, which read as a one-sided mount"
    )
    return changes


BRUSH_UPS = {
    "MeterRound": brush_up_meter_round,
    "Lever": brush_up_lever,
    "Throttle": brush_up_throttle,
}


# ---------------------------------------------------------------------------
# Measurement and contract validation
# ---------------------------------------------------------------------------


def meshes_under(root):
    return [obj for obj in root.children_recursive if obj.type == "MESH"]


def world_bounds(meshes):
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    return {
        "min": [round(min(point[i] for point in corners), 6) for i in range(3)],
        "max": [round(max(point[i] for point in corners), 6) for i in range(3)],
    }


def pivot_state(pivot):
    return {
        "name": pivot.name,
        "parent": pivot.parent.name if pivot.parent else None,
        "location": [round(value, 9) for value in pivot.location],
        "rotation_euler": [round(value, 9) for value in pivot.rotation_euler],
        "scale": [round(value, 9) for value in pivot.scale],
        "matrix_world": [
            [round(value, 9) for value in row] for row in pivot.matrix_world
        ],
    }


def triangulated_stats(meshes):
    """Topology of a deterministic triangulation, measured on throwaway copies."""
    copies = []
    for source in meshes:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.parent = None
        duplicate.matrix_world = source.matrix_world.copy()
        bpy.context.collection.objects.link(duplicate)
        copies.append(duplicate)
    retopo.triangulate(copies)
    stats = retopo.topology_stats(copies)
    per_object = {
        source.name: len(duplicate.data.polygons)
        for source, duplicate in zip(meshes, copies)
    }
    degenerate = {
        source.name: sum(
            1 for polygon in duplicate.data.polygons if polygon.area <= 1e-12
        )
        for source, duplicate in zip(meshes, copies)
    }
    stats["zero_area_faces_by_object"] = {
        name: count for name, count in degenerate.items() if count
    }
    for duplicate in copies:
        bpy.data.objects.remove(duplicate, do_unlink=True)
    return stats, per_object


def material_role_of(material):
    if material is None:
        return "body"
    name = material.name.lower()
    if "readout" in name or "emissive" in name:
        return "readout"
    if "gasket" in name:
        return "gasket"
    if "metal" in name:
        return "metal"
    return "body"


GASKET_TOKENS = ("gasket", "washer", "bushing", "pivot_boot")


def material_role_summary(meshes):
    roles = {}
    for obj in meshes:
        gasket = any(token in obj.name.lower() for token in GASKET_TOKENS)
        for material in obj.data.materials:
            role = "gasket" if gasket else material_role_of(material)
            roles.setdefault(role, []).append(obj.name)
    return {role: sorted(set(names)) for role, names in sorted(roles.items())}


def _point_in_triangle(point, triangle, normal, epsilon=1e-12):
    first, second, third = triangle
    if (second - first).cross(point - first).dot(normal) < -epsilon:
        return False
    if (third - second).cross(point - second).dot(normal) < -epsilon:
        return False
    if (first - third).cross(point - third).dot(normal) < -epsilon:
        return False
    return True


def _edge_crossings(triangle, distance, other, other_normal):
    points = []
    for index in range(3):
        following = (index + 1) % 3
        near, far = distance[index], distance[following]
        if near == 0.0:
            if _point_in_triangle(triangle[index], other, other_normal):
                points.append(triangle[index])
            continue
        if near * far >= 0.0:
            continue
        ratio = near / (near - far)
        crossing = triangle[index] + (triangle[following] - triangle[index]) * ratio
        if _point_in_triangle(crossing, other, other_normal):
            points.append(crossing)
    return points


def triangle_contact_points(first, second, epsilon=1e-9):
    """Exact triangle-triangle intersection, returning the contact points.

    ``BVHTree.overlap`` is only a broad phase: it pairs triangles that are tens
    of millimetres apart, which inflates any penetration count built on it and
    makes the movable triangle's centroid a poor locator (the joined handle mesh
    has fan triangles spanning a whole outline). Returning the real crossing
    points instead gives both a trustworthy count and the place where the two
    surfaces actually meet.

    Coplanar pairs return no points on purpose: two surfaces sliding on each
    other is contact, not penetration.
    """
    normal_b = (second[1] - second[0]).cross(second[2] - second[0])
    offset_b = -normal_b.dot(second[0])
    distance_a = [normal_b.dot(point) + offset_b for point in first]
    if all(value > epsilon for value in distance_a):
        return []
    if all(value < -epsilon for value in distance_a):
        return []

    normal_a = (first[1] - first[0]).cross(first[2] - first[0])
    offset_a = -normal_a.dot(first[0])
    distance_b = [normal_a.dot(point) + offset_a for point in second]
    if all(value > epsilon for value in distance_b):
        return []
    if all(value < -epsilon for value in distance_b):
        return []

    if normal_a.cross(normal_b).length < epsilon:
        return []

    return _edge_crossings(first, distance_a, second, normal_b) + _edge_crossings(
        second, distance_b, first, normal_a
    )


# Candidate gathering only, and deliberately conservative: inflating the boxes
# costs a few extra pairs, which the exact test then rejects.
#
# The earlier comment here claimed this fixed a case where `overlap` missed 36
# "real intersections" on MeterLarge. That was wrong and is corrected in
# alignment 83.4 and 84.4: those extra hits were zero-depth touches at a shared
# plane, which the old un-normalised plane test reported as crossings. The
# inflation changed none of those numbers. It stays because a broad phase that
# under-approximates is a bug waiting to happen, not because it fixed that one.
#
# This tree is for candidates. Measuring depth needs an un-inflated tree - ten
# micrometres of slack silently swallows a five micrometre intrusion, which the
# fixtures in `opus5_contact_fixtures` demonstrate (alignment 84.4).
BVH_EPSILON = 1.0e-5


def bvh_for(obj, matrix=None):
    matrix = obj.matrix_world if matrix is None else matrix
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = [matrix @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]
    return BVHTree.FromPolygons(
        [tuple(vertex) for vertex in vertices],
        polygons,
        all_triangles=True,
        epsilon=BVH_EPSILON,
    ), vertices, polygons


def motion_report(root, spec):
    """Sweep the movable island and measure penetration against static parts.

    Static-to-static interpenetration is normal in this asset family (the axle
    is deliberately buried in its bearing), so overlaps inside an interface
    sphere around the pivot are reported separately from the ones outside it,
    which are the real failures.
    """
    pivot = bpy.data.objects[spec["pivot"]]
    movable = bpy.data.objects[spec["movable"]]
    statics = [obj for obj in meshes_under(root) if obj is not movable]
    static_trees = []
    for obj in statics:
        tree, vertices, polygons = bvh_for(obj)
        static_trees.append((obj.name, tree, vertices, polygons))

    axis = Vector(spec["axis"]).normalized()
    pivot_world = pivot.matrix_world.translation.copy()
    base_matrix = movable.matrix_world.copy()
    interface_radius = spec["interface_radius"]

    mesh = movable.data
    mesh.calc_loop_triangles()
    local_vertices = [vertex.co.copy() for vertex in mesh.vertices]
    triangles = [tuple(triangle.vertices) for triangle in mesh.loop_triangles]

    def sample(angle_degrees):
        rotation = (
            Matrix.Translation(pivot_world)
            @ Matrix.Rotation(math.radians(angle_degrees), 4, axis)
            @ Matrix.Translation(-pivot_world)
        )
        matrix = rotation @ base_matrix
        points = [matrix @ vertex for vertex in local_vertices]
        tree = BVHTree.FromPolygons(
            [tuple(point) for point in points],
            triangles,
            all_triangles=True,
        )
        behind_mount = max(point.y for point in points)
        hits = []
        for name, static_tree, static_points, static_triangles in static_trees:
            pairs = 0
            outside = 0
            farthest = 0.0
            contact = None
            for movable_index, static_index in tree.overlap(static_tree):
                contacts = triangle_contact_points(
                    [points[index] for index in triangles[movable_index]],
                    [
                        static_points[index]
                        for index in static_triangles[static_index]
                    ],
                )
                if not contacts:
                    continue
                pairs += 1
                distance = max(
                    (point - pivot_world).length for point in contacts
                )
                if distance > interface_radius:
                    outside += 1
                    if distance > farthest:
                        farthest = distance
                        contact = max(
                            contacts,
                            key=lambda point: (point - pivot_world).length,
                        )
            if not pairs:
                continue
            hits.append(
                {
                    "static": name,
                    "intersecting_pairs": pairs,
                    "outside_interface": outside,
                    "farthest_contact_from_pivot": round(farthest, 5),
                    "farthest_contact_point": (
                        [round(value, 5) for value in contact]
                        if contact is not None
                        else None
                    ),
                }
            )
        return {
            "angle_degrees": round(angle_degrees, 3),
            "max_y_behind_mount_plane": round(behind_mount, 6),
            "mount_plane_ok": behind_mount <= MOUNT_PLANE_TOLERANCE,
            "bounds": {
                "min": [round(min(p[i] for p in points), 6) for i in range(3)],
                "max": [round(max(p[i] for p in points), 6) for i in range(3)],
            },
            "static_overlaps": hits,
            "penetrations_outside_interface": sum(
                hit["outside_interface"] for hit in hits
            ),
        }

    start, end = spec["sweep"]
    steps = spec["sweep_steps"]
    sweep = [
        sample(start + (end - start) * index / steps) for index in range(steps + 1)
    ]
    labelled = {
        label: sample(angle) for label, angle in spec["labelled_poses"].items()
    }
    mirrored = [sample(-entry["angle_degrees"]) for entry in sweep]
    return {
        "axis_blender": list(spec["axis"]),
        "sweep_degrees": [start, end],
        "interface_radius": interface_radius,
        "labelled_poses": labelled,
        "worst_mount_plane_y": round(
            max(entry["max_y_behind_mount_plane"] for entry in sweep), 6
        ),
        "penetrations_outside_interface": sum(
            entry["penetrations_outside_interface"] for entry in sweep
        ),
        "mount_plane_violations": [
            entry["angle_degrees"] for entry in sweep if not entry["mount_plane_ok"]
        ],
        "samples": sweep,
        "mirrored_sign_check": {
            "note": (
                "Same sweep with the opposite rotation sign. Recorded so the "
                "Unity-side rotation direction can be confirmed without a "
                "second Blender pass."
            ),
            "worst_mount_plane_y": round(
                max(entry["max_y_behind_mount_plane"] for entry in mirrored), 6
            ),
            "penetrations_outside_interface": sum(
                entry["penetrations_outside_interface"] for entry in mirrored
            ),
            "mount_plane_violations": [
                entry["angle_degrees"]
                for entry in mirrored
                if not entry["mount_plane_ok"]
            ],
        },
    }


def measure(root, spec):
    meshes = meshes_under(root)
    for mesh in meshes:
        mesh.data.calc_loop_triangles()
    source_stats = retopo.topology_stats(meshes)
    final_stats, per_object = triangulated_stats(meshes)
    return {
        "objects": len(list(root.children_recursive)) + 1,
        "meshes": len(meshes),
        "mesh_names": sorted(obj.name for obj in meshes),
        "vertices": source_stats["vertices"],
        "retopo_topology": source_stats,
        "triangulated_topology": final_stats,
        "triangles_by_object": dict(
            sorted(per_object.items(), key=lambda item: -item[1])
        ),
        "triangles": final_stats["faces"],
        "bounds": world_bounds(meshes),
        "pivot": pivot_state(bpy.data.objects[spec["pivot"]]),
        "material_roles": material_role_summary(meshes),
        "motion": motion_report(root, spec),
    }


def forbidden_datablocks():
    problems = []
    for obj in bpy.data.objects:
        if obj.type in {"CAMERA", "LIGHT", "SPEAKER"}:
            problems.append(f"forbidden object type in scene: {obj.name} ({obj.type})")
        if obj.type == "MESH" and obj.modifiers:
            problems.append(
                f"unapplied modifier on {obj.name}: "
                + ", ".join(modifier.type for modifier in obj.modifiers)
            )
        if obj.animation_data is not None:
            problems.append(f"animation data on {obj.name}")
    return problems


def validate(root, spec, before, after):
    problems = []
    if root.name != spec["root"]:
        problems.append(f"root renamed: {root.name} != {spec['root']}")
    for key in ROOT_PROPERTY_CONTRACT:
        if root.get(key) != before["root_properties"].get(key):
            problems.append(f"root property changed: {key}")
    for key, value in before["root_properties"].items():
        if key not in root:
            problems.append(f"root property removed: {key}")
        elif root[key] != value:
            problems.append(f"root property mutated: {key}")
    if list(root.scale) != [1.0, 1.0, 1.0]:
        problems.append(f"root scale is not unit: {list(root.scale)}")

    pivot = bpy.data.objects.get(spec["pivot"])
    if pivot is None:
        problems.append(f"missing pivot: {spec['pivot']}")
    elif after["pivot"] != before["pivot"]:
        problems.append(f"pivot transform changed: {spec['pivot']}")

    movable = bpy.data.objects.get(spec["movable"])
    if movable is None or movable.type != "MESH":
        problems.append(f"missing movable mesh: {spec['movable']}")
    elif movable.parent is None or movable.parent.name != spec["pivot"]:
        problems.append(
            f"{spec['movable']} is no longer parented to {spec['pivot']}"
        )

    for obj in meshes_under(root):
        if any(abs(value - 1.0) > 1e-6 for value in obj.scale):
            problems.append(f"unapplied scale on {obj.name}: {list(obj.scale)}")
        if any(value < 0.0 for value in obj.scale):
            problems.append(f"negative scale on {obj.name}")

    stats = after["triangulated_topology"]
    if stats["non_manifold_edges"]:
        problems.append(f"non-manifold edges: {stats['non_manifold_edges']}")
    if stats["zero_area_faces"]:
        problems.append(
            f"zero-area faces: {stats['zero_area_faces']} "
            f"{stats.get('zero_area_faces_by_object')}"
        )
    if after["triangles"] > spec["triangle_budget"]:
        problems.append(
            f"triangle budget exceeded: {after['triangles']} > "
            f"{spec['triangle_budget']}"
        )

    retopo_stats = after["retopo_topology"]
    quad_share = retopo_stats["quads"] / max(retopo_stats["faces"], 1)
    if quad_share < 0.55:
        problems.append(f"retopo mesh is no longer quad dominant: {quad_share:.2f}")

    for index, axis in enumerate("xyz"):
        if after["bounds"]["min"][index] < before["bounds"]["min"][index] - 1e-6:
            problems.append(
                f"envelope grew on -{axis}: "
                f"{after['bounds']['min'][index]} < {before['bounds']['min'][index]}"
            )
        if after["bounds"]["max"][index] > before["bounds"]["max"][index] + 1e-6:
            problems.append(
                f"envelope grew on +{axis}: "
                f"{after['bounds']['max'][index]} > {before['bounds']['max'][index]}"
            )
    if after["bounds"]["max"][1] > MOUNT_PLANE_TOLERANCE:
        problems.append(
            f"static geometry passes the mount plane: y={after['bounds']['max'][1]}"
        )

    missing_roles = {"body", "metal", "readout"} - set(after["material_roles"])
    if missing_roles:
        problems.append(f"material roles lost: {sorted(missing_roles)}")

    problems.extend(forbidden_datablocks())
    return problems


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def save_blend(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    path.with_suffix(".blend1").unlink(missing_ok=True)


def run_one(project_root, key, revision):
    spec = PILOT[key]
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / THEME
        / f"BL_{key}_{THEME}_V6_Retopo.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    candidate_dir = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / THEME
    )
    candidate = candidate_dir / f"BL_{key}_{THEME}_V6_Opus5_{revision}_Retopo.blend"
    report_path = (
        candidate_dir / "reports" / f"{key}_{THEME}_V6_Opus5_{revision}.json"
    )

    blender_compat.require_v6_pipeline()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    blender_compat.require_v6_pipeline()

    root = bpy.data.objects.get(spec["root"])
    if root is None:
        raise RuntimeError(f"{key}: expected root {spec['root']} was not found")
    for name in (spec["pivot"], spec["movable"]):
        if bpy.data.objects.get(name) is None:
            raise RuntimeError(f"{key}: missing motion node {name}")

    root_properties = {
        prop: root[prop] for prop in root.keys() if prop != "_RNA_UI"
    }
    before = measure(root, spec)
    before["root_properties"] = root_properties

    mats = materials_by_role()
    changes = BRUSH_UPS[key](root, mats)

    meshes = meshes_under(root)
    common.apply_transforms(meshes)
    after = measure(root, spec)

    problems = validate(root, spec, before, after)
    if problems:
        breakdown = "\n  ".join(
            f"{name}: {count}"
            for name, count in list(after["triangles_by_object"].items())[:20]
        )
        raise RuntimeError(
            f"{key}: candidate violates the runtime contract:\n  - "
            + "\n  - ".join(problems)
            + f"\n  triangles by object (top 20):\n  {breakdown}"
        )

    save_blend(candidate)

    report = {
        "source": str(source.relative_to(project_root)),
        "candidate": str(candidate.relative_to(project_root)),
        "generator": "Tools/Blender/opus5_brushup_kinetic_pilot.py",
        "blender_version": bpy.app.version_string,
        "object": key,
        "theme": THEME,
        "revision": revision,
        "root": root.name,
        "root_properties": root_properties,
        "changes": changes,
        "unchanged_contracts": [
            f"root name {spec['root']}",
            "root custom properties (instrument_type_id, theme_id, "
            "unity_mount_axis, art_pass, quality_floor, geometry/texture/"
            "assembly policy)",
            f"motion hierarchy {spec['pivot']}/{spec['movable']}",
            f"pivot transform {before['pivot']['location']} and local axis "
            f"{list(spec['axis'])}",
            "1 Blender unit = 1 m, Z-up, root scale (1, 1, 1)",
            "mount plane at Blender y = 0, outward -Y",
            "no new Blender material; the four atlas roles resolve through the "
            "existing MAT_KineticSafety_V5_* names and the gasket name tokens",
            "no collider, animator, camera, light or add-on modifier",
        ],
        "vertices": after["vertices"],
        "triangles": after["triangles"],
        "triangle_budget": spec["triangle_budget"],
        "non_manifold_edges": after["triangulated_topology"]["non_manifold_edges"],
        "zero_area_faces": after["triangulated_topology"]["zero_area_faces"],
        "renderer_islands": {
            "static": 1,
            "movable": 1,
            "note": (
                "export_v6_replacement_candidates.combine_runtime_renderers "
                "merges every mesh under the pivot into the movable renderer "
                "and everything else into the static renderer."
            ),
        },
        "bounds_before": before["bounds"],
        "bounds_after": after["bounds"],
        "pivot_before": before["pivot"],
        "pivot_after": after["pivot"],
        "topology_before": {
            "retopo": before["retopo_topology"],
            "triangulated": before["triangulated_topology"],
        },
        "topology_after": {
            "retopo": after["retopo_topology"],
            "triangulated": after["triangulated_topology"],
        },
        "triangles_by_object_before": before["triangles_by_object"],
        "triangles_by_object_after": after["triangles_by_object"],
        "material_roles": sorted(after["material_roles"]),
        "material_role_members": after["material_roles"],
        "motion_checks_before": before["motion"],
        "motion_checks_after": after["motion"],
        "known_risks": [],
        "status": "CANDIDATE",
        "authoring_environment": blender_compat.provenance(),
    }

    budget_headroom = spec["triangle_budget"] - after["triangles"]
    report["known_risks"].append(
        f"triangle headroom after the pass: {budget_headroom} of "
        f"{spec['triangle_budget']}"
    )
    if after["motion"]["penetrations_outside_interface"]:
        report["known_risks"].append(
            "movable island still overlaps static geometry outside the pivot "
            "interface sphere; see motion_checks_after.samples"
        )
    if before["motion"]["penetrations_outside_interface"]:
        report["known_risks"].append(
            "the baseline already overlapped static geometry outside the pivot "
            "interface sphere; see motion_checks_before for the comparison"
        )
    report["known_risks"].append(
        "rotation sign: the Unity range is [-2A, 0] about the pivot local X "
        "for Lever and Throttle. This report sweeps the outward direction; "
        "motion_checks_after.mirrored_sign_check records the opposite sign."
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"[Opus5BrushUp] {key}: {before['triangles']} -> {after['triangles']} "
        f"triangles (budget {spec['triangle_budget']}); candidate {candidate}"
    )
    return report


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    keys = args.object_key or list(PILOT)
    for key in keys:
        run_one(project_root, key, args.revision)


if __name__ == "__main__":
    main()
