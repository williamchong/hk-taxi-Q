---
paths:
  - "etl/pipeline/config_blocks/railings.py"
  - "etl/pipeline/railings.py"
  - "etl/tests/test_railings.py"
  - "etl/tests/test_railing_error.py"
  - "tools/railing_error.py"
  - "game/assets/shaders/railings.gdshader"
  - "game/tools/verify_railings.gd"
  - "game/tuning/{railings,bollards,barriers}.{tres,md}"
---

# Railings — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/railings.py`, the `railings` config block, or any railing change: paste, PER CLASS,
  `railings.json`'s `shift_m` (with its `n`), `samples_over_shift`, `metres_on_buried_kerb`,
  `metres_bridged`, `metres_dropped_collapsed`, `stations_merged`, `stations_folded`,
  `stations_unfolded` and `facing_away`, plus the shared `refused_m`, before and after — and run
  `tools/railing_error.py` and paste all three of its tables.** ⚠️ **Per class since `Q61`, and
  pooling them defeats the point**: the fence is 90% of the metres, so anything the two small
  classes did wrong disappears into its average. ⚠️ **The
  position of a railing is *registered*, not read** — the one place in the bundle a published extent
  is moved — because **67.9%** of the region's railing metres were surveyed inside the 1.6x ribbon
  (`Q60`). `shift_m` is the price of that and is recorded over the samples `max_shift_m` refuses, so
  **`n` must exceed what was drawn**; move that append below the guard and every percentile is
  confined to the bar by construction — `Q58`'s `drawn_gauge_m` trap, and the defect review caught in
  `arrows.py`. ⚠️ **`metres_bridged` is the one part of `drawn_m` the stage invents** — fence drawn
  across a gap the source never published, **320.58 / 39.89 / 28.00 m** per class today — so a jump
  in it is `bridge_gap_m` reaching further, not more railing. ⚠️ **The metre counters do not form a
  partition**: the refusals live in two frames, published and ribbon, which is why `metres_dropped`
  is **three** fields — `short` in published metres, `sliver` and (since `Q112`) `collapsed` in
  ribbon metres, and a collapsed piece is not a short one. ⚠️ **A widening change is a railing change**: `surface.floor_default_m` moves the drawn kerb and
  therefore moves every fence, silently and plausibly. ⚠️ `facing_away` must be **0** and
  `railings.gdshader` must stay `cull_disabled` — it is the only generated mesh that is, and the
  slab did **not** make that redundant: the fence is 60-75% air, so through every gap in the near
  face the player sees the *inside* of the far one.
  🔴 **The fence is a SLAB since `Q112`, extruded OUTWARD ONLY** — road-side face, far face, cap —
  so the registered face never moves and `outset_m` still means what it says (`Q78` at a second
  layer). ⚠️ **The three windings come from one convention**: near takes `flip`, far takes
  `not flip`, the cap takes `flip` again. Winding each quad to whatever normal it was handed, or
  dropping the triangles that disagree, makes `facing_away` 0 **by construction** — `Q58`'s trap in
  the one check that can see this layer built backwards.
  🔴 **`min_station_gap_m` and `fold_tolerance_deg` are two bars for two DIFFERENT degeneracies and
  must not be merged.** Two stations at one place are not a facing problem at all — as a sheet the
  quad had no area and the collapse bar deleted it, as a slab the two facings pull its far rail into
  a 50 mm panel across the fence; a *fold* is the offset rail running across its own centreline, and
  its repair takes a facing from along the run. 🔴 **The fold rule fires only where EVERY step at a
  station folds** — "any step" repaired `e642` station 18, whose facing was serving its own panel,
  to −0.55. ⚠️ **Sweep both and paste both**, and note `facing_away` is reachable in the failing
  direction at four of the sixteen rows, which is what says it is not confined by construction.
  ⚠️ **`facing_away` reads the FIRST vertex's normal and the nearside reversal moves which vertex
  that is**, so an offside quad is graded on station `i` and a nearside quad on `i + 1`. The shipped
  sheet's weakest triangle read **+0.23** and was saved only by its run being nearside.
  🔴 **`railing_error.py`'s walk knows about the slab and its p50 is now the MID-SURFACE** — half a
  thickness outside the registered face, uniformly. It folds the two foot lines together from the
  mesh's own topology and deliberately does **not** tell them apart: "the end nearer a centreline"
  picks the wrong face on 2,526 of 5,067 pairs, and the normals are `facing_away`'s own claim.
  ⚠️ **Its `drawn_m` is the number that catches a broken fold** — both faces walked reads double,
  one face discarded per pair reads short.
  ⚠️ **`classes` is a whitelist read off code strings and nothing published defines them** — no
  index-plan sheet covers railings, and the layer's other 40 columns are cartography (`SYMBOL_SIZE_*`
  is plot inches, `COLOR` has no domain, `LINE_WIDTH_*` is null) — so a change to it is a
  `DATA_SOURCES.md` change and the refused metres are what makes it reviewable. ⚠️ **The split is by
  class of object and never within one**: five codes draw one fence, and keying a style to `CRAIL1`
  versus `HCAIL2` is `Q54`'s debit on the bundle's weakest-evidenced field.
  ⚠️ **A class is a parameterisation, not a shader** — all three share `railings.gdshader` and differ
  only in six mask numbers in their `.tres`, so a class handed the wrong `.tres` is a picket fence
  standing where a bollard should be and it renders perfectly. `verify_railings.gd` checks the
  dispatch per class; a new class needs a row there, in `generated_scene_import.gd` and in the config,
  and `check.sh` fails if the three disagree.
  ⚠️ **`ALPHA` is coverage, not translucency, and there must be no opacity dial** — the steel is
  opaque and the gaps are gaps. One would repeat `marking_paint.gdshader`'s recorded misreading of
  `paint_opacity`.
  ⚠️ **A railings change is also a shader change** —
  `check.sh` exits 0 on a shader that fails to compile, so render and `grep -i "shader error"`.
  Numbers in `Q60` and `Q61`.
  🔴 **`railings.glb` is a LIBRARY since `P5-5` — one unit panel per class — and the city is
  `railings_placements.json`** (`Q115`). Also paste, per class, `panels`, `metres_snapped`, `joints`,
  `joint_gap_m` and `bends`: `drawn_m` is the TILED metres now, within half a panel of the clipped run
  at each end, and the residual and the far-face wedge at every joint are published rather than
  closed — a panel stretched or turned to hide either is `Q54`'s invented fence. 🔴 **`panel_m` IS the
  `.tres` `post_pitch_m`**, bound by test: a joint stands under a post. ⚠️ **`facing_away` is asked of
  the panel and never per stand** — a rotation turns winding and normal together, so per stand it is
  `Q72`'s tautology. ⚠️ **`railing_error.py` walks the UNIT and stands its samples** — a pitched
  panel's foot and head no longer share an `(x, z)`, so walking the expansion breaks its pairing.
  🔴 **The kerb a fence stands on is the ROAD's (`drawnroad.Ribbon.kerb_at`) since `P3-35d` (`Q133`),
  never `±half` about the centreline** — a level-0 rail is a SHARE (`Q57`). Three rules move
  together: the standing line (`near + outset`, `off − outset`), the SIDE (the nearer kerb about the
  road's middle — `SideIndex`'s is about the centreline), and the FACING (toward `Ribbon.middle`).
  `TestRoad` holds one test per rule; mutation-check each alone. ⚠️ **Prove a change here inert by
  forcing the road symmetric** (`offset_m = 0`, no kerb line): it must reproduce the prior bundle
  byte-for-byte. ⚠️ **`bends` is the price** (32 → 81 / 10 → 24): the kerb is read every few metres
  and a rigid panel does not follow it. 🔴 **The standing line is the PLAIN offset, never
  `surface.boundary`'s hold** (`P3-35d5`): a fence is a line samples are stood on by station, not a
  polygon, and the hold stood 8 m of Causeway Bay `e10` on one point. ⚠️ **A kerb station within
  `min_station_gap_m` of a published vertex is dropped** (`_own_places`) — the same place and not
  the same float, and a 0.2 mm step has no direction for any backward test to read. 🚫 **Do not count "panels in the road against the kerb
  line"** — the fence is built from that line, so it reads 0 by construction (`Q58`);
  `railing_error.py`'s to-source table is the independent reading.
