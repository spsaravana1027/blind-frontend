#ifndef TELEGRAM_CLIENT_H
#define TELEGRAM_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <UniversalTelegramBot.h>
#include "config.h"

#define MAX_QUEUE_SIZE 5

struct TelegramAlertMessage {
    char messageText[256];
    unsigned long timestamp;
    uint8_t retryCount;
    bool active;
};

class TelegramNotifier {
private:
    WiFiClientSecure securedClient;
    UniversalTelegramBot* bot;
    
    TelegramAlertMessage alertQueue[MAX_QUEUE_SIZE];
    uint8_t queueHead;
    uint8_t queueTail;
    uint8_t queueCount;

    unsigned long lastWifiCheckTime;
    unsigned long lastBotPollTime;
    bool wifiConnected;

public:
    TelegramNotifier();
    ~TelegramNotifier();

    void begin();
    void update();

    bool queueEmergencyAlert(const char* deviceId, const char* details = "Fall detected!");
    bool queueSafeMessage(const char* details = "User is safe. Alarm turned off.");
    bool queueStatusMessage(const char* text);
    
    bool isWifiConnected() const { return WiFi.status() == WL_CONNECTED; }
    uint8_t getPendingQueueCount() const { return queueCount; }

private:
    void processWifiConnection();
    void processQueue();
    void checkIncomingMessages();
    bool sendSingleTelegramMessage(const char* text);
};

#endif // TELEGRAM_CLIENT_H
