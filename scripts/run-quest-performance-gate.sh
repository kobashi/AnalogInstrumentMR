#!/usr/bin/env bash
set -euo pipefail

COUNT="${1:-24}"
THEME="${2:-OrbitalAnalog}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-30}"
MEASUREMENT_SECONDS="${MEASUREMENT_SECONDS:-600}"
DURATION_SECONDS="${DURATION_SECONDS:-$((MEASUREMENT_SECONDS + 30))}"
INSTALL_APK="${INSTALL_APK:-1}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-30}"
DISTANCE_METERS="${DISTANCE_METERS:-1.35}"
INSTRUMENT_KIND="${INSTRUMENT_KIND:-}"
ADB="${ADB:-/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb}"
APK="${APK:-Builds/Performance/AnalogInstrumentMR-v0.2.0-perfgate-quest3.apk}"
PACKAGE="com.DefaultCompany.MatsuMotoMeterAR"
ACTIVITY="com.unity3d.player.UnityPlayerGameActivity"

case "$COUNT" in
  12|24|40|48|64) ;;
  *) echo "count must be 12, 24, 40, 48, or 64" >&2; exit 64 ;;
esac

case "$THEME" in
  OrbitalAnalog|ForgeBrass|KineticSafety|MachinedErgonomics|machined-ergonomics) ;;
  *) echo "theme must be a registered production theme" >&2; exit 64 ;;
esac

case "$MEASUREMENT_SECONDS" in
  60|600|1800) ;;
  *) echo "MEASUREMENT_SECONDS must be 60, 600, or 1800" >&2; exit 64 ;;
esac

case "$INSTALL_APK" in
  0|1) ;;
  *) echo "INSTALL_APK must be 0 or 1" >&2; exit 64 ;;
esac

if ! awk -v value="$DISTANCE_METERS" \
  'BEGIN { exit !(value + 0 >= 0.5 && value + 0 <= 5.0) }'; then
  echo "DISTANCE_METERS must be between 0.5 and 5.0" >&2
  exit 64
fi

case "$INSTRUMENT_KIND" in
  ""|RoundMeter|Lever|ToggleSwitch|RotaryKnob|PushButton|IndicatorLamp|\
WindowMeter|WindowPanel|StatusIndicator|ThrottleLever|PowerSlider|\
RoundMeterMedium|RoundMeterLarge) ;;
  *) echo "INSTRUMENT_KIND is not a supported MockInstrumentKind" >&2; exit 64 ;;
esac

if [[ ! -x "$ADB" ]]; then
  echo "adb not found: $ADB" >&2
  exit 69
fi
if [[ ! -f "$APK" ]]; then
  echo "APK not found: $APK" >&2
  exit 66
fi
if [[ "$($ADB get-state 2>/dev/null || true)" != "device" ]]; then
  echo "Quest is not authorized as an adb device." >&2
  "$ADB" devices -l
  exit 69
fi

REPORT_DIR="Builds/Reports"
mkdir -p "$REPORT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT="$REPORT_DIR/perfgate-${COUNT}-${THEME}-${STAMP}.log"
DEVICE_LOG="$REPORT_DIR/perfgate-${COUNT}-${THEME}-${STAMP}-device.log"
LOGCAT_PID=""

start_logcat() {
  "$ADB" logcat -v threadtime -s Unity:I AndroidRuntime:E ActivityManager:E >> "$DEVICE_LOG" &
  LOGCAT_PID=$!
}

