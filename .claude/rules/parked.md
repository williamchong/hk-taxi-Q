---
paths:
  - "etl/pipeline/parked.py"
  - "etl/pipeline/config_blocks/parked.py"
  - "etl/tests/test_parked.py"
  - "etl/tests/test_make_parked.py"
  - "tools/make_parked.py"
  - "game/scripts/city/parked_layer.gd"
  - "game/scripts/city/parked_roster.gd"
  - "game/scripts/city/parked_profile.gd"
  - "game/scripts/fares/near_miss.gd"
  - "game/tools/verify_parked.gd"
  - "game/tuning/parked.{tres,md}"
---

# The parked roster and the near miss — before marking work done

`P3-71`–`P3-73`, `P3-2a`, `Q161`. The stationary vehicles the streets carry, in place of moving
traffic, and the bonus for threading them.

- **`pipeline/parked.py`, the `parked` config block, or any parked-vehicle change: paste
  `parked.json`'s `by_kind`, `by_source`, `by_hours`, `refused` (the whole table, by source and
  rule), `bays_on_restriction`, `published_in_lane` and `narrowest_lane_room_m`, before and
  after** — `tools/battery.py parked` runs it. 🔴 **The partition closes**: `candidates` =
  `placed` + every count under `refused`; a rule that drops a candidate without counting it ships
  a hole nobody can see.
- 🔴 **A published bay or stop stands where the publisher put it; only what the stage INVENTS
  takes the invented bars.** `junction_m` and the lane-room bar (`lane_width_m`) refuse the fill,
  a frontage and a taxi queue — never a bay or a bus stop. A bay inside the junction trim is still
  refused (the trim is geometry); a bay in a restriction run is COUNTED (`bays_on_restriction`,
  TD's two layers disagreeing) and placed. Do not "fix" `published_in_lane` by refusing bays —
  a bus at its stop is in the lane in Hong Kong too.
- 🔴 **The side convention is `kerbside.py`'s trap and renders plausibly when wrong.** A vehicle
  facing against its kerb's flow is a perfectly drawn vehicle. `_flow_heading` reads
  `Snap.offset_m`'s sign (`+` nearside) and nothing else; `test_parked.py` stands a car on each
  side of a two-way fixture edge and checks the two face apart, and a one-way street's two kerbs
  face the same way. A motorcycle stands nose to the kerb (`across`), its LENGTH off the road.
- 🔴 **An invented kerb is a slow street's** (`parked.slow_streets`, the user's drive 2026-10-11:
  "cars dont park in fast lanes"): the fill draws no slot and a frontage is refused `FAST_STREET`
  on a `main` edge, over 50 km/h, with a bus lane, unclassified, under `min_lanes` (2), on a
  structure, or on the OFFSIDE of a one-way street (the fast lane — `allows_side`). A bay, a stop
  and a stand are
  the publisher's and are never gated by it. Do not loosen it to fill a quiet main road.
- 🔴 **A lay-by is the kerb's own widening** (`laybys:`, the user's drive 2026-10-11): a run of
  `kerb_left_m` / `kerb_right_m` 1.8–4.0 m proud of the edge's median for 8–90 m inside the trim,
  stood on ANY street and either kerb with no setback and no lane bar. Past `max_bulge_m` it is a
  flare or a slip road; do not raise it to catch one. `layby_runs` and `layby_m` are the counters.
- 🔴 **The fill is a share, never a licence** (`Q161`). 57 of Wan Chai's 90 km of level-0 kerb
  carries no published restriction; `fill.share` of the slots is kept on a draw seeded by the
  slot, so a rebuild places the same cars. A single yellow joins the fill OUTSIDE
  `single_yellow_hours` only, and never for a kind with hours of its own (a van by day). Do not
  raise `share` to "make the street busy": the bays are the busy part.
- 🔴 **Hours are the rig's `time_of_day` read against `parked.tres`'s clock, never a second clock**
  (`Q160`). `in_window` is spelled twice on purpose — `parked.py` writes the windows,
  `parked_roster.gd` reads them — and `verify_parked.gd`'s table holds the GDScript side from both
  sides of every bar; `test_parked.py` holds the Python side. A change to one is made twice.
- 🔴 **A cell rebuilds only while HIDDEN** (`ParkedLayer._process`): past `range_m` from the
  camera, when the hour moved or `reroll_s` passed for a cell with a chance under 1. A vehicle
  appearing in view is a pop; do not "fix" a stale street by rebuilding visible cells.
