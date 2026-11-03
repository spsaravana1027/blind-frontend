"""
Diagnostic Tool: MAX98357A I2S Audio Amplifier & Speaker Test
=============================================================
Tests I2S sound output on Raspberry Pi by playing preloaded Tamil voice clips.
Wiring Reference:
  • VIN     -> Physical Pin 4 (5V)
  • GND     -> Physical Pin 6 (GND)
  • BCLK    -> Physical Pin 12 (BCM GPIO 18)
  • LRC/WS  -> Physical Pin 35 (BCM GPIO 19)
  • DIN     -> Physical Pin 40 (BCM GPIO 21)
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

from rpi.audio_manager import AudioManager

def test_audio():
    print("\n--- [TEST 4/8] MAX98357A I2S Audio Amplifier & Speaker ---")
    print("Testing audio playback through I2S speaker...")

    audio = AudioManager()

    print("\nPlaying Tamil Audio Clip #1: 'System Ready' (0001_system_ready.mp3)...")
    audio.play_clip(1, force=True, blocking=True)
    time.sleep(1.0)

    print("Playing Tamil Audio Clip #14: 'Obstacle Warning' (0014_obstacle_warning.mp3)...")
    audio.play_clip(14, force=True, blocking=True)
    time.sleep(1.0)

    print("Playing Tamil Audio Clip #39: 'User Safe' (0039_user_safe.mp3)...")
    audio.play_clip(39, force=True, blocking=True)

    print("\nDid you hear the Tamil speech through the speaker attached to MAX98357A?")
    print("If NO SOUND was heard, verify Raspberry Pi I2S configuration:")
    print("1. Did you add 'dtoverlay=hifiberry-dac' to /boot/config.txt or /boot/firmware/config.txt?")
    print("2. Check 'aplay -l' in terminal. A sound card named 'snd_rpi_hifiberry_dac' should be listed.")
    print("3. Check that BCLK is Pin 12 (BCM 18), LRC is Pin 35 (BCM 19), DIN is Pin 40 (BCM 21).")
    print("4. Check that VIN is connected to 5V (Pin 4) and GND is connected (Pin 6).")

    audio.stop()
    print("\n✅ Audio test completed.")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_audio()
