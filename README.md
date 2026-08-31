# hk-taxi-Q

An arcade taxi game set in Hong Kong, built from Hong Kong government open geodata.

Real road topology from the Transport Department's Road Network. Real building massing from the
Lands Department's 3D Visualisation Map and iB1000 topographic map. Wan Chai and Causeway Bay,
reconstructed to the point where a Hong Kong driver can navigate it from memory — then widened,
ramped, and tuned until it's fun to drive badly.

> **Status:** Phases 0 and 1 complete; Phase 2 is its on-device review away from its gate, and
> Phase 3's first build is shipped. One command turns nine government datasets from four publishers
> into a drivable city in **19 seconds**: 66 building tiles, 797 road edges with turn
> restrictions, a drivable road surface, 48 fare nodes, and the markings, tram rails, railings,
> traffic signs and lamp posts the government publishes. Godot streams it, the car drives it, the
> buildings and the flyovers are solid, and it plays in a browser. Left before the Phase 2 gate: the
> on-device performance pass and touch input's on-device review, both of which need a handset. See
> [`docs/PROGRESS.md`](docs/PROGRESS.md).

---

## The idea

Most city-driving games either hand-build a fictional city or drape photogrammetry over a real one.
Hong Kong publishes its buildings as **untextured extruded footprints** and its roads as a
**navigable graph with turn restrictions and one-way directions** — both free for commercial use.

Extruded untextured footprints are, structurally, already low-poly buildings. So the art style isn't
applied on top of the data; it's the shape the data already has. That's what makes a project this
size tractable.

The design goal is narrow and testable:

> Hand the build to a Hong Kong driver, turn off the minimap and the direction arrow, and name a
> destination. If they can drive there from memory, using the correct one-way streets, it works.

---

## Stack

| | |
|---|---|
| Engine | Godot 4.7, GDScript, Jolt physics |
| Pipeline | Python 3.11+ — `pyogrio` (ships its own GDAL), `pyproj`, `numpy`, `pillow`, `pypdfium2`, `pyyaml` — see `etl/pyproject.toml` |
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
└── tools/         # dev, check and export scripts
```

The ETL runs **at build time only**. The game ships static assets and makes no network calls.

---

## Getting started

You need [Godot 4.7](https://godotengine.org/) — on macOS, `brew install --cask godot` — and
Python 3.11+.

**Build the city.** The first run downloads ~320 MB of source data and caches it; after that the
whole region rebuilds in about 27 seconds across 18 stages. Output is gitignored build artefact, not
source, so a fresh clone has none of it until you do this:

```bash
python3 -m venv .venv && .venv/bin/pip install -e "etl/[dev]"

