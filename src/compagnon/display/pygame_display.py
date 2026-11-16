"""Computer-screen implementation of the Display interface (S7).

Fixed layout (FC1): title on top, character on the left, instruction bubble with the
drawn speaker icon, picture on the right, answer balloons in the middle, and the three
fixed buttons "Aide", "Pause", "J'ai fini" at the bottom of EVERY child screen (FC3).
Adult mode: long press (3 s) on the discreet dot in the top-right corner.
"""

from __future__ import annotations

import time
from pathlib import Path

import pygame

from compagnon.companion.mode import CompanionMode
from compagnon.core.events import InputEvent, Kind
from compagnon.core.settings import Settings
from compagnon.display.base import RewardView, Scene
from compagnon.display.character import Character, GeometricCharacter
from compagnon.display.companion_screen import CompanionScreen
from compagnon.display.drawing import (
    blit_center,
    draw_balloon,
    draw_mystery_balloon,
    draw_speaker,
    draw_star,
    rounded_rect,
    wrap_text,
)
from compagnon.display.palettes import FONT_SIZES, palette

W, H = 1024, 720
ADULT_CORNER = pygame.Rect(W - 56, 0, 56, 56)
LONG_PRESS_S = 3.0
EMPHASIS_S = 1.5
FONT_NAMES = "verdana,dejavusans,arial"


