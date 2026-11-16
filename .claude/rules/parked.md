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

`P3-71`–`P3-73`, `P3-2a`, `Q161`.

## The ETL stage — `pipeline/parked.py`, the `parked` block

`tools/battery.py parked --region <r> --before <checkout root>` (`parked.json`'s `by_kind`,
`by_source`, `by_hours`, `refused`, `bays_on_restriction`, `published_in_lane`,
`narrowest_lane_room_m`), and a drive by day and at `--time-of-day=0.9`. The frame time with the
colliders resident is owed (`P4-5`).

- **The partition should close**: `candidates` = `placed` + every count under `refused`. It reads
  −99 (Wan Chai) and −16 (Causeway Bay) since before `Q187`: an open hole; do not widen it.
- **Only what the stage INVENTS takes the invented bars**: `junction_m` and the lane-room bar
  refuse the fill, a frontage and a taxi queue, never a published bay or bus stop. A bay inside
  the junction trim is refused (geometry); one in a restriction run is placed and counted. Do not
  fix `published_in_lane` by refusing bays.
- **The side convention renders plausibly when wrong**: `_flow_heading` reads `Snap.offset_m`'s
  sign (`+` nearside) alone (`test_parked.py`). A motorcycle stands nose to the kerb (`across`).
- **An invented kerb is a slow street's** (`parked.slow_streets`, the user's call): no fill and no
  frontage (`FAST_STREET`) on a `main` edge, over 50 km/h, with a bus lane, unclassified, under
  `min_lanes`, on a structure, or the offside of a one-way street (`allows_side`). Do not loosen
  it to fill a quiet main road.
- **A lay-by is the kerb's own widening** (`laybys:`), stood on any street. Past `max_bulge_m` it
  is a flare or slip road; do not raise it. Counters `layby_runs`, `layby_m`.
- **The fill is a share** (`Q161`, `fill.share`, seeded by the slot); a single yellow joins
  outside `single_yellow_hours` only. Do not raise `share` to make a street busy.
- **Nothing stands in a tram's path** (`Q176`): `on_tram_line` in `refused`, published sources
  included (`tramway.lines.tram_path_m`). `parked` runs after `tramlines` and `busroutes`.
- **No bus stands at a stop; a terminus is filled by the timetable** (`Q187`): `terminals` queues
  `ceil(departures × layover_min / 60)` buses (≤ `queue`) behind each route's first stop, a rank
  per `hour_windows` run. Paste `terminals_read`, `terminal_routes`, `terminals_resnapped`,
  `terminals_unsnapped`, `terminal_off_edge`, `terminal_windows` for both regions.
- **A taxi's licence is the stands'** (`Q183`): `taxi`, `taxi_nt`, `taxi_lantau` are three meshes
  of one kind. A stand's taxi wears its category's shares; others draw on the mix of every stand
  in the DISTRICTS the region's stands lie in (not the box: Sha Tin's holds 3 urban stands of 52).
  Paste `taxi_licences`, `taxi_licence_districts`, `taxi_licence_stands`, `by_licence`. With only
  red resident the placements are byte-identical.
