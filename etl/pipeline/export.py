"""Stage outputs to the shipped manifest (`P1-6`).

Every earlier stage writes what it alone knows. This one reconciles them into
`city.json` — the single document the game opens first, per the contract in
`docs/ARCHITECTURE.md` — and then checks that the set it just described is
actually coherent.

Three decisions are worth stating, because the file's shape follows from them:

- **`city.json` references, it does not inline.** The road graph is 0.65 MB on
  disk and ~6 MB parsed, and the fare nodes are read by a different system at a
  different time; folding them in would make every consumer parse both to learn
  where a tile is. Each is separately versioned in the contract and stays a
  separate file.
- **`buildings.json` and `roadsurface.json` do not ship.** They are stage
  intermediates whose only reader is this module. What the game needs from
  them — tile paths, AABBs, the surface mesh name — is either copied into
  `city.json` or recoverable from the GLB itself.
- **`bounds_game` is the union of the content, not the region rectangle.**
  Wan Chai's declared region is 1650 x 887 m, but the tiles reach 1657 x 923 m
  because a building is assigned to a tile whole and may overhang it. A
  consumer sizing a spatial partition or framing a camera off the rectangle
  would clip real geometry, so this reports what is there.

`validate` checks what no single stage checks. A fare node naming an edge the
graph does not have, a tile whose GLB never got written, two documents built
from different runs, a manifest listing tiles the building stage did not build
— each stage's own output is internally fine in all four cases, and the last
three are only visible from here.

Every assertion the manifest makes is checked against the document it was
derived from, never against the manifest itself. A stale `city.json` is
perfectly self-consistent — its tile list and its bounds were written in the
same breath — so checking it against itself confirms nothing.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from pipeline import __version__
from pipeline.arrows import ARROWS_MANIFEST_NAME, ARROWS_MANIFEST_SCHEMA
from pipeline.boxjunctions import BOXJUNCTIONS_MANIFEST_NAME, BOXJUNCTIONS_MANIFEST_SCHEMA
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA
from pipeline.clearance import CLEARANCE_NAME, CLEARANCE_SCHEMA, NOT_MEASURED
from pipeline.config import (
    LANDMARK_ASSET_ROOT,
    LANDMARK_GENERATED_ROOT,
    CityConfig,
    load_city,
)
from pipeline.crs import GameTransform
from pipeline.documents import read_document, round_position, write_document
from pipeline.fares import FARES_NAME, FARES_SCHEMA
from pipeline.gltf import Bounds
from pipeline.lamps import LAMPS_MANIFEST_NAME, LAMPS_MANIFEST_SCHEMA
from pipeline.landmarks import ASSETS_NAME, ASSETS_SCHEMA, landmark_in_region
from pipeline.railings import RAILINGS_MANIFEST_NAME, RAILINGS_MANIFEST_SCHEMA
from pipeline.roadmarks import ROADMARKS_MANIFEST_NAME, ROADMARKS_MANIFEST_SCHEMA
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA
from pipeline.signals import SIGNALS_MANIFEST_NAME, SIGNALS_MANIFEST_SCHEMA
from pipeline.signs import SIGNS_MANIFEST_NAME, SIGNS_MANIFEST_SCHEMA
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, SURFACE_NAME
from pipeline.tramway import TRAMWAY_MANIFEST_NAME, TRAMWAY_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

CITY_NAME = "city.json"
# 3: the finest tier of every tile ships a `-col` collider. The document's own
# keys did not change, and the bump is deliberate anyway — a build reading v2
# would load v3 tiles happily and put a car through a wall, which is a silent
# wrong answer rather than a missing field. The version gates the whole asset
# set, not just the JSON.
# 4 since `Q23`: `carriageway[].half_width_m` is a list, one value per station
# of that edge's polyline, where it used to be one number for the whole edge.
# This is the rarer kind of bump — a field that changed *shape* rather than
# meaning — and it is still the same rule: a v3 reader would take a float and
# get an array.
# 5 since `P3-7`: every tile ships `TEXCOORD_0` and names its material
# `city_facade`. Neither is a manifest key, and the bump is the same rule as 3 —
# a v4 reader would load a v5 tile happily, ignore the payload, and draw a blank
# city that reads as a shader bug rather than as a version mismatch. The version
# gates the asset set, not just the JSON.
# 6 since `Q40`/`Q41`: every tile ships `TEXCOORD_1` — a packed per-building
# facade-survey state in `x` (glazed / tint bin / grammar, 0 = refused → hash)
# with `y` reserved for `Q42`'s riders. Same rule as 5: a v5 reader would load
# a v6 tile, ignore the payload, and silently draw the hash city while the
# bundle claims the survey.
# 7 since `P3-6`: the manifest names `landmarks.json`, and the tiles no longer
# contain the buildings its heroes replace. The bump is for the *removal*: a
# v6 reader would load v7 tiles happily and draw holes where the excluded
# buildings stood, with no hero over them — the silent wrong answer again.
# The version gates the whole asset set, not just the JSON.
# 8 since the HKCEC repaint (`P3-6` amendment): the manifest names generated
# hero assets under `landmark_assets`, and the committed
# `assets/authored/landmarks/hkcec.glb` a v7 bundle's `landmarks.json` points
# at no longer exists in the repo. Not a bump for the added keys — an old
# reader ignoring those would be right — but for the asset set again: a v7
# generated directory would place a hero from a path that now loads nothing,
# and draw the hole the v7 bump itself was written against.
# 9 since `Q51`: `carriageway[]` carries `clear_width_m` beside the drawn width,
# and the manifest publishes `lane_width_m` as the bar it is read against. The
# silent wrong answer again, and the worst-shaped one yet: a v8 reader would
# load a v9 bundle happily and route traffic down edges the bundle itself
# records as holding less than a lane clear.
# 10 since `P3-12`: `roads.glb` gained a `TEXCOORD_1` marking payload and a
# material name the engine dispatches a shader on. `P3-7`'s precedent — adding a
# vertex attribute bumped 4 to 5 — rather than `P3-10`'s, which added none and
# did not bump. The wrong answer here is quieter than `Q51`'s and still worth
# the bump: a v9 reader hands the surface a `BaseMaterial3D` and gets an
# unmarked road, which looks like the road it always drew rather than like a
# failure.
# 11 since `P3-14`: the manifest names `tram.glb`, a new shipped asset. The
# `landmark_assets` precedent decides it — 7 and 8 both bumped because "the
# asset set a v-N document describes" had changed, and `shipped()` is what turns
# that set into a PCK. A v10 reader draws no tramway, which on its own would be
# `P3-10`'s no-bump case; what it also does is compute a shipped set that is
# missing a file the bundle depends on, and being wrong about the contents of
# the bundle is the thing this number is for.
#
# ⚠️ The key is **optional and may be null**: a city whose estate publishes no
# tramway ships none. So it is deliberately not in `DOCUMENT_KEYS`, which
# `REQUIRED_KEYS` and `shipped()` both treat as always-present.
# 12 since `P3-15`: the manifest names `arrows.glb`, a new shipped asset, on
# exactly `P3-14`'s argument — a v11 reader computes a shipped set missing a file
# the bundle depends on, and being wrong about the contents of the bundle is what
# this number is for. The key is optional and nullable for the same reason
# `tramway` is: a city whose estate publishes no marking symbols ships none.
# 13 since `P3-18`: the manifest names `boxjunctions.glb`, a new shipped asset —
# `P3-14`/`P3-15`'s argument a third time, unchanged: a v12 reader computes a
# shipped set missing a bundle file. The key is optional and nullable like
# `tramway` and `arrows`: a city whose estate publishes no box polygons ships
# none.
# 14 since `P3-19`: the manifest names `railings.glb`, a new shipped asset —
# `P3-14`/`P3-15`/`P3-18`'s argument a fourth time, unchanged: a v13 reader
# computes a shipped set missing a bundle file. The key is optional and nullable
# like the three before it: a city whose estate publishes no railing layer ships
# none, and so does one that publishes it and finds no kerb to hang it on.
# 15 since `P3-16`: the manifest names `signs.glb`, a new shipped asset — the
# same argument a fifth time, unchanged: a v14 reader computes a shipped set
# missing a bundle file. The key is optional and nullable like the four before
# it: a city whose estate publishes no sign layer ships none, and so does one
# that publishes it and whose signs are all text-faced.
# 16 since `P3-23`: the manifest names `roadmarks.glb`, a new shipped asset —
# the same argument a sixth time, unchanged: a v15 reader computes a shipped set
# missing a bundle file. The key is optional and nullable like the five before
# it: a city whose estate publishes no transverse markings ships none, and so
# does one that publishes them and finds no road drawn across.
# 18 since `P3-17`: the manifest names `signals.glb`, the published traffic
# signal heads drawn from TD's `DTAD_TRAFFIC_LIGHT_PT`. The same argument an
# eighth time — a v17 reader computes a shipped set missing a bundle file.
# 17 since `Q70`: the manifest names `signs_text.png`, the sign lettering's
# atlas, which used to ride inside `signs.glb` as an embedded buffer view. The
# same argument as 11 through 16 — a v16 reader computes a shipped set missing a
# file the bundle depends on — but arrived at from the other direction, and the
# direction is the finding. Godot's importer *extracts* an embedded image beside
# the asset, so the bundle already had a seventh file here; what it did not have
# was a manifest that knew, and `sync_generated.sh` deletes what the manifest
# does not name. The bump is for the asset set, and the key is optional and
# nullable like the six before it: a region whose faces carry no lettering bakes
# no atlas, and so does a city whose whitelist has none.
# 19 since `P3-26`: the manifest names `lamps.glb`, the published lamp posts
# drawn from iB1000's `UtilityPoint`. The same argument a ninth time — a v18
# reader computes a shipped set missing a bundle file. The key is optional and
# nullable like the seven before it: a city whose estate publishes no utility
# point layer ships none, and so does one that publishes it and finds no kerb to
# stand a column on.
CITY_SCHEMA = 19

# The hero-building placement document (`P3-6`), written by this stage from the
# city config — ~2 entries derived from `landmarks:` plus one CRS conversion,
# which is why it is assembled here rather than by a stage of its own. The
# contract is in `docs/ARCHITECTURE.md`. The `.glb`s it points at are either
# committed under `res://assets/authored/landmarks/` and deliberately outside
# `shipped()` (they are not build output), or — for mesh-sourced heroes —
# built by `pipeline/landmarks.py` into the out tree, named in the manifest
# under `landmark_assets`, and shipped like any tile.
# Schema 2 with the HKCEC repaint: entries carry `triangle_budget`, and the
# asset set a v1 document describes (all-authored, all-committed) is gone —
# same argument as `CITY_SCHEMA` 8.
LANDMARKS_NAME = "landmarks.json"
LANDMARKS_SCHEMA = 2

# Manifest keys naming a document that ships. One tuple rather than a literal
# at each use, because `shipped` reads them and `REQUIRED_KEYS` guards them:
# a fourth document added to one and not the other is a `KeyError` raised from
# inside the validator instead of a finding reported by it.
DOCUMENT_KEYS = ("road_graph", "road_surface", "fares", "landmarks")

# Manifest keys naming an asset that ships **when the region has one**, in the
# order `shipped()` lists them. Optional and nullable every one: a city whose
# estate publishes no tramway, no marking symbols, no box polygons, no lamp
# posts, no railing layer, no sign layer, no transverse markings or no sign
# lettering ships none.
#
# ⚠️ **A tuple because this was seven hand-written copies of one `if`**, and the
# repo's own trigger — `mesh_contract.gd`'s "a third copy should force it"
# (`Q58`) — had been quoted in the commit that added the seventh. A new asset is
# now one row here, and `game/scripts/city/city_manifest.gd`'s `shipped()` holds
# the same list in the same order so the two can be read as mirrors.
OPTIONAL_ASSET_KEYS = (
    "tramway",
    "arrows",
    "boxjunctions",
    "lamps",
    "railings",
    "signs",
    "signs_text_atlas",
    "roadmarks",
    "signals",
)
REQUIRED_KEYS = (*DOCUMENT_KEYS, "tiles", "landmark_assets", "bounds_game")

# Positions are written at millimetre precision, and `bounds_game` is rounded
# from the same values. Rounding both can push a coordinate a hair outside its
# own bounding box, so the containment checks allow exactly that much.
_TOLERANCE_M = 0.001


@dataclass(frozen=True)
class Input:
    """A stage output this reads, and the command that regenerates it."""

    name: str
    schema: int
    # A module, not a description: the error message pastes into a shell.
    module: str

    def read(self, out_dir: Path, city_id: str, region_id: str) -> dict:
        rebuild = f"python -m pipeline.{self.module} --city {city_id} --region {region_id}"
        return read_document(out_dir / self.name, self.schema, rebuild)


INPUTS: tuple[Input, ...] = (
    Input(BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA, "buildings"),
    Input(ASSETS_NAME, ASSETS_SCHEMA, "landmarks"),
    Input(SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, "surface"),
    Input(CLEARANCE_NAME, CLEARANCE_SCHEMA, "clearance"),
    Input(ROADGRAPH_NAME, ROADGRAPH_SCHEMA, "roads"),
    Input(FARES_NAME, FARES_SCHEMA, "fares"),
    Input(TRAMWAY_MANIFEST_NAME, TRAMWAY_MANIFEST_SCHEMA, "tramway"),
    Input(ARROWS_MANIFEST_NAME, ARROWS_MANIFEST_SCHEMA, "arrows"),
    Input(BOXJUNCTIONS_MANIFEST_NAME, BOXJUNCTIONS_MANIFEST_SCHEMA, "boxjunctions"),
    Input(LAMPS_MANIFEST_NAME, LAMPS_MANIFEST_SCHEMA, "lamps"),
    Input(RAILINGS_MANIFEST_NAME, RAILINGS_MANIFEST_SCHEMA, "railings"),
    Input(SIGNS_MANIFEST_NAME, SIGNS_MANIFEST_SCHEMA, "signs"),
    Input(ROADMARKS_MANIFEST_NAME, ROADMARKS_MANIFEST_SCHEMA, "roadmarks"),
    Input(SIGNALS_MANIFEST_NAME, SIGNALS_MANIFEST_SCHEMA, "signals"),
)


@dataclass
class ExportReport:
    tiles: int = 0
    lod_files: int = 0
    fare_nodes: int = 0
    edges: int = 0
    bounds: Bounds = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    # Every byte a build would ship for this region — the manifest, the three
    # documents it names, and every tile GLB. The bundle budget is 200 MB.
    shipped_bytes: int = 0
    shipped_files: int = 0


class Box:
    """A growing axis-aligned bounding box.

    Starts empty rather than at the origin: a box seeded with `Vector3.ZERO`
    would report a region reaching back to (0, 0, 0) whatever its contents do,
    which is the same trap `road_preview.gd` sidesteps with its `measured` flag.
    """

    def __init__(self) -> None:
        self.low: list[float] | None = None
        self.high: list[float] | None = None

    def add(self, point: Sequence[float]) -> None:
        if self.low is None or self.high is None:
            self.low = [float(value) for value in point]
            self.high = list(self.low)
            return
        for axis in range(3):
            self.low[axis] = min(self.low[axis], float(point[axis]))
            self.high[axis] = max(self.high[axis], float(point[axis]))

    def add_box(self, aabb: Sequence[Sequence[float]]) -> None:
        self.add(aabb[0])
        self.add(aabb[1])

    def corners(self) -> Bounds:
        if self.low is None or self.high is None:
            raise ValueError("nothing was added to this box")
        low, high = self.low, self.high
        return ((low[0], low[1], low[2]), (high[0], high[1], high[2]))


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    out_root: Path | None = None,
    generated_utc: str | None = None,
) -> ExportReport:
    """Write `city.json` from the stage outputs already in the region's out dir.

    `generated_utc` is injectable so a test can pin it. It is the one field
    that changes on every run, which makes a plain diff of two builds useless
    for answering "did anything actually change?" — pass it, or strip it, when
    that is the question.
    """
    out_dir, documents = _inputs(city, region_id, out_root)
    buildings = documents[BUILDINGS_MANIFEST_NAME]
    surface = documents[SURFACE_MANIFEST_NAME]
    clearance = documents[CLEARANCE_NAME]
    graph = documents[ROADGRAPH_NAME]
    fares = documents[FARES_NAME]
    tramway = documents[TRAMWAY_MANIFEST_NAME]
    arrows = documents[ARROWS_MANIFEST_NAME]
    boxjunctions = documents[BOXJUNCTIONS_MANIFEST_NAME]
    lamps = documents[LAMPS_MANIFEST_NAME]
    railings = documents[RAILINGS_MANIFEST_NAME]
    signs = documents[SIGNS_MANIFEST_NAME]
    roadmarks = documents[ROADMARKS_MANIFEST_NAME]
    signals = documents[SIGNALS_MANIFEST_NAME]

    tiles = [
        {
            "id": tile["id"],
            # Nearest-first, one file per tier. The dicts in `buildings.json`
            # carry triangle and byte counts too; those are build diagnostics
            # and the streamer has no use for them.
            "lods": [lod["path"] for lod in tile["lods"]],
            "aabb": tile["aabb"],
        }
        for tile in buildings["tiles"]
    ]

    box = Box()
    for tile in tiles:
        box.add_box(tile["aabb"])
    box.add_box(surface["aabb"])
    # The graph and the fare nodes are inside the drawn surface almost
    # everywhere, but not by construction: an edge trimmed to nothing at a
    # junction leaves a centreline the ribbon never covered.
    for point in _graph_points(graph):
        box.add(point)
    for node in fares["nodes"]:
        box.add(node["pos"])

    transform = city.game_transform(region_id)
    landmarks = _landmarks_document(city, region_id, buildings, transform)
    write_document(out_dir / LANDMARKS_NAME, landmarks)
    assets = documents[ASSETS_NAME]
    # The excluded footprints join the union: the authored hero stands where
    # the excluded buildings stood, so without this the bounds would shrink by
    # exactly the geometry the region still contains.
    for entry in landmarks["landmarks"]:
        if entry["excluded_bounds"] is not None:
            box.add_box(entry["excluded_bounds"])

    low, high = box.corners()
    document = {
        "schema_version": CITY_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "source_crs": city.projected_crs,
        # Enough to put a game-space position back on the map: the game never
        # needs it, but anything comparing against the source data does.
        "origin": {
            "easting": transform.origin_easting,
            "northing": transform.origin_northing,
            "elevation": transform.origin_elevation,
        },
        "city_offset": round_position(city.city_offset(region_id)),
        "bounds_game": {"min": round_position(low), "max": round_position(high)},
        "tile_size_m": buildings["tile_size_m"],
        "tiles": tiles,
        "road_graph": ROADGRAPH_NAME,
        "road_surface": SURFACE_NAME,
        # Drawn half-width per edge, carried from the surface stage rather than
        # recomputed. `roadgraph.json` publishes the *authored* street width and
        # `config.py` keeps the playability widening on the surface style on
        # purpose — "a change here never changes `roadgraph.json`" — so this is
        # the only route by which the game can know how wide the tarmac it is
        # driving on actually is. `P2-2` needs it to place a car in the nearside
        # lane instead of on the ribbon seam. Same category as `tiles[].aabb`:
        # geometry the runtime cannot derive, measured once by the stage that
        # drew it.
        "carriageway": _carriageway(surface, clearance),
        # The bar `clear_width_m` is read against, published once rather than
        # left to the game to re-derive. `roadgraph.json`'s `width_m` is
        # `lanes x lane_width_m` *hand-tuned upward for playability*, so
        # dividing it back by `lanes` does not recover this number.
        "lane_width_m": city.roads.lane_width_m,
        "fares": FARES_NAME,
        # `null` where the city drew no tramway, which is the honest answer and
        # not an omission — see `pipeline/tramway.py`. The asset is named from
        # the stage's own manifest rather than from `TRAMWAY_NAME` directly, so
        # a stage that read the source and found nothing cannot be contradicted
        # here by a constant.
        "tramway": tramway["asset"],
        # `null` where the city drew no turn arrows, on the same terms as
        # `tramway` above and read from the stage's own manifest for the same
        # reason: a region whose symbols all failed the join must not be
        # contradicted here by a constant.
        "arrows": arrows["asset"],
        # `null` where the city drew no box junctions, on `tramway`'s terms and
        # read from the stage's own manifest for its reason: a region whose
        # boxes all failed the join must not be contradicted here by a constant.
        "boxjunctions": boxjunctions["asset"],
        "lamps": lamps["asset"],
        "railings": railings["asset"],
        # `null` where the city drew no traffic signs, on `tramway`'s terms and
        # read from the stage's own manifest for its reason. ⚠️ Null is the
        # ordinary answer for a region whose signs are all text-faced, because
        # `Q42` refuses those — see `pipeline/signs.py`.
        "signs": signs["asset"],
        # 🔴 **The one image in the bundle, named** (`Q70`, `Q63`). `null` where
        # the region baked no lettering, on `tramway`'s terms. It is here because
        # of what the *engine* does with an embedded one: Godot extracts it to a
        # PNG beside the asset, and a file in `game/assets/generated/` that this
        # document does not name is a file `sync_generated.sh` sweeps — which it
        # did, on every run, leaving `verify_signs.gd` red. The atlas ships
        # beside `signs.glb` now and this key is what keeps it there.
        "signs_text_atlas": signs["text_atlas"],
        # `null` where the city drew no stop or give-way lines, on `tramway`'s
        # terms and read from the stage's own manifest for its reason: a region
        # whose markings all failed the transverse join must not be contradicted
        # here by a constant.
        "roadmarks": roadmarks["asset"],
        # `null` where the city drew no signal heads, on `tramway`'s terms. ⚠️ An
        # ordinary answer for a region whose estate publishes no signal layer —
        # and `P3-17` refuses everything its gate does not admit, so a region
        # whose codes are spelled differently draws none and is correct to.
        "signals": signals["asset"],
        "landmarks": LANDMARKS_NAME,
        # The mesh-sourced hero models `pipeline/landmarks.py` built — shipped
        # files like the tile GLBs, unlike the committed authored heroes,
        # which the manifest never names (`P3-6` amendment).
        "landmark_assets": sorted(str(asset["path"]) for asset in assets["assets"]),
        "etl_version": __version__,
        "generated_utc": generated_utc or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # The manifest itself ships too, so it counts in both totals.
    manifest_bytes = write_document(out_dir / CITY_NAME, document)
    names = shipped(document)
    return ExportReport(
        tiles=len(tiles),
        lod_files=sum(len(tile["lods"]) for tile in tiles),
        fare_nodes=len(fares["nodes"]),
        edges=len(graph["edges"]),
        bounds=box.corners(),
        # A missing file counts as zero rather than raising: reporting it is
        # `validate`'s job, and it says which file and why.
        shipped_bytes=manifest_bytes + sum(_size(out_dir / name) for name in names),
        shipped_files=len(names) + 1,
    )


def _inputs(
    city: CityConfig, region_id: str, out_root: Path | None
) -> tuple[Path, dict[str, dict]]:
    """The region's out directory and every stage output in it.

    Both `build_region` and `validate` need all four — the second reads them
    again from disk rather than being handed the first's copies, because
    `--check` runs it on its own and because re-reading is what makes it a
    check of the files rather than of memory.
    """
    out_dir = city.out_dir(region_id, out_root)
    return out_dir, {source.name: source.read(out_dir, city.id, region_id) for source in INPUTS}


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _carriageway(surface: dict, clearance: dict) -> list[dict]:
    """The per-station carriageway table the game reads.

    Two stages measured this and neither could have measured both — `surface.py`
    knows how wide it drew the ribbon, `clearance.py` knows what stands in it —
    so the join happens here, where every other reconciliation of the stage
    outputs already does. `trim_m` does not travel: it is how a ribbon met its
    junction caps, which is a question the game never asks.

    Refused rather than padded when the two disagree about an edge. `P2-2` warns
    and falls back on a short half-width array because a lane centre off the
    tarmac is survivable; a short *clearance* array is not the same kind of
    mistake, because the station it fails to describe is the one a router would
    then believe is clear.
    """
    measured = {int(entry["edge"]): entry["clear_width_m"] for entry in clearance["clearance"]}
    table = []
    for entry in surface["carriageway"]:
        edge_id = int(entry["edge"])
        halves = entry["half_width_m"]
        clear = measured.get(edge_id)
        if clear is None or len(clear) != len(halves):
            raise ValueError(
                f"edge {edge_id} has {len(halves)} drawn half-widths and "
                f"{'no' if clear is None else len(clear)} clearances; "
                f"{SURFACE_MANIFEST_NAME} and {CLEARANCE_NAME} are from different runs"
            )
        if any(width < 0.0 and width != NOT_MEASURED for width in clear):
            raise ValueError(f"edge {edge_id} publishes a negative clearance that is not a refusal")
        table.append({"edge": edge_id, "half_width_m": halves, "clear_width_m": clear})
    return table


def _landmarks_document(
    city: CityConfig, region_id: str, buildings: dict, transform: GameTransform
) -> dict:
    """The hero-placement document (`P3-6`), from config plus what the
    building stage actually dropped.

    Only landmarks inside this region's rectangle ship with it — `config.py`
    guarantees each lies in *some* region, and a hero belongs to the region
    that contains it. Positions arrive in the projected CRS and leave in game
    space; this is the one conversion, so nothing downstream ever sees an
    easting.

    `excluded_bounds` is the game-space union, over the entry's stems, of the
    AABBs `buildings.json` recorded at exclusion time — the geometry the
    in-engine verifier probes the tiles against. `None` when no stem matched
    anything; written rather than omitted so `validate` reports the mismatch
    instead of this function hiding it.
    """
    high_x, high_z = city.region_high(region_id)
    excluded = buildings.get("excluded", {})
    entries = []
    for landmark in city.landmarks:
        # The shared predicate, deliberately: the landmarks stage builds the
        # models this document places, and two spellings of "in this region"
        # is how a model ends up built with no entry, or placed with no model.
        if not landmark_in_region(landmark, transform, high_x, high_z):
            continue
        x, y, z = transform.to_game(landmark.easting, landmark.northing, landmark.elevation)
        bounds = None
        recorded = [excluded[stem] for stem in landmark.replaces_source_ids if stem in excluded]
        if recorded:
            union = Box()
            for aabb in recorded:
                union.add_box(aabb)
            low, high = union.corners()
            bounds = [round_position(low), round_position(high)]
        entries.append(
            {
                "id": landmark.id,
                "asset": landmark.asset,
                "transform": {
                    "pos": round_position((x, y, z)),
                    # A compass bearing — 0 at north, rising eastward, the
                    # `CityManifest.bearing_deg` convention. The game converts.
                    "rot_y_deg": landmark.rot_y_deg,
                },
                "name": {"en": landmark.name_en, "zh": landmark.name_zh},
                "replaces_source_ids": list(landmark.replaces_source_ids),
                "excluded_bounds": bounds,
                # What `verify_landmarks.gd` holds the placed model to —
                # config data, carried so the ceiling lives with the entry it
                # grades rather than as an in-engine constant.
                "triangle_budget": landmark.triangle_budget,
            }
        )
    return {
        "schema_version": LANDMARKS_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "landmarks": entries,
    }


# The manifest read back as an `Input`, which is what it is once written — same
# version refusal, same rebuild hint, no second copy of the command string. It
# stays out of `INPUTS` because that tuple is what this stage *reads to write
# it*; this is for the two callers that read back what it wrote.
_MANIFEST = Input(CITY_NAME, CITY_SCHEMA, "export")

# Same standing as `_MANIFEST`: written by this stage, read back by `validate`.
_LANDMARKS = Input(LANDMARKS_NAME, LANDMARKS_SCHEMA, "export")


def read_manifest(city: CityConfig, region_id: str, *, out_root: Path | None = None) -> dict:
    """The region's `city.json`, refusing a stale one by schema version."""
    return _MANIFEST.read(city.out_dir(region_id, out_root), city.id, region_id)


