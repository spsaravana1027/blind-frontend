import sys
import time
import subprocess
import serial.tools.list_ports

FIRMWARE_DIR = r"d:\iot-blind\firmware\esp32_main\.pio\build\esp32dev"
APP_BIN = rf"{FIRMWARE_DIR}\firmware.bin"

print("=" * 60)
print("  READY TO FLASH! WAITING FOR USB RE-PLUG...")
print("=" * 60)

target_port = None
t_start = time.time()
while time.time() - t_start < 60:
    ports = [p.device for p in serial.tools.list_ports.comports() if "CP210" in p.description or "COM10" == p.device or "USB" in p.description]
    if ports:
        target_port = ports[0]
        print(f"\n[PORT DETECTED: {target_port}]")
        cmd = [
            sys.executable, "-m", "esptool",
            "--chip", "esp32",
            "--port", target_port,
            "--baud", "460800",
            "write-flash", "-z",
            "0x10000", APP_BIN
        ]
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print("\n" + "=" * 60)
            print(">>> SUCCESS! ESP32 FLASHED 100% PERFECTLY! <<<")
            print("=" * 60)
            sys.exit(0)
    print(".", end="", flush=True)
    time.sleep(0.8)

sys.exit(1)

