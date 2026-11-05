# taxi_audio.tres

Rationale for `game/tuning/taxi_audio.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The taxi's own sounds (`P3-79`, `Q185`): what `TaxiAudio` plays off the car and what `TaxiHire` plays
off the fare. The files are `tools/make_vehicle_sounds.py`'s; this table is how they are played.

⚠️ EVERY KEY THAT `TaxiAudioProfile.usable` NAMES IS REQUIRED: the profile declares no defaults, a
missing key reads as zero, and the taxi stays silent on one rather than run on a literal. The decibel
levels and `hybrid` are not guarded: 0 dB and off are real choices, so Godot's writer drops them
(`impact_db = 0.0` is absent for that reason).

None of it is graded by a number. Every level is a first pass by reasoning, owed the user's ear.

🔴 **What is always there sits under what happens** (the user's call, 2026-11-06: "make the noise that
consistently appear less distracting compared to event based one"). The loops that run the whole
drive — the engine, the EV whine, the wind — are 10–20 dB under the one-shots, and the squeal a little
under them too; a horn, a crash or the flag is what the ear should catch. Raise a loop only against a
drive, never on its own.

## `hybrid` (absent: off)

Off is the Crown Comfort LPG's four through its 4-speed automatic, the car `crown_comfort.tres`
describes, so the engine is the car's own. On is the Comfort Hybrid's: the EV whine, the engine
cutting in on a CVT drone. The user's call between the two was left open on 2026-11-05; the car
decided the default.

## `loop_rpms = (1050, 2520, 5040)`

Mirrors `make_vehicle_sounds.ENGINE_RPMS`. Each is an rpm at which an engine cycle (two crank turns)
is a whole number of samples at 22,050 Hz, so a loop of whole cycles joins itself. Crossfaded between
neighbours (`loop_mix`), so no loop plays far from its own rpm: 0.76× at idle, 1.19× at the redline.

## `idle_rpm = 800.0`, `redline_rpm = 6000.0`

A 1TR-FPE's: idle around 750–800, red line at 6,000 (`rev_limiter.tres` holds the wheels, not this).

## `rpm_per_kph = (103, 55, 37, 27)`

`crown_comfort.tres`' own derivation: the Toyota 4-speed's ratios (≈2.8 / 1.5 / 1.0 / 0.73) and the
final drive (≈4.3) on 0.31 m wheels — 8.56 wheel rpm per kph. Typical figures, not the car's
published ones, as the car's own table says. Top gear at 140 kph is about 3,800 rpm.

## `upshift_rpm = 4000.0`, `upshift_light_share = 0.6`, `downshift_rpm = 1200.0`

A pedal-down change at 4,000 (1st to 39 kph, 2nd to 73, 3rd to 108); a light pedal changes at 2,400.
A taxi is driven for fuel, not for the redline: at 5,000 the user heard "a ferrari more than a taxi"
(2026-11-06). ⚠️ The downshift must sit under the light change's landing rpm in the next gear, or the
box hunts: the lowest landing is 1→2 at 2,400 × 55 / 103 = 1,282, so 1,200 leaves 82 rpm. A lighter
`upshift_light_share` than 0.59 hunts; `verify_vehicle` sweeps it.

## `stall_rpm = 1800.0`

The torque converter lets the engine run to idle + 1,800 with the pedal down at rest, as an automatic
does off the line, before the wheels' speed takes it.

## `rpm_slew = 6000.0`

The heard rpm follows the box's at this rate, so a change up is a drop over about a sixth of a
second, which is what makes it read as a gear change and not a cut.

## `engine_db = -18.0`, `off_throttle_cut_db = 6.0`

The engine sits well under the horns and impacts: -4, then -12 on the user's call above, then -18 on
"need less engine noise" (2026-11-06). Lifting off drops it 6 dB, the cheapest way to hear
load without a second set of loops.

## `park_fade_s = 0.6`

Parked — the menu's showroom, HOME, REPORT — the taxi is silent, as its horn
already was (the user's call, 2026-11-06): the idle under the menu at `engine_db` read as a car
left running. The loops fall from where they stand to silence over this long and then pause,
so a shift ending into REPORT does not cut the engine mid-cycle; the one-shots already playing,
the payout's coins among them, finish. Back on the road the loops come up on the next tick.

## `ev_ref_kph = 50.0`, `ev_db = -20.0`, `engine_on_kph = 45.0`, `engine_on_throttle = 0.6`, `cvt_low_rpm = 1200.0`, `cvt_high_rpm = 4800.0`

The hybrid alone. Mirrors `EV_REF_KPH`. The engine starts over 45 kph or past 60% pedal, roughly
where a Toyota hybrid's does, and the CVT holds it by the pedal rather than by the speed: the drone.

## `skid_full_slip = 2.0`, `skid_db = -10.0`, `skid_pitch_rise = 0.15`

The squeal starts at `skid_marks.tres`' `mark_from_slip`, read from that file so the sound and the
marks start on the same tick, and is full at twice the tyre's peak. It rises 15% in pitch as it does.

## `skid_full_kph = 60.0`, `skid_slow_share = 0.3`, `skid_speed_pitch = 0.2`

The user's ask (2026-11-06): the squeal follows the speed as well as the angle. A slide at a crawl
keeps 30% of the level (a wheelspin still squeals) and is full by 60 kph; the pitch moves ±10% about
the slip's own pitch from a crawl to 60 kph. The angle is the slip: a car sideways slips more.

## `wind_from_kph = 30.0`, `wind_full_kph = 140.0`, `wind_db = -22.0`

Nothing under 30; full at the car's top speed. The quietest loop: at speed it never stops, and its file
is dark (nothing over 1 kHz) for the same reason.

## `tap_min_mps = 1.5`, `impact_cool_s = 0.25`

Under 5.4 kph into a contact is a nudge and silent. The tiers above it are `skills.tres`' bump and
crash bars (20 and 60 kph), the award's own, so the crash you hear is the one you are docked for. A
second hit inside a quarter second is the same impact rattling.

## `materials`

What a struck body is, by a piece of its node's name: the traffic's `car_<id>`, the trams'
`tram_<n>`, the parked library's `<kind>_col_<n>`, the trees' `<mesh>_trunks_<x>_<z>`, the fence's
`barrier_col_<n>`. First match wins; a body matching none is a wall, the dead thud alone. A name is
the cheapest tag every layer already writes; a metadata key would need every layer to set one.

## `scrape_from_mps = 1.0`, `scrape_full_mps = 10.0`, `scrape_db = -6.0`

The grind along a wall, by how fast the car slides along it.

## `land_min_air_s = 0.3`

A kerb hop is not a landing. `skills.tres`' `air_min_s` (0.5) pays; this sounds a little under it.

## `cabin_db = -2.0`

The cabin's sounds (the flag, the payout and the indicator relay) play at this, not positioned.

## `coin_hkd = 2.0`, `coin_max = 15`, `coin_gap_s = 0.07`, `coin_after_s = 0.35`

At the delivery a coin per HK$2 of tip, after the card reader's beep: a HK$22.50 tip is eleven coins
in under a second. Capped so the longest payout stays about 1.4 s.
