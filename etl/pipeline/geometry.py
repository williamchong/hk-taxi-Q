"""Plan-polygon predicates shared across stages (`P3-7a`).

Hand-rolled on numpy rather than pulled in: the only candidate dependency is
shapely, and `pyproject.toml` already turned down geopandas for wanting pandas
to reach the numpy underneath — the same trade in miniature, made once in
`surface.py` and inherited here when the tower↔block join (`Q47`) needed the
same tests against the iB1000 rings.

Everything works on plan coordinates, shape `(n, 2)`, in whatever frame the
caller is consistent about. Rings follow `gdb.polygons`' convention: a polygon
is a list of `(n, 2)` rings, outer first, interior rings after.
"""

from __future__ import annotations

import numpy as np


def inside_polygon(points: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """Which plan points fall inside a plan polygon. Crossing number.

    Vectorised over the polygon's edges as well as its points, because this was
    the single most expensive thing the surface stage does — a Python loop here
    cost 2.2 s of a 2.5 s build.
    """
    x, z = points[:, 0][:, None], points[:, 1][:, None]
    ax, az = polygon[:, 0], polygon[:, 1]
    bx, bz = np.roll(ax, -1), np.roll(az, -1)
    rise = bz - az
    straddles = (az > z) != (bz > z)
    # `x < ax + (bx - ax) * (z - az) / rise`, cross-multiplied. A horizontal edge
    # never straddles the ray, so `rise` is non-zero wherever the result is read
    # and the sign of it is all the division was contributing. Multiplying also
    # spares the region 476,000 `np.errstate` context managers, which were 15% of
    # the stage on their own, guarding a quotient that was masked away anyway.
    side = (x - ax) * rise - (bx - ax) * (z - az)
    crossings = straddles & np.where(rise > 0.0, side < 0.0, side > 0.0)
    return crossings.sum(axis=1) % 2 == 1


def inside_rings(points: np.ndarray, rings: list[np.ndarray]) -> np.ndarray:
    """Which plan points fall inside a polygon given as rings, holes excluded.

    `gdb.polygons` hands interior rings back and `inside_polygon` cannot know
    about them — a tower standing in a podium's courtyard is *outside* the
    podium, and testing only the outer ring would join the two anyway.
    """
    inside = inside_polygon(points, rings[0])
    for hole in rings[1:]:
        inside &= ~inside_polygon(points, hole)
    return inside


def orient(p: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Twice the signed area of `pqr` — the broadcast 2-D cross product.

    Written out because numpy 2.0 dropped 2-vector support from `np.cross`.
    """
    return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (
        r[..., 0] - p[..., 0]
    )


def edges_cross(a: np.ndarray, b: np.ndarray) -> bool:
    """Whether any edge of ring `a` properly crosses any edge of ring `b`.

    Proper crossings only — collinear overlap and shared endpoints do not
    count, which is what keeps two polygons abutting along a sheet cut from
    reading as overlapping. Touch semantics belong to `rings_overlap`'s
    `touch_m`, where the tolerance is explicit instead of an accident of
    floating-point collinearity.
    """
    a1, a2 = a[:, None, :], np.roll(a, -1, axis=0)[:, None, :]
    b1, b2 = b[None, :, :], np.roll(b, -1, axis=0)[None, :, :]
    d1, d2 = orient(a1, a2, b1), orient(a1, a2, b2)
    d3, d4 = orient(b1, b2, a1), orient(b1, b2, a2)
    return bool(((d1 * d2 < 0.0) & (d3 * d4 < 0.0)).any())


def gap_between(points: np.ndarray, ring: np.ndarray) -> float:
    """Smallest distance from any of the points to any edge of the ring."""
    a = ring
    b = np.roll(ring, -1, axis=0)
    ab = b - a
    length_sq = (ab**2).sum(axis=1)
    # A degenerate zero-length edge contributes its endpoint: `t` clamps to 0.
    length_sq[length_sq == 0.0] = 1.0
    ap = points[:, None, :] - a[None, :, :]
    t = np.clip((ap * ab[None, :, :]).sum(axis=2) / length_sq[None, :], 0.0, 1.0)
    nearest = a[None, :, :] + t[:, :, None] * ab[None, :, :]
    return float(np.sqrt(((points[:, None, :] - nearest) ** 2).sum(axis=2)).min())


def rings_overlap(a: list[np.ndarray], b: list[np.ndarray], *, touch_m: float) -> bool:
    """Whether two polygons share interior, or come strictly closer than `touch_m`.

    Three tests, cheapest first: a vertex of one inside the other (holes
    respected), a proper edge crossing between the outer rings, and finally the
    ε-touch — a tower drawn flush against its podium block shares an edge with
    it, which proper crossing does not see. What is promised: interior overlap
    is True, a gap of `touch_m` or more is False. Exact boundary contact at
    `touch_m = 0.0` is *unspecified* — a vertex lying on the other ring
    classifies arbitrarily under the crossing number's strict inequalities —
    so callers that care about contact pass a positive tolerance, as the join
    does. The one blind spot left open is a crossing region that falls
    entirely inside an interior ring, which no source polygon this serves has
    produced.
    """
    if inside_rings(a[0], b).any() or inside_rings(b[0], a).any():
        return True
    if edges_cross(a[0], b[0]):
        return True
    return gap_between(a[0], b[0]) < touch_m or gap_between(b[0], a[0]) < touch_m


def points_in_triangles(points: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Which plan points fall inside any of the plan triangles.

    `corners` is `(m, 3, 2)`. Sign tests against all three edges, either
    winding accepted — mesh triangles arrive projected from 3-D, where plan
    winding is an artefact of which way the face happened to lean. Degenerate
    slivers have a zero cross product somewhere and accept only their own
    boundary, which the strict inequalities then reject.
    """
    p = points[:, None, :]
    a, b, c = corners[None, :, 0, :], corners[None, :, 1, :], corners[None, :, 2, :]
    d1, d2, d3 = orient(a, b, p), orient(b, c, p), orient(c, a, p)
    inside = ((d1 > 0.0) & (d2 > 0.0) & (d3 > 0.0)) | ((d1 < 0.0) & (d2 < 0.0) & (d3 < 0.0))
    return inside.any(axis=1)
