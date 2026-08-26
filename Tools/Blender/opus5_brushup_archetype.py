"""Spec-driven shape brush-up for one archetype, for the 39-model rollout.

The Kinetic Safety pilot (`opus5_brushup_kinetic_pilot`) proved the approach on
three movable controls, but its spec assumes a pivot and a movable island, so it
cannot describe an indicator that does not move. This module carries the same
measurement and validation machinery over a spec where the motion block is
optional, which is what the remaining archetypes need (alignment 51.2).

For a static assembly the interesting failure is the opposite of a movable one.
A movable island fails by penetrating what it sweeps past; a static island fails
by *floating* - a part that touches nothing reads as a decal rather than as
hardware, and the V6 root itself promises "supported marks" and "supports
explain construction". So every part the brush-up adds has to contact something
that was already there, and that is checked rather than assumed.

Source is the shipped Retopo blend; output goes to the Opus 5 candidate tree
only. Production Retopo, ProductionReady, Unity FBX, prefab, material, texture
and `.meta` are never written.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_brushup_archetype.py -- \
      --project-root "$PWD" --model KineticSafety/Lamp
"""

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_hardsurface_kinetic_set_v4 as v4
import generate_hardsurface_lever_prototype as hs
import generate_hardsurface_lever_retopo_v3 as retopo
import opus5_brushup_kinetic_pilot as pilot
import opus5_joint_contact_section as section
import opus5_publish as publishing


REVISION = "B1"

# Plate envelope per archetype, from `generate_theme_hardsurface_v6_remaining`
# SMALL_ENVELOPES (the Kinetic Safety pair of each row).
SPECS = {
    "KineticSafety/Lamp": {
        "root": "PF_Visual_Lamp_KineticSafety_V6",
        "triangle_budget": 5000,
        "envelope_xz": (0.142, 0.116),
        "builder": "brush_up_kinetic_lamp",
        "intent": (
            "The lens sits in a shallow tray behind one 14 mm bar. Give it a "
            "retained lens assembly - rolled bezel following the lens, a single "
            "guard bar narrowed to 8 mm, and a glare hood - so the lamp reads "
            "as protected safety hardware instead of a slab in a recess, while "
            "leaving more of the emissive lens visible than the shipped model."
        ),
    },
    "KineticSafety/StatusIndicator": {
        "root": "PF_Visual_StatusIndicator_KineticSafety_V6",
        "triangle_budget": 5000,
        "envelope_xz": (0.184, 0.124),
        "builder": "brush_up_kinetic_status",
        "intent": (
            "Three lens bars share a tray with two dividers, so the outer two "
            "lenses run off the ends unframed. Close the cell block with end "
            "ribs that tie both braces together, hood the panel, and give it a "
            "legend strip so the three states read as an instrument."
        ),
    },
}

for _key, _budget in (
    ("MeterRound", 5000),
    ("MeterMedium", 25000),
    ("MeterLarge", 25000),
):
    SPECS[f"KineticSafety/{_key}"] = {
        "root": f"PF_Visual_{_key}_KineticSafety_V6",
        "triangle_budget": _budget,
        # Meters are round; the plate envelope rows do not cover them, so the
        # envelope is taken from the baseline itself and simply must not grow.
        "envelope_xz": None,
        "builder": "brush_up_kinetic_meter",
        "motion": {
            "pivot": "needle_pivot",
            "axis": (0.0, 1.0, 0.0),
            "sweep": (-55.0, 55.0),
            "steps": 22,
            "poses": {"minimum": -55.0, "neutral": 0.0, "maximum": 55.0},
            # The bearing fit is the hub, so the radius that separates "shaft
            # in its boss" from "needle hitting the dial" scales with the hub
            # rather than being tabulated per model.
            "bearing_radius_hub_multiple": 1.7,
            "allowed_bearing_pairs": {
                "needle x kinetic_v6_needle_boss": (
                    "the needle turning in the bearing boss this brush-up adds"
                ),
                "kinetic_v6_needle_counterweight x kinetic_v6_needle_boss": (
                    "the counterweight seated against the same boss"
                ),
            },
        },
        "intent": (
            "The dial is a bare plate: the needle runs from a plain hub with "
            "nothing balancing it and nothing marking where the reading "
            "matters. Add the bearing boss the needle should turn in, a "
            "counterweight behind the pivot, and a zone band over the top of "
            "the sweep, all sized from the model's own needle so one builder "
            "covers Round, Medium and Large."
        ),
    }

SPECS["KineticSafety/WindowMeter"] = {
    "root": "PF_Visual_WindowMeter_KineticSafety_V6",
    "triangle_budget": 25000,
    "envelope_xz": None,
    # The same builder as Round / Medium / Large: everything it needs is read
    # off this model's own needle and tick ring, so a fourth scale - a 1.2 m
    # panel meter - needs no new constants (alignment 51.2).
    "builder": "brush_up_kinetic_meter",
    # Only the bearing boss transfers. The dial reaches into the needle's depth
    # band, leaving nowhere for a counterweight to sweep; and the needle
    # overhangs the dial, so a zone band pushed clear of the swept circle would
    # have no dial to sit on. Both are measured, not assumed - see 72.2.
    "meter_parts": ("boss",),
    "motion": {
        "pivot": "needle_pivot",
        "axis": (0.0, 1.0, 0.0),
        "sweep": (-55.0, 55.0),
        "steps": 22,
        "poses": {"minimum": -55.0, "neutral": 0.0, "maximum": 55.0},
        "bearing_radius_hub_multiple": 1.7,
    },
    "intent": (
        "The largest dial in the set has a needle running from a plain hub. It "
        "takes the bearing boss the other meters got, sized from its own "
        "needle; the counterweight and zone band do not fit this dial."
    ),
}

SPECS["KineticSafety/WindowPanel"] = {
    "root": "PF_Visual_WindowPanel_KineticSafety_V6",
    "triangle_budget": 25000,
    "envelope_xz": None,
    "builder": "brush_up_kinetic_window_panel",
    "motion": {
        "pivot": "vane_pivot",
        "axis": (0.0, 1.0, 0.0),
        "sweep": (-42.0, 42.0),
        "steps": 28,
        "poses": {"minimum": -42.0, "neutral": 0.0, "maximum": 42.0},
        "bearing_radius": 0.030,
    },
    "intent": (
        "A 1.6 m panel whose recessed display runs off both ends unframed and "
        "whose face carries no labelling. Cap the display, hood it, and give it "
        "a legend strip - all outside the vane's swept disc, which is the one "
        "region of this panel that is not free."
    ),
}

SPECS["KineticSafety/Toggle"] = {
    "root": "PF_Visual_Toggle_KineticSafety_V6",
    "triangle_budget": 5000,
    "envelope_xz": (0.124, 0.146),
    "builder": "brush_up_kinetic_toggle",
    "motion": {
        "pivot": "switch_pivot",
        "axis": (1.0, 0.0, 0.0),
        # Unity applies a matching negative offset, so the shipped sweep is the
        # one-sided [-56, 0]; in Blender that is 0 .. 56 (handoff 6.3).
        "sweep": (0.0, 56.0),
        "steps": 28,
        "poses": {"minimum": 0.0, "neutral": 28.0, "maximum": 56.0},
        # The ball joint is the bearing here, not a hub.
        "bearing_radius": 0.026,
    },
    "intent": (
        "A bare stem on a flat plate: nothing closes the socket and nothing "
        "stops a sleeve catching the lever. Add a pair of guard posts flanking "
        "the swing plane and socket cheeks on the two sides the lever never "
        "crosses, which is what a safety toggle carries and what the two side "
        "detents already hint at."
    ),
}

SPECS["KineticSafety/Rotary"] = {
    "root": "PF_Visual_Rotary_KineticSafety_V6",
    "triangle_budget": 5000,
    "envelope_xz": (0.152, 0.152),
    "builder": "brush_up_kinetic_rotary",
    "motion": {
        "pivot": "knob_pivot",
        "axis": (0.0, 1.0, 0.0),
        # "連続回転で偏心しない" (handoff 6.3): the acceptance is a full turn,
        # not an end-stopped sweep, so the audit walks the whole revolution.
        "sweep": (0.0, 360.0),
        "steps": 36,
        "poses": {"minimum": 0.0, "neutral": 180.0, "maximum": 360.0},
        "bearing_radius": 0.042,
    },
    "intent": (
        "The knob is a smooth drum - nothing to grip and nothing sealing the "
        "gap it turns in. Add grip ribs around it and a dust seal at its base, "
        "so the control reads as something a gloved hand turns."
    ),
}

