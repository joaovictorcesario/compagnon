"""Entry point: builds the modules and runs the loop.

python -m compagnon                       # V1 (prepared phrases only)
python -m compagnon --ia ollama           # V2 (local model + filter)"""

from __future__ import annotations

import argparse
import random
import threading
from pathlib import Path

from compagnon import phrases
from compagnon.adulte import CompanionMode, PinStore
from compagnon.enfant import ProfileStore
from compagnon.ia import (
    DEFAULT_TIMEOUT_S,
    AIService,
    OllamaRephraser,
    SentenceFilter,
    StubRephraser,
)
from compagnon.jeux import CATALOG, build_activities
from compagnon.reglages import DataPaths, Kind, RealClock, SettingsStore, default_data_dir
from compagnon.seance import SessionController, SessionLogger, new_log_path
from compagnon.voix import DEFAULT_VOICE, VOICE_PRESETS, RecordingVoice


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="compagnon", description="Compagnon virtuel (prototype S7)")
    p.add_argument("--profil", default="enfant1", help="pseudonyme de l'enfant (jamais son nom)")
    p.add_argument("--donnees", type=Path, default=None, help="dossier des données locales")
    p.add_argument("--ia", choices=["stub", "ollama"], default="stub")
    p.add_argument("--modele", default="qwen2.5:1.5b")
    p.add_argument("--prompt", choices=["normal", "court"], default="normal")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S)
    p.add_argument("--voix", default=None,
                   help=f"préréglage ({', '.join(VOICE_PRESETS)}) ou modèle Piper ; par défaut "
                        f"celle choisie dans le mode accompagnant ({DEFAULT_VOICE} au départ)")
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

    from compagnon.dessin import load_character
    from compagnon.ecran import GREETING, PygameDisplay
    from compagnon.voix import PygameVoice, load_engine

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
    ai = build_ai(args)

    if args.sans_voix:
        voice = RecordingVoice()
    else:
        voice_name = args.voix or companion.settings.voice
        engine = load_engine(paths.voices, voice_name)
        print(f"[voix] {engine.name if engine else 'aucune (texte seulement)'}")
        voice = PygameVoice(paths.tts_cache, engine,
                            engine_loader=lambda name: load_engine(paths.voices, name),
                            voice_name=voice_name)
        if args.voix:  # command line wins for this run
            companion.settings.voice = args.voix if args.voix in VOICE_PRESETS else voice_name
        texts = [GREETING, *phrases.ALL_FIXED]
        for entry in CATALOG.entries():
            texts += [entry.description, *entry.factory().fixed_phrases()]
        voice.preload(texts)

    display = PygameDisplay(companion.settings, companion, args.plein_ecran, paths.rewards,
                            load_character(args.personnage or paths.character),
                            speaking=getattr(voice, "is_speaking", None))
    voice.configure(companion.settings)
    rng = random.Random(args.graine)

    def new_session(activity_id: str) -> SessionController:
        """One session = the game chosen on the home screen."""
        logger = SessionLogger(None, clock)
        logger.path = new_log_path(paths.logs, profile.name, logger.session_id)
        print(f"[journal] {logger.path}")
        display.set_activity(CATALOG.get(activity_id) if activity_id in CATALOG else None)
        ctrl = SessionController(
            clock=clock, display=display, voice=voice, ai=ai,
            activities=build_activities([activity_id]),
            settings=companion.settings, profile=profile, logger=logger,
            profile_store=profile_store, rng=rng,
        )
        holder["ctrl"] = ctrl
        ctrl.start()
        return ctrl

    def home(greet: bool) -> None:
        display.show_menu(companion.visible_games())
        if greet:
            voice.say(GREETING)

    ctrl: SessionController | None = None
    home(greet=True)
    fps = pygame.time.Clock()
    running = True
    while running:
        for ev in display.poll_events():
            if ev.kind == Kind.QUIT:
                running = False
                break
            if ev.kind in (Kind.MENU, Kind.NEW_SESSION):  # back to the home screen
                if ctrl is not None:
                    ctrl.close("menu" if ev.kind == Kind.MENU else "nouvelle_seance")
                    ctrl = None
                    holder.pop("ctrl", None)
                voice.stop()
                home(greet=False)
                continue
            if ev.kind == Kind.START and ev.value:
                if ctrl is not None:
                    ctrl.close("nouvelle_seance")
                ctrl = new_session(ev.value)
                continue
            if ev.kind == Kind.DESCRIBE and ev.value in CATALOG:
                voice.say(CATALOG.get(ev.value).description)
                continue
            if ev.kind == Kind.ADULT_CLOSE:
                display.apply_settings(companion.settings)
                voice.configure(companion.settings)
                if ctrl is None:  # on the home screen: the adult may have changed the games
                    home(greet=False)
                else:
                    ctrl.update_settings(companion.settings)
            if ctrl is not None:
                ctrl.handle(ev)
        if ctrl is not None:
            ctrl.tick()
        display.render()
        fps.tick(30)
    if ctrl is not None:
        ctrl.close("quitter")
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
