from compagnon.activities.base import Activity, Choice, ImageSpec, Item
from compagnon.activities.colors import ColorActivity

REGISTRY = {"couleurs": ColorActivity}


def build_activities(ids: list[str]) -> list[Activity]:
    acts = [REGISTRY[i]() for i in ids if i in REGISTRY]
    return acts or [ColorActivity()]


__all__ = ["Activity", "Choice", "ImageSpec", "Item", "ColorActivity", "build_activities"]
