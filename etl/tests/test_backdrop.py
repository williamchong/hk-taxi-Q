"""`pipeline/backdrop.py` — the far shore (`P3-100`, `Q249`).

What is asserted is what a frame cannot show: that the cap is a cap, that the
skyline it refuses is the short end, that the far sea never lies under a
frame's land, and that the block the fetch reads is the one the stage does.
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
    far_sea_of,
    shore_of,
    skyline_of,
    strip_of,
)
from pipeline.basemap import WATER_MATERIAL, frame_of
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
        (lambda b: b.update(regions=[]), "regions"),
        (lambda b: b.update(regions="wan_chai"), "regions"),
        (lambda b: b.update(ground_material="moss"), "ground_material"),
        (lambda b: b["bands"][0].update(above_m=10.0), "the first is 0"),
        (lambda b: b["bands"][1].update(above_m=0.0), "not above the band before"),
        (lambda b: b["bounds"].pop("north"), "north"),
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


def test_the_strip_stands_clear_of_every_region_that_ships_it(hong_kong, spec) -> None:
    """North of the frame and off it: the far sea is run from the frame's north
    edge, and a strip that reached into the frame would stand on the street."""
    strip = strip_of(hong_kong, spec)
    for region_id in spec.regions:
        frame = frame_of(hong_kong, region_id, hong_kong.basemap.reach_m)
        assert strip.bounds[1] > frame.bounds[3]
        assert strip.distance(frame) > 400.0


def test_the_fetch_reads_the_strip_for_a_region_that_ships_it(hong_kong, spec) -> None:
    for region_id in hong_kong.regions:
        extents = hong_kong.fetch_extents(spec.source, region_id)
        assert extents == ((spec.bounds,) if region_id in spec.regions else ())
    assert hong_kong.fetch_extents("buildings", next(iter(spec.regions))) == ()


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
    shore = shore_of(strip, blocks, [wall], spec)

    assert shore.contains(shapely.Point(980.0, 980.0))  # the park, filled
    assert shore.contains(shapely.Point(980.0, 450.0))  # closed out to the sea wall
    assert not shore.contains(shapely.Point(980.0, 150.0))  # and no further
    assert not shore.contains(shapely.Point(100.0, 100.0))


def test_the_far_sea_keeps_off_a_frames_land_and_carries_its_sea() -> None:
    strip = box(-1000.0, 3000.0, 3000.0, 4000.0)
    own = box(0.0, 0.0, 1000.0, 1000.0)
    # A neighbour whose frame runs further north than the region's own.
    beside = box(1000.0, 0.0, 2000.0, 1500.0)
    own_sea = box(0.0, 800.0, 1000.0, 1000.0)
    far_sea = far_sea_of(strip, [own, beside], [own_sea, Polygon()])

    assert far_sea.contains(shapely.Point(500.0, 2000.0))  # the channel
    assert far_sea.contains(shapely.Point(500.0, 3500.0))  # under the strip
    assert far_sea.contains(shapely.Point(500.0, 900.0))  # the frame's own sea
    assert not far_sea.contains(shapely.Point(500.0, 400.0))  # its land
    assert not far_sea.contains(shapely.Point(1500.0, 900.0))  # a neighbour with no sea
    assert not far_sea.contains(shapely.Point(1500.0, 1200.0))  # nor past the own north edge
    assert far_sea.contains(shapely.Point(1500.0, 1600.0))
    # East to west it spans the strip and the frames both.
    assert far_sea.bounds[0] == -1000.0 and far_sea.bounds[2] == 3000.0


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
