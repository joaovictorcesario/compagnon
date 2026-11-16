"""Child profile and learning across sessions (FP6).

* the next session resumes the difficulty, the helps that worked, the preferred activities;
* after a difficult moment, questions are queued for the ADULT (never shown to the child);
* the adult can pause learning (nothing is updated) and factory-reset (all learned data
  erased; logs are kept, they have their own delete button).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from compagnon.overload.detector import MAX_SENSITIVITY

HINT_LEVELS = (3, 4, 5)

QUESTION_CRISIS = "Était-ce une crise ?"
QUESTION_HELP = "Cette aide a-t-elle marché ?"


@dataclass
class ChildProfile:
    name: str
    level: int | None = None  # last difficulty reached
    sensitivity: int = 0  # 0..MAX_SENSITIVITY, raised by "crise = oui"
    learning_paused: bool = False
    sessions: int = 0
    # help level (as str) -> {"used", "solved", "adult_yes", "adult_no"}
    help_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    # activity id -> {"sessions", "completed", "items", "seconds"}
    activity_stats: dict[str, dict[str, float]] = field(default_factory=dict)
    pending_questions: list[dict] = field(default_factory=list)

    def reset_learned(self) -> None:
        """Factory reset, in place (other objects keep a reference to this profile)."""
        fresh = ChildProfile(self.name)
        for f in fields(self):
            setattr(self, f.name, getattr(fresh, f.name))

    @classmethod
    def from_dict(cls, data: dict) -> ChildProfile:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)[:40] or "enfant"


class ProfileStore:
    def __init__(self, directory: Path) -> None:
        self.dir = directory

    def _path(self, name: str) -> Path:
        return self.dir / f"{safe_name(name)}.json"

    def load(self, name: str) -> ChildProfile:
        p = self._path(name)
        if p.exists():
            try:
                return ChildProfile.from_dict(json.loads(p.read_text("utf-8")))
            except (OSError, ValueError, TypeError):
                pass
        return ChildProfile(name)

    def save(self, profile: ChildProfile) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        p = self._path(profile.name)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2), "utf-8")
        os.replace(tmp, p)

    def delete_all(self) -> None:
        if self.dir.exists():
            for p in self.dir.glob("*.json"):
                p.unlink()


def _stat(profile: ChildProfile, level: int) -> dict[str, int]:
    return profile.help_stats.setdefault(
        str(level), {"used": 0, "solved": 0, "adult_yes": 0, "adult_no": 0})


def best_hint_level(profile: ChildProfile) -> int:
    """Which help to give after N errors: the one that worked best for this child (default 3)."""
    if profile.learning_paused:
        return 3
    best, best_score = 3, None
    for level in HINT_LEVELS:
        s = profile.help_stats.get(str(level))
        if not s or (s["used"] < 2 and not s["adult_yes"] and not s["adult_no"]):
            continue
        score = s["solved"] / max(1, s["used"]) + 0.5 * s["adult_yes"] - 0.5 * s["adult_no"]
        if best_score is None or score > best_score:
            best, best_score = level, score
    return best


def order_activities(activity_ids: list[str], profile: ChildProfile) -> list[str]:
    """Preferred activities first (completed more often, then played longer)."""
    if profile.learning_paused:
        return list(activity_ids)

    def score(aid: str) -> tuple[float, float]:
        s = profile.activity_stats.get(aid, {})
        sessions = max(1.0, s.get("sessions", 0))
        return (s.get("completed", 0) / sessions, s.get("seconds", 0) / sessions)

    return sorted(activity_ids, key=score, reverse=True)


def record_session(profile: ChildProfile, *, session_id: str, date: str, difficulty: int,
                   help_used: dict[int, int], help_solved: dict[int, int],
                   activities: dict[str, dict[str, float]], difficult_moments: list[str],
                   hint_levels: list[int]) -> bool:
    """Update the profile at the end of a session. Does nothing while learning is paused."""
    if profile.learning_paused:
        return False
    profile.sessions += 1
    profile.level = difficulty
    for level, n in help_used.items():
        _stat(profile, level)["used"] += n
    for level, n in help_solved.items():
        _stat(profile, level)["solved"] += n
    for aid, s in activities.items():
        acc = profile.activity_stats.setdefault(
            aid, {"sessions": 0, "completed": 0, "items": 0, "seconds": 0})
        acc["sessions"] += 1
        acc["completed"] += 1 if s.get("completed") else 0
        acc["items"] += s.get("items", 0)
        acc["seconds"] += round(s.get("seconds", 0), 1)
    if difficult_moments:
        profile.pending_questions.append({
            "id": uuid.uuid4().hex[:8], "type": "crise", "texte": QUESTION_CRISIS,
            "contexte": "Moment difficile : " + ", ".join(difficult_moments),
            "session": session_id, "date": date,
        })
    if hint_levels:
        level = hint_levels[-1]
        profile.pending_questions.append({
            "id": uuid.uuid4().hex[:8], "type": "aide", "texte": QUESTION_HELP,
            "contexte": f"Aide de niveau {level} donnée après plusieurs essais",
            "niveau": level, "session": session_id, "date": date,
        })
    return True


def apply_answer(profile: ChildProfile, question_id: str, yes: bool) -> bool:
    """Use the adult's answer. Returns True if the profile was changed."""
    q = next((q for q in profile.pending_questions if q["id"] == question_id), None)
    if q is None:
        return False
    profile.pending_questions.remove(q)
    if profile.learning_paused:
        return False
    if q["type"] == "crise" and yes:
        profile.sensitivity = min(MAX_SENSITIVITY, profile.sensitivity + 1)
    elif q["type"] == "aide":
        _stat(profile, int(q["niveau"]))["adult_yes" if yes else "adult_no"] += 1
    return True
