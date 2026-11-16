"""Sentence filter: keeps good French sentences (elisions, accents), rejects the rest."""

from __future__ import annotations

import random

import pytest

from compagnon import phrases
from compagnon.ia import FORBIDDEN, SentenceFilter, clean_llm_output, load_default_lexicon
from compagnon.jeux import ColorActivity


@pytest.fixture(scope="module")
def filt() -> SentenceFilter:
    return SentenceFilter.default()


@pytest.fixture(scope="module")
def ctx_rouge() -> dict:
    act = ColorActivity()
    item = act.make_item(1, random.Random(0))
    item.key = "rouge"
    item.instruction = act.colors["rouge"]["consigne"]
    return act.ai_context(item)


@pytest.mark.parametrize("text", [
    "C'est la couleur des fraises.",
    "Rouge comme une fraise.",
    "Il est rouge comme une tomate !",
    "C'est très rouge, comme une cerise.",
    "Une fraise, c'est rouge.",
    "Regarde, c'est l'objet rouge comme la fraise.",
    "La coccinelle est rouge, touche-le.",
    "Aujourd’hui, cherche la couleur des fraises.",  # typographic apostrophe
    "C’est rouge comme les pompiers.",
    "ÉCOUTE, rouge comme une fraise.",  # uppercase accented letter
])
def test_good_hints_are_accepted(filt, ctx_rouge, text):
    res = filt.check(text, "indice", ctx_rouge)
    assert res.ok, (text, res.reason)


@pytest.mark.parametrize("text", [
    "Touche le rouge.",
    "Montre-moi le ballon rouge.",
    "Où est le ballon rouge ?",
    "Qu'est-ce qui est rouge ?",
    "Touche celui qui est rouge.",
])
def test_good_simplifications_are_accepted(filt, ctx_rouge, text):
    res = filt.check(text, "simplifier", ctx_rouge)
    assert res.ok, (text, res.reason)


def test_missing_accent_is_corrected(filt, ctx_rouge):
    res = filt.check("C'est tres rouge comme une fraise.", "indice", ctx_rouge)
    assert res.ok and res.text == "C'est très rouge comme une fraise."
    res = filt.check("Ecoute, rouge comme une fraise.", "indice", ctx_rouge)
    assert res.ok and res.text.startswith("Écoute")


@pytest.mark.parametrize("text, reason", [
    ("", "vide"),
    ("Touche le ballon rouge qui est à côté du petit ballon vert là-bas.", "trop_long"),
    ("Touche le rouge. Bravo.", "plusieurs_phrases"),
    ("Touche le rouge 🎈.", "caracteres"),
    ("Touche le rouge n°1.", "caracteres"),
    ("Touche le ballon.", "cible_absente"),
    ("Touche le rouge, pas le bleu.", "autre_couleur:bleu"),
    ("C'est faux, touche le rouge.", "mot_interdit:faux"),
    ("C'est une erreur, touche le rouge.", "mot_interdit:erreur"),
    ("Le médecin aime le rouge.", "mot_interdit:médecin"),
    ("Le medecin aime le rouge.", "mot_interdit:medecin"),
    ("Dépêche-toi, touche le rouge.", "mot_interdit:dépêche"),
    ("Sélectionne l'élément rouge.", "mot_inconnu:sélectionne"),
    ("Touche le rouge, connard.", "mot_interdit:connard"),
    ("Xyz'est rouge.", "mot_inconnu:xyz'"),
])
def test_bad_sentences_are_rejected(filt, ctx_rouge, text, reason):
    res = filt.check(text, "simplifier", ctx_rouge)
    assert not res.ok
    assert res.reason == reason, res.reason


def test_hint_must_use_a_prepared_association(filt, ctx_rouge):
    assert not filt.check("Il est rouge comme le ciel.", "indice", ctx_rouge).ok
    assert filt.check("Il est rouge comme le ciel.", "indice", ctx_rouge).reason in (
        "association_absente", "mot_inconnu:ciel")


def test_clean_llm_output():
    assert clean_llm_output('Phrase : « Touche le rouge. »\nAutre ligne') == "Touche le rouge."
    assert clean_llm_output('"Rouge comme une fraise."') == "Rouge comme une fraise."
    assert clean_llm_output("\n\n  Indice: Rouge comme une fraise") == "Rouge comme une fraise"
    assert clean_llm_output(None) == ""


def test_all_prepared_phrases_pass_the_filter(filt):
    """The fallback phrases must themselves be valid, otherwise the guarantee means nothing."""
    act = ColorActivity()
    for cid in act.colors:
        item = act.make_item(4, random.Random(0))
        item.key = cid
        item.instruction = act.colors[cid]["consigne"]
        ctx = act.ai_context(item)
        assert filt.check(item.instruction, "fixe", ctx).ok, item.instruction
        for p in ctx["reserve"]["simplifier"]:
            assert filt.check(p, "simplifier", ctx).ok, (p, filt.check(p, "simplifier", ctx))
        for p in ctx["reserve"]["indice"]:
            assert filt.check(p, "indice", ctx).ok, (p, filt.check(p, "indice", ctx))
    for p in (*phrases.ALL_FIXED, act.announce_text, act.end_text):
        res = filt.check(p, "fixe", {"vocabulaire": ["couleurs"]})
        assert res.ok, (p, res.reason)


def test_lexicon_and_forbidden_do_not_overlap():
    assert not load_default_lexicon() & FORBIDDEN


@pytest.mark.parametrize("text,kind,reason", [
    ("Chocolat.", "indice", "trop_court"),
    ("Comme fraise.", "indice", "trop_court"),
    ("Rouge comme fraise.", "indice", "article_manquant"),
    ("La fraise est rouge comme.", "indice", "article_manquant"),
    ("Touche le ballon rouge.", "simplifier", "identique"),
])
def test_quality_rules_from_benchmark(filt, ctx_rouge, text, kind, reason):
    r = filt.check(text, kind, ctx_rouge)
    assert not r.ok and r.reason == reason


def test_participle_typo_is_corrected_to_imperative(filt, ctx_rouge):
    r = filt.check("Touché le rouge.", "simplifier", ctx_rouge)
    assert r.ok and r.text == "Touche le rouge."


def test_comme_with_elided_article_is_accepted(filt):
    act = ColorActivity()
    item = act.make_item(1, random.Random(0))
    item.key, item.instruction = "vert", act.colors["vert"]["consigne"]
    assert filt.check("Vert comme l'herbe.", "indice", act.ai_context(item)).ok


def test_infinitive_and_markdown_are_cleaned():
    assert clean_llm_output("**Toucher le rouge.**") == "Touche le rouge."
    assert clean_llm_output("Montrer l'orange.") == "Montre l'orange."


@pytest.mark.parametrize("text", ["C'est la couleur de la herbe.", "Montre-moi le herbe."])
def test_missing_elision_is_rejected(filt, text):
    act = ColorActivity()
    item = act.make_item(1, random.Random(0))
    item.key, item.instruction = "vert", act.colors["vert"]["consigne"]
    assert filt.check(text, "fixe", act.ai_context(item)).reason == "elision_manquante"
