"""
Camera Manager for Raspberry Pi CSI Ribbon Camera
==================================================
Handles CSI camera capture with automatic backend detection:
1. Picamera2 (modern libcamera on Raspberry Pi OS Bookworm & Bullseye)
2. OpenCV VideoCapture (V4L2 fallback with bcm2835-v4l2 or USB camera)
3. Simulated test pattern fallback (for development/dry-run)
"""

import time
import numpy as np
from rpi.config import CAMERA_FRAME_WIDTH, CAMERA_FRAME_HEIGHT, CAMERA_FPS
from rpi.logging_config import setup_logger

logger = setup_logger("CameraManager")

class CameraManager:
    def __init__(self, width: int = CAMERA_FRAME_WIDTH, height: int = CAMERA_FRAME_HEIGHT, fps: int = CAMERA_FPS):
        self.width = width
        self.height = height
        self.fps = fps
        self.backend = None
        self.picam2 = None
        self.cv_cap = None
        self.is_running = False
        self.last_frame = None

    def start(self) -> bool:
        """Initializes the camera using the best available backend."""
        logger.info(f"Initializing camera ({self.width}x{self.height} @ {self.fps}fps)...")

        # 1. Try Picamera2 (Official library for Raspberry Pi OS Bookworm/Bullseye)
        try:
            from picam2 import Picamera2
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"}
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.backend = "picamera2"
            self.is_running = True
            logger.info("✅ CSI Camera initialized successfully via Picamera2 (libcamera).")
            return True
        except ImportError:
            logger.info("Picamera2 not installed. Checking for OpenCV V4L2 camera...")
        except Exception as e:
            logger.warning(f"Picamera2 init failed ({e}). Falling back to OpenCV V4L2...")

        # 2. Try OpenCV VideoCapture (V4L2 / bcm2835-v4l2 or USB webcam fallback)
        try:
            import cv2
            self.cv_cap = cv2.VideoCapture(0)
            if self.cv_cap and self.cv_cap.isOpened():
                self.cv_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cv_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cv_cap.set(cv2.CAP_PROP_FPS, self.fps)
                self.backend = "opencv"
                self.is_running = True
                logger.info("✅ Camera initialized successfully via OpenCV (V4L2 /dev/video0).")
                return True
            else:
                logger.warning("OpenCV could not open /dev/video0.")
        except Exception as e:
            logger.warning(f"OpenCV camera init error: {e}")

        # 3. Fallback: Simulation mode
        logger.error("❌ No physical camera detected! Starting in SIMULATION mode.")
        logger.info("HINT: On Raspberry Pi, ensure CSI ribbon is securely locked in CAMERA port and 'camera_auto_detect=1' is set in config.txt.")
        self.backend = "simulation"
        self.is_running = True
        return False

    def capture_frame(self) -> np.ndarray:
        """
        Captures a single BGR/RGB frame as a NumPy array.
        Returns:
            np.ndarray: Image array (H, W, 3) or synthetic frame on failure.
        """
        if not self.is_running:
            return self._generate_synthetic_frame("Camera Offline")

        if self.backend == "picamera2" and self.picam2:
            try:
                frame_rgb = self.picam2.capture_array()
                # Convert RGB to BGR for OpenCV compatibility
                import cv2
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                self.last_frame = frame_bgr
                return frame_bgr
            except Exception as e:
                logger.warning(f"Picamera2 capture error: {e}")
                return self._generate_synthetic_frame("Capture Error")

        elif self.backend == "opencv" and self.cv_cap:
            try:
                ret, frame = self.cv_cap.read()
                if ret and frame is not None:
                    self.last_frame = frame
                    return frame
                else:
                    logger.warning("OpenCV empty frame read.")
                    return self._generate_synthetic_frame("No Frame")
            except Exception as e:
                logger.warning(f"OpenCV capture error: {e}")
                return self._generate_synthetic_frame("Capture Error")

        else:
            return self._generate_synthetic_frame("Simulated Stream")

    def _generate_synthetic_frame(self, label: str) -> np.ndarray:
        """Generates a synthetic diagnostic frame for headless testing."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (40, 40, 40)
        try:
            import cv2
            cv2.putText(frame, f"Raspberry Pi 3 ({label})", (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            cv2.putText(frame, time.strftime("%H:%M:%S"), (15, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        except Exception:
            pass
        return frame

    def stop(self):
        """Releases camera hardware resources."""
        self.is_running = False
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None
        if self.cv_cap:
            try:
                self.cv_cap.release()
            except Exception:
                pass
            self.cv_cap = None
        logger.info("Camera resources released.")
