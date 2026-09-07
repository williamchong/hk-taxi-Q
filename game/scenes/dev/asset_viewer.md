# asset_viewer.tscn

Rationale for `game/scenes/dev/asset_viewer.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One `.glb` under the shipped rig, with a readout of what the importer did to
it (`P5-22`, `Q124`). The artist's loop: `city_preview.tscn` draws a region
and needs the ETL, a fetch and a build before it draws anything; this needs
the one file, so it runs on a fresh clone with `VERIFY_GENERATED=0`.

```
.claude/skills/run-hk-taxi-q/drive.sh --scene=res://scenes/dev/asset_viewer.tscn \
  --asset=res://assets/authored/fixtures/dcc_roundtrip.glb --seconds=1 --shots=0.8
```

Nothing here is a `.tres` and nothing is tuning: a viewer carries no taste.
The rig is the shipped one, instanced rather than authored again (`Q26`), and
the import hook is the project's — the asset arrives as it would in the drive.

## `[node name="Lighting" parent="." instance=ExtResource("3_light")]`

`clean_daylight.tscn`, the rig both other dev scenes instance. A prop judged
under a rig of its own would be judged under a look that never ships.

## `[node name="Camera3D" type="Camera3D" parent="."]`

The fly camera, framing on the root's `built` the way it frames on `Tiles` in
`city_preview.tscn` — the asset's own AABB, so a bollard and a hero building
both fill the frame. `--camera` / `--look` override it a frame later.
