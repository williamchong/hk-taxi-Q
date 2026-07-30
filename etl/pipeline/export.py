"""Stage outputs to the shipped manifest (`P1-6`).

Every earlier stage writes what it alone knows. This one reconciles them into
`city.json` — the single document the game opens first, per the contract in
`docs/ARCHITECTURE.md` — and then checks that the set it just described is
actually coherent.

Three decisions are worth stating, because the file's shape follows from them:

- **`city.json` references, it does not inline.** The road graph is 6 MB and
  the fare nodes are read by a different system at a different time; folding
  them in would make every consumer parse both to learn where a tile is. Each
  is separately versioned in the contract and stays a separate file.
- **`buildings.json` and `roadsurface.json` do not ship.** They are stage
  intermediates whose only reader is this module. What the game needs from
  them — tile paths, AABBs, the surface mesh name — is either copied into
  `city.json` or recoverable from the GLB itself.
- **`bounds_game` is the union of the content, not the region rectangle.**
  Wan Chai's declared region is 1650 x 887 m, but the tiles reach 1657 x 923 m
  because a building is assigned to a tile whole and may overhang it. A
  consumer sizing a spatial partition or framing a camera off the rectangle
  would clip real geometry, so this reports what is there.

`validate` checks the one class of error no single stage can see: whether the
documents agree with *each other*. A fare node naming an edge the graph does
not have, a tile whose GLB never got written, two documents built from
different runs — each stage's own output is internally fine in all three cases.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pipeline import __version__
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA
from pipeline.config import CityConfig, load_city
from pipeline.fares import FARES_NAME, FARES_SCHEMA
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA, read_document, round_position
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, SURFACE_NAME

log = logging.getLogger(__name__)

CITY_NAME = "city.json"
CITY_SCHEMA = 1

# Positions are written at millimetre precision, and `bounds_game` is rounded
# from the same values. Rounding both can push a coordinate a hair outside its
# own bounding box, so the containment checks allow exactly that much.
_TOLERANCE_M = 0.001

Vec3 = tuple[float, float, float]


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
    low: Vec3 = (0.0, 0.0, 0.0)
    high: Vec3 = (0.0, 0.0, 0.0)
    # Every byte a build would ship for this region — the manifest, the three
    # documents it names, and every tile GLB. The bundle budget is 200 MB.
    shipped_bytes: int = 0
    shipped_files: int = 0
    manifest_bytes: int = 0


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

    def corners(self) -> tuple[Vec3, Vec3]:
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
    out_dir = city.out_dir(region_id, out_root)
    documents = {source.name: source.read(out_dir, city.id, region_id) for source in INPUTS}

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
        "fares": FARES_NAME,
        "etl_version": __version__,
        "generated_utc": generated_utc or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    path = out_dir / CITY_NAME
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # The manifest itself ships too, so it counts in both totals.
    names = shipped(document)
    manifest_bytes = path.stat().st_size
    return ExportReport(
        tiles=len(tiles),
        lod_files=sum(len(tile["lods"]) for tile in tiles),
        fare_nodes=len(fares["nodes"]),
        edges=len(graph["edges"]),
        low=low,
        high=high,
        # A missing file counts as zero rather than raising: reporting it is
        # `validate`'s job, and it says which file and why.
        shipped_bytes=manifest_bytes + sum(_size(out_dir / name) for name in names),
        shipped_files=len(names) + 1,
        manifest_bytes=manifest_bytes,
    )


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def shipped(manifest: dict) -> list[str]:
    """Every file `city.json` names, relative to the region's out directory.

    The definition of "what a build copies into the game", and the reason the
    intermediates can sit in the same directory without being shipped by
    accident: this list is derived from the manifest, never from a directory
    listing.
    """
    paths = [str(manifest[key]) for key in ("road_graph", "road_surface", "fares")]
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

    Deliberately scoped to what crosses a document boundary. Each stage already
    tests its own invariants and re-checking them here would only mean two
    places to update; what none of them can see is the other files.

    Returns rather than raises, so one run reports every problem instead of the
    first one. A version mismatch still raises — that is a stale build, not a
    finding, and the message names the command that fixes it.
    """
    out_dir = city.out_dir(region_id, out_root)
    rebuild = f"python -m pipeline.export --city {city.id} --region {region_id}"
    manifest = read_document(out_dir / CITY_NAME, CITY_SCHEMA, rebuild)
    documents = {source.name: source.read(out_dir, city.id, region_id) for source in INPUTS}

    problems: list[str] = []
    required = ("tiles", "road_graph", "road_surface", "fares", "bounds_game")
    missing = [key for key in required if key not in manifest]
    if missing:
        # Nothing below can be trusted without these, so stop here rather than
        # report a cascade of consequences.
        return [f"{CITY_NAME} is missing {', '.join(missing)}"]

    problems += _check_identity(manifest, documents)
    problems += _check_files(out_dir, manifest)
    problems += _check_tiles(manifest)
    problems += _check_fares(documents[FARES_NAME], documents[ROADGRAPH_NAME])
    problems += _check_graph(documents[ROADGRAPH_NAME])
    problems += _check_bounds(manifest, documents)
    return problems


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


def _check_tiles(manifest: dict) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for tile in manifest["tiles"]:
        tile_id = str(tile.get("id"))
        if tile_id in seen:
            problems.append(f"two tiles share the id {tile_id}")
        seen.add(tile_id)
        if not tile.get("lods"):
            problems.append(f"tile {tile_id} has no LOD files")
        low, high = tile["aabb"]
        if any(high[axis] < low[axis] for axis in range(3)):
            problems.append(f"tile {tile_id} has an inverted aabb")
    return problems


def _check_fares(fares: dict, graph: dict) -> list[str]:
    """Fare nodes point at edges that exist, at a position along them.

    The check the fare stage cannot do for itself once its output is on disk:
    re-running the road stage renumbers edges, and every `nearest_edge` written
    before that quietly names a different street.
    """
    edges = {int(edge["id"]) for edge in graph.get("edges", [])}
    problems: list[str] = []
    for node in fares.get("nodes", []):
        if int(node["nearest_edge"]) not in edges:
            problems.append(
                f"fare node {node['id']} names edge {node['nearest_edge']}, "
                f"which {ROADGRAPH_NAME} does not have"
            )
        if not 0.0 <= float(node["edge_t"]) <= 1.0:
            problems.append(f"fare node {node['id']} has edge_t {node['edge_t']} outside [0, 1]")
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

    graph = documents[ROADGRAPH_NAME]
    groups: list[tuple[str, Iterable[Sequence[float]]]] = [
        ("tile corners", (corner for tile in manifest["tiles"] for corner in tile["aabb"])),
        ("road graph positions", _graph_points(graph)),
        ("fare node positions", (node["pos"] for node in documents[FARES_NAME]["nodes"])),
        ("road surface corners", iter(documents[SURFACE_MANIFEST_NAME]["aabb"])),
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
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the existing city.json instead of writing a new one",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)
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
        log.info(
            "  spans %.0f x %.0f m, y %.1f to %.1f",
            report.high[0] - report.low[0],
            report.high[2] - report.low[2],
            report.low[1],
            report.high[1],
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
