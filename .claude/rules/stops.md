---
paths:
  - "etl/pipeline/stops.py"
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
- **A taxi STAND takes no flag**: TD's `TS324` stands there. Do not add one beside it.
- **What is authored**: every size, and the liveries by broad colour only — no operator's logo or
  wording. Colours are NAMES in `signs.colours`
  (`test_no_colour_escapes_the_materials_table`); a hex in the block fails that test.
- **A pole is registered outward only** (`register`, `lamps._register`'s rule) and refused where
  it would still stand on the asphalt (`drawnroad.drawn_carriageway`, `Q237`). A widening moves
  every pole.
- **Colliders** (`Q191`): `region.tscn`'s `posts` stands a cylinder under every library mesh whose
  foot is at its origin. `pole` is the only one: a flag hangs, and the shelter's feet are sunk
  `_SHELTER_SUNK_M` on purpose — the game draws no island, so the lane beside the track runs where
  the shelter stands. `verify_stops.gd` fails a shelter that gains a post.
- **The shelter stands on the track's left**, `offset_m` from its centreline; a tram is 1.98 m
  wide. Moving `trams.tres`' body or `tramway.lines` owes a frame of a tram at a stop.
- The material is the signs' (`SIGNS_MATERIAL`, `signs.tres`); `STOPS_MATERIAL` in
  `verify_stops.gd` moves with it.
