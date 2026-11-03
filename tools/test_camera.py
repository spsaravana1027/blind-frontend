import os
import sys
import time
import requests
import cv2

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Default ESP32-CAM IP (configurable via CLI or env)
CAM_IP = os.getenv("ESP32_CAM_IP", "192.168.29.50")

def test_camera():
    print("=" * 60)
    print("           ESP32-CAM & WEBCAM DIAGNOSTIC TEST")
    print("=" * 60)
    print(f"Target ESP32-CAM IP: http://{CAM_IP}")

    # 1. Test HTTP Snapshot endpoint
    snap_url = f"http://{CAM_IP}/capture"
    print(f"\n1. Testing HTTP snapshot endpoint: {snap_url}")
    cam_found = False
    try:
        t0 = time.time()
        r = requests.get(snap_url, timeout=3.0)
        t_elapsed = (time.time() - t0) * 1000
        if r.status_code == 200 and len(r.content) > 1000:
            print(f"✅ ESP32-CAM snapshot capture SUCCESS! ({len(r.content)} bytes in {t_elapsed:.1f}ms)")
            out_file = os.path.join(os.path.dirname(__file__), "test_capture_esp32cam.jpg")
            with open(out_file, "wb") as f:
                f.write(r.content)
            print(f"   Saved sample frame to: {out_file}")
            cam_found = True
        else:
            print(f"⚠️ HTTP response: {r.status_code} (length: {len(r.content)})")
    except Exception as e:
        print(f"ℹ️ ESP32-CAM HTTP endpoint not reachable at {snap_url}: {e}")

    # 2. Test MJPEG stream endpoint
    stream_url = f"http://{CAM_IP}:81/stream"
    print(f"\n2. Testing MJPEG stream endpoint: {stream_url}")
    try:
        cap = cv2.VideoCapture(stream_url)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"✅ MJPEG stream SUCCESS! Resolution: {w}x{h}")
                cam_found = True
            cap.release()
        else:
            print(f"ℹ️ Could not open stream at {stream_url}")
    except Exception as e:
        print(f"ℹ️ Stream test notice: {e}")

    # 3. Test Local Webcam (Index 0) fallback
    print("\n3. Testing Local PC Webcam (Index 0) as fallback:")
    try:
        cap_local = cv2.VideoCapture(0)
        if cap_local.isOpened():
            ret, frame = cap_local.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                print(f"✅ Local USB webcam is working properly! Resolution: {w}x{h}")
                out_file = os.path.join(os.path.dirname(__file__), "test_capture_local.jpg")
                cv2.imwrite(out_file, frame)
                print(f"   Saved local frame to: {out_file}")
            cap_local.release()
        else:
            print("ℹ️ Local USB webcam (Index 0) not found.")
    except Exception as e:
        print(f"❌ Local webcam test error: {e}")

    if not cam_found:
        print("\n" + "-" * 60)
        print("💡 SUMMARY & ACTION REQUIRED FOR ESP32-CAM:")
        print("  1. Verify the ESP32-CAM is powered with a stable 5V (>= 2A) supply.")
        print(f"  2. Check the IP assigned to your ESP32-CAM on your Wi-Fi router.")
        print(f"  3. Set ESP32_CAM_IP in environment or run: python tools/test_camera.py <YOUR_CAM_IP>")
        print("-" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        CAM_IP = sys.argv[1]
    test_camera()
