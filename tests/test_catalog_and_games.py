"""Game catalogue (home-screen cards) and the adult's choice of games (FP4, FC1)."""

from __future__ import annotations

import pytest

from compagnon.adulte import CompanionMode, PinStore
from compagnon.enfant import ChildProfile, ProfileStore
from compagnon.jeux import (
    CATALOG,
    MAX_VISIBLE,
    Catalog,
    CatalogEntry,
    ColorActivity,
    build_activities,
)
from compagnon.reglages import FakeClock, SettingsStore


def entry(gid: str, title: str = "") -> CatalogEntry:
    return CatalogEntry(gid, title or f"Les {gid}", f"Joue avec les {gid}.", gid, "accent2",
                        ColorActivity)


def five() -> Catalog:
    return Catalog([entry(g) for g in ("couleurs", "formes", "animaux", "emotions", "sons")])


@pytest.fixture
def mode_factory(data_paths):
    def make(catalog: Catalog) -> CompanionMode:
        m = CompanionMode(paths=data_paths, settings_store=SettingsStore(data_paths.settings),
                          pin_store=PinStore(data_paths.pin),
                          profile_store=ProfileStore(data_paths.profiles),
                          profile=ChildProfile("x"), clock=FakeClock(), catalog=catalog)
        assert m.unlock("1234") == "ok"
        return m
    return make


# ------------------------------------------------------------------ catalogue
def test_the_app_registers_the_colours_game():
    assert [e.id for e in CATALOG.entries()] == ["couleurs"]
    assert isinstance(build_activities(["couleurs"])[0], ColorActivity)


def test_a_registered_game_appears_as_a_card_by_itself():
    cat = Catalog([entry("couleurs")])
    assert [e.id for e in cat.visible(["couleurs"], [])] == ["couleurs"]
    cat.register(entry("formes"))
    # no setting changed: the new card shows up, AFTER the existing one (FC1)
    assert [e.id for e in cat.visible(["couleurs"], [])] == ["couleurs", "formes"]


def test_same_id_cannot_be_registered_twice():
    cat = Catalog([entry("couleurs")])
    with pytest.raises(ValueError):
        cat.register(entry("couleurs"))


def test_at_most_max_visible_cards_and_never_empty():
    cat = five()
    assert len(cat.visible([], [])) == MAX_VISIBLE
    everything_hidden = [e.id for e in cat.entries()]
    assert [e.id for e in cat.visible([], everything_hidden)] == ["couleurs"]
    assert cat.visible(["inconnu"], []) and all(e.id in cat for e in cat.visible(["x"], []))


def test_spoken_description_and_icon_fallback_are_defined():
    e = CATALOG.get("couleurs")
    assert e.description and e.icon == "ballons" and e.color in ("accent1", "accent2", "accent3")


# ------------------------------------------------------------------ adult choice
def test_adult_hides_and_shows_games(mode_factory):
    m = mode_factory(five())
    assert [e.id for e in m.visible_games()] == ["couleurs", "formes", "animaux", "emotions"]
    assert m.toggle_game("formes") is None
    assert [e.id for e in m.visible_games()] == ["couleurs", "animaux", "emotions"]
    assert m.toggle_game("sons") is None  # shown again: added at the end
    assert [e.id for e in m.visible_games()] == ["couleurs", "animaux", "emotions", "sons"]
    states = {e.id: shown for e, shown in m.games()}
    assert states == {"couleurs": True, "animaux": True, "emotions": True, "sons": True,
                      "formes": False}


def test_adult_cannot_show_too_many_or_hide_the_last(mode_factory):
    m = mode_factory(five())
    assert "maximum" in (m.toggle_game("sons") or "")  # already 4 visible
    m2 = mode_factory(Catalog([entry("couleurs")]))
    assert m2.toggle_game("couleurs") and [e.id for e in m2.visible_games()] == ["couleurs"]


def test_adult_reorders_and_order_is_kept_between_sessions(mode_factory, data_paths):
    m = mode_factory(five())
    m.move_game("animaux", -1)
    m.move_game("animaux", -1)
    m.move_game("couleurs", +5)  # clamped to the last place
    order = ["animaux", "formes", "emotions", "couleurs"]
    assert [e.id for e in m.visible_games()] == order
    # next session: same cards, same places (FC1)
    again = mode_factory(five())
    assert [e.id for e in again.visible_games()] == order


def test_games_need_the_adult_code(mode_factory):
    m = mode_factory(five())
    m.lock()
    with pytest.raises(PermissionError):
        m.toggle_game("formes")
    with pytest.raises(PermissionError):
        m.move_game("formes", 1)


def test_factory_reset_restores_default_games(mode_factory):
    m = mode_factory(five())
    m.toggle_game("formes")
    m.factory_reset()
    assert [e.id for e in m.visible_games()] == ["couleurs", "formes", "animaux", "emotions"]
