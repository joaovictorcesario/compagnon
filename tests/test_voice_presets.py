from compagnon.voice.presets import DEFAULT_VOICE, VOICE_PRESETS, resolve_voice


def test_presets():
    assert DEFAULT_VOICE in VOICE_PRESETS
    assert resolve_voice("siwis-douce").semitones == 3
    assert resolve_voice("fr_FR-tom-medium").model == "fr_FR-tom-medium"
