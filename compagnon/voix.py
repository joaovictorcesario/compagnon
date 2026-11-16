"""La voix (Piper) et le son de bonne réponse.

Sommaire (chercher « PARTIE n ») :
  1. Ce qu'est une voix
  2. Les voix disponibles
  3. Son de bonne réponse
  4. Voix Piper et lecture du son
"""

from __future__ import annotations

import array
import hashlib
import io
import math
import os
import threading
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pygame

from compagnon.reglages import DOSSIER_PROJET, Settings

# ================================================================================================
# PARTIE 1 — CE QU'EST UNE VOIX
# Voice/sound output interface (part of the swappable output layer, FC7).
# ================================================================================================

class Voice(Protocol):
    def say(self, text: str) -> None: ...

    def stop(self) -> None: ...

    def set_muted(self, muted: bool) -> None: ...

    def configure(self, settings: Settings) -> None: ...

    def chime(self) -> None: ...


class RecordingVoice:
    """For tests and for --sans-voix: remembers what would have been said."""

    def __init__(self) -> None:
        self.said: list[str] = []
        self.suppressed: list[str] = []  # said while muted
        self.muted = False
        self.stops = 0
        self.chimes = 0
        self.settings: Settings | None = None

    def say(self, text: str) -> None:
        (self.suppressed if self.muted else self.said).append(text)

    def stop(self) -> None:
        self.stops += 1

    def set_muted(self, muted: bool) -> None:
        self.muted = muted

    def configure(self, settings: Settings) -> None:
        self.settings = settings

    def chime(self) -> None:
        if not self.muted:
            self.chimes += 1


# ================================================================================================
# PARTIE 2 — LES VOIX DISPONIBLES
# Voice presets. Piper has no child voice in French: raising the pitch (speed unchanged)
# gives a softer, younger-sounding voice. Choose with `--voix <preset>`.
# ================================================================================================

@dataclass(frozen=True)
class VoicePreset:
    model: str  # Piper model file name (without .onnx)
    speaker: str | None = None  # for multi-speaker models
    semitones: float = 0.0  # > 0 = higher voice


VOICE_PRESETS: dict[str, VoicePreset] = {
    "siwis": VoicePreset("fr_FR-siwis-medium"),
    "siwis-douce": VoicePreset("fr_FR-siwis-medium", semitones=3),
    "siwis-enfant": VoicePreset("fr_FR-siwis-medium", semitones=5),
    "jessica": VoicePreset("fr_FR-upmc-medium", "jessica"),
    "jessica-douce": VoicePreset("fr_FR-upmc-medium", "jessica", semitones=3),
    "jessica-enfant": VoicePreset("fr_FR-upmc-medium", "jessica", semitones=5),
}
DEFAULT_VOICE = "jessica"  # calm and natural (chosen by the team)


def resolve_voice(name: str) -> VoicePreset:
    """A preset name ("siwis-douce") or a raw Piper model ("fr_FR-siwis-medium")."""
    return VOICE_PRESETS.get(name) or VoicePreset(name)


# ================================================================================================
# PARTIE 3 — SON DE BONNE RÉPONSE
# Generated sounds (no audio files, no licence issue).
#
# Success sound, designed for autistic children (FC2):
# * always the same, so it is predictable (FC1);
# * three soft rising notes G4-C5-E5 (major chord, warm medium register, nothing shrill);
# * marimba-like timbre: sine + a little octave, gentle 25 ms attack, natural decay;
# * low level (peak ~30 % of full scale) and a final fade: never sudden, never loud.
# ================================================================================================

NOTES_HZ = (392.00, 523.25, 659.25)  # G4, C5, E5
NOTE_GAP_S = 0.16
DECAY_S = 0.32
LENGTH_S = 1.2
PEAK = 0.30
ATTACK_S = 0.025


def success_samples(rate: int = 22050) -> list[float]:
    n = int(rate * LENGTH_S)
    out = [0.0] * n
    for k, f in enumerate(NOTES_HZ):
        start = int(k * NOTE_GAP_S * rate)
        gain = 0.85 + 0.075 * k  # last note slightly fuller
        for i in range(start, n):
            t = (i - start) / rate
            env = min(1.0, t / ATTACK_S) * math.exp(-t / DECAY_S)
            out[i] += gain * env * (math.sin(2 * math.pi * f * t)
                                    + 0.18 * math.sin(4 * math.pi * f * t))
    fade = int(0.25 * rate)
    for i in range(n - fade, n):
        out[i] *= (n - i) / fade
    peak = max(abs(v) for v in out) or 1.0
    return [v * PEAK / peak for v in out]


def success_pcm(rate: int = 22050, channels: int = 1) -> bytes:
    buf = array.array("h")
    for v in success_samples(rate):
        buf.extend([int(v * 32767)] * channels)
    return buf.tobytes()


def write_success_wav(path: Path, rate: int = 22050) -> Path:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(success_pcm(rate))
    return path


# ================================================================================================
# PARTIE 4 — VOIX PIPER ET LECTURE DU SON
# Offline French voice: Piper (preferred) -> WAV cache -> pygame.mixer.
#
# * each sentence is synthesised once and cached, so the voice is always identical (FC1);
# * soft fade-in, never a sudden sound (FC2);
# * nothing is recorded, nothing leaves the computer (FC5).
# ================================================================================================

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


PROJECT_VOICES = DOSSIER_PROJET / "voix"  # <projet>/voix (livrées avec le projet)


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
