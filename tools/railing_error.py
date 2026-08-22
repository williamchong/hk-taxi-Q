"""Where the drawn railings stand against the ones TD published (`P3-19`, `Q60`).

Grades the **shipped bundle**, not the pipeline's intentions. `railings.glb` is
read back, every fence is walked at a fixed pitch, and each station is measured
against the railing layer itself — the source, re-read here, not the stage's
account of it.

**What this sees that nothing else can.** `Q60` registers each railing onto the
drawn kerb because two-thirds of them were surveyed inside the widened ribbon.
That move is the whole of the decision, and between the join and the pixel there
are three ways to be wrong that neither side can inspect:

- the fence is put on the **wrong kerb of the right street**, which mirrors
  every railing in the city and still renders as a city;
- the run is published against the graph's polyline and drawn against the
  **trimmed** ribbon, so a street's fences slide by its junction trim;
- the registration quietly grows — a widening change, a new `outset_m` — and the
  fence walks out into the carriageway or back into the buildings.

Each of those renders as a perfectly good fence. This is the instrument that
reads a number instead.

⚠️ **This grades rather than checks**, the rule CLAUDE.md already records for
`kerbside_source_audit.py` and `carriageway_margin.py`. It exits 0 whatever it
finds. There is no bar here, deliberately: `shift_m` *should* be nonzero — it is
the price of `Q60`, published so it stays visible — and a bar on it would turn a
recorded cost into a tuning target.

⚠️ **It does not grade the join's *choice of street*.** The nearest published
railing to a drawn fence is found geometrically, so a fence hung on the wrong
edge of a pair of parallel streets agrees with itself. `etl/tests/test_railings.py`
pins the side convention against `surface.mitres`, and the stage's own
`shift_m` and `samples_unassigned` are what report the join's reach.

⚠️ **The region's own build output is what is graded, not the copy under
`game/assets/generated/`.** `tools/sync_generated.sh` mirrors one to the other
verbatim — but `roadsurface.json` carries the junction trims and does not ship,
and the side of a fence cannot be named without the centreline it is offset
from.

Run:  .venv/bin/python tools/railing_error.py --city hong_kong --region wan_chai
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline import gdb  # noqa: E402
from pipeline.config import CityConfig, load_city  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402
from pipeline.railings import AT_GRADE, RAILINGS_NAME  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402

log = logging.getLogger(__name__)

# Pitch the drawn fence is walked at. Finer than the stage's own `station_m`, so
# a station here is not the same point the stage placed — the two agreeing at a
# shared vertex would be a tautology rather than a measurement.
WALK_M = 0.5


@dataclass
class Report:
    """What one class's shipped mesh says, measured against the source that fed it."""

    # The class graded, so a report and its heading cannot be mismatched.
    klass_id: str = ""
    drawn_m: float = 0.0
    stations: int = 0
    # Distance from each drawn station to the nearest published railing of a
    # drawn code. **This is `Q60`'s price, re-measured from the artefact** — the
    # stage publishes its own `shift_m` from the arithmetic it did, and this is
    # the same quantity read off the bytes that ship.
    to_source_m: list[float] = field(default_factory=list)
    # Stations whose side of the nearest centreline differs from the side the
    # nearest published railing is on. ⚠️ **The mirror detector.** A flipped
    # convention puts every fence on the opposite kerb, which renders perfectly.
    side_disagrees: int = 0
    side_judged: int = 0
    # Published metres of a drawn code, at grade, with a drawn fence within
    # `--near-m`. The complement is what the join, the shift bar, the buried
    # kerb and the ribbon clip refused between them — not a fault, a coverage.
    source_m: float = 0.0
    covered_m: float = 0.0
    # The median panel, not the mesh's y range — see `walk`.
    height_m: float = 0.0


