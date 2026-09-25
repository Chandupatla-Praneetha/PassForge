#!/bin/bash
# Double-click this (or run ./PassForge.command) to open PassForge directly.
cd "$(dirname "$0")"

# If you've already built the standalone binary (via build.sh), use it.
if [ -x "dist/PassForge" ]; then
    ./dist/PassForge &
    exit 0
fi

# Otherwise, run from source. Install dependencies only if missing.
python3 -c "import customtkinter, cryptography, PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Setting up PassForge for the first time, this may take a minute..."
    python3 -m pip install -r requirements.txt --quiet
fi

python3 main.py &
