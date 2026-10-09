#!/usr/bin/env bash
# Execute only in the currently available AI-controlled runtime.
# Source/package downloads are allowed; never outsource numerical computation.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
INSTALL_CCX=0
for arg in "$@"; do
  case "$arg" in
    --install-ccx) INSTALL_CCX=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done
if python -m venv --system-site-packages .venv; then
  . .venv/bin/activate
else
  echo 'No venv available; continuing with the current Python' >&2
fi
if ! python -c 'import numpy,scipy' >/dev/null 2>&1; then
  python -m pip install 'numpy>=1.23' 'scipy>=1.9'
fi
if ! python -c 'import matplotlib' >/dev/null 2>&1; then
  python -m pip install 'matplotlib>=3.5' || echo 'Matplotlib unavailable: continue without PNG visualization' >&2
fi
if ! python -c 'import pytest' >/dev/null 2>&1; then
  python -m pip install 'pytest>=7' || echo 'pytest unavailable; CLI still usable' >&2
fi
# If dependency installation or editable pip packaging is prohibited, PYTHONPATH=src works.
python -m pip install --no-deps --no-build-isolation -e . || echo 'Editable install failed; use PYTHONPATH=src python -m nopc_bridge' >&2
if [[ "$INSTALL_CCX" == 1 ]]; then
  if command -v ccx >/dev/null 2>&1; then
    echo 'CalculiX already present.'
  elif command -v apt-get >/dev/null 2>&1; then
    if [[ "$EUID" -eq 0 ]]; then
      timeout 120 apt-get update && timeout 120 apt-get install -y --no-install-recommends calculix-ccx || echo 'CalculiX apt setup unavailable; native solver still works.' >&2
    elif command -v sudo >/dev/null 2>&1; then
      timeout 120 sudo -n apt-get update && timeout 120 sudo -n apt-get install -y --no-install-recommends calculix-ccx || echo 'No sudo apt permission. Native solver still works.' >&2
    else
      echo 'Cannot install CalculiX (no root/sudo). Native solver still works.' >&2
    fi
  else
    echo 'No apt-get; prepare a separately verified official binary when allowed.' >&2
  fi
fi
PYTHONPATH=src python -m nopc_bridge doctor
