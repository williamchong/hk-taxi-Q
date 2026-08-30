"""`pipeline/signals.py` — the published signal heads (`P3-17`).

⚠️ **Every failure this stage has renders as a perfectly drawn signal head, or
as nothing at all.** A head turned 180 degrees is a good head facing the wrong
way; a gate that started admitting push buttons draws good heads on them; a
prism wound inward vanishes entirely under `cull_back`. So what is asserted here
is the arithmetic nothing downstream can see — the winding, the derived
grouping, and the partitions that have to close.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import load_config
from pipeline.meshbuild import ColouredBuilder
from pipeline.railings import facing_away
from pipeline.signals import (
    SIGNALS_MATERIAL,
    Signal,
    SignalReport,
    _assemble,
    _draw_head,
    _draw_post,
    _merge_placements,
    _Placed,
)
from tests.helpers import CITY_YAML

# The shipped block's shape with the region's own values, so a test that pins a
# number is pinning the one that ships. Held here rather than read out of
# `hong_kong.yaml` for `test_signs.py`'s stated reason: a test that mutates the
# real city file's block cannot then assert what the real block says.
BLOCK: dict[str, Any] = {
    "source": "stands",
    "layer": "DTAD_TRAFFIC_LIGHT_PT",
    "fields": {"code": "REFNAME", "bearing": "ANGLE", "level": "ELEVATION"},
    "head_prefixes": ["P", "S"],
    "refuse_codes": [],
    "colours": {
        "body": "#2b2f33",
        "lens_red": "#4a1416",
        "lens_amber": "#4d3510",
        "lens_green": "#0f3a24",
    },
    "lens_colours": ["lens_red", "lens_amber", "lens_green"],
    "head_width_m": 0.42,
    "head_height_m": 1.10,
    "head_depth_m": 0.30,
    "lens_diameter_m": 0.30,
    "lens_segments": 12,
    "lens_lift_m": 0.012,
    "mount_height_m": 2.40,
    "post_radius_m": 0.06,
    "post_sides": 8,
    "post_headroom_m": 0.15,
    "max_offset_m": 25.0,
    "host_ambiguity_m": 3.0,
    "outset_m": 0.45,
    "max_shift_m": 6.0,
    "assembly_merge_m": 1.0,
}


def city_with(tmp_path, block: dict[str, Any] | None):
    """`testville` carrying the given signals block, through the real loader."""
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["signals"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_config(cities / "testville.yaml")


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).signals


def mutated(tmp_path, mutate):
    """`testville` with `BLOCK` altered by `mutate`, through the real loader.

    ⚠️ **These tests moved here from `test_config.py` when `P3-17`'s layer was
    dropped from the bundle** (`Q77`). They pinned the *shipped* `signals:`
    block; Hong Kong no longer declares one, so they pin `BLOCK` above instead
    — which is the shape every sibling stage's tests already use, and where
    loader validation belonged in the first place.
    """
    block = copy.deepcopy(BLOCK)
    mutate(block)
    return city_with(tmp_path, block)


def head(x: float, z: float, code: str = "P24") -> Signal:
    """One `Signal` for the assembly tests, where only position varies."""
    return Signal(code=code, x=x, z=z, axis_deg=0.0)


class TestTheAssemblyIsDerived:
    """🔴 **The join `signs.py` gets from the publisher and this stage invents.**

    `DTAD_TS_ABV_PT` carries `GG_NAME`; `DTAD_TRAFFIC_LIGHT_PT` carries nothing
    of the kind. So a post is a cluster of coincident points, and the radius is
    doing real work — a value that swallowed a neighbouring post would draw one
    post carrying six aspects and render perfectly.
    """

    def test_coincident_heads_become_one_post(self):
        posts = _assemble([head(0.0, 0.0), head(0.02, 0.0), head(0.0, 0.03)], 1.0)

        assert len(posts) == 1
        assert len(posts[0][2]) == 3

    def test_heads_further_apart_than_the_radius_stay_separate(self):
        posts = _assemble([head(0.0, 0.0), head(4.0, 0.0)], 1.0)

        assert len(posts) == 2
        assert [len(carried) for _, _, carried in posts] == [1, 1]

    def test_a_post_stands_at_the_centroid_of_what_it_carries(self):
        """⚠️ **Not at the first member's position.** That would make the post's
        place depend on the read order, so two builds of one input would
        differ — and a mesh that changes shape between builds is not
        reproducible."""
        posts = _assemble([head(0.0, 0.0), head(0.4, 0.0)], 1.0)

        assert posts[0][0] == pytest.approx(0.2)
        assert posts[0][1] == pytest.approx(0.0)

    def test_the_clustering_is_single_linkage(self):
        """Three heads in a chain, each within the radius of the next but the
        ends 1.2 m apart — one post, because they are one physical assembly."""
        posts = _assemble([head(0.0, 0.0), head(0.6, 0.0), head(1.2, 0.0)], 1.0)

        assert len(posts) == 1
        assert len(posts[0][2]) == 3

    def test_the_result_does_not_depend_on_input_order(self):
        signals = [head(0.0, 0.0), head(9.0, 0.0), head(0.1, 0.0), head(9.05, 0.0)]

        forward = _assemble(signals, 1.0)
        backward = _assemble(list(reversed(signals)), 1.0)

        assert [(x, z, len(c)) for x, z, c in forward] == [(x, z, len(c)) for x, z, c in backward]

    def test_an_empty_region_assembles_to_nothing(self):
        assert _assemble([], 1.0) == []


class TestWhatIsBuiltIsWoundRight:
    """Nothing this stage draws may disagree with the normal it was given.

    ⚠️ `signs.gdshader` is `cull_back`, so a violation renders as **nothing**.
    The signs' first build shipped 3,200 such triangles — every pole in the
    region — because the prism ring was wound the way a plate wants, and this
    stage reuses that prism.
    """

    def test_a_head_agrees_with_its_normals(self, spec):
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        for facing_deg in (0.0, 45.0, 180.0, 300.0):
            _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), facing_deg)
        mesh = builder.build("signals")

        assert mesh is not None
        assert facing_away(mesh) == 0

    def test_a_post_agrees_with_its_normals(self, spec):
        """The regression this test exists for, held explicitly."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_post(builder, spec, 4.0, -7.0, 0.0, 3.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert facing_away(mesh) == 0

    def test_a_post_starts_at_the_deck_it_stands_on(self, spec):
        """🔴 **The regression this test exists for, and it shipped.** The first
        build copied `signs._draw_pole` *without* its `base_y`, so every post ran
        from world y=0 up through the carriageway — 3 to 12 m too long, with
        `signals.json`'s AABB reading min-y 0.0 against the signs' 3.18.

        Nothing saw it. `facing_away` was 0, both partitions closed,
        `verify_signals` was green, and the extra length points *downward* where
        opaque asphalt hides it from any camera above the road."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_post(builder, spec, 0.0, 0.0, 6.5, 10.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.positions[:, 1].min() == pytest.approx(6.5)
        assert mesh.positions[:, 1].max() == pytest.approx(10.0)

    def test_a_post_faces_outward_rather_than_inward(self, spec):
        """`facing_away` alone would pass a post wound inward *and* labelled so.

        It asks whether winding and normal agree, not whether either is right."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_post(builder, spec, 0.0, 0.0, 0.0, 3.0)
        mesh = builder.build("signals")

        assert mesh is not None
        sides = np.abs(mesh.normals[:, 1]) < 0.5
        outward = (mesh.normals[sides, 0] * mesh.positions[sides, 0]) + (
            mesh.normals[sides, 2] * mesh.positions[sides, 2]
        )
        assert (outward > 0.0).all()

    def test_the_material_is_the_contract_name(self, spec):
        """The string `generated_scene_import.gd` dispatches the shader on.

        ⚠️ It is not `signs`, although the *shader* is shared: the material name
        is what selects `signals.tres`, and a head handed `signs.tres` would be
        a signal head lit as painted aluminium and would render perfectly."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_post(builder, spec, 0.0, 0.0, 0.0, 3.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.material == SIGNALS_MATERIAL

    def test_every_head_carries_vertex_colour(self, spec):
        """⚠️ The channel that makes one draw call carry four colours."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.colours is not None
        assert len(mesh.colours) == len(mesh.positions)


