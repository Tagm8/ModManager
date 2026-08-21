#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "ERROR: python3 is not installed."
    echo "Install it with: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

if [ ! -d ".venv" ] || [ ! -f ".venv/bin/activate" ]; then
    echo "[SA Mod Manager] Creating Python virtual environment..."
    rm -rf .venv

    if ! "$PYTHON" -m venv .venv; then
        echo
        echo "ERROR: Python could not create a virtual environment."
        echo "On Linux Mint/Debian, install the missing packages with:"
        echo
        echo "    sudo apt update"
        echo "    sudo apt install python3-venv python3-pip"
        echo
        echo "Then run ./run.sh again."
        exit 1
    fi
fi

source ".venv/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

exec python sa_mod_manager.py
