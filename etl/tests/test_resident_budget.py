"""`tools/resident_budget.py` (`P5-18`, `Q122`): resident triangles at the worst
camera, banded the way `CityStreamer` bands — by plan distance to the published
`aabb`, not to its centre.

The second half is the point. `Q120`'s 108% was computed by distance to the tile
centre, which a 150 m tile makes 75 m more generous than the engine on every
side; under the engine's own rule the same bundle reads 184%. The test that
pins that is not a number from a region — it is the shape: a box the camera is
inside is at distance 0 whatever its centre reads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest
from resident_budget import (
    DISTANCE_RULES,
    Bundle,
    Profile,
    Unit,
    band_of,
    centre_distance_to,
    load_bundle,
    lod_ratio,
    main,
    plan_distance_to,
    resident_at,
    worst_camera,
)

from pipeline.buildings import BUILDINGS_MANIFEST_SCHEMA
from pipeline.surface import SURFACE_MANIFEST_SCHEMA

ENGINE = Profile(250.0, 400.0, DISTANCE_RULES["aabb"])
CENTRE = Profile(250.0, 400.0, DISTANCE_RULES["centre"])

BOX = ((0.0, 0.0, 0.0), (150.0, 40.0, 150.0))


class TestPlanDistance:
    def test_inside_the_box_is_zero_whatever_the_centre_reads(self) -> None:
        # 100 m from the centre and still inside: the engine loads it at LOD0.
        assert plan_distance_to(BOX, 5.0, 5.0) == 0.0

    def test_outside_is_the_distance_to_the_nearest_face_in_plan(self) -> None:
        assert plan_distance_to(BOX, 250.0, 75.0) == pytest.approx(100.0)
        assert plan_distance_to(BOX, 250.0, 250.0) == pytest.approx((100.0**2 * 2) ** 0.5)

    def test_height_is_ignored(self) -> None:
        assert plan_distance_to(BOX, 75.0, 75.0) == 0.0


class TestBand:
    def test_the_bands_are_the_streamer_s(self) -> None:
        assert band_of(0.0, 250.0, 400.0) == 0
        assert band_of(250.0, 250.0, 400.0) == 0
        assert band_of(250.1, 250.0, 400.0) == 1
        assert band_of(400.0, 250.0, 400.0) == 1
        assert band_of(400.1, 250.0, 400.0) is None


def _tile(name: str, ix: int, iz: int, tiers: tuple[int, ...]) -> Unit:
    return Unit(
        id=name,
        aabb=((ix * 150.0, 0.0, iz * 150.0), ((ix + 1) * 150.0, 40.0, (iz + 1) * 150.0)),
        tiers=tiers,
        is_road=False,
    )


class TestResident:
    units: ClassVar[list[Unit]] = [
        _tile("t_00_00", 0, 0, (1000, 400)),
        _tile("t_02_00", 2, 0, (1000, 400)),  # 150 m past the first: LOD0 from (75, 75)
        _tile("t_03_00", 3, 0, (1000, 400)),  # 300 m: LOD1
        _tile("t_04_00", 4, 0, (1000, 400)),  # 450 m: unloaded
        Unit("r_00_00", ((0.0, 0.0, 0.0), (150.0, 5.0, 150.0)), (200,), is_road=True),
        Unit("r_04_00", ((600.0, 0.0, 0.0), (750.0, 5.0, 150.0)), (200,), is_road=True),
    ]

    def test_a_camera_sums_the_resident_tier_of_each_unit(self) -> None:
        camera = resident_at(self.units, 75.0, 75.0, ENGINE)
        assert camera.buildings == 1000 + 1000 + 400
        assert camera.tiles_by_tier == (2, 1)
        assert camera.triangles_by_tier == (2000, 400)
        assert camera.resident_road == 200

    def test_the_engine_s_rule_differs_from_q120_s_centre_rule(self) -> None:
        """A tile whose centre is 300 m off but whose near face is 225 m off is
        LOD0 to the engine and LOD1 to a centre rule — the whole of the gap
        between `Q120`'s 108% and this tool's 184% on one tile."""
        far_edge = _tile("t_02_00", 2, 0, (1000, 400))
        assert plan_distance_to(far_edge.aabb, 75.0, 75.0) == 225.0
        assert centre_distance_to(far_edge.aabb, 75.0, 75.0) == 300.0
        # Q120's rule: t_02_00 falls to LOD1 (400) and t_03_00's centre, 450 m off,
        # is past the unload distance the engine still holds it inside.
        by_centre = resident_at(self.units, 75.0, 75.0, CENTRE)
        assert by_centre.buildings == 1000 + 400
        assert by_centre.buildings < resident_at(self.units, 75.0, 75.0, ENGINE).buildings

    def test_worst_camera_is_the_heaviest_not_the_average(self) -> None:
        # From (1500, 75) nothing is within 400 m; from (675, 75) three tiles are LOD0.
        points = [(75.0, 75.0), (675.0, 75.0), (1500.0, 75.0)]
        bundle = Bundle(units=self.units, cameras=points, whole_road=0, lod1_cell_m=None)
        worst = worst_camera(bundle, ENGINE)
        assert (worst.x, worst.z) == (675.0, 75.0)
        assert worst.buildings == 3000
        assert resident_at(self.units, 1500.0, 75.0, ENGINE).buildings == 0

    def test_lod_ratio_reads_the_coarsest_over_the_finest(self) -> None:
        assert lod_ratio(self.units) == pytest.approx(0.4)


def _bundle(root: Path) -> Path:
    region = root / "wan_chai"
    region.mkdir(parents=True)
    (region / "buildings.json").write_text(
        json.dumps(
            {
                "schema_version": BUILDINGS_MANIFEST_SCHEMA,
                "tile_size_m": 150.0,
                "lod_cell_sizes_m": [1.5, 4.0],
                "tiles": [
                    {
                        "id": "t_00_00",
                        "ix": 0,
                        "iz": 0,
                        "aabb": [[0.0, 0.0, 0.0], [150.0, 40.0, 150.0]],
                        "lods": [{"triangles": 1000}, {"triangles": 400}],
                    },
                    {
                        "id": "t_03_00",
                        "ix": 3,
                        "iz": 0,
                        "aabb": [[450.0, 0.0, 0.0], [600.0, 40.0, 150.0]],
                        "lods": [{"triangles": 500}, {"triangles": 200}],
                    },
                ],
            }
        )
    )
    (region / "roadsurface.json").write_text(
        json.dumps(
            {
                "schema_version": SURFACE_MANIFEST_SCHEMA,
                "triangles": 300,
                "chunks": [
                    {"id": "t_00_00", "triangles": 100, "aabb": [[0, 0, 0], [150, 5, 150]]},
                    {"id": "t_03_00", "triangles": 200, "aabb": [[450, 0, 0], [600, 5, 150]]},
                ],
            }
        )
    )
    return root


class TestBundle:
    def test_units_and_cameras_come_from_the_manifests(self, tmp_path: Path) -> None:
        root = _bundle(tmp_path)
        bundle = load_bundle(root / "wan_chai", "wan_chai")
        assert bundle.whole_road == 300 and bundle.lod1_cell_m == 4.0
        assert [unit.id for unit in bundle.units] == ["t_00_00", "t_03_00", "t_00_00", "t_03_00"]
        assert bundle.cameras == [(75.0, 75.0), (525.0, 75.0)]

    def test_a_stale_manifest_is_refused_with_the_rebuild_command(self, tmp_path: Path) -> None:
        root = _bundle(tmp_path)
        path = root / "wan_chai" / "buildings.json"
        document = json.loads(path.read_text())
        document["schema_version"] = BUILDINGS_MANIFEST_SCHEMA + 1
        path.write_text(json.dumps(document))
        with pytest.raises(ValueError, match="pipeline --region wan_chai"):
            load_bundle(root / "wan_chai", "wan_chai")

    def test_main_prints_both_road_figures_and_the_sweep(self, tmp_path: Path, capsys) -> None:
        root = _bundle(tmp_path)
        assert main(["--region", "wan_chai", "--out-root", str(root), "--sweep"]) == 0
        out = capsys.readouterr().out
        # From (75, 75): t_00_00 at LOD0 (1000), t_03_00 at 300 m → LOD1 (200).
        assert "1,200 building triangles resident over 1 LOD0 + 1 LOD1 tiles" in out
        assert "of which LOD0 tiles 1,000 (83%) and LOD1 tiles 200" in out
        assert "+ whole road 300 = 1,500" in out
        assert "+ resident road 300 = 1,500" in out
        assert "L1/L0 triangle ratio 0.40 at a 4.0 m LOD1 cell" in out
        assert "| 250 / 400 m |" in out and "| 120 / 250 m |" in out
        assert "the engine's aabb rule" in out

    def test_band_by_centre_is_labelled_as_not_the_engine_s(self, tmp_path: Path, capsys) -> None:
        root = _bundle(tmp_path)
        assert main(["--region", "wan_chai", "--out-root", str(root), "--band-by", "centre"]) == 0
        out = capsys.readouterr().out
        assert "NOT the engine's" in out
        # From (75, 75) by centre: t_00_00 at 0 m (1000); t_03_00's centre at 450 m, unloaded.
        assert "1,000 building triangles resident over 1 LOD0 + 0 LOD1 tiles" in out

    def test_a_lod0_distance_past_the_unload_distance_is_refused(self, tmp_path: Path) -> None:
        root = _bundle(tmp_path)
        with pytest.raises(SystemExit):
            main(["--region", "wan_chai", "--out-root", str(root), "--lod0-m", "500"])
