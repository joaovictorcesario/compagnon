from compagnon.core.settings import VOICE_CHOICES, Settings
from compagnon.voice.presets import DEFAULT_VOICE, VOICE_PRESETS, resolve_voice
from compagnon.voice.sounds import ATTACK_S, PEAK, success_samples


def test_presets():
    assert DEFAULT_VOICE == "jessica" == Settings().voice
    assert set(VOICE_CHOICES) == set(VOICE_PRESETS)  # adult mode offers every preset
    assert resolve_voice("siwis-douce").semitones == 3
    assert resolve_voice("fr_FR-tom-medium").model == "fr_FR-tom-medium"


def test_success_sound_is_soft():
    rate = 22050
    s = success_samples(rate)
    assert abs(len(s) / rate - 1.2) < 0.01
    assert max(abs(v) for v in s) <= PEAK + 1e-9  # low level
    assert abs(s[0]) < 1e-6 and abs(s[-1]) < 0.01  # starts and ends in silence
    first_ms = s[: int(rate * ATTACK_S / 2)]
    assert max(abs(v) for v in first_ms) < PEAK * 0.6  # gradual attack, no click
