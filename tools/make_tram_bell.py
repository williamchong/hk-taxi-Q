#!/usr/bin/env python3
"""Synthesise the tram's bell: `game/assets/authored/audio/tram_bell.wav` (`P3-4`).

The foot gong of a Hong Kong tram, "ding ding": two strikes of a small bell, as a
handful of inharmonic partials decaying at their own rates. Authored, not recorded,
so it comes under the hand-authored licence with nothing to attribute. Byte-identical
each run: no noise, no clock.

    python tools/make_tram_bell.py
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

RATE_HZ = 22050
LENGTH_S = 1.1
PEAK = 0.85
# The second strike follows the first, slightly softer, as a foot does.
STRIKES = ((0.0, 1.0), (0.24, 0.8))
# (frequency, level, decay per second): a small bell's partials stand off the harmonics.
PARTIALS = (
    (1180.0, 1.0, 7.0),
    (1690.0, 0.55, 9.0),
    (2510.0, 0.45, 12.0),
    (3730.0, 0.25, 18.0),
)
# The strike's first milliseconds: no click.
ATTACK_S = 0.002
OUT = Path(__file__).parent.parent / "game/assets/authored/audio/tram_bell.wav"


def sample(t: float) -> float:
    """The bell `t` seconds in, before normalising."""
    total = 0.0
    for start, weight in STRIKES:
        since = t - start
        if since < 0.0:
            continue
        attack = min(since / ATTACK_S, 1.0)
        for frequency, level, decay in PARTIALS:
            total += (
                weight
                * attack
                * level
                * math.exp(-decay * since)
                * math.sin(math.tau * frequency * since)
            )
    return total


def samples() -> bytes:
    """The whole bell as signed 16-bit mono, its peak at `PEAK`."""
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
