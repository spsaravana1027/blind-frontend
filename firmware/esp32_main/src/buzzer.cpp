#include "buzzer.h"

BuzzerController::BuzzerController(uint8_t buzzerPin)
    : pin(buzzerPin), currentPattern(BUZZER_OFF), patternStartTime(0),
      lastToggleTime(0), buzzerState(false), beepCount(0) {}

void BuzzerController::begin() {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
    currentPattern = BUZZER_OFF;
    buzzerState = false;
}

void BuzzerController::setPattern(BuzzerPattern pattern) {
    if (currentPattern == pattern) return;
    currentPattern = pattern;
    patternStartTime = millis();
    lastToggleTime = millis();
    buzzerState = false;
    beepCount = 0;
    digitalWrite(pin, LOW);
}

void BuzzerController::stop() {
    setPattern(BUZZER_OFF);
}

bool BuzzerController::isAlerting() const {
    return currentPattern == BUZZER_EMERGENCY_ALARM || currentPattern == BUZZER_URGENT_WARNING;
}

void BuzzerController::update() {
    unsigned long now = millis();

    switch (currentPattern) {
        case BUZZER_OFF:
            if (buzzerState) {
                buzzerState = false;
                digitalWrite(pin, LOW);
            }
            break;

        case BUZZER_SHORT_BEEP:
            if (now - patternStartTime < 150) {
                if (!buzzerState) {
                    buzzerState = true;
                    digitalWrite(pin, HIGH);
                }
            } else {
                buzzerState = false;
                digitalWrite(pin, LOW);
                currentPattern = BUZZER_OFF;
            }
            break;

        case BUZZER_DOUBLE_BEEP:
            if (now - patternStartTime < 120) {
                digitalWrite(pin, HIGH);
            } else if (now - patternStartTime < 240) {
                digitalWrite(pin, LOW);
            } else if (now - patternStartTime < 360) {
                digitalWrite(pin, HIGH);
            } else {
                digitalWrite(pin, LOW);
                currentPattern = BUZZER_OFF;
            }
            break;

        case BUZZER_URGENT_WARNING:
            // Continuous fast beep 100ms ON, 100ms OFF
            if (now - lastToggleTime >= 100) {
                lastToggleTime = now;
                buzzerState = !buzzerState;
                digitalWrite(pin, buzzerState ? HIGH : LOW);
            }
            break;

        case BUZZER_EMERGENCY_ALARM:
            // Siren pattern: 300ms ON, 150ms OFF
            if (now - lastToggleTime >= (buzzerState ? 300 : 150)) {
                lastToggleTime = now;
                buzzerState = !buzzerState;
                digitalWrite(pin, buzzerState ? HIGH : LOW);
            }
            break;
    }
}
