"""Automatic screenshots of every screen (visual check of the design), headless.

    python -m compagnon.tools.captures                      # docs/captures/1280x720, 1920x1080
    python -m compagnon.tools.captures --tailles 1024x768 --sortie captures

The 4-card menu uses FICTITIOUS games, only for this check: they are never registered
in the application.
"""

from __future__ import annotations

import argparse
import os
import random
import tempfile
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from compagnon.activities import ColorActivity  # noqa: E402
from compagnon.activities.catalog import CATALOG, Catalog, CatalogEntry  # noqa: E402
from compagnon.child import ChildProfile, ProfileStore  # noqa: E402
from compagnon.companion import CompanionMode, PinStore  # noqa: E402
from compagnon.core import phrases  # noqa: E402
from compagnon.core.clock import FakeClock  # noqa: E402
from compagnon.core.settings import Settings, SettingsStore  # noqa: E402
from compagnon.display.base import RewardView, Scene  # noqa: E402
from compagnon.paths import DataPaths  # noqa: E402


def fake_catalog() -> Catalog:
    real = CATALOG.get("couleurs")
    return Catalog([
        real,
        CatalogEntry("formes", "Les formes", "Touche la bonne forme.", "formes", "accent2",
                     ColorActivity),
        CatalogEntry("animaux", "Les animaux", "Écoute et trouve l'animal.", "animaux",
                     "accent3", ColorActivity),
        CatalogEntry("emotions", "Les émotions", "Regarde les visages.", "emotions",
                     "accent1", ColorActivity),
    ])


def _scene(act: ColorActivity, difficulty: int, seed: int, **kw: object) -> Scene:
    item = act.make_item(difficulty, random.Random(seed))
    args = {"title": act.title, "text": item.instruction, "image": item.image,
            "choices": tuple(item.choices)}
    args.update(kw)
    if args.get("highlight") == "cible":
        args["highlight"] = item.key
    return Scene(**args)  # type: ignore[arg-type]


def capture_all(out: Path, sizes: list[tuple[int, int]]) -> list[Path]:
    from compagnon.display.pygame_display import PygameDisplay

    saved: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        paths = DataPaths(Path(tmp)).ensure()
        settings = Settings(animations=False)  # still images: no breathing offset
        fake = fake_catalog()
        comp = CompanionMode(paths=paths, settings_store=SettingsStore(paths.settings),
                             pin_store=PinStore(paths.pin),
                             profile_store=ProfileStore(paths.profiles),
                             profile=ChildProfile("demo"), clock=FakeClock(), catalog=fake)
        comp.settings = settings
        disp = PygameDisplay(settings, comp, rewards_dir=paths.rewards, size=sizes[0])
        act = ColorActivity()
        couleurs = CATALOG.get("couleurs")

        def shot(name: str, size: tuple[int, int]) -> None:
            disp.skip_transition()
            disp.render()
            disp.skip_transition()
            disp.render()
            folder = out / f"{size[0]}x{size[1]}"
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{name}.png"
            pygame.image.save(disp.screen, str(path))
            saved.append(path)

        for size in sizes:
            disp.resize(size)
            disp.calm = False
            disp.show_menu(CATALOG.entries())
            shot("01_menu_1_carte", size)
            disp.show_menu(fake.entries())
            shot("02_menu_4_cartes_fictives", size)

            disp.set_activity(couleurs)
            disp.announce_activity(act.title, act.announce_text)
            shot("03_roteiro", size)
            for n, (diff, seed) in ((2, (1, 3)), (4, (3, 5)), (6, (4, 8))):
                disp.show_scene(_scene(act, diff, seed))
                disp.rounds_done = 3
                shot(f"04_jeu_{n}_ballons", size)

            sc = _scene(act, 3, 5, text=phrases.VISUAL_HINT, highlight="cible",
                        expression="encourage")
            disp.show_scene(sc)
            disp.emphasize_instruction()
            shot("05_aide_niveau_4", size)

            sc = _scene(act, 3, 5)
            disp.show_scene(sc)
            disp._emphasis_until = 0.0
            target = sc.choices[1].id
            disp._choose(target)
            disp.show_reward(RewardView("etoile"))
            disp.set_expression("content")
            shot("06_bonne_reponse", size)

            disp.show_scene(_scene(act, 3, 6))
            disp.confirm_home = True
            shot("07_confirmation_maison", size)
            disp.confirm_home = False

            disp.set_calm(True)
            disp.propose_pause(phrases.PAUSE_OFFER)
            shot("08_pause_proposee", size)
            disp.show_pause(phrases.PAUSE)
            shot("09_pause", size)
            disp.set_calm(False)

            disp.stars = 7
            disp.show_end(act.end_text)
            shot("10_fin", size)

            disp.companion_ui.open()
            comp.unlock("1234")
            comp.toggle_game("emotions")  # one hidden game, to show both states
            disp.companion_ui.state, disp.companion_ui.tab = "menu", "jeux"
            shot("11_adulte_jeux", size)
            disp.companion_ui.tab = "reglages"
            shot("12_adulte_reglages", size)
            comp.toggle_game("emotions")
            disp.companion_ui.active = False
            comp.lock()
        pygame.quit()
    return saved


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Captures d'écran automatiques")
    p.add_argument("--sortie", type=Path, default=Path("docs/captures"))
    p.add_argument("--tailles", nargs="+", default=["1280x720", "1920x1080"])
    a = p.parse_args(argv)
    sizes = [tuple(int(x) for x in t.lower().split("x")) for t in a.tailles]
    for path in capture_all(a.sortie, sizes):  # type: ignore[arg-type]
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