def shipped(manifest: dict) -> list[str]:
    """Every file `city.json` names, relative to the region's out directory.

    `city.json` itself is not in the list — it names the others, not itself —
    so a caller copying a region wants this plus the manifest.

    The definition of "what a build copies into the game", and the reason the
    intermediates can sit in the same directory without being shipped by
    accident: this list is derived from the manifest, never from a directory
    listing.
    """
    paths = [str(manifest[key]) for key in DOCUMENT_KEYS]
    for tile in manifest.get("tiles", []):
        paths.extend(str(lod) for lod in tile.get("lods", []))
    paths.extend(str(path) for path in manifest.get("landmark_assets", []))
    # ⚠️ **Key by key, and `signs_text_atlas` independently of `signs`.** The two
    # are written together and a bundle with one and not the other is broken, but
    # this list is the definition of what a build copies — treating the pair as
    # one would hide the asymmetric case from the only thing that could show it.
    paths.extend(str(manifest[key]) for key in OPTIONAL_ASSET_KEYS if manifest.get(key))
    return paths


def _graph_points(graph: dict) -> Iterable[Sequence[float]]:
    for node in graph.get("nodes", []):
        yield node["pos"]
    for edge in graph.get("edges", []):
        yield from edge["polyline"]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def validate(city: CityConfig, region_id: str, *, out_root: Path | None = None) -> list[str]:
    """Everything wrong with the exported set, as human-readable lines.

    Scoped to what no single stage checks. Some of that crosses a document
    boundary — a fare node naming an edge the graph does not have — and some is
    simply unclaimed: nothing validates the road graph's internal references
    either, because the stage that writes it builds them correct by
    construction and cannot see them go stale afterwards.

    Everything the manifest asserts is checked against the document it came
    from, never against the manifest itself. That is the difference between
    catching a stale `city.json` and confirming it is self-consistent, which
    it always is.

    Returns rather than raises, so one run reports every problem instead of the
    first one. A version mismatch still raises — that is a stale build, not a
    finding, and the message names the command that fixes it.
    """
    out_dir, documents = _inputs(city, region_id, out_root)
    manifest = read_manifest(city, region_id, out_root=out_root)

    missing = [key for key in REQUIRED_KEYS if key not in manifest]
    if missing:
        # Nothing below can be trusted without these, so stop here rather than
        # report a cascade of consequences.
        return [f"{CITY_NAME} is missing {', '.join(missing)}"]

    buildings = documents[BUILDINGS_MANIFEST_NAME]
    landmarks = _LANDMARKS.read(out_dir, city.id, region_id)
    return [
        *_check_identity(manifest, {**documents, LANDMARKS_NAME: landmarks}),
        *_check_files(out_dir, manifest),
        *_check_tiles(manifest, buildings),
        *_check_fares(documents[FARES_NAME], documents[ROADGRAPH_NAME]),
        *_check_graph(documents[ROADGRAPH_NAME]),
        *_check_landmarks(manifest, landmarks, buildings, documents[ASSETS_NAME]),
        *_check_bounds(manifest, documents),
    ]


