#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

mkdir -p "1  INPUT" "3  MOODBOARD REFERENCE" "output"

if [ ! -f "vertex-cred.json" ] && [ -z "${VERTEX_CREDENTIALS_BASE64:-}" ]; then
    echo "[ERROR] Missing vertex-cred.json and VERTEX_CREDENTIALS_BASE64 is not set."
    exit 1
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

PYTHON_BIN="$ROOT_DIR/venv/bin/python"
PIP_BIN="$ROOT_DIR/venv/bin/pip"

if [ ! -f "venv/.deps_installed" ] || [ "requirements.txt" -nt "venv/.deps_installed" ]; then
    "$PIP_BIN" install --upgrade pip
    "$PIP_BIN" install -r requirements.txt gunicorn
    touch "venv/.deps_installed"
fi

exec "$ROOT_DIR/venv/bin/gunicorn" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-8}" \
  --timeout "${GUNICORN_TIMEOUT:-300}" \
  --bind "${HOST:-127.0.0.1}:${PORT:-5001}" \
  server:app
