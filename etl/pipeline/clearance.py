"""How much of each carriageway station a car can actually get through (`Q51`).

    python -m pipeline.clearance --region wan_chai

`Q19` measured that solid geometry stands in the drawn carriageway and stopped
there, deliberately: it grades the shipped bundle and publishes nothing. But
`RoadGraph` routes on edges, and `P3-3`'s traffic has to be told which edges it
must never be sent down. That is a fact about the built city, so the pipeline
owes it as *data* — this stage measures it and `export.py` carries the result
into `city.json` beside the drawn half-width, which reaches the game by the same
route and for the same reason (`Q23`, `P2-2`).

**What is measured.** A cross-section every `ALONG_M` along every drivable
level-0 edge, reported at the nearest station, spanning the carriageway
`surface.py` actually drew there. A sample across
that section is blocked where an occupier's geometry stands between
`BUMPER_LOW_M` and `BUMPER_HIGH_M` above the deck, so a podium overhanging the
street six metres up is Hong Kong working as intended. The station's clearance
is the widest continuous unblocked run — not the unblocked total, because a car
needs one gap it fits through rather than two halves of one.

⚠️ **This is not an independent check of `Q19`, and must not be quoted as one.**
`tools/carriageway_occupancy.py` grades what this publishes, and the two are
independent in implementation and in inputs — this reads the graph's own
`polyline.y` for the deck and the classes the config names, where the tool
samples `roads.glb` and infers class from shipped vertex colours — but they are
not independent in *method*. They cannot be. A wall at bumper height projects to
a line in plan, so no footprint test finds it (`Q19` says the same thing about
vertical rays), while a footprint-plus-height-span test would mark the whole area
*under a flyover* as blocked, which is the bounding-box error that first read
13.71%. Asking what surfaces stand in the band is the only formulation that
survives both, so both instruments ask it.

⚠️ **The occupier subdivision is by *plan* extent, never by area.** A building
wall is one triangle a hundred metres tall and centimetres wide in plan; an
expressway ramp face is the reverse. Splitting by edge length would shatter the
first into thousands of pieces to no purpose and leave the second whole, taking
its full height range across a plan footprint it only touches at one end. A piece
is at most `SUBDIVIDE_M` across in plan and as tall as it likes, which is what
makes taking its whole height range over the cells it covers both cheap and
honest — ⚠️ except where `MAX_SUBDIVISIONS` caps the split, which on this region
is 9,779 triangles a run and is where this stage over-blocks hardest.

⚠️ **A station the ribbon never reached is not a starved station.** `surface.py`
holds each end back so a junction cap can fill the middle, and the nominal
corridor still has a published width there. Judging those cross-sections is what
condemned 18 innocent edges in `Q19` — 44 failures where there were 26 — so the
trims travel in `roadsurface.json` since schema 4 and the stations outside them
are published as `NOT_MEASURED` rather than as zero.

Nothing here knows a Hong Kong fact: the bar, the classes and the region all
arrive from `config/hong_kong.yaml`.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import numpy as np

from pipeline import gltf
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA
from pipeline.config import (
    GAME_ROOT,
    LANDMARK_ASSET_ROOT,
    LANDMARK_GENERATED_ROOT,
    Config,
    load_config,
)
from pipeline.documents import read_document, write_document
from pipeline.landmarks import landmark_in_region
from pipeline.polyline import plan_lengths
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

CLEARANCE_NAME = "clearance.json"
CLEARANCE_SCHEMA = 1

# The band a car occupies, in metres above the deck. `Q19`'s numbers are taken
# over exactly this band and the two instruments have to agree about it, so the
# figures stay comparable — change one and the other is measuring something else.
BUMPER_LOW_M = 0.30
BUMPER_HIGH_M = 2.00

# Spacing of the samples across a cross-section, and so the resolution of every
# width this stage publishes: a run of `n` clear samples is `n * ACROSS_M` wide.
# Finer than the tool's 0.5 m because the answer here is a published number
# rather than a table to read, and a lane bar of 3.20 m deserves better than
# being rounded to the nearest half metre.
ACROSS_M = 0.25

# The largest plan extent of one occupier piece. Below this a piece's height
# range is tight enough over its own plan box that taking the whole of it across
# every cell the box touches is honest rather than a smear.
SUBDIVIDE_M = 0.5

# The plan cell a piece is matched to a cross-section sample through. Equal to
# `SUBDIVIDE_M` so a piece usually lands in the four cells its box touches —
# usually, not always, which is why `_emit` rasterises the box in full: the
# subdivision cap can leave a piece wider than a cell.
CELL_M = SUBDIVIDE_M

# Spacing of the cross-sections along an edge, and **`CELL_M` rather than a value
# of its own, because the equality is the whole argument**. Occupiers are binned
# in plan at `CELL_M`, so a walk stepping at cell pitch cannot stride over a cell
# without sampling it — on axis. Every other error here over-blocks, which is what
# makes a published width a lower bound; the spacing was the one exception,
# because a wall standing between two cross-sections is not smeared but *missed*,
# and a missed wall reads as clear road that `RoadGraph.is_routable` then hands a
# car. ⚠️ Written as `CELL_M` and not as `0.5` so that moving `SUBDIVIDE_M` cannot
# leave this behind: nothing else checks the match, and losing it would retire the
# bound while every comment here still claimed it.
#
# ⚠️ It read 1.0 until `Q51`, and over that period the published widths were
# **not** a lower bound. Swept with `--along-m` on the same bundle: **21 starved
# edges at 1.00 m, 24 at 0.50 m and 25 at 0.25 m**, and `e636` HARBOUR ROAD — one
# of the six edges the grader condemned and this stage cleared — went from
# passable to **0.00 m clear**. There the grader was simply right.
#
# ⚠️ **One residue survives, and it is why 0.25 m finds one edge more.** The cells
# are axis-aligned in plan and an edge runs at whatever angle it likes, so a
# diagonal walk stepping 0.50 m advances 0.35 m in each of x and z and can
# corner-cross a cell without landing in it — `e520` TONNOCHY ROAD, 4.50 m here
# against 2.50 m at 0.25 m.
#
# ⚠️ **Below `CELL_M` the extra samples mostly land in cells already sampled**, and
# that is the argument for stopping here rather than the cost. Unique plan cells
# reached go 846,087 at 1.0 m to 1,461,818 at 0.5 m — and then to 1,478,556 at
# 0.25 m, **+1.1% for twice the samples**. All a finer walk buys against this cell
# index is depth within a cell, at a peak **1.088 GB** RSS against this one's
# 789 MB, back toward the 1.64 GB `PIECE_BUDGET` exists to cut.
# `tools/clearance_reconcile.py` holds the counts, so neither the fix nor the
# residue can go quiet.
ALONG_M = CELL_M

# Plan cell of the coarse occupancy grid the prune tests against. Coarser than
# `CELL_M` because it only has to answer "could this triangle be near any
# carriageway at all", and a road is a small share of a city's plan area — the
# region's whole ground is 1.7 km2 and its drawn carriageway is a fraction of it.
COARSE_M = 2.0

# Pieces held in flight at once. Without it the whole of one mesh is subdivided
# and rasterised in a single breath, and the biggest is a hero: 2.1 M pieces and
# 6.9 M cell rows, which put peak RSS at 1.64 GB — more than the buildings stage,
# the longest in the pipeline. A budget on *pieces* rather than on triangles is
# what actually bounds it, because `MAX_SUBDIVISIONS` means 3,773 triangles can
# produce 763,000 pieces. Measured when it went in: 1.64 GB -> 482 MB, and not a
# second slower. ⚠️ Neither is today's peak — `ALONG_M` has halved since, and the
# stage now runs at 789 MB.
PIECE_BUDGET = 64_000

# Pieces per triangle are capped, so a single enormous face cannot turn one
# triangle into a hundred thousand. 32 across covers a 16 m plan span at
# `SUBDIVIDE_M`.
#
# ⚠️ This comment used to end "anything wider than that in plan is ground, and
# ground is excluded below". **Counted, that is 9,779 triangles per run** — hero
# meshes and long ramp faces, none of them ground. Each keeps pieces wider than
# `CELL_M`, and `_emit` then blocks by the piece's plan box at its *whole* height
# range, so this is where the stage over-blocks hardest. `_plan_steps` returns the
# count and `build_region` warns it, because a smear nobody counts reads as a wall.
MAX_SUBDIVISIONS = 32

# What a station whose ribbon was trimmed away publishes. Negative because no
# real clearance can be, so a consumer that forgets to check it gets an obviously
# wrong answer rather than a plausible zero — and zero is the one value that
# would read as "blocked solid" on precisely the stations that are not.
NOT_MEASURED = -1.0


@dataclass
class ClearanceReport:
    """What one region's measurement found."""

    # Clear width in metres per station, keyed by graph edge id, one value per
    # station of that edge's published polyline. `NOT_MEASURED` where the ribbon
    # did not reach.
    corridor_m: dict[int, list[float]] = field(default_factory=dict)
    edges: int = 0
    # Cross-sections, not stations: `ALONG_M` decides these and the graph's own
    # vertices decide the stations they are reported at.
    sections_measured: int = 0
    sections_trimmed: int = 0
    # Triangles that reached the band, of those read. A collapse in the first
    # would mean the prune had started throwing away occupiers rather than that
    # the city had cleared itself up.
    occupier_triangles: int = 0
    occupier_pieces: int = 0
    # Triangles `MAX_SUBDIVISIONS` held back from reaching `SUBDIVIDE_M` in plan,
    # each of which then blocks by a box carrying its whole height range. This
    # stage's own smear, and the direction it over-blocks in — see `_plan_steps`.
    occupier_clipped: int = 0
    tiles_read: int = 0
    landmarks_read: int = 0
    # The spacing the cross-sections were taken at. Carried so `_write` can refuse
    # to publish a sweep — see `ALONG_M` — rather than trusting every caller of
    # `build_region` to remember that only the shipped value may reach the bundle.
    along_m: float = ALONG_M

    def count(self, occupancy: _Occupancy) -> None:
        """Fold one `occupy` pass into the running totals."""
        self.occupier_triangles += occupancy.triangles
        self.occupier_pieces += occupancy.pieces
        self.occupier_clipped += occupancy.clipped

    def tightest(self) -> dict[int, float]:
        """The narrowest measured station of every edge that has one.

        Refusals are filtered before the `min`, never clamped after: `-1.0` is
        the narrowest number in any row it appears in, so folding it would make
        every part-trimmed edge the most blocked in the region.
        """
        return {
            edge_id: min(width for width in widths if width != NOT_MEASURED)
            for edge_id, widths in self.corridor_m.items()
            if any(width != NOT_MEASURED for width in widths)
        }

    def starved(self, bar_m: float) -> list[tuple[int, float]]:
        """Edges whose tightest measured station is under `bar_m`, worst first."""
        found = (row for row in self.tightest().items() if row[1] < bar_m)
        return sorted(found, key=lambda row: row[1])


