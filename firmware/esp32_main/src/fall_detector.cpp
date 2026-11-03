#include "fall_detector.h"
#include <cmath>

FallDetector::FallDetector()
    : mpuInitialized(false), lastSampleTime(0),
      accelMagG(1.0f), gyroMagDegSec(0.0f), tiltAngleDeg(0.0f),
      axOffset(0.0f), ayOffset(0.0f), azOffset(0.0f),
      currentStage(FALL_STAGE_IDLE), freefallTime(0),
      impactTime(0), inactivityStartTime(0),
      fallEventDetected(false), simulatedMode(false) {}

bool FallDetector::begin() {
    Serial.println("[MPU6050] Initializing MPU6050 on I2C (SDA: 21, SCL: 22)...");
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setTimeOut(50); // Prevent infinite I2C lockups if MPU is disconnected or wires are loose
    
    // Quick non-blocking bus scan at addresses 0x68 and 0x69
    uint8_t mpuAddr = 0;
    Wire.beginTransmission(0x68);
    if (Wire.endTransmission() == 0) {
        mpuAddr = 0x68;
    } else {
        Wire.beginTransmission(0x69);
        if (Wire.endTransmission() == 0) {
            mpuAddr = 0x69;
        }
    }

    if (mpuAddr == 0 || !mpu.begin(mpuAddr, &Wire)) {
        Serial.println("[MPU6050 NOTICE] MPU6050 sensor not detected on I2C bus (simulated fallback enabled).");
        mpuInitialized = false;
        return false;
    }

    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

    mpuInitialized = true;
    Serial.printf("[MPU6050] MPU6050 successfully initialized at 0x%02X.\n", mpuAddr);
    return true;
}

void FallDetector::injectSimulatedFall() {
    Serial.println("[FALL SIMULATION] 💥 Injecting simulated fall event!");
    fallEventDetected = true;
    currentStage = FALL_STAGE_IDLE;
}

void FallDetector::processSensorData(float ax, float ay, float az, float gx, float gy, float gz) {
    // 1. Compute total acceleration magnitude in G (9.81 m/s^2)
    accelMagG = sqrt(ax * ax + ay * ay + az * az) / 9.81f;

    // 2. Compute gyro angular velocity magnitude in deg/s
    gyroMagDegSec = (sqrt(gx * gx + gy * gy + gz * gz) * 180.0f) / M_PI;

    // 3. Compute tilt angle relative to upright vertical (Z-axis gravity)
    float cosTilt = az / (sqrt(ax * ax + ay * ay + az * az) + 0.0001f);
    cosTilt = constrain(cosTilt, -1.0f, 1.0f);
    tiltAngleDeg = acos(cosTilt) * 180.0f / M_PI;

    unsigned long now = millis();

    // Multi-Stage Fall Algorithm State Machine
    switch (currentStage) {
        case FALL_STAGE_IDLE:
            // Stage 1: Check for Free-Fall (< 0.45g)
            if (accelMagG < FALL_FREE_FALL_THRES_G) {
                currentStage = FALL_STAGE_FREEFALL_DETECTED;
                freefallTime = now;
                Serial.printf("[FALL ALGORITHM] Stage 1: Free-fall detected! Accel: %.2fg\n", accelMagG);
            }
            break;

        case FALL_STAGE_FREEFALL_DETECTED:
            // Stage 2: Check for Impact (> 2.50g) within 400ms of freefall
            if (now - freefallTime <= 400) {
                if (accelMagG > FALL_IMPACT_THRES_G) {
                    currentStage = FALL_STAGE_IMPACT_DETECTED;
                    impactTime = now;
                    Serial.printf("[FALL ALGORITHM] Stage 2: Impact spike detected! Accel: %.2fg\n", accelMagG);
                }
            } else {
                // Timeout: false alarm free-fall (e.g. slight drop or movement)
                currentStage = FALL_STAGE_IDLE;
            }
            break;

        case FALL_STAGE_IMPACT_DETECTED:
            // Stage 3: Check for Tilt (> 60 degrees) within 500ms of impact
            if (now - impactTime <= 500) {
                if (tiltAngleDeg > FALL_TILT_THRES_DEG) {
                    currentStage = FALL_STAGE_CHECKING_INACTIVITY;
                    inactivityStartTime = now;
                    Serial.printf("[FALL ALGORITHM] Stage 3: Tilt confirmed (%.1f deg). Checking inactivity...\n", tiltAngleDeg);
                }
            } else {
                // Impact without tilt (e.g., jumping or dropping an object)
                currentStage = FALL_STAGE_IDLE;
            }
            break;

        case FALL_STAGE_CHECKING_INACTIVITY:
            // Stage 4: Post-impact inactivity (user lying flat/immobile for ~1.2 seconds)
            if (now - inactivityStartTime >= FALL_INACTIVITY_TIME_MS) {
                if (accelMagG >= 0.7f && accelMagG <= 1.3f && gyroMagDegSec < 25.0f) {
                    Serial.println("[FALL ALGORITHM] Stage 4: Inactivity confirmed! FALL DETECTED!");
                    fallEventDetected = true;
                } else {
                    Serial.println("[FALL ALGORITHM] Motion detected post-impact. Fall invalidated.");
                }
                currentStage = FALL_STAGE_IDLE;
            }
            break;
    }
}

void FallDetector::update() {
    unsigned long now = millis();
    // 50 Hz sampling rate (20ms interval)
    if (now - lastSampleTime >= 20) {
        lastSampleTime = now;

        if (mpuInitialized) {
            sensors_event_t a, g, temp;
            mpu.getEvent(&a, &g, &temp);
            processSensorData(a.acceleration.x, a.acceleration.y, a.acceleration.z,
                              g.gyro.x, g.gyro.y, g.gyro.z);
        }
    }
}

bool FallDetector::isFallDetected() {
    return fallEventDetected;
}

void FallDetector::clearFallEvent() {
    fallEventDetected = false;
    currentStage = FALL_STAGE_IDLE;
}
