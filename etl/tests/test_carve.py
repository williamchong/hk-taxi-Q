"""`P3-28` carve tests.

Two layers, mirroring the module. The prism and the retaining wall are pure
geometry, tested on hand-built meshes where every triangle's fate is checkable by
eye. The stage itself is tested for the three things no frame can show: that an
absent config block leaves the bundle alone, that a region declaring no edges
takes that same path, and that a configured edge the graph does not carry stops
the build rather than being skipped.

🔴 **The wall tests are the ones that matter.** Every other way this stage breaks
renders as a plausible frame — a wall at the wrong height still looks like a
wall — and the estate is not watertight, so nothing can check the cut closed.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pipeline.buildings import (
    BUILDINGS_MANIFEST_NAME,
    BUILDINGS_MANIFEST_SCHEMA,
    CARVED_EDGES_KEY,
    FACADE_MATERIAL,
    collider_name,
    facade_uv,
    identity_uv2,
    occluder_name,
)
from pipeline.carve import (
    CarveReport,
    EdgeCarve,
    EdgePlan,
    Population,
    _band_plans,
    _band_split,
    _carve_plan,
    _carve_tile,
    _double_side,
    _facing_away,
    _named,
    _prisms,
    _retaining_wall,
    _stations,
    _structure,
    _structure_runs,
    build_region,
)
from pipeline.config_blocks.roads import Parapets
from pipeline.documents import write_document
from pipeline.gltf import MeshData, read_glb, write_glb
from pipeline.mesh import subtract_prism
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA
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


def _manifest(city_id: str, **extra) -> dict:
    """A buildings manifest with nothing in it but the keys `carve` reads.

    Two stage tests need one, and the boilerplate is nine keys of which they
    differ in two — so the shared shape lives here and each test states only
    what it is actually about.
    """
    return {
        "schema_version": BUILDINGS_MANIFEST_SCHEMA,
        "city_id": city_id,
        "region_id": "wan_chai",
        "tile_size_m": 150,
        "grid": {},
        "lod_cell_sizes_m": [],
        "class_lod_cell_sizes_m": {},
        "tiles": [],
        "excluded": {},
        **extra,
    }


def _uv(mesh: MeshData, class_id: str) -> MeshData:
    """The same mesh, tagged through the **real** encoder.

    ⚠️ Not a hand-rolled copy of `facade_uv`'s pack format. A test that encodes
    and decodes with its own copy of the convention stays self-consistent while
    the shipped encoder moves — which is the one failure `_structure` exists to
    catch.
    """
    return replace(
        mesh,
        uvs=facade_uv(style(), class_id, mesh),
        uv2=identity_uv2(style(), class_id, mesh, 0),
    )


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

    def test_the_wall_is_capped_at_the_face_top(self) -> None:
        """`Q147`: the cut face closes the cut below the deck and stops just
        above it. Drawn to the removed flank's top it was `e99`'s parapet."""
        cut, plan = self._cut(4.0)
        plan.face_above_m = 0.0

        wall, metres = _retaining_wall(cut, plan, cut)

        assert wall is not None and metres > 0.0
        assert wall.positions[:, 1].max() == pytest.approx(0.5)

    def test_the_cap_follows_the_higher_station_of_a_sloped_segment(self) -> None:
        """A cap at the lower station would leave a slit into the hollow at
        the higher end; the lip at the low end is one station's rise."""
        cut = box(origin=(0.0, 0.0, -3.0), size=6.0)
        plan = _plan(line((0, 0.5, 0), (6, 1.5, 0)), half_m=3.0)
        plan.face_above_m = 0.0

        wall, _ = _retaining_wall(cut, plan, cut)

        assert wall is not None
        assert wall.positions[:, 1].max() == pytest.approx(1.5)

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

    def test_the_back_face_is_coincident_with_the_front(self) -> None:
        """⚠️ Coincident and not offset: exactly one of the pair survives
        `cull_back` from any viewpoint, so there is nothing to z-fight. A
        thickness instead would push the back face into retained structure."""
        cut, plan = self._cut(4.0)
        wall, _ = _retaining_wall(cut, plan, cut)

        both = _double_side(wall)
        faces = both.positions[both.triangles]
        front, back = faces[: wall.triangle_count], faces[wall.triangle_count :]

        assert both.triangle_count == 2 * wall.triangle_count
        assert np.array_equal(front, back[:, ::-1, :])

    def test_the_back_face_carries_its_own_negated_normal(self) -> None:
        """🔴 This is what the free version costs. Appending `triangles[:, ::-1]`
        alone doubles the faces at zero added vertices, but the back face then
        shares the front's outward `NORMAL` — and `city_facade.gdshader` shades
        from it, so the back of the wall would be lit as though it faced the road.
        Nothing else here can see that: the geometry, the counters and every other
        assertion are identical either way."""
        cut, plan = self._cut(4.0)
        wall, _ = _retaining_wall(cut, plan, cut)

        both = _double_side(wall)
        front, back = both.normals[: len(wall.normals)], both.normals[len(wall.normals) :]

        assert np.array_equal(front, -back)
        assert not np.allclose(front, 0.0)

    def test_the_mirror_is_why_the_counter_is_taken_first(self) -> None:
        """🔴 Half a double-sided wall faces away *by construction*, so
        `_facing_away` graded after the mirror reads half the wall whatever the
        geometry does — `Q72`'s tautology from the other side. This pins the
        number the build would get if the two were ever reordered."""
        cut, plan = self._cut(4.0)
        wall, _ = _retaining_wall(cut, plan, cut)

        assert _facing_away(wall, plan.points) == 0
        assert _facing_away(_double_side(wall), plan.points) == wall.triangle_count

    def test_the_mirror_carries_per_vertex_attributes_rather_than_tiling_one(self) -> None:
        """🔴 The spelling that rebuilds the buffers has to tile vertex 0's value,
        and `TEXCOORD_1.x` is the `SurfaceClass` channel `_structure` cuts on — so
        that spelling misclassifies a wall silently. Nothing about the wall's own
        geometry can catch it, because `_retaining_wall` happens to emit constant
        attributes; this hands it varying ones and checks both halves survive."""
        cut, plan = self._cut(4.0)
        wall, _ = _retaining_wall(_uv(cut, "INFRASTRUCTURE"), plan, cut)
        assert wall is not None and wall.uvs is not None
        varied = wall.uvs.copy()
        varied[:, 0] = np.arange(len(varied), dtype=varied.dtype)

        both = replace(wall, uvs=varied)
        both = _double_side(both)

        assert both.uvs is not None
        assert np.array_equal(both.uvs[: len(varied)], varied)
        assert np.array_equal(both.uvs[len(varied) :], varied)


