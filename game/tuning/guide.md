# guide.tres

Rationale for `game/tuning/guide.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The world-space guide to the fare (`P3-5a`, `Q142`, the user's calls of 2026-09-24): the arrow over
the taxi grows and turns green as the target nears, and a ring pulses on the road where the
customer waits or the passenger gets out. Both read distance in plan metres from the car to the
stop point. The colours are the guide's own — red far, green near — and not the map's pips, which
keep amber for the pool and red for the destination.

⚠️ EVERY KEY BELOW IS REQUIRED. `fare_guide_profile.gd` declares no defaults, so a missing key reads
zero, and `verify_hud.gd` refuses a zero it would draw with.

## `near_m = 30.0`

Inside this the guide is at its near look; beyond `far_m` (400 m — a long fare inside the region
is ~1.5 km, so most of a trip reads "far" and the change is the last few blocks) at its far. A
first guess ahead of the user's drive.

## `arrow_near_m = 2.4`

The arrow's length near and far (`arrow_far_m` 1.0): a flat unshaded arrow at 2.6 m over the car
reads small from the chase camera, so it grows as it starts to matter.

Every pending customer gets a ring too while no one is aboard (the user's call: all of them, like
a map), in the map's amber, as one multimesh; the destination's ring alone takes the guide's
distance colour.

## `ring_radius_m = 4.0`

The ring on the road: a car length across, `ring_width_m` 0.6 wide, floated `ring_lift_m` 0.08
above the surface — the road's own paint is lifted less, and this sits over it. It pulses at
`pulse_hz` by `pulse_depth` of its size, alpha-blended at `ring_alpha`.
