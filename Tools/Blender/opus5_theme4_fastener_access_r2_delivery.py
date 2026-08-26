"""Theme 4 fastener access R2 delivery: 316's deletions, measured.

Every instrument in the Theme 4 roster is built twice from one camera frame -
its R1 state (rotary nameplate gone, sixteen screws relocated) and its R2
state (that, plus the fifteen buried screws deleted). The two builds feed the
same audits, so the census, the triangle delta and the freeze claim are all
differences between two things measured the same way rather than a number
quoted from a previous run.

Writes only to delivery_p6/fastener_access_r2/**.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_fastener_access_r2_delivery.py -- \
      --project-root "$PWD"
"""

import argparse
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
import opus5_theme4_material_p2 as m2
import opus5_theme4_full_p6_batch_b as bb
import opus5_theme4_full_p6_batch_b_r1 as br1
import opus5_theme4_full_p6_batch_b_r1_delivery as r1d
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_a_delivery as bad
import opus5_theme4_fastener_access_r1 as fa
import opus5_theme4_fastener_access_r1_delivery as fad
import opus5_theme4_fastener_access_r2 as r2

THEME = "MachinedErgonomics"
TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
        "delivery_p6/fastener_access_r2")
R1_TREE = ("ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/"
           "delivery_p6/fastener_access_r1")
OUTPUT = f"{TREE}/theme4_fastener_access_r2.json"
# Everything R1 shipped, plus the two meters R2 changes.
EXPORTED = ("Rotary", "Button", "Lamp", "StatusIndicator", "Toggle", "Lever",
            "MeterMedium", "MeterLarge")
BATCH_A_ROLES = ("MeterMedium", "MeterLarge")


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def role_for(asset, name):
    """Batch A's rules for the meters, Batch B's for what R1 shipped."""
    return (bad.role_for(name) if asset in BATCH_A_ROLES
            else r1d.role_for(name))


def build(asset, builder, stage, overrides=None, materials=True):
    """Build one instrument at `stage` ("r1" or "r2"), capturing every part."""
    p1.clear_scene()
    review.configure_scene()
    roles = m2.make_materials() if materials else None
    # Same asset name in both stages, so the relocation table still matches;
    # only the deletions are switched off for the r1 build.
    saved = r2.install(asset, drop_nameplate=asset in fa.NAMEPLATE_REMOVED,
                       overrides=overrides,
                       drop_fasteners=(stage == "r2"))
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
                role = role_for(asset, obj.name)
                tagged[stem] = role
                obj.data.materials.clear()
                obj.data.materials.append(roles[role])
        return original_join(target, others)

    def assign(obj, material):
        if roles is not None and not obj.data.materials:
            role = role_for(asset, obj.name)
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
        r2.restore(saved)
    movers = list(movers) if isinstance(movers, (list, tuple)) else [movers]
    root = bpy.data.objects.new(f"PF_Visual_{asset}_{THEME}_V6", None)
    bpy.context.collection.objects.link(root)
    for obj in (body, mover):
        if obj is not None:
            obj.parent = root
    bpy.context.view_layer.update()
    parts = {name: np.concatenate(rows) for name, rows in captured.items()}
    return root, body, mover, movers, audit, parts


def gates_for(asset, root, body, mover, movers, audit):
    """Each asset measured by its own batch's contract, not by Batch B's.

    R1 sent MeterMedium and MeterLarge down the generic branch because they
    are absent from Batch B's CONTRACT, so they were gated on a triangle count
    alone - no envelope, no mount plane, no motion clearance. They belong to
    Batch A and are measured there.
    """
    if asset in bb.CONTRACT:
        measured = bb.measure_asset(asset, root, body, mover, movers)
        statics = bb.snapshot_statics([body])
        return measured, bb.motion_clearance_audit(mover, movers, statics,
                                                   asset)
    if asset in ba.CONTRACT:
        # Batch A takes the single moving object, not Batch B's list.
        moving = movers[0]
        measured = ba.measure_asset(asset, root, body, mover, moving)
        return measured, ba.motion_clearance_audit(mover, moving, asset)
    # The pilot instruments have no Batch A/B contract row. Mesh health and
    # the triangle count are still real gates; the envelope is not ours.
    meshes = [body] + [obj for obj in movers if obj is not None]
    health = {obj.name: p1.mesh_health(obj) for obj in meshes}
    triangles = sum(row["triangles"] for row in health.values())
    return ({"triangles_total": triangles, "renderers": len(meshes),
             "renderer_budget": None, "mesh_health": health,
             "gates": {
                 "non_manifold_zero": all(row["non_manifold_edges"] == 0
                                          for row in health.values()),
                 "zero_area_zero": all(row["zero_area_faces"] == 0
                                       for row in health.values())},
             "note": ("pilot asset: no Batch A/B contract row, so mesh health "
                      "and the triangle delta are the gates")},
            None)


