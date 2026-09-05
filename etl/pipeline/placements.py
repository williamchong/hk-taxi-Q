"""A prop layer's placements: the document that stands a library in the world.

`P5-2` made the signs a LIBRARY — one mesh per repeated shape — and a document
of stands; `P5-3` gave the lamps the same shape and moved what the two share
here; `P5-4` laid the arrows along their grade with it. A stand is
`landmarks.json`'s transform (`pos`, a compass `rot_y_deg`, and for a prop laid
along a slope a `pitch_deg`) plus an optional `scale`, and the rotation itself
is `gltf.placed_positions`' one statement. What this module owns is the entry's
shape, the rounding, the drawn totals a stage publishes so its numbers stay the
merged build's, and the document writer — each written once so a third layer
cannot drift from the first two.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.documents import write_document
from pipeline.gltf import MeshData, placed_positions, write_glb

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
    mesh: str,
    position: Sequence[float],
    rot_y_deg: float,
    scale: Sequence[float] | None = None,
    pitch_deg: float | None = None,
) -> Placement:
    """One placements entry, in `landmarks.json`'s transform shape.

    `pitch_deg` (`P5-4`) is written only when a stage passes one, so a layer
    that stands upright props — signs, lamps — writes the document it always
    did; the arrows are the one layer laid along a grade. ⚠️ **Written even
    when it is 0.0** on such a layer, because "this glyph is level" is a
    measurement and an absent key is not.
    """
    transform: dict[str, Any] = {
        "pos": [_rounded(value) for value in position],
        "rot_y_deg": _rounded(rot_y_deg),
    }
    if pitch_deg is not None:
        transform["pitch_deg"] = _rounded(pitch_deg)
    entry: Placement = {"mesh": mesh, "transform": transform}
    if scale is not None:
        entry["scale"] = [_rounded(value) for value in scale]
    return entry


def placed_at(positions: np.ndarray, entry: Placement) -> np.ndarray:
    """`positions`, in a library mesh's own frame, where `entry` stands them.

    🔴 **The one place an entry is decoded into `placed_positions`' arguments.**
    `stood_positions` and `stood` are this over a mesh; `tools/railing_error.py`
    is this over the foot samples of a panel. Written three times it was three
    places for a default — `pitch_deg` absent meaning level, `scale` absent
    meaning none — to drift, and a reader that read one differently would grade
    a city the engine does not draw.
    """
    transform = entry["transform"]
    return placed_positions(
        positions,
        transform["pos"],
        float(transform["rot_y_deg"]),
        entry.get("scale"),
        float(transform.get("pitch_deg", 0.0)),
    )


def pitch_between(rise_m: float, run_m: float) -> float:
    """The `pitch_deg` a stand carries to lie along a grade: nose-up positive.

    `atan2(rise, run)` in degrees, the same expression for a 4 m arrow between
    its two deck heights and a 2 m panel between its two ends — one statement
    so the two layers cannot disagree about which end a positive pitch raises.
    """
    return float(np.degrees(np.arctan2(rise_m, run_m)))


def stood_positions(mesh: MeshData, entry: Placement) -> np.ndarray:
    """`mesh`'s vertices where `entry` stands them, in region game space.

    The rotation is `gltf.placed_positions`' — the one statement `landmarks.json`
    and every placements document share — so what this owns is only the entry's
    shape. Each stage's tests pin it against that stage's own draw-in-place,
    which is what makes a library's `triangles`/`aabb` the merged build's
    numbers and not an estimate.
    """
    return placed_at(mesh.positions, entry)


def stood(mesh: MeshData, entry: Placement) -> MeshData:
    """`mesh` as `entry` stands it — the drawn copy, for a grader that asks a
    question of triangles rather than of vertices (`arrows.py`'s `inverted`).

    The normals turn with it: a normal is a direction, so it takes the stand's
    two rotations and neither its move nor its scale — under a non-uniform
    scale a normal transforms by the inverse of the factors, then renormalises.
    Left at the library's values (the first draft) they would have been silently
    wrong for the first caller that read them.
    """
    transform = entry["transform"]
    scale = entry.get("scale")
    normals = np.asarray(mesh.normals, dtype=np.float64)
    if scale is not None:
        normals = normals / np.asarray(scale, dtype=np.float64)
    # A direction takes the two rotations and neither the move nor the scale:
    # the same entry, decoded as `placed_at` decodes it, at the origin and with
    # its `scale` left off (the factors were applied above, inverted).
    turned = placed_at(normals, {"transform": {**transform, "pos": (0.0, 0.0, 0.0)}})
    length = np.linalg.norm(turned, axis=1, keepdims=True)
    turned = np.divide(turned, length, out=np.zeros_like(turned), where=length > 0.0)
    return replace(mesh, positions=stood_positions(mesh, entry), normals=turned.astype(np.float32))


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


@dataclass(frozen=True)
class Library:
    """A prop library built and stood — the numbers every prop stage publishes.

    `P5-2`, `P5-3` and `P5-4` each retyped the same fifteen lines between
    building their meshes and writing them: refuse the stands whose mesh
    collapsed, count the library, count what it draws under its stands, assert
    that every drawn object stands exactly once, write both files. This is that
    glue once. What stays with each stage is what differs — the grading of the
    meshes (`facing_away` on a vertical prop, `inverted` over the stood copies
    of a flat one) and what "every drawn object" adds up to.
    """

    meshes: list[MeshData]
    stands: list[Placement]
    placements_refused: int
    # What is DRAWN: the library under every stand, so a reader comparing a
    # stage's numbers to the merged build it replaced reads the same numbers.
    triangles: int
    vertices: int
    aabb: list[list[float]]

    @property
    def by_name(self) -> dict[str, MeshData]:
        return {mesh.name: mesh for mesh in self.meshes}

    def publish(self, report: Any) -> None:
        """Write the eight shared counters onto a stage's report.

        By attribute name, because the three reports spell them identically
        and a fourth that did not would fail here rather than publish zeros.
        """
        report.placements = len(self.stands)
        report.placements_refused = self.placements_refused
        report.library_meshes = len(self.meshes)
        report.library_triangles = sum(mesh.triangle_count for mesh in self.meshes)
        report.library_vertices = sum(len(mesh.positions) for mesh in self.meshes)
        report.triangles = self.triangles
        report.vertices = self.vertices
        report.aabb = self.aabb

    def require_every_stand(self, expected: int, what: str) -> None:
        """⚠️ **Computed, not claimed**: every drawn object stands exactly once.

        A stand dropped or doubled renders as a missing prop or a z-fighting
        one, and nothing in a frame says which; `expected` is what the stage
        drew, in its own terms.
        """
        if len(self.stands) + self.placements_refused != expected:
            raise ValueError(
                f"{len(self.stands)} placements and {self.placements_refused} refused for "
                f"{what} — expected {expected}, so a stand was dropped or doubled"
            )

    def write(
        self, out_dir: Path, asset: str, placements_name: str, city_id: str, region_id: str
    ) -> int:
        """The library and its document, side by side; returns the `.glb`'s bytes."""
        written = write_glb(out_dir / asset, self.meshes)
        write_placements(out_dir / placements_name, city_id, region_id, asset, self.stands)
        return written


def stand_library(
    meshes: Sequence[MeshData],
    stands: Sequence[Placement],
    *,
    counted: Callable[[str], bool] = lambda _name: True,
) -> Library:
    """`meshes` stood by `stands`, with the stands of a collapsed mesh refused.

    `counted` is `drawn_totals`'s: which meshes count toward the drawn
    triangle and vertex totals (the signs leave their lettering out).
    """
    by_name = {mesh.name: mesh for mesh in meshes}
    kept, refused = refuse_unbuilt(stands, by_name)
    triangles, vertices, aabb = drawn_totals(by_name, kept, counted=counted)
    return Library(list(meshes), kept, refused, triangles, vertices, aabb)


def expanded(
    meshes: dict[str, MeshData], stands: Sequence[Placement], name: str
) -> MeshData | None:
    """One mesh of every stood copy — what the engine draws, as a test can measure it.

    Positions, normals and `uvs` per copy from `stood`, triangles offset; `None`
    when no stand names a mesh in `meshes`. `tests/test_railings.py` measures
    panels off it. ⚠️ **It is deliberately NOT what `tools/railing_error.py`
    walks**: that walk pairs a foot with the head above it by a shared `(x, z)`,
    which a pitched stand breaks, and every panel's end edges would read as
    foot — measured, the expansion walks as 21,499 m of an 8,850 m fence. The
    grader walks the unit and stands the samples (`placed_at`).
    """
    copies = [stood(meshes[entry["mesh"]], entry) for entry in stands if entry["mesh"] in meshes]
    if not copies:
        return None
    offsets = np.cumsum([0] + [len(copy.positions) for copy in copies[:-1]])
    first = copies[0]
    return MeshData(
        name=name,
        positions=np.vstack([copy.positions for copy in copies]),
        normals=np.vstack([copy.normals for copy in copies]).astype(np.float32),
        triangles=np.vstack(
            [copy.triangles + offset for copy, offset in zip(copies, offsets, strict=True)]
        ).astype(np.uint32),
        uvs=None if first.uvs is None else np.vstack([copy.uvs for copy in copies]),
        material=first.material,
    )


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
