"""`pipeline/backdrop.py` — the far shore (`P3-100`, `Q249`).

What is asserted is what a frame cannot show: that the cap is a cap, that the
skyline it refuses is the short end, that the open water never lies in a
frame or inland, that a region's skyline is its own, and that the reach the
fetch reads is the one the stage does.
"""

from __future__ import annotations

import copy
import dataclasses

import numpy as np
import pytest
import shapely
import yaml
from shapely.geometry import LineString, Polygon, box

from pipeline.backdrop import (
    BACKDROP_MATERIAL,
    BACKDROP_SEA_MESH_NAME,
    FAR_SEA_ALPHA,
    BackdropReport,
    Block,
    build_meshes,
    ground_of,
    open_sea_of,
    shore_of,
    skyline_of,
)
from pipeline.basemap import WATER_MATERIAL
from pipeline.config import CONFIG_PATH, _materials, _MaterialTable
from pipeline.config_blocks.backdrop import _backdrop


@pytest.fixture
def spec(hong_kong):
    assert hong_kong.backdrop is not None
    return hong_kong.backdrop


def _tower(x: float, y: float, height_m: float, side_m: float = 20.0) -> Block:
    return Block(box(x, y, x + side_m, y + side_m), roof_m=height_m + 5.0, height_m=height_m)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b.update(triangle_cap=0), "triangle_cap"),
        (lambda b: b.update(min_height_m=0.0), "min_height_m"),
        (lambda b: b.update(ground_close_m=-1.0), "ground_close_m"),
        (lambda b: b.update(sea_reach_m=0.0), "sea_reach_m"),
        (lambda b: b.pop("sea_reach_m"), "sea_reach_m"),
        (lambda b: b.update(ground_material="moss"), "ground_material"),
        (lambda b: b["bands"][0].update(above_m=10.0), "the first is 0"),
        (lambda b: b["bands"][1].update(above_m=0.0), "not above the band before"),
        (lambda b: b["buildings"]["fields"].pop("roof"), "roof"),
    ],
)
def test_block_refuses(mutate, message: str) -> None:
    document = yaml.safe_load(CONFIG_PATH.read_text())
    table = _MaterialTable(_materials(document["materials"], "materials"))
    body = copy.deepcopy(document["backdrop"])
    mutate(body)
    with pytest.raises((ValueError, KeyError), match=message):
        _backdrop(body, "backdrop", table)


def test_the_fetch_reads_the_sea_reach_of_every_region(hong_kong, spec) -> None:
    for region_id in hong_kong.regions:
        extents = hong_kong.fetch_extents(spec.source, region_id)
        assert extents == (hong_kong.bounds_past(region_id, spec.sea_reach_m),)
    assert hong_kong.fetch_extents("buildings", "wan_chai") == ()


def test_the_reach_meets_a_far_only_region_from_the_frame_across_from_it(hong_kong, spec) -> None:
    """Tsim Sha Tsui's reach runs its water to Wan Chai's frame: the open
    harbour between the two is somebody's."""
    from pipeline.basemap import frame_of

    reach = frame_of(hong_kong, "tsim_sha_tsui", spec.sea_reach_m)
    assert reach.intersects(frame_of(hong_kong, "wan_chai", hong_kong.basemap.reach_m))


def test_the_skyline_is_the_tall_blocks_and_the_cap_refuses_the_shortest(spec) -> None:
    tall = [_tower(40.0 * row, 0.0, spec.min_height_m + 10.0 * row) for row in range(6)]
    short = _tower(0.0, 100.0, spec.min_height_m - 1.0)
    # A square tower is four walls and a roof: ten triangles.
    assert tall[0].triangles == 10

    report = BackdropReport()
    assert len(skyline_of([short, *tall], spec, report)) == 6
    assert (report.blocks_tall, report.blocks_drawn) == (6, 6)
    # The shortest tower stands exactly `min_height_m` tall.
    assert report.min_height_drawn_m == pytest.approx(spec.min_height_m)
    assert skyline_of([short], spec, BackdropReport()) == []

    capped = dataclasses.replace(spec, triangle_cap=35)
    drawn = skyline_of([short, *tall], capped, report)
    assert [block.height_m for block in drawn] == sorted(
        (block.height_m for block in tall), reverse=True
    )[:3]
    assert report.blocks_drawn == 3
    assert report.min_height_drawn_m == pytest.approx(spec.min_height_m + 30.0)


