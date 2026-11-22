---
paths:
  - "etl/pipeline/stops.py"
  - "etl/pipeline/drawnroad.py"
  - "etl/pipeline/config_blocks/stops.py"
  - "etl/tests/test_stops.py"
  - "game/tools/verify_stops.gd"
---

# Stop furniture: flags and tram shelters — before marking work done

`P3-93` to `P3-96`, `Q242`. Authored furniture at published stops; `stopmarks.py` draws the paint
and `signs.py` TD's own `TS324` taxi stand plate.

- **`pipeline/stops.py`, the `stops` block**: `tools/battery.py stops --region <r> --before
  <root>`, both regions. From `stops.json` compare `read` / `merged` / `stood` / `refused` (per
  kind, `read == merged + stood + sum(refused)`), `shift_m`, `posts_kept_as_surveyed`,
  `facing_away` (must be 0). A frame of each kind: `city_preview.tscn`, explicit `--camera` /
  `--look`.
- **Where is the bundle's, never a source's**: `bus_routes.json`'s stop points (once a `stop_id`),
  `fares.json`'s `pudo` nodes, `tram_lines.json`'s stops (once an id, on the first track). A
  change to `busroutes`, `fares` or `tramlines` moves this layer; the stage runs after all three.
- **No taxi flag** (the user's call, 2026-11-18): TD's `TS324` marks a stand and `TS3643` and
  the lettering a pick-up point. `taxi_point` is still a kind the block may declare.
- **What is authored**: every size, and the liveries by broad colour only — no operator's logo or
  wording. Colours are NAMES in `signs.colours`
  (`test_no_colour_escapes_the_materials_table`); a hex in the block fails that test.
- **A pole is registered outward only** (`register`, through `drawnroad.Ribbon.register`) and refused where
  it would still stand on the asphalt (`drawnroad.drawn_carriageway`, `Q237`). A widening moves
  every pole.
- **Colliders** (`Q191`): `region.tscn`'s `posts` stands a cylinder under every library mesh whose
  foot is at its origin: `pole` and `tram_post` (the user's call, 2026-11-18). A flag hangs, and
  the shelter's roof (`tram_shelter`) hangs too — standing on its origin it would take a cylinder
  its whole footprint. `verify_stops.gd` fails a roof that gains a post or a post that loses one.
  The game draws no island, so a shelter post can stand in the lane beside the track.
- **The shelter stands on the track's left**, `offset_m` from its centreline; a tram is 1.98 m
  wide. Moving `trams.tres`' body or `tramway.lines` owes a frame of a tram at a stop.
- The material is the signs' (`SIGNS_MATERIAL`, `signs.tres`); `STOPS_MATERIAL` in
  `verify_stops.gd` moves with it.
- **A station exit's portal** (`P3-107`, `Q269`): one library mesh an exit (`exit_<node id>`),
  drawn on the shipped tile wall nearest `fares.json`'s `station_exit` within `wall_reach_m`, the
  wall facing its road preferred. A frame of one from its road after any change to `walls` /
  `exit_stand` / the block, and `stops.json`'s `exit_signs` (`on_wall` / `on_post`) and
  `exit_wall_m`. The stage now reads the tiles, so it needs `carve`. The station's colour is its
  `fares.stations.table` row's, a NAME in `signs.colours`; the lettering is `roadtext.Face` set by
  `fascia_zh` / `fascia_en`, and a character the font lacks stops the build. On a wall the mesh's
  foot is below its origin, so `post_of` stands no collider across the door; keep it so.
