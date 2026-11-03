import os
import sys
import time
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8919888784:AAFSIikz6iS3mqwLvCauRngpOiHUd2BZ3N0")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7906413709")

def test_telegram_connection():
    print("=" * 60)
    print("       TELEGRAM GUARDIAN ALERT INTEGRATION TEST")
    print("=" * 60)
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...{TELEGRAM_BOT_TOKEN[-6:]}")
    print(f"Chat ID:   {TELEGRAM_CHAT_ID}")

    # 1. Test getMe
    get_me_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    try:
        r = requests.get(get_me_url, timeout=10)
        if r.status_code == 200:
            bot_info = r.json().get("result", {})
            print(f"✅ Bot Verified: @{bot_info.get('username')} ({bot_info.get('first_name')})")
        else:
            print(f"❌ getMe failed: HTTP {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error testing getMe: {e}")
        return False

    # 2. Test sending emergency alert message
    curr_time = time.strftime('%Y-%m-%d %H:%M:%S')
    test_msg = (
        f"🚨 [TEST ALERT] Assistive Fall & Obstacle Device\n"
        f"Timestamp: {curr_time}\n"
        f"System Status: ONLINE & FUNCTIONAL\n"
        f"Device: ESP32 DevKit V1 + ESP32-CAM\n"
        f"Telegram Alerting is working properly."
    )

    send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": test_msg
    }

    try:
        r = requests.post(send_url, json=payload, timeout=10)
        if r.status_code == 200:
            print("✅ Telegram test message sent successfully to guardian!")
            print(f"   Message content:\n{test_msg}")
            return True
        else:
            print(f"❌ sendMessage failed: HTTP {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error sending message: {e}")
        return False

if __name__ == "__main__":
    success = test_telegram_connection()
    sys.exit(0 if success else 1)
