"""The sounds are authored by scripts (`Q178`, `P3-79`): the committed file is what they write."""

from __future__ import annotations

import importlib.util
import struct
import wave
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

ROOT = Path(__file__).parent.parent.parent


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / f"tools/{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BEEP = _load("make_meter_beep")
SOUNDS = _load("make_vehicle_sounds")
RENDERED = SOUNDS.rendered()


def test_the_committed_beep_is_what_the_script_writes() -> None:
    with wave.open(str(BEEP.OUT), "rb") as committed:
        assert committed.getframerate() == BEEP.RATE_HZ
        assert committed.getnchannels() == 1
        assert committed.readframes(committed.getnframes()) == BEEP.samples()


def test_the_beep_starts_and_ends_silent_so_nothing_clicks() -> None:
    assert BEEP.sample(0.0) == 0.0
    assert BEEP.sample(BEEP.LENGTH_S) == 0.0


@pytest.mark.parametrize("name", sorted(RENDERED))
def test_the_committed_sound_is_what_the_script_writes(name: str) -> None:
    frames, _loop = RENDERED[name]
    with wave.open(str(SOUNDS.OUT_DIR / f"{name}.wav"), "rb") as committed:
        assert committed.getframerate() == SOUNDS.RATE_HZ
        assert committed.getnchannels() == 1
        assert committed.readframes(committed.getnframes()) == frames


def _samples(name: str) -> np.ndarray:
    return np.frombuffer(RENDERED[name][0], "<i2").astype(float)


@pytest.mark.parametrize("name", sorted(SOUNDS.SHOTS))
def test_a_one_shot_starts_and_ends_silent_so_nothing_clicks(name: str) -> None:
    samples = _samples(name)
    assert samples[0] == 0.0
    assert samples[-1] == 0.0


@pytest.mark.parametrize("name", sorted(SOUNDS.LOOPS))
def test_a_loop_joins_itself_without_a_step(name: str) -> None:
    """The step from the last sample back to the first is no bigger than the loop's own steps."""
    samples = _samples(name)
    join = abs(samples[0] - samples[-1])
    assert join <= np.max(np.abs(np.diff(samples)))


@pytest.mark.parametrize("name", sorted(SOUNDS.LOOPS))
def test_a_loop_carries_its_loop_for_the_importer(name: str) -> None:
    """Godot reads the `smpl` chunk ("Detect From WAV"): one forward loop over the whole file."""
    data = (SOUNDS.OUT_DIR / f"{name}.wav").read_bytes()
    at = data.index(b"smpl")
    loops = struct.unpack_from("<I", data, at + 8 + 28)[0]
    kind, start, end = struct.unpack_from("<3I", data, at + 8 + 36 + 4)
    assert (loops, kind, start, end) == (1, 0, 0, len(RENDERED[name][0]) // 2 - 1)
    assert struct.unpack_from("<I", data, 4)[0] == len(data) - 8


@pytest.mark.parametrize("name", sorted(SOUNDS.SHOTS))
def test_a_one_shot_does_not_loop(name: str) -> None:
    assert b"smpl" not in (SOUNDS.OUT_DIR / f"{name}.wav").read_bytes()


def test_every_engine_loop_is_whole_engine_cycles() -> None:
    for rpm in SOUNDS.ENGINE_RPMS:
        cycle = SOUNDS.RATE_HZ * 120.0 / rpm
        assert cycle == round(cycle)
        assert _samples(f"engine_{int(rpm)}").size % round(cycle) == 0


def test_every_horn_tone_sits_on_its_loop_grid() -> None:
    grid = 1.0 / SOUNDS.HORN_LOOP_S
    for tones, _harmonics, _air, _peak in SOUNDS.HORNS.values():
        for tone in tones:
            assert tone / grid == round(tone / grid)


def test_every_kind_the_traffic_draws_has_its_own_horn() -> None:
    tres = (ROOT / "game/tuning/traffic.tres").read_text()
    block = tres[tres.index("kinds = ") : tres.index("})", tres.index("kinds = "))]
    kinds = {line.split('"')[1] for line in block.splitlines() if line.startswith('"')}
    assert kinds <= set(SOUNDS.HORNS)
    # The routed buses (`P3-78`) are not in the draw, and have their own.
    assert "bus" in SOUNDS.HORNS


def _gd_list(name: str) -> set[str]:
    """A `PackedStringArray` constant's strings, out of `verify_vehicle.gd`."""
    source = (ROOT / "game/tools/verify_vehicle.gd").read_text()
    start = source.index(f"const {name}: PackedStringArray = [")
    block = source[start : source.index("]", start)]
    return set(block.split('"')[1::2])


def test_the_verify_tool_loads_every_file_in_its_shape() -> None:
    """`verify_vehicle` mirrors this script's two tables by hand, so hold the mirror."""
    assert _gd_list("AUDIO_LOOPS") == set(SOUNDS.LOOPS)
    assert _gd_list("AUDIO_SHOTS") == set(SOUNDS.SHOTS) | {"meter_beep", "tram_bell"}
