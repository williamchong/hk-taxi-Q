# signs.tres

Rationale for `game/tuning/signs.tres`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

Traffic signs, drawn as their own geometry (`P3-16`).

`tools/generated_scene_import.gd` maps the ETL's `signs` material name to this
path and only this path, so this file is the switch: delete the entry there and
every sign in the city falls back to the `BaseMaterial3D` it imported with —
which draws the right plates in the right places, in the right colours, because
the colour is on the vertex. ⚠️ **That is a quieter failure than the arrows'
equivalent**, where the fallback is visibly the wrong grey. Here the only thing
lost is `vertex_srgb_to_linear`, so the whole city's signage comes out pale
rather than absent — `Q27`'s exact failure mode. `verify_signs.gd` checks the
dispatch for that reason.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants.

⚠️ **There is no colour in this file, and its absence is the decision.** Every
other generated-mesh material in `tuning/` carries its colour — `arrows.tres`
the paint white, `boxjunctions.tres` the yellow, `railings.tres` the galvanised
grey — because each of those meshes is one colour. A sign is four, so the
livery lives in `hong_kong.yaml`'s `signs.colours` and arrives on `COLOR_0`.
What is left here is the two things that are genuinely *material* rather than
content: how the surface takes light, and how much the sheeting lifts it.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table, on
**Hennessy and Johnston**, under both the `clean_daylight` and `golden_hour`
rigs — the second because `sheeting_glow` is the parameter that misbehaves in
low light, and a NO ENTRY that reads as a lamp is worse than one that reads
flat.
