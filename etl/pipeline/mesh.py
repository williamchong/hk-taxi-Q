"""Geometry operations on decoded meshes: merging tiles and building LOD tiers.

Kept apart from `gltf.py`, which is only concerned with the file format. Nothing
here knows what a building is — `buildings.py` supplies the policy, this module
supplies the arithmetic.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from pipeline.gltf import MeshData, normalise


class EmptyMeshError(ValueError):
    """A `collapse` tier removed every triangle.

    Its own type so callers can catch *this* rather than `ValueError` at large.
    `MeshData.__post_init__` also raises `ValueError`, so a broad except here
    would downgrade a future invariant break to a silently missing LOD tier and
    let the run finish green.
    """


_FACINGS = 6


def _as_indices(triangles: np.ndarray) -> np.ndarray:
    """(m, 3) uint32.

    `np.unique(..., return_inverse=True)` returns int64, which then promotes
    every array it is concatenated with — doubling a merged tile's index buffer
    for vertex counts nowhere near 2^32.
    """
    return triangles.astype(np.uint32, copy=False).reshape(-1, 3)


def merge(meshes: Sequence[MeshData], *, name: str) -> MeshData:
    """Concatenate meshes into one, so the tile costs one draw call.

    Every input must carry vertex colours or none may: a merged primitive has a
    single attribute set, and a half-coloured one would render the uncoloured
    buildings at whatever the missing attribute defaults to.

    Textured meshes are rejected outright rather than merged. Two textures
    cannot share one primitive without repacking their UVs into an atlas, which
    this does not do — and silently keeping one texture and dropping the other
    would render the second mesh in a single wrong colour, with no error.
    """
    if not meshes:
        raise ValueError(f"cannot merge zero meshes into '{name}'")

    coloured = [mesh.colours is not None for mesh in meshes]
    if any(coloured) and not all(coloured):
        raise ValueError(
            f"'{name}': cannot merge coloured and uncoloured meshes into one primitive"
        )
    if any(mesh.texture is not None or mesh.uvs is not None for mesh in meshes):
        raise ValueError(f"'{name}': cannot merge textured meshes — that needs a UV atlas")

    # uint32 rather than the int64 a Python-list cumsum defaults to, which would
    # promote every merged index array and double the index buffer.
    offsets = np.cumsum([0] + [len(mesh.positions) for mesh in meshes[:-1]], dtype=np.uint32)
    return MeshData(
        name=name,
        positions=np.concatenate([mesh.positions for mesh in meshes]),
        normals=np.concatenate([mesh.normals for mesh in meshes]),
        triangles=np.concatenate(
            [mesh.triangles + offset for mesh, offset in zip(meshes, offsets, strict=True)]
        ),
        colours=np.concatenate([mesh.colours for mesh in meshes]) if all(coloured) else None,
    )


def select_triangles(mesh: MeshData, keep: np.ndarray) -> MeshData | None:
    """The kept triangles as a mesh of their own, or None if none were kept.

    Vertices no surviving triangle uses are dropped, but no vertex is moved and
    no triangle is cut. Two selections that partition a mesh therefore abut
    exactly — there is no seam to close between them.
    """
    triangles = mesh.triangles[keep]
    if len(triangles) == 0:
        return None

    used, triangles = np.unique(triangles, return_inverse=True)
    return MeshData(
        name=mesh.name,
        positions=mesh.positions[used],
        normals=mesh.normals[used],
        triangles=_as_indices(triangles),
        colours=None if mesh.colours is None else mesh.colours[used],
        uvs=None if mesh.uvs is None else mesh.uvs[used],
        texture=mesh.texture,
    )


def collapse(mesh: MeshData, *, cell_m: float) -> MeshData:
    """Merge vertices sharing a grid cell and a facing; drop triangles that fold.

    Vertex clustering rather than quadric error decimation. Three reasons it is
    the right tool for this data specifically:

    - The source is extruded footprints. Clustering keeps silhouettes blocky and
      axis-aligned, which *is* the art direction; quadric decimation smooths
      corners, which fights it.
    - It is robust on triangle soup. These meshes are unwelded, non-manifold in
      places, and share no topology between buildings — the conditions under
      which edge-collapse decimators produce holes.
    - Its aggressiveness is one number in metres, so the LOD tiers stay tuning
      data in city config rather than a curve in code (CLAUDE.md hard rule 4).

    Keying on facing as well as position is what preserves flat shading. Merge
    on position alone and a wall vertex averages with the roof vertex above it,
    rounding off the hard normals the source ships and the style depends on.

    `cell_m <= 0` welds exactly: same position, same normal, one vertex. That is
    LOD0 — lossless, and worth doing because the source repeats every vertex per
    triangle.
    """
    exact = cell_m <= 0.0
    if exact:
        # Raw float64 positions and normals cannot be packed into one integer,
        # so this tier pays for the row-wise unique.
        key = np.column_stack([mesh.positions, mesh.normals])
        _, representative, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    else:
        representative, inverse = _cluster_bins(mesh, cell_m)
    inverse = inverse.reshape(-1)

    triangles = inverse[mesh.triangles]
    triangles = _drop_degenerate(triangles)
    triangles = _drop_duplicates(triangles)
    if len(triangles) == 0:
        raise EmptyMeshError(f"mesh '{mesh.name}': collapsing at {cell_m} m left no triangles")

    # Clusters no surviving triangle refers to are dead weight in the vertex
    # buffer. Compacting here rather than at write time keeps the triangle-count
    # and vertex-count figures the report quotes honest.
    used, triangles = np.unique(triangles, return_inverse=True)
    triangles = _as_indices(triangles)

    if exact:
        # Every member of an exact cluster compares equal, so one of them *is*
        # the answer. Averaging would be shorter to write, but summing k equal
        # doubles and dividing by k is not guaranteed to reproduce them — and
        # "lossless" is a claim this tier makes.
        #
        # Compares equal, not bit-identical: `np.unique` sorts by value, so +0.0
        # and -0.0 share a cluster. Taking a representative still yields a real
        # source value, which is the property that matters.
        chosen = representative[used]
        positions = mesh.positions[chosen]
        normals = mesh.normals[chosen]
    else:
        clusters = len(representative)
        positions = _cluster_mean(mesh.positions, inverse, clusters)[used]
        normals = normalise(_cluster_mean(mesh.normals, inverse, clusters)[used]).astype(np.float32)

    return MeshData(
        name=mesh.name,
        positions=positions,
        normals=normals,
        triangles=triangles,
        # Colour and UV come from one representative vertex rather than a mean.
        # Averaging two buildings' colours where their walls meet would invent a
        # third colour along the seam; taking one side's is invisible.
        colours=None if mesh.colours is None else mesh.colours[representative][used],
        uvs=None if mesh.uvs is None else mesh.uvs[representative][used],
        texture=mesh.texture,
    )


def _cluster_bins(mesh: MeshData, cell_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Cluster a binned tier, keyed on one integer per vertex.

    `np.unique(..., axis=0)` views each row as a void and argsorts it with
    memcmp comparisons, which measured **83% of the whole build**. Binned keys
    are small integers, so they fit a single int64 in mixed-radix — most
    significant digit first, which reproduces the lexicographic order the
    row-wise sort produced. Same clusters, same ordering, therefore byte
    identical output: measured 8.2x faster on this stage, ~40% off the build.

    Falls back to the row-wise path if the grid is too large to encode, which
    needs a region ~3,500 km across at 1.5 m cells.
    """
    cells = np.floor(mesh.positions / cell_m).astype(np.int64)
    facing = _facing(mesh.normals).reshape(-1)

    low = cells.min(axis=0)
    span = (cells.max(axis=0) - low + 1).tolist()
    if span[0] * span[1] * span[2] * _FACINGS >= 2**63:
        key = np.column_stack([cells, facing])
        _, representative, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
        return representative, inverse

    offsets = cells - low
    packed = (offsets[:, 0] * span[1] + offsets[:, 1]) * span[2] + offsets[:, 2]
    _, representative, inverse = np.unique(
        packed * _FACINGS + facing, return_index=True, return_inverse=True
    )
    return representative, inverse


