"""`pipeline/signals.py` — the published signal heads (`P3-17`).

⚠️ **Every failure this stage has renders as a perfectly drawn signal head, or
as nothing at all.** A head turned 180 degrees is a good head facing the wrong
way; a gate that started admitting push buttons draws good heads on them; a
prism wound inward vanishes entirely under `cull_back`. So what is asserted here
is the arithmetic nothing downstream can see — the winding, the derived
grouping, and the partitions that have to close.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import load_city
from pipeline.railings import facing_away
from pipeline.signals import (
    SIGNALS_MATERIAL,
    Signal,
    SignalReport,
    _assemble,
    _Builder,
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
    return load_city("testville", cities_root=cities)


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).signals


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
        builder = _Builder()
        for facing_deg in (0.0, 45.0, 180.0, 300.0):
            _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), facing_deg)
        mesh = builder.build("signals")

        assert mesh is not None
        assert facing_away(mesh) == 0

    def test_a_post_agrees_with_its_normals(self, spec):
        """The regression this test exists for, held explicitly."""
        builder = _Builder()
        _draw_post(builder, spec, 4.0, -7.0, 3.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert facing_away(mesh) == 0

    def test_a_post_faces_outward_rather_than_inward(self, spec):
        """`facing_away` alone would pass a post wound inward *and* labelled so.

        It asks whether winding and normal agree, not whether either is right."""
        builder = _Builder()
        _draw_post(builder, spec, 0.0, 0.0, 3.0)
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
        builder = _Builder()
        _draw_post(builder, spec, 0.0, 0.0, 3.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.material == SIGNALS_MATERIAL

    def test_every_head_carries_vertex_colour(self, spec):
        """⚠️ The channel that makes one draw call carry four colours."""
        builder = _Builder()
        _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        assert mesh.colours is not None
        assert len(mesh.colours) == len(mesh.positions)


class TestTheHeadGeometry:
    def test_a_head_is_closed(self, spec):
        """Six faces, and the bottom is not optional: `mount_height_m` is 2.40,
        so the underside is what a driver stopped at the line looks up at."""
        builder = _Builder()
        _draw_head(builder, spec, np.array([0.0, 3.0, 0.0]), 0.0)
        mesh = builder.build("signals")

        assert mesh is not None
        normals = {tuple(np.round(normal, 3)) for normal in mesh.normals}
        # Up and down both present, and four sideways.
        assert (0.0, 1.0, 0.0) in normals
        assert (0.0, -1.0, 0.0) in normals

    def test_every_aspect_is_drawn(self, spec):
        builder = _Builder()
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
        builder = _Builder()
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
        builder = _Builder()
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
        builder = _Builder()
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


class TestTheShippedRegionReproduces:
    """The numbers `DECISIONS.md` `Q76` and the city file quote.

    ⚠️ **Read against the shipped `hong_kong.yaml`, not a fixture** — these are
    claims about what the gate does to the real vocabulary, and a fixture would
    let the two drift.
    """

    def test_the_gate_admits_the_measured_share(self, hong_kong):
        """843 of the region's 913 features, over 33 of its 46 codes. A change
        here is a change to what ships, and it should be deliberate."""
        spec = hong_kong.signals
        # The region's own vocabulary, transcribed from the layer.
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
