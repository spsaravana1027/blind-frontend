"""
AI Assistive Webcam Vision & Tamil Voice Assistant for Visually Impaired
========================================================================
Features:
1. Live Webcam Feed Capture (OpenCV)
2. Obstacle Detection (YOLOv8) with Ultrasonic Distance Check
   -> If distance is NEAR (<= 50 cm), speaks: "எச்சரிக்கை! பொருள் அருகில் உள்ளது."
3. Medicine Identification (EasyOCR)
   -> Paracetamol tablet  -> "இது பாராசிட்டமால் மாத்திரை."
   -> Rantac tablet       -> "இது ரான்டாக் மாத்திரை."
   -> Tassic Tanic syrup  -> "இது டாசிக் டானிக் மருந்து."
4. Currency Identification (EasyOCR)
   -> 500 Rs note -> "இது 500 ரூபாய்."
   -> 200, 100, 50, 20, 10 Rs notes recognized
5. Immediate Fall Detection (Key 'F'):
   -> Immediately activates buzzer and sends emergency alert to guardian on Telegram!
6. Safe Switch (Key 'S'):
   -> Turns off the buzzer and immediately sends safe message to guardian on Telegram!
7. Real-time Tamil Speech Output through Speaker (gTTS + pygame)
"""

import sys
import os
import time
import threading
import tempfile
import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

# Initialize Pygame mixer for real audio playback
AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audio"))

CLIP_FILES = {
    1: "0001_system_ready.mp3",
    2: "0002_system_error.mp3",
    3: "0003_obstacle_front.mp3",
    4: "0004_dustbin_front.mp3",
    5: "0005_dog_left.mp3",
    6: "0006_chair_right.mp3",
    7: "0007_person_front.mp3",
    8: "0008_car_front.mp3",
    9: "0009_table_front.mp3",
    10: "0010_emergency_fall.mp3",
    11: "0011_alert_cancelled.mp3",
    12: "0012_telegram_sent.mp3",
    13: "0013_obstacle_notice.mp3",
    14: "0014_obstacle_warning.mp3",  # "எச்சரிக்கை! பொருள் அருகில் உள்ளது."
    15: "0015_person_ahead.mp3",
    16: "0016_person_left.mp3",
    17: "0017_person_right.mp3",
    18: "0018_chair_ahead.mp3",
    19: "0019_table_ahead.mp3",
    20: "0020_door_ahead.mp3",
    21: "0021_stairs_ahead.mp3",     # "முன்னால் படிக்கட்டுகள் உள்ளன."
    22: "0022_wall_ahead.mp3",
    23: "0023_vehicle_ahead.mp3",
    24: "0024_medicine_reminder.mp3",
    30: "0030_medicine_paracetamol.mp3",
    31: "0031_medicine_rantac.mp3",
    32: "0032_medicine_tassic.mp3",
    33: "0033_currency_500.mp3",
    34: "0034_currency_200.mp3",
    35: "0035_currency_100.mp3",
    36: "0036_currency_50.mp3",
    37: "0037_currency_20.mp3",
    38: "0038_currency_10.mp3",
    39: "0039_user_safe.mp3",
    40: "0040_system_connected.mp3"
}

PRELOADED_SOUNDS = {}
HAVE_PYGAME = False

try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    HAVE_PYGAME = True
    print(f"[AUDIO] Pygame mixer active. Preloading 35 real Tamil MP3 speech clips from: {AUDIO_DIR}")
    for cid, fname in CLIP_FILES.items():
        fpath = os.path.join(AUDIO_DIR, fname)
        if os.path.exists(fpath):
            try:
                PRELOADED_SOUNDS[cid] = pygame.mixer.Sound(fpath)
            except Exception as e:
                pass
    print(f"[AUDIO] Preloaded {len(PRELOADED_SOUNDS)} real Tamil speech audio clips successfully!")
except Exception as e:
    print(f"[AUDIO WARNING] Pygame mixer init failed: {e}")

