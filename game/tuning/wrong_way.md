# wrong_way.tres

Rationale for `game/tuning/wrong_way.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The wrong-way sign's bars and dwells (`Q81`, `P5-26`). These were constants in
`wrong_way_monitor.gd` until `Q124`'s re-read counted them against
`ARCHITECTURE.md`'s Constraint 4 — tuning is data. The look of the sign is
`hud_style.tres`'s `warn_*` keys; this file is when it goes up and comes down.

⚠️ EVERY KEY BELOW IS REQUIRED. `wrong_way_profile.gd` declares no defaults, so
a missing key reads as zero, and the monitor refuses to construct on a zero
dwell or bar rather than fall back to a literal. `verify_hud.gd` reads this
file and asserts the two bars are 120 and 90 and not one number.

## `raise_s = 0.5`

Seconds and not metres, `street_tracker.gd`'s reasoning: the artefact being
suppressed is a sign appearing at a junction the player is driving straight
through, and that is a property of time. Long enough to cover a junction mouth
at speed, short enough that it is up while there is still road to correct on —
at 50 kph this is ~7 m, plus up to one sample interval of latency.

## `clear_s = 0.8`

⚠️ Deliberately longer than the raise, which is the hysteresis. Driving the
wrong way *through* a junction hands the monitor the cross street for a
moment, and a symmetric clear would blink the sign off in the middle of the
emergency it is reporting. A sign that flickers reads as a glitch rather than
as an instruction.

## `angle_deg = 120.0`

The nose only; the wheels are judged against `correcting_angle_deg`, a
different question and deliberately a different number.

🔴 Not 90, and this is the number that stops a turn from ringing the alarm. A
car turning across or crossing a one-way street passes through perpendicular,
and everything past 90 degrees would be "against" — so a legal right turn over
a one-way carriageway would raise a warning halfway round. At 120 the car has
to be pointed substantially back down the street before anything happens,
which is what actually being on it the wrong way looks like. The region is
93.5% one-way by drivable length, so the false alarm is the failure mode.

## `min_kph = 10.0`

Below this the car is not going anywhere and its velocity is noise. Read on
the withholding side only: a car slower than this cannot be "already
correcting", so the sign stands — which is what a car stopped dead facing the
wrong way should get, since being stationary is not being right.

## `correcting_angle_deg = 90.0`

🔴 A second bar, and reusing the 120 above was a defect. "Already correcting"
is not the complement of "pointed the wrong way": at 120 a car pointed fully
backwards while sliding sideways — 90 degrees off the law, a drift through a
junction — counted as carrying itself back the legal way, and the sign was
withheld from exactly the moment it is for. The withholding case is the
reverse out of a mistake, where travel is squarely with the flow, so the bar
is the neutral split and nothing wider. Found by mutation: dropping the nose
bar to 90 left every assertion green, because this one absorbed the change.
