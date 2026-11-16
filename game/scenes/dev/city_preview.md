# city_preview.tscn

Every synced region drawn whole, for looking at ETL output with a free camera.

- `Regions` (`city_regions.gd`, `P5-9c`): `region.tscn` once per region at its offset, each with a
  `tile_preview.gd` added as `Tiles`, which loads every tile and road chunk `city.json` names
  (no `StreamingProfile` is given, so nothing streams). The layers and heroes are the drive's
  (`region.md`), because `Q27`'s two fixed colour viewpoints are shot here.
- `Fares` (`fare_preview.gd`, `P1-5`): the fare nodes as pins and tethers, lifted clear of the
  carriageway. Visible by default.
- `Roads` (`road_preview.gd`, `P1-3`): the graph diagnostic, hidden. It draws flat ribbons at the
  surface's height and z-fights it; switch it on to read one-way arrows or elevation levels.
- `Lighting`: `clean_daylight.tscn`.
- `Camera3D` (`free_look_camera.gd`): `far = 6000.0`, framing the box `Regions` forwards as
  `built`.
