"""A carriageway width read from HyD's pavement AREA, where no ray can reach.

`Q95`'s ray survey needs three stations — two that agree since `Q128` — clear of
a 12 m junction guard at 4 m spacing, so an edge under about 34 m is never read.
That is 429 of Wan Chai's 734 level-0 edges and 97 of Causeway Bay's 196 after
the two-station licence, and they are the *short* ones: p50 24 m against a
reference whose minimum is 34.5 m.

🔴 **This is the same publisher read a different way, not a new source.** HyD's
Pavement Polygon already arrives as `carriageway_survey.edges`' third spec
(`Q94`), where `_union_boundary` turns it into kerb segments for a ray to hit.
Here the polygons stay polygons: each edge's own corridor is rastered, every cell
is handed to the centreline NEAREST it, and the width is the unbroken owned run
through the centre column. No ray, no station count — so a 15 m link reads as
well as a 150 m one, which is exactly the population the survey cannot serve.

⚠️ **The reading alone is NOT published.** `Q127` measured it at |p90| 2.53 m
against the survey's own widths, and 4.69 m on the short edges that need it —
no better than the invented `lanes x lane_width_m` it would replace. What ships
is the reading CONFIRMED by an independent one within a metre (`carriageway`'s
`_confirm`), which reads 1.17 / 1.35 m. The strip is the candidate; the
confirmation is the licence.

⚠️ **A second implementation of `tools/width_evidence.read_area`, deliberately.**
The survey exists twice so that the tool can grade the stage without being the
stage, and this half of it is no different — `Q95` records why sharing a core to
save six hundred lines would retire the only independent check on the reading.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

import numpy as np

from pipeline import gdb
from pipeline.config import CARRIAGEWAY_AREA, CarriagewayEdge, Config
from pipeline.crs import GameTransform
from pipeline.fetch import source_reads
from pipeline.geometry import inside_polygon

log = logging.getLogger(__name__)

# How the corridor is rastered. ⚠️ **A resolution, not a bound**: the reading is a
# run of cells through the centre, so a coarser cell moves the answer by a
# fraction of a cell and refuses nothing. Both restate
# `tools/width_evidence`'s own values, because two readings quantised
# differently cannot be compared and comparison is the point of keeping the
# second one — the same rule `STATION_M` and `JUNCTION_M` carry.
ALONG_M = 1.0
ACROSS_M = 0.25
# Covered length under which no reading is taken: one station of the ray survey's
# own spacing, so nothing here rests on less road than one station of the
# instrument it is graded against.
MIN_COVERED_M = 4.0
# Plan cell of the ring index. A lookup accelerator and nothing else — a cell only
# ever gathers candidates, which are then tested exactly by `inside_polygon`.
_INDEX_CELL_M = 32.0
# Points tested against the segment table at once. Memory, not meaning.
_CHUNK = 4096


@dataclass
class AreaReport:
    """What the strip reading found, and what it refused."""

    # Outer rings read from the publisher, and edges the raster reached at all.
    rings: int = 0
    edges_walked: int = 0
    stations: int = 0
    # Stations whose whole transverse row lay outside every polygon. Not a
    # failure: HyD does not tile the whole region, and `Q104` records HKCEC
    # standing on no HyD carriageway at all.
    stations_unsurveyed: int = 0
    # Edges refused for too little covered length, and for having no station left
    # once the junction mouths were dropped. Two refusals, counted apart: the
    # first is a silent publisher and the second is a short edge that is all
    # junction, and they want different answers.
    edges_under_covered: int = 0
    edges_all_mouth: int = 0
    # The published candidate: the median over mid-block stations of the unbroken
    # owned run through the centreline.
    run_m: dict[int, float] = field(default_factory=dict)


# --------------------------------------------------------------------------
# The junction mouths, read off the graph
# --------------------------------------------------------------------------


@dataclass
class Openings:
    """Which side streets leave each node, and how wide their mouths are.

    🔴 **`Q127` REFUTED junction openings as a gate on the RAY SURVEY and this is
    not that rule.** There, admitting near-node stations moved widths the survey
    already had — LEIGHTON ROAD `e263` 10.57 → 15.34 m — because a re-admitted
    station casts across the mouth to the far kerb. Here the mouths only *drop*
    stations from a reading that is published nowhere the survey speaks, so it
    cannot move a measured width; `carriageway._confirm` asserts that rather than
    trusting it. The reading with mouths dropped is the one `Q127` ranked best of
    every single reading it graded.

    ⚠️ **A continuation is not a side street.** The graph inserts a node wherever
    a speed limit changes or a region is cut, so an edge running straight on (or
    straight back) through a node is this same road and opens no mouth. Without
    that test every such node would fence off its own street.
    """

    # Node plan position by id, and per node the arms leaving it as
    # `(edge id, unit heading away from the node, that edge's graph width)`.
    node_at: dict[int, np.ndarray] = field(default_factory=dict)
    arms: dict[int, list[tuple[int, np.ndarray, float]]] = field(default_factory=dict)
    ends: dict[int, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def of(cls, edges: Iterable) -> Openings:
        """Read every level-0 edge's two ends. Graph only — no source is opened."""
        found = cls()
        for edge in edges:
            if edge.elevation_level != 0:
                continue
            plan = np.asarray(edge.polyline, dtype=np.float64)[:, [0, 2]]
            if len(plan) < 2:
                continue
            found.ends[edge.id] = (edge.from_node, edge.to_node)
            for node, here, next_to in (
                (edge.from_node, plan[0], plan[1]),
                (edge.to_node, plan[-1], plan[-2]),
            ):
                away = next_to - here
                length = float(np.hypot(*away))
                if length <= 0.0:
                    continue
                found.node_at[node] = here
                found.arms.setdefault(node, []).append((edge.id, away / length, edge.width_m))
        return found

    def mouths(self, edge_id: int, continuation_deg: float) -> list[tuple[np.ndarray, float]]:
        """This edge's own two nodes, each with the half-width of its widest mouth.

        The half-width is the side street's *graph* `width_m` — authored or
        measured — and deliberately not the drawn ribbon: what is being asked is
        how far the junction's asphalt reaches, and the ribbon carries the
        playability floor.
        """
        ends = self.ends.get(edge_id)
        if ends is None:
            return []
        limit = float(np.cos(np.radians(continuation_deg)))
        out: list[tuple[np.ndarray, float]] = []
        for node in ends:
            mine = [heading for arm, heading, _ in self.arms.get(node, ()) if arm == edge_id]
            widest = 0.0
            for arm, heading, width in self.arms.get(node, ()):
                if arm == edge_id:
                    continue
                if any(abs(float(np.dot(heading, own))) > limit for own in mine):
                    # Straight on or straight back: the same road through a node
                    # the graph inserted, not a mouth.
                    continue
                widest = max(widest, width)
            if widest > 0.0:
                out.append((self.node_at[node], 0.5 * widest))
        return out