SPECS["KineticSafety/PowerSlider"] = {
    "root": "PF_Visual_PowerSlider_KineticSafety_V6",
    "triangle_budget": 5000,
    "envelope_xz": (0.168, 0.340),
    "builder": "brush_up_kinetic_slider",
    "motion": {
        "kind": "linear",
        "pivot": "slider_travel",
        # Handoff 6.3 gives 0.18 m of travel along Unity local Y, which is
        # Blender Z. The rest pose is the centre of it.
        "axis": (0.0, 0.0, 1.0),
        "sweep": (-0.09, 0.09),
        "steps": 36,
        "poses": {"minimum": -0.09, "neutral": 0.0, "maximum": 0.09},
        # The carriage rides two rails rather than turning in a bore, so there
        # is no bearing sphere; everything it touches is measured as contact.
        "bearing_radius": 0.0,
        # Alignment 66.4. The bridge rides the rails, so surface contact along
        # the whole travel is the interface, not a defect. It is allowed by
        # name and with a reason, and it stays in the report - the guard below
        # still fails if the contact ever gains volume, which is what would
        # separate riding a rail from sinking into it.
        "allowed_interface_pairs": {
            "KineticSafety_slider_v6_handle_bridge x kinetic_slider_rail": (
                "carriage bridge sliding on its rail; measured 0 of 17,472 "
                "sampled rail cells occupied (alignment 65.5)"
            ),
            "KineticSafety_slider_v6_handle_bridge x kinetic_slider_rail.001": (
                "carriage bridge sliding on its rail; measured 0 of 17,472 "
                "sampled rail cells occupied (alignment 65.5)"
            ),
        },
        # An allowed pair may touch but must not occupy material.
        "allowed_interface_volume_limit": 0.005,
        # The bridge rides flush on the rail face, so a couple of vertices land
        # a hair inside it: measured 0.00099 mm and 0.00234 mm over 37 samples.
        # 0.01 mm is an order of magnitude above that and 1/200 of the smallest
        # authored feature in these models (~2 mm), so it separates coincident
        # surfaces from anything a reviewer could see. It is a stated tolerance,
        # not the measurement rounded up until the test passes.
        "allowed_interface_depth_tolerance_mm": 0.01,
    },
    "intent": (
        "An eleven-mark scale strip with nothing pointing at it, and 180 mm of "
        "travel that stops at nothing. Add an index finger on the carriage that "
        "reads against the strip, and end stops on the housing that explain "
        "where the travel ends."
    ),
}

ROLE_BUDGET = 2
AUTHOR_ROLES = {"body", "metal", "gasket", "readout"}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--model", dest="models", action="append", choices=tuple(SPECS))
    parser.add_argument("--revision", default=REVISION)
    parser.add_argument(
        "--trial-dir",
        help=(
            "Write everything here instead of the candidate tree. Use this to "
            "iterate: canonical revisions are never replaced (alignment 73.4)."
        ),
    )
    return parser.parse_args(args)


def rolled(points, degrees):
    """Roll an outline about the outward (Y) axis, the way the lens is rolled.

    Baking the roll into the outline keeps the object transform at identity.
    The shipped lens instead carries a live `rotation_euler.y`, which is fine
    for one object but would leave a frame of four bars each needing the same
    unapplied rotation to stay coherent.
    """
    if not degrees:
        return list(points)
    angle = math.radians(degrees)
    cos, sin = math.cos(angle), math.sin(angle)
    return [(x * cos + z * sin, -x * sin + z * cos) for x, z in points]


def plate(
    name,
    width,
    height,
    y_back,
    y_front,
    material,
    x=0.0,
    z=0.0,
    chamfer=None,
    bevel=None,
    roll_degrees=0.0,
):
    """A prism placed by outline rather than by object transform."""
    if chamfer:
        outline = hs.chamfered_outline(width, height, chamfer, z)
    else:
        half_x, half_z = width * 0.5, height * 0.5
        outline = [
            (-half_x, z - half_z),
            (half_x, z - half_z),
            (half_x, z + half_z),
            (-half_x, z + half_z),
        ]
    outline = rolled([(px + x, pz) for px, pz in outline], roll_degrees)
    obj = retopo.clean_prism(name, outline, y_back, y_front, material)
    if bevel:
        retopo.bevel(obj, bevel, 1)
    return obj


def attach(root, objects):
    for obj in objects:
        obj.parent = root
    return [obj.name for obj in objects]


def arc_band(
    name,
    inner_radius,
    outer_radius,
    start_degrees,
    end_degrees,
    y_back,
    y_front,
    material,
    segments=10,
    centre_x=0.0,
    centre_z=0.0,
):
    """A closed ring sector in the XZ plane, extruded along Y.

    Angles follow the needle: 0 points along +Z and positive rotates toward +X,
    which is what rotating the pivot about +Y does.
    """
    vertices = []
    for index in range(segments + 1):
        fraction = index / segments
        angle = math.radians(
            start_degrees + (end_degrees - start_degrees) * fraction
        )
        sin, cos = math.sin(angle), math.cos(angle)
        for radius in (inner_radius, outer_radius):
            for y in (y_back, y_front):
                vertices.append(
                    (centre_x + radius * sin, y, centre_z + radius * cos)
                )
    # Per station: 0 inner/back, 1 inner/front, 2 outer/back, 3 outer/front.
    faces = []
    for index in range(segments):
        here, following = index * 4, (index + 1) * 4
        faces.append((here + 1, here + 3, following + 3, following + 1))
        faces.append((here + 2, here + 0, following + 0, following + 2))
        faces.append((here + 3, here + 2, following + 2, following + 3))
        faces.append((here + 0, here + 1, following + 1, following + 0))
    last = segments * 4
    faces.append((0, 2, 3, 1))
    faces.append((last + 1, last + 3, last + 2, last + 0))
    return pilot._finalise(name, vertices, faces, material)


def meter_geometry(root, motion):
    """Measure the dial from the model instead of tabulating it per scale.

    Round, Medium and Large are the same instrument at 1x, 2x and 3x, so every
    dimension below is read off the needle and the tick ring. One builder then
    covers all three, and a fourth scale would need no new constants.
    """
    pivot = bpy.data.objects[motion["pivot"]]
    needle = bpy.data.objects["needle"]
    corners = [needle.matrix_world @ Vector(c) for c in needle.bound_box]
    centre = pivot.matrix_world.translation
    hub_radius = max(abs(point.x - centre.x) for point in corners)
    tail = min(point.z - centre.z for point in corners)
    tip = max(point.z - centre.z for point in corners)
    y_front = min(point.y for point in corners)
    y_back = max(point.y for point in corners)

    ticks = [
        obj
        for obj in pilot.meshes_under(root)
        if "tick" in obj.name.lower()
    ]
    tick_points = [
        obj.matrix_world @ Vector(c) for obj in ticks for c in obj.bound_box
    ]
    tick_radius = max(
        math.hypot(point.x - centre.x, point.z - centre.z) for point in tick_points
    )
    tick_y_front = min(point.y for point in tick_points)
    tick_y_back = max(point.y for point in tick_points)
    return {
        "hub_radius": hub_radius,
        "needle_tail": tail,
        "needle_tip": tip,
        "needle_y": (y_back, y_front),
        "tick_radius": tick_radius,
        "tick_y": (tick_y_back, tick_y_front),
        "pivot": pivot,
    }


