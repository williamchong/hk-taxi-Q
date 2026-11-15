# dawn.tres

Rationale for `game/tuning/dawn.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One of the looks `day_to_night.tres` blends the rig through (`Q225`); `day_to_night.md` has the
table and the order. 06:15 on a free drive's lap: a rose horizon under a paler, cooler blue than
dusk's, a cooler and dimmer ambient (0.60), and a morning mist (`fog_density` 0.0006 against dusk's
0.0004) at a lower saturation — so the sunrise is not the sunset played backwards, which is what
borrowing `dusk.tres` made it.

A copy of `dusk.tres` with only the blended values moved. ⚠️ **Only what `LightingRig.BLENDED` and
`BLENDED_SKY` name is ever read from this file** (`dusk.md`). A first table picked from frames
(`build/driver/q225/`, gitignored), beside the borrowed dusk; the user has not picked between them.
