"""City configuration loading.

Every city specific — CRS codes, region bounds, deck heights, source URLs —
lives in `config/cities/*.yaml` and reaches the pipeline only through this
module (CLAUDE.md hard rule 3). Pipeline logic that needs a Hong Kong fact asks
the config for it; it never spells the fact out.

Loading is strict and fails on the first problem rather than defaulting. A
silently-defaulted CRS or bound produces output that looks plausible and is
wrong by hundreds of metres, which is far more expensive than a stack trace.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeline.crs import (
    GameTransform,
    GeodeticBounds,
    ProjectedBounds,
    project_bounds,
)

SUPPORTED_SCHEMA = 1
CITIES_ROOT = Path(__file__).resolve().parent.parent / "config" / "cities"
# Where every stage writes its output. One definition, because two stages
# writing into the same tree from two of them is how they end up disagreeing.
OUT_ROOT = Path(__file__).resolve().parent.parent / "out"


@dataclass(frozen=True)
class RegionConfig:
    id: str
    name: str
    bounds: GeodeticBounds
    tile_size_m: float


@dataclass(frozen=True)
class TiledSource:
    """A dataset published per map sheet, reachable only through an index.

    The index is a vector layer whose features carry both a footprint and the
    download URL for that footprint's models, so which sheets a region needs is
    derived rather than listed. The property names below are what keeps this
    city-agnostic: the pipeline knows "some property holds the URL", never that
    Hong Kong happens to call it `Format_glTF`.

    Those URLs may embed a publisher's API key, which is why they are read from
    the fetched index at run time and never written into config or the manifest.
    """

    id: str
    index_url: str
    # Datum of the index geometry, which need not match the region's.
    index_crs: str
    id_property: str
    url_property: str
    # Per-tile version stamp used as the cache key. Optional: a publisher that
    # offers none simply gets fetch-once semantics.
    revision_property: str | None = None


@dataclass(frozen=True)
class HeightBand:
    """A colour for buildings up to a given height above their own base."""

    up_to_m: float
    colour: tuple[int, int, int]


@dataclass(frozen=True)
class BuildingStyle:
    """How `P1-2` turns source massing into vertex-coloured tiles.

    All of it is tuning data rather than constants in code (CLAUDE.md hard
    rule 4), and all of it is city-shaped: the sub-directory names come from the
    publisher's zip layout, and the palette is Hong Kong's, not a generic city's.
    """

    # Sheet sub-directories holding massing to tile.
    classes: tuple[str, ...]
    # Sheet sub-directory holding the textured ground, which is read only by the
    # evaluation path and never tiled. Named here rather than in the pipeline
    # because "TERRAIN(TB)" is a LandsD spelling, not a fact about terrain.
    terrain_class: str
    # Flat colour for a class, overriding the height bands.
    class_colours: dict[str, tuple[int, int, int]]
    height_bands: tuple[HeightBand, ...]
    # Fraction of brightness a building's colour may be varied by, seeded from
    # its own id so the result is stable across runs.
    colour_jitter: float
    # One clustering cell size per LOD tier, in metres, coarsest last. The first
    # is normally 0.0 — an exact weld, losing nothing.
    lod_cell_sizes_m: tuple[float, ...]

    def colour_for(self, class_id: str, height_m: float) -> tuple[int, int, int]:
        if class_id in self.class_colours:
            return self.class_colours[class_id]
        return next(band.colour for band in self.height_bands if height_m <= band.up_to_m)


@dataclass(frozen=True)
class SourceLayer:
    """One layer of a source dataset, and what the pipeline calls its fields.

    `fields` maps a **role** the pipeline asks for onto the publisher's own
    column name. That indirection is the whole point: `roads.py` may know that
    a centreline has a travel direction, and may not know that Hong Kong's
    Transport Department spells it `TRAVEL_DIRECTION` (CLAUDE.md hard rule 3).
    """

    layer: str
    fields: dict[str, str]

    def field(self, role: str) -> str:
        return _field(self.fields, role, f"layer '{self.layer}'")

    @property
    def columns(self) -> list[str]:
        """Every source column to read, deduplicated and ordered."""
        return sorted(set(self.fields.values()))


def _field(fields: Mapping[str, str], role: str, where: str) -> str:
    """The publisher's column name for a role the pipeline asked for.

    Shared by every configured schema mapping, so the error a missing role
    produces reads the same wherever it is hit.
    """
    if role not in fields:
        known = ", ".join(sorted(fields)) or "none"
        raise KeyError(f"{where} declares no field for '{role}'. Declared: {known}")
    return fields[role]


# Directions a city file may declare. `BACKWARD` never reaches
# `roadgraph.json`: a source that codes direction against its own digitisation
# is normalised away by reversing the polyline, so the game never has to know
# the difference. Named here, next to the validation, so the stage that acts
# on them cannot drift from the set that is accepted.
BOTH = "both"
FORWARD = "forward"
BACKWARD = "backward"
DIRECTIONS = (BOTH, FORWARD, BACKWARD)

# Where game y=0 sits for a road deck. `TERRAIN` samples the source height
# field; `DATUM` puts level 0 at zero and is right only for a city whose
# sources carry no terrain.
TERRAIN = "terrain"
DATUM = "datum"
GROUND_SOURCES = (TERRAIN, DATUM)

# Fare-node kinds in the data contract. `poi` is listed because the contract
# lists it; no dataset produces one yet, and a city that adds hotels or malls
# adds a group rather than a code path.
TAXI_STAND = "taxi_stand"
PUDO = "pudo"
POI = "poi"
FARE_KINDS = (TAXI_STAND, PUDO, POI)

# What a fare group must name in the publisher's schema, in roles the pipeline
# owns. Same indirection as `_ROAD_LAYER_ROLES` and for the same reason.
_FARE_ROLES = ("name_en", "name_zh", "category")

# What each road layer must declare. The pipeline states its requirements here,
# in role names it owns, and the city file supplies the column names.
_ROAD_LAYER_ROLES: dict[str, tuple[str, ...]] = {
    "centrelines": ("elevation", "travel_direction", "route", "name_en", "name_zh"),
    "turns": ("first_edge", "first_end", "second_edge"),
    "speed_limits": ("route", "speed_limit"),
    "bus_lanes": ("route",),
}


@dataclass(frozen=True)
class RoadSurface:
    """How `P1-4` turns the road graph into a drivable ribbon mesh.

    Separate from `RoadNetwork` because it tunes a different thing: the graph is
    a description of the city, this is how wide and how kerbed to draw it. A
    change here never changes `roadgraph.json`.
    """

    # Multiplier on the graph's `width_m`, for play rather than accuracy. Real
    # Hong Kong street widths are unforgiving at arcade speeds; see
    # `docs/GAME_DESIGN.md`, which fixes the range at roughly 1.3-1.8x.
    widen_default: float
    widen_by_min_speed_limit_kph: dict[int, float]

    # Kerbs are modelled but low and mountable — collision is forgiving by
    # design. The lip is what stops the carriageway ending in mid-air, since
    # the terrain is not shipped.
    kerb_height_m: float
    kerb_width_m: float

    # How far back from a node each ribbon stops so a junction cap can fill the
    # middle, as a multiple of the widest half-width meeting there.
    junction_trim_factor: float
    # Ceiling on that trim as a fraction of the edge's own length, so a short
    # edge between two wide roads is not consumed from both ends.
    junction_trim_max_fraction: float

    surface_colour: tuple[int, int, int]
    kerb_colour: tuple[int, int, int]

    def widen_for(self, speed_limit_kph: int) -> float:
        """Widening factor for an edge, from the fastest matching rule.

        Expressways are already drawn wide by their lane count and need less
        help; a two-lane street is where the widening earns its keep.
        """
        return float(
            _by_fastest_rule(self.widen_by_min_speed_limit_kph, speed_limit_kph, self.widen_default)
        )


def _by_fastest_rule(table: Mapping[int, float], speed_limit_kph: int, default: float) -> float:
    """The value of the highest speed threshold the limit reaches, else `default`.

    The *fastest* matching rule wins, not the largest value. Identical while a
    table is monotonic, which none of them need stay: a city that gave a 90 km/h
    tunnel two lanes and a 70 km/h arterial three would otherwise get three
    either way.
    """
    matched = [
        (threshold, value) for threshold, value in table.items() if speed_limit_kph >= threshold
    ]
    return max(matched)[1] if matched else default


@dataclass(frozen=True)
class RoadNetwork:
    """How `P1-3` turns a published road network into a drivable graph.

    Everything here is either the publisher's schema or a tuning value, and both
    kinds are barred from the pipeline by CLAUDE.md hard rules 3 and 4.
    """

    # Which `sources:` entry holds the dataset, and the layers inside it.
    source: str
    centrelines: SourceLayer
    turns: SourceLayer
    speed_limits: SourceLayer
    bus_lanes: SourceLayer

    # Source travel-direction code to a direction in the data contract.
    travel_directions: dict[int, str]
    # Value of the turn layer's "which end of the first edge" field that means
    # the turn passes through the end rather than the start.
    turn_at_end_value: str
    # Strings that mean "no value" in a text field. Compared after Unicode
    # normalisation, so one entry covers the full-width spellings too.
    null_values: tuple[str, ...]

    # Applied where the source signs no limit. Hong Kong signs only exceptions
    # to the 50 km/h urban default, so this covers 90% of the region's edges.
    default_speed_limit_kph: int
    # Douglas-Peucker tolerance for centreline geometry, in metres.
    simplify_tolerance_m: float
    # Shortest run of road the region boundary may leave behind. A feature that
    # only clips a corner contributes a stub no vehicle can occupy.
    min_edge_length_m: float

    # Lane counts are not published — see `lanes_for`.
    lanes_default: int
    lanes_by_min_speed_limit_kph: dict[int, int]
    lane_width_m: float

    # Streets carrying tram tracks. Hand-authored: no dataset marks them, and
    # `docs/GAME_DESIGN.md` calls trams the highest-leverage object in the game.
    tram_streets: frozenset[str]

    # Whether to take ground level from the terrain mesh (`Q11`). A city with no
    # terrain in its sources leaves this off and gets the vertical datum.
    ground_from_terrain: bool

    # How `P1-4` draws what the graph describes.
    surface: RoadSurface

    def lanes_for(self, speed_limit_kph: int) -> int:
        """Lane count for an edge, from the fastest matching rule.

        **Not a published attribute.** Road Network v2 carries no lane count in
        any layer, so this is authored policy keyed on what the source does
        carry. `P1-4` widens the result for play on top; see `docs/PLAN.md`.
        """
        return int(
            _by_fastest_rule(self.lanes_by_min_speed_limit_kph, speed_limit_kph, self.lanes_default)
        )


@dataclass(frozen=True)
class FareCategory:
    """One rule turning a publisher's category text into a contract slug.

    `match` is a substring rather than an exact value, because the categories
    are free text with an operating-time note glued on: Hong Kong publishes a
    stand as `Cross Harbour Taxi Stand\\n(1200-0600 daily)`. Sixteen distinct
    strings collapse to five categories that way.

    Rules are tried in order and the first hit wins, so a city file orders them
    most specific first — `load_city` refuses a table where a later rule could
    never be reached.
    """

    match: str
    id: str
    # Whether a fare may be hailed here, and whether one may be delivered here.
    # Not every legal drop-off point is a legal pick-up point: a quarter of
    # Hong Kong's published points are drop-off only, and a game that let a
    # player hail at one would be wrong in a way a local would notice.
    pickup: bool
    dropoff: bool


@dataclass(frozen=True)
class FareGroup:
    """One published point dataset, and what kind of fare node it produces."""

    # A `kind` in the data contract. The pipeline owns this vocabulary.
    kind: str
    # Which `sources:` entry holds the dataset.
    source: str
    # Datum the dataset's coordinates are on, which need not be the region's.
    # GeoJSON with no `crs` member is CRS84 per RFC 7946 — state that here
    # rather than let a reader assume it.
    crs: str
    fields: dict[str, str]
    categories: tuple[FareCategory, ...]

    def field(self, role: str) -> str:
        return _field(self.fields, role, f"fare group '{self.kind}'")

    def categorise(self, text: str) -> FareCategory:
        """The first rule whose `match` appears in `text`.

        An unmatched category raises rather than defaulting. These datasets are
        republished twice a year, and a new category appearing in one should
        stop the build — silently filing it under the fallback would ship a
        premium cross-harbour stand as an ordinary one.
        """
        folded = text.casefold()
        for rule in self.categories:
            if rule.match.casefold() in folded:
                return rule
        known = ", ".join(repr(rule.match) for rule in self.categories)
        raise KeyError(
            f"fare group '{self.kind}' has a feature categorised {text!r}, which matches no "
            f"rule. Rules: {known}"
        )


@dataclass(frozen=True)
class Fares:
    """How `P1-5` turns published point datasets into fare nodes."""

    groups: tuple[FareGroup, ...]
    # Furthest a source point may sit from a road edge and still be attached to
    # it. Beyond this the node is dropped: a fare node whose `nearest_edge`
    # names a road it has no relationship with is worse than no fare node.
    max_snap_m: float
    # Strings that mean "no value" in a text field, as in `RoadNetwork`.
    null_values: tuple[str, ...]


@dataclass(frozen=True)
class CityConfig:
    id: str
    name: str
    # CRS the source datasets are published in; all pipeline geometry lives here.
    projected_crs: str
    # Datum the region bounds above are expressed in. Stated rather than assumed
    # because reading Hong Kong bounds on the wrong datum moves them ~304 m.
    geodetic_crs: str
    # Ordinal grade-separation level to authored deck height in metres. Road
    # Network v2 carries no Z; ELEVATION is a layer index, not a measurement.
    elevation_levels: dict[int, float]
    # Whole-city extent. Only ever used to anchor the city-space frame that
    # regions are positioned in, so it must be *declared and stable* rather
    # than derived from the regions that happen to exist — see `city_transform`.
    bounds: GeodeticBounds
    regions: dict[str, RegionConfig]
    # Datasets available at a single fixed URL.
    sources: dict[str, str]
    # Datasets that must be selected per region via an index.
    tiled_sources: dict[str, TiledSource]
    buildings: BuildingStyle
    roads: RoadNetwork
    fares: Fares

    @property
    def source_ids(self) -> set[str]:
        """Every fetchable source name, of either kind."""
        return set(self.sources) | set(self.tiled_sources)

    def region(self, region_id: str) -> RegionConfig:
        if region_id not in self.regions:
            known = ", ".join(sorted(self.regions)) or "none"
            raise KeyError(f"City '{self.id}' has no region '{region_id}'. Known: {known}")
        return self.regions[region_id]

    def projected_bounds(self, region_id: str) -> ProjectedBounds:
        return project_bounds(
            self.region(region_id).bounds,
            geodetic_crs=self.geodetic_crs,
            projected_crs=self.projected_crs,
        )

    def game_transform(self, region_id: str) -> GameTransform:
        """The region's own frame — what its geometry is authored in.

        Region-local rather than city-wide on purpose. Everything the player
        drives through sits within ~2 km of this origin, where float32 resolves
        to a fraction of a millimetre. A city-wide frame would put Wan Chai
        35 km out, quantising every position — the car's included — to ~4 mm.
        See `city_offset` for how regions are then placed relative to each other.
        """
        return GameTransform.from_bounds(self.projected_bounds(region_id))

    def region_high(self, region_id: str) -> tuple[float, float]:
        """The region's far corner in game plan metres — `(max x, max z)`.

        The near corner is `(0, 0)` by construction: `GameTransform.from_bounds`
        anchors the origin at the north-west. So this pair *is* the region's
        extent, and `0 <= x <= high[0] and 0 <= z <= high[1]` is what "inside
        the region" means for every stage.

        A method rather than three call sites working it out, because getting
        it by hand means writing `to_game(max_easting, min_northing)` — the
        corner that is maximal in X is minimal in northing, since Godot's
        handedness flips Z. Three stages need it and each one is a chance to
        pair the wrong two bounds.
        """
        bounds = self.projected_bounds(region_id)
        far_x, _, far_z = self.game_transform(region_id).to_game(
            bounds.max_easting, bounds.min_northing
        )
        return (far_x, far_z)

    def out_dir(self, region_id: str, root: Path | None = None) -> Path:
        """Where a region's build output goes.

        The single definition of the out-tree layout, as `fetch.artefact_path`
        is for the sources tree. Every stage resolves through this rather than
        rebuilding `<root>/<city>/<region>`, so the three that write there
        cannot disagree about it.
        """
        return (root or OUT_ROOT) / self.id / region_id

    def city_transform(self) -> GameTransform:
        """The shared frame all regions are positioned in (`Q10`).

        Anchored on the city's *declared* bounds, never on the union of the
        regions defined so far. Deriving it would make the frame move every time
        a region is added, silently invalidating every offset already written
        into a published `city.json`. Declared bounds are allowed to be generous;
        they are not allowed to change.
        """
        return GameTransform.from_bounds(
            project_bounds(
                self.bounds,
                geodetic_crs=self.geodetic_crs,
                projected_crs=self.projected_crs,
            )
        )

    def city_offset(self, region_id: str) -> tuple[float, float, float]:
        """Add this to a region-local position to get a city-space one.

        The number that lets two regions abut without either giving up its local
        precision. A region loaded alone can ignore it entirely; a build that
        streams neighbours applies it as a translation.

        Non-negative in X and Z whenever the city bounds actually contain the
        region, which `load_city` checks.
        """
        region = self.game_transform(region_id)
        city = self.city_transform()
        return (
            region.origin_easting - city.origin_easting,
            region.origin_elevation - city.origin_elevation,
            city.origin_northing - region.origin_northing,
        )

    def deck_height_m(self, elevation_level: int) -> float:
        """Authored height for a road-graph ELEVATION value.

        Tunnels are plausible in the source and were not seen in the sample, so
        an unmapped level is an error rather than a silent 0.0 that would drag a
        tunnel up to street level and invent a junction.
        """
        if elevation_level not in self.elevation_levels:
            known = ", ".join(str(k) for k in sorted(self.elevation_levels))
            raise KeyError(
                f"City '{self.id}' maps no deck height for ELEVATION {elevation_level}. "
                f"Known levels: {known}"
            )
        return self.elevation_levels[elevation_level]


def load_city(city_id: str, *, cities_root: Path | None = None) -> CityConfig:
    """Read and validate `<cities_root>/<city_id>.yaml`."""
    path = (cities_root or CITIES_ROOT) / f"{city_id}.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} is not a YAML mapping")

    version = document.get("schema_version")
    if version != SUPPORTED_SCHEMA:
        raise ValueError(f"{path} declares schema_version {version!r}, expected {SUPPORTED_SCHEMA}")
    if document.get("id") != city_id:
        raise ValueError(f"{path} declares id {document.get('id')!r}, expected {city_id!r}")

    crs = _require(document, "crs", path)
    regions = _require(document, "regions", path)
    if not regions:
        raise ValueError(f"{path} defines no regions")

    city = CityConfig(
        id=city_id,
        name=str(_require(document, "name", path)),
        projected_crs=str(_require(crs, "projected", f"{path}:crs")),
        geodetic_crs=str(_require(crs, "geodetic", f"{path}:crs")),
        elevation_levels=_elevation_levels(_require(document, "elevation_levels", path), path),
        bounds=_bounds(_require(document, "bounds", path), f"{path}:bounds"),
        regions={region_id: _region(region_id, body, path) for region_id, body in regions.items()},
        sources={str(k): str(v) for k, v in (document.get("sources") or {}).items()},
        tiled_sources={
            str(source_id): _tiled_source(str(source_id), body, path)
            for source_id, body in (document.get("tiled_sources") or {}).items()
        },
        buildings=_building_style(_require(document, "buildings", path), f"{path}:buildings"),
        roads=_road_network(_require(document, "roads", path), f"{path}:roads"),
        fares=_fares(_require(document, "fares", path), f"{path}:fares"),
    )
    _check_regions_lie_within_the_city(city, path)
    _check_source_exists(city, city.roads.source, f"{path}:roads.source")
    for index, group in enumerate(city.fares.groups):
        _check_source_exists(city, group.source, f"{path}:fares.groups[{index}].source")
    return city


def _check_source_exists(city: CityConfig, source_id: str, where: str) -> None:
    """A stage that names a source it cannot fetch is a config error, not a run.

    Caught at load rather than at first use, so a typo fails before the
    pipeline has read 17 MB of geodatabase to discover it.
    """
    if source_id not in city.sources:
        known = ", ".join(sorted(city.sources)) or "none"
        raise ValueError(f"{where} names '{source_id}', which is not in sources ({known})")


def _check_regions_lie_within_the_city(city: CityConfig, path: Path) -> None:
    """A region outside the declared city bounds is a config error, not a shift.

    It would still produce coordinates, just with a negative `city_offset` —
    i.e. a region placed north or west of the frame everything else is measured
    from. Caught here because the symptom otherwise appears in `P1-6` output as
    a region that loads fine alone and lands in the wrong place beside another.
    """
    city_bounds = city.bounds
    for region in city.regions.values():
        r = region.bounds
        if (
            r.west < city_bounds.west
            or r.east > city_bounds.east
            or r.south < city_bounds.south
            or r.north > city_bounds.north
        ):
            raise ValueError(
                f"{path}:regions.{region.id} lies outside the city bounds. "
                f"Region ({r.west}, {r.south})-({r.east}, {r.north}) is not inside "
                f"({city_bounds.west}, {city_bounds.south})-"
                f"({city_bounds.east}, {city_bounds.north})."
            )


def _tiled_source(source_id: str, body: dict[str, Any], path: Path) -> TiledSource:
    where = f"{path}:tiled_sources.{source_id}"
    revision = body.get("revision_property")
    return TiledSource(
        id=source_id,
        index_url=str(_require(body, "index_url", where)),
        index_crs=str(_require(body, "index_crs", where)),
        id_property=str(_require(body, "id_property", where)),
        url_property=str(_require(body, "url_property", where)),
        revision_property=None if revision is None else str(revision),
    )


def _building_style(body: dict[str, Any], where: str) -> BuildingStyle:
    bands = tuple(
        HeightBand(
            up_to_m=float(_require(band, "up_to_m", where)),
            colour=_parse_hex(str(_require(band, "colour", where)), f"{where}:height_bands"),
        )
        for band in _require(body, "height_bands", where)
    )
    if not bands:
        raise ValueError(f"{where}:height_bands is empty")
    heights = [band.up_to_m for band in bands]
    if heights != sorted(heights):
        raise ValueError(f"{where}:height_bands must be ordered by ascending up_to_m")
    if heights[-1] != float("inf"):
        # Without an open-ended last band, `colour_for` has nothing to return for
        # a building taller than the table — and the tallest buildings are the
        # ones a Hong Kong skyline is read by.
        raise ValueError(f"{where}:height_bands must end with `up_to_m: .inf`")

    cells = tuple(float(size) for size in _require(body, "lod_cell_sizes_m", where))
    if not cells:
        raise ValueError(f"{where}:lod_cell_sizes_m is empty")
    if list(cells) != sorted(cells):
        raise ValueError(f"{where}:lod_cell_sizes_m must be ordered coarsest last")

    classes = tuple(str(name) for name in _require(body, "classes", where))
    if not classes:
        raise ValueError(f"{where}:classes is empty")

    class_colours = {
        str(name): _parse_hex(str(value), f"{where}:class_colours.{name}")
        for name, value in (body.get("class_colours") or {}).items()
    }
    unknown = set(class_colours) - set(classes)
    if unknown:
        # A misspelled key parses, loads, and silently colours nothing — the one
        # way this table can be wrong without saying so.
        raise ValueError(
            f"{where}:class_colours names {', '.join(sorted(unknown))}, "
            f"which is not in classes ({', '.join(classes)})"
        )

    jitter = float(_require(body, "colour_jitter", where))
    if not 0.0 <= jitter < 1.0:
        raise ValueError(f"{where}:colour_jitter must be in [0, 1), got {jitter}")

    return BuildingStyle(
        classes=classes,
        terrain_class=str(_require(body, "terrain_class", where)),
        class_colours=class_colours,
        height_bands=bands,
        colour_jitter=jitter,
        lod_cell_sizes_m=cells,
    )


def _road_network(body: dict[str, Any], where: str) -> RoadNetwork:
    layers = {
        name: _source_layer(_require(body, name, where), f"{where}:{name}", roles)
        for name, roles in _ROAD_LAYER_ROLES.items()
    }

    directions: dict[int, str] = {}
    for code, direction in _require(body, "travel_directions", where).items():
        # Same YAML 1.1 boolean trap as `elevation_levels`: a bare `on:` key
        # resolves to True, and True == 1 as a dict key, so it would quietly
        # redefine whichever code the city uses for a two-way road.
        if isinstance(code, bool) or not isinstance(code, int):
            raise ValueError(f"{where}:travel_directions key {code!r} is not an integer")
        if direction not in DIRECTIONS:
            raise ValueError(
                f"{where}:travel_directions[{code}] is {direction!r}, "
                f"expected one of {', '.join(DIRECTIONS)}"
            )
        directions[code] = str(direction)
    if not directions:
        raise ValueError(f"{where}:travel_directions is empty")

    lanes = {
        int(threshold): int(count)
        for threshold, count in (body.get("lanes_by_min_speed_limit_kph") or {}).items()
    }
    tolerance = float(_require(body, "simplify_tolerance_m", where))
    if tolerance < 0.0:
        raise ValueError(f"{where}:simplify_tolerance_m must not be negative, got {tolerance}")

    ground = str(_require(body, "ground", where))
    if ground not in GROUND_SOURCES:
        raise ValueError(
            f"{where}:ground is {ground!r}, expected one of {', '.join(GROUND_SOURCES)}"
        )

    return RoadNetwork(
        source=str(_require(body, "source", where)),
        centrelines=layers["centrelines"],
        turns=layers["turns"],
        speed_limits=layers["speed_limits"],
        bus_lanes=layers["bus_lanes"],
        travel_directions=directions,
        turn_at_end_value=str(_require(body, "turn_at_end_value", where)),
        null_values=tuple(str(value) for value in (body.get("null_values") or ())),
        default_speed_limit_kph=int(_require(body, "default_speed_limit_kph", where)),
        simplify_tolerance_m=tolerance,
        min_edge_length_m=float(_require(body, "min_edge_length_m", where)),
        lanes_default=int(_require(body, "lanes_default", where)),
        lanes_by_min_speed_limit_kph=lanes,
        lane_width_m=float(_require(body, "lane_width_m", where)),
        tram_streets=frozenset(str(name) for name in (body.get("tram_streets") or ())),
        ground_from_terrain=ground == TERRAIN,
        surface=_road_surface(_require(body, "surface", where), f"{where}:surface"),
    )


def _road_surface(body: dict[str, Any], where: str) -> RoadSurface:
    widen_default = float(_require(body, "widen_default", where))
    widen = {
        int(threshold): float(factor)
        for threshold, factor in (body.get("widen_by_min_speed_limit_kph") or {}).items()
    }
    for factor in (widen_default, *widen.values()):
        # Narrowing a road is not a tuning choice, it is a typo: the graph's
        # width already comes from an authored lane count, and a sub-1 factor
        # would put the carriageway inside the buildings beside it.
        if factor < 1.0:
            raise ValueError(f"{where} widening factor {factor} is below 1.0")

    fraction = float(_require(body, "junction_trim_max_fraction", where))
    if not 0.0 < fraction < 0.5:
        # At a half, an edge trimmed at both ends has nothing left between the
        # two junctions and the ribbon disappears.
        raise ValueError(f"{where}:junction_trim_max_fraction must be in (0, 0.5), got {fraction}")

    # A negative kerb turns the lip inside out, which inverts its winding and
    # renders as a hole; a negative trim pushes the ribbon *past* its junction.
    # Both produce plausible-looking output, which is why they are refused here
    # rather than left to be noticed in the engine.
    measures = {
        name: float(_require(body, name, where))
        for name in ("kerb_height_m", "kerb_width_m", "junction_trim_factor")
    }
    for name, value in measures.items():
        if value < 0.0:
            raise ValueError(f"{where}:{name} must not be negative, got {value}")

    return RoadSurface(
        widen_default=widen_default,
        widen_by_min_speed_limit_kph=widen,
        kerb_height_m=measures["kerb_height_m"],
        kerb_width_m=measures["kerb_width_m"],
        junction_trim_factor=measures["junction_trim_factor"],
        junction_trim_max_fraction=fraction,
        surface_colour=_parse_hex(str(_require(body, "surface_colour", where)), where),
        kerb_colour=_parse_hex(str(_require(body, "kerb_colour", where)), where),
    )


def _source_layer(body: dict[str, Any], where: str, roles: tuple[str, ...]) -> SourceLayer:
    return SourceLayer(
        layer=str(_require(body, "layer", where)),
        fields=_fields(body, where, roles),
    )


def _fields(body: dict[str, Any], where: str, roles: tuple[str, ...]) -> dict[str, str]:
    """A role-to-column mapping, checked to cover every role the stage needs.

    Checked at load for the reason `_check_source_exists` gives.
    """
    fields = {str(role): str(column) for role, column in _require(body, "fields", where).items()}
    missing = [role for role in roles if role not in fields]
    if missing:
        raise ValueError(f"{where}:fields is missing {', '.join(missing)}")
    return fields


def _fares(body: dict[str, Any], where: str) -> Fares:
    groups = tuple(
        _fare_group(entry, f"{where}:groups[{index}]")
        for index, entry in enumerate(_require(body, "groups", where))
    )
    if not groups:
        raise ValueError(f"{where}:groups is empty")

    max_snap_m = float(_require(body, "max_snap_m", where))
    if max_snap_m <= 0.0:
        # Zero would require a source point to lie exactly on a centreline.
        # Every real one is a kerbside position half a carriageway away.
        raise ValueError(f"{where}:max_snap_m must be positive, got {max_snap_m}")

    return Fares(
        groups=groups,
        max_snap_m=max_snap_m,
        null_values=tuple(str(value) for value in (body.get("null_values") or ())),
    )


def _fare_group(body: dict[str, Any], where: str) -> FareGroup:
    kind = str(_require(body, "kind", where))
    if kind not in FARE_KINDS:
        raise ValueError(f"{where}:kind is {kind!r}, expected one of {', '.join(FARE_KINDS)}")

    categories = tuple(
        FareCategory(
            match=str(_require(rule, "match", f"{where}:categories")),
            id=str(_require(rule, "id", f"{where}:categories")),
            # A stand is both by default; only a source that distinguishes them
            # has to say so.
            pickup=bool(rule.get("pickup", True)),
            dropoff=bool(rule.get("dropoff", True)),
        )
        for rule in _require(body, "categories", where)
    )
    if not categories:
        raise ValueError(f"{where}:categories is empty")
    _check_categories_are_reachable(categories, where)

    return FareGroup(
        kind=kind,
        source=str(_require(body, "source", where)),
        crs=str(_require(body, "crs", where)),
        fields=_fields(body, where, _FARE_ROLES),
        categories=categories,
    )


def _check_categories_are_reachable(categories: tuple[FareCategory, ...], where: str) -> None:
    """Refuse a rule an earlier one always shadows.

    Matching is first-hit-wins over substrings, so `"DF"` before `"PU/DF"`
    makes the second rule dead and files every pick-up point as drop-off only.
    That loads cleanly, produces a full `fares.json`, and is wrong — the
    failure mode this whole module is written to avoid.
    """
    for later, rule in enumerate(categories):
        for earlier in categories[:later]:
            if earlier.match.casefold() in rule.match.casefold():
                raise ValueError(
                    f"{where}:categories[{later}] matches {rule.match!r}, which contains the "
                    f"earlier {earlier.match!r} and can therefore never be reached. Order "
                    f"rules most specific first."
                )


def _parse_hex(value: str, where: str) -> tuple[int, int, int]:
    text = value.lstrip("#")
    if len(text) != 6:
        raise ValueError(f"{where} is not a #rrggbb colour: {value!r}")
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError as error:
        raise ValueError(f"{where} is not a #rrggbb colour: {value!r}") from error


def _require(mapping: dict[str, Any], key: str, where: Path | str) -> Any:
    if key not in mapping:
        raise ValueError(f"{where} is missing required key '{key}'")
    return mapping[key]


def _elevation_levels(raw: dict[Any, Any], path: Path) -> dict[int, float]:
    levels: dict[int, float] = {}
    for key, value in raw.items():
        # Two YAML traps here, both silent, both producing a map that loads
        # cleanly and answers wrongly.
        #
        # Quoted "-1" stays a str, giving a level no ELEVATION lookup can hit.
        #
        # Worse: PyYAML implements YAML 1.1, where bare `on`/`off`/`yes`/`no`
        # resolve to booleans. Since bool subclasses int, `off: 3.0` satisfies a
        # plain isinstance(key, int) check — and then lands on level 0, because
        # False == 0 as a dict key. A typo would silently redefine ground level.
        #
        # A collision PyYAML resolves before we see it (both `1:` and `on:` in
        # one mapping) is beyond this layer; it needs both spellings at once.
        if isinstance(key, bool) or not isinstance(key, int):
            raise ValueError(f"{path}:elevation_levels key {key!r} is not an integer")
        levels[key] = float(value)
    if 0 not in levels:
        raise ValueError(f"{path}:elevation_levels has no level 0 — ground must be mapped")
    return levels


def _bounds(body: dict[str, Any], where: str) -> GeodeticBounds:
    return GeodeticBounds(
        west=float(_require(body, "west", where)),
        east=float(_require(body, "east", where)),
        south=float(_require(body, "south", where)),
        north=float(_require(body, "north", where)),
    )


def _region(region_id: str, body: dict[str, Any], path: Path) -> RegionConfig:
    where = f"{path}:regions.{region_id}"
    return RegionConfig(
        id=region_id,
        name=str(_require(body, "name", where)),
        bounds=_bounds(_require(body, "bounds", where), f"{where}.bounds"),
        tile_size_m=float(_require(body, "tile_size_m", where)),
    )
