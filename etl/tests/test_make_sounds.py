"""The horn and the beep are authored by scripts (`Q178`): the committed file is what they write."""

from __future__ import annotations

import importlib.util
import wave
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parent.parent.parent


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / f"tools/{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["make_car_horn", "make_meter_beep"])
def test_the_committed_sound_is_what_the_script_writes(name: str) -> None:
    module = _load(name)
    with wave.open(str(module.OUT), "rb") as committed:
        assert committed.getframerate() == module.RATE_HZ
        assert committed.getnchannels() == 1
        assert committed.readframes(committed.getnframes()) == module.samples()


@pytest.mark.parametrize("name", ["make_car_horn", "make_meter_beep"])
def test_it_starts_and_ends_silent_so_nothing_clicks(name: str) -> None:
    module = _load(name)
    assert module.sample(0.0) == 0.0
    assert module.sample(module.LENGTH_S) == 0.0


def test_the_horn_holds_its_level_through_the_press() -> None:
    horn = _load("make_car_horn")

    def level(start_s: float, span_s: float = 0.02) -> float:
        rows = range(int(start_s * horn.RATE_HZ), int((start_s + span_s) * horn.RATE_HZ))
        return max(abs(horn.sample(row / horn.RATE_HZ)) for row in rows)

    assert level(0.1) == pytest.approx(level(0.3), rel=0.35)
    assert level(horn.LENGTH_S - 0.005, 0.004) < 0.25 * level(0.1)
