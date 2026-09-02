"""What TD painted, against the carriageway this bundle drew (`P3-30`).

A yellow box cannot be painted on a pavement. So every box in
`DTAD_YL_BOX_POLY` is a **published statement that the ground beneath it is
carriageway** — a fourth extent publisher beside `Q94`'s three, and the only one
that covers junctions, where `Q95`'s ray survey refuses to station. This tool
asks the one question that follows from it: **how much of the paint the bundle
ships has no drawn road under it, and what is around the part that does not?**

`Q104` measured that with a scratch script, which is the debt `Q37` was opened
about and `Q55` had to repay. This is the instrument.

Nothing here is shared with the code it grades:

| | the pipeline | this tool |
|---|---|---|
| The paint | rings, hatch clipping, border offsets | the **shipped `boxjunctions.glb`** |
| Is it road | the stage never asks | the **shipped `roads.glb`**, by point query |
| Which box | the ring it drew from | the **source polygon**, re-read |
| What is around it | nothing | **eight rays**, marched |

`gdb` and `crs` are general utilities and the source's own `box_types` and
at-grade filters are re-derived below rather than imported, on
`carriageway_margin.py`'s terms: a grader that shares a core with what it grades
retires itself.

🔴 **Identity comes from the source polygons and never from clustering the
mesh.** Plan-space single-linkage over the shipped triangles returns **18**
boxes where the stage drew 20 — two of the region's boxes abut — and it returns
18 flat from a 1.5 m to a 15 m radius, so a radius sweep cannot see the
undercount. That is `Q58`'s `drawn_gauge_m` trap in a new place: a quantity
stable across its own free value, read as correct. `boxes_unattributed` is what
holds the replacement honest — a triangle inside no published ring is a finding,
not a rounding.

🔴 **The classification radius and the distance reach are two different numbers
and merging them manufactures the answer.** The distance past the drawn edge
runs to nearly 5 m while the neighbourhood test is 4 m wide, so marching the
distance along the classification rays would confine the distribution to
`--ray-m` by construction and report a clean sweep whatever the data does —
`Q58`'s trap, reachable from the command line. `--ray-m` classifies;
`--reach-m` measures. Distances are recorded over **every** off-road triangle,
including the ones that classify `isolated`; recorded below the guard they would
be confined to the bar.

**Three classes, and they want opposite fixes — do not pool them.** Eight rays
at 45 degrees from an off-road triangle's centroid:

- **`void`** — some opposed pair of rays *both* find drawn road. The paint is
  crossing the gap between two ribbons that never meet, which is not a narrowing
  at all. `P3-31`.
- **`past kerb`** — road on one side only. The drawn ribbon really is narrower
  than the carriageway the publisher painted. `P3-32`.
- **`isolated`** — nothing within `--ray-m`. Unassigned.

The predicate is boolean, so the three are exhaustive and mutually exclusive by
construction, and `on road + void + past kerb + isolated` is asserted to close on
the total paint area. ⚠️ **That is what disjointness rests on — not on a config
mutation.** A widened ribbon closes voids as well as kerb overhangs, so *both*
shares fall under any global widening and a check demanding otherwise can only
pass on a broken instrument (`Q72`'s tautology, from the other side). The
rule's one free value is `--ray-m`, so sweep it: `--sweep` prints the table, on
the precedent of `carriageway_margin.py --pair-bearing-deg`.

⚠️ **A triangle is judged at its centroid, so the quantum is one triangle** —
`paint_clearance.py`'s rule, and the median shipped box triangle is a few
hundredths of a square metre. Count and area are both reported and neither is
derived from the other, because they can disagree.

⚠️ **The distance is an upper bound twice over**: eight rays resolve direction
to 45 degrees, and a march resolves range to `--step-m`. The true nearest drawn
road is never further than what this prints.

⚠️ It **grades rather than checks** and exits 0 whatever it finds. There is no
bar here on purpose: the shares this publishes are what `P3-31` and `P3-32` are
graded on, and a bar would turn the two fixes into one number (`Q57`).

Run:  .venv/bin/python tools/box_extent.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable
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
    drawn_surface,
    load_bundle,
    log_bundle,
)
from paint_clearance import paint_triangles, twice_plan_area  # noqa: E402
from pipeline import gdb  # noqa: E402
from pipeline.config import Config, load_config  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.geometry import inside_polygon  # noqa: E402
from pipeline.polyline import Segments  # noqa: E402

log = logging.getLogger(__name__)

# ⚠️ The source's own encoding of "no structure", re-derived rather than
# imported from `boxjunctions.py` — this tool may not share a filter with the
# stage whose output it grades. It is not a threshold anyone may tune.
_AT_GRADE = ("", "none", "null", "<na>")

# Eight rays, 45 degrees apart, so `i` and `i + 4` are exactly opposed. The
# count is what makes an opposed pair expressible at all: with six the pairs
# still exist, with five they do not.
_RAYS = 8

# The eight unit directions, hoisted because they are constants and the march
# would otherwise rebuild them once per off-road triangle.
_DIRECTIONS = np.stack(
    [
        np.cos(2.0 * np.pi * np.arange(_RAYS) / _RAYS),
        np.sin(2.0 * np.pi * np.arange(_RAYS) / _RAYS),
    ],
    axis=1,
)

ON_ROAD = "on road"
VOID = "void"
PAST_KERB = "past kerb"
ISOLATED = "isolated"

# The three an off-road triangle can be, and the whole set. ⚠️ Order matters
# only for the printed table: `ON_ROAD` leads because it is the denominator's
# larger half and a reader checks the partition against it first.
_OFF_CLASSES = (VOID, PAST_KERB, ISOLATED)
_CLASSES = (ON_ROAD, *_OFF_CLASSES)


@dataclass(frozen=True)
class SourceBox:
    """One published box junction, as the publisher drew it, in game plan space."""

    index: int
    # The outer ring, `(n, 2)` as `(x, z)`, open.
    ring: np.ndarray

    @property
    def centre(self) -> tuple[float, float]:
        """The ring's centroid, used only to name the row and to order the table."""
        return float(self.ring[:, 0].mean()), float(self.ring[:, 1].mean())


