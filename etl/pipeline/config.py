"""City configuration loading.

A Hong Kong fact has one of two homes (CLAUDE.md hard rule 3, `Q100`): what is
tunable or a publisher's vocabulary — region bounds, deck heights, source URLs,
codes — lives in `config/hong_kong.yaml` and reaches the pipeline only through
this module; the handful of constants that *are* the city live in
`pipeline/hongkong.py`, which the `Config` properties re-export. A value lives
in exactly one of the two, never both.

Loading is strict and fails on the first problem rather than defaulting. A
silently-defaulted CRS or bound produces output that looks plausible and is
wrong by hundreds of metres, which is far more expensive than a stack trace.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pipeline import hongkong
from pipeline.colour import reflectance

# Every block's names, re-exported: `pipeline.config` stays the one door (`P3-35f`).
from pipeline.config_blocks.arrows import (  # noqa: F401
    _ARROW_ROLES,
    ARROW_AHEAD,
    ARROW_LEFT,
    ARROW_MOVEMENTS,
    ARROW_RIGHT,
    ArrowGlyph,
    Arrows,
    _arrows,
)
from pipeline.config_blocks.base import (  # noqa: F401
    LayerSpec,
    Material,
    SourceLayer,
    _field,
    _fields,
    _MaterialTable,
    _measures,
    _parse_hex,
    _Read,
    _require,
    _source_layer,
    _spec_header,
    _tile_member,
    _tracked,
    _unread,
)
from pipeline.config_blocks.boxjunctions import (  # noqa: F401
    _BOXJUNCTION_ROLES,
    BoxJunctions,
    _boxjunctions,
)
from pipeline.config_blocks.buildings import (  # noqa: F401
    _PODIUM_BLOCK_ROLES,
    _PODIUM_CODE_ROLES,
    HUE_STRENGTH_MAX,
    WEIGHT_SUM_TOLERANCE,
    BuildingStyle,
    ChromaRing,
    HeightBand,
    HueSector,
    MaterialAssignment,
    PodiumBlocks,
    SurfaceClass,
    WeightedDraw,
    _albedo_bounds,
    _ascending_to_inf,
    _building_style,
    _cell_sizes,
    _cell_table,
    _hue_sectors,
    _jitter,
    _material_assignment,
    _materials,
    _number,
    _occluder_cells,
    _podium_blocks,
    _reflectance,
    _scale,
)
from pipeline.config_blocks.fares import (  # noqa: F401
    _FARE_OPTIONAL_ROLES,
    _FARE_ROLES,
    FARE_KINDS,
    POI,
    PUDO,
    TAXI_STAND,
    FareCategory,
    FareGroup,
    Fares,
    _check_categories_are_reachable,
    _fare_group,
    _fares,
)
from pipeline.config_blocks.lamps import (  # noqa: F401
    _LAMP_MEASURES,
    _LAMP_ROLES,
    Lamps,
    _lamps,
)
from pipeline.config_blocks.landmarks import (  # noqa: F401
    _PAINT_SURFACES,
    LANDMARK_ASSET_ROOT,
    LANDMARK_GENERATED_ROOT,
    Landmark,
    SourcePaint,
    _landmark,
    _landmarks,
    _source_paint,
)
from pipeline.config_blocks.railings import (  # noqa: F401
    _RAILING_ROLES,
    RailingClass,
    Railings,
    _railing_class,
    _railings,
)
from pipeline.config_blocks.roadmarks import (  # noqa: F401
    _ROAD_MARK_ROLES,
    BROKEN_LEFT,
    BROKEN_RIGHT,
    BROKEN_SIDES,
    LONGITUDINAL,
    MARK_AXES,
    TRANSVERSE,
    RoadMark,
    RoadMarks,
    _road_mark,
    _road_marks,
)
from pipeline.config_blocks.roads import (  # noqa: F401
    _CARRIAGEWAY_EDGE_ROLES,
    _KERBSIDE_AUDIT_ROLES,
    _KERBSIDE_ROLES,
    _ROAD_LAYER_ROLES,
    BACKWARD,
    BOTH,
    CARRIAGEWAY_AREA,
    CARRIAGEWAY_GEOMETRIES,
    CARRIAGEWAY_LINE,
    DATUM,
    DIRECTIONS,
    FORWARD,
    GROUND_SOURCES,
    KERB_DOUBLE,
    KERB_KINDS,
    KERB_SINGLE,
    TERRAIN,
    CarriagewayEdge,
    CarriagewayRegion,
    CarriagewaySurvey,
    Carve,
    Clearance,
    DeckSampling,
    Fence,
    GroundProfile,
    Join,
    KerbsideAudit,
    KerbsideRestrictions,
    RoadNetwork,
    RoadSurface,
    WidthBounds,
    _by_fastest_rule,
    _carriageway_edge,
    _carriageway_region,
    _carriageway_survey,
    _carve,
    _clearance,
    _deck_sampling,
    _elevation_level_int,
    _fence,
    _ground_profile,
    _join,
    _kerbside,
    _kerbside_audit,
    _lane_lines,
    _pair,
    _road_network,
    _road_surface,
    _sampling_block,
    _survey_levels,
    _thresholds,
    _touchdown_levels,
    _width_bounds,
)
from pipeline.config_blocks.signs import (  # noqa: F401
    _SIGN_POLE_ROLES,
    _SIGN_ROLES,
    SIGN_ARROW_BENT_LEFT,
    SIGN_ARROW_BENT_RIGHT,
    SIGN_ARROW_DOUBLE,
    SIGN_ARROW_DOWN_LEFT,
    SIGN_ARROW_DOWN_RIGHT,
    SIGN_ARROW_LEFT,
    SIGN_ARROW_RIGHT,
    SIGN_ARROW_U,
    SIGN_ARROW_UP,
    SIGN_BACK_COLOUR,
    SIGN_BACKSLASH,
    SIGN_BAR,
    SIGN_BOARD_TALL,
    SIGN_BOARD_WIDE,
    SIGN_CHEVRONS,
    SIGN_DISC,
    SIGN_DRAWINGS,
    SIGN_OCTAGON,
    SIGN_PLATES,
    SIGN_RANK_DEFAULT,
    SIGN_RANKS,
    SIGN_RECT,
    SIGN_RECT_INFO,
    SIGN_RECT_WIDE,
    SIGN_SLASH,
    SIGN_TEE,
    SIGN_TEE_BAR,
    SIGN_TEXT,
    SIGN_TRIANGLE_DOWN,
    SignFace,
    SignLayer,
    Signs,
    _signs,
)
from pipeline.config_blocks.sources import (
    PagedSource,
    TiledSource,
    _extra_cas,
    _paged_source,
    _tiled_source,
)
from pipeline.config_blocks.tramway import (  # noqa: F401
    _TRAMWAY_ROLES,
    Tramway,
    _tramway,
)
from pipeline.crs import (
    GameTransform,
    GeodeticBounds,
    PlanExtent,
    ProjectedBounds,
    project_bounds,
)

SUPPORTED_SCHEMA = 5
# How far a shipped colour may sit from the `reflectance` it declares, in
# percentage points of luminance. One 8-bit step at the lightest end of this
# palette is worth ~0.4, so this is a round-trip through `#rrggbb` and no more —
# see `_check_reflectance` for why it is deliberately not slack.
EXPOSURE_TOLERANCE_PCT = 0.5
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "hong_kong.yaml"
# Where every stage writes its output. One definition, because two stages
# writing into the same tree from two of them is how they end up disagreeing.
OUT_ROOT = Path(__file__).resolve().parent.parent / "out"

# The Godot project. The pipeline writes nothing here — `tools/sync_generated.sh`
# does the copying — and reads exactly one thing: the committed authored landmark
# models, which `clearance.py` must measure because they stand in the street like
# any other building. Named here beside the roots that resolve `res://` prefixes,
# so there is one place the pipeline admits the game tree exists rather than a
# `parents[2]` buried in a stage.
GAME_ROOT = Path(__file__).resolve().parent.parent.parent / "game"


@dataclass(frozen=True)
class RegionConfig:
    id: str
    name: str
    bounds: GeodeticBounds
    tile_size_m: float


# The four sides of a region, named as the compass reads them in the geodetic
# frame. In game space east is +x, west is -x, south is +z and north is -z
# (`GameTransform.from_bounds` anchors the origin at the north-west corner).
SIDES = ("west", "east", "south", "north")


# ⚠️ **The rank is load-bearing twice**, and the second use is why the sheet
# classes are transcribed rather than collapsed to "main or not". Besides
# ordering the stack, `signs.py` refuses a post carrying *nothing but* plates of
# this rank: a supplementary plate qualifies the sign above it, and with that
# sign out of scope (`Q65`) the arrow points at nothing. See `SUPPLEMENTARY`
# there for the Road Users' Code wording that makes the case.
SIGN_RANK_SUPPLEMENTARY = SIGN_RANKS["supplementary"]


@dataclass(frozen=True)
class Config:
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
    # Datasets served a page at a time and assembled at fetch (`Q94`).
    paged_sources: dict[str, PagedSource]
    # Every colour the city ships, by name. ⚠️ **Top-level rather than a member
    # of `buildings:`** — `roads:` draws from it too, and burying it under one of
    # its two consumers would make the other reach across for its asphalt. That
    # asymmetry is not hypothetical: it is the shape that let `235aa4f` re-expose
    # `buildings:` and miss `roads:`.
    materials: dict[str, Material]
    buildings: BuildingStyle
    roads: RoadNetwork
    fares: Fares
    # The surveyed building-block layer, when the city has one (`Q47`). Optional
    # with a default — a city without a topographic source builds as before.
    podiums: PodiumBlocks | None = None
    # Published carriageway edges (`Q57`) — read by `tools/carriageway_margin.py`
    # AND, since `Q95`, by `pipeline/carriageway.py`, which measures `width_m`
    # from them. Optional: absent, every edge keeps its authored width and the
    # region is honestly unmeasurable rather than measured against an invented
    # width.
    carriageway_survey: CarriagewaySurvey | None = None
    # Which edges `pipeline/carve.py` cuts structure back from (`P3-28`).
    # Optional: absent, that stage writes its document and touches no tile,
    # so the bundle is byte-identical to a build without it.
    carve: Carve | None = None
    # Optional because a city of one region has no seam to read across, and
    # absent it reads as "no neighbour widens anything", which is the pre-`P5-7`
    # state exactly.
    join: Join | None = None
    # How `pipeline/region.py` builds the level-0 carriageway as a region
    # (`Q129`, `P3-33b`). Optional: absent, the stage writes nothing and the
    # level-0 road stays a ribbon.
    carriageway_region: CarriagewayRegion | None = None
    # The bar `P3-29`'s player fence is set at (the car's own width), as opposed
    # to `roads.lane_width_m`, which is what traffic is routed on. Optional:
    # absent, nothing is fenced and the bundle is byte-identical.
    clearance: Clearance | None = None
    # How `pipeline/fence.py` dresses the edges `clearance` fences (`P3-29`).
    # Optional: absent, the fenced set is still published and no barrier stands
    # at it — which `Q19` forbids shipping, and which a build can still be in.
    fence: Fence | None = None
    # The published tramway, drawn by `pipeline/tramway.py` (`Q58`). Optional
    # for the same reason `podiums` is, and with a sharper consequence: a city
    # without the block ships no `tram.glb` and the manifest names none, where
    # inventing rails off `roads.tram_streets` would put them a measured 3.26 m
    # from where the estate says they are.
    tramway: Tramway | None = None
    # Published turn arrows, drawn by `pipeline/arrows.py` (`Q53`). Optional for
    # the same reason `tramway` is: a city whose estate publishes no marking
    # symbols ships no `arrows.glb` and the manifest names none. ⚠️ The
    # alternative — inferring arrows from junction topology — is what `Q53`
    # priced as content that would be *invented*, and the whole argument for
    # this stage is that it is read instead.
    arrows: Arrows | None = None
    signs: Signs | None = None
    # Published lamp posts, drawn by `pipeline/lamps.py` (`P3-26`). Optional on
    # the same terms as the blocks around it, and the fallback it deliberately
    # does not offer is the plainest of all: a lamp every N metres down every
    # drawn kerb. The estate publishes 1,263 surveyed positions at a p50 16.74 m
    # pitch, and a derived rhythm would be `Q54`'s invention on the one property
    # — regularity — that is this layer's entire visual content.
    lamps: Lamps | None = None
    # Published yellow box junctions, drawn by `pipeline/boxjunctions.py`
    # (`P3-18`). Optional for the same reason `arrows` is — and the fallback it
    # deliberately does not offer is sharper: the region publishes 20 boxes
    # against 393 junction nodes, so deriving placement from topology would be
    # wrong nineteen times in twenty.
    boxjunctions: BoxJunctions | None = None
    # Published pedestrian railings, drawn by `pipeline/railings.py` (`P3-19`).
    # Optional on the same terms as the three blocks above: a city whose estate
    # publishes no railing layer ships none rather than running a fence down
    # every kerb it drew.
    railings: Railings | None = None
    # Published stop and give-way lines, drawn by `pipeline/roadmarks.py`
    # (`P3-23`). Optional on the same terms as the four blocks above: a city
    # whose estate publishes no transverse markings ships none rather than
    # painting a stop line at every junction node it found.
    road_marks: RoadMarks | None = None
    # Hero buildings shipped as authored models (`P3-6`). Empty for a city
    # without any: the building stage then excludes nothing and the export
    # writes an empty landmarks document.
    landmarks: tuple[Landmark, ...] = ()
    # Committed CA certificates that complete a publisher's TLS chain, resolved
    # to absolute paths at load. For hosts that serve their chain without the
    # issuing intermediate; verification is never relaxed, only completed.
    extra_cas: tuple[Path, ...] = ()

    @property
    def source_ids(self) -> set[str]:
        """Every fetchable source name, of any of the three kinds."""
        return set(self.sources) | set(self.tiled_sources) | set(self.paged_sources)

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

    # The city itself is not config (`Q100`): these four read `hongkong.py`, and
    # are properties rather than fields so no caller can construct a config for
    # a city that does not exist.
    @property
    def id(self) -> str:
        return hongkong.CITY_ID

    @property
    def name(self) -> str:
        return hongkong.CITY_NAME

    @property
    def projected_crs(self) -> str:
        """CRS the source datasets are published in; all pipeline geometry lives here."""
        return hongkong.PROJECTED_CRS

    @property
    def geodetic_crs(self) -> str:
        """Datum the region bounds are expressed in — never assumed (`P0-4`)."""
        return hongkong.GEODETIC_CRS

    def out_dir(self, region_id: str, root: Path | None = None) -> Path:
        """Where a region's build output goes.

        The single definition of the out-tree layout, as `fetch.artefact_path`
        is for the sources tree. Every stage resolves through this rather than
        rebuilding `<root>/<region>`, so the three that write there cannot
        disagree about it.
        """
        return (root or OUT_ROOT) / region_id

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
        region, which `load_config` checks.
        """
        region = self.game_transform(region_id)
        city = self.city_transform()
        return (
            region.origin_easting - city.origin_easting,
            region.origin_elevation - city.origin_elevation,
            city.origin_northing - region.origin_northing,
        )

    def neighbours(self, region_id: str) -> dict[str, str]:
        """The declared regions sharing a whole edge with this one, by side.

        Derived from the bounds rather than declared, so two regions cannot
        disagree about whether they are neighbours. "Whole edge" is literal for
        the first build (`Q116`): the shared longitude or latitude is equal and
        the extents along it are identical, so the union of the two rectangles
        is a rectangle and `roads.clip` needs no second shape. A pair that
        touches along part of an edge is refused at load rather than treated as
        two strangers — see `_check_regions_are_disjoint_or_share_a_whole_edge`.
        """
        mine = self.region(region_id).bounds
        found: dict[str, str] = {}
        for other_id, other in self.regions.items():
            if other_id == region_id:
                continue
            side = _shared_whole_edge(mine, other.bounds)
            if side is not None:
                found[side] = other_id
        return found

    def read_reach(self, region_id: str) -> dict[str, float]:
        """Metres to read past each side of the region: `join.reach_m` where a
        neighbour shares that side, 0.0 everywhere else."""
        reach = 0.0 if self.join is None else self.join.reach_m
        near = self.neighbours(region_id)
        return {side: reach if side in near else 0.0 for side in SIDES}

    def read_bounds(self, region_id: str) -> GeodeticBounds:
        """The geodetic rectangle a region's sheets are selected on.

        The reach is converted to degrees on the region's own projected extent,
        which is exact enough for a sheet that is kilometres across and lets
        `fetch.select_tiles` keep comparing degrees to degrees.
        """
        region = self.region(region_id).bounds
        projected = self.projected_bounds(region_id)
        reach = self.read_reach(region_id)
        per_lon = (region.east - region.west) / projected.width_m
        per_lat = (region.north - region.south) / projected.height_m
        return GeodeticBounds(
            west=region.west - reach["west"] * per_lon,
            east=region.east + reach["east"] * per_lon,
            south=region.south - reach["south"] * per_lat,
            north=region.north + reach["north"] * per_lat,
        )

    def read_box(self, region_id: str) -> ProjectedBounds:
        """The projected rectangle a region's vector sources are read with."""
        bounds = self.projected_bounds(region_id)
        reach = self.read_reach(region_id)
        return ProjectedBounds(
            min_easting=bounds.min_easting - reach["west"],
            min_northing=bounds.min_northing - reach["south"],
            max_easting=bounds.max_easting + reach["east"],
            max_northing=bounds.max_northing + reach["north"],
        )

    def read_extent(self, region_id: str) -> PlanExtent:
        """`(low, high)` in game plan metres — `region_high`'s box, widened by the reach.

        `low` is `(0, 0)` for a region with no western or northern neighbour and
        negative where one exists: game x runs east from the origin and z runs
        south, so a neighbour on the west or north lies at negative coordinates.
        """
        high_x, high_z = self.region_high(region_id)
        reach = self.read_reach(region_id)
        return (
            (-reach["west"], -reach["north"]),
            (high_x + reach["east"], high_z + reach["south"]),
        )

    def frame_offset(self, other_id: str, *, frame: str) -> tuple[float, float, float]:
        """`other_id`'s origin in `frame`'s game coordinates: the one translation
        that moves anything authored in `other_id`'s frame into `frame`'s.

        Exact in float for the reason `rect_of` gives — both origins are whole
        metres — and it equals `city_offset(other) - city_offset(frame)`
        component-wise, `[1649, 0, 0]` for Causeway Bay into Wan Chai. The graph
        merge (`join.py`) and the resident budget's pair mode both move a region
        by it, so they cannot disagree about where the neighbour is.
        """
        own = self.game_transform(frame)
        other = self.game_transform(other_id)
        x, y, z = own.to_game(other.origin_easting, other.origin_northing, other.origin_elevation)
        return (float(x), float(y), float(z))

    def rect_of(self, other_id: str, *, frame: str) -> PlanExtent:
        """`other_id`'s own clip rectangle — `(0, 0)` to its `region_high` in its
        frame — expressed in `frame`'s game plan metres as `(low, high)`.

        The two origins are whole metres (`GameTransform.from_bounds` floors and
        ceils them), so the translation between frames is exact in float and
        two neighbours computing the same rectangle from opposite sides get the
        same numbers. That is what lets `clip_extent` be identical in both
        builds, which is what `Q116`'s cut rests on.
        """
        bounds = self.projected_bounds(other_id)
        low_x, _, low_z = self.frame_offset(other_id, frame=frame)
        high_x, _, high_z = self.game_transform(frame).to_game(
            bounds.max_easting, bounds.min_northing
        )
        return ((low_x, low_z), (high_x, high_z))

    def clip_extent(self, region_id: str) -> PlanExtent:
        """The box a region's roads are clipped to (`Q116`, `P5-7e`): the union
        of its own rectangle and every declared neighbour's.

        A rectangle, because `neighbours` admits only whole shared edges, so
        `roads.clip` needs no second shape. A region with no neighbour gets
        `(0, 0)`-`region_high`, the pre-`P5-7` clip exactly. ⚠️ **This is not the
        read box**: sources are read `join.reach_m` past the shared edge and
        roads are kept whole across it, so a crossing run longer than the reach
        carries stations no source covered — `roads.py` counts them.

        🔴 **Extended along the shared axis ONLY.** The two regions share the
        same latitudes, but a latitude projects to a slightly different
        northing 1.5 km further east, so a neighbour's rectangle sits a few
        centimetres north or south of this one. Taking the union across that
        axis too moved where **45** of Wan Chai's own outer-edge runs were cut,
        for nothing. The price is that the two neighbours' boxes differ by
        those centimetres across the shared axis, so a feature cut at the outer
        edge *inside the neighbour's territory* could in principle split into
        a different number of runs on the two sides; `tools/join_seam.py`
        counts a foreign copy whose identity the owner does not publish.
        """
        (low_x, low_z), (high_x, high_z) = self.rect_of(region_id, frame=region_id)
        for side, other in self.neighbours(region_id).items():
            (x0, z0), (x1, z1) = self.rect_of(other, frame=region_id)
            if side == "west":
                low_x = min(low_x, x0)
            elif side == "east":
                high_x = max(high_x, x1)
            elif side == "north":
                low_z = min(low_z, z0)
            elif side == "south":
                high_z = max(high_z, z1)
            else:
                raise ValueError(f"neighbour side {side!r} is not one of {SIDES}")
        return ((low_x, low_z), (high_x, high_z))

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


