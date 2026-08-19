"""Mesh- and vector-shaped test helpers.

A plain module, not `conftest.py`, because these are imported by name. pytest
imports `conftest.py` as top-level `conftest` while an `import tests.conftest`
creates a *second* module object — so anything living in both places exists
twice, and only pytest's copy of a fixture is a working fixture.
"""

from __future__ import annotations

import struct
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
from pyogrio.raw import write as _ogr_write

from pipeline.config import BuildingStyle, HeightBand, Material, MaterialAssignment
from pipeline.gltf import MeshData
from pipeline.terrain import HeightField

# The six faces of an axis-aligned box, over corners ordered x-outer, y-middle,
# z-inner. Each face is a quad; callers decide how to triangulate it.
BOX_FACES = [
    ((0, 1, 3, 2), (-1, 0, 0)),
    ((4, 6, 7, 5), (1, 0, 0)),
    ((0, 4, 5, 1), (0, -1, 0)),
    ((2, 3, 7, 6), (0, 1, 0)),
    ((0, 2, 6, 4), (0, 0, -1)),
    ((1, 5, 7, 3), (0, 0, 1)),
]


def box_corners(low: tuple[float, float, float], high: tuple[float, float, float]) -> np.ndarray:
    """The eight corners of a box, in the order `BOX_FACES` indexes."""
    return np.array(
        [
            [x, y, z]
            for x in (low[0], high[0])
            for y in (low[1], high[1])
            for z in (low[2], high[2])
        ],
        dtype=np.float64,
    )


def box_soup(corners: np.ndarray) -> tuple[list, list]:
    """A box's 36 positions and matching face normals, vertices unshared.

    Unshared on purpose: every vertex repeated per face so each carries its own
    face normal. That repetition is exactly what LOD0's exact weld exists to
    remove, so a test must not start from a welded box.
    """
    positions, normals = [], []
    for (a, b, c, d), normal in BOX_FACES:
        for index in (a, b, c, a, c, d):
            positions.append(corners[index])
            normals.append(normal)
    return positions, normals


def soup(
    corners: list[list[tuple[float, float, float]]],
    *,
    name: str,
    normals: np.ndarray | None = None,
    colour: tuple[int, int, int, int] | None = None,
) -> MeshData:
    """Triangle soup from a list of corner triples, vertices unshared.

    The assembly three fixtures had each written out: flatten to float64
    positions, number the triangles, and repeat one normal per vertex. Shared
    because the *shapes* differ — a box, a ramp, a sub-cell sheet — while this
    never does, and because `MeshData`'s invariants are easier to break by hand
    than to notice.

    `normals` is per *triangle* and is repeated three times; omit it for the
    flat +Y that a height-field fixture wants, where the normal is not what is
    under test. Pass `normalise(triangle_cross(...))` where it is.
    """
    positions = np.array([corner for face in corners for corner in face], dtype=np.float64)
    triangles = np.arange(len(positions), dtype=np.uint32).reshape(-1, 3)
    if normals is None:
        normals = np.tile(np.array([0.0, 1.0, 0.0], np.float32), (len(triangles), 1))
    return MeshData(
        name=name,
        positions=positions,
        normals=np.repeat(normals, 3, axis=0).astype(np.float32),
        triangles=triangles,
        colours=(
            None if colour is None else np.tile(np.array(colour, np.uint8), (len(positions), 1))
        ),
    )


def covered(meshes: list[MeshData], xs: np.ndarray, zs: np.ndarray) -> np.ndarray:
    """Which of a plan lattice has surface over it, as a boolean mask.

    ⚠️ **Coverage, not triangle count.** A tear in a decimated sheet does not
    have to drop a triangle — it pulls the two sides apart to different cluster
    means and leaves a wedge of plan with nothing above it, which a triangle
    count reports as absent. This is the same question `tools/ground_clearance.py`
    asks of the shipped bundle, through the same height-field query.
    """
    grid_x, grid_z = np.meshgrid(xs, zs)
    return np.isfinite(HeightField.from_meshes(meshes).sample(grid_x.ravel(), grid_z.ravel()))


def box(
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
    size: float = 10.0,
    *,
    colour: tuple[int, int, int, int] = (200, 190, 180, 255),
) -> MeshData:
    """An axis-aligned box in game space, unwelded and flat-shaded."""
    corners = box_corners(origin, tuple(value + size for value in origin))
    positions, normals = box_soup(corners)

    return MeshData(
        name="box",
        positions=np.array(positions, dtype=np.float64),
        normals=np.array(normals, dtype=np.float32),
        triangles=np.arange(36, dtype=np.uint32).reshape(-1, 3),
        colours=np.tile(np.array(colour, np.uint8), (36, 1)),
    )


