"""Phase M2l1: the evidence M2l published without.

Alignment 128.2. The three canonical Blends are sound and are not rebuilt. Two
things about how they were published are not, and both are fixed without
touching a byte of what was published.

* M2l re-checked the production source hash straight after each audit and then
  rendered everything before publishing, so the check was not immediately
  before the publish the way 126.2-1 asked. The script is corrected for future
  runs; for the Blends already on disk this pass can only verify integrity
  *now*, and says so rather than dressing it up as the check that was missed.
* 126.2-6 asked for fixed comparison sheets. M2l produced the two halves and
  never put them side by side. The 27 sheets are built here from the existing
  labelled PNGs, which are read and not modified.

Nothing here writes to a canonical Blend, a commit-marker report or any of the
108 published PNGs. In particular, no field is back-written into a published
report: `report_sha256` and `promoted` are not knowable at the moment a report
is written, and a report that claims them after the fact is worth less than one
that does not.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_d6_canonical_verify.py -- \
      --project-root "$PWD"
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import opus5_brushup_kinetic_review as review
import opus5_d6_canonical_build as m2l
import opus5_d6_repair_decision as m2k


OUTPUT = (
    "ArtSource/Blender/BrushUp/Opus5/d6_canonical_verification_supplement.json"
)
PREFIX = "d6_canonical_compare"
POSES = ("minimum", "neutral", "maximum")
VIEWS = ("front", "oblique", "section")


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    return parser.parse_args(args)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_model(project_root, key):
    """Re-hash what is on disk and check it against what the report claims."""
    plan = m2l.PLAN[key]
    blend = m2l.candidate_path(project_root, key, None)
    report = m2l.report_path(project_root, key, None)
    production = m2k.production_blend(project_root, key)
    payload = json.loads(report.read_text())

    blend_sha = digest(blend)
    claimed = {
        "publish.blend_sha256": payload.get("publish", {}).get("blend_sha256"),
        "published_blend_sha256": payload.get("published_blend_sha256"),
        "staged_sha256": payload.get("staged_sha256"),
    }
    production_sha = digest(production)
    return {
        "model": f"{m2k.THEME}/{key}",
        "revision": plan["revision"],
        "blend": {
            "path": str(blend.relative_to(project_root)),
            "sha256_now": blend_sha,
            "bytes": blend.stat().st_size,
            "claimed_in_report": claimed,
            "matches_report": all(
                value == blend_sha for value in claimed.values() if value
            ),
        },
        "report": {
            "path": str(report.relative_to(project_root)),
            "sha256_now": digest(report),
            "exists": True,
        },
        "production_source": {
            "path": str(production.relative_to(project_root)),
            "sha256_now": production_sha,
            "sha256_in_report": payload.get("source_sha256"),
            "unchanged_since_build": production_sha == payload.get("source_sha256"),
        },
        "commit_evidence": (
            "the commit-marker report exists and the Blend on disk hashes to "
            "the value that report certifies; that pair is what makes the "
            "publish complete under opus5_publish"
        ),
    }


def build_sheets(project_root):
    directory = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / m2k.THEME / "review"
    )
    sheets = {}
    for key in m2l.PLAN:
        for pose in POSES:
            for view in VIEWS:
                stem = f"d6_canonical_{key}"
                before = directory / f"{stem}_production_{pose}_{view}_labelled.png"
                after = directory / f"{stem}_candidate_{pose}_{view}_labelled.png"
                if not before.is_file() or not after.is_file():
                    sheets[f"{key}/{pose}/{view}"] = {
                        "missing": [
                            str(p.relative_to(project_root))
                            for p in (before, after)
                            if not p.is_file()
                        ]
                    }
                    continue
                target = directory / f"{PREFIX}_{key}_{pose}_{view}.png"
                review.contact_sheet(before, after, target)
                image = review.load_rgba(target)
                sheets[f"{key}/{pose}/{view}"] = {
                    "sheet": str(target.relative_to(project_root)),
                    "sheet_sha256": digest(target),
                    "width": int(image.shape[1]),
                    "height": int(image.shape[0]),
                    "sources": {
                        "production": {
                            "path": str(before.relative_to(project_root)),
                            "sha256": digest(before),
                        },
                        "candidate": {
                            "path": str(after.relative_to(project_root)),
                            "sha256": digest(after),
                        },
                    },
                }
    return sheets


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()

    started = time.perf_counter()
    models = {theme: verify_model(project_root, theme) for theme in m2l.PLAN}
    sheets = build_sheets(project_root)

    directory = (
        project_root / "ArtSource/Blender/BrushUp/Opus5" / m2k.THEME / "review"
    )
    published_pngs = sorted(directory.glob("d6_canonical_*_labelled.png"))
    published_plain = sorted(
        p
        for p in directory.glob("d6_canonical_*.png")
        if not p.stem.endswith("_labelled") and not p.stem.startswith(PREFIX)
    )

    integrity = all(
        entry["blend"]["matches_report"]
        and entry["production_source"]["unchanged_since_build"]
        for entry in models.values()
    )
    complete = all("sheet" in entry for entry in sheets.values())

    output = project_root / OUTPUT
    output.write_text(
        json.dumps(
            {
                "phase": "M2l1",
                "note": (
                    "Post-publication integrity verification and the "
                    "comparison sheets M2l did not produce (alignment 128.2). "
                    "Nothing published by M2l is modified."
                ),
                "scope_statement": (
                    "this pass verifies integrity now; it does not and cannot "
                    "prove the immediately-before-publish check that 126.2-1 "
                    "asked for, because that moment has passed"
                ),
                "script_correction": {
                    "file": "Tools/Blender/opus5_d6_canonical_build.py",
                    "change": (
                        "the production source hash is re-read immediately "
                        "before each publish.publish() call, after rendering, "
                        "and a mismatch aborts the publish"
                    ),
                    "applies_to": "future runs only; no canonical revision is rebuilt",
                },
                "report_field_policy": (
                    "report_sha256 and promoted are not back-written into "
                    "published reports; they are not knowable when the report "
                    "is written, and the commit evidence is the report's "
                    "existence plus the Blend hash it certifies"
                ),
                "models": models,
                "integrity_pass": integrity,
                "comparison_sheets": sheets,
                "comparison_sheet_count": sum(
                    1 for entry in sheets.values() if "sheet" in entry
                ),
                "comparison_sheets_complete": complete,
                "published_png_inventory": {
                    "labelled": len(published_pngs),
                    "unlabelled": len(published_plain),
                    "total": len(published_pngs) + len(published_plain),
                },
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "authoring_environment": blender_compat.provenance(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for key, entry in models.items():
        print(
            f"[Opus5D6verify] {key} {entry['revision']}: blend matches report "
            f"{entry['blend']['matches_report']}, source unchanged "
            f"{entry['production_source']['unchanged_since_build']}"
        )
    print(
        f"[Opus5D6verify] sheets {sum(1 for e in sheets.values() if 'sheet' in e)}"
        f"/27 complete={complete}, integrity={integrity}, PNG inventory "
        f"{len(published_pngs) + len(published_plain)}"
    )
    print(f"[Opus5D6verify] -> {output.relative_to(project_root)}")


if __name__ == "__main__":
    main()
