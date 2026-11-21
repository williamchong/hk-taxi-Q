"""The Buildings Department's signboards, drawn as plain boards (`P3-103`, `Q260`).

The Legal/Validated Signboards Database publishes each lawful board in the
territory as a point with its type, its length, height and thickness in metres,
the street it faces (`FACING HENNESSY ROAD`) and a photo with the board outlined
in red. This stage stands each on the wall the tiles draw nearest its point, in
its published size, as a box in one colour whose faces glow at night.

🔴 **Only where a board is surveyed, and only its board.** Nothing fills a
street the database is silent on; it lists lawful boards only, so a street of
unauthorised ones reads bare.

⚠️ **The point is ON a wall, and that is measured, not assumed.** Against
iB1000's building outlines it lies a median 0.42 m from a wall (p90 2.6 m), so
it is snapped to the nearest wall the shipped tiles draw within `max_snap_m`.
Where two walls are near, the one whose outward normal looks at the published
street wins (`facing_weight_m`); `facing_moved` counts where that overrode the
nearest.

⚠️ **No height is published.** Every `base_m` is authored; boards that overlap
on one wall are stacked, the later id over the earlier, and a projecting board
whose end reaches over the level-0 carriageway is raised to `road_base_m`.

⚠️ **A board's colour is its photo's where the survey is confident, else the
palette's.** `tools/signboard_colour.py` measures it off the outlined part of
the photo; the build never reads a photo itself. Nothing published says what a
board reads, and no lettering is drawn: a shop's name is a trademark (`Q42`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry

from pipeline import signboard_text
from pipeline.colour import lab_to_srgb, srgb_to_lab
from pipeline.config import (
    CONFIG_PATH,
    Config,
    GameTransform,
    Mount,
    Signboards,
    SignText,
    load_config,
)
from pipeline.config_blocks.base import _parse_hex
from pipeline.config_blocks.signboards import PROJECTING, ROOF
from pipeline.documents import read_document, write_document
from pipeline.fetch import cached_source, read_feature_collection, source_dir
from pipeline.gltf import MeshData, Texture, write_glb
from pipeline.meshbuild import Cell, ColouredBuilder, cell_name, face
from pipeline.railings import facing_away
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA
from pipeline.surface_region import read as read_carriageway_region
from pipeline.trees import Faces, tile_triangles

log = logging.getLogger(__name__)

SIGNBOARDS_NAME = "signboards.glb"
SIGNBOARDS_MANIFEST_NAME = "signboards.json"
# 2 since step 2: the manifest names `text_atlas`, the lettering's own PNG.
SIGNBOARDS_MANIFEST_SCHEMA = 2
SIGNBOARDS_MESH_NAME = "signboards"
# The glTF material the engine's importer dispatches on — `SHADERS` in
# `game/tools/generated_scene_import.gd` holds the other end.
SIGNBOARDS_MATERIAL = "signboards"
# The screens (step 3): their own primitive on `signboards_screen.gdshader`.
SCREEN_MESH_NAME = "signboards_screen"
SCREEN_MATERIAL = "signboards_screen"
# The neon tube round every board's lit face but a screen's (`neon_lift_m`): its own
# primitive on `signboards_neon.gdshader`, which draws the tube and only at night.
NEON_MESH_NAME = "signboards_neon"
NEON_MATERIAL = "signboards_neon"
# Where `tools/signboard_colour.py` writes under the sources tree: a stage name,
# on `buildings.HUE_SOURCE_ID`'s terms.
COLOUR_SOURCE_ID = "signboard_colour"
COLOUR_SURVEY_SCHEMA = 1

# `COLOR_0` alpha on a board's two faces: the shader lights them at night, on
# `lamps.py`'s lantern convention (`ColouredBuilder.polygon`).
LIT_ALPHA = 0
# A triangle is a wall when its normal leans off the horizontal by less than this.
_WALL_MAX_UP = 0.1
# A wall triangle narrower than this in plan is a sliver, not a wall.
_WALL_MIN_PLAN_M = 0.3
_GRID_M = 10.0
_URL = re.compile(r"https://[^\s\"<>]+")


@dataclass
class Board:
    ident: str
    kind: str
    mount: Mount
    x: float
    z: float
    length_m: float | None
    height_m: float | None
    thickness_m: float | None
    facing: tuple[str, ...]
    photo: str | None


@dataclass
class SignboardReport:
    features: int = 0
    empty_geometry: int = 0
    outside: int = 0
    # Read inside the region, by published type, drawn or not.
    by_type: dict[str, int] = field(default_factory=dict)
    read: int = 0
    # `read` in disjoint parts: a type no mount is declared for, a size past
    # `max_dimension_m`, no size and no median to give it, no wall within
    # `max_snap_m`, and drawn.
    unmounted: int = 0
    implausible: int = 0
    no_size: int = 0
    no_wall: int = 0
    drawn: int = 0
    drawn_by_mount: dict[str, int] = field(default_factory=dict)
    # A length or height not published, drawn at its type's median.
    sized_by_median: int = 0
    snap_m: list[float] = field(default_factory=list)
    # The published street was found on the road graph, was not, or moved the
    # board off the nearest wall.
    facing_named: int = 0
    facing_unmatched: int = 0
    facing_moved: int = 0
    stacked: int = 0
    over_road: int = 0
    # Where each board's colour came from.
    colour_surveyed: int = 0
    colour_weak: int = 0
    colour_unread: int = 0
    colour_palette: int = 0
    survey_table: bool = False
    cells: int = 0
    triangles: int = 0
    vertices: int = 0
    # Triangles wound against their own normal; `cull_back` draws them as
    # nothing. Must be 0.
    facing_away: int = 0
    bytes: int = 0
    # The lettering: boards named, by trade, and how many near a restaurant
    # licence; then the atlas and the quads.
    lettered: int = 0
    by_trade: dict[str, int] = field(default_factory=dict)
    near_licence: int = 0
    text_atlas_px: int = 0
    text_atlas_bytes: int = 0
    text_triangles: int = 0
    # Boards drawn as screens (`screens:`), and none lettered.
    screens: int = 0
    # The neon tubes' triangles (`neon_lift_m`).
    neon_triangles: int = 0


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------


def _number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0.0 else None


def facing_streets(text: object) -> tuple[str, ...]:
    """The street names a `Location_Description_EN` names: `FACING A / B` is
    `("A", "B")`, upper case; anything that does not open with `FACING` names none."""
    words = str(text or "").strip().upper()
    if not words.startswith("FACING "):
        return ()
    return tuple(name.strip() for name in words[len("FACING ") :].split("/") if name.strip())


def photo_url(text: object) -> str | None:
    """The photo PDF's link out of `Photos_EN`, which wraps it in a `<span>`."""
    found = _URL.search(str(text or ""))
    return found.group(0) if found else None


