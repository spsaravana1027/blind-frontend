"""
Diagnostic Tool: Emergency Cancel / Safe Push Button Test
==========================================================
Tests the debounced push button on BCM GPIO 17 (Physical Pin 11).
Uses the Raspberry Pi internal PULL-UP resistor (Active LOW when pressed to GND).
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

def test_button():
    print("\n--- [TEST 6/8] Emergency Cancel Push Button Test ---")
    print("Wiring Reference:")
    print("  • Button Leg 1 -> Physical Pin 11 (BCM GPIO 17)")
    print("  • Button Leg 2 -> Physical Pin 9 or 14 (GND)")
    print("  (Internal pull-up enabled. Button connects pin to GND when pressed).")
    print("\nPlease PRESS the push button within the next 10 seconds...")

    alerts = AlertManager()
    pressed = False

    def on_cancel():
        nonlocal pressed
        pressed = True
        print("\n🎉 BUTTON PRESS DETECTED SUCCESSFULLY!")

    alerts.on_alert_cancelled = on_cancel

    start_t = time.time()
    while time.time() - start_t < 10.0:
        if pressed:
            break
        time.sleep(0.2)

    alerts.stop()

    if not pressed:
        print("\n⚠️ No button press detected within 10 seconds.")
        print("Check that one terminal connects to Physical Pin 11 and the other connects to GND.")
    else:
        print("✅ Button test completed successfully.")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_button()
