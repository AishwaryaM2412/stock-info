#!/usr/bin/env bash
# Run script for macOS / Linux: sets up a virtual environment, installs requests, starts the program.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install -q -r requirements.txt
python stockinfo.py
