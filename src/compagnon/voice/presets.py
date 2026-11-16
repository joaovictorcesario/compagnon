"""Voice presets. Piper has no child voice in French: raising the pitch (speed unchanged)
gives a softer, younger-sounding voice. Choose with `--voix <preset>`."""

from __future__ import annotations

from dataclasses import dataclass


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
