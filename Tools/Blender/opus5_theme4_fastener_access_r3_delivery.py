"""Theme 4 fastener access R3 delivery: R2's geometry, R1's UV.

Writes only to delivery_p6/fastener_access_r3/**.

Three instruments are rebuilt - MeterMedium, MeterLarge and Rotary - with R2's
deletions intact and the surviving UV copied off the reference FBX. The five
R1 instruments are not rebuilt at all; their R1 FBX digests are re-measured and
recorded, which is the whole of what 317.7 asks.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_fastener_access_r3_delivery.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
import json
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
import opus5_theme4_full_p6_batch_a_r4_b3u as b3u
import opus5_theme4_fastener_access_r1 as fa
import opus5_theme4_fastener_access_r2 as r2
import opus5_theme4_fastener_access_r2_delivery as r2d
import opus5_theme4_fastener_access_r3 as r3

THEME = "MachinedErgonomics"
BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
TREE = f"{BASE}/fastener_access_r3"
OUTPUT = f"{TREE}/theme4_fastener_access_r3.json"
R1_TREE = f"{BASE}/fastener_access_r1"
R2_TREE = f"{BASE}/fastener_access_r2"
CARRIED = ("Lever", "Toggle", "Button", "Lamp", "StatusIndicator")


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
    """Per-object triangles, bounds, centroid and position set, re-imported.

    The position digest is what makes "same geometry" checkable without
    trusting the exporter: it hashes the sorted set of world positions the
    importer read back, so a single vertex moving anywhere changes it.
    """
    rows, hierarchy = b3u.read_fbx(path)
    out = {}
    for name, row in rows.items():
        positions = row["unique_positions"]
        centre = [round(sum(p[i] for p in positions) / len(positions), 6)
                  for i in range(3)] if positions else None
        out[name] = {
            "triangles": row["triangles"],
            "vertices": row["vertices"],
            "bounds_min": row["bounds_min"],
            "bounds_max": row["bounds_max"],
            "position_count": len(positions),
            "position_centroid": centre,
            "position_digest": hashlib.sha256(
                repr(positions).encode("utf-8")).hexdigest(),
            "materials": row["materials"],
        }
    return {"objects": out, "hierarchy": hierarchy}


def build_state(asset, stage, textures, overrides, reference=None):
    """Build one stage and, when a reference is given, restore its UV."""
    root, body, mover, movers, audit, parts = r2d.build(
        asset, builder_for(asset), stage, overrides=overrides, materials=True)
    meshes = [body] + [obj for obj in movers if obj is not None]
    packing = r2d.dress(asset, meshes, textures)
    copied = {}
    if reference is not None:
        for obj in meshes:
            key = r3.object_key(obj.name)
            if key not in reference:
                copied[obj.name] = {"error": "no reference object of this name",
                                    "clean": False}
                continue
            copied[obj.name] = r3.copy_uv(obj, reference[key])
        bpy.context.view_layer.update()
    return root, body, mover, movers, audit, parts, packing, copied


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in ("r1", "r2", "r3", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-fastener-access-R3",
        "alignment": "317",
        "note": ("R2's geometry to the vertex, R1's UV to the loop. R2's "
                 "'atlas repacking' explanation was wrong: the four atlas "
                 "PNGs are byte-identical across R1, R2 and R3, and what "
                 "moved was the mesh UV, because unwrap and pack_into_regions "
                 "were re-run on a mesh that had just lost fifteen screws."),
        "frozen_trees": [R1_TREE, R2_TREE, f"{BASE}/batch_a",
                         f"{BASE}/batch_b", f"{BASE}/batch_b_r1",
                         f"{BASE}/batch_b_r2"],
        "uv_reference": {asset: {"fbx": path, "why": why}
                         for asset, (path, why) in r3.REFERENCE.items()},
        "position_match_tolerance_mm": r3.POSITION_TOLERANCE * 1000.0,
        "match_method": ("object name, then a triangle keyed by the set of "
                         "its three vertex positions, snapped to the "
                         "reference's own position clusters through a "
                         "KD-tree. Face order and loop order are never used."),
        "instruments": {},
        "carried_from_r1": {},
    }

    # 317.7: the five R1 instruments are referenced, not rebuilt.
    r1_payload = json.loads(
        (project_root / f"{R1_TREE}/theme4_fastener_access_r1.json").read_text())
    for asset in CARRIED:
        row = r1_payload["instruments"][asset]
        path = project_root / row["fa_fbx"]
        payload["carried_from_r1"][asset] = {
            "regenerated": False,
            "fbx": row["fa_fbx"],
            "sha256_now": m1.digest(path),
            "sha256_in_r1_json": row["fa_fbx_sha256"],
            "matches_r1_json": m1.digest(path) == row["fa_fbx_sha256"],
            "bytes": path.stat().st_size,
            "fastener_count": row["fastener_count_before"],
            "pass_after": row["pass_after"],
        }

    for asset in r3.TARGETS:
        reference_path, why = r3.REFERENCE[asset]
        reference = r3.read_reference(project_root / reference_path)

        # The relocation table has to come from an unmodified build, exactly
        # as R1 and R2 derived it.
        _, _, _, movers0, _, parts0 = r2d.build(
            asset, builder_for(asset), "r1", materials=False)
        pristine = fa.audit_instrument(asset, source_for(asset), parts0,
                                       movers0)
        overrides = fa.fix_positions(asset, pristine["fasteners"])

        states = {}
        for stage, label, use_reference in (("r1", "r1", True),
                                            ("r2", "r2", False),
                                            ("r2", "r3", True)):
            root, body, mover, movers, audit, parts, packing, copied = \
                build_state(asset, stage, textures, overrides,
                            reference if use_reference else None)
            meshes = [body] + [obj for obj in movers if obj is not None]
            if label == "r1":
                focus, radius, scale = p1.rig_for(meshes)
            verify = {obj.name: r3.verify_uv(obj, reference[
                r3.object_key(obj.name)])
                for obj in meshes
                if r3.object_key(obj.name) in reference}
            measured, clearance = r2d.gates_for(asset, root, body, mover,
                                                movers, audit)
            review.configure_scene()
            images = {}
            for view_label, view in p1.VIEWS.items():
                path = dirs[label] / f"{label.upper()}_{asset}_{view_label}.png"
                p1.shot(focus, radius, view, 52.0, scale, path)
                images[view_label] = str(path.relative_to(project_root))
            states[label] = {
                "uv_copy": copied,
                "uv_verify": verify,
                "packing": packing,
                "triangles": measured["triangles_total"],
                "renderers": measured["renderers"],
                "gates": measured["gates"],
                "clearance": clearance,
                "coplanar_overlap": audit,
                "images": images,
                "submeshes_total": sum(r["submeshes"] for r in
                                       packing.values()),
                "max_material_slots_per_object": max(
                    len(r["material_slots"]) for r in packing.values()),
                "material_slots": {name: r["material_slots"]
                                   for name, r in packing.items()},
            }
            if label == "r3":
                fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_FA_R3.fbx"
                d2.export_fbx(root, fbx)
                blend = dirs["blend"] / f"{asset}_{THEME}_FA_R3.blend"
                bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
                states[label].update({
                    "fbx": str(fbx.relative_to(project_root)),
                    "fbx_sha256": m1.digest(fbx),
                    "fbx_bytes": fbx.stat().st_size,
                    "blend": str(blend.relative_to(project_root)),
                })

        # 317.5: the shipped R3 FBX against the shipped R2 FBX, both re-read.
        r2_fbx = project_root / (
            f"{R2_TREE}/SM_{asset}_{THEME}_V6_Opus5_FA_R2.fbx")
        r3_fbx = project_root / states["r3"]["fbx"]
        r2_signature = signature_from_fbx(r2_fbx)
        r3_signature = signature_from_fbx(r3_fbx)
        geometry_same = (
            r2_signature["hierarchy"] == r3_signature["hierarchy"]
            and set(r2_signature["objects"]) == set(r3_signature["objects"])
            and all(r2_signature["objects"][name]["position_digest"]
                    == r3_signature["objects"][name]["position_digest"]
                    and r2_signature["objects"][name]["triangles"]
                    == r3_signature["objects"][name]["triangles"]
                    and r2_signature["objects"][name]["bounds_min"]
                    == r3_signature["objects"][name]["bounds_min"]
                    and r2_signature["objects"][name]["bounds_max"]
                    == r3_signature["objects"][name]["bounds_max"]
                    for name in r2_signature["objects"]))

        # 317.3: the shipped R3 FBX, re-imported, against the reference UV.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(r3_fbx))
        bpy.context.view_layer.update()
        on_import = {}
        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue
            key = r3.object_key(obj.name)
            if key in reference:
                on_import[key] = r3.verify_uv(obj, reference[key])

        difference = {}
        for pair in (("r1", "r2"), ("r1", "r3"), ("r2", "r3")):
            rows = {}
            for view_label in p1.VIEWS:
                a = review.load_rgba(
                    project_root / states[pair[0]]["images"][view_label])
                b = review.load_rgba(
                    project_root / states[pair[1]]["images"][view_label])
                delta = np.abs(a[..., :3] - b[..., :3])
                rows[view_label] = {
                    "max_channel_delta": round(float(delta.max()), 6),
                    "pixels_changed": int(np.count_nonzero(
                        delta.max(axis=2) > 1.0 / 255.0)),
                }
            difference[f"{pair[0]}_vs_{pair[1]}"] = rows

        totals = {
            "triangles": sum(row["triangles"] for row in
                             states["r3"]["uv_verify"].values()),
            "uv_changed": sum(row["uv_changed"] for row in
                              states["r3"]["uv_verify"].values()),
            "position_mismatch": sum(row["position_mismatch"] for row in
                                     states["r3"]["uv_verify"].values()),
            "unmatched": sum(row["unmatched"] for row in
                             states["r3"]["uv_verify"].values()),
            "duplicate_match": sum(row["duplicate_match"] for row in
                                   states["r3"]["uv_verify"].values()),
        }
        totals_on_import = {
            "triangles": sum(row["triangles"] for row in on_import.values()),
            "uv_changed": sum(row["uv_changed"] for row in on_import.values()),
            "position_mismatch": sum(row["position_mismatch"] for row in
                                     on_import.values()),
            "unmatched": sum(row["unmatched"] for row in on_import.values()),
            "duplicate_match": sum(row["duplicate_match"] for row in
                                   on_import.values()),
        }
        r2_uv_changed = sum(row["uv_changed"] for row in
                            states["r2"]["uv_verify"].values())

        payload["instruments"][asset] = {
            "source": source_for(asset),
            "uv_reference_fbx": reference_path,
            "uv_reference_why": why,
            "reference_triangles": {name: row["triangle_count"]
                                    for name, row in reference.items()},
            "removed_in_r2": sorted(r2.dropped_names(asset)),
            "states": states,
            "uv_totals_r3_in_blender": totals,
            "uv_totals_r3_on_fbx_reimport": totals_on_import,
            "uv_changed_r2_for_comparison": r2_uv_changed,
            "uv_verify_on_import": on_import,
            "geometry_signature_r2": r2_signature,
            "geometry_signature_r3": r3_signature,
            "geometry_identical_to_r2": geometry_same,
            "image_difference": difference,
        }
        print(f"[FA-R3] {asset}: tris {totals['triangles']}, "
              f"uv_changed R2 {r2_uv_changed} -> R3 {totals['uv_changed']} "
              f"(reimport {totals_on_import['uv_changed']}), "
              f"unmatched {totals['unmatched']}, "
              f"dup {totals['duplicate_match']}, "
              f"geometry==R2 {geometry_same}")

    payload["textures"] = {}
    for name, path in textures.items():
        here = m1.digest(path)
        r1_copy = project_root / R1_TREE / path.name
        r2_copy = project_root / R2_TREE / path.name
        payload["textures"][name] = {
            "path": str(path.relative_to(project_root)),
            "sha256": here,
            "bytes": path.stat().st_size,
            "matches_r1": r1_copy.exists() and m1.digest(r1_copy) == here,
            "matches_r2": r2_copy.exists() and m1.digest(r2_copy) == here,
        }

    payload["gate"] = {
        "uv_changed_total": sum(
            row["uv_totals_r3_in_blender"]["uv_changed"]
            for row in payload["instruments"].values()),
        "uv_changed_total_on_reimport": sum(
            row["uv_totals_r3_on_fbx_reimport"]["uv_changed"]
            for row in payload["instruments"].values()),
        "unmatched_total": sum(
            row["uv_totals_r3_in_blender"]["unmatched"]
            + row["uv_totals_r3_in_blender"]["position_mismatch"]
            + row["uv_totals_r3_in_blender"]["duplicate_match"]
            for row in payload["instruments"].values()),
        "geometry_identical_to_r2": all(
            row["geometry_identical_to_r2"]
            for row in payload["instruments"].values()),
        "atlas_byte_identical": all(
            row["matches_r1"] and row["matches_r2"]
            for row in payload["textures"].values()),
        "carried_r1_digests_match": all(
            row["matches_r1_json"] for row in
            payload["carried_from_r1"].values()),
    }
    gate = payload["gate"]
    payload["status"] = (
        "fastener_access_r3_ready"
        if gate["uv_changed_total"] == 0
        and gate["uv_changed_total_on_reimport"] == 0
        and gate["unmatched_total"] == 0
        and gate["geometry_identical_to_r2"]
        and gate["atlas_byte_identical"]
        and gate["carried_r1_digests_match"]
        and all(all(row["states"]["r3"]["gates"].values())
                for row in payload["instruments"].values())
        and all(row["states"]["r3"]["max_material_slots_per_object"] <= 2
                for row in payload["instruments"].values())
        else "fastener_access_r3_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[FA-R3] status {payload['status']}; gate {json.dumps(gate)}")


if __name__ == "__main__":
    main()
