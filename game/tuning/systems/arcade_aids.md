# arcade_aids.tres

The game's own aids, which no real car has, kept apart from the car's systems (`Q155`): the rear
side cut that starts a drift, the flick that engages drift mode, the steering cap, and the cap on
a caught slide's countersteer (`CatchLimiter`). Ease is layered on the real car here, never by
bending a physical number. `Q152`, `Q153` and `Q156` hold the sweeps.

`slide_lock_deg` and `drift_side_cut_fast` are absent from the file because both are 0.

## `drift_side_cut = 0.6`, `drift_side_cut_from_kph = 42.0`, `drift_side_cut_to_kph = 105.0`

While drift mode is engaged the rears' sideways force is capped at a share of what the turn asks,
so the slide starts inside the corner. Latched at the press, full strength up to 42 kph, easing to
`drift_side_cut_fast` (0) by 105 kph. Letting the steering go re-arms the aids, which ends it.

- Kept, not removed (`Q156`): without it the turn under-rotates or scatters. `turn@off` comes out
  at 59 / 78 / 146° at 42 / 63 / 86 kph with the cut at 0, against 91 / 97 / 110° at 0.6, and a
  stronger handbrake (`lock_ratio` 1.3–2.0) does not buy it back.
- Not built: a limited-slip differential, the real answer. It is a joint solve in `_solve_spin`,
  and does nothing while the handbrake holds both rears.
- The band ends at 105 (`Q153`): ending at 65, the tap at 63 kph no longer slid (13.8°). A cut at
  every speed puts the tap at 105 kph over the 60° bar (69.8°).
- Grade on `turn` (start and settled heading) with `hold` and `ride` as the guard.

## `flick_window_s = 0.6`, `flick_feint_s = 0.2`, `flick_min_kph = 30.0`, `flick_input_share = 0.5`

The flick (`P3-54`, `Q153`), read by `FlickWatch`: steering held past `flick_input_share` to one
side for `flick_feint_s`, with the throttle under that share or the brake touched, then past the
share on the other side within `flick_window_s`, at `flick_min_kph` or faster. Drift mode then
engages as on the handbrake's press. `flick_window_s` 0 is no flick.

- A trigger and not a dial: every lever that let the rear go on a flick let it go on a plain
  corner too. A plain corner never reverses the steering. The lift or brake is required so a
  held-throttle slalom stays a grip manoeuvre.
- `flick_window_s` is 0.6 (`Q210`) because a key now reaches the car as a linear input
  (`keyboard_steer.tres`) and takes 0.38–0.54 s to cross at 63–86 kph; at 0.3 the flick stopped
  firing on keys. A drive assist is tuned against a linear input, never a raw key.
- Open (`Q153`): on the road tyre the flick only frees traction control, and the slide it leaves
  is small: `flick@lift` peaks 3.7 / 19.2 / 9.3° at 42 / 63 / 86 kph, over the 14° threshold at 63
  alone. Whether it should slide more is the user's call.

## `steer_to_grip = 1.0`

Caps full steering input at the angle the front tyres can use (16° at 50 kph, 11° at 80). Without
it full lock at 50 kph put the fronts at 22.9° on a tyre that peaks at 8°, and the car ploughed.
0.8 put the plain tap at 42 kph to 102°.

- Lifted while drift mode is engaged, so a drift's start is unchanged.
- Lifted on the countersteer side of a slide only. Lifted for any rear slip, a power-on corner's
  slight slide widened the lock and the car ploughed.
- Grade a change to the lift on `--only=technique` with
  `--sweep=stability_control.understeer_power_cut=0,0.5`; at 0.5 alone `corner` cannot see it.

## `slide_lock_deg` (absent, 0.0)

Extra lock on the countersteer side during a slide. Inert at 0. Do not set it to lengthen `hold`:
every value over the table's lock shortens the slide at every speed (24° gives 0.78 / 0.75 /
0.90 s at 42 / 63 / 86 kph against 1.87 / 2.55 / 1.40 s), because the pad's driver steers in
shares of the lock. Kept for a player's hands, which the pad cannot grade.

## `catch_lock_deg = 6.0`, `catch_turn_dps = 10.0`, `catch_window_s = 1.0`

A cap on the countersteer once a caught slide turns the car the other way (`Q152`, the user's "the
counter steer turn the car to other way too easily"). `TyreVehicleController._cap_catch` latches
the side a tail-out slide went out on. While the player keeps steering towards it, the fronts are
capped at `catch_lock_deg` from the tick the heading turns the other way faster than
`catch_turn_dps`, for `catch_window_s` after the tail was last out. It only takes angle away; the
catch is the player's. A drive assist for every input method (`Q210`). 0 turns it off.

- 6° holds the heading within 2.4° through a 1.5 s held countersteer at 42 / 63 / 86 kph; uncapped
  the car turns 50° the other way; 4° gives −12°, 8° gives +11°.
- The side latches only while the yaw and the countersteer's sign disagree. Latched on slip alone,
  a plough at turn-in read as a countersteer and the cap cut the player's steering into the turn.
- `catch_turn_dps`: flat from 5 to 40; 10 is over a tick's jitter.
- `catch_window_s`: at 1.0 a key still held about 1.4 s after the countersteer is read as the
  player's own turn and gets full lock back.
- Re-measure with `tools/skidpad.sh --only=catch`.