def sweeps_into_static(root, pivot, mover, bearing_radius, samples=12):
    """Does `mover` touch static geometry *outside the bearing* over the sweep?

    The same classification the motion auditor uses: an overlap whose contact
    points all sit inside the bearing radius is the shaft in its boss, and the
    round meters legitimately have one there. Counting those as collisions
    would drop a part the approved candidates already carry.
    """
    statics = [
        obj for obj in pilot.meshes_under(root) if not _under(obj, pivot)
    ]
    trees = [pilot.bvh_for(obj) for obj in statics]
    centre = pivot.matrix_world.translation.copy()
    base = pivot.rotation_euler.copy()
    try:
        for index in range(samples + 1):
            angle = -55.0 + 110.0 * index / samples
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            tree, vertices, polygons = pilot.bvh_for(mover)
            for other, other_vertices, other_polygons in trees:
                for mine, theirs in tree.overlap(other):
                    points = pilot.triangle_contact_points(
                        [vertices[i] for i in polygons[mine]],
                        [other_vertices[i] for i in other_polygons[theirs]],
                    )
                    if any(
                        (point - centre).length > bearing_radius
                        for point in points
                    ):
                        return True
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return False


def brush_up_kinetic_meter(root, mats):
    """Give the dial a bearing, a balance and a marked zone.

    The shipped meter is a needle on a bare plate: the hub is a plain disc, the
    needle has no counterweight, and nothing on the dial says which end of the
    sweep is the one that matters. All three are standard analogue-instrument
    hardware, and all three are sized from the model's own needle so Round,
    Medium and Large share this one builder.
    """
    spec = next(
        value
        for value in SPECS.values()
        if value["root"] == root.name
    )
    geometry = meter_geometry(root, spec["motion"])
    hub = geometry["hub_radius"]
    y_back, y_front = geometry["needle_y"]
    pivot = geometry["pivot"]

    # Bearing boss: a collar the needle turns in, wide enough to show around
    # the hub disc and narrow enough that the counterweight clears it.
    # Everything here is placed on the pivot, not on the model origin. Round,
    # Medium and Large happen to have their pivot on the Y axis; WindowMeter's
    # sits 75 mm back in Z, and building about the origin put its boss and zone
    # band three quarters of the dial away from the needle.
    centre = pivot.matrix_world.translation
    boss = v4.cylinder_y(
        "kinetic_v6_needle_boss",
        hub * 1.15,
        (y_back - y_front) * 0.5,
        -(y_back + y_front) * 0.5 + (y_back - y_front) * 0.25,
        mats["metal"],
        16,
    )
    boss.location.x += centre.x
    boss.location.z += centre.z

    # Counterweight, seated on the needle tail and sweeping with it.
    scale = spec.get("counterweight_scale", 1.0)
    weight = plate(
        "kinetic_v6_needle_counterweight",
        hub * 0.98 * scale,
        hub * 0.70 * scale,
        y_back,
        y_front,
        mats["metal"],
        x=centre.x,
        z=centre.z + geometry["needle_tail"] - hub * 0.33 * scale,
        chamfer=hub * 0.16 * scale,
    )
    pilot.parent_keep_world(weight, pivot)
    # WindowMeter's dial reaches into the needle's depth band, so the weight has
    # nowhere to sweep there. That is declared in the spec rather than inferred:
    # a placement heuristic that decides per model silently dropped the weight
    # from the already-approved Medium and Large candidates too.
    if "counterweight" not in spec.get("meter_parts", ("boss", "counterweight", "zone")):
        bpy.data.objects.remove(weight, do_unlink=True)
        weight = None

    # Zone band over the top of the sweep, just inside the tick ring. It runs
    # slightly past the +55 degree stop so the needle at maximum sits inside
    # the band rather than on its edge.
    tick_back, tick_front = geometry["tick_y"]
    # Long and thin rather than short and deep: at 21 degrees by 10% of the
    # radius the first attempt just read as one fat tick.
    # The zone band sits inside the tick ring, which assumes the needle stops
    # short of the ticks. WindowMeter's needle reaches past them, so the band
    # is pushed outside the swept circle with the same clearance D-3 uses.
    swept = max(
        math.hypot(
            (obj.matrix_world @ vertex.co).x - centre.x,
            (obj.matrix_world @ vertex.co).z - centre.z,
        )
        for obj in pilot.meshes_under(root)
        if _under(obj, pivot)
        for vertex in obj.data.vertices
    )
    zone_inner = max(geometry["tick_radius"] * 0.885, swept + 0.0021)
    zone_outer = max(geometry["tick_radius"] * 0.945, zone_inner * 1.068)
    # And a third assumption: that there is dial to put the band on. On
    # WindowMeter the needle overhangs its dial, so once the band is pushed
    # clear of the swept circle there is nothing out there to carry it. Rather
    # than hang it in space, the band is skipped and the omission recorded.
    dial_reach = max(
        (
            math.hypot(
                (obj.matrix_world @ vertex.co).x - centre.x,
                (obj.matrix_world @ vertex.co).z - centre.z,
            )
            for obj in pilot.meshes_under(root)
            if not _under(obj, pivot)
            for vertex in obj.data.vertices
            if tick_front - 0.002 <= (obj.matrix_world @ vertex.co).y <= tick_back + 0.002
        ),
        default=0.0,
    )
    parts = [boss]
    if "zone" in spec.get("meter_parts", ("boss", "counterweight", "zone")) and dial_reach >= zone_outer:
        parts.append(
            arc_band(
                "kinetic_v6_zone_band",
                zone_inner,
                zone_outer,
                29.0,
                59.0,
                tick_back,
                tick_front,
                mats["readout"],
                segments=12,
                centre_x=centre.x,
                centre_z=centre.z,
            )
        )

    added = attach(root, parts)
    return [], added + ([weight.name] if weight is not None else [])


def brush_up_kinetic_lamp(root, mats):
    """Retain and protect the lens instead of parking it in a recess.

    The shipped assembly is a rolled lens slab, a flat socket behind it and one
    14 mm bar across the front. Nothing holds the lens and nothing explains the
    two side guards, which stand clear of everything.

    The lens roll is the theme signature here, so the bezel is rolled with it
    while the cage stays square to the housing: the rolled assembly reading
    against the straight cage is the point, not an accident.
    """
    removed = pilot.remove_objects(["kinetic_lamp_v6_cross_guard"])

    # Lens: 72 x 34 rolled -16 degrees, front face at y = -0.078.
    roll = -16.0
    bezel = []
    for label, width, height, x, z in (
        ("top", 0.086, 0.007, 0.0, 0.0225),
        ("bottom", 0.086, 0.007, 0.0, -0.0225),
        ("left", 0.007, 0.052, -0.0395, 0.0),
        ("right", 0.007, 0.052, 0.0395, 0.0),
    ):
        bezel.append(
            plate(
                f"kinetic_lamp_v6_lens_bezel_{label}",
                width,
                height,
                -0.064,
                -0.0765,
                mats["metal"],
                x=x,
                z=z,
                chamfer=0.0018,
                roll_degrees=roll,
            )
        )

    # One bar across the lens, square to the housing and long enough to land
    # inside both side guards (x = +-0.044 .. 0.056).
    #
    # A two-bar cage was tried first and rejected: it reads as better hardware
    # but cuts the emissive lens into strips, and on an MR instrument the lit
    # area is the payload. This bar is 8 mm where the shipped one was 14 mm, so
    # the lens ends up *less* occluded than before while still being guarded.
    cage = [
        plate(
            "kinetic_lamp_v6_guard_cage_bar",
            0.105,
            0.008,
            -0.0665,
            -0.0815,
            mats["metal"],
            chamfer=0.0025,
            bevel=0.0006,
        )
    ]

    # Glare hood over the top edge, tying the two side guards together.
    hood = plate(
        "kinetic_lamp_v6_glare_hood",
        0.112,
        0.013,
        -0.0605,
        -0.0805,
        mats["metal"],
        z=0.0395,
        chamfer=0.004,
        bevel=0.0009,
    )

    added = attach(root, bezel + cage + [hood])
    return removed, added


