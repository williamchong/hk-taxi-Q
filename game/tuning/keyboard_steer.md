# keyboard_steer.tres

Rationale for `game/tuning/keyboard_steer.tres`. Each heading is the line the block sat above; `Overview` is
the file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The keyboard's input assist (`Q210`): a key reads 0 or 1, and `InputRouter.steer_for` shapes it into
a linear input before the car sees it. **Two layers, never mixed** (the user's call, 2026-11-14): an
input assist per input METHOD (this table for keys, `touch.tres` for a thumb, nothing for a stick,
a wheel's own table when there is one), and the drive assists per CAR (`systems/arcade_aids.tres`,
the systems' tables), tuned against a linear input. A drive assist is never tuned against a key.

Shaped: a held key ramps the input from centre to full; easing off or letting go is not shaped (the
car's own `steer_release_s` returns the wheel), and a reversal ramps the whole way, as the car's
rack did when it carried this ramp. The car asks for the quick ramp (`attack_s`) in drift mode and
on the countersteer side of a slide, off the key's own side (`_wants_quick_steer`). A stick past its
dead zone or a steering thumb hands the steering to the analogue path, which passes through as it
reads; a key press hands it back (`InputRouter.steer_from_keys`).

## `attack_s = 0.2`

Seconds to full at rest, and whenever the car asks for the quick ramp. The car's rack is the same
0.2 s (`handling.tres` `steer_attack_s`), so at rest a key steers as it did before `Q210` to the tick.

## `attack_at_top_s = 2.0`

Moved here from `handling.tres`'s `steer_attack_at_top_s` (`Q174`, built 2026-10-29, `Q210` moved it,
2026-11-14), unchanged. The seconds to full blend from `attack_s` at rest to this at the limiter on
the SQUARE of the share of the limiter, as the yaw a swing of the wheels puts in grows with v² —
0.28 s at 42 kph, 0.38 at 63, 0.54 at 86, 0.75 at 110 on the pace-2.0 limiter of 198 kph.

Why, from `Q174` (the user's report: "taxi cant steer properly at highspeed (>60 <120) and start
sliding, even without pressing drift"): a full-lock lane change with the throttle held,
`--only=flick`'s `flick@held`, peak slip at 0.2 s everywhere against 2.0:

| Entry | 0.2 s | 2.0 s |
|---|---|---|
| 95 kph | 9.7° | 5.9° |
| 110 kph | 20.8°, 22 kph shed | 6.3°, 8 kph gained |
| 120 kph | 29.8°, 30 kph shed | 6.5° |

🔴 That table was a KEY's: full lock in one tick is what slid the car. A thumb or a stick has no
such ramp since `Q210`; whether one slams full lock at 110 kph is the handset's question, and if it
does, the answer is the touch table's, not a car dial. Graded on `--only=flick` at 95 / 110 / 120 kph
(`tools/skidpad.sh` steers as a key unless `--steer=analog`), sweep it as
`--sweep=keyboard_steer.attack_at_top_s=…`.

## `curve = 1.0`

The slow ramp's shape: the input is its linear progress to this power, so 2 eases out of centre (a
0.1 s tap at 86 kph is 3% of the input against 19% at 1) while a held key reaches full in the same
seconds. The quick ramp stays linear. Added and swept 2026-11-14 on the user's question (linear,
quadratic or exponential); exponential — a first-order lag, a big first step that never reaches full
— was not built: it is the twitch the slow ramp is there to stop.

Swept `--sweep=keyboard_steer.curve=1,1.5,2`, the full pad at 42 / 63 / 86 kph and `--only=flick` at
95 / 110 / 120:

| row | 1 | 1.5 | 2 |
|---|---|---|---|
| `flick@held`, 110 / 120 kph peak slip | 6.3 / 6.5° | 6.0 / 6.2° | 6.0 / 6.1° |
| `corner` yaw over 4 s, 63 kph | −194.5° | −190.3° | −187.3° |
| `flick@lift`, 63 kph | 15.7° | 4.3° | 4.4° |
| `flick@brake`, 63 / 86 kph | 25.7 / 10.0° | 25.0 / 4.5° | 4.0 / 4.5° |

`turn`'s `came out` within 1.1°, `hold`'s `longest` within 0.03 s, `catch`'s `yaw@hold` within 1.2°
at every value. Kept at 1: the curve buys the lane change 0.3–0.4°, where the key is already held at
6°, and costs the keyboard flick at 63 and 86 kph again — an eased crossing reaches half the other
side later (at 71% of the ramp at 2), past `flick_window_s` 0.6. What it would buy, a smaller
correction from a short tap, no pad row reads; that is a keyboard street drive's call, with the
window re-swept beside it.
