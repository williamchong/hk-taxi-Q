"""Where the drawn railings stand against the ones TD published (`P3-19`, `Q60`).

Grades the **shipped bundle**, not the pipeline's intentions. `railings.glb` is
read back, every fence is walked at a fixed pitch, and each station is measured
against the railing layer itself — the source, re-read here, not the stage's
account of it.

🔴 **Since `P5-5` the fence is a LIBRARY of one panel per class stood by
`railings_placements.json`, and this walks PANELS**: the foot line is recovered
from the unit panel's own triangles exactly as it was from the merged strip —
`walk` is unchanged and runs on twelve vertices — and every sample on it is then
stood where the document stands the panel, with the ETL's own
`placed_positions`. What is trusted from the stage is therefore the transform
convention and nothing else; the registration, the side and the coverage are
still read off where the steel actually is.

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

Run:  .venv/bin/python tools/railing_error.py --region wan_chai
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
from pipeline.config import Config, load_config  # noqa: E402
from pipeline.documents import read_document  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402
from pipeline.placements import PLACEMENTS_SCHEMA, placed_at  # noqa: E402
from pipeline.railings import AT_GRADE, RAILINGS_NAME, RAILINGS_PLACEMENTS_NAME  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402

log = logging.getLogger(__name__)

# Pitch the drawn fence is walked at. Finer than the stage's own `station_m`, so
# a station here is not the same point the stage placed — the two agreeing at a
# shared vertex would be a tautology rather than a measurement.
WALK_M = 0.5

# How far below its own stack's top a vertex may sit and still count as "at the
# top", when telling a slab's cap edges from its panels' (`Q112`). Only ever
# compared within one plan position, where the two candidates are a foot and a
# head a whole panel apart, so this is a float32 guard and not a tuning value.
_TOP_EPS_M = 1e-6


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


def _mid_shift(
    keyed: dict[tuple[float, float], list[int]],
    mesh_positions: np.ndarray,
    triangles: np.ndarray,
) -> dict[tuple[float, float], np.ndarray]:
    """Half the vector across the fence, per plan position (`Q112`).

    🔴 **A fence has thickness since `Q112`, so its foot comes in two lines, and
    walking both walks the same fence twice.** Left alone this tool read
    `drawn_m` **17,708 m** where the fence is 8,854, and its registration p50
    moved 1.40 → 1.42 m purely because half the samples stood 50 mm further out.
    Neither is a finding about the city.

    So the two are folded into one line at their **mid-surface**, and each
    surviving foot is shifted by the half-vector this returns. That is a uniform
    25 mm outside the face `_station` registered — stated rather than hidden,
    an order below the 0.5 m walk pitch, and the same on every sample, where
    walking both faces was bimodal.

    🚫 **The two faces are deliberately NOT told apart.** They are 50 mm
    apart and a fence commonly stands nearer the *opposed* carriageway than its
    own, so "the end closer to a centreline" picks the wrong face on **2,526 of
    5,067** pairs here — a coin toss. Reading the stage's normals instead would
    be trusting `facing_away`'s own claim, and this file's first paragraph is
    that the stage's account is what is not being trusted. A midpoint needs
    neither.

    ⚠️ **Found from the mesh's own topology.** The slab is closed at the top by
    a cap, so an edge joining two different plan positions at the top of their
    own vertex stacks, whose positions are **not** also joined at the foot, runs
    across the fence rather than along it. 🔴 **That second half is
    load-bearing**: the panel's own top edge joins consecutive stations at the
    top too, and without the foot test every station pairs with its neighbour
    and the walk returns **nothing at all**. And 🔴 **only the nearest such
    partner counts** — the cap fans into triangles, so its diagonals pair a
    station with its neighbour's far face as well, and taking every partner
    leaves 4,582 of 10,136 positions claiming to be both faces at once. Mutual
    nearest gives **5,067** pairs covering 10,134 of 10,136 positions at a
    separation of p50 exactly 0.0500 m.

    A sheet has no cap and therefore no such edge, so this returns nothing and
    the walk is what it always was.
    """
    tops = {key: float(mesh_positions[rows, 1].max()) for key, rows in keyed.items()}
    at_key = {
        index: (round(float(x), 4), round(float(z), 4))
        for index, (x, _y, z) in enumerate(mesh_positions)
    }

    crossings: set[tuple[tuple[float, float], tuple[float, float]]] = set()
    along: set[tuple[tuple[float, float], tuple[float, float]]] = set()
    for triangle in triangles:
        for first, second in ((0, 1), (1, 2), (2, 0)):
            a, b = int(triangle[first]), int(triangle[second])
            left, right = at_key[a], at_key[b]
            if left == right:
                continue
            pair = (min(left, right), max(left, right))
            low = mesh_positions[a][1] <= tops[left] - _TOP_EPS_M
            if low and mesh_positions[b][1] <= tops[right] - _TOP_EPS_M:
                along.add(pair)
            elif not low and mesh_positions[b][1] > tops[right] - _TOP_EPS_M:
                crossings.add(pair)

    nearest: dict[tuple[float, float], tuple[tuple[float, float], float]] = {}
    for left, right in crossings - along:
        span = float(np.hypot(*(np.asarray(left) - np.asarray(right))))
        for key, other in ((left, right), (right, left)):
            if key not in nearest or span < nearest[key][1]:
                nearest[key] = (other, span)

    shift: dict[tuple[float, float], np.ndarray] = {}
    for key, (other, _span) in nearest.items():
        if nearest.get(other, (None,))[0] != key:
            # Not mutual: this position's nearest partner has a nearer one of
            # its own, so the pair is not a cross-section and nothing is folded.
            continue
        shift[key] = (np.asarray(other) - np.asarray(key)) / 2.0
    return shift


def walk(mesh_positions: np.ndarray, triangles: np.ndarray) -> tuple[np.ndarray, float, float]:
    """The fence's foot line as points, its drawn length, and its panel height.

    Recovered from the triangles rather than from any manifest — the stage's
    own account of what it drew is exactly what is not being trusted.

    ⚠️ **One line per fence, not one per face** since `Q112` gave the fence
    thickness — see `_mid_shift` for how the two are folded together and why
    they are deliberately not told apart. ⚠️ **Run on the unit panel since
    `P5-5`**, twelve vertices in the panel's own frame, where a foot and its
    head still share an `(x, z)`; a pitched stand would break that pairing, so
    the walk happens before the stand and `_stood_stations` after it. 🚫 **Do
    not walk `placements.expanded()` instead**: every panel's end edges read as
    foot there, and it measures **21,499 m** of an 8,850 m fence. Walking the
    unit is also what took this tool's walk from ~620 ms to ~25 ms.

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

    # 🔴 **Both faces are moved onto the mid-line, and the duplicate edges are
    # then dropped by POSITION rather than one face being discarded.** Choosing
    # a face per pair loses the fence wherever two neighbouring stations choose
    # opposite ones — a near foot and a far foot are joined by no triangle — and
    # that read **8,802 m** against the sheet's 8,854 while looking like a
    # plausible small change.
    shift = _mid_shift(keyed, mesh_positions, triangles)

    is_foot = np.zeros(len(mesh_positions), dtype=bool)
    moved = mesh_positions[:, [0, 2]].copy()
    panels: list[float] = []
    for key, rows in keyed.items():
        heights = mesh_positions[rows, 1]
        is_foot[rows[int(np.argmin(heights))]] = True
        if key in shift:
            moved[rows] = np.asarray(key) + shift[key]
        if len(rows) > 1:
            panels.append(float(heights.max() - heights.min()))
    height_m = float(np.median(panels)) if panels else 0.0

    feet: dict[tuple[tuple[float, ...], tuple[float, ...]], tuple[int, int]] = {}
    for triangle in triangles:
        for first, second in ((0, 1), (1, 2), (2, 0)):
            a, b = int(triangle[first]), int(triangle[second])
            if not (is_foot[a] and is_foot[b]):
                continue
            ends = (tuple(np.round(moved[a], 4)), tuple(np.round(moved[b], 4)))
            feet.setdefault((min(ends), max(ends)), (a, b))

    points: list[np.ndarray] = []
    drawn_m = 0.0
    for a, b in feet.values():
        start = moved[a]
        end = moved[b]
        length = float(np.hypot(*(end - start)))
        if length <= 0.0:
            continue
        drawn_m += length
        steps = max(1, round(length / WALK_M))
        for fraction in (np.arange(steps) + 0.5) / steps:
            points.append(start + fraction * (end - start))
    return (np.vstack(points) if points else np.empty((0, 2))), drawn_m, height_m


