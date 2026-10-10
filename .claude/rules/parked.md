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
  on a `main` edge, over 50 km/h, with a bus lane, unclassified, under `min_lanes` (2) or on a
  structure. A bay, a stop and a stand are
  the publisher's and are never gated by it. Do not loosen it to fill a quiet main road.
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
  a commit of the `.glb`. The `.import` sidecar is committed beside it.
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
- ⚠️ **The car's extent comes off its meshes** (`FareSystem._ready`: `MeshContract.bounds` in
  the car's frame) and `verify_fares` hands in a Crown Comfort's; a car of no width is an inert
  detector, named. `NearMiss` refuses a close-call band not under the near-miss band.
- ⚠️ A parked-vehicle change owes a drive by day and at night (`--time-of-day=0.9`): the vans
  gone, the single-yellow fill in, the buses re-rolled past 400 m. The frame time with the
  colliders resident is owed (`P4-5`).
