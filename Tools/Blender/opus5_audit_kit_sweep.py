"""Audit kit sweep: every shipped model, through the FBX-only checks.

The checks the kit consolidated were each written after a headset review found
something, and each was then run on one instrument. This runs them across the
whole shipped family in one pass, which is the thing that never happened: the
sealed screws lived in Batch A from the start and were found five batches
later only because a new check was written for a different instrument.

Only Tier A runs here - buried geometry, exact coplanar overlap, the display
plane contract and pose interference. Seat and tool access need part-level
geometry and cannot be answered from a joined FBX; they run at candidate build
time instead.

Findings are candidates, not verdicts. Geometry sealed behind a mount plane is
hidden by design; geometry sealed inside a housing is dead. Telling those two
apart is a judgement, so the report ranks and describes rather than failing.

Writes only to ArtSource/Blender/BrushUp/Opus5/AuditKit/Sweep/.

Usage::

    "/Applications/Blender 5.2.app/Contents/MacOS/Blender" --background \
      --factory-startup --python Tools/Blender/opus5_audit_kit_sweep.py -- \
      --project-root "$PWD"
"""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_audit_kit as kit
import opus5_theme4_machined_ergonomics_p1 as p1
import opus5_theme4_full_p6_batch_a as ba
import opus5_theme4_full_p6_batch_b as bb
import opus5_theme4_full_p6_batch_c as bc
import opus5_theme4_full_p6_batch_c_r2 as c2

TREE = "ArtSource/Blender/BrushUp/Opus5/AuditKit/Sweep"
OUTPUT = f"{TREE}/audit_kit_sweep.json"
ROOT = "ArtSource/Blender/BrushUp/Opus5"
D = f"{ROOT}/MachinedErgonomics/delivery_p6"

# The authoritative version of every shipped model, plus the two candidate
# sets waiting on a gate.
SWEEP = [
    ("MeterRound", "MachinedErgonomics", "delivery_p5",
     f"{ROOT}/MachinedErgonomics/delivery_p5/"
     "SM_MeterRound_MachinedErgonomics_V6_Opus5_P5.fbx"),
    ("Lever", "MachinedErgonomics", "fastener_access_r4",
     f"{D}/fastener_access_r4/SM_Lever_MachinedErgonomics_V6_Opus5_FA_R4.fbx"),
    ("Toggle", "MachinedErgonomics", "fastener_access_r4",
     f"{D}/fastener_access_r4/SM_Toggle_MachinedErgonomics_V6_Opus5_FA_R4.fbx"),
    ("MeterMedium", "MachinedErgonomics", "fastener_access_r3",
     f"{D}/fastener_access_r3/"
     "SM_MeterMedium_MachinedErgonomics_V6_Opus5_FA_R3.fbx"),
    ("MeterLarge", "MachinedErgonomics", "fastener_access_r3",
     f"{D}/fastener_access_r3/"
     "SM_MeterLarge_MachinedErgonomics_V6_Opus5_FA_R3.fbx"),
    ("Rotary", "MachinedErgonomics", "fastener_access_r3",
     f"{D}/fastener_access_r3/"
     "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R3.fbx"),
    ("Button", "MachinedErgonomics", "fastener_access_r1",
     f"{D}/fastener_access_r1/"
     "SM_Button_MachinedErgonomics_V6_Opus5_FA_R1.fbx"),
    ("Lamp", "MachinedErgonomics", "fastener_access_r1",
     f"{D}/fastener_access_r1/SM_Lamp_MachinedErgonomics_V6_Opus5_FA_R1.fbx"),
    ("StatusIndicator", "MachinedErgonomics", "fastener_access_r1",
     f"{D}/fastener_access_r1/"
     "SM_StatusIndicator_MachinedErgonomics_V6_Opus5_FA_R1.fbx"),
    ("Throttle", "MachinedErgonomics", "batch_a_r4_b3u_r2",
     f"{D}/batch_a_r4_b3u_r2/"
     "SM_Throttle_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx"),
    ("PowerSlider", "MachinedErgonomics", "batch_a_r4_b3u_r2",
     f"{D}/batch_a_r4_b3u_r2/"
     "SM_PowerSlider_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx"),
    ("WindowMeter", "MachinedErgonomics", "batch_c_r2",
     f"{D}/batch_c_r2/SM_WindowMeter_MachinedErgonomics_V6_Opus5_P6C_R2.fbx"),
    ("WindowPanel", "MachinedErgonomics", "batch_c_r2",
     f"{D}/batch_c_r2/SM_WindowPanel_MachinedErgonomics_V6_Opus5_P6C_R2.fbx"),
    ("TrendMonitor", "MachinedErgonomics", "batch_c",
     f"{D}/batch_c/SM_TrendMonitor_MachinedErgonomics_V6_Opus5_P6C.fbx"),
    ("TrendMonitor", "OrbitalAnalog", "TrendMonitorThemes/T1",
     f"{ROOT}/TrendMonitorThemes/T1/"
     "SM_TrendMonitor_OrbitalAnalog_V6_Opus5_T1.fbx"),
    ("TrendMonitor", "ForgeBrass", "TrendMonitorThemes/T1",
     f"{ROOT}/TrendMonitorThemes/T1/"
     "SM_TrendMonitor_ForgeBrass_V6_Opus5_T1.fbx"),
    ("TrendMonitor", "KineticSafety", "TrendMonitorThemes/T1",
     f"{ROOT}/TrendMonitorThemes/T1/"
     "SM_TrendMonitor_KineticSafety_V6_Opus5_T1.fbx"),
    ("WindowPanel", "OrbitalAnalog", "WindowPanel/WP3/r2",
     f"{ROOT}/WindowPanel/WP3/r2/SM_WindowPanel_OrbitalAnalog_WP3.fbx"),
    ("WindowPanel", "ForgeBrass", "WindowPanel/WP3/r2",
     f"{ROOT}/WindowPanel/WP3/r2/SM_WindowPanel_ForgeBrass_WP3.fbx"),
    ("WindowPanel", "KineticSafety", "WindowPanel/WP3/r2",
     f"{ROOT}/WindowPanel/WP3/r2/SM_WindowPanel_KineticSafety_WP3.fbx"),
    ("WindowPanel", "MachinedErgonomics", "WindowPanel/WP3/r2",
     f"{ROOT}/WindowPanel/WP3/r2/SM_WindowPanel_MachinedErgonomics_WP3.fbx"),
]

