"""Authored furniture at published stops (`P3-93` to `P3-95`, `Q242`).

A flag on a pole where a bus or a green minibus stops and where a taxi may pick
up or set down, and a shelter beside the track at a tram stop. `stopmarks.py`
draws the paint TD surveyed; this stands what nothing publishes.

- **Where is read from the bundle, never from a source.** `bus_routes.json`
  carries each operator's stop points with the kerb they are on, `fares.json`
  TD's taxi pick-up / drop-off points, `tram_lines.json` the stops each track
  serves. A stop this stage draws is one a bus, a fare or a tram already uses.
- **A taxi STAND takes no flag**: TD's own `TS324` plate stands there
  (`signs.py`), and a second post beside it would be ours contradicting theirs.
- **A pole is registered to the drawn kerb**, `lamps._register`'s rule: pushed
  out to `outset_m` past it, never pulled in, refused past `max_shift_m` or
  where it would still stand on the asphalt.
- **A shelter stands on the left of its track**, the side a tram's doors open
  on, and carries no collider: the game draws no island under it, so the lane
  beside the track runs where it stands.
- The library is `signs.glb`'s shape (`placements.Library`): a mesh a kind, a
  unit `pole` scaled to its height. `region.tscn` stands a collider on every
  `pole` and on nothing else.
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import shapely

from pipeline.busroutes import (
    BUS_ROUTES_SCHEMA,
    BUSROUTES_MANIFEST_NAME,
    BUSROUTES_MANIFEST_SCHEMA,
)
from pipeline.config import Config, Stops, load_config
from pipeline.config_blocks.stops import BUS, MINIBUS, POLE_KINDS, TAXI, StopFlag, TramShelter
from pipeline.documents import read_document, write_document
from pipeline.drawnroad import Ribbon, drawn_carriageway, kerbed_ribbons
from pipeline.fares import FARES_NAME, FARES_SCHEMA
from pipeline.gltf import MeshData
from pipeline.meshbuild import ColouredBuilder
from pipeline.placements import Placement, placement, stand_library
from pipeline.polyline import Segments, Snap, bearing_deg, frame, plan_lengths
from pipeline.railings import facing_away
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.signs import SIGNS_MATERIAL, facing_from_side
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA
from pipeline.tramlines import (
    TRAM_LINES_SCHEMA,
    TRAMLINES_MANIFEST_NAME,
    TRAMLINES_MANIFEST_SCHEMA,
)

log = logging.getLogger(__name__)

STOPS_NAME = "stops.glb"
STOPS_PLACEMENTS_NAME = "stops_placements.json"
STOPS_MANIFEST_NAME = "stops.json"
STOPS_MANIFEST_SCHEMA = 1

# The unit post every flag stands on, scaled to its kind's height. The name is
# the one `region.tscn`'s `posts` stands a collider on (`Q191`).
POLE_MESH_NAME = "pole"
TRAM_MESH_NAME = "tram_shelter"
# How far a shelter's posts run into the ground. `PropBatch.post_of` stands a
# collider under any library mesh whose foot is at its origin, and a shelter is
# to have none: its feet are below it.
_SHELTER_SUNK_M = 0.1

# Which of `bus_routes.json`'s route kinds stops at which flag.
_ROUTE_KIND = {"bus": BUS, "minibus": MINIBUS}
# `fares.json`'s taxi pick-up / drop-off points. Its `taxi_stand` is TD's sign's.
_FARE_TAXI_POINT = "pudo"

# Refusals, as `stops.json` spells them.
NO_RIBBON = "no_ribbon"
OVER_SHIFT = "over_shift"
IN_CARRIAGEWAY = "in_carriageway"
NO_TRACK = "no_track"


@dataclass
class StopReport:
    """What the stage read and stood.

    Per kind, `read == merged + stood + sum(refused)`: a stop within `merge_m`
    of one already taken shares its pole.
    """

    read: dict[str, int] = field(default_factory=dict)
    merged: dict[str, int] = field(default_factory=dict)
    stood: dict[str, int] = field(default_factory=dict)
    refused: dict[str, dict[str, int]] = field(default_factory=dict)
    posts_kept_as_surveyed: int = 0
    shift_m: list[float] = field(default_factory=list)
    facing_away: int = 0

    placements: int = 0
    placements_refused: int = 0
    library_meshes: int = 0
    library_triangles: int = 0
    library_vertices: int = 0
    triangles: int = 0
    vertices: int = 0
    aabb: list[list[float]] = field(default_factory=list)
    bytes: int = 0

    def refuse(self, kind: str, reason: str) -> None:
        reasons = self.refused.setdefault(kind, {})
        reasons[reason] = reasons.get(reason, 0) + 1

    def closes(self, kind: str) -> bool:
        return self.read.get(kind, 0) == (
            self.merged.get(kind, 0)
            + self.stood.get(kind, 0)
            + sum(self.refused.get(kind, {}).values())
        )


def pole_points(routes: dict[str, Any], fares: dict[str, Any]) -> dict[str, list[np.ndarray]]:
    """Every published point a flag stands at, by kind, in a stable order: each
    operator stop once however many routes call there, then TD's taxi points."""
    stops: dict[str, dict[str, np.ndarray]] = {BUS: {}, MINIBUS: {}}
    for route in routes.get("routes", []):
        kind = _ROUTE_KIND.get(str(route["kind"]))
        if kind is None:
            continue
        for stop in route["stops"]:
            stops[kind].setdefault(str(stop["stop_id"]), np.array(stop["plan"], dtype=float))
    points = {kind: [by_id[key] for key in sorted(by_id)] for kind, by_id in stops.items()}
    points[TAXI] = [
        np.array([node["pos"][0], node["pos"][2]], dtype=float)
        for node in fares.get("nodes", [])
        if node["kind"] == _FARE_TAXI_POINT
    ]
    return points


