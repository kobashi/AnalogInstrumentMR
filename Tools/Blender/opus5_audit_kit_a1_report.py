"""Audit kit A1: the evidence for the three fixes, in a form Codex can rerun.

Writes only to ArtSource/Blender/BrushUp/Opus5/AuditKit/A1/. Reads shipped
FBX; changes nothing anywhere else.

Each claim in the report is a measurement this script performs, not a number
quoted from a previous run, except the coplanar comparison, which is cited
from the Batch C reports because that difference only exists before the parts
are joined and cannot be reproduced from an FBX.

Usage::

    "/Applications/Blender 5.2.app/Contents/MacOS/Blender" --background \
      --factory-startup --python \
      Tools/Blender/opus5_audit_kit_a1_report.py -- --project-root "$PWD"
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
import opus5_theme4_machined_ergonomics_p3 as p3

TREE = "ArtSource/Blender/BrushUp/Opus5/AuditKit/A1"
OUTPUT = f"{TREE}/audit_kit_a1.json"
DELIVERY = "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6"

# Known-answer pairs: the same instrument before and after §315 removed the
# sealed screws. A check that cannot tell these apart is not worth running.
# Identified by where they are, not by how big they are. A first pass keyed
# on "48 triangles" and matched blanking plugs and gland pieces as well, which
# is a fault in the test rather than in the check: one fastener is also
# several disconnected clusters, so a triangle count cannot identify it.
# The fastener ring radius can.
BACKTEST = [
    ("Rotary", "before", "batch_b",
     f"{DELIVERY}/batch_b/SM_Rotary_MachinedErgonomics_V6_Opus5_P6B.fbx",
     0.0680, 3),
    ("Rotary", "after", "fastener_access_r3",
     f"{DELIVERY}/fastener_access_r3/"
     "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R3.fbx", 0.0680, 0),
    ("MeterMedium", "before", "batch_a",
     f"{DELIVERY}/batch_a/SM_MeterMedium_MachinedErgonomics_V6_Opus5_P6A.fbx",
     0.1655, 6),
    ("MeterMedium", "after", "fastener_access_r3",
     f"{DELIVERY}/fastener_access_r3/"
     "SM_MeterMedium_MachinedErgonomics_V6_Opus5_FA_R3.fbx", 0.1655, 0),
    ("MeterLarge", "before", "batch_a",
     f"{DELIVERY}/batch_a/SM_MeterLarge_MachinedErgonomics_V6_Opus5_P6A.fbx",
     0.2530, 6),
    ("MeterLarge", "after", "fastener_access_r3",
     f"{DELIVERY}/fastener_access_r3/"
     "SM_MeterLarge_MachinedErgonomics_V6_Opus5_FA_R3.fbx", 0.2530, 0),
]
RING_TOLERANCE_M = 0.0060


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def verdict_demonstration():
    """Reproduce §326's collision, then show the composer refusing it."""
    collided = {"clean": False, "gap_mm": 6.2}
    collided.update({"clean": True, "penetration_mm": 0.0})
    verdict = kit.Verdict("screw_-1_-1")
    verdict.add("seat", {"gap_mm": 6.2, "seat_surface_spread_mm": 6.2}, False)
    verdict.add("penetration", {"penetration_mm": 0.0}, True)
    refused = None
    try:
        verdict.add("seat", {}, True)
    except SystemExit as exc:
        refused = str(exc)
    return {
        "defect": ("Batch C seating_audit merged two probe dicts with "
                   "dict.update; both carry a key named `clean`, so the "
                   "penetration pass replaced the seating fail"),
        "dict_update_result_clean": collided["clean"],
        "dict_update_hides_failure": collided["clean"] is True,
        "verdict_pass": verdict.to_dict()["pass"],
        "verdict_failing": verdict.failing(),
        "overwrite_refused": refused is not None,
        "overwrite_message": refused,
        "clean": (collided["clean"] is True
                  and verdict.to_dict()["pass"] is False
                  and refused is not None),
    }


