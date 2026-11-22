"""Published road lettering, drawn as its own mesh (`P3-21`, `Q262`).

TD files the words painted on the carriageway — `CENTRAL 中區`, `KOWLOON 九龍`,
`HAPPY VALLEY 跑馬地`, `BEWARE OF PED 小心行人` — in `DTAD_RD_MARK_ANNO`: each
legend its string, an `Angle`, and the rectangle the lettering fills. Long
words are filed in fragments, a lane's width each (`CEN` and `TRAL` are two
features), and each is drawn where it was filed.

- **The letterforms are the one authored thing.** No stroke is published, so
  the glyphs are `road_text.font_source`'s outlines at `font_weight`, flattened
  to `flatten_em`, triangulated once per character, and stretched into TD's
  rectangle — the rectangle sets the proportions, so the face decides little
  beyond the stroke weight. ⚠️ The rectangle is the text's FRAME (advances by
  line box), not its ink: `Face.block`.
- **The rectangle fixes the axis; the traffic fixes the facing.** `Angle` is
  the plan's reading angle, and `FlipAngle` turns it to read upright on the
  drawing, so it is right modulo 180 and no better. The letters' tops point
  the way the nearest flow runs — `stopmarks._in_flow_frame`'s rule — and
  `axis_residual_deg` is how far TD's axis lies from that flow
  (`bearing_tolerance_deg` refuses, counted as `off_axis`).
- **The rest is `stopmarks.py`'s shape**: a legend belongs to the region its
  middle is in, every triangle stands on the drawn road through
  `boxjunctions._place`, a triangle over nothing drawn is refused
  (`off_road_m2`), and a deck legend (`deck_codes`, `Q134`) is hosted among
  off-grade edges and stood on that level's drawn surface.
"""

from __future__ import annotations

import argparse
import logging
import math
import re
from dataclasses import dataclass, field, replace
from functools import cache
from pathlib import Path

import numpy as np
import shapely
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

from pipeline import gdb
from pipeline.boxjunctions import _place
from pipeline.config import Config, GameTransform, RoadText, load_config
from pipeline.crossings import _plan
from pipeline.documents import read_document, write_document
from pipeline.drawnroad import flows_along
from pipeline.drawnsurface import DrawnSurface
from pipeline.fetch import cached_source, source_reads
from pipeline.geometry import twice_area, wound_up
from pipeline.gltf import MeshData, write_glb
from pipeline.mesh import weld
from pipeline.meshbuild import (
    CellBuilder,
    PaintMeshReport,
    cell_meshes,
    import_quantum_m,
)
from pipeline.polyline import (
    Segments,
    axis_residual_deg,
    directed_residual_deg,
    frame,
    game_heading_deg,
)
from pipeline.railings import AT_GRADE
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.stopmarks import _bearing
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

ROADTEXT_NAME = "roadtext.glb"
ROADTEXT_MANIFEST_NAME = "roadtext.json"
ROADTEXT_MANIFEST_SCHEMA = 1

# The glTF material and mesh name: `tools/generated_scene_import.gd` maps it
# onto the road marks' white. ⚠️ No `-col` suffix — paint is not a collider.
KIND = "roadtext_white"

# `<FNT name="ENGINEERING" size="5.00">HAPPY</FNT>`, `<BOL>…</BOL>`: ArcGIS's
# text-formatting tags, which say how the drawing set it and nothing of the paint.
_MARKUP = re.compile(r"<[^>]*>")


