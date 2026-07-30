"""Ground level, sampled from the source terrain mesh (`Q11`).

Road Network v2 carries no Z ordinate, and `elevation_levels` maps grade
separation to an *offset* — it never said what that offset is measured from.
`P1-2` measured the gap: 99.9% of Wan Chai's buildings have their base above
2 m, median 4.29 m. Taking level 0 as y=0 would run Hennessy Road four metres
below the doorways on it, and below the terrain surface as well.

The LandsD sheets ship a real height field covering the whole region, we already
parse it, and sampling happens at build time — so it costs nothing at runtime.
That is the strongest reason to keep the terrain in the pipeline even if it is
never rendered; see the `P1-2` terrain decision in `docs/PROGRESS.md`.

Nothing here knows what is being placed on the ground. `roads.py` supplies the
points and adds the deck height.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from pipeline.gltf import MeshData

log = logging.getLogger(__name__)

# Triangles this close to vertical in plan view carry no usable height: a wall
# in the terrain mesh projects to a sliver, and its barycentric coordinates are
# a division by roughly zero. Compared against *twice* the signed plan area —
# the cross product itself — rather than the area, hence the name.
_MIN_PLAN_CROSS = 1e-9


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

        NaN rather than a fallback value, so the caller decides what an
        uncovered point means. Silently substituting zero here would reintroduce
        exactly the bug this module exists to fix, in the few places the terrain
        does not reach.
        """
        x = np.asarray(x, dtype=np.float64).reshape(-1)
        z = np.asarray(z, dtype=np.float64).reshape(-1)
        out = np.full(len(x), np.nan)

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

        for index in np.flatnonzero(inside):
            key = keys[index]
            candidates = self.cell_triangles[self.cell_starts[key] : self.cell_starts[key + 1]]
            if len(candidates):
                out[index] = _highest_hit(self.corners[candidates], x[index], z[index])
        return out


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


def _highest_hit(corners: np.ndarray, x: float, z: float) -> float:
    """Interpolated height of the upper triangle covering `(x, z)`, or NaN.

    Upper, because the ground surface is not single-valued everywhere — the two
    faces of a retaining wall or a sea wall both project onto the same plan
    position, and the one a vehicle can be on is the top.
    """
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
        return float("nan")

    beta, gamma = beta[hit] / twice_area[hit], gamma[hit] / twice_area[hit]
    height = (
        corners[hit, 0, 1]
        + beta * (corners[hit, 1, 1] - corners[hit, 0, 1])
        + gamma * (corners[hit, 2, 1] - corners[hit, 0, 1])
    )
    return float(height.max())