# Front axis and its sign per family, and where the mount plane sits.
# Y-forward: the Machined Ergonomics batches, authored with the mount plane
# at max Y and the front at -Y. Z-forward: the trend monitor family and the
# WP3 candidates, mount plane at Z = 0 and front at +Z. Keying this on the
# theme was wrong - the WP3 Machined Ergonomics candidate is Z-forward like
# its three siblings, and reading it as Y-forward reported its display plane
# as failing.
Y_FORWARD = {"front_axis": 1, "front_sign": -1.0,
             "mount_axis": 1, "mount_sign": 1.0}
Z_FORWARD = {"front_axis": 2, "front_sign": 1.0,
             "mount_axis": 2, "mount_sign": -1.0}


def frame_for(tree_name):
    return Z_FORWARD if ("TrendMonitorThemes" in tree_name
                         or "WindowPanel/WP3" in tree_name) else Y_FORWARD


# What each contract asks the display plane to be. §325 allowed a closed slab
# for the Batch C trend monitor; §347 requires a two triangle plane.
DISPLAY_TRIANGLES = {"WindowPanel/WP3/r2": 2, "TrendMonitorThemes/T1": 2,
                     "batch_c": 12}
DISPLAY_MODELS = {"TrendMonitor", "WindowPanel"}
# These two are built without booleans and interpenetrate by construction:
# the lever's hub passes through its plate and its pin sits inside the pillow
# bearings, and the toggle's head lives inside the shell. P5's own audit gated
# a named subset of statics for that reason. From a joined FBX the parts
# cannot be separated, so the number is reported and not judged.
POSE_DESIGNED_CONTACT = {"Lever", "Toggle"}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--pose-steps", type=int, default=48)
    return parser.parse_args(args)


# A candidate tree may redefine what its instrument does. WP3 is the case:
# §347 replaced the Window Panel vane with a flat display_surface and §348
# forbids vane, needle and analog scale nodes outright, so the four WP3
# candidates have no moving part at all. Selecting a contract by model name
# alone found the older rotating Window Panel, looked for its `vane`, and
# filed the miss as "mover object not in FBX" - a measurement failure
# reported where a specification fact belonged.
REVISION_MOTION = {
    "WindowPanel/WP3/r2": {
        "kind": "none",
        "reason": ("WP3 has no moving part by specification: §347 replaced "
                   "the vane with a flat display_surface and §348 forbids "
                   "vane, needle and analog scale nodes"),
    },
}


