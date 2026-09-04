#!/usr/bin/env bash
#
# Build a self-contained Linux executable with PyInstaller.
# Run this ON a Linux machine (PyInstaller does not cross-compile).
#
# Output: dist/Mist-Engine-Sheet-Builder/  (zip this folder to distribute)
#
# Prerequisites:
#   * Python 3.10+
#   * The Pango/Cairo system libraries WeasyPrint needs at runtime, so
#     PyInstaller can find and copy them. On Debian/Ubuntu:
#       sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev
#     On Fedora:
#       sudo dnf install pango cairo gdk-pixbuf2

set -euo pipefail
cd "$(dirname "$0")"

echo "Setting up an isolated build environment..."
python3 -m venv .build-venv
# shellcheck disable=SC1091
source .build-venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt pyinstaller

echo "Building..."
pyinstaller --noconfirm --clean mist_engine_sheet_builder.spec

echo ""
echo "Done. Standalone app is in:  dist/Mist-Engine-Sheet-Builder/"
echo "Launch it with:              ./dist/Mist-Engine-Sheet-Builder/Mist-Engine-Sheet-Builder"
echo "To distribute, zip the whole dist/Mist-Engine-Sheet-Builder/ folder."
