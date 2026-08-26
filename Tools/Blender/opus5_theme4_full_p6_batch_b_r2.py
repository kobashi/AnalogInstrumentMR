"""Theme 4 Phase 3 Batch B R2: the status bar keeps its widths *and* its place.

312.2 accepted R1's frame position and rejected the way it got there. R1 made
the three wells one size to buy a symmetric group; 312.4 points out those are
not the same requirement - the group's outline can sit centred on the base
while the three lamps inside it stay three different widths, because nothing
says the internal spacing has to be symmetric too.

So R2 restores Batch B's half widths - 0.0170 / 0.0200 / 0.0230 - and solves
for the centres instead. The three wells are laid end to end with one equal
gap between them, and the run is centred on the base:

    SAFE   outer -0.0804 .. -0.0396   centre -0.0600   half width 0.0170
    WARN   outer -0.0294 .. +0.0174   centre -0.0060   half width 0.0200
    DANGER outer +0.0276 .. +0.0804   centre +0.0540   half width 0.0230

Equal 10.2 mm gaps, so both ribs keep their full 6.2 mm thickness; the group
runs +/-0.0804 against a shell front face of +/-0.0819, which is 1.47 mm of
margin on each side and no overhang at all. The internal centre spacing is
54.0 mm on the left and 60.0 mm on the right - asymmetric, which 312.5 allows
explicitly, and which is the price of keeping the width coding.

Rotary, Button and Lamp are not built here. They are R1's, frozen, and the
delivery script proves that by digest rather than by rebuilding them.
"""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3
import opus5_theme4_full_p6_batch_b as bb
import opus5_theme4_full_p6_batch_b_r1 as r1

SHUT = bb.SHUT
EMBED = bb.EMBED
CONTRACT = bb.CONTRACT

# Batch B's three half widths, back where they were. Only the centres move.
STATUS_HALF_WIDTHS = tuple(row[2] for row in bb.STATUS_SEGMENTS)
STATUS_WELL_MARGIN = bb.STATUS_WELL_MARGIN
STATUS_GROUP_HALF = 0.0804        # shell front face is +/-0.0819
STATUS_HOOD_WIDTH = 2.0 * STATUS_GROUP_HALF


def _solve_centres():
    """Lay the three wells end to end with one equal gap, centred on zero."""
    outer = [2.0 * (hw + STATUS_WELL_MARGIN) for hw in STATUS_HALF_WIDTHS]
    gap = (2.0 * STATUS_GROUP_HALF - sum(outer)) / (len(outer) - 1)
    centres, cursor = [], -STATUS_GROUP_HALF
    for width in outer:
        centres.append(round(cursor + width / 2.0, 6))
        cursor += width + gap
    return centres, gap


STATUS_CENTRES, STATUS_GAP = _solve_centres()
STATUS_SEGMENTS = tuple(
    (row[0], centre, row[2], row[3], row[4])
    for row, centre in zip(bb.STATUS_SEGMENTS, STATUS_CENTRES))


