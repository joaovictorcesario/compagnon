"""Original, simple drawings made of geometric shapes (no image files, no emoji)."""

from __future__ import annotations

import math

import pygame

Color = tuple[int, int, int]


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
