from __future__ import annotations

import random
from dataclasses import dataclass

import pytest

from compagnon.enfant import ChildProfile, ProfileStore
from compagnon.ia import AIService, SentenceFilter, StubRephraser
from compagnon.jeux import ColorActivity
from compagnon.reglages import DataPaths, FakeClock, InputEvent, Kind, Settings
from compagnon.seance import SessionController, SessionLogger
from compagnon.voix import RecordingVoice
from fake_display import FakeDisplay


@dataclass
class Harness:
    clock: FakeClock
    display: FakeDisplay
    voice: RecordingVoice
    log: SessionLogger
    ctrl: SessionController
    profile: ChildProfile
    store: ProfileStore

    # --- child actions -------------------------------------------------------
    def press(self, kind: Kind, value: str | None = None) -> None:
        self.ctrl.handle(InputEvent(kind, value))

    def answer_right(self) -> None:
        self.press(Kind.CHOICE, self.ctrl.item.key)

    def answer_wrong(self) -> None:
        wrong = next(c.id for c in self.ctrl.item.choices if c.id != self.ctrl.item.key)
        self.press(Kind.CHOICE, wrong)

    def wait(self, seconds: float, step: float = 0.5) -> None:
        """Simulated time: ticks every `step` seconds, no real waiting."""
        t = 0.0
        while t < seconds - 1e-9:
            dt = min(step, seconds - t)
            self.clock.advance(dt)
            self.ctrl.tick()
            t += dt

    def to_first_question(self) -> None:
        self.wait(3.0)
        assert self.ctrl.phase.value == "question"

    def next_question(self) -> None:
        self.wait(2.0)

    @property
    def spoken(self) -> list[str]:
        return self.voice.said


@pytest.fixture
def data_paths(tmp_path) -> DataPaths:
    return DataPaths(tmp_path / "donnees").ensure()


@pytest.fixture
def make_session(data_paths):
    """Factory: make_session(settings=..., profile=..., ai=...) -> started Harness."""

    def factory(settings: Settings | None = None, profile: ChildProfile | None = None,
                ai: AIService | None = None, seed: int = 7) -> Harness:
        clock = FakeClock()
        display, voice = FakeDisplay(), RecordingVoice()
        store = ProfileStore(data_paths.profiles)
        profile = profile or store.load("test")
        log = SessionLogger(None, clock)
        ai = ai or AIService(StubRephraser(), SentenceFilter.default())
        ctrl = SessionController(
            clock=clock, display=display, voice=voice, ai=ai, activities=[ColorActivity()],
            settings=settings or Settings(), profile=profile, logger=log, profile_store=store,
            rng=random.Random(seed),
        )
        ctrl.start()
        return Harness(clock, display, voice, log, ctrl, profile, store)

    return factory
