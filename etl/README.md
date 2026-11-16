# ETL

Build-time pipeline: Hong Kong government open geodata → game-ready glTF and JSON.

The game never calls it and never calls a network (`CLAUDE.md` hard rule 2). Output is a versioned
build artefact, not source. Read `docs/DATA_SOURCES.md` before changing a stage.

## Setup

The Python environment is the **repo-root** `.venv`. Do not create one in `etl/`.

```sh
python3 -m venv ../.venv
../.venv/bin/pip install -e ".[dev]"
```

Dependencies are in `pyproject.toml`: `numpy`, `pillow`, `pyogrio` (ships its own GDAL),
`pypdfium2`, `pyproj`, `pyyaml`, `shapely` (ships its own GEOS). No system install, no geopandas.

## Checks

```sh
../.venv/bin/python -m pytest             # from etl/; add -n auto to use every core
```

Lint and format from the **repo root** — the root `ruff.toml` extends these rules to `tools/*.py`,
which running ruff from `etl/` skips:

```sh
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Building a region

All commands run from `etl/`. Regions are the keys under `regions:` in `config/hong_kong.yaml`:
`wan_chai` and `causeway_bay` ship in the game; `sha_tin` and `mong_kok` are built for measurement
only.

```sh
../.venv/bin/python -m pipeline --region wan_chai [--jobs 4] [--from <stage>] [--force]
```

- Runs every stage in dependency order and writes `out/<region>/city.json`. A stage that exits
  non-zero stops the run.
- `--jobs N` runs stages side by side, each started when the stages it reads (`NEEDS` in
  `pipeline/__main__.py`) are done. The bundle is byte-identical to the serial run's. Past 4 the
  critical path is all that is left.
- `--from <stage>` skips the stages before it; their output must already be on disk.
- `--force` is passed to `fetch`.
- Two regions build side by side as two commands: no stage reads another region's output.
- `HK_TAXI_LAYER_CACHE=0` turns off the on-disk cache of clipped layer reads (`etl/.cache/layers/`,
  safe to delete).

Then merge the two shipped regions' graphs and put the bundles in front of the engine:

```sh
../.venv/bin/python -m pipeline.join --region-a wan_chai --region-b causeway_bay   # out/wan_chai+causeway_bay/
cd .. && tools/sync_generated.sh wan_chai causeway_bay && tools/check.sh
```

`tools/sync_generated.sh` is the only supported copy. It validates each `city.json`, copies exactly
the files it names into `game/assets/generated/<region>/`, and removes everything else — including
any region not on its argument list. The first region is the frame the others are placed in. With
no arguments it re-syncs the regions already synced. `tools/check.sh` then runs the engine-side
`verify_*.gd` tools, which assert what Python cannot see (imports, colliders, draw calls).

## Stages

Each stage is also its own command, `python -m pipeline.<stage> --region <region>`, and the full
run calls the same entry point. In run order:

| Stage | Does |
|---|---|
| `fetch` | Downloads and caches sources; the only stage that touches the network |
| `podiums` | iB1000 podium blocks, stitched across sheet cuts and joined to the building meshes |
| `basemap` | The harbour and the parks: sea polygon, `water.glb`, the minimap's ground |
| `buildings` | Source massing → per-tile, vertex-coloured `tiles/*.glb`, with LODs, colliders and occluders |
| `landmarks` | The mesh-sourced hero landmarks |
| `roads` | Road Network centrelines → `roadgraph.json`, with surveyed widths, lanes and turn bans |
| `carve` | Cuts road structure in the tiles back to the surveyed carriageway |
| `region` | The level-0 carriageway as one region, a territory per centreline (`carriageway_region.json`) |
| `surface` | Graph → the drivable ribbon, `roads/*.glb` chunks with collision, and `roadsurface.json` |
| `clearance` | How much of each carriageway station a car can get through |
| `fence` | Where a barrier stands on an edge the car cannot pass |
| `fares` | Taxi stands, pick-up points and street hails → `fares.json`, snapped to the graph |
| `tramway` | The tram rails as drawn geometry |
| `arrows`, `boxjunctions`, `crossings`, `roadmarks` | Published road paint, each its own mesh |
| `railings`, `signs`, `lamps`, `trees` | Published street furniture, each its own mesh or placement list |
| `signals` | The signalled junctions and their stages |
| `tramlines` | The tramway as lines a tram can run |
| `busroutes` | The bus and green-minibus routes moving traffic keeps to |
| `parked` | The stationary vehicles a region's streets carry |
| `export` | Stage outputs → `city.json`, plus cross-document validation |

`join` is not in the chain; it runs once per pair after both regions are built.

Flags beyond `--region`:

| Command | Flag |
|---|---|
| `pipeline.fetch` | `--dry-run` reports the plan without downloading payload; `--only SOURCE...` fetches named sources (an unknown name is an error); `--force` takes a fresh snapshot |
| `pipeline.buildings` | `--terrain` also emits the textured ground mesh — evaluation only, never part of the tile set (`P1-2`) |
| `pipeline.export` | `--check` validates the existing `city.json` instead of writing one; `--list` prints the files it names |
| `pipeline.join` | `--region-a`, `--region-b`, `--out` (no `--region`) |
| `pipeline.tramway`, `pipeline.signs` | `--sources-root`, `--out-root` |

## Fetching

- Re-running downloads nothing. The snapshot is fixed, so upstream publishing new data cannot
  change the map underfoot.
- `--force` overrides fetch-once but still respects each sheet's `REVISIONDATE`, so only
  republished sheets re-download. Sources with no version stamp (the roads, the sheet index) always
  re-download under it.
- Which building sheets a region needs is derived: the fetcher intersects the region bounds with
  the publisher's sheet index. Move the bounds and the sheet set follows.
- Some publishers embed an API key in the download URLs inside their index. Never copy one into
  config, docs or a commit. `fetch.py` reads URLs from the fetched index at run time and strips
  query strings from everything it records.

## Layout

| Path | Contains |
|---|---|
| `config/hong_kong.yaml` | Tuning and the publishers' vocabulary: bounds, regions, source URLs, field role maps, materials, per-stage blocks |
| `config/certs/` | The extra CA a government endpoint needs |
| `pipeline/hongkong.py` | The constants that are the city: the CRS pair, drive-on-the-left, the sign codes |
| `pipeline/config.py` | Loads and validates the YAML; nothing else reads it. Blocks live in `pipeline/config_blocks/`, one module a stage, imported through `config.py`. Refuses any key no parser read |
| `pipeline/crs.py` | The only module that converts projected coordinates to game space |
| `pipeline/gdb.py`, `gltf.py`, `mesh.py`, `meshbuild.py`, `geometry.py`, `polyline.py`, `documents.py` | Format and geometry helpers, no policy |
| `pipeline/carriageway.py`, `carriageway_area.py` | The width survey `roads` publishes as `width_m` and `lanes` |
| `pipeline/<stage>.py` | One per stage above |
| `pipeline/__main__.py` | `python -m pipeline` — the stage order and `NEEDS` |
| `tests/` | `pytest`; also covers the graders in `../tools/` |
| `sources/` | Raw downloads and `manifest.json` — gitignored |
| `out/<region>/` | Pipeline output — gitignored. `buildings.json` and `roadsurface.json` are stage intermediates and never reach the bundle |

## Rules

- **Hong Kong is the only city** (`CLAUDE.md` hard rule 3, `Q100`). Each fact lives once: tuning
  and vocabulary in `config/hong_kong.yaml`, the city's constants in `pipeline/hongkong.py`. No
  second copy in a stage, and no `--city` flag. Tests are exempt: `tests/test_crs.py` hardcodes the
  published HK1980 grid constants on purpose.
- **All tuning is data** (hard rule 4): a width, a floor or a colour goes in the YAML, not in code.
- **Datums:** HK1980 and WGS84 differ by ~304 m on the ground in Hong Kong. Region bounds are
  geodetic and the sources are HK1980 grid (EPSG:2326); only `crs.py` converts.
- **The data contract** (`docs/ARCHITECTURE.md`): a change a consumer would misread bumps
  `schema_version` and moves both sides together.
