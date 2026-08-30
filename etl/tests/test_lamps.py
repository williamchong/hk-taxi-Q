"""`pipeline/lamps.py` — the published lamp posts (`P3-26`).

⚠️ **Every failure this stage has renders as a perfectly drawn lamp post, or as
nothing at all.** A column on the wrong side of the street is a good column; an
arm reaching away from the road is a good arm; a prism wound inward vanishes
entirely under `cull_back`. So what is asserted here is the arithmetic nothing
downstream can see — the winding, the registration's direction, the invariant
that no column stands in the road, and the partitions that have to close.

🔴 **The winding tests are the ones that earned their place.** This stage
shipped **25,116 of 35,880** triangles facing away on its first run, because it
inherited the ring reversal that `signs._draw_pole` and `signals._draw_post`
both call "the whole correctness of this function" — and which is wrong here,
since `_strut` builds its own frame instead of mapping onto world `X`/`Z`.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.arrows import Ribbon
from pipeline.config import _LAMP_MEASURES, load_config
from pipeline.lamps import (
    LAMPS_MATERIAL,
    LampReport,
    _draw_lamp,
    _lantern,
    _merge,
    _Placed,
    _register,
    _spacing_m,
    _strut,
)
from pipeline.meshbuild import ColouredBuilder
from pipeline.railings import facing_away
from tests.helpers import CITY_YAML

# The shipped block's shape with the region's own values, so a test that pins a
# number is pinning the one that ships. Held here rather than read out of
# `hong_kong.yaml` for `test_signs.py`'s stated reason: a test that mutates the
# real city file's block cannot then assert what the real block says.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "UtilityPoint",
    "fields": {"kind": "UTILITYPOINTTYPE"},
    "kinds": ["LPO"],
    "column_material": "galvanised_steel",
    "column_height_m": 9.0,
    "column_radius_m": 0.09,
    "column_sides": 6,
    "arm_reach_m": 1.6,
    "arm_radius_m": 0.06,
    "arm_drop_m": 0.5,
    "lantern_length_m": 0.8,
    "lantern_width_m": 0.32,
    "lantern_depth_m": 0.16,
    "max_offset_m": 12.0,
    "outset_m": 0.6,
    "max_shift_m": 3.0,
    "merge_m": 0.75,
    "gap_report_m": 40.0,
}


# ⚠️ **The block names a material, so the fixture city has to declare one.**
# That is the whole shape of `Q33` arriving at this layer — every other furniture
# stage's tests carry an inline `colours:` mapping and never touch `materials:`,
# because `signs.colours` is exempt from the palette rule and this is not.
# `_check_every_material_is_used` means it cannot simply be added and left
# unreferenced, which is why it goes in beside the block rather than in
# `helpers.py`.
# ⚠️ **The reflectance is 14.70 and not Hong Kong's 28.0**, because `testville`'s
# `exposure_anchor` is 1.0 where Hong Kong's is 0.520 — the same colour claims a
# different material under a different sun, which is exactly what the anchor
# means and why `_check_exposure` grades the pair rather than either alone.
COLUMN_MATERIAL = {
    "colour": "#6b6b6b",
    "reflectance": 14.70,
    "source": "test fixture; weathered hot-dip galvanised steel is 25-35%",
}


def city_with(tmp_path, block: dict[str, Any] | None):
    """`testville` carrying the given lamps block, through the real loader."""
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["lamps"] = block
        document["materials"]["galvanised_steel"] = COLUMN_MATERIAL
    path = tmp_path / "testville.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_config(path)


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).lamps


def mutated(tmp_path, mutate):
    """`testville` with `BLOCK` altered by `mutate`, through the real loader."""
    block = copy.deepcopy(BLOCK)
    mutate(block)
    return city_with(tmp_path, block)


def placed(x: float = 0.0, z: float = 0.0, y: float = 0.0, arm=(1.0, 0.0)) -> _Placed:
    """One registered column, for the tests that do not exercise the registration.

    ⚠️ **`kerb_offset_m` and `half_width_m` are what the second-stage refusal
    settled on**, not what the config asked for. `_measure_placement` grades the
    placement rather than re-snapping it, so a test that wants to move the
    grading moves these — and a stage that started re-deriving them would make
    this helper a lie, which is the point of it carrying them at all.
    """
    return _Placed(
        kind="LPO",
        x=x,
        z=z,
        y=y,
        arm=np.array(arm, dtype=float),
        arm_reach_m=1.6,
        kerb_offset_m=5.6,
        half_width_m=5.0,
    )


class _Snap:
    """The two fields `_register` reads off a `Snap`, without a road graph.

    ⚠️ **A stand-in rather than a real snap**, because what is under test is the
    registration's *arithmetic* — where a column goes given an offset and a
    half-width — and building a graph to reach it would test `Segments` instead.
    """

    def __init__(self, offset_m: float, heading_deg: float = 0.0, t: float = 0.5) -> None:
        self.offset_m = offset_m
        self.heading_deg = heading_deg
        self.t = t


class _Ribbon:
    """A straight ribbon of constant half-width, running north up `x = 0`."""

    def __init__(self, half_width_m: float) -> None:
        self._half_width_m = half_width_m

    def half_width_at(self, t: float) -> float:
        return self._half_width_m

    def foot_at(self, t: float) -> np.ndarray:
        return np.array([0.0, 0.0])

    # The real arithmetic, bound onto the stub — the method reads only
    # `half_width_at` and `foot_at`, and copying it here would test a copy.
    kerb_target = Ribbon.kerb_target


class TestTheRegistrationRunsOutwardOnly:
    """🔴 **`Q78`'s clamp, and the reason this stage follows `signs.py` rather
    than `signals.py` or `railings.py`.**

    The argument for moving a column at all is that `widen_default` draws the
    ribbon 1.6x the real carriageway, and that argument runs outward and nowhere
    else. `CLAUDE.md` says not to align the fence stages with it — a fence is a
    run and a conditional push would zigzag it. A lamp post is not a run.
    """

    def test_a_column_inside_the_ribbon_is_pushed_out_to_the_kerb(self, spec):
        report = LampReport()
        placed, side = _register(
            spec, _Snap(offset_m=4.0), _Ribbon(5.0), np.array([4.0, 0.0]), report
        )

        # Heading 0 is north, so the nearside runs along one axis; what matters
        # is the magnitude, which is half-width plus outset.
        assert float(np.linalg.norm(placed)) == pytest.approx(5.6)
        assert side == 1.0
        assert report.posts_kept_as_surveyed == 0
        assert report.shift_m == pytest.approx([1.6])

    def test_a_column_already_clear_keeps_the_point_landsd_surveyed(self, spec):
        """🔴 **The whole of `Q78`.** Assigning the target unconditionally would
        pull this column 1.4 m *toward* the road — and `shift_m` is an absolute
        value, so no counter could tell that from a 1.4 m push."""
        published = np.array([7.0, 0.0])
        report = LampReport()
        placed, _ = _register(spec, _Snap(offset_m=7.0), _Ribbon(5.0), published, report)

        assert placed is published
        assert report.posts_kept_as_surveyed == 1

    def test_a_column_kept_as_surveyed_still_appends_a_real_zero(self, spec):
        """⚠️ **Not a skipped append.** The identity over `len(shift_m)` is what
        lets a reader decompose the distribution, and a skipped entry breaks it
        silently."""
        report = LampReport()
        _register(spec, _Snap(offset_m=7.0), _Ribbon(5.0), np.array([7.0, 0.0]), report)

        assert report.shift_m == [0.0]

    def test_a_move_past_the_bar_is_refused(self, spec):
        report = LampReport()
        refused = _register(spec, _Snap(offset_m=0.0), _Ribbon(5.0), np.array([0.0, 0.0]), report)

        assert refused is None

    def test_the_refused_move_is_still_recorded(self, spec):
        """⚠️ **`Q58`'s trap.** Recorded before the refusal, so `n` exceeds
        `drawn` and the distribution can read outside its own bar. Move this
        append below the guard and every percentile is confined to
        `max_shift_m` by construction."""
        report = LampReport()
        _register(spec, _Snap(offset_m=0.0), _Ribbon(5.0), np.array([0.0, 0.0]), report)

        assert len(report.shift_m) == 1
        assert report.shift_m[0] > spec.max_shift_m

    def test_a_column_on_the_centreline_takes_the_nearside(self, spec):
        """⚠️ **`side`, not `snap.offset_m`.** `-0.0 >= 0.0` is true and
        `-0.0 > 0.0` is false, so a caller re-deriving the side from the offset
        would place the column one side and reach the arm the other."""
        report = LampReport()
        _, side = _register(spec, _Snap(offset_m=-0.0), _Ribbon(1.0), np.array([0.0, 0.0]), report)

        assert side == 1.0


class TestTheMeshFacesOutward:
    """🔴 **The failure that fails to nothing, and this stage shipped it.**

    `signs.gdshader` is `cull_back`, so winding decides visibility and the
    normal attribute does not. A mesh wound the other way is correct geometry,
    in the correct place, with the correct material, and the city simply has no
    lamps in it.
    """

    def _mesh(self, spec, arm=(1.0, 0.0)):
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _draw_lamp(
            builder,
            spec,
            placed(arm=arm),
        )
        return builder.build("test")

    def test_reversing_the_prism_ring_would_invert_most_of_it(self, spec):
        """🔴 **The regression this file exists for.** `signs._draw_pole` and
        `signals._draw_post` both reverse their ring and both are right to;
        inheriting that here inverted 70% of the layer. This pins the direction
        rather than the comment."""
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _strut(
            builder,
            spec,
            np.array([0.0, 0.0, 0.0]),
            np.array([0.0, 9.0, 0.0]),
            spec.column_radius_m,
            cap_end=True,
        )
        mesh = builder.build("column")
        assert facing_away(mesh) == 0

        # The same column with its ring the other way round, built by hand so
        # the assertion is about the geometry rather than about a flag.
        flipped = ColouredBuilder(LAMPS_MATERIAL)
        for polygon, normal, colour in zip(
            [np.flipud(block) for block in _polygons(mesh)],
            _normals(mesh),
            [(0, 0, 0)] * mesh.triangle_count,
            strict=True,
        ):
            flipped.polygon(polygon, normal, colour)
        assert facing_away(flipped.build("flipped")) > 0

    def test_the_lantern_is_a_closed_box(self, spec):
        """⚠️ **Six faces, including the top.** A five-faced box reads as a hole
        from `ART_DESIGN.md`'s `overview` viewpoint."""
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _lantern(builder, spec, np.array([0.0, 9.0, 0.0]), np.array([1.0, 0.0, 0.0]))
        mesh = builder.build("lantern")

        assert mesh.triangle_count == 12
        assert facing_away(mesh) == 0

    def test_the_lantern_faces_point_six_different_ways(self, spec):
        """A box whose faces share a normal is a box with a fold in it."""
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _lantern(builder, spec, np.array([0.0, 9.0, 0.0]), np.array([1.0, 0.0, 0.0]))
        mesh = builder.build("lantern")
        unique = {tuple(np.round(normal, 6)) for normal in mesh.normals}

        assert len(unique) == 6