def motion_for(model, tree_name):
    """The runtime range, read from the contracts rather than guessed.

    `tree_name` selects the revision first: the same model name can mean
    different things in two candidate trees.
    """
    override = REVISION_MOTION.get(tree_name)
    if override is not None:
        return dict(override, source=f"revision override for {tree_name}")
    for table in (c2.CONTRACT, bb.CONTRACT, ba.CONTRACT, bc.CONTRACT):
        row = table.get(model)
        if not row:
            continue
        # Batch A calls it `moving`, Batch B and C call it `movable`.
        mover = row.get("movable") or row.get("moving")
        if row.get("motion") == "rotate":
            low, high = row["blender_range_deg"]
            return {"mover": mover, "axis": row["blender_axis"],
                    "kind": "rotate", "low": float(low), "high": float(high),
                    "source": "batch contract"}
        if row.get("motion") == "translate":
            low, high = row["blender_range_m"]
            # Batch A writes the axis as "Z", Batch B as "+Y": the letter is
            # the axis and a leading minus flips the travel direction. The
            # ranges are already signed, so the sign is only applied when the
            # contract states one.
            axis = row["blender_axis"]
            sign = -1.0 if axis.startswith("-") else 1.0
            return {"mover": mover, "axis": axis[-1], "kind": "translate",
                    "low": float(low) * sign, "high": float(high) * sign,
                    "source": "batch contract"}
    row = p1.MOTION.get(model)
    if row:
        angles = row["audit_deg_blender"]
        return {"mover": row["part"], "axis": row["blender_axis"],
                "kind": "rotate", "low": float(min(angles)),
                "high": float(max(angles)), "source": "p1.MOTION"}
    return None


def classify(cluster, frame, mount_level):
    """Sealed by design, or dead inside the housing?

    A part sitting on the mount plane disappears once the instrument is in a
    panel, and that is intended. A part sealed well in front of it is not
    reachable, not visible and not doing anything.
    """
    axis = frame["mount_axis"]
    depth = abs(cluster["centre_m"][axis] - mount_level)
    behind = depth <= 0.006
    return {
        "distance_from_mount_plane_mm": round(depth * 1000.0, 2),
        "category": "hidden by mounting" if behind else "sealed inside body",
        "needs_review": not behind,
    }


def sweep_one(project_root, model, theme, tree_name, path, pose_steps):
    target = project_root / path
    if not target.exists():
        return {"model": model, "theme": theme, "tree": tree_name,
                "fbx": path, "missing": True}
    frame = frame_for(tree_name)
    objects = kit.load_fbx(target)
    triangles = 0
    for obj in objects:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    points = [obj.matrix_world @ v.co
              for obj in objects for v in obj.data.vertices]
    axis = frame["mount_axis"]
    mount_level = (max(p[axis] for p in points) if frame["mount_sign"] > 0
                   else min(p[axis] for p in points))

    clusters = kit.buried_clusters(objects)
    for cluster in clusters:
        cluster.update(classify(cluster, frame, mount_level))
    review_needed = [c for c in clusters if c["needs_review"]]
    coplanar = kit.coplanar_overlap(objects, axis=frame["front_axis"])

    row = {
        "model": model, "theme": theme, "tree": tree_name, "fbx": path,
        "fbx_sha256": m1.digest(target),
        "objects": sorted(o.name.split(".")[0] for o in objects),
        "triangles": triangles,
        "mount_plane_level_m": round(mount_level, 6),
        "sealed_clusters": len(clusters),
        "sealed_triangles": sum(c["triangles"] for c in clusters),
        "sealed_needing_review": len(review_needed),
        "sealed_triangles_needing_review": sum(c["triangles"]
                                               for c in review_needed),
        "sealed_detail": review_needed[:12],
        "coplanar_overlap": coplanar,
    }

    if model in DISPLAY_MODELS:
        has_display = any(o.name.split(".")[0] == "display_surface"
                          for o in objects)
        if not has_display:
            row["display_plane"] = {
                "not_applicable": ("this revision has no display_surface; "
                                   "it is the pointer version")}
        else:
            row["display_plane"] = kit.display_plane(
                objects, front_axis=frame["front_axis"],
                front_sign=frame["front_sign"],
                expect_triangles=DISPLAY_TRIANGLES.get(tree_name, 2))

    motion = motion_for(model, tree_name)
    if motion and motion["kind"] == "none":
        row["pose_interference"] = {"skipped": motion["reason"],
                                    "source": motion["source"]}
    elif motion:
        mover = next((o for o in objects
                      if o.name.split(".")[0] == motion["mover"]), None)
        if mover is None:
            row["pose_interference"] = {"skipped": "mover object not in FBX",
                                        "expected": motion["mover"]}
        else:
            statics = [o for o in objects if o is not mover]
            sweep_check = (kit.linear_interference
                           if motion["kind"] == "translate"
                           else kit.pose_interference)
            measurements, ok = sweep_check(
                mover, statics, motion["axis"], motion["low"], motion["high"],
                steps=pose_steps)
            measurements["range_source"] = motion["source"]
            measurements["motion_kind"] = motion["kind"]
            rest, rest_ok = sweep_check(
                mover, statics, motion["axis"], 0.0, 0.0, steps=0)
            measurements["intersects_at_rest"] = not rest_ok
            if model in POSE_DESIGNED_CONTACT or not rest_ok:
                # Parts that already overlap before anything moves are the
                # boolean-free construction this family uses - a hub through
                # a plate, a pin in a bearing. A joined FBX cannot name them,
                # so the count is reported and left for a per-part pass.
                measurements["pass"] = None
                measurements["informational"] = (
                    "overlap is present at rest, so it is construction "
                    "rather than a motion defect; a per-part verdict needs "
                    "build-time geometry")
            else:
                measurements["pass"] = ok
            row["pose_interference"] = measurements
    else:
        row["pose_interference"] = {
            "skipped": "no moving part in contract"}
    return row


