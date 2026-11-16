# keyboard_steer.tres

Rationale for `game/tuning/keyboard_steer.tres` (`Q119`).

The keyboard's input assist (`Q210`): a key reads 0 or 1, and `InputRouter.steer_for` shapes it
into a linear input before the car sees it. Two layers, never mixed: an input assist per input
method (this table for keys, `touch.tres` for a thumb, nothing for a stick) and the drive assists
per car (`systems/arcade_aids.tres`), tuned against a linear input. A drive assist is never tuned
against a key.

A held key ramps the input from centre to full. Easing off is not shaped (the car's
`steer_release_s` returns the wheel), and a reversal ramps the whole way. A stick past its dead
zone or a steering thumb takes the analogue path; a key press hands it back
(`InputRouter.steer_from_keys`).

- `attack_s` 0.2: seconds to full at rest, and whenever the car asks for the quick ramp (drift
  mode, or the countersteer side of a slide: `_wants_quick_steer`). Equal to `handling.tres`'s
  `steer_attack_s`.
- `attack_at_top_s` 2.0 (`Q174`): seconds to full at the limiter. The ramp blends from `attack_s`
  on the square of the share of the limiter, as yaw grows with v². Full lock in one tick slides
  the car above about 95 kph: `flick@held` at 110 kph peaks at 20.8° slip at 0.2 s against 6.3°
  here. Graded on `tools/skidpad.sh --only=flick` at 95 / 110 / 120 kph; sweep as
  `--sweep=keyboard_steer.attack_at_top_s=…`.
- `curve` 1.0: the slow ramp's shape, the linear progress to this power. Kept linear: 2 buys the
  lane change 0.3–0.4° and costs the keyboard flick at 63 and 86 kph, because an eased crossing
  reaches the other side past `flick_window_s`. The quick ramp is always linear.
