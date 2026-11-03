# AI-Powered Smart Assistive Device for Visually Impaired People
### Fall Detection, Obstacle Vision Navigation & Tamil Voice Guidance System

An end-to-end embedded system designed for visually impaired safety and obstacle navigation assistance. The system integrates computer vision object detection via YOLOv8, ultrasonic distance measurement, Tamil voice guidance delivered over **MAX98357A I2S audio**, multi-stage fall detection using **MPU-6050**, emergency buzzer alarms, push-button cancellation, and **Telegram emergency guardian alerts**.

---

## 🍓 Primary Architecture: Single Raspberry Pi 3 Model B / B+

The system has been upgraded to run directly on a **single Raspberry Pi 3** as the primary controller, replacing the dual-ESP32 setup:

```
                            ┌──────────────────────────────────────────────┐
                            │      Raspberry Pi 3 Model B / B+             │
                            │                                              │
                            │  • CSI Ribbon Camera (Picamera2 / libcamera) │
                            │  • Embedded YOLOv8n Obstacle Vision (320x320)│
                            │  • MPU-6050 50 Hz Fall Detection (I2C-1)     │
                            │  • HC-SR04 Ultrasonic Distance Sensor        │
                            │  • MAX98357A I2S 3W Speaker Amplifier (ALSA) │
                            │  • 35 Real Tamil Speech MP3 Audio Clips      │
                            │  • Active Emergency Siren Buzzer (BCM 27)    │
                            │  • Emergency Cancel Push Button (BCM 17)     │
                            │  • Telegram Guardian Alert Dispatcher        │
                            └──────────────────────────────────────────────┘
```