def brush_up_kinetic_status(root, mats):
    """Close the cell block and give the panel a face.

    The three lens bars reach x = +-0.085 but the carrier stops at +-0.083 and
    the only dividers sit between the lenses, so the outer two run off the ends
    with nothing framing them. The end ribs are made tall enough to meet both
    braces, which is also what turns the two loose braces into one frame.
    """
    # The rib has to straddle both the brace ends (x = +-0.084) and the outer
    # lens edges (x = +-0.085) to be held by them, so it spans 0.081 .. 0.090
    # rather than sitting in the 1 mm gap between the two.
    ribs = [
        plate(
            "kinetic_status_v6_end_rib",
            0.009,
            0.096,
            -0.068,
            -0.083,
            mats["metal"],
            x=x,
            chamfer=0.0015,
            bevel=0.0004,
        )
        for x in (-0.0855, 0.0855)
    ]

    hood = plate(
        "kinetic_status_v6_glare_hood",
        0.172,
        0.012,
        -0.0625,
        -0.0825,
        mats["metal"],
        z=0.056,
        chamfer=0.004,
        bevel=0.0009,
    )

    legend = plate(
        "kinetic_status_v6_legend_plate",
        0.140,
        0.012,
        -0.0665,
        -0.0745,
        mats["metal"],
        z=-0.056,
        chamfer=0.003,
        bevel=0.0007,
    )

    added = attach(root, ribs + [hood, legend])
    return [], added


def brush_up_kinetic_window_panel(root, mats):
    """Frame and label the panel, staying out of the vane's swept disc.

    The vane turns about the plate normal, so it sweeps a disc roughly 0.5 m
    across in the middle of a 1.6 m panel. Everything here is placed outside
    that disc; the panel has plenty of room elsewhere, and anything inside it
    would be struck at some angle of the +-42 degree travel.
    """
    display = bpy.data.objects["kinetic_recessed_display"]
    corners = [display.matrix_world @ Vector(c) for c in display.bound_box]
    x_max = max(point.x for point in corners)
    z_low = min(point.z for point in corners)
    z_high = max(point.z for point in corners)
    y_back = max(point.y for point in corners)
    y_front = min(point.y for point in corners)

    caps = [
        plate(
            "kinetic_v6_display_end_cap",
            0.030,
            (z_high - z_low) + 0.030,
            y_back,
            y_front - 0.004,
            mats["metal"],
            x=x,
            z=(z_high + z_low) * 0.5,
            chamfer=0.006,
            bevel=0.0012,
        )
        for x in (-x_max + 0.008, x_max - 0.008)
    ]
    hood = plate(
        "kinetic_v6_display_hood",
        (x_max - 0.010) * 2.0,
        0.034,
        y_back,
        y_front - 0.010,
        mats["metal"],
        z=z_high + 0.030,
        chamfer=0.008,
        bevel=0.0014,
    )
    # The legend was meant to go below the vane's swept disc, but the disc is
    # wider than the panel is deep: clearing it would put the strip outside the
    # model's own envelope. Measured, then dropped - the caps and hood sit
    # outside the disc in X, where there is room.
    vane = bpy.data.objects["vane"]
    vane_pivot = bpy.data.objects["vane_pivot"]
    vane_centre = vane_pivot.matrix_world.translation
    vane_reach = max(
        math.hypot(
            (vane.matrix_world @ vertex.co).x - vane_centre.x,
            (vane.matrix_world @ vertex.co).z - vane_centre.z,
        )
        for vertex in vane.data.vertices
    )
    return [], attach(root, caps + [hood])


def brush_up_kinetic_toggle(root, mats):
    """Seal the joint and flank the lever.

    The socket and retaining ring already say there is a sealed joint here, but
    nothing seals it; and the two detent marks on the plate say the lever has
    positions worth protecting, but nothing protects them. The boot is a ring
    rather than a solid pad because the stem passes through it and swings 56
    degrees inside it.

    """
    # A full boot ring on the plate cannot work, and measuring said so before
    # any was shipped: at rest the lever lies almost in the plate's plane and
    # reaches 84 mm from the pivot, so it sweeps through every radius of a
    # coaxial ring. What the lever never crosses is +-X - it stays inside
    # x = +-0.020 all the way through the sweep - so the seal becomes two cheeks
    # on those sides, overlapping the retaining ring (radius 0.0284) that holds
    # them.
    cheeks = [
        arc_band(
            f"kinetic_toggle_v6_socket_cheek_{index}",
            0.0240,
            0.0330,
            start,
            start + 30.0,
            -0.0616,
            -0.0704,
            mats["body"],
            segments=6,
        )
        for index, start in enumerate((75.0, 255.0))
    ]
    # Posts flank the swing plane in X, where the lever never goes: the switch
    # stays inside x = +-0.020 through the whole sweep.
    posts = [
        plate(
            "kinetic_toggle_v6_guard_post",
            0.010,
            0.070,
            # The plate face is recessed to y = -0.039, so a post that starts
            # at the outer housing bound would stand 23 mm off nothing.
            -0.0360,
            -0.0862,
            mats["metal"],
            x=x,
            z=0.020,
            chamfer=0.0028,
            bevel=0.0007,
        )
        for x in (-0.0345, 0.0345)
    ]
    return [], attach(root, cheeks + posts)


def brush_up_kinetic_slider(root, mats):
    """Give the travel a reading and an end.

    The scale strip carries eleven marks and nothing points at them, so the
    slider has a scale it cannot be read against; and the travel simply stops in
    mid-air. The index rides on the carriage in front of the marks - outboard of
    the rails, which the carriage passes through - and the stops sit on the
    housing beyond the handle bridge's furthest reach.

    Triangles are the constraint here, not room: the shipped model is already
    at 4,040 of 5,000, so the index is built without a bevel pass.
    """
    travel = bpy.data.objects["slider_travel"]

    # In front of the mark band (y -0.0800 .. -0.0750) and outboard of the rail
    # (y -0.0760 .. -0.0440), which the carriage travels the whole length of.
    index_finger = plate(
        "kinetic_slider_v6_index_finger",
        0.011,
        0.008,
        -0.0805,
        -0.0855,
        mats["readout"],
        x=0.0435,
        chamfer=0.0018,
    )
    pilot.parent_keep_world(index_finger, travel)

    # The handle bridge reaches z = +-0.133 at full travel; the stops sit past
    # that and are carried by the housing, not by the rails, which end at 0.135.
    stops = [
        plate(
            "kinetic_slider_v6_end_stop",
            0.104,
            0.012,
            # Outside the plate recess (x +-0.052, z +-0.1156) the housing face
            # is at y = -0.046, not at the -0.065 outer bound, so a stop that
            # started at -0.050 stood 4 mm off nothing.
            -0.0440,
            -0.0800,
            mats["metal"],
            z=z,
            chamfer=0.0035,
            bevel=0.0008,
        )
        for z in (-0.146, 0.146)
    ]
    return [], attach(root, stops) + [index_finger.name]


def brush_up_kinetic_rotary(root, mats):
    """Give the knob something to grip and something to turn inside.

    Ribs go on the knob so they turn with it; the seal stays on the housing so
    it does not. Both are placed off the knob's measured radius rather than
    off constants, the same way the meters are.
    """
    # The swept radius has to come from vertices, not from the bounding box.
    # The knob is a polygon presenting a flat to +X, so its axis-aligned bound
    # understates the circle its corners actually sweep, and a seal placed off
    # that bound is buried in the knob as soon as it turns.
    knob = bpy.data.objects["knob"]
    knob_radius = max(
        math.hypot((knob.matrix_world @ vertex.co).x, (knob.matrix_world @ vertex.co).z)
        for vertex in knob.data.vertices
    )

    # Wide and shallow, not narrow and tall: eight thin fins standing 3.5 mm
    # proud read as spokes on a capstan rather than as knurling on a knob.
    ribs = []
    for index in range(12):
        rib = plate(
            "kinetic_rotary_v6_grip_rib",
            0.015,
            0.006,
            -0.0740,
            -0.1005,
            mats["metal"],
            z=knob_radius - 0.0005,
            chamfer=0.0022,
            roll_degrees=index * 30.0,
        )
        ribs.append(rib)
        pilot.parent_keep_world(rib, knob)

    seal = arc_band(
        "kinetic_rotary_v6_dust_seal",
        knob_radius + 0.0015,
        knob_radius + 0.0105,
        0.0,
        360.0,
        -0.0455,
        -0.0545,
        mats["body"],
        segments=24,
    )
    return [], attach(root, [seal]) + [rib.name for rib in ribs]


