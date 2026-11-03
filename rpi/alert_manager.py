"""
Alert Manager & Emergency State Machine
=======================================
Manages:
1. Emergency Buzzer on BCM GPIO27 (Physical pin 13)
2. Emergency Cancel / Safe Push Button on BCM GPIO17 (Physical pin 11, internal pull-up)
3. Configurable verification countdown state (default 15 seconds)
4. Emergency alert dispatching and safe state cancellation
"""

import time
import threading
from typing import Callable, Optional
from rpi.config import (
    PINS,
    FALL_COUNTDOWN_SECONDS
)
from rpi.logging_config import setup_logger

logger = setup_logger("AlertManager")

# System States
STATE_MONITORING = "MONITORING"
STATE_FALL_COUNTDOWN = "FALL_COUNTDOWN"
STATE_EMERGENCY_ALARM = "EMERGENCY_ALARM"

class AlertManager:
    def __init__(self,
                 buzzer_bcm: int = PINS["BUZZER"]["bcm"],
                 button_bcm: int = PINS["BUTTON_CANCEL"]["bcm"],
                 countdown_sec: int = FALL_COUNTDOWN_SECONDS,
                 simulated: bool = False):
        self.buzzer_pin = buzzer_bcm
        self.button_pin = button_bcm
        self.countdown_duration = countdown_sec
        self.simulated = simulated
        self.hardware_active = False

        self.current_state = STATE_MONITORING
        self.countdown_remaining = 0
        self.countdown_thread = None

        self.buzzer_active = False
        self.buzzer_thread = None

        self.last_button_press_time = 0.0
        self.lock = threading.Lock()
        self._gpio = None

        # Callbacks
        self.on_fall_confirmed: Optional[Callable[[], None]] = None
        self.on_alert_cancelled: Optional[Callable[[], None]] = None
        self.on_countdown_tick: Optional[Callable[[int], None]] = None

        if not self.simulated:
            self._init_gpio()

    def _init_gpio(self):
        """Configures buzzer output and debounced button input."""
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            # Buzzer: Output (Active HIGH)
            GPIO.setup(self.buzzer_pin, GPIO.OUT)
            GPIO.output(self.buzzer_pin, GPIO.LOW)

            # Button: Input with internal PULL-UP (Active LOW when pressed to GND)
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Button event listener with 200ms bouncetime
            GPIO.add_event_detect(
                self.button_pin,
                GPIO.FALLING,
                callback=self._handle_hardware_button_press,
                bouncetime=200
            )

            self.hardware_active = True
            logger.info(f"✅ Alert peripherals configured (Buzzer: BCM {self.buzzer_pin}, Button: BCM {self.button_pin}).")
        except (ImportError, RuntimeError) as e:
            logger.warning(f"RPi.GPIO unavailable ({e}). Running alerts in SIMULATION mode.")
            self.simulated = True
            self.hardware_active = False

    def _handle_hardware_button_press(self, channel):
        """ISR callback when button is physically pressed."""
        now = time.time()
        if now - self.last_button_press_time < 0.2:
            return
        self.last_button_press_time = now
        logger.info("🔘 Hardware Push Button Pressed!")
        self.cancel_or_safe_pressed()

    def trigger_possible_fall(self):
        """
        Transitions from MONITORING to FALL_COUNTDOWN state.
        Initiates the verification timer.
        """
        with self.lock:
            if self.current_state != STATE_MONITORING:
                return
            self.current_state = STATE_FALL_COUNTDOWN
            self.countdown_remaining = self.countdown_duration

        logger.warning(f"🚨 Possible fall detected! Verification countdown started ({self.countdown_duration}s)...")

        def _countdown_worker():
            while True:
                with self.lock:
                    if self.current_state != STATE_FALL_COUNTDOWN:
                        break
                    rem = self.countdown_remaining

                if self.on_countdown_tick:
                    self.on_countdown_tick(rem)

                if rem <= 0:
                    self._confirm_emergency_fall()
                    break

                time.sleep(1.0)
                with self.lock:
                    self.countdown_remaining -= 1

        self.countdown_thread = threading.Thread(target=_countdown_worker, daemon=True, name="CountdownThread")
        self.countdown_thread.start()

    def _confirm_emergency_fall(self):
        """Countdown expired without user cancellation: trigger full emergency."""
        with self.lock:
            if self.current_state != STATE_FALL_COUNTDOWN:
                return
            self.current_state = STATE_EMERGENCY_ALARM

        logger.critical("🚨 EMERGENCY CONFIRMED! User did not cancel. Activating buzzer & emergency alert.")
        self.start_buzzer()

        if self.on_fall_confirmed:
            self.on_fall_confirmed()

    def cancel_or_safe_pressed(self):
        """Called when user presses the cancel/safe button or clicks safe switch."""
        with self.lock:
            prev_state = self.current_state
            self.current_state = STATE_MONITORING
            self.countdown_remaining = 0

        self.stop_buzzer()

        if prev_state in (STATE_FALL_COUNTDOWN, STATE_EMERGENCY_ALARM):
            logger.info("✅ Fall alert CANCELLED by user button press. Returning to normal monitoring.")
            if self.on_alert_cancelled:
                self.on_alert_cancelled()
        else:
            logger.info("Button pressed in normal monitoring state.")

    def start_buzzer(self):
        """Starts audible pulsating emergency buzzer."""
        with self.lock:
            if self.buzzer_active:
                return
            self.buzzer_active = True

        def _buzzer_worker():
            logger.info("📢 Buzzer active: sounding emergency alarm.")
            while self.buzzer_active:
                if self.hardware_active and self._gpio:
                    try:
                        self._gpio.output(self.buzzer_pin, self._gpio.HIGH)
                        time.sleep(0.3)
                        self._gpio.output(self.buzzer_pin, self._gpio.LOW)
                        time.sleep(0.2)
                    except Exception:
                        break
                else:
                    time.sleep(0.5)

        self.buzzer_thread = threading.Thread(target=_buzzer_worker, daemon=True, name="BuzzerThread")
        self.buzzer_thread.start()

    def stop_buzzer(self):
        """Stops the emergency buzzer immediately."""
        with self.lock:
            self.buzzer_active = False
        if self.hardware_active and self._gpio:
            try:
                self._gpio.output(self.buzzer_pin, self._gpio.LOW)
            except Exception:
                pass

    def get_state(self) -> str:
        """Returns the current system operational state."""
        with self.lock:
            return self.current_state

    def stop(self):
        """Releases all alert and GPIO resources."""
        self.stop_buzzer()
        if self.hardware_active and self._gpio:
            try:
                self._gpio.cleanup((self.buzzer_pin, self.button_pin))
            except Exception:
                pass
        logger.info("Alert manager stopped.")
