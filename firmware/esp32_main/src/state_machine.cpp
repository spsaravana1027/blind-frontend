#include "state_machine.h"

SystemController::SystemController()
    : currentState(SYSTEM_STATE_STARTUP), stateStartTime(0),
      lastCountdownBeepTime(0), remainingSeconds(FALL_CANCEL_WINDOW_SEC),
      buttonPin(PIN_CANCEL_BUTTON), lastButtonState(HIGH), debouncedButtonState(HIGH),
      lastDebounceTime(0),
      medicineReminderEnabled(true), medicineTestMode(false),
      lastMedicineReminderTime(0), medicineReminderActive(false),
      ntpSynced(false), lastNtpCheckTime(0) {}

void SystemController::begin() {
    Serial.println("\n==================================================");
    Serial.println("   ASSISTIVE DEVICE FOR VISUALLY IMPAIRED PEOPLE");
    Serial.println("   TAMIL AI VOICE ASSISTANT (CAMERA & SENSORS)");
    Serial.println("==================================================");

    pinMode(buttonPin, INPUT_PULLUP);

    // Initialize all hardware subsystems
    buzzer.begin();
    audio.begin();
    distanceSensor.begin();
    fallSensor.begin();
    vision.begin();
    telegram.begin();

    // Set initial medicine reminder timestamp so first reminder occurs after interval
    lastMedicineReminderTime = millis();

    // Start startup sequence
    currentState = SYSTEM_STATE_STARTUP;
    stateStartTime = millis();
    
    // Startup self-test complete (Quiet startup: speaker only speaks on obstacle detection)
    Serial.println("[SYSTEM] Startup self-test complete. System ready.");
}

void SystemController::syncNtpTime() {
    if (telegram.isWifiConnected()) {
        if (!ntpSynced || (millis() - lastNtpCheckTime > 3600000UL)) { // Sync every 1 hour
            Serial.println("[NTP TIME] Synchronizing time with NTP servers (Asia/Kolkata)...");
            configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER_PRIMARY, NTP_SERVER_SECONDARY);
            
            struct tm timeinfo;
            if (getLocalTime(&timeinfo, 2000)) {
                ntpSynced = true;
                lastNtpCheckTime = millis();
                char timeStr[64];
                strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S IST", &timeinfo);
                Serial.printf("[NTP TIME SUCCESS] Clock synchronized: %s\n", timeStr);
            } else {
                Serial.println("[NTP TIME NOTICE] NTP sync timeout. Continuing with millis() elapsed timer.");
            }
        }
    }
}

String SystemController::getFormattedLocalTime() {
    if (ntpSynced) {
        struct tm timeinfo;
        if (getLocalTime(&timeinfo, 50)) {
            char timeStr[64];
            strftime(timeStr, sizeof(timeStr), "%H:%M:%S", &timeinfo);
            return String(timeStr);
        }
    }
    // Fallback to formatted elapsed time
    unsigned long sec = millis() / 1000;
    unsigned long hrs = sec / 3600;
    unsigned long mins = (sec % 3600) / 60;
    sec = sec % 60;
    char buf[32];
    snprintf(buf, sizeof(buf), "+%02lu:%02lu:%02lu", hrs, mins, sec);
    return String(buf);
}

void SystemController::updateMedicineReminder() {
    if (!medicineReminderEnabled) return;

    unsigned long interval = getMedicineReminderInterval();
    unsigned long now = millis();

    if (now - lastMedicineReminderTime >= interval) {
        lastMedicineReminderTime = now;
        playMedicineReminder();
    }
}

void SystemController::playMedicineReminder() {
    medicineReminderActive = true;
    String timeStr = getFormattedLocalTime();
    
    Serial.println("\n==================================================");
    Serial.printf("⏰ MEDICINE REMINDER DUE! [%s]\n", timeStr.c_str());
    Serial.println("🗣 TAMIL VOICE: \"மருந்து எடுத்துக்கொள்ள வேண்டிய நேரம் வந்துவிட்டது. தயவுசெய்து உங்கள் மருந்தை எடுத்துக்கொள்ளுங்கள்.\"");
    Serial.println("   (English: \"It is time to take your medicine. Please take your medicine.\")");
    Serial.println("==================================================\n");

    // Play medicine reminder speech clip over MAX98357A I2S amplifier
    audio.playClip(CLIP_MEDICINE_REMINDER, true);
}

