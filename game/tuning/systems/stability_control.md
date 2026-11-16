# stability_control.tres

Stability control (`Q155`): takes engine torque away when the car runs wide or its tail swings
out, and brakes one wheel to turn the car back. Every slip here is the rear axle's
(`VehicleController.rear_axle_velocity`, `Q153`). `Q153` and `Q156` hold the sweeps.

- `understeer_power_cut = 0.5` (`P3-55`): the share of drive taken off at full lock while traction
  control is armed (Bosch's enhanced understeer control, open loop). With it a full-throttle
  corner holds 0.87–0.90 g with the rears at 0.6× their grip from 20 to 86 kph; without, the rears
  run at 1.2–1.8×, the fronts at 2.2–3.5× and lateral falls to 0.70–0.86 g. Two closed-loop forms
  (a yaw-rate deficit, traction control on combined slip) were measured and withdrawn. Drift mode
  disarms it, so grade on `corner`, `liftoff` and the 10 kph pull-away, never `hold` or `ride`.
- `slip_power_cut_from_deg = 10.0`, `slip_power_cut_to_deg = 40.0`: with drift mode engaged, the
  drive fades out over this band of slip so a held throttle cannot spin the car. The start was the
  only lever that stopped the plain tap spinning at 42 kph (10 / 15 / 20° → 67.7 / 110.4 /
  163.4°). The end stays at 40: 20–30 collapses `hold` at 42 kph to under a second.
- `armed_slip_cut_from_deg = 8.0`, `armed_slip_cut_to_deg = 14.0`: drift mode off, power is cut as
  the tail steps out, from the tyre's peak slip angle to the angle the game calls a slide. A
  gripping corner runs 4–5° at the rear axle, so this band costs it nothing; a 3–6° band slowed
  every corner.
- Both slip cuts stand aside past 90° of slip (`REVERSED_SLIP_DEG`), so a car rolling backwards
  after a spin still has drive.
- `yaw_brake_lock_ratio = 1.5`, `yaw_brake_from_deg = 25.0`, `yaw_brake_to_deg = 40.0` (`Q156`):
  past 25° of slip the front wheel outside the slide is braked, up to 1.5× a wheel's lock torque
  (`TyreVehicleController._wheel_lock_nm`) by 40°. A real ESC's oversteer intervention, and the
  slip ceiling a real drift mode keeps, so drift mode does not stand it down. The force is the
  braked tyre's own and cannot exceed its grip. The power cuts cannot do this: the remaining spin
  is the car's momentum (a let-go turn came out at 180 / 164 / 146° with power already gone).
  - 25–40 is the earliest band that leaves a countersteered slide alone at 42 and 63 kph (`hold`
    peaks at 22–27°). From 20° `hold` at 86 kph drops to 1.7 s; a harder brake (2.0) or a shorter
    ramp does the same. 1.5 and 2.0 read alike: the wheel is at its grip first.
  - Left over: a handbrake turn with the throttle lifted still goes round at 63 and 86 kph (both
    rears locked; one front tyre is not enough).
  - Grade on `turn`'s `came out` with `hold`'s `longest` as the guard, at 42 / 63 / 86 kph.
