"""
Telegram Emergency Notification Client
=======================================
Sends asynchronous, non-blocking alerts to the designated guardian
via the Telegram Bot API.
"""

import time
import queue
import threading
import requests
from typing import Optional
from rpi.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_TIMEOUT_SEC,
    TELEGRAM_MAX_RETRIES
)
from rpi.logging_config import setup_logger

logger = setup_logger("TelegramClient")

class TelegramClient:
    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.msg_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None

    def start(self):
        """Starts the background message sender worker."""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True, name="TelegramWorkerThread")
            self.worker_thread.start()
            logger.info("Telegram background alert dispatcher started.")

    def send_emergency_fall_alert(self, device_id: str = "Smart_Assistive_RPI3"):
        """Queues an emergency fall alert to the guardian."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"🚨 EMERGENCY ALERT: FALL DETECTED!\n\n"
            f"Device: {device_id}\n"
            f"Time: {timestamp}\n"
            f"Status: Fall confirmed by MPU-6050 sensor.\n"
            f"User did not cancel the alert. Please check immediately!"
        )
        self.queue_message(msg)

    def send_safe_status_alert(self, device_id: str = "Smart_Assistive_RPI3"):
        """Queues a safe cancellation confirmation to the guardian."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"✅ USER STATUS UPDATE: SAFE\n\n"
            f"Device: {device_id}\n"
            f"Time: {timestamp}\n"
            f"Status: Emergency alarm cancelled. User pressed the Safe Switch."
        )
        self.queue_message(msg)

    def send_system_online_alert(self, device_id: str = "Smart_Assistive_RPI3"):
        """Queues a boot-up notification."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"ℹ️ SYSTEM ONLINE\n\n"
            f"Device: {device_id}\n"
            f"Time: {timestamp}\n"
            f"Raspberry Pi 3 Smart Assistive System started successfully."
        )
        self.queue_message(msg)

    def queue_message(self, message: str):
        """Places a message into the dispatch queue without blocking callers."""
        self.msg_queue.put(message)

    def _dispatch_http(self, message: str) -> bool:
        """Sends the HTTP POST request to Telegram Bot API."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram Bot Token or Chat ID not configured. Skipping alert.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message
        }

        for attempt in range(1, TELEGRAM_MAX_RETRIES + 1):
            try:
                r = requests.post(url, json=payload, timeout=TELEGRAM_TIMEOUT_SEC)
                if r.status_code == 200:
                    logger.info("✅ Telegram emergency alert delivered successfully to guardian.")
                    return True
                else:
                    logger.warning(f"Telegram HTTP {r.status_code} on attempt {attempt}: {r.text}")
            except Exception as e:
                logger.warning(f"Telegram dispatch error on attempt {attempt}: {e}")
            time.sleep(1.0)

        logger.error("❌ Failed to deliver Telegram alert after retries.")
        return False

    def _worker(self):
        """Processes queued messages sequentially."""
        while self.is_running:
            try:
                msg = self.msg_queue.get(timeout=1.0)
                self._dispatch_http(msg)
                self.msg_queue.task_done()
            except queue.Empty:
                continue

    def stop(self):
        """Stops the worker thread."""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
        logger.info("Telegram client stopped.")
