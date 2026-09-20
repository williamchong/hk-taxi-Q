---
paths:
  - "etl/pipeline/clearance.py"
  - "tools/carriageway_occupancy.py"
  - "tools/clearance_reconcile.py"
  - "tools/narrowing.py"
  - "tools/corridor_truth.py"
  - "etl/tests/test_clearance.py"
  - "etl/tests/test_carriageway_occupancy.py"
  - "etl/tests/test_clearance_reconcile.py"
  - "etl/tests/test_narrowing.py"
  - "etl/tests/test_corridor_truth.py"
---

# Clearance, the widening and the corridor graders — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`surface.floor_default_m`, any `roads.surface` widening change, or anything that moves the pipeline's
  starved population — `ALONG_M` included: also `tools/narrowing.py`, before and after.** It is what
  priced the current value: narrowing clears *no* blocked edge at any factor down to the 1.3x floor
  and loses two — `e207` and `e595` (`Q19`). A change that does not re-run it is re-opening a
  question that has been measured shut. ⚠️ **The second trigger is the non-obvious one**: this tool
  imports `pipeline.clearance` whole, so its class split and refusal table are computed over the
  pipeline's own starved set and a resolution constant moves them without touching a width.
- **`clearance.py` or `carriageway_occupancy.py` changes: also `tools/clearance_reconcile.py`, and
  paste its table.** The pipeline publishes a number that tool grades, they disagree — 24 starved
  edges against 26 — and the gap is **reconciled** as plan cell size (`Q51`). The reconcile tool is
  the ratchet that keeps both figures describing the same bundle, and it fails when either count
  moves: a finding to go and look at, never a bar to retune. Add `--sweep` when the change touches a
  resolution constant — `ALONG_M`, `ACROSS_M`, `CELL_M`, `SUBDIVIDE_M`, `MAX_SUBDIVISIONS`,
  `INDEX_CELL_M` — because those are what the gap is made of.
  ✅ **`ALONG_M` is `CELL_M` since 2026-08-19, so the published clearance is a lower bound** at that
  cell and `is_routable` no longer routes traffic onto a wall. ⚠️ It is a bound at `CELL_M` and no
  finer — a diagonal edge can corner-cross a cell, which a 0.25 m walk catches and the shipped one
  does not. ⚠️ **`ALONG_M` is still shipped behaviour, not a tuning knob**: moving it re-publishes
  `city.json` and changes what routing refuses, so it is the user's call. Numbers in `Q51`.
  ⚠️ **`tools/narrowing.py` is owed too** — see the bullet above for why that is not obvious.
