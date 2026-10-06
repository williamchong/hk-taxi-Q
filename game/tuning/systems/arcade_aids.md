# arcade_aids.tres

Rationale for `game/tuning/systems/arcade_aids.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The game's own aids, which no real car has, grouped so they are never mistaken for one of the car's systems: the rear side cut that starts the drift, the flick that engages drift mode as the button does, the slide lock, and the cap on a caught slide's countersteer (`CatchLimiter`). Pillar 2's ease is layered on the real car here, never by bending a physical number (`GAME_DESIGN.md`). `slide_lock_deg` is absent because it is 0.0 — Godot's writer drops a value equal to the type's zero — and `drift_side_cut_fast` the same.

⚠️ The sections below moved here from `tyre.md` when the dials became the car's systems (`Q155`,
2026-10-05); their prose keeps the names the dials had when it was written: unchanged; "traction control off" means drift mode engaged.

## `drift_side_cut = 0.6`, `drift_side_cut_from_kph = 42.0`, `drift_side_cut_to_kph = 105.0`

**Tried without it and kept (2026-10-06, `Q156`)** — the last force on the car that no car has,
and the question was whether a road tyre's weight transfer and the handbrake now start the slide
alone. At pace 1.5, 42 / 63 / 86 kph, cut 0 / 0.3 / 0.6: the tap still slides (peak 29.5 / 18.8 /
18.6° at 0) and `hold` is longer at 42 (3.15 s against 1.93), but the turn under-rotates —
`turn@off` comes out at 59 / 78 / 146° at 0 and 72 / 151 / 155° at 0.3, against 91 / 97 / 110° at
0.6. The handbrake does not buy it back: `lock_ratio` 1.3 / 1.6 / 2.0 with the cut at 0 gives 56 /
58 / 70° at 42 kph and scatters the faster rows (119 / 91 / 76° at 63, a 130° tap at 86 at 2.0).
🚫 Left: a limited-slip differential, which is what a real drift car has here. It couples the two
rear wheels' spin, so it is a joint solve in `_solve_spin` — new machinery in the model's most
fragile part — and it does nothing while the handbrake holds both wheels, which is when the
turn's first 45° is made.

**The band ends at 105 kph since 2026-10-06** (`Q153`), with the drive sized on the rim's speed.
The band ended at 65 because "0.6 at 63 kph spins the car"; that spin was the engine handing a
spinning wheel more power than it has. On the engine's real power the tap at 63 kph no longer
slid at all with the band to 65 (13.8°, under the 14° a slide is). Swept 65 / 85 / 105 / 140 at
50 / 63 / 75 / 86 kph — tap peak 26.8 / 13.7 / 18.1 / 27.1° at 65, 34.0 / 26.8 / 21.3 / 27.1° at
105, 36.4 / 31.1 / 27.8 / 27.7° at 140 — and a cut at every speed (`to` 0) against 65 at 105 kph:
the tap 69.8° against 54.3°, over the 60° bar. So 105: the tap starts at every speed from 30 to
105 and spins at none of them; `hold` 3.43 / 3.35 / 3.13 / 2.98 s. At 86 kph the band reads the
same at every end: the handbrake has the rears under what the cut would leave. The slips below
are the centre of mass's, as read before that day.

The 90° drift (`Q153`, the user's street report of 2026-10-02). The cut caps the rears' sideways
force at a share of what the turn asks while the button is engaged, so the slide starts inside the
corner (0.57 s and 54° of heading at 42 kph, from 2.1 s and 181°); it is latched at the press and
eases to `drift_side_cut_fast` (absent, 0) by 70 kph, because 0.6 at 63 kph spins the car and 0.2
at 86 does. The re-arm brings traction control back the tick the steering is let go, which is the
ending: settled at 81–85° at 42 kph and 83–91° at 63 on the pad's `turn` row (96–107° at 63 with
the band to 70). It fires once the player has steered since the press, whichever came first. Graded on `turn`
(start and settled heading) with `hold` and `ride` as the guard. The band ended at 70 kph first; 65 since the
user's second street drive ("sometimes the rear feels too spinny"), with the fade below.

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

🔴 **That table is the `mu` 2.0 car's, and the tail no longer comes round** (bisected 2026-10-07,
`Q153`). The trigger still fires and stands traction control down, but on the real car the slide
it frees stays under `drift_slip_threshold_deg` at 63 / 86 kph, so it pays nothing. It went with
the Crown Comfort's chassis (`1876da9`), not with a dial, and no commit since has brought it back.
Peak slip from the turn-in, the current pad graded on each commit, 42 / 63 / 86 kph:

| commit | `flick@lift` | `flick@brake` (63 / 86) |
|---|---|---|
| `47afca8`, `mu` 2.0 (the table above, re-read at the rear axle) | 41.4 / 37.5 / 34.4° | 39.5 / 37.7° |
| `e1ffcf4`, `mu` 1.0 | 53.3 / 53.4 / 98.7° | 52.4 / 110.2° |
| `1876da9`, the Crown Comfort's chassis | 3.6 / 5.5 / 36.5° | 6.7 / 33.1° |
| `b8aaa56`, its power curve | 179.3 / 11.5 / 23.5° | 58.1 / 30.4° |
| `620c4c4`, the slip cut from 10° | 51.8 / 11.5 / 17.9° | 29.9 / 18.9° |
| `5ec326d`, the drive on each wheel's speed | 19.1 / 7.0 / 14.3° | 7.8 / 13.5° |
| `d3eeca9`, pace 1.5 (shipped) | 3.7 / 12.3 / 9.7° | 19.1 / 10.7° |

Stability control's yaw brake is not it: `--sweep=stability_control.yaw_brake_lock_ratio=0,1.5`
leaves every flick row byte-identical. The trigger takes traction control alone, never the side
cut (the button's), so the feint's weight transfer is all that moves the rear, and on a 1.0 g
tyre at the real drive that is a few degrees. Open, not measured shut: whether the flick should
be made to slide again is the user's call (`Q153`).

## `steer_to_grip = 1.0`

🔥 **`drive_boost` is retired (2026-10-06, `Q156`)**: half as much drive again, on the road only,
fading with the steering — a force no car has, standing in for a game that wanted to be quicker.
The pace (`pace.tres`) is that dial now, for the whole car at once. At pace 1.5 with the boost at
0 / 0.5: 80 / 97 kph after 4 s and 122 / 148 after 8 (pace 1 with the boost: 68 / 108), and every
drift row within 0.1° and 1.6° of heading at 42 / 63 / 86 kph, since drift mode never had it. The
field and its code are gone; the paragraphs below that name it are the record of why it existed.

**Both since 2026-10-06, on the user's drive** ("i cant even throttle and turn at 50kph, it just
slide out", then "we need faster acceleration"). Measured on the pad, the full-throttle full-lock
`corner` at 50 kph: the speed-narrowed lock put the fronts at 22.9° on a road tyre that peaks at 8°
of slip — front tyres at 2.54× their grip, the car ploughing wide at 24 m and shedding speed, with
the marks and smoke of a slide. `steer_to_grip` 1.0 caps full input at the angle the tyres can use
(16° at 50 kph, 11° at 80): front use 1.64, the car holding 54 kph on the same radius — the radius
is the road tyre's (about v² ÷ g), which no steering changes. Swept 0.8 / 1.0 / 1.2: 0.8 put the
plain tap at 42 kph to 102°. **Lifted while drift mode is engaged** (the user's question of what
the cap does to a drift's start): capped through the press, the tap at 42 kph read 83–85° where it
reads 69° without the aid; lifted, every drift row is the aid-off row's to a tenth.

**Lifted on the countersteer side of a slide alone since later that day** (`Q153`). It first stood
aside for any rear slip past the tyre's peak, whichever way the player steered, so a power-on
corner's slight slide sent the fronts from the grip lock to the table's (12.5 → 17.5–19.7° at
63 kph with the understeer cut at 0, front use 2.2 → 3.3×) and the car ploughed — the cascade both
closed-loop understeer trials ran into. A tail out only adds to the fronts' slip on the turn's
side, so the cap holds there: 12.4° and 2.3× on the same row. The shipped car's pad is unmoved but
for the held-throttle flick at 86 kph (35°/s against 28 in its second second, peak slip 28.3°
against 20.6); 🔴 grade a change to the lift on `--only=technique` with
`--sweep=stability_control.understeer_power_cut=0,0.5` — at 0.5 alone the rear never reaches the
peak in `corner` and the row cannot see it.

`drive_boost` 0.5, the user's pick from 0 / 0.25 / 0.5 / 1.0 (0–100 kph ≈ 10 / 7.9 / 7.1 / 6.1 s;
69 kph after 4 s and 109 after 8 at 0.5, against 57 / 89). The launch is the rear tyres' grip
under traction control, so past 0.25 the first seconds barely move. Unfaded it spun every tap
(162°) and put the rears at 1.54× their grip in the 42 kph corner; so it is **off in drift mode**
and **fades with the steering**, whole straight and gone at full lock. Faded: the corner's rears at
0.65 / 0.66 / 0.72 / 0.88× at 42 / 50 / 63 / 86 kph, every drift row as without it.

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
