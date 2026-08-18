"""Whether solid geometry stands in the drawn carriageway (`Q19`).

The fourth sibling of `deck_error.py`, `overhang.py` and `ground_clearance.py`,
and the only one that asks a question about the *player's* path rather than
about the road's own shape. `deck_error` asks how far an elevated road sits from
the deck under it; `overhang` asks whether there is a deck under it at all;
`ground_clearance` asks whether the ground stands in it. This asks the one none
of them reach — **is anything standing in the road at bumper height?**

It exists because collision shipped. Before that, geometry crossing the
carriageway was a drawing defect; since then it is **invisible wall on roads the
graph calls legal**, and `RoadGraph` has no idea any of it is there. `P3-3`'s
traffic routes on those edges, so every blocked lane is a car driving into a
building — the reason `Q19` names `P3-3` as its owner and asks for a tool that
fails the build.

Two occupier classes, and they do not share a fix:

- **`INFRASTRUCTURE`** — a genuine defect, and the half that shrank with `Q20`.
- **Buildings** — the half this project *chose*. `widen_default` is 1.6x and
  `GAME_DESIGN.md` fixes the range at 1.3-1.8x, so widening eats the pavement
  first and then the ground-floor frontage. That is a playability trade, not a
  bug. This tool's job is to stop it drifting unwatched, never to overturn it.

⚠️ **Ground is not an occupier and is excluded by name.** Terrain standing in
the carriageway is `Q24`, it is `ground_clearance.py`'s to grade, and counting
it here would double-report one defect under two questions.

**What "occupied" means, and the trap in the obvious alternative.** A cell is
occupied when class geometry has *surface* in the band 0.3-2.0 m above the drawn
road. Surfaces, not volumes, and not bounding boxes:

- ⚠️ A first measurement for `Q19` marked each triangle's **bounding box** and
  read **13.71%**; sampling the actual surfaces cut it to a third. A box around
  a sloped flyover soffit covers carriageway the soffit is nowhere near.
- ⚠️ **A vertical ray cannot find a wall.** A wall is a vertical face, so it
  projects to a line in plan and a point-in-plan test hits it with probability
  zero — which is why `Faces.heights_at` cannot be reused here however much it
  looks like the right query. It is built for "what height is drawn here", and
  that question only has an answer for near-horizontal faces.
- The consequence, stated rather than hidden: the *interior* of a building
  footprint reads as clear, because an extruded building has no floor and its
  roof is far above the band. That is the right model for what a car meets — it
  collides with the wall at the perimeter and never reaches the middle — and the
  clear-corridor criterion below is what actually catches a blocked lane.

**The gate that matters is per-edge, not the region share.** A share tells
`P3-3` nothing: `RoadGraph` routes on edges, and what strands a traffic car is
one blocked edge rather than an average. Scattered occupancy a car can weave
through and a wall straight across the road are the same percentage. So the
criterion is a **clear corridor at least one lane wide**, `lane_width_m` from
the city config, held continuously along every drivable level-0 edge.

Region shares are gated too, but as a ratchet against `Q19`'s own published
figures rather than as the headline. Those numbers were fixed before this
grader existed — the `podium_error.py` precedent for a bar the instrument
cannot have been tuned to.

⚠️ **Off-grade carriageway is reported and never gated.** `Q21` has not decided
whether level -1 should be drawn at all and Phase 4 owns it; failing the build
over a decision nobody has made would be this tool inventing policy.

Nothing here is shared with the code it grades — same argument as
`deck_error.py`'s docstring, same table. The occupiers come from the **shipped
tiles**, found by vertex colour, and the road from the **shipped `roads.glb`**
rather than from the graph the ETL wrote.

Run:  .venv/bin/python tools/carriageway_occupancy.py --city hong_kong
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# `wears` is the single statement of how a class is told apart once a tile is
# merged into one primitive — a colour *ray* from black through the base, because
# `colour_for` jitters by a single scale factor across all three channels. Made
# public for this tool on the precedent `overhang.py` set for its own four
# helpers: `class_faces` cannot serve here, since it returns near-horizontal
# `Faces` and refuses any class without a `class_materials` entry — which is
# every building.
from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    class_triangles,
    drawn_surface,
    load_bundle,
    log_bundle,
    nearest,
    wears,
)
from overhang import cross_section, half_width_at, half_widths, left_of, walk_width  # noqa: E402
from pipeline.config import CityConfig, load_city  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402

log = logging.getLogger(__name__)

# `Q19`'s band, mirrored so this tool reproduces the frame the 5.17% was measured
# in. The floor clears the 0.15 m kerb and the road's own thickness; the ceiling
# is where a podium stops being an obstacle and starts being Hong Kong working as
# intended — the city overhangs its pavements everywhere, and a soffit 6 m up is
# not something a car can hit.
BUMPER_LOW_M = 0.30
BUMPER_HIGH_M = 2.00

# Plan cell for the occupier index, and **the dominant error term in every
# corridor width below** — not `--across-m`, which only quantises the answer.
# A cell blocks in full as soon as one surface sample lands in it, so a wall
# `w` metres thick in plan blocks up to `w + 2 * INDEX_CELL_M` of carriageway,
# and a corridor bounded by two obstructions loses up to twice that again.
#
# ⚠️ **This is why the tool reads more starved edges than `clearance.py` does,
# and it is deliberate.** `Q51` records 26 here against the pipeline's 21, and
# the gap was measured to this constant: brute-forcing `e132` from its own
# geometry reproduces **0.98 m at 1.0 m** and **4.00 m at 0.25 m**, which are
# the two instruments' published numbers exactly. Sweep it with
# `--index-cell-m` to price that; the default stays coarse on purpose, because
# the smear is also what makes this tool immune to the aliasing the pipeline is
# exposed to — a wall between two of its 1 m cross-sections is missed outright,
# while a 1 m bin cannot miss one. Two instruments, two error dimensions.
INDEX_CELL_M = 1.0

# Coarse cell for the pruning pass. Free to choose — the prune is a superset
# test — and set to `deck_error`'s own index cell because that is a size this
# region's geometry is already known to bin well at.
COARSE_CELL_M = 8.0

# How much of a station's drawn width must actually be there before a corridor is
# judged from it. See the guard in `survey`.
_CORRIDOR_MEASURED = 0.90

# The walk's own defaults, named rather than typed into `argparse` alone because
# `tools/clearance_reconcile.py` grades with them too. Hand-copied into a second
# parser, they could drift and the reconciler would quietly ratchet `Q51`'s counts
# against settings this tool no longer uses.
SPACING_M = 1.0
ACROSS_M = 0.5
SAMPLE_M = 0.25

# Names for the two classes the config cannot supply. `INFRASTRUCTURE` is the
# city's to name (`buildings.structure_class`); these two are not, and
# `tools/narrowing.py` already declares them for the same reason.
BUILDING = "BUILDING"
LANDMARK = "LANDMARK"


@dataclass(frozen=True)
class Occupied:
    """Surface sample heights of one occupier class, binned in plan.

    Heights are sorted per cell so the band test is a binary search rather than a
    scan: the carriageway asks this roughly a million times.
    """

    cells: dict[tuple[int, int], np.ndarray]
    triangles_kept: int
    triangles_seen: int
    samples: int
    # The plan cell the heights were binned at. Carried rather than read off the
    # module constant so a sweep cannot bin at one size and query at another —
    # which reads as a city that has cleared itself up.
    cell_m: float = INDEX_CELL_M

    def in_band(self, x: float, z: float, low: float, high: float) -> bool:
        """Is there surface between `low` and `high` at this plan position?"""
        heights = self.cells.get((int(np.floor(x / self.cell_m)), int(np.floor(z / self.cell_m))))
        if heights is None:
            return False
        index = int(np.searchsorted(heights, low, side="left"))
        return index < len(heights) and bool(heights[index] <= high)


def _barycentric(steps: int) -> np.ndarray:
    """Weights for a triangle sampled `steps` times along its longest edge."""
    first, second = np.meshgrid(np.arange(steps + 1), np.arange(steps + 1), indexing="ij")
    keep = (first + second) <= steps
    alpha = first[keep] / steps
    beta = second[keep] / steps
    return np.stack([alpha, beta, 1.0 - alpha - beta], axis=1)


def _touches_band(
    plan_low: np.ndarray,
    plan_high: np.ndarray,
    height_low: float,
    height_high: float,
    bands: dict[tuple[int, int], tuple[float, float]],
) -> bool:
    """Could one triangle reach the carriageway's occupiable band anywhere?

    Both tests admit more than the real one — a plan *box* against a coarse cell,
    and a height *range* against the widest band in it — so this is a superset of
    what is really occupied. That direction is the safe one: it keeps geometry a
    finer test would have to look at, and never drops any.
    """
    for column in range(int(plan_low[0]), int(plan_high[0]) + 1):
        for row in range(int(plan_low[1]), int(plan_high[1]) + 1):
            band = bands.get((column, row))
            if band is not None and height_high >= band[0] and height_low <= band[1]:
                return True
    return False


def class_predicates(
    city: CityConfig,
) -> tuple[str, Callable[[np.ndarray], np.ndarray], Callable[[np.ndarray], np.ndarray]]:
    """The structure class's name, and the two colour tests that select occupiers.

    Public because `tools/clearance_reconcile.py` has to index the *same* classes
    this tool does — that is the entire premise of comparing the two instruments —
    and a second copy of the complement below is a second place for it to stop
    being true. `deck_error.class_triangles` carries the same argument about
    itself, having already been written out twice.
    """
    structure_class = city.buildings.structure_class
    if structure_class is None:
        raise SystemExit(f"city '{city.id}' declares no buildings.structure_class")
    material = city.buildings.class_materials[structure_class]
    jitter = city.buildings.jitter_for(structure_class)

    def is_structure(colours: np.ndarray) -> np.ndarray:
        return wears(colours, material.colour, jitter)

    def is_building(colours: np.ndarray) -> np.ndarray:
        # Everything the config gives a flat material to, subtracted. Buildings
        # take height-banded colours, so they occupy many rays rather than one
        # and cannot be selected positively — but every class that *can* be is
        # named in `class_materials`, so the complement is buildings.
        #
        # ⚠️ **Every entry, not just structure and ground.** Subtracting only the
        # two named above left a third flat-material class counted as `BUILDING`
        # and gated against `--accept-building-share`, while the comment claimed
        # the complement "stays right when a class is added". It does now.
        other = np.zeros(len(colours), dtype=bool)
        for name, entry in city.buildings.class_materials.items():
            other = other | wears(colours, entry.colour, city.buildings.jitter_for(name))
        return ~other

    return structure_class, is_structure, is_building


def index_classes(
    city: CityConfig,
    generated: Path,
    manifest: dict[str, Any],
    tiles: list[Path],
    bands: dict[tuple[int, int], tuple[float, float]],
    *,
    sample_m: float,
    cell_m: float,
) -> dict[str, Occupied]:
    """Every occupier class, indexed at one plan cell.

    One call site for all three, so a caller cannot bin two of them at one cell
    size and the third at another — `survey` would consume that mixed dict without
    complaint and the mismatched class would simply stop being found.
    """
    structure_class, is_structure, is_building = class_predicates(city)
    return {
        structure_class: occupiers(tiles, is_structure, bands, sample_m, cell_m=cell_m),
        BUILDING: occupiers(tiles, is_building, bands, sample_m, cell_m=cell_m),
        LANDMARK: landmark_occupiers(generated, manifest, bands, sample_m, cell_m=cell_m),
    }


def occupiers(
    tiles: list[Path],
    keep: Callable[[np.ndarray], np.ndarray],
    bands: dict[tuple[int, int], tuple[float, float]],
    sample_m: float,
    *,
    cell_m: float = INDEX_CELL_M,
) -> Occupied:
    """Index one occupier class's surfaces across the shipped tiles.

    The class rule — a triangle joins only if **all three** corners wear it —
    belongs to `deck_error.class_triangles` and is applied there, not restated
    here.
    """
    return index_corners(class_triangles(tiles, keep), bands, sample_m, cell_m=cell_m)


def index_corners(
    blocks: Iterator[np.ndarray],
    bands: dict[tuple[int, int], tuple[float, float]],
    sample_m: float,
    *,
    cell_m: float = INDEX_CELL_M,
) -> Occupied:
    """Bin the surfaces of every triangle that could reach the road.

    ⚠️ **The pruning is what makes this affordable, and it is a superset rather
    than an approximation.** Sampling every building triangle in the region would
    be hundreds of millions of points to answer a question about the lowest two
    metres of the wall. A triangle survives only if its plan bounding box meets a
    coarse cell holding carriageway *and* its own height range overlaps that
    cell's band. Both tests admit more than the real one, so nothing that could
    have been occupied is dropped.
    """
    binned: dict[tuple[int, int], list[np.ndarray]] = {}
    kept = seen = sampled = 0

    for corners in blocks:
        seen += len(corners)
        plan_low = np.floor(corners[:, :, [0, 2]].min(axis=1) / COARSE_CELL_M).astype(np.int64)
        plan_high = np.floor(corners[:, :, [0, 2]].max(axis=1) / COARSE_CELL_M).astype(np.int64)
        height_low = corners[:, :, 1].min(axis=1)
        height_high = corners[:, :, 1].max(axis=1)

        wanted = [
            index
            for index in range(len(corners))
            if _touches_band(
                plan_low[index],
                plan_high[index],
                float(height_low[index]),
                float(height_high[index]),
                bands,
            )
        ]
        if not wanted:
            continue

        chosen = corners[np.asarray(wanted, dtype=np.int64)]
        kept += len(chosen)

        # Grouped by how many steps each triangle needs, so one lattice is
        # built per group and applied to the whole group at once. Per-triangle
        # lattices dominated the runtime when this was written the obvious way.
        longest = np.sqrt(
            np.maximum.reduce(
                [
                    np.sum((chosen[:, 1] - chosen[:, 0]) ** 2, axis=1),
                    np.sum((chosen[:, 2] - chosen[:, 1]) ** 2, axis=1),
                    np.sum((chosen[:, 0] - chosen[:, 2]) ** 2, axis=1),
                ]
            )
        )
        steps = np.clip(np.ceil(longest / sample_m), 1, 64).astype(np.int64)
        for count in np.unique(steps):
            block = chosen[steps == count]
            points = np.einsum("kc,tcd->tkd", _barycentric(int(count)), block).reshape(-1, 3)
            sampled += len(points)
            keys = np.floor(points[:, [0, 2]] / cell_m).astype(np.int64)
            order = np.lexsort((keys[:, 1], keys[:, 0]))
            keys, heights = keys[order], points[order, 1]
            cuts = np.flatnonzero(np.any(np.diff(keys, axis=0) != 0, axis=1)) + 1
            for piece_keys, piece in zip(
                np.split(keys, cuts), np.split(heights, cuts), strict=True
            ):
                if not len(piece):
                    continue
                binned.setdefault((int(piece_keys[0, 0]), int(piece_keys[0, 1])), []).append(piece)

    return Occupied(
        cells={key: np.sort(np.concatenate(value)) for key, value in binned.items()},
        triangles_kept=kept,
        triangles_seen=seen,
        samples=sampled,
        cell_m=cell_m,
    )


@dataclass
class Survey:
    """Every carriageway cell, and what stands in it.

    ⚠️ **`asked` and the misses are counted, not merely skipped**, and that is
    `deck_error`'s hardest-won lesson rather than bookkeeping. Its fourth defect
    left unmeasurable stations out of the denominator: breaking a third of the
    carriageway made the broken third stop being measured, every ratio improved,
    and the tool exited 0.
    """

    asked: int = 0
    measured: int = 0
    no_road: int = 0
    # Area by level, and the occupied part of it by level and class. Area rather
    # than a cell count, so the share does not move when the sampling lattice
    # does — a narrow ramp and a wide arterial are not equals.
    area_m2: dict[int, float] = field(default_factory=dict)
    occupied_m2: dict[tuple[int, str], float] = field(default_factory=dict)
    # The narrowest clear corridor found on each drivable level-0 edge, and where.
    corridor_m: dict[int, float] = field(default_factory=dict)
    corridor_at: dict[int, tuple[float, float]] = field(default_factory=dict)
    # The same corridor measured only inside the authored width, at the same
    # worst station — how much of the blockage the playability widening owns.
    corridor_authored_m: dict[int, float] = field(default_factory=dict)
    # The across-spacing the reported corridor was counted in, per edge. Every
    # width above is an integer multiple of it, and it is *not* `--across-m`:
    # `cross_section` divides the drawn width into whole cells, so a 10.24 m
    # ribbon at 0.5 m becomes 21 cells of 0.4876. Published because `Q51`'s
    # table read as centimetre measurement when "0.49 m" only ever meant
    # "one cell", and the reader cannot tell those apart without this.
    corridor_span_m: dict[int, float] = field(default_factory=dict)
    # Stations whose cross-section was too trimmed to judge a corridor from.
    # Counted rather than silently skipped, for the reason in the class docstring.
    corridor_stations: int = 0
    corridor_skipped: int = 0

    def add(self, level: int, class_name: str | None, area_m2: float) -> None:
        self.area_m2[level] = self.area_m2.get(level, 0.0) + area_m2
        if class_name is not None:
            key = (level, class_name)
            self.occupied_m2[key] = self.occupied_m2.get(key, 0.0) + area_m2

    def share(self, level: int, class_name: str) -> float:
        """Occupied share of one level's own drawn area."""
        area = self.area_m2.get(level, 0.0)
        return 0.0 if area <= 0.0 else self.occupied_m2.get((level, class_name), 0.0) / area

    def drawn_share(self, level: int, class_name: str) -> float:
        """Occupied share of **all** drawn carriageway — `Q19`'s denominator.

        ⚠️ The two are not interchangeable and the gates ride on this one.
        `Q19` publishes `BUILDING` 1.72%, `INFRASTRUCTURE` 1.60% and off-grade
        1.87% as three shares that **sum to its 5.17% headline**, so they are
        all shares of the same whole. Gating the level-0 pair against a level-0
        denominator instead reads them as ~10% looser than they were written,
        which is the bar being quietly moved by a choice of divisor.
        """
        total = sum(self.area_m2.values())
        return 0.0 if total <= 0.0 else self.occupied_m2.get((level, class_name), 0.0) / total

    @property
    def coverage(self) -> float:
        return 0.0 if not self.asked else self.measured / self.asked