def _stood_stations(local: np.ndarray, foot_y: float, stands: list[dict]) -> np.ndarray:
    """The unit panel's foot samples, in plan, under every stand.

    `local` is `walk`'s plan points on the unit and `foot_y` the unit's own foot
    height. 🔴 **The height row is the foot's, not zero.** A stand pitches
    about the panel's `+X`, so plan gains `sin(pitch) x y`; seeded at zero the
    samples sat `0.25 x sin(pitch)` off the foot — measured p50 1.1 mm and
    **47 mm** at the steepest 10.9° stand, where the first draft's docstring
    claimed "under a millimetre". Review caught it.
    """
    if not len(local) or not stands:
        return np.empty((0, 2))
    points = np.column_stack([local[:, 0], np.full(len(local), foot_y), local[:, 1]])
    return np.vstack([placed_at(points, entry)[:, [0, 2]] for entry in stands])


def placements(city: Config, region_id: str, out_root: Path | None) -> dict[str, list[dict]]:
    """Every stand in the shipped document, keyed by the class it stands (`P5-5`).

    One read for all classes, on `published()`'s own argument — the document
    is 1 MB, and reading it per class is three answers to one question.
    """
    out_dir = city.out_dir(region_id, out_root)
    document = read_document(
        out_dir / RAILINGS_PLACEMENTS_NAME,
        PLACEMENTS_SCHEMA,
        f"python -m pipeline.railings --region {region_id}",
    )
    by_class: dict[str, list[dict]] = {}
    for entry in document["placements"]:
        by_class.setdefault(str(entry["mesh"]), []).append(entry)
    return by_class


