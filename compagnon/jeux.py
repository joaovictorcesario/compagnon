"""Les jeux : ce qu'est un jeu, le jeu des couleurs, les cartes de l'accueil.

Sommaire (chercher « PARTIE n ») :
  1. Ce qu'est un jeu
  2. Le jeu des couleurs
  3. Les cartes de l'écran d'accueil
  4. Préparer les jeux choisis
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol

from compagnon.reglages import CONTENU

# ================================================================================================
# PARTIE 1 — CE QU'EST UN JEU
# Generic activity contract (FP1). New activities (shapes, emotions...) implement this.
# ================================================================================================

@dataclass(frozen=True)
class Choice:
    id: str
    label: str
    rgb: tuple[int, int, int]


@dataclass(frozen=True, eq=False)
class ImageSpec:
    """What picture goes with the instruction (FC4). The display decides how to draw it."""

    kind: str
    data: dict = field(default_factory=dict)


@dataclass
class Item:
    key: str  # id of the correct answer
    choices: list[Choice]
    instruction: str
    image: ImageSpec


class Activity(Protocol):
    id: str
    title: str
    announce_text: str
    end_text: str
    max_difficulty: int

    def make_item(self, difficulty: int, rng: random.Random) -> Item: ...

    def is_correct(self, item: Item, choice_id: str) -> bool: ...

    def model_choices(self, item: Item) -> list[Choice]: ...

    def ai_context(self, item: Item) -> dict: ...

    def fixed_phrases(self) -> list[str]: ...


# ================================================================================================
# PARTIE 2 — LE JEU DES COULEURS
# Activity "Les couleurs": touch the balloon of the requested colour.
#
# Difficulty = number of choices (2, 3, 4, 6), independent from the 5 help levels.
# ================================================================================================

def noun(association: str) -> str:
    """'une fraise' -> 'fraise', "l'herbe" -> 'herbe' (associations are stored with article)."""
    return association.replace("'", " ").split()[-1]


def _plural_forms(words: list[str]) -> list[str]:
    out: list[str] = []
    for w in words:
        out.append(w)
        if not w.endswith(("s", "x")):
            out.append(w + "s")
    return out


class ColorActivity:
    id = "couleurs"

    def __init__(self, content: dict | None = None) -> None:
        if content is None:
            text = (CONTENU / "couleurs.json").read_text("utf-8")
            content = json.loads(text)
        self.title: str = content["titre"]
        self.announce_text: str = content["annonce"]
        self.end_text: str = content["fin"]
        self.colors: dict[str, dict] = {c["id"]: c for c in content["couleurs"]}
        self.levels: dict[int, dict] = {int(k): v for k, v in content["niveaux"].items()}
        self.max_difficulty = max(self.levels)
        self._last_target: str | None = None

    def make_item(self, difficulty: int, rng: random.Random) -> Item:
        level = self.levels[max(1, min(self.max_difficulty, difficulty))]
        pool: list[str] = level["couleurs"]
        candidates = [c for c in pool if c != self._last_target] or pool
        target = rng.choice(candidates)
        self._last_target = target
        others = rng.sample([c for c in pool if c != target], level["choix"] - 1)
        ids = [target, *others]
        rng.shuffle(ids)
        choices = [Choice(i, self.colors[i]["nom"], tuple(self.colors[i]["rgb"])) for i in ids]
        return Item(
            key=target,
            choices=choices,
            instruction=self.colors[target]["consigne"],
            image=ImageSpec("ballon_mystere"),
        )

    def is_correct(self, item: Item, choice_id: str) -> bool:
        return choice_id == item.key

    def model_choices(self, item: Item) -> list[Choice]:
        """Help level 5: only the right answer and one other, same order as before."""
        other = next(c for c in item.choices if c.id != item.key)
        return [c for c in item.choices if c.id in (item.key, other.id)]

    def ai_context(self, item: Item) -> dict:
        c = self.colors[item.key]
        others = [f for cid, o in self.colors.items() if cid != item.key for f in o["formes"]]
        all_forms = [f for o in self.colors.values() for f in o["formes"]]
        all_assoc = [noun(a) for o in self.colors.values() for a in o["associations"]]
        return {
            "cible": c["nom"],
            "formes": list(c["formes"]),
            "associations": list(c["associations"]),
            "associations_formes": _plural_forms([noun(a) for a in c["associations"]]),
            "consigne": item.instruction,
            "autres_couleurs": others,
            "vocabulaire": all_forms + _plural_forms(all_assoc) + ["ballon", "ballons"],
            "reserve": {
                "simplifier": list(c["reserve_simplifier"]),
                "indice": list(c["reserve_indice"]),
            },
        }

    def fixed_phrases(self) -> list[str]:
        out = [self.announce_text, self.end_text]
        for c in self.colors.values():
            out += [c["consigne"], *c["reserve_simplifier"], *c["reserve_indice"]]
        return out


# ================================================================================================
# PARTIE 3 — LES CARTES DE L'ÉCRAN D'ACCUEIL
# Catalogue of the educational games shown as cards on the home screen.
#
# Adding a game = writing the Activity (see base.py) and registering ONE entry here:
#
#     CATALOG.register(CatalogEntry(
#         id="formes", title="Les formes", description="Touche la bonne forme.",
#         icon="formes", color="accent2", factory=ShapeActivity))
#
# The card appears by itself on the home screen (after the cards already there, so they
# never move: FC1); the adult can hide it or change the order (FP4).
#
# `icon` is either the name of a drawn illustration (display/icons.py, e.g. "ballons") or
# the path of a PNG; unknown names get a simple round badge with the first letter.
# `color` is a palette token (accent1, accent2, accent3), never a free colour (FC2).
# ================================================================================================

# Not too many cards for the child: the adult can show at most this many (FP4, FC2).
MAX_VISIBLE = 4


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    title: str  # card title, e.g. "Les couleurs"
    description: str  # short sentence said by the character (card's speaker icon)
    icon: str  # drawn illustration name or PNG path
    color: str  # card colour: palette token
    factory: Callable[[], Activity]
    announce: str = ""  # said when the card is touched (default: "On va jouer avec ...")

    @property
    def announce_text(self) -> str:
        if self.announce:
            return self.announce
        title = self.title[0].lower() + self.title[1:]
        return f"On va jouer avec {title}."


class Catalog:
    def __init__(self, entries: Iterable[CatalogEntry] = ()) -> None:
        self._entries: dict[str, CatalogEntry] = {}
        for e in entries:
            self.register(e)

    def register(self, entry: CatalogEntry) -> None:
        if entry.id in self._entries:
            raise ValueError(f"activité déjà enregistrée : {entry.id}")
        self._entries[entry.id] = entry

    def __contains__(self, activity_id: object) -> bool:
        return activity_id in self._entries

    def get(self, activity_id: str) -> CatalogEntry:
        return self._entries[activity_id]

    def entries(self) -> list[CatalogEntry]:
        """All registered games, in registration order."""
        return list(self._entries.values())

    def ordered_ids(self, order: list[str], hidden: list[str]) -> list[str]:
        """Adult's order first, then games registered later (appended at the end, so the
        cards already on screen keep their place). Unknown ids are ignored."""
        known = [i for i in order if i in self._entries]
        new = [i for i in self._entries if i not in known and i not in hidden]
        return known + new

    def visible(self, order: list[str], hidden: list[str],
                limit: int = MAX_VISIBLE) -> list[CatalogEntry]:
        """Cards on the home screen: adult's choice, at most `limit`, never empty."""
        ids = [i for i in self.ordered_ids(order, hidden) if i not in hidden][:limit]
        if not ids and self._entries:
            ids = [next(iter(self._entries))]
        return [self._entries[i] for i in ids]


CATALOG = Catalog([
    CatalogEntry(
        id="couleurs", title="Les couleurs",
        description="Touche le ballon de la bonne couleur.",
        icon="ballons", color="accent1", factory=ColorActivity,
    ),
])


# ================================================================================================
# PARTIE 4 — PRÉPARER LES JEUX CHOISIS
# ================================================================================================

# id -> factory, derived from the catalogue (one place to register a game)
REGISTRY = {e.id: e.factory for e in CATALOG.entries()}


def build_activities(ids: list[str]) -> list[Activity]:
    acts = [CATALOG.get(i).factory() for i in ids if i in CATALOG]
    return acts or [ColorActivity()]
