class_name PaceProfile
extends Resource
## The game's pace, as one named scale (`Q156`): how much faster than a real
## road the game plays, for every car alike. Read by `VehicleController`; why
## the value is what it is lives in `tuning/pace.md`. No defaults (`Q119`).
##
## It is the world that is scaled, never the car: gravity is multiplied by
## `pace_scale` and every force the car makes follows it, which is the real car
## on a road where everything happens `√pace_scale` times as fast. The same
## corner is taken `√pace_scale` times as quickly, at the same angles, with the
## same share of each tyre's grip — so a car's character (which axle lets go,
## how a lift tucks the nose) is its `CarSpec`'s at every pace, where a made-up
## grip number flattened it and wanted every torque re-seeded by hand.
##
## What follows the scale, in `VehicleController` and `TyreVehicleController`:
##   × `pace_scale`      gravity, the launch force, rolling resistance — and
##                       through the weight, the brake, the handbrake, the yaw
##                       brake and a spring's ceiling
##   × `√pace_scale`     the limiter, the spring's frequency, the coast's
##                       viscous term, the tyre's low-speed floor, every
##                       speed a system or an aid is keyed on, and the
##                       systems' own clocks (drift mode's re-arm, the catch
##                       limiter, the drift button's ramp)
##   × `pace_scale^1.5`  the engine's power (a force times a speed)
##   unchanged           mass, the tyre, air drag (it goes with speed squared
##                       by itself), every angle — and the PLAYER: the
##                       steering's ramp (`steer_attack_s`) stays in seconds,
##                       because hands do not speed up with the world.
##
## The game around the car is not scaled either, on purpose: the fare's and
## the skills' bars (`speed_min_kph`, the wall tiers, `par_kph`), the wall
## response and auto-righting read real speeds and real seconds. They are what
## the player is asked for, and a pace change re-grades them by hand.

## 1.0 is a real road. Above it the game is quicker and a slide is shorter in
## seconds; below it, slower. 0 is unauthored and parks the car.
@export_range(0.0, 5.0, 0.05) var pace_scale: float