def read_boards(
    city: Config,
    spec: Signboards,
    region_id: str,
    transform: GameTransform,
    report: SignboardReport,
    *,
    sources_root: Path | None = None,
) -> list[Board]:
    """Every published signboard inside the region's rectangle, in id order."""
    far_x, far_z = city.region_high(region_id)
    collection = read_feature_collection(
        cached_source(city, spec.source, root=sources_root), "signboards"
    )
    boards: list[Board] = []
    for feature in collection["features"]:
        report.features += 1
        properties = feature.get("properties") or {}
        easting = _number(properties.get(spec.fields["easting"]))
        northing = _number(properties.get(spec.fields["northing"]))
        if easting is None or northing is None:
            report.empty_geometry += 1
            continue
        x, _, z = transform.to_game(easting, northing)
        if not (0.0 <= x <= far_x and 0.0 <= z <= far_z):
            report.outside += 1
            continue
        kind = str(properties.get(spec.fields["type"]) or "").strip().upper()
        report.by_type[kind] = report.by_type.get(kind, 0) + 1
        mount = spec.mounts.get(kind)
        ident = properties.get(spec.fields["id"])
        if mount is None or ident is None:
            report.unmounted += 1
            continue
        boards.append(
            Board(
                ident=str(ident),
                kind=kind,
                mount=mount,
                x=float(x),
                z=float(z),
                length_m=_number(properties.get(spec.fields["length"])),
                height_m=_number(properties.get(spec.fields["height"])),
                thickness_m=_number(properties.get(spec.fields["thickness"])),
                facing=facing_streets(properties.get(spec.fields["facing"])),
                photo=photo_url(properties.get(spec.fields["photo"])),
            )
        )
    report.read = sum(report.by_type.values())
    boards.sort(key=lambda board: (len(board.ident), board.ident))
    return boards


