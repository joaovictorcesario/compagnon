"""Le cerveau d'une séance : question, réponse, aide, pause, fin, journal.

Sommaire (chercher « PARTIE n ») :
  1. Ce que la séance demande à l'écran
  2. Niveaux d'aide
  3. Journal de séance
  4. Déroulement de la séance
"""

from __future__ import annotations

import json
import random
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum
from pathlib import Path
from typing import Protocol

from compagnon import phrases
from compagnon.enfant import (
    ChildProfile,
    ClickMonitor,
    EmotionSource,
    NullEmotionSource,
    ProfileStore,
    best_hint_level,
    order_activities,
    record_session,
    thresholds_for,
)
from compagnon.ia import AIService
from compagnon.jeux import Activity, Choice, ImageSpec, Item
from compagnon.reglages import CHILD_KINDS, Clock, InputEvent, Kind, Settings
from compagnon.voix import Voice

# ================================================================================================
# PARTIE 1 — CE QUE LA SÉANCE DEMANDE À L'ÉCRAN
# Display interface (FC7). The core talks ONLY to this. For the robot (S8), write a new
# class implementing it (face on a small screen + head motor); nothing else changes.
# ================================================================================================

EXPRESSIONS = ("neutre", "content", "encourage", "calme", "ecoute")


@dataclass(frozen=True)
class Scene:
    title: str  # current activity, always at the same place (FC1)
    text: str  # instruction text, shown together with voice and image (FC4)
    image: ImageSpec
    choices: tuple[Choice, ...]
    highlight: str | None = None  # visual hint, no blinking (FC2)
    expression: str = "neutre"


@dataclass(frozen=True)
class RewardView:
    kind: str  # "etoile" | "image" | "aucune"
    image_path: str = ""


class Display(Protocol):
    def announce_activity(self, title: str, text: str) -> None: ...

    def show_scene(self, scene: Scene) -> None: ...

    def set_expression(self, expression: str) -> None: ...

    def emphasize_instruction(self) -> None: ...  # instruction repeated: make it visible

    def show_reward(self, reward: RewardView) -> None: ...

    def propose_pause(self, text: str) -> None: ...

    def show_pause(self, text: str) -> None: ...

    def set_calm(self, calm: bool) -> None: ...

    def show_end(self, text: str) -> None: ...

    def apply_settings(self, settings: Settings) -> None: ...

    def poll_events(self) -> list[InputEvent]: ...


# ================================================================================================
# PARTIE 2 — NIVEAUX D'AIDE
# Help levels and difficulty (FP2).
#
# Two independent axes:
# * help level 0-5 for the current item (lightest to strongest);
# * difficulty 1-4 (number of choices), changed after N successes without help
#   or N errors in a row (N set by the adult).
# ================================================================================================

class HelpLevel(IntEnum):
    NONE = 0
    REPEAT = 1  # same instruction again
    REFORMULATE = 2  # simpler instruction (AI or prepared phrase)
    HINT = 3  # verbal hint (AI or prepared phrase)
    VISUAL = 4  # right answer gently highlighted (no blinking)
    MODEL = 5  # only 2 choices left, the character shows the answer


class Decision(Enum):
    NONE = "aucune"
    HARDER = "plus_difficile"
    HINT_THEN_EASIER = "indice_puis_plus_facile"


class Adaptation:
    def __init__(self, difficulty: int, max_difficulty: int, success_threshold: int,
                 error_threshold: int) -> None:
        self.max_difficulty = max_difficulty
        self.difficulty = max(1, min(max_difficulty, difficulty))
        self.success_threshold = success_threshold
        self.error_threshold = error_threshold
        self.success_streak = 0  # successes without help
        self.error_streak = 0
        self._pending = 0  # difficulty change applied at the next item

    def set_thresholds(self, success_threshold: int, error_threshold: int) -> None:
        self.success_threshold = success_threshold
        self.error_threshold = error_threshold

    def on_answer(self, correct: bool, used_help: bool) -> Decision:
        if correct:
            self.error_streak = 0
            if used_help:
                self.success_streak = 0
                return Decision.NONE
            self.success_streak += 1
            if self.success_streak >= self.success_threshold:
                self.success_streak = 0
                self._pending = +1
                return Decision.HARDER
            return Decision.NONE
        self.success_streak = 0
        self.error_streak += 1
        if self.error_streak >= self.error_threshold:
            self.error_streak = 0
            self._pending = -1
            return Decision.HINT_THEN_EASIER
        return Decision.NONE

    @property
    def next_difficulty(self) -> int:
        """Difficulty of the next item (pending change included), saved for next session."""
        return max(1, min(self.max_difficulty, self.difficulty + self._pending))

    def start_item(self) -> tuple[int, int] | None:
        """Apply a pending change. Returns (old, new) if the difficulty changed."""
        if not self._pending:
            return None
        old = self.difficulty
        self.difficulty = max(1, min(self.max_difficulty, self.difficulty + self._pending))
        self._pending = 0
        return (old, self.difficulty) if old != self.difficulty else None


