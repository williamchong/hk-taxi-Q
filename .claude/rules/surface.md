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

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **`surface._read_offside`, `_opposed_gaps`, or `roads.surface.opposed_pair_bearing_deg`: paste the
  stage's `edge ends are half of an opposed pair` line before and after — all three numbers — sweep
  the angle and paste the table, and A/B render one pair at a fixed camera.** The stage grades
  itself and there is no separate grader, because **every way this breaks renders as a road with no
  line down it**, which is what a correct road with one flow also looks like (`Q117`).
  🔴 **The pairing is MUTUAL and that is not tidiness**: each half computes the join in its own lane
  coordinate, so an unreturned vote is two halves naming different lines — the 3.9 m double line
  `P3-12` shipped on FLEMING ROAD. `opposed_pairs_one_sided` is the counter that can fail; it is 6
  and reachable at zero, so **mutation-check it rather than reading its value**.
  🔴 **The search distance carries NO FREE knob and must not gain one** — `Q72`'s rejection of a free
  radius is the whole answer, and nothing here may be swept for a count. ⚠️ **It is no longer the
  publish guard exactly** (`Q125`): the reach is the drawn width **plus one kerb**, for a second
  consumer that draws the join as geometry and is not written in a lane coordinate. The codec's own
  `steps < 8 * lanes` still refuses everything that term adds, so a change here must show
  `centre_step`'s population and `roads.glb` unmoved. The angle is the one free value, so it is config and it is swept; ⚠️ **its sweep is not a
  plateau (1.35x over 10-75 deg) and must not be quoted as one** — what it says is that it is not the
  radius rule's 10x, and that `one-sided` climbing 4 → 17 is the rule announcing its own failure.
  ⚠️ **Deliberately a SECOND value from `carriageway_survey.width_bounds.pair_bearing_tolerance_deg`,
  which carries the same number**: that block is optional, so a region with no width survey would
  lose its centre lines to a width setting. Do not "de-duplicate" them.
  🔴 **An angle-free rule — mutual offside-kerb burial — is BUILT, MEASURED and REJECTED, so do not
  re-propose it**: same population, no angle, but its share bar runs 62 → 4 pairs over 0.10 → 1.00
  with nothing published behind 0.5, which is trading a swept knob for an unswept one.
  ⚠️ **The plan-bounds reject is a BOUND, not a reading, and the tests are expected to survive
  deleting it** — the two mutations that must fail are the anti-parallel test and mutuality.
  ⚠️ **Its scalar `_Ribbon` fields are measured, not preferred**: the same filter on `(2,)` arrays
  with `.any()` — the form `_Occluders.cover` uses on a bucketed handful — is 395 ms against 34 over
  387,122 candidate pairs, so that test is deliberately written twice. Do not "de-duplicate" it.
  ⚠️ **A centre line moves no geometry, and that is the inertness proof** — `roads.glb`'s positions,
  normals, colours, indices and `TEXCOORD_0` byte-identical, `TEXCOORD_1.y` byte-identical, and
  `TEXCOORD_1.x` differing **in the centre field only**, asserted field by field; `roadsurface.json`,
  `arrows.glb`, `roadmarks.glb`, `boxjunctions.glb` and `clearance.json` byte-identical.
  ⚠️ **The evidence is a frame and the cache lies** — every counter read correctly while the road was
  blank — so delete `game/.godot/imported/roads.glb-*` and re-import before *each* side, and shoot
  each side twice and `cmp` them. Numbers in `Q117`.
