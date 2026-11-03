#include <Arduino.h>

// Connect:
// ESP32-CAM U0T (TX) -> DevKit RX2 (GPIO 16)
// ESP32-CAM U0R (RX) -> DevKit TX2 (GPIO 17)
// ESP32-CAM GND      -> DevKit GND
// ESP32-CAM 5V       -> DevKit 5V
// ESP32-CAM GPIO 0   -> CAM GND (for flashing)

#define RX2_PIN 16
#define TX2_PIN 17

void setup() {
    // Hardware USB Serial to Laptop
    Serial.begin(115200);
    Serial.setRxBufferSize(4096);

    // Hardware UART2 to ESP32-CAM
    Serial2.begin(115200, SERIAL_8N1, RX2_PIN, TX2_PIN);
    Serial2.setRxBufferSize(4096);

    delay(200);
}

void loop() {
    uint8_t buffer[256];

    // Forward computer -> ESP32-CAM
    int availableUSB = Serial.available();
    if (availableUSB > 0) {
        int bytesRead = Serial.readBytes(buffer, min(availableUSB, (int)sizeof(buffer)));
        Serial2.write(buffer, bytesRead);
    }

    // Forward ESP32-CAM -> computer
    int availableCAM = Serial2.available();
    if (availableCAM > 0) {
        int bytesRead = Serial2.readBytes(buffer, min(availableCAM, (int)sizeof(buffer)));
        Serial.write(buffer, bytesRead);
    }
}
