"""Voice/sound output interface (part of the swappable output layer, FC7)."""

from __future__ import annotations

from typing import Protocol

from compagnon.core.settings import Settings


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