def sized(spec: Signboards, boards: list[Board], report: SignboardReport) -> list[Board]:
    """`boards` with a length and height each, refusing a size past
    `max_dimension_m`; a missing one takes its type's median over the published
    ones, and a type with none to take is refused."""
    kept = []
    for board in boards:
        if any(
            value is not None and value > spec.max_dimension_m
            for value in (board.length_m, board.height_m, board.thickness_m)
        ):
            report.implausible += 1
            continue
        kept.append(board)
    medians: dict[str, tuple[float | None, float | None]] = {}
    for kind in {board.kind for board in kept}:
        lengths = [b.length_m for b in kept if b.kind == kind and b.length_m is not None]
        heights = [b.height_m for b in kept if b.kind == kind and b.height_m is not None]
        medians[kind] = (
            float(np.median(lengths)) if lengths else None,
            float(np.median(heights)) if heights else None,
        )
    out = []
    for board in kept:
        length, height = medians[board.kind]
        if board.length_m is None or board.height_m is None:
            if (board.length_m or length) is None or (board.height_m or height) is None:
                report.no_size += 1
                continue
            report.sized_by_median += 1
            board.length_m = board.length_m or length
            board.height_m = board.height_m or height
        if board.thickness_m is None:
            board.thickness_m = spec.default_thickness_m
        out.append(board)
    return out


# --------------------------------------------------------------------------
# The walls and the ground the tiles draw
# --------------------------------------------------------------------------


class Walls:
    """Every wall triangle the shipped tiles draw, as a plan segment with an
    outward normal and the heights it spans.

    The normal is the tile's own stored vertex normal, not one re-derived from
    the winding: the importer lights the wall by it, so it is what the engine
    calls outward.
    """

    def __init__(self, corners: np.ndarray, normals: np.ndarray) -> None:
        """Keeps the triangles that stand upright and span `_WALL_MIN_PLAN_M`
        in plan; `normals` is one stored normal a triangle."""
        plan = corners[:, :, [0, 2]]
        # A wall triangle's three corners lie on one plan line: its two ends are
        # the pair farthest apart.
        pairs = ((0, 1), (1, 2), (0, 2))
        spans = np.stack(
            [np.linalg.norm(plan[:, i] - plan[:, j], axis=1) for i, j in pairs], axis=1
        )
        length = np.linalg.norm(normals, axis=1)
        keep = (
            (length > 0.0)
            & (np.abs(normals[:, 1]) < _WALL_MAX_UP * length)
            & (spans.max(axis=1) >= _WALL_MIN_PLAN_M)
        )
        corners, normals, plan, spans = corners[keep], normals[keep], plan[keep], spans[keep]
        best = spans.argmax(axis=1)
        first = np.array([pairs[k][0] for k in best])
        second = np.array([pairs[k][1] for k in best])
        rows = np.arange(len(plan))
        self.a = plan[rows, first]
        self.b = plan[rows, second]
        flat = normals[:, [0, 2]]
        self.normal = flat / np.linalg.norm(flat, axis=1, keepdims=True)
        self.low = corners[:, :, 1].min(axis=1)
        self.high = corners[:, :, 1].max(axis=1)
        self._cells: dict[Cell, list[int]] = {}
        for index in range(len(self.a)):
            low = np.floor(np.minimum(self.a[index], self.b[index]) / _GRID_M).astype(int)
            high = np.floor(np.maximum(self.a[index], self.b[index]) / _GRID_M).astype(int)
            for cx in range(low[0], high[0] + 1):
                for cz in range(low[1], high[1] + 1):
                    self._cells.setdefault((cx, cz), []).append(index)

    def __len__(self) -> int:
        return len(self.a)

    def near(self, x: float, z: float, reach_m: float) -> list[tuple[int, float, np.ndarray]]:
        """Every wall within `reach_m` of the point: its index, the plan
        distance and the foot of the perpendicular, nearest first."""
        point = np.array([x, z])
        span = math.ceil(reach_m / _GRID_M)
        cx, cz = math.floor(x / _GRID_M), math.floor(z / _GRID_M)
        found: set[int] = set()
        for dx in range(-span, span + 1):
            for dz in range(-span, span + 1):
                found.update(self._cells.get((cx + dx, cz + dz), ()))
        rows = np.array(sorted(found), dtype=np.int64)
        a, along = self.a[rows], self.b[rows] - self.a[rows]
        share = np.clip(np.einsum("ij,ij->i", point - a, along) / (along**2).sum(axis=1), 0.0, 1.0)
        feet = a + share[:, None] * along
        distances = np.linalg.norm(point - feet, axis=1)
        out = [
            (int(rows[k]), float(distances[k]), feet[k])
            for k in np.flatnonzero(distances <= reach_m)
        ]
        out.sort(key=lambda entry: (entry[1], entry[0]))
        return out