def merged(points: list[np.ndarray], merge_m: float) -> tuple[list[np.ndarray], int]:
    """`points` with any within `merge_m` of one already kept dropped, and how
    many were. Two operators' poles a metre apart are one flag here. Within a
    kind only: a bus flag and a taxi point side by side say different things."""
    kept: list[np.ndarray] = []
    for point in points:
        if all(math.dist(point, other) > merge_m for other in kept):
            kept.append(point)
    return kept, len(points) - len(kept)


def register(
    spec: Stops, snap: Snap, ribbon: Ribbon, published: np.ndarray, report: StopReport
) -> tuple[np.ndarray, float] | None:
    """The point a pole stands at and its kerb side: `lamps._register`'s rule,
    outward only, `None` past `max_shift_m`."""
    side, _, target_m, placed = ribbon.kerb_target(snap, spec.outset_m)
    if ribbon.past_kerb_m(snap) > spec.outset_m:
        report.shift_m.append(0.0)
        report.posts_kept_as_surveyed += 1
        return published, side
    shift_m = abs(target_m - snap.offset_m)
    report.shift_m.append(shift_m)
    return None if shift_m > spec.max_shift_m else (placed, side)


def tram_stands(
    tracks: dict[str, Any], shelter: TramShelter, report: StopReport
) -> list[tuple[np.ndarray, float]]:
    """Where each tram stop's shelter stands — `(x, y, z)` and the track's
    heading there — once a stop, on the first track that serves it."""
    stands: dict[str, tuple[np.ndarray, float]] = {}
    seen: set[str] = set()
    for track in tracks.get("tracks", []):
        points = np.array(track["points"], dtype=float).reshape(-1, 3)
        along_m = plan_lengths(points) if len(points) else np.zeros(0)
        steps = np.diff(along_m)
        # A doubled vertex has no direction to take a heading from.
        runs = np.flatnonzero(steps > 0.0)
        for stop in track["stops"]:
            if stop["id"] in seen:
                continue
            seen.add(stop["id"])
            report.read[TRAM_MESH_NAME] = report.read.get(TRAM_MESH_NAME, 0) + 1
            if not len(runs):
                report.refuse(TRAM_MESH_NAME, NO_TRACK)
                continue
            s_m = float(np.clip(stop["s_m"], 0.0, along_m[-1]))
            at_or_before = runs[along_m[runs] <= s_m]
            index = int(at_or_before[-1] if len(at_or_before) else runs[0])
            share = min((s_m - along_m[index]) / float(steps[index]), 1.0)
            at = points[index] + share * (points[index + 1] - points[index])
            run = points[index + 1] - points[index]
            heading = bearing_deg(run[[0, 2]])
            _, across = frame(heading)
            # The nearside is -across (`polyline.frame`): the track's left.
            left = at[[0, 2]] - shelter.offset_m * across
            stands[stop["id"]] = (np.array([left[0], at[1], left[1]]), heading)
    return [stands[key] for key in sorted(stands)]


Rgb = tuple[int, int, int]


def liveries(city: Config, spec: Stops) -> dict[str, Rgb]:
    """`signs.colours`, once every name the `stops:` block uses is found in it."""
    table = city.signs.colours if city.signs is not None else {}
    used = {spec.pole} | {c for flag in spec.flags.values() for c in (flag.colour, flag.band)}
    if spec.tram is not None:
        used |= {spec.tram.colour, spec.tram.roof}
    missing = sorted(used - set(table))
    if missing:
        raise ValueError(f"stops: {missing} are not colours in signs.colours ({', '.join(table)})")
    return table


