"""The `P3-29` closure-barrier generator (`tools/make_barrier.py`).

Four kinds of test, three of them `test_make_landmark.py`'s and one this
layer's own.

**The committed-asset guard.** The `.glb` is build output that is *committed*,
and `tools/check.sh` does not know this tool exists. Regenerating and comparing
bytes is what catches "edited the generator, forgot to re-run".

**The contract the game imports on.** `generated_scene_import.gd` branches on
the glTF material name, and the `-col` node-name suffix is what buys a
collider. None of that is visible in a render; all of it is checkable here.

**The palette rule.** Every colour claims `reflectance x exposure_anchor`
(`Q33`/`Q38`) exactly as the city's materials table does, held to the same
tolerance by the same shared body.

🔴 **And the one this layer does not share: the collider must be there.** Every
other thing named "barrier" in this repo is the *generated* railing class,
which `verify_railings.gd` asserts has **no** collision. This prop asserts the
opposite, because `Q19` forbids an invisible refusal and a barrier the car
drives through is one. A test that only inherited the family's rule would
enforce exactly the wrong thing here.
"""

from __future__ import annotations

from pathlib import Path

import make_barrier
import pytest
from make_barrier import (
    MATERIAL,
    PALETTE,
    UNIT_WIDTH_M,
    Barrier,
    build_barrier,
    build_barriers,
    check_palette,
    write_barriers,
)

from pipeline.buildings import COLLISION_SUFFIX
from pipeline.config import Material, load_config
from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
SHIPPED = ROOT / "game" / "assets" / "authored" / "barriers"

# A prop standing at 14 mouths, several units to a mouth. It is furniture seen
# from a stopping car, not a hero: the budget is what stops "legible at speed"
# turning into a modelled crash barrier with bolt heads.
TRIANGLE_BUDGET = 600

# `make_vehicle.py` records why: Godot's importer converts node names ending in
# these into physics nodes, silently. `-col` is the one suffix this *wants*.
FORBIDDEN_SUFFIXES = ("_wheel", "_convcol", "_navmesh", "_occ", "_rigid", "_vehicle")


@pytest.fixture(scope="module")
def barriers() -> list[tuple[str, MeshData]]:
    return build_barriers()


class TestShippedAssets:
    """The `.glb` is committed, and nothing else in the build checks it."""

    def test_the_committed_file_matches_the_generator(self, tmp_path: Path) -> None:
        written = write_barriers(tmp_path)
        assert written, "the generator produced nothing at all"
        for path, _, _ in written:
            shipped = SHIPPED / path.name
            assert shipped.exists(), f"{shipped.name} is not committed"
            assert shipped.read_bytes() == path.read_bytes(), (
                f"{shipped.name} is stale — re-run tools/make_barrier.py"
            )


class TestImportContract:
    """What `generated_scene_import.gd` and Godot's importer read."""

    def test_the_node_name_asks_for_a_collider(self, barriers) -> None:
        """🔴 The inversion of the railing family's rule, and the point of the
        prop. `write_glb` writes the mesh name as the node name, which is where
        the importer looks; without the suffix this is a barrier the car drives
        straight through, which renders perfectly and refuses nothing."""
        for _, mesh in barriers:
            assert mesh.name.endswith(COLLISION_SUFFIX)

    def test_the_suffix_is_hyphenated(self, barriers) -> None:
        """`-col` buys a static trimesh collider; `_col` is a different suffix
        in the same silent family as the ones below."""
        for _, mesh in barriers:
            assert not mesh.name.endswith("_col")

    def test_no_name_trips_another_importer_suffix(self, barriers) -> None:
        for _, mesh in barriers:
            stem = mesh.name.removesuffix(COLLISION_SUFFIX)
            for suffix in FORBIDDEN_SUFFIXES:
                assert not stem.endswith(suffix), f"{mesh.name} would import as a physics node"

    def test_the_material_is_not_the_generated_railing_class(self) -> None:
        """⚠️ `barriers` is already taken — it dispatches the *generated* railing
        class to `tuning/barriers.tres`, which `verify_railings.gd` requires to
        have no collision. Sharing the name would hand this prop a fence's
        shader and fail that tool, and both halves would render."""
        assert MATERIAL != "barriers"
        assert MATERIAL == "barrier_vertex"

    def test_the_mesh_carries_vertex_colours_and_no_texture(self, barriers) -> None:
        """The vertex-colour fallback branch is the one this takes, exactly as
        the authored landmark does — so `COLOR_0` is the whole of its look."""
        for _, mesh in barriers:
            assert mesh.colours is not None
            assert mesh.texture is None
            assert mesh.uvs is None

    def test_it_stays_inside_the_triangle_budget(self, barriers) -> None:
        for _, mesh in barriers:
            assert mesh.triangle_count <= TRIANGLE_BUDGET