👉 **Complete Raspberry Pi Documentation:**
- **[Hardware Wiring & Safety Guide (Pinout Table & Schematics)](file:///d:/iot_new/rpi/WIRING.md)**
- **[Step-by-Step Installation & Setup Guide](file:///d:/iot_new/rpi/SETUP_RPI.md)**
- **[Full ESP32-to-Raspberry Pi Architecture Migration Report](file:///d:/iot_new/MIGRATION_REPORT.md)**

### Quick Start on Raspberry Pi:
```bash
cd ~/iot_new/rpi
./install.sh
./run.sh
```

---

## 📦 Legacy 2-Board Architecture (ESP32-CAM + ESP32 DevKit)
*(Preserved for backward compatibility and reference)*


```
                       ┌────────────────────────────────────────────────────────┐
                       │                     PC / LAPTOP                        │
                       │  • Python YOLOv8 Vision Detection (COCO Model)         │
                       │  • EasyOCR (Currency & Medicine Identification)        │
                       │  • Real Tamil Audio Engine (pygame.mixer Speaker)      │
                       │  • FastAPI Backend Server (Port 8000)                  │
                       └────────────────────────────────────────────────────────┘
                                     ▲ HTTP                     │ Serial Bridge (USB)
                                     │ /capture or /stream      │ (clip <id> commands)
                                     │                          ▼
┌─────────────────────────────┐  Wi-Fi   ┌──────────────────────────────────────────────┐
│  BOARD 1: ESP32-CAM         │          │  BOARD 2: ESP32 DevKit V1                    │
│  (AI-Thinker OV2640)        │          │  • MPU-6050 Accelerometer (Fall Detection)   │
│  • Continuous Video Capture │─────────>│  • MAX98357A I2S 3W Speaker Amplifier       │
│  • Embedded Snapshot & Stream│  UART    │  • Active Emergency Buzzer Alarm (GPIO 4)    │
│  • Hardware Brownout Bypass │ (32/33)  │  • Safe Switch Push Button (GPIO 19)         │
│  • Task Watchdog Protection │          │  • HC-SR04 Ultrasonic Distance Sensor        │
└─────────────────────────────┘          │  • Universal Telegram Bot Emergency Client   │
                                         └──────────────────────────────────────────────┘
```

---

## ⚡ ASCII Hardware Wiring Diagrams

### Board 1: AI-Thinker ESP32-CAM
```
    +-----------------------------------------------+
    |             ESP32-CAM (AI-Thinker)            |
    |                                               |
    | 5V  <----------------------- 5V (>= 2A PSU)   |
    | GND <----------------------- GND (Common Rail)|
    |                                               |
    | TX0 (GPIO 1) --------------> Main ESP32 RX1   | (GPIO 32)
    | RX0 (GPIO 3) <-------------- Main ESP32 TX1   | (GPIO 33)
    |                                               |
    | [GPIO 0 to GND during flashing; open on boot] |
    +-----------------------------------------------+
```

### Board 2: Main ESP32 DevKit V1
```
                   +-------------------------------+
                   |       ESP32 DevKit V1         |
                   |                               |
                   | 5V  <------- 5V Power Rail    |
                   | GND <------- Common GND       |
                   +---------------+---------------+
                                   |
    +------------------------------+------------------------------+
    |                              |                              |
[MPU-6050]                  [MAX98357A I2S Amp]             [Active Buzzer]
VCC -> 3.3V                 VIN -> 5V                       VCC -> GPIO 4
GND -> GND                  GND -> GND                      GND -> GND
SDA -> GPIO 21              DIN -> GPIO 27
SCL -> GPIO 22              BCLK-> GPIO 26                  [Safe Switch]
                            LRC -> GPIO 25                  Pin 1 -> GPIO 19
[HC-SR04 Ultrasonic]        (+) -> Speaker (+)              Pin 2 -> GND (Pull-Up)
VCC  -> 5V                  (-) -> Speaker (-)
GND  -> GND
TRIG -> GPIO 5
ECHO -> 1kΩ / 2kΩ Divider -> GPIO 18
```

---

## 📋 Complete Pin Table

| Module | Module Pin | ESP32 Pin | Electrical / Logic Guidelines |
| :--- | :--- | :--- | :--- |
| **MAX98357A I2S Amp** | DIN / SD | **GPIO 27** | I2S Data In (3.3V logic) |
| **MAX98357A I2S Amp** | BCLK | **GPIO 26** | I2S Bit Clock (3.3V logic) |
| **MAX98357A I2S Amp** | LRC / WS | **GPIO 25** | I2S Word Select / Left-Right Clock |
| **MAX98357A Power** | VIN / GND | **5V / GND** | Power from 5V rail for 3W output |
| **MPU-6050 Accel/Gyro** | SDA / SCL | **GPIO 21 / 22** | 3.3V I2C bus (Common GND) |
| **HC-SR04 Distance** | TRIG | **GPIO 5** | 3.3V Trigger output (10 µs pulse) |
| **HC-SR04 Distance** | ECHO | **GPIO 18** | **Must use 1kΩ / 2kΩ Voltage Divider** (5V to 3.3V max) |
| **Active Buzzer** | (+) | **GPIO 4** | Active HIGH drive (emergency fall siren only) |
| **Safe Switch (Button)** | Pin 1 / Pin 2 | **GPIO 19 / GND** | Active LOW (internal `INPUT_PULLUP` enabled) |
| **ESP32-CAM UART Link** | RX1 / TX1 | **GPIO 32 / 33** | Connect to CAM TX0 (GPIO 1) & RX0 (GPIO 3) |

---

## 📁 Repository Structure

```
d:/iot_new/
├── DIAGNOSIS.md                 # Full root cause analysis and engineering fixes
├── README.md                    # System architecture and setup guide
├── audio/                       # 35 real Tamil & English MP3 audio speech clips
├── data/
│   └── currency_50/             # 5 sample test images of ₹50 note (100% verified)
├── firmware/
│   ├── esp32_cam/               # ESP32-CAM Firmware (PlatformIO)
│   │   ├── include/cam_config.h # Pin definitions, Wi-Fi credentials, server IP
│   │   ├── src/main.cpp         # Snapshot server, MJPEG stream, brownout protection
│   │   └── platformio.ini
│   └── esp32_main/              # Main ESP32 Firmware (PlatformIO)
│       ├── include/             # config.h, audio_player.h, fall_detector.h, secrets.h
│       ├── src/main.cpp         # Fall detector, I2S audio, CLI simulation engine
│       └── platformio.ini
├── server/                      # Python AI Vision & Speech Backend
│   ├── app.py                   # FastAPI server (YOLOv8 + OCR + Audio Player)
│   ├── webcam_assistant.py      # Interactive OpenCV Assistant UI
│   ├── start_assistant.bat      # One-click startup script for Windows
│   ├── .env.example             # Environment variable template
│   └── requirements.txt         # Dependencies (fastapi, ultralytics, opencv, pygame)
└── tools/                       # Standalone Diagnostic & Verification Scripts
    ├── test_camera.py           # Camera snapshot & MJPEG stream tester
    ├── test_speaker.py          # PC & hardware MAX98357A speaker audio tester
    ├── test_fall_sensor.py      # MPU6050 & buzzer & safe switch tester
    └── test_telegram.py         # Telegram Bot API alert verification
```

---

## 🚀 Flashing & Running Instructions

### 1. Build & Upload Firmware (PlatformIO)

**Board 1: ESP32-CAM**
```powershell
# In terminal:
cd d:\iot_new\firmware\esp32_cam
pio run -t upload
```
*(Remember to bridge GPIO 0 to GND while pressing RESET to enter flash mode, then disconnect GPIO 0 and press RESET to run).*

**Board 2: Main ESP32 DevKit**
```powershell
cd d:\iot_new\firmware\esp32_main
pio run -t upload
```

---

### 2. Run the Python Detection Server

```powershell
cd d:\iot_new\server
python app.py
```
Or double-click `server/start_assistant.bat`.

To launch the interactive visual assistant window:
```powershell
cd d:\iot_new\server
# To connect to ESP32-CAM stream:
python webcam_assistant.py http://<YOUR_ESP32_CAM_IP>:81/stream

# Or to run with local USB webcam fallback:
python webcam_assistant.py
```

---

### 3. Run Diagnostic Verification Tests

1. **Test Speaker Audio:**
   ```powershell
   python tools/test_speaker.py
   ```
   Plays "System ready" and tests both PC speaker and MAX98357A hardware speaker.

2. **Test Camera Stream:**
   ```powershell
   python tools/test_camera.py <YOUR_ESP32_CAM_IP>
   ```

3. **Test MPU6050 Fall Sensor & Buzzer:**
   ```powershell
   python tools/test_fall_sensor.py
   ```

4. **Test Telegram Alerts:**
   ```powershell
   python tools/test_telegram.py
   ```

---

## ⚠️ Required Physical Actions

1. **Power Supply:** Connect the ESP32-CAM to a dedicated **5V $\ge$ 2A power supply**. Place a **470 µF capacitor across 5V and GND** near the board to absorb Wi-Fi radio current spikes.
2. **Wi-Fi Credentials:** Set your Wi-Fi SSID and Password in `firmware/esp32_cam/include/cam_config.h` and `firmware/esp32_main/include/secrets.h`.
3. **Telegram Authorization:** Open your Telegram app, search for **`@elder_assist_alert_bot`**, and click **Start** (`/start`) once. This authorizes the bot to deliver emergency fall alerts to chat ID `7906413709`.
4. **Common Ground:** Ensure a **common GND wire** connects the ESP32-CAM, Main ESP32, MPU-6050, and MAX98357A amplifier.
