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
  on. Its roof hangs and its two posts are their own mesh, so the engine stands
  a collider under each post and none under the roof (the user's call).
- **A station exit's sign** (`P3-107`) hangs on the wall the shipped tiles
  draw nearest the exit's surveyed point — the stair head the 3D map already
  models, or the building the exit opens from — the wall facing the exit's road
  preferred; where no wall is in reach it tops a post. The plate is the
  station's colour (`fares.stations.table`'s `colour`), its lettering Noto Sans
  HK as geometry, so it rides the signs' material and needs no atlas. No
  operator's logo or word mark.
- The library is `signs.glb`'s shape (`placements.Library`): a mesh a kind, a
  unit `pole` scaled to its height. `region.tscn` stands a collider on every
  `pole` and every shelter post, the two meshes drawn standing on their origin.
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
from pipeline.config_blocks.fares import Station
from pipeline.config_blocks.stops import (
    BUS,
    MINIBUS,
    POLE_KINDS,
    TAXI,
    ExitSign,
    StopFlag,
    TramShelter,
)
from pipeline.direction_signs import box
from pipeline.documents import read_document, write_document
from pipeline.drawnroad import Ribbon, drawn_carriageway, kerbed_ribbons
from pipeline.fares import FARES_NAME, FARES_SCHEMA, STATION_EXIT
from pipeline.fetch import cached_source
from pipeline.gltf import MeshData
from pipeline.meshbuild import ColouredBuilder
from pipeline.placements import Placement, placement, stand_library
from pipeline.polyline import Segments, Snap, bearing_deg, frame, plan_lengths
from pipeline.railings import facing_away
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.roadtext import Face
from pipeline.signboards import Walls, shipped_walls, wall_ground_y
from pipeline.signs import SIGNS_MATERIAL, facing_from_side
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA
from pipeline.tramlines import (
    TRAM_LINES_SCHEMA,
    TRAMLINES_MANIFEST_NAME,
    TRAMLINES_MANIFEST_SCHEMA,
)
from pipeline.trees import Faces

log = logging.getLogger(__name__)

STOPS_NAME = "stops.glb"
STOPS_PLACEMENTS_NAME = "stops_placements.json"
STOPS_MANIFEST_NAME = "stops.json"
STOPS_MANIFEST_SCHEMA = 1

# The unit post every flag stands on, scaled to its kind's height. The name is
# the one `region.tscn`'s `posts` stands a collider on (`Q191`).
POLE_MESH_NAME = "pole"
TRAM_MESH_NAME = "tram_shelter"
# A shelter's post, its own mesh so the engine stands a collider under each
# (`PropBatch.post_of`, the user's call 2026-11-18); the roof hangs and takes none.
TRAM_POST_MESH_NAME = "tram_post"

# Which of `bus_routes.json`'s route kinds stops at which flag.
_ROUTE_KIND = {"bus": BUS, "minibus": MINIBUS}
# `fares.json`'s taxi pick-up / drop-off points. Its `taxi_stand` is TD's sign's.
_FARE_TAXI_POINT = "pudo"

# Refusals, as `stops.json` spells them.
NO_RIBBON = "no_ribbon"
OVER_SHIFT = "over_shift"
IN_CARRIAGEWAY = "in_carriageway"
NO_TRACK = "no_track"
NO_STATION = "no_station"
NO_COLOUR = "no_colour"

# A station exit's sign, by where it hangs: counted in `stops.json`.
ON_WALL = "on_wall"
ON_POST = "on_post"

