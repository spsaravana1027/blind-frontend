#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <Arduino.h>
#include <time.h>
#include "config.h"
#include "buzzer.h"
#include "audio_player.h"
#include "ultrasonic.h"
#include "fall_detector.h"
#include "vision_link.h"
#include "telegram_client.h"

enum SystemState {
    SYSTEM_STATE_STARTUP,
    SYSTEM_STATE_MONITORING,
    SYSTEM_STATE_FALL_COUNTDOWN,
    SYSTEM_STATE_EMERGENCY_ALERT
};

class SystemController {
private:
    SystemState currentState;
    
    // Subsystem references
    BuzzerController buzzer;
    MAX98357AAudioPlayer audio;
    UltrasonicSensor distanceSensor;
    FallDetector fallSensor;
    VisionLink vision;
    TelegramNotifier telegram;

    // Countdown / Timing state
    unsigned long stateStartTime;
    unsigned long lastCountdownBeepTime;
    uint8_t remainingSeconds;

    // Push button debounce
    uint8_t buttonPin;
    bool lastButtonState;
    bool debouncedButtonState;
    unsigned long lastDebounceTime;

    // Medicine Reminder State
    bool medicineReminderEnabled;
    bool medicineTestMode;
    unsigned long lastMedicineReminderTime;
    bool medicineReminderActive;
    
    // NTP Timekeeping State
    bool ntpSynced;
    unsigned long lastNtpCheckTime;

public:
    SystemController();
    void begin();
    void update();

    // Medicine Reminder Interface (per Prompt Requirements)
    void updateMedicineReminder();
    void playMedicineReminder();
    void stopMedicineReminder();
    void setMedicineReminderEnabled(bool enabled);
    void setMedicineTestMode(bool enabled);
    bool isMedicineReminderEnabled() const { return medicineReminderEnabled; }
    bool isMedicineTestMode() const { return medicineTestMode; }
    unsigned long getMedicineReminderInterval() const {
        return medicineTestMode ? MEDICINE_REMINDER_TEST_INTERVAL_MS : MEDICINE_REMINDER_DEFAULT_INTERVAL_MS;
    }

    // Timekeeping & NTP
    void syncNtpTime();
    String getFormattedLocalTime();

    // Command injections for Serial testing / simulation
    void triggerSimulatedFall();
    void triggerSimulatedCancel();
    void triggerSimulatedObject(const char* label, const char* pos = "center", const char* tamilText = "");
    void triggerSimulatedDistance(float distCm);
    void triggerI2SAudioTest(uint16_t freqHz = 440, uint16_t durationMs = 1000);
    void playClipById(uint16_t clipId, bool isEmergency = false);
    void processProtocolLine(const String& line);
    void printStatus();

private:
    void updateButton();
    void processStartupState();
    void processMonitoringState();
    void processFallCountdownState();
    void processEmergencyAlertState();
    
    void handleDistanceWarnings();
    void handleVisionWarnings();
};

#endif // STATE_MACHINE_H
