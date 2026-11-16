from compagnon.activities.base import Activity, Choice, ImageSpec, Item
from compagnon.activities.catalog import CATALOG, MAX_VISIBLE, Catalog, CatalogEntry
from compagnon.activities.colors import ColorActivity

# id -> factory, derived from the catalogue (one place to register a game)
REGISTRY = {e.id: e.factory for e in CATALOG.entries()}


def build_activities(ids: list[str]) -> list[Activity]:
    acts = [CATALOG.get(i).factory() for i in ids if i in CATALOG]
    return acts or [ColorActivity()]


__all__ = ["Activity", "Choice", "ImageSpec", "Item", "ColorActivity", "build_activities",
           "CATALOG", "Catalog", "CatalogEntry", "MAX_VISIBLE", "REGISTRY"]
