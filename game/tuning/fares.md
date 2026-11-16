# fares.tres

Rationale for `game/tuning/fares.tres` (`Q119`).

The fare loop's own numbers (`P3-1a`, `Q141`), as against `tariff.tres`, which is Transport
Department's. The allowance is legal road distance over a par speed and the tip is seconds left
times a rate, so a shortcut and a fast run pay through the same number. Apart from `par_kph` these
are first guesses that a drive grades.

Every key is required: `fare_profile.gd` declares no defaults, and `FareSystem` refuses a zero
radius, bar or rate (all but `street_share`).

- `hail_radius_m` 12: plan distance from the car to the pickup's stop point (`nearest_edge` at
  `edge_t`, on the road). A car length and a half: stopping anywhere alongside hails, and two
  stands 30 m apart stay two. `RoadSpawn.DEFAULT_SETBACK_M` (20 m) must stay outside it.
- `deliver_radius_m` 12: the same reach at the other end. Not tighter: a found destination is not
  a parking test.
- `board_s` 1.0: a beat, so the hail is seen before the clock starts.
- `stop_below_kph` 5: a walking pace, read at both ends.
- `min_trip_m` 300: the shortest legal route a destination may be drawn at; a block and a turn. A
  pickup reaching no destination at this bar is stranded: dropped as a pickup, kept as a
  destination. Lowering the bar is not the answer to a stranded stand (`.claude/rules/fares.md`).
- `par_kph` 19: the speed the allowance is priced at, with no floor (`Q203`). Measured: the median
  run of the AI traffic, which obeys every light and give-way (18.8 kph at 18:00, 19.2 at 12:00).
  The player beats it by driving better or breaking rules. Re-measure when the traffic's pace or
  the signal timings change.
- `tip_hkd_per_s` 0.5: what each second left at delivery pays. Sized so the skill half is the
  order of the HK$29 flagfall most trips read.
- `sample_hz` 5: how often the loop asks the graph (`nearest_edge`, `route`). The meter and clock
  run every physics tick.
- `live_pickups` 4 (`Q203`, the user's call): customers waiting at once. Enough that one is near,
  few enough that each is a place to drive to.
- `place_m` 160: plan metres from the car within which a new customer is placed. Half the
  minimap's `span_m`, so a new customer shows on the map at once. Where no kerb is free within
  it, the nearest free kerb is used.
- `retire_m` 320: past this the farthest waiting customer is swapped for one within `place_m`,
  one a sample, and never while no free kerb is within this distance. Twice `place_m`, the
  minimap's whole span. `FareSystem` refuses it at or under `place_m`.
- `street_share` 0.75 (the user's call): the share of draws taken from `fares.json`'s street spots
  rather than the published stands and PUDO points. No published figure splits stand from street.
  0 is the off switch (published points alone), the one key not refused at zero.
