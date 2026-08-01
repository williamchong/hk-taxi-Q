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
from pathlib import Path

from pipeline import __version__
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA
from pipeline.config import CityConfig, load_city
from pipeline.documents import read_document, round_position, write_document
from pipeline.fares import FARES_NAME, FARES_SCHEMA
from pipeline.gltf import Bounds
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, SURFACE_NAME

log = logging.getLogger(__name__)

CITY_NAME = "city.json"
# 3: the finest tier of every tile ships a `-col` collider. The document's own
# keys did not change, and the bump is deliberate anyway — a build reading v2
# would load v3 tiles happily and put a car through a wall, which is a silent
# wrong answer rather than a missing field. The version gates the whole asset
# set, not just the JSON.
CITY_SCHEMA = 3

# Manifest keys naming a document that ships. One tuple rather than a literal
# at each use, because `shipped` reads them and `REQUIRED_KEYS` guards them:
# a fourth document added to one and not the other is a `KeyError` raised from
# inside the validator instead of a finding reported by it.
DOCUMENT_KEYS = ("road_graph", "road_surface", "fares")
REQUIRED_KEYS = (*DOCUMENT_KEYS, "tiles", "bounds_game")

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
    Input(SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, "surface"),
    Input(ROADGRAPH_NAME, ROADGRAPH_SCHEMA, "roads"),
    Input(FARES_NAME, FARES_SCHEMA, "fares"),
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
    graph = documents[ROADGRAPH_NAME]
    fares = documents[FARES_NAME]

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

    low, high = box.corners()
    transform = city.game_transform(region_id)
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
        "carriageway": surface["carriageway"],
        "fares": FARES_NAME,
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


# The manifest read back as an `Input`, which is what it is once written — same
# version refusal, same rebuild hint, no second copy of the command string. It
# stays out of `INPUTS` because that tuple is what this stage *reads to write
# it*; this is for the two callers that read back what it wrote.
_MANIFEST = Input(CITY_NAME, CITY_SCHEMA, "export")


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
    return [
        *_check_identity(manifest, documents),
        *_check_files(out_dir, manifest),
        *_check_tiles(manifest, buildings),
        *_check_fares(documents[FARES_NAME], documents[ROADGRAPH_NAME]),
        *_check_graph(documents[ROADGRAPH_NAME]),
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


def _check_fares(fares: dict, graph: dict) -> list[str]:
    """Fare nodes point at edges that exist, at a position along them.

    The check the fare stage cannot do for itself once its output is on disk:
    re-running the road stage renumbers edges, and every `nearest_edge` written
    before that quietly names a different street.
    """
    edges = {int(edge["id"]) for edge in graph.get("edges", [])}
    nodes = fares.get("nodes", [])
    # Counted, like every other check here. This is the one failure that fires
    # on every node at once — renumber the edges and none of them resolve — so
    # listing them would bury the other findings under the region's node count.
    lost = [node["id"] for node in nodes if int(node["nearest_edge"]) not in edges]
    adrift = [node["id"] for node in nodes if not 0.0 <= float(node["edge_t"]) <= 1.0]

    problems: list[str] = []
    if lost:
        problems.append(
            f"{len(lost)} fare nodes name an edge {ROADGRAPH_NAME} does not have: {lost[:5]}"
        )
    if adrift:
        problems.append(f"{len(adrift)} fare nodes have an edge_t outside [0, 1]: {adrift[:5]}")
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
