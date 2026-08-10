"""Source CRS to game space.

This is the only module in the pipeline permitted to know how projected
coordinates become Godot world metres. It is deliberately *not* permitted to
know which CRS Hong Kong uses: every code arrives from `config/cities/*.yaml`,
so adding a second city is a config file rather than a patch (CLAUDE.md hard
rule 3). See `docs/ARCHITECTURE.md` for the conversion and the data contract.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache

import numpy as np
from pyproj import Transformer

# `GameTransform` is pure arithmetic, so it works elementwise on arrays exactly
# as it does on scalars. Spelled out so callers know a whole polyline may go
# through it rather than reaching for a second, vectorised copy.
_Coordinate = float | np.ndarray

# pyproj walks each edge of the rectangle before taking the envelope. A
# geodetic rectangle is not a rectangle once projected, so sampling only the
# four corners can cut a sliver off a curved edge; densifying keeps the
# projected bounds a true superset. Negligible at 1.5 km, wrong at city scale.
_BOUNDS_DENSIFY_PTS = 21


@dataclass(frozen=True)
class GeodeticBounds:
    """A lon/lat rectangle in degrees.

    Which datum these degrees are on is the caller's business and must be
    stated in city config, not assumed. In Hong Kong the same numbers read as
    WGS84 rather than HK1980 land ~304 m away — a fifth of the width of the
    Wan Chai region. `test_crs.py` guards this.
    """

    west: float
    east: float
    south: float
    north: float

    def __post_init__(self) -> None:
        if self.west >= self.east:
            raise ValueError(f"west {self.west} must be less than east {self.east}")
        if self.south >= self.north:
            raise ValueError(f"south {self.south} must be less than north {self.north}")

    def intersects(self, other: GeodeticBounds) -> bool:
        """Whether two rectangles share any area, edge contact included.

        Touching counts as intersecting on purpose. Published map sheets tile
        their territory edge to edge, so a boundary landing exactly on a shared
        edge should select both neighbours rather than silently drop the one it
        grazes.

        Both rectangles must already be on the same datum — see
        `reproject_bounds`. Comparing degrees across datums is the ~304 m
        mistake documented in the class docstring.
        """
        return (
            self.west <= other.east
            and other.west <= self.east
            and self.south <= other.north
            and other.south <= self.north
        )

    @classmethod
    def around(cls, lons: Sequence[float], lats: Sequence[float]) -> GeodeticBounds:
        """Envelope of a set of points."""
        if not lons or not lats:
            raise ValueError("cannot build bounds around no points")
        return cls(west=min(lons), east=max(lons), south=min(lats), north=max(lats))


@dataclass(frozen=True)
class ProjectedBounds:
    """An easting/northing rectangle in the source CRS's linear unit (metres)."""

    min_easting: float
    min_northing: float
    max_easting: float
    max_northing: float

    @property
    def width_m(self) -> float:
        return self.max_easting - self.min_easting

    @property
    def height_m(self) -> float:
        return self.max_northing - self.min_northing

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """`(min_x, min_y, max_x, max_y)` — the order OGR's bbox filter takes."""
        return (self.min_easting, self.min_northing, self.max_easting, self.max_northing)


@cache
def transformer(from_crs: str, to_crs: str) -> Transformer:
    """Cached transformer for a CRS pair.

    Construction queries the PROJ database and picks a datum operation, which
    costs milliseconds. The pipeline pushes millions of vertices through a
    handful of pairs, so building one per call would dominate the run.

    `always_xy` forces lon/lat and easting/northing ordering regardless of the
    axis order the CRS declares. EPSG:4326 is officially lat-then-lon, and
    silently swapped coordinates are the classic way to place a city in the
    Indian Ocean.
    """
    return Transformer.from_crs(from_crs, to_crs, always_xy=True)


def _transform_bounds(
    bounds: GeodeticBounds, from_crs: str, to_crs: str
) -> tuple[float, float, float, float]:
    """Envelope of `bounds` in `to_crs`, as (min x, min y, max x, max y).

    Shared by the two public conversions so the densification setting and the
    argument order — both load-bearing, neither obvious — exist once.
    """
    return transformer(from_crs, to_crs).transform_bounds(
        bounds.west,
        bounds.south,
        bounds.east,
        bounds.north,
        densify_pts=_BOUNDS_DENSIFY_PTS,
    )


