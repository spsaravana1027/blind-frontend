#ifndef ULTRASONIC_H
#define ULTRASONIC_H

#include <Arduino.h>
#include "config.h"

#define MEDIAN_SAMPLE_SIZE 5

class UltrasonicSensor {
private:
    uint8_t trigPin;
    uint8_t echoPin;
    float samples[MEDIAN_SAMPLE_SIZE];
    uint8_t sampleIndex;
    unsigned long lastMeasureTime;
    float lastMedianDistance;
    bool simulatedMode;
    float simulatedDistance;

public:
    UltrasonicSensor(uint8_t trig = PIN_ULTRASONIC_TRIG, uint8_t echo = PIN_ULTRASONIC_ECHO);
    void begin();
    void update();
    float getDistanceCm();
    void injectSimulatedDistance(float distCm);
    
    // Convenience threshold checks
    bool isUrgent() const { return lastMedianDistance > 0 && lastMedianDistance <= DIST_URGENT_CM; }
    bool isWarning() const { return lastMedianDistance > DIST_URGENT_CM && lastMedianDistance <= DIST_WARNING_CM; }
    bool isNotice() const { return lastMedianDistance > DIST_WARNING_CM && lastMedianDistance <= DIST_NOTICE_CM; }
    bool isClear() const { return lastMedianDistance > DIST_MAX_CLEAR_CM || lastMedianDistance <= 0; }

    // Triggered distance calculation upon vision obstacle detection (Requirement 3)
    float measureImmediateDistance();
    float triggerDistanceCalculation() { return measureImmediateDistance(); }

private:
    float measureRawDistance();
    float computeMedian();
};

#endif // ULTRASONIC_H
