"""Adult settings (FP4), stored locally as JSON."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from itertools import permutations
from pathlib import Path

AVAILABLE_ACTIVITIES = ("couleurs",)
# Voice presets (see voice/presets.py; same names, checked by a test)
VOICE_CHOICES = ("jessica", "jessica-douce", "jessica-enfant", "siwis", "siwis-douce",
                 "siwis-enfant")


@dataclass
class Settings:
    volume: int = 70  # 0-100
    voice: str = "jessica"  # voice preset (timbre)
    voice_rate: str = "normale"  # "lente" | "normale"
    sounds: bool = True  # sound effects (soft success sound)
    palette: str = "sable"  # "sable" | "ciel" | "menthe"
    animations: bool = True
    text_size: str = "moyen"  # "petit" | "moyen" | "grand"
    activities: list[str] = field(default_factory=lambda: list(AVAILABLE_ACTIVITIES))
    initial_level: int = 1  # difficulty 1-4 (number of choices)
    success_threshold: int = 3  # successes without help -> harder
    error_threshold: int = 3  # errors in a row -> hint, then easier
    silence_repeat_s: int = 15  # no answer -> simpler instruction
    silence_end_s: int = 60  # no answer at all -> end calmly
    pause_mode: str = "proposee"  # "proposee" | "automatique"
    pause_interval_s: int = 180  # scheduled pause offer (0 = never)
    reward: str = "etoile"  # visual reward: "etoile" | "image" | "aucune" (sound only)
    reward_image: str = ""  # file name in the rewards folder
    items_per_activity: int = 10
    activity_max_s: int = 240  # 2-5 min per activity (FP1)
    agitation_clicks: int = 5  # more than N clicks ...
    agitation_window_s: float = 3.0  # ... within this window = agitation
    overload_errors: int = 5  # errors in a row -> offer a pause


@dataclass(frozen=True)
class SettingSpec:
    key: str
    label: str
    options: tuple


SETTING_SPECS: tuple[SettingSpec, ...] = (
    SettingSpec("volume", "Volume", tuple(range(0, 101, 10))),
    SettingSpec("voice", "Voix", VOICE_CHOICES),
    SettingSpec("voice_rate", "Débit de la voix", ("lente", "normale")),
    SettingSpec("sounds", "Son de réussite", (True, False)),
    SettingSpec("palette", "Couleurs de l'écran", ("sable", "ciel", "menthe")),
    SettingSpec("animations", "Animations", (True, False)),
    SettingSpec("text_size", "Taille du texte", ("petit", "moyen", "grand")),
    SettingSpec("activities", "Activités (ordre)",
                tuple(list(p) for p in permutations(AVAILABLE_ACTIVITIES))),
    SettingSpec("initial_level", "Niveau de départ", (1, 2, 3, 4)),
    SettingSpec("success_threshold", "Réussites pour monter", (2, 3, 4, 5)),
    SettingSpec("error_threshold", "Erreurs avant l'aide", (2, 3, 4, 5)),
    SettingSpec("silence_repeat_s", "Répéter la consigne après", (5, 10, 15, 20, 25, 30)),
    SettingSpec("pause_mode", "Pause si surcharge", ("proposee", "automatique")),
    SettingSpec("pause_interval_s", "Pause proposée toutes les", (0, 90, 120, 150, 180, 240)),
    SettingSpec("activity_max_s", "Durée d'une activité", (120, 180, 240, 300)),
    SettingSpec("reward", "Récompense visuelle", ("etoile", "image", "aucune")),
)

_LABELS = {
    "lente": "lente", "normale": "normale", "sable": "sable", "ciel": "ciel", "menthe": "menthe",
    "petit": "petit", "moyen": "moyen", "grand": "grand", "proposee": "proposée",
    "automatique": "automatique", "etoile": "étoile", "image": "image", "aucune": "aucune",
}


def format_value(key: str, value: object) -> str:
    if isinstance(value, bool):
        return "oui" if value else "non"
    if key == "pause_interval_s":
        return "jamais" if value == 0 else f"{int(value) // 60} min {int(value) % 60:02d}"
    if key in ("silence_repeat_s",):
        return f"{value} s"
    if key == "activity_max_s":
        return f"{int(value) // 60} min"
    if key == "activities":
        return ", ".join(value)  # type: ignore[arg-type]
    if key == "reward_image":
        return str(value) or "aucune"
    if key == "volume":
        return f"{value} %"
    return _LABELS.get(str(value), str(value))


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        try:
            data = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return Settings()
        known = {f.name for f in fields(Settings)}
        try:
            return Settings(**{k: v for k, v in data.items() if k in known})
        except TypeError:
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), "utf-8")
        os.replace(tmp, self.path)

    def reset(self) -> Settings:
        if self.path.exists():
            self.path.unlink()
        return Settings()
