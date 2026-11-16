"""Where local data lives. Nothing is ever sent anywhere (FC5)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


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

    def ensure(self) -> DataPaths:
        for d in (self.root, self.profiles, self.logs, self.tts_cache, self.voices, self.rewards):
            d.mkdir(parents=True, exist_ok=True)
        return self
