class_name HandlingProfile
extends Resource
## Arcade vehicle feel, as data.
##
## CLAUDE.md hard rule 4: tuning values are data, never constants in code.
## This script declares the schema and nothing else — the numbers live only in
## game/tuning/handling.tres. Deliberately no defaults here: a profile that was
## never assigned reads as all-zeroes and fails loudly, rather than quietly
## driving on values buried in a script.
##
## The model is Godot's VehicleBody3D/VehicleWheel3D, driven from these numbers.
##
## ⚠️ **That reverses P0-5a, at the user's explicit instruction (Q50).** The
## raycast controller this replaced kept lateral and longitudinal grip as separate
## semi-axes of a friction ellipse; VehicleWheel3D exposes one isotropic
## wheel_friction_slip, so the two collapse into tyre_grip and the drift becomes a
## per-axle scale on that single number. What that costs is recorded in
## docs/DECISIONS.md Q50, measured, and it is a cost rather than a trade.
## See also docs/GAME_DESIGN.md "Controls".

@export_group("Speed")
## Top speed in forward gear.
@export_range(0.0, 300.0, 1.0, "suffix:km/h") var max_speed_kph: float
## Reverse is instant — no gear delay.
@export_range(0.0, 100.0, 1.0, "suffix:km/h") var max_reverse_kph: float
## Drive force at full throttle, handed to `VehicleBody3D.engine_force`.
##
## ⚠️ **Not per wheel.** The engine splits it across the wheels marked
## `use_as_traction`, where the raycast model this replaced applied it at each
## driven contact patch itself.
@export_range(0.0, 5000.0, 10.0) var engine_force: float
## Braking, handed to `VehicleBody3D.brake`.
##
## ⚠️ **This is not newtons and does not convert from the value it replaced.** The
## raycast model applied `brake_force` at each contact patch itself, and 2,400
## there was ~8.0 m/s². Godot's `brake` is its own quantity: carried across
## unchanged it stopped the car from 63 km/h in **0.10 s over 1.0 m at 173 m/s²**,
## which looks like a working brake until someone reads the table. Re-seeded
## against `tools/skidpad.sh` at **40**, which reproduces the raycast car's stop to
## within half a percent — 8.75 m/s² over 17.0 m against 8.79 over 16.6 (`Q50`).
##
## Measured linear in this region: 40 → 8.75 m/s², 80 → 16.53, 120 → 24.20. So it
## is safe to dial, and ⚠️ **the range below is deliberately far wider than the
## shipped value** — it has to keep reaching what a heavier roster vehicle needs,
## and 40 sitting near the bottom of it is information, not a mis-scaled slider.
##
## Grip does not bind here: `tyre_grip` is isotropic and generous, and the stop is
## limited by this dial rather than by the tyre. ⚠️ That was checked against
## `grip_longitudinal` before `Q50` deleted it and has **not** been re-checked
## against `tyre_grip`.
@export_range(0.0, 5000.0, 10.0) var brake_force: float

@export_group("Steering")
## Steering angle at standstill.
@export_range(0.0, 60.0, 0.5, "suffix:°") var steer_angle_max_deg: float
## Steering angle at max_speed_kph. Lower keeps the car stable at speed.
@export_range(0.0, 60.0, 0.5, "suffix:°") var steer_angle_at_top_deg: float
## Seconds to reach full lock from centre.
@export_range(0.01, 1.0, 0.01, "suffix:s") var steer_attack_s: float
## Seconds to return to centre when input is released.
@export_range(0.01, 1.0, 0.01, "suffix:s") var steer_release_s: float

@export_group("Grip")
## VehicleWheel3D.wheel_friction_slip — the tyre's whole friction budget.
##
## ⚠️ **One number, and it is isotropic.** It is the tyre's lateral limit and its
## longitudinal limit at once, so it cannot be spent asymmetrically: this is
## exactly the property P0-5a rejected VehicleBody3D for, and Q50 accepted. The
## grip_lateral / grip_longitudinal pair it replaces were the semi-axes of an
## ellipse, and there is no ellipse here to be the semi-axes of.
##
## The practical consequence is that everything below which scales this scales
## braking and traction with it, by exactly the same factor.
@export_range(0.0, 20.0, 0.05) var tyre_grip: float

