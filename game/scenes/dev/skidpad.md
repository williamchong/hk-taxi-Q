# skidpad.tscn

A measuring instrument for `tools/skidpad.sh`: the greybox ground with the car parked clear of
every building, so a handling number is not cut short by a wall. The rows that want an obstacle
(`--only=wall`, `P3-50`; `--only=traffic`, `Q175`) stand it from the tool and free it after.
`--scene=` takes another path if a second car is ever graded.

- `City` (`greybox_builder.gd`): `ground_grid_m = 5.0` draws a 5 m grid, heavier every 20 m
  (`greybox_grid.gdshader`), so a human driver can see the tail step out. Paint only; no graded
  number moves. `greybox.tscn` leaves it at 0.
- `Taxi`: `taxi_tyre.tscn`, the game's car. The spawn (−400, 1, −500) is the point of this scene:
  about 350 m clear of the nearest greybox segment. `greybox.tscn`'s spawn is inside the road
  network, where a drift run hit a block and read in telemetry like a spin. Facing +X; the
  transform is row-major and forward is the −Z column, so do not rewrite it from a direction.
  `sun` names this scene's key light (`P5-24`); unset, the car reads no rig and drives with its
  front lamps out.
- `Sun`, `WorldEnvironment`: a plain greybox light, not the shipped rig.
- `CameraRig`: the chase camera on `tuning/camera.tres`, `far = 2000.0`.
