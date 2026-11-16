"""Outils de dessin : mise à l'échelle, formes, icônes, personnage.

Sommaire (chercher « PARTIE n ») :
  1. Mise à l'échelle de la fenêtre
  2. Dessins simples
  3. Formes et icônes
  4. Le personnage
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import pygame
import pygame.gfxdraw

from compagnon.apparence import LINE, LOGICAL_H, LOGICAL_W, SHADOW, Color, font_path, mix
from compagnon.seance import EXPRESSIONS

# ================================================================================================
# PARTIE 1 — MISE À L'ÉCHELLE DE LA FENÊTRE
# Proportional scaling. Every child screen is laid out on a 1280x720 logical canvas;
# View converts logical coordinates to the real window (any size, letterboxed when the
# aspect ratio differs), so the drawing stays sharp at 1280x720 as well as 1920x1080.
# ================================================================================================

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


# ================================================================================================
# PARTIE 2 — DESSINS SIMPLES
# Original, simple drawings made of geometric shapes (no image files, no emoji).
# ================================================================================================



def rounded_rect(surf: pygame.Surface, color: Color, rect: pygame.Rect, radius: int = 18,
                 border: Color | None = None, width: int = 3) -> None:
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surf, border, rect, width, border_radius=radius)


def wrap_text(font: pygame.font.Font, text: str, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def blit_center(surf: pygame.Surface, font: pygame.font.Font, text: str, color: Color,
                center: tuple[int, int]) -> None:
    img = font.render(text, True, color)
    surf.blit(img, img.get_rect(center=center))


def draw_character(surf: pygame.Surface, center: tuple[int, int], r: int, expression: str,
                   pal: dict, t: float, animate: bool) -> None:
    """Round, friendly character. Slow 'breathing' only if animations are on. Never blinks."""
    cx, cy = center
    scale = 1.0 + (0.02 * math.sin(t * 1.2) if animate else 0.0)
    rr = int(r * scale)
    pygame.draw.circle(surf, pal["char"], (cx, cy), rr)
    pygame.draw.circle(surf, pal["outline"], (cx, cy), rr, 3)
    eye_dx, eye_y = int(rr * 0.36), cy - int(rr * 0.15)
    for ex in (cx - eye_dx, cx + eye_dx):
        if expression == "calme":
            rect = pygame.Rect(ex - 11, eye_y - 8, 22, 16)
            pygame.draw.arc(surf, pal["outline"], rect, math.pi, 2 * math.pi, 3)
        else:
            pygame.draw.ellipse(surf, pal["outline"], pygame.Rect(ex - 7, eye_y - 11, 14, 22))
            pygame.draw.circle(surf, (255, 255, 255), (ex + 2, eye_y - 5), 3)
    for chx in (cx - int(rr * 0.58), cx + int(rr * 0.58)):
        pygame.draw.circle(surf, pal["cheek"], (chx, cy + int(rr * 0.15)), int(rr * 0.12))
    if expression == "content":
        rect = pygame.Rect(cx - int(rr * 0.32), cy + int(rr * 0.02), int(rr * 0.64), int(rr * 0.5))
        pygame.draw.arc(surf, pal["outline"], rect, math.pi, 2 * math.pi, 4)
    elif expression in ("encourage", "calme"):
        rect = pygame.Rect(cx - int(rr * 0.2), cy + int(rr * 0.18), int(rr * 0.4), int(rr * 0.28))
        pygame.draw.arc(surf, pal["outline"], rect, math.pi, 2 * math.pi, 4)
    else:
        y = cy + int(rr * 0.38)
        pygame.draw.line(surf, pal["outline"], (cx - int(rr * 0.18), y),
                         (cx + int(rr * 0.18), y), 4)


def draw_balloon(surf: pygame.Surface, center: tuple[int, int], r: int, color: Color,
                 outline: Color, highlight: bool = False) -> pygame.Rect:
    cx, cy = center
    if highlight:
        r = int(r * 1.12)
    body = pygame.Rect(cx - r, cy - int(r * 1.15), 2 * r, int(2.3 * r))
    bottom = body.bottom
    pygame.draw.line(surf, outline, (cx, bottom + 6), (cx - 6, bottom + 30), 2)
    pygame.draw.line(surf, outline, (cx - 6, bottom + 30), (cx + 4, bottom + 55), 2)
    pygame.draw.polygon(surf, color, [(cx, bottom - 2), (cx - 8, bottom + 9), (cx + 8, bottom + 9)])
    pygame.draw.ellipse(surf, color, body)
    pygame.draw.ellipse(surf, outline, body, 7 if highlight else 3)
    shine = pygame.Rect(cx - int(r * 0.55), cy - int(r * 0.8), int(r * 0.35), int(r * 0.5))
    pygame.draw.ellipse(surf, _lighter(color), shine)
    return body.inflate(10, 70)


def draw_mystery_balloon(surf: pygame.Surface, rect: pygame.Rect, pal: dict,
                         font: pygame.font.Font) -> None:
    """Instruction picture: an empty balloon with a question mark ('which one?')."""
    r = min(rect.width, rect.height) // 3
    cx, cy = rect.centerx, rect.centery - 14
    body = pygame.Rect(cx - r, cy - int(r * 1.15), 2 * r, int(2.3 * r))
    pygame.draw.ellipse(surf, pal["panel"], body)
    pygame.draw.ellipse(surf, pal["mystery"], body, 4)
    pygame.draw.line(surf, pal["mystery"], (cx, body.bottom), (cx - 4, body.bottom + 26), 2)
    blit_center(surf, font, "?", pal["mystery"], (cx, cy))


def draw_speaker(surf: pygame.Surface, rect: pygame.Rect, pal: dict) -> None:
    """Drawn loudspeaker icon (pygame cannot render emoji)."""
    rounded_rect(surf, pal["panel"], rect, 14, pal["outline"], 3)
    x, y, h = rect.x, rect.y, rect.height
    s = h / 64
    body = pygame.Rect(x + int(12 * s), y + int(24 * s), int(10 * s), int(16 * s))
    pygame.draw.rect(surf, pal["outline"], body)
    pygame.draw.polygon(surf, pal["outline"], [
        (x + int(22 * s), y + int(24 * s)), (x + int(34 * s), y + int(13 * s)),
        (x + int(34 * s), y + int(51 * s)), (x + int(22 * s), y + int(40 * s)),
    ])
    for i, size in enumerate((14, 26)):
        arc = pygame.Rect(0, 0, int(size * s), int((size + 10) * s))
        arc.center = (x + int((36 + i * 2) * s), y + h // 2)
        pygame.draw.arc(surf, pal["outline"], arc, -math.pi / 3, math.pi / 3, 3)


def draw_star(surf: pygame.Surface, center: tuple[int, int], r: int, color: Color,
              outline: Color) -> None:
    cx, cy = center
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, outline, pts, 3)


def _lighter(c: Color) -> Color:
    return tuple(min(255, int(v + (255 - v) * 0.45)) for v in c)  # type: ignore[return-value]


# ================================================================================================
# PARTIE 3 — FORMES ET ICÔNES
# Drawing kit for the child screens: panels with light shadows, text, smooth shapes and
# the drawn pictograms (no emoji, no image files: original and simple, FC4).
#
# All functions take LOGICAL coordinates (1280x720 canvas) and a View that scales them.
# Smooth edges: pygame.gfxdraw anti-aliased ellipses and polygons.
# ================================================================================================

Point = tuple[float, float]


# ---------------------------------------------------------------- screen-space helpers
def aa_ellipse(surf: pygame.Surface, color: Color, center: tuple[int, int], rx: int,
               ry: int) -> None:
    cx, cy = center
    if rx < 1 or ry < 1:
        return
    pygame.gfxdraw.filled_ellipse(surf, cx, cy, rx, ry, color)
    pygame.gfxdraw.aaellipse(surf, cx, cy, rx, ry, color)


def aa_polygon(surf: pygame.Surface, color: Color, pts: Sequence[tuple[float, float]]) -> None:
    ipts = [(round(x), round(y)) for x, y in pts]
    if len(ipts) < 3:
        return
    pygame.gfxdraw.filled_polygon(surf, ipts, color)
    pygame.gfxdraw.aapolygon(surf, ipts, color)


def _arc_points(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float,
                n: int = 24) -> list[Point]:
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n),
             cy + ry * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def thick_arc(surf: pygame.Surface, color: Color, center: tuple[float, float], rx: float,
              ry: float, a0: float, a1: float, width: float) -> None:
    """Smooth thick arc (screen coords). Angles in radians, y pointing down."""
    cx, cy = center
    hw = width / 2
    outer = _arc_points(cx, cy, rx + hw, ry + hw, a0, a1)
    inner = _arc_points(cx, cy, max(0.5, rx - hw), max(0.5, ry - hw), a0, a1)
    aa_polygon(surf, color, outer + inner[::-1])
    for (x0, y0), (x1, y1) in ((outer[0], inner[0]), (outer[-1], inner[-1])):
        aa_ellipse(surf, color, (round((x0 + x1) / 2), round((y0 + y1) / 2)),
                   max(1, round(hw)), max(1, round(hw)))


def thick_line(surf: pygame.Surface, color: Color, pts: Sequence[Point], width: float) -> None:
    """Smooth polyline with round joints (screen coords)."""
    hw = width / 2
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d * hw, dx / d * hw
        aa_polygon(surf, color, [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                                 (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])
    for x, y in pts:
        aa_ellipse(surf, color, (round(x), round(y)), max(1, round(hw)), max(1, round(hw)))


def capsule(surf: pygame.Surface, color: Color, p0: Point, p1: Point, width: float) -> None:
    thick_line(surf, color, [p0, p1], width)


# ---------------------------------------------------------------- panels & text
def shadow(surf: pygame.Surface, v: View, rect: pygame.Rect, radius: int, pal: dict,
           strength: float = 1.0) -> None:
    """Light, soft shadow (three blurred layers) instead of a thick black outline."""
    r = v.rect(rect)
    off = v.s(SHADOW["offset"])
    layer = pygame.Surface((r.w + 4 * off, r.h + 4 * off), pygame.SRCALPHA)
    for i, a in enumerate((0.35, 0.25, 0.15)):
        grow = (i + 1) * off // 2
        box = pygame.Rect(2 * off - grow, 2 * off - grow + off, r.w + 2 * grow, r.h + 2 * grow)
        alpha = int(SHADOW["alpha"] * a * strength)
        pygame.draw.rect(layer, (*pal["shadow"], alpha), box,
                         border_radius=v.s(radius) + grow)
    surf.blit(layer, (r.x - 2 * off, r.y - 2 * off))


def panel(surf: pygame.Surface, v: View, rect: pygame.Rect, fill: Color, pal: dict,
          radius: int, border: Color | None = None, width: float = LINE,
          lifted: bool = True) -> pygame.Rect:
    if lifted:
        shadow(surf, v, rect, radius, pal)
    r = v.rect(rect)
    pygame.draw.rect(surf, fill, r, border_radius=v.s(radius))
    if border is not None:
        pygame.draw.rect(surf, border, r, v.s(width), border_radius=v.s(radius))
    return r


def text(surf: pygame.Surface, v: View, txt: str, size: int, color: Color,
         center: Point | None = None, topleft: Point | None = None,
         bold: bool = False) -> pygame.Rect:
    img = v.font(size, bold).render(txt, True, color)
    if center is not None:
        rect = img.get_rect(center=v.p(*center))
    else:
        rect = img.get_rect(topleft=v.p(*(topleft or (0, 0))))
    surf.blit(img, rect)
    return rect


def wrap(v: View, txt: str, size: int, width: float, bold: bool = False) -> list[str]:
    font = v.font(size, bold)
    limit = v.s(width)
    lines: list[str] = []
    current = ""
    for word in txt.split():
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= limit or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def text_block(surf: pygame.Surface, v: View, txt: str, size: int, color: Color,
               rect: pygame.Rect, bold: bool = False, line_gap: float = 1.18) -> None:
    """Wrapped, centred text inside a logical rect (shrinks if it would overflow)."""
    while True:
        lines = wrap(v, txt, size, rect.w, bold)
        lh = size * line_gap
        if len(lines) * lh <= rect.h or size <= 18:
            break
        size -= 2
    y0 = rect.centery - (len(lines) - 1) * lh / 2
    for i, line in enumerate(lines):
        text(surf, v, line, size, color, center=(rect.centerx, y0 + i * lh), bold=bold)


def speech_bubble(surf: pygame.Surface, v: View, rect: pygame.Rect, tail_to: Point,
                  fill: Color, pal: dict, border: Color | None = None,
                  border_w: float = LINE) -> None:
    """Rounded bubble whose tail points exactly at `tail_to` (the character's mouth)."""
    shadow(surf, v, rect, 30, pal)
    tx, ty = tail_to
    by = max(rect.top + 34, min(rect.bottom - 34, ty))
    if tx < rect.left:
        base = [(rect.left + 2, by - 18), (rect.left + 2, by + 18)]
    else:
        base = [(rect.right - 2, by - 18), (rect.right - 2, by + 18)]
    tail = [v.p(*base[0]), v.p(tx, ty), v.p(*base[1])]
    if border is not None:
        grow = border_w
        aa_polygon(surf, border, [v.p(base[0][0], base[0][1] - grow),
                                  v.p(tx - (grow if tx < rect.left else -grow), ty),
                                  v.p(base[1][0], base[1][1] + grow)])
    r = v.rect(rect)
    pygame.draw.rect(surf, fill, r, border_radius=v.s(30))
    if border is not None:
        pygame.draw.rect(surf, border, r, v.s(border_w), border_radius=v.s(30))
    aa_polygon(surf, fill, tail)


# ---------------------------------------------------------------- pictograms
def icon_house(surf: pygame.Surface, v: View, c: Point, size: float, color: Color) -> None:
    x, y = c
    s = size
    roof = [(x - 0.48 * s, y - 0.02 * s), (x, y - 0.44 * s), (x + 0.48 * s, y - 0.02 * s)]
    thick_line(surf, color, [v.p(*p) for p in roof], v.s(0.1 * s))
    body = v.r(x - 0.32 * s, y - 0.08 * s, 0.64 * s, 0.48 * s)
    pygame.draw.rect(surf, color, body, border_radius=v.s(0.06 * s))
    door = v.r(x - 0.09 * s, y + 0.14 * s, 0.18 * s, 0.26 * s)
    pygame.draw.rect(surf, (255, 255, 255), door, border_radius=v.s(0.06 * s))


def icon_hand(surf: pygame.Surface, v: View, c: Point, size: float, color: Color) -> None:
    """Raised open hand ("Aide": I raise my hand)."""
    x, y = c
    s = size
    palm = v.r(x - 0.24 * s, y - 0.06 * s, 0.46 * s, 0.44 * s)
    pygame.draw.rect(surf, color, palm, border_radius=v.s(0.16 * s))
    fw = v.s(0.115 * s)
    for dx, top in ((-0.17, -0.34), (-0.055, -0.44), (0.06, -0.42), (0.17, -0.3)):
        capsule(surf, color, v.p(x + dx * s, y + 0.02 * s), v.p(x + dx * s, y + top * s), fw)
    capsule(surf, color, v.p(x - 0.2 * s, y + 0.2 * s), v.p(x - 0.42 * s, y - 0.02 * s), fw)


def icon_pause(surf: pygame.Surface, v: View, c: Point, size: float, color: Color) -> None:
    x, y = c
    s = size
    for dx in (-0.15, 0.15):
        bar = v.r(x + dx * s - 0.085 * s, y - 0.32 * s, 0.17 * s, 0.64 * s)
        pygame.draw.rect(surf, color, bar, border_radius=v.s(0.07 * s))


def icon_check(surf: pygame.Surface, v: View, c: Point, size: float, color: Color) -> None:
    x, y = c
    s = size
    pts = [(x - 0.32 * s, y + 0.02 * s), (x - 0.08 * s, y + 0.26 * s), (x + 0.36 * s, y - 0.24 * s)]
    thick_line(surf, color, [v.p(*p) for p in pts], v.s(0.14 * s))


def icon_play(surf: pygame.Surface, v: View, c: Point, size: float, color: Color) -> None:
    x, y = c
    s = size
    pts = [(x - 0.2 * s, y - 0.3 * s), (x + 0.3 * s, y), (x - 0.2 * s, y + 0.3 * s)]
    thick_line(surf, color, [v.p(*p) for p in [*pts, pts[0]]], v.s(0.08 * s))
    aa_polygon(surf, color, [v.p(*p) for p in pts])


def icon_speaker(surf: pygame.Surface, v: View, c: Point, size: float, color: Color) -> None:
    x, y = c
    s = size
    body = [(x - 0.36 * s, y - 0.12 * s), (x - 0.2 * s, y - 0.12 * s), (x + 0.02 * s, y - 0.32 * s),
            (x + 0.02 * s, y + 0.32 * s), (x - 0.2 * s, y + 0.12 * s), (x - 0.36 * s, y + 0.12 * s)]
    aa_polygon(surf, color, [v.p(*p) for p in body])
    for rr in (0.16, 0.3):
        thick_arc(surf, color, v.p(x + 0.06 * s, y), v.s(rr * s), v.s(rr * s),
                  -math.pi / 3.2, math.pi / 3.2, v.s(0.06 * s))


def star_points(cx: float, cy: float, r: float, inner: float = 0.47) -> list[Point]:
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * inner
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def icon_star(surf: pygame.Surface, v: View, c: Point, size: float, pal: dict,
              filled: bool = True) -> None:
    pts = [v.p(*p) for p in star_points(c[0], c[1], size / 2)]
    if filled:
        thick_line(surf, pal["star_line"], [*pts, pts[0]], v.s(size * 0.07))
        aa_polygon(surf, pal["star"], pts)
    else:
        thick_line(surf, pal["line"], [*pts, pts[0]], v.s(size * 0.06))


def balloon(surf: pygame.Surface, v: View, c: Point, r: float, color: Color,
            string_len: float = 1.0, ring: Color | None = None, ring_w: float = 0,
            halo: Color | None = None) -> pygame.Rect:
    """Balloon with a soft border, a shine and a gently curved string. Returns its
    generous touch area (logical rect: body + string)."""
    x, y = c
    if halo is not None:  # steady soft yellow glow (help level 4), never blinking
        aa_ellipse(surf, mix(halo, (255, 255, 255), 0.45), v.p(x, y), v.s(r * 1.42),
                   v.s(r * 1.5))
        aa_ellipse(surf, halo, v.p(x, y), v.s(r * 1.3), v.s(r * 1.4))
    edge = mix(color, (60, 60, 70), 0.22)
    rx, ry = r, r * 1.16
    bottom = y + ry
    # string: soft S-curve
    pts = []
    for i in range(13):
        t = i / 12
        pts.append(v.p(x + math.sin(t * math.pi * 1.6) * r * 0.12,
                       bottom + 8 + t * r * 0.95 * string_len))
    thick_line(surf, mix(edge, (255, 255, 255), 0.25), pts, v.s(2.2))
    knot = [v.p(x, bottom - 3), v.p(x - r * 0.12, bottom + 10), v.p(x + r * 0.12, bottom + 10)]
    aa_polygon(surf, edge, knot)
    if ring is not None and ring_w:
        aa_ellipse(surf, ring, v.p(x, y), v.s(rx + ring_w + 2), v.s(ry + ring_w + 2))
        aa_ellipse(surf, (255, 255, 255), v.p(x, y), v.s(rx + 2), v.s(ry + 2))
    aa_ellipse(surf, edge, v.p(x, y), v.s(rx), v.s(ry))
    aa_ellipse(surf, color, v.p(x, y), v.s(rx - 2.5), v.s(ry - 2.5))
    shine_c = v.p(x - rx * 0.38, y - ry * 0.42)
    aa_ellipse(surf, mix(color, (255, 255, 255), 0.55), shine_c, v.s(rx * 0.16), v.s(ry * 0.22))
    return pygame.Rect(round(x - rx - 14), round(y - ry - 14), round(2 * rx + 28),
                       round(2 * ry + r * 0.95 * string_len + 34))


def icon_balloons(surf: pygame.Surface, v: View, c: Point, size: float, pal: dict) -> None:
    """Illustration of the colours game: three soft balloons."""
    x, y = c
    s = size
    colors = ((236, 140, 132), (132, 176, 226), (244, 210, 110))
    for (dx, dy), col in zip(((-0.26, 0.02), (0.26, 0.0), (0.0, -0.1)), colors, strict=True):
        balloon(surf, v, (x + dx * s, y + dy * s - 0.08 * s), 0.17 * s, col, string_len=1.1)


def icon_touch(surf: pygame.Surface, v: View, c: Point, size: float, pal: dict) -> None:
    """Action pictogram: a finger touching a balloon (does not reveal the colour)."""
    x, y = c
    s = size
    # neutral balloon on top (no colour: the pictogram shows the ACTION, not the answer)
    bc, br = (x, y - 0.25 * s), 0.15 * s
    balloon(surf, v, bc, br, pal["surface_alt"], string_len=0.0)
    # hand below, index finger pointing up and touching the balloon
    col = pal["text_soft"]
    tip = (x, y - 0.06 * s)
    capsule(surf, col, v.p(*tip), v.p(x, y + 0.14 * s), v.s(0.095 * s))  # index finger
    fist = v.r(x - 0.06 * s, y + 0.08 * s, 0.27 * s, 0.22 * s)
    pygame.draw.rect(surf, col, fist, border_radius=v.s(0.08 * s))
    for fx in (0.075, 0.15):  # folded fingers
        aa_ellipse(surf, col, v.p(x + fx * s, y + 0.1 * s), v.s(0.045 * s), v.s(0.045 * s))
    capsule(surf, col, v.p(x - 0.03 * s, y + 0.22 * s), v.p(x - 0.12 * s, y + 0.13 * s),
            v.s(0.075 * s))  # thumb
    for side in (-1, 1):  # small "touch" marks on both sides of the fingertip
        a0, a1 = (math.pi * 1.05, math.pi * 1.35) if side < 0 else (math.pi * 1.65, math.pi * 1.95)
        thick_arc(surf, pal["accent1_strong"], v.p(*tip), v.s(0.1 * s), v.s(0.1 * s),
                  a0, a1, v.s(0.022 * s))


def icon_badge(surf: pygame.Surface, v: View, c: Point, size: float, pal: dict,
               letter: str) -> None:
    aa_ellipse(surf, pal["surface"], v.p(*c), v.s(size * 0.36), v.s(size * 0.36))
    text(surf, v, letter.upper(), int(size * 0.4), pal["text"], center=c, bold=True)


_PNG_CACHE: dict[tuple[str, int], pygame.Surface | None] = {}


def icon_image(surf: pygame.Surface, v: View, c: Point, size: float, path: str) -> bool:
    key = (path, v.s(size))
    if key not in _PNG_CACHE:
        try:
            img = pygame.image.load(path).convert_alpha()
            k = key[1] / max(img.get_width(), img.get_height())
            _PNG_CACHE[key] = pygame.transform.smoothscale(
                img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
        except (pygame.error, FileNotFoundError):
            _PNG_CACHE[key] = None
    img = _PNG_CACHE[key]
    if img is None:
        return False
    surf.blit(img, img.get_rect(center=v.p(*c)))
    return True


def game_icon(surf: pygame.Surface, v: View, name: str, c: Point, size: float, pal: dict,
              title: str = "?") -> None:
    """Illustration of a game card: drawn name, PNG path, or a letter badge."""
    drawn = {"ballons": icon_balloons}
    if name in drawn:
        drawn[name](surf, v, c, size, pal)
    elif name.lower().endswith((".png", ".jpg")) and Path(name).exists() and icon_image(
            surf, v, c, size, name):
        return
    else:  # "Les formes" -> F (the noun, not the article)
        words = [w for w in title.replace("'", " ").split() if w.lower() not in
                 ("le", "la", "les", "l", "un", "une", "des")]
        icon_badge(surf, v, c, size, pal, (words[-1] if words else title or "?")[:1])


# ================================================================================================
# PARTIE 4 — LE PERSONNAGE
# The character, behind a small interface so it can be replaced by a custom one.
#
# Two implementations:
# * GeometricCharacter: "Pipo", an original round little creature with a sprout on its
#   head, drawn with simple shapes (default). Same drawing on every screen, menu included:
#   it is the child's friend.
# * SpriteCharacter: one image per expression from a folder, for the team's own artwork:
#       <dossier>/neutre.png  content.png  encourage.png  calme.png  ecoute.png
#   Missing expressions fall back to neutre.png. Transparent PNG, square, any size (scaled).
#   Optional parle.png: shown every other beat while the voice is speaking.
# The robot (S8) can reuse the same images on its small face screen.
#
# Expressions: neutre (gentle smile), content, encourage, calme (pause), ecoute (waiting
# for the child's answer). Animations (FC2, can be turned off): slow breathing (slight
# scale) and a mouth that opens and closes while speaking. Nothing ever blinks.
# ================================================================================================

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
