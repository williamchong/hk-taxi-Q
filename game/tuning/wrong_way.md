# wrong_way.tres

When the wrong-way sign goes up and comes down (`Q81`, `P5-26`). Its look is `hud_style.tres`'s
`warn_*` keys.

Every key is required: `wrong_way_profile.gd` declares no defaults and the monitor refuses a zero
dwell or bar. `verify_hud.gd` asserts the two angle bars are 120 and 90 and not one number.

- `raise_s = 0.5`: seconds, like `street_tracker.tres`. Covers a junction mouth driven straight
  through; about 7 m at 50 kph.
- `clear_s = 0.8`: longer than the raise on purpose. Driving the wrong way through a junction
  hands the monitor the cross street for a moment, and a symmetric clear would blink the sign off.
- `angle_deg = 120.0`: the nose against the legal direction. Not 90: a legal turn across a one-way
  street passes through perpendicular. The region is 93.5% one-way by length, so the false alarm
  is the failure mode.
- `min_kph = 10.0`: below this velocity is noise, so a slow car cannot be "already correcting" and
  the sign stands.
- `correcting_angle_deg = 90.0`: travel within this of the legal way withholds the sign (reversing
  out of a mistake). A second bar on purpose: at 120 a car pointed backwards while sliding
  sideways counted as correcting.