def load_config(path: Path | None = None) -> Config:
    """Read and validate the config, `etl/config/hong_kong.yaml` by default."""
    path = path or CONFIG_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} is not a YAML mapping")
    reads: list[_Read] = []
    document = _tracked(document, str(path), reads)

    version = document.get("schema_version")
    if version != SUPPORTED_SCHEMA:
        raise ValueError(f"{path} declares schema_version {version!r}, expected {SUPPORTED_SCHEMA}")
    regions = _require(document, "regions", path)
    if not regions:
        raise ValueError(f"{path} defines no regions")

    # Parsed before anything that could reference it, so every `table.get` below
    # resolves against a complete table — a material declared after its first use
    # would otherwise fail on document order rather than on being absent.
    table = _MaterialTable(_materials(_require(document, "materials", path), f"{path}:materials"))

    city = Config(
        elevation_levels=_elevation_levels(_require(document, "elevation_levels", path), path),
        bounds=_bounds(_require(document, "bounds", path), f"{path}:bounds"),
        regions={region_id: _region(region_id, body, path) for region_id, body in regions.items()},
        sources={str(k): str(v) for k, v in (document.get("sources") or {}).items()},
        tiled_sources={
            str(source_id): _tiled_source(str(source_id), body, path)
            for source_id, body in (document.get("tiled_sources") or {}).items()
        },
        paged_sources={
            str(source_id): _paged_source(str(source_id), body, f"{path}:paged_sources")
            for source_id, body in (document.get("paged_sources") or {}).items()
        },
        # Copied rather than aliased: `table` is load-scoped and mutable, and a
        # frozen config holding a live reference into it is a shape that only
        # works while nothing keeps the table.
        materials=dict(table.declared),
        buildings=_building_style(
            _require(document, "buildings", path), f"{path}:buildings", table
        ),
        roads=_road_network(_require(document, "roads", path), f"{path}:roads", table),
        fares=_fares(_require(document, "fares", path), f"{path}:fares"),
        podiums=(
            _podium_blocks(document["podiums"], f"{path}:podiums")
            if document.get("podiums") is not None
            else None
        ),
        carriageway_survey=_carriageway_survey(
            document.get("carriageway_survey"), f"{path}:carriageway_survey"
        ),
        carve=_carve(document.get("carve"), f"{path}:carve"),
        carriageway_region=_carriageway_region(
            document.get("carriageway_region"), f"{path}:carriageway_region"
        ),
        join=_join(document.get("join"), f"{path}:join"),
        clearance=_clearance(document.get("clearance"), f"{path}:clearance"),
        fence=_fence(document.get("fence"), f"{path}:fence"),
        tramway=_tramway(document.get("tramway"), f"{path}:tramway", table),
        arrows=_arrows(document.get("arrows"), f"{path}:arrows"),
        signs=_signs(document.get("signs"), f"{path}:signs"),
        lamps=_lamps(document.get("lamps"), f"{path}:lamps", table),
        boxjunctions=_boxjunctions(document.get("boxjunctions"), f"{path}:boxjunctions"),
        railings=_railings(document.get("railings"), f"{path}:railings"),
        road_marks=_road_marks(document.get("road_marks"), f"{path}:road_marks"),
        landmarks=_landmarks(document.get("landmarks") or [], f"{path}:landmarks", table),
        extra_cas=_extra_cas(document.get("extra_cas"), path),
    )
    _check_regions_lie_within_the_city(city, path)
    _check_regions_are_disjoint_or_share_a_whole_edge(city, path)
    # Usage before exposure, so a stray entry is reported as stray. The other
    # order exposure-checks a colour that ships nowhere and leads with whichever
    # complaint that raises, which is the less actionable of the two.
    _check_every_material_is_used(table, path)
    _check_reflectance(city, path)
    _check_deck_sampling_has_a_structure_class(city, path)
    _check_widening_levels_are_mapped(city, path)
    _check_touchdown_levels_are_mapped(city, path)
    _check_survey_levels_are_mapped(city, path)
    _check_source_exists(city, city.roads.source, f"{path}:roads.source")
    if city.roads.kerbside is not None and city.roads.kerbside.audit is not None:
        _check_source_exists(
            city,
            city.roads.kerbside.audit.source,
            f"{path}:roads.kerbside_restrictions.audit.source",
        )
    for index, group in enumerate(city.fares.groups):
        _check_source_exists(city, group.source, f"{path}:fares.groups[{index}].source")
    if city.podiums is not None:
        _check_tiled_source_exists(city, city.podiums.source, f"{path}:podiums.source")
    if city.carriageway_survey is not None:
        for index, edge in enumerate(city.carriageway_survey.edges):
            _check_declared_source(city, edge, f"{path}:carriageway_survey.edges[{index}].source")
    if city.tramway is not None:
        _check_declared_source(city, city.tramway, f"{path}:tramway.source")
    if city.arrows is not None:
        _check_declared_source(city, city.arrows, f"{path}:arrows.source")
    if city.boxjunctions is not None:
        _check_declared_source(city, city.boxjunctions, f"{path}:boxjunctions.source")
    if city.railings is not None:
        _check_declared_source(city, city.railings, f"{path}:railings.source")
    if city.road_marks is not None:
        _check_declared_source(city, city.road_marks, f"{path}:road_marks.source")
    if city.signs is not None:
        _check_declared_source(city, city.signs, f"{path}:signs.source")
    _check_landmarks_lie_within_a_region(city, path)
    _check_carve_regions_are_declared(city, path)
    unread = _unread(reads)
    if unread:
        # A key nothing read is a setting that tunes nothing — see `_Read`.
        raise ValueError(f"{path} declares keys nothing reads: {', '.join(unread)}")
    return city


