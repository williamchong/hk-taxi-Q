# traction_control.tres

A real car's traction control: a driven wheel's torque is cut once it spins past the tyre's grip.
Drift mode stands it down for a slide the player asked for (`drift_mode.md`).

- `wheelspin_limit = 1.0`: the cut starts at peak wheelspin, so full throttle at full lock grips
  (peak slip 2.5° against 82° without). Forward slip only: keyed on combined slip it cut the drive
  at every cornering limit.