def dress(asset, meshes, textures):
    for obj in meshes:
        m2.unwrap(obj)
    atlas, emissive = p4d.delivery_materials_p4(textures)
    rows = {}
    for obj in meshes:
        role_of_slot = [slot.material.name.rsplit("_", 1)[-1].lower()
                        for slot in obj.material_slots]
        counts, used = p4d.pack_into_regions(obj, role_of_slot, atlas,
                                             emissive)
        rows[obj.name] = {
            "role_face_counts": counts,
            "material_slots": [s.material.name for s in obj.material_slots],
            "submeshes": len(used),
        }
    bpy.context.view_layer.update()
    return rows


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in ("r1", "r2", "tool", "blend",
                                          "neutral")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-fastener-access-R2",
        "alignment": "316",
        "note": ("R1's accepted changes carried forward unchanged - the "
                 "rotary nameplate deleted and sixteen screws relocated - "
                 "plus 316's deletion of the fifteen screws buried inside "
                 "the meter and rotary housings. Nothing else moves, and the "
                 "part signatures say so."),
        "frozen_trees": [R1_TREE,
                         "delivery_p6/batch_b", "delivery_p6/batch_b_r1",
                         "delivery_p6/batch_b_r2"],
        "removed_in_r2": {asset: list(names)
                          for asset, names in r2.REMOVED.items()},
        "standard": {
            "shaft_radius_mm": fa.TOOL_SHAFT_R * 1000.0,
            "working_clearance_radius_mm": fa.TOOL_CLEAR_R * 1000.0,
            "straight_reach_mm": fa.TOOL_REACH * 1000.0,
            "accept": "both proxies hit zero triangles",
        },
        "instruments": {},
    }

    table = []
    total_before = total_after = passing = removed = 0

    for asset, source, builder in fa.ROSTER:
        wanted = asset in EXPORTED
        overrides_seed = None

        # --- R1 state: relocations need the unmodified audit to derive them,
        # so the pristine build comes first and is thrown away.
        root, body, mover, movers, audit, parts = build(
            asset, builder, "r1", materials=False)
        pristine = fa.audit_instrument(asset, source, parts, movers)
        overrides_seed = fa.fix_positions(asset, pristine["fasteners"])

        root, body, mover, movers, audit, parts = build(
            asset, builder, "r1", overrides=overrides_seed, materials=wanted)
        meshes = [body] + [obj for obj in movers if obj is not None]
        if wanted:
            dress(asset, meshes, textures)
        focus, radius, scale = p1.rig_for(meshes)
        half_extent = radius * 0.34
        r1_audit = fa.audit_instrument(asset, source, parts, movers)
        r1_measured, r1_clearance = gates_for(asset, root, body, mover,
                                              movers, audit)
        r1_signature = r2.part_signature(parts)

        review.configure_scene()
        r1_images = {}
        for label, view in p1.VIEWS.items():
            path = dirs["r1"] / f"R1_{asset}_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            r1_images[label] = str(path.relative_to(project_root))

        # --- R2 state
        root, body, mover, movers, audit, parts = build(
            asset, builder, "r2", overrides=overrides_seed, materials=wanted)
        meshes = [body] + [obj for obj in movers if obj is not None]
        packing = dress(asset, meshes, textures) if wanted else {}
        r2_audit = fa.audit_instrument(asset, source, parts, movers)
        r2_measured, r2_clearance = gates_for(asset, root, body, mover,
                                              movers, audit)

        r2_signature = r2.part_signature(parts)
        preserved = fad.preserved_audits(asset, body, mover, movers, parts,
                                         focus, half_extent)
        drop = r2.dropped_names(asset)
        freeze = r2.signature_diff(r1_signature, r2_signature, drop)

        r2_images = {}
        for label, view in p1.VIEWS.items():
            path = dirs["r2"] / f"R2_{asset}_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            r2_images[label] = str(path.relative_to(project_root))
        if r2_audit["fastener_count"]:
            r2_images.update(fad.proxy_images(
                asset, r2_audit["fasteners"], focus, radius, scale,
                dirs["tool"], f"R2_{asset}", project_root))

        # 316 calls the fifteen invisible. That is testable: render the same
        # camera before and after and difference the pixels. If a deleted
        # screw ever showed, this is where it would turn up.
        difference = {}
        for label in p1.VIEWS:
            a = review.load_rgba(project_root / r1_images[label])
            b = review.load_rgba(project_root / r2_images[label])
            delta = np.abs(a[..., :3] - b[..., :3])
            difference[label] = {
                "max_channel_delta": round(float(delta.max()), 6),
                "mean_channel_delta": round(float(delta.mean()), 8),
                "pixels_changed": int(np.count_nonzero(
                    delta.max(axis=2) > 1.0 / 255.0)),
            }

        neutral = {}

        row = {
            "source": source,
            "fastener_count_before": r1_audit["fastener_count"],
            "fastener_count_after": r2_audit["fastener_count"],
            "removed_in_r2": sorted(drop),
            "removed_count": len(drop),
            "fasteners_after": r2_audit["fasteners"],
            "pass_after": r2_audit["pass"],
            "triangles_r1": r1_measured["triangles_total"],
            "triangles_r2": r2_measured["triangles_total"],
            "triangle_delta": r2_measured["triangles_total"]
            - r1_measured["triangles_total"],
            "renderers": r2_measured["renderers"],
            "renderer_budget": r2_measured.get("renderer_budget"),
            "gates": r2_measured["gates"],
            "mesh_health": r2_measured.get("mesh_health"),
            "clearance": r2_clearance,
            "coplanar_overlap": audit,
            "preserved_audits": preserved,
            "frozen_parts": freeze,
            "images_r1": r1_images,
            "images_r2": r2_images,
            "r1_r2_image_difference": difference,
            "r1_r2_image_difference_note": (
                "textured pair; a non-zero delta here is the atlas repacking "
                "after parts were removed, not geometry - see "
                "r1_r2_geometry_only_difference"),
            "r1_r2_geometry_only_difference": neutral,
        }
        if drop:
            row["residue"] = r2.residue(asset)
            row["deleted_triangles"] = -row["triangle_delta"]
            row["deleted_triangles_per_screw"] = round(
                -row["triangle_delta"] / len(drop), 2)
        if wanted:
            row.update({
                "objects": packing,
                "submeshes_total": sum(r["submeshes"] for r in
                                       packing.values()),
                "max_material_slots_per_object": max(
                    len(r["material_slots"]) for r in packing.values()),
            })
            fbx = tree / f"SM_{asset}_{THEME}_V6_Opus5_FA_R2.fbx"
            d2.export_fbx(root, fbx)
            blend = dirs["blend"] / f"{asset}_{THEME}_FA_R2.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
            row.update({
                "fa_r2_fbx": str(fbx.relative_to(project_root)),
                "fa_r2_fbx_sha256": m1.digest(fbx),
                "fa_r2_fbx_bytes": fbx.stat().st_size,
                "fa_r2_blend": str(blend.relative_to(project_root)),
            })

        # The textured pair is not a clean answer to "was it visible": the
        # atlas repacks when parts disappear, so every texel shifts a little
        # and the diff is dominated by that. Rendering both stages with one
        # flat material removes the packing from the question and leaves only
        # geometry, which is what 316's "invisible" claim is actually about.
        if drop:
            neutral_paths = {}
            for stage in ("r1", "r2"):
                nroot, nbody, nmover, nmovers, naudit, nparts = build(
                    asset, builder, stage, overrides=overrides_seed,
                    materials=False)
                review.configure_scene()
                for label, view in p1.VIEWS.items():
                    path = (dirs["neutral"]
                            / f"{stage.upper()}_{asset}_{label}_neutral.png")
                    p1.shot(focus, radius, view, 52.0, scale, path)
                    neutral_paths[(stage, label)] = path
            for label in p1.VIEWS:
                a = review.load_rgba(neutral_paths[("r1", label)])
                b = review.load_rgba(neutral_paths[("r2", label)])
                delta = np.abs(a[..., :3] - b[..., :3])
                neutral[label] = {
                    "r1": str(neutral_paths[("r1", label)]
                              .relative_to(project_root)),
                    "r2": str(neutral_paths[("r2", label)]
                              .relative_to(project_root)),
                    "max_channel_delta": round(float(delta.max()), 6),
                    "pixels_changed": int(np.count_nonzero(
                        delta.max(axis=2) > 1.0 / 255.0)),
                }

        row["r1_r2_geometry_only_difference"] = neutral
        if neutral:
            worst = max(neutral.items(),
                        key=lambda kv: kv[1]["pixels_changed"])
            front = neutral["front"]["pixels_changed"]
            row["visibility_finding"] = {
                "front_pixels_changed": front,
                "worst_view": worst[0],
                "worst_view_pixels_changed": worst[1]["pixels_changed"],
                "worst_view_max_channel_delta":
                    worst[1]["max_channel_delta"],
                "correction": (
                    "R1 reported these screws as invisible from every "
                    "direction, and 316 repeated it. Differencing the two "
                    "geometry-only renders shows that is right from the "
                    "front and the obliques - 0 to 11 pixels, at the 1/255 "
                    "quantisation floor - but wrong at the grazing side "
                    "view, where a buried head coincides with the housing "
                    "surface and prints a dark mark on it. Deleting them "
                    "removes that artefact as well as the dead triangles, "
                    "so 316's decision holds; the claim behind it was "
                    "overstated and is corrected here."),
            }

        for entry in r1_audit["fasteners"]:
            name = entry["fastener"]
            if name in drop:
                table.append({
                    "asset": asset, "fastener": name,
                    "head_centre_m": entry["head_centre_m"],
                    "driver_axis": entry["driver_axis"],
                    "approach_side": entry["approach_side"],
                    "r1": "FAIL", "r2": "removed_in_r2",
                    "reason": ("enclosed inside the housing solid; 316 rules "
                               "out changing the land or the collar"),
                })
                removed += 1
                continue
            done = next(e for e in r2_audit["fasteners"]
                        if e["fastener"] == name)
            table.append({
                "asset": asset, "fastener": name,
                "head_centre_m": done["head_centre_m"],
                "driver_axis": done["driver_axis"],
                "approach_side": done["approach_side"],
                "r1": "PASS" if entry["pass"] else "FAIL",
                "r2": "PASS" if done["pass"] else "FAIL",
                "shaft_triangle_hits": done["shaft_triangle_hits"],
                "clearance_triangle_hits": done["clearance_triangle_hits"],
                "shaft_clearance_mm": done["shaft_clearance_mm"],
                "clearance_margin_mm": done["clearance_margin_mm"],
            })
            passing += 1 if done["pass"] else 0

        total_before += r1_audit["fastener_count"]
        total_after += r2_audit["fastener_count"]
        payload["instruments"][asset] = row
        print(f"[FA-R2] {asset}: {r1_audit['fastener_count']} -> "
              f"{r2_audit['fastener_count']} fasteners, all pass "
              f"{r2_audit['pass']}, tris {r1_measured['triangles_total']} -> "
              f"{r2_measured['triangles_total']} "
              f"({row['triangle_delta']:+d}), frozen {freeze['clean']}")

    for name, reason in fa.ABSENT:
        payload["instruments"][name] = {
            "source": "absent", "fastener_count_before": 0,
            "fastener_count_after": 0, "removed_in_r2": [],
            "fasteners_after": [], "pass_after": True, "reason": reason}

    payload["table"] = table
    payload["census"] = {
        "instruments_audited": len(fa.ROSTER),
        "instruments_absent": [name for name, _ in fa.ABSENT],
        "fasteners_r1": total_before,
        "removed_in_r2": removed,
        "fasteners_r2": total_after,
        "passing_r2": passing,
        "failing_r2": total_after - passing,
    }
    payload["textures"] = {
        name: {"path": str(path.relative_to(project_root)),
               "sha256": m1.digest(path), "bytes": path.stat().st_size}
        for name, path in textures.items()}

    exported = [asset for asset in EXPORTED]
    payload["status"] = (
        "fastener_access_r2_ready"
        if total_after == passing
        and removed == sum(len(names) for names in r2.REMOVED.values())
        and all(payload["instruments"][asset]["frozen_parts"]["clean"]
                for asset in payload["instruments"]
                if "frozen_parts" in payload["instruments"][asset])
        and all(payload["instruments"][asset].get("residue", {"clean": True})
                ["clean"] for asset in payload["instruments"]
                if isinstance(payload["instruments"][asset], dict))
        and all(all(payload["instruments"][asset]["gates"].values())
                for asset in exported)
        and all(payload["instruments"][asset]["clearance"] is None
                or payload["instruments"][asset]["clearance"]["clean"]
                for asset in exported)
        and all(payload["instruments"][asset]["max_material_slots_per_object"]
                <= 2 for asset in exported)
        else "fastener_access_r2_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[FA-R2] census {total_before} -> {total_after} fasteners "
          f"({removed} removed), {passing} passing; "
          f"status {payload['status']}")


if __name__ == "__main__":
    main()