def reproject_bounds(bounds: GeodeticBounds, *, from_crs: str, to_crs: str) -> GeodeticBounds:
    """Move a lon/lat rectangle onto another geodetic datum.

    Needed because a published index and a region definition need not share a
    datum, and comparing their degrees directly is the ~304 m error. Densified
    like `project_bounds`, so the result is a superset: a filter built on it
    over-selects at worst, which costs a spare download rather than a hole in
    the map.
    """
    if from_crs == to_crs:
        return bounds
    west, south, east, north = _transform_bounds(bounds, from_crs, to_crs)
    return GeodeticBounds(west=west, east=east, south=south, north=north)


def project_bounds(
    bounds: GeodeticBounds, *, geodetic_crs: str, projected_crs: str
) -> ProjectedBounds:
    """Convert a lon/lat rectangle to source-CRS metres."""
    return ProjectedBounds(*_transform_bounds(bounds, geodetic_crs, projected_crs))


@dataclass(frozen=True)
class GameTransform:
    """Projected metres to Godot world metres: translate, then flip the Z axis.

    Deliberately free of pyproj. The source CRS is already projected and metric,
    so this leg is pure arithmetic — keeping it that way means the per-vertex
    hot path never re-enters PROJ, and the transform can be serialised into
    `city.json` as three numbers the game could reproduce itself.

    The negation on northing is forced, not chosen. Godot is right-handed and
    Y-up, so rotating +X by 90° counter-clockwise about +Y lands on -Z; if east
    is +X then north must be -Z, or the city comes out mirrored. Only *where
    zero sits* was ever a free choice — see `from_bounds`.
    """

    origin_easting: float
    origin_northing: float
    # Height of game y=0 in the source vertical datum. Hong Kong Principal
    # Datum is approximately mean sea level, so 0.0 puts the harbour at y=0.
    origin_elevation: float = 0.0

    @classmethod
    def from_bounds(
        cls, bounds: ProjectedBounds, *, origin_elevation: float = 0.0
    ) -> GameTransform:
        """Place the origin at the region's north-west corner.

        North-west, not south-west, so the whole region sits in the positive
        quadrant: X runs east from 0, and because the Z flip below is forced by
        handedness rather than chosen, anchoring at the *northern* edge is what
        makes Z run 0 southward instead of 0 northward. Tile indices are then
        natural numbers — row 0 at the north, like a raster or a map sheet —
        rather than the 0, -1, -2 a southern anchor produces. Resolves Q7.

        Rounded outward to whole metres rather than used raw: the origin is
        written into `city.json` and every tile boundary is measured from it, so
        a projected value differing in its sixth decimal between PROJ releases
        would otherwise renumber every tile. Outward — floor west, ceil north —
        so every offset inside the region stays non-negative.
        """
        return cls(
            origin_easting=float(math.floor(bounds.min_easting)),
            origin_northing=float(math.ceil(bounds.max_northing)),
            origin_elevation=origin_elevation,
        )

    def to_game(
        self, easting: _Coordinate, northing: _Coordinate, elevation: _Coordinate = 0.0
    ) -> tuple[_Coordinate, _Coordinate, _Coordinate]:
        """Source easting/northing/elevation to game (x, y, z).

        Vectorises: being pure arithmetic, it takes numpy arrays as readily as
        scalars and returns the same shape. Callers with a whole polyline should
        use it directly rather than write the translation out again — the sign
        on Z is a consequence of Godot's handedness, and the moment it is
        restated somewhere else it can drift.
        """
        return (
            easting - self.origin_easting,
            elevation - self.origin_elevation,
            -(northing - self.origin_northing),
        )

    def to_source(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Game (x, y, z) back to source (easting, northing, elevation).

        Note the tuple order differs from `to_game`'s: this returns surveyor
        order, not Godot order.
        """
        return (
            x + self.origin_easting,
            self.origin_northing - z,
            y + self.origin_elevation,
        )