- 🔴 **`_Edge.is_stub`, `_stub_clusters`, `_cap_ring`'s corner rule, or `junction_trim_max_fraction`:
  paste `roadsurface.json`'s `clusters` block (87 stubs / 54 clusters / 139 nodes) and `caps` count
  before and after, `tools/box_extent.py` PER BOX, `tools/cap_pavement.py`'s two pooled lines, and
  the `carriageway[]` / `offset_m` / `trim_m` byte-identity** (`P3-31`, `Q104`). A junction between
  two dual carriageways is several nodes joined by stubs — links clamped at both ends — and since
  `P3-31` one hull caps the cluster; a stub lends **no corner** and keeps its ribbon under the cap.
  ⚠️ **No new knob**: a stub is the two existing trim decisions read together, and the cluster count
  is reachable at zero by loosening the fraction (`test_a_looser_ceiling_dissolves_the_cluster`), so
  mutation-check it rather than reading 54. 🔴 **A stub across a seam joins NOTHING** — the neighbour
  never sees it and caps the far node alone, so clustering it draws that junction twice or not at
  all; `_stub_clusters` takes `owned` for that reason and `test_a_stub_across_the_seam_joins_nothing`
  is the ratchet. ⚠️ **A hull can only grow, so price it**: `cap_pavement.py` reads HyD's Pavement
  Polygon in THREE states, because HKCEC has no HyD carriageway under it at all and a two-state
  reading prices the change against a publisher's silence; quote past-kerb and unsurveyed apart, at
  one `--cell-m` and `--near-m`. ⚠️ **The cap's fan and the stub ribbon under it disagree in height**
  (max 0.199 m; the per-node caps read 0.255) — the old cap-over-ribbon overlap, not a new one, so
  quote both sides. ⚠️ **The evidence is a frame and the first after-shot may not repeat** — HKCEC
  needed three; shoot until a hash repeats. 🔴 **And `_through_corridors` / `_far_section`: paste
  `corridors` (68) and the NEW-asphalt price by HyD class, never `cap_pavement.py`'s quad area alone**
  — corridors overlap the ribbons and the cluster cap they straighten, so 20,000 m² of quad is
  745 m² of asphalt. RN2 splays each carriageway into its node; the corridor is the straight quad
  between two arms' far sections and is **unioned, never hulled** into the cap, or it sweeps the
  pavement corner `hull` exists to leave. ⚠️ **The kerb-line corner rule is REFUTED, do not
  re-propose it**: it found the HKCEC wedge from two far-side rails extended across the junction.
  🚫 **`_paint_flanks`, `_add_paint_stations` and the `paint` block are DELETED (`P3-35e`, `Q133`).**
  🔴 **A region-less bundle now draws NOTHING under a box that overhangs its ribbon**, so "leave
  `carriageway_region:` out and every file hashes as it did" is no longer true of `roadsurface.json`
  (it lost `paint`) or of a region-less city with box junctions. What the flanks taught is in `Q104`.
  ⚠️ `paint_clearance.py --layer boxjunctions` is still the check that box paint stands on the road.
  Numbers in `Q104`.
- 🔴 **The drawn ribbon is `[offset − half, offset + half]` PER STATION, never `±half` about the
  centreline (`Q106`, `Q107`).** Read both from `city.json`'s `carriageway[]` — `half_width_m` and
  `offset_m`, via `overhang.half_width_at` and `overhang.offset_at` — and pass the offset to
  `overhang.cross_section`. 🔴 **`half_width_m` is half the distance BETWEEN the rails and not a
  half-width about anything**: since `Q107` the two rails are cut to the deck independently, so
  off-grade the ribbon is asymmetric and a half-width alone does not say where the road is.
  ⚠️ **Four tools got this wrong at once and failed in OPPOSITE directions** — `overhang.py` drops a
  sample with no road under it, `deck_margin.py` keeps every one — and 5.6% against 10.7% was taken
  for a model difference. ⚠️ **A tool that already has an `offset_m`
  meaning a CELL's distance from the centreline must ADD the drawn offset, never replace it** —
  `carriageway_occupancy.py` and `ground_clearance.py` both do, because `Section.is_inside` and "the
  centreline cell" are about the published centreline. ⚠️ **"0.0 on all 737 level-0 edges" EXPIRED
  at `P3-33c`**: a level-0 ribbon's rails are its territory, and 288 of 734 are drawn more than 1 m
  off their centreline. `arrows.py` read `±half` until `Q130` put its arrows 1.5 m out of the painted
  lanes; ✅ **`Ribbon.kerb_target` — signs, lamps — is FIXED since `P3-35d` (`Q133`)**: it and `past_kerb_m`
  read the ROAD's running kerb line (`pipeline/drawnroad.py::_kerbs`) and never the centreline.
  🔴 **The kerb is `carriageway_region.json`'s dense stations, each side read only where it ENDED AT
  A KERB and the straight line between — never the ribbon's rail (a SHARE, `Q57`) and never
  `roadsurface.json`'s per-vertex `corridor_*`, which was BUILT, MEASURED and WITHDRAWN**: a straight
  street's two vertices are both at junctions, and graded against where iB1000's surveyed lamp posts
  stand it reads 24.2% of Wan Chai's as in the road against 21.8% for the `±half` it replaced; the
  running kerb line reads 13.3%. ⚠️ **The grader is a scratch script and is owed as a tool.** ✅ `fence._dress` centres its row on the ribbon's `offset_m` since `P3-35d`; 🔴 **the sign is
  load-bearing there** — nearside is `-across` at a start mouth and `+across` at an end mouth — and
  `test_the_row_stands_across_the_ribbon_at_both_mouths` is the ratchet; mutation-check both ways.
  ✅ **`railings.ribbons` came through the same door at `P3-35d` (4)**: an outset past `kerb_at`'s
  two kerbs, side and facing asked about the road's MIDDLE — the `railings` rule has it. Numbers in `Q106`, `Q107`, `Q130`, `Q133`.
