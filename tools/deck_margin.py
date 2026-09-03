"""Where the drawn carriageway sits against the deck the model draws (`Q22`, `Q94`).

    .venv/bin/python tools/deck_margin.py

`tools/overhang.py` measures **how much** off-grade carriageway hangs past its
structure — **10.3%** as it prints today, after
`surface.floor_by_elevation_level` exempted level 1 from the widening and took
it from 20.1%. (`Q22` records 10.2% by hand and 10.0% from the tool; the figure
has drifted with the bundle and the instrument is the one to quote.)

It cannot say **why**, and `hong_kong.yaml` reads the residual as
unreachable: *"The remainder is a separate defect and no width rule reaches it —
Q22."*

This decomposes that same quantity into the two things that can cause it:

    span_m        the deck the model draws, parapet to parapet
    off_centre_m  signed offset of the published centreline from that deck's middle
    overhang_m    metres of drawn ribbon with no deck under them, per station

A ribbon can hang because it is **too wide** for the deck (`width_m`) or because
it is **registered wrong** (the centreline sits off the deck). Those need
opposite fixes and `overhang.py` reports one number for both.

⚠️ **Off-grade `width_m` stopped being `lanes x lane_width_m` at `Q103`** — it is
a reading of the deck itself where `width_source` says `deck`, so the `graph`
column below is the graph's *published* width whatever licensed it, and `lanes`
beside it is still authored up there. It was labelled `authored`, which was true
when this tool was written and is not now.

⚠️ **This is NOT an independent check of `overhang.py`.** Its truth side is the
same `INFRASTRUCTURE` class in the same shipped tiles, read through the same
`deck_error.Faces` index — so the two agree by construction and a divergence
would be a bug in one of them, not a finding. It is a decomposition, and it must
never be quoted as a second source in `kerbside_source_audit.py`'s sense.

⚠️ **The reference height is the station's own, NOT `deck_error.drawn_surface`,
and that is forced rather than chosen.** `overhang.py` takes the drawn road's
height at each cell first and then asks whether structure is under it — the
better rule, and it works there because it only ever samples *across the drawn
ribbon*. This walk deliberately runs past the ribbon's edge, which is where the
deck's own edge is and where the answer lives, and out there `drawn_surface`
returns nothing at all. So the two-step cannot reach the quantity this measures.
The predicate itself is `deck_error.nearest`, the repo's one selection rule,
against the station's height.

⚠️ **The truth side carries the 3D map's own registration error.** At grade,
`carriageway_margin.py` can read a carriageway edge two publishers *print*. No
publisher draws a viaduct deck edge, so up here the only thing that says where
the deck is is the model — which is also what `clearance.py` blocks against and
what the player sees. That makes it the right truth for "is the paint on the
deck", and the wrong truth for "is the centreline correct".

🔴 **`span_m` is bounded by `--max-lateral-m` BY CONSTRUCTION**, so it cannot
report a deck wider than the walk. That is `Q58`'s `drawn_gauge_m` trap, and it
is closed two ways: a run that reaches the limit is counted as `clipped` and
kept **out** of the span distribution rather than clamped into it, and the tool
refuses to start unless `2 x max_lateral_m` clears the widest ribbon it will
walk. Sweep the cap with `--sweep` and quote it, exactly as
`carriageway_margin.py` quotes its ray cap.

✅ **And as there, the overhang headline is cap-STABLE where the span is not**,
which is why there is one cap and not two. Measured over `--max-lateral-m` 8 /
10 / 12 / 16 at the default bridge: the hanging area fraction runs 11.8 / 11.1 /
10.4 / 11.0%, while the deck span's p50 drifts 7.30 / 7.40 / 7.60 / 7.95 and its
p90 balloons 9.70 / 12.40 / 15.00 / 16.90 as runs merge across a whole
interchange. **So quote the cap with a span and never with an overhang.** 12 m
is the knee: clipped stations fall 669 -> 390 up to it and the agreement with
`overhang.py` is closest there.

🔴 **`off_centre_m` is SIGNED and the frame is `overhang.left_of`** — positive is
left of travel, the `surface.mitres` convention, and never
`carriageway._stations`, which is the *opposite* normal. The frame is imported
rather than re-derived for that reason, and pinned by
`test_left_of_agrees_with_mitres` — which had to be written, because
`left_of`'s own docstring disclaimed its sign until this file became the first
consumer to depend on it. ⚠️ **There is exactly ONE negation, at the point of
publication**: the walk locates the deck in the centreline's frame, and what is
published is the centreline in the deck's, which is `centreline_error.py`'s
sense of a field of the same name and the sense in which the number is the
correction to apply. An absolute value here would inherit `Q78`'s defect, where
a registration that ran the wrong way survived three published distributions
because the counter could not report a direction.

⚠️ **Level -1 is excluded**, for `overhang.py`'s reason restated: a tunnel is a
void with nothing to stand on, so every station would read as hanging in air.
That is `Q21`'s question rather than this one. Level -1 had a widening bug of its
own — `floor_by_elevation_level` carried a key for 1 and none for -1, so 15
tunnels were drawn inside their own bores — and it was found and fixed by the
clearance walk in the same change, never by this tool (`Q103`).

⚠️ **Per station, never a per-edge median.** A viaduct widens along its length:
`e208` FLEMING ROAD spans 0.70 m to 8.10 m across its 27 kept stations against a
p50 of 6.60, so an edge-level median describes neither end of it. The per-edge
table below therefore carries `n` beside every figure, and the pooled
distributions are over stations rather than over edges.

⚠️ **It is slow on purpose and two speedups were measured and declined.** The
walk spends ~81% of its time in `deck_error.heights_at`, and batching those 241
per-station point queries by index cell was prototyped at **5.9 s → 0.24 s**,
bit-identical over every station. It is not taken: it adds a second query path
to a `Faces` class four other graders share, with no test behind it, to save six
seconds on a tool nobody runs in CI. `--sweep-bridge` likewise re-walks where
`bridge_m` touches nothing before `hits` is complete, and could cache one walk
per cap — same trade. Both stay available if this ever grows a real sweep grid;
neither is worth the surface area today.

⚠️ **`--probe-edges` prints one named edge station by station**, so the series
can be laid against `carriageway_occupancy.py`'s occupier walk of the same edge
and `Q103`'s remaining question answered: does the ribbon drift under a fixed
rim, or does a diagonal object move under a fixed ribbon? Those need opposite
fixes — a per-vertex `half_width_m` against `P4-1` geometry — and no column
published today separates them. 🔴 **The join is `along_m` and never the station
index**: the two walks run at different pitches (2.0 m here, 1.0 m there) and
neither pitch is constant, for the reason `along_metres` gives. ⚠️ **A refused
station prints its reason in place rather than being skipped**, because refusals
outnumber keeps here and a series printed from `Row`'s dense lists alone would
run smoothly across the hole that is the finding.

⚠️ **This grades rather than checks and exits 0 whatever it finds.** There is no
bar, deliberately, for `carriageway_margin.py`'s reason: the overhang it reports
is a cost this project has already decided to carry once (`Q22`), and a bar on it
would turn a recorded cost into a tuning target.
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import (  # noqa: E402
    SPACING_M as OCCUPANCY_SPACING_M,
)
from carriageway_occupancy import (  # noqa: E402
    edges_argument,
    edges_label,
    road_names,
)
from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    load_bundle,
    log_bundle,
    nearest,
    structure_faces,
)
from overhang import half_width_at, half_widths, left_of, walk_width  # noqa: E402
from pipeline.carriageway import (  # noqa: E402
    DECK_ACROSS_M,
    DECK_BRIDGE_M,
    DECK_MAX_LATERAL_M,
    JUNCTION_M,
    MIN_STATIONS,
)
from pipeline.config import load_config  # noqa: E402
from pipeline.polyline import plan_lengths  # noqa: E402

log = logging.getLogger(__name__)

# How far apart stations are walked down each centreline. 2.0 m is
# `overhang.py`'s own default and the two are meant to be comparable.
STATION_M = 2.0

# Lateral step of the cross-section walk. The deck edge is what is being found,
# so this is the resolution of every number here: a span is quantised to it and
# an overhang is quantised to it. 0.10 m keeps that below the 0.13 m parapets
# measured on CANAL ROAD FLYOVER without making a station cost more than a
# few hundred point queries.
ACROSS_M = DECK_ACROSS_M

# Half-width of the cross-section walk. 12 m reaches past the widest authored
# off-grade ribbon (9.60 m, so 4.80 m of half-width) with room for the deck to
# be wider than the paint, which is the common case.
MAX_LATERAL_M = DECK_MAX_LATERAL_M

# ⚠️ `JUNCTION_M`, `MIN_STATIONS` and the three walk constants below are
# imported from `pipeline.carriageway`, not restated. At a junction mouth the
# deck runs into the ramp it joins, so the
# contiguous run is the whole interchange rather than this edge's deck — the
# same reason `carriageway_margin.py` refuses there, and the two are *required*
# to agree for the populations to be comparable. Restating the numbers here
# would let them drift apart silently, which is what `centreline_error.py`
# already avoids by importing the same pair.

# How wide an interior hole in the deck may be before it stops being a hole and
# starts being a void between two decks. Sourced from the gap distribution's own
# bimodality rather than chosen — see `deck_run` for the numbers and `Q19` for
# why this estate has holes at all.
BRIDGE_M = DECK_BRIDGE_M


@dataclass(frozen=True)
class Station:
    """One walked station of a probed edge, kept **or** refused.

    🔴 **A refusal is a row here, not a gap.** `Row`'s lists are dense and carry
    no positional marker, so a series printed from them alone runs continuously
    across a hole — and refusals are the larger population on this tool, junction
    trims most of all. A probe that skipped them would draw a smooth drift
    through the very stations it could not read, which is the reading `Q103` came
    here to avoid making.

    ⚠️ **The DECK columns are NaN on a refusal, never 0.0** — `span_m`,
    `off_centre_m` and `overhang_m`. A zero span reads as a measured absence of
    deck; there is no measurement at all. ⚠️ `drawn_m` is the exception and is
    recorded on `no_deck` and `clipped`, because the ribbon's width is known at
    a station whose deck is not.
    """

    vertex: int
    along_m: float
    # "" when the station was kept; otherwise the `Refusals` field that took it.
    refused: str
    span_m: float
    off_centre_m: float
    overhang_m: float
    drawn_m: float
    # 🔴 **The column that separates a wide deck from two bridged ones.** A span
    # that widens under a drifting centreline reads as registration, and reads
    # exactly the same when `deck_run` has closed a hole between two decks and
    # published their combined extent — in which case the centreline may be
    # correctly on its own carriageway and the offset is against a middle that
    # is not a deck's. `bridge_m` is the dial, so the metres it closed belong
    # beside every span it closed them into.
    bridged_m: float
    centre_off_deck: bool


@dataclass
class Refusals:
    """Why a station published nothing. Counted, never silently dropped."""

    junction: int = 0
    no_ribbon: int = 0
    no_deck: int = 0
    clipped: int = 0

    @property
    def total(self) -> int:
        return self.junction + self.no_ribbon + self.no_deck + self.clipped


@dataclass
class Row:
    """One edge's stations, kept and refused."""

    edge: int
    # The graph's published `width_m`, whatever licensed it. ⚠️ Named for what it
    # is rather than where it came from: off-grade it is a deck reading since
    # `Q103`, and `authored_m` had become a lie.
    graph_m: float
    lanes: int
    lanes_source: str
    span_m: list[float] = field(default_factory=list)
    off_centre_m: list[float] = field(default_factory=list)
    overhang_m: list[float] = field(default_factory=list)
    drawn_m: list[float] = field(default_factory=list)
    bridged_m: list[float] = field(default_factory=list)
    refused: Refusals = field(default_factory=Refusals)
    # Stations whose centreline fell outside the deck run entirely. The
    # strongest single reading here: the paint is not merely wider than the
    # deck, its middle is off it.
    centre_off_deck: int = 0


