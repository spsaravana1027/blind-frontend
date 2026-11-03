import os
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def test_fall_and_buzzer():
    print("=" * 60)
    print("    MPU6050 ACCELEROMETER, BUZZER & SAFE SWITCH TEST")
    print("=" * 60)

    try:
        import serial
        import serial.tools.list_ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
        print(f"Available Serial ports: {ports}")

        target_port = "COM6" if "COM6" in ports else (ports[0] if ports else None)
        if not target_port:
            print("❌ No serial COM port found. Please connect ESP32 DevKit via USB.")
            return False

        print(f"Connecting to ESP32 on {target_port} at 115200 baud...")
        ser = serial.Serial(target_port, 115200, timeout=1.5)
        time.sleep(2)

        # 1. Check System Status
        print("\n--- 1. Reading System & MPU6050 Diagnostics ---")
        ser.write(b"status\n")
        time.sleep(0.5)
        response = ser.read_all().decode('utf-8', errors='ignore')
        print(response)

        # 2. Trigger Fall Simulation
        print("\n--- 2. Triggering Simulated Fall Event ---")
        ser.write(b"fall\n")
        time.sleep(1.0)
        fall_resp = ser.read_all().decode('utf-8', errors='ignore')
        print(fall_resp)
        print(">> Buzzer should be sounding continuous emergency alarm!")

        time.sleep(2.0)

        # 3. Trigger Safe Switch Press
        print("\n--- 3. Pressing Safe Switch (Deactivating Buzzer) ---")
        ser.write(b"safe\n")
        time.sleep(1.0)
        safe_resp = ser.read_all().decode('utf-8', errors='ignore')
        print(safe_resp)
        print(">> Buzzer should be stopped and user confirmed safe!")

        ser.close()
        print("\n✅ MPU6050, Buzzer, and Safe Switch sequence completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Serial test error: {e}")
        return False

if __name__ == "__main__":
    test_fall_and_buzzer()
