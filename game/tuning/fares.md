# fares.tres

Rationale for `game/tuning/fares.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The fare loop's radii, dwells, bars and rates (`P3-1a`, `Q141`) — the numbers that are ours, as
against `tariff.tres`, which is Transport Department's. Every one below is a first guess ahead of
the user's drive, and the drive is what grades them; what is not a guess is the shape: the
allowance is road distance over a par speed, and the tip is seconds left times a rate, so a
shortcut and a fast run pay through the same number. `par_kph` is the one measured value.

⚠️ EVERY KEY BELOW IS REQUIRED. `fare_profile.gd` declares no defaults, so a missing key reads as
zero, and `FareSystem` refuses to run on a zero radius, bar or rate rather than fall back to a
literal.

## `hail_radius_m = 12.0`

Plan distance from the car to the pickup's stop point — `nearest_edge` at `edge_t`, on the road,
not the kerbside `pos`. A car length and a half: wide enough that stopping anywhere alongside a
stand hails, narrow enough that two stands 30 m apart on one street stay two.

## `board_s = 1.0`

The passenger walks to the car. One second is a beat, not a wait: long enough that the hail is
seen before the clock starts, short enough that a stopped car is not idling.

## `deliver_radius_m = 12.0`

The same reach at the other end. Not tighter: the destination is announced by name and found
by memory (`GAME_DESIGN.md` pillar 1), and a radius that demanded a precise stop would turn a
found destination into a parking test.

## `stop_below_kph = 5.0`

A walking pace. Read at both ends: a passenger boards a stopped taxi and leaves one. Under
this the car may still be creeping into the kerb.

## `min_trip_m = 300.0`

The shortest legal route a destination may be drawn at. `GAME_DESIGN.md` names 191 m as
"barely a trip"; 300 m is a block and a turn. A pickup from which the legal network reaches
no destination at this bar is **stranded** — dropped from the pickup pool as it is drawn, kept as a
destination, and named by `verify_fares` and by the boot line. On the shipped regions that is three westbound points on
Hennessy and Johnston Road at Wan Chai's west edge and two of Causeway Bay's far-side stands,
whose forward direction leaves the clip; raising this bar strands more, and lowering it is not
how a stranded stand is answered (`.claude/rules/fares.md`).

## `par_kph = 19.0`

The speed the allowance is priced at over the legal route — the allowance IS that, with no floor
(the user's call, 2026-11-12). **Measured** (`Q203`): the AI traffic, which obeys every light and
give-way, driven headless at four seeded points over the merged runtime for 3 minutes a side, two
seeds, each car's run of 200 m or more metered as plan metres over seconds, kerbside stops left
out. The median run is 18.8 kph at 18:00 and 19.2 at 12:00 (p25 14.2 / 15.3, p75 24.6 / 26.7, p90
30.8 / 33.8; the whole fleet 15.7 / 17.3), stood mostly behind another car (21 / 16% of its time)
and at a light (14 / 16%). So par is a cab in this city's traffic obeying the signs, and the
player beats it by driving better or breaking the rules. It was 30 until then, a first guess that
turned out to be the legal traffic's 90th percentile; with no floor it is the whole clock.

## `tip_hkd_per_s = 0.5`

What each second left at delivery pays. Sized against the meter, which reads HK$29 for nearly
every trip inside the flagfall: when it was set a 600 m standard fare had a 72 s allowance, and
driven at a 60 kph average arrived with 36 s left, an HK$18 tip (at par 19 the same drive has
114 s and arrives with 78 s, HK$39) — the skill half is the same order as the
base, which is the point. `P3-2b`'s style chain adds to the same tip.

## `sample_hz = 5.0`

How often the loop asks the graph. `hud.gd`'s `STREET_HZ`, for its reason: at 100 kph a sample
is 5.5 m apart, well inside both radii. The meter and the clock run every physics tick; only the
`nearest_edge` and `route` calls are sampled.

## `live_pickups = 4`

How many customers wait at once (`Q203`), each drawn with where they are going; one boarding
takes them off the kerb and the fare's end draws a replacement. Four pins on the map and four
rings in the street: enough that one is usually near, few enough that each is a place to drive to
rather than a carpet. Kept at 4 on the user's call (2026-11-13) against a measured curve, before
`place_m` kept them near the car: legal-direction route metres from a fare's end to the nearest
of N drawn city-wide on Wan Chai, against a 1,197 m median trip — N = 2: 892 m p50; 4: 656 m;
6: 571 m; 8: 489 m. Each step past 4 bought less. Since `place_m` the distance is set by that
radius instead, and this is only how many pins.

## `place_m = 160.0`

Plan metres from the car within which a new customer is placed (the user's ask, 2026-11-13:
"there is always 4 nearby as the car is moving"; "the farest one is removed and a new one is
placed when necessary"). Half the minimap's `span_m` (320 m across a heading-up slot), so a
customer placed shows on the map at once. Measured against the kerbs: 5% of Wan Chai's and 6%
of Causeway Bay's kerbs have fewer than four others within 160 m (p10 four and six), against
37% / 21% at 100 m. Where none is free within it, the nearest free kerb is placed instead.

## `retire_m = 320.0`

Plan metres past which the farthest waiting customer leaves and one is placed within
`place_m` — a swap, one a sample, and none while no free kerb is within this distance (the
clip, the harbour), or a far placement would be removed every sample. The minimap's whole
span: twice `place_m`, so a customer placed at its edge survives the car turning away, and
one is dropped only once off the map's long way too. `FareSystem` refuses it at or under
`place_m`.

## `street_share = 0.75`

The share of draws, waiting customers and destinations alike, taken from `fares.json`'s street
spots (387 on the merged runtime, 2026-11-13) rather than the published stands and PUDO points (27 that may be
hailed at): three of four waiting customers flag a cab off a stand, and one in four still waits
at a stand, which Hong Kong has plenty of. Kept on the user's call (2026-11-13): no published
figure splits stand from street. The nearest is TD's 2024–25 point-to-point study (LegCo Panel
on Transport paper, 18 July 2025, para 6): of drivers who take app orders, about a third of
trips come by app and "over 60%" by "passengers hailing taxis directly on the street", which
counts the stands in too. Drawing every place alike would be about 0.92. 0 is the off switch — the published points alone, as
before `Q203` — and is why this is the one key `FareSystem` does not refuse at zero.
