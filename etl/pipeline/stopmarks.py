"""Published bus stop, stand and tram stop paint, drawn as its own mesh (`P3-89`).

TD surveys what marks a stopping place on the road, and this stage draws it
where it was surveyed:

- **Boxes and bars are lines** — `RM1048` the bus stop boundary, `RM1049` the
  taxi / minibus / scheduled-service stand, `RM1045` the tram stop line — each
  drawn as a band at the sheet's width and module.
- **Legends are strokes** — `RM1047` BUS STOP 巴士站 and `RM1175` / `RM1176`'s
  taxi lettering are filed in `DTAD_RD_MARK_SYM_LINE` as the strokes of a stick
  font, in place, turned and to size. So no typeface is authored (`P3-21`'s
  refusal was of `DTAD_RD_MARK_ANNO`'s rectangles); the one authored dimension
  is the stroke's width, `legend_stroke_m`.

The shape is `crossings.py`'s: nothing is registered to the ribbon, each
vertex stands at the drawn road's own height through `DrawnSurface`, and
`_place` is `boxjunctions._place`, imported. Two things are this layer's own:

- **A marking belongs to the region its middle is in.** A box across the seam
  is drawn whole by one region, never cut and never twice.
- **A piece over nothing drawn is refused** (`off_road_m`): a stand box is the
  kerb's, and where the ribbon stops short of it the paint would lie on the
  footway.
- **A legend filed as a point is stood with the region's own strokes as its
  glyph** (`glyph_of`). TD files a legend as strokes or as a point and an
  angle, never both, so the glyph is the median of the region's stroke legends
  of that code, each read in its own traffic's frame, and `glyph_fit_m` says
  how far each of them lies from it. ⚠️ The point is taken for the legend's
  MIDDLE — `arrows.py`'s reading of the same layer, and unpublished.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.boxjunctions import _place
from pipeline.config import Config, GameTransform, StopMark, StopMarks, load_config
from pipeline.config_blocks.stopmarks import BARE, PAINTS
from pipeline.crossings import _plan
from pipeline.documents import read_document, write_document
from pipeline.drawnroad import flows_along
from pipeline.drawnsurface import DrawnSurface
from pipeline.fetch import source_reads
from pipeline.geometry import wound_up
from pipeline.gltf import write_glb
from pipeline.meshbuild import (
    CellBuilder,
    PaintMeshReport,
    cell_meshes,
    import_quantum_m,
)
from pipeline.polyline import Segments, frame, game_heading_deg, plan_lengths_2d
from pipeline.railings import AT_GRADE
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

STOPMARKS_NAME = "stopmarks.glb"
STOPMARKS_MANIFEST_NAME = "stopmarks.json"
STOPMARKS_MANIFEST_SCHEMA = 1

# glTF material names, the contract channel `crossings.KINDS` is:
# `tools/generated_scene_import.gd` maps each onto its `.tres`. They are the
# mesh names too. ⚠️ **No `-col` suffix** — paint is not a collider.
KINDS = {paint: f"stopmarks_{paint}" for paint in PAINTS}

# A painted run shorter than this is rounding, not paint (`roadmarks._MIN_MARK_M`).
_MIN_RUN_M = 1e-6


@dataclass
class StopMarkReport(PaintMeshReport):
    """What the stage read and drew.

    The partitions, asserted where they are complete:

        features == other_code + on_structure + empty_geometry + other_region
                    + duplicates + candidates
        symbols == symbols_other_code + symbols_on_structure + symbols_empty
                   + symbols_other_region + symbols_no_glyph + symbols_stood
        candidates + symbols_stood == drawn + too_far + off_road
    """

    features: int = 0
    other_code: int = 0
    on_structure: int = 0
    empty_geometry: int = 0
    other_region: int = 0
    # A feature filed a second time, vertex for vertex. TD files 44 of the two
    # regions' 113 `RM1049` twice — a line a paint, by the look of it — and the
    # pair drawn is two coplanar bands.
    duplicates: int = 0
    candidates: int = 0

    # Legends filed as a point: the read, and how many found a glyph to stand.
    symbols: int = 0
    symbols_other_code: int = 0
    symbols_on_structure: int = 0
    symbols_empty: int = 0
    symbols_other_region: int = 0
    symbols_no_glyph: int = 0
    symbols_stood: int = 0
    # Per legend with a glyph: how many stroke legends it is the median of.
    # Then, over all of them: how far the worst vertex of each lies from the
    # glyph once laid onto it — whether they are one drawing — and the turn that
    # took, which is how far the traffic's heading is from the legend's own.
    glyph_from: dict[str, int] = field(default_factory=dict)
    glyph_fit_m: list[float] = field(default_factory=list)
    glyph_turn_deg: list[float] = field(default_factory=list)

    drawn: int = 0
    too_far: int = 0
    off_road: int = 0
    drawn_from_symbols_by_id: dict[str, int] = field(default_factory=dict)
    drawn_by_id: dict[str, int] = field(default_factory=dict)
    # Metres of surveyed line drawn, and of paint laid by colour: a module's
    # bare stretches are in the first and not the second.
    drawn_m_by_id: dict[str, float] = field(default_factory=dict)
    paint_m_by_kind: dict[str, float] = field(
        default_factory=lambda: dict.fromkeys(KINDS.values(), 0.0)
    )
    # Paint refused piece by piece for lying over nothing drawn, drawn features'
    # included: the ribbon stopping short of a surveyed box.
    off_road_m: float = 0.0
    off_road_m_by_id: dict[str, float] = field(default_factory=dict)

    nearest_edge_m: list[float] = field(default_factory=list)
    height_spread_m: list[float] = field(default_factory=list)

    # `boxjunctions._place`'s counters — see `BoxJunctionReport`.
    vertices_drawn: int = 0
    vertices_over_cap: int = 0
    over_cap_rise_m: list[float] = field(default_factory=list)
    vertices_over_void: int = 0
    void_reach_m: list[float] = field(default_factory=list)
    polygons_placed: int = 0
    polygons_split: int = 0
    pieces_placed: int = 0

    measured = staticmethod(tail_of)


@dataclass(frozen=True)
class Marking:
    """One published feature: its mark and its lines in the game's `(x, z)` plan."""

    mark: StopMark
    lines: tuple[np.ndarray, ...]
    # A legend filed as a point, stood from the glyph rather than surveyed.
    stood: bool = False

    @property
    def length_m(self) -> float:
        return float(sum(plan_lengths_2d(line)[-1] for line in self.lines))

    @property
    def middle(self) -> np.ndarray:
        """The middle of the feature's extent: what says which region and which
        road it belongs to."""
        points = np.vstack(self.lines)
        return 0.5 * (points.min(axis=0) + points.max(axis=0))


