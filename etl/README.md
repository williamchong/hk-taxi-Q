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

## Layout

| Path | Contains |
|---|---|
| `config/cities/*.yaml` | **Every** city specific — CRS, bounds, deck heights, source URLs |
| `pipeline/crs.py` | The only module that converts projected coordinates to game space |
| `pipeline/config.py` | Loads and validates city config; nothing else reads the YAML |
| `sources/` | Raw downloads — gitignored |
| `out/` | Pipeline output — gitignored |

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
