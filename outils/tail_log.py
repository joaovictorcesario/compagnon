"""Live view of the session log for the observer during a role-play test.

    python outils/tail_log.py            # follows the newest log
    python outils/tail_log.py fichier.jsonl
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from compagnon.reglages import default_data_dir

SHOW = {
    "debut_seance", "question", "reponse", "dit", "aide", "ia", "silence", "surcharge",
    "pause_planifiee", "pause", "reprise", "difficulte", "fin_activite", "fin_seance",
    "mode_adulte", "action_adulte",
}


def fmt(r: dict) -> str | None:
    ev = r["evenement"]
    if ev not in SHOW:
        return None
    t = f"[{r['t']:7.1f} s]"
    if ev == "dit":
        src = r.get("source", "")
        tag = {"llm": "IA ", "reserve": "RES"}.get(src, "   ")
        return f"{t} {tag} « {r['texte']} »  ({r.get('role')})"
    if ev == "ia":
        extra = f"  rejet={r['rejet']}" if r.get("rejet") else ""
        return (f"{t} IA   {r['type']}: source={r['source']} {r['latence_ms']} ms{extra}"
                f"  brut={r.get('brut')!r}")
    keys = {k: v for k, v in r.items() if k not in ("heure", "t", "seance", "evenement")}
    return f"{t} {ev.upper():14} {keys}"


def newest(log_dir: Path) -> Path | None:
    files = sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else newest(default_data_dir() / "journaux")
    if path is None:
        print("Aucun journal. Lancez d'abord le compagnon.")
        return 1
    print(f"Journal : {path}\n")
    pos = 0
    try:
        while True:
            with path.open(encoding="utf-8") as f:
                f.seek(pos)
                for line in f:
                    line = fmt(json.loads(line))
                    if line:
                        print(line, flush=True)
                pos = f.tell()
            time.sleep(0.3)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
