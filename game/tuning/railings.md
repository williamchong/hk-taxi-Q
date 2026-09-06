# railings.tres

Rationale for `game/tuning/railings.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Pedestrian railings, drawn as their own geometry (`P3-19`, `Q60`).

`tools/generated_scene_import.gd` maps the ETL's `railings` material name to
this path and only this path, so this file is the switch: delete the entry
there and the fences fall back to the `BaseMaterial3D` they imported with,
which draws the right fences in whatever grey the importer picks.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants — and beside `arrows.tres` and `boxjunctions.tres`, which
is the whole point of the file.

⚠️ **`rail_colour` is not a copy of anything, and that is the difference from
its two neighbours.** The marking yellow and the marking white are each
authored two and three times over, held together only by a mismatch being
visible in one frame. A railing shares its colour with nothing in the bundle,
so there is no copy to drift — but it also has no second reading to be checked
against, which is worth knowing when judging it: the shade below is authored
from the street, not derived from a survey, and nothing measures it.

⚠️ **And nothing measuring it is how it has now been wrong twice.** `P3-19`
authored 0.78/0.80/0.76 — pale, which is the right reading of the street — with
no headroom left above it, so the sun took the fence to white and the shipped
frames read as a concrete parapet. Taken down on the frames. It was then wrong
a second way for two more revisions: a **green** bias, described as "a pale
institutional grey-green", read off nothing and inherited by all three classes.
Hong Kong's street railings are galvanised steel and they are grey. Corrected
on the user's report — which, for this one value, is the instrument. Now dead
neutral: `railings.gdshader` records why the cool cast is left to the sky
rather than authored here.

⚠️ **`rail_metallic` stays 0.0**, and that is a measurement rather than taste.
`P3-14` shipped the tram rails at 0.65 and they came out **sky blue** — metal
reflects its environment, the only environment here is sky, and the mobile
tier ships no reflection probes. Painted steel is a dielectric coat over
metal, so 0.0 is the truthful value as well as the one that renders.

⚠️ **The fence's shape is now split across two files, and the split is where
the geometry ends.** Height, station pitch, how far it stands outside the kerb
and how far its foot sinks are *mesh* — decided by `pipeline/railings.py` from
`hong_kong.yaml`'s `railings:` block. Everything finer than a quad is *mask* —
baluster pitch and width, post pitch and width, the two rail bands — and lives
here, because it is expressed in the shader and hard rule 4 puts tuning in
data. Both halves are authored for the same reason: no sheet in the bundle
publishes a railing dimension at all (`Q60`, strengthened by the symbology
correction). Neither half is read from anywhere.

⚠️ **The rail bands are in metres above the ribbon deck**, which is `UV.y`'s
own frame — `0.0` is the ground line, not the bottom of the mesh. So `(0.95,
1.10)` is a top rail from 950 to 1100 mm up, and it means that on every fence
in the region regardless of what the road is doing underneath.

⚠️ **`ALPHA` here is coverage, not opacity.** There is no translucency dial in
this file and there should not be: the steel is opaque and the gaps are gaps,
so what reaches `ALPHA` is the fraction of a fragment the members cover,
computed from the four dimensions below. An opacity uniform would be
`marking_paint.gdshader`'s recorded misreading of `paint_opacity` repeated here.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table: a
railing is the nearest object to the camera on most of the region's streets,
so it is judged against the kerb it stands on rather than from the air.