def _facing(normals: np.ndarray) -> np.ndarray:
    """Bucket normals by dominant signed axis, as a single column.

    Six buckets, one per signed axis. Coarse on purpose: the source is extruded
    footprints, where the distinction worth preserving is wall from roof from
    soffit. A finer split would keep detail the LOD tiers exist to lose.
    """
    axis = np.abs(normals).argmax(axis=1)
    sign = np.take_along_axis(normals, axis[:, None], axis=1).reshape(-1) < 0
    return (axis * 2 + sign).reshape(-1, 1)


def _cluster_mean(values: np.ndarray, inverse: np.ndarray, clusters: int) -> np.ndarray:
    counts = np.bincount(inverse, minlength=clusters).astype(np.float64)
    sums = np.stack(
        [np.bincount(inverse, weights=values[:, axis], minlength=clusters) for axis in range(3)],
        axis=1,
    )
    return sums / counts[:, None]


def _drop_degenerate(triangles: np.ndarray) -> np.ndarray:
    """Remove triangles whose corners collapsed onto each other.

    This is where the decimation actually happens: clustering merges vertices,
    and a triangle small enough to fit inside one cell then has two or three
    corners pointing at the same vertex and no area left to draw.
    """
    a, b, c = triangles.T
    return triangles[(a != b) & (b != c) & (a != c)]


def _drop_duplicates(triangles: np.ndarray) -> np.ndarray:
    """Remove triangles that became coincident with another.

    Two parallel walls a metre apart merge into one at LOD2, leaving the same
    triangle twice — invisible, but z-fighting and paid for on every draw.
    Compared on sorted corners so winding does not hide a duplicate.
    """
    _, first = np.unique(np.sort(triangles, axis=1), axis=0, return_index=True)
    return triangles[np.sort(first)]