void SystemController::stopMedicineReminder() {
    if (medicineReminderActive) {
        medicineReminderActive = false;
        audio.stop();
        Serial.println("[MEDICINE REMINDER] Audio reminder stopped by user button press.");
    }
}

void SystemController::setMedicineReminderEnabled(bool enabled) {
    medicineReminderEnabled = enabled;
    lastMedicineReminderTime = millis(); // Reset interval start time
    Serial.printf("[MEDICINE REMINDER] Reminder feature %s. First reminder in %lu minutes.\n",
                  enabled ? "ENABLED" : "DISABLED",
                  getMedicineReminderInterval() / (60 * 1000UL));
}

void SystemController::setMedicineTestMode(bool enabled) {
    medicineTestMode = enabled;
    lastMedicineReminderTime = millis(); // Reset interval start time
    Serial.printf("[MEDICINE REMINDER] Quick test mode (1-min interval) %s.\n",
                  enabled ? "ACTIVATED" : "DEACTIVATED");
}

void SystemController::updateButton() {
    bool reading = digitalRead(buttonPin);
    if (reading != lastButtonState) {
        lastDebounceTime = millis();
        lastButtonState = reading;
    }

    if ((millis() - lastDebounceTime) > 50) { // 50ms stable debounce window
        if (reading != debouncedButtonState) {
            debouncedButtonState = reading;
            // Only trigger on Falling Edge (HIGH -> LOW press)
            if (debouncedButtonState == LOW) {
                if (currentState == SYSTEM_STATE_FALL_COUNTDOWN || currentState == SYSTEM_STATE_EMERGENCY_ALERT) {
                    triggerSimulatedCancel();
                } else if (medicineReminderActive || (audio.isPlaying() && currentState == SYSTEM_STATE_MONITORING)) {
                    stopMedicineReminder();
                }
            }
        }
    }
}

void SystemController::processStartupState() {
    if (millis() - stateStartTime >= 2500) {
        currentState = SYSTEM_STATE_MONITORING;
        stateStartTime = millis();
        Serial.println("[SYSTEM STATE] Transitioned to MONITORING state.");
        // Requirement 2: Speaker plays ready and connected confirmation after connection
        audio.playClip(CLIP_SYSTEM_CONNECTED, true);
    }
}

void SystemController::handleDistanceWarnings() {
    // Requirement 2: It does NOT sound the buzzer for obstacles.
    // Ultrasonic sensor calculates distance. Buzzer is strictly reserved for emergency fall down.
    float dist = distanceSensor.getDistanceCm();

    // If an alert was not actively running, ensure buzzer remains off
    if (currentState == SYSTEM_STATE_MONITORING && !fallSensor.isFallDetected()) {
        if (buzzer.isAlerting()) buzzer.stop();
    }
}