def read_markings(
    city: Config,
    spec: StopMarks,
    region_id: str,
    transform: GameTransform,
    region_high: tuple[float, float],
    report: StopMarkReport,
    *,
    sources_root: Path | None = None,
) -> list[Marking]:
    """Every declared mark's features at grade whose middle is in the region."""
    by_layer: dict[str, list[StopMark]] = defaultdict(list)
    for mark in spec.marks:
        by_layer[mark.layer.layer].append(mark)

    markings: list[Marking] = []
    seen: set[tuple[str, bytes]] = set()
    for marks in by_layer.values():
        layer = marks[0].layer
        by_code = {code: mark for mark in marks for code in mark.codes}
        for path, member in source_reads(city, spec, region_id, root=sources_root):
            read = gdb.read_layer(
                path,
                layer.layer,
                columns=layer.columns,
                bbox=city.projected_bounds(region_id).bbox,
                zip_member=member,
                expect_crs=city.projected_crs,
            )
            codes = read.column(layer.field("code"))
            levels = read.column(layer.field("level"))
            owners, parts = gdb.polylines(read)
            by_feature: dict[int, list[np.ndarray]] = defaultdict(list)
            for owner, points in zip(owners, parts, strict=True):
                by_feature[int(owner)].append(np.asarray(points, dtype=np.float64)[:, :2])
            for owner in range(len(read.fids)):
                report.features += 1
                mark = by_code.get(str(codes[owner]).strip().upper())
                usable = [
                    part
                    for part in by_feature.get(owner, [])
                    if len(part) >= 2 and np.isfinite(part).all()
                ]
                if mark is None:
                    report.other_code += 1
                elif str(levels[owner]).strip().lower() not in AT_GRADE:
                    report.on_structure += 1
                elif not usable:
                    report.empty_geometry += 1
                else:
                    marking = Marking(mark, tuple(_plan(transform, part) for part in usable))
                    x, z = marking.middle
                    # To the millimetre, the survey's own unit.
                    shape = (mark.id, np.round(np.vstack(marking.lines), 3).tobytes())
                    if not (0.0 <= x <= region_high[0] and 0.0 <= z <= region_high[1]):
                        report.other_region += 1
                    elif shape in seen:
                        report.duplicates += 1
                    else:
                        seen.add(shape)
                        report.candidates += 1
                        markings.append(marking)
    return markings


