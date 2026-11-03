"""
Diagnostic Tool: Telegram Emergency Notification Verification
==============================================================
Validates Telegram bot token, chat ID, and outgoing emergency alert dispatch.
"""

import sys
import time
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rpi.telegram_alert import TelegramClient
from rpi.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def test_telegram():
    print("\n--- [TEST 8/8] Telegram Emergency Alert Verification ---")
    print(f"Bot Token : {TELEGRAM_BOT_TOKEN[:15]}... (Masked)")
    print(f"Chat ID   : {TELEGRAM_CHAT_ID}")
    print("\nAttempting to dispatch test verification message to guardian...")

    client = TelegramClient()
    client.start()

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    test_msg = (
        f"🧪 HARDWARE TEST: RASPBERRY PI 3 MIGRATION\n\n"
        f"Time: {timestamp}\n"
        f"Device: Smart_Assistive_RPI3\n"
        f"Message: Telegram emergency messaging pipeline is OPERATIONAL!"
    )

    client.queue_message(test_msg)
    time.sleep(3.0)
    client.stop()

    print("\nCheck your Telegram app (@elder_assist_alert_bot)!")
    print("If you received the message, Telegram alerts are 100% verified.")
    print("If NOT received, verify that you opened '@elder_assist_alert_bot' in Telegram and clicked 'Start' (/start).")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_telegram()
