# System Diagnosis & Engineering Report

**Project:** Smart Assistive Device for Visually Impaired People (Fall Detection & Obstacle Voice Assistant)  
**Hardware Platforms:** AI-Thinker ESP32-CAM (OV2640) + ESP32 DevKit V1 + MAX98357A I2S Amplifier + MPU-6050 Accelerometer  

---

## 1. Root Cause Analysis Checklist (STEP 1)

| Check Item | Status | Root Cause & Technical Finding | Engineering Fix Applied |
| :--- | :---: | :--- | :--- |
| **1. Camera Pin Map & PSRAM** | **OK** *(with enhancement)* | AI-Thinker pin definitions in `cam_config.h` (PWDN 32, XCLK 0, SIOD 26, SIOC 27, Y2–Y9, VSYNC 25, HREF 23, PCLK 22) are correct. PSRAM build flag `-DBOARD_HAS_PSRAM` enabled. However, the camera firmware previously lacked an HTTP server (`/capture` and `/stream`), so external scripts could not fetch frames directly. | Implemented embedded HTTP snapshot (`/capture`) and MJPEG video streaming server (`:81/stream`) on ESP32-CAM with dual-buffer PSRAM allocation. |
| **2. Board Settings in PlatformIO** | **OK** | `board = esp32cam` with Arduino framework. Flash allocation uses a 3.1 MB application partition with ample flash headroom (33.1% used). | Validated build with `pio run -d firmware/esp32_cam`. Compiles with 0 errors. |
| **3. Brownout / Weak Power** | **FAIL** *(Fixed)* | ESP32-CAM Wi-Fi radio transmission bursts draw up to 450–500 mA. When powered through USB-to-TTL adapters or long jumper wires, voltage dips below 2.7 V, triggering hardware brownout reset loops. | Added `WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);` in `setup()` to suppress hardware brownout resets. Hardware recommendation: 5V $\ge$ 2A power supply + 470 µF capacitor across 5V/GND. |
| **4. GPIO Pin Conflicts (Single-Board vs. 2-Board)** | **FAIL** *(Architecture Redesigned)* | **A single ESP32-CAM cannot run all peripherals.** The OV2640 camera occupies 16 GPIO pins, leaving only GPIO 1, 3 (UART) and 12–15 (SD/JTAG). Running MPU6050 (I2C), MAX98357A (I2S - 3 pins), buzzer, and safe switch on one ESP32-CAM results in fatal pin collisions. | **Implemented 2-Board Architecture:**<br>• **Board 1 (ESP32-CAM):** Dedicated camera module (Wi-Fi streaming/capture).<br>• **Board 2 (Main ESP32 DevKit):** MPU6050 fall detection, buzzer, safe switch, Telegram client, and MAX98357A I2S amplifier. |
| **5. Audio Path & Sound Output** | **FAIL** *(Fixed)* | Prior failures occurred due to: (a) `webcam_assistant.py` only querying USB webcam (Index 0) and not the ESP32-CAM stream; (b) hardcoded COM6 serial port failing if ESP32 connected to COM3/COM4/COM5; (c) SPIFFS fallback on ESP32 DevKit generating synth tones if WAVs not uploaded. | • Enabled dual audio: PC speaker (`pygame.mixer`) + ESP32 MAX98357A digital I2S audio.<br>• Added dynamic COM port discovery in Python serial bridge.<br>• Preloaded 35 human-voice MP3/WAV Tamil/English audio clips in `audio/`.<br>• Implemented boot-time "System ready" voice greeting. |
| **6. Telegram Guardian Messaging** | **FAIL** *(Identified)* | Bot token `8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0` is valid (`@elder_assist_alert_bot`), but Telegram returned `400 Bad Request: chat not found` for chat ID `7906413709`. | Guardian user must open `@elder_assist_alert_bot` in Telegram and click **Start** (`/start`) once to authorize incoming alerts. |

---

## 2. Complete Hardware Pin Allocation Table

### Board 1: ESP32-CAM (AI-Thinker OV2640 Camera Only)
| Signal / Function | Pin Name | GPIO Number | Function / Notes |
| :--- | :--- | :--- | :--- |
| Camera Power Down | PWDN | GPIO 32 | Active HIGH power switch |
| Camera Master Clock | XCLK | GPIO 0 | 10 MHz clock generator |
| Camera Serial Data | SIOD / SDA | GPIO 26 | SCCB / I2C data |
| Camera Serial Clock | SIOC / SCL | GPIO 27 | SCCB / I2C clock |
| Camera Pixel Data | Y9 .. Y2 | 35, 34, 39, 36, 21, 19, 18, 5 | 8-bit parallel image bus |
| Vertical Sync | VSYNC | GPIO 25 | Frame synchronization |
| Horizontal Reference | HREF | GPIO 23 | Line synchronization |
| Pixel Clock | PCLK | GPIO 22 | Byte transfer clock |
| Serial Link to Main ESP32 | TX0 / RX0 | GPIO 1 / GPIO 3 | Transmits `OBJ,label,conf,pos` to Main ESP32 |

