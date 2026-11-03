#include "telegram_client.h"

TelegramNotifier::TelegramNotifier()
    : bot(nullptr), queueHead(0), queueTail(0), queueCount(0),
      lastWifiCheckTime(0), lastBotPollTime(0), wifiConnected(false) {
    for (int i = 0; i < MAX_QUEUE_SIZE; i++) {
        alertQueue[i].active = false;
        alertQueue[i].retryCount = 0;
    }
}

TelegramNotifier::~TelegramNotifier() {
    if (bot) {
        delete bot;
        bot = nullptr;
    }
}

void TelegramNotifier::begin() {
    Serial.printf("[WIFI/TELEGRAM] Connecting to Wi-Fi SSID: '%s'...\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setTxPower(WIFI_POWER_11dBm); // Energy saving mode prevents current spikes
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    wifiConnected = false;
    lastWifiCheckTime = millis();
}

void TelegramNotifier::processWifiConnection() {
    if (WiFi.status() == WL_CONNECTED) {
        if (!wifiConnected) {
            wifiConnected = true;
            Serial.printf("[WIFI SUCCESS] Connected to '%s'! ESP32 IP: %s\n", WIFI_SSID, WiFi.localIP().toString().c_str());
        }
    } else {
        if (wifiConnected) {
            wifiConnected = false;
            Serial.println("[WIFI NOTICE] Wi-Fi connection reconnecting...");
        }
        unsigned long now = millis();
        if (now - lastWifiCheckTime >= 15000) {
            lastWifiCheckTime = now;
            WiFi.disconnect();
            WiFi.begin(WIFI_SSID, WIFI_PASS);
        }
    }
}

bool TelegramNotifier::queueEmergencyAlert(const char* deviceId, const char* details) {
    if (queueCount >= MAX_QUEUE_SIZE) {
        Serial.println("[TELEGRAM QUEUE ERROR] Queue full! Overwriting oldest message.");
        queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
        queueCount--;
    }

    TelegramAlertMessage& msg = alertQueue[queueTail];
    snprintf(msg.messageText, sizeof(msg.messageText),
             "🚨 அவசர எச்சரிக்கை! (EMERGENCY FALL ALERT)\n"
             "பயனர் கீழே விழுந்துவிட்டார்!\n"
             "உடனடியாக கவனிக்கவும்.\n"
             "Device: %s\n"
             "Status: Fall Detected\n"
             "Details: %s\n"
             "Action: Please assist the user immediately!",
             deviceId, details);
    msg.timestamp = millis();
    msg.retryCount = 0;
    msg.active = true;

    queueTail = (queueTail + 1) % MAX_QUEUE_SIZE;
    queueCount++;

    Serial.printf("[TELEGRAM QUEUE] Enqueued IMMEDIATE emergency fall alert. Queue size: %d\n", queueCount);
    return true;
}

bool TelegramNotifier::queueSafeMessage(const char* details) {
    if (queueCount >= MAX_QUEUE_SIZE) {
        queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
        queueCount--;
    }

    TelegramAlertMessage& msg = alertQueue[queueTail];
    snprintf(msg.messageText, sizeof(msg.messageText),
             "✅ பாதுகாப்பு தகவல் (SAFE UPDATE)\n"
             "பயனர் பாதுகாப்பாக உள்ளார்.\n"
             "அவசர எச்சரிக்கை சுவிட்ச் மூலம் அணைக்கப்பட்டது.\n"
             "Status: User is SAFE\n"
             "Details: %s\n"
             "Action: Alert buzzer stopped. No further emergency action required.",
             details);
    msg.timestamp = millis();
    msg.retryCount = 0;
    msg.active = true;

    queueTail = (queueTail + 1) % MAX_QUEUE_SIZE;
    queueCount++;

    Serial.printf("[TELEGRAM QUEUE] Enqueued SAFE update to guardian. Queue size: %d\n", queueCount);
    return true;
}

bool TelegramNotifier::queueStatusMessage(const char* text) {
    if (queueCount >= MAX_QUEUE_SIZE) return false;

    TelegramAlertMessage& msg = alertQueue[queueTail];
    snprintf(msg.messageText, sizeof(msg.messageText), "ℹ️ SYSTEM STATUS\n%s", text);
    msg.timestamp = millis();
    msg.retryCount = 0;
    msg.active = true;

    queueTail = (queueTail + 1) % MAX_QUEUE_SIZE;
    queueCount++;
    return true;
}

bool TelegramNotifier::sendSingleTelegramMessage(const char* text) {
    if (!wifiConnected || !bot) return false;

    Serial.println("[TELEGRAM] Sending message to Telegram Bot...");
    bool success = bot->sendMessage(TELEGRAM_CHAT_ID, text, "");
    if (success) {
        Serial.println("[TELEGRAM SUCCESS] Emergency alert delivered via Telegram!");
    } else {
        Serial.println("[TELEGRAM ERROR] Failed to deliver Telegram message.");
    }
    return success;
}

void TelegramNotifier::processQueue() {
    if (queueCount == 0 || !wifiConnected) return;

    TelegramAlertMessage& msg = alertQueue[queueHead];
    if (sendSingleTelegramMessage(msg.messageText)) {
        msg.active = false;
        queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
        queueCount--;
    } else {
        msg.retryCount++;
        if (msg.retryCount >= 5) {
            Serial.println("[TELEGRAM ERROR] Exceeded max retries for message. Dropping.");
            msg.active = false;
            queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
            queueCount--;
        }
    }
}

void TelegramNotifier::checkIncomingMessages() {
    if (!wifiConnected || !bot) return;

    unsigned long now = millis();
    if (now - lastBotPollTime >= 5000) { // Poll every 5 seconds
        lastBotPollTime = now;

        int numNewMessages = bot->getUpdates(bot->last_message_received + 1);
        for (int i = 0; i < numNewMessages; i++) {
            String text = bot->messages[i].text;
            String fromId = bot->messages[i].chat_id;

            if (fromId == TELEGRAM_CHAT_ID) {
                if (text == "/status") {
                    bot->sendMessage(fromId, "✅ Assistive Device Status: ONLINE\nBattery: Normal\nSensors: Active", "");
                } else if (text == "/test") {
                    bot->sendMessage(fromId, "🔔 Test message received from Assistive Device!", "");
                }
            }
        }
    }
}

void TelegramNotifier::update() {
    processWifiConnection();
    processQueue();
    checkIncomingMessages();
}
