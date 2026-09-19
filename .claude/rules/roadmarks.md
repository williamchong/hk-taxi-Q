---
paths:
  - "etl/pipeline/config_blocks/roadmarks.py"
  - "etl/pipeline/drawnsurface.py"
  - "etl/pipeline/roadmarks.py"
  - "etl/tests/test_roadmarks.py"
  - "game/assets/shaders/marking_paint.gdshader"
---

# Road markings: white lines, stop lines and the inferred join — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **The WHITE LINES along a road are TD's survey since `P3-34` (`Q132`), and `draw_lane_lines` /
  `draw_centre_line` are 0.0 on the user's call: where TD surveys no line, none is drawn.** Do not
  switch either back on to fill a bare street — measured, the silent streets are surveyed streets
  with no centre line (nothing within 1.5 m of the middle on 94% / 84% of silent stations), and
  where the middle *is* occupied it is by hatching, zigzags or a yellow box an invented line would
  run through. **`road_marks.more_layers`, a `marks:` row, `broken_line`, `divides_flows` or
  `_host`'s `on` preference: paste `roadmarks.json`'s `drawn_by_id` / `drawn_m_by_id`,
  `host_off_carriageway`, `host_disagreement`, the `join` block and `slivers_dropped` before and
  after, both regions, and run `tools/paint_clearance.py --layer roadmarks`.**
  🔴 **TD files ONE family across sister layers** — `RM1001` in `DTAD_RD_MARK_LINE`, the broken half
  in `DTAD_RD_MARK_LINE_C` — and `Q118` recorded 4,211 m of at-grade double line as *absent* by
  reading one. A code missing from a layer is not missing from the geodatabase.
  🔴 **`broken_line` is an INSTRUCTION and a wrong side renders perfectly**: `RM1002` breaks the
  RIGHT line and `RM1003` the LEFT, *of the part's digitised direction* — TD's own frame, because
  it renders both through representation rules (`RULEID` 2 / 3) that ArcGIS applies along the
  digitised line. ⚠️ `band_quads`' `across` is **RIGHT** of that direction (it read "left" while
  every mark was symmetric), so bands run left → right; `test_the_broken_line_is_on_its_own_side`
  pins it against `surface.mitres` — mutation-check it. ⚠️ **No frame or counter can see a wrong
  side**; the only outside check is a Street View site.
  🔴 **A longitudinal line is hosted by a road it lies ON where there is one, and only then by
  angle.** Angle alone handed a line on one carriageway to a neighbour a fraction of a degree more
  parallel, which `_on_its_own_carriageway` then refused: 44 of 143 `RM1001` and 55 of 201
  `RM1101`. Both bars already existed (the candidate's drawn half-width, `bearing_tolerance_deg`);
  refusals fell 232 → 59 and `paint_clearance`'s buried share 3.0% → 1.7%. ⚠️ **Transverse hosting
  is untouched** — those rows and `underfill_m` must stay byte-identical across a change here.
  ⚠️ **`divides_flows` is what the inferred join yields to, and a lane line must never carry it**:
  it lies half a carriageway from the join, which is `_covered`'s own reach. `RM1104` carries it
  although most of it divides lanes, because the invention yielding too often is the safe side.
  ⚠️ **The publisher draws the RUN and not the dashes**, so the phase is `band_quads`' anchor at the
  part's first vertex. ⚠️ **`slivers_dropped` jumps (292 → 8,888 on Wan Chai) and that is priced, not
  ignored**: a 100 mm line is 2x the lattice bar, the casualties are the short quads beside source
  vertices, and they cost **0.41%** of the paint's plan area. ⚠️ **`height_spread_m`'s tail now
  reads a long line climbing a hill** (max 8.4 / 19.5 m) and is no longer a burial signal;
  `paint_clearance` is. ⚠️ **`lane_paint.py` still runs but its question moved**: the shader cuts
  the ribbon into `lanes_painted` strips for the bus lane and the kerbside yellows only. Schema 33.
  Numbers in `Q132`.
- 🔴 **`RoadMark.axis`, `longitudinal_legibility_scale`, or `_on_its_own_carriageway`: paste
  `roadmarks.json`'s `drawn_by_id`/`drawn_m_by_id`, `host_off_carriageway` and `no_host_on_axis`
  before and after, and run `tools/paint_clearance.py`** (`Q118`). 🔴 **The axis selects the HOST
  RULE, not a counter** — transverse scores `|90 - angle|`, longitudinal the angle itself — so a code
  declared with the wrong axis finds the most nearly perpendicular road, is refused by
  `bearing_tolerance_deg`, and draws **nothing with every partition still closing**. It is required
  with no default for that reason. ⚠️ **The bar is shared and means the same thing in both**, so do
  not add a second tolerance. 🔴 **`_on_its_own_carriageway` is a REFUSAL with a derived bar — the
  host's own drawn half-width — and it is longitudinal-only on purpose**: a stop line at a four-lane
  mouth is *supposed* to sit p90 16.1 m from the centreline it crosses, so applying it to transverse
  marks refuses the layer `P3-23` exists to draw. It took `paint_clearance` 1.50% → 0.21% and the
  worst height spread 4.51 → 1.18 m; ⚠️ **the obvious fix is REFUTED — do not re-propose sampling
  from the host's own edge**, which reads **8.58%** because a 236 m line spans several edges.
  🔴 **`longitudinal_legibility_scale` is AUTHORED and every `marks:` dimension is TRANSCRIBED — do
  not edit a published width to fix legibility.** The scale stretches geometry at draw time only;
  ⚠️ **the gap scales with the lines** or the pair closes into one bar, which is the sheet's own
  `LINES SPACING` trap from the back door; ⚠️ **longitudinal only**, or it moves geometry `P3-23`
  shipped and `underfill_m` measures. ⚠️ **Markings are clipped to the region** (`roads.clip`) —
  without it a 450 m line paints 44 of its 55 vertices over void — and that clip is **not inert on
  the transverse layer**, so a change there moves stop lines too.
  ⚠️ **The parts partition gained a leg — `outside_region`** — because `clip` returning nothing left
  `parts` uncounted; it is **0 and unexercised** here (no published part lies outside the region), so
  removing the increment leaves the suite green. Do not read its 0 as proven.
  ✅ **`_reachable` is GONE (`Q92`)** — `DrawnSurface` reads the published rails through a plan index.
  Do not bring a narrowing back.
  ⚠️ **`underfill_m` is transverse-only** — it is `host width - marking length`, and a longitudinal
  marking's length runs along the road, so pooling it is `Q57` in the one field that cannot survive
  it. Numbers in `Q118`.
- 🔴 **`road_marks.opposed_join_mark`, `opposed_joins`, `_covered`, `draw_opposed_joins`, or
  `surface.py`'s `opposed_pairs`: paste `roadmarks.json`'s `join` block — all seven numbers — before
  and after, and mutation-check the cut by disabling it** (`Q125`). This is the one placement in the
  bundle that is **inferred**: where two one-way carriageways run as a dual road, the line between
  the flows is drawn from `surface.py`'s geometric pairing along every metre TD surveyed no `RM1001`
  on. ⚠️ **`covered_m` is the counter that can fail** — with the cut off the two lines are drawn on
  top of each other, which is exactly what `Q118` switched `Q117`'s shader join off over — so it is
  mutation-checked, never read. ⚠️ **The join is counted APART from `drawn` and `drawn_by_id`**,
  which are over what the publisher surveyed and must stay byte-identical across a join change; that
  is the inertness proof. 🔴 **Do not switch `draw_pair_join` back on** — a shader yields per edge
  and 24 of the region's 95 pairs are only partly surveyed, and its line is 28 cm against the
  survey's 15. ⚠️ **No new knob**: covered is half the pair's own measured gap and the shared
  `bearing_tolerance_deg`. 🔴 **The pairing's reach is the drawn width plus ONE KERB
  (`style.kerb_width_m`) and that is a reading, not the free radius `Q72` refused** — two ribbons a
  seam apart are one drawn surface, which is the question `_paint_flanks` already answers with that
  same 0.5 m. It is what `Q19`'s floor leaves of a paved-over median: EXPO DRIVE EAST missed by
  0.245 m. ⚠️ **`13 / 24 / 58` is the CODEC's 95 ends, not the join's population** — the join draws
  **47** of the 54 published pairs, and the two counts must not stand in for each other.
  ⚠️ **Sweep it and paste the table** (flat at +0.25 and +0.50, one-sided 7 → 18 by +4.0),
  and ⚠️ **check that `centre_step` did NOT widen with it** — the codec's own `steps < 8 * lanes`
  must still refuse every added pair, so the shader's end count and `roads.glb` do not move. ⚠️ A change to
  `_opposed_gaps` still owes `Q117`'s bullet above — the three-number line, the angle sweep, the A/B
  render — and `roads.glb` must stay **byte-identical**, because publishing the pair moves no
  geometry. ⚠️ `over_refused_survey_m` grades and never gates: metres where the invention stands in
  for a *refused* survey line rather than for a silence. Numbers in `Q125`.
- **`pipeline/roadmarks.py`, the `road_marks` config block, or any stop / give-way line change:
  paste `roadmarks.json`'s two partitions, `host_disagreement` with `host_considered`,
  `axis_residual_deg`, `underfill_m`, `inverted`, and since 2026-09-16 `stations_on_drawn_structure`
  with `on_drawn_structure_m`, before and after.** 🔴 **Those two are the BUNDLE's word on structure
  beside the source's `on_structure` / `on_structure_m`, and they refuse stations, never features**: a
  station quad (or the piece of one the crease cut leaves past the host strip's end) over nothing drawn
  at level 0 and under a deck drawn above it is refused and counted rather than placed 52–131 mm inside
  the slab (`Q92`'s deck stub, 5 / 7.74 m on Wan Chai). ⚠️ **Two coverage facts, no radius, no knob**,
  asked from the piece's own side (`covers(toward=)`) because a cut corner sits on the end line and
  counts as covered. 🔴 **A void station with nothing drawn over it is KEPT** — a stop line reaching
  past a kerb is `Q54`'s on-kerb population — so mutation-check the rule's second half rather than
  reading its count, and do not "simplify" it to *over void → refuse*. ⚠️ **`levels_drawn` and never
  `elevation_levels`**: `DrawnSurface.of` refuses a level with nothing drawn. ⚠️ **`underfill_m` is
  measured against `roadsurface.json`'s DRAWN half-width, never the graph's authored `width_m`** —
  shipping the latter was an 18x error (p50 0.22 m against 4.04), and it is why this stage depends
  on `surface` as well as `roads`. There is no separate grader
  and there should not be: the stage grades itself, because every way this breaks renders as a
  perfectly drawn bar, or as nothing. 🔴 **`host_disagreement` is the load-bearing counter and
  `axis_residual_deg` is not** — the residual grades a rule that *optimises the thing it reports*,
  which is `Q58`'s `drawn_gauge_m` trap for the third time. The disagreement count is how often the
  transverse pick and the plain nearest edge choose different hosts, **90 of 209** today, and a fall
  towards zero means the pick has stopped picking. ⚠️ **This is the one stage that does NOT host by
  nearest edge, and that is not a bug to tidy away**: a stop line sits at a junction mouth, so
  proximity picks the road it is parallel to on 43% of the layer (`Q69`). ⚠️ **`axis_residual_deg`
  is recorded over refusals as well as keeps, and `n` exceeding `drawn` is how you tell** — move
  that append below the guard and every percentile is confined to `bearing_tolerance_deg` by
  construction, the defect review caught in `arrows.py`. ⚠️ **`inverted` must be 0** —
  `marking_paint.gdshader` is `cull_back`, so winding decides visibility and the normal attribute does
  not; and the engine-side and ETL-side winding tests have **opposite signs** (`Q59`), so do not
  "fix" one to agree with the other. ⚠️ **A dimension change is a `DATA_SOURCES.md` change**: every
  width, count, gap and dash module comes from TD drawing `CT174/51-5(1)F`, a **scanned** sheet with
  no text layer, so `Q59`'s by-eye rule applies and `Q67`'s rasterise-and-diff cannot help. And
  ⚠️ **`LINES SPACING` is the clear gap, not a centre-to-centre pitch** — the pitch reading draws
  every double marking at twice the weight and renders perfectly. ⚠️ **A roadmarks change is also a
  shader change, and its shader is shared with the arrows and the boxes** (`Q71`) — `check.sh` exits
  0 on a shader that fails to compile, so render and `grep -i "shader error"`, and look at all three
  layers rather than only this one. Numbers in `Q69`.