# --------------------------------------------------------------------------
# The polygons
# --------------------------------------------------------------------------


class _Rings:
    """Outer rings bucketed by plan cell, so a corridor asks only its neighbours."""

    def __init__(self, rings: list[np.ndarray]) -> None:
        self._rings = rings
        self._low = [ring.min(axis=0) for ring in rings]
        self._high = [ring.max(axis=0) for ring in rings]
        self._cells: dict[tuple[int, int], list[int]] = {}
        for key, (low, high) in enumerate(zip(self._low, self._high, strict=True)):
            for cell in self._cells_of(low, high):
                self._cells.setdefault(cell, []).append(key)

    @staticmethod
    def _cells_of(low: np.ndarray, high: np.ndarray) -> list[tuple[int, int]]:
        lo = np.floor(low / _INDEX_CELL_M).astype(int)
        hi = np.floor(high / _INDEX_CELL_M).astype(int)
        return [(x, z) for x in range(lo[0], hi[0] + 1) for z in range(lo[1], hi[1] + 1)]

    def inside(self, points: np.ndarray) -> np.ndarray:
        """Whether each plan point lies in some carriageway polygon."""
        covered = np.zeros(len(points), dtype=bool)
        if not len(points) or not self._rings:
            return covered
        low, high = points.min(axis=0), points.max(axis=0)
        keys = {
            cell_key for cell in self._cells_of(low, high) for cell_key in self._cells.get(cell, ())
        }
        for key in sorted(keys):
            if (self._low[key] > high).any() or (self._high[key] < low).any():
                continue
            # Clipped to the ring's own box before the exact test: a ring touching
            # one corner of a corridor is otherwise tested against every cell of
            # it, which is most of the pairs on this region.
            todo = ~covered & ((points >= self._low[key]) & (points <= self._high[key])).all(axis=1)
            if todo.any():
                covered[todo] = inside_polygon(points[todo], self._rings[key])
        return covered


