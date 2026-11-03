import time
import subprocess
import sys
import os
import serial.tools.list_ports

FIRMWARE_DIR = r"d:\iot-blind\firmware\esp32_main\.pio\build\esp32dev"
BOOTLOADER = rf"{FIRMWARE_DIR}\bootloader.bin"
PARTITIONS = rf"{FIRMWARE_DIR}\partitions.bin"
APP_BIN = rf"{FIRMWARE_DIR}\firmware.bin"
SPIFFS_BIN = rf"{FIRMWARE_DIR}\spiffs.bin"

print("=" * 60)
print("  MONITORING FOR ESP32 VIRTUAL COM PORT (CP2102)...")
print("  Standing daemon waiting for driver installation...")
print("=" * 60)

detected_port = None
while True:
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if ports:
        detected_port = ports[0]
        print(f"\n[FOUND PORT] Detected COM Port: {detected_port}!")
        break
    time.sleep(2)

time.sleep(2) # Give Windows a moment to finish configuring the port

print(f"\n[FLASHING START] Flashing ESP32 on {detected_port}...")

cmd_flash = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32",
    "--port", detected_port,
    "--baud", "921600",
    "write_flash", "-z",
    "0x1000", BOOTLOADER,
    "0x8000", PARTITIONS,
    "0x10000", APP_BIN
]

res = subprocess.run(cmd_flash)
if res.returncode != 0:
    print("[RETRYING] Retrying at 115200 baud...")
    cmd_flash[6] = "115200"
    res = subprocess.run(cmd_flash)

if res.returncode == 0:
    print("\n[FLASHING AUDIO] Flashing 35 Tamil WAV audio clips to SPIFFS partition...")
    cmd_spiffs = [
        sys.executable, "-m", "esptool",
        "--chip", "esp32",
        "--port", detected_port,
        "--baud", "921600",
        "write_flash", "-z",
        "0x160000", SPIFFS_BIN
    ]
    res_spiffs = subprocess.run(cmd_spiffs)
    if res_spiffs.returncode == 0:
        print("\n" + "=" * 60)
        print(f"  SUCCESS! ESP32 FIRMWARE & AUDIO FLASHED 100% TO {detected_port}!")
        print("=" * 60)
        sys.exit(0)

print("\n[ERROR] Flashing failed. Please check connection.")
sys.exit(1)
