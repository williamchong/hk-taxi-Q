"""`P3-28` carve tests.

Two layers, mirroring the module. The prism and the retaining wall are pure
geometry, tested on hand-built meshes where every triangle's fate is checkable by
eye. The stage itself is tested for the two things no frame can show: that an
absent config block leaves the bundle alone, and that a configured edge the graph
does not carry stops the build rather than being skipped.

🔴 **The wall tests are the ones that matter.** Every other way this stage breaks
renders as a plausible frame — a wall at the wrong height still looks like a
wall — and the estate is not watertight, so nothing can check the cut closed.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from pipeline.buildings import (
    BUILDINGS_MANIFEST_NAME,
    BUILDINGS_MANIFEST_SCHEMA,
    CARVED_EDGES_KEY,
    facade_uv,
)
from pipeline.carve import (
    EdgeCarve,
    EdgePlan,
    _facing_away,
    _prisms,
    _retaining_wall,
    _stations,
    _structure,
    build_region,
)
from pipeline.documents import write_document
from pipeline.gltf import MeshData
from pipeline.mesh import subtract_prism
from pipeline.surface import mitres
from tests.helpers import box, line, style


def _plan(points: np.ndarray, *, half_m: float = 3.0) -> EdgePlan:
    """An `EdgePlan` over a hand-built ribbon, floors at zero, no soffit."""
    offsets = mitres(points)
    floors = np.zeros(len(points))
    ceilings = np.full(len(points), np.inf)
    return EdgePlan(
        row=EdgeCarve(0, "test", half_m * 2, "measured", len(points), 0, 0, 0.0, 0.0, 0.0),
        points=points,
        offsets=offsets,
        half_m=half_m,
        floors=floors,
        prisms=_prisms(points, offsets, half_m, floors, ceilings),
    )


def _uv(mesh: MeshData, class_id: str) -> MeshData:
    """The same mesh, tagged through the **real** encoder.

    ⚠️ Not a hand-rolled copy of `facade_uv`'s pack format. A test that encodes
    and decodes with its own copy of the convention stays self-consistent while
    the shipped encoder moves — which is the one failure `_structure` exists to
    catch.
    """
    return replace(mesh, uvs=facade_uv(style(), class_id, mesh))


class TestStations:
    def test_the_walk_never_strides_past_the_spacing(self) -> None:
        """Measured on the walked geometry rather than on the parameterisation
        that produced it — a prism rebuilt per station is only as close to the
        ramp's curve as the longest step between two of them."""
        points = _stations(line((0, 0, 0), (10, 0, 0), (10, 0, 7)), 2.0)
        steps = np.linalg.norm(np.diff(points[:, [0, 2]], axis=0), axis=1)

        assert steps.max() <= 2.0 + 1e-9
        assert points[0] == pytest.approx([0, 0, 0])
        assert points[-1] == pytest.approx([10, 0, 7])

    def test_height_is_carried_along_the_walk(self) -> None:
        """The ribbon's own y is the datum the cut floor and the headroom are
        measured from, so a walk that flattened it would cut at the wrong level
        on every ramp — and a ramp is what this stage exists for."""
        points = _stations(line((0, 4.0, 0), (10, 6.0, 0)), 5.0)

        assert points[:, 1].min() == pytest.approx(4.0)
        assert points[:, 1].max() == pytest.approx(6.0)


class TestPrisms:
    def test_consecutive_prisms_share_their_end_plane(self) -> None:
        """What makes the union of the segment prisms the ribbon itself. A prism
        squared off to its own segment leaves a wedge uncut on the outside of
        every bend, and a ramp is nothing but bends."""
        points = line((0, 0, 0), (10, 0, 0), (18, 0, 6))
        offsets = mitres(points)
        built = _prisms(points, offsets, 3.0, np.zeros(3), np.full(3, 10.0))

        ahead_of_first = built[0][1]
        behind_second = built[1][0]
        assert ahead_of_first[0] == pytest.approx(-behind_second[0])
        assert ahead_of_first[1] == pytest.approx(-behind_second[1])

    def test_the_prism_is_the_surveyed_width_and_not_the_floor(self) -> None:
        """🔴 `Q54` inverted is the one thing `Q19` forbids here: cutting at the
        10.24 m widening floor removes published structure on an invented
        width's authority. A 3.84 m edge must cut 3.84 m."""
        points = line((0, 0, 0), (20, 0, 0))
        built = _prisms(points, mitres(points), 3.84 / 2.0, np.zeros(2), np.full(2, 9.0))

        left, right = built[0][2], built[0][3]
        width = left[1] + right[1]
        assert width == pytest.approx(3.84)


class TestSubtraction:
    def test_a_wall_across_the_carriageway_is_cut_and_its_flanks_are_kept(self) -> None:
        wall = box(origin=(8.0, 0.0, -6.0), size=12.0)
        points = line((0, 2.0, 0), (30, 2.0, 0))
        built = _prisms(points, mitres(points), 3.0, np.zeros(2), np.full(2, 9.0))

        kept, removed = subtract_prism(wall, built[0])
        assert removed is not None and kept is not None
        assert removed.positions[:, 2].min() >= -3.0 - 1e-6
        assert removed.positions[:, 2].max() <= 3.0 + 1e-6
        assert kept.positions[:, 2].max() > 3.0