- 🔴 **`clearance.LEVELS` and `carriageway_occupancy.CORRIDOR_LEVELS` are `(0, 1)` since
  2026-09-04 and they move TOGETHER — `centreline_error.py --levels` and `narrowing.py` stay at
  `(0,)`.** The bundle publishes a level-1 `clear_width_m`: `e208` FLEMING ROAD reads **2.00 m**,
  under the lane bar and over the car's 1.80 m, where it published `-1.0` before. That is `Q13`'s
  refusal expiring where it stood — `Q103` had already measured that 39 of 60 off-grade ends are
  reachable by driving at them. 🔴 **A level is a BUNDLE change and the user's call**, so `_write`
  still refuses anything but `LEVELS`; what the knob buys now is level **−1**, left out because a
  bore has no deck for this walk to find and `e489`'s defect is 0.22 m of *headroom* that a
  horizontal corridor cannot express. ⚠️ **Keep `clearance.LEVELS == carriageway_survey.levels`** —
  a corridor across a width nothing surveyed is the failure — and
  `test_the_shipped_levels_match_the_width_surveys` is the ratchet.
  🔴 **NO LONGER INERT — `P4-1` reversed it 2026-09-04 (`Q111`), and the invariant is now
  `open exactly where clearance.LEVELS measures`.** `fence.touchdown_levels` is `[-1, 2]`,
  `RoadGraph.is_drivable` is `level == 0 or the bundle measured a corridor here`, and
  `test_the_open_levels_are_the_measured_levels` pins the two together — it refuses `[-1, 1]`,
  `[-1]` and `[]` alike. ⚠️ **So moving `LEVELS` now moves what a player can drive on**, not just
  what a number says: widening it without opening the matching level fails that ratchet, which is
  the point. ⚠️ **Level 2 is listed in `touchdown_levels` and is inert** — it makes the invariant
  total, so a level-2 edge in a later region is closed until something measures it. 🚫 **Level −1
  stays shut and a wider `levels` is not the way in**: `e489`'s defect is 0.22 m of headroom and
  needs a vertical instrument. ⚠️ **`fenced_edges` takes the CLOSED levels, never the literal 0** —
  that literal's stated reason ("the off-grade network is closed already, at its touchdowns")
  expired the moment level 1 opened — and it is 0 of 45 today, so mutation-check the paired tests
  rather than reading the count. ⚠️ Prove a change to the walk inert
  the way `Q96` says, in **two** steps, because only the first can be byte-for-byte: hold the
  levels and reproduce `clearance.json` exactly (`Q108`'s frame fix did, at `fa5bcf39…`), then
  move the level and check that every row that moved is one the old default never walked — **45
  moved, all level 1, 0 at grade**.
  🔴 **`pipeline/fence.py::fenced_edges`' level filter is LOAD-BEARING now and reads as
  belt-and-braces.** Off-grade rows were all `NOT_MEASURED` before, so `starved` skipped them
  whatever that line did; it is now the only thing between a measured off-grade width and a barrier
  across a live ramp. It is 0 of 45 today and **reachable**, so mutation-check
  `test_an_off_grade_edge_under_the_bar_is_not_fenced` rather than reading the count. ⚠️ **Do not
  "fix" it by fencing off-grade**: `fence.touchdown_levels` already closes that network at its
  touchdowns, and a second barrier would stand behind the first.
  🔴 **`clearance_reconcile.py` takes ONE `--levels` reaching both halves, and that is not
  cosmetic** — `published()` read every row in `city.json` while `grade()` walked level 0, which was
  one population only while the pipeline published one level. ✅ The ratchet moved 19→**21**,
  21→**25**, 4→**6**, and the at-grade halves are **unchanged at 19 / 21 / 4** — a move that cannot
  say that is a bar retuned, not a population arriving. Numbers in `Q108`.
  🔴 **The occupancy flag is strictly ADDITIVE and a set omitting 0 is refused** — the corridor gate
  reads the level-0 rows alone, so `--levels 1` left it an empty population and printed *"Within the
  accepted bounds."* on a bundle with 21 starved edges. The unmapped-level guard cannot catch that,
  because level 1 *is* mapped. ⚠️ **Widening moves no share**: that tool's area half always walked
  every level and reported per level, and only its corridor was bound to 0 — so an inertness proof
  here is the corridor table, not the shares. 🚫 **Negative levels are refused deliberately**:
  `walk_carriageway` skips them and folding them in would add their area to `drawn_share`'s
  all-level denominator, loosening the two gated bars by a choice of divisor. So this tool **cannot**
  corroborate `e489`: that refusal puts level −1 out of its reach, and no height reading changes it
  (`Q103`).
  ⚠️ **`--probe-edges` DOES read heights, and its two bounds are one-sided in OPPOSITE directions** —
  `index_corners` prunes any triangle that misses the bumper band, so `base` is an **upper** bound
  (a negative reading is *proof* geometry reaches the road, which is how the four level-1 edges were
  cleared of `e489`'s headroom defect) and `top` is a **lower** one (a short reading is never
  evidence of clear air above). Reading `top` as headroom is the trap. It reports for named edges
  only, gates nothing, and the corridor half above is still the horizontal instrument it was.
  ⚠️ **Do not import the parse from `pipeline.clearance`** — that
  module's bumper bounds are `ground_clearance.py`'s deliberate exception and no second import comes
  in on it.
- 🔴 **`carriageway_occupancy.py` walks TWO windows since `P3-33e` and each half is owed its own**:
  the ribbon for the area shares, the corridor (`walk_carriageway(corridor=True)`) for the corridor
  half and for `clearance_reconcile.py`. Two rules are the corridor's alone and both came from a
  wrong build — it is **tapered between vertices** as `clearance.py` walks it (`e751`, 22.5 m to
  6.4 m in 9.5 m), and **an undrawn corridor cell stands at its own ribbon's height**, only where
  that ribbon is drawn (`e402`'s ramp; a junction trim stays refused). Prove a change to either by
  the sweep line — the grader at the pipeline's 0.50 m cell reads 24 against 28 and 10 against 9 —
  and an unchanged share table. `EXPECT` is 28 / 32 / 8 and 9 / 13 / 4. Numbers in `Q129`.
- **When `clearance.py` and `carriageway_occupancy.py` disagree about one edge, the answer is
  `tools/corridor_truth.py` and never a preference between them (`Q110`).** Both bin occupiers in
  plan and both over-block at their own bin — 0.5 m against 1.0 m — so the published widths are
  lower bounds that differ by the bins, and the first move is always to re-run the grader at the
  pipeline's own resolution (`--across-m 0.25 --index-cell-m 0.5 --spacing-m 0.5`), which closed
  `Q109`'s 0.65 m gap to 0.10 m on its own. 🔴 **The exact tool can CLEAR an edge and can never
  CONDEMN one**: the clip is closed-form with no plan cell, no across cell and no sampling, and
  **every** tile triangle blocks with no colour filter, so its reading is a lower bound on the true
  corridor and a figure *above* a bar is proof while a figure below one is evidence of nothing.
  ⚠️ **So its level-0 rows are a control on the machinery, not a reconciliation** — unclassified
  geometry includes classes both instruments exclude, and `e132` reads below both. ⚠️ It asks what
  stands *in* the bumper band and never whether deck stands *under* it, so beyond the ribbon's rails
  air reads clear; `deck_margin.py` and `overhang.py` are what answer that half. ⚠️ Its frame comes
  from `overhang.py`'s helpers deliberately (a third hand-rolled frame would be `Q106`'s fifth tool)
  and its bumper bounds are **restated**, on `carriageway_occupancy.py`'s precedent. It grades rather
  than checks and exits 0 whatever it finds. Numbers in `Q110`.
