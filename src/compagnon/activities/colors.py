"""Activity "Les couleurs": touch the balloon of the requested colour.

Difficulty = number of choices (2, 3, 4, 6), independent from the 5 help levels.
"""

from __future__ import annotations

import json
import random
from importlib import resources

from compagnon.activities.base import Choice, ImageSpec, Item


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
            text = resources.files("compagnon.content").joinpath("couleurs.json").read_text("utf-8")
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
