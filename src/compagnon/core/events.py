"""Input events, independent of the display (FC7): pygame, robot or tests all produce these."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Kind(str, Enum):
    CHOICE = "choix"  # value = choice id
    HELP = "aide"
    PAUSE = "pause"
    FINISHED = "fini"  # "J'ai fini"
    REPEAT = "repeter"  # drawn speaker icon next to the instruction
    CONTINUE = "continuer"  # "Continuer" / "Reprendre"
    BACKGROUND = "fond"  # click on nothing (still counts for agitation)
    ADULT_OPEN = "adulte_ouvert"
    ADULT_CLOSE = "adulte_ferme"
    NEW_SESSION = "nouvelle_seance"
    QUIT = "quitter"
    # Home screen (handled by the app, never by the session controller)
    MENU = "menu"  # back to the home screen ("Maison" button, confirmed)
    START = "lancer"  # value = activity id of the touched card
    DESCRIBE = "decrire"  # value = activity id: the character says the card's description


CHILD_KINDS = frozenset(
    {Kind.CHOICE, Kind.HELP, Kind.PAUSE, Kind.FINISHED, Kind.REPEAT, Kind.CONTINUE, Kind.BACKGROUND}
)


@dataclass(frozen=True)
class InputEvent:
    kind: Kind
    value: str | None = None
