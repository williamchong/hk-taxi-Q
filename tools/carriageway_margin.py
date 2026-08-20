"""How far the drawn carriageway sits from the edge the city publishes (`Q57`, `Q19`).

`Q19` spent months recording that the carriageway width "no source publishes",
and `Q57` found it published twice over in files already on disk. What `Q57`
did not do is read them repeatably: its probe cast a perpendicular from each
centreline station to the first margin each side, and its own record says twice
that the number is not shippable — *"the perpendicular escapes through junction
mouths and crosses both halves of a dual carriageway, so it over-reads at the
top of the distribution. Anyone building on this owes a real cross-section, not
this number."* This is that cross-section.

**The headline is near-side overhang, not measured width**, and that is the
whole answer to the objection above:

    overhang_m = drawn half-width - distance to the nearest published edge

The far ray is exactly what a junction mouth and a dual carriageway corrupt —
it escapes across an open mouth, or crosses a median and lands on the far
kerb of the other carriageway. The near ray is short, and it lands on the kerb
the ribbon is actually about to cross. Dropping the far side removes the
confound rather than documenting it again, and it *raises* coverage, because a
station needs one hit instead of two. Both distances are still reported, so a
width is derivable; only the headline declines to depend on the weak half.

**Two publishers, and the second one is not belt-and-braces.** `Q57` traced four
wrong "no source publishes that" claims to a single mechanism: a fact measured
properly against one dataset, then generalised to the estate. An instrument that
read one margin layer and called the result "the width" would be that same step
in a new place. So `carriageway_survey.edges` is a list, the report says which
publisher answered each station, and where they disagree the disagreement is the
finding rather than an error in either.

| | Traffic Aids Drawings | iB1000 |
|---|---|---|
| Draws | TD's painted `RM1108`/`RM1109` edge | LandsD's surveyed `RM` margin |
| Truth | cartographic — what is painted | topographic — where the edge is |
| Grade | a relative-level code, domain undecoded | the `RMU` complement only |
| In region | 745 segments | 29,018 segments |

⚠️ **This grades rather than checks**, the rule CLAUDE.md already records for
`kerbside_source_audit.py`. It exits 0 whatever it finds. A widening gap is a
finding to go and look at, never a bar to retune against — and there is a
specific reason not to gate this one yet, recorded under "the open question".

⚠️ **It is not a fifth bundle grader.** `deck_error`, `overhang`,
`ground_clearance` and `carriageway_occupancy` take their truth from the shipped
bundle, so a pipeline that is confidently wrong is agreed with. This takes its
truth from outside, as `kerbside_source_audit.py` does — the difference from
that one is that it shares no code with what it grades, where the audit
deliberately runs the pipeline's own join. In exchange it inherits the
publishers' registration error and their 2D projection, which the four do not.

**The open question this was built to settle, and did not.** `Q19` finds that 12
of its 14 `BUILDING` failures are edges under 20 m, and `Q57` concludes the
building half fails *because* the width is invented. Measured, short edges are
the **least** overhung part of the network, not the most — and the reason turns
out to be that this method barely reaches them. Of the four `BUILDING` edges
`Q19` names, two return **no station at all** and two return **one**, whose
nearest published kerb is 8-10 m away on a 7-11 m street: a ray leaving through
the junction mouth and finding the far side of the crossing.

⚠️ **So read the coverage column before any figure beside it.** The network
answer is solid — 92.3% of level-0 stations, and the ribbon crosses the
published kerb at three quarters of them. The `Q19` answer is *absence of
evidence*, and the report is built to show that rather than to average it away:
`--junction-m` prints the same population junctions-in and junctions-out, and
below twice that radius an edge has no non-junction station at all, so the short
band empties outright and the tool says so in words. It is not a knob to turn
until the answer agrees with the record.

What this implies for the sequel is in `Q19`: a fix for the building half has to
work on stubs an 8 m ray cannot cross, which points at counting lanes *between*
two published edges (`Q57` follow-on 1) rather than casting to the nearest one.

Run:  .venv/bin/python tools/carriageway_margin.py --city hong_kong --region wan_chai
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from overhang import half_width_at, half_widths, left_of, walk_width  # noqa: E402
from pipeline import gdb  # noqa: E402
from pipeline.config import CarriagewayEdge, CityConfig, load_city  # noqa: E402
from pipeline.crs import GameTransform  # noqa: E402
from pipeline.export import read_manifest  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, plan_lengths, read_graph  # noqa: E402

log = logging.getLogger("carriageway_margin")

# Cell size of the segment index, in game metres. Only a lookup accelerator —
# it changes runtime and nothing reported, unlike the resolution constants in
# `clearance.py` that `Q51` found were deciding a published count.
_INDEX_CELL_M = 20.0

# Per-edge rows in the listing. `Q19` was corrected twice for reasoning about a
# population it could only see the top of, so this caps the *listing* only: every
# distribution above it is the whole population.
_WORST = 15

# Edge-length bands for the short-stub question. The middle bound is the graph's
# own median edge length as `Q19` publishes it, so the bands are the record's
# own split rather than a new one invented here.
_BANDS = ((0.0, 20.0, "< 20 m"), (20.0, 47.3, "20-47.3 m"), (47.3, float("inf"), ">= 47.3 m"))


@dataclass
class Station:
    """One measured cross-section of one edge."""

    edge: int
    # Distance to the nearest published edge on either side. The measurement;
    # `overhang_m` is it subtracted from the drawn half-width, kept beside it so
    # a reader can check one against the other without the ribbon in hand.
    nearest_m: float
    # Metres the drawn ribbon reaches past that edge. Negative means the ribbon
    # stops short of it, which is the normal, healthy case.
    overhang_m: float
    # Which `carriageway_survey.edges` entry answered.
    source: str
    # Whether the station sits within `--junction-m` of a graph node.
    near_junction: bool


@dataclass
class Report:
    stations: list[Station] = field(default_factory=list)
    # Stations walked but unmeasurable — no published edge either side within
    # the ray cap. Counted rather than dropped: coverage that silently falls is
    # indistinguishable from a city whose ribbon suddenly fits.
    unmeasured: int = 0
    # Level-0 edges considered, and those that got at least one reading.
    edges_walked: int = 0
    edges_measured: set[int] = field(default_factory=set)
    # Segments read per configured source, after code and grade filtering.
    segments: dict[str, int] = field(default_factory=dict)
    # Stations where more than one source answered, and the absolute spread
    # between their nearest-edge distances. This is the cross-check.
    agreement: list[float] = field(default_factory=list)
    # Per level-0 edge, its plan length and street name — report data rather
    # than extra return values, so `render` takes one argument.
    lengths: dict[int, float] = field(default_factory=dict)
    names: dict[int, str] = field(default_factory=dict)

    @property
    def measured(self) -> int:
        return len(self.stations)

    @property
    def coverage(self) -> float:
        walked = self.measured + self.unmeasured
        return self.measured / walked if walked else 0.0


def _segments(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A polyline's segments as start and end arrays, dropping zero-length ones.

    Zero-length segments are not hypothetical here: `Q57` records iB1000's
    transport lines arriving with repeated vertices, and a degenerate segment
    makes the ray/segment determinant vanish rather than miss.
    """
    if len(points) < 2:
        return np.empty((0, 2)), np.empty((0, 2))
    starts, ends = points[:-1], points[1:]
    keep = np.hypot(ends[:, 0] - starts[:, 0], ends[:, 1] - starts[:, 1]) > 1e-9
    return starts[keep], ends[keep]


