# signals.tres

Rationale for `game/tuning/signals.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

Traffic signal heads, drawn as their own geometry (`P3-17`).

`signs.tres`'s sibling, on the **same shader**. What tells a signal head from a
sign plate is entirely the geometry `pipeline/signals.py` built and the two
numbers below: nothing branches in `signs.gdshader`, because a layer is a
parameterisation rather than a shader of its own — `Q61`'s rule for the three
railing classes and `Q71`'s for the three paint layers, arriving at a fourth
place. That keeps the difference in tuning data (CLAUDE.md hard rule 4) rather
than in a second shader that would drift from the first.

🔴 **SO `signs.gdshader` IS NOW A TWO-LAYER SHADER.** A change to it is a change
to the signs *and* the signals, and `tools/check.sh` exits 0 on a shader that
fails to compile — so render both and `grep -i "shader error"`. The per-layer
dispatch is still checked: `check_shader_material` compares the material's
`resource_path` rather than the shader, so a head handed `signs.tres` still
fails. Do not reach for `check_shader_source` to quiet that.

`tools/generated_scene_import.gd` maps the ETL's `signals` material name to this
path and only this path. ⚠️ **The fallback failure is the quiet one `signs.tres`
records**: the livery is on `COLOR_0`, so a head that kept its imported
`BaseMaterial3D` still draws the right box in the right place in the right
colours — it just loses `vertex_srgb_to_linear` and comes out pale (`Q27`).
`verify_signals.gd` checks the dispatch because nothing else would notice.

⚠️ **There is no colour in this file, and its absence is the decision** —
`signs.tres`'s paragraph, for its reason. A head is four colours (a body and
three aspects) inside one draw call, so the livery lives in `hong_kong.yaml`'s
`signals.colours` and arrives on the vertex. It is a *city* fact besides: a
second city's signals are its own publisher's.

⚠️ **And there is no lit aspect, which is the thing to resist changing here.**
`P3-17` ships no cycle — no dataset publishes timing, an invented one
*instructs*, and nothing obeys it until `P3-3`'s traffic exists. Pushing
`sheeting_glow` up to "make the signals read" would turn every junction in the city
into a standing instruction the game cannot honour. The named route for state is
`P3-11d`'s `instance uniform` lamp circuit, wired in `B3`.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table, on
**Hennessy and Johnston**, under both the `clean_daylight` and `golden_hour`
rigs — the second because the glow parameter is the one that misbehaves in low
light, and a dark lens that reads as lit is exactly the failure above.

## `shader_parameter/plate_roughness = 0.72`

Rougher than a sign plate's 0.55. A signal head is a powder-coated aluminium
casting rather than the retroreflective sheeting beside it, and it is the one
object here the player is *not* meant to read at speed — it carries no
instruction while the lamps are off.

## `shader_parameter/sheeting_glow = 0.0`

🔴 **Zero, and the zero is load-bearing.** `sheeting_glow` exists because a sign
face is retroreflective and reads as slightly self-lit at dusk. A signal lens
with its lamp off is the opposite: dark glass in a dark housing. Any value above
zero here makes an unlit aspect read as a lit one, which is the instruction
`P3-17` deliberately refuses to give.
