---
paths:
  - "etl/pipeline/config_blocks/buildings.py"
  - "tools/ring_weights.py"
  - "tools/facade_*.py"
  - "tools/lighting_rig.py"
  - "tools/frame_stats.py"
  - "etl/pipeline/colour.py"
  - "etl/tests/test_facade_*.py"
  - "etl/tests/test_colour.py"
  - "game/tuning/city_facade*.{tres,md}"
  - "game/assets/shaders/city_facade*.gdshader"
  - "game/scripts/world/lighting_rig.gd"
---

# Façade, materials and exposure — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- Height-ramp or façade-survey changes: also `tools/ring_weights.py`, and paste what it derives. The
  surveyed material weights are authored against both, and no check can see them go stale (`Q34′`).
- Façade-survey or `facade_hue.strength` changes: also `tools/facade_chroma.py`, and paste its table
  into `docs/ART_DESIGN.md`. `Q30`'s numbers are the argument that the shipped palette is not the
  authored one, and they are only an argument while they describe the survey that ships.
- 🔴 **`materials:` colours, a material's `bounds:`, or the rigs' `exposure_anchor`: the ETL half and
  the game half move in ONE commit and `schema_version` goes with them** (`Q38`, `P5-28c`). Since the
  un-bake a shipped colour **is** a material's reflectance and the rig multiplies — so a bundle
  without the multiply, or a rig without the bundle, renders a city 1/0.520 too bright or too dark
  with nothing in a frame to say which half is missing. ⚠️ **`_check_reflectance`'s round trip is a
  tautology on its own**: with the anchor gone `luminance(colour)` *is* `reflectance` by
  construction, and `bounds:` — the numeric half of the `source:` each entry already wrote in prose —
  is the only part that can fail. **Correct a colour outside its bounds; never widen the bounds to
  admit it**, which is the one direction the rule does not work in. ⚠️ **The exposure has exactly one
  home, the rig scene**, read by `tools/lighting_rig.py` and never restated: `facade_chroma.py`
  applies it to every figure — chroma does **not** survive a linear-light scale: `C*` is multiplied
  by `anchor ** (1/3)`, **0.804** at 0.520, so an unexposed table reads **1.24x MORE** saturated than
  the screen — and `frame_stats.py` applies it to `--albedo-l`, where it moves **`gain` only** — `linear ratio` and `additive share` are quotients of
  linear luminances and a uniform scale cancels exactly in them. ⚠️ **Do not put the number back into
  `etl/`**: the ETL publishes reflectance and knows nothing about the hour, and that is the coupling
  the un-bake removed. Owed: the per-material round trip, `facade_chroma.py --shipped` before and
  after, and the `Q27`/`Q31` cameras — ⚠️ **shooting the skyline at `t=2.0` and not `t=0.8`**, where
  the streamer has not settled and two runs disagree. Numbers in `Q38`.
- **Filler-guard changes — `is_filler`, `filler_colours`, `MODAL_SHARE`, `MODAL_STRIDE`: also
  `tools/facade_survey.py --all --filler-report`, and paste its table.** It is the only thing that
  reproduces `Q55`, whose every number came from a scratch script — the same debt `Q37` was opened
  about. ⚠️ **Validate with the guard off first**: re-run the survey with `MODAL_SHARE` above 1.0
  and diff against the shipped table. It must differ on **zero** rows, and that is what proves
  nothing but the guard moved — `Q37`'s own validation move. ⚠️ **The two axes must stay
  disjoint**: a repeated *grey* belongs to `Q37`'s channel tie and is filtered out of the colour
  set, or the sweep reports every grey-padded building in the region instead of the 100 that carry
  a panel. ⚠️ `facade_lab.json` is **not committed** — it is under `etl/sources/`, which is
  gitignored — so re-publishing it is a local act and `superseded/` is the only way back.
