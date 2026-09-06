# tramway.tres

Rationale for `game/tuning/tramway.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The tramway — rail heads and track bed (`P3-14`, `Q58`).

`tools/generated_scene_import.gd` maps the ETL's `tramway` material name to
this path and only this path, so this file is the switch: delete the entry
there and the tramway falls back to the `BaseMaterial3D` it imported with,
which draws the right geometry with none of the specular that makes a rail
read as metal.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants — and beside `road_markings.tres` and `golden_hour.tres`,
because the low sun these are judged under is tuned in the same directory.
Loaded as one resource for the whole region: the tramway is a single primitive.

⚠️ **Nothing here is a colour, and that is deliberate.** Both albedos live in
`hong_kong.yaml`'s `materials:` table — `steel_rail` at 35% and
`concrete_sooty` at 22% — because `Q33`'s palette rule is only total while
that table is the one place a colour is written, and `Q34` made the loop
depend on exactly that. What is tuned here is how the two catch light, which
is not a colour and has no published albedo to answer to.

⚠️ **`rail_roughness` is the value that does the work, not the albedo.** A
rail is recognisable because it is a polished strip in a matte street: at the
low sun `golden_hour.tres` sets, the highlight running along the head is the
entire cue, and the same geometry at `road_roughness` 0.95 is a grey line. It
ships at 0.28 against the bed's 0.9 — the widest separation in the city, and
the one thing to reach for first if the tramway reads as painted rather than
as laid.

⚠️ **`rail_metallic` is deliberately low, and 0.65 was measured wrong.** A
metallic surface reflects its environment and the only environment here is the
sky, so at 0.65 the rails rendered **sky blue** — two painted lines down the
reserve rather than steel. It is the one value in this file that was set by
looking at a frame rather than by argument, and the frame is in
`build/driver/tram_fixed`.

⚠️ **`flank_darkening` shades the rail only.** The bed is a plain surface, and
darkening its edges would draw two soft lines down the reserve that no source
puts there — `Q54`'s invented marking in a place it would be much harder to
notice than a kerbside yellow.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table, on
**Hennessy and Johnston**, and at a low sun rather than at noon: at noon a rail
and a painted line are nearly the same object.
