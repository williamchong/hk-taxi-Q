#!/usr/bin/env python3
"""Synthesise the driving music: `game/assets/authored/audio/bgm_*.wav` (`P3-97`, `Q246`).

Four beds, one for each part of the day, and the style combo's layers. Every file is the
same eight bars at one tempo (the three drum layers two of them, repeated), so the game
plays them locked together and only turns each up and down: a bed fades into the next as
the hour moves, and a layer comes in as the combo climbs (`music.tres`).

The bed is a street groove, on the user's pick by ear: swung drums, a walking bass and an
electric piano, thinned out by the hour. The layers add to that rhythm section and never
double it.

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
BPM = 84.0
BEAT_S = 60.0 / BPM
BARS = 8
ROWS = round(BARS * 4 * BEAT_S * RATE_HZ)
# A chord lasts two bars.
TWO_BARS_S = 8 * BEAT_S
# How late an off semiquaver lands, as a share of a semiquaver: the groove's lean.
SWING = 0.45
OUT_DIR = Path(__file__).parent.parent / "game/assets/authored/audio"
# A file's loudest sample when every layer plays at once over the loudest bed: the files
# share one scale, so the game mixes them at the levels they were written against.
PEAK = 0.9

# Day is IVmaj9 - iii7 - ii9 - V13sus in C; night is its minor side, ii9 - vi9 - bVIImaj9 -
# V9sus, each chord sharing three notes or more with the day chord in its slot so the two
# cross-fade without a clash. Two bars each; the roots sit at 147 Hz and up and the bass
# walks down to 139 at its lowest, so a phone speaker carries them.
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


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def span(seconds: float) -> np.ndarray:
    return np.arange(round(seconds * RATE_HZ)) / RATE_HZ


def place(bed: np.ndarray, start_s: float, piece: np.ndarray, pan: float = 0.5) -> None:
    """Add a mono piece into the stereo loop at `start_s`, wrapping past the end."""
    rows = (round(start_s * RATE_HZ) + np.arange(piece.size)) % ROWS
    np.add.at(bed[:, 0], rows, piece * np.cos(pan * np.pi / 2.0))
    np.add.at(bed[:, 1], rows, piece * np.sin(pan * np.pi / 2.0))


def rhodes(
    midi: float, level: float, seconds: float = 5.0, bright: float = 1.1, decay: float = 1.1
) -> np.ndarray:
    """An electric piano: a sine bent by a decaying modulator, a short tine on top."""
    t = span(seconds)
    f = hz(midi)
    index = bright * level * np.exp(-3.0 * t)
    body = np.sin(TAU * f * t + index * np.sin(TAU * f * t))
    tine = 0.12 * np.exp(-14.0 * t) * np.sin(TAU * f * 7.0 * t)
    tremolo = 1.0 + 0.08 * np.sin(TAU * 4.5 * t)
    envelope = (
        np.minimum(t / 0.004, 1.0) * np.exp(-decay * t) * np.minimum((seconds - t) / 0.3, 1.0)
    )
    return level * envelope * tremolo * (body + tine)


def pad(midi: float, seconds: float) -> np.ndarray:
    """A soft sustained voice: a few falling harmonics, slow in and slow out."""
    t = span(seconds)
    f = hz(midi)
    tone = sum(np.sin(TAU * f * n * t) / n**2.2 for n in (1, 2, 3, 4))
    envelope = np.minimum(t / 1.4, 1.0) * np.minimum((seconds - t) / 1.8, 1.0)
    return envelope * tone


def at(beat: float) -> float:
    """A beat's time in the loop, an off semiquaver pushed late by the swing."""
    late = SWING * BEAT_S / 4.0 if round(beat * 4.0) % 2 else 0.0
    return beat * BEAT_S + late


def kick() -> np.ndarray:
    """A drum that falls from 215 Hz to 105: low enough to push, high enough for a phone."""
    t = span(0.25)
    return np.exp(-14.0 * t) * np.sin(TAU * (105.0 * t + 110.0 / 30.0 * (1.0 - np.exp(-30.0 * t))))


def hit(rng: np.random.Generator, seconds: float, decay: float) -> np.ndarray:
    """A burst of noise: a hat, a shaker or a clap once its band is cut."""
    t = span(seconds)
    return rng.standard_normal(t.size) * np.exp(-decay * t)


def snare(rng: np.random.Generator) -> np.ndarray:
    t = span(0.2)
    return 0.6 * hit(rng, 0.2, 24.0) + 0.5 * np.exp(-30.0 * t) * np.sin(TAU * 210.0 * t)


