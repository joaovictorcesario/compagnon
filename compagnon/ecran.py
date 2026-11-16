"""Les écrans de l'enfant : accueil, emploi du temps, jeu, pause, fin."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pygame

from compagnon import dessin as kit
from compagnon.adulte import CompanionMode, CompanionScreen
from compagnon.apparence import FADE_S, FONT_SIZES, LOGICAL_H, LOGICAL_W, RADIUS, mix, palette
from compagnon.dessin import Character, GeometricCharacter, View
from compagnon.jeux import CatalogEntry
from compagnon.reglages import InputEvent, Kind, Settings
from compagnon.seance import RewardView, Scene

# ================================================================================================
# PARTIE 1 — ÉCRANS DE L'ENFANT
# Computer-screen implementation of the Display interface (S7), plus the app screens.
#
# Screens (all laid out on a 1280x720 logical canvas, scaled to the window, see view.py):
# * menu      : the character says "Bonjour !", game cards below (from the catalogue);
# * annonce   : visual schedule "D'abord : le jeu -> Ensuite : une récompense -> Fin";
# * scene     : the game. Same layout every time (FC1): "Maison" top-left, title and
#               progress dots top-centre, small schedule top-right; character, speech
#               bubble, speaker icon, action pictogram; balloons; the three fixed buttons
#               Aide / Pause / J'ai fini with drawn pictograms (FC3, FC4);
# * pause_proposee, pause : calm screen, one clear choice;
# * fin       : "C'est fini pour aujourd'hui. Bravo !", stars earned, back to the menu.
# Adult mode: long press (3 s) on the top-right corner, on every screen.
#
# Calm by design (FC2): soft colours from theme.py, nothing blinks, short fades between
# screens (<= 300 ms) only when animations are on, no sound from the display.
# ================================================================================================

ADULT_CORNER = pygame.Rect(LOGICAL_W - 72, 0, 72, 72)  # logical
LONG_PRESS_S = 3.0
EMPHASIS_S = 1.5
SELECT_S = 1.4  # soft ring around the touched balloon
RISE_S = 1.6  # the right balloon floats up slowly
GREETING = "Bonjour !"
END_TITLE = "C'est fini pour aujourd'hui. Bravo !"

Action = Callable[[], list[InputEvent]]


def default_window_size() -> tuple[int, int]:
    """1280x720, smaller if the screen is smaller (keeps 16:9)."""
    try:
        info = pygame.display.Info()
        w = min(LOGICAL_W, int(info.current_w * 0.92)) if info.current_w > 0 else LOGICAL_W
    except pygame.error:
        w = LOGICAL_W
    return w, round(w * LOGICAL_H / LOGICAL_W)


class PygameDisplay:
    def __init__(self, settings: Settings, companion: CompanionMode | None = None,
                 fullscreen: bool = False, rewards_dir: Path | None = None,
                 character: Character | None = None,
                 size: tuple[int, int] | None = None,
                 speaking: Callable[[], bool] | None = None) -> None:
        pygame.init()
        self.fullscreen = fullscreen
        self._windowed_size = size or default_window_size()
        self._set_mode()
        pygame.display.set_caption("Compagnon")
        self.companion = companion
        self.companion_ui = CompanionScreen(companion) if companion else None
        self.rewards_dir = rewards_dir
        self.character = character or GeometricCharacter()
        self.speaking = speaking or (lambda: False)
        self.mode = "vide"
        self.title = ""
        self.text = ""
        self.scene: Scene | None = None
        self.expression = "neutre"
        self.reward: RewardView | None = None
        self.calm = False
        self.entries: list[CatalogEntry] = []
        self.current: CatalogEntry | None = None
        self.stars = 0
        self.rounds_done = 0
        self._round_counted = False
        self._selected: tuple[str, float] | None = None
        self._success: tuple[str, float] | None = None
        self.confirm_home = False
        self._emphasis_until = 0.0
        self._targets: list[tuple[pygame.Rect, Action, InputEvent | None]] = []
        self._press_start: float | None = None
        self._t0 = time.monotonic()
        self._images: dict[tuple[str, int], pygame.Surface | None] = {}
        self._screen_key: tuple | None = None
        self._fade_from: pygame.Surface | None = None
        self._fade_start = 0.0
        self.apply_settings(settings)

    # ------------------------------------------------------------ window
    def _set_mode(self, size: tuple[int, int] | None = None) -> None:
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(size or self._windowed_size,
                                                  pygame.RESIZABLE)
        if hasattr(self, "view"):
            self.view.resize(self.screen.get_size())
        else:
            self.view = View(self.screen.get_size())

    def resize(self, size: tuple[int, int]) -> None:
        """Proportional scaling of every screen (also used for the screenshots)."""
        self._windowed_size = size
        self._set_mode(size)
        self._screen_key = None

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self._set_mode()
        self._screen_key = None

    # ------------------------------------------------------------ app screens
    def show_menu(self, entries: list[CatalogEntry]) -> None:
        """Home screen: the cards chosen by the adult, always in the same order."""
        self.mode, self.entries, self.current = "menu", list(entries), None
        self.title, self.text, self.expression = "", GREETING, "neutre"
        self.calm, self.confirm_home, self.reward = False, False, None

    def set_activity(self, entry: CatalogEntry | None) -> None:
        self.current = entry

    # ------------------------------------------------------------ Display interface
    def apply_settings(self, settings: Settings) -> None:
        self.settings = settings
        self.size_text, self.size_btn, self.size_title = FONT_SIZES.get(
            settings.text_size, FONT_SIZES["moyen"])

    def announce_activity(self, title: str, text: str) -> None:
        self.mode, self.title, self.text = "annonce", title, text
        self.expression, self.reward = "content", None
        self.stars = self.rounds_done = 0
        self._round_counted = False
        self._selected = self._success = None
        self.confirm_home = False

    def show_scene(self, scene: Scene) -> None:
        if self._round_counted:  # previous round finished: this is the next question
            self._round_counted = False
            self._selected = self._success = None
        self.mode, self.scene, self.title = "scene", scene, scene.title
        self.text, self.expression, self.reward = scene.text, scene.expression, None

    def set_expression(self, expression: str) -> None:
        # The controller shows "content" during a question only for a right answer:
        # that is when the round counts and the touched balloon floats up.
        if expression == "content" and self.mode == "scene" and not self._round_counted:
            self._round_counted = True
            self.rounds_done += 1
            if self._selected is not None:
                self._success = (self._selected[0], time.monotonic())
        self.expression = expression

    def show_reward(self, reward: RewardView) -> None:
        self.reward = reward
        self.stars += 1

    def propose_pause(self, text: str) -> None:
        self.mode, self.text, self.expression = "pause_proposee", text, "calme"
        self.confirm_home = False

    def show_pause(self, text: str) -> None:
        self.mode, self.text, self.expression = "pause", text, "calme"
        self.confirm_home = False

    def emphasize_instruction(self) -> None:
        """Instruction said again: the bubble turns soft blue for 1.5 s (steady, no
        blinking), so a repeat is also visible, not only audible."""
        self._emphasis_until = time.monotonic() + EMPHASIS_S

    def set_calm(self, calm: bool) -> None:
        self.calm = calm

    def show_end(self, text: str) -> None:
        self.mode, self.text, self.reward = "fin", text, None
        self.confirm_home = False

    # ------------------------------------------------------------ input
    def poll_events(self) -> list[InputEvent]:
        out: list[InputEvent] = []
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                out.append(InputEvent(Kind.QUIT))
                continue
            if e.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.view.resize(self.screen.get_size())
                self._screen_key = None
                continue
            if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.toggle_fullscreen()
                continue
            if self.companion_ui is not None and self.companion_ui.active:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    out += self.companion_ui.click(self._companion_pos(e.pos))
                elif e.type == pygame.KEYDOWN:
                    out += self.companion_ui.key(e)
                continue
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                lx, ly = self.view.to_logical(e.pos)
                if self.companion_ui is not None and ADULT_CORNER.collidepoint(lx, ly):
                    self._press_start = time.monotonic()
                    continue
                out += self._hit(e.pos)
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self._press_start:
                self._press_start = None
                out.append(InputEvent(Kind.BACKGROUND))
        if (self._press_start is not None and self.companion_ui is not None
                and time.monotonic() - self._press_start >= LONG_PRESS_S):
            self._press_start = None
            self.companion_ui.open()
            out.append(InputEvent(Kind.ADULT_OPEN))
        return out

    def _hit(self, pos: tuple[int, int]) -> list[InputEvent]:
        for rect, action, _ev in reversed(self._targets):
            if rect.collidepoint(pos):
                return action()
        return [InputEvent(Kind.BACKGROUND)]

    def _companion_pos(self, pos: tuple[int, int]) -> tuple[int, int]:
        lx, ly = self.view.to_logical(pos)
        return int(lx), int(ly)

    def target_for(self, kind: Kind, value: str | None = None) -> pygame.Rect | None:
        """Screen rect that produces this event (used by tests and screenshots)."""
        for rect, _action, ev in self._targets:
            if ev is not None and ev.kind == kind and ev.value == value:
                return rect
        return None

    def _add(self, rect_logical: pygame.Rect, event: InputEvent | Action,
             grow: int = 0, produces: InputEvent | None = None) -> None:
        rect = self.view.rect(rect_logical.inflate(grow, grow))
        if isinstance(event, InputEvent):
            def action(ev: InputEvent = event) -> list[InputEvent]:
                return [ev]
            produces = event
        else:
            action = event
        self._targets.append((rect, action, produces))

    def _choose(self, choice_id: str) -> list[InputEvent]:
        self._selected = (choice_id, time.monotonic())
        return [InputEvent(Kind.CHOICE, choice_id)]

    def _ask_home(self) -> list[InputEvent]:
        self.confirm_home = True
        return []

    def _cancel_home(self) -> list[InputEvent]:
        self.confirm_home = False
        return []

    def _go_home(self) -> list[InputEvent]:
        self.confirm_home = False
        return [InputEvent(Kind.MENU)]

    def _start(self, entry: CatalogEntry) -> list[InputEvent]:
        self.current = entry
        return [InputEvent(Kind.START, entry.id)]

    # ------------------------------------------------------------ drawing
    def skip_transition(self) -> None:
        self._fade_from = None

    def render(self) -> None:
        now = time.monotonic()
        t = now - self._t0
        s = self.screen
        if self.companion_ui is not None and self.companion_ui.active:
            self._render_companion(s)
            pygame.display.flip()
            return
        calm = self.calm or self.mode in ("pause", "pause_proposee")
        pal = palette(self.settings.palette, calm)
        animate = self.settings.animations and not calm
        key = (self.mode, self.confirm_home, self.current.id if self.current else None)
        if key != self._screen_key:
            if self._screen_key is not None and self.settings.animations:
                self._fade_from = s.copy()
                self._fade_start = now
            self._screen_key = key
        self._targets = []
        s.fill(pal["bg"])
        draw = {
            "menu": self._render_menu, "annonce": self._render_schedule,
            "scene": self._render_scene, "pause_proposee": self._render_pause_offer,
            "pause": self._render_pause, "fin": self._render_end,
        }.get(self.mode)
        if draw is not None:
            draw(s, pal, t, animate)
        if self.confirm_home and self.mode == "scene":
            self._render_confirm_home(s, pal)
        if self.companion_ui is not None:  # discreet adult corner
            kit.aa_ellipse(s, mix(pal["bg"], pal["line"], 0.9), self.view.p(LOGICAL_W - 30, 30),
                           self.view.s(6), self.view.s(6))
        if self._fade_from is not None:
            k = (now - self._fade_start) / FADE_S
            if k >= 1:
                self._fade_from = None
            else:
                self._fade_from.set_alpha(int(255 * (1 - k)))
                s.blit(self._fade_from, (0, 0))
        pygame.display.flip()

    def _render_companion(self, s: pygame.Surface) -> None:
        pal = palette(self.settings.palette, False)
        logical = pygame.Surface((LOGICAL_W, LOGICAL_H))
        assert self.companion_ui is not None
        self.companion_ui.render(logical, pal)
        s.fill(pal["surface"])
        dest = self.view.r(0, 0, LOGICAL_W, LOGICAL_H)
        s.blit(pygame.transform.smoothscale(logical, dest.size), dest)

    # .................................................................. pieces
    def _char(self, s: pygame.Surface, pal: dict, center: tuple[float, float], r: float,
              expression: str, t: float, animate: bool) -> tuple[float, float]:
        """Draws the character; returns its mouth side (logical) for the bubble tail."""
        self.character.draw(s, self.view.p(*center), self.view.s(r), expression, pal, t,
                            animate, self.speaking())
        return center[0] + r * 1.08, center[1] + r * 0.16

    def _button(self, s: pygame.Surface, pal: dict, rect: pygame.Rect, label: str,
                icon: Callable | None, color: str, event: InputEvent | Action) -> None:
        v = self.view
        kit.panel(s, v, rect, pal[color], pal, RADIUS["button"])
        size = min(rect.h * 0.62, 58)
        label_w = v.font(self.size_btn, True).size(label)[0] / v.k
        total = (size + 18 if icon else 0) + label_w
        x0 = rect.centerx - total / 2
        if icon is not None:
            icon(s, v, (x0 + size / 2, rect.centery), size, pal["ink"])
            x0 += size + 18
        kit.text(s, v, label, self.size_btn, pal["text"],
                 center=(x0 + label_w / 2, rect.centery), bold=True)
        self._add(rect, event)

    def _title(self, s: pygame.Surface, pal: dict, text: str, y: float = 42) -> None:
        if text:
            kit.text(s, self.view, text, self.size_title, pal["text"], center=(LOGICAL_W / 2, y),
                     bold=True)

    def _steps(self) -> list[tuple[str, str, str]]:
        """Visual schedule built from the chosen game: (label, pictogram, caption)."""
        icon = self.current.icon if self.current else "ballons"
        steps = [("D'abord", icon, "le jeu")]
        if self.settings.reward != "aucune":
            steps.append(("Ensuite", "etoile", "une récompense"))
        steps.append(("Fin", "fin", ""))
        return steps

    def _step_icon(self, s: pygame.Surface, pal: dict, name: str, c: tuple[float, float],
                   size: float) -> None:
        v = self.view
        if name == "etoile":
            kit.icon_star(s, v, c, size * 0.95, pal)
        elif name == "fin":
            kit.icon_check(s, v, c, size * 0.8, pal["accent3_strong"])
        else:
            title = self.current.title if self.current else "?"
            kit.game_icon(s, v, name, c, size, pal, title)

    def _mini_schedule(self, s: pygame.Surface, pal: dict, current: int) -> None:
        """Small schedule at the top right of the game and end screens (FC1)."""
        v = self.view
        steps = self._steps()
        w, gap = 64, 10
        x = LOGICAL_W - 92 - len(steps) * (w + gap)
        for i, (_label, icon, _cap) in enumerate(steps):
            r = pygame.Rect(x + i * (w + gap), 14, w, 56)
            if i == current:
                kit.panel(s, v, r, pal["accent1"], pal, RADIUS["small"], pal["accent1_strong"], 3)
            else:
                kit.panel(s, v, r, pal["surface_alt"], pal, RADIUS["small"], lifted=False)
            self._step_icon(s, pal, icon, r.center, 40)
            if i < current:  # done: a soft veil over it
                veil = pygame.Surface(v.rect(r).size, pygame.SRCALPHA)
                veil.fill((*pal["surface_alt"], 120))
                s.blit(veil, v.rect(r))

    # .................................................................. menu
    def _render_menu(self, s: pygame.Surface, pal: dict, t: float, animate: bool) -> None:
        v = self.view
        mouth = self._char(s, pal, (470, 150), 84, "neutre", t, animate)
        bubble = pygame.Rect(600, 96, 300, 100)
        kit.speech_bubble(s, v, bubble, mouth, pal["surface"], pal)
        kit.text(s, v, GREETING, self.size_title + 4, pal["text"], center=bubble.center, bold=True)
        n = len(self.entries)
        if n == 0:
            return
        if n <= 4:
            w = 520 if n == 1 else min(400, (1180 - 30 * (n - 1)) / n)
            h = 400 if n == 1 else 390
            x0 = LOGICAL_W / 2 - (n * w + (n - 1) * 30) / 2
            rects = [pygame.Rect(round(x0 + i * (w + 30)), 282, round(w), h) for i in range(n)]
            horizontal = False
        else:
            cols, w, h = 3, 373, 195
            rects = []
            for i in range(n):
                row, col = divmod(i, cols)
                in_row = min(cols, n - row * cols)
                x0 = LOGICAL_W / 2 - (in_row * w + (in_row - 1) * 30) / 2
                rects.append(pygame.Rect(round(x0 + col * (w + 30)), 282 + row * (h + 22), w, h))
            horizontal = True
        for entry, rect in zip(self.entries, rects, strict=False):
            self._card(s, pal, entry, rect, horizontal)

    def _card(self, s: pygame.Surface, pal: dict, entry: CatalogEntry, rect: pygame.Rect,
              horizontal: bool) -> None:
        v = self.view
        color = pal.get(entry.color, pal["accent1"])
        strong = pal.get(entry.color + "_strong", pal["accent1_strong"])
        kit.panel(s, v, rect, pal["surface"], pal, RADIUS["card"])
        self._add(rect, lambda e=entry: self._start(e), produces=InputEvent(Kind.START, entry.id))
        if horizontal:
            art = pygame.Rect(rect.x + 12, rect.y + 12, rect.h - 24, rect.h - 24)
            title_c = (art.right + (rect.right - art.right) / 2, rect.centery - 18)
            play_c = (rect.right - 46, rect.bottom - 42)
        else:
            art = pygame.Rect(rect.x + 14, rect.y + 14, rect.w - 28, round(rect.h * 0.68))
            title_c = (rect.centerx, art.bottom + (rect.bottom - art.bottom) / 2)
            play_c = (art.right - 40, art.bottom - 40)
        kit.panel(s, v, art, color, pal, RADIUS["card"] - 8, lifted=False)
        size = min(art.w, art.h) * 0.78
        kit.game_icon(s, v, entry.icon, (art.centerx, art.centery + size * 0.06), size, pal,
                      entry.title)
        title_size = self.size_title
        avail = (rect.right - art.right - 24) if horizontal else rect.w - 28
        while title_size > 22 and v.font(title_size, True).size(entry.title)[0] / v.k > avail:
            title_size -= 2
        kit.text(s, v, entry.title, title_size, pal["text"], center=title_c, bold=True)
        # play button (the whole card starts the game; this shows that it can)
        kit.aa_ellipse(s, strong, v.p(*play_c), v.s(30), v.s(30))
        kit.icon_play(s, v, (play_c[0] + 3, play_c[1]), 30, (255, 255, 255))
        # speaker: the character says what the game is about (FC4)
        sp = pygame.Rect(art.right - 66, art.y + 10, 56, 56)
        kit.panel(s, v, sp, pal["surface"], pal, 28, lifted=False)
        kit.icon_speaker(s, v, sp.center, 36, pal["ink"])
        self._add(sp, InputEvent(Kind.DESCRIBE, entry.id), grow=8)

    # .................................................................. schedule
    def _render_schedule(self, s: pygame.Surface, pal: dict, t: float, animate: bool) -> None:
        v = self.view
        self._title(s, pal, self.title)
        mouth = self._char(s, pal, (300, 236), 100, "content", t, animate)
        bubble = pygame.Rect(450, 166, 700, 140)
        kit.speech_bubble(s, v, bubble, mouth, pal["surface"], pal)
        kit.text_block(s, v, self.text, self.size_text, pal["text"], bubble.inflate(-48, -24))
        self._schedule_cards(s, pal, current=0, y=404)

    def _schedule_cards(self, s: pygame.Surface, pal: dict, current: int, y: int) -> None:
        v = self.view
        steps = self._steps()
        w, h, gap = 290, 236, 96
        x0 = LOGICAL_W / 2 - (len(steps) * w + (len(steps) - 1) * gap) / 2
        for i, (label, icon, caption) in enumerate(steps):
            r = pygame.Rect(round(x0 + i * (w + gap)), y, w, h)
            active = i == current
            kit.panel(s, v, r, pal["accent1"] if active else pal["surface"], pal, RADIUS["card"],
                      pal["accent1_strong"] if active else pal["line"], 4 if active else 2)
            kit.text(s, v, label, self.size_btn, pal["text"], center=(r.centerx, r.y + 36),
                     bold=True)
            self._step_icon(s, pal, icon, (r.centerx, r.y + (118 if caption else 136)), 104)
            if caption:
                kit.text(s, v, caption, self.size_btn - 4, pal["text"],
                         center=(r.centerx, r.bottom - 30))
            if i + 1 < len(steps):  # soft chevron between the cards
                cx, cy = r.right + gap / 2, r.centery
                kit.thick_line(s, pal["line"], [v.p(cx - 12, cy - 22), v.p(cx + 10, cy),
                                                v.p(cx - 12, cy + 22)], v.s(8))

    # .................................................................. game
    def _render_scene(self, s: pygame.Surface, pal: dict, t: float, animate: bool) -> None:
        scene = self.scene
        assert scene is not None
        v = self.view
        now = time.monotonic()
        # top bar: Maison (discreet), title + progress, small schedule
        home = pygame.Rect(22, 14, 64, 58)
        kit.panel(s, v, home, pal["surface"], pal, RADIUS["small"], pal["line"])
        kit.icon_house(s, v, home.center, 40, pal["text_soft"])
        self._add(home, self._ask_home, grow=8)
        self._title(s, pal, scene.title, 36)
        self._progress(s, pal)
        self._mini_schedule(s, pal, 0)

        expression = self.expression
        if expression == "neutre" and not self.speaking():
            expression = "ecoute"  # waiting for the child's answer
        mouth = self._char(s, pal, (160, 204), 78, expression, t, animate)
        bubble = pygame.Rect(282, 116, 680, 152)
        emphasized = now < self._emphasis_until
        kit.speech_bubble(s, v, bubble, mouth, pal["accent1"] if emphasized else pal["surface"],
                          pal, pal["accent1_strong"] if emphasized else None, 3)
        kit.text_block(s, v, scene.text, self.size_text, pal["text"], bubble.inflate(-48, -28))
        speaker = pygame.Rect(984, 148, 88, 88)
        kit.panel(s, v, speaker, pal["surface"], pal, RADIUS["small"] + 6)
        kit.icon_speaker(s, v, speaker.center, 56, pal["ink"])
        self._add(speaker, InputEvent(Kind.REPEAT), grow=16)

        slot = pygame.Rect(1094, 116, 162, 152)
        kit.panel(s, v, slot, pal["surface"], pal, RADIUS["card"])
        if self.reward is None:
            kit.icon_touch(s, v, (slot.centerx, slot.centery + 4), 146, pal)
        else:  # the reward takes the place of the pictogram, never covers a choice
            img = self._reward_image(self.reward)
            if img is not None:
                s.blit(img, img.get_rect(center=v.p(*slot.center)))
            else:
                kit.icon_star(s, v, slot.center, 112, pal)

        self._balloons(s, pal, scene, now, animate)
        buttons = (("Aide", kit.icon_hand, "accent1", Kind.HELP),
                   ("Pause", kit.icon_pause, "accent2", Kind.PAUSE),
                   ("J'ai fini", kit.icon_check, "accent3", Kind.FINISHED))
        for i, (label, icon, color, kind) in enumerate(buttons):
            r = pygame.Rect(40 + i * 414, 618, 372, 86)
            self._button(s, pal, r, label, icon, color, InputEvent(kind))

    def _progress(self, s: pygame.Surface, pal: dict) -> None:
        """Discreet dots under the title: how many rounds are done / left."""
        v = self.view
        n = max(1, self.settings.items_per_activity)
        gap = 22 if n <= 12 else 14
        x0 = LOGICAL_W / 2 - (n - 1) * gap / 2
        for i in range(n):
            c = v.p(x0 + i * gap, 78)
            if i < self.rounds_done:
                kit.aa_ellipse(s, pal["accent3_strong"], c, v.s(7), v.s(7))
            else:
                kit.aa_ellipse(s, pal["line"], c, v.s(7), v.s(7))
                kit.aa_ellipse(s, pal["bg"], c, v.s(4.5), v.s(4.5))

    def _balloons(self, s: pygame.Surface, pal: dict, scene: Scene, now: float,
                  animate: bool) -> None:
        n = len(scene.choices)
        spacing = 1180 / max(1, n)
        r = min(72.0, spacing * 0.31)
        cy = 443 - (8 + 0.95 * r) / 2  # the whole balloon + string block is centred
        for i, choice in enumerate(scene.choices):
            cx = 50 + spacing * (i + 0.5)
            dy, ring, halo = 0.0, None, None
            if self._success and self._success[0] == choice.id:
                k = min(1.0, (now - self._success[1]) / RISE_S) if animate else 1.0
                dy = -38 * (1 - (1 - k) ** 3)  # slow ease-out, stays clear of the bubble
                ring = pal["accent3_strong"]
            elif (self._selected and self._selected[0] == choice.id
                  and now - self._selected[1] < SELECT_S):
                ring = pal["accent1_strong"]
            highlighted = choice.id == scene.highlight
            if highlighted:
                halo = pal["star"]
            rr = r * (1.08 if highlighted else 1.0)
            hit = kit.balloon(s, self.view, (cx, cy + dy), rr, choice.rgb, ring=ring,
                              ring_w=5 if ring else 0, halo=halo)
            hit.width = max(hit.width, round(spacing) - 12)  # generous touch area
            hit.centerx = round(cx)
            hit.y = round(cy - 1.16 * r - 14)
            self._add(hit, lambda cid=choice.id: self._choose(cid),
                      produces=InputEvent(Kind.CHOICE, choice.id))

    def _render_confirm_home(self, s: pygame.Surface, pal: dict) -> None:
        """Simple confirmation with pictograms, so a stray touch does not leave."""
        v = self.view
        veil = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        veil.fill((*pal["bg"], 215))
        s.blit(veil, (0, 0))
        self._targets = []  # only the two choices are active
        box = pygame.Rect(340, 160, 600, 400)
        kit.panel(s, v, box, pal["surface"], pal, RADIUS["card"])
        kit.text(s, v, "On retourne au menu ?", self.size_title, pal["text"],
                 center=(box.centerx, box.y + 62), bold=True)
        go = pygame.Rect(box.x + 40, box.y + 130, 245, 220)
        stay = pygame.Rect(box.right - 285, box.y + 130, 245, 220)
        for r, label, icon, color, act, ev in (
                (go, "Menu", kit.icon_house, "accent1", self._go_home, InputEvent(Kind.MENU)),
                (stay, "Continuer", kit.icon_play, "accent3", self._cancel_home, None)):
            kit.panel(s, v, r, pal[color], pal, RADIUS["button"])
            icon(s, v, (r.centerx, r.y + 88), 92, pal["ink"])
            kit.text(s, v, label, self.size_btn, pal["text"], center=(r.centerx, r.bottom - 40),
                     bold=True)
            self._add(r, act, produces=ev)

    # .................................................................. pause & end
    def _render_pause_offer(self, s: pygame.Surface, pal: dict, t: float,
                            animate: bool) -> None:
        v = self.view
        self._char(s, pal, (640, 220), 118, "calme", t, False)
        kit.text_block(s, v, self.text, self.size_title + 4, pal["text"],
                       pygame.Rect(200, 376, 880, 90), bold=True)
        self._button(s, pal, pygame.Rect(270, 510, 340, 110), "Pause", kit.icon_pause,
                     "accent2", InputEvent(Kind.PAUSE))
        self._button(s, pal, pygame.Rect(670, 510, 340, 110), "Continuer", kit.icon_play,
                     "accent3", InputEvent(Kind.CONTINUE))

    def _render_pause(self, s: pygame.Surface, pal: dict, t: float, animate: bool) -> None:
        v = self.view
        self._char(s, pal, (640, 230), 124, "calme", t, False)
        kit.text_block(s, v, self.text, self.size_title + 4, pal["text"],
                       pygame.Rect(200, 390, 880, 80), bold=True)
        self._button(s, pal, pygame.Rect(450, 520, 380, 116), "Reprendre", kit.icon_play,
                     "accent3", InputEvent(Kind.CONTINUE))

    def _render_end(self, s: pygame.Surface, pal: dict, t: float, animate: bool) -> None:
        v = self.view
        self._mini_schedule(s, pal, len(self._steps()) - 1)
        kit.text(s, v, END_TITLE, self.size_title + 6, pal["text"], center=(LOGICAL_W / 2, 122),
                 bold=True)
        expression = "content" if self.stars else "neutre"
        mouth = self._char(s, pal, (330, 330), 108, expression, t, animate)
        bubble = pygame.Rect(484, 250, 660, 120)
        kit.speech_bubble(s, v, bubble, mouth, pal["surface"], pal)
        kit.text_block(s, v, self.text, self.size_text, pal["text"], bubble.inflate(-44, -20))
        if self.stars and self.settings.reward != "aucune":
            n = min(self.stars, 10)
            size = 58
            x0 = bubble.centerx - (n - 1) * (size + 8) / 2
            for i in range(n):
                kit.icon_star(s, v, (x0 + i * (size + 8), 440), size, pal)
        self._button(s, pal, pygame.Rect(470, 560, 340, 104), "Menu", kit.icon_house,
                     "accent1", InputEvent(Kind.MENU))

    def _reward_image(self, reward: RewardView) -> pygame.Surface | None:
        if reward.kind != "image" or not reward.image_path or self.rewards_dir is None:
            return None
        key = (reward.image_path, self.view.s(130))
        if key not in self._images:
            try:
                img = pygame.image.load(str(self.rewards_dir / reward.image_path)).convert_alpha()
                scale = key[1] / max(img.get_width(), img.get_height())
                self._images[key] = pygame.transform.smoothscale(
                    img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            except (pygame.error, FileNotFoundError):
                self._images[key] = None
        return self._images[key]
