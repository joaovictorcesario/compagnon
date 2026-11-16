"""Help levels and difficulty (FP2).

Two independent axes:
* help level 0-5 for the current item (lightest to strongest);
* difficulty 1-4 (number of choices), changed after N successes without help
  or N errors in a row (N set by the adult).
"""

from __future__ import annotations

from enum import Enum, IntEnum


class HelpLevel(IntEnum):
    NONE = 0
    REPEAT = 1  # same instruction again
    REFORMULATE = 2  # simpler instruction (AI or prepared phrase)
    HINT = 3  # verbal hint (AI or prepared phrase)
    VISUAL = 4  # right answer gently highlighted (no blinking)
    MODEL = 5  # only 2 choices left, the character shows the answer


class Decision(Enum):
    NONE = "aucune"
    HARDER = "plus_difficile"
    HINT_THEN_EASIER = "indice_puis_plus_facile"


class Adaptation:
    def __init__(self, difficulty: int, max_difficulty: int, success_threshold: int,
                 error_threshold: int) -> None:
        self.max_difficulty = max_difficulty
        self.difficulty = max(1, min(max_difficulty, difficulty))
        self.success_threshold = success_threshold
        self.error_threshold = error_threshold
        self.success_streak = 0  # successes without help
        self.error_streak = 0
        self._pending = 0  # difficulty change applied at the next item

    def set_thresholds(self, success_threshold: int, error_threshold: int) -> None:
        self.success_threshold = success_threshold
        self.error_threshold = error_threshold

    def on_answer(self, correct: bool, used_help: bool) -> Decision:
        if correct:
            self.error_streak = 0
            if used_help:
                self.success_streak = 0
                return Decision.NONE
            self.success_streak += 1
            if self.success_streak >= self.success_threshold:
                self.success_streak = 0
                self._pending = +1
                return Decision.HARDER
            return Decision.NONE
        self.success_streak = 0
        self.error_streak += 1
        if self.error_streak >= self.error_threshold:
            self.error_streak = 0
            self._pending = -1
            return Decision.HINT_THEN_EASIER
        return Decision.NONE

    @property
    def next_difficulty(self) -> int:
        """Difficulty of the next item (pending change included), saved for next session."""
        return max(1, min(self.max_difficulty, self.difficulty + self._pending))

    def start_item(self) -> tuple[int, int] | None:
        """Apply a pending change. Returns (old, new) if the difficulty changed."""
        if not self._pending:
            return None
        old = self.difficulty
        self.difficulty = max(1, min(self.max_difficulty, self.difficulty + self._pending))
        self._pending = 0
        return (old, self.difficulty) if old != self.difficulty else None