BUILDERS = {
    "brush_up_kinetic_lamp": brush_up_kinetic_lamp,
    "brush_up_kinetic_status": brush_up_kinetic_status,
    "brush_up_kinetic_meter": brush_up_kinetic_meter,
    "brush_up_kinetic_toggle": brush_up_kinetic_toggle,
    "brush_up_kinetic_rotary": brush_up_kinetic_rotary,
    "brush_up_kinetic_slider": brush_up_kinetic_slider,
    "brush_up_kinetic_window_panel": brush_up_kinetic_window_panel,
}


def _under(obj, parent):
    node = obj
    while node is not None:
        if node is parent:
            return True
        node = node.parent
    return False


class CanonicalOutputExists(RuntimeError):
    """A canonical revision is already published and must not be replaced."""


def displayed(path, project_root):
    """Repo-relative when it is in the repo, absolute when it is a trial path."""
    try:
        return str(Path(path).relative_to(project_root))
    except ValueError:
        return str(path)


def publish_guard(blend_exists, report_exists, problems, trial):
    """Where, if anywhere, a run is allowed to write (alignment 73.4).

    Three rules, and no way around any of them:

    * a canonical revision that already exists is never replaced - iteration
      goes to a trial directory or to a new revision, not over an approved one;
    * nothing canonical is written until every check has run, so a failing run
      cannot leave a half-written report behind;
    * the Blend and the report are published together or not at all.

    Deliberately free of `bpy` and of the filesystem so the three cases can be
    exercised directly. There is no force option: replacing an approved
    revision is the thing this exists to prevent (alignment 73.4).
    """
    if trial:
        return {
            "mode": "trial",
            "may_write_report": True,
            "may_write_blend": not problems,
            "reason": "trial run; canonical outputs untouched",
        }
    if blend_exists or report_exists:
        raise CanonicalOutputExists(
            "canonical outputs already exist for this revision "
            f"(blend={blend_exists}, report={report_exists}); "
            "use --trial-dir to iterate, or publish a new revision"
        )
    if problems:
        return {
            "mode": "canonical",
            "may_write_report": False,
            "may_write_blend": False,
            "reason": f"{len(problems)} problem(s); nothing is published",
        }
    return {
        "mode": "canonical",
        "may_write_report": True,
        "may_write_blend": True,
        "reason": "all checks passed; publishing blend and report together",
    }


def self_test_publish_guard():
    """Existing output / failing audit / successful new revision."""
    results = {}

    try:
        publish_guard(True, False, [], trial=None)
    except CanonicalOutputExists as error:
        results["existing_output"] = {"raised": True, "message": str(error)}
    else:
        results["existing_output"] = {"raised": False}
    results["existing_output"]["passed"] = results["existing_output"]["raised"]

    failing = publish_guard(False, False, ["bad"], trial=None)
    results["failing_audit"] = {
        "decision": failing,
        "passed": not failing["may_write_report"] and not failing["may_write_blend"],
    }

    success = publish_guard(False, False, [], trial=None)
    results["successful_new_revision"] = {
        "decision": success,
        "passed": success["may_write_report"] and success["may_write_blend"],
    }

    trial = publish_guard(True, True, ["bad"], trial="/tmp/x")
    results["trial_never_publishes_blend"] = {
        "decision": trial,
        "passed": trial["may_write_report"] and not trial["may_write_blend"],
    }
    return results


def contact_pairs(audit_result):
    """Every pair that touched, whatever bucket it landed in."""
    return (
        set(audit_result.get("bearing_pairs", {}))
        | set(audit_result.get("outside_bearing_pairs", {}))
        | set(audit_result.get("allowed_interface_pairs", {}))
    )


def cleared_interface_pairs(motion, audit_result):
    """Sliding pairs that the interface allowance already cleared.

    Alignment 78.2: a pair the volume/depth guard has passed is judged by that
    guard, not asked for a second, bearing-shaped declaration.
    """
    declared = set(audit_result.get("allowed_interface_pairs", {}))
    if not declared:
        return set()
    failing = {
        label
        for label in declared
        for problem in allowance_problems(motion, audit_result)
        if label in problem
    }
    return declared - failing


def bearing_pair_problems(motion, baseline, candidate, cleared=frozenset()):
    """Any contact pair the candidate adds is a failure, inside or outside.

    Alignment 76.1. The previous rule only failed on new *outside-bearing*
    pairs, which meant a brush-up could introduce a brand new contact and pass
    simply because every contact point happened to fall inside the bearing
    radius. A new pair is a new mechanical relationship whichever side of that
    radius it sits on, so it has to be declared rather than inferred.

    `allowed_bearing_pairs` is deliberately a different schema from
    `allowed_interface_pairs`: that one excuses a *sliding* interface measured
    to have no volume, this one records an intended new *bearing* pair. Merging
    them would recreate the blanket "inside the radius, therefore fine" rule
    this replaces.
    """
    problems = []
    declared = motion.get("allowed_bearing_pairs") or {}
    added = sorted(contact_pairs(candidate) - contact_pairs(baseline) - set(cleared))
    for label in added:
        if label not in declared:
            problems.append(
                f"candidate introduces contact pair {label}; declare it in "
                "allowed_bearing_pairs with a reason if it is intended"
            )
    unseen = sorted(set(declared) - contact_pairs(candidate))
    for label in unseen:
        problems.append(
            f"allowed_bearing_pairs declares {label} but no contact was "
            "observed; remove the stale allowance"
        )
    # A pair can regress without changing its name. Alignment 82.1: on
    # MeterMedium the shipped `needle x plate` contact is the hub seated in its
    # mount, inside the bearing; a candidate turned the same label into a blade
    # reaching 80 mm outside it. Comparing name sets alone reports "no new
    # pairs" for exactly that. Category is part of the pair.
    # Only pairs the baseline already had: a brand new pair is reported once,
    # above, rather than twice under two headings.
    moved_outside = sorted(
        (set(candidate.get("outside_bearing_pairs", {})) & contact_pairs(baseline))
        - set(baseline.get("outside_bearing_pairs", {}))
        - set(cleared)
        - set(declared)
    )
    for label in moved_outside:
        problems.append(
            f"{label} was an inside-bearing contact in the baseline and now "
            "reaches outside the bearing radius"
        )

    # A bearing declaration is a claim that the pair stays inside the bearing.
    # Being named is not enough - if it ever reaches outside the radius it is
    # no longer the thing that was declared.
    outside = candidate.get("outside_bearing_pairs", {})
    for label in sorted(set(declared) & set(outside)):
        problems.append(
            f"allowed_bearing_pairs declares {label} as a bearing pair, but it "
            "reaches outside the bearing radius during the sweep"
        )
    for label, reason in sorted(declared.items()):
        if not str(reason).strip():
            problems.append(
                f"allowed_bearing_pairs declares {label} with no reason; an "
                "allowance without a stated reason cannot be reviewed"
            )
    return problems


