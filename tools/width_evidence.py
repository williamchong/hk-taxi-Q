"""Read a carriageway width where the ray survey cannot (`Q127`).

The pipeline's survey (`pipeline/carriageway.py`, graded by
`tools/carriageway_margin.py`) licenses a width on 290 of Wan Chai's 734 level-0
edges. The other 444 carry `lanes x lane_width_m`, an invented 6.4 m, because the
survey refuses to read within 12 m of a node and needs three stations — so an
edge under about 34 m is never read at all. This tool asks whether anything else
the build already downloads can say how wide those streets are.

**Four readings, each from a different publisher's layer, and none a kerb ray:**

1. **Stop and give-way lines** (`RM1011`-`RM1013`). A stop line is painted
   across the whole approach, so its length is the approach's width — and it
   sits at the junction mouth, exactly where the survey gives up.
2. **Lane spacing.** Two painted lines abreast are one lane apart. Read off TD's
   lane lines (`carriageway_survey.lane_lines`) and, separately, off rows of
   turn arrows abreast. The only width reading in the estate that owes nothing
   to a kerb.
3. **HyD pavement area / length.** The carriageway polygons HyD maintains,
   rasterised in each edge's own corridor and divided by the length covered —
   no ray, no station count, so a 15 m link reads as well as a 150 m one.
4. **Bounds.** Building frontages and surveyed posts cannot give a width, but
   they can refuse one: a kerb lies between the centreline and a lamp post.

🔴 **Graded before it is counted.** Every reading is first compared against the
290 edges the survey already measured (`width_source` `two_way_span` or
`one_way_uncrossed`), and only then is its reach on the unmeasured edges
reported. A reading that cannot reproduce the widths the survey can see has no
business supplying the ones it cannot. ⚠️ **One table per reading and one-way
apart from two-way, never pooled** (`Q57`): a one-way edge in an opposed pair
and a two-way street are different measurements under one column name.

⚠️ **It grades rather than checks** and exits 0 whatever it finds. Nothing here
publishes a width; the synthesis at the bottom is the question the next change
has to answer, not an answer.

⚠️ **It reuses the pipeline's READERS, never its survey.** Running a stage's
reader against a question that stage does not ask is `kerbside_source_audit.py`'s
precedent; importing `pipeline.carriageway`'s measurement would make the
reference and the reading one instrument.

Run:  .venv/bin/python tools/width_evidence.py --region wan_chai
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cap_pavement import _Index as _Rings  # noqa: E402
from cap_pavement import carriageway_polygons  # noqa: E402
from carriageway_margin import (  # noqa: E402
    BASIS_DECOMPOSED,
    Openings,
    _away_from_junction,
    _Index,
    _percentiles,
    _segments,
    _share_over,
    edge_widths,
    mouth_noise,
    published_edges,
    survey,
)
from carriageway_occupancy import road_names  # noqa: E402
from overhang import left_of, walk_width  # noqa: E402
from pipeline.arrows import ArrowReport, read_symbols  # noqa: E402
from pipeline.config import BOTH, Config, WidthBounds, load_config  # noqa: E402
from pipeline.crs import GameTransform  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.lamps import LampReport, read_lamps  # noqa: E402
from pipeline.podiums import decode_blocks  # noqa: E402
from pipeline.polyline import Segments, axis_residual_deg, plan_lengths  # noqa: E402
from pipeline.railings import RailingReport, read_lines  # noqa: E402
from pipeline.roadmarks import Network, RoadMarkReport, _host, read_markings  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402
from pipeline.signs import _read_poles  # noqa: E402

# The survey's own licensed bases — the reference population every reading is
# graded against. `deck` is excluded: it is level 1, which no reading here walks.
MEASURED = ("two_way_span", "one_way_uncrossed")
AUTHORED = "authored"

# Edge-length bands for reach, matching `carriageway_margin._GAIN_BANDS` plus the
# open top, because the short end is the question.
LENGTH_BANDS = ((0.0, 10.0, "<=10"), (10.0, 20.0, "10-20"), (20.0, 30.0, "20-30"))

# Rasterisation of the HyD corridor. A resolution, not a bound: the reading is an
# area divided by a length, so a coarser cell moves the answer by a fraction of
# a cell and never refuses anything. Swept in `Q127`.
AREA_ALONG_M = 1.0
AREA_ACROSS_M = 0.25
# Covered length under which an area reading is not taken: one station's worth
# of the survey's own spacing, so no reading rests on less road than one
# station of the instrument it is graded against.
AREA_MIN_COVERED_M = 4.0

# Railing sample spacing. A railing is a line and a post is a point; sampling
# turns the one into the other at a pitch well under any carriageway width.
RAILING_SAMPLE_M = 1.0

# The short end of the reference: its own p10 is 41 m and its minimum 34.5 m on
# Wan Chai, so 60 m keeps enough edges to read a p90 while staying the shortest
# third of what the survey can see.
SHORT_REFERENCE_M = 60.0

# The readings allowed to CONFIRM a strip, keyed by the name `--voters` takes and
# valued by the method whose row they are. ⚠️ **The ray survey is deliberately
# absent and may never be added** — on a reference edge it IS the reference, and
# letting it vote read the combinations at 0.63 m by construction (`Q127`).
_VOTERS = {
    "borrow": "street borrow",
    "arrows": "arrow pitch x abreast",
    "stop_line": "stop line (one-way)",
}


# --------------------------------------------------------------------------
# The graph
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Edge:
    """One level-0 edge as the reference and the readings both need it."""

    id: int
    polyline: np.ndarray  # (n, 3) game xyz
    length_m: float
    width_m: float
    width_source: str
    two_way: bool
    lanes: int
    lanes_source: str
    speed_limit_kph: int
    name: str
    # Street identity for the borrow: the published name (both languages) and
    # the direction, so a two-way street never lends to a one-way carriageway.
    street: tuple[str, bool] | None
    # Whether the graph says a tram runs here. HyD draws a tram reserve as its own
    # polygon class, so the strip through the centreline stops at the rails.
    tram: bool = False
    # Share of 1 m samples along the edge within `DECK_REACH_M` of a level >= 1
    # centreline. A 2D publisher under a flyover draws the deck or nothing.
    under_deck_share: float = 0.0

    @property
    def measured(self) -> bool:
        return self.width_source in MEASURED

    @property
    def authored(self) -> bool:
        return self.width_source == AUTHORED


# How close in plan a level >= 1 centreline must pass to count a sample as under
# a deck: TPDM's one through lane (`width_bounds.hard_min_m`), restated because
# `level_zero` runs before the bounds are in hand and asserted equal in `main`.
DECK_REACH_M = 3.0


def level_zero(graph: dict[str, Any]) -> dict[int, Edge]:
    names = road_names(graph)
    decks = [edge for edge in graph["edges"] if int(edge["elevation_level"]) >= 1]
    overhead = Segments.of(decks) if decks else None
    edges: dict[int, Edge] = {}
    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        name = edge.get("road_name") or {}
        key = (
            f"{name.get('en') or ''}|{name.get('zh') or ''}"
            if isinstance(name, dict) and (name.get("en") or name.get("zh"))
            else None
        )
        two_way = str(edge["direction"]) == BOTH
        edge_id = int(edge["id"])
        share = 0.0
        if overhead is not None:
            samples = _resample(polyline[:, [0, 2]], 1.0)
            share = sum(
                1 for x, z in samples if overhead.nearest(x, z).distance_m <= DECK_REACH_M
            ) / len(samples)
        edges[edge_id] = Edge(
            id=edge_id,
            polyline=polyline,
            length_m=float(plan_lengths(polyline)[-1]),
            width_m=float(edge["width_m"]),
            width_source=str(edge.get("width_source", AUTHORED)),
            two_way=two_way,
            lanes=int(edge["lanes"]),
            lanes_source=str(edge.get("lanes_source", AUTHORED)),
            speed_limit_kph=int(edge["speed_limit_kph"]),
            name=names.get(edge_id, "unnamed"),
            street=(key, two_way) if key is not None else None,
            tram=bool(edge.get("tram_tracks", False)),
            under_deck_share=share,
        )
    return edges


def _level_zero_list(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]


def _stations(edge: Edge, spacing_m: float) -> Iterable[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """`(origin, tangent, left normal)` in plan, down one edge."""
    for vertex, station in walk_width(edge.polyline, spacing_m):
        along = (edge.polyline[vertex + 1] - edge.polyline[vertex])[[0, 2]]
        length = float(np.hypot(*along))
        if length <= 0.0:
            continue
        yield station[[0, 2]], along / length, left_of(along)


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------


@dataclass
class Grade:
    """One reading graded against the survey and counted on the rest."""

    label: str
    population: str
    # Signed `reading - reference`, one per reference edge the reading reached.
    errors: list[float] = field(default_factory=list)
    # Edge ids the reading reached that the survey left authored.
    reached: list[int] = field(default_factory=list)


def _pct(values: list[float], q: int) -> float:
    """One percentile, on the sibling grader's own arithmetic."""
    return _percentiles(values, (q,))[0]


