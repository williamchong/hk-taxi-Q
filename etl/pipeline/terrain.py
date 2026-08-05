"""Surface level, sampled from the source map sheets (`Q11`, `P2-7`).

Road Network v2 carries no Z ordinate, and `elevation_levels` maps grade
separation to an *offset* — it never said what that offset is measured from.
`P1-2` measured the gap: 99.9% of Wan Chai's buildings have their base above
2 m, median 4.29 m. Taking level 0 as y=0 would run Hennessy Road four metres
below the doorways on it, and below the terrain surface as well.

The LandsD sheets ship a real height field covering the whole region, we already
parse it, and sampling happens at build time — so it costs nothing at runtime.
That was reason enough to keep the terrain in the pipeline back when it was
never rendered; `P3-10` draws it as well, from the same geometry, which is what
stops the height a road thinks it sits at drifting from the ground drawn under
it. See the `P1-2` terrain decision in `docs/PROGRESS.md`.

Three queries. They share their machinery and differ only in how they pick among
the surfaces found at one point, which is the whole of what separates them:

`sample` answers *how high is the ground here*, one height per point, the
highest thing found. Terrain is single-valued wherever a vehicle can be, so the
top face is the answer and the query needs no context.

`sample_along` answers *which deck is this carriageway on*, and cannot work
per-point: a flyover is a closed volume, so a station under one gets the deck's
top face, its underside, and any structure stacked above or below it. `P2-7`
measured picking by height alone — nearest to the level's nominal offset — and
it scored *worse* than taking the highest, because a slab's two faces are up to
2.57 m apart and the seed sits between them. The hits are therefore clustered
into slabs, and the slab chosen is the one continuing the station before it.
Continuity resolves what height cannot.

`sample_lowest_above` answers *is this at-grade road resting on a ramp*, which
continuity cannot: the road it is asked about is at level 0, so there is no
elevated run to stay on, and the structure of interest is whatever the road
sits directly on rather than whatever passes overhead. `P2-7` uses it from a
node where two levels meet, walking until the answer comes back down to the
ground.

Nothing here knows what is being placed on the surface. `roads.py` supplies the
points and decides what an uncovered one means.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

import numpy as np

from pipeline.gltf import MeshData

log = logging.getLogger(__name__)

# Triangles this close to vertical in plan view carry no usable height: a wall
# in the terrain mesh projects to a sliver, and its barycentric coordinates are
# a division by roughly zero. Compared against *twice* the signed plan area —
# the cross product itself — rather than the area, hence the name.
_MIN_PLAN_CROSS = 1e-9

# Shared rather than allocated per miss: most stations of a road resample fall
# outside the structure mesh entirely, and every one of them takes this path.
# Read-only because it is shared — a caller that wrote to a "no hits" result
# would be writing to every other one.
_NO_HITS = np.zeros(0)
_NO_HITS.flags.writeable = False


def _within(corners: np.ndarray, region_high: tuple[float, float] | None) -> np.ndarray:
    """Triangles whose plan bounding box meets `(0, 0)`-`region_high`."""
    if region_high is None:
        return corners
    plan = corners[:, :, [0, 2]]
    low, high = plan.min(axis=1), plan.max(axis=1)
    return corners[
        (high[:, 0] >= 0.0)
        & (low[:, 0] <= region_high[0])
        & (high[:, 1] >= 0.0)
        & (low[:, 1] <= region_high[1])
    ]


@dataclass(frozen=True)
class HeightField:
    """Terrain triangles in game space, indexed for point queries.

    Built once per region and asked for a few thousand heights, so the index is
    sized for cheap construction rather than for the fastest possible query: a
    uniform grid over the plan, with each triangle registered in every cell its
    plan bounding box touches.
    """

    # (m, 3, 3): triangle, corner, xyz. Game space, so y is height.
    corners: np.ndarray
    cell_m: float
    origin: np.ndarray  # (2,) plan-space corner the grid is measured from
    columns: int
    rows: int
    # Triangle indices ordered by cell, with the start of each cell's run. The
    # flat pair is a compressed adjacency list: a dict of 400,000 short lists
    # costs more to build than the queries ever save.
    cell_starts: np.ndarray
    cell_triangles: np.ndarray

    @classmethod
    def from_meshes(
        cls,
        meshes: Iterable[MeshData],
        *,
        cell_m: float = 8.0,
        region_high: tuple[float, float] | None = None,
    ) -> HeightField:
        """Index the triangles of the given meshes, already in game space.

        `region_high` bounds the area that will ever be queried, and triangles
        whose plan box does not meet `(0, 0)`-`region_high` are dropped before
        anything else happens. Published map sheets overlap a region rather than
        matching it: 54% of Wan Chai's six sheets of terrain lies outside it and
        can never be hit, but would otherwise be area-tested, binned, sorted and
        then held resident for the life of the object.

        A `meshes` generator is consumed one at a time and the cull applied per
        mesh, so a sheet's geometry is freed before the next is read.
        """
        blocks = [
            block
            for mesh in meshes
            if len(mesh.triangles)
            and len(block := _within(mesh.positions[mesh.triangles], region_high))
        ]
        if not blocks:
            raise ValueError("cannot build a height field from meshes with no triangles")
        corners = np.concatenate(blocks).astype(np.float64, copy=False)
        del blocks

        plan = corners[:, :, [0, 2]]
        # Twice the signed plan area. Near-vertical triangles are dropped here
        # rather than guarded against per query.
        edge_a = plan[:, 1] - plan[:, 0]
        edge_b = plan[:, 2] - plan[:, 0]
        usable = np.abs(edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0]) > _MIN_PLAN_CROSS
        corners = corners[usable]
        plan = plan[usable]
        if not len(corners):
            raise ValueError("every triangle of the height field is vertical in plan")

        origin = plan.reshape(-1, 2).min(axis=0)
        high = plan.reshape(-1, 2).max(axis=0)
        columns = max(1, int((high[0] - origin[0]) // cell_m) + 1)
        rows = max(1, int((high[1] - origin[1]) // cell_m) + 1)

        low_cell = np.floor((plan.min(axis=1) - origin) / cell_m).astype(np.int64)
        high_cell = np.floor((plan.max(axis=1) - origin) / cell_m).astype(np.int64)
        np.clip(low_cell[:, 0], 0, columns - 1, out=low_cell[:, 0])
        np.clip(high_cell[:, 0], 0, columns - 1, out=high_cell[:, 0])
        np.clip(low_cell[:, 1], 0, rows - 1, out=low_cell[:, 1])
        np.clip(high_cell[:, 1], 0, rows - 1, out=high_cell[:, 1])

        keys, triangles = _spread(low_cell, high_cell, columns)
        order = np.argsort(keys, kind="stable")
        keys, triangles = keys[order], triangles[order]
        cell_starts = np.searchsorted(keys, np.arange(columns * rows + 1))

        return cls(
            corners=corners,
            cell_m=cell_m,
            origin=origin,
            columns=columns,
            rows=rows,
            cell_starts=cell_starts.astype(np.int64),
            cell_triangles=triangles,
        )

    @property
    def triangle_count(self) -> int:
        return len(self.corners)

    def sample(
        self, x: Sequence[float] | np.ndarray, z: Sequence[float] | np.ndarray
    ) -> np.ndarray:
        """Ground height under each `(x, z)`, or NaN where the terrain has none.

        The highest surface found, because the ground is not single-valued
        everywhere — the two faces of a retaining wall or a sea wall both
        project onto the same plan position, and the one a vehicle can be on is
        the top.

        NaN rather than a fallback value, so the caller decides what an
        uncovered point means. Silently substituting zero here would reintroduce
        exactly the bug this module exists to fix, in the few places the terrain
        does not reach.
        """
        x, z, cells = self._cells(x, z)
        out = np.full(len(x), np.nan)
        for index, key in cells:
            hits = self._hits_at(key, x[index], z[index])
            if len(hits):
                out[index] = hits.max()
        return out

    def sample_along(
        self,
        x: Sequence[float] | np.ndarray,
        z: Sequence[float] | np.ndarray,
        *,
        slab_gap_m: float,
    ) -> np.ndarray:
        """Height of the surface a path stays on, or NaN where there is none.

        The points are consecutive stations along one path, and that ordering is
        the whole method: where a station sits over a stack — a deck over its own
        underside, or a flyover over a ramp — the slab chosen is the one nearest
        the station before it.

        The walk is anchored on the stations with exactly one slab. Those are
        unambiguous by construction, so a stacked run is resolved by what it
        connects to rather than by a seed height — which is the failure this
        query exists to avoid. `P2-7` measured them at 73% or more of the
        covered stations on every Wan Chai edge but one, and where an edge has
        no unambiguous station at all there is nothing to grow from, so it
        degrades to `sample`. The exception is ISLAND EASTERN CORRIDOR, which
        crosses the region on two stations and is stacked on both.

        Station spacing deliberately does not enter the choice. Comparing
        gradients rather than heights would rank the candidates at a station
        identically, since they all share the same gap to the one before.
        """
        slabs = self._slabs(x, z, slab_gap_m)

        chosen = np.full(len(slabs), np.nan)
        for index, tops in enumerate(slabs):
            if len(tops) == 1:
                chosen[index] = tops[0]

        def walk(order: range, behind: int) -> None:
            for index in order:
                tops, settled = slabs[index], chosen[index + behind]
                if np.isfinite(chosen[index]) or not len(tops) or not np.isfinite(settled):
                    continue
                chosen[index] = tops[int(np.abs(tops - settled).argmin())]

        # Every anchor seeds both directions, not just the first one: a station
        # with no structure under it settles nothing, and continuity cannot
        # cross it, so a path can hold several independently anchored runs.
        walk(range(1, len(slabs)), -1)
        walk(range(len(slabs) - 2, -1, -1), +1)

        # Whatever no anchor reached — a run walled off by such a gap, or every
        # station when the path is ambiguous end to end.
        for index in np.flatnonzero(np.isnan(chosen)):
            if len(slabs[index]):
                chosen[index] = slabs[index].max()
        return chosen

    def sample_lowest_above(
        self,
        x: Sequence[float] | np.ndarray,
        z: Sequence[float] | np.ndarray,
        floor: Sequence[float] | np.ndarray,
        *,
        slab_gap_m: float,
    ) -> np.ndarray:
        """Lowest slab top at or above `floor`, per point, or NaN where none is.

        The floor is per point rather than one value because the caller's is the
        terrain, which is not level. A NaN floor admits nothing: with no ground
        to measure against there is no way to tell a ramp from a flyover
        overhead, and the lowest slab is then as likely to be the wrong one.

        Lowest rather than highest, which is the opposite of `sample` and for the
        opposite reason. This asks what a road is resting *on*, so anything
        further up is something the road passes under — Canal Road Flyover over
        Gloucester Road is the case that decides it. `sample`'s question is what
        a vehicle could stand on, where the top face is the only candidate.
        """
        floor = np.asarray(floor, dtype=np.float64).reshape(-1)
        slabs = self._slabs(x, z, slab_gap_m)
        if len(floor) != len(slabs):
            raise ValueError(f"floor has {len(floor)} values for {len(slabs)} points")

        chosen = np.full(len(slabs), np.nan)
        for index, tops in enumerate(slabs):
            above = tops[tops >= floor[index]]
            if len(above):
                # `slab_tops` returns them ascending, so the first is the lowest.
                chosen[index] = above[0]
        return chosen

    def _slabs(
        self,
        x: Sequence[float] | np.ndarray,
        z: Sequence[float] | np.ndarray,
        slab_gap_m: float,
    ) -> list[np.ndarray]:
        """Slab tops under each point, ascending, empty where nothing is found.

        Shared by the two queries that pick among structures rather than among
        raw hits. Clustering is the expensive half and it is identical for both;
        only the choice made afterwards differs, and keeping that difference to
        one loop each is what makes the two comparable.
        """
        x, z, cells = self._cells(x, z)
        slabs: list[np.ndarray] = [_NO_HITS] * len(x)
        for index, key in cells:
            slabs[index] = slab_tops(self._hits_at(key, x[index], z[index]), slab_gap_m)
        return slabs

    def _cells(
        self, x: Sequence[float] | np.ndarray, z: Sequence[float] | np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, Iterator[tuple[int, int]]]:
        """Plan coordinates as flat arrays, and the grid cell of each point on it.

        Points off the grid are *absent* from the iterator rather than flagged in
        it, which is why both callers fill their result with NaN before looping
        instead of writing an answer for every point.
        """
        x = np.asarray(x, dtype=np.float64).reshape(-1)
        z = np.asarray(z, dtype=np.float64).reshape(-1)

        cells = np.floor((np.column_stack([x, z]) - self.origin) / self.cell_m).astype(np.int64)
        # Both axes are tested, not just the flattened key: a negative row with
        # a large column produces a key that lands back inside the range and
        # would query an unrelated cell on the row above.
        inside = (
            (cells[:, 0] >= 0)
            & (cells[:, 0] < self.columns)
            & (cells[:, 1] >= 0)
            & (cells[:, 1] < self.rows)
        )
        keys = cells[:, 0] + cells[:, 1] * self.columns
        on_grid = np.flatnonzero(inside)
        return x, z, zip(on_grid, keys[on_grid], strict=True)

    def _hits_at(self, key: int, x: float, z: float) -> np.ndarray:
        """Every surface height at `(x, z)`, from the triangles binned in `key`."""
        candidates = self.cell_triangles[self.cell_starts[key] : self.cell_starts[key + 1]]
        if not len(candidates):
            return _NO_HITS
        return _hits(self.corners[candidates], x, z)


def _spread(low: np.ndarray, high: np.ndarray, columns: int) -> tuple[np.ndarray, np.ndarray]:
    """Cell key and triangle index for every cell each triangle's box touches.

    Terrain triangles are a few metres across against an eight-metre cell, so
    most land in one or two cells. Measured on the real region: 1.94 entries per
    triangle.
    """
    spans = (high[:, 0] - low[:, 0] + 1) * (high[:, 1] - low[:, 1] + 1)
    triangles = np.repeat(np.arange(len(low), dtype=np.int64), spans)

    # Position within each triangle's own box, as a flat running index. The
    # subtracted term is the exclusive prefix sum of `spans`.
    within = np.arange(len(triangles), dtype=np.int64) - np.repeat(np.cumsum(spans) - spans, spans)
    width = np.repeat(high[:, 0] - low[:, 0] + 1, spans)
    keys = (
        np.repeat(low[:, 0], spans)
        + within % width
        + (np.repeat(low[:, 1], spans) + within // width) * columns
    )
    return keys, triangles


def slab_tops(hits: np.ndarray, gap_m: float) -> np.ndarray:
    """Top face of each distinct slab among `hits`, ascending.

    A closed volume is hit twice by a downward query — its top face and its
    underside — and only the top can be driven on. Runs of hits closer together
    than `gap_m` are taken to be one such structure.

    The two populations are separated, but not by much: across Wan Chai's
    elevated edges the gaps *within* a deck reach 2.57 m and the gaps *between*
    stacked structures start at 3.36 m. That 0.79 m is the whole margin a
    `gap_m` of 3.0 sits in, so it is a tuning value rather than a constant, and
    a second city should be measured rather than assumed.

    NaN hits are dropped rather than clustered. `np.sort` puts them last and no
    comparison against one is ever true, so a single NaN would otherwise survive
    as the top of the highest slab and propagate down the rest of a path.
    """
    hits = hits[np.isfinite(hits)]
    if not len(hits):
        return hits
    ordered = np.sort(hits)
    # Keep the last of each run, so the sentinel goes at the end — the mirror of
    # `surface.dedupe`, which keeps the first and puts it at the front.
    return ordered[np.concatenate([np.diff(ordered) > gap_m, [True]])]


def _hits(corners: np.ndarray, x: float, z: float) -> np.ndarray:
    """Interpolated height of every triangle covering `(x, z)`, in no order."""
    ax, az = corners[:, 0, 0], corners[:, 0, 2]
    bx, bz = corners[:, 1, 0] - ax, corners[:, 1, 2] - az
    cx, cz = corners[:, 2, 0] - ax, corners[:, 2, 2] - az

    twice_area = bx * cz - bz * cx
    px, pz = x - ax, z - az
    # Barycentric coordinates, scaled by the (signed) area so the sign test
    # below works without dividing first.
    beta = px * cz - pz * cx
    gamma = pz * bx - px * bz
    scale = np.where(twice_area < 0.0, -1.0, 1.0)
    magnitude = np.abs(twice_area)

    hit = (beta * scale >= 0.0) & (gamma * scale >= 0.0) & ((beta + gamma) * scale <= magnitude)
    if not hit.any():
        return _NO_HITS

    beta, gamma = beta[hit] / twice_area[hit], gamma[hit] / twice_area[hit]
    return (
        corners[hit, 0, 1]
        + beta * (corners[hit, 1, 1] - corners[hit, 0, 1])
        + gamma * (corners[hit, 2, 1] - corners[hit, 0, 1])
    )