def _check_declared_source(city: Config, spec: Any, where: str) -> None:
    """A block that names its own `source:` names one the city declares.

    The dispatch on `tiled` is the same five lines for every such block — three
    of them since `P3-15` — and it goes with `fetch.source_reads`, which makes
    the same choice at read time. Typed `Any` rather than through
    `fetch.DeclaredSource` because `config` may not import `fetch`: `fetch`
    imports `config`.
    """
    if spec.tiled:
        _check_tiled_source_exists(city, spec.source, where)
    else:
        _check_source_exists(city, spec.source, where)


def _check_landmarks_lie_within_a_region(city: Config, path: Path) -> None:
    """Every landmark's position falls inside some declared region.

    A landmark outside every region would still have its source meshes
    excluded wherever a sheet carries them, while its model ships nowhere —
    a hole with no hero over it. Checked at load for the reason
    `_check_source_exists` gives: the failure would otherwise surface as a
    validation finding regions away from the typo that caused it.
    """
    rectangles = [city.projected_bounds(region_id) for region_id in city.regions]
    for index, landmark in enumerate(city.landmarks):
        contained = any(
            bounds.min_easting <= landmark.easting <= bounds.max_easting
            and bounds.min_northing <= landmark.northing <= bounds.max_northing
            for bounds in rectangles
        )
        if not contained:
            raise ValueError(
                f"{path}:landmarks[{index}] ({landmark.id}) sits at "
                f"E {landmark.easting}, N {landmark.northing} — inside no declared region"
            )


