"""Mode adulte : code, réglages, choix des jeux, et son écran.

Sommaire (chercher « PARTIE n ») :
  1. Code adulte
  2. Ce que l'adulte peut faire
  3. Écran du mode adulte
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Callable
from datetime import datetime
from functools import partial
from pathlib import Path

import pygame

from compagnon.apparence import LOGICAL_H, LOGICAL_W, font_path
from compagnon.dessin import blit_center, rounded_rect, wrap_text
from compagnon.enfant import ChildProfile, ProfileStore, apply_answer
from compagnon.jeux import CATALOG, MAX_VISIBLE, Catalog, CatalogEntry
from compagnon.reglages import (
    SETTING_SPECS,
    Clock,
    DataPaths,
    InputEvent,
    Kind,
    Settings,
    SettingSpec,
    SettingsStore,
    format_value,
)

# ================================================================================================
# PARTIE 1 — CODE ADULTE
# 4-digit adult code, stored as a salted PBKDF2 hash (never in clear).
# ================================================================================================

DEFAULT_PIN = "1234"
_ITER = 100_000


def _hash(pin: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _ITER)


def valid_pin(pin: str) -> bool:
    return len(pin) == 4 and pin.isdigit()


class PinStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def is_default(self) -> bool:
        return not self.path.exists()

    def check(self, pin: str) -> bool:
        if not valid_pin(pin):
            return False
        if self.is_default():
            return hmac.compare_digest(pin, DEFAULT_PIN)
        data = json.loads(self.path.read_text("utf-8"))
        salt = bytes.fromhex(data["sel"])
        return hmac.compare_digest(_hash(pin, salt).hex(), data["hash"])

    def set(self, pin: str) -> None:
        if not valid_pin(pin):
            raise ValueError("Le code doit avoir 4 chiffres.")
        salt = os.urandom(16)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"sel": salt.hex(), "hash": _hash(pin, salt).hex()}),
                             "utf-8")


# ================================================================================================
# PARTIE 2 — CE QUE L'ADULTE PEUT FAIRE
# Adult mode logic (FP4, FP6), independent of the screen. The pygame view only calls it.
# ================================================================================================

MAX_ATTEMPTS = 3
LOCK_S = 30.0
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp")


class CompanionMode:
    def __init__(self, *, paths: DataPaths, settings_store: SettingsStore, pin_store: PinStore,
                 profile_store: ProfileStore, profile: ChildProfile, clock: Clock,
                 on_action: Callable[..., object] | None = None,
                 catalog: Catalog | None = None) -> None:
        self.catalog = catalog or CATALOG
        self.paths = paths
        self.settings_store = settings_store
        self.pin_store = pin_store
        self.profile_store = profile_store
        self.profile = profile
        self.clock = clock
        self.settings: Settings = settings_store.load()
        self.on_action = on_action or (lambda *a, **k: None)
        self.unlocked = False
        self._attempts = 0
        self._locked_until = 0.0

    # --- access -------------------------------------------------------------------
    def unlock(self, pin: str) -> str:
        """Returns "ok", "faux" or "bloque" (after 3 wrong codes, 30 s)."""
        now = self.clock.now()
        if now < self._locked_until:
            return "bloque"
        if self.pin_store.check(pin):
            self.unlocked, self._attempts = True, 0
            self.on_action("adulte_deverrouille")
            return "ok"
        self._attempts += 1
        if self._attempts >= MAX_ATTEMPTS:
            self._attempts = 0
            self._locked_until = now + LOCK_S
            return "bloque"
        return "faux"

    def lock(self) -> None:
        self.unlocked = False

    def _require(self) -> None:
        if not self.unlocked:
            raise PermissionError("Mode accompagnant verrouillé")

    @property
    def pin_is_default(self) -> bool:
        return self.pin_store.is_default()

    def change_pin(self, new_pin: str) -> bool:
        self._require()
        if not valid_pin(new_pin):
            return False
        self.pin_store.set(new_pin)
        self.on_action("code_change")
        return True

    # --- settings -----------------------------------------------------------------
    def reward_images(self) -> list[str]:
        if not self.paths.rewards.exists():
            return []
        return sorted(p.name for p in self.paths.rewards.iterdir()
                      if p.suffix.lower() in IMAGE_EXT)

    def specs(self) -> list[SettingSpec]:
        images = ("", *self.reward_images())
        return [*SETTING_SPECS, SettingSpec("reward_image", "Image préférée", images)]

    def value_label(self, key: str) -> str:
        return format_value(key, getattr(self.settings, key))

    def adjust(self, key: str, step: int) -> None:
        self._require()
        spec = next(s for s in self.specs() if s.key == key)
        current = getattr(self.settings, key)
        idx = spec.options.index(current) if current in spec.options else 0
        new = spec.options[(idx + step) % len(spec.options)]
        setattr(self.settings, key, list(new) if isinstance(new, list) else new)
        self.settings_store.save(self.settings)
        self.on_action("reglage", cle=key, valeur=getattr(self.settings, key))

    # --- games on the home screen (FP4) -------------------------------------------
    def visible_games(self) -> list[CatalogEntry]:
        """Cards shown to the child, in the adult's order (same place every session)."""
        s = self.settings
        return self.catalog.visible(s.activities, s.hidden_activities)

    def games(self) -> list[tuple[CatalogEntry, bool]]:
        """Every registered game with its state: visible ones first, in card order."""
        visible = self.visible_games()
        ids = {e.id for e in visible}
        rest = [e for e in self.catalog.entries() if e.id not in ids]
        return [(e, True) for e in visible] + [(e, False) for e in rest]

    def toggle_game(self, game_id: str) -> str | None:
        """Show / hide a card. Returns a message when refused (last card, or too many)."""
        self._require()
        s = self.settings
        visible = [e.id for e in self.visible_games()]
        if game_id in visible:
            if len(visible) == 1:
                return "Il faut au moins un jeu."
            visible.remove(game_id)
            hidden = [*s.hidden_activities, game_id]
        else:
            if len(visible) >= MAX_VISIBLE:
                return f"{MAX_VISIBLE} jeux au maximum, pour ne pas surcharger l'écran."
            visible.append(game_id)
            hidden = [i for i in s.hidden_activities if i != game_id]
        self._save_games(visible, hidden)
        return None

    def move_game(self, game_id: str, step: int) -> None:
        """Move a visible card one place earlier (-1) or later (+1)."""
        self._require()
        visible = [e.id for e in self.visible_games()]
        if game_id not in visible:
            return
        i = visible.index(game_id)
        j = max(0, min(len(visible) - 1, i + step))
        visible.insert(j, visible.pop(i))
        self._save_games(visible, list(self.settings.hidden_activities))

    def _save_games(self, visible: list[str], hidden: list[str]) -> None:
        s = self.settings
        s.activities = visible
        # Once the adult has chosen, every game not shown is hidden on purpose; only games
        # registered LATER (new versions of the app) appear by themselves.
        not_shown = {e.id for e in self.catalog.entries()} - set(visible)
        s.hidden_activities = sorted((set(hidden) | not_shown) - set(visible))
        self.settings_store.save(s)
        self.on_action("jeux", visibles=visible, caches=s.hidden_activities)

    # --- questions to the adult (FP6) ---------------------------------------------
    def questions(self) -> list[dict]:
        return list(self.profile.pending_questions)

    def answer(self, question_id: str, yes: bool) -> bool:
        self._require()
        changed = apply_answer(self.profile, question_id, yes)
        self.profile_store.save(self.profile)
        self.on_action("reponse_adulte", question=question_id, oui=yes, applique=changed)
        return changed

    # --- learning and data --------------------------------------------------------
    @property
    def learning_paused(self) -> bool:
        return self.profile.learning_paused

    def set_learning_paused(self, paused: bool) -> None:
        self._require()
        self.profile.learning_paused = paused
        self.profile_store.save(self.profile)
        self.on_action("apprentissage", en_pause=paused)

    def factory_reset(self) -> None:
        """Erase everything learned and restore default settings. Logs and code are kept."""
        self._require()
        self.profile_store.delete_all()
        self.profile.reset_learned()
        self.settings = self.settings_store.reset()
        self.on_action("reinitialisation_usine")

    def delete_logs(self) -> int:
        self._require()
        n = 0
        for p in self.paths.logs.glob("*.jsonl"):
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
        return n


