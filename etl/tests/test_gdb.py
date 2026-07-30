"""Geodatabase reading and WKB decoding.

The WKB tests matter more than they look. Every coordinate in the road graph
comes through `_coordinates`, and the ways that can go wrong — a stride off by
eight bytes, a byte order assumed — do not raise. They produce a road network
somewhere plausible and wrong, which is the failure this project is most
exposed to.
"""

from __future__ import annotations

import struct

import numpy as np
import pytest

from pipeline import gdb
from tests.helpers import line_wkb, write_layer


def _layer(name: str, geometry: list[bytes]) -> gdb.Layer:
    return gdb.Layer(
        name=name, crs=None, fids=np.arange(len(geometry)), geometry=geometry, columns={}
    )


class TestPolylines:
    def test_a_linestring_decodes_to_its_coordinates(self) -> None:
        points = [(1.5, 2.5), (3.0, 4.0), (5.0, 6.0)]
        owners, parts = gdb.polylines(_layer("l", [line_wkb(points)]))

        assert owners.tolist() == [0]
        np.testing.assert_array_equal(parts[0], np.array(points))

    def test_a_multilinestring_yields_one_part_per_run(self) -> None:
        """Concatenating the parts would draw a road across the gap between
        them. Each part is its own edge, tagged with the row it came from."""
        wkb = line_wkb([(0.0, 0.0), (1.0, 0.0)], [(50.0, 0.0), (51.0, 0.0)])
        owners, parts = gdb.polylines(_layer("l", [wkb]))

        assert owners.tolist() == [0, 0]
        assert len(parts) == 2
        np.testing.assert_array_equal(parts[1], np.array([(50.0, 0.0), (51.0, 0.0)]))

    def test_rows_without_geometry_do_not_shift_the_owner_mapping(self) -> None:
        wkb = [line_wkb([(0.0, 0.0), (1.0, 1.0)]), line_wkb([(2.0, 2.0), (3.0, 3.0)])]
        owners, parts = gdb.polylines(_layer("l", wkb))

        assert owners.tolist() == [0, 1]
        assert parts[1][0].tolist() == [2.0, 2.0]

    def test_big_endian_wkb_decodes_to_the_same_coordinates(self) -> None:
        points = [(836000.25, 816000.5), (836001.0, 816002.0)]
        _, little = gdb.polylines(_layer("l", [line_wkb(points)]))
        _, big = gdb.polylines(_layer("l", [line_wkb(points, big_endian=True)]))

        np.testing.assert_array_equal(little[0], big[0])

    def test_a_multilinestring_may_mix_byte_orders_between_parts(self) -> None:
        """The outer header does not speak for the parts: WKB gives each nested
        geometry its own byte-order flag, and a reader that assumes otherwise
        returns garbage rather than an error."""
        first = (
            struct.pack("<BII", 1, 2, 2) + np.array([(1.0, 2.0), (3.0, 4.0)], dtype="<f8").tobytes()
        )
        second = (
            struct.pack(">BII", 0, 2, 2) + np.array([(5.0, 6.0), (7.0, 8.0)], dtype=">f8").tobytes()
        )
        wkb = struct.pack("<BII", 1, 5, 2) + first + second

        _, parts = gdb.polylines(_layer("l", [wkb]))
        np.testing.assert_array_equal(parts[0], np.array([(1.0, 2.0), (3.0, 4.0)]))
        np.testing.assert_array_equal(parts[1], np.array([(5.0, 6.0), (7.0, 8.0)]))

    def test_a_z_geometry_is_refused_rather_than_misread(self) -> None:
        """Masking the dimension flag off would leave the reader striding 16
        bytes through 24-byte points — wrong coordinates, no error."""
        wkb = struct.pack("<BII", 1, 1002, 2) + np.zeros(6, dtype="<f8").tobytes()
        with pytest.raises(gdb.GeometryError, match="Z or M"):
            gdb.polylines(_layer("l", [wkb]))

    def test_a_polygon_where_a_line_was_expected_is_refused(self) -> None:
        wkb = struct.pack("<BI", 1, 3) + b"\x00" * 32
        with pytest.raises(gdb.GeometryError, match="expected a linestring"):
            gdb.polylines(_layer("l", [wkb]))


class TestReadLayer:
    def test_reads_geometry_columns_and_feature_ids(self, tmp_path) -> None:
        path = tmp_path / "roads.gpkg"
        write_layer(
            path,
            "CENTERLINE",
            [line_wkb([(0.0, 0.0), (10.0, 0.0)]), line_wkb([(10.0, 0.0), (10.0, 10.0)])],
            {"ELEVATION": np.array([0, 1]), "NAME": np.array(["A", "B"], dtype=object)},
        )

        layer = gdb.read_layer(path, "CENTERLINE", columns=["ELEVATION", "NAME"])

        assert len(layer) == 2
        assert layer.crs == "EPSG:2326"
        assert layer.column("ELEVATION").tolist() == [0, 1]

    def test_the_bounding_box_selects_and_keeps_feature_ids(self, tmp_path) -> None:
        """Ids must survive a filtered read unchanged — the turn layer points at
        centrelines by id, and a read that renumbered them would resolve every
        restriction onto the wrong pair of roads."""
        path = tmp_path / "roads.gpkg"
        write_layer(
            path,
            "CENTERLINE",
            [line_wkb([(0.0, 0.0), (1.0, 0.0)]), line_wkb([(500.0, 500.0), (501.0, 500.0)])],
            {"ELEVATION": np.array([0, 0])},
        )

        everything = gdb.read_layer(path, "CENTERLINE", columns=["ELEVATION"])
        near = gdb.read_layer(
            path, "CENTERLINE", columns=["ELEVATION"], bbox=(400.0, 400.0, 600.0, 600.0)
        )

        assert len(near) == 1
        assert near.fids.tolist() == [everything.fids[1]]

    def test_an_unknown_column_is_an_error_not_a_silent_drop(self, tmp_path) -> None:
        """OGR drops a column it does not recognise without complaint, so a
        renamed field upstream would arrive as an attribute that is uniformly
        null several stages downstream."""
        path = tmp_path / "roads.gpkg"
        write_layer(
            path, "CENTERLINE", [line_wkb([(0.0, 0.0), (1.0, 1.0)])], {"ELEVATION": np.array([0])}
        )

        with pytest.raises(KeyError, match="TRAVEL_DIRECTION"):
            gdb.read_layer(path, "CENTERLINE", columns=["ELEVATION", "TRAVEL_DIRECTION"])

    def test_an_unread_column_is_named_in_the_error(self, tmp_path) -> None:
        path = tmp_path / "roads.gpkg"
        write_layer(
            path, "CENTERLINE", [line_wkb([(0.0, 0.0), (1.0, 1.0)])], {"ELEVATION": np.array([0])}
        )
        layer = gdb.read_layer(path, "CENTERLINE", columns=["ELEVATION"])

        with pytest.raises(KeyError, match="ELEVATION"):
            layer.column("MISSING")
