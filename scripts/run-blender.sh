#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${BLENDER_BIN:-}" ]]; then
  analogmr_blender_bin="$BLENDER_BIN"
elif [[ -x "/Applications/Blender 5.2.app/Contents/MacOS/Blender" ]]; then
  analogmr_blender_bin="/Applications/Blender 5.2.app/Contents/MacOS/Blender"
elif command -v blender >/dev/null 2>&1; then
  analogmr_blender_bin="$(command -v blender)"
else
  echo "Blender was not found. Install Blender 5.2.x or set BLENDER_BIN." >&2
  exit 69
fi

if [[ ! -x "$analogmr_blender_bin" ]]; then
  echo "Blender is not executable: $analogmr_blender_bin" >&2
  exit 69
fi

analogmr_blender_version_output="$("$analogmr_blender_bin" --version 2>&1)"
analogmr_blender_version="$(
  printf '%s\n' "$analogmr_blender_version_output" |
    awk '!found && /^Blender [0-9]/{print; found=1}'
)"
if [[ "$analogmr_blender_version" != Blender\ 5.2.* ]] &&
   [[ "${ANALOGMR_ALLOW_UNSUPPORTED_BLENDER:-0}" != "1" ]]; then
  echo "AnalogInstrumentMR requires Blender 5.2.x; found: ${analogmr_blender_version:-unknown}" >&2
  echo "Set BLENDER_BIN to the Blender 5.2 executable." >&2
  exit 65
fi

if [[ "${1:-}" == "--print-bin" ]]; then
  printf '%s\n' "$analogmr_blender_bin"
  exit 0
fi

analogmr_python_command=0
analogmr_python_exit_code_set=0
for analogmr_blender_arg in "$@"; do
  case "$analogmr_blender_arg" in
    --python|--python-expr|--python-text)
      analogmr_python_command=1
      ;;
    --python-exit-code)
      analogmr_python_exit_code_set=1
      ;;
  esac
done

if [[ "$analogmr_python_command" == "1" ]] &&
   [[ "$analogmr_python_exit_code_set" == "0" ]]; then
  exec "$analogmr_blender_bin" --python-exit-code 1 "$@"
fi

exec "$analogmr_blender_bin" "$@"
