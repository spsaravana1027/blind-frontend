#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Include secrets if available, otherwise fallback to defaults
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #include "secrets.h.example"
#endif

// ==========================================
// PIN CONFIGURATION (ESP32 DevKit V1)
// ==========================================

// MPU6050 I2C Pins
#define PIN_I2C_SDA         21
#define PIN_I2C_SCL         22

// HC-SR04 Ultrasonic Sensor Pins
#define PIN_ULTRASONIC_TRIG  5
#define PIN_ULTRASONIC_ECHO 18  // ECHO output connected via 5V->3.3V resistor voltage divider to GPIO 18

// MAX98357A I2S Audio Amplifier Pins
#define PIN_I2S_BCLK        26  // I2S Bit Clock (BCLK)
#define PIN_I2S_LRC         25  // I2S Word Select / Left-Right Clock (LRC / WS)
#define PIN_I2S_DIN         27  // I2S Data In (DIN / SD)

// ESP32-CAM UART Link (Hardware Serial 1)
#define PIN_VISION_RX       32  // ESP32 RX1 -> Connected to ESP32-CAM TX (GPIO1)
#define PIN_VISION_TX       33  // ESP32 TX1 -> Connected to ESP32-CAM RX (GPIO3)

// Local Alarm & Input Pins
#define PIN_BUZZER           4  // Active Buzzer output
#define PIN_CANCEL_BUTTON   19  // Push button (Active LOW, internal pull-up)

// ==========================================
// FALL DETECTION THRESHOLDS (MPU6050)
// ==========================================
// Acceleration is evaluated in Earth G-force units (1g = 9.81 m/s^2)
#define FALL_FREE_FALL_THRES_G   0.45f // Free fall acceleration threshold (<0.45g)
#define FALL_IMPACT_THRES_G      2.50f // Impact acceleration threshold (>2.50g)
#define FALL_TILT_THRES_DEG     60.00f // Post-impact tilt angle threshold (>60 degrees from upright)
#define FALL_INACTIVITY_TIME_MS  1200  // Post-impact low-activity duration window (ms)
#define FALL_CANCEL_WINDOW_SEC     15  // User cancellation window duration (seconds)

// ==========================================
// ULTRASONIC DISTANCE THRESHOLDS (CM)
// ==========================================
#define DIST_CRITICAL_CM    50    // <= 50 cm: Critical immediate hazard
#define DIST_WARNING_CM    120    // 51 - 120 cm: Warning obstacle zone
#define DIST_CLEAR_CM      120    // > 120 cm: Clearer path

// Backward compatibility alias definitions
#define DIST_URGENT_CM      DIST_CRITICAL_CM
#define DIST_NOTICE_CM      150
#define DIST_MAX_CLEAR_CM   DIST_CLEAR_CM

