"""R3 / B2P design survey: where can the counterweight actually go?

Alignment 76.2 and 78.2. Placing the brush-up parts on the true pivot puts the
counterweight inside `kinetic_polygon_bezel`, which turns out to be a solid
twelve-sided plate rather than a ring (alignment 76.1). Shrinking the weight
until it fits inside the bearing radius would only hide that, so three options
are measured instead:

* A - separate the weight in depth, in front of or behind the plate;
* B - open the plate's centre into the bezel/hub aperture it is drawn as;
* C - drop the weight and let the boss and zone band carry the intent.

The same run also settles a question the fix depends on: the shipped
`needle x kinetic_polygon_bezel` contact. The needle is a joined mesh, so its
hub, shaft and blade are split into connected components and attributed
separately - a hub seated in its mount is a different finding from a blade
buried in a solid plate.

Design-only: every edit is made to throwaway in-memory geometry and no blend is
saved.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_r3_b2p_design_survey.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_archetype as brushup
import opus5_brushup_kinetic_pilot as pilot
import opus5_d5_toggle_axle_proposal as components
import opus5_joint_contact_section as section


THEME = "KineticSafety"
KEYS = ("MeterRound", "MeterMedium", "MeterLarge")
PLATE = "kinetic_polygon_bezel"
SWEEP = (-55.0, 55.0)
STEPS = 22


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--key", dest="keys", action="append", choices=KEYS)
    parser.add_argument(
        "--trial-dir",
        required=True,
        help="Where the comparison images go. Nothing canonical is written.",
    )
    return parser.parse_args(args)


def radial(point, centre):
    return math.hypot(point.x - centre.x, point.z - centre.z)


def open_meter(project_root, key):
    source = (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / THEME
        / f"BL_{key}_{THEME}_V6_Retopo.blend"
    )
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects[f"PF_Visual_{key}_{THEME}_V6"]
    pivot = bpy.data.objects["needle_pivot"]
    return source, root, pivot


def sweep_contact(pivot, movers, statics, centre, bearing, steps=STEPS):
    """Contact per pair with the radius its contact points reach."""
    trees = [(obj.name, *pilot.bvh_for(obj)) for obj in statics]
    base = pivot.rotation_euler.copy()
    low, high = SWEEP
    pairs = {}
    try:
        for index in range(steps + 1):
            angle = low + (high - low) * index / steps
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            for mover in movers:
                tree, vertices, polygons = pilot.bvh_for(mover)
                for name, other, other_vertices, other_polygons in trees:
                    for mine, theirs in tree.overlap(other):
                        points = pilot.triangle_contact_points(
                            [vertices[i] for i in polygons[mine]],
                            [other_vertices[i] for i in other_polygons[theirs]],
                        )
                        if not points:
                            continue
                        entry = pairs.setdefault(
                            f"{mover.name} x {name}",
                            {
                                "samples": set(),
                                "radius_min": None,
                                "radius_max": None,
                                "outside_bearing": False,
                            },
                        )
                        entry["samples"].add(round(angle, 3))
                        for point in points:
                            radius = radial(point, centre)
                            entry["radius_min"] = (
                                radius
                                if entry["radius_min"] is None
                                else min(entry["radius_min"], radius)
                            )
                            entry["radius_max"] = (
                                radius
                                if entry["radius_max"] is None
                                else max(entry["radius_max"], radius)
                            )
                            if (point - centre).length > bearing:
                                entry["outside_bearing"] = True
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    for entry in pairs.values():
        entry["sample_count"] = len(entry.pop("samples"))
        for field in ("radius_min", "radius_max"):
            if entry[field] is not None:
                entry[field] = round(entry[field], 6)
    return pairs


def attribute_needle(project_root, key):
    """Split the joined needle and attribute the shipped plate contact."""
    _, root, pivot = open_meter(project_root, key)
    needle = bpy.data.objects["needle"]
    plate = bpy.data.objects[PLATE]
    centre = pivot.matrix_world.translation.copy()
    hub_radius = max(
        abs((needle.matrix_world @ vertex.co).x - centre.x)
        for vertex in needle.data.vertices
    )
    pieces = components.components_of(needle)
    for piece in pieces:
        pilot.parent_keep_world(piece, pivot)
    needle.hide_viewport = True
    bpy.context.view_layer.update()
    facts = {piece.name: components.describe(piece, centre) for piece in pieces}
    contact = sweep_contact(
        pivot, pieces, [plate], centre, hub_radius * 1.7
    )
    return {
        "components": facts,
        "contact_with_plate": contact,
        "bearing_radius": round(hub_radius * 1.7, 6),
    }


def triangles_of(obj):
    """Real triangle count, so before and after are the same measurement.

    Alignment 80.3: `len(mesh.polygons)` counts n-gons as one face, so mixing
    it with a triangulated count makes a plate look like it lost triangles it
    never had. `loop_triangles` is the number that means the same thing on both
    sides of a comparison.
    """
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def classify_pairs(pairs, spec, baseline):
    """Split contacts into the four groups a reviewer needs kept apart."""
    declared = set((spec.get("motion") or {}).get("allowed_bearing_pairs") or {})
    groups = {"intended_bearing": {}, "known_tick_d3": {}, "plate_d9": {}, "new": {}}
    for label, entry in sorted(pairs.items()):
        static = label.split(" x ", 1)[-1]
        if label in declared:
            groups["intended_bearing"][label] = entry
        elif "tick" in static:
            groups["known_tick_d3"][label] = entry
        elif static == PLATE:
            groups["plate_d9"][label] = entry
        elif label not in baseline:
            groups["new"][label] = entry
        else:
            groups.setdefault("other_pre_existing", {})[label] = entry
    return groups


def plate_facts(plate, centre):
    points = [plate.matrix_world @ vertex.co for vertex in plate.data.vertices]
    radii = [radial(point, centre) for point in points]
    return {
        "vertex_radius": [round(min(radii), 6), round(max(radii), 6)],
        "y": [
            round(min(point.y for point in points), 6),
            round(max(point.y for point in points), 6),
        ],
        "triangles": triangles_of(plate),
        "is_solid": True,
        "note": (
            "built by v4.cylinder_y(..., 12): a solid twelve-sided plate, so "
            "the minimum vertex radius says nothing about a hole"
        ),
    }


def build_parts(root, spec_key):
    mats = pilot.materials_by_role()
    spec = brushup.SPECS[f"{THEME}/{spec_key}"]
    brushup.BUILDERS[spec["builder"]](root, mats)
    return spec


def option_a_depth(project_root, key, offset_mm):
    """Move the counterweight clear of the plate in depth."""
    _, root, pivot = open_meter(project_root, key)
    spec = build_parts(root, key)
    weight = bpy.data.objects.get("kinetic_v6_needle_counterweight")
    plate = bpy.data.objects[PLATE]
    centre = pivot.matrix_world.translation.copy()
    if weight is None:
        return None
    plate_front = min(
        (plate.matrix_world @ vertex.co).y for vertex in plate.data.vertices
    )
    target_front = plate_front - offset_mm / 1000.0
    current_back = max(
        (weight.matrix_world @ vertex.co).y for vertex in weight.data.vertices
    )
    delta = target_front - current_back
    for vertex in weight.data.vertices:
        world = weight.matrix_world @ vertex.co
        world.y += delta
        vertex.co = weight.matrix_world.inverted() @ world
    weight.data.update()
    bpy.context.view_layer.update()
    hub = brushup.meter_geometry(root, spec["motion"])["hub_radius"]
    statics = [
        obj
        for obj in pilot.meshes_under(root)
        if not _under(obj, pivot)
    ]
    contact = sweep_contact(pivot, [weight], statics, centre, hub * 1.7)
    bounds = pilot.world_bounds(pilot.meshes_under(root))
    return {
        "shift_mm": round(delta * 1000.0, 4),
        "clearance_from_plate_mm": offset_mm,
        "weight_contact": contact,
        "unintended_contact": undeclared(contact, spec),
        "contact_free": not undeclared(contact, spec),
        "bounds": bounds,
    }


def option_b_aperture(project_root, key, aperture_scale, trial_dir=None):
    """Open the plate's centre, then sweep the whole movable island.

    The first version swept only the counterweight, so the claim that opening
    the plate also clears the blade (defect D-9) was an inference from the
    shape rather than a measurement (alignment 80.3). The island is swept whole
    here, and the pairs are reported in the groups they belong to.
    """
    _, root, pivot = open_meter(project_root, key)
    spec = build_parts(root, key)
    weight = bpy.data.objects.get("kinetic_v6_needle_counterweight")
    plate = bpy.data.objects[PLATE]
    centre = pivot.matrix_world.translation.copy()
    hub = brushup.meter_geometry(root, spec["motion"])["hub_radius"]

    movers_before = [obj for obj in pilot.meshes_under(root) if _under(obj, pivot)]
    statics_before = [
        obj for obj in pilot.meshes_under(root) if not _under(obj, pivot)
    ]
    baseline_pairs = sweep_contact(
        pivot, movers_before, statics_before, centre, hub * 1.7
    )
    triangles_before = triangles_of(plate)
    bounds_before = pilot.world_bounds(pilot.meshes_under(root))

    reach = (
        max(
            radial(weight.matrix_world @ vertex.co, centre)
            for vertex in weight.data.vertices
        )
        if weight is not None
        else hub
    )
    aperture = reach * aperture_scale
    points = [plate.matrix_world @ vertex.co for vertex in plate.data.vertices]
    outer_min = min(
        radial(point, centre)
        for point in points
        if radial(point, centre) > aperture
    )
    outer_max = max(radial(point, centre) for point in points)
    y_low = min(point.y for point in points)
    y_high = max(point.y for point in points)
    material = plate.data.materials[0] if plate.data.materials else None
    parent = plate.parent
    bpy.data.objects.remove(plate, do_unlink=True)
    ring = brushup.arc_band(
        PLATE,
        aperture,
        outer_max,
        0.0,
        360.0,
        y_low,
        y_high,
        material,
        segments=12,
        centre_x=centre.x,
        centre_z=centre.z,
    )
    ring.parent = parent
    bpy.context.view_layer.update()

    movers = [obj for obj in pilot.meshes_under(root) if _under(obj, pivot)]
    statics = [obj for obj in pilot.meshes_under(root) if not _under(obj, pivot)]
    pairs = sweep_contact(pivot, movers, statics, centre, hub * 1.7)
    boss = bpy.data.objects.get("kinetic_v6_needle_boss")
    images = {}
    if trial_dir is not None:
        images = trial_images(root, pivot, key, aperture_scale, Path(trial_dir))
    return {
        "aperture_radius": round(aperture, 6),
        "counterweight_reach": round(reach, 6),
        # How much bezel is left: from the aperture out to the nearest point of
        # the plate's outer polygon, which is the narrowest the ring ever is.
        "remaining_ring_width_mm": round((outer_min - aperture) * 1000.0, 4),
        "outer_polygon_min_radius": round(outer_min, 6),
        "plate_triangles_before": triangles_before,
        "plate_triangles_after": triangles_of(ring),
        "hub_boss_still_supported": bool(
            boss is not None
            and any(
                label.endswith(boss.name) or boss.name in label for label in pairs
            )
        ),
        "pairs_baseline": classify_pairs(baseline_pairs, spec, {}),
        "pairs_after": classify_pairs(pairs, spec, baseline_pairs),
        "unintended_contact": undeclared(
            {
                label: entry
                for label, entry in pairs.items()
                if label not in baseline_pairs
            },
            spec,
        ),
        "plate_pairs_resolved": sorted(
            label
            for label in baseline_pairs
            if label.endswith(PLATE) and label not in pairs
        ),
        "plate_pairs_remaining": sorted(
            label for label in pairs if label.endswith(PLATE)
        ),
        "bounds_before": bounds_before,
        "bounds_after": pilot.world_bounds(pilot.meshes_under(root)),
        "bounds_unchanged": bounds_before
        == pilot.world_bounds(pilot.meshes_under(root)),
        "images": images,
    }


def trial_images(root, pivot, key, aperture_scale, trial_dir):
    """Fixed-camera views of the throwaway scene, trial area only."""
    import opus5_brushup_kinetic_review as review
    import opus5_brushup_review as brushup_review

    review.configure_scene()
    rig = brushup_review.rig_from(root)
    rig = dict(rig, radius=rig["radius"] * 0.85, lens=80.0)
    base = pivot.rotation_euler.copy()
    directory = trial_dir / "option_b"
    directory.mkdir(parents=True, exist_ok=True)
    images = {}
    try:
        for pose, angle in (("neutral", 0.0), ("maximum", 55.0)):
            posed = base.copy()
            posed[1] = base[1] + math.radians(angle)
            pivot.rotation_euler = posed
            bpy.context.view_layer.update()
            path = directory / f"{key}_aperture_x{aperture_scale:g}_{pose}.png"
            review.shot(rig, rig["focus"], rig["radius"], (0.0, 6.0), rig["lens"], path)
            images[pose] = str(path)
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    return images


def option_c_no_weight(project_root, key):
    """Boss and zone band only."""
    _, root, pivot = open_meter(project_root, key)
    spec = build_parts(root, key)
    weight = bpy.data.objects.get("kinetic_v6_needle_counterweight")
    centre = pivot.matrix_world.translation.copy()
    if weight is not None:
        bpy.data.objects.remove(weight, do_unlink=True)
    bpy.context.view_layer.update()
    hub = brushup.meter_geometry(root, spec["motion"])["hub_radius"]
    movers = [obj for obj in pilot.meshes_under(root) if _under(obj, pivot)]
    statics = [obj for obj in pilot.meshes_under(root) if not _under(obj, pivot)]
    contact = sweep_contact(pivot, movers, statics, centre, hub * 1.7)
    return {
        "parts_kept": sorted(
            obj.name
            for obj in pilot.meshes_under(root)
            if obj.name.startswith("kinetic_v6_")
        ),
        "movable_contact": {
            label: entry
            for label, entry in contact.items()
            if entry["outside_bearing"]
        },
        "bounds": pilot.world_bounds(pilot.meshes_under(root)),
    }


def undeclared(contact, spec):
    """Contacts other than the ones the spec already declares as intended.

    The counterweight seated against its own boss is a declared bearing pair
    (alignment 77.2); counting it as a collision would reject every option.
    """
    declared = set((spec.get("motion") or {}).get("allowed_bearing_pairs") or {})
    return sorted(set(contact) - declared)


def _under(obj, parent):
    node = obj
    while node is not None:
        if node is parent:
            return True
        node = node.parent
    return False


def survey_one(project_root, key, trial_dir=None):
    _, root, pivot = open_meter(project_root, key)
    centre = pivot.matrix_world.translation.copy()
    plate = plate_facts(bpy.data.objects[PLATE], centre)
    attribution = attribute_needle(project_root, key)
    return {
        "model": f"{THEME}/{key}",
        "saved_anything": False,
        "pivot_world": [round(v, 6) for v in centre],
        "plate": plate,
        "shipped_needle_attribution": attribution,
        "option_a_depth_separation": {
            f"{offset:g}mm": option_a_depth(project_root, key, offset)
            for offset in (0.7, 1.4)
        },
        "option_b_open_aperture": {
            f"x{scale:g}": option_b_aperture(project_root, key, scale, trial_dir)
            for scale in (1.15, 1.35)
        },
        "option_c_drop_counterweight": option_c_no_weight(project_root, key),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    entries = [
        survey_one(project_root, key, args.trial_dir)
        for key in (args.keys or KEYS)
    ]
    for entry in entries:
        a = entry["option_a_depth_separation"]
        b = entry["option_b_open_aperture"]
        c = entry["option_c_drop_counterweight"]
        print(
            f"[Opus5R3B2P] {entry['model']}: "
            f"A {[k for k, v in a.items() if v and v['contact_free']] or 'none clear'}; "
            f"B {[k for k, v in b.items() if v and not v['unintended_contact']] or 'none clear'}; "
            f"C outside pairs {len(c['movable_contact'])}"
        )
    output = (
        project_root / "ArtSource/Blender/BrushUp/Opus5/r3_b2p_design_survey.json"
    )
    output.write_text(
        json.dumps(
            {
                "note": (
                    "Design-only (alignment 76.2). Throwaway in-memory "
                    "geometry; no blend is saved and no candidate is written."
                ),
                "models": {entry["model"]: entry for entry in entries},
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5R3B2P] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
