# tyre.tres

Rationale for `game/tuning/tyre.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The per-wheel tyre model's table (`P3-52`, `Q152`): built as the spike that asked whether a
drift can be physical on `VehicleBody3D`, and the game's car since 2026-10-03 (`city_drive.tscn`
instances `taxi_tyre.tscn`). Read by `TyreVehicleController` alone. "The shipped car" below is the
car before it — `taxi.tscn` on the engine's tyres, still the control on `skidpad.tscn`. Every
value was graded on
`tools/skidpad.sh --scene=res://scenes/dev/skidpad_tyre.tscn --entry-kph=` at 42, 63 and 86 kph,
and `Q152` holds the tables.

⚠️ `substeps`, `mu`, `slide_ratio`, `peak_slip_ratio`, `peak_slip_angle_deg`,
`wheel_inertia_kgm2`, `low_speed_mps` and `drive_scale` are required: `tyre_profile.gd` declares no
defaults, and a zero leaves the car on the engine's own tyres (`TyreVehicleController.usable`).
`yaw_assist_scale` is absent because it is 0.0 — Godot's writer drops a value equal to the type's
zero — and 0 is the choice: the yaw torque did not rescue the low end and is not needed for the
held slide. `countersteer_assist` and `assist_drive_fade_from_deg` are the drift assist's, inert
while `TyreVehicleController.drift_assist` is off — the player's option since `P3-56`, on by
default in the game and off on the pads (`--assist=on` turns it on there).
`slide_lock_deg` is absent for the same reason, refuted on the pad's driver; its section keeps the
sweep. `catch_lock_deg` is set at 6.0 on the user's call (2026-09-30), ahead of their drive, which
stays the veto.

## `mu = 2.0`

The shipped car corners at 2.7 g on the skidpad's `corner` row (11.2 m radius at 63 kph), and the
car carries `gravity_scale` 1.6, so its tyres need 1.7 × load at the limit. 2.0 leaves a margin.
This is arcade grip — a real tyre is near 1.0 — and it is why the car needs twice the drive to
spin its rear tyres (`drive_scale`).

## `slide_ratio = 0.9`

The sliding tail. Swept 0.5–0.9 on `hold`: 0.9 was the only value holding past 2 s at both 63 and
86 kph (2.08 / 2.12 s before the roll point moved to 0.8); at 0.6 the 86 kph slide spun (179°).

## `peak_slip_ratio = 0.1`

Where drive and brake force peak, a textbook road tyre. Not swept.

## `peak_slip_angle_deg = 8.0`

A road tyre's cornering peak. Swept 4–8 on `corner`: a stiffer tyre scrubs less and the doubled
drive then accelerates the car even further through the bend, so it moves the failing row the
wrong way.

## `wheel_inertia_kgm2 = 1.2`

A 0.35 m wheel and tyre with a share of the drivetrain. The spin is solved implicitly, so this sets
how fast a wheel spins up, not whether the step is stable.

## `drift_side_cut = 0.6`, `drift_side_cut_from_kph = 42.0`, `drift_side_cut_to_kph = 65.0`, `rearm_on_steer_release = true`

The 90° drift (`Q153`, the user's street report of 2026-10-02). The cut caps the rears' sideways
force at a share of what the turn asks while the button is engaged, so the slide starts inside the
corner (0.57 s and 54° of heading at 42 kph, from 2.1 s and 181°); it is latched at the press and
eases to `drift_side_cut_fast` (absent, 0) by 70 kph, because 0.6 at 63 kph spins the car and 0.2
at 86 does. The re-arm brings traction control back the tick the steering is let go, which is the
ending: settled at 81–85° at 42 kph and 83–91° at 63 on the pad's `turn` row (96–107° at 63 with
the band to 70). It fires once the player has steered since the press, whichever came first. Graded on `turn`
(start and settled heading) with `hold` and `ride` as the guard. `handbrake_declutch` is absent:
built, measured, and only a harsh brake (`Q153`). The band ended at 70 kph first; 65 since the
user's second street drive ("sometimes the rear feels too spinny"), with the fade below.

## `slide_drive_fade_from_deg = 25.0`, `slide_drive_fade_to_deg = 40.0`

