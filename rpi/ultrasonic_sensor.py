"""
Ultrasonic Sensor Driver (HC-SR04) for Raspberry Pi
===================================================
Uses BCM GPIO23 (TRIG) and BCM GPIO24 (ECHO).
CRITICAL: ECHO pin outputs 5V. Must be stepped down to ~3.3V using
a 1kΩ / 2kΩ resistor voltage divider before connecting to BCM GPIO24.

Features:
- Non-blocking background thread sampling at 20 Hz
- 5-sample median filtering to reject noisy spikes and reflections
- Out-of-range and timeout protection
- Simulated fallback mode for headless/desktop testing
"""

import time
import threading
from typing import List
from rpi.config import (
    PINS,
    ULTRASONIC_SAMPLE_INTERVAL_SEC,
    ULTRASONIC_TIMEOUT_SEC,
    ULTRASONIC_MEDIAN_WINDOW,
    DISTANCE_MAX_VALID_CM,
    DISTANCE_MIN_VALID_CM
)
from rpi.logging_config import setup_logger

logger = setup_logger("UltrasonicSensor")

class UltrasonicSensor:
    def __init__(self, trig_bcm: int = PINS["ULTRASONIC_TRIG"]["bcm"],
                 echo_bcm: int = PINS["ULTRASONIC_ECHO"]["bcm"],
                 simulated: bool = False):
        self.trig_pin = trig_bcm
        self.echo_pin = echo_bcm
        self.simulated = simulated
        self.hardware_active = False

        self.samples: List[float] = [200.0] * ULTRASONIC_MEDIAN_WINDOW
        self.last_distance = 200.0
        self.lock = threading.Lock()
        self.is_running = False
        self.thread = None

        self._gpio = None
        if not self.simulated:
            self._init_gpio()

    def _init_gpio(self):
        """Initializes hardware GPIO pins."""
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.trig_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            GPIO.output(self.trig_pin, GPIO.LOW)
            time.sleep(0.05)
            self.hardware_active = True
            logger.info(f"✅ HC-SR04 initialized (TRIG: BCM {self.trig_pin}, ECHO: BCM {self.echo_pin} via divider).")
        except (ImportError, RuntimeError) as e:
            logger.warning(f"RPi.GPIO unavailable ({e}). Running HC-SR04 in SIMULATED mode.")
            self.simulated = True
            self.hardware_active = False

    def _measure_raw_distance(self) -> float:
        """Sends a 10µs pulse and measures the echo return time."""
        if not self.hardware_active or self.simulated:
            return self.last_distance

        GPIO = self._gpio
        try:
            # Send 10 microsecond trigger pulse
            GPIO.output(self.trig_pin, GPIO.LOW)
            time.sleep(0.000002)
            GPIO.output(self.trig_pin, GPIO.HIGH)
            time.sleep(0.000010)
            GPIO.output(self.trig_pin, GPIO.LOW)

            # Wait for echo to go HIGH (start of pulse)
            pulse_start = time.time()
            timeout_start = pulse_start
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                pulse_start = time.time()
                if pulse_start - timeout_start > ULTRASONIC_TIMEOUT_SEC:
                    return DISTANCE_MAX_VALID_CM

            # Wait for echo to go LOW (end of pulse)
            pulse_end = pulse_start
            timeout_end = time.time()
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                pulse_end = time.time()
                if pulse_end - timeout_end > ULTRASONIC_TIMEOUT_SEC:
                    return DISTANCE_MAX_VALID_CM

            duration = pulse_end - pulse_start
            # Speed of sound = 34300 cm/s -> distance = (duration * 34300) / 2
            distance = (duration * 34300.0) / 2.0

            if distance < DISTANCE_MIN_VALID_CM or distance > DISTANCE_MAX_VALID_CM:
                return DISTANCE_MAX_VALID_CM

            return round(distance, 1)

        except Exception as e:
            logger.debug(f"Raw measurement exception: {e}")
            return DISTANCE_MAX_VALID_CM

    def _update_median(self, raw_val: float) -> float:
        """Appends to sample window and calculates median."""
        with self.lock:
            self.samples.pop(0)
            self.samples.append(raw_val)
            sorted_samples = sorted(self.samples)
            median_val = sorted_samples[len(sorted_samples) // 2]
            self.last_distance = median_val
            return median_val

    def _worker(self):
        """Continuous background sampling worker."""
        while self.is_running:
            raw = self._measure_raw_distance()
            self._update_median(raw)
            time.sleep(ULTRASONIC_SAMPLE_INTERVAL_SEC)

    def start(self):
        """Starts background sampling."""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._worker, daemon=True, name="UltrasonicThread")
            self.thread.start()
            logger.info("Ultrasonic background measurement started.")

    def get_distance(self) -> float:
        """Returns the current filtered distance in centimeters."""
        with self.lock:
            return self.last_distance

    def set_simulated_distance(self, distance_cm: float):
        """Sets distance manually during testing or simulation."""
        self.simulated = True
        self._update_median(distance_cm)
        logger.info(f"[SIMULATION] Injected ultrasonic distance: {distance_cm:.1f} cm")

    def stop(self):
        """Stops sampling and cleans up GPIO."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        if self.hardware_active and self._gpio:
            try:
                self._gpio.cleanup((self.trig_pin, self.echo_pin))
            except Exception:
                pass
        logger.info("Ultrasonic sensor stopped.")
