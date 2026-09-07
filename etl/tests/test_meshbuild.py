"""`FlatBuilder`'s fan, and the precondition it states but does not test.

The builder is shared by `arrows.py`, `roadmarks.py` and `boxjunctions.py`, and
it triangulates every polygon as a fan from vertex 0. That is a valid
triangulation only while the polygon is convex, and nothing in the class checks
it — so the statement lives here, pinned, rather than in a docstring alone
(`Q123`).

⚠️ **These tests assert the defect, not a repair.** A fan that quietly fixed
itself would make each stage's `inverted` counter read 0 by construction, which
is the one thing that must not happen to it (`Q58`, `Q72`): that counter is what
caught `sha_tin`'s folded border quad, and each producer owns refusing its own
reflex polygons — `boxjunctions.border_polygons` does, counted.

⚠️ **Wound clockwise in plan, because that is what faces `+Y`.** The `y`
component of the cross product is the negation of the `(x, z)` signed area, so
a counter-clockwise fixture here would test the builder upside down.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from pipeline.boxjunctions import _turns_one_way
from pipeline.gltf import MeshData
from pipeline.meshbuild import FlatBuilder
from pipeline.surface import downward_facing

MATERIAL = "res://tuning/boxjunctions.tres"


def built(polygon: np.ndarray) -> MeshData:
    """The one-polygon mesh, at a uniform height so only the winding decides."""
    builder = FlatBuilder(MATERIAL)
    builder.polygon(polygon, np.zeros(len(polygon)))
    mesh = builder.build("fan")
    assert mesh is not None
    return mesh


class TestTheFanPrecondition:
    def test_a_convex_quad_fans_face_up(self) -> None:
        """The contract as all three callers rely on it."""
        convex = np.array([[0.0, 0.0], [1.28, 0.0], [1.28, -0.3], [0.0, -0.3]])

        mesh = built(convex)

        assert mesh.triangle_count == 2
        assert downward_facing(mesh) == (0, 0.0)

    def test_a_reflex_corner_at_v3_folds_one_triangle_under_the_mesh(self) -> None:
        """`sha_tin`'s border quad, in its own frame (`Q123`).

        The fold is `(0, 2, 3)` — the `0`-`2` diagonal has left the polygon —
        and it reproduces the 0.0327 m² that bundle published as
        `inverted_area_m2` — to the four decimals its vertices were read back
        at, which is the tolerance below. Under `cull_back` it draws as
        nothing, so no frame shows it and only the stage's counter can.
        """
        shipped = np.array([[0.0, 0.0], [1.2776, 0.0], [1.2895, -0.3], [0.4063, -0.0437]])

        inverted, area = downward_facing(built(shipped))

        assert inverted == 1
        assert area == pytest.approx(0.0327, abs=1e-4)

    def test_a_reflex_corner_at_v2_still_fans_correctly(self) -> None:
        """Why `border_polygons` bars non-convexity and not *a reflex corner*.

        The fan survives a reflex vertex at `v0` or `v2`, because the diagonal
        it uses stays inside. So the condition that actually breaks a quad is
        narrower than the one worth guarding, and a guard written to the narrow
        condition would depend on which vertex the mitre turned back at.
        """
        reflex_at_v2 = np.array([[0.0, 0.0], [1.28, 0.0], [0.7, -0.1], [0.0, -0.3]])

        assert downward_facing(built(reflex_at_v2)) == (0, 0.0)

    def test_a_star_polygon_turns_one_way_and_folds_anyway(self) -> None:
        """The limit of `boxjunctions._turns_one_way`, pinned so it is not
        reused past it (`Q123`).

        Same-sign turns is convexity only for a *simple* polygon. A pentagram
        turns one way at every vertex, passes that guard, and still fans a
        triangle under the mesh — so the guard is a quad rule, not a general
        fan precondition. It is sound where it is called because a quad cannot
        do this: no self-intersecting quad passes it.
        """
        pentagram = np.array(
            [
                [math.sin(4.0 * math.pi * k / 5.0), math.cos(4.0 * math.pi * k / 5.0)]
                for k in range(5)
            ]
        )

        assert _turns_one_way(pentagram)
        assert downward_facing(built(pentagram))[0] > 0
