"""The 8 scenarios of the specification, with simulated time.

Each test = one line of the table "comportement joué / ce que le compagnon perçoit /
réaction attendue". The same scenarios are the script of the demonstration.
"""

from __future__ import annotations

import time

from compagnon.ai.filter import FORBIDDEN
from compagnon.core import phrases
from compagnon.core.controller import Phase
from compagnon.core.events import Kind
from compagnon.core.settings import Settings


def test_s1_no_answer_15s_repeats_simpler(make_session):
    """L'enfant ne répond pas / rien pendant 15 s / répète la consigne plus simple."""
    h = make_session()
    h.to_first_question()
    first = h.ctrl.instruction
    h.wait(14.5)
    assert h.ctrl.help_level == 0, "nothing must happen before 15 s"
    h.wait(0.5)
    assert h.ctrl.help_level == 2  # level 2 = simpler instruction
    simpler = h.spoken[-1]
    assert simpler != first
    assert h.ctrl.item.key in simpler.lower()  # still names the target colour
    assert len(simpler.split()) <= len(first.split())
    assert h.log.events("silence")


def test_s2_three_errors_hint_then_easier(make_session):
    """Activité trop difficile / 3 erreurs de suite / donne un indice, puis facilite."""
    h = make_session(settings=Settings(initial_level=3))
    h.to_first_question()
    assert len(h.ctrl.item.choices) == 4
    h.answer_wrong()
    h.answer_wrong()
    assert h.spoken[-1] == phrases.WRONG
    h.answer_wrong()
    assert h.ctrl.help_level == 3  # hint
    hint = h.log.events("ia")[-1]
    assert hint["type"] == "indice"
    assert h.spoken[-1] == hint["texte"]
    h.answer_right()
    h.next_question()
    assert h.ctrl.difficulty == 2
    assert len(h.ctrl.item.choices) == 3  # easier: fewer choices


def test_s3_three_successes_without_help_harder(make_session):
    """L'enfant progresse / 3 réussites sans aide / rend un peu plus difficile."""
    h = make_session()
    h.to_first_question()
    assert len(h.ctrl.item.choices) == 2
    for _ in range(3):
        h.answer_right()
        h.next_question()
    assert h.ctrl.difficulty == 2
    assert len(h.ctrl.item.choices) == 3


def test_s3b_success_with_help_does_not_count(make_session):
    h = make_session()
    h.to_first_question()
    for _ in range(3):
        h.press(Kind.HELP)
        h.answer_right()
        h.next_question()
    assert h.ctrl.difficulty == 1


def test_s4_repeat_says_exactly_the_same(make_session):
    """Demande de répéter / même consigne demandée / répète exactement pareil."""
    h = make_session()
    h.to_first_question()
    before = h.spoken[-1]
    h.press(Kind.REPEAT)
    assert h.spoken[-1] == before
    assert h.ctrl.help_level == 0  # repeating is not a help level
    # also after a reformulation: repeats the last instruction word for word
    h.press(Kind.HELP)
    h.press(Kind.HELP)
    said = h.spoken[-1]
    h.press(Kind.REPEAT)
    assert h.spoken[-1] == said


def test_s5_agitation_more_than_5_clicks_in_3s(make_session):
    """Agitation / > 5 clics en 3 s / propose une pause, coupe les sons, calme l'écran."""
    h = make_session()
    h.to_first_question()
    for _ in range(5):
        h.press(Kind.BACKGROUND)
        h.clock.advance(0.4)
    assert h.ctrl.phase == Phase.ASK, "5 clicks is not yet agitation"
    t0 = time.perf_counter()
    h.press(Kind.BACKGROUND)
    elapsed = time.perf_counter() - t0
    assert h.ctrl.phase == Phase.PAUSE_OFFER
    assert h.voice.muted and h.voice.stops > 0
    assert h.display.calm
    assert h.display.mode == "pause_proposee"
    assert elapsed < 2.0
    # slow clicks are never agitation
    h2 = make_session()
    h2.to_first_question()
    for _ in range(10):
        h2.press(Kind.BACKGROUND)
        h2.clock.advance(1.0)
    assert h2.ctrl.phase == Phase.ASK


def test_s6_pause_button_stops_and_resumes_same_point(make_session):
    """Demande une pause / bouton Pause / tout s'arrête, écran calme, reprend au même point."""
    h = make_session()
    h.to_first_question()
    h.press(Kind.HELP)  # help level 1
    item, choices, level = h.ctrl.item, list(h.ctrl.item.choices), h.ctrl.help_level
    instruction = h.ctrl.instruction
    h.press(Kind.PAUSE)
    assert h.ctrl.phase == Phase.PAUSED and h.display.mode == "pause" and h.display.calm
    n_said = len(h.spoken)
    h.wait(120)  # long pause: no repeat, no end
    assert h.ctrl.phase == Phase.PAUSED
    assert len(h.spoken) == n_said
    h.press(Kind.CONTINUE)
    assert h.ctrl.phase == Phase.ASK and not h.display.calm
    assert h.ctrl.item is item and list(h.ctrl.item.choices) == choices
    assert h.ctrl.help_level == level
    assert h.spoken[-1] == instruction
    assert h.display.scene.choices == tuple(choices)


