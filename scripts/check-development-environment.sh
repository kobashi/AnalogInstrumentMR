#!/usr/bin/env bash
set -u

failures=0

check_command() {
  local command_name="$1"
  local hint="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    echo "[ok] $command_name: $(command -v "$command_name")"
  else
    echo "[missing] $command_name - $hint"
    failures=$((failures + 1))
  fi
}

echo "MatsuMotoMeterAR development environment"
check_command adb "Install Android Build Support (SDK/NDK/OpenJDK) from Unity Hub."
check_command git-lfs "Install Git LFS, then run: git lfs install"

if command -v adb >/dev/null 2>&1; then
  echo
  echo "Connected Android devices"
  adb devices -l
fi

if [ "$failures" -gt 0 ]; then
  echo
  echo "$failures prerequisite(s) are missing. See docs/DEVELOPMENT.md."
  exit 1
fi

echo
echo "Environment command-line prerequisites are available."

