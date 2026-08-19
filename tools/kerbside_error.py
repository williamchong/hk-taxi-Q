"""How much of the game's kerbside yellow the source actually supports (`P3-13`).

Grades the **shipped bundle**, not the pipeline's intentions. `roads.glb` is
read back, every carriageway triangle is asked where the shader's yellow line
crosses it, and the metres that come out are compared against the runs
`roadgraph.json` publishes. Before `P3-13` drew anything, that ratio is the
size of `Q54`: a double yellow on every kerb in the region against the third of
it the source restricts.

**What this sees that nothing else can.** The join lives in
`pipeline/kerbside.py` and the paint lives in a shader, and between them are
four places to be wrong that neither side can inspect:

- the extent is written on the wrong **rail**, mirroring every line in the city;
- `COLOR_0.a` does not survive the glTF round trip, so every kerb paints or none
  does;
- the runs are published against the graph's polyline and drawn against the
  **trimmed** ribbon, so an edge's lines slide by its junction trim;
- the shader's own `draw_double_yellow` is turned down, and the city quietly
  stops asserting anything.

Each of those renders as a road. This is the instrument that reads a number
instead.

⚠️ **This does not check the join, and must not be quoted as though it did.**
The truth side is what `roadgraph.json` publishes, so a restriction attached to
the wrong centreline is agreed with rather than caught. Two other things cover
that: `tests/test_kerbside.py` pins the side convention on a fixture with a
known side, and the stage's own log reports source metres against published
metres. What is graded here is the half of the path that runs from the published
run to the pixel.

⚠️ **The tuning is read from `game/tuning/road_markings.tres`, never from the
shader's defaults.** The `.tres` is what ships (CLAUDE.md hard rule 4), and a
tool grading the defaults would report paint the game does not draw.

⚠️ **The region's own build output is what is graded, not the copy under
`game/assets/generated/`.** `tools/sync_generated.sh` mirrors one to the other
verbatim, so they are the same bytes — but `roadsurface.json` carries the
junction trims and does not ship, and without those a published run cannot be
converted into the V the ribbon is actually drawn at.

Run:  .venv/bin/python tools/kerbside_error.py --city hong_kong --region wan_chai
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline import kerbside  # noqa: E402
from pipeline.config import load_city  # noqa: E402
from pipeline.documents import read_document  # noqa: E402
from pipeline.fares import FARES_NAME, FARES_SCHEMA  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402
from pipeline.surface import (  # noqa: E402
    MARKING_CENTRE,
    MARKING_CLASS_CARRIAGEWAY,
    MARKING_DIRECTION,
    MARKING_LANES,
    MARKING_OFFSIDE_KERB,
    SURFACE_MANIFEST_NAME,
    SURFACE_MANIFEST_SCHEMA,
)

log = logging.getLogger(__name__)

# The `.tres` values this tool needs, and what it does without them. A missing
# key is the file being edited, not a reason to guess — every one of these
# changes the answer, so the tool exits rather than reporting a plausible number
# against tuning the game is not using.
_TUNING = ("yellow_inset", "fade_m", "fade_softness_m", "draw_double_yellow")
_PARAMETER = re.compile(r"^shader_parameter/(\w+)\s*=\s*([-\d.eE]+)\s*$", re.MULTILINE)

# Pitch both sides of the comparison integrate the junction fade at, in metres.
# A tenth of the join's own 1 m resolution, so the 3 m fade ramp is resolved
# rather than sampled at its ends.
_INTEGRATION_M = 0.1

# Two triangle corners whose U values straddle the line by less than this are
# treated as lying on it, and the chord is skipped. Below it the crossing point
# is the ratio of two numbers that are both noise.
_MIN_U_SPAN = 1e-9


@dataclass
class Sides:
    """One measurement, kept per side because a mirrored convention is the
    failure this exists to find and it is invisible in a total."""

    near: float = 0.0
    off: float = 0.0

    def add(self, side: str, metres: float) -> None:
        if side == kerbside.NEARSIDE:
            self.near += metres
        else:
            self.off += metres

    @property
    def total(self) -> float:
        return self.near + self.off


@dataclass
class Report:
    painted: Sides = field(default_factory=Sides)
    restricted: Sides = field(default_factory=Sides)
    # Per `(edge, side)`: painted, restricted, drawable. Kept per pair rather
    # than summarised, because a gross ratio near 1 can still be every line in
    # the wrong place — and this table is the only thing that would say so.
    by_side: dict[tuple[int, str], list[float]] = field(default_factory=dict)
    # Metres of restriction `roadgraph.json` publishes, before any of it is
    # clipped to what the ribbon draws. The gap to `restricted` is junction
    # trims and the marking fade, and it is a floor nothing here can lower.
    published: float = 0.0
    # Taxi stands, and how many sit inside a published restriction. `Q54` argued
    # the game paints no-stopping over its own fare nodes; this is that argument
    # measured against the source rather than against the invention.
    stands: int = 0
    stands_restricted: int = 0

    def add(self, edge: int, side: str, painted: float, restricted: float, drawable: float) -> None:
        row = self.by_side.setdefault((edge, side), [0.0, 0.0, 0.0])
        row[0] += painted
        row[1] += restricted
        row[2] += drawable

    @property
    def unreachable_m(self) -> float:
        """Restriction on a kerb the drawn city does not have.

        The 1.6x play widening makes two parallel ribbons overlap, so the kerb
        between them is paved over and `MARKING_OFFSIDE_KERB` says — correctly —
        that `U = lanes` is not a kerb there. Gloucester Road, Lung Wo Road and
        Harbour Drive are most of it. No shader change reaches this, so it is
        reported on its own line rather than folded into missed paint, where it
        would put a floor under the error that correct work could never clear.
        """
        return sum(max(0.0, row[1] - row[2]) for row in self.by_side.values())

    @property
    def reachable_m(self) -> float:
        return sum(min(row[1], row[2]) for row in self.by_side.values())

    @property
    def unsourced_m(self) -> float:
        """What `P3-12` asserted: a line on every kerb the city draws.

        Computable from this same run because `drawable` *is* that city — the
        metres of kerb line the mesh could carry if the extent said yes
        everywhere, which is exactly what it said before `P3-13`. Reported so
        the before and the after come off one measurement of one mesh rather
        than out of two runs someone has to trust were comparable.
        """
        return sum(max(0.0, row[2] - row[1]) for row in self.by_side.values())

    @property
    def over_m(self) -> float:
        return sum(max(0.0, row[0] - row[1]) for row in self.by_side.values())

    @property
    def missed_m(self) -> float:
        return sum(max(0.0, min(row[1], row[2]) - row[0]) for row in self.by_side.values())

    @property
    def gross_error(self) -> float:
        """Over-paint plus missed paint, against the length that could exist.

        The two are added rather than netted: a metre painted where nothing is
        restricted and a metre restricted and left bare are both wrong, and
        letting them cancel would report a city with every line in the wrong
        place as correct.
        """
        return (self.over_m + self.missed_m) / max(self.reachable_m, 1e-9)


def fade(v: np.ndarray, drawn_m: np.ndarray, fade_m: float, softness_m: float) -> np.ndarray:
    """The shader's `away`, reproduced here because the metric needs the same
    curve on both sides of the comparison.

    `smoothstep` written out rather than approximated by a step: the ramp is 3 m
    of every junction approach and there are 1,398 of them, so treating it as a
    hard edge would cost about 4 km of the region's answer.
    """
    edge = np.clip(
        (np.minimum(v, drawn_m - v) - (fade_m - softness_m)) / max(softness_m, 1e-9), 0.0, 1.0
    )
    return edge * edge * (3.0 - 2.0 * edge)


def painted_lines(
    mesh, tuning: dict[str, float]
) -> list[tuple[np.ndarray, str, float, float, float]]:
    """Where the shader draws a line, as `(midpoint, side, painted, drawable, drawn_m)`.

    The line is the locus `U = yellow_inset` on the nearside and
    `U = lanes - yellow_inset` on the offside, so every carriageway triangle is
    clipped against it and the chord's length is taken **in V**, which is metres
    along the road by construction. No strip has to be reconstructed and no
    vertex has to be matched to its partner — which matters, because
    `_Builder.build` drops collapsed triangles and the merge scrambles any
    ordering a reader might otherwise lean on.

    Two lengths come back, and the second is what makes the first readable.
    `painted` is weighted by the junction fade *and* by `COLOR_0.a`, which is
    where `P3-13` writes the extent — it is the paint. `drawable` is weighted by
    the fade alone: the metres this kerb could carry a line on if the source
    restricted every one of them. Their difference is the extent doing its job;
    a restriction published where `drawable` is zero is one the drawn city has
    nowhere to put, which is a different failure from paint in the wrong place
    and must not be added to it.
    """
    if mesh.uvs is None or mesh.uv2 is None or mesh.colours is None:
        raise SystemExit(f"mesh '{mesh.name}' is missing a channel this tool reads")

    packed = np.floor(mesh.uv2[:, 0] + 0.5)
    surface_class = np.mod(packed, MARKING_LANES)
    lanes = np.floor(np.mod(packed / MARKING_LANES, MARKING_DIRECTION / MARKING_LANES))
    offside = np.floor(np.mod(packed / MARKING_OFFSIDE_KERB, MARKING_CENTRE / MARKING_OFFSIDE_KERB))
    alpha = mesh.colours[:, 3].astype(np.float64) / 255.0

    corners = mesh.triangles
    carriageway = (surface_class[corners] == MARKING_CLASS_CARRIAGEWAY).all(axis=1)
    corners = corners[carriageway]

    inset = tuning["yellow_inset"]
    found: list[tuple[np.ndarray, str, float, float, float]] = []
    for side, at in (
        (kerbside.NEARSIDE, lambda row: np.full(3, inset)),
        (kerbside.OFFSIDE, lambda row: lanes[row] - inset),
    ):
        for row in corners:
            if side == kerbside.OFFSIDE and offside[row][0] < 0.5:
                # Not a known kerb. The shader folds the offside onto the
                # nearside only where the ETL says there is one, so nothing is
                # drawn here and nothing should be counted.
                continue
            chord = _chord(mesh, row, at(row), alpha, tuning)
            if chord is not None:
                found.append((chord[0], side, chord[1], chord[2], chord[3]))
    return found


def _chord(mesh, row, at: np.ndarray, alpha: np.ndarray, tuning: dict[str, float]):
    """One triangle's crossing of the line at `at`, or `None` if it misses.

    Returns the crossing's 3D midpoint, the metres of paint on it, the metres of
    kerb line that could have been painted there, and the drawn length of the
    edge it belongs to — which is how the caller tells that edge from its
    neighbours.
    """
    u = mesh.uvs[row, 0] - at
    v = mesh.uvs[row, 1]
    hits: list[tuple[float, float, np.ndarray]] = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        span = u[a] - u[b]
        if abs(span) < _MIN_U_SPAN or (u[a] > 0.0) == (u[b] > 0.0):
            continue
        t = u[a] / span
        hits.append(
            (
                float(v[a] + t * (v[b] - v[a])),
                float(alpha[row[a]] + t * (alpha[row[b]] - alpha[row[a]])),
                mesh.positions[row[a]] + t * (mesh.positions[row[b]] - mesh.positions[row[a]]),
            )
        )
    if len(hits) != 2:
        return None

    (v0, alpha0, point0), (v1, alpha1, point1) = hits
    drawn_m = float(mesh.uv2[row[0], 1])
    length = abs(v1 - v0)

    # ⚠️ **Integrated along the chord, never sampled at its midpoint.** A
    # triangle here is not small: 204 of the region's edges carry two stations,
    # so one triangle spans the whole ribbon and its chord runs end to end. The
    # midpoint of such a chord sits exactly where the junction fade is 1, which
    # weighed a 12.6 m edge at 12.0 m when the truth is 3.6 — the fade is a
    # curve over the very interval being measured. Same pitch as
    # `restricted_metres`, so both sides of the comparison resolve the 3 m ramp
    # the same way.
    steps = max(2, int(length / _INTEGRATION_M))
    at = (np.arange(steps) + 0.5) / steps
    weight = fade(
        v0 + at * (v1 - v0),
        np.full(steps, drawn_m),
        tuning["fade_m"],
        tuning["fade_softness_m"],
    )
    # The alpha is integrated raw where the shader passes it through a
    # `smoothstep(0.4, 0.6, ...)`. Deliberate, and it costs nothing: over the
    # half-metre ramp the ETL builds, both are symmetric about 0.5 and integrate
    # to the same length, and everywhere else the value is already 0 or 1. What
    # it buys is one less shader constant this tool has to be kept in step with.
    extent = alpha0 + at * (alpha1 - alpha0)
    drawable = length * float(weight.mean())
    painted = length * float((weight * extent).mean()) * tuning["draw_double_yellow"]
    return (point0 + point1) * 0.5, painted, drawable, drawn_m


# How heavily a height difference counts against a plan distance when a painted
# line is matched back to the edge it was drawn from. Not a tolerance — the
# region has a flyover directly over the street it shadows, and the two are the
# same place in plan. Any weight above zero separates them; this one keeps the
# match plan-led where nothing is stacked.
_HEIGHT_WEIGHT = 4.0

# How closely a candidate edge's drawn length must match the one the mesh
# carries in `TEXCOORD_1.y` to be considered the same edge. Millimetres, because
# that is what the manifest rounds its trims to and what float32 holds at this
# region's scale.
_DRAWN_TOLERANCE_M = 0.01


class _Attributor:
    """Which edge a point on the drawn road came from, height included.

    A plan-only nearest is not enough here and the reason is specific: Canal
    Road flyover runs directly over Canal Road, so a yellow line drawn on the
    flyover's kerb is *plan-identical* to one on the street. Painted metres
    attributed to the wrong one would report over-paint on a street that has
    none and hide it on a viaduct that does.

    Deliberately not the pipeline's own segment index: that one is plan-only on
    purpose, because an `NSR` line has no height to compare with. This one is
    matching drawn geometry, which does.

    ⚠️ **Position is the weaker half of this, and the mesh carries the stronger
    one.** A yellow line sits half a carriageway off its own centreline, which
    on a road drawn as several parallel edges can put it nearer a neighbour's —
    position alone attributed 416 m of paint to a 191 m stretch of Gloucester
    Road. But `TEXCOORD_1.y` is that edge's *drawn length*, which is very nearly
    a fingerprint: filtering candidates by it first and only then taking the
    nearest is what makes the per-edge table mean anything.
    """

    cell_m = 25.0

    def __init__(self, edges: list[dict], trims: dict[int, tuple[float, float]]) -> None:
        starts, ends, heights, ids, drawn = [], [], [], [], []
        for edge in edges:
            points = np.asarray(edge["polyline"], dtype=np.float64)
            if len(points) < 2:
                continue
            trim = trims.get(edge["id"], (0.0, 0.0))
            length = float(np.hypot(*np.diff(points[:, [0, 2]], axis=0).T).sum())
            starts.append(points[:-1])
            ends.append(points[1:])
            heights.append(0.5 * (points[:-1, 1] + points[1:, 1]))
            ids.append(np.full(len(points) - 1, edge["id"]))
            drawn.append(np.full(len(points) - 1, length - trim[0] - trim[1]))
        self.drawn = np.concatenate(drawn)
        self.start = np.vstack(starts)[:, [0, 2]]
        self.step = np.vstack(ends)[:, [0, 2]] - self.start
        self.height = np.concatenate(heights)
        self.edge = np.concatenate(ids)
        self.length_squared = np.maximum((self.step**2).sum(axis=1), 1e-9)

        buckets: dict[tuple[int, int], list[int]] = {}
        low = np.minimum(self.start, self.start + self.step)
        high = np.maximum(self.start, self.start + self.step)
        for index, (lo, hi) in enumerate(zip(low, high, strict=True)):
            for x in range(int(lo[0] // self.cell_m), int(hi[0] // self.cell_m) + 1):
                for z in range(int(lo[1] // self.cell_m), int(hi[1] // self.cell_m) + 1):
                    buckets.setdefault((x, z), []).append(index)
        self.buckets = {key: np.array(value) for key, value in buckets.items()}

    def edge_of(self, point: np.ndarray, drawn_m: float) -> int | None:
        x, z = int(point[0] // self.cell_m), int(point[2] // self.cell_m)
        near = [
            self.buckets[(x + dx, z + dz)]
            for dx in (-1, 0, 1)
            for dz in (-1, 0, 1)
            if (x + dx, z + dz) in self.buckets
        ]
        if not near:
            return None
        candidates = np.unique(np.concatenate(near))
        # The fingerprint first. Kept as a filter rather than a requirement: two
        # neighbouring edges can be drawn to the same length, and a chord that
        # matches nothing nearby is better attributed by position than dropped.
        matched = candidates[np.abs(self.drawn[candidates] - drawn_m) <= _DRAWN_TOLERANCE_M]
        if len(matched):
            candidates = matched
        plan = point[[0, 2]] - self.start[candidates]
        travel = np.clip(
            (plan * self.step[candidates]).sum(axis=1) / self.length_squared[candidates], 0.0, 1.0
        )
        gap = np.hypot(*(plan - travel[:, None] * self.step[candidates]).T)
        score = gap + _HEIGHT_WEIGHT * np.abs(self.height[candidates] - point[1])
        return int(self.edge[candidates[int(np.argmin(score))]])


def restricted_metres(
    edge: dict, trims: tuple[float, float], tuning: dict[str, float]
) -> dict[str, float]:
    """Metres of this edge's published runs that fall inside what is drawn,
    weighted by the same junction fade the shader applies.

    Clipped to the drawn extent rather than compared against the whole edge: a
    restriction under a junction cap is one no marking shader can show, and
    counting it as missing paint would put a floor under the error that no
    amount of correct work could reach.
    """
    points = np.asarray(edge["polyline"], dtype=np.float64)
    length = float(np.hypot(*np.diff(points[:, [0, 2]], axis=0).T).sum())
    drawn_m = length - trims[0] - trims[1]
    totals = {kerbside.NEARSIDE: 0.0, kerbside.OFFSIDE: 0.0}
    if drawn_m <= 0.0:
        return totals

    for run in edge["kerbside"]:
        low = max(run["from_m"], trims[0])
        high = min(run["to_m"], length - trims[1])
        if high <= low:
            continue
        # Integrated numerically at `_INTEGRATION_M`, the same pitch `_chord`
        # uses on the other side of the comparison.
        at = np.arange(low - trims[0] + _INTEGRATION_M / 2, high - trims[0], _INTEGRATION_M)
        totals[run["side"]] += float(
            fade(at, np.full(len(at), drawn_m), tuning["fade_m"], tuning["fade_softness_m"]).sum()
            * _INTEGRATION_M
        )
    return totals


def stands_in_restriction(fares: dict, edges: dict[int, dict]) -> tuple[int, int, list[str]]:
    """Taxi stands, and how many stand inside a published no-stopping run.

    `Q54` argued the game paints no-stopping over its own fare nodes. That was
    measured against the invention, before the overlapping source features were
    deduped — one stand read 110% covered — so it is re-asked here of the
    published runs, where a metre can only be counted once.

    Either side counts. A stand's own side is knowable from its position, but
    the fare node is snapped to the centreline and its offset is small enough
    that the sign is not reliable; a stand inside a restriction on *either* kerb
    is the honest reading of "the source says the line runs past it".
    """
    total = 0
    covered = 0
    names: list[str] = []
    for node in fares["nodes"]:
        if node["kind"] != "taxi_stand":
            continue
        total += 1
        edge = edges.get(node["nearest_edge"])
        if edge is None:
            continue
        points = np.asarray(edge["polyline"], dtype=np.float64)
        length = float(np.hypot(*np.diff(points[:, [0, 2]], axis=0).T).sum())
        at = node["edge_t"] * length
        if any(run["from_m"] <= at <= run["to_m"] for run in edge["kerbside"]):
            covered += 1
            names.append(node["name"]["en"])
    return total, covered, names


def tuning_from(path: Path) -> dict[str, float]:
    """The shipped `.tres`'s shader parameters, refusing a missing one."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(
            f"{path} does not exist; this tool grades the tuning the game ships"
        ) from None
    found = {name: float(value) for name, value in _PARAMETER.findall(text)}
    missing = [name for name in _TUNING if name not in found]
    if missing:
        raise SystemExit(f"{path} declares no {', '.join(missing)}")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--out-root",
        type=Path,
        default=None,
        help="the build output to grade (default: the region's own out dir)",
    )
    parser.add_argument(
        "--tuning",
        type=Path,
        default=ROOT / "game" / "tuning" / "road_markings.tres",
        help="the shader tuning the game ships",
    )
    parser.add_argument("--worst", type=int, default=12, help="edge sides to name (default: 12)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    tuning = tuning_from(args.tuning)
    city = load_city(args.city)
    out_dir = city.out_dir(args.region, args.out_root)
    rebuild = f"python -m pipeline --city {city.id} --region {args.region}"
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, args.region)
    surface = read_document(out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, rebuild)
    fares = read_document(out_dir / FARES_NAME, FARES_SCHEMA, rebuild)

    trims = {row["edge"]: tuple(row["trim_m"]) for row in surface["carriageway"]}
    edges = {edge["id"]: edge for edge in graph["edges"]}
    if not edges or "kerbside" not in next(iter(edges.values())):
        raise SystemExit(f"{out_dir / ROADGRAPH_NAME} publishes no kerbside runs")

    report = Report()
    report.published = sum(
        run["to_m"] - run["from_m"] for edge in edges.values() for run in edge["kerbside"]
    )
    for edge_id, edge in edges.items():
        for side, metres in restricted_metres(edge, trims[edge_id], tuning).items():
            report.restricted.add(side, metres)
            report.add(edge_id, side, 0.0, metres, 0.0)

    attribute = _Attributor(graph["edges"], trims)
    for mesh in read_glb(out_dir / surface["mesh"]):
        for point, side, metres, drawable, drawn_m in painted_lines(mesh, tuning):
            report.painted.add(side, metres)
            edge_id = attribute.edge_of(point, drawn_m)
            if edge_id is not None:
                report.add(edge_id, side, metres, 0.0, drawable)

    report.stands, report.stands_restricted, names = stands_in_restriction(fares, edges)
    _log(report, args.worst, names, tuning)
    return 0


