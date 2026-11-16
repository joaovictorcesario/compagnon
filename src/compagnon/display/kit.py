"""Drawing kit for the child screens: panels with light shadows, text, smooth shapes and
the drawn pictograms (no emoji, no image files: original and simple, FC4).

All functions take LOGICAL coordinates (1280x720 canvas) and a View that scales them.
Smooth edges: pygame.gfxdraw anti-aliased ellipses and polygons.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path

import pygame
import pygame.gfxdraw

from compagnon.display.theme import LINE, SHADOW, Color, mix
from compagnon.display.view import View

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
