"""Batch A R1: the Throttle only, brought under the real triangle budget.

Alignment 296 / Gate B. `RefinedModelReplacementValidator.CountTriangles`
sums every MeshFilter under the prefab instance and compares the total with
`InstrumentGreyboxSpecification.GetTriangleBudget(kind)`, which returns 5,000
for `ThrottleLever`. Batch A's Throttle was 6,500 across body and handle, so
it fails that check. Target here is 4,800 total.

The reduction is density, not deletion. Measured per part, the cost was not
where a glance would put it:

    cover_panel      812   the p1 composite, panel plus four screws
    screw_*          768   four corner fasteners
    pillow_cap_*     480   two bearing caps at 20 segments
    mount_*          472
    handle_grip     1724   26 rows x 32 segments

So the cuts are: the grip loft keeps its shape with rows spent where the
finger hollow and palm swell need them instead of spread evenly; the two
bearing caps drop from 20 circumferential segments to 12; the hub, cross pin
and pin bosses drop a few segments each; and the cover panel and blanking plug
are rebuilt from simple primitives that keep the feature - a removable panel
with four screws, a plugged port - at a fraction of the composite's cost.

Everything alignment 296 asked to keep is kept: outline, grip, yoke cross pin,
both bearing bosses, slot, end stops, and the 70 degree runtime range.
MeterMedium, MeterLarge, PowerSlider, P1-P5 and the original Batch A outputs
are untouched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_a_r1.py -- \
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
import opus5_theme4_machined_ergonomics_p5 as p5
import opus5_theme4_full_p6_batch_a as ba

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/batch_a_r1")
OUTPUT = f"{TREE}/geometry/theme4_full_p6_batch_a_r1.json"
NEUTRAL = ba.NEUTRAL
TARGET_TOTAL = 4800

# Alignment 296 / Gate B. `RefinedModelReplacementValidator.CountTriangles`
# sums the whole prefab instance and compares it with
# `GetTriangleBudget(ThrottleLever)`, which is 5,000. Batch A recorded 25,000
# for this kind, and that figure is what Gate B rejected. batch_a.py is frozen
# because its other three assets are accepted, so the correction is published
# here instead of edited there, and it is applied to every number this module
# emits rather than only to the headline.
THROTTLE_BUDGET_TOTAL = 5000
CONTRACT_THROTTLE = dict(ba.CONTRACT["Throttle"],
                         triangle_budget_total=THROTTLE_BUDGET_TOTAL)


def measure_throttle(root, body, mover, moving):
    """ba.measure_asset with the prefab-total budget corrected to 5,000."""
    row = ba.measure_asset("Throttle", root, body, mover, moving)
    row["triangle_budget_total"] = THROTTLE_BUDGET_TOTAL
    row["gates"]["triangles_total"] = (
        row["triangles_total"] <= THROTTLE_BUDGET_TOTAL)
    return row


lathe = p3.lathe
loft = p3.capsule_loft
stations = p3.station_profile

# Segment counts, all reduced from Batch A. The circumference of each of these
# is small enough that the faceting is below a Quest texel at arm's length.
HUB_SEG = 18          # was 26
PIN_SEG = 14          # was 18
BOSS_SEG = 14         # was 18
CAP_SEG = 10          # was 20
GRIP_SEG = 20         # was 32


def grip_stops():
    """Rows placed where the hand feels the shape, not spread evenly.

    Batch A used 26 uniform cosine rows and spent most of them on a plain
    tapered shaft. The finger hollow at s = 0.62 has a 0.055 sigma and the
    palm swell at 0.84 has 0.18, so those are the only two places that need
    close spacing. Twenty rows placed this way resolve both better than
    twenty-six placed evenly, at 77 per cent of the triangles.
    """
    return [0.00, 0.06, 0.13, 0.21, 0.30, 0.39, 0.47, 0.54,
            0.575, 0.60, 0.62, 0.645, 0.675,
            0.72, 0.775, 0.815, 0.845, 0.885, 0.94, 0.98, 1.00]


def build_throttle(material):
    """Batch A's throttle at Batch A's dimensions, at lower density."""
    width, depth_env, height = ba.envelope_blender("Throttle")
    plate_y = -0.0180
    shell_y = -0.0440
    shell = (width - 0.020, height - 0.014)
    shell_centre_z = 0.0
    pivot_y, pivot_z = ba.THROTTLE_PIVOT[1], ba.THROTTLE_PIVOT[2]
    EMBED = ba.EMBED
    SHUT = ba.SHUT
    angles = (0.0, 70.0)
    mid = 0.5 * (angles[0] + angles[1])
    pin_local = ba._pin_local(ba.THROTTLE_PIN_RADIUS, mid)

    pivot = bpy.data.objects.new("throttle_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = ba.THROTTLE_PIVOT
    pivot.rotation_mode = "XYZ"

    hub = lathe("handle_hub", [
        (0.0000, 0.0195),
        (0.0155, 0.0184),
        (0.0170, 0.0084),
        (0.0170, -0.0084),
        (0.0155, -0.0184),
        (0.0000, -0.0195),
    ], segments=HUB_SEG, axis="x", centre=(0.0, 0.0), smooth=False)
    cheeks = []
    for sign in (-1.0, 1.0):
        cheeks.append(p1.chamfer(p1.frustum_box(
            f"handle_yoke_{int(sign)}", 0.0055, -0.0360, (0.0072, 0.0480),
            (0.0062, 0.0425), centre=(sign * 0.0150, 0.0125)), 0.0010))
    pin = lathe("handle_pin", [
        (0.0000, ba.THROTTLE_PIN_HALF_X),
        (0.0040, ba.THROTTLE_PIN_HALF_X - 0.0006),
        (ba.THROTTLE_PIN_R, ba.THROTTLE_PIN_HALF_X - 0.0019),
        (ba.THROTTLE_PIN_R, -(ba.THROTTLE_PIN_HALF_X - 0.0019)),
        (0.0040, -(ba.THROTTLE_PIN_HALF_X - 0.0006)),
        (0.0000, -ba.THROTTLE_PIN_HALF_X),
    ], segments=PIN_SEG, axis="x", centre=pin_local, smooth=False)
    bosses = []
    for sign in (-1.0, 1.0):
        boss = lathe(f"handle_pin_boss_{int(sign)}", [
            (0.0000, 0.0042),
            (0.0072, 0.0039),
            (ba.THROTTLE_BOSS_R, 0.0025),
            (ba.THROTTLE_BOSS_R, -0.0031),
            (0.0058, -0.0042),
            (0.0000, -0.0042),
        ], segments=BOSS_SEG, axis="x", centre=pin_local, smooth=False)
        boss.location = (sign * 0.0168, 0.0, 0.0)
        bosses.append(boss)

    arm_a = (0.0, -0.0040, 0.0090)
    arm_b = (0.0, -0.0640, ba.THROTTLE_ARM + 0.0180)
    arm_u = stations([(0.00, 0.0195), (0.18, 0.0150), (0.46, 0.0116),
                      (0.62, 0.0128), (0.80, 0.0186), (0.92, 0.0192),
                      (1.00, 0.0152)])
    arm_v = stations([(0.00, 0.0165), (0.18, 0.0132), (0.46, 0.0106),
                      (0.62, 0.0122), (0.80, 0.0214), (0.92, 0.0220),
                      (1.00, 0.0168)])

    def swell(s):
        finger = -0.0026 * math.exp(-(((s - 0.62) / 0.055) ** 2))
        palm = 0.0032 * math.exp(-(((s - 0.84) / 0.18) ** 2))
        return finger + palm

    grip = loft("handle_grip", arm_a, arm_b, arm_u, arm_v,
                offset_v=swell, segments=GRIP_SEG, stops=grip_stops())
    handle = p1.join(hub, cheeks + [pin] + bosses + [grip])
    handle.name = "throttle_handle"
    handle.data.name = "throttle_handle"
    p1.assign(handle, material)

    face_slab = (shell_y - ba.THROTTLE_RIM_PROUD, plate_y - SHUT)
    floor_slab = (pivot_y, pivot_y + 0.004)
    need_face = p5.swept_footprint_solid(handle, ba.THROTTLE_PIVOT,
                                         face_slab[0], face_slab[1], angles)
    need_floor = p5.swept_footprint_solid(handle, ba.THROTTLE_PIVOT,
                                          floor_slab[0], floor_slab[1], angles)
    pin_span = ba.pin_sweep_generic(ba.THROTTLE_PIVOT, pin_local, angles,
                                    ba.THROTTLE_BOSS_R)
    margin = 0.0032
    slot_lo = min(need_face["z_min"], pin_span["z"][0]) - margin
    slot_hi = max(need_face["z_max"], pin_span["z"][1]) + margin
    slot = (max(0.062, 2.0 * (need_face["x_max"] + margin)), slot_hi - slot_lo)
    slot_centre_z = 0.5 * (slot_lo + slot_hi)

    parts = []
    parts.append(p1.chamfer(p1.frustum_box(
        "plate", 0.0, plate_y, (width, height),
        (width - 0.012, height - 0.012)), 0.0016))
    parts.append(p1.frustum_box("gasket", plate_y + EMBED,
                                plate_y - SHUT - EMBED,
                                (width - 0.032, height - 0.040),
                                (width - 0.032, height - 0.040),
                                centre=(0.0, shell_centre_z)))
    parts.append(p1.chamfer(p1.rect_frame(
        "shell", plate_y - SHUT, shell_y, shell, slot,
        centre=(0.0, shell_centre_z),
        inner_centre=(0.0, slot_centre_z)), 0.0020))
    parts.append(p1.chamfer(p1.frustum_box(
        "skirt", plate_y + ba.EMBED_SKIRT, plate_y - 0.0090,
        (shell[0] + 0.014, shell[1] + 0.014),
        (shell[0] + 0.004, shell[1] + 0.004),
        centre=(0.0, shell_centre_z)), 0.0016))
    floor_lo = need_floor["z_min"] - 0.0070
    floor_hi = need_floor["z_max"] + 0.0070
    parts.append(p1.rect_frame(
        "slot_floor", pivot_y + 0.0040, pivot_y,
        (slot[0] + 0.024, slot[1] + 0.024),
        (2.0 * (need_floor["x_max"] + 0.0070), floor_hi - floor_lo),
        centre=(0.0, slot_centre_z),
        inner_centre=(0.0, 0.5 * (floor_lo + floor_hi))))

    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"pillow_{int(sign)}", pivot_y + 0.0055, pivot_y - 0.0185,
            (0.0185, 0.0370), (0.0155, 0.0315),
            centre=(sign * 0.0330, pivot_z)), 0.0011))
        cap = lathe(f"pillow_cap_{int(sign)}", [
            (0.0068, 0.0058),
            (0.0092, 0.0058),
            (0.0104, 0.0038),
            (0.0104, -0.0038),
            (0.0092, -0.0058),
            (0.0068, -0.0058),
        ], segments=CAP_SEG, axis="x",
            centre=(pivot_y - 0.0035, pivot_z), smooth=False)
        cap.location = (sign * 0.0330, 0.0, 0.0)
        parts.append(cap)

    for name, cx, sx, cz, sz in (
        ("rim_left", -(slot[0] / 2.0 + 0.0042), 0.0084, slot_centre_z,
         slot[1] + 0.0168),
        ("rim_right", (slot[0] / 2.0 + 0.0042), 0.0084, slot_centre_z,
         slot[1] + 0.0168),
        ("rim_top", 0.0, slot[0], slot_hi + 0.0042, 0.0084),
        ("rim_bottom", 0.0, slot[0], slot_lo - 0.0042, 0.0084),
    ):
        parts.append(p1.chamfer(p1.frustum_box(
            name, shell_y + EMBED, shell_y - ba.THROTTLE_RIM_PROUD, (sx, sz),
            (sx - 0.0013, sz - 0.0013), centre=(cx, cz)), 0.0008))

    stop_span = ba.pin_sweep_generic(ba.THROTTLE_PIVOT, pin_local, angles,
                                     ba.THROTTLE_BOSS_R)
    stop_slab = p5.swept_footprint_solid(
        handle, ba.THROTTLE_PIVOT, pivot_y - 0.0110, pivot_y + 0.0040, angles)
    stop_low_z = (stop_slab["z_min"] if stop_slab
                  else stop_span["z"][0]) - 0.0110
    parts.append(p1.chamfer(p1.frustum_box(
        "stop_low", pivot_y + 0.0040, pivot_y - 0.0110,
        (0.0400, 0.0110), (0.0355, 0.0092),
        centre=(0.0, stop_low_z)), 0.0014))
    for sign in (-1.0, 1.0):
        parts.append(p1.chamfer(p1.frustum_box(
            f"stop_high_{int(sign)}", pivot_y + 0.0040, pivot_y - 0.0110,
            (0.0100, 0.0130), (0.0088, 0.0108),
            centre=(sign * 0.0280, stop_span["z"][1] + 0.0110)), 0.0012))

    count = ba.CONTRACT["Throttle"]["detents"]
    for index in range(count):
        deg = angles[0] + (angles[1] - angles[0]) * index / (count - 1)
        a = math.radians(deg)
        mark = pivot_z + pin_local[0] * math.sin(a) + pin_local[1] * math.cos(a)
        parts.append(p1.chamfer(p1.frustum_box(
            f"detent_{index}", shell_y + EMBED, shell_y - 0.0018,
            (0.0150, 0.0034), (0.0132, 0.0030),
            centre=(slot[0] / 2.0 + 0.0180, mark)), 0.0006))

    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.fastener(
                f"screw_{int(sx)}_{int(sz)}",
                (sx * (width / 2.0 - 0.0140), sz * (height / 2.0 - 0.0140)),
                plate_y - 0.0006, 0.0060, 0.0044))
    parts.append(p1.access_cap("access", (-0.0740, 0.1180), shell_y + EMBED,
                               0.0125, 0.0106, 0.0044))

    # A removable panel with four screws, built from primitives instead of the
    # p1 composite: same feature, 172 triangles instead of 812.
    cover_centre = (0.0700, 0.1180)
    parts.append(p1.chamfer(p1.frustum_box(
        "cover", shell_y + EMBED, shell_y - 0.0030, (0.0440, 0.0620),
        (0.0408, 0.0578), centre=cover_centre), 0.0012))
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            parts.append(p1.chamfer(p1.frustum_cyl(
                f"cover_screw_{int(sx)}_{int(sz)}",
                shell_y - 0.0026, shell_y - 0.0044, 0.0036, 0.0029,
                segments=6,
                centre=(cover_centre[0] + sx * 0.0150,
                        cover_centre[1] + sz * 0.0230)), 0.0006))

    parts.append(p1.register_step("register", (width, height), -EMBED,
                                  -0.0030, 0.0120))
    parts.append(p1.cable_gland("gland", (0.0, -0.1480), shell_y - 0.0018,
                                0.0095, 0.0230))
    parts.append(p1.nameplate("plate_label", (0.0, -0.1000), (0.0560, 0.0180),
                              shell_y + EMBED, 0.0018))
    for sign in (-1.0, 1.0):
        parts.append(p1.mount_hole(f"mount_{int(sign)}",
                                   (sign * 0.0880, -0.1420), plate_y - 0.0004,
                                   0.0078, 0.0046, 0.0034))
    # A plugged port, as a seat and a domed cap rather than the composite.
    parts.append(p1.chamfer(p1.frustum_cyl(
        "blank_seat", plate_y - 0.0004, plate_y - 0.0030, 0.0082, 0.0074,
        segments=10, centre=(-0.0880, 0.1420)), 0.0008))
    parts.append(p1.chamfer(p1.frustum_cyl(
        "blank_cap", plate_y - 0.0028, plate_y - 0.0052, 0.0062, 0.0046,
        segments=10, centre=(-0.0880, 0.1420)), 0.0008))

    audit = p3.coplanar_overlap_audit(parts)
    ba.STATIC_PARTS = ba.snapshot_statics(parts)
    audit["slot"] = {
        "face_slab_m": list(face_slab),
        "required_z_m": [need_face["z_min"], need_face["z_max"]],
        "pin_span_z_m": list(pin_span["z"]),
        "slot_z_m": [slot_lo, slot_hi],
        "slot_size_m": list(slot),
        "margin_m": margin,
        "footprint_method": need_face["method"],
        "range_deg": list(angles),
    }
    audit["working_point"] = {
        "part": "handle_pin",
        "carried_by": ["handle_yoke_-1", "handle_yoke_1"],
        "support_parts": ["handle_pin_boss_-1", "handle_pin_boss_1"],
        "local_yz": [round(v, 6) for v in pin_local],
        "radius_m": ba.THROTTLE_PIN_RADIUS,
        "phase_deg": mid,
        "cheek_contains_pin": (-0.0360 < pin_local[0] - ba.THROTTLE_PIN_R
                               and pin_local[0] + ba.THROTTLE_PIN_R < 0.0055),
        "floating_gap_mm": 0.0,
    }
    audit["density"] = {
        "hub_segments": [26, HUB_SEG],
        "pin_segments": [18, PIN_SEG],
        "boss_segments": [18, BOSS_SEG],
        "bearing_cap_segments": [20, CAP_SEG],
        "grip_loft_segments": [32, GRIP_SEG],
        "grip_loft_rows": [26, len(grip_stops()) - 1],
        "grip_rows_placement": "concentrated on the finger hollow and palm swell",
        "cover_panel": "p1 composite -> box plus four 6-segment screws",
        "blanking_plug": "p1 composite -> seat plus domed cap",
        "kept": ["outline", "grip", "yoke cross pin", "both bearing bosses",
                 "slot", "end stops", "70 deg range"],
    }
    body = p1.join(parts[0], parts[1:])
    body.name = "Throttle_body"
    body.data.name = "Throttle_body"
    p1.assign(body, material)
    handle.parent = pivot
    return body, pivot, handle, audit


BUILDERS_R1 = {"Throttle": build_throttle}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def part_breakdown():
    """Triangles per top-level part, so the reduction can be shown not claimed."""
    rows = {}
    calls = []
    original = p1.join

    def counting_join(target, others):
        snap = []
        for obj in [target] + list(others):
            obj.data.calc_loop_triangles()
            snap.append((obj.name.split(".")[0],
                         len(obj.data.loop_triangles)))
        calls.append(snap)
        return original(target, others)

    p1.clear_scene()
    p1.join = counting_join
    try:
        material = p1.proto.make_material(f"MAT_{THEME}_R1_Neutral", NEUTRAL)
        build_throttle(material)
    finally:
        p1.join = original
    calls.sort(key=lambda c: -len(c))
    for label, snap in (("body", calls[0]), ("handle", calls[1])):
        agg = {}
        for name, tris in snap:
            key = name
            for prefix in ("screw_", "cover_screw_", "detent_", "rim_",
                           "pillow_cap_", "pillow_", "handle_yoke_",
                           "handle_pin_boss_", "stop_high_", "mount_"):
                if name.startswith(prefix):
                    key = prefix + "*"
                    break
            agg[key] = agg.get(key, 0) + tris
        rows[label] = dict(sorted(agg.items(), key=lambda kv: -kv[1]))
    return rows


BATCH_A_BREAKDOWN = {
    "body": {"cover_panel": 812, "screw_*": 768, "pillow_cap_*": 480,
             "mount_*": 472, "detent_*": 264, "access_rim": 212,
             "blank_seat": 192, "rim_*": 176, "gland_body": 168,
             "shell": 96, "pillow_*": 88, "stop_high_*": 88, "plate": 44,
             "skirt": 44, "stop_low": 44, "plate_label": 44,
             "slot_floor": 32, "gasket": 12, "register": 12},
    "handle": {"handle_grip": 1724, "handle_pin_boss_*": 288,
               "handle_hub": 208, "handle_pin": 144, "handle_yoke_*": 88},
    "totals": {"Throttle_body": 4048, "throttle_handle": 2452, "all": 6500},
}


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

    breakdown = part_breakdown()

    import opus5_brushup_kinetic_review as review
    p1.clear_scene()
    review.configure_scene()
    material = p1.proto.make_material(f"MAT_{THEME}_R1_Neutral", NEUTRAL)
    root = bpy.data.objects.new(f"PF_Visual_Throttle_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    body, pivot, moving, audit = build_throttle(material)
    for obj in (body, pivot):
        obj.parent = root
    bpy.context.view_layer.update()

    row = measure_throttle(root, body, pivot, moving)
    row["coplanar_overlap"] = audit
    row["clearance"] = ba.motion_clearance_audit(pivot, moving, "Throttle")
    row["triangle_budget_validator_total"] = THROTTLE_BUDGET_TOTAL
    row["triangle_target_total"] = TARGET_TOTAL
    row["gates"]["triangles_validator_total"] = (
        row["triangles_total"] <= THROTTLE_BUDGET_TOTAL)
    row["gates"]["triangles_target"] = row["triangles_total"] <= TARGET_TOTAL
    blend = geometry_dir / f"BL_Throttle_{THEME}_V6_Opus5_P6A_R1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    row["blend"] = str(blend.relative_to(project_root))
    row["blend_sha256"] = m1.digest(blend)

    focus, radius, scale = p1.rig_for([body, moving])
    images = {}
    for label, view in p1.VIEWS.items():
        path = grey_dir / f"Grey_Throttle_{THEME}_P6A_R1_{label}.png"
        p1.shot(focus, radius, view, 52.0, scale, path)
        images[label] = str(path.relative_to(project_root))
    row["grayscale_images"] = images

    details = {}
    for value, label in ba.pose_set("Throttle"):
        ba.apply_pose(pivot, "Throttle", value)
        near = detail_dir / f"Detail_Throttle_motion_{label}.png"
        p1.shot(focus, radius * 0.52, (44.0, 12.0), 60.0, scale * 0.52, near)
        details[f"motion_{label}"] = str(near.relative_to(project_root))
        wide = detail_dir / f"Detail_Throttle_pose_{label}.png"
        p1.shot(focus, radius, (58.0, 8.0), 52.0, scale, wide)
        details[f"pose_{label}"] = str(wide.relative_to(project_root))
    ba.apply_pose(pivot, "Throttle", 0.0)
    row["detail_images"] = details
    row["all_gates_passed"] = all(row["gates"].values())

    delta = {
        "batch_a": BATCH_A_BREAKDOWN,
        "r1": {"body": breakdown["body"], "handle": breakdown["handle"],
               "totals": dict(row["triangles_per_object"],
                              all=row["triangles_total"])},
        "reduction_total": BATCH_A_BREAKDOWN["totals"]["all"]
        - row["triangles_total"],
        "batch_a_envelope_whd": [0.239, 0.339, 0.117],
        "r1_envelope_whd": [round(v, 4)
                            for v in row["measured_width_height_depth"]],
    }

    payload = {
        "phase": "Theme4-P6-BatchA-R1-geometry",
        "note": ("Throttle only. RefinedModelReplacementValidator counts the "
                 "whole prefab instance against GetTriangleBudget, which is "
                 "5000 for ThrottleLever; Batch A was 6500. Density reduced, "
                 "structure kept. MeterMedium, MeterLarge, PowerSlider and "
                 "P1-P5 are untouched."),
        "changed_asset": "Throttle",
        "contract": {k: (list(v) if isinstance(v, tuple) else v)
                     for k, v in CONTRACT_THROTTLE.items()},
        "triangle_delta": delta,
        "assets": {"Throttle": row},
    }
    payload["status"] = (
        "p6_batch_a_r1_geometry_ready"
        if row["all_gates_passed"] and row["clearance"]["clean"]
        else "p6_batch_a_r1_geometry_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchA-R1] Throttle: body {row['triangles_per_object']} "
          f"total {row['triangles_total']} (was 6500, target {TARGET_TOTAL}), "
          f"clearance clean {row['clearance']['clean']} "
          f"min {row['clearance']['min_clearance_mm']} mm, "
          f"gates {row['all_gates_passed']}")
    print(f"[BatchA-R1] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
