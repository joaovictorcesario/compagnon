"""Design tokens: readable text (WCAG contrast >= 4.5:1) in every palette, calm included."""

from __future__ import annotations

import pytest

from compagnon.core.settings import SETTING_SPECS
from compagnon.display.theme import (
    CARD_COLORS,
    FONT_SIZES,
    PALETTES,
    TEXT_PAIRS,
    contrast,
    font_path,
    palette,
)


@pytest.mark.parametrize("calm", [False, True])
@pytest.mark.parametrize("name", list(PALETTES))
def test_text_contrast_at_least_4_5(name, calm):
    pal = palette(name, calm)
    for fg, bg in TEXT_PAIRS:
        ratio = contrast(pal[fg], pal[bg])
        assert ratio >= 4.5, f"{name} calm={calm}: {fg} sur {bg} = {ratio:.2f}"


def test_contrast_formula():
    assert contrast((0, 0, 0), (255, 255, 255)) == pytest.approx(21, rel=1e-3)
    assert contrast((10, 10, 10), (10, 10, 10)) == pytest.approx(1)


def test_adult_palettes_all_come_from_the_tokens():
    spec = next(s for s in SETTING_SPECS if s.key == "palette")
    assert set(spec.options) == set(PALETTES)
    keys = set(PALETTES["sable"])
    for name in PALETTES:
        assert set(PALETTES[name]) == keys
        for token in CARD_COLORS:
            assert token in PALETTES[name]


def test_bundled_font_is_present_offline():
    import os

    for bold in (False, True):
        assert os.path.getsize(font_path(bold)) > 100_000
    assert set(FONT_SIZES) == {"petit", "moyen", "grand"}