def _clear_run(occupied: list[bool], span_m: float) -> float:
    """The widest continuous clear width across one station."""
    best = run = 0
    for blocked in occupied:
        run = 0 if blocked else run + 1
        best = max(best, run)
    return best * span_m


@dataclass(frozen=True)
class Lattice:
    """Every drawn carriageway cell, walked **once**.

    ⚠️ **One walk, because two walks is a silent false pass.** This tool needs
    two passes — the occupier index can only be pruned to the band the road
    actually occupies, so the road has to be measured before the buildings are
    read — and the obvious way to write that is to walk the carriageway twice.
    Measured, the second walk cost **22 s of a 47 s run**: `heights_at` alone was
    2,231,164 calls, exactly twice the 1,115,582 cells, and the two walks emitted
    a byte-identical cell sequence.

    The cost was the smaller half of the problem. The prune is only sound while
    pass one visits a **superset** of what pass two asks about, and with the walk
    written out twice nothing enforced that. Change the level filter, the spacing,
    or the attribution window in one copy and the index is pruned away from
    carriageway the survey then asks about — and every one of those cells reads
    **clear**, which is the one direction this tool must never flatter. Walking
    once makes the superset property structural instead of a convention.

    Stored as parallel arrays rather than objects: 1.1 M cells is ~45 MB this way
    and several times that as Python tuples.
    """

    edge: np.ndarray  # int32, which edge the cell belongs to
    level: np.ndarray  # int8, elevation level
    station: np.ndarray  # int32, cells sharing one cross-section
    x: np.ndarray  # float64, plan position
    z: np.ndarray
    span: np.ndarray  # float64, the width this cell stands for
    offset: np.ndarray  # float64, signed distance from the centreline
    authored_half: np.ndarray  # float64, half the un-widened width at this cell
    surface_y: np.ndarray  # float64, drawn road height — NaN where none is drawn
    spacing_m: float

    @property
    def asked(self) -> int:
        return len(self.surface_y)

    @property
    def drawn(self) -> np.ndarray:
        """Which cells had road drawn at them."""
        return np.isfinite(self.surface_y)


