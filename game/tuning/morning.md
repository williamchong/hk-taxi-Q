# morning.tres

Rationale for `game/tuning/morning.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One of the looks `day_to_night.tres` blends the rig through (`Q222`); `day_to_night.md` has the
table and the order. 07:00, the shift's opening hour: a pale warm horizon under the day's blue, the ambient lower (0.70) and the haze a little thicker and sunlit (`fog_sun_scatter` 0.2).

A copy of `clean_daylight.tres` with only the blended values moved. ⚠️ **Only what
`LightingRig.BLENDED` and `BLENDED_SKY` name is ever read from this file**; its switches, its
tonemapper and its glow levels are the day's and are carried here unread (`dusk.md`).
A first table picked from frames (`build/driver/q221/`, gitignored); the user has not driven it.
