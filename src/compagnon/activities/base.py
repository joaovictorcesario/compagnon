"""Generic activity contract (FP1). New activities (shapes, emotions...) implement this."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Choice:
    id: str
    label: str
    rgb: tuple[int, int, int]


@dataclass(frozen=True, eq=False)
class ImageSpec:
    """What picture goes with the instruction (FC4). The display decides how to draw it."""

    kind: str
    data: dict = field(default_factory=dict)


@dataclass
class Item:
    key: str  # id of the correct answer
    choices: list[Choice]
    instruction: str
    image: ImageSpec


class Activity(Protocol):
    id: str
    title: str
    announce_text: str
    end_text: str
    max_difficulty: int

    def make_item(self, difficulty: int, rng: random.Random) -> Item: ...

    def is_correct(self, item: Item, choice_id: str) -> bool: ...

    def model_choices(self, item: Item) -> list[Choice]: ...

    def ai_context(self, item: Item) -> dict: ...

    def fixed_phrases(self) -> list[str]: ...
