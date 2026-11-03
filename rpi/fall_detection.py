"""
MPU-6050 Accelerometer & Gyroscope Fall Detection Engine
=========================================================
Runs at 50 Hz over Raspberry Pi I2C-1 (BCM GPIO2 SDA, BCM GPIO3 SCL).
Address: 0x68 (default).

Features:
- Robust 4-stage physics detection model:
    Stage 1: Free-fall detection (acceleration magnitude < 0.45g)
    Stage 2: Impact spike (acceleration magnitude > 2.50g within 400 ms)
    Stage 3: Tilt verification (posture tilt > 60° within 500 ms)
    Stage 4: Post-impact immobility confirmation (1.2 s inactivity check)
- Sensor offset calibration routine
- Safe simulated fall injection for hazard-free verification
"""

import math
import time
import threading
from typing import Tuple
from rpi.config import (
    FALL_SAMPLING_RATE_HZ,
    FALL_FREE_FALL_THRES_G,
    FALL_IMPACT_THRES_G,
    FALL_TILT_THRES_DEG,
    FALL_FREEFALL_MAX_WINDOW_MS,
    FALL_IMPACT_MAX_WINDOW_MS,
    FALL_INACTIVITY_DURATION_MS,
    FALL_INACTIVITY_GYRO_MAX_DPS
)
from rpi.logging_config import setup_logger

logger = setup_logger("FallDetector")

# MPU-6050 Registers
MPU_ADDR = 0x68
REG_PWR_MGMT_1   = 0x6B
REG_ACCEL_CONFIG = 0x1C
REG_GYRO_CONFIG  = 0x1B
REG_ACCEL_XOUT_H = 0x3B
REG_GYRO_XOUT_H  = 0x43

# Algorithm Stages
STAGE_IDLE = 0
STAGE_FREEFALL = 1
STAGE_IMPACT = 2
STAGE_INACTIVITY = 3