# ================================================================================================
# PARTIE 3 — JOURNAL DE SÉANCE
# One JSON line per exchange, so the observer can check each reaction against the
# scenario. The child appears only under a pseudonym. Files stay on this computer.
# ================================================================================================

def new_log_path(log_dir: Path, profile_name: str, session_id: str) -> Path:
    from compagnon.enfant import safe_name

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


# ================================================================================================
# PARTIE 4 — DÉROULEMENT DE LA SÉANCE
# Session orchestrator. Pure and synchronous: it receives input events and clock ticks,
# and sends commands to the Display and Voice interfaces. No pygame, no real time here,
# so every scenario can be tested with a FakeClock.
# ================================================================================================

ANNOUNCE_S = 3.0  # time the activity announcement stays on screen (FC1)
FEEDBACK_S = 2.0  # time the reward stays before the next question


class Phase(str, Enum):
    IDLE = "attente"
    ANNOUNCE = "annonce"
    ASK = "question"
    FEEDBACK = "retour"
    PAUSE_OFFER = "pause_proposee"
    PAUSED = "pause"
    ADULT = "adulte"
    ENDED = "fin"


ACTIVE = frozenset({Phase.ANNOUNCE, Phase.ASK, Phase.FEEDBACK})


class SessionController:
    def __init__(self, *, clock: Clock, display: Display, voice: Voice, ai: AIService,
                 activities: list[Activity], settings: Settings, profile: ChildProfile,
                 logger: SessionLogger, profile_store: ProfileStore | None = None,
                 rng: random.Random | None = None, emotion: EmotionSource | None = None) -> None:
        self.clock, self.display, self.voice, self.ai = clock, display, voice, ai
        self.settings, self.profile, self.log = settings, profile, logger
        self.profile_store = profile_store
        self.rng = rng or random.Random()
        self.emotion = emotion or NullEmotionSource()

        learning = not profile.learning_paused
        by_id = {a.id: a for a in activities}
        self.activities = [by_id[i] for i in order_activities(list(by_id), profile)]
        self.activity_index = 0
        self.sensitivity = profile.sensitivity if learning else 0
        start = profile.level if (learning and profile.level) else settings.initial_level
        self.adapt = Adaptation(start, self.activity.max_difficulty,
                                settings.success_threshold, settings.error_threshold)
        self.th = thresholds_for(settings, self.sensitivity)
        self.clicks = ClickMonitor(self.th.clicks, self.th.window_s)

        self.phase = Phase.IDLE
        self._before_interrupt: Phase | None = None
        self.item: Item | None = None
        self.help_level = 0
        self.instruction = ""  # last instruction said (repeat button says it again)
        self.consecutive_errors = 0
        now = clock.now()
        self.last_input = self.last_prompt = self.last_pause_mark = now
        self.phase_until = now
        self.activity_start = now
        self.session_start = now
        self.items_done = 0
        self.help_used: Counter[int] = Counter()
        self.help_solved: Counter[int] = Counter()
        self.difficult_moments: list[str] = []
        self.hint_levels: list[int] = []
        self.activity_report: dict[str, dict[str, float]] = {}
        self.end_reason: str | None = None

    # ------------------------------------------------------------------ helpers
    @property
    def activity(self) -> Activity:
        return self.activities[self.activity_index]

    @property
    def difficulty(self) -> int:
        return self.adapt.difficulty

    def _now(self) -> float:
        return self.clock.now()

    def _say(self, text: str, role: str, source: str = "fixe", **extra: object) -> None:
        self.voice.say(text)
        self.log.log("dit", texte=text, role=role, source=source, **extra)

    def _visible_choices(self) -> tuple[Choice, ...]:
        assert self.item is not None
        if self.help_level >= HelpLevel.MODEL:
            return tuple(self.activity.model_choices(self.item))
        return tuple(self.item.choices)

    def _present(self, expression: str = "neutre") -> None:
        assert self.item is not None
        highlight = self.item.key if self.help_level >= HelpLevel.VISUAL else None
        self.display.show_scene(Scene(
            title=self.activity.title, text=self.instruction, image=self.item.image,
            choices=self._visible_choices(), highlight=highlight, expression=expression,
        ))

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self.log.log("debut_seance", profil=self.profile.name, difficulte=self.difficulty,
                     sensibilite=self.sensitivity,
                     apprentissage="pause" if self.profile.learning_paused else "actif",
                     activites=[a.id for a in self.activities], seuils=self.th.__dict__)
        self.display.apply_settings(self.settings)
        self.voice.configure(self.settings)
        now = self._now()
        self.last_input = self.last_pause_mark = now
        self._announce()

    def _announce(self) -> None:
        self.phase = Phase.ANNOUNCE
        self.activity_start = self._now()
        self.item = None
        self.display.announce_activity(self.activity.title, self.activity.announce_text)
        self._say(self.activity.announce_text, "annonce")
        self.phase_until = self._now() + ANNOUNCE_S

    def _next_item(self) -> None:
        change = self.adapt.start_item()
        if change:
            self.log.log("difficulte", avant=change[0], apres=change[1])
        self.item = self.activity.make_item(self.difficulty, self.rng)
        self.help_level = 0
        self.instruction = self.item.instruction
        self.phase = Phase.ASK
        self._present()
        self.log.log("question", cible=self.item.key, choix=[c.id for c in self.item.choices],
                     difficulte=self.difficulty)
        self._say(self.instruction, "consigne")
        self.last_prompt = self._now()

    def _activity_finished(self) -> bool:
        return (self.items_done >= self.settings.items_per_activity
                or self._now() - self.activity_start >= self.settings.activity_max_s)

    def _close_activity_report(self, completed: bool) -> None:
        self.activity_report[self.activity.id] = {
            "items": self.items_done, "seconds": self._now() - self.activity_start,
            "completed": completed,
        }

    # ------------------------------------------------------------------ clock
    def tick(self) -> None:
        est = self.emotion.poll() if self.emotion.enabled else None
        if est is not None:  # FP7 extension point: logged only, no reaction in S7
            self.log.log("emotion_estimee", label=est.label, confiance=est.confidence)
        now = self._now()
        if self.phase == Phase.ANNOUNCE and now >= self.phase_until:
            self._next_item()
        elif self.phase == Phase.FEEDBACK and now >= self.phase_until:
            self._after_feedback()
        elif self.phase == Phase.ASK:
            if now - self.last_input >= self.settings.silence_end_s:
                self.end("silence")
            elif now - self.last_prompt >= self.settings.silence_repeat_s:
                self._silence_repeat()
            elif (self.th.pause_interval_s
                  and now - self.last_pause_mark >= self.th.pause_interval_s):
                self.last_pause_mark = now
                self._offer_pause("planifiee", overload=False)

    def _after_feedback(self) -> None:
        if not self._activity_finished():
            self._next_item()
            return
        self._close_activity_report(completed=True)
        self.log.log("fin_activite", activite=self.activity.id, items=self.items_done)
        if self.activity_index + 1 < len(self.activities):
            self.activity_index += 1
            self.items_done = 0
            self._announce()  # every change of activity is announced (FC1)
        else:
            self.end("termine")

    # ------------------------------------------------------------------ input
    def handle(self, ev: InputEvent) -> None:
        t0 = time.perf_counter()
        before = self.phase
        self._dispatch(ev)
        self.log.log("evenement_entree", type=ev.kind.value, valeur=ev.value,
                     phase_avant=before.value, phase_apres=self.phase.value,
                     reaction_ms=round((time.perf_counter() - t0) * 1000, 2))

    def _dispatch(self, ev: InputEvent) -> None:
        if ev.kind == Kind.ADULT_OPEN:
            self._adult_open()
            return
        if ev.kind == Kind.ADULT_CLOSE:
            self._adult_close()
            return
        if self.phase in (Phase.IDLE, Phase.ENDED, Phase.ADULT) or ev.kind not in CHILD_KINDS:
            return
        now = self._now()
        if self.phase in ACTIVE and self.clicks.register(now):
            self._offer_pause("agitation", overload=True)
            return
        self.last_input = now

        if ev.kind == Kind.FINISHED:
            self.end("enfant")
        elif ev.kind == Kind.PAUSE:
            if self.phase in (Phase.PAUSED, ):
                self._resume()
            else:
                self._pause("enfant")
        elif ev.kind == Kind.CONTINUE:
            if self.phase in (Phase.PAUSED, Phase.PAUSE_OFFER):
                self._resume()
        elif self.phase == Phase.ASK:
            if ev.kind == Kind.CHOICE and ev.value is not None:
                self._answer(ev.value)
            elif ev.kind == Kind.HELP:
                self._give_help(min(HelpLevel.MODEL, self.help_level + 1), "bouton_aide")
            elif ev.kind == Kind.REPEAT:
                self.display.emphasize_instruction()
                self._say(self.instruction, "repetition")
                self.last_prompt = now
        elif self.phase == Phase.ANNOUNCE and ev.kind == Kind.REPEAT:
            self._say(self.activity.announce_text, "repetition")

    # ------------------------------------------------------------------ answers & help
    def _answer(self, choice_id: str) -> None:
        assert self.item is not None
        correct = self.activity.is_correct(self.item, choice_id)
        used_help = self.help_level > 0
        decision = self.adapt.on_answer(correct, used_help)
        self.log.log("reponse", choix=choice_id, cible=self.item.key, correcte=correct,
                     niveau_aide=self.help_level, decision=decision.value)
        if correct:
            self.consecutive_errors = 0
            if used_help:
                self.help_solved[self.help_level] += 1
            self.items_done += 1
            self._reward()
            self.phase = Phase.FEEDBACK
            self.phase_until = self._now() + FEEDBACK_S
            return
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.th.errors:
            self._offer_pause("erreurs", overload=True)
            return
        if decision == Decision.HINT_THEN_EASIER:
            level = max(self.help_level + 1, best_hint_level(self.profile), HelpLevel.HINT)
            level = min(HelpLevel.MODEL, level)
            self.hint_levels.append(level)
            self._give_help(level, "erreurs")
        else:
            self.display.set_expression("encourage")
            self._say(phrases.WRONG, "encouragement")
            self.last_prompt = self._now()

    def _reward(self) -> None:
        s = self.settings
        path = ""
        if s.reward == "image" and s.reward_image:
            path = s.reward_image
        if s.reward != "aucune":
            self.display.show_reward(RewardView(s.reward, path))
        self.display.set_expression("content")
        # No spoken praise (it became repetitive): always the same soft success sound,
        # predictable for the child (FC1). Silent if the adult turned sounds off.
        if s.sounds:
            self.voice.chime()
        self.log.log("recompense", visuelle=s.reward, son=s.sounds)

    def _give_help(self, level: int, trigger: str) -> None:
        assert self.item is not None
        self.help_level = level
        self.help_used[level] += 1
        ctx = self.activity.ai_context(self.item)
        source, extra = "fixe", {}
        if level == HelpLevel.REPEAT:
            pass  # same instruction, same words
        elif level in (HelpLevel.REFORMULATE, HelpLevel.HINT):
            kind = "simplifier" if level == HelpLevel.REFORMULATE else "indice"
            p = self.ai.rephrase(kind, ctx)
            self.instruction, source = p.text, p.source
            extra = {"latence_ia_ms": p.latency_ms, "rejet": p.reason, "brut": p.raw}
            self.log.log("ia", type=kind, source=p.source, texte=p.text,
                         latence_ms=p.latency_ms, rejet=p.reason, brut=p.raw)
        elif level == HelpLevel.VISUAL:
            self.instruction = phrases.VISUAL_HINT
        else:
            self.instruction = phrases.MODEL
        self.log.log("aide", niveau=level, declencheur=trigger)
        self._present(expression="encourage")
        self.display.emphasize_instruction()
        self._say(self.instruction, f"aide_{level}", source=source, **extra)
        self.last_prompt = self._now()

    def _silence_repeat(self) -> None:
        """No answer: say the instruction again, in a simpler way (level 2 at least)."""
        self.log.log("silence", secondes=round(self._now() - self.last_prompt, 1))
        if self.help_level < HelpLevel.REFORMULATE:
            self._give_help(HelpLevel.REFORMULATE, "silence")
        else:
            self.display.emphasize_instruction()
            self._say(self.instruction, "repetition_silence")
            self.last_prompt = self._now()

    # ------------------------------------------------------------------ pause & overload
    def _offer_pause(self, reason: str, overload: bool) -> None:
        self.log.log("surcharge" if overload else "pause_planifiee", raison=reason)
        self._before_interrupt = self.phase
        if overload:
            self.difficult_moments.append(reason)
            self.voice.stop()
            self.voice.set_muted(True)  # cut all sounds (FP5)
            self.display.set_calm(True)  # calm screen: muted colours, no animation
        self.clicks.reset()
        if self.settings.pause_mode == "automatique":
            self._enter_pause(reason)
            return
        self.phase = Phase.PAUSE_OFFER
        text = phrases.PAUSE_OFFER if overload else phrases.SCHEDULED_PAUSE_OFFER
        self.display.propose_pause(text)
        self._say(text, "proposition_pause")  # silent when muted, text stays on screen

    def _pause(self, reason: str) -> None:
        if self._before_interrupt is None or self.phase in ACTIVE:
            self._before_interrupt = self.phase
        self._enter_pause(reason)

    def _enter_pause(self, reason: str) -> None:
        self.voice.stop()
        self.display.set_calm(True)
        self.phase = Phase.PAUSED
        self.display.show_pause(phrases.PAUSE)
        self.log.log("pause", raison=reason)

    def _resume(self) -> None:
        """Back to exactly the same point: same question, same choices, same help."""
        before = self._before_interrupt or Phase.ASK
        self._before_interrupt = None
        self.voice.set_muted(False)
        self.display.set_calm(False)
        self.clicks.reset()
        now = self._now()
        self.last_input = self.last_prompt = self.last_pause_mark = now
        self.log.log("reprise", vers=before.value)
        if before == Phase.ANNOUNCE or self.item is None:
            self._announce()
        elif before == Phase.FEEDBACK:
            self._after_feedback()
        else:
            self.phase = Phase.ASK
            self._present()
            self._say(self.instruction, "reprise")

    # ------------------------------------------------------------------ adult mode
    def _adult_open(self) -> None:
        if self.phase == Phase.ADULT:
            return
        self._adult_before = self.phase
        self.voice.stop()
        self.phase = Phase.ADULT
        self.log.log("mode_adulte", ouvert=True)

    def _adult_close(self) -> None:
        if self.phase != Phase.ADULT:
            return
        before = getattr(self, "_adult_before", Phase.ASK)
        self.log.log("mode_adulte", ouvert=False)
        if before == Phase.ENDED:
            self.phase = Phase.ENDED
            self.display.show_end(phrases.END_ADULT)
        elif before in (Phase.PAUSED, Phase.PAUSE_OFFER):
            self.phase = Phase.PAUSED
            self.display.show_pause(phrases.PAUSE)
        elif before == Phase.IDLE:
            self.phase = Phase.IDLE
        else:
            self._before_interrupt = before
            self._resume()

    def update_settings(self, settings: Settings) -> None:
        self.settings = settings
        self.adapt.set_thresholds(settings.success_threshold, settings.error_threshold)
        self.th = thresholds_for(settings, self.sensitivity)
        self.clicks = ClickMonitor(self.th.clicks, self.th.window_s)
        self.display.apply_settings(settings)
        self.voice.configure(settings)
        self.log.log("reglages_appliques")

    # ------------------------------------------------------------------ end
    def end(self, reason: str) -> None:
        if self.phase == Phase.ENDED:
            return
        self.voice.stop()
        text = {
            "enfant": phrases.END_CHILD,
            "silence": phrases.END_SILENCE,
            "termine": self.activity.end_text,
        }.get(reason, phrases.END_ADULT)
        if reason == "silence":
            self.difficult_moments.append("absence de réponse")
        if self.activity.id not in self.activity_report:
            self._close_activity_report(completed=(reason == "termine"))
        self.phase = Phase.ENDED
        self.end_reason = reason
        self.display.set_expression("calme" if reason != "termine" else "content")
        self.display.show_end(text)
        self._say(text, "fin")
        self._finalize()

    def close(self, reason: str = "adulte") -> None:
        """End without speaking (new session or quit from adult mode)."""
        if self.phase == Phase.ENDED:
            return
        if self.activity.id not in self.activity_report:
            self._close_activity_report(completed=False)
        self.phase = Phase.ENDED
        self.end_reason = reason
        self.voice.stop()
        self._finalize()

    def _finalize(self) -> None:
        updated = record_session(
            self.profile, session_id=self.log.session_id,
            date=datetime.now().strftime("%d/%m/%Y %H:%M"), difficulty=self.adapt.next_difficulty,
            help_used=dict(self.help_used), help_solved=dict(self.help_solved),
            activities=self.activity_report, difficult_moments=self.difficult_moments,
            hint_levels=self.hint_levels,
        )
        if updated and self.profile_store is not None:
            self.profile_store.save(self.profile)
        self.log.log("fin_seance", raison=self.end_reason, items=self.items_done,
                     difficulte=self.difficulty, moments_difficiles=self.difficult_moments,
                     profil_mis_a_jour=updated,
                     duree_s=round(self._now() - self.session_start, 1))
