"""
Diagnostic Tool: HC-SR04 Ultrasonic Distance Sensor Test
========================================================
Validates distance sensing with median noise rejection.
CRITICAL ELECTRICAL SAFETY:
  • TRIG: BCM GPIO 23 (Physical Pin 16)
  • ECHO: BCM GPIO 24 (Physical Pin 18) -> MUST GO THROUGH 1kΩ / 2kΩ VOLTAGE DIVIDER!
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

from rpi.ultrasonic_sensor import UltrasonicSensor
from rpi.config import DISTANCE_CRITICAL_CM

def test_ultrasonic():
    print("\n--- [TEST 3/8] HC-SR04 Ultrasonic Distance Sensor ---")
    print("Wiring Reference & Voltage Divider:")
    print("  • VCC  -> Physical Pin 2 or 4 (5V)")
    print("  • GND  -> Physical Pin 6 (GND)")
    print("  • TRIG -> Physical Pin 16 (BCM GPIO 23)")
    print("  • ECHO -> 1kΩ Resistor -> Junction -> Physical Pin 18 (BCM GPIO 24)")
    print("            Junction -> 2kΩ Resistor -> Physical Pin 6 (GND)")
    print("\nInitializing HC-SR04...")

    sensor = UltrasonicSensor()
    sensor.start()

    if not sensor.hardware_active:
        print("\n⚠️ WARNING: Hardware GPIO is not available. Running in SIMULATED mode.")
        print("To test physical pins, execute directly on Raspberry Pi with RPi.GPIO installed.")

    print("\nReading distance continuously for 10 seconds. Place hands or obstacles in front...")
    print("-" * 55)

    try:
        for _ in range(20):
            time.sleep(0.5)
            dist = sensor.get_distance()
            status = "🚨 NEAR OBSTACLE!" if dist <= DISTANCE_CRITICAL_CM else "✅ Clear path"
            print(f"Measured Distance: {dist:5.1f} cm  [{status}]")
    finally:
        sensor.stop()

    print("\n✅ Ultrasonic sensor test completed.")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_ultrasonic()
