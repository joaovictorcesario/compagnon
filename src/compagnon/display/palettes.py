"""Soft palettes, dark text on light background (FC2)."""

from __future__ import annotations

_BASE = {
    "text": (40, 42, 52),
    "soft_text": (110, 112, 122),
    "outline": (70, 72, 82),
    "bubble": (255, 255, 255),
    "btn_text": (40, 42, 52),
    "star": (245, 205, 90),
    "mystery": (150, 152, 160),
    "adult_dot": (226, 222, 214),
}

PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "sable": {**_BASE, "bg": (250, 246, 238), "header": (238, 230, 214), "char": (243, 196, 140),
              "cheek": (238, 168, 150), "aide": (206, 224, 244), "pause": (246, 234, 200),
              "fini": (214, 234, 212), "panel": (255, 252, 246)},
    "ciel": {**_BASE, "bg": (238, 244, 250), "header": (220, 232, 244), "char": (160, 196, 232),
             "cheek": (232, 170, 176), "aide": (206, 224, 244), "pause": (240, 234, 210),
             "fini": (214, 234, 222), "panel": (250, 252, 255)},
    "menthe": {**_BASE, "bg": (236, 246, 240), "header": (216, 236, 224), "char": (156, 208, 176),
               "cheek": (232, 176, 166), "aide": (210, 226, 240), "pause": (242, 236, 206),
               "fini": (206, 232, 214), "panel": (250, 255, 252)},
}

# Calm screen (overload / pause): everything a bit greyer and quieter.
CALM_OVERRIDE = {"bg": (232, 234, 238), "header": (222, 224, 230), "char": (200, 204, 214),
                 "cheek": (214, 200, 204)}

FONT_SIZES = {  # (instruction, buttons, title)
    "petit": (26, 26, 28),
    "moyen": (32, 30, 32),
    "grand": (40, 34, 36),
}


def palette(name: str, calm: bool) -> dict[str, tuple[int, int, int]]:
    pal = dict(PALETTES.get(name, PALETTES["sable"]))
    if calm:
        pal.update(CALM_OVERRIDE)
    return pal
