---
paths:
  - "etl/pipeline/surface.py"
  - "etl/tests/test_surface.py"
  - "tools/cap_pavement.py"
  - "tools/overhang.py"
  - "tools/deck_error.py"
  - "etl/tests/test_overhang.py"
  - "etl/tests/test_deck_error.py"
---

# The drawn road surface — before marking work done

- **Road-surface, deck-height or ground changes**: `tools/battery.py q19 --region <r> --before
  <root>` (`carriageway_occupancy`, `deck_error`, `overhang`, `ground_clearance`,
  `clearance_reconcile`, `narrowing`). They grade the shipped bundle and share no method with the
  pipeline. Widening, building footprints and landmark placement move `carriageway_occupancy`
  too; it gates per edge and currently fails (read the exit code; `PROGRESS.md` says on what).
- **The drawn ribbon is `[offset − half, offset + half]` per station** (`Q106`, `Q107`), never
  `±half` about the centreline. Read `half_width_m` and `offset_m` from `city.json`'s
  `carriageway[]` (`overhang.half_width_at`, `overhang.offset_at`) and pass the offset to
  `overhang.cross_section`. A tool whose own `offset_m` means a cell's distance from the
  centreline adds the drawn offset to it. At level 0 the rails are a territory, often more than
  1 m off the centreline.
- **The kerb** (`Q133`): `Ribbon.kerb_target`, `past_kerb_m` and `kerb_at` read the road's running
  kerb line (`drawnroad._kerbs`): `carriageway_region.json`'s dense stations, each side only where
  it ended at a kerb, straight between. Never the ribbon's rail (a share, `Q57`).
  - Measured shut: not `roadsurface.json`'s per-vertex `corridor_*` — built and withdrawn. Graded
    against iB1000's lamp posts it puts 24.2% of Wan Chai's in the road, against 21.8% for
    `±half` and 13.3% for the running kerb line.
  - `fence._dress` centres its row on `offset_m`, and the sign is load-bearing
    (`test_the_row_stands_across_the_ribbon_at_both_mouths`; mutation-check both ways).
- **`_clamped_rails`, `deck_rim_m`** (`Q107`): the off-grade ribbon is cut to its deck per station
  and per side, and may only cut. `width_m` does not move (`Q105`: a rim licenses paint).
  - No deck is `inf`, never 0.0.
  - `_deck_rims` discards the rim wherever `on_structure` is `False` (`Q113`): where a ramp lands,
    the walk finds a sliver of slab (0.100 m, `carriageway.DECK_ACROSS_M`). Do not read a small rim
    as a narrow deck; mutation-check the gate. `on_structure` also selects the authored width over
    the floor (`Q23`), so a fixture that sets it moves both.
  - A station whose rails cross keeps its ribbon and is counted; reachable, so mutation-check it.
  - `_slid_onto_deck` slides the ribbon back by its overhang before the cut, and never reads the
    deck's middle (`Q103`). Three refusals, no knob; `slide_refused_stations` at zero means the bar
    stopped refusing.
  - Owed: the stage's `slid back onto their deck` line and `battery.py off-grade`. No level-0 row
    may move, and no station may come out narrower or wider than `width_m`. Prove inertness by neutralising
    the clamp and rebuilding.
  - Evidence is a frame, and the cache lies: delete `game/.godot/imported/roads.glb-*` and
    re-import before each shot, aimed at the edge with the largest drawn-width change.
  - Rebuild `etl/out/wan_chai+causeway_bay` (`python -m pipeline.join`) after moving either region.
- **`_read_offside`, `_opposed_gaps`, `roads.surface.opposed_pair_bearing_deg`** (`Q117`): paste
  the stage's `edge ends are half of an opposed pair` line (all three numbers), sweep the angle,
  and A/B render one pair at a fixed camera. No separate grader: every failure renders as a road
  with no line.
  - The pairing is mutual. `opposed_pairs_one_sided` is the counter that can fail; mutation-check
    it.
  - Measured shut (`Q72`): no free search radius. The reach is the drawn width plus one kerb
    (`Q125`); `centre_step`'s population and `roads.glb` must not move.
  - The angle is the one free value: config, swept, and not a plateau (1.35x over 10–75°,
    one-sided 4 → 17).
  - Measured shut: no angle-free rule. Mutual offside-kerb burial was built and rejected: its
    share bar runs 62 → 4 pairs over 0.10 → 1.00.
  - `opposed_pair_bearing_deg` and `width_bounds.pair_bearing_tolerance_deg` carry the same number
    and stay two values (the survey block is optional). `_Ribbon`'s scalar filter duplicates
    `_Occluders.cover` on purpose (34 against 395 ms).
  - The plan-bounds reject is a bound: tests survive deleting it. The mutations that must fail
    are the anti-parallel test and mutuality.
  - Inertness: `roads.glb` byte-identical except `TEXCOORD_1.x`'s centre field; `roadsurface.json`,
    `roadmarks.glb`, `boxjunctions.glb`, `clearance.json` byte-identical.
- **`_Edge.is_stub`, `_stub_clusters`, `_cap_ring`'s corner rule, `junction_trim_max_fraction`,
  `_through_corridors`, `_far_section`** (`Q104`; off-grade and region-less bundles only — none
  runs at level 0 while a region is built): paste `roadsurface.json`'s `clusters` block and `caps`
  count, `box_extent.py` per box, `tools/cap_pavement.py --region <r>`'s two pooled lines, and the
  `carriageway[]` / `offset_m` / `trim_m` byte-identity.
  - A stub is the two existing trim decisions read together: no knob. One hull caps a cluster; a
    stub lends no corner. Mutation-check via `test_a_looser_ceiling_dissolves_the_cluster`.
  - A stub across a seam joins nothing (`test_a_stub_across_the_seam_joins_nothing`).
  - `cap_pavement.py` reads HyD in three states; quote past-kerb and unsurveyed apart, at one
    `--cell-m` and `--near-m`. For corridors quote new asphalt by HyD class, not quad area
    (20,000 m² of quad is 745 m² of asphalt). A corridor is unioned into the cap, never hulled.
  - Measured shut: no kerb-line corner rule for caps — it found the HKCEC wedge from two far-side
    rails extended across the junction.
  - Without a region, nothing is drawn under a box that overhangs its ribbon.
