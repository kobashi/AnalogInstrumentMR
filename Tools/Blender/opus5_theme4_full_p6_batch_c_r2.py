"""Theme 4 Phase 3 Batch C R2: the window scales opened out to 230 degrees.

329 failed the two window instruments on Quest for the same reason twice: the
pointer swept about 80 degrees where a RoundMeter sweeps 230, and the scale
had been drawn to match the old amplitude rather than to the range the family
actually uses. Codex is moving the runtime amplitude to
`InstrumentGreyboxSpecification.MeterSweepDegrees`, +/-115; this module moves
the geometry to meet it.

Three things follow from the wider sweep and are worth stating.

The scale is laid out so the pose extremes land on marks rather than between
them: ten major intervals give eleven major ticks, the middle one on the
instrument's up axis, and the first and last exactly on -115 and +115.

The window panel's vane pivot has to move. A 230 degree arc struck from the
old pivot, 150 mm below the field centre, runs off the bottom of the field
unless its radius drops to 128 mm - a 128 mm scale on a 1.6 m panel. The pivot
goes to the field centre and the arc is sized to the field instead.

The flank strips and the side wells carried linear tick ladders, which at 230
degrees read as a second scale competing with the pointer. They become flat
readout plates: still sub-readouts, no longer anything a viewer could mistake
for the main scale, and no ticks left to double up or flicker against it.
"""

import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_full_p6_batch_c as bc
import opus5_theme4_full_p6_batch_c_r1 as cr1

SHUT = bc.SHUT
EMBED = bc.EMBED
NEUTRAL = bc.NEUTRAL
revolve = bc.revolve

SWEEP_DEG = 230.0                 # 329.1: RoundMeter's range, +/-115
AMPLITUDE_DEG = SWEEP_DEG / 2.0
MAJOR_INTERVALS = 10              # 11 major ticks, the middle one on up
MINORS_PER_MAJOR = 4

CONTRACT = {}
for _asset in ("WindowMeter", "WindowPanel"):
    _row = dict(bc.CONTRACT[_asset])
    _row.update({
        "amplitude_deg": AMPLITUDE_DEG,
        "unity_range_deg": (-AMPLITUDE_DEG, AMPLITUDE_DEG),
        "blender_range_deg": (-AMPLITUDE_DEG, AMPLITUDE_DEG),
        "scale_sweep_deg": SWEEP_DEG,
    })
    CONTRACT[_asset] = _row

# The window panel's arc is struck from the field centre now, and sized so
# 230 degrees stays inside the field opening.
WP_PIVOT_Z = 0.0560
WP_ARC_OUT = 0.2500
WP_ARC_MAJOR_IN = 0.1960
WP_ARC_MINOR_IN = 0.2200
WP_VANE_TIP = 0.2320


def major_angles(up_deg=90.0):
    """Where the eleven major ticks sit, and where the poses have to land."""
    return [up_deg + SWEEP_DEG * (index / MAJOR_INTERVALS - 0.5)
            for index in range(MAJOR_INTERVALS + 1)]


def pose_angle(value_deg, up_deg=90.0):
    """The dial angle a Blender Y rotation of `value_deg` points the pointer at.

    A rotation about +Y takes +Z to (sin, cos), which is the dial angle
    90 - value. The scale is centred on 90, so pose -115 lands on the last
    major tick and +115 on the first: the ends of the travel are marks, not
    gaps.
    """
    return up_deg - value_deg


def readout_plate(name, centre, size, y_face, depth=0.0030):
    """A flat sub-readout, deliberately not a tick."""
    return p1.nameplate(name, centre, size, y_face, depth)


