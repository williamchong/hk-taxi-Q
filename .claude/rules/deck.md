---
paths:
  - "etl/pipeline/roads.py"
  - "tools/deck_margin.py"
  - "tools/touchdown_error.py"
  - "etl/tests/test_deck_margin.py"
  - "etl/tests/test_roads.py"
---

# Off-grade ribbons, decks and touchdowns — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`_deck_heights`, `_descend`, `_lifted_heights`, or `deck.touchdown_max_grade_pct`: also
  `tools/touchdown_error.py`, and paste its table — plus the roads stage's `descended / refused /
  graded across` line, before and after.** 🔴 **`deck_error.py` cannot see this defect and never
  could**: where the structure is absent there is nothing to measure against, so a ribbon clamped
  level in the air over an unmodelled touchdown reads as *uncovered* rather than wrong, and it
  scored a clean `P2-7` acceptance over a flyover visibly afloat above the street (`Q90`).
  ⚠️ **The grade is measured ribbon-to-ribbon, `clearance_m` included, never off the deck top** —
  the deck-top reading is ~0.2 m shallower over the same run and understated every row of `Q90`'s
  first table. ⚠️ **`touchdown_grade_pct` is recorded over the refusals as well as the keeps, and
  `n` exceeding `ends_descended` is how you tell** — recorded below the guard it is confined to the
  cap by construction and reports a clean sweep whatever the data does, which is `Q58`'s
  `drawn_gauge_m` trap for the fourth time. 🔴 **There is a THIRD refusal and it is deliberately
  OUTSIDE that distribution**: `ends_no_target` counts an end with no terrain to measure from, and
  it must stay counted rather than appended — an end with no grade has no grade to record, and
  review found this one holding the identity true by never reaching the list. So the partition is
  `len(touchdown_grade_pct) == ends_descended + ends_over_grade`, with `ends_no_target` beside it.
  🔴 **`_descend` gates on a LEVEL-0 edge at the node, never on "mixed"** — `elevation_levels`
  declares a level 2, and a `(1, 2)` node is mixed with no street to land on. ⚠️ **The grader cannot
  catch that**: a wrongly descended end is no longer clamped, so `clamped_m == 0` drops it from both
  halves of its partition. ⚠️ **`_deck_heights` and `_lifted_heights` ask different questions of the
  same node** — `sample_along` continuity against `sample_lowest_above` + `at_grade_m` — so both
  firing on one end is possible and would re-open a step; the 16 lifted and 9 descended ends are
  measured disjoint, which is data and not construction. ⚠️ **The bar is one-sided on purpose**: a ribbon still
  clamped *inside* the cap is the defect returning, one clamped *over* it is the refusal working.
  ⚠️ **`overhang.py` will read slightly worse and that is the instrument** — it asks whether
  structure lies under the ribbon, never whether air does, so a ramp resting on the terrain still
  counts as hanging and `Q22` is untouched. 🔴 **The evidence is a frame** (`Q62`): every counter
  read correctly while the bridge floated, so shoot one fixed camera in `city_preview.tscn` with
  `--debug-view=off --hud=off`, twice, and `cmp` them — a `minimal` pair differs in the fps readout
  alone. ⚠️ **`check.sh` cannot help**: both its `on_structure` assertions skip off-grade edges.
  Numbers in `Q90`.
- **Anything that moves an OFF-GRADE ribbon — `surface.floor_by_elevation_level`,
  `floor_on_structure_m`, or an off-grade width: also `tools/deck_margin.py`, and paste its per-edge
  table, its pooled distributions and its counterfactual.** It decomposes `overhang.py`'s `Q22` figure into the deck's
  own span, the **signed** offset of the centreline from it, and the metres of ribbon with nothing
  under them — which is the difference between a ribbon that is too *wide* and one that is
  *registered wrong*, and those need opposite fixes. ⚠️ **It is NOT an independent check of
  `overhang.py`** — same faces, same class, same tiles — so a divergence is a bug in one of them,
  never a second source. They read **7.6%** against **4.3%**, and the gap is the run-versus-cell
  model (this one is an upper bound; see `--bridge-m` below).
  🔴 **A stale pair here is how `Q106` went unseen for a release** — both tools rebuilt the ribbon
  about the centreline while `surface._shape` draws it at `±half + offset_m`. If the two numbers
  drift apart again, that is the finding. 🔴 **`--bridge-m` is load-bearing and
  its default is sourced, not chosen**: `Q19`'s estate is not watertight, so a contiguous deck run
  terminates at the first hole and 921 of 1,948 stations read two or more runs; the gap distribution
  is bimodal (p50 0.40 m, then p90 3.37 m) and 1.0 sits between the clusters. Without it the tool is
  a hole detector reading 14.1%. ⚠️ **The plausible explanation for that gap was the junction
  refusal and it is measured FALSE** — `--junction-m 0` moves it 14.0 → 14.3%, the wrong way.
  ✅ **The overhang headline is cap-stable where the span is not**, so quote `--max-lateral-m` with a
  span and never with an overhang. ⚠️ It **grades rather than checks** and exits 0 whatever it finds.
  🔴 **Do not answer a hanging ribbon by extending `Q95`'s survey off-grade** — measured and refused:
  the publishers license 5 of 45 level-1 edges and their lines are a **2D plan projection**, so a ray
  from a deck centreline finds the street *underneath* and 2 of the 5 publish a width **wider** than
  the deck. Numbers in `Q103`.
  🔴 **The THIRD table is a COUNTERFACTUAL and not a reading (`Q105`)** — it cuts each station's
  ribbon back to its deck's own two rims and prices only what that costs: **2 of 1,327 priced**
  stations under `is_passable`'s lane bar, **1** under `fits_car`'s, **7** with a *negative* half
  and priced apart (`Q106`-corrected — the first reading was taken in the wrong frame).
  ⚠️ **There is deliberately no "stations on deck after the clamp" counter** — it is 1,334 of 1,334
  **by construction**, because a half cut to its own rim cannot overhang it, and printing it would
  put `Q58`'s trap in the one number a reader takes as the case for building this. The **benefit** is
  the hanging population the table above already prints. 🔴 **The two halves are published APART and
  their sum is not a width wherever either is negative**: `left + right` stays positive at all 8, and
  the pricing run counted *"0 undrawable"* over every one of them, so the tool refuses to print
  unless that count equals `centre_off_deck`. 🔴 **And the priced population EXCLUDES them, which the
  first build did not** — medians, minima, the sort key and both bar counts all ran over the eight,
  publishing `e208` at **0.70 m** where it is 2.90; `priced_widths` is the function that owns the
  exclusion and `TestPricedWidths` mutation-fails without it. ⚠️ **The paint given up is `overhang_m`
  exactly and unconditionally**, so it is deliberately not a column — `over p50` / `over max` above
  are the same numbers, and the table's only new content is the left/right split. ⚠️ **`e104` carries 5 of the 8 in one run**, so a
  fallback rule is part of any build. 🚫 **It licenses PAINT and never a `width_m`** — the rims come
  from one contiguous run of structure, which at `e208` is the interchange's — so a build clamps the
  **drawn ribbon** and leaves the published width alone, or it meets `Q103`'s own refutation of the
  per-vertex offset. ✅ **Cap-stable like the overhang and unlike the span, for its own reason**:
  `min(half, rim)` is bounded by the ribbon, not the cap, so the lane-bar count held at 2 across
  `--max-lateral-m` 11-20 while the deck span's max ran 19.00 → 36.20 m. ⚠️ **That sweep predates
  `Q106` and has not been re-run in the corrected frame**; the argument is structural and the
  numbers are the old frame's. Quote `--max-lateral-m` with a span and with neither of the
  other two. Numbers in `Q105`.