def published(
    city: Config, region_id: str, sources_root: Path | None
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
    city: Config,
    region_id: str,
    klass_id: str,
    source: np.ndarray,
    source_m: float,
    stands: list[dict],
    *,
    near_m: float,
    out_root: Path | None,
) -> Report | None:
    """Grade one class's shipped mesh against its own published source.

    `source` is that class's share of `published()` and `stands` its share of
    `placements()`, both passed in rather than re-read: the layer is one read
    for all classes, and so is the document.

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
            f"`python -m pipeline.railings --region {region_id}` first. "
            "A region whose sources publish no railing layer ships none, and that is not a failure."
        )

    # ⚠️ **This class's panel and no other.** `walk` recovers a fence's feet by
    # grouping vertices that share a plan position and taking the lowest — pool
    # three classes standing at three heights into one pile and the panel
    # heights it medians are a mixture of all three.
    mesh = next((entry for entry in read_glb(path) if entry.name == klass_id), None)
    if mesh is None:
        return None
    # The unit panel is walked once, in its own frame, and every sample is then
    # stood where the document stands the panel (`P5-5`). `drawn_m` is the
    # panel's foot length times the stands, which is `panels x panel_m`.
    report = Report(klass_id=klass_id, source_m=source_m)
    centres = _Centrelines(read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id))
    local, unit_m, report.height_m = walk(mesh.positions, mesh.triangles)
    drawn = _stood_stations(local, float(mesh.positions[:, 1].min()), stands)
    report.drawn_m = unit_m * len(stands)
    report.stations = len(drawn)
    lines = _Nearest(source, max(near_m, 1.0))
    fences = _Nearest(drawn, max(near_m, 1.0))

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
    city = load_config()
    if city.railings is None:
        raise SystemExit(f"city '{city.id}' declares no railings block; nothing to grade")

    # One table per class since `Q61`. Kept as separate tables rather than one
    # pooled figure because that is the whole point of grading a class against
    # its own source: the fence is 90% of the metres, so anything the two small
    # classes did wrong would vanish into its average.
    sources = published(city, args.region, args.sources_root)
    stands = placements(city, args.region, args.out_root)
    for klass in city.railings.classes:
        source, source_m = sources[klass.id]
        report = survey(
            city,
            args.region,
            klass.id,
            source,
            source_m,
            stands.get(klass.id, []),
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
