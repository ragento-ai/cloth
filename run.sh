#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "========================================================"
echo "  Ragento Visual Studio - One-Command Run               "
echo "========================================================"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 is required but not installed."
    exit 1
fi

mkdir -p "1  INPUT" "3  MOODBOARD REFERENCE" "output"

if [ ! -f "vertex-cred.json" ]; then
    echo "[ERROR] Missing vertex-cred.json in $ROOT_DIR"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

PYTHON_BIN="$ROOT_DIR/venv/bin/python"
PIP_BIN="$ROOT_DIR/venv/bin/pip"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "[ERROR] Virtualenv python not found at $PYTHON_BIN"
    exit 1
fi

if [ ! -f "venv/.deps_installed" ] || [ "requirements.txt" -nt "venv/.deps_installed" ]; then
    echo "[INFO] Installing Python dependencies..."
    "$PIP_BIN" install --upgrade pip
    "$PIP_BIN" install -r requirements.txt
    touch "venv/.deps_installed"
fi

export FLASK_APP=server
export FLASK_DEBUG=1

echo "[INFO] Starting app with auto-reload on http://127.0.0.1:5000"
exec "$PYTHON_BIN" -m flask --app server run --debug --host 0.0.0.0 --port 5000
