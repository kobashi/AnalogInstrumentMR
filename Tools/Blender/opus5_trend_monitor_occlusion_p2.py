"""Trend Monitor P2: a real aperture in the front plate.

Alignment 256. On Quest the numbers and traces show on Kinetic Safety but not
on Forge Brass or Orbital Analog. Codex's ray diagnosis found `static_opaque`
in front of `display_surface` by 9 and 10 mm on those two themes.

The cause is in the P1 generator: `housing` is a solid slab spanning the whole
body outline from z = 0 to the body depth, and the screen plane sits at
bezel_front - DISPLAY_RECESS, which for those two themes falls *inside* that
slab. Kinetic Safety escapes only because its shroud pushes the bezel - and so
the screen - past the housing's front face.

The fix is the one alignment 256.2 asks for: cut a window in the front plate
rather than floating the screen forward. The housing becomes a closed back slab
plus a front frame whose opening clears the display, so from the front the
first thing a ray meets over the screen is `display_surface`.

P1 is not touched. The generator is imported and its `slab` is wrapped for the
one call that builds the housing; nothing is written back to it, and the P1
Blend, FBX, hashes and script keep their own names.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_trend_monitor_occlusion_p2.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_trend_monitor_prototype as p1
import opus5_trend_monitor_themes as t2

# Forge Brass and Orbital Analog only. Kinetic Safety is the read-only baseline
# alignment 256.2(6) fixes, and is neither rebuilt nor re-exported here.
TARGETS = ("ForgeBrass", "OrbitalAnalog")
BASELINE = "KineticSafety"

# The window clears the display (0.368 x 0.188) and stays inside the bezel
# opening (0.372 x 0.192), so the bezel still overlaps the aperture edge and
# the screen still reads as housed rather than applied.
APERTURE = (0.370, 0.190)
# The closed back sits this far behind the screen: enough that the screen is
# unambiguously the first hit, small enough that the cavity reads as a recess.
BACK_CLEARANCE = 0.002

OUTPUT = "ArtSource/Blender/BrushUp/Opus5/trend_monitor_occlusion_p2.json"
# Screen centre, both numeric fields and the graph band, as alignment 256.1
# sampled them, plus the four display corners for coverage.
SAMPLES = {
    "screen_centre": (0.0, 0.0),
    "numeric_left": (-0.12, 0.07),
    "numeric_right": (0.12, 0.07),
    "graph_band": (0.0, -0.04),
    "corner_lower_left": (-0.175, -0.085),
    "corner_upper_right": (0.175, 0.085),
}

STATE = {"screen_z": None}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def screen_z_for(spec):
    """Where build_theme will put the screen, computed the same way it does."""
    front = spec["body_depth"]
    shroud = spec.get("shroud")
    if shroud:
        front += shroud["depth"]
    return front + spec["bezel_depth"] - t2.DISPLAY_RECESS


def merged(name, meshes):
    """Join meshes into one, carrying the material with them.

    A fresh mesh datablock has no material slots, so merging without copying
    them leaves the housing unshaded - it rendered white against the theme
    while every other part kept its colour.
    """
    work = bmesh.new()
    for mesh in meshes:
        work.from_mesh(mesh)
    out = bpy.data.meshes.new(name)
    work.to_mesh(out)
    work.free()
    for material in meshes[0].materials:
        out.materials.append(material)
    for mesh in meshes:
        bpy.data.meshes.remove(mesh)
    return out


ORIGINAL_SLAB = p1.slab


def housing_with_window(name, outline, near_z, far_z, material):
    """The housing gains a window; every other slab is built as before."""
    if name != "housing":
        return ORIGINAL_SLAB(name, outline, near_z, far_z, material)
    split = STATE["screen_z"] - BACK_CLEARANCE
    back = ORIGINAL_SLAB("housing_back", outline, near_z, split, material)
    aperture = p1.rounded_rectangle(APERTURE[0], APERTURE[1],
                                    t2.OPENING[0] * 0.0 + 0.010,
                                    p1.CORNER_SEGMENTS)
    window = p1.frame("housing_window", outline, aperture, split, far_z, material)
    return merged(name, [back, window])


def first_hit(root, x, y, direction):
    """Which object a ray from outside the instrument meets first."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    start = Vector((x, y, 1.0 if direction > 0 else -1.0))
    ray = Vector((0.0, 0.0, -1.0 if direction > 0 else 1.0))
    hit, location, _, _, obj, _ = bpy.context.scene.ray_cast(depsgraph, start, ray)
    if not hit:
        return {"hit": False}
    return {"hit": True, "object": obj.name, "z": round(location.z, 6)}