def _check_carve_regions_are_declared(city: Config, path: Path) -> None:
    """Every region `carve` names is one the city declares.

    🔴 A carve edge id is a per-region ORDINAL (`roads.py`'s
    `edge_id = len(pending)`), so a misspelt region name does not fail loudly —
    it silently carves nothing, which reads exactly like a region that has
    nothing to carve. Checked at load for the reason `_check_source_exists`
    gives, and this is the earliest the mistake can be caught at all: an edge
    *id* is only checkable at stage 6 of 19, against a graph, and then only when
    it happens to fall outside that region's range (`Q120`).
    """
    if city.carve is None:
        return
    for region_id in city.carve.edges:
        if region_id not in city.regions:
            raise ValueError(
                f"{path}:carve.edges names {region_id!r}, which is not a declared region "
                f"— carve edge ids are per-region ordinals, so a list under an unknown "
                f"region names nothing. Declared: {', '.join(sorted(city.regions))}"
            )


def _check_reflectance(city: Config, path: Path) -> None:
    """Every authored colour IS its declared `reflectance`, and that reflectance
    sits inside the range its `source` names (`Q33`, `P5-28c`).

    The rule exists because the palette had no external referent. Colours were
    placed by eye against each other, so the only question a reviewer could ask
    was whether they looked consistent — and a set judged only on internal
    consistency always indicts its most extreme member, right or wrong. Stating
    the material each colour claims to be makes it checkable against published
    albedos instead. What that caught is in `hong_kong.yaml`'s header and
    `docs/ART_DESIGN.md`; it is not repeated here.

    🔴 **Two tests, and only the second one can fail on its own.** Until
    `P5-28c` the colour was `reflectance x exposure_anchor`, and comparing the
    two was a real comparison because the anchor stood between them. The anchor
    lives in the lighting rig now (`Q38`), so a shipped colour *is* its
    reflectance and `luminance(colour) == reflectance` is a round trip through
    `#rrggbb` and nothing else — true by construction, and alone it would be
    `Q72`'s tautology: a rule that reads as enforced and has become unfailable.
    `bounds` is what keeps this a check. It is the numeric half of `source`,
    which every entry already had to state in prose.

    ⚠️ **The round trip is still worth running.** It is what refuses a colour
    edited without its reflectance — the ordinary way this table goes wrong, and
    the one an eye cannot catch at 0.4 of a percentage point.

    ⚠️ **The cross-section property has moved, and this loop is now the wrong
    place to look for it.** The rule was written to be whole-config because the
    colours lived in two unrelated dataclasses, and `235aa4f` re-exposed one and
    not the other — not by argument, but because `roads:` was not in the diff
    that changed `buildings:`. A per-section check would have passed that commit.

    Since `Q34` there is only one section: this loop is total because the
    **table** is, not because the loop is careful. That is a stronger guarantee
    and a more fragile one, because it now depends on something this function
    cannot see — that no colour is authored outside `materials:`. Two things hold
    that, and neither is optional: `_check_every_material_is_used` from this side,
    and `test_no_colour_escapes_the_materials_table` from the other.

    The tolerance is 8-bit quantisation and nothing else. It is not slack for a
    colour that nearly obeys: a value that misses by more than a round-trip
    through `#rrggbb` is asserting a different material, and should either say
    so or be corrected.
    """
    for name, material in city.materials.items():
        check_material_reflectance(material, f"{path}:materials.{name}")


