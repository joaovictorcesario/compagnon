"""Entry point: builds the modules and runs the loop.

    python -m compagnon                       # V1 (prepared phrases only)
    python -m compagnon --ia ollama           # V2 (local model + filter)
"""

from __future__ import annotations

import argparse
import random
import threading
from pathlib import Path

from compagnon.activities import build_activities
from compagnon.ai import AIService, OllamaRephraser, SentenceFilter, StubRephraser
from compagnon.ai.service import DEFAULT_TIMEOUT_S
from compagnon.child import ProfileStore
from compagnon.companion import CompanionMode, PinStore
from compagnon.core import phrases
from compagnon.core.clock import RealClock
from compagnon.core.controller import SessionController
from compagnon.core.events import Kind
from compagnon.core.settings import SettingsStore
from compagnon.logs import SessionLogger, new_log_path
from compagnon.paths import DataPaths, default_data_dir
from compagnon.voice import RecordingVoice
from compagnon.voice.presets import DEFAULT_VOICE, VOICE_PRESETS


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="compagnon", description="Compagnon virtuel (prototype S7)")
    p.add_argument("--profil", default="enfant1", help="pseudonyme de l'enfant (jamais son nom)")
    p.add_argument("--donnees", type=Path, default=None, help="dossier des données locales")
    p.add_argument("--ia", choices=["stub", "ollama"], default="stub")
    p.add_argument("--modele", default="qwen2.5:1.5b")
    p.add_argument("--prompt", choices=["normal", "court"], default="normal")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    p.add_argument("--voix", default=DEFAULT_VOICE,
                   help=f"préréglage ({', '.join(VOICE_PRESETS)}) ou modèle Piper")
    p.add_argument("--personnage", type=Path, default=None,
                   help="dossier d'images du personnage (neutre.png, content.png...)")
    p.add_argument("--sans-voix", action="store_true")
    p.add_argument("--plein-ecran", action="store_true")
    p.add_argument("--graine", type=int, default=None, help="graine aléatoire (démo reproductible)")
    return p.parse_args(argv)


def build_ai(args: argparse.Namespace) -> AIService:
    filt = SentenceFilter.default()
    if args.ia != "ollama":
        return AIService(StubRephraser(), filt, args.timeout)
    reph = OllamaRephraser(model=args.modele, prompt_style=args.prompt)
    if not reph.available():
        print(f"[ia] Ollama ou le modèle « {args.modele} » est introuvable : "
              "phrases préparées uniquement. (voir README, section V2)")
        return AIService(StubRephraser(), filt, args.timeout)

    def warm() -> None:
        try:
            reph.warmup()
            print(f"[ia] modèle {args.modele} chargé")
        except OSError as exc:
            print(f"[ia] préchargement impossible : {exc}")

    threading.Thread(target=warm, daemon=True).start()
    return AIService(reph, filt, args.timeout)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    import pygame

    from compagnon.display.character import load_character
    from compagnon.display.pygame_display import PygameDisplay
    from compagnon.voice.audio import PygameVoice, load_engine

    paths = DataPaths(args.donnees or default_data_dir()).ensure()
    print(f"[données] {paths.root}")
    clock = RealClock()
    settings_store = SettingsStore(paths.settings)
    profile_store = ProfileStore(paths.profiles)
    profile = profile_store.load(args.profil)
    holder: dict[str, SessionController] = {}

    def adult_action(name: str, **data: object) -> None:
        if "ctrl" in holder:
            holder["ctrl"].log.log("action_adulte", action=name, **data)

    companion = CompanionMode(paths=paths, settings_store=settings_store,
                              pin_store=PinStore(paths.pin), profile_store=profile_store,
                              profile=profile, clock=clock, on_action=adult_action)
    display = PygameDisplay(companion.settings, companion, args.plein_ecran, paths.rewards,
                            load_character(args.personnage or paths.character))
    ai = build_ai(args)
    activities = build_activities(companion.settings.activities)

    if args.sans_voix:
        voice = RecordingVoice()
    else:
        engine = load_engine(paths.voices, args.voix)
        print(f"[voix] {engine.name if engine else 'aucune (texte seulement)'}")
        voice = PygameVoice(paths.tts_cache, engine)
        texts = list(phrases.ALL_FIXED)
        for a in activities:
            texts += a.fixed_phrases()
        voice.preload(texts)

    rng = random.Random(args.graine)

    def new_session() -> SessionController:
        logger = SessionLogger(None, clock)
        logger.path = new_log_path(paths.logs, profile.name, logger.session_id)
        print(f"[journal] {logger.path}")
        ctrl = SessionController(
            clock=clock, display=display, voice=voice, ai=ai,
            activities=build_activities(companion.settings.activities),
            settings=companion.settings, profile=profile, logger=logger,
            profile_store=profile_store, rng=rng,
        )
        holder["ctrl"] = ctrl
        ctrl.start()
        return ctrl

    ctrl = new_session()
    fps = pygame.time.Clock()
    running = True
    while running:
        for ev in display.poll_events():
            if ev.kind == Kind.QUIT:
                running = False
                break
            if ev.kind == Kind.NEW_SESSION:
                ctrl.close("nouvelle_seance")
                ctrl = new_session()
                continue
            if ev.kind == Kind.ADULT_CLOSE:
                ctrl.update_settings(companion.settings)
            ctrl.handle(ev)
        ctrl.tick()
        display.render()
        fps.tick(30)
    ctrl.close("quitter")
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