cd etl && ../.venv/bin/python -m pipeline --region wan_chai && cd ..
tools/sync_generated.sh          # copies exactly what city.json names
```

**Look at it.** Open the project (`open -a Godot --args --path "$PWD/game"`) and press **F6** on
`scenes/dev/city_preview.tscn` to fly around the city, or `scenes/dev/city_drive.tscn` to drive it.
**F3** cycles the debug overlay — off, then a position and frame-rate block, then the road graph's
readout and chevrons. It starts off; see `docs/ARCHITECTURE.md` "The debug overlay".

**Check it.** The ETL cannot assert engine-side facts about its own output, so twenty headless tools
do. The import step is required, not optional — it builds the gitignored `game/.godot/`, without
which the freshly synced `.glb` files have no import sidecars:

```bash
tools/check.sh
```

That runs `gdformat`, the project-settings and tuning-rationale tripwires, the import (~8 s cold),
a GDScript warnings sweep and the verify tools, and is the **only** route that fails on error. Godot exits `0` whatever happens — including when a script
fails to parse — so the script reads its output and supplies the exit code the engine will not.
Running the steps by hand and eyeballing them is how a broken check passes.

The warnings sweep is the GDScript linter: engine warnings are set to *error* in `project.godot`,
including untyped declarations. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the list —
and for why an editor save can silently drop them (the `settings` step is what catches it).

GitHub Actions runs the same script on every push and pull request, alongside `ruff` and `pytest`. It
**skips the generated-asset verify tools** — a fresh checkout has no generated assets to check, and
building them in CI would mean re-downloading the source data every push. The five that need no
built region (`verify_beam_budget`, `verify_mesh_contract`, `verify_vehicle`, `verify_hud`,
`verify_input`) run there anyway. So the asset contracts are yours to run locally after a pipeline
build; everything else CI catches for you.

Grading tools sit beside the suite and are run by hand after a build, because they need a built
region under `etl/out`. `CLAUDE.md` lists which change owes which; two of them:

```bash
.venv/bin/python tools/deck_error.py --generated etl/out/wan_chai
.venv/bin/python tools/overhang.py   --generated etl/out/wan_chai
```

They measure the drawn carriageway against the *shipped* tiles and share no code with the pipeline
that produced them — a stage cannot mark its own work.

**Export and play it in a browser.**

```bash
tools/export.sh              # macOS + web; needs export templates installed
tools/serve_web.py           # then open http://127.0.0.1:8060
```

Not `python -m http.server`: the build needs `SharedArrayBuffer`, which browsers gate behind
COOP/COEP headers that it does not send.

⚠️ **Opening the editor or running an export rewrites `game/project.godot` and
`game/export_presets.cfg`**, stripping their comments and the web renderer setting. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how to restore and verify. Headless `--import` and
`--script` runs do not.

---

## Documentation

| Doc | What's in it |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Locked decisions, hard rules, conventions. **Read first.** |
| [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) | Verified datasets, licences, CRS, known defects. Read before touching the ETL |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Stack, repo layout, ETL↔game data contract, checks, perf budget |
| [`docs/GAME_DESIGN.md`](docs/GAME_DESIGN.md) | Core loop, fares, scoring, controls, HK authenticity mechanics |
| [`docs/ART_DESIGN.md`](docs/ART_DESIGN.md) | Visual direction, palette, shaders, LOD policy |
| [`docs/PLAN.md`](docs/PLAN.md) | Phased task breakdown with acceptance criteria |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Live status — task board, open questions, risks, measured metrics |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Why anything is the way it is, keyed by `Q` or task ID |
| [`LICENSING.md`](LICENSING.md) | Which licence covers what, and why the generated data is not ours to relicense |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Checks to run, commit style, and the inbound-MIT licensing of contributions |

---

## Three things that will bite you

**Don't use the photogrammetry mesh.** The Lands Department also publishes a tile-based
oblique-photogrammetry model. It has ground gaps, level discontinuities, and cars fused into the
terrain — a prior public attempt concluded it suited flight simulation, not driving. Use the
**non-textured** models and **iB1000** instead.

**The road centrelines are 2D — grade separation is an attribute, not a Z value.** Hong Kong drives on
three levels in places, and a naive 2D graph turns every flyover into a junction that doesn't exist.
Road Network v2 carries no Z, but it does carry an integer `ELEVATION`. **Only ever join edges at
matching levels — but never key a *node* on the level**, because every place two levels meet at a
shared endpoint is a ramp touching down, and splitting there severs the elevated network from the
ground one.

**Where the deck actually *is* comes from the map sheets, not the road data.** The `INFRASTRUCTURE`
class in the LandsD sheets models the flyovers *including their approach ramps*, and that is the only
height source there is for off-grade roads. A tunnel is a void, so it has none and never will.

---

## Data attribution

Contains geospatial data from the Lands Department, the Transport Department and the Highways
Department of the Government of the Hong Kong Special Administrative Region, which own the
intellectual property rights in that data, obtained via [DATA.GOV.HK](https://data.gov.hk) and the
[Common Spatial Data Infrastructure Portal](https://portal.csdi.gov.hk). Used under the DATA.GOV.HK
and CSDI Portal Terms and Conditions of Use. Data is provided "as is". The Government of the HKSAR
does not endorse this product.

---

## Licence

Three kinds of thing, three answers, because they have three different owners — plus one bundled
exception (`Q79`):

| What | Licence |
|---|---|
| **Code** — pipeline, engine scripts, tools, config, tuning | **GPL-3.0-or-later** ([`LICENSE`](LICENSE)) |
| **Hand-authored assets** — hero buildings, vehicles, UI, shaders (`game/assets/authored/`, `game/assets/shaders/`) | **CC BY-SA 4.0** ([`game/assets/authored/LICENSE`](game/assets/authored/LICENSE)) |
| **Generated city data** — tiles, road surface, road graph, fares | **Not relicensed by us.** Derived from HK government data under the DATA.GOV.HK and CSDI Portal Terms and Conditions of Use |
| **Bundled typeface** — `game/assets/authored/fonts/` | **CC BY 4.0**, third party — see [`LICENSING.md`](LICENSING.md) |

**This repository redistributes no government data** — `etl/sources/`, `etl/out/` and
`game/assets/generated/` are all gitignored. You regenerate them from the government endpoints
yourself, in about 19 seconds, and accept those terms directly. An exported *game* does ship them, and
that is what makes the credits screen mandatory rather than nice-to-have.

⚠️ **GPLv3 conflicts with App Store distribution terms**, so store builds need a separate proprietary
grant — which works only while a single copyright holder owns everything, and therefore needs a CLA
before the first outside contribution. See [`LICENSING.md`](LICENSING.md), which is where
the reasoning and the open items live.