def check_material_reflectance(material: Material, where: str) -> None:
    """One colour against the palette rule — the shared body of
    `_check_reflectance` and `tools/make_landmark.py`'s `check_palette`.

    Shared so the materials table and the landmark palette cannot drift onto
    different definitions of `Q33`: the generator's colours never pass through
    this loader, but they make the same claim and answer to the same tolerance.
    """
    low, high = material.bounds
    if not low <= material.reflectance <= high:
        raise ValueError(
            f"{where} declares reflectance {material.reflectance}%, outside the "
            f"{low}-{high}% its own source names ({material.source!r}). "
            "Correct the colour, or cite a source that covers it — do NOT widen "
            "the bounds to admit the number they were written to grade."
        )
    actual = reflectance(material.colour)
    if abs(actual - material.reflectance) > EXPOSURE_TOLERANCE_PCT:
        red, green, blue = material.colour
        raise ValueError(
            f"{where} is #{red:02x}{green:02x}{blue:02x}, whose "
            f"luminance is {actual:.2f}% — but it declares reflectance "
            f"{material.reflectance}%. "
            "Change the colour, or change the material it claims to be."
        )


def _check_every_material_is_used(table: _MaterialTable, path: Path) -> None:
    """Nothing may be declared in `materials:` that nothing references.

    The reverse direction of the join, and it inherits its argument from the
    `class_reflectance` stray-key check this replaces: a table entry that colours
    nothing parses, loads, and is silently inert — the one way this table can be
    wrong without saying so. Worse here than there, because `_check_reflectance`
    reads the whole table: an unused entry is a colour being *validated* as
    though it ships, which is how a palette acquires members it no longer has.

    Usage is recorded by `_MaterialTable.get` rather than enumerated here, so
    this stays correct when a consumer is added. See that class.
    """
    stray = set(table.declared) - table.used
    if stray:
        raise ValueError(
            f"{path}:materials declares {', '.join(sorted(stray))}, which nothing references. "
            "Every material is a colour the city ships; delete it, or use it."
        )


