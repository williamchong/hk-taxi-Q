# arrows.tres

Rationale for `game/tuning/arrows.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Turn arrows, drawn as their own geometry (`P3-15`, `Q53`).

`tools/generated_scene_import.gd` maps the ETL's `arrows` material name to this
path and only this path, so this file is the switch: delete the entry there and
the arrows fall back to the `BaseMaterial3D` they imported with, which draws
the right geometry in whatever grey the importer picks.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants — and beside `road_markings.tres`, which is the whole
point of the file.

⚠️ **The shader is shared and this file is what makes these arrows arrows**
(`Q71`). `marking_paint.gdshader` serves the box junctions and the stop lines
too — it was `arrows.gdshader` until the third copy of it was authored — so
the colour here is the entire difference between this layer and the yellow one
next to it. `verify_arrows.gd` checks the dispatch against *this path*, not
against the shader, so a mesh handed the wrong `.tres` still fails.

⚠️ **`paint_colour` and `paint_roughness` are duplicates of
`road_markings.tres`'s `line_colour` and `paint_roughness`, and the duplication
is the decision.** `Q53` deliberately kept the marking colours out of
`hong_kong.yaml`'s `materials:` table, outside `Q33`'s exposure rule, because
paint is not cladding — and it predicted that a third road colour authored
somewhere else would be the problem. This is that third place, put next door so
the two can be read side by side. There is no mechanism in Godot to share a
value between two `.tres` files; what there is instead is that a mismatch shows
up in a single frame, because an arrow a different white from the dashes on
either side of it is the first thing anyone would notice.

  road_markings.tres  line_colour      = Color(0.91, 0.91, 0.87, 1.0)
  road_markings.tres  paint_roughness  = 0.7

⚠️ **`paint_opacity` is deliberately NOT copied across.** Next door it is 0.85
because the paint is mixed into the road's own albedo on one opaque surface, so
the remaining 0.15 is asphalt showing through. An arrow is a second surface
15 mm above the road: the same number there would mean transparency, which
costs a sorted alpha pass and models thermoplastic as tinted glass. The first
draft of the shader made exactly that mistake.

⚠️ **Nothing here is a fade.** `road_markings.tres` carries `fade_m = 6.0`,
priced against the measured 4.21 m worst-case junction cap overlap, and an
arrow deliberately has none: it is a whole object rather than a length of line,
and half an arrow is not a marking. 51 of the region's arrows sit over a cap
and are drawn there on purpose — the cap is still carriageway.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table, on
**Hennessy and Johnston**, against the lane dividers `P3-12` draws beside them:
the thing this has to survive is being seen next to the markings it matches.