def walk(mesh_positions: np.ndarray, triangles: np.ndarray) -> tuple[np.ndarray, float, float]:
    """The fence's foot line as points, its drawn length, and its panel height.

    Recovered from the triangles rather than from any manifest — the stage's
    own account of what it drew is exactly what is not being trusted.

    ⚠️ **"The two lowest corners of a triangle" is not the foot, and reading it
    that way overstated the drawn length by 49%.** A quad fans into `[b0, t0,
    t1]` and `[b0, t1, b1]`; only the second has two feet, and the first's two
    lowest corners are a bottom and a *top*, which is the panel's diagonal. So a
    vertex is called a foot by the mesh's own structure instead: positions come
    in pairs sharing an `(x, z)`, and the lower of each pair is the foot.

    The height comes from the same pairing — the median panel, not the range of
    the whole mesh, which spans the region's terrain and read **12.96 m**.
    """
    keyed: dict[tuple[float, float], list[int]] = {}
    for index, (x, _y, z) in enumerate(mesh_positions):
        keyed.setdefault((round(float(x), 4), round(float(z), 4)), []).append(index)

    is_foot = np.zeros(len(mesh_positions), dtype=bool)
    panels: list[float] = []
    for rows in keyed.values():
        heights = mesh_positions[rows, 1]
        is_foot[rows[int(np.argmin(heights))]] = True
        if len(rows) > 1:
            panels.append(float(heights.max() - heights.min()))
    height_m = float(np.median(panels)) if panels else 0.0

    feet: dict[tuple[int, int], None] = {}
    for triangle in triangles:
        for first, second in ((0, 1), (1, 2), (2, 0)):
            a, b = int(triangle[first]), int(triangle[second])
            if is_foot[a] and is_foot[b]:
                feet[(min(a, b), max(a, b))] = None

    points: list[np.ndarray] = []
    drawn_m = 0.0
    for a, b in feet:
        start = mesh_positions[a][[0, 2]]
        end = mesh_positions[b][[0, 2]]
        length = float(np.hypot(*(end - start)))
        if length <= 0.0:
            continue
        drawn_m += length
        steps = max(1, round(length / WALK_M))
        for fraction in (np.arange(steps) + 0.5) / steps:
            points.append(start + fraction * (end - start))
    return (np.vstack(points) if points else np.empty((0, 2))), drawn_m, height_m


def published(
    city: CityConfig, region_id: str, sources_root: Path | None
) -> dict[str, tuple[np.ndarray, float]]:
    """Every published feature, at grade, as sampled points **keyed by class**.

    Re-read here rather than taken from `railings.json`, which is the difference
    between an instrument and an echo.

    ⚠️ **Partitioned by class, never pooled.** Since `Q61` the layer draws three
    classes into one `.glb`, and grading a class's mesh against every class's
    published lines would let a bollard drawn where a railing belongs find a
    railing nearby and call itself covered. Each class is graded against its own
    source and nothing else.

    One read for all of them, though: the layer is read once and split in memory.
    Called per class it re-opened the geodatabase once per class — 0.26 s each of
    a 2.4 s run, which is not a performance problem, but it is three answers to a
    question with one answer.
    """
    spec = city.railings
    if spec is None:
        raise SystemExit(f"city '{city.id}' declares no railings block; nothing to grade")

    transform = city.game_transform(region_id)
    samples: dict[str, list[np.ndarray]] = {klass.id: [] for klass in spec.classes}
    total_m: dict[str, float] = {klass.id: 0.0 for klass in spec.classes}
    for path, member in source_reads(city, spec, region_id, root=sources_root):
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = layer.column(spec.layer.field("line_type"))
        levels = layer.column(spec.layer.field("level"))
        owners, parts = gdb.polylines(layer)
        for owner, points in zip(owners, parts, strict=True):
            klass = spec.class_of(str(types[owner]))
            if klass is None:
                continue
            if str(levels[owner]).strip().lower() not in AT_GRADE:
                continue
            source = np.asarray(points, dtype=np.float64)
            if len(source) < 2:
                continue
            game_x, _, game_z = transform.to_game(source[:, 0], source[:, 1])
            plan = np.column_stack([game_x, game_z])
            step = np.diff(plan, axis=0)
            for index, length in enumerate(np.hypot(step[:, 0], step[:, 1])):
                if length <= 0.0:
                    continue
                total_m[klass.id] += float(length)
                steps = max(1, round(length / WALK_M))
                for fraction in (np.arange(steps) + 0.5) / steps:
                    samples[klass.id].append(plan[index] + fraction * step[index])
    return {
        klass_id: (
            np.vstack(points) if points else np.empty((0, 2)),
            total_m[klass_id],
        )
        for klass_id, points in samples.items()
    }


