"""Adult mode logic (FP4, FP6), independent of the screen. The pygame view only calls it."""

from __future__ import annotations

from collections.abc import Callable

from compagnon.child.profile import ChildProfile, ProfileStore, apply_answer
from compagnon.companion.pin import PinStore, valid_pin
from compagnon.core.clock import Clock
from compagnon.core.settings import (
    SETTING_SPECS,
    Settings,
    SettingSpec,
    SettingsStore,
    format_value,
)
from compagnon.paths import DataPaths

MAX_ATTEMPTS = 3
LOCK_S = 30.0
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp")


class CompanionMode:
    def __init__(self, *, paths: DataPaths, settings_store: SettingsStore, pin_store: PinStore,
                 profile_store: ProfileStore, profile: ChildProfile, clock: Clock,
                 on_action: Callable[..., object] | None = None) -> None:
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
