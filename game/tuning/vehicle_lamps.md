# vehicle_lamps.tres

Rationale for `game/tuning/vehicle_lamps.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The taxi's lamp dials (`P3-11d`): the indicators, the roof sign, the light probe
that runs the lighting ladder, and the side lamps' share of the thrown beam.
These were `@export` defaults in `vehicle_lamps.gd` until `Q150` moved them,
against `ARCHITECTURE.md`'s Constraint 4 — tuning is data. How bright a lamp is
and how far it reaches are NOT here: those are the fitting's, authored beside
its position and cone in `taxi.tscn` and read once in `_ready`, so a roster car
can carry a dimmer or narrower beam without a second export. This file is what
the *state* does to whatever the lamp was authored at. `lamps.tres` beside it
is the street lamps' material and nothing to do with the car.

⚠️ EVERY KEY BELOW IS REQUIRED. `vehicle_lamps_profile.gd` declares no defaults,
so a missing key reads as zero, and the rig refuses to run at all on a zero
`blink_hz`, `blink_duty`, `sun_probe_m`, `cover_probe_m` or `probe_hz` — every
lens dark, no cone, no slot asked of `BeamBudget` — rather than fall back to a
literal (`VehicleLamps.usable`). The other nine keys have an export floor of
0.0, so a chosen zero is legal and a missing one cannot be told from it: they
are required to be present and are not guarded. `verify_vehicle.gd` reads this
file, asserts the scene hands the rig this very resource, and proves a zeroed
`probe_hz` reads unusable.

## `blink_hz = 1.5`

UK and Hong Kong regulation puts a real indicator between 1 and 2 Hz, and the
middle of that is also what reads as a flash rather than as a flicker at the
frame rates this ships at.

## `blink_duty = 0.55`

Above a half on purpose: an indicator seen from behind at speed is a small
object, and the eye needs longer on than off to call it a light rather than a
glint.

## `steer_threshold = 0.35`

A fraction of the lock available at this speed (`VehicleController.steer_ratio`)
rather than an angle, because full lock at 140 km/h is a quarter of full lock
parked.

⚠️ The floor on this is comfort, not correctness. Set it near zero and the
indicators strobe through every steering correction the player makes on a
straight, which is what a real driver does *not* do.

## `steer_hold_s = 0.3`

⚠️ **The threshold above cannot do this job on its own, and that is why both
exist.** One says how hard a turn is, the other says how long it lasts, and an
arcade car crosses hard lock constantly — a flick round a parked lorry, a
correction out of a drift, a lane change. Every one of those trips the
threshold, and without a hold the tail of the car strobes amber through all of
them, which is worse than no indicator at all: it stops meaning "turning".

The cost is that the lamp is late by exactly this much, which is fine — a real
driver indicates before turning and this car indicates after, so it is already
a read-out of what the car is doing rather than a signal of intent.

⚠️ **0.3 rather than the 0.5 this shipped at, on the user's call** — the lamp
read as late from the chase camera. That buys back 0.2 s of the lateness above
and spends it on the other side of the same trade: a flick round a parked
lorry now has to be shorter than a third of a second to stay dark, where it
had half a second before. What still refuses a straight-line correction is
`steer_threshold`, which rejects on *amplitude* rather than on duration — the
hold was never the only guard, which is why it can be shortened without the
indicators strobing.

## `sign_lit = 0.45`

⚠️ **The one circuit on this car that answers to neither the driver nor the
light, and that is what it is for.** A roof sign says the car is a taxi and
whether it is in service; it is not a read-out of steering, of the pedal, or
of whether the sky is shut out. It answers to `for_hire` alone, which the
fare loop writes (`TaxiHire`): lit while the car is plying for hire, dark with
a passenger aboard — the Hong Kong taxi's "TAXI" lamp, which the meter flag
puts out.

⚠️ **A level rather than a switch, and the reason is the one thing every other
circuit wants and this one must not have: bloom.** `lamp_emission` is 1.6
against `clean_daylight.tres`'s glow threshold of 1.0, so a lens driven to 1.0
carries a halo — which is what makes a brake lamp read as a lamp rather than
as paint, and is exactly what makes a roof sign read as a headlamp bolted to
the roof. Shipped full, in sun, it was reported as precisely that.

Under about **0.63** the emission lands below the threshold and the sign
brightens without glowing, which the shader's own note calls "merely a
brighter swatch" — a fault for a lamp and the whole brief for a sign. 0.45
sits clear of the knee rather than on it, so the tonemap has room before the
halo comes back.

⚠️ **This is not the place to make the sign dimmer in daylight.** A level that
tracked the lighting ladder would put the sign back on it, which is the one
thing the paragraph above refuses. This is how bright the sign burns *when* it
is lit; whether it is lit is `for_hire`, and the sun owns neither.

## `sun_probe_m = 200.0`

⚠️ **Bounded by where collision exists, not by where shadow does.** Only the
finest tile tier ships a collider (`city_streamer.gd`), and `streaming.tres`
puts that band at 250 m — so a ray longer than this passes through the coarse
tiles beyond it as if they were air and reports sun. 200 m keeps the probe
inside the band with room for the hysteresis distance. It is not enough for
every caster: `golden_hour.tscn`'s sun sits at 30°, so anything over about
115 m casts further than this ray reaches and its far shadow reads as sunlit.
Raising it past the collider band cannot fix that, and a taller number would
only look like it had.

## `cover_probe_m = 25.0`

Sized to a road deck rather than to a building: this asks whether something
is *over* the car, and the tallest thing that legitimately is — an elevated
carriageway, the HKCEC's overhang — is tens of metres up, not hundreds.

⚠️ **Long is not safer here.** Extend it and the probe starts finding the
upper storeys of whatever the car is parked beside the moment the footprint
overhangs the kerb, which puts the taxi on main beam in open sun.

## `probe_height_m = 1.0`

Clear of the car's own roof — `taxi.tscn`'s body box tops out at 0.70 m — so
the rays begin outside the shell rather than relying on the probe's
self-exclusion to save them. Belt and braces, and it costs nothing.

## `probe_hz = 10.0`

The one thing in the rig that *asks* the world rather than reading what was
written to it, and `dark_hold_s` already refuses to believe a single reading.
10 Hz puts several samples inside the shortest hold, which is all the hold can
use.

Measured on the built region with 65 tier-0 tiles resident: the 25 m cover ray
costs **0.49 µs** and the 200 m sun ray **0.91 µs**, against 0.50 µs for one of
the four wheel rays the controller already casts every tick. So a probe is
worth about three wheel rays, twenty times a second.

⚠️ **Every car on this script probes on the same tick, and that is left
alone deliberately.** `_probe_due_s` starts at zero on every instance, so a
roster spawned in one frame stays in lockstep for the life of the process —
~28 µs on one tick at twenty cars rather than 1.4 µs amortised. The obvious
fix is a random starting phase, and it is **refused**: `.claude/skills`'
driver runs are byte-deterministic and this project grades frames by `cmp`,
so a per-run phase would make the moment a lamp switches unreproducible to
buy ~1% of a frame on the device floor. Stagger it from something stable —
the node path, a spawn index — if `P3-3` ever makes it matter.

## `dark_hold_s = 0.35`

Short, because being late into a dark place is the failure a driver notices.

## `light_hold_s = 1.6`

⚠️ **Deliberately several times `dark_hold_s`, and the asymmetry is the whole
anti-flicker mechanism.** A street in Wan Chai is a picket fence of shadow —
kerbside towers, gantries, footbridges, the gaps between them — and a car at
50 km/h crosses one every second or so. Symmetric holds would strobe the
lamps through all of it, which is the failure `steer_hold_s` above already
records for the indicators: a lamp that switches constantly stops meaning
anything. Lingering on the way out costs a few seconds of lamps in sunlight
and buys a lamp that only changes when the light really has.

## `sidelamp_beam = 0.3`

⚠️ **The only beam dial here, because the scene owns the rest.** This is the
one number that belongs to the *state* rather than to the fitting: what
`SHADOW` does to whatever the lamp was authored at.

⚠️ It shipped the other way round for a moment, and the asymmetry was silent:
reach came from the scene while energy came from an export, so the authored
`light_energy` was overwritten before the first frame and editing it did
nothing at all.

⚠️ **Not zero, and not much above it.** Position lamps exist to be *seen*, not
to see by, so a side lamp that lights the road as far as a headlamp erases the
difference the two circuits were split to express. A short dim pool says "lit,
but not driving on it".

## `night_energy = 0.05`

⚠️ **A dial rather than a rule, because the rig that would trip it does not
exist yet.** `DECISIONS.md` records night as a *switch between two static
rigs*, so whatever `Q26` authors is what this has to answer to; a rig that
dims its key light is caught here, and one that drops the sun below the
horizon is caught by the elevation test in `read_rig` beside it. The two
shipped rigs measure 1.4 and 0.9, so both clear this by a wide margin.

⚠️ A rig that deletes its `DirectionalLight3D` outright is **not** caught, and
that is deliberate rather than an oversight — see `read_rig`.

## `tail_lit = 0.35`

The tail lamps (`Q160`): with the front lamps on, the brake lenses burn at this share of the
brake's 1.0. A floor under the brake circuit rather than a lens of its own — which is what a tail
lamp is — because a car at dusk with dark tails until it brakes reads as unlit. 0.35 x
`lamp_emission` 1.6 is 0.56, under the glow threshold, so braking still visibly gains the bloom.
May legally be 0.0 (no tail lamps), so it is one of the keys `usable()` cannot guard.

## `night_energy = 0.4` (was 0.05)

Raised with `Q160`: the night keyframe keeps a moon at 0.30 for the form it gives the blocks, and
a bar at 0.05 would call that day and leave the car probing for the moon's shadow. 0.4 sits
between the moon and the dusk sun's 0.80, so the main beams come on part-way down the dusk.
`verify_day_cycle.gd` holds the last keyframe under this bar.
