# Telegram Bot Setup Guide

This guide walks you through setting up a Telegram Bot to receive real-time emergency fall alerts and status updates from the Assistive Device.

## Step 1: Create a New Telegram Bot

1. Open Telegram on your phone or desktop.
2. Search for `@BotFather` and start a chat.
3. Send the command: `/newbot`
4. Follow the prompts:
   - Enter a name for your bot (e.g., `Assistive Device Alert Bot`).
   - Enter a unique username ending in `bot` (e.g., `elderly_assist_alert_bot`).
5. BotFather will reply with your **HTTP API Bot Token**. It looks like this:
   `123456789:ABCdefGHIjklMNOpqrsTUVwxyZ`
6. Save this token! You will paste it into `secrets.h` as `TELEGRAM_BOT_TOKEN`.

---

## Step 2: Get Your Personal Chat ID

To receive alerts on your account:
1. Search for `@userinfobot` on Telegram.
2. Start the chat or send any message.
3. The bot will reply with your **Id** (a numerical string, e.g., `987654321`).
4. Save this ID! You will paste it into `secrets.h` as `TELEGRAM_CHAT_ID`.

---

## Step 3: Configure `secrets.h` in Firmware

1. Copy `firmware/esp32_main/include/secrets.h.example` to `secrets.h`:
   ```bash
   cp firmware/esp32_main/include/secrets.h.example firmware/esp32_main/include/secrets.h
   ```
2. Edit `secrets.h` with your Wi-Fi credentials and Telegram details:
   ```cpp
   #define WIFI_SSID "Your_Home_WiFi_SSID"
   #define WIFI_PASS "Your_WiFi_Password"
   #define TELEGRAM_BOT_TOKEN "123456789:ABCdefGHIjklMNOpqrsTUVwxyZ"
   #define TELEGRAM_CHAT_ID "987654321"
   ```

---

## Step 4: Interacting with the Bot

Once the device is online, open a chat with your newly created Telegram Bot and click **Start**. You can send the following commands:

- `/status` — Queries device health, Wi-Fi status, and active sensors.
- `/test` — Triggers a test notification to verify end-to-end communication.

---

## Step 5: Test Telegram Alerts via Browser

You can test if your Bot Token and Chat ID work directly from your web browser:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage?chat_id=<YOUR_CHAT_ID>&text=Test Alert From Browser
```
If configured correctly, you will receive a Telegram notification instantly.
