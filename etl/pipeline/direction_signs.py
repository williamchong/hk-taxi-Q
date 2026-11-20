"""TD's overhead direction signs on their gantries (`P3-105`, `Q265`).

`DTAD_DS_PLATE_LINE` draws every direction sign's whole face as line-work — its
legends in English and Chinese, lane arrows, route shields, tunnel and airport
symbols and the panel frames — as a callout set beside the road at
`drawing_units_per_m`, with its own size label (`HT7687(ref)/200/19100X2000(H)`)
and reference (`H/WA/Glo-G27A`) drawn under it. A `Leader Line` in
`DTAD_DS_MISC_LINE` runs from the callout to the road, and on a gantry it ends
on a `GS` line in `DTAD_DS_POLE_LINE_C`: the gantry's beam across the
carriageway. This stage fills each gantry board's face into an atlas and hangs
it on its beam, over the road it signs.

🔴 **The words are TD's line-work, never a string.** Nothing in the layer is
text: the face is filled from the strokes (`face_image`), and the size label is
dropped as every part outside a panel. Shipped as TD publishes it, a board out
of date included (the user's call, 2026-11-21).

⚠️ **The fill reads two kinds of lettering, measured on G27A** (`Q265`):
- Chinese is closed outlines, every one drawn twice (62 of 125 parts on G27A);
  even-odd would cancel them, so parts are deduplicated first. Filled, and
  thickened by `bold_m`.
- English is single centre-line strokes of a CAD stroke font, an `o` two open
  arcs: drawn `stroke_m` wide. A closed face of open line-work under
  `counter_max_m2` is a counter and is only stroked; a bigger one (an arrow, a
  shield, the airplane, a panel) is filled, its colour flipping with depth.

⚠️ **The steel is authored, its place is not.** The beam is TD's line; TD draws
no leg, so one stands at each beam end pushed off the drawn asphalt
(`leg_clear_m`, at most `leg_max_push_m`). An end that cannot leave the road
within the push is a cantilever's free end. The board sits on the beam, the
beam's underside at `clearance_m` over the road, as on G57A in Street View.

⚠️ **The scale is measured on two boards**, not published: the drawn width
against the size label's, 4.96 units a metre on G27A and G26A.
"""

from __future__ import annotations

import argparse
import io
import logging
import math
from dataclasses import dataclass, field, replace
from functools import partial
from itertools import pairwise
from pathlib import Path

import numpy as np
import shapely
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry.base import BaseGeometry

from pipeline import gdb
from pipeline.config import Config, DirectionSigns, load_config
from pipeline.documents import write_document
from pipeline.drawnroad import drawn_carriageway
from pipeline.fetch import source_reads
from pipeline.gltf import COLLISION_ONLY_SUFFIX, MeshData, Texture, write_glb
from pipeline.meshbuild import ColouredBuilder, face
from pipeline.polyline import Segments
from pipeline.railings import facing_away
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.signboard_text import _power_of_two
from pipeline.trees import Faces, shipped_faces

log = logging.getLogger(__name__)

DIRECTION_SIGNS_NAME = "direction_signs.glb"
DIRECTION_SIGNS_MANIFEST_NAME = "direction_signs.json"
DIRECTION_SIGNS_MANIFEST_SCHEMA = 1
# The steel and the board's back: vertex-coloured, on the signs' own material
# (`SHADERS` in `game/tools/generated_scene_import.gd`).
FRAME_MESH_NAME = "direction_signs"
FRAME_MATERIAL = "direction_signs"
# The faces: each panel's outline triangulated, sampling the atlas (`TEXTURED` there).
FACE_MESH_NAME = "direction_signs_face"
FACE_MATERIAL = "direction_signs_face"
ATLAS_NAME = "direction_signs_text.png"
COLLIDER_NAME = f"direction_signs_collision{COLLISION_ONLY_SUFFIX}"

_UP = np.array([0.0, 1.0, 0.0])
# Below this a leg's foot is buried, so it meets a footway a kerb high.
_FOOT_DROP_M = 0.2
# How finely a leg is pushed along the beam off the asphalt, and a gantry off a deck.
_PUSH_STEP_M = 0.1
# How finely a beam's line is sampled for a deck over it.
_DECK_SAMPLE_M = 0.5
# A part this near a panel, in real metres, is that panel's.
_PANEL_TOLERANCE_M = 0.01
# A panel's outline is thinned to this before it is triangulated: its rounded
# corners are drawn a vertex a few millimetres.
_OUTLINE_SIMPLIFY_M = 0.02


