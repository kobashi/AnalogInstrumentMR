"""Theme 4 P4 geometry: the three Quest Gate C failures, fixed at the source.

Alignment 290. P3 failed on Quest for three separate reasons and each one is
addressed here without touching P1, P2 or P3, which stay frozen as the failure
record.

MeterRound - the needle was never visible because the blade was on the wrong
side of the dial. `capsule_loft` resolves its in-plane basis to v = (0,-1,0)
for a +Z axis, so the P3 blade's `offset_v = -0.0042` displaced the section
*+Y*, which is toward the wall. Measured on the P3 blend the blade occupied
y -0.0279..-0.0237 against a dial face at -0.0280: its front-most point was
0.1 mm behind the dial, and the dial disc (radius 51 mm) covers the whole
blade sweep (tip radius 45.5 mm). Only the boss stood proud, which is why a
cyan-pixel gate passed with a blade that drew nothing. P4 rebuilds the needle
with an explicit depth ladder measured against the dial and the bearing
collar, and the delivery pass gates it on an isolated render instead of on
total cyan.

Toggle - the hub was a closed barrel ending at |x| = 10.4 mm with the bearing
bosses starting at |x| = 14 mm, so the knob floated with a 3.6 mm air gap and
no axle. P4 puts a real through axle on the moving assembly, narrows the hub
to expose it, adds rotating retaining collars, and replaces the solid bearing
caps with bored rings so the axle is seen entering and emerging.

Lever - the mesh knurl is withdrawn in full: no bump field, no non-uniform row
spacing, no flat-shaded band, no 0.9 mm silhouette displacement. The grip goes
back to a plain smooth loft and the diamond pattern moves to a tangent-space
normal map in the P4 delivery pass.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_machined_ergonomics_p4.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_machined_ergonomics_p3 as p3

THEME = "MachinedErgonomics"
TREE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p4"
OUTPUT = f"{TREE}/geometry/theme4_machined_ergonomics_p4.json"
NEUTRAL = p3.NEUTRAL

# ---------------------------------------------------------------------------
# MeterRound: the needle, rebuilt against a measured depth ladder
# ---------------------------------------------------------------------------

# Every one of these is a world Y, and front is -Y, so "more negative" means
# "closer to the viewer". The ladder is written out rather than expressed as
# an offset from the pivot because an offset with the wrong sign is exactly
# the defect being fixed.
DIAL_FACE = p3.DIAL_FACE                       # -0.0280 dial plate surface
COLLAR_FRONT = p3.LAND_FRONT - 0.0038          # -0.0329 static bearing face
NEEDLE_BLADE_CENTRE = -0.0362                  # blade section centre
NEEDLE_BOSS_BACK = -0.0335                     # 0.6 mm proud of the collar
NEEDLE_BOSS_FRONT = -0.0408
NEEDLE_TIP_R = 0.0455


def build_needle(pivot_y):
    """Blade in front of the dial, boss in front of the bearing collar."""
    local = NEEDLE_BLADE_CENTRE - pivot_y      # negative: toward the viewer
    # capsule_loft's v for a +Z axis is (0,-1,0), so the offset it wants in
    # order to move the section to `local` is -local.
    offset = -local
    blade = p3.capsule_loft(
        "needle_blade", (0.0, 0.0, -0.0075), (0.0, 0.0, NEEDLE_TIP_R),
        lambda s: 0.0031 * p3.rounded(s, 3.4) * (1.0 - 0.45 * s) + 0.0004,
        lambda s: 0.0021 * p3.rounded(s, 3.0) * (1.0 - 0.30 * s) + 0.0003,
        offset_v=lambda s: offset,
        rows=18, segments=14)
    b0 = NEEDLE_BOSS_BACK - pivot_y
    b1 = NEEDLE_BOSS_FRONT - pivot_y
    boss = p3.lathe("needle_boss", [
        (0.0000, b0),
        (0.0072, b0),
        (0.0076, b0 + (b1 - b0) * 0.34),
        (0.0068, b0 + (b1 - b0) * 0.72),
        (0.0040, b0 + (b1 - b0) * 0.92),
        (0.0000, b1),
    ], segments=24, axis="y", smooth=False)
    needle = p1.join(blade, [boss])
    needle.name = "needle"
    needle.data.name = "needle"
    return needle


def needle_depth_audit(body, pivot, needle):
    """Where the blade sits relative to everything that could hide it."""
    rows = {}
    original = tuple(pivot.rotation_euler)
    for deg in (-115.0, 0.0, 115.0):
        pivot.rotation_euler = (0.0, math.radians(deg), 0.0)
        bpy.context.view_layer.update()
        matrix = needle.matrix_world
        blade = [matrix @ v.co for v in needle.data.vertices
                 if (v.co.x ** 2 + v.co.z ** 2) ** 0.5 > 0.012]
        ys = [w.y for w in blade]
        radii = [(w.x ** 2 + w.z ** 2) ** 0.5 for w in blade]
        rows[f"{deg:+.0f}"] = {
            "blade_vertices": len(blade),
            "blade_y_m": [min(ys), max(ys)],
            "in_front_of_dial": max(ys) < DIAL_FACE - 1e-6,
            "gap_to_dial_mm": round((DIAL_FACE - max(ys)) * 1000.0, 3),
            "gap_to_collar_face_mm": round((COLLAR_FRONT - max(ys)) * 1000.0, 3),
            "tip_radius_m": round(max(radii), 5),
        }
    pivot.rotation_euler = original
    bpy.context.view_layer.update()
    body_front = min(v.co.y for v in body.data.vertices)
    return {
        "dial_face_m": DIAL_FACE,
        "collar_front_m": COLLAR_FRONT,
        "body_front_m": round(body_front, 5),
        "p3_defect": {
            "p3_blade_y_m": [-0.0279, -0.0237],
            "p3_front_most_vs_dial_mm": 0.1,
            "cause": ("offset_v sign: capsule_loft v is (0,-1,0) for a +Z "
                      "axis, so P3's -0.0042 pushed the blade +Y, behind the "
                      "dial plate"),
        },
        "poses": rows,
        "blade_in_front_of_dial_all_poses": all(
            row["in_front_of_dial"] for row in rows.values()),
    }


def build_meter_round(material):
    """P3's validated housing, with only the needle rebuilt."""
    body, pivot, old_needle, audit = p3.build_meter_round(material)
    mesh = old_needle.data
    bpy.data.objects.remove(old_needle, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
    needle = build_needle(p3.PIVOTS["MeterRound"][1][1])
    p1.assign(needle, material)
    needle.parent = pivot
    bpy.context.view_layer.update()
    audit["needle_depth"] = needle_depth_audit(body, pivot, needle)
    return body, pivot, needle, audit


# ---------------------------------------------------------------------------
# Lever: the mesh knurl withdrawn, nothing else changed
# ---------------------------------------------------------------------------

LEVER_GRIP_ROWS = 26


def _plain_stops():
    """The cosine row spacing capsule_loft uses when nothing asks otherwise."""
    return [0.5 - 0.5 * math.cos(math.pi * i / LEVER_GRIP_ROWS)
            for i in range(LEVER_GRIP_ROWS + 1)]


def build_lever(material):
    """P3's lever with the knurl machinery neutralised at the source.

    The three things that made the P3 grip a mesh knurl are the bump field,
    the row concentration and the flat-shaded band. Each is replaced with its
    no-op for the duration of the build, so the grip comes out as the plain
    smooth loft it was before P3 added the pattern, and the slot measurement
    that P3 got right is reused untouched rather than re-derived.
    """
    saved = (p3.knurl_field, p3.knurl_stops, p3.flat_shade_band)
    p3.knurl_field = lambda s, phi: 0.0
    p3.knurl_stops = _plain_stops
    p3.flat_shade_band = lambda obj, start, end, s0, s1: 0
    try:
        body, pivot, handle, audit = p3.build_lever(material)
    finally:
        p3.knurl_field, p3.knurl_stops, p3.flat_shade_band = saved
    # Only the grip band is in scope. The hub, yoke, collar and roller are
    # lathed parts P2 and P3 both emit with smooth=False on purpose, and
    # counting those as "knurl faces" would fail a gate that is about the
    # grip. Faces are selected by their position along the arm axis, which
    # is the same parameter the withdrawn band was defined on.
    flat_band, band_faces = 0, 0
    a, b = p3.LEVER_ARM_A, p3.LEVER_ARM_B
    axis = tuple(b[i] - a[i] for i in range(3))
    length2 = sum(c * c for c in axis)
    for poly in handle.data.polygons:
        c = poly.center
        s = sum((c[i] - a[i]) * axis[i] for i in range(3)) / length2
        if p3.KNURL_S0 <= s <= p3.KNURL_S1:
            band_faces += 1
            if not poly.use_smooth:
                flat_band += 1
    audit["knurl"] = {
        "mesh_knurl": "withdrawn",
        "bump_field": None,
        "silhouette_displacement_m": 0.0,
        "flat_shaded_faces": flat_band,
        "faces_in_former_knurl_band": band_faces,
        "flat_shaded_faces_elsewhere_on_handle": sum(
            1 for poly in handle.data.polygons if not poly.use_smooth) - flat_band,
        "flat_elsewhere_note": ("lathed hub / yoke / collar / roller, "
                                "flat-shaded in P2 and P3 alike; unrelated "
                                "to the knurl"),
        "grip_rows": LEVER_GRIP_ROWS,
        "loft_segments": 40,
        "p3_withdrawn": {"amplitude_m": 0.0009, "flat_shaded_faces": 2240,
                         "diamonds_around": 10, "rows_along": 8},
        "pattern_moves_to": "P4 Normal atlas, Lever grip UV patch only",
    }
    return body, pivot, handle, audit


# ---------------------------------------------------------------------------
# Toggle: a real through axle between two bored bearings
# ---------------------------------------------------------------------------

AXLE_R = 0.0064          # rotating shaft
BORE_R = 0.0072          # static bearing bore
AXLE_HALF = 0.0365       # shaft nose; 2.3 mm of full-diameter shaft
                         # stands proud of the cap face at 0.0325, so
                         # what emerges is a shaft and not just a dome
HUB_HALF = 0.0078        # narrowed from P3's 0.0104 to expose the shaft
COLLAR_X = 0.0147        # rotating retaining collar centre
COLLAR_R = 0.0084
BOSS_X0, BOSS_X1 = 0.0180, 0.0290     # static bearing housing
CAP_X = 0.0265
CAP_HALF = 0.0060


def build_toggle(material):
    """P3's toggle housing with the missing axle supplied.

    P3 had `switch_hub` ending at |x| 10.4 mm and the bearing bosses starting
    at 14 mm, with nothing in between and no shaft anywhere: on Quest the knob
    reads as floating. Here the moving assembly is hub -> shaft -> retaining
    collar -> shaft, running through a bored bearing cap that the shaft ends
    1.0 mm proud of. The shaft is coaxial with switch_pivot, so the clearance
    to the bore is the same 0.8 mm at every angle of the throw.
    """
    width, height, depth = p3.ENVELOPE_P3["Toggle"]
    EMBED = p3.EMBED
    parts = []
    plate_y = -0.013
    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.009, height - 0.009)), 0.0014))
    shell_y = -0.040
    parts.append(p1.chamfer(p1.frustum_box(
        "shell", plate_y - p1.SHUT_LINE, shell_y,
        (width - 0.014, height - 0.018),
        (width - 0.034, height - 0.042)), 0.0016))
    parts.append(p1.frustum_box("gasket", plate_y + 0.0013,
                                plate_y - p1.SHUT_LINE - 0.0003,
                                (width - 0.021, height - 0.025),
                                (width - 0.021, height - 0.025)))

    # Bearing housings, shortened along X so the shaft is seen for 10.2 mm
    # either side of the hub instead of disappearing straight into a boss.
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"boss_{int(sign)}", shell_y + 0.004, shell_y - 0.008,
            (BOSS_X1 - BOSS_X0, 0.026), (BOSS_X1 - BOSS_X0 - 0.002, 0.022),
            centre=(sign * (BOSS_X0 + BOSS_X1) / 2.0, 0.0)), 0.0009))
        # A bored ring, not a solid lens: the bore is what lets the shaft be
        # seen entering the bearing and emerging from it.
        cap = p3.lathe(f"boss_cap_{int(sign)}", [
            (BORE_R, CAP_HALF),
            (0.0086, CAP_HALF),
            (0.0100, CAP_HALF - 0.0020),
            (0.0100, -(CAP_HALF - 0.0020)),
            (0.0086, -CAP_HALF),
            (BORE_R, -CAP_HALF),
        ], segments=20, axis="x", centre=(shell_y - 0.002, 0.0), smooth=False)
        cap.location = (sign * CAP_X, 0.0, 0.0)
        parts.append(cap)

    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"stop_{int(sign)}", shell_y + 0.002, shell_y - 0.011,
            (0.007, 0.026), (0.006, 0.023),
            centre=(sign * 0.017, 0.013)), 0.0008))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.011), sz * (height / 2.0 - 0.011)),
                plate_y - 0.0006, 0.0052, 0.0040))
    parts.append(p1.access_cap("access", (-0.034, 0.050), shell_y + EMBED,
                               0.0105, 0.0089, 0.0040))
    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0026, 0.010))
    parts.append(p1.nameplate("plate_label", (0.0, -0.052), (0.062, 0.016),
                              shell_y + EMBED, 0.0016))
    for sign in (-1.0, 1.0):
        parts.append(p1.rib(f"rib_{int(sign)}", (sign * 0.040, 0.010),
                            (0.0055, 0.052), shell_y + EMBED, 0.0022))
    parts.append(p1.mount_hole("mount_a", (0.034, 0.050),
                               plate_y - 0.0004, 0.0072, 0.0040, 0.0026))
    parts.append(p1.blanking_plug("blank_a", (0.0, 0.062), plate_y - 0.0006,
                                  0.0068, 0.0032))

    audit = p3.coplanar_overlap_audit(parts)
    body = p1.join(parts[0], parts[1:])
    body.name = "Toggle_body"
    body.data.name = "Toggle_body"
    p1.assign(body, material)

    pivot = bpy.data.objects.new("switch_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = p3.PIVOTS["Toggle"][1]
    pivot.rotation_mode = "XYZ"

    hub = p3.lathe("switch_hub", [
        (0.0000, HUB_HALF),
        (0.0070, HUB_HALF - 0.0006),
        (0.0100, 0.0000),
        (0.0070, -(HUB_HALF - 0.0006)),
        (0.0000, -HUB_HALF),
    ], segments=24, axis="x", centre=(0.0, 0.0), smooth=False)
    axle = p3.lathe("switch_axle", [
        (0.0000, AXLE_HALF),
        (0.0042, AXLE_HALF - 0.0005),
        (AXLE_R, AXLE_HALF - 0.0017),
        (AXLE_R, -(AXLE_HALF - 0.0017)),
        (0.0042, -(AXLE_HALF - 0.0005)),
        (0.0000, -AXLE_HALF),
    ], segments=20, axis="x", centre=(0.0, 0.0), smooth=False)
    collars = []
    for sign in (-1.0, 1.0):
        collar = p3.lathe(f"switch_collar_{int(sign)}", [
            (0.0000, 0.0022),
            (0.0072, 0.0022),
            (COLLAR_R, 0.0012),
            (COLLAR_R, -0.0012),
            (0.0072, -0.0022),
            (0.0000, -0.0022),
        ], segments=20, axis="x", centre=(0.0, 0.0), smooth=False)
        collar.location = (sign * COLLAR_X, 0.0, 0.0)
        collars.append(collar)
    head = p3.lathe("switch_head", [
        (0.0000, 0.0020),
        (0.0074, 0.0034),
        (0.0064, 0.0130),
        (0.0059, 0.0270),
        (0.0058, 0.0392),
        (0.0072, 0.0472),
        (0.0104, 0.0548),
        (0.0126, 0.0626),
        (0.0132, 0.0684),
        (0.0124, 0.0730),
        (0.0100, 0.0764),
        (0.0064, 0.0782),
        (0.0032, 0.0778),
        (0.0000, 0.0770),
    ], segments=28, axis="z", centre=(0.0, -0.0060), smooth=True)

    moving = [hub, axle] + collars + [head]
    axle_audit = axle_continuity_audit(moving)
    switch = p1.join(moving[0], moving[1:])
    switch.name = "switch"
    switch.data.name = "switch"
    p1.assign(switch, material)
    switch.parent = pivot
    audit["axle"] = axle_audit
    return body, pivot, switch, audit


def axle_continuity_audit(moving_parts):
    """Prove the moving assembly is axially continuous, and clear of the bore.

    "The knob has no axle" is a continuity claim, so it is answered with a
    continuity measurement: the X intervals every rotating part occupies are
    merged, and the merged run has to reach from the hub centre out past the
    bearing without a break. Radial clearance is a separate number because a
    shaft that touches its bore is a z-fighting seam, not a bearing.
    """
    spans = {}
    for obj in moving_parts:
        xs = [v.co.x for v in obj.data.vertices]
        spans[obj.name.split(".")[0]] = [round(min(xs), 5), round(max(xs), 5)]
    ordered = sorted(spans.values())
    merged = [list(ordered[0])]
    gaps = []
    for lo, hi in ordered[1:]:
        if lo <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            gaps.append(round((lo - merged[-1][1]) * 1000.0, 3))
            merged.append([lo, hi])
    return {
        "part_x_spans_m": spans,
        "merged_x_runs_m": [[round(a, 5), round(b, 5)] for a, b in merged],
        "axial_gaps_mm": gaps,
        "axially_continuous": not gaps,
        "axle_radius_m": AXLE_R,
        "bearing_bore_radius_m": BORE_R,
        "radial_clearance_mm": round((BORE_R - AXLE_R) * 1000.0, 3),
        "bearing_cap_x_m": [round(CAP_X - CAP_HALF, 5),
                            round(CAP_X + CAP_HALF, 5)],
        "shaft_proud_of_cap_mm": round(
            (AXLE_HALF - (CAP_X + CAP_HALF)) * 1000.0, 3),
        "hub_half_x_m": HUB_HALF,
        "p3_defect": {"hub_half_x_m": 0.0104, "boss_inner_x_m": 0.0140,
                      "air_gap_mm": 3.6, "through_axle": False},
    }


BUILDERS_P4 = {
    "MeterRound": build_meter_round,
    "Lever": build_lever,
    "Toggle": build_toggle,
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    geometry_dir = tree / "geometry"
    grey_dir = tree / "review_grayscale"
    detail_dir = tree / "detail"
    for folder in (geometry_dir, grey_dir, detail_dir):
        folder.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "Theme4-P4-geometry",
        "note": ("Quest Gate C fixes: meter needle moved in front of the dial, "
                 "toggle given a through axle in bored bearings, lever mesh "
                 "knurl withdrawn. P1/P2/P3 scripts and their delivery trees "
                 "are untouched."),
        "fixes": {
            "MeterRound": "needle blade was behind the dial plate (offset_v sign)",
            "Toggle": "no through axle between hub and bearing bosses",
            "Lever": "mesh knurl withdrawn; pattern moves to the normal map",
        },
        "envelope_p4": {k: list(v) for k, v in p3.ENVELOPE_P3.items()},
        "assets": {},
    }

    import opus5_brushup_kinetic_review as review
    for asset, builder in BUILDERS_P4.items():
        p1.clear_scene()
        review.configure_scene()
        material = p1.proto.make_material(f"MAT_{THEME}_P4_Neutral", NEUTRAL)
        root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
        bpy.context.collection.objects.link(root)
        body, pivot, part, audit = builder(material)
        for obj in (body, pivot):
            obj.parent = root
        bpy.context.view_layer.update()

        scan = p1.sweep_scan(pivot, body, part, p1.MOTION[asset])
        row = p1.measure(asset, root, body, pivot, part, scan)
        row["pose_bounds"] = p1.pose_bounds(pivot, body, part,
                                            p1.MOTION[asset], scan)
        row["coplanar_overlap"] = audit
        blend = geometry_dir / f"BL_{asset}_{THEME}_V6_Opus5_P4.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        row["blend"] = str(blend.relative_to(project_root))
        row["blend_sha256"] = m1.digest(blend)

        focus, radius, scale = p1.rig_for([body, part])
        images = {}
        for label, view in p1.VIEWS.items():
            path = grey_dir / f"Grey_{asset}_{THEME}_P4_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        row["grayscale_images"] = images

        details = {}
        if asset == "MeterRound":
            # The needle at both ends of the throw and at rest, from the
            # front, in grey: the delivery pass repeats this with the real
            # material and adds the isolated mask that actually gates it.
            for deg in (-115.0, 0.0, 115.0):
                pivot.rotation_euler = (0.0, math.radians(deg), 0.0)
                bpy.context.view_layer.update()
                name = f"Detail_{asset}_needle_{int(deg):+d}.png"
                p1.shot(focus, radius, (0.0, 0.0), 52.0, scale,
                        detail_dir / name)
                details[f"needle_{int(deg):+d}"] = str(
                    (detail_dir / name).relative_to(project_root))
            pivot.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            p1.shot((0.020, DIAL_FACE - 0.008, 0.020), 0.086, (30.0, 22.0),
                    72.0, 0.043, detail_dir / f"Detail_{asset}_needle_depth.png")
            details["needle_depth"] = str(
                (detail_dir / f"Detail_{asset}_needle_depth.png")
                .relative_to(project_root))
        if asset == "Toggle":
            axis_y = p3.PIVOTS["Toggle"][1][1]
            p1.shot((0.0, axis_y - 0.004, 0.0), 0.115, (16.0, 14.0), 74.0,
                    0.057, detail_dir / f"Detail_{asset}_axle.png")
            details["axle"] = str((detail_dir / f"Detail_{asset}_axle.png")
                                  .relative_to(project_root))
            # Outboard and above, far enough back that the camera is not
            # inside the bearing's own shadow: the point of this frame is the
            # bore with the shaft end standing proud of it.
            p1.shot((CAP_X - 0.004, axis_y - 0.003, 0.001), 0.105,
                    (62.0, 26.0), 70.0, 0.052,
                    detail_dir / f"Detail_{asset}_bearing.png")
            details["bearing"] = str(
                (detail_dir / f"Detail_{asset}_bearing.png")
                .relative_to(project_root))
            for deg in p1.MOTION["Toggle"]["audit_deg_blender"]:
                pivot.rotation_euler = (math.radians(deg), 0.0, 0.0)
                bpy.context.view_layer.update()
                name = f"Detail_{asset}_axle_{int(deg):+d}.png"
                p1.shot((0.0, axis_y - 0.004, 0.0), 0.115, (16.0, 14.0), 74.0,
                        0.057, detail_dir / name)
                details[f"axle_{int(deg):+d}"] = str(
                    (detail_dir / name).relative_to(project_root))
            pivot.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
        if asset == "Lever":
            grip = (0.0, p3.PIVOTS["Lever"][1][1] - 0.076,
                    p3.PIVOTS["Lever"][1][2] + 0.208)
            p1.shot(grip, 0.150, (34.0, 12.0), 62.0, 0.072,
                    detail_dir / f"Detail_{asset}_grip_smooth.png")
            details["grip_smooth"] = str(
                (detail_dir / f"Detail_{asset}_grip_smooth.png")
                .relative_to(project_root))
        row["detail_images"] = details
        row["all_gates_passed"] = all(row["gates"].values())
        payload["assets"][asset] = row
        print(f"[Theme4P4] {asset}: tris {row['triangles_total']}, "
              f"coplanar pairs {audit['pair_count']}, "
              f"gates {row['all_gates_passed']}")

    payload["coplanar_overlap_pairs_total"] = sum(
        row["coplanar_overlap"]["pair_count"]
        for row in payload["assets"].values())
    payload["tick_plane_audit"] = \
        payload["assets"]["MeterRound"]["coplanar_overlap"]["tick_planes"]
    payload["needle_depth_audit"] = \
        payload["assets"]["MeterRound"]["coplanar_overlap"]["needle_depth"]
    payload["axle_audit"] = \
        payload["assets"]["Toggle"]["coplanar_overlap"]["axle"]
    payload["lever_knurl"] = \
        payload["assets"]["Lever"]["coplanar_overlap"]["knurl"]
    payload["status"] = (
        "p4_geometry_ready"
        if all(row["all_gates_passed"] for row in payload["assets"].values())
        and payload["needle_depth_audit"]["blade_in_front_of_dial_all_poses"]
        and payload["axle_audit"]["axially_continuous"]
        and payload["lever_knurl"]["flat_shaded_faces"] == 0
        and payload["lever_knurl"]["silhouette_displacement_m"] == 0.0
        else "p4_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Theme4P4] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