def percentiles(values: list[float]) -> tuple[float, float, float, float]:
    """p50, p90, p99 and max, of a MAGNITUDE.

    The house four points, restated by hand rather than imported, which is this
    repo's convention — see `centreline_error.percentiles` for why one shared
    function would be the wrong answer to two definitions.
    """
    if not values:
        return (0.0, 0.0, 0.0, 0.0)
    points = np.percentile(np.asarray(values, dtype=np.float64), (50, 90, 99, 100))
    return (float(points[0]), float(points[1]), float(points[2]), float(points[3]))


def signed_percentiles(values: list[float]) -> tuple[float, float, float, float, float]:
    """p1, p10, p50, p90 and p99 of a SIGNED distribution.

    🔴 **Beside the magnitude convention, never instead of it.** `off_centre_m`
    and `drawn - deck` are two-sided: a population half at +2 m and half at -2 m
    has a median near zero and a maximum of 2, which reads as a centred
    centreline with one outlier. That is `Q78` at population scale, and it is
    why running a signed column through the four-point magnitude table — which
    an earlier draft of this file did — publishes a distribution that cannot
    report the direction of what it measures.
    """
    if not values:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    points = np.percentile(np.asarray(values, dtype=np.float64), (1, 10, 50, 90, 99))
    return tuple(float(value) for value in points)  # type: ignore[return-value]


def sides(values: list[float]) -> tuple[int, int, int]:
    """How many offsets fall left of travel, right of it, and exactly on it.

    The counts are what say a population has two sides; a median cannot. Zero is
    its own column rather than folded into either side, on `Q19`'s precedent.
    """
    left = sum(1 for value in values if value > 0.0)
    right = sum(1 for value in values if value < 0.0)
    return (left, right, len(values) - left - right)


