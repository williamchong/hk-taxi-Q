#!/usr/bin/env python3
"""Synthesise the driving music: `game/assets/authored/audio/bgm_*.wav` (`P3-97`, `Q246`).

Four beds, one for each part of the day, and the style combo's layers. Every file is the
same eight bars at one tempo (the three drum layers two of them, repeated), so the game
plays them locked together and only turns each up and down: a bed fades into the next as
the hour moves, and a layer comes in as the combo climbs (`music.tres`).

Authored, not recorded, so it comes under the hand-authored licence with nothing to
attribute. Every voice is an enveloped note placed modulo the loop, so each loop is exactly
periodic. Byte-identical each run: every draw is seeded.

    python tools/make_bgm.py
"""

from __future__ import annotations

import functools
import struct
import wave
from pathlib import Path

import numpy as np

RATE_HZ = 22050
TAU = 2.0 * np.pi
BPM = 75.0
BEAT_S = 60.0 / BPM
BARS = 8
ROWS = round(BARS * 4 * BEAT_S * RATE_HZ)
# A chord lasts two bars.
TWO_BARS_S = 8 * BEAT_S
OUT_DIR = Path(__file__).parent.parent / "game/assets/authored/audio"
# A file's loudest sample when every layer plays at once over the loudest bed: the files
# share one scale, so the game mixes them at the levels they were written against.
PEAK = 0.9

# Day is IVmaj9 - iii7 - ii9 - V13sus in C; night is its minor side, ii9 - vi9 - bVIImaj9 -
# V9sus, each chord sharing three notes or more with the day chord in its slot so the two
# cross-fade without a clash. Two bars each; the roots sit at 147 Hz and up so a phone
# speaker carries them.
CHORDS = {
    "day": (
        (53, 57, 60, 64, 67),
        (52, 59, 62, 67, 71),
        (50, 57, 60, 64, 65),
        (55, 60, 64, 65, 69),
    ),
    "night": (
        (50, 57, 60, 64, 65),
        (57, 60, 64, 67, 71),
        (58, 62, 65, 69, 72),
        (55, 60, 62, 65, 69),
    ),
}
PENTATONIC = (72, 74, 76, 79, 81, 84)


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def place(bed: np.ndarray, start_s: float, piece: np.ndarray, pan: float = 0.5) -> None:
    """Add a mono piece into the stereo loop at `start_s`, wrapping past the end."""
    at = (round(start_s * RATE_HZ) + np.arange(piece.size)) % ROWS
    np.add.at(bed[:, 0], at, piece * np.cos(pan * np.pi / 2.0))
    np.add.at(bed[:, 1], at, piece * np.sin(pan * np.pi / 2.0))


def rhodes(
    midi: float, level: float, seconds: float = 5.0, bright: float = 1.1, decay: float = 1.1
) -> np.ndarray:
    """An electric piano: a sine bent by a decaying modulator, a short tine on top."""
    t = np.arange(round(seconds * RATE_HZ)) / RATE_HZ
    f = hz(midi)
    index = bright * level * np.exp(-3.0 * t)
    body = np.sin(TAU * f * t + index * np.sin(TAU * f * t))
    tine = 0.12 * np.exp(-14.0 * t) * np.sin(TAU * f * 7.0 * t)
    tremolo = 1.0 + 0.08 * np.sin(TAU * 4.5 * t)
    envelope = (
        np.minimum(t / 0.004, 1.0) * np.exp(-decay * t) * np.minimum((seconds - t) / 0.3, 1.0)
    )
    return level * envelope * tremolo * (body + tine)


def pad(midi: float, seconds: float, detune_cents: float) -> np.ndarray:
    """A soft sustained voice: a few falling harmonics, slow in and slow out."""
    t = np.arange(round(seconds * RATE_HZ)) / RATE_HZ
    f = hz(midi + detune_cents / 100.0)
    tone = sum(np.sin(TAU * f * n * t) / n**2.2 for n in (1, 2, 3, 4))
    envelope = np.minimum(t / 1.4, 1.0) * np.minimum((seconds - t) / 1.8, 1.0)
    return np.clip(envelope, 0.0, 1.0) * tone


def bell(midi: float, level: float, seconds: float = 2.5) -> np.ndarray:
    """The sparse top line: a glassy pluck."""
    t = np.arange(round(seconds * RATE_HZ)) / RATE_HZ
    f = hz(midi)
    tone = np.sin(TAU * f * t) + 0.3 * np.exp(-6.0 * t) * np.sin(TAU * f * 3.0 * t)
    return level * np.minimum(t / 0.003, 1.0) * np.exp(-2.6 * t) * tone


