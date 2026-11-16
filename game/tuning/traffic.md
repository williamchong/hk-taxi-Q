# traffic.tres

How the moving traffic drives and where it lives (`P3-3c`, `Q173`). The cars are a backdrop to the
taxi, so every value is authored except `kinds` and `fleet_by_hour`, which are TD's (`Q186`).
`traffic_system.gd` says what each rule does.

Every key is required: `traffic_profile.gd` declares no defaults and `TrafficSystem` refuses a
zero. Also refused: `spawn_max_m` not over `spawn_min_m`, `retire_m` not over `spawn_max_m`,
`brake_max_mps2` not over `brake_mps2`, `spawn_seen_min_m` not over `spawn_min_m`, and an hourly
table not 24 long. `verify_traffic.gd` drives this file in both regions with the parked roster
resident.

## Fleet and ring

- `cars = 60` (`Q219`, the user's pick over 40 and 80): the fleet alive in the busiest hour. The
  largest of the three that holds every `verify_traffic` gate: at 80, Causeway Bay has two cars
  meet in a signalled junction and no routed vehicle reaches a stop. The answer to that is fewer
  cars, never a shorter `give_way_look_m`. The mobile tier (`P0-3b`) must re-take the cost.
- `spawn_min_m = 60.0`, `spawn_max_m = 220.0`: the ring cars appear in; the near edge keeps them
  out of the chase camera's near field.
- `retire_m = 260.0`: 40 m past the ring, so an edge-placed car does not vanish on its first tick.
- `spawn_clear_m = 12.0`: no car is placed nearer another, or on an edge shorter than this.
- `spawn_main_weight = 1.0` (`Q219`, the user's pick over 1.5 and 2): a spawn picks a road by its
  lane-metres, a main road's counted this many times. 1.0 spreads the fleet evenly over the lanes.
  Every seeded drive moves with it.
- `spawn_seen_min_m = 180.0` (`Q214`): a place the camera can see takes a car only this far away,
  and the car fades in. Nearer, a car is placed only out of view. Past the beams' `draw_m` (140)
  and inside the ring.
- `retire_unseen_s = 1.0` (`Q214`): how long a car past `retire_m` must be out of view before it
  goes, so a look back finds the street as it was.
- `retire_far_margin_m = 30.0` (`Q214`): a car in view is kept until this close to the camera's
  `far` (400 m, `city_drive.tscn`), then fades out, so a car that passed can be chased.
- `fade_in_s = 0.8`, `fade_out_s = 0.8`: the dither's run (`vehicle_body.gdshader`).
- `thin_every = 4` (`Q219`): a far car out of view reads its rules every fourth tick and drives on
  its last speed between. 67 ms late is inside the margin between `brake_mps2` and
  `brake_max_mps2`. 1 is the off switch. Bench: `tools/bench_traffic.gd --view=on`
  (1.67 ms a tick at 60 against 3.58 unthinned).
- `thin_beyond_m = 60.0`: thinned only past this from the camera and out of its frustum.
  `spawn_min_m`'s value and under `horn_range_m`.

## Driving

- `cruise_of_limit = 0.8`: 40 kph on a 50 kph street, so the taxi passes traffic.
- `turn_mps = 7.0`: 25 kph through a junction's curve.
- `accel_mps2 = 2.0`: a gentle pull-away.
- `brake_mps2 = 3.0`: the planned, comfortable stop.
- `brake_max_mps2 = 8.0`: the hardest a car brakes. The amber judgement is made at this rate; at
  the planned rate a car crossed into the red.
- `gap_m = 2.0`: bumper to bumper behind a stopped car.
- `look_m = 45.0`: how far a car looks for one to follow; over the planned stop from cruise (21 m).
- `follow_heading_deg = 45.0`: past this a car ahead is crossing, not queueing. The car's own path
  is read first and has no angle bar.
- `turn_span_m = 6.0`: fallback only. A turn runs between the junction mouths the bundle publishes
  (`trim_m`); this serves a node whose ribbon met no cap.
- `lane_change_m = 25.0`: travel to move one lane over. A car moves toward its turn's lane only
  while the lane beside is clear; one that never got across turns from where it is.
- `wink_hold_m = 5.0`: how far the tail runs past the mouth before a finished turn's indicator
  goes off. At the join, it stopped while the car still sat across the junction.
- `straight_deg = 30.0`: under this a move is straight on and keeps its lane. Over it a left turn
  goes nearside to nearside, a right offside to offside. Also `give_way`'s angle bar.
- `pass_look_m = 40.0` (`P3-3f`): how far ahead a parked vehicle in the lane makes a car move out.
  Most roster vehicles stand in lane 0.
- `side_clear_m = 0.3`: the room a moving car keeps from a parked vehicle's flank. It decides
  which pinches are passable: a minibus behind a bus on a 4.6 m one-way street (edge 349) has
  2.32 m and needs 2.38, so it waits. Lowering it puts a mirror on a bus.
- `give_way_look_m = 30.0` (`Q173`): how far short of its line a car starts giving way at an
  unsignalled junction, and how near its line a crossing car must be to be given way to. The
  planned stop from 40 kph with room. Longer holds side roads for a car half a block off; shorter
  makes cars brake hard at every crossing.

## Horns (`P3-79`)

- `horn_voices = 6`: a honk pattern holds its voice up to about 3.5 s; a seventh caller takes the
  voice nearest done.
- `horn_range_m = 110.0`, `horn_repeat_s = 4.0`: the tram bell's numbers (`trams.md`). The range
  is only the fade: a car sees the taxi within `look_m`, so no horn sounds from past about 46 m.
- `horn_after_s = 2.0`: the wait behind a taxi stopped in the lane. A red does not count.
- `horn_cut_mps = 3.0`: closing this much over the speed the car could still stop from is being
  cut up or met head-on. The horn a moving taxi hears.
- `horn_pitch_spread = 0.08`: about a semitone either side, fixed per car.
- `horn_count`, `horn_press_s`, `horn_gap_s`: per honk, the presses, press length and gap are
  drawn from these ranges by reason: `stood` (a polite tap), `cut` (a blast), `hit` (leaning on
  it), `close_call` (beep-beep-beep). Authored. Drawn on their own RNG off the traffic seed, so a
  pattern never moves a car (`Q178`). Files: `horn_<kind>.wav`.
- `horn_temper_step = 0.3`, `horn_temper_max = 0.8`, `horn_temper_s = 20.0`: each honk at the taxi
  raises the car's temper, pushing its next draws toward the top of their ranges; it decays over
  20 s.

## `kinds` and `fleet_by_hour` (`Q186`, `Q198`)

TD's numbers, printed by `tools/traffic_census.py`. Do not edit by hand; rerun the tool. 24
entries each, hour 0 first.

- `kinds`: each wandering kind's weight by clock hour, drawn at every spawn. Source: *The Annual
  Traffic Census 2025* via `atc.td.gov.hk`, the vehicle classification surveys at stations 1002
  Victoria Park Road, 2214 Causeway Road and 1107 Tung Lo Wan Road, pooled by vehicles counted.
  Private car → `car_a` + `car_b`, taxi → `taxi`, public light bus → `minibus`, light goods →
  `van`, renormalised to 100; other classes are left out.
  - Taxis are 24–42% by hour. Not tuned for the look: it is the census on these streets.
  - `car_a` : `car_b` is 4 : 3, authored (`CAR_SPLIT` in the tool); the census has one class.
  - The survey covers 07:00–23:00 on one weekday per station; hours outside hold the nearest
    surveyed one.
  - No coach (too long for the turn curve) and no motorcycle. The bus runs on its routes only.
- `fleet_by_hour`: the share of `cars` alive at each hour. A car leaving the ring is not replaced
  while the wandering fleet is at or over `round(cars × share)`, so the fleet thins and fills out
  of view. It is flow over speed (`Q198`), because flow alone saturates in a jam:
  - flow: the weekday hourly variation at seven stations (1002, 1020 Lockhart Road, 1024 Tai Hang
    Road, 1028 Gloucester Road, 1029 Hennessy Road, 1107, 2214), each station counted once;
  - speed: TD's eight detectors in the regions (Canal Road Flyover ×4, Gloucester Road ×4), from
    DATA.GOV.HK's archive over 18 weekdays. Trunk roads only; TD has no side-street detector.
  - Peak is 18:00 (1.00); 08:00–19:00 is 0.65–1.00; 04:00 is 0.07.

## Taxis

- `taxi_kind = "taxi"` (`Q183`): the kind that wears a licence. At spawn a taxi takes the mesh its
  road's region draws from `city.json`'s `taxi_licences`. Chosen off the car's id and spawn count,
  never the seeded RNG.
- `taxi_for_hire = 0.5`: the share of moving taxis with the roof sign lit (the user's "random roof
  sign"). TD publishes no vacancy rate.

## Knocked by the taxi (`Q180`)

A hit car takes the impulse its mass gives (`parked.tres` `masses_kg`, `handling.tres`
`collision_restitution`), slides on the taxi's own tyre grip (`tyre.tres` `mu` × the pace), stands
on its hazards while traffic passes it, then tries to drive on.

- `react_s = 0.9`: TD's thinking time (Road Users' Code ch. 5: 10 / 15 / 20 m at 40 / 60 / 80
  km/h).
- `recover_after_s = 2.0`: the pause before pulling away, and between tries.
- `recover_radius_m = 6.0`: a car within this of the centreline drives back; one further off
  stands until the ring takes it.
- `recover_heading_deg = 45.0`: a knocked car does not reverse. Facing within this of a legal way
  it curves back; otherwise it stands.
- `recover_ahead_m = 12.0`: where it rejoins the nearside lane, so the curve is a lane change.
- `recover_clear_m = 15.0`: no car under way within this of the rejoin point or the way there. A
  standing car is not looked for (a queue behind the wreck would hold it for ever), but the path
  is swept against every body.

## The routed fleet (`P3-78`, `Q182`)

Buses and green minibuses on TD's published routes (`bus_routes.json`), placed at a stop in the
ring mid-dwell and driven stop to stop on the legal router's arcs.

- `buses = 6`: slots on top of `cars`. Not TD's count: the published service would bury the
  street. The headways choose which route, not how many.
- `dwell_s = 12.0`: authored; TD publishes no dwell time.
- `placed_dwell_left = 0.2`: a vehicle placed at a stop has between this share and all of its
  dwell left, so a ring of buses does not pull out together.
- `dwell_reach_m = 1.5`: a stopped vehicle with its front within this of the pole dwells. Further
  back it is queued; carried further past, it missed the stop (counted by the verify tool).
- `pull_out_m = 15.0`: how far it drives from its stop with the right indicator on (the user's
  call). It winks left on the approach and while standing.
- `kerb_stop_kinds = [minibus, taxi]`, `kerb_stop_every_m = 500.0`, `kerb_dwell_s = 8.0` (the
  user's call): on joining a road these kinds pull up at the nearside kerb at a chance of the
  road's usable length over `kerb_stop_every_m`, on `_kerb_rng`. Never on a restriction run
  (`RoadGraph.no_stopping`, double and single yellow alike), beside a parked vehicle, within
  `lane_change_m` of a mouth, off level 0, or before an offside turn.
- `kerb_unlawful_kinds = [minibus, taxi]`, `kerb_unlawful_share = 0.25` (the user's call): a
  quarter of those stops ignore the restriction. Wandering vehicles only.
- `wander_liveries = {minibus: red}`, `route_liveries = {minibus: green}`: the colour is the
  licence (`Q167`). `parked.tres`'s own two `minibus` colours. The bus wears none.