def build_status(material):
    """Batch B's status bar: its widths, R1's placement, R2's centres.

    Everything outside the well / rib / hood group is Batch B's - plate,
    gasket, shell, nameplate, screws, register, the `indicator` empty, the
    SAFE / WARN / DANGER order and the four renderers.
    """
    width, depth_env, height = bb.envelope_blender("StatusIndicator")
    plate_y = -0.0130
    face_y = -0.0380
    parts = []

    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.010, height - 0.009)), 0.0014))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.024, height - 0.022),
                                (width - 0.024, height - 0.022)))
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - SHUT, face_y, (width - 0.006, height - 0.014),
        (width - 0.018, height - 0.026)), 0.0016))

    edges = []
    for name, cx, hw, hh, _ in STATUS_SEGMENTS:
        outer_w = 2.0 * (hw + STATUS_WELL_MARGIN)
        outer_h = 2.0 * (hh + STATUS_WELL_MARGIN)
        parts.append(p1.chamfer(p1.rect_frame(
            f"well_{name.split('_')[1]}", face_y + EMBED, face_y - 0.0034,
            (outer_w, outer_h),
            (2.0 * hw + 0.0052, 2.0 * hh + 0.0052),
            centre=(cx, 0.0)), 0.0010))
        edges.append((cx - outer_w / 2.0, cx + outer_w / 2.0))
    for index in range(len(edges) - 1):
        gap_lo, gap_hi = edges[index][1], edges[index + 1][0]
        centre = 0.5 * (gap_lo + gap_hi)
        thickness = min(0.0062, (gap_hi - gap_lo) - 0.0040)
        parts.append(p1.chamfer(p1.frustum_box(
            f"rib_{index}", face_y + EMBED, face_y - 0.0086,
            (thickness, 2.0 * 0.0165 + 0.0128),
            (thickness - 0.0012, 2.0 * 0.0165 + 0.0102),
            centre=(centre, 0.0)), 0.0012))
    parts.append(p1.chamfer(p1.frustum_box(
        "hood", face_y - 0.0030, face_y - 0.0104,
        (STATUS_HOOD_WIDTH, 0.0088), (STATUS_HOOD_WIDTH - 0.008, 0.0070),
        centre=(0.0, 0.0170 + 0.0102)), 0.0012))

    parts.append(p1.nameplate("plate_label", (0.0, -(height / 2.0 - 0.0125)),
                              (0.0520, 0.0106), plate_y - 0.0019, 0.0013))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.0115), sz * (height / 2.0 - 0.0115)),
                plate_y - 0.0015, 0.0052, 0.0038))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0026, 0.0100))

    audit = p3.coplanar_overlap_audit(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = "StatusIndicator_body"
    body.data.name = "StatusIndicator_body"
    p1.assign(body, material)

    indicator = bpy.data.objects.new("indicator", None)
    bpy.context.collection.objects.link(indicator)
    indicator.location = (0.0, 0.0, 0.0)
    indicator.rotation_mode = "XYZ"

    lenses = []
    for name, cx, hw, hh, _ in STATUS_SEGMENTS:
        lens = p1.chamfer(p1.frustum_box(
            name, face_y - 0.0006, face_y - 0.0074,
            (2.0 * hw, 2.0 * hh), (2.0 * hw - 0.0068, 2.0 * hh - 0.0068),
            centre=(cx, 0.0)), 0.0022)
        lens.name = name
        lens.data.name = name
        p1.assign(lens, material)
        lens.parent = indicator
        lenses.append(lens)

    group_lo = min(e[0] for e in edges)
    group_hi = max(e[1] for e in edges)
    audit["mechanism"] = {
        "indicator_is_empty_at_origin": True,
        "segment_meshes": [row[0] for row in STATUS_SEGMENTS],
        "segment_centres_m": [row[1] for row in STATUS_SEGMENTS],
        "segment_centres_batch_b_m": [row[1] for row in bb.STATUS_SEGMENTS],
        "segment_centres_r1_m": [row[1] for row in r1.STATUS_SEGMENTS],
        "segment_half_widths_m": list(STATUS_HALF_WIDTHS),
        "segment_half_widths_batch_b_m": [row[2] for row in bb.STATUS_SEGMENTS],
        "segment_half_widths_r1_m": [row[2] for row in r1.STATUS_SEGMENTS],
        "widths_restored_from_batch_b": (
            list(STATUS_HALF_WIDTHS) == [row[2] for row in bb.STATUS_SEGMENTS]),
        "distinct_widths": len(set(STATUS_HALF_WIDTHS)) == 3,
        "well_gap_m": round(STATUS_GAP, 6),
        "internal_centre_spacing_mm": [
            round((STATUS_CENTRES[1] - STATUS_CENTRES[0]) * 1000.0, 2),
            round((STATUS_CENTRES[2] - STATUS_CENTRES[1]) * 1000.0, 2)],
        "well_group_x_m": [round(group_lo, 4), round(group_hi, 4)],
        "well_group_centre_mm": round(
            0.5 * (group_lo + group_hi) * 1000.0, 3),
        "hood_width_m": STATUS_HOOD_WIDTH,
        "hood_width_batch_b_m": round(0.185 - 0.030, 4),
        "hood_matches_group": True,
        "wells": 3, "ribs": len(STATUS_SEGMENTS) - 1, "hood": True,
        "states": CONTRACT["StatusIndicator"]["states"],
        "renderers": 1 + len(STATUS_SEGMENTS),
        "readability": (
            "three widths and three positions, as Batch B had, inside a frame "
            "group centred on the base as R1 had. The internal centre spacing "
            "is 54.0 mm left and 60.0 mm right, which is what paying for both "
            "at once costs and what 312.5 permits."),
    }
    return body, indicator, lenses, audit


BUILDERS_B2 = {"StatusIndicator": build_status}
