"""4-digit adult code, stored as a salted PBKDF2 hash (never in clear)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

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