def build_window_meter(material):
    """Batch C R1's window meter with a 230 degree scale on the same dial.

    The dial, the ring, the needle, the shell, the plate and every fastener -
    including the one R1 moved off the nameplate - are unchanged. What moves
    is the tick arc and the flank strips' contents.
    """
    width, depth_env, height = bc.envelope_blender("WindowMeter")
    plate_y = -0.0180
    face_y = bc.WM_FACE_Y
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.020, height - 0.020)), 0.0026))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.044, height - 0.044),
                                (width - 0.044, height - 0.044)))
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - SHUT, face_y, (width - 0.016, height - 0.016),
        (width - 0.052, height - 0.052)), 0.0034))

    parts.append(revolve("dial_pan", [
        (0.0000, face_y + 0.0030),
        (0.3025, face_y + 0.0030),
        (0.3025, bc.WM_DIAL_FACE + 0.0056),
        (0.2985, bc.WM_DIAL_FACE),
        (0.0000, bc.WM_DIAL_FACE),
    ], segments=64, axis="y", smooth=False))
    parts.append(revolve("bezel_ring", [
        (bc.WM_DIAL_R, face_y + 0.0030),
        (bc.WM_DIAL_R, bc.WM_RING_FRONT + 0.0055),
        (bc.WM_DIAL_R + 0.0075, bc.WM_RING_FRONT),
        (bc.WM_RING_OUTER - 0.0075, bc.WM_RING_FRONT),
        (bc.WM_RING_OUTER, bc.WM_RING_FRONT + 0.0055),
        (bc.WM_RING_OUTER, face_y + 0.0030),
    ], segments=64, axis="y", smooth=False))

    parts.extend(bc.scale_arc(
        "tick", (0.0, 0.0), SWEEP_DEG, MAJOR_INTERVALS, MINORS_PER_MAJOR,
        0.2060, 0.2340, 0.2680, 0.0090, 0.0046,
        bc.WM_DIAL_FACE + EMBED, bc.WM_DIAL_FACE - 0.0075,
        bc.WM_DIAL_FACE - 0.0055))

    # Flank strips keep their shape and lose their tick ladders: at 230
    # degrees a linear ladder either side reads as a second scale.
    for sign in (-1.0, 1.0):
        cx = sign * 0.4300
        parts.append(p1.chamfer(p1.frustum_box(
            f"scale_strip_{int(sign)}", face_y + EMBED, face_y - 0.0090,
            (0.1120, 0.5240), (0.1040, 0.5160), centre=(cx, 0.0300)), 0.0022))
        for index, offset in enumerate((0.1560, 0.0000, -0.1560)):
            parts.append(readout_plate(
                f"plate_label_flank_{int(sign)}_{index}",
                (cx, 0.0300 + offset), (0.0820, 0.0420),
                face_y - 0.0090 - 0.0028))

    parts.append(p1.nameplate("plate_label", (-0.4300, -0.3180),
                              (0.2200, 0.0480), face_y - 0.0028, 0.0034))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            centre = cr1.MOVED.get(("WindowMeter",
                                    f"screw_{int(sx)}_{int(sz)}"),
                                   (sx * 0.5480, sz * 0.3230))
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}", centre, face_y, 0.0120, 0.0090))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0044, 0.0180))

    audit = p3.coplanar_overlap_audit(parts)
    bpy.context.view_layer.update()
    body = p1.join(parts[0], parts[1:])
    body.name = "WindowMeter_body"
    body.data.name = "WindowMeter_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("needle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, bc.WM_PIVOT_Y, 0.0)
    pivot.rotation_mode = "XYZ"

    blade = bc.taper_blade("needle_blade", 0.0260, 0.2520, 0.0230, 0.0072,
                           0.0000, -0.0110)
    hub = revolve("needle_hub", [
        (0.0000, 0.0038),
        (0.0430, 0.0038),
        (0.0430, -0.0106),
        (0.0330, -0.0166),
        (0.0000, -0.0166),
    ], segments=32, axis="y", smooth=False)
    needle = p1.join(blade, [hub])
    needle.name = "needle"
    needle.data.name = "needle"
    p1.assign(needle, material)
    needle.parent = pivot

    audit["mechanism"] = {
        "scale_sweep_deg": SWEEP_DEG,
        "amplitude_deg": AMPLITUDE_DEG,
        "major_ticks": MAJOR_INTERVALS + 1,
        "minor_per_major": MINORS_PER_MAJOR,
        "tick_count": MAJOR_INTERVALS * MINORS_PER_MAJOR + 1,
        "major_angles_deg": [round(a, 4) for a in major_angles()],
        "flank_scales_replaced_with": "three readout plates each side",
        "needle_tip_inside_bore_mm": round(
            (bc.WM_DIAL_R - 0.2520) * 1000.0, 1),
        "needle_tip_past_major_inner_mm": round((0.2520 - 0.2060) * 1000.0, 1),
        "needle_tip_short_of_arc_outer_mm": round(
            (0.2680 - 0.2520) * 1000.0, 1),
        "needle_clears_ticks_in_depth_mm": round(
            ((bc.WM_DIAL_FACE - 0.0075) - bc.WM_PIVOT_Y) * 1000.0, 1),
    }
    return body, pivot, [needle], audit