@dataclass(frozen=True)
class Symbol:
    """One legend filed as a point: where, and which way its glyph heads —
    `ANGLE` as a game heading, turned into the traffic's frame."""

    mark: StopMark
    x: float
    z: float
    heading_deg: float


def read_symbols(
    city: Config,
    spec: StopMarks,
    region_id: str,
    transform: GameTransform,
    region_high: tuple[float, float],
    report: StopMarkReport,
    *,
    sources_root: Path | None = None,
) -> list[Symbol]:
    """Every legend's point-filed features at grade inside the region."""
    by_layer: dict[str, list[StopMark]] = defaultdict(list)
    for mark in spec.marks:
        if mark.symbols is not None:
            by_layer[mark.symbols.layer.layer].append(mark)

    symbols: list[Symbol] = []
    for marks in by_layer.values():
        layer = marks[0].symbols.layer  # type: ignore[union-attr]  # filtered above
        by_code = {code: mark for mark in marks for code in mark.codes}
        for path, member in source_reads(city, spec, region_id, root=sources_root):
            read = gdb.read_layer(
                path,
                layer.layer,
                columns=layer.columns,
                bbox=city.projected_bounds(region_id).bbox,
                zip_member=member,
                expect_crs=city.projected_crs,
            )
            codes = read.column(layer.field("code"))
            levels = read.column(layer.field("level"))
            bearings = read.column(layer.field("bearing"))
            owners, plan = gdb.points(read)
            game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])
            for row, owner in enumerate(owners):
                report.symbols += 1
                mark = by_code.get(str(codes[owner]).strip().upper())
                x, z = float(game_x[row]), float(game_z[row])
                # Only a claimed code's angle is read: another's may be null.
                bearing = _bearing(bearings[owner]) if mark is not None else None
                if mark is None:
                    report.symbols_other_code += 1
                elif str(levels[owner]).strip().lower() not in AT_GRADE:
                    report.symbols_on_structure += 1
                elif bearing is None or not np.isfinite([x, z]).all():
                    report.symbols_empty += 1
                elif not (0.0 <= x <= region_high[0] and 0.0 <= z <= region_high[1]):
                    report.symbols_other_region += 1
                else:
                    heading = game_heading_deg(bearing) + mark.symbols.turn_deg  # type: ignore[union-attr]
                    symbols.append(Symbol(mark, x, z, heading % 360.0))
    return symbols


def _bearing(value: object) -> float | None:
    """A published angle, or None where it is null or not a number."""
    try:
        bearing = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return bearing if np.isfinite(bearing) else None


def _in_flow_frame(
    marking: Marking, segments: Segments, one_way: dict[int, bool]
) -> tuple[np.ndarray, ...]:
    """A legend's strokes as `(along, across)` metres about its middle, in the
    frame of the traffic that reads it: `parked._flow_heading`'s rule."""
    x, z = marking.middle
    snap = segments.nearest(float(x), float(z))
    heading = snap.heading_deg
    if not flows_along(snap.offset_m, one_way[snap.edge]):
        heading += 180.0
    along, across = frame(heading)
    local = [np.column_stack([line @ along, line @ across]) for line in marking.lines]
    points = np.vstack(local)
    middle = 0.5 * (points.min(axis=0) + points.max(axis=0))
    return tuple(line - middle for line in local)


