#include "ultrasonic.h"
#include <algorithm>

UltrasonicSensor::UltrasonicSensor(uint8_t trig, uint8_t echo)
    : trigPin(trig), echoPin(echo), sampleIndex(0),
      lastMeasureTime(0), lastMedianDistance(200.0f),
      simulatedMode(false), simulatedDistance(200.0f) {
    for (int i = 0; i < MEDIAN_SAMPLE_SIZE; i++) {
        samples[i] = 200.0f;
    }
}

void UltrasonicSensor::begin() {
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    digitalWrite(trigPin, LOW);
    Serial.println("[ULTRASONIC] HC-SR04 Sensor initialized.");
}

void UltrasonicSensor::injectSimulatedDistance(float distCm) {
    simulatedMode = true;
    simulatedDistance = distCm;
    lastMedianDistance = distCm;
    for (int i = 0; i < MEDIAN_SAMPLE_SIZE; i++) {
        samples[i] = distCm;
    }
    Serial.printf("[ULTRASONIC SIMULATION] Distance injected: %.1f cm\n", distCm);
}

float UltrasonicSensor::measureRawDistance() {
    if (simulatedMode) {
        return simulatedDistance;
    }

    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    // Pulse width measurement with 30ms timeout (~5 meters max)
    unsigned long duration = pulseIn(echoPin, HIGH, 30000);
    if (duration == 0) {
        // Out of range or no echo return
        return 400.0f;
    }

    // Speed of sound = 343 m/s = 0.0343 cm/us
    float distance = (duration * 0.0343f) / 2.0f;
    if (distance < 2.0f || distance > 400.0f) {
        return 400.0f;
    }
    return distance;
}

float UltrasonicSensor::computeMedian() {
    float temp[MEDIAN_SAMPLE_SIZE];
    for (int i = 0; i < MEDIAN_SAMPLE_SIZE; i++) {
        temp[i] = samples[i];
    }
    std::sort(temp, temp + MEDIAN_SAMPLE_SIZE);
    return temp[MEDIAN_SAMPLE_SIZE / 2];
}

void UltrasonicSensor::update() {
    unsigned long now = millis();
    // Non-blocking sampling every 60ms
    if (now - lastMeasureTime >= 60) {
        lastMeasureTime = now;
        float raw = measureRawDistance();
        samples[sampleIndex] = raw;
        sampleIndex = (sampleIndex + 1) % MEDIAN_SAMPLE_SIZE;
        lastMedianDistance = computeMedian();
    }
}

float UltrasonicSensor::getDistanceCm() {
    return lastMedianDistance;
}

float UltrasonicSensor::measureImmediateDistance() {
    // Immediately calculate distance right as webcam captures an obstacle
    float raw = measureRawDistance();
    samples[sampleIndex] = raw;
    sampleIndex = (sampleIndex + 1) % MEDIAN_SAMPLE_SIZE;
    lastMedianDistance = computeMedian();
    lastMeasureTime = millis();
    return lastMedianDistance;
}