class TestStructureSelection:
    def test_only_infrastructure_is_cut(self) -> None:
        """🔴 A tile is one merged primitive, so `TEXCOORD_1.x` is the only thing
        telling a viaduct from a shopfront. Selecting on anything else here would
        carve buildings, which `Q19` measured as a different problem and refused."""
        assert _structure(_uv(box(), "INFRASTRUCTURE")).all()
        assert not _structure(_uv(box(), "BUILDING")).any()
        assert not _structure(_uv(box(), "TERRAIN(TB)")).any()

    def test_a_tile_without_the_identity_channel_is_cut_nothing(self) -> None:
        """Rather than raising: `landmarks/*.glb` carry no class payload, and a
        stage that refused them would fail on a bundle that is correct."""
        assert not _structure(box()).any()


def _band_plan(
    points: np.ndarray, *, half_m: float = 4.5, tolerance_m: float = 0.3, max_m: float = 2.5
) -> EdgePlan:
    """A parapet-band plan over a hand-built ribbon: floored AT the ribbon."""
    offsets = mitres(points)
    floors = points[:, 1].copy()
    ceilings = np.full(len(points), np.inf)
    row = EdgeCarve(0, "test", 6.0, "measured", len(points), 0, 0, 0.0, 0.0, 0.0)
    row.population = Population.PARAPET
    return EdgePlan(
        row=row,
        points=points,
        offsets=offsets,
        half_m=half_m,
        floors=floors,
        prisms=_prisms(points, offsets, half_m, floors, ceilings),
        band=True,
        wall_tolerance_m=tolerance_m,
        wall_max_m=max_m,
        half_at=np.full(len(points), half_m),
    )


