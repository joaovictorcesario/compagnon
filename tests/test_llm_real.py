"""V2 acceptance test with the REAL local model (Ollama). Slow, so not run by default:

    python -m pytest -m llm -s

Asks 100 reformulations/hints and checks that NO inappropriate sentence reaches the
child, and that the AI really appears (not only prepared phrases).
"""

from __future__ import annotations

import os
import random
from collections import Counter

import pytest

from compagnon.ai import AIService, OllamaRephraser, SentenceFilter
from compagnon.ai.filter import FORBIDDEN
from compagnon.tools.benchmark_llm import FALLBACK_LIMIT, contexts

MODEL = os.environ.get("COMPAGNON_MODELE", "qwen2.5:1.5b")
PROMPT = os.environ.get("COMPAGNON_PROMPT", "normal")

pytestmark = pytest.mark.llm


@pytest.fixture(scope="module")
def service():
    reph = OllamaRephraser(model=MODEL, prompt_style=PROMPT, rng=random.Random(5))
    if not reph.available():
        pytest.skip(f"Ollama ou le modèle {MODEL} absent (ollama pull {MODEL})")
    reph.warmup()
    return AIService(reph, SentenceFilter.default())


def test_100_reformulations_no_inappropriate_sentence(service):
    filt = SentenceFilter.default()
    sources: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    for kind, ctx in contexts(100, random.Random(11)):
        p = service.rephrase(kind, ctx)
        sources[p.source] += 1
        if p.reason:
            reasons[p.reason.split(":")[0]] += 1
        assert filt.check(p.text, kind, ctx).ok, p
        assert len(p.text.split()) <= 10, p
        words = {w.strip(".,!?«»").lower() for w in p.text.replace("'", " ").split()}
        assert not words & FORBIDDEN, p
        assert p.latency_ms < 2000, p
    rate = sources["reserve"] / 100
    print(f"\n{MODEL}/{PROMPT}: IA {sources['llm']} %, réserve {sources['reserve']} %",
          dict(reasons))
    assert sources["llm"] > 0, "l'IA n'apparaît jamais : voir le benchmark"
    if rate > FALLBACK_LIMIT:
        pytest.xfail(f"réserve {rate:.0%} > {FALLBACK_LIMIT:.0%} : prompt court ou modèle 0.5b")
