#ifndef VISION_LINK_H
#define VISION_LINK_H

#include <Arduino.h>
#include "config.h"

struct VisionDetection {
    char label[32];
    float confidence;
    char position[16]; // "left", "center", "right"
    char tamilText[128]; // Custom Tamil instruction text from server if available
    uint16_t clipId;     // Optional direct clip ID mapping
    bool valid;
};

class VisionLink {
private:
    HardwareSerial visionSerial;
    String inputBuffer;
    VisionDetection lastDetection;
    bool newDetectionAvailable;

public:
    VisionLink();
    void begin();
    void update();
    bool hasDetection();
    VisionDetection getLatestDetection();
    void injectSimulatedObject(const char* label, float conf = 0.90f, const char* pos = "center", const char* tamilText = "");

    // Mapping helper: label + position -> AudioClip enum
    static AudioClip mapDetectionToAudioClip(const char* label, const char* position);
    void parseProtocolLine(const String& line);
};

#endif // VISION_LINK_H