- **The lorry is parked only** (`Q200`): do not add it to `traffic.tres` `kinds` by hand (the
  census's table; moving, it also owes a mass and a horn file). A second kind in a frontage
  class's `kinds` is a second RANK, `pitch_m` behind the first.

## The library — `tools/make_parked.py`, `parked.glb`

A change is `python tools/make_parked.py`, `pytest tests/test_make_parked.py` (pins the bytes) and
a commit of the `.glb` with its `.import`; `parked.vehicles:` must match each kind's extent
within 5 cm. A new feature owes a lineup sheet before and after (`asset_viewer.tscn --lineup=20`,
a forced reimport first) and the throttle route's `prims`.

- **A roster taxi is the player's body** (`Q200`): built from `make_vehicle.taxi_parts`, so a change
  to the player's taxi owes this rebuild. Its footprint is 4.575 m; do not put 4.7 back in
  `parked.vehicles:`. The roof's white is found by part name (`glass_*`, `greenhouse`).
- **Everything stands inside the footprint, in the skin** (`FLANK_PROUD_M`, `SKIN_M`): a stalk
  mirror or a step widens the collider. Detail is `Shape` fields, off by default; a refused drop
  is answered by lowering the drop.
- **A relief is what the real vehicle carries** (`Q232`): `joints_m` (bus), `box_ribs_m` (lorry),
  `crease_y_m` (saloon, Alphard, van, minibus). Owes the lineup sheet, `verify_parked`'s `pressed
  kinds:` line, a Compatibility frame and `grep -i "shader error"` (`vehicle_body.md`).
- **Do not "complete the set"**: only the tram has folding door leaves and faceted lenses (`Q234`;
  `DOOR_LEAF_PROUD_M` 2.5 mm sits between `vehicle_ink`'s 1.5 mm touch and `SKIN_M`); the tram,
  coach and taxis carry no relief; the coach's cabin stays dark (`Q177`).
- The bus and tram are flat-sided (`Shape.slab_sided`), windows clear of every door. The tram's
  box is its collider, the raised pole in it (5.17 m); no cream band, hidden trucks (`Q166`).
- Lenses: `taillamp_{side}_brake`, `headlamp_{side}`, `indicator_{side}` /
  `taillamp_{side}_indicator`; a parked car writes 0. `parked.tres`' `hazard_sources` wink both
  indicators — by source, never by kind.
- A new cabin marker is four places: `make_vehicle.py`, the importer's `VEHICLE`, the shader,
  `verify_parked`'s `LIT_CABINS`. The sky's streak (`GLINT`) is on glass only.
- **A colour that means something is never a livery** (`Q167`): the taxi, bus and tram carry none;
  the minibus's palette is green and red only. Keep private cars off saturated red.

## The layer — `parked_layer.gd`, `parked_roster.gd`, `parked.tres`

- **Hours are the rig's `time_of_day` against `parked.tres`' clock** (`Q160`). `in_window` is
  spelled twice on purpose (`parked.py` writes, `parked_roster.gd` reads): change both.
- **A cell rebuilds only while HIDDEN**: its nearest edge past the camera's `far` plus
  `range_margin_m`. Do not fix a stale street by rebuilding visible cells.
- **No `visibility_range_end` on a parked batch** (`Q214`): Godot measures to the `MultiMesh` box's
  centre, so a whole 300 m cell popped at once ~190 m ahead.
- **`verify_parked.gd` grades the join one way**: a library kind stood nowhere is `info`; an entry
  naming no mesh fails. Do not swap in `GeneratedPlacements.check_join`.
- **The traffic reads this layer** (`edge_of`, `obstacle_of`, `source_of`, `is_standing`): a change
  to `edge`, the footprint or what stands owes `tools/check.sh` and `verify_traffic`'s `parked:`
  table. The lane-room bar counts fill rows only, so a fill car across from a published bay can
  pinch a back street.
- **`masses_kg`** (`Q180`): kerb weight per kind, cited in `parked.md`. A parked vehicle is NOT
  pushed (a scope cut); a kind that moves needs a mass (`verify_traffic`).

## The near miss — `near_miss.gd`, `skills.tres`

`verify_fares`' `near miss:` and `near miss moving:` blocks hold every bar from both sides.

- **It pays for DANGER, not proximity** (the user's call): the obstacle was in the car's own path
  (`near_miss_look_s`, `near_miss_memory_s`), then passed inside `near_miss_m` at or over
  `near_miss_min_kph` with no touch. A lane pass pays nothing.
- **Two exceptions, do not put the path rule back on either**: a pass inside `close_call_m` pays
  aimed or not (`Q161`), and an ONCOMING car inside `near_miss_m` pays (`Track.oncoming`).
- A touch or a flight while alongside spoils the pass (`Track.spoiled`).
- **A moving car is the same detector on the closing speed** (`Q175`); a parked obstacle's
  velocity is zero, so the parked rows hold byte for byte. `near_miss_min_kph` stays on the taxi's
  own speed.
- The car's extent comes off its meshes (`MeshContract.bounds`); a car of no width is an inert
  detector, refused. `NearMiss` refuses a close-call band not under the near-miss band.