void SystemController::handleVisionWarnings() {
    // Requirement 3: If webcam/camera captures image, ultrasonic sensor calculates distance.
    // If distance of obstacle is near (<= 50cm), speaker speaks "எச்சரிக்கை! பொருள் அருகில் உள்ளது."
    // Requirement 6 & 7: Camera identifies medicines and currency in Tamil speech.
    if (vision.hasDetection()) {
        VisionDetection det = vision.getLatestDetection();
        // Requirement 3: If webcam/camera captures image, ultrasonic sensor starts to calculate distance immediately
        float dist = distanceSensor.measureImmediateDistance();
        String lbl = String(det.label);
        lbl.toLowerCase();

        // 1. Medicines & Currency Identification (Req 6 & 7)
        bool isMedicineOrCurrency = (lbl.indexOf("500") != -1 || lbl.indexOf("200") != -1 ||
                                     lbl.indexOf("100") != -1 || lbl.indexOf("50") != -1 ||
                                     lbl.indexOf("20") != -1  || lbl.indexOf("10") != -1 ||
                                     lbl.indexOf("paracetamol") != -1 || lbl.indexOf("paracetomal") != -1 ||
                                     lbl.indexOf("rantac") != -1 || lbl.indexOf("tassic") != -1 ||
                                     lbl.indexOf("tanic") != -1  || lbl.indexOf("tonic") != -1 ||
                                     lbl.indexOf("medicine") != -1 || lbl.indexOf("tablet") != -1);

        if (isMedicineOrCurrency) {
            if (det.clipId > 0) {
                audio.playClip(static_cast<AudioClip>(det.clipId), false);
            } else if (strlen(det.tamilText) > 0) {
                audio.playTamilText(det.tamilText, false);
            } else {
                AudioClip clip = VisionLink::mapDetectionToAudioClip(det.label, det.position);
                audio.playClip(clip, false);
            }
            return;
        }

        // 2. Obstacle navigation and distance assessment (Req 3)
        // If distance of obstacle captured by webcam is near (<= 50 cm), speaker speaks based on situation:
        // E.g.: "எச்சரிக்கை! பொருள் அருகில் உள்ளது." + situation description
        AudioClip targetClip = (det.clipId > 0) ? static_cast<AudioClip>(det.clipId) : VisionLink::mapDetectionToAudioClip(det.label, det.position);

        if (dist > 0 && dist <= DIST_CRITICAL_CM) {
            Serial.printf("[OBSTACLE NEAR ALERT] Camera captured '%s', ultrasonic measured %.1f cm (NEAR!)\n",
                          det.label, dist);
            // Play critical proximity warning: "எச்சரிக்கை! பொருள் அருகில் உள்ளது." (0014_obstacle_warning.wav)
            audio.playClip(CLIP_OBSTACLE_WARNING, true);
        } else {
            // General obstacle notice or warning zone: play the identified object WAV clip
            audio.playClip(targetClip, false);
        }
    }
}

void SystemController::processMonitoringState() {
    // 1. Requirement 4: If person falls down, IMMEDIATELY buzzer and send Telegram alert
    if (fallSensor.isFallDetected()) {
        fallSensor.clearFallEvent();
        currentState = SYSTEM_STATE_EMERGENCY_ALERT;
        stateStartTime = millis();

        Serial.println("==================================================");
        Serial.println("🚨 FALL DETECTED! IMMEDIATELY ACTIVATING BUZZER & SENDING TELEGRAM ALERT");
        Serial.println("==================================================");

        // Immediately start buzzer
        buzzer.setPattern(BUZZER_EMERGENCY_ALARM);
        // Immediately speak emergency prompt
        audio.playClip(CLIP_EMERGENCY_FALL, true);
        // Immediately dispatch alert to Telegram guardian
        telegram.queueEmergencyAlert("Assistive_Device_01", "User has fallen down! Please assist immediately.");
        return;
    }

    // 2. Ultrasonic distance monitoring
    handleDistanceWarnings();

    // 3. Vision detection & distance coordination
    handleVisionWarnings();

    // 4. Medicine reminder monitoring
    updateMedicineReminder();
}

void SystemController::processFallCountdownState() {
    // Maintained for backward compatibility; falls transition directly to EMERGENCY_ALERT
    currentState = SYSTEM_STATE_EMERGENCY_ALERT;
}

void SystemController::processEmergencyAlertState() {
    buzzer.setPattern(BUZZER_EMERGENCY_ALARM);
}

void SystemController::triggerSimulatedFall() {
    fallSensor.injectSimulatedFall();
}