def shipped_walls(city: Config, region_id: str, out_dir: Path) -> tuple[Walls, Faces]:
    """The walls the region's tiles draw, and the ground they draw."""
    ground: list[np.ndarray] = []
    walls: list[np.ndarray] = []
    normals: list[np.ndarray] = []
    for mesh, corners, is_ground in tile_triangles(city, region_id, out_dir):
        ground.append(corners[is_ground])
        if mesh.normals is None:
            continue
        walls.append(corners[~is_ground])
        normals.append(mesh.normals[mesh.triangles[~is_ground, 0]].astype(np.float64))
    return Walls(np.concatenate(walls), np.concatenate(normals)), Faces(np.concatenate(ground))


def named_streets(out_dir: Path, region_id: str) -> dict[str, BaseGeometry]:
    """Every level-0 street on the region's road graph, by its English name."""
    rebuild = f"python -m pipeline.roads --region {region_id}"
    graph = read_document(out_dir / ROADGRAPH_NAME, ROADGRAPH_SCHEMA, rebuild)
    lines: dict[str, list[shapely.LineString]] = {}
    for edge in graph["edges"]:
        name = ((edge.get("road_name") or {}).get("en") or "").strip().upper()
        if not name or edge.get("elevation_level", 0) != 0 or len(edge["polyline"]) < 2:
            continue
        plan = [(point[0], point[2]) for point in edge["polyline"]]
        lines.setdefault(name, []).append(shapely.LineString(plan))
    return {name: shapely.MultiLineString(parts) for name, parts in lines.items()}


# --------------------------------------------------------------------------
# Placing
# --------------------------------------------------------------------------


@dataclass
class Placed:
    board: Board
    foot: np.ndarray  # plan, on the wall
    normal: np.ndarray  # plan, outward
    tangent: np.ndarray  # plan, along the wall
    ground_y: float
    wall_top_y: float
    base_y: float = 0.0
    colour: tuple[int, int, int] = (0, 0, 0)
    # The generic name lettered on it, or "" for a plain board.
    name: str = ""

    @property
    def top_y(self) -> float:
        return self.base_y + (self.board.height_m or 0.0)


def snap(
    spec: Signboards,
    board: Board,
    walls: Walls,
    ground: Faces,
    streets: dict[str, BaseGeometry],
    report: SignboardReport,
) -> Placed | None:
    """The board on the wall that best answers its point and its street."""
    candidates = walls.near(board.x, board.z, spec.max_snap_m)
    if not candidates:
        report.no_wall += 1
        return None
    named = [streets[name] for name in board.facing if name in streets]
    if board.facing:
        if named:
            report.facing_named += 1
        else:
            report.facing_unmatched += 1

    def cost(entry: tuple[int, float, np.ndarray]) -> float:
        index, distance, foot = entry
        if not named:
            return distance
        normal = walls.normal[index]
        probe = shapely.Point(*(foot + normal * spec.facing_probe_m))
        nearest = min(named, key=probe.distance)
        way = np.asarray(shapely.shortest_line(nearest, probe).coords[0]) - foot
        length = float(np.linalg.norm(way))
        cosine = float(np.dot(way, normal) / length) if length > 0.0 else 1.0
        return distance + spec.facing_weight_m * (1.0 - cosine)

    chosen = min(candidates, key=lambda entry: (cost(entry), entry[0]))
    index, distance, foot = chosen
    # A facade is several triangles in one plane; only a turn to another
    # facing is a move.
    if float(np.dot(walls.normal[index], walls.normal[candidates[0][0]])) < 0.9:
        report.facing_moved += 1
    report.snap_m.append(distance)
    normal = walls.normal[index]
    tangent = np.array([-normal[1], normal[0]])
    outside = foot + normal * 1.0
    under = ground.heights(float(outside[0]), float(outside[1]))
    low = float(walls.low[index])
    below = under[under <= low + 1.0]
    ground_y = float(below.max()) if len(below) else low
    return Placed(
        board=board,
        foot=foot,
        normal=normal,
        tangent=tangent,
        ground_y=ground_y,
        wall_top_y=float(walls.high[index]),
    )


