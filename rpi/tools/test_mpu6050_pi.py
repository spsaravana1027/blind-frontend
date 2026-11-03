"""
Diagnostic Tool: MPU-6050 Fall Detection Sensor Test
====================================================
Tests I2C connection (SDA BCM GPIO 2, SCL BCM GPIO 3).
Validates accelerometer and gyroscope readings and calculates posture tilt angle.
"""

import sys
import time
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rpi.fall_detection import FallDetector

def test_mpu6050():
    print("\n--- [TEST 2/8] MPU-6050 Accelerometer & Gyroscope ---")
    print("Wiring Reference:")
    print("  • VCC -> Physical Pin 1 (3V3)")
    print("  • GND -> Physical Pin 6 (GND)")
    print("  • SDA -> Physical Pin 3 (BCM GPIO 2)")
    print("  • SCL -> Physical Pin 5 (BCM GPIO 3)")
    print("\nInitializing MPU-6050...")

    sensor = FallDetector()

    if not sensor.hardware_active:
        print("\n⚠️ WARNING: MPU-6050 hardware was not detected on I2C bus 1 (Addr 0x68).")
        print("Troubleshooting Checklist:")
        print("1. Did you enable I2C? Run: sudo raspi-config -> Interface Options -> I2C -> Enable.")
        print("2. Run 'i2cdetect -y 1' in terminal. Address '68' must appear in the grid.")
        print("3. Check that VCC is connected to 3.3V (Pin 1), NOT 5V, and GND is connected (Pin 6).")
        print("Continuing with simulated telemetry...")

    print("\nReading sensor values for 5 seconds (move/tilt the sensor to test)...")
    print(f"{'Time':<8} | {'Accel (g)':<10} | {'Gyro (deg/s)':<14} | {'Tilt (deg)':<10}")
    print("-" * 50)

    for i in range(10):
        time.sleep(0.5)
        ax, ay, az, gx, gy, gz = sensor.read_raw()
        import math
        accel_mag = math.sqrt(ax * ax + ay * ay + az * az)
        gyro_mag = math.sqrt(gx * gx + gy * gy + gz * gz)
        cos_tilt = max(-1.0, min(1.0, az / (accel_mag + 0.0001)))
        tilt_deg = math.degrees(math.acos(cos_tilt))

        print(f"{i*0.5:5.1f}s   | {accel_mag:6.2f} g   | {gyro_mag:8.1f} deg/s   | {tilt_deg:6.1f}°")

    sensor.stop()
    print("\n✅ MPU-6050 test completed.")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_mpu6050()