def _deck_with_parapet() -> MeshData:
    """A 1 m thick deck slab, top at y=0, 6 m wide across a ribbon at y=0
    running along x, with a 0.3 m thick, 1.2 m tall parapet standing on its
    z=+3 edge — the shape every flyover in the estate has."""
    # `box` scales about the origin, so the origin is placed pre-scale.
    deck = box(origin=(0.0, -6.0, -3.0), size=6.0)
    deck = replace(deck, positions=deck.positions * np.array([1.0, 1.0 / 6.0, 1.0]))
    parapet = box(origin=(0.0, 0.0, 54.0), size=6.0)
    parapet = replace(parapet, positions=parapet.positions * np.array([1.0, 0.2, 0.05]))
    return MeshData(
        name="structure",
        positions=np.concatenate([deck.positions, parapet.positions]),
        normals=np.concatenate([deck.normals, parapet.normals]),
        triangles=np.concatenate([deck.triangles, parapet.triangles + len(deck.positions)]),
    )


class TestParapetBand:
    """🔴 `P3-51`'s band keeps the deck and removes the parapet, and the naive
    prism does neither — a floor at the ribbon takes the deck top with the
    wall, and a car leaving the road falls THROUGH the deck. Every test here
    is on the hand-built deck above, where each triangle's fate is checkable."""

    RIBBON = line((0, 0.0, 0), (6, 0.0, 0))

    def test_the_parapet_goes_and_the_deck_top_stays(self) -> None:
        structure = _deck_with_parapet()
        plan = _band_plan(self.RIBBON)

        carved = _carve_plan(structure, plan, structure)
        remaining, cut, wall, metres, kept = (
            carved.remaining,
            carved.removed,
            carved.wall,
            carved.wall_m,
            carved.deck_top_kept,
        )

        assert cut is not None and remaining is not None
        # Nothing above the deck survives: the parapet's 1.2 m is gone.
        assert remaining.positions[:, 1].max() == pytest.approx(0.0, abs=1e-6)
        # And the deck top itself is still there, at the ribbon's own height —
        # upward-facing triangles at y=0 inside the band.
        top = remaining.positions[remaining.triangles][:, :, 1]
        assert (np.abs(top) < 1e-6).all(axis=1).any()
        assert kept > 0
        # The band draws no wall.
        assert wall is None and metres == 0.0

    def test_the_naive_prism_takes_the_deck_with_the_wall(self) -> None:
        """⚠️ The trap, pinned so nobody 'simplifies' the split away: the same
        prism as a plain carve, floored at the ribbon, removes the deck top
        beside the ribbon — the mutation `deck_top_kept` exists to catch."""
        structure = _deck_with_parapet()
        naive = _band_plan(self.RIBBON)
        naive.band = False

        carved = _carve_plan(structure, naive, structure)
        remaining, cut, kept = carved.remaining, carved.removed, carved.deck_top_kept

        assert cut is not None
        assert kept == 0
        top = None if remaining is None else remaining.positions[remaining.triangles][:, :, 1]
        assert top is None or not (np.abs(top) < 1e-6).all(axis=1).any()

    def test_the_split_reads_the_normal_and_the_height(self) -> None:
        """Both tests, because each alone is wrong: by normal alone a cap a
        metre up is kept as a floating slab; by height alone the deck top goes."""
        structure = _deck_with_parapet()
        parapet, deck = _band_split(structure, 0.0, 0.3)
        corners = structure.positions[structure.triangles]
        tops = corners[:, :, 1].min(axis=1)
        # The parapet's cap: horizontal, wholly above the tolerance.
        cap = tops > 1.0
        assert cap.any() and parapet[cap].all()
        # The parapet's faces: vertical, so walls.
        faces = (corners[:, :, 2].min(axis=1) >= 2.7 - 1e-9) & (corners[:, :, 1].max(axis=1) > 0.5)
        assert faces.any() and parapet[faces].all()
        # The deck top: horizontal at the ribbon, kept.
        deck_top = (np.abs(corners[:, :, 1]) < 1e-9).all(axis=1)
        assert deck_top.any() and deck[deck_top].all()

    def test_a_face_rising_past_wall_max_m_is_not_a_parapet(self) -> None:
        """A pier, a higher deck's side, a noise barrier: a wall whose top
        stands more than `wall_max_m` above the deck stays whole, however
        close to the rail it stands."""
        structure = _deck_with_parapet()
        pier = box(origin=(0.0, 0.0, 54.0), size=6.0)
        pier = replace(pier, positions=pier.positions * np.array([1.0, 1.0, 0.05]))
        with_pier = MeshData(
            name="structure",
            positions=np.concatenate([structure.positions, pier.positions]),
            normals=np.concatenate([structure.normals, pier.normals]),
            triangles=np.concatenate(
                [structure.triangles, pier.triangles + len(structure.positions)]
            ),
        )

        remaining = _carve_plan(with_pier, _band_plan(self.RIBBON), with_pier).remaining

        assert remaining is not None
        assert remaining.positions[:, 1].max() == pytest.approx(6.0)
        # The parapet's ten standing triangles go and its underside, flat on
        # the deck at the ribbon's height, stays as deck; the pier's twelve stay.
        assert remaining.triangle_count == with_pier.triangle_count - 10

    def test_a_parapet_whole_in_the_band_is_taken_whole(self) -> None:
        """No slicing where none is needed: the parapet's ten standing
        triangles come out as ten, not as one sliver per station, and its
        underside — flat on the deck, at the ribbon's height — is deck."""
        structure = _deck_with_parapet()
        plan = _band_plan(self.RIBBON)

        carved = _carve_plan(structure, plan, structure)

        assert carved.removed is not None
        assert carved.removed.triangle_count == 10
        assert carved.remaining is not None
        assert carved.remaining.triangle_count == structure.triangle_count - 10

    def test_a_face_below_the_ribbon_is_outside_the_band(self) -> None:
        """The deck's outer face below the deck stays: the slab keeps its
        thickness and the flyover is not a floating sheet from below."""
        structure = _deck_with_parapet()
        remaining = _carve_plan(structure, _band_plan(self.RIBBON), structure).remaining

        assert remaining is not None
        assert remaining.positions[:, 1].min() == pytest.approx(-1.0)

    def test_the_band_is_planned_by_level_and_by_structure_run(self) -> None:
        """A listed edge or a banded level takes the whole polyline; a level-0
        edge takes each run of `on_structure` stations two or more long, and
        nothing else."""
        spec = _spec(
            Parapets(
                levels=(1,),
                on_structure=True,
                reach_m=1.5,
                wall_tolerance_m=0.3,
                wall_max_m=2.5,
                face_above_m=0.0,
            )
        )
        edge = {
            "id": 7,
            "road_name": {"en": "TEST"},
            "width_m": 6.0,
            "width_source": "measured",
            "offset_m": 0.0,
            "polyline": [[0, 5, 0], [10, 5, 0], [20, 5, 0], [30, 5, 0], [40, 5, 0]],
            "elevation_level": 1,
        }
        flyover = _band_plans(edge, spec, _NoSoffit())
        assert len(flyover) == 1 and flyover[0].band
        assert flyover[0].row.population == Population.PARAPET
        assert flyover[0].half_m == pytest.approx(3.0 + 1.5)

        # The measured rim widens the band where it reaches past the width:
        # the parapet stands at the rim, not at the authored rail.
        rimmed = dict(edge, deck_rim_m=[[2.0, 4.0], [8.0, 3.0], [2.0, 2.0], [1.0, 1.0], [0.0, 0.0]])
        assert _band_plans(rimmed, spec, _NoSoffit())[0].half_m == pytest.approx(8.0 + 1.5)

        approach = dict(edge, elevation_level=0, on_structure=[False, True, True, False, True])
        runs = _band_plans(approach, spec, _NoSoffit())
        assert len(runs) == 1 and len(runs[0].points) >= 2
        assert runs[0].points[:, 0].min() == pytest.approx(10.0)
        assert runs[0].points[:, 0].max() == pytest.approx(20.0)

        street = dict(edge, elevation_level=0, on_structure=[False] * 5)
        assert _band_plans(street, spec, _NoSoffit()) == []
        # A listed ramp takes the band whole, whatever its flags say: `Q19`'s
        # eight are walled flanks whose heights came from terrain.
        assert len(_band_plans(street, spec, _NoSoffit(), listed=(7,))) == 1
        tunnel = dict(edge, elevation_level=-1)
        assert _band_plans(tunnel, spec, _NoSoffit()) == []

    def test_no_block_plans_no_band(self) -> None:
        edge = {"id": 1, "polyline": [[0, 0, 0], [1, 0, 0]], "elevation_level": 1}
        assert _band_plans(edge, _spec(None), _NoSoffit()) == []

    def test_structure_runs_need_two_stations(self) -> None:
        polyline = np.arange(18, dtype=np.float64).reshape(6, 3)
        runs = _structure_runs(polyline, [True, False, True, True, False, True])
        assert len(runs) == 1
        assert runs[0].shape == (2, 3)