def grade(
    label: str,
    estimates: dict[int, float],
    edges: dict[int, Edge],
    *,
    reference: Callable[[Edge], float] = lambda edge: edge.width_m,
) -> list[Grade]:
    """Split a reading by direction and grade each half against the survey."""
    grades = {
        False: Grade(label, "one-way"),
        True: Grade(label, "two-way"),
    }
    for edge_id, value in estimates.items():
        edge = edges.get(edge_id)
        if edge is None or math.isnan(value):
            continue
        target = grades[edge.two_way]
        if edge.measured:
            target.errors.append(value - reference(edge))
        elif edge.authored:
            target.reached.append(edge_id)
    return [grades[False], grades[True]]


def render_grades(grades: list[Grade], edges: dict[int, Edge]) -> list[str]:
    lines = [
        f"  {'reading':<30} {'dir':<8} {'ref n':>6} {'p50':>6} {'|p90|':>6} {'max':>6} "
        f"{'>0.5':>6} {'>1.0':>6}  {'authored':>8} "
        + " ".join(f"{label:>6}" for _, _, label in LENGTH_BANDS)
        + f" {'>30':>6}"
    ]
    for g in grades:
        absolute = [abs(e) for e in g.errors]
        bands = [
            sum(1 for e in g.reached if low < edges[e].length_m <= high)
            for low, high, _ in LENGTH_BANDS
        ]
        longer = sum(1 for e in g.reached if edges[e].length_m > LENGTH_BANDS[-1][1])
        if g.errors:
            stats = (
                f"{len(g.errors):>6} {_pct(g.errors, 50):>+6.2f} {_pct(absolute, 90):>6.2f} "
                f"{max(absolute):>6.2f} {_share_over(absolute, 0.5):>6.1%} "
                f"{_share_over(absolute, 1.0):>6.1%}"
            )
        else:
            stats = f"{0:>6} {'-':>6} {'-':>6} {'-':>6} {'-':>6} {'-':>6}"
        lines.append(
            f"  {g.label:<30} {g.population:<8} {stats}  {len(g.reached):>8} "
            + " ".join(f"{count:>6}" for count in bands)
            + f" {longer:>6}"
        )
    return lines


# --------------------------------------------------------------------------
# 1. Stop and give-way lines
# --------------------------------------------------------------------------


@dataclass
class StopLines:
    """Transverse marking lengths by host edge, and what the join refused."""

    lengths: dict[int, list[float]] = field(default_factory=lambda: defaultdict(list))
    read: int = 0
    no_host: int = 0
    off_axis: int = 0

    def one_way_estimate(self, edges: dict[int, Edge]) -> dict[int, float]:
        """The approach width IS the carriageway on a one-way host."""
        return {
            e: float(np.median(v))
            for e, v in self.lengths.items()
            if e in edges and not edges[e].two_way
        }

    def two_way_estimate(self, edges: dict[int, Edge], *, doubled: bool) -> dict[int, float]:
        """On a two-way host a stop line spans ONE approach: half, or doubled to a whole.

        ⚠️ The two are printed apart, never chosen between here: doubling assumes the
        centre line sits in the middle, which `Q126`'s split exists to deny.
        """
        factor = 2.0 if doubled else 1.0
        return {
            e: factor * float(np.median(v))
            for e, v in self.lengths.items()
            if e in edges and edges[e].two_way
        }

    def lower_bound(self) -> dict[int, float]:
        """No carriageway is narrower than the longest line painted across it."""
        return {e: max(v) for e, v in self.lengths.items()}


def read_stop_lines(
    city: Config,
    region_id: str,
    transform: GameTransform,
    graph: dict[str, Any],
    *,
    sources_root: Path | None,
) -> StopLines:
    """Every at-grade transverse marking, hosted by `roadmarks.py`'s own transverse pick.

    ⚠️ **The host is the stage's `_host`, deliberately**: a stop line sits at a
    junction mouth a metre off the major road's kerb, so proximity hands it the
    road it is parallel to on 43% of the layer (`Q69`). The drawn width that
    `Network` carries is passed empty, because nothing here may read the floor.
    """
    found = StopLines()
    spec = city.road_marks
    if spec is None:
        return found
    markings = read_markings(
        city,
        spec,
        region_id,
        transform,
        city.region_high(region_id),
        RoadMarkReport(),
        sources_root=sources_root,
    )
    network = Network.of(Segments.of(_level_zero_list(graph)), {})
    for marking in markings:
        if not marking.mark.transverse:
            continue
        found.read += 1
        host = _host(network, marking, spec)
        if host is None:
            found.no_host += 1
            continue
        if host.residual_deg > spec.bearing_tolerance_deg:
            found.off_axis += 1
            continue
        found.lengths[host.edge_id].append(marking.length_m)
    return found


# --------------------------------------------------------------------------
# 2a. Lane lines
# --------------------------------------------------------------------------


@dataclass
class LaneStation:
    pitch_m: float
    lanes: int
    outer_m: float  # outermost divider to outermost divider

    @property
    def width_m(self) -> float:
        return self.pitch_m * self.lanes