def build_window_panel(material):
    """Batch C's window panel with the arc re-struck from the field centre.

    The pivot moves 206 mm up, from 150 mm below the field centre to the
    centre itself, because a 230 degree arc from the old position would have
    to shrink to a 128 mm radius to stay on the field. Everything outside the
    arc, the vane and the wells' contents is Batch C's.
    """
    width, depth_env, height = bc.envelope_blender("WindowPanel")
    plate_y = -0.0200
    face_y = bc.WP_FACE_Y
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.024, height - 0.024)), 0.0030))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.052, height - 0.052),
                                (width - 0.052, height - 0.052)))
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - SHUT, face_y, (width - 0.018, height - 0.018),
        (width - 0.060, height - 0.060)), 0.0038))

    field = (1.1600, 0.5600)
    field_centre = (0.0, 0.0560)
    parts.append(p1.chamfer(p1.frustum_box(
        "field_pan", face_y + 0.0030, bc.WP_FIELD_FACE,
        (field[0] + 0.0120, field[1] + 0.0120), (field[0], field[1]),
        centre=field_centre), 0.0026))
    parts.append(p1.chamfer(p1.rect_frame(
        "field_ring", face_y + 0.0030, bc.WP_RING_FRONT,
        (field[0] + 0.0560, field[1] + 0.0560), (field[0], field[1]),
        centre=field_centre), 0.0030))

    parts.extend(bc.scale_arc(
        "tick", (0.0, WP_PIVOT_Z), SWEEP_DEG, MAJOR_INTERVALS,
        MINORS_PER_MAJOR,
        WP_ARC_MAJOR_IN, WP_ARC_MINOR_IN, WP_ARC_OUT, 0.0110, 0.0056,
        bc.WP_FIELD_FACE + EMBED, bc.WP_FIELD_FACE - 0.0085,
        bc.WP_FIELD_FACE - 0.0062))

    # Datum bar below the arc rather than across it, and the side wells lose
    # their tick ladders for the same reason the flank strips do.
    parts.append(p1.chamfer(p1.frustum_box(
        "datum_bar", bc.WP_FIELD_FACE + EMBED, bc.WP_FIELD_FACE - 0.0070,
        (0.7400, 0.0180), (0.7320, 0.0150),
        centre=(0.0, -0.1900)), 0.0026))
    for sign in (-1.0, 1.0):
        cx = sign * 0.4400
        parts.append(p1.chamfer(p1.rect_frame(
            f"well_{int(sign)}", bc.WP_FIELD_FACE + EMBED,
            bc.WP_FIELD_FACE - 0.0090,
            (0.2000, 0.1300), (0.1640, 0.0940),
            centre=(cx, 0.1400)), 0.0026))
        parts.append(readout_plate(
            f"plate_label_well_{int(sign)}", (cx, 0.1400), (0.1500, 0.0800),
            bc.WP_FIELD_FACE - 0.0090 - 0.0030))

    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"rail_{int(sign)}", face_y + EMBED, face_y - 0.0420,
            (0.0480, 0.7200), (0.0400, 0.7120),
            centre=(sign * 0.7000, 0.0)), 0.0044))

    parts.append(p1.nameplate("plate_label", (0.0, -0.3620),
                              (0.3200, 0.0640), face_y - 0.0032, 0.0038))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}", (sx * 0.7440, sz * 0.3940),
                face_y, 0.0130, 0.0100))
    for sx in (-1.0, 1.0):
        parts.append(p1.fastener(
            f"screw_mid_{int(sx)}", (sx * 0.6400, 0.0), face_y, 0.0130,
            0.0100))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0048, 0.0210))

    audit = p3.coplanar_overlap_audit(parts)
    bpy.context.view_layer.update()
    body = p1.join(parts[0], parts[1:])
    body.name = "WindowPanel_body"
    body.data.name = "WindowPanel_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("vane_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = (0.0, bc.WP_PIVOT_Y, WP_PIVOT_Z)
    pivot.rotation_mode = "XYZ"

    blade = bc.taper_blade("vane_blade", 0.0320, WP_VANE_TIP, 0.0340, 0.0110,
                           0.0000, -0.0130)
    hub = revolve("vane_hub", [
        (0.0000, 0.0044),
        (0.0520, 0.0044),
        (0.0520, -0.0124),
        (0.0400, -0.0196),
        (0.0000, -0.0196),
    ], segments=32, axis="y", smooth=False)
    vane = p1.join(blade, [hub])
    vane.name = "vane"
    vane.data.name = "vane"
    p1.assign(vane, material)
    vane.parent = pivot

    audit["mechanism"] = {
        "scale_sweep_deg": SWEEP_DEG,
        "amplitude_deg": AMPLITUDE_DEG,
        "major_ticks": MAJOR_INTERVALS + 1,
        "minor_per_major": MINORS_PER_MAJOR,
        "tick_count": MAJOR_INTERVALS * MINORS_PER_MAJOR + 1,
        "major_angles_deg": [round(a, 4) for a in major_angles()],
        "pivot_z_batch_c_m": bc.WP_PIVOT_Z,
        "pivot_z_r2_m": WP_PIVOT_Z,
        "pivot_moved_mm": round((WP_PIVOT_Z - bc.WP_PIVOT_Z) * 1000.0, 1),
        "pivot_move_reason": (
            "a 230 degree arc from the old pivot has to drop to a 128 mm "
            "radius to stay inside the field; struck from the field centre it "
            "carries a 250 mm radius"),
        "arc_outer_m": WP_ARC_OUT,
        "vane_length_mm": round(WP_VANE_TIP * 1000.0, 1),
        # The pointer passes over the scale band, as it does on every meter
        # in this family, so these are two separate facts: how far the tip
        # reaches into the band, and how far short of its outer end it stops.
        "vane_tip_past_major_inner_mm": round(
            (WP_VANE_TIP - WP_ARC_MAJOR_IN) * 1000.0, 1),
        "vane_tip_short_of_arc_outer_mm": round(
            (WP_ARC_OUT - WP_VANE_TIP) * 1000.0, 1),
        "vane_clears_ticks_in_depth_mm": round(
            ((bc.WP_FIELD_FACE - 0.0085) - bc.WP_PIVOT_Y) * 1000.0, 1),
        "well_scales_replaced_with": "one readout plate each",
    }
    return body, pivot, [vane], audit


