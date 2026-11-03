#include "vision_link.h"

VisionLink::VisionLink()
    : visionSerial(1), newDetectionAvailable(false) {
    lastDetection.valid = false;
    lastDetection.label[0] = '\0';
    lastDetection.position[0] = '\0';
    lastDetection.tamilText[0] = '\0';
    lastDetection.confidence = 0.0f;
}

void VisionLink::begin() {
    Serial.println("[VISION LINK] Initializing UART1 link to ESP32-CAM (RX: 32, TX: 33)...");
    visionSerial.begin(115200, SERIAL_8N1, PIN_VISION_RX, PIN_VISION_TX);
    inputBuffer.reserve(256);
}

void VisionLink::injectSimulatedObject(const char* label, float conf, const char* pos, const char* tamilText) {
    snprintf(lastDetection.label, sizeof(lastDetection.label), "%s", label);
    lastDetection.confidence = conf;
    snprintf(lastDetection.position, sizeof(lastDetection.position), "%s", pos);
    if (tamilText && strlen(tamilText) > 0) {
        snprintf(lastDetection.tamilText, sizeof(lastDetection.tamilText), "%s", tamilText);
    } else {
        lastDetection.tamilText[0] = '\0';
    }
    lastDetection.valid = true;
    newDetectionAvailable = true;
    Serial.printf("[VISION SIMULATION] 👁 Injected Object: label=%s, conf=%.2f, pos=%s\n", label, conf, pos);
}

void VisionLink::parseProtocolLine(const String& line) {
    // Protocol formats:
    // 1) OBJ,<label>,<confidence>,<position>,<clip_id>,<tamil_text>
    // 2) OBJ,<label>,<confidence>,<position>,<tamil_text>
    // 3) OBJ,<label>,<confidence>,<position>
    if (!line.startsWith("OBJ,")) return;

    int idx1 = line.indexOf(',');
    int idx2 = line.indexOf(',', idx1 + 1);
    int idx3 = line.indexOf(',', idx2 + 1);

    if (idx1 == -1 || idx2 == -1 || idx3 == -1) return;

    String labelStr = line.substring(idx1 + 1, idx2);
    String confStr  = line.substring(idx2 + 1, idx3);
    
    int idx4 = line.indexOf(',', idx3 + 1);
    String posStr = "";
    uint16_t parsedClipId = 0;
    String tamilStr = "";

    if (idx4 != -1) {
        posStr = line.substring(idx3 + 1, idx4);
        int idx5 = line.indexOf(',', idx4 + 1);
        if (idx5 != -1) {
            String clipStr = line.substring(idx4 + 1, idx5);
            clipStr.trim();
            parsedClipId = clipStr.toInt();
            tamilStr = line.substring(idx5 + 1);
        } else {
            String remainder = line.substring(idx4 + 1);
            remainder.trim();
            if (remainder.length() > 0 && isDigit(remainder.charAt(0))) {
                parsedClipId = remainder.toInt();
            } else {
                tamilStr = remainder;
            }
        }
    } else {
        posStr = line.substring(idx3 + 1);
    }
    posStr.trim();
    tamilStr.trim();

    labelStr.toCharArray(lastDetection.label, sizeof(lastDetection.label));
    lastDetection.confidence = confStr.toFloat();
    posStr.toCharArray(lastDetection.position, sizeof(lastDetection.position));
    tamilStr.toCharArray(lastDetection.tamilText, sizeof(lastDetection.tamilText));
    lastDetection.clipId = parsedClipId;
    lastDetection.valid = (lastDetection.confidence >= VISION_MIN_CONFIDENCE);

    if (lastDetection.valid) {
        newDetectionAvailable = true;
        Serial.printf("[VISION] Received Object: %s (%.2f) [%s] Clip:%u Tamil:\"%s\"\n",
                      lastDetection.label, lastDetection.confidence, lastDetection.position,
                      lastDetection.clipId, lastDetection.tamilText);
    }
}

void VisionLink::update() {
    while (visionSerial.available()) {
        char c = (char)visionSerial.read();
        if (c == '\n') {
            inputBuffer.trim();
            if (inputBuffer.length() > 0) {
                parseProtocolLine(inputBuffer);
            }
            inputBuffer = "";
        } else if (c != '\r') {
            inputBuffer += c;
        }
    }
}

bool VisionLink::hasDetection() {
    return newDetectionAvailable;
}

VisionDetection VisionLink::getLatestDetection() {
    newDetectionAvailable = false;
    return lastDetection;
}

AudioClip VisionLink::mapDetectionToAudioClip(const char* label, const char* position) {
    String lbl = String(label);
    lbl.toLowerCase();
    String pos = String(position);
    pos.toLowerCase();

    // 1. Medicines Identification (Requirement 6)
    if (lbl.indexOf("paracetamol") != -1 || lbl.indexOf("paracetomal") != -1 ||
        lbl.indexOf("dolo") != -1 || lbl.indexOf("calpol") != -1 || lbl.indexOf("crocin") != -1) {
        return CLIP_MEDICINE_PARACETAMOL;
    }
    if (lbl.indexOf("rantac") != -1 || lbl.indexOf("ranitidine") != -1 || lbl.indexOf("aciloc") != -1) {
        return CLIP_MEDICINE_RANTAC;
    }
    if (lbl.indexOf("tassic") != -1 || lbl.indexOf("tanic") != -1 ||
        lbl.indexOf("tonic") != -1 || lbl.indexOf("tastic") != -1 || lbl.indexOf("tusq") != -1) {
        return CLIP_MEDICINE_TASSIC;
    }

    // 2. Currency Identification (Requirement 7)
    if (lbl.indexOf("500") != -1) return CLIP_CURRENCY_500;
    if (lbl.indexOf("200") != -1) return CLIP_CURRENCY_200;
    if (lbl.indexOf("100") != -1) return CLIP_CURRENCY_100;
    if (lbl.indexOf("50") != -1)  return CLIP_CURRENCY_50;
    if (lbl.indexOf("20") != -1)  return CLIP_CURRENCY_20;
    if (lbl.indexOf("10") != -1)  return CLIP_CURRENCY_10;

    // 3. General Obstacles
    if (lbl == "dustbin" || lbl == "garbage bin" || lbl == "trash") {
        return CLIP_DUSTBIN_FRONT;
    }
    if (lbl == "dog") {
        if (pos == "left") return CLIP_DOG_LEFT;
        return CLIP_OBSTACLE_FRONT;
    }
    if (lbl == "chair") {
        if (pos == "right") return CLIP_CHAIR_RIGHT;
        return CLIP_CHAIR_AHEAD;
    }
    if (lbl == "person" || lbl == "human") {
        if (pos == "left") return CLIP_PERSON_LEFT;
        if (pos == "right") return CLIP_PERSON_RIGHT;
        return CLIP_PERSON_FRONT;
    }
    if (lbl == "car" || lbl == "vehicle" || lbl == "bus" || lbl == "truck") {
        return CLIP_CAR_FRONT;
    }
    if (lbl == "table" || lbl == "desk" || lbl == "dining table") {
        return CLIP_TABLE_FRONT;
    }
    if (lbl == "door") return CLIP_DOOR_AHEAD;
    if (lbl == "stairs") return CLIP_STAIRS_AHEAD;
    if (lbl == "wall") return CLIP_WALL_AHEAD;

    // Default fallback clip for unmapped object
    return CLIP_OBSTACLE_FRONT;
}
