"""Source CRS to game space.

This is the only module in the pipeline permitted to know how projected
coordinates become Godot world metres. It is deliberately *not* permitted to
know which CRS Hong Kong uses: every code arrives from `config/cities/*.yaml`,
so adding a second city is a config file rather than a patch (CLAUDE.md hard
rule 3). See `docs/ARCHITECTURE.md` for the conversion and the data contract.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache

from pyproj import Transformer

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


def project_bounds(
    bounds: GeodeticBounds, *, geodetic_crs: str, projected_crs: str
) -> ProjectedBounds:
    """Convert a lon/lat rectangle to source-CRS metres."""
    min_easting, min_northing, max_easting, max_northing = transformer(
        geodetic_crs, projected_crs
    ).transform_bounds(
        bounds.west,
        bounds.south,
        bounds.east,
        bounds.north,
        densify_pts=_BOUNDS_DENSIFY_PTS,
    )
    return ProjectedBounds(min_easting, min_northing, max_easting, max_northing)


@dataclass(frozen=True)
class GameTransform:
    """Projected metres to Godot world metres: translate, then flip the Z axis.

    Deliberately free of pyproj. The source CRS is already projected and metric,
    so this leg is pure arithmetic — keeping it that way means the per-vertex
    hot path never re-enters PROJ, and the transform can be serialised into
    `city.json` as three numbers the game could reproduce itself.

    Godot is right-handed and Y-up with -Z forward, hence the negation on
    northing: without it the conversion would mirror the city.
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
        """Place the origin at the region's south-west corner.

        Floored to whole metres rather than used raw. The origin is written into
        `city.json` and every tile boundary is measured from it, so a projected
        value that differs in its sixth decimal between PROJ releases would
        otherwise renumber every tile. Flooring rather than rounding keeps every
        offset within the region non-negative before the Z flip.

        Note what the flip then does: with the origin at the south-west corner,
        the region runs +X eastward but **-Z northward**, so its game-space Z is
        zero-or-negative throughout. The `bounds_game` example in
        docs/ARCHITECTURE.md shows a positive Z extent and cannot be reconciled
        with the conversion stated two sections below it. See PROGRESS.md, Q7.
        """
        return cls(
            origin_easting=float(math.floor(bounds.min_easting)),
            origin_northing=float(math.floor(bounds.min_northing)),
            origin_elevation=origin_elevation,
        )

    def to_game(
        self, easting: float, northing: float, elevation: float = 0.0
    ) -> tuple[float, float, float]:
        """Source easting/northing/elevation to game (x, y, z)."""
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