def _polygons(mesh):
    """Each triangle's three corners, for the hand-built inversion above."""
    return [mesh.positions[triangle] for triangle in mesh.triangles]


def _normals(mesh):
    return [mesh.normals[triangle[0]] for triangle in mesh.triangles]


class TestTheColumnStandsOnTheDeck:
    def test_the_base_sits_at_the_snapped_height_and_not_at_world_zero(self, spec):
        """🔴 **`signals.py`'s shipped defect, pinned so it cannot arrive here.**
        `_draw_post` copied `signs._draw_pole` without its `base_y` and rooted
        every post at world y=0, running each 3-12 m down through the
        carriageway — where opaque asphalt hides it from any camera above."""
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _draw_lamp(
            builder,
            spec,
            placed(y=4.25),
        )
        low, high = builder.build("lamp").aabb()

        assert low[1] == pytest.approx(4.25)
        # ⚠️ **The top of the mesh is the ARM's shoulder, not the column top.**
        # The bracket prism starts at the column top and slopes down, so its
        # cross-section carries `arm_radius_m` of it above the axis — 13.30 for a
        # column topping out at 13.25. Asserted with that tolerance rather than
        # exactly, because "exactly the column height" is the wrong claim and
        # tightening it would be pinning a bug.
        assert high[1] == pytest.approx(4.25 + spec.column_height_m, abs=spec.arm_radius_m)
        assert high[1] > 4.25 + spec.column_height_m

    def test_the_lantern_hangs_at_the_far_end_of_the_arm(self, spec):
        """⚠️ **A horizontal arm plus a separately-dropped lantern was the first
        shape and it leaves the housing floating.** The arm slopes to meet it."""
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _draw_lamp(
            builder,
            spec,
            placed(),
        )
        low, high = builder.build("lamp").aabb()

        # The arm reaches +x, so the mesh runs from the back of the column out to
        # the reach plus half the lantern.
        assert high[0] == pytest.approx(spec.arm_reach_m + 0.5 * spec.lantern_length_m, abs=1e-6)
        # ⚠️ **`column_radius_m` is the CIRCUMRADIUS, so a hexagon's flat sits at
        # `r cos(30 deg)` — 0.078, not 0.090.** Pinned because it is the number a
        # reader checking the drawn column against a published diameter would
        # otherwise get wrong by 13%, and because nothing published constrains it
        # either way (the dimension is authored).
        assert low[0] == pytest.approx(-spec.column_radius_m * math.cos(math.pi / 6), abs=1e-6)