def test_the_shore_closes_over_what_stands_on_it_and_fills_a_park(spec) -> None:
    strip = box(0.0, 0.0, 2000.0, 2000.0)
    # A ring of blocks round an unbuilt square wider than the closing: a park.
    blocks = [
        _tower(600.0 + 100.0 * column, 600.0 + 100.0 * row, 40.0, side_m=60.0)
        for column in range(8)
        for row in range(8)
        if column in (0, 7) or row in (0, 7)
    ]
    wall = LineString([(600.0, 300.0), (1360.0, 300.0)])
    shore = shore_of(strip, ground_of(blocks, [wall], spec), spec)

    assert shore.contains(shapely.Point(980.0, 980.0))  # the park, filled
    assert shore.contains(shapely.Point(980.0, 450.0))  # closed out to the sea wall
    assert not shore.contains(shapely.Point(980.0, 150.0))  # and no further
    assert not shore.contains(shapely.Point(100.0, 100.0))


def test_the_open_water_is_outside_every_frame_and_joined_to_a_sea() -> None:
    reach = box(-1000.0, -1000.0, 3000.0, 4000.0)
    frame = box(0.0, 0.0, 1000.0, 1000.0)
    sea = box(0.0, 800.0, 1000.0, 1000.0)
    # The far shore's land along the north, and an island of land in the
    # harbour that walls off a lagoon.
    land = shapely.union_all(
        [
            box(-1000.0, 3000.0, 3000.0, 4000.0),
            box(2000.0, 1500.0, 2600.0, 2100.0).difference(box(2100.0, 1600.0, 2500.0, 2000.0)),
        ]
    )
    # Inland behind the frame: unbuilt, but walled off from the sea by the
    # frame's own land.
    inland = box(-1000.0, -1000.0, 3000.0, 0.0)
    open_sea = open_sea_of(
        reach, shapely.union_all([land, box(1000.0, -1000.0, 3000.0, 0.0)]), [frame], [sea]
    )

    assert open_sea.contains(shapely.Point(500.0, 2000.0))  # the channel
    assert open_sea.contains(shapely.Point(-500.0, 900.0))  # beside the frame, off its sea
    assert not open_sea.contains(shapely.Point(500.0, 900.0))  # the frame's own sea is its own
    assert not open_sea.contains(shapely.Point(500.0, 400.0))  # nor its land
    assert not open_sea.contains(shapely.Point(500.0, 3500.0))  # the far shore's land
    assert not open_sea.contains(shapely.Point(2300.0, 1800.0))  # the walled lagoon
    assert open_sea.contains(shapely.Point(-500.0, -500.0))  # joined round the frame's west
    assert inland.intersects(open_sea)
    assert open_sea_of(reach, land, [frame], [Polygon()]).is_empty  # no sea, no open water


def test_the_meshes_are_the_skyline_on_its_shore_and_a_marked_sea(hong_kong, spec) -> None:
    transform = hong_kong.game_transform("wan_chai")
    east, north = transform.origin_easting, transform.origin_northing + 2000.0
    towers = [_tower(east + 100.0, north + 100.0, 150.0), _tower(east + 200.0, north + 100.0, 50.0)]
    shore = box(east, north, east + 400.0, north + 400.0)
    far_sea = box(east, north - 1500.0, east + 400.0, north + 400.0)
    report = BackdropReport()
    land, sea = build_meshes(towers, shore, far_sea, hong_kong, transform, report)

    assert land.material == BACKDROP_MATERIAL
    assert report.skyline_triangles == sum(tower.triangles for tower in towers)
    # The shore is one square slab: four walls and a top.
    assert report.shore_triangles == 10
    assert len(land.triangles) == report.skyline_triangles + 10
    # Stood on the shore's ground, up to each published roof, north of the origin.
    assert land.positions[:, 1].max() == pytest.approx(155.0)
    assert land.positions[:, 1].min() < hong_kong.basemap.water_level_m
    assert land.positions[:, 2].max() <= -2000.0
    # Each block in its own height band's colour.
    colours = {tuple(row) for row in land.colours[:, :3]}
    assert tuple(spec.material_for(150.0).colour) in colours
    assert tuple(spec.material_for(50.0).colour) in colours
    assert tuple(spec.ground_material.colour) in colours

    assert sea.name == BACKDROP_SEA_MESH_NAME and sea.material == WATER_MATERIAL
    assert (sea.colours[:, 3] == FAR_SEA_ALPHA).all()
    assert np.allclose(sea.positions[:, 1], hong_kong.basemap.water_level_m)
    assert (sea.normals[:, 1] == 1.0).all()