The forward drive fades out over this band of body slip while traction control is disarmed, so a
held throttle cannot spin the car (`Q153`, the user's street report). A plain held tap peaked 30.7 /
47.8 / 65.1 / 49.7 / 50.0° at 42 / 50 / 63 / 75 / 86 kph; with the band and the cut ending at 65 kph,
29.0 / 35.7 / 41.6 / 35.3 / 34.5°. `hold` never reaches the band (peak 23–27°) and is unchanged, as
is the `turn` row at 42 kph. 30 → 40–50 left 63 kph at 50–53°; no existing dial did it
(`rim_overspeed` 0 calms 75–86 kph and loses `hold` at 86; `traction_rearm_s` moves nothing).

## `handbrake_torque_nm = 3000.0`

Locks the rear wheels at the car's load (capacity ≈ 2 × 4,700 N × 0.35 m ≈ 3,300 N⋅m per wheel with
`mu`). Swept 1,500–4,000 on `hold`: 3,000 was the best at 63 kph; 4,000 killed the slide there and
helped it at 86.

## `low_speed_mps = 3.0`

The floor under which slip is measured against 3 m/s rather than the wheel's own speed, so a car
at rest does not read an infinite slip.

## `substeps = 8`

The spin solve's steps a tick. At 8 the residual stays monotone (the wheel's inertia term outweighs
the tyre's falling slope); at fewer it may not, and the safeguarded Newton then bisects.

## `drive_scale = 2.0`

The finding in one number. At 1.0 — the shipped drive — the rear tyres cannot be spun and no row
holds a slide; at 2.0 `hold` passes at both speeds; at 3.0 the 86 kph slide spins. The cost: the
car runs up to 119 kph in 4 s where it made 63, and the `corner` row accelerates through the bend.

🔴 Not the lever for the power-on corner (`Q153`'s `liftoff` round, 2026-10-02): at 1.5 and 1.75
the tap does not slide at 30, 42 or 63 kph (peak 5.2–10.9°, `hold` 0 s) and `hold` at 86 falls
1.40 → 1.00 s, while `corner` still accelerates (86 → 118 kph at 1.5) and widens. The slide needs
the whole 2.0; the corner is answered elsewhere (`P3-55`).

## `rim_overspeed = 0.5`

How far past top speed a driven wheel's rim may spin before the drive is stopped, as a share of it
(`P3-53`, `Q153`). At 0 the limiter sits at 140 kph of rim speed and a countersteered slide at
86 kph meets it mid-slide: `hold` 1.40 s. At 0.5, `hold` reads 1.93 / 2.63 / 3.17 s at 42 / 63 /
86 kph and every bar but the assisted slide at 42 kph (1.92 s) passes; the cost is a plain input's
peak, 28–30° → 48–52° against the 60° bar. 0.25 does not carry 86 kph (1.62 s). `Q153` holds the
grid with `handbrake_torque_nm`. Set at 0.5 on the user's call after driving the pad (2026-10-02,
"seems ok for now"); 0 is today's limiter.

## `traction_limit = 1.0`

Traction control cuts a driven wheel's torque past peak wheelspin, so full throttle at full lock
grips (peak slip 2.5° where it was 82° without it). Forward slip only: keyed on the combined slip
it cut the drive at every cornering limit.

## `traction_rearm_s = 2.0`

The drift button switches traction control off; it re-arms once the button has been up this long
and the body's slip is under the game's 14°. At 0 and 0.5 it re-armed before the throttle took the
slide over (`hold` at 63 kph 0.00 s). At 1.0 a player's own input — the tap, the steering and the
throttle held (`ride`) — slid 0 s at 42 kph, because the governor came back and cut the power the
slow slide needed; at 2.0 it slides 1.85 s. 3.0 reads the same as 2.0.

## `turn_drive_cut = 0.5`

The share of the forward drive taken off at full lock while traction control is armed (`P3-55`,
`Q153`), for the power-on corner: at 0 a full-lock corner under the doubled drive runs to about
128 kph from any entry and its arc widens, where the shipped car settles at 62–65. The drift button
disarms traction control, so a slide never sees it — `ride` and `hold` hold their peak and
`longest` at every value, and only the exit after the re-arm moves. Swept 0–0.9 on `corner` at 42 /
63 / 86 / 105 / 125 kph (`Q153` holds the table): 0.5 settles near 90 kph and pulls away from
10 kph at full lock as the shipped car does (45.1 against 43.3 kph two seconds in); 0.6 settles
near 70 and 0.7 near 57, the shipped car's terminal speed between them, pulling away 13% and 30%
behind it. Set at 0.5 on the user's call after driving the pad (2026-10-02, "seems ok for now"):
the arc stops widening and the pull-away is the shipped car's; 0 turns it off. 🔴 Graded on `corner` and
`liftoff`'s windows across entries and on the 10 kph pull-away, never on `hold` or `ride`, which
cannot see it.

