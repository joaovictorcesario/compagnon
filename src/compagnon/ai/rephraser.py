"""Text generators behind one interface: stub (V1), Ollama (V2). On the robot (S8) a
cached generator can be added here without touching the rest."""

from __future__ import annotations

import json
import random
import urllib.request
from typing import Protocol
from urllib.parse import urlparse

from compagnon.ai.prompts import build_prompt

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class Rephraser(Protocol):
    enabled: bool
    name: str

    def generate(self, kind: str, ctx: dict) -> str | None: ...


class StubRephraser:
    """V1: no model. The service always uses the prepared phrases."""

    enabled = False
    name = "stub"

    def generate(self, kind: str, ctx: dict) -> str | None:
        return None


def check_local(host: str) -> str:
    """FC5: refuse any non-local address, so nothing can leave the computer."""
    parsed = urlparse(host)
    if parsed.hostname not in LOCAL_HOSTS:
        raise ValueError(f"Hôte refusé (doit être local) : {host}")
    return host.rstrip("/")


class OllamaRephraser:
    enabled = True

    def __init__(self, model: str = "qwen2.5:1.5b", host: str = "http://127.0.0.1:11434",
                 prompt_style: str = "normal", temperature: float = 0.6,
                 rng: random.Random | None = None) -> None:
        self.host = check_local(host)
        self.model = model
        self.prompt_style = prompt_style
        self.temperature = temperature
        self.rng = rng or random.Random()
        self.name = f"ollama:{model}:{prompt_style}"

    def _post(self, path: str, body: dict, timeout: float) -> dict:
        req = urllib.request.Request(
            self.host + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (local only)
            return json.loads(resp.read().decode("utf-8"))

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.host + "/api/tags", timeout=1.0) as resp:  # noqa: S310
                tags = json.loads(resp.read().decode("utf-8"))
        except (OSError, ValueError):
            return False
        names = {m.get("name", "") for m in tags.get("models", [])}
        return self.model in names or f"{self.model}:latest" in names

    def warmup(self) -> None:
        """Load the model in memory and keep it there (first call can take seconds)."""
        self._post("/api/generate", {"model": self.model, "prompt": "", "keep_alive": "30m"}, 120)

    def generate(self, kind: str, ctx: dict) -> str | None:
        system, prompt = build_prompt(self.prompt_style, kind, ctx, self.rng)
        body = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": self.temperature,
                "top_p": 0.9,
                "num_predict": 24,
                "num_ctx": 512,
                "stop": ["\n"],
            },
        }
        out = self._post("/api/generate", body, timeout=10)
        return out.get("response")
