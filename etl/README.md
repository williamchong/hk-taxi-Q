# ETL

Build-time pipeline: Hong Kong government open geodata → game-ready glTF and JSON.

Runs offline and rarely. The game never calls it and never calls a network at all
(`CLAUDE.md` hard rule 2). Output is a versioned build artefact, not source.

## Setup

```sh
python3 -m venv ../.venv          # repo-root venv; .gitignore already covers it
../.venv/bin/pip install -e ".[dev]"
```

## Checks

```sh
cd etl
../.venv/bin/python -m pytest        # tests
../.venv/bin/python -m ruff check .  # lint
../.venv/bin/python -m ruff format . # format
```

## Fetching sources

```sh
../.venv/bin/python -m pipeline.fetch --city hong_kong --region wan_chai --dry-run
../.venv/bin/python -m pipeline.fetch --city hong_kong --region wan_chai
```

Wan Chai pulls **~820 MB**: six 44 MB building sheets, plus roads — of which 539 MB is GML that
duplicates the 17 MB FGDB (see `PROGRESS.md`, `Q9`). Scope it while that is unresolved:

```sh
--only buildings road_network_gdb road_centrelines_schema   # ~283 MB
```

Re-running downloads nothing. That is deliberate: the snapshot is fixed, so upstream publishing a
new month of road data must not silently change the map underfoot.

`--force` takes a fresh snapshot. It overrides fetch-once but still respects each sheet's
`REVISIONDATE`, so re-snapshotting after one sheet was republished costs one sheet, not 265 MB.
Sources with no version stamp — the roads, and the index itself — always re-download under
`--force`, which is what refreshes the sheet revisions in the first place.

Which building sheets a region needs is **derived**, never listed — the fetcher intersects the
region bounds with the publisher's sheet index. Move the bounds and the sheet set follows.

## Building tiles

```sh
../.venv/bin/python -m pipeline.buildings --city hong_kong --region wan_chai
```

Reads the cached sheets — no network — and writes `out/hong_kong/wan_chai/tiles/*.glb`, one merged,
vertex-coloured mesh per 150 m tile per LOD tier, plus a `buildings.json` intermediate. Wan Chai is
65 tiles × 3 tiers in about six seconds.

The palette, the sheet sub-directories to read, and the LOD cell sizes are all city config
(`buildings:` in the YAML). Nothing about Hong Kong is in the code.

Add `--terrain` to also emit each sheet's textured ground mesh. That output is **evaluation only**
and is not part of the tile set: it is 267 MB of JPEG for the region, against a <128 MB texture
budget. See `PROGRESS.md`.

Verify the result in the engine, which is the only place the acceptance criteria can be checked:

```sh
cp out/hong_kong/wan_chai/tiles/*.glb ../game/assets/generated/tiles/
godot --headless --path ../game --import
godot --headless --path ../game --script res://tools/verify_tiles.gd
```

## Layout

| Path | Contains |
|---|---|
| `config/cities/*.yaml` | **Every** city specific — CRS, bounds, deck heights, palette, source URLs |
| `pipeline/config.py` | Loads and validates city config; nothing else reads the YAML |
| `pipeline/crs.py` | The only module that converts projected coordinates to game space |
| `pipeline/fetch.py` | Downloads and caches sources; derives tile sets from published indexes |
| `pipeline/gltf.py` | glTF reading and GLB writing — no library, see the module docstring |
| `pipeline/mesh.py` | Merge, partition and LOD-collapse meshes. Geometry only, no policy |
| `pipeline/buildings.py` | Sheets → vertex-coloured tiles. Where the policy lives |
| `sources/<city>/<source>/` | Raw downloads and `manifest.json` — gitignored |
| `out/<city>/<region>/` | Pipeline output — gitignored |

## Credentials

Some publishers embed an API key in the download URLs inside their index. **Never copy one into
config, docs, or a commit.** `fetch.py` reads URLs from the fetched index at run time and strips
query strings from everything it records, so a rotated key costs nothing and no key reaches the
repo. `etl/sources/` is gitignored, but that is the second line of defence, not the first.

## The one rule that matters

**No Hong Kong fact may appear in `pipeline/`** — not a CRS code, not a bound, not a
URL (`CLAUDE.md` hard rule 3). The second city is the business case, and it should
cost a YAML file. Tests are exempt: `tests/test_crs.py` deliberately hardcodes the
published HK1980 grid constants, because a test that derived its expectations from
the code under test would verify nothing.

## Datums are not decoration

HK1980 and WGS84 differ by **~304 m on the ground** in Hong Kong. Bounds read off a
consumer web map are WGS84; the source datasets are HK1980. Config states
`crs.geodetic` explicitly for exactly this reason, and `test_crs.py` fails if the
two datums ever stop disagreeing — which would mean PROJ had quietly fallen back to
a ballpark transformation.