def walk_carriageway(
    graph: dict[str, Any],
    manifest: dict[str, Any],
    drawn: Faces,
    *,
    spacing_m: float,
    across_m: float,
    attribute_within_m: float,
) -> Lattice:
    """Walk every drawn carriageway cell once, recording what both passes need."""
    widths = half_widths(manifest)

    edges: list[int] = []
    levels: list[int] = []
    stations: list[int] = []
    xs: list[float] = []
    zs: list[float] = []
    spans: list[float] = []
    offsets: list[float] = []
    authored: list[float] = []
    surfaces: list[float] = []
    station_id = 0

    for edge in graph["edges"]:
        level = int(edge["elevation_level"])
        # Level -1 is a void under the terrain that nothing can see and nobody
        # can drive — `Q21`'s question, and not evidence about this one.
        if level < 0:
            continue
        edge_id = int(edge["id"])
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue

        # The width before `widen_default` multiplied it. `Q19` names the
        # widening as the cause of its building half, so the report separates a
        # blockage that reaches the real lanes from one that only eats the
        # frontage the widening took — those are not the same defect, and only
        # the first one strands a car that drives where the street actually is.
        authored_half = float(edge["width_m"]) / 2.0

        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            half = half_width_at(widths.get(edge_id, []), vertex)
            for index, (x, z, span) in enumerate(
                cross_section(station[[0, 2]], normal, half, across_m)
            ):
                # The drawn road first, because the question is what stands in
                # *what is drawn*. Falling back to the graph's own y would ask
                # about a surface that may never have been built.
                found_y = nearest(drawn.heights_at(x, z), float(station[1]), attribute_within_m)
                edges.append(edge_id)
                levels.append(level)
                stations.append(station_id)
                xs.append(x)
                zs.append(z)
                spans.append(span)
                # `cross_section` walks from the left rim inward in even steps,
                # so the offset from the centreline is recoverable without it
                # having to return one.
                offsets.append(-half + span * (index + 0.5))
                authored.append(authored_half)
                # NaN, not a sentinel height: "no road drawn here" is a junction
                # trim or a stale width table, and it has to stay distinguishable
                # from a road at y = 0 rather than quietly leave the denominator.
                surfaces.append(float("nan") if found_y is None else found_y)
            station_id += 1

    return Lattice(
        edge=np.asarray(edges, dtype=np.int32),
        level=np.asarray(levels, dtype=np.int8),
        station=np.asarray(stations, dtype=np.int32),
        x=np.asarray(xs, dtype=np.float64),
        z=np.asarray(zs, dtype=np.float64),
        span=np.asarray(spans, dtype=np.float64),
        offset=np.asarray(offsets, dtype=np.float64),
        authored_half=np.asarray(authored, dtype=np.float64),
        surface_y=np.asarray(surfaces, dtype=np.float64),
        spacing_m=spacing_m,
    )