def _check_deck_sampling_has_a_structure_class(city: Config, path: Path) -> None:
    """Deck sampling names its thresholds, but not the geometry to apply them to.

    The two halves sit in different sections because each follows its own
    precedent — `buildings:` is where sheet class names are declared, `roads:`
    is where road tuning lives, and `roads.py` already reaches across for
    `terrain_class`. The asymmetry with that precedent is what needs a check:
    `terrain_class` is required, so it cannot go missing, while both of these
    are optional and only make sense together.

    One direction only, deliberately. Thresholds with no geometry to apply them
    to would put the carriageway somewhere wrong; a `structure_class` with no
    `deck:` block is merely unused, and refusing it would reject a city whose
    output is correct.
    """
    if city.roads.deck is not None and city.buildings.structure_class is None:
        raise ValueError(
            f"{path}:roads.deck samples elevated structure, but "
            "buildings.structure_class names none. Add it, or drop roads.deck."
        )


def _check_widening_levels_are_mapped(city: Config, path: Path) -> None:
    """A widening rule for a level the city never maps is a rule that never fires.

    The same trap `class_materials` and `class_lod_cell_sizes_m` both refuse: the
    key is a join, so a level merely absent from `elevation_levels` gives a
    config that loads, a surface that builds, and a rule that silently overrides
    nothing. Off-grade ribbon would go on being drawn at its at-grade width,
    which is the defect the table exists to remove — and the output looks like a
    city that never asked for the rule.

    Here rather than in `_road_surface` because it is a cross-section check, and
    `roads:` cannot see `elevation_levels` while it is being parsed.
    """
    _refuse_unmapped_levels(
        city.roads.surface.floor_by_elevation_level,
        city,
        path,
        "roads.surface.floor_by_elevation_level",
    )


