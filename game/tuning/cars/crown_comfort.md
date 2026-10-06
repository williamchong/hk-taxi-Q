# crown_comfort.tres

Rationale for `game/tuning/cars/crown_comfort.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The Toyota Crown Comfort LPG, Hong Kong's taxi, as a `CarSpec` (`Q156`, 2026-10-06): the car's own
numbers and nothing about how the game should feel. Split out of `handling.tres`, which keeps the
game layer (steering ramps, the drift's threshold, the wall response); the values did not move.
A second car is a second file here and its wheels' positions in a scene (`taxi.tscn` holds this
car's wheelbase 2,785 mm and its mean track 1,430 mm, `Q153`).

**A real taxi is the baseline** (the user's call, 2026-10-05): a number here is the car's, or a
typical figure for its class where the maker's is not published, and says so. Gameplay goes on top
— the systems' tables, `arcade_aids`, the pace — never by bending one of these.

🔴 **A force this table decides is derived, never authored beside it** (`Q156`): the brake is
`brake_g` of the weight, the handbrake `HandbrakeProfile.lock_ratio` of a rear wheel's lock, a
spring's ceiling `suspension_max_load_ratio` of a wheel's load at rest. Hand-sized, each was
re-seeded at every change of mass, gravity or grip (`Q153` lists four rounds), and under one that
was missed every tap spun at 168°.

## `mass_kg = 1400.0`

The Crown Comfort's kerb weight is about 1,390 kg; with a driver, 1,400 (`Q153`). Set on the rigid
body in `VehicleController._ready` — it was `taxi.tscn`'s `mass` until 2026-10-06.

## `centre_of_mass_offset_y = -0.35`

Under the body's origin, not a measured figure: seeded for roll on the engine-tyre car (`Q50`) and
kept. The side force's own height is `TyreProfile.side_force_depth`.

## `max_speed_kph = 140.0`, `max_reverse_kph = 40.0`

The limiter the drive tapers into. A game's ceiling for city streets rather than the car's own top
speed (about 170 kph); the power and the air set the pace well under it.

## `engine_force = 6000.0`, `engine_power_kw = 83.0`, `driveline_efficiency = 0.85`

The 1TR-FPE's 83 kW and 186 N·m (`Q153`): 6,000 N at the tyres off the line through a typical
Toyota 4-speed first gear (≈ 2.8) and final drive (≈ 4.3 — typical, not this car's published
ratios) at 85% on 0.31 m wheels, and the power over the speed above about 42 kph.

## `drag_area_m2 = 0.72`

A saloon's Cd of about 0.36 on about 2.0 m² — typical figures, not the Crown Comfort's published
ones (`Q153`). About 240 N at 80 kph.

## `brake_g = 1.2`, `brake_front_share = 0.65`

A road car's brakes, a little over what its tyres can use, so the tyre and ABS set the stop
(`Q153`; swept 1.0–1.3, the stop is the tyre's from 1.1 up). The bias is a front-engined saloon's.

## `steer_angle_max_deg = 32.0`

The front wheels' lock at rest. The lock at speed is the game's (`HandlingProfile.steer_angle_at_top_deg`,
and `arcade_aids.steer_to_grip` under it).

## `wheel_radius_m = 0.31`

A 195/65 R15, the taxi's fitment: 0.318 m unladen. `tools/make_vehicle.py` mirrors it.

## `suspension_rest_length_m = 0.39`, `suspension_travel_m = 0.18`

The rig's, not the car's sheet: the hub's drop under the wheel node and the travel that absorbs
a kerb (`Q50`, `Q153`). `tools/ground_clearance.py` mirrors the travel.

## `suspension_frequency_hz = 2.2`, `suspension_damping_ratio = 0.55`

Stiffer than a road car's 1.5 Hz, for a flat arcade ride; 2.2 at the world's own gravity, where it
was 2.8 at 1.6× (the ride height holds when it scales by the root of the gravity, `Q153`).

## `suspension_max_load_ratio = 4.0`

A spring may push with four times its wheel's load at rest: 13,720 N on this car. It was
`suspension_max_force_n` 13,700, hand-seeded "at roughly 4× static load" (19,000 on the 1,200 kg
car at 1.6× gravity, 4.04×). Measured 2026-10-06: at 3.994 (13,700 exactly) the pad at 42 / 63 /
86 kph is byte-identical with the authored newtons, the walls included; at 4.0 only the wall
clips' exits move (`wall@30` 24.3 → 23.1 / 35.8 → 31.0 / 42.4 → 49.0 kph), the one place on the
pad a spring reaches its ceiling — the approach, the impact and every other row unmoved.
