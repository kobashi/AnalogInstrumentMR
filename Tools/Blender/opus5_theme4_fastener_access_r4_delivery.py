"""Theme 4 fastener access R4 delivery: Lever and Toggle only.

Writes only to delivery_p6/fastener_access_r4/**. R3's meters and rotary, R1's
button, lamp and status indicator, and the four P4 atlas PNGs are referenced by
digest and never rebuilt.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_fastener_access_r4_delivery.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_contact_migration_m1 as m1
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_delivery_p2 as d2
import opus5_theme4_delivery_p4 as p4d
import opus5_theme4_full_p6_batch_a_r4_b3u as b3u
import opus5_theme4_fastener_access_r1 as fa
import opus5_theme4_fastener_access_r2_delivery as r2d
import opus5_theme4_fastener_access_r3 as r3
import opus5_theme4_fastener_access_r4 as r4

THEME = "MachinedErgonomics"
BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
TREE = f"{BASE}/fastener_access_r4"
OUTPUT = f"{TREE}/theme4_fastener_access_r4.json"
R1_TREE = f"{BASE}/fastener_access_r1"
R3_TREE = f"{BASE}/fastener_access_r3"
CARRIED_R1 = ("Button", "Lamp", "StatusIndicator")
CARRIED_R3 = ("MeterMedium", "MeterLarge", "Rotary")


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def builder_for(asset):
    return next(builder for name, _, builder in fa.ROSTER if name == asset)


def source_for(asset):
    return next(source for name, source, _ in fa.ROSTER if name == asset)


def signature_from_fbx(path):
    rows, hierarchy = b3u.read_fbx(path)
    out = {}
    for name, row in rows.items():
        positions = row["unique_positions"]
        out[name] = {
            "triangles": row["triangles"],
            "bounds_min": row["bounds_min"],
            "bounds_max": row["bounds_max"],
            "position_count": len(positions),
            "position_digest": hashlib.sha256(
                repr(positions).encode("utf-8")).hexdigest(),
            "materials": row["materials"],
        }
    return {"objects": out, "hierarchy": hierarchy}


def render_set(meshes, focus, radius, scale, out_dir, prefix, project_root):
    review.configure_scene()
    images = {}
    for label, view in p1.VIEWS.items():
        path = out_dir / f"{prefix}_{label}.png"
        p1.shot(focus, radius, view, 52.0, scale, path)
        images[label] = str(path.relative_to(project_root))
    return images


def set_normal_maps(meshes, enabled):
    """Turn the Normal map on or off on every material these meshes use.

    Done through the Normal Map node's Strength rather than by unlinking:
    `link.to_socket` hands back a fresh RNA wrapper on every access, so an
    identity test against the BSDF socket never matches and the first attempt
    at this silently changed nothing - both renders came out identical and the
    knurl test passed while proving nothing.
    """
    touched = 0
    for obj in meshes:
        for slot in obj.material_slots:
            material = slot.material
            if material is None or not material.use_nodes:
                continue
            for node in material.node_tree.nodes:
                if node.type != "NORMAL_MAP":
                    continue
                node.inputs["Strength"].default_value = 1.0 if enabled else 0.0
                touched += 1
    bpy.context.view_layer.update()
    return touched


def isolate_render(meshes, keep, focus, radius, scale, path):
    """Render only `keep`, so a difference is about that object alone."""
    hidden = []
    for obj in meshes:
        if obj not in keep:
            obj.hide_render = True
            hidden.append(obj)
    bpy.context.view_layer.update()
    p1.shot(focus, radius, (0.0, 0.0), 52.0, scale, path)
    for obj in hidden:
        obj.hide_render = False
    bpy.context.view_layer.update()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in ("p5", "r4", "closeup", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-fastener-access-R4",
        "alignment": "321",
        "note": ("Lever and Toggle only. The UV comes back off the P5 FBX "
                 "triangle by triangle, and the toggle's four screws move "
                 "onto the one surface on that instrument that faces the "
                 "driver, because R1 had put them 11.09 mm off the shell's "
                 "corner chamfer with nothing under them."),
        "frozen_trees": [R1_TREE, R3_TREE, f"{BASE}/../delivery_p5"],
        "uv_reference": r4.REFERENCE,
        "position_match_tolerance_mm": r3.POSITION_TOLERANCE * 1000.0,
        "match_method": ("object name, then a triangle keyed by the set of "
                         "its three vertex positions snapped through a "
                         "KD-tree; a relocated screw is matched by adding the "
                         "vector back to its P5 head centre. Face order and "
                         "loop order are never used."),
        "knurl_patch_uv": [round(v, 6) for v in p4d.REGIONS["knurl"]],
        "instruments": {},
        "carried_unchanged": {},
    }

    r1_payload = json.loads(
        (project_root / f"{R1_TREE}/theme4_fastener_access_r1.json").read_text())
    r3_payload = json.loads(
        (project_root / f"{R3_TREE}/theme4_fastener_access_r3.json").read_text())
    for asset in CARRIED_R1:
        row = r1_payload["instruments"][asset]
        path = project_root / row["fa_fbx"]
        payload["carried_unchanged"][asset] = {
            "regenerated": False, "tree": R1_TREE, "fbx": row["fa_fbx"],
            "sha256_now": m1.digest(path),
            "sha256_recorded": row["fa_fbx_sha256"],
            "matches": m1.digest(path) == row["fa_fbx_sha256"]}
    for asset in CARRIED_R3:
        row = r3_payload["instruments"][asset]["states"]["r3"]
        path = project_root / row["fbx"]
        payload["carried_unchanged"][asset] = {
            "regenerated": False, "tree": R3_TREE, "fbx": row["fbx"],
            "sha256_now": m1.digest(path),
            "sha256_recorded": row["fbx_sha256"],
            "matches": m1.digest(path) == row["fbx_sha256"]}

    for asset in r4.TARGETS:
        reference_path = r4.REFERENCE[asset]
        reference = r3.read_reference(project_root / reference_path)

        # Pristine build: the P5 fastener positions, and the audit R1 derived
        # its relocation from.
        _, _, _, movers0, _, parts0 = r2d.build(
            asset, builder_for(asset), "r1", materials=False)
        pristine = fa.audit_instrument(asset, source_for(asset), parts0,
                                       movers0)
        overrides = r4.overrides_for(asset, pristine["fasteners"])

        states = {}
        for label, use_overrides in (("p5", False), ("r4", True)):
            root, body, mover, movers, audit, parts = r2d.build(
                asset, builder_for(asset), "r1",
                overrides=overrides if use_overrides else None,
                materials=True)
            meshes = [body] + [obj for obj in movers if obj is not None]
            packing = r2d.dress(asset, meshes, textures)
            current = fa.audit_instrument(asset, source_for(asset), parts,
                                          movers)
            shifts = r4.screw_offsets(parts0, parts)
            offsets = [("common", (0.0, 0.0, 0.0))] + [
                (name, shift) for name, shift in shifts]
            copied, verified = {}, {}
            for obj in meshes:
                key = r3.object_key(obj.name)
                if key not in reference:
                    copied[obj.name] = {"error": "no reference object",
                                        "clean": False}
                    continue
                copied[obj.name] = r4.copy_uv_multi(obj, reference[key],
                                                    offsets)
                verified[obj.name] = r4.verify_uv_multi(obj, reference[key],
                                                        offsets)
            bpy.context.view_layer.update()

            if label == "p5":
                focus, radius, scale = p1.rig_for(meshes)
            images = render_set(meshes, focus, radius, scale, dirs[label],
                                f"{label.upper()}_{asset}", project_root)
            # 321.6: the moving assembly on its own. Its geometry and its UV
            # are untouched by the screw move, so this pair has to be pixel
            # identical; the whole-instrument frames cannot say that because
            # the screws legitimately moved in them.
            movers_only = dirs[label] / f"{label.upper()}_{asset}_mover.png"
            isolate_render(meshes, [obj for obj in movers if obj is not None],
                           focus, radius, scale, movers_only)
            images["mover_only"] = str(movers_only.relative_to(project_root))
            if asset == "Lever":
                # P4's grip close-up is framed relative to the lever pivot,
                # not the origin. Dropping that offset pointed the camera at
                # empty space, where the normal map on and off render the
                # same background and the knurl test passes vacuously.
                pivot_at = mover.matrix_world.translation
                grip_focus = (0.0, pivot_at.y - 0.076, pivot_at.z + 0.208)
                normal_nodes = 0
                for state, flag in (("normal_on", True),
                                    ("normal_off", False)):
                    normal_nodes = set_normal_maps(meshes, flag)
                    path = (dirs["closeup"]
                            / f"{label.upper()}_{asset}_grip_{state}.png")
                    p1.shot(grip_focus, 0.150, (34.0, 12.0), 62.0, 0.072, path)
                    images[f"grip_{state}"] = str(
                        path.relative_to(project_root))
                set_normal_maps(meshes, True)
                images["grip_normal_nodes"] = normal_nodes

            tree_static = r4.static_tree(parts)
            seats = {}
            for row in current["fasteners"]:
                name = row["fastener"]
                face_y = row["head_centre_m"][1] + 0.0005
                centre = (row["head_centre_m"][0], row["head_centre_m"][2])
                seat = r4.seat_probe(tree_static, centre, face_y,
                                     r4.SEAT_RADIUS[asset])
                seat.update(r4.penetration_probe(
                    tree_static, centre, face_y, 0.0012))
                seat.update({
                    "head_centre_m": row["head_centre_m"],
                    "shaft_triangle_hits": row["shaft_triangle_hits"],
                    "clearance_triangle_hits": row["clearance_triangle_hits"],
                    "shaft_clearance_mm": row["shaft_clearance_mm"],
                    "clearance_margin_mm": row["clearance_margin_mm"],
                    "tool_path_clean": row["pass"],
                })
                seats[name] = seat

            motion = r4.motion_interference(
                mover, movers, r4.static_parts(parts, movers), asset)
            health = {obj.name: p1.mesh_health(obj) for obj in meshes}
            grip = None
            if asset == "Lever" and "handle_grip" in parts:
                handle = next(obj for obj in movers if obj is not None)
                grip = r4.patch_reference(
                    handle, parts["handle_grip"], p4d.REGIONS["knurl"],
                    transforms=[mover.matrix_world.translation.copy() * 0.0,
                                mover.matrix_world.translation.copy()])

            states[label] = {
                "uv_copy": copied,
                "uv_verify": verified,
                "uv_offsets": [{"fastener": name, "shift_m": [round(v, 8) for v in shift]}
                               for name, shift in shifts],
                "packing": packing,
                "submeshes_total": sum(r["submeshes"] for r in
                                       packing.values()),
                "max_material_slots_per_object": max(
                    len(r["material_slots"]) for r in packing.values()),
                "triangles_total": sum(row["triangles"] for row
                                       in health.values()),
                "mesh_health": health,
                "gates": {
                    "non_manifold_zero": all(row["non_manifold_edges"] == 0
                                             for row in health.values()),
                    "zero_area_zero": all(row["zero_area_faces"] == 0
                                          for row in health.values()),
                },
                "coplanar_overlap": audit,
                "fastener_seating": seats,
                "motion": motion,
                "grip_knurl_patch": grip,
                "images": images,
            }
            if label == "r4":
                fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_FA_R4.fbx"
                d2.export_fbx(root, fbx)
                blend = dirs["blend"] / f"{asset}_{THEME}_FA_R4.blend"
                bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
                states[label].update({
                    "fbx": str(fbx.relative_to(project_root)),
                    "fbx_sha256": m1.digest(fbx),
                    "fbx_bytes": fbx.stat().st_size,
                    "blend": str(blend.relative_to(project_root))})

        # The shipped FBX, re-imported, against P5's UV.
        r4_fbx = project_root / states["r4"]["fbx"]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(r4_fbx))
        bpy.context.view_layer.update()
        offsets = [("common", (0.0, 0.0, 0.0))] + [
            (row["fastener"], tuple(row["shift_m"]))
            for row in states["r4"]["uv_offsets"]]
        on_import = {}
        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue
            key = r3.object_key(obj.name)
            if key in reference:
                on_import[key] = r4.verify_uv_multi(obj, reference[key],
                                                    offsets)

        difference = {}
        for view_label in list(p1.VIEWS) + ["mover_only"]:
            a = review.load_rgba(
                project_root / states["p5"]["images"][view_label])
            b = review.load_rgba(
                project_root / states["r4"]["images"][view_label])
            delta = np.abs(a[..., :3] - b[..., :3])
            difference[view_label] = {
                "max_channel_delta": round(float(delta.max()), 6),
                "pixels_changed": int(np.count_nonzero(
                    delta.max(axis=2) > 1.0 / 255.0)),
            }

        motion_identical = (
            states["p5"]["motion"]["intersecting_parts_all"]
            == states["r4"]["motion"]["intersecting_parts_all"])

        totals = {
            key: sum(row[key] for row in states["r4"]["uv_verify"].values())
            for key in ("triangles", "compared", "uv_changed", "unmatched",
                        "position_mismatch", "duplicate_match")}
        totals_on_import = {
            key: sum(row[key] for row in on_import.values())
            for key in ("triangles", "compared", "uv_changed", "unmatched",
                        "position_mismatch", "duplicate_match")}
        p5_uv_changed = sum(row["uv_changed"] for row
                            in states["p5"]["uv_verify"].values())

        payload["instruments"][asset] = {
            "source": source_for(asset),
            "uv_reference_fbx": reference_path,
            "reference_triangles": {name: row["triangle_count"]
                                    for name, row in reference.items()},
            "states": states,
            "uv_totals_r4_in_blender": totals,
            "uv_totals_r4_on_fbx_reimport": totals_on_import,
            "uv_changed_p5_state_control": p5_uv_changed,
            "uv_verify_on_import": on_import,
            "p5_vs_r4_image_difference": difference,
            "mover_only_identical": difference["mover_only"][
                "pixels_changed"] == 0,
            "signature_r4": signature_from_fbx(r4_fbx),
            "motion_identical_to_p5_state": motion_identical,
        }
        seats = states["r4"]["fastener_seating"]
        print(f"[FA-R4] {asset}: tris {totals['triangles']}, uv_changed "
              f"{totals['uv_changed']} (reimport "
              f"{totals_on_import['uv_changed']}), unmatched "
              f"{totals['unmatched'] + totals['position_mismatch'] + totals['duplicate_match']}"
              f", seats clean "
              f"{sum(1 for s in seats.values() if s.get('clean'))}/{len(seats)}"
              f", motion {states['r4']['motion']['clean']}")

    payload["textures"] = {}
    for name, path in textures.items():
        here = m1.digest(path)
        others = {}
        for label, folder in (("r1", R1_TREE), ("r3", R3_TREE)):
            candidate = project_root / folder / path.name
            others[label] = candidate.exists() and m1.digest(candidate) == here
        payload["textures"][name] = {
            "path": str(path.relative_to(project_root)), "sha256": here,
            "bytes": path.stat().st_size, "matches": others}

    lever = payload["instruments"]["Lever"]
    # 321.6: the knurl is only shading, so its presence is the difference
    # between the same frame with the Normal wired in and cut out.
    on = review.load_rgba(project_root
                          / lever["states"]["r4"]["images"]["grip_normal_on"])
    off = review.load_rgba(project_root
                           / lever["states"]["r4"]["images"]["grip_normal_off"])
    delta = np.abs(on[..., :3] - off[..., :3])
    grip_normal = {
        "images": {"on": lever["states"]["r4"]["images"]["grip_normal_on"],
                   "off": lever["states"]["r4"]["images"]["grip_normal_off"]},
        "max_channel_delta": round(float(delta.max()), 6),
        "mean_channel_delta": round(float(delta.mean()), 8),
        "pixels_changed": int(np.count_nonzero(
            delta.max(axis=2) > 2.0 / 255.0)),
        "normal_map_nodes_switched":
            lever["states"]["r4"]["images"].get("grip_normal_nodes"),
        "visible": int(np.count_nonzero(delta.max(axis=2) > 2.0 / 255.0)) > 2000,
    }
    payload["gate"] = {
        "uv_changed_total": sum(
            row["uv_totals_r4_in_blender"]["uv_changed"]
            for row in payload["instruments"].values()),
        "uv_changed_total_on_reimport": sum(
            row["uv_totals_r4_on_fbx_reimport"]["uv_changed"]
            for row in payload["instruments"].values()),
        "uv_unmatched_total": sum(
            row["uv_totals_r4_in_blender"]["unmatched"]
            + row["uv_totals_r4_in_blender"]["position_mismatch"]
            + row["uv_totals_r4_in_blender"]["duplicate_match"]
            for row in payload["instruments"].values()),
        "toggle_seats_clean": all(
            seat["clean"] for seat in payload["instruments"]["Toggle"]
            ["states"]["r4"]["fastener_seating"].values()),
        "tool_paths_clean": all(
            seat["tool_path_clean"] for row in payload["instruments"].values()
            for seat in row["states"]["r4"]["fastener_seating"].values()),
        "motion_gated_clean": all(row["states"]["r4"]["motion"]["clean"]
                                  for row in payload["instruments"].values()),
        "motion_identical_to_p5": all(
            row["motion_identical_to_p5_state"]
            for row in payload["instruments"].values()),
        "grip_on_knurl_patch": lever["states"]["r4"]["grip_knurl_patch"],
        "mover_only_identical": all(row["mover_only_identical"]
                                    for row in payload["instruments"].values()),
        "grip_normal_visible": grip_normal,
        "atlas_matches_r1_r3": all(
            row["matches"]["r1"] and row["matches"]["r3"]
            for row in payload["textures"].values()),
        "carried_digests_match": all(
            row["matches"] for row in payload["carried_unchanged"].values()),
    }
    gate = payload["gate"]
    payload["status"] = (
        "fastener_access_r4_ready"
        if gate["uv_changed_total"] == 0
        and gate["uv_changed_total_on_reimport"] == 0
        and gate["uv_unmatched_total"] == 0
        and gate["toggle_seats_clean"] and gate["tool_paths_clean"]
        and gate["motion_gated_clean"] and gate["motion_identical_to_p5"]
        and gate["atlas_matches_r1_r3"]
        and gate["carried_digests_match"]
        and (gate["grip_on_knurl_patch"] or {}).get("clean")
        and gate["mover_only_identical"]
        and (gate["grip_normal_visible"] or {}).get("visible")
        and all(all(row["states"]["r4"]["gates"].values())
                for row in payload["instruments"].values())
        else "fastener_access_r4_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[FA-R4] status {payload['status']}")


if __name__ == "__main__":
    main()
