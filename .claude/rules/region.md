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

A level-0 ribbon's rails are its territory in `carriageway_region.json`; the rest of R is `areas`.
A territory is a share, never a `width_m`, a corridor or a carriageway (`Q57`). Any new reader of
`half_width_m` at level 0 owes the question "the share or the road?".

- **`tools/carriageway_region.py`, `pipeline/region.py`** (`Q129`): `tools/battery.py region
  --region <r> --before <root>`, both regions. Paste the tool's four tables (R's composition, span
  against the ray survey, the end-pair table both ways, the orphan line), the stage's three log
  lines and the tool's `|stage - tool|` line. The tool grades and exits 0.
  - The finding is the end-pair table's mid-block column, with the ray-measured row as control.
    The stage's `ends` block runs over every station and is not that table.
  - Stage and tool are deliberately duplicated (no shared method; they agree to 0.025 m² per
    territory). Do not import one into the other.
  - Measured shut: where HyD is silent the rule is rails, not faces. The line publishers' kerbs
    do not close (24 faces, 0.3% of the length, against 13.5% silent). No polygonising them.
  - R is cut to the region's rectangle. `silent_m[0]` is the only place R comes from the graph's
    `width_m`; a rise is the invented width returning.
  - The normal is right of travel and the sign is load-bearing (`test_left_is_left_of_travel`).
  - Silence is asked of the publisher's union, never the clipped one, with `intersects`.
  - A broken Voronoi cell is repaired, never dropped. `shapely>=2.1` is a real floor.
  - `foreign` territories are published and foreign runs cast rails.
  - Extents are published at dense stations (`station_m`), indexed by `vertex_station`. An end
    station is measured half a sample in from its node.
  - `test_surface.py` drives the region-less path, which no region ships;
    `test_surface_on_region.py` drives the shipped one — assert on the mesh there.
    `territory_mismatched_edges` in the surface `region:` line must be 0.
- **`surface_region.py`, `_with_territory_stations`, `_stations_kept`, `_clamped_rails(exact=)`,
  `_publish_territory_table`, `_LANE_SPAN_PERCENTILE`, `rail_tolerance_m`, the level-0 floors**:
  `tools/battery.py surface-region --region <r> --before <root>`, plus the surface stage's
  `region:` line and triangle count, the throttle route's `draws`, and two frames a side at
  `--camera=235,45,265 --look=235,0,195` and `--camera=270,5.5,691 --look=30,4.5,719`.
  - `clearance` and `roadmarks` read `corridor_*` (kerb to kerb through every share). A new
    corridor reader takes the pair (`_lib.ribbon.corridors`): half-width and offset. The painted
    count is `lanes_painted`: the territory as a one-sided ceiling, `lanes` untouched.
  - An inserted station's rim is assigned its measured extent; `min` is for a deck rim only.
  - `surface_region.bridged` holds a share run between two kerbed stations to the line between
    them (`min` only), because a territory bulges into every side-street mouth. A run reaching an
    end of the edge is left alone. `carriageway_region.json` is never rewritten.
  - `rail_tolerance_m` is triangles (226,824 unpruned against 79,790). Areas are triangulated
    whole, never per owner.
  - Seam (`Q116`): a run's ribbon is its owner's, whole; the rest of R is drawn by the region
    whose rectangle holds it. A change there owes `tools/join_seam.py`'s carriageway line.
  - `carriageway[]` at a vertex inside a junction trim publishes the width at the trim.
- **`opened`, `flare_m`, `_kerb_lines`, `_draw_area_kerb`, `rail_opening_m`**: measure the wobble
  inside the drawn ribbons before and after (metres standing > 0.75 m off their own 20 m median,
  outward and inward apart; script shape in `Q129`), with `lane_paint`, the triangle count, and
  the fence and `by marking` lines.
  - A mid-block bay is `opened` away (never widens); a flare near a node is trimmed (`flare_m`);
    an area carries its own kerb.
  - `opened`'s four guards each stand: a run stands out by more than `kerb_width_m`; only
    stations clear of the mouths take part; a bay needs a quarter-window of kept rail either
    side; a side let go of its kerb clears its kerb flag.
  - The area kerb excludes stretches within `kerb_width_m` of a ribbon's own kerbed rail. Its
    codec value is a one-lane one-way kerb, never "no lanes". The inward wobble is left.
- **`region._closed`, `islands_of`, `_through`, the across refusal in `rails`, `seam_m`,
  `surface_region.island_tops` / `island_rings`** (`Q131`): the region stage's `R:`, `seams:` and
  `islands:` lines and the `|stage - tool|` line, both regions, then the `surface-region` battery
  and `reachability.py --refuse`.
  - Measured shut: `seam_m` sits on a plateau (0.05–0.15 m; 161 m² at 0.40) and closes HyD's
    tiles only. It is not raised to clear a pinch.
  - Measured shut: no area cap for islands — areas run continuously from 1 m² to a city block,
    and 40 m² let 24 m platform strips through. An island is shorter than `rail_opening_m` and no
    wider than `lane_width_m`, so moving either moves which rings are islands.
  - An extent is read through an island only where the ray comes out in its own territory
    (`test_an_island_with_another_carriageway_behind_it_stays_a_kerb`). `island_stations` at zero
    is the failure. The corridor (`left_kerb_m` / `right_kerb_m`) still stops at an island.
  - The across refusal is per station with no angle; a refused side raises `silent_m[0]`.
  - A ribbon runs under an island; `surface_region` rings and tops each. Paint under a slab is
    `paint_clearance`'s `on kerb` column, not its gate.
  - The tool's closing stays a pairwise union (`unary_union` filled HyD's holes, +9,010 m²).
  - The width bar is waived for a ring a centreline runs through; the length bar is not. Stage
    and tool ask it differently; do not align them.
  - Open: single stations where HyD's polygon touches the centreline at a node (`e37`); the
    shader's invented two-way centre line follows the rails and zigzags.