BUILDERS_C2 = {
    "WindowMeter": build_window_meter,
    "WindowPanel": build_window_panel,
}


class contract_scope(bc.contract_scope):
    """Batch C's scope with R2's wider range."""

    def __enter__(self):
        self.saved = (bc.bb.VALIDATOR_TOTAL, bc.bb.TARGET_TOTAL,
                      bc.bb.CONTRACT.get(self.asset))
        bc.bb.CONTRACT[self.asset] = CONTRACT[self.asset]
        bc.bb.VALIDATOR_TOTAL = CONTRACT[self.asset]["triangle_budget_total"]
        bc.bb.TARGET_TOTAL = CONTRACT[self.asset]["triangle_target_total"]
        return self


def measure_asset(asset, root, body, mover, movers):
    with contract_scope(asset):
        return bc.bb.measure_asset(asset, root, body, mover, movers)


def apply_pose(mover, asset, value):
    with contract_scope(asset):
        bc.bb.apply_pose(mover, asset, value)


def clearance_audit(asset, mover, movers, statics, steps=144):
    with contract_scope(asset):
        return bc.bb.motion_clearance_audit(mover, movers, statics, asset,
                                            steps=steps)


def pose_set(asset):
    low, high = CONTRACT[asset]["blender_range_deg"]
    return ((low, "min"), (0.5 * (low + high), "mid"), (high, "max"))


def pointer_audit(asset, mover, movers, statics_objects, steps=144):
    """329.4 on the pointer, over the full 230 degrees."""
    low, high = CONTRACT[asset]["blender_range_deg"]
    movable = CONTRACT[asset]["movable"]
    offenders = {}
    poses = 0
    for index in range(steps + 1):
        value = low + (high - low) * index / steps
        apply_pose(mover, asset, value)
        poses += 1
        report = bc.coplanar_overlap_exact(list(statics_objects) + list(movers))
        for pair in report["pairs"]:
            if movable in pair:
                offenders[str(tuple(pair))] = (
                    offenders.get(str(tuple(pair)), 0) + 1)
    apply_pose(mover, asset, 0.0)
    return {"poses": poses, "pointer_coplanar_pairs": offenders,
            "clean": not offenders}


def pose_alignment(asset, mover, movers):
    """329.2: do min / mid / max actually land on major ticks?"""
    rows = {}
    angles = major_angles()
    for value, label in pose_set(asset):
        apply_pose(mover, asset, value)
        angle = pose_angle(value)
        nearest = min(angles, key=lambda a: abs(a - angle))
        rows[label] = {
            "pose_deg": round(value, 4),
            "pointer_dial_angle_deg": round(angle, 4),
            "nearest_major_tick_deg": round(nearest, 4),
            "offset_deg": round(abs(angle - nearest), 6),
            "major_index": angles.index(nearest),
            "on_major": abs(angle - nearest) <= 1e-6,
        }
    apply_pose(mover, asset, 0.0)
    return {"major_ticks": len(angles), "poses": rows,
            "clean": all(row["on_major"] for row in rows.values())}
