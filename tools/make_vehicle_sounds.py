#!/usr/bin/env python3
"""Synthesise the vehicles' sounds into `game/assets/authored/audio/` (`P3-79`, `Q185`).

Every file is authored, not recorded, so it comes under the hand-authored licence with
nothing to attribute. Byte-identical each run: the noise is drawn from a seeded
generator, one seed per file, and nothing reads the clock.

Two shapes of file:

- **A loop** (`LOOPS`) is exactly periodic over its length — every tone sits on the
  loop's own frequency grid and every noise is drawn on it, through `irfft` — so it
  joins itself without a click at any pitch. It carries a `smpl` chunk, which Godot's
  WAV importer reads as the loop ("Detect From WAV", the import default), so no
  `.import` file is edited by hand.
- **A one-shot** (`SHOTS`) starts and ends at zero.

The numbers a game reads off a file — an engine loop's reference rpm, the EV whine's
reference speed — are mirrored in `game/tuning/taxi_audio.tres`, and its sidecar names
this script as their source.

    python tools/make_vehicle_sounds.py
"""

from __future__ import annotations

import struct
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np

RATE_HZ = 22050
OUT_DIR = Path(__file__).parent.parent / "game/assets/authored/audio"
TAU = 2.0 * np.pi

# ---------------------------------------------------------------- the horns (loops)

# A horn's loop is 0.2 s, so every tone in it is a multiple of 5 Hz.
HORN_LOOP_S = 0.2
# Per kind: (tones Hz, harmonic levels, air-noise level, peak). A diaphragm horn is
# reedy, so its harmonics stand well up; an air horn is a sawtooth with breath in it.
HORNS: dict[str, tuple[tuple[float, ...], tuple[float, ...], float, float]] = {
    # The traffic's old twin-note horn, `Q178`'s.
    "car_a": ((415.0, 495.0), (1.0, 0.8, 0.6, 0.45, 0.3, 0.2), 0.0, 0.8),
    # A lower, rounder pair.
    "car_b": ((350.0, 440.0), (1.0, 0.55, 0.35, 0.2, 0.1), 0.0, 0.8),
    # The taxi's thin, nasal note: two tones 15 Hz apart beat, and the odd harmonics stand.
    "taxi": ((520.0, 535.0), (1.0, 0.3, 0.9, 0.2, 0.7, 0.15, 0.5), 0.0, 0.75),
    # A minibus is high and sharp.
    "minibus": ((660.0, 790.0), (1.0, 0.7, 0.5, 0.35), 0.0, 0.75),
    # A van has one flat disc horn.
    "van": ((400.0,), (1.0, 0.5, 0.3), 0.0, 0.8),
    # A bus's air horn, low.
    "bus": ((155.0, 195.0), tuple(1.0 / n for n in range(1, 16)), 0.08, 0.9),
}

# ------------------------------------------------------------- the engine (loops)

# Each loop is whole engine cycles (two turns of the crank, four firings), so the rpm is
# one at which a cycle is a whole number of samples: 22050 x 120 / rpm.
ENGINE_RPMS = (1050.0, 2520.0, 5040.0)
ENGINE_LOOP_S = 0.45
# The four cylinders fire unevenly, as a worn LPG four does: level and timing per cylinder.
CYLINDER_LEVELS = (1.0, 0.84, 0.95, 0.89)
CYLINDER_LATE = (0.0, 0.035, -0.02, 0.015)
# A firing is a pressure pulse out of the tailpipe: a smooth bump this long, so the
# note is the firing rate and its harmonics, not a ringing tone. The first try rang
# resonances up to 790 Hz over a band of hiss to 3.5 kHz, and the user heard "some
# kind of noisy motor" (2026-11-06): a petrol four is thump, and the muffler eats the top.
PULSE_S = 0.0012
# The pipe's one broad resonance, and the muffler's corner: little gets past it.
PIPE_HZ = 170.0
MUFFLER_HZ = 550.0
# Each firing's level wanders this much, drawn once per loop: the lumpiness.
FIRING_JITTER = 0.08
# The intake's breath under it, low and gated by the firings, against the note's RMS.
BREATH_LEVEL = 0.12
# The EV motor's whine at `EV_REF_KPH`: the motor and its reduction gear's mesh.
EV_REF_KPH = 50.0
EV_TONES = ((1000.0, 1.0), (1500.0, 0.45), (2400.0, 0.2), (3000.0, 0.1))

