#!/bin/bash
# Build a standalone PassForge executable for macOS or Linux.
set -e

cd "$(dirname "$0")"

echo "Installing dependencies..."
python3 -m pip install -r requirements.txt --quiet
python3 -m pip install pyinstaller --quiet

echo "Building PassForge..."
pyinstaller --noconfirm passforge.spec

echo ""
echo "Done. Find the executable at: dist/PassForge"
echo "Copy it (and, if you want, the whole dist/ folder) anywhere you like."