def make_font(size: int, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont(FONT_NAMES, size, bold=bold)


class PygameDisplay:
    def __init__(self, settings: Settings, companion: CompanionMode | None = None,
                 fullscreen: bool = False, rewards_dir: Path | None = None,
                 character: Character | None = None) -> None:
        pygame.init()
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else 0)
        self.screen = pygame.display.set_mode((W, H), flags)
        pygame.display.set_caption("Compagnon")
        self.companion = companion
        self.companion_ui = CompanionScreen(companion) if companion else None
        self.rewards_dir = rewards_dir
        self.mode = "vide"
        self.title = ""
        self.text = ""
        self.scene: Scene | None = None
        self.expression = "neutre"
        self.reward: RewardView | None = None
        self.calm = False
        self.character = character or GeometricCharacter()
        self._emphasis_until = 0.0
        self._targets: list[tuple[pygame.Rect, InputEvent]] = []
        self._press_start: float | None = None
        self._t0 = time.monotonic()
        self._images: dict[str, pygame.Surface | None] = {}
        self.apply_settings(settings)

    # ------------------------------------------------------------ Display interface
    def apply_settings(self, settings: Settings) -> None:
        self.settings = settings
        text, btn, title = FONT_SIZES.get(settings.text_size, FONT_SIZES["moyen"])
        self.f_text = make_font(text)
        self.f_btn = make_font(btn, bold=True)
        self.f_title = make_font(title, bold=True)
        self.f_big = make_font(64, bold=True)

    def announce_activity(self, title: str, text: str) -> None:
        self.mode, self.title, self.text = "annonce", title, text
        self.expression, self.reward = "content", None

    def show_scene(self, scene: Scene) -> None:
        self.mode, self.scene, self.title = "scene", scene, scene.title
        self.text, self.expression, self.reward = scene.text, scene.expression, None

    def set_expression(self, expression: str) -> None:
        self.expression = expression

    def show_reward(self, reward: RewardView) -> None:
        self.reward = reward

    def propose_pause(self, text: str) -> None:
        self.mode, self.text, self.expression = "pause_proposee", text, "calme"

    def show_pause(self, text: str) -> None:
        self.mode, self.text, self.expression = "pause", text, "calme"

    def emphasize_instruction(self) -> None:
        """Instruction said again: the bubble turns soft blue for 1.5 s (steady, no blinking),
        so a repeat is also visible, not only audible."""
        self._emphasis_until = time.monotonic() + EMPHASIS_S

    def set_calm(self, calm: bool) -> None:
        self.calm = calm

    def show_end(self, text: str) -> None:
        self.mode, self.text, self.reward = "fin", text, None

    def poll_events(self) -> list[InputEvent]:
        out: list[InputEvent] = []
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                out.append(InputEvent(Kind.QUIT))
                continue
            if self.companion_ui is not None and self.companion_ui.active:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    out += self.companion_ui.click(e.pos)
                elif e.type == pygame.KEYDOWN:
                    out += self.companion_ui.key(e)
                continue
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.companion_ui is not None and ADULT_CORNER.collidepoint(e.pos):
                    self._press_start = time.monotonic()
                    continue
                out.append(self._hit(e.pos))
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self._press_start:
                self._press_start = None
                out.append(InputEvent(Kind.BACKGROUND))
        if (self._press_start is not None and self.companion_ui is not None
                and time.monotonic() - self._press_start >= LONG_PRESS_S):
            self._press_start = None
            self.companion_ui.open()
            out.append(InputEvent(Kind.ADULT_OPEN))
        return out

    # ------------------------------------------------------------ drawing
    def _hit(self, pos: tuple[int, int]) -> InputEvent:
        for rect, ev in reversed(self._targets):
            if rect.collidepoint(pos):
                return ev
        return InputEvent(Kind.BACKGROUND)

    def render(self) -> None:
        t = time.monotonic() - self._t0
        pal = palette(self.settings.palette, self.calm)
        if self.companion_ui is not None and self.companion_ui.active:
            self.companion_ui.render(self.screen, palette(self.settings.palette, False))
            pygame.display.flip()
            return
        animate = self.settings.animations and not self.calm
        targets: list[tuple[pygame.Rect, InputEvent]] = []
        s = self.screen
        s.fill(pal["bg"])
        pygame.draw.rect(s, pal["header"], pygame.Rect(0, 0, W, 64))
        blit_center(s, self.f_title, self.title, pal["text"], (W // 2, 32))

        if self.mode == "scene" and self.scene is not None:
            self._render_scene(s, pal, t, animate, targets)
        elif self.mode == "annonce":
            self.character.draw(s, (W // 2, 230), 95, "content", pal, t, animate)
            self._center_text(s, pal, self.text, 400, self.f_title)
        elif self.mode == "pause_proposee":
            self.character.draw(s, (W // 2, 200), 85, "calme", pal, t, False)
            self._center_text(s, pal, self.text, 330, self.f_title)
            offer = (("Pause", Kind.PAUSE), ("Continuer", Kind.CONTINUE))
            for i, (label, kind) in enumerate(offer):
                r = pygame.Rect(W // 2 - 270 + i * 290, 400, 250, 110)
                rounded_rect(s, pal["pause"] if i == 0 else pal["fini"], r, 24, pal["outline"])
                blit_center(s, self.f_title, label, pal["btn_text"], r.center)
                targets.append((r, InputEvent(kind)))
        elif self.mode == "pause":
            self.character.draw(s, (W // 2, 200), 85, "calme", pal, t, False)
            self._center_text(s, pal, self.text, 330, self.f_title)
            r = pygame.Rect(W // 2 - 150, 400, 300, 110)
            rounded_rect(s, pal["fini"], r, 24, pal["outline"])
            blit_center(s, self.f_title, "Reprendre", pal["btn_text"], r.center)
            targets.append((r, InputEvent(Kind.CONTINUE)))
        elif self.mode == "fin":
            self.character.draw(s, (W // 2, 230), 95, self.expression, pal, t, animate)
            self._center_text(s, pal, self.text, 400, self.f_title)

        self._render_fixed_buttons(s, pal, targets)
        if self.companion_ui is not None:
            pygame.draw.circle(s, pal["adult_dot"], (W - 20, 20), 8)
        pygame.display.flip()
        self._targets = targets

    def _center_text(self, s: pygame.Surface, pal: dict, text: str, y: int,
                     font: pygame.font.Font) -> None:
        for i, line in enumerate(wrap_text(font, text, W - 160)):
            blit_center(s, font, line, pal["text"], (W // 2, y + i * (font.get_height() + 6)))

    def _render_scene(self, s: pygame.Surface, pal: dict, t: float, animate: bool,
                      targets: list) -> None:
        scene = self.scene
        assert scene is not None
        self.character.draw(s, (150, 200), 80, self.expression, pal, t, animate)
        bubble = pygame.Rect(262, 90, 510, 170)
        emphasized = time.monotonic() < self._emphasis_until
        bubble_color = pal["aide"] if emphasized else pal["bubble"]
        pygame.draw.polygon(s, bubble_color, [(236, 200), (266, 180), (266, 220)])
        rounded_rect(s, bubble_color, bubble, 24, pal["outline"], 5 if emphasized else 3)
        lines = wrap_text(self.f_text, scene.text, bubble.width - 40)
        lh = self.f_text.get_height() + 4
        y0 = bubble.centery - (len(lines) * lh) // 2 + lh // 2
        for i, line in enumerate(lines):
            blit_center(s, self.f_text, line, pal["text"], (bubble.centerx, y0 + i * lh))
        speaker = pygame.Rect(786, 143, 64, 64)
        draw_speaker(s, speaker, pal)
        targets.append((speaker.inflate(16, 16), InputEvent(Kind.REPEAT)))
        image_slot = pygame.Rect(862, 80, 140, 200)
        if self.reward is None:
            draw_mystery_balloon(s, image_slot, pal, self.f_big)
        else:  # the reward takes the place of the instruction picture, never covers a choice
            img = self._reward_image(self.reward)
            if img is not None:
                s.blit(img, img.get_rect(center=image_slot.center))
            else:
                draw_star(s, image_slot.center, 58, pal["star"], pal["outline"])

        n = len(scene.choices)
        spacing = (W - 120) / max(1, n)
        r = int(min(68, spacing * 0.32))
        for i, choice in enumerate(scene.choices):
            cx = int(60 + spacing * (i + 0.5))
            hit = draw_balloon(s, (cx, 405), r, choice.rgb, pal["outline"],
                               highlight=(choice.id == scene.highlight))
            targets.append((hit, InputEvent(Kind.CHOICE, choice.id)))

    def _reward_image(self, reward: RewardView) -> pygame.Surface | None:
        if reward.kind != "image" or not reward.image_path or self.rewards_dir is None:
            return None
        key = reward.image_path
        if key not in self._images:
            try:
                img = pygame.image.load(str(self.rewards_dir / key)).convert_alpha()
                scale = 120 / max(img.get_width(), img.get_height())
                self._images[key] = pygame.transform.smoothscale(
                    img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            except (pygame.error, FileNotFoundError):
                self._images[key] = None
        return self._images[key]

    def _render_fixed_buttons(self, s: pygame.Surface, pal: dict, targets: list) -> None:
        buttons = (("Aide", Kind.HELP, "aide"), ("Pause", Kind.PAUSE, "pause"),
                   ("J'ai fini", Kind.FINISHED, "fini"))
        for i, (label, kind, color) in enumerate(buttons):
            r = pygame.Rect(40 + i * 330, H - 104, 284, 84)
            rounded_rect(s, pal[color], r, 22, pal["outline"])
            blit_center(s, self.f_btn, label, pal["btn_text"], r.center)
            targets.append((r, InputEvent(kind)))
