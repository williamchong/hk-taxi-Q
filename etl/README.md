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
cd etl && ../.venv/bin/python -m pytest   # tests — testpaths is etl/tests
```

Lint and format from the **repo root**, not from here — the root `ruff.toml` extends this
project's rules to every Python file in the repo, including `tools/*.py`, which running ruff from
`etl/` silently skips:

```sh
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format .
```

## Fetching sources

```sh
../.venv/bin/python -m pipeline.fetch --region wan_chai --dry-run
../.venv/bin/python -m pipeline.fetch --region wan_chai
```

Wan Chai pulls **~320 MB** across 11 artefacts, of which 299 MB is the six building sheets
(41.7–55.9 MB each). Nothing needs scoping: `Q9` resolved on 2026-07-30 by dropping every GML
source from config — they duplicated the 17 MB FGDB at 539 MB — so the plain command is already
the cheap one. `--only` still exists for rebuilding a single source, and errors on an unknown name
rather than silently fetching nothing.

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
../.venv/bin/python -m pipeline.buildings --region wan_chai
```

Reads the cached sheets — no network — and writes `out/hong_kong/wan_chai/tiles/*.glb`, one merged,
vertex-coloured mesh per 150 m tile per LOD tier, plus a `buildings.json` intermediate. Wan Chai is
66 tiles × 2 tiers in a couple of seconds.

The palette, the sheet sub-directories to read, and the LOD cell sizes are all city config
(`buildings:` in the YAML). Nothing about Hong Kong is in the code.

The ground is one of those sub-directories since `P3-10`, so it tiles with everything else — with
its texture stripped, because the tile output carries none. Add `--terrain` to emit the **textured**
ground instead: that output is **evaluation only** and is not part of the tile set, because its
JPEGs are 224 MB for the region against a <128 MB texture budget. See `docs/DECISIONS.md`, `P1-2`.

Verify the result in the engine, which is the only place the acceptance criteria can be checked:

```sh
cp out/hong_kong/wan_chai/tiles/*.glb ../game/assets/generated/tiles/
godot --headless --path ../game --import
godot --headless --path ../game --script res://tools/verify_tiles.gd
```

## Road graph (`P1-3`)

```sh
../.venv/bin/python -m pipeline.roads --region wan_chai
```

Reads the cached geodatabase — no network, nothing unpacked, OGR opens it inside its zip — and
writes `out/hong_kong/wan_chai/roadgraph.json`. Wan Chai is 797 edges over 615 nodes with 217 turn
restrictions, in under a second.

Layer and column names are city config (`roads:` in the YAML), because they are the Transport
Department's schema rather than a fact about roads. The pipeline asks for a *role*.

To look at it beside the buildings:

```sh
cp out/hong_kong/wan_chai/roadgraph.json ../game/assets/generated/
```

then open `scenes/dev/city_preview.tscn` in Godot and press **F6**. The `Roads` node draws each
edge as a flat ribbon of its `width_m` with arrows along every one-way, which is what `Q12` — the
one acceptance criterion no test can settle — is asking you to check. Its `colouring` property
switches between direction, grade separation and speed limit. It ships hidden, because the road
*surface* now occupies the same heights; switch it on to read the graph rather than the road.

## Road surface (`P1-4`)

```sh
../.venv/bin/python -m pipeline.surface --region wan_chai
```

Reads `roadgraph.json` — not the geodatabase — and writes `out/hong_kong/wan_chai/roads.glb`:
28,423 triangles for the whole region, in under half a second. One mesh, one draw call, no
texture, and the same vertex-coloured treatment as the tiles.

Widening, kerb dimensions and colours are city config (`roads.surface:` in the YAML). The widening
is not cosmetic — `docs/GAME_DESIGN.md` fixes it at ~1.3–1.8× because real Wan Chai streets are
unforgiving at arcade speeds, and at 1.6× the region's six opposed carriageway pairs merge into one
continuous surface instead of leaving a slot down the middle of Lockhart Road.

Both of those are *at-grade* arguments, so `widen_by_elevation_level` holds structure to 1.0×. The
slot they argue against shows unshipped terrain at grade but the flyover deck up on structure, and
a viaduct is a fixed parapet-to-parapet width however fast it is signed.

The mesh is named `road_surface-col`, which is Godot's importer suffix for "build a static trimesh
collider from this". Collision is therefore part of the asset rather than something built at load.

```sh
cp out/hong_kong/wan_chai/roads.glb ../game/assets/generated/
godot --headless --path ../game --import
godot --headless --path ../game --script res://tools/verify_road_surface.gd
```

That last command is the engine-side half of the acceptance criteria — one draw call, vertex
colours, UVs for the markings shader, no texture, and a `ConcavePolygonShape3D` that actually
imported. None of it is visible from Python.

## The whole region (`P1-6`, `P1-7`)

```sh
../.venv/bin/python -m pipeline --region wan_chai
```

Runs all six stages in dependency order — fetch, buildings, roads, surface, fares, export — in
**4.4 s** for Wan Chai against a warm cache, and writes `out/hong_kong/wan_chai/city.json`. Each
stage is invoked through the same entry point its own command uses, so a full build and a partial
one cannot drift. `--from roads` resumes mid-chain; a stage that exits non-zero stops the run.

The export stage also validates what it wrote, against the documents it was derived from rather
than against itself:

```sh
../.venv/bin/python -m pipeline.export --region wan_chai --check
```

Then put it in front of the engine. This is the only supported way — it copies exactly the files
`city.json` names, so the two stage intermediates in the same directory (`buildings.json`,
`roadsurface.json`) cannot reach the bundle, and it removes tiles a previous build left behind:

```sh
cd .. && tools/sync_generated.sh hong_kong wan_chai
godot --headless --path game --script res://tools/verify_city.gd
```

`verify_city.gd` is the engine-side half of `P1-7`'s acceptance: it measures every imported LOD0
mesh and compares it to the `aabb` this pipeline recorded, to 1 cm. That round trip cannot be
checked from Python, which never sees an importer. Then open `game/scenes/dev/city_preview.tscn`
and press **F6** to look at the result, or `scenes/main.tscn` to drive it.

## Layout

| Path | Contains |
|---|---|
| `config/hong_kong.yaml` | **Every** city specific — CRS, bounds, deck heights, palette, source URLs |
| `pipeline/config.py` | Loads and validates city config; nothing else reads the YAML |
| `pipeline/crs.py` | The only module that converts projected coordinates to game space |
| `pipeline/fetch.py` | Downloads and caches sources; derives tile sets from published indexes |
| `pipeline/gltf.py` | glTF reading and GLB writing — no library, see the module docstring |
| `pipeline/mesh.py` | Merge, partition and LOD-collapse meshes. Geometry only, no policy |
| `pipeline/buildings.py` | Sheets → vertex-coloured tiles. Where the policy lives |
| `pipeline/gdb.py` | Geodatabase layers and WKB → numpy. Format only, no policy |
| `pipeline/terrain.py` | Terrain mesh → a sampleable height field (`Q11`) |
| `pipeline/roads.py` | Road network → `roadgraph.json`. Where the policy lives |
| `pipeline/surface.py` | `roadgraph.json` → `roads.glb`. Ribbon, kerbs, junction caps, collision |
| `pipeline/fares.py` | Taxi stands and pick-up points → `fares.json`, snapped to the graph |
| `pipeline/export.py` | Stage outputs → `city.json`, plus the cross-document validation |
| `pipeline/documents.py` | Read and write a versioned JSON document. Its own module because stages consume each other's output in both directions |
| `pipeline/__main__.py` | `python -m pipeline` — every stage, in dependency order |
| `sources/<source>/` | Raw downloads and `manifest.json` — gitignored |
| `out/<region>/` | Pipeline output — gitignored |

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
