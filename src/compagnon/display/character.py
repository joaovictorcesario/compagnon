"""The character, behind a small interface so it can be replaced by a custom one.

Two implementations:
* GeometricCharacter: the current drawn face (default);
* SpriteCharacter: one image per expression from a folder, for the team's own artwork:
      <dossier>/neutre.png  content.png  encourage.png  calme.png
  Missing expressions fall back to neutre.png. Transparent PNG, square, any size (scaled).
The robot (S8) can reuse the same images on its small face screen.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

import pygame

from compagnon.display.base import EXPRESSIONS
from compagnon.display.drawing import draw_character

SPRITE_EXT = (".png", ".jpg", ".jpeg", ".bmp")


class Character(Protocol):
    def draw(self, surf: pygame.Surface, center: tuple[int, int], radius: int,
             expression: str, pal: dict, t: float, animate: bool) -> None: ...


class GeometricCharacter:
    def draw(self, surf: pygame.Surface, center: tuple[int, int], radius: int,
             expression: str, pal: dict, t: float, animate: bool) -> None:
        draw_character(surf, center, radius, expression, pal, t, animate)


class SpriteCharacter:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.images: dict[str, pygame.Surface] = {}
        for expr in EXPRESSIONS:
            for ext in SPRITE_EXT:
                p = folder / f"{expr}{ext}"
                if p.exists():
                    self.images[expr] = pygame.image.load(str(p))
                    break
        if "neutre" not in self.images:
            raise FileNotFoundError(f"{folder / 'neutre.png'} manquant")
        self._scaled: dict[tuple[str, int], pygame.Surface] = {}

    def draw(self, surf: pygame.Surface, center: tuple[int, int], radius: int,
             expression: str, pal: dict, t: float, animate: bool) -> None:
        expr = expression if expression in self.images else "neutre"
        size = 2 * radius
        if animate:  # same slow 'breathing' as the drawn character, never blinking
            size = int(size * (1.0 + 0.02 * math.sin(t * 1.2)))
        key = (expr, size)
        if key not in self._scaled:
            if len(self._scaled) > 64:
                self._scaled.clear()
            img = self.images[expr]
            scale = size / max(img.get_width(), img.get_height())
            w = max(1, int(img.get_width() * scale))
            h = max(1, int(img.get_height() * scale))
            self._scaled[key] = pygame.transform.smoothscale(img, (w, h))
        sprite = self._scaled[key]
        surf.blit(sprite, sprite.get_rect(center=center))


def load_character(folder: Path | None) -> Character:
    """Custom sprites if the folder has at least neutre.png, otherwise the drawn face."""
    if folder is not None and folder.is_dir():
        try:
            return SpriteCharacter(folder)
        except (FileNotFoundError, pygame.error) as exc:
            print(f"[personnage] {exc} : personnage dessiné par défaut")
    return GeometricCharacter()