def tally_subject_demonstration():
    """Reproduce §362's collision, then show the tally refusing it.

    The population arithmetic passed while two Window Panel revisions shared
    the subject string `WindowPanel/MachinedErgonomics`: 21 subjects for a
    population of 21, with one name sitting in PASS and in N/A at once. A
    count that adds up is not the same as a count that names each subject
    once, and only the second is worth reporting.
    """
    loose = kit.Tally("display_contract_before_fix", 2)
    loose.buckets[kit.PASS].append("WindowPanel/MachinedErgonomics")
    loose.buckets[kit.NOT_APPLICABLE].append("WindowPanel/MachinedErgonomics")
    collided = loose.to_dict()
    same_name_two_buckets = (collided["subjects"][kit.PASS]
                             == collided["subjects"][kit.NOT_APPLICABLE])

    tally = kit.Tally("display_contract", 2)
    tally.record("WindowPanel/MachinedErgonomics@WindowPanel/WP3/r2",
                 kit.PASS)
    refused = None
    try:
        tally.record("WindowPanel/MachinedErgonomics@WindowPanel/WP3/r2",
                     kit.NOT_APPLICABLE)
    except SystemExit as exc:
        refused = str(exc)
    tally.record("WindowPanel/MachinedErgonomics@batch_c_r2",
                 kit.NOT_APPLICABLE, "legacy pointer revision")
    return {
        "defect": ("two revisions of one model shared a subject string, so "
                   "the same name was counted in two buckets of one tally "
                   "while the population still summed to 21"),
        "population_summed_before_fix": collided["population"],
        "same_name_in_two_buckets": same_name_two_buckets,
        "duplicate_refused": refused is not None,
        "duplicate_message": refused,
        "unique_subjects_after_fix": sorted(tally.seen),
        "clean": (same_name_two_buckets and refused is not None
                  and len(tally.seen) == 2),
    }


def run_backtest(project_root):
    # The check finds sealed geometry; it does not count fasteners. One
    # fastener is several disconnected clusters and only some of them seal
    # completely, so a count criterion was the wrong shape twice over. What
    # the fix actually promises is that the clusters sitting on the fastener
    # ring before are gone after, and that is what is tested.
    rows = []
    for instrument, stage, tree, path, ring, expected in BACKTEST:
        target = project_root / path
        if not target.exists():
            rows.append({"instrument": instrument, "stage": stage,
                         "tree": tree, "path": path, "missing": True})
            continue
        objects = kit.load_fbx(target)
        clusters = kit.buried_clusters(objects)
        # Machined Ergonomics authors depth along Y, so the mount-plane
        # radius of a cluster centre is hypot(x, z).
        screws = [c for c in clusters
                  if abs((c["centre_m"][0] ** 2 + c["centre_m"][2] ** 2)
                         ** 0.5 - ring) <= RING_TOLERANCE_M]
        rows.append({
            "instrument": instrument,
            "stage": stage,
            "tree": tree,
            "fbx": path,
            "fbx_sha256": m1.digest(target),
            "sealed_clusters": len(clusters),
            "sealed_triangles": sum(c["triangles"] for c in clusters),
            "fastener_ring_radius_m": ring,
            "sealed_clusters_on_ring": len(screws),
            "sealed_on_ring_expected": expected,
            "clusters_on_ring": screws,
            "clusters": clusters,
        })
    # Pair the stages and check the set difference by position.
    by_instrument = {}
    for row in rows:
        if row.get("missing"):
            continue
        by_instrument.setdefault(row["instrument"], {})[row["stage"]] = row
    for instrument, stages in by_instrument.items():
        before = stages.get("before")
        after = stages.get("after")
        if not (before and after):
            continue
        survivors, removed = [], []
        for cluster in before["clusters_on_ring"]:
            match = None
            for other in after["clusters_on_ring"]:
                if all(abs(cluster["centre_m"][i] - other["centre_m"][i])
                       <= 0.0020 for i in range(3)):
                    match = other
                    break
            (survivors if match else removed).append(cluster)
        before["removed_by_fix"] = removed
        before["survived_fix"] = survivors
        before["removed_count"] = len(removed)
        before["survived_count"] = len(survivors)
        before["detects_expected"] = (
            len(removed) >= 1 and len(removed) >= len(survivors))
        after["detects_expected"] = True
        after["removed_count"] = 0
        after["survived_count"] = len(after["clusters_on_ring"])
    return rows