def _check_identity(manifest: dict, documents: dict[str, dict]) -> list[str]:
    """Every document names the same city and region.

    The cheapest detector of a half-rebuilt directory: run the road stage
    against a second region without clearing the first, and the graph disagrees
    with everything around it while remaining perfectly valid on its own.
    """
    expected = (manifest.get("city_id"), manifest.get("region_id"))
    return [
        f"{name} is for {document.get('city_id')}/{document.get('region_id')}, "
        f"{CITY_NAME} for {expected[0]}/{expected[1]}"
        for name, document in documents.items()
        if (document.get("city_id"), document.get("region_id")) != expected
    ]


def _check_files(out_dir: Path, manifest: dict) -> list[str]:
    problems: list[str] = []
    for relative in shipped(manifest):
        try:
            size = (out_dir / relative).stat().st_size
        except FileNotFoundError:
            problems.append(f"{CITY_NAME} names {relative}, which does not exist")
            continue
        if size == 0:
            problems.append(f"{relative} is empty")
    return problems


def _check_tiles(manifest: dict, buildings: dict) -> list[str]:
    """The manifest lists exactly the tiles the building stage built.

    Compared against `buildings.json` rather than checked for internal
    consistency, because a manifest left over from a previous run is perfectly
    consistent with itself — it simply describes a region that no longer
    exists, and its tile list is the part of it a rebuild is most likely to
    change.
    """
    problems: list[str] = []
    listed: set[str] = set()
    for tile in manifest["tiles"]:
        tile_id = str(tile.get("id"))
        if tile_id in listed:
            problems.append(f"two tiles share the id {tile_id}")
        listed.add(tile_id)
        if not tile.get("lods"):
            problems.append(f"tile {tile_id} has no LOD files")
        low, high = tile["aabb"]
        if any(high[axis] < low[axis] for axis in range(3)):
            problems.append(f"tile {tile_id} has an inverted aabb")

    built = {str(tile.get("id")) for tile in buildings.get("tiles", [])}
    if missing := sorted(built - listed):
        problems.append(
            f"{len(missing)} tiles in {BUILDINGS_MANIFEST_NAME} are not in {CITY_NAME}: "
            f"{missing[:5]}"
        )
    if extra := sorted(listed - built):
        problems.append(
            f"{len(extra)} tiles in {CITY_NAME} were not built by "
            f"{BUILDINGS_MANIFEST_NAME}: {extra[:5]}"
        )
    return problems


