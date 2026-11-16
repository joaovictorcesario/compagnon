"""Apparence : couleurs (palettes), tailles de texte, police."""

from __future__ import annotations

from pathlib import Path

# ================================================================================================
# PARTIE 1 — COULEURS, TAILLES DE TEXTE, POLICE
# Design tokens: the ONLY place where colours, sizes and the font are defined.
#
# "Beautiful" for these children = calm, clean and consistent (FC2): light warm backgrounds,
# dark text (contrast >= 4.5:1, checked by tests/test_theme.py), three soft accent colours,
# thin borders and light shadows instead of thick black outlines, one rounded font.
#
# The three palettes of the adult mode (sable, ciel, menthe) are built from the same token
# names, so every screen works with every palette. The calm screen (overload, pause)
# replaces a few tokens with greyer, quieter ones.
# ================================================================================================

Color = tuple[int, int, int]

# Logical canvas: every screen is designed in 1280x720 and scaled to the window.
LOGICAL_W, LOGICAL_H = 1280, 720

RADIUS = {"small": 14, "card": 28, "button": 26, "bubble": 30}
LINE = 2  # border width (logical px)
SHADOW = {"offset": 5, "alpha": 34}
FADE_S = 0.25  # screen transition (<= 300 ms, none when animations are off)

# One font: Andika (SIL Open Font License, see assets/fonts/OFL.txt), made for children
# learning to read. Bundled, so it works offline.
FONT_FILES = {False: "Andika-Regular.ttf", True: "Andika-Bold.ttf"}

FONT_SIZES = {  # text_size setting -> (instruction, buttons, title), logical px
    "petit": (30, 28, 32),
    "moyen": (36, 30, 38),
    "grand": (44, 34, 44),
}

_COMMON: dict[str, Color] = {
    "text": (44, 46, 56),
    "text_soft": (86, 88, 98),
    "ink": (62, 64, 76),  # eyes, icons
    "white": (255, 255, 255),
    "star": (246, 200, 92),
    "star_line": (200, 150, 60),
    "shadow": (90, 70, 50),
}

PALETTES: dict[str, dict[str, Color]] = {
    "sable": {
        **_COMMON,
        "bg": (250, 246, 238), "surface": (255, 253, 249), "surface_alt": (241, 234, 221),
        "line": (222, 212, 196),
        "accent1": (205, 225, 244), "accent1_strong": (96, 142, 190),
        "accent2": (248, 231, 190), "accent2_strong": (205, 160, 66),
        "accent3": (209, 234, 210), "accent3_strong": (98, 156, 108),
        "char": (247, 196, 150), "char_shade": (229, 168, 120), "cheek": (243, 160, 150),
        "leaf": (140, 190, 130),
    },
    "ciel": {
        **_COMMON,
        "bg": (239, 245, 251), "surface": (252, 254, 255), "surface_alt": (224, 234, 245),
        "line": (200, 214, 230),
        "accent1": (206, 226, 246), "accent1_strong": (90, 138, 192),
        "accent2": (246, 234, 204), "accent2_strong": (200, 158, 70),
        "accent3": (210, 236, 222), "accent3_strong": (90, 152, 118),
        "char": (170, 204, 236), "char_shade": (140, 178, 216), "cheek": (236, 170, 178),
        "leaf": (130, 186, 150),
    },
    "menthe": {
        **_COMMON,
        "bg": (237, 247, 241), "surface": (251, 255, 252), "surface_alt": (221, 238, 228),
        "line": (196, 220, 206),
        "accent1": (210, 228, 242), "accent1_strong": (92, 140, 186),
        "accent2": (244, 236, 206), "accent2_strong": (196, 156, 72),
        "accent3": (204, 234, 214), "accent3_strong": (84, 150, 108),
        "char": (164, 214, 184), "char_shade": (130, 188, 154), "cheek": (236, 176, 166),
        "leaf": (110, 170, 130),
    },
}

# Calm screen (overload / pause): greyer, quieter. Text tokens unchanged (contrast).
CALM: dict[str, Color] = {
    "bg": (234, 236, 241), "surface_alt": (224, 227, 234), "line": (206, 210, 220),
}
# The character keeps its own colours, only softened (it stays the same friend).
CALM_SOFTEN = ("char", "char_shade", "cheek", "leaf")
CALM_GREY: Color = (222, 224, 230)

CARD_COLORS = ("accent1", "accent2", "accent3")  # a game's card colour is one of these

# Names used by the adult screens (written before the tokens existed).
_ALIASES = {
    "panel": "surface", "bubble": "surface", "header": "surface_alt", "outline": "line",
    "soft_text": "text_soft", "btn_text": "text", "aide": "accent1", "pause": "accent2",
    "fini": "accent3", "mystery": "line", "adult_dot": "surface_alt",
}

# Every text/background pair used on screen (checked >= 4.5:1).
TEXT_PAIRS = (
    ("text", "bg"), ("text", "surface"), ("text", "surface_alt"), ("text", "accent1"),
    ("text", "accent2"), ("text", "accent3"), ("text_soft", "bg"), ("text_soft", "surface"),
    ("text_soft", "surface_alt"),
)


def palette(name: str, calm: bool = False) -> dict[str, Color]:
    pal = dict(PALETTES.get(name, PALETTES["sable"]))
    if calm:
        pal.update(CALM)
        for token in CALM_SOFTEN:
            pal[token] = mix(pal[token], CALM_GREY, 0.45)
    for alias, token in _ALIASES.items():
        pal[alias] = pal[token]
    return pal


def font_path(bold: bool = False) -> str:
    return str(Path(__file__).resolve().parent / "polices" / FONT_FILES[bold])


def _lum(c: Color) -> float:
    def ch(v: int) -> float:
        x = v / 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: Color, b: Color) -> float:
    """WCAG contrast ratio."""
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a: Color, b: Color, t: float) -> Color:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))  # type: ignore[return-value]
