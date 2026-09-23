# fares.tres

Rationale for `game/tuning/fares.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The fare loop's radii, dwells, bars and rates (`P3-1a`, `Q141`) — the numbers that are ours, as
against `tariff.tres`, which is Transport Department's. Every one below is a first guess ahead of
the user's drive, and the drive is what grades them; what is not a guess is the shape: the
allowance is road distance over a par speed with a floor, and the tip is seconds left times a
rate, so a shortcut and a fast run pay through the same number.

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
"barely a trip"; 300 m is a block and a turn. A pickup that reaches no destination at this bar is
**stranded** — dropped from the pickup pool at load, kept as a destination, and named by
`verify_fares` and by the boot line. On the shipped regions that is three westbound points on
Hennessy and Johnston Road at Wan Chai's west edge and two of Causeway Bay's far-side stands,
whose forward direction leaves the clip; raising this bar strands more, and lowering it is not
how a stranded stand is answered (`.claude/rules/fares.md`).

## `par_kph = 30.0`

The speed the allowance is priced at over the legal route. Deliberately slow — a taxi in
Wan Chai traffic, obeying the signs — so the allowance is beatable by driving well and the
tip is real. At 60 kph average on a 600 m fare, half the allowance is left.

## `short_hop_floor_s = 30.0`

`GAME_DESIGN.md`'s short-hop allowance, now the least a `pudo` destination gets: over 250 m of
route the distance term is larger.

## `standard_floor_s = 60.0`

`GAME_DESIGN.md`'s standard allowance, the least a `taxi_stand` destination gets; the distance
term takes over past 500 m.

## `tip_hkd_per_s = 0.5`

What each second left at delivery pays. Sized against the meter, which reads HK$29 for nearly
every trip inside the flagfall: a 600 m standard fare has a 72 s allowance, and driven at a
60 kph average it arrives with 36 s left, an HK$18 tip — the skill half is the same order as the
base, which is the point. `P3-2b`'s style chain adds to the same tip.

## `sample_hz = 5.0`

How often the loop asks the graph. `hud.gd`'s `STREET_HZ`, for its reason: at 100 kph a sample
is 5.5 m apart, well inside both radii. The meter and the clock run every physics tick; only the
`nearest_edge` and `route` calls are sampled.
