"""The driving music is authored by a script (`P3-97`, `Q246`): the committed files are its."""

from __future__ import annotations

import importlib.util
import re
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


BGM = _load("make_bgm")
RENDERED = BGM.rendered()
TRES = (ROOT / "game/tuning/music.tres").read_text()


def _samples(name: str) -> np.ndarray:
    """A file's samples, a row a frame and a column a channel."""
    frames, channels = RENDERED[name]
    return np.frombuffer(frames, "<i2").astype(float).reshape(-1, channels)


def _tres_list(key: str) -> list[str]:
    """A packed array's entries out of `music.tres`, as written."""
    found = re.search(rf"^{key} = Packed\w+Array\((.*)\)$", TRES, re.MULTILINE)
    assert found is not None, key
    return [entry.strip().strip('"') for entry in found.group(1).split(",")]


@pytest.mark.parametrize("name", sorted(RENDERED))
def test_the_committed_file_is_what_the_script_writes(name: str) -> None:
    frames, channels = RENDERED[name]
    with wave.open(str(BGM.OUT_DIR / f"{name}.wav"), "rb") as committed:
        assert committed.getframerate() == BGM.RATE_HZ
        assert committed.getnchannels() == channels
        assert committed.readframes(committed.getnframes()) == frames


@pytest.mark.parametrize("name", sorted(RENDERED))
def test_a_loop_joins_itself_without_a_step(name: str) -> None:
    """The step from the last frame back to the first is no bigger than the loop's own."""
    samples = _samples(name)
    join = np.abs(samples[0] - samples[-1]).max()
    assert join <= np.abs(np.diff(samples, axis=0)).max()


@pytest.mark.parametrize("name", sorted(RENDERED))
def test_a_loop_carries_its_loop_for_the_importer(name: str) -> None:
    """Godot reads the `smpl` chunk ("Detect From WAV"): one forward loop over the whole file."""
    data = (BGM.OUT_DIR / f"{name}.wav").read_bytes()
    at = data.index(b"smpl")
    loops = struct.unpack_from("<I", data, at + 8 + 28)[0]
    kind, start, end = struct.unpack_from("<3I", data, at + 8 + 36 + 4)
    assert (loops, kind, start, end) == (1, 0, 0, _samples(name).shape[0] - 1)
    assert struct.unpack_from("<I", data, 4)[0] == len(data) - 8


def test_every_file_is_a_whole_share_of_the_bed() -> None:
    """They play locked together: a layer that did not divide the bed would drift against it."""
    for name in RENDERED:
        rows = _samples(name).shape[0]
        if name.removeprefix("bgm_") in BGM.MOODS:
            assert rows == BGM.ROWS
        else:
            assert BGM.ROWS % rows == 0


def test_every_layer_at_its_top_over_the_loudest_bed_does_not_clip() -> None:
    """The files share one scale, set so the fullest mix the table can ask for peaks at `PEAK`."""
    signals = BGM.signals()
    loudest = 0.0
    for mood, look in BGM.MOODS.items():
        mix = signals[f"bgm_{mood}"].copy()
        for stem, level in zip(BGM.STEMS, BGM.FULL, strict=True):
            layer = signals[BGM.layer_name(stem, look["chords"])]
            mix += level * np.resize(layer, BGM.ROWS)[:, None]
        loudest = max(loudest, float(np.abs(mix).max()))
    assert loudest == pytest.approx(BGM.PEAK, abs=1e-6)


def test_the_table_names_the_files_the_script_writes() -> None:
    """`music.tres` mirrors the script's moods, sides and layers by hand, so hold the mirror."""
    assert _tres_list("moods") == list(BGM.MOODS)
    assert _tres_list("mood_side") == [look["chords"] for look in BGM.MOODS.values()]
    assert _tres_list("stems") == list(BGM.STEMS)
    assert _tres_list("sided_stems") == list(BGM.TONAL)


def test_the_script_scales_against_the_table_s_top_row() -> None:
    """`FULL` is the last `tiers` row: a louder row in the table would clip the mix."""
    tiers = [float(entry) for entry in _tres_list("tiers")]
    assert tiers[-len(BGM.STEMS) :] == list(BGM.FULL)
    assert max(tiers) == max(BGM.FULL)
