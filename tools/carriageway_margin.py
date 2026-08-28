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

**And since `Q95` the far ray is read too, because TD published the bound it
was missing.** The Transport Planning & Design Manual Vol 2 Ch 3 says the widest
urban carriageway in Hong Kong is 13.5 m, 15.8 m on a tight curve and ~16.5 m
with a parking strip — so a two-sided ray above that has crossed a median, a
tram reserve or a junction mouth, which is a *citable* refusal rather than the
suspicion that kept the far side unread. The bounds live in the city file under
hard rule 3; the second city has its own manual.

🔴 **The ceiling is a plausibility bound and NOT a confound filter, and the
difference is most of the network.** 621 of the region's 737 level-0 edges are
one-way, and Hong Kong runs those as opposed pairs — so the centreline sits
inside one carriageway and the ray legitimately spans both. Two carriageways
summing to 13 m are a legal four-lane single carriageway and pass 16.5 m
cleanly. What separates them is `off_centre`, because the near ray is then short
and the far one long. ⚠️ **So the one-way number is reported as a kerb-to-kerb
span and never as a carriageway width**; the two coincide only on the 34
two-way edges.

⚠️ **The span is cap-sensitive where the overhang headline is not, so quote its
cap.** Measured over `--max-ray-m` 10 / 15 / 20 / 25: coverage 54.7 / 70.4 /
78.4 / 81.8%, and the non-junction p50 drifts 7.40 / 8.18 / 8.93 / 9.15 m.
✅ **The measurement saturates at the 15 m default** — kept spans peak there at
8,204 and *fall* to 8,162 by 25 m, published edges 343 → 336, because above the
default the extra stations are refusals. That is why there is one cap and not
two: a second flag would advertise a sensitivity the kept population does not
have, and casting a second pair of rays for the width would re-open the very
failure `_Index.cast_both` exists to close.

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

⚠️ **What the width half does NOT reproduce, and that is a finding rather than a
bar to tune.** `Q94` published three roads measured by a scratch script whose
commit touched only the docs. Walked here at its stated 4 m stations and 12 m
junction exclusion, the **p10 reproduces to 0.03 m on all three** — so the rays,
the walk and the exclusion are the same instrument — while `HENNESSY ROAD`
reproduces on every percentile (7.81 / 11.55 / 23.18 against 7.80 / 11.54 /
23.17) only at a ray cap of **25 m or more**, which its prose never states.
`STEWART ROAD` and `CANAL ROAD EAST` reproduce at no cap, and `STEWART ROAD` is
cap-*insensitive* — 22 stations reading 16.67 m from 15 m to 40 m. So the
record's stated method does not determine the record's numbers, which is the
argument for this code existing rather than a reason to make it agree.

