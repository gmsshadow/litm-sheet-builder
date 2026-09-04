#!/usr/bin/env bash
#
# Mist Engine Sheet Builder — Linux / macOS launcher.
#
# Double-click (or run from a terminal). On first launch it builds a private
# Python virtual environment next to this script and installs the required
# packages; subsequent launches reuse it and start almost instantly. The app
# opens in your default web browser. Close this terminal window to quit.
#
# Requires: Python 3.10+  (https://www.python.org/downloads/)
# For PDF export you also need the Pango/Cairo system libraries — see the
# "Linux PDF export" note in PACKAGING.md (one apt/dnf/brew line).

set -euo pipefail

# Resolve the directory this script lives in, following symlinks, so the app
# works no matter where it's launched from.
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
APP_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
cd "$APP_DIR"

VENV_DIR="$APP_DIR/.venv"

# Find a usable Python 3 interpreter.
PYTHON=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
      PYTHON="$cand"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.10 or newer was not found on your PATH."
  echo "Install it from https://www.python.org/downloads/ and run this again."
  read -r -p "Press Enter to close..." _ || true
  exit 1
fi

# Create the virtual environment on first run.
if [ ! -d "$VENV_DIR" ]; then
  echo "First-time setup: creating a private Python environment..."
  "$PYTHON" -m venv "$VENV_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  echo "Installing dependencies (this happens only once)..."
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r "$APP_DIR/requirements.txt"
else
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
fi

echo ""
echo "Starting the Sheet Builder. Your browser should open shortly."
echo "If it doesn't, visit:  http://127.0.0.1:${LITM_PORT:-5000}"
echo "Close this window to quit."
echo ""

exec python "$APP_DIR/run.py"