class _NoSoffit:
    """A height field with nothing overhead."""

    def sample_lowest_soffit_above(self, x: np.ndarray, _z: np.ndarray, _above: np.ndarray):
        return np.full(len(x), np.nan)


def _spec(parapets: Parapets | None):
    from pipeline.config_blocks.roads import Carve

    return Carve(
        edges={},
        station_m=2.0,
        floor_below_m=2.0,
        headroom_m=5.1,
        soffit_clearance_m=0.3,
        parapets=parapets,
    )


class TestRegionScope:
    """🔴 An edge id is a per-region ORDINAL, so the list is keyed by region.

    `roads.py` assigns `edge_id = len(pending)`. Unkeyed, `wan_chai`'s eight ids
    resolve **7 of 8** in `mong_kok`, naming six roads — ARGYLE, FERRY, HOI WANG,
    LIBERTY, PITT and WATERLOO —
    and the only thing that stopped them being carved is that the largest id is
    788: all eight resolve only in a region of 789 edges or more, and `mong_kok`
    has 537 where `wan_chai` has 797.
    """

    def test_a_region_with_no_edges_carves_nothing(self, tmp_path, hong_kong) -> None:
        """🔴 **The mutation check that matters.** `causeway_bay` declares no
        edges, so the stage must take the absent block's path — write its
        document, re-emit **zero** tiles and touch no manifest — rather than
        reaching for a list belonging to another region.

        It returns before reading `buildings.json` at all, which is why this
        needs nothing on disk: an unmeasured region is not a half-built one.
        """
        out = tmp_path / "causeway_bay"
        out.mkdir(parents=True)
        # Without the parapet band: declared, it reads the tiles of every region
        # even where it plans nothing.
        unbanded = replace(hong_kong, carve=replace(hong_kong.carve, parapets=None))

        report = build_region(unbanded, "causeway_bay", out_root=tmp_path)

        assert report.edges == []
        assert report.tiles_written == []
        assert not (out / BUILDINGS_MANIFEST_NAME).exists()

    def test_an_edge_the_graph_does_not_carry_stops_the_build(self, tmp_path, hong_kong) -> None:
        """🔴 **Refused, never skipped**, and the refusal names the region.

        Skipping is the intuitive fix and it is the dangerous one: it would let a
        list written for one region cut prisms out of whatever the same integers
        happen to name in another, with both partitions closing, `facing_away` 0
        and `check.sh` green. That is `Q54` inverted — published structure
        removed on the authority of an id nobody surveyed.
        """
        out = tmp_path / "wan_chai"
        out.mkdir(parents=True)
        (out / "tiles").mkdir()
        tile = _named(_uv(box(), "INFRASTRUCTURE"), "t", FACADE_MATERIAL)
        write_glb(out / "tiles" / "t.glb", [tile])
        write_document(
            out / BUILDINGS_MANIFEST_NAME,
            _manifest(hong_kong.id, tiles=[{"id": "t", "lods": [{"path": "tiles/t.glb"}]}]),
        )
        # A graph carrying none of the configured ids — a region refreshed, or a
        # list written for its neighbour.
        write_document(
            out / ROADGRAPH_NAME,
            {
                "schema_version": ROADGRAPH_SCHEMA,
                "city_id": hong_kong.id,
                "region_id": "wan_chai",
                "nodes": [],
                "edges": [],
            },
        )

        with pytest.raises(ValueError, match="for region wan_chai"):
            build_region(hong_kong, "wan_chai", out_root=tmp_path)


