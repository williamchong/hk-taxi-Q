# shift.tres

Rationale for `game/tuning/shift.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

特更 / THE SHIFT (`Q162`, the user's ask, 2026-10-11): a run from morning to night, then the total
fare weighed against the best. Read by `scripts/world/day_clock.gd` in `Mode.SHIFT` for the hours on
the HUD's clock; the shift's LENGTH is not here. It is `day_to_night.tres`'s `length_s`, the rig's,
so the clock on the dash and the sky end on the same game second and there is one number to move.
`--shift-s=<seconds>` compresses the whole shift for a frame of the handover.

## `opens_h = 7.0`

The shift opens at 07:00, the morning the user asked for. The rig opens on the authored daylight —
there is no dawn keyframe — so 07:00 is drawn as the day every frame so far was graded under.

## `closes_h = 21.0`

交更 at 21:00: an hour after `day_to_night.tres` reaches full night at 20:00, so the last stretch of
every shift is driven in the dark it was lit for. 14 game hours over 300 s of driving is about
21 s an hour.
