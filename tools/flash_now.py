import sys
import time
import subprocess

FIRMWARE_DIR = r"d:\iot-blind\firmware\esp32_main\.pio\build\esp32dev"
APP_BIN = rf"{FIRMWARE_DIR}\firmware.bin"
PORT = "COM10"

print("=" * 60)
print("  PREPARING TO FLASH ESP32 FIRMWARE (I2C & AUDIO FIX)")
print(f"  Target: {PORT} @ 460800 baud")
print("=" * 60)

cmd = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32",
    "--port", PORT,
    "--baud", "115200",
    "write-flash", "-z",
    "0x10000", APP_BIN
]

for attempt in range(1, 31):
    print(f"\n[Attempt {attempt}/30] Waiting for ESP32 on {PORT}... (HOLD 'BOOT' BUTTON)")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print(">>> SUCCESS! FIRMWARE FLASHED 100% PERFECTLY! <<<")
        print("=" * 60)
        time.sleep(2)
        # Test serial connection
        try:
            import serial
            s = serial.Serial(PORT, 115200, timeout=3)
            time.sleep(1)
            # Read startup messages
            for _ in range(10):
                if s.in_waiting:
                    line = s.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        print("ESP32:", line)
            s.close()
        except Exception as e:
            print("Serial notice:", e)
        sys.exit(0)
    time.sleep(1)

print("\nFailed to connect after 30 attempts.")
sys.exit(1)