- 🔴 **The library is AUTHORED and committed** (`assets/authored/vehicles/parked.glb`, CC BY-SA):
  `tools/make_parked.py` writes it, `test_make_parked.py` pins the bytes, and `parked.vehicles:`
  in the yaml must match each kind's extent within 5 cm — the ETL places by the numbers and the
  engine draws the mesh. A proportion change is `python tools/make_parked.py`, a test run, and
  a commit of the `.glb`. The `.import` sidecar is committed beside it. ⚠️ The rear lens is
  `taillamp_{side}_brake` (the brake circuit) and the head lens `headlamp_{side}`: the moving cars
  light them through `INSTANCE_CUSTOM.a` and a parked car writes 0 — dark. The indicator lenses
  are the taxi's `indicator_{side}` / `taillamp_{side}_indicator` (`P3-3f2`). A placement whose
  source is in `parked.tres`' `hazard_sources` writes both indicator bits (`datum_of`, held by
  `verify_parked`; its `hazards on:` line is the share) — by source, never by kind.
- 🔴 **A roster taxi is the player's body, never a loft of its own** (`P3-85`, `Q200`):
  `make_parked.Taxi` builds each licence from `make_vehicle.taxi_parts`, the door shut, the
  mirrors tucked (`TAXI_MIRROR_REACH_M`), so a change to the player's taxi changes all three and
  owes `python tools/make_parked.py` and the `.glb`. The footprint is that body's, 4.575 m: do not
  put the real car's 4.7 back in `parked.vehicles:` — the stand's queue moves with it. The roof's
  white is found by part name (`glass_*`, `greenhouse`); a rename in `make_vehicle` fails the
  build, by design.
- **A lofted kind's die-cast detail is `Shape` fields, off by default** (`P3-85`): `nose_drop_m` /
  `tail_drop_m`, `hub_slots`, `bezels`, `shut_lines`, `rub_strip`, `wipers`, `doors_m` /
  `door_glass`, `window_bar`. 🔴 Everything stands inside the footprint, in the skin
  (`FLANK_PROUD_M`): a mirror on a stalk or a step past the flank widens the collider. ⚠️ A falling
  deck takes its waist down with it (`waist_y_at`); a drop that puts an arch's crown over the
  waist, or the deck under the lamps, is refused — lower the drop, do not move the guard. Doors are
  on `KERB_SIDE` and refused in a wheel arch. A new feature owes a lineup sheet before and after
  (`asset_viewer.tscn --lineup=20`, a forced reimport first) and the throttle route's `prims`.
- **The lorry is parked only** (`P3-85`, `Q200`): at TD's `Goods Vehicles` bays and as the second
  rank of the `office` frontage. 🔴 Do not add it to `traffic.tres` `kinds` by hand — that table is
  the census's (`signals.md`), the lorry's share of light goods is unmeasured, and a new kind there
  moves every seeded drive. Moving, it also owes a mass (`masses_kg`) and a horn file. ⚠️ A second
  kind in a frontage class's `kinds` is a second RANK, `pitch_m` behind the first: new candidates,
  each counted, the first rank's own places unmoved.