def conga(f: float) -> np.ndarray:
    t = span(0.18)
    return np.exp(-22.0 * t) * np.sin(TAU * (f * t + f / 160.0 * (1.0 - np.exp(-40.0 * t))))


def bass(midi: float, seconds: float) -> np.ndarray:
    """A fingered electric bass: falling harmonics that darken as the note rings."""
    t = span(seconds)
    f = hz(midi)
    tone = sum(np.exp(-(2.0 + 5.0 * n) * t) * np.sin(TAU * f * n * t) / n for n in range(1, 7))
    envelope = np.minimum(t / 0.004, 1.0) * np.minimum((seconds - t) / 0.03, 1.0)
    return 0.5 * envelope * (tone + 0.5 * np.sin(TAU * f * t))


def chank(chord: tuple[int, ...], level: float) -> np.ndarray:
    """A muted guitar chord: bright, and dead in a tenth of a second."""
    t = span(0.1)
    tone = sum(np.sin(TAU * hz(midi + 12) * n * t) / n for midi in chord[1:4] for n in range(1, 6))
    return level * np.minimum(t / 0.002, 1.0) * np.exp(-40.0 * t) * tone


def brass(chord: tuple[int, ...], seconds: float) -> np.ndarray:
    """A horn section's stab: the upper voices, sawish, with a quick swell."""
    t = span(seconds)
    tone = sum(
        np.sin(TAU * hz(midi + 12) * n * t) / n**1.3 for midi in chord[2:] for n in range(1, 8)
    )
    envelope = np.minimum(t / 0.03, 1.0) * np.minimum((seconds - t) / 0.06, 1.0)
    return 0.04 * envelope * tone


# Each mood is the same eight bars of the same groove, so any two cross-fade in time.
# chords: which side's; kick, snare, hat, bass: each one's level; comp: the piano's chords
# in a bar as (beat, level), with bright its tone and ring its decay per second; line:
# single piano notes over two bars instead, as (beat, chord voice, level); sparse: the kick
# and hat thinned; pad: the level of a low held chord, which is all the harmony a mood
# without a piano has; high: where the bed's top rolls off.
QUIET = {"comp": (), "line": (), "sparse": False, "pad": 0.0, "bright": 1.0, "ring": 2.6}
MOODS = {
    "morning": {
        "chords": "day",
        "kick": 0.3,
        "snare": 0.12,
        "hat": 0.15,
        "bass": 0.6,
        # One piano note at a time (the user's pick): up the chord and back.
        "line": (
            (0.0, 0, 0.34),
            (1.75, 2, 0.26),
            (2.5, 3, 0.3),
            (4.0, 4, 0.3),
            (5.75, 3, 0.24),
            (6.5, 2, 0.26),
        ),
        "high": 6000.0,
    },
    "afternoon": {
        "chords": "day",
        "kick": 0.55,
        "snare": 0.28,
        "hat": 0.2,
        "bass": 0.8,
        "comp": ((0.0, 0.2), (1.75, 0.13), (2.5, 0.15)),
        "high": 5000.0,
    },
    "night": {
        "chords": "night",
        "kick": 0.5,
        "snare": 0.22,
        "hat": 0.14,
        "bass": 0.85,
        "comp": ((0.0, 0.17), (2.5, 0.11)),
        "bright": 0.6,
        "ring": 2.0,
        "high": 3000.0,
    },
    # No piano at all (the user's pick).
    "midnight": {
        "chords": "night",
        "kick": 0.4,
        "snare": 0.12,
        "hat": 0.1,
        "bass": 0.8,
        "sparse": True,
        "pad": 0.022,
        "high": 2000.0,
    },
}
BED_BANDS = {
    "kick": (95.0, 2500.0),
    "snare": (180.0, 6000.0),
    "hat": (6000.0, 10000.0),
    "bass": (120.0, 1800.0),
}


