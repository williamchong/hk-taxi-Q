"""Geodatabase reading and WKB decoding.

The WKB tests matter more than they look. Every coordinate in the road graph
comes through `_coordinates`, and the ways that can go wrong — a stride off by
eight bytes, a byte order assumed — do not raise. They produce a road network
somewhere plausible and wrong, which is the failure this project is most
exposed to.
"""

from __future__ import annotations

import struct
import zipfile

import numpy as np
import pytest

from pipeline import gdb
from tests.helpers import line_wkb, polygon_wkb, write_layer


def _layer(name: str, geometry: list[bytes]) -> gdb.Layer:
    return gdb.Layer(
        name=name, crs=None, fids=np.arange(len(geometry)), geometry=geometry, columns={}
    )


class TestPoints:
    """The point decoder (`P3-15`).

    ⚠️ **A point body carries no count prefix**, which is what makes it the one
    geometry here that cannot go through `_coordinates` — that reader would take
    the first eight bytes of the X ordinate as a length. Every test below is
    really about that, from a different angle.
    """

    def test_a_point_decodes_to_its_coordinate(self) -> None:
        wkb = struct.pack("<BI", 1, 1) + np.array([(1.5, 2.5)], dtype="<f8").tobytes()
        owners, plan = gdb.points(_layer("marks", [wkb]))

        assert owners.tolist() == [0]
        assert plan.tolist() == [[1.5, 2.5]]

    def test_a_multipoint_yields_one_part_per_point(self) -> None:
        parts = b"".join(
            struct.pack("<BI", 1, 1) + np.array([xy], dtype="<f8").tobytes()
            for xy in [(1.0, 2.0), (3.0, 4.0)]
        )
        wkb = struct.pack("<BII", 1, 4, 2) + parts
        owners, plan = gdb.points(_layer("marks", [wkb]))

        assert owners.tolist() == [0, 0]
        assert plan.tolist() == [[1.0, 2.0], [3.0, 4.0]]

    def test_rows_keep_their_owner_mapping(self) -> None:
        rows = [
            struct.pack("<BI", 1, 1) + np.array([(1.0, 1.0)], dtype="<f8").tobytes(),
            struct.pack("<BI", 1, 1) + np.array([(2.0, 2.0)], dtype="<f8").tobytes(),
        ]
        owners, plan = gdb.points(_layer("marks", rows))

        assert owners.tolist() == [0, 1]
        assert plan.tolist() == [[1.0, 1.0], [2.0, 2.0]]

    def test_big_endian_wkb_decodes_to_the_same_coordinate(self) -> None:
        wkb = struct.pack(">BI", 0, 1) + np.array([(1.5, 2.5)], dtype=">f8").tobytes()
        owners, plan = gdb.points(_layer("marks", [wkb]))

        assert owners.tolist() == [0]
        assert plan.tolist() == [[1.5, 2.5]]

    def test_a_z_point_is_strided_past_not_misread(self) -> None:
        """The X and Y that come back are the X and Y, not X and Z.

        The failure this rules out is the one `polylines` was bitten by before
        `Q57`: a reader striding 16 bytes through a 24-byte point returns
        coordinates that are wrong without being obviously wrong.
        """
        wkb = struct.pack("<BI", 1, 1001) + np.array([(1.0, 2.0, 99.0)], dtype="<f8").tobytes()
        _, plan = gdb.points(_layer("marks", [wkb]))

        assert plan.tolist() == [[1.0, 2.0]]

    def test_the_old_ogc_high_bit_also_marks_a_z_point(self) -> None:
        """GDAL's export writes the high-bit dialect, so this is the one that
        actually arrives from pyogrio."""
        wkb = (
            struct.pack("<BI", 1, 0x8000_0001) + np.array([(1.0, 2.0, 99.0)], dtype="<f8").tobytes()
        )
        _, plan = gdb.points(_layer("marks", [wkb]))

        assert plan.tolist() == [[1.0, 2.0]]

    def test_a_multipoint_may_mix_byte_orders_between_parts(self) -> None:
        little = struct.pack("<BI", 1, 1) + np.array([(1.0, 2.0)], dtype="<f8").tobytes()
        big = struct.pack(">BI", 0, 1) + np.array([(3.0, 4.0)], dtype=">f8").tobytes()
        wkb = struct.pack("<BII", 1, 4, 2) + little + big
        _, plan = gdb.points(_layer("marks", [wkb]))

        assert plan.tolist() == [[1.0, 2.0], [3.0, 4.0]]

    def test_a_linestring_where_a_point_was_expected_is_refused(self) -> None:
        wkb = struct.pack("<BII", 1, 2, 0)
        with pytest.raises(gdb.GeometryError, match="expected a point"):
            gdb.points(_layer("marks", [wkb]))

    def test_m_ordinates_are_still_refused_on_the_point_path(self) -> None:
        for kind in (2001, 3001, 0x4000_0001):
            wkb = struct.pack("<BI", 1, kind) + b"\x00" * 32
            with pytest.raises(gdb.GeometryError, match="M ordinates"):
                gdb.points(_layer("marks", [wkb]))

    def test_an_empty_point_is_passed_through_rather_than_refused(self) -> None:
        """⚠️ `POINT EMPTY` is spelled NaN in WKB, and the decoder is not where
        that judgement belongs — this module knows the container and nothing
        about what is in it. `arrows.py` counts them as `empty_geometry`."""
        wkb = struct.pack("<BI", 1, 1) + np.array([(np.nan, np.nan)], dtype="<f8").tobytes()
        _, plan = gdb.points(_layer("marks", [wkb]))

        assert np.isnan(plan).all()


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

    def test_a_z_linestring_is_strided_past_not_misread(self) -> None:
        """Masking the dimension flag off would leave the reader striding 16
        bytes through 24-byte points — wrong coordinates, no error. ⚠️ This path
        *refused* Z until `Q57`, which is what made iB1000's road margin
        unreadable while the `Building` polygons beside it had been read since
        `P3-7a`. It now strides like the polygon path and drops the Z column."""
        points = np.array([(1.0, 2.0, 9.0), (3.0, 4.0, 9.0)])
        wkb = struct.pack("<BII", 1, 1002, len(points)) + points.astype("<f8").tobytes()

        _, parts = gdb.polylines(_layer("l", [wkb]))
        np.testing.assert_array_equal(parts[0], points[:, :2])

    def test_the_old_ogc_high_bit_also_marks_a_z_linestring(self) -> None:
        """GDAL's export marks Z with the wkb25D high bit rather than the ISO
        offset, and it is the dialect pyogrio hands back for `CartoTransLine`.
        Both must decode to the same plan coordinates at the same 24-byte
        stride — the property `test_multipolygon_z_round_trips_through_gdal`
        pins for polygons, asserted here directly for lines."""
        points = np.array([(1.0, 2.0, 9.0), (3.0, 4.0, 9.0)])
        wkb = struct.pack("<BII", 1, 0x8000_0002, len(points)) + points.astype("<f8").tobytes()

        _, parts = gdb.polylines(_layer("l", [wkb]))
        np.testing.assert_array_equal(parts[0], points[:, :2])

    def test_a_multilinestring_may_mix_dimensionality_between_parts(self) -> None:
        """The outer header does not speak for the parts, so a 2D multilinestring
        can legally hold a Z part — the per-part header is the one that counts,
        and a reader that took the outer one would stride the Z part wrong."""
        flat = np.array([(1.0, 2.0), (3.0, 4.0)])
        tall = np.array([(5.0, 6.0, 9.0), (7.0, 8.0, 9.0)])
        first = struct.pack("<BII", 1, 2, len(flat)) + flat.astype("<f8").tobytes()
        second = struct.pack("<BII", 1, 1002, len(tall)) + tall.astype("<f8").tobytes()
        wkb = struct.pack("<BII", 1, 5, 2) + first + second

        _, parts = gdb.polylines(_layer("l", [wkb]))
        np.testing.assert_array_equal(parts[0], flat)
        np.testing.assert_array_equal(parts[1], tall[:, :2])

    def test_m_ordinates_are_still_refused_on_the_line_path(self) -> None:
        """Accepting Z must not have accepted M with it: `NSR` is a *Measured*
        MultiLineString, so this is a live dialect in the estate rather than a
        hypothetical, and a wrong stride returns coordinates that are wrong
        without being obviously wrong."""
        for kind in (2002, 3002, 0x4000_0002, 0xC000_0002):
            wkb = struct.pack("<BII", 1, kind, 0)
            with pytest.raises(gdb.GeometryError, match="M ordinates"):
                gdb.polylines(_layer("l", [wkb]))

    def test_a_polygon_where_a_line_was_expected_is_refused(self) -> None:
        wkb = struct.pack("<BI", 1, 3) + b"\x00" * 32
        with pytest.raises(gdb.GeometryError, match="expected a linestring"):
            gdb.polylines(_layer("l", [wkb]))


