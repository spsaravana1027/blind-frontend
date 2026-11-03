import sys
import time
import subprocess

FIRMWARE_DIR = r"d:\iot-blind\firmware\esp32_main\.pio\build\esp32dev"
BOOTLOADER = rf"{FIRMWARE_DIR}\bootloader.bin"
PARTITIONS = rf"{FIRMWARE_DIR}\partitions.bin"
APP_BIN = rf"{FIRMWARE_DIR}\firmware.bin"
SPIFFS_BIN = rf"{FIRMWARE_DIR}\spiffs.bin"
PORT = "COM10"

print("=" * 60)
print("  MONITORING FOR ESP32 BOOTLOADER ON COM10...")
print("  Please do the hardware button trick:")
print("  1. Press and HOLD the 'BOOT' button on ESP32.")
print("  2. Click the 'EN' (or 'RST') button once.")
print("  3. Keep holding 'BOOT' for 2 seconds.")
print("=" * 60)

cmd = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32",
    "--port", PORT,
    "--baud", "115200",
    "write-flash", "-z",
    "0x1000", BOOTLOADER,
    "0x8000", PARTITIONS,
    "0x10000", APP_BIN,
    "0x160000", SPIFFS_BIN
]

for attempt in range(1, 30): # Run for 30 attempts (~5 minutes)
    print(f"\n[Attempt {attempt}/30] Waiting for ESP32 Bootloader on {PORT}...")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print("  SUCCESS! FIRMWARE & AUDIO 100% FLASHED TO ESP32!")
        print("=" * 60)
        # Launch server
        subprocess.Popen([sys.executable, r"d:\iot-blind\server\app.py"], cwd=r"d:\iot-blind\server")
        print("AI Server restarted and ready on COM10!")
        sys.exit(0)
    time.sleep(2)

sys.exit(1)