def deck_run(
    structure: Faces,
    station: np.ndarray,
    normal: np.ndarray,
    *,
    max_lateral_m: float,
    across_m: float,
    attribute_within_m: float,
    bridge_m: float,
) -> tuple[float, float, bool, float] | None:
    """The deck's lateral extent at this station, and whether the walk clipped it.

    Returns `(left_m, right_m, clipped, bridged_m)` in the `left_of` frame, or
    `None` where no structure carries this station's height anywhere across the
    walk.

    The run kept is the one **nearest the centreline**, not the widest and not
    the one containing zero: a badly registered edge has its centreline off the
    deck altogether, and refusing those would drop exactly the stations worth
    reporting. `centre_off_deck` counts them instead.

    🔴 **Interior gaps up to `bridge_m` are closed first, and that is not
    tidying — without it the measurement is a hole detector.** `Q19` measured
    this estate as **not watertight**: 5.38% of edge slots open across the source
    `INFRASTRUCTURE` meshes and 14-26% in the decimated tiles this reads. So a
    contiguous run of "structure at ribbon height" terminates at the first hole,
    and 921 of 1,948 stations read two or more runs. The gap distribution is
    **bimodal and that is where the default comes from, rather than from
    caution**: p50 0.40 m with 760 of 1,064 under 0.5 m, then a separate tail at
    p90 3.37 m. The first cluster is holes, the second is real voids between two
    decks. 1.0 m sits in the gap between them and closes 822 of 1,064.
    ⚠️ **The metres closed are returned and reported**, on `railings.py`'s
    `metres_bridged` precedent: a jump in them is the bridge reaching further,
    not more deck. Sweep it with `--sweep-bridge` and quote what it does.
    """
    steps = int(np.floor(max_lateral_m / across_m))
    offsets = np.arange(-steps, steps + 1) * across_m
    hits = np.zeros(len(offsets), dtype=bool)
    for index, offset in enumerate(offsets):
        x = float(station[0] + normal[0] * offset)
        z = float(station[2] + normal[1] * offset)
        found = nearest(structure.heights_at(x, z), float(station[1]), attribute_within_m)
        hits[index] = found is not None

    if not hits.any():
        return None

    # Tracked as a mask rather than a running total, because what has to be
    # reported is the bridging inside the run that is *kept*. A total cannot be
    # narrowed to that afterwards: the runs below are maximal blocks of the
    # post-bridge `hits`, so asking them which cells were filled always answers
    # none. This is the second form of `Q58`'s trap — a counter confined by the
    # construction it is meant to report on.
    filled_gap = np.zeros(len(offsets), dtype=bool)
    max_gap_cells = round(bridge_m / across_m)
    if max_gap_cells > 0:
        for low, high in itertools.pairwise(np.flatnonzero(hits)):
            if 1 <= high - low - 1 <= max_gap_cells:
                hits[low + 1 : high] = True
                filled_gap[low + 1 : high] = True

    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, hit in enumerate(hits):
        if hit and start is None:
            start = index
        elif not hit and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(hits) - 1))

    def distance_to_centre(run: tuple[int, int]) -> float:
        low, high = offsets[run[0]], offsets[run[1]]
        if low <= 0.0 <= high:
            return 0.0
        return float(min(abs(low), abs(high)))

    low_index, high_index = min(runs, key=distance_to_centre)
    clipped = low_index == 0 or high_index == len(hits) - 1
    # Only the gaps inside the run that was kept — bridging elsewhere across the
    # walk is not this station's deck, and counting it would inflate the figure
    # with the neighbouring carriageway's holes.
    closed = int(filled_gap[low_index : high_index + 1].sum())
    return (
        float(offsets[low_index]),
        float(offsets[high_index]),
        clipped,
        float(closed) * across_m,
    )


def along_metres(polyline: np.ndarray, vertex: int, station: np.ndarray) -> float:
    """Plan distance from the edge's start to a station, in metres.

    🔴 **The join key between this walk and `carriageway_occupancy.py`'s, and the
    station INDEX is not.** `deck_error.stations` cuts each segment into
    `ceil(L / spacing)` equal pieces, so the real pitch is `L / ceil(L / spacing)`
    and lands anywhere in `(spacing / 2, spacing]` — `_starved_shape` measures the
    length-weighted mean at **0.968 m against a nominal 1.0** on the shipped
    graph, with the shortest segment running at 0.451 m. So `index x spacing` is
    not a distance in either tool, and the two walks run at different pitches
    besides (2.0 m here, 1.0 m there). Metres are the only frame they share.

    Plan distance, because that is the frame every length in both tools is
    already quoted in — and through `plan_lengths` rather than restated, because
    that module calls itself a **primitive the duplicate-deliberately rule does
    not reach**: it grades nothing, so a second copy buys no check. Six tools
    already import it. ⚠️ Not `deck_error.stations`' case, which is licensed
    because it adds height interpolation; this adds only the residual from the
    vertex.
    """
    behind = float(plan_lengths(polyline)[vertex])
    return behind + float(np.hypot(*(station[[0, 2]] - polyline[vertex][[0, 2]])))


def survey(
    graph: dict[str, Any],
    manifest: dict[str, Any],
    structure: Faces,
    *,
    spacing_m: float,
    across_m: float,
    max_lateral_m: float,
    junction_m: float,
    attribute_within_m: float,
    bridge_m: float,
    trace: dict[int, list[Station]] | None = None,
) -> dict[int, Row]:
    """Every off-grade station, asked where the deck under it starts and stops.

    ⚠️ `trace`, when given, is filled per station for the edges it already has
    keys for — recorded **by the loop that makes each decision**, rather than by
    a second walk that would agree with this one only until one of them changed.
    It is read-only as far as this function's own counters go: the default path
    appends nothing and prints the same bytes it always did.
    """
    widths = half_widths(manifest)
    nodes = np.asarray([node["pos"] for node in graph["nodes"]], dtype=np.float64)
    nodes = nodes[:, [0, 2]] if len(nodes) else np.empty((0, 2))

    rows: dict[int, Row] = {}
    for edge in graph["edges"]:
        level = int(edge["elevation_level"])
        # Level -1 is a void; see the module docstring. Level 0 is what
        # `carriageway_margin.py` already reads against a published edge.
        if level <= 0:
            continue
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        edge_id = int(edge["id"])
        row = Row(
            edge=edge_id,
            graph_m=float(edge["width_m"]),
            lanes=int(edge["lanes"]),
            lanes_source=str(edge.get("lanes_source", "")),
        )
        rows[edge_id] = row

        walked = trace.get(edge_id) if trace is not None else None

        def record(
            vertex: int,
            station: np.ndarray,
            refused: str,
            *,
            span_m: float = float("nan"),
            off_centre_m: float = float("nan"),
            overhang_m: float = float("nan"),
            drawn_m: float = float("nan"),
            bridged_m: float = float("nan"),
            centre_off_deck: bool = False,
            _walked: list[Station] | None = walked,
            _polyline: np.ndarray = polyline,
        ) -> None:
            # Bound as defaults rather than read from the enclosing scope.
            # ⚠️ **Not the late-binding fix it looks like**: every call is inside
            # the same iteration that defines this, so a plain closure reads the
            # current edge either way — mutation-checked, and the two-edge test
            # below passes with the binding removed. What it actually buys is
            # `B023` staying quiet without a `noqa`, and correctness if a call is
            # ever deferred. Do not describe it as fixing a reachable bug.
            if _walked is None:
                return
            _walked.append(
                Station(
                    vertex=vertex,
                    along_m=along_metres(_polyline, vertex, station),
                    refused=refused,
                    span_m=span_m,
                    off_centre_m=off_centre_m,
                    overhang_m=overhang_m,
                    drawn_m=drawn_m,
                    bridged_m=bridged_m,
                    centre_off_deck=centre_off_deck,
                )
            )

        for vertex, station in walk_width(polyline, spacing_m):
            if len(nodes) and float(np.hypot(*(nodes - station[[0, 2]]).T).min()) < junction_m:
                row.refused.junction += 1
                record(vertex, station, "junction")
                continue
            half = half_width_at(widths.get(edge_id, []), vertex)
            if half <= 0.0:
                row.refused.no_ribbon += 1
                record(vertex, station, "no_ribbon")
                continue
            normal = left_of((polyline[vertex + 1] - polyline[vertex])[[0, 2]])
            found = deck_run(
                structure,
                station,
                normal,
                max_lateral_m=max_lateral_m,
                across_m=across_m,
                attribute_within_m=attribute_within_m,
                bridge_m=bridge_m,
            )
            if found is None:
                row.refused.no_deck += 1
                record(vertex, station, "no_deck", drawn_m=2.0 * half)
                continue
            low, high, clipped, bridged = found
            if clipped:
                # Kept out of the distribution rather than clamped into it: a
                # clipped run's span is `2 x max_lateral_m` whatever the deck
                # does, and a percentile over those reports the flag.
                row.refused.clipped += 1
                record(vertex, station, "clipped", drawn_m=2.0 * half)
                continue
            off_deck = not low <= 0.0 <= high
            if off_deck:
                row.centre_off_deck += 1
            row.span_m.append(high - low)
            # Negated: `low` and `high` locate the deck in the centreline's
            # frame, so their midpoint is the deck's middle relative to the
            # road. What is published is the other way round — the centreline
            # relative to the deck — which is the sense `centreline_error.py`
            # already gives a field of this name, and the sense in which the
            # value is the correction to apply.
            row.off_centre_m.append(-0.5 * (low + high))
            row.drawn_m.append(2.0 * half)
            row.bridged_m.append(bridged)
            row.overhang_m.append(max(0.0, low + half) + max(0.0, half - high))
            record(
                vertex,
                station,
                "",
                span_m=row.span_m[-1],
                off_centre_m=row.off_centre_m[-1],
                overhang_m=row.overhang_m[-1],
                drawn_m=row.drawn_m[-1],
                bridged_m=row.bridged_m[-1],
                centre_off_deck=off_deck,
            )
    return rows


