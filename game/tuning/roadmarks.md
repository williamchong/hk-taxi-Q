# roadmarks.tres

Rationale for `game/tuning/roadmarks.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Stop lines and give-way lines, drawn as their own geometry (`P3-23`, `Q53`).

`tools/generated_scene_import.gd` maps the ETL's `roadmarks` material name to
this path and only this path, so this file is the switch: delete the entry
there and the markings fall back to the `BaseMaterial3D` they imported with,
which draws the right bars in whatever grey the importer picks.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants — and beside `road_markings.tres` and `arrows.tres`, which
is the whole point of the file.

⚠️ **The shader is shared** (`Q71`). `marking_paint.gdshader` serves the arrows
and the box junctions too — this layer was the third copy of it, which is what
triggered the merge. `verify_roadmarks.gd` checks the dispatch against *this
path* and not against the shader, so a stop line handed `arrows.tres` is still
caught even though the two now run identical code.

⚠️ **`paint_colour` is the FIFTH authored copy of the marking white, and the
duplication is the decision** — the paragraph `arrows.tres` and
`boxjunctions.tres` both carry. `Q53` kept the marking colours out of
`hong_kong.yaml`'s `materials:` table, outside `Q33`'s exposure rule, because
paint is not cladding, and predicted that a road colour authored in a further
place would be the problem. This is that place again, put next door so the
copies can be read side by side. There is no mechanism in Godot to share a
value between `.tres` files, nor between a shader default and a `.tres`; what
there is instead is that a mismatch shows up in a single frame, and this copy
is the most exposed of the set — a stop line meets the lane dividers of its
own approach end-on, so a different white reads as a different marking rather
than as a shade.

🔴 **This ledger is the count, and it must be recomputed whenever the set
moves.** It said SIX until `Q71` merged `arrows.gdshader`, `boxjunctions.gdshader`
and `roadmarks.gdshader` into `marking_paint.gdshader`: three shader defaults
became one, taking the white from six copies to five and the yellow from four
to three. A stale ledger is worse than the duplication it describes, because it
is the only thing anyone reads to find out how bad the duplication is.

  road_markings.gdshader   line_colour  (default) = vec3(0.91, 0.91, 0.87)
  road_markings.tres       line_colour            = Color(0.91, 0.91, 0.87, 1.0)
  marking_paint.gdshader   paint_colour (default) = vec4(0.91, 0.91, 0.87, 1.0)
  arrows.tres              paint_colour           = Color(0.91, 0.91, 0.87, 1.0)
  — and this file is the fifth.
  road_markings.tres       paint_roughness        = 0.7

⚠️ **`paint_opacity` is deliberately NOT copied across**, for `arrows.tres`'s
stated reason: next door the 0.85 is asphalt showing through paint mixed into
one opaque surface; here it would be transparency on a lifted second surface.

⚠️ **Nothing here is a fade, and nothing here is the dash pattern.** The 600 mm
mark and 300 mm gap of a `RM1013` give-way line are geometry, decided by
`pipeline/roadmarks.py` from `hong_kong.yaml`'s `road_marks:` block, which
transcribes them from TD's index plan `CT174/51-5(1)F`. This file only says
what colour the paint is; putting the module here would move a published
dimension out of the city file that owns it.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table, on an
approach carrying a `TS102` GIVE WAY plate: the thing this has to survive is
being seen from the driving seat at the moment the sign above it is read.
