#include "audio_player.h"
#include <cmath>

// Static metadata table for Tamil Voice Assistant announcements
static const TamilClipMetaData TAMIL_CLIPS[] = {
    { CLIP_SYSTEM_READY,    "அமைப்பு தயார். பாதுகாப்பான பயணம் அமைய வாழ்த்துகிறோம்.", "System ready", 523 },
    { CLIP_SYSTEM_ERROR,    "அமைப்பில் கோளாறு. அமைப்பைச் சரிபார்க்கவும்.", "System error", 330 },
    { CLIP_OBSTACLE_FRONT,  "முன்னால் தடை உள்ளது. உடனே நின்று கவனிக்கவும்.", "Obstacle ahead! Stop immediately", 880 },
    { CLIP_DUSTBIN_FRONT,   "முன்னால் குப்பைத்தொட்டி உள்ளது. கவனமாக விலகிச் செல்லவும்.", "Dustbin ahead. Move carefully", 659 },
    { CLIP_DOG_LEFT,        "இடது பக்கத்தில் நாய் உள்ளது. கவனமாக வலது பக்கம் செல்லவும்.", "Dog on left. Move right", 698 },
    { CLIP_CHAIR_RIGHT,     "வலது பக்கத்தில் நாற்காலி உள்ளது. கவனமாக இடது பக்கம் செல்லவும்.", "Chair on right. Move left", 784 },
    { CLIP_PERSON_FRONT,    "முன்னால் ஒருவர் உள்ளார். கவனமாகச் செல்லவும்.", "Person ahead. Move carefully", 587 },
    { CLIP_CAR_FRONT,       "முன்னால் கார் உள்ளது. பாதுகாப்பாக நிற்கவும்.", "Car ahead. Stop safely", 987 },
    { CLIP_TABLE_FRONT,     "முன்னால் மேஜை உள்ளது. கவனமாகச் செல்லவும்.", "Table ahead. Proceed with caution", 622 },
    { CLIP_EMERGENCY_FALL,  "அவசரம்! கீழே விழுந்துவிட்டீர்கள். ரத்து செய்ய பொத்தானை அழுத்தவும்.", "Emergency! Fall detected", 1046 },
    { CLIP_ALERT_CANCELLED, "அவசர எச்சரிக்கை ரத்து செய்யப்பட்டது.", "Emergency alert cancelled", 493 },
    { CLIP_TELEGRAM_SENT,   "பாதுகாவலருக்கு அவசரத் தகவல் அனுப்பப்பட்டது.", "Guardian alert sent via Telegram", 740 },
    { CLIP_OBSTACLE_NOTICE, "முன்னால் பொருள் உள்ளது.", "Obstacle notice", 659 },
    { CLIP_OBSTACLE_WARNING,"எச்சரிக்கை! பொருள் அருகில் உள்ளது.", "Obstacle warning", 880 },
    { CLIP_PERSON_AHEAD,    "முன்னால் ஒருவர் உள்ளார்.", "Person ahead", 587 },
    { CLIP_PERSON_LEFT,     "இடதுபுறம் ஒருவர் உள்ளார்.", "Person left", 587 },
    { CLIP_PERSON_RIGHT,    "வலதுபுறம் ஒருவர் உள்ளார்.", "Person right", 587 },
    { CLIP_CHAIR_AHEAD,     "முன்னால் நாற்காலி உள்ளது.", "Chair ahead", 784 },
    { CLIP_TABLE_AHEAD,     "முன்னால் மேஜை உள்ளது.", "Table ahead", 622 },
    { CLIP_DOOR_AHEAD,      "முன்னால் கதவு உள்ளது.", "Door ahead", 698 },
    { CLIP_STAIRS_AHEAD,    "முன்னால் படிக்கட்டுகள் உள்ளன.", "Stairs ahead", 740 },
    { CLIP_WALL_AHEAD,      "முன்னால் சுவர் உள்ளது.", "Wall ahead", 523 },
    { CLIP_VEHICLE_AHEAD,   "முன்னால் வாகனம் உள்ளது.", "Vehicle ahead", 987 },
    { CLIP_MEDICINE_REMINDER, "மருந்து எடுத்துக்கொள்ள வேண்டிய நேரம் வந்துவிட்டது. தயவுசெய்து உங்கள் மருந்தை எடுத்துக்கொள்ளுங்கள்.", "It is time to take your medicine. Please take your medicine.", 659 },
    // Medicines Identification (Requirement 6)
    { CLIP_MEDICINE_PARACETAMOL, "இது பாராசிட்டமால் மாத்திரை.", "This is a Paracetamol tablet.", 784 },
    { CLIP_MEDICINE_RANTAC,      "இது ரான்டாக் மாத்திரை.", "This is a Rantac tablet.", 740 },
    { CLIP_MEDICINE_TASSIC,      "இது டாசிக் டானிக் மருந்து.", "This is Tassic Tanic medicine.", 698 },
    // Currency Identification (Requirement 7)
    { CLIP_CURRENCY_500,         "இது 500 ரூபாய்.", "This is 500 Rupees note.", 880 },
    { CLIP_CURRENCY_200,         "இது 200 ரூபாய்.", "This is 200 Rupees note.", 830 },
    { CLIP_CURRENCY_100,         "இது 100 ரூபாய்.", "This is 100 Rupees note.", 784 },
    { CLIP_CURRENCY_50,          "இது 50 ரூபாய்.", "This is 50 Rupees note.", 698 },
    { CLIP_CURRENCY_20,          "இது 20 ரூபாய்.", "This is 20 Rupees note.", 659 },
    { CLIP_CURRENCY_10,          "இது 10 ரூபாய்.", "This is 10 Rupees note.", 587 },
    // User Safe & Connection Status (Requirements 2, 5, 8)
    { CLIP_USER_SAFE,            "பாதுகாப்பாக உள்ளீர்கள். எச்சரிக்கை நிறுத்தப்பட்டது.", "You are safe. Alert stopped.", 523 },
    { CLIP_SYSTEM_CONNECTED,     "அமைப்பு தயார். இணைக்கப்பட்டது.", "System ready and connected.", 659 }
};

