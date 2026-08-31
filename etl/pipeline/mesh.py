"""Geometry operations on decoded meshes: merging tiles and building LOD tiers.

Kept apart from `gltf.py`, which is only concerned with the file format. Nothing
here knows what a building is — `buildings.py` supplies the policy, this module
supplies the arithmetic.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np

from pipeline.gltf import MeshData, normalise

# How a slicer lands a point on its plane, given the two endpoints of an edge
# that strictly straddles it. Passed rather than derived so each slicer keeps
# its own arithmetic — see `_slice_corners`.
_Cut = Callable[[np.ndarray, np.ndarray], np.ndarray]


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

    Every input must carry vertex colours or none may, and the same for UVs: a
    merged primitive has a single attribute set, and a half-coloured one would
    render the uncoloured buildings at whatever the missing attribute defaults
    to.

    Textured meshes are rejected outright rather than merged. Two textures
    cannot share one primitive without repacking their UVs into an atlas, which
    this does not do — and silently keeping one texture and dropping the other
    would render the second mesh in a single wrong colour, with no error.

    ⚠️ **UVs without a texture are a different question, and they merge** (`P3-7`).
    This rejected both together until the window-band shader needed a payload
    the geometry cannot derive: height above the building's own base, and a
    per-building seed. That is a coordinate meant for a *shader*, not for an
    image, so the atlas objection does not reach it — nothing has to be repacked
    because nothing is being sampled. The texture half of the guard is unchanged
    and still catches the case it was written for.

    **`material` is not carried, where `collapse` and `select_triangles` do carry
    it.** Those are one mesh in and one out, so the answer is unambiguous; this
    takes many and a merged primitive has exactly one material, so inheriting
    whichever mesh happened to be first would be a coin toss with no error. The
    caller that merges a tile names the result — see `buildings._write_tile`.
    """
    if not meshes:
        raise ValueError(f"cannot merge zero meshes into '{name}'")

    coloured = [mesh.colours is not None for mesh in meshes]
    if any(coloured) and not all(coloured):
        raise ValueError(
            f"'{name}': cannot merge coloured and uncoloured meshes into one primitive"
        )
    if any(mesh.texture is not None for mesh in meshes):
        raise ValueError(f"'{name}': cannot merge textured meshes — that needs a UV atlas")
    mapped = [mesh.uvs is not None for mesh in meshes]
    if any(mapped) and not all(mapped):
        raise ValueError(f"'{name}': cannot merge meshes with and without UVs into one primitive")
    has_uv2 = [mesh.uv2 is not None for mesh in meshes]
    if any(has_uv2) and not all(has_uv2):
        raise ValueError(f"'{name}': cannot merge meshes with and without UV2 into one primitive")

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
        uvs=np.concatenate([mesh.uvs for mesh in meshes]) if all(mapped) else None,
        uv2=np.concatenate([mesh.uv2 for mesh in meshes]) if all(has_uv2) else None,
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
        uv2=None if mesh.uv2 is None else mesh.uv2[used],
        texture=mesh.texture,
        material=mesh.material,
    )


# On-plane tolerance for `slice_horizontal`, in metres. Well under any band
# thickness the paint will express, and far above float64 noise at sheet
# magnitudes (~1e-10 m around easting 836,000).
_ON_PLANE_M = 1e-6