- 🔴 **`surface.py` cuts the off-grade ribbon to its deck, per station and per side (`Q107`) —
  `_clamped_rails` is the one place, and it may only CUT.** `upper = min(shift + half, left_rim)`,
  `lower = max(shift − half, −right_rim)`, with the rims from `roadgraph.json`'s `deck_rim_m`.
  A deck wider than the paint changes nothing, because extending would invent carriageway (`Q54`)
  and `Q105` licensed a deck rim as **paint and not a width** — so ⚠️ **`width_m` must not move
  here**. ⚠️ **Absence of a deck is `inf`, never 0.0**: that is what makes the whole at-grade
  network inert by arithmetic rather than by a branch, and a 0.0 default collapses 737 edges to
  nothing. 🔴 **"Absent" is not the only way a deck ends, and `_deck_rims` discards the rim
  wherever `on_structure` is `False` (`Q113`)** — a road resting on the ground is as deckless as one
  nobody measured. Where a ramp descends to grade the walk still finds a sliver of slab: `e208`
  FLEMING ROAD's last four vertices returned a rim of **0.100**, `carriageway.DECK_ACROSS_M`
  exactly — the smallest non-zero reach that walk can produce — and the clamp cut the ribbon
  **5.60 → 3.15 m**, which the markings shader painted as two **1.57 m** lanes. **Do not treat a
  small rim as a narrow deck**, and do not remove the `on_structure` gate: **20 vertices over 6
  edges** carry a rim it discards and **4** of those ribbons move, which are two different counts —
  mutation-check it rather than reading either. ⚠️ **`on_structure` is not only
  this gate** — `Q23` draws an on-structure edge at its authored width instead of the playability
  floor — so a test fixture that sets it moves the widening too. ⚠️ **A station whose rails cross keeps the ribbon it had and is counted** — 0 in this
  region and *reachable*, so mutation-check it rather than reading its value. ⚠️ **Prove inertness
  by neutralising the clamp and rebuilding**: it must reproduce **32,177 triangles / 39,078
  vertices**, the pre-`Q107` bundle exactly. 🔴 **The evidence is a frame and the cache will lie to
  you** — delete `game/.godot/imported/roads.glb-*` and re-import before *each* shot, or the pair
  comes back identical over a 2.16 m change; and aim at `e337`, not `e208`, whose cut is under
  0.5 m. Numbers in `Q107`.
- Road-surface, deck-height or ground changes: also `tools/deck_error.py`, `tools/overhang.py`,
  `tools/ground_clearance.py` and `tools/carriageway_occupancy.py`, by hand after a build. They grade
  the *shipped* bundle and share no **method** with the pipeline — `check.sh` does not require a built
  region and should not start requiring one. ⚠️ **"No code" was true until 2026-09-02 and is now one
  step weaker**: `ground_clearance.py` imports `BUMPER_LOW_M`/`BUMPER_HIGH_M` from
  `pipeline.clearance`, deliberately, because the band it publishes is the *gap* in that instrument's
  reach and must move when it does. A shared **bound** is not a shared reading; do not let a second
  import in on this precedent. Moving the road moves what `ground_clearance.py`
  measures, so it is not only a ground check — and **widening, building footprints and landmark
  placement move `carriageway_occupancy.py`'s answer** without touching the road at all, so that one
  is owed for those too. It gates per *edge*, because `RoadGraph` routes on edges. ⚠️ It **fails
  today**; read the exit code rather than the table, and see `PROGRESS.md` for what it is failing on.
