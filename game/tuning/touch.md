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

🔴 Desk picks, both: no thumb has driven either. At 2.5 the last quarter of the travel carries 51%
of the lock, which may snatch; if it does, 2.3 before removing the choice. `verify_input.gd` holds
the order — gentle over normal over sharp, none under 1 — and nothing about the values.
