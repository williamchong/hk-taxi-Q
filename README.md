# hk-taxi-Q

An arcade taxi game set in Hong Kong, built from Hong Kong government open geodata.

Real road topology from the Transport Department's Road Network. Real building massing from the
Lands Department's 3D Digital Map. Wan Chai and Causeway Bay, reconstructed to the point where a
Hong Kong driver can navigate it from memory — then widened, ramped, and tuned until it's fun to
drive badly.

> **Status:** Phase 1 complete — the real city builds from open data and renders in Godot. Wan Chai
> is 65 building tiles, 797 road edges with turn restrictions, a drivable road surface and 29 taxi
> stands, assembled by one command in 4.4 s. It is drivable in a browser. Next is Phase 2: tile
> streaming, a road-graph runtime, and the car on real geometry. See
> [`docs/PROGRESS.md`](docs/PROGRESS.md).

---

## The idea

Most city-driving games either hand-build a fictional city or drape photogrammetry over a real one.
Hong Kong publishes its buildings as **untextured extruded footprints** and its roads as a
**navigable graph with turn restrictions and one-way directions** — both free for commercial use.

Extruded untextured footprints are, structurally, already low-poly buildings. So the art style
isn't applied on top of the data; it's the shape the data already has. That's what makes a project
this size tractable.

The design goal is narrow and testable:

> Hand the build to a Hong Kong driver, turn off the minimap and the direction arrow, and name a
> destination. If they can drive there from memory, using the correct one-way streets, it works.

---

## Stack

| | |
|---|---|
| Engine | Godot 4.7, GDScript, Jolt physics |
| Pipeline | Python 3.11+ — `pyogrio` (ships its own GDAL), `pyproj`, `numpy` |
| Targets | iOS, Android, desktop/Steam; web export for a demo slice |
| Region | Wan Chai → Causeway Bay, ~1.5 km² |

---

## Layout

```
hk-taxi-Q/
├── CLAUDE.md      # agent instructions — locked decisions and hard rules
├── docs/          # architecture, design, plan, progress
├── etl/           # Python: HK open geodata → game assets (build time)
├── game/          # Godot project
└── tools/         # dev and export scripts
```

The ETL runs **at build time only**. The game ships static assets and makes no network calls.

---

## Getting started

You need [Godot 4.7](https://godotengine.org/) — on macOS, `brew install --cask godot` — and
Python 3.11+.

**Build the city.** The first run downloads ~283 MB of source data and caches it; after that the
whole region rebuilds in about 4.4 seconds. Output is gitignored build artefact, not source, so a
fresh clone has none of it until you do this:

```bash
python3 -m venv .venv && .venv/bin/pip install -e "etl/[dev]"

cd etl && ../.venv/bin/python -m pipeline --city hong_kong --region wan_chai && cd ..
tools/sync_generated.sh          # copies exactly what city.json names
```

**Look at it.** Open the project (`open -a Godot --args --path "$PWD/game"`) and press **F6** on
`scenes/dev/city_preview.tscn` to fly around the city, or `scenes/dev/city_drive.tscn` to drive it.

**Check it.** The ETL cannot assert engine-side facts about its own output, so three headless tools
do — draw calls and vertex colours, road collision, and whether the imported geometry actually
lands where `city.json` says:

```bash
godot --headless --path game --script res://tools/verify_city.gd
godot --headless --path game --script res://tools/verify_tiles.gd
godot --headless --path game --script res://tools/verify_road_surface.gd
```

⚠️ Running Godot rewrites `game/project.godot` and `game/export_presets.cfg`, stripping their
comments. Restore them afterwards and verify with `git diff --exit-code` — `git checkout` reports
nothing useful either way.

**Export and play it in a browser.**

```bash
tools/export.sh              # macOS + web; needs export templates installed
tools/serve_web.py           # then open http://127.0.0.1:8060
```

Not `python -m http.server`: the build needs `SharedArrayBuffer`, which browsers gate behind
COOP/COEP headers that it does not send.

**Checks**, from the repo root:

```bash
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .
cd etl && ../.venv/bin/python -m pytest
```

Next up is Phase 2 — tile streaming, the road-graph runtime, and the car on real geometry. See
[`docs/PLAN.md`](docs/PLAN.md).

---

## Documentation

| Doc | What's in it |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Locked decisions, hard rules, conventions. **Read first.** |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | Verified datasets, licences, CRS, known defects. Read before touching the ETL. |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Stack, repo layout, ETL↔game data contract, perf budget |
| [`docs/GAME_DESIGN.md`](docs/GAME_DESIGN.md) | Core loop, fares, scoring, controls, HK authenticity mechanics |
| [`docs/ART_DESIGN.md`](docs/ART_DESIGN.md) | Visual direction, palette, shaders, LOD policy |
| [`docs/PLAN.md`](docs/PLAN.md) | Phased task breakdown with acceptance criteria |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Live status, decision log, open questions, risks |

---

## Two things that will bite you

**Don't use the photogrammetry mesh.** The Lands Department also publishes a tile-based
oblique-photogrammetry model. It has ground gaps, level discontinuities, and cars fused into the
terrain — a prior public attempt concluded it suited flight simulation, not driving. Use the
**non-textured** models and **3D-BIT00 Level 1** instead.

**Check for Z values before trusting the road graph.** Hong Kong drives on three levels in places.
A 2D centreline turns every flyover into a junction that doesn't exist. This is open question `Q1`
and the first task in the plan.

---

## Data attribution

Contains geospatial data from the Lands Department and the Transport Department of the Government
of the Hong Kong Special Administrative Region, obtained via
[DATA.GOV.HK](https://data.gov.hk) and the
[Common Spatial Data Infrastructure Portal](https://portal.csdi.gov.hk).
Used under the DATA.GOV.HK Terms and Conditions of Use. Data is provided "as is". The Government
of the HKSAR does not endorse this product.

---

## Licence

Not yet decided. Code and assets are separate questions — hand-authored art and the generated
city data have different considerations from the pipeline source.
