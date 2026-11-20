# hk-taxi-Q

An arcade taxi game set in Hong Kong, built from Hong Kong government open geodata.

Real road topology from the Transport Department's Road Network. Real building massing from the
Lands Department's 3D Visualisation Map and iB1000 topographic map. Wan Chai and Causeway Bay,
reconstructed to the point where a Hong Kong driver can navigate them from memory, then tuned until
it's fun to drive badly.

> **Status:** playable on desktop, in a browser and on an iPhone. One command turns the
> government's datasets into a drivable city: building tiles, a road graph with turn restrictions,
> a road surface, fare nodes, and the markings, tram rails, railings, signs, signals, lamp posts and
> trees the government publishes. Fares, traffic, trams, a day-to-night cycle and a start menu are
> built. Live status is in [`docs/PROGRESS.md`](docs/PROGRESS.md).

## The idea

Hong Kong publishes its buildings as **untextured extruded footprints** and its roads as a
**navigable graph with turn restrictions and one-way directions**, both free for commercial use.
Extruded untextured footprints are already low-poly buildings, so the art style is the shape the
data already has.

The design goal is narrow and testable:

> Hand the build to a Hong Kong driver, turn off the minimap and the direction arrow, and name a
> destination. If they can drive there from memory, using the correct one-way streets, it works.

## Stack

| | |
|---|---|
| Engine | Godot 4.7, GDScript, Jolt physics, Mobile renderer |
| Pipeline | Python 3.11+ — `pyogrio` (ships its own GDAL), `shapely`, `pyproj`, `numpy` — see `etl/pyproject.toml` |
| Targets | iOS, Android, desktop; web export for a demo slice |
| Region | Wan Chai → Causeway Bay, ~1.5 km² |

## Layout

```
hk-taxi-Q/
├── CLAUDE.md      # agent instructions — locked decisions and hard rules
├── docs/          # architecture, design, plan, progress, decisions
├── etl/           # Python: HK open geodata → game assets (build time)
├── game/          # Godot project
├── tools/         # check, export, sync and grading scripts
└── fastlane/      # App Store listing text
```

The ETL runs **at build time only**. The game ships static assets and makes no network calls.

## Getting started