CHECKS = ("display_contract", "motion_interference", "z_fighting",
          "contact_seam", "sealed_geometry")


def build_tallies(rows):
    """Every model lands in exactly one bucket, for every check.

    §360 rejected a summary that counted twelve models which were never
    examined as passing. The population here is always the full sweep, and
    `Tally.to_dict` refuses to serialise if the buckets do not add up to it.
    """
    tallies = {name: kit.Tally(name, len(rows)) for name in CHECKS}
    for row in rows:
        # §362: two Window Panel revisions for one theme shared this name and
        # landed in two different buckets of the same tally. The tree is what
        # tells them apart.
        subject = f"{row['model']}/{row['theme']}@{row['tree']}"
        if row.get("missing"):
            for tally in tallies.values():
                tally.record(subject, kit.NOT_APPLICABLE,
                             "input FBX not on disk")
            continue

        display = row.get("display_plane")
        if display is None:
            tallies["display_contract"].record(
                subject, kit.NOT_APPLICABLE,
                "non-display model: no screen in its contract")
        elif "not_applicable" in display:
            tallies["display_contract"].record(
                subject, kit.NOT_APPLICABLE,
                "legacy pointer revision: no display_surface to judge")
        else:
            tallies["display_contract"].record(
                subject, kit.PASS if display["clean"] else kit.FAIL)

        pose = row.get("pose_interference") or {}
        if "skipped" in pose:
            tallies["motion_interference"].record(
                subject, kit.NOT_APPLICABLE, pose["skipped"])
        elif pose.get("pass") is True:
            tallies["motion_interference"].record(subject, kit.PASS)
        elif pose.get("pass") is False:
            tallies["motion_interference"].record(subject, kit.FAIL)
        else:
            tallies["motion_interference"].record(
                subject, kit.REVIEW,
                "parts overlap at rest: construction rather than motion, "
                "and a joined FBX cannot name the parts to settle it")

        overlap = row["coplanar_overlap"]
        tallies["z_fighting"].record(
            subject,
            kit.PASS if not overlap["z_fighting_count"] else kit.FAIL)
        tallies["contact_seam"].record(
            subject,
            kit.PASS if not overlap["contact_seam_count"] else kit.REVIEW,
            None if not overlap["contact_seam_count"]
            else "coplanar faces pointing away from each other: hidden "
                 "surface, culled at runtime, not a rendering defect")
        tallies["sealed_geometry"].record(
            subject,
            kit.PASS if not row["sealed_needing_review"] else kit.REVIEW,
            None if not row["sealed_needing_review"]
            else "clusters sealed away from the mount plane: a judgement "
                 "call on dead weight, not a failure")
    return tallies


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    tree.mkdir(parents=True, exist_ok=True)

    rows = []
    for model, theme, tree_name, path in SWEEP:
        row = sweep_one(project_root, model, theme, tree_name, path,
                        args.pose_steps)
        rows.append(row)
        if row.get("missing"):
            print(f"[Sweep] {model:16s} {theme:18s} MISSING")
            continue
        pose = row.get("pose_interference", {})
        pose_note = ("skip" if "skipped" in pose
                     else f"{pose['intersecting_poses']}/{pose['poses']}"
                     + ("*" if pose.get("pass") is None else ""))
        display = row.get("display_plane")
        print(f"[Sweep] {model:16s} {theme:18s} tris {row['triangles']:5d}  "
              f"sealed {row['sealed_clusters']:2d} "
              f"(review {row['sealed_needing_review']:2d}/"
              f"{row['sealed_triangles_needing_review']:4d}tri)  "
              f"zfight {row['coplanar_overlap']['z_fighting_count']} "
              f"seam {row['coplanar_overlap']['contact_seam_count']}  "
              f"pose {pose_note}"
              + ("" if not display else
                 "  display n/a" if "not_applicable" in display
                 else f"  display {display['clean']}"))

    tallies = build_tallies(rows)
    findings = [r for r in rows if not r.get("missing")
                and (r["sealed_needing_review"]
                     or r["coplanar_overlap"]["z_fighting_count"]
                     or (r.get("display_plane") or {}).get("clean") is False
                     or r.get("pose_interference", {}).get("pass") is False)]
    payload = {
        "phase": "AuditKit-Sweep",
        "tier": "A (FBX only)",
        "note": ("checks that need part-level geometry - seat, penetration "
                 "and tool access - are not in this sweep and run at "
                 "candidate build time"),
        "module": "Tools/Blender/opus5_audit_kit.py",
        "driver": "Tools/Blender/opus5_audit_kit_sweep.py",
        "audit_scripts_sha256": kit.script_digests([
            Path(kit.__file__), Path(__file__)]),
        "checks_run": list(CHECKS),
        "verdict_values": list(kit.VERDICT_VALUES),
        "pose_steps": args.pose_steps,
        "models_swept": len([r for r in rows if not r.get("missing")]),
        "models_missing": [r["fbx"] for r in rows if r.get("missing")],
        "models_with_findings": [f"{r['model']}/{r['theme']}@{r['tree']}"
                                 for r in findings],
        "totals": {
            "triangles": sum(r["triangles"] for r in rows
                             if not r.get("missing")),
            "sealed_clusters": sum(r["sealed_clusters"] for r in rows
                                   if not r.get("missing")),
            "sealed_triangles_needing_review": sum(
                r["sealed_triangles_needing_review"] for r in rows
                if not r.get("missing")),
            "z_fighting_pairs": sum(
                r["coplanar_overlap"]["z_fighting_count"]
                for r in rows if not r.get("missing")),
            "contact_seams": sum(
                r["coplanar_overlap"]["contact_seam_count"]
                for r in rows if not r.get("missing")),
        },
        "tallies": {name: tally.to_dict()
                    for name, tally in tallies.items()},
        "tally_note": (
            "§361 fixed the motion baseline at PASS 6 / FAIL 0 / REVIEW 4 / "
            "N/A 11, counting PowerSlider as the only instrument whose "
            "motion had no check. Button declares `motion: translate` too, "
            "so the uncovered count was 5, not 4. The linear check now "
            "covers both, and its A2 fixture separates the shipped original "
            "from a manufactured interference, so both move from REVIEW to "
            "their measured verdicts. The three structural REVIEWs - Lever, "
            "Toggle and Throttle, which overlap before anything moves - are "
            "unchanged."),
        "results": rows,
        "interpretation": (
            "findings are candidates for judgement, not failures: geometry "
            "sealed against the mount plane is hidden by design, geometry "
            "sealed inside the body is dead weight"),
    }
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[Sweep] {payload['models_swept']} models, "
          f"{payload['totals']['sealed_triangles_needing_review']} sealed "
          f"triangles to review, "
          f"{payload['totals']['z_fighting_pairs']} z-fighting pairs, "
          f"{payload['totals']['contact_seams']} contact seams")
    print(f"[Sweep] findings on: {payload['models_with_findings']}")
    for name in CHECKS:
        counts = payload["tallies"][name]["counts"]
        print(f"[Sweep] {name:20s} of {payload['tallies'][name]['population']}"
              + "".join(f"  {value} {counts[value]:2d}"
                        for value in kit.VERDICT_VALUES))


if __name__ == "__main__":
    main()
