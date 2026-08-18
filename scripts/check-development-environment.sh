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

if [ -x "scripts/run-blender.sh" ]; then
  if analogmr_blender_version="$(scripts/run-blender.sh --version 2>&1 | awk '!found && /^Blender [0-9]/{print; found=1}')" &&
     [ -n "$analogmr_blender_version" ]; then
    echo "[ok] blender: $analogmr_blender_version"
  else
    echo "[missing] blender - Install Blender 5.2.x or set BLENDER_BIN."
    failures=$((failures + 1))
  fi
else
  echo "[missing] Blender launcher: scripts/run-blender.sh"
  failures=$((failures + 1))
fi

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