def _box(builder: ColouredBuilder, low: np.ndarray, high: np.ndarray, colour: Rgb) -> None:
    """An axis-aligned box in the library's frame, every face wound outward."""
    ends = (low, high)
    corners = np.array(
        [[ends[i][0], ends[j][1], ends[k][2]] for i, j, k in np.ndindex(2, 2, 2)]
    ).reshape(2, 2, 2, 3)
    for axis in range(3):
        for end in range(2):
            face = np.take(corners, end, axis=axis).reshape(4, 3)[[0, 1, 3, 2]]
            normal = np.zeros(3)
            normal[axis] = 1.0 if end else -1.0
            if np.dot(np.cross(face[1] - face[0], face[2] - face[0]), normal) < 0.0:
                face = face[::-1]
            builder.polygon(face, normal, colour)


def pole_mesh(spec: Stops, colours: dict[str, Rgb]) -> MeshData:
    """A unit post on the origin: a stand scales it to its flag's height."""
    builder = ColouredBuilder(SIGNS_MATERIAL)
    r = spec.pole_radius_m
    _box(builder, np.array([-r, 0.0, -r]), np.array([r, 1.0, r]), colours[spec.pole])
    return _built(builder, POLE_MESH_NAME)


def flag_mesh(spec: Stops, kind: str, flag: StopFlag, colours: dict[str, Rgb]) -> MeshData:
    """A kind's flag about the pole's axis, its faces to north and south: a
    stand turns one to the traffic that passes it."""
    builder = ColouredBuilder(SIGNS_MATERIAL)
    half_w, half_t = 0.5 * flag.width_m, 0.5 * spec.plate_thickness_m
    top = flag.mount_m + 0.5 * flag.height_m
    split = top - 0.25 * flag.height_m
    _box(
        builder,
        np.array([-half_w, flag.mount_m - 0.5 * flag.height_m, -half_t]),
        np.array([half_w, split, half_t]),
        colours[flag.colour],
    )
    _box(
        builder,
        np.array([-half_w, split, -half_t]),
        np.array([half_w, top, half_t]),
        colours[flag.band],
    )
    return _built(builder, kind)


def shelter_mesh(spec: Stops, shelter: TramShelter, colours: dict[str, Rgb]) -> MeshData:
    """A roof on two posts, its length along the library's north: a stand turns
    it to the track's heading."""
    builder = ColouredBuilder(SIGNS_MATERIAL)
    r, half_l, half_w = spec.pole_radius_m * 1.5, 0.5 * shelter.length_m, 0.5 * shelter.width_m
    under = shelter.height_m - shelter.roof_m
    for z in (-half_l + 4.0 * r, half_l - 4.0 * r):
        _box(
            builder,
            np.array([-r, -_SHELTER_SUNK_M, z - r]),
            np.array([r, under, z + r]),
            colours[shelter.colour],
        )
    _box(
        builder,
        np.array([-half_w, under, -half_l]),
        np.array([half_w, shelter.height_m, half_l]),
        colours[shelter.roof],
    )
    return _built(builder, TRAM_MESH_NAME)


def _built(builder: ColouredBuilder, name: str) -> MeshData:
    mesh = builder.build(name)
    assert mesh is not None  # a box of positive extent, by the config's own bars
    return mesh


