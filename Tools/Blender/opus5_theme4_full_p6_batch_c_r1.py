"""Theme 4 Phase 3 Batch C R1: one screw, and the gate that hid it.

326 found two things and both are mine.

The real one: WindowMeter's `screw_-1_-1` sits at (-0.5480, -0.3230) with a
12 mm seat, and the nameplate's left edge is at x -0.5398 standing 6.2 mm
proud of the shell face. The inner 4 mm of that seat is therefore lying on the
nameplate, not on the panel - the centre ray finds the face and reports a zero
gap while the ring finds a 6.2 mm step. The screw moves 12.5 mm to
(-0.5540, -0.3120), the nearest position on the same face where the whole seat
lands on one plane and the driver path is still clear; that was searched over
a 80 x 120 mm window rather than chosen.

The validator one is worse, because it is what let the first through:
`seating_audit` called `probe.update(penetration_probe(...))`, and both probes
return a key called `clean`. The penetration result therefore overwrote the
seating result, and a screw that failed seating reported clean. R1 keeps the
two answers under their own names and ANDs them, so neither can hide the
other.

Nothing else moves. WindowPanel and TrendMonitor are not rebuilt for export at
all - their Batch C digests are re-measured and recorded - and WindowMeter's
UV is copied back off the Batch C FBX rather than left to whatever
pack_into_regions does to a mesh that has just had a screw move.
"""

import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_full_p6_batch_c as bc
import opus5_theme4_fastener_access_r1 as fa
import opus5_theme4_fastener_access_r4 as r4

BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
BATCH_C = f"{BASE}/batch_c"

# 326.1. Searched, not chosen: the nearest cell on the shell face whose whole
# seat lands on one plane facing the driver, with the tool path still clear.
MOVED = {("WindowMeter", "screw_-1_-1"): (-0.5540, -0.3120)}
SEAT_RADIUS = {"WindowMeter": 0.0120, "WindowPanel": 0.0130,
               "TrendMonitor": 0.0062}
SEAT_PLANE = {"WindowMeter": bc.WM_FACE_Y, "WindowPanel": bc.WP_FACE_Y,
              "TrendMonitor": None}      # trend monitor seats on the bezel
UV_REFERENCE = {
    "WindowMeter": f"{BATCH_C}/SM_WindowMeter_MachinedErgonomics_V6_Opus5_P6C.fbx",
}
CARRIED = ("WindowPanel", "TrendMonitor")


def install(asset):
    """Patch p1.fastener so only the named screw's centre changes."""
    original = p1.fastener

    def fastener(name, centre, y_face, radius, depth):
        key = (asset, name)
        if key in MOVED:
            centre = MOVED[key]
        return original(name, centre, y_face, radius, depth)

    p1.fastener = fastener
    return original


def restore(saved):
    p1.fastener = saved


# ---------------------------------------------------------------------------
# 326.2 / 326.3: the two answers kept apart
# ---------------------------------------------------------------------------

def seating_audit(parts, asset, tolerance=0.0001, normal_tolerance=0.1):
    """Seat and penetration measured separately, then ANDed.

    Batch C merged the two probe dictionaries and both carry a key called
    `clean`, so `probe.update(penetration_probe(...))` silently replaced the
    seating verdict with the penetration one. Here each keeps its own name and
    the combined verdict is built from both, so neither result can be lost by
    a dictionary key collision.
    """
    tree = r4.static_tree(parts)
    seat_r = SEAT_RADIUS[asset]
    rows = {}
    for name in sorted({fa.fastener_id(n) for n in parts
                        if fa.fastener_id(n)}):
        frame = r4.fastener_frame(parts, name)
        if frame is None:
            continue
        cx, head_front_y, cz = frame
        # p1.fastener stands the head 0.5 mm proud of the plane it is given,
        # so the seat plane is the head's front plus that.
        face_y = head_front_y + 0.0005
        seat = r4.seat_probe(tree, (cx, cz), face_y, seat_r)
        penetration = r4.penetration_probe(tree, (cx, cz), face_y, 0.0012)
        seat_clean = bool(
            seat.get("surface_hit")
            and seat.get("ray_misses", 1) == 0
            and abs(seat.get("gap_mm", 99.0)) <= tolerance * 1000.0
            and seat.get("seat_surface_spread_mm", 99.0)
            <= tolerance * 1000.0
            and seat.get("normal_off_axis_deg", 99.0) <= normal_tolerance)
        penetration_clean = bool(penetration.get("clean"))
        rows[name] = {
            "head_centre_m": [round(cx, 5), round(head_front_y, 5),
                              round(cz, 5)],
            "seat_plane_y_m": round(face_y, 5),
            "seat": {key: value for key, value in seat.items()
                     if key != "clean"},
            "penetration": {key: value for key, value in penetration.items()
                            if key != "clean"},
            "seat_clean": seat_clean,
            "penetration_clean": penetration_clean,
            "clean": seat_clean and penetration_clean,
            "moved_in_r1": (asset, name) in MOVED,
        }
    return {
        "fasteners": rows,
        "count": len(rows),
        "seat_clean": all(row["seat_clean"] for row in rows.values()),
        "penetration_clean": all(row["penetration_clean"]
                                 for row in rows.values()),
        "clean": all(row["clean"] for row in rows.values()),
        "thresholds": {"gap_mm": tolerance * 1000.0,
                       "seat_surface_spread_mm": tolerance * 1000.0,
                       "normal_off_axis_deg": normal_tolerance,
                       "penetration_mm": 0.0, "ray_misses": 0},
    }


def screw_offsets(before_parts, after_parts):
    return r4.screw_offsets(before_parts, after_parts)