class _Index:
    """Published-edge segments in game plan metres, bucketed for ray casting.

    A segment is filed under every cell its **bounding box** covers, and that is
    what makes the query exact without a neighbourhood halo: if a segment
    crosses the ray inside a cell then part of it lies in that cell, so its box
    covers that cell, so it is already in that bucket. Cell size is a lookup
    accelerator only — unlike the constants in `clearance.py`, which `Q51` found
    were deciding a published count, nothing reported here moves with it.
    """

    def __init__(self, starts: np.ndarray, ends: np.ndarray) -> None:
        self.starts = starts
        self.ends = ends
        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        low = np.floor_divide(np.minimum(starts, ends), _INDEX_CELL_M).astype(np.intp)
        high = np.floor_divide(np.maximum(starts, ends), _INDEX_CELL_M).astype(np.intp)
        for i in range(len(starts)):
            for cx in range(low[i, 0], high[i, 0] + 1):
                for cy in range(low[i, 1], high[i, 1] + 1):
                    buckets[(cx, cy)].append(i)
        # Packed once: the query concatenates whole buckets, and a list of
        # Python ints would be re-boxed into an array on every one of ~27k casts.
        self.cells = {cell: np.asarray(rows, dtype=np.intp) for cell, rows in buckets.items()}

    def cast_both(
        self, origin: np.ndarray, direction: np.ndarray, max_m: float
    ) -> tuple[float | None, float | None]:
        """Distance to the nearest segment each way along `direction`, or None.

        Both directions out of one solve: negating `direction` negates the
        determinant and `along` while leaving `across` untouched, so the
        backward ray is the same arithmetic read at negative `along`. That
        halves the work, and — the reason it is written this way rather than as
        two calls — it makes it impossible for the two sides of a station to be
        measured by subtly different code.

        Nearest rather than first-found: a bucket holds its segments in the
        order the sheets were read, so taking the first hit would make the
        answer depend on which of six map sheets happened to load first.
        """
        near, far = origin - direction * max_m, origin + direction * max_m
        low = np.floor_divide(np.minimum(near, far), _INDEX_CELL_M).astype(np.intp)
        high = np.floor_divide(np.maximum(near, far), _INDEX_CELL_M).astype(np.intp)
        chunks = [
            rows
            for cx in range(low[0], high[0] + 1)
            for cy in range(low[1], high[1] + 1)
            if (rows := self.cells.get((cx, cy))) is not None
        ]
        if not chunks:
            return None, None

        # A segment spanning several cells appears in several chunks. Left in:
        # a duplicate cannot change a minimum, and de-duplicating costs more
        # than the arithmetic it would save.
        rows = chunks[0] if len(chunks) == 1 else np.concatenate(chunks)
        start = self.starts[rows]
        edge = self.ends[rows] - start
        offset = start - origin
        denominator = direction[1] * edge[:, 0] - direction[0] * edge[:, 1]
        solvable = np.abs(denominator) >= 1e-12
        if not solvable.any():
            return None, None

        safe = np.where(solvable, denominator, 1.0)
        along = (offset[:, 1] * edge[:, 0] - offset[:, 0] * edge[:, 1]) / safe
        across = (direction[0] * offset[:, 1] - direction[1] * offset[:, 0]) / safe
        on_segment = solvable & (across >= -1e-9) & (across <= 1.0 + 1e-9)
        forward = on_segment & (along >= 0.0) & (along <= max_m)
        backward = on_segment & (along <= 0.0) & (along >= -max_m)
        return (
            float(along[forward].min()) if forward.any() else None,
            float(-along[backward].max()) if backward.any() else None,
        )

    def cast(self, origin: np.ndarray, direction: np.ndarray, max_m: float) -> float | None:
        """`cast_both`'s forward half, for a caller measuring one direction."""
        return self.cast_both(origin, direction, max_m)[0]