cleanup() {
  if [[ -n "$LOGCAT_PID" ]]; then
    kill "$LOGCAT_PID" 2>/dev/null || true
    wait "$LOGCAT_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

exec > >(tee -a "$REPORT") 2>&1

echo "[host] report=$REPORT"
echo "[host] apk=$APK"
echo "[host] sha256=$(shasum -a 256 "$APK" | awk '{print $1}')"
echo "[host] scenario=count:${COUNT} theme:${THEME} duration:${MEASUREMENT_SECONDS}s distance:${DISTANCE_METERS}m kind:${INSTRUMENT_KIND:-Baseline}"
if [[ "$INSTALL_APK" == "1" ]]; then
  "$ADB" install -r "$APK"
else
  echo "[host] APK install skipped"
fi
"$ADB" logcat -c
"$ADB" shell am force-stop "$PACKAGE"
: > "$DEVICE_LOG"
start_logcat

start_app() {
  local command=(
    "$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY"
    --ei matsu_perf_count "$COUNT" \
    --ei matsu_perf_duration "$MEASUREMENT_SECONDS" \
    --es matsu_perf_theme "$THEME" \
    --ef matsu_perf_distance "$DISTANCE_METERS"
  )
  if [[ -n "$INSTRUMENT_KIND" ]]; then
    command+=(--es matsu_perf_kind "$INSTRUMENT_KIND")
  fi
  "${command[@]}"
}

start_app
PID=""
for ((second = 1; second <= STARTUP_TIMEOUT_SECONDS; second++)); do
  PID="$($ADB shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
  if [[ -n "$PID" ]]; then
    break
  fi
  if (( second == 10 )); then
    echo "[host] app process not detected after 10s; retrying launch"
    start_app
  fi
  sleep 1
done
if [[ -z "$PID" ]]; then
  echo "[host] APP START FAILED after ${STARTUP_TIMEOUT_SECONDS}s"
  exit 70
fi
echo "[host] app process started pid=$PID"

SCENARIO_READY=""
for ((second = 1; second <= STARTUP_TIMEOUT_SECONDS; second++)); do
  if grep -q '\[PerfGate\] Scenario ready:' "$DEVICE_LOG"; then
    SCENARIO_READY=1
    break
  fi
  PID="$($ADB shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
  if [[ -z "$PID" ]]; then
    echo "[host] APP EXITED before PerfGate scenario became ready"
    exit 71
  fi
  sleep 1
done
if [[ -z "$SCENARIO_READY" ]]; then
  echo "[host] PERF GATE NOT READY after ${STARTUP_TIMEOUT_SECONDS}s"
  grep -E '\[PerfGate\]' "$DEVICE_LOG" || true
  exit 71
fi
grep -E '\[PerfGate\] Scenario ready:' "$DEVICE_LOG" | tail -n 1

START_EPOCH="$(date +%s)"
while true; do
  NOW_EPOCH="$(date +%s)"
  ELAPSED=$((NOW_EPOCH - START_EPOCH))
  if (( ELAPSED >= DURATION_SECONDS )); then
    break
  fi

  if [[ -n "$LOGCAT_PID" ]] && ! kill -0 "$LOGCAT_PID" 2>/dev/null; then
    wait "$LOGCAT_PID" 2>/dev/null || true
    echo "[host] logcat capture stopped; restarting"
    start_logcat
  fi

  PID="$($ADB shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)"
  BATTERY="$($ADB shell dumpsys battery | tr -d '\r')"
  LEVEL="$(printf '%s\n' "$BATTERY" | awk '/level:/{print $2; exit}')"
  TEMP_DECI_C="$(printf '%s\n' "$BATTERY" | awk '/temperature:/{print $2; exit}')"
  TEMP_C="$(awk -v value="${TEMP_DECI_C:-0}" 'BEGIN { printf "%.1f", value / 10 }')"
  echo "[sample] elapsed=${ELAPSED}s pid=${PID:-none} battery=${LEVEL:-unknown}% temp=${TEMP_C}C"

  if [[ -n "$PID" ]]; then
    "$ADB" shell dumpsys meminfo "$PACKAGE" | \
      awk '/TOTAL PSS:|TOTAL RSS:|TOTAL SWAP PSS:/{print "[memory] " $0}'
  fi

  if [[ -n "${TEMP_DECI_C:-}" ]] && (( TEMP_DECI_C >= 480 )); then
    echo "[host] THERMAL STOP at ${TEMP_C}C"
    "$ADB" shell am force-stop "$PACKAGE"
    exit 2
  fi

  sleep "$INTERVAL_SECONDS"
done

cleanup
LOGCAT_PID=""
if ! grep -q '\[PerfGate\] FINAL' "$DEVICE_LOG"; then
  echo "[host] FINAL missing from live capture; appending device buffer snapshot"
  "$ADB" logcat -d -v threadtime \
    -s Unity:I AndroidRuntime:E ActivityManager:E >> "$DEVICE_LOG"
fi
echo "[host] PerfGate log"
grep -E '\[PerfGate\]|FATAL EXCEPTION|AndroidRuntime' "$DEVICE_LOG" || true
echo "[host] fatal-count"
grep -Ec 'FATAL EXCEPTION|Fatal signal|AndroidRuntime.*FATAL' "$DEVICE_LOG" || true
if ! grep -q '\[PerfGate\] FINAL' "$DEVICE_LOG"; then
  echo "[host] PERF GATE FINAL MISSING"
  exit 71
fi
echo "[host] completed"