def _check_landmarks(manifest: dict, landmarks: dict, buildings: dict, assets: dict) -> list[str]:
    """The heroes and the exclusions agree, in both directions (`P3-6`).

    One direction catches a typo'd stem — a landmark claiming a building the
    stage never saw, which would z-fight the moment the model lands on the
    still-present source. The other catches an orphaned exclusion — a hole in
    the city with no hero over it. Neither side can see the mismatch alone:
    the config is internally fine, and so is `buildings.json`.

    The *authored* `.glb` assets are `res://` paths into the committed game
    tree, so they are deliberately **not** checked as files here — `shipped()`
    never lists them, and this stage's out-tree does not contain them. The
    *mesh-sourced* ones are build output like any tile: `landmark_assets.json`
    names them, the manifest carries them under `landmark_assets`, and
    `_check_files` stats them; this check holds the three spellings of each
    path — config asset, built path, manifest list — to one another.
    """
    problems: list[str] = []
    entries = landmarks.get("landmarks", [])
    built = {str(asset.get("id")): str(asset.get("path")) for asset in assets.get("assets", [])}
    listed = {str(path) for path in manifest.get("landmark_assets", [])}
    if stale := sorted(set(built.values()) - listed):
        problems.append(
            f"{len(stale)} built landmark assets are not in {CITY_NAME}'s "
            f"landmark_assets: {stale[:5]}"
        )
    if unbuilt := sorted(listed - set(built.values())):
        problems.append(
            f"{len(unbuilt)} manifest landmark_assets were not built by "
            f"{ASSETS_NAME}: {unbuilt[:5]}"
        )

    claimed = {stem for entry in entries for stem in entry.get("replaces_source_ids", [])}
    dropped = set(buildings.get("excluded", {}))
    if missing := sorted(claimed - dropped):
        problems.append(
            f"{len(missing)} landmark stems were never excluded by the building stage "
            f"(typo'd id? wrong variant suffix?): {missing[:5]}"
        )
    if stray := sorted(dropped - claimed):
        problems.append(
            f"{len(stray)} excluded stems belong to no landmark in {LANDMARKS_NAME}: {stray[:5]}"
        )

    bounds = manifest["bounds_game"]
    low, high = bounds["min"], bounds["max"]
    for entry in entries:
        landmark_id = str(entry.get("id"))
        pos = entry.get("transform", {}).get("pos", [])
        if len(pos) != 3:
            problems.append(f"landmark {landmark_id} has no usable position")
            continue
        outside, _ = _outside([pos], low, high)
        if outside:
            problems.append(f"landmark {landmark_id} sits outside bounds_game: {pos}")
        footprint = entry.get("excluded_bounds")
        if footprint is None:
            problems.append(
                f"landmark {landmark_id} has no excluded_bounds — none of its stems "
                "matched a source mesh"
            )
        else:
            # The authored position should stand on the footprint it replaced.
            # One metre of slack: a centroid is not a centre, not misregistration.
            (flow, fhigh) = footprint
            if not (
                flow[0] - 1.0 <= pos[0] <= fhigh[0] + 1.0
                and flow[2] - 1.0 <= pos[2] <= fhigh[2] + 1.0
            ):
                problems.append(
                    f"landmark {landmark_id} at {pos} stands off the footprint it "
                    f"replaced: {footprint}"
                )
        asset = str(entry.get("asset", ""))
        if landmark_id in built:
            # `sync_generated.sh` mirrors the out tree under
            # `res://assets/generated/`, which is what makes this equality the
            # statement "the config's asset path is the built file".
            expected = f"{LANDMARK_GENERATED_ROOT}{PurePosixPath(built[landmark_id]).name}"
            if asset != expected:
                problems.append(
                    f"landmark {landmark_id} asset {asset!r} does not match its built "
                    f"model at {built[landmark_id]!r}"
                )
        elif not asset.startswith(LANDMARK_ASSET_ROOT):
            problems.append(
                f"landmark {landmark_id} asset {asset!r} is outside {LANDMARK_ASSET_ROOT}"
            )
    return problems


