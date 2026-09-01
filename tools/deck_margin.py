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

A ribbon can hang because it is **too wide** for the deck (`width_m`, which
off-grade is still `lanes x lane_width_m` with an authored `lanes`) or because it
is **registered wrong** (the centreline sits off the deck). Those need opposite
fixes and `overhang.py` reports one number for both.

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

from carriageway_occupancy import road_names  # noqa: E402
from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    load_bundle,
    log_bundle,
    nearest,
    structure_faces,
)
from overhang import half_width_at, half_widths, left_of, walk_width  # noqa: E402
from pipeline.carriageway import JUNCTION_M, MIN_STATIONS  # noqa: E402
from pipeline.config import load_config  # noqa: E402

log = logging.getLogger(__name__)

# How far apart stations are walked down each centreline. 2.0 m is
# `overhang.py`'s own default and the two are meant to be comparable.
STATION_M = 2.0

# Lateral step of the cross-section walk. The deck edge is what is being found,
# so this is the resolution of every number here: a span is quantised to it and
# an overhang is quantised to it. 0.10 m keeps that below the 0.13 m parapets
# measured on CANAL ROAD FLYOVER without making a station cost more than a
# few hundred point queries.
ACROSS_M = 0.10

# Half-width of the cross-section walk. 12 m reaches past the widest authored
# off-grade ribbon (9.60 m, so 4.80 m of half-width) with room for the deck to
# be wider than the paint, which is the common case.
MAX_LATERAL_M = 12.0

# ⚠️ `JUNCTION_M` and `MIN_STATIONS` are imported from `pipeline.carriageway`,
# not restated. At a junction mouth the deck runs into the ramp it joins, so the
# contiguous run is the whole interchange rather than this edge's deck — the
# same reason `carriageway_margin.py` refuses there, and the two are *required*
# to agree for the populations to be comparable. Restating the numbers here
# would let them drift apart silently, which is what `centreline_error.py`
# already avoids by importing the same pair.

# How wide an interior hole in the deck may be before it stops being a hole and
# starts being a void between two decks. Sourced from the gap distribution's own
# bimodality rather than chosen — see `deck_run` for the numbers and `Q19` for
# why this estate has holes at all.
BRIDGE_M = 1.0


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
    authored_m: float
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
) -> dict[int, Row]:
    """Every off-grade station, asked where the deck under it starts and stops."""
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
            authored_m=float(edge["width_m"]),
            lanes=int(edge["lanes"]),
            lanes_source=str(edge.get("lanes_source", "")),
        )
        rows[edge_id] = row

        for vertex, station in walk_width(polyline, spacing_m):
            if len(nodes) and float(np.hypot(*(nodes - station[[0, 2]]).T).min()) < junction_m:
                row.refused.junction += 1
                continue
            half = half_width_at(widths.get(edge_id, []), vertex)
            if half <= 0.0:
                row.refused.no_ribbon += 1
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
                continue
            low, high, clipped, bridged = found
            if clipped:
                # Kept out of the distribution rather than clamped into it: a
                # clipped run's span is `2 x max_lateral_m` whatever the deck
                # does, and a percentile over those reports the flag.
                row.refused.clipped += 1
                continue
            if not low <= 0.0 <= high:
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
    return rows


def report(
    rows: dict[int, Row],
    names: dict[int, str],
    *,
    min_stations: int,
    spacing_m: float,
    across_m: float,
) -> None:
    """The per-edge table, the pooled distributions, and the refusals."""
    kept = {
        edge: row for edge, row in rows.items() if row.span_m and len(row.span_m) >= min_stations
    }
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
        "authored",
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
            row.authored_m,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, parents=[bundle_arguments()])
    parser.add_argument("--spacing-m", type=float, default=STATION_M)
    parser.add_argument("--across-m", type=float, default=ACROSS_M)
    parser.add_argument("--max-lateral-m", type=float, default=MAX_LATERAL_M)
    parser.add_argument("--junction-m", type=float, default=JUNCTION_M)
    parser.add_argument("--bridge-m", type=float, default=BRIDGE_M)
    parser.add_argument("--min-stations", type=int, default=MIN_STATIONS)
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

    bridges = [args.bridge_m]
    if args.sweep_bridge:
        bridges = [float(value) for value in args.sweep_bridge.split(",")]

    for cap in caps:
        for bridge in bridges:
            if args.sweep or args.sweep_bridge:
                log.info("")
                log.info("=== --max-lateral-m %.1f --bridge-m %.2f ===", cap, bridge)
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
            )
            report(
                rows,
                names,
                min_stations=args.min_stations,
                spacing_m=args.spacing_m,
                across_m=args.across_m,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