def build_region(city: Config, region_id: str, *, out_root: Path | None = None) -> StopReport:
    out_dir = city.out_dir(region_id, out_root)
    report = StopReport()
    spec = city.stops
    if spec is None:
        log.info("stops: no `stops` block for %s, so nothing is stood", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    edges = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    segments = Segments.of(edges)
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    ribbons = kerbed_ribbons(city, out_dir, region_id, graph, surface)
    road = drawn_carriageway(city, out_dir, region_id)

    colours = liveries(city, spec)
    meshes: dict[str, MeshData] = {}
    stands: list[Placement] = []
    routes = _published(
        out_dir, BUSROUTES_MANIFEST_NAME, BUSROUTES_MANIFEST_SCHEMA, BUS_ROUTES_SCHEMA, "busroutes"
    )
    fares = read_document(out_dir / FARES_NAME, FARES_SCHEMA, "python -m pipeline.fares")
    points = pole_points(routes, fares)
    for kind in POLE_KINDS:
        flag = spec.flags.get(kind)
        if flag is None:
            continue
        report.read[kind] = len(points[kind])
        kept, report.merged[kind] = merged(points[kind], spec.merge_m)
        for published in kept:
            snap = segments.nearest(float(published[0]), float(published[1]))
            ribbon = ribbons.get(snap.edge)
            if ribbon is None:
                report.refuse(kind, NO_RIBBON)
                continue
            registered = register(spec, snap, ribbon, published, report)
            if registered is None:
                report.refuse(kind, OVER_SHIFT)
                continue
            placed, side = registered
            if road is not None and shapely.contains_xy(road, float(placed[0]), float(placed[1])):
                report.refuse(kind, IN_CARRIAGEWAY)
                continue
            foot = np.array([placed[0], snap.y, placed[1]])
            if POLE_MESH_NAME not in meshes:
                meshes[POLE_MESH_NAME] = pole_mesh(spec, colours)
            if kind not in meshes:
                meshes[kind] = flag_mesh(spec, kind, flag, colours)
            top_m = flag.mount_m + 0.5 * flag.height_m
            stands.append(placement(POLE_MESH_NAME, foot, 0.0, scale=[1.0, top_m, 1.0]))
            facing = facing_from_side(snap.heading_deg, side, ribbon.one_way)
            stands.append(placement(kind, foot, facing))
            report.stood[kind] = report.stood.get(kind, 0) + 1
        assert report.closes(kind), kind

    if spec.tram is not None:
        tracks = _published(
            out_dir,
            TRAMLINES_MANIFEST_NAME,
            TRAMLINES_MANIFEST_SCHEMA,
            TRAM_LINES_SCHEMA,
            "tramlines",
        )
        for foot, heading in tram_stands(tracks, spec.tram, report):
            if TRAM_MESH_NAME not in meshes:
                meshes[TRAM_MESH_NAME] = shelter_mesh(spec, spec.tram, colours)
            stands.append(placement(TRAM_MESH_NAME, foot, heading))
            report.stood[TRAM_MESH_NAME] = report.stood.get(TRAM_MESH_NAME, 0) + 1

    library = stand_library([meshes[name] for name in sorted(meshes)], stands)
    if library.meshes:
        report.facing_away = sum(facing_away(mesh) for mesh in library.meshes)
        library.publish(report)
        poles = sum(report.stood.get(kind, 0) for kind in POLE_KINDS)
        library.require_every_stand(
            2 * poles + report.stood.get(TRAM_MESH_NAME, 0),
            f"{poles} flags on their poles and {report.stood.get(TRAM_MESH_NAME, 0)} shelters",
        )
        report.bytes = library.write(out_dir, STOPS_NAME, STOPS_PLACEMENTS_NAME, city.id, region_id)

    _write_manifest(out_dir, city, region_id, report)
    return report


def _published(
    out_dir: Path, manifest_name: str, manifest_schema: int, schema: int, stage: str
) -> dict[str, Any]:
    """A sibling stage's document through its manifest, schema-checked as
    `parked.py` reads it; nothing where the stage drew none."""
    rebuild = f"python -m pipeline.{stage}"
    document = read_document(out_dir / manifest_name, manifest_schema, rebuild).get("document")
    return read_document(out_dir / str(document), schema, rebuild) if document else {}


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: StopReport) -> int:
    drawn = report.bytes > 0
    return write_document(
        out_dir / STOPS_MANIFEST_NAME,
        {
            "schema_version": STOPS_MANIFEST_SCHEMA,
            "city_id": city.id,
            "region_id": region_id,
            "asset": STOPS_NAME if drawn else None,
            "placements_document": STOPS_PLACEMENTS_NAME if drawn else None,
            "read": dict(sorted(report.read.items())),
            "merged": dict(sorted(report.merged.items())),
            "stood": dict(sorted(report.stood.items())),
            "refused": {
                kind: dict(sorted(why.items())) for kind, why in sorted(report.refused.items())
            },
            "posts_kept_as_surveyed": report.posts_kept_as_surveyed,
            "shift_m": tail_of(report.shift_m),
            "facing_away": report.facing_away,
            "placements": report.placements,
            "placements_refused": report.placements_refused,
            "library_meshes": report.library_meshes,
            "library_triangles": report.library_triangles,
            "library_vertices": report.library_vertices,
            "triangles": report.triangles,
            "vertices": report.vertices,
            "aabb": report.aabb,
            "bytes": report.bytes,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--region", default="wan_chai")
    parser.add_argument("--out-root", type=Path, default=None, help="override etl/out")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    report = build_region(load_config(), args.region, out_root=args.out_root)
    log.info(
        "stops: read %s -> stood %s (merged %s, refused %s), %d triangles, %d facing away",
        dict(sorted(report.read.items())),
        dict(sorted(report.stood.items())),
        dict(sorted(report.merged.items())),
        {kind: dict(why) for kind, why in sorted(report.refused.items())},
        report.triangles,
        report.facing_away,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
