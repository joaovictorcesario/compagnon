"""Display used by the tests: records every command, draws nothing."""

from __future__ import annotations

from compagnon.core.events import InputEvent
from compagnon.core.settings import Settings
from compagnon.display.base import RewardView, Scene


class FakeDisplay:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.mode = "vide"
        self.scene: Scene | None = None
        self.calm = False
        self.texts: list[str] = []  # every text shown to the child
        self.queue: list[InputEvent] = []

    def _rec(self, name: str, arg: object = None) -> None:
        self.calls.append((name, arg))

    def named(self, name: str) -> list[object]:
        return [a for n, a in self.calls if n == name]

    def announce_activity(self, title: str, text: str) -> None:
        self.mode = "annonce"
        self.texts.append(text)
        self._rec("announce_activity", (title, text))

    def show_scene(self, scene: Scene) -> None:
        self.mode = "scene"
        self.scene = scene
        self.texts.append(scene.text)
        self._rec("show_scene", scene)

    def set_expression(self, expression: str) -> None:
        self._rec("set_expression", expression)

    def show_reward(self, reward: RewardView) -> None:
        self._rec("show_reward", reward)

    def propose_pause(self, text: str) -> None:
        self.mode = "pause_proposee"
        self.texts.append(text)
        self._rec("propose_pause", text)

    def show_pause(self, text: str) -> None:
        self.mode = "pause"
        self.texts.append(text)
        self._rec("show_pause", text)

    def set_calm(self, calm: bool) -> None:
        self.calm = calm
        self._rec("set_calm", calm)

    def show_end(self, text: str) -> None:
        self.mode = "fin"
        self.texts.append(text)
        self._rec("show_end", text)

    def apply_settings(self, settings: Settings) -> None:
        self._rec("apply_settings", settings)

    def poll_events(self) -> list[InputEvent]:
        out, self.queue = self.queue, []
        return out
