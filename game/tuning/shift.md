# shift.tres

The shift's clock hours (`Q162`), read by `day_clock.gd` in `Mode.SHIFT` for the HUD clock. The
shift's length is not here: it is `day_to_night.tres`'s `length_s` (840 s), so the clock and the
sky end on the same game second. `--shift-s=<seconds>` compresses a whole shift. Both keys are
required (`shift_profile.gd` declares no defaults).

- `opens_h = 7.0`: the rig opens on the authored daylight; there is no dawn keyframe before it.
- `closes_h = 21.0`: an hour after the rig reaches full night at 20:00, so every shift ends in the
  dark. 14 game hours over 840 s is a clock minute per second driven (`Q233`).
