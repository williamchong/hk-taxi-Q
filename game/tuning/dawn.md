# dawn.tres

Rationale for `game/tuning/dawn.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One of the looks `day_to_night.tres` blends the rig through (`Q225`); `day_to_night.md` has the
table and the order. 06:15 on a free drive's lap: a pale blue horizon under a deeper blue, a blue
and dimmer ambient (0.60), and a morning mist (`fog_density` 0.0006 against dusk's 0.0004) at a
lower saturation — so the sunrise is not the sunset played backwards, which is what
borrowing `dusk.tres` made it.

A copy of `dusk.tres` with only the blended values moved. ⚠️ **Only what `LightingRig.BLENDED` and
`BLENDED_SKY` name is ever read from this file** (`dusk.md`). A first table picked from frames
(`build/driver/q225/dawn_pair.png`, gitignored), beside the dusk the dawn borrowed before.

**Blue since `Q235`** (the user's ask, 2026-11-17: "can we make dawn more blue shaded and dusk yellow
shaded so that we can tell the time diff"): the rose horizon, fog, ambient, key light and
`sky_light` all went to blue, the middle of three strengths rendered beside the rose
(`build/driver/dawn_dusk/options.png`, gitignored). ⚠️ The model's pick of the three; the user has
not chosen.
