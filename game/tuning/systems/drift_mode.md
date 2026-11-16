# drift_mode.tres

A real car's drift mode (`Q155`, `DriftMode`): traction control and stability control's understeer
cut stand down from the handbrake's press, or a flick (`arcade_aids.md`), until the slide is over.

- `rearm_s = 2.0`: the aids re-arm once the button has been up this long and the body's slip is
  under the 14° threshold. At 1.0 a player's `ride` at 42 kph slid 0 s, because the governor came
  back and cut the power the slow slide needed; at 2.0 it slides. 3.0 reads the same. Runs at the
  pace (`pace.md`).
- `rearm_on_steer_release = true`: letting the steering go re-arms at once, which ends the drift.
  Graded with `arcade_aids.md`'s `drift_side_cut`.