def _check_touchdown_levels_are_mapped(city: Config, path: Path) -> None:
    """A touchdown closure for a level the city never maps closes nothing (`Q103`).

    `_check_widening_levels_are_mapped`'s trap at a second key, and worse here:
    a widening rule that never fires draws the ribbon at the wrong width, which
    at least a grader can see. A closure that never fires leaves the network
    *open*, and open is exactly the state this key exists to end — so it would
    read as a fence that is working while the player drives straight past it.

    Here rather than in `_fence` because it is a cross-section check, and
    `fence:` cannot see `elevation_levels` while it is being parsed.
    """
    if city.fence is None:
        return
    _refuse_unmapped_levels(city.fence.touchdown_levels, city, path, "fence.touchdown_levels")


def _refuse_unmapped_levels(levels: Iterable[int], city: Config, path: Path, key: str) -> None:
    """The refusal both level-joined keys make, written once.

    Shared for `_measures`' reason rather than to save lines: the message names
    the offending level *and* what the city does map, and two copies of that
    wording drift apart silently. The two callers' docstrings say why each key
    needs it, which is the part that differs.
    """
    unknown = set(levels) - set(city.elevation_levels)
    if not unknown:
        return
    known = ", ".join(str(level) for level in sorted(city.elevation_levels))
    raise ValueError(
        f"{path}:{key} names level "
        f"{', '.join(str(level) for level in sorted(unknown))}, "
        f"which elevation_levels does not map ({known})"
    )