def test_s7_finished_button_ends_calmly(make_session):
    """Ne veut pas continuer / « J'ai fini » / termine calmement, sans message d'échec."""
    h = make_session()
    h.to_first_question()
    h.press(Kind.FINISHED)
    assert h.ctrl.phase == Phase.ENDED and h.display.mode == "fin"
    assert h.spoken[-1] == phrases.END_CHILD


def test_s7b_60s_without_anything_ends_calmly(make_session):
    h = make_session()
    h.to_first_question()
    h.wait(56.5)
    assert h.ctrl.phase == Phase.ASK
    h.wait(1.0)  # 60 s since the session started (3 s announce + 57 s)
    assert h.ctrl.phase == Phase.ENDED
    assert h.ctrl.end_reason == "silence"
    assert h.spoken[-1] == phrases.END_SILENCE


def test_s8_adult_says_crisis_pause_offered_earlier_next_session(make_session):
    """L'adulte répond « oui » à « Était-ce une crise ? » / la séance suivante propose
    la pause plus tôt."""
    h = make_session()
    h.to_first_question()
    for _ in range(6):
        h.press(Kind.BACKGROUND)
    h.press(Kind.FINISHED)  # child does not want to go on
    h.press(Kind.CONTINUE)
    h.ctrl.end("enfant")
    q = [q for q in h.profile.pending_questions if q["type"] == "crise"]
    assert q, "a question must be waiting for the adult"
    # the adult answers in companion mode
    from compagnon.child import apply_answer

    assert apply_answer(h.profile, q[0]["id"], yes=True)
    h.store.save(h.profile)

    h2 = make_session(profile=h.store.load("test"))
    assert h2.ctrl.th.clicks == 4  # was 5
    assert h2.ctrl.th.pause_interval_s == 150  # was 180
    h2.to_first_question()
    for _ in range(5):  # 5 clicks: agitation now (it needed 6 before)
        h2.press(Kind.BACKGROUND)
    assert h2.ctrl.phase == Phase.PAUSE_OFFER


def test_scheduled_pause_offer(make_session):
    h = make_session(settings=Settings(pause_interval_s=90, silence_end_s=600,
                                       silence_repeat_s=600))
    h.to_first_question()
    h.wait(86.5)  # 89.5 s since the start of the session
    assert h.ctrl.phase == Phase.ASK
    h.wait(1)
    assert h.ctrl.phase == Phase.PAUSE_OFFER


def test_automatic_pause_mode(make_session):
    h = make_session(settings=Settings(pause_mode="automatique"))
    h.to_first_question()
    for _ in range(6):
        h.press(Kind.BACKGROUND)
    assert h.ctrl.phase == Phase.PAUSED


def test_five_errors_in_a_row_offer_pause(make_session):
    h = make_session()
    h.to_first_question()
    for _ in range(5):
        h.answer_wrong()
        h.clock.advance(1.0)
    assert h.ctrl.phase == Phase.PAUSE_OFFER
    assert "erreurs" in h.ctrl.difficult_moments


def test_activity_change_is_announced_and_activity_ends(make_session):
    h = make_session(settings=Settings(items_per_activity=2))
    assert h.display.named("announce_activity")
    h.to_first_question()
    h.answer_right()
    h.next_question()
    h.answer_right()
    h.next_question()
    assert h.ctrl.phase == Phase.ENDED and h.ctrl.end_reason == "termine"


def test_every_instruction_has_voice_text_and_image(make_session):
    h = make_session()
    h.to_first_question()
    h.wait(15)
    h.press(Kind.HELP)
    for scene in h.display.named("show_scene"):
        assert scene.text and scene.image is not None and scene.choices
        assert scene.text in h.spoken


def test_reward_shown_on_success(make_session):
    h = make_session(settings=Settings(reward="son"))
    h.to_first_question()
    h.answer_right()
    assert h.display.named("show_reward")[-1].kind == "son"
    assert h.voice.chimes == 1
    h2 = make_session(settings=Settings(reward="son", sounds=False))
    h2.to_first_question()
    h2.answer_right()
    assert h2.voice.chimes == 0


def test_never_a_failure_message(make_session):
    """FP5/FC6: across every scenario, nothing said or shown contains a forbidden word."""
    h = make_session(settings=Settings(initial_level=4))
    h.to_first_question()
    for _ in range(4):
        h.answer_wrong()
    h.press(Kind.CONTINUE)
    for _ in range(5):
        h.press(Kind.HELP)
    h.wait(20)
    for _ in range(6):
        h.press(Kind.BACKGROUND)
    h.press(Kind.CONTINUE)
    h.press(Kind.FINISHED)
    texts = h.spoken + h.voice.suppressed + h.display.texts
    for t in texts:
        words = {w.strip(".,!?'").lower() for w in t.replace("'", " ").split()}
        assert not words & FORBIDDEN, t


def test_reaction_time_under_2s(make_session):
    h = make_session()
    h.to_first_question()
    for kind in (Kind.HELP, Kind.HELP, Kind.HELP, Kind.REPEAT, Kind.PAUSE, Kind.CONTINUE):
        h.press(kind)
    for rec in h.log.events("evenement_entree"):
        assert rec["reaction_ms"] < 2000