class TestAuthoredFrame:
    """Where the prop sits relative to its own origin — `fence.json`'s contract."""

    def test_it_is_centred_on_x_and_stands_on_y_zero(self, barriers) -> None:
        """`fence.json` carries a position and a direction and the runtime applies
        them, so an off-centre prop puts every barrier in the region off-centre
        by the same amount — a defect that reads as a placement bug forever."""
        for _, mesh in barriers:
            low, high = mesh.aabb()
            assert low[0] == pytest.approx(-0.5 * UNIT_WIDTH_M)
            assert high[0] == pytest.approx(0.5 * UNIT_WIDTH_M)
            assert high[1] == pytest.approx(Barrier().height_m)

    def test_it_continues_below_the_road(self, barriers) -> None:
        """±0.1 m of disagreement with the ribbon has to read as a barrier
        standing on tarmac rather than one floating over it —
        `make_landmark.py`'s plinth at the scale of a post."""
        for _, mesh in barriers:
            assert mesh.aabb()[0][1] < 0.0

    def test_it_is_thin_in_z_so_it_reads_as_a_barrier_across_the_road(self, barriers) -> None:
        """A prop as deep as it is wide is a block, not a barrier."""
        for _, mesh in barriers:
            low, high = mesh.aabb()
            assert (high[2] - low[2]) < 0.25 * (high[0] - low[0])

    def test_the_prop_has_no_front_so_the_facing_cannot_be_backwards(self, barriers) -> None:
        """🔴 The trap the first asymmetric detail added here would inherit.

        `Basis.looking_at` — via `RoadSpawn.basis_facing` — puts a model's **-Z**
        on the target, which is Godot's forward. A prop authored with a front on
        +Z would therefore stand backwards at every mouth in the region *and
        render perfectly*, which is `Q62`'s class of defect exactly. This prop
        has no front: it is mirror-symmetric about `z = 0`, so the question does
        not arise. Add a chevron, a plate or a lamp and this fails, which is the
        moment to author the front at -Z rather than to relax the test.

        ⚠️ Thinness cannot stand in for this — a thin prop can still be
        asymmetric, and the previous test asserted only that."""
        for _, mesh in barriers:
            mirrored = mesh.positions.copy()
            mirrored[:, 2] *= -1.0
            front = {tuple(round(float(v), 6) for v in row) for row in mesh.positions}
            back = {tuple(round(float(v), 6) for v in row) for row in mirrored}
            assert front == back, "the prop has a front, so it must be authored facing -Z"


class TestWidth:
    def test_a_barrier_narrower_than_its_posts_is_refused(self) -> None:
        """Clamping would emit the two posts crossed, and a mesh that renders as
        a knot is exactly the class of defect this layer exists to stop being
        invisible."""
        with pytest.raises(ValueError, match="cannot carry posts"):
            build_barrier(0.5)

    def test_the_banding_survives_every_width(self) -> None:
        """The pattern is counted, not pitched, so a unit keeps its bands
        whatever width it is asked for — which is what lets the row span a mouth
        without the prop being scaled."""
        for width in (1.0, UNIT_WIDTH_M, 4.0):
            mesh = build_barrier(width)
            assert mesh.triangle_count == build_barrier(UNIT_WIDTH_M).triangle_count
            low, high = mesh.aabb()
            assert (high[0] - low[0]) == pytest.approx(width)


class TestPalette:
    """`Q33`'s rule, on colours the ETL never sees."""

    def test_the_shipped_palette_holds_against_the_live_anchor(self) -> None:
        check_palette(load_config().exposure_anchor)

    def test_a_colour_that_lies_about_its_reflectance_is_refused(self) -> None:
        """The check is what makes the palette a claim rather than a preference,
        and `Q38` is why the anchor is read live: move it and this generator
        stops, loudly, instead of shipping a prop lit for another exposure."""
        wrong = Material("barrier_white", (255, 255, 255), 62.0, "pure white")
        original = make_barrier.PALETTE
        make_barrier.PALETTE = (wrong,)
        try:
            with pytest.raises(ValueError, match="barrier_white"):
                check_palette(load_config().exposure_anchor)
        finally:
            make_barrier.PALETTE = original

    def test_every_declared_colour_is_actually_used(self, barriers) -> None:
        """A palette entry nothing draws passes every check above and ships
        nothing — the inert-config failure `_thresholds` refuses elsewhere."""
        drawn = {
            tuple(int(channel) for channel in row[:3])
            for _, mesh in barriers
            for row in mesh.colours
        }
        for surface in PALETTE:
            assert surface.colour in drawn, f"{surface.name} is declared and never drawn"