You need [Godot 4.7](https://godotengine.org/) (`brew install --cask godot` on macOS), Python 3.11+,
and [Git LFS](https://git-lfs.com/) **before you clone** (`brew install git-lfs && git lfs install`).
The authored `.glb`, `.png` and `.ttf` files are LFS objects; a clone made without it holds pointer
files and `tools/check.sh` fails. Repair one with `git lfs install && git lfs pull`.

**Build the city.** The first run downloads and caches the source data (a few hundred MB a region). The
output is gitignored, so a fresh clone has no city until you do this:

```bash
python3 -m venv .venv && .venv/bin/pip install -e "etl/[dev]"

cd etl
../.venv/bin/python -m pipeline --region wan_chai --jobs 4
../.venv/bin/python -m pipeline --region causeway_bay --jobs 4
../.venv/bin/python -m pipeline.join --region-a wan_chai --region-b causeway_bay
cd ..
tools/sync_generated.sh wan_chai causeway_bay   # copies exactly what each city.json names
```

Wan Chai alone also works: build it and run `tools/sync_generated.sh wan_chai` (add `--drop`
first on a tree that already holds Causeway Bay). See
[`etl/README.md`](etl/README.md).

**Look at it.** Open the project (`open -a Godot --args --path "$PWD/game"`) and press **F5** to
play `scenes/main.tscn`, or **F6** on `scenes/dev/city_preview.tscn` to fly around the city.
**F3** cycles the debug overlay (`docs/ARCHITECTURE.md` "The debug overlay").

**Check it.**

```bash
.venv/bin/ruff check . && .venv/bin/ruff format --check .   # from the repo root
(cd etl && ../.venv/bin/pytest -n auto)
tools/check.sh
```

`tools/check.sh` runs `gdformat`, the settings and tuning-sidecar checks, the import, a GDScript
warnings sweep (warnings are errors, untyped declarations included) and the headless `verify_*.gd`
tools. Use its exit code: Godot itself exits `0` even when a script fails to parse. With no city
built, `VERIFY_GENERATED=0 tools/check.sh` skips the tools that need one. CI runs it that way,
beside `ruff` and `pytest`, so the generated-asset contracts are yours to run locally.

Grading tools in `tools/` measure a built region under `etl/out/` against the shipped tiles.
`.venv/bin/python tools/battery.py --list` says which change owes which.

**Export and play it in a browser.** Needs Godot's export templates.

```bash
tools/export.sh              # macOS + web; or one of macos|web|android|ios
tools/serve_web.py           # then open http://127.0.0.1:8060
```

Not `python -m http.server`: the build needs `SharedArrayBuffer`, which browsers gate behind
COOP/COEP headers that it does not send.

**Build it for an iPhone.** Needs Xcode, the iOS export templates and an Apple Developer team.

```bash
IOS_TEAM_ID=<team> tools/ios.sh device       # build, install and launch on the connected phone
IOS_TEAM_ID=<team> tools/ios.sh testflight   # archive and upload to TestFlight
```

The App Store listing is text in `fastlane/metadata/`. `tools/store_screenshots.sh` takes its
screenshots and `fastlane metadata` sends both, with an App Store Connect API key in the
environment (see `fastlane/Fastfile`).

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
| [`PRIVACY.md`](PRIVACY.md), [`SUPPORT.md`](SUPPORT.md) | The app's privacy policy and support page |

## Three things that will bite you

**Don't use the photogrammetry mesh.** The Lands Department also publishes a tile-based
oblique-photogrammetry model. It has ground gaps, level discontinuities, and cars fused into the
terrain. Use the **non-textured** models and **iB1000** instead.

**The road centrelines are 2D — grade separation is an attribute, not a Z value.** Road Network v2
carries no Z, only an integer `ELEVATION`. Only ever join edges at matching levels, but never key a
*node* on the level: every place two levels meet at a shared endpoint is a ramp touching down, and
splitting there severs the elevated network from the ground one.

**Where a deck actually is comes from the map sheets, not the road data.** The `INFRASTRUCTURE`
class in the LandsD sheets models the flyovers including their approach ramps, and it is the only
height source for off-grade roads. A tunnel is a void, so it has none.

## Data attribution

Contains geospatial data from the Lands Department, the Transport Department and the Highways
Department of the Government of the Hong Kong Special Administrative Region, which own the
intellectual property rights in that data, obtained via [DATA.GOV.HK](https://data.gov.hk) and the
[Common Spatial Data Infrastructure Portal](https://portal.csdi.gov.hk). Used under the DATA.GOV.HK
and CSDI Portal Terms and Conditions of Use. Data is provided "as is". The Government of the HKSAR
does not endorse this product.

## Licence

Three kinds of thing, three answers, because they have three different owners — plus one bundled
exception (`Q79`):

| What | Licence |
|---|---|
| **Code** — pipeline, engine scripts, tools, config, tuning | **GPL-3.0-or-later** ([`LICENSE`](LICENSE)) |
| **Hand-authored assets** — hero buildings, vehicles, UI, shaders (`game/assets/authored/`, `game/assets/shaders/`) | **CC BY-SA 4.0** ([`game/assets/authored/LICENSE`](game/assets/authored/LICENSE)) |
| **Generated city data** — tiles, road surface, road graph, fares | **Not relicensed by us.** Derived from HK government data under the DATA.GOV.HK and CSDI Portal Terms and Conditions of Use |
| **Bundled typefaces** — `game/assets/authored/fonts/` | **CC BY 4.0** and **SIL OFL 1.1**, third party — see [`LICENSING.md`](LICENSING.md) |

**This repository redistributes no government data** — `etl/sources/`, `etl/out/` and
`game/assets/generated/` are all gitignored. You regenerate them from the government endpoints
yourself and accept those terms directly. An exported *game* does ship them, and
that is what makes the credits screen mandatory rather than nice-to-have.

**GPLv3 conflicts with App Store distribution terms**, so store builds need a separate proprietary
grant — which works only while a single copyright holder owns everything, and therefore needs a CLA
before the first outside contribution. See [`LICENSING.md`](LICENSING.md), which is where
the reasoning and the open items live.
