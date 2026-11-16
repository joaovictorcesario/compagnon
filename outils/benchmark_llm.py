"""Benchmark of the local model on THIS computer (step 1 of V2).

Measures, for each model / prompt style:
* raw latency of the model (p50, p95);
* timeout rate (answer later than the limit) and rejection rate (filter);
* fallback rate = timeouts + rejections + errors -> prepared phrase used.
Rule agreed with the team: if the fallback rate is above ~20 %, shorten the prompt
(--prompt court) or use the smaller model (qwen2.5:0.5b): in the demo the AI must
really be visible.

    python outils/benchmark_llm.py --modele qwen2.5:1.5b qwen2.5:0.5b --prompt normal court
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import threading
import time
from collections import Counter
from pathlib import Path

from compagnon.ia import DEFAULT_TIMEOUT_S, OllamaRephraser, SentenceFilter, clean_llm_output
from compagnon.jeux import ColorActivity

FALLBACK_LIMIT = 0.20


def contexts(n: int, rng: random.Random) -> list[tuple[str, dict]]:
    act = ColorActivity()
    out = []
    ids = list(act.colors)
    for i in range(n):
        item = act.make_item(4, rng)
        item.key = ids[i % len(ids)]
        item.instruction = act.colors[item.key]["consigne"]
        out.append(("simplifier" if i % 2 == 0 else "indice", act.ai_context(item)))
    return out


def run_one(model: str, style: str, n: int, timeout: float, seed: int) -> dict:
    reph = OllamaRephraser(model=model, prompt_style=style, rng=random.Random(seed))
    if not reph.available():
        return {"modele": model, "prompt": style, "erreur": "modèle introuvable dans Ollama"}
    reph.warmup()
    filt = SentenceFilter.default()
    latencies: list[float] = []
    outcome: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    accepted: list[str] = []
    rejected: list[str] = []
    for kind, ctx in contexts(n, random.Random(seed)):
        box: dict[str, object] = {}

        def call(kind: str = kind, ctx: dict = ctx, box: dict = box) -> None:
            try:
                box["out"] = reph.generate(kind, ctx)
            except Exception as exc:  # noqa: BLE001
                box["err"] = repr(exc)

        t0 = time.perf_counter()
        th = threading.Thread(target=call, daemon=True)
        th.start()
        th.join(30)  # measure the real latency, even beyond the limit
        lat = time.perf_counter() - t0
        latencies.append(lat)
        if "err" in box or th.is_alive():
            outcome["erreur"] += 1
            continue
        if lat > timeout:
            outcome["timeout"] += 1
            continue
        res = filt.check(clean_llm_output(str(box.get("out") or "")), kind, ctx)
        if res.ok:
            outcome["llm"] += 1
            accepted.append(res.text)
        else:
            outcome["rejet"] += 1
            reasons[(res.reason or "?").split(":")[0]] += 1
            rejected.append(f"[{kind}/{ctx['cible']}] {res.text!r} -> {res.reason}")
    lat_sorted = sorted(latencies)
    fallback = (n - outcome["llm"]) / n
    return {
        "modele": model, "prompt": style, "n": n, "timeout_s": timeout,
        "latence_p50_s": round(statistics.median(lat_sorted), 3),
        "latence_p95_s": round(lat_sorted[int(0.95 * (n - 1))], 3),
        "taux_ia": round(outcome["llm"] / n, 3),
        "taux_timeout": round(outcome["timeout"] / n, 3),
        "taux_rejet": round(outcome["rejet"] / n, 3),
        "taux_erreur": round(outcome["erreur"] / n, 3),
        "taux_reserve": round(fallback, 3),
        "raisons_rejet": dict(reasons),
        "exemples": accepted[:8],
        "exemples_rejetes": rejected[:12],
    }


def advice(r: dict) -> str:
    if "erreur" in r:
        return f"{r['modele']} : {r['erreur']} (ollama pull {r['modele']})"
    if r["taux_reserve"] <= FALLBACK_LIMIT:
        return f"OK : {r['taux_reserve']:.0%} de phrases de réserve (<= {FALLBACK_LIMIT:.0%})."
    tips = []
    if r["taux_timeout"] > 0.1:
        tips.append("trop lent : essayer --prompt court ou le modèle qwen2.5:0.5b")
    if r["taux_rejet"] > 0.1:
        tips.append(f"trop de rejets {r['raisons_rejet']} : simplifier le prompt / voir les "
                    "exemples, ou compléter le lexique si des bons mots sont refusés")
    head = f"ATTENTION : {r['taux_reserve']:.0%} de réserve (> {FALLBACK_LIMIT:.0%}). "
    return head + "; ".join(tips)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--modele", nargs="+", default=["qwen2.5:1.5b"])
    p.add_argument("--prompt", nargs="+", default=["normal"], choices=["normal", "court"])
    p.add_argument("-n", type=int, default=50)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    p.add_argument("--graine", type=int, default=1)
    p.add_argument("--sortie", type=Path, default=None, help="fichier JSON des résultats")
    a = p.parse_args(argv)
    results = []
    for model in a.modele:
        for style in a.prompt:
            print(f"\n=== {model} / prompt {style} ({a.n} requêtes) ===")
            r = run_one(model, style, a.n, a.timeout, a.graine)
            results.append(r)
            for k, v in r.items():
                if k not in ("modele", "prompt"):
                    print(f"  {k:16} {v}")
            print("  -> " + advice(r))
    if a.sortie:
        a.sortie.write_text(json.dumps(results, ensure_ascii=False, indent=2), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
