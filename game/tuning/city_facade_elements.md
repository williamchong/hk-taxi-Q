# city_facade_elements.tres

Rationale for `game/tuning/city_facade_elements.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

⚠️ Candidate `A‴` — the clean look with its facade elements ON, kept as the
alternative to whatever `city_facade.tres` currently holds.

This is the configuration the user accepted on 2026-08-09 from the
`build/driver/q26_A3_422ee16/` frames ("much more acceptable now") and which
shipped as the default until **2026-08-16**, when `Q26`'s working default was
moved to candidate `C`. Nothing about `A‴` was faulted; the user chose to
continue development on flat colour. See `docs/DECISIONS.md` `Q26`.

⚠️ **`Q26` closed on `C` on 2026-08-17, so this file is now the runner-up
rather than the pending alternative.** It is kept, not deprecated: the closure
came before the `≥3`-HK-driver round at `P3-9a`, so that round can still
reopen the question.

🔴 **`A‴` is not what the user accepted in 2026-08-09 any more, and the
difference is `Q102`.** This file used to carry `survey_apply 1.0` and the
five `quiet_*` values — it was the only thing in the repo that loaded the
vision reader's per-building verdicts, so reopening `Q26` meant grading them
here. The reader was withdrawn on cost, so those six lines are gone and every
building takes the hashed treatment. What remains is the *elements* half of
`A‴`, unchanged and still the accepted argument for them; the surveyed half
is not restorable by a `cp`, and the `q26_A3_422ee16` frames are a record of
a look this file no longer reproduces.

⚠️ **Not loaded by anything.** `tools/generated_scene_import.gd` maps the ETL's
`city_facade` material name to `res://tuning/city_facade.tres` and only that
path, so restoring this look is `cp city_facade_elements.tres city_facade.tres`
and a reimport — no rebuild, because it names the same shader and reads the
same `TEXCOORD_0` payload as the shipped `C`.

**The seven values that separate the two looks**, which here are the ON side:

  solid_share 0.27 · glass_ratio 0.44 · shopfront_share 0.55 · accent_share 0.11
  cornice_darkness 0.28 · floor_line_darkness 0.11 · mullion_darkness 0.12

⚠️ **Why it takes all seven, why `solid_share` is a gate rather than a value,
and what the retired eighth was are argued once, in `city_facade.tres`.** They
are facts about the pair, not about this file, and the switch is where a reader
already is. Not repeated here, because two copies of an argument drift.

The lineage: `A″` (`Q43`, `build/driver/q43/`) fixed the collapsed fenestration
gate; `A‴` (`P3-7a`, `build/driver/q26_A3_422ee16/`) added `unglazed_glassy`
and the `pane_*` modulation and held the `Q30` chroma bar on all three audit
cameras. All three survive `Q102` — none of them read the survey channel.
`city_facade_warm.tres` is the third look, `B`.

## `shader_parameter/night_spot_*` — the floodlights (`Q160`)

At night `night_spot_share` 0.6 of the buildings are floodlit from street level, in three of the
user's calls: "skip the window, just make the building glow"; then "not so bright, maybe just
something that feels like a spotlight onto it"; then "spotlight the whole building instead of just
the bottom". So `lit_window_share` and `emission_strength` stay 0.0 and reserved, the all-over
glow that was tried is gone, and what ships is a lamp every `night_spot_spacing_m` 14 m along the
wall throwing a warm cone (`night_spot_colour`) up it at `night_spot_strength` 0.55. The cones
widen with `night_spot_spread` 2.5 until they merge into one wash, which dims to `night_spot_top`
0.3 of its strength by `night_spot_reach_m` 120 m and holds to the roofline.

What is lit is the wall's own finished colour, so each look keeps its palette. All of it is
multiplied by the rig's `night_lights`: these are the values at FULL night and draw nothing at
noon. Walls only — the branch tests `wall_normal_max`, so no roof is lit from the kerb.