def bed(mood: str) -> np.ndarray:
    look = QUIET | MOODS[mood]
    chords = CHORDS[look["chords"]]
    parts = {name: np.zeros((ROWS, 2)) for name in (*BED_BANDS, "keys")}
    rng = np.random.default_rng(11)
    for slot, chord in enumerate(chords):
        leading = chords[(slot + 1) % len(chords)][0] - 1
        for bar in range(2):
            b0 = slot * 8 + bar * 4
            for beat in (0.0, 2.5) if look["sparse"] else (0.0, 1.75, 2.5):
                place(parts["kick"], at(b0 + beat), kick())
            for beat in (1.0, 3.0):
                place(parts["snare"], at(b0 + beat), snare(rng))
            # Quavers, and a semiquaver pushed in before the third and the next bar.
            for semi in range(16):
                if semi % 2 == 0 or (semi in (7, 15) and not look["sparse"]):
                    tick = (0.9 if semi % 4 else 0.6) * hit(rng, 0.05, 80.0)
                    place(parts["hat"], at(b0 + semi / 4.0), tick, 0.6)
            # The bass walks the chord, and into the next one through its leading note.
            walk = (0, 1, 2, 1) if bar == 0 else (0, 2, 1, None)
            for beat, voice in enumerate(walk):
                midi = leading if voice is None else chord[voice]
                note = bass(midi if midi < 62 else midi - 12, 0.85 * BEAT_S)
                place(parts["bass"], at(b0 + beat), note)
            for beat, level in look["comp"]:
                for midi in chord[1:]:
                    note = rhodes(midi, level, 1.6, bright=look["bright"], decay=look["ring"])
                    place(parts["keys"], at(b0 + beat), note, 0.45)
        for beat, voice, level in look["line"]:
            note = rhodes(chord[voice] + 12, level, 2.5, bright=1.0, decay=1.6)
            place(parts["keys"], at(slot * 8 + beat), note, 0.4 + 0.05 * voice)
        if look["pad"]:
            for midi in chord[1:4]:
                held = look["pad"] * pad(midi, TWO_BARS_S + 1.8)
                place(parts["keys"], slot * TWO_BARS_S - 0.9, held)
    out = sum(
        look.get(name, 1.0) * band(part, *BED_BANDS.get(name, (140.0, 7500.0)))
        for name, part in parts.items()
    )
    return band(out, 100.0, look["high"])


# The combo's layers, and each one's level with the combo at its top: `music.tres`'s last
# `tiers` row, mirrored here only to find the loudest the files can sum to.
STEMS = ("shaker", "conga", "guitar", "arp", "horns", "clap")
FULL = (1.2, 1.15, 1.0, 1.1, 1.0, 1.0)
# The layers that play the chords, so there is one of each for the day and for the night.
TONAL = ("guitar", "arp", "horns")
# Each layer's band and its level against the bed. The bed has its own drums and bass, so
# a layer is something a street band would add on top.
STEM_MIX = {
    "shaker": (4500.0, 9000.0, 0.1),
    "conga": (150.0, 2500.0, 0.45),
    "guitar": (500.0, 4500.0, 1.0),
    "arp": (140.0, 7000.0, 0.5),
    "horns": (300.0, 4000.0, 1.0),
    "clap": (900.0, 3200.0, 0.12),
}


def fire_stems(side: str) -> dict[str, np.ndarray]:
    """The combo's layers over one side's chords, each a loop of its own."""
    stems = {name: np.zeros((ROWS, 2)) for name in STEMS}
    for slot, chord in enumerate(CHORDS[side]):
        # The same draws every two bars, so the drum layers repeat and ship as two.
        rng = np.random.default_rng(1997)
        climb = [midi + 12 for midi in chord[1:]]
        pattern = climb + climb[-2:0:-1]
        for bar in range(2):
            b0 = slot * 8 + bar * 4
            # The shaker is loudest on the semiquavers the bed's hat leaves out.
            for semi in range(16):
                shake = (1.0 if semi % 2 else 0.45) * hit(rng, 0.07, 50.0)
                place(stems["shaker"], at(b0 + semi / 4.0), shake)
            for beat, f, level in (
                (0.75, 250.0, 0.7),
                (1.5, 250.0, 1.0),
                (2.25, 190.0, 0.8),
                (3.5, 250.0, 1.0),
                (3.75, 190.0, 0.7),
            ):
                place(stems["conga"], at(b0 + beat), level * conga(f))
            for beat, level in ((0.5, 1.0), (1.5, 0.8), (2.25, 0.5), (2.5, 1.0), (3.5, 0.8)):
                place(stems["guitar"], at(b0 + beat), chank(chord, 0.05 * level))
            for quaver in range(8):
                midi = pattern[(bar * 8 + quaver) % len(pattern)]
                level = 0.2 if quaver % 2 == 0 else 0.14
                pluck = rhodes(midi, level, 1.2, bright=1.8, decay=5.0)
                place(stems["arp"], at(b0 + quaver / 2.0), pluck)
            for beat in (1.0, 3.0):
                place(stems["clap"], at(b0 + beat), hit(rng, 0.16, 32.0))
        # The horns punch once in the middle of the chord and answer twice at its end.
        for beat, held in ((3.5, 0.3), (6.5, 0.25), (7.0, 0.7)):
            place(stems["horns"], at(slot * 8 + beat), brass(chord, held * BEAT_S))
    return {
        name: STEM_MIX[name][2] * band(stem, *STEM_MIX[name][:2]) for name, stem in stems.items()
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