def _overlaps(spec: Signboards, one: Placed, other: Placed) -> bool:
    """Whether two boards would share space on their wall, ignoring height."""
    projecting = one.board.mount.mount == PROJECTING
    if projecting != (other.board.mount.mount == PROJECTING):
        return False
    if float(np.dot(one.normal, other.normal)) < 0.9:
        return False
    offset = other.foot - one.foot
    across = abs(float(np.dot(offset, one.normal)))
    along = abs(float(np.dot(offset, one.tangent)))
    if projecting:
        return across < spec.stack_radius_m and along < spec.stack_radius_m
    half = 0.5 * ((one.board.length_m or 0.0) + (other.board.length_m or 0.0))
    return across < spec.stack_radius_m and along < half


def stack(
    spec: Signboards, placed: list[Placed], carriageway: BaseGeometry, report: SignboardReport
) -> None:
    """Each board's lowest edge: its mount's base over the ground, raised over
    the road where a blade reaches it, and over every earlier board it would
    otherwise overlap on its wall."""
    shapely.prepare(carriageway)
    cells: dict[Cell, list[Placed]] = {}
    reach = math.ceil(spec.max_dimension_m / _GRID_M)
    for item in placed:
        board = item.board
        if board.mount.mount == ROOF:
            base = item.wall_top_y + board.mount.base_m
        else:
            base = item.ground_y + board.mount.base_m
            if board.mount.mount == PROJECTING:
                end = item.foot + item.normal * (spec.outset_m + (board.length_m or 0.0))
                if carriageway.intersects(shapely.LineString([item.foot, end])):
                    report.over_road += 1
                    base = max(base, item.ground_y + spec.road_base_m)
        cx, cz = (math.floor(v / _GRID_M) for v in item.foot)
        neighbours = [
            other
            for dx in range(-reach, reach + 1)
            for dz in range(-reach, reach + 1)
            for other in cells.get((cx + dx, cz + dz), ())
            if _overlaps(spec, item, other)
        ]
        item.base_y = base
        moved = True
        while moved:
            moved = False
            for other in neighbours:
                if item.base_y < other.top_y + spec.stack_gap_m and other.base_y < item.top_y:
                    item.base_y = other.top_y + spec.stack_gap_m
                    moved = True
        if item.base_y > base:
            report.stacked += 1
        cells.setdefault((cx, cz), []).append(item)


# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------


def read_survey(spec: Signboards, *, sources_root: Path | None = None) -> dict | None:
    """`tools/signboard_colour.py`'s table, or None where it has not been run."""
    if spec.colour_survey is None:
        return None
    path = source_dir(COLOUR_SOURCE_ID, root=sources_root) / spec.colour_survey
    if not path.exists():
        log.warning("signboards: no colour survey at %s; every board takes the palette", path)
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != COLOUR_SURVEY_SCHEMA:
        raise ValueError(
            f"{path} is schema {document.get('schema_version')}, not {COLOUR_SURVEY_SCHEMA}. "
            "Run: python tools/signboard_colour.py"
        )
    return document


def palette_colour(spec: Signboards, ident: str) -> tuple[int, int, int]:
    """The palette's colour for a board, by its id, the same on every build."""
    digest = hashlib.blake2b(ident.encode("utf-8"), digest_size=4).digest()
    return spec.palette[int.from_bytes(digest, "big") % len(spec.palette)]