@dataclass
class RoadTextReport(PaintMeshReport):
    """What the stage read and drew.

    The partitions, asserted where they are complete:

        features == no_text + refused + glyph_missing + on_structure
                    + empty_geometry + other_region + candidates + deck_candidates
        candidates + deck_candidates == drawn + too_far + off_axis + off_road
    """

    features: int = 0
    no_text: int = 0
    refused: int = 0
    glyph_missing: int = 0
    # The characters the face lacks, each once, so a re-cut can be named.
    missing_characters: set[str] = field(default_factory=set)
    on_structure: int = 0
    empty_geometry: int = 0
    other_region: int = 0
    candidates: int = 0
    deck_candidates: int = 0

    drawn: int = 0
    drawn_on_decks: int = 0
    too_far: int = 0
    off_axis: int = 0
    off_road: int = 0
    # Of `off_road`: deck legends with no deck surface drawn to stand on.
    no_deck_drawn: int = 0
    characters_drawn: int = 0
    drawn_by_text: dict[str, int] = field(default_factory=dict)
    # TD's axis against the traffic's, over every legend near enough to a road
    # to have one — the refusals included (`Q58`).
    axis_residual_deg: list[float] = field(default_factory=list)
    nearest_edge_m: list[float] = field(default_factory=list)
    # The ink's extent along the letters — their height on a one-line legend:
    # what says the paint is legible from a car.
    letter_height_m: list[float] = field(default_factory=list)
    off_road_m2: float = 0.0
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


# ---------------------------------------------------------------------------
# The face
# ---------------------------------------------------------------------------


