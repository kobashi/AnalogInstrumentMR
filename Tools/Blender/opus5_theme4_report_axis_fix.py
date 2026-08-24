"""Apply alignment 277.3's report-only corrections without rebuilding anything.

Codex asked for two source-report fixes and explicitly forbade regenerating
geometry, UV, palette, images, Blend or FBX. Re-running either generator would
rewrite all of those, so the corrections are applied to the existing JSON
instead, recomputed from the Blender bounds the reports already carry.

1. Unity Y was reported as +Blender Z. Through bakeAxisConversion plus the
   import wrapper's -90 degree X rotation the sign is negated, which Codex
   measured as +0.000583 m on MeterRound's swept centre where the report said
   -0.000583. Every `*_unity` block is recomputed from its Blender twin.
2. The Phase 2 atlas note hard-coded a 56 per cent dominant share; the taper
   moved it to 60.675. The generator now carries a number-free sentence and the
   stored report is brought in line.

Usage::

    python3 Tools/Blender/opus5_theme4_report_axis_fix.py --project-root "$PWD"
"""

import argparse
import json
from pathlib import Path

PHASE1 = "ArtSource/Blender/BrushUp/Opus5/theme4_machined_ergonomics_p1.json"
PHASE2 = "ArtSource/Blender/BrushUp/Opus5/theme4_material_p2.json"
NOTE = ("The area fits the island budget exactly; the shelf pack above is only "
        "indicative and overflows because the dominant object exceeds one "
        "shelf row. A real packer is delivery work. The Blend still carries a "
        "per-object 0-1 unwrap - packing it would change the FBX Codex has "
        "validated.")


def to_unity(bounds):
    lo, hi = bounds["min"], bounds["max"]
    umin = [lo[0], -hi[2], -hi[1]]
    umax = [hi[0], -lo[2], -lo[1]]
    return {
        "min": [round(v, 6) for v in umin],
        "max": [round(v, 6) for v in umax],
        "size": [round(umax[i] - umin[i], 6) for i in range(3)],
        "centre": [round((umin[i] + umax[i]) / 2.0, 6) for i in range(3)],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()

    path = root / PHASE1
    report = json.loads(path.read_text())
    changed = []
    for asset, row in report["assets"].items():
        poses = row["pose_bounds"]
        for key, pose in poses.items():
            if not key.startswith("blender"):
                continue
            before = pose["combined_unity"]["centre"][1]
            pose["combined_unity"] = to_unity(pose["combined"])
            after = pose["combined_unity"]["centre"][1]
            if before != after:
                changed.append(f"{asset}/{key} Y centre {before} -> {after}")
        lo = [min(p["combined_unity"]["min"][i] for k, p in poses.items()
                  if k.startswith("blender")) for i in range(3)]
        hi = [max(p["combined_unity"]["max"][i] for k, p in poses.items()
                  if k.startswith("blender")) for i in range(3)]
        union = poses["collider_union_unity"]
        union["min"] = [round(v, 6) for v in lo]
        union["max"] = [round(v, 6) for v in hi]
        union["size"] = [round(hi[i] - lo[i], 6) for i in range(3)]
        union["centre"] = [round((lo[i] + hi[i]) / 2.0, 6) for i in range(3)]
        pivot = row["motion"]["pivot_local"]
        row["motion"]["pivot_local_unity"] = [round(pivot[0], 6),
                                              round(-pivot[2], 6),
                                              round(-pivot[1], 6)]
        row["motion"]["sign_note"] = (
            "Unity (x, -z, -y) from Blender: bakeAxisConversion plus the "
            "import wrapper's -90 degree X rotation negate Y as well as Z. "
            "Rotation sign also flips: Unity -48 deg is Blender +48 deg. "
            "Alignment 277.3.")
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    path2 = root / PHASE2
    report2 = json.loads(path2.read_text())
    report2["atlas_layout"]["note"] = NOTE
    path2.write_text(json.dumps(report2, indent=2) + "\n", encoding="utf-8")

    print(f"[Theme4AxisFix] corrected {len(changed)} Unity Y values")
    for line in changed:
        print(f"  {line}")
    print("[Theme4AxisFix] Phase 2 atlas note replaced with a number-free form")


if __name__ == "__main__":
    main()
