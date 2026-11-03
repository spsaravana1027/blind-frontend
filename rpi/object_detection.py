"""
Object Detection & Recognition Engine
======================================
Optimized for Raspberry Pi 3 CPU inference.
Supports:
1. YOLOv8 nano obstacle detection (person, chair, table, stairs, car, etc.)
2. Bounding-box spatial direction analysis (Left, Center, Right)
3. Proximity classification coordinated with ultrasonic sensor
4. Optional EasyOCR for Indian currency & medicines
"""

import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from rpi.config import (
    MODEL_PATH,
    VISION_CONFIDENCE_THRESHOLD,
    TARGET_OBSTACLES,
    OCR_ENABLED
)
from rpi.logging_config import setup_logger

logger = setup_logger("ObjectDetection")

class ObjectDetector:
    def __init__(self, model_path: str = str(MODEL_PATH)):
        self.model_path = model_path
        self.model = None
        self.ocr_reader = None
        self.is_loaded = False
        self._init_model()

    def _init_model(self):
        """Loads the YOLO model if available."""
        try:
            from ultralytics import YOLO
            import os
            if os.path.exists(self.model_path):
                logger.info(f"Loading YOLOv8 model from {self.model_path}...")
                self.model = YOLO(self.model_path)
                self.is_loaded = True
                logger.info("✅ YOLOv8 model loaded successfully.")
            else:
                logger.warning(f"Model file not found at {self.model_path}. Trying 'yolov8n.pt' auto-download...")
                self.model = YOLO("yolov8n.pt")
                self.is_loaded = True
                logger.info("✅ YOLOv8n auto-loaded.")
        except ImportError:
            logger.warning("ultralytics package not installed. Running in mock vision mode.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")

        if OCR_ENABLED:
            try:
                import easyocr
                logger.info("Initializing EasyOCR for medicines and currency...")
                self.ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                logger.info("✅ EasyOCR initialized.")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}")

    def detect_objects(self, frame: np.ndarray, ultrasonic_distance_cm: float = 200.0) -> List[Dict[str, Any]]:
        """
        Runs object detection on the input frame.
        Returns a list of detected objects with label, confidence, position, and proximity.
        """
        if not self.is_loaded or self.model is None or frame is None:
            return []

        h, w = frame.shape[:2]
        detections = []

        try:
            # Inference with imgsz=320 for Raspberry Pi 3 CPU performance
            results = self.model(frame, imgsz=320, conf=VISION_CONFIDENCE_THRESHOLD, verbose=False)[0]

            for box in results.boxes:
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                label = self.model.names[cls_id]

                if label not in TARGET_OBSTACLES:
                    continue

                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]
                bw, bh = max(x2 - x1, 1), max(y2 - y1, 1)

                # Spatial Position Classification
                center_x = (x1 + x2) / 2.0
                if center_x < w * 0.33:
                    pos = "left"
                elif center_x > w * 0.66:
                    pos = "right"
                else:
                    pos = "center"

                # Proximity assessment: combined optical size and ultrasonic reading
                rel_h = bh / float(h)
                is_near = (rel_h > 0.40) or (0.0 < ultrasonic_distance_cm <= 50.0)

                detections.append({
                    "label": label,
                    "confidence": round(conf, 2),
                    "position": pos,
                    "is_near": is_near,
                    "box": (x1, y1, x2, y2),
                    "area": bw * bh
                })

            # Sort by area (largest/closest obstacle first)
            detections.sort(key=lambda x: x["area"], reverse=True)

        except Exception as e:
            logger.error(f"Inference error: {e}")

        return detections

    def recognize_medicine_or_currency(self, frame: np.ndarray) -> Optional[Tuple[str, str, int]]:
        """
        Uses EasyOCR to recognize medicine labels or currency denominations.
        Returns: (label, tamil_phrase, clip_id) or None.
        """
        if self.ocr_reader is None or frame is None:
            return None

        try:
            import cv2
            small = cv2.resize(frame, (480, 360))
            ocr_results = self.ocr_reader.readtext(small)
            full_text = " ".join([res[1].lower() for res in ocr_results])
            if not full_text.strip():
                return None

            # 1. Medicines
            if any(w in full_text for w in ["paracetamol", "paracetomal", "dolo", "calpol", "crocin"]):
                return ("paracetamol", "இது பாராசிட்டமால் மாத்திரை.", 30)
            elif any(w in full_text for w in ["rantac", "ranitidine", "aciloc"]):
                return ("rantac", "இது ரான்டாக் மாத்திரை.", 31)
            elif any(w in full_text for w in ["tassic", "tanic", "tonic", "cough"]):
                return ("tassic", "இது டாசிக் டானிக் மருந்து.", 32)

            # 2. Currency
            if any(w in full_text for w in ["500", "five hundred", "५००"]):
                return ("500rs note", "இது 500 ரூபாய்.", 33)
            elif any(w in full_text for w in ["200", "two hundred"]):
                return ("200rs note", "இது 200 ரூபாய்.", 34)
            elif any(w in full_text for w in ["100", "one hundred"]):
                return ("100rs note", "இது 100 ரூபாய்.", 35)
            elif any(w in full_text for w in ["50", "fifty", "pachas"]):
                return ("50rs note", "இது 50 ரூபாய்.", 36)
            elif any(w in full_text for w in ["20", "twenty"]):
                return ("20rs note", "இது 20 ரூபாய்.", 37)
            elif any(w in full_text for w in ["10", "ten"]):
                return ("10rs note", "இது 10 ரூபாய்.", 38)

        except Exception as e:
            logger.warning(f"OCR recognition error: {e}")

        return None
