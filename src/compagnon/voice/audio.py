"""Offline French voice: Piper (preferred) -> WAV cache -> pygame.mixer.

* each sentence is synthesised once and cached, so the voice is always identical (FC1);
* soft fade-in, never a sudden sound (FC2);
* nothing is recorded, nothing leaves the computer (FC5).
"""

from __future__ import annotations

import array
import hashlib
import math
import os
import threading
import wave
from pathlib import Path

import pygame

from compagnon.core.settings import Settings

DEFAULT_VOICE = "fr_FR-siwis-medium"
SAMPLE_RATE = 22050
FADE_MS = 120


class PiperEngine:
    def __init__(self, model_path: Path) -> None:
        from piper import PiperVoice

        self.voice = PiperVoice.load(str(model_path))
        self.name = f"piper:{model_path.stem}"

    def synthesize(self, text: str, out: Path, slow: bool) -> None:
        from piper import SynthesisConfig

        cfg = SynthesisConfig(length_scale=1.3 if slow else 1.0)
        with wave.open(str(out), "wb") as wf:
            self.voice.synthesize_wav(text, wf, syn_config=cfg)


def load_engine(voices_dir: Path, voice_name: str = DEFAULT_VOICE) -> PiperEngine | None:
    model = voices_dir / f"{voice_name}.onnx"
    if not model.exists():
        return None
    try:
        return PiperEngine(model)
    except Exception as exc:  # noqa: BLE001
        print(f"[voix] Piper indisponible : {exc}")
        return None


class PygameVoice:
    def __init__(self, cache_dir: Path, engine: PiperEngine | None) -> None:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.engine = engine
        self.volume = 0.7
        self.slow = False
        self.sounds = True
        self.muted = False
        self._lock = threading.Lock()
        self._chime = self._make_chime()
        self._voice_channel: pygame.mixer.Channel | None = None

    # ------------------------------------------------------------ Voice interface
    def configure(self, settings: Settings) -> None:
        self.volume = max(0, min(100, settings.volume)) / 100
        self.slow = settings.voice_rate == "lente"
        self.sounds = settings.sounds

    def say(self, text: str) -> None:
        if self.muted or self.volume <= 0 or self.engine is None:
            return
        path = self._wav(text)
        if path is None:
            return
        snd = pygame.mixer.Sound(str(path))
        snd.set_volume(self.volume)
        if self._voice_channel is not None:
            self._voice_channel.stop()
        self._voice_channel = snd.play(fade_ms=FADE_MS)

    def stop(self) -> None:
        pygame.mixer.fadeout(150)

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        if muted:
            self.stop()

    def chime(self) -> None:
        if self.muted or not self.sounds or self.volume <= 0:
            return
        self._chime.set_volume(self.volume * 0.6)
        self._chime.play(fade_ms=FADE_MS)

    # ------------------------------------------------------------ cache
    def preload(self, texts: list[str]) -> threading.Thread:
        """Synthesise the prepared phrases in the background at start-up."""
        th = threading.Thread(target=lambda: [self._wav(t) for t in texts], daemon=True)
        th.start()
        return th

    def _wav(self, text: str) -> Path | None:
        if self.engine is None:
            return None
        key = hashlib.sha1(f"{self.engine.name}|{self.slow}|{text}".encode()).hexdigest()[:16]
        path = self.cache_dir / f"{key}.wav"
        if path.exists():
            return path
        with self._lock:
            if path.exists():
                return path
            tmp = path.with_suffix(".tmp")
            try:
                self.engine.synthesize(text, tmp, self.slow)
                os.replace(tmp, path)
            except Exception as exc:  # noqa: BLE001
                print(f"[voix] synthèse impossible : {exc}")
                return None
        return path

    @staticmethod
    def _make_chime() -> pygame.mixer.Sound:
        """Soft two-note chime, generated (no sound file), with fade in and out."""
        freq, size, channels = pygame.mixer.get_init()
        n = int(freq * 0.7)
        buf = array.array("h")
        for i in range(n):
            t = i / freq
            note = 660 if t < 0.3 else 880
            env = min(1.0, t / 0.05) * max(0.0, 1 - t / 0.7)
            v = int(6000 * env * math.sin(2 * math.pi * note * t))
            buf.extend([v] * channels)
        return pygame.mixer.Sound(buffer=buf.tobytes())
