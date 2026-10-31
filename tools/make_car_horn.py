#!/usr/bin/env python3
"""Synthesise a car's horn: `game/assets/authored/audio/car_horn.wav` (`Q178`).

One short press of a twin-note electric horn: two reedy tones a minor third apart,
each a stack of harmonics falling away. Authored, not recorded, so it comes under the
hand-authored licence with nothing to attribute. Byte-identical each run: no noise,
no clock.

    python tools/make_car_horn.py
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

RATE_HZ = 22050
LENGTH_S = 0.42
PEAK = 0.8
# A car's two horns, the low and the high.
TONES_HZ = (415.0, 494.0)
# A diaphragm horn is reedy, so its harmonics stand well up.
HARMONICS = (1.0, 0.8, 0.6, 0.45, 0.3, 0.2)
# The press and the release: no click at either end.
ATTACK_S = 0.012
RELEASE_S = 0.05
OUT = Path(__file__).parent.parent / "game/assets/authored/audio/car_horn.wav"


def sample(t: float) -> float:
    """The horn `t` seconds in, before normalising."""
    envelope = min(t / ATTACK_S, (LENGTH_S - t) / RELEASE_S, 1.0)
    if envelope <= 0.0:
        return 0.0
    total = 0.0
    for tone in TONES_HZ:
        for number, level in enumerate(HARMONICS, start=1):
            total += level * math.sin(math.tau * tone * number * t)
    return envelope * total


def samples() -> bytes:
    """The whole press as signed 16-bit mono, its peak at `PEAK`."""
    raw = [sample(row / RATE_HZ) for row in range(int(RATE_HZ * LENGTH_S))]
    scale = PEAK * 32767.0 / max(abs(value) for value in raw)
    return b"".join(struct.pack("<h", round(value * scale)) for value in raw)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE_HZ)
        out.writeframes(samples())


if __name__ == "__main__":
    main()