# Each mood is eight bars at one tempo, so any two cross-fade in time.
# comp: the piano's hits in two bars as (beat, level, first voice); ring: its decay per
# second; pad: its level, with the voices' own octave (low) or two octaves up (high);
# bells: notes per two bars, their echoes and how fast those fade; lead: the held night
# voice as (beat, chord voice, beats long, level); wash: the level of a low city hum;
# trim: the whole bed's level, where a thick pad would stand it over the others.
# What a mood leaves out: no piano, nothing beside the pad's octave, no lead, no hum.
QUIET = {
    "comp": (),
    "notes": (),
    "pad_low": 0.0,
    "pad_high": 0.0,
    "lead": (),
    "wash": 0.0,
    "trim": 1.0,
}
MOODS = {
    "morning": {
        "chords": "day",
        "bright": 1.1,
        "roll_s": 0.045,
        "ring": 1.3,
        # One piano note at a time, as (beat, chord voice, level): up the chord and back.
        "notes": ((0.0, 0, 0.4), (1.5, 2, 0.3), (3.0, 3, 0.34), (4.5, 4, 0.3), (6.0, 2, 0.26)),
        "pad": 0.065,
        "pad_high": 0.45,
        "bells": (4, 7),
        "echoes": 2,
        "echo_fall": 0.4,
        "band": (180.0, 8000.0),
    },
    "afternoon": {
        "chords": "day",
        "bright": 1.6,
        "roll_s": 0.02,
        "ring": 1.8,
        "comp": (
            (0.0, 0.55, 0),
            (1.5, 0.3, 2),
            (3.0, 0.3, 0),
            (4.5, 0.26, 1),
            (5.5, 0.32, 1),
            (7.0, 0.24, 2),
        ),
        "pad": 0.03,
        "pad_high": 0.2,
        "bells": (4, 6),
        "echoes": 3,
        "echo_fall": 0.45,
        "band": (150.0, 7500.0),
    },
    "night": {
        "chords": "night",
        "bright": 0.5,
        "roll_s": 0.07,
        "ring": 0.6,
        "comp": ((0.0, 0.45, 0),),
        "pad": 0.085,
        "pad_low": 0.9,
        "bells": (0, 2),
        "echoes": 5,
        "echo_fall": 0.62,
        "lead": ((2.0, 3, 3.0, 0.11), (5.5, 4, 2.0, 0.08)),
        "wash": 0.02,
        "band": (140.0, 2400.0),
        "trim": 0.75,
    },
    "midnight": {
        "chords": "night",
        "bright": 0.3,
        "roll_s": 0.12,
        "ring": 0.5,
        "pad": 0.11,
        "pad_low": 1.0,
        "bells": (0, 1),
        "echoes": 7,
        "echo_fall": 0.72,
        "lead": ((4.0, 2, 3.5, 0.07),),
        "wash": 0.035,
        "band": (140.0, 1600.0),
        "trim": 0.75,
    },
}


def lead(midi: float, seconds: float, level: float) -> np.ndarray:
    """The night's held voice: a near-sine that swells in and grows a slow vibrato."""
    t = np.arange(round(seconds * RATE_HZ)) / RATE_HZ
    f = hz(midi)
    wobble = 0.5 * np.minimum(t / 1.0, 1.0) * np.sin(TAU * 4.8 * t)
    tone = np.sin(TAU * f * t + wobble) + 0.15 * np.sin(2.0 * (TAU * f * t + wobble))
    envelope = np.minimum(t / 0.3, 1.0) * np.minimum((seconds - t) / 0.7, 1.0)
    return level * np.clip(envelope, 0.0, 1.0) * tone