_UP = np.array([0.0, 1.0, 0.0])


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
    # Each station exit's sign by where it hangs, and how far its wall is.
    exit_signs: dict[str, int] = field(default_factory=dict)
    exit_wall_m: list[float] = field(default_factory=list)
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
    operator stop once however many routes call there, then TD's taxi points
    (read for a city that declares a `taxi_point` flag; Hong Kong's does not)."""
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


def station_table(city: Config) -> tuple[Station, ...]:
    """`fares.stations.table`, or none where the city reads no stations."""
    stations = city.fares.stations
    return stations.table if stations is not None else ()


def liveries(city: Config, spec: Stops) -> dict[str, Rgb]:
    """`signs.colours`, once every name the `stops:` block uses is found in it."""
    table = city.signs.colours if city.signs is not None else {}
    used = {spec.pole} | {c for flag in spec.flags.values() for c in (flag.colour, flag.band)}
    if spec.tram is not None:
        used |= {spec.tram.colour, spec.tram.roof}
    sign = spec.station_exit
    if sign is not None:
        used |= {
            sign.fascia,
            sign.opening,
            sign.trim,
            sign.ink,
            sign.letter_ground,
            sign.letter_ink,
        }
        used |= {s.colour for s in station_table(city) if s.colour is not None}
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


def _post_mesh(name: str, half_m: float, top_m: float, colour: Rgb) -> MeshData:
    """A square post standing on its origin, which is what the engine stands a
    collider under (`PropBatch.post_of`)."""
    builder = ColouredBuilder(SIGNS_MATERIAL)
    _box(builder, np.array([-half_m, 0.0, -half_m]), np.array([half_m, top_m, half_m]), colour)
    return _built(builder, name)


def pole_mesh(spec: Stops, colours: dict[str, Rgb]) -> MeshData:
    """A unit post: a stand scales it to its flag's height."""
    return _post_mesh(POLE_MESH_NAME, spec.pole_radius_m, 1.0, colours[spec.pole])


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


def shelter_mesh(shelter: TramShelter, colours: dict[str, Rgb]) -> MeshData:
    """The roof, hung at its height, its length along the library's north: a
    stand turns it to the track's heading."""
    builder = ColouredBuilder(SIGNS_MATERIAL)
    half_l, half_w = 0.5 * shelter.length_m, 0.5 * shelter.width_m
    _box(
        builder,
        np.array([-half_w, shelter.height_m - shelter.roof_m, -half_l]),
        np.array([half_w, shelter.height_m, half_l]),
        colours[shelter.roof],
    )
    return _built(builder, TRAM_MESH_NAME)


def _shelter_post_m(spec: Stops) -> float:
    """Half a shelter post's width: half as thick again as a flag's pole."""
    return 1.5 * spec.pole_radius_m


def shelter_post_mesh(spec: Stops, shelter: TramShelter, colours: dict[str, Rgb]) -> MeshData:
    """One post, up to the roof's underside."""
    return _post_mesh(
        TRAM_POST_MESH_NAME,
        _shelter_post_m(spec),
        shelter.height_m - shelter.roof_m,
        colours[shelter.colour],
    )


def shelter_posts(
    spec: Stops, shelter: TramShelter, foot: np.ndarray, heading: float
) -> list[np.ndarray]:
    """The two posts' feet, `(x, y, z)`: under the roof's ends, along the track."""
    along, _ = frame(heading)
    reach = 0.5 * shelter.length_m - 4.0 * _shelter_post_m(spec)
    step = np.array([along[0], 0.0, along[1]]) * reach
    return [foot - step, foot + step]


@dataclass(frozen=True)
class ExitStand:
    """Where one station exit's portal stands: its fascia's middle `(x, y, z)`
    in the frame's plane, its outward plan normal, the ground under it, and whether it tops a post
    (both faces lettered) or hangs on a wall (the face away from it only)."""

    middle: np.ndarray
    out: np.ndarray
    ground_y: float
    on_post: bool
    # How far the wall is from the surveyed exit; None on a post.
    wall_m: float | None = None


def road_point(edges: dict[int, dict[str, Any]], node: dict[str, Any]) -> np.ndarray:
    """The plan point on the node's road where the taxi stops for it."""
    plan = [(point[0], point[2]) for point in edges[int(node["nearest_edge"])]["polyline"]]
    line = shapely.LineString(plan)
    stop = line.interpolate(float(node["edge_t"]), normalized=True)
    return np.array([stop.x, stop.y])


def _facing(toward: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(toward))
    return toward / length if length > 1e-6 else np.array([0.0, -1.0])


def _clamped(sign: ExitSign, walls: Walls, index: int, foot: np.ndarray) -> np.ndarray:
    """`foot` along wall `index`, inside its ends by half the portal: past them
    it runs into the return of a recess the 3D map models round a doorway."""
    a, b = walls.a[index], walls.b[index]
    span = float(np.linalg.norm(b - a))
    along = (b - a) / span
    reach = 0.5 * span - 0.5 * sign.width_m
    share = float(np.dot(foot - a, along)) - 0.5 * span
    return a + along * (0.5 * span + (float(np.clip(share, -reach, reach)) if reach > 0 else 0.0))


def _proud_m(sign: ExitSign, walls: Walls, index: int, foot: np.ndarray) -> float:
    """How far out the most proud wall facing wall `index`'s way stands across
    the portal's width: the 3D map draws some facades out of plane, and a frame
    laid on one triangle is buried by the next."""
    out = walls.normal[index]
    along = np.array([-out[1], out[0]])
    proud = 0.0
    for end in (-0.5 * sign.width_m, 0.0, 0.5 * sign.width_m):
        probe = foot + along * end
        for other, _, nearest in walls.near(float(probe[0]), float(probe[1]), 1.0):
            if float(np.dot(walls.normal[other], out)) > 0.9:
                proud = max(proud, float(np.dot(nearest - foot, out)))
    return proud


def exit_stand(
    sign: ExitSign,
    at: np.ndarray,
    road_y: float,
    road: np.ndarray,
    walls: Walls,
    ground: Faces,
) -> ExitStand:
    """The wall the exit's portal is drawn on, or the post its fascia tops.

    A wall within `wall_reach_m` whose foot is near the road's height, the one
    facing the road preferred by `facing_weight_m`; none, and a post stands at
    the surveyed point facing the road."""
    toward = _facing(road - at)
    candidates = [
        entry
        for entry in walls.near(float(at[0]), float(at[1]), sign.wall_reach_m)
        if walls.low[entry[0]] <= road_y + sign.door_height_m
    ]
    if not candidates:
        under = ground.heights(float(at[0]), float(at[1]))
        near = under[np.abs(under - road_y) <= sign.door_height_m]
        ground_y = float(near.max()) if len(near) else road_y
        middle = np.array([at[0], ground_y + sign.door_height_m + 0.5 * sign.fascia_m, at[1]])
        return ExitStand(middle, toward, ground_y, on_post=True)
    index, distance, foot = min(
        candidates,
        key=lambda entry: (
            entry[1] + sign.facing_weight_m * (1.0 - float(np.dot(walls.normal[entry[0]], toward))),
            entry[0],
        ),
    )
    out = walls.normal[index]
    foot = _clamped(sign, walls, index, foot)
    ground_y = wall_ground_y(walls, ground, index, foot)
    # Under the wall's top: a stair head the 3D map draws lower than the portal
    # takes its fascia at its brow, the door shortened under it.
    top = min(ground_y + sign.door_height_m + sign.fascia_m, float(walls.high[index]))
    middle_y = max(top, ground_y + sign.fascia_m) - 0.5 * sign.fascia_m
    plan = foot + out * (_proud_m(sign, walls, index, foot) + sign.off_wall_m + 0.5 * sign.depth_m)
    return ExitStand(
        np.array([plan[0], middle_y, plan[1]]), out, ground_y, on_post=False, wall_m=distance
    )


def _lettered(
    builder: ColouredBuilder,
    face: Face,
    line: str,
    middle: np.ndarray,
    right: np.ndarray,
    out: np.ndarray,
    box: tuple[float, float],
    colour: Rgb,
) -> None:
    """`line` set in `face`, as large as fits `box` (across, up), centred on
    `middle` and facing `out`."""
    triangles, extent = face.block([line], 0.0)
    wide, tall = extent[2] - extent[0], extent[3] - extent[1]
    if not len(triangles) or wide <= 0.0 or tall <= 0.0:
        return
    scale = min(box[0] / wide, box[1] / tall)
    centre = np.array([0.5 * (extent[0] + extent[2]), 0.5 * (extent[1] + extent[3])])
    for triangle in triangles:
        local = (triangle - centre) * scale
        points = middle + np.outer(local[:, 0], right) + np.outer(local[:, 1], _UP)
        turn = np.dot(np.cross(points[1] - points[0], points[2] - points[0]), out)
        if abs(turn) < 1e-12:
            continue
        builder.polygon(points if turn > 0.0 else points[::-1], out, colour)


def _names(
    builder: ColouredBuilder,
    sign: ExitSign,
    face: Face,
    station: Station,
    middle: np.ndarray,
    right: np.ndarray,
    out: np.ndarray,
    box_m: tuple[float, float],
    colour: Rgb,
) -> None:
    """`灣仔站 Wan Chai Station` on one line (`fascia_zh`, `fascia_en`), the
    Chinese the taller, as an MTR fascia sets it, as large as fits `box_m` (across, up)."""
    lines = (sign.fascia_zh.format(station=station.zh), sign.fascia_en.format(station=station.en))
    tall = (sign.zh_m, sign.en_m)
    natural = []
    for line, height in zip(lines, tall, strict=True):
        _, extent = face.block([line], 0.0)
        natural.append(height * (extent[2] - extent[0]) / (extent[3] - extent[1]))
    gap = 0.4 * tall[1]
    shrink = min(1.0, box_m[0] / (sum(natural) + gap), box_m[1] / sign.zh_m)
    u = -0.5 * shrink * (sum(natural) + gap)
    for line, height, wide in zip(lines, tall, natural, strict=True):
        across = wide * shrink
        _lettered(
            builder,
            face,
            line,
            middle + right * (u + 0.5 * across),
            right,
            out,
            (across, height * shrink),
            colour,
        )
        u += across + gap * shrink


def exit_mesh(
    name: str,
    spec: Stops,
    sign: ExitSign,
    stand: ExitStand,
    station: Station,
    letter: str | None,
    face: Face,
    colours: dict[str, Rgb],
) -> MeshData:
    """One exit's portal in the library's frame: world axes, the origin at
    the fascia's middle. On a wall the jambs reach down to the ground, and the
    mesh's foot is below its origin, so the engine stands no collider across
    the door (`PropBatch.post_of`); on a post the fascia tops the post and the
    origin is the post's foot, which takes one."""
    assert station.colour is not None  # `build_region` refuses a station with none
    builder = ColouredBuilder(SIGNS_MATERIAL)
    out = np.array([stand.out[0], 0.0, stand.out[1]])
    right = np.cross(_UP, out)
    half_w, half_f, half_d = 0.5 * sign.width_m, 0.5 * sign.fascia_m, 0.5 * sign.depth_m
    lintel = stand.middle[1] - half_f - stand.ground_y
    fascia = np.zeros(3)
    if stand.on_post:
        fascia = np.array([0.0, stand.middle[1] - stand.ground_y, 0.0])
        post = 2.0 * spec.pole_radius_m
        _box(
            builder,
            np.array([-post, 0.0, -post]),
            np.array([post, fascia[1] - half_f, post]),
            colours[sign.trim],
        )
    box(builder, fascia, (right * half_w, _UP * half_f, out * half_d), colours[sign.fascia])
    faces = (1.0, -1.0) if stand.on_post else (1.0,)
    if not stand.on_post:
        # The jambs, the trim under the fascia and the dark doorway between.
        half_door = 0.5 * sign.door_width_m
        floor = fascia - _UP * (half_f + lintel)
        for side in (-1.0, 1.0):
            jamb = floor + right * side * (half_door + 0.5 * sign.jamb_m) + _UP * 0.5 * lintel
            box(
                builder,
                jamb,
                (right * 0.5 * sign.jamb_m, _UP * 0.5 * lintel, out * half_d),
                colours[station.colour],
            )
        trim = fascia - _UP * (half_f - 0.04)
        box(
            builder,
            trim + out * 0.01,
            (right * half_w, _UP * 0.04, out * half_d),
            colours[sign.trim],
        )
        door = floor + _UP * 0.5 * lintel - out * (half_d - 0.01)
        box(
            builder,
            door,
            (right * half_door, _UP * 0.5 * lintel, out * 0.01),
            colours[sign.opening],
        )
        if letter:
            # Beside the door on the wall, at eye height, as the street plates hang.
            plate = (
                floor
                + right * -(half_w + 0.1 + 0.5 * sign.letter_m)
                + _UP * min(sign.letter_mount_m, lintel - 0.5 * sign.letter_m)
            )
            half_l = 0.5 * sign.letter_m
            box(
                builder,
                plate - out * (half_d - 0.02),
                (right * half_l, _UP * half_l, out * 0.02),
                colours[sign.letter_ground],
            )
            _lettered(
                builder,
                face,
                letter,
                plate - out * (half_d - 0.04 - sign.lift_m),
                right,
                out,
                (sign.letter_fill * sign.letter_m, sign.letter_fill * sign.letter_m),
                colours[sign.letter_ink],
            )
    for facing in faces:
        o, r = out * facing, right * facing
        front = fascia + o * (half_d + sign.lift_m)
        names_from = -half_w + 0.15 * sign.fascia_m
        if letter and stand.on_post:
            square = 0.8 * sign.fascia_m
            at = front + r * (names_from + 0.5 * square)
            corners = [
                at + r * du * 0.5 * square + _UP * dv * 0.5 * square
                for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ]
            builder.polygon(np.array(corners), o, colours[sign.letter_ground])
            _lettered(
                builder,
                face,
                letter,
                at + o * sign.lift_m,
                r,
                o,
                (sign.letter_fill * square, sign.letter_fill * square),
                colours[sign.letter_ink],
            )
            names_from += square + 0.15 * sign.fascia_m
        across = half_w - 0.15 * sign.fascia_m - names_from
        _names(
            builder,
            sign,
            face,
            station,
            front + r * (names_from + 0.5 * across),
            r,
            o,
            (across, sign.fascia_m - sign.trim_m),
            colours[sign.ink],
        )
    return _built(builder, name)


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

    sign = spec.station_exit
    exits = [node for node in fares.get("nodes", []) if node["kind"] == STATION_EXIT]
    if sign is not None and exits:
        stations = {station.en: station for station in station_table(city)}
        face = Face(cached_source(city, sign.font_source), sign.font_weight, sign.flatten_em)
        walls, ground = shipped_walls(city, region_id, out_dir)
        by_id = {int(edge["id"]): edge for edge in graph["edges"]}
        for node in exits:
            report.read[STATION_EXIT] = report.read.get(STATION_EXIT, 0) + 1
            published = node.get("exit") or {}
            station = stations.get(str(published.get("station")))
            if station is None:
                report.refuse(STATION_EXIT, NO_STATION)
                continue
            if station.colour is None:
                report.refuse(STATION_EXIT, NO_COLOUR)
                continue
            lacking = face.lacks(
                sign.fascia_zh.format(station=station.zh)
                + sign.fascia_en.format(station=station.en)
                + str(published.get("letter") or "")
            )
            if lacking:
                raise ValueError(
                    f"stops: {sign.font_source} cannot letter {sorted(lacking)} on "
                    f"{station.en}'s exit sign"
                )
            at = np.array([node["pos"][0], node["pos"][2]], dtype=float)
            stand = exit_stand(
                sign, at, float(node["pos"][1]), road_point(by_id, node), walls, ground
            )
            where = ON_POST if stand.on_post else ON_WALL
            report.exit_signs[where] = report.exit_signs.get(where, 0) + 1
            if stand.wall_m is not None:
                report.exit_wall_m.append(stand.wall_m)
            name = f"exit_{node['id']}"
            meshes[name] = exit_mesh(
                name, spec, sign, stand, station, published.get("letter"), face, colours
            )
            origin = [at[0], stand.ground_y, at[1]] if stand.on_post else stand.middle
            stands.append(placement(name, origin, 0.0))
            report.stood[STATION_EXIT] = report.stood.get(STATION_EXIT, 0) + 1

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
                meshes[TRAM_MESH_NAME] = shelter_mesh(spec.tram, colours)
                meshes[TRAM_POST_MESH_NAME] = shelter_post_mesh(spec, spec.tram, colours)
            stands.append(placement(TRAM_MESH_NAME, foot, heading))
            for post in shelter_posts(spec, spec.tram, foot, heading):
                stands.append(placement(TRAM_POST_MESH_NAME, post, heading))
            report.stood[TRAM_MESH_NAME] = report.stood.get(TRAM_MESH_NAME, 0) + 1

    library = stand_library([meshes[name] for name in sorted(meshes)], stands)
    if library.meshes:
        report.facing_away = sum(facing_away(mesh) for mesh in library.meshes)
        library.publish(report)
        poles = sum(report.stood.get(kind, 0) for kind in POLE_KINDS)
        signs = report.stood.get(STATION_EXIT, 0)
        library.require_every_stand(
            2 * poles + 3 * report.stood.get(TRAM_MESH_NAME, 0) + signs,
            f"{poles} flags on their poles, {report.stood.get(TRAM_MESH_NAME, 0)} shelters "
            f"on two posts each and {signs} station exit signs",
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
            "exit_signs": dict(sorted(report.exit_signs.items())),
            "exit_wall_m": tail_of(report.exit_wall_m),
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