@dataclass(frozen=True)
class Corridor:
    """Every cross-section sample in the region, as flat parallel arrays.

    One array set rather than a nest of per-edge lists for the same reason
    `tools/carriageway_occupancy.py` keeps a `Lattice`: the occupier pass below
    is a single vectorised sweep over all of them at once, and a million rows is
    tens of megabytes this way and several times that as Python objects.

    Samples of one cross-section are contiguous, so `section_count` is enough to
    cut them apart again — no per-sample section id has to be carried.
    """

    x: np.ndarray  # (n,) float64 — plan position of one sample
    z: np.ndarray  # (n,) float64
    deck_y: np.ndarray  # (n,) float64 — the graph's own height at that station
    section_count: np.ndarray  # (s,) int64 — samples in each cross-section
    section_edge: np.ndarray  # (s,) int32 — graph edge id
    section_station: np.ndarray  # (s,) int32 — polyline vertex it is reported at
    section_width: np.ndarray  # (s,) float64 — the drawn carriageway there

    def band(self) -> tuple[np.ndarray, np.ndarray]:
        return self.deck_y + BUMPER_LOW_M, self.deck_y + BUMPER_HIGH_M

    def __len__(self) -> int:
        return len(self.x)


# --------------------------------------------------------------------------
# The walk: where the carriageway is, and how wide it was drawn
# --------------------------------------------------------------------------


