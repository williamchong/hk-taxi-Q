"""The `P3-6` landmark generator (`tools/make_landmark.py`).

Three kinds of test.

**The committed-asset guard.** The `.glb`s are build output that is *committed*,
and `tools/check.sh` does not know this tool exists. Regenerating and comparing
bytes is what catches "edited the generator, forgot to re-run" — the same guard
`test_make_vehicle.py` carries, for the same reason.

**The contract the game imports on.** `generated_scene_import.gd` branches on
the glTF material name, the `-col` node-name suffix is what buys a collider
(and the excluded source building took its tile collision with it), and Godot's
importer converts other suffixes into physics nodes silently. None of that is
visible in a render; all of it is checkable here.

**The palette rule.** Every colour a hero ships **is** a real material's diffuse
albedo, inside the range its own source names (`Q33`, un-baked by `P5-28c`),
exactly as the city's materials table is — but these colours cannot live in that
table, because a committed `.glb` never passes through the ETL. `check_palette`
is the enforcement, on the same shared body `_check_reflectance` applies to the
YAML. ⚠️ **It reads no anchor any more**, so these tests no longer load the city
config to run: the exposure is the lighting rig's (`Q38`) and a hero's colour
says nothing about it.
"""

from __future__ import annotations

from pathlib import Path

import make_landmark
import numpy as np
import pytest
from make_landmark import (
    MATERIAL,
    PALETTE,
    build_landmarks,
    check_palette,
    write_landmarks,
)

from pipeline.buildings import COLLISION_SUFFIX
from pipeline.config import Material
from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
SHIPPED = ROOT / "game" / "assets" / "authored" / "landmarks"

# ART_DESIGN.md's hero budget: 3-8k triangles each — silhouette landmarks seen
# at distance and speed, not hero props.
TRIANGLE_BUDGET = 8000

# `make_vehicle.py` records why: Godot's importer converts node names ending in
# these into physics nodes, silently. `-col` is the one suffix a hero *wants*.
FORBIDDEN_SUFFIXES = ("_wheel", "_convcol", "_navmesh", "_occ", "_rigid", "_vehicle")


@pytest.fixture(scope="module")
def landmarks() -> list[tuple[str, MeshData]]:
    return build_landmarks()


class TestShippedAssets:
    """The `.glb`s are committed, and nothing else in the build checks them."""

    def test_the_committed_files_match_the_generator(self, tmp_path: Path) -> None:
        written = write_landmarks(tmp_path)
        assert written, "the generator produced nothing at all"
        for path, _, _ in written:
            shipped = SHIPPED / path.name
            assert shipped.exists(), f"{shipped.name} is not committed"
            assert shipped.read_bytes() == path.read_bytes(), (
                f"{shipped.name} is stale — re-run tools/make_landmark.py"
            )


class TestImportContract:
    """What Godot's importer reads out of the file, not what it looks like."""

    def test_every_hero_fits_the_triangle_budget(self, landmarks) -> None:
        assert landmarks, "no heroes generated"
        for filename, mesh in landmarks:
            assert 0 < mesh.triangle_count <= TRIANGLE_BUDGET, (
                f"{filename}: {mesh.triangle_count} triangles against {TRIANGLE_BUDGET}"
            )

    def test_every_hero_is_its_own_collider(self, landmarks) -> None:
        for filename, mesh in landmarks:
            assert mesh.name.endswith(COLLISION_SUFFIX), (
                f"{filename}: node '{mesh.name}' has no -col suffix, so the taxi "
                "drives through the one building the tile mesh no longer covers"
            )

    def test_no_node_name_ends_in_an_importer_trap(self, landmarks) -> None:
        for filename, mesh in landmarks:
            hits = [s for s in FORBIDDEN_SUFFIXES if mesh.name.endswith(s)]
            assert not hits, f"{filename}: '{mesh.name}' ends in {hits[0]}"

    def test_the_material_is_the_landmark_contract_not_the_tile_one(self, landmarks) -> None:
        for filename, mesh in landmarks:
            assert mesh.material == MATERIAL, (
                f"{filename}: material {mesh.material!r} — `city_facade` would take "
                "the tile shader without its TEXCOORD payloads, anything else "
                f"unnamed loses the vertex-colour import path; it must be {MATERIAL!r}"
            )

    def test_colour_is_authored_and_shader_payloads_are_not(self, landmarks) -> None:
        for filename, mesh in landmarks:
            assert mesh.colours is not None, f"{filename}: no COLOR_0"
            assert mesh.uvs is None, f"{filename}: TEXCOORD_0 is the tile shader's channel"
            assert mesh.uv2 is None, f"{filename}: TEXCOORD_1 is the tile shader's channel"
            assert mesh.texture is None, f"{filename}: heroes are vertex-coloured (P3-6)"

    def test_geometry_is_authored_at_the_origin(self, landmarks) -> None:
        """`landmarks.json` carries the position; the mesh must not smuggle one."""
        for filename, mesh in landmarks:
            low, high = mesh.aabb()
            centre = (np.asarray(low) + np.asarray(high)) / 2.0
            assert abs(centre[0]) < 20.0, f"{filename}: x centre {centre[0]:.1f}"
            assert low[1] == pytest.approx(-1.0), (
                f"{filename}: base at y {low[1]:.2f} — the plinth continues 1 m "
                "below the base level the authored position carries"
            )


class TestPalette:
    """`Q33` for the colours the ETL never sees."""

    def test_the_shipped_palette_holds(self) -> None:
        check_palette()

    def test_the_check_can_fail(self, monkeypatch) -> None:
        """A guard written in the same round as its subject must show it can
        refuse — `P3-11`'s lesson about filtered-set tests, applied to a check.

        ⚠️ **This used to pass a wrong anchor and there is none to pass**, so it
        mutates the palette instead — which is the stronger form: it names the
        entry, and it exercises the body these colours actually go through.
        """
        wrong = Material("aluminium_roof", (255, 255, 255), 55.0, "pure white", (50.0, 60.0))
        monkeypatch.setattr(make_landmark, "PALETTE", (wrong,))
        with pytest.raises(ValueError, match="aluminium_roof"):
            check_palette()

    def test_a_reflectance_outside_its_own_bounds_is_refused(self, monkeypatch) -> None:
        """🔴 **The half the round trip cannot see** (`P5-28c`). Un-baked, a
        colour *is* its reflectance, so an honest author who moves both together
        defeats the comparison entirely. `bounds` is what is left, and a
        generator palette needs it for the same reason the YAML does."""
        lighter = Material("curtain_glass", (168, 179, 190), 45.0, "glass, 8-15%", (8.0, 15.0))
        monkeypatch.setattr(make_landmark, "PALETTE", (lighter,))
        with pytest.raises(ValueError, match=r"outside the 8\.0-15\.0%"):
            check_palette()

    def test_every_surface_names_a_source(self) -> None:
        for surface in PALETTE:
            assert surface.source.strip(), f"{surface.name}: an unsourced albedo"

    def test_every_declared_surface_is_registered(self) -> None:
        """A surface added and not appended to PALETTE would be silently exempt
        from `check_palette` — the filtered set that quietly matches nothing."""
        declared = [value for value in vars(make_landmark).values() if isinstance(value, Material)]
        assert declared, "no surfaces declared at module level at all"
        for surface in declared:
            assert surface in PALETTE, f"{surface.name} is not in PALETTE"
