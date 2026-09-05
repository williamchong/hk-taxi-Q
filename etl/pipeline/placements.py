"""A prop layer's placements: the document that stands a library in the world.

`P5-2` made the signs a LIBRARY — one mesh per repeated shape — and a document
of stands; `P5-3` gave the lamps the same shape and moved what the two share
here. A stand is `landmarks.json`'s transform (`pos`, a compass `rot_y_deg`)
plus an optional `scale`, and the rotation itself is `gltf.placed_positions`'
one statement. What this module owns is the entry's shape, the rounding, the
drawn totals a stage publishes so its numbers stay the merged build's, and the
document writer — each written once so a third layer cannot drift from the
first two.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.documents import write_document
from pipeline.gltf import MeshData

# Every `*_placements.json` shares one schema, because the format is one
# format. Mirrors `GeneratedPlacements.SCHEMA_VERSION` in the engine.
PLACEMENTS_SCHEMA = 1

# Decimals a placement keeps. Float32 spacing at region scale (~10³ m) is
# ~1e-4 m, which is what a `.glb` stores and the engine's `Transform3D` holds,
# so 4 dp is that resolution: 3 would be coarser than the merged build, 5 would
# be bytes the consumer cannot represent. The tests derive their tolerance from
# this number rather than restating it.
PLACEMENT_DP = 4


def _rounded(value: float) -> float:
    # `+ 0.0` collapses `-0.0`, on `documents.round_position`'s argument: a prop
    # at the region's western edge can land on it, and "-0.0" is a diff.
    return round(float(value), PLACEMENT_DP) + 0.0


# One entry of a placements document — `placement` below is the one writer.
Placement = dict[str, Any]


def placement(
    mesh: str, position: Sequence[float], rot_y_deg: float, scale: Sequence[float] | None = None
) -> Placement:
    """One placements entry, in `landmarks.json`'s transform shape."""
    entry: Placement = {
        "mesh": mesh,
        "transform": {
            "pos": [_rounded(value) for value in position],
            "rot_y_deg": _rounded(rot_y_deg),
        },
    }
    if scale is not None:
        entry["scale"] = [_rounded(value) for value in scale]
    return entry


def stood_positions(mesh: MeshData, entry: Placement) -> np.ndarray:
    """`mesh`'s vertices where `entry` stands them, in region game space.

    The rotation is `gltf.placed_positions`' — the one statement `landmarks.json`
    and every placements document share — so what this owns is only the entry's
    shape. Each stage's tests pin it against that stage's own draw-in-place,
    which is what makes a library's `triangles`/`aabb` the merged build's
    numbers and not an estimate.
    """
    transform = entry["transform"]
    return mesh.placed(transform["pos"], float(transform["rot_y_deg"]), entry.get("scale"))


def refuse_unbuilt(
    stands: Sequence[Placement], by_name: dict[str, MeshData]
) -> tuple[list[Placement], int]:
    """`stands` whose mesh was built, and how many were not.

    A stand whose mesh collapsed entirely (every triangle a sliver) would be a
    placement of nothing; refused rather than shipped, and counted so the
    stage's partition still closes — 0 on both layers today.
    """
    kept = [entry for entry in stands if entry["mesh"] in by_name]
    return kept, len(stands) - len(kept)


def drawn_totals(
    by_name: dict[str, MeshData],
    stands: Sequence[Placement],
    *,
    counted: Callable[[str], bool] = lambda _name: True,
) -> tuple[int, int, list[list[float]]]:
    """What is DRAWN: triangles, vertices and extent of the library under `stands`.

    Published so a reader comparing a stage's numbers to the merged build it
    replaced reads the same numbers. `counted` narrows the triangle and vertex
    sums — the signs exclude their lettering, which has its own count — while
    the extent takes every stand.
    """
    if not stands:
        return 0, 0, []
    triangles = 0
    vertices = 0
    low = np.full(3, np.inf)
    high = np.full(3, -np.inf)
    for entry in stands:
        mesh = by_name[entry["mesh"]]
        if counted(mesh.name):
            triangles += mesh.triangle_count
            vertices += len(mesh.positions)
        placed = stood_positions(mesh, entry)
        low = np.minimum(low, placed.min(axis=0))
        high = np.maximum(high, placed.max(axis=0))
    return triangles, vertices, [[float(v) for v in low], [float(v) for v in high]]


def write_placements(
    path: Path, city_id: str, region_id: str, library: str, stands: Sequence[Placement]
) -> int:
    """The document, beside the library it stands."""
    return write_document(
        path,
        {
            "schema_version": PLACEMENTS_SCHEMA,
            "city_id": city_id,
            "region_id": region_id,
            "library": library,
            "placements": list(stands),
        },
    )
