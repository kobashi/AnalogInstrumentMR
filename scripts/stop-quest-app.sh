#!/usr/bin/env bash
set -euo pipefail

package_name="${1:-com.DefaultCompany.MatsuMotoMeterAR}"

if ! command -v adb >/dev/null 2>&1; then
  echo "adb was not found. Install Android Platform Tools first." >&2
  exit 1
fi

devices=()
while read -r serial state _; do
  if [[ "$state" == "device" ]]; then
    devices+=("$serial")
  fi
done < <(adb devices)

if [[ "${#devices[@]}" -ne 1 ]]; then
  echo "Expected exactly one authorized Quest device, found ${#devices[@]}." >&2
  adb devices -l >&2
  exit 1
fi

serial="${devices[0]}"

package_path="$(adb -s "$serial" shell pm path "$package_name")"
if [[ "$package_path" != package:* ]]; then
  echo "$package_name is not installed on $serial." >&2
  exit 1
fi

adb -s "$serial" shell am force-stop "$package_name"

if adb -s "$serial" shell pidof "$package_name" | grep -q '[0-9]'; then
  echo "Failed to stop $package_name." >&2
  exit 1
fi

echo "$package_name is stopped on $serial. The Quest system shell is now in control."
