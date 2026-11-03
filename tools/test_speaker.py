import os
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audio"))

def test_speaker():
    print("=" * 60)
    print("           SPEAKER AUDIO SUBSYSTEM TEST")
    print("=" * 60)
    print(f"Audio directory: {AUDIO_DIR}")

    # 1. Test PC Speaker playback via Pygame
    try:
        import pygame
        pygame.mixer.init()
        print("✅ Pygame audio mixer initialized.")
        
        # Test boot greeting: 0040_system_connected.mp3 / 0001_system_ready.mp3
        test_clip = os.path.join(AUDIO_DIR, "0001_system_ready.mp3")
        if not os.path.exists(test_clip):
            test_clip = os.path.join(AUDIO_DIR, "0040_system_connected.mp3")

        if os.path.exists(test_clip):
            print(f"🔊 Playing boot greeting clip on PC / External Speaker: {os.path.basename(test_clip)}")
            pygame.mixer.music.load(test_clip)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            print("✅ PC / External Speaker playback completed successfully!")
        else:
            print(f"⚠️ Clip file not found: {test_clip}")
    except Exception as e:
        print(f"❌ PC audio test error: {e}")

    # 2. Test Hardware MAX98357A I2S Speaker on ESP32 via Serial bridge
    print("\nChecking for connected ESP32 DevKit for Hardware I2S Speaker test...")
    try:
        import serial
        import serial.tools.list_ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
        print(f"Available Serial ports: {ports}")
        
        target_port = "COM6" if "COM6" in ports else (ports[0] if ports else None)
        if target_port:
            print(f"📡 Testing hardware MAX98357A speaker on {target_port}...")
            ser = serial.Serial(target_port, 115200, timeout=1)
            time.sleep(1.5)
            # Send I2S test tone (440 Hz for 800ms)
            ser.write(b"i2s 440 800\n")
            ser.flush()
            time.sleep(1.0)
            # Send System ready clip
            ser.write(b"clip 1\n")
            ser.flush()
            time.sleep(1.5)
            ser.close()
            print("✅ MAX98357A I2S test command sent to ESP32 DevKit successfully!")
        else:
            print("ℹ️ No ESP32 serial COM port found right now (connect ESP32 via USB to test hardware I2S speaker).")
    except Exception as e:
        print(f"ℹ️ Hardware serial test notice: {e}")

if __name__ == "__main__":
    test_speaker()
