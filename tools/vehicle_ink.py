"""Where a vehicle's detail lines go, as mesh data the body shader inks.

The city's outline (`cel_outline.gdshader`) is a pass over the depth buffer, so
it draws a vehicle's silhouette and folds and nothing else: a window, a livery
band or a lens is a change of colour on one flat panel, and depth cannot see
it. Which edges those are is known here, where the body is built, and nowhere
later — so this stamps them into `uv2` and `vehicle_body.gdshader` draws
the line.

An edge is inked when the surface on its far side is not more of the same: no
other triangle of the same colour and marker touches it. A fold between two
faces of one colour is left to the depth pass, which already draws it.

`uv2` (`TEXCOORD_1`) holds, per channel, `1 - d / INK_SPAN_M`, where `d` is the vertex's
distance in metres from one inked edge of its triangle. A channel with no edge
is 0 at all three corners — the far end of the span, so no line — and a body
with no `TEXCOORD_1` at all (a DCC export) reads the same 0 and draws none.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from pipeline.gltf import MeshData, normalise
from pipeline.mesh import weld

# Longer than any vehicle, so `1 - d / span` stays inside (0, 1] and the
# engine's 16-bit UV packing holds it to a quarter of a millimetre.
# Must match `INK_SPAN_M` in `vehicle_body.gdshader`.
INK_SPAN_M = 16.0
# How near a triangle must come to an edge's sample point to count as the
# surface carrying on past it. A seated fixture sits millimetres proud.
_TOUCH_M = 0.0015
# Where along an edge the far side is sampled; two of three decide.
_SAMPLES = (0.25, 0.5, 0.75)
_CHUNK = 256


def _covered(
    points: np.ndarray, corners: np.ndarray, normals: np.ndarray, skip: np.ndarray
) -> np.ndarray:
    """Whether each point lies on some triangle of `corners` other than its own."""
    hit = np.zeros(len(points), dtype=bool)
    a, b, c = corners[:, 0], corners[:, 1], corners[:, 2]
    sides = []
    for start, end in ((a, b), (b, c), (c, a)):
        sides.append((start, normalise(np.cross(normals, end - start))))
    owners = np.arange(len(corners))
    for begin in range(0, len(points), _CHUNK):
        p = points[begin : begin + _CHUNK, None, :]
        inside = np.abs(np.einsum("ptk,tk->pt", p - a[None], normals)) < _TOUCH_M
        for start, inward in sides:
            inside &= np.einsum("ptk,tk->pt", p - start[None], inward) > -_TOUCH_M
        inside &= owners[None, :] != skip[begin : begin + _CHUNK, None]
        hit[begin : begin + _CHUNK] = inside.any(axis=1)
    return hit


def _borders(corners: np.ndarray, identity: np.ndarray) -> np.ndarray:
    """(triangles, 3) bool: edge `i` runs from corner `i` to corner `i + 1`."""
    cross = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    # A sliver neither takes a line nor counts as the surface carrying on.
    sound = np.linalg.norm(cross, axis=1) > 1e-10
    normals = normalise(cross)
    borders = np.zeros((len(corners), 3), dtype=bool)
    for key in np.unique(identity, axis=0):
        members = np.flatnonzero(np.all(identity == key, axis=1) & sound)
        if len(members) == 0:
            continue
        mine = corners[members]
        local = np.arange(len(members))
        for edge in range(3):
            start, end = mine[:, edge], mine[:, (edge + 1) % 3]
            open_samples = np.zeros(len(members), dtype=int)
            for t in _SAMPLES:
                points = start + (end - start) * t
                open_samples += ~_covered(points, mine, normals[members], local)
            borders[members, edge] = open_samples >= 2
    return borders


def _ink(points: np.ndarray, start: np.ndarray, end: np.ndarray) -> np.ndarray:
    """One channel's value at `points`, off their distance from the edge's line."""
    along = (end - start) / max(float(np.linalg.norm(end - start)), 1e-12)
    off = points - start
    distance = np.linalg.norm(off - np.outer(off @ along, along), axis=1)
    return 1.0 - distance / INK_SPAN_M


def inked(body: MeshData) -> MeshData:
    """`body` with its inked edges in `uv2`, sharing whatever vertices still agree.

    A triangle with three inked edges is split at its incentre into three, each
    the part nearest one edge, because two channels carry two edges. The new
    corner takes the triangle's first corner's normal, colour and payload: the
    bodies are flat-shaded, so all three agree.
    """
    if body.colours is None or body.uvs is None:
        raise ValueError(f"'{body.name}': ink needs the colours and the marker payload")
    triangles = np.asarray(body.triangles).reshape(-1, 3)
    corners = body.positions[triangles]
    first = triangles[:, 0]
    identity = np.concatenate(
        [body.colours[first, :3].astype(np.float64), body.uvs[first].astype(np.float64)],
        axis=1,
    )

    positions: list[np.ndarray] = []
    source: list[np.ndarray] = []
    ink: list[np.ndarray] = []
    for triangle, tri, flags in zip(triangles, corners, _borders(corners, identity), strict=True):
        if flags.all():
            lengths = np.linalg.norm(np.roll(tri, -1, axis=0) - np.roll(tri, -2, axis=0), axis=1)
            centre = lengths @ tri / lengths.sum()
            for e in range(3):
                end = (e + 1) % 3
                piece = np.stack([tri[e], tri[end], centre])
                positions.append(piece)
                source.append(np.array([triangle[e], triangle[end], triangle[0]]))
                ink.append(np.column_stack([_ink(piece, tri[e], tri[end]), np.zeros(3)]))
            continue
        channels = np.zeros((3, 2))
        for slot, e in enumerate(np.flatnonzero(flags)):
            channels[:, slot] = _ink(tri, tri[e], tri[(e + 1) % 3])
        positions.append(tri)
        source.append(triangle)
        ink.append(channels)

    lookup = np.concatenate(source)
    return weld(
        replace(
            body,
            positions=np.concatenate(positions),
            normals=body.normals[lookup],
            triangles=np.arange(len(lookup), dtype=np.uint32).reshape(-1, 3),
            colours=body.colours[lookup],
            uvs=body.uvs[lookup],
            uv2=np.concatenate(ink).astype(np.float32),
        )
    )
