"""Extension point for FP7 (emotion from face/voice). OPTIONAL, disabled by default,
not implemented in S7.

A real source (camera/microphone) must analyse frames in memory only and never record
them (FC5). The controller only logs the estimates; nothing reacts to them yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmotionEstimate:
    label: str  # e.g. "calme", "agite"
    confidence: float  # 0..1


class EmotionSource(Protocol):
    enabled: bool

    def poll(self) -> EmotionEstimate | None: ...


class NullEmotionSource:
    enabled = False

    def poll(self) -> EmotionEstimate | None:
        return None
