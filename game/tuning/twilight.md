# twilight.tres

Rationale for `game/tuning/twilight.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One of the looks `day_to_night.tres` blends the rig through (`Q160`); `day_to_night.md` has the
table and the order. The sun gone and the sky still holding colour: the keyframe the key light changes hands under.

A copy of `clean_daylight.tres` with only the blended values moved. ⚠️ **Only what
`LightingRig.BLENDED` and `BLENDED_SKY` name is ever read from this file** — the ambient, the
fog, the glow's intensity, the saturation and the sky's four colours. Its switches, its tonemapper
and its glow levels are the day's and are carried here unread, so changing one of them in this file
changes nothing; a property that should move with the hour is added to those lists first.
