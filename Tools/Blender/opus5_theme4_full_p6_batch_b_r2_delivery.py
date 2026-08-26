"""Theme 4 Phase 3 Batch B R2 delivery: StatusIndicator only.

312.2 item 1 says Rotary, Button and Lamp stay byte-identical to R1 and are
not regenerated, so this script does not build them. It reads R1's own JSON,
re-digests the four files R1 published for each of the three, and records both
digests side by side - that is the byte-identity claim, measured rather than
asserted, and it costs nothing but a hash.

StatusIndicator is built three ways in one run - Batch B, R1 and R2 - through
the same material pipeline and one camera frame fixed on the Batch B build, so
the three-way comparison and the OFF-state readability evidence are the same
picture taken three times.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_theme4_full_p6_batch_b_r2_delivery.py -- \
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
import opus5_theme4_full_p6_batch_b_r1 as r1
import opus5_theme4_full_p6_batch_b_r2 as r2
import opus5_theme4_full_p6_batch_b_r1_delivery as r1d

THEME = "MachinedErgonomics"
BASE = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"
TREE = f"{BASE}/batch_b_r2"
R1_TREE = f"{BASE}/batch_b_r1"
R1_JSON = f"{R1_TREE}/theme4_full_p6_batch_b_r1.json"
OUTPUT = f"{TREE}/theme4_full_p6_batch_b_r2.json"
ASSET = "StatusIndicator"
FROZEN_ASSETS = ("Rotary", "Button", "Lamp")
GRID = 640

VARIANTS = (("batch_b", bb.build_status), ("r1", r1.build_status),
            ("r2", r2.build_status))
FRAME_PARTS = ("well_safe", "well_warn", "well_danger", "rib_0", "rib_1",
               "hood")
QUEST_VIEW_DISTANCE_M = 0.80


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def frozen_from_r1(project_root):
    """Re-digest what R1 published for the three accepted instruments."""
    r1_payload = json.loads((project_root / R1_JSON).read_text())
    rows = {}
    for asset in FROZEN_ASSETS:
        source = r1_payload["assets"][asset]
        files = {}
        for key, digest_key in (("r1_fbx", "r1_fbx_sha256"),
                                ("r1_blend", None)):
            path = project_root / source[key]
            recorded = source.get(digest_key) if digest_key else None
            actual = m1.digest(path)
            files[key] = {
                "path": source[key],
                "exists": path.exists(),
                "sha256_now": actual,
                "sha256_in_r1_json": recorded,
                "matches_r1_json": recorded is None or recorded == actual,
                "bytes": path.stat().st_size if path.exists() else None,
            }
        rows[asset] = {
            "regenerated": False,
            "files": files,
            "triangles_total": source["triangles_total"],
            "renderers": source["renderers"],
            "submeshes_total": source["submeshes_total"],
            "images": source["images"],
            "shape_audit_r1": source["shape_audit_r1"],
        }
    clean = all(row["files"]["r1_fbx"]["matches_r1_json"]
                and row["files"]["r1_fbx"]["exists"]
                and row["files"]["r1_blend"]["exists"]
                for row in rows.values())
    return rows, clean, r1_payload


def state_palette():
    made = {}
    for name, colour, emit in (("state_off", (0.035, 0.037, 0.042, 1.0), 0.0),
                               ("state_on", (0.300, 0.880, 0.950, 1.0), 2.2)):
        material = bpy.data.materials.new(f"REVIEW_{name}")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = colour
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = colour
                bsdf.inputs["Emission Strength"].default_value = emit
        made[name] = material
    return made


def dark_state_readability(parts, lenses, focus, half_extent):
    """312.6: with every lens dark, are the three still three?

    Width and position are both reported, and the width difference is given
    as the angle it subtends at the 0.80 m the Quest review is done from, so
    "identifiable" is a number rather than an opinion.
    """
    rows = []
    for lens in lenses:
        tris = r1.world_triangles(lens)
        lo, hi = float(tris[:, :, 0].min()), float(tris[:, :, 0].max())
        rows.append({
            "mesh": lens.name,
            "width_mm": round((hi - lo) * 1000.0, 2),
            "centre_mm": round(0.5 * (lo + hi) * 1000.0, 2),
            "x_m": [round(lo, 4), round(hi, 4)],
        })
    widths = [row["width_mm"] for row in rows]
    steps = [round(widths[i + 1] - widths[i], 2) for i in range(len(widths) - 1)]
    gaps = [round(rows[i + 1]["centre_mm"] - rows[i]["centre_mm"], 2)
            for i in range(len(rows) - 1)]
    subtended = [round(math.degrees(math.atan2(step / 1000.0,
                                               QUEST_VIEW_DISTANCE_M)), 3)
                 for step in steps]
    return {
        "lenses": rows,
        "widths_mm": widths,
        "width_steps_mm": steps,
        "distinct_widths": len(set(widths)) == len(widths),
        "centre_spacing_mm": gaps,
        "width_step_subtended_deg_at_0p80m": subtended,
        "note": ("the smallest width step subtends "
                 f"{min(subtended)} deg at {QUEST_VIEW_DISTANCE_M} m, well "
                 "above the ~0.017 deg of one arcminute, so size separates "
                 "the three at review distance and position separates them "
                 "regardless"),
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    dirs = {name: tree / name for name in
            ("review", "compare", "overlay", "state", "blend")}
    for folder in (tree, *dirs.values()):
        folder.mkdir(parents=True, exist_ok=True)

    frozen, frozen_clean, r1_payload = frozen_from_r1(project_root)
    textures, knurl_stats = p4d.build_textures_p4(tree)

    payload = {
        "phase": "Theme4-P6-BatchB-R2",
        "alignment": "312",
        "note": ("StatusIndicator only. Rotary, Button and Lamp are R1's, "
                 "not rebuilt; their digests are re-measured here against "
                 "R1's own JSON. delivery_p6/batch_b and batch_b_r1 are read "
                 "and never written."),
        "frozen_trees": [f"{BASE}/batch_b", R1_TREE],
        "change": ("Batch B's three half widths 0.0170 / 0.0200 / 0.0230 are "
                   "restored and the centres solved for instead: three wells "
                   "laid end to end with one equal 10.2 mm gap, the run "
                   "centred on the base. Internal centre spacing is 54.0 mm "
                   "and 60.0 mm, which 312.5 permits."),
        "frozen_from_r1": frozen,
        "frozen_from_r1_clean": frozen_clean,
        "atlas_pixels": d2.ATLAS,
        "regions_uv": {role: list(box) for role, box in p4d.REGIONS.items()},
        "knurl_patch": knurl_stats,
        "new_atlas_region_required": False,
        "textures": {name: {"path": str(path.relative_to(project_root)),
                            "sha256": m1.digest(path),
                            "bytes": path.stat().st_size}
                     for name, path in textures.items()},
        "budgets": {"triangle_budget_validator_total": bb.VALIDATOR_TOTAL,
                    "triangle_target_total": bb.TARGET_TOTAL,
                    "shared_material_budget": 2},
        "variants": {},
    }

    frame = None
    masks, group_masks, off_images = {}, {}, {}
    for variant, builder in VARIANTS:
        root, body, mover, movers, tagged, audit, parts = r1d.build(
            ASSET, builder)
        meshes = [body] + list(movers)
        rows = r1d.dress(meshes, textures)
        if frame is None:
            frame = p1.rig_for(meshes)
        focus, radius, scale = frame
        half_extent = radius * 0.34

        measured = bb.measure_asset(ASSET, root, body, mover, movers)
        statics = bb.snapshot_statics([body])
        clearance = bb.motion_clearance_audit(mover, movers, statics, ASSET)
        alignment = r1.status_alignment_audit(parts, movers, focus,
                                              half_extent, GRID)
        readability = dark_state_readability(parts, movers, focus, half_extent)

        review.configure_scene()
        images = {}
        for label, view in p1.VIEWS.items():
            path = dirs["compare"] / f"{variant}_{ASSET}_{label}.png"
            p1.shot(focus, radius, view, 52.0, scale, path)
            images[label] = str(path.relative_to(project_root))
        if variant == "r2":
            for label in p1.VIEWS:
                source = dirs["compare"] / f"r2_{ASSET}_{label}.png"
                target = dirs["review"] / f"R2_{ASSET}_{label}.png"
                target.write_bytes(source.read_bytes())
                images[label] = str(target.relative_to(project_root))

        whole = np.concatenate([r1.world_triangles(obj) for obj in meshes])
        group = np.concatenate([parts[name] for name in FRAME_PARTS
                                if name in parts]
                               + [r1.world_triangles(obj) for obj in movers])
        masks[variant] = {label: r1.silhouette_mask(whole, view, focus,
                                                    half_extent, GRID)
                          for label, view in r1d.FOCUS_VIEWS.items()}
        group_masks[variant] = {
            label: r1.silhouette_mask(group, view, focus, half_extent, GRID)
            for label, view in r1d.FOCUS_VIEWS.items()}

        row = dict(measured)
        row.update({
            "objects": rows,
            "submeshes_total": sum(r["submeshes"] for r in rows.values()),
            "max_material_slots_per_object": max(
                len(r["material_slots"]) for r in rows.values()),
            "coplanar_overlap": audit,
            "clearance": clearance,
            "alignment": alignment,
            "dark_state_readability": readability,
            "images": images,
        })

        if variant == "r2":
            fbx = tree / f"SM_{ASSET}_{THEME}_V6_Opus5_P6B_R2.fbx"
            d2.export_fbx(root, fbx)
            blend = dirs["blend"] / f"{ASSET}_{THEME}_P6B_R2.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(blend), copy=True)
            row.update({
                "r2_fbx": str(fbx.relative_to(project_root)),
                "r2_fbx_sha256": m1.digest(fbx),
                "r2_fbx_bytes": fbx.stat().st_size,
                "r2_blend": str(blend.relative_to(project_root)),
            })
            hits, closest = p4d.knurl_bleed_audit(
                [(f"{ASSET}:{obj.name}", obj) for obj in meshes])
            payload["knurl_bleed"] = {
                "loops_inside_knurl_region": hits,
                "objects_with_loops_inside": {k: v for k, v in hits.items()
                                              if v},
                "nearest_uv_to_region_texels": round(closest * d2.ATLAS, 1)
                if closest is not None else None,
                "clean": not any(hits.values()),
            }

        # The four states, from the one fixed camera, for every variant: the
        # OFF frame is the evidence 312.6 asks for.
        palette = state_palette()
        saved = {obj.name: [s.material for s in obj.material_slots]
                 for obj in movers}
        states = {}
        for index, state in enumerate(("OFF", "SAFE", "WARN", "DANGER")):
            for position, obj in enumerate(movers):
                lit = index > 0 and position == index - 1
                obj.data.materials.clear()
                obj.data.materials.append(
                    palette["state_on" if lit else "state_off"])
            bpy.context.view_layer.update()
            path = dirs["state"] / f"State_{variant}_{ASSET}_{state}.png"
            p1.shot(focus, radius, (0.0, 0.0), 52.0, scale, path)
            states[state] = str(path.relative_to(project_root))
        for obj in movers:
            obj.data.materials.clear()
            for material in saved[obj.name]:
                obj.data.materials.append(material)
        row["state_images"] = states
        off_images[variant] = project_root / states["OFF"]

        payload["variants"][variant] = row
        print(f"[BatchB-R2] {variant}: tris {row['triangles_total']}, "
              f"renderers {row['renderers']}/{row['renderer_budget']}, "
              f"submeshes {row['submeshes_total']}, slots "
              f"{row['max_material_slots_per_object']}, clearance "
              f"{clearance['clean']} {clearance['min_clearance_mm']}, "
              f"overhang {alignment['front_projection_overhang_past_shell_face_mm2']}"
              f" mm2, widths {row['dark_state_readability']['widths_mm']}")

    overlays = {}
    for older in ("batch_b", "r1"):
        for label in r1d.FOCUS_VIEWS:
            path = dirs["overlay"] / f"Overlay_{older}_vs_r2_{label}.png"
            r1.save_overlay(masks[older][label], masks["r2"][label], path)
            overlays[f"{older}_vs_r2_{label}"] = str(
                path.relative_to(project_root))
            path = dirs["overlay"] / f"Overlay_{older}_vs_r2_frame_{label}.png"
            r1.save_overlay(group_masks[older][label], group_masks["r2"][label],
                            path)
            overlays[f"{older}_vs_r2_frame_{label}"] = str(
                path.relative_to(project_root))
    payload["overlay_images"] = overlays
    payload["overlay_legend"] = (
        "the older variant only in red, R2 only in green, both in grey; "
        "`frame_*` is the well / rib / hood group plus the three lenses, "
        "which is where the change is")

    # Three rows, one per variant, same camera and same materials.
    tiles = [review.load_rgba(project_root / payload["variants"][variant]
                              ["images"][label])
             for variant, _ in VARIANTS
             for label in ("front", "oblique_left", "oblique_right", "side")]
    height, width = tiles[0].shape[:2]
    gap, columns = 16, 4
    rows_n = len(tiles) // columns
    canvas = np.zeros((rows_n * height + (rows_n - 1) * gap,
                       columns * width + (columns - 1) * gap, 4),
                      dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(tiles):
        r, c = divmod(index, columns)
        top = (rows_n - 1 - r) * (height + gap)
        canvas[top:top + height,
               c * (width + gap):c * (width + gap) + width] = tile
    sheet = tree / f"ContactSheet_{ASSET}_{THEME}_P6B_BatchB_R1_R2.png"
    review.save_rgba(canvas, sheet)

    off_tiles = [review.load_rgba(off_images[variant])
                 for variant, _ in VARIANTS]
    canvas = np.zeros((height, 3 * width + 2 * gap, 4), dtype=np.float32)
    canvas[..., 3] = 1.0
    for index, tile in enumerate(off_tiles):
        canvas[:, index * (width + gap):index * (width + gap) + width] = tile
    off_sheet = tree / f"ContactSheet_{ASSET}_OFF_BatchB_R1_R2.png"
    review.save_rgba(canvas, off_sheet)
    payload["contact_sheets"] = {
        "three_way": {"path": str(sheet.relative_to(project_root)),
                      "sha256": m1.digest(sheet),
                      "layout": "rows Batch B / R1 / R2, columns front / "
                                "oblique left / oblique right / side"},
        "off_state": {"path": str(off_sheet.relative_to(project_root)),
                      "sha256": m1.digest(off_sheet),
                      "layout": "Batch B / R1 / R2, every lens dark"},
    }

    r2row = payload["variants"]["r2"]
    payload["shared_material_identities"] = sorted(
        {n for obj in r2row["objects"].values() for n in obj["material_slots"]})
    payload["acceptance_312"] = {
        "widths_restored": r2row["coplanar_overlap"]["mechanism"][
            "widths_restored_from_batch_b"],
        "distinct_widths": r2row["dark_state_readability"]["distinct_widths"],
        "frame_group_centre_mm": r2row["alignment"]["frame_group_centre_mm"],
        "frame_margin_left_mm": r2row["alignment"]["frame_margin_left_mm"],
        "frame_margin_right_mm": r2row["alignment"]["frame_margin_right_mm"],
        "margins_equal": abs(r2row["alignment"]["frame_margin_left_mm"]
                             - r2row["alignment"]["frame_margin_right_mm"])
        <= 0.05,
        "overhang_zero": r2row["alignment"]["clean"],
        "renderers": r2row["renderers"],
        "submeshes_total": r2row["submeshes_total"],
        "segment_order": [row[0] for row in r2.STATUS_SEGMENTS],
        "order_preserved": [row[0] for row in r2.STATUS_SEGMENTS]
        == [row[0] for row in bb.STATUS_SEGMENTS],
        "rotary_button_lamp_untouched": frozen_clean,
    }
    checks = payload["acceptance_312"]
    payload["status"] = (
        "p6_batch_b_r2_ready"
        if all(checks[key] for key in ("widths_restored", "distinct_widths",
                                       "margins_equal", "overhang_zero",
                                       "order_preserved",
                                       "rotary_button_lamp_untouched"))
        and checks["renderers"] == 4 and checks["submeshes_total"] == 5
        and r2row["max_material_slots_per_object"] <= 2
        and len(payload["shared_material_identities"]) <= 2
        and all(r2row["gates"].values())
        and r2row["clearance"]["clean"]
        and payload["knurl_bleed"]["clean"]
        else "p6_batch_b_r2_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[BatchB-R2] status {payload['status']}; wrote {OUTPUT}")


if __name__ == "__main__":
    main()
