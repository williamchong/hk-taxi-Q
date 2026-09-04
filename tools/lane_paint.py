"""Is the lane the markings shader paints wide enough to be a lane (`Q113`)?

    .venv/bin/python tools/lane_paint.py

`road_markings.gdshader` runs `UV.x` from 0 at the nearside kerb to `lanes` at
the offside, so it cuts the **drawn** ribbon into `lanes` equal strips whatever
that ribbon turned out to be. The strip a driver sees is therefore a quotient of
two numbers no stage computes together: `lanes` is `pipeline/carriageway.py`'s
and the drawn half-width is `pipeline/surface.py`'s, and neither stage can see
the other's answer. That is why this is a tool rather than a counter — every
figure `roadgraph.json` and `roadsurface.json` publish grades a stage against its
own intermediates, and this quotient is not one of them. It is
`tools/paint_clearance.py`'s argument one dimension over: that tool asks whether
the paint sits on top of the road, this one asks whether what it divides the
road into is a lane.

`Q113` fixed one cause of a thin strip — a ribbon clamped to a deck the edge was
not standing on — and then swept the region for the rest **from a scratch
script**. This is that sweep, committed, which is `Q37`'s debt at a second layer:
the table `Q113` publishes cannot be re-derived by anyone today.

🔴 **The bar is TPDM 4.3.9.8's own narrow end and it is CONFIG, not a constant
here** — `carriageway_survey.width_bounds.lane_m[0]`, 3.00 m on this city. A
strip narrower than the narrowest through lane TD publishes is not a lane, and
that is a statement with a publisher behind it. ⚠️ `Q113` swept at **2.50 m**,
an unsourced round number; `--min-lane-m 2.5` reproduces its table exactly. The
sourced figure is the default and the round one stays reachable, rather than the
other way round.

⚠️ **Two counts, two questions, and the record gave only one of them.** An edge
with one thin station and an edge thin along its whole length are different
findings — `Q113`'s own correction at `_deck_rims`, which first published the
edges a rim was discarded on and not the ribbons that moved. Both are printed,
and so are the **metres**, because a vertex count is a property of the
resampling and metres are a property of the city.

⚠️ **`offset_m` is deliberately absent, and that is not `Q106` repeating.** That
defect was four tools rebuilding the ribbon symmetrically about a centreline the
paint had left; what it cost them was knowing *where* the road is. This asks
what a strip **of** the ribbon is worth, and since `Q107` `half_width_m` is half
the distance between the two rails — so `2 x half_width_m` is the ribbon's width
wherever it is centred. The divisor is `surface._u_metres`' own: the drawn width
over the lane count.

⚠️ **The lane bracket column is imported from `tools/carriageway_margin.py`**
rather than restated. There are two implementations of that arithmetic on
purpose — the pipeline's and that tool's, kept apart because their agreement
over independently *measured* widths is the only check either has — and a third
would be a third thing to drift. Nothing is graded on it here: it is a
diagnostic saying what the width thinks of the count, and this tool's own
reading needs no bracket at all.

⚠️ **It grades rather than checks and exits 0 whatever it finds.** A thin strip
is a disagreement between two published readings, so it is a finding to go and
look at and never a bar to retune.

Run:  .venv/bin/python tools/lane_paint.py
      .venv/bin/python tools/lane_paint.py --min-lane-m 2.5   # `Q113`'s table
      .venv/bin/python tools/lane_paint.py --sweep
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(ROOT / "tools"))

from carriageway_margin import lane_bracket  # noqa: E402
from carriageway_occupancy import road_names  # noqa: E402
from deck_error import bundle_arguments, load_bundle, log_bundle  # noqa: E402
from overhang import half_width_at, half_widths  # noqa: E402
from pipeline.config import WidthBounds, load_config  # noqa: E402
from pipeline.polyline import plan_steps  # noqa: E402

log = logging.getLogger(__name__)

# The bars the sweep walks, in metres of painted strip.
#
# TPDM 4.3.9.8's through-lane range at both ends, the authored `lane_width_m`
# between them, and `Q113`'s own 2.50 so its table stays on the same page as the
# sourced readings. ⚠️ A bound that cannot be swept is `Q58`'s trap, and this one
# decides the whole headline.
SWEEP_BARS_M = (2.00, 2.50, 3.00, 3.20, 3.65)


@dataclass(frozen=True)
class Edge:
    """One published edge, and the strip its markings shader paints on it."""

    id: int
    name: str
    level: int
    lanes: int
    lanes_source: str
    width_m: float
    width_source: str
    two_way: bool
    bracket: tuple[int, int] | None
    # The painted strip at every published vertex, and the metres of road each
    # of those vertices speaks for. Kept per station rather than reduced here so
    # that a sweep re-reads the same walk instead of re-walking it.
    strip_m: np.ndarray
    station_m: np.ndarray

    @property
    def narrowest_m(self) -> float:
        return float(self.strip_m.min())

    @property
    def length_m(self) -> float:
        return float(self.station_m.sum())

    def thin(self, bar_m: float) -> np.ndarray:
        """Which stations paint a strip under the bar."""
        return self.strip_m < bar_m

    def thin_m(self, bar_m: float) -> float:
        return float(self.station_m[self.thin(bar_m)].sum())

    @property
    def verdict(self) -> str:
        """What the measured width thinks of the published lane count.

        🔴 **Three states, and the third is not the second.** A boolean here
        reads a *missing* bracket as agreement, so a city that declares no
        `carriageway_survey.width_bounds` — or any edge whose width no publisher
        licensed — would be counted among the rows the width endorses, and the
        split below would print `0 over the bracket` on a population it cannot
        grade at all. That is `Q58`'s trap reachable from a config file, and it
        is why `ungraded` is a value rather than a `False`.

        ⚠️ **`within` is not an endorsement either**, only the absence of this
        particular disagreement: the bracket is a range, and an edge inside a
        wide one has not been told anything.
        """
        if self.bracket is None:
            return "ungraded"
        return "over" if self.lanes > self.bracket[1] else "within"


def station_metres(polyline: np.ndarray) -> np.ndarray:
    """How many metres of road each published vertex speaks for, in plan.

    Half of each adjacent segment, so the stations partition the edge exactly
    and the ends are not double-counted. ⚠️ **Metres beside the vertex count and
    never instead of it**: the count is what `Q113` published and is comparable
    with it, and the metres are what a driver drives. The two disagree wherever
    `deck.resample_m` puts stations unevenly, which is at every touchdown.
    """
    steps = plan_steps(polyline)
    if len(steps) == 0:
        return np.zeros(len(polyline))
    padded = np.concatenate([[0.0], steps, [0.0]])
    return 0.5 * (padded[:-1] + padded[1:])


def narrow_points(values: np.ndarray) -> tuple[float, float, float, float]:
    """min, p1, p10 and p50 of a painted strip.

    🔴 **Deliberately NOT the house p50/p90/p99/max table, which is upside down
    for this quantity.** That convention reports the tail of a *magnitude* — an
    error, an overhang, a shift — where the large values are the finding. A
    painted lane fails at its narrow end, so a p90 here would report the widest
    roads in the region and say nothing at all about the defect. Restated by
    hand rather than imported, which is what `deck_margin.percentiles` and
    `centreline_error.percentiles` already do for the two definitions that exist.
    """
    if values.size == 0:
        return (0.0, 0.0, 0.0, 0.0)
    points = np.percentile(values, (0, 1, 10, 50))
    return (float(points[0]), float(points[1]), float(points[2]), float(points[3]))


def survey(
    graph: dict[str, Any], manifest: dict[str, Any], bounds: WidthBounds | None
) -> list[Edge]:
    """Every drawn edge, with the strip its lane count cuts the ribbon into."""
    halves = half_widths(manifest)
    names = road_names(graph)
    rows: list[Edge] = []
    for published in graph["edges"]:
        edge_id = int(published["id"])
        widths = halves.get(edge_id)
        if not widths:
            # An edge the surface stage drew nothing for. It paints no strip, so
            # it has no reading here — reported by `undrawn` rather than being
            # given a zero, which would be the narrowest row in the table.
            continue
        lanes = int(published.get("lanes", 2))
        if lanes < 1:
            # `surface.MarkingCode` refuses this outright, so a bundle carrying
            # it is malformed rather than thin. Louder than a divide by zero.
            raise SystemExit(f"e{edge_id} publishes {lanes} lanes, which cannot be painted")
        polyline = np.asarray(published["polyline"], dtype=np.float64)
        strip = np.array(
            [2.0 * half_width_at(widths, vertex) / lanes for vertex in range(len(polyline))]
        )
        width_m = float(published.get("width_m", 0.0))
        two_way = str(published.get("direction", "both")) == "both"
        rows.append(
            Edge(
                id=edge_id,
                name=names.get(edge_id, "unnamed"),
                level=int(published.get("elevation_level", 0)),
                lanes=lanes,
                lanes_source=str(published.get("lanes_source", "authored")),
                width_m=width_m,
                width_source=str(published.get("width_source", "authored")),
                two_way=two_way,
                bracket=(
                    lane_bracket(width_m, bounds, two_way=two_way) if bounds is not None else None
                ),
                strip_m=strip,
                station_m=station_metres(polyline),
            )
        )
    return rows


def render(rows: list[Edge], *, bar_m: float, undrawn: int) -> list[str]:
    """The headline, the per-edge table and the pooled distribution."""
    thin = sorted((row for row in rows if row.narrowest_m < bar_m), key=lambda r: r.narrowest_m)
    stations = int(sum(int(row.thin(bar_m).sum()) for row in thin))
    metres = sum(row.thin_m(bar_m) for row in thin)
    pooled = np.concatenate([row.strip_m for row in rows]) if rows else np.array([])

    lines = [
        "",
        f"painted lane under {bar_m:.2f} m — {len(thin)} of {len(rows)} drawn edges, "
        f"{stations} vertices, {metres:.0f} m of road",
        f"  ({undrawn} published edges draw no ribbon and carry no reading)",
    ]
    if not thin:
        lines.append("  nothing under the bar.")
    else:
        lines += [
            "",
            f"{'edge':>6} {'lvl':>3} {'lanes':>5} {'lanes_source':>12} {'width_m':>8}"
            f" {'width_source':>18} {'bracket':>8} {'narrowest':>9} {'thin':>9} {'street'}",
        ]
        for row in thin:
            bracket = "-" if row.bracket is None else f"{row.bracket[0]}-{row.bracket[1]}"
            flag = {"over": "!", "within": " ", "ungraded": "?"}[row.verdict]
            lines.append(
                f"e{row.id:<5} {row.level:>3} {row.lanes:>5} {row.lanes_source:>12}"
                f" {row.width_m:>8.2f} {row.width_source:>18} {bracket:>7}{flag}"
                f" {row.narrowest_m:>9.2f}"
                f" {int(row.thin(bar_m).sum()):>3}/{len(row.strip_m):<5}"
                f" {row.name}"
            )
        lines.append(
            "  ! = `lanes` is more than the measured width brackets to — the width and the "
            "count disagree;  ? = no bracket, so the width says nothing about the count"
        )

    low, p1, p10, p50 = narrow_points(pooled)
    lines += [
        "",
        f"painted strip over all {pooled.size} drawn stations: "
        f"min {low:.2f}  p1 {p1:.2f}  p10 {p10:.2f}  p50 {p50:.2f} m",
    ]
    return lines


def render_by_class(rows: list[Edge], bar_m: float) -> list[str]:
    """The thin population split the two ways its two fixes are split.

    🔴 **`lanes_source` and elevation level, never pooled into one share.** At
    grade a thin strip is a *count* published against the width's own bracket;
    off-grade it is a count with no lane evidence at all, because no turn arrows
    are painted on any bridge deck in this region (`Q113`). The two want
    opposite fixes and an acceptance number over both is `Q57`'s generalisation.
    """
    thin = [row for row in rows if row.narrowest_m < bar_m]
    if not thin:
        return []
    lines = ["", "the thin population, split by where its evidence comes from:"]
    families = (
        ("at grade", [row for row in thin if row.level == 0]),
        ("off grade", [row for row in thin if row.level != 0]),
    )
    for level_label, here in families:
        if not here:
            continue
        by_source: dict[str, list[Edge]] = {}
        for row in here:
            by_source.setdefault(row.lanes_source, []).append(row)
        parts = ", ".join(f"{len(edges)} {source}" for source, edges in sorted(by_source.items()))
        over = sum(1 for row in here if row.verdict == "over")
        ungraded = sum(1 for row in here if row.verdict == "ungraded")
        lines.append(
            f"  {level_label:<9} {len(here):>2} edges — lanes_source: {parts}"
            f"; {over} carry more lanes than the width brackets to,"
            f" {ungraded} have no bracket to disagree with"
        )
    return lines


def render_sweep(rows: list[Edge], bars: tuple[float, ...]) -> list[str]:
    """What the headline does as the bar moves.

    A bound that cannot be swept is `Q58`'s trap, and this one decides every
    number above it. What the sweep is looking for is a population that grows
    smoothly with the bar — which would mean the finding is the bar's — against
    one that is flat over a range and then steps, which is a real cliff.
    """
    lines = [
        "",
        f"{'bar_m':>6} {'edges':>6} {'vertices':>9} {'metres':>8}",
    ]
    for bar_m in bars:
        thin = [row for row in rows if row.narrowest_m < bar_m]
        lines.append(
            f"{bar_m:>6.2f} {len(thin):>6} "
            f"{sum(int(row.thin(bar_m).sum()) for row in thin):>9} "
            f"{sum(row.thin_m(bar_m) for row in thin):>8.0f}"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        parents=[bundle_arguments()],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--min-lane-m",
        type=float,
        default=None,
        help="the bar (default: the city's own width_bounds.lane_m narrow end)",
    )
    parser.add_argument(
        "--sweep", action="store_true", help="also walk the bar across TPDM's through-lane range"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    survey_spec = city.carriageway_survey
    bounds = survey_spec.width_bounds if survey_spec is not None else None
    bar_m = args.min_lane_m
    if bar_m is None:
        if bounds is None:
            # The convention `carriageway_margin.py` keeps: loud about a
            # configuration it cannot measure rather than quietly substituting a
            # number of its own. A default with no publisher behind it is the
            # thing this tool's docstring refuses.
            raise SystemExit(
                f"city '{city.id}' declares no carriageway_survey.width_bounds, so there is no "
                "published through-lane width to take a bar from — pass --min-lane-m"
            )
        bar_m = float(bounds.lane_m[0])
    if bar_m <= 0.0:
        raise SystemExit(f"--min-lane-m {bar_m} is not a width")

    manifest, _ = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)
    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    rows = survey(graph, manifest, bounds)
    undrawn = len(graph["edges"]) - len(rows)

    for line in render(rows, bar_m=bar_m, undrawn=undrawn):
        log.info(line)
    for line in render_by_class(rows, bar_m):
        log.info(line)
    if args.sweep:
        for line in render_sweep(rows, SWEEP_BARS_M):
            log.info(line)
    # Grades rather than checks: a thin strip is two published readings
    # disagreeing, which is a finding to go and look at and not a build failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
