# skills.tres

Rationale for `game/tuning/skills.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The skill bonuses' dwells, bars and prices (`P3-49`, `Q145`) — what a drift, a run at speed and an
early arrival pay into the tip. Ours, like `fares.tres`, and every number below is a first guess
ahead of the user's drive; what is not a guess is the shape: each skill is a flat HK$ per event
(the user's call over `GAME_DESIGN.md`'s style chain), paid the moment it is earned, and a bail
forfeits the lot.

The one number NOT here is the drift's angle: `HandlingProfile.drift_slip_threshold_deg` (14°)
is the design target the skidpad grades dwell against (`Q84`), and this table reads it rather than
restating it.

⚠️ EVERY KEY BELOW IS REQUIRED. `skill_profile.gd` declares no defaults, so a missing key reads as
zero, and `FareSystem` refuses to run on a zero dwell, bar or price rather than fall back to a
literal.

## `drift_s = 1.0`

A slide must hold at or over the threshold for a second before it pays, and pays again each
further second. The skidpad's shipped drift dwells 0.57–0.85 s (`Q84`, `Q86`), so a tap does not
pay and a held slide on Hennessy does — every second of it, which is `GAME_DESIGN.md`'s
"points per second" as money.

## `drift_hkd = 5.0`

Ten seconds of the time tip. A one-second slide is worth a block driven fast; a five-second one
is worth half a short hop's allowance, which is what makes the corner worth taking sideways.

## `speed_min_kph = 80.0`

Above the drift's fade (`drift_fade_from_kph` 65) and well under `max_speed_kph` 140: Gloucester
Road pays it, Hennessy between the trams does not, which is the route choice `GAME_DESIGN.md`
asks for.

## `speed_hold_s = 3.0`

Three seconds at the floor is 67 m; a burst between two junctions does not pay, a straight held
does, and pays again every three seconds it is held.

## `speed_hkd = 5.0`

The drift's price: a second sideways and three seconds flat out are the same money, so neither
route is the only one worth driving.

## `early_share = 0.5`

Half the allowance left at the door. Par is 30 kph over the legal route (`fares.md`), so half the
clock left is a 60 kph average or a shortcut — the two things the tip is for, paid once more at
the end so the receipt has a line that says so.

## `early_hkd = 10.0`

Twice a skill: arriving well early is the trip's point, and the receipt should show it as the
biggest single line under the time itself.
