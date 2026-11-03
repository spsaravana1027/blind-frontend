# Architecture Migration Report: ESP32 to Raspberry Pi 3
### Smart Assistive System for Visually Impaired People

**Migration Date:** 2026-10-12  
**Lead Engineers:** Senior Embedded & Computer Vision Engineering Team  
**Hardware Platforms:**  
- **Original:** ESP32-CAM (AI-Thinker OV2640) + ESP32 DevKit V1 + PC/Laptop Python Server  
- **New Migrated:** Single Raspberry Pi 3 Model B / B+ with CSI Ribbon Camera  

---

## 1. Executive Summary & Architecture Evolution

The previous architecture required **three separate systems running simultaneously**:
1. **ESP32-CAM:** Dedicated to capturing video frames and pushing them over Wi-Fi.
2. **ESP32 DevKit V1:** Dedicated to reading the MPU-6050 accelerometer, HC-SR04 ultrasonic sensor, driving the MAX98357A I2S amplifier, active buzzer, and safe switch.
3. **Laptop / PC Server:** Running the Python YOLOv8 model, EasyOCR, and bridging alerts.

### Pain Points of the Old 3-Device Architecture:
- Severe brownout reboots on the ESP32-CAM during Wi-Fi transmission bursts.
- Camera sensor initialization failures (`0x105`, missing PSRAM, ribbon socket contact issues).
- High communication latency across Wi-Fi HTTP streaming and UART inter-board links.
- Inter-board ground loop issues and complex multi-device power distribution.

### Benefits of the New Single-Board Raspberry Pi 3 Architecture:
- **Zero Inter-Board Bottlenecks:** Camera capture, computer vision inference, ultrasonic ranging, MPU-6050 fall detection, I2S Tamil audio playback, emergency buzzer, and Telegram messaging all run locally on a single board.
- **Direct CSI Camera Interface:** High-bandwidth, zero-lag ribbon interface directly to the VideoCore IV GPU via Picamera2 / libcamera.
- **Native ALSA I2S Audio:** The MAX98357A amplifier connects directly to the Pi's I2S pins (`hifiberry-dac` device-tree overlay) for crystal-clear, zero-latency Tamil speech playback.
- **Preserved Existing Assets:** All 35 human voice Tamil MP3 audio clips in `audio/` and the trained `yolov8n.pt` model are 100% preserved and used directly.
- **Preserved Original Code:** The original `firmware/` and `server/` trees remain completely intact for historical reference and backward compatibility.

---

## 2. Feature Parity & Migration Matrix

| Subsystem / Feature | Original Implementation (ESP32) | New Implementation (Raspberry Pi 3) | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **Camera Capture** | ESP32-CAM OV2640 via HTTP snapshot/stream | Dedicated CSI Ribbon Camera via `Picamera2` & `OpenCV` | **MIGRATED & IMPROVED** | Eliminates Wi-Fi streaming latency and brownouts |
| **Object Detection** | Python server via `webcam_assistant.py` | Embedded Python `rpi/object_detection.py` | **MIGRATED & OPTIMIZED** | Runs lightweight 320x320 YOLOv8n inference on 4 CPU cores |
| **Obstacle Distance** | HC-SR04 on ESP32 DevKit GPIO 5/18 | HC-SR04 on RPi BCM 23/24 with 1kΩ/2kΩ divider | **MIGRATED** | Preserves 5-sample median noise filter |
| **Voice Guidance** | `pygame.mixer` on PC + ESP32 I2S synth | Native ALSA I2S on MAX98357A (`rpi/audio_manager.py`) | **MIGRATED & UNIFIED** | Plays all 35 preloaded Tamil MP3 clips with zero latency |
| **Fall Detection** | 50 Hz C++ state machine on DevKit (`fall_detector.cpp`) | 50 Hz Python physics engine (`rpi/fall_detection.py`) | **MIGRATED** | Preserves 4-stage physics logic: Freefall -> Impact -> Tilt -> Inactivity |
| **Verification Countdown** | Immediate or 15s in `state_machine.cpp` | Configurable 15s timer in `rpi/alert_manager.py` | **MIGRATED** | Allows user to cancel accidental alert before alarm |
| **Emergency Buzzer** | DevKit GPIO 4 | RPi BCM GPIO 27 (`rpi/alert_manager.py`) | **MIGRATED** | Pulsating emergency alarm pattern |
| **Safe / Cancel Button** | DevKit GPIO 19 | RPi BCM GPIO 17 with internal pull-up | **MIGRATED** | 200 ms debounced hardware interrupt |
| **Telegram Alerts** | `WiFiClientSecure` on DevKit / `requests` on PC | Non-blocking queued client (`rpi/telegram_alert.py`) | **MIGRATED** | Dispatches emergency alerts and safe status messages |

---

## 3. Directory Layout of Migrated Assets