void SystemController::triggerSimulatedCancel() {
    // Requirements 5 & 8: If person became safe, click switch to off buzzer and send safe Telegram message
    if (currentState == SYSTEM_STATE_EMERGENCY_ALERT || currentState == SYSTEM_STATE_FALL_COUNTDOWN) {
        Serial.println("==================================================");
        Serial.println("✅ SAFE SWITCH CLICKED: BUZZER STOPPED & DISPATCHING SAFE TELEGRAM MESSAGE");
        Serial.println("==================================================");

        currentState = SYSTEM_STATE_MONITORING;
        // Requirement 5: Stop sounding the buzzer
        buzzer.stop();
        // Speaker informs the user they are safe
        audio.playClip(CLIP_USER_SAFE, true);
        // Requirement 8: Send message to the guardian that he/she is safe
        telegram.queueSafeMessage("User is safe. Emergency buzzer turned off.");
    } else if (medicineReminderActive) {
        stopMedicineReminder();
    } else {
        Serial.println("[SYSTEM] Safe switch pressed, system in normal monitoring state.");
    }
}

void SystemController::triggerSimulatedObject(const char* label, const char* pos, const char* tamilText) {
    vision.injectSimulatedObject(label, 0.95f, pos, tamilText);
}

void SystemController::triggerSimulatedDistance(float distCm) {
    distanceSensor.injectSimulatedDistance(distCm);
}

void SystemController::triggerI2SAudioTest(uint16_t freqHz, uint16_t durationMs) {
    audio.playTestTone(freqHz, durationMs);
}

void SystemController::playClipById(uint16_t clipId, bool isEmergency) {
    audio.playClipIndex(clipId, isEmergency);
}

void SystemController::processProtocolLine(const String& line) {
    vision.parseProtocolLine(line);
}

void SystemController::printStatus() {
    Serial.println("\n----------------- SYSTEM DIAGNOSTICS -----------------");
    Serial.printf("Current State        : %s\n",
                  currentState == SYSTEM_STATE_STARTUP ? "STARTUP" :
                  currentState == SYSTEM_STATE_MONITORING ? "MONITORING" :
                  currentState == SYSTEM_STATE_FALL_COUNTDOWN ? "FALL COUNTDOWN" : "EMERGENCY ALERT");
    Serial.printf("System Local Time    : %s (NTP Synced: %s)\n", getFormattedLocalTime().c_str(), ntpSynced ? "YES" : "NO");
    Serial.printf("Medicine Reminder    : %s (Interval: %lu min, Next due in %lu sec)\n",
                  medicineReminderEnabled ? "ENABLED" : "DISABLED",
                  getMedicineReminderInterval() / (60 * 1000UL),
                  (getMedicineReminderInterval() - (millis() - lastMedicineReminderTime)) / 1000UL);
    Serial.printf("Wi-Fi Connected      : %s\n", telegram.isWifiConnected() ? "YES" : "NO");
    Serial.printf("Telegram Pending Q   : %u messages\n", telegram.getPendingQueueCount());
    Serial.printf("Ultrasonic Distance  : %.1f cm\n", distanceSensor.getDistanceCm());
    Serial.printf("MPU Accel Mag        : %.2f g\n", fallSensor.getAccelMagG());
    Serial.printf("MPU Tilt Angle       : %.1f deg\n", fallSensor.getTiltAngleDeg());
    Serial.printf("MAX98357A I2S Status : %s\n", audio.isInitialized() ? "INITIALIZED" : "ERROR");
    Serial.println("------------------------------------------------------\n");
}

void SystemController::update() {
    // 1. Update button input
    updateButton();

    // 2. Sync NTP time if Wi-Fi available
    syncNtpTime();

    // 3. Update hardware subsystems
    buzzer.update();
    audio.update();
    distanceSensor.update();
    fallSensor.update();
    vision.update();
    telegram.update();

    // 4. Process current state logic
    switch (currentState) {
        case SYSTEM_STATE_STARTUP:
            processStartupState();
            break;

        case SYSTEM_STATE_MONITORING:
            processMonitoringState();
            break;

        case SYSTEM_STATE_FALL_COUNTDOWN:
            processFallCountdownState();
            break;

        case SYSTEM_STATE_EMERGENCY_ALERT:
            processEmergencyAlertState();
            break;
    }
}
