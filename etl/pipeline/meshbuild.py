"""Shared mesh accumulators for the painted and furniture layers (`Q100`).

Two families, which between them were six byte-identical `polygon()` methods:

- `FlatBuilder` — horizontal paint (arrows, box junctions, road marks). One
  up-normal for the whole mesh, position and normal only.
- `ColouredBuilder` — vertical furniture (signs, signals, lamps). A normal per
  polygon, because everything faces a different sideways, and a `COLOR_0` per
  polygon, because a whole layer is one draw call.

⚠️ **Which channels a layer ships is a per-stage decision and stays recorded in
each stage**, beside the `.tres` and shader that read them — `arrows.py` refuses
`COLOR_0` for the same `Q54` bar under which `signs.py` requires it. What lives
here is only the accumulation arithmetic.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from pipeline.gltf import MeshData
from pipeline.mesh import select_triangles

# Below this, twice a triangle's area means it has collapsed and it is dropped
# rather than shipped. Compared against *twice* the area, which is what the
# cross product's length gives — a square millimetre of road is not road, a
# collision shape built from degenerate triangles is a collision shape with
# holes in it, and a zero-area triangle has no normal for `facing_away` to
# grade, so it would sit in the count forever.
MIN_TWICE_AREA_M2 = 1e-6


class SliverReport(Protocol):
    """Any stage report that counts the slivers `FlatBuilder.build` drops."""

    slivers_dropped: int


class FlatBuilder:
    """Accumulates flat convex polygons into one mesh.

    Every polygon is horizontal and convex, so a fan from its first vertex
    triangulates it, and the normal is up.
    """

    def __init__(self, material: str) -> None:
        self._material = material
        self._positions: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def polygon(self, plan: np.ndarray, height: np.ndarray) -> None:
        span = len(plan)
        if span < 3:
            return
        base = self._count
        fan = np.arange(1, span - 1)
        self._triangles.append(
            np.column_stack([np.zeros(len(fan), dtype=np.int64), fan, fan + 1]) + base
        )
        self._positions.append(np.column_stack([plan[:, 0], height, plan[:, 1]]))
        self._count += span

    def build(
        self,
        name: str,
        thin_bar_m: float = 0.0,
        report: SliverReport | None = None,
    ) -> MeshData | None:
        """The mesh, minus collapsed triangles and sub-lattice slivers.

        ⚠️ The sliver bar is judged **per triangle, not per polygon** — a convex
        quad wider than the bar can still fan into one sound triangle and one
        needle along its long diagonal, and the needle is what the import
        lattice flips. Judged per polygon first, 37 of the box junctions'
        survived to fail the engine-side check; per triangle, none do. At the
        default bar of zero nothing is a sliver and nothing is counted.
        """
        if not self._triangles:
            return None
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.tile(np.array([0.0, 1.0, 0.0], dtype=np.float32), (self._count, 1)),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            material=self._material,
        )
        cross = mesh.triangle_cross()
        twice_area = np.linalg.norm(cross, axis=1)
        corners = mesh.positions[mesh.triangles][:, :, [0, 2]]
        sides = np.roll(corners, -1, axis=1) - corners
        longest = np.linalg.norm(sides, axis=2).max(axis=1)
        # Plan twice-area over the longest plan edge — twice the width, for a
        # rectangle — against the lattice bar `_import_quantum_m` explains.
        thin = np.abs(cross[:, 1]) < thin_bar_m * np.where(longest > 0.0, longest, 1.0)
        if report is not None:
            report.slivers_dropped = int(thin.sum())
        return select_triangles(mesh, (twice_area > MIN_TWICE_AREA_M2) & ~thin)


class ColouredBuilder:
    """Accumulates flat convex polygons, each with its own colour and normal."""

    def __init__(self, material: str) -> None:
        self._material = material
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._colours: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def polygon(self, points: np.ndarray, normal: np.ndarray, colour: tuple[int, int, int]) -> None:
        """One convex polygon in world space, already wound to face `normal`."""
        span = len(points)
        if span < 3:
            return
        base = self._count
        fan = np.arange(1, span - 1)
        self._triangles.append(
            np.column_stack([np.zeros(len(fan), dtype=np.int64), fan, fan + 1]) + base
        )
        self._positions.append(points)
        self._normals.append(np.tile(normal.astype(np.float32), (span, 1)))
        self._colours.append(np.tile(np.array([*colour, 255], dtype=np.uint8), (span, 1)))
        self._count += span

    def build(self, name: str) -> MeshData | None:
        if not self._triangles:
            return None
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.vstack(self._normals),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            colours=np.vstack(self._colours),
            material=self._material,
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        return select_triangles(mesh, twice_area > MIN_TWICE_AREA_M2)


def import_quantum_m(points: np.ndarray) -> float:
    """The plan pitch Godot's importer would quantise a region-spanning mesh to.

    `span / 65535` — the 16-bit lattice the scene importer used to compress
    vertex positions onto, about **17 mm** for Wan Chai. ✅ `Q82` turned
    `meshes/force_disable_compression` on project-wide, so the lattice no longer
    exists at import; the callers keep their guards anyway, and say why. Derived
    from the features' own extent rather than authored, because the pitch is a
    property of the region's size, not a number anyone should tune.
    """
    if len(points) == 0:
        return 0.0
    spans = points.max(axis=0) - points.min(axis=0)
    return float(spans.max()) / 65535.0
