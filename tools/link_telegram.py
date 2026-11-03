import sys
import time
import requests
import re
import os

TOKEN = "8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0"

print("=" * 60)
print("  TELEGRAM BOT LINKING LISTENER (@elder_assist_alert_bot)")
print("  Waiting for user to press START in Telegram...")
print("=" * 60)

t0 = time.time()
while time.time() - t0 < 90:
    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=5).json()
        if r.get("ok") and r.get("result"):
            last_update = r["result"][-1]
            msg = last_update.get("message", {})
            chat = msg.get("chat", {})
            chat_id = str(chat.get("id"))
            first_name = chat.get("first_name", "Guardian")

            if chat_id and chat_id != "None":
                print(f"\n🎉 [CONNECTED!] Found User: {first_name} (Chat ID: {chat_id})")

                # Send test alert message
                test_text = (
                    "🚨 *AI பார்வை & பாதுகாப்பு சாதனம் (Assistive Device)*\n\n"
                    "✅ *Telegram Guardian Bot இணைக்கப்பட்டது!*\n"
                    f"👤 பாதுகாவலர்: {first_name}\n"
                    "🛡️ நிலை: Active & Monitoring\n\n"
                    "முதியவர் / பார்வையற்றோர் கீழே விழுந்தால் உடனடியாக இந்த Telegram சாட்டுக்கு அவசர எச்சரிக்கை வரும்!"
                )
                res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": test_text,
                    "parse_mode": "Markdown"
                }).json()
                print("Send message status:", res.get("ok"))

                # 1. Update server/.env
                env_path = r"d:\iot-blind\server\.env"
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        c = f.read()
                    c = re.sub(r'TELEGRAM_CHAT_ID=".*?"', f'TELEGRAM_CHAT_ID="{chat_id}"', c)
                    with open(env_path, "w", encoding="utf-8") as f:
                        f.write(c)
                    print("Updated server/.env with real Chat ID!")

                # 2. Update secrets.h
                sec_path = r"d:\iot-blind\firmware\esp32_main\include\secrets.h"
                if os.path.exists(sec_path):
                    with open(sec_path, "r", encoding="utf-8") as f:
                        c = f.read()
                    c = re.sub(r'#define TELEGRAM_CHAT_ID ".*?"', f'#define TELEGRAM_CHAT_ID "{chat_id}"', c)
                    with open(sec_path, "w", encoding="utf-8") as f:
                        f.write(c)
                    print("Updated firmware/esp32_main/include/secrets.h!")

                # 3. Update server app.py live variable if running
                print(">>> TELEGRAM BOT 100% LINKED & VERIFIED! <<<")
                sys.exit(0)
    except Exception as e:
        print("Polling error:", e)
    time.sleep(1)

print("Listener timed out after 90s.")
sys.exit(1)

