"""Overload detection thresholds (FP5) and how they move with the child's sensitivity (FP6).

Each "oui" from the adult to "Était-ce une crise ?" raises the sensitivity by one step
(only while learning is active). Higher sensitivity = the pause is offered earlier:
fewer fast clicks, fewer errors in a row, shorter scheduled-pause interval, with a floor.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from compagnon.core.settings import Settings

MAX_SENSITIVITY = 3
MIN_CLICKS = 3
MIN_ERRORS = 4  # stays above the default "3 errors -> hint" rule
MIN_PAUSE_INTERVAL_S = 90
PAUSE_STEP_S = 30


@dataclass(frozen=True)
class OverloadThresholds:
    clicks: int  # agitation = MORE than this many clicks ...
    window_s: float  # ... within this many seconds
    errors: int  # errors in a row -> offer a pause
    pause_interval_s: int  # scheduled pause offer, 0 = never


def thresholds_for(settings: Settings, sensitivity: int) -> OverloadThresholds:
    s = max(0, min(MAX_SENSITIVITY, sensitivity))
    interval = settings.pause_interval_s
    if interval:
        interval = max(MIN_PAUSE_INTERVAL_S, interval - PAUSE_STEP_S * s)
    return OverloadThresholds(
        clicks=max(MIN_CLICKS, settings.agitation_clicks - s),
        window_s=settings.agitation_window_s,
        errors=max(MIN_ERRORS, settings.overload_errors - s),
        pause_interval_s=interval,
    )


class ClickMonitor:
    """Sliding window of click times."""

    def __init__(self, max_clicks: int, window_s: float) -> None:
        self.max_clicks = max_clicks
        self.window_s = window_s
        self._times: deque[float] = deque()

    def register(self, t: float) -> bool:
        self._times.append(t)
        while self._times and t - self._times[0] > self.window_s:
            self._times.popleft()
        if len(self._times) > self.max_clicks:
            self._times.clear()
            return True
        return False

    def reset(self) -> None:
        self._times.clear()
