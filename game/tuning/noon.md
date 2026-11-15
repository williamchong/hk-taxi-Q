# noon.tres

Rationale for `game/tuning/noon.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One of the looks `day_to_night.tres` blends the rig through (`Q222`); `day_to_night.md` has the
table and the order. 12:00, the brightest look of the day (the user's ask): a clean blue sky — zenith `(0.12, 0.42, 0.95)` over a light blue horizon
`(0.62, 0.82, 1)`, no grey band — and a neutral ambient at 1.25 against the day's 0.85. The fog is the day's.
Both are the user's picks from frames (2026-11-16, "can we have a brighter noon", "a clean blue or
white sky instead of some grey"; `build/driver/q222_sky/sheet2.png`, gitignored): clean blue over
pale-blue-to-white, white and the first table's `(0.16, 0.4, 0.8)` / `(0.8, 0.9, 0.98)`.
⚠️ `ground_bottom_color` stays the day's neutral grey: the sky is the ambient's source, and a blue
ground half turned every shadow purple in the trial.

A copy of `clean_daylight.tres` with only the blended values moved. ⚠️ **Only what
`LightingRig.BLENDED` and `BLENDED_SKY` name is ever read from this file**; its switches, its
tonemapper and its glow levels are the day's and are carried here unread (`dusk.md`).
The first table was picked from frames (`build/driver/q221/`, gitignored); the user has not driven it.