class TestTheHeadGeometry:
    def test_a_head_is_closed(self, spec):
        """Six faces, and the bottom is not optional: `mount_height_m` is 2.40,
        so the underside is what a driver stopped at the line looks up at.

        ⚠️ **This asserted only the two vertical normals until review caught
        it** — a head missing its back face passed. It counts the faces now."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        normals = {tuple(np.round(normal, 3)) for normal in mesh.normals}
        # Six box faces, all six distinct directions, plus the lens discs which
        # share the front normal — so six is the count of distinct box normals.
        assert (0.0, 1.0, 0.0) in normals, "no top"
        assert (0.0, -1.0, 0.0) in normals, "no bottom"
        # Facing 0 is north, so the outward normal is -Z and `right` is -X.
        assert (0.0, 0.0, -1.0) in normals, "no front"
        assert (0.0, 0.0, 1.0) in normals, "no back"
        assert (-1.0, 0.0, 0.0) in normals, "no left side"
        assert (1.0, 0.0, 0.0) in normals, "no right side"

    def test_a_head_sits_in_front_of_its_post(self, spec):
        """🔴 **The regression this test exists for.** The first build lifted
        `signs._draw_plate`'s `+ pole_radius_m * normal`, which is right for a
        plate one quad thick and wrong for a box with depth: 0.24 m of the
        0.30 m head sat on the far side of its own post, away from the traffic
        it addresses, and it rendered perfectly.

        The head's **back** must clear the post, so every part of the body lies
        at or beyond the post's front surface."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        front = np.array([0.0, 3.0, 0.0]) + (spec.post_radius_m + spec.head_depth_m) * np.array(
            [0.0, 0.0, -1.0]
        )
        _draw_head(builder, spec, front, 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        # Facing north, so "in front" is more negative z than the post surface.
        assert mesh.positions[:, 2].max() <= -spec.post_radius_m + 1e-9

    def test_every_aspect_is_drawn(self, spec):
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.colours is not None
        painted = {tuple(colour[:3]) for colour in mesh.colours}
        for name in spec.lens_colours:
            assert spec.colours[name] in painted

    def test_the_aspects_are_stacked_top_to_bottom_in_order(self, spec):
        """🔴 Red on top. Reversed, it is a working signal head giving the
        opposite instruction, and nothing in a frame says so."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.colours is not None
        heights = {}
        for position, colour in zip(mesh.positions, mesh.colours, strict=True):
            key = tuple(colour[:3])
            heights[key] = max(heights.get(key, -math.inf), position[1])
        ordered = [spec.colours[name] for name in spec.lens_colours]
        assert heights[ordered[0]] > heights[ordered[1]] > heights[ordered[2]]

    def test_the_aspects_sit_proud_of_the_face_they_are_on(self, spec):
        """Coplanar faces z-fight, which is what `lens_lift_m` is for."""
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.colours is not None
        lens = spec.colours[spec.lens_colours[0]]
        on_lens = np.array([tuple(c[:3]) == lens for c in mesh.colours])
        # Facing 0 degrees is north, so the outward normal is `-Z` and a lifted
        # lens sits at a *smaller* z than the face it is lifted off.
        assert mesh.positions[on_lens, 2].max() < 0.0

    @pytest.mark.parametrize(
        ("facing_deg", "normal"),
        [(0.0, (0.0, -1.0)), (90.0, (1.0, 0.0)), (180.0, (0.0, 1.0)), (270.0, (-1.0, 0.0))],
    )
    def test_a_head_faces_the_way_it_was_told_to(self, spec, facing_deg, normal):
        """🔴 **The whole failure class in one assertion.** A head turned 180
        degrees is a perfectly drawn head addressing traffic that cannot see it,
        and no counter but this catches it.

        The aspects are lifted along the head's outward normal, so where the
        lenses sit relative to the body *is* which way the head faces."""
        head_centre = np.array([0.0, 3.0, 0.0])
        builder = ColouredBuilder(SIGNALS_MATERIAL)
        _draw_head(builder, spec, head_centre, facing_deg)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.colours is not None
        lens = spec.colours[spec.lens_colours[0]]
        on_lens = np.array([tuple(colour[:3]) == lens for colour in mesh.colours])
        # Horizontal displacement of the aspect from the body it is mounted on.
        offset = mesh.positions[on_lens].mean(axis=0) - head_centre
        assert offset[0] == pytest.approx(spec.lens_lift_m * normal[0], abs=1e-9)
        assert offset[2] == pytest.approx(spec.lens_lift_m * normal[1], abs=1e-9)


class TestPostsThatRegistrationPushedTogether:
    """⚠️ **A second merge, over a different population from `_assemble`'s.**

    That one runs over *surveyed* positions and is the publisher's coincidence;
    this runs over *registered* ones and is this stage's own doing — every post
    on the same edge, side and `t` is pushed to the same offset.
    """

    def placed(self, x: float, z: float) -> _Placed:
        return _Placed(x=x, z=z, y=0.0, facing_deg=0.0, heads=[head(x, z)])

    def test_posts_pushed_onto_one_point_are_folded(self):
        report = SignalReport()

        kept = _merge_placements([self.placed(0.0, 0.0), self.placed(0.1, 0.0)], 1.0, report)

        assert len(kept) == 1
        assert len(kept[0].heads) == 2
        assert report.posts_merged_after_shift == 1

    def test_posts_that_stayed_apart_are_kept(self):
        report = SignalReport()

        kept = _merge_placements([self.placed(0.0, 0.0), self.placed(5.0, 0.0)], 1.0, report)

        assert len(kept) == 2
        assert report.posts_merged_after_shift == 0


class TestTheRegionsVocabulary:
    """The numbers `DECISIONS.md` `Q76` quotes, over Wan Chai's real codes.

    ⚠️ **Read against `BLOCK` rather than the shipped city file since `Q77`**,
    because Hong Kong no longer declares a `signals:` block — the layer was
    dropped from the bundle. The vocabulary below is still the region's real
    one, transcribed from `DTAD_TRAFFIC_LIGHT_PT`, so what this pins is the
    gate's behaviour on real input; it is no longer a claim about what ships.
    """

    def test_the_gate_refuses_exactly_the_non_head_vocabulary(self, spec):
        """Every code the gate turns away, and nothing else. 70 of the region's
        913 features."""
        # ⚠️ **The refused half of the region's vocabulary, complete, plus a
        # sample of the admitted half.** It is not the whole 46 — review caught
        # it being described as such — and it does not need to be: what is
        # asserted below is that every code the gate turns away is turned away,
        # which is the half no counter downstream can recover.
        vocabulary = {
            "P24": 278,
            "P01": 149,
            "S01": 100,
            "P21": 57,
            "P04R": 33,
            "P08R": 28,
            "P07L": 25,
            "S07L": 21,
            "P03L": 19,
            "S04R": 17,
            "P26": 17,
            "S08R": 13,
            "S10R": 9,
            "P22": 8,
            "P02": 8,
            "S03L": 8,
            "P06R": 7,
            "S02": 6,
            "S12L": 5,
            "P10R": 5,
            "P12L": 4,
            "P05L": 4,
            "S05L": 3,
            "P23": 3,
            "S11": 3,
            "KLBOLL": 24,
            "M52": 16,
            "PBUTT": 8,
            "PBOLL": 6,
            "WIGWAG": 4,
            "STR02": 3,
            "KRBOLL": 3,
            "TRAML": 1,
            "PTR01": 1,
            "PTR02": 1,
            "M51": 1,
            "M53L": 1,
            "M54R": 1,
        }
        admitted = {code: n for code, n in vocabulary.items() if spec.is_head(code)}
        refused = {code: n for code, n in vocabulary.items() if not spec.is_head(code)}

        assert sum(refused.values()) == 70
        assert set(refused) == {
            "KLBOLL",
            "KRBOLL",
            "PBUTT",
            "PBOLL",
            "WIGWAG",
            "STR02",
            "PTR01",
            "PTR02",
            "TRAML",
            "M51",
            "M52",
            "M53L",
            "M54R",
        }
        assert "P24" in admitted and "S07L" in admitted


class TestSignals:
    """The published-signal-head block (`P3-17`).

    🔴 **The gate is the weakest-evidenced rule in the bundle, so it is the most
    heavily tested thing here.** `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has no
    published domain — no index-plan sheet defines it, the fgdb specification
    gives the column eight characters of untyped text, and
    `hk-traffic-sign-map`'s catalogue is `TS`-only — so what admits a code is a
    rule about *spelling* that this project wrote. Nothing downstream can grade
    it: a head drawn on a push button renders as a perfectly good signal head.
    """

    def test_the_region_declares_signals(self, spec) -> None:
        assert spec is not None
        assert spec.layer.layer == "DTAD_TRAFFIC_LIGHT_PT"
        assert not spec.tiled

    def test_the_gate_admits_the_head_codes_the_region_publishes(self, spec) -> None:
        """Every one of these is a real `REFNAME` in Wan Chai, including the
        `L`/`R` filter-arrow suffixes."""

        for code in ("P24", "P01", "S01", "P21", "P04R", "P08R", "P07L", "S07L", "S04R"):
            assert spec.is_head(code), code

    def test_the_gate_refuses_the_objects_that_are_not_heads(self, spec) -> None:
        """⚠️ **The near misses are the point, and they refuse for three
        different reasons.** `KLBOLL`/`KRBOLL`/`WIGWAG`/`TRAML` never match a
        prefix; `PBUTT`/`PBOLL` match and leave letters; `PTR01`/`PTR02`/`STR02`
        leave **digits behind a letter**, which is the one a laxer rule would
        wave through. `PBOLL` and `TRAML` also end in `L`, so a suffix strip
        that ran before the digit test would admit them."""

        for code in ("KLBOLL", "KRBOLL", "PBUTT", "PBOLL", "WIGWAG", "STR02", "PTR01", "TRAML"):
            assert not spec.is_head(code), code

    def test_the_undecoded_m_family_is_refused(self, spec) -> None:
        """🔴 **A decision, not an oversight.** The region publishes `M52` x16,
        `M51`, `M53L` and `M54R`, every one within 2.57 m of a `P`/`S` head — so
        they are part of the signal assembly rather than strays. But part of the
        assembly is not *is a head*, nothing published settles which, and drawing
        them would be inventing 19 heads (`Q54`). Reversing it is one word in
        `head_prefixes`, and `refused_by_code` is where a reader sees them."""

        assert "M" not in spec.head_prefixes
        for code in ("M52", "M51", "M53L", "M54R"):
            assert not spec.is_head(code)

    def test_a_bare_prefix_is_not_a_head(self, spec) -> None:
        """A prefix with no number after it is not a code, and `P` + `L` is a
        suffix strip that leaves nothing to test."""

        assert not spec.is_head("P")
        assert not spec.is_head("PL")
        assert not spec.is_head("")

    def test_a_lower_case_prefix_is_rejected(self, tmp_path) -> None:
        """🔴 **The regression this pins, and it is this block's own failure
        class.** `REFNAME` is upper case throughout the layer and the gate does
        no case folding, so a city file writing `p` would load clean, pass every
        other test here, and ship **zero** signals — and a region that draws
        nothing is indistinguishable from a region that has none."""

        def lower(block: dict[str, Any]) -> None:
            block["head_prefixes"] = ["p", "s"]

        with pytest.raises(ValueError, match="upper-case ASCII"):
            mutated(tmp_path, lower)

    def test_a_prefix_carrying_a_digit_is_rejected(self, tmp_path) -> None:
        def numbered(block: dict[str, Any]) -> None:
            block["head_prefixes"] = ["P2"]

        with pytest.raises(ValueError, match="upper-case ASCII"):
            mutated(tmp_path, numbered)

    def test_refusing_a_code_the_prefix_rule_already_refuses_is_rejected(self, tmp_path) -> None:
        """Dead config that reads as a live decision: a reviewer sees a
        deliberate refusal where deleting the line would change nothing."""

        def restate(block: dict[str, Any]) -> None:
            block["refuse_codes"] = ["KLBOLL"]

        with pytest.raises(ValueError, match="already refuses"):
            mutated(tmp_path, restate)

    def test_refusing_a_code_the_prefix_rule_admits_is_accepted(self, tmp_path) -> None:
        """The escape hatch the field exists for: a publisher who numbers a push
        button `P90` gets a signal head out of the spelling rule, and this is the
        one word that stops it without a code change."""

        def hatch(block: dict[str, Any]) -> None:
            block["refuse_codes"] = ["P90"]

        spec = mutated(tmp_path, hatch).signals
        assert not spec.is_head("P90")
        assert spec.is_head("P24")

    def test_the_lens_livery_must_be_declared(self, tmp_path) -> None:
        """An unknown colour would otherwise fall back to something and render a
        plausible head in the wrong livery."""

        def stray(block: dict[str, Any]) -> None:
            block["lens_colours"] = ["lens_red", "lens_purple"]

        with pytest.raises(ValueError, match="lens_purple"):
            mutated(tmp_path, stray)

    def test_the_aspect_count_is_derived_from_the_livery(self, spec) -> None:
        """⚠️ One fact, not two. A `lens_count` authored beside a colour table is
        a way for them to disagree, and a head drawn with two lenses in three
        colours renders perfectly."""

        assert spec.lens_count == len(spec.lens_colours) == 3

    def test_lenses_that_overflow_their_own_head_are_rejected(self, tmp_path) -> None:
        def tall(block: dict[str, Any]) -> None:
            block["lens_diameter_m"] = 0.40

        with pytest.raises(ValueError, match="head_height_m"):
            mutated(tmp_path, tall)

    def test_a_lens_lifted_off_the_back_of_its_head_is_rejected(self, tmp_path) -> None:
        def floating(block: dict[str, Any]) -> None:
            block["lens_lift_m"] = 0.40

        with pytest.raises(ValueError, match="floats off the back"):
            mutated(tmp_path, floating)

    def test_an_ambiguity_radius_that_kills_its_own_counter_is_rejected(self, tmp_path) -> None:
        """`host_ambiguous` is report-only, so nothing renders differently — it
        just reads 100% forever, and the one instrument that can see the
        junction-mouth join go weak (`Q69`) stops saying anything."""

        def dead(block: dict[str, Any]) -> None:
            block["host_ambiguity_m"] = 25.0

        with pytest.raises(ValueError, match="counter would be dead"):
            mutated(tmp_path, dead)

    def test_a_non_finite_measurement_is_rejected(self, tmp_path) -> None:
        """⚠️ Why this block goes through `_measures`: YAML 1.1 resolves `.nan`,
        a NaN passes every sign test, and it then makes false every comparison it
        feeds downstream."""

        def nan(block: dict[str, Any]) -> None:
            block["mount_height_m"] = float("nan")

        with pytest.raises(ValueError, match="finite"):
            mutated(tmp_path, nan)

    def test_the_body_livery_is_required_by_name(self, tmp_path) -> None:
        """The one colour key `lens_colours` cannot vouch for. Without it the
        build dies partway through on a bare `KeyError`."""

        def renamed(block: dict[str, Any]) -> None:
            colours = block["colours"]
            colours["carcass"] = colours.pop("body")

        with pytest.raises(ValueError, match="does not name 'body'"):
            mutated(tmp_path, renamed)

    def test_a_city_without_signals_loads(self, tmp_path) -> None:
        """Optional on the same terms as `tramway`, `arrows`, `signs`,
        `boxjunctions` and `railings`: a city whose estate publishes no signal
        layer ships none rather than putting a signal at every junction node.

        🔴 **This is the state Hong Kong itself is in since `Q77`**, so it is the
        path the shipping city takes rather than a hypothetical one."""
        assert city_with(tmp_path, None).signals is None


class TestTheLayerStaysLatent:
    """🚫 `Q77` un-shipped this layer by removing its config block, and `Q100`
    kept the code on the user's instruction. This is the ratchet: re-declaring
    a `signals:` block is a deliberate act that fails here first, and the
    failure message says what has to be true before it may pass."""

    def test_the_shipped_config_declares_no_signals_block(self) -> None:
        assert load_config().signals is None, (
            "the config declares a signals: block again. Q77 dropped the layer "
            "because an unlit head asserts a signal out of service and nothing "
            "publishes coordination; bringing it back needs a real phase plan "
            "(B3) and a decision record superseding Q77"
        )
