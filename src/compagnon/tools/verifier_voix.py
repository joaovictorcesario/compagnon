"""Check the voice: where the models are looked for, which one loads, and say a sentence.

    python -m compagnon.tools.verifier_voix
    python -m compagnon.tools.verifier_voix --voix jessica-douce
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from compagnon.core.settings import Settings
from compagnon.paths import DataPaths, default_data_dir
from compagnon.voice.presets import DEFAULT_VOICE, VOICE_PRESETS, resolve_voice


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--voix", default=DEFAULT_VOICE, help=", ".join(VOICE_PRESETS))
    p.add_argument("--texte", default="Bonjour ! Touche le ballon rouge.")
    a = p.parse_args(argv)
    from compagnon.voice.audio import PygameVoice, load_engine, voice_dirs

    paths = DataPaths(default_data_dir())
    model = resolve_voice(a.voix).model
    for d in voice_dirs(paths.voices):
        print(f"  {'OK ' if (d / f'{model}.onnx').exists() else '-- '} {d}")
    engine = load_engine(paths.voices, a.voix)
    if engine is None:
        return 1
    print(f"[voix] {engine.name}")
    voice = PygameVoice(Path(tempfile.mkdtemp()), engine)
    voice.configure(Settings())
    t0 = time.perf_counter()
    voice.say(a.texte)
    print(f"[voix] « {a.texte} » ({(time.perf_counter() - t0) * 1000:.0f} ms)")
    time.sleep(3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
