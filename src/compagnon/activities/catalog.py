"""Catalogue of the educational games shown as cards on the home screen.

Adding a game = writing the Activity (see base.py) and registering ONE entry here:

    CATALOG.register(CatalogEntry(
        id="formes", title="Les formes", description="Touche la bonne forme.",
        icon="formes", color="accent2", factory=ShapeActivity))

The card appears by itself on the home screen (after the cards already there, so they
never move: FC1); the adult can hide it or change the order (FP4).

`icon` is either the name of a drawn illustration (display/icons.py, e.g. "ballons") or
the path of a PNG; unknown names get a simple round badge with the first letter.
`color` is a palette token (accent1, accent2, accent3), never a free colour (FC2).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from compagnon.activities.base import Activity
from compagnon.activities.colors import ColorActivity

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