class TestTheMergeFoldsOnlyWhatTheMoveBroughtTogether:
    """⚠️ **Every fold here is a coincidence this stage MADE.** Unlike
    `signals._assemble` there is no surveyed clustering to reproduce: the layer
    publishes zero coincident pairs under 0.05 m.
    """

    def test_columns_on_one_point_become_one_column(self):
        report = LampReport()
        kept = _merge([placed(0.0, 0.0), placed(0.1, 0.0)], 0.75, report)

        assert len(kept) == 1
        assert report.merged == 1

    def test_columns_further_apart_than_the_radius_both_stand(self):
        report = LampReport()
        kept = _merge([placed(0.0, 0.0), placed(4.0, 0.0)], 0.75, report)

        assert len(kept) == 2
        assert report.merged == 0

    def test_a_merge_radius_above_the_shift_bar_is_refused_at_load(self, tmp_path):
        """🔴 A radius wider than the move that creates the coincidence folds
        columns that were never brought together, thinning a row whose
        regularity is the whole reason for drawing it."""
        with pytest.raises(ValueError, match="never moved together"):
            mutated(tmp_path, lambda block: block.update(merge_m=4.0))


class TestTheSpacingInstrument:
    """🔴 **This layer's own failure mode, which no other stage here has.**

    A missing sign is invisible; a missing lamp in a regular row is a hole.
    Neither a refusal count nor a survivor count can see a rhythm.
    """

    def test_spacing_is_the_nearest_neighbour_of_each_point(self):
        assert _spacing_m([(0.0, 0.0), (3.0, 0.0), (10.0, 0.0)]) == pytest.approx([3.0, 3.0, 7.0])

    def test_one_point_has_no_spacing(self):
        assert _spacing_m([(0.0, 0.0)]) == []

    def test_removing_a_point_widens_the_gap_it_left(self):
        """The whole argument for publishing both distributions: the drawn set
        alone says nothing about what refusing cost."""
        surveyed = _spacing_m([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)])
        drawn = _spacing_m([(0.0, 0.0), (20.0, 0.0)])

        assert max(surveyed) == pytest.approx(10.0)
        assert max(drawn) == pytest.approx(20.0)