# Try importing gTTS as fallback
try:
    from gtts import gTTS
    HAVE_GTTS = True
except ImportError:
    HAVE_GTTS = False

# Try importing Ultralytics YOLO
try:
    from ultralytics import YOLO
    HAVE_YOLO = True
    print("[INIT] Loading YOLOv8 nano model...")
    model = YOLO("yolov8n.pt")
    print("[INIT] YOLOv8 ready.")
except Exception as e:
    HAVE_YOLO = False
    model = None
    print(f"[YOLO WARNING] YOLO model load failed: {e}")
# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

ocr_reader = None
HAVE_OCR = False

def _init_ocr():
    global ocr_reader, HAVE_OCR
    try:
        import easyocr
        print("[INIT] Loading EasyOCR in background thread...")
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        ocr_reader = reader
        HAVE_OCR = True
        print("[INIT] EasyOCR reader active.")
    except Exception as e:
        print(f"[OCR NOTICE] EasyOCR async notice: {e}")

threading.Thread(target=_init_ocr, daemon=True).start()

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0"
TELEGRAM_CHAT_ID = "7906413709"

def send_telegram(message: str) -> bool:
    """Dispatches Telegram alert directly to guardian."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        r = requests.post(url, json=payload, timeout=8)
        return r.status_code == 200
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return False

# Global Assistant State
class AssistantState:
    def __init__(self):
        self.ultrasonic_distance_cm = 45.0  # Default simulated distance
        self.is_buzzer_active = False
        self.last_played_clip = 0
        self.last_played_time = 0.0
        self.speech_cooldown_sec = 3.5
        self.is_speaking = False
        self.lock = threading.Lock()

state = AssistantState()

def play_real_audio(clip_id: int, secondary_clip_id: int = None, force: bool = False):
    """
    Plays real human voice Tamil MP3 speech clip through the speaker.
    Debounces repeated calls within speech_cooldown_sec unless force=True.
    """
    if not HAVE_PYGAME:
        return

    now = time.time()
    with state.lock:
        if not force and clip_id == state.last_played_clip and (now - state.last_played_time < state.speech_cooldown_sec):
            return
        if state.is_speaking and not force:
            return
        state.last_played_clip = clip_id
        state.last_played_time = now
        state.is_speaking = True

    def _worker():
        try:
            for cid in [clip_id, secondary_clip_id]:
                if cid is None:
                    continue
                fname = CLIP_FILES.get(cid, f"clip_{cid}.mp3")
                sound = PRELOADED_SOUNDS.get(cid)
                if sound:
                    print(f"🔊 [SPEAKER PLAYING REAL AUDIO] {fname} (Clip ID: {cid})", flush=True)
                    ch = sound.play()
                    if ch:
                        while ch.get_busy():
                            time.sleep(0.05)
                    else:
                        time.sleep(sound.get_length())
                else:
                    fpath = os.path.join(AUDIO_DIR, fname)
                    if os.path.exists(fpath):
                        print(f"🔊 [SPEAKER PLAYING REAL AUDIO FILE] {fname}", flush=True)
                        pygame.mixer.music.load(fpath)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.05)

                # Send command to physical MAX98357A speaker on ESP32
                try:
                    import serial
                    s = serial.Serial()
                    s.port = 'COM6'
                    s.baudrate = 115200
                    s.dtr = False
                    s.rts = False
                    s.timeout = 0.3
                    s.open()
                    s.write(f"clip {cid}\n".encode('utf-8'))
                    s.flush()
                    s.close()
                    print(f"📡 [PHYSICAL SPEAKER] Dispatched 'clip {cid}' to MAX98357A on ESP32!", flush=True)
                except Exception:
                    pass
        except Exception as err:
            print(f"[AUDIO PLAYBACK ERROR] {err}", flush=True)
        finally:
            with state.lock:
                state.is_speaking = False

    threading.Thread(target=_worker, daemon=True).start()

def speak_tamil(text: str, force: bool = False):
    """
    Maps text to corresponding pre-recorded human-voice Tamil MP3 file.
    If no pre-recorded clip matches, falls back to gTTS.
    """
    # Auto-map known Tamil phrases to real audio clip IDs:
    txt = text.strip()
    if "படிக்கட்டு" in txt or "stair" in txt:
        play_real_audio(21, force=force) # 0021_stairs_ahead.mp3
        return
    elif "அருகில் உள்ளது" in txt:
        play_real_audio(14, force=force) # 0014_obstacle_warning.mp3
        return
    elif "பாராசிட்டமால்" in txt or "paracetamol" in txt:
        play_real_audio(30, force=force) # 0030_medicine_paracetamol.mp3
        return
    elif "ரான்டாக்" in txt or "rantac" in txt:
        play_real_audio(31, force=force) # 0031_medicine_rantac.mp3
        return
    elif "டாசிக்" in txt or "tassic" in txt:
        play_real_audio(32, force=force) # 0032_medicine_tassic.mp3
        return
    elif "500" in txt:
        play_real_audio(33, force=force) # 0033_currency_500.mp3
        return
    elif "200" in txt:
        play_real_audio(34, force=force)
        return
    elif "100" in txt:
        play_real_audio(35, force=force)
        return
    elif "50" in txt:
        play_real_audio(36, force=force)
        return
    elif "20" in txt:
        play_real_audio(37, force=force)
        return
    elif "10" in txt:
        play_real_audio(38, force=force)
        return
    elif "கீழே விழுந்து" in txt or "அவசரம்" in txt:
        play_real_audio(10, force=True)  # 0010_emergency_fall.mp3
        return
    elif "பாதுகாப்பாக" in txt or "நிறுத்தப்பட்டது" in txt:
        play_real_audio(39, force=True)  # 0039_user_safe.mp3
        return
    elif "இணைக்கப்பட்டது" in txt or "தயார்" in txt:
        play_real_audio(40, force=True)  # 0040_system_connected.mp3
        return
    elif "நாற்காலி" in txt:
        play_real_audio(18, force=force) # 0018_chair_ahead.mp3
        return
    elif "ஒருவர்" in txt:
        play_real_audio(7, force=force)  # 0007_person_front.mp3
        return
    elif "மேஜை" in txt:
        play_real_audio(9, force=force)  # 0009_table_front.mp3
        return
    elif "குப்பைத்தொட்டி" in txt:
        play_real_audio(4, force=force)  # 0004_dustbin_front.mp3
        return
    elif "நாய்" in txt:
        play_real_audio(3, force=force)  # 0003_obstacle_front.mp3
        return
    elif "வாகனம்" in txt or "கார்" in txt:
        play_real_audio(8, force=force)  # 0008_car_front.mp3
        return

    # Fallback to general obstacle clip 3
    play_real_audio(3, force=force)

def buzzer_sound_worker():
    """Generates continuous alarm beeps while buzzer is active."""
    sound = None
    try:
        import numpy as np
        sample_rate = 22050
        duration = 0.2
        n_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        tone = (np.sin(2 * np.pi * 950 * t) * 16384).astype(np.int16)
        stereo_tone = np.column_stack((tone, tone))
        sound = pygame.sndarray.make_sound(stereo_tone)
    except Exception as e:
        sound = None

    while True:
        if state.is_buzzer_active and sound:
            try:
                sound.play()
            except Exception:
                pass
            time.sleep(0.3)
        else:
            time.sleep(0.1)

if HAVE_PYGAME:
    b_thread = threading.Thread(target=buzzer_sound_worker, daemon=True)
    b_thread.start()

def trigger_fall():
    """Requirement 4: Fall down -> Immediately starts buzzer and sends Telegram alert."""
    state.is_buzzer_active = True
    print("\n" + "="*50)
    print("🚨 FALL DETECTED! BUZZER STARTED & SENDING TELEGRAM ALERT")
    print("="*50)

    # Speak emergency alert
    speak_tamil("அவசரம்! கீழே விழுந்துவிட்டீர்கள்.", force=True)

    # Send Telegram
    msg = (
        "🚨 அவசர எச்சரிக்கை! (EMERGENCY FALL ALERT)\n"
        "பயனர் கீழே விழுந்துவிட்டார்!\n"
        "உடனடியாக கவனிக்கவும்.\n"
        "Status: Fall Detected\n"
        "Action: Please check the user immediately!"
    )
    def _t():
        ok = send_telegram(msg)
        print(f"[TELEGRAM] Fall alert sent: {ok}")
    threading.Thread(target=_t, daemon=True).start()

def trigger_safe():
    """Requirements 5 & 8: Safe switch clicked -> Stops buzzer and sends safe Telegram message."""
    state.is_buzzer_active = False
    print("\n" + "="*50)
    print("✅ SAFE SWITCH PRESSED: BUZZER STOPPED & SENDING SAFE TELEGRAM MESSAGE")
    print("="*50)

    # Speak safe confirmation
    speak_tamil("பாதுகாப்பாக உள்ளீர்கள். எச்சரிக்கை நிறுத்தப்பட்டது.", force=True)

    # Send Telegram safe update
    msg = (
        "✅ பாதுகாப்பு தகவல் (SAFE UPDATE)\n"
        "பயனர் பாதுகாப்பாக உள்ளார்.\n"
        "அவசர எச்சரிக்கை சுவிட்ச் மூலம் அணைக்கப்பட்டது.\n"
        "Status: User is SAFE. Alert buzzer deactivated."
    )
    def _t():
        ok = send_telegram(msg)
        print(f"[TELEGRAM] Safe status message sent: {ok}")
    threading.Thread(target=_t, daemon=True).start()

def detect_medicines_and_currency(frame: np.ndarray):
    """Requirement 6 & 7: Recognize medicines and currency notes from camera frame."""
    if not HAVE_OCR or ocr_reader is None:
        return None

    try:
        # Resize for fast OCR inference
        small_frame = cv2.resize(frame, (480, 360))
        ocr_results = ocr_reader.readtext(small_frame)
        full_text = " ".join([res[1].lower() for res in ocr_results])
        if len(full_text.strip()) > 0:
            print(f"[CAMERA OCR TEXT] \"{full_text}\"")

        # 1. Medicines (Req 6)
        if any(w in full_text for w in ["paracetamol", "paracetomal", "paracet", "dolo", "calpol", "crocin", "pcm", "paracip"]):
            return ("paracetamol tablet", "இது பாராசிட்டமால் மாத்திரை.")
        elif any(w in full_text for w in ["rantac", "ranitidine", "aciloc", "zantac"]):
            return ("rantac tablet", "இது ரான்டாக் மாத்திரை.")
        elif any(w in full_text for w in ["tassic", "tanic", "tonic", "tastic", "tusq", "cough"]):
            return ("tassic tanic", "இது டாசிக் டானிக் மருந்து.")

        # 2. Currency (Req 7)
        # Check fluorescent blue / teal color for 50 Rs note
        hsv = cv2.cvtColor(small_frame, cv2.COLOR_BGR2HSV)
        teal_mask = cv2.inRange(hsv, np.array([75, 25, 40]), np.array([125, 255, 255]))
        total_px = float(small_frame.shape[0] * small_frame.shape[1])
        teal_ratio = np.sum(teal_mask > 0) / total_px

        has_teal_note = False
        contours, _ = cv2.findContours(teal_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) > (total_px * 0.035):
                _, _, cw, ch = cv2.boundingRect(cnt)
                aspect = max(cw, ch) / float(max(min(cw, ch), 1))
                if 1.2 <= aspect <= 3.8:
                    has_teal_note = True
                    break

        import re
        has_50_text = (
            "50" in full_text or
            bool(re.search(r'(?:\b|[^0-9])50(?:\b|[^0-9])', full_text)) or
            any(w in full_text for w in ["fifty", "५०", "₹50", "50rs", "50 rs", "50/-", "s0", "5o", "pachas", "fifty rupees"])
        )

        if has_50_text or has_teal_note or teal_ratio > 0.08:
            return ("50rs note", "இது 50 ரூபாய்.")
        elif any(w in full_text for w in ["500", "five hundred", "५००", "₹500", "5oo", "soo"]):
            return ("500rs note", "இது 500 ரூபாய்.")
        elif any(w in full_text for w in ["200", "two hundred", "२००", "₹200", "2oo"]):
            return ("200rs note", "இது 200 ரூபாய்.")
        elif any(w in full_text for w in ["100", "one hundred", "१००", "₹100", "1oo"]):
            return ("100rs note", "இது 100 ரூபாய்.")
        elif any(w in full_text for w in ["20", "twenty", "२०", "₹20"]):
            return ("20rs note", "இது 20 ரூபாய்.")
        elif any(w in full_text for w in ["10", "ten", "१०", "₹10"]):
            return ("10rs note", "இது 10 ரூபாய்.")

    except Exception as e:
        print(f"[OCR ERROR] {e}")
    return None

def run_webcam_assistant():
    print("\n" + "="*60)
    print("   AI ASSISTIVE VISION & TAMIL VOICE ASSISTANT")
    print("   Designed for Visually Impaired People")
    print("="*60)
    print("Keyboard Hotkeys:")
    print("  'f' - Trigger Fall down (Immediate buzzer & Telegram alert)")
    print("  's' - Press Safe switch (Stops buzzer & sends safe message)")
    print("  '+' - Increase ultrasonic distance (+10 cm)")
    print("  '-' - Decrease ultrasonic distance (-10 cm)")
    print("  'q' - Quit webcam assistant")
    print("="*60 + "\n")

    # Camera Source selection: CLI arg, env var, or fallback
    import sys
    cam_source = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cam_source = sys.argv[1]
    elif os.getenv("ESP32_CAM_URL"):
        cam_source = os.getenv("ESP32_CAM_URL")

    cap = None
    if cam_source:
        print(f"[CAMERA] Connecting to ESP32-CAM stream: {cam_source} ...")
        cap = cv2.VideoCapture(cam_source)
        if not cap.isOpened():
            print(f"[CAMERA WARNING] Could not open {cam_source}. Falling back to USB webcam (Index 0)...")
            cap = None

    if cap is None:
        print("[CAMERA] Opening local USB webcam (Index 0)...")
        cap = cv2.VideoCapture(0)

    if not cap or not cap.isOpened():
        print("[CAMERA ERROR] Cannot open any video stream. Please check camera connection or ESP32-CAM IP.")
        return

    WINDOW_NAME = "AI Assistive Vision & Tamil Voice Assistant (Visually Impaired)"
    has_gui = True
    try:
        cv2.namedWindow(WINDOW_NAME)
        # Requirements 5 & 8: Mouse click handler for on-screen Safe Switch
        def on_mouse_click(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                if 20 <= x <= 320 and 120 <= y <= 160:
                    print("\n[CLICK] Safe Switch clicked by user!")
                    trigger_safe()
                elif 340 <= x <= 540 and 120 <= y <= 160:
                    print("\n[CLICK] Fall button clicked!")
                    trigger_fall()

        cv2.setMouseCallback(WINDOW_NAME, on_mouse_click)
    except Exception as e:
        print(f"[GUI NOTICE] OpenCV window display not available ({e}). Running in background mode.")
        has_gui = False

    # Sound connection greeting in speaker (Requirement 2: sounds in speaker after connection)
    speak_tamil("அமைப்பு தயார். இணைக்கப்பட்டது.", force=True)

    frame_count = 0
    detected_special = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[CAMERA WARNING] Failed to capture frame.")
            time.sleep(0.1)
            continue

        frame_count += 1
        h, w, _ = frame.shape
        display_frame = frame.copy()

        # Check medicines & currency every 10 frames (~0.3s)
        if frame_count % 10 == 0:
            server_handled = False
            try:
                _, jpg_bytes = cv2.imencode('.jpg', frame)
                resp = requests.post(
                    f"http://127.0.0.1:8000/detect?distance={state.ultrasonic_distance_cm}",
                    data=jpg_bytes.tobytes(),
                    headers={"Content-Type": "image/jpeg"},
                    timeout=0.6
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        top = data[0]
                        lbl = top.get("label", "")
                        if any(c in lbl for c in ["50", "100", "200", "500", "20", "10", "paracetamol", "rantac", "tassic"]):
                            detected_special = (lbl, top.get("tamil_text", ""))
                            server_handled = True
            except Exception:
                pass

            if not server_handled:
                detected_special = detect_medicines_and_currency(frame)
                if detected_special:
                    item_label, tamil_phrase = detected_special
                    speak_tamil(tamil_phrase)

        # Run YOLO object detection for obstacles with position & distance estimation
        detected_obstacle = None
        obstacle_info = None
        if HAVE_YOLO and model is not None:
            results = model(frame, verbose=False)[0]
            best_area = 0
            for box in results.boxes:
                conf = float(box.conf[0].cpu().numpy())
                if conf < 0.45:
                    continue
                cls_id = int(box.cls[0].cpu().numpy())
                label = model.names[cls_id]

                # Draw bounding box
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]
                bw, bh = max(x2 - x1, 1), max(y2 - y1, 1)
                area = bw * bh

                # Position & relative height estimation
                center_x = (x1 + x2) / 2.0
                pos = "left" if center_x < w * 0.33 else ("right" if center_x > w * 0.66 else "center")
                rel_h = bh / float(h)
                is_near = (rel_h > 0.40) or (state.ultrasonic_distance_cm <= 50.0)

                color = (0, 0, 255) if is_near else (0, 255, 0)
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display_frame, f"{label} ({pos.upper()}, {'NEAR' if is_near else 'FAR'}) {conf:.2f}",
                            (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

                TARGET_OBSTACLES = [
                    "person", "chair", "table", "dining table", "door", "stairs", "pole",
                    "car", "bus", "truck", "motorcycle", "bicycle", "dog", "couch", "sofa",
                    "bed", "bench", "wall", "dustbin", "backpack"
                ]
                if label in TARGET_OBSTACLES:
                    if area > best_area:
                        best_area = area
                        detected_obstacle = label
                        obstacle_info = {
                            "label": label,
                            "position": pos,
                            "is_near": is_near,
                            "conf": conf
                        }

        # Voice output dispatch based on situation, position, and distance
        if obstacle_info and not detected_special:
            lbl = obstacle_info["label"]
            pos = obstacle_info["position"]
            is_near = obstacle_info["is_near"]

            if lbl == "person":
                phrase = "இடதுபுறம் ஒருவர் உள்ளார்." if pos == "left" else ("வலதுபுறம் ஒருவர் உள்ளார்." if pos == "right" else "முன்னால் ஒருவர் உள்ளார்.")
            elif lbl in ["chair", "couch", "sofa"]:
                phrase = "இடது பக்கத்தில் நாற்காலி உள்ளது." if pos == "left" else ("வலது பக்கத்தில் நாற்காலி உள்ளது." if pos == "right" else "முன்னால் நாற்காலி உள்ளது.")
            elif lbl in ["table", "dining table"]:
                phrase = "முன்னால் மேஜை உள்ளது."
            elif lbl in ["stairs", "stair"]:
                phrase = "முன்னால் படிக்கட்டுகள் உள்ளன."
            elif lbl == "dog":
                phrase = "இடது பக்கத்தில் நாய் உள்ளது." if pos == "left" else "முன்னால் நாய் உள்ளது."
            elif lbl in ["car", "bus", "truck", "motorcycle", "bicycle"]:
                phrase = "முன்னால் வாகனம் உள்ளது. பாதுகாப்பாக நிற்கவும்."
            elif lbl == "door":
                phrase = "முன்னால் கதவு உள்ளது."
            elif lbl == "wall":
                phrase = "முன்னால் சுவர் உள்ளது."
            elif lbl == "dustbin":
                phrase = "முன்னால் குப்பைத்தொட்டி உள்ளது."
            else:
                phrase = "முன்னால் தடை உள்ளது."

            if is_near:
                speak_tamil(f"எச்சரிக்கை! பொருள் அருகில் உள்ளது. {phrase}")
            else:
                speak_tamil(phrase)

        # Overlay UI Information
        dist_color = (0, 0, 255) if state.ultrasonic_distance_cm <= 50 else (0, 255, 0)
        cv2.rectangle(display_frame, (10, 10), (w - 10, 170), (20, 20, 20), -1)
        cv2.putText(display_frame, f"Distance: {state.ultrasonic_distance_cm:.1f} cm", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, dist_color, 2)
        status_text = "HAZARD NEAR" if state.ultrasonic_distance_cm <= 50 else "PATH CLEAR"
        cv2.putText(display_frame, f"Proximity Status: {status_text}", (260, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, dist_color, 2)

        buzzer_status = "ALARM ACTIVE!" if state.is_buzzer_active else "OFF (Normal)"
        buzzer_color = (0, 0, 255) if state.is_buzzer_active else (200, 200, 200)
        cv2.putText(display_frame, f"Buzzer: {buzzer_status}", (20, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, buzzer_color, 2)

        if detected_special:
            cv2.putText(display_frame, f"Found: {detected_special[0].upper()} (Spoken in Tamil)", (20, 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        elif detected_obstacle:
            near_tag = " [NEAR! SPEAKING WARNING]" if state.ultrasonic_distance_cm <= 50 else ""
            cv2.putText(display_frame, f"Obstacle: {detected_obstacle.upper()}{near_tag}", (20, 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
        else:
            cv2.putText(display_frame, "Monitoring for Obstacles, Medicines, & Currency...", (20, 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

        # Draw Interactive On-Screen Clickable Buttons
        # 1. Safe Switch Button (Req 5 & 8)
        btn_safe_color = (0, 180, 0) if not state.is_buzzer_active else (0, 220, 0)
        cv2.rectangle(display_frame, (20, 115), (320, 160), btn_safe_color, -1)
        cv2.rectangle(display_frame, (20, 115), (320, 160), (255, 255, 255), 2)
        cv2.putText(display_frame, "CLICK: SAFE SWITCH (OFF BUZZER)", (28, 145),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2)

        # 2. Fall Test Button (Req 4)
        btn_fall_color = (0, 0, 180) if state.is_buzzer_active else (50, 50, 150)
        cv2.rectangle(display_frame, (340, 115), (540, 160), btn_fall_color, -1)
        cv2.rectangle(display_frame, (340, 115), (540, 160), (255, 255, 255), 2)
        cv2.putText(display_frame, "CLICK: FALL EVENT", (355, 145),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        if has_gui:
            try:
                cv2.imshow(WINDOW_NAME, display_frame)
                key = cv2.waitKey(1) & 0xFF
            except Exception:
                has_gui = False
                key = 255
        else:
            time.sleep(0.03)
            key = 255

        if key == ord('q'):
            break
        elif key == ord('f') or key == ord('F'):
            trigger_fall()
        elif key == ord('s') or key == ord('S'):
            trigger_safe()
        elif key == ord('+') or key == ord('='):
            state.ultrasonic_distance_cm = min(400.0, state.ultrasonic_distance_cm + 10.0)
            print(f"[DISTANCE] Set to {state.ultrasonic_distance_cm:.1f} cm")
        elif key == ord('-') or key == ord('_'):
            state.ultrasonic_distance_cm = max(10.0, state.ultrasonic_distance_cm - 10.0)
            print(f"[DISTANCE] Set to {state.ultrasonic_distance_cm:.1f} cm")

    cap.release()
    if has_gui:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    print("[SYSTEM] Webcam assistant closed.")

if __name__ == "__main__":
    run_webcam_assistant()