def _check_fares(fares: dict, graph: dict) -> list[str]:
    """Fare nodes point at edges that exist, at a position along them, at grade.

    The check the fare stage cannot do for itself once its output is on disk:
    re-running the road stage renumbers edges, and every `nearest_edge` written
    before that quietly names a different street.

    ⚠️ **The level check is about a stale artefact, not about a stale graph.**
    `fares.py` has restricted its snap to `elevation_level == 0` since `Q15`, so
    nothing it writes today can fail this — what fails it is a `fares.json`
    written *before* that, still sitting in the output directory when
    `sync_generated.sh` runs. `__main__.py` takes `--from`, so a partial rebuild
    is an ordinary thing to do, and this is the only guard that sees the result:
    the unit tests grade the code and `FareReport.off_grade_nearer` is a
    stage-time log that a skipped stage never prints. It refuses the sync before
    a byte is copied, which is where a bundle 8.6 m in the air should stop.
    """
    # ⚠️ **Subscripted rather than defaulted, unlike `clearance.py`'s read of the
    # same field.** A default would make a roadgraph missing `elevation_level`
    # pass this check rather than fail it, and a validator that silently agrees
    # with a document it cannot read is worse than one that crashes on it — the
    # whole job here is refusing a bundle nothing else would catch. `roads.py`
    # writes the field on every edge and `read_document` refuses any roadgraph at
    # another `schema_version`, so the strict read is also the accurate one.
    levels = {int(edge["id"]): int(edge["elevation_level"]) for edge in graph.get("edges", [])}
    nodes = fares.get("nodes", [])
    # Counted, like every other check here. This is the one failure that fires
    # on every node at once — renumber the edges and none of them resolve — so
    # listing them would bury the other findings under the region's node count.
    lost = [node["id"] for node in nodes if int(node["nearest_edge"]) not in levels]
    adrift = [node["id"] for node in nodes if not 0.0 <= float(node["edge_t"]) <= 1.0]
    # `None` for an unknown id rather than a level, so `lost` and `aloft` cannot
    # both name a node: an edge that resolves to nothing has no level to be wrong
    # about, and `lost` above already says so. ⚠️ `adrift` is orthogonal to both
    # and may fire alongside either — which edge and where along it are separate
    # faults, and a node carrying both should be told about both.
    aloft = [
        node["id"]
        for node in nodes
        if (level := levels.get(int(node["nearest_edge"]))) is not None and level != 0
    ]

    problems: list[str] = []
    if lost:
        problems.append(
            f"{len(lost)} fare nodes name an edge {ROADGRAPH_NAME} does not have: {lost[:5]}"
        )
    if adrift:
        problems.append(f"{len(adrift)} fare nodes have an edge_t outside [0, 1]: {adrift[:5]}")
    if aloft:
        problems.append(
            f"{len(aloft)} fare nodes name an off-grade edge, so their height came off a deck "
            f"or a tunnel rather than the street (`Q15`): {aloft[:5]}"
        )
    return problems