class TestTheSelectionReadsAPublishedDomain:
    """✅ **The first street-furniture vocabulary here the publisher defines.**

    `LPO - Lamp post` is a coded-value domain inside the geodatabase, so unlike
    `Railings.classes` and `Signals.head_prefixes` a wrong entry is checkable
    against the source rather than only reviewable.
    """

    def test_a_declared_kind_is_admitted(self, spec):
        assert spec.is_lamp("LPO")

    def test_a_hydrant_is_not(self, spec):
        assert not spec.is_lamp("FWH")

    def test_an_empty_kinds_list_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="draws nothing"):
            mutated(tmp_path, lambda block: block.update(kinds=[]))

    def test_a_repeated_kind_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="repeats a code"):
            mutated(tmp_path, lambda block: block.update(kinds=["LPO", "LPO"]))


class TestTheLoaderRefusesGeometryThatCannotBeDrawn:
    def test_a_material_the_city_does_not_declare_is_refused(self, tmp_path):
        """✅ **The colour goes through `Q33`, not around it.** `signs.colours`'
        exemption rests on a printed specification with no reflectance and on
        four colours in one draw call; a lamp post is neither, so the value lives
        in `materials:` where `_check_exposure` grades it."""
        with pytest.raises(ValueError):
            mutated(tmp_path, lambda block: block.update(column_material="zinc"))

    def test_a_lantern_hanging_below_the_ground_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="below the ground"):
            mutated(tmp_path, lambda block: block.update(arm_drop_m=9.0))

    def test_an_arm_thicker_than_its_column_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="thinner than its own column"):
            mutated(tmp_path, lambda block: block.update(arm_radius_m=0.2))

    def test_a_lantern_running_back_through_its_column_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="back through its column"):
            mutated(tmp_path, lambda block: block.update(lantern_length_m=4.0))

    def test_a_two_sided_column_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="at least 3"):
            mutated(tmp_path, lambda block: block.update(column_sides=2))

    def test_a_nan_measurement_is_refused(self, tmp_path):
        """⚠️ YAML 1.1 resolves `.nan`, and a NaN passes every sign test and
        then makes false every comparison it feeds."""
        with pytest.raises(ValueError, match="finite"):
            mutated(tmp_path, lambda block: block.update(column_height_m=float("nan")))


