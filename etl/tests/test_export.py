"""Manifest assembly and cross-document validation (`P1-6`).

The assembly half is small enough to check by reading the output, so most of
this exercises `validate` — and it does so by building a *good* set first and
then breaking one thing, because that is how the failures actually happen. Each
one is a real sequence: re-run the road stage and every `nearest_edge` written
before it names a different street; build one region over another's output and
every document is individually fine.

`__main__` is tested with the stage table stubbed out. What is worth pinning
there is the ordering and the stop-on-failure, not that the stages work — they
have their own tests, and running them for real would make this the slowest
file in the suite by three orders of magnitude.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import ClassVar

import pytest

from pipeline import __main__ as orchestrator
from pipeline.arrows import ARROWS_MANIFEST_NAME, ARROWS_MANIFEST_SCHEMA
from pipeline.boxjunctions import BOXJUNCTIONS_MANIFEST_NAME, BOXJUNCTIONS_MANIFEST_SCHEMA
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA
from pipeline.clearance import CLEARANCE_NAME, CLEARANCE_SCHEMA
from pipeline.config import Landmark, Material, SourcePaint
from pipeline.export import (
    CITY_NAME,
    CITY_SCHEMA,
    LANDMARKS_NAME,
    LANDMARKS_SCHEMA,
    build_region,
    read_manifest,
    shipped,
    validate,
)
from pipeline.fares import FARES_NAME, FARES_SCHEMA
from pipeline.landmarks import ASSETS_NAME, ASSETS_SCHEMA
from pipeline.railings import RAILINGS_MANIFEST_NAME, RAILINGS_MANIFEST_SCHEMA
from pipeline.roadmarks import ROADMARKS_MANIFEST_NAME, ROADMARKS_MANIFEST_SCHEMA
from pipeline.roads import ROADGRAPH_NAME, ROADGRAPH_SCHEMA
from pipeline.signs import SIGNS_MANIFEST_NAME, SIGNS_MANIFEST_SCHEMA
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, SURFACE_NAME
from pipeline.tramway import TRAMWAY_MANIFEST_NAME, TRAMWAY_MANIFEST_SCHEMA

REGION = "middle"

# A fixed stamp, so two builds of the same inputs are byte-identical and a diff
# between them means something. `generated_utc` is the only field that would
# otherwise change on every run.
STAMP = "2026-07-31T00:00:00Z"

_EDGE_ID = 40


class _Region:
    """A complete, valid set of stage outputs, ready to be broken.

    Documents live in memory and are rewritten by `save`, so a test can reach
    into one, change a single field, and rebuild or revalidate around it.
    """

    def __init__(self, city, out_root: Path) -> None:
        self.city = city
        self.out_root = out_root
        self.out_dir = city.out_dir(REGION, out_root)
        (self.out_dir / "tiles").mkdir(parents=True)

        # The second tile deliberately reaches past the region's east edge, the
        # way a building assigned to a tile whole overhangs it. `bounds_game`
        # has to cover it — see `test_bounds_cover_content_past_the_region`.
        self.far_x = city.region_high(REGION)[0] + 40.0
        self.documents: dict[str, dict] = {
            BUILDINGS_MANIFEST_NAME: {
                "schema_version": BUILDINGS_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "tile_size_m": 150.0,
                "grid": {"columns": 2, "rows": 1},
                "lod_cell_sizes_m": [0.0, 1.5],
                "tiles": [
                    {
                        "id": "t_00_00",
                        "ix": 0,
                        "iz": 0,
                        "aabb": [[0.0, 0.0, 0.0], [150.0, 40.0, 150.0]],
                        "lods": [
                            {"path": "tiles/t_00_00_lod0.glb", "triangles": 12, "bytes": 3},
                            {"path": "tiles/t_00_00_lod1.glb", "triangles": 6, "bytes": 3},
                        ],
                    },
                    {
                        "id": "t_01_00",
                        "ix": 1,
                        "iz": 0,
                        "aabb": [[150.0, 0.0, 0.0], [self.far_x, 90.0, 150.0]],
                        "lods": [{"path": "tiles/t_01_00_lod0.glb", "triangles": 12, "bytes": 3}],
                    },
                ],
            },
            SURFACE_MANIFEST_NAME: {
                "schema_version": SURFACE_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "mesh": SURFACE_NAME,
                "mesh_name": "road_surface-col",
                "triangles": 24,
                "vertices": 48,
                "bytes": 3,
                "aabb": [[-4.0, -1.0, -4.0], [204.0, 2.0, 104.0]],
                # The drawn half-width per edge, which `export.py` carries into
                # `city.json` so the game can place a car in the nearside lane.
                "carriageway": [
                    {"edge": _EDGE_ID, "half_width_m": [5.12, 5.12], "trim_m": [0.0, 0.0]},
                    {"edge": _EDGE_ID + 1, "half_width_m": [5.12, 5.12], "trim_m": [0.0, 0.0]},
                ],
            },
            CLEARANCE_NAME: {
                "schema_version": CLEARANCE_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "bumper_band_m": [0.3, 2.0],
                "resolution_m": 0.25,
                # One clear width per station, alongside the drawn half-width
                # above. `export.py` joins the two; neither stage could have
                # measured both.
                "clearance": [
                    {"edge": _EDGE_ID, "clear_width_m": [10.24, 10.24]},
                    {"edge": _EDGE_ID + 1, "clear_width_m": [10.24, 2.0]},
                ],
            },
            ROADGRAPH_NAME: {
                "schema_version": ROADGRAPH_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "nodes": [
                    {"id": 0, "pos": [0.0, 0.0, 0.0], "kind": "endpoint"},
                    {"id": 1, "pos": [100.0, 0.0, 0.0], "kind": "junction"},
                    {"id": 2, "pos": [200.0, 0.0, 100.0], "kind": "endpoint"},
                ],
                "edges": [
                    # `elevation_level` is written here because `roads.py` writes
                    # it on every real edge and `_check_fares` reads it strictly.
                    # The fixture omitted it until `Q15`, which is not a shape any
                    # published roadgraph has.
                    {
                        "id": _EDGE_ID,
                        "from": 0,
                        "to": 1,
                        "polyline": [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]],
                        "elevation_level": 0,
                    },
                    {
                        "id": _EDGE_ID + 1,
                        "from": 1,
                        "to": 2,
                        "polyline": [[100.0, 0.0, 0.0], [200.0, 0.0, 100.0]],
                        "elevation_level": 0,
                    },
                ],
                "turn_restrictions": [
                    {"from_edge": _EDGE_ID, "via_node": 1, "to_edge": _EDGE_ID + 1}
                ],
            },
            FARES_NAME: {
                "schema_version": FARES_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "nodes": [
                    {
                        "id": "f_001",
                        "pos": [50.0, 0.0, 4.0],
                        "kind": "taxi_stand",
                        "stand_category": "urban",
                        "name": {"en": "Middle", "zh": "中"},
                        "nearest_edge": _EDGE_ID,
                        "edge_t": 0.5,
                        "pickup": True,
                        "dropoff": True,
                    }
                ],
            },
            # Written whether or not the city has a tramway, for the same
            # reason `ASSETS_NAME` is: export's input read is unconditional, and
            # a stage that found nothing still has to say so. `testville`
            # declares no `tramway:` block, so this is the found-nothing shape —
            # a null asset, which must leave `city.json`'s key null and the
            # shipped list unchanged.
            TRAMWAY_MANIFEST_NAME: {
                "schema_version": TRAMWAY_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "asset": None,
                "rails": 0,
                "tracks": 0,
            },
            # Same shape and same reason as the tramway above: `testville`
            # declares no `arrows:` block, so the stage found nothing and says
            # so, and `city.json`'s key must come out null with the shipped list
            # unchanged.
            ARROWS_MANIFEST_NAME: {
                "schema_version": ARROWS_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "asset": None,
                "symbols": 0,
                "drawn": 0,
            },
            # Same shape and same reason again: `testville` declares no
            # `boxjunctions:` block, so the stage found nothing and says so.
            BOXJUNCTIONS_MANIFEST_NAME: {
                "schema_version": BOXJUNCTIONS_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "asset": None,
                "boxes": 0,
                "drawn": 0,
            },
            # Same shape and same reason a fourth time: `testville` declares no
            # `road_marks:` block, so the stage found nothing and says so.
            ROADMARKS_MANIFEST_NAME: {
                "schema_version": ROADMARKS_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "asset": None,
                "parts": 0,
                "drawn": 0,
            },
            # Same shape and same reason a fifth time: `testville` declares no
            # `railings:` block, so the stage found nothing and says so.
            RAILINGS_MANIFEST_NAME: {
                "schema_version": RAILINGS_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "asset": None,
                "features": 0,
                "drawn_m": 0.0,
            },
            # Same shape and same reason a fifth time: `testville` declares no
            # `signs:` block, so the stage found nothing and says so.
            SIGNS_MANIFEST_NAME: {
                "schema_version": SIGNS_MANIFEST_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "asset": None,
                "signs": 0,
                "drawn": 0,
            },
            # Written even when empty by the landmarks stage, so export's
            # input read is unconditional.
            ASSETS_NAME: {
                "schema_version": ASSETS_SCHEMA,
                "city_id": city.id,
                "region_id": REGION,
                "assets": [],
            },
        }

        (self.out_dir / SURFACE_NAME).write_bytes(b"glb")
        for tile in self.documents[BUILDINGS_MANIFEST_NAME]["tiles"]:
            for lod in tile["lods"]:
                (self.out_dir / lod["path"]).write_bytes(b"glb")
        self.save()

    def save(self) -> None:
        for name, document in self.documents.items():
            (self.out_dir / name).write_text(json.dumps(document), encoding="utf-8")

    def build(self, **kwargs):
        self.save()
        kwargs.setdefault("generated_utc", STAMP)
        return build_region(self.city, REGION, out_root=self.out_root, **kwargs)

    def check(self) -> list[str]:
        self.save()
        return validate(self.city, REGION, out_root=self.out_root)

    def manifest(self) -> dict:
        return json.loads((self.out_dir / CITY_NAME).read_text(encoding="utf-8"))


@pytest.fixture
def region(tmp_path, testville_config):
    return _Region(testville_config, tmp_path / "out")


class TestAssembly:
    def test_writes_a_manifest_naming_every_shipped_document(self, region) -> None:
        report = region.build()
        manifest = region.manifest()

        assert manifest["schema_version"] == CITY_SCHEMA
        assert manifest["city_id"] == "testville"
        assert manifest["region_id"] == REGION
        assert manifest["road_graph"] == ROADGRAPH_NAME
        assert manifest["road_surface"] == SURFACE_NAME
        assert manifest["fares"] == FARES_NAME
        assert report.tiles == 2
        assert report.lod_files == 3

    def test_tiles_carry_their_lod_paths_in_order(self, region) -> None:
        region.build()
        tile = region.manifest()["tiles"][0]

        assert tile["id"] == "t_00_00"
        assert tile["lods"] == ["tiles/t_00_00_lod0.glb", "tiles/t_00_00_lod1.glb"]

    def test_the_intermediates_are_not_shipped(self, region) -> None:
        """`buildings.json` and `roadsurface.json` sit in the same directory and
        are not part of the contract. A build copies what the manifest names."""
        region.build()
        names = shipped(region.manifest())

        assert BUILDINGS_MANIFEST_NAME not in names
        assert SURFACE_MANIFEST_NAME not in names
        assert ASSETS_NAME not in names
        assert set(names) >= {ROADGRAPH_NAME, SURFACE_NAME, FARES_NAME}

    def test_a_drawn_box_junction_asset_is_shipped_and_a_null_is_not(self, region) -> None:
        """The two halves of the optional-key contract (`P3-18`), in one place:
        a found-nothing manifest leaves `city.json`'s key null and the shipped
        list unchanged, and a drawn asset joins both — the same terms `tramway`
        and `arrows` ship under."""
        region.build()
        assert region.manifest()["boxjunctions"] is None
        assert "boxjunctions.glb" not in shipped(region.manifest())

        region.documents[BOXJUNCTIONS_MANIFEST_NAME]["asset"] = "boxjunctions.glb"
        (region.out_dir / "boxjunctions.glb").write_bytes(b"glb")
        region.build()
        assert region.manifest()["boxjunctions"] == "boxjunctions.glb"
        assert "boxjunctions.glb" in shipped(region.manifest())

    def test_the_carriageway_widths_reach_the_manifest(self, region) -> None:
        """Carried, not recomputed. A second evaluation of `widen_for` in
        `export.py` would be a second thing to keep in step with the config."""
        region.build()
        surface = region.documents[SURFACE_MANIFEST_NAME]
        table = region.manifest()["carriageway"]
        assert [entry["half_width_m"] for entry in table] == [
            entry["half_width_m"] for entry in surface["carriageway"]
        ]
        assert {entry["edge"] for entry in table} == {
            edge["id"] for edge in region.documents[ROADGRAPH_NAME]["edges"]
        }

    def test_the_clearances_join_the_widths_and_the_trims_do_not(self, region) -> None:
        """`Q51`. Two stages measured this table and neither could have measured
        both, so the join is here. `trim_m` is how a ribbon met its junction
        caps — an intermediate, and a question the game never asks."""
        region.build()
        clearance = region.documents[CLEARANCE_NAME]
        table = {entry["edge"]: entry for entry in region.manifest()["carriageway"]}
        for entry in clearance["clearance"]:
            assert table[entry["edge"]]["clear_width_m"] == entry["clear_width_m"]
        assert all("trim_m" not in entry for entry in table.values())
        assert region.manifest()["lane_width_m"] == region.city.roads.lane_width_m

    def test_a_clearance_out_of_step_with_the_widths_is_refused(self, region) -> None:
        """Not padded. `P2-2` falls back on a short half-width array because a
        lane centre off the tarmac is survivable; the station a missing
        clearance fails to describe is the one a router would call clear."""
        region.documents[CLEARANCE_NAME]["clearance"][0]["clear_width_m"] = [10.24]
        with pytest.raises(ValueError, match="different runs"):
            region.build()

    def test_the_origin_is_the_region_transform(self, region) -> None:
        region.build()
        transform = region.city.game_transform(REGION)

        assert region.manifest()["origin"] == {
            "easting": transform.origin_easting,
            "northing": transform.origin_northing,
            "elevation": transform.origin_elevation,
        }

    def test_bounds_cover_content_past_the_region(self, region) -> None:
        """The reason `bounds_game` is the union of the content rather than the
        region rectangle: a tile is allowed to overhang, and a consumer sizing
        anything off the rectangle would clip it."""
        region.build()
        bounds = region.manifest()["bounds_game"]

        assert region.far_x > region.city.region_high(REGION)[0]
        assert bounds["max"][0] == pytest.approx(region.far_x)

    def test_bounds_cover_the_road_surface_outside_the_tiles(self, region) -> None:
        region.build()
        bounds = region.manifest()["bounds_game"]

        assert bounds["min"][0] == pytest.approx(-4.0)
        assert bounds["min"][2] == pytest.approx(-4.0)

    def test_two_builds_of_the_same_inputs_are_identical(self, region) -> None:
        """With the stamp pinned, a diff between two builds means something."""
        region.build()
        first = (region.out_dir / CITY_NAME).read_bytes()
        region.build()

        assert (region.out_dir / CITY_NAME).read_bytes() == first


class TestLandmarks:
    """`landmarks.json` — assembly from config, and the two-way stem check.

    Neither side can see the mismatch alone: a config claiming a stem the
    building stage never saw is internally fine, and so is a `buildings.json`
    recording an exclusion no landmark owns. `validate` is the only place the
    two meet.
    """

    FOOTPRINT: ClassVar[list[list[float]]] = [[40.0, 0.0, 40.0], [60.0, 300.0, 60.0]]

    def hero(self, region, stems: tuple[str, ...] = ("hero_a",), *, excluded: bool = True):
        """Put one landmark on the region's config, standing at game (50, 50).

        `excluded` also writes the matching record into `buildings.json`, the
        way a real build would have; a test drops it to make the sides disagree.
        """
        easting, northing, _ = region.city.game_transform(REGION).to_source(50.0, 0.0, 50.0)
        landmark = Landmark(
            id="hero",
            asset="res://assets/authored/landmarks/hero.glb",
            easting=easting,
            northing=northing,
            elevation=0.0,
            rot_y_deg=45.0,
            name_en="Hero",
            name_zh="主角",
            replaces_source_ids=stems,
        )
        region.city = replace(region.city, landmarks=(landmark,))
        if excluded:
            region.documents[BUILDINGS_MANIFEST_NAME]["excluded"] = {
                stem: self.FOOTPRINT for stem in stems
            }
        return landmark

    def landmarks_document(self, region) -> dict:
        return json.loads((region.out_dir / LANDMARKS_NAME).read_text(encoding="utf-8"))

    def test_the_manifest_names_the_document_and_ships_it(self, region) -> None:
        region.build()
        manifest = region.manifest()
        assert manifest["landmarks"] == LANDMARKS_NAME
        assert LANDMARKS_NAME in shipped(manifest)
        assert (region.out_dir / LANDMARKS_NAME).exists()

    def test_a_city_without_landmarks_ships_an_empty_document(self, region) -> None:
        region.build()
        document = self.landmarks_document(region)
        assert document["schema_version"] == LANDMARKS_SCHEMA
        assert document["landmarks"] == []

    def test_positions_convert_to_game_space_and_the_bearing_passes_through(self, region) -> None:
        self.hero(region)
        region.build()
        [entry] = self.landmarks_document(region)["landmarks"]

        assert entry["id"] == "hero"
        assert entry["transform"]["pos"] == [50.0, 0.0, 50.0]
        assert entry["transform"]["rot_y_deg"] == 45.0
        assert entry["name"] == {"en": "Hero", "zh": "主角"}
        assert entry["excluded_bounds"] == self.FOOTPRINT

    def test_the_excluded_footprint_joins_bounds_game(self, region) -> None:
        """The hero stands where the excluded buildings stood, so the bounds
        must not shrink by the geometry the region still contains."""
        self.hero(region)
        region.build()
        assert region.manifest()["bounds_game"]["max"][1] == pytest.approx(300.0)

    def test_a_matched_pair_validates_clean(self, region) -> None:
        """Also the proof the committed `.glb` is never checked as a file —
        `res://` points into the game tree, which this out-tree lacks."""
        self.hero(region)
        region.build()
        assert region.check() == []

    def test_a_stem_never_excluded_is_flagged(self, region) -> None:
        self.hero(region, excluded=False)
        region.build()
        problems = region.check()
        assert any("never excluded" in problem for problem in problems)

    def test_an_orphaned_exclusion_is_flagged(self, region) -> None:
        region.documents[BUILDINGS_MANIFEST_NAME]["excluded"] = {
            "orphan": [[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]]
        }
        region.build()
        problems = region.check()
        assert any("belong to no landmark" in problem for problem in problems)

    def test_a_position_off_its_footprint_is_flagged(self, region) -> None:
        """The authored centroid should stand on what it replaced — a config
        pasted from the wrong building fails here, not in a drive."""
        self.hero(region)
        region.documents[BUILDINGS_MANIFEST_NAME]["excluded"]["hero_a"] = [
            [150.0, 0.0, 100.0],
            [170.0, 300.0, 120.0],
        ]
        region.build()
        problems = region.check()
        assert any("off the footprint" in problem for problem in problems)

    # -- mesh-sourced heroes (`P3-6` amendment) ----------------------------

    PAINT: ClassVar[SourcePaint] = SourcePaint(
        wall=Material("wall", (134, 128, 119), 42.0, "test"),
        ribbon=Material("ribbon", (61, 72, 83), 12.0, "test"),
        roof=Material("roof", (90, 96, 99), 22.0, "test"),
        base=Material("base", (114, 110, 102), 30.0, "test"),
        ribbon_first_m=15.0,
        ribbon_pitch_m=4.8,
        ribbon_thickness_m=1.5,
        ribbon_count=10,
        base_below_m=8.0,
    )

    def mesh_hero(self, region, *, built: bool = True):
        """A `source_paint` hero, with its built model and assets record.

        `built` also writes the `.glb` and the `landmark_assets.json` entry
        the landmarks stage would have; a test drops it to make the manifest
        claim a model nothing built.
        """
        landmark = self.hero(region)
        landmark = replace(
            landmark,
            asset="res://assets/generated/landmarks/hero.glb",
            rot_y_deg=0.0,
            source_paint=self.PAINT,
            triangle_budget=120_000,
        )
        region.city = replace(region.city, landmarks=(landmark,))
        if built:
            (region.out_dir / "landmarks").mkdir(exist_ok=True)
            (region.out_dir / "landmarks" / "hero.glb").write_bytes(b"glb")
            region.documents[ASSETS_NAME]["assets"] = [
                {
                    "id": "hero",
                    "path": "landmarks/hero.glb",
                    "triangles": 99_577,
                    "bytes": 3,
                    "stems": ["hero_a"],
                }
            ]
        return landmark

    def test_a_mesh_sourced_hero_ships_its_model(self, region) -> None:
        self.mesh_hero(region)
        region.build()
        manifest = region.manifest()

        assert manifest["landmark_assets"] == ["landmarks/hero.glb"]
        assert "landmarks/hero.glb" in shipped(manifest)
        assert region.check() == []

    def test_the_entry_carries_its_triangle_budget(self, region) -> None:
        """The in-engine verifier reads the ceiling from the entry it grades —
        config data, not a constant it could drift from."""
        self.mesh_hero(region)
        region.build()
        [entry] = self.landmarks_document(region)["landmarks"]
        assert entry["triangle_budget"] == 120_000

    def test_a_missing_built_model_is_flagged(self, region) -> None:
        """Unlike the authored heroes, the built ones are files this out-tree
        must contain — `shipped()` lists them and `_check_files` stats them."""
        self.mesh_hero(region)
        region.build()
        (region.out_dir / "landmarks" / "hero.glb").unlink()
        problems = region.check()
        assert any("landmarks/hero.glb" in p and "does not exist" in p for p in problems)

    def test_a_model_built_after_the_manifest_is_flagged(self, region) -> None:
        """A stale manifest names yesterday's asset set; the assets document
        is the side a rebuild moves first."""
        self.mesh_hero(region, built=False)
        region.build()
        (region.out_dir / "landmarks").mkdir(exist_ok=True)
        (region.out_dir / "landmarks" / "hero.glb").write_bytes(b"glb")
        region.documents[ASSETS_NAME]["assets"] = [
            {
                "id": "hero",
                "path": "landmarks/hero.glb",
                "triangles": 1,
                "bytes": 3,
                "stems": ["hero_a"],
            }
        ]
        problems = region.check()
        assert any("not in city.json's landmark_assets" in p for p in problems)

    def test_an_asset_disagreeing_with_its_built_model_is_flagged(self, region) -> None:
        self.mesh_hero(region)
        region.build()
        document = self.landmarks_document(region)
        document["landmarks"][0]["asset"] = "res://assets/authored/landmarks/hero.glb"
        (region.out_dir / LANDMARKS_NAME).write_text(json.dumps(document), encoding="utf-8")
        problems = validate(region.city, REGION, out_root=region.out_root)
        assert any("does not match its built model" in p for p in problems)


class TestShippedList:
    """`--list`, which `tools/sync_generated.sh` copies from (`P1-7`).

    The sync script exists so the game's asset directory is the manifest's
    contents and nothing else. What makes that true is that the list comes from
    here rather than from a directory listing on either side.
    """

    def test_every_named_file_is_listed_and_exists(self, region) -> None:
        region.build()
        names = shipped(read_manifest(region.city, REGION, out_root=region.out_root))

        assert names
        for name in names:
            assert (region.out_dir / name).exists(), name

    def test_the_manifest_is_not_in_its_own_list(self, region) -> None:
        """A caller syncing a region copies this plus `city.json`. Listing the
        manifest inside itself would also change the shipped-file count the
        build reports."""
        region.build()

        assert CITY_NAME not in shipped(
            read_manifest(region.city, REGION, out_root=region.out_root)
        )

    def test_a_stale_manifest_is_refused_rather_than_listed(self, region) -> None:
        """The copy must not be the one thing that reads a mismatched schema
        happily — it is the step that puts files in front of the engine."""
        region.build()
        manifest = region.manifest()
        manifest["schema_version"] = CITY_SCHEMA + 1
        (region.out_dir / CITY_NAME).write_text(json.dumps(manifest), encoding="utf-8")

        with pytest.raises(ValueError, match=r"python -m pipeline\.export"):
            read_manifest(region.city, REGION, out_root=region.out_root)


class TestStaleInputs:
    def test_a_missing_intermediate_names_the_command_that_writes_it(self, region) -> None:
        (region.out_dir / SURFACE_MANIFEST_NAME).unlink()

        with pytest.raises(FileNotFoundError, match=r"python -m pipeline\.surface"):
            build_region(region.city, REGION, out_root=region.out_root)

    def test_a_schema_from_the_future_is_refused(self, region) -> None:
        region.documents[ROADGRAPH_NAME]["schema_version"] = ROADGRAPH_SCHEMA + 1

        with pytest.raises(ValueError, match=r"python -m pipeline\.roads"):
            region.build()


class TestValidation:
    def test_a_complete_set_has_no_problems(self, region) -> None:
        region.build()

        assert region.check() == []

    def test_a_tile_whose_mesh_never_got_written(self, region) -> None:
        region.build()
        (region.out_dir / "tiles" / "t_01_00_lod0.glb").unlink()

        assert region.check() == ["city.json names tiles/t_01_00_lod0.glb, which does not exist"]

    def test_an_empty_asset_counts_as_missing(self, region) -> None:
        region.build()
        (region.out_dir / SURFACE_NAME).write_bytes(b"")

        assert region.check() == ["roads.glb is empty"]

    def test_a_fare_node_naming_an_edge_the_graph_lost(self, region) -> None:
        """Re-running the road stage renumbers edges. Every `nearest_edge`
        written before it then names a different street, or none at all."""
        region.build()
        region.documents[FARES_NAME]["nodes"][0]["nearest_edge"] = 999

        assert region.check() == [
            "1 fare nodes name an edge roadgraph.json does not have: ['f_001']"
        ]

    def test_an_edge_t_off_the_end_of_its_edge(self, region) -> None:
        region.build()
        region.documents[FARES_NAME]["nodes"][0]["edge_t"] = 1.5

        assert region.check() == ["1 fare nodes have an edge_t outside [0, 1]: ['f_001']"]

    def test_a_fare_node_hosted_by_an_off_grade_edge(self, region) -> None:
        """`Q15`, and it is a staleness check rather than a graph one.

        `fares.py` cannot write this any more, so what reaches here is a
        `fares.json` built before that restriction and left in the output
        directory through a `--from` rebuild — the case the unit tests cannot
        see, because they grade the code, and `off_grade_nearer` cannot either,
        because a skipped stage prints nothing.
        """
        region.build()
        region.documents[ROADGRAPH_NAME]["edges"][0]["elevation_level"] = 1

        assert region.check() == [
            "1 fare nodes name an off-grade edge, so their height came off a deck "
            "or a tunnel rather than the street (`Q15`): ['f_001']"
        ]

    def test_a_document_left_over_from_another_region(self, region) -> None:
        """Each document is perfectly valid on its own. Only the set is wrong."""
        region.build()
        region.documents[ROADGRAPH_NAME]["region_id"] = "elsewhere"

        assert region.check() == [
            "roadgraph.json is for testville/elsewhere, city.json for testville/middle"
        ]

    def test_an_edge_with_no_node_at_its_end(self, region) -> None:
        region.build()
        region.documents[ROADGRAPH_NAME]["edges"][0]["to"] = 77

        assert region.check() == [f"1 edges reference a node that does not exist: [{_EDGE_ID}]"]

    def test_a_turn_restriction_pointing_at_nothing(self, region) -> None:
        region.build()
        region.documents[ROADGRAPH_NAME]["turn_restrictions"][0]["to_edge"] = 900

        assert region.check() == ["1 turn restrictions reference something that does not exist"]

    def test_a_manifest_left_over_from_a_smaller_build(self, region) -> None:
        """The failure `bounds_game` has: a manifest from a previous run is
        still schema-valid and describes a region that no longer exists."""
        region.build()
        manifest = region.manifest()
        manifest["bounds_game"] = {"min": [0.0, 0.0, 0.0], "max": [10.0, 10.0, 10.0]}
        (region.out_dir / CITY_NAME).write_text(json.dumps(manifest), encoding="utf-8")

        problems = region.check()

        assert len(problems) == 4
        assert all("outside bounds_game" in problem for problem in problems)

    def test_a_tile_the_manifest_forgot(self, region) -> None:
        """A stale manifest is self-consistent by definition — its tile list and
        its bounds were written together. Only `buildings.json` can say a tile
        is missing from it."""
        region.build()
        manifest = region.manifest()
        del manifest["tiles"][1]
        (region.out_dir / CITY_NAME).write_text(json.dumps(manifest), encoding="utf-8")

        assert region.check() == ["1 tiles in buildings.json are not in city.json: ['t_01_00']"]

    def test_a_tile_the_building_stage_never_built(self, region) -> None:
        region.build()
        manifest = region.manifest()
        manifest["tiles"][1]["id"] = "t_09_09"
        (region.out_dir / CITY_NAME).write_text(json.dumps(manifest), encoding="utf-8")

        assert region.check() == [
            "1 tiles in buildings.json are not in city.json: ['t_01_00']",
            "1 tiles in city.json were not built by buildings.json: ['t_09_09']",
        ]

    def test_two_tiles_with_the_same_id(self, region) -> None:
        region.build()
        manifest = region.manifest()
        manifest["tiles"][1]["id"] = manifest["tiles"][0]["id"]
        (region.out_dir / CITY_NAME).write_text(json.dumps(manifest), encoding="utf-8")

        assert "two tiles share the id t_00_00" in region.check()


class TestOrchestrator:
    """The stage table, with the stages themselves stubbed out."""

    @staticmethod
    def _stub(monkeypatch, calls: list[tuple[str, list[str]]], failing: str | None = None):
        for name in list(orchestrator.STAGES):

            def run(argv: list[str], name: str = name) -> int:
                calls.append((name, argv))
                return 1 if name == failing else 0

            monkeypatch.setitem(orchestrator.STAGES, name, run)

    def test_every_stage_runs_in_dependency_order(self, monkeypatch) -> None:
        calls: list[tuple[str, list[str]]] = []
        self._stub(monkeypatch, calls)

        status = orchestrator.main(["--city", "testville", "--region", REGION])

        assert status == 0
        assert [name for name, _ in calls] == [
            "fetch",
            "podiums",
            "buildings",
            "landmarks",
            "roads",
            "surface",
            "clearance",
            "fares",
            "tramway",
            "arrows",
            "boxjunctions",
            "roadmarks",
            "railings",
            "signs",
            "export",
        ]

    def test_every_stage_gets_the_city_and_region(self, monkeypatch) -> None:
        calls: list[tuple[str, list[str]]] = []
        self._stub(monkeypatch, calls)

        orchestrator.main(["--city", "testville", "--region", REGION])

        assert all(argv == ["--city", "testville", "--region", REGION] for _, argv in calls)

    def test_force_reaches_fetch_and_nothing_else(self, monkeypatch) -> None:
        calls: list[tuple[str, list[str]]] = []
        self._stub(monkeypatch, calls)

        orchestrator.main(["--city", "testville", "--region", REGION, "--force"])

        assert calls[0][1][-1] == "--force"
        assert not any("--force" in argv for _, argv in calls[1:])

    def test_from_skips_the_stages_before_it(self, monkeypatch) -> None:
        calls: list[tuple[str, list[str]]] = []
        self._stub(monkeypatch, calls)

        orchestrator.main(["--city", "testville", "--region", REGION, "--from", "surface"])

        assert [name for name, _ in calls] == [
            "surface",
            "clearance",
            "fares",
            "tramway",
            "arrows",
            "boxjunctions",
            "roadmarks",
            "railings",
            "signs",
            "export",
        ]

    def test_force_without_fetch_is_refused_rather_than_ignored(self, monkeypatch) -> None:
        calls: list[tuple[str, list[str]]] = []
        self._stub(monkeypatch, calls)

        with pytest.raises(SystemExit):
            orchestrator.main(
                ["--city", "testville", "--region", REGION, "--from", "roads", "--force"]
            )

        assert calls == []

    def test_a_failing_stage_stops_the_run(self, monkeypatch) -> None:
        """Every later stage reads what an earlier one writes, so carrying on
        would build the rest of the region from the previous run's output."""
        calls: list[tuple[str, list[str]]] = []
        self._stub(monkeypatch, calls, failing="roads")

        status = orchestrator.main(["--city", "testville", "--region", REGION])

        assert status == 1
        assert [name for name, _ in calls] == [
            "fetch",
            "podiums",
            "buildings",
            "landmarks",
            "roads",
        ]