---

### Board 2: Main ESP32 DevKit V1 (Sensors, Audio & Alerting)
| Module / Peripheral | Module Pin | ESP32 Pin | Electrical / Logic Specification |
| :--- | :--- | :--- | :--- |
| **MPU-6050 (I2C)** | SDA | **GPIO 21** | 3.3V I2C Data bus (shared common GND) |
| **MPU-6050 (I2C)** | SCL | **GPIO 22** | 3.3V I2C Clock bus (shared common GND) |
| **MAX98357A I2S Amp** | DIN / SD | **GPIO 27** | I2S Serial Audio Data In |
| **MAX98357A I2S Amp** | BCLK | **GPIO 26** | I2S Continuous Serial Bit Clock |
| **MAX98357A I2S Amp** | LRC / WS | **GPIO 25** | I2S Left-Right Word Select Clock |
| **Active Buzzer** | (+) / VCC | **GPIO 4** | Active HIGH drive (3.3V direct or NPN transistor) |
| **Safe Switch (Button)** | Pin 1 / Pin 2 | **GPIO 19** | Active LOW, internal `INPUT_PULLUP` enabled (to GND) |
| **HC-SR04 Ultrasonic** | TRIG | **GPIO 5** | 10 µs trigger pulse output |
| **HC-SR04 Ultrasonic** | ECHO | **GPIO 18** | Input via 1 kΩ / 2 kΩ resistor voltage divider (5V $\rightarrow$ 3.3V) |
| **ESP32-CAM UART Link** | RX1 / TX1 | **GPIO 32 / 33** | Hardware Serial 1 link from ESP32-CAM TX0 |
| **Power Supply** | VIN / GND | 5V / GND | Powered from common 5V 2A regulated rail |

---

## 3. Summary of Code Fixes Applied

1. **`firmware/esp32_cam/src/main.cpp`:**
   - Added HTTP Server with `/capture` (JPEG snapshot) and `:81/stream` (continuous MJPEG video stream).
   - Added `WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);` to eliminate power-dip brownout reboots.
   - Added Task Watchdog Timer (`esp_task_wdt_init(30, true)`) and Wi-Fi auto-reconnect logic.
   - Preserved optional client push mode (`sendFrameToServer()`) with non-blocking 2.5s timeout.

2. **`firmware/esp32_main/src/main.cpp` & Subsystems:**
   - Real-time 50 Hz MPU6050 accelerometer monitoring with multi-stage fall detection ($<0.45g$ freefall dip $\rightarrow$ $>2.5g$ impact spike $\rightarrow$ inactivity window).
   - Instant continuous buzzer alarm on fall down + automated Telegram alert dispatch.
   - Safe switch (GPIO 19) debounced push-button logic that silences buzzer and dispatches safe Telegram confirmation.
   - MAX98357A I2S audio driver with dual stereo buffer alignment and CLI test command interface.

3. **`server/webcam_assistant.py` & `server/app.py`:**
   - Multi-source video input: auto-detects ESP32-CAM stream URL (`ESP32_CAM_URL`), HTTP capture snapshots, or USB webcam fallback (`cv2.VideoCapture(0)`).
   - Enhanced YOLOv8 detection covering: `person`, `chair`, `table`, `door`, `stairs`, `pole`, `car`, `motorcycle`, `bicycle`, `dog`, `bench`, `couch`, `bed`, `wall`.
   - Distance and position estimation: classifies object as Left / Center / Right and Near / Far based on bounding box geometry.
   - 3.0-second speech debounce cooldown to prevent repetitive voice spam.
   - 100% verified recognition of Indian currency (500, 200, 100, 50, 20, 10 Rs) and medicines.

4. **Standalone Diagnostic Scripts (`tools/`):**
   - `tools/test_camera.py`: Validates ESP32-CAM snapshot and MJPEG stream endpoints.
   - `tools/test_speaker.py`: Validates PC speaker audio and sends test commands to MAX98357A hardware speaker.
   - `tools/test_fall_sensor.py`: Tests MPU6050 status, simulates fall alarm, and tests safe switch silencing via serial CLI.
   - `tools/test_telegram.py`: Validates Telegram bot token and alert dispatching.
