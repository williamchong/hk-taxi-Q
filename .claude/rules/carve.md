---
paths:
  - "etl/pipeline/carve.py"
  - "etl/tests/test_carve.py"
---

# The carve — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/carve.py`, the `carve` config block, or any change to which edges are carved: paste
  `carve.json`'s per-edge rows (`carved_area_m2`, `carved_volume_m3`, `wall_m`, `soffit_bounded`,
  `triangles_removed`), `tiles_written` and `facing_away`, before and after — and run the whole
  `Q19` battery:
  `carriageway_occupancy`, `deck_error`, `overhang`, `ground_clearance`, `clearance_reconcile`,
  `narrowing`.** 🔴 **The cut face is CONSTRUCTED, not derived, and that is measured rather than
  chosen**: the estate is **not watertight** — 5.38% of edge slots open across the 74 source
  `INFRASTRUCTURE` meshes, 14-26% in the decimated tiles — so a cap taken from "edges the removal
  opened" returns **zero** closed loops. ⚠️ **Carving at source rescues nothing**: `roads` reads no
  tile so the stages *could* be reordered, and the sheets are no more watertight than the tiles.
  🔴 **A second pass DEGRADES the first and the stage refuses one** — the wall stands on the prism's
  own side planes, so a re-run eats it and rebuilds it shorter (`e327` 141.8 → 75.8 m, every counter
  still closing). `buildings.json` carries a `carved_edges` marker; ⚠️ this is reached by
  `--from roads`, not only by running the stage twice, and the fix is always to rebuild from
  `buildings`. 🔴 **The wall takes its colour and class from the structure REMOVED, never from the
  tile** — a tile's first vertex is usually a building, and the window-band shader then draws storeys
  of glazing on concrete while the share moves between two gates (`BUILDING` 1.204 → 1.292% when it
  was wrong). ⚠️ **`carved_volume_m3` is accumulated per prism**, because one box over a whole edge's
  removals spans the ramp's curve and reports many times what was taken. ⚠️ **The prism is the
  surveyed `width_m` and never the drawn floor**, and a residual is never answered by widening it —
  that is `Q54` inverted. The three residuals are the grader's 1.0 m plan bin, not a failed cut.
  🔴 **`e99` is the block's ONE exception and it is not a precedent.** Its prism is cut at an
  **authored** 6.40 m — exactly what the sentence above forbids — taken on 2026-09-01 because a drive
  stranded the car there and no width bar can reach the defect: the obstruction is *interior*, with
  drivable road either side, so every rule that catches it fences 59-67 edges including major roads.
  What licensed it is that the **class** (100% `INFRASTRUCTURE`, 119 band hits, no `BUILDING`) and the
  **containment** (116 of 119 inside the authored width) were both measured — ⚠️ **pre-carve, and not
  reproducible from the shipped bundle**, which reads 115 and 72 because the cut moved the mass those
  figures describe. ⚠️ **The carve MOVES the
  wall to the carriageway edge rather than deleting it**, so a width instrument barely registers it
  (`e99` 4.50 → 5.00 m) while the interior obstruction goes — never read a small corridor delta as a
  small change. ⚠️ `e125`, `e207` and `e781` stay `P3-29`'s fence. Numbers in `Q19`.
  ⚠️ **`clearance_reconcile` fails until its ratchet is moved**, which is the ratchet working, not a
  bar to retune. ⚠️ **The evidence is a frame** (`Q62`): the `q19s` cameras, shot twice and `cmp`'d.
  Numbers in `Q19`.
- 🔴 **The parapet band is a SECOND population in the SAME pass** (`P3-51`, `Q147`, the user's call:
  a carved ramp's edge is jumpable). `carve.parapets`' population is the carve's own `edges` — a
  listed edge takes the band whole — plus, by RULE, every edge on a banded level and every run of
  level-0 `on_structure` stations; **both ship OFF** (`levels: []`, `on_structure: false`): the band
  over every flyover edge was built, measured and withdrawn on the user's call (`Q147`, "keep the
  original structure"). 🚫 Do not re-propose it; flip the switch on his instruction only, and the
  numbers to expect are in `Q147`. Declared, the stage reads every region's tiles, so
  `test_a_region_with_no_edges_carves_nothing` strips it first. Paste, per band row, `population`,
  `triangles_removed`, `carved_area_m2` and **`deck_top_kept`** before and after, the band's totals,
  and **the region's tile vertex total and bytes from `buildings.json`** — the number three refused
  shapes moved (`Q147`: +47%, +22%, then +4.6%). 🔴 **The band keeps the deck and removes the wall
  by the triangle's NORMAL, and takes a parapet WHOLE by its centroid, with NO prism** —
  `_band_split` and `_band_candidates`. A prism floored at the ribbon takes the deck top with the
  parapet and the car falls THROUGH the deck (`test_the_naive_prism_takes_the_deck_with_the_wall`);
  a prism's side and end planes slice every wall they straddle into slivers the tiles ship. Do not
  re-propose either. `deck_top_kept` is the counter a split mutation drives to 0; mutation-check it
  rather than reading its value (`Q72`). ⚠️ **Both halves of the split are needed**: by normal alone
  a cap is kept as a floating slab; by height alone the deck goes; and **`wall_max_m` is what keeps a
  pier, a neighbouring deck's side and a noise barrier** (`test_a_face_rising_past_wall_max_m_is_not_a_parapet`).
  ⚠️ **The band's width is the deck's RIM (`deck_rim_m`) station by station, never the authored
  width alone** — `e208`'s parapet stands 8.0 m out on a 5.60 m ribbon. ⚠️ **No wall for a band
  row** — `wall_m` is 0 on every band row by construction, so it is not evidence. ⚠️ **`_snap_rows`
  is load-bearing**: the floor cut invents vertices whose `TEXCOORD_1` the slicer interpolates, and
  `verify_tiles` refuses a row between two objects. ⚠️ **Absent, the band is a no-op and the bundle
  is byte-identical** — the `Q95` move. ⚠️ Schema 2: `population` and `deck_top_kept` per row.
  🔴 **A widening, a `reach_m` or a `wall_max_m` change moves the band** the way `floor_default_m`
  moves a fence, so it owes this rule, `ground_clearance` and `clearance` too. The drive is the
  evidence a frame cannot give: off a listed ramp, `e99` FLEMING ROAD first.
