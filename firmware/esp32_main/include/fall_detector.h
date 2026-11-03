#ifndef FALL_DETECTOR_H
#define FALL_DETECTOR_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "config.h"

enum InternalFallStage {
    FALL_STAGE_IDLE,
    FALL_STAGE_FREEFALL_DETECTED,
    FALL_STAGE_IMPACT_DETECTED,
    FALL_STAGE_CHECKING_INACTIVITY
};

class FallDetector {
private:
    Adafruit_MPU6050 mpu;
    bool mpuInitialized;
    unsigned long lastSampleTime;

    // Filtered / Current values
    float accelMagG;
    float gyroMagDegSec;
    float tiltAngleDeg;
    
    // Baseline calibration offsets
    float axOffset, ayOffset, azOffset;

    // Internal state tracking
    InternalFallStage currentStage;
    unsigned long freefallTime;
    unsigned long impactTime;
    unsigned long inactivityStartTime;

    bool fallEventDetected;
    bool simulatedMode;

public:
    FallDetector();
    bool begin();
    void update();
    bool isFallDetected();
    void clearFallEvent();
    void injectSimulatedFall();

    // Diagnostics / Status getter
    float getAccelMagG() const { return accelMagG; }
    float getTiltAngleDeg() const { return tiltAngleDeg; }
    InternalFallStage getStage() const { return currentStage; }
    bool isMpuWorking() const { return mpuInitialized; }

private:
    void processSensorData(float ax, float ay, float az, float gx, float gy, float gz);
};

#endif // FALL_DETECTOR_H