def band_map(lattice: Lattice) -> dict[tuple[int, int], tuple[float, float]]:
    """Coarse plan cell to the height band any carriageway in it could be occupied at.

    The prune's whole input. Built from the same lattice `survey` consumes, so
    nothing it covers can be missing from what the survey asks about.
    """
    drawn = lattice.drawn
    if not drawn.any():
        return {}
    keys = np.floor(np.stack([lattice.x[drawn], lattice.z[drawn]], axis=1) / COARSE_CELL_M)
    keys = keys.astype(np.int64)
    low = lattice.surface_y[drawn] + BUMPER_LOW_M
    high = lattice.surface_y[drawn] + BUMPER_HIGH_M

    coarse: dict[tuple[int, int], tuple[float, float]] = {}
    for (column, row), band_low, band_high in zip(map(tuple, keys), low, high, strict=True):
        key = (int(column), int(row))
        seen = coarse.get(key)
        coarse[key] = (
            (float(band_low), float(band_high))
            if seen is None
            else (min(seen[0], float(band_low)), max(seen[1], float(band_high)))
        )
    return coarse


def survey(lattice: Lattice, classes: dict[str, Occupied]) -> Survey:
    """Ask every drawn carriageway cell what stands in it."""
    found = Survey()
    found.asked = lattice.asked

    blocked: list[bool] = []
    inside: list[bool] = []
    station_span = 0.0
    station_cells = 0
    current = -1
    current_edge = -1
    current_level = 0
    # Where a failing station is *reported*, and it has to be the centreline
    # rather than whichever cell happened to be walked last: a rim cell is half
    # the drawn width away, which on a widened arterial is 5 m of "go and look
    # here".
    seen_x = seen_z = 0.0
    seen_offset = float("inf")

    def close_station() -> None:
        # The corridor is a level-0 question. An off-grade ribbon nobody can
        # reach cannot strand a traffic car, and `Q21`/`Q22` own its defects.
        if current_level != 0 or not blocked:
            return
        found.corridor_stations += 1

        # ⚠️ **A trimmed cross-section cannot be judged, and judging one anyway
        # invents blocked edges.** Cells with no road drawn are not appended to
        # `blocked` at all, so at a junction trim the corridor would be measured
        # across whatever few cells survived — one clear cell out of twenty reads
        # as a 0.49 m corridor and condemns the edge. Measured on Wan Chai before
        # this guard: 44 edges failed, and seven of the eight tightest sat at
        # exactly one cell's width, which is the artefact rather than a wall.
        if len(blocked) < _CORRIDOR_MEASURED * station_cells:
            found.corridor_skipped += 1
            return
        clear = _clear_run(blocked, station_span)
        if clear < found.corridor_m.get(current_edge, float("inf")):
            found.corridor_m[current_edge] = clear
            found.corridor_at[current_edge] = (seen_x, seen_z)
            found.corridor_span_m[current_edge] = station_span
            found.corridor_authored_m[current_edge] = _clear_run(
                [wall for wall, within in zip(blocked, inside, strict=True) if within],
                station_span,
            )

    for i in range(lattice.asked):
        station = int(lattice.station[i])
        if station != current:
            close_station()
            blocked = []
            inside = []
            station_cells = 0
            seen_offset = float("inf")
            current = station
            current_edge = int(lattice.edge[i])
            current_level = int(lattice.level[i])
        station_cells += 1
        station_span = float(lattice.span[i])
        if abs(float(lattice.offset[i])) < seen_offset:
            seen_offset = abs(float(lattice.offset[i]))
            seen_x, seen_z = float(lattice.x[i]), float(lattice.z[i])

        surface_y = lattice.surface_y[i]
        if not np.isfinite(surface_y):
            # Counted so it cannot quietly leave the denominator.
            found.no_road += 1
            continue
        found.measured += 1

        x, z = float(lattice.x[i]), float(lattice.z[i])
        low, high = float(surface_y) + BUMPER_LOW_M, float(surface_y) + BUMPER_HIGH_M
        standing = next(
            (name for name, index in classes.items() if index.in_band(x, z, low, high)),
            None,
        )
        found.add(current_level, standing, float(lattice.span[i]) * lattice.spacing_m)
        blocked.append(standing is not None)
        inside.append(abs(float(lattice.offset[i])) <= float(lattice.authored_half[i]))
    close_station()

    return found


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        parents=[bundle_arguments()],
        description="Whether solid geometry stands in the drawn carriageway (Q19).",
    )
    parser.add_argument(
        "--spacing-m", type=float, default=SPACING_M, help="station spacing along an edge"
    )
    parser.add_argument(
        "--across-m", type=float, default=ACROSS_M, help="cell width across the ribbon"
    )
    parser.add_argument(
        "--index-cell-m",
        type=float,
        default=INDEX_CELL_M,
        # A sweep knob, not a tuning knob. The shipped default stays coarse for
        # the reason the constant's comment gives; this exists so the gap against
        # `clearance.py` can be *priced* — see `Q51` — rather than argued about.
        help="plan cell the occupier index bins at (the dominant error term)",
    )
    parser.add_argument(
        "--sample-m",
        type=float,
        default=SAMPLE_M,
        # Fine enough that a wall crossing one `--across-m` cell puts several
        # samples in the 1.7 m band, coarse enough that the lowest storey of the
        # region is a few million points rather than a few hundred million.
        help="how densely each occupier triangle's surface is sampled",
    )
    parser.add_argument(
        "--accept-building-share",
        type=float,
        default=0.0172,
        # `Q19`'s own published figure, fixed before this grader existed. The
        # `podium_error.py` precedent: a bar the instrument cannot have been
        # tuned to, because it predates the instrument.
        help="fail above this share of level-0 carriageway area occupied by buildings",
    )
    parser.add_argument(
        "--accept-infrastructure-share",
        type=float,
        default=0.0160,
        help="fail above this share of level-0 carriageway area occupied by structure",
    )
    parser.add_argument(
        "--accept-corridor-lanes",
        type=float,
        default=1.0,
        # In lanes rather than metres so the criterion travels to the next city
        # with its own `lane_width_m`, and so the number reads as the thing it
        # means: a car needs a lane.
        help="every drivable level-0 edge must keep this many lanes clear",
    )
    parser.add_argument(
        "--accept-coverage",
        type=float,
        default=0.90,
        # `deck_error`'s fourth defect, refused here by construction: a tool
        # whose denominator shrinks when the thing it measures breaks will
        # report a pass for having stopped looking.
        help="fail below this share of asked cells actually measured",
    )
    args = parser.parse_args(argv)

    city = load_city(args.city)
    manifest, tiles = load_bundle(args.generated, args.lod, args.city)

    # ⚠️ Named by the config, never guessed from `class_materials`' iteration
    # order. `terrain_class` is a **required** field (`pipeline/config.py`) and
    # `ground_clearance.py` reads it directly; picking "the first non-structure
    # key" instead is dict-order-dependent and yields nothing at all for a city
    # whose terrain takes height-banded colours rather than a flat material.
    ground_class = city.buildings.terrain_class

    log_bundle(manifest, args.lod)
    log.info("carriageway occupancy, %s, lod %d", args.city, args.lod)
    log.info(
        "  occupied means class surface %.2f-%.2f m above the drawn road, "
        "binned in %.2f m plan cells",
        BUMPER_LOW_M,
        BUMPER_HIGH_M,
        args.index_cell_m,
    )

    # Read once, used by everything below: the graph feeds the walk and the
    # street names, and the road mesh index feeds the walk alone. Both were
    # rebuilt per pass before the walk was unified.
    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    drawn = drawn_surface(args.generated, manifest)

    # The walk sizes the question — where is carriageway, and at what height
    # could it be occupied — and *records* it, so the occupier index is pruned
    # to exactly the cells the survey will go on to ask about.
    lattice = walk_carriageway(
        graph,
        manifest,
        drawn,
        spacing_m=args.spacing_m,
        across_m=args.across_m,
        attribute_within_m=args.attribute_within_m,
    )
    if not lattice.drawn.any():
        raise SystemExit(
            "no drawn carriageway could be found — is the road mesh present, and does "
            "city.json still name it?"
        )
    bands = band_map(lattice)
    structure_class = class_predicates(city)[0]

    log.info("")
    log.info("  indexing occupier surfaces near the carriageway:")
    classes = index_classes(
        city,
        args.generated,
        manifest,
        tiles,
        bands,
        sample_m=args.sample_m,
        cell_m=args.index_cell_m,
    )
    for name, index in classes.items():
        log.info(
            "    %-16s %7d of %7d triangles reach the band, %9d surface samples",
            name,
            index.triangles_kept,
            index.triangles_seen,
            index.samples,
        )
    log.info("    %-16s excluded — that is Q24, and ground_clearance.py grades it", ground_class)

    found = survey(lattice, classes)

    lane_m = float(city.roads.lane_width_m)
    corridor_bar_m = lane_m * args.accept_corridor_lanes
    names = road_names(graph)

    log.info("")
    log.info("  share of ALL drawn carriageway with geometry standing in it — Q19's frame,")
    log.info("  so these sum to its 5.17%% headline and the gates below read against them:")
    drawn_total = sum(found.area_m2.values())
    running = 0.0
    for level in sorted(found.area_m2):
        parts = " · ".join(
            f"{name} {100.0 * found.drawn_share(level, name):6.3f}%" for name in sorted(classes)
        )
        subtotal = sum(found.drawn_share(level, name) for name in classes)
        running += subtotal
        log.info(
            "    level %+d   %s   = %6.3f%%   (%.0f m2 drawn, %.1f%% of all)",
            level,
            parts,
            100.0 * subtotal,
            found.area_m2[level],
            100.0 * found.area_m2[level] / drawn_total,
        )
    log.info("    %-56s   total %6.3f%%", "", 100.0 * running)
    if any(level != 0 for level in found.area_m2):
        log.info("    level +1 and above is reported, never gated — Q21/Q22 and Phase 4 own it")

    log.info("")
    log.info("  the same, against each level's own area — informative, never gated:")
    for level in sorted(found.area_m2):
        parts = " · ".join(
            f"{name} {100.0 * found.share(level, name):6.3f}%" for name in sorted(classes)
        )
        log.info("    level %+d   %s", level, parts)

    log.info("")
    log.info(
        "  narrowest clear corridor per drivable level-0 edge, against %.2f m (%.1f lane):",
        corridor_bar_m,
        args.accept_corridor_lanes,
    )
    log.info("    'authored' is the same station measured inside the un-widened width")
    # ⚠️ Every width below is a *lower bound*, and the two resolutions say how
    # loose a bound. `cell` is the plan bin, which blocks in full on one sample
    # and so smears a wall by up to a cell either side; `step` is the across
    # spacing, which is what the width is counted in. `Q51`'s 26-against-21 was
    # measured to the first of these — quoting a width without them reads as a
    # measurement when it is an upper bound on the blockage.
    log.info(
        "    each width is an integer number of 'step' cells and a LOWER bound: "
        "the %.2f m plan bin blocks in full on one sample",
        args.index_cell_m,
    )
    tightest = sorted(found.corridor_m.items(), key=lambda item: item[1])[:8]
    for edge_id, clear in tightest:
        x, z = found.corridor_at[edge_id]
        log.info(
            "    e%-5d %6.2f m clear (authored %5.2f m, step %4.2f m)  at (%7.1f, %7.1f)  %s",
            edge_id,
            clear,
            found.corridor_authored_m.get(edge_id, float("nan")),
            found.corridor_span_m.get(edge_id, float("nan")),
            x,
            z,
            names.get(edge_id, "unnamed"),
        )
    log.info(
        "    %d level-0 edges judged from %d stations; %d stations too trimmed to judge",
        len(found.corridor_m),
        found.corridor_stations,
        found.corridor_skipped,
    )

    log.info("")
    log.info(
        "  %d cells asked, %d measured (%.1f%%), %d with no road drawn",
        found.asked,
        found.measured,
        100.0 * found.coverage,
        found.no_road,
    )

    problems = []
    starved = sorted(
        ((edge_id, clear) for edge_id, clear in found.corridor_m.items() if clear < corridor_bar_m),
        key=lambda item: item[1],
    )
    if starved:
        named = ", ".join(
            f"e{edge_id} {clear:.2f} m ({names.get(edge_id, 'unnamed')})"
            for edge_id, clear in starved[:6]
        )
        problems.append(
            f"{len(starved)} drivable level-0 edges keep less than {corridor_bar_m:.2f} m "
            f"clear — a traffic car cannot pass: {named}" + (" ..." if len(starved) > 6 else "")
        )
    # ⚠️ Buildings and landmarks are gated **together** against the one building
    # bar. `Q19` measured 1.72% while HKCEC was still a tile; `P3-6` moved it to
    # `landmarks.json` afterwards. Scoring the two separately would compare a
    # 2026-08 figure against a bundle that has since had its largest roadside
    # building taken out of the population, and the bar would silently loosen.
    for names_gated, bar in (
        ((BUILDING, LANDMARK), args.accept_building_share),
        ((structure_class,), args.accept_infrastructure_share),
    ):
        share = sum(found.drawn_share(0, name) for name in names_gated)
        if share > bar:
            problems.append(
                f"{100.0 * share:.3f}% of all drawn carriageway has {'+'.join(names_gated)} "
                f"standing in it at grade, against {100.0 * bar:.3f}%"
            )
    if found.coverage < args.accept_coverage:
        problems.append(
            f"only {100.0 * found.coverage:.1f}% of asked cells could be measured, against "
            f"{100.0 * args.accept_coverage:.1f}% — the rest is not evidence of anything"
        )

    if problems:
        log.error("")
        for problem in problems:
            log.error("  FAIL  %s", problem)
        return 1

    log.info("")
    log.info("  Within the accepted bounds.")
    return 0