def _spread(counts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Expand per-group counts into a group index and a position within it."""
    total = int(counts.sum())
    group = np.repeat(np.arange(len(counts)), counts)
    within = np.arange(total) - np.repeat(np.cumsum(counts) - counts, counts)
    return group, within


def walk(
    graph: dict,
    drawn: dict[int, dict],
    *,
    along_m: float = ALONG_M,
    levels: tuple[int, ...] = (0,),
) -> tuple[Corridor, ClearanceReport]:
    """Every cross-section of every drivable level-0 edge, at `along_m` spacing.

    🔴 **`levels` exists so a TOOL can measure off-grade without the bundle
    changing, and the default must stay `(0,)`.** What ships is level 0, because
    `Q13` closed the off-grade network to driving and its clearance is `P4-1`'s
    question. Moving this default re-publishes `city.json` and changes what
    `roadgraph.json` carries for 60 edges, which is the user's call and not a
    parameter's — so the parameter buys the measurement without buying the
    republish. ⚠️ **A wider `levels` is still not a runtime change on its own**:
    `RoadGraph.is_drivable` is level 0 too, and both `impassable_edge_ids` and
    `fenced_edge_ids` filter through it, so an off-grade clearance is inert
    until `P4-1` reverses that as well.

    ⚠️ **`along_m` is the one dimension this stage can be *wrong* in rather than
    merely coarse** — everything else over-blocks, where a spacing too coarse to
    reach a wall *misses* it. `ALONG_M` carries why the shipped value bounds that,
    and the residue that survives. It stays a parameter so the cost of the choice
    remains measurable rather than assumed; sweeping it does not publish, see
    `main`.

    `drawn` is `roadsurface.json`'s carriageway table, keyed by edge id, giving
    the half-width per station and the trims at the two ends.

    ⚠️ **Sampled along the edge, and reported at the nearest station.** The two
    are not the same thing and an earlier draft measured only at the stations
    themselves, which is wrong twice over: `roads.py` simplifies to 0.2 m, so a
    straight street is *two* vertices and a wall halfway along it stands between
    them unmeasured — and both of those vertices are the ends, which is exactly
    the stretch the junction trims remove. That version measured nothing at all
    on every two-vertex edge while reporting a full table.
    """
    report = ClearanceReport()
    xs: list[np.ndarray] = []
    zs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    counts: list[np.ndarray] = []
    widths: list[np.ndarray] = []
    section_edge: list[np.ndarray] = []
    section_station: list[np.ndarray] = []

    for published in graph["edges"]:
        # Level 0 only, and that is `Q13` rather than an optimisation: the game
        # refuses to hand a car an off-grade edge, so its clearance is a Phase 4
        # question. Every edge still gets a full-length row below, so the table
        # covers the graph rather than a subset of it.
        edge_id = int(published["id"])
        points = np.asarray(published["polyline"], dtype=np.float64)
        entry = drawn.get(edge_id)
        halves = np.asarray((entry or {}).get("half_width_m", []), dtype=np.float64)
        report.corridor_m[edge_id] = [NOT_MEASURED] * len(points)
        if int(published.get("elevation_level", 0)) not in levels or len(points) < 2:
            continue
        if len(halves) != len(points):
            # The manifest and the graph disagree about this edge. Refused rather
            # than clamped: `surface.py` writes the two from one array, so a
            # mismatch means they came from different runs and every width after
            # it would be attributed to the wrong station.
            raise SystemExit(
                f"edge {edge_id} has {len(points)} stations but "
                f"{len(halves)} published half-widths; {SURFACE_MANIFEST_NAME} and "
                f"{ROADGRAPH_NAME} are from different runs"
            )

        along = plan_lengths(points)
        length = float(along[-1])
        trim_start, trim_end = (entry or {}).get("trim_m", (0.0, 0.0))
        at = (np.arange(np.ceil(length / along_m)) + 0.5) * along_m
        at = at[(at >= float(trim_start)) & (at <= length - float(trim_end))]
        report.sections_trimmed += int(np.ceil(length / along_m)) - len(at)
        if not len(at):
            # Wholly inside its own junction caps. Common and not an error: 208
            # of the region's trims are clamped by edge length precisely because
            # the edge is shorter than the two caps that meet on it.
            continue

        # Which segment each station falls on, and how far along it — one
        # interpolation serving the position, the height and the drawn width, so
        # the three cannot disagree about where the cross-section is.
        segment = np.clip(np.searchsorted(along, at, side="right") - 1, 0, len(points) - 2)
        span = along[segment + 1] - along[segment]
        fraction = np.divide(at - along[segment], span, out=np.zeros_like(at), where=span > 0.0)
        centre = points[segment] + (points[segment + 1] - points[segment]) * fraction[:, None]
        half = halves[segment] + (halves[segment + 1] - halves[segment]) * fraction

        # `normalise` rather than a bare divide, and that is correctness rather
        # than reuse: a vertex repeating the previous one in plan is **legal in
        # the published graph** — `surface.dedupe` exists to drop them — and this
        # walk never dedupes, so a zero-length segment would divide by zero. The
        # NaN cross-section it produced fell in no plan cell and so read *clear*.
        forward = gltf.normalise((points[segment + 1] - points[segment])[:, [0, 2]])
        across = np.stack([-forward[:, 1], forward[:, 0]], axis=1)

        count = np.ceil(2.0 * half / ACROSS_M).astype(np.int64)
        keep = count > 0
        if not keep.any():
            continue
        centre, half, across, count = centre[keep], half[keep], across[keep], count[keep]
        fraction, segment = fraction[keep], segment[keep]
        # Counted here, past both guards, because `main` reports it as edges
        # *measured* — an edge whose cross-sections were all trimmed away or came
        # out zero-width has been looked at and not measured.
        report.edges += 1

        # Reported at the nearer of the two vertices bracketing it, so the
        # published table stays indexed by `roadgraph.json`'s own numbering —
        # the same indexing `half_width_m` uses, which is what lets the game
        # read both off one station.
        station = np.where(fraction < 0.5, segment, segment + 1)

        index, within = _spread(count)
        offset = (within + 0.5) * ACROSS_M - half[index]
        xs.append(centre[index, 0] + across[index, 0] * offset)
        zs.append(centre[index, 2] + across[index, 1] * offset)
        ys.append(centre[index, 1])
        counts.append(count)
        # Clamped against the *station's* drawn width as well as this
        # cross-section's own. The two differ where the ribbon tapers, and the
        # number is published at the station — so a consumer reading the
        # clearance and the half-width off one station would otherwise find a
        # corridor wider than the carriageway it is measured across.
        widths.append(2.0 * np.minimum(half, halves[station]))
        section_edge.append(np.full(len(count), edge_id, dtype=np.int32))
        section_station.append(station.astype(np.int32))
        report.sections_measured += len(count)

    if not counts:
        raise SystemExit(
            f"no drivable level-0 carriageway in {ROADGRAPH_NAME} — nothing to measure"
        )
    corridor = Corridor(
        x=np.concatenate(xs),
        z=np.concatenate(zs),
        deck_y=np.concatenate(ys),
        section_count=np.concatenate(counts),
        section_width=np.concatenate(widths),
        section_edge=np.concatenate(section_edge),
        section_station=np.concatenate(section_station),
    )
    return corridor, report


# --------------------------------------------------------------------------
# The occupiers: everything solid that is not the ground
# --------------------------------------------------------------------------


def wears(colours: np.ndarray, base: tuple[int, int, int], jitter: float) -> np.ndarray:
    """Which vertex colours could be `base` after `colour_for` jittered it.

    The inverse of `buildings.colour_for`'s single scale factor across all three
    channels: a jittered class occupies a ray from black through its base colour
    rather than one value, so each channel admits a factor in
    `[(c - 0.5) / base, (c + 0.5) / base]` and the class is whatever has a
    non-empty intersection inside the configured jitter.

    ⚠️ `tools/deck_error.py` has the same test and the two are deliberately not
    shared — that split is the whole reason the graders can disagree with the
    pipeline. This one is used for a single question, "is this the ground", and
    the tool's is used to attribute every class.
    """
    channels = np.asarray(base, dtype=np.float64)
    if (channels <= 0.0).any() or (channels * (1.0 + jitter) > 255.0).any():
        raise SystemExit(
            f"colour {base} jitters past a channel limit, where `colour_for` clamps "
            "and this test stops being exact"
        )
    values = colours[:, :3].astype(np.float64)
    low = np.maximum(((values - 0.5) / channels).max(axis=1), 1.0 - jitter)
    high = np.minimum(((values + 0.5) / channels).min(axis=1), 1.0 + jitter)
    return low <= high


class _Steps(NamedTuple):
    """How finely each triangle splits, and how many the cap held back."""

    steps: np.ndarray
    clipped: int


def _plan_steps(corners: np.ndarray) -> _Steps:
    """How many ways each triangle must be split to get under `SUBDIVIDE_M`.

    Separate from `_subdivide` because the answer also sizes the work: `_batches`
    needs it before any piece exists.

    ⚠️ **Returns how many triangles the cap held back, because that is this
    stage's own over-blocking and nothing used to say so.** A triangle spanning
    more than `MAX_SUBDIVISIONS * SUBDIVIDE_M` = 16 m in plan keeps pieces wider
    than a cell, and `_emit` then rasterises each piece's plan box carrying the
    piece's *whole* height range — so a large sloped face blocks carriageway it
    is nowhere near. Hero meshes are where this bites, their triangles being the
    region's largest, and `Q51`'s one edge where this stage is the *more*
    pessimistic of the two instruments — `e702` EXPO DRIVE CENTRAL, 1.25 m here
    against the grader's 3.41 m — is `LANDMARK`-blocked. Counted, not fixed by
    raising the cap: the cap is what bounds `PIECE_BUDGET`'s worst case, and a
    number in the log is what lets the next reader tell a wall from a smear.
    """
    plan = corners[:, :, [0, 2]]
    span = plan.max(axis=1) - plan.min(axis=1)
    want = np.ceil(span.max(axis=1) / SUBDIVIDE_M)
    # Counted from what was *wanted*, not from the clipped result: a triangle
    # legitimately needing exactly `MAX_SUBDIVISIONS` is not one the cap held back.
    return _Steps(
        np.clip(want, 1, MAX_SUBDIVISIONS).astype(np.int64),
        int((want > MAX_SUBDIVISIONS).sum()),
    )


def _batches(steps: np.ndarray) -> list[tuple[int, int]]:
    """Runs of triangles whose pieces together stay under `PIECE_BUDGET`.

    Contiguous slices rather than a re-ordering, so the arrays stay views and a
    batch costs nothing to take. A single triangle can never exceed the budget on
    its own — `MAX_SUBDIVISIONS` caps it at 1,024 pieces.
    """
    load = np.cumsum(steps**2)
    if not len(load) or load[-1] <= PIECE_BUDGET:
        return [(0, len(steps))]
    marks = np.arange(PIECE_BUDGET, int(load[-1]) + PIECE_BUDGET, PIECE_BUDGET)
    ends = np.unique(np.clip(np.searchsorted(load, marks) + 1, 1, len(steps)))
    return list(zip(np.concatenate([[0], ends[:-1]]), ends, strict=True))


def _subdivide(corners: np.ndarray, steps: np.ndarray) -> np.ndarray:
    """Triangles split until each is at most `SUBDIVIDE_M` across in plan.

    `corners` is `(m, 3, 3)`. Returns `(k, 3, 3)`, `k >= m`. Split by *plan*
    extent — see the module header for why area would be the wrong measure.
    """
    pieces: list[np.ndarray] = []
    for step in np.unique(steps):
        chosen = corners[steps == step]
        if step == 1:
            pieces.append(chosen)
            continue
        # One barycentric lattice serves the whole group, which is what keeps
        # this a handful of array operations rather than a loop over triangles.
        weights = _lattice(int(step))
        # (group, cell, corner) x (corner, xyz) -> (group, cell, xyz), then the
        # three corners of each cell are already the three lattice rows.
        #
        # `optimize=True` is not a micro-tune: without it `einsum` runs its own
        # naive C loop, and with it the contraction goes through `tensordot` and
        # so through BLAS. 41.8 ms -> 1.2 ms on one group of 500 at 32 steps, and
        # this was 30% of the whole stage.
        points = np.einsum("kj,mjc->mkc", weights, chosen, optimize=True)
        pieces.append(points.reshape(-1, 3, 3))
    return np.concatenate(pieces) if pieces else corners[:0]


@lru_cache(maxsize=MAX_SUBDIVISIONS + 1)
def _lattice(step: int) -> np.ndarray:
    """Barycentric weights for the corners of every cell of a subdivided triangle.

    Returns `(3 * cells, 3)` reshaped by the caller into `(cells, 3, 3)` corner
    weights: `step ** 2` cells, upward and downward pointing.

    Cached, because there are only `MAX_SUBDIVISIONS` of these in the whole run
    and this was rebuilding them per mesh — 1,649 calls and 1.75 M `_weights`
    calls over one region, for 32 distinct answers. The result is read-only by
    convention: `einsum` never writes to it.
    """
    rows: list[tuple[float, float, float]] = []
    scale = 1.0 / step
    for i in range(step):
        for j in range(step - i):
            a = (i * scale, j * scale)
            rows.extend(
                [
                    _weights(a[0], a[1]),
                    _weights(a[0] + scale, a[1]),
                    _weights(a[0], a[1] + scale),
                ]
            )
            if i + j < step - 1:
                rows.extend(
                    [
                        _weights(a[0] + scale, a[1]),
                        _weights(a[0] + scale, a[1] + scale),
                        _weights(a[0], a[1] + scale),
                    ]
                )
    return np.asarray(rows, dtype=np.float64)


def _weights(u: float, v: float) -> tuple[float, float, float]:
    return (1.0 - u - v, u, v)


def _cell(values: np.ndarray) -> np.ndarray:
    return np.floor(values / CELL_M).astype(np.int64)


def _key(cx: np.ndarray, cz: np.ndarray) -> np.ndarray:
    """One integer per plan cell. The region is ~1.7 km, so the stride is ample."""
    return cx * 100_000 + cz


class _Sections:
    """The cross-section samples, indexed by plan cell for the occupier sweep."""

    def __init__(self, corridor: Corridor) -> None:
        self.band_low, self.band_high = corridor.band()
        keys = _key(_cell(corridor.x), _cell(corridor.z))
        self.order = np.argsort(keys, kind="stable")
        sorted_keys = keys[self.order]
        self.unique, starts, counts = np.unique(sorted_keys, return_index=True, return_counts=True)
        self.starts = starts
        self.counts = counts
        self.depth = int(counts.max())
        self.low_x, self.high_x = float(corridor.x.min()), float(corridor.x.max())
        self.low_z, self.high_z = float(corridor.z.min()), float(corridor.z.max())
        self.low_y = float(self.band_low.min())
        self.high_y = float(self.band_high.max())
        self.blocked = np.zeros(len(corridor), dtype=bool)

        # A coarse map of where any carriageway is, as a summed-area table, so
        # the prune below can ask "does this triangle's plan box touch any road"
        # in constant time per triangle rather than by rasterising it.
        #
        # ⚠️ Built from the very samples the survey then consumes, and that is
        # structural rather than tidy. `Q19` records a prune whose superset
        # property had decayed into a convention: derive this grid from anything
        # else — the graph, the surface mesh, a bounding box — and a change to
        # the walk silently prunes away carriageway the survey still asks about,
        # and every one of those samples reads clear.
        self.coarse_x = np.floor(corridor.x / COARSE_M).astype(np.int64)
        self.coarse_z = np.floor(corridor.z / COARSE_M).astype(np.int64)
        self.origin_x = int(self.coarse_x.min())
        self.origin_z = int(self.coarse_z.min())
        columns = int(self.coarse_x.max()) - self.origin_x + 1
        rows = int(self.coarse_z.max()) - self.origin_z + 1
        grid = np.zeros((columns, rows), dtype=np.int32)
        grid[self.coarse_x - self.origin_x, self.coarse_z - self.origin_z] = 1
        self.integral = np.pad(grid.cumsum(axis=0).cumsum(axis=1), ((1, 0), (1, 0)))
        self.columns = columns
        self.rows = rows

    def near(self, plan_low: np.ndarray, plan_high: np.ndarray) -> np.ndarray:
        """Which plan boxes cover at least one coarse cell holding carriageway.

        A box test, so it admits triangles that only *nearly* touch a road — the
        direction that costs time rather than answers.
        """
        low_x = np.clip(
            np.floor(plan_low[:, 0] / COARSE_M).astype(np.int64) - self.origin_x, 0, self.columns
        )
        low_z = np.clip(
            np.floor(plan_low[:, 1] / COARSE_M).astype(np.int64) - self.origin_z, 0, self.rows
        )
        high_x = np.clip(
            np.floor(plan_high[:, 0] / COARSE_M).astype(np.int64) - self.origin_x + 1,
            0,
            self.columns,
        )
        high_z = np.clip(
            np.floor(plan_high[:, 1] / COARSE_M).astype(np.int64) - self.origin_z + 1, 0, self.rows
        )
        covered = (
            self.integral[high_x, high_z]
            - self.integral[low_x, high_z]
            - self.integral[high_x, low_z]
            + self.integral[low_x, low_z]
        )
        return covered > 0

    def mark(self, keys: np.ndarray, low: np.ndarray, high: np.ndarray) -> None:
        """Block every sample in `keys`' cells that these height ranges reach."""
        slot = np.searchsorted(self.unique, keys)
        np.clip(slot, 0, len(self.unique) - 1, out=slot)
        hit = self.unique[slot] == keys
        if not hit.any():
            return
        slot, low, high = slot[hit], low[hit], high[hit]
        # One vectorised pass per occupancy depth rather than a loop over cells:
        # a cell holds a handful of samples, so this is a handful of sweeps over
        # the whole record set instead of a Python iteration per record.
        for step in range(self.depth):
            live = step < self.counts[slot]
            if not live.any():
                break
            index = self.order[self.starts[slot[live]] + step]
            reaches = (low[live] <= self.band_high[index]) & (high[live] >= self.band_low[index])
            self.blocked[index[reaches]] = True


def _emit(sections: _Sections, corners: np.ndarray) -> None:
    """Record every plan cell each piece covers, with the piece's height range."""
    plan = corners[:, :, [0, 2]]
    low = plan.min(axis=1)
    high = plan.max(axis=1)
    cx0, cz0 = _cell(low[:, 0]), _cell(low[:, 1])
    cx1, cz1 = _cell(high[:, 0]), _cell(high[:, 1])

    across = (cx1 - cx0 + 1).astype(np.int64)
    down = (cz1 - cz0 + 1).astype(np.int64)
    cells = across * down
    # Rasterised in full rather than by the box's four corners: the subdivision
    # cap can leave a piece wider than a cell, and a corner-only emission would
    # then step straight over the cells in between — under-reporting blockage,
    # which is the direction that fails silently.
    piece, within = _spread(cells)
    stride = across[piece]
    keys = _key(cx0[piece] + within % stride, cz0[piece] + within // stride)
    heights = corners[:, :, 1]
    sections.mark(keys, heights.min(axis=1)[piece], heights.max(axis=1)[piece])


class _Occupancy(NamedTuple):
    """What one pass over some meshes contributed, for `ClearanceReport.count`."""

    triangles: int
    pieces: int
    clipped: int


def occupy(
    sections: _Sections, meshes: list[gltf.MeshData], ground: tuple, jitter: float
) -> _Occupancy:
    """Block every cross-section sample an occupier's geometry stands over."""
    triangles = pieces = clipped = 0
    for mesh in meshes:
        corners = mesh.positions[mesh.triangles]
        if mesh.colours is not None:
            # The ground is excluded because it is `Q24`'s question, graded by
            # `tools/ground_clearance.py` — a road that follows a cross-slope
            # would otherwise read as a road with a wall down one side. A
            # triangle counts as ground only when all three of its vertices do,
            # so the seam between the ground and anything standing on it stays
            # with the thing standing on it.
            is_ground = wears(mesh.colours, ground, jitter)
            corners = corners[~is_ground[mesh.triangles].all(axis=1)]

        # Two prunes. A triangle wholly above or below every band in the region
        # cannot reach any sample, and neither can one whose plan box covers no
        # carriageway. The height test is applied first — it is a comparison
        # against two scalars where the other is four gathers — but both read
        # the same plan box, so it saves work rather than building.
        plan_low = corners[:, :, [0, 2]].min(axis=1)
        plan_high = corners[:, :, [0, 2]].max(axis=1)
        height = corners[:, :, 1]
        near = (height.max(axis=1) >= sections.low_y) & (height.min(axis=1) <= sections.high_y)
        near[near] = sections.near(plan_low[near], plan_high[near])
        corners = corners[near]
        if not len(corners):
            continue
        triangles += len(corners)

        # In batches, so one hero mesh cannot decide the pipeline's peak memory.
        steps, held = _plan_steps(corners)
        clipped += held
        for start, end in _batches(steps):
            split = _subdivide(corners[start:end], steps[start:end])
            pieces += len(split)
            _emit(sections, split)
    return _Occupancy(triangles, pieces, clipped)


# --------------------------------------------------------------------------
# Reading what stands beside the road
# --------------------------------------------------------------------------


def tile_meshes(out_dir: Path, buildings: dict) -> list[Path]:
    """The finest tier of every tile — the geometry a car actually collides with.

    LOD0 rather than the tier a distant camera draws: the coarser tiers exist to
    be looked at, and `Q19`'s tool reads LOD0 for the same reason.
    """
    paths = []
    for tile in buildings.get("tiles", []):
        lods = tile.get("lods", [])
        if lods:
            paths.append(out_dir / lods[0]["path"])
    return paths


def landmark_meshes(city: Config, region_id: str, out_dir: Path) -> list[gltf.MeshData]:
    """Every hero building, placed where `export.py` will publish it.

    Derived from the config rather than read from `landmarks.json`, because that
    document is written by `export.py` — which runs *after* this stage and needs
    what this stage measures. The shared predicate is `landmark_in_region`, so a
    hero cannot be measured here and placed somewhere else there.

    ⚠️ **The bearing is applied negated.** `rot_y_deg` is a compass bearing and
    `generated_landmarks.gd` places a hero with the *negative* rotation. HKCEC's
    bearing is 0.0, so getting this wrong stays invisible until Central Plaza's
    143.1 goes through it — which is exactly how `Q19` found it.
    """
    transform = city.game_transform(region_id)
    high_x, high_z = city.region_high(region_id)
    placed: list[gltf.MeshData] = []
    for landmark in city.landmarks:
        if not landmark_in_region(landmark, transform, high_x, high_z):
            continue
        angle = np.radians(-float(landmark.rot_y_deg))
        cos, sin = float(np.cos(angle)), float(np.sin(angle))
        offset = np.asarray(
            transform.to_game(landmark.easting, landmark.northing, landmark.elevation),
            dtype=np.float64,
        )
        for mesh in gltf.read_glb(_asset_path(landmark.asset, out_dir)):
            spun = mesh.positions.copy()
            spun[:, 0] = mesh.positions[:, 0] * cos + mesh.positions[:, 2] * sin
            spun[:, 2] = -mesh.positions[:, 0] * sin + mesh.positions[:, 2] * cos
            # `replace` rather than a fresh `MeshData`: spelling the fields out
            # drops whatever the dataclass grows next, silently. `colours` is
            # cleared on purpose — a hero carries none of the class palette the
            # ground test reads, and keeping them would put it up for exclusion.
            placed.append(replace(mesh, positions=spun + offset, colours=None))
    return placed


def _asset_path(asset: str, out_dir: Path) -> Path:
    """A hero's `res://` path as a file on disk.

    The generated heroes are in this region's own out tree; the authored ones are
    committed under `game/assets/authored/`. ⚠️ This is the one place the
    pipeline reads the game tree, and it is deliberate: measuring only the heroes
    the ETL happens to build would leave the committed ones standing in the road
    unmeasured, and the two instruments would then disagree by construction —
    the same different-populations mistake that left `Q19`'s 5.17% and 3.693%
    unreconciled.
    """
    if asset.startswith(LANDMARK_GENERATED_ROOT):
        return out_dir / "landmarks" / asset[len(LANDMARK_GENERATED_ROOT) :]
    if asset.startswith(LANDMARK_ASSET_ROOT):
        return GAME_ROOT / "assets" / "authored" / "landmarks" / asset[len(LANDMARK_ASSET_ROOT) :]
    raise SystemExit(f"landmark asset {asset!r} is under neither landmark root")


# --------------------------------------------------------------------------
# The answer: one width per station
# --------------------------------------------------------------------------


def _longest_clear(flags: np.ndarray) -> int:
    """Samples in the widest continuous unblocked run.

    The widest run rather than the unblocked total, and that is the whole
    criterion: a car needs one gap it fits through, not two halves of one on
    either side of a pillar.
    """
    if not flags.any():
        return len(flags)
    marked = np.flatnonzero(flags)
    bounds = np.concatenate([[-1], marked, [len(flags)]])
    return int((np.diff(bounds) - 1).max())


def measure(corridor: Corridor, blocked: np.ndarray, report: ClearanceReport) -> None:
    """Fold the per-sample verdicts into one width per cross-section, then per station.

    A station usually gathers several cross-sections — `ALONG_M` is a plan cell and
    the graph's vertices are much further apart than that — and it takes the
    **tightest** of them. Averaging would let a wall across half a station hide
    behind the clear half beside it, which is the same mistake at station scale
    that a region share makes at network scale (`Q19`).
    """
    starts = np.cumsum(corridor.section_count) - corridor.section_count
    for index, count in enumerate(corridor.section_count):
        start = int(starts[index])
        # Clamped to the carriageway that was drawn. `ACROSS_M` does not divide
        # every width, so an unobstructed 10.24 m street measures as 41 clear
        # samples — 10.25 m, and a clearance wider than the road it is measured
        # across reads as an instrument error however small it is.
        run = _longest_clear(blocked[start : start + int(count)]) * ACROSS_M
        width = round(min(run, float(corridor.section_width[index])), 3)
        widths = report.corridor_m[int(corridor.section_edge[index])]
        station = int(corridor.section_station[index])
        standing = widths[station]
        widths[station] = width if standing == NOT_MEASURED else min(standing, width)


def ground_colour(city: Config) -> tuple[tuple[int, int, int], float]:
    """The colour the ground wears, and how far it is jittered either side.

    The ground is excluded by its colour, so a city naming a `terrain_class` it
    gives no flat material to would measure its own ground as a wall down every
    street. Named here rather than raised as a `KeyError` from an index three
    frames down — and shared, so a second caller cannot skip the check.
    """
    ground_class = city.buildings.terrain_class
    if ground_class not in city.buildings.class_materials:
        raise SystemExit(
            f"{city.id} names terrain_class {ground_class!r}, which has no class_materials "
            "entry — there is no colour to exclude the ground by"
        )
    return city.buildings.class_materials[ground_class].colour, city.buildings.jitter_for(
        ground_class
    )


def open_region(
    city: Config, region_id: str, *, out_root: Path | None = None
) -> tuple[Path, dict, dict[int, dict], dict]:
    """A built region's out dir, road graph, carriageway table and tile manifest.

    Shared with `tools/narrowing.py`, which measures the same region at widths it
    was not drawn at. Four documents resolved one way, so the two cannot end up
    reading different builds and comparing the results.
    """
    out_dir = city.out_dir(region_id, out_root)
    rebuild = f"python -m pipeline --region {region_id}"
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    surface = read_document(out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, rebuild)
    buildings = read_document(out_dir / BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA, rebuild)
    drawn = {int(entry["edge"]): entry for entry in surface.get("carriageway", [])}
    return out_dir, graph, drawn, buildings


def build_region(
    city: Config,
    region_id: str,
    *,
    out_root: Path | None = None,
    along_m: float = ALONG_M,
    levels: tuple[int, ...] = (0,),
) -> ClearanceReport:
    """Measure the region already built in its out dir.

    ⚠️ `levels` is a measurement knob and never a shipped one; see `walk`.
    """
    out_dir, graph, drawn, buildings = open_region(city, region_id, out_root=out_root)
    corridor, report = walk(graph, drawn, along_m=along_m, levels=levels)
    report.along_m = along_m
    log.info(
        "  %d level %s edges, %d cross-sections to judge, %d left to their junction caps"
        " at %.2f m spacing",
        report.edges,
        "/".join(str(level) for level in levels),
        report.sections_measured,
        report.sections_trimmed,
        report.along_m,
    )

    ground, jitter = ground_colour(city)
    sections = _Sections(corridor)

    # Streamed one tile at a time. The region's tiles are 43 MB of geometry and
    # only the slice standing near the road survives the prune, so holding them
    # all at once would cost a hundredfold what the measurement needs.
    for path in tile_meshes(out_dir, buildings):
        report.count(occupy(sections, gltf.read_glb(path), ground, jitter))
        report.tiles_read += 1
    heroes = landmark_meshes(city, region_id, out_dir)
    report.count(occupy(sections, heroes, ground, jitter))
    report.landmarks_read = len(heroes)

    log.info(
        "  %d tiles and %d hero meshes read; %d triangles reach the corridor, %d pieces",
        report.tiles_read,
        report.landmarks_read,
        report.occupier_triangles,
        report.occupier_pieces,
    )
    if report.occupier_clipped:
        # Warned rather than logged: every one of these blocks by a box wider
        # than a cell carrying its whole height range, so a clearance measured
        # near one is a lower bound with no stated floor. See `_plan_steps`.
        log.warning(
            "  %d of them span over %.0f m in plan and could not be split to %.2f m — "
            "each blocks by its plan box at its full height range",
            report.occupier_clipped,
            MAX_SUBDIVISIONS * SUBDIVIDE_M,
            SUBDIVIDE_M,
        )
    measure(corridor, sections.blocked, report)
    return report


def _write(out_root: Path | None, city: Config, region_id: str, report: ClearanceReport) -> int:
    """An intermediate for `P1-6`, not the game-facing contract.

    Same reasoning as `roadsurface.json` and `buildings.json`: `city.json` is
    `export.py`'s to write, and this records only what this stage knows so the
    two stay independently runnable.

    ⚠️ **A swept measurement is never published**, and the refusal lives here
    rather than at the CLI because `build_region` is public and takes `along_m`
    too. A bundle measured at a spacing the stage does not ship is a document
    nobody can reproduce, and `RoadGraph.is_routable` would route on it.
    """
    if report.along_m != ALONG_M:
        raise SystemExit(
            f"{CLEARANCE_NAME} was measured at {report.along_m:.2f} m rather than the "
            f"shipped {ALONG_M:.2f} m — a sweep reports, it does not publish"
        )
    return write_document(
        city.out_dir(region_id, out_root) / CLEARANCE_NAME,
        {
            "schema_version": CLEARANCE_SCHEMA,
            "city_id": city.id,
            "region_id": region_id,
            "bumper_band_m": [BUMPER_LOW_M, BUMPER_HIGH_M],
            # The resolution of every width below, published so a consumer can
            # tell a measured 3.25 m from a bar of 3.20 m it only just clears.
            "resolution_m": ACROSS_M,
            "clearance": [
                {"edge": edge_id, "clear_width_m": widths}
                for edge_id, widths in sorted(report.corridor_m.items())
            ],
        },
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--along-m",
        type=float,
        default=ALONG_M,
        # A sweep knob for the aliasing `walk` names, and **report-only**: a
        # bundle whose clearances were measured at a spacing the stage does not
        # ship would be a document nobody could reproduce, so anything but the
        # default refuses to write. `--index-cell-m` on
        # `tools/carriageway_occupancy.py` is the same knob for the other
        # instrument's own error dimension.
        help="cross-section spacing along an edge; off the default it reports without writing",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    report = build_region(city, args.region, along_m=args.along_m)
    if report.along_m == ALONG_M:
        _write(None, city, args.region, report)
    else:
        # `_write` would refuse this anyway; saying so here is what makes a sweep
        # read as a measurement rather than as a failed run.
        log.warning(
            "  measured at %.2f m rather than the shipped %.2f m — reporting, not writing %s",
            report.along_m,
            ALONG_M,
            CLEARANCE_NAME,
        )

    bar_m = float(city.roads.lane_width_m)
    starved = report.starved(bar_m)
    log.info("  %d edges measured, bar is one lane at %.2f m", report.edges, bar_m)
    if starved:
        # Reported, never refused. This stage publishes what is there; the gate
        # is `tools/carriageway_occupancy.py`, and failing the build here would
        # stop every run until the geometry itself is fixed — which is `Q19`'s
        # remaining half and nobody's to fix by rebuilding.
        log.warning("  %d edges keep less than one lane clear, worst first:", len(starved))
        for edge_id, width in starved[:8]:
            log.warning("    e%-5d %5.2f m", edge_id, width)
    else:
        log.info("  every measured edge keeps a lane clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
