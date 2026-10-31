"""The bell is authored by a script (`P3-4`): the committed file is what it writes."""

from __future__ import annotations

import importlib.util
import wave
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
_SPEC = importlib.util.spec_from_file_location("make_tram_bell", ROOT / "tools/make_tram_bell.py")
assert _SPEC is not None and _SPEC.loader is not None
make_tram_bell = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(make_tram_bell)


def test_the_committed_bell_is_what_the_script_writes() -> None:
    with wave.open(str(make_tram_bell.OUT), "rb") as committed:
        assert committed.getframerate() == make_tram_bell.RATE_HZ
        assert committed.getnchannels() == 1
        assert committed.readframes(committed.getnframes()) == make_tram_bell.samples()


def test_it_strikes_twice_and_dies_away() -> None:
    def level(start_s: float, span_s: float = 0.01) -> float:
        rows = range(
            int(start_s * make_tram_bell.RATE_HZ), int((start_s + span_s) * make_tram_bell.RATE_HZ)
        )
        return max(abs(make_tram_bell.sample(row / make_tram_bell.RATE_HZ)) for row in rows)

    assert level(0.23) < level(0.245)
    assert level(1.05) < 0.05 * level(0.0)
