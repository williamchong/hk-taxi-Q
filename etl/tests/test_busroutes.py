"""`pipeline/busroutes.py` (`P3-78`, `Q182`): the headways and the stop snap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest

from pipeline.busroutes import (
    BUS_ROUTES_NAME,
    BUSROUTES_MANIFEST_NAME,
    HOURS,
    BusRoutesReport,
    _write_manifest,
    departures_per_hour,
    read_directions,
    snap_stop,
)
from pipeline.config import load_config
from pipeline.fetch import artefact_path, source_artefact
from pipeline.polyline import Segments


@pytest.fixture(scope="module")
def city():
    return load_config()


def _put(city, root: Path, source: str, text: str) -> None:
    path = artefact_path(source_artefact(source, city.sources[source]), root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _headways(city, root: Path, trips: str, frequencies: str) -> dict[str, list[int]]:
    spec = city.bus_routes
    days = "monday,tuesday,wednesday,thursday,friday,saturday,sunday"
    _put(
        city,
        root,
        spec.calendar,
        # The publisher's byte-order mark and CRLF, as fetched.
        f"﻿service_id,{days},start_date,end_date\r\n"
        "31,1,1,1,1,1,0,0,20200101,20991231\r\n"
        "64,0,0,0,0,0,0,1,20200101,20991231\r\n",
    )
    _put(city, root, spec.trips, "route_id,service_id,trip_id\r\n" + trips)
    _put(city, root, spec.frequencies, "trip_id,start_time,end_time,headway_secs\r\n" + frequencies)
    return departures_per_hour(city, spec, root=root)


class TestHeadways:
    def test_a_frequency_row_departs_every_headway_until_its_end(self, city, tmp_path) -> None:
        counts = _headways(
            city,
            tmp_path,
            "7,31,7-1-31-0700\r\n",
            # 07:00, 07:20, 07:40, 08:00 — the end is exclusive, so not 08:20.
            "7-1-31-0700,07:00:00,08:20:00,1200\r\n",
        )
        assert counts["7-1"][7] == 3
        assert counts["7-1"][8] == 1
        assert sum(counts["7-1"]) == 4

    def test_a_trip_with_no_frequency_row_departs_once_at_its_id(self, city, tmp_path) -> None:
        counts = _headways(city, tmp_path, "7,31,7-2-31-1815\r\n", "")
        assert counts["7-2"][18] == 1
        assert sum(counts["7-2"]) == 1

    def test_a_trip_not_running_on_the_service_day_counts_nothing(self, city, tmp_path) -> None:
        counts = _headways(city, tmp_path, "7,64,7-1-64-0900\r\n", "")
        assert "7-1" not in counts

    def test_past_midnight_folds_back_onto_the_clock(self, city, tmp_path) -> None:
        counts = _headways(
            city,
            tmp_path,
            "9,31,9-1-31-2330\r\n",
            "9-1-31-2330,23:30:00,24:40:00,1800\r\n",
        )
        # 23:30, then 24:00 and 24:30 on the next day's clock.
        assert counts["9-1"][23] == 1
        assert counts["9-1"][0] == 2
        assert len(counts["9-1"]) == HOURS

    def test_the_bound_is_the_trip_ids_not_the_routes(self, city, tmp_path) -> None:
        counts = _headways(city, tmp_path, "7,31,7-1-31-0700\r\n7,31,7-2-31-0700\r\n", "")
        assert set(counts) == {"7-1", "7-2"}


class TestDirections:
    def test_stops_are_ordered_by_seq_and_keyed_by_bound(self, city, tmp_path) -> None:
        spec = city.bus_routes

        def stop(seq: int, bound: int, route: int = 5) -> dict:
            return {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [114.18, 22.28]},
                "properties": {
                    "routeId": route,
                    "routeSeq": bound,
                    "stopSeq": seq,
                    "stopId": 100 + seq,
                    "routeNameE": "5B",
                    "companyCode": "CTB",
                },
            }

        for route_set in spec.sets:
            # The minibus set carries a route of its own: an empty file is refused as an
            # error page (`read_feature_collection`).
            bus = route_set.kind == "bus"
            features = [stop(2, 1), stop(1, 1), stop(1, 2)] if bus else [stop(1, 1, route=7)]
            _put(
                city,
                tmp_path,
                route_set.source,
                "﻿" + json.dumps({"type": "FeatureCollection", "features": features}),
            )
        directions = read_directions(city, spec, root=tmp_path)
        assert sorted(direction.key for direction in directions) == ["5-1", "5-2", "7-1"]
        directions = [direction for direction in directions if direction.kind == "bus"]
        assert [direction.key for direction in directions] == ["5-1", "5-2"]
        assert [stop.seq for stop in directions[0].stops] == [1, 2]
        assert directions[0].kind == "bus"
        assert directions[0].name == "5B"


class _Ribbon:
    """A ribbon whose road is centred on its edge, 6 m each side."""

    def kerb_at(self, t: float) -> tuple[float, float]:
        return 0.0, 6.0


class TestSnap:
    # An edge running +x; left of travel is `(step_z, -step_x)`, so -z.
    EDGE: ClassVar[dict] = {"id": 3, "polyline": [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]]}

    def _snap(self, z: float, direction: str, max_snap_m: float = 12.0):
        segments = Segments.of([self.EDGE])
        edges = {3: {**self.EDGE, "direction": direction}}
        return snap_stop(segments, {3: _Ribbon()}, edges, 40.0, z, max_snap_m)

    def test_the_nearside_of_a_two_way_road_runs_with_the_edge(self) -> None:
        snapped = self._snap(-4.0, "both")
        assert snapped is not None
        assert snapped["side"] == 1
        assert snapped["along"] is True
        assert snapped["t"] == pytest.approx(0.4)

    def test_the_offside_of_a_two_way_road_runs_against_it(self) -> None:
        snapped = self._snap(4.0, "both")
        assert snapped is not None
        assert snapped["side"] == -1
        assert snapped["along"] is False

    def test_both_kerbs_of_a_one_way_road_run_its_way(self) -> None:
        snapped = self._snap(4.0, "forward")
        assert snapped is not None
        assert snapped["side"] == -1
        assert snapped["along"] is True

    def test_a_stop_past_the_snap_is_refused(self) -> None:
        assert self._snap(-13.0, "both") is None


class TestTheManifest:
    def test_a_build_that_keeps_no_route_leaves_no_route_document(self, city, tmp_path) -> None:
        # A stale `bus_routes.json` would lay buses over at its termini
        # (`parked`), whatever this build kept (the review, 2026-11-06).
        stale = tmp_path / BUS_ROUTES_NAME
        stale.write_text("{}", encoding="utf-8")
        _write_manifest(tmp_path, city, "wan_chai", BusRoutesReport(), wrote=False)
        assert not stale.exists()
        manifest = json.loads((tmp_path / BUSROUTES_MANIFEST_NAME).read_text(encoding="utf-8"))
        assert manifest["document"] is None
