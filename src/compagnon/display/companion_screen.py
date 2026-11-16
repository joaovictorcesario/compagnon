"""Adult screens (code, settings, questions, data). Only drawing and clicks here; all the
logic is in companion/mode.py so it is tested without a screen."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from functools import partial

import pygame

from compagnon.companion.mode import CompanionMode
from compagnon.core.events import InputEvent, Kind
from compagnon.display.drawing import blit_center, rounded_rect, wrap_text

W, H = 1024, 720
Action = Callable[[], list[InputEvent] | None]


class CompanionScreen:
    def __init__(self, mode: CompanionMode) -> None:
        self.mode = mode
        self.active = False
        self.state = "pin"
        self.purpose = "unlock"
        self.entry = ""
        self.message = ""
        self.tab = "reglages"
        self.confirm: str | None = None
        self._targets: list[tuple[pygame.Rect, Action]] = []
        self.f_small = pygame.font.SysFont("verdana,dejavusans,arial", 20)
        self.f_mid = pygame.font.SysFont("verdana,dejavusans,arial", 24, bold=True)
        self.f_big = pygame.font.SysFont("verdana,dejavusans,arial", 30, bold=True)

    # ------------------------------------------------------------ control
    def open(self) -> None:
        self.mode.lock()
        self.active, self.state, self.purpose = True, "pin", "unlock"
        self.entry, self.message, self.confirm, self.tab = "", "", None, "reglages"

    def _close(self) -> list[InputEvent]:
        self.mode.lock()
        self.active = False
        return [InputEvent(Kind.ADULT_CLOSE)]

    def click(self, pos: tuple[int, int]) -> list[InputEvent]:
        for rect, action in reversed(self._targets):
            if rect.collidepoint(pos):
                return action() or []
        return []

    def key(self, e: pygame.event.Event) -> list[InputEvent]:
        if self.state != "pin":
            return []
        if e.unicode and e.unicode.isdigit():
            self._digit(e.unicode)
        elif e.key == pygame.K_BACKSPACE:
            self.entry = self.entry[:-1]
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self._ok() or []
        elif e.key == pygame.K_ESCAPE:
            return self._cancel() or []
        return []

    def _backspace(self) -> None:
        self.entry = self.entry[:-1]

    def _digit(self, d: str) -> None:
        if len(self.entry) < 4:
            self.entry += d

    def _ok(self) -> list[InputEvent] | None:
        if self.purpose == "change":
            ok = self.mode.change_pin(self.entry)
            self.message = "Code changé." if ok else "Le code doit avoir 4 chiffres."
            self.entry = ""
            if ok:
                self.state, self.tab = "menu", "donnees"
            return None
        result = self.mode.unlock(self.entry)
        self.entry = ""
        if result == "ok":
            self.state, self.message = "menu", ""
        elif result == "bloque":
            self.message = "Trop d'essais. Attendez 30 secondes."
        else:
            self.message = "Code incorrect."
        return None

    def _cancel(self) -> list[InputEvent] | None:
        if self.purpose == "change":
            self.state, self.purpose, self.entry = "menu", "unlock", ""
            return None
        return self._close()

    # ------------------------------------------------------------ drawing
    def render(self, s: pygame.Surface, pal: dict) -> None:
        self._targets = []
        s.fill(pal["panel"])
        if self.state == "pin":
            self._render_pin(s, pal)
        else:
            self._render_menu(s, pal)

    def _button(self, s: pygame.Surface, pal: dict, rect: pygame.Rect, label: str,
                action: Action, color: str = "aide", font: pygame.font.Font | None = None) -> None:
        rounded_rect(s, pal[color], rect, 12, pal["outline"], 2)
        blit_center(s, font or self.f_mid, label, pal["text"], rect.center)
        self._targets.append((rect, action))

    def _render_pin(self, s: pygame.Surface, pal: dict) -> None:
        title = "Mode accompagnant" if self.purpose == "unlock" else "Nouveau code"
        blit_center(s, self.f_big, title, pal["text"], (W // 2, 60))
        sub = "Code à 4 chiffres" if self.purpose == "unlock" else "Choisissez 4 chiffres"
        blit_center(s, self.f_small, sub, pal["soft_text"], (W // 2, 105))
        for i in range(4):
            c = (W // 2 - 75 + i * 50, 160)
            pygame.draw.circle(s, pal["outline"], c, 12, 0 if i < len(self.entry) else 2)
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Effacer", "0", "OK"]
        for i, k in enumerate(keys):
            r = pygame.Rect(W // 2 - 165 + (i % 3) * 115, 200 + (i // 3) * 85, 100, 70)
            act: Action = {"Effacer": self._backspace, "OK": self._ok}.get(
                k, partial(self._digit, k))
            self._button(s, pal, r, k, act, "fini" if k == "OK" else "aide",
                         self.f_small if k == "Effacer" else self.f_big)
        self._button(s, pal, pygame.Rect(W // 2 - 110, 560, 220, 56), "Annuler", self._cancel,
                     "pause")
        if self.message:
            blit_center(s, self.f_small, self.message, pal["text"], (W // 2, 650))

    def _render_menu(self, s: pygame.Surface, pal: dict) -> None:
        n_q = len(self.mode.questions())
        tabs = (("reglages", "Réglages"), ("questions", f"Questions ({n_q})"),
                ("donnees", "Données"))
        for i, (tid, label) in enumerate(tabs):
            r = pygame.Rect(20 + i * 230, 12, 215, 52)
            self._button(s, pal, r, label, lambda t=tid: self._set_tab(t),  # type: ignore[misc]
                         "fini" if self.tab == tid else "header")
        self._button(s, pal, pygame.Rect(W - 190, 12, 170, 52), "Fermer", self._close, "pause")
        if self.tab == "reglages":
            self._render_settings(s, pal)
        elif self.tab == "questions":
            self._render_questions(s, pal)
        else:
            self._render_data(s, pal)
        if self.message:
            blit_center(s, self.f_small, self.message, pal["text"], (W // 2, H - 22))

    def _set_tab(self, tab: str) -> None:
        self.tab, self.confirm, self.message = tab, None, ""

    def _render_settings(self, s: pygame.Surface, pal: dict) -> None:
        specs = self.mode.specs()
        per_col = (len(specs) + 1) // 2
        for i, spec in enumerate(specs):
            col, row = divmod(i, per_col)
            x, y = 20 + col * 502, 82 + row * 70
            box = pygame.Rect(x, y, 482, 60)
            rounded_rect(s, pal["bg"], box, 10)
            s.blit(self.f_small.render(spec.label, True, pal["text"]), (x + 12, y + 8))
            s.blit(self.f_small.render(self.mode.value_label(spec.key), True, pal["soft_text"]),
                   (x + 12, y + 32))
            for j, (label, step) in enumerate((("-", -1), ("+", 1))):
                r = pygame.Rect(x + 370 + j * 56, y + 8, 46, 44)
                self._button(s, pal, r, label,
                             lambda k=spec.key, st=step: self.mode.adjust(k, st))  # type: ignore[misc]

    def _render_questions(self, s: pygame.Surface, pal: dict) -> None:
        qs = self.mode.questions()
        if self.mode.learning_paused:
            blit_center(s, self.f_small, "Apprentissage en pause : les réponses ne seront pas "
                        "utilisées.", pal["soft_text"], (W // 2, 90))
        if not qs:
            blit_center(s, self.f_mid, "Aucune question.", pal["soft_text"], (W // 2, 200))
            return
        for i, q in enumerate(qs[:4]):
            y = 115 + i * 135
            box = pygame.Rect(20, y, W - 40, 122)
            rounded_rect(s, pal["bg"], box, 12)
            s.blit(self.f_mid.render(q["texte"], True, pal["text"]), (36, y + 10))
            ctx = f"{q.get('contexte', '')} - séance du {q.get('date', '')}"
            for k, line in enumerate(wrap_text(self.f_small, ctx, W - 360)[:2]):
                s.blit(self.f_small.render(line, True, pal["soft_text"]), (36, y + 52 + k * 26))
            for j, (label, yes) in enumerate((("Oui", True), ("Non", False))):
                r = pygame.Rect(W - 300 + j * 135, y + 30, 120, 60)
                self._button(s, pal, r, label,
                             lambda qid=q["id"], v=yes: self._answer(qid, v),  # type: ignore[misc]
                             "fini" if yes else "pause")

    def _answer(self, qid: str, yes: bool) -> None:
        used = self.mode.answer(qid, yes)
        self.message = ("Réponse prise en compte." if used
                        else "Réponse notée (apprentissage en pause).")

    def _render_data(self, s: pygame.Surface, pal: dict) -> list[InputEvent] | None:
        p = self.mode.profile
        info = f"Profil : {p.name}   -   séances : {p.sessions}   -   niveau : {p.level or '-'}"
        blit_center(s, self.f_small, info, pal["soft_text"], (W // 2, 92))
        if self.mode.pin_is_default:
            blit_center(s, self.f_small, "Code par défaut : pensez à le changer.",
                        pal["text"], (W // 2, 120))
        learning = ("Apprentissage : actif (toucher pour le mettre en pause)"
                    if not self.mode.learning_paused else
                    "Apprentissage : en pause (toucher pour le reprendre)")
        rows: list[tuple[str, Action, str]] = [
            (learning, lambda: self.mode.set_learning_paused(not self.mode.learning_paused),
             "aide"),
            ("Nouvelle séance", self._new_session, "fini"),
            ("Changer le code", self._change_pin, "aide"),
            ("Confirmer : tout ce qui a été appris sera effacé"
             if self.confirm == "reset" else "Réinitialiser (réglages d'usine)",
             self._reset, "pause"),
            ("Confirmer : supprimer tous les journaux"
             if self.confirm == "logs" else "Supprimer les journaux", self._delete_logs,
             "pause"),
            ("Quitter l'application", lambda: [InputEvent(Kind.QUIT)], "header"),
        ]
        for i, (label, act, color) in enumerate(rows):
            r = pygame.Rect(W // 2 - 330, 150 + i * 82, 660, 66)
            self._button(s, pal, r, label, act, color, self.f_small)
        return None

    def _new_session(self) -> list[InputEvent]:
        self.mode.lock()
        self.active = False
        return [InputEvent(Kind.NEW_SESSION)]

    def _change_pin(self) -> None:
        self.state, self.purpose, self.entry, self.message = "pin", "change", "", ""

    def _reset(self) -> None:
        if self.confirm != "reset":
            self.confirm = "reset"
            return
        self.mode.factory_reset()
        self.confirm = None
        self.message = f"Réglages d'usine rétablis ({datetime.now():%H:%M})."

    def _delete_logs(self) -> None:
        if self.confirm != "logs":
            self.confirm = "logs"
            return
        n = self.mode.delete_logs()
        self.confirm = None
        self.message = f"{n} journal(aux) supprimé(s)."
