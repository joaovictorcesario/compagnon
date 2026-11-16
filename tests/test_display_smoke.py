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
    d = PygameDisplay(Settings(), comp, rewards_dir=data_paths.rewards, size=(1280, 720))
    yield d
    pygame.quit()


def _near(color, expected, tol=3):
    return all(abs(a - b) <= tol for a, b in zip(color[:3], expected, strict=True))


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
    # positions come from the layout itself (it changed with the new design)
    for kind in (Kind.HELP, Kind.PAUSE, Kind.FINISHED, Kind.REPEAT):
        _click(disp.target_for(kind).center)
    _click((640, 100))  # empty area under the title -> background
    kinds = [e.kind for e in disp.poll_events()]
    assert kinds == [Kind.HELP, Kind.PAUSE, Kind.FINISHED, Kind.REPEAT, Kind.BACKGROUND]
    # a balloon
    _click(disp.target_for(Kind.CHOICE, item.choices[0].id).center)
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


def test_custom_character_from_images(tmp_path, disp):
    """Future custom character: one PNG per expression; missing ones fall back to neutre."""
    from compagnon.display.character import GeometricCharacter, SpriteCharacter, load_character

    folder = tmp_path / "personnage"
    folder.mkdir()
    for name, color in (("neutre", (200, 120, 60)), ("content", (60, 160, 90))):
        img = pygame.Surface((300, 300), pygame.SRCALPHA)
        pygame.draw.circle(img, color, (150, 150), 140)
        pygame.image.save(img, str(folder / f"{name}.png"))
    char = load_character(folder)
    assert isinstance(char, SpriteCharacter)
    disp.character = char
    disp.announce_activity("Les couleurs", "On va jouer avec les couleurs.")
    disp.render()
    disp.skip_transition()
    disp.render()
    assert _near(disp.screen.get_at(disp.view.p(300, 236)), (60, 160, 90))  # "content" sprite
    disp.show_pause("C'est la pause.")  # "calme": missing image -> neutre
    disp.render()
    disp.skip_transition()
    disp.render()
    assert _near(disp.screen.get_at(disp.view.p(640, 230)), (200, 120, 60))
    assert isinstance(load_character(tmp_path / "absent"), GeometricCharacter)


def test_repeat_emphasizes_the_bubble(disp):
    import random

    act = ColorActivity()
    item = act.make_item(1, random.Random(1))
    disp.show_scene(Scene(act.title, item.instruction, item.image, tuple(item.choices)))
    disp.render()
    disp.skip_transition()
    disp.render()
    inside_bubble = disp.view.p(320, 140)
    normal = disp.screen.get_at(inside_bubble)[:3]
    disp.emphasize_instruction()
    disp.render()
    assert disp.screen.get_at(inside_bubble)[:3] != normal


# ------------------------------------------------------------------ app screens
def _show(disp):
    disp.render()
    disp.skip_transition()
    disp.render()


def test_menu_cards_start_and_describe_games(disp):
    from compagnon.activities import CATALOG

    disp.show_menu(CATALOG.entries())
    _show(disp)
    pygame.event.clear()
    _click(disp.target_for(Kind.DESCRIBE, "couleurs").center)
    _click(disp.target_for(Kind.START, "couleurs").center)
    evs = disp.poll_events()
    assert [(e.kind, e.value) for e in evs] == [(Kind.DESCRIBE, "couleurs"),
                                               (Kind.START, "couleurs")]
    assert disp.current.id == "couleurs"


def test_home_button_asks_before_leaving(disp):
    import random

    act = ColorActivity()
    item = act.make_item(1, random.Random(1))
    disp.show_scene(Scene(act.title, item.instruction, item.image, tuple(item.choices)))
    _show(disp)
    pygame.event.clear()
    _click(disp.view.p(54, 43))  # "Maison" (top left)
    assert disp.poll_events() == [] and disp.confirm_home
    _show(disp)
    assert disp.target_for(Kind.HELP) is None  # only the two choices are active
    _click(disp.target_for(Kind.MENU).center)
    assert [e.kind for e in disp.poll_events()] == [Kind.MENU]
    assert not disp.confirm_home


def test_schedule_follows_the_reward_setting(disp):
    disp.apply_settings(Settings())
    assert [s[0] for s in disp._steps()] == ["D'abord", "Ensuite", "Fin"]
    disp.apply_settings(Settings(reward="aucune"))
    assert [s[0] for s in disp._steps()] == ["D'abord", "Fin"]


def test_progress_and_stars_follow_the_game(disp):
    import random

    act = ColorActivity()
    disp.announce_activity(act.title, act.announce_text)
    for seed in range(3):
        item = act.make_item(1, random.Random(seed))
        disp.show_scene(Scene(act.title, item.instruction, item.image, tuple(item.choices)))
        disp.set_expression("encourage")  # wrong answer: no progress
        disp.show_reward(RewardView("etoile"))
        disp.set_expression("content")  # right answer
    assert disp.rounds_done == 3 and disp.stars == 3
    disp.show_end(act.end_text)
    _show(disp)


@pytest.mark.parametrize("size", [(1280, 720), (1920, 1080), (1024, 768)])
def test_window_scales_proportionally(disp, size):
    from compagnon.activities import CATALOG

    disp.resize(size)
    disp.show_menu(CATALOG.entries())
    _show(disp)
    card = disp.target_for(Kind.START, "couleurs")
    k = min(size[0] / 1280, size[1] / 720)
    assert abs(card.width - 520 * k) <= 2
    assert disp.screen.get_rect().contains(card)
