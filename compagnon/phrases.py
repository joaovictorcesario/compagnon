"""Fixed phrases said by the character, read from contenu/phrases.txt (editable by the team).

All of them pass the sentence filter (tested). Never a failure message (FP5): a wrong answer
only gets a neutral "Essaie encore."
"""

from __future__ import annotations

from compagnon.reglages import CONTENU

NAMES = ("WRONG", "VISUAL_HINT", "MODEL", "PAUSE_OFFER", "SCHEDULED_PAUSE_OFFER", "PAUSE",
         "END_CHILD", "END_SILENCE", "END_ADULT")


def load(path=CONTENU / "phrases.txt") -> dict[str, str]:
    """`NOM = texte` lines; '#' starts a comment line. Every name must be present."""
    found: dict[str, str] = {}
    for n, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, text = line.partition("=")
        name, text = name.strip(), text.strip().strip('"')
        if not sep or name not in NAMES or not text:
            raise ValueError(f"{path.name}, ligne {n} : « {line} » (attendu : NOM = texte)")
        found[name] = text
    missing = [n for n in NAMES if n not in found]
    if missing:
        raise ValueError(f"{path.name} : il manque {', '.join(missing)}")
    return found


_P = load()
WRONG = _P["WRONG"]
VISUAL_HINT = _P["VISUAL_HINT"]
MODEL = _P["MODEL"]
PAUSE_OFFER = _P["PAUSE_OFFER"]
SCHEDULED_PAUSE_OFFER = _P["SCHEDULED_PAUSE_OFFER"]
PAUSE = _P["PAUSE"]
END_CHILD = _P["END_CHILD"]
END_SILENCE = _P["END_SILENCE"]
END_ADULT = _P["END_ADULT"]

ALL_FIXED = (WRONG, VISUAL_HINT, MODEL, PAUSE_OFFER, SCHEDULED_PAUSE_OFFER, PAUSE,
             END_CHILD, END_SILENCE)

HELP_LABELS = {
    0: "aucune",
    1: "répéter",
    2: "reformuler",
    3: "indice",
    4: "indice visuel",
    5: "modèle",
}