Run:  .venv/bin/python tools/carriageway_margin.py --city hong_kong --region wan_chai
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from overhang import half_width_at, half_widths, left_of, walk_width  # noqa: E402
from pipeline import gdb  # noqa: E402
from pipeline.config import CarriagewayEdge, CityConfig, WidthBounds, load_city  # noqa: E402
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

    # ── the two-sided half (`Q95`), NaN and "" where no publisher spanned ──
    #
    # ⚠️ **`width_source` is not `source`.** The publisher that wins the near
    # side and the publisher that spans the road are different sets — the
    # drawings are the semantically better edge and are far too sparse to reach
    # across a street — so crediting a width to `source` would attribute most of
    # them to the wrong publisher.
    width_source: str = ""
    # The near and far ray of the *spanning* publisher, sorted, so the pair
    # carries no side convention. `left_of`'s sign is irrelevant to a sum.
    width_near_m: float = float("nan")
    width_far_m: float = float("nan")

    @property
    def width_m(self) -> float:
        return self.width_near_m + self.width_far_m

    @property
    def off_centre(self) -> float:
        """How far off the middle of its own span the centreline sits, 0 to 1.

        🔴 **The confounder detector, and the ceiling is not one.** 621 of the
        region's 737 level-0 edges are one-way, and Hong Kong runs those as
        opposed pairs — so the centreline sits *inside* one carriageway and the
        two-sided ray legitimately spans both plus whatever lies between. Two
        carriageways summing to 13 m are a legal four-lane single carriageway
        and pass `max_m` cleanly; what separates them is that the near ray is
        short and the far one long, which is this number.
        """
        width = self.width_m
        return abs(self.width_far_m - self.width_near_m) / width if width > 0 else float("nan")


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

    # ── the two-sided half (`Q95`) ────────────────────────────────────────
    #
    # Every station walked, whether or not anything answered. The width's own
    # denominator: `coverage` above is "one hit *either* side" and reads 92.3%,
    # where a width needs both and is far sparser. Reporting one as the other
    # would state a number for a measurement that was not made.
    stations_walked: int = 0
    # Stations no publisher spanned — zero rays or one, which are the same
    # answer here. Counted BESIDE the distribution and never appended to it: a
    # station with one ray has no width to record, and a placeholder would hold
    # the identity true by never reaching the list. `touchdown_error.py`'s
    # `ends_no_target` was found doing exactly that.
    width_no_span: int = 0
    # 🔴 Every candidate width, INCLUDING the ones the bounds refuse. Appended
    # above the guard, so `n` exceeds the keeps and a reader can tell. Recorded
    # below it, the distribution is confined to `max_m` by construction and
    # reports a clean sweep whatever the region does — `Q58`'s `drawn_gauge_m`
    # trap, which has since shipped in four other stages.
    widths: list[float] = field(default_factory=list)
    width_over_ceiling: int = 0
    width_under_hard_min: int = 0
    # How often each publisher spanned the road, against `segments` above.
    width_spanned_by: Counter[str] = field(default_factory=Counter)
    # Stations more than one publisher spanned, and by how much they differ.
    # ⚠️ Reported separately from `agreement` rather than folded into it: the
    # near-side cross-check is two orders of magnitude larger, and quoting one
    # for the other would be `Q57`'s own generalisation in a new place.
    width_agreement: list[float] = field(default_factory=list)
    # `roadgraph.json`'s own `direction`, for the split `off_centre` explains.
    directions: dict[int, str] = field(default_factory=dict)
    lanes: dict[int, int] = field(default_factory=dict)
    widths_authored: dict[int, float] = field(default_factory=dict)

    @property
    def width_measured(self) -> int:
        return len(self.widths)

    @property
    def width_kept(self) -> int:
        return self.width_measured - self.width_over_ceiling - self.width_under_hard_min

    @property
    def width_coverage(self) -> float:
        return self.width_measured / self.stations_walked if self.stations_walked else 0.0

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


def _sides(
    origin: np.ndarray,
    normal: np.ndarray,
    indexes: list[tuple[str, _Index]],
    max_ray_m: float,
) -> list[tuple[str, float | None, float | None]]:
    """Every publisher's two ray hits at one station, in preference order.

    🔴 **The only place `cast_both` is called per station**, and that is the
    point rather than tidiness. Both readings below — the near-side overhang and
    the two-sided width — consume this one list, so they cannot disagree about
    what was hit. Casting a second, independent pair for the width would re-open
    precisely the failure `cast_both`'s own docstring exists to close.

    A row per configured publisher, including ones that hit nothing, because the
    losers are the cross-check. Short-circuiting once one answers is the obvious
    optimisation and it would delete both the spread and the width's preference
    order in one move.
    """
    return [(name, *index.cast_both(origin, normal, max_ray_m)) for name, index in indexes]


def nearest_published(
    sides: list[tuple[str, float | None, float | None]],
) -> tuple[str, float, list[float]]:
    """The nearest published edge at one station, who published it, and the spread.

    `sides` is read as a preference order — the first publisher that answers
    wins — which is the rule the whole two-source design rests on, so it lives
    in one named function with a test on it rather than inline in the walk.
    Every publisher is still asked: the losers do not decide the measurement but
    they are the cross-check, and `Q57`'s argument for reading two sources is
    exactly that their disagreement is a finding.

    The nearer of a publisher's two rays wins, because the far one is what a
    junction mouth and a dual carriageway corrupt. `width_published` below is
    the reading that wants the far one, and it is a different question with a
    different preference order.

    Returns an empty name and a NaN distance when nobody answered.
    """
    chosen, nearest = "", float("nan")
    spread: list[float] = []
    for name, forward, backward in sides:
        hits = [hit for hit in (forward, backward) if hit is not None]
        if not hits:
            continue
        closest = min(hits)
        spread.append(closest)
        if not chosen:
            chosen, nearest = name, closest
    return chosen, nearest, spread


