# region.tscn

One region's content, placed once per synced region by `CityRegions` (`P5-9c`), which sets each
node's `region` before it enters the tree. Everything is authored in the region's frame, so the
one translation on the region node places it. Both `city_drive.tscn` and `city_preview.tscn`
instance this, so `verify_city.gd` holds this file against `generated_layer.gd`'s table.

No tiles here: the drive streams them (`CityStreamer`) and the preview loads every one
(`tile_preview.gd`), so `CityRegions` adds them as the first child.

A layer whose region publishes nothing for it stays empty. Each `city_layer.gd` node prints its
collider count: none of the generated meshes carries a collider (`Q74`); what collides is listed
below.

- `Water`: the basemap's sea as one flat mesh at mean sea level (`water.glb`). No collider: a car
  that leaves the quay lands on the sunk ground under the plane (`pipeline/buildings.py` sinks
  terrain inside the sea to `basemap.seabed_m`) and `drive_level.gd` pulls it back to the nearest
  road (`drown_depth_m`).
- `Tramway` (`P3-14`): a separate mesh at the position iB1000 publishes, which `Q58` measured is
  not on the drawn carriageway. No collider: a 30 mm rail is a kerb with no point.
- `Arrows` (`P3-15`): one draw call per glyph, stood by `arrows_placements.json` (`P5-4`).
  Separate geometry because drawn on the surface they would sit under `road_markings.tres`'s
  junction fade. No collider: a step every vehicle crosses at speed. The same holds for the three
  paint layers below.
- `BoxJunctions` (`P3-18`): the published yellow boxes, drawn over the junction caps.
- `Crossings` (`P3-35g2`): pedestrian-crossing stripes, one mesh per paint (signal yellow, zebra
  white).
- `RoadMarks` (`P3-23`): the published line marks. Lifted 16 mm, a millimetre over the arrows.
- `Railings` (`P3-19`): one panel per class tiled by `railings_placements.json` (`P5-5`), standing
  on the kerb the ribbon drew. `collides = true` (`Q159`, the user's call): a box body per panel,
  the panel's own extent, so a bumper stops flat. `false` is the off switch.
- `Lamps` (`P3-26`): the published lamp posts on the drawn kerb. `posts = true` (`Q191`, the
  user's call): an upright cylinder up each column (`PropBatch.post_of`), nothing for the arm or
  lantern, one static body per plan cell. Breakaway is `B3`'s. `false` is the off switch.
- `Trees` (`P3-77`, `Q171`): HyD's and LCSD's inventories as four library kinds scaled to each
  tree's height. `trunks = true` (the user's call): a cylinder of the trunk's radius up to the
  crown's base, one static body per plan cell holding a shape per tree. Never a body per tree:
  Jolt's `max_bodies` is 10,240 and the railings hold most of it. `collides` stays off: its box is
  the whole tree, crown included.
- `Signs` (`P3-16`): the published signs on the poles TD surveyed. `posts = true` (`Q191`): a
  cylinder up every `pole` placement, none under a face. Not in `prop_cells.tres`, so one body a
  region.
- `Stops` (`P3-94`, `Q242`): the authored flags and tram shelters at published stops.
  `posts = true`: a cylinder up every `pole` placement, none under a flag, and none under a
  shelter — its feet are sunk so the lane beside the track stays open. Not in `prop_cells.tres`.
- `Landmarks` (`landmarks.gd`, `P3-6`): the authored heroes from `landmarks.json`. Beside the
  tiles, not streamed: a hero is always resident.
- `Fence` (`fence.gd`, `P3-29`): the barriers from `fence.json`. Not optional: `RoadGraph.fits_car`
  refuses some drivable edges, and `Q19` forbids a refusal the player cannot see. The barrier
  collides.
- `Parked` (`parked_layer.gd`, `P3-73`, `Q161`): the vehicles `parked_placements.json` stands from
  the authored `assets/authored/vehicles/parked.glb`, by the rig's clock hour (`parked.md`). Not a
  `city_layer` row: its library is committed, and it re-stands hidden cells as the hour moves. A
  box body per vehicle (`PropBatch.bodies`): a parked bus the car drives through is an invisible
  refusal, and the near miss (`P3-2a`) reads bodies.
