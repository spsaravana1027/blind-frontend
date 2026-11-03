import sys
import time
import subprocess

PORT = "COM10"
FIRMWARE_DIR = r"d:\iot-blind\firmware\esp32_main\.pio\build\esp32dev"
APP_BIN = rf"{FIRMWARE_DIR}\firmware.bin"

cmd = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32",
    "--port", PORT,
    "--baud", "460800",
    "write-flash", "-z",
    "0x10000", APP_BIN
]

print("=" * 60)
print("  WAITING FOR ESP32 IN DOWNLOAD MODE...")
print("=" * 60)

for i in range(1, 90): # 90 attempts = ~3 minutes
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print(">>> SUCCESS! FIRMWARE FLASHED 100%! <<<")
        print("=" * 60)
        sys.exit(0)
    time.sleep(1)

sys.exit(1)

