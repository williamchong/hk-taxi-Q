# asset_viewer.tscn

One `.glb` under the shipped rig, with a readout of what the importer did to it (`P5-22`, `Q124`).
It needs only the one file, so it runs on a fresh clone with `VERIFY_GENERATED=0`. The asset goes
through the project's import hook, as in the drive.

```
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/asset_viewer.tscn \
  --asset=res://assets/authored/fixtures/dcc_roundtrip.glb --seconds=1 --shots=0.8
```

- `Lighting`: `clean_daylight.tscn`, instanced, so a prop is judged under the look that ships.
- `Camera3D` (`free_look_camera.gd`): frames the root's `built` AABB, so any asset fills the
  frame. `--camera` / `--look` override it a frame later.
