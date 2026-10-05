# tyre.tres

Rationale for `game/tuning/tyre.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The per-wheel tyre model's table (`P3-52`, `Q152`): built as the spike that asked whether a
drift can be physical on `VehicleBody3D`, and the game's car since 2026-10-03 (`city_drive.tscn`
instances `taxi_tyre.tscn`). Read by `TyreVehicleController` alone. "The shipped car" below is the
car before it — `taxi.tscn` on the engine's tyres, the pad's control until it was dropped on
2026-10-05. Every value was graded on `tools/skidpad.sh --entry-kph=` at 42, 63 and 86 kph (on
`skidpad_tyre.tscn` before that day, the same pad with this car on it), and `Q152` holds the
tables.

⚠️ `substeps`, `mu`, `slide_ratio`, `peak_slip_ratio`, `peak_slip_angle_deg`,
`wheel_inertia_kgm2`, `low_speed_mps` and `drive_scale` are required: `tyre_profile.gd` declares no
defaults, and a zero parks the car (`TyreVehicleController.usable`). `yaw_assist_scale` (a share
of the engine-tyre car's drift yaw torque) and `handbrake_declutch` went with that car on
2026-10-05: both were 0 / off, the torque not rescuing the low end, the declutch only a harsh brake
(`Q153`). `countersteer_assist` and `assist_drive_fade_from_deg` are the drift assist's, inert
while `TyreVehicleController.drift_assist` is off — the player's option since `P3-56`, on by
default in the game and off on the pads (`--assist=on` turns it on there).
`slide_lock_deg` is absent because it is 0.0 — Godot's writer drops a value equal to the type's
zero — refuted on the pad's driver and kept for the user's own drive; its section keeps the
sweep. `catch_lock_deg` is set at 6.0 on the user's call (2026-09-30), ahead of their drive, which
stays the veto.

## `mu = 1.0`

A road tyre's grip (`Q153`, the user's call 2026-10-05, with `drive_scale` and
`handbrake_torque_nm` below). Pillar 2 asks for a car that is easy to drive, not for unrealistic
grip: the ease is the hidden aids'. The car still carries `gravity_scale` 1.6, so the tyres hold
about 1.6 g where a road car holds 0.9. Gravity at 1.0 or 1.3 was measured the same day and refused: with the
handbrake at the same share of the lock, every tap spins and `corner` runs twice as wide (`Q153`).

What a road tyre gives that 2.0 could not: weight transfer moves the rear. At 2.0 a corner left
the tyres about 3.2 g, so a lift or a feint never took the rear under what the turn asked, and no
single dial gave a flick while `corner` gripped (`Q153`'s nine levers). At 1.0 the lifted flick
slides on physics alone, 44 / 48° at 42 / 63 kph (31–34° at 2.0, and those only because the flick
trigger stood traction control down).

⚠️ **1.0 alone spins the car** (2026-10-05, `mu` 1.0 with the rest as at 2.0): the tap and the
lifted flick peak at 168–180° at 42, 63 and 86 kph, the plain `corner` slips 12 / 16 / 23°. Not
answered by any stability dial: `turn_drive_cut` 0.8 / 1.0, `slide_drive_fade_from_deg` 10 / 15 /
20, `traction_limit` 0.5 / 0.75, `drift_side_cut` 0.2 / 0.4, the drift assist and the body's
gravity at 1.0 each left the tap at 164–168°. The spin was the two torques sized for 2.0 —
`drive_scale` and `handbrake_torque_nm` — on a tyre with half the force to answer them. Refused
before at 2.0's drive (`Q153`, 1.0 and 1.25) for the same reason.

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
(start and settled heading) with `hold` and `ride` as the guard. The band ended at 70 kph first; 65 since the
user's second street drive ("sometimes the rear feels too spinny"), with the fade below.

## `slide_drive_fade_from_deg = 25.0`, `slide_drive_fade_to_deg = 40.0`

The forward drive fades out over this band of body slip while traction control is disarmed, so a
held throttle cannot spin the car (`Q153`, the user's street report). A plain held tap peaked 30.7 /
47.8 / 65.1 / 49.7 / 50.0° at 42 / 50 / 63 / 75 / 86 kph; with the band and the cut ending at 65 kph,
29.0 / 35.7 / 41.6 / 35.3 / 34.5°. `hold` never reaches the band (peak 23–27°) and is unchanged, as
is the `turn` row at 42 kph. 30 → 40–50 left 63 kph at 50–53°; no existing dial did it
(`rim_overspeed` 0 calms 75–86 kph and loses `hold` at 86; `traction_rearm_s` moves nothing).

## `handbrake_torque_nm = 2000.0`

Over the rear wheels' lock at `mu` 1.0 (capacity ≈ 4,700 N × 0.35 m ≈ 1,650 N⋅m per wheel), so the
button still locks them, by less than 3,000 did: about 1.2 × the lock, the gentle end of a
rally hydraulic handbrake, which is built to lock the rears at once with margin (kept on the
user's call after asking). Swept 1,000 / 1,500 / 2,000 at `mu` 1.0 and
`drive_scale` 1.0 (2026-10-05): the tap peaks 69 / 62 / 53° at 42 kph and 47–48° at 63 at all
three; 2,000 is the only value bringing the countersteered `turn` out inside 80–110° at both 42 and
63 kph (100 / 96°; 158 / 70° at 1,000) and gives `hold` 3.40 / 3.12 s there. At 3,000 the tap
spins at 63 and 86 (164 / 168°).

At `mu` 2.0 it was 3,000 (capacity ≈ 3,300 N⋅m): swept 1,500–4,000 on `hold`, 3,000 the best at 63
kph, 4,000 killed the slide there and helped it at 86.

## `low_speed_mps = 3.0`

The floor under which slip is measured against 3 m/s rather than the wheel's own speed, so a car
at rest does not read an infinite slip.

## `substeps = 8`

The spin solve's steps a tick. At 8 the residual stays monotone (the wheel's inertia term outweighs
the tyre's falling slope); at fewer it may not, and the safeguarded Newton then bisects.

## `drive_scale = 1.0`

The handling table's drive, unscaled: at `mu` 1.0 it spins the rears, which is all 2.0 was for
(`Q153`, 2026-10-05). The pace is the old car's again — 0 to 63 kph in about 4 s, not 2 — and the
user's call that kept the faster taxi is reversed with it. At `mu` 1.0, 1.5 spins every tap (168°)
and the lifted flick (158–168°); 1.0 keeps `corner` at 1.5–4.2° of slip, its exit 43 / 52 / 66 kph
from 42 / 63 / 86.

At `mu` 2.0 it was 2.0, the spike's finding in one number: at 1.0 the rears could not be spun and
no row held a slide, at 3.0 the 86 kph slide spun, and 1.5–1.75 lost the tap (`Q153`'s `liftoff`
round). The car then ran up to 119 kph in 4 s, which `turn_drive_cut` (`P3-55`) answered.

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

## `flick_window_s = 0.3`, `flick_feint_s = 0.2`, `flick_min_kph = 30.0`, `flick_input_share = 0.5`

The flick (`P3-54`, `Q153`), read by `FlickWatch`: the steering held past `flick_input_share` to
one side for `flick_feint_s` with the throttle under that share or the brake touched at some point
of it, then past the share on the other side within `flick_window_s` of leaving the first, at
`flick_min_kph` or faster. On that tick traction control stands down as the drift button's press
does, and comes back the same ways (the steering let go, or `traction_rearm_s` and the slip under
the bar); it never fires while traction control is already off. `flick_window_s` 0 is no flick.

Why traction control and not a dial: nine levers swept on the pad (`Q153`) — every one that let
the rear go on a flick (traction control off, a raised centre of mass, a lower `mu`) let it go on a
plain corner too, and none that spared the corner freed the flick. A plain corner never reverses
the steering, so a trigger on the reversal leaves it alone by construction. The lift or the brake
is required because the real flick has one (`Q153`'s research) and because a held-throttle slalom
must stay a grip manoeuvre.

The values are first choices, set before the pad and not swept: 0.2 s is under the pad's 0.35 s
feint and well over a key's bounce; 0.3 s covers a keyboard's instant switch and a touch thumb
crossing the centre; 30 kph is the button's own start floor (`Q153`: the tap slides from 30); 0.5
is half an analogue input, the whole of a key. Graded 2026-10-05, `--sweep=flick_window_s=0,0.3`,
peak slip after the turn-in, assist off / on (without the flick in brackets); every other row on
the pad — `corner`, `liftoff`, `tap`, `turn`, `hold`, `ride`, `catch`, the walls, the handbrake and
the trail-brake — byte-identical between 0 and 0.3, in both modes:

| entry kph | `flick@lift` | `flick@brake` | `flick@held` |
|---|---|---|---|
| 42 | 34.4 / 38.8° (7.8 without) | no fire: the brake takes it under 30 kph | no fire, by design |
| 63 | 32.7 / 39.3° (5.0) | 33.9 / 39.5° (5.5) | no fire |
| 86 | 31.1 / 38.4° (1.3) | 33.5 / 39.7° (3.3) | no fire |

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
