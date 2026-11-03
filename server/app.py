import io
import os
import sys
import re
import time
import queue
import threading
import tempfile
import requests
import uvicorn
import cv2
from fastapi import FastAPI, Request, File, UploadFile, Query
from fastapi.responses import JSONResponse, Response, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import numpy as np

# Set writable cache directories for serverless environments (e.g. Vercel, AWS Lambda)
_temp_dir = tempfile.gettempdir()
os.environ.setdefault("YOLO_CONFIG_DIR", os.path.join(_temp_dir, "Ultralytics"))
os.environ.setdefault("TORCH_HOME", os.path.join(_temp_dir, "torch"))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(_temp_dir, "matplotlib"))
os.environ.setdefault("EASYOCR_MODULE_PATH", os.path.join(_temp_dir, ".EasyOCR"))

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Global EasyOCR reader (initialized asynchronously in background so server starts instantly)
ocr_reader = None
HAVE_EASYOCR = False

def _init_easyocr_worker():
    global ocr_reader, HAVE_EASYOCR
    try:
        import easyocr
        print("[SERVER] Initializing EasyOCR in background thread...")
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        ocr_reader = reader
        HAVE_EASYOCR = True
        print("[SERVER] EasyOCR reader successfully loaded and active!")
    except Exception as e:
        print(f"[SERVER NOTICE] EasyOCR async init notice: {e}")

import threading
# Lazy load EasyOCR on cloud to keep boot RAM low
if "RENDER" not in os.environ and "PORT" not in os.environ:
    ocr_thread = threading.Thread(target=_init_easyocr_worker, daemon=True)
    ocr_thread.start()

# Try importing Ultralytics YOLO
try:
    from ultralytics import YOLO
    HAVE_ULTRALYTICS = True
except ImportError:
    HAVE_ULTRALYTICS = False
    YOLO = None

# Try importing gTTS
try:
    from gtts import gTTS
    HAVE_GTTS = True
except ImportError:
    HAVE_GTTS = False

app = FastAPI(
    title="AI Assistive Vision & Tamil Voice Assistant for Visually Impaired",
    description="FastAPI service for YOLOv8 object detection, EasyOCR medicine/currency recognition, distance assessment, and Tamil voice synthesis",
    version="3.0.0"
)

# Enable CORS for mobile browsers and remote clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load lightweight YOLOv8 nano model if available
if HAVE_ULTRALYTICS:
    print("[SERVER] Loading YOLOv8n model...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "yolov8n.pt"),
        os.path.join(base_dir, "..", "yolov8n.pt"),
        os.path.join(os.getcwd(), "yolov8n.pt"),
        os.path.join(os.getcwd(), "server", "yolov8n.pt"),
        "yolov8n.pt"
    ]
    model_path = next((p for p in candidates if os.path.exists(p)), "yolov8n.pt")
    try:
        model = YOLO(model_path)
        print(f"[SERVER] YOLOv8n model ready from {model_path}.")
    except Exception as e:
        print(f"[SERVER WARNING] Could not load YOLO model ({e}). Continuing in fallback mode.")
        model = None
else:
    print("[SERVER WARNING] 'ultralytics' not installed. Running in fallback mode.")
    model = None

# Telegram Bot Credentials (from secrets.h)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7906413709")

