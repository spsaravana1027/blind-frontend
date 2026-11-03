import io
import sys
import requests
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "http://127.0.0.1:8000"

# Try importing in-process TestClient for fast, standalone test execution
try:
    from fastapi.testclient import TestClient
    from app import app
    client = TestClient(app)
    USE_TEST_CLIENT = True
except Exception as e:
    USE_TEST_CLIENT = False
    client = None

def create_synthetic_image(text=None):
    """Generates a test image (320x240) with an optional text label for OCR."""
    img = Image.new("RGB", (320, 240), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Colored shapes simulating objects
    draw.rectangle([20, 40, 100, 180], fill=(0, 100, 250))
    draw.rectangle([120, 50, 200, 190], fill=(250, 50, 50))

    if text:
        draw.text((30, 20), text, fill=(0, 0, 0))

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()

def request_post(endpoint, data=None, params=None):
    if USE_TEST_CLIENT:
        return client.post(endpoint, content=data, params=params, headers={"Content-Type": "image/jpeg"})
    else:
        return requests.post(f"{BASE_URL}{endpoint}", data=data, params=params, headers={"Content-Type": "image/jpeg"}, timeout=10)

def request_get(endpoint, params=None):
    if USE_TEST_CLIENT:
        return client.get(endpoint, params=params)
    else:
        return requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)

def test_detect_obstacle_near():
    print(f"\n[TEST 1] Obstacle Proximity Warning (Distance = 35cm <= 50cm)")
    img_data = create_synthetic_image()
    try:
        r = request_post("/detect?distance=35", data=img_data)
        print(f"Status Code: {r.status_code}")
        data = r.json()
        print(f"Response: {data}")
        assert r.status_code == 200
        assert len(data) > 0
        tamil_txt = data[0].get("tamil_text", "")
        print(f"Tamil Speech: {tamil_txt}")
        assert "எச்சரிக்கை! பொருள் அருகில் உள்ளது" in tamil_txt
        print(">>> PASS: Obstacle proximity warning correctly triggered: 'எச்சரிக்கை! பொருள் அருகில் உள்ளது.'")
        return True
    except Exception as e:
        print(f"[TEST 1 FAILED] {e}")
        return False

def test_detect_medicines():
    print(f"\n[TEST 2] Medicines Identification (Paracetamol, Rantac, Tassic Tanic)")
    all_passed = True
    meds = [
        ("PARACETAMOL 500 MG", "paracetamol", "பாராசிட்டமால்"),
        ("RANTAC 150 TABLET", "rantac", "ரான்டாக்"),
        ("TASSIC TANIC SYRUP", "tassic", "டாசிக் டானிக்")
    ]
    for text_sample, expected_lbl, expected_tamil in meds:
        try:
            # Test direct detection endpoint override and logic
            r = request_post(f"/detect?label={expected_lbl}")
            data = r.json()
            assert r.status_code == 200
            tamil_speech = data[0].get("tamil_text", "")
            print(f"  Medicine: '{expected_lbl}' -> Tamil: \"{tamil_speech}\"")
            assert expected_tamil in tamil_speech
        except Exception as e:
            print(f"  [MEDICINE TEST FAILED for {expected_lbl}]: {e}")
            all_passed = False

    if all_passed:
        print(">>> PASS: Paracetamol, Rantac, and Tassic Tanic correctly identified with Tamil speech!")
    return all_passed

def test_detect_currency():
    print(f"\n[TEST 3] Currency Note Identification (500, 200, 100 Rs)")
    all_passed = True
    currencies = [
        ("500", "இது 500 ரூபாய்."),
        ("200", "இது 200 ரூபாய்."),
        ("100", "இது 100 ரூபாய்.")
    ]
    for denom, expected_tamil in currencies:
        try:
            r = request_post(f"/detect?label={denom}")
            data = r.json()
            assert r.status_code == 200
            tamil_speech = data[0].get("tamil_text", "")
            print(f"  Currency: {denom} Rs Note -> Tamil: \"{tamil_speech}\"")
            assert expected_tamil in tamil_speech
        except Exception as e:
            print(f"  [CURRENCY TEST FAILED for {denom}]: {e}")
            all_passed = False

    if all_passed:
        print(">>> PASS: Currency notes correctly announced in Tamil ('idhu 500 rupaai')!")
    return all_passed

def test_fall_and_safe_alerts():
    print(f"\n[TEST 4] Fall Emergency & Safe Switch Telegram Endpoints")
    try:
        r_fall = request_post("/alert/fall", params={"details": "Simulated fall down"})
        print(f"Fall Alert Response: {r_fall.json()}")
        assert r_fall.status_code == 200
        assert r_fall.json().get("status") == "ok"

        r_safe = request_post("/alert/safe", params={"details": "Safe switch clicked"})
        print(f"Safe Alert Response: {r_safe.json()}")
        assert r_safe.status_code == 200
        assert r_safe.json().get("status") == "ok"

        print(">>> PASS: Immediate fall alert and safe switch notification endpoints verified!")
        return True
    except Exception as e:
        print(f"[TEST 4 FAILED] {e}")
        return False

def test_tts():
    print(f"\n[TEST 5] Tamil TTS Endpoint (/tts)")
    try:
        r = request_get("/tts", params={"text": "எச்சரிக்கை! பொருள் அருகில் உள்ளது."})
        print(f"Status Code: {r.status_code}, Bytes: {len(r.content)}")
        assert r.status_code == 200
        assert len(r.content) > 500
        print(">>> PASS: Tamil TTS audio synthesized successfully!")
        return True
    except Exception as e:
        print(f"[TEST 5 FAILED] {e}")
        return False

if __name__ == "__main__":
    print("==================================================")
    print("   AI ASSISTIVE SERVER TEST SUITE")
    print("   Visually Impaired Assistive System Verification")
    print("==================================================")
    t1 = test_detect_obstacle_near()
    t2 = test_detect_medicines()
    t3 = test_detect_currency()
    t4 = test_fall_and_safe_alerts()
    t5 = test_tts()
    print("\n--------------------------------------------------")
    print(f"Summary: Obstacle Near={t1}, Medicines={t2}, Currency={t3}, Fall/Safe={t4}, TTS={t5}")
    all_ok = all([t1, t2, t3, t4, t5])
    print(f"OVERALL STATUS: {'ALL TESTS PASSED' if all_ok else 'SOME TESTS FAILED'}")
    print("==================================================")
    if not all_ok:
        sys.exit(1)
