"""
Diagnostic Tool: Fall Verification & Cancellation Test
======================================================
Safely simulates the complete emergency fall workflow:
1. Injects simulated fall event.
2. Enters FALL_COUNTDOWN state (15s verification window).
3. Prompts user to either:
   - Option A: Press the Cancel Button (or type 's') to verify safe cancellation.
   - Option B: Let the countdown expire to verify emergency siren & Telegram dispatch.
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

from rpi.alert_manager import AlertManager, STATE_MONITORING, STATE_FALL_COUNTDOWN, STATE_EMERGENCY_ALARM
from rpi.audio_manager import AudioManager

def test_fall_workflow():
    print("\n--- [TEST 7/8] Fall Detection & Emergency Workflow Test ---")
    print("Testing the 15-second verification countdown and cancellation logic...")

    audio = AudioManager()
    alerts = AlertManager(countdown_sec=10) # 10s for quick test

    fall_confirmed = False
    cancelled = False

    def on_confirmed():
        nonlocal fall_confirmed
        fall_confirmed = True
        print("\n🚨 COUNTDOWN EXPIRED! Emergency alarm activated.")
        audio.play_clip("emergency_fall", force=True)

    def on_cancelled():
        nonlocal cancelled
        cancelled = True
        print("\n✅ ALERT CANCELLED! User safe.")
        audio.play_clip("user_safe", force=True)

    def on_tick(rem):
        print(f"⏳ Countdown: {rem} seconds remaining (Press Button to cancel!)...")

    alerts.on_fall_confirmed = on_confirmed
    alerts.on_alert_cancelled = on_cancelled
    alerts.on_countdown_tick = on_tick

    print("\nSimulating Fall Event...")
    alerts.trigger_possible_fall()
    audio.play_clip("emergency_fall", force=True)

    start_t = time.time()
    while time.time() - start_t < 12.0:
        if cancelled or fall_confirmed:
            time.sleep(2.0)
            break
        time.sleep(0.5)

    alerts.stop()
    audio.stop()
    print("✅ Fall workflow test complete.")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_fall_workflow()