def published_edges(
    city: CityConfig,
    spec: CarriagewayEdge,
    region_id: str,
    transform: GameTransform,
    *,
    sources_root: Path | None,
) -> _Index:
    """One publisher's carriageway edge, in the region's game plan frame.

    Read into game space rather than leaving the graph in projected metres,
    because the graph's polylines are what the drawn ribbon is measured from and
    they are already here. `to_game` is used vectorised for the reason its
    docstring gives: the sign on Z is a consequence of Godot's handedness, and
    restating it is how it drifts.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    wanted = set(spec.codes)
    off_grade = set(spec.off_grade_codes)
    elevation_field = spec.elevation_field
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("edge_type"))
        # Grade, on whichever term the publisher offers, and both are
        # exclusions because at grade is the *unmarked* case in both files — a
        # null relative level in the drawings, a code absent from `codes` in
        # iB1000. See the city file for the measurement behind the drawing
        # codes; it is the opposite of the obvious reading.
        levels = layer.column(elevation_field) if elevation_field else None
        owners, parts = gdb.polylines(layer)
        for owner, points in zip(owners, parts, strict=True):
            if str(codes[owner]) not in wanted:
                continue
            if levels is not None and str(levels[owner]) in off_grade:
                continue
            projected = np.asarray(points, dtype=np.float64)
            game_x, _, game_z = transform.to_game(projected[:, 0], projected[:, 1])
            part_starts, part_ends = _segments(np.column_stack([game_x, game_z]))
            starts.append(part_starts)
            ends.append(part_ends)

    if not starts:
        return _Index(np.empty((0, 2)), np.empty((0, 2)))
    return _Index(np.vstack(starts), np.vstack(ends))


def nearest_published(
    origin: np.ndarray,
    normal: np.ndarray,
    indexes: list[tuple[str, _Index]],
    max_ray_m: float,
) -> tuple[str, float, list[float]]:
    """The nearest published edge at one station, who published it, and the spread.

    `indexes` is read as a preference order — the first publisher that answers
    wins — which is the rule the whole two-source design rests on, so it lives
    in one named function with a test on it rather than inline in the walk.
    Every publisher is still asked: the losers do not decide the measurement but
    they are the cross-check, and `Q57`'s argument for reading two sources is
    exactly that their disagreement is a finding.

    Returns an empty name and a NaN distance when nobody answered.
    """
    chosen, nearest = "", float("nan")
    spread: list[float] = []
    for name, index in indexes:
        hits = [hit for hit in index.cast_both(origin, normal, max_ray_m) if hit is not None]
        if not hits:
            continue
        closest = min(hits)
        spread.append(closest)
        if not chosen:
            chosen, nearest = name, closest
    return chosen, nearest, spread


def survey(
    city: CityConfig,
    region_id: str,
    *,
    spacing_m: float,
    max_ray_m: float,
    junction_m: float,
    sources_root: Path | None,
    out_root: Path | None,
) -> Report:
    """Walk every level-0 edge and measure it against each published source."""
    spec = city.carriageway_survey
    if spec is None:
        raise SystemExit(
            f"city '{city.id}' declares no carriageway_survey block, so there is no published "
            "edge to measure against. That is the honest answer, not a failure."
        )

    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    widths = half_widths(read_manifest(city, region_id, out_root=out_root))
    transform = city.game_transform(region_id)

    report = Report(names=road_names(graph))
    indexes: list[tuple[str, _Index]] = []
    for entry in spec.edges:
        index = published_edges(city, entry, region_id, transform, sources_root=sources_root)
        report.segments[entry.name] = len(index.starts)
        indexes.append((entry.name, index))

    nodes = np.asarray([node["pos"] for node in graph["nodes"]], dtype=np.float64)[:, [0, 2]]

    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        edge_id = int(edge["id"])
        report.edges_walked += 1
        report.lengths[edge_id] = float(plan_lengths(polyline)[-1])
        edge_widths = widths.get(edge_id, [])

        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            if not normal.any():
                continue
            origin = station[[0, 2]]
            chosen, nearest, spread = nearest_published(origin, normal, indexes, max_ray_m)
            if not chosen:
                report.unmeasured += 1
                continue
            if len(spread) > 1:
                report.agreement.append(max(spread) - min(spread))

            report.stations.append(
                Station(
                    edge=edge_id,
                    nearest_m=nearest,
                    overhang_m=half_width_at(edge_widths, vertex) - nearest,
                    source=chosen,
                    near_junction=bool(np.min(np.hypot(*(nodes - origin).T)) <= junction_m),
                )
            )
            report.edges_measured.add(edge_id)

    return report


def _percentiles(values: list[float], points: tuple[int, ...]) -> list[float]:
    if not values:
        return [float("nan")] * len(points)
    return [float(v) for v in np.percentile(np.asarray(values), points)]


def _share_over(values: list[float], threshold: float) -> float:
    return float(np.mean(np.asarray(values) > threshold)) if values else 0.0


def render(report: Report, *, spacing_m: float, max_ray_m: float, junction_m: float) -> str:
    lines: list[str] = []
    lines.append("published carriageway edge, segments read in region:")
    for name, count in report.segments.items():
        lines.append(f"  {name:<16} {count:>8,}")
    lines.append("")
    lines.append(
        f"  {report.measured:,} stations measured on {len(report.edges_measured)} of "
        f"{report.edges_walked} level-0 edges; {report.unmeasured:,} found no published edge "
        f"within {max_ray_m:.1f} m ({report.coverage:.1%} coverage, {spacing_m:.1f} m spacing)"
    )
    if report.agreement:
        spread = _percentiles(report.agreement, (50, 90))
        lines.append(
            f"  both sources answered {len(report.agreement):,} stations; "
            f"they disagree by p50 {spread[0]:.2f} m, p90 {spread[1]:.2f} m"
        )

    lines.append("")
    lines.append("overhang = drawn half-width - nearest published edge; positive crosses the kerb")
    lines.append(
        f"  {'population':<22} {'n':>8} {'p50':>8} {'p75':>8} {'p90':>8} {'> 0':>7} {'> 1 m':>7}"
    )
    away_stations = [s for s in report.stations if not s.near_junction]
    at_junction = [s for s in report.stations if s.near_junction]
    for label, population in (
        ("all stations", report.stations),
        (f"junctions dropped ({junction_m:.0f} m)", away_stations),
        ("junctions only", at_junction),
    ):
        values = [s.overhang_m for s in population]
        if not values:
            lines.append(f"  {label:<22} {0:>8}")
            continue
        p50, p75, p90 = _percentiles(values, (50, 75, 90))
        past = _share_over(values, 0.0)
        past_metre = _share_over(values, 1.0)
        lines.append(
            f"  {label:<22} {len(values):>8,} {p50:>8.2f} {p75:>8.2f} {p90:>8.2f} "
            f"{past:>6.1%} {past_metre:>6.1%}"
        )

    # The short-stub question, which is the reason this tool exists. Reported
    # twice over, because dropping junction stations does not isolate the
    # artefact on this population — it deletes it. See the note below the table.
    lines.append("")
    lines.append("by edge length — Q19's building half is 12 of 14 under 20 m:")
    lines.append(
        f"  {'band':<12} {'stations':>9} {'p50':>7} {'p90':>7} {'> 1 m':>7}   "
        f"{'no-jct n':>9} {'p50':>7} {'p90':>7} {'> 1 m':>7}"
    )
    everywhere: dict[int, list[float]] = defaultdict(list)
    away: dict[int, list[float]] = defaultdict(list)
    for station in report.stations:
        everywhere[station.edge].append(station.overhang_m)
        if not station.near_junction:
            away[station.edge].append(station.overhang_m)

    def _band(source: dict[int, list[float]], low: float, high: float) -> list[float]:
        return [
            value
            for edge_id, values in source.items()
            if low <= report.lengths.get(edge_id, 0.0) < high
            for value in values
        ]

    starved_band = False
    for low, high, label in _BANDS:
        row = f"  {label:<12}"
        for source in (everywhere, away):
            flat = _band(source, low, high)
            if not flat:
                starved_band = True
                row += f" {0:>9} {'-':>7} {'-':>7} {'-':>7}  "
                continue
            p50, p90 = _percentiles(flat, (50, 90))
            past_metre = _share_over(flat, 1.0)
            row += f" {len(flat):>9,} {p50:>7.2f} {p90:>7.2f} {past_metre:>6.1%}  "
        lines.append(row.rstrip())
    if starved_band:
        # Not a gap in the data. An edge shorter than twice `--junction-m` has
        # no station that is not junction-adjacent, so the exclusion empties
        # the band by construction — which is the answer to the question this
        # table was built to ask, rather than a failure to answer it.
        lines.append(
            f"  ⚠️ a band is empty on the right: below {2 * junction_m:.0f} m an edge has no "
            f"station further than {junction_m:.0f} m from a node, so 'short edge' and "
            "'junction' are the same population here and cannot be separated this way"
        )

    lines.append("")
    lines.append(f"worst {_WORST} edges by p90 overhang, junction stations dropped:")
    lines.append(
        f"  {'edge':>6} {'len m':>7} {'n':>5} {'p90':>7} {'worst':>7}  {'source':<12} road"
    )
    ranked = sorted(
        (
            (edge_id, _percentiles(values, (90,))[0], values)
            for edge_id, values in away.items()
            if len(values) >= 3
        ),
        key=lambda item: -item[1],
    )
    # The publisher that answered *most* of an edge's stations, not whichever
    # answered last: a preference-ordered fallback means one edge can be
    # answered by both, and naming the last would be a coin toss printed as a
    # fact.
    answered: dict[int, Counter[str]] = defaultdict(Counter)
    for station in report.stations:
        answered[station.edge][station.source] += 1
    for edge_id, p90, values in ranked[:_WORST]:
        source = answered[edge_id].most_common(1)[0][0]
        lines.append(
            f"  {edge_id:>6} {report.lengths.get(edge_id, 0.0):>7.1f} {len(values):>5} "
            f"{p90:>7.2f} {max(values):>7.2f}  {source:<12} "
            f"{report.names.get(edge_id, 'unnamed')}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--spacing-m", type=float, default=4.0, help="station spacing along an edge"
    )
    parser.add_argument(
        "--max-ray-m",
        type=float,
        default=15.0,
        # A cap rather than unbounded, because an uncapped perpendicular finds
        # *something* eventually and calls it a kerb. Swept in the report a
        # reader pastes, per `Q51`'s lesson about a headline that turns out to
        # be a function of one constant.
        help="how far a perpendicular may travel before the station is unmeasurable",
    )
    parser.add_argument(
        "--junction-m",
        type=float,
        default=12.0,
        help="stations this close to a graph node are reported separately (see the docstring)",
    )
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_city(args.city)
    report = survey(
        city,
        args.region,
        spacing_m=args.spacing_m,
        max_ray_m=args.max_ray_m,
        junction_m=args.junction_m,
        sources_root=args.sources_root,
        out_root=args.out_root,
    )
    if not report.stations:
        raise SystemExit(
            "no station could be measured — is the region built and are the sources fetched?"
        )
    print(
        render(
            report,
            spacing_m=args.spacing_m,
            max_ray_m=args.max_ray_m,
            junction_m=args.junction_m,
        )
    )
    # Grades, never checks. See the docstring, and CLAUDE.md's rule for the
    # sibling this follows.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