def read_rings(
    city: Config,
    spec: CarriagewayEdge,
    region_id: str,
    transform: GameTransform,
) -> list[np.ndarray]:
    """One area publisher's carriageway polygons, in the graph's own frame.

    ⚠️ **OUTER rings only.** A hole in a pavement polygon is a traffic island or
    a planter, which a centreline does not run down, and treating it as
    not-carriageway would cut the strip at something the road goes around.
    `tools/width_evidence` reads them the same way, which is the other reason.

    ⚠️ **Both grade filters are EXCLUSIONS** — at grade is the unmarked case, so
    an inclusion filter keeps the flyovers and reports a plausible number
    (`Q57`). Restated here rather than shared with `_read_publisher`, which
    builds a boundary index from the same rows for a different question.
    """
    if spec.geometry != CARRIAGEWAY_AREA:
        return []
    wanted, off_grade = set(spec.codes), set(spec.off_grade_codes)
    elevation_field = spec.elevation_field
    bbox = city.read_box(region_id).bbox
    out: list[np.ndarray] = []
    for path, member in source_reads(
        city, spec, region_id, root=None, bounds=city.read_bounds(region_id)
    ):
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("edge_type"))
        levels = layer.column(elevation_field) if elevation_field else None
        owners, parts = gdb.polygons(layer)
        for owner, part in zip(owners, parts, strict=True):
            if str(codes[owner]) not in wanted:
                continue
            if levels is not None and str(levels[owner]) in off_grade:
                continue
            if not len(part):
                continue
            projected = np.asarray(part[0], dtype=np.float64)
            game_x, _, game_z = transform.to_game(projected[:, 0], projected[:, 1])
            ring = np.column_stack([game_x, game_z])
            if len(ring) >= 3:
                out.append(ring)
    return out


# --------------------------------------------------------------------------
# The reading
# --------------------------------------------------------------------------


def _segment_table(edges: list) -> tuple[np.ndarray, ...]:
    """Every level-0 segment in one table, with its owner and its two end flags.

    Ownership is decided against the WHOLE graph rather than against each edge in
    turn, which is what hands a cross street's asphalt to the cross street and a
    junction's to nobody — with no junction radius and no station count.
    """
    starts, deltas, owner, first, last = [], [], [], [], []
    for edge in edges:
        plan = np.asarray(edge.polyline, dtype=np.float64)[:, [0, 2]]
        step = np.diff(plan, axis=0)
        if not len(step):
            continue
        starts.append(plan[:-1])
        deltas.append(step)
        owner.append(np.full(len(step), edge.id))
        head = np.zeros(len(step), dtype=bool)
        head[0] = True
        tail = np.zeros(len(step), dtype=bool)
        tail[-1] = True
        first.append(head)
        last.append(tail)
    if not starts:
        empty = np.empty((0, 2))
        return empty, empty, np.empty(0, int), np.empty(0, bool), np.empty(0, bool)
    return (
        np.vstack(starts),
        np.vstack(deltas),
        np.concatenate(owner),
        np.concatenate(first),
        np.concatenate(last),
    )


