import sys
import time
import subprocess
import os

FIRMWARE_DIR = r"d:\iot-blind\firmware\esp32_main\.pio\build\esp32dev"
BOOTLOADER = rf"{FIRMWARE_DIR}\bootloader.bin"
PARTITIONS = rf"{FIRMWARE_DIR}\partitions.bin"
APP_BIN = rf"{FIRMWARE_DIR}\firmware.bin"
SPIFFS_BIN = rf"{FIRMWARE_DIR}\spiffs.bin"
PORT = "COM10"

print("=" * 60)
print("  FLASHING ESP32 ON COM10...")
print("  IMPORTANT: PRESS AND HOLD THE 'BOOT' BUTTON ON ESP32 NOW!")
print("=" * 60)

cmd = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32",
    "--port", PORT,
    "--baud", "460800",
    "write-flash", "-z",
    "0x1000", BOOTLOADER,
    "0x8000", PARTITIONS,
    "0x10000", APP_BIN,
    "0x160000", SPIFFS_BIN
]

success = False
for attempt in range(1, 6): # Try up to 5 times (gives user ample time)
    print(f"\n>>> [ATTEMPT {attempt}/5] Connecting to ESP32 on {PORT}...")
    print(">>> (PLEASE HOLD DOWN THE 'BOOT' BUTTON ON ESP32!)")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        success = True
        break
    time.sleep(2)

if success:
    print("\n" + "=" * 60)
    print("  SUCCESS! ESP32 FIRMWARE & AUDIO FLASHED 100% PERFECTLY!")
    print("  STARTING AI SERVER WITH PHYSICAL SPEAKER ON COM10...")
    print("=" * 60)
    # Start app.py
    subprocess.Popen([sys.executable, r"d:\iot-blind\server\app.py"], cwd=r"d:\iot-blind\server")
    print("  Server is now running on https://192.168.29.89:8000/camera")
    sys.exit(0)
else:
    print("\n[ERROR] Flashing failed after 5 attempts.")
    sys.exit(1)