def kept_rows(rows: dict[int, Row], min_stations: int) -> dict[int, Row]:
    """The edges both tables describe — one predicate, called twice.

    🔴 **Shared because a divergence here is SILENT.** `clamp_report`'s ratchet
    compares its negative halves against `centre_off_deck` summed over its own
    `kept`, so two copies of this comprehension drifting apart would leave the
    two tables describing different populations with the ratchet still passing.
    ⚠️ Not one of this repo's deliberate duplications — those are second
    *measurements* across files (`carriageway.py` against `carriageway_margin.py`),
    and this is one filter twice in one file.
    """
    return {
        edge: row for edge, row in rows.items() if row.span_m and len(row.span_m) >= min_stations
    }


def report(
    rows: dict[int, Row],
    names: dict[int, str],
    *,
    min_stations: int,
    spacing_m: float,
    across_m: float,
) -> None:
    """The per-edge table, the pooled distributions, and the refusals."""
    kept = kept_rows(rows, min_stations)
    log.info("")
    log.info(
        "  %d off-grade edges walked, %d with at least %d kept stations",
        len(rows),
        len(kept),
        min_stations,
    )
    if not kept:
        return

    log.info("")
    log.info("  drawn ribbon against the deck under it, per edge")
    log.info(
        "    %-6s %-26s %5s %-9s %8s %8s %8s %8s %8s %5s %5s",
        "edge",
        "road",
        "lanes",
        "from",
        "graph",
        "drawn",
        "deck p50",
        "over p50",
        "over max",
        "off",
        "n",
    )
    ordered = sorted(kept.values(), key=lambda row: -percentiles(row.overhang_m)[0])
    for row in ordered:
        deck_p50 = percentiles(row.span_m)[0]
        over_p50 = percentiles(row.overhang_m)[0]
        log.info(
            "    e%-5d %-26s %5d %-9s %8.2f %8.2f %8.2f %8.2f %8.2f %5d %5d",
            row.edge,
            names.get(row.edge, "unnamed")[:26],
            row.lanes,
            row.lanes_source[:9],
            row.graph_m,
            percentiles(row.drawn_m)[0],
            deck_p50,
            over_p50,
            max(row.overhang_m),
            row.centre_off_deck,
            len(row.span_m),
        )

    spans = [value for row in kept.values() for value in row.span_m]
    overs = [value for row in kept.values() for value in row.overhang_m]
    offs = [value for row in kept.values() for value in row.off_centre_m]
    drawns = [value for row in kept.values() for value in row.drawn_m]
    excess = [
        drawn - span
        for row in kept.values()
        for drawn, span in zip(row.drawn_m, row.span_m, strict=True)
    ]
    log.info("")
    log.info("  pooled over %d kept stations — magnitudes", len(spans))
    log.info("    %-22s %8s %8s %8s %8s", "", "p50", "p90", "p99", "max")
    for label, values in (
        ("deck span m", spans),
        ("drawn ribbon m", drawns),
        ("overhang m", overs),
    ):
        log.info("    %-22s %8.2f %8.2f %8.2f %8.2f", label, *percentiles(values))

    # 🔴 Signed, and on its own table. These two are two-sided populations and
    # the four-point magnitude convention above cannot see a side: see
    # `signed_percentiles`.
    log.info("")
    log.info("  the same stations — SIGNED, positive is left of travel")
    log.info(
        "    %-22s %8s %8s %8s %8s %8s %7s %7s %6s",
        "",
        "p1",
        "p10",
        "p50",
        "p90",
        "p99",
        "left",
        "right",
        "zero",
    )
    for label, values in (
        ("off centre m", offs),
        ("drawn - deck m", excess),
    ):
        log.info(
            "    %-22s %8.2f %8.2f %8.2f %8.2f %8.2f %7d %7d %6d",
            label,
            *signed_percentiles(values),
            *sides(values),
        )

    # Half a cell: the walk quantises every extent to `across_m`, so a
    # smaller threshold would be reporting float noise as overhang.
    hanging = sum(1 for value in overs if value > across_m / 2.0)
    off_deck = sum(row.centre_off_deck for row in kept.values())
    log.info("")
    log.info(
        "    %d of %d kept stations hang past the deck (%.1f%%); "
        "%d have their centreline off it entirely",
        hanging,
        len(overs),
        100.0 * hanging / len(overs),
        off_deck,
    )
    # The line that ties this tool to `overhang.py`'s published `Q22` figure.
    #
    # ⚠️ **The two read the same faces and are still not equal, and the reason is
    # this tool's model rather than a defect in either.** `overhang.py` asks each
    # cell independently whether structure is under it; this asks for the deck's
    # *extent*, which is one contiguous run, so every hole the estate leaves
    # narrows the run and the overhang is an **upper bound**. `--bridge-m` is
    # what closes that, and the residual difference is the holes wider than it.
    #
    # ⚠️ **It is NOT the junction refusal, which was the first guess and is
    # measured false**: at `--junction-m 0` the fraction moves 14.0% -> 14.3%,
    # the wrong way. Recorded because the plausible explanation and the true one
    # point in opposite directions here.
    log.info(
        "    %.0f m2 of %.0f m2 drawn at those stations has no deck under it (%.1f%%); "
        "overhang.py grades the whole level",
        sum(overs) * spacing_m,
        sum(drawns) * spacing_m,
        100.0 * sum(overs) / sum(drawns),
    )
    bridged = [value for row in kept.values() for value in row.bridged_m]
    closed = [value for value in bridged if value > 0.0]
    log.info(
        "    %d of %d kept stations had a hole bridged, p50 %.2f m, max %.2f m, "
        "%.0f m closed in all",
        len(closed),
        len(bridged),
        percentiles(closed)[0],
        percentiles(closed)[3],
        sum(closed),
    )

    total = Refusals()
    for row in rows.values():
        total.junction += row.refused.junction
        total.no_ribbon += row.refused.no_ribbon
        total.no_deck += row.refused.no_deck
        total.clipped += row.refused.clipped
    log.info("")
    log.info(
        "    refused: %d junction, %d no ribbon, %d no deck, %d clipped by the walk (%d total)",
        total.junction,
        total.no_ribbon,
        total.no_deck,
        total.clipped,
        total.total,
    )