def _check_survey_levels_are_mapped(city: Config, path: Path) -> None:
    """The third level-joined key, and the trap is the same (`Q103`).

    A survey level the city never maps walks no edge and reports total coverage
    of nothing — which reads as agreement, the same reason `edges` is refused
    empty two fields up rather than treated as absent.
    """
    if city.carriageway_survey is None:
        return
    _refuse_unmapped_levels(city.carriageway_survey.levels, city, path, "carriageway_survey.levels")


def _check_source_exists(city: Config, source_id: str, where: str) -> None:
    """A stage that names a source it cannot fetch is a config error, not a run.

    Caught at load rather than at first use, so a typo fails before the
    pipeline has read 17 MB of geodatabase to discover it.
    """
    # ⚠️ **Paged sources count**, because they assemble to a single file and are
    # read through `cached_source` exactly as a plain one is. The distinction is
    # a fetch-time concern and a consumer must not have to know it (`Q94`).
    if source_id not in city.sources and source_id not in city.paged_sources:
        known = ", ".join(sorted({*city.sources, *city.paged_sources})) or "none"
        raise ValueError(f"{where} names '{source_id}', which is not in sources ({known})")


def _check_tiled_source_exists(city: Config, source_id: str, where: str) -> None:
    """`_check_source_exists`, for a stage that reads a per-sheet dataset."""
    if source_id not in city.tiled_sources:
        known = ", ".join(sorted(city.tiled_sources)) or "none"
        raise ValueError(f"{where} names '{source_id}', which is not in tiled_sources ({known})")


def _check_regions_lie_within_the_city(city: Config, path: Path) -> None:
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


def _shared_whole_edge(mine: GeodeticBounds, other: GeodeticBounds) -> str | None:
    """The side of `mine` along which `other` shares a whole edge, or None.

    Keyed by `SIDES` so the four names have one home: `read_reach` looks a side
    up by that name, and a literal misspelt here would make that lookup miss
    silently on one side of one region.
    """
    same_lat = mine.south == other.south and mine.north == other.north
    same_lon = mine.west == other.west and mine.east == other.east
    shares = {
        "west": same_lat and mine.west == other.east,
        "east": same_lat and mine.east == other.west,
        "south": same_lon and mine.south == other.north,
        "north": same_lon and mine.north == other.south,
    }
    assert set(shares) == set(SIDES)
    return next((side for side in SIDES if shares[side]), None)


def _check_regions_are_disjoint_or_share_a_whole_edge(city: Config, path: Path) -> None:
    """Every pair of declared regions is disjoint, or shares one whole edge (`Q116`).

    Two regions that overlap would both own the roads in the overlap, and two
    that touch along part of an edge make a union that is not a rectangle,
    which `roads.clip` cannot cut to. Both are refused at load, whether or not a
    `join:` block asks for the neighbour, because the membership rule is on
    the bounds and the bounds are what a later `join:` would read.
    """
    regions = list(city.regions.values())
    for index, mine in enumerate(regions):
        for other in regions[index + 1 :]:
            a, b = mine.bounds, other.bounds
            if not a.intersects(b):
                continue
            overlap_lon = min(a.east, b.east) - max(a.west, b.west)
            overlap_lat = min(a.north, b.north) - max(a.south, b.south)
            if overlap_lon > 0 and overlap_lat > 0:
                raise ValueError(
                    f"{path}:regions.{mine.id} and regions.{other.id} overlap — every point "
                    f"belongs to at most one declared region"
                )
            if overlap_lon == 0 and overlap_lat == 0:
                continue  # a corner
            if _shared_whole_edge(a, b) is None:
                raise ValueError(
                    f"{path}:regions.{mine.id} and regions.{other.id} touch along part of an "
                    f"edge — neighbours must share a whole edge with identical extents along "
                    f"it, or be disjoint"
                )


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