@dataclass
class LaneLines:
    stations: dict[int, list[LaneStation]] = field(default_factory=lambda: defaultdict(list))
    segments: int = 0
    walked: int = 0
    one_divider: int = 0
    chains_broken: int = 0

    def estimate(self, *, minimum_n: int = 2) -> dict[int, float]:
        return {
            e: float(np.median([s.width_m for s in v]))
            for e, v in self.stations.items()
            if len(v) >= minimum_n
        }

    def pitch(self, *, minimum_n: int = 2) -> dict[int, float]:
        return {
            e: float(np.median([s.pitch_m for s in v]))
            for e, v in self.stations.items()
            if len(v) >= minimum_n
        }

    def lanes(self, *, minimum_n: int = 2) -> dict[int, int]:
        return {
            e: Counter(s.lanes for s in v).most_common(1)[0][0]
            for e, v in self.stations.items()
            if len(v) >= minimum_n
        }

    def lower_bound(self) -> dict[int, float]:
        return {e: max(s.outer_m for s in v) for e, v in self.stations.items()}


def dividers(offsets: list[float], merge_m: float) -> list[float]:
    """Signed offsets of painted lines, a double line folded into one divider.

    ⚠️ **The merge bar is half TPDM's narrowest lane**, derived and not chosen:
    two hits closer than that cannot have a lane between them, so they are one
    marking drawn as two lines (`RM1001`'s pair is 0.1 m apart).
    """
    merged: list[list[float]] = []
    for offset in sorted(offsets):
        if merged and offset - merged[-1][-1] < merge_m:
            merged[-1].append(offset)
        else:
            merged.append([offset])
    return [float(np.mean(group)) for group in merged]


def chain_at_centre(lines: list[float], gap_m: float) -> tuple[list[float], bool]:
    """The run of dividers nearest the centreline, cut where a gap is two lanes wide.

    ⚠️ **The cut is TWICE TPDM's widest lane, derived**: a gap wider than two lanes
    between neighbouring dividers is a median, a tram reserve or an unpainted
    lane, and a pitch taken across it is not a lane. Returned with whether any
    cut happened, so a reader sees how often the chain was not the whole row.
    """
    if not lines:
        return [], False
    chains: list[list[float]] = [[lines[0]]]
    for previous, line in itertools.pairwise(lines):
        if line - previous > gap_m:
            chains.append([line])
        else:
            chains[-1].append(line)
    best = min(
        chains,
        key=lambda chain: (
            0.0 if chain[0] <= 0.0 <= chain[-1] else min(abs(chain[0]), abs(chain[-1]))
        ),
    )
    return best, len(chains) > 1


def read_lane_lines(
    city: Config,
    region_id: str,
    transform: GameTransform,
    edges: dict[int, Edge],
    bounds: WidthBounds,
    *,
    spacing_m: float,
    max_ray_m: float,
    sources_root: Path | None,
) -> LaneLines:
    found = LaneLines()
    survey_spec = city.carriageway_survey
    if survey_spec is None or not survey_spec.lane_lines:
        return found
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    for spec in survey_spec.lane_lines:
        index = published_edges(city, spec, region_id, transform, sources_root=sources_root)
        starts.append(index.starts)
        ends.append(index.ends)
    index = _Index(np.vstack(starts), np.vstack(ends))
    found.segments = len(index.starts)
    parallel = math.cos(math.radians(bounds.pair_bearing_tolerance_deg))
    merge_m = bounds.lane_m[0] / 2.0
    gap_m = 2.0 * bounds.lane_m[1]

    for edge in edges.values():
        for origin, tangent, normal in _stations(edge, spacing_m):
            found.walked += 1
            offsets: list[float] = []
            for distance, row in index.cast_all(origin, normal, max_ray_m):
                step = index.ends[row] - index.starts[row]
                length = float(np.hypot(*step))
                if length > 0.0 and abs(float(step @ tangent)) / length >= parallel:
                    offsets.append(distance)
            chain, broken = chain_at_centre(dividers(offsets, merge_m), gap_m)
            found.chains_broken += int(broken)
            if len(chain) == 1:
                found.one_divider += 1
            if len(chain) < 2:
                continue
            found.stations[edge.id].append(
                LaneStation(
                    pitch_m=float(np.median(np.diff(chain))),
                    lanes=len(chain) + 1,
                    outer_m=chain[-1] - chain[0],
                )
            )
    return found


# --------------------------------------------------------------------------
# 2b. Turn-arrow rows
# --------------------------------------------------------------------------


@dataclass
class ArrowRows:
    pitch: dict[int, float] = field(default_factory=dict)
    abreast: dict[int, int] = field(default_factory=dict)
    read: int = 0
    kept: int = 0

    def one_way_estimate(self, edges: dict[int, Edge]) -> dict[int, float]:
        """Pitch x arrows abreast, one-way only.

        ⚠️ **A lower bound in disguise**: a lane with no arrow painted in it is
        invisible here, so the count abreast can only under-read.
        """
        return {
            e: self.pitch[e] * self.abreast[e]
            for e in self.pitch
            if e in edges and not edges[e].two_way
        }


def runs(
    values: list[tuple[float, float]], bar: Callable[[float, float], float]
) -> list[list[tuple[float, float]]]:
    """Split sorted `(key, glyph length)` pairs where a gap reaches half a glyph.

    🔴 **A third copy of `arrows._runs` / `carriageway._runs`, and forced**: those
    are private to two stages that must not share a line (`Q94`), and this is
    their grader. Same bar — half the shorter glyph — for their reason.
    """
    ordered = sorted(values)
    if not ordered:
        return []
    out = [[ordered[0]]]
    for previous, value in itertools.pairwise(ordered):
        if value[0] - previous[0] >= bar(previous[1], value[1]):
            out.append([value])
        else:
            out[-1].append(value)
    return out


def read_arrow_rows(
    city: Config,
    region_id: str,
    transform: GameTransform,
    graph: dict[str, Any],
    edges: dict[int, Edge],
    *,
    sources_root: Path | None,
) -> ArrowRows:
    found = ArrowRows()
    spec = city.arrows
    if spec is None:
        return found
    symbols = read_symbols(
        city, spec, region_id, transform, ArrowReport(), sources_root=sources_root
    )
    segments = Segments.of(_level_zero_list(graph))
    laid: dict[int, list[tuple[float, float, float]]] = defaultdict(list)
    for symbol in symbols:
        found.read += 1
        snap = segments.nearest(symbol.x, symbol.z)
        if snap.distance_m > spec.max_offset_m:
            continue
        if axis_residual_deg(symbol.heading_deg, snap.heading_deg) > spec.bearing_tolerance_deg:
            continue
        edge = edges.get(snap.edge)
        if edge is None:
            continue
        found.kept += 1
        laid[snap.edge].append(
            (snap.t * edge.length_m, snap.offset_m, spec.glyphs[symbol.code].length_m)
        )

    half = lambda a, b: 0.5 * min(a, b)  # noqa: E731
    for edge_id, arrows in laid.items():
        pitches: list[float] = []
        widest = 0
        for row in runs([(along, length) for along, _, length in arrows], half):
            members = {(along, length) for along, length in row}
            across = [
                (offset, length) for along, offset, length in arrows if (along, length) in members
            ]
            lanes = runs(across, half)
            widest = max(widest, len(lanes))
            if len(lanes) >= 2:
                centres = [float(np.mean([offset for offset, _ in lane])) for lane in lanes]
                pitches.append(float(np.median(np.diff(centres))))
        if pitches:
            found.pitch[edge_id] = float(np.median(pitches))
            found.abreast[edge_id] = widest
    return found