def bed(mood: str) -> np.ndarray:
    look = QUIET | MOODS[mood]
    out = np.zeros((ROWS, 2))
    rng = np.random.default_rng(852)
    for slot, chord in enumerate(CHORDS[look["chords"]]):
        start = slot * TWO_BARS_S
        # The piano: the whole chord rolled from the bottom, then whatever the mood comps.
        for beat, level, first in look["comp"]:
            for step, midi in enumerate(chord[first:]):
                note = rhodes(midi, level, bright=look["bright"], decay=look["ring"])
                at = start + beat * BEAT_S + look["roll_s"] * step
                place(out, at, note, 0.35 + 0.075 * (step + first))
        for beat, voice, level in look["notes"]:
            note = rhodes(chord[voice], level, bright=look["bright"], decay=look["ring"])
            place(out, start + beat * BEAT_S, note, 0.4 + 0.05 * voice)
        # The pad holds the upper voices an octave up, overlapping its neighbours.
        for midi in chord[2:]:
            for cents, pan in ((-5.0, 0.15), (5.0, 0.85)):
                voice = pad(midi + 12, TWO_BARS_S + 1.8, cents)
                if look["pad_low"]:
                    voice = voice + look["pad_low"] * pad(midi, TWO_BARS_S + 1.8, -cents)
                if look["pad_high"]:
                    voice = voice + look["pad_high"] * pad(midi + 24, TWO_BARS_S + 1.8, -cents)
                place(out, start - 0.9, look["pad"] * voice, pan)
        # A few bell notes, each with fading echoes a dotted quaver apart.
        count = rng.integers(look["bells"][0], look["bells"][1] + 1)
        for beat in sorted(rng.choice(np.arange(2, 16), size=count, replace=False)):
            midi = PENTATONIC[rng.integers(0, len(PENTATONIC))]
            pan = float(rng.uniform(0.25, 0.75))
            for echo in range(look["echoes"]):
                place(
                    out,
                    start + beat * BEAT_S / 2.0 + echo * 0.75 * BEAT_S,
                    bell(midi, 0.16 * look["echo_fall"] ** echo),
                    pan if echo % 2 == 0 else 1.0 - pan,
                )
        for beat, voice, beats, level in look["lead"]:
            for echo in range(3):
                note = lead(chord[voice] + 12, beats * BEAT_S, level * 0.5**echo)
                place(
                    out, start + (beat + 1.5 * echo) * BEAT_S, note, 0.5 + 0.3 * (echo % 2) - 0.15
                )
    if look["wash"]:
        hum = band(np.random.default_rng(31).standard_normal((ROWS, 2)), 200.0, 700.0)
        out += look["wash"] * hum / np.sqrt(np.mean(hum**2))
    return look["trim"] * band(out, *look["band"])


# The combo's layers, and each one's level with the combo at its top: `music.tres`'s last
# `tiers` row, mirrored here only to find the loudest the files can sum to.
STEMS = ("shaker", "thump", "bass", "arp", "top", "clap")
FULL = (1.2, 1.15, 1.0, 1.1, 1.0, 1.0)
# The layers that play the chords, so there is one of each for the day and for the night.
TONAL = ("bass", "arp", "top")


def fire_stems(chords: str) -> dict[str, np.ndarray]:
    """The combo's layers over one side's chords, each a loop of its own."""
    stems = {name: np.zeros((ROWS, 2)) for name in STEMS}
    tick = np.arange(round(0.09 * RATE_HZ)) / RATE_HZ
    slap = np.arange(round(0.16 * RATE_HZ)) / RATE_HZ
    fall = np.arange(round(0.22 * RATE_HZ)) / RATE_HZ
    # A soft thump that falls from 190 Hz to 120: low enough to push, high enough for a phone.
    thump = np.exp(-16.0 * fall) * np.sin(
        TAU * (120.0 * fall + 70.0 / 16.0 * (1.0 - np.exp(-16.0 * fall)))
    )
    for slot, chord in enumerate(CHORDS[chords]):
        start = slot * TWO_BARS_S
        # The same draws every two bars, so the drum layers repeat and ship as two.
        rng = np.random.default_rng(1997)
        climb = [midi + 12 for midi in chord[1:]]
        pattern = climb + climb[-2:0:-1]
        root = 0.22 * rhodes(chord[0], 1.0, 0.6, bright=0.8, decay=7.0)
        for quaver in range(16):
            at = start + quaver * BEAT_S / 2.0
            accent = 1.0 if quaver % 2 == 0 else 0.7
            pluck = rhodes(pattern[quaver % len(pattern)], 0.2 * accent, 1.2, bright=1.8, decay=5.0)
            place(stems["arp"], at, pluck, 0.3 + 0.4 * (quaver % 2))
            place(stems["bass"], at, root, 0.5)
            shake = rng.standard_normal(tick.size) * np.exp(-45.0 * tick)
            place(stems["shaker"], at, (0.5 if quaver % 2 == 0 else 1.0) * shake, 0.65)
            # A semiquaver ghost before every other off-beat keeps it leaning forward.
            if quaver % 4 == 3:
                ghost = 0.4 * rng.standard_normal(tick.size) * np.exp(-60.0 * tick)
                place(stems["shaker"], at - BEAT_S / 4.0, ghost, 0.4)
        # The top line runs the same climb in semiquavers, two octaves over the chord.
        for semi in range(32):
            midi = pattern[(semi * 3) % len(pattern)] + 12
            level = 0.07 * (1.0 if semi % 4 == 0 else 0.6)
            place(
                stems["top"],
                start + semi * BEAT_S / 4.0,
                bell(midi, level, 0.5),
                0.2 + 0.6 * (semi % 2),
            )
        for beat in range(8):
            place(
                stems["thump"], start + beat * BEAT_S, (0.5 if beat % 2 == 0 else 0.3) * thump, 0.5
            )
            if beat % 2 == 1:
                clap = rng.standard_normal(slap.size) * np.exp(-32.0 * slap)
                place(stems["clap"], start + beat * BEAT_S, clap, 0.5)
    bands = {"shaker": (4500.0, 9000.0), "clap": (900.0, 3200.0), "thump": (110.0, 2000.0)}
    levels = {"shaker": 0.45, "clap": 0.5, "top": 2.4}
    return {
        name: levels.get(name, 2.0) * band(stem, *bands.get(name, (140.0, 7000.0)))
        for name, stem in stems.items()
    }


