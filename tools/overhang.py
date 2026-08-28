"""Where the drawn carriageway is not over the structure it claims (`Q22`, `Q23`).

The sibling of `deck_error.py`, asking the question that one deliberately does
not. `deck_error` samples **centrelines** and measures height: how far is the
road from the deck under it, vertically. This samples **across the full drawn
width** and measures presence: is there a deck under it at all. A ribbon can
pass the first and fail the second — that is exactly what `Q19` found, and what
`Q22` is still open on.

Two figures come out of one pass, because they are the same probe pointed at two
populations:

- **`Q22` — off-grade carriageway hanging in air.** Cells of level-1 ribbon with
  no structure beneath them. 20.1% when the question was raised, 10.2% after the
  off-grade width rule, and no width rule reaches the rest: a single-lane ramp
  drawn at the two-lane default, a source centreline not centred on its deck,
  and `P2-1`'s 0.5 m decimation of `INFRASTRUCTURE` moving the deck's own edge.
- **`Q23` — level-0 carriageway standing on structure and still widened.** A
  road becomes a bridge partway along an edge, so `elevation_level` cannot say
  where. 1,070 m across 28 edges when the question was raised, every metre of it
  widened. This reports the metres and how many of them are still wide.

⚠️ **The two questions disagree about what counts as "on structure", and both
are right.** `roads.py` decides it *topologically* — an edge end is on a ramp
because it connects to the edge that is, and the walk stops where the structure
reaches grade. This tool decides it *geometrically* — there is an upward face
within `--support-m` of the drawn surface. The geometric set is larger and
includes things that are not bridges: a street laid over a covered structure
answers yes and should not be narrowed. So the two numbers are a lower and an
upper bound on the same defect, and the gap between them is a finding rather
than an error in either.

Shares `deck_error`'s reading of the shipped bundle and nothing with the
pipeline — same table as that module's docstring, same reason. What is new here
is reconstructing the ribbon's *width*, which comes from `city.json`'s
`carriageway` table: the number `surface.py` published, not a re-derivation of
`floor_for`. A tool that recomputed the widening would agree with the config
rather than with the mesh.

**`left_of`, `cross_section`, `half_width_at` and `walk_width` are public
because a third tool uses them.** `ground_clearance.py` asks a different
question of the same cells, and the four together are how a drawn carriageway is
walked across its width — `walk_width`'s duplicated-vertex guard most of all,
which is a defect anyone reimplementing this would have to rediscover. Same
argument as `deck_error` exporting its bundle reader to this module.

Run:  .venv/bin/python tools/overhang.py --city hong_kong
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    drawn_surface,
    load_bundle,
    log_bundle,
    nearest,
    stations,
    structure_faces,
)
from pipeline.config import load_city  # noqa: E402

log = logging.getLogger(__name__)


@dataclass
class Tally:
    """One population of ribbon cells, counted by whether anything holds it up."""

    cells: int = 0
    unsupported: int = 0
    area_m2: float = 0.0
    unsupported_area_m2: float = 0.0

    def add(self, *, supported: bool, area_m2: float) -> None:
        self.cells += 1
        self.area_m2 += area_m2
        if not supported:
            self.unsupported += 1
            self.unsupported_area_m2 += area_m2

    @property
    def share(self) -> float:
        return self.unsupported_area_m2 / self.area_m2 if self.area_m2 else 0.0


@dataclass
class Widened:
    """`Q23`: level-0 centreline resting on structure, and what its width does there.

    Three numbers rather than one, because "on structure" turned out to mean two
    different things and only one of them is a defect.

    `roads.py` lifts a level-0 end onto its ramp only while the structure stands
    more than `deck.at_grade_m` above the ground — 0.30 m in Hong Kong. Past
    that the structure is still *modelled*, as an abutment or a retaining wall,
    and the road on it is a road at grade. This probe cannot see the terrain, so
    it reports both populations and lets the third number separate them:

    - `on_structure_m` — every level-0 metre with structure under its centreline,
      at grade or up in the air. The upper bound, 943 m in Wan Chai.
    - `still_widened_m` — how much of that is drawn wider than its authored
      street. Not a defect on its own: an at-grade road on an abutment is
      supposed to be widened like every other street.
    - `overhanging_m` — how much of it is widened **past what holds it up**, so
      the outer edge of the carriageway stands over air. This is the closest
      this tool gets to the user's report, and it is still not a clean gate.

    ⚠️ **`overhanging_m` does not fall to zero, and it should not.** Measured on
    Wan Chai against the ETL's terrain, the two populations separate cleanly:
    the stations `Q23` narrowed sit on structure a median **1.55 m** above the
    ground (p90 3.13, max 4.03 — ramps), and the stations left wide sit on
    structure a median **0.15 m** above it (p90 0.41, max 0.92 — **none above a
    metre**). The second set is abutment and retaining wall at ground level, and
    a street there is a street: widening it is right, and its outer metre reads
    as unsupported only because nothing models the pavement beside it. Which is
    which needs the terrain, and this tool deliberately sees only the bundle. So
    the number is reported, moved 896 m to 382 m by the fix, and left ungated.
    """

    on_structure_m: float = 0.0
    still_widened_m: float = 0.0
    overhanging_m: float = 0.0
    edges: set[int] = field(default_factory=set)
    widened_edges: set[int] = field(default_factory=set)
    overhanging_edges: set[int] = field(default_factory=set)


def left_of(along: np.ndarray) -> np.ndarray:
    """The plan normal one metre to the left of travel.

    Hong Kong drives on the left and `surface.py` offsets the same way, but this
    tool only ever uses the normal symmetrically — both rails, both signs — so a
    flipped sign here would change nothing it reports. Written out anyway, since
    a reader comparing this against `mitres` will look for it.
    """
    length = float(np.hypot(along[0], along[1]))
    if length <= 0.0:
        return np.zeros(2)
    return np.array([along[1], -along[0]]) / length


def cross_section(
    point: np.ndarray, normal: np.ndarray, half_width_m: float, across_m: float
) -> list[tuple[float, float, float]]:
    """Plan positions across one station's full drawn width, and each one's share.

    Returned with the *area* each stands for rather than as bare points, so a
    ribbon whose width varies along its length weights its wide half correctly.
    A count of cells would report a narrow ramp and a wide arterial as equals.
    """
    if half_width_m <= 0.0:
        return []
    steps = max(1, int(np.ceil(2.0 * half_width_m / across_m)))
    span = 2.0 * half_width_m / steps
    return [
        (
            float(point[0] + normal[0] * offset),
            float(point[1] + normal[1] * offset),
            span,
        )
        for offset in (-half_width_m + span * (step + 0.5) for step in range(steps))
    ]


def half_widths(manifest: dict[str, Any]) -> dict[int, list[float]]:
    """`city.json`'s carriageway width table, per edge.

    Paired with `half_width_at`, and public for the same reason: the pre-`Q23`
    fallback below is a compatibility rule, and a second copy of it is a second
    place for it to stop being true.
    """
    return {
        int(entry["edge"]): (
            list(entry["half_width_m"])
            if isinstance(entry["half_width_m"], list)
            else [float(entry["half_width_m"])]
        )
        for entry in manifest["carriageway"]
    }


def half_width_at(widths: list[float], vertex: int) -> float:
    """The published half-width at one polyline vertex.

    Indexed by vertex because that is how `city.json` publishes it since `Q23`.
    A bundle from before that carries one number per edge, and is read here as
    a constant so the tool can grade an older build — which is the whole reason
    `deck_error` has a `--clearance-m` override.
    """
    if not widths:
        return 0.0
    return float(widths[min(vertex, len(widths) - 1)])


def walk_width(polyline: np.ndarray, spacing_m: float) -> Iterator[tuple[int, np.ndarray]]:
    """Stations down a polyline, each with the vertex it came from.

    `stations` interpolates but does not say which segment a station belongs
    to, and the width does — so the walk is repeated per segment here rather
    than the width being interpolated by plan distance. The difference is at
    most one station's worth of taper, well inside `--across-m`.

    ⚠️ **The tail of each segment is dropped except on the last**, because
    `stations` yields the polyline's final vertex as well as every interior
    step — so run per segment it emits each shared vertex twice, once as one
    segment's tail and again as the next one's head. Measured on Wan Chai
    before the guard: **735 of 4,127 level-1 stations were duplicates, 17.8%**.
    Q23's length is unharmed either way, since a repeat advances zero metres,
    but every duplicate contributes a whole extra cross-section to the area
    tally and biased `Q22`'s share toward the vertices.
    """
    for vertex in range(len(polyline) - 1):
        emitted = list(stations(polyline[vertex : vertex + 2], spacing_m))
        if vertex < len(polyline) - 2:
            emitted = emitted[:-1]
        for x, y, z in emitted:
            yield vertex, np.array([x, y, z])


def survey(
    generated: Path,
    manifest: dict[str, Any],
    deck: Faces,
    *,
    spacing_m: float,
    across_m: float,
    support_m: float,
    attribute_within_m: float,
) -> tuple[dict[int, Tally], Widened]:
    """Every drawn carriageway cell, asked whether structure lies under it."""
    graph = json.loads((generated / manifest["road_graph"]).read_text())
    widths = half_widths(manifest)
    drawn = drawn_surface(generated, manifest)

    tallies: dict[int, Tally] = {}
    widened = Widened()
    for edge in graph["edges"]:
        level = int(edge["elevation_level"])
        # Level -1 is a void with nothing to stand on and nothing to see it.
        # Measuring it would report every tunnel as hanging in air, which is
        # true and is `Q21`'s question rather than this one.
        if level < 0:
            continue
        edge_id = int(edge["id"])
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        tally = tallies.setdefault(level, Tally())
        authored_half = float(edge["width_m"]) / 2.0

        previous: np.ndarray | None = None
        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            half = half_width_at(widths.get(edge_id, []), vertex)

            # `None` means "no road is drawn at this cell" and is not evidence
            # either way, so it is left out of both the tally and the rim. They
            # used to disagree — the tally excluded it while the rim counted it
            # as hanging in air — which let a cell that is merely outside the
            # mesh, at a junction trim or against a stale width table, inflate
            # the `overhanging_m` headline.
            rim: list[bool] = []
            for x, z, span in cross_section(station[[0, 2]], normal, half, across_m):
                # The drawn road first, because the question is whether *what is
                # drawn* is held up. Falling back to the graph's own y would
                # measure a surface that may not have been built.
                surface_y = nearest(drawn.heights_at(x, z), float(station[1]), attribute_within_m)
                if surface_y is None:
                    continue
                below = nearest(deck.heights_at(x, z), surface_y, support_m)
                tally.add(supported=below is not None, area_m2=span * spacing_m)
                rim.append(below is None)

            if level != 0:
                previous = station
                continue
            # `Q23` counts centreline metres, so it advances by the distance
            # walked rather than by the station count — `walk_width` does not space
            # stations evenly across a segment boundary.
            step = 0.0 if previous is None else float(np.hypot(*(station - previous)[[0, 2]]))
            previous = station

            # ⚠️ **At the centreline, not anywhere across the width.** Asking
            # whether any cell of the ribbon has structure under it would make
            # this metric depend on the width — so narrowing the road would
            # shrink the very number that measures whether narrowing worked, and
            # the tool would report progress for having stopped looking. The
            # centreline is the one sample the fix cannot move.
            middle = nearest(
                drawn.heights_at(float(station[0]), float(station[2])),
                float(station[1]),
                attribute_within_m,
            )
            if middle is None:
                continue
            under_middle = nearest(
                deck.heights_at(float(station[0]), float(station[2])), middle, support_m
            )
            if under_middle is None:
                continue
            widened.on_structure_m += step
            widened.edges.add(edge_id)
            if half <= authored_half + 1e-3:
                continue
            widened.still_widened_m += step
            widened.widened_edges.add(edge_id)
            # Standing on structure in the middle and over nothing at the edge:
            # the carriageway is wider than what carries it. Either rim, since
            # a centreline is not always centred on its deck — that half of
            # `Q22` reaches level 0 too.
            if rim and (rim[0] or rim[-1]):
                widened.overhanging_m += step
                widened.overhanging_edges.add(edge_id)

    return tallies, widened


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    parser.add_argument(
        "--spacing-m", type=float, default=2.0, help="station spacing along an edge"
    )
    parser.add_argument("--across-m", type=float, default=0.5, help="cell width across the ribbon")
    parser.add_argument(
        "--support-m",
        type=float,
        default=1.0,
        # A cell is held up when structure sits within this of the drawn road.
        # Generous because the two surfaces are allowed to differ: `P2-1`
        # decimates `INFRASTRUCTURE` on a 0.5 m cell and the road carries a
        # 0.20 m clearance above its deck. What it must still reject is a cell
        # over open air beside a viaduct, where the nearest structure is the
        # deck 6 m below or nothing at all.
        help="how far structure may sit from the drawn road and still hold it up",
    )
    parser.add_argument(
        "--accept-off-grade",
        type=float,
        default=0.11,
        help="fail above this share of off-grade carriageway hanging in air (Q22's 10.2%%)",
    )
    parser.add_argument(
        "--accept-overhanging-m",
        type=float,
        default=None,
        help="fail above this many metres of level-0 carriageway widened past its support (Q23)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    manifest, tiles = load_bundle(args.generated, args.lod, args.city)
    log_bundle(manifest, args.lod)

    deck, structure_class = structure_faces(city, tiles)
    tallies, widened = survey(
        args.generated,
        manifest,
        deck,
        spacing_m=args.spacing_m,
        across_m=args.across_m,
        support_m=args.support_m,
        attribute_within_m=args.attribute_within_m,
    )
    log.info(
        "  %d upward faces of '%s' across %d tiles, sampled on a %.1f x %.1f m grid",
        len(deck.corners),
        structure_class,
        len(tiles),
        args.spacing_m,
        args.across_m,
    )

    total_area = sum(tally.area_m2 for tally in tallies.values())
    if not total_area:
        raise SystemExit("no drawn carriageway could be sampled — is the road mesh present?")

    # Off-grade only. At grade the same probe reads ~98% "hanging in air" and
    # means nothing by it — a street is supposed to have nothing under it, and
    # the terrain that would be there is not shipped. Its area is still summed,
    # because the share below is against the whole carriageway.
    log.info("")
    log.info("  Q22 — off-grade carriageway with no structure under it:")
    for level in sorted(level for level in tallies if level > 0):
        tally = tallies[level]
        log.info(
            "    level %+d  %8.0f m2 drawn, %6.1f%% hanging in air, %.0f m2 of it",
            level,
            tally.area_m2,
            100.0 * tally.share,
            tally.unsupported_area_m2,
        )
    off_grade = tallies.get(1, Tally())
    log.info(
        "    off-grade is %.1f%% of all drawn carriageway (level -1 excluded, see Q21)",
        100.0 * off_grade.area_m2 / total_area,
    )

    log.info("")
    log.info("  Q23 — level-0 carriageway standing on structure:")
    log.info("    %6.0f m across %d edges", widened.on_structure_m, len(widened.edges))
    log.info(
        "    %6.0f m of it still widened, across %d edges",
        widened.still_widened_m,
        len(widened.widened_edges),
    )
    log.info(
        "    %6.0f m widened past its support, across %d edges  <- the defect",
        widened.overhanging_m,
        len(widened.overhanging_edges),
    )
    if widened.overhanging_edges:
        log.info("    by edge id: %s", sorted(widened.overhanging_edges)[:8])

    problems = []
    if off_grade.share > args.accept_off_grade:
        problems.append(
            f"{100.0 * off_grade.share:.1f}% of off-grade carriageway hangs in air, "
            f"against {100.0 * args.accept_off_grade:.1f}%"
        )
    if args.accept_overhanging_m is not None and widened.overhanging_m > args.accept_overhanging_m:
        problems.append(
            f"{widened.overhanging_m:.0f} m of level-0 carriageway is widened past its support, "
            f"against {args.accept_overhanging_m:.0f} m"
        )
    if problems:
        log.error("")
        for problem in problems:
            log.error("  FAIL  %s", problem)
        return 1

    log.info("")
    log.info("  Within the accepted bounds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
