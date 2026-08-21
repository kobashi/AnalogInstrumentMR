"""Audit the constant-density atlas UV pass across all 39 V6 models.

Codex review item 5.3-3: before the pass can be considered for the production
exporter, it has to hold up on every model and every theme, not just the three
pilot ones. This reads each `*_Retopo.blend`, applies the pass, and reports the
texel-density spread, any part that had to be clamped because it cannot reach
the target inside one quadrant, the world bounds, and which material roles are
present.

Read-only: no blend is saved and nothing under `Assets/` is touched.

Usage::

    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/opus5_uv_atlas_audit_all.py -- \
      --project-root "$PWD" --output <report.json>
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_compat
import export_v6_replacement_candidates as export
import opus5_uv_atlas_pass as uv_pass
import v6_theme_materials


THEMES = ("OrbitalAnalog", "ForgeBrass", "KineticSafety")
KEYS = (
    "MeterRound",
    "MeterMedium",
    "MeterLarge",
    "Lever",
    "Toggle",
    "Rotary",
    "Button",
    "Lamp",
    "Throttle",
    "PowerSlider",
    "StatusIndicator",
    "WindowMeter",
    "WindowPanel",
)
LARGE = ("MeterLarge", "WindowMeter", "WindowPanel")

# Models that carry no emissive readout by design. Anything outside this list
# that measures no `readout` role is reported as a defect, and any entry here
# that turns out to have one is reported as a stale allowance.
#
# Confirmed 2026-08-09 (docs/OPUS5_CODEX_ALIGNMENT.md 10.2): Forge Brass is the
# non-emissive theme signature - neither its V5 builder nor its V6 detail pass
# authors a readout for these two, while Orbital Analog and Kinetic Safety do.
#
# The three `Button` models are deliberately NOT listed. `build_button` creates
# a `button_glyph` with the readout material in every theme, but no V6 Retopo
# contains that object, so their missing readout is a pipeline defect and has to
# keep failing this check until it is fixed.
READOUT_NOT_REQUIRED = frozenset(
    {
        "ForgeBrass/Lever",
        "ForgeBrass/WindowPanel",
    }
)


def parse_args():
    args = sys.argv
    args = args[args.index("--") + 1 :] if "--" in args else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--key", dest="keys", action="append", choices=KEYS,
        help="Limit the audit to these object keys.",
    )
    parser.add_argument("--theme", action="append", choices=THEMES)
    parser.add_argument(
        "--target-texels", type=float, default=None,
        help=(
            "Override the scale class target. Used to explore a density that "
            "only a larger sheet can hold; the module default is unchanged."
        ),
    )
    parser.add_argument(
        "--atlas-pixels", type=int, default=uv_pass.ATLAS_PIXELS,
        help="Sheet size the density figures are reported against.",
    )
    parser.add_argument(
        "--substitute", action="append", metavar="THEME/KEY=PATH",
        help=(
            "Audit a candidate blend in place of the shipped one, as "
            "'KineticSafety/Button=ArtSource/.../BL_Button_...blend'. The "
            "substitution is recorded in the report so a candidate result is "
            "never mistaken for a production one."
        ),
    )
    return parser.parse_args(args)


def scale_class_for(key):
    if key in LARGE:
        return "Large"
    if key == "MeterMedium":
        return "Medium"
    return "Standard"


def audit_one(
    project_root,
    source,
    root_name,
    scale_class,
    theme,
    target=None,
    atlas_pixels=uv_pass.ATLAS_PIXELS,
):
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    root = bpy.data.objects.get(root_name)
    if root is None:
        raise RuntimeError(f"{source}: missing root {root_name}")

    # Run the same semantic role assignment the Material stage performs, so the
    # roles measured here are the roles production actually ships. Reading the
    # Retopo materials directly would judge roles one stage too early.
    materials = v6_theme_materials.apply(project_root, theme, scale_class)
    v6_theme_materials.assign_special_roles(root, materials)

    meshes = [obj for obj in root.children_recursive if obj.type == "MESH"]
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in meshes
        for corner in obj.bound_box
    ]
    bounds = {
        "min": [round(min(p[i] for p in corners), 6) for i in range(3)],
        "max": [round(max(p[i] for p in corners), 6) for i in range(3)],
    }

    entries = uv_pass.apply(root, scale_class, target, atlas_pixels)
    summary = uv_pass.summarise(root, atlas_pixels)
    clamped = [entry for entry in entries if entry["clamped"]]
    roles = sorted({entry["role"] for entry in entries})
    return {
        "scale_class": scale_class,
        "target_texels_per_metre": (
            uv_pass.TARGET_TEXELS_PER_METRE[scale_class] if target is None else target
        ),
        "atlas_pixels": atlas_pixels,
        "meshes": len(meshes),
        "bounds": bounds,
        "roles": roles,
        "density_median": summary["median"],
        "density_lowest": summary["lowest"],
        "density_highest": summary["highest"],
        "spread_ratio": summary["spread_ratio"],
        "clamped_parts": [
            {
                "object": entry["object"],
                "role": entry["role"],
                "texels_per_metre": entry["texels_per_metre"],
            }
            for entry in clamped
        ],
    }


def main():
    args = parse_args()
    blender_compat.require_v6_pipeline()
    project_root = Path(args.project_root).resolve()
    models = {}
    failures = []
    substitutions = dict(
        item.split("=", 1) for item in (args.substitute or [])
    )
    unused = sorted(set(substitutions) - {
        f"{theme}/{key}"
        for theme in args.theme or THEMES
        for key in args.keys or KEYS
    })
    if unused:
        raise SystemExit(f"--substitute targets not in this run: {unused}")
    for theme in args.theme or THEMES:
        for key in args.keys or KEYS:
            label = f"{theme}/{key}"
            source = (
                project_root / substitutions[label]
                if label in substitutions
                else project_root
                / "ArtSource/Blender/ThemeHardSurfaceV6"
                / theme
                / f"BL_{key}_{theme}_V6_Retopo.blend"
            )
            if not source.is_file():
                failures.append(f"{label}: missing {source.name}")
                continue
            try:
                models[label] = audit_one(
                    project_root,
                    source,
                    f"PF_Visual_{key}_{theme}_V6",
                    scale_class_for(key),
                    theme,
                    args.target_texels,
                    args.atlas_pixels,
                )
            except Exception as exception:  # noqa: BLE001 - reported, not raised
                failures.append(f"{label}: {exception}")

    spreads = [model["spread_ratio"] for model in models.values()]
    clamped_models = {
        label: model["clamped_parts"]
        for label, model in models.items()
        if model["clamped_parts"]
    }
    # Roles are measured after the Material stage's semantic assignment, so a
    # missing `readout` here really means the shipped model emits nothing.
    missing_readout = sorted(
        label for label, model in models.items() if "readout" not in model["roles"]
    )
    unexpected = [
        label for label in missing_readout if label not in READOUT_NOT_REQUIRED
    ]
    stale_allowances = [
        label for label in READOUT_NOT_REQUIRED if label not in missing_readout
    ]
    report = {
        "note": (
            "Constant-density atlas UV pass applied to every V6 Retopo source. "
            "spread_ratio is the ratio between the highest and lowest per-object "
            "median texel density inside one model; 1.0 is perfect."
        ),
        "substituted_sources": dict(sorted(substitutions.items())),
        "all_sources_are_production": not substitutions,
        "models_audited": len(models),
        "worst_spread_ratio": round(max(spreads), 2) if spreads else None,
        "median_spread_ratio": (
            round(statistics.median(spreads), 2) if spreads else None
        ),
        "models_with_clamped_parts": clamped_models,
        "readout_role": {
            "measured_after": "v6_theme_materials.apply + assign_special_roles",
            "models_without_readout": missing_readout,
            "allowed_without_readout": sorted(READOUT_NOT_REQUIRED),
            "unexpected_missing_readout": unexpected,
            "stale_allowances": stale_allowances,
        },
        "failures": failures,
        "models": models,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        f"[UVAuditAll] {len(models)} models, "
        f"worst spread x{report['worst_spread_ratio']}, "
        f"median spread x{report['median_spread_ratio']}, "
        f"{len(clamped_models)} models with clamped parts, "
        f"{len(failures)} failures"
    )
    for label, parts in sorted(clamped_models.items()):
        print(f"  CLAMPED {label}: " + ", ".join(
            f"{part['object']}({part['role']}, {part['texels_per_metre']} tx/m)"
            for part in parts[:4]
        ))
    if unexpected:
        print("  READOUT MISSING (not on the allow list): " + ", ".join(unexpected))
    if stale_allowances:
        print("  STALE ALLOWANCE (now has readout): " + ", ".join(stale_allowances))
    for failure in failures:
        print(f"  FAIL {failure}")


if __name__ == "__main__":
    main()