@dataclass
class DirectionSignReport:
    plates: int = 0
    # Gantry boards (`gantry_code`) whose leader ends in the region — or, with
    # no leader, whose drawing lies in it — and then `read` in disjoint parts.
    read: int = 0
    no_leader: int = 0
    no_beam: int = 0
    off_road: int = 0
    no_panel: int = 0
    under_deck: int = 0
    no_footing: int = 0
    drawn: int = 0
    drawn_codes: list[str] = field(default_factory=list)
    duplicate_parts: int = 0
    label_parts: int = 0
    panels: int = 0
    counters: int = 0
    legs: int = 0
    cantilevers: int = 0
    # Gantries moved off a deck along their normal, and how far.
    cleared: int = 0
    clear_push_m: list[float] = field(default_factory=list)
    leg_push_m: list[float] = field(default_factory=list)
    host_m: list[float] = field(default_factory=list)
    beam_m: list[float] = field(default_factory=list)
    board_width_m: list[float] = field(default_factory=list)
    # A board drawn wider than its beam plus legs: the scale or the beam is off.
    wider_than_beam: int = 0
    atlas_px: int = 0
    atlas_bytes: int = 0
    triangles: int = 0
    face_triangles: int = 0
    collider_triangles: int = 0
    facing_away: int = 0
    bytes: int = 0


# --------------------------------------------------------------------------
# The face
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Panel:
    """One connected panel of a board's drawing, in the drawing's own units."""

    outline: shapely.Polygon
    closed: tuple[shapely.LineString, ...]
    opened: tuple[shapely.LineString, ...]


def parts_of(plate: BaseGeometry) -> tuple[list[shapely.LineString], int]:
    """The drawing's line parts, plan only, each once, and how many repeated.

    TD draws every Chinese outline twice; even-odd filling would cancel it."""
    seen: set[bytes] = set()
    parts: list[shapely.LineString] = []
    duplicates = 0
    for part in shapely.get_parts(shapely.force_2d(plate)):
        if part.is_empty or len(part.coords) < 2:
            continue
        key = shapely.to_wkb(shapely.normalize(part))
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        parts.append(part)
    return parts, duplicates


def _faces(lines) -> list[shapely.Polygon]:
    """Every face the lines enclose, noded first: a panel's frame meets the
    board under it in a T that `polygonize` cannot see un-noded."""
    if not lines:
        return []
    noded = shapely.get_parts(shapely.union_all(list(lines)))
    return shapely.get_parts(shapely.polygonize(noded)).tolist()


def panels_of(parts: list[shapely.LineString], spec: DirectionSigns) -> tuple[list[Panel], int]:
    """The board's panels and how many parts lie outside all of them (the label).

    A panel is a connected piece of the drawing's faces at least
    `panel_min_m2`; the size label's letters are far smaller."""
    if not parts:
        return [], 0
    scale = spec.drawing_units_per_m
    faces = _faces(parts)
    if not faces:
        return [], len(parts)
    merged = shapely.union_all(faces)
    outlines = [
        shapely.Polygon(piece.exterior)
        for piece in shapely.get_parts(merged)
        if piece.geom_type == "Polygon" and piece.area >= spec.panel_min_m2 * scale**2
    ]
    tolerance = _PANEL_TOLERANCE_M * scale
    grown = [outline.buffer(tolerance) for outline in outlines]
    owned: list[list[shapely.LineString]] = [[] for _ in outlines]
    labels = 0
    for part in parts:
        for index, area in enumerate(grown):
            if area.contains(part):
                owned[index].append(part)
                break
        else:
            labels += 1
    panels = [
        Panel(
            outline=outline,
            closed=tuple(p for p in mine if p.is_closed and len(p.coords) >= 4),
            opened=tuple(p for p in mine if not (p.is_closed and len(p.coords) >= 4)),
        )
        for outline, mine in zip(outlines, owned, strict=True)
    ]
    return panels, labels


