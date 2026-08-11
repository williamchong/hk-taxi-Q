"""Flat-shaded mesh primitives shared by the `tools/` generators.

Promoted out of `make_vehicle.py` when `P3-6` added a second generator
(`make_landmark.py`). The alternative was importing another tool's
underscore-privates — coupling two generators through a non-contract — or
copying six geometry functions that would then drift. The byte-comparison
test in `etl/tests/test_make_vehicle.py` is the proof the promotion changed
no output.

Everything here builds `MeshData` with unshared vertices: every face carries
its own normal, so an edge stays an edge and a vertex colour stays crisp
across it — flat shading without smoothing groups, which is the city's art
direction (`docs/ART_DESIGN.md`).
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etl"))

from pipeline.gltf import MeshData, normalise
from pipeline.mesh import merge

Colour = tuple[int, int, int]
Point = Sequence[float]


def polygon(corners: Sequence[Point], colour: Colour, *, name: str) -> MeshData:
    """One flat convex face, wound counter-clockwise seen from outside.

    Vertices are never shared between faces. That is what makes the whole model
    flat-shaded without smoothing groups: every triangle carries its own face
    normal, so an edge stays an edge and a vertex colour stays crisp across it.

    Triangles and quads go through the same call because a wheel needs both, and
    the earlier version faked the triangles as quads with two coincident
    corners. That is not a harmless trick: the face normal comes from
    `corners[1] - corners[0]` crossed with `corners[-1] - corners[0]`, and
    duplicating `corners[0]` makes the second of those zero — so every cap on
    the first wheel got a zero normal and a degenerate triangle to go with it.
    """
    positions = np.asarray(corners, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[0] < 3 or positions.shape[1] != 3:
        raise ValueError(f"'{name}': need at least three xyz corners, got {positions.shape}")

    face = normalise(np.cross(positions[1] - positions[0], positions[-1] - positions[0])[None, :])
    if not np.isfinite(face).all() or np.allclose(face, 0.0):
        raise ValueError(f"'{name}': corners are collinear or coincident, so it has no normal")

    fan = [(0, i, i + 1) for i in range(1, len(positions) - 1)]
    return MeshData(
        name=name,
        positions=positions,
        normals=np.repeat(face, len(positions), axis=0).astype(np.float32),
        triangles=np.array(fan, dtype=np.uint32),
        colours=np.repeat(np.array([[*colour, 255]], dtype=np.uint8), len(positions), axis=0),
    )


def polygon_facing(
    corners: Sequence[Point], colour: Colour, outward: Sequence[float], *, name: str
) -> MeshData:
    """A face wound so its normal points along `outward`.

    Curved runs — the arch band and its rim — are generated from angles rather
    than written out corner by corner, and which way round that comes out flips
    with the side of the car and with the direction of travel around the arc.
    Stating the direction the face should look and letting the code reverse
    itself is the difference between one rule and four hand-checked cases; the
    wheel proved the alternative by rendering itself inside-out.
    """
    ring_ = list(corners)
    normal = np.cross(
        np.subtract(ring_[1], ring_[0], dtype=np.float64),
        np.subtract(ring_[-1], ring_[0], dtype=np.float64),
    )
    if float(np.dot(normal, np.asarray(outward, dtype=np.float64))) < 0.0:
        ring_.reverse()
    return polygon(ring_, colour, name=name)


def hexahedron(
    bottom: Sequence[Point],
    top: Sequence[Point],
    colour: Colour,
    *,
    name: str,
) -> MeshData:
    """Six quads over eight corners, so a taper costs no more than a box.

    Corners run anticlockwise seen from above: (-x,-z), (+x,-z), (+x,+z),
    (-x,+z). Taking bottom and top as separate rings is what lets a fixture
    narrow towards its top without becoming two parts.

    One colour for the whole solid. It used to take a colour per named face,
    which is what painted the old boxed body — a dark glasshouse under a silver
    roof. `loft` does that job now, band by band, and every caller left here is
    a lamp or a bumper that wants one flat colour.
    """
    b0, b1, b2, b3 = bottom
    t0, t1, t2, t3 = top
    quads = [
        polygon(corners, colour, name=f"{name}_{i}")
        for i, corners in enumerate(
            (
                (b0, b1, b2, b3),
                (t0, t3, t2, t1),
                (b1, b0, t0, t1),
                (b3, b2, t2, t3),
                (b0, b3, t3, t0),
                (b2, b1, t1, t2),
            )
        )
    ]
    return merge(quads, name=name)


def ring(
    y: float, half_w: float, z_front: float, z_back: float, cut: float = 0.0
) -> tuple[Point, ...]:
    """One horizontal section, in order around the body.

    With `cut` the four square corners become eight, turning each vertical edge
    into three short facets instead of one 90° turn. That is what "rounded"
    means here: the faces stay flat and every edge stays crisp, so the car still
    belongs in a flat-shaded city — there are simply more of them. Smooth
    shading would be the thing that broke the art direction; a chamfer is not.
    """
    if cut <= 0.0:
        return (
            (-half_w, y, z_front),
            (half_w, y, z_front),
            (half_w, y, z_back),
            (-half_w, y, z_back),
        )
    cut = min(cut, half_w * 0.9, abs(z_back - z_front) * 0.45)
    return (
        (-half_w + cut, y, z_front),
        (half_w - cut, y, z_front),
        (half_w, y, z_front + cut),
        (half_w, y, z_back - cut),
        (half_w - cut, y, z_back),
        (-half_w + cut, y, z_back),
        (-half_w, y, z_back - cut),
        (-half_w, y, z_front + cut),
    )


def flank_edges(corners: int) -> tuple[int, int]:
    """Which two edges of a ring are the long flanks.

    Derived rather than pinned. They were hardcoded as `(2, 6)`, correct only
    for the eight-corner ring — and `corner_cut_m = 0` is an offered setting
    that returns four corners, where edge 2 is the *boot face*. Skipping it left
    a hole through the back of the car and drew both flanks twice, silently, for
    fifty fewer triangles and no error.
    """
    return (corners // 4, 3 * corners // 4)


def loft(
    rings: Sequence[Sequence[Point]],
    band_colours: Sequence[Colour],
    *,
    bottom: Colour,
    top: Colour,
    skip_edges: Sequence[int] = (),
    axis: int = 1,
    name: str,
) -> MeshData:
    """A profile lofted through stacked rings — the shape a car body is.

    Bevels at this scale are not rounded edges, they are *one more ring* a few
    centimetres in and up. Stacking three or four rings gives a chamfered sill,
    a tucked roof and a raked pillar for four quads apiece, and it keeps every
    face flat — which is the whole point, since the city it drives through is
    flat-shaded and a smooth-shaded car would sit outside its own art direction.

    `axis` is which way the rings are stacked, and it is a parameter because the
    4 SEATS badge is the same operation lying on its side — a profile extruded
    along Z rather than Y. That was written out by hand first, centroid, outward
    masking and both caps, and it produced the *identical* solid: same 28
    triangles, same vertices, same area. Two copies of this loop is one more
    place for the outward-facing rule to be got wrong.
    """
    if len(rings) < 2:
        raise ValueError(f"'{name}': a loft needs at least two rings")
    if len(band_colours) != len(rings) - 1:
        raise ValueError(
            f"'{name}': {len(rings)} rings need {len(rings) - 1} band colours, "
            f"got {len(band_colours)}"
        )

    corners = len(rings[0])
    if any(len(ring_) != corners for ring_ in rings):
        raise ValueError(f"'{name}': every ring needs the same number of corners")
    out_of_range = [edge for edge in skip_edges if not 0 <= edge < corners]
    if out_of_range:
        raise ValueError(f"'{name}': no edge {out_of_range} on a {corners}-corner ring")

    parts: list[MeshData] = []
    # Flattened along the stacking axis, both here and on every band below. A
    # side face looks *outward from the profile*, and leaving the axis component
    # in tilts that vector by however much the rings taper — which is enough to
    # flip a face on a steeply raked band.
    centre = np.mean(np.asarray(rings[0], dtype=np.float64), axis=0)
    centre[axis] = 0.0
    for i, colour in enumerate(band_colours):
        lower, upper = rings[i], rings[i + 1]
        for edge in range(corners):
            if edge in skip_edges:
                continue
            nxt = (edge + 1) % corners
            outward = np.mean([lower[edge], lower[nxt], upper[edge], upper[nxt]], axis=0) - centre
            outward[axis] = 0.0
            parts.append(
                polygon_facing(
                    [lower[nxt], lower[edge], upper[edge], upper[nxt]],
                    colour,
                    outward,
                    name=f"{name}_edge{edge}_{i}",
                )
            )

    end = np.zeros(3)
    end[axis] = 1.0
    parts.append(polygon_facing(rings[0], bottom, -end, name=f"{name}_bottom"))
    parts.append(polygon_facing(rings[-1], top, end, name=f"{name}_top"))
    return merge(parts, name=name)


def box(low: Point, high: Point, colour: Colour, *, name: str) -> MeshData:
    """An axis-aligned box — the untapered case of `hexahedron`."""
    (lx, ly, lz), (hx, hy, hz) = low, high

    def ring_(y: float) -> tuple[Point, ...]:
        return ((lx, y, lz), (hx, y, lz), (hx, y, hz), (lx, y, hz))

    return hexahedron(ring_(ly), ring_(hy), colour, name=name)


def box_at(centre: Point, half: Point, colour: Colour, *, name: str) -> MeshData:
    """A box from its centre and half-extents.

    Fixtures that come in mirrored pairs — lamps, mirrors, arches — are placed
    by centre, because writing them as opposing corners means every one of them
    needs its own `min`/`max` reasoning and the left of the pair reads
    differently from the right.
    """
    low = tuple(c - h for c, h in zip(centre, half, strict=True))
    high = tuple(c + h for c, h in zip(centre, half, strict=True))
    return box(low, high, colour, name=name)