def slice_horizontal(mesh: MeshData, heights: Sequence[float]) -> MeshData:
    """Cut every triangle that crosses a horizontal plane; move no vertex.

    Vertex colours interpolate across a triangle, so a colour boundary is only
    crisp along edges the mesh actually has. This supplies those edges: after
    slicing, no triangle spans any of `heights`, so a per-triangle paint can
    express a band boundary exactly (`landmarks.paint` is the caller).

    The output is unshared — three vertices per triangle — which is both the
    form the sheet sources arrive in and the invariant a per-triangle paint
    needs: colouring a shared vertex would bleed into its neighbours. Sharing
    in the input is tolerated and flattened.

    A vertex within `_ON_PLANE_M` of a plane counts as *on* it and is never
    cut through; cut points get their y written to exactly the plane height,
    so a later plane at the same height re-classifies them as on rather than
    re-cutting. Cut edges are interpolated lower-endpoint-first regardless of
    winding, so the two triangles sharing an edge compute bit-identical cut
    points and the sliced surface stays closed. Every cut lands strictly
    inside an edge (the endpoints are strictly on opposite sides), so no
    degenerate triangle is created and nothing needs dropping afterwards.
    """
    corners, widths = _unpack(mesh)

    for height in sorted(set(float(h) for h in heights)):
        y = corners[:, :, 1]
        if height <= y.min() + _ON_PLANE_M or height >= y.max() - _ON_PLANE_M:
            continue
        # ⚠️ Written as a comparison against a shifted plane rather than against
        # a signed distance, and `slice_plane` below does the opposite. The two
        # are not bit-identical near the tolerance, and this is the form that
        # published `landmarks/*.glb`; keeping it is what lets the topology be
        # shared without moving a single hero vertex.
        side = np.zeros(y.shape, dtype=np.int8)
        side[y > height + _ON_PLANE_M] = 1
        side[y < height - _ON_PLANE_M] = -1
        corners = _slice_corners(corners, side, lambda a, b, h=height: _cut_edge(a, b, h))

    return _rebuild(mesh, corners, widths)


def slice_plane(mesh: MeshData, normal: Sequence[float], offset: float) -> MeshData:
    """Cut every triangle that crosses an arbitrary plane; move no vertex.

    `slice_horizontal` generalised off the Y axis, for `carve.py`, whose cutting
    prism has two vertical walls at whatever bearing the centreline runs and two
    end planes square to it. The plane is `dot(p, normal) == offset` with
    `normal` unit-length after normalisation; the half-space `dot(p, normal) >
    offset` is the *outside*, so a caller wanting to keep the outside pairs this
    with `select_triangles` on the same test.

    This **subdivides and keeps everything**, exactly as `slice_horizontal`
    does. It is not a clip: nothing is discarded here, and after slicing no
    triangle spans the plane, so a whole-triangle selection afterwards abuts it
    exactly and leaves no seam.

    ⚠️ **Cutting alone opens a shell.** The source meshes are surfaces, not
    solids, so removing the inside of a closed volume leaves backfaces that cull
    to nothing — an invisible hole. Capping the cut is the caller's job and it
    is load-bearing, not cosmetic.
    """
    unit = np.asarray(normal, dtype=np.float64).reshape(3)
    length = float(np.sqrt(unit @ unit))
    if length <= 0.0:
        raise ValueError(f"slice_plane needs a non-zero normal, got {normal!r}")
    unit = unit / length
    offset = float(offset)

    corners, widths = _unpack(mesh)
    distance = corners[:, :, :3] @ unit - offset
    if distance.min() >= -_ON_PLANE_M or distance.max() <= _ON_PLANE_M:
        return _rebuild(mesh, corners, widths)

    side = np.zeros(distance.shape, dtype=np.int8)
    side[distance > _ON_PLANE_M] = 1
    side[distance < -_ON_PLANE_M] = -1
    corners = _slice_corners(corners, side, lambda a, b: _cut_edge_on_plane(a, b, unit, offset))
    return _rebuild(mesh, corners, widths)


def _unpack(mesh: MeshData) -> tuple[np.ndarray, list[int]]:
    """Every channel widened to float64 and gathered per triangle corner.

    One array rather than several so a cut interpolates position, normal, colour
    and both UV sets in the same expression — a channel left behind is a cut
    vertex carrying its neighbour's colour, which renders as a plausible smudge.
    """
    channels = [mesh.positions, mesh.normals.astype(np.float64)]
    widths = [3, 3]
    for values in (mesh.colours, mesh.uvs, mesh.uv2):
        if values is not None:
            channels.append(values.astype(np.float64))
            widths.append(values.shape[1])
    return np.concatenate(channels, axis=1)[mesh.triangles], widths