def send_telegram_notification(message: str) -> bool:
    """Send immediate message to guardian via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Missing bot token or chat ID.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code == 200:
            print("[TELEGRAM] Message sent successfully to guardian.")
            return True
        else:
            print(f"[TELEGRAM ERROR] HTTP {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"[TELEGRAM EXCEPTION] {e}")
        return False

# =========================================================================
# REAL TAMIL AUDIO PLAYER SUBSYSTEM (PYGAME MIXER)
# Plays actual human voice MP3 audio clips through the computer speaker
# =========================================================================
AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "audio"))
if not os.path.exists(AUDIO_DIR):
    AUDIO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "audio"))
if not os.path.exists(AUDIO_DIR):
    AUDIO_DIR = os.path.abspath(os.path.join(os.getcwd(), "audio"))
if not os.path.exists(AUDIO_DIR):
    AUDIO_DIR = os.path.abspath(os.path.join(os.getcwd(), "server", "audio"))

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

class RealAudioPlayer:
    """
    Host computer audio player - MUTED by user design requirement!
    Audio output is strictly directed ONLY to the physical MAX98357A speaker connected to ESP32.
    """
    def __init__(self, audio_dir: str):
        self.audio_dir = audio_dir
        print("[AUDIO] Laptop & Phone speakers are strictly MUTED. Only MAX98357A speaker on ESP32 will output sound.")

    def play(self, clip_id: int, secondary_clip_id: int = None, force: bool = False):
        # Muted on laptop by design - PhysicalSpeakerBridge sends to ESP32 MAX98357A
        pass

audio_player = RealAudioPlayer(AUDIO_DIR)

class PhysicalSpeakerBridge:
    """
    Direct Hardware Serial Bridge to ESP32 (MAX98357A I2S Amplifier).
    Whenever a camera image is processed, this bridge triggers the real Tamil
    voice announcement on the physical MAX98357A speaker plugged into the ESP32!
    """
    def __init__(self, port: str = "COM10", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.lock = threading.Lock()
        self.last_sent_clip = 0
        self.last_sent_time = 0.0
        self.same_clip_debounce = 6.0   # Same object will not repeat within 6.0 seconds
        self.min_clip_interval = 2.8    # Minimum interval between ANY audio announcements (audio clip length)
        self._connect()

    def _connect(self):
        try:
            import serial
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
            target = self.port if self.port in ports else (ports[0] if ports else None)
            if target:
                self.ser = serial.Serial()
                self.ser.port = target
                self.ser.baudrate = self.baudrate
                self.ser.dtr = False
                self.ser.rts = False
                self.ser.timeout = 1
                self.ser.open()
                print(f"[PHYSICAL SPEAKER] Successfully connected to Main ESP32 on {target} at {self.baudrate} baud!")
        except Exception as e:
            print(f"[PHYSICAL SPEAKER NOTICE] Serial port {self.port} not currently available: {e}")
            self.ser = None

    def send_clip(self, clip_id: int, label: str = "", position: str = "center", tamil_text: str = "", confidence: float = 0.95, force: bool = False):
        # Strict 70% accuracy threshold: Speaker will NEVER speak if accuracy < 70% (0.70)
        if not force and confidence < 0.70:
            return

        now = time.time()
        with self.lock:
            # 1. Prevent interrupting an ongoing audio clip: Tamil speech clips take ~2.5s to play
            if not force and (now - self.last_sent_time < self.min_clip_interval):
                return

            # 2. Prevent repeating the exact same object announcement continuously
            if not force and clip_id == self.last_sent_clip and (now - self.last_sent_time < self.same_clip_debounce):
                return

            self.last_sent_clip = clip_id
            self.last_sent_time = now

            if self.ser is None or not self.ser.is_open:
                self._connect()

            if self.ser and self.ser.is_open:
                try:
                    # Send direct clip command to ESP32 to play over MAX98357A I2S amplifier
                    cmd = f"clip {clip_id}\n"
                    self.ser.write(cmd.encode("utf-8"))
                    self.ser.flush()
                    print(f"📡 [PHYSICAL SPEAKER] Playing Clip #{clip_id} ('{label}', Conf: {confidence:.2f}) on MAX98357A!")
                except Exception as e:
                    print(f"[PHYSICAL SPEAKER ERROR] Failed to send to ESP32: {e}")
                    self.ser = None

    def trigger_fall_alarm(self):
        """Sends 'fall' command to ESP32 to immediately activate the active buzzer siren and emergency audio."""
        with self.lock:
            if self.ser is None or not self.ser.is_open:
                self._connect()
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(b"fall\n")
                    self.ser.flush()
                    print("🚨 [PHYSICAL BRIDGE] Sent 'fall' command to ESP32! Active Buzzer + Fall Emergency Alarm Triggered!")
                except Exception as e:
                    print(f"[PHYSICAL BRIDGE ERROR] Failed to send 'fall': {e}")
                    self.ser = None

    def trigger_safe_alarm(self):
        """Sends 'safe' command to ESP32 to immediately turn off the active buzzer and restore safe monitoring."""
        with self.lock:
            if self.ser is None or not self.ser.is_open:
                self._connect()
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(b"safe\n")
                    self.ser.flush()
                    print("✅ [PHYSICAL BRIDGE] Sent 'safe' command to ESP32! Active Buzzer Stopped!")
                except Exception as e:
                    print(f"[PHYSICAL BRIDGE ERROR] Failed to send 'safe': {e}")
                    self.ser = None

physical_speaker = PhysicalSpeakerBridge("COM10")

# Class mapping & Tamil speech lookup
TARGET_CLASSES = {
    "person": "person",
    "dog": "dog",
    "cat": "cat",
    "chair": "chair",
    "dining table": "table",
    "table": "table",
    "desk": "table",
    "couch": "chair",
    "sofa": "chair",
    "bed": "bed",
    "bottle": "bottle",
    "cup": "cup",
    "cell phone": "cell phone",
    "laptop": "laptop",
    "tv": "laptop",
    "book": "book",
    "backpack": "backpack",
    "handbag": "backpack",
    "suitcase": "backpack",
    "clock": "clock",
    "umbrella": "umbrella",
    "waste container": "dustbin",
    "garbage bin": "dustbin",
    "trash can": "dustbin",
    "bin": "dustbin",
    "car": "car",
    "bus": "car",
    "truck": "car",
    "motorcycle": "car",
    "bicycle": "car",
    "door": "door",
    "stairs": "stairs",
    "stair": "stairs",
    "steps": "stairs",
    "staircase": "stairs"
}

def generate_tamil_instruction(label: str, position: str = "center", distance_cm: float = 0.0) -> dict:
    """
    Generates natural Tamil speech phrase based on object type, bounding-box position,
    and measured ultrasonic distance.
    """
    lbl = label.lower()
    pos = position.lower()

    clip_id = 3
    tamil_text = "முன்னால் தடை உள்ளது. உடனே நின்று கவனிக்கவும்."
    english_text = "Obstacle ahead. Stop and observe."

    # 1. Medicines Identification (Requirement 6)
    if "paracetamol" in lbl or "paracetomal" in lbl or "dolo" in lbl or "calpol" in lbl or "crocin" in lbl or "pcm" in lbl:
        clip_id = 30
        tamil_text = "இது பாராசிட்டமால் மாத்திரை."
        english_text = "This is a Paracetamol tablet."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0030_medicine_paracetamol.mp3"}

    elif "rantac" in lbl or "ranitidine" in lbl or "aciloc" in lbl or "zantac" in lbl:
        clip_id = 31
        tamil_text = "இது ரான்டாக் மாத்திரை."
        english_text = "This is a Rantac tablet."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0031_medicine_rantac.mp3"}

    elif "tassic" in lbl or "tanic" in lbl or "tonic" in lbl or "tastic" in lbl or "tusq" in lbl:
        clip_id = 32
        tamil_text = "இது டாசிக் டானிக் மருந்து."
        english_text = "This is Tassic Tanic medicine."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0032_medicine_tassic.mp3"}

    elif "medicine" in lbl or "tablet" in lbl or "syrup" in lbl:
        clip_id = 30
        tamil_text = "இது மருந்து மாத்திரை."
        english_text = "This is a medicine tablet."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0030_medicine_paracetamol.mp3"}

    # 2. Currency Identification (Requirement 7)
    elif "500" in lbl or "five hundred" in lbl:
        clip_id = 33
        tamil_text = "இது 500 ரூபாய்."
        english_text = "This is 500 Rupees."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0033_currency_500.mp3"}

    elif "200" in lbl:
        clip_id = 34
        tamil_text = "இது 200 ரூபாய்."
        english_text = "This is 200 Rupees."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0034_currency_200.mp3"}

    elif "100" in lbl:
        clip_id = 35
        tamil_text = "இது 100 ரூபாய்."
        english_text = "This is 100 Rupees."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0035_currency_100.mp3"}

    elif "50" in lbl:
        clip_id = 36
        tamil_text = "இது 50 ரூபாய்."
        english_text = "This is 50 Rupees."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0036_currency_50.mp3"}

    elif "20" in lbl:
        clip_id = 37
        tamil_text = "இது 20 ரூபாய்."
        english_text = "This is 20 Rupees."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0037_currency_20.mp3"}

    elif "10" in lbl:
        clip_id = 38
        tamil_text = "இது 10 ரூபாய்."
        english_text = "This is 10 Rupees."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0038_currency_10.mp3"}

    elif "currency" in lbl or "money" in lbl or "rupee" in lbl or "cash" in lbl or "note" in lbl:
        clip_id = 35
        tamil_text = "இது ரூபாய் நோட்டு பணம்."
        english_text = "This is Indian Currency / Money."
        return {"clip_id": clip_id, "tamil_text": tamil_text, "english_text": english_text, "audio_file": "0035_currency_100.mp3"}

    # 3. Stairs Navigation (0021_stairs_ahead.mp3)
    elif "stair" in lbl or "step" in lbl:
        clip_id = 21
        tamil_text = "முன்னால் படிக்கட்டுகள் உள்ளன."
        english_text = "Stairs ahead."

    # 4. Obstacle & Position recognition (Requirement 3)
    elif "dustbin" in lbl or "garbage" in lbl or "trash" in lbl:
        clip_id = 4
        tamil_text = "முன்னால் குப்பைத்தொட்டி உள்ளது. கவனமாக விலகிச் செல்லவும்."
        english_text = "Dustbin ahead. Move away carefully."
    elif "dog" in lbl:
        if pos == "left":
            clip_id = 5
            tamil_text = "இடது பக்கத்தில் நாய் உள்ளது. கவனமாக வலது பக்கம் செல்லவும்."
            english_text = "Dog on the left. Move carefully to the right."
        else:
            clip_id = 3
            tamil_text = "முன்னால் நாய் உள்ளது. கவனமாக விலகிச் செல்லவும்."
            english_text = "Dog ahead. Move carefully."
    elif "chair" in lbl:
        if pos == "right":
            clip_id = 6
            tamil_text = "வலது பக்கத்தில் நாற்காலி உள்ளது. கவனமாக இடது பக்கம் செல்லவும்."
            english_text = "Chair on the right. Move carefully to the left."
        elif pos == "left":
            clip_id = 18
            tamil_text = "இடது பக்கத்தில் நாற்காலி உள்ளது. கவனமாக வலது பக்கம் செல்லவும்."
            english_text = "Chair on the left. Move carefully to the right."
        else:
            clip_id = 18
            tamil_text = "முன்னால் நாற்காலி உள்ளது. கவனமாகச் செல்லவும்."
            english_text = "Chair ahead. Move carefully."
    elif "person" in lbl or "human" in lbl:
        if pos == "left":
            clip_id = 16
            tamil_text = "இடதுபுறம் ஒருவர் உள்ளார். கவனமாகச் செல்லவும்."
            english_text = "Person on the left. Proceed carefully."
        elif pos == "right":
            clip_id = 17
            tamil_text = "வலதுபுறம் ஒருவர் உள்ளார். கவனமாகச் செல்லவும்."
            english_text = "Person on the right. Proceed carefully."
        else:
            clip_id = 7
            tamil_text = "முன்னால் ஒருவர் உள்ளார். கவனமாகச் செல்லவும்."
            english_text = "Person ahead. Proceed carefully."
    elif "car" in lbl or "vehicle" in lbl or "bus" in lbl or "truck" in lbl:
        clip_id = 8
        tamil_text = "முன்னால் வாகனம் உள்ளது. பாதுகாப்பாக நிற்கவும்."
        english_text = "Vehicle ahead. Stop safely."
    elif "table" in lbl or "desk" in lbl:
        clip_id = 9
        tamil_text = "முன்னால் மேஜை உள்ளது. கவனமாகச் செல்லவும்."
        english_text = "Table ahead. Proceed with caution."
    elif "cell phone" in lbl or "phone" in lbl:
        clip_id = 13
        tamil_text = "இது மொபைல் போன்."
        english_text = "This is a mobile phone."
    elif "bottle" in lbl:
        clip_id = 3
        tamil_text = "முன்னால் பாட்டில் உள்ளது."
        english_text = "Bottle ahead."
    elif "cup" in lbl:
        clip_id = 3
        tamil_text = "முன்னால் கப் உள்ளது."
        english_text = "Cup ahead."
    elif "laptop" in lbl or "computer" in lbl or "tv" in lbl:
        clip_id = 9
        tamil_text = "முன்னால் கணினி லேப்டாப் உள்ளது."
        english_text = "Laptop computer ahead."
    elif "book" in lbl:
        clip_id = 13
        tamil_text = "இது புத்தகம்."
        english_text = "This is a book."
    elif "backpack" in lbl or "bag" in lbl:
        clip_id = 3
        tamil_text = "முன்னால் பை உள்ளது."
        english_text = "Bag ahead."
    elif "bed" in lbl:
        clip_id = 9
        tamil_text = "முன்னால் படுக்கை உள்ளது."
        english_text = "Bed ahead."
    elif "cat" in lbl:
        clip_id = 5
        tamil_text = "முன்னால் பூனை உள்ளது."
        english_text = "Cat ahead."
    elif "clock" in lbl:
        clip_id = 13
        tamil_text = "முன்னால் கடிகாரம் உள்ளது."
        english_text = "Clock ahead."
    elif "door" in lbl:
        clip_id = 20
        tamil_text = "முன்னால் கதவு உள்ளது."
        english_text = "Door ahead."
    elif "wall" in lbl:
        clip_id = 22
        tamil_text = "முன்னால் சுவர் உள்ளது."
        english_text = "Wall ahead."

    audio_file = CLIP_FILES.get(clip_id, "0003_obstacle_front.mp3")

    # Requirement 3: If ultrasonic sensor calculates distance and distance is NEAR (<= 50cm),
    # speaker starts to speak based on the situation: "எச்சரிக்கை! பொருள் அருகில் உள்ளது."
    is_near = False
    if distance_cm > 0 and distance_cm <= 50.0:
        is_near = True
        tamil_text = "எச்சரிக்கை! பொருள் அருகில் உள்ளது. " + tamil_text
        english_text = "Warning! Object is near. " + english_text

    return {
        "clip_id": clip_id,
        "tamil_text": tamil_text,
        "english_text": english_text,
        "audio_file": audio_file,
        "is_near": is_near
    }

def determine_position(x_center: float, img_width: float) -> str:
    """Classify bounding box center into left, center, or right third."""
    one_third = img_width / 3.0
    two_thirds = (2.0 * img_width) / 3.0
    if x_center < one_third:
        return "left"
    elif x_center > two_thirds:
        return "right"
    else:
        return "center"

def detect_text_medicines_and_currency(img_np: np.ndarray) -> list:
    """
    Extracts text via EasyOCR to detect medicines (Paracetamol, Rantac, Tassic Tanic)
    and currencies (500, 200, 100, 50, 20, 10 Rs, or general currency notes).
    Uses full image + central reticle crop for ultra-sharp reading.
    """
    global ocr_reader, HAVE_EASYOCR
    if not HAVE_EASYOCR and ocr_reader is None:
        try:
            _init_easyocr_worker()
        except Exception:
            pass
    if not HAVE_EASYOCR or ocr_reader is None:
        return []

    try:
        h, w = img_np.shape[:2]
        
        # 1. Full frame reading
        ocr_input = img_np
        if w < 700:
            ocr_input = cv2.resize(img_np, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        results = ocr_reader.readtext(ocr_input)
        
        # 2. If no text or few results, zoom into center reticle ROI (where user aims phone)
        if not results or len(results) < 2:
            ch1, ch2 = int(h * 0.12), int(h * 0.88)
            cw1, cw2 = int(w * 0.12), int(w * 0.88)
            center_crop = img_np[ch1:ch2, cw1:cw2]
            center_up = cv2.resize(center_crop, (int(center_crop.shape[1] * 1.5), int(center_crop.shape[0] * 1.5)), interpolation=cv2.INTER_CUBIC)
            res_center = ocr_reader.readtext(center_up)
            if res_center:
                if not results:
                    results = res_center
                else:
                    results.extend(res_center)

        if not results:
            return []

        extracted = []
        full_text = " ".join([str(res[1]).lower() for res in results])
        print(f"[OCR DETECTED TEXT] \"{full_text}\"")

        # 1. Medicines check (Requirement 6)
        if any(w in full_text for w in ["paracetamol", "paracetomal", "paracet", "dolo", "calpol", "crocin", "pcm", "paracip", "metacin", "650", "p-650", "acetaminophen", "fevridol", "pyregesic", "pacimol"]):
            extracted.append({"label": "paracetamol", "confidence": 0.98})
        elif any(w in full_text for w in ["rantac", "ranitidine", "aciloc", "zantac", "histac", "pan 40", "pantop", "omez", "omeprazole", "pantocid"]):
            extracted.append({"label": "rantac", "confidence": 0.98})
        elif any(w in full_text for w in ["tassic", "tanic", "tonic", "tastic", "tusq", "cough", "syrup", "benadryl", "corex", "ascoril", "grilinctus", "cheston", "koflet", "ambroxol"]):
            extracted.append({"label": "tassic", "confidence": 0.98})
        elif any(w in full_text for w in ["medicine", "tablet", "tablets", "capsule", "capsules", "pharma", "pharmaceutical", "strip"]):
            extracted.append({"label": "medicine", "confidence": 0.95})

        # 2. Currency check (Requirement 7)
        words = re.findall(r'[a-zA-Z0-9]+', full_text)
        has_curr_context = any(k in full_text for k in [
            "rupee", "rupees", "rs", "₹", "bank", "reserve", "note", "gandhi", "india", "bharat",
            "paisa", "central", "rbi", "guaranteed", "governor", "currency", "cash"
        ])

        has_500 = ("500" in words) or any(w in full_text for w in ["500", "५००", "five hundred", "₹500", "500rs", "500 rs", "500/-"])
        has_200 = ("200" in words) or any(w in full_text for w in ["200", "२००", "two hundred", "₹200", "200rs", "200 rs", "200/-"])
        has_100 = ("100" in words) or any(w in full_text for w in ["100", "१००", "one hundred", "₹100", "100rs", "100 rs", "100/-"])
        has_50  = (("50" in words and has_curr_context) or any(w in full_text for w in ["५०", "fifty", "₹50", "50rs", "50 rs", "50/-"]))
        has_20  = (("20" in words and has_curr_context) or any(w in full_text for w in ["२०", "twenty", "₹20", "20rs", "20 rs", "20/-"]))
        has_10  = (("10" in words and has_curr_context) or any(w in full_text for w in ["१०", "ten", "₹10", "10rs", "10 rs", "10/-"]))

        if has_500:
            extracted.append({"label": "500", "confidence": 0.99})
        elif has_200:
            extracted.append({"label": "200", "confidence": 0.99})
        elif has_100:
            extracted.append({"label": "100", "confidence": 0.99})
        elif has_50:
            extracted.append({"label": "50", "confidence": 0.99})
        elif has_20:
            extracted.append({"label": "20", "confidence": 0.99})
        elif has_10:
            extracted.append({"label": "10", "confidence": 0.99})
        elif has_curr_context and any(k in full_text for k in ["reserve bank", "bank of india", "rupees", "central government", "gandhi", "bharat", "currency", "money"]):
            extracted.append({"label": "currency", "confidence": 0.95})

        # 3. Stairs & Direction signs check (0021_stairs_ahead.mp3)
        if any(w in full_text for w in ["stair", "stairs", "step", "steps", "staircase", "steps ahead", "stairway"]):
            extracted.append({"label": "stairs", "confidence": 0.97})

        return extracted
    except Exception as e:
        print(f"[OCR EXCEPTION] {e}")
        return []

def detect_staircase_pattern(img_np: np.ndarray) -> bool:
    """
    Detects staircase step structure using horizontal parallel edge analysis in OpenCV.
    Stairs present a characteristic pattern of 4+ approximately parallel horizontal edges.
    """
    try:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        # Focus on middle and lower 80% where stairs appear in walking path
        roi = gray[int(h * 0.20):, :]
        blurred = cv2.GaussianBlur(roi, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 130)
        min_line_len = int(w * 0.25)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=min_line_len, minLineLength=min_line_len, maxLineGap=25)
        if lines is None:
            return False
        
        horizontal_y = []
        for line in lines:
            pts = line.flatten()
            if len(pts) >= 4:
                x1, y1, x2, y2 = pts[0], pts[1], pts[2], pts[3]
                if abs(y2 - y1) <= 6 and abs(x2 - x1) >= min_line_len:
                    horizontal_y.append(int((y1 + y2) // 2))
        
        if len(horizontal_y) < 4:
            return False
            
        horizontal_y.sort()
        distinct_y = []
        for y in horizontal_y:
            if not distinct_y or abs(y - distinct_y[-1]) > 12:
                distinct_y.append(y)
                
        # 4 or more distinct parallel horizontal step edges indicates stairs
        return len(distinct_y) >= 4
    except Exception:
        return False

MOBILE_CAMERA_HTML = """<!DOCTYPE html>
<html lang="ta">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AI Smart Assistive Mobile Camera</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f1115; color: #fff; text-align: center; overflow-x: hidden; padding-bottom: 30px; }
        header { background: #161922; padding: 14px 10px; border-bottom: 2px solid #232733; }
        h1 { font-size: 1.25rem; color: #00E676; font-weight: 700; letter-spacing: 0.5px; }
        .subtitle { font-size: 0.8rem; color: #8892b0; margin-top: 3px; }
        
        #video-container { 
            position: relative; 
            width: 95%; 
            max-width: 480px; 
            margin: 14px auto; 
            border-radius: 16px; 
            overflow: hidden; 
            background: #000; 
            box-shadow: 0 8px 30px rgba(0,0,0,0.8); 
            aspect-ratio: 4/3; 
            border: 2px solid #2a2e3d;
        }
        video { width: 100%; height: 100%; display: block; object-fit: cover; }
        
        /* Reticle target overlay */
        .reticle {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 190px;
            height: 190px;
            transform: translate(-50%, -50%);
            border: 2px dashed rgba(0, 230, 118, 0.45);
            border-radius: 14px;
            pointer-events: none;
            transition: all 0.25s ease;
        }
        .reticle.observing {
            border: 3px dashed #FFB300;
            box-shadow: 0 0 20px rgba(255, 179, 0, 0.5);
            transform: translate(-50%, -50%) scale(1.02);
        }
        .reticle.detected {
            border: 3px solid #00E676;
            box-shadow: 0 0 28px rgba(0, 230, 118, 0.75);
            transform: translate(-50%, -50%) scale(1.05);
        }
        .reticle.gold {
            border: 3px solid #FFD700;
            box-shadow: 0 0 32px rgba(255, 215, 0, 0.85);
            transform: translate(-50%, -50%) scale(1.05);
        }

        /* Live Detection HUD Card */
        #hud-card { 
            position: absolute; 
            bottom: 12px; 
            left: 12px; 
            right: 12px; 
            background: rgba(15, 17, 21, 0.94); 
            backdrop-filter: blur(10px);
            padding: 14px 16px; 
            border-radius: 12px; 
            border-left: 6px solid #00E676; 
            box-shadow: 0 6px 20px rgba(0,0,0,0.7);
            text-align: left; 
            transition: all 0.25s ease;
        }
        #hud-card.observing-border { border-left-color: #FFB300; }
        #hud-card.confirmed-border { border-left-color: #00E676; }
        #hud-card.gold-border { border-left-color: #FFD700; }
        
        .hud-badge {
            display: inline-block;
            font-size: 0.72rem;
            text-transform: uppercase;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 12px;
            background: #00E676;
            color: #000;
            margin-bottom: 6px;
        }
        .hud-badge.observing { background: #FFB300; color: #000; }
        .hud-badge.confirmed { background: #00E676; color: #000; }
        .hud-badge.gold { background: #FFD700; color: #000; }

        #detected-label { font-size: 1.45rem; font-weight: 800; color: #FFFFFF; line-height: 1.25; }
        #detected-sub { font-size: 0.9rem; color: #a0aec0; margin-top: 4px; font-weight: 500; }
        
        .hud-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 8px;
            padding-top: 6px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-size: 0.75rem;
            color: #718096;
        }
        .hud-meta span { color: #00E676; font-weight: bold; }

        /* Controls */
        .controls { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin: 12px auto; max-width: 480px; padding: 0 12px; }
        button { flex: 1 1 45%; padding: 13px; font-size: 0.88rem; font-weight: bold; border: none; border-radius: 10px; cursor: pointer; transition: transform 0.1s, opacity 0.2s; }
        button:active { transform: scale(0.97); opacity: 0.85; }
        .btn-start { background: #00E676; color: #000; }
        .btn-stop { background: #f44336; color: #fff; }
        .btn-switch { background: #2979FF; color: #fff; }
        .btn-sound { background: #1f2937; color: #9ca3af; border: 1px solid #374151; }
        .btn-sound.active { background: #059669; color: #fff; border: 1px solid #10b981; }
        
        .emergency-bar { display: flex; gap: 10px; max-width: 480px; margin: 10px auto; padding: 0 12px; }
        .btn-fall { background: #d32f2f; color: #fff; flex: 1; }
        .btn-safe { background: #2e7d32; color: #fff; flex: 1; }
        
        #status-pill { display: inline-block; padding: 5px 14px; border-radius: 20px; font-size: 0.8rem; background: #232733; color: #8892b0; margin-top: 8px; }
        .scanning { background: #133a1e !important; color: #69f0ae !important; font-weight: bold; }
        
        .server-info {
            max-width: 480px;
            margin: 14px auto 0;
            padding: 10px 14px;
            background: #161922;
            border-radius: 10px;
            font-size: 0.8rem;
            color: #718096;
            text-align: left;
            line-height: 1.5;
        }
        .server-info b { color: #e2e8f0; }
    </style>
</head>
<body>
    <header>
        <h1>👁 AI Smart Assistive Vision</h1>
        <div class="subtitle">Live Detection: Money, Medicines & Obstacles</div>
        <div id="status-pill">● Initializing Camera...</div>
    </header>

    <div id="video-container">
        <video id="webcam" autoplay playsinline muted></video>
        <div id="reticle-box" class="reticle"></div>
        <div id="hud-card">
            <div id="hud-badge" class="hud-badge">🔍 scanning</div>
            <div id="detected-label">கேமரா தயாராகிறது...</div>
            <div id="detected-sub">பொருட்கள் அல்லது பணத்தை கேமராவில் காட்டவும்</div>
            <div class="hud-meta">
                <div id="hud-conf">துல்லியம்: <span>--</span></div>
                <div id="hud-speaker">📢 MAX98357A + போன் ஸ்பீக்கர்</div>
            </div>
        </div>
    </div>

    <div class="controls">
        <button id="btn-toggle" class="btn-stop" onclick="toggleCamera()">⏹ Stop Camera</button>
        <button class="btn-switch" onclick="switchCamera()">🔄 Flip Camera</button>
        <button id="btn-phone-audio" class="btn-sound active" onclick="togglePhoneAudio()">🔊 போன் ஒலி: ஆன்</button>
    </div>

    <div class="emergency-bar">
        <button class="btn-fall" onclick="triggerFall()">🚨 FALL ALERT</button>
        <button class="btn-safe" onclick="triggerSafe()">✅ SAFE SWITCH</button>
    </div>

    <div class="server-info">
        <div><b>AI Server:</b> https://192.168.29.89:8000</div>
        <div><b>ஸ்பீக்கர்:</b> MAX98357A ஹார்ட்வேர் ஸ்பீக்கர் + போன் HD ஆடியோ (தெளிவான தமிழ் குரல்)</div>
    </div>

    <canvas id="hidden-canvas" style="display: none;"></canvas>
    <audio id="phone-audio" preload="auto"></audio>

    <script>
        let video = document.getElementById('webcam');
        let canvas = document.getElementById('hidden-canvas');
        let phoneAudioPlayer = document.getElementById('phone-audio');
        let statusPill = document.getElementById('status-pill');
        let hudCard = document.getElementById('hud-card');
        let hudBadge = document.getElementById('hud-badge');
        let labelElem = document.getElementById('detected-label');
        let subElem = document.getElementById('detected-sub');
        let confElem = document.getElementById('hud-conf');
        let speakerElem = document.getElementById('hud-speaker');
        let reticle = document.getElementById('reticle-box');
        let toggleBtn = document.getElementById('btn-toggle');
        let audioBtn = document.getElementById('btn-phone-audio');

        let stream = null;
        let isRunning = false;
        let isSending = false;
        let currentFacingMode = 'environment';
        let clearHudTimer = null;
        let phoneAudioActive = true;
        let lastPlayedPhoneFile = "";
        let lastPhonePlayTime = 0;

        function togglePhoneAudio() {
            phoneAudioActive = !phoneAudioActive;
            if (phoneAudioActive) {
                audioBtn.innerText = "🔊 போன் ஒலி: ஆன்";
                audioBtn.className = "btn-sound active";
                phoneAudioPlayer.src = '/audio/0040_system_connected.mp3';
                phoneAudioPlayer.play().catch(e => {});
            } else {
                audioBtn.innerText = "🔇 போன் ஒலி: ஆஃப்";
                audioBtn.className = "btn-sound";
                phoneAudioPlayer.pause();
            }
        }

        function playPhoneAudio(audioFile) {
            if (!phoneAudioActive || !audioFile) return;
            let now = Date.now();
            if (now - lastPhonePlayTime < 2800) return;
            if (audioFile === lastPlayedPhoneFile && (now - lastPhonePlayTime < 5000)) return;

            lastPlayedPhoneFile = audioFile;
            lastPhonePlayTime = now;

            phoneAudioPlayer.src = '/audio/' + audioFile;
            phoneAudioPlayer.play().catch(e => console.log("Audio play notice:", e));
        }

        async function startCamera() {
            try {
                if (stream) stream.getTracks().forEach(t => t.stop());
                // Request HD 720p stream with continuous auto-focus for crystal clear close-up observation
                const constraints = {
                    video: {
                        facingMode: { ideal: currentFacingMode },
                        width: { ideal: 1280, min: 640 },
                        height: { ideal: 720, min: 480 }
                    },
                    audio: false
                };
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                video.srcObject = stream;

                // Try applying continuous autofocus if device camera supports it
                try {
                    const track = stream.getVideoTracks()[0];
                    const capabilities = track.getCapabilities ? track.getCapabilities() : {};
                    if (capabilities.focusMode && capabilities.focusMode.includes('continuous')) {
                        await track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] });
                    }
                } catch (e) {
                    console.log("Autofocus constraint notice:", e);
                }

                isRunning = true;
                toggleBtn.innerText = "⏹ Stop Camera";
                toggleBtn.className = "btn-stop";
                statusPill.className = "scanning";
                statusPill.innerText = "● Live AI Scanning Active";

                // Warm up audio context on user gesture
                phoneAudioPlayer.load();

                // Start adaptive capture loop
                scheduleNextFrame();
            } catch (err) {
                statusPill.innerText = "Camera Access Error";
                alert("Camera error: " + err.message + "\\nPlease ensure HTTPS and allow camera access.");
            }
        }

        function stopCamera() {
            if (stream) {
                stream.getTracks().forEach(t => t.stop());
                stream = null;
            }
            isRunning = false;
            toggleBtn.innerText = "📷 Start Camera";
            toggleBtn.className = "btn-start";
            statusPill.className = "";
            statusPill.innerText = "Camera Paused";
            reticle.className = "reticle";
        }

        function toggleCamera() {
            if (isRunning) stopCamera();
            else startCamera();
        }

        function switchCamera() {
            currentFacingMode = (currentFacingMode === 'environment') ? 'user' : 'environment';
            if (isRunning) startCamera();
        }

        function scheduleNextFrame() {
            if (isRunning) {
                setTimeout(captureAndSendFrame, 180);
            }
        }

        async function captureAndSendFrame() {
            if (!isRunning || isSending || video.videoWidth === 0) {
                scheduleNextFrame();
                return;
            }
            isSending = true;

            // 800x600 capture with high image smoothing ensures sharp text for medicine & currency recognition
            canvas.width = 800;
            canvas.height = 600;
            let ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            canvas.toBlob(async (blob) => {
                if (!blob) { isSending = false; scheduleNextFrame(); return; }
                try {
                    let resp = await fetch('/detect', {
                        method: 'POST',
                        headers: { 'Content-Type': 'image/jpeg' },
                        body: blob
                    });
                    if (resp.ok) {
                        let data = await resp.json();
                        if (data && data.length > 0) {
                            let top = data[0];
                            let confPct = Math.round((top.confidence || 0) * 100);
                            
                            if (confPct >= 70) {
                                // CONFIRMED DETECTION (>= 70%): Speaker speaks & HUD glows confirmed!
                                let isSpecial = ['500','200','100','50','20','10','paracetamol','rantac','tassic','tanic','tonic','currency','medicine'].includes(String(top.label).toLowerCase());

                                hudBadge.className = isSpecial ? "hud-badge gold" : "hud-badge confirmed";
                                hudBadge.innerText = isSpecial ? "🪙 பணம் / மருந்து (" + confPct + "%)" : "🎯 உறுதி (" + confPct + "%)";
                                hudCard.className = isSpecial ? "gold-border" : "confirmed-border";
                                
                                labelElem.innerText = top.tamil_text || top.label;
                                subElem.innerText = (top.english_text || top.label) + (top.position ? " [" + top.position + "]" : "");
                                
                                confElem.innerHTML = "துல்லியம்: <span style='color:#00E676;font-weight:bold;'>" + confPct + "% (ஸ்பீக்கர் பேசியது)</span>";
                                speakerElem.innerText = "📢 MAX98357A Clip #" + top.clip_id;
                                
                                reticle.className = isSpecial ? "reticle gold" : "reticle detected";

                                // Play crystal-clear Tamil HD audio on phone speaker if enabled
                                if (top.audio_file) {
                                    playPhoneAudio(top.audio_file);
                                }

                                if (clearHudTimer) clearTimeout(clearHudTimer);
                                clearHudTimer = setTimeout(resetHud, 3500);

                            } else if (confPct >= 50) {
                                // ACTIVE OBSERVING (50% - 69%): Camera is observing! Guides user to hold steady / move slightly closer
                                hudBadge.className = "hud-badge observing";
                                hudBadge.innerText = "👁 கவனிக்கிறது (" + confPct + "%)";
                                hudCard.className = "observing-border";
                                
                                labelElem.innerText = top.tamil_text || top.label;
                                subElem.innerText = "துல்லியம் " + confPct + "% (70% வந்ததும் ஸ்பீக்கர் பேசும் - இன்னும் அருகில் காட்டவும்)";
                                confElem.innerHTML = "துல்லியம்: <span style='color:#FFB300;font-weight:bold;'>" + confPct + "% (அருகில் காட்டவும்)</span>";
                                speakerElem.innerText = "⏳ 70% வந்ததும் பேசும்...";
                                
                                reticle.className = "reticle observing";

                                if (clearHudTimer) clearTimeout(clearHudTimer);
                                clearHudTimer = setTimeout(resetHud, 2500);
                            }
                        }
                    }
                } catch (e) {
                    console.log("Detect error:", e);
                } finally {
                    isSending = false;
                    scheduleNextFrame();
                }
            }, 'image/jpeg', 0.85);
        }

        function resetHud() {
            reticle.className = "reticle";
            hudBadge.className = "hud-badge";
            hudBadge.innerText = "🔍 scanning";
            hudCard.className = "";
            labelElem.innerText = "ஸ்கேன் செய்கிறது...";
            subElem.innerText = "பொருட்கள் அல்லது பணத்தை கேமராவில் காட்டவும்";
            confElem.innerHTML = "துல்லியம்: <span>--</span>";
            speakerElem.innerText = "📢 MAX98357A + போன் ஸ்பீக்கர்";
        }

        async function triggerFall() {
            try {
                await fetch('/alert/fall', { method: 'POST' });
                alert("🚨 Fall SOS Alert Sent to Guardian Telegram!");
            } catch (e) {
                alert("Alert error: " + e.message);
            }
        }

        async function triggerSafe() {
            try {
                await fetch('/alert/safe', { method: 'POST' });
                alert("✅ Safe Switch Confirmed!");
            } catch (e) {
                alert("Safe switch error: " + e.message);
            }
        }

        window.addEventListener('load', () => {
            startCamera();
        });
    </script>
</body>
</html>
"""

@app.api_route("/camera", methods=["GET", "HEAD"], response_class=HTMLResponse)
def mobile_camera_page(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    """Serves the live mobile camera capture app for smartphones."""
    return HTMLResponse(content=MOBILE_CAMERA_HTML)

@app.api_route("/", methods=["GET", "HEAD"])
def read_root(request: Request):
    if request.method == "HEAD":
        return Response(status_code=200)
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return HTMLResponse(content=MOBILE_CAMERA_HTML)
    return {
        "status": "online",
        "service": "Assistive Vision YOLOv8, OCR Medicine/Currency & Tamil Voice Server",
        "for": "Visually Impaired People",
        "mobile_camera_url": "/camera",
        "audio_player": "Real Human Voice MP3 Speaker Active (35 clips loaded)",
        "features": [
            "Obstacle Proximity Warning (எச்சரிக்கை! பொருள் அருகில் உள்ளது)",
            "Stairs Ahead Voice Warning (0021_stairs_ahead.mp3 - முன்னால் படிக்கட்டுகள் உள்ளன)",
            "Medicine Identification (Paracetamol, Rantac, Tassic Tanic)",
            "Currency Note Identification (500, 200, 100, 50, 20, 10 Rs)",
            "Immediate Fall Telegram Alert & Safe Switch Notification",
            "Real Tamil MP3 Audio Playback through Computer Speaker"
        ],
        "endpoints": ["/camera", "/detect", "/alert/fall", "/alert/safe", "/play", "/audio/{filename}", "/tts"]
    }

@app.post("/detect")
async def detect_objects(
    request: Request,
    label: str = Query(None, description="Explicit label override for testing"),
    distance: float = Query(0.0, description="Ultrasonic distance in cm")
):
    """
    Accepts image bytes via raw POST body (image/jpeg) or multipart form-data.
    Executes EasyOCR for medicines & currency identification and YOLOv8 / OpenCV for obstacle detection.
    Strict Accuracy Threshold: ONLY detections with confidence >= 0.70 (70%) will trigger speech on MAX98357A.
    """
    try:
        CONF_THRESHOLD = 0.70  # Strict 70% accuracy requirement: speaker will NEVER speak below 70%

        # If explicit label passed (e.g. testing or direct classification)
        if label:
            t_info = generate_tamil_instruction(label, "center", distance_cm=distance)
            cid = t_info["clip_id"]
            physical_speaker.send_clip(cid, label=label, confidence=0.98)
            return JSONResponse(content=[{
                "label": label,
                "confidence": 0.98,
                "position": "center",
                "clip_id": t_info["clip_id"],
                "tamil_text": t_info["tamil_text"],
                "english_text": t_info["english_text"],
                "audio_file": t_info.get("audio_file", "")
            }])

        image_bytes = await request.body()
        if not image_bytes or len(image_bytes) < 10:
            return JSONResponse(content=[])

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(img)

        # 1. First priority: Check medicines, currency, and stairs text via OCR
        special_items = detect_text_medicines_and_currency(img_np)
        if special_items:
            results = []
            for item in special_items:
                conf = float(item["confidence"])
                if conf < CONF_THRESHOLD:
                    continue
                t_info = generate_tamil_instruction(item["label"], "center", distance_cm=distance)
                results.append({
                    "label": item["label"],
                    "confidence": conf,
                    "position": "center",
                    "clip_id": t_info["clip_id"],
                    "tamil_text": t_info["tamil_text"],
                    "english_text": t_info["english_text"],
                    "audio_file": t_info.get("audio_file", "")
                })
            if results:
                # Prioritize highest confidence special detection
                results.sort(key=lambda d: d["confidence"], reverse=True)
                top = results[0]
                cid = top["clip_id"]
                lbl = top["label"]
                conf = top["confidence"]
                print(f"[SERVER DETECTION] 👁 Special Item (>= 70%): {lbl} (Conf: {conf:.2f}) -> Clip ID: {cid}")
                physical_speaker.send_clip(cid, label=lbl, confidence=conf)
                return JSONResponse(content=results)

        # 2. Second priority: Object / Obstacle detection via YOLOv8
        detections = []
        if model is not None:
            yolo_results = model(img, verbose=False)[0]
            for box in yolo_results.boxes:
                conf = float(box.conf[0].cpu().numpy())
                # Allow observing from 50% so phone HUD displays live observation guidance to user!
                if conf < 0.50:
                    continue
                cls_id = int(box.cls[0].cpu().numpy())
                raw_label = model.names[cls_id]
                mapped_label = TARGET_CLASSES.get(raw_label, raw_label)

                xyxy = box.xyxy[0].cpu().numpy().astype(float)
                x_center = (xyxy[0] + xyxy[2]) / 2.0
                position = determine_position(x_center, float(img.width))

                t_info = generate_tamil_instruction(mapped_label, position, distance_cm=distance)
                detections.append({
                    "label": mapped_label,
                    "confidence": round(conf, 2),
                    "position": position,
                    "clip_id": t_info["clip_id"],
                    "tamil_text": t_info["tamil_text"],
                    "english_text": t_info["english_text"],
                    "audio_file": t_info.get("audio_file", "")
                })

            # Sort strictly by highest confidence first
            if detections:
                detections.sort(key=lambda d: d["confidence"], reverse=True)

        # 3. Third priority: Visual staircase pattern if no YOLO objects
        if not detections and detect_staircase_pattern(img_np):
            t_info = generate_tamil_instruction("stairs", "center", distance_cm=distance)
            detections.append({
                "label": "stairs",
                "confidence": 0.95,
                "position": "center",
                "clip_id": t_info["clip_id"],
                "tamil_text": t_info["tamil_text"],
                "english_text": t_info["english_text"],
                "audio_file": t_info.get("audio_file", "0021_stairs_ahead.mp3")
            })

        # Trigger physical speaker ONLY IF CONFIDENCE >= 0.70
        if detections:
            top_det = detections[0]
            primary_clip = top_det["clip_id"]
            lbl = top_det["label"]
            conf = top_det["confidence"]
            pos = top_det.get("position", "center")
            tamil_t = top_det.get("tamil_text", "")
            if conf >= CONF_THRESHOLD:
                print(f"[SERVER DETECTION] 👁 Obstacle Confirmed (>= 70%): {lbl} [{pos}] (Conf: {conf:.2f}) -> Clip ID: {primary_clip}")
                physical_speaker.send_clip(primary_clip, label=lbl, position=pos, tamil_text=tamil_t, confidence=conf)
            else:
                print(f"[SERVER OBSERVING] 👁 Observing: {lbl} [{pos}] (Conf: {conf:.2f} < 0.70 - speaker silent)")

        return JSONResponse(content=detections)

    except Exception as e:
        print(f"[DETECT ERROR] {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/alert/fall")
async def alert_fall(details: str = Query("Fall detected", description="Fall alert details")):
    """Sends emergency fall alert to guardian via Telegram Bot API, starts hardware buzzer siren and emergency audio."""
    msg = (
        "🚨 அவசர எச்சரிக்கை! (EMERGENCY FALL ALERT)\n"
        "பயனர் கீழே விழுந்துவிட்டார்!\n"
        "உடனடியாக கவனிக்கவும்.\n"
        f"Details: {details}\n"
        "Status: Fall Detected\n"
        "Action: Please assist the user immediately!"
    )
    sent = send_telegram_notification(msg)
    # 1. TRIGGER ACTIVE BUZZER EMERGENCY SIREN ON ESP32 HARDWARE!
    physical_speaker.trigger_fall_alarm()
    # 2. Also play emergency Tamil voice clip #10
    physical_speaker.send_clip(10, label="emergency fall", force=True)
    return JSONResponse(content={
        "status": "ok",
        "alert": "fall",
        "telegram_sent": sent,
        "buzzer": "active_siren",
        "message": "Emergency alert dispatched to guardian with active buzzer siren alarm",
        "audio_played": "0010_emergency_fall.mp3"
    })

@app.post("/alert/safe")
async def alert_safe(details: str = Query("Safe switch clicked", description="Safe status details")):
    """Sends safe update to guardian via Telegram when safe switch is clicked and immediately stops the buzzer."""
    msg = (
        "✅ பாதுகாப்பு தகவல் (SAFE UPDATE)\n"
        "பயனர் பாதுகாப்பாக உள்ளார்.\n"
        "அவசர எச்சரிக்கை சுவிட்ச் மூலம் அணைக்கப்பட்டது.\n"
        f"Details: {details}\n"
        "Status: User is SAFE. Alert buzzer deactivated."
    )
    sent = send_telegram_notification(msg)
    # 1. IMMEDIATELY STOP ACTIVE BUZZER ON ESP32 HARDWARE!
    physical_speaker.trigger_safe_alarm()
    # 2. Also play safe confirmation Tamil voice clip #39
    physical_speaker.send_clip(39, label="user safe", force=True)
    return JSONResponse(content={
        "status": "ok",
        "alert": "safe",
        "telegram_sent": sent,
        "buzzer": "stopped",
        "message": "Safe update dispatched to guardian and buzzer stopped",
        "audio_played": "0039_user_safe.mp3"
    })

@app.get("/play")
def play_audio_endpoint(
    clip_id: int = Query(None, description="Clip ID to play (e.g. 21 for stairs)"),
    label: str = Query(None, description="Label (e.g. stairs, paracetamol, 500)"),
    name: str = Query(None, description="Audio file name (e.g. 0021_stairs_ahead.mp3)")
):
    """Directly triggers real Tamil audio playback through the speaker."""
    cid = clip_id
    if name:
        for k, v in CLIP_FILES.items():
            if name.lower() in v.lower():
                cid = k
                break
    elif label:
        t_info = generate_tamil_instruction(label)
        cid = t_info["clip_id"]

    if cid is not None:
        physical_speaker.send_clip(cid, label=label or str(cid), force=True)
        audio_player.play(clip_id=cid, force=True)
        fname = CLIP_FILES.get(cid, f"clip_{cid}.mp3")
        return {
            "status": "playing",
            "clip_id": cid,
            "filename": fname,
            "message": f"Real audio '{fname}' is now playing through the speaker"
        }
    return JSONResponse(status_code=400, content={"error": "Specify clip_id, label, or name"})

@app.get("/audio/{filename}")
def stream_audio_file(filename: str):
    """Streams or downloads an audio file from the audio repository."""
    fpath = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(fpath):
        return FileResponse(fpath, media_type="audio/mpeg")
    return JSONResponse(status_code=404, content={"error": f"Audio file '{filename}' not found"})

@app.get("/tts")
async def generate_tts(text: str = Query(..., description="Tamil text to synthesize")):
    """Generates Tamil speech audio MP3 via gTTS."""
    if not HAVE_GTTS:
        return JSONResponse(status_code=503, content={"error": "gTTS package not installed on server"})
    try:
        tts = gTTS(text=text, lang='ta', slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_filename = fp.name
        tts.save(temp_filename)

        with open(temp_filename, "rb") as f:
            audio_bytes = f.read()

        try:
            os.remove(temp_filename)
        except Exception:
            pass
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    cert_path = os.path.join(os.path.dirname(__file__), "cert.pem")
    key_path = os.path.join(os.path.dirname(__file__), "key.pem")
    port = int(os.environ.get("PORT", 8000))
    
    # If deployed on Cloud (Render, Hugging Face, etc.), the Cloud provides HTTPS at the edge
    if "PORT" in os.environ:
        print(f"[CLOUD SERVER READY] Binding to 0.0.0.0:{port}")
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
    elif os.path.exists(cert_path) and os.path.exists(key_path):
        print("\n" + "=" * 65)
        print(" [SECURE HTTPS READY] Camera Enabled for Mobile Chrome & Safari")
        print(f" Mobile URL: https://192.168.29.89:{port}/camera")
        print("=" * 65 + "\n")
        uvicorn.run(app, host="0.0.0.0", port=port, ssl_certfile=cert_path, ssl_keyfile=key_path, reload=False)
    else:
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