class TestPolygons:
    def test_a_polygon_decodes_to_its_ring(self) -> None:
        ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 0.0)]
        owners, parts = gdb.polygons(_layer("b", [polygon_wkb([ring])]))

        assert owners.tolist() == [0]
        assert len(parts[0]) == 1
        np.testing.assert_array_equal(parts[0][0], np.array(ring))

    def test_a_hole_is_returned_after_its_outer_ring(self) -> None:
        """WKB fixes the outer ring first; a caller doing containment relies on
        that ordering to tell a boundary from a hole."""
        outer = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        hole = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0), (4.0, 4.0)]
        _, parts = gdb.polygons(_layer("b", [polygon_wkb([outer, hole])]))

        assert len(parts[0]) == 2
        np.testing.assert_array_equal(parts[0][0], np.array(outer))
        np.testing.assert_array_equal(parts[0][1], np.array(hole))

    def test_a_multipolygon_yields_one_part_per_footprint(self) -> None:
        """Two footprints sharing a database row are separate buildings that
        happen to be surveyed as one feature; merging them would invent floor
        area between them, exactly as concatenating line parts invents road."""
        near = [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0)]]
        far = [[(50.0, 0.0), (51.0, 0.0), (51.0, 1.0), (50.0, 0.0)]]
        owners, parts = gdb.polygons(_layer("b", [polygon_wkb(near, far)]))

        assert owners.tolist() == [0, 0]
        assert len(parts) == 2
        np.testing.assert_array_equal(parts[1][0], np.array(far[0]))

    def test_rows_keep_their_owner_mapping(self) -> None:
        first = [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0)]]
        second = [[(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 2.0)]]
        owners, parts = gdb.polygons(_layer("b", [polygon_wkb(first), polygon_wkb(second)]))

        assert owners.tolist() == [0, 1]
        assert parts[1][0][0].tolist() == [2.0, 2.0]

    def test_a_multipolygon_may_mix_byte_orders_between_parts(self) -> None:
        """As with multilinestrings: each part carries its own byte-order flag,
        and the outer header does not speak for the parts."""
        little = polygon_wkb([[(1.0, 2.0), (3.0, 4.0), (5.0, 6.0), (1.0, 2.0)]])
        big = polygon_wkb([[(7.0, 8.0), (9.0, 10.0), (11.0, 12.0), (7.0, 8.0)]], big_endian=True)
        wkb = struct.pack("<BII", 1, 6, 2) + little + big

        _, parts = gdb.polygons(_layer("b", [wkb]))
        np.testing.assert_array_equal(parts[0][0][1], np.array([3.0, 4.0]))
        np.testing.assert_array_equal(parts[1][0][1], np.array([9.0, 10.0]))

    def test_z_coordinates_are_strided_past_not_misread(self) -> None:
        """The load-bearing case. A reader that noticed Z but kept a 16-byte
        stride would return these z values as the next point's x — plausible
        coordinates, no error. The plan positions must come back exact."""
        ring = [(1.0, 2.0, 100.0), (3.0, 4.0, 200.0), (5.0, 6.0, 300.0), (1.0, 2.0, 100.0)]
        _, parts = gdb.polygons(_layer("b", [polygon_wkb([ring])]))

        np.testing.assert_array_equal(
            parts[0][0], np.array([(1.0, 2.0), (3.0, 4.0), (5.0, 6.0), (1.0, 2.0)])
        )

    def test_a_multipolygon_z_decodes_each_part_at_its_own_stride(self) -> None:
        one = [[(1.0, 2.0, 9.0), (3.0, 4.0, 9.0), (5.0, 6.0, 9.0), (1.0, 2.0, 9.0)]]
        two = [[(7.0, 8.0, 9.0), (9.0, 10.0, 9.0), (11.0, 12.0, 9.0), (7.0, 8.0, 9.0)]]
        owners, parts = gdb.polygons(_layer("b", [polygon_wkb(one, two)]))

        assert owners.tolist() == [0, 0]
        np.testing.assert_array_equal(parts[1][0][0], np.array([7.0, 8.0]))

    def test_m_ordinates_are_refused_in_both_dialects(self) -> None:
        """Nothing in the pipeline reads measures, and a wrong stride returns
        coordinates that are wrong without being obviously wrong."""
        for kind in (2003, 3003, 0x4000_0003, 0xC000_0003):
            wkb = struct.pack("<BII", 1, kind, 0)
            with pytest.raises(gdb.GeometryError, match="M ordinates"):
                gdb.polygons(_layer("b", [wkb]))

    def test_the_old_ogc_high_bit_also_marks_z(self) -> None:
        """GDAL's export marks Z with the wkb25D high bit rather than the ISO
        offset — it is the dialect pyogrio actually hands back, so both must
        decode to the same plan coordinates at the same 24-byte stride."""
        ring = np.array([(1.0, 2.0, 9.0), (3.0, 4.0, 9.0), (5.0, 6.0, 9.0), (1.0, 2.0, 9.0)])
        wkb = struct.pack("<BIII", 1, 0x8000_0003, 1, len(ring)) + ring.astype("<f8").tobytes()

        _, parts = gdb.polygons(_layer("b", [wkb]))
        np.testing.assert_array_equal(parts[0][0], ring[:, :2])

    def test_an_embedded_srid_is_refused(self) -> None:
        """The EWKB SRID flag inserts four bytes into the header itself; a
        reader that ignored it would parse the SRID as a part count."""
        wkb = struct.pack("<BII", 1, 0x2000_0003, 0)
        with pytest.raises(gdb.GeometryError, match="SRID"):
            gdb.polygons(_layer("b", [wkb]))

    def test_a_linestring_where_a_polygon_was_expected_is_refused(self) -> None:
        with pytest.raises(gdb.GeometryError, match="expected a polygon"):
            gdb.polygons(_layer("b", [line_wkb([(0.0, 0.0), (1.0, 1.0)])]))

    def test_a_zero_ring_polygon_contributes_no_part(self) -> None:
        """OGR writes an empty geometry as a polygon with no rings; it must not
        shift the owner mapping of the rows behind it."""
        empty = struct.pack("<BII", 1, 3, 0)
        real = polygon_wkb([[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0)]])
        owners, parts = gdb.polygons(_layer("b", [empty, real]))

        assert owners.tolist() == [1]
        assert len(parts) == 1


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

    def test_multipolygon_z_round_trips_through_gdal(self, tmp_path) -> None:
        """Written through pyogrio and read back through the same GDAL that
        reads the real geodatabase — the property `write_layer` exists for.
        The topographic source's blocks arrive exactly this shape: multipolygon
        Z geometry whose vertical extent lives in attribute columns."""
        path = tmp_path / "blocks.gpkg"
        tower = [(10.0, 20.0, 5.5), (30.0, 20.0, 5.5), (30.0, 40.0, 5.5), (10.0, 20.0, 5.5)]
        podium = [(50.0, 20.0, 3.7), (70.0, 20.0, 3.7), (70.0, 40.0, 3.7), (50.0, 20.0, 3.7)]
        write_layer(
            path,
            "Building",
            [polygon_wkb([tower], [podium])],
            {"ROOFLEVEL": np.array([75.6])},
            geometry_type="MultiPolygon Z",
        )

        layer = gdb.read_layer(path, "Building", columns=["ROOFLEVEL"])
        owners, parts = gdb.polygons(layer)

        assert layer.crs == "EPSG:2326"
        assert layer.column("ROOFLEVEL").tolist() == [75.6]
        assert owners.tolist() == [0, 0]
        np.testing.assert_array_equal(
            parts[1][0], np.array([(50.0, 20.0), (70.0, 20.0), (70.0, 40.0), (50.0, 20.0)])
        )

    def test_a_zip_member_reaches_a_nested_geodatabase(self, tmp_path) -> None:
        """The topographic publisher zips its geodatabase under a directory
        rather than at the archive root, so the reader must be able to name the
        member — a GeoPackage stands in for the geodatabase here, which is the
        container `/vsizip/` cares about, not the format inside."""
        inner = tmp_path / "inner.gpkg"
        write_layer(
            inner,
            "Building",
            [line_wkb([(0.0, 0.0), (1.0, 1.0)])],
            {"KIND": np.array(["T"], dtype=object)},
        )
        archive = tmp_path / "sheet.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.write(inner, "sheet/sheet.gpkg")

        layer = gdb.read_layer(archive, "Building", columns=["KIND"], zip_member="sheet/sheet.gpkg")

        assert len(layer) == 1
        assert layer.column("KIND").tolist() == ["T"]

    def test_a_zip_member_that_escapes_its_archive_is_refused(self, tmp_path) -> None:
        """The member is formatted with a tile id that originated in a remote
        index; a publisher's index must not be able to name a path outside the
        archive it came with."""
        for member in ("../evil.gdb", "/evil.gdb", "a/../../evil.gdb"):
            with pytest.raises(ValueError, match="escapes"):
                gdb.read_layer(tmp_path / "sheet.zip", "Building", columns=[], zip_member=member)
