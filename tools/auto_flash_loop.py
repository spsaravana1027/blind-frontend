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
print("  BACKGROUND FLASH LISTENER ACTIVE (COM10)")
print("  Pull out the MAX98357A VIN wire on the breadboard now!")
print("=" * 60)

for i in range(1, 60):
    print(f"\n[Attempt {i}/60] Checking ESP32...")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print(">>> FLASH SUCCESSFUL! 100% COMPLETE! <<<")
        print("=" * 60)
        sys.exit(0)
    time.sleep(1)

sys.exit(1)