@export_group("Drift")
## Rear-axle tyre_grip multiplier while drift is held. 1.0 leaves the rear axle
## alone; lower breaks it loose.
##
## ⚠️ **"Nothing lands on 14°" was published here until Q84 and it was wrong.**
## It came from a 0.02 sweep grid read through a `%.2f` row label, which printed
## 0.670, 0.668 and 0.665 as three rows all reading `drift@0.67` — a label that
## could not resolve the band it was being used to explore. Swept at 0.002 the
## response is smooth and monotonic at ~990°/unit between 0.68 and 0.66, and
## **0.6695 peaks at exactly 14.0°**. There is no cliff.
##
## 🔴 **What is real is that the peak is the wrong target.** GAME_DESIGN.md pays
## drift per *second* above the threshold, and 0.6695 spends 0.05 s there against
## the shipped 0.66's 0.57 s — so tuning the peak onto the bar scores nothing.
## Grade this dial on skidpad.sh's `secs>thr` column, never on `peak slip`.
##
## ⚠️ **And dwell is bought with speed, on this one dial, always.** 0.6695 exits
## at 48.6 kph with 0.05 s of drift; 0.66 at 45.1 with 0.57 s; 0.64 at 41.1 with
## 0.77 s; 0.60 at 36.4 with 0.85 s. "Easy to hold" and "scrubs little speed" are
## opposite ends of it. That is Q50's isotropic cost, stated properly — one
## wheel_friction_slip carries the rear axle's drive as well as its grip.
##
## ⚠️ **The window moves with tyre_grip**: re-swept at tyre_grip 4.0 it sits at
## 0.43/0.44. Sweep it with `tools/skidpad.sh --drift-grip=`, at 0.002 or finer.
##
## ⚠️ **And inside it the slide does not hold.** Because tyre_grip is isotropic,
## the same scale that lets the tail step out takes the rear axle's drive and
## braking with it — so slip opens only while speed collapses (53.9 → 26.4 kph in
## 0.75 s with the throttle down throughout), then self-terminates and the car
## grips again. GAME_DESIGN.md asks for a drift that is easy to hold; this cannot
## be one. Q50 records that as the accepted cost of the switch.
@export_range(0.0, 1.0, 0.001) var drift_rear_grip_scale: float
## Front-axle tyre_grip multiplier while drift is held.
##
## A real handbrake does nothing to the front axle, and the raycast model this
## replaced left it alone for that reason. It is back because the rear-only form
## is unusable here: with one isotropic budget, softening the rear alone spins the
## car rather than sliding it, and easing the front is the only lever left that
## keeps the nose from biting. It models no mechanism — it is a fudge, and it is
## named honestly rather than dressed up.
@export_range(0.0, 1.0, 0.01) var drift_front_grip_scale: float
## Seconds for the drift to reach full engagement while the button is held.
##
## Short: the tail should step out when the player asks, not a moment later.
@export_range(0.01, 1.0, 0.01, "suffix:s") var drift_attack_s: float
## Seconds for grip to come back after the button is released.
##
## 🔴 **This does NOT fix the tap, and Q84 built it expecting that it would.**
## The diagnosis was that a 0.5 s tap returns 1.9 deg because grip is restored on
## the tick the button comes up, so the slide carries no momentum out of the
## release. Built and measured, the tap is unchanged: 1.9 deg, and a yaw and
## distance still identical to `corner`. Swept, a release of 1.0 s reaches 2.0 deg,
## 2.0 s reaches 2.2, and 3.0 s — six times the tap itself — reaches 3.3, against a
## threshold of 14. **Nothing here is a tap any more and it still is not a drift.**
##
## ⚠️ **The real cause is that the slide takes seconds to build, not that it ends
## too quickly.** Held, the drift spends 0.57 s of a 4.00 s run above 14 deg, so
## the bar is not crossed until late in the fourth second; a 0.5 s tap is a small
## fraction of the way there whatever happens afterwards. A locked raycast tyre
## produced yaw immediately (7.1 deg) because the force appears the moment the
## tyre stops rolling; an isotropic wheel_friction_slip has to be *driven* into
## saturation, and that is a rate, not an event.
##
## 🔴 **Q85 then closed the route Q49, Q50 and Q84 all named.** get_rpm() is road
## speed re-expressed — this class carries no wheel inertia, so per-wheel angular
## velocity cannot be read here at all. The drift is assisted with a yaw torque
## instead; see drift_yaw_torque_nm.
##
## ✅ **Kept anyway, for a consumer that is recorded and is not this one.** Q83's
## touch scheme holds drift past a thumb threshold and needs hysteresis at the
## boundary; every scheme there assumes `_drift_engagement` exists. It also stops
## grip snapping between two values in one tick. Both are real, neither was the
## reason it was built, and saying so is the point of this comment.
##
## ⚠️ **Asymmetric with drift_attack_s on purpose, and the asymmetry is the
## feature.** Same shape as steer_attack_s / steer_release_s above, and for the
## same reason — the car should answer the input immediately and let go slowly.
## Do not collapse the two into one number to "restore consistency".
##
## ⚠️ **`InputRouter.drift` stays a bool and this duration lives here** (Q83): the
## router is the single source of player *intent* and the intent is binary. A ramp
## there would report held while nothing is held and lie to drift_started.
@export_range(0.01, 3.0, 0.01, "suffix:s") var drift_release_s: float
## Peak yaw torque at the moment the drift engages, in N⋅m, signed by the steer.
## Decays from here toward drift_yaw_sustain over drift_yaw_decay_s; this is the
## kick, not the whole of what a held drift gets.
##
## 🔴 **This is the game asserting rotation the tyres did not produce, and that is
## the point rather than a compromise.** Q84 measured the friction route: slip
## needs about 3.4 s of held input to reach drift_slip_threshold_deg, because
## lowering wheel_friction_slip only asks the tyres to lose an argument with
## momentum and that takes seconds. Torque on the body opens the same angle in a
## tick. Q49 already recorded that GAME_DESIGN.md's "easy to hold, scrubs little
## speed" is anti-physical, so fidelity was never the target this had to hit.
##
## 🔴 **It is a TORQUE and must never become a slip-angle setpoint.** Drive the
## car to a target angle and "slip above the threshold" degrades into "the player
## held the button" — Q72's tautology moved into the gameplay, and secs>thr stops
## grading anything. As a torque the physics still resists, so the angle is an
## outcome and the measurement keeps its meaning. Same rule that makes Q84's
## dwell column safe: the quantity controlled and the quantity measured must stay
## different variables.
##
## ⚠️ Scaled by the drift engagement, so it inherits drift_attack_s and
## drift_release_s rather than switching. Yaw inertia here is m(x²+z²)/12 =
## 1200(1.8²+4.0²)/12 ≈ 1924 kg⋅m², so 2000 N⋅m is roughly 60°/s² before the
## tyres take their share back.
@export_range(0.0, 20000.0, 100.0, "suffix:N⋅m") var drift_yaw_torque_nm: float
## Seconds over which the yaw torque decays from its peak to drift_yaw_sustain of
## it, timed from the press.
##
## 🔴 **The decay runs on TIME, and must never be made to run on measured slip.**
## Backing the torque off as the angle opens closes the loop, and "slip above the
## threshold" degrades into "the dial said so" — Q72's tautology, and the exact
## failure drift_yaw_torque_nm's own note refuses. On time it stays open-loop: the
## tyres still get to argue, so the angle is an outcome and secs>thr keeps its
## meaning. The quantity controlled and the quantity measured stay different
## variables, which is the whole rule.
##
## ⚠️ **It exists because torque × time is rotation, so a tap collects a fraction
## of what a hold does and one constant cannot serve both.** Measured at a flat
## 1000 N⋅m the hold peaked 42.1° and the tap 2.4°; at 5000 the tap reached 27.0°
## and the hold spun to 162.9° (Q85). Spending the budget early hands the tap the
## whole burst and leaves the hold a sustain it can survive.
##
## ⚠️ Linear rather than exponential, on _update_steering's move_toward idiom and
## because it gives the kick an end a player can be told about — "the burst lasts
## 0.6 s" — instead of an asymptote.
##
## ⚠️ Floored at 0.01 rather than 0 because the decay divides by it, the same
## guard drift_attack_s carries.
@export_range(0.01, 2.0, 0.01, "suffix:s") var drift_yaw_decay_s: float
## Fraction of drift_yaw_torque_nm the burst decays to and then holds for as long
## as the button is down.
##
## 0.0 makes the drift a pure kick that friction then eats: the slide
## self-terminates in about 1.8 s on its own (Q85). Above 0 is what
## GAME_DESIGN.md's "easy to hold" asks for, so this is the dial that trades a
## holdable angle against a spin, and drift_yaw_torque_nm no longer has to.
@export_range(0.0, 1.0, 0.01) var drift_yaw_sustain: float
## Slip angle above which the drift scores style points.
@export_range(0.0, 90.0, 1.0, "suffix:°") var drift_slip_threshold_deg: float
## Fraction of rolling speed shed per second when coasting — engine braking.
## Small values glide, large values stop the car the moment you lift off.
##
## ⚠️ **This is the minority of the coast drag, and the majority is invisible
## from here.** Godot's `default_linear_damp` is 0.1 and `project.godot` does not
## override it, so the engine damps the body as well. Measured on the flat
## skidpad with this dial and rolling_resistance_mps2 both at zero, the car
## decayed at **0.100/s** — exactly the engine default, and exactly twice what
## this asks for. Restoring the dial gives 0.150/s, so it does contribute its
## stated 0.05, but it is one third of the total. Tune against a measurement,
## never against the number written here.
@export_range(0.0, 1.0, 0.01) var coast_drag_per_s: float
## Speed-independent share of the coasting deceleration — rolling resistance.
##
## ⚠️ **The term that actually stops the car.** Viscous drag is an exponential
## decay with no zero: every halving of speed halves the force meant to remove
## it. With this at 0.0 a skidpad coast from 30.6 km/h was **still rolling at
## 3.9 km/h 13.8 s later**, and the same pedal that would have braked it
## reverses below STATIONARY_KPH — so there was no way to bring it to rest at
## all. At the shipped 0.8 the same coast reaches a dead stop in 6.5 s, and
## 5 km/h takes 1.5 s.
##
## This is what makes coasting shed a similar speed per second at 5 km/h as at
## 50, which is how a driver expects a car to behave.
@export_range(0.0, 5.0, 0.05, "suffix:m/s²") var rolling_resistance_mps2: float