def glyph_of(
    mark: StopMark,
    markings: list[Marking],
    segments: Segments,
    one_way: dict[int, bool],
    report: StopMarkReport,
) -> tuple[np.ndarray, ...] | None:
    """The legend's glyph: the vertex-wise median of the region's stroke legends
    of this mark, over the commonest stroke layout among them. None where the
    region surveys no stroke legend to take it from.

    The median, so one legend read against the wrong flow (a two-way street's
    far kerb) moves nothing; `glyph_turn_deg` is where it shows.
    """
    by_layout: dict[tuple[int, ...], list[tuple[np.ndarray, ...]]] = defaultdict(list)
    for marking in markings:
        if marking.mark is mark and not marking.stood:
            layout = tuple(len(line) for line in marking.lines)
            by_layout[layout].append(_in_flow_frame(marking, segments, one_way))
    if not by_layout:
        return None
    # The commonest layout; the first read among equals, so a rebuild agrees.
    members = max(by_layout.values(), key=len)
    cuts = np.cumsum([len(stroke) for stroke in members[0]])[:-1]
    stacked = np.stack([np.vstack(member) for member in members])
    # Twice: the first median is of legends each a degree or two off the
    # traffic's heading (a 12 m legend's ends swing 0.2 m a degree), the second
    # of the same legends laid onto it, so what is left is the survey's own.
    glyph = np.median(stacked, axis=0)
    fitted = np.stack([_laid_onto(glyph, member)[0] for member in stacked])
    glyph = np.median(fitted, axis=0)
    report.glyph_from[mark.id] = len(members)
    for member in stacked:
        laid, turn_deg = _laid_onto(glyph, member)
        report.glyph_fit_m.append(float(np.hypot(*(laid - glyph).T).max()))
        report.glyph_turn_deg.append(abs(turn_deg))
    return tuple(np.split(glyph, cuts))


def _laid_onto(glyph: np.ndarray, member: np.ndarray) -> tuple[np.ndarray, float]:
    """`member` turned and shifted to lie closest on `glyph`, vertex for vertex,
    and the turn it took in degrees."""
    centre, about = glyph.mean(axis=0), member.mean(axis=0)
    ours, theirs = glyph - centre, member - about
    turn = np.arctan2(
        float(np.sum(theirs[:, 0] * ours[:, 1] - theirs[:, 1] * ours[:, 0])),
        float(np.sum(theirs * ours)),
    )
    cos, sin = np.cos(turn), np.sin(turn)
    laid = theirs @ np.array([[cos, sin], [-sin, cos]]) + centre
    return laid, float(np.degrees(turn))


def stand_symbols(
    spec: StopMarks,
    markings: list[Marking],
    symbols: list[Symbol],
    segments: Segments,
    one_way: dict[int, bool],
    report: StopMarkReport,
) -> list[Marking]:
    """Each point-filed legend as the marking its glyph makes there."""
    glyphs = {
        mark.id: glyph_of(mark, markings, segments, one_way, report)
        for mark in spec.marks
        if mark.symbols is not None
    }
    stood: list[Marking] = []
    for symbol in symbols:
        glyph = glyphs[symbol.mark.id]
        if glyph is None:
            report.symbols_no_glyph += 1
            continue
        along, across = frame(symbol.heading_deg)
        origin = np.array([symbol.x, symbol.z])
        lines = tuple(origin + stroke[:, :1] * along + stroke[:, 1:] * across for stroke in glyph)
        stood.append(Marking(symbol.mark, lines, stood=True))
        report.symbols_stood += 1
    return stood


def painted_runs(mark: StopMark, total: float) -> list[tuple[str, float, float]]:
    """The painted intervals along a line of length `total`, as `(paint, start,
    stop)`; the module repeats from the line's start and its last run is cut
    where the line ends."""
    if mark.continuous:
        return [(mark.module[0][0], 0.0, total)]
    runs: list[tuple[str, float, float]] = []
    # ⚠️ `index * period`, never `start += period` (`roadmarks._MIN_MARK_M`).
    for index in range(int(np.ceil(total / mark.period_m))):
        start = index * mark.period_m
        for paint, length in mark.module:
            stop = min(start + length, total)
            if paint != BARE and stop - start > _MIN_RUN_M:
                runs.append((paint, start, stop))
            start += length
    return runs


