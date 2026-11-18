# touch.tres

How a thumb is read (`P2-4`, scheme `Q83`); `touch_profile.gd` documents each field. Every value
is a desk pick: no skidpad row reads a thumb, and the handset is the grader (`P0-3b`).

Design units, not device pixels: the 1920x1080 frame `hud_layout.tres` uses, scaled by the
`canvas_items` stretch and, on a touch screen, by the touch table's 1.25 (`Q204`,
`hud_layout_touch.md`). Every key is required: `touch_profile.gd` declares no defaults, and a zero
travel is full lock the instant a thumb lands. `verify_input.gd` refuses one.

- `steer_travel_px = 140.0`: sideways travel for full lock, a quarter of the left zone's width.
  About 11 mm of thumb on the iPhone Air.
- `drive_travel_px = 110.0`: vertical travel for full throttle or brake. One number for both
  halves of the one longitudinal axis (`Q83`).
- `jitter_deadzone_px = 6.0`: a resting thumb's tremor, clipped as a distance. Not the action
  map's 0.2 deadzone; touch does not go through the action map (`Q97`).
- `steer_curve = 2.0` (`Q220`): lock is the share of travel to this power, so half the travel is a
  quarter of the lock. The user found linear "too sensitive". A curve, not a longer travel, so
  full lock stays in reach and the drawn wheel does not grow. Cost: the last quarter of travel
  carries 44% of the lock. Steering only; the pedals stay linear.
- `steer_curve_gentle = 2.5`, `steer_curve_sharp = 1.5` (`Q223`): the OPTIONS menu's STEERING
  RESPONSE; NORMAL is `steer_curve`. At 2.5 the last quarter carries 51% of the lock; if it
  snatches, try 2.3 before removing the choice. `verify_input.gd` holds the order (gentle over
  normal over sharp, none under 1).
- `steer_attack_at_top_s = 2.0` (`Q230`): a thumb may add lock no faster than this many seconds to
  full at the limiter; the limit grows from none at rest on the square of the speed share, the
  keyboard's `attack_at_top_s` rule (`Q174`). Easing off, a countersteer and drift mode pass
  through, and a stick is not limited (`InputRouter.steer_from_thumb`). 2.0 is the first value
  that keeps a full-lock swap at 110–150 kph under the tyre's 8° peak (7.2° rear slip; 1.5 gives
  11.9–13.0°, none gives 20.8–31.4°). Cost: 20% of lock at 120 kph takes 0.15 s to arrive. Sweep
  with `tools/skidpad.sh --only=flick --steer=touch --sweep=touch.steer_attack_at_top_s=…`.
- `steer_return_at_top_s = 0.05` (`Q238`): a lifted thumb leaves the wheel where it was. It
  returns in proportion to speed, this many seconds from full lock at the limiter (never at rest,
  0.7 s at 10 kph, 0.23 s at 30, 0.06 s at 120), and a landing thumb takes it up from there. If a
  lift at 20–30 kph keeps the car turning, lower it; 0 snaps to centre at every speed.
- `wheel_radius_px = 77.0`, `wheel_hub_px = 24.0` (`Q238`, the user's design): the wheel hangs
  from the thumb. The landing point is twelve o'clock and the wheel's middle is 77 units below
  (0.55 of `steer_travel_px`). Inside 24 units of the middle no bearing is read.
- `spin_lock_deg = 180.0` (`Q251`, the user's call): the steering thumb either SPINS the wheel or
  SLIDES across it, the player's pick on CONTROLS (方向盤), spin by default, the same under either
  anchor — never a switch between the two mid-stroke (that was `Q243`'s `spin_enter_deg`, gone).
  - Spun: the wheel turns with the thumb's angle round its middle, full lock at 180° (the bottom),
    so the drawn rim keeps up with the finger. Relative, the thumb lands on twelve o'clock and the
    wheel takes up from where it was. A move through the hub turns nothing.
  - Spun and fixed (`Q239`): a push. Down on the wheel's left, up turns right and down turns
    left, `steer_travel_px` each way to full lock; along its top it is a slide. The wheel is
    taken up from where it was, never jumped to the thumb.
  - Slid: the thumb's sideways offset alone, at any height, `steer_travel_px` to full lock.
  - Lower `spin_lock_deg` for a quicker spin (90 is lock at three o'clock); it is also the angle
    the drawn wheel turns at full lock on a slid wheel.

The handbrake threshold and its hysteresis are not declared (`Q83`, deferred by `Q97`).