@dataclass(frozen=True)
class Clamp:
    """One station's ribbon cut back to the deck's own two rims (`Q105`).

    The counterfactual `Q103` left open: `carriageway.py` publishes **one**
    deck-derived width and **one** deck-derived offset per edge, both symmetric,
    so a ribbon centred on a deck that is not centred under it hangs on one side
    and stops short on the other. This asks what each station would be if the
    two halves were allowed to differ.

    🔴 **`left_m` and `right_m` are published APART and their sum is not a width
    whenever either is negative.** A negative half is not a narrow road, it is a
    centreline lying outside its own deck — there is no rim on that side to cut
    back to — and the two want opposite responses. Summed, the second vanishes
    into the first: the pricing run that opened this counted "0 undrawable" over
    **8** stations with a negative half, because `left + right` stayed positive
    at every one of them. That is `Q57` in miniature and `Q78`'s defect in a new
    column, so `undrawable` is a property of the two halves and never of the sum.

    ⚠️ **`width_m` is a PAINT extent and not a carriageway width.** The rims come
    from one contiguous run of structure at ribbon height, and `Q103` measured
    that at `e208` the run is the interchange's — 7.9 m against a 5.60 m ribbon,
    with 20 `clipped` stations upstream — so its middle is not this
    carriageway's. Cutting paint back to structure is the reading this file's
    own truth side licenses (*"the right truth for is-the-paint-on-the-deck"*);
    publishing the result as `width_m` would be `Q57`'s generalisation with a
    deck for a population, and is exactly what `Q103` refused for the offset.
    """

    left_m: float
    right_m: float
    drawn_m: float

    @property
    def width_m(self) -> float:
        return self.left_m + self.right_m

    @property
    def given_up_m(self) -> float:
        """Paint this station would give up — which is `overhang_m` EXACTLY.

        🔴 **An identity, not a correlation, and unconditional.**
        `half - min(half, high) == max(0, half - high)` and
        `half - min(half, -low) == max(0, half + low)` for every input, so this
        is `survey`'s own overhang formula rearranged — checked at 3.6e-15 over
        200,000 random triples. **So the clamp gives up precisely the metres
        that had no deck under them and not one more**, which is what makes it
        a cut back to structure rather than a narrowing.

        ⚠️ **It is therefore NOT published as a column**: `over p50` and
        `over max` in the table above are the same numbers, and printing them
        twice under a second name would be the fourth table claiming
        information it does not add. It stays as the assertion that ties this
        arithmetic to the walk's own recorded value — see
        `test_it_reproduces_the_overhang_the_walk_ALREADY_recorded`.
        """
        return self.drawn_m - self.width_m

    @property
    def undrawable(self) -> bool:
        """Either half negative — the centreline is off the deck it stands on."""
        return self.left_m < 0.0 or self.right_m < 0.0


def clamp_station(span_m: float, off_centre_m: float, drawn_m: float) -> Clamp:
    """Cut one station's half-widths back to the deck's left and right rims.

    Arithmetic on two columns `survey` already records, and deliberately not a
    second walk: `span_m` and `off_centre_m` locate both rims exactly —
    `high = span / 2 - off_centre`, `low = -span / 2 - off_centre` — because
    the published offset is the negation of the deck's middle. A walk that
    re-found them would be a second reading of the same faces that could only
    ever disagree with this one by drifting.

    ⚠️ **`overhang_m` is already the SUM of the two sides this separates.**
    `survey` records `max(0, low + half) + max(0, half - high)`; the right term
    is the left rim's and the left term is the right rim's. So the clamp is not
    a new measurement, it is a refusal to add those two together.
    """
    half = 0.5 * drawn_m
    return Clamp(
        left_m=min(half, 0.5 * span_m - off_centre_m),
        right_m=min(half, 0.5 * span_m + off_centre_m),
        drawn_m=drawn_m,
    )


def priced_widths(clamps: dict[int, list[Clamp]]) -> dict[int, list[float]]:
    """Per edge, the clamped widths that ARE widths — undrawable ones dropped.

    🔴 **The exclusion this function exists for was the fourth table's own first
    defect.** `Clamp` says in red that `left + right` is not a width where
    either half is negative, and the first build then computed every median,
    every minimum, the sort key and both bar counts over a population that
    included them — reading `e208` at **0.70 m**, which is a station with a
    -0.10 m half counted as a narrow carriageway. `Q57` inside the one class
    written to prevent it.

    ⚠️ **An edge whose every station is undrawable prices nothing and is
    dropped**, rather than left in for `min` to raise on. The caller reports how
    many, because a silently absent edge is the same defect one level up.
    """
    priced = {
        edge: [clamp.width_m for clamp in series if not clamp.undrawable]
        for edge, series in clamps.items()
    }
    return {edge: values for edge, values in priced.items() if values}


