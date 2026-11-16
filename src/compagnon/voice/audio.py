"""Offline French voice: Piper (preferred) -> WAV cache -> pygame.mixer.

* each sentence is synthesised once and cached, so the voice is always identical (FC1);
* soft fade-in, never a sudden sound (FC2);
* nothing is recorded, nothing leaves the computer (FC5).
"""

from __future__ import annotations

import hashlib
import io
import os
import threading
import wave
from collections.abc import Callable
from pathlib import Path

import pygame

from compagnon.core.settings import Settings
from compagnon.voice.presets import DEFAULT_VOICE, resolve_voice
from compagnon.voice.sounds import success_pcm

SAMPLE_RATE = 22050
FADE_MS = 120


class PiperEngine:
    def __init__(self, model_path: Path, speaker: str | None = None,
                 semitones: float = 0.0) -> None:
        from piper import PiperVoice

        self.voice = PiperVoice.load(str(model_path))
        self.speaker_id: int | None = None
        if speaker is not None:
            ids = self.voice.config.speaker_id_map or {}
            if speaker not in ids:
                raise ValueError(f"locuteur « {speaker} » absent ({', '.join(ids)})")
            self.speaker_id = ids[speaker]
        self.pitch = 2 ** (semitones / 12)
        self.name = f"piper:{model_path.stem}:{speaker or '-'}:{semitones:+g}"
        self._warmup()

    def _warmup(self) -> None:
        """The very first synthesis takes several seconds (engine start-up). Do it now,
        before the session starts, so no reaction during the session exceeds 2 s."""
        self._render("Bonjour.", slow=False)

    def _render(self, text: str, slow: bool) -> tuple[wave._wave_params, bytes]:
        from piper import SynthesisConfig

        # Speak slower by the pitch factor, then play the samples faster by the same
        # factor: higher voice, same speed.
        cfg = SynthesisConfig(speaker_id=self.speaker_id,
                              length_scale=(1.3 if slow else 1.0) * self.pitch)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            self.voice.synthesize_wav(text, wf, syn_config=cfg)
        buf.seek(0)
        with wave.open(buf, "rb") as rf:
            return rf.getparams(), rf.readframes(rf.getnframes())

    def synthesize(self, text: str, out: Path, slow: bool) -> None:
        params, frames = self._render(text, slow)
        with wave.open(str(out), "wb") as wf:
            wf.setnchannels(params.nchannels)
            wf.setsampwidth(params.sampwidth)
            wf.setframerate(round(params.framerate * self.pitch))
            wf.writeframes(frames)


PROJECT_VOICES = Path(__file__).resolve().parents[3] / "voix"  # <dépôt>/voix (hors git)


def voice_dirs(data_voices: Path) -> list[Path]:
    """Where to look for Piper models, in order: $COMPAGNON_VOIX, the data folder, then the
    project's own `voix/` folder and `./voix` (useful when AppData is redirected)."""
    dirs = [Path(p) for p in [os.environ.get("COMPAGNON_VOIX")] if p]
    dirs += [data_voices, PROJECT_VOICES, Path.cwd() / "voix"]
    return list(dict.fromkeys(dirs))


def load_engine(voices_dir: Path, voice_name: str = DEFAULT_VOICE) -> PiperEngine | None:
    preset = resolve_voice(voice_name)
    dirs = voice_dirs(voices_dir)
    model = next((d / f"{preset.model}.onnx" for d in dirs
                  if (d / f"{preset.model}.onnx").exists()), None)
    if model is None:
        print(f"[voix] modèle « {preset.model} » introuvable dans : "
              + " ; ".join(str(d) for d in dirs) + " -> texte seulement (voir README)")
        return None
    try:
        return PiperEngine(model, preset.speaker, preset.semitones)
    except Exception as exc:  # noqa: BLE001
        print(f"[voix] Piper indisponible : {exc}")
        return None


class PygameVoice:
    def __init__(self, cache_dir: Path, engine: PiperEngine | None,
                 engine_loader: Callable[[str], PiperEngine | None] | None = None,
                 voice_name: str | None = None) -> None:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.engine = engine
        self.engine_loader = engine_loader  # to change voice from the adult settings
        self.voice_name = voice_name
        self._engines: dict[str, PiperEngine | None] = {}
        if voice_name is not None:
            self._engines[voice_name] = engine
        self._preload_texts: list[str] = []
        self.volume = 0.7
        self.slow = False
        self.sounds = True
        self.muted = False
        self._lock = threading.Lock()
        freq, _size, channels = pygame.mixer.get_init()
        self._success = pygame.mixer.Sound(buffer=success_pcm(freq, channels))
        self._voice_channel: pygame.mixer.Channel | None = None

    # ------------------------------------------------------------ Voice interface
    def configure(self, settings: Settings) -> None:
        self.volume = max(0, min(100, settings.volume)) / 100
        self.slow = settings.voice_rate == "lente"
        self.sounds = settings.sounds
        if self.engine_loader is not None and settings.voice != self.voice_name:
            self._switch_voice(settings.voice)

    def _switch_voice(self, name: str) -> None:
        if name not in self._engines:
            self._engines[name] = self.engine_loader(name) if self.engine_loader else None
        if self._engines[name] is None:  # voice not installed: keep the current one
            print(f"[voix] « {name} » indisponible, voix actuelle conservée")
            return
        self.engine, self.voice_name = self._engines[name], name
        print(f"[voix] {self.engine.name}")
        if self._preload_texts:
            self.preload(self._preload_texts)

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

    def is_speaking(self) -> bool:
        """True while a sentence is playing (the character's mouth moves)."""
        ch = self._voice_channel
        return bool(ch is not None and ch.get_busy())

    def stop(self) -> None:
        pygame.mixer.fadeout(150)

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        if muted:
            self.stop()

    def chime(self) -> None:
        """Soft success sound (see sounds.py)."""
        if self.muted or not self.sounds or self.volume <= 0:
            return
        self._success.set_volume(self.volume)
        self._success.play(fade_ms=FADE_MS)

    # ------------------------------------------------------------ cache
    def preload(self, texts: list[str]) -> threading.Thread:
        """Synthesise the prepared phrases in the background at start-up."""
        self._preload_texts = list(texts)
        th = threading.Thread(target=lambda: [self._wav(t) for t in texts], daemon=True)
        th.start()
        return th

    def _wav(self, text: str) -> Path | None:
        engine = self.engine
        if engine is None:
            return None
        key = hashlib.sha1(f"{engine.name}|{self.slow}|{text}".encode()).hexdigest()[:16]
        path = self.cache_dir / f"{key}.wav"
        if path.exists():
            return path
        with self._lock:
            if path.exists():
                return path
            tmp = path.with_suffix(".tmp")
            try:
                engine.synthesize(text, tmp, self.slow)
                os.replace(tmp, path)
            except Exception as exc:  # noqa: BLE001
                print(f"[voix] synthèse impossible : {exc}")
                return None
        return path
