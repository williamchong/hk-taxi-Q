# city_drive.tscn

Rationale for `game/scenes/city_drive.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The first scene that puts the car on the real city (`P1-4` + `P0-5`).

`city_preview.tscn` is for looking at the ETL output; this is for driving it.
The two are separate because they answer different questions and want
different cameras — and because a free-look camera in a scene with a physics
body is a scene where nobody is sure what they just judged.

It exists to put a real answer under `Q8` — whether real Wan Chai geometry is
fun to drive — which a grey box could not.

Since `P2-1` the tiles stream from `city.json` rather than being instantiated
wholesale by a dev preview, so this is no longer only a dev scene: it is what
`run/main_scene` boots and the closest thing to a build the project has. The
buildings still carry no collision — that is an ETL product, see PROGRESS.md.

## `[node name="Regions" type="Node3D" parent="."]`

Every synced region at its offset from the frame (`P5-9c`): `region.tscn` once per region, with a
`CityStreamer` added to each as its `Tiles`. Its layers, heroes and fence are argued in
`region.md`. The harness asks this node, not a streamer, to hold the road under the start line,
and it asks every region's streamer, because the regions' boxes overlap by the far halves each one
owns.

`camera` points at the Camera3D inside the rig, not at the rig and not
at the Taxi — the far plane is on the camera, and it is the camera a look-back
swings away from the car. See city_streamer.gd for the rest.

There is no `RoadSurface` node since `P5-6`: the drivable surface (`P1-4`)
ships as one chunk per tile and `Tiles` streams it beside the buildings, each
chunk with the `-col` trimesh the wheels stand on — `verify_road_surface.gd`
asserts it is there on every chunk, and `drive_harness.gd` asks the streamer
to hold the chunks under the start line before the first tick. Every layer
node in `region.tscn` prints its collider count for the opposite reason — there must be
none — and each says why (`Q74`).

## `[node name="Taxi" parent="." instance=ExtResource("4_taxi")]`

⚠️ This transform is a FALLBACK, not the start line. Since P2-3 the spawn is
resolved at runtime: drive_harness.gd asks RoadSpawn for a fare node and calls
place_at, so what is written here only survives on a clone with no generated
assets — where there is no road to drive on either. The harness prints the gap
between the two when it exceeds AUTHORED_DRIFT_M.

It is left in place because it puts the camera somewhere sensible while the
"run the ETL" warning gets read, and because it records what the query should
produce: eastbound in the nearside lane of Expo Drive underneath HKCEC Phase
II, 2.56 m off the centreline, road surface + 1.0 m.

Do NOT hand-edit it to move the spawn — set `spawn_fare_id` on the root, which
defaults to RoadSpawn.DEFAULT_FARE_ID. And do not rewrite these twelve floats
from a direction: they are row-major while "forward" is the -Z column, so
writing them as columns transposes the basis, which is undetectable on a
north-south street. road_spawn.gd carries that argument in full;
tools/verify_spawn.gd is what asserts the resolved basis against the edge.

See docs/ARCHITECTURE.md "To drive it".

`sun` points the car at this scene's own key light (`P5-24`): the glint and
the lamps read `VehicleController.sun` instead of searching the window for a
`DirectionalLight3D`, so the scene that owns the rig is the one that names it.
Unset, the car reads no rig — no daylight to be in or out of — and drives with
its front lamps out, which is `vehicle_lamps.gd`'s stated rule for a car with
no world around it.

## `[node name="GraphOverlay" type="Node3D" parent="."]`

`P2-2`'s debug overlay: what `RoadGraph` believes is under the car, drawn on
the road and written out as text. Dev-only, and after the Taxi so the node it
follows already exists when it looks for it.

## `[node name="Fares" type="Node" parent="."]`

`P3-1a`'s `FareSystem`: the hail → board → carry → deliver / bail loop over the
resident regions' fare nodes, metered at the real tariff (`Q141`). A plain
`Node` under the level, not under `GUI`: it owns no pixels — its state reaches
the HUD through signals. After the Taxi, which it reads every physics tick, and
before the camera, which it does not. `--fares=off` frees it, which is free
roam and what `P3-9` runs.

## `[node name="Readout" type="Node" parent="Fares"]`

`fare_readout.gd`: the loop's state, destination, clock and meter on the
`DebugHud` overlay, its only face until `P3-5a`. A child of `Fares` rather than
lines inside it, on `GraphOverlay`'s pattern: this one names the `DebugHud`
autoload, and `FareSystem` must not, because `verify_fares.gd` loads that
script before any autoload exists. Freed with its parent under `--fares=off`.

## `[node name="Hire" type="Node" parent="Fares"]`

`taxi_hire.gd` (`P3-48`): the fare loop as the car shows it — the roof sign
dark from boarding to the drop, the passenger door open from the hail to the
boarding and briefly at the drop. Signals only, so it adds nothing per frame. A
child of `Fares` on `Readout`'s pattern, so `--fares=off` frees it with the
loop and the car keeps its authored state: sign lit, door shut.

## `[node name="Attract" type="Node" parent="."]`

`MenuOrbit` (`P6-1`): the chase rig's slow circle round the car while the start
menu is up. It moves the SAME rig — `Regions.camera` is the rig's camera and
the streamer measures from it — with the rig's own `_physics_process` off,
which `DriveHarness.park` and `resume` switch. Its numbers are
`tuning/menu.tres`. The harness's `showroom_fare_id = "f_001"` is where the
car stands for it: the Harbour Road stand, HKCEC's old wing behind it, not the
start line under the Phase II podium (`menu.md`); `resume` puts the car back
on the line. `guide` is the `FareGuide` below, hidden under the menu and shown
again by its own next sample.

## `[node name="Camera3D" type="Camera3D" parent="CameraRig"]`

400 m, not the fly camera's 2 km. The region is only 1.66 km across, so a 2 km
far plane culls nothing at all, and a chase camera 6.5 m behind a car in a Wan
Chai street canyon cannot see past a couple of blocks anyway. Measured: 94 draw
calls and 2.06 M primitives at 2 km, against 48 and 1.16 M at 400 m, with
nothing visible lost at street level.
