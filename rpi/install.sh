#!/usr/bin/env bash
# Automated Installation Script for Raspberry Pi 3
# =================================================
set -e

echo "=============================================================="
echo "  INSTALLING SMART ASSISTIVE SYSTEM ON RASPBERRY PI 3"
echo "=============================================================="

# 1. Update system packages
echo "--> Updating APT packages..."
sudo apt update -y
sudo apt install -y python3-pip python3-dev python3-setuptools \
                    libatlas-base-dev mpg123 alsa-utils i2c-tools \
                    libcamera-tools python3-picamera2 || true

# 2. Check Raspberry Pi Model
echo -n "--> Detected Hardware: "
cat /proc/device-tree/model || echo "Generic Linux Board"
echo ""

# 3. Create Python Virtual Environment (recommended for Bookworm)
if [ ! -d "venv" ]; then
    echo "--> Creating Python Virtual Environment (venv)..."
    python3 -m venv --system-site-packages venv
fi

# 4. Install Python Requirements
echo "--> Installing Python dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. Copy .env if not exists
if [ ! -f ".env" ]; then
    echo "--> Creating .env from .env.example..."
    cp .env.example .env
fi

echo ""
echo "=============================================================="
echo "✅ Installation Complete!"
echo "Next step: Configure I2S audio and I2C (see SETUP_RPI.md)"
echo "To run the application: ./run.sh"
echo "=============================================================="
