"""
Smart Assistive System for Visually Impaired People
===================================================
Raspberry Pi 3 Model B/B+ Primary Application Orchestrator

Workflow:
1. Initializes CSI Camera, MPU-6050, HC-SR04, MAX98357A I2S Audio,
   Emergency Buzzer, and Safe Switch.
2. Continuously reads accelerometer & gyroscope at 50 Hz for fall detection.
3. If a possible fall is detected:
   - System enters FALL_COUNTDOWN state (15s verification window).
   - Speaks emergency prompt over speaker.
   - User can press Cancel/Safe button (BCM 17) to cancel alert.
   - If not cancelled, triggers emergency siren and dispatches Telegram alert.
4. Concurrently, CSI camera captures frames and runs YOLOv8 obstacle detection:
   - Combined with HC-SR04 ultrasonic sensor (BCM 23/24).
   - If obstacle is NEAR (<= 50 cm), speaks critical proximity warning:
     "எச்சரிக்கை! பொருள் அருகில் உள்ளது."
   - Identifies directional positions (Left / Center / Right) and objects.
5. All subsystems operate asynchronously without thread starvation or CPU lag.
"""

import sys
import os
import time
import signal
import threading
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rpi.config import (
    DISTANCE_CRITICAL_CM,
    VISION_INFERENCE_INTERVAL_SEC,
    OCR_ENABLED
)
from rpi.logging_config import setup_logger
from rpi.camera_manager import CameraManager
from rpi.object_detection import ObjectDetector
from rpi.ultrasonic_sensor import UltrasonicSensor
from rpi.fall_detection import FallDetector
from rpi.audio_manager import AudioManager
from rpi.alert_manager import AlertManager, STATE_MONITORING, STATE_FALL_COUNTDOWN, STATE_EMERGENCY_ALARM
from rpi.telegram_alert import TelegramClient

logger = setup_logger("MainApp")

