"""Phase M2n3: publish the three verified meter candidates into the candidate tree.

Alignment 184.4. Nothing is measured again and nothing is re-decided here. The
FBX that M2n3 verified are promoted as they are, with the publish transaction
that refuses to replace an existing canonical output: staged in a temporary
directory, verified by re-reading, then the FBX first and the report last, so
the report is the commit marker.

The bytes are reused when the staged FBX still match the hashes alignment 183
recorded. If one is missing or has moved, the trial's own export runs once with
the approved settings - `mesh_smooth_type="EDGE"`, `use_triangles=False`, the
export-normalized path, and the custom properties copied onto the export root.

The canonical Blends are hashed before and after. They are opened read-only by
the export path and never saved.

Only the candidate tree is written: `KineticSafety/staging/fbx/`, the candidate
reports, and one handoff summary. No active or production asset, no Unity
asset, no existing manifest or prefab is touched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_meter_m2n3_publish.py -- \
      --project-root "$PWD" --staging /tmp/opus5-m2n3
"""

import argparse
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_contact_migration_m1 as m1
import opus5_d6_canonical_build as m2l
import opus5_meter_fbx_handoff as m2n
import opus5_meter_m2n3_trial as trial
import opus5_publish as publish


SUMMARY = "ArtSource/Blender/BrushUp/Opus5/meter_m2n3_handoff.json"
TRIAL = "ArtSource/Blender/BrushUp/Opus5/meter_m2n3_trial.json"
# The hashes to reuse come from the trial report itself, not from a copy of
# them pasted here: a constant that drifts from the report it claims to quote
# is worse than no constant.
SETTINGS = {
    "mesh_smooth_type": "EDGE",
    "use_triangles": False,
    "export_path": "export-normalized copy, FIXED / EAR_CLIP triangulation",
    "custom_properties": "copied onto the export root",
}


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--staging", required=True)
    return parser.parse_args(args)


def staged_fbx(staging, key):
    return staging / m2n.SOURCES[key]["fbx"]


def candidate_report_path(project_root, key):
    stem = m2n.SOURCES[key]["fbx"].replace("SM_", "").replace(".fbx", "")
    return project_root / m2l.REPORT_DIR / f"{stem}_m2n3_candidate.json"


def published_fbx_path(project_root, key):
    return (
        m2l.theme_dir(project_root) / "staging/fbx" / m2n.SOURCES[key]["fbx"]
    )


def staged_state(staging, recorded):
    """Are the verified bytes still on disk, unchanged?"""
    rows = {}
    for key in m2n.SOURCES:
        path = staged_fbx(staging, key)
        if not path.is_file():
            rows[key] = {"present": False, "reusable": False}
            continue
        digest = m1.digest(path)
        expected = recorded.get(key)
        rows[key] = {
            "present": True,
            "bytes": path.stat().st_size,
            "sha256": digest,
            "recorded_sha256": expected,
            "reusable": bool(expected) and digest == expected,
        }
    return rows


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    staging = Path(args.staging)
    blender_compat.require_v6_pipeline()

    payload = {
        "phase": "M2n3",
        "note": (
            "Candidate handoff publish (alignment 184.4). The candidate tree "
            "only: no active or production asset, no Unity asset, no existing "
            "manifest or prefab is written."
        ),
        "settings": SETTINGS,
        "production_approval": False,
    }
    started = time.perf_counter()
    try:
        recorded = {}
        trial_report = project_root / TRIAL
        if trial_report.is_file():
            measured = json.loads(trial_report.read_text())
            recorded = {
                key: model["fbx_sha256"]
                for key, model in measured.get("models", {}).items()
            }
        payload["source_hashes_before"] = trial.source_hashes(project_root)
        for key, row in payload["source_hashes_before"].items():
            if not row["blend_matches_alignment_140"]:
                raise SystemExit(f"[Opus5M2n3Publish] {key}: source hash moved")

        state = staged_state(staging, recorded)
        payload["staged_fbx_before_publish"] = state
        if not all(row["reusable"] for row in state.values()):
            print("[Opus5M2n3Publish] staged bytes unusable; exporting once")
            trial.do_export(project_root, staging)
            state = staged_state(
                staging,
                {
                    key: m1.digest(staged_fbx(staging, key))
                    for key in m2n.SOURCES
                },
            )
            payload["re_exported"] = True
            payload["staged_fbx_after_export"] = state
        else:
            payload["re_exported"] = False
            print("[Opus5M2n3Publish] reusing the verified bytes for all three")

        measured = json.loads((project_root / TRIAL).read_text())
        results = {}
        for key in m2n.SOURCES:
            source = staged_fbx(staging, key)
            target = published_fbx_path(project_root, key)
            report_path = candidate_report_path(project_root, key)
            model = measured["models"][key]
            report = {
                "phase": "M2n3",
                "model": key,
                "revision": m2n.SOURCES[key]["revision"],
                "status": "candidate_handoff_approved",
                "production_approval": False,
                "source": payload["source_hashes_before"][key],
                "settings": SETTINGS,
                "fbx": m2n.SOURCES[key]["fbx"],
                "staged_sha256": state[key]["sha256"],
                "gates": model["gates"],
                "failing_gates": model["failing_gates"],
                "inventory_identical_note": (
                    "alignment 184.1.4: the rounding-boundary difference is "
                    "0.000022 mm unrounded and is a practical pass"
                ),
                "bounds_full_precision": model["bounds_full_precision"],
                "uv_selection_metadata": model["uv_selection_metadata"],
                "authoring_environment": blender_compat.provenance(),
            }

            def save(destination, origin=source):
                shutil.copyfile(origin, destination)

            def reopen(destination, origin=source):
                if m1.digest(destination) != m1.digest(origin):
                    raise publish.PublishFailed(
                        f"{destination.name}: staged copy does not match"
                    )

            record = publish.publish(
                target,
                report_path,
                report,
                problems=[],
                save_blend=save,
                reopen_blend=reopen,
            )
            results[key] = {
                "fbx": str(target.relative_to(project_root)),
                "fbx_bytes": target.stat().st_size,
                "fbx_sha256": m1.digest(target),
                "report": str(report_path.relative_to(project_root)),
                "report_sha256": m1.digest(report_path),
                "bytes_reused_from_trial": not payload["re_exported"],
                "publish": record,
                "status": "candidate_handoff_approved",
            }
            print(
                f"[Opus5M2n3Publish] {key}: {target.name} "
                f"{target.stat().st_size} bytes, report {report_path.name}"
            )
        payload["models"] = results
        payload["source_hashes_after"] = trial.source_hashes(project_root)
        payload["sources_unchanged"] = (
            payload["source_hashes_before"] == payload["source_hashes_after"]
        )
        payload["status"] = (
            "candidate_handoff_published"
            if payload["sources_unchanged"]
            else "source changed during publish"
        )
    except Exception:  # noqa: BLE001 - recorded, then written out below
        payload["status"] = "exception"
        payload["traceback"] = traceback.format_exc()
    finally:
        payload["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        payload["authoring_environment"] = blender_compat.provenance()
        output = project_root / SUMMARY
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(
            f"[Opus5M2n3Publish] status {payload.get('status')}, sources "
            f"unchanged {payload.get('sources_unchanged')}"
        )


if __name__ == "__main__":
    main()
