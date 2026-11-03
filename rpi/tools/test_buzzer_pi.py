"""
Diagnostic Tool: Emergency Active Buzzer Test
=============================================
Tests the emergency buzzer on BCM GPIO 27 (Physical Pin 13).
Pulsates the buzzer ON and OFF for 3 seconds.

ELECTRICAL WARNING:
If using a 5V active buzzer that draws > 16mA, drive it via an NPN
transistor (e.g. 2N2222) with a 1kΩ base resistor from BCM GPIO 27.
Never connect 5V directly to a Raspberry Pi GPIO pin.
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

from rpi.alert_manager import AlertManager

def test_buzzer():
    print("\n--- [TEST 5/8] Emergency Buzzer Test ---")
    print("Wiring Reference:")
    print("  • Buzzer Signal (+) -> Physical Pin 13 (BCM GPIO 27)")
    print("  • Buzzer Ground (-) -> Physical Pin 14 (GND)")
    print("\nActivating buzzer in pulsating test mode for 3 seconds...")

    alerts = AlertManager()
    alerts.start_buzzer()
    time.sleep(3.0)
    alerts.stop_buzzer()
    alerts.stop()

    print("✅ Buzzer test completed.")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_buzzer()
