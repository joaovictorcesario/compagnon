"""Clock abstraction: the core never calls time.* directly, so tests can simulate time."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float: ...


class RealClock:
    def now(self) -> float:
        return time.monotonic()


class FakeClock:
    """Simulated time for tests: `advance(15)` instead of waiting 15 real seconds."""

    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds
