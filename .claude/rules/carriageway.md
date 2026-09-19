---
paths:
  - "etl/pipeline/carriageway.py"
  - "etl/pipeline/carriageway_area.py"
  - "tools/carriageway_margin.py"
  - "tools/width_evidence.py"
  - "tools/centreline_error.py"
  - "etl/tests/test_carriageway.py"
  - "etl/tests/test_carriageway_area.py"
  - "etl/tests/test_carriageway_margin.py"
  - "etl/tests/test_width_evidence.py"
  - "etl/tests/test_centreline_error.py"
---

# The carriageway width survey — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **`carriageway_survey.edges` is THREE publishers since `Q94`, and the third is an AREA.** TD's
  painted edge and iB1000's margin are lines; HyD's Pavement Polygon draws the maintained carriageway
  as polygons, so `geometry: area` and `_union_boundary` — HyD tiles the region into **552** of them
  and a seam between two is not a kerb. ⚠️ **Preference order is load-bearing**: third, it adds 33
  edges and refines 50 without overriding a station the lines answered; **second, it re-baselines
  every published width**. ⚠️ **"Third" still does not mean "only where they are silent"** — the loop
  runs per station. ⚠️ It arrives via `paged_sources`, the third source kind, at **~163 MB on every
  clone** — second only to the 218 MB Traffic Aids geodatabase among sources a build reads.
- **`surface.floor_*`, `lanes_*`, `lane_width_m`, the `carriageway_survey` config block, or
  `pipeline/carriageway.py`: also
  `tools/carriageway_margin.py`, and paste its table.** It measures the drawn ribbon against the
  carriageway edge **two publishers actually print** — TD's `RM1108`/`RM1109`, then iB1000's `RM` —
  so its truth side is one no build reads, as `kerbside_source_audit.py`'s is. Unlike that one it
  shares no code with what it grades: the audit runs the pipeline's own join on a second source,
  this measures the shipped ribbon with neither. ⚠️ It **grades rather than checks** and exits 0
  whatever it finds; there is no bar, deliberately, and `Q19` records why.
  ⚠️ Quote the headline, not the two-source agreement: the headline is stable across
  the ray cap (p50 1.69 → 1.50 m from 10 to 25 m) and the agreement is not (p90 3.76 → 14.30 m over
  the same sweep).
  🔴 **It also publishes a per-edge SPAN since `Q95`, and that is a second table with different
  rules — paste both.** ⚠️ **The span is cap-sensitive where the overhang headline is not**, so quote
  its cap: coverage 54.7 → 81.8% and non-junction p50 7.40 → 9.15 m from 10 to 25 m. ✅ It saturates
  at the 15 m default — kept spans peak there at 8,204 and *fall* to 8,162 by 25 m — which is why
  there is one cap and not two. 🔴 **On a one-way edge the number is a KERB-TO-KERB SPAN and not a
  carriageway width** wherever the ray crosses an opposed pair; the TPDM ceiling cannot see that and
  `off_centre` is what does. The two coincide on 34 edges.
  🔴 **There is a THIRD table since the split, and it has different rules again — paste all four.**
  It pairs each one-way edge with its opposed partner and reports `own = 2 x near` per half with the
  leftover as the median. ⚠️ **Do not pool it into the span line**: that is `Q57`'s generalisation,
  a property established on one population and quoted for another. 🔴 **The load-bearing counter is
  the NEGATIVE residual, not the pairing count** — the parts exceeding the whole cannot be true, so
  it is the split refusing itself, and it reads **96 of 110** mutual pairs today because on most of
  the network *the ray never crossed the median at all*. All three LOCKHART ROAD pairs land there.
  A fall towards zero is a finding to go and look at, never a bar to retune.
  ⚠️ **"621 of 737 run as opposed pairs" was half asserted and is corrected**: 621 are one-way, and
  **110 of 352** with a median pair mutually. Only **14** decompose to a width.
  🔴 **The six shared-endpoint pairs in `surface.py` are the only ground truth for a pairing rule and
  cost nothing to check — check them.** Capping the partner search at the station's own far ray
  sounded principled and missed all three Lockhart pairs, whose partner centreline is 6.82 m away
  behind a far ray that stops at 3.5 m. The cap is `--max-ray-m`, the tool's own; 5 of 6 recover and
  the sixth is 9.0 m with no station clear of a node. ⚠️ **`--pair-bearing-deg` is the rule's one free
  value, so sweep it and paste the table** — `Q72` rejected a divider test whose count ran
  8 → 29 → 49 → 80 over a free radius, and this one is flat at 14 decomposed from 10° to 75°.
  🔴 **And a FOURTH since the crossing rule, which is the one that publishes WIDTHS — 276 of 387
  edges.** `beyond = span - 2 x near ray` is the room an opposed carriageway would need; under
  `hard_min_m` there is none, so the span *is* that edge's carriageway. ⚠️ **Three states, and the
  middle one publishes nothing on purpose** — TONNOCHY `e142` sits in it, and a single threshold in
  that gap ships a 16.7 m span as a width. ⚠️ **`carriageway_m` is not one population**: a decomposed
  row publishes half a span and every other row publishes the whole of one, so quote the `basis`
  column with it or it is `Q57`'s generalisation again.
  🔴 **`--dual-min-m` classifies and licenses NOTHING, so do not read its sweep as a plateau.**
  Over 3.0 → 14.6 the crossed count runs 79 → 0 while uncrossed and licensed stay flat at 230 and
  276 — that bound only moves rows between two states that both publish nothing, and every width
  rests on `hard_min_m` instead. Sweep it anyway; a *moving* licensed count means the states have
  stopped meaning what they say. ✅ **The width is cap-insensitive where the span is not** (p50
  7.15-7.18 m over a 10-25 m ray sweep), so quote the cap for the span line and not for this one.
  ⚠️ **The pairs' residual cross-checks this for free and its misses are about the PAIRING** — 12 of
  14 are rows whose partner claims an impossible half. A finding, never a bar to retune.
  ⚠️ `--json` writes `carriageway_width.json` under `etl/out/`, which is **gitignored** — a local act
  like `facade_lab.json`, and re-running is the only way back.
  🔴 **Lanes are a bracket from TPDM 4.3.9.8 (3.0-3.65 m) and never a division by `lane_width_m`** —
  dividing by the authored 3.2 makes the instrument agree with the value under test. ⚠️ **The bounds
  are config, not constants** (`carriageway_survey.width_bounds`), and the tool refuses to start
  unless `2 × max_ray_m` exceeds the ceiling — otherwise the cap manufactures a clean sweep, which is
  `Q58`'s `drawn_gauge_m` trap reachable from the command line. ⚠️ Its truth is a **2D projection carrying the publishers' own registration
  error**, which the bundle graders below do not inherit — that is the price of reading outside the
  bundle, not a defect to tune away.
- **`pipeline/carriageway.py`, the `carriageway_survey` block, or anything that moves `width_m`:
  paste the roads stage's `carriageway:` two lines before and after, run `tools/carriageway_margin.py`
  and paste all four of its tables, and run EVERY grader in the widening bullet above.** 🔴 **This
  stage is a SECOND implementation of the survey that tool performs and the duplication is
  deliberate** — the tool "shares no code with what it grades", and sharing a core to save six
  hundred lines would retire the only independent check on the reading. **They are expected to agree
  and a divergence is a finding**: today `|pipeline − tool|` is p50 **0.005 m** over the 259 edges
  both license, and the tool's own `measured − authored` line reads p50 **+0.00**. A drift there is
  the thing to go and look at. ⚠️ **Do not "fix" it by importing one into the other.**
  ⚠️ **The widths may never be read from `carriageway_width.json`** — it is gitignored generated city
  data under hard rule 7, so a build that reads it cannot be cloned (hard rule 2). That is *why* this
  stage exists. ⚠️ **`width_m` is no longer `lanes x lane_width_m`** and the schema is 5 because of
  it; `lanes` is still authored, so ⚠️ **this does NOT fix `Q94`** — `stacked_disagreeing` is
  byte-identical at 51 and only a lane count moves it. Numbers in `Q95`.
- **`tools/width_evidence.py`, `carriageway_margin.py`'s junction-openings section, or `carriageway_survey.lane_lines`: paste the synthesis table — both `|p90|` columns — for `wan_chai` and `causeway_bay`** (`Q127`). It grades readings of a carriageway width the survey cannot take and exits 0. 🔴 **Every reading is graded against the survey's measured edges FIRST, and the ray survey may never be a combination's second reading** — on a reference edge it IS the reference, and letting it vote certified a combination at 0.63 m by construction. 🔴 **Quote the `<60m` column with the pooled one**: the reference is long by construction (min 34.5 m) and the unmeasured edges run p50 24 m, and the unconfirmed HyD strip that reads 2.59 pooled reads 4.70 there — worse than today's rule. ⚠️ **The street borrow is leave-one-out** and `mouth_noise` is too; an edge in its own donor pool grades itself. ⚠️ **The junction opening rule is refuted, do not re-propose it** without a new idea about foreign nodes: it moves measured widths at every R and angle swept.
- 🔴 **`MIN_STATIONS`, `MIN_AGREEING_STATIONS`, `_station_scatter`, `_agree_m`, `DECK_MIN_STATIONS`, `pipeline/carriageway_area.py`, `_row_widths`, `_street_widths`, `_confirmed` or `carriageway_survey.confirm_within_m`: paste the roads stage's `carriageway:` block — the two-station line, the `HyD strip:` line, the both-read agreement line and `confirmed by:` — before and after, on BOTH regions, and run the whole widening battery above** (`Q128`).
  🔴 **The two surveys must walk the same way**, so `tools/carriageway_margin.py::shipped_rows` moves in the same commit — `STATION_M`/`JUNCTION_M`'s own comment is the rule, and the graders' independently derived tolerance (2.77 / 2.85 m against the pipeline's 2.81 / 2.91) is how you tell they still do.
  🔴 **The two-station licence is ADDITIVE BY CONSTRUCTION and must stay so**: three-station edges are assigned before the pass runs, so `_assign` takes no tolerance and a test pins that. A rule that re-reduced the whole population at a lower bar would owe "0 moved, 0 lost" every build instead of never.
  🔴 **The tolerance is DERIVED and read over the edges the BOUNDS admit, never the edges the licence attributed** — those refuse different things, and the narrower set reads 2.13 against 2.81 m, which is the licence leaking into the instrument's noise. It may not become config.
  🔴 **`DECK_MIN_STATIONS` must NOT follow the publishers' bar**: they reduce with a median, the deck with `DECK_WIDTH_PERCENTILE`, and a p10 over two values is the smaller of them nudged a tenth (`[8.0, 12.0]` → 8.4). It is reachable — 2 Wan Chai edges — and refusing it is what keeps the whole off-grade network and `Q107`'s rim clamp inert.
  🔴 **The strip is a CANDIDATE and the agreement is the LICENCE.** Alone it reads |p90| 2.53 m pooled and 4.69 m on the short edges it exists for, no better than the invented width it replaces, so `strip_unconfirmed` (203 / 53) is the counter the design rests on and a fall towards zero means the confirmation stopped confirming. ⚠️ **`confirm_within_m` is a trade curve, not a plateau** (0.75 / 1.23 / 1.58 m at 11 / 22 / 35% reach) — it is a value the city chooses, never a bar to retune when a count disappoints.
  🔴 **The ray survey is not a voter and `_confirmed` ASSERTS it**: on an edge it measured it IS the answer. Equally, **`hyd_strip` may never join `width_evidence.MEASURED`** — that would grade the strip against itself — and it is deliberately absent from `centreline_error._MEASURED_SOURCES` because a strip edge is by definition one no ray reached.
  ⚠️ **The openings filter here is NOT the rule `Q127` refuted**: that was a gate on the ray survey, which moves measured widths; this only drops stations from a reading published where the survey is silent, and the assert above is what makes that true rather than argued.
  ⚠️ **The `e99` gate**: `carve.py` cuts its prism at `edge["width_m"]`, and it is the only carved Wan Chai edge still `authored`. `carve.json`'s per-edge rows must be byte-identical, and a strip on a carved edge is a decision to bring back, not to absorb. ⚠️ `--from roads` is refused by the carve marker — rebuild `--from buildings`.
  ⚠️ **Most new widths move NO geometry**: `floor_default_m` is 10.24 m and a measured width under it draws the same ribbon, so count the widths clearing the floor first and expect the railing/sign/lamp/box/paint battery to be inert where that count is zero. Today it is **8 of 103** on Wan Chai and **7 of 57** on Causeway Bay.
  🔴 **`strip_agreement_m` is the only in-bundle grading of the strip and it COSTS 7.2 s of a 24 s stage** — the raster walks every level-0 edge and 59.6% of the stations are on edges a ray already measured. Skipping those is byte-identical on every published width, so that time is the instrument's price; it is a trade to take deliberately, never by accident. It is — the 289 edges both a ray and a strip read — and it is recorded, never gated: those edges publish the ray's answer, and it is agreement about the long edges rather than the short ones the strip serves. ⚠️ **This stage is 2.3x slower than it was (10.3 → 24.1 s) and the raster is all of it** — profiled, with the two apparent narrowings measured already-tight and a ±8.5 m corridor measured NOT inert. Two real wins are priced and deliberately untaken; do not re-derive them. Numbers in `Q128`.
- 🔴 **The two station normals in this repo are OPPOSITE, and that is deliberate — do not "restore
  consistency".** `pipeline/carriageway.py::_stations` emits `[-unit[1], unit[0]]`, **right** of
  travel; `surface.mitres` and `tools/overhang.py::left_of` emit **left**, and `mitres` names its
  frame load-bearing because `TEXCOORD_0` is a lane coordinate from the nearside kerb and Hong Kong
  drives on the left. `carriageway.py` can hold the other convention because it keeps only
  `ahead + behind` and `min(ahead, behind)`, **both sign-free**. ⚠️ **Anything that keeps the
  DIFFERENCE inherits `Q78`'s defect** — an absolute value cannot report the direction of the move it
  measures — so it needs a named negation and a mutation check, never a comment.
  `tools/centreline_error.py` is the one consumer today and
  `test_the_station_normal_is_the_negation_of_mitres` is what fails loudly if either side moves.
- **`Q19`'s three candidates are all priced and candidate 1 is REFUTED — do not re-propose a
  centreline rule.** (Refuted, not refused: no rule declined it, a measurement disproved it.) `tools/centreline_error.py` registers the published centreline against the
  middle of the carriageway a publisher spanned: the correction available is 0.02-0.88 m where
  1.43-4.49 m is needed, it clears **0** edges at either bar, and `e233` has no clear cell in its
  cross-section at any offset. ⚠️ **Run it again if `pipeline/carriageway.py`'s survey, `_stations`,
  `surface.mitres` or `clearance.py` moves**; it grades and exits 0 whatever it finds. Numbers in
  `Q19`.
