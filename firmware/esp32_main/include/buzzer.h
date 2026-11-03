#ifndef BUZZER_H
#define BUZZER_H

#include <Arduino.h>
#include "config.h"

enum BuzzerPattern {
    BUZZER_OFF,
    BUZZER_SHORT_BEEP,
    BUZZER_DOUBLE_BEEP,
    BUZZER_EMERGENCY_ALARM,
    BUZZER_URGENT_WARNING
};

class BuzzerController {
private:
    uint8_t pin;
    BuzzerPattern currentPattern;
    unsigned long patternStartTime;
    unsigned long lastToggleTime;
    bool buzzerState;
    uint16_t beepCount;

public:
    BuzzerController(uint8_t buzzerPin = PIN_BUZZER);
    void begin();
    void setPattern(BuzzerPattern pattern);
    void stop();
    void update();
    bool isAlerting() const;
};

#endif // BUZZER_H
