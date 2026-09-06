# bollards.tres

Rationale for `game/tuning/bollards.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Footway bollards, drawn from the railing layer's own `bollard0..3` (`Q61`).

`railings.tres`'s sibling, on the **same shader**. What tells a bollard from a
fence is entirely the six mask numbers below: wide uprights at a wide pitch,
and no balusters and no rails. Nothing branches in `railings.gdshader` — a
class is a parameterisation, which is what keeps the difference in tuning data
(CLAUDE.md hard rule 4) rather than in a second shader that would drift.

⚠️ **`P3-19` refused these outright, and the refusal was right at the time.**
They are posts, not fences, and drawing them as the same fence would have
asserted a sameness no source states — `Q54`'s debit. What changed is that
they now have somewhere of their own to go.

⚠️ **This is the one dimension a source COULD have carried and does not.**
`hong_kong.yaml` and `Q60` used to say `SYMBOL_STEP_1`/`SYMBOL_SIZE_1` carried
bollard spacing and diameter. They do not: the fgdb spec calls them "symbol
size of *marker symbol*", the values are plot sizes in inches, and **0 of the
region's 196 bollard features** populate any of the five slots. So the pitch
and width below are authored, exactly as the fence's are, and are declared as
authored here because there is nothing to declare them from.

⚠️ **A bollard here is a flat masked quad, not a round post.** It is one quad
thick like the fence beside it and `cull_disabled` for the same reason, so it
reads from both faces and thins to nothing edge-on. Consistent with the
bundle's own fidelity rather than an oversight, and recorded in
`ART_DESIGN.md` rather than hidden.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table.

## `shader_parameter/rail_colour = Color(0.43, 0.43, 0.43, 1.0)`

Darker than the fence, and the same galvanised grey — Hong Kong's footway
bollards are the same steel as the railing beside them. The shade is what keeps
the two from reading as one object, so it is a value difference and not a hue
one. ⚠️ Carried the fence's unsourced green bias until it was corrected.

## `shader_parameter/rail_metallic = 0.0`

0.0 for `railings.tres`'s measured reason: `P3-14` shipped the tram rails at
0.65 and they rendered sky blue, because the only environment here is sky.

## `shader_parameter/baluster_pitch_m = 0.11`

No balusters and no rails: zero width and zero-height bands are exactly 0.0
out of the shader's two coverage functions, which is the "off" convention.

## `shader_parameter/post_pitch_m = 1.5`

The post itself. Pitch authored at a stride, width at a bollard's diameter.