def _check_graph(graph: dict) -> list[str]:
    nodes = {int(node["id"]) for node in graph.get("nodes", [])}
    edges = {int(edge["id"]) for edge in graph.get("edges", [])}

    dangling = [
        edge["id"]
        for edge in graph.get("edges", [])
        if int(edge["from"]) not in nodes or int(edge["to"]) not in nodes
    ]
    broken = [
        turn
        for turn in graph.get("turn_restrictions", [])
        if int(turn["from_edge"]) not in edges
        or int(turn["to_edge"]) not in edges
        or int(turn["via_node"]) not in nodes
    ]

    problems: list[str] = []
    if dangling:
        problems.append(
            f"{len(dangling)} edges reference a node that does not exist: {dangling[:5]}"
        )
    if broken:
        problems.append(f"{len(broken)} turn restrictions reference something that does not exist")
    return problems


def _check_bounds(manifest: dict, documents: dict[str, dict]) -> list[str]:
    """Nothing sits outside the bounds the manifest declares.

    Counted rather than listed. Bounds are wrong in bulk or not at all — a
    manifest carried over from a previous run puts every position outside it,
    and 600 identical lines say nothing 1 line does not.
    """
    low = manifest["bounds_game"]["min"]
    high = manifest["bounds_game"]["max"]

    # Tile corners come from `buildings.json`, not from the manifest's own copy
    # of them: `bounds_game` is derived from those corners, so checking it
    # against itself can only ever pass.
    buildings = documents[BUILDINGS_MANIFEST_NAME]
    groups: list[tuple[str, Iterable[Sequence[float]]]] = [
        (
            "tile corners",
            (corner for tile in buildings.get("tiles", []) for corner in tile["aabb"]),
        ),
        ("road graph positions", _graph_points(documents[ROADGRAPH_NAME])),
        ("fare node positions", (node["pos"] for node in documents[FARES_NAME].get("nodes", []))),
        ("road surface corners", documents[SURFACE_MANIFEST_NAME]["aabb"]),
    ]

    problems: list[str] = []
    for label, points in groups:
        outside, worst = _outside(points, low, high)
        if outside:
            problems.append(f"{outside} {label} lie outside bounds_game, by up to {worst:.3f} m")
    return problems