# --------------------------------------------------------------------------
# 3. HyD area / length
# --------------------------------------------------------------------------


@dataclass
class Area:
    """Four readings off one raster, printed side by side and never chosen between here.

    - `width`: every owned cell over the length covered — the plain area / length.
    - `station`: the median over stations of that station's owned cells. A median
      because a junction flare at one end inflates a total and not a middle.
    - `run`: the median over stations of the CONTIGUOUS owned strip through the
      centreline — a service road or a lay-by beyond a kerb island is not counted.
    - `run_away`: `run` over stations clear of a side street's opening only, the
      opening read by `carriageway_margin.Openings` at R 0.
    """

    width: dict[int, float] = field(default_factory=dict)
    station: dict[int, float] = field(default_factory=dict)
    run: dict[int, float] = field(default_factory=dict)
    run_away: dict[int, float] = field(default_factory=dict)
    stations: int = 0
    stations_unsurveyed: int = 0
    rings: int = 0


def read_area(
    city: Config,
    region_id: str,
    edges: dict[int, Edge],
    *,
    max_ray_m: float,
    sources_root: Path | None,
    openings: Openings | None = None,
    continuation_deg: float = 30.0,
) -> Area:
    """Carriageway area in each edge's own corridor, over the length it covers.

    🔴 **A cell counts for the edge whose centreline is NEAREST it, and only where
    its foot falls inside that edge** — never past either end. That is what hands
    a cross street's asphalt to the cross street and a junction's to nobody,
    with no junction radius and no station count. ⚠️ Opposed carriageways split
    at their midline, so a one-way reading includes half of any PAVED median; a
    median island HyD codes as something other than carriageway is not counted.
    """
    found = Area()
    rings = carriageway_polygons(city, region_id, sources_root=sources_root)
    found.rings = len(rings)
    index = _Rings(rings)

    starts: list[np.ndarray] = []
    deltas: list[np.ndarray] = []
    owner: list[np.ndarray] = []
    first: list[np.ndarray] = []
    last: list[np.ndarray] = []
    for edge in edges.values():
        plan = edge.polyline[:, [0, 2]]
        step = np.diff(plan, axis=0)
        n = len(step)
        starts.append(plan[:-1])
        deltas.append(step)
        owner.append(np.full(n, edge.id))
        flags = np.zeros(n, dtype=bool)
        head = flags.copy()
        head[0] = True
        tail = flags.copy()
        tail[-1] = True
        first.append(head)
        last.append(tail)
    seg_start = np.vstack(starts)
    seg_delta = np.vstack(deltas)
    seg_owner = np.concatenate(owner)
    seg_first = np.concatenate(first)
    seg_last = np.concatenate(last)
    seg_low = np.minimum(seg_start, seg_start + seg_delta)
    seg_high = np.maximum(seg_start, seg_start + seg_delta)
    squared = (seg_delta**2).sum(axis=1)

    across = np.arange(-max_ray_m, max_ray_m + 1e-9, AREA_ACROSS_M)
    for edge in edges.values():
        frames = list(_stations(edge, AREA_ALONG_M))
        if not frames:
            continue
        origins = np.array([origin for origin, _, _ in frames])
        normals = np.array([normal for _, _, normal in frames])
        points = (origins[:, None, :] + across[None, :, None] * normals[:, None, :]).reshape(-1, 2)
        station_of = np.repeat(np.arange(len(frames)), len(across))
        found.stations += len(frames)
        inside = index.inside(points)
        surveyed = np.bincount(station_of[inside], minlength=len(frames)) > 0
        found.stations_unsurveyed += int((~surveyed).sum())
        if not inside.any():
            continue

        candidates = points[inside]
        stations_in = station_of[inside]
        kept = np.zeros(len(candidates), dtype=bool)
        for chunk in range(0, len(candidates), 4096):
            p = candidates[chunk : chunk + 4096]
            # ⚠️ **Narrowed to the CHUNK's own box, not the whole edge's.** The
            # true nearest segment to any of these points lies within the ray cap
            # of one of them, so it survives; `flatnonzero` keeps ascending order,
            # so `argmin`'s tie-break is the same one a whole-edge filter gives.
            near = np.flatnonzero(
                (
                    (seg_high >= p.min(axis=0) - max_ray_m) & (seg_low <= p.max(axis=0) + max_ray_m)
                ).all(axis=1)
            )
            start, delta, norm = seg_start[near], seg_delta[near], squared[near]
            offset = p[:, None, :] - start[None, :, :]
            raw = (offset * delta[None, :, :]).sum(axis=2) / np.where(norm > 0, norm, 1.0)
            u = np.clip(raw, 0.0, 1.0)
            foot = start[None, :, :] + u[:, :, None] * delta[None, :, :]
            distance = np.hypot(*(p[:, None, :] - foot).transpose(2, 0, 1))
            winner = distance.argmin(axis=1)
            rows = near[winner]
            chosen = raw[np.arange(len(p)), winner]
            mine = seg_owner[rows] == edge.id
            past = (seg_first[rows] & (chosen < 0.0)) | (seg_last[rows] & (chosen > 1.0))
            kept[chunk : chunk + 4096] = mine & ~past
        per_station = np.bincount(stations_in[kept], minlength=len(frames))
        covered = float((per_station > 0).sum()) * AREA_ALONG_M
        if covered < AREA_MIN_COVERED_M:
            continue
        area = float(per_station.sum()) * AREA_ALONG_M * AREA_ACROSS_M
        found.width[edge.id] = area / covered
        found.station[edge.id] = float(np.median(per_station[per_station > 0])) * AREA_ACROSS_M

        owned = np.zeros(len(points), dtype=bool)
        owned[np.flatnonzero(inside)[kept]] = True
        grid = owned.reshape(len(frames), len(across))
        runs_m = contiguous_run(grid, int(np.argmin(np.abs(across)))) * AREA_ACROSS_M
        if (runs_m > 0).sum() * AREA_ALONG_M >= AREA_MIN_COVERED_M:
            found.run[edge.id] = float(np.median(runs_m[runs_m > 0]))
        if openings is not None:
            # The openings are a property of the EDGE, so they are read once per
            # edge and the stations are measured against them, rather than
            # re-deriving every node's side streets at every metre.
            inside_mouth = np.zeros(len(origins), dtype=bool)
            for node, widest in openings.mouths(edge.id, continuation_deg):
                inside_mouth |= np.hypot(*(origins - node).T) < widest
            away = runs_m[~inside_mouth & (runs_m > 0)]
            if len(away) * AREA_ALONG_M >= AREA_MIN_COVERED_M:
                found.run_away[edge.id] = float(np.median(away))
    return found


def contiguous_run(grid: np.ndarray, centre: int) -> np.ndarray:
    """Per row, the length in cells of the unbroken True run through `centre`.

    Zero where the centre cell itself is False: a centreline standing on no
    carriageway has no strip to read, and borrowing the nearest one would read a
    neighbouring road.
    """
    right = np.cumprod(grid[:, centre:], axis=1).sum(axis=1)
    left = np.cumprod(grid[:, centre - 1 :: -1], axis=1).sum(axis=1) if centre > 0 else 0
    return np.where(grid[:, centre], right + left, 0)


