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

## Layout

| Path | Contains |
|---|---|
| `config/cities/*.yaml` | **Every** city specific — CRS, bounds, deck heights, source URLs |
| `pipeline/crs.py` | The only module that converts projected coordinates to game space |
| `pipeline/config.py` | Loads and validates city config; nothing else reads the YAML |
| `pipeline/fetch.py` | Downloads and caches sources; derives tile sets from published indexes |
| `sources/` | Raw downloads and `manifest.json` — gitignored |
| `out/` | Pipeline output — gitignored |

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
