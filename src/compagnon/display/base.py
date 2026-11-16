"""Display interface (FC7). The core talks ONLY to this. For the robot (S8), write a new
class implementing it (face on a small screen + head motor); nothing else changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from compagnon.activities.base import Choice, ImageSpec
from compagnon.core.events import InputEvent
from compagnon.core.settings import Settings

EXPRESSIONS = ("neutre", "content", "encourage", "calme")


@dataclass(frozen=True)
class Scene:
    title: str  # current activity, always at the same place (FC1)
    text: str  # instruction text, shown together with voice and image (FC4)
    image: ImageSpec
    choices: tuple[Choice, ...]
    highlight: str | None = None  # visual hint, no blinking (FC2)
    expression: str = "neutre"


@dataclass(frozen=True)
class RewardView:
    kind: str  # "etoile" | "son" | "image"
    image_path: str = ""


class Display(Protocol):
    def announce_activity(self, title: str, text: str) -> None: ...

    def show_scene(self, scene: Scene) -> None: ...

    def set_expression(self, expression: str) -> None: ...

    def emphasize_instruction(self) -> None: ...  # instruction repeated: make it visible

    def show_reward(self, reward: RewardView) -> None: ...

    def propose_pause(self, text: str) -> None: ...

    def show_pause(self, text: str) -> None: ...

    def set_calm(self, calm: bool) -> None: ...

    def show_end(self, text: str) -> None: ...

    def apply_settings(self, settings: Settings) -> None: ...

    def poll_events(self) -> list[InputEvent]: ...
