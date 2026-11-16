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