// ==========================================
// TAMIL VOICE ASSISTANT AUDIO CLIPS & PHRASES
// ==========================================
enum AudioClip {
    CLIP_SYSTEM_READY          = 1,  // "அமைப்பு தயார். பாதுகாப்பான பயணம் அமைய வாழ்த்துகிறோம்."
    CLIP_SYSTEM_ERROR          = 2,  // "அமைப்பில் கோளாறு. அமைப்பைச் சரிபார்க்கவும்."
    CLIP_OBSTACLE_FRONT        = 3,  // "முன்னால் தடை உள்ளது. உடனே நின்று கவனிக்கவும்."
    CLIP_DUSTBIN_FRONT         = 4,  // "முன்னால் குப்பைத்தொட்டி உள்ளது. கவனமாக விலகிச் செல்லவும்."
    CLIP_DOG_LEFT              = 5,  // "இடது பக்கத்தில் நாய் உள்ளது. கவனமாக வலது பக்கம் செல்லவும்."
    CLIP_CHAIR_RIGHT           = 6,  // "வலது பக்கத்தில் நாற்காலி உள்ளது. கவனமாக இடது பக்கம் செல்லவும்."
    CLIP_PERSON_FRONT          = 7,  // "முன்னால் ஒருவர் உள்ளார். கவனமாகச் செல்லவும்."
    CLIP_CAR_FRONT             = 8,  // "முன்னால் கார் உள்ளது. பாதுகாப்பாக நிற்கவும்."
    CLIP_TABLE_FRONT           = 9,  // "முன்னால் மேஜை உள்ளது. கவனமாகச் செல்லவும்."
    CLIP_EMERGENCY_FALL        = 10, // "அவசரம்! கீழே விழுந்துவிட்டீர்கள். ரத்து செய்ய பொத்தானை அழுத்தவும்."
    CLIP_ALERT_CANCELLED       = 11, // "அவசர எச்சரிக்கை ரத்து செய்யப்பட்டது."
    CLIP_TELEGRAM_SENT         = 12, // "பாதுகாவலருக்கு அவசரத் தகவல் அனுப்பப்பட்டது."
    CLIP_OBSTACLE_NOTICE       = 13, // "முன்னால் பொருள் உள்ளது"
    CLIP_OBSTACLE_WARNING      = 14, // "எச்சரிக்கை! பொருள் அருகில் உள்ளது"
    CLIP_PERSON_AHEAD          = 15, // "முன்னால் ஒருவர் உள்ளார்"
    CLIP_PERSON_LEFT           = 16, // "இடதுபுறம் ஒருவர் உள்ளார்"
    CLIP_PERSON_RIGHT          = 17, // "வலதுபுறம் ஒருவர் உள்ளார்"
    CLIP_CHAIR_AHEAD           = 18, // "முன்னால் நாற்காலி உள்ளது"
    CLIP_TABLE_AHEAD           = 19, // "முன்னால் மேஜை உள்ளது"
    CLIP_DOOR_AHEAD            = 20, // "முன்னால் கதவு உள்ளது"
    CLIP_STAIRS_AHEAD          = 21, // "முன்னால் படிக்கட்டுகள் உள்ளன"
    CLIP_WALL_AHEAD            = 22, // "முன்னால் சுவர் உள்ளது"
    CLIP_VEHICLE_AHEAD         = 23, // "முன்னால் வாகனம் உள்ளது"
    CLIP_MEDICINE_REMINDER     = 24, // "மருந்து எடுத்துக்கொள்ள வேண்டிய நேரம் வந்துவிட்டது."
    // Medicines Identification (Requirement 6)
    CLIP_MEDICINE_PARACETAMOL  = 30, // "இது பாராசிட்டமால் மாத்திரை."
    CLIP_MEDICINE_RANTAC       = 31, // "இது ரான்டாக் மாத்திரை."
    CLIP_MEDICINE_TASSIC       = 32, // "இது டாசிக் டானிக் மருந்து."
    // Currency Identification (Requirement 7)
    CLIP_CURRENCY_500          = 33, // "இது 500 ரூபாய்."
    CLIP_CURRENCY_200          = 34, // "இது 200 ரூபாய்."
    CLIP_CURRENCY_100          = 35, // "இது 100 ரூபாய்."
    CLIP_CURRENCY_50           = 36, // "இது 50 ரூபாய்."
    CLIP_CURRENCY_20           = 37, // "இது 20 ரூபாய்."
    CLIP_CURRENCY_10           = 38, // "இது 10 ரூபாய்."
    // User Safe & Connection Status (Requirements 2, 5, 8)
    CLIP_USER_SAFE             = 39, // "பாதுகாப்பாக உள்ளீர்கள். எச்சரிக்கை நிறுத்தப்பட்டது."
    CLIP_SYSTEM_CONNECTED      = 40  // "அமைப்பு தயார். இணைக்கப்பட்டது."
};

// ==========================================
// MEDICINE REMINDER CONFIGURATION
// ==========================================
#define MEDICINE_REMINDER_DEFAULT_INTERVAL_MS (15UL * 60UL * 1000UL) // 15 Minutes (900,000 ms)
#define MEDICINE_REMINDER_TEST_INTERVAL_MS    (1UL * 60UL * 1000UL)  // 1 Minute (60,000 ms quick test mode)

// ==========================================
// NTP TIMEKEEPING CONFIGURATION (Asia/Kolkata)
// ==========================================
#define NTP_SERVER_PRIMARY   "pool.ntp.org"
#define NTP_SERVER_SECONDARY "time.nist.gov"
#define GMT_OFFSET_SEC       (5 * 3600 + 30 * 60) // IST UTC+5:30
#define DAYLIGHT_OFFSET_SEC  0

// Structure mapping Tamil audio clips to text representation & tone audio synthesis parameters
struct TamilClipMetaData {
    AudioClip clip;
    const char* tamilText;
    const char* englishTranslation;
    uint16_t baseToneHz;
};

// ==========================================
// TIMING & RATE LIMIT CONFIGURATION
// ==========================================
#define AUDIO_REPEAT_DEBOUNCE_MS 4000 // Minimum time before repeating same object warning
#define MPU_SAMPLING_RATE_HZ       50 // MPU6050 sample rate in Hz
#define VISION_MIN_CONFIDENCE    0.50f // Minimum confidence threshold for object announcements

#endif // CONFIG_H
