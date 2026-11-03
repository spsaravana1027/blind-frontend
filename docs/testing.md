# Comprehensive Testing Plan & Verification Guide

This document outlines the test methodology, step-by-step module verification, multi-stage fall detection validation, false-alarm rejection tests, and network resilience recovery procedures.

---

## 1. Modular Subsystem Standalone Testing

### A. MPU6050 IMU Fall Detector
1. **Serial CLI Command:** Type `status` in the Serial monitor.
2. **Expected Output:** Verify `MPU Accel Mag` displays `~1.00 g` at rest, and `MPU Tilt Angle` displays `~0.0 deg` when horizontal.
3. **Physical Verification:** Tilt the device 90 degrees. Verify tilt reading updates to `~90.0 deg`.

### B. HC-SR04 Ultrasonic Distance Sensor & Camera Obstacle Coordination
1. **Serial CLI Command:** Type `dist 35` followed by `obj chair center`.
2. **Expected Output:** Verify `Ultrasonic Distance` reports `35.0 cm` (Near Obstacle).
3. **Voice Prompt Verification:** Speaker announces: *"எச்சரிக்கை! பொருள் அருகில் உள்ளது. முன்னால் நாற்காலி உள்ளது."*
4. **Quiet Buzzer Rule:** Verify active buzzer remains completely SILENT (buzzer is never sounded for obstacles).

### C. MAX98357A I2S Audio Player
1. **Serial CLI Command:** Type `status`.
2. **Hardware Test:** On bootup/connection, verify speaker plays *"அமைப்பு தயார். இணைக்கப்பட்டது."*

### D. Vision Link, Medicine & Currency Recognition
1. **Server Test:** Run `python server/app.py` in one shell and `python server/test_server.py` in another shell.
2. **Expected Output:** All 5 test suites PASS:
   - Near obstacle warning: *"எச்சரிக்கை! பொருள் அருகில் உள்ளது."*
   - Medicine recognition: Paracetamol, Rantac, Tassic Tanic in Tamil speech.
   - Currency recognition: 500 Rs note ("idhu 500 rupaai" / *"இது 500 ரூபாய்."*).
   - Immediate fall alert & safe switch Telegram dispatch.
3. **ESP32 CLI Test:**
   - Type `med paracetamol` -> Speaker says: *"இது பாராசிட்டமால் மாத்திரை."*
   - Type `med rantac` -> Speaker says: *"இது ரான்டாக் மாத்திரை."*
   - Type `med tassic` -> Speaker says: *"இது டாசிக் டானிக் மருந்து."*
   - Type `curr 500` -> Speaker says: *"இது 500 ரூபாய்."*

---

## 2. Multi-Stage Fall Detection Test Matrix

| Test ID | Test Scenario | Simulated Physical Motion | Expected State Transition | Expected System Output | Result |
|---|---|---|---|---|---|
| **TC-FALL-01** | True Real Fall | Drop unit 0.5m onto pad -> impact spike >2.5g -> leave on side (>60° tilt) for 1.5s | `IDLE` -> `FREEFALL` -> `IMPACT` -> `TILT_CHECK` -> `FALL_CONFIRMED` | Alarm Siren ON + Speaker Emergency prompt + Immediate Telegram alert dispatched | PASS |
| **TC-FALL-02** | False Alarm: Jumping / Running | Hard step or jump (Impact >3g), stay upright (Tilt <20°) | `IDLE` -> `IMPACT` -> Timeout -> `IDLE` | No false fall triggered. System remains in `MONITORING`. | PASS |
| **TC-FALL-03** | False Alarm: Bending Down | Slow tilt >70° to pick up item (no freefall, no impact) | `IDLE` (no freefall or impact) | No false fall triggered. | PASS |
| **TC-FALL-04** | False Alarm: Dropping Sensor Unit | Dropped onto carpet (Freefall + Impact), but sensor rolls back upright (Tilt <30°) | `FREEFALL` -> `IMPACT` -> `TILT_CHECK` -> Timeout -> `IDLE` | No false fall triggered. | PASS |

---

## 3. Immediate Fall Alarm & Safe Switch Notification Test

1. **Trigger Fall:** Type `fall` in Serial CLI or click Fall button in webcam assistant.
2. **Verify Immediate Alarm & Alert:**
   - Buzzer siren starts immediately.
   - Emergency Tamil prompt plays in speaker: *"அவசரம்! கீழே விழுந்துவிட்டீர்கள்."*
   - Emergency Telegram alert is immediately enqueued and dispatched to guardian.
3. **Test Safe Switch:**
   - Press physical Pushbutton (GPIO 19) or type `safe` / `cancel` in CLI (or click on-screen Safe Switch).
   - **Expected Outcome:** Buzzer turns OFF immediately. Speaker announces *"பாதுகாப்பாக உள்ளீர்கள். எச்சரிக்கை நிறுத்தப்பட்டது."*. Telegram dispatches safe message confirming user is safe.

---

## 4. Wi-Fi Loss & Resiliency Test

1. Disconnect home Wi-Fi router / mobile hotspot.
2. Trigger fall event (`fall`), allow 15s timer to expire.
3. **Verify Offline Behavior:**
   - Local buzzer siren and Tamil audio alerts continue uninterrupted.
   - Serial monitor reports `[TELEGRAM QUEUE] Enqueued emergency alert. Queue size: 1`.
4. Re-enable Wi-Fi connection / hotspot.
5. **Verify Auto-Recovery:**
   - System re-establishes Wi-Fi connection automatically.
   - Background Telegram queue flushes queued message to caregiver's Telegram chat.
