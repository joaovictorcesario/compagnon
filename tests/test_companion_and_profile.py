"""Adult mode (FP4) and learning across sessions (FP6)."""

from __future__ import annotations

import pytest

from compagnon.adulte import CompanionMode, PinStore
from compagnon.enfant import ChildProfile, ProfileStore, apply_answer, best_hint_level
from compagnon.reglages import FakeClock, Kind, SettingsStore


@pytest.fixture
def comp(data_paths):
    store = ProfileStore(data_paths.profiles)
    clock = FakeClock()
    mode = CompanionMode(paths=data_paths, settings_store=SettingsStore(data_paths.settings),
                         pin_store=PinStore(data_paths.pin), profile_store=store,
                         profile=store.load("test"), clock=clock)
    mode.test_clock = clock
    return mode


def test_pin_required_and_lock_after_3_wrong(comp):
    with pytest.raises(PermissionError):
        comp.adjust("volume", 1)
    assert comp.unlock("0000") == "faux"
    assert comp.unlock("1111") == "faux"
    assert comp.unlock("2222") == "bloque"
    assert comp.unlock("1234") == "bloque"  # even the right code, during 30 s
    comp.test_clock.advance(31)
    assert comp.unlock("1234") == "ok"


def test_change_pin_is_hashed(comp, data_paths):
    comp.unlock("1234")
    assert comp.change_pin("4321")
    assert "4321" not in data_paths.pin.read_text()
    comp.lock()
    assert comp.unlock("1234") == "faux"
    assert comp.unlock("4321") == "ok"
    assert not comp.change_pin("12a4")


def test_settings_are_saved(comp, data_paths):
    comp.unlock("1234")
    comp.adjust("volume", -1)
    comp.adjust("voice_rate", 1)
    comp.adjust("animations", 1)
    s = SettingsStore(data_paths.settings).load()
    assert (s.volume, s.voice_rate, s.animations) == (60, "lente", False)
    assert comp.value_label("pause_interval_s") == "3 min 00"


def test_next_session_resumes_level_and_helps(make_session):
    h = make_session()
    h.to_first_question()
    for _ in range(3):  # 3 successes -> level 2
        h.answer_right()
        h.next_question()
    for _ in range(3):  # 3 errors -> hint (calm pace: 1 s between clicks)
        h.answer_wrong()
        h.wait(1)
    h.answer_right()
    h.wait(1)
    h.press(Kind.FINISHED)
    assert h.ctrl.end_reason == "enfant"
    saved = h.store.load("test")
    assert saved.level == 1  # level 2 then easier after the 3 errors
    assert saved.sessions == 1
    assert saved.help_stats["3"]["used"] == 1 and saved.help_stats["3"]["solved"] == 1
    assert [q["type"] for q in saved.pending_questions] == ["aide"]
    h2 = make_session(profile=saved)
    assert h2.ctrl.difficulty == 1


def test_help_that_worked_is_reused(make_session):
    p = ChildProfile("test", help_stats={
        "3": {"used": 4, "solved": 0, "adult_yes": 0, "adult_no": 1},
        "4": {"used": 4, "solved": 4, "adult_yes": 1, "adult_no": 0},
    })
    assert best_hint_level(p) == 4
    h = make_session(profile=p)
    h.to_first_question()
    for _ in range(3):
        h.answer_wrong()
    assert h.ctrl.help_level == 4  # visual hint, the one that worked


def test_learning_pause_freezes_everything(make_session):
    p = ChildProfile("test", level=3, sensitivity=2, learning_paused=True)
    h = make_session(profile=p)
    assert h.ctrl.difficulty == 1  # initial level from settings, not the learned one
    assert h.ctrl.th.clicks == 5  # learned sensitivity not used
    h.to_first_question()
    for _ in range(6):
        h.press(Kind.BACKGROUND)
    h.ctrl.end("enfant")
    assert p.sessions == 0 and not p.pending_questions
    p.pending_questions.append({"id": "q1", "type": "crise"})
    assert not apply_answer(p, "q1", True)
    assert p.sensitivity == 2


def test_sensitivity_has_a_floor():
    from compagnon.enfant import thresholds_for
    from compagnon.reglages import Settings

    t = thresholds_for(Settings(), 99)
    assert t.clicks == 3 and t.errors == 4 and t.pause_interval_s == 90


def test_factory_reset_erases_learning_keeps_logs(comp, data_paths, make_session):
    p = comp.profile
    p.level, p.sensitivity, p.sessions = 3, 2, 5
    comp.profile_store.save(p)
    (data_paths.logs / "x.jsonl").write_text("{}\n")
    comp.unlock("1234")
    comp.adjust("volume", 1)
    comp.factory_reset()
    assert (p.level, p.sensitivity, p.sessions) == (None, 0, 0)
    assert not list(data_paths.profiles.glob("*.json"))
    assert comp.settings.volume == 70
    assert (data_paths.logs / "x.jsonl").exists()  # logs kept
    assert comp.delete_logs() == 1
    assert not (data_paths.logs / "x.jsonl").exists()


def test_crisis_answer_only_used_by_adult_mode(comp):
    p = comp.profile
    p.pending_questions.append({"id": "q1", "type": "crise", "texte": "Était-ce une crise ?"})
    with pytest.raises(PermissionError):
        comp.answer("q1", True)
    comp.unlock("1234")
    assert comp.answer("q1", True)
    assert p.sensitivity == 1 and not p.pending_questions


def test_adult_mode_freezes_the_session(make_session):
    h = make_session()
    h.to_first_question()
    item = h.ctrl.item
    h.press(Kind.ADULT_OPEN)
    h.wait(120)
    assert h.ctrl.phase.value == "adulte"
    h.press(Kind.HELP)  # child clicks are ignored while the adult is in settings
    assert h.ctrl.help_level == 0
    h.press(Kind.ADULT_CLOSE)
    assert h.ctrl.phase.value == "question" and h.ctrl.item is item