@export_group("Collision and recovery")
## 0 = head-on stop, 1 = full glancing deflection. Glancing hits deflect;
## head-on hits cost speed, never control.
@export_range(0.0, 1.0, 0.01) var collision_deflection: float
## Fraction of speed retained after a head-on impact.
@export_range(0.0, 1.0, 0.01) var collision_speed_retained: float
## Seconds before an upside-down car auto-rights itself.
@export_range(0.0, 5.0, 0.05, "suffix:s") var auto_right_delay_s: float

@export_group("Suspension")
## Chassis layout (wheelbase, track, hardpoints) is deliberately NOT here: that is
## per-vehicle model data and belongs to the vehicle scene. Wheel radius is the one
## exception, because `VehicleWheel3D.wheel_radius` needs it — and because
## `ray_length_m()` below is still what the spawn drops the car from.
@export_range(0.1, 1.0, 0.01, "suffix:m") var wheel_radius_m: float
## Uncompressed spring length, measured from the mount point down to the hub.
## It does NOT include the wheel: the ray cast to find the ground is
## suspension_rest_length_m + wheel_radius_m.
@export_range(0.05, 1.0, 0.01, "suffix:m") var suspension_rest_length_m: float
## Maximum compression from rest before the spring bottoms out.
## Must not exceed suspension_rest_length_m.
@export_range(0.01, 0.6, 0.01, "suffix:m") var suspension_travel_m: float
## Spring rate expressed as natural frequency, not a raw N/m constant.
## Deliberate: frequency is mass-independent, so retuning vehicle mass or
## swapping in a heavier vehicle does not silently change how the car rides.
## Road cars sit near 1.5 Hz; arcade wants stiffer and flatter.
##
## It is NOT gravity-independent. Static sag is g_eff / (2πf)², so raising
## gravity_scale deepens sag and eats the bump travel that absorbs kerbs and
## jump landings. Scale this by √gravity_scale to hold ride height: the seeded
## 2.8 Hz is 2.2 Hz compensated for gravity_scale 1.6.
@export_range(0.5, 5.0, 0.05, "suffix:Hz") var suspension_frequency_hz: float
## 1.0 is critically damped. Below 1.0 allows a little bounce, above is sluggish.
@export_range(0.0, 2.0, 0.01) var suspension_damping_ratio: float
## VehicleWheel3D.wheel_roll_influence — how much of the suspension force reaches
## the chassis as roll torque. 0 suppresses body roll entirely, 1 passes it all.
##
## ⚠️ **Not an anti-roll bar, and not the anti_roll dial it replaces.** That one
## added a restoring torque across each axle, sized from the compression
## *difference* between its two wheels, so it fought roll only while the car was
## actually rolling. This scales the force that causes roll in the first place,
## at every wheel independently, whether the car is cornering or standing still.
## The numbers do not convert, and a value ported across by arithmetic would be a
## guess wearing a measurement's clothes.
##
## It is also why the anti-roll bar could not simply be kept: VehicleWheel3D
## publishes is_in_contact() and get_skidinfo() but no suspension compression, so
## the term the old bar was computed from is not readable from here.
@export_range(0.0, 1.0, 0.01) var roll_influence: float
## VehicleWheel3D.suspension_max_force, in newtons — the ceiling on what one
## spring may push with.
##
## ⚠️ **Godot's default of 6000 N cannot carry this car, and the failure is
## quiet.** Static corner load is mass × g × gravity_scale ÷ 4 = 1200 × 9.8 × 1.6
## ÷ 4 ≈ 4704 N, so the default leaves 1.27× headroom and the spring clips on the
## first kerb — the car sags onto its bump stops rather than reporting anything.
## Seeded at roughly 4× static load. It scales with mass and with gravity_scale,
## so it is not portable to a heavier vehicle unchanged.
@export_range(0.0, 60000.0, 100.0, "suffix:N") var suspension_max_force_n: float

@export_group("Body")
## Downward offset of the centre of mass from the body origin. Lower = less roll.
@export_range(-2.0, 2.0, 0.01, "suffix:m") var centre_of_mass_offset_y: float
## Above 1.0 shortens air time and lands jumps flatter.
@export_range(0.0, 5.0, 0.05) var gravity_scale: float


## How far a suspension ray reaches below its hardpoint — the car's ride height
## with the springs fully extended.
##
## The only function on an otherwise pure schema, and it is here rather than on
## VehicleController for two reasons. It is a fact about the profile, which
## suspension_rest_length_m already states in prose. And it has to be reachable
## from a headless --script tool: VehicleController reads the InputRouter
## autoload, autoloads are not registered under --script, and so anything that
## touches it there fails to compile. tools/verify_spawn.gd needs this number to
## check the drop height and must not drag the controller in to get it.
func ray_length_m() -> float:
	return suspension_rest_length_m + wheel_radius_m