# --------------------------------------------------------------------------
# 4. Bounds
# --------------------------------------------------------------------------


@dataclass
class Bounds:
    """Upper and lower limits per edge, per source, and how often each is wrong."""

    upper: dict[str, dict[int, float]] = field(default_factory=dict)
    lower: dict[str, dict[int, float]] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)


def _side_sum(
    points: list[tuple[float, float]], segments: Segments, reach_m: float
) -> dict[int, float]:
    """Per edge: nearest point on the left plus nearest on the right, where both exist.

    A kerb lies between the centreline and anything standing on the pavement, so
    the sum bounds the carriageway from above — wherever the centreline sits
    across it.
    """
    left: dict[int, float] = {}
    right: dict[int, float] = {}
    for x, z in points:
        snap = segments.nearest(x, z)
        if snap.distance_m > reach_m or not (0.0 < snap.t < 1.0):
            continue
        side = left if snap.offset_m > 0.0 else right
        side[snap.edge] = min(side.get(snap.edge, math.inf), abs(snap.offset_m))
    return {e: left[e] + right[e] for e in left if e in right}


def _resample(plan: np.ndarray, step_m: float) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in itertools.pairwise(plan):
        length = float(np.hypot(*(b - a)))
        count = max(int(length // step_m), 1)
        for i in range(count):
            p = a + (b - a) * (i / count)
            out.append((float(p[0]), float(p[1])))
    if len(plan):
        out.append((float(plan[-1][0]), float(plan[-1][1])))
    return out


def read_bounds(
    city: Config,
    region_id: str,
    transform: GameTransform,
    graph: dict[str, Any],
    edges: dict[int, Edge],
    stop_lines: StopLines,
    lane_lines: LaneLines,
    *,
    spacing_m: float,
    reach_m: float,
    sources_root: Path | None,
) -> Bounds:
    found = Bounds()
    segments = Segments.of(_level_zero_list(graph))

    # Buildings: frontage to frontage, towers and podiums only. ⚠️ `OS` and `TS`
    # blocks are left out — an overhead structure spans the road it is over, and
    # a frontage read off one is a width of zero.
    spec = city.podiums
    if spec is not None:
        wanted = {spec.code("tower"), spec.code("podium")}
        starts: list[np.ndarray] = []
        ends: list[np.ndarray] = []
        for block in decode_blocks(city, region_id, sources_root=sources_root):
            if block.kind not in wanted:
                continue
            for rings in block.parts:
                outer = np.asarray(rings[0], dtype=np.float64)
                x, _, z = transform.to_game(outer[:, 0], outer[:, 1])
                closed = np.column_stack([x, z])
                closed = np.vstack([closed, closed[:1]])
                s, e = _segments(closed)
                starts.append(s)
                ends.append(e)
        found.counts["building segments"] = sum(len(s) for s in starts)
        if starts:
            index = _Index(np.vstack(starts), np.vstack(ends))
            spans: dict[int, list[float]] = defaultdict(list)
            for edge in edges.values():
                for origin, _, normal in _stations(edge, spacing_m):
                    ahead, behind = index.cast_both(origin, normal, reach_m)
                    if ahead is not None and behind is not None:
                        spans[edge.id].append(ahead + behind)
            found.upper["buildings"] = {e: float(np.median(v)) for e, v in spans.items() if v}

    if city.lamps is not None:
        lamps = read_lamps(
            city, city.lamps, region_id, transform, LampReport(), sources_root=sources_root
        )
        found.counts["lamp posts"] = len(lamps)
        found.upper["lamp posts"] = _side_sum(
            [(lamp.x, lamp.z) for lamp in lamps], segments, reach_m
        )

    if city.signs is not None:
        poles: list[tuple[float, float]] = []
        bbox = city.projected_bounds(region_id).bbox
        for path, member in source_reads(city, city.signs, region_id, root=sources_root):
            for group in _read_poles(path, member, city, city.signs, bbox, transform).values():
                poles.extend(group)
        found.counts["sign poles"] = len(poles)
        found.upper["sign poles"] = _side_sum(poles, segments, reach_m)

    if city.railings is not None:
        samples: list[tuple[float, float]] = []
        for plan, _ in read_lines(
            city, city.railings, region_id, transform, RailingReport(), sources_root=sources_root
        ):
            samples.extend(_resample(np.asarray(plan, dtype=np.float64), RAILING_SAMPLE_M))
        found.counts["railing samples"] = len(samples)
        found.upper["railings"] = _side_sum(samples, segments, reach_m)

    found.lower["stop lines"] = stop_lines.lower_bound()
    found.lower["lane lines"] = lane_lines.lower_bound()
    return found


# The two kinds of limit, and the one place they differ.
UPPER = "upper"
LOWER = "lower"


def outside(width_m: float, limit_m: float, kind: str) -> bool:
    """Whether a width breaks this limit."""
    return width_m > limit_m if kind == UPPER else width_m < limit_m


def bound_wrong(limits: dict[int, float], edges: dict[int, Edge], kind: str) -> float:
    """Share of reference edges whose measured width falls outside this limit."""
    ref = [(e, v) for e, v in limits.items() if e in edges and edges[e].measured]
    if not ref:
        return 1.0
    return sum(1 for e, v in ref if outside(edges[e].width_m, v, kind)) / len(ref)


def render_bounds(found: Bounds, edges: dict[int, Edge], borrow: dict[int, float]) -> list[str]:
    lines = [
        f"  {'source':<14} {'kind':<6} {'ref n':>6} {'wrong':>6} {'margin p50':>10}   "
        f"{'authored n':>10} {'6.4/9.6 out':>11} {'borrow out':>10}"
    ]
    for kind, table in ((UPPER, found.upper), (LOWER, found.lower)):
        for source, limits in table.items():
            ref = [(e, v) for e, v in limits.items() if e in edges and edges[e].measured]
            margins = [
                (v - edges[e].width_m) if kind == UPPER else (edges[e].width_m - v) for e, v in ref
            ]
            authored = [(e, v) for e, v in limits.items() if e in edges and edges[e].authored]
            out = sum(1 for e, v in authored if outside(edges[e].width_m, v, kind))
            borrowed = [(e, v) for e, v in authored if e in borrow]
            borrow_out = sum(1 for e, v in borrowed if outside(borrow[e], v, kind))
            lines.append(
                f"  {source:<14} {kind:<6} {len(ref):>6} "
                f"{bound_wrong(limits, edges, kind) if ref else 0.0:>6.1%} "
                f"{_pct(margins, 50):>+10.2f}   {len(authored):>10} {out:>11} "
                f"{borrow_out:>4} of {len(borrowed):<4}"
            )
    return lines


# --------------------------------------------------------------------------
# Borrow and synthesis
# --------------------------------------------------------------------------


def street_borrow(edges: dict[int, Edge], *, leave_out: bool) -> dict[int, float]:
    """Median measured width of the same street name and direction.

    `leave_out=True` reads a measured edge from its street's OTHER measured
    edges — its grade. False reads every unmeasured edge from all of them.
    """
    by_street: dict[tuple[str, bool], list[tuple[int, float]]] = defaultdict(list)
    for edge in edges.values():
        if edge.measured and edge.street is not None:
            by_street[edge.street].append((edge.id, edge.width_m))
    out: dict[int, float] = {}
    for edge in edges.values():
        if edge.street is None or edge.street not in by_street:
            continue
        donors = [w for e, w in by_street[edge.street] if not (leave_out and e == edge.id)]
        if not donors or (not leave_out and edge.measured):
            continue
        out[edge.id] = float(np.median(donors))
    return out


@dataclass(frozen=True)
class Method:
    name: str
    estimates: dict[int, float]
    # Every edge the reading reached, measured ones included — what a combination
    # is built from, so a combination is graded exactly as a single reading is.
    values: dict[int, float]
    # Reference error of this method, pooled over both directions it reads — the
    # tolerance two methods are compared at, and the cascade's rank.
    p50: float
    p90_abs: float
    reference_n: int
    # The same error over the reference edges under `SHORT_REFERENCE_M` only.
    # 🔴 **The reference is long by construction** — the survey cannot read an
    # edge under ~34 m — while the unmeasured edges run p50 24 m, so the pooled
    # p90 describes a population the question is not about. This is the nearest
    # the survey can come to the short end, and it reads worse on every reading.
    short_p90_abs: float = float("nan")
    short_n: int = 0


def method(
    name: str,
    estimates: dict[int, float],
    edges: dict[int, Edge],
    grading: dict[int, float] | None = None,
) -> Method:
    source = estimates if grading is None else grading
    errors = [v - edges[e].width_m for e, v in source.items() if e in edges and edges[e].measured]
    short = [
        abs(v - edges[e].width_m)
        for e, v in source.items()
        if e in edges and edges[e].measured and edges[e].length_m < SHORT_REFERENCE_M
    ]
    return Method(
        name=name,
        estimates={e: v for e, v in estimates.items() if e in edges and edges[e].authored},
        values={**source, **estimates},
        p50=_pct(errors, 50),
        p90_abs=_pct([abs(x) for x in errors], 90),
        reference_n=len(errors),
        short_p90_abs=_pct(short, 90),
        short_n=len(short),
    )


def voter_suffix(voters: list[str]) -> str:
    """What a combination's row is called when fewer than every voter may confirm.

    ⚠️ **The roster goes in the row's own NAME.** These tables are pasted into
    `DECISIONS.md`, and "+ another within 1 m" is a different rule at two voters
    than at three — `Q128` measured it reading 0.95 m against 1.23. The full
    roster prints the label `Q127` published, so its tables still reproduce.
    """
    if len(voters) == len(_VOTERS):
        return ""
    return " [" + "+".join(voters) + "]"


def agreeing(
    primary: dict[int, float], others: list[dict[int, float]], tolerance_m: float
) -> dict[int, float]:
    """`primary` where at least one INDEPENDENT reading lands within `tolerance_m` of it."""
    return {
        e: v
        for e, v in primary.items()
        if any(e in other and abs(other[e] - v) <= tolerance_m for other in others)
    }


def consensus(readings: list[dict[int, float]], tolerance_m: float) -> dict[int, float]:
    """The median of the readings within `tolerance_m` of all readings' median, where two are.

    ⚠️ **Only independent readings may be passed** — the HyD variants are one
    publisher read four ways, and two of them agreeing is one reading agreeing
    with itself.
    """
    out: dict[int, float] = {}
    for e in {e for reading in readings for e in reading}:
        values = [reading[e] for reading in readings if e in reading]
        if len(values) < 2:
            continue
        middle = float(np.median(values))
        close = [v for v in values if abs(v - middle) <= tolerance_m]
        if len(close) >= 2:
            out[e] = float(np.median(close))
    return out


def render_synthesis(
    methods: list[Method],
    edges: dict[int, Edge],
    found_bounds: Bounds,
    *,
    minimum_reference_n: int,
    bound_wrong_max: float,
) -> list[str]:
    """Which readings, and which combination of them, reach the unmeasured edges best.

    🔴 **A cascade in order of reference accuracy, never a vote**: each unmeasured
    edge takes the most accurate reading that reaches it. Ranked by `|p90|`
    against the survey, so a reading earns its place by reproducing widths
    already known. A reading graded on fewer than `minimum_reference_n` edges is
    listed and never ranked — a p90 over a handful is not an accuracy.
    """
    authored = [e for e in edges.values() if e.authored]
    lines = [
        f"  unmeasured (authored) level-0 edges: {len(authored)}",
        "",
        "  single readings, ranked by reference |p90|",
        f"  {'reading':<30} {'ref n':>6} {'p50':>6} {'|p90|':>6} "
        f"{'<60m n':>6} {'|p90|':>6} {'reach':>6} {'share':>6} "
        f"{'<=10':>5} {'<=20':>5} {'bound conflict':>14}",
    ]
    # 🔴 **Only a bound the survey itself rarely contradicts may refuse anything.**
    # A limit wrong on the reference edges more often than `bound_wrong_max` is a
    # guess about where a kerb is, and counting conflicts against it grades a
    # reading by the bound's own error.
    upper = {
        k: v
        for k, v in found_bounds.upper.items()
        if bound_wrong(v, edges, UPPER) <= bound_wrong_max
    }
    lower = {
        k: v
        for k, v in found_bounds.lower.items()
        if bound_wrong(v, edges, LOWER) <= bound_wrong_max
    }
    lines.insert(
        1,
        f"  bound conflict counts only bounds wrong on <= {bound_wrong_max:.0%} of reference "
        f"edges: {', '.join([*upper, *lower]) or 'none'}",
    )

    def conflicts(assign: dict[int, float]) -> int:
        return sum(
            1
            for e, v in assign.items()
            if any(
                e in limits and outside(v, limits[e], kind)
                for kind, table in ((UPPER, upper), (LOWER, lower))
                for limits in table.values()
            )
        )

    ranked = sorted(
        (m for m in methods if m.reference_n >= minimum_reference_n),
        key=lambda m: m.p90_abs,
    )
    unranked = [m for m in methods if m.reference_n < minimum_reference_n]
    for m in [*ranked, *unranked]:
        reach = m.estimates
        short = sum(1 for e in reach if edges[e].length_m <= 10.0)
        short20 = sum(1 for e in reach if edges[e].length_m <= 20.0)
        flag = "" if m.reference_n >= minimum_reference_n else "  (unranked: ref n too small)"
        lines.append(
            f"  {m.name:<30} {m.reference_n:>6} {m.p50:>+6.2f} {m.p90_abs:>6.2f} "
            f"{m.short_n:>6} {m.short_p90_abs:>6.2f} {len(reach):>6} "
            f"{len(reach) / len(authored) if authored else 0.0:>6.1%} {short:>5} {short20:>5} "
            f"{conflicts(reach):>14}{flag}"
        )

    lines.append("")
    lines.append("  cascades: each edge takes the most accurate reading that reaches it")
    lines.append(
        f"  {'cascade':<58} {'reach':>6} {'share':>6} {'worst |p90|':>11} {'used |p90| p50':>14} "
        f"{'conflict':>8}"
    )
    for depth in range(1, len(ranked) + 1):
        chosen = ranked[:depth]
        assign: dict[int, float] = {}
        used: list[float] = []
        for edge in authored:
            for m in chosen:
                if edge.id in m.estimates:
                    assign[edge.id] = m.estimates[edge.id]
                    used.append(m.p90_abs)
                    break
        label = " > ".join(m.name for m in chosen)
        if len(label) > 58:
            label = "..." + label[-55:]
        share = len(assign) / len(authored) if authored else 0.0
        worst = max(m.p90_abs for m in chosen)
        lines.append(
            f"  {label:<58} {len(assign):>6} {share:>6.1%} {worst:>11.2f} "
            f"{_pct(used, 50):>14.2f} {conflicts(assign):>8}"
        )

    lines.append("")
    lines.append("  agreement where two readings reach one unmeasured edge (|a - b|)")
    lines.append(f"  {'pair':<48} {'n':>5} {'p50':>6} {'p90':>6} {'within both p90':>15}")
    for i, a in enumerate(ranked):
        for b in ranked[i + 1 :]:
            both = [e for e in a.estimates if e in b.estimates]
            if not both:
                continue
            gaps = [abs(a.estimates[e] - b.estimates[e]) for e in both]
            tol = max(a.p90_abs, b.p90_abs)
            lines.append(
                f"  {a.name + ' / ' + b.name:<48} {len(both):>5} {_pct(gaps, 50):>6.2f} "
                f"{_pct(gaps, 90):>6.2f} {sum(1 for g in gaps if g <= tol) / len(gaps):>15.1%}"
            )
    return lines


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--spacing-m", type=float, default=4.0, help="station spacing, as the survey"
    )
    parser.add_argument(
        "--max-ray-m",
        type=float,
        default=15.0,
        help="how far across a lane-line cast and an area corridor reach, as the survey's ray",
    )
    parser.add_argument(
        "--bound-reach-m",
        type=float,
        default=30.0,
        # A reach and not a bound: a limit exists only where BOTH sides find
        # something, so a longer reach admits more edges and never tightens one.
        help="how far from a centreline a building, post or railing may stand and still bound it",
    )
    parser.add_argument(
        "--minimum-reference-n",
        type=int,
        default=20,
        help="reference edges a reading needs before the synthesis ranks it",
    )
    parser.add_argument(
        "--agree-m",
        type=float,
        default=1.0,
        # Swept in `Q127`, never settled here: the combinations are graded at the
        # tolerance they are built at, so a looser one shows its own cost.
        help="how close two independent readings must land to count as agreeing",
    )
    parser.add_argument(
        "--bound-wrong-max",
        type=float,
        default=0.05,
        help="a bound wrong on more of the reference edges than this refuses nothing",
    )
    parser.add_argument(
        "--voters",
        default=",".join(_VOTERS),
        # 🔴 **Which readings may confirm is a question about the PIPELINE, not
        # about the data.** `arrows` imports `roads` imports `carriageway`, so a
        # width published by the survey stage can be confirmed only by a reading
        # that stage can reach: the arrow rows it already clusters for itself,
        # and the graph it already holds. The stop line needs `roadmarks._host`,
        # which is two imports the other way round. Grading the cascade without
        # it is what says whether the reachable voters are enough to build.
        help="which independent readings may confirm, comma-separated: " + ", ".join(_VOTERS),
    )
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    args = parser.parse_args(argv)
    voters = [name.strip() for name in args.voters.split(",") if name.strip()]
    unknown = [name for name in voters if name not in _VOTERS]
    if unknown or not voters:
        raise SystemExit(
            f"--voters {args.voters!r} names {unknown or 'nothing'}; pick from {', '.join(_VOTERS)}"
        )

    city = load_config()
    survey_spec = city.carriageway_survey
    if survey_spec is None or survey_spec.width_bounds is None:
        raise SystemExit(
            f"city '{city.id}' declares no carriageway_survey.width_bounds; there is no "
            "reference width and no lane bracket to read against."
        )
    bounds = survey_spec.width_bounds
    if not math.isclose(bounds.hard_min_m, DECK_REACH_M):
        raise SystemExit(
            f"DECK_REACH_M {DECK_REACH_M} restates width_bounds.hard_min_m "
            f"{bounds.hard_min_m}; move the two together"
        )
    out_dir = city.out_dir(args.region, args.out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, args.region)
    transform = city.game_transform(args.region)
    edges = level_zero(graph)
    measured = sum(1 for e in edges.values() if e.measured)
    authored = sum(1 for e in edges.values() if e.authored)
    print(
        f"level-0 edges {len(edges)}: {measured} measured by the survey (the reference), "
        f"{authored} authored (the question), {len(edges) - measured - authored} other"
    )

    # ── 1 ──
    stops = read_stop_lines(city, args.region, transform, graph, sources_root=args.sources_root)
    print("")
    print(
        f"1. STOP / GIVE-WAY LINE LENGTH — {stops.read} transverse parts, "
        f"{stops.no_host} no host in range, {stops.off_axis} off axis, "
        f"hosted on {len(stops.lengths)} edges"
    )
    stop_one = stops.one_way_estimate(edges)
    stop_half = stops.two_way_estimate(edges, doubled=False)
    stop_double = stops.two_way_estimate(edges, doubled=True)
    grades = [
        *grade("stop line (one-way host)", stop_one, edges)[:1],
        grade("stop line x2 (two-way host)", stop_double, edges)[1],
        grade(
            "stop line vs half (two-way)",
            stop_half,
            edges,
            reference=lambda edge: edge.width_m / 2.0,
        )[1],
    ]
    print("\n".join(render_grades(grades, edges)))

    # ── 2a ──
    lanes = read_lane_lines(
        city,
        args.region,
        transform,
        edges,
        bounds,
        spacing_m=args.spacing_m,
        max_ray_m=args.max_ray_m,
        sources_root=args.sources_root,
    )
    print("")
    print(
        f"2a. LANE-LINE SPACING — {lanes.segments:,} line segments; {lanes.walked:,} stations, "
        f"{sum(len(v) for v in lanes.stations.values()):,} with >= 2 dividers, "
        f"{lanes.one_divider:,} with one (no pitch), {lanes.chains_broken:,} chains cut at "
        f"{2.0 * bounds.lane_m[1]:.1f} m"
    )
    lane_width = lanes.estimate()
    print("\n".join(render_grades(grade("pitch x lanes seen", lane_width, edges), edges)))
    pitch = lanes.pitch()
    in_bracket = [p for e, p in pitch.items() if bounds.lane_m[0] <= p <= bounds.lane_m[1]]
    print(
        f"  pitch over {len(pitch)} edges: p10 {_pct(list(pitch.values()), 10):.2f} "
        f"p50 {_pct(list(pitch.values()), 50):.2f} p90 {_pct(list(pitch.values()), 90):.2f}; "
        f"inside TPDM {bounds.lane_m[0]:.2f}-{bounds.lane_m[1]:.2f} m on "
        f"{len(in_bracket)} ({len(in_bracket) / len(pitch) if pitch else 0.0:.0%})"
    )
    seen = lanes.lanes()
    graded_lanes = [
        (seen[e], edges[e].lanes)
        for e in seen
        if e in edges and edges[e].lanes_source in ("measured", "arrows")
    ]
    agree = sum(1 for a, b in graded_lanes if a == b)
    print(
        f"  lanes seen vs the graph's MEASURED lanes: {agree} of {len(graded_lanes)} agree"
        + (
            f"; seen more on {sum(1 for a, b in graded_lanes if a > b)}, "
            f"fewer on {sum(1 for a, b in graded_lanes if a < b)}"
            if graded_lanes
            else ""
        )
    )

    # ── 2b ──
    arrows = read_arrow_rows(
        city, args.region, transform, graph, edges, sources_root=args.sources_root
    )
    arrow_width = arrows.one_way_estimate(edges)
    print("")
    print(
        f"2b. TURN-ARROW ROWS — {arrows.read} symbols, {arrows.kept} hosted, "
        f"a pitch on {len(arrows.pitch)} edges"
    )
    print("\n".join(render_grades(grade("arrow pitch x abreast", arrow_width, edges)[:1], edges)))
    both = [e for e in arrows.pitch if e in pitch]
    if both:
        gaps = [abs(arrows.pitch[e] - pitch[e]) for e in both]
        print(
            f"  arrow pitch vs lane-line pitch on {len(both)} edges both reach: "
            f"|diff| p50 {_pct(gaps, 50):.2f} p90 {_pct(gaps, 90):.2f}"
        )

    # ── 3 ──
    area = read_area(
        city,
        args.region,
        edges,
        max_ray_m=args.max_ray_m,
        sources_root=args.sources_root,
        openings=Openings.of(graph),
        continuation_deg=bounds.pair_bearing_tolerance_deg,
    )
    print("")
    print(
        f"3. HYD AREA / LENGTH — {area.rings} carriageway polygons; {area.stations:,} stations at "
        f"{AREA_ALONG_M:.2f} x {AREA_ACROSS_M:.2f} m, {area.stations_unsurveyed:,} with no HyD "
        f"carriageway within {args.max_ray_m:.0f} m "
        f"({area.stations_unsurveyed / max(area.stations, 1):.1%}); "
        f"a reading on {len(area.width)} edges (covered >= {AREA_MIN_COVERED_M:.0f} m)"
    )
    print(
        "\n".join(
            render_grades(
                [
                    *grade("area / covered length", area.width, edges),
                    *grade("median station", area.station, edges),
                    *grade("median strip through centre", area.run, edges),
                    *grade("  … clear of openings", area.run_away, edges),
                ],
                edges,
            )
        )
    )

    # ── borrow ──
    borrow_grade = street_borrow(edges, leave_out=True)
    borrow = street_borrow(edges, leave_out=False)
    print("")
    print("S. STREET BORROW (median measured width of the same street and direction) — for scale")
    print(
        "\n".join(render_grades(grade("street borrow", {**borrow_grade, **borrow}, edges), edges))
    )

    # ── 4 ──
    found_bounds = read_bounds(
        city,
        args.region,
        transform,
        graph,
        edges,
        stops,
        lanes,
        spacing_m=args.spacing_m,
        reach_m=args.bound_reach_m,
        sources_root=args.sources_root,
    )
    print("")
    print(
        "4. BOUNDS — wrong = the survey's measured width falls outside the limit; "
        + ", ".join(f"{k} {v:,}" for k, v in found_bounds.counts.items())
    )
    print("\n".join(render_bounds(found_bounds, edges, borrow)))

    # ── A ── the survey itself, two agreeing stations (`Q126`, `Q127` Part A)
    report = survey(
        city,
        args.region,
        spacing_m=args.spacing_m,
        max_ray_m=args.max_ray_m,
        junction_m=12.0,
        sources_root=args.sources_root,
        out_root=args.out_root,
    )
    shipped = edge_widths(report, bounds)
    noise = _pct(mouth_noise(report, shipped), 90)
    two = edge_widths(report, bounds, minimum_n=2, keep=_away_from_junction, agree_m=noise)
    ray_two = {row.edge: row.carriageway_m(bounds) for row in two if row.basis(bounds)}
    ray_two_whole = {
        row.edge: row.carriageway_m(bounds)
        for row in two
        if row.basis(bounds) and row.basis(bounds) != BASIS_DECOMPOSED
    }

    print("")
    print(
        "5. SYNTHESIS — which reading, or which cascade of readings, covers the unmeasured "
        "edges best"
    )
    # The status quo, graded the same way: what every authored edge carries today,
    # re-derived for the measured ones from the city's own rule. This is the bar
    # every reading below has to beat before it is worth publishing.
    today = {
        e.id: city.roads.lanes_for(e.speed_limit_kph) * city.roads.lane_width_m
        for e in edges.values()
    }
    methods = [
        method("TODAY: lanes x lane_width_m", today, edges),
        # ⚠️ Graded against the instrument it IS — the pipeline's survey is a
        # second implementation of this one — so its reference p90 is agreement
        # between two copies and says nothing about the two-station edges it
        # adds. `Q126` is the evidence for those: no measured width moved.
        method("ray survey, 2 agreeing", ray_two_whole, edges, ray_two),
        method("stop line (one-way)", stop_one, edges),
        method("stop line x2 (two-way)", stop_double, edges),
        method("lane-line pitch x lanes", lane_width, edges),
        method("arrow pitch x abreast", arrow_width, edges),
        method("HyD area / length", area.width, edges),
        method("HyD median station", area.station, edges),
        method("HyD strip through centre", area.run, edges),
        method("HyD strip, clear of openings", area.run_away, edges),
        method("street borrow", borrow, edges, {**borrow_grade}),
    ]
    # ── combinations, graded exactly as the single readings are ──
    by_name = {m.name: m.values for m in methods}
    strip = by_name["HyD strip, clear of openings"]
    # 🔴 **The ray survey is NOT a second reading here, and letting it be one
    # certified the combinations.** On a reference edge it IS the reference, so
    # "agrees with another reading" becomes "agrees with the answer", and the
    # combination's reference p90 read 0.63 m for that reason alone. It stays a
    # single reading, ranked on its own row, and the cascade still reaches for it
    # first.
    independent = [by_name[_VOTERS[name]] for name in voters]
    who = voter_suffix(voters)
    clean_strip = {
        e: v for e, v in strip.items() if not edges[e].tram and edges[e].under_deck_share == 0.0
    }
    tol = args.agree_m
    methods += [
        method("HyD strip, no tram, no deck", clean_strip, edges),
        method(
            f"HyD strip + another within {tol:g} m{who}",
            agreeing(strip, independent, tol),
            edges,
        ),
        method(
            f"HyD clean strip + another {tol:g} m{who}",
            agreeing(clean_strip, independent, tol),
            edges,
        ),
        method(
            f"consensus of >= 2 within {tol:g} m{who}",
            consensus([strip, *independent], tol),
            edges,
        ),
        method(
            "street borrow, no tram, no deck",
            {
                e: v
                for e, v in by_name["street borrow"].items()
                if not edges[e].tram and edges[e].under_deck_share == 0.0
            },
            edges,
        ),
    ]
    print(
        "\n".join(
            render_synthesis(
                methods,
                edges,
                found_bounds,
                minimum_reference_n=args.minimum_reference_n,
                bound_wrong_max=args.bound_wrong_max,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