def face_image(
    panel: Panel,
    spec: DirectionSigns,
    field_rgb: tuple[int, int, int],
    ink_rgb: tuple[int, int, int],
) -> tuple[Image.Image, int]:
    """The panel's face, `px_per_m`, and how many counters it stroked.

    Filled shapes and the Chinese colour by even-odd depth: the panel itself is
    depth 1 and takes the field, a shape on it the ink, a shape on that the
    field again (the tunnel symbol's portal). Strokes take the colour opposite
    to what lies under their middle."""
    scale = spec.drawing_units_per_m
    counter = spec.counter_max_m2 * scale**2
    faces = [f for f in _faces(panel.opened) if panel.outline.contains(f.representative_point())]
    shells = [shapely.Polygon(f.exterior) for f in faces if f.area > counter]
    counters = sum(1 for f in faces if f.area <= counter)
    rings = [shapely.Polygon(part.coords) for part in panel.closed]

    x0, y0, x1, y1 = panel.outline.bounds
    k = spec.px_per_m * spec.supersample / scale
    width = max(1, math.ceil((x1 - x0) * k))
    height = max(1, math.ceil((y1 - y0) * k))

    def pixels(coords) -> list[tuple[float, float]]:
        return [((x - x0) * k, (y1 - y) * k) for x, y in coords]

    def mask(shape: BaseGeometry) -> np.ndarray:
        image = Image.new("L", (width, height), 0)
        draw = ImageDraw.Draw(image)
        for polygon in shapely.get_parts(shape).tolist():
            if polygon.geom_type != "Polygon" or polygon.is_empty:
                continue
            draw.polygon(pixels(polygon.exterior.coords), fill=255)
            for hole in polygon.interiors:
                draw.polygon(pixels(hole.coords), fill=0)
        return np.asarray(image) > 0

    odd = np.zeros((height, width), dtype=bool)
    for shell in shells:
        odd ^= mask(shell)
    # The Chinese in raster: TD's outlines cross themselves now and then, which
    # a vector even-odd refuses, and the thickening is a dilation of the fill.
    chinese = np.zeros((height, width), dtype=bool)
    for ring in rings:
        chinese ^= mask(ring)
    grow = round(0.5 * spec.bold_m * spec.px_per_m * spec.supersample)
    if grow > 0 and chinese.any():
        dilated = Image.fromarray(chinese.astype(np.uint8) * 255).filter(
            ImageFilter.MaxFilter(2 * grow + 1)
        )
        chinese = np.asarray(dilated) > 0
    odd ^= chinese
    rgb = np.empty((height, width, 3), dtype=np.uint8)
    rgb[:] = field_rgb
    rgb[~odd] = ink_rgb
    # Outside the panel's rounded frame is the field too: linear filtering at the outline reads it.
    rgb[~mask(panel.outline)] = field_rgb
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    under = [*shells, *rings]
    filled = shapely.STRtree(under) if under else None
    stroke = max(1, round(spec.stroke_m * spec.px_per_m * spec.supersample))
    for part in panel.opened:
        middle = part.interpolate(0.5, normalized=True)
        depth = 0
        if filled is not None:
            depth = sum(1 for i in filled.query(middle) if under[i].contains(middle))
        colour = field_rgb if depth % 2 == 0 else ink_rgb
        draw.line(pixels(part.coords), fill=colour, width=stroke, joint="curve")
    if spec.supersample > 1:
        image = image.resize(
            (max(1, width // spec.supersample), max(1, height // spec.supersample)),
            Image.LANCZOS,
        )
    return image, counters


@dataclass(frozen=True)
class Atlas:
    png: bytes
    width: int
    height: int
    # Each image's cell as (u0, v0, u1, v1), v down from the image's top.
    cells: list[tuple[float, float, float, float]]

    @property
    def pixels(self) -> int:
        return self.width * self.height


def pack(images: list[Image.Image], pad: int) -> Atlas:
    """Shelf-packed into the narrowest power-of-two width that holds the widest,
    and the shortest power-of-two height. Each image is ringed by `pad` pixels
    of its own edge, so linear filtering never reads a neighbour."""
    widest = max(image.width for image in images) + 2 * pad
    width = max(_power_of_two(widest), 256)
    order = sorted(range(len(images)), key=lambda i: -images[i].height)
    spots: list[tuple[int, int]] = [(0, 0)] * len(images)
    x = y = shelf = 0
    for index in order:
        w, h = images[index].width + 2 * pad, images[index].height + 2 * pad
        if x + w > width:
            x, y, shelf = 0, y + shelf, 0
        spots[index] = (x, y)
        x, shelf = x + w, max(shelf, h)
    height = _power_of_two(y + shelf)
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    cells = []
    for index, image in enumerate(images):
        sx, sy = spots[index]
        padded = np.pad(np.asarray(image.convert("RGB")), ((pad, pad), (pad, pad), (0, 0)), "edge")
        canvas[sy : sy + padded.shape[0], sx : sx + padded.shape[1]] = padded
        u0, v0 = (sx + pad) / width, (sy + pad) / height
        cells.append((u0, v0, u0 + image.width / width, v0 + image.height / height))
    out = io.BytesIO()
    Image.fromarray(canvas).save(out, format="PNG", optimize=True)
    return Atlas(png=out.getvalue(), width=width, height=height, cells=cells)


# --------------------------------------------------------------------------
# The read
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Gantry:
    """A gantry board and where its leader says it stands, in source metres."""

    code: str
    plate: BaseGeometry
    # The leader's road end, or None with no leader.
    foot: tuple[float, float] | None
    # The beam's two ends, or None.
    beam: tuple[tuple[float, float], tuple[float, float]] | None


def read_gantries(
    city: Config,
    spec: DirectionSigns,
    region_id: str,
    report: DirectionSignReport,
    *,
    sources_root: Path | None,
) -> list[Gantry]:
    """Every gantry board the region owns, with its leader's foot and its beam."""
    bounds = city.projected_bounds(region_id)
    low_x, low_y, high_x, high_y = bounds.bbox
    reach = spec.reach_m
    wide = (low_x - reach, low_y - reach, high_x + reach, high_y + reach)
    region = shapely.box(low_x, low_y, high_x, high_y)
    gantries: list[Gantry] = []
    for path, member in source_reads(city, spec, region_id, root=sources_root):

        def layer(name: str, columns: list[str], path=path, member=member) -> gdb.Layer:
            return gdb.read_layer(
                path,
                name,
                columns=columns,
                bbox=wide,
                zip_member=member,
                expect_crs=city.projected_crs,
            )

        plates = layer(spec.layer.layer, spec.layer.columns)
        leaders = layer(spec.leaders.layer, spec.leaders.columns)
        beams = layer(spec.beams.layer, spec.beams.columns)
        codes = plates.column(spec.layer.field("code"))
        report.plates += len(plates)
        boards = [
            (str(code), shapely.force_2d(shapely.from_wkb(wkb)))
            for code, wkb in zip(codes, plates.geometry, strict=True)
            if code is not None and spec.gantry_code in str(code)
        ]
        ends = [
            (np.asarray(part.coords[0]), np.asarray(part.coords[-1]))
            for part in _lines_of(leaders, spec.leaders.field("kind"), spec.leader_kind)
        ]
        spans = _lines_of(beams, spec.beams.field("kind"), spec.beam_kind)
        beam_tree = shapely.STRtree(spans) if spans else None
        for code, plate in boards:
            foot = _foot(plate, [b for _, b in boards if b is not plate], ends, spec)
            where = shapely.Point(foot) if foot is not None else plate.centroid
            if not region.contains(where):
                continue
            report.read += 1
            beam = None
            if foot is not None and beam_tree is not None:
                hits = beam_tree.query(where, predicate="dwithin", distance=spec.beam_reach_m)
                if len(hits):
                    nearest = min(hits, key=lambda i: spans[i].distance(where))
                    line = spans[nearest]
                    beam = (tuple(line.coords[0][:2]), tuple(line.coords[-1][:2]))
            gantries.append(Gantry(code=code, plate=plate, foot=foot, beam=beam))
    gantries.sort(key=lambda g: g.code)
    return gantries


def _lines_of(layer: gdb.Layer, field_name: str, kind: str) -> list[shapely.LineString]:
    """Every plan line part of the layer's features of that kind."""
    return [
        part
        for value, wkb in zip(layer.column(field_name), layer.geometry, strict=True)
        if str(value) == kind
        for part in shapely.get_parts(shapely.force_2d(shapely.from_wkb(wkb))).tolist()
        if len(part.coords) >= 2
    ]


def _foot(
    plate: BaseGeometry,
    others: list[BaseGeometry],
    ends: list[tuple[np.ndarray, np.ndarray]],
    spec: DirectionSigns,
) -> tuple[float, float] | None:
    """The road end of the leader that touches this board at its other end.

    A leader touching a board at both ends, or another board nearer, is not
    this board's. With several, the shortest wins: a callout's own leader runs
    straight to its gantry."""
    best: tuple[float, tuple[float, float]] | None = None
    for a, b in ends:
        for near, far in ((a, b), (b, a)):
            here = shapely.Point(near)
            touch = plate.distance(here)
            if touch > spec.leader_touch_m:
                continue
            if plate.distance(shapely.Point(far)) <= spec.leader_touch_m:
                continue
            if any(other.distance(here) < touch for other in others):
                continue
            length = float(np.linalg.norm(far - near))
            if best is None or length < best[0]:
                best = (length, (float(far[0]), float(far[1])))
    return None if best is None else best[1]


# --------------------------------------------------------------------------
# The gantry
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Hung:
    """A board on its beam, in the region's frame."""

    code: str
    panels: list[Panel]
    images: list[Image.Image]
    # The beam's ends with its legs (or free ends) in plan, and which carry one.
    ends: tuple[np.ndarray, np.ndarray]
    legs: tuple[bool, bool]
    road_y: float
    # Where along the beam the board's middle hangs, and the face's normal.
    centre: np.ndarray
    normal: np.ndarray


def _leg_end(
    end: np.ndarray, outward: np.ndarray, road: BaseGeometry, spec: DirectionSigns
) -> tuple[np.ndarray, float] | None:
    """The beam end pushed outward until it stands `leg_clear_m` off the asphalt."""
    steps = round(spec.leg_max_push_m / _PUSH_STEP_M)
    for step in range(steps + 1):
        point = end + outward * step * _PUSH_STEP_M
        here = shapely.Point(point)
        if not road.contains(here) and road.distance(here) >= spec.leg_clear_m:
            return point, step * _PUSH_STEP_M
    return None


def _clear_of_decks(
    a: np.ndarray,
    b: np.ndarray,
    along: np.ndarray,
    normal: np.ndarray,
    wide: float,
    tall: float,
    road_y: float,
    structure: Faces,
    spec: DirectionSigns,
) -> float | None:
    """How far along the face's normal the gantry moves to stand clear of a
    deck, 0.0 where nothing is in the way, or None where no shift within
    `clear_max_push_m` clears it.

    A deck is in the way where its walking surface lies over the beam's line
    between the beam's underside and the board's top plus `deck_depth_m`: G26A's
    GS line runs the length of a footbridge whose walkway is 6.8 m up, under a
    board that tops out at 8.8 m. TD's sign is on the bridge's face; the
    nearest clear line in front of or behind it stands for that."""
    low = road_y + spec.clearance_m
    high = low + spec.beam_depth_m + tall + spec.deck_depth_m
    reach = float(np.linalg.norm(b - a))
    over = max(0.0, 0.5 * (wide - reach))
    samples = [a + along * t for t in np.arange(-over, reach + over + 1e-9, _DECK_SAMPLE_M)]

    def clashes(shift: float) -> bool:
        for point in samples:
            here = point + normal * shift
            heights = structure.heights(float(here[0]), float(here[1]))
            if np.any((heights > low) & (heights < high)):
                return True
        return False

    steps = round(spec.clear_max_push_m / _PUSH_STEP_M)
    for step in range(steps + 1):
        for sign in (1.0, -1.0):
            shift = sign * step * _PUSH_STEP_M
            if not clashes(shift):
                return shift
    return None


def _facing(snap_heading_deg: float, direction: str, offset_m: float) -> np.ndarray:
    """The plan normal a board faces: back down the traffic that reads it.

    A one-way edge's traffic runs from `from` to `to`; on a two-way edge it is
    the flow on the side the beam's middle fell (drive on the left: the
    nearside, `offset_m > 0`, runs from `from` to `to`)."""
    heading = math.radians(snap_heading_deg)
    travel = np.array([math.sin(heading), -math.cos(heading)])
    if direction == "both" and offset_m < 0.0:
        travel = -travel
    return -travel


def hang(
    gantry: Gantry,
    spec: DirectionSigns,
    city: Config,
    region_id: str,
    segments: Segments,
    edges: dict[int, dict],
    road: BaseGeometry,
    structure: Faces,
    report: DirectionSignReport,
    colours: tuple[tuple[int, int, int], tuple[int, int, int]],
) -> Hung | None:
    if gantry.foot is None:
        report.no_leader += 1
        return None
    if gantry.beam is None:
        report.no_beam += 1
        return None
    transform = city.game_transform(region_id)
    (ax, ay), (bx, by) = gantry.beam
    gx, _, gz = transform.to_game(np.array([ax, bx]), np.array([ay, by]))
    a, b = np.array([gx[0], gz[0]]), np.array([gx[1], gz[1]])
    middle = 0.5 * (a + b)
    snap = segments.nearest(float(middle[0]), float(middle[1]))
    if snap.distance_m > spec.host_max_m or not road.contains(shapely.Point(middle)):
        report.off_road += 1
        return None

    parts, duplicates = parts_of(gantry.plate)
    panels, labels = panels_of(parts, spec)
    if not panels:
        report.no_panel += 1
        return None

    along = (b - a) / float(np.linalg.norm(b - a))
    edge = edges[snap.edge]
    traffic = _facing(snap.heading_deg, str(edge["direction"]), snap.offset_m)
    # The beam runs across the road; the face's normal is the plan perpendicular
    # to it nearest the traffic's.
    across = np.array([-along[1], along[0]])
    normal = across if float(np.dot(across, traffic)) >= 0.0 else -across

    scale = spec.drawing_units_per_m
    tall = (
        max(p.outline.bounds[3] for p in panels) - min(p.outline.bounds[1] for p in panels)
    ) / scale
    wide = (
        max(p.outline.bounds[2] for p in panels) - min(p.outline.bounds[0] for p in panels)
    ) / scale
    shift = _clear_of_decks(a, b, along, normal, wide, tall, snap.y, structure, spec)
    if shift is None:
        report.under_deck += 1
        return None
    if shift != 0.0:
        report.cleared += 1
        report.clear_push_m.append(abs(shift))
        a, b = a + normal * shift, b + normal * shift

    placed = []
    for end, outward in ((a, -along), (b, along)):
        placed.append(_leg_end(end, outward, road, spec))
    if placed[0] is None and placed[1] is None:
        report.no_footing += 1
        return None

    report.duplicate_parts += duplicates
    report.label_parts += labels
    report.host_m.append(snap.distance_m)
    report.beam_m.append(float(np.linalg.norm(b - a)))
    ends, legs = [], []
    for end, leg in zip((a, b), placed, strict=True):
        if leg is None:
            ends.append(end)
            legs.append(False)
            report.cantilevers += 1
        else:
            ends.append(leg[0])
            legs.append(True)
            report.legs += 1
            report.leg_push_m.append(leg[1])

    fx, _, fz = transform.to_game(gantry.foot[0], gantry.foot[1])
    span = ends[1] - ends[0]
    reach = float(np.linalg.norm(span))
    t = float(np.clip(np.dot(np.array([fx, fz]) - ends[0], span) / reach**2, 0.0, 1.0))
    centre = ends[0] + span * t
    images, counters = [], 0
    for panel in panels:
        image, stroked = face_image(panel, spec, *colours)
        images.append(image)
        counters += stroked
    report.counters += counters
    report.panels += len(panels)
    report.board_width_m.append(wide)
    if wide > reach + 1e-6:
        report.wider_than_beam += 1
    return Hung(
        code=gantry.code,
        panels=panels,
        images=images,
        ends=(ends[0], ends[1]),
        legs=(legs[0], legs[1]),
        road_y=snap.y,
        centre=centre,
        normal=normal,
    )


# --------------------------------------------------------------------------
# The mesh
# --------------------------------------------------------------------------


def box(
    builder: ColouredBuilder,
    centre: np.ndarray,
    axes: tuple[np.ndarray, np.ndarray, np.ndarray],
    colour: tuple[int, int, int],
) -> None:
    """A box: `centre` and its three half-axes, each face wound outward."""
    for axis in range(3):
        u, v = axes[(axis + 1) % 3], axes[(axis + 2) % 3]
        for sign in (1.0, -1.0):
            middle = centre + sign * axes[axis]
            quad = np.array([middle - u - v, middle + u - v, middle + u + v, middle - u + v])
            face(builder, quad, colour, sign * axes[axis])


def _on_board(
    plane: tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float],
    points: np.ndarray,
    depth: float,
) -> np.ndarray:
    """Drawing units on a board to the world, `depth` along its normal."""
    base, right, normal, middle, bottom, scale = plane
    across = (points[:, 0] - middle) / scale
    up = (points[:, 1] - bottom) / scale
    return base + across[:, None] * right + up[:, None] * _UP + depth * normal


def _flat(plan: np.ndarray, y: float = 0.0) -> np.ndarray:
    return np.array([plan[0], y, plan[1]])


class FaceBuilder:
    """The boards' faces: triangles sampling the atlas, white `COLOR_0` (the
    lettering shader's identity), each wound to face its board's normal."""

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._uvs: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []

    def triangle(self, corners: np.ndarray, uv: np.ndarray, normal: np.ndarray) -> None:
        if float(np.cross(corners[1] - corners[0], corners[2] - corners[0]) @ normal) < 0.0:
            corners, uv = corners[::-1], uv[::-1]
        self._positions.append(corners)
        self._uvs.append(uv)
        self._normals.append(np.tile(normal, (3, 1)))

    def build(self, texture: Texture) -> MeshData | None:
        if not self._positions:
            return None
        count = 3 * len(self._positions)
        return MeshData(
            name=FACE_MESH_NAME,
            positions=np.vstack(self._positions).astype(np.float32),
            normals=np.vstack(self._normals).astype(np.float32),
            triangles=np.arange(count, dtype=np.uint32).reshape(-1, 3),
            colours=np.full((count, 4), 255, dtype=np.uint8),
            uvs=np.vstack(self._uvs).astype(np.float32),
            texture=texture,
            material=FACE_MATERIAL,
        )


def build_meshes(
    spec: DirectionSigns,
    hung: list[Hung],
    atlas: Atlas,
    steel: tuple[int, int, int],
) -> list[MeshData]:
    """The steel and the boards' backs, the faces, and the legs' collider."""
    frame = ColouredBuilder(FRAME_MATERIAL)
    solid = ColouredBuilder(FRAME_MATERIAL)
    faces = FaceBuilder()
    scale = spec.drawing_units_per_m
    cell = 0
    for item in hung:
        a, b = item.ends
        along = (b - a) / float(np.linalg.norm(b - a))
        beam_low = item.road_y + spec.clearance_m
        beam_top = beam_low + spec.beam_depth_m
        middle = _flat(0.5 * (a + b), 0.5 * (beam_low + beam_top))
        half_beam = (
            _flat(along) * 0.5 * float(np.linalg.norm(b - a)),
            _UP * 0.5 * spec.beam_depth_m,
            _flat(np.array([-along[1], along[0]])) * 0.5 * spec.beam_width_m,
        )
        box(frame, middle, half_beam, steel)
        for end, leg in zip(item.ends, item.legs, strict=True):
            if not leg:
                continue
            foot = item.road_y - _FOOT_DROP_M
            half = 0.5 * spec.leg_width_m
            axes = (
                _flat(along) * half,
                _UP * 0.5 * (beam_top - foot),
                _flat(np.array([-along[1], along[0]])) * half,
            )
            centre = _flat(end, 0.5 * (beam_top + foot))
            box(frame, centre, axes, steel)
            box(solid, centre, axes, steel)

        normal = _flat(item.normal)
        right = np.cross(_UP, normal)
        x0 = min(p.outline.bounds[0] for p in item.panels)
        x1 = max(p.outline.bounds[2] for p in item.panels)
        y0 = min(p.outline.bounds[1] for p in item.panels)
        board_middle = 0.5 * (x0 + x1)
        plane = (_flat(item.centre, beam_top), right, normal, board_middle, y0, scale)
        half = 0.5 * spec.board_thickness_m
        world = partial(_on_board, plane)

        for panel in item.panels:
            # The panel's own outline, not its box: G26A's two top plates stand
            # apart over the board, and the sky shows between them.
            outline = shapely.Polygon(panel.outline.exterior).simplify(_OUTLINE_SIMPLIFY_M * scale)
            outline = shapely.geometry.polygon.orient(outline, 1.0)
            triangles = [
                np.asarray(t.exterior.coords)[:3]
                for t in shapely.get_parts(shapely.constrained_delaunay_triangles(outline))
            ]
            ring = np.asarray(outline.exterior.coords)
            for corners in triangles:
                face(frame, world(corners, half), steel, normal)
                face(frame, world(corners, -half), steel, -normal)
            for start, end in pairwise(ring):
                edge = np.array([start, end])
                quad = np.vstack([world(edge, -half), world(edge[::-1], half)])
                outward = (end[1] - start[1]) * right - (end[0] - start[0]) * _UP
                face(frame, quad, steel, outward)
            px0, py0, px1, py1 = panel.outline.bounds
            u0, v0, u1, v1 = atlas.cells[cell]
            for corners in triangles:
                uv = np.column_stack(
                    [
                        u0 + (corners[:, 0] - px0) / (px1 - px0) * (u1 - u0),
                        v0 + (py1 - corners[:, 1]) / (py1 - py0) * (v1 - v0),
                    ]
                )
                faces.triangle(world(corners, half + spec.face_lift_m), uv, normal)
            cell += 1
    meshes = []
    built = frame.build(FRAME_MESH_NAME)
    if built is not None:
        meshes.append(built)
    texture = Texture(data=atlas.png, mime_type="image/png", uri=ATLAS_NAME)
    drawn = faces.build(texture)
    if drawn is not None:
        meshes.append(drawn)
    collider = solid.build(COLLIDER_NAME)
    if collider is not None:
        meshes.append(replace(collider, colours=None, material=None))
    return meshes


# --------------------------------------------------------------------------
# The region
# --------------------------------------------------------------------------


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> DirectionSignReport:
    """Read the region's gantry boards and write `direction_signs.glb`."""
    spec = city.direction_signs
    report = DirectionSignReport()
    out_dir = city.out_dir(region_id, out_root)
    _clear(out_dir)
    if spec is None or city.signs is None:
        log.info("city '%s' declares no direction_signs block; nothing to hang", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    livery = city.signs.colours
    colours = (livery[spec.colours["field"]], livery[spec.colours["ink"]])
    steel = livery[spec.colours["steel"]]
    gantries = read_gantries(city, spec, region_id, report, sources_root=sources_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    at_grade = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    segments = Segments.of(at_grade)
    edges = {int(edge["id"]): edge for edge in at_grade}
    road = drawn_carriageway(city, out_dir, region_id)
    if road is None:
        raise ValueError("direction_signs needs a carriageway_region: a leg stands off the asphalt")
    _, structure = shipped_faces(city, region_id, out_dir)

    hung = []
    for gantry in gantries:
        item = hang(
            gantry, spec, city, region_id, segments, edges, road, structure, report, colours
        )
        if item is not None:
            hung.append(item)
    report.drawn = len(hung)
    report.drawn_codes = [item.code for item in hung]
    if hung:
        atlas = pack([image for item in hung for image in item.images], spec.pad_px)
        meshes = build_meshes(spec, hung, atlas, steel)
        report.collider_triangles = sum(len(m.triangles) for m in meshes if m.name == COLLIDER_NAME)
        report.triangles = sum(len(m.triangles) for m in meshes if m.name == FRAME_MESH_NAME)
        report.face_triangles = sum(len(m.triangles) for m in meshes if m.name == FACE_MESH_NAME)
        report.facing_away = sum(facing_away(m) for m in meshes if m.material is not None)
        report.bytes = write_glb(out_dir / DIRECTION_SIGNS_NAME, meshes)
        report.atlas_px = atlas.pixels
        report.atlas_bytes = len(atlas.png)
    _write_manifest(out_dir, city, region_id, report)
    return report


def _clear(out_dir: Path) -> None:
    """Remove what an earlier build wrote, so a manifest saying "none" ships none."""
    (out_dir / DIRECTION_SIGNS_NAME).unlink(missing_ok=True)
    (out_dir / ATLAS_NAME).unlink(missing_ok=True)


def _write_manifest(
    out_dir: Path, city: Config, region_id: str, report: DirectionSignReport
) -> int:
    drawn = report.drawn > 0
    document = {
        "schema_version": DIRECTION_SIGNS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "asset": DIRECTION_SIGNS_NAME if drawn else None,
        "text_atlas": ATLAS_NAME if drawn else None,
        "plates": report.plates,
        # Gantry boards the region owns, then `read` in disjoint parts: no
        # leader, no beam at the leader's foot, the beam over no level-0 road,
        # no panel in the drawing, no line clear of a deck, no leg off the
        # asphalt, and drawn.
        "read": report.read,
        "no_leader": report.no_leader,
        "no_beam": report.no_beam,
        "off_road": report.off_road,
        "no_panel": report.no_panel,
        "under_deck": report.under_deck,
        "no_footing": report.no_footing,
        "drawn": report.drawn,
        "drawn_codes": report.drawn_codes,
        "duplicate_parts": report.duplicate_parts,
        "label_parts": report.label_parts,
        "panels": report.panels,
        "counters": report.counters,
        "legs": report.legs,
        "cantilevers": report.cantilevers,
        "cleared": report.cleared,
        "clear_push_m": tail_of(report.clear_push_m),
        "leg_push_m": tail_of(report.leg_push_m),
        "host_m": tail_of(report.host_m),
        "beam_m": tail_of(report.beam_m),
        "board_width_m": tail_of(report.board_width_m),
        "wider_than_beam": report.wider_than_beam,
        "text_atlas_px": report.atlas_px,
        "text_atlas_bytes": report.atlas_bytes,
        "triangles": report.triangles,
        "face_triangles": report.face_triangles,
        "collider_triangles": report.collider_triangles,
        "facing_away": report.facing_away,
        "bytes": report.bytes,
    }
    return write_document(out_dir / DIRECTION_SIGNS_MANIFEST_NAME, document)


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
        "direction_signs: %d gantry boards read -> %d drawn (%d no leader, %d no beam, "
        "%d off road, %d no panel, %d under a deck, %d no footing), %d cleared, "
        "%d legs, %d cantilevers, atlas %d px, %d + %d triangles",
        report.read,
        report.drawn,
        report.no_leader,
        report.no_beam,
        report.off_road,
        report.no_panel,
        report.under_deck,
        report.no_footing,
        report.cleared,
        report.legs,
        report.cantilevers,
        report.atlas_px,
        report.triangles,
        report.face_triangles,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
