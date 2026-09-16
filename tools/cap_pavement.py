"""How much junction cap is drawn where a publisher says there is no carriageway (`P3-31`).

`surface.py` closes each junction with the convex hull of the arm mouths meeting
it, and since `P3-31` one hull closes a whole *cluster* of nodes joined by stubs.
A hull can only grow, and a hull over a wider junction grows over the corner
between two streets — which is pavement, not road. Nothing inside the bundle can
price that: the cap is the stage's own invention and `carriageway[]` describes
the ribbons, not the caps.

HyD's Pavement Polygon can. It draws the maintained carriageway as **area**, so
a point of cap paint either lies in some carriageway polygon or it lies on
something HyD did not call carriageway — footway, island, run-in. This tool
rasterises every cap ring in `roadsurface.json` at `--cell-m` and sorts each
cell into three states, pooled and per cap, worst first, so a cluster hull that
paved a corner is a row a reader can go and look at:

* **on carriageway** — inside some HyD carriageway polygon;
* **past a kerb** — outside every polygon but within `--near-m` of one's edge,
  which is cap drawn over what HyD calls footway, island or run-in;
* **unsurveyed** — outside every polygon and further than `--near-m` from any,
  which is HyD saying nothing about the ground at all. HKCEC's Expo Drive is
  the case: no carriageway polygon is published under the whole junction, so
  its caps read 100% off-polygon before `P3-31` and after, and a two-state
  reading would price a rule change there against a publisher's silence.

🔴 **The middle state is the price and the third is not**: a cap over silence
may be right or wrong and this tool cannot say which; a cap past a published
kerb is cap over something a publisher drew as not-carriageway. Quote them
apart. ⚠️ `--near-m` is the one free value, so sweep it when the split is
load-bearing — a cell in the middle of a silent junction reads `unsurveyed`
at 3 m and `past a kerb` at 30 m.

⚠️ **It grades and does not gate**, and there is deliberately no bar. HyD's
polygons carry the publisher's own registration error (`carriageway_margin.py`
says the same of its truth side), the drawn ribbon is already `max(width_m,
floor)` wide and so overlaps footway wherever the floor bites (`Q19`), and a cap
inherits that overlap from every arm it meets. So the number is a *price*, to be
compared before and after a change to the cap rule, never a share to be driven
to zero. ⚠️ **Compare it at one `--cell-m`**: the raster is what turns area into
a count, and a finer cell moves the tail.

⚠️ **The truth side is a 2D plan projection** and the polygons' `LVL` filter is
the `carriageway_survey` block's own (`off_grade_codes`), so the tool reads
level-0 caps only — a cap on a flyover has no HyD carriageway under it in plan
and would read as 100% off-road for the wrong reason.

Run it from the repo root:

    python tools/cap_pavement.py --region wan_chai
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterable
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import street_namer  # noqa: E402
from pipeline import gdb  # noqa: E402
from pipeline.carriageway import CARRIAGEWAY_AREA  # noqa: E402
from pipeline.config import Config, load_config  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.geometry import edge_distances, inside_polygon  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402
from pipeline.surface import SURFACE_MANIFEST_NAME  # noqa: E402

log = logging.getLogger("cap_pavement")


def carriageway_polygons(
    city: Config, region_id: str, *, sources_root: Path | None
) -> list[np.ndarray]:
    """HyD's carriageway polygons in the game frame, outer rings only.

    Read the way `carriageway._read_publisher` reads them — same source, same
    layer, same code and grade filters — but kept as rings rather than
    dissolved into boundary segments, because this tool asks *inside or not*
    where that stage asks *how far to the edge*. A polygon's holes are ignored:
    a traffic island inside a carriageway polygon is drawn as its own polygon
    with another code, and the outer ring is the carriageway HyD maintains.
    """
    survey = city.carriageway_survey
    if survey is None:
        raise SystemExit(
            f"city '{city.id}' declares no carriageway_survey block, so no publisher draws "
            "the carriageway as an area to price the caps against."
        )
    specs = [spec for spec in survey.edges if spec.geometry == CARRIAGEWAY_AREA]
    if not specs:
        raise SystemExit(
            "no carriageway_survey publisher declares `geometry: area`; the lines publishers "
            "draw an edge, not a surface, and this tool needs a surface."
        )
    transform = city.game_transform(region_id)
    bbox = city.read_box(region_id).bbox
    rings: list[np.ndarray] = []
    for spec in specs:
        wanted, off_grade = set(spec.codes), set(spec.off_grade_codes)
        reads = source_reads(
            city, spec, region_id, root=sources_root, bounds=city.read_bounds(region_id)
        )
        for path, member in reads:
            layer = gdb.read_layer(
                path,
                spec.layer.layer,
                columns=spec.layer.columns,
                bbox=bbox,
                zip_member=member,
                expect_crs=city.projected_crs,
            )
            codes = layer.column(spec.layer.field("edge_type"))
            levels = layer.column(spec.elevation_field) if spec.elevation_field else None
            owners, parts = gdb.polygons(layer)
            for owner, part in zip(owners, parts, strict=True):
                if str(codes[owner]) not in wanted:
                    continue
                if levels is not None and str(levels[owner]) in off_grade:
                    continue
                if not part:
                    continue
                outer = np.asarray(part[0], dtype=np.float64)
                if len(outer) < 3:
                    continue
                game_x, _, game_z = transform.to_game(outer[:, 0], outer[:, 1])
                rings.append(np.column_stack([game_x, game_z]))
    return rings


class _Index:
    """Polygons bucketed by plan cell, so a cap asks only its neighbours.

    The same bucket-then-reject shape as `surface._Occluders`, without its
    elevation-level key (every ring here is level 0) and with a margin, because
    `within` asks for distance to an edge where `cover` asks for containment.
    A tool-side copy rather than a shared helper on `Q19`'s precedent: a grader
    that imports the stage's own index is graded by it.
    """

    CELL_M = 32.0

    def __init__(self, rings: Iterable[np.ndarray]) -> None:
        self._rings = list(rings)
        self._low = [ring.min(axis=0) for ring in self._rings]
        self._high = [ring.max(axis=0) for ring in self._rings]
        self._cells: dict[tuple[int, int], list[int]] = {}
        for key, (low, high) in enumerate(zip(self._low, self._high, strict=True)):
            for cell in self._cells_of(low, high):
                self._cells.setdefault(cell, []).append(key)

    @classmethod
    def _cells_of(cls, low: np.ndarray, high: np.ndarray) -> list[tuple[int, int]]:
        lo = np.floor(low / cls.CELL_M).astype(int)
        hi = np.floor(high / cls.CELL_M).astype(int)
        return [(x, z) for x in range(lo[0], hi[0] + 1) for z in range(lo[1], hi[1] + 1)]

    def _near(self, low: np.ndarray, high: np.ndarray, margin: float) -> list[int]:
        pad = np.array([margin, margin])
        keys = {
            key
            for cell in self._cells_of(low - pad, high + pad)
            for key in self._cells.get(cell, ())
        }
        return [
            key
            for key in sorted(keys)
            if not ((self._low[key] > high + pad).any() or (self._high[key] < low - pad).any())
        ]

    def inside(self, points: np.ndarray) -> np.ndarray:
        """Whether each plan point lies in some carriageway polygon."""
        covered = np.zeros(len(points), dtype=bool)
        if len(points) == 0:
            return covered
        low, high = points.min(axis=0), points.max(axis=0)
        for key in self._near(low, high, 0.0):
            # Point-level clip on the box the ring already carries: a ring
            # touching one corner of a cap was otherwise tested against every
            # cell of it, 76% of the pairs on this region.
            todo = ~covered & ((points >= self._low[key]) & (points <= self._high[key])).all(axis=1)
            if todo.any():
                covered[todo] = inside_polygon(points[todo], self._rings[key])
        return covered

    def within(self, points: np.ndarray, distance_m: float) -> np.ndarray:
        """Whether each plan point lies within `distance_m` of some polygon's edge.

        Asked only of points already known to be outside, so "near an edge" is
        "near the carriageway": the cap is drawn past a kerb HyD drew, rather
        than over ground HyD never surveyed. Chunked because `edge_distances`
        builds a `(points, segments, 2)` array per ring.
        """
        near = np.zeros(len(points), dtype=bool)
        if len(points) == 0:
            return near
        low, high = points.min(axis=0), points.max(axis=0)
        for key in self._near(low, high, distance_m):
            # Only the points not yet near and within `distance_m` of the ring's
            # box can be within it of the ring's edge; the exact test is a
            # `(points, segments, 2)` array per ring, so it is worth the clip.
            gap = np.maximum(self._low[key] - points, 0.0) + np.maximum(
                points - self._high[key], 0.0
            )
            todo = np.flatnonzero(~near & (np.hypot(gap[:, 0], gap[:, 1]) <= distance_m))
            for chunk in range(0, len(todo), 2048):
                rows = todo[chunk : chunk + 2048]
                near[rows] = edge_distances(points[rows], self._rings[key]) <= distance_m
        return near


def raster(ring: np.ndarray, cell_m: float) -> np.ndarray:
    """Cell centres inside a plan ring, on a world-anchored grid.

    World-anchored — cells at multiples of `cell_m`, never at the ring's own
    corner — so two caps that overlap sample the same points and their areas
    can be compared, and so the count does not shift with where a hull starts.
    """
    low, high = ring.min(axis=0), ring.max(axis=0)
    xs = (np.arange(np.floor(low[0] / cell_m), np.ceil(high[0] / cell_m)) + 0.5) * cell_m
    zs = (np.arange(np.floor(low[1] / cell_m), np.ceil(high[1] / cell_m)) + 0.5) * cell_m
    if len(xs) == 0 or len(zs) == 0:
        return np.empty((0, 2))
    grid_x, grid_z = np.meshgrid(xs, zs)
    points = np.column_stack([grid_x.ravel(), grid_z.ravel()])
    return points[inside_polygon(points, ring)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--cell-m",
        type=float,
        default=0.25,
        help="raster cell; area is cells x cell^2, so quote it with every figure",
    )
    parser.add_argument(
        "--near-m",
        type=float,
        default=3.0,
        # An off-polygon cell this close to a polygon edge is past a kerb HyD
        # drew; further, HyD drew nothing here. The one free value, so a flag.
        help="how far past a HyD carriageway edge still counts as past its kerb",
    )
    parser.add_argument("--worst", type=int, default=12, help="how many caps to list")
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.cell_m <= 0.0 or args.near_m < 0.0:
        raise SystemExit("--cell-m must be positive and --near-m non-negative")

    city = load_config()
    out_dir = city.out_dir(args.region, args.out_root)
    manifest = json.loads((out_dir / SURFACE_MANIFEST_NAME).read_text(encoding="utf-8"))
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, args.region)
    name_of = street_namer(graph)
    caps = [
        np.asarray(cap["ring"], dtype=np.float64)[:, [0, 2]]
        for cap in manifest.get("caps", ())
        if cap["level"] == 0
    ]
    if not caps:
        raise SystemExit(f"{out_dir / SURFACE_MANIFEST_NAME} publishes no level-0 caps")

    rings = carriageway_polygons(city, args.region, sources_root=args.sources_root)
    log.info(
        "%s / %s: %d level-0 caps against %d HyD carriageway polygons, cell %.2f m, "
        "past-kerb within %.1f m of a polygon edge",
        city.id,
        args.region,
        len(caps),
        len(rings),
        args.cell_m,
        args.near_m,
    )
    index = _Index(rings)
    area = args.cell_m * args.cell_m
    rows: list[tuple[float, float, float, int, float, float, str]] = []
    total = kerb_total = silent_total = 0.0
    for ring in caps:
        cells = raster(ring, args.cell_m)
        outside = ~index.inside(cells)
        kerb = np.zeros(len(cells), dtype=bool)
        kerb[outside] = index.within(cells[outside], args.near_m)
        cap_area = len(cells) * area
        kerb_area = int(kerb.sum()) * area
        silent_area = int((outside & ~kerb).sum()) * area
        total += cap_area
        kerb_total += kerb_area
        silent_total += silent_area
        centre = ring.mean(axis=0)
        rows.append(
            (
                kerb_area,
                silent_area,
                cap_area,
                len(ring),
                float(centre[0]),
                float(centre[1]),
                name_of(float(centre[0]), float(centre[1])),
            )
        )
    rows.sort(reverse=True)

    log.info("")
    log.info("  cap area drawn: %.0f m2", total)
    log.info(
        "    past a HyD kerb: %.0f m2 (%.1f%%)   unsurveyed by HyD: %.0f m2 (%.1f%%)",
        kerb_total,
        100.0 * kerb_total / total if total else 0.0,
        silent_total,
        100.0 * silent_total / total if total else 0.0,
    )
    log.info(
        "  caps with any paint past a kerb: %d of %d; wholly unsurveyed: %d",
        sum(1 for row in rows if row[0] > 0.0),
        len(rows),
        sum(1 for row in rows if row[1] > 0.0 and row[1] == row[2]),
    )
    log.info("")
    log.info("  worst %d caps, by area past a HyD kerb:", min(args.worst, len(rows)))
    log.info("    kerb m2  silent m2    cap m2   corners   centre x/z      nearest street")
    for kerb_area, silent_area, cap_area, corners, x, z, name in rows[: args.worst]:
        log.info(
            "    %7.1f    %7.1f    %6.1f   %7d   %5.0f/%4.0f   %s",
            kerb_area,
            silent_area,
            cap_area,
            corners,
            x,
            z,
            name,
        )
    log.info("")
    log.info(
        "  This grades and does not gate: the past-kerb figure is a price to compare across a "
        "cap-rule change at one --cell-m and one --near-m, never a bar. HyD's polygons carry "
        "their own registration error and the ribbon already overlaps footway wherever the "
        "floor bites (Q19); the unsurveyed figure is HyD's silence, not a finding."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
