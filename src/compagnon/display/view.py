"""Proportional scaling. Every child screen is laid out on a 1280x720 logical canvas;
View converts logical coordinates to the real window (any size, letterboxed when the
aspect ratio differs), so the drawing stays sharp at 1280x720 as well as 1920x1080."""

from __future__ import annotations

import pygame

from compagnon.display.theme import LOGICAL_H, LOGICAL_W, font_path


class View:
    def __init__(self, size: tuple[int, int]) -> None:
        self._fonts: dict[tuple[int, bool], pygame.font.Font] = {}
        self.resize(size)

    def resize(self, size: tuple[int, int]) -> None:
        w, h = size
        self.size = (w, h)
        self.k = min(w / LOGICAL_W, h / LOGICAL_H)
        self.ox = (w - LOGICAL_W * self.k) / 2
        self.oy = (h - LOGICAL_H * self.k) / 2
        self._fonts.clear()

    # logical -> screen
    def s(self, v: float) -> int:
        return max(1, round(v * self.k))

    def p(self, x: float, y: float) -> tuple[int, int]:
        return round(self.ox + x * self.k), round(self.oy + y * self.k)

    def r(self, x: float, y: float, w: float, h: float) -> pygame.Rect:
        x0, y0 = self.p(x, y)
        x1, y1 = self.p(x + w, y + h)
        return pygame.Rect(x0, y0, x1 - x0, y1 - y0)

    def rect(self, rect: pygame.Rect) -> pygame.Rect:
        return self.r(rect.x, rect.y, rect.w, rect.h)

    # screen -> logical
    def to_logical(self, pos: tuple[int, int]) -> tuple[float, float]:
        return (pos[0] - self.ox) / self.k, (pos[1] - self.oy) / self.k

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (self.s(size), bold)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.Font(font_path(bold), key[0])
        return self._fonts[key]