def _rebuild(mesh: MeshData, corners: np.ndarray, widths: list[int]) -> MeshData:
    """`_unpack`'s inverse: unshared triangles, every channel narrowed back."""
    parts = np.split(corners.reshape(-1, corners.shape[2]), np.cumsum(widths)[:-1], axis=1)
    optional = iter(parts[2:])
    return MeshData(
        name=mesh.name,
        positions=np.ascontiguousarray(parts[0]),
        normals=normalise(parts[1]).astype(np.float32),
        triangles=_as_indices(np.arange(len(corners) * 3).reshape(-1, 3)),
        colours=None
        if mesh.colours is None
        else np.clip(np.rint(next(optional)), 0, 255).astype(np.uint8),
        uvs=None if mesh.uvs is None else next(optional).astype(np.float32),
        uv2=None if mesh.uv2 is None else next(optional).astype(np.float32),
        texture=mesh.texture,
        material=mesh.material,
    )


def _slice_corners(corners: np.ndarray, side: np.ndarray, cut: _Cut) -> np.ndarray:
    """One plane's worth of cutting, given each corner's side of it.

    Shared by `slice_horizontal` and `slice_plane` because the topology — which
    triangles cross, which corner is alone on its side, and the winding each
    piece inherits — is the whole subtlety here and does not depend on which
    plane is being cut.

    🔴 **The side array and the cut arithmetic are the caller's, deliberately.**
    Both differ between the two in their last bits, and the horizontal case
    already published `landmarks/*.glb`. Deriving either here would make one of
    them agree with the other rather than with what it shipped.
    """
    crossing = (side == 1).any(axis=1) & (side == -1).any(axis=1)
    if not crossing.any():
        return corners
    pieces = [corners[~crossing]]
    # A crossing triangle has at most one on-plane corner: two would leave
    # a single strict side, which is not a crossing.
    on_plane = side == 0
    split_two = crossing & on_plane.any(axis=1)
    split_three = crossing & ~on_plane.any(axis=1)
    if split_two.any():
        pieces.extend(_split_at_on_corner(corners[split_two], side[split_two], cut))
    if split_three.any():
        pieces.extend(_split_at_lone_corner(corners[split_three], side[split_three], cut))
    return np.concatenate(pieces)


def _rotate_corners(corners: np.ndarray, pivot: np.ndarray) -> np.ndarray:
    """Each triangle cycled so its pivot corner comes first. Winding survives."""
    order = (pivot[:, None] + np.arange(3)[None, :]) % 3
    return np.take_along_axis(corners, order[:, :, None], axis=1)


def _cut_edge(a: np.ndarray, b: np.ndarray, height: float) -> np.ndarray:
    """Where edge a-b meets the plane, interpolated lower-endpoint-first.

    The endpoints are strictly on opposite sides, so the denominator cannot
    vanish. Ordering by height before interpolating makes the arithmetic
    identical for the neighbouring triangle that walks the same edge the other
    way — same values in, bit-identical cut point out, no crack.
    """
    swap = a[:, 1] > b[:, 1]
    low = np.where(swap[:, None], b, a)
    high = np.where(swap[:, None], a, b)
    t = (height - low[:, 1]) / (high[:, 1] - low[:, 1])
    cut = low + t[:, None] * (high - low)
    cut[:, 1] = height
    return cut


