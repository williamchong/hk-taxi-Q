# street_tracker.tres

Rationale for `game/tuning/street_tracker.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The street plate's dwell (`P3-24`, `P5-26`) — `street_tracker.gd`'s one
constant until `Q124`'s re-read counted it against `ARCHITECTURE.md`'s
Constraint 4. ⚠️ THE KEY BELOW IS REQUIRED: `street_tracker_profile.gd`
declares no default, and the tracker refuses a zero dwell.

## `dwell_s = 0.6`

How long a different street must stay nearest before the plate follows it.
Not a distance. A dwell in metres is speed-invariant and sounds more
principled, but the artefact being suppressed is visual — a name changing
faster than it can be read — and that is a property of seconds. At 50 kph
this is ~8 m, comfortably inside a junction mouth and well short of the
region's ~50-150 m blocks. `CityStreamer`'s hysteresis is the same idea
against the same failure.