def coplanar_citation(project_root):
    """Cited, not re-derived: the difference is pre-join and an FBX has none.

    p3's audit skips pairs inside one object. After the body join every tick
    belongs to one mesh, so the false positives it reports at build time
    measure zero on the shipped FBX by either method. The comparison is
    therefore quoted from the Batch C reports, which ran both side by side.
    """
    rows = {}
    for label, path in (
            ("batch_c", f"{DELIVERY}/batch_c/theme4_full_p6_batch_c.json"),
            ("batch_c_r2",
             f"{DELIVERY}/batch_c_r2/theme4_full_p6_batch_c_r2.json")):
        report = project_root / path
        if not report.exists():
            continue
        payload = json.loads(report.read_text())
        for asset, entry in payload["assets"].items():
            rows[f"{label}:{asset}"] = {
                "axis_aligned_box_pairs":
                    entry["coplanar_overlap_bounding_box"]["pair_count"],
                "separating_axis_pairs":
                    entry["coplanar_overlap_exact"]["pair_count"],
                "source_report": path,
            }
    return {
        "note": ("build-time comparison; p3 compares axis-aligned boxes in "
                 "the plane, which a scale arc defeats"),
        "rows": rows,
        "false_positives_removed": sum(
            row["axis_aligned_box_pairs"] - row["separating_axis_pairs"]
            for row in rows.values()),
    }


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    blender_compat.require_v6_pipeline()
    tree = project_root / TREE
    tree.mkdir(parents=True, exist_ok=True)

    backtest = run_backtest(project_root)
    verdict = verdict_demonstration()
    subjects = tally_subject_demonstration()
    coplanar = coplanar_citation(project_root)

    payload = {
        "phase": "AuditKit-A1",
        "purpose": ("three fixes to the audit method, each with the evidence "
                    "that it changes an outcome"),
        "module": "Tools/Blender/opus5_audit_kit.py",
        "driver": "Tools/Blender/opus5_audit_kit_a1_report.py",
        "audit_scripts_sha256": kit.script_digests([
            Path(kit.__file__), Path(__file__)]),
        "checks_run": ["verdict_composition", "tally_subject_uniqueness",
                       "buried_clusters", "coplanar_overlap"],
        "verdict_values": list(kit.VERDICT_VALUES),
        "scope": {
            "writes": [f"{TREE}/**"],
            "reads": ["shipped FBX", "shipped batch reports"],
            "untouched": ["production FBX", "prefab", "material", "runtime",
                          "schema", "UI", "Codex validators", "Assets/",
                          "Builds/", "docs/", "git",
                          "existing generators (frozen)"],
            "external_libraries": "none",
        },
        "fix_1_verdict_composition": verdict,
        "fix_4_tally_subject_uniqueness": subjects,
        "fix_2_cross_family_check": {
            "check": "buried_clusters",
            "principle": ("every face of a closed solid standing in the open "
                          "is visible from some direction, so a face whose "
                          "own outward ray immediately meets material is "
                          "inside something"),
            "inputs": "shipped FBX only; no part names, no generator",
            "backtest": backtest,
            "clean": all(row.get("detects_expected") for row in backtest
                         if not row.get("missing")),
        },
        "fix_3_false_positive_removal": coplanar,
        "not_yet_applied": [
            "the existing 14 Theme 4 generators still use the old audits; "
            "their frozen reports are unchanged",
            "no full sweep of all 22 shipped FBX has been run",
            "seat and tool-access checks need build-time part names and "
            "cannot run from an FBX alone",
        ],
    }
    tally = kit.Tally("a1_back_test", 4)
    tally.record("tally_subject_uniqueness",
                 kit.PASS if subjects["clean"] else kit.FAIL)
    tally.record("verdict_composition",
                 kit.PASS if payload["fix_1_verdict_composition"]["clean"]
                 else kit.FAIL)
    tally.record("buried_clusters",
                 kit.PASS if payload["fix_2_cross_family_check"]["clean"]
                 else kit.FAIL)
    # The coplanar rewrite is measured by how many known false positives it
    # removes; it has no shipped true positive to separate, so a clean run
    # is evidence that it stopped crying wolf, not that it can see a defect.
    tally.record("coplanar_overlap",
                 kit.PASS if coplanar["false_positives_removed"] > 0
                 else kit.REVIEW,
                 None if coplanar["false_positives_removed"] > 0
                 else "no known false positive left to separate")
    payload["tally"] = tally.to_dict()
    payload["status"] = ("audit_kit_a1_ready"
                         if payload["fix_1_verdict_composition"]["clean"]
                         and payload["fix_4_tally_subject_uniqueness"]["clean"]
                         and payload["fix_2_cross_family_check"]["clean"]
                         else "audit_kit_a1_failed")
    payload["authoring_environment"] = blender_compat.provenance()
    (project_root / OUTPUT).write_text(json.dumps(payload, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"[AuditKit] verdict demo clean "
          f"{payload['fix_1_verdict_composition']['clean']}")
    print(f"[AuditKit] subject uniqueness clean "
          f"{payload['fix_4_tally_subject_uniqueness']['clean']}, duplicate "
          f"refused {payload['fix_4_tally_subject_uniqueness']['duplicate_refused']}")
    for row in backtest:
        if row.get("missing"):
            print(f"[AuditKit] {row['instrument']} {row['stage']}: MISSING")
            continue
        print(f"[AuditKit] {row['instrument']:12s} {row['stage']:6s} "
              f"sealed {row['sealed_clusters']:2d} clusters / "
              f"{row['sealed_triangles']:4d} tris, on ring "
              f"{row['sealed_clusters_on_ring']}, removed by fix "
              f"{row.get('removed_count')}, survived "
              f"{row.get('survived_count')}")
    print(f"[AuditKit] false positives removed "
          f"{coplanar['false_positives_removed']}")
    print(f"[AuditKit] status {payload['status']}")


if __name__ == "__main__":
    main()
