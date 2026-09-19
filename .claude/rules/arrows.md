---
paths:
  - "etl/pipeline/config_blocks/arrows.py"
  - "etl/pipeline/arrows.py"
  - "etl/tests/test_arrows.py"
  - "game/tools/verify_arrows.gd"
  - "game/tuning/arrows.{tres,md}"
  - "game/assets/shaders/marking_paint.gdshader"
---

# Turn arrows — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/arrows.py`, the `arrows` config block, or any turn-arrow change: paste `arrows.json`'s
  two partitions (`symbols` and `candidates`), `axis_residual_deg`, `offset_m`, `against_one_way`,
  `stacked_pairs`, `stacked_disagreeing`, `outside_carriageway` and `inverted`, before and after.**
  🔴 **The lane snap's denominator is the SURVEYED `width_m` and never `lanes x lane_width_m`** (`Q96`).
  That identity was `roadgraph.json`'s until `Q95` measured the width, and this stage went on rebuilding
  it for itself on 292 of 737 edges — reading `e351` CANAL ROAD EAST's 16.11 m as 6.4. ⚠️ **A change here
  is inert on the 445 authored rows by construction**, so force the old denominator region-wide first and
  require a **byte-identical** `arrows.glb`; that is what separates the refactor from the fix.
  ⚠️ **`outside_carriageway` is not `outside_drawn_ribbon`** — surveyed frame against drawn frame, 38
  against 9 — so quote both or neither. ⚠️ **At `lanes == 2` the snap reduces to `sign(offset_m)` and no
  width can reach it**, which is 670 of 737 edges, so a width change that moves nothing here is expected
  rather than a failure. There is no separate grader and there should not be: the stage grades itself,
  because **every way this breaks renders as a perfectly drawn arrow, or as nothing**. An arrow on
  the wrong street, turned 180°, or drawn from a mis-transcribed glyph table all look correct in a
  frame. ⚠️ **The residual distributions publish p90/p99/max, not a median** — the tail is where a
  match to the wrong road goes, and a median near zero is also what a wholly broken join looks like.
  ⚠️ **`axis_residual_deg` is recorded over the symbols the stage *refuses* as well as the ones it
  keeps, and `n` exceeding `drawn` is how you tell.** Move that append below the guard and every
  percentile is confined to `bearing_tolerance_deg` by construction — it read max 28.87 against a
  30 deg bar for exactly that reason until review caught it. `Q58`'s `drawn_gauge_m` trap.
  ⚠️ `inverted` must be **0**: `marking_paint.gdshader` is `cull_back`, so winding decides visibility and
  the normal attribute does not. ⚠️ **The engine-side and ETL-side winding tests have opposite
  signs** — Godot winds front faces clockwise and glTF counter-clockwise — so do not "fix" one to
  agree with the other; `Q59` records how that was settled and against which meshes.
  ⚠️ **A glyph-table change is a `DATA_SOURCES.md` change**: the codes come from TD drawing
  `CT174/51-5(1)F`, a **scanned** sheet with no text layer, and reading the histogram instead would
  have painted 61 `RM1116`-`RM1119` *warning* arrows as turn instructions.
  🔴 **And so is a *dimension* change, because that sheet publishes `LENGTH` for `RM1017`-`RM1030`
  and nothing else** — every proportion is read off TD's pictogram by eye (`Q59`), and `Q67`'s
  rasterise-and-diff cannot help here because the page is a scan. ⚠️ **The turn branch is not the
  ahead head**: reusing its length made `shoulder = reach - head_length` **negative**, put the turn
  head's base past the far side of the stem and merged the two into a blob on **416 of 747** arrows,
  through a release and a green `check.sh`. `config.py` refuses that now, and
  `test_no_head_overlaps_the_stem_it_grows_from` catches the class whatever the numbers are —
  ⚠️ **mutation-check it rather than reading its pass**, the way `Q72` says a counter is tested.
  ✅ **The sheet IS drawn to proportion despite the NOT TO SCALE stamp, and that is measured**:
  `RM1016` publishes `SIZE = 5600(H) x 2000` and its pictogram reads **2.802** against 2.800. So a
  proportion taken off a pictogram here is evidence — check a self-dimensioning code before assuming
  otherwise. 🔴 **The turn branch is authored anyway, and the reason is the trap**: TD's branch head
  is *wider than it is deep* because thin swept barbs do the work, so this model's plain triangle is
  a mushroom on the shaft and the faithful dart is a detached diamond — and its barbs are 0.09 m on a
  4 m arrow, which `Q91` removes at any driving distance. Fidelity to the drawing and legibility on
  the road are not the same target on this layer. ⚠️ **The ahead head and the stem taper are measured
  and must stay so** — the overlay agrees on both. Numbers in `Q93`.
  🔴 **`stacked_disagreeing` is `Q19`'s invented lane count arriving where a frame can show it, and
  it is 25 of 747 today** — 51 → 35 when the count became measured, 35 → 24 when the arrows' own
  row was let resolve an ambiguous bracket (`Q94`), 24 → 25 on 2026-08-30 (`e114` HENNESSY ROAD), 25 → **29** on 2026-09-05 when the floor came off
  the lane count (`Q114`), 28 → **25** on 2026-09-17 when the row was read by direction (`Q126`), 24 → **18** on 2026-09-18 when a row could raise an unmeasured edge's count (`Q130`) — on a one-lane edge there is one slot, so two differently-instructed
  arrows share it, and the count is now a finding about a *measured* lane count rather than an
  invented one. The registration snaps a published offset to one
  of `ribbon.lanes` slots; the count came from the speed-limit table, so where the painted carriageway
  is wider two
  symbols collapse into one slot and draw **one shaft wearing two branches** — found from the driving
  seat, with every other counter correct and `inverted` 0. ⚠️ **Nothing is refused and nothing is
  moved**: de-duplicating would discard a published instruction on the authority of an invented
  width, which is `Q54` inverted. ⚠️ **A rising count is a finding, never a bar to retune** — and it
  is reachable at zero, so mutation-check it rather than reading its value. ✅ **The arrows are also a
  lane-count source** — a row across a carriageway is the count written down, 31 of 306 edges imply
  more lanes than the graph has — which is the most direct lead `Q19` has — ✅ **and it now ASSIGNS,
  not just grades**: a row resolves the brackets TPDM leaves ambiguous, `lanes` measured 153 → 210 of
  737. 🔴 **A row of ONE arrow is not a row.** It counts *painted* lanes, so it is a **lower bound** —
  an unpainted lane is invisible to it — and at one abreast it states a marking, not a count; 81 edges
  do that. ⚠️ **Refused, never floored**: flooring them published 28 edges whose `lanes_source` said
  `arrows` and whose count the arrows had not chosen, which is `Q72`'s tautology wearing the other hat.
  🔴 **Ambiguous brackets only, so the row is never a standalone publisher** — that keeps
  `verify_road_graph.gd`'s "measured lanes implies measured width" true by construction. ✅ **STEWART
  ROAD `e505` is fixed since `Q130`**, by a SECOND rule rather than by widening this one: where no
  width was licensed, a row RAISES the count as `arrows_unmeasured`, which that check exempts and
  then requires an authored width beside.
  ⚠️ **The clustering is a SECOND implementation and the duplication is forced** — `arrows` imports
  `roads` imports `carriageway`, so no import exists — and `arrows.json`'s `lanes_row_disagreement`
  grades it at 0 of 57, over the rows the roads stage *published* and never all 306. Numbers in `Q94`.
  ⚠️ **An arrows change is also a shader change** — `check.sh` exits 0 on a shader that fails to
  compile, so render and `grep -i "shader error"`. Numbers in `Q59`.
  🔴 **`arrows.glb` is a LIBRARY since `P5-4` and the city is `arrows_placements.json`** (`Q115`): one
  flat glyph per `RM` code, nose north at the origin, stood by position, `rot_y_deg` and a
  **`pitch_deg`** between the deck heights under tail and nose. ⚠️ **The glyph is rigid where the merged
  build sheared it** — max 18 mm apart at the steepest 7.69° arrow — so a byte-identical `arrows.glb` is
  no longer the inertness proof for a lane-count change; the counters and `arrows_placements.json`
  are. ⚠️ **`inverted` is asked of the STOOD copies, never of the library or a determinant** — the
  pitch is a second rotation and only a stand pitched past vertical can make it non-zero.
  ⚠️ **`pitch_deg` composes BEFORE the bearing, in the mesh's own frame, on both sides** —
  `placed_positions` and `GeneratedPlacements.placement_of` — and `Basis.rotated` (world X) is the
  wrong call. `tools/paint_clearance.py` expands the library under its placements; a tool reading
  `arrows.glb` alone grades seven glyphs lying at the origin over no road.
  🔴 **And a shader change is a change to THREE layers**: `marking_paint.gdshader` is shared by the
  arrows, the box junctions and the stop lines since `Q71`, on `railings.gdshader`'s precedent — a
  layer is a parameterisation, not a shader, and the colour lives in each `.tres`. So render and
  look at all three, not just the one you changed. ⚠️ The per-layer dispatch is still checked:
  `check_shader_material` compares the material's `resource_path`, not the shader, so a mesh handed
  the wrong `.tres` still fails — do not reach for `check_shader_source` to quiet it.
