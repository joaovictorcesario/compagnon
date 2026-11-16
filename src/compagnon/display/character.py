"""The character, behind a small interface so it can be replaced by a custom one.

Two implementations:
* GeometricCharacter: "Pipo", an original round little creature with a sprout on its
  head, drawn with simple shapes (default). Same drawing on every screen, menu included:
  it is the child's friend.
* SpriteCharacter: one image per expression from a folder, for the team's own artwork:
      <dossier>/neutre.png  content.png  encourage.png  calme.png  ecoute.png
  Missing expressions fall back to neutre.png. Transparent PNG, square, any size (scaled).
  Optional parle.png: shown every other beat while the voice is speaking.
The robot (S8) can reuse the same images on its small face screen.

Expressions: neutre (gentle smile), content, encourage, calme (pause), ecoute (waiting
for the child's answer). Animations (FC2, can be turned off): slow breathing (slight
scale) and a mouth that opens and closes while speaking. Nothing ever blinks.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

import pygame

from compagnon.display.base import EXPRESSIONS
from compagnon.display.kit import aa_ellipse, aa_polygon, thick_arc
from compagnon.display.theme import mix

SPRITE_EXT = (".png", ".jpg", ".jpeg", ".bmp")
BREATH_HZ = 0.18  # one slow breath every ~5.5 s
TALK_HZ = 3.2


def breathing(t: float, animate: bool) -> float:
    return 1.0 + (0.018 * math.sin(t * 2 * math.pi * BREATH_HZ) if animate else 0.0)


def mouth_open(t: float, speaking: bool, animate: bool) -> float:
    """0 = closed smile, up to 1 = open (only while the voice speaks)."""
    if not (speaking and animate):
        return 0.0
    return 0.35 + 0.65 * abs(math.sin(t * math.pi * TALK_HZ))


class Character(Protocol):
    def draw(self, surf: pygame.Surface, center: tuple[int, int], radius: int,
             expression: str, pal: dict, t: float, animate: bool,
             speaking: bool = False) -> None: ...


class GeometricCharacter:
    def draw(self, surf: pygame.Surface, center: tuple[int, int], radius: int,
             expression: str, pal: dict, t: float, animate: bool,
             speaking: bool = False) -> None:
        draw_pipo(surf, center, radius, expression, pal, t, animate, speaking)


def draw_pipo(surf: pygame.Surface, center: tuple[int, int], r: int, expression: str,
              pal: dict, t: float, animate: bool, speaking: bool) -> None:
    cx, cy = center
    b = breathing(t, animate)
    ink = pal["ink"]
    body, shade = pal["char"], pal["char_shade"]
    rx, ry = r, int(r * 0.98 * b)
    top = cy - ry

    # soft ground shadow
    sh = pygame.Surface((int(r * 1.8), max(2, int(r * 0.34))), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (*pal["shadow"], 22), sh.get_rect())
    surf.blit(sh, sh.get_rect(center=(cx, cy + int(r * 1.02))))
    # feet and arms
    for dx in (-0.42, 0.42):
        aa_ellipse(surf, shade, (cx + int(dx * r), cy + int(r * 0.9)), int(r * 0.24),
                   int(r * 0.13))
    for dx in (-1, 1):
        aa_ellipse(surf, shade, (cx + dx * int(r * 0.95), cy + int(r * 0.22)), int(r * 0.15),
                   int(r * 0.24))
    # sprout on the head: a short stem and two leaves
    base = (cx, top + int(r * 0.04))
    stem_top = (cx + int(r * 0.03), top - int(r * 0.2))
    aa_polygon(surf, pal["leaf"], [(base[0] - r * 0.025, base[1]), (stem_top[0] - r * 0.02,
               stem_top[1]), (stem_top[0] + r * 0.02, stem_top[1]), (base[0] + r * 0.025,
               base[1])])
    for ang in (-0.9, 0.9):
        leaf = []
        for side in (1, -1):  # two edges of the leaf
            steps = range(17) if side == 1 else range(16, -1, -1)
            for i in steps:
                px = side * math.sin(i / 16 * math.pi) * r * 0.1
                py = -i / 16 * r * 0.34
                leaf.append((stem_top[0] + px * math.cos(ang) - py * math.sin(ang),
                             stem_top[1] + px * math.sin(ang) + py * math.cos(ang)))
        aa_polygon(surf, pal["leaf"], leaf)
    # body
    aa_ellipse(surf, shade, (cx, cy), rx, ry)
    aa_ellipse(surf, body, (cx, cy - int(r * 0.03)), rx - max(2, r // 30), ry - max(2, r // 22))
    belly = mix(body, (255, 255, 255), 0.35)
    aa_ellipse(surf, belly, (cx, cy + int(r * 0.45)), int(r * 0.44), int(r * 0.3))

    eye_y = cy - int(r * 0.12)
    eye_dx = int(r * 0.33)
    look = int(r * 0.04) if expression == "ecoute" else 0
    for ex in (cx - eye_dx, cx + eye_dx):
        if expression == "content":  # happy closed eyes
            thick_arc(surf, ink, (ex, eye_y + int(r * 0.03)), r * 0.11, r * 0.09,
                      math.pi * 1.1, math.pi * 1.9, max(2, r * 0.05))
        elif expression == "calme":  # relaxed closed eyes
            thick_arc(surf, ink, (ex, eye_y - int(r * 0.02)), r * 0.1, r * 0.07,
                      math.pi * 0.1, math.pi * 0.9, max(2, r * 0.045))
        else:
            aa_ellipse(surf, ink, (ex + look, eye_y), max(2, int(r * 0.075)),
                       max(3, int(r * 0.11)))
            aa_ellipse(surf, (255, 255, 255),
                       (ex + look + int(r * 0.025), eye_y - int(r * 0.04)),
                       max(1, int(r * 0.025)), max(1, int(r * 0.025)))
        if expression == "encourage":  # raised eyebrows: "you can do it"
            thick_arc(surf, ink, (ex, eye_y - int(r * 0.2)), r * 0.09, r * 0.05,
                      math.pi * 1.15, math.pi * 1.85, max(2, r * 0.035))
    for chx in (cx - int(r * 0.56), cx + int(r * 0.56)):
        aa_ellipse(surf, pal["cheek"], (chx, cy + int(r * 0.1)), int(r * 0.11), int(r * 0.07))

    mouth_y = cy + int(r * 0.14)
    opening = mouth_open(t, speaking, animate)
    if opening > 0:
        h = int(r * (0.05 + 0.12 * opening))
        aa_ellipse(surf, ink, (cx, mouth_y + h // 2), int(r * 0.13), max(2, h))
        aa_ellipse(surf, pal["cheek"], (cx, mouth_y + h), int(r * 0.07), max(1, h // 2))
    elif expression == "content":  # big open smile
        pts = [(cx + math.cos(a) * r * 0.22, mouth_y - r * 0.02 + math.sin(a) * r * 0.2)
               for a in [i / 20 * math.pi for i in range(21)]]
        aa_polygon(surf, ink, pts)
        aa_ellipse(surf, pal["cheek"], (cx, mouth_y + int(r * 0.11)), int(r * 0.09),
                   int(r * 0.05))
    elif expression == "ecoute":  # small closed smile + "listening" marks
        thick_arc(surf, ink, (cx, mouth_y - int(r * 0.03)), r * 0.1, r * 0.07,
                  math.pi * 0.15, math.pi * 0.85, max(2, r * 0.045))
        for k, rr in enumerate((0.16, 0.27)):
            # on the far side from the speech bubble, so they never touch its tail
            thick_arc(surf, pal["accent1_strong"], (cx - int(r * 1.12), cy - int(r * 0.12)),
                      r * rr, r * rr, math.pi * 0.75, math.pi * 1.25,
                      max(2, r * (0.04 - k * 0.008)))
    else:  # neutre / encourage / calme: gentle smile (never a flat, sad-looking line)
        w = 0.17 if expression == "calme" else 0.2
        thick_arc(surf, ink, (cx, mouth_y - int(r * 0.05)), r * w, r * 0.11,
                  math.pi * 0.12, math.pi * 0.88, max(2, r * 0.05))


class SpriteCharacter:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.images: dict[str, pygame.Surface] = {}
        for expr in (*EXPRESSIONS, "parle"):
            for ext in SPRITE_EXT:
                p = folder / f"{expr}{ext}"
                if p.exists():
                    self.images[expr] = pygame.image.load(str(p))
                    break
        if "neutre" not in self.images:
            raise FileNotFoundError(f"{folder / 'neutre.png'} manquant")
        self._scaled: dict[tuple[str, int], pygame.Surface] = {}

    def draw(self, surf: pygame.Surface, center: tuple[int, int], radius: int,
             expression: str, pal: dict, t: float, animate: bool,
             speaking: bool = False) -> None:
        expr = expression if expression in self.images else "neutre"
        if "parle" in self.images and mouth_open(t, speaking, animate) > 0.7:
            expr = "parle"
        size = int(2 * radius * breathing(t, animate))
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
    """Custom sprites if the folder has at least neutre.png, otherwise the drawn one."""
    if folder is not None and folder.is_dir():
        try:
            return SpriteCharacter(folder)
        except (FileNotFoundError, pygame.error) as exc:
            print(f"[personnage] {exc} : personnage dessiné par défaut")
    return GeometricCharacter()