class TestRetainingWall:
    """🔴 The cut face is constructed, so its height is the thing to pin."""

    @staticmethod
    def _cut(top: float) -> tuple[MeshData, EdgePlan]:
        """Structure `top` metres tall sitting across a 6 m straight ribbon."""
        cut = box(origin=(0.0, 0.0, -3.0), size=6.0)
        cut = replace(cut, positions=cut.positions * np.array([1.0, top / 6.0, 1.0]))
        return cut, _plan(line((0, 0.5, 0), (6, 0.5, 0)), half_m=3.0)

    def test_the_wall_takes_its_height_from_what_was_removed(self) -> None:
        """⚠️ Not from the prism. A wall drawn to the cut ceiling would stand at
        the cut height wherever the structure was shorter — a slab of concrete
        over the carriageway with nothing behind it, and every counter closing.
        `Q72`'s tautology: a number the construction guarantees says nothing."""
        low, low_plan = self._cut(3.0)
        high, high_plan = self._cut(9.0)

        short, _ = _retaining_wall(low, low_plan, low)
        tall, _ = _retaining_wall(high, high_plan, high)

        assert short is not None and tall is not None
        assert short.positions[:, 1].max() == pytest.approx(3.0)
        assert tall.positions[:, 1].max() == pytest.approx(9.0)

    def test_the_wall_wears_the_class_of_what_it_replaces(self) -> None:
        """🔴 A tile is one merged primitive whose first vertex is usually a
        building, so taking the wall's channels from the tile tags a concrete
        retaining wall `FACADE` — and the window-band shader draws storeys of
        glazing on it. It also moves the wall between the two share gates
        `carriageway_occupancy.py` reads: measured BUILDING 1.204 → 1.292% with
        the wall mislabelled, which is a defect that renders as a plausible
        frame and shows up only as a number moving in the wrong table."""
        cut, plan = self._cut(4.0)
        removed = _uv(cut, "INFRASTRUCTURE")
        tile_first_vertex_is_a_building = _uv(box(), "BUILDING")

        wall, _ = _retaining_wall(removed, plan, tile_first_vertex_is_a_building)

        assert wall is not None
        assert _structure(wall).all()

    def test_nothing_removed_draws_no_wall(self) -> None:
        """The wall exists along the run the carve opened, not for the length of
        the edge — otherwise it walls in carriageway that was never blocked."""
        away = box(origin=(0.0, 0.0, 400.0), size=6.0)

        wall, metres = _retaining_wall(away, _plan(line((0, 0.5, 0), (6, 0.5, 0))), away)

        assert wall is None
        assert metres == 0.0

    def test_the_wall_faces_the_carriageway(self) -> None:
        """A face wound away from the road is invisible from it and solid from
        behind — the hole this stage exists to remove, wearing the other sign."""
        cut, plan = self._cut(4.0)

        wall, _ = _retaining_wall(cut, plan, cut)

        assert wall is not None
        # Through the shipped counter, not a second hand-rolled facing test: what
        # ships is what `_facing_away` says, so that is what has to be pinned.
        assert _facing_away(wall, plan.points) == 0

    def test_the_facing_counter_can_actually_fail(self) -> None:
        """🔴 `Q72`: the test of a counter is not that it reads 0 but that some
        reachable state makes it non-zero. Mirrored about the ribbon, every quad
        turns its back on the road and the counter must say so."""
        cut, plan = self._cut(4.0)
        wall, _ = _retaining_wall(cut, plan, cut)

        reversed_wall = replace(wall, triangles=wall.triangles[:, ::-1])

        assert _facing_away(reversed_wall, plan.points) == wall.triangle_count


class TestStructureSelection:
    def test_only_infrastructure_is_cut(self) -> None:
        """🔴 A tile is one merged primitive, so `TEXCOORD_0.y` is the only thing
        telling a viaduct from a shopfront. Selecting on anything else here would
        carve buildings, which `Q19` measured as a different problem and refused."""
        assert _structure(_uv(box(), "INFRASTRUCTURE")).all()
        assert not _structure(_uv(box(), "BUILDING")).any()
        assert not _structure(_uv(box(), "TERRAIN(TB)")).any()

    def test_a_tile_without_uvs_is_cut_nothing(self) -> None:
        """Rather than raising: `landmarks/*.glb` carry no class payload, and a
        stage that refused them would fail on a bundle that is correct."""
        assert not _structure(box()).any()


class TestReRunning:
    """🔴 A second pass DEGRADES the first rather than repeating it."""

    def test_carving_carved_tiles_is_refused(self, tmp_path, hong_kong) -> None:
        """The retaining wall stands on the prism's own side planes, so a re-run
        reads it as wholly inside, removes it and rebuilds a shorter one —
        measured at `e327` 141.8 → 75.8 m of wall in one repeat, with every
        counter still closing. Silent loss, so the stage refuses instead.

        ⚠️ Reached by `--from roads`, not only by running this stage twice: the
        tiles on disk are already carved by then.
        """
        out = tmp_path / "wan_chai"
        out.mkdir(parents=True)
        write_document(
            out / BUILDINGS_MANIFEST_NAME,
            {
                "schema_version": BUILDINGS_MANIFEST_SCHEMA,
                "city_id": hong_kong.id,
                "region_id": "wan_chai",
                "tile_size_m": 150,
                "grid": {},
                "lod_cell_sizes_m": [],
                "class_lod_cell_sizes_m": {},
                "tiles": [],
                "excluded": {},
                CARVED_EDGES_KEY: [233],
            },
        )
        with pytest.raises(ValueError, match="already carved"):
            build_region(hong_kong, "wan_chai", out_root=tmp_path)
