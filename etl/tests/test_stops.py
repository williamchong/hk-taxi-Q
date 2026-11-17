"""`pipeline/stops.py` — authored furniture at published stops (`P3-93`)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import load_config
from pipeline.config_blocks.stops import BUS, MINIBUS, TAXI
from pipeline.gltf import placed_positions
from pipeline.railings import facing_away
from pipeline.stops import (
    POLE_MESH_NAME,
    TRAM_MESH_NAME,
    StopReport,
    flag_mesh,
    merged,
    pole_mesh,
    pole_points,
    shelter_mesh,
    tram_stands,
)
from tests.helpers import CITY_YAML

COLOURS = {
    "red": (194, 26, 38),
    "white": (240, 240, 234),
    "grey": (112, 115, 122),
    "green": (31, 138, 76),
}

FLAG = {"width_m": 0.5, "height_m": 0.8, "mount_m": 2.5, "colour": "red", "band": "white"}

BLOCK: dict[str, Any] = {
    "outset_m": 0.45,
    "max_shift_m": 6.0,
    "merge_m": 4.0,
    "pole_radius_m": 0.04,
    "pole_colour": "grey",
    "plate_thickness_m": 0.04,
    "flags": {BUS: FLAG, MINIBUS: FLAG, TAXI: FLAG},
    "tram": {
        "offset_m": 1.9,
        "length_m": 8.0,
        "width_m": 1.4,
        "height_m": 2.7,
        "roof_m": 0.12,
        "colour": "green",
        "roof": "green",
    },
}


def city_with(tmp_path, block: dict[str, Any] | None):
    document = yaml.safe_load(CITY_YAML)
    if block is not None:
        document["stops"] = block
    cities = tmp_path / "cities"
    cities.mkdir(exist_ok=True)
    (cities / "testville.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    return load_config(cities / "testville.yaml")


@pytest.fixture
def spec(tmp_path):
    return city_with(tmp_path, BLOCK).stops


def route(kind: str, *stops: tuple[str, float, float]) -> dict[str, Any]:
    return {"kind": kind, "stops": [{"stop_id": key, "plan": [x, z]} for key, x, z in stops]}


class TestWhereAFlagStands:
    def test_a_stop_many_routes_call_at_is_one_point(self):
        routes = {
            "routes": [
                route("bus", ("a", 1.0, 2.0), ("b", 5.0, 6.0)),
                route("bus", ("a", 1.0, 2.0)),
                route("minibus", ("m", 9.0, 9.0)),
                route("ferry", ("f", 0.0, 0.0)),
            ]
        }
        points = pole_points(routes, {})
        assert [tuple(point) for point in points[BUS]] == [(1.0, 2.0), (5.0, 6.0)]
        assert [tuple(point) for point in points[MINIBUS]] == [(9.0, 9.0)]
        assert points[TAXI] == []

    def test_a_taxi_point_takes_a_flag_and_a_taxi_stand_does_not(self):
        fares = {
            "nodes": [
                {"kind": "pudo", "pos": [3.0, 4.0, 5.0]},
                {"kind": "taxi_stand", "pos": [7.0, 4.0, 8.0]},
                {"kind": "poi", "pos": [9.0, 4.0, 9.0]},
            ]
        }
        assert [tuple(point) for point in pole_points({}, fares)[TAXI]] == [(3.0, 5.0)]

    def test_stops_a_pace_apart_share_a_pole(self):
        points = [np.array([0.0, 0.0]), np.array([3.0, 0.0]), np.array([9.0, 0.0])]
        kept, dropped = merged(points, 4.0)
        assert [tuple(point) for point in kept] == [(0.0, 0.0), (9.0, 0.0)]
        assert dropped == 1


class TestTheShelter:
    def track(self, *stops: tuple[str, float]) -> dict[str, Any]:
        # Eastward, +X: a game heading of 90.
        return {
            "points": [[0.0, 4.0, 0.0], [50.0, 4.0, 0.0], [100.0, 4.0, 0.0]],
            "stops": [{"id": key, "s_m": s_m} for key, s_m in stops],
        }

    def test_it_stands_on_the_tracks_left_at_the_stop(self, spec):
        report = StopReport()
        ((foot, heading),) = tram_stands({"tracks": [self.track(("a", 60.0))]}, spec.tram, report)
        assert heading == pytest.approx(90.0)
        # Eastbound, the left is north, and north is -Z.
        assert foot == pytest.approx([60.0, 4.0, -1.9])
        assert report.read == {TRAM_MESH_NAME: 1}

    def test_a_stop_two_tracks_serve_takes_one_shelter(self, spec):
        report = StopReport()
        tracks = {"tracks": [self.track(("a", 10.0)), self.track(("a", 20.0), ("b", 30.0))]}
        stands = tram_stands(tracks, spec.tram, report)
        assert [foot[0] for foot, _ in stands] == pytest.approx([10.0, 30.0])
        assert report.read == {TRAM_MESH_NAME: 2}

    def test_a_doubled_vertex_gives_no_heading_and_the_run_before_it_does(self, spec):
        track = {
            "points": [[0.0, 4.0, 0.0], [50.0, 4.0, 0.0], [50.0, 4.0, 0.0]],
            "stops": [{"id": "end", "s_m": 50.0}],
        }
        ((foot, heading),) = tram_stands({"tracks": [track]}, spec.tram, StopReport())
        assert heading == pytest.approx(90.0)
        assert foot == pytest.approx([50.0, 4.0, -1.9])

    def test_a_track_of_no_length_is_refused_once(self, spec):
        report = StopReport()
        empty = {"points": [], "stops": [{"id": "a", "s_m": 0.0}]}
        assert tram_stands({"tracks": [empty, empty]}, spec.tram, report) == []
        assert report.read == {TRAM_MESH_NAME: 1}
        assert report.refused == {TRAM_MESH_NAME: {"no_track": 1}}

    def test_its_length_runs_along_the_track(self, spec):
        mesh = shelter_mesh(spec, spec.tram, COLOURS)
        stood = placed_positions(mesh.positions, [0.0, 0.0, 0.0], 90.0)
        extent = stood.max(axis=0) - stood.min(axis=0)
        assert extent == pytest.approx([8.0, 2.8, 1.4])
        # Its feet are sunk, so the engine stands no post collider under it.
        assert stood[:, 1].min() < 0.0


class TestTheLibrary:
    def test_every_face_is_wound_outward(self, spec):
        meshes = [
            pole_mesh(spec, COLOURS),
            flag_mesh(spec, BUS, spec.flags[BUS], COLOURS),
            shelter_mesh(spec, spec.tram, COLOURS),
        ]
        assert [facing_away(mesh) for mesh in meshes] == [0, 0, 0]
        # Six faces a box: a pole is one, a flag two, a shelter three.
        assert [mesh.triangle_count for mesh in meshes] == [12, 24, 36]

    def test_the_pole_is_a_unit_a_stand_scales(self, spec):
        mesh = pole_mesh(spec, COLOURS)
        assert mesh.name == POLE_MESH_NAME
        low, high = mesh.aabb()
        assert (low[1], high[1]) == pytest.approx((0.0, 1.0))

    def test_the_flag_hangs_at_its_mount(self, spec):
        low, high = flag_mesh(spec, BUS, spec.flags[BUS], COLOURS).aabb()
        assert (low[1], high[1]) == pytest.approx((2.1, 2.9))
        assert high[0] - low[0] == pytest.approx(0.5)


class TestTheConfig:
    def test_no_block_is_no_furniture(self, tmp_path):
        assert city_with(tmp_path, None).stops is None

    def test_an_unknown_kind_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="is not one of"):
            city_with(tmp_path, {**BLOCK, "flags": {"ferry_pier": FLAG}})

    def test_a_flag_of_no_width_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="width_m"):
            city_with(tmp_path, {**BLOCK, "flags": {BUS: {**FLAG, "width_m": 0.0}}})

    def test_a_flag_hung_into_the_ground_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="hangs into the ground"):
            city_with(tmp_path, {**BLOCK, "flags": {BUS: {**FLAG, "mount_m": 0.2}}})

    def test_a_roof_deeper_than_the_shelter_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="roof_m"):
            city_with(tmp_path, {**BLOCK, "tram": {**BLOCK["tram"], "roof_m": 3.0}})

    def test_the_shelter_is_optional(self, tmp_path):
        body = {key: value for key, value in BLOCK.items() if key != "tram"}
        assert city_with(tmp_path, body).stops.tram is None