class _Nearest:
    """Nearest-point lookup over a sample cloud, on a grid.

    Deliberately not `kerbside.SideIndex`: this tool exists to disagree with the
    join when the join is wrong, and sharing its index would be sharing the half
    of it most likely to be at fault (`Q56`'s "two implementations disagreeing
    tells you one is wrong and never which" — read the other way round, an
    instrument that shares the implementation cannot disagree at all).
    """

    def __init__(self, points: np.ndarray, cell_m: float) -> None:
        self.points = points
        self.cell_m = cell_m
        self.buckets: dict[tuple[int, int], list[int]] = {}
        for index, (x, z) in enumerate(points // cell_m):
            self.buckets.setdefault((int(x), int(z)), []).append(index)

    def of(self, point: np.ndarray) -> tuple[int, float] | None:
        x, z = int(point[0] // self.cell_m), int(point[1] // self.cell_m)
        near = [
            index
            for dx in (-1, 0, 1)
            for dz in (-1, 0, 1)
            for index in self.buckets.get((x + dx, z + dz), ())
        ]
        if not near:
            return None
        rows = np.asarray(near)
        gap = np.hypot(*(self.points[rows] - point).T)
        best = int(np.argmin(gap))
        return int(rows[best]), float(gap[best])


class _Centrelines:
    """Every level-0 segment, for naming which side of a street a point is on."""

    def __init__(self, graph: dict) -> None:
        starts, ends = [], []
        for edge in graph["edges"]:
            if int(edge["elevation_level"]) != 0:
                continue
            plan = np.asarray(edge["polyline"], dtype=np.float64)[:, [0, 2]]
            if len(plan) < 2:
                continue
            starts.append(plan[:-1])
            ends.append(plan[1:])
        self.start = np.vstack(starts)
        self.step = np.vstack(ends) - self.start
        self.squared = np.maximum((self.step * self.step).sum(axis=1), 1e-9)

    def side_of(self, point: np.ndarray) -> tuple[int, float] | None:
        """The nearest segment's index and the signed side the point falls on.

        The sign is `mitres`'s own cross product, and it is written out here
        rather than imported for the reason `_Nearest` gives: an instrument that
        borrows the expression it is checking cannot catch a flip in it.
        """
        offset = point - self.start
        travel = np.clip((offset * self.step).sum(axis=1) / self.squared, 0.0, 1.0)
        gap = np.hypot(*((self.start + travel[:, None] * self.step) - point).T)
        best = int(np.argmin(gap))
        cross = offset[best, 0] * self.step[best, 1] - offset[best, 1] * self.step[best, 0]
        return best, float(cross)


def survey(
    city: CityConfig,
    region_id: str,
    klass_id: str,
    source: np.ndarray,
    source_m: float,
    *,
    near_m: float,
    out_root: Path | None,
) -> Report | None:
    """Grade one class's shipped mesh against its own published source.

    `source` is that class's share of `published()`, passed in rather than
    re-read: the layer is one read for all classes.

    `None` where the class drew nothing — a region need not publish every class,
    and an absent mesh is not a failure. What *is* a finding is a class that
    read metres and drew none, and that shows in `railings.json`'s own per-class
    `read_m` against `drawn_m` rather than here.
    """
    out_dir = city.out_dir(region_id, out_root)
    path = out_dir / RAILINGS_NAME
    if not path.exists():
        raise SystemExit(
            f"{path} does not exist. Run "
            f"`python -m pipeline.railings --city {city.id} --region {region_id}` first. "
            "A region whose sources publish no railing layer ships none, and that is not a failure."
        )

    # ⚠️ **This class's mesh and no other.** `walk` recovers a fence's feet by
    # grouping vertices that share a plan position and taking the lowest — pool
    # three classes standing at three heights into one pile and the panel
    # heights it medians are a mixture of all three.
    mesh = next((entry for entry in read_glb(path) if entry.name == klass_id), None)
    if mesh is None:
        return None

    report = Report(klass_id=klass_id, source_m=source_m)
    drawn, report.drawn_m, report.height_m = walk(mesh.positions, mesh.triangles)
    report.stations = len(drawn)
    lines = _Nearest(source, max(near_m, 1.0))
    fences = _Nearest(drawn, max(near_m, 1.0))
    centres = _Centrelines(read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id))

    for station in drawn:
        found = lines.of(station)
        if found is None:
            continue
        index, distance = found
        report.to_source_m.append(distance)
        drawn_side = centres.side_of(station)
        source_side = centres.side_of(source[index])
        if drawn_side is None or source_side is None:
            continue
        if drawn_side[0] != source_side[0]:
            # Different segments; the sign is not comparable, so this station
            # says nothing about the convention rather than voting badly.
            continue
        report.side_judged += 1
        if np.sign(drawn_side[1]) != np.sign(source_side[1]):
            report.side_disagrees += 1

    # Each source sample stands for the same share of the published length,
    # because they were laid down at a fixed pitch.
    per_sample_m = report.source_m / len(source) if len(source) else 0.0
    for sample in source:
        found = fences.of(sample)
        if found is not None and found[1] <= near_m:
            report.covered_m += per_sample_m
    return report


def _percentiles(values: list[float]) -> tuple[float, ...]:
    if not values:
        return (float("nan"),) * 4
    return tuple(float(value) for value in np.percentile(np.asarray(values), (50, 90, 99, 100)))


def render(report: Report, *, near_m: float) -> str:
    p50, p90, p99, worst = _percentiles(report.to_source_m)
    share = 100.0 * report.covered_m / report.source_m if report.source_m else float("nan")
    mirrored = (
        100.0 * report.side_disagrees / report.side_judged if report.side_judged else float("nan")
    )
    lines = [
        f"{report.klass_id} drawn against the {report.klass_id} published",
        "",
        f"  drawn                {report.drawn_m:9.0f} m over {report.stations} stations",
        f"  published (this class, at grade)   {report.source_m:9.0f} m",
        f"  covered within {near_m:.1f} m      {report.covered_m:9.0f} m  ({share:.1f}%)",
        f"  panel height         {report.height_m:9.2f} m",
        "",
        "  distance from each drawn station to the nearest published railing —",
        "  this is Q60's registration, re-measured from the shipped bytes:",
        f"    p50 {p50:.2f}   p90 {p90:.2f}   p99 {p99:.2f}   max {worst:.2f} m",
        "",
        "  side of the street, drawn against published:",
        f"    {report.side_disagrees} of {report.side_judged} stations disagree ({mirrored:.2f}%)",
        "",
        "  ⚠️ Grades rather than checks; exits 0 whatever it finds. A nonzero",
        "     distribution above is the recorded price of Q60, not a bar to tune",
        "     against. A side disagreement is a finding to go and look at — a",
        "     mirrored convention renders as a city.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--near-m",
        type=float,
        default=6.0,
        help=(
            "how close a drawn fence must come to a published railing to count "
            "as covering it (default 6.0, a little past the widening's own reach)"
        ),
    )
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_city(args.city)
    if city.railings is None:
        raise SystemExit(f"city '{city.id}' declares no railings block; nothing to grade")

    # One table per class since `Q61`. Kept as separate tables rather than one
    # pooled figure because that is the whole point of grading a class against
    # its own source: the fence is 90% of the metres, so anything the two small
    # classes did wrong would vanish into its average.
    sources = published(city, args.region, args.sources_root)
    for klass in city.railings.classes:
        source, source_m = sources[klass.id]
        report = survey(
            city,
            args.region,
            klass.id,
            source,
            source_m,
            near_m=args.near_m,
            out_root=args.out_root,
        )
        if report is None:
            log.info("%s: nothing drawn for this region\n", klass.id)
            continue
        log.info("%s\n", render(report, near_m=args.near_m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
