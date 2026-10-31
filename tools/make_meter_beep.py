#!/usr/bin/env python3
"""Synthesise the taxi meter's beep: `game/assets/authored/audio/meter_beep.wav` (`Q178`).

One short electronic pip, played inside the cab each time the reading moves. Authored,
not recorded, so it comes under the hand-authored licence with nothing to attribute.
Byte-identical each run: no noise, no clock.

    python tools/make_meter_beep.py
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

RATE_HZ = 22050
LENGTH_S = 0.09
# Not a 3D voice, so nothing attenuates it: the file's own level is how loud it plays.
PEAK = 0.3
TONE_HZ = 2000.0
# A little square in it, as a cheap piezo has.
THIRD_LEVEL = 0.25
# No click at either end.
ATTACK_S = 0.003
RELEASE_S = 0.012
OUT = Path(__file__).parent.parent / "game/assets/authored/audio/meter_beep.wav"


def sample(t: float) -> float:
    """The beep `t` seconds in, before normalising."""
    envelope = min(t / ATTACK_S, (LENGTH_S - t) / RELEASE_S, 1.0)
    if envelope <= 0.0:
        return 0.0
    return envelope * (
        math.sin(math.tau * TONE_HZ * t) + THIRD_LEVEL * math.sin(math.tau * 3.0 * TONE_HZ * t)
    )


def samples() -> bytes:
    """The whole beep as signed 16-bit mono, its peak at `PEAK`."""
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