def hit_sequence(x, y):
    """Front-side hits in order, so the report can show what is behind what."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    z = 1.0
    order = []
    for _ in range(6):
        hit, location, _, _, obj, _ = bpy.context.scene.ray_cast(
            depsgraph, Vector((x, y, z)), Vector((0.0, 0.0, -1.0)))
        if not hit:
            break
        order.append({"object": obj.name, "z": round(location.z, 6)})
        z = location.z - 1e-5
        if z < -0.05:
            break
    return order


def verify(theme, root):
    rows = {}
    passed = True
    for label, (x, y) in SAMPLES.items():
        order = hit_sequence(x, y)
        front = order[0]["object"] if order else None
        ok = front == "display_surface"
        passed &= ok
        rows[label] = {"point": [x, y], "front_first_hit": front,
                       "sequence": order, "display_surface_first": ok}
    back = first_hit(root, 0.0, 0.0, -1)
    rows["from_behind"] = {
        "first_hit": back.get("object"),
        "display_surface_hidden": back.get("object") != "display_surface",
    }
    passed &= rows["from_behind"]["display_surface_hidden"]
    return rows, passed


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    payload = {
        "phase": "TrendMonitor-P2",
        "note": ("A window in the front plate so display_surface is the first "
                 "front-side hit. Alignment 256. P1 is not modified."),
        "aperture_m": list(APERTURE),
        "back_clearance_m": BACK_CLEARANCE,
        "baseline_untouched": BASELINE,
        "themes": {},
    }

    p1.slab = housing_with_window
    try:
        for theme in TARGETS:
            spec = t2.THEMES[theme]
            STATE["screen_z"] = screen_z_for(spec)
            root, display, screen_z = t2.build_theme(theme, spec)
            bpy.context.view_layer.update()

            rows, passed = verify(theme, root)
            report = p1.measure(root, display)
            tree = (project_root / "ArtSource/Blender/BrushUp/Opus5"
                    / theme / "TrendMonitor")
            review_dir = tree / "review"
            review_dir.mkdir(parents=True, exist_ok=True)
            blend = tree / f"BL_TrendMonitor_{theme}_V6_Opus5_P2_Retopo.blend"
            fbx = tree / f"SM_TrendMonitor_{theme}_V6_Opus5_P2.fbx"
            bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
            t2.export(root, fbx)

            review.configure_scene()
            images = {}
            for name, view in p1.VIEWS.items():
                path = review_dir / f"Preview_TrendMonitor_{theme}_P2_{name}.png"
                p1.shot((0.0, 0.0, 0.03), 0.78, view, 55.0, 0.30, path)
                images[name] = str(path.relative_to(project_root))

            payload["themes"][theme] = {
                "screen_z_m": round(screen_z, 6),
                "occlusion": rows,
                "occlusion_passed": passed,
                "geometry": report,
                "blend": str(blend.relative_to(project_root)),
                "blend_sha256": m1.digest(blend),
                "fbx": str(fbx.relative_to(project_root)),
                "fbx_sha256": m1.digest(fbx),
                "fbx_bytes": fbx.stat().st_size,
                "images": images,
            }
            print(f"[TrendMonitorP2] {theme}: screen_z {screen_z:.4f}, "
                  f"occlusion {'PASS' if passed else 'FAIL'}")
    finally:
        p1.slab = ORIGINAL_SLAB

    payload["all_passed"] = all(row["occlusion_passed"]
                                for row in payload["themes"].values())
    payload["status"] = ("p2_candidate_ready" if payload["all_passed"]
                         else "occlusion_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[TrendMonitorP2] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