- 🔴 **A colour that means something is never a livery** (`Q167`, the user's rule 2026-10-13):
  the taxi, the bus and the tram carry no `livery`, and the minibus's palette is green and red
  only — the licence colours. `parked.tres`'s `liveries` is the palette; a kind's `Shape.livery`
  is which authored colour it repaints, and `verify_parked` fails a palette on a kind with no
  livery panel. Keep the private cars off saturated red: the player's taxi is the red car.
- 🔴 **A taxi's licence is the stands', never authored per region** (`Q183`): `taxi`, `taxi_nt`,
  `taxi_lantau` are three meshes of one kind, never a livery. A stand's taxi wears its category's
  shares (`licences.by_category`); every other taxi draws on the region's mix, which is every stand
  in the DISTRICTS (`District_EN`) the region's own stands lie in. Do not narrow it to the box
  (Sha Tin's holds three urban stands of 52), and do not hand-write a region's colour. Paste
  `parked.json`'s `taxi_licences`, `taxi_licence_districts`, `taxi_licence_stands` and `by_licence`
  for both regions. ⚠️ With only red resident the placements are byte-identical; a change that
  moves them moved the draw.
- ⚠️ **`verify_parked.gd` grades the join ONE way.** A library kind stood nowhere in a region
  (no taxi stand in Causeway Bay) is the data, printed as `info`; an entry naming no mesh fails.
  Do not swap in `GeneratedPlacements.check_join`, which fails the unstood kind.
- 🔴 **The near miss pays for DANGER, not proximity** (`near_miss.gd`, the user's call 2026-10-11:
  "should not trigger if we are just passing cars in nearby lane without real danger"). A pass
  pays only when the parked vehicle was IN THE PATH — inside the car's own width along its
  travel, within `near_miss_look_s` — no more than `near_miss_memory_s` before the car came
  alongside, and was then passed inside `near_miss_m` at or over `near_miss_min_kph` with no
  touch. `verify_fares.gd`'s `near miss:` block drives the SAME clearance twice, aimed and not,
  and the unaimed pass must pay nothing; every bar is held from both sides. The memory is
  measured to the tick the car comes alongside, not to the end of the pass — a bus is 12 m long.
  ⚠️ **Except the close call** (`Q161`, the user's call 2026-11-05, off the user's logged drive: 0.24 m
  at 130 kph in the next lane paid nothing): a pass inside `close_call_m` pays aimed or not, and
  `near_miss_m` went 0.6 → 0.9, so a lane-centred pass (~0.65 m) is inside the near-miss band and
  the path rule alone refuses it. A touch or a flight while alongside spoils any pass
  (`Track.spoiled`). Do not "restore consistency" by putting the path rule back on the close call.
  ⚠️ **Down a row, only the cars inside `near_miss_look_s` at the swerve pay** (2 of 6 at
  54 kph); the rest are a lane pass by the same rule. `verify_fares`'s row checks hold that, and
  that a second row past a gap pays again; dropping the in-path width test fails both (6 of 6,
  12 of 4).
- 🔴 **A moving car is the same detector on the closing speed** (`Q175`): an obstacle's optional
  `velocity`, a parked one's zero, so every parked row holds byte for byte. The look runs on the
  closing speed, a car pulling away is no threat, one drawn level that pulls clear is a fresh
  approach, and `near_miss_min_kph` stays on the taxi's own speed. `verify_fares`' `near miss moving:`
  holds it; each of the three is a named mutation. 🚫 A lane pass still pays nothing.
- 🔴 **The moving traffic reads this layer** (`P3-3f1`): `TrafficSystem` indexes every placement
  by its `edge` (`edge_of`, `obstacle_of`, `source_of`) and asks `is_standing` each tick. A change
  to `edge`, the footprint or what stands when moves the traffic too: run `tools/check.sh` and paste
  `verify_traffic`'s `parked:` table. ⚠️ The table is a reading of the roster in the LANES — 759 of
  1,081 in lane 0 on 2026-10-30 — and the fill's lane-room bar counts fill rows only, so a fill
  car across from a published bay can pinch a back street below a car's width (a `P3-71` finding).
- ⚠️ **The car's extent comes off its meshes** (`FareSystem._ready`: `MeshContract.bounds` in
  the car's frame) and `verify_fares` hands in a Crown Comfort's; a car of no width is an inert
  detector, named. `NearMiss` refuses a close-call band not under the near-miss band.
- ⚠️ A parked-vehicle change owes a drive by day and at night (`--time-of-day=0.9`): the vans
  gone, the single-yellow fill in, the buses re-rolled past 400 m. The frame time with the
  colliders resident is owed (`P4-5`).
- **`masses_kg` is the push's** (`Q180`): kerb weight per kind, cited in `parked.md`, read by
  `TrafficSystem` and `TramSystem`. The bus carries one since `P3-78` (it moves on its routes). 🔴 A parked vehicle is NOT pushed in v1 (a scope cut); a kind
  that moves needs a mass, which `verify_traffic` checks.
- **A tram no longer stands, and nothing stands in a tram's path** (`P3-4`, `Q176`): `on_tram_line` in
  `refused`, published sources included (3 stops on Wan Chai, 2 laybys on Causeway Bay), by
  `tramway.lines.tram_path_m`. Do not exempt a published bay: the tram drives through it. `parked` now
  runs after `tramlines`.
- **Public transport's windows light at night** (`Q177`): `Shape.cabin` is `MARKER_CABIN` on the bus and
  the tram and `MARKER_CABIN_DIM` on the minibus. The coach stays dark because it only ever parks; do not
  "complete the set". A new cabin marker is four places: `make_vehicle.py`, the importer's `VEHICLE`,
  the shader and `verify_parked`'s `LIT_CABINS`. A shader change owes a render and `grep -i "shader error"`.
- 🔴 **No bus stands at a stop; a terminus is filled by the timetable** (`Q187`, reversing
  `Q182`'s parked bus): `terminals` queues `ceil(departures × layover_min / 60)` buses (≤ `queue`)
  behind each bus route's first stop, a rank per run of hours (`hour_windows`), re-snapped within
  `max_snap_m` where `busroutes` left it. Paste `terminals_read`, `terminal_routes`,
  `terminals_resnapped`, `terminals_unsnapped`, `terminal_off_edge`, `terminal_windows` for both
  regions. A rank off the edge's end is counted under `terminal`'s `at_junction` AND in
  `candidates`. ⚠️ The partition reads `candidates` − `placed` − refused = −99 (Wan Chai) and −16
  (Causeway Bay) at HEAD before `Q187` too: a pre-existing hole, not this block's.
