#!/usr/bin/env bash
set -euo pipefail

THEME="${1:-KineticSafety}"
MEASUREMENT_SECONDS="${MEASUREMENT_SECONDS:-600}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-30}"
COOLDOWN_TARGET_DECI_C="${COOLDOWN_TARGET_DECI_C:-430}"
COOLDOWN_TIMEOUT_SECONDS="${COOLDOWN_TIMEOUT_SECONDS:-1800}"
COOLDOWN_STABLE_SAMPLES="${COOLDOWN_STABLE_SAMPLES:-3}"
ADB="${ADB:-/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb}"
APK="${APK:-Builds/Performance/AnalogInstrumentMR-v0.2.0-perfgate-quest3.apk}"
INSTALL_APK="${INSTALL_APK:-1}"

case "$THEME" in
  OrbitalAnalog|ForgeBrass|KineticSafety|MachinedErgonomics|machined-ergonomics) ;;
  *) echo "theme must be a registered production theme" >&2; exit 64 ;;
esac

case "$MEASUREMENT_SECONDS" in
  600|1800) ;;
  *) echo "matrix requires MEASUREMENT_SECONDS=600 or 1800" >&2; exit 64 ;;
esac

case "$INSTALL_APK" in
  0|1) ;;
  *) echo "INSTALL_APK must be 0 or 1" >&2; exit 64 ;;
esac

if [[ ! -x "$ADB" ]]; then
  echo "adb not found: $ADB" >&2
  exit 69
fi
if [[ "$($ADB get-state 2>/dev/null || true)" != "device" ]]; then
  echo "Quest is not authorized as an adb device." >&2
  "$ADB" devices -l
  exit 69
fi

REPORT_DIR="Builds/Reports"
mkdir -p "$REPORT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
MATRIX_REPORT="$REPORT_DIR/perfgate-matrix-48-64-${THEME}-${STAMP}.log"
exec > >(tee -a "$MATRIX_REPORT") 2>&1

temperature_deci_c() {
  "$ADB" shell dumpsys battery | tr -d '\r' | awk '/temperature:/{print $2; exit}'
}

cool_down() {
  local started now elapsed temperature stable=0
  started="$(date +%s)"
  echo "[matrix] cooldown target=$(awk -v value="$COOLDOWN_TARGET_DECI_C" 'BEGIN { printf "%.1f", value / 10 }')C stable_samples=$COOLDOWN_STABLE_SAMPLES"
  while true; do
    now="$(date +%s)"
    elapsed=$((now - started))
    temperature="$(temperature_deci_c)"
    if [[ -z "$temperature" ]]; then
      echo "[matrix] battery temperature unavailable"
      exit 69
    fi
    echo "[matrix] cooldown elapsed=${elapsed}s temp=$(awk -v value="$temperature" 'BEGIN { printf "%.1f", value / 10 }')C stable=${stable}/${COOLDOWN_STABLE_SAMPLES}"
    if (( temperature <= COOLDOWN_TARGET_DECI_C )); then
      stable=$((stable + 1))
      if (( stable >= COOLDOWN_STABLE_SAMPLES )); then
        return
      fi
    else
      stable=0
    fi
    if (( elapsed >= COOLDOWN_TIMEOUT_SECONDS )); then
      echo "[matrix] cooldown timeout"
      exit 2
    fi
    sleep "$INTERVAL_SECONDS"
  done
}

run_gate() {
  local count="$1"
  local install="$2"
  echo "[matrix] begin count=$count theme=$THEME install=$install"
  env \
    ADB="$ADB" \
    APK="$APK" \
    INSTALL_APK="$install" \
    INTERVAL_SECONDS="$INTERVAL_SECONDS" \
    MEASUREMENT_SECONDS="$MEASUREMENT_SECONDS" \
    DURATION_SECONDS="$((MEASUREMENT_SECONDS + 30))" \
    scripts/run-quest-performance-gate.sh "$count" "$THEME"
  echo "[matrix] completed count=$count"
}

echo "[matrix] report=$MATRIX_REPORT"
echo "[matrix] policy=48-object acceptance gate, 64-object characterization stress"
cool_down
run_gate 48 "$INSTALL_APK"
cool_down
run_gate 64 0

echo "[matrix] final reports"
for count in 48 64; do
  latest="$(ls -t "$REPORT_DIR"/perfgate-${count}-${THEME}-*-device.log 2>/dev/null | head -n 1 || true)"
  echo "[matrix] count=$count device_log=${latest:-missing}"
  if [[ -n "$latest" ]]; then
    grep -E '\[PerfGate\] FINAL' "$latest" || true
  fi
done
echo "[matrix] completed"