## `side_force_depth = 0.7`

Where the sideways force goes in, 0 at the centre of mass's height, 1 at the contact. The shipped
0.2 (`handling.tres`'s `roll_influence`) takes away the load transfer that rotates the car — at 0.6
and below a player's input does not slide at 63 or 42 kph; at 1.0 the car rolled onto its side at a
kerb on Expo Drive. 0.7 is the least that slides at all three speeds (`ride` 1.85 / 2.55 / 3.15 s),
and on the full-throttle kerb it bounces the body 0.19 m less than 0.8 (peak 6.57 m against 6.76);
both still lift the inside wheels at 72 kph. Its own name, not `roll_influence`: a sweep resolves a
field by name across both tables, and the shared name swept the handling table's copy.

## `countersteer_assist = 1.5`

The share the drift assist turns the fronts by, while the player's option is on (`P3-56`,
`Q153`: default on, the floor a novice's slide pays from). Off, countersteering is the player's
skill — the user's call of 2026-09-29 ("i want counter steering to be part of gameplay") is the off
mode, not reversed. 🔴 With the option off the `ride` row is *meant* to fall short of the fare's
bar; the countersteered `hold` row is the one that pays. With it on, `ride` is the row, and `hold`
must read as it does off: a player who countersteers is not fought.
The assist acts only while the player steers INTO the slide (`_update_steering`): still turning the
fronts after a let-go or a countersteer, it brought the 90° `turn` out at 58–75°; gated, `turn` is
byte-identical in both modes. And once the player countersteers, it stands aside until the slide is
over (`assist_yields`, the slip back under the tyre's peak): re-tested each tick, it stepped back in
every time the pad's feathering driver crossed zero, and `hold` read 0.27 / 0.27 / 1.05 s at 42 /
63 / 86 kph. Latched, 2.00 / 3.28 / 1.45 s — the off mode's 2.00 / 3.28 at 42 and 63, every other
row in both modes byte-identical. 86.48 kph sits on `hold`'s own cliff (`Q153`): across 76–95 kph
the two modes read within 0.1 s, about 3.1 s to 83 kph and about 1.4 s from 90, and only the
step's place differs. Graded 2026-10-05, `--assist=on`, three identical runs a cell:

| entry kph | `ride` longest, off / on | `ride` peak, off / on |
|---|---|---|
| 42 | 0.85 / 3.30 s | 29.0 / 26.0° |
| 63 | 0.80 / 3.32 s | 41.6 / 33.8° |
| 86 | 1.12 / 3.17 s | 34.5 / 39.4° |

2.0–3.0 straightens the slide at every speed (86 kph 0.73 s at 2.0). The history below is from
before the call that made it an option.

Before: off, on the user's call after driving the pad by hand (2026-09-29): countersteering is the
player's skill, not the car's. The mechanism stays in
`TyreVehicleController._update_steering` behind the zero: while the car slides past the tyre's
peak, the fronts would turn towards the travel by this share of the excess. Swept on `ride` before
the call: 0 → 1.5 took 63 kph from 1.43 to 2.60 s above 14° and 86 kph from 1.57 to 3.22 s with the
peak under 40°; 1.0 and 1.25 peaked near 50°. At 1.5 a plain held input held 1.85 / 2.55 / 3.15 s at
42 / 63 / 86 kph, where `hold`'s scripted driver, countersteering on top of it, killed the slide
(0.13 s). At 0, graded the same day:

| entry kph | `ride` longest | `ride` peak | `hold` longest | `hold` peak |
|---|---|---|---|---|
| 42 | 1.63 s | 28.0° | 1.87 s | 25.8° |
| 63 | 1.60 s | 28.5° | 2.55 s | 24.9° |
| 86 | 1.68 s | 30.3° | 1.40 s | 27.5° |

A plain input does not reach the fare's first payment (`drift_min_s` 2.0 s); a player who
countersteers does at 63 kph — the design. Both rows grade this car now. Open: `hold` at 86 kph
(1.40 s) sits under the bar. The handling table's speed-narrowed steering lock was the suspect and
is refuted (`slide_lock_deg` below).

## `assist_drive_fade_from_deg = 35.0`

Where the slide's drive fade starts while the drift assist is on, in place of
`slide_drive_fade_from_deg` (25). At 25 the assisted slide at 86 kph lost its drive at 1.40 s, under
`drift_min_s`; 30° 1.58 s, 32° 3.17 s (a cliff, so 35 sits past it), 35° 3.17 s, with 42 / 63 kph
unmoved. Moved for everyone, 35° raised a plain tap's peak 41.6 → 49.3° at 63 kph and left `turn`
and `hold` identical; kept to the assist on the user's call (2026-10-05), so the off mode keeps the
calmer rear. Refuted at 86 first: the share, `countersteer_lock_deg`, `drift_side_cut_to_kph`,
`turn_drive_cut`, `traction_rearm_s`, `side_force_depth`; `rim_overspeed` 0 works and loses `hold`
(`Q153`).

## `countersteer_lock_deg = 35.0`

Inert while the drift assist is off. Swept 15–60 with it on: flat at 42 / 63 kph and 1.38–1.40 s at
86 under the plain fade band. How far the fronts may turn while the assist
countersteers, where the handling table narrows the player's lock with speed (16.4° at 63 kph). A
slide of 37° needs a front wheel near that angle to point along the travel.

## `slide_lock_deg` — absent, 0.0

The lock the player has on the countersteer side while the car slides past the tyre's peak, where
the handling table narrows it with speed (18.9° at 42 kph, 16.4° at 63, 13.6° at 86). Built on the
suspicion above — a 27° slide needs a front wheel near that angle to point along the travel, and a
countersteer at 86 kph had less to give than the slide asked. Swept on `hold` at all three speeds
(2026-09-29), 0 being the table's lock alone:

| `slide_lock_deg` | 42 kph `hold` / exit | 63 kph `hold` / exit | 86 kph `hold` / exit |
|---|---|---|---|
| 0 | 1.87 s / 50.7 kph | 2.55 s / 45.1 kph | 1.40 s / 71.6 kph |
| 16 | 1.87 s / 50.7 | 2.55 s / 45.1 | 1.40 s / 71.5 |
| 20 | 1.85 s / 53.5 | 2.55 s / 49.0 | — |
| 24 | 0.78 s / 74.2 | 0.75 s / 81.6 | 0.90 s / 91.4 |
| 35 | 0.37 s / 85.6 | 0.37 s / 97.2 | 0.40 s / 102.8 |
| 45 | — | — | 0.33 s / 104.7 |

Refuted: a value under the table's lock is inert, and every value over it SHORTENS the slide at
every speed while the exit speed climbs — the driver catches the slide sooner and the throttle
takes the straightened car away. The reason is the pad's driver, not the tyres:
`skidpad_ablation._countersteer` commands a share of whatever lock the car has (three quarters of
it at 27° of slip), so a wider lock re-tunes the driver, and 35° of lock makes its catch a 26°
countersteer that straightens the car inside a step. `ride` never moves (its steering is held into
the slide, so the lock never widens); `corner`, `brake` and `coast` are unmoved by construction.
Absent, so 0 and inert; the tables above are byte-identical with the mechanism in the tree. Kept
because a player's hands scale to the wheel where the driver's do not, and the user's own drive on
the pad is the only grade that could still want it. 🔴 Do not set it to lift `hold` — the sweep
says it cannot. What limits `hold` at 86 kph is still open; the drive's speed taper is the next
suspect, and the driver itself (a gain in lock shares, a 20° target set by the old lock) is an
instrument to question before another dial is.

## `catch_lock_deg = 6.0`

A cap on the player's countersteer once a caught slide turns the car the other way (`Q152`'s
catch round, the user's street report of 2026-09-30: "the counter steer turn the car to other way
too easily"). The pad found no snap: full opposite lock on gripping tyres turns the car the other
way at about 90°/s once the slide is caught, and a key holds full lock for as long as it is down.
With the throttle held the turn starts only once the wheel is at full lock, so the lock kept is
the lever; the user picked it over a slower countersteer rate and a keyboard ramp in
`InputRouter` (2026-09-30). `TyreVehicleController._cap_catch` latches the side a tail-out slide
went out on and, while the player keeps steering towards it, caps the fronts at this angle from
the tick the heading turns the other way faster than `catch_turn_dps`, for `catch_window_s` after
the tail was last out. It only takes angle away; the catch itself is the player's.

Swept on `--only=catch` at 42 / 63 / 86 kph with `catch_turn_dps` 10 and `catch_window_s` 1.0,
full opposite lock from the slide's peak. `yaw@hold` is the heading swept while the key was held,
positive the other way:

| `catch_lock_deg` | held 1.5 s, 42 / 63 / 86 kph | lifted 1.2 s, 42 / 63 / 86 kph |
|---|---|---|
| 0 | +51.8 / +52.0 / +49.6° | +26.0 / +23.2 / +26.8° |
| 4 | −12.1 / −13.9 / −12.0° | −14.9 / −15.9 / −14.1° |
| 6 | −0.5 / −2.4 / −0.4° | −9.9 / −11.2 / −9.2° |
| 8 | +11.0 / +8.9 / +10.9° | −4.9 / −6.4 / −4.2° |
| 12 | +31.9 / +30.0 / +31.3° | +5.2 / +3.1 / +5.9° |

One value reads the same at every speed: with the throttle held, 6° holds the heading within 2.4°
through a 1.5 s hold where the uncapped car turns 50° the other way. The catch is untouched — the
slip falls under 14° at 0.50–0.53 s against 0.52–0.55 uncapped, the cap engages the tick after the
turn (0.48 / 0.50 / 0.53 s held, 0.37–0.38 lifted), and the slip the other way stays under 1.4° on
every row. It is not a straightening: a capped wheel is still steering, and the turn it keeps is
the everyday one a few degrees of lock give at that speed. With the throttle lifted the cap works
too, which the eval before it expected only of a slower rate. Past the window the lock comes back
at the attack rate: on the 2.5 s hold the fronts are at the table's full lock again and the car
turns the other way (+64.6° at 63 kph with 6°) — a key held a second after the slide is over is a
turn the player asked for.

🔴 A plough at turn-in is past the tyre's peak too, with the travel on the other side of the nose.
Latched on the slip alone, the cap read the player's steering INTO the turn as a countersteer and
capped it (the tap's peak at 42 kph 28.0° → 22.3°); the side latches only while the yaw and the
countersteer's sign disagree, and the tap and `ride` rows are byte-identical with the cap set.
With 6° set, every row but `catch` — `hold` included, 1.87 / 2.55 / 1.40 s — is byte-identical
at all three speeds: the pad's countersteering driver never turns the car the other way, so the
fare's row is not what the cap moves. An early catch (`--catch-at` 2.2 s at 63 kph, 1.6 s at 86)
catches as before and turns 47° / 39° less the other way over a 1.5 s hold (+31.6 → −15.4°,
+14.6 → −24.1°); a late one (`--catch-late` 0.3 s at 63 kph) 45° less over 1.2 s (+42.2 → −3.0°),
`settled` unmoved in both.
Mutated, each guard bites: the trigger's sign flipped caps the catch itself (`capped` 0.02 s,
`settled` 0.50 → 0.67 s), and the latch without the tail-out test brings the plough back (the
tap's peak at 42 kph 28.0° → 22.7°).

Set at 6.0 on the user's call (2026-09-30) rather than held for the drive: the pad passed it on every
row and it touches the spike alone. The drive stays the veto; 0 turns it off.

## `catch_turn_dps = 10.0`

Inert while `catch_lock_deg` is 0. The heading rate the other way that engages the cap. Swept 5 /
10 / 20 / 40 at 63 kph with 6° of cap: engaged at 0.48 / 0.48 / 0.50 / 0.53 s held (0.37–0.40
lifted), the heading at 1.5 s −2.4 / −2.4 / −1.4 / +0.6° — flat, because the heading reverses
sharply once the slide is caught. 10 sits inside the flat band and over a tick's jitter.

## `catch_window_s = 1.0`

Inert while `catch_lock_deg` is 0. How long after the tail was last out the cap may hold. Counted
from the last tail-out tick, about half a second after the wheel goes over, so at 63 kph the full
lock comes back before a 1.2 s hold at 0.5, between 1.2 and 1.5 s at 1.0, and between 1.5 and 2.5 s
at 2.0 (the 1.2 s heading −8.3 / −14.7 / −14.7°). At 1.0 a key still held about 1.4 s after the
countersteer is read as the player's own turn and gets the full lock.