# ================================================================================================
# PARTIE 3 — ÉCRAN DU MODE ADULTE
# Adult screens (code, settings, questions, data). Only drawing and clicks here; all the
# logic is in companion/mode.py so it is tested without a screen.
# ================================================================================================

W, H = LOGICAL_W, LOGICAL_H  # drawn on the logical canvas, scaled by the display
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
        self.f_small = pygame.font.Font(font_path(), 22)
        self.f_mid = pygame.font.Font(font_path(True), 26)
        self.f_big = pygame.font.Font(font_path(True), 32)

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
        tabs = (("reglages", "Réglages"), ("jeux", "Jeux"), ("questions", f"Questions ({n_q})"),
                ("donnees", "Données"))
        for i, (tid, label) in enumerate(tabs):
            r = pygame.Rect(20 + i * 230, 12, 215, 52)
            self._button(s, pal, r, label, lambda t=tid: self._set_tab(t),  # type: ignore[misc]
                         "fini" if self.tab == tid else "header")
        self._button(s, pal, pygame.Rect(W - 190, 12, 170, 52), "Fermer", self._close, "pause")
        if self.tab == "reglages":
            self._render_settings(s, pal)
        elif self.tab == "jeux":
            self._render_games(s, pal)
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
            x, y = 20 + col * 630, 82 + row * 70
            box = pygame.Rect(x, y, 610, 60)
            rounded_rect(s, pal["bg"], box, 10)
            s.blit(self.f_small.render(spec.label, True, pal["text"]), (x + 12, y + 8))
            s.blit(self.f_small.render(self.mode.value_label(spec.key), True, pal["soft_text"]),
                   (x + 12, y + 32))
            for j, (label, step) in enumerate((("-", -1), ("+", 1))):
                r = pygame.Rect(x + 494 + j * 56, y + 8, 46, 44)
                self._button(s, pal, r, label,
                             lambda k=spec.key, st=step: self.mode.adjust(k, st))  # type: ignore[misc]

    def _render_games(self, s: pygame.Surface, pal: dict) -> None:
        """FP4: which games appear on the child's home screen, and in which order.
        The cards keep this order from one session to the next (FC1)."""
        blit_center(s, self.f_small, "Jeux affichés sur l'écran d'accueil de l'enfant "
                    "(dans cet ordre).", pal["soft_text"], (W // 2, 92))
        for i, (entry, visible) in enumerate(self.mode.games()):
            y = 122 + i * 84
            box = pygame.Rect(20, y, W - 40, 72)
            rounded_rect(s, pal["bg"] if visible else pal["header"], box, 12)
            pos = f"{i + 1}." if visible else "-"
            s.blit(self.f_mid.render(f"{pos}  {entry.title}", True, pal["text"]), (40, y + 8))
            s.blit(self.f_small.render(entry.description, True, pal["soft_text"]), (40, y + 40))
            label = "Affiché" if visible else "Caché"
            self._button(s, pal, pygame.Rect(W - 520, y + 10, 170, 52), label,
                         lambda g=entry.id: self._toggle_game(g),  # type: ignore[misc]
                         "fini" if visible else "pause", self.f_small)
            if visible:
                for j, (arrow, step) in enumerate((("Monter", -1), ("Descendre", 1))):
                    r = pygame.Rect(W - 335 + j * 160, y + 10, 150, 52)
                    self._button(s, pal, r, arrow,
                                 lambda g=entry.id, st=step: self.mode.move_game(g, st),  # type: ignore[misc]
                                 "aide", self.f_small)

    def _toggle_game(self, game_id: str) -> None:
        self.message = self.mode.toggle_game(game_id) or ""

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
