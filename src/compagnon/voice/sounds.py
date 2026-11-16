"""Generated sounds (no audio files, no licence issue).

Success sound, designed for autistic children (FC2):
* always the same, so it is predictable (FC1);
* three soft rising notes G4-C5-E5 (major chord, warm medium register, nothing shrill);
* marimba-like timbre: sine + a little octave, gentle 25 ms attack, natural decay;
* low level (peak ~30 % of full scale) and a final fade: never sudden, never loud.
"""

from __future__ import annotations

import array
import math
import wave
from pathlib import Path

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