def self_test_bearing_pairs():
    """Distant / outside / inside-undeclared / declared / mislabelled."""
    def audit(bearing=(), outside=()):
        return {
            "bearing_pairs": {name: {} for name in bearing},
            "outside_bearing_pairs": {name: {} for name in outside},
        }

    declared = {"allowed_bearing_pairs": {"needle x boss": "shaft in its boss"}}
    none = {}
    cases = {
        # Nothing new: the candidate keeps the baseline's pairs.
        "unchanged_pairs": (
            none, audit(bearing=("a x b",)), audit(bearing=("a x b",)), 0
        ),
        # A new pair outside the bearing must fail.
        "new_outside_pair": (
            none, audit(), audit(outside=("blade x dial",)), 1
        ),
        # A new pair *inside* the bearing must also fail unless declared - this
        # is the case the old rule let through.
        "new_inside_pair_undeclared": (
            none, audit(), audit(bearing=("weight x plate",)), 1
        ),
        # The declared one is allowed and stays in the report.
        "declared_bearing_pair": (
            declared, audit(), audit(bearing=("needle x boss",)), 0
        ),
        # A declaration that never matches anything is stale and must fail, so
        # a renamed object cannot leave a permanent blanket allowance behind.
        "stale_declaration": (
            {"allowed_bearing_pairs": {"needle x typo": "wrong name"}},
            audit(), audit(), 1
        ),
        # Declared as a bearing pair but measured outside the radius.
        "declared_bearing_outside_radius": (
            declared, audit(), audit(outside=("needle x boss",)), 1
        ),
        # A declaration with no reason cannot be reviewed.
        "empty_bearing_reason": (
            {"allowed_bearing_pairs": {"needle x boss": "   "}},
            audit(), audit(bearing=("needle x boss",)), 1
        ),
        # The same pair name, moved from inside the bearing to outside it: a
        # regression the name-set diff cannot see (alignment 82.3).
        "existing_inside_pair_moves_outside": (
            none,
            audit(bearing=("needle x plate",)),
            audit(outside=("needle x plate",)),
            1,
        ),
        # The opposite direction is an improvement and must not fail.
        "existing_outside_pair_moves_inside": (
            none,
            audit(outside=("needle x plate",)),
            audit(bearing=("needle x plate",)),
            0,
        ),
    }
    results = {}
    for name, (spec_motion, before, after, expected) in cases.items():
        found = bearing_pair_problems(spec_motion, before, after)
        results[name] = {
            "problems": found,
            "expected_count": expected,
            "passed": len(found) == expected,
        }
    # A new sliding pair cleared by the interface allowance must not also be
    # required to carry a bearing declaration.
    sliding_motion = {
        "allowed_interface_volume_limit": 0.005,
        "allowed_interface_depth_tolerance_mm": 0.01,
        "allowed_interface_pairs": {"bridge x rail": "rides the rail"},
    }
    sliding_after = {
        "bearing_pairs": {},
        "outside_bearing_pairs": {},
        "declared_allowances_not_seen": [],
        "allowed_interface_pairs": {
            "bridge x rail": {
                "occupied_fraction": 0.0,
                "occupied_material": {
                    "max_intruding_vertices": 0,
                    "deepest_intrusion_mm": 0.0,
                },
            }
        },
    }
    cleared = cleared_interface_pairs(sliding_motion, sliding_after)
    found = bearing_pair_problems(
        sliding_motion,
        {"bearing_pairs": {}, "outside_bearing_pairs": {}},
        sliding_after,
        cleared,
    )
    results["declared_sliding_not_bearing"] = {
        "problems": found,
        "expected_count": 0,
        "passed": not found,
    }
    return results


def allowance_problems(motion, audit_result):
    """Every way a named allowance can go wrong, as failures rather than notes.

    Alignment 68.3. An allowance is a standing claim about a pair, so it has to
    fail loudly in all four states, not only when the number is too big:

    * over-limit - the interface gained volume;
    * intruding - something sank in at a pose the grid did not sample;
    * unavailable - the volume could not be measured, so the claim is untested;
    * missing - the pair was declared but never observed, so the allowance is
      stale and would silently excuse a future pair of the same name.

    Kept free of `bpy` so the four cases can be exercised without a scene.
    """
    problems = []
    limit = motion.get("allowed_interface_volume_limit")
    for label in audit_result.get("declared_allowances_not_seen", []):
        problems.append(
            f"allowance declared for {label} but no contact was observed; "
            "remove it or explain why it no longer applies"
        )
    for label, entry in audit_result.get("allowed_interface_pairs", {}).items():
        material = entry.get("occupied_material")
        fraction = entry.get("occupied_fraction")
        if material is None or fraction is None:
            problems.append(
                f"allowed interface {label} could not be measured; an "
                "unverified allowance is not an allowance"
            )
            continue
        if limit is not None and fraction > limit:
            problems.append(
                f"allowed interface {label} occupies {fraction:.4f} of the "
                f"static part at pose {entry.get('worst_pose')} (limit {limit})"
            )
        intruding = material.get("max_intruding_vertices", 0)
        depth = material.get("deepest_intrusion_mm", 0.0)
        tolerance = motion.get("allowed_interface_depth_tolerance_mm", 0.0)
        if intruding and depth > tolerance:
            problems.append(
                f"allowed interface {label} has {intruding} movable vertices "
                f"up to {depth} mm inside the static part during the sweep "
                f"(tolerance {tolerance} mm)"
            )
    return problems


def self_test_allowance_guard():
    """Exercise pass / over-limit / unavailable / missing without a scene."""
    motion = {
        "allowed_interface_volume_limit": 0.005,
        "allowed_interface_depth_tolerance_mm": 0.01,
    }
    cases = {
        "pass": (
            {
                "declared_allowances_not_seen": [],
                "allowed_interface_pairs": {
                    "a x b": {
                        "occupied_fraction": 0.0,
                        "occupied_material": {"max_intruding_vertices": 0},
                    }
                },
            },
            0,
        ),
        "over_limit": (
            {
                "declared_allowances_not_seen": [],
                "allowed_interface_pairs": {
                    "a x b": {
                        "occupied_fraction": 0.02,
                        "worst_pose": "maximum",
                        "occupied_material": {"max_intruding_vertices": 0},
                    }
                },
            },
            1,
        ),
        "unavailable": (
            {
                "declared_allowances_not_seen": [],
                "allowed_interface_pairs": {
                    "a x b": {"occupied_fraction": None, "occupied_material": None}
                },
            },
            1,
        ),
        "missing": (
            {
                "declared_allowances_not_seen": ["a x b"],
                "allowed_interface_pairs": {},
            },
            1,
        ),
        "intruding": (
            {
                "declared_allowances_not_seen": [],
                "allowed_interface_pairs": {
                    "a x b": {
                        "occupied_fraction": 0.0,
                        "occupied_material": {
                            "max_intruding_vertices": 7,
                            "deepest_intrusion_mm": 0.9,
                        },
                    }
                },
            },
            1,
        ),
        # A vertex a hair inside a shared face is authoring tolerance, not an
        # intrusion; the guard has to tell the two apart or it cries wolf.
        "intruding_within_tolerance": (
            {
                "declared_allowances_not_seen": [],
                "allowed_interface_pairs": {
                    "a x b": {
                        "occupied_fraction": 0.0,
                        "occupied_material": {
                            "max_intruding_vertices": 2,
                            "deepest_intrusion_mm": 0.004,
                        },
                    }
                },
            },
            0,
        ),
    }
    results = {}
    for name, (payload, expected) in cases.items():
        found = allowance_problems(motion, payload)
        results[name] = {
            "problems": found,
            "expected_count": expected,
            "passed": len(found) == expected,
        }
    return results


def pose_pivot(pivot, motion, base, value):
    """Set one pose, rotary or linear."""
    axis = Vector(motion["axis"]).normalized()
    component = max(range(3), key=lambda index: abs(axis[index]))
    if motion.get("kind") == "linear":
        location = base.copy()
        location[component] = base[component] + value
        pivot.location = location
    else:
        posed = base.copy()
        posed[component] = base[component] + math.radians(value)
        pivot.rotation_euler = posed
    bpy.context.view_layer.update()