class _FlatteningPen(BasePen):
    """A glyph's contours as closed point rings in font units, every curve cut
    into chords no further than `tolerance` from it."""

    def __init__(self, glyph_set: object, tolerance: float) -> None:
        super().__init__(glyph_set)
        self.tolerance = tolerance
        self.rings: list[list[tuple[float, float]]] = []
        self._ring: list[tuple[float, float]] = []

    def _chords(self, deviation: float) -> int:
        # A curve whose control polygon bends by `deviation` stays within
        # deviation / (4 n^2) of n chords — the second difference's bound.
        return max(1, math.ceil(math.sqrt(deviation / (4.0 * self.tolerance))))

    def _moveTo(self, pt: tuple[float, float]) -> None:
        self._ring = [pt]

    def _lineTo(self, pt: tuple[float, float]) -> None:
        self._ring.append(pt)

    def _qCurveToOne(self, pt1: tuple[float, float], pt2: tuple[float, float]) -> None:
        p0, p1, p2 = (np.asarray(p, dtype=np.float64) for p in (self._ring[-1], pt1, pt2))
        n = self._chords(float(np.linalg.norm(p0 - 2.0 * p1 + p2)))
        for t in np.arange(1, n + 1) / n:
            point = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2
            self._ring.append((float(point[0]), float(point[1])))

    def _curveToOne(
        self, pt1: tuple[float, float], pt2: tuple[float, float], pt3: tuple[float, float]
    ) -> None:
        p0, p1, p2, p3 = (np.asarray(p, dtype=np.float64) for p in (self._ring[-1], pt1, pt2, pt3))
        bend = max(np.linalg.norm(p0 - 2 * p1 + p2), np.linalg.norm(p1 - 2 * p2 + p3))
        n = self._chords(1.5 * float(bend))
        for t in np.arange(1, n + 1) / n:
            point = (
                (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3
            )
            self._ring.append((float(point[0]), float(point[1])))

    def _closePath(self) -> None:
        if len(self._ring) >= 3:
            self.rings.append(self._ring)
        self._ring = []

    _endPath = _closePath


def _filled(rings: list[list[tuple[float, float]]]) -> shapely.Geometry:
    """A glyph's contours as the area they fill.

    🔴 **Not even-odd.** A variable font keeps its strokes as overlapping
    contours (instancing does not remove overlaps without `skia-pathops`), so
    where two strokes of 中 cross, even-odd would punch a hole. The fill is the
    non-zero rule's, read off the winding: the union of the contours wound the
    way the glyph's largest one is, less the union of those wound against it.
    """
    polygons = [shapely.make_valid(shapely.Polygon(ring)) for ring in rings]
    areas = [twice_area(np.asarray(ring)) for ring in rings]
    signs = [float(np.sign(area)) for area in areas]
    if not polygons:
        return shapely.Polygon()
    outer = signs[int(np.argmax(np.abs(areas)))]
    filled = shapely.union_all([p for p, s in zip(polygons, signs, strict=True) if s == outer])
    holes = [p for p, s in zip(polygons, signs, strict=True) if s != outer]
    if holes:
        filled = shapely.difference(filled, shapely.union_all(holes))
    return filled


@dataclass(frozen=True)
class Glyph:
    """One character's triangles in font units; the pen's step is `Face.advance`."""

    triangles: np.ndarray  # (n, 3, 2)


class Face:
    """`road_text.font_source` at `font_weight`, read through fontTools.

    Each character is flattened and triangulated once and cached; a legend is
    a layout of cached glyphs, so the cost is per distinct character."""

    def __init__(self, path: Path, weight: float, flatten_em: float) -> None:
        font = TTFont(str(path))
        location = None
        if "fvar" in font:
            axes = {axis.axisTag: axis for axis in font["fvar"].axes}
            if "wght" not in axes:
                raise ValueError(f"{path.name} is variable but has no weight axis")
            low, high = axes["wght"].minValue, axes["wght"].maxValue
            if not low <= weight <= high:
                raise ValueError(f"font_weight {weight} is outside {path.name}'s {low}-{high}")
            if "MVAR" in font:
                raise ValueError(f"{path.name} varies its line box with weight; instance it")
            # Read at the weight, not instanced: instancing rewrites every
            # glyph of a CJK font (3.6 s) to draw the forty a region uses.
            location = {"wght": weight}
        self.em = float(font["head"].unitsPerEm)
        # The line box a drawing program sets text in: what TD's rectangle is.
        self.ascent = float(font["hhea"].ascent)
        self.descent = float(font["hhea"].descent)
        self._cmap = font.getBestCmap()
        self._glyphs = font.getGlyphSet(location=location)
        self._tolerance = flatten_em * self.em

    def lacks(self, text: str) -> set[str]:
        """The characters of `text` the face cannot draw (a space draws nothing
        and is never lacking)."""
        return {char for char in text if not char.isspace() and ord(char) not in self._cmap}

    @cache  # noqa: B019 — one Face per build; the cache is its point
    def glyph(self, char: str) -> Glyph:
        name = self._cmap[ord(char)]
        pen = _FlatteningPen(self._glyphs, self._tolerance)
        self._glyphs[name].draw(pen)
        filled = _filled(pen.rings)
        triangles = [
            np.asarray(triangle.exterior.coords, dtype=np.float64)[:3]
            for part in shapely.get_parts(filled)
            if isinstance(part, shapely.Polygon) and not part.is_empty
            for triangle in shapely.get_parts(shapely.constrained_delaunay_triangles(part))
        ]
        stacked = np.stack(triangles) if triangles else np.zeros((0, 3, 2))
        return Glyph(stacked)

    def advance(self, char: str) -> float:
        name = self._cmap.get(ord(char))
        return float(self._glyphs[name].width) if name is not None else 0.25 * self.em

    def block(self, lines: list[str], line_gap_em: float) -> tuple[np.ndarray, np.ndarray]:
        """A legend's lines as triangles in font units, and the FRAME they are
        set in, `(x_low, y_low, x_high, y_high)`.

        🔴 **The frame is what TD's rectangle is, never the ink.** A drawing
        program files annotation as its text's box: the advances across, the
        line box (`hhea` ascent to descent) down. Measured on Wan Chai's
        `九龍 / 西 / 及 / 博覽道 / 東` column: `東` and `及` take identical
        1.34 x 2.82 m rectangles 1.9 m apart, so a rectangle is no character's
        ink, and ink stretched to fill one overlaps the next row by half.

        Line 1's baseline is at 0 and each line below it one line box plus
        `line_gap_em` lower; each line is centred on `x = 0` (the layer's
        `HorizontalAlignment` is 1, centre, on every feature).
        """
        pitch = self.ascent - self.descent + line_gap_em * self.em
        rows: list[np.ndarray] = []
        widest = 0.0
        for index, line in enumerate(lines):
            steps = [self.advance(char) for char in line]
            width = sum(steps)
            widest = max(widest, width)
            pen_x = -0.5 * width
            for char, step in zip(line, steps, strict=True):
                if not char.isspace():
                    glyph = self.glyph(char)
                    if len(glyph.triangles):
                        rows.append(glyph.triangles + np.array([pen_x, -index * pitch]))
                pen_x += step
        frame = np.array(
            [
                -0.5 * widest,
                -(len(lines) - 1) * pitch + self.descent,
                0.5 * widest,
                self.ascent,
            ]
        )
        return (np.concatenate(rows) if rows else np.zeros((0, 3, 2))), frame


def legend_lines(raw: object) -> list[str]:
    """A published `TextString` as the lines it paints: markup stripped, each
    line trimmed, blank lines dropped."""
    text = _MARKUP.sub("", "" if raw is None else str(raw))
    return [line.strip() for line in text.replace("\r\n", "\n").split("\n") if line.strip()]


# ---------------------------------------------------------------------------
# The read
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Legend:
    """One published legend in the game's `(x, z)` plan."""

    lines: tuple[str, ...]
    ring: np.ndarray  # the rectangle, (n, 2)
    baseline_deg: float  # TD's reading heading, right modulo 180
    deck: bool

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def middle(self) -> np.ndarray:
        return 0.5 * (self.ring.min(axis=0) + self.ring.max(axis=0))


def read_legends(
    city: Config,
    spec: RoadText,
    region_id: str,
    transform: GameTransform,
    region_high: tuple[float, float],
    face: Face,
    report: RoadTextReport,
    *,
    sources_root: Path | None = None,
) -> list[Legend]:
    """Every legend whose middle is in the region and which this face can draw."""
    layer = spec.layer
    legends: list[Legend] = []
    for path, member in source_reads(city, spec, region_id, root=sources_root):
        read = gdb.read_layer(
            path,
            layer.layer,
            columns=layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        texts = read.column(layer.field("text"))
        bearings = read.column(layer.field("bearing"))
        levels = read.column(layer.field("level"))
        owners, parts = gdb.polygons(read)
        rings: dict[int, list[np.ndarray]] = {}
        for owner, part in zip(owners, parts, strict=True):
            rings.setdefault(int(owner), []).append(np.asarray(part[0], dtype=np.float64)[:, :2])
        for owner in range(len(read.fids)):
            report.features += 1
            lines = legend_lines(texts[owner])
            level = "" if levels[owner] is None else str(levels[owner]).strip()
            bearing = _bearing(bearings[owner])
            outline = [ring for ring in rings.get(owner, []) if np.isfinite(ring).all()]
            if not lines:
                report.no_text += 1
                continue
            if "\n".join(lines) in spec.refused:
                report.refused += 1
                continue
            lacking = face.lacks("".join(lines))
            if lacking:
                report.glyph_missing += 1
                report.missing_characters |= lacking
                continue
            deck = level.upper() in spec.deck_codes
            if level.lower() not in AT_GRADE and not deck:
                report.on_structure += 1
                continue
            if not outline or bearing is None:
                report.empty_geometry += 1
                continue
            ring = _plan(transform, np.vstack(outline))
            legend = Legend(tuple(lines), ring, game_heading_deg(bearing), deck)
            x, z = legend.middle
            if not (0.0 <= x <= region_high[0] and 0.0 <= z <= region_high[1]):
                report.other_region += 1
                continue
            if deck:
                report.deck_candidates += 1
            else:
                report.candidates += 1
            legends.append(legend)
    return legends


# ---------------------------------------------------------------------------
# The draw
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Host:
    """The roads a legend may stand on: the street's, or the decks'."""

    segments: Segments
    one_way: dict[int, bool]
    drawn: dict[int, DrawnSurface]  # by the edge's elevation level
    level_of: dict[int, int]


def _host(edges: list[dict], drawn: dict[int, DrawnSurface]) -> Host | None:
    edges = [edge for edge in edges if int(edge["elevation_level"]) in drawn]
    if not edges:
        return None
    return Host(
        segments=Segments.of(edges),
        one_way={int(edge["id"]): str(edge["direction"]) != "both" for edge in edges},
        drawn=drawn,
        level_of={int(edge["id"]): int(edge["elevation_level"]) for edge in edges},
    )


def facing(legend: Legend, flow_deg: float) -> tuple[float, float]:
    """The heading the letters' tops point along, and TD's axis residual.

    Up is a quarter turn left of the reading heading; of its two senses the one
    with the traffic is taken, so a plan legend read upside down on the
    drawing is drawn the right way up for the driver."""
    up = (legend.baseline_deg - 90.0) % 360.0
    if directed_residual_deg(up, flow_deg) > 90.0:
        up = (up + 180.0) % 360.0
    return up, axis_residual_deg(up, flow_deg)


def laid(
    legend: Legend, up_deg: float, block: np.ndarray, frame_box: np.ndarray
) -> tuple[np.ndarray, float]:
    """The block's triangles, its frame stretched onto the legend's rectangle,
    in plan; and the ink's extent along the letters (their height on one line)."""
    along, across = frame(up_deg)
    centre = legend.middle
    local = legend.ring - centre
    u, v = local @ across, local @ along
    width, height = float(u.max() - u.min()), float(v.max() - v.min())
    middle = centre + 0.5 * (u.max() + u.min()) * across + 0.5 * (v.max() + v.min()) * along
    low, high = frame_box[:2], frame_box[2:]
    span = high - low
    scale = np.array([width / span[0] if span[0] else 0.0, height / span[1] if span[1] else 0.0])
    fitted = (block - 0.5 * (low + high)) * scale
    plan = middle + fitted[..., :1] * across + fitted[..., 1:] * along
    ink_m = float(np.ptp(fitted[..., 1])) if len(fitted) else 0.0
    return plan, ink_m


def draw(
    spec: RoadText,
    legends: list[Legend],
    face: Face,
    street: Host | None,
    decks: Host | None,
    report: RoadTextReport,
) -> tuple[CellBuilder, float]:
    """Every legend onto the drawn road. Apart from `build_region` so it can be
    driven without a geodatabase."""
    builder = CellBuilder(KIND, spec.cell_m)
    every = [legend.ring for legend in legends]
    report.import_quantum_m = round(import_quantum_m(np.vstack(every)), 6) if every else 0.0
    # 🔴 **`sliver_m`, never the other paint's twice-the-quantum.** A glyph's
    # triangulation is long thin triangles across its strokes, and a stroke of
    # a letter squeezed 0.4 m wide is ~5 cm: the 4.5 cm bar dropped 5,775 of Wan
    # Chai's 24,586 pieces, holes through the letters. With no bar at all,
    # `split` cuts slivers a few mm wide onto a cap's near-vertical facets at the
    # tunnel portal, and 74 triangles stand on edge (`check_faces_up`). 1.5 cm
    # clears them in both regions (1 cm left one) for 0.13% of the area.
    thinness_bar_m = spec.sliver_m

    for legend in legends:
        host = decks if legend.deck else street
        if host is None:
            report.no_deck_drawn += 1
            report.off_road += 1
            continue
        x, z = legend.middle
        snap = host.segments.nearest(float(x), float(z))
        report.nearest_edge_m.append(snap.distance_m)
        if snap.distance_m > spec.max_offset_m:
            report.too_far += 1
            continue
        flow = snap.heading_deg
        if not flows_along(snap.offset_m, host.one_way[snap.edge]):
            flow += 180.0
        up, residual = facing(legend, flow % 360.0)
        report.axis_residual_deg.append(residual)
        if residual > spec.bearing_tolerance_deg:
            report.off_axis += 1
            continue

        drawn = host.drawn[host.level_of[snap.edge]]
        triangles, height_m = laid(legend, up, *face.block(list(legend.lines), spec.line_gap_em))
        heights: list[float] = []
        for triangle in triangles:
            centre = triangle.mean(axis=0)
            if not drawn.covers(float(centre[0]), float(centre[1])):
                report.off_road_m2 += 0.5 * abs(twice_area(triangle))
                continue
            heights.extend(
                _place(builder, drawn, wound_up(triangle), spec.lift_m, report, thinness_bar_m)
            )
        if not heights:
            report.off_road += 1
            continue
        report.drawn += 1
        report.drawn_on_decks += int(legend.deck)
        report.characters_drawn += sum(not char.isspace() for line in legend.lines for char in line)
        report.drawn_by_text[legend.text] = report.drawn_by_text.get(legend.text, 0) + 1
        report.letter_height_m.append(height_m)
        report.height_spread_m.append(max(heights) - min(heights))

    assert len(legends) == report.drawn + report.too_far + report.off_axis + report.off_road
    return builder, thinness_bar_m


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> RoadTextReport:
    """Read the region's published road lettering and write `roadtext.glb`."""
    spec = city.road_text
    report = RoadTextReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no road_text block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    face = Face(
        cached_source(city, spec.font_source, root=sources_root),
        spec.font_weight,
        spec.flatten_em,
    )
    transform, region_high = city.game_transform(region_id), city.region_high(region_id)
    legends = read_legends(
        city, spec, region_id, transform, region_high, face, report, sources_root=sources_root
    )
    assert report.features == (
        report.no_text
        + report.refused
        + report.glyph_missing
        + report.on_structure
        + report.empty_geometry
        + report.other_region
        + report.candidates
        + report.deck_candidates
    )

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    # Level 0 only for the street, the restriction every snap makes (`Q15`).
    street = _host(graph["edges"], {0: DrawnSurface.of(surface, level=0)})
    decks = _host(graph["edges"], DrawnSurface.decks(surface))

    builder, thinness_bar_m = draw(spec, legends, face, street, decks, report)
    meshes = cell_meshes({KIND: builder}, thinness_bar_m, report, _stored_welded)
    if meshes:
        report.bytes = write_glb(out_dir / ROADTEXT_NAME, meshes)

    _write_manifest(out_dir, city, region_id, report)
    return report


def _stored_welded(mesh: MeshData) -> MeshData:
    """A letter's triangles each carry their own corners, which agree only to
    float64 round-off, so they are narrowed to the float32 `write_glb` stores
    first: the weld is then exact against the file."""
    return weld(replace(mesh, positions=mesh.positions.astype(np.float32).astype(np.float64)))


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: RoadTextReport) -> int:
    document = {
        "schema_version": ROADTEXT_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, as `stopmarks.json`'s is.
        "asset": ROADTEXT_NAME if report.triangles else None,
        # The read, as eight disjoint parts of `features`.
        "features": report.features,
        "no_text": report.no_text,
        "refused": report.refused,
        "glyph_missing": report.glyph_missing,
        "missing_characters": "".join(sorted(report.missing_characters)),
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "other_region": report.other_region,
        "candidates": report.candidates,
        "deck_candidates": report.deck_candidates,
        # The draw, as four disjoint parts of `candidates + deck_candidates`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        "off_axis": report.off_axis,
        "off_road": report.off_road,
        "drawn_on_decks": report.drawn_on_decks,
        "no_deck_drawn": report.no_deck_drawn,
        "characters_drawn": report.characters_drawn,
        "drawn_by_text": dict(sorted(report.drawn_by_text.items())),
        "axis_residual_deg": report.measured(report.axis_residual_deg),
        "nearest_edge_m": report.measured(report.nearest_edge_m),
        "letter_height_m": report.measured(report.letter_height_m),
        "off_road_m2": round(report.off_road_m2, 2),
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
    return write_document(out_dir / ROADTEXT_MANIFEST_NAME, document)


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
        "roadtext: %d features -> %d candidates + %d on decks -> %d drawn (%d on decks; "
        "%d too far, %d off axis, %d off the road), %d triangles",
        report.features,
        report.candidates,
        report.deck_candidates,
        report.drawn,
        report.drawn_on_decks,
        report.too_far,
        report.off_axis,
        report.off_road,
        report.triangles,
    )
    log.info(
        "  refused %d, glyph missing %d (%s), no text %d, on structure %d; "
        "axis residual %s deg; letters %s m",
        report.refused,
        report.glyph_missing,
        "".join(sorted(report.missing_characters)) or "none",
        report.no_text,
        report.on_structure,
        report.measured(report.axis_residual_deg),
        report.measured(report.letter_height_m),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
