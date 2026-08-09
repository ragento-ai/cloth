#!/bin/bash
set -e

echo "========================================================"
echo "  Ragento Visual Studio - One-Command Setup & Launch    "
echo "========================================================"

# Step 1: Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 is required but not installed."
    exit 1
fi

# Step 2: Environment setup
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[INFO] Creating .env from .env.example template..."
        cp .env.example .env
    else
        echo "[WARNING] No .env file found. Make sure environment variables are configured."
    fi
fi

# Step 3: Virtual environment creation
if [ ! -d "venv" ]; then
    echo "[INFO] Creating Virtual Environment (venv)..."
    python3 -m venv venv
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Step 4: Install Dependencies
echo "[INFO] Installing Python dependencies from requirements.txt..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Step 5: Launch Application
echo "[SUCCESS] Environment setup complete!"
echo "[INFO] Launching Ragento Visual Studio Server on http://localhost:5000..."
python server.py
