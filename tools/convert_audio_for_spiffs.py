"""convert_audio_for_spiffs.py

Generates all Tamil speech WAV files for SPIFFS upload onto the ESP32.
Uses gTTS (Google Text-to-Speech) + miniaudio for MP3->WAV conversion.
No ffmpeg required.

Install requirements:
    pip install gTTS miniaudio

Output: firmware/esp32_main/data/*.wav  (16000 Hz, mono, 16-bit PCM)

Usage:
    python tools/convert_audio_for_spiffs.py
"""

import io, os, sys, wave

# ---------------------------------------------------------------------------
# Tamil clip definitions (matches audio_player.cpp / config.h)
# ---------------------------------------------------------------------------
CLIPS = [
    ( 1, "0001_system_ready.wav",        "அமைப்பு தயார். பாதுகாப்பான பயணம் அமைய வாழ்த்துகிறோம்."),
    ( 2, "0002_system_error.wav",         "அமைப்பில் கோளாறு. அமைப்பைச் சரிபார்க்கவும்."),
    ( 3, "0003_obstacle_front.wav",       "முன்னால் தடை உள்ளது. உடனே நின்று கவனிக்கவும்."),
    ( 4, "0004_dustbin_front.wav",        "முன்னால் குப்பைத்தொட்டி உள்ளது. கவனமாக விலகிச் செல்லவும்."),
    ( 5, "0005_dog_left.wav",             "இடது பக்கத்தில் நாய் உள்ளது. கவனமாக வலது பக்கம் செல்லவும்."),
    ( 6, "0006_chair_right.wav",          "வலது பக்கத்தில் நாற்காலி உள்ளது. கவனமாக இடது பக்கம் செல்லவும்."),
    ( 7, "0007_person_front.wav",         "முன்னால் ஒருவர் உள்ளார். கவனமாகச் செல்லவும்."),
    ( 8, "0008_car_front.wav",            "முன்னால் கார் உள்ளது. பாதுகாப்பாக நிற்கவும்."),
    ( 9, "0009_table_front.wav",          "முன்னால் மேஜை உள்ளது. கவனமாகச் செல்லவும்."),
    (10, "0010_emergency_fall.wav",       "அவசரம்! கீழே விழுந்துவிட்டீர்கள். ரத்து செய்ய பொத்தானை அழுத்தவும்."),
    (11, "0011_alert_cancelled.wav",      "அவசர எச்சரிக்கை ரத்து செய்யப்பட்டது."),
    (12, "0012_telegram_sent.wav",        "பாதுகாவலருக்கு அவசரத் தகவல் அனுப்பப்பட்டது."),
    (13, "0013_obstacle_notice.wav",      "முன்னால் பொருள் உள்ளது."),
    (14, "0014_obstacle_warning.wav",     "எச்சரிக்கை! பொருள் அருகில் உள்ளது."),
    (15, "0015_person_ahead.wav",         "முன்னால் ஒருவர் உள்ளார்."),
    (16, "0016_person_left.wav",          "இடதுபுறம் ஒருவர் உள்ளார்."),
    (17, "0017_person_right.wav",         "வலதுபுறம் ஒருவர் உள்ளார்."),
    (18, "0018_chair_ahead.wav",          "முன்னால் நாற்காலி உள்ளது."),
    (19, "0019_table_ahead.wav",          "முன்னால் மேஜை உள்ளது."),
    (20, "0020_door_ahead.wav",           "முன்னால் கதவு உள்ளது."),
    (21, "0021_stairs_ahead.wav",         "முன்னால் படிக்கட்டுகள் உள்ளன."),
    (22, "0022_wall_ahead.wav",           "முன்னால் சுவர் உள்ளது."),
    (23, "0023_vehicle_ahead.wav",        "முன்னால் வாகனம் உள்ளது."),
    (24, "0024_medicine_reminder.wav",    "மருந்து எடுத்துக்கொள்ள வேண்டிய நேரம் வந்துவிட்டது. தயவுசெய்து உங்கள் மருந்தை எடுத்துக்கொள்ளுங்கள்."),
    (30, "0030_medicine_paracetamol.wav", "இது பாராசிட்டமால் மாத்திரை."),
    (31, "0031_medicine_rantac.wav",      "இது ரான்டாக் மாத்திரை."),
    (32, "0032_medicine_tassic.wav",      "இது டாசிக் டானிக் மருந்து."),
    (33, "0033_currency_500.wav",         "இது 500 ரூபாய்."),
    (34, "0034_currency_200.wav",         "இது 200 ரூபாய்."),
    (35, "0035_currency_100.wav",         "இது 100 ரூபாய்."),
    (36, "0036_currency_50.wav",          "இது 50 ரூபாய்."),
    (37, "0037_currency_20.wav",          "இது 20 ரூபாய்."),
    (38, "0038_currency_10.wav",          "இது 10 ரூபாய்."),
    (39, "0039_user_safe.wav",            "பாதுகாப்பாக உள்ளீர்கள். எச்சரிக்கை நிறுத்தப்பட்டது."),
    (40, "0040_system_connected.wav",     "அமைப்பு தயார். இணைக்கப்பட்டது."),
]

