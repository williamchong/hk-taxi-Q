# skills.tres

Rationale for `game/tuning/skills.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The skill bonuses' dwells, bars and prices (`P3-49`, `Q145`; air `P3-51`, `Q147`) — what a drift,
a run at speed, a jump and an early arrival pay into the tip. Ours, like `fares.tres`, and every number below is a first guess
ahead of the user's drive; what is not a guess is the shape: each skill is a flat HK$ per event
(the user's call over `GAME_DESIGN.md`'s style chain), paid the moment it is earned, and a bail
forfeits the lot.

The one number NOT here is the drift's angle: `HandlingProfile.drift_slip_threshold_deg` (14°)
is the design target the skidpad grades dwell against (`Q84`), and this table reads it rather than
restating it.

⚠️ EVERY KEY BELOW IS REQUIRED. `skill_profile.gd` declares no defaults, so a missing key reads as
zero, and `FareSystem` refuses to run on a zero dwell, bar or price rather than fall back to a
literal.

## `drift_min_s = 2.0`

A slide must hold at or over the threshold for two seconds before it counts at all; a shorter
one pays nothing. The first table paid at one second, and on the user's drive that paid a flick
through a junction (2026-09-25, the user's call: a drift only counts when it is longer than a
threshold). The skidpad's shipped drift dwells 0.57–0.85 s (`Q84`, `Q86`), so a tap is well
under this, and a slide held through a corner on Hennessy is over it. Seconds, not metres,
because `Q84` grades the drift dial on dwell in seconds, and a distance bar would pay a fast
slide over a slow one for the same control — which is the speed skill's job.

## `drift_s = 1.0`

Once a slide has counted, it pays again each further second held — `GAME_DESIGN.md`'s "points
per second" as money. The first payment lands at `drift_min_s`, the second at
`drift_min_s + drift_s`, and so on; releasing the slide forfeits the part not yet paid.

## `drift_hkd = 5.0`

Ten seconds of the time tip. A two-second slide is worth a block driven fast; a five-second one
pays four times and is worth a short hop's allowance, which is what makes the corner worth
taking sideways.

## `speed_min_kph = 80.0`

Above the drift's fade (`drift_fade_from_kph` 65) and well under `max_speed_kph` 140: Gloucester
Road pays it, Hennessy between the trams does not, which is the route choice `GAME_DESIGN.md`
asks for.

## `speed_hold_m = 200.0`

The tariff's own unit (`tariff.tres` `step_m`): the speed skill pays once per 200 m driven at or
over the floor, and again each further 200 m, so it can never tick more often than the meter
does (2026-09-25, the user's call — the first table paid every 3 s, four times a meter tick at
the floor). Distance, not time, so a faster run pays sooner over the same road, which is the
skill. `verify_fares` refuses a value under `step_m`; raising it is a tuning pass, lowering it
past the tariff is not. At 80 kph a unit is 9 s; a burst between two junctions does not pay,
Gloucester Road held does.

## `speed_hkd = 5.0`

The drift's price: a second sideways past the qualifying two and 200 m flat out are the same
money, so neither route is the only one worth driving.

## `air_min_s = 0.5`

Every wheel off the ground for half a second before the flight counts, judged at the landing. A
kerb hop or a crest on Gloucester Road is a tenth or two; a drop off a flyover deck at street
speed is 0.8–1.2 s (a 6 m deck falls in 1.1 s on its own), so the bar sits between the two. Seconds
rather than metres, like the drift: the skill is the flight, and the speed skill already pays the
speed. Judged at the landing rather than paid in the air (`Q147`) so a car falling off the world
pays nothing and a roll — four wheels in the air, upside down — can be told apart.

## `air_s = 0.5`

Once a flight has counted, each further half second pays again, all at the landing: a jump off the
interchange pays twice, a hop off a kerb ramp once. The same repeat shape as `drift_s`.

## `air_hkd = 5.0`

The drift's and the speed's price: a qualifying flight is worth a second sideways past the two, so
the shortcut off a bridge pays for itself in the tip as well as on the clock. Paid only on an
upright landing — a jump that lands on the roof pays nothing, which is the whole of the crash
penalty's job until `P3-50` builds one.

## `early_share = 0.5`

Half the allowance left at the door. Par is 30 kph over the legal route (`fares.md`), so half the
clock left is a 60 kph average or a shortcut — the two things the tip is for, paid once more at
the end so the receipt has a line that says so.

## `early_hkd = 10.0`

Twice a skill: arriving well early is the trip's point, and the receipt should show it as the
biggest single line under the time itself.

## `bump_min_kph = 20.0`

The penalties (`P3-50`, `Q148`) read ONE number off the car: the speed into the wall on the tick
of the hit, `VehicleController.take_impact_mps`, the pre-step velocity's component along the
contact normal. Two bars on it make three tiers. Under this one a contact is a touch — free, no
flash, but it ends a slide so a car pinned sideways on a wall cannot farm the drift. The
skidpad's wall rows (`tools/skidpad.sh --only=wall`) put a 10° brush at 11.2 / 15.2 / 18.4 kph
into the wall from 63 / 86 / 105 kph entries, so 20 keeps every brush free at any speed the car
reaches, and a 30° clip at 63 kph reads 34.1, well over.

## `bump_hkd = 2.0`

A collision — a 30° clip at any speed, 34.1 to 53.9 kph into the wall on the pad — docks less
than one skill pays: a warning, not a wipe, since the design line says a hit costs speed and
never control and the tip should read the same way.

## `crash_min_kph = 60.0`

A head-on reads 69.5 / 90.5 / 108.3 kph into the wall from the three entries, and the hardest
30° clip 53.9, so 60 splits them at every speed measured. `FareSystem.setup` refuses a value at
or under `bump_min_kph`.

## `crash_hkd = 5.0`

One skill's worth: a heavy crash wipes the drift or the 200 m that paid before it, which is what
makes the wall matter without making the meter a punishment — the meter is never docked (`Q141`)
and the tip floors at zero.

## `crash_cool_s = 1.0`

One wall is one dock. The pad shows a head-on reporting two contact ticks and a brush eighteen to
twenty-four, all inside a second; a rebound off the same wall inside the window is the same
event. A second wall a second later is a second dock.