def band_quads(mark: StopMark, line: np.ndarray) -> list[tuple[str, np.ndarray]]:
    """One line as `(paint, quad)` pieces: a rectangle per straight segment per
    painted run, wound to face `+Y`.

    A legend's stroke is squared off half a width past each segment's ends, so
    the strokes of a character meet at their corners; a line's are not, because
    its ends are the survey's.
    """
    along = plan_lengths_2d(line)
    half = 0.5 * mark.width_m
    cap = half if mark.legend else 0.0
    quads: list[tuple[str, np.ndarray]] = []
    for paint, start, stop in painted_runs(mark, float(along[-1])):
        for index in range(len(line) - 1):
            low, high = float(along[index]), float(along[index + 1])
            if high - low <= _MIN_RUN_M:
                continue
            head, tail = max(start, low), min(stop, high)
            if tail - head <= _MIN_RUN_M:
                continue
            direction = (line[index + 1] - line[index]) / (high - low)
            across = np.array([-direction[1], direction[0]])
            first = line[index] + direction * (head - low - cap)
            last = line[index] + direction * (tail - low + cap)
            quad = np.array(
                [
                    first + half * across,
                    last + half * across,
                    last - half * across,
                    first - half * across,
                ]
            )
            quads.append((paint, wound_up(quad)))
    return quads


