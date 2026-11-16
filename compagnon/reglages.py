"""Fondations : réglages de l'adulte, dossiers de données, horloge, touches.

Sommaire (chercher « PARTIE n ») :
  1. Réglages (changés dans le mode adulte)
  2. Dossiers des données
  3. Horloge
  4. Touches et événements
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Protocol

# ================================================================================================
# PARTIE 1 — RÉGLAGES (changés dans le mode adulte)
# Adult settings (FP4), stored locally as JSON.
# ================================================================================================

AVAILABLE_ACTIVITIES = ("couleurs",)  # default order; games are chosen in the "Jeux" tab
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
    # home-screen cards: `activities` = order chosen by the adult, these ones are hidden
    hidden_activities: list[str] = field(default_factory=list)
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

# Dossier du projet (celui qui contient "Lancer le compagnon.bat")
DOSSIER_PROJET = Path(__file__).resolve().parent.parent
# Tout ce qu'on peut modifier sans programmer : textes, couleurs du jeu, mots, personnage
CONTENU = DOSSIER_PROJET / "contenu"


# ================================================================================================
# PARTIE 2 — DOSSIERS DES DONNÉES
# Where local data lives. Nothing is ever sent anywhere (FC5).
# ================================================================================================

def default_data_dir() -> Path:
    env = os.environ.get("COMPAGNON_DATA")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", str(Path.home()))) / "compagnon"
    base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(base) / "compagnon"


@dataclass(frozen=True)
class DataPaths:
    root: Path

    @property
    def settings(self) -> Path:
        return self.root / "reglages.json"

    @property
    def pin(self) -> Path:
        return self.root / "code.json"

    @property
    def profiles(self) -> Path:
        return self.root / "profils"

    @property
    def logs(self) -> Path:
        return self.root / "journaux"

    @property
    def tts_cache(self) -> Path:
        return self.root / "cache_voix"

    @property
    def voices(self) -> Path:
        return self.root / "voix"

    @property
    def rewards(self) -> Path:
        return self.root / "recompenses"

    @property
    def character(self) -> Path:
        return self.root / "personnage"

    def ensure(self) -> DataPaths:
        for d in (self.root, self.profiles, self.logs, self.tts_cache, self.voices, self.rewards):
            d.mkdir(parents=True, exist_ok=True)
        return self


# ================================================================================================
# PARTIE 3 — HORLOGE
# Clock abstraction: the core never calls time.* directly, so tests can simulate time.
# ================================================================================================

class Clock(Protocol):
    def now(self) -> float: ...


class RealClock:
    def now(self) -> float:
        return time.monotonic()


class FakeClock:
    """Simulated time for tests: `advance(15)` instead of waiting 15 real seconds."""

    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


# ================================================================================================
# PARTIE 4 — TOUCHES ET ÉVÉNEMENTS
# Input events, independent of the display (FC7): pygame, robot or tests all produce these.
# ================================================================================================

class Kind(str, Enum):
    CHOICE = "choix"  # value = choice id
    HELP = "aide"
    PAUSE = "pause"
    FINISHED = "fini"  # "J'ai fini"
    REPEAT = "repeter"  # drawn speaker icon next to the instruction
    CONTINUE = "continuer"  # "Continuer" / "Reprendre"
    BACKGROUND = "fond"  # click on nothing (still counts for agitation)
    ADULT_OPEN = "adulte_ouvert"
    ADULT_CLOSE = "adulte_ferme"
    NEW_SESSION = "nouvelle_seance"
    QUIT = "quitter"
    # Home screen (handled by the app, never by the session controller)
    MENU = "menu"  # back to the home screen ("Maison" button, confirmed)
    START = "lancer"  # value = activity id of the touched card
    DESCRIBE = "decrire"  # value = activity id: the character says the card's description


CHILD_KINDS = frozenset(
    {Kind.CHOICE, Kind.HELP, Kind.PAUSE, Kind.FINISHED, Kind.REPEAT, Kind.CONTINUE, Kind.BACKGROUND}
)


@dataclass(frozen=True)
class InputEvent:
    kind: Kind
    value: str | None = None
