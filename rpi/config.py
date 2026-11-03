"""
Configuration Settings for Smart Assistive System on Raspberry Pi 3
====================================================================
Defines BCM GPIO pin assignments, physical header pins, sensor thresholds,
audio clip mappings, and Telegram credentials.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
AUDIO_DIR = PROJECT_ROOT / "audio"
MODEL_PATH = PROJECT_ROOT / "yolov8n.pt"

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# =============================================================================
# 1. HARDWARE PIN CONFIGURATION (Raspberry Pi 3 Model B / B+)
# =============================================================================
# IMPORTANT: All GPIO numbers used in code are Broadcom (BCM) numbers.
# Physical pin numbers on the 40-pin header are listed for wiring reference.

PINS = {
    # MPU-6050 Accelerometer / Gyroscope (I2C-1)
    "I2C_SDA": {
        "bcm": 2,
        "physical": 3,
        "desc": "I2C Data (SDA) - 3.3V logic"
    },
    "I2C_SCL": {
        "bcm": 3,
        "physical": 5,
        "desc": "I2C Clock (SCL) - 3.3V logic"
    },

    # HC-SR04 Ultrasonic Distance Sensor
    "ULTRASONIC_TRIG": {
        "bcm": 23,
        "physical": 16,
        "desc": "Ultrasonic Trigger Pulse (Output, 3.3V)"
    },
    "ULTRASONIC_ECHO": {
        "bcm": 24,
        "physical": 18,
        "desc": "Ultrasonic Echo Pulse (Input via 1k/2k voltage divider, 3.3V max)"
    },

    # MAX98357A I2S Audio Amplifier
    "I2S_BCLK": {
        "bcm": 18,
        "physical": 12,
        "desc": "I2S Bit Clock (BCLK)"
    },
    "I2S_LRC": {
        "bcm": 19,
        "physical": 35,
        "desc": "I2S Word Select / Left-Right Clock (LRC / WS)"
    },
    "I2S_DIN": {
        "bcm": 21,
        "physical": 40,
        "desc": "I2S Serial Data In (DIN)"
    },

    # Emergency Cancel Button
    "BUTTON_CANCEL": {
        "bcm": 17,
        "physical": 11,
        "desc": "Cancel / Safe Push Button (Active LOW, internal pull-up to 3.3V)"
    },

    # Emergency Buzzer
    "BUZZER": {
        "bcm": 27,
        "physical": 13,
        "desc": "Emergency Siren Buzzer (Output, active HIGH)"
    }
}

# =============================================================================
# 2. ULTRASONIC SENSOR THRESHOLDS
# =============================================================================
ULTRASONIC_SAMPLE_INTERVAL_SEC = 0.05    # 20 Hz distance sampling
ULTRASONIC_TIMEOUT_SEC = 0.03            # 30 ms max timeout (~5 m)
ULTRASONIC_MEDIAN_WINDOW = 5             # Median filter size to reject noise spikes
DISTANCE_CRITICAL_CM = 50.0             # Obstacle <= 50 cm triggers near warning
DISTANCE_WARNING_CM = 120.0             # Obstacle <= 120 cm triggers caution notice
DISTANCE_MAX_VALID_CM = 400.0           # Maximum valid sensor distance
DISTANCE_MIN_VALID_CM = 2.0             # Minimum valid sensor distance

# =============================================================================
# 3. MPU-6050 FALL DETECTION ALGORITHM THRESHOLDS
# =============================================================================
FALL_SAMPLING_RATE_HZ = 50.0             # 50 Hz sampling loop (20 ms interval)
FALL_FREE_FALL_THRES_G = 0.45            # Acceleration magnitude < 0.45g (free-fall)
FALL_IMPACT_THRES_G = 2.50               # Acceleration magnitude > 2.50g (impact spike)
FALL_TILT_THRES_DEG = 60.0               # Post-impact body tilt > 60 degrees from vertical
FALL_FREEFALL_MAX_WINDOW_MS = 400        # Time window between free-fall and impact
FALL_IMPACT_MAX_WINDOW_MS = 500          # Time window between impact and tilt confirmation
FALL_INACTIVITY_DURATION_MS = 1200       # Immobile duration post-impact
FALL_INACTIVITY_GYRO_MAX_DPS = 25.0      # Angular velocity limit during immobility (deg/s)

# Emergency Verification Countdown
FALL_COUNTDOWN_SECONDS = int(os.getenv("FALL_COUNTDOWN_SECONDS", "15"))

# =============================================================================
# 4. COMPUTER VISION & OBJECT DETECTION SETTINGS
# =============================================================================
CAMERA_FRAME_WIDTH = 320                 # Low resolution for fast CPU inference on Pi 3
CAMERA_FRAME_HEIGHT = 240
CAMERA_FPS = 15                          # CSI camera stream rate
VISION_INFERENCE_INTERVAL_SEC = 0.3      # Run YOLO inference ~3 times per second
VISION_CONFIDENCE_THRESHOLD = 0.45       # Minimum confidence to accept detection

TARGET_OBSTACLES = [
    "person", "chair", "table", "dining table", "door", "stairs", "pole",
    "car", "bus", "truck", "motorcycle", "bicycle", "dog", "couch", "sofa",
    "bed", "bench", "wall", "dustbin", "backpack"
]

# Medicine and Currency keywords for OCR identification
OCR_ENABLED = os.getenv("ENABLE_OCR", "false").lower() == "true"
OCR_INFERENCE_INTERVAL_SEC = 2.0         # Run OCR less frequently to save CPU

# =============================================================================
# 5. AUDIO & VOICE PLAYBACK SETTINGS
# =============================================================================
SPEECH_COOLDOWN_SEC = 3.5                # Prevent repetitive audio playback
AUDIO_OUTPUT_DEVICE = os.getenv("AUDIO_OUTPUT_DEVICE", "default") # ALSA device
ENABLE_TTS_FALLBACK = os.getenv("ENABLE_TTS_FALLBACK", "false").lower() == "true"

# Preloaded Audio Clip Mappings (Mapped to audio/ directory)
CLIP_MAP = {
    "system_ready": 1,          # 0001_system_ready.mp3
    "system_error": 2,          # 0002_system_error.mp3
    "obstacle_front": 3,        # 0003_obstacle_front.mp3
    "dustbin_front": 4,         # 0004_dustbin_front.mp3
    "dog_left": 5,              # 0005_dog_left.mp3
    "chair_right": 6,           # 0006_chair_right.mp3
    "person_front": 7,          # 0007_person_front.mp3
    "car_front": 8,             # 0008_car_front.mp3
    "table_front": 9,           # 0009_table_front.mp3
    "emergency_fall": 10,       # 0010_emergency_fall.mp3
    "alert_cancelled": 11,      # 0011_alert_cancelled.mp3
    "telegram_sent": 12,        # 0012_telegram_sent.mp3
    "obstacle_notice": 13,      # 0013_obstacle_notice.mp3
    "obstacle_warning": 14,     # 0014_obstacle_warning.mp3 ("எச்சரிக்கை! பொருள் அருகில் உள்ளது.")
    "person_ahead": 15,         # 0015_person_ahead.mp3
    "person_left": 16,          # 0016_person_left.mp3
    "person_right": 17,         # 0017_person_right.mp3
    "chair_ahead": 18,          # 0018_chair_ahead.mp3
    "table_ahead": 19,          # 0019_table_ahead.mp3
    "door_ahead": 20,           # 0020_door_ahead.mp3
    "stairs_ahead": 21,         # 0021_stairs_ahead.mp3 ("முன்னால் படிக்கட்டுகள் உள்ளன.")
    "wall_ahead": 22,           # 0022_wall_ahead.mp3
    "vehicle_ahead": 23,        # 0023_vehicle_ahead.mp3
    "medicine_reminder": 24,    # 0024_medicine_reminder.mp3
    "med_paracetamol": 30,      # 0030_medicine_paracetamol.mp3
    "med_rantac": 31,           # 0031_medicine_rantac.mp3
    "med_tassic": 32,           # 0032_medicine_tassic.mp3
    "curr_500": 33,             # 0033_currency_500.mp3
    "curr_200": 34,             # 0034_currency_200.mp3
    "curr_100": 35,             # 0035_currency_100.mp3
    "curr_50": 36,              # 0036_currency_50.mp3
    "curr_20": 37,              # 0037_currency_20.mp3
    "curr_10": 38,              # 0038_currency_10.mp3
    "user_safe": 39,            # 0039_user_safe.mp3
    "system_connected": 40      # 0040_system_connected.mp3
}

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
    14: "0014_obstacle_warning.mp3",
    15: "0015_person_ahead.mp3",
    16: "0016_person_left.mp3",
    17: "0017_person_right.mp3",
    18: "0018_chair_ahead.mp3",
    19: "0019_table_ahead.mp3",
    20: "0020_door_ahead.mp3",
    21: "0021_stairs_ahead.mp3",
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

# =============================================================================
# 6. TELEGRAM NOTIFICATION CREDENTIALS
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7906413709")
TELEGRAM_TIMEOUT_SEC = 8.0
TELEGRAM_MAX_RETRIES = 2