class TestTheStageIsWiredWhereTheEngineLooks:
    def test_the_material_name_is_the_one_the_import_dispatches_on(self):
        """⚠️ A name, not a shader: this layer shares `signs.gdshader` and
        differs only in `game/tuning/lamps.tres` (`Q61`, `Q71`)."""
        assert LAMPS_MATERIAL == "lamps"


class TestTheShippedRegionReproducesItsPublishedNumbers:
    """The stage's own manifest, asserted against the values `DECISIONS.md`
    `Q82` and `hong_kong.yaml` both quote — so a change that moves one of them
    has to move the record with it."""

    def test_the_fixture_block_still_matches_the_shipped_one(self):
        """🔴 **The guard on every other test in this file that uses `BLOCK`.**

        `BLOCK` hand-copies `hong_kong.yaml`'s eighteen values so a mutation test
        can alter one without editing the shipped city. Nothing else makes the two
        stay equal — so without this, changing `column_sides` in the real city
        leaves `test_a_lamp_costs_forty_triangles` green while `verify_lamps.gd`'s
        bar, `PROGRESS.md`'s 35,880 and `Q82`'s per-lamp enumeration all go stale
        at once. Field-for-field, deliberately, rather than on a spot check.
        """
        shipped = load_config().lamps

        assert shipped is not None
        assert shipped.kinds == tuple(BLOCK["kinds"])
        assert shipped.column_sides == BLOCK["column_sides"]
        assert shipped.layer.layer == BLOCK["layer"]
        assert shipped.column_material.name == BLOCK["column_material"]
        for name in _LAMP_MEASURES:
            assert getattr(shipped, name) == pytest.approx(BLOCK[name]), name

    def test_the_lantern_overhangs_the_kerb_by_reach_less_outset(self):
        """The design intent as arithmetic, and the value `lamps.json` publishes
        as `lantern_overhang_m.p50`: a column stands `outset_m` behind the kerb
        and its lantern reaches `arm_reach_m` back in."""
        shipped = load_config().lamps

        assert shipped.arm_reach_m - shipped.outset_m == pytest.approx(1.0)

    def test_the_shipped_block_declares_the_published_domain_code(self):
        spec = load_config().lamps

        assert spec is not None
        assert spec.kinds == ("LPO",)

    def test_the_shipped_block_takes_the_measured_shift_bar(self):
        """🔴 3.0 rather than `signs.py`'s 6.0, and the sweep in the config
        comment is the argument: 6.0 buys 68 posts for a 6 m lateral move."""
        spec = load_config().lamps

        assert spec.max_shift_m == pytest.approx(3.0)

    def test_a_lamp_costs_forty_triangles(self, spec):
        """⚠️ **Multiplied by 897, which is why it is pinned.** Column 12 sides
        + 4 cap, arm 12 sides and no cap, lantern 6 faces of 2."""
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _draw_lamp(
            builder,
            spec,
            placed(),
        )

        assert builder.build("lamp").triangle_count == 40

    def test_half_the_mesh_stands_upright_by_construction(self, spec):
        """🔴 **The number `verify_lamps.gd`'s bar is derived from**, and the
        one its first version invented as 0.70. 20 of 40: column sides 12 plus
        the lantern's four vertical faces 8."""
        builder = ColouredBuilder(LAMPS_MATERIAL)
        _draw_lamp(
            builder,
            spec,
            placed(),
        )
        mesh = builder.build("lamp")
        cross = mesh.triangle_cross()
        upright = np.abs(cross[:, 1] / np.linalg.norm(cross, axis=1)) <= 0.35

        assert int(upright.sum()) == 20
        assert math.isclose(upright.mean(), 0.5)