def width_published(
    sides: list[tuple[str, float | None, float | None]],
) -> tuple[str, float, float, list[float]]:
    """The first publisher that spans the road, and the two rays it spanned with.

    🔴 **Both rays must come from ONE publisher.** The drawings are TD's painted
    carriageway edge and iB1000's `RM` is LandsD's surveyed margin; summing one
    on the near side and the other on the far side adds a cartographic truth to
    a topographic one, and the two disagree by metres where both answer. The sum
    would still look like a road.

    ⚠️ **A different preference order than `nearest_published`'s**, on the same
    list. A publisher can answer the near side and not reach across the street —
    which is the drawings' normal case, being two orders of magnitude sparser —
    so it wins the overhang and loses the width. That is why the caller records
    `width_source` separately.

    Returns an empty name and NaN distances when nobody spanned. The name is the
    presence test; a NaN width summed into a distribution is not.
    """
    chosen, near, far = "", float("nan"), float("nan")
    spread: list[float] = []
    for name, forward, backward in sides:
        if forward is None or backward is None:
            continue
        spread.append(forward + backward)
        if not chosen:
            chosen, near, far = name, min(forward, backward), max(forward, backward)
    return chosen, near, far, spread


def survey(
    city: CityConfig,
    region_id: str,
    *,
    spacing_m: float,
    max_ray_m: float,
    junction_m: float,
    bounds: WidthBounds | None,
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
        report.directions[edge_id] = str(edge["direction"])
        report.lanes[edge_id] = int(edge["lanes"])
        report.widths_authored[edge_id] = float(edge["width_m"])
        edge_widths = widths.get(edge_id, [])

        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            if not normal.any():
                continue
            origin = station[[0, 2]]
            report.stations_walked += 1
            # One solve, two readings. See `_sides`.
            sides = _sides(origin, normal, indexes, max_ray_m)
            chosen, nearest, spread = nearest_published(sides)
            spanner, near, far, span_spread = width_published(sides)

            if spanner:
                # Appended ABOVE the bounds, so `n` exceeds the keeps. The
                # refusals are counted here and the value is kept: a
                # distribution recorded below its own guard cannot report the
                # thing the guard is for.
                report.widths.append(near + far)
                report.width_spanned_by[spanner] += 1
                if bounds is not None:
                    if near + far > bounds.max_m:
                        report.width_over_ceiling += 1
                    elif near + far < bounds.hard_min_m:
                        report.width_under_hard_min += 1
                if len(span_spread) > 1:
                    report.width_agreement.append(max(span_spread) - min(span_spread))
            else:
                report.width_no_span += 1

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
                    width_source=spanner,
                    width_near_m=near,
                    width_far_m=far,
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


def _share_under(values: list[float], threshold: float) -> float:
    return float(np.mean(np.asarray(values) < threshold)) if values else 0.0


@dataclass
class EdgeWidth:
    """One edge's measured span, and what it does and does not license."""

    edge: int
    median_m: float
    n: int
    # Share of this edge's stations the ceiling refuses. The column that tells a
    # reader which rows are escapes rather than roads.
    refused_share: float
    off_centre: float
    source: str
    refused: bool


def edge_widths(
    report: Report, bounds: WidthBounds | None, *, minimum_n: int = 3
) -> list[EdgeWidth]:
    """Per-edge span: the median FIRST, then the refusal.

    🔴 **Order matters, and the obvious order is the wrong one.** Refusing
    stations at `max_m` and then taking a median manufactures a median just
    under the ceiling for an edge most of whose stations escape through a
    junction mouth — a number that looks like a careful reading of a wide street
    and is an average of the crossings beside it. Taking the median over every
    two-sided station and refusing the *edge* on that median cannot do this, and
    it leaves `refused_share` to say how much of the edge was escaping.

    That also gives the `n` exceeds keeps tell at edge level: the edges that have
    a median outnumber the edges published.

    Junction stations are dropped, as everywhere else in this report — a station
    in a junction mouth has no far kerb to find, and it reads as a wide road.
    """
    per_edge: dict[int, list[Station]] = defaultdict(list)
    for station in report.stations:
        if not station.near_junction and station.width_source:
            per_edge[station.edge].append(station)

    rows: list[EdgeWidth] = []
    for edge_id, stations in per_edge.items():
        if len(stations) < minimum_n:
            continue
        widths = [s.width_m for s in stations]
        median = float(np.median(widths))
        answered: Counter[str] = Counter(s.width_source for s in stations)
        rows.append(
            EdgeWidth(
                edge=edge_id,
                median_m=median,
                n=len(stations),
                refused_share=(_share_over(widths, bounds.max_m) if bounds is not None else 0.0),
                off_centre=float(np.median([s.off_centre for s in stations])),
                source=answered.most_common(1)[0][0],
                refused=bounds is not None and not (bounds.hard_min_m <= median <= bounds.max_m),
            )
        )
    return sorted(rows, key=lambda row: -row.median_m)


def lane_bracket(width_m: float, bounds: WidthBounds, *, two_way: bool) -> tuple[int, int]:
    """How many through lanes a span could hold, as a range.

    🔴 **Never `width / lane_width_m`.** 3.2 m is the authored constant this
    whole question is about, and dividing by it would make the instrument agree
    with the value under test by construction — `Q72`'s tautology, one dimension
    over from the one it was written for. The divisor is TPDM 4.3.9.8's
    published through-lane range instead, so the answer is a bracket and its
    ambiguity is reported rather than resolved by fiat.

    On a two-way edge 3.4.2.7 removes the odd counts from the bracket — a
    two-way single carriageway may not be divided into three lanes, other than a
    climbing lane on a gradient. ⚠️ That narrows an *ambiguous* bracket only. A
    bracket that is unambiguously odd is left standing, because it is then a
    finding about the measurement or the direction field rather than a reading
    to be corrected into agreement.
    """
    low = int(width_m // bounds.lane_m[1])
    high = int(width_m // bounds.lane_m[0])
    if two_way and high > low:
        allowed = [n for n in range(low, high + 1) if not (n >= 3 and n % 2)]
        if allowed:
            return min(allowed), max(allowed)
    return low, high


def render(
    report: Report,
    *,
    spacing_m: float,
    max_ray_m: float,
    junction_m: float,
    bounds: WidthBounds | None = None,
) -> str:
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
    if bounds is not None:
        lines.extend(_render_width(report, bounds, max_ray_m=max_ray_m))
    return "\n".join(lines)


def _render_width(report: Report, bounds: WidthBounds, *, max_ray_m: float) -> list[str]:
    """The two-sided half (`Q95`), appended below the overhang report.

    Not behind a flag. CLAUDE.md already requires this tool's table pasted for a
    `lane_width_m` or `widen_default` change, and behind a flag the pasted table
    would silently omit the one section that grades exactly those values.
    """
    lines = ["", "measured span = BOTH published edges at one station, from ONE publisher"]
    lines.append(
        f"  {report.width_measured:,} of {report.stations_walked:,} stations were spanned "
        f"({report.width_coverage:.1%}, {max_ray_m:.1f} m ray), against "
        f"{report.measured:,} answered on the near side"
    )
    spanned = ", ".join(
        f"{name} {count:,}" for name, count in report.width_spanned_by.most_common()
    )
    lines.append(f"  spanned by: {spanned or 'nobody'}")
    if report.width_agreement:
        spread = _percentiles(report.width_agreement, (50, 90))
        lines.append(
            f"  both spanned {len(report.width_agreement):,} stations, disagreeing by p50 "
            f"{spread[0]:.2f} m, p90 {spread[1]:.2f} m — ⚠️ far fewer than the "
            f"{len(report.agreement):,} above, so the near side's cross-check does NOT carry over"
        )
    lines.append(
        f"  {report.width_no_span:,} stations no publisher spanned; partition "
        f"{report.width_measured:,} + {report.width_no_span:,} = {report.stations_walked:,}"
    )

    lines.append("")
    lines.append(
        f"station span, recorded over the REFUSALS too — n {report.width_measured:,} exceeds the "
        f"{report.width_kept:,} kept, and max must exceed {bounds.max_m:.1f} m"
    )
    lines.append(
        f"  {'population':<24} {'n':>7} {'p50':>7} {'p90':>7} {'max':>7} "
        f"{'> ' + format(bounds.max_m, '.1f'):>8} {'< ' + format(bounds.min_m, '.1f'):>8}"
    )
    spanning = [s for s in report.stations if s.width_source]
    away = [s for s in spanning if not s.near_junction]
    for label, population in (
        ("all spanned", spanning),
        ("  direction both", [s for s in spanning if report.directions.get(s.edge) == "both"]),
        (
            "  direction forward",
            [s for s in spanning if report.directions.get(s.edge) == "forward"],
        ),
        ("junctions dropped", away),
        ("junctions only", [s for s in spanning if s.near_junction]),
    ):
        values = [s.width_m for s in population]
        if not values:
            lines.append(f"  {label:<24} {0:>7}")
            continue
        p50, p90 = _percentiles(values, (50, 90))
        lines.append(
            f"  {label:<24} {len(values):>7,} {p50:>7.2f} {p90:>7.2f} {max(values):>7.2f} "
            f"{_share_over(values, bounds.max_m):>7.1%} {_share_under(values, bounds.min_m):>7.1%}"
        )
    lines.append(
        f"  refused: {report.width_over_ceiling:,} over {bounds.max_m:.1f} m, "
        f"{report.width_under_hard_min:,} under one through lane ({bounds.hard_min_m:.1f} m); "
        f"kept {report.width_kept:,}"
    )

    # 🔴 The confounder the ceiling cannot see. Kept its own table because the
    # one-way population is most of the network and its number is not a
    # carriageway width.
    lines.append("")
    lines.append(
        "off-centre = |near - far| / span; a centreline inside ONE carriageway of an opposed pair"
    )
    lines.append(f"  {'band':<12} {'n':>7} {'span p50':>9} {'> ' + format(bounds.max_m, '.1f'):>8}")
    for low, high in ((0.0, 0.10), (0.10, 0.25), (0.25, 0.50), (0.50, 1.01)):
        values = [s.width_m for s in away if low <= s.off_centre < high]
        if not values:
            lines.append(f"  {f'{low:.2f}-{high:.2f}':<12} {0:>7}")
            continue
        lines.append(
            f"  {f'{low:.2f}-{high:.2f}':<12} {len(values):>7,} "
            f"{_percentiles(values, (50,))[0]:>9.2f} {_share_over(values, bounds.max_m):>7.1%}"
        )

    rows = edge_widths(report, bounds)
    published = [row for row in rows if not row.refused]
    lines.append("")
    lines.append("per edge: median over non-junction spanned stations, n >= 3, THEN the refusal")
    lines.append(
        f"  {len(rows)} edges have a median; {len(rows) - len(published)} refused on it; "
        f"{len(published)} published"
    )
    for label, want in (
        ("two-way — a carriageway width", "both"),
        ("one-way — a KERB-TO-KERB SPAN", "forward"),
    ):
        values = [row.median_m for row in published if report.directions.get(row.edge) == want]
        if not values:
            continue
        p50, p90 = _percentiles(values, (50, 90))
        lines.append(f"  {label:<32} {len(values):>4} edges  p50 {p50:>6.2f}  p90 {p90:>6.2f}")
    if published:
        gaps = [row.median_m - report.widths_authored.get(row.edge, 0.0) for row in published]
        p10, p50, p90 = _percentiles(gaps, (10, 50, 90))
        lines.append(
            f"  measured - authored width_m: p10 {p10:+.2f}  p50 {p50:+.2f}  p90 {p90:+.2f}; "
            f"wider on {_share_over(gaps, 0.0):.0%}"
        )
        below = [row.median_m for row in published]
        lines.append(
            f"  below TD's {bounds.min_m:.1f} m two-lane minimum: "
            f"{round(_share_under(below, bounds.min_m) * len(below))} of {len(below)} — "
            "reported, never refused (3.4.2.2)"
        )

    lines.append("")
    lines.append(
        f"lanes = span / a TPDM through lane, {bounds.lane_m[0]:.2f}-{bounds.lane_m[1]:.2f} m "
        "(4.3.9.8) — never / lane_width_m"
    )
    outside = too_few = too_many = ambiguous = 0
    findings: list[tuple[int, float]] = []
    for row in published:
        two_way = report.directions.get(row.edge) == "both"
        low, high = lane_bracket(row.median_m, bounds, two_way=two_way)
        authored = report.lanes.get(row.edge, 0)
        if authored < low:
            outside, too_few = outside + 1, too_few + 1
        elif authored > high:
            outside, too_many = outside + 1, too_many + 1
        if high > low:
            ambiguous += 1
        elif two_way and low >= 3 and low % 2:
            findings.append((row.edge, row.median_m))
    lines.append(
        f"  the graph's lanes fall outside the bracket on {outside} of {len(published)} "
        f"({too_few} too few, {too_many} too many); ambiguous on {ambiguous}"
    )
    lines.append(f"  3.4.2.7 findings — two-way, unambiguously odd, >= 3 lanes: {len(findings)}")
    for edge_id, median in findings[:_WORST]:
        lines.append(f"    {edge_id:>6} {median:>7.2f} m  {report.names.get(edge_id, 'unnamed')}")

    lines.append("")
    lines.append(
        f"widest {_WORST} PUBLISHED edges by median span, junction stations dropped "
        f"({len(rows) - len(published)} refused rows not listed; they rank above every row here)"
    )
    lines.append(
        f"  {'edge':>6} {'n':>5} {'span':>7} {'refus':>6} {'offctr':>7} {'dir':<8} "
        f"{'source':<12} road"
    )
    # ⚠️ Published rows only. Ranked over everything, this listing is fifteen
    # escapes: a ray through a junction mouth is wider than any road, so the
    # refusals sweep the top and a reader never sees a street. `refused_share`
    # stays as a column because a kept edge can still be part escape.
    for row in published[:_WORST]:
        lines.append(
            f"  {row.edge:>6} {row.n:>5} {row.median_m:>7.2f} {row.refused_share:>5.0%} "
            f"{row.off_centre:>7.2f} {report.directions.get(row.edge, '?'):<8} "
            f"{row.source:<12} {report.names.get(row.edge, 'unnamed')}"
        )
    return lines


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
    parser.add_argument(
        "--max-width-m",
        type=float,
        # Defaults to the city's own `width_bounds.max_m`. A flag as well as a
        # config value because the counter has to be shown reachable at zero —
        # a ceiling nothing can move is not measuring anything (`Q72`).
        help="override the city's carriageway ceiling; above it a ray has crossed something",
    )
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_city(args.city)
    survey_spec = city.carriageway_survey
    bounds = survey_spec.width_bounds if survey_spec is not None else None
    if bounds is not None and args.max_width_m is not None:
        bounds = replace(bounds, max_m=args.max_width_m)
    if bounds is not None and 2.0 * args.max_ray_m <= bounds.max_m:
        # 🔴 The `drawn_gauge_m` trap, reachable from the command line. Two rays
        # capped at `max_ray_m` cannot sum past twice it, so a small enough cap
        # makes the ceiling unreachable and the report announces a clean sweep
        # that the cap manufactured rather than the city earned.
        raise SystemExit(
            f"--max-ray-m {args.max_ray_m:.1f} caps a span at {2 * args.max_ray_m:.1f} m, which "
            f"cannot reach the {bounds.max_m:.1f} m ceiling — every span would be kept by "
            "construction. Raise the ray or lower the ceiling."
        )
    report = survey(
        city,
        args.region,
        spacing_m=args.spacing_m,
        max_ray_m=args.max_ray_m,
        junction_m=args.junction_m,
        bounds=bounds,
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
            bounds=bounds,
        )
    )
    # Grades, never checks. See the docstring, and CLAUDE.md's rule for the
    # sibling this follows.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
