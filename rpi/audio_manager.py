"""
Audio & Tamil Voice Guidance Manager
====================================
Designed for MAX98357A I2S amplifier & speaker connected to Raspberry Pi.
Features:
- Preloads 35 real Tamil & English MP3 audio clips from the audio/ directory
- Zero-latency non-blocking background audio playback via pygame.mixer
- ALSA system fallback (mpg123 / aplay)
- Speech debounce timer to prevent repetitive voice spam
- Optional online gTTS dynamic fallback for arbitrary sentences
"""

import os
import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from rpi.config import (
    AUDIO_DIR,
    CLIP_MAP,
    CLIP_FILES,
    SPEECH_COOLDOWN_SEC,
    ENABLE_TTS_FALLBACK
)
from rpi.logging_config import setup_logger

logger = setup_logger("AudioManager")

class AudioManager:
    def __init__(self, audio_dir: Path = AUDIO_DIR):
        self.audio_dir = Path(audio_dir)
        self.have_pygame = False
        self.sounds: Dict[int, Any] = {}
        self.last_played_clip = 0
        self.last_played_time = 0.0
        self.is_playing = False
        self.lock = threading.Lock()

        self._init_player()

    def _init_player(self):
        """Initializes the audio playback engine."""
        try:
            import pygame
            if not pygame.mixer.get_init():
                # Initialize mixer for 44.1kHz, 16-bit, stereo/mono
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self.have_pygame = True
            logger.info("✅ Pygame audio mixer initialized.")
            self._preload_clips()
        except ImportError:
            logger.warning("pygame not installed. Audio will attempt system CLI fallback (mpg123/aplay).")
        except Exception as e:
            logger.warning(f"Pygame mixer init error: {e}. Falling back to CLI audio.")

    def _preload_clips(self):
        """Preloads all available audio clips into memory for instant playback."""
        import pygame
        loaded_count = 0
        for clip_id, filename in CLIP_FILES.items():
            filepath = self.audio_dir / filename
            if filepath.exists():
                try:
                    sound = pygame.mixer.Sound(str(filepath))
                    self.sounds[clip_id] = sound
                    loaded_count += 1
                except Exception as e:
                    logger.debug(f"Could not preload {filename}: {e}")
        logger.info(f"✅ Preloaded {loaded_count}/{len(CLIP_FILES)} Tamil voice clips from {self.audio_dir}.")

    def play_clip(self, clip_id_or_name: Any, force: bool = False, blocking: bool = False):
        """
        Plays an audio clip by integer ID or string name (e.g. 'obstacle_warning').
        Debounces repeated calls within SPEECH_COOLDOWN_SEC unless force=True.
        """
        clip_id = None
        if isinstance(clip_id_or_name, int):
            clip_id = clip_id_or_name
        elif isinstance(clip_id_or_name, str):
            clip_id = CLIP_MAP.get(clip_id_or_name)

        if clip_id is None:
            logger.warning(f"Unknown clip identifier: {clip_id_or_name}")
            return

        now = time.time()
        with self.lock:
            # Debounce check
            if not force and clip_id == self.last_played_clip and (now - self.last_played_time < SPEECH_COOLDOWN_SEC):
                return
            if not force and self.is_playing:
                return
            self.last_played_clip = clip_id
            self.last_played_time = now
            self.is_playing = True

        filename = CLIP_FILES.get(clip_id, f"clip_{clip_id}.mp3")

        def _play_worker():
            try:
                logger.info(f"🔊 Playing Audio Clip #{clip_id}: {filename}")
                # 1. Try Pygame Sound object
                if self.have_pygame and clip_id in self.sounds:
                    import pygame
                    channel = self.sounds[clip_id].play()
                    if channel:
                        while channel.get_busy():
                            time.sleep(0.05)
                    else:
                        time.sleep(self.sounds[clip_id].get_length())

                # 2. Try Pygame Music stream from file
                elif self.have_pygame and (self.audio_dir / filename).exists():
                    import pygame
                    pygame.mixer.music.load(str(self.audio_dir / filename))
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)

                # 3. System CLI fallback (Raspberry Pi ALSA / mpg123)
                else:
                    filepath = self.audio_dir / filename
                    if filepath.exists():
                        os.system(f"mpg123 -q '{filepath}' >/dev/null 2>&1 || aplay -q '{filepath}' >/dev/null 2>&1")
                    else:
                        logger.warning(f"Audio file missing: {filepath}")

            except Exception as e:
                logger.error(f"Error during audio playback: {e}")
            finally:
                with self.lock:
                    self.is_playing = False

        if blocking:
            _play_worker()
        else:
            threading.Thread(target=_play_worker, daemon=True, name="AudioPlaybackThread").start()

    def speak_tamil_text(self, tamil_text: str, force: bool = False):
        """
        Synthesizes arbitrary Tamil text via gTTS if online and enabled.
        """
        if not ENABLE_TTS_FALLBACK:
            logger.info(f"[TAMIL SPEECH NOTICE] TTS disabled. Text was: {tamil_text}")
            return

        def _tts_worker():
            try:
                import tempfile
                from gtts import gTTS
                logger.info(f"Synthesizing online Tamil TTS: '{tamil_text}'...")
                tts = gTTS(text=tamil_text, lang='ta')
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                    tmp_name = fp.name
                tts.save(tmp_name)

                if self.have_pygame:
                    import pygame
                    pygame.mixer.music.load(tmp_name)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                else:
                    os.system(f"mpg123 -q '{tmp_name}' >/dev/null 2>&1")

                try:
                    os.remove(tmp_name)
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"gTTS Tamil playback failed: {e}")

        threading.Thread(target=_tts_worker, daemon=True).start()

    def stop(self):
        """Stops any active audio playback."""
        if self.have_pygame:
            try:
                import pygame
                pygame.mixer.stop()
                pygame.mixer.music.stop()
            except Exception:
                pass
        with self.lock:
            self.is_playing = False
