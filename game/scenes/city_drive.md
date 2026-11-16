# city_drive.tscn

The drive level: the car on the streamed city. `main.tscn` boots it under `World`.
(`city_preview.tscn` is for looking at ETL output with a free camera.) To drive
it: `.claude/skills/run-hk-taxi-q/SKILL.md`.

- `CityDrive` (`drive_level.gd`): the harness. `showroom_fare_id = "f_001"` is where the car
  stands under the start menu (the Harbour Road stand, `menu.md`); `resume` puts it back on the
  start line. `showroom_time_of_day = 0.41` lights the boot menu at 12:44, one of the few hours
  the stand is in sun and not in HKCEC's shadow (the user's ask). Boot only: a menu over a
  finished run keeps the run's hour, and `play` restores the run's hour through
  `DayClock.restart`.
- `Regions` (`city_regions.gd`, `P5-9c`): `region.tscn` once per synced region at its offset, with
  a `CityStreamer` added to each as `Tiles` (see `region.md`). `camera` points at the `Camera3D`
  inside the rig, not the rig or the taxi: the far plane is on the camera, and a look-back swings
  it away from the car. There is no `RoadSurface` node (`P5-6`): the road ships one chunk per tile
  with its `-col` trimesh, and the harness asks every region's streamer to hold the chunks under
  the start line before the first tick.
- `Lighting`: `clean_daylight.tscn`, the rig (`clean_daylight.md`).
- `DayClock` (`day_clock.gd`, `Q160`): counts the seconds driven and hands them to `Lighting` as
  `time_of_day`. It holds while `Taxi.parked` is true. `--day-cycle=off` (which `drive.sh`
  appends) and the options menu's ALWAYS DAY leave it idle.
- `Taxi`: `taxi_tyre.tscn`. The transform is a fallback, not the start line: `drive_level.gd`
  asks `RoadSpawn` for a fare node and calls `place_at`, and prints the gap past
  `AUTHORED_DRIFT_M`. Move the spawn with `spawn_fare_id` on the root, never by editing the
  transform. Do not rewrite the twelve floats from a direction: they are row-major while forward
  is the -Z column (`road_spawn.gd`; `tools/verify_spawn.gd` asserts the resolved basis). `sun`
  names this scene's key light (`P5-24`); unset, the car reads no rig and drives with its front
  lamps out.
- `GraphOverlay` (`road_graph_overlay.gd`, `P2-2`): dev overlay of what `RoadGraph` believes is
  under the car. After the Taxi it follows.
- `Signals` (`signal_controller.gd`) and `Signals/Heads` (`signal_heads.gd`, `P3-3e`, `Q173`):
  the signal plan and the lit heads. `posts = true` (`Q191`, the user's call): each head's post
  collides, an upright cylinder read off `heads.glb`'s foot, one body per plan cell. `false` is
  the off switch.
- `Traffic` (`traffic_system.gd`) and `Trams` (`tram_system.gd`): the moving fleet, each given the
  taxi and `Signals` (`traffic.md`, `trams.md`).
- `Fares` (`fare_system.gd`, `P3-1a`): the hail, board, carry, deliver or bail loop, metered at
  the real tariff (`Q141`). A plain `Node` under the level: it owns no pixels and reaches the HUD
  through signals. `--fares=off` frees it (free roam, what `P3-9` runs).
  - `Fares/Readout` (`fare_readout.gd`): the loop's state on the `DebugHud` overlay. A child,
    because it names the `DebugHud` autoload and `FareSystem` must not (`verify_fares.gd` loads
    that script before any autoload exists).
  - `Fares/Hire` (`taxi_hire.gd`, `P3-48`): the loop as the car shows it: roof sign, passenger
    door, and since `P3-79` the meter's flag and the payout sounds. Signals only. Freed with the
    loop, leaving the sign lit and the door shut.
- `Horn` (`taxi_horn.gd`) and `Sounds` (`taxi_audio.gd`, `P3-79`): the player's car's horn and
  sounds. Siblings of the car, not children, so an AI taxi on the same body does not carry them,
  and not under `Fares`, so free roam still hears the engine. Numbers in `tuning/taxi_audio.tres`.
- `FareGuide` (`fare_guide.gd`): the fare's guide in the world, hidden under the start menu.
- `CameraRig` (`chase_camera.gd`, `tuning/camera.tres`) and its `Camera3D`: `far = 400.0`. A chase
  camera in a street canyon cannot see past a couple of blocks, and 400 m roughly halved draw
  calls and primitives against 2 km with nothing visible lost. Other layers key off this value
  (`prop_cells.md`, `parked.md`, `traffic.md`).
- `Attract` (`menu_orbit.gd`, `P6-1`): the chase rig's slow circle round the car while the start
  menu is up. It moves the same rig with the rig's own `_physics_process` off, which
  `DriveLevel.park` and `resume` switch. Numbers in `tuning/menu.tres`.
