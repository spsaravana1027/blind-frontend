# Raspberry Pi 3 Setup & Installation Guide
### Smart Assistive System for Visually Impaired People

This guide walks you through setting up your **Raspberry Pi 3 Model B / B+** from a fresh Raspberry Pi OS installation to running the complete assistive system.

---

## 📋 Table of Contents
1. [Identify Pi Model and OS Version](#1-identify-pi-model-and-os-version)
2. [Enable Camera, I2C, and I2S in config.txt](#2-enable-camera-i2c-and-i2s-in-configtxt)
3. [Configure MAX98357A I2S Audio in ALSA](#3-configure-max98357a-i2s-audio-in-alsa)
4. [Install System Dependencies & Python Virtualenv](#4-install-system-dependencies--python-virtualenv)
5. [Hardware-by-Hardware Standalone Diagnostic Tests](#5-hardware-by-hardware-standalone-diagnostic-tests)
6. [Running the Integrated Application](#6-running-the-integrated-application)
7. [Optional: Auto-Start on Boot via systemd](#7-optional-auto-start-on-boot-via-systemd)
8. [Troubleshooting Common Issues](#8-troubleshooting-common-issues)

---

## 1. Identify Pi Model and OS Version

Open a terminal on your Raspberry Pi (or SSH) and run:

```bash
# Check hardware model
cat /proc/device-tree/model
# Output example: Raspberry Pi 3 Model B Plus Rev 1.3

# Check OS version (Bookworm vs Bullseye)
cat /etc/os-release | grep PRETTY_NAME
```

> **Note on OS Differences:**
> - **Raspberry Pi OS Bookworm (Debian 12):** Boot configuration is located at `/boot/firmware/config.txt`.
> - **Raspberry Pi OS Bullseye (Debian 11) or older:** Boot configuration is located at `/boot/config.txt`.

---

## 2. Enable Camera, I2C, and I2S in config.txt

### Step A: Locate config.txt
```bash
# Determine configuration file path
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
else
    CONFIG_FILE="/boot/config.txt"
fi

# Create a backup before editing!
sudo cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
```

### Step B: Edit config.txt
Open the file in `nano`:
```bash
sudo nano "$CONFIG_FILE"
```

Ensure the following parameters are added or enabled:

```ini
# --- Smart Assistive System Hardware Overlays ---

# 1. Enable CSI Camera auto-detection
camera_auto_detect=1

# 2. Enable I2C Bus for MPU-6050
dtparam=i2c_arm=on
dtparam=i2c1=on

# 3. Disable built-in headphone PWM audio to prevent DMA conflicts
dtparam=audio=off

# 4. Enable MAX98357A I2S Audio DAC overlay
dtoverlay=hifiberry-dac
```

Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit.

### Step C: Reboot the Pi
```bash
sudo reboot
```

---

## 3. Configure MAX98357A I2S Audio in ALSA

After rebooting, verify that the I2S sound card was detected:

```bash
aplay -l
```
You should see:
```text
card 0: sndrpihifiberry [snd_rpi_hifiberry_dac], device 0: HifiBerry DAC HiFi pcm5102a-hifi-0 []
```

### Create /etc/asound.conf for Default Audio Routing:
```bash
sudo nano /etc/asound.conf
```

Paste the following ALSA configuration:

```ini
pcm.!default {
    type hw
    card 0
}

ctl.!default {
    type hw
    card 0
}
```
Save and exit (`Ctrl + O`, `Enter`, `Ctrl + X`).

---

## 4. Install System Dependencies & Python Virtualenv

### Step A: Install System Packages
```bash
sudo apt update -y
sudo apt install -y python3-pip python3-dev python3-venv \
                    libatlas-base-dev mpg123 alsa-utils i2c-tools \
                    libcamera-tools python3-picamera2
```

### Step B: Navigate to Project Directory & Setup venv
```bash
cd ~/iot_new/rpi

# Create virtual environment allowing access to system picamera2
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Upgrade pip and install Python packages
pip install --upgrade pip
pip install -r requirements.txt
```

### Step C: Configure Telegram Credentials
```bash
cp .env.example .env
nano .env
```
Ensure your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured.

---

## 5. Hardware-by-Hardware Standalone Diagnostic Tests

Before launching the full application, run each standalone verification tool in `rpi/tools/`:

### Test 1: CSI Camera Capture
```bash
python3 tools/test_camera_pi.py
```
*Captures a frame and saves `tools/test_csi_capture.jpg`.*

### Test 2: MPU-6050 Accelerometer & Gyroscope
```bash
# Check if device 0x68 is visible on I2C bus:
i2cdetect -y 1

# Run live sensor reading test:
python3 tools/test_mpu6050_pi.py
```
*Prints real-time acceleration magnitude, angular velocity, and posture tilt angle.*

### Test 3: HC-SR04 Ultrasonic Distance Sensor
```bash
python3 tools/test_ultrasonic_pi.py
```
*Wave your hand in front of the sensor to see distance update in real time.*

### Test 4: MAX98357A I2S Speaker Audio
```bash
python3 tools/test_audio_pi.py
```
*Plays Tamil audio clips: "System Ready", "Obstacle Warning", and "User Safe".*

### Test 5: Emergency Buzzer
```bash
python3 tools/test_buzzer_pi.py
```
*Pulses the buzzer for 3 seconds on BCM GPIO 27.*

### Test 6: Cancel / Safe Push Button
```bash
python3 tools/test_button_pi.py
```
*Prompts you to press the push button on BCM GPIO 17 within 10 seconds.*

### Test 7: Fall Detection Verification & Countdown Simulation
```bash
python3 tools/test_fall_pi.py
```
*Simulates a fall, starts the 10s countdown, and tests cancellation vs alarm.*

### Test 8: Telegram Guardian Alert Dispatch
```bash
python3 tools/test_telegram_pi.py
```
*Sends a verification message to your Telegram app (@elder_assist_alert_bot).*

---

## 6. Running the Integrated Application

Once all 8 diagnostic tests pass, start the main application:

```bash
# Activate environment if not already active
source venv/bin/activate

# Run orchestrator
python3 main.py
```
Or simply use the launch script:
```bash
./run.sh
```

### Keyboard Hotkeys (During Execution):
- `f` + Enter : Simulates a fall down event.
- `s` + Enter : Simulates pressing the cancel/safe button.
- `d 40` + Enter : Sets simulated obstacle distance to 40 cm.
- `q` + Enter : Shuts down the system cleanly.

---

## 7. Optional: Auto-Start on Boot via systemd

To run the assistive device automatically when the Raspberry Pi powers on:

1. Create a service file:
```bash
sudo nano /etc/systemd/system/assistive.service
```

2. Paste the following configuration (replace `pi` with your username if different):
```ini
[Unit]
Description=Smart Assistive Device for Visually Impaired People
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/iot_new/rpi
ExecStart=/home/pi/iot_new/rpi/venv/bin/python3 /home/pi/iot_new/rpi/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable assistive.service
sudo systemctl start assistive.service
```

---

## 8. Troubleshooting Common Issues

| Issue / Symptom | Possible Cause | Solution |
| :--- | :--- | :--- |
| **`libcamera-hello` says "no cameras available"** | Ribbon cable reversed or loose | Power off Pi. Ensure silver pins face HDMI port and blue tape faces audio jack. Re-seat latch firmly. |
| **`i2cdetect -y 1` shows an empty grid** | I2C not enabled or loose wiring | Run `sudo raspi-config` -> Interface Options -> I2C -> Enable. Check that VCC is on Pin 1 (3.3V) and GND is on Pin 6. |
| **No sound from I2S speaker** | Missing `hifiberry-dac` overlay | Check `/boot/config.txt` or `/boot/firmware/config.txt` for `dtoverlay=hifiberry-dac` and `dtparam=audio=off`. Reboot. |
| **Pi reboots when speaker plays or camera captures** | Weak power supply | Use a 5V $\ge$ 2.5A power adapter. Never use a 9V battery or a low-power phone charger. |
| **Telegram alert returns HTTP 400 "chat not found"** | Bot not initiated by user | Open `@elder_assist_alert_bot` in your Telegram app and click **Start** (`/start`). |