def _cut_edge_on_plane(
    a: np.ndarray, b: np.ndarray, normal: np.ndarray, offset: float
) -> np.ndarray:
    """Where edge a-b meets an arbitrary plane, interpolated from the low side.

    `_cut_edge`'s discipline off the Y axis: order the endpoints by signed
    distance before interpolating, so the neighbouring triangle walking the same
    edge the other way does identical arithmetic and produces a bit-identical
    cut point. The endpoints are strictly on opposite sides, so the denominator
    cannot vanish and the ordering is unambiguous.

    ⚠️ The result is **projected** onto the plane rather than having one
    component assigned. `_cut_edge` can assign because a horizontal plane fixes
    exactly one coordinate; here all three move, and the projection is what
    guarantees the point satisfies the plane equation rather than merely coming
    close to it.
    """
    da = a[:, :3] @ normal - offset
    db = b[:, :3] @ normal - offset
    swap = da > db
    low = np.where(swap[:, None], b, a)
    high = np.where(swap[:, None], a, b)
    low_d = np.where(swap, db, da)
    high_d = np.where(swap, da, db)
    t = -low_d / (high_d - low_d)
    cut = low + t[:, None] * (high - low)
    cut[:, :3] -= (cut[:, :3] @ normal - offset)[:, None] * normal
    return cut


def _split_at_on_corner(corners: np.ndarray, side: np.ndarray, cut: _Cut) -> list[np.ndarray]:
    """(O, B, C) with O on the plane: cut B-C at D, yield (O, B, D), (O, D, C)."""
    rotated = _rotate_corners(corners, np.argmax(side == 0, axis=1))
    o, b, c = rotated[:, 0], rotated[:, 1], rotated[:, 2]
    d = cut(b, c)
    return [np.stack([o, b, d], axis=1), np.stack([o, d, c], axis=1)]


def _split_at_lone_corner(corners: np.ndarray, side: np.ndarray, cut: _Cut) -> list[np.ndarray]:
    """(A, B, C) with A alone on its side: cut A-B at D and A-C at E, yield
    the tip (A, D, E) and the far quad as (D, B, C), (D, C, E).

    The sides are a permutation of (+1, -1, -1) or (-1, +1, +1), so the row
    sum is the majority sign and the lone corner is the one carrying its
    negation.
    """
    majority = side.sum(axis=1, dtype=np.int8)
    rotated = _rotate_corners(corners, np.argmax(side == -majority[:, None], axis=1))
    a, b, c = rotated[:, 0], rotated[:, 1], rotated[:, 2]
    d = cut(a, b)
    e = cut(a, c)
    return [
        np.stack([a, d, e], axis=1),
        np.stack([d, b, c], axis=1),
        np.stack([d, c, e], axis=1),
    ]


def weld(mesh: MeshData) -> MeshData:
    """Share vertices that agree in **every** attribute; change no triangle.

    The lossless counterpart of `collapse(cell_m=0)`, differing in one way that
    matters to a painted mesh: the key includes colours and UVs, so two
    coincident vertices on opposite sides of a colour boundary stay separate
    and the boundary stays crisp. The exact-weld path in `collapse` keys on
    position and normal only, which would weld those pairs and bleed one
    band's colour into its neighbour.

    Worth running after a per-triangle paint (`landmarks.paint`), whose
    unshared input triples the vertex buffer: everywhere the paint agreed the
    duplicates collapse back, and everywhere it disagreed they were never
    mergeable anyway. Rendering is identical either way.
    """
    channels = [mesh.positions, mesh.normals.astype(np.float64)]
    for values in (mesh.colours, mesh.uvs, mesh.uv2):
        if values is not None:
            channels.append(values.astype(np.float64))
    _, representative, inverse = np.unique(
        np.column_stack(channels), axis=0, return_index=True, return_inverse=True
    )
    return MeshData(
        name=mesh.name,
        positions=mesh.positions[representative],
        normals=mesh.normals[representative],
        triangles=_as_indices(inverse.reshape(-1)[mesh.triangles]),
        colours=None if mesh.colours is None else mesh.colours[representative],
        uvs=None if mesh.uvs is None else mesh.uvs[representative],
        uv2=None if mesh.uv2 is None else mesh.uv2[representative],
        texture=mesh.texture,
        material=mesh.material,
    )


