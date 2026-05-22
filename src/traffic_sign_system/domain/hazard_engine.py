"""Rule-based hazard prediction with alert cooldown and temporal smoothing."""

import time
import threading
from collections import deque, Counter
from typing import List, Dict
from traffic_sign_system.config.sign_classes import get_hazard, HAZARD_LEVEL_PRIORITY


class HazardEngine:
    """
    Accepts sign detections and emits hazard alerts.

    Features:
    - Rule-based sign->hazard mapping
    - Per-sign alert cooldown (avoids alert spam)
    - Temporal smoothing (majority vote over a rolling window)
    - Thread-safe (can be polled from the UI thread)
    """

    def __init__(self, cfg: dict = None):
        cfg = cfg or {}
        hz_cfg = cfg.get("hazard", {})
        inf_cfg = cfg.get("inference", {})

        self.cooldown_sec  = hz_cfg.get("alert_cooldown_sec", 3)
        self.window_size   = inf_cfg.get("smoothing_window", 3)
        self.audio_enabled = hz_cfg.get("audio_enabled", False)
        self.tts_enabled   = hz_cfg.get("tts_enabled", False)

        self._last_alert: Dict[int, float] = {}
        self._window: deque = deque(maxlen=self.window_size)
        self.active_alerts: List[Dict] = []
        self._lock = threading.Lock()

        # Safe TTS initialization (only once)
        self.engine = None
        self.last_spoken = 0
        if self.tts_enabled:
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 160)
            except Exception as e:
                print(f"[TTS INIT ERROR] {e}")
                self.engine = None

    # -- Core update -----------------------------------------------------------
    def update(self, detections: List[Dict]) -> List[Dict]:
        now = time.time()
        frame_classes = [d["class_id"] for d in detections if "class_id" in d]

        with self._lock:
            self._window.append(frame_classes)
            all_ids = [cid for frame in self._window for cid in frame]
            if not all_ids:
                self.active_alerts = []
                return []

            id_counts = Counter(all_ids)
            threshold = max(1, len(self._window) // 2)
            stable_ids = [cid for cid, cnt in id_counts.items() if cnt >= threshold]

            alerts = []
            for cid in stable_ids:
                hz   = get_hazard(cid)
                last = self._last_alert.get(cid, 0)
                if now - last >= self.cooldown_sec:
                    self._last_alert[cid] = now
                    alerts.append(hz)

            alerts.sort(
                key=lambda h: HAZARD_LEVEL_PRIORITY.get(h["level"], 0),
                reverse=True,
            )
            self.active_alerts = alerts

        if alerts:
            self._dispatch_alerts(alerts)
        return alerts

    # -- Alert dispatch --------------------------------------------------------
    def _dispatch_alerts(self, alerts: List[Dict]):
        if not (self.tts_enabled or self.audio_enabled):
            return
        top = alerts[0]
        msg = f"Warning: {top['message']}. {top['action']}"

        if self.audio_enabled:
            threading.Thread(target=self.play_beep, daemon=True).start()

        if self.tts_enabled and self.engine:
            now = time.time()
            if now - self.last_spoken >= 2:
                self.last_spoken = now
                threading.Thread(target=self._speak, args=(msg,), daemon=True).start()

    def _speak(self, text: str):
        """Text-to-speech via pyttsx3 (cross-platform - Windows/Mac/Linux)."""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"[TTS] {e}")

    @staticmethod
    def play_beep(frequency: int = 1000, duration_ms: int = 300):
        """
        Play a beep tone using pygame.
        Replaces playsound which is broken on Python 3.12 / Windows.
        Falls back silently if pygame is not installed.
        """
        try:
            import pygame
            import numpy as np
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            sample_rate = 44100
            n_samples   = int(sample_rate * duration_ms / 1000)
            t    = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
            wave = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
            sound = pygame.sndarray.make_sound(wave)
            sound.play()
            pygame.time.wait(duration_ms)
        except Exception as e:
            print(f"[Audio] {e}")

    # -- Helpers ---------------------------------------------------------------
    def get_active_alerts(self) -> List[Dict]:
        with self._lock:
            return list(self.active_alerts)

    def reset(self):
        with self._lock:
            self._window.clear()
            self.active_alerts = []
            self._last_alert.clear()

    @staticmethod
    def hazard_level_color(level: str) -> tuple:
        """Returns BGR color for OpenCV overlay."""
        return {
            "critical": (60,  60,  226),
            "warning":  (39, 159,  239),
            "info":     (117, 139,  59),
        }.get(level, (128, 128, 128))