def flat_mesh(name: str, height: float) -> MeshData:
    """One triangle of a given height, named — the smallest thing `colour_for`
    and `facade_uv` will read a band and a seed off."""
    positions = np.array([[0, 0, 0], [1, 0, 0], [0, height, 0]], dtype=np.float64)
    return MeshData(
        name=name,
        positions=positions,
        normals=np.zeros((3, 3), dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
    )


def style(jitter: float = 0.0) -> BuildingStyle:
    """A minimal two-band building style. `replace()` it for anything else.

    The `reflectance` values are plausible materials rather than values
    consistent with these colours, and deliberately so: `Q33`'s rule is enforced
    by `load_city`, which a hand-built style never goes through. Made consistent
    at any sane anchor these colours would need over 100% albedo, which is the
    honest signal that they are arbitrary test values and not a palette.
    """
    return BuildingStyle(
        classes=("BUILDING", "INFRASTRUCTURE"),
        terrain_class="TERRAIN",
        structure_class=None,
        class_materials={
            "INFRASTRUCTURE": Material(
                name="structure", colour=(100, 100, 100), reflectance=22.0, source="test"
            )
        },
        material_assignment=MaterialAssignment(
            by_height=(
                HeightBand(
                    up_to_m=12.0,
                    material=Material(
                        name="low", colour=(200, 180, 150), reflectance=48.0, source="test"
                    ),
                ),
                HeightBand(
                    up_to_m=float("inf"),
                    material=Material(
                        name="high", colour=(190, 200, 200), reflectance=55.0, source="test"
                    ),
                ),
            ),
            # No surveyed rule: the default style takes the height ramp for every
            # building, surveyed or not, which is what most of these tests mean.
            rings=(),
        ),
        colour_jitter=jitter,
        class_colour_jitter={},
        lod_cell_sizes_m=(0.0,),
        class_lod_cell_sizes_m={},
        ground_sink_m=0.0,
    )


# --------------------------------------------------------------------------
# Vector geometry, for `gdb.py` and `roads.py`
# --------------------------------------------------------------------------


# Every spelling of Road Network v2's null sentinel for a text field. Written
# as escapes rather than literally: the difference between an en-dash and a
# hyphen, or a full-width digit and an ASCII one, is exactly what these test
# and exactly what is invisible in a source file.
NULL_SENTINELS = (
    "-99",
    "\u2013\uff19\uff19",  # en-dash, full-width nines
    "\uff0d\uff19\uff19",  # full-width hyphen and nines
    "-\uff19\uff19",  # ASCII hyphen, full-width nines
)


def line_wkb(*parts: object, big_endian: bool = False) -> bytes:
    """A 2D LineString or MultiLineString as WKB.

    One part gives a plain LineString, several give a MultiLineString, so a test
    can exercise either shape without a second helper.
    """
    order, prefix = (0, ">") if big_endian else (1, "<")
    blocks = [_line_block(np.asarray(part, dtype=np.float64), order, prefix) for part in parts]
    if len(blocks) == 1:
        return blocks[0]
    return struct.pack(f"{prefix}BII", order, 5, len(blocks)) + b"".join(blocks)


def _line_block(points: np.ndarray, order: int, prefix: str) -> bytes:
    body = points.astype(f"{prefix}f8", copy=False).tobytes()
    return struct.pack(f"{prefix}BII", order, 2, len(points)) + body


def polygon_wkb(*parts: object, big_endian: bool = False) -> bytes:
    """A Polygon or MultiPolygon as WKB, plan or Z.

    Each part is a list of rings, each ring a list of `(x, y)` or `(x, y, z)`
    points — Z is inferred from the point width, so a test exercises the
    24-byte stride simply by handing three-wide points. One part gives a plain
    Polygon, several give a MultiPolygon, mirroring `line_wkb`.
    """
    order, prefix = (0, ">") if big_endian else (1, "<")
    blocks: list[bytes] = []
    z_flags: list[bool] = []
    for part in parts:
        block, has_z = _polygon_block(part, order, prefix)
        blocks.append(block)
        z_flags.append(has_z)
    if len(blocks) == 1:
        return blocks[0]
    outer = 1006 if any(z_flags) else 6
    return struct.pack(f"{prefix}BII", order, outer, len(blocks)) + b"".join(blocks)


def _polygon_block(rings: object, order: int, prefix: str) -> tuple[bytes, bool]:
    arrays = [np.asarray(ring, dtype=np.float64) for ring in rings]
    has_z = bool(arrays) and arrays[0].shape[1] == 3
    body = b"".join(
        struct.pack(f"{prefix}I", len(ring)) + ring.astype(f"{prefix}f8", copy=False).tobytes()
        for ring in arrays
    )
    kind = 1003 if has_z else 3
    return struct.pack(f"{prefix}BII", order, kind, len(arrays)) + body, has_z


def write_layer(
    path: Path,
    layer: str,
    geometry: list[bytes],
    columns: dict[str, Any],
    *,
    geometry_type: str = "LineString",
    crs: str = "EPSG:2326",
) -> None:
    """Append one layer of WKB features to a GeoPackage.

    Built through pyogrio's raw writer rather than a checked-in fixture file, so
    the tests read their input back through the same GDAL that reads the real
    geodatabase — a fixture would only prove that the parser agrees with itself.
    """
    fields = np.array(list(columns), dtype=object)
    field_data = [np.asarray(values) for values in columns.values()]
    _ogr_write(
        str(path),
        geometry=np.array(geometry, dtype=object),
        field_data=field_data,
        fields=fields,
        layer=layer,
        driver="GPKG",
        geometry_type=geometry_type,
        crs=crs,
        append=path.exists(),
    )


# A 1 km square of made-up city, far enough east to be inside the declared
# bounds and metric throughout, so expected coordinates can be worked out by
# hand rather than read back off the output.
#
# Shared by the road-graph and road-surface tests, which is the point: the
# two stages are a pipeline, and a fixture city that drifted between them
# would let the second stage pass against a city the first never built.
CITY_YAML = textwrap.dedent(
    """
    schema_version: 3
    id: testville
    name: Testville
    # Deliberately 1.0 where Hong Kong ships 0.520, so the fixture proves the
    # palette rule (`Q33`) is portable rather than a Hong Kong constant. At a
    # unit anchor a declared reflectance *is* the colour's luminance, which
    # keeps this city hand-checkable in the way the rest of it already is.
    exposure_anchor: 1.0
    # Every colour Testville ships (`Q34`). Three, because three things reference
    # one: the single height band, and the two road surfaces. Declaring a fourth
    # would fail `_check_every_material_is_used`, which is the point of it.
    materials:
      facade: {colour: "#808080", reflectance: 21.59, source: "test fixture"}
      asphalt: {colour: "#3c3a37", reflectance: 4.26, source: "test fixture"}
      kerb: {colour: "#9a968d", reflectance: 30.61, source: "test fixture"}
    crs:
      projected: EPSG:2326
      geodetic: EPSG:4326
    elevation_levels:
      -1: -8.0
      0: 0.0
      1: 6.0
    bounds: {west: 114.00, east: 114.30, south: 22.20, north: 22.40}
    regions:
      middle:
        name: Middle
        bounds: {west: 114.170, east: 114.180, south: 22.276, north: 22.282}
        tile_size_m: 150.0
    sources:
      roads: https://example.test/roads.gpkg
      stands: https://example.test/stands.geojson
      points: https://example.test/points.geojson
    buildings:
      classes: [BUILDING]
      terrain_class: TERRAIN
      class_materials: {}
      material_assignment:
        unsurveyed:
          by_height:
            - {up_to_m: .inf, material: facade}
      colour_jitter: 0.0
      lod_cell_sizes_m: [0.0]
    roads:
      source: roads
      centrelines:
        layer: CENTERLINE
        fields:
          elevation: ELEVATION
          travel_direction: TRAVEL_DIRECTION
          route: ROUTE_ID
          name_en: STREET_ENAME
          name_zh: STREET_CNAME
      turns:
        layer: TURN
        fields:
          first_edge: EDGE1FID
          first_end: EDGE1END
          second_edge: EDGE2FID
      speed_limits:
        layer: SPEED_LIMIT
        fields: {route: ROAD_ROUTE_ID, speed_limit: SPEED_LIMIT}
      bus_lanes:
        layer: BUS_ONLY_LANE
        fields: {route: ROAD_ROUTE_ID}
      kerbside_restrictions:
        layer: NSR
        fields: {vehicle_type: VEHICLE_TYPE, time_zone: TIME_ZONE}
        painted_vehicle_types: [1]
        kinds: {1: double, 3: single, 4: single}
        sample_m: 1.0
        bridge_gap_m: 3.0
        min_run_m: 5.0
        max_offset_m: 20.0
      travel_directions:
        1: both
        3: forward
      turn_at_end_value: "Y"
      null_values: ["-99"]
      default_speed_limit_kph: 50
      simplify_tolerance_m: 0.2
      min_edge_length_m: 2.0
      lanes_default: 2
      lanes_by_min_speed_limit_kph: {70: 3}
      lane_width_m: 3.2
      tram_streets: [TRAM STREET]
      ground: datum
      surface:
        widen_default: 1.5
        widen_by_min_speed_limit_kph: {70: 1.2}
        widen_by_elevation_level: {1: 1.0}
        widen_on_structure: 1.0
        structure_taper_m: 15.0
        kerb_height_m: 0.15
        kerb_width_m: 0.5
        junction_trim_factor: 1.0
        junction_trim_max_fraction: 0.35
        surface_material: asphalt
        kerb_material: kerb
    fares:
      max_snap_m: 30.0
      null_values: ["-99"]
      groups:
        - kind: taxi_stand
          source: stands
          crs: EPSG:4326
          fields: {name_en: NAME_EN, name_zh: NAME_ZH, category: STATUS}
          categories:
            - {match: "Cross Harbour", id: cross_harbour}
            - {match: "Urban", id: urban}
        - kind: pudo
          source: points
          crs: EPSG:4326
          fields: {name_en: NAME_EN, name_zh: NAME_ZH, category: STATUS}
          categories:
            - {match: "PU/DF", id: pickup_dropoff}
            - {match: "DF", id: dropoff, pickup: false}
    """
)