def collapse(mesh: MeshData, *, cell_m: float, height_field: bool = False) -> MeshData:
    """Merge vertices sharing a grid cell — and, unless `height_field`, a facing;
    drop triangles that fold.

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

    ⚠️ **`height_field` drops that facing term, and a single-sided sheet needs it
    dropped.** The rule above is a rule about *solids*: a wall and a roof meet at
    a hard edge that must survive, and a small tear where they meet is inside a
    closed volume where nothing can see it. Ground is a sheet with one height per
    plan position and no wall-versus-roof distinction to preserve — so the facing
    key cannot help it, and where a slope crosses one of the six buckets the
    shared vertices land in different clusters, move to different means, and
    **the surface tears open**. Every such tear is a hole through to the sky,
    which is why the gaps appear exactly where the ground is sloped.

    Measured on Wan Chai's terrain at a 4 m cell: region coverage **99.61% with
    the facing key against 99.84% without**, for 163,913 triangles against
    164,494 — better coverage and slightly fewer triangles. This is not a tuning
    value under hard rule 4; it is a statement about what the class *is*, which
    is why the caller decides it from the class name rather than from config.

    ⚠️ **It is only safe under the invariant its name states.** With the facing
    key gone, `_cluster_mean` can average two normals that oppose each other and
    `normalise` hands back a zero vector for the pair — impossible on the binned
    path before, because two normals in the same signed-axis bucket cannot
    cancel. A height field has one surface per plan position and so no opposed
    pair to average; anything with an inside does, and must not be passed this.
    Nothing checks it, which is the other reason the caller decides it from the
    class rather than from a config key someone could set on a building.

    `cell_m <= 0` welds exactly: same position, same normal, one vertex —
    lossless, and worth doing because the source repeats every vertex per
    triangle. Whether any tier asks for it is the city's choice; Hong Kong
    stopped shipping one at Q16.
    """
    exact = cell_m <= 0.0
    if exact:
        # Raw float64 positions and normals cannot be packed into one integer,
        # so this tier pays for the row-wise unique. An exact weld keeps the
        # normal whatever the caller said: it merges only vertices that already
        # agree on one, so there is no facing to tear along.
        key = np.column_stack([mesh.positions, mesh.normals])
        _, representative, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    else:
        representative, inverse = _cluster_bins(mesh, cell_m, height_field=height_field)
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
        # ⚠️ **A UV2 payload must be constant across whatever this clusters**, or
        # the representative invents a state no source vertex carried. That is a
        # rule for every layer that ships the channel, not a property of one:
        # the tiles' survey payload was reduced to a verdict per *building*
        # before emission for exactly this reason, and it is why a per-face
        # payload could never have ridden here. (Those tiles no longer ship a
        # UV2 at all — `Q102` — but the constraint outlived them.)
        uv2=None if mesh.uv2 is None else mesh.uv2[representative][used],
        texture=mesh.texture,
        material=mesh.material,
    )


