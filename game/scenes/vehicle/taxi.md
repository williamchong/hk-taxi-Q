# taxi.tscn

Rationale for `game/scenes/vehicle/taxi.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The player's taxi.

⚠️ Since `Q50` this is a `VehicleBody3D` with four `VehicleWheel3D` children,
reversing `P0-5a`. It was a `RigidBody3D` with `Marker3D` hardpoints under a
hand-rolled raycast model until 2026-08-18. `scripts/vehicle/wheel_mount.gd`
and `scripts/vehicle/wheel_visual.gd` were deleted in the same change: a
`VehicleWheel3D` positions, rolls and steers its own child mesh, so the tyre
instances below carry no script at all.

⚠️ **A `VehicleWheel3D` must be a DIRECT child of the `VehicleBody3D`.** The
engine collects them that way and silently ignores one nested any deeper —
`vehicle_controller.gd` matches that rule rather than a recursive search, so a
misplaced wheel is a car that drives on three.

⚠️ **The tyre mesh is `taxi_tyre.glb` and must stay so.** Godot's glTF importer
turns any node whose name ends in `_wheel` into a `VehicleWheel3D` — which is
how `P3-11` lost its wheels — and here that would silently nest a wheel inside
a wheel. See docs/ARCHITECTURE.md "The importer can reinstate VehicleWheel3D".

Godot strips these comments on any editor resave, so anything load-bearing
lives in the scripts and in docs/, not here.

## `[sub_resource type="BoxShape3D" id="BoxShape3D_body"]`

Not the visual body, deliberately — see docs/PROGRESS.md, P3-11.

## `[node name="Mesh" parent="." instance=ExtResource("4_body")]`

The lamp rig rides on the body mesh rather than beside it, the same way the
tyre mesh rides on its wheel: the circuits are per-instance shader state, and
the instance is the `MeshInstance3D` inside this .glb. See
scripts/vehicle/vehicle_lamps.gd.

## `[node name="PassengerDoor" type="Node3D" parent="."]`

The rear kerbside door, swung by scripts/vehicle/taxi_door.gd while a fare
boards or alights (`P3-48`). THE NODE IS THE HINGE: its origin is the doorway's
front edge on the flank, and the leaf below it is built in that frame, so the
swing is this node's rotation about y and the script needs no pivot maths.

⚠️ **The origin is a hand copy of `make_vehicle.door_hinge`** — x the kerb
side's `half_width_m`, z `cabin_mid_z_m` — exactly as the wheels are copies of
`Chassis`, and `etl/tests/test_make_vehicle.py` binds the two. Move the door in
the generator and not here and the leaf swings about a hinge standing in air;
shut, it no longer fills the hole the body was cut with.

Which way is out is read off the sign of x, so the same script hangs a door on
either flank. The kerb is the left (-x) because Hong Kong drives on the left
(`DRIVES_ON_LEFT`), and only the REAR door opens: a Hong Kong taxi's driver
swings it from the seat with a lever. Swing angle, time and the hold at a drop
are the script's exports; none is re-authored here, so the defaults are the
values.

No collider, deliberately: the door is presentation, and an open leaf that
could catch a lamp post would change how the car drives.

## `[node name="Leaf" parent="PassengerDoor" instance=ExtResource("11_doorleaf")]`

`taxi_door.glb`, from tools/make_vehicle.py. It goes through the import hook's
vehicle material door like the body, so it renders with `vehicle_body.tres` and
shades as the flank it fills. It carries no lamp, so `VehicleLamps` never finds
it — that script takes the first mesh under `Mesh`, not under the car.

## `[node name="PassengerEmote" type="Node3D" parent="."]`

Where the passenger sits, and where their face pops out of the cab
(`P3-49`, `Q145`): scripts/vehicle/passenger_emote.gd instances one of the
two emote meshes here, rises it through the roof and shrinks it away. The
origin is the rear kerbside seat — x on the kerb side like the door
(-0.45, half way from the centreline to the flank), y 0.55 (between the belt
line and the roof, `make_vehicle.Proportions`), z 0.8 (behind the door hinge
at `cabin_mid_z_m` 0.315 and ahead of `cabin_rear_z_m` 1.25) — so the face is
hidden by the roof at the pop and emerges from the back of the car rather than
appearing on it. `verify_vehicle.gd` holds it on the door's side of the car and
behind the hinge.

The rise, life, pop, shrink and how many faces may be up at once are the
script's exports; none is re-authored here, so the defaults are the values.

No collider, and unshaded: a glyph in the world, not a surface the rig lights.

## `[node name="HeadlampL" type="SpotLight3D" parent="."]`

The light the headlamps actually throw, switched by vehicle_lamps.gd along
with the lenses — the lenses only glow, and a glowing lamp over a black road
is what P3-11e shipped first.

One cone per lamp, at the same x as the lenses tools/make_vehicle.py builds
(+/-0.58). A single central spot shipped first and was rejected on the look:
the argument for it was that two cones merge into one pool a few metres out,
which is true of the far field and misses the near field entirely — the twin
roots at the bumper are the part that reads as a car rather than as a torch.
The script drives however many spots the scene holds, so this is a scene edit.

spot_angle is Godot's HALF angle, which is the trap in this node, and the tilt
has to be read together with it. THE CONE MUST NOT REACH ABOVE HORIZONTAL: at
7 degrees down with a half angle of 11, the top of the beam pointed 4 degrees
UP, so part of it never met the road at all and the rest grazed it at a
vanishing angle. Rendered from the chase camera that lit a tall rounded dome
climbing the screen toward the vanishing point, and it read — correctly — as a
light shining upward rather than as a road being lit. Reported as exactly that.
tools/verify_vehicle.gd now checks this rather than trusting the comment.

14 down against a half angle of 13 puts the top edge 1 degree BELOW horizontal,
so every ray lands on tarmac and the pool is bounded instead of running to the
horizon. Basis is row-major here: the *column* -Z each shines along works out
as (0, -0.242, -0.970).

The half angle is otherwise set by how far the two pools stay apart, not by
what a headlamp spreads. Lamps 0.58 m off centre overlap from d =
0.58/tan(angle) onward, so 22 merged them inside 1.5 m and rendered as one blob
with two lamps behind it, and 15 still read as a single lobe with a notch. 13
holds them apart to ~2.5 m, which is in front of where the chase camera sits.

spot_angle_attenuation above 1.0 softens the rim, because a crisp-edged circle
of light is the other half of "too clearly a cone". spot_attenuation near
Godot's 1.0 default lets the far end fade rather than stopping at a visible
arc, which is what spot_range alone does.

light_energy is per lamp, and two overlapping cones add where they cross —
which is the middle of the road. shadow_enabled stays off, and that is the
mobile tier's rule rather than a saving: docs/ART_DESIGN.md allows vehicle blob
shadows and no realtime shadow maps. The line is not in the file because off is
the engine default, and the editor's writer omits every default-equal value
(Q119); it was written out until the first editor save dropped it (P5-21).

distance_fade is NOT a saving, it is a seat at the table. Forward Mobile pairs
at most 8 spot lights PER RENDERED OBJECT and the fragment shader loops that
fixed list — measured linear to 8 and then exactly zero from the 9th on, with
no warning. The road was ONE mesh for the whole region when this was measured
(one chunk per 150 m tile since `P5-6`, so the bound below is conservative now),
so every beam in the game competed for the same 8 slots: at 2 lamps a car that
is FOUR CARS, and which four is decided by pair order rather than by distance,
so beams would pop on and off the road as the BVH re-pairs. Fading a light out
frees its slot, measured: 16 spots on one object give 8 units of light, and
fading the first 8 gives the same 8 units from the other half. 35 m of full
reach is well past the chase camera and past where a 32 m cone is more than a
few pixels, so nothing visible is spent. ⚠️ This bounds the competitors, it does
not cap them — `BeamBudget` is the nearest-N rule that does. See DECISIONS
P3-11e.

THIS NODE OWNS BRIGHTNESS AND REACH. vehicle_lamps.gd reads light_energy and
spot_range once in _ready and thereafter only scales them by sidelamp_beam, so
both values here are live and a roster car can carry a dimmer or shorter beam
without touching the script. It briefly worked the other way for energy alone
— an export overwrote this before the first frame, so editing it did nothing
and nothing said so.

## `[node name="SunGlint" type="Node3D" parent="."]`

Feeds the body shader the scene's real sun, so the glint never carries a
second copy of the rig's rotation. See scripts/vehicle/sun_glint.gd.

## `[node name="WheelFL" type="VehicleWheel3D" parent="."]`

Suspension, friction and roll influence are written by the controller from
`handling.tres` at `_ready`, so these four carry only what is geometry or role.
Leaving the numbers out of the scene is deliberate: two places to author one
spring is how a car ends up measuring its own tuning instead of the profile's.

⚠️ The roles below are NOT what the controller splits axles by — it uses
position along the chassis, because a front-wheel-drive roster car would
otherwise invert the drift bias. See VehicleController._group_axles.
