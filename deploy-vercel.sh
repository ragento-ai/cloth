#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v vercel >/dev/null 2>&1; then
    echo "[ERROR] Vercel CLI is not installed."
    echo "Install it with: npm i -g vercel"
    exit 1
fi

echo "[INFO] Creating or reusing Vercel project: studio"
vercel project add studio || true

echo "[INFO] Linking local directory to Vercel project: studio"
vercel link --project studio --yes

echo "[INFO] Deploying production build"
vercel --prod
