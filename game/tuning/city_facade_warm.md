# city_facade_warm.tres

Rationale for `game/tuning/city_facade_warm.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The measured Hong Kong facade look, kept as the alternative to whatever
`city_facade.tres` currently holds.

This is `P3-7` verbatim: window bands at the pitch read off the real facade
textures — 227 walls on 219 buildings of one individualised LandsD sheet, read
once offline and never shipped. docs/PROGRESS.md carries the distribution and
docs/DATA_SOURCES.md records that the sheet does not enter the build path.

⚠️ **Not loaded by anything.** `tools/generated_scene_import.gd` maps the ETL's
`city_facade` material name to `res://tuning/city_facade.tres` and only that
path, so switching looks is `cp city_facade_warm.tres city_facade.tres` and a
reimport — no rebuild, because both shaders read the same `TEXCOORD_0` payload.
A file rather than a second entry in that map because which look ships is
tuning, and CLAUDE.md hard rule 4 keeps tuning out of code.

⚠️ **"Verbatim" is a promise about the pitch, not a claim that this is the
better shader.** `city_facade_clean.gdshader` was forked from this one and then
fixed in three places that were never back-ported, because keeping this file a
faithful record of what `P3-7` measured is worth more than keeping two large
shaders in step. So switching to this look knowingly reintroduces:

  · `band()` without the analytic duty-cycle convergence — diagonal moire on
    any wall seen at a shallow angle, which in a street of towers is most of them
  · `along_m` from the face normal's plan-perpendicular — per-triangle grid
    origins, so a curved podium breaks into chevrons
  · a 90–240 m fade, safe against the 250 m LOD1 switch by accident rather than
    by the reasoning in docs/ART_DESIGN.md

The first two are survivable at a 2.4 m column pitch and were, for a whole
phase. Anything that makes this the shipping look again should port the three
across first — and at that point the two shaders probably do earn a shared
`.gdshaderinc`, which two call sites currently do not.