def clamp_report(
    rows: dict[int, Row],
    names: dict[int, str],
    *,
    min_stations: int,
    max_lateral_m: float,
    lane_bar_m: float,
    car_bar_m: float | None,
) -> None:
    """What an asymmetric ribbon would cost, per edge and pooled (`Q105`).

    🔴 **There is deliberately NO "stations on deck after the clamp" counter,
    and that number is the reason this function exists rather than the reason it
    is trusted.** It is every kept station, by construction: if `-low >= half`
    then `right = half` and `low + right <= 0`, and otherwise `right = -low` and
    `low + right = 0` exactly — the overhang term is identically zero either
    way, and the same on the left. Printing it would report the algebra as a
    result, which is `Q58`'s confined-to-the-bar trap arriving in the one number
    a reader would take as the case for building this. **The benefit is the
    hanging population the table above already prints** — a rim inside the
    ribbon is a parapet standing in the paint, read from the other side — and
    what is priced here is only the cost.

    🔴 **The UNDRAWABLE stations are excluded from every priced figure, and
    leaving them in was this table's own first defect.** A station with a
    negative half has no rim on that side, so `left + right` is not a width —
    `Clamp` says so in red — and the first build then computed the medians, the
    minima, the sort key and both bar counts over a population that included
    them. It read `e208` at **0.70 m**, `e729` at 1.30 and `e104` at 2.81, and
    every one of those three is a station with a negative half being counted as
    a narrow carriageway: `Q57` inside the one class written to prevent it.
    Excluded, the same edges read **2.90**, **6.40** and **6.51 m** and the
    whole cost collapses from 6 stations on three edges to **2 on one**, with
    the car bar clear. They are counted and listed on their own below, which is
    the only honest place for them.

    ⚠️ **The paint given up is NOT a column here.** It is `overhang_m` exactly
    and unconditionally — see `Clamp.given_up_m` — so `over p50` and `over max`
    in the table above already publish it. What this table adds that nothing
    else does is the **left/right split**: the clamped width, the two bar counts
    over it, and the stations where the split has no answer at all.

    ⚠️ **The two bars are `fence.py`'s and stay apart.** `is_passable` reads the
    lane and `fits_car` reads the car, and `Q19` says re-pointing either at the
    other sends traffic down a 1.95 m edge or fences the player out of a 3.50 m
    one. They are counted as two columns for that reason and never as one
    "too narrow". ⚠️ **The car bar is read from `clearance.car_width_m` where
    `narrowing.py`, `reachability.py` and `centreline_error.py` each hold their
    own `CAR_WIDTH_M = 1.8` behind a `--car-width-m` flag.** The config's comment
    says that constant is the same fact — the taxi's own box collider — so the
    figures are comparable while the two agree and this side is the one that
    moves with the city. A city declaring no `clearance:` block loses the column
    and keeps the table, which is `fence.py`'s own degrade.

    ✅ **The cost counters are cap-STABLE, and that was predicted the wrong way
    round.** The plan for this work argued the clamp must inherit `span_m`'s cap
    sensitivity because it is derived from it. It does not, and the reason is
    structural: the clamp is `min(half, rim)`, **bounded above by the ribbon's
    own half-width**, so a deck that grows past the ribbon as the cap widens
    cannot move it. The cap reaches only stations whose deck is *narrower* than
    the ribbon — exactly the stations it was never clipping. Measured over
    `--max-lateral-m` 11 / 12 / 14 / 16 / 20 the deck span's p90 runs
    14.50 -> 18.80 m and its max 19.00 -> 36.20, while the stations under the
    lane bar hold at **2**, under the car bar at **0** and the negative halves
    at **8** throughout. ⚠️ **A drifting p50 is the population and not the
    clamp** — 6.75 -> 7.10 m as priced stations grow 1,295 -> 1,663 with the
    clipping refusal falling away. So quote the cap with a span, and not with
    this; the same rule as the overhang headline above, arrived at differently.

    ⚠️ **`--bridge-m` is the dial that does move it, and only at zero.** Over
    0 / 0.5 / 1 / 2 / 4 the lane-bar count reads 5 / 2 / 2 / 2 / 2, the car bar
    2 / 0 / 0 / 0 / 0 and the negative halves 9 / 8 / 8 / 7 / 7: unbridged, the
    walk is the hole detector the module docstring describes and it manufactures
    three pinches and a negative half of its own. Above 0.5 m the pricing is
    flat.
    """
    kept = kept_rows(rows, min_stations)
    if not kept:
        return

    clamps = {
        edge: [
            clamp_station(span, off, drawn)
            for span, off, drawn in zip(row.span_m, row.off_centre_m, row.drawn_m, strict=True)
        ]
        for edge, row in kept.items()
    }
    # Collected where the predicate is first evaluated, so the count, the two
    # side tallies and the listing below all read one list and the population
    # cannot be re-derived differently for the table than for the ratchet.
    undrawable = [
        (edge, clamp, span)
        for edge, series in clamps.items()
        for clamp, span in zip(series, kept[edge].span_m, strict=True)
        if clamp.undrawable
    ]
    priced = priced_widths(clamps)

    log.info("")
    log.info(
        "  COUNTERFACTUAL — the ribbon cut back to its deck's own two rims, "
        "at --max-lateral-m %.1f",
        max_lateral_m,
    )
    log.info("    nothing here is published and nothing is gated; it prices a fix, it is not one")
    log.info(
        "    clamp    left + right, over the stations where BOTH halves exist — an undrawable "
        "station is not a narrow road and is counted apart below"
    )
    log.info(
        "    %s  stations the clamp would put under fence.py's %s",
        f"<{lane_bar_m:.2f}/<{car_bar_m:.2f}" if car_bar_m is not None else f"<{lane_bar_m:.2f}",
        (
            "lane bar / car bar — two bars, never one"
            if car_bar_m is not None
            else "lane bar; the city declares no `clearance:` block, so there is no car bar"
        ),
    )
    log.info(
        "    neg      stations with a NEGATIVE half — no rim on that side to cut back to; "
        "must equal the `off` column above"
    )
    log.info(
        "    ⚠ the paint given up is `overhang_m` exactly, so it is `over p50` / `over max` "
        "above and is not repeated here"
    )
    log.info(
        "    %-6s %-26s %8s %8s %8s %6s %6s %5s %5s",
        "edge",
        "road",
        "drawn",
        "clamp50",
        "clamp mn",
        f"<{lane_bar_m:.2f}",
        f"<{car_bar_m:.2f}" if car_bar_m is not None else "<—",
        "neg",
        "n",
    )
    for edge in sorted(priced, key=lambda edge: min(priced[edge])):
        values = priced[edge]
        log.info(
            # 🔴 The car-bar cell is a STRING so an absent bar prints "-" rather
            # than 0. A zero there reads as "no station is under the car bar",
            # which is a measurement, where the truth is that nothing was
            # measured — `Q72`'s unreachable-counter trap in a single cell.
            "    e%-5d %-26s %8.2f %8.2f %8.2f %6d %6s %5d %5d",
            edge,
            names.get(edge, "unnamed")[:26],
            percentiles(kept[edge].drawn_m)[0],
            percentiles(values)[0],
            min(values),
            sum(1 for value in values if value < lane_bar_m),
            sum(1 for value in values if value < car_bar_m) if car_bar_m is not None else "-",
            sum(1 for clamp in clamps[edge] if clamp.undrawable),
            len(values),
        )
    if len(priced) != len(clamps):
        log.info(
            "    %d edge(s) price nothing — every kept station undrawable",
            len(clamps) - len(priced),
        )

    pooled = [value for values in priced.values() for value in values]
    log.info("")
    log.info("  pooled over %d priced stations — the LOW tail is the finding", len(pooled))
    log.info("    %-22s %8s %8s %8s %8s %8s", "", "p1", "p10", "p50", "p90", "p99")
    # 🔴 The signed five points and not the four-point magnitude table, for
    # `signed_percentiles`' reason arriving at a one-sided column: what matters
    # about a clamped width is its **bottom**, and p50/p90/p99/max reports the
    # top of it. A width has no negative half to make it two-sided; it is the
    # tail of interest that decides which convention applies, not the sign.
    log.info(
        "    %-22s %8.2f %8.2f %8.2f %8.2f %8.2f", "clamped width m", *signed_percentiles(pooled)
    )

    under_lane = sum(1 for value in pooled if value < lane_bar_m)
    log.info("")
    log.info(
        "    %d of %d priced stations fall under the %.2f m lane bar (%.1f%%); %s",
        under_lane,
        len(pooled),
        lane_bar_m,
        100.0 * under_lane / len(pooled),
        (
            f"{sum(1 for value in pooled if value < car_bar_m)} under the {car_bar_m:.2f} m "
            "car bar — fence.py's two bars, counted apart"
            if car_bar_m is not None
            else "the car bar is not counted — the city declares no `clearance:` block"
        ),
    )

    # 🔴 The ratchet on the sign. These are the same stations by construction —
    # a half goes negative exactly when the centreline falls outside the run —
    # so an inequality means one of the two stopped measuring what it says, and
    # the silent direction is `undrawable` reading 0 because the sum stayed
    # positive. Asserted rather than commented, `Q72`'s standard for a counter.
    off_deck = sum(row.centre_off_deck for row in kept.values())
    if len(undrawable) != off_deck:
        raise SystemExit(
            f"{len(undrawable)} stations have a negative half-width but {off_deck} were recorded "
            "with the centreline off the deck. These are the same stations; one of the two "
            "has stopped measuring what it says."
        )
    log.info(
        "    %d have a NEGATIVE half — %d left, %d right — which is the `off` column above; "
        "the clamp is undefined at every one and none is priced above",
        len(undrawable),
        sum(1 for _, clamp, _ in undrawable if clamp.left_m < 0.0),
        sum(1 for _, clamp, _ in undrawable if clamp.right_m < 0.0),
    )
    if undrawable:
        log.info("    %-6s %-26s %8s %8s %8s %8s", "edge", "road", "left", "right", "span", "drawn")
        for edge, clamp, span in undrawable:
            log.info(
                "    e%-5d %-26s %8.2f %8.2f %8.2f %8.2f",
                edge,
                names.get(edge, "unnamed")[:26],
                clamp.left_m,
                clamp.right_m,
                span,
                clamp.drawn_m,
            )
    log.info("    a clamp cuts paint back to structure; it does NOT license a width — see `Clamp`")


