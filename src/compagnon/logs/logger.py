"""One JSON line per exchange, so the observer can check each reaction against the
scenario. The child appears only under a pseudonym. Files stay on this computer."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from compagnon.core.clock import Clock


def new_log_path(log_dir: Path, profile_name: str, session_id: str) -> Path:
    from compagnon.child.profile import safe_name

    stamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
    return log_dir / f"{stamp}_{safe_name(profile_name)}_{session_id}.jsonl"


class SessionLogger:
    def __init__(self, path: Path | None, clock: Clock, session_id: str | None = None) -> None:
        self.path = path
        self.clock = clock
        self.session_id = session_id or uuid.uuid4().hex[:8]
        self.t0 = clock.now()
        self.records: list[dict] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **data: object) -> dict:
        rec = {
            "heure": datetime.now().isoformat(timespec="milliseconds"),
            "t": round(self.clock.now() - self.t0, 2),
            "seance": self.session_id,
            "evenement": event,
            **data,
        }
        self.records.append(rec)
        if self.path is not None:
            # open/close each time: no file handle kept, so logs can be deleted at any time
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def events(self, name: str) -> list[dict]:
        return [r for r in self.records if r["evenement"] == name]
