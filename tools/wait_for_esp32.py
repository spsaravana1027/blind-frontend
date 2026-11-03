import sys
import time
import subprocess
import serial

PORT = "COM10"
APP_BIN = r"d:\iot-blind\firmware\esp32_main\.pio\build\esp32dev\firmware.bin"

print("=" * 60)
print("  ESP32 POWER RECOVERY & FLASH MONITOR")
print("  Waiting for ESP32 to boot or flash...")
print("=" * 60)

cmd = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32",
    "--port", PORT,
    "--baud", "460800",
    "write-flash", "-z",
    "0x10000", APP_BIN
]

t0 = time.time()
while time.time() - t0 < 60:
    # 1. Try esptool flash
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print(">>> SUCCESS! ESP32 FLASHED SUCCESSFULLY! <<<")
        print("=" * 60)
        sys.exit(0)
    
    # 2. Check if serial sent anything
    try:
        s = serial.Serial(PORT, 115200, timeout=0.2)
        s.dtr = False
        s.rts = False
        if s.in_waiting:
            raw = s.read(s.in_waiting)
            print("Received from ESP32:", raw)
        s.close()
    except:
        pass
    
    time.sleep(1)

print("Timeout after 60 seconds.")
sys.exit(1)