def landmark_occupiers(
    generated: Path,
    manifest: dict[str, Any],
    bands: dict[tuple[int, int], tuple[float, float]],
    sample_m: float,
    *,
    cell_m: float = INDEX_CELL_M,
) -> Occupied:
    """Hero buildings, which since `P3-6` are not in the tiles at all.

    ⚠️ **Without this the tool is blind exactly where the player starts.**
    `P3-6` gave `landmarks.json` an `excluded_bounds` and took HKCEC *out* of the
    shipped tiles, so a tile-only survey sees a hole where the largest building on
    Expo Drive used to be — and Expo Drive is where `RoadSpawn` puts the car. A
    reading that fell because a building stopped being a tile is not the
    carriageway getting clearer.

    No colour filter: a landmark is building geometry end to end, and it wears a
    hand-authored palette that matches none of the class rays anyway. Each asset
    is placed by its own `transform` — position and a yaw — because these ship
    unbaked, unlike the tiles whose vertices are already in world space.
    """
    entry = manifest.get("landmarks")
    if not entry:
        return Occupied(cells={}, triangles_kept=0, triangles_seen=0, samples=0, cell_m=cell_m)
    catalogue = json.loads((generated / entry).read_text())

    def blocks() -> Iterator[np.ndarray]:
        for landmark in catalogue.get("landmarks", []):
            asset = str(landmark["asset"])
            # `res://` is Godot's project root, which is `game/`. The bundle path
            # is the tools' handle on the same tree, and it is `game/assets/…`.
            path = generated.parent.parent / asset.removeprefix("res://")
            if not path.exists():
                raise SystemExit(
                    f"landmark '{landmark['id']}' names {asset}, which is not at {path}. "
                    "Rebuild the region, or sync the generated assets."
                )
            place = landmark.get("transform") or {}
            offset = np.asarray(place.get("pos", (0.0, 0.0, 0.0)), dtype=np.float64)
            # ⚠️ **`rot_y_deg` is a compass bearing, so it is applied negated**,
            # and getting this wrong is silent. Bearings run clockwise from north
            # while game north is -Z, so `generated_landmarks.gd` places a hero
            # with `Basis(Vector3.UP, deg_to_rad(-rot_y_deg))` and this has to
            # match it exactly or the tool measures a building the game draws
            # somewhere else. Written the obvious way first, and HKCEC's bearing
            # is 0.0 — so the error hid completely until Central Plaza, at 143.1,
            # was checked against the scene.
            yaw = np.radians(-float(place.get("rot_y_deg", 0.0)))
            cos, sin = float(np.cos(yaw)), float(np.sin(yaw))
            spin = np.array([[cos, 0.0, sin], [0.0, 1.0, 0.0], [-sin, 0.0, cos]])
            for mesh in read_glb(path):
                if not len(mesh.triangles):
                    continue
                corners = mesh.positions[mesh.triangles].astype(np.float64)
                yield corners @ spin.T + offset

    return index_corners(blocks(), bands, sample_m, cell_m=cell_m)


def road_names(graph: dict[str, Any]) -> dict[int, str]:
    """Edge id to a street name, for a failure a reader can go and look at.

    English where the source has it, Chinese where it does not — many service
    roads carry only one, and "unnamed" for a slip road that carries neither is
    more use than an empty column.
    """
    names: dict[int, str] = {}
    for edge in graph["edges"]:
        name = edge.get("road_name") or {}
        chosen = name.get("en") or name.get("zh") if isinstance(name, dict) else None
        if chosen:
            names[int(edge["id"])] = str(chosen)
    return names


if __name__ == "__main__":
    raise SystemExit(main())
