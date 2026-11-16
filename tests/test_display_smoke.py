"""The pygame display draws every screen without crashing (headless) and maps clicks
to the right events."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from compagnon.activities import ColorActivity  # noqa: E402
from compagnon.child import ChildProfile, ProfileStore  # noqa: E402
from compagnon.companion import CompanionMode, PinStore  # noqa: E402
from compagnon.core.clock import FakeClock  # noqa: E402
from compagnon.core.events import Kind  # noqa: E402
from compagnon.core.settings import Settings, SettingsStore  # noqa: E402
from compagnon.display.base import RewardView, Scene  # noqa: E402


@pytest.fixture
def disp(data_paths):
    from compagnon.display.pygame_display import PygameDisplay

    comp = CompanionMode(paths=data_paths, settings_store=SettingsStore(data_paths.settings),
                         pin_store=PinStore(data_paths.pin),
                         profile_store=ProfileStore(data_paths.profiles),
                         profile=ChildProfile("x"), clock=FakeClock())
    d = PygameDisplay(Settings(), comp, rewards_dir=data_paths.rewards)
    yield d
    pygame.quit()


def _click(pos):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_all_child_screens_render(disp):
    import random

    act = ColorActivity()
    item = act.make_item(4, random.Random(1))
    disp.announce_activity(act.title, act.announce_text)
    disp.render()
    for size in ("petit", "moyen", "grand"):
        disp.apply_settings(Settings(text_size=size, palette="menthe"))
        disp.show_scene(Scene(act.title, item.instruction, item.image, tuple(item.choices),
                              highlight=item.key, expression="encourage"))
        disp.render()
    disp.show_reward(RewardView("etoile"))
    disp.render()
    disp.set_calm(True)
    disp.propose_pause("Tu veux faire une pause ?")
    disp.render()
    disp.show_pause("C'est la pause.")
    disp.render()
    disp.show_end("D'accord, on s'arrête, merci et à bientôt !")
    disp.render()


def test_clicks_map_to_events(disp):
    import random

    act = ColorActivity()
    item = act.make_item(1, random.Random(1))
    disp.show_scene(Scene(act.title, item.instruction, item.image, tuple(item.choices)))
    disp.render()
    pygame.event.clear()
    _click((40 + 142, 720 - 62))  # "Aide"
    _click((40 + 330 + 142, 720 - 62))  # "Pause"
    _click((40 + 660 + 142, 720 - 62))  # "J'ai fini"
    _click((818, 175))  # drawn speaker icon
    _click((500, 30))  # header -> background
    kinds = [e.kind for e in disp.poll_events()]
    assert kinds == [Kind.HELP, Kind.PAUSE, Kind.FINISHED, Kind.REPEAT, Kind.BACKGROUND]
    # a balloon
    spacing = (1024 - 120) / 2
    _click((int(60 + spacing * 0.5), 405))
    ev = disp.poll_events()[0]
    assert ev.kind == Kind.CHOICE and ev.value == item.choices[0].id


def test_companion_screens_render(disp):
    disp.companion_ui.open()
    disp.render()
    assert disp.companion.unlock("1234") == "ok"
    disp.companion_ui.state = "menu"
    for tab in ("reglages", "questions", "donnees"):
        disp.companion_ui.tab = tab
        disp.render()
