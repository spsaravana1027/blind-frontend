#!/usr/bin/env bash
# Startup Script for Raspberry Pi 3 Smart Assistive System
# ========================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "venv/bin/python3" ]; then
    PYTHON_CMD="venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

echo "=============================================================="
echo "  LAUNCHING SMART ASSISTIVE SYSTEM ON RASPBERRY PI 3"
echo "=============================================================="

exec $PYTHON_CMD main.py