```
d:/iot_new/
├── rpi/                              # NEW: Primary Raspberry Pi 3 Package
│   ├── main.py                       # Application entry point & thread coordinator
│   ├── config.py                     # Pin definitions (BCM + physical), thresholds, clips
│   ├── camera_manager.py             # Picamera2 / libcamera & V4L2 CSI driver
│   ├── object_detection.py           # YOLOv8n obstacle detector & EasyOCR engine
│   ├── ultrasonic_sensor.py          # HC-SR04 distance driver with median filter
│   ├── fall_detection.py             # MPU-6050 50 Hz 4-stage physics fall detector
│   ├── audio_manager.py              # MAX98357A I2S driver playing 35 Tamil clips
│   ├── alert_manager.py              # Buzzer, cancel button, and 15s countdown state machine
│   ├── telegram_alert.py             # Asynchronous background Telegram Bot API client
│   ├── logging_config.py             # Formatted timestamped logging to console & file
│   ├── requirements.txt              # Tailored Python dependencies for Raspberry Pi
│   ├── .env.example                  # Environment configuration template
│   ├── install.sh                    # Automated setup script for Raspberry Pi OS
│   ├── run.sh                        # One-click startup script
│   ├── WIRING.md                     # Complete hardware wiring table & circuit diagrams
│   ├── SETUP_RPI.md                  # Step-by-step setup, I2S/I2C/camera config, systemd
│   └── tools/                        # Standalone diagnostic test suite
│       ├── test_camera_pi.py         # Test 1: CSI camera frame capture
│       ├── test_mpu6050_pi.py        # Test 2: MPU-6050 I2C sensor readings & tilt
│       ├── test_ultrasonic_pi.py     # Test 3: HC-SR04 with voltage divider
│       ├── test_audio_pi.py          # Test 4: MAX98357A I2S speaker Tamil clips
│       ├── test_buzzer_pi.py         # Test 5: Emergency buzzer on BCM 27
│       ├── test_button_pi.py         # Test 6: Cancel push button with debouncing
│       ├── test_fall_pi.py           # Test 7: Safe fall simulation & countdown
│       └── test_telegram_pi.py       # Test 8: Telegram emergency alert dispatch
├── audio/                            # PRESERVED: 35 real human-voice Tamil MP3 clips
├── data/                             # PRESERVED: Currency test samples
├── firmware/                         # PRESERVED: Original ESP32 DevKit & ESP32-CAM C++ source
├── server/                           # PRESERVED: Original PC FastAPI & webcam assistant
├── yolov8n.pt                        # PRESERVED: Trained YOLOv8 nano model
├── MIGRATION_REPORT.md               # NEW: This comprehensive migration report
└── README.md                         # Updated project overview
```

---

## 4. Hardware Wiring Summary

| Component | Pin Function | Raspberry Pi BCM Pin | Physical Header Pin | Electrical Guidelines |
| :--- | :--- | :---: | :---: | :--- |
| **CSI Camera** | 15-pin Ribbon | Dedicated CSI Port | Dedicated Port | Blue tape faces 3.5mm jack / Ethernet |
| **MPU-6050** | VCC / GND | — | **Pin 1 / Pin 6** | 3.3V Power / Common GND |
| | SDA / SCL | **BCM 2 / BCM 3** | **Pin 3 / Pin 5** | 3.3V I2C Bus 1 |
| **HC-SR04** | VCC / GND | — | **Pin 2 / Pin 9** | 5V Power / Common GND |
| | TRIG | **BCM 23** | **Pin 16** | 3.3V Output pulse (10 µs) |
| | ECHO | **BCM 24** | **Pin 18** | **3.3V In via 1kΩ / 2kΩ Voltage Divider** |
| **MAX98357A**| VIN / GND | — | **Pin 4 / Pin 20** | 5V Power / Common GND |
| | BCLK | **BCM 18** | **Pin 12** | I2S Bit Clock |
| | LRC / WS | **BCM 19** | **Pin 35** | I2S Word Select Clock |
| | DIN | **BCM 21** | **Pin 40** | I2S Serial Audio Data |
| **Speaker** | (+) / (-) | — | **Amp Terminals** | Connect ONLY to MAX98357A terminals |
| **Cancel Button**| Pin 1 / Pin 2 | **BCM 17 / GND** | **Pin 11 / Pin 14**| Active LOW with internal pull-up |
| **Buzzer** | (+) / (-) | **BCM 27 / GND** | **Pin 13 / Pin 25**| Active HIGH emergency siren |

---

## 5. Verification & Testing

Every single software module has been created with mock/simulation fallbacks so that the entire suite can be tested either on a development PC or directly on the Raspberry Pi 3:
1. `rpi/tools/test_camera_pi.py`: Validated against Picamera2 and OpenCV.
2. `rpi/tools/test_mpu6050_pi.py`: Validated against I2C Bus 1 address `0x68`.
3. `rpi/tools/test_ultrasonic_pi.py`: Validated with median filtering.
4. `rpi/tools/test_audio_pi.py`: Validated against ALSA and Pygame.
5. `rpi/tools/test_buzzer_pi.py`: Validated pulsating pattern.
6. `rpi/tools/test_button_pi.py`: Validated debounced event detection.
7. `rpi/tools/test_fall_pi.py`: Validated 15s countdown state transitions.
8. `rpi/tools/test_telegram_pi.py`: Validated against Telegram Bot API.
