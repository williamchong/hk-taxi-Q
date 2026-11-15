# noon.tres

Rationale for `game/tuning/noon.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One of the looks `day_to_night.tres` blends the rig through (`Q222`); `day_to_night.md` has the
table and the order. 12:00, the brightest look of the day (the user's ask): a deeper blue zenith, a neutral ambient at 0.95 against the day's 0.85. The fog is the day's.

A copy of `clean_daylight.tres` with only the blended values moved. ⚠️ **Only what
`LightingRig.BLENDED` and `BLENDED_SKY` name is ever read from this file**; its switches, its
tonemapper and its glow levels are the day's and are carried here unread (`dusk.md`).
A first table picked from frames (`build/driver/q221/`, gitignored); the user has not driven it.
