# beams.tres

Rationale for `game/tuning/beams.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How many thrown beams the renderer can actually pay for, and how `BeamBudget`
hands them out (`P3-11e`). A tuning resource rather than a constant because it
is a **hardware fact with a number in it**, and hard rule 4 puts those in
`.tres`: Forward Mobile pairs a fixed list of spot lights per rendered object
and the fragment shader loops that list, so the ninth light on an object is not
dimmer — it is **absent**, with no warning and no fallback.

⚠️ The competition is per *object*, and the road under the car is one object —
the whole region until `P5-6`, one 150 m chunk since. Every beam on the same
chunk therefore contends for the same list, and the budget stays as that
bound. Two lamps a car makes `max_spot_lights` a **car** count once divided,
and that is why this cannot be left to `distance_fade` — fade bounds who
competes, it does not cap how many win.

⚠️ EVERY KEY BELOW IS REQUIRED. `beam_profile.gd` declares no defaults, so a
missing key reads as zero, and `BeamBudget.adopt` refuses the table on a zero
`regrant_hz` — no rig is ever granted — rather than fall back to a literal.
`max_spot_lights` may legally be 0 (light nothing) and `swap_margin_m` 0.0, so
those two are required to be present and are not guarded.
`verify_beam_budget.gd` reads this file, refuses a shipped cap or rate of zero
(its checks would pass vacuously on a cap of 0), pins this path equal to
`BeamProfile.PATH` and `BeamBudget.PROFILE_PATH`, and proves a zeroed
`regrant_hz` grants nothing.

⚠️ **This file was EMPTY from `Q119` until `Q150`, and nothing noticed.** It was
committed with these three values; an editor save then dropped every key,
because Godot's writer omits any key equal to the script's `@export` default,
and the profile script carried the same numbers as defaults. The game ran on
the script's copy the whole time. Removing the defaults is what makes the file
keep its values across a save — a second copy is not a safety net, it is the
reason the first copy can vanish unseen.

## `max_spot_lights = 8`

8 is measured, not quoted: brightness was linear to eight and **exactly zero**
from the ninth. Lower it to buy headroom for anything else that throws a spot;
raising it past the driver's own limit buys nothing and hides the cliff again.

## `regrant_hz = 6.0`

⚠️ **Deliberately not every frame.** The ranking is a sort over every car with
a lamp rig, and beams that re-rank at frame rate *swap* at frame rate — a car
a metre either side of the cut flickers as the order churns. Slow enough that
a swap reads as a car arriving, fast enough that it has arrived before the
player is past it.

## `swap_margin_m = 8.0`

Hysteresis, and the reason two cars driving abreast do not trade beams every
regrant. Costs nothing when the field is not tied, which is most of the time.