# ------------------------------------------------------------------ helpers


def _time(seconds: float) -> np.ndarray:
    return np.arange(round(seconds * RATE_HZ)) / RATE_HZ


def _band_noise(
    rows: int, low_hz: float, high_hz: float, seed: int, tilt: float = 0.0
) -> np.ndarray:
    """Noise between two frequencies, exactly periodic over `rows`, RMS 1.

    Drawn as a spectrum with a random phase in every bin, so it loops; `tilt` leans it
    down by that power of the frequency (1 is pink).
    """
    rng = np.random.default_rng(seed)
    freqs = np.fft.rfftfreq(rows, 1.0 / RATE_HZ)
    gain = ((freqs >= low_hz) & (freqs <= high_hz)).astype(float)
    gain[1:] /= freqs[1:] ** (tilt / 2.0)
    spectrum = gain * np.exp(1j * rng.uniform(0.0, TAU, freqs.size))
    noise = np.fft.irfft(spectrum, rows)
    return noise / max(float(np.sqrt(np.mean(noise**2))), 1e-12)


def _modes(t: np.ndarray, partials: tuple[tuple[float, float, float], ...]) -> np.ndarray:
    """Struck modes: (Hz, level, decay per second) each, from `t` = 0."""
    out = np.zeros_like(t)
    for hz, level, decay in partials:
        out += level * np.exp(-decay * t) * np.sin(TAU * hz * t)
    return out


def _fade(signal: np.ndarray, attack_s: float = 0.002, release_s: float = 0.02) -> np.ndarray:
    """No click at either end of a one-shot: it starts and ends at zero."""
    rows = signal.size
    ramp = np.ones(rows)
    up = max(int(attack_s * RATE_HZ), 1)
    down = max(int(release_s * RATE_HZ), 1)
    ramp[:up] = np.linspace(0.0, 1.0, up)
    ramp[rows - down :] = np.minimum(ramp[rows - down :], np.linspace(1.0, 0.0, down))
    return signal * ramp


def _at(rows: int, start_s: float, piece: np.ndarray) -> np.ndarray:
    """`piece` laid into silence `rows` long at `start_s`, cut at the end."""
    out = np.zeros(rows)
    start = int(start_s * RATE_HZ)
    if start < rows:
        span = min(piece.size, rows - start)
        out[start : start + span] = piece[:span]
    return out


# ------------------------------------------------------------------ the loops


def horn(kind: str) -> np.ndarray:
    tones, harmonics, air, _peak = HORNS[kind]
    t = _time(HORN_LOOP_S)
    out = np.zeros_like(t)
    for tone in tones:
        for number, level in enumerate(harmonics, start=1):
            if tone * number < RATE_HZ / 2:
                out += level * np.sin(TAU * tone * number * t)
    if air > 0.0:
        out += air * np.max(np.abs(out)) * _band_noise(t.size, 300.0, 4000.0, seed=11)
    return out


def _exhaust_gain(freqs: np.ndarray) -> np.ndarray:
    """The pulse's spectrum through the pipe and the muffler, nothing under 20 Hz."""
    pulse = 1.0 / np.abs(1.0 + 2j * np.pi * freqs * PULSE_S) ** 2
    pipe = 1.0 + 1.5 / (1.0 + ((freqs - PIPE_HZ) / (PIPE_HZ * 0.5)) ** 2)
    muffler = 1.0 / np.sqrt(1.0 + (freqs / MUFFLER_HZ) ** 4)
    return pulse * pipe * muffler * (freqs >= 20.0)