def _outside(
    points: Iterable[Sequence[float]], low: Sequence[float], high: Sequence[float]
) -> tuple[int, float]:
    count = 0
    worst = 0.0
    for point in points:
        overshoot = max(
            max(low[axis] - float(point[axis]), float(point[axis]) - high[axis])
            for axis in range(3)
        )
        if overshoot > _TOLERANCE_M:
            count += 1
            worst = max(worst, overshoot)
    return (count, worst)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="validate the existing city.json instead of writing a new one",
    )
    mode.add_argument(
        "--list",
        dest="list_shipped",
        action="store_true",
        help="print the files city.json names, one per line, and do nothing else",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)

    if args.list_shipped:
        # stdout, while logging goes to stderr, so `tools/sync_generated.sh` can
        # read the list without parsing prose. The manifest leads, because a
        # caller copying a region needs it and `shipped` deliberately omits it.
        names = [CITY_NAME, *shipped(read_manifest(city, args.region))]
        print("\n".join(names))
        return 0

    log.info("%s / %s", city.name, region.name)

    if not args.check:
        report = build_region(city, args.region)
        log.info(
            "%d tiles (%d LOD files), %d road edges, %d fare nodes",
            report.tiles,
            report.lod_files,
            report.edges,
            report.fare_nodes,
        )
        low, high = report.bounds
        log.info(
            "  spans %.0f x %.0f m, y %.1f to %.1f",
            high[0] - low[0],
            high[2] - low[2],
            low[1],
            high[1],
        )
        log.info(
            "  %.1f MB shipped across %d files",
            report.shipped_bytes / 1e6,
            report.shipped_files,
        )

    problems = validate(city, args.region, out_root=None)
    if problems:
        for problem in problems:
            log.error("  %s", problem)
        log.error("%s is not valid: %d problem(s)", CITY_NAME, len(problems))
        return 1
    log.info("  %s validates against every document it names", CITY_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
