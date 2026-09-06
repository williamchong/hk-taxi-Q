# city_facade.tres

Rationale for `game/tuning/city_facade.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The facade look the city actually loads, shared by every tile.

`tools/generated_scene_import.gd` maps the ETL's `city_facade` material name to
this path and only this path, so this file *is* the switch. All three of
`Q26`'s looks now have a file, and swapping is a copy and a reimport — never a
rebuild, because all three read the same `TEXCOORD_0` payload:

  candidate `C`  this file             flat per-building colour, elements off
  candidate `A‴` city_facade_elements  the clean look with its elements on
  candidate `B`  city_facade_warm      the measured Hong Kong window bands

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants — and beside `golden_hour.tres` because the sun these are
judged under is tuned in the same directory. Loaded as **one** resource for all
66 tiles: retuning the city is this file.

✅ **This file ships candidate `C`: accurate massing, flat per-building colour
and no facade fabric.** The user's call, 2026-08-16, to
continue development on flat colour, and **`Q26`'s closing verdict on
2026-08-17** — `C` is the look that ships, not merely the one being developed
against. It is the same configuration that shipped from 2026-08-06 to
2026-08-09 and that every `P3-7a` step since has been proved byte-identical
against — the reducibility baseline is now also the default *and* the answer.

⚠️ **`A‴` was not faulted, and closing `Q26` is not a verdict against it.** The
user accepted `A‴` on 2026-08-09 from the `q26_A3_422ee16` frames and it
shipped until 2026-08-16; that grading stands. `city_facade_elements.tres`
carries `A‴` unchanged and its header holds the argument for the elements.
Restoring it is one `cp`, and the `≥3`-HK-driver round at `P3-9a` — which
closed before running — is now what can **reopen** `Q26` rather than what
decides it.

**Seven values separate this from `A‴`**, and `diff` against
`city_facade_elements.tres` should show exactly those seven lines:

  solid_share 1.0 · glass_ratio 0.0 · shopfront_share 0.0 · accent_share 0.0
  cornice_darkness 0.0 · floor_line_darkness 0.0 · mullion_darkness 0.0

⚠️ **It takes all seven, and `solid_share` is a gate rather than a zero.**
`glazed = step(solid_share, …)` in the shader, so at 1.0 no building is ever
glazed and the curtain-wall, fin and punched types stop drawing — but
shopfronts, cornices, floor lines and mullions draw *outside* that gate, and
with only the gate closed 86% of the frame still differed.

⚠️ **It was eight until `Q102`.** The eighth was `survey_apply 0.0`, the gate
on the vision reader's per-building verdicts, and the pair's headers argued at
length that it must never move alone. The reader was withdrawn on cost and the
`TEXCOORD_1` payload with it, so both files lost that line and the five
`quiet_*` values behind it. `A‴` did move, and its header records what it lost.

⚠️ **`C` moved by compiler precision only, and that was measured rather than
argued.** The gate was already closed here, so the removal could not reach a
pixel by any path — and it did anyway: A/B at both `Q27` cameras puts **1.59%**
(`street`) and **1.61%** (`skyline`) of pixels **2 of 255** apart, whole-frame
`L*` +0.0003. Tile geometry is byte-identical and the sky and road do not move
at all, so it is interpolator allocation, not a look. 🔴 **Do not certify this
with the 0.1% figure from 2026-08-16** — that measured what the *payload* cost
the frame at schema 6, a different change, and borrowing it here would be
asserting a number nobody took of this one. `DECISIONS.md` `Q102`.

⚠️ **This was "the city without the reader" before there was no reader.** The
per-building hue is `COLOR_0`, which the ETL picks from the `materials:` table
in `etl/config/hong_kong.yaml`, and `Q37`'s glazing dip/tint survey is local
compute upstream of it. Neither was switched off here, and neither went with
the reader.

The dozens of uniforms the seven make inert — `bay_width_m`, `glass_colour`,
`pane_bow` and the fresnel terms — are left at their `A‴` values on purpose.
They are what makes the two files diffable, and they are the state a future
art idea starts from, not dead weight to be cleaned up.

⚠️ **`base_wash` is 0.0 because the palette lives in the city config**, which
is where the shader's header says it belongs. The `materials:` table in
`etl/config/cities/hong_kong.yaml` carries the city's level — every colour in
it was re-authored 19 L* darker once the anchor probe measured that as what the
white city needed — so the wash has nothing left to trial. That leaves
`base_colour` inert, kept at its tuned value on the same rule as above.

⚠️ Those colours used to sit inline on the height bands, and `Q34` moved them:
the field's position asserted that material is a function of height, which 0.9%
of measured facade lightness does not support. Nothing about the level changed.

`value_jitter` 0.35 is the small half of that change and is bounded on both
sides. Below it a block reads as one mass; above roughly 0.4 the darkest draws
stop reading as buildings differing and start reading as a few of them being
broken. It is not the lever that fixed the white city — at the 0.6 ceiling it
moved the frame 0.4 L*, against 10.3 for the bands.

`floor_height_m` is still the measured 2.8 m and stays that way whichever look
is loaded — the massing is real and the floor rhythm should be.