def engine(rpm: float) -> np.ndarray:
    """Whole engine cycles at `rpm`: four firings a cycle, each a pulse through the exhaust."""
    cycle = round(RATE_HZ * 120.0 / rpm)
    cycles = max(round(ENGINE_LOOP_S * RATE_HZ / cycle), 1)
    rows = cycle * cycles
    rng = np.random.default_rng(int(rpm))
    firings = np.zeros(rows)
    for n in range(cycles * 4):
        cylinder = n % 4
        start = (n * cycle // 4 + round(CYLINDER_LATE[cylinder] * cycle / 4)) % rows
        firings[start] += CYLINDER_LEVELS[cylinder] * (1.0 + FIRING_JITTER * rng.standard_normal())
    # Shaped in the frequency domain over the whole loop, so it is circular: the
    # loop's last firings ring into its first.
    freqs = np.fft.rfftfreq(rows, 1.0 / RATE_HZ)
    note = np.fft.irfft(np.fft.rfft(firings) * _exhaust_gain(freqs), rows)
    gate = np.fft.irfft(
        np.fft.rfft(firings) * np.fft.rfft(np.exp(-40.0 * np.arange(rows) / RATE_HZ)), rows
    )
    breath = (
        _band_noise(rows, 80.0, 1200.0, seed=int(rpm) + 1, tilt=1.0)
        * gate
        / max(float(np.max(gate)), 1e-12)
    )
    return note / float(np.sqrt(np.mean(note**2))) + BREATH_LEVEL * breath


def ev_whine() -> np.ndarray:
    t = _time(0.2)
    out = np.zeros_like(t)
    for hz, level in EV_TONES:
        out += level * np.sin(TAU * hz * t)
    return out + 0.05 * _band_noise(t.size, 2000.0, 8000.0, seed=21)


def skid() -> np.ndarray:
    rows = round(0.4 * RATE_HZ)
    # Narrow bands waver, which is what a squeal does.
    return (
        _band_noise(rows, 1040.0, 1160.0, seed=31)
        + 0.45 * _band_noise(rows, 2240.0, 2330.0, seed=32)
        + 0.12 * _band_noise(rows, 3000.0, 6500.0, seed=33)
    )


def wind() -> np.ndarray:
    # Dark on purpose: it is always there, so it must sit under everything (the user's
    # call, 2026-11-06).
    return _band_noise(round(0.8 * RATE_HZ), 60.0, 1000.0, seed=41, tilt=1.5)


def scrape() -> np.ndarray:
    rows = round(0.5 * RATE_HZ)
    grit = 1.0 + 0.8 * np.tanh(_band_noise(rows, 15.0, 70.0, seed=52))
    return _band_noise(rows, 600.0, 5000.0, seed=51, tilt=0.5) * grit


# ------------------------------------------------------------------ the one-shots


def _motor(seconds: float, from_hz: float, to_hz: float, clunk_level: float) -> np.ndarray:
    """The meter's flag: a small geared motor running, then the flag landing."""
    t = _time(seconds)
    run_s = seconds - 0.15
    hz = np.interp(t, (0.0, 0.08, run_s), (from_hz * 0.6, from_hz, to_hz))
    phase = TAU * np.cumsum(hz) / RATE_HZ
    buzz = np.tanh(3.0 * np.sin(phase))
    teeth = 0.5 + 0.5 * np.sin(phase * 7.0)
    brush = _band_noise(t.size, 2500.0, 7000.0, seed=int(from_hz)) * 0.15
    running = (buzz * (0.6 + 0.4 * teeth) + brush) * (t < run_s)
    running *= np.clip(np.minimum(t / 0.02, (run_s - t) / 0.02), 0.0, 1.0)
    landing = clunk_level * _modes(
        t, ((120.0, 1.0, 30.0), (880.0, 0.5, 70.0), (2300.0, 0.3, 140.0))
    )
    return _fade(0.6 * running + _at(t.size, run_s, landing))


def flag_down() -> np.ndarray:
    return _motor(0.7, 85.0, 115.0, 1.4)


def flag_up() -> np.ndarray:
    return _motor(0.55, 100.0, 125.0, 0.9)


def _crunch(t: np.ndarray, seed: int, length_s: float, density: float) -> np.ndarray:
    """Metal giving: noise gated by a sparse crackle that thins out over `length_s`."""
    rng = np.random.default_rng(seed)
    crackle = (rng.random(t.size) < density * np.exp(-t / length_s * 3.0)).astype(float)
    grains = np.convolve(crackle, np.exp(-np.arange(80) / 12.0), mode="same")
    return _band_noise(t.size, 500.0, 5000.0, seed) * np.minimum(grains, 1.0)


def _hit(seconds: float, seed: int, thud_hz: float, decay: float, crunch_s: float) -> np.ndarray:
    t = _time(seconds)
    rng = np.random.default_rng(seed)
    wobble = rng.uniform(0.92, 1.08)
    thud = _modes(t, ((thud_hz * wobble, 1.0, decay), (thud_hz * 2.7 * wobble, 0.4, decay * 1.8)))
    knock = _band_noise(t.size, 150.0, 1500.0, seed) * np.exp(-45.0 * t) * 0.5
    crunch = _crunch(t, seed, crunch_s, 0.02) * 0.6 if crunch_s > 0.0 else 0.0
    return _fade(thud + knock + crunch)


def hit_tap(variant: int) -> np.ndarray:
    return _hit(0.35, 60 + variant, 105.0, 18.0, 0.0)


def hit_bump(variant: int) -> np.ndarray:
    return _hit(0.7, 70 + variant, 75.0, 10.0, 0.25)


def hit_crash(variant: int) -> np.ndarray:
    t = _time(1.3)
    panels = _modes(
        t, ((310.0, 0.4, 9.0), (470.0, 0.3, 11.0), (820.0, 0.25, 14.0), (1270.0, 0.2, 18.0))
    )
    return _fade(_hit(1.3, 80 + variant, 55.0, 7.0, 0.6) + panels)


def top_car() -> np.ndarray:
    t = _time(0.8)
    return _fade(
        _modes(t, ((180.0, 1.0, 9.0), (262.0, 0.8, 11.0), (413.0, 0.6, 14.0), (633.0, 0.4, 18.0)))
    )


def _bell_metal(seconds: float, base_hz: float, decay: float) -> np.ndarray:
    t = _time(seconds)
    # A bar's partials stand off the harmonics.
    ratios = ((1.0, 1.0), (2.76, 0.6), (5.40, 0.4), (8.93, 0.25))
    return _fade(
        _modes(t, tuple((base_hz * r, level, decay * (1.0 + r * 0.4)) for r, level in ratios)),
        release_s=0.1,
    )


def top_railing() -> np.ndarray:
    return _bell_metal(1.5, 520.0, 2.5)


def top_tram() -> np.ndarray:
    t = _time(2.0)
    thud = _modes(t, ((48.0, 1.2, 5.0),))
    return _fade(_bell_metal(2.0, 140.0, 1.2) + thud, release_s=0.1)


def top_tree() -> np.ndarray:
    t = _time(0.8)
    knock = _modes(t, ((230.0, 1.0, 28.0), (382.0, 0.6, 34.0), (611.0, 0.4, 40.0)))
    leaves = _band_noise(t.size, 2000.0, 7000.0, seed=91) * np.exp(-5.0 * t) * 0.25
    return _fade(knock + leaves)


def _scatter(seconds: float, seed: int, count: int, low_hz: float, high_hz: float) -> np.ndarray:
    t = _time(seconds)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(t)
    for _ in range(count):
        start = rng.uniform(0.0, seconds * 0.6) ** 1.5 / (seconds * 0.6) ** 0.5
        hz = rng.uniform(low_hz, high_hz)
        piece = _modes(t, ((hz, rng.uniform(0.3, 1.0), rng.uniform(30.0, 70.0)),))
        out += _at(t.size, start, piece)
    return out


def debris() -> np.ndarray:
    return _fade(_scatter(0.9, 101, 9, 700.0, 2500.0))


def glass() -> np.ndarray:
    t = _time(1.0)
    shatter = _band_noise(t.size, 3000.0, 10000.0, seed=111) * np.exp(-18.0 * t) * 0.5
    return _fade(_scatter(1.0, 112, 30, 3000.0, 9000.0) + shatter)


def land() -> np.ndarray:
    t = _time(0.45)
    springs = _modes(t, ((62.0, 1.0, 9.0), (300.0, 0.5, 30.0), (1400.0, 0.15, 60.0)))
    return _fade(springs + _band_noise(t.size, 100.0, 900.0, seed=121) * np.exp(-30.0 * t) * 0.4)


def door_open() -> np.ndarray:
    t = _time(0.3)
    latch = _modes(t, ((2100.0, 1.0, 120.0), (3400.0, 0.5, 160.0)))
    return _fade(latch + _at(t.size, 0.04, _modes(t, ((900.0, 0.4, 60.0),))))


def door_shut() -> np.ndarray:
    t = _time(0.45)
    thud = _modes(t, ((88.0, 1.0, 14.0), (210.0, 0.5, 22.0)))
    latch = _at(t.size, 0.015, _modes(t, ((2300.0, 0.4, 140.0),)))
    return _fade(
        thud + latch + _band_noise(t.size, 200.0, 1200.0, seed=131) * np.exp(-40.0 * t) * 0.3
    )


def indicator() -> np.ndarray:
    t = _time(0.05)
    relay = _band_noise(t.size, 1500.0, 4500.0, seed=141) * np.exp(-260.0 * t)
    return _fade(relay + _modes(t, ((1100.0, 0.8, 200.0),)), release_s=0.005)


def wrong_way() -> np.ndarray:
    t = _time(0.5)
    buzz = np.tanh(4.0 * np.sin(TAU * 220.0 * t)) * ((t < 0.18) | ((t > 0.26) & (t < 0.44)))
    return _fade(np.convolve(buzz, np.ones(4) / 4.0, mode="same"))


def octopus() -> np.ndarray:
    """The card reader's double beep at the delivery: lower and softer than the meter's pip."""
    t = _time(0.3)
    beep = np.sin(TAU * 1250.0 * t) * ((t < 0.08) | ((t > 0.14) & (t < 0.22)))
    return _fade(np.convolve(beep, np.ones(8) / 8.0, mode="same"), release_s=0.01)


def coin() -> np.ndarray:
    t = _time(0.3)
    return _fade(
        _modes(
            t, ((3150.0, 1.0, 22.0), (4350.0, 0.7, 28.0), (5800.0, 0.5, 34.0), (7400.0, 0.3, 40.0))
        )
    )


# ------------------------------------------------------------------ the table

# name -> (synthesiser, peak). A cabin sound's peak is its level (it is not a 3D voice).
LOOPS: dict[str, tuple[Callable[[], np.ndarray], float]] = {
    **{f"horn_{kind}": (lambda kind=kind: horn(kind), spec[3]) for kind, spec in HORNS.items()},
    **{f"engine_{int(rpm)}": (lambda rpm=rpm: engine(rpm), 0.6) for rpm in ENGINE_RPMS},
    "engine_ev": (ev_whine, 0.3),
    "skid": (skid, 0.5),
    "wind": (wind, 0.5),
    "scrape": (scrape, 0.5),
}
SHOTS: dict[str, tuple[Callable[[], np.ndarray], float]] = {
    "flag_down": (flag_down, 0.45),
    "flag_up": (flag_up, 0.4),
    **{f"hit_tap_{v}": (lambda v=v: hit_tap(v), 0.6) for v in (1, 2)},
    **{f"hit_bump_{v}": (lambda v=v: hit_bump(v), 0.8) for v in (1, 2)},
    **{f"hit_crash_{v}": (lambda v=v: hit_crash(v), 0.95) for v in (1, 2)},
    "top_car": (top_car, 0.6),
    "top_railing": (top_railing, 0.6),
    "top_tram": (top_tram, 0.8),
    "top_tree": (top_tree, 0.6),
    "debris": (debris, 0.5),
    "glass": (glass, 0.5),
    "land": (land, 0.7),
    "door_open": (door_open, 0.4),
    "door_shut": (door_shut, 0.6),
    "indicator": (indicator, 0.25),
    "wrong_way": (wrong_way, 0.3),
    "octopus": (octopus, 0.3),
    "coin": (coin, 0.3),
}


def pcm(signal: np.ndarray, peak: float) -> bytes:
    """`signal` as signed 16-bit mono, its peak at `peak`."""
    scaled = signal * (peak * 32767.0 / max(float(np.max(np.abs(signal))), 1e-12))
    return np.round(scaled).astype("<i2").tobytes()


def smpl_chunk(rows: int) -> bytes:
    """One forward loop over the whole file: RIFF's sampler chunk."""
    header = struct.pack("<9I", 0, 0, round(1e9 / RATE_HZ), 60, 0, 0, 0, 1, 0)
    loop = struct.pack("<6I", 0, 0, 0, rows - 1, 0, 0)
    body = header + loop
    return b"smpl" + struct.pack("<I", len(body)) + body


def write(path: Path, frames: bytes, loop: bool) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE_HZ)
        out.writeframes(frames)
    if loop:
        data = path.read_bytes() + smpl_chunk(len(frames) // 2)
        path.write_bytes(data[:4] + struct.pack("<I", len(data) - 8) + data[8:])


def rendered() -> dict[str, tuple[bytes, bool]]:
    """Every file's frames, by name, and whether it loops."""
    out = {name: (pcm(make(), peak), True) for name, (make, peak) in LOOPS.items()}
    out.update({name: (pcm(make(), peak), False) for name, (make, peak) in SHOTS.items()})
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (frames, loop) in rendered().items():
        write(OUT_DIR / f"{name}.wav", frames, loop)


if __name__ == "__main__":
    main()