def draw(
    spec: StopMarks,
    markings: list[Marking],
    segments: Segments,
    drawn: DrawnSurface,
    report: StopMarkReport,
) -> tuple[dict[str, CellBuilder], float]:
    """Every marking onto the drawn road, one builder per paint.

    Apart from `build_region` so it can be driven without a geodatabase.
    """
    builders = {kind: CellBuilder(kind, spec.cell_m) for kind in KINDS.values()}
    every = [line for marking in markings for line in marking.lines]
    report.import_quantum_m = round(import_quantum_m(np.vstack(every)), 6) if every else 0.0
    thinness_bar_m = 2.0 * report.import_quantum_m

    for marking in markings:
        mark = marking.mark
        x, z = marking.middle
        snap = segments.nearest(float(x), float(z))
        # Recorded for every candidate, before any refusal (`Q58`).
        report.nearest_edge_m.append(snap.distance_m)
        if snap.distance_m > spec.max_offset_m:
            report.too_far += 1
            continue

        heights: list[float] = []
        for line in marking.lines:
            for paint, quad in band_quads(mark, line):
                # The quad's long side: its run along the line (a legend's caps in).
                run_m = float(np.linalg.norm(quad[1] - quad[0]))
                centre = quad.mean(axis=0)
                if not drawn.covers(float(centre[0]), float(centre[1])):
                    report.off_road_m += run_m
                    report.off_road_m_by_id[mark.id] = (
                        report.off_road_m_by_id.get(mark.id, 0.0) + run_m
                    )
                    continue
                kind = KINDS[paint]
                heights.extend(
                    _place(builders[kind], drawn, quad, spec.lift_m, report, thinness_bar_m)
                )
                report.paint_m_by_kind[kind] += run_m
        if not heights:
            report.off_road += 1
            continue
        report.drawn += 1
        report.drawn_by_id[mark.id] = report.drawn_by_id.get(mark.id, 0) + 1
        if marking.stood:
            report.drawn_from_symbols_by_id[mark.id] = (
                report.drawn_from_symbols_by_id.get(mark.id, 0) + 1
            )
        report.drawn_m_by_id[mark.id] = report.drawn_m_by_id.get(mark.id, 0.0) + marking.length_m
        report.height_spread_m.append(max(heights) - min(heights))

    assert len(markings) == report.drawn + report.too_far + report.off_road
    return builders, thinness_bar_m


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> StopMarkReport:
    """Read the region's published stop and stand paint and write `stopmarks.glb`."""
    spec = city.stop_marks
    report = StopMarkReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no stop_marks block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform, region_high = city.game_transform(region_id), city.region_high(region_id)
    markings = read_markings(
        city, spec, region_id, transform, region_high, report, sources_root=sources_root
    )
    symbols = read_symbols(
        city, spec, region_id, transform, region_high, report, sources_root=sources_root
    )
    assert report.features == (
        report.other_code
        + report.on_structure
        + report.empty_geometry
        + report.other_region
        + report.duplicates
        + report.candidates
    )

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, the restriction every snap in the pipeline makes (`Q15`).
    edges = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    segments = Segments.of(edges)
    one_way = {int(edge["id"]): str(edge["direction"]) != "both" for edge in edges}
    markings += stand_symbols(spec, markings, symbols, segments, one_way, report)
    assert report.symbols == (
        report.symbols_other_code
        + report.symbols_on_structure
        + report.symbols_empty
        + report.symbols_other_region
        + report.symbols_no_glyph
        + report.symbols_stood
    )
    drawn = DrawnSurface.of(
        read_document(
            out_dir / SURFACE_MANIFEST_NAME,
            SURFACE_MANIFEST_SCHEMA,
            f"python -m pipeline.surface --region {region_id}",
        ),
        level=0,
    )

    builders, thinness_bar_m = draw(spec, markings, segments, drawn, report)
    meshes = cell_meshes(builders, thinness_bar_m, report)
    if meshes:
        report.bytes = write_glb(out_dir / STOPMARKS_NAME, meshes)

    _write_manifest(out_dir, city, region_id, report)
    return report


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: StopMarkReport) -> int:
    def rounded(values: dict[str, float]) -> dict[str, float]:
        return {key: round(value, 2) for key, value in sorted(values.items())}

    document = {
        "schema_version": STOPMARKS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, as `crossings.json`'s is.
        "asset": STOPMARKS_NAME if report.triangles else None,
        # The read, as six disjoint parts of `features`.
        "features": report.features,
        "other_code": report.other_code,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "other_region": report.other_region,
        "duplicates": report.duplicates,
        "candidates": report.candidates,
        # The legends filed as points, as six disjoint parts of `symbols`.
        "symbols": report.symbols,
        "symbols_other_code": report.symbols_other_code,
        "symbols_on_structure": report.symbols_on_structure,
        "symbols_empty": report.symbols_empty,
        "symbols_other_region": report.symbols_other_region,
        "symbols_no_glyph": report.symbols_no_glyph,
        "symbols_stood": report.symbols_stood,
        "glyph_from": dict(sorted(report.glyph_from.items())),
        "glyph_fit_m": report.measured(report.glyph_fit_m),
        "glyph_turn_deg": report.measured(report.glyph_turn_deg),
        # The join, as three disjoint parts of `candidates + symbols_stood`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        "off_road": report.off_road,
        "drawn_by_id": dict(sorted(report.drawn_by_id.items())),
        "drawn_from_symbols_by_id": dict(sorted(report.drawn_from_symbols_by_id.items())),
        "drawn_m_by_id": rounded(report.drawn_m_by_id),
        "paint_m_by_kind": rounded(report.paint_m_by_kind),
        "off_road_m": round(report.off_road_m, 2),
        "off_road_m_by_id": rounded(report.off_road_m_by_id),
        "nearest_edge_m": report.measured(report.nearest_edge_m),
        "height_spread_m": report.measured(report.height_spread_m),
        "vertices_drawn": report.vertices_drawn,
        "vertices_over_cap": report.vertices_over_cap,
        "over_cap_rise_m": report.measured(report.over_cap_rise_m),
        "vertices_over_void": report.vertices_over_void,
        "void_reach_m": report.measured(report.void_reach_m),
        "polygons_placed": report.polygons_placed,
        "polygons_split": report.polygons_split,
        "pieces_placed": report.pieces_placed,
        **report.mesh_tail(),
    }
    return write_document(out_dir / STOPMARKS_MANIFEST_NAME, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "stopmarks: %d features -> %d candidates (%d filed twice) -> %d drawn (%d too far, "
        "%d off the road), %d triangles",
        report.features,
        report.candidates,
        report.duplicates,
        report.drawn,
        report.too_far,
        report.off_road,
        report.triangles,
    )
    log.info(
        "  %d legends filed as points: %d stood (%s), %d with no glyph; glyphs from %s, "
        "fit %s m, turned %s deg",
        report.symbols - report.symbols_other_code,
        report.symbols_stood,
        dict(sorted(report.drawn_from_symbols_by_id.items())),
        report.symbols_no_glyph,
        dict(sorted(report.glyph_from.items())),
        report.measured(report.glyph_fit_m),
        report.measured(report.glyph_turn_deg),
    )
    log.info(
        "  drawn by id: %s; paint: %s m; %.0f m refused over nothing drawn: %s",
        dict(sorted(report.drawn_by_id.items())),
        {key: round(value) for key, value in report.paint_m_by_kind.items()},
        report.off_road_m,
        {key: round(value) for key, value in sorted(report.off_road_m_by_id.items())} or "none",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