def _cluster_bins(
    mesh: MeshData, cell_m: float, *, height_field: bool
) -> tuple[np.ndarray, np.ndarray]:
    """Cluster a binned tier, keyed on one integer per vertex.

    `np.unique(..., axis=0)` views each row as a void and argsorts it with
    memcmp comparisons, which measured **83% of the whole build**. Binned keys
    are small integers, so they fit a single int64 in mixed-radix — most
    significant digit first, which reproduces the lexicographic order the
    row-wise sort produced. Same clusters, same ordering, therefore byte
    identical output: measured 8.2x faster on this stage, ~40% off the build.

    Falls back to the row-wise path if the grid is too large to encode, which
    needs a region ~3,500 km across at 1.5 m cells.

    `height_field` collapses the facing term to one bucket rather than removing
    it, so both paths keep their shape, the packing arithmetic is unchanged and
    the overflow guard below stays exact — see `collapse` for why a sheet wants
    it gone. Required rather than defaulted: the one caller always decides it,
    and a default here is what a second caller would silently inherit wrong.
    """
    cells = np.floor(mesh.positions / cell_m).astype(np.int64)
    if height_field:
        facings, facing = 1, np.zeros(len(mesh.positions), dtype=np.int64)
    else:
        facings, facing = _FACINGS, _facing(mesh.normals).reshape(-1)

    low = cells.min(axis=0)
    span = (cells.max(axis=0) - low + 1).tolist()
    if span[0] * span[1] * span[2] * facings >= 2**63:
        key = np.column_stack([cells, facing])
        _, representative, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
        return representative, inverse

    offsets = cells - low
    packed = (offsets[:, 0] * span[1] + offsets[:, 1]) * span[2] + offsets[:, 2]
    _, representative, inverse = np.unique(
        packed * facings + facing, return_index=True, return_inverse=True
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


def subtract_prism(
    mesh: MeshData, planes: Sequence[tuple[np.ndarray, float]]
) -> tuple[MeshData | None, MeshData | None]:
    """`mesh` split by a convex prism into the part outside it and the part in.

    Each plane is `(normal, offset)` with the prism on the `dot(p, normal) <=
    offset` side, so the prism is the intersection of the half-spaces. Slicing
    first means the two halves abut exactly and no triangle straddles the
    boundary; either half is `None` where it is empty.

    🔴 **This removes and does not cap, and the caller owes the cut face.** The
    published estate is **not watertight** — measured 5.38% of edge slots open
    across the 74 source `INFRASTRUCTURE` meshes, and 14-26% in the decimated
    tiles — so a cut face cannot be derived from "edges the removal opened":
    a quarter of the edges were already open. Deriving one was tried and
    returned **zero** closed loops on `e233`. `carve.py` builds its cut face
    instead, sized from the `removed` half this returns, which is why that half
    is returned rather than discarded.

    ⚠️ **An uncapped removal is an open shell**, whose backfaces cull to
    nothing — the invisible wall `Q19` exists to remove, wearing the opposite
    sign. Nothing here can check that the caller capped it.
    """
    planes = [
        (np.asarray(normal, dtype=np.float64).reshape(3), float(offset))
        for normal, offset in planes
    ]
    if not planes:
        return mesh, None

    # 🔴 **Only triangles that straddle the boundary are sliced**, and this is
    # the difference between the stage finishing and not. A triangle wholly
    # beyond any one plane cannot meet a convex prism, and one satisfying every
    # plane is wholly inside it; neither needs cutting. Slicing everything that
    # was not wholly outside instead re-cut the whole ramp once per segment —
    # a 232 m edge is 115 of them, and one tile reached 2.5 million vertices.
    corners = mesh.positions[mesh.triangles]
    outside = np.zeros(len(mesh.triangles), dtype=bool)
    inside = np.ones(len(mesh.triangles), dtype=bool)
    for normal, offset in planes:
        beyond = corners @ normal > offset
        outside |= beyond.all(axis=1)
        inside &= ~beyond.any(axis=1)
    straddle = ~outside & ~inside
    if not (inside.any() or straddle.any()):
        return mesh, None

    keep = [select_triangles(mesh, outside)]
    take = [select_triangles(mesh, inside)]
    if straddle.any():
        cut = select_triangles(mesh, straddle)
        for normal, offset in planes:
            cut = slice_plane(cut, normal, offset)
        centroids = cut.triangle_centroids()
        within = np.ones(len(centroids), dtype=bool)
        for normal, offset in planes:
            within &= centroids @ normal <= offset
        keep.append(select_triangles(cut, ~within))
        take.append(select_triangles(cut, within))

    kept = [part for part in keep if part is not None]
    taken = [part for part in take if part is not None]
    return (
        (merge(kept, name=mesh.name) if len(kept) > 1 else kept[0]) if kept else None,
        (merge(taken, name=mesh.name) if len(taken) > 1 else taken[0]) if taken else None,
    )
