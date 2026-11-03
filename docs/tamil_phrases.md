# Tamil Voice Assistant & MAX98357A I2S Audio Reference

This document lists all Tamil guidance phrases used by the device, their English translations, audio clip mapping, and I2S playback architecture via **MAX98357A**.

## 1. Master Tamil Voice Guidance Phrase Mapping

| Clip ID | Tamil Script Phrase | English Translation | System Trigger Condition |
|---|---|---|---|
| **01** | **அமைப்பு தயார். பாதுகாப்பான பயணம் அமைய வாழ்த்துகிறோம்.** | System Ready. Wish you a safe trip. | Power-on self-test pass |
| **02** | **அமைப்பில் கோளாறு. அமைப்பைச் சரிபார்க்கவும்.** | System Error. Please check hardware. | Boot self-test failure |
| **03** | **முன்னால் தடை உள்ளது. உடனே நின்று கவனிக்கவும்.** | Obstacle ahead! Stop immediately. | Ultrasonic distance \(\le 50\text{ cm}\) or vision immediate hazard |
| **04** | **முன்னால் குப்பைத்தொட்டி உள்ளது. கவனமாக விலகிச் செல்லவும்.** | Dustbin ahead. Move away carefully. | Vision detects dustbin/garbage bin in front |
| **05** | **இடது பக்கத்தில் நாய் உள்ளது. கவனமாக வலது பக்கம் செல்லவும்.** | Dog on left. Move carefully to the right. | Vision detects dog on left |
| **06** | **வலது பக்கத்தில் நாற்காலி உள்ளது. கவனமாக இடது பக்கம் செல்லவும்.** | Chair on right. Move carefully to the left. | Vision detects chair on right |
| **07** | **முன்னால் ஒருவர் உள்ளார். கவனமாகச் செல்லவும்.** | Person ahead. Move carefully. | Vision detects person in center |
| **08** | **முன்னால் கார் உள்ளது. பாதுகாப்பாக நிற்கவும்.** | Car ahead. Stop safely. | Vision detects car/vehicle in front |
| **09** | **முன்னால் மேஜை உள்ளது. கவனமாகச் செல்லவும்.** | Table ahead. Proceed with caution. | Vision detects table in front |
| **10** | **அவசரம்! கீழே விழுந்துவிட்டீர்கள். ரத்து செய்ய பொத்தானை அழுத்தவும்.** | Emergency! You fell down. Press button to cancel. | Fall confirmed (15s cancel active) |
| **11** | **அவசர எச்சரிக்கை ரத்து செய்யப்பட்டது.** | Emergency alert cancelled. | User pressed cancel push button |
| **12** | **பாதுகாவலருக்கு அவசரத் தகவல் அனுப்பப்பட்டது.** | Emergency alert sent to guardian. | 15s countdown expired, Telegram sent |
| **13** | **முன்னால் பொருள் உள்ளது.** | Obstacle notice. | Ultrasonic distance 51–120 cm |
| **14** | **எச்சரிக்கை! பொருள் அருகில் உள்ளது.** | Warning! Obstacle close. | Camera detects obstacle & ultrasonic \(\le 50\text{ cm}\) |
| **24** | **மருந்து எடுத்துக்கொள்ள வேண்டிய நேரம் வந்துவிட்டது. தயவுசெய்து உங்கள் மருந்தை எடுத்துக்கொள்ளுங்கள்.** | It is time to take your medicine. Please take your medicine. | 15-minute periodic medicine reminder |
| **30** | **இது பாராசிட்டமால் மாத்திரை.** | This is a Paracetamol tablet. | Camera identifies Paracetamol tablet |
| **31** | **இது ரான்டாக் மாத்திரை.** | This is a Rantac tablet. | Camera identifies Rantac tablet |
| **32** | **இது டாசிக் டானிக் மருந்து.** | This is Tassic Tanic medicine. | Camera identifies Tassic Tanic medicine |
| **33** | **இது 500 ரூபாய்.** | This is 500 Rupees. | Camera identifies 500 Rs note ("idhu 500 rupaai") |
| **34** | **இது 200 ரூபாய்.** | This is 200 Rupees. | Camera identifies 200 Rs note |
| **35** | **இது 100 ரூபாய்.** | This is 100 Rupees. | Camera identifies 100 Rs note |
| **36** | **இது 50 ரூபாய்.** | This is 50 Rupees. | Camera identifies 50 Rs note |
| **37** | **இது 20 ரூபாய்.** | This is 20 Rupees. | Camera identifies 20 Rs note |
| **38** | **இது 10 ரூபாய்.** | This is 10 Rupees. | Camera identifies 10 Rs note |
| **39** | **பாதுகாப்பாக உள்ளீர்கள். எச்சரிக்கை நிறுத்தப்பட்டது.** | You are safe. Alert stopped. | User clicked Safe Switch to turn off buzzer |
| **40** | **அமைப்பு தயார். இணைக்கப்பட்டது.** | System ready and connected. | Speaker sounds ready & connected greeting |

---

## 2. MAX98357A I2S Audio Architecture

The device uses **ESP32 native I2S digital audio** over three pins:
- **DIN:** GPIO 27
- **BCLK:** GPIO 26
- **LRC / WS:** GPIO 25

Audio sample generation is non-blocking. Synthesized PCM audio waveforms and multi-frequency acoustic envelopes are output directly over I2S to the MAX98357A amplifier driving a 3W speaker.

---

## 3. Server-Based Tamil TTS Generation (`/tts` Endpoint)

The Python FastAPI backend (`server/app.py`) includes a `/tts` endpoint leveraging Google Text-to-Speech (`gTTS`) to dynamically synthesize high-fidelity Tamil audio:

```bash
# Example HTTP GET request for Tamil TTS generation
curl "http://127.0.0.1:8000/tts?text=முன்னால்%20கார்%20உள்ளது" --output car_warning.mp3
```

This architecture allows offline-capable synthesized I2S announcements on the ESP32 while providing high-definition voice streaming over Wi-Fi when connected to the server.
