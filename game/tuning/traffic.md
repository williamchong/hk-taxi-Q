# traffic.tres

Rationale for `game/tuning/traffic.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How the moving traffic drives and where it lives (`P3-3c`, `Q173`). Every value is AUTHORED but
two: the cars are a backdrop to the taxi, not a model of the city's traffic. The two are `kinds`
and `fleet_by_hour`, the mix and the fleet by clock hour, which are TD's census on these streets
(`Q186`). `traffic_system.gd` says what each rule does; this says why each number.

⚠️ EVERY KEY BELOW IS REQUIRED. `traffic_profile.gd` declares no defaults, so a missing key reads
as zero, and `TrafficSystem` refuses to run on a zero. Three are held as DIFFERENCES — `spawn_max_m`
over `spawn_min_m`, `retire_m` over `spawn_max_m`, `brake_max_mps2` over `brake_mps2` — so a table
that inverts one is refused too, and an hourly table of any length but 24. `verify_traffic.gd` drives this file, three seeds × 90 s round the signals and one on the back
streets, with each region's parked roster resident.

## `cars = 24`

The fleet alive at once. Measured on the throttle route (2026-10-29, desktop): +7 `draws` (one
`MultiMesh` per kind, and their shadows) and about +1 ms of `phys` against `--traffic=off`
(2.8 against 1.8 ms a tick, ±0.5 ms run to run). The mobile tier (`P0-3b`) must re-take it; the
per-car cost is the car-ahead search, which is every pair.

## `spawn_min_m = 60.0`

Far enough that a car rarely appears in the chase camera's near field.

## `spawn_max_m = 220.0`

The ring cars appear in. With 24 cars over the streets inside 220 m, a busy road shows a car or
two at a time, not a jam.

## `retire_m = 260.0`

40 m past the ring, so a car placed at its edge does not vanish on its first tick away.

## `spawn_clear_m = 12.0`

No car is placed nearer another than about two car lengths, and no car is placed on an edge
shorter than this.

## `cruise_of_limit = 0.8`

40 kph on a 50 kph street: a car that keeps to its limit, under it, so the taxi passes traffic.

## `turn_mps = 7.0`

25 kph through a junction's curve.

## `accel_mps2 = 2.0`

A gentle pull-away; 0 to 40 kph in about 5.5 s.

## `brake_mps2 = 3.0`

The planned stop, for a light or a car ahead: comfortable.

## `brake_max_mps2 = 8.0`

The hardest a car brakes on a tick: near a dry tyre's limit, for a car cut up. ⚠️ The AMBER
judgement is made at this rate, not the planned one — see `traffic_system.gd`; at the planned rate
a car rode the line of its own judgement and crossed into the red.

## `gap_m = 2.0`

Bumper to bumper behind a stopped car.

## `look_m = 45.0`

How far a car looks for one to follow: further than its stopping distance from cruise at the planned
rate (40 kph → 21 m).

## `follow_heading_deg = 45.0`

Past this a car ahead is crossing, not queueing, and is not followed in the plan cone. The car's own
path (its edge and the edge it turns into) is read first and has no angle bar.

## `turn_span_m = 6.0`

The fallback only, since city schema 41: a turn runs from the junction mouth the bundle publishes
(`trim_m`, where the stop line stands) to the next road's, and this reaches either side of a node
whose ribbon met no cap. 40% of a short edge, and never short of the stop point.

## `lane_change_m = 25.0`

Travel to move one lane over, a three-second change at 30 kph. A car moves toward its turn's lane
from the moment it joins the road and only while the lane beside it is clear for both cars' lengths
and `gap_m`; one that never got across turns from where it is. Shorter reads as a swerve.

## `wink_hold_m = 5.0`

How far the car's tail runs past the mouth it joined by before the indicator of the turn it finished
goes off — a driver's stalk cancels as the wheel comes straight, not as the nose meets the new road.
Off at the join, the wink stopped while the car still sat across the junction (the user's report,
2026-10-30). The next turn's approach takes the indicator over; a lane change waits for it.

## `straight_deg = 30.0`

Under this between the way in and the way out a move is straight on and keeps its lane; over it a
left turn is taken from the nearside lane into the nearside, a right from the offside into the
offside (the user's drive, 2026-10-29: cars turned right from the left lane). A staggered crossroad's
dog-leg reads straight at 30°.

## `pass_look_m = 40.0`

How far ahead a parked vehicle in a car's lane makes it move out to pass (`P3-3f`, the user's drive
2026-10-29: cars drove through parked ones). The roster puts most of its vehicles IN lane 0 — a bay
or a fill car at the kerb takes the nearside lane, which is Hong Kong's kerbside, and
`verify_traffic`'s `parked:` table counts it (Wan Chai + Causeway Bay, 2026-10-29: of the 1,081
placements on roads traffic drives, 759 stand in lane 0 and 247 in a lane past it only). 40 m at 30 kph is five seconds: room for a `lane_change_m` change
before the car meets it, and short enough that a car does not leave the nearside for a van a block
away.

## `side_clear_m = 0.3`

The room a moving car keeps from a parked vehicle's flank: closer, the vehicle is in its lane. Kept
from the vehicle only — a car edging out may run its flank to the far kerb, because the published
width is kerb to kerb and a back street is "parked on one side and passed in the lane left"
(`parked.py`). It decides which pinches are passable: a minibus behind a bus at its stop on a 4.6 m
one-way street (edge 349) has 2.32 m beside the bus and needs 2.38 (its 2.08 m and this), so it waits — that wait is the
`parked:` "longest stand" line, and lowering this to clear it would put a car's mirror on a bus.

## `give_way_look_m = 30.0`

How far short of its line a car starts giving way (`Q173`, the user's drive 2026-11-04: cars drove
through each other at junctions without lights), and how near its own line a car coming must be
to be given way to. 30 m is the planned stop from 40 kph (21 m at `brake_mps2`) with room: a car
nearer its line than it can stop for at `brake_max_mps2` is in the junction and is given way to
whatever this says. Longer holds a side-road car for a main-road car still half a block off; shorter
than the planned stop and a car brakes hard for every crossing. The rule's angle bar is
`straight_deg` (two paths under it run side by side or head to head) and its clearance
`side_clear_m` (bodies apart by it, as a flank from a parked vehicle) — not values of their own.

## `horn_voices = 6`, `horn_range_m = 110.0`, `horn_repeat_s = 4.0`

The range and the repeat are the tram bell's numbers (`trams.md`), for the same reasons: four seconds is
impatient without being a car alarm. The voices were the bell's three until `P3-79`: a honk is now a
pattern that holds its voice up to about 3.5 s (a temper-full `hit`), where the old press was 0.42 s, so
three would be stolen mid-pattern at any busy junction. A seventh caller takes the voice nearest done. ⚠️ `horn_range_m` is only the fade: a car sees the taxi
within `look_m`, so no horn sounds from past about 46 m, where this leaves it at around 0.6.

## `horn_after_s = 2.0`

Hong Kong patience behind a taxi that has stopped in the lane. A red does not count: the wait starts
when nothing but the taxi holds the car, so the queue at a light stays quiet until it goes green.

## `horn_cut_mps = 3.0`

About 11 kph over the speed the car could still stop from. A car closing on the taxi normally rides
that speed down at `brake_mps2`, so it reads near nothing; being cut up or met head-on reads far past
this on the tick it happens. This is the horn a moving taxi hears: it rarely stands in front of anyone.

## `horn_pitch_spread = 0.08`

A semitone or so either side, so that two cars do not sound like one car twice. Fixed per car.

## `horn_count`, `horn_press_s`, `horn_gap_s`

A honk is a pattern (`P3-79`, the user's ask 2026-11-05: "randomised the length, interval and
times"): presses, each press's length and the gap between, drawn per honk from these ranges by why
the car honks. Each kind sounds its own file (`horn_<kind>.wav`, `tools/make_vehicle_sounds.py`), a
loop held for the press, so one file gives any length.

- `stood` — 1–2 presses of 0.08–0.2 s, 0.1–0.25 s apart: the polite tap of a car whose driver has
  noticed the taxi is not going anywhere.
- `cut` — 1–2 of 0.4–1.2 s: being cut up or met head-on is a real blast.
- `hit` — 1–2 of 0.6–1.6 s, close together: leaning on it after the taxi hit it or the car ahead.
- `close_call` — 2–4 of 0.1–0.3 s, 0.08–0.15 s apart: the angry beep-beep-beep after a scrape past.

All authored by ear-sense, none measured: no Hong Kong source counts honks. The draws are on their
own RNG off the traffic seed, so a pattern never moves a car (`Q178`'s pitch rule, for the same reason).

## `horn_temper_step = 0.3`, `horn_temper_max = 0.8`, `horn_temper_s = 20.0`

Escalation: each honk at the taxi raises the car's temper 0.3, which pushes its next count and press
lengths toward the top of their ranges (never past them); the gaps stay random. Held at 0.8 so even
the angriest car's draws still vary, and falling a whole share over 20 s, so a car the taxi left alone
for half a minute is calm again. The first honk is a tap, the third a long blast.

## `kinds = {car_a, car_b, minibus, taxi, van}`, each by clock hour

The parked library's road vehicles, each weighted by the clock hour (`Q186`, the user's ask
2026-11-06: "can road car type and density change according to time of day? … fetch the TD census
first"). 24 entries a kind, hour 0 first; a wandering car's kind is drawn on its hour's weights at
every spawn. No coach (too long for the turn curve the cars take) and no motorcycle (a box under it
would read as a car). ⚠️ The 12 m bus does take that curve since `P3-78`, on its routes only;
`verify_traffic`'s routed drive holds it to every rule a car is held to.

**Every number is TD's**, printed by `tools/traffic_census.py` — do not edit it by hand; rerun the
tool. Source: *The Annual Traffic Census 2025*, read through the census's interactive site
(`atc.td.gov.hk`, the AADT Analysis page's `api/analysis`): the vehicle classification surveys at
the three counting stations inside the two regions that have one — 1002 Victoria Park Road,
2214 Causeway Road and 1107 Tung Lo Wan Road — **pooled by vehicles counted** each hour (about
3,000–5,000 an hour; Tung Lo Wan Road's ~20 an hour barely moves it). Of the census's ten classes
four are drawn: private car → `car_a` + `car_b`, taxi → `taxi`, public light bus → `minibus`, light
goods → `van`; the rest (motorcycles, heavy goods, coaches, private light buses, franchised buses —
which run on their routes) are left out and the four renormalised to 100.

| hour | car_a + car_b | taxi | minibus | van |
|---|---|---|---|---|
| 07 | 48.5 | 39.9 | 1.8 | 9.8 |
| 10 | 50.2 | 31.5 | 0.3 | 17.9 |
| 12 | 54.5 | 35.1 | 0.0 | 10.4 |
| 16 | 63.0 | 23.9 | 0.4 | 12.7 |
| 18 | 72.6 | 23.4 | 0.0 | 4.0 |
| 20 | 54.8 | 42.4 | 0.3 | 2.5 |

- **The taxis**: about a third of what these roads carry, 24–42% by hour, most at 20:00 — well over
  the 16.8% (`Q183`) the roster drew before, which was the CROSS-HARBOUR share (§5.4 of the 2023
  report), the nearest the PDF printed; the stations' own surveys were not in it. 🔴 Not tuned for
  the look: the user asked for the census, and this is the census on these streets.
- **The vans** — light goods — work the day: 10–18% from 09:00 to 15:00, under 4% after 18:00.
- **The red minibus all but vanishes** (0–2%): the public light buses these three stations counted
  were few. The green ones keep to their routes (`buses`, `P3-78`) and are not drawn here.
- ⚠️ **`car_a` : `car_b` is 4 : 3, AUTHORED** (`CAR_SPLIT` in the tool): the census has one class for
  private cars, and this is the split the roster drew them at before.
- ⚠️ **The survey covers 07:00–23:00**: hours outside it hold the nearest surveyed one (00–06 the
  07:00 mix, 23 the 22:00). The shift runs 07:00–21:00, so only free mode past its clock could read
  one, and the clock holds at 21:00 there.
- ⚠️ **One weekday's survey per station**: the census surveys each station once, on a weekday;
  the API answers the same row whatever day is asked.

## `fleet_by_hour`, 24 entries

The share of `cars` alive at each clock hour (`Q186`): a car that leaves the ring is not placed
again while the wandering fleet stands at or over `round(cars × share)`, so the fleet thins as cars
drive off and fills as the ring places them, never popping in view. **TD's too**, by the same tool:
the weekday (`M-F`) hourly variation — each hour's share of the day — at the seven counting
stations inside the two regions (1002, 1020 Lockhart Road, 1024 Tai Hang Road, 1028 Gloucester
Road, 1029 Hennessy Road, 1107, 2214), averaged with each station counted ONCE and divided by the
busiest hour. A mean of shapes, not of flows: Gloucester Road's 104,000 a day would otherwise drown
the side streets the taxi drives.

| hour | 04 | 07 | 08 | 12 | 18 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|---|---|
| share | 0.14 | 0.77 | 0.97 | 1.00 | 0.99 | 0.79 | 0.74 | 0.68 |
| cars of 24 | 3 | 19 | 23 | 24 | 24 | 19 | 18 | 16 |

⚠️ **Daytime Wan Chai is flat**: from 08:00 to 19:00 every hour is within 7% of the busiest, so the
shift opens at three-quarters of the fleet, fills by 08:00 and thins from 20:00. `cars` is the
busiest hour's fleet and the ceiling: no hour runs more than the 24 the cost was measured at.

## `taxi_kind = "taxi"`

The kind that wears a licence (`Q183`): at each spawn a taxi takes the mesh its road's region draws
from `city.json`'s `taxi_licences` (TD's stands, read by `parked.py`), so a green New Territories
taxi runs only where the stands say green taxis are. Off the car's id and its spawn count, never
the seeded RNG: one more roll would move every later car.

## `taxi_for_hire = 0.5`

The share of the moving taxis whose roof sign is lit at each spawn (the user's call 2026-11-05:
"random roof sign"), at the player's own `sign_lit` (`vehicle_lamps.tres`). Not measured: TD
publishes no vacancy rate for the street. A half, so that both read.

## Knocked by the taxi (`Q180`, the user's calls, 2026-11-04)

A car the taxi hits takes the impulse its mass gives (`parked.tres` `masses_kg`,
`handling.tres` `collision_restitution`) and leaves its lane. It slides on its tyres: across them
at the road tyre's grip times the world's gravity (`tyre.tres` `mu` × `pace.tres`' scale — the
taxi's own, never a second grip), along them coasting until its driver reacts, then braking at
`brake_max_mps2`; its spin dies on the same grip over its box. It stands on its hazards, the
traffic stops for it and, once it has settled, passes it as a parked car. Then it tries to drive
on; where it cannot, it stays until the ring takes it away. A car is not damaged yet, so every
knocked car tries.

## `react_s = 0.9`

TD's own thinking time: the Road Users' Code, chapter 5, "Stopping Distance", draws 10 / 15 / 20 m
of thinking distance at 40 / 60 / 80 km/h — 0.90 s at every speed, for "an alert driver" on a dry
road, the shortest it gives. A driver who has just been hit is no quicker. Over it the car loses
almost nothing: rolling resistance takes about 0.1 m/s in 0.9 s, so it is not modelled.

## `recover_after_s = 2.0`

The pause a driver takes before pulling away again, and the wait between tries when the way back
is not clear. Authored; nothing publishes it.

## `recover_radius_m = 6.0`

About a lane and a half from the centreline it rejoins: a car shoved onto the footway or into a
side street's mouth drives back; one put further off — over a central reserve, into a building's
recess — stands. Authored.

## `recover_heading_deg = 45.0`

A knocked car does not reverse. Facing within 45° of a way it may drive, it turns back into the
lane in one curve, as a turn does; turned further round — across the road, or backwards on a
one-way street — it stands until the ring takes it. Authored.

## `recover_ahead_m = 12.0`

Where it rejoins its nearside lane, down the road from where it stands: a little under three car
lengths, so the curve back is a lane change, not a turn on the spot.

## `recover_clear_m = 15.0`

It looks first: no other car under way within this of where it rejoins or the middle of its way
there. A car standing is not looked for — one queued behind the wreck waiting for it to move would
hold it for ever — but the way back is swept against every body, so one standing in it still stops
it. Over
a lane change's own `lane_change_m` this is a gap a car coming at 50 km/h closes in about a second;
a car that cannot see one waits `recover_after_s` and looks again.

## The routed fleet (`P3-78`, `Q182`, the user's asks, 2026-11-04)

Buses and green minibuses on the routes TD publishes (`bus_routes.json`): `buses` more slots
than `cars`, each placed at a stop in the ring, mid-dwell, on a route drawn by its departures in
the game hour (TD's GTFS headways), and driven stop to stop on the legal router's own arcs.

## `buses = 6`

Not TD's count. 464 route directions stop in Wan Chai, and those routes publish 1,099 departures
in the 07:00 hour alone (`busroutes.json`, 2026-11-05), so a share of the published service would
bury the street. Six beside 24 cars is a bus or two on a main road at a time. The headways choose
WHICH route a bus is on, not how many there are. The draw-call cost is one more `MultiMesh`
(the bus); the green minibus shares the wandering minibus's.

## `dwell_s = 12.0`

How long a bus stands at its pole: an authored figure for a few passengers boarding by
Octopus at the front door. TD publishes no dwell time. A vehicle placed at a stop is found part
way through its dwell.

## `dwell_reach_m = 1.5`

A stopped routed vehicle whose front is within this of its pole is at its stop and dwells.
Further back it is queued behind another bus at the same stop, and waits to move up. A vehicle
carried more than this past its pole has missed the stop and goes on to the next, which the
verify tool counts.

## `wander_liveries = {minibus: red}`, `route_liveries = {minibus: green}`

The colour IS the licence (`Q167`): a green minibus runs a fixed route and a red one does not,
so a minibus with no route is red, and one on a route green. Both colours are the parked roster's
own `minibus` entries (`parked.tres` `liveries`). A kind named in neither wears the parked
palette, and the bus wears none: its livery would be its operator's, which `Q167` keeps off.