def band(signal: np.ndarray, low_hz: float, high_hz: float) -> np.ndarray:
    """A periodic band-pass: the loop's own spectrum with the skirts rolled off."""
    freqs = np.fft.rfftfreq(signal.shape[0], 1.0 / RATE_HZ)
    gain = 1.0 / np.sqrt(1.0 + (low_hz / np.maximum(freqs, 1e-9)) ** 6)
    gain /= np.sqrt(1.0 + (freqs / high_hz) ** 6)
    return np.fft.irfft(np.fft.rfft(signal, axis=0) * gain[:, None], signal.shape[0], axis=0)


def smpl_chunk(rows: int) -> bytes:
    """One forward loop over the whole file: RIFF's sampler chunk."""
    header = struct.pack("<9I", 0, 0, round(1e9 / RATE_HZ), 60, 0, 0, 0, 1, 0)
    loop = struct.pack("<6I", 0, 0, 0, rows - 1, 0, 0)
    body = header + loop
    return b"smpl" + struct.pack("<I", len(body)) + body


def write(path: Path, frames: bytes, channels: int) -> None:
    """A looping 16-bit file: Godot reads the loop off the `smpl` chunk."""
    with wave.open(str(path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(RATE_HZ)
        out.writeframes(frames)
    data = path.read_bytes() + smpl_chunk(len(frames) // (2 * channels))
    path.write_bytes(data[:4] + struct.pack("<I", len(data) - 8) + data[8:])


def layer_name(stem: str, side: str) -> str:
    """A layer's file: one for each side's chords, or one for both."""
    return f"bgm_fire_{side}_{stem}" if stem in TONAL else f"bgm_fire_{stem}"


@functools.cache
def signals() -> dict[str, np.ndarray]:
    """Every file's signal by name, on one scale: the beds in stereo, the layers mono."""
    out = {f"bgm_{mood}": bed(mood) for mood in MOODS}
    for side in CHORDS:
        for name, stem in fire_stems(side).items():
            # The drums are the same under either side, and the same every two bars.
            rows = ROWS if name in TONAL else ROWS // len(CHORDS[side])
            out[layer_name(name, side)] = stem.mean(axis=1)[:rows]
    # As the game sums them: a mono layer on both channels, a short one repeated.
    loudest = 0.0
    for mood, look in MOODS.items():
        mix = out[f"bgm_{mood}"].copy()
        for stem, level in zip(STEMS, FULL, strict=True):
            mix += level * np.resize(out[layer_name(stem, look["chords"])], ROWS)[:, None]
        loudest = max(loudest, float(np.abs(mix).max()))
    return {name: signal * (PEAK / loudest) for name, signal in out.items()}


def rendered() -> dict[str, tuple[bytes, int]]:
    """Every file's frames by name, and how many channels they interleave."""
    return {
        name: (np.round(signal * 32767.0).astype("<i2").tobytes(), signal.ndim)
        for name, signal in signals().items()
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (frames, channels) in rendered().items():
        write(OUT_DIR / f"{name}.wav", frames, channels)


if __name__ == "__main__":
    main()