def occupancy_indices(polyline: np.ndarray, alongs: list[float], spacing_m: float) -> list[int]:
    """Each station's counterpart index in `carriageway_occupancy.py`'s walk.

    That tool's `--probe-edges` prints station index ranges and no distance, so
    without this column the join is arithmetic a reader cannot do by hand —
    `along_metres` says why `along_m / spacing` is not the answer.

    ⚠️ **Derived by re-walking, never computed from the pitch.** The index is
    the nearest station of `walk_width(polyline, spacing_m)` at that tool's own
    spacing, found in metres. That is the same generator over the same polyline,
    so the mapping is exact up to the two walks' resolutions rather than assumed.

    ⚠️ **It is only true for a run of that tool at this `spacing_m`.** The pitch
    is a flag there too, which is why it is one here — a default silently
    borrowed from the other tool's constant would go on printing indices after
    someone swept it.
    """
    occupancy = [
        along_metres(polyline, vertex, station)
        for vertex, station in walk_width(polyline, spacing_m)
    ]
    if not occupancy and alongs:
        # Unreachable behind `refuse_unprobeable`, and raised rather than
        # sentinelled for that reason: a `-1` here reaches the row formatter and
        # prints as a station number the occupier walk does not have.
        raise SystemExit(
            "occupancy_indices: the polyline walks no station, so there is nothing "
            "for these stations to be joined against"
        )
    grid = np.asarray(occupancy, dtype=np.float64)
    return [int(np.abs(grid - along).argmin()) for along in alongs]


def refuse_unprobeable(graph: dict[str, Any], edges: tuple[int, ...]) -> None:
    """Refuse a `--probe-edges` id that this walk could never print a row for.

    🔴 **Refused, never skipped.** An edge with nothing to print leaves the
    report silent about it, and silence here reads as "the deck is fine there" —
    the empty set as agreement, which is what `carriageway_occupancy`'s own
    `refuse_unprobeable` is written against.

    ⚠️ **Called from `main` before the walk, not from `probe` after it**, that
    tool's reason at this one: both conditions need only the graph, and left at
    the report they cost a mistyped id the whole walk and index before saying
    so — once per `--sweep` cap, here, because the walk runs inside that loop.

    The conditions are `survey`'s own admission rule restated in the order a
    reader would ask them, and a graph edge satisfying both is in `rows` by
    construction, which is what lets `probe` index rather than `.get`.
    """
    published = {int(edge["id"]): edge for edge in graph["edges"]}
    missing = [edge_id for edge_id in edges if edge_id not in published]
    if missing:
        raise SystemExit(
            f"--probe-edges names {edges_label(tuple(missing))}, which this region's "
            "road graph does not carry"
        )
    at_grade = [edge_id for edge_id in edges if int(published[edge_id]["elevation_level"]) <= 0]
    if at_grade:
        raise SystemExit(
            f"--probe-edges names {edges_label(tuple(at_grade))}, which is at or below "
            "grade — this walk reads level 1 and above, and `carriageway_margin.py` is "
            "what reads a carriageway edge a publisher printed"
        )
    stubs = [edge_id for edge_id in edges if len(published[edge_id]["polyline"]) < 2]
    if stubs:
        raise SystemExit(
            f"--probe-edges names {edges_label(tuple(stubs))}, whose polyline is a single "
            "point — there is no direction to take a cross-section against"
        )


def _cell(value: float, *, signed: bool = False) -> str:
    """One numeric column, or a dash where there is no measurement.

    Here rather than inline so the refused row and the kept row cannot drift:
    they shared a column layout across three hand-synced format strings, and a
    width changed in one of them lines a table up against nothing.
    """
    if np.isnan(value):
        return "-"
    return f"{value:+.2f}" if signed else f"{value:.2f}"


# The one place the probe's column widths are written down. ⚠️ All `%s`: the
# numbers arrive pre-formatted from `_cell`, because a `%7.2f` cannot render the
# dash a refusal needs and a second format string is how the two rows drift.
_PROBE_ROW = "      %3s %4s %8s %6s %7s %8s %7s %7s %6s  %s"


