# touch.tres

Rationale for `game/tuning/touch.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How far a thumb travels (P2-4). See touch_profile.gd for what each number
means, and Q83 for the scheme these serve.

🔴 THESE ARE A FIRST GUESS AND THE FILE EXISTS SO THEY CAN BE RE-SEEDED. Q83
says no desk can pick them and P2-4's review is blocked on P0-3b for the
handset. Nothing here has been measured against a thumb.

⚠️ DESIGN UNITS, NOT DEVICE PIXELS — the same 1920x1080 frame hud_layout.tres
is written in. On a 2340-wide panel every number here is scaled by the
canvas_items stretch before it reaches a finger — and on a touch screen by
the touch table's 1.25 on top (`Q204`, `hud_layout_touch.md`), so 140 here is
175 desk units of thumb there.

⚠️ EVERY KEY BELOW IS REQUIRED. touch_profile.gd declares no defaults, so a
missing key is a zero rather than something sensible — and a zero travel is a
car at full lock the instant a thumb lands. verify_input.gd refuses one.

## `steer_curve = 2.0`

The steering thumb's response curve (`Q220`, 2026-11-16): the lock is the share of the usable travel
to this power. Was linear (1.0, unstated). The user's report off the handset: "the touch steering is
too sensitive". On the iPhone Air the 140 units of travel are about 11 mm of thumb at the touch
table's 1.25, so linear was a tenth of the lock per millimetre from the first one.

| Share of the travel | 1.0 (was) | 1.5 | 2.0 (ships) |
|---|---|---|---|
| 25% | 25% of the lock | 13% | 6% |
| 50% | 50% | 35% | 25% |
| 75% | 75% | 65% | 56% |
| 100% | 100% | 100% | 100% |

A curve and not a longer `steer_travel_px`: full lock stays where the thumb already finds it, and the
drawn wheel (`TouchSticks`, sized off the travel) does not grow. ⚠️ The cost is the far end: at 2.0
the last quarter of the travel carries 44% of the lock.

🔴 A desk pick, like every number here: no pad row reads a thumb (`tools/skidpad.sh --steer=analog`
steers in shares of the lock, past this table). The handset is the grader. If it is still too quick,
raise this before the travel; if the far end snatches, 1.5.

Steering only; the pedals stay linear.

## `steer_curve_gentle = 2.5`

The same curve for a player who asks OPTIONS for a gentler or a sharper thumb (`Q223`, 2026-11-16):
STEERING RESPONSE is GENTLE / NORMAL / SHARP, and NORMAL is `steer_curve`. `steer_curve_sharp` 1.5
is the alternative `Q220` named and left owed; 2.5 is the same step the other way.

| Share of the travel | sharp 1.5 | normal 2.0 | gentle 2.5 |
|---|---|---|---|
| 25% | 13% of the lock | 6% | 3% |
| 50% | 35% | 25% | 18% |
| 75% | 65% | 56% | 49% |
| 100% | 100% | 100% | 100% |

## `steer_attack_at_top_s = 2.0`

The thumb's slew at speed (`Q230`, 2026-11-16, the user's report: "steer should be stable on
straight high speed roads, esp on touch"). A thumb may add lock no faster than this many seconds to
full with the car at its limiter; the limit grows from none at rest on the square of the car's share
of the limiter, the keyboard's `attack_at_top_s` rule and its value (`Q174`). Easing off, a
countersteer and drift mode pass through. Until it, a thumb reached the car as it read at every
speed, and `keyboard_steer.md` had left the question to the handset; this is the handset's answer.

Swept `tools/skidpad.sh --only=flick --steer=touch --sweep=touch.steer_attack_at_top_s=…`, the
full-lock swap with the throttle held (`flick@held`), peak rear-axle slip:

| Entry | 0 (was) | 1.0 | 1.5 | **2.0** | 3.0 |
|---|---|---|---|---|---|
| 86 kph | 6.8° | 6.9° | 6.6° | 6.3° | 5.6° |
| 95 kph | 9.7° | 9.3° | 8.7° | 6.9° | 5.8° |
| 110 kph | 20.8° | 18.5° | 11.9° | 7.2° | 6.1° |
| 120 kph | 29.8° | 27.9° | 13.0° | 7.2° | 6.2° |
| 150 kph | 31.4° | 32.2° | 11.9° | 7.2° | 6.3° |

2.0 is the first value under the tyre's 8° peak at every speed; 1.5 still lets the tail go. At
63 kph the limit is 0.2 s to full, the rack's own, so nothing changes there. ⚠️ The cost is a
thumb's quick correction at speed: 20% of the lock at 120 kph takes 0.15 s to arrive. A desk pick
on the pad's driver, which slams the lock as no thumb does; the handset grades it. A stick still
passes through as it reads (`InputRouter.steer_from_thumb`).

## `steer_curve_gentle` and `steer_curve_sharp`: the picks

🔴 Desk picks, both: no thumb has driven either. At 2.5 the last quarter of the travel carries 51%
of the lock, which may snatch; if it does, 2.3 before removing the choice. `verify_input.gd` holds
the order — gentle over normal over sharp, none under 1 — and nothing about the values.

## `steer_return_at_top_s = 0.05`

The wheel between touches (`Q238`, 2026-11-17, the user's report: players expect the wheel not to
spring back to centre). A lifted thumb leaves the wheel where it was; it returns in proportion to
the car's speed, this many seconds from full lock at the limiter, and a thumb landing again takes it
up from there. Until it, the steering was zero the tick the thumb lifted.

| Speed (140 kph limiter) | Full lock to centre |
|---|---|
| standing | never: it holds |
| 5 kph | 1.4 s |
| 10 kph | 0.7 s |
| 30 kph | 0.23 s |
| 60 kph | 0.12 s |
| 120 kph | 0.06 s |

Linear in the wheel's position, so on `steer_curve` 2.0 the steering itself is down to a quarter at
half the time. 🔴 A desk pick: lifting the thumb is how a turn or a catch is ended, and the number is
set so that at street pace the return is near the car's own `steer_release_s` (0.08 s). If a lift
at 20–30 kph keeps the car turning, lower it; 0 is the old snap at every speed. No pad row reads it:
the pad steers through the action map and never leaves a wheel turned (`--only=flick --steer=touch`
byte-identical before and after).

## `wheel_radius_px = 77.0`, `wheel_hub_px = 24.0`, `spin_lock_deg = 120.0`

The wheel hangs from the thumb (`Q238`'s amendment, the user's design, 2026-11-17: "since movement of
spin and slide would be the same on top of wheel … place the top of wheel onto the thumb", "then an
intentional spin would be very obvious movement towards bottom of wheel"). Where the thumb lands is
the wheel's twelve o'clock and its middle is 77 units below — the radius it was already drawn at
(0.55 of `steer_travel_px`), about 6 mm on the iPhone Air. The thumb's angle round that middle turns
the wheel, 120° for full lock, the angle the drawn wheel turns; inside 24 units of the middle
nothing is read.

🔴 **A slide along the top is not moved by it, and that is arithmetic, not tuning.** Both readings
go through one dead band and the larger steers. A thumb `x` along the top is `77·atan(x/77)` of rim,
always under `x`, over a rim travel of 161 units against the slide's 140 — so the slide is the
larger at every offset. `verify_input.gd` walks 41 offsets and requires the rim travel over the
slide's: a smaller `wheel_radius_px` or `spin_lock_deg` (under 105° at this radius) breaks it.

| Thumb on the rim | Slide alone | Round the wheel | Steers (curve 2.0) |
|---|---|---|---|
| 1 o'clock (30°) | 20% of the wheel | 22% | 5% of the lock |
| 3 o'clock (90°) | 53% | 74% | 55% |
| 4 o'clock (120°) | 45% | 100% | 100% |
| 6 o'clock (180°) | 0 | 100% | 100% |
| 9 o'clock, by the bottom | 53% the OTHER way | 100% | 100% |

⚠️ Costs. The wheel is drawn under the heel of the thumb, not round it. A thumb landing in the
bottom 6 mm of the glass has its wheel's middle off the screen: it slides, it cannot go round. A
slide that sinks most of a radius while it is out to the side begins to read as a turn — at
`(40, 100)` from the landing it is full lock where the slide alone says 6%. What was wound is
unwound: a thumb gone twice round comes twice back.

🔴 Desk picks, and the third way this was read in a day: the SLIDE / SPIN option and a spin told
from the path's curving (60° of it, which the handset refused: a thumb coming back on itself hooks
through half a turn) are in `Q238`. The fixed wheel (`Q239`) is slid across and never gone round.