def clamp_lightness(spec: Signboards, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    lab = srgb_to_lab(np.array([rgb], dtype=np.float64))[0]
    lab[0] = float(np.clip(lab[0], *spec.survey_lightness))
    out = lab_to_srgb(lab[None, :])[0]
    return tuple(int(v) for v in np.clip(np.round(out), 0, 255))  # type: ignore[return-value]


def colour_of(
    spec: Signboards, ident: str, survey: dict | None, report: SignboardReport
) -> tuple[int, int, int]:
    entry = None if survey is None else survey.get("boards", {}).get(ident)
    if entry is not None and entry.get("share", 0.0) >= spec.survey_min_share:
        report.colour_surveyed += 1
        return clamp_lightness(spec, _parse_hex(str(entry["rgb"]), f"colour survey board {ident}"))
    if entry is not None:
        report.colour_weak += 1
    elif survey is not None:
        report.colour_unread += 1
    report.colour_palette += 1
    return palette_colour(spec, ident)


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------


def box(item: Placed, spec: Signboards) -> signboard_text.Box:
    """The board as a box: its centre in plan, its two plan half-axes (across
    its face, through its face) and its height range."""
    board = item.board
    length, thickness = board.length_m or 0.0, board.thickness_m or spec.default_thickness_m
    if board.mount.mount == PROJECTING:
        centre = item.foot + item.normal * (spec.outset_m + 0.5 * length)
        across, through = item.normal * 0.5 * length, item.tangent * 0.5 * thickness
    elif board.mount.mount == ROOF:
        centre = item.foot - item.normal * (spec.roof_setback_m + 0.5 * thickness)
        across, through = item.tangent * 0.5 * length, item.normal * 0.5 * thickness
    else:
        centre = item.foot + item.normal * (spec.outset_m + 0.5 * thickness)
        across, through = item.tangent * 0.5 * length, item.normal * 0.5 * thickness
    return centre, across, through, np.array([item.base_y, item.top_y])


def draw(builder: ColouredBuilder, item: Placed, spec: Signboards) -> None:
    """Six quads: the two faces in the board's colour and lit, the four edges
    darkened by `frame_darken`."""
    centre, across, through, (low, high) = box(item, spec)
    frame = tuple(round(c * (1.0 - spec.frame_darken)) for c in item.colour)

    def corner(sa: float, st: float, y: float) -> np.ndarray:
        plan = centre + sa * across + st * through
        return np.array([plan[0], y, plan[1]])

    def flat(vector: np.ndarray) -> np.ndarray:
        unit = vector / np.linalg.norm(vector)
        return np.array([unit[0], 0.0, unit[1]])

    for sign in (1.0, -1.0):
        lit = np.array(
            [
                corner(-1, sign, low),
                corner(1, sign, low),
                corner(1, sign, high),
                corner(-1, sign, high),
            ]
        )
        face(builder, lit, item.colour, flat(through) * sign, LIT_ALPHA)
        edge = np.array(
            [
                corner(sign, -1, low),
                corner(sign, 1, low),
                corner(sign, 1, high),
                corner(sign, -1, high),
            ]
        )
        face(builder, edge, frame, flat(across) * sign)
    for y, up in ((high, 1.0), (low, -1.0)):
        cap = np.array([corner(-1, -1, y), corner(1, -1, y), corner(1, 1, y), corner(-1, 1, y)])
        face(builder, cap, frame, np.array([0.0, up, 0.0]))


def _built(
    builders: dict[Cell, signboard_text.QuadBuilder],
    name: str,
    material: str,
    texture: Texture | None,
) -> list[MeshData]:
    return [
        mesh
        for cell in sorted(builders)
        if (mesh := builders[cell].build(cell_name(name, cell), material, texture)) is not None
    ]


def _face_quads(
    builder: signboard_text.QuadBuilder,
    item: Placed,
    spec: Signboards,
    lift_m: float,
    rgba: tuple[int, int, int, int],
    *,
    centred: bool,
) -> None:
    """A quad over the board's lit face (both faces of a blade), `lift_m` off
    it, its UVs in metres: from the face's top-left corner, or `centred` from
    its middle."""
    board = box(item, spec)
    _, across, _, (low, high) = board
    width, height = 2.0 * float(np.linalg.norm(across)), high - low
    left, top = (-0.5 * width, -0.5 * height) if centred else (0.0, 0.0)
    cell = (left, top, left + width, top + height)
    up = np.array([0.0, 1.0, 0.0])
    for middle, out in signboard_text.faces(board, item.board.mount.mount, lift_m):
        builder.quad(middle, np.cross(up, out), up, (width, height), cell, rgba)


def screen(builder: signboard_text.QuadBuilder, item: Placed, spec: Signboards) -> None:
    """The screen on the board's lit face, `screen_lift_m` off it. Its UVs are
    metres across and down the face, so the shader's LED pitch is the same on
    every screen; `COLOR_0`'s red is a seed from the id, so two screens do not
    show the same frame."""
    digest = hashlib.blake2b(item.board.ident.encode("utf-8"), digest_size=1).digest()
    _face_quads(
        builder, item, spec, spec.screen_lift_m, (digest[0], 0, 0, LIT_ALPHA), centred=False
    )


def neon(builder: signboard_text.QuadBuilder, item: Placed, spec: Signboards) -> None:
    """The quad the shader draws the neon tube round the rim of, `neon_lift_m`
    off the lit face. Its UVs are metres from the face's centre, so a vertex's
    `abs(UV)` is the face's half-size and the tube's inset and width are metres
    on every board; `COLOR_0` is the board's colour."""
    if spec.neon_lift_m is not None:
        _face_quads(builder, item, spec, spec.neon_lift_m, (*item.colour, LIT_ALPHA), centred=True)


def build_meshes(
    spec: Signboards, placed: list[Placed], atlas: signboard_text.Atlas | None = None
) -> tuple[list[MeshData], list[MeshData], list[MeshData], list[MeshData]]:
    """The boards, their lettering, the screens and the neon, a mesh each a
    plan cell.

    The lettering, the screens and the neon are their own primitives: they need
    `TEXCOORD_0` and their own shaders, and the boards need neither
    (`verify_signs.gd`'s reason for the signs). A screen takes no neon.
    """
    cells: dict[Cell, ColouredBuilder] = {}
    letters: dict[Cell, signboard_text.QuadBuilder] = {}
    screens: dict[Cell, signboard_text.QuadBuilder] = {}
    tubes: dict[Cell, signboard_text.QuadBuilder] = {}
    for item in placed:
        cell: Cell = (
            math.floor(item.foot[0] / spec.cell_m),
            math.floor(item.foot[1] / spec.cell_m),
        )
        if cell not in cells:
            cells[cell] = ColouredBuilder(SIGNBOARDS_MATERIAL)
        draw(cells[cell], item, spec)
        if item.board.ident in spec.screens:
            screen(screens.setdefault(cell, signboard_text.QuadBuilder()), item, spec)
            continue
        neon(tubes.setdefault(cell, signboard_text.QuadBuilder()), item, spec)
        if atlas is not None and spec.text is not None and item.name:
            signboard_text.letter(
                letters.setdefault(cell, signboard_text.QuadBuilder()),
                spec.text,
                atlas,
                item.name,
                (*signboard_text.ink(spec.text, item.colour), LIT_ALPHA),
                item.board.mount.mount,
                box(item, spec),
            )
    meshes = [
        mesh
        for cell in sorted(cells)
        if (mesh := cells[cell].build(cell_name(SIGNBOARDS_MESH_NAME, cell))) is not None
    ]
    lettering: list[MeshData] = []
    if atlas is not None:
        texture = Texture(data=atlas.png, mime_type="image/png", uri=signboard_text.TEXT_ATLAS_NAME)
        lettering = _built(
            letters, signboard_text.TEXT_MESH_NAME, signboard_text.TEXT_MATERIAL, texture
        )
    return (
        meshes,
        lettering,
        _built(screens, SCREEN_MESH_NAME, SCREEN_MATERIAL, None),
        _built(tubes, NEON_MESH_NAME, NEON_MATERIAL, None),
    )


# --------------------------------------------------------------------------
# The region
# --------------------------------------------------------------------------


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> SignboardReport:
    """Read the region's published signboards and write `signboards.glb`."""
    spec = city.signboards
    report = SignboardReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no signboards block; nothing to build", city.id)
        _clear(out_dir)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    boards = sized(
        spec,
        read_boards(city, spec, region_id, transform, report, sources_root=sources_root),
        report,
    )
    walls, ground = shipped_walls(city, region_id, out_dir)
    streets = named_streets(out_dir, region_id)
    survey = read_survey(spec, sources_root=sources_root)
    report.survey_table = survey is not None

    placed = []
    for board in boards:
        item = snap(spec, board, walls, ground, streets, report)
        if item is None:
            continue
        item.colour = colour_of(spec, board.ident, survey, report)
        placed.append(item)
    atlas = None
    if spec.text is not None and spec.text.lettered:
        atlas = signboard_text.build_atlas(spec.text, CONFIG_PATH.parents[2])
        licences = signboard_text.read_licences(
            city, spec.text, region_id, transform, sources_root=sources_root
        )
        name_boards(spec.text, spec.screens, placed, licences, report)
    stack(spec, placed, read_carriageway_region(out_dir, region_id).whole, report)
    for item in placed:
        report.drawn_by_mount[item.board.mount.mount] = (
            report.drawn_by_mount.get(item.board.mount.mount, 0) + 1
        )
    report.drawn = len(placed)

    meshes, lettering, screens, tubes = build_meshes(spec, placed, atlas)
    report.screens = sum(item.board.ident in spec.screens for item in placed)
    report.neon_triangles = sum(len(mesh.triangles) for mesh in tubes)
    report.cells = len(meshes)
    report.triangles = sum(len(mesh.triangles) for mesh in meshes)
    report.vertices = sum(len(mesh.positions) for mesh in meshes)
    report.text_triangles = sum(len(mesh.triangles) for mesh in lettering)
    report.facing_away = sum(facing_away(mesh) for mesh in [*meshes, *lettering, *screens, *tubes])
    _clear(out_dir)
    if meshes:
        report.bytes = write_glb(out_dir / SIGNBOARDS_NAME, [*meshes, *lettering, *screens, *tubes])
    if lettering and atlas is not None:
        report.text_atlas_px = atlas.pixels
        report.text_atlas_bytes = len(atlas.png)
    _write_manifest(out_dir, city, region_id, report)
    return report


def name_boards(
    text: SignText,
    screens: tuple[str, ...],
    placed: list[Placed],
    licences: shapely.STRtree | None,
    report: SignboardReport,
) -> None:
    """Each board's generic name, from its mount, a licence nearby and its street."""
    for item in placed:
        if item.board.ident in screens:
            continue
        near = signboard_text.licensed(text, licences, item.foot)
        name, trade = signboard_text.pick_name(
            text, item.board.ident, item.board.mount.mount, item.board.facing, near
        )
        if not name:
            continue
        item.name = name
        report.lettered += 1
        report.near_licence += int(near)
        report.by_trade[trade] = report.by_trade.get(trade, 0) + 1


def _clear(out_dir: Path) -> None:
    """Remove what an earlier build wrote: a stale mesh or atlas beside a
    manifest that says "none" is what `sync_generated.sh` would ship."""
    (out_dir / SIGNBOARDS_NAME).unlink(missing_ok=True)
    (out_dir / signboard_text.TEXT_ATLAS_NAME).unlink(missing_ok=True)


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: SignboardReport) -> int:
    document = {
        "schema_version": SIGNBOARDS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "asset": SIGNBOARDS_NAME if report.triangles else None,
        "features": report.features,
        "empty_geometry": report.empty_geometry,
        "outside": report.outside,
        # Every published type read inside the region, drawn or not.
        "by_type": dict(sorted(report.by_type.items())),
        "read": report.read,
        # `read` in disjoint parts: no mount declared, a size past
        # `max_dimension_m`, no size to give, no wall near, and drawn.
        "unmounted": report.unmounted,
        "implausible": report.implausible,
        "no_size": report.no_size,
        "no_wall": report.no_wall,
        "drawn": report.drawn,
        "drawn_by_mount": dict(sorted(report.drawn_by_mount.items())),
        # ⚠️ Every height is authored; these say what else is not published.
        "sized_by_median": report.sized_by_median,
        "snap_m": tail_of(report.snap_m),
        "facing_named": report.facing_named,
        "facing_unmatched": report.facing_unmatched,
        "facing_moved": report.facing_moved,
        "stacked": report.stacked,
        "over_road": report.over_road,
        # Where each drawn board's colour came from: the survey, or the palette
        # because the survey was weak, never read the board, or was not run.
        "survey_table": report.survey_table,
        "colour_surveyed": report.colour_surveyed,
        "colour_weak": report.colour_weak,
        "colour_unread": report.colour_unread,
        "colour_palette": report.colour_palette,
        "cells": report.cells,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "facing_away": report.facing_away,
        "bytes": report.bytes,
        # The lettering (`P3-103` step 2): generic names, never a real one.
        "text_atlas": signboard_text.TEXT_ATLAS_NAME if report.text_atlas_px else None,
        "lettered": report.lettered,
        "by_trade": dict(sorted(report.by_trade.items())),
        "near_licence": report.near_licence,
        "text_atlas_px": report.text_atlas_px,
        "text_atlas_bytes": report.text_atlas_bytes,
        "text_triangles": report.text_triangles,
        # The authored screens drawn (step 3).
        "screens": report.screens,
        # The neon tubes, every board but a screen.
        "neon_triangles": report.neon_triangles,
    }
    return write_document(out_dir / SIGNBOARDS_MANIFEST_NAME, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "signboards: %d read -> %d drawn (%d unmounted, %d implausible, %d no size, %d no wall), "
        "%d stacked, %d over the road, %d surveyed colours, %d palette, %d triangles in %d cells",
        report.read,
        report.drawn,
        report.unmounted,
        report.implausible,
        report.no_size,
        report.no_wall,
        report.stacked,
        report.over_road,
        report.colour_surveyed,
        report.colour_palette,
        report.triangles,
        report.cells,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
