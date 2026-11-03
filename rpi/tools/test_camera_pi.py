"""
Diagnostic Tool: Raspberry Pi CSI Camera Test
==============================================
Validates CSI Ribbon Camera via Picamera2 (libcamera) and OpenCV.
Saves a captured frame as 'test_csi_capture.jpg'.
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

from rpi.camera_manager import CameraManager

def test_camera():
    print("\n--- [TEST 1/8] Raspberry Pi CSI Ribbon Camera ---")
    print("Testing camera initialization and frame capture...")

    cam = CameraManager(width=640, height=480, fps=15)
    success = cam.start()

    if not success:
        print("\n⚠️ WARNING: Hardware CSI camera was not detected.")
        print("Troubleshooting Checklist:")
        print("1. Did you connect the ribbon cable to the CSI port (labelled 'CAMERA' between HDMI and 3.5mm jack)?")
        print("   (Ensure the blue tape on the ribbon cable faces the 3.5mm audio jack / Ethernet port).")
        print("2. Run 'rpicam-hello' or 'libcamera-hello' on Raspberry Pi OS Bookworm/Bullseye.")
        print("3. Check '/boot/config.txt' or '/boot/firmware/config.txt' for 'camera_auto_detect=1'.")
        print("Continuing test with fallback frame...")

    time.sleep(1.0)
    frame = cam.capture_frame()

    if frame is not None and frame.shape[0] > 0:
        import cv2
        out_path = Path(__file__).resolve().parent / "test_csi_capture.jpg"
        cv2.imwrite(str(out_path), frame)
        print(f"✅ Camera frame captured successfully! Shape: {frame.shape}")
        print(f"📁 Image saved to: {out_path}")
    else:
        print("❌ Failed to capture frame from camera.")

    cam.stop()
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    test_camera()