def _log(report: Report, worst: int, names: list[str], tuning: dict[str, float]) -> None:
    log.info("kerbside yellow, as drawn against as published")
    log.info(
        "  tuning: yellow_inset %.3f lanes, fade %.1f m over %.1f m, draw_double_yellow %.2f",
        tuning["yellow_inset"],
        tuning["fade_m"],
        tuning["fade_softness_m"],
        tuning["draw_double_yellow"],
    )
    log.info(
        "  %.0f m published; %.0f m of it inside what the ribbon draws, after the junction "
        "trims and the %.0f m marking fade",
        report.published,
        report.restricted.total,
        tuning["fade_m"],
    )
    log.info("  %-12s %10s %10s %10s", "", "nearside", "offside", "total")
    log.info(
        "  %-12s %10.0f %10.0f %10.0f",
        "painted",
        report.painted.near,
        report.painted.off,
        report.painted.total,
    )
    log.info(
        "  %-12s %10.0f %10.0f %10.0f",
        "restricted",
        report.restricted.near,
        report.restricted.off,
        report.restricted.total,
    )
    log.info(
        "  %.0f m of the restriction is on a kerb the drawn city does not have "
        "(the widening paved it over); %.0f m is reachable",
        report.unreachable_m,
        report.reachable_m,
    )
    log.info(
        "  over-painted %.0f m, missed %.0f m -> gross error %.0f%% of the reachable %.0f m",
        report.over_m,
        report.missed_m,
        100.0 * report.gross_error,
        report.reachable_m,
    )
    log.info(
        "  a line on every kerb — what `P3-12` asserted — would over-paint %.0f m: %.0f%%",
        report.unsourced_m,
        100.0 * report.unsourced_m / max(report.reachable_m, 1e-9),
    )
    log.info(
        "  %d of %d taxi stands stand inside a published restriction",
        report.stands_restricted,
        report.stands,
    )
    for name in names[:worst]:
        log.info("    %s", name)

    # Ranked by the error this actually counts, not by `painted - restricted`:
    # the largest raw gaps are all restrictions on a kerb the city does not
    # draw, which have their own line above and are nobody's fault to fix.
    def counted(row: list[float]) -> float:
        return max(0.0, row[0] - row[1]) + max(0.0, min(row[1], row[2]) - row[0])

    ranked = sorted(report.by_side.items(), key=lambda item: -counted(item[1]))[:worst]
    ranked = [item for item in ranked if counted(item[1]) > 0.5]
    if ranked:
        log.info("  worst edge sides by counted error:")
        log.info(
            "    %-8s %-5s %10s %10s %10s %10s",
            "edge",
            "side",
            "painted",
            "restr.",
            "drawable",
            "error",
        )
        for (edge_id, side), (painted, restricted, drawable) in ranked:
            log.info(
                "    %-8d %-5s %10.1f %10.1f %10.1f %+10.1f",
                edge_id,
                side,
                painted,
                restricted,
                drawable,
                painted - restricted,
            )


if __name__ == "__main__":
    raise SystemExit(main())