static const size_t NUM_TAMIL_CLIPS = sizeof(TAMIL_CLIPS) / sizeof(TAMIL_CLIPS[0]);

const TamilClipMetaData* MAX98357AAudioPlayer::getTamilMetaData(AudioClip clip) {
    for (size_t i = 0; i < NUM_TAMIL_CLIPS; i++) {
        if (TAMIL_CLIPS[i].clip == clip) {
            return &TAMIL_CLIPS[i];
        }
    }
    return nullptr;
}

MAX98357AAudioPlayer::MAX98357AAudioPlayer(uint8_t bclk, uint8_t lrc, uint8_t din)
    : i2sPort(I2S_NUM_0), bclkPin(bclk), lrcPin(lrc), dinPin(din),
      initialized(false), spiffsOk(false), volumePercent(100), playing(false),
      currentClip(CLIP_SYSTEM_READY),
      lastPlayedClip(0), lastPlayedTime(0), playStartTime(0), clipDurationMs(0),
      pendingClip(CLIP_SYSTEM_READY), hasPendingClip(false), pendingIsEmergency(false) {}

MAX98357AAudioPlayer::~MAX98357AAudioPlayer() {
    if (initialized) {
        i2s_driver_uninstall(i2sPort);
    }
}

bool MAX98357AAudioPlayer::begin() {
    Serial.printf("[I2S AUDIO] Initializing MAX98357A I2S Audio Amplifier (BCLK: %u, LRC: %u, DIN: %u)...\n",
                  bclkPin, lrcPin, dinPin);

    i2s_config_t i2sConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = 8000,  // 8 kHz — matches Tamil WAV files in SPIFFS
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 256,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pinConfig = {
        .bck_io_num = bclkPin,
        .ws_io_num = lrcPin,
        .data_out_num = dinPin,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    esp_err_t err = i2s_driver_install(i2sPort, &i2sConfig, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("[I2S ERROR] Failed to install I2S driver: 0x%x\n", err);
        initialized = false;
        return false;
    }

    err = i2s_set_pin(i2sPort, &pinConfig);
    if (err != ESP_OK) {
        Serial.printf("[I2S ERROR] Failed to set I2S pins: 0x%x\n", err);
        i2s_driver_uninstall(i2sPort);
        initialized = false;
        return false;
    }

    i2s_zero_dma_buffer(i2sPort);
    initialized = true;
    Serial.println("[I2S AUDIO] MAX98357A I2S driver successfully initialized.");

    // Mount SPIFFS to access pre-recorded Tamil WAV files
    if (SPIFFS.begin(true)) {
        spiffsOk = true;
        Serial.println("[SPIFFS] Mounted successfully. Real Tamil WAV speech clips available.");
    } else {
        spiffsOk = false;
        Serial.println("[SPIFFS] Mount failed — falling back to synthesized tones.");
    }

    return true;
}

void MAX98357AAudioPlayer::setVolume(uint8_t volume) {
    if (volume > 100) volume = 100;
    volumePercent = volume;
}

void MAX98357AAudioPlayer::stop() {
    if (initialized) {
        i2s_zero_dma_buffer(i2sPort);
    }
    playing = false;
    hasPendingClip = false;
}

bool MAX98357AAudioPlayer::isPlaying() const {
    return playing && ((millis() - playStartTime) < clipDurationMs);
}

void MAX98357AAudioPlayer::writeSineWaveI2S(uint16_t freqHz, uint16_t durationMs, float maxAmplitude) {
    if (!initialized) return;

    const float sampleRate = 8000.0f;
    const float volumeScale = (volumePercent / 100.0f) * maxAmplitude * 32767.0f;
    size_t totalSamples = (size_t)((sampleRate * durationMs) / 1000.0f);

    size_t samplesWritten = 0;
    float phase = 0.0f;
    float phaseInc = (2.0f * M_PI * freqHz) / sampleRate;

    while (samplesWritten < totalSamples) {
        size_t chunkSize = (totalSamples - samplesWritten < DMA_BUF_SIZE / 2) ? 
                            (totalSamples - samplesWritten) : (DMA_BUF_SIZE / 2);

        for (size_t i = 0; i < chunkSize; i++) {
            // Apply envelope (fade in / out to eliminate clicks)
            float envelope = 1.0f;
            size_t sampleIdx = samplesWritten + i;
            if (sampleIdx < 160) {
                envelope = (float)sampleIdx / 160.0f;
            } else if (sampleIdx > totalSamples - 160) {
                envelope = (float)(totalSamples - sampleIdx) / 160.0f;
            }

            int16_t sampleVal = (int16_t)(sinf(phase) * volumeScale * envelope);
            phase += phaseInc;
            if (phase >= 2.0f * M_PI) phase -= 2.0f * M_PI;

            // Stereo channel format (Left = Right)
            sampleBuffer[i * 2] = sampleVal;     // Left channel
            sampleBuffer[i * 2 + 1] = sampleVal; // Right channel
        }

        size_t bytesToWrite = chunkSize * 2 * sizeof(int16_t);
        size_t bytesWritten = 0;
        i2s_write(i2sPort, sampleBuffer, bytesToWrite, &bytesWritten, portMAX_DELAY);
        samplesWritten += chunkSize;
    }
}

void MAX98357AAudioPlayer::writeHarmonicMelodyI2S(const uint16_t freqs[], const uint16_t durationsMs[], size_t count) {
    for (size_t i = 0; i < count; i++) {
        writeSineWaveI2S(freqs[i], durationsMs[i], 0.75f);
    }
}

void MAX98357AAudioPlayer::playTestTone(uint16_t frequencyHz, uint16_t durationMs) {
    Serial.printf("[I2S TEST] 🔊 Playing %u Hz test tone for %u ms over MAX98357A I2S...\n",
                  frequencyHz, durationMs);
    writeSineWaveI2S(frequencyHz, durationMs, 0.85f);
    i2s_zero_dma_buffer(i2sPort);
}

// ---------------------------------------------------------------------------
// SPIFFS WAV Playback — streams a 16kHz / mono / 16-bit PCM WAV to I2S
// Returns true if the file was found and played, false otherwise.
// ---------------------------------------------------------------------------
bool MAX98357AAudioPlayer::playWavFromSpiffs(const char* wavPath) {
    if (!initialized || !spiffsOk) return false;

    File f = SPIFFS.open(wavPath, "r");
    if (!f) {
        Serial.printf("[SPIFFS] WAV not found: %s  (will use tone fallback)\n", wavPath);
        return false;
    }

    // Skip 44-byte standard WAV header
    if (f.size() <= 44) {
        Serial.printf("[SPIFFS] WAV too small: %s\n", wavPath);
        f.close();
        return false;
    }
    f.seek(44);

    Serial.printf("[SPIFFS] 🔊 Speaking Tamil WAV: %s  (%u bytes)\n", wavPath, (unsigned)f.size());

    // Apply 2.5x digital preamp boost to maximize loudness for gTTS speech
    const float DIGITAL_BOOST = 2.5f;
    const float volScale = (volumePercent / 100.0f) * DIGITAL_BOOST;
    const size_t CHUNK = DMA_BUF_SIZE;   // raw int16 samples per chunk
    int16_t readBuf[CHUNK];
    int16_t stereo[CHUNK * 2];           // I2S is configured stereo (L=R)

    unsigned long startMs = millis();

    while (f.available()) {
        size_t bytesRead = f.read((uint8_t*)readBuf, CHUNK * sizeof(int16_t));
        size_t samplesRead = bytesRead / sizeof(int16_t);
        if (samplesRead == 0) break;

        for (size_t i = 0; i < samplesRead; i++) {
            int32_t amplified = (int32_t)(readBuf[i] * volScale);
            // Saturation clamping to prevent integer overflow distortion
            if (amplified > 32767) amplified = 32767;
            else if (amplified < -32768) amplified = -32768;
            int16_t s = (int16_t)amplified;
            stereo[i * 2]     = s;  // Left
            stereo[i * 2 + 1] = s;  // Right
        }

        size_t bytesWritten = 0;
        i2s_write(i2sPort, stereo, samplesRead * 2 * sizeof(int16_t),
                  &bytesWritten, pdMS_TO_TICKS(200));
    }

    f.close();
    clipDurationMs = millis() - startMs;
    i2s_zero_dma_buffer(i2sPort);
    return true;
}

void MAX98357AAudioPlayer::generateAndWriteAudioSequence(AudioClip clip) {
    const TamilClipMetaData* meta = getTamilMetaData(clip);
    if (meta) {
        Serial.println("--------------------------------------------------");
        Serial.printf("🗣 TAMIL VOICE ASSISTANT: \"%s\"\n", meta->tamilText);
        Serial.printf("   [ENGLISH TRANSLATION: \"%s\"]\n", meta->englishTranslation);
        Serial.println("--------------------------------------------------");
    }

    // --- Primary path: play real Tamil speech from SPIFFS WAV ---
    // Filename pattern mirrors the MP3 names: 0001_system_ready.wav etc.
    // Map AudioClip enum value to the known filename.
    static const struct { uint8_t id; const char* wav; } WAV_MAP[] = {
        {  1, "/0001_system_ready.wav"      },
        {  2, "/0002_system_error.wav"       },
        {  3, "/0003_obstacle_front.wav"     },
        {  4, "/0004_dustbin_front.wav"      },
        {  5, "/0005_dog_left.wav"           },
        {  6, "/0006_chair_right.wav"        },
        {  7, "/0007_person_front.wav"       },
        {  8, "/0008_car_front.wav"          },
        {  9, "/0009_table_front.wav"        },
        { 10, "/0010_emergency_fall.wav"     },
        { 11, "/0011_alert_cancelled.wav"    },
        { 12, "/0012_telegram_sent.wav"      },
        { 13, "/0013_obstacle_notice.wav"    },
        { 14, "/0014_obstacle_warning.wav"   },
        { 15, "/0015_person_ahead.wav"       },
        { 16, "/0016_person_left.wav"        },
        { 17, "/0017_person_right.wav"       },
        { 18, "/0018_chair_ahead.wav"        },
        { 19, "/0019_table_ahead.wav"        },
        { 20, "/0020_door_ahead.wav"         },
        { 21, "/0021_stairs_ahead.wav"       },
        { 22, "/0022_wall_ahead.wav"         },
        { 23, "/0023_vehicle_ahead.wav"      },
        { 24, "/0024_medicine_reminder.wav"  },
        { 30, "/0030_medicine_paracetamol.wav" },
        { 31, "/0031_medicine_rantac.wav"    },
        { 32, "/0032_medicine_tassic.wav"    },
        { 33, "/0033_currency_500.wav"       },
        { 34, "/0034_currency_200.wav"       },
        { 35, "/0035_currency_100.wav"       },
        { 36, "/0036_currency_50.wav"        },
        { 37, "/0037_currency_20.wav"        },
        { 38, "/0038_currency_10.wav"        },
        { 39, "/0039_user_safe.wav"          },
        { 40, "/0040_system_connected.wav"   },
    };
    constexpr size_t WAV_MAP_LEN = sizeof(WAV_MAP) / sizeof(WAV_MAP[0]);

    uint8_t clipId = static_cast<uint8_t>(clip);
    for (size_t i = 0; i < WAV_MAP_LEN; i++) {
        if (WAV_MAP[i].id == clipId) {
            if (playWavFromSpiffs(WAV_MAP[i].wav)) {
                return;   // Real speech played — done!
            }
            break;
        }
    }

    // --- Fallback path: synthesize tone melody (no WAV file in SPIFFS) ---
    switch (clip) {
        case CLIP_SYSTEM_READY: {
            uint16_t f[] = {523, 659, 784, 1046};
            uint16_t d[] = {150, 150, 150, 300};
            writeHarmonicMelodyI2S(f, d, 4);
            clipDurationMs = 750;
            break;
        }
        case CLIP_SYSTEM_ERROR: {
            uint16_t f[] = {440, 330};
            uint16_t d[] = {300, 500};
            writeHarmonicMelodyI2S(f, d, 2);
            clipDurationMs = 800;
            break;
        }
        case CLIP_OBSTACLE_FRONT: { // Critical obstacle
            uint16_t f[] = {880, 1046, 880, 1046};
            uint16_t d[] = {150, 150, 150, 250};
            writeHarmonicMelodyI2S(f, d, 4);
            clipDurationMs = 700;
            break;
        }
        case CLIP_OBSTACLE_WARNING: { // Near obstacle proximity hazard: "எச்சரிக்கை! பொருள் அருகில் உள்ளது."
            uint16_t f[] = {880, 1046, 880, 1046, 880};
            uint16_t d[] = {150, 150, 150, 150, 250};
            writeHarmonicMelodyI2S(f, d, 5);
            clipDurationMs = 850;
            break;
        }
        case CLIP_DUSTBIN_FRONT: {
            uint16_t f[] = {659, 587, 659};
            uint16_t d[] = {200, 200, 300};
            writeHarmonicMelodyI2S(f, d, 3);
            clipDurationMs = 700;
            break;
        }
        case CLIP_DOG_LEFT: {
            uint16_t f[] = {698, 784, 698};
            uint16_t d[] = {200, 200, 300};
            writeHarmonicMelodyI2S(f, d, 3);
            clipDurationMs = 700;
            break;
        }
        case CLIP_CHAIR_RIGHT: {
            uint16_t f[] = {784, 698, 784};
            uint16_t d[] = {200, 200, 300};
            writeHarmonicMelodyI2S(f, d, 3);
            clipDurationMs = 700;
            break;
        }
        case CLIP_PERSON_FRONT: {
            uint16_t f[] = {587, 659, 587};
            uint16_t d[] = {200, 200, 300};
            writeHarmonicMelodyI2S(f, d, 3);
            clipDurationMs = 700;
            break;
        }
        case CLIP_CAR_FRONT: {
            uint16_t f[] = {987, 880, 987};
            uint16_t d[] = {200, 200, 400};
            writeHarmonicMelodyI2S(f, d, 3);
            clipDurationMs = 800;
            break;
        }
        case CLIP_EMERGENCY_FALL: { // Siren alarm sequence
            uint16_t f[] = {1046, 784, 1046, 784, 1046};
            uint16_t d[] = {250, 250, 250, 250, 400};
            writeHarmonicMelodyI2S(f, d, 5);
            clipDurationMs = 1400;
            break;
        }
        case CLIP_ALERT_CANCELLED: {
            uint16_t f[] = {587, 493, 440};
            uint16_t d[] = {200, 200, 400};
            writeHarmonicMelodyI2S(f, d, 3);
            clipDurationMs = 800;
            break;
        }
        case CLIP_TELEGRAM_SENT: {
            uint16_t f[] = {740, 880, 1046};
            uint16_t d[] = {200, 200, 300};
            writeHarmonicMelodyI2S(f, d, 3);
            clipDurationMs = 700;
            break;
        }
        case CLIP_MEDICINE_REMINDER: { // Distinct multi-chime reminder melody
            uint16_t f[] = {523, 659, 784, 659, 784, 1046};
            uint16_t d[] = {250, 250, 250, 250, 250, 500};
            writeHarmonicMelodyI2S(f, d, 6);
            clipDurationMs = 1750;
            break;
        }
        case CLIP_MEDICINE_PARACETAMOL:
        case CLIP_MEDICINE_RANTAC:
        case CLIP_MEDICINE_TASSIC: {
            uint16_t f[] = {659, 784, 987, 880};
            uint16_t d[] = {200, 200, 250, 350};
            writeHarmonicMelodyI2S(f, d, 4);
            clipDurationMs = 1000;
            break;
        }
        case CLIP_CURRENCY_500:
        case CLIP_CURRENCY_200:
        case CLIP_CURRENCY_100:
        case CLIP_CURRENCY_50:
        case CLIP_CURRENCY_20:
        case CLIP_CURRENCY_10: {
            uint16_t f[] = {784, 880, 1046, 1175};
            uint16_t d[] = {150, 150, 200, 300};
            writeHarmonicMelodyI2S(f, d, 4);
            clipDurationMs = 800;
            break;
        }
        case CLIP_USER_SAFE: {
            uint16_t f[] = {440, 523, 659, 880};
            uint16_t d[] = {200, 200, 250, 400};
            writeHarmonicMelodyI2S(f, d, 4);
            clipDurationMs = 1050;
            break;
        }
        case CLIP_SYSTEM_CONNECTED: {
            uint16_t f[] = {523, 659, 784, 1046};
            uint16_t d[] = {150, 150, 150, 350};
            writeHarmonicMelodyI2S(f, d, 4);
            clipDurationMs = 800;
            break;
        }
        default: {
            uint16_t base = meta ? meta->baseToneHz : 440;
            writeSineWaveI2S(base, 600, 0.75f);
            clipDurationMs = 600;
            break;
        }
    }

    i2s_zero_dma_buffer(i2sPort);
}

void MAX98357AAudioPlayer::playClip(AudioClip clip, bool isEmergency) {
    playClipIndex(static_cast<uint16_t>(clip), isEmergency);
}

void MAX98357AAudioPlayer::playTamilText(const char* tamilText, bool isEmergency) {
    Serial.println("--------------------------------------------------");
    Serial.printf("🗣 LIVE TAMIL TTS ANNOUNCEMENT: \"%s\"\n", tamilText);
    Serial.println("--------------------------------------------------");

    if (tamilText != nullptr && strlen(tamilText) > 0) {
        // First check if it matches a known Tamil clip in the metadata table
        for (size_t i = 0; i < NUM_TAMIL_CLIPS; i++) {
            if (strstr(tamilText, TAMIL_CLIPS[i].tamilText) != nullptr ||
                strstr(TAMIL_CLIPS[i].tamilText, tamilText) != nullptr) {
                playClip(TAMIL_CLIPS[i].clip, isEmergency);
                return;
            }
        }

        // Check if warning keyword is present
        if (strstr(tamilText, "எச்சரிக்கை") != nullptr) {
            playClip(CLIP_OBSTACLE_WARNING, isEmergency);
            return;
        }
    }

    // Fallback: If no WAV match found in table, synthesize tone
    if (isEmergency) {
        uint16_t f[] = {880, 1046, 880, 1046, 880};
        uint16_t d[] = {120, 120, 120, 120, 250};
        writeHarmonicMelodyI2S(f, d, 5);
        clipDurationMs = 750;
    } else {
        writeSineWaveI2S(659, 150, 0.7f);
        writeSineWaveI2S(880, 250, 0.8f);
        clipDurationMs = 600;
    }
    i2s_zero_dma_buffer(i2sPort);
    playStartTime = millis();
    playing = true;
}

void MAX98357AAudioPlayer::playClipIndex(uint16_t clipIndex, bool isEmergency) {
    AudioClip clip = static_cast<AudioClip>(clipIndex);
    unsigned long now = millis();

    // Debounce non-emergency duplicate clips
    if (!isEmergency && clipIndex == lastPlayedClip) {
        if (now - lastPlayedTime < AUDIO_REPEAT_DEBOUNCE_MS) {
            return;
        }
    }

    if (isEmergency) {
        Serial.printf("[I2S AUDIO EMERGENCY] Interrupting for clip %u\n", clipIndex);
        stop();
        currentClip = clip;
        lastPlayedClip = clipIndex;
        lastPlayedTime = now;
        playStartTime = now;
        playing = true;
        generateAndWriteAudioSequence(clip);
    } else {
        if (!isPlaying()) {
            currentClip = clip;
            lastPlayedClip = clipIndex;
            lastPlayedTime = now;
            playStartTime = now;
            playing = true;
            generateAndWriteAudioSequence(clip);
        } else {
            pendingClip = clip;
            pendingIsEmergency = false;
            hasPendingClip = true;
        }
    }
}

void MAX98357AAudioPlayer::update() {
    if (playing && ((millis() - playStartTime) >= clipDurationMs)) {
        playing = false;
    }

    if (hasPendingClip && !isPlaying()) {
        AudioClip clipToPlay = pendingClip;
        bool isEmerg = pendingIsEmergency;
        hasPendingClip = false;
        playClip(clipToPlay, isEmerg);
    }
}