def probe(
    walked: dict[int, list[Station]],
    rows: dict[int, Row],
    names: dict[int, str],
    graph: dict[str, Any],
    edges: tuple[int, ...],
    *,
    spacing_m: float,
    max_lateral_m: float,
    bridge_m: float,
    occupancy_spacing_m: float,
) -> None:
    """One named edge's stations in walk order, for reading against the occupier.

    🔴 **A third report and its own function**, on `carriageway_occupancy`'s
    argument for the same flag: the two tables above answer a question about a
    *population this tool decided* and print one verdict per edge, and this
    answers a question about the **stations of edges the reader named**, printing
    many rows per edge. Folding it into either would hand that one a population
    nobody measured (`Q57`), so the edges arrive through a flag and never a
    filter.

    🔴 **Why it exists.** `Q103` left the four blocked level-1 edges at a
    mechanism it could not name, and the occupier probe answered *what stands
    there and how high* without being able to say whether the **ribbon** moves
    underneath it. `off_centre_m` is that missing column, and it separates the
    two fixes this whole file exists to keep apart: a ribbon drifting under a
    fixed rim is registration, a rim drifting under a fixed ribbon is geometry.
    A per-edge median cannot show either — `e208` runs 0.70 m to 8.10 m of span
    across its own kept stations — so the series is what is printed.

    ⚠️ **Reporting only, and there is no bar.** Nothing here is gated and
    nothing published; an edge named on the command line is not a population
    anything could be graded against.
    """
    if not edges:
        return
    # Indexed rather than `.get`, because `refuse_unprobeable` has already run
    # against this same graph in `main` — a miss here is an inconsistency to
    # hear about, which is the call `carriageway_occupancy`'s probe makes too.
    polylines = {
        int(edge["id"]): np.asarray(edge["polyline"], dtype=np.float64) for edge in graph["edges"]
    }

    log.info("")
    log.info(
        "  station walk — %d edge(s) named on the command line, reporting only, nothing gated",
        len(edges),
    )
    log.info(
        "    along    metres down the centreline — the join key to carriageway_occupancy.py, "
        "whose station index is NOT one"
    )
    log.info(
        "    occ      that tool's own station index at its --spacing-m %.2f, found in metres "
        "rather than by arithmetic",
        occupancy_spacing_m,
    )
    log.info(
        "    off_ctr  SIGNED offset of the centreline from the deck's middle, positive LEFT of "
        "travel (overhang.left_of)"
    )
    log.info(
        "    span     the deck parapet to parapet, quantised to the across cell and bounded by "
        "--max-lateral-m %.1f",
        max_lateral_m,
    )
    log.info(
        "    hang     drawn ribbon with no deck under it at this station; drawn is the ribbon's "
        "own width there"
    )
    log.info(
        "    brdg     metres of hole inside that span closed by --bridge-m %.2f — a span with "
        "this set spans TWO decks, so its middle is not one deck's and off_ctr against it is "
        "not a registration reading",
        bridge_m,
    )
    log.info(
        "    ⚠ a refused station prints its reason in place — the series has holes and they are "
        "the finding, not a gap to read across"
    )

    for edge_id in edges:
        row = rows[edge_id]
        series = walked[edge_id]
        log.info("")
        log.info(
            "    e%d %s — %d stations walked at %.2f m, %d kept, %d refused "
            "(%d junction, %d no_ribbon, %d no_deck, %d clipped)",
            edge_id,
            names.get(edge_id, "unnamed"),
            len(series),
            spacing_m,
            len(row.span_m),
            row.refused.total,
            row.refused.junction,
            row.refused.no_ribbon,
            row.refused.no_deck,
            row.refused.clipped,
        )
        indices = occupancy_indices(
            polylines[edge_id], [station.along_m for station in series], occupancy_spacing_m
        )
        log.info(
            _PROBE_ROW,
            "st",
            "vtx",
            "along",
            "occ",
            "span",
            "off_ctr",
            "hang",
            "drawn",
            "brdg",
            "note",
        )
        for index, (station, occupancy) in enumerate(zip(series, indices, strict=True)):
            note = (
                f"refused: {station.refused}"
                if station.refused
                else ("centreline off the deck" if station.centre_off_deck else "")
            )
            log.info(
                _PROBE_ROW,
                index,
                station.vertex,
                f"{station.along_m:.2f}",
                occupancy,
                _cell(station.span_m),
                _cell(station.off_centre_m, signed=True),
                _cell(station.overhang_m),
                _cell(station.drawn_m),
                _cell(station.bridged_m),
                note,
            )

    log.info("")
    log.info(
        "    no bar is applied above — this reads a mechanism station by station, "
        "it does not price a fix"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, parents=[bundle_arguments()])
    parser.add_argument("--spacing-m", type=float, default=STATION_M)
    parser.add_argument("--across-m", type=float, default=ACROSS_M)
    parser.add_argument("--max-lateral-m", type=float, default=MAX_LATERAL_M)
    parser.add_argument("--junction-m", type=float, default=JUNCTION_M)
    parser.add_argument("--bridge-m", type=float, default=BRIDGE_M)
    parser.add_argument("--min-stations", type=int, default=MIN_STATIONS)
    parser.add_argument(
        "--probe-edges",
        type=edges_argument,
        default=(),
        # The parser is imported rather than restated, so the flag is spelled the
        # same in both tools and `Q103`'s "order is kept, unlike --levels" rule
        # travels with it. Named edges, never a filter over a population this
        # tool decided — `probe` says in red why that is a third function.
        help=(
            "comma-separated edge ids to print station by station, for reading against "
            "carriageway_occupancy.py's walk of the same edges (default: none)"
        ),
    )
    parser.add_argument(
        "--probe-occupancy-spacing-m",
        type=float,
        default=OCCUPANCY_SPACING_M,
        # A flag and not the imported constant used directly: the `occ` column is
        # only true for a run of that tool at this pitch, and that pitch is a
        # flag there.
        help="the --spacing-m carriageway_occupancy.py was run at, for the probe's occ column",
    )
    parser.add_argument(
        "--sweep",
        default="",
        help="comma-separated --max-lateral-m values to re-measure at, for the cap's sensitivity",
    )
    parser.add_argument(
        "--sweep-bridge",
        default="",
        help="comma-separated --bridge-m values to re-measure at, for the bridge's sensitivity",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    manifest, tiles = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)
    structure, structure_class = structure_faces(city, tiles)
    log.info(
        "  '%s' is the structure class; %d upward faces", structure_class, len(structure.corners)
    )

    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    names = road_names(graph)
    # 🔴 **Both bars read here, and the missing one DEGRADES rather than
    # aborting.** `clearance:` is an optional block; `fence.py` guards the same
    # read with `if city.clearance is not None`, logs that nothing is fenced and
    # carries on. Refusing to start instead would kill the per-edge and pooled
    # tables — neither of which knows what a car is — over one absent column, on
    # a tool whose docstring says it grades rather than checks. `None` is the
    # absence of a bar and never a zero, which would silently price every
    # station as clearing it.
    lane_bar_m = float(city.roads.lane_width_m)
    car_bar_m = float(city.clearance.car_width_m) if city.clearance is not None else None
    # Measured off the DRAWN ribbon, not the graph's `width_m`. The two coincide
    # only while `floor_by_elevation_level` exempts off-grade from the widening;
    # a floor added there would widen the walk's subject without moving
    # `width_m`, and the guard would go on passing while the cap silently became
    # the measurement.
    drawn = half_widths(manifest)
    widest = 2.0 * max(
        (
            max(drawn.get(int(edge["id"]), [0.0]), default=0.0)
            for edge in graph["edges"]
            if int(edge["elevation_level"]) > 0
        ),
        default=0.0,
    )
    caps = [args.max_lateral_m]
    if args.sweep:
        caps = [float(value) for value in args.sweep.split(",")]
    for cap in caps:
        if 2.0 * cap <= widest:
            # `Q58`'s trap reachable from the command line: a walk narrower than
            # the paint reports every station as clipped, or worse, clamps the
            # span to the cap and publishes a clean distribution of the flag.
            raise SystemExit(
                f"--max-lateral-m {cap} walks {2.0 * cap:.2f} m, which cannot reach the "
                f"widest off-grade ribbon ({widest:.2f} m). The measurement would be the cap."
            )

    refuse_unprobeable(graph, args.probe_edges)

    bridges = [args.bridge_m]
    if args.sweep_bridge:
        bridges = [float(value) for value in args.sweep_bridge.split(",")]

    for cap in caps:
        for bridge in bridges:
            if args.sweep or args.sweep_bridge:
                log.info("")
                log.info("=== --max-lateral-m %.1f --bridge-m %.2f ===", cap, bridge)
            # Keyed before the walk, because `survey` fills the edges it
            # already has keys for and never invents one — an edge named on the
            # command line that it never reaches must reach `probe`'s own
            # refusal rather than quietly printing an empty series.
            walked: dict[int, list[Station]] = {edge: [] for edge in args.probe_edges}
            rows = survey(
                graph,
                manifest,
                structure,
                spacing_m=args.spacing_m,
                across_m=args.across_m,
                max_lateral_m=cap,
                junction_m=args.junction_m,
                attribute_within_m=args.attribute_within_m,
                bridge_m=bridge,
                trace=walked,
            )
            report(
                rows,
                names,
                min_stations=args.min_stations,
                spacing_m=args.spacing_m,
                across_m=args.across_m,
            )
            # The two bars are `fence.py`'s own pair — `roads.lane_width_m` for
            # `is_passable`, `clearance.car_width_m` for `fits_car` — read from
            # the city above rather than restated, so a config move cannot leave
            # this file printing 3.20 and 1.80 for ever.
            clamp_report(
                rows,
                names,
                min_stations=args.min_stations,
                max_lateral_m=cap,
                lane_bar_m=lane_bar_m,
                car_bar_m=car_bar_m,
            )
            probe(
                walked,
                rows,
                names,
                graph,
                args.probe_edges,
                spacing_m=args.spacing_m,
                max_lateral_m=cap,
                bridge_m=bridge,
                occupancy_spacing_m=args.probe_occupancy_spacing_m,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