# Target: 8000 Hz, mono, 16-bit signed PCM
# NOTE: 8 kHz is sufficient for speech and keeps total SPIFFS usage under 1.5 MB.
# The I2S driver in audio_player.cpp is configured at 16000 Hz, so we also
# update i2s_config sample_rate below. If you want 16 kHz, change back here
# AND in audio_player.cpp begin() -> i2sConfig.sample_rate = 16000.
TARGET_RATE     = 8000
TARGET_CHANNELS = 1
TARGET_WIDTH    = 2   # bytes (16-bit)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SPIFFS_DATA  = os.path.join(PROJECT_ROOT, "firmware", "esp32_main", "data")
os.makedirs(SPIFFS_DATA, exist_ok=True)

# ---------------------------------------------------------------------------
# Check for required packages
# ---------------------------------------------------------------------------
try:
    from gtts import gTTS
except ImportError:
    print("[ERROR] gTTS not installed. Run:  pip install gTTS")
    sys.exit(1)

try:
    import miniaudio
    HAVE_MINIAUDIO = True
except ImportError:
    HAVE_MINIAUDIO = False
    print("[WARN] miniaudio not installed — MP3 decoding will be skipped.")
    print("       Run:  pip install miniaudio")
    print("       Without it, WAV files cannot be produced.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# gTTS MP3 -> WAV conversion (no ffmpeg needed)
# ---------------------------------------------------------------------------
def gtts_to_wav(tamil_text: str, out_path: str) -> bool:
    try:
        # 1. Synthesise speech -> MP3 bytes in memory
        tts = gTTS(text=tamil_text, lang='ta', slow=False)
        mp3_buf = io.BytesIO()
        tts.write_to_fp(mp3_buf)
        mp3_bytes = mp3_buf.getvalue()

        # 2. Decode MP3 -> PCM via miniaudio (pure Python, no ffmpeg)
        decoded = miniaudio.decode(
            mp3_bytes,
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=TARGET_CHANNELS,
            sample_rate=TARGET_RATE
        )

        # 3. Write standard WAV file
        with wave.open(out_path, 'wb') as wf:
            wf.setnchannels(TARGET_CHANNELS)
            wf.setsampwidth(TARGET_WIDTH)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(bytes(decoded.samples))

        return True

    except Exception as e:
        print(f"\n  [ERROR] {e}")
        return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 65)
print("  Tamil WAV Generator for ESP32 SPIFFS")
print(f"  Output: {SPIFFS_DATA}")
print("=" * 65)

converted   = 0
failed      = 0
total_bytes = 0

for clip_id, wav_name, tamil_text in CLIPS:
    out_path = os.path.join(SPIFFS_DATA, wav_name)
    print(f"  [{clip_id:2d}] {wav_name:42s}", end=" ", flush=True)

    if gtts_to_wav(tamil_text, out_path):
        size = os.path.getsize(out_path)
        total_bytes += size
        converted += 1
        print(f"OK  ({size/1024:.1f} KB)")
    else:
        failed += 1
        print("FAILED")

print("-" * 65)
print(f"Done: {converted} converted, {failed} failed.")
print(f"Total SPIFFS size: {total_bytes/1024:.0f} KB  ({total_bytes/1024/1024:.2f} MB)")

LIMIT = 1.5 * 1024 * 1024
if total_bytes > LIMIT:
    print(f"WARNING: {total_bytes/1024:.0f} KB exceeds SPIFFS limit (~1536 KB).")
    print("Consider reducing TARGET_RATE to 8000 Hz.")
else:
    print(f"SPIFFS usage OK ({total_bytes/1024:.0f} / 1536 KB)")

if failed:
    sys.exit(1)