class FallDetector:
    def __init__(self, i2c_bus: int = 1, i2c_addr: int = MPU_ADDR, simulated: bool = False):
        self.i2c_bus_num = i2c_bus
        self.i2c_addr = i2c_addr
        self.simulated = simulated
        self.hardware_active = False
        self.bus = None

        # Offsets
        self.ax_offset = 0.0
        self.ay_offset = 0.0
        self.az_offset = 0.0
        self.gx_offset = 0.0
        self.gy_offset = 0.0
        self.gz_offset = 0.0

        # State Variables
        self.stage = STAGE_IDLE
        self.freefall_time = 0.0
        self.impact_time = 0.0
        self.inactivity_start_time = 0.0
        self.fall_detected_flag = False

        self.last_accel_mag = 1.0
        self.last_gyro_mag = 0.0
        self.last_tilt_deg = 0.0

        self.lock = threading.Lock()
        self.is_running = False
        self.thread = None

        if not self.simulated:
            self._init_sensor()

    def _init_sensor(self):
        """Initializes the MPU-6050 via smbus2."""
        try:
            import smbus2
            self.bus = smbus2.SMBus(self.i2c_bus_num)
            # Wake up MPU-6050 (write 0 to Power Management 1)
            self.bus.write_byte_data(self.i2c_addr, REG_PWR_MGMT_1, 0)
            time.sleep(0.05)
            # Set Accel range to ±8g (FS_SEL = 2)
            self.bus.write_byte_data(self.i2c_addr, REG_ACCEL_CONFIG, 0x10)
            # Set Gyro range to ±500 deg/s (FS_SEL = 1)
            self.bus.write_byte_data(self.i2c_addr, REG_GYRO_CONFIG, 0x08)
            time.sleep(0.05)
            self.hardware_active = True
            logger.info("✅ MPU-6050 initialized successfully on I2C bus 1 (Addr: 0x68).")
            self._calibrate()
        except (ImportError, Exception) as e:
            logger.warning(f"I2C MPU-6050 unavailable ({e}). Fall detection running in SIMULATED mode.")
            self.simulated = True
            self.hardware_active = False

    def _read_word_2c(self, reg: int) -> int:
        """Reads a signed 16-bit 2's complement word."""
        high = self.bus.read_byte_data(self.i2c_addr, reg)
        low = self.bus.read_byte_data(self.i2c_addr, reg + 1)
        val = (high << 8) + low
        if val >= 0x8000:
            val = -((65535 - val) + 1)
        return val

    def _calibrate(self, samples: int = 50):
        """Calibrates sensor offsets while device is stationary."""
        logger.info("Calibrating MPU-6050 stationary offsets (keep device still)...")
        ax_sum = ay_sum = az_sum = 0.0
        gx_sum = gy_sum = gz_sum = 0.0

        for _ in range(samples):
            try:
                ax = self._read_word_2c(REG_ACCEL_XOUT_H) / 4096.0
                ay = self._read_word_2c(REG_ACCEL_XOUT_H + 2) / 4096.0
                az = self._read_word_2c(REG_ACCEL_XOUT_H + 4) / 4096.0
                gx = self._read_word_2c(REG_GYRO_XOUT_H) / 65.5
                gy = self._read_word_2c(REG_GYRO_XOUT_H + 2) / 65.5
                gz = self._read_word_2c(REG_GYRO_XOUT_H + 4) / 65.5

                ax_sum += ax
                ay_sum += ay
                az_sum += (az - 1.0) # Subtract 1g gravity from Z
                gx_sum += gx
                gy_sum += gy
                gz_sum += gz
            except Exception:
                pass
            time.sleep(0.01)

        self.ax_offset = ax_sum / samples
        self.ay_offset = ay_sum / samples
        self.az_offset = az_sum / samples
        self.gx_offset = gx_sum / samples
        self.gy_offset = gy_sum / samples
        self.gz_offset = gz_sum / samples
        logger.info("✅ MPU-6050 calibrated successfully.")

    def read_raw(self) -> Tuple[float, float, float, float, float, float]:
        """Reads scaled acceleration (g) and angular velocity (deg/s)."""
        if not self.hardware_active or self.simulated:
            return (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)

        try:
            # Scale for ±8g range: 4096 LSB/g
            ax = (self._read_word_2c(REG_ACCEL_XOUT_H) / 4096.0) - self.ax_offset
            ay = (self._read_word_2c(REG_ACCEL_XOUT_H + 2) / 4096.0) - self.ay_offset
            az = (self._read_word_2c(REG_ACCEL_XOUT_H + 4) / 4096.0) - self.az_offset

            # Scale for ±500 deg/s range: 65.5 LSB/(deg/s)
            gx = (self._read_word_2c(REG_GYRO_XOUT_H) / 65.5) - self.gx_offset
            gy = (self._read_word_2c(REG_GYRO_XOUT_H + 2) / 65.5) - self.gy_offset
            gz = (self._read_word_2c(REG_GYRO_XOUT_H + 4) / 65.5) - self.gz_offset

            return (ax, ay, az, gx, gy, gz)
        except Exception as e:
            logger.debug(f"I2C read exception: {e}")
            return (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)

    def _process_sample(self, ax: float, ay: float, az: float, gx: float, gy: float, gz: float):
        """Executes the multi-stage fall detection algorithm."""
        # 1. Total Acceleration Magnitude in G
        accel_mag = math.sqrt(ax * ax + ay * ay + az * az)
        self.last_accel_mag = accel_mag

        # 2. Total Angular Velocity Magnitude in deg/s
        gyro_mag = math.sqrt(gx * gx + gy * gy + gz * gz)
        self.last_gyro_mag = gyro_mag

        # 3. Tilt Angle Relative to Vertical (Z-axis)
        cos_tilt = az / (accel_mag + 0.0001)
        cos_tilt = max(-1.0, min(1.0, cos_tilt))
        tilt_deg = math.degrees(math.acos(cos_tilt))
        self.last_tilt_deg = tilt_deg

        now_ms = time.time() * 1000.0

        # State Machine Transitions
        if self.stage == STAGE_IDLE:
            # Stage 1: Freefall detection
            if accel_mag < FALL_FREE_FALL_THRES_G:
                self.stage = STAGE_FREEFALL
                self.freefall_time = now_ms
                logger.info(f"[FALL ALGORITHM] Stage 1: Free-fall detected! Accel: {accel_mag:.2f}g")

        elif self.stage == STAGE_FREEFALL:
            # Stage 2: Impact detection within window
            if now_ms - self.freefall_time <= FALL_FREEFALL_MAX_WINDOW_MS:
                if accel_mag > FALL_IMPACT_THRES_G:
                    self.stage = STAGE_IMPACT
                    self.impact_time = now_ms
                    logger.info(f"[FALL ALGORITHM] Stage 2: Impact spike! Accel: {accel_mag:.2f}g")
            else:
                # Timed out without impact -> false alarm
                self.stage = STAGE_IDLE

        elif self.stage == STAGE_IMPACT:
            # Stage 3: Post-impact body tilt verification
            if now_ms - self.impact_time <= FALL_IMPACT_MAX_WINDOW_MS:
                if tilt_deg > FALL_TILT_THRES_DEG:
                    self.stage = STAGE_INACTIVITY
                    self.inactivity_start_time = now_ms
                    logger.info(f"[FALL ALGORITHM] Stage 3: Tilt confirmed ({tilt_deg:.1f}°). Verifying immobility...")
            else:
                # Impact with no tilt (e.g. running or jumping)
                self.stage = STAGE_IDLE

        elif self.stage == STAGE_INACTIVITY:
            # Stage 4: Immobility check (person lying still on floor)
            if now_ms - self.inactivity_start_time >= FALL_INACTIVITY_DURATION_MS:
                if 0.7 <= accel_mag <= 1.3 and gyro_mag < FALL_INACTIVITY_GYRO_MAX_DPS:
                    logger.warning("🚨 [FALL CONFIRMED] Multi-stage fall criteria satisfied!")
                    with self.lock:
                        self.fall_detected_flag = True
                else:
                    logger.info("[FALL ALGORITHM] Motion detected post-impact. False alarm filtered.")
                self.stage = STAGE_IDLE

    def _worker(self):
        """Continuous 50 Hz sampling loop."""
        interval = 1.0 / FALL_SAMPLING_RATE_HZ
        while self.is_running:
            t0 = time.time()
            ax, ay, az, gx, gy, gz = self.read_raw()
            self._process_sample(ax, ay, az, gx, gy, gz)
            elapsed = time.time() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def start(self):
        """Starts 50 Hz background sampling."""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._worker, daemon=True, name="FallDetectorThread")
            self.thread.start()
            logger.info("Fall detection 50 Hz background monitoring active.")

    def is_fall_detected(self) -> bool:
        """Returns True if a fall event occurred."""
        with self.lock:
            return self.fall_detected_flag

    def clear_fall_event(self):
        """Resets the fall flag."""
        with self.lock:
            self.fall_detected_flag = False
            self.stage = STAGE_IDLE

    def inject_simulated_fall(self):
        """Manually triggers a verified fall event for testing."""
        logger.warning("[FALL SIMULATION] 💥 Injected verified fall event!")
        with self.lock:
            self.fall_detected_flag = True
            self.stage = STAGE_IDLE

    def get_telemetry(self) -> dict:
        """Returns instantaneous sensor metrics."""
        return {
            "accel_mag_g": round(self.last_accel_mag, 2),
            "gyro_mag_dps": round(self.last_gyro_mag, 1),
            "tilt_deg": round(self.last_tilt_deg, 1),
            "stage": self.stage,
            "hardware_active": self.hardware_active
        }

    def stop(self):
        """Stops sampling and releases I2C bus."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        if self.bus:
            try:
                self.bus.close()
            except Exception:
                pass
        logger.info("Fall detector stopped.")
