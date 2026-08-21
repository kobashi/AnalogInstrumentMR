"""Phase M2c: which slot angle, judged on the faithful ring?

Alignment 100.4. The minimum clear angles from M2b have nothing but the search
quantisation between them and a failing sweep, and the old +-18/+-24 numbers
were only ever seen on the `arc_band` stand-in. So two angles per theme are cut
from the production mesh, measured, and rendered side by side against the
shipped ring under one camera, light and exposure setup.

Three corrections from 100.2 and 100.3 are built in:

* The lip proxy is compared **at the same pose**. Kinetic Safety's drop across
  its throw was measured on the slotted ring alone in M2b, which cannot show
  whether the cut caused it - the production ring is now measured at the same
  three poses and the difference taken per pose.
* The 0.10 mm drop limit is kept, not relaxed.
* Minimum surface separation over the whole sweep is reported as an exact
  triangle-triangle distance, so "clear" comes with a margin rather than only a
  yes.

Read-only. No Blend is saved and no existing report is modified; the renders go
to each theme's review directory under a name of their own.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d5_faithful_slot_selection.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import generate_hardsurface_lever_prototype as hs
import opus5_brushup_kinetic_pilot as pilot
import opus5_brushup_kinetic_review as review
import opus5_contact as contact
import opus5_contact_migration_m1 as m1
import opus5_d5_profile_preserving_slot as m2b


OUTPUT = "ArtSource/Blender/BrushUp/Opus5/d5_faithful_slot_visual_selection.json"
PREFIX = "d5_faithful_slot_selection"

# Alignment 100.4. Compact is the M2b minimum plus one degree; conservative is
# the angle the earlier visual review ran on, now cut faithfully.
VARIANTS = {
    "OrbitalAnalog": {"compact": 17.0, "conservative": 18.0},
    "ForgeBrass": {"compact": 19.5, "conservative": 24.0},
    "KineticSafety": {"compact": 22.0, "conservative": 24.0},
}

POSES = (("minimum", 0.0), ("neutral", 28.0), ("maximum", 56.0))
SEPARATION_SEARCH_M = 0.006
# The shared default of 5 runs a 32-character caption off a 900 px frame.
LABEL_SCALE = 4
LABEL_STRIP = 2 * 7 * LABEL_SCALE + 4 * LABEL_SCALE

VIEWS = {
    "neutral_front": {"pose": 28.0, "azimuth": 0.0, "elevation": 15.0, "shot": "model"},
    "neutral_oblique": {"pose": 28.0, "azimuth": 40.0, "elevation": 28.0, "shot": "ring"},
    # Straight down the cut plane the ring's section and the ball's are
    # coplanar and shade identically, so the ring vanishes into the disc. The
    # camera is swung off the plane and the ring is tinted for this shot only.
    "neutral_section": {
        "pose": 28.0, "azimuth": 68.0, "elevation": 20.0, "shot": "section",
        "energy_boost": 1.6,
    },
    "minimum_oblique": {"pose": 0.0, "azimuth": 40.0, "elevation": 28.0, "shot": "ring"},
    "maximum_oblique": {"pose": 56.0, "azimuth": 40.0, "elevation": 28.0, "shot": "ring"},
    # The slot sits behind the shaft and under the ball, which is where it has
    # to be - so on the assembled model the opening is barely visible from any
    # angle. This view drops everything but the ring so the two angles can
    # actually be told apart. It is a diagnostic, not a look at the product.
    "ring_only_axial": {
        "pose": 28.0, "azimuth": 0.0, "elevation": 0.0, "shot": "ring_only",
        # A lone ring has nothing around it to bounce light back, so it needs
        # more than the inverse-square compensation gives it.
        "energy_boost": 2.5,
    },
}

# The shared label font has no K, X or full stop, and every one of those is in
# the labels this phase needs. The table's own comment says to add the glyph
# rather than lose the letter.
review.GLYPHS.update(
    {
        "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
        "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
        "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
        "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
        "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
        "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
        ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
        "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
        "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    }
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--theme", dest="themes", action="append")
    parser.add_argument("--skip-renders", action="store_true")
    return parser.parse_args(args)


def source_blend(project_root, theme):
    return (
        project_root
        / "ArtSource/Blender/ThemeHardSurfaceV6"
        / theme
        / f"BL_Toggle_{theme}_V6_Retopo.blend"
    )


def set_pose(pivot, degrees):
    pivot.rotation_euler[0] = math.radians(degrees)
    bpy.context.view_layer.update()


def minimum_separation(scene, ring, poses):
    """Exact closest approach over the sweep, in mm, or None if out of reach."""
    pivot = scene["pivot"]
    base = pivot.rotation_euler.copy()
    best = None
    try:
        for degrees in poses:
            set_pose(pivot, degrees)
            static_tris = m1.world_triangles(ring)
            static_broad, _ = m1.trees(ring)
            for mover in scene["movers"]:
                mover_tris = m1.world_triangles(mover)
                mover_broad, _ = m1.trees(mover)
                pairs = contact.candidate_pairs(
                    mover_tris, static_tris, mover_broad, static_broad,
                    tolerance=SEPARATION_SEARCH_M,
                )
                for mover_index, static_index in pairs:
                    distance = contact.triangle_distance(
                        mover_tris[mover_index], static_tris[static_index]
                    )
                    if best is None or distance < best[0]:
                        best = (distance, mover.name, degrees)
    finally:
        pivot.rotation_euler = base
        bpy.context.view_layer.update()
    if best is None:
        return {
            "computable": False,
            "reason": (
                f"nothing came within {SEPARATION_SEARCH_M * 1000.0} mm; "
                "no estimate is substituted"
            ),
        }
    return {
        "computable": True,
        "minimum_separation_mm": round(best[0] * 1000.0, 6),
        "component": best[1],
        "pose_degrees": round(best[2], 4),
        "search_radius_mm": SEPARATION_SEARCH_M * 1000.0,
        "method": "exact triangle-triangle distance over candidate pairs",
    }


def facet_alignment(ring, centre, half_angle):
    """Where the cut lands on the ring's facets.

    These rings are polygons, not circles - Kinetic Safety's is a decagon. A
    cut that stops just short of a facet corner leaves a sliver that reads as a
    modelling mistake, so where the edge falls is a silhouette argument with a
    number behind it rather than an impression.
    """
    points = [ring.matrix_world @ vertex.co for vertex in ring.data.vertices]
    outer = max(math.hypot(p.x - centre.x, p.z - centre.z) for p in points)
    raw = sorted(
        m2b.azimuth_of(p, centre)
        for p in points
        if math.hypot(p.x - centre.x, p.z - centre.z) > outer - 1e-5
    )
    # A chamfered rim puts two vertices at almost the same azimuth, and Kinetic
    # Safety's corners are not evenly spaced at all, so the facet boundaries
    # are clustered out of the raw azimuths rather than assumed to be 360/n.
    corners = []
    for azimuth in raw:
        if corners and (azimuth - corners[-1]) < 1.0:
            continue
        corners.append(azimuth)
    if len(corners) > 1 and (corners[0] + 360.0 - corners[-1]) < 1.0:
        corners.pop()
    if len(corners) < 3:
        return {"facets": len(corners), "computable": False}

    gaps = [
        (corners[(i + 1) % len(corners)] - corners[i]) % 360.0
        for i in range(len(corners))
    ]
    edge = half_angle % 360.0
    behind = max(
        (c for c in corners if (edge - c) % 360.0 < 360.0), key=lambda c: -((edge - c) % 360.0)
    )
    index = corners.index(behind)
    ahead = corners[(index + 1) % len(corners)]
    local = gaps[index]
    fragment = (ahead - edge) % 360.0
    return {
        "computable": True,
        "facets": len(corners),
        "facet_widths_deg": {
            "min": round(min(gaps), 4),
            "max": round(max(gaps), 4),
            "even": round(max(gaps) - min(gaps), 4) < 0.01,
        },
        "corner_azimuths_deg": [round(c, 3) for c in corners],
        "cut_edge_deg": half_angle,
        "facet_containing_edge_deg": [round(behind, 3), round(ahead, 3)],
        "local_facet_width_deg": round(local, 4),
        "residual_fragment_deg": round(fragment, 4),
        "fragment_as_facet_fraction": round(fragment / local, 4) if local else None,
        "sliver": bool(local) and fragment / local < 0.15,
        "meaning": (
            "angle from the cut edge to the next facet corner still in "
            "material, against the width of the facet it lands in; a small "
            "fraction leaves a sliver"
        ),
    }


def lip_by_pose(ring, joint, centre, pivot, half_angle, heights):
    measured = {}
    for label, degrees in POSES:
        set_pose(pivot, degrees)
        profile = m2b.lip_profile(ring, joint, centre, half_angle, heights)
        measured[label] = {
            "degrees": degrees,
            "ball_max_radius": profile["ball_max_radius"],
            "min_lip_overlap_mm": profile["min_lip_overlap_mm"],
            "worst_azimuth_deg": profile["worst_azimuth_deg"],
            "worst_section_y": profile["worst_section_y"],
            "coverage_deg": profile["coverage"]["coverage_deg"],
            "total_gap_deg": profile["coverage"]["total_gap_deg"],
            "largest_gap_deg": profile["coverage"]["largest_gap_deg"],
        }
    set_pose(pivot, 0.0)
    return measured


def measure_variant(project_root, theme, name, half_angle, baseline_lip):
    scene = m2b.toggle_scene(project_root, theme)
    ring, joint, centre = scene["ring"], scene["joint"], scene["centre"]
    heights = m2b.section_heights(ring, centre)
    production_health = m2b.mesh_health(ring)

    cut = m2b.cut_slot(ring, centre, half_angle)
    deviation = m2b.surface_deviation(cut, ring, centre, half_angle)
    health = m2b.mesh_health(cut)
    ring.hide_viewport = True
    ring.hide_render = True
    cut.parent = ring.parent
    bpy.context.view_layer.update()

    facets = facet_alignment(ring, centre, half_angle)
    lip = lip_by_pose(cut, joint, centre, scene["pivot"], half_angle, heights)
    sweep = m2b.clear_over_poses(scene, cut)
    separation = minimum_separation(scene, cut, m2b.POSES)

    same_pose = {}
    for label, _ in POSES:
        base = baseline_lip[label]["min_lip_overlap_mm"] or 0.0
        slotted = lip[label]["min_lip_overlap_mm"] or 0.0
        same_pose[label] = {
            "production_mm": round(base, 6),
            "slotted_mm": round(slotted, 6),
            "ratio": round(slotted / base, 6) if base else None,
            "drop_mm": round(base - slotted, 6),
            "pass": (
                base > 0.0
                and slotted / base >= m2b.LIP_RATIO_FLOOR
                and (base - slotted) <= m2b.LIP_DROP_LIMIT_MM
            ),
        }

    contract = {
        "profile_preservation": {
            "limit_mm": m2b.DEVIATION_LIMIT_MM,
            "measured_mm": deviation["max_deviation_mm"],
            "pass": deviation["max_deviation_mm"] <= m2b.DEVIATION_LIMIT_MM,
        },
        "collision": {
            "surface_crossing": sweep["surface_crossing"],
            "penetrating_vertices": sweep["penetrating_vertices"],
            "deepest_intrusion_mm": sweep["deepest_intrusion_mm"],
            "pass": sweep["clear"],
        },
        "lip_proxy_same_pose": {
            "requirement": (
                "production(pose) vs slotted(pose), ratio >= 0.95 and drop "
                "<= 0.10 mm, at every pose (alignment 100.2)"
            ),
            "per_pose": same_pose,
            "worst_ratio": min(
                (v["ratio"] for v in same_pose.values() if v["ratio"] is not None),
                default=None,
            ),
            "worst_drop_mm": max(v["drop_mm"] for v in same_pose.values()),
            "pass": all(v["pass"] for v in same_pose.values()),
        },
        "intended_opening": {
            "expected_total_gap_deg": round(half_angle * 2.0, 4),
            "measured_total_gap_deg": lip["neutral"]["total_gap_deg"],
            "difference_deg": round(
                abs(lip["neutral"]["total_gap_deg"] - half_angle * 2.0), 4
            ),
            "pass": abs(lip["neutral"]["total_gap_deg"] - half_angle * 2.0) <= 1.0,
        },
        "triangles_and_materials": {
            "production": production_health["loop_triangles"],
            "slotted": health["loop_triangles"],
            "delta": health["loop_triangles"] - production_health["loop_triangles"],
            "material_slots_preserved": (
                production_health["material_slots"] == health["material_slots"]
            ),
            "pass": (
                health["loop_triangles"] <= production_health["loop_triangles"]
                and production_health["material_slots"] == health["material_slots"]
            ),
        },
        "mesh_health": {
            "closed": health["closed"],
            "normals_outward": health["normals_outward"],
            "degenerate_faces": health["degenerate_faces"],
            "pass": (
                health["closed"]
                and health["normals_outward"]
                and health["degenerate_faces"] == 0
            ),
        },
    }
    contract["all_pass"] = all(item["pass"] for item in contract.values())

    return {
        "variant": name,
        "slot_half_angle_deg": half_angle,
        "lip_by_pose": lip,
        "facet_alignment": facets,
        "surface_deviation": deviation,
        "mesh_health": health,
        "collision_sweep": {
            key: value for key, value in sweep.items() if key != "pairs"
        },
        "minimum_surface_separation": separation,
        "contract": contract,
    }


def baseline_measurements(project_root, theme):
    scene = m2b.toggle_scene(project_root, theme)
    ring, joint, centre = scene["ring"], scene["joint"], scene["centre"]
    heights = m2b.section_heights(ring, centre)
    lip = lip_by_pose(ring, joint, centre, scene["pivot"], None, heights)
    return lip, m2b.mesh_health(ring), heights


def build_render_state(project_root, theme, variant, half_angle):
    """Load the toggle and put it in the state this variant describes."""
    if variant == "production":
        m1.open_blend(source_blend(project_root, theme))
        root = bpy.data.objects[f"PF_Visual_Toggle_{theme}_V6"]
        pivot = bpy.data.objects["switch_pivot"]
        ring = next(
            o for o in pilot.meshes_under(root) if "retaining_ring" in o.name.lower()
        )
        joint = next(
            o for o in pilot.meshes_under(root) if "hemisphere" in o.name.lower()
        )
        return {"root": root, "pivot": pivot, "ring": ring, "joint": joint}

    scene = m2b.toggle_scene(project_root, theme)
    ring, centre = scene["ring"], scene["centre"]
    cut = m2b.cut_slot(ring, centre, half_angle)
    cut.parent = ring.parent
    ring.hide_viewport = True
    ring.hide_render = True
    bpy.context.view_layer.update()
    return {
        "root": bpy.data.objects[f"PF_Visual_Toggle_{theme}_V6"],
        "pivot": scene["pivot"],
        "ring": cut,
        "joint": scene["joint"],
    }


def half_space_cut(obj, centre):
    """Trim everything at x > centre so the lip engagement is visible."""
    reach = 1.0
    mesh = bpy.data.meshes.new("opus5_section_box")
    box = bpy.data.objects.new("opus5_section_box", mesh)
    bpy.context.collection.objects.link(box)
    low = [centre.x, centre.y - reach, centre.z - reach]
    high = [centre.x + reach, centre.y + reach, centre.z + reach]
    verts = [
        (low[0], low[1], low[2]), (high[0], low[1], low[2]),
        (high[0], high[1], low[2]), (low[0], high[1], low[2]),
        (low[0], low[1], high[2]), (high[0], low[1], high[2]),
        (high[0], high[1], high[2]), (low[0], high[1], high[2]),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    mesh.update()
    for material in obj.data.materials:
        box.data.materials.append(material)

    modifier = obj.modifiers.new("section", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.object = box
    modifier.solver = "EXACT"
    depsgraph = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    obj.modifiers.remove(modifier)
    old = obj.data
    obj.data = baked
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(box, do_unlink=True)
    bpy.context.view_layer.update()


def render_view(state, theme, view, path):
    root, pivot = state["root"], state["pivot"]
    set_pose(pivot, view["pose"])
    centre = pivot.matrix_world.translation.copy()

    meshes = [o for o in pilot.meshes_under(root) if not o.hide_render]
    if view["shot"] == "ring_only":
        for obj in meshes:
            if obj.name != state["ring"].name:
                obj.hide_render = True
        meshes = [state["ring"]]
    if view["shot"] == "section":
        keep = {state["ring"].name, state["joint"].name}
        for obj in meshes:
            if obj.name not in keep:
                obj.hide_render = True
        for obj in (state["ring"], state["joint"]):
            half_space_cut(obj, centre)
        tint = hs.material(
            "MAT_Opus5_Section_Ring", (0.45, 0.16, 0.05, 1.0), 0.85, 0.30
        )
        state["ring"].data.materials.clear()
        state["ring"].data.materials.append(tint)
        meshes = [state["ring"], state["joint"]]

    points = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    span = max(
        max(p[i] for p in points) - min(p[i] for p in points) for i in range(3)
    )
    ring_points = [
        state["ring"].matrix_world @ v.co for v in state["ring"].data.vertices
    ]
    ring_span = max(
        math.hypot(p.x - centre.x, p.z - centre.z) for p in ring_points
    )

    ball_span = max(
        (state["joint"].matrix_world @ v.co - centre).length
        for v in state["joint"].data.vertices
    )
    if view["shot"] == "model":
        focus, radius, lens, scale = centre, span * 2.4, 58.0, span * 0.9
    elif view["shot"] == "section":
        # Centred, so the retained lip at the bottom and the opening at the top
        # are both in frame rather than one at a time.
        focus, radius, lens, scale = centre, ring_span * 5.2, 58.0, ring_span * 2.8
    elif view["shot"] == "ring_only":
        focus, radius, lens, scale = centre, ring_span * 7.0, 55.0, ring_span * 3.0
    else:
        focus, radius, lens, scale = centre, ring_span * 9.0, 55.0, ring_span * 3.4

    # Not clamped at 1.0: these rigs sit closer than the pilot's 0.17 m, so the
    # ratio has to be allowed below one or every close-up blows out.
    rig = {
        "light_scale": scale,
        "energy_scale": (scale / 0.17) ** 2 * view.get("energy_boost", 1.0),
    }
    review.shot(
        rig, (focus.x, focus.y, focus.z), radius,
        (view["azimuth"], view["elevation"]), lens, path,
    )


def label_copy(source, destination, lines):
    """Same image with a caption strip added above the rendered frame."""
    import numpy

    array = review.load_rgba(source)
    height, width = array.shape[0], array.shape[1]
    canvas = numpy.zeros((height + LABEL_STRIP, width, 4), dtype=array.dtype)
    canvas[:, :, 3] = 1.0
    canvas[0:height, :, :] = array
    previous = review.LABEL_SCALE
    review.LABEL_SCALE = LABEL_SCALE
    try:
        for index, line in enumerate(lines[:2]):
            review.draw_label(
                canvas, line, 12, 8 + index * (7 + 2) * LABEL_SCALE
            )
    finally:
        review.LABEL_SCALE = previous
    review.save_rgba(canvas, destination)


def blind_letters(theme):
    """Stable but not guessable from the angle order."""
    digest = hashlib.sha256(f"opus5-m2c-{theme}".encode()).digest()[0]
    return ("A", "B") if digest % 2 == 0 else ("B", "A")


def render_theme(project_root, theme, angles):
    directory = project_root / "ArtSource/Blender/BrushUp/Opus5" / theme / "review"
    directory.mkdir(parents=True, exist_ok=True)
    compact_letter, conservative_letter = blind_letters(theme)
    letters = {"compact": compact_letter, "conservative": conservative_letter}
    manifest = {"blind_assignment": letters, "images": {}}

    review.configure_scene()
    for variant in ("production", "compact", "conservative"):
        half = angles.get(variant)
        for view_name, view in VIEWS.items():
            state = build_render_state(project_root, theme, variant, half)
            review.configure_scene()
            plain = directory / f"{PREFIX}_{variant}_{view_name}.png"
            render_view(state, theme, view, plain)
            caption = (
                variant.upper()
                if half is None
                else f"{variant} +-{half} DEG".upper()
            )
            labelled = directory / f"{PREFIX}_{variant}_{view_name}_labelled.png"
            label_copy(
                plain,
                labelled,
                [caption, f"{theme} {view_name.replace('_', ' ')}".upper()],
            )
            entry = {
                "unlabelled": str(plain.relative_to(project_root)),
                "labelled": str(labelled.relative_to(project_root)),
            }
            if variant in letters:
                blind = directory / f"{PREFIX}_blind_{letters[variant]}_{view_name}.png"
                blind.write_bytes(plain.read_bytes())
                entry["blind"] = str(blind.relative_to(project_root))
            manifest["images"][f"{variant}/{view_name}"] = entry
    return manifest


def recommend(theme, variants):
    compact, conservative = variants["compact"], variants["conservative"]
    if not compact["contract"]["all_pass"]:
        return {
            "variant": "conservative",
            "reason": "compact does not meet the contract",
        }
    compact_margin = compact["minimum_surface_separation"].get(
        "minimum_separation_mm"
    )
    conservative_margin = conservative["minimum_surface_separation"].get(
        "minimum_separation_mm"
    )
    slivers = [
        name
        for name, entry in (("compact", compact), ("conservative", conservative))
        if entry["facet_alignment"].get("sliver")
    ]
    if slivers == ["compact"]:
        return {
            "variant": "conservative",
            "slot_half_angle_deg": conservative["slot_half_angle_deg"],
            "reason": (
                "both meet the contract, but the compact cut stops "
                f"{compact['facet_alignment']['residual_fragment_deg']} deg "
                "short of a facet corner and leaves a sliver of facet at the "
                "opening; the conservative cut does not"
            ),
            "caveat": "the visual call is Codex's on the renders",
        }
    return {
        "variant": "compact",
        "slot_half_angle_deg": compact["slot_half_angle_deg"],
        "reason": (
            "both meet the contract, so the smaller opening is preferred: it "
            "removes less of the theme's ring silhouette while keeping a "
            f"clearance of {compact_margin} mm against "
            f"{conservative_margin} mm, and neither cut leaves a facet sliver"
        ),
        "caveat": (
            "a geometry argument only; the visual call between the two "
            "openings is Codex's on the renders"
        ),
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    gate = m1.preflight(project_root)

    started = time.perf_counter()
    themes = {}
    for theme in args.themes or VARIANTS:
        begin = time.perf_counter()
        angles = VARIANTS[theme]
        baseline_lip, baseline_health, _ = baseline_measurements(project_root, theme)
        variants = {
            name: measure_variant(project_root, theme, name, half, baseline_lip)
            for name, half in angles.items()
        }
        manifest = (
            {"skipped": True}
            if args.skip_renders
            else render_theme(project_root, theme, angles)
        )
        themes[theme] = {
            "source": str(source_blend(project_root, theme).relative_to(project_root)),
            "sha256": m1.digest(source_blend(project_root, theme)),
            "production_baseline": {
                "lip_by_pose": baseline_lip,
                "mesh_health": baseline_health,
            },
            "variants": variants,
            "renders": manifest,
            "recommendation": recommend(theme, variants),
        }
        print(
            f"[Opus5SlotM2c] {theme}: compact +-{angles['compact']} "
            f"{variants['compact']['contract']['all_pass']} sep "
            f"{variants['compact']['minimum_surface_separation'].get('minimum_separation_mm')} mm | "
            f"conservative +-{angles['conservative']} "
            f"{variants['conservative']['contract']['all_pass']} sep "
            f"{variants['conservative']['minimum_surface_separation'].get('minimum_separation_mm')} mm | "
            f"{round(time.perf_counter() - begin, 1)}s"
        )

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2c",
                "note": (
                    "Read-only visual selection (alignment 100.4). Slots are "
                    "cut from production ring copies with an EXACT Boolean; "
                    "no Blend is saved and no candidate is published."
                ),
                "proxy_status": (
                    "lip overlap is a mechanical-plausibility geometry proxy, "
                    "not a retention-force guarantee (alignment 98.1)"
                ),
                "preflight": gate,
                "variants_offered": VARIANTS,
                "views": VIEWS,
                "themes": themes,
                "contract_summary": {
                    theme: {
                        name: entry["contract"]["all_pass"]
                        for name, entry in payload["variants"].items()
                    }
                    for theme, payload in themes.items()
                },
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[Opus5SlotM2c] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
