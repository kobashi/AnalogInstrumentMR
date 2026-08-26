"""Theme 4 fastener access R1 delivery: the 315 audit, the fixes, the proof.

Writes only to delivery_p6/fastener_access_r1/**. Every existing delivery
tree, Assets, Builds, docs and git are read-only or untouched.

What ships:

* the whole-of-Theme-4 fastener census - 11 accepted candidates plus the one
  that has no Theme 4 build at all, recorded as zero rather than skipped
* the two 315 defects fixed: the rotary's blank nameplate deleted, and every
  screw a shell was standing in front of moved onto that shell's front face
* the two cases a fastener move cannot fix, with the measurement that says so
  and a proposal, which is what 315.5 asks for when a hole is unnatural
* tool proxy renders at both radii, before/after, and the geometry gates rerun

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_fastener_access_r1_delivery.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_delivery_p4 as p4d
import opus5_theme4_material_p2 as m2
import opus5_theme4_full_p6_batch_b as bb
import opus5_theme4_full_p6_batch_b_r1 as br1
import opus5_theme4_full_p6_batch_b_r2 as br2
import opus5_theme4_full_p6_batch_b_r1_delivery as r1d
import opus5_theme4_fastener_access_r1 as fa

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/fastener_access_r1")
OUTPUT = f"{TREE}/theme4_fastener_access_r1.json"
EXPORTED = ("Rotary", "Button", "Lamp", "StatusIndicator", "Toggle", "Lever")
PROXY_COLOUR = (0.95, 0.42, 0.10, 1.0)
AXIS_COLOUR = (0.20, 0.78, 0.95, 1.0)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def build(asset, builder, materials=None, overrides=None,
          drop_nameplate=False):
    """One build path for every instrument: tag, capture, normalise."""
    p1.clear_scene()
    review.configure_scene()
    roles = materials() if materials else None
    fa.OVERRIDES.clear()
    if overrides:
        fa.OVERRIDES.update(overrides)
    saved = fa.install_overrides(asset, drop_nameplate)
    original_join, original_assign = p1.join, p1.assign
    captured, tagged = {}, {}

    def hook(target, others):
        for obj in [target] + list(others):
            if obj is None:
                continue
            stem = obj.name.split(".")[0]
            tris = br1.world_triangles(obj)
            if len(tris):
                captured.setdefault(stem, []).append(tris)
            if roles is not None:
                role = r1d.role_for(obj.name)
                tagged[stem] = role
                obj.data.materials.clear()
                obj.data.materials.append(roles[role])
        return original_join(target, others)

    def assign(obj, material):
        if roles is not None and not obj.data.materials:
            role = r1d.role_for(obj.name)
            tagged[obj.name.split(".")[0]] = role
            obj.data.materials.append(roles[role])
        elif roles is None:
            original_assign(obj, material)

    p1.join, p1.assign = hook, assign
    try:
        body, mover, movers, audit = builder(
            roles["body"] if roles else p1.proto.make_material("m", bb.NEUTRAL))
    finally:
        p1.join, p1.assign = original_join, original_assign
        fa.remove_overrides(saved)
        fa.OVERRIDES.clear()
    movers = list(movers) if isinstance(movers, (list, tuple)) else [movers]
    # The root is made after the build, not before: Batch A's proposal path
    # clears the scene on its way in and would take a pre-made root with it.
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    for obj in (body, mover):
        if obj is not None:
            obj.parent = root
    bpy.context.view_layer.update()
    parts = {name: np.concatenate(rows) for name, rows in captured.items()}
    return root, body, mover, movers, audit, parts


def proxy_cylinder(name, axis_xz, start_y, radius, length, colour, alpha=0.4):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=length, vertices=28,
        location=(axis_xz[0], start_y - length / 2.0, axis_xz[1]),
        rotation=(math.pi / 2.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    material = bpy.data.materials.new(f"REVIEW_{name}")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = colour
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = colour
            bsdf.inputs["Emission Strength"].default_value = 0.7
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
    obj.data.materials.append(material)
    return obj


def proxy_images(asset, rows, focus, radius, scale, out_dir, prefix,
                 project_root, reach=fa.TOOL_REACH):
    """315.7: the driver shaft and its working clearance, drawn."""
    made = []
    for index, row in enumerate(rows):
        cx, start_y, cz = row["head_centre_m"]
        made.append(proxy_cylinder(f"clear_{index}", (cx, cz), start_y,
                                   fa.TOOL_CLEAR_R, reach, PROXY_COLOUR, 0.28))
        made.append(proxy_cylinder(f"shaft_{index}", (cx, cz), start_y,
                                   fa.TOOL_SHAFT_R, reach, AXIS_COLOUR, 0.85))
    bpy.context.view_layer.update()
    images = {}
    for label, view in (("front", (0.0, 0.0)), ("oblique", (36.0, 20.0)),
                        ("side", (78.0, 6.0))):
        path = out_dir / f"{prefix}_tool_{label}.png"
        p1.shot(focus, radius * 1.35, view, 52.0, scale * 1.35, path)
        images[f"tool_{label}"] = str(path.relative_to(project_root))
    for obj in made:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()
    return images


def gates_for(asset, root, body, mover, movers, audit):
    """Only the Theme 4 assets Batch A/B measure have a contract row."""
    if asset in bb.CONTRACT:
        measured = bb.measure_asset(asset, root, body, mover, movers)
        statics = bb.snapshot_statics([body])
        clearance = bb.motion_clearance_audit(mover, movers, statics, asset)
        return measured, clearance
    meshes = [body] + [obj for obj in movers if obj is not None]
    triangles = 0
    for obj in meshes:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return ({"triangles_total": triangles, "renderers": len(meshes),
             "renderer_budget": None, "gates": {},
             "note": ("no Batch A/B contract row: this asset is gated on its "
                      "triangle count not changing, not on Batch B's budget")},
            None)


def preserved_audits(asset, body, mover, movers, parts, focus, half_extent):
    """The 315.6 promise, measured: what already passed still passes."""
    if asset == "Rotary":
        return {"grip_311_2": br1.rotary_finger_audit(
            body, movers[0], collar_y=br1.ROTARY_COLLAR_Y)}
    if asset == "Button":
        return {"press_311_3": br1.button_finger_audit(
            body, movers[0], mover, guard_y=br1.BUTTON_GUARD_Y)}
    if asset == "Lamp":
        return {"proportion_311_4": br1.lamp_proportion_audit(
            parts, movers[0], focus, half_extent, 480)}
    if asset == "StatusIndicator":
        return {"alignment_312_5": br1.status_alignment_audit(
            parts, movers, focus, half_extent, 480)}
    return {}


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in
            ("before", "after", "tool", "blend", "state")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-fastener-access-R1",
        "alignment": "315",
        "standard": {
            "shaft_radius_mm": fa.TOOL_SHAFT_R * 1000.0,
            "working_clearance_radius_mm": fa.TOOL_CLEAR_R * 1000.0,
            "straight_reach_mm": fa.TOOL_REACH * 1000.0,
            "access_hole_min_diameter_mm": fa.ACCESS_HOLE_D * 1000.0,
            "accept": "both proxies hit zero triangles",
            "method": ("the swept cylinder is sampled as spheres every 1 mm "
                       "and tested against every triangle in the instrument "
                       "except the fastener itself; the first sample stands "
                       "0.2 mm off the head so the screw never blocks its own "
                       "path"),
        },
        "roster": [{"asset": name, "source": source} for name, source, _
                   in fa.ROSTER]
        + [{"asset": name, "source": "absent", "fastener_count": 0,
            "reason": reason} for name, reason in fa.ABSENT],
        "instruments": {},
        "proposals": [],
    }

    census_before, census_after = 0, 0
    pass_before, pass_after = 0, 0
    table = []

    for asset, source, builder in fa.ROSTER:
        # --- before
        # Only what ships goes through the atlas pipeline. The rest is a
        # read-only audit, and Batch A's builders tag their own materials -
        # running a second tagger over them frees datablocks under their feet.
        wanted = asset in EXPORTED
        root, body, mover, movers, audit, parts = build(
            asset, builder, materials=m2.make_materials if wanted else None)
        meshes = [body] + [obj for obj in movers if obj is not None]
        if wanted:
            r1d.dress(meshes, textures)
        focus, radius, scale = p1.rig_for(meshes)
        half_extent = radius * 0.34
        before = fa.audit_instrument(asset, source, parts, movers)
        before_measured, before_clearance = gates_for(
            asset, root, body, mover, movers, audit)
        census_before += before["fastener_count"]
        pass_before += sum(1 for row in before["fasteners"] if row["pass"])

        review.configure_scene()
        before_images = {}
        for label, view in p1.VIEWS.items():
            path = dirs["before"] / f"Before_{asset}_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            before_images[label] = str(path.relative_to(project_root))
        before_images.update(proxy_images(
            asset, before["fasteners"], focus, radius, scale, dirs["tool"],
            f"Before_{asset}", project_root))

        # Covered, or actually inside the solid? The ray answers it, and the
        # answer changes what the fix has to be.
        for entry in before["fasteners"]:
            if entry["pass"]:
                continue
            cx, hy, cz = entry["head_centre_m"]
            names = sorted(entry.get("blockers", {}))
            if not names:
                continue
            blocker = np.concatenate([parts[name] for name in names
                                      if name in parts])
            entry["enclosure"] = fa.enclosed_in(blocker, (cx, cz), hy)
            entry["enclosure"]["parts"] = names

        row = {
            "source": source,
            "fastener_count_before": before["fastener_count"],
            "fasteners_before": before["fasteners"],
            "triangles_before": before_measured["triangles_total"],
            "images_before": before_images,
            "modified": asset in fa.FIXES or asset in fa.NAMEPLATE_REMOVED,
        }

        # --- the two cases a fastener move cannot fix
        if asset in ("MeterMedium", "MeterLarge", "Rotary"):
            housing = parts["housing" if asset == "Rotary"
                            else f"{asset}_housing"]
            enclosure = {}
            for entry in before["fasteners"]:
                cx, hy, cz = entry["head_centre_m"]
                enclosure[entry["fastener"]] = fa.enclosed_in(
                    housing, (cx, cz), hy)
            seat = fa.SEAT_RADIUS[asset]
            lip = {"MeterMedium": (0.1445, 0.1505),
                   "MeterLarge": (0.2215, 0.2330),
                   "Rotary": (0.0530, 0.0649)}[asset]
            count = {"Rotary": "three"}.get(asset, "six")
            payload["proposals"].append({
                "asset": asset,
                "fasteners": [entry["fastener"] for entry in
                              before["fasteners"]],
                "finding": (
                    f"the {count} screws are not merely covered - they are inside "
                    "the housing solid of revolution, between its front and "
                    "back surfaces on their own axis, so they are invisible "
                    "from every direction and no tool path to them can exist"),
                "enclosure": enclosure,
                "only_flat_front_land": {
                    "name": "bezel lip ring",
                    "inner_radius_m": lip[0], "outer_radius_m": lip[1],
                    "width_mm": round((lip[1] - lip[0]) * 1000.0, 1),
                    "seat_radius_mm": round(seat * 1000.0, 1),
                    "seat_needs_width_mm": round(seat * 2000.0, 1),
                },
                "proposal": (
                    "delete them, as 315.1 deletes the rotary's "
                    "blank nameplate: they carry no silhouette, no shading "
                    "and no function, and they cost triangles inside a "
                    "solid. If they are to stay, the only flat front land is "
                    "the bezel ring, and it is narrower than the clearance "
                    "plus one seat, so the head would have to shrink as well "
                    "as move - a visual change 315.6 freezes."),
                "land_short_by_mm": round(
                    (fa.TOOL_CLEAR_R + seat) * 1000.0
                    - (lip[1] - lip[0]) * 1000.0, 1),
                "applied": False,
                "applied_reason": (
                    "315.1 authorises deleting one named nameplate, not "
                    "screws, and 315.6 freezes geometry outside holes and "
                    "fastener positions"),
            })

        # --- after
        overrides = fa.fix_positions(asset, before["fasteners"])
        if row["modified"]:
            root, body, mover, movers, audit, parts = build(
                asset, builder, materials=m2.make_materials,
                overrides=overrides,
                drop_nameplate=asset in fa.NAMEPLATE_REMOVED)
            meshes = [body] + [obj for obj in movers if obj is not None]
            packing = r1d.dress(meshes, textures)
            after = fa.audit_instrument(asset, source, parts, movers)
            measured, clearance = gates_for(asset, root, body, mover, movers,
                                            audit)
            preserved = preserved_audits(asset, body, mover, movers, parts,
                                         focus, half_extent)
            residue = fa.nameplate_residue() if asset in fa.NAMEPLATE_REMOVED \
                else None

            review.configure_scene()
            after_images = {}
            for label, view in p1.VIEWS.items():
                path = dirs["after"] / f"After_{asset}_{label}.png"
                p1.shot(focus, radius, view, 52.0, scale, path)
                after_images[label] = str(path.relative_to(project_root))
            after_images.update(proxy_images(
                asset, after["fasteners"], focus, radius, scale, dirs["tool"],
                f"After_{asset}", project_root))

            fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_FA_R1.fbx"
            d2.export_fbx(root, fbx)
            blend = dirs["blend"] / f"{asset}_{THEME}_FA_R1.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)

            if not measured["gates"]:
                measured["gates"] = {
                    "triangles_unchanged": measured["triangles_total"]
                    == before_measured["triangles_total"]}
            row.update({
                "change": ("plate_label deleted"
                           if asset in fa.NAMEPLATE_REMOVED else "")
                + ("; " if asset in fa.NAMEPLATE_REMOVED
                   and asset in fa.FIXES else "")
                + (f"screws moved to the {fa.FIXES[asset]['land']}, radial "
                   f"shift {fa.FIXES[asset]['radial_shift_m'] * 1000.0:+.1f} mm"
                   if asset in fa.FIXES else ""),
                "fix_rule": fa.FIXES.get(asset),
                "fastener_moves": [
                    {"fastener": name, "to_xz_m": list(centre),
                     "to_face_y_m": face}
                    for (owner, name), (centre, face) in overrides.items()],
                "fasteners_after": after["fasteners"],
                "pass_after": after["pass"],
                "triangles_after": measured["triangles_total"],
                "triangle_delta": measured["triangles_total"]
                - before_measured["triangles_total"],
                "renderers": measured["renderers"],
                "renderer_budget": measured.get("renderer_budget"),
                "gates": measured["gates"],
                "coplanar_overlap": audit,
                "clearance": clearance,
                "objects": packing,
                "submeshes_total": sum(r["submeshes"] for r in
                                       packing.values()),
                "max_material_slots_per_object": max(
                    len(r["material_slots"]) for r in packing.values()),
                "preserved_audits": preserved,
                "nameplate_residue": residue,
                "images_after": after_images,
                "fa_fbx": str(fbx.relative_to(project_root)),
                "fa_fbx_sha256": m1.digest(fbx),
                "fa_blend": str(blend.relative_to(project_root)),
            })
            census_after += after["fastener_count"]
            pass_after += sum(1 for entry in after["fasteners"]
                              if entry["pass"])
            after_rows = {entry["fastener"]: entry
                          for entry in after["fasteners"]}
        else:
            census_after += before["fastener_count"]
            pass_after += sum(1 for entry in before["fasteners"]
                              if entry["pass"])
            after_rows = {entry["fastener"]: entry
                          for entry in before["fasteners"]}

        for entry in before["fasteners"]:
            done = after_rows.get(entry["fastener"], entry)
            table.append({
                "asset": asset,
                "fastener": entry["fastener"],
                "head_centre_m": entry["head_centre_m"],
                "driver_axis": entry["driver_axis"],
                "approach_side": entry["approach_side"],
                "before": "PASS" if entry["pass"] else "FAIL",
                "blockers": sorted(entry.get("blockers", {})),
                "after": "PASS" if done["pass"] else "FAIL",
                "verdict": ("PASS" if entry["pass"] and done["pass"]
                            else "fixed" if done["pass"]
                            else "FAIL"),
                "shaft_hits_after": done["shaft_triangle_hits"],
                "clearance_hits_after": done["clearance_triangle_hits"],
                "head_centre_after_m": done["head_centre_m"],
            })

        payload["instruments"][asset] = row
        print(f"[FA-R1] {asset}: {before['fastener_count']} fasteners, "
              f"before {sum(1 for e in before['fasteners'] if e['pass'])} pass, "
              f"after {sum(1 for e in after_rows.values() if e['pass'])} pass"
              + (f", tris {row.get('triangles_after')}" if row["modified"]
                 else ""))

    for name, reason in fa.ABSENT:
        payload["instruments"][name] = {
            "source": "absent", "fastener_count_before": 0,
            "fasteners_before": [], "modified": False, "reason": reason}

    # The alternative to deleting the rotary's three, if they are to stay.
    payload["proposals"].append({
        "asset": "Rotary",
        "fasteners": ["screw_0", "screw_1", "screw_2"],
        "option": "keep the screws, widen the land",
        "finding": (
            "if the three are to stay rather than be deleted, the bezel's "
            "only flat front land runs from the collar's outer radius 0.0530 "
            "to the drum edge 0.0649 - 11.9 mm. A compliant seat needs 8.2 mm "
            "of clearance plus its own 4.6 mm radius, 12.8 mm, so the land is "
            "0.9 mm too narrow and the best clearance any legal seat on it "
            "can reach is 7.85 mm against the 8.2 mm standard"),
        "measured": {"land_width_mm": 11.9, "required_mm": 12.8,
                     "best_achievable_clearance_mm": 7.85,
                     "standard_mm": fa.TOOL_CLEAR_R * 1000.0,
                     "short_by_mm": 0.35},
        "proposal": (
            "take the collar's outer radius from 0.0530 to 0.0500. The bore "
            "0.0472 and the front plane -0.0620 do not move, so every number "
            "311.2 and 312 accepted - proxy clearance 3.71 mm, grippable side "
            "17.0 mm, zero guard intersections - is untouched, and the bezel "
            "land becomes 14.9 mm, enough for a seat at radius 0.0592 with "
            "1.0 mm of clearance margin"),
        "applied": False,
        "applied_reason": (
            "thinning the collar wall is instrument geometry, which 315.6 "
            "freezes; it needs Codex's decision, not mine"),
    })

    payload["census"] = {
        "instruments_audited": len(fa.ROSTER),
        "instruments_absent": [name for name, _ in fa.ABSENT],
        "fasteners_total": census_before,
        "pass_before": pass_before,
        "fail_before": census_before - pass_before,
        "pass_after": pass_after,
        "fixed": pass_after - pass_before,
        "still_failing": census_before - pass_after,
    }
    payload["table"] = table
    payload["textures"] = {
        name: {"path": str(path.relative_to(project_root)),
               "sha256": m1.digest(path), "bytes": path.stat().st_size}
        for name, path in textures.items()}
    modified = [asset for asset in EXPORTED
                if payload["instruments"][asset].get("modified")]
    proposed = {row["asset"] for row in payload["proposals"]}
    unexplained = sorted({row["asset"] for row in table
                          if row["after"] == "FAIL"} - proposed)
    payload["still_failing_without_a_proposal"] = unexplained
    payload["status"] = (
        "fastener_access_r1_ready_with_proposals"
        if not unexplained
        and all(all(payload["instruments"][asset]["gates"].values())
                for asset in modified)
        and all(payload["instruments"][asset]["clearance"] is None
                or payload["instruments"][asset]["clearance"]["clean"]
                for asset in modified)
        and not payload["instruments"]["Rotary"]["nameplate_residue"]["objects"]
        and not payload["instruments"]["Rotary"]["nameplate_residue"]["meshes"]
        else "fastener_access_r1_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[FA-R1] census {census_before} fasteners, {pass_before} -> "
          f"{pass_after} passing; status {payload['status']}")


if __name__ == "__main__":
    main()
