"""AI service = generator + filter + prepared phrases + hard timeout (FP3).

The < 2 s guarantee comes from the timeout: if the model is late or its sentence is
rejected, a prepared phrase is used immediately.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from compagnon.ai.filter import SentenceFilter, clean_llm_output
from compagnon.ai.rephraser import Rephraser

DEFAULT_TIMEOUT_S = 1.3


@dataclass(frozen=True)
class Phrase:
    text: str
    source: str  # "llm" | "reserve"
    latency_ms: int
    reason: str | None = None  # why the AI sentence was not used
    raw: str | None = None  # raw model output (for the log)


class AIService:
    def __init__(self, rephraser: Rephraser, sentence_filter: SentenceFilter,
                 timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self.rephraser = rephraser
        self.filter = sentence_filter
        self.timeout_s = timeout_s
        self._next: dict[tuple[str, str], int] = {}

    def rephrase(self, kind: str, ctx: dict) -> Phrase:
        t0 = time.perf_counter()
        raw: str | None = None
        reason: str | None = "ia_desactivee"
        if self.rephraser.enabled:
            raw, reason = self._call(kind, ctx)
            if raw is not None:
                res = self.filter.check(clean_llm_output(raw), kind, ctx)
                if res.ok:
                    return Phrase(res.text, "llm", _ms(t0), None, raw)
                reason = res.reason
        return Phrase(self._fallback(kind, ctx), "reserve", _ms(t0), reason, raw)

    def _call(self, kind: str, ctx: dict) -> tuple[str | None, str | None]:
        box: dict[str, object] = {}

        def run() -> None:
            try:
                box["out"] = self.rephraser.generate(kind, ctx)
            except Exception as exc:  # noqa: BLE001 - any failure -> prepared phrase
                box["err"] = repr(exc)

        th = threading.Thread(target=run, daemon=True)
        th.start()
        th.join(self.timeout_s)
        if th.is_alive():
            return None, "timeout"
        if "err" in box:
            return None, "erreur"
        out = box.get("out")
        if not out:
            return None, "vide"
        return str(out), None

    def _fallback(self, kind: str, ctx: dict) -> str:
        options = ctx["reserve"][kind]
        key = (ctx.get("cible", ""), kind)
        i = self._next.get(key, 0)
        self._next[key] = i + 1
        return options[i % len(options)]


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
