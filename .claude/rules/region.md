---
paths:
  - "etl/pipeline/region.py"
  - "etl/pipeline/surface_region.py"
  - "etl/pipeline/surface.py"
  - "etl/pipeline/drawnroad.py"
  - "tools/carriageway_region.py"
  - "etl/tests/test_region.py"
  - "etl/tests/test_surface_region.py"
  - "etl/tests/test_surface_on_region.py"
  - "etl/tests/test_carriageway_region.py"
  - "etl/tests/test_drawnroad.py"
---

# The level-0 carriageway as a region — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **`tools/carriageway_region.py`, or anything that builds the level-0 carriageway as a REGION
  (`Q129`, `P3-33`): paste its four tables for `wan_chai` AND `causeway_bay`** — R's composition,
  the span against the ray survey, the end-pair table **both ways** (every station and mid-block),
  and the orphan line. 🔴 **The finding is the END-PAIR table and the span agreement is not**: where
  R is HyD's, the ray survey's third publisher is that same polygon's boundary, so |p50| 0.04 m says
  the partition does not move a kerb and nothing more. ⚠️ **Quote the mid-block column** — a station
  inside the junction guard ends in a share by geometry — and quote the ray-measured row beside it
  as the control (84.3% / 93.5% kerb|kerb against 19.8% / 25.6% on `authored`).
  🔴 **Where HyD is silent the rule is RAILS, not faces, and that is measured**: the line publishers'
  kerbs do not close (24 faces, 0.3% of the length, against 13.5% silent — GLOUCESTER ROAD's main
  carriageway and all of HKCEC). Do not re-propose polygonising them. ⚠️ **R is cut to the region's
  own rectangle**: unclipped, asphalt the graph does not reach is handed to the nearest edge (6.8%
  orphan, one piece 228 m from its owner). ⚠️ **`silent_m[0]` is the only place R is not read from a
  publisher** — the graph's `width_m`, 2.0% / 2.2% of the length — so a rise there is the invented
  width coming back. 🔴 **Its normal is RIGHT of travel like `carriageway._stations`, but here the
  sign is load-bearing**: every printed figure is a sum or a sorted pair, so the first build had the
  sides swapped with no table moved. `test_left_is_left_of_travel` is the ratchet; mutation-check it.
  ⚠️ **A broken Voronoi cell is REPAIRED, never dropped** (1 of 45,086 on Wan Chai) — a dropped cell
  is asphalt with no owner — and the cells are not a valid coverage, so `coverage_union_all` is not
  the fix. ⚠️ `shapely>=2.1` is a real floor: `voronoi_polygons(ordered=True)` is what maps a cell
  to its owner. 🚫 **A territory span is a SHARE and never a `width_m`** (`Q57`). It grades rather
  than checks and exits 0. Numbers in `Q129`.
  🔴 **`pipeline/region.py` is its SECOND implementation and the duplication is deliberate**
  (`Q95`'s precedent): paste the stage's three log lines and the tool's `|stage - tool|` line, both
  regions. They share I/O and no method, agree to **0.025 / 0.014 m²** per territory, and a
  divergence is a finding — the first one was the stage casting a rail from every run cut at the
  rectangle. ⚠️ **Do not "fix" it by importing one into the other.** 🔴 **Silence is asked of the
  publisher's UNION, never of the clipped one, and with `intersects`, never `contains`**: a cut run
  ends ON the clip line and a station can stand ON HyD's own edge, and either read as silent casts a
  rail from a road HyD drew. 🔴 **The seam: `foreign` territories are PUBLISHED and
  foreign runs cast rails**, because the asphalt beside a neighbour's run inside this rectangle is
  this region's to draw — dropping them is a hole neither build draws. (The run's own RIBBON stays
  its owner's; the bullet below has the rule as `P3-33c` settled it.) 🔴 **Extents are published
  at dense STATIONS (`station_m`), never at the published vertices alone**: a straight street is two
  vertices, both at nodes, where a territory pinches to a wedge, so schema 1 described a sliver the
  length of the block. `vertex_station` indexes `roadgraph.json`'s own vertices, repeats included,
  into them; ⚠️ an END station is measured half a sample in from its node, because at the node it
  reads zero on a good road. ⚠️ **The stage's `ends` block runs over EVERY station and is not
  `Q129`'s mid-block table** — never quote one for the other. ⚠️ **No longer inert**: `surface.py` has read it
  since `P3-33c`, so a change here is a change to the drawn road and owes the bullet below. What
  still holds is the region-less path — leave `carriageway_region:` out and every published file
  must hash as it did, only `city.json`'s `generated_utc` differing.
  🔴 **`test_surface.py`'s 132 tests drive that region-less path, which NO region ships; the path that
  ships is `tests/test_surface_on_region.py`** (`P3-35c`, `Q133`), whose `regionville` runs the real
  `region.build` and hands its file to `surface`. ⚠️ **Assert on the MESH there, never on
  `carriageway[]` alone**: with `_shape`'s `exact=` switched off every manifest assertion still
  passes and only the mesh read fails. ⚠️ The surface `region:` log line ends in two fallback
  counters — `territory_mismatched_edges` **must be 0** (a `carriageway_region.json` built off
  another graph; the edge draws the invented width whole) and `territory_missing_edges` is reported.
- 🔴 **`surface_region.py`, `_with_territory_stations`, `_stations_kept`, `_clamped_rails(exact=)`,
  `_publish_territory_table`, `_LANE_SPAN_PERCENTILE`, `carriageway_region.rail_tolerance_m`, or the
  level-0 floors (`P3-33c`, `Q129`): paste the surface stage's `region:` line and its triangle count,
  `lane_paint.py --sweep`, `box_extent.py` per box, `paint_clearance.py`, the fence line, the
  roadmarks `by marking` line, and the throttle route's `draws` — before AND after, the before from
  a detached worktree — and shoot the recorded cameras twice a side** (`hkcec`
  `--camera=235,45,265 --look=235,0,195`, `street` `--camera=270,5.5,691 --look=30,4.5,719`).
  A level-0 ribbon's rails ARE its territory (`Q107`'s clamp, `exact`) and everything else of R is
  `areas`; **the hull caps, stub clusters, through corridors and paint flanks do not run at level 0
  while a region is built**, so their bullets above describe off-grade and region-less bundles only
  until `P3-33d` deletes them.
  🔴 **A territory is a SHARE and never a corridor or a carriageway (`Q57`), and three readers got
  that wrong in one afternoon.** `clearance` fenced GLOUCESTER ROAD `e390` off a 25 m carriageway
  (fence 14 → 25); `roadmarks` refused the double white lines that lie ON a shared boundary (91 →
  66); the shader cut a 1.4 m share into three lanes. So: `clearance` and `roadmarks` read
  `corridor_*` (kerb to kerb, through every share) where a row carries it, and the PAINTED lane
  count is `lanes_painted` — the territory as a one-sided CEILING at the span's p10 clear of the
  mouths, never a source, the graph's `lanes` untouched. **Any new reader of `half_width_m` at level
  0 owes the question "do I mean the share or the road?"**
  🔴 **An inserted station's rim is ASSIGNED its measured extent; `min` is for a DECK rim only.**
  `min(lerp, measured)` lets the lerp between the two end WEDGES win everywhere and drew `e709`
  1.2 m wide in a 6.5 m territory with every counter closing.
  🔴 **A rail BRIDGES a side-street mouth along the kerb line (`surface_region.bridged`) and that is
  not smoothing.** A territory bulges into every opening as far as the bisector with the side
  street — 80 openings on 58 edges by over 0.5 m, FLEMING ROAD `e264` by 11.63 m — so a rail that
  follows it makes a straight road broaden and shrink, which is how it was found: from the seat. A
  share run between two kerbed stations is held to the line between them, `min` only; ⚠️ a share
  run reaching an END of the edge is left alone (a shared carriageway has no second kerb), and ⚠️
  `carriageway_region.json` is never rewritten — it is the measurement.
  🔴 **`opened`, `flare_m`, `_kerb_lines`, `_draw_area_kerb` or `rail_opening_m`: measure the wobble
  INSIDE THE DRAWN RIBBONS before and after** (sides and metres standing > 0.75 m off their own 20 m
  median, outward and inward apart — `Q129` has the script's shape), with `lane_paint`, the triangle
  count, the fence and `by marking` lines. **Three pieces, and they are not interchangeable**: a BAY
  mid-block is `opened` away (a morphological opening — it never widens, leaves a taper alone, and a
  bump a window long is a carriageway); a FLARE near a node is never filtered, it is where the ribbon
  should not have started, so `flare_m` reads the junction trim off the territory; and an AREA carries
  its own kerb, or every corner is kerbless and every bay loses the kerb it had.
  🔴 **`opened`'s four guards each come from a build that was wrong — do not "simplify" any away**:
  a run is what stands out by more than `kerb_width_m` (whole, it moved 33,400 m² to area; cut at a
  hair, jitter merges every bump into one run touching both ends); only stations clear of the mouths
  take part (an 11 m edge is one bump between its wedges — `e0` collapsed and `verify_road_graph`
  caught it); a bay needs a quarter-window of kept rail either side; and a side let go of its kerb
  clears its kerb flag, because the strip is drawn ALONG THE RAIL. 🔴 **The area kerb excludes every
  stretch within `kerb_width_m` of a ribbon's own kerbed rail** — rails are simplified, so a sliver
  of area lies beside almost every one and the ring was 27.4 km of kerb drawn twice. ⚠️ Its codec
  value is a one-lane one-way KERB, never a bare class: "no lanes" means a junction cap. 🚫 The INWARD
  wobble (islands, an intruding link) is left on purpose — closing it is the widening `opened` refuses.
  🔴 **`rail_tolerance_m` is triangles, not tidiness**: every station is two carriageway triangles
  and four kerb strips — 226,824 unpruned against 79,790 — and ⚠️ **the areas are triangulated WHOLE,
  never per owner**, which cost 45k more for nothing.
  🔴 **The seam: a run's RIBBON is its owner's, whole (`Q116`); every other square metre of R is
  drawn by the region whose rectangle holds it**, so the neighbour's ribbons are subtracted from the
  areas like owned ones. ⚠️ `carriageway[]` at a vertex inside a junction trim publishes the width
  AT THE TRIM — at the node a territory is a wedge. ⚠️ **`clearance.py` and
  `carriageway_occupancy.py` walk the same corridor again since `P3-33e`** — kerb to kerb, tapered
  between vertices, off `city.json`'s `corridor_half_width_m` AND `corridor_offset_m` — and the
  grader's AREA half stays on the ribbon, because corridors overlap and ribbons tile. 🔴 A new
  reader of the corridor takes the pair (`_lib.ribbon.corridors`), never the half-width alone: it
  sits 0.91 m off the centreline at p50. ⚠️ A change to where R meets the rectangle owes
  `tools/join_seam.py`'s carriageway line, 0.00 m today. ⚠️ Open and known:
  `lane_paint` 79 edges under 3.00 m since the rail filter (the mouths, and one-lane shares that paint no line),
  `paint_clearance` `deeper than` 7 on boxes. Numbers in `Q129`.
- 🔴 **`region._closed`, `islands_of`, `_is_island`, `_through`, the across refusal in `rails`,
  `carriageway_region.seam_m`, or `surface_region.island_tops` / `island_rings` (`Q131`): paste the
  region stage's `R:`, `seams:` and `islands:` lines and the tool's `|stage - tool|` line, both
  regions, before AND after — then the whole `P3-33c` battery in the bullet above, the fence line and
  `reachability.py --refuse`.** A kerb IN the road is not the road's edge, and three rules say so.
  🔴 **`seam_m` sits on a swept plateau (0.05-0.15 m, 5-9 m² on Wan Chai) and 0.25 is past it** — one
  8.4 m² piece, then 161 m² at 0.40. It closes HyD's tiles, never a real gap; do not raise it to
  clear a pinch. 🔴 **An island has NO knob of its own and an area cap is BUILT, SWEPT and DROPPED —
  do not re-propose one**: areas run continuously from 1 m² to a city block, and 40 m² let Causeway
  Bay's 24 m platform strips through. It is shorter than `rail_opening_m` and no wider than
  `lane_width_m`, so ⚠️ **moving either of those moves which rings are islands**. 🔴 **An extent is
  read through an island ONLY where the ray comes out in its own territory** — a median's nose has
  the other carriageway beyond it — and `test_an_island_with_another_carriageway_behind_it_stays_a_kerb`
  is the ratchet; mutation-check it. ⚠️ **`island_stations` is the counter that can fail** (150 / 70):
  zero is every refuge a wedge across its lane again. ⚠️ **The corridor (`left_kerb_m` /
  `right_kerb_m`) still STOPS at an island, on purpose** (`Q57`): a car does not drive through one.
  🔴 **The across refusal is per STATION and declares no angle** — a hit is refused where its line
  reaches this centreline nearer, along the road, than the hit stands off it — and ⚠️ its big effect
  is not the pinch: a stub street with no kerb lines had been reading the MAIN road's kerb across
  its own mouth. Refused, that side is unanswered, so **`silent_m[0]` rises (926 → 944 m) and that
  IS the invented width**, and the fence gained `e315` and `e744`. 🔴 **A ribbon now runs UNDER an
  island**, so `surface_region` rings every island whole (riser only — the top covers the lip) and
  tops it; a reader that paints on a ribbon can now be under a slab, which is `paint_clearance`'s
  `on kerb` column and not its gate. ⚠️ **The tool's closing must stay a PAIRWISE union**:
  `unary_union` over the slivers filled HyD's holes, +9,010 m², with no error. ⚠️ The spike count in
  `Q131` is a scratch heuristic and is not monotone in anything; it found the classes and grades no
  fix. 🔴 **The width bar is WAIVED for a ring a centreline runs through** (`e785`, `e124`): "a wide
  island displaces a lane" supposes the road is beside it, and with the centreline inside the same
  road is on both sides. The LENGTH bar is not waived and is what keeps out the city blocks a
  centreline also crosses; two tests, mutation-check both directions. The tool asks it as a
  predicate where the stage measures a length — do not align them. ⚠️ Open: single stations where
  HyD's polygon touches the centreline at a node (`e37`; `e426` and `e125` are inside the junction
  trim and never drawn) — ⚠️ **not `Q19`**, which refuted one centreline shift for edges with a
  building in the corridor and is no rule that a centreline cannot move; and 🔴 the shader's two-way
  centre line, an invented `RM1001` that follows the rails and so zigzags and breaks. Numbers in
  `Q131`.
