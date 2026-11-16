"""L'IA locale (V2) : filtre des phrases, consignes données à l'IA, appel à Ollama.

Sommaire (chercher « PARTIE n ») :
  1. Filtre des phrases
  2. Consignes données à l'IA
  3. Appel à l'IA (Ollama)
  4. IA + filtre + phrases de secours
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
import unicodedata
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from compagnon.reglages import CONTENU

# ================================================================================================
# PARTIE 1 — FILTRE DES PHRASES
# Automatic check of every AI sentence (FP3). A sentence that fails is replaced by a
# prepared phrase (see service.py).
#
# Rules:
# * one sentence, at most 10 words, letters and simple punctuation only;
# * every word belongs to the simple vocabulary (+ the activity's own words);
# * French elisions (l', c'est, qu'il, jusqu'à...) and hyphenated forms (celui-ci,
#   touche-le, a-t-il) are split before the lookup;
# * accents: Unicode is normalised (NFC, typographic apostrophes, non-breaking spaces);
#   a word written without its accents ("tres") is accepted only if it matches exactly one
#   word of the vocabulary, and the spelling is then corrected ("très");
# * no forbidden word (failure, medical, inappropriate), even without accents;
# * no other colour than the target; "simplifier" must keep the target colour,
#   "indice" must use one of the prepared associations (the AI phrases, it does not invent);
# * quality (added after the first benchmark): at least 3 words, "comme" followed by an
#   article ("comme le ciel", not "comme mer"), and a "simplifier" sentence must differ
#   from the instruction it replaces.
# ================================================================================================

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
_COMME = re.compile(rf"\bcomme\s+([{_LETTERS}]+)(')?")
# "la herbe", "le orange" -> the article must be elided (l'herbe, l'orange)
_NO_ELISION = re.compile(rf"\b(le|la|de|ne|je|que)\s+([aeiouàâéèêîôœh][{_LETTERS}]*)")
H_ASPIRE = frozenset({"haut", "haute", "hibou", "héros", "hérisson", "hamster", "haricot",
                      "haricots", "hache", "hop"})
IMPERATIVES = {"toucher": "touche", "montrer": "montre", "trouver": "trouve",
               "regarder": "regarde", "chercher": "cherche", "choisir": "choisis",
               "montrez": "montre", "touchez": "touche", "trouvez": "trouve",
               "regardez": "regarde", "cherchez": "cherche"}
MIN_WORDS = 3
DETERMINERS = frozenset({"un", "une", "le", "la", "les", "des", "du", "mon", "ma", "mes",
                         "ton", "ta", "tes", "ce", "cet", "cette", "ces",
                         "celle", "celui", "celles", "ceux"})  # "comme celle d'une feuille"


def _core(text: str) -> str:
    return re.sub(r"[\s.!?]+$", "", text).strip()


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
    t = lines[0].replace("**", "").replace("__", "")  # markdown bold
    t = _LABEL.sub("", t.strip())
    t = t.strip().strip(_QUOTES).strip()
    t = normalize(t)
    # "Toucher le rouge." -> "Touche le rouge." (we talk to the child)
    first, _, rest = t.partition(" ")
    if first.lower() in IMPERATIVES:
        imp = IMPERATIVES[first.lower()]
        t = (imp.capitalize() if first[0].isupper() else imp) + (" " + rest if rest else "")
    return t


@dataclass(frozen=True)
class FilterResult:
    ok: bool
    text: str
    reason: str | None = None


def load_default_lexicon() -> set[str]:
    raw = (CONTENU / "lexique_simple.txt").read_text("utf-8")
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

        if kind in ("simplifier", "indice") and len(_WORD_RUN.findall(low)) < MIN_WORDS:
            return FilterResult(False, t, "trop_court")
        for m in _COMME.finditer(low):  # "bleu comme mer" -> missing article
            if m.group(1) not in DETERMINERS and not (m.group(1) in ELISIONS and m.group(2)):
                return FilterResult(False, t, "article_manquant")
        if re.search(r"\bcomme\s*[.!?]*$", low):
            return FilterResult(False, t, "article_manquant")
        for m in _NO_ELISION.finditer(low):
            if m.group(2) not in H_ASPIRE:
                return FilterResult(False, t, "elision_manquante")
        if kind == "simplifier" and target_forms and not target_forms & set(words):
            return FilterResult(False, t, "cible_absente")
        if kind == "simplifier" and _core(low) == _core(normalize(ctx.get("consigne", "")).lower()):
            return FilterResult(False, t, "identique")
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


# ================================================================================================
# PARTIE 2 — CONSIGNES DONNÉES À L'IA
# Prompts for the local model. Two styles: "normal" and "court" (shorter, for slow CPUs).
#
# The model only PHRASES things: the target colour and the associations ("une fraise",
# "le ciel"...) come from the activity content, so a hint is never an invented fact.
# Small models follow complete example sentences much better than rules, so each prompt
# shows examples built with the SAME colour (another colour would leak into the answer)
# and asks for one association drawn at random (variety).
#
# Benchmark on RTX 2050 (2026-11-16): with rule-only prompts the 1.5b model wrote
# "Bleu comme mer." / "Comme lavande." -> replaced by these few-shot prompts.
# ================================================================================================

SYSTEM = {
    "normal": ("Tu aides un enfant de 6 ans à reconnaître les couleurs. Tu écris UNE phrase "
               "courte et correcte, en français très simple, avec les petits mots "
               "(le, la, un, une). Pas de guillemets, pas d'emoji."),
    "court": "Une phrase courte et correcte, français très simple, avec le, la, un, une.",
}


def _le(cible: str) -> str:
    return "l'" if cible[0] in "aeiouyéè" else "le "


def build_prompt(style: str, kind: str, ctx: dict, rng: random.Random) -> tuple[str, str]:
    """Returns (system, prompt)."""
    style = style if style in SYSTEM else "normal"
    cible = ctx["cible"]
    Cible = cible.capitalize()
    le = _le(cible)
    assoc = list(ctx.get("associations", [])) or [cible]
    if kind == "simplifier":
        # The full instruction is NOT shown: the 1.5b model then copied it without the
        # colour ("Touche le ballon.") in 1 answer out of 5.
        if style == "court":
            prompt = (f"Exemple : Touche {le}{cible}.\n"
                      f"Autre phrase pour toucher le {cible}, avec le mot « {cible} » :")
        else:
            # The model sometimes answers with the infinitive ("Toucher le rouge."):
            # clean_llm_output turns it into "Touche le rouge.". A wording without
            # "toucher" was tried and gave twice as many rejects (echoed the prompt).
            prompt = (
                f"Dis à l'enfant de toucher la couleur {cible}, en 3 à 6 mots. "
                f"Le mot « {cible} » doit être dans la phrase.\n"
                "Exemples :\n"
                f"Touche {le}{cible}.\n"
                f"Où est le ballon {cible} ?\n"
                f"Montre-moi {le}{cible}.\n"
                f"Ta phrase avec « {cible} » :"
            )
    elif kind == "indice":
        mot = rng.choice(assoc)
        others = [a for a in assoc if a != mot] or assoc
        ex1, ex2 = others[0], others[-1]
        if style == "court":
            prompt = (f"Exemple : {Cible} comme {ex1}.\n"
                      f"Même chose avec « {mot} » :")
        else:
            prompt = (
                f"Écris un petit indice pour trouver la couleur {cible}, avec « {mot} ».\n"
                "Exemples :\n"
                f"{Cible} comme {ex1}.\n"
                f"C'est la couleur de {ex2}.\n"
                f"Avec « {mot} » :"
            )
    else:
        raise ValueError(f"type inconnu : {kind}")
    return SYSTEM[style], prompt


# ================================================================================================
# PARTIE 3 — APPEL À L'IA (OLLAMA)
# Text generators behind one interface: stub (V1), Ollama (V2). On the robot (S8) a
# cached generator can be added here without touching the rest.
# ================================================================================================

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
# Models with a "thinking" mode (Ollama `think` option), turned off for speed.
THINKING_PREFIXES = ("qwen3", "deepseek-r1", "gpt-oss", "magistral")


class Rephraser(Protocol):
    enabled: bool
    name: str

    def generate(self, kind: str, ctx: dict) -> str | None: ...


class StubRephraser:
    """V1: no model. The service always uses the prepared phrases."""

    enabled = False
    name = "stub"

    def generate(self, kind: str, ctx: dict) -> str | None:
        return None


def check_local(host: str) -> str:
    """FC5: refuse any non-local address, so nothing can leave the computer."""
    parsed = urlparse(host)
    if parsed.hostname not in LOCAL_HOSTS:
        raise ValueError(f"Hôte refusé (doit être local) : {host}")
    return host.rstrip("/")


class OllamaRephraser:
    enabled = True

    def __init__(self, model: str = "qwen2.5:1.5b", host: str = "http://127.0.0.1:11434",
                 prompt_style: str = "normal", temperature: float = 0.6,
                 rng: random.Random | None = None) -> None:
        self.host = check_local(host)
        self.model = model
        self.prompt_style = prompt_style
        self.temperature = temperature
        self.rng = rng or random.Random()
        self.name = f"ollama:{model}:{prompt_style}"
        self.thinking_model = model.startswith(THINKING_PREFIXES)

    def _post(self, path: str, body: dict, timeout: float) -> dict:
        req = urllib.request.Request(
            self.host + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (local only)
            return json.loads(resp.read().decode("utf-8"))

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.host + "/api/tags", timeout=1.0) as resp:  # noqa: S310
                tags = json.loads(resp.read().decode("utf-8"))
        except (OSError, ValueError):
            return False
        names = {m.get("name", "") for m in tags.get("models", [])}
        return self.model in names or f"{self.model}:latest" in names

    def warmup(self) -> None:
        """Load the model in memory and keep it there (first call can take seconds)."""
        body = self._body("Réponds en un mot.", "Bonjour")
        body["options"]["num_predict"] = 1
        self._post("/api/generate", body, 120)

    def generate(self, kind: str, ctx: dict) -> str | None:
        system, prompt = build_prompt(self.prompt_style, kind, ctx, self.rng)
        out = self._post("/api/generate", self._body(system, prompt), timeout=10)
        return out.get("response")

    def _body(self, system: str, prompt: str) -> dict:
        # Same options for warm-up and real calls: a different num_ctx makes Ollama
        # reload the model (seen in the benchmark: 7-10 s on the first real request).
        body = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": self.temperature,
                "top_p": 0.9,
                "num_predict": 24,
                "num_ctx": 512,
                "stop": ["\n"],
            },
        }
        if self.thinking_model:
            body["think"] = False  # no hidden reasoning: it would eat the time and tokens
        return body


# ================================================================================================
# PARTIE 4 — IA + FILTRE + PHRASES DE SECOURS
# AI service = generator + filter + prepared phrases + hard timeout (FP3).
#
# The < 2 s guarantee comes from the timeout: if the model is late or its sentence is
# rejected, a prepared phrase is used immediately.
# ================================================================================================

DEFAULT_TIMEOUT_S = 1.3


@dataclass(frozen=True)
class Phrase:
    text: str
    source: str  # "llm" | "reserve"
    latency_ms: int
    reason: str | None = None  # why the AI sentence was not used
    raw: str | None = None  # raw model output (for the log)


class AIService:
    def __init__(self, rephraser: Rephraser, sentence_filter: SentenceFilter,
                 timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self.rephraser = rephraser
        self.filter = sentence_filter
        self.timeout_s = timeout_s
        self._next: dict[tuple[str, str], int] = {}

    def rephrase(self, kind: str, ctx: dict) -> Phrase:
        t0 = time.perf_counter()
        raw: str | None = None
        reason: str | None = "ia_desactivee"
        if self.rephraser.enabled:
            raw, reason = self._call(kind, ctx)
            if raw is not None:
                res = self.filter.check(clean_llm_output(raw), kind, ctx)
                if res.ok:
                    return Phrase(res.text, "llm", _ms(t0), None, raw)
                reason = res.reason
        return Phrase(self._fallback(kind, ctx), "reserve", _ms(t0), reason, raw)

    def _call(self, kind: str, ctx: dict) -> tuple[str | None, str | None]:
        box: dict[str, object] = {}

        def run() -> None:
            try:
                box["out"] = self.rephraser.generate(kind, ctx)
            except Exception as exc:  # noqa: BLE001 - any failure -> prepared phrase
                box["err"] = repr(exc)

        th = threading.Thread(target=run, daemon=True)
        th.start()
        th.join(self.timeout_s)
        if th.is_alive():
            return None, "timeout"
        if "err" in box:
            return None, "erreur"
        out = box.get("out")
        if not out:
            return None, "vide"
        return str(out), None

    def _fallback(self, kind: str, ctx: dict) -> str:
        options = ctx["reserve"][kind]
        key = (ctx.get("cible", ""), kind)
        i = self._next.get(key, 0)
        self._next[key] = i + 1
        return options[i % len(options)]


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