@dataclass
class BoxRow:
    """What one published box's paint did against the drawn carriageway."""

    index: int
    name: str
    centre: tuple[float, float]
    triangles: dict[str, int] = field(default_factory=lambda: dict.fromkeys(_CLASSES, 0))
    area_m2: dict[str, float] = field(default_factory=lambda: dict.fromkeys(_CLASSES, 0.0))
    # Distance past the drawn edge, over every off-road triangle in this box.
    past_m: list[float] = field(default_factory=list)

    @property
    def total_m2(self) -> float:
        return sum(self.area_m2.values())

    @property
    def off_m2(self) -> float:
        return self.total_m2 - self.area_m2[ON_ROAD]

    @property
    def off_n(self) -> int:
        return sum(self.triangles[name] for name in _OFF_CLASSES)


@dataclass
class Report:
    """Everything one run publishes."""

    rows: list[BoxRow] = field(default_factory=list)
    # 🔴 Triangles inside no published ring. Must be 0: the attribution is what
    # replaced clustering, and a triangle it cannot place is the finding that
    # says so. Never silently pooled into a nearest box.
    unattributed: int = 0
    unattributed_area_m2: float = 0.0

    def totals(self, name: str) -> tuple[int, float]:
        return (
            sum(row.triangles[name] for row in self.rows),
            sum(row.area_m2[name] for row in self.rows),
        )

    @property
    def placed(self) -> int:
        """Triangles that landed in a published ring, over every class.

        One spelling, because the partition assertion and the printed total were
        computed two different ways and agreed only while `BoxRow.triangles`
        held exactly `_CLASSES`. A stray key would have satisfied the assertion
        and shrunk the table.
        """
        return sum(sum(row.triangles.values()) for row in self.rows)

    @property
    def paint_m2(self) -> float:
        """Paint inside a published ring. ⚠️ Not the layer where `unattributed` is non-zero."""
        return sum(row.total_m2 for row in self.rows)

    @property
    def off_m2(self) -> float:
        return sum(row.off_m2 for row in self.rows)

    @property
    def off_n(self) -> int:
        return sum(row.off_n for row in self.rows)

    @property
    def past_m(self) -> list[float]:
        return [value for row in self.rows for value in row.past_m]