def motion_audit(root, motion):
    """Sweep the movable island and report which pairs really touch.

    Two departures from the pilot's version, both learned since. The island is
    everything under the pivot rather than one named object, because a brush-up
    can add parts to it. And contacts are classified by where they happen: an
    overlap whose contact points all sit inside the bearing radius is the shaft
    turning in its boss, while one that reaches outside it is the failure.
    Pairs are reported rather than counted so the caller can diff the candidate
    against the baseline (alignment 50.3).
    """
    pivot = bpy.data.objects[motion["pivot"]]
    meshes = pilot.meshes_under(root)
    movable = [obj for obj in meshes if _under(obj, pivot)]
    statics = [obj for obj in meshes if not _under(obj, pivot)]
    if not movable:
        raise RuntimeError(f"nothing under {motion['pivot']}")

    centre = pivot.matrix_world.translation.copy()
    interface = motion["interface_radius"]
    static_trees = [(obj.name, *pilot.bvh_for(obj)) for obj in statics]

    linear = motion.get("kind") == "linear"
    base = (pivot.location if linear else pivot.rotation_euler).copy()
    low, high = motion["sweep"]
    pairs = {}
    try:
        for index in range(motion["steps"] + 1):
            value = low + (high - low) * index / motion["steps"]
            pose_pivot(pivot, motion, base, value)
            for obj in movable:
                tree, vertices, polygons = pilot.bvh_for(obj)
                for name, other, other_vertices, other_polygons in static_trees:
                    outside = 0
                    hits = 0
                    for mine, theirs in tree.overlap(other):
                        first = [vertices[i] for i in polygons[mine]]
                        second = [other_vertices[i] for i in other_polygons[theirs]]
                        points = pilot.triangle_contact_points(first, second)
                        if not points:
                            continue
                        hits += 1
                        if any(
                            (point - centre).length > interface for point in points
                        ):
                            outside += 1
                    if not hits:
                        continue
                    entry = pairs.setdefault(
                        f"{obj.name} x {name}",
                        {"samples": 0, "max_triangles": 0, "outside_bearing": 0},
                    )
                    entry["samples"] += 1
                    entry["max_triangles"] = max(entry["max_triangles"], hits)
                    entry["outside_bearing"] = max(entry["outside_bearing"], outside)
    finally:
        if linear:
            pivot.location = base
        else:
            pivot.rotation_euler = base
        bpy.context.view_layer.update()

    allowed = motion.get("allowed_interface_pairs") or {}
    # Alignment 68.3: one rest-pose measurement cannot see an intrusion that
    # only happens part-way along the travel. The grid volume is measured at
    # the three named poses, and every other pose is guarded by counting
    # movable vertices strictly inside the static part - which is 0 for a
    # surface graze and non-zero the moment anything sinks in.
    occupancy = {}
    for label in allowed:
        if label not in pairs:
            continue
        mover_name, static_name = label.split(" x ")
        mover = bpy.data.objects.get(mover_name)
        static_obj = bpy.data.objects.get(static_name)
        if mover is None or static_obj is None:
            occupancy[label] = None
            continue
        per_pose = {}
        worst = None
        worst_pose = None
        for pose_name, pose_value in motion["poses"].items():
            pose_pivot(pivot, motion, base, pose_value)
            volume = section.occupied_volume(static_obj, [mover])
            per_pose[pose_name] = volume
            fraction = (volume or {}).get("occupied_fraction")
            if fraction is not None and (worst is None or fraction > worst):
                worst, worst_pose = fraction, pose_name
        intruding = {}
        deepest = 0.0
        for index in range(motion["steps"] + 1):
            value = low + (high - low) * index / motion["steps"]
            pose_pivot(pivot, motion, base, value)
            static_tree, _, _ = pilot.bvh_for(static_obj)
            count = 0
            for vertex in mover.data.vertices:
                world = mover.matrix_world @ vertex.co
                if not section.inside(static_tree, world):
                    continue
                count += 1
                # How far in, not just how many: a vertex a micrometre inside a
                # shared face is a tolerance, one a millimetre in is a defect.
                _, _, _, distance = static_tree.find_nearest(world)
                if distance is not None:
                    deepest = max(deepest, distance)
            if count:
                intruding[round(value, 6)] = count
        pose_pivot(pivot, motion, base, 0.0 if not linear else 0.0)
        occupancy[label] = {
            "by_pose": per_pose,
            "worst_occupied_fraction": worst,
            "worst_pose": worst_pose,
            "poses_measured": sorted(per_pose),
            "sweep_samples_checked": motion["steps"] + 1,
            "intruding_vertices_by_sample": intruding,
            "max_intruding_vertices": max(intruding.values(), default=0),
            "deepest_intrusion_mm": round(deepest * 1000.0, 6),
        }

    return {
        "pivot": motion["pivot"],
        "kind": motion.get("kind", "rotary"),
        "sweep": list(motion["sweep"]),
        "allowed_interface_pairs": {
            label: dict(
                entry,
                reason=allowed[label],
                occupied_fraction=(occupancy.get(label) or {}).get(
                    "worst_occupied_fraction"
                ),
                occupied_material=occupancy.get(label),
            )
            for label, entry in sorted(pairs.items())
            if label in allowed
        },
        "declared_allowances_not_seen": sorted(set(allowed) - set(pairs)),
        "steps": motion["steps"],
        "bearing_radius": interface,
        "movable": sorted(obj.name for obj in movable),
        "bearing_pairs": {
            label: entry
            for label, entry in sorted(pairs.items())
            if not entry["outside_bearing"] and label not in allowed
        },
        "outside_bearing_pairs": {
            label: entry
            for label, entry in sorted(pairs.items())
            if entry["outside_bearing"] and label not in allowed
        },
    }


def snapshot(root):
    meshes = pilot.meshes_under(root)
    stats, per_object = pilot.triangulated_stats(meshes)
    return {
        "meshes": sorted(obj.name for obj in meshes),
        "triangles": stats["faces"],
        "triangles_by_object": dict(sorted(per_object.items())),
        "topology": stats,
        "material_roles": pilot.material_role_summary(meshes),
        "bounds": pilot.world_bounds(meshes),
        "hierarchy": {
            obj.name: (obj.parent.name if obj.parent else None)
            for obj in sorted(root.children_recursive, key=lambda item: item.name)
        },
        "root_properties": {
            key: root[key] for key in sorted(root.keys()) if not key.startswith("_")
        },
    }


def support_audit(root, added):
    """Which existing parts each new part actually touches.

    Exact triangle-triangle contact, not `BVHTree.overlap`, which pairs
    triangles tens of millimetres apart (alignment 8.2).
    """
    meshes = pilot.meshes_under(root)
    trees = {obj.name: pilot.bvh_for(obj) for obj in meshes}
    report = {}
    for name in added:
        tree, vertices, polygons = trees[name]
        touching = []
        for other in meshes:
            if other.name == name:
                continue
            other_tree, other_vertices, other_polygons = trees[other.name]
            for mine, theirs in tree.overlap(other_tree):
                first = [vertices[i] for i in polygons[mine]]
                second = [other_vertices[i] for i in other_polygons[theirs]]
                if pilot.triangle_contact_points(first, second):
                    touching.append(other.name)
                    break
        report[name] = sorted(set(touching))
    return report


def runtime_material_count(roles):
    opaque = any(role in roles for role in ("body", "metal", "gasket"))
    return int(opaque) + int("readout" in roles)