class TestCollider:
    """🔴 The finest tier's collider is cut beside the render mesh (`P5-12`)."""

    @staticmethod
    def _drawn() -> MeshData:
        """A structure across the ribbon, tagged and named as a render tier is."""
        return _named(
            _uv(box(origin=(8.0, 0.0, -6.0), size=12.0), "INFRASTRUCTURE"), "t", FACADE_MATERIAL
        )

    @classmethod
    def _tile(cls, out: Path) -> dict:
        """One LOD0 file holding a structure across the ribbon twice over: the
        drawn tier with every payload, and the collider with the marker alone."""
        drawn = cls._drawn()
        collider = replace(drawn, name=collider_name("t"), colours=None, uvs=None, material=None)
        occluder = replace(collider, name=occluder_name("t"))
        (out / "tiles").mkdir(parents=True)
        write_glb(out / "tiles" / "t_lod0.glb", [drawn, collider, occluder])
        return {
            "id": "t",
            "aabb": drawn.aabb(),
            "lods": [{"path": "tiles/t_lod0.glb", "triangles": 12, "vertices": 24}],
        }

    def test_the_collider_is_cut_where_the_render_tier_is(self, tmp_path) -> None:
        """A wall carved from what the player sees and left in what the car
        hits is the stranding the carve exists to end. Both primitives lose
        the prism, the collider keeps its name and its bare payload, and the
        counters are the render tier's alone."""
        tile = self._tile(tmp_path)
        plan = _plan(line((0, 2.0, 0), (30, 2.0, 0)))
        report = CarveReport()

        _carve_tile(tmp_path, tile, [plan], report)

        drawn, collider, occluder = read_glb(tmp_path / "tiles" / "t_lod0.glb")
        assert collider.name == collider_name("t")
        assert occluder.name == occluder_name("t")
        assert drawn.triangle_count > 12 and collider.triangle_count > 12
        assert occluder.triangle_count > 12
        for mesh in (drawn, collider, occluder):
            assert not ((mesh.positions[:, 2] > -2.9) & (mesh.positions[:, 2] < 2.9)).any()
        assert tile["lods"][0]["occluder_triangles"] == occluder.triangle_count
        assert collider.colours is None and collider.uvs is None and collider.uv2 is not None
        assert drawn.colours is not None and drawn.uvs is not None
        assert tile["lods"][0]["triangles"] == drawn.triangle_count
        assert tile["lods"][0]["collision_triangles"] == collider.triangle_count
        assert report.tiles_written == ["tiles/t_lod0.glb"]
        # The counters are the render tier's alone: the same cut of the same
        # box with no collider beside it books the same removal.
        alone = _plan(line((0, 2.0, 0), (30, 2.0, 0)))
        _carve_tile(
            tmp_path / "alone", self._render_only(tmp_path / "alone"), [alone], CarveReport()
        )
        assert plan.row.triangles_removed == alone.row.triangles_removed > 0
        assert plan.row.wall_m == alone.row.wall_m > 0.0

    @classmethod
    def _render_only(cls, out: Path) -> dict:
        """The same structure with no collider beside it."""
        drawn = cls._drawn()
        (out / "tiles").mkdir(parents=True)
        write_glb(out / "tiles" / "t_lod0.glb", [drawn])
        return {"id": "t", "aabb": drawn.aabb(), "lods": [{"path": "tiles/t_lod0.glb"}]}

    def test_a_tile_without_a_collider_is_still_carved(self, tmp_path) -> None:
        """The stage does not require the second primitive: a tile written
        before `P5-12`, or a fixture, carves as it always did."""
        tile = self._render_only(tmp_path)

        _carve_tile(tmp_path, tile, [_plan(line((0, 2.0, 0), (30, 2.0, 0)))], CarveReport())

        [carved] = read_glb(tmp_path / "tiles" / "t_lod0.glb")
        assert carved.triangle_count > 12
        assert "collision_triangles" not in tile["lods"][0]


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
            _manifest(hong_kong.id, **{CARVED_EDGES_KEY: [233]}),
        )
        with pytest.raises(ValueError, match="already carved"):
            build_region(hong_kong, "wan_chai", out_root=tmp_path)
