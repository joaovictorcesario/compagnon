"""AI service without a real model: timeout, errors, and 100 adversarial outputs."""

from __future__ import annotations

import random
import time

import pytest

from compagnon.activities import ColorActivity
from compagnon.ai import AIService, SentenceFilter, StubRephraser
from compagnon.ai.filter import FORBIDDEN
from compagnon.ai.rephraser import OllamaRephraser


def _ctx(color: str) -> dict:
    act = ColorActivity()
    item = act.make_item(4, random.Random(0))
    item.key = color
    item.instruction = act.colors[color]["consigne"]
    return act.ai_context(item)


class SlowRephraser:
    enabled, name = True, "lent"

    def generate(self, kind, ctx):
        time.sleep(3)
        return "Touche le rouge."


class BrokenRephraser:
    enabled, name = True, "casse"

    def generate(self, kind, ctx):
        raise ConnectionError("ollama arrêté")


class ScriptedRephraser:
    """Plays a list of outputs, good and bad, like a small model having a bad day."""

    enabled, name = True, "script"

    def __init__(self, outputs):
        self.outputs, self.i = outputs, 0

    def generate(self, kind, ctx):
        out = self.outputs[self.i % len(self.outputs)]
        self.i += 1
        return out


BAD = [
    "C'est faux, recommence.", "Tu as raté, touche le rouge.", "Touche le bleu.",
    "Touche le rouge. Bravo. Encore.", "Phrase : Touche le rouge 🎈", "Ton autisme te gêne ?",
    "Le médecin dit rouge.", "Dépêche-toi, touche le rouge !",
    "Touche le ballon rouge qui est juste à côté du grand ballon tout vert.",
    "Sélectionnez l'élément de couleur rouge.", "Il faut tuer le rouge.", "", "   ",
    "Rouge comme le sang.", "Rouge, c'est nul.", "1. Touche le rouge.",
    "Voici une phrase simple : touche le rouge.", "<b>Touche le rouge</b>",
    "Touche le rouge, idiot.", "Rouge comme une erreur.",
]
GOOD = [
    "Touche le rouge.", "« Montre le ballon rouge. »", "Où est le rouge ?",
    "Rouge comme une fraise.", "C’est la couleur des tomates.", "Indice : rouge comme une cerise",
]


def test_timeout_gives_prepared_phrase_fast():
    svc = AIService(SlowRephraser(), SentenceFilter.default(), timeout_s=0.3)
    t0 = time.perf_counter()
    p = svc.rephrase("simplifier", _ctx("rouge"))
    assert time.perf_counter() - t0 < 1.0
    assert p.source == "reserve" and p.reason == "timeout"
    assert p.text in _ctx("rouge")["reserve"]["simplifier"]


def test_model_error_gives_prepared_phrase():
    p = AIService(BrokenRephraser(), SentenceFilter.default()).rephrase("indice", _ctx("vert"))
    assert p.source == "reserve" and p.reason == "erreur"


def test_stub_uses_prepared_phrases_in_turn():
    svc = AIService(StubRephraser(), SentenceFilter.default())
    ctx = _ctx("jaune")
    texts = [svc.rephrase("indice", ctx).text for _ in range(4)]
    assert texts[0] != texts[1] and texts[0] == texts[2]


def test_100_adversarial_outputs_never_reach_the_child():
    rng = random.Random(42)
    outputs = [rng.choice(BAD + GOOD) for _ in range(100)]
    svc = AIService(ScriptedRephraser(outputs), SentenceFilter.default(), timeout_s=1.0)
    filt = SentenceFilter.default()
    ctx = _ctx("rouge")
    sources = []
    for i in range(100):
        kind = "simplifier" if outputs[i] in BAD or i % 2 == 0 else "indice"
        p = svc.rephrase(kind, ctx)
        sources.append(p.source)
        assert filt.check(p.text, kind, ctx).ok, p
        words = {w.strip(".,!?«»").lower() for w in p.text.replace("'", " ").split()}
        assert not words & FORBIDDEN
        if outputs[i] in BAD:
            assert p.source == "reserve", (outputs[i], p)
    assert "llm" in sources and "reserve" in sources


def test_ollama_host_must_be_local():
    with pytest.raises(ValueError):
        OllamaRephraser(host="http://192.168.1.20:11434")
    with pytest.raises(ValueError):
        OllamaRephraser(host="https://api.example.com")
    OllamaRephraser(host="http://localhost:11434")


def test_ai_phrase_is_logged_with_its_source(make_session):
    from compagnon.core.events import Kind

    ai = AIService(ScriptedRephraser(GOOD), SentenceFilter.default())
    h = make_session(ai=ai)
    h.to_first_question()
    h.press(Kind.HELP)
    h.press(Kind.HELP)  # level 2 -> AI
    rec = h.log.events("ia")[-1]
    assert rec["source"] in ("llm", "reserve")
    assert h.log.events("dit")[-1]["source"] == rec["source"]