def validate(root, spec, before, after, added, removed, supports, motions):
    problems = []
    if root.name != spec["root"]:
        problems.append(f"root renamed: {root.name} != {spec['root']}")
    for key, value in before["root_properties"].items():
        if after["root_properties"].get(key) != value:
            problems.append(f"root property changed: {key}")

    kept = set(before["meshes"]) - set(removed)
    if not kept <= set(after["meshes"]):
        problems.append(
            f"unexpectedly dropped: {sorted(kept - set(after['meshes']))}"
        )
    if set(after["meshes"]) - kept != set(added):
        problems.append("added meshes do not match the builder's report")
    for name in kept:
        if before["hierarchy"].get(name) != after["hierarchy"].get(name):
            problems.append(f"reparented: {name}")
        if before["triangles_by_object"][name] != after["triangles_by_object"][name]:
            problems.append(f"existing mesh retopologised: {name}")

    if after["triangles"] > spec["triangle_budget"]:
        problems.append(
            f"{after['triangles']} triangles > {spec['triangle_budget']}"
        )

    # The mount plane is the contract with Unity: the model hangs off y = 0.
    if abs(after["bounds"]["max"][1]) > 1e-9:
        problems.append(f"mount plane moved: max Y = {after['bounds']['max'][1]}")
    # The envelope rows describe the mounting plate, not the whole model, so a
    # model with a lever standing off it (Toggle reaches z = 0.157 against a
    # 0.146 row) already exceeds its row before any brush-up. Rounds have no row
    # at all. In both cases the enforceable rule is the baseline: hold the spec
    # where the spec is already met, and otherwise simply do not grow.
    for axis, label in ((0, "width"), (2, "depth")):
        baseline_span = before["bounds"]["max"][axis] - before["bounds"]["min"][axis]
        row = spec["envelope_xz"][axis // 2] if spec["envelope_xz"] else None
        limit = baseline_span if row is None else max(row, baseline_span)
        span = after["bounds"]["max"][axis] - after["bounds"]["min"][axis]
        if span > limit + 1e-6:
            problems.append(
                f"{label} {span:.6f} exceeds {limit:.6f} "
                f"(row {row}, baseline {baseline_span:.6f})"
            )
    if after["bounds"]["min"][1] < before["bounds"]["min"][1] - 1e-9:
        problems.append(
            f"grew outward: y min {after['bounds']['min'][1]} < "
            f"{before['bounds']['min'][1]}"
        )

    roles = set(after["material_roles"])
    if roles - AUTHOR_ROLES:
        problems.append(f"unexpected roles: {sorted(roles - AUTHOR_ROLES)}")
    if "readout" not in roles:
        problems.append("readout role lost")
    count = runtime_material_count(roles)
    if count > ROLE_BUDGET:
        problems.append(f"runtime materials {count} > {ROLE_BUDGET}")

    for stats, stage in ((after["topology"], "final"),):
        if stats["non_manifold_edges"]:
            problems.append(f"non-manifold {stage}: {stats['non_manifold_edges']}")
        if stats["zero_area_faces"]:
            problems.append(f"degenerate {stage}: {stats['zero_area_faces']}")

    unsupported = sorted(name for name, touching in supports.items() if not touching)
    if unsupported:
        problems.append(f"floating parts, supported by nothing: {unsupported}")

    if motions:
        baseline_motion, candidate_motion = motions
        if baseline_motion["movable"] != candidate_motion["movable"]:
            gained = sorted(
                set(candidate_motion["movable"]) - set(baseline_motion["movable"])
            )
            lost = sorted(
                set(baseline_motion["movable"]) - set(candidate_motion["movable"])
            )
            if lost:
                problems.append(f"movable island lost parts: {lost}")
            if set(gained) - set(added):
                problems.append(f"movable island gained unbuilt parts: {gained}")
        problems.extend(allowance_problems(spec["motion"], candidate_motion))
        problems.extend(
            bearing_pair_problems(
                spec["motion"],
                baseline_motion,
                candidate_motion,
                cleared_interface_pairs(spec["motion"], candidate_motion),
            )
        )

    problems.extend(pilot.forbidden_datablocks())
    return problems


def run_one(project_root, label, revision, trial_dir=None):
    spec = SPECS[label]
    theme, key = label.split("/")
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_{key}_{theme}_V6_Retopo.blend"
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    stat_before = source.stat()
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[spec["root"]]

    motion = spec.get("motion")
    if motion:
        motion = dict(motion)
        if "bearing_radius_hub_multiple" in motion:
            # Meters: derived from the baseline hub so the same number is used
            # for both sweeps and so a fourth scale needs no new constant.
            motion["interface_radius"] = (
                meter_geometry(root, motion)["hub_radius"]
                * motion["bearing_radius_hub_multiple"]
            )
        else:
            motion["interface_radius"] = motion["bearing_radius"]

    before = snapshot(root)
    before_motion = motion_audit(root, motion) if motion else None
    mats = pilot.materials_by_role()
    removed, added = BUILDERS[spec["builder"]](root, mats)
    after = snapshot(root)
    after_motion = motion_audit(root, motion) if motion else None
    supports = support_audit(root, added)
    problems = validate(
        root,
        spec,
        before,
        after,
        added,
        removed,
        supports,
        (before_motion, after_motion) if motion else None,
    )

    stat_after = source.stat()
    if (stat_before.st_mtime_ns, stat_before.st_size) != (
        stat_after.st_mtime_ns,
        stat_after.st_size,
    ):
        problems.append(f"source blend changed on disk: {source}")

    candidate_dir = (
        Path(trial_dir) if trial_dir
        else project_root / "ArtSource/Blender/BrushUp/Opus5" / theme
    )
    blend = candidate_dir / f"BL_{key}_{theme}_V6_Opus5_{revision}_Retopo.blend"
    report_path = (
        candidate_dir / "reports" / f"{key}_{theme}_V6_Opus5_{revision}.json"
    )
    report = {
        "model": label,
        "revision": revision,
        "intent": spec["intent"],
        "source_blend": str(source.relative_to(project_root)),
        "source_unmodified": True,
        "candidate_blend": displayed(blend, project_root),
        "meshes_removed": removed,
        "meshes_added": added,
        "support": supports,
        "motion": (
            {
                "bearing_radius": motion["interface_radius"],
                "poses_degrees": motion["poses"],
                "baseline": before_motion,
                "candidate": after_motion,
            }
            if motion
            else None
        ),
        "triangle_budget": spec["triangle_budget"],
        "envelope_xz": (
            list(spec["envelope_xz"])
            if spec["envelope_xz"]
            else "baseline bounds (round model, no envelope row)"
        ),
        "baseline": before,
        "candidate": after,
        "difference": {
            "triangles_baseline": before["triangles"],
            "triangles_candidate": after["triangles"],
            "triangles_added": after["triangles"] - before["triangles"],
            "roles_baseline": sorted(before["material_roles"]),
            "roles_candidate": sorted(after["material_roles"]),
            "bounds_baseline": before["bounds"],
            "bounds_candidate": after["bounds"],
        },
        "problems": problems,
        "authoring_environment": blender_compat.provenance(),
    }
    record = publishing.publish(
        blend,
        report_path,
        report,
        problems,
        trial_dir,
        save_blend=pilot.save_blend,
        reopen_blend=lambda path: bpy.ops.wm.open_mainfile(
            filepath=str(path), load_ui=False
        ),
    )
    report["publish"] = record
    if problems:
        raise RuntimeError(f"{label}: " + "; ".join(problems))
    print(
        f"[Opus5BrushUp] {label}: {before['triangles']} -> {after['triangles']} tris "
        f"(+{after['triangles'] - before['triangles']}, budget {spec['triangle_budget']}), "
        f"+{len(added)} parts, -{len(removed)}, "
        f"roles {'+'.join(sorted(after['material_roles']))}, "
        f"all parts supported"
    )
    return report


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    models = tuple(args.models) if args.models else tuple(SPECS)
    guard = self_test_allowance_guard()
    failed = sorted(name for name, case in guard.items() if not case["passed"])
    if failed:
        raise SystemExit(f"allowance guard self-test failed: {failed}")
    print(
        "[Opus5BrushUp] allowance guard self-test: "
        + ", ".join(f"{name} OK" for name in sorted(guard))
    )
    publish = publishing.self_test_publish_transaction(
        Path(args.trial_dir or tempfile.mkdtemp(prefix="opus5-guard-"))
        / "publish_self_test"
    )
    bearing = self_test_bearing_pairs()
    bearing_broken = sorted(
        name for name, case in bearing.items() if not case["passed"]
    )
    if bearing_broken:
        raise SystemExit(f"bearing pair self-test failed: {bearing_broken}")
    print(
        "[Opus5BrushUp] bearing pair self-test: "
        + ", ".join(f"{name} OK" for name in sorted(bearing))
    )
    broken = sorted(name for name, case in publish.items() if not case["passed"])
    if broken:
        raise SystemExit(f"publish guard self-test failed: {broken}")
    print(
        "[Opus5BrushUp] publish guard self-test: "
        + ", ".join(f"{name} OK" for name in sorted(publish))
    )
    reports = [
        run_one(project_root, label, args.revision, args.trial_dir)
        for label in models
    ]
    summary = (
        Path(args.trial_dir) / f"brushup_{args.revision.lower()}_summary.json"
        if args.trial_dir
        else project_root
        / "ArtSource/Blender/BrushUp/Opus5"
        / f"brushup_{args.revision.lower()}_summary.json"
    )
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(
        json.dumps(
            {
                "revision": args.revision,
                "models": {
                    report["model"]: {
                        "triangles": report["candidate"]["triangles"],
                        "triangles_added": report["difference"]["triangles_added"],
                        "parts_added": report["meshes_added"],
                        "parts_removed": report["meshes_removed"],
                        "roles": report["difference"]["roles_candidate"],
                        "bounds": report["candidate"]["bounds"],
                    }
                    for report in reports
                },
                "allowance_guard_self_test": guard,
                "publish_guard_self_test": publish,
                "bearing_pair_self_test": bearing,
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5BrushUp] summary -> {displayed(summary, project_root)}")


if __name__ == "__main__":
    main()