class SmartAssistiveApp:
    def __init__(self):
        self.is_running = False

        # Initialize Subsystems
        logger.info("==============================================================")
        logger.info("  STARTING SMART ASSISTIVE SYSTEM ON RASPBERRY PI 3")
        logger.info("==============================================================")

        self.audio = AudioManager()
        self.telegram = TelegramClient()
        self.alert = AlertManager()
        self.ultrasonic = UltrasonicSensor()
        self.fall_detector = FallDetector()
        self.camera = CameraManager()
        self.detector = ObjectDetector()

        # Connect Alert Callbacks
        self.alert.on_fall_confirmed = self._on_fall_confirmed
        self.alert.on_alert_cancelled = self._on_alert_cancelled
        self.alert.on_countdown_tick = self._on_countdown_tick

        # Threads
        self.vision_thread = None
        self.fall_monitor_thread = None

    def _on_fall_confirmed(self):
        """Callback when fall countdown expires without user cancellation."""
        logger.critical("🚨 Emergency Fall Confirmed! Playing alarm and notifying guardian...")
        self.audio.play_clip("emergency_fall", force=True)
        self.telegram.send_emergency_fall_alert()

    def _on_alert_cancelled(self):
        """Callback when user presses safe button during countdown or alarm."""
        logger.info("✅ Fall alert cancelled. Playing user safe confirmation...")
        self.audio.play_clip("user_safe", force=True)
        self.telegram.send_safe_status_alert()

    def _on_countdown_tick(self, seconds_left: int):
        """Callback on each countdown tick."""
        if seconds_left in (15, 10, 5, 3, 2, 1):
            logger.warning(f"⏳ Emergency verification countdown: {seconds_left}s remaining! Press button to cancel.")

    def _fall_monitor_loop(self):
        """Continuously checks MPU-6050 fall detection state."""
        while self.is_running:
            if self.fall_detector.is_fall_detected():
                self.fall_detector.clear_fall_event()
                if self.alert.get_state() == STATE_MONITORING:
                    logger.warning("💥 MPU-6050 triggered fall criteria! Starting countdown...")
                    self.audio.play_clip("emergency_fall", force=True)
                    self.alert.trigger_possible_fall()

            time.sleep(0.05)

    def _vision_loop(self):
        """Captures camera frames, queries ultrasonic sensor, and guides the user."""
        logger.info("Vision & Obstacle navigation loop active.")
        last_inference_time = 0.0

        while self.is_running:
            now = time.time()
            if now - last_inference_time >= VISION_INFERENCE_INTERVAL_SEC:
                last_inference_time = now

                # Only process vision guidance if not in an active emergency alarm
                if self.alert.get_state() != STATE_MONITORING:
                    time.sleep(0.1)
                    continue

                # 1. Read distance from HC-SR04
                distance_cm = self.ultrasonic.get_distance()

                # 2. Capture frame from CSI camera
                frame = self.camera.capture_frame()

                # 3. Optional OCR for medicines and currency
                if OCR_ENABLED:
                    ocr_res = self.detector.recognize_medicine_or_currency(frame)
                    if ocr_res:
                        lbl, tamil_phrase, clip_id = ocr_res
                        logger.info(f"🔍 Recognized: {lbl} -> '{tamil_phrase}'")
                        self.audio.play_clip(clip_id, force=False)
                        continue

                # 4. Run YOLOv8 object detection
                detections = self.detector.detect_objects(frame, ultrasonic_distance_cm=distance_cm)

                if detections:
                    top_obj = detections[0]
                    label = top_obj["label"]
                    pos = top_obj["position"]
                    is_near = top_obj["is_near"]

                    logger.info(f"👁️ Detected: {label} [{pos.upper()}], Distance: {distance_cm:.1f} cm (Near: {is_near})")

                    # If obstacle is near (<= 50 cm), speak critical obstacle warning
                    if distance_cm <= DISTANCE_CRITICAL_CM or is_near:
                        # "எச்சரிக்கை! பொருள் அருகில் உள்ளது."
                        self.audio.play_clip("obstacle_warning", force=False)
                    else:
                        # Directional audio announcements
                        clip_key = f"{label}_{pos}" if f"{label}_{pos}" in ["person_left", "person_right", "chair_right", "dog_left"] else f"{label}_ahead"
                        if clip_key in ["person_left", "person_right", "person_ahead", "chair_ahead", "table_ahead", "door_ahead", "stairs_ahead", "wall_ahead", "vehicle_ahead"]:
                            self.audio.play_clip(clip_key, force=False)
                        else:
                            self.audio.play_clip("obstacle_notice", force=False)

            time.sleep(0.02)

    def start(self):
        """Starts all background worker threads and state loops."""
        self.is_running = True

        # Start hardware subsystems
        self.telegram.start()
        self.ultrasonic.start()
        self.fall_detector.start()
        self.camera.start()

        # Play system startup confirmation
        self.audio.play_clip("system_ready", force=True)
        self.telegram.send_system_online_alert()

        # Start processing loops
        self.fall_monitor_thread = threading.Thread(target=self._fall_monitor_loop, daemon=True, name="FallMonitorThread")
        self.fall_monitor_thread.start()

        self.vision_thread = threading.Thread(target=self._vision_loop, daemon=True, name="VisionThread")
        self.vision_thread.start()

        logger.info("✅ Smart Assistive System is fully ONLINE and MONITORING.")

    def run_interactive(self):
        """Allows interactive console testing (hotkeys 'f' to simulate fall, 's' for safe button)."""
        self.start()
        print("\n" + "="*60)
        print("  SYSTEM RUNNING. Console Test Commands:")
        print("    f + Enter  : Simulate MPU-6050 Fall Down event")
        print("    s + Enter  : Press Cancel / Safe Push Button")
        print("    d <cm>     : Set simulated distance (e.g. 'd 35')")
        print("    q + Enter  : Quit application gracefully")
        print("="*60 + "\n")

        try:
            while self.is_running:
                line = sys.stdin.readline()
                if not line:
                    break
                cmd = line.strip().lower()
                if cmd == 'f':
                    logger.warning("[USER CLI] Simulating fall event...")
                    self.fall_detector.inject_simulated_fall()
                elif cmd == 's':
                    logger.info("[USER CLI] Pressing safe switch...")
                    self.alert.cancel_or_safe_pressed()
                elif cmd.startswith('d '):
                    try:
                        d_val = float(cmd.split()[1])
                        self.ultrasonic.set_simulated_distance(d_val)
                    except ValueError:
                        print("Invalid distance value.")
                elif cmd == 'q':
                    logger.info("Quitting application...")
                    break
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received.")
        finally:
            self.stop()

    def stop(self):
        """Performs a clean shutdown and resource release."""
        if not self.is_running:
            return
        logger.info("Shutting down Smart Assistive System...")
        self.is_running = False

        self.alert.stop()
        self.ultrasonic.stop()
        self.fall_detector.stop()
        self.camera.stop()
        self.audio.stop()
        self.telegram.stop()

        logger.info("✅ All hardware peripherals safely released. System terminated cleanly.")

def main():
    app = SmartAssistiveApp()

    # Register OS signal handlers
    def _sig_handler(signum, frame):
        logger.info(f"Signal {signum} received. Initiating graceful shutdown...")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    app.run_interactive()

if __name__ == "__main__":
    main()