def _stations(plan: np.ndarray, spacing_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Evenly spaced plan points down a polyline, with the left-of-travel normal.

    ⚠️ **Left of travel**, which is `surface.mitres`' frame and the opposite of
    `carriageway._stations`' right. It does not matter here — the corridor is
    symmetric about the centreline and the run is measured through it — and it is
    stated rather than left to be noticed, because `Q78` is what happens when a
    frame is assumed.
    """
    steps = np.diff(plan, axis=0)
    lengths = np.hypot(steps[:, 0], steps[:, 1])
    total = float(lengths.sum())
    if total <= 0.0:
        return np.empty((0, 2)), np.empty((0, 2))
    at = np.concatenate([[0.0], np.cumsum(lengths)])
    points, normals = [], []
    for along in np.arange(spacing_m * 0.5, total, spacing_m):
        index = min(max(int(np.searchsorted(at, along, side="right") - 1), 0), len(steps) - 1)
        if lengths[index] <= 0.0:
            continue
        unit = steps[index] / lengths[index]
        points.append(plan[index] + unit * (along - at[index]))
        normals.append(np.array([unit[1], -unit[0]]))
    if not points:
        return np.empty((0, 2)), np.empty((0, 2))
    return np.array(points), np.array(normals)


def contiguous_run(grid: np.ndarray, centre: int) -> np.ndarray:
    """Per row, the length in cells of the unbroken True run through `centre`.

    🔴 **Zero where the centre cell itself is False**, which is the whole
    difference between this and an area. A centreline standing on no carriageway
    has no strip to read, and taking the widest run in the row instead would
    read the service road beyond the kerb island, or the opposed carriageway.
    """
    right = np.cumprod(grid[:, centre:], axis=1).sum(axis=1)
    left = np.cumprod(grid[:, centre - 1 :: -1], axis=1).sum(axis=1) if centre > 0 else 0
    return np.where(grid[:, centre], right + left, 0)


def measure(
    city: Config,
    region_id: str,
    transform: GameTransform,
    edges: list,
    *,
    max_ray_m: float,
    continuation_deg: float,
) -> AreaReport:
    """The strip width through every level-0 centreline, mouths dropped."""
    report = AreaReport()
    survey = city.carriageway_survey
    if survey is None:
        return report
    rings: list[np.ndarray] = []
    for spec in survey.edges:
        rings.extend(read_rings(city, spec, region_id, transform))
    report.rings = len(rings)
    if not rings:
        return report

    level_zero = [
        edge
        for edge in edges
        if edge.elevation_level == 0 and len(edge.polyline) > 1 and edge.foreign is None
    ]
    report.edges_walked = len(level_zero)
    index = _Rings(rings)
    openings = Openings.of(level_zero)
    seg_start, seg_delta, seg_owner, seg_first, seg_last = _segment_table(level_zero)
    if not len(seg_start):
        return report
    seg_low = np.minimum(seg_start, seg_start + seg_delta)
    seg_high = np.maximum(seg_start, seg_start + seg_delta)
    squared = (seg_delta**2).sum(axis=1)
    across = np.arange(-max_ray_m, max_ray_m + 1e-9, ACROSS_M)
    centre_column = int(np.argmin(np.abs(across)))

    for edge in level_zero:
        plan = np.asarray(edge.polyline, dtype=np.float64)[:, [0, 2]]
        origins, normals = _stations(plan, ALONG_M)
        if not len(origins):
            continue
        report.stations += len(origins)
        points = (origins[:, None, :] + across[None, :, None] * normals[:, None, :]).reshape(-1, 2)
        station_of = np.repeat(np.arange(len(origins)), len(across))
        inside = index.inside(points)
        surveyed = np.bincount(station_of[inside], minlength=len(origins)) > 0
        report.stations_unsurveyed += int((~surveyed).sum())
        if not inside.any():
            continue

        candidates = points[inside]
        kept = np.zeros(len(candidates), dtype=bool)
        for chunk in range(0, len(candidates), _CHUNK):
            here = candidates[chunk : chunk + _CHUNK]
            # ⚠️ Narrowed to the CHUNK's own box, never the whole edge's. The true
            # nearest segment to any point here lies within the ray cap of one of
            # them, so it survives the filter; `flatnonzero` keeps ascending
            # order, so `argmin` breaks ties exactly as an unfiltered pass would.
            near = np.flatnonzero(
                (
                    (seg_high >= here.min(axis=0) - max_ray_m)
                    & (seg_low <= here.max(axis=0) + max_ray_m)
                ).all(axis=1)
            )
            if not len(near):
                continue
            start, delta, norm = seg_start[near], seg_delta[near], squared[near]
            offset = here[:, None, :] - start[None, :, :]
            raw = (offset * delta[None, :, :]).sum(axis=2) / np.where(norm > 0, norm, 1.0)
            foot = start[None, :, :] + np.clip(raw, 0.0, 1.0)[:, :, None] * delta[None, :, :]
            winner = np.hypot(*(here[:, None, :] - foot).transpose(2, 0, 1)).argmin(axis=1)
            rows = near[winner]
            chosen = raw[np.arange(len(here)), winner]
            # Mine, and the foot not past either end of me: a cell off the end of
            # an edge belongs to the junction and therefore to nobody.
            past = (seg_first[rows] & (chosen < 0.0)) | (seg_last[rows] & (chosen > 1.0))
            kept[chunk : chunk + _CHUNK] = (seg_owner[rows] == edge.id) & ~past

        owned = np.zeros(len(points), dtype=bool)
        owned[np.flatnonzero(inside)[kept]] = True
        runs_m = contiguous_run(owned.reshape(len(origins), len(across)), centre_column) * ACROSS_M
        if float((runs_m > 0).sum()) * ALONG_M < MIN_COVERED_M:
            report.edges_under_covered += 1
            continue
        in_mouth = np.zeros(len(origins), dtype=bool)
        for node, reach in openings.mouths(edge.id, continuation_deg):
            in_mouth |= np.hypot(*(origins - node).T) < reach
        away = runs_m[~in_mouth & (runs_m > 0)]
        if float(len(away)) * ALONG_M < MIN_COVERED_M:
            report.edges_all_mouth += 1
            continue
        report.run_m[edge.id] = float(np.median(away))
    return report
