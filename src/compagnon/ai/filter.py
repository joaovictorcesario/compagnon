"""Automatic check of every AI sentence (FP3). A sentence that fails is replaced by a
prepared phrase (see service.py).

Rules:
* one sentence, at most 10 words, letters and simple punctuation only;
* every word belongs to the simple vocabulary (+ the activity's own words);
* French elisions (l', c'est, qu'il, jusqu'à...) and hyphenated forms (celui-ci,
  touche-le, a-t-il) are split before the lookup;
* accents: Unicode is normalised (NFC, typographic apostrophes, non-breaking spaces);
  a word written without its accents ("tres") is accepted only if it matches exactly one
  word of the vocabulary, and the spelling is then corrected ("très");
* no forbidden word (failure, medical, inappropriate), even without accents;
* no other colour than the target; "simplifier" must keep the target colour,
  "indice" must use one of the prepared associations (the AI phrases, it does not invent).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources

MAX_WORDS = 10

ELISIONS = frozenset({"l", "d", "j", "qu", "c", "n", "s", "m", "t", "jusqu", "lorsqu", "puisqu"})

FORBIDDEN = frozenset({
    # echec / jugement (FP5 : jamais de message d'echec)
    "faux", "fausse", "raté", "ratée", "rater", "nul", "nulle", "nuls", "échec", "échoué",
    "échouer", "perdu", "perdue", "perdre", "mauvais", "mauvaise", "mal", "erreur", "erreurs",
    "faute", "fautes", "bête", "idiot", "idiote", "stupide", "incapable", "dommage", "honte",
    "puni", "punition", "gronder", "vite", "dépêche", "tais", "taire", "triste", "pleure",
    "pleurer",
    # medical / diagnostic (FC6)
    "autisme", "autiste", "autistes", "malade", "maladie", "médecin", "docteur", "diagnostic",
    "traitement", "médicament", "médicaments", "thérapie", "trouble", "troubles", "handicap",
    "handicapé", "crise", "crises", "symptôme", "hôpital",
    # inadapte
    "mort", "morte", "mourir", "meurt", "tuer", "tue", "sang", "arme", "armes", "fusil", "peur",
    "méchant", "méchante", "monstre", "diable", "enfer", "guerre", "drogue", "alcool", "sexe",
    "merde", "putain", "con", "conne", "connard", "bordel", "chier", "fesse", "fesses", "caca",
    "zut",
})

_LETTERS = "a-zàâäçéèêëîïôöùûüÿœæ"
_ALLOWED = re.compile(rf"^[{_LETTERS}' ,.!?\-]+$")
_WORD_RUN = re.compile(rf"[{_LETTERS}]+")
_LABEL = re.compile(r"^\s*(phrase|indice|consigne|réponse|reponse)\s*:\s*", re.IGNORECASE)
_QUOTES = "«»\"“”„‘’'`*"


def strip_accents(word: str) -> str:
    nfd = unicodedata.normalize("NFD", word)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", text)
    t = t.replace("’", "'").replace("‘", "'").replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()


def clean_llm_output(raw: str | None) -> str:
    """Remove what small models add around the sentence (labels, quotes, extra lines)."""
    if not raw:
        return ""
    lines = [ln for ln in raw.replace("\r", "").split("\n") if ln.strip()]
    if not lines:
        return ""
    t = _LABEL.sub("", lines[0].strip())
    t = t.strip().strip(_QUOTES).strip()
    return normalize(t)


@dataclass(frozen=True)
class FilterResult:
    ok: bool
    text: str
    reason: str | None = None


def load_default_lexicon() -> set[str]:
    raw = resources.files("compagnon.ai").joinpath("lexique_simple.txt").read_text("utf-8")
    words: set[str] = set()
    for line in raw.splitlines():
        line = line.split("#", 1)[0]
        words.update(normalize(w).lower() for w in line.split())
    return words


class SentenceFilter:
    def __init__(self, lexicon: Iterable[str], forbidden: Iterable[str] = FORBIDDEN,
                 max_words: int = MAX_WORDS) -> None:
        self.lexicon = {normalize(w).lower() for w in lexicon}
        self.forbidden = {normalize(w).lower() for w in forbidden}
        self.forbidden_stripped = {strip_accents(w) for w in self.forbidden}
        self.max_words = max_words

    @classmethod
    def default(cls) -> SentenceFilter:
        return cls(load_default_lexicon())

    def check(self, text: str, kind: str, ctx: dict | None = None) -> FilterResult:
        ctx = ctx or {}
        t = normalize(text or "")
        if not t:
            return FilterResult(False, t, "vide")
        if t[-1] not in ".!?":
            t += "."
        low = t.lower()
        if len(low) != len(t) or not _ALLOWED.match(low):
            return FilterResult(False, t, "caracteres")
        core = re.sub(r"[\s.!?]+$", "", low)
        if re.search(r"[.!?]", core):
            return FilterResult(False, t, "plusieurs_phrases")
        n_words = sum(1 for w in low.split() if _WORD_RUN.search(w))
        if n_words == 0:
            return FilterResult(False, t, "vide")
        if n_words > self.max_words:
            return FilterResult(False, t, "trop_long")

        vocab = self.lexicon | {normalize(w).lower() for w in ctx.get("vocabulaire", ())}
        by_stripped: dict[str, set[str]] = {}
        for w in vocab:
            by_stripped.setdefault(strip_accents(w), set()).add(w)
        target_forms = {w.lower() for w in ctx.get("formes", ())}
        other_colors = {w.lower() for w in ctx.get("autres_couleurs", ())} - target_forms

        words: list[str] = []
        corrections: list[tuple[int, int, str]] = []
        for m in _WORD_RUN.finditer(low):
            w, start, end = m.group(), m.start(), m.end()
            nxt = low[end:end + 1]
            prev = low[start - 1:start] if start else ""
            if w == "aujourd" and low.startswith("'hui", end):
                words.append("aujourd'hui")
                continue
            if w == "hui" and low[max(0, start - 8):start] == "aujourd'":
                continue
            if nxt == "'":
                if w not in ELISIONS:
                    return FilterResult(False, t, f"mot_inconnu:{w}'")
                continue
            if w == "t" and prev == "-" and nxt == "-":  # a-t-il
                continue
            base = strip_accents(w)
            if w in self.forbidden or base in self.forbidden_stripped:
                return FilterResult(False, t, f"mot_interdit:{w}")
            if w not in vocab:
                cands = by_stripped.get(base, set())
                if len(cands) != 1:
                    return FilterResult(False, t, f"mot_inconnu:{w}")
                fixed = next(iter(cands))
                corrections.append((start, end, fixed))
                w = fixed
            if w in other_colors:
                return FilterResult(False, t, f"autre_couleur:{w}")
            words.append(w)

        if kind == "simplifier" and target_forms and not target_forms & set(words):
            return FilterResult(False, t, "cible_absente")
        if kind == "indice":
            assoc = {a.lower() for a in ctx.get("associations_formes", ctx.get("associations", ()))}
            if assoc and not assoc & set(words):
                return FilterResult(False, t, "association_absente")

        for start, end, fixed in reversed(corrections):
            seg = t[start:end]
            rep = fixed[0].upper() + fixed[1:] if seg[:1].isupper() else fixed
            t = t[:start] + rep + t[end:]
        t = t[0].upper() + t[1:]
        return FilterResult(True, t, None)
