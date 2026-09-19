---
paths:
  - "etl/pipeline/lamps.py"
  - "etl/tests/test_lamps.py"
  - "game/tools/verify_lamps.gd"
  - "game/tuning/lamps.{tres,md}"
---

# Lamp posts — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/lamps.py`, the `lamps` config block, or any lamp-post change: paste `lamps.json`'s two
  partitions, `min_kerb_clearance_m`, `shift_m` (with its `n`), `lantern_overhang_m`,
  `lanterns_past_centreline`, `spacing_surveyed_m` vs `spacing_drawn_m`, `gaps_over_report_m` and
  `facing_away`, before and after — and A/B render one street at a fixed camera.** There is no
  separate grader and there should not be: the stage grades itself, because every way this breaks
  renders as a perfectly drawn lamp post or as nothing.
  🔴 **`min_kerb_clearance_m` is the invariant the user asked for — no column stands in the road —
  and it comes from TWO refusals, not from `max_shift_m`.** `_register` clears a column's own host
  kerb; a second pass re-snaps the *placed* point against every edge and refuses it where 1.6x
  ribbons overlap. Deleting that pass leaves both partitions closing, `facing_away` at 0 and
  `check.sh` green, with columns standing in junction mouths. It is **not** a tautology: a foot
  reconstructed from `offset_m` rather than read off the polyline drives it negative (`signs.py`'s
  recorded 10.6 m defect). ⚠️ **Do not "fix" it by iterating the push** — measured on the SIGNS
  and cited as precedent, not measured here: 9.7% plateau, worst shift 5.52 → 16.77 m (`Q78`), where
  this layer's own `shift_m` max is 6.7329. The lamps sweep was never run and the argument is
  borrowed; say so rather than quoting another layer's numbers as this one's.
  🔴 **There must be NO `arms_against_kerb` counter.** The arm direction is derived from the kerb
  side, so such a counter reads 0 by construction — `Q72`'s tautology, which certified a whole
  region's signs as correct while every one faced the wrong way. `lantern_overhang_m` and
  `lanterns_past_centreline` are what ship, and the second is reachable by raising `arm_reach_m`,
  which is the test a counter here has to pass. The facing itself **cannot** be graded against
  anything published (`Q62`) — the evidence is an A/B render at one fixed camera, shot twice and
  `cmp`'d.
  🔴 **The prism ring is NOT reversed here, and `signs._draw_pole` reverses its own, as the removed
  `signals._draw_post` did.** Both carry a paragraph calling the reversal "the whole correctness of this
  function" and both are right about their own frame; `lamps._strut` builds an explicit one with
  `u x v == axis`, because a bracket arm is not vertical. Inheriting their fix inverted **25,116 of
  35,880** triangles. Do not "restore consistency".
  ⚠️ **`shift_m` is recorded over refusals as well as keeps, and `n` exceeding `drawn` is how you
  tell** (`Q58`'s trap); `Q78`'s outward-only clamp applies here and deliberately **not** in
  `railings.py` — a fence is a run, a lamp post is not.
  ⚠️ **A widening change is a lamp-position change**: `surface.floor_default_m` moves the drawn kerb and
  therefore moves every column, silently and plausibly.
  ⚠️ **The spacing pair is this layer's own failure mode and no other layer here has it** — a lamp
  row's regularity *is* its content, so a refusal is a hole where a missing sign is invisible. Quote
  both distributions; the *difference* is the finding.
  ⚠️ **The colour is in `materials:` and answers to `Q33`** — `signs.colours`' exemption does not
  transfer, because a lamp post is not a printed specification and is one colour. ⚠️ **A lamps change
  is also a shader change, and its shader is shared with the signs** — `check.sh`
  exits 0 on a shader that fails to compile, so render and `grep -i "shader error"`, and look at
  both layers. 🔴 **Do not light the lantern**: `Q38` bakes the exposure at build time and `Q26` has
  not chosen a look, so a glow here is wrong in every frame the project renders.
  ⚠️ **`verify_lamps.gd`'s upright bar grades the IMPORTED mesh, and the two used to differ.** Godot
  quantises imported vertex positions over each mesh's **own AABB** — 0.025 m across `lamps.glb`'s
  1,646 m, against a 0.06 m bracket arm — until `Q82` turned compression off project-wide, at
  **+2.002%** of PCK and **0** extra draw calls. 🔴 **It
  is `[importer_defaults]` in `project.godot` and `check.sh`'s `settings` step pins its value**,
  because `game/assets/generated/` is gitignored and a per-asset `.import` does not survive a clone.
  An editor save drops it silently and every generated mesh then imports geometry the ETL did not
  build. 🔴 **And `[importer_defaults]` seeds only a NEW `.import`** — changing the key does not
  migrate assets that already have a sidecar, and `check.sh` cannot see a stale one. Delete the
  sidecars and re-import, then re-measure. Do not "tighten" the bar toward a measured value either — it is a lay-flat detector.
  Numbers in `Q82`.
