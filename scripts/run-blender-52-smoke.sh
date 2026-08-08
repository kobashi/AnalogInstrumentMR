#!/usr/bin/env bash
set -euo pipefail

analogmr_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
analogmr_project_root="$(cd "$analogmr_script_dir/.." && pwd)"
analogmr_smoke_dir="${ANALOGMR_BLENDER_SMOKE_DIR:-$(mktemp -d)}"
analogmr_smoke_mode="${1:-representative}"
analogmr_smoke_quiet=0
analogmr_smoke_count=0

mkdir -p "$analogmr_smoke_dir"
cd "$analogmr_project_root"

run_smoke() {
  local analogmr_theme="$1"
  local analogmr_key="$2"
  local analogmr_source="ArtSource/Blender/ThemeHardSurfaceV6/${analogmr_theme}/BL_${analogmr_key}_${analogmr_theme}_V6_ProductionReady.blend"
  local analogmr_root="PF_Visual_${analogmr_key}_${analogmr_theme}_V6"
  local analogmr_log="$analogmr_smoke_dir/${analogmr_theme}-${analogmr_key}.log"
  local analogmr_render_args=()
  if [[ "$analogmr_smoke_quiet" == "0" ]]; then
    analogmr_render_args=(--render-preview)
  fi

  echo "[smoke] ${analogmr_theme}/${analogmr_key}"
  if [[ "$analogmr_smoke_quiet" == "1" ]]; then
    if ! scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/smoke_test_blender_52.py -- \
      --source "$analogmr_source" \
      --expected-root "$analogmr_root" \
      "${analogmr_render_args[@]}" \
      --output-dir "$analogmr_smoke_dir" >"$analogmr_log" 2>&1; then
      sed -n '1,260p' "$analogmr_log" >&2
      return 1
    fi
  else
    scripts/run-blender.sh --background --factory-startup \
      --python Tools/Blender/smoke_test_blender_52.py -- \
      --source "$analogmr_source" \
      --expected-root "$analogmr_root" \
      "${analogmr_render_args[@]}" \
      --output-dir "$analogmr_smoke_dir"
  fi
  analogmr_smoke_count=$((analogmr_smoke_count + 1))
}

if [[ "$analogmr_smoke_mode" == "--all" ]]; then
  analogmr_smoke_quiet=1
  analogmr_themes=(OrbitalAnalog ForgeBrass KineticSafety)
  analogmr_objects=(
    MeterRound MeterMedium MeterLarge Lever Toggle Rotary Button Lamp
    Throttle PowerSlider StatusIndicator WindowMeter WindowPanel
  )
  for analogmr_theme in "${analogmr_themes[@]}"; do
    for analogmr_key in "${analogmr_objects[@]}"; do
      run_smoke "$analogmr_theme" "$analogmr_key"
    done
  done
elif [[ "$analogmr_smoke_mode" == "representative" ]]; then
  run_smoke OrbitalAnalog Lever
  run_smoke ForgeBrass MeterRound
  run_smoke KineticSafety Throttle
  run_smoke OrbitalAnalog PowerSlider
  run_smoke ForgeBrass StatusIndicator
  run_smoke KineticSafety WindowPanel
else
  echo "usage: scripts/run-blender-52-smoke.sh [--all]" >&2
  exit 64
fi

echo "[smoke] PASS ${analogmr_smoke_count}/${analogmr_smoke_count}"
echo "[smoke] reports=$analogmr_smoke_dir"
