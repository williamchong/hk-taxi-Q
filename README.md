# hk-taxi-Q

An arcade taxi game set in Hong Kong, built from Hong Kong government open geodata.

Real road topology from the Transport Department's Road Network. Real building massing from the
Lands Department's 3D Digital Map. Wan Chai and Causeway Bay, reconstructed to the point where a
Hong Kong driver can navigate it from memory — then widened, ramped, and tuned until it's fun to
drive badly.

> **Status:** planning complete, no code yet. See [`docs/PROGRESS.md`](docs/PROGRESS.md).

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
| Engine | Godot 4.6, GDScript, Jolt physics |
| Pipeline | Python 3.11+ — GDAL/OGR, geopandas |
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

Nothing to run yet. First tasks are `P0-2` and `P0-5` in [`docs/PLAN.md`](docs/PLAN.md).

Once the pipeline exists:

```bash
# Build city assets
cd etl
python -m pipeline --city hong_kong --region wan_chai

# Then open game/ in Godot 4.6
```

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