def pct(part: float, whole: float, blank: str = "—") -> str:
    """A percentage of a total that may be zero, formatted for a table.

    One spelling. There were six, and two of them guarded truthiness where the
    others guarded `> 0.0` — which is the kind of difference that survives
    review and then decides a printed row.
    """
    return f"{100.0 * part / whole:.1f}%" if whole > 0.0 else blank


def distribution(values: list[float]) -> dict[str, float | int]:
    """p50/p90/p99/max and the count they were taken over.

    The tail rather than the middle, for `ArrowReport.measured`'s stated reason,
    and `n` beside them because `n` is how a reader tells a distribution that was
    recorded over its refusals from one that was confined to a bar (`Q58`).
    """
    if not values:
        return {"p50": 0.0, "p90": 0.0, "p99": 0.0, "max": 0.0, "n": 0}
    array = np.asarray(values, dtype=np.float64)
    return {
        "p50": round(float(np.percentile(array, 50)), 4),
        "p90": round(float(np.percentile(array, 90)), 4),
        "p99": round(float(np.percentile(array, 99)), 4),
        "max": round(float(array.max()), 4),
        "n": len(values),
    }


# --------------------------------------------------------------------------
# The published side
# --------------------------------------------------------------------------


def outer_ring(ring: np.ndarray) -> np.ndarray | None:
    """The ring without its closing vertex, or None if nothing is left to place."""
    points = np.asarray(ring, dtype=np.float64)
    if len(points) and np.array_equal(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3 or not np.isfinite(points).all():
        return None
    return points


def published_boxes(
    city: Config, region_id: str, *, sources_root: Path | None
) -> tuple[list[SourceBox], dict[str, int]]:
    """Every published box junction in the region, in game plan space.

    Refusals are the publisher's own — a type outside `box_types`, a feature on
    a structure, an empty ring — and are counted rather than logged, so a run
    pasted into a report says what it did not place.
    """
    spec = city.boxjunctions
    if spec is None:
        raise SystemExit(
            f"city '{city.id}' declares no boxjunctions block, so nothing published an extent "
            "to grade the drawn carriageway against. That is the honest answer, not a failure."
        )
    transform = city.game_transform(region_id)
    refused = {"not_a_yellow_box": 0, "on_structure": 0, "empty_geometry": 0}
    boxes: list[SourceBox] = []
    for path, member in source_reads(city, spec, region_id, root=sources_root):
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = layer.column(spec.layer.field("type"))
        levels = layer.column(spec.layer.field("level"))
        owners, parts = gdb.polygons(layer)
        for owner, rings in zip(owners, parts, strict=True):
            if str(types[owner]) not in spec.box_types:
                refused["not_a_yellow_box"] += 1
                continue
            if str(levels[owner]).strip().lower() not in _AT_GRADE:
                refused["on_structure"] += 1
                continue
            ring = outer_ring(rings[0])
            if ring is None:
                refused["empty_geometry"] += 1
                continue
            game_x, _, game_z = transform.to_game(ring[:, 0], ring[:, 1])
            boxes.append(SourceBox(index=len(boxes), ring=np.column_stack([game_x, game_z])))
    return boxes, refused


# ⚠️ `paint_triangles` and `twice_plan_area` come from `paint_clearance.py`,
# which already reads this exact asset and argues its own case for both: every
# triangle of a marking is judged including the ones facing the ground, and plan
# area is what a paint layer covers on the street. Tool-to-tool, so no
# grader/pipeline boundary is crossed — and one fewer place for the two graders
# of one file to disagree about what its triangles are.


def covered(road: Faces, x: float, z: float) -> bool:
    """Whether the shipped road mesh has any face at this plan position."""
    return len(road.heights_at(x, z)) > 0


def march(road: Faces, x: float, z: float, *, reach_m: float, step_m: float) -> list[float]:
    """First drawn road along each of the eight rays, or `inf` where there is none.

    Marched to `reach_m` — the distance reach, never the classification radius —
    so that a caller can classify at one bar and measure at another.
    """
    # 🔴 Floor, never round, and no `max(1, ...)` floor under it. Rounding
    # marches *past* `reach_m` whenever the step does not divide it — 10.0 m in
    # 0.6 m steps reaches 10.2 — and a one-step minimum makes the overshoot
    # unbounded. A distance column that can exceed its own stated reach is the
    # thing this tool keeps two separate values to avoid.
    steps = int(reach_m // step_m)
    hits: list[float] = []
    for dx, dz in _DIRECTIONS:
        found = float("inf")
        for step in range(1, steps + 1):
            distance = step * step_m
            if covered(road, x + dx * distance, z + dz * distance):
                found = distance
                break
        hits.append(found)
    return hits


def classify(hits: list[float], *, ray_m: float) -> str:
    """`void`, `past kerb` or `isolated`, from the eight ray hits.

    ⚠️ Exhaustive and mutually exclusive by construction — the opposed-pair test
    is a boolean over a set that is either empty or not. That, and the partition
    identity the caller asserts, is what disjointness rests on; a config
    mutation cannot establish it, because a widened ribbon closes voids and kerb
    overhangs alike.
    """
    within = [hit <= ray_m for hit in hits]
    if not any(within):
        return ISOLATED
    opposed = _RAYS // 2
    if any(within[ray] and within[ray + opposed] for ray in range(opposed)):
        return VOID
    return PAST_KERB


# --------------------------------------------------------------------------
# The survey
# --------------------------------------------------------------------------


def name_boxes(graph: dict[str, Any], boxes: list[SourceBox]) -> list[str]:
    """Each box named by the nearest street, for a row a reader can find.

    ⚠️ **Naming only.** Nothing here scores a box, and the nearest edge is not
    treated as its host — a box spans several arms and has none
    (`boxjunctions.py`). Two boxes on one street are separated by the centroid
    printed beside the name, which is why the table carries both.

    ⚠️ **`Segments.nearest`, not the nearest polyline vertex.** Hand-rolled, this
    measured to vertices, so a long straight edge with two distant endpoints lost
    to a denser-vertexed side street and the box took the wrong name. The shared
    join clamps to the segment. ⚠️ **Level 0 only, as every other caller passes**
    (`polyline.Segments.nearest`): a deck overhead is not the street a box is
    painted on.
    """
    named = road_names(graph)
    level_0 = [
        edge
        for edge in graph["edges"]
        if int(edge["elevation_level"]) == 0 and int(edge["id"]) in named
    ]
    if not level_0:
        return ["unnamed"] * len(boxes)
    segments = Segments.of(level_0)
    return [named.get(segments.nearest(*box.centre).edge, "unnamed") for box in boxes]


@dataclass(frozen=True)
class Marched:
    """The expensive half of the survey, done once and classified many times.

    🔴 **The march does not know `ray_m`, and that is what makes `--sweep`
    honest.** Sweeping by re-running the whole survey would re-march every ray
    and re-attribute every triangle, so a moving row could be the radius or
    could be anything else that moved with it. Here the sweep re-reads one set
    of marched hits at a second bar, and nothing else can differ.
    """

    # Which published box each triangle fell in, `-1` for none.
    owner: np.ndarray
    areas: np.ndarray
    on_road: np.ndarray
    # First drawn road along each of the eight rays, per off-road triangle,
    # keyed by triangle index. `inf` where a ray found none within the reach.
    hits: dict[int, list[float]]


def attribute(centroids: np.ndarray, boxes: list[SourceBox]) -> np.ndarray:
    """Which published box each paint centroid falls in, `-1` for none."""
    owner = np.full(len(centroids), -1, dtype=np.int64)
    for box in boxes:
        # ⚠️ First ring wins, and what that buys is determinism. `inside_polygon`
        # is half-open, so a point on an axis-aligned shared border already falls
        # in exactly one ring; two of this region's boxes abut, and on a seam
        # that is not axis-aligned the two rings can round differently.
        unplaced = owner < 0
        if not unplaced.any():
            break
        hit = inside_polygon(centroids[unplaced], box.ring)
        owner[np.flatnonzero(unplaced)[hit]] = box.index
    return owner


def march_paint(
    corners: np.ndarray, road: Faces, boxes: list[SourceBox], *, reach_m: float, step_m: float
) -> Marched:
    """Place every paint triangle, then march the ones with no road under them."""
    areas = 0.5 * twice_plan_area(corners)
    centroids = corners.mean(axis=1)[:, [0, 2]]
    owner = attribute(centroids, boxes)

    on_road = np.zeros(len(centroids), dtype=bool)
    hits: dict[int, list[float]] = {}
    for triangle in range(len(centroids)):
        if owner[triangle] < 0:
            continue
        x, z = float(centroids[triangle, 0]), float(centroids[triangle, 1])
        if covered(road, x, z):
            on_road[triangle] = True
            continue
        hits[triangle] = march(road, x, z, reach_m=reach_m, step_m=step_m)
    return Marched(owner=owner, areas=areas, on_road=on_road, hits=hits)


def survey(marched: Marched, boxes: list[SourceBox], names: list[str], *, ray_m: float) -> Report:
    """Read one marched paint layer at one classification radius."""
    report = Report()
    for box, name in zip(boxes, names, strict=True):
        report.rows.append(BoxRow(index=box.index, name=name, centre=box.centre))

    for triangle in range(len(marched.owner)):
        index = int(marched.owner[triangle])
        area = float(marched.areas[triangle])
        if index < 0:
            report.unattributed += 1
            report.unattributed_area_m2 += area
            continue
        row = report.rows[index]
        if marched.on_road[triangle]:
            row.triangles[ON_ROAD] += 1
            row.area_m2[ON_ROAD] += area
            continue
        hits = marched.hits[triangle]
        nearest = min(hits)
        # ⚠️ Recorded over every off-road triangle, `isolated` included, and
        # without consulting `ray_m`. Appended below the guard it would be
        # confined to the classification radius by construction (`Q58`).
        if np.isfinite(nearest):
            row.past_m.append(nearest)
        name_of = classify(hits, ray_m=ray_m)
        row.triangles[name_of] += 1
        row.area_m2[name_of] += area
    return report


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def log_rows(report: Report) -> None:
    """The per-box table, every published box, including the clean ones.

    ⚠️ **The three class shares here are of the box's off-road TRIANGLES**, and
    the area is printed beside them rather than folded into them. That is the
    axis `Q104` quoted its two sites on — 99% and 79% — and the pooled table
    below carries both, because they disagree.
    """
    log.info("")
    log.info("  per published box — every one, including those wholly on the road (`Q58`):")
    log.info("")
    log.info(
        "    %3s  %-22s %9s %7s %8s %6s %8s %8s %8s %8s",
        "box",
        "nearest street",
        "centre x/z",
        "tris",
        "m2",
        "off n",
        "off m2",
        "void %",
        "kerb %",
        "isol %",
    )
    for row in sorted(report.rows, key=lambda entry: entry.off_m2, reverse=True):
        log.info(
            "    %3d  %-22s %4.0f/%4.0f %7d %8.2f %6d %8.2f %8s %8s %8s",
            row.index,
            row.name[:22],
            row.centre[0],
            row.centre[1],
            sum(row.triangles.values()),
            row.total_m2,
            row.off_n,
            row.off_m2,
            *(pct(row.triangles[name], row.off_n, "0.0%") for name in _OFF_CLASSES),
        )
    log.info("")
    log.info(
        "    the three class shares are of each box's own off-road TRIANGLE count; "
        "its off-road area is the column beside them"
    )


def log_summary(report: Report, *, ray_m: float, reach_m: float, step_m: float) -> None:
    """The pooled figures `P3-31` and `P3-32` are graded against."""
    paint = report.paint_m2
    log.info("")
    log.info("  pooled, over %d published boxes:", len(report.rows))
    log.info("")
    log.info(
        "    %-12s %8s %10s %10s %12s %12s",
        "class",
        "tris",
        "m2",
        "of paint",
        "of off (n)",
        "of off (m2)",
    )
    for name in _CLASSES:
        count, area = report.totals(name)
        log.info(
            "    %-12s %8d %10.2f %9s %12s %12s",
            name,
            count,
            area,
            pct(area, paint, "0.0%"),
            "—" if name == ON_ROAD else pct(count, report.off_n),
            "—" if name == ON_ROAD else pct(area, report.off_m2),
        )
    # ⚠️ **Attributed paint, not the layer.** Every share above is taken against
    # this, and `unattributed` is outside it — so the row says which it is, and
    # the count beside it is the one the partition assertion uses.
    log.info("    %-12s %8d %10.2f", "attributed", report.placed, paint)
    log.info("")
    # 🔴 Both shares, because they disagree materially and neither is derived
    # from the other (`paint_clearance.py`'s rule, earning its keep). The void
    # triangles are small and many — hatch stripe ends crossing a median gap —
    # and the past-kerb ones are larger, so the count split reads 55.7/40.3/4.0
    # where the area split reads 43.6/48.0/8.4. ⚠️ `Q104` published the COUNT
    # split beside an AREA headline, which sizes `P3-31` at 55.5% of 38.7 m2
    # when by area it owns 43.6%. Quote which one, or it is `Q57`'s
    # generalisation with the denominators swapped.
    log.info(
        "    the two off-road columns disagree — quote which one; they are not interchangeable"
    )
    log.info("")
    log.info(
        "    %.2f m2 of %.2f (%.2f%%) has no drawn carriageway under it",
        report.off_m2,
        paint,
        100.0 * report.off_m2 / paint if paint > 0.0 else 0.0,
    )
    past = distribution(report.past_m)
    log.info(
        "    distance past the drawn edge: p50 %.2f  p90 %.2f  p99 %.2f  max %.2f  n %d",
        past["p50"],
        past["p90"],
        past["p99"],
        past["max"],
        int(past["n"]),
    )
    log.info(
        "    (classified within %.2f m, measured to %.2f m in %.3f m steps — two bars, "
        "deliberately not one)",
        ray_m,
        reach_m,
        step_m,
    )


def log_sweep(
    report_for: Callable[[float], Report], values: list[float], *, off_m2: float, off_n: int
) -> None:
    """`--ray-m` is the rule's one free value, so it is swept, not asserted.

    ⚠️ **Both bases, for the same reason the pooled table carries both.** The
    split quoted in `Q104` is a triangle-count share and the paint it describes
    is an area, and a sweep printed on one basis invites the reader to compare it
    against a figure taken on the other.

    ⚠️ The off-road population is fixed across the sweep — the radius
    reclassifies and never reclaims — so a moving row is the classification and
    can be nothing else. `Q72` rejected a divider test whose *count* ran
    8 → 29 → 49 → 80 over a free radius; this one moves within a constant
    denominator, which is a different claim and a weaker one.
    """
    log.info("")
    log.info("  the classification radius swept — the rule's one free value (`Q72`):")
    log.info("")
    log.info(
        "    %8s %9s %9s %9s   %9s %9s %9s",
        "--ray-m",
        "void n",
        "kerb n",
        "isol n",
        "void m2",
        "kerb m2",
        "isol m2",
    )
    for value in values:
        totals = [report_for(value).totals(name) for name in _OFF_CLASSES]
        log.info(
            "    %8.2f %9s %9s %9s   %9s %9s %9s",
            value,
            *(pct(count, off_n) for count, _ in totals),
            *(pct(area, off_m2) for _, area in totals),
        )
    log.info("")
    log.info(
        "    shares are of the %d triangles / %.2f m2 of off-road paint, which the radius "
        "cannot move",
        off_n,
        off_m2,
    )


def write_json(
    destination: Path, report: Report, *, ray_m: float, reach_m: float, refused: dict[str, int]
) -> None:
    """Per-box rows, for a reader who wants the numbers rather than the table."""
    payload = {
        "ray_m": ray_m,
        "reach_m": reach_m,
        "paint_m2": round(report.paint_m2, 4),
        "off_road_m2": round(report.off_m2, 4),
        "unattributed": report.unattributed,
        "refused": refused,
        "past_m": distribution(report.past_m),
        "boxes": [
            {
                "index": row.index,
                "name": row.name,
                "centre": [round(row.centre[0], 3), round(row.centre[1], 3)],
                "triangles": row.triangles,
                "area_m2": {name: round(value, 4) for name, value in row.area_m2.items()},
                "past_m": distribution(row.past_m),
            }
            for row in report.rows
        ],
    }
    destination.write_text(json.dumps(payload, indent=1, sort_keys=True, allow_nan=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    parser.add_argument(
        "--ray-m",
        type=float,
        default=4.0,
        # 🔴 The classification radius and nothing else. It decides what counts
        # as "there is road on that side", so it is the rule's one free value —
        # swept from the command line rather than by editing a constant, on
        # `carriageway_margin.py --pair-bearing-deg`'s precedent.
        help="how far a ray may look for drawn road when classifying a neighbourhood",
    )
    parser.add_argument(
        "--reach-m",
        type=float,
        default=10.0,
        # 🔴 Deliberately larger than `--ray-m` and deliberately separate. The
        # measured overrun runs past the classification radius, so sharing one
        # value would cap the distribution at the bar and report a clean sweep
        # whatever the data does (`Q58`).
        help="how far the distance-past-the-edge column may look",
    )
    parser.add_argument(
        "--step-m",
        type=float,
        default=0.05,
        # The march's range resolution, and the reason the distance is an upper
        # bound. Well under the kerb-scale overrun being measured, and 200 steps
        # of a 15 us point query is affordable on a layer this size.
        help="march resolution; the reported distance is accurate to this",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="also print the classification shares over a range of --ray-m",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="also write the per-box rows to box_extent.json under the region's out dir",
    )
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.step_m <= 0.0 or args.step_m > args.reach_m:
        # A zero step is a `ZeroDivisionError` traceback where every other bad
        # configuration here is a named exit, and a step over the reach marches
        # past it on the first stride.
        raise SystemExit(
            f"--step-m {args.step_m:.3f} must be positive and no larger than --reach-m "
            f"{args.reach_m:.2f}"
        )
    if args.reach_m < args.ray_m:
        # The one configuration that silently makes the tool wrong: a reach
        # under the classification radius caps the distribution below the bar
        # the classes are drawn at, which is the trap this tool is built to
        # avoid rather than to reproduce.
        raise SystemExit(
            f"--reach-m {args.reach_m:.2f} is under --ray-m {args.ray_m:.2f}; the distance "
            "column would be capped below the radius it classifies at"
        )

    manifest, _ = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)
    asset = manifest.get("boxjunctions")
    if asset is None:
        raise SystemExit(
            f"{args.generated / 'city.json'} declares no boxjunctions layer — this region ships "
            "no published extent to grade the drawn carriageway against"
        )

    road = drawn_surface(args.generated, manifest)
    log.info("  %d near-horizontal faces in %s", len(road.corners), manifest["road_surface"])
    corners = paint_triangles(args.generated / asset)
    log.info("  %d paint triangles in %s", len(corners), asset)

    city = load_config()
    region_id = str(manifest["region_id"])
    boxes, refused = published_boxes(city, region_id, sources_root=args.sources_root)
    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    log.info(
        "  %d published boxes, %d refused by the publisher (%s)",
        len(boxes),
        sum(refused.values()),
        ", ".join(f"{name} {count}" for name, count in refused.items()),
    )

    names = name_boxes(graph, boxes)
    marched = march_paint(corners, road, boxes, reach_m=args.reach_m, step_m=args.step_m)
    report = survey(marched, boxes, names, ray_m=args.ray_m)

    log_rows(report)
    log_summary(report, ray_m=args.ray_m, reach_m=args.reach_m, step_m=args.step_m)

    # 🔴 The partition, asserted rather than assumed. The three off-road classes
    # and the on-road paint must account for every triangle placed, or the
    # classification has stopped being a partition and every share above is
    # describing something other than what it says.
    if report.placed + report.unattributed != len(corners):
        raise SystemExit(
            f"partition does not close: {report.placed} classified + {report.unattributed} "
            f"unattributed against {len(corners)} paint triangles"
        )
    if report.unattributed:
        log.info("")
        log.info(
            "  🔴 %d triangles (%.3f m2) lie inside no published ring — the attribution that "
            "replaced clustering has a hole in it; go and look",
            report.unattributed,
            report.unattributed_area_m2,
        )

    if args.sweep:
        log_sweep(
            lambda value: survey(marched, boxes, names, ray_m=value),
            [1.0, 2.0, 3.0, 4.0, 6.0, 8.0],
            off_m2=report.off_m2,
            off_n=report.off_n,
        )

    if args.json:
        destination = city.out_dir(region_id, args.out_root) / "box_extent.json"
        write_json(destination, report, ray_m=args.ray_m, reach_m=args.reach_m, refused=refused)
        log.info("")
        log.info("  wrote %s", destination)

    log.info("")
    log.info(
        "  This grades and does not gate. The void share is `P3-31`'s and the past-kerb share "
        "is `P3-32`'s; they are different halves of one total and must not share a bar (`Q57`)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
