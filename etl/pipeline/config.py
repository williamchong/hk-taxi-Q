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

import math
from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml

from pipeline.colour import reflectance
from pipeline.crs import (
    GameTransform,
    GeodeticBounds,
    ProjectedBounds,
    project_bounds,
)

SUPPORTED_SCHEMA = 3
# How far a shipped colour may sit from `reflectance x exposure_anchor`, in
# percentage points of luminance. One 8-bit step at the lightest end of this
# palette is worth ~0.4, so this is a round-trip through `#rrggbb` and no more —
# see `_check_exposure` for why it is deliberately not slack.
EXPOSURE_TOLERANCE_PCT = 0.5
# Ceiling on `exposure_anchor`. See `_exposure_anchor` — a bound rather than a
# taste limit, and deliberately above 1.0.
EXPOSURE_ANCHOR_MAX = 2.0
# How far a set of draw weights may sit from summing to 1.0. Float addition of
# authored decimals, and nothing else — see `WeightedDraw.build` for why they are
# refused rather than normalised.
WEIGHT_SUM_TOLERANCE = 1e-6
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
    # Filename suffix for downloaded tiles, for publishers whose download URL
    # path carries none (`/directDownload?productName=…&productFormat=FGDB`).
    # Without it such a tile would land as `<id>.bin`, which the zip-aware
    # readers refuse to route through `/vsizip/`.
    tile_suffix: str | None = None


class SurfaceClass(IntEnum):
    """What a tile vertex belongs to, as shipped in `TEXCOORD_0.y` (`P3-7`).

    A tile is one merged primitive, so every class in it arrives at the shader
    through the same material with nothing to tell them apart. This is that
    something. `BuildingStyle.surface_class` decides which one a class gets.

    ⚠️ **The values are a wire format shared with `city_facade.gdshader`**, which
    compares against integer literals. Renumbering here silently repaints the
    city — a viaduct grows windows, or the ground does. They are part of
    `city.json`'s `schema_version`, not a private enumeration.
    """

    # Height-banded massing: bands, windows and the grounding gradient.
    FACADE = 0
    # The region's ground. Reserved rather than used — merging into the tile
    # primitive bought the ground a free draw call and cost it its own material,
    # so a later ground-only treatment needs something to select on and this is
    # cheaper to ship now than to bump the schema for twice (ARCHITECTURE.md).
    GROUND = 1
    # Elevated road structure. Drawn plain: a viaduct soffit has no floors, and
    # banding one is the giveaway that the effect is procedural.
    STRUCTURE = 2


# The most a city may amplify its measured facade chroma by. High enough that no
# defensible art direction hits it, low enough that a typo or a YAML `.inf` does
# — the point of the bound is the refusal, not the number. See `_scale`.
HUE_STRENGTH_MAX = 8.0


@dataclass(frozen=True)
class Material:
    """A real-world surface the city is built out of, and the colour it ships as.

    ⚠️ **The colour and the albedo belong together, and neither belongs on
    `HeightBand`.** Holding them there makes the *shape* of the schema assert that
    material is a function of height — a claim nobody would write down and the
    data refuses: on the 2,171-building photo survey, height explains **0.9%** of
    facade `L*` once log pixel count is controlled. `Q34` has the rest of the
    measurement and the worked example.

    Naming the material instead makes the claim attach to the thing it is about,
    and makes it **portable** (CLAUDE.md hard rule 3): concrete is concrete in the
    second city, where a height-to-material mapping would have to be re-derived
    from scratch.

    ⚠️ **Every colour the city ships is declared here and nowhere else.** That is
    what makes `_check_exposure` total — see its docstring, and
    `_check_every_material_is_used` for the other direction.
    """

    # The key this material is declared under. Carried on the object so an error
    # raised deep in a consumer can name it without threading the key along.
    name: str
    colour: tuple[int, int, int]
    # Real-world diffuse albedo, as a percentage. See `_check_exposure` for what
    # it is checked against and why it is required.
    reflectance: float
    # Where that number comes from, in free text. Required, and deliberately not
    # validated: the point is that somebody had to type an answer, including
    # "back-derived, not cited" where that is the truth. An unsourced albedo is
    # how the palette drifted before `Q33`.
    source: str


class _MaterialTable:
    """The declared materials, plus which of them anything actually referenced.

    Load-scoped and mutable, unlike everything else here. `get` is the *only* way
    a material reaches a config object, so usage is recorded by the act of using
    it — a consumer added later is counted without anyone remembering to add it
    to a list.

    That is the whole reason this is a class rather than a dict. A hand-written
    enumeration of reference sites in `load_city` would be a second copy of the
    join, and the copy that drifts is the one that quietly stops catching
    anything — which is exactly how `class_reflectance` could have failed.
    """

    def __init__(self, declared: dict[str, Material]) -> None:
        self.declared = declared
        self.used: set[str] = set()

    def get(self, name: str, where: str) -> Material:
        material = self.declared.get(name)
        if material is None:
            raise ValueError(
                f"{where} names material {name!r}, which materials: does not declare. "
                f"Declared: {', '.join(sorted(self.declared)) or '(none)'}"
            )
        self.used.add(name)
        return material


@dataclass(frozen=True)
class HeightBand:
    """A material for buildings up to a given height above their own base.

    ⚠️ **A lightness ramp, not a claim about what buildings are made of.** The
    band a building falls in is chosen by height because the *look* wants tall
    buildings paler, and that is legitimate art direction. What is not
    legitimate is reading the band's material as evidence about the city's
    stock — see `Material` for the measurement that settled it.
    """

    up_to_m: float
    material: Material


@dataclass(frozen=True)
class WeightedDraw:
    """A material chosen from a fixed distribution by one number in [0, 1).

    ⚠️ **Sorted by name, and that is load-bearing rather than tidiness.** The
    draw is a function of position in this tuple, so ordering it by the YAML's
    key order would mean re-indenting or alphabetising a config block repaints
    every building it touches — a diff with no visible intent and a large visible
    effect. Sorting here makes the output depend on the *set* of weights, which
    is what the author actually chose.

    ⚠️ **`bounds` ends at exactly 1.0 by assignment, not by summation.** Floating
    addition of authored weights lands near 1.0, not on it, and a cumulative
    table whose last entry is 0.9999999999 drops whichever building draws above
    it off the end of the search. That is `_phase`'s defect in a different shape:
    rare, silent, and confined to the unlucky object. The sum is validated
    separately, at parse time, where it can still be a useful error.
    """

    materials: tuple[Material, ...]
    bounds: tuple[float, ...]

    @staticmethod
    def build(weights: dict[str, Any], table: _MaterialTable, where: str) -> WeightedDraw:
        """Authored weights, with material *names* resolved through `table`.

        The parsing half, kept apart from `of` so the private table is a loader
        concern and nothing else has to hold one to describe a distribution.
        """
        if not weights:
            raise ValueError(f"{where} is empty — a draw needs at least one material")
        # Through `_number` rather than trusting YAML to have produced floats: a
        # quoted weight reaches `fsum` as a string and raises a bare `TypeError`
        # naming neither the file nor the block, which in a config of forty-odd
        # numbers is most of the answer. `_measures` says the same where it lives.
        return WeightedDraw.of(
            {
                table.get(str(name), where): _number(weight, f"{where}.{name}")
                for name, weight in weights.items()
            },
            where,
        )

    @staticmethod
    def of(weights: Mapping[Material, float], where: str) -> WeightedDraw:
        """A distribution over materials that already exist."""
        if not weights:
            raise ValueError(f"{where} is empty — a draw needs at least one material")
        total = math.fsum(weights.values())
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            # ⚠️ Not normalised. A table summing to 0.9 is one somebody stopped
            # editing, and rescaling it would redistribute the missing tenth
            # across the materials that *are* listed — silently, and in
            # proportions nobody chose.
            raise ValueError(
                f"{where} weights sum to {total:.6f}, not 1.0. "
                f"Weights are a distribution and are not normalised for you."
            )
        for material, weight in weights.items():
            if not 0.0 < weight <= 1.0:
                raise ValueError(f"{where}.{material.name} is {weight}, which is not in (0, 1]")

        # `Material.name` is the sort key, which is the job that field exists to
        # do — ordering on it here is what makes the draw a function of the *set*
        # of weights rather than of the order somebody happened to type them in.
        ordered = sorted(weights, key=lambda material: material.name)
        running = 0.0
        bounds: list[float] = []
        for material in ordered:
            running += weights[material]
            bounds.append(running)
        bounds[-1] = 1.0
        return WeightedDraw(materials=tuple(ordered), bounds=tuple(bounds))

    def pick(self, draw: float) -> Material:
        """The material `draw` in [0, 1) falls to."""
        return self.materials[min(bisect_right(self.bounds, draw), len(self.materials) - 1)]


@dataclass(frozen=True)
class HueSector:
    """One wedge of the hue circle, and what a building in it is built of."""

    from_deg: float
    draw: WeightedDraw


@dataclass(frozen=True)
class ChromaRing:
    """Buildings out to a given chroma, split by hue angle if they need to be.

    ⚠️ **Rings *and* sectors, because chroma alone cannot express the measured
    structure.** The two largest hue clusters in the survey are cool grey at
    `C*` 2.6 and neutral grey at `C*` 3.1 — indistinguishable by chroma, and
    opposite in `b*` (-2.5 against +3.1). A flat chroma bin would merge them.

    Total by construction, which is why it is shaped this way rather than as a
    list of first-match rules: rings reuse `height_bands`' ascending-and-`.inf`
    rule, and sectors partition the circle as long as `from_deg` ascends inside
    [0, 360) — the last one wraps through 360 to the first. A rule list would
    need a reachability check the loader cannot honestly write.
    """

    up_to_chroma: float
    # Exactly one of these. A ring with no hue structure worth naming takes a
    # single draw; one that has it takes sectors.
    draw: WeightedDraw | None
    sectors: tuple[HueSector, ...]

    def draw_for(self, hue_deg: float) -> WeightedDraw:
        if self.draw is not None:
            return self.draw
        index = bisect_right([sector.from_deg for sector in self.sectors], hue_deg) - 1
        # Below the first boundary is the wrap: it belongs to the last sector,
        # which runs from its own `from_deg` through 360 and round to this one.
        return self.sectors[index].draw


@dataclass(frozen=True)
class MaterialAssignment:
    """Which material a building is built of, and on what evidence.

    ⚠️ **The two branches are named for what is *known* about the building, not
    for how the answer is computed**, and that is the correction `Q34` had to
    make to its own first proposal. Falling back to the marginal distribution of
    the surveyed population reads as the natural default and is wrong:
    `facade_hue` is optional by contract, so a clone without the 4.9 GB survey
    must build the **same** city, and a marginal draw would build a different
    one. An unsurveyed building is not a surveyed building whose hue we are
    guessing — it is a building the height ramp answers for, exactly as before.
    """

    # Reached by having no measurement. Required: it is the whole city on a
    # fresh clone.
    by_height: tuple[HeightBand, ...]
    # Reached by having one. Empty where the city states no rule, in which case
    # a surveyed building takes the height ramp too and only its hue is used.
    rings: tuple[ChromaRing, ...]

    def draw_for(self, chroma: float, hue_deg: float) -> WeightedDraw | None:
        for ring in self.rings:
            if chroma <= ring.up_to_chroma:
                return ring.draw_for(hue_deg)
        return None


@dataclass(frozen=True)
class BuildingStyle:
    """How `P1-2` turns source massing into vertex-coloured tiles.

    All of it is tuning data rather than constants in code (CLAUDE.md hard
    rule 4), and all of it is city-shaped: the sub-directory names come from the
    publisher's zip layout, and the palette is Hong Kong's, not a generic city's.
    """

    # Sheet sub-directories holding massing to tile.
    classes: tuple[str, ...]
    # Sheet sub-directory holding the ground. Named here rather than in the
    # pipeline because "TERRAIN(TB)" is a LandsD spelling, not a fact about
    # terrain.
    #
    # Two jobs, one name, deliberately. `roads.py` reads it as a height field to
    # decide how high every road sits (`Q11`), and since `P3-10` it is also one
    # of `classes` and so tiled and drawn. The same geometry serving both is the
    # property that matters: any drift between where roads think the ground is
    # and where it is drawn would show as kerbs at the wrong height on every
    # street in the region.
    terrain_class: str
    # Class holding elevated road structure, which `RoadNetwork.deck` samples an
    # off-grade carriageway's height from. Optional: a city that declares no
    # deck sampling needs none. Always one of `classes`, so the carriageway
    # lands on geometry that ships rather than on geometry only the ETL sees.
    structure_class: str | None
    # Flat material for a class, overriding the height bands.
    #
    # One map, never two. A colour and the albedo it claims are one fact, and
    # splitting them into parallel `class_colours` and `class_reflectance` maps
    # is what makes a join — and the both-directions check guarding it —
    # necessary at all (`Q34`). `_MaterialTable` carries that reasoning.
    class_materials: dict[str, Material]
    # What everything else is built of, and on what evidence. See
    # `MaterialAssignment` — the branch names are a contract, not a description.
    material_assignment: MaterialAssignment
    # Fraction of brightness a building's colour may be varied by, seeded from
    # its own id so the result is stable across runs.
    colour_jitter: float
    # Jitter for a class that must not vary like the rest, overriding the value
    # above. Same units, same range.
    class_colour_jitter: dict[str, float]
    # One clustering cell size per LOD tier, in metres, coarsest last. A 0.0
    # entry is an exact weld that loses nothing; whether a city ships one is a
    # bundle decision, not a rule (Q16).
    lod_cell_sizes_m: tuple[float, ...]
    # Cell sizes for a class that must not decimate like the rest, overriding
    # the table above. Same length, same ordering rule.
    class_lod_cell_sizes_m: dict[str, tuple[float, ...]]
    # How far below its sampled height the drawn ground is placed, in metres.
    #
    # `roads.py` lays the level-0 carriageway at `terrain + 0.0`, so ground and
    # road are coplanar *by construction* and would z-fight the length of the
    # network. The ground drops under the kerb, whose 0.15 m riser and 0.5 m lip
    # are what hide the seam. Sized by measuring what still stands proud of the
    # shipped carriageway — `tools/ground_clearance.py` — not by taste.
    ground_sink_m: float
    # Optional table of per-building hue measured from photographs, named as a
    # bare filename that `buildings.facade_hue` resolves through
    # `fetch.source_dir` — the city id belongs to the tree, not to this value.
    # **Defaulted, and that is the contract**: the survey
    # is a 4.9 GB read that `etl/sources/` caches and `.gitignore` excludes, so a
    # clone that has never run it must still build — and build the same city the
    # height bands alone always produced.
    #
    # ⚠️ **Hue only, never lightness.** The same survey carries a per-building
    # `L*` with a far larger spread and it is deliberately unused; `colour.py`'s
    # header has the reason and the numbers.
    facade_hue_source: str | None = None
    # How far the measured hue is pushed, as a multiple of what was measured.
    # 1.0 is faithful; above it keeps *which* building is warmer and exaggerates
    # only by how much. A stylisation knob, deliberately separated from the
    # measurement so the two cannot be confused.
    facade_hue_strength: float = 1.0
    # Largest fraction of a survey sample that may be vegetation before the row
    # is dropped rather than trusted. A sample that is mostly canopy measured the
    # tree in front of the building, not the building.
    #
    # `None` is no threshold, and it is a separate value rather than 1.0 because
    # 1.0 is a legal threshold: it keeps every row *and* still requires the
    # column, which is a thing a city might mean. Setting any threshold makes the
    # survey's `vegetation` column required — one set against a survey that never
    # recorded it would filter nothing while looking like it filtered.
    facade_hue_vegetation_max: float | None = None
    # Optional per-building survey verdicts consumed into `TEXCOORD_1`
    # (schema 6): the glazing survey's tint table, resolved through
    # `buildings.HUE_SOURCE_ID`, and the vision reader's merged verdict table,
    # resolved through `buildings.GRAMMAR_SOURCE_ID`. **Defaulted on the same
    # contract as `facade_hue_source`**: both are gitignored derived data, and
    # a clone without them must build the same hash-driven city it always
    # built — absent, every building ships the refusal sentinel.
    facade_glazing_source: str | None = None
    facade_grammar_source: str | None = None

    @property
    def height_bands(self) -> tuple[HeightBand, ...]:
        """The unsurveyed ramp, under the name it had before `Q34` nested it."""
        return self.material_assignment.by_height

    def material_for(self, class_id: str, height_m: float) -> Material:
        """The material a class at a height is built of, before any variation.

        The **unsurveyed** answer, and the only one this class can give: a
        surveyed building's material depends on its measured hue and on a seed
        drawn from its id, neither of which is config. `buildings.material_for`
        is the whole rule and falls back to this.

        Split out from `colour_for` by `Q34` so the *choice* of material and the
        extraction of its colour are separable.
        """
        if class_id in self.class_materials:
            return self.class_materials[class_id]
        return next(band.material for band in self.height_bands if height_m <= band.up_to_m)

    def colour_for(self, class_id: str, height_m: float) -> tuple[int, int, int]:
        return self.material_for(class_id, height_m).colour

    def cell_size_m(self, class_id: str, level: int) -> float:
        """Clustering cell for one class at one tier.

        Per class because one cell size does not suit two kinds of geometry.
        A building is a big box: a 1.5 m cell takes half its triangles and
        leaves the silhouette. An elevated road deck is *thin* — a 1.5 m cell
        is thicker than the deck, so the top and bottom surfaces cluster into
        one another and the structure folds into a warped sliver. `P2-1`
        measured that on screen at Gloucester Road.
        """
        return self.class_lod_cell_sizes_m.get(class_id, self.lod_cell_sizes_m)[level]

    def is_ground(self, class_id: str) -> bool:
        """Whether this class is the region's ground rather than something on it.

        Named once because two decisions in `buildings.py` turn on it and they
        have to agree: the ground is the class that gets **sunk** under the
        carriageway, and the class clustered as a **height field**. A city that
        drifted between the two would ship ground sunk but torn, or welded but
        floating — and neither says anything on the way past.
        """
        return class_id == self.terrain_class

    def surface_class(self, class_id: str) -> int:
        """Which kind of surface a class is, as the marker `P3-7` ships per vertex.

        The window-band shader has to tell a façade from a viaduct soffit from
        the pavement, and a vertex carries nothing that says which it is. So the
        ETL says, in `TEXCOORD_0.y`'s integer part — see `buildings._facade_uv`.

        **Derived from config that already exists rather than from a new key**,
        because the distinction is one the palette has always drawn: a class with
        a flat `class_materials` entry is a thing whose colour does not depend on
        how tall it is, and that is exactly the set with no floors to band. Hard
        rule 3 holds — no class name reaches this file, and a second city gets
        the right answer from its own palette without writing the mapping twice.

        `FACADE` is the fallback rather than a listed case, so a class the
        palette height-bands is banded by the shader too. That is the safe
        direction: a new massing class reads as a building until someone gives it
        a flat colour, and one that should not be banded announces itself by
        needing a colour that height cannot supply.
        """
        if self.is_ground(class_id):
            return SurfaceClass.GROUND
        if class_id in self.class_materials:
            return SurfaceClass.STRUCTURE
        return SurfaceClass.FACADE

    def jitter_for(self, class_id: str) -> float:
        """Brightness variation for one class.

        Per class for the same reason as `cell_size_m`: the default suits a
        city of separate objects and the ground is not one. Jitter is seeded per
        *source mesh*, which for buildings is one building — the variation is
        what stops a height band reading as a single mass. The ground arrives as
        a handful of sheet-sized meshes, so the same rule would paint the region
        in as many shades, with the seams on the publisher's sheet boundaries.
        """
        return self.class_colour_jitter.get(class_id, self.colour_jitter)


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


@dataclass(frozen=True)
class PodiumBlocks:
    """The building-block layer of a per-sheet topographic source (`Q47`).

    `source` names a `tiled_sources` entry. `member` is the path of the
    geodatabase inside each sheet's zip, with `{tile}` standing for the sheet
    id — how a publisher nests its archive is a packaging fact like a column
    name, so it is declared here and never spelt in pipeline logic.
    """

    source: str
    member: str
    blocks: SourceLayer


def _field(fields: Mapping[str, str], role: str, where: str) -> str:
    """The publisher's column name for a role the pipeline asked for.

    Shared by every configured schema mapping, so the error a missing role
    produces reads the same wherever it is hit.
    """
    if role not in fields:
        known = ", ".join(sorted(fields)) or "none"
        raise KeyError(f"{where} declares no field for '{role}'. Declared: {known}")
    return fields[role]


def _measures(
    body: dict[str, Any], where: str, names: tuple[str, ...], *, positive: bool = False
) -> dict[str, float]:
    """Required float measurements, refused when their value cannot be used.

    Shared so a bad measurement reads the same wherever it is hit, as `_field`
    is for a missing role.

    Finiteness is checked rather than assumed. YAML 1.1 resolves `.nan` and
    `.inf` — this file relies on that for `height_bands`' open last band — and a
    NaN passes every sign test below, then silently makes false every comparison
    it feeds downstream. That is the one bad value that never announces itself.
    """
    values: dict[str, float] = {}
    for name in names:
        value = _require(body, name, where)
        try:
            values[name] = float(value)
        except (TypeError, ValueError):
            # `float()` alone names the bad value but not where it came from,
            # which in a config of forty-odd numbers is most of the answer.
            raise ValueError(f"{where}:{name} is {value!r}, which is not a number") from None

    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"{where}:{name} must be a finite number, got {value}")
        if value < 0.0 or (positive and value == 0.0):
            limit = "must be positive" if positive else "must not be negative"
            raise ValueError(f"{where}:{name} {limit}, got {value}")
    return values


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
    # Off-grade carriageway, by elevation level. Both *reasons* for widening are
    # at-grade reasons, and they are stated where the values are — see the table
    # in `hong_kong.yaml`. `widen_for` explains only why this rule wins outright.
    widen_by_elevation_level: dict[int, float]
    # `Q23`: the same claim made per *station* rather than per edge. A road does
    # not become a bridge at an edge boundary, so a level-0 edge can spend its
    # first 90 m on a ramp deck and the rest on the street — 1,070 m of the
    # region's level-0 centreline does exactly that. `roads.py` publishes which
    # stations those are; this is what they are drawn at.
    widen_on_structure: float
    # How far back along the approach the widening is given up, so the ribbon
    # arrives at the deck already narrow. Zero would be the literal reading of
    # "stop widening at the structure" and it jogs the carriageway edge and its
    # kerb sideways by ~1.9 m between two stations, which reads as a defect
    # rather than as a bridge.
    structure_taper_m: float

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

    # ⚠️ **Named, not authored here.** These two colours are in a different
    # dataclass from the rest of the palette, and that is precisely how they
    # escaped the one exposure change every other colour took (`235aa4f`). They
    # now reference the same `materials:` table as everything else, so a section
    # can no longer be re-exposed without its neighbour — there is only one place
    # left to change. See `_check_exposure`.
    surface_material: Material
    kerb_material: Material

    def widen_for(
        self, speed_limit_kph: int, *, elevation_level: int, on_structure: bool = False
    ) -> float:
        """Widening factor for one station, by level if the level has a rule,
        else by whether that station is on structure, else from the fastest
        matching speed rule.

        Expressways are already drawn wide by their lane count and need less
        help; a two-lane street is where the widening earns its keep.

        The level rule wins outright rather than combining, because the two are
        different kinds of claim. The speed table is a preference about how much
        room a fast road wants; a level rule is a statement about what the
        carriageway is sitting on. `P2-7` put the off-grade ribbon on its
        structure, and a viaduct deck does not get wider because the road on it
        is signed at 70 — it ends at a parapet. A widened ribbon there overhangs
        into the air beside the deck, which is both wrong and, with a guardrail
        drawn beyond it, unreadable.

        ⚠️ **The level rule is still checked first, and that ordering is load
        bearing rather than historical.** `on_structure` is a per-station fact
        and the level table is a per-edge one, so letting the station win would
        change what an off-grade edge is drawn at wherever the structure was
        never found — `ISLAND EASTERN CORRIDOR`'s stub, which takes the flat
        offset precisely because nothing is under it, would go back to being
        widened. Checking the level first leaves levels 1 and -1 exactly as
        `P2-7` measured them, so `Q23` moves level 0 and nothing else.
        """
        if elevation_level in self.widen_by_elevation_level:
            return float(self.widen_by_elevation_level[elevation_level])
        if on_structure:
            return float(self.widen_on_structure)
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
class DeckSampling:
    """How `P2-7` takes an off-grade carriageway's height from its structure.

    `elevation_levels` gives a level one flat offset, which `Q20` measured as
    |error| p90 4.19 m against the real decks, with the ribbon sitting *below*
    the deck — inside the structure — in 66% of samples. These four values
    replace that constant with a measurement of what the road is built on.

    Tuning data rather than constants in code (CLAUDE.md hard rule 4), and none
    of it is derivable: every value here was measured on Wan Chai, and a city
    whose flyovers are thicker or whose ramps are shorter will need its own.
    """

    # Station spacing along an edge before sampling. Justified by the worst
    # vertex gap rather than the typical one — see the city file.
    resample_m: float
    # Two hits further apart than this are separate structures rather than the
    # top and bottom faces of one deck.
    slab_gap_m: float
    # How far below the terrain a sample may sit and still be a deck. The
    # structure class is not only elevated carriageway, and a sample under the
    # ground is the sign that something else was hit.
    max_below_terrain_m: float
    # Where the lift of a level-0 edge that starts on a ramp stops: a structure top
    # this close to the ground is the ground. Also the residual step that lift
    # is allowed to leave behind, which is what bounds it.
    at_grade_m: float
    # How far above the sampled structure the carriageway is drawn. Not a fudge
    # factor: a real road is a wearing course laid *on* a structural deck, and
    # this is that layer. It also has to absorb the tile decimation, which is
    # what makes it a measured value rather than a nominal one.
    clearance_m: float


@dataclass(frozen=True)
class GroundProfile:
    """How `Q24` follows the ground along an at-grade road.

    `simplify` keeps the vertices a centreline needs *in plan* — 2.0% of the
    source's on this region — and the terrain is sampled only at those. Between
    two of them the road is a straight chord over ground that curves, so on a
    crest the ground rises through a carriageway that never asked about it.
    Since `P3-10` drew and collided that ground, the chord is solid geometry
    standing in legal road.

    The sibling of `DeckSampling` in job and in shape: both densify a run before
    asking a height field about it. What differs is that a deck is *found* and
    the ground is merely followed, so this needs a tolerance where that needs a
    slab gap.

    Tuning data rather than constants in code (CLAUDE.md hard rule 4), and both
    values were measured on Wan Chai rather than chosen.
    """

    # Station spacing along an edge before sampling, as `DeckSampling`'s and for
    # the same reason.
    resample_m: float
    # Vertical error a station has to beat to be kept after sampling.
    #
    # Densifying without thinning doubles the region's level-0 stations to buy
    # 0.107% of carriageway under proud ground; thinning at this tolerance
    # reaches 0.110% for **+12%**. Most of Wan Chai is flat and needs no extra
    # vertex at all — the tolerance is what spends them where the ground bends.
    # Zero keeps every inserted station, which is the un-thinned behaviour.
    tolerance_m: float


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

    # How `P2-7` takes an off-grade carriageway's height from the structure it
    # is built on. `None` leaves every level on its flat `elevation_levels`
    # offset, which is all a city whose sources carry no structure can do.
    deck: DeckSampling | None

    # How `Q24` follows the ground along an at-grade road. `None` samples the
    # terrain only at the vertices `simplify` left, which is what shipped before
    # the ground was drawn and nothing could be compared against.
    ground_profile: GroundProfile | None

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
    # Every colour the city ships, by name. ⚠️ **Top-level, a sibling of
    # `exposure_anchor` rather than a member of `buildings:`** — `roads:` draws
    # from it too, and burying it under one of its two consumers would make the
    # other reach across for its asphalt. That asymmetry is not hypothetical: it
    # is the shape that let `235aa4f` re-expose `buildings:` and miss `roads:`.
    materials: dict[str, Material]
    buildings: BuildingStyle
    roads: RoadNetwork
    fares: Fares
    # The one number that converts a material's real albedo into the albedo this
    # city ships. Art direction — the sun, the latitude, the mood — where the
    # reflectances it multiplies are physical and portable to the next city.
    exposure_anchor: float
    # The surveyed building-block layer, when the city has one (`Q47`). Optional
    # with a default — a city without a topographic source builds as before.
    podiums: PodiumBlocks | None = None
    # Committed CA certificates that complete a publisher's TLS chain, resolved
    # to absolute paths at load. For hosts that serve their chain without the
    # issuing intermediate; verification is never relaxed, only completed.
    extra_cas: tuple[Path, ...] = ()

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

    # Parsed before anything that could reference it, so every `table.get` below
    # resolves against a complete table — a material declared after its first use
    # would otherwise fail on document order rather than on being absent.
    table = _MaterialTable(_materials(_require(document, "materials", path), f"{path}:materials"))

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
        # Copied rather than aliased: `table` is load-scoped and mutable, and a
        # frozen config holding a live reference into it is a shape that only
        # works while nothing keeps the table.
        materials=dict(table.declared),
        buildings=_building_style(
            _require(document, "buildings", path), f"{path}:buildings", table
        ),
        roads=_road_network(_require(document, "roads", path), f"{path}:roads", table),
        fares=_fares(_require(document, "fares", path), f"{path}:fares"),
        exposure_anchor=_exposure_anchor(
            _require(document, "exposure_anchor", path), f"{path}:exposure_anchor"
        ),
        podiums=(
            _podium_blocks(document["podiums"], f"{path}:podiums")
            if document.get("podiums") is not None
            else None
        ),
        extra_cas=_extra_cas(document.get("extra_cas"), path),
    )
    _check_regions_lie_within_the_city(city, path)
    # Usage before exposure, so a stray entry is reported as stray. The other
    # order exposure-checks a colour that ships nowhere and leads with whichever
    # complaint that raises, which is the less actionable of the two.
    _check_every_material_is_used(table, path)
    _check_exposure(city, path)
    _check_deck_sampling_has_a_structure_class(city, path)
    _check_widening_levels_are_mapped(city, path)
    _check_source_exists(city, city.roads.source, f"{path}:roads.source")
    for index, group in enumerate(city.fares.groups):
        _check_source_exists(city, group.source, f"{path}:fares.groups[{index}].source")
    if city.podiums is not None:
        _check_tiled_source_exists(city, city.podiums.source, f"{path}:podiums.source")
    return city


def _check_exposure(city: CityConfig, path: Path) -> None:
    """Every authored colour is `material reflectance x exposure_anchor` (`Q33`).

    The rule exists because the palette had no external referent. Colours were
    placed by eye against each other, so the only question a reviewer could ask
    was whether they looked consistent — and a set judged only on internal
    consistency always indicts its most extreme member, right or wrong. Stating
    the material each colour claims to be makes it checkable against published
    albedos instead. What that caught is in `hong_kong.yaml`'s header and
    `docs/ART_DESIGN.md`; it is not repeated here.

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
        expected = material.reflectance * city.exposure_anchor
        actual = reflectance(material.colour)
        if abs(actual - expected) > EXPOSURE_TOLERANCE_PCT:
            red, green, blue = material.colour
            raise ValueError(
                f"{path}:materials.{name} is #{red:02x}{green:02x}{blue:02x}, whose "
                f"luminance is {actual:.2f}% — but it declares reflectance "
                f"{material.reflectance}% at exposure_anchor {city.exposure_anchor}, "
                f"which is {expected:.2f}%. "
                "Change the colour, or change the material it claims to be."
            )


def _check_every_material_is_used(table: _MaterialTable, path: Path) -> None:
    """Nothing may be declared in `materials:` that nothing references.

    The reverse direction of the join, and it inherits its argument from the
    `class_reflectance` stray-key check this replaces: a table entry that colours
    nothing parses, loads, and is silently inert — the one way this table can be
    wrong without saying so. Worse here than there, because `_check_exposure`
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


def _check_deck_sampling_has_a_structure_class(city: CityConfig, path: Path) -> None:
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


def _check_widening_levels_are_mapped(city: CityConfig, path: Path) -> None:
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
    unknown = set(city.roads.surface.widen_by_elevation_level) - set(city.elevation_levels)
    if unknown:
        known = ", ".join(str(level) for level in sorted(city.elevation_levels))
        raise ValueError(
            f"{path}:roads.surface.widen_by_elevation_level names level "
            f"{', '.join(str(level) for level in sorted(unknown))}, "
            f"which elevation_levels does not map ({known})"
        )


def _check_source_exists(city: CityConfig, source_id: str, where: str) -> None:
    """A stage that names a source it cannot fetch is a config error, not a run.

    Caught at load rather than at first use, so a typo fails before the
    pipeline has read 17 MB of geodatabase to discover it.
    """
    if source_id not in city.sources:
        known = ", ".join(sorted(city.sources)) or "none"
        raise ValueError(f"{where} names '{source_id}', which is not in sources ({known})")


def _extra_cas(values: Any, path: Path) -> tuple[Path, ...]:
    """CA certificate paths, resolved against the yaml's own directory.

    Each must exist at load: a fetch that quietly fell back to the default
    store would re-surface the publisher's broken chain as a mid-run download
    failure, hundreds of megabytes in.
    """
    if not values:
        return ()
    resolved: list[Path] = []
    for value in values:
        candidate = (path.parent / str(value)).resolve()
        if not candidate.is_file():
            raise ValueError(f"{path}:extra_cas names {value!r}, which does not exist")
        resolved.append(candidate)
    return tuple(resolved)


def _check_tiled_source_exists(city: CityConfig, source_id: str, where: str) -> None:
    """`_check_source_exists`, for a stage that reads a per-sheet dataset."""
    if source_id not in city.tiled_sources:
        known = ", ".join(sorted(city.tiled_sources)) or "none"
        raise ValueError(f"{where} names '{source_id}', which is not in tiled_sources ({known})")


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
    suffix = body.get("tile_suffix")
    if suffix is not None:
        suffix = str(suffix)
        if not suffix.startswith("."):
            raise ValueError(f"{where}:tile_suffix is {suffix!r}, expected a '.suffix'")
    return TiledSource(
        id=source_id,
        index_url=str(_require(body, "index_url", where)),
        index_crs=str(_require(body, "index_crs", where)),
        id_property=str(_require(body, "id_property", where)),
        url_property=str(_require(body, "url_property", where)),
        revision_property=None if revision is None else str(revision),
        tile_suffix=suffix,
    )


def _cell_sizes(values: Any, field: str) -> tuple[float, ...]:
    """LOD clustering cells, ascending — the ordering every such table shares.

    Coarsest last because `collapse` only ever removes geometry: a tier finer
    than the one before it would draw *more* the further away it is.
    """
    sizes = tuple(float(size) for size in values)
    if list(sizes) != sorted(sizes):
        raise ValueError(f"{field} must be ordered coarsest last")
    return sizes


def _materials(body: dict[str, Any], where: str) -> dict[str, Material]:
    if not body:
        raise ValueError(f"{where} is empty — a city ships at least one colour")
    return {
        str(name): Material(
            name=str(name),
            colour=_parse_hex(str(_require(entry, "colour", f"{where}.{name}")), f"{where}.{name}"),
            reflectance=_reflectance(
                _require(entry, "reflectance", f"{where}.{name}"), f"{where}.{name}.reflectance"
            ),
            source=str(_require(entry, "source", f"{where}.{name}")),
        )
        for name, entry in body.items()
    }


def _hue_sectors(entries: Any, table: _MaterialTable, where: str) -> tuple[HueSector, ...]:
    sectors = tuple(
        HueSector(
            from_deg=float(_require(entry, "from_deg", f"{where}[{index}]")),
            draw=WeightedDraw.build(
                _require(entry, "weights", f"{where}[{index}]"), table, f"{where}[{index}].weights"
            ),
        )
        for index, entry in enumerate(entries)
    )
    if not sectors:
        raise ValueError(f"{where} is empty")
    angles = [sector.from_deg for sector in sectors]
    if angles != sorted(angles) or len(set(angles)) != len(angles):
        raise ValueError(f"{where} must be ordered by strictly ascending from_deg")
    if angles[0] < 0.0 or angles[-1] >= 360.0:
        # Outside [0, 360) the wrap stops being a partition: an angle below the
        # first boundary is meant to belong to the last sector, and that is only
        # a covering of the circle if every boundary is on it.
        raise ValueError(f"{where} from_deg must all lie in [0, 360), got {angles}")
    return sectors


def _ascending_to_inf(values: list[float], field: str, key: str) -> None:
    """A first-match table's keys ascend and the last one is open-ended.

    Shared because two tables are built on the same rule — the height ramp and
    the chroma rings — and this file's norm is that the copy which drifts is the
    one that quietly stops catching anything (`_jitter`, `_measures`,
    `_thresholds` all say so where they are defined).

    ⚠️ The open-ended last entry is what makes the table **total**, and totality
    is the property both callers rely on to have no fallback branch at all. Why
    each table has no ceiling differs, so that reasoning stays at the call sites.
    """
    if not values:
        raise ValueError(f"{field} is empty")
    if values != sorted(values):
        raise ValueError(f"{field} must be ordered by ascending {key}")
    if values[-1] != float("inf"):
        raise ValueError(f"{field} must end with `{key}: .inf`")


def _material_assignment(
    body: dict[str, Any], table: _MaterialTable, where: str
) -> MaterialAssignment:
    unsurveyed = _require(body, "unsurveyed", where)
    bands = tuple(
        HeightBand(
            up_to_m=float(_require(band, "up_to_m", where)),
            material=table.get(
                str(_require(band, "material", where)),
                f"{where}:unsurveyed.by_height[{index}]",
            ),
        )
        for index, band in enumerate(_require(unsurveyed, "by_height", f"{where}:unsurveyed"))
    )
    # Without an open-ended last band, `material_for` has nothing to return for a
    # building taller than the table — and the tallest buildings are the ones a
    # Hong Kong skyline is read by.
    _ascending_to_inf([band.up_to_m for band in bands], f"{where}:unsurveyed.by_height", "up_to_m")

    surveyed = body.get("surveyed")
    rings: tuple[ChromaRing, ...] = ()
    if surveyed is not None:
        field = f"{where}:surveyed.rings"
        rings = tuple(
            ChromaRing(
                up_to_chroma=float(_require(ring, "up_to_chroma", field)),
                draw=(
                    WeightedDraw.build(ring["weights"], table, f"{field}[{index}].weights")
                    if "weights" in ring
                    else None
                ),
                sectors=(
                    _hue_sectors(ring["sectors"], table, f"{field}[{index}].sectors")
                    if "sectors" in ring
                    else ()
                ),
            )
            for index, ring in enumerate(_require(surveyed, "rings", f"{where}:surveyed"))
        )
        for index, ring in enumerate(rings):
            if (ring.draw is None) == (not ring.sectors):
                # Both would make one of them silently dead; neither leaves the
                # ring with no answer at all.
                raise ValueError(
                    f"{field}[{index}] must have exactly one of `weights` or `sectors`"
                )
        # The same rule as the height ramp, for a different reason: chroma has no
        # ceiling either, so an unbounded last ring is what makes this total.
        _ascending_to_inf([ring.up_to_chroma for ring in rings], field, "up_to_chroma")

    return MaterialAssignment(by_height=bands, rings=rings)


def _building_style(body: dict[str, Any], where: str, table: _MaterialTable) -> BuildingStyle:
    assignment = _material_assignment(
        _require(body, "material_assignment", where), table, f"{where}:material_assignment"
    )

    hue = body.get("facade_hue")
    hue_source = None if hue is None else str(_require(hue, "source", f"{where}:facade_hue"))
    hue_strength = (
        1.0
        if hue is None
        else _scale(hue.get("strength", 1.0), f"{where}:facade_hue.strength", HUE_STRENGTH_MAX)
    )
    vegetation_max = None if hue is None else hue.get("vegetation_max")
    hue_vegetation_max = (
        None
        if vegetation_max is None
        else _scale(vegetation_max, f"{where}:facade_hue.vegetation_max", 1.0)
    )

    survey = body.get("facade_survey") or {}
    if not isinstance(survey, dict):
        raise ValueError(f"{where}:facade_survey must be a mapping")
    glazing_source = survey.get("glazing")
    grammar_source = survey.get("grammar")

    cells = _cell_sizes(_require(body, "lod_cell_sizes_m", where), f"{where}:lod_cell_sizes_m")
    if not cells:
        raise ValueError(f"{where}:lod_cell_sizes_m is empty")

    classes = tuple(str(name) for name in _require(body, "classes", where))
    if not classes:
        raise ValueError(f"{where}:classes is empty")

    class_materials = {
        str(name): table.get(str(value), f"{where}:class_materials.{name}")
        for name, value in (body.get("class_materials") or {}).items()
    }
    unknown = set(class_materials) - set(classes)
    if unknown:
        # A misspelled key parses, loads, and silently colours nothing — the one
        # way this table can be wrong without saying so.
        raise ValueError(
            f"{where}:class_materials names {', '.join(sorted(unknown))}, "
            f"which is not in classes ({', '.join(classes)})"
        )

    class_cells: dict[str, tuple[float, ...]] = {}
    for name, sizes in (body.get("class_lod_cell_sizes_m") or {}).items():
        field = f"{where}:class_lod_cell_sizes_m.{name}"
        if str(name) not in classes:
            # Same trap as `class_materials`: a misspelled key parses, loads, and
            # silently overrides nothing.
            raise ValueError(f"{field} is not in classes ({', '.join(classes)})")
        override = _cell_sizes(sizes, field)
        if len(override) != len(cells):
            # A short table would index-error partway through a build, after the
            # expensive read; a long one would describe tiers that never exist.
            raise ValueError(
                f"{field} has {len(override)} tiers, but lod_cell_sizes_m has {len(cells)}"
            )
        class_cells[str(name)] = override

    structure = body.get("structure_class")
    if structure is not None and str(structure) not in classes:
        # This one must be inside `classes`: `P2-7` lays the carriageway on this
        # geometry and is accepted against the *shipped* tiles, so structure
        # that never ships would be accurate against nothing the player can
        # meet. `terrain_class` is under no such rule — a city may sample the
        # ground for road heights without drawing it — which is why the two are
        # checked differently.
        raise ValueError(
            f"{where}:structure_class is {structure!r}, "
            f"which is not in classes ({', '.join(classes)})"
        )

    jitter = _jitter(_require(body, "colour_jitter", where), f"{where}:colour_jitter")

    class_jitter: dict[str, float] = {}
    for name, value in (body.get("class_colour_jitter") or {}).items():
        field = f"{where}:class_colour_jitter.{name}"
        if str(name) not in classes:
            # Same trap as `class_materials`: a misspelled key parses, loads, and
            # silently overrides nothing.
            raise ValueError(f"{field} is not in classes ({', '.join(classes)})")
        class_jitter[str(name)] = _jitter(value, field)

    terrain = str(_require(body, "terrain_class", where))
    # Zero where the city never tiles its ground: the value is unused there, and
    # refusing a city for omitting a key it cannot act on would reject correct
    # output.
    sink = (
        _measures(body, where, ("ground_sink_m",))["ground_sink_m"]
        if "ground_sink_m" in body
        else 0.0
    )
    if terrain in classes and sink <= 0.0:
        # Tested on the **value**, not on the key. A missing `ground_sink_m` and
        # an explicit `0.0` reach the same place, and `_measures` admits zero —
        # so a presence check would let the exact state below through.
        #
        # One direction only, on `_check_deck_sampling_has_a_structure_class`'s
        # pattern. A tiled ground with no sink is the silent failure: `roads.py`
        # lays the level-0 carriageway at `terrain + 0.0`, so the two surfaces
        # would be coplanar by construction and z-fight the length of the
        # network — which looks like a rendering bug rather than a config one.
        raise ValueError(
            f"{where}:classes tiles the ground ({terrain!r}), so ground_sink_m must be "
            f"positive, got {sink}. Set it, or drop {terrain!r} from classes."
        )

    return BuildingStyle(
        classes=classes,
        terrain_class=terrain,
        structure_class=str(structure) if structure is not None else None,
        class_materials=class_materials,
        material_assignment=assignment,
        colour_jitter=jitter,
        class_colour_jitter=class_jitter,
        facade_hue_source=hue_source,
        facade_hue_strength=hue_strength,
        facade_hue_vegetation_max=hue_vegetation_max,
        facade_glazing_source=None if glazing_source is None else str(glazing_source),
        facade_grammar_source=None if grammar_source is None else str(grammar_source),
        lod_cell_sizes_m=cells,
        class_lod_cell_sizes_m=class_cells,
        ground_sink_m=sink,
    )


def _number(value: Any, field: str) -> float:
    """One config value as a float, named in the error when it is not one."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} is {value!r}, which is not a number") from None


def _jitter(value: Any, field: str) -> float:
    """A brightness-variation fraction, refused when it cannot be used.

    Written once because the global value and the per-class overrides are the
    same quantity, and the copy that drifts is the one that quietly stops
    catching anything.

    The range test does the finiteness work for free, and that is worth saying
    out loud because it is not obvious: YAML 1.1 resolves `.nan` and `.inf`, and
    every comparison against a NaN is false — so `0.0 <= value` fails and the
    value is refused rather than surviving to make every downstream comparison
    false in silence. That is the `P2-7` config trap, and the shape of this test
    happens to close it.
    """
    number = _number(value, field)
    if not 0.0 <= number < 1.0:
        raise ValueError(f"{field} must be in [0, 1), got {number}")
    return number


def _exposure_anchor(value: Any, field: str) -> float:
    """The city's exposure scale, in `(0, EXPOSURE_ANCHOR_MAX]`.

    Its own validator rather than `_scale`, which admits `0.0`. Zero is the trap
    worth refusing by name: it makes every shipped colour black and then
    satisfies `_check_exposure` for *any* declared reflectance, turning the rule
    into a no-op that still reads as enforced.

    The ceiling is above 1.0 on purpose. A city brighter than its own materials
    is a coherent direction — an over-exposed, blown-out look is a choice, not an
    error — and the bound is here only to keep the test two-sided against `.nan`
    and `.inf`, per `_scale`'s reasoning.
    """
    number = _number(value, field)
    if not 0.0 < number <= EXPOSURE_ANCHOR_MAX:
        raise ValueError(f"{field} must be in (0, {EXPOSURE_ANCHOR_MAX}], got {number}")
    return number


def _reflectance(value: Any, field: str) -> float:
    """A real-world diffuse albedo as a percentage, in (0, 100].

    Zero is refused rather than clamped: a surface reflecting nothing is a
    surface no material has, and it would pair with a black colour that passes
    `_check_exposure` while saying nothing about what it depicts. 100 is the
    perfect diffuser, so above it is a measurement error, not a bright material.
    """
    number = _number(value, field)
    if not 0.0 < number <= 100.0:
        raise ValueError(f"{field} must be a percentage in (0, 100], got {number}")
    return number


def _scale(value: Any, field: str, high: float) -> float:
    """A non-negative multiplier, bounded above so the test stays two-sided.

    The ceiling is not a taste limit — it is what makes this close the `_jitter`
    trap above. A one-sided `< 0.0` test passes `.nan` and `.inf`, and a NaN
    strength propagates through `with_hue` into `np.clip(np.round(nan))`, which
    silently miscolours every surveyed building rather than failing.
    """
    number = _number(value, field)
    if not 0.0 <= number <= high:
        raise ValueError(f"{field} must be in [0, {high}], got {number}")
    return number


def _road_network(body: dict[str, Any], where: str, table: _MaterialTable) -> RoadNetwork:
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

    deck = _sampling_block(body, "deck", where, ground)
    profile = _sampling_block(body, "ground_profile", where, ground)

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
        surface=_road_surface(_require(body, "surface", where), f"{where}:surface", table),
        deck=_deck_sampling(deck, f"{where}:deck") if deck is not None else None,
        ground_profile=(
            _ground_profile(profile, f"{where}:ground_profile") if profile is not None else None
        ),
    )


def _sampling_block(
    body: dict[str, Any], key: str, where: str, ground: str
) -> dict[str, Any] | None:
    """An optional block of height-field thresholds, or `None` if the city has none.

    Shared by `deck:` and `ground_profile:` because both are optional, both ask
    a height field about a road, and both are therefore unreachable without one.
    Written once because the copy that drifts is the one that quietly stops
    catching anything — and every guard below refuses a config that *loads*.
    """
    block = body.get(key)
    if key in body and block is None:
        # A block with nothing under it — the natural state while commenting the
        # values out to tune — resolves to None, which would otherwise read as
        # "this city wants none of this" and skip the checks below. Omitting the
        # key is already how a city says that, so this spelling can be refused
        # outright rather than guessed at.
        raise ValueError(f"{where}:{key} is empty; give it thresholds or remove the key")
    if block is not None and not isinstance(block, dict):
        # Otherwise `_require` asks a non-mapping for a key and the author gets a
        # bare TypeError naming neither the file nor the block they just edited.
        raise ValueError(f"{where}:{key} must be a mapping of thresholds, got {block!r}")
    if block is not None and ground != TERRAIN:
        # Both blocks measure against the terrain — one gates and falls back to
        # it, the other follows it — so under any other ground source they are
        # unreachable. Refused rather than ignored: a config that cannot do what
        # it says is a mistake, and a silently inert block is the kind that
        # survives review.
        raise ValueError(f"{where}:{key} needs ground '{TERRAIN}', but ground is {ground!r}")
    return block


def _thresholds(
    body: dict[str, Any], where: str, *, positive: tuple[str, ...], signed: tuple[str, ...]
) -> dict[str, float]:
    """Every measurement of one threshold block, and nothing else.

    `positive` names the values zero is degenerate for and `signed` the ones it
    is merely strict for — a split by what zero *means*, not by tidiness.

    The closed-key-set check is the reason this is shared rather than written
    per block. Misspelling one of the names is already caught by its absence;
    adding a spare on top of them is not, and would parse, load and tune
    nothing. Refused for the reason `class_materials` refuses the same thing, with
    more grounds: these key sets are closed and known, and they are the blocks
    whose whole point is not to be silently inert.
    """
    values = _measures(body, where, positive, positive=True)
    values |= _measures(body, where, signed)

    unknown = set(body) - set(values)
    if unknown:
        raise ValueError(f"{where} does not use {', '.join(sorted(unknown))}")
    return values


def _ground_profile(body: dict[str, Any], where: str) -> GroundProfile:
    # A spacing of zero asks for infinitely many stations. A tolerance of zero
    # is coherent if expensive: it keeps every station the resample inserted,
    # which is the un-thinned behaviour the measurements compare against.
    values = _thresholds(body, where, positive=("resample_m",), signed=("tolerance_m",))
    return GroundProfile(resample_m=values["resample_m"], tolerance_m=values["tolerance_m"])


def _deck_sampling(body: dict[str, Any], where: str) -> DeckSampling:
    # A spacing or a slab gap of zero is degenerate — the first asks for
    # infinitely many stations, the second makes every distinct height its own
    # slab and so defeats the clustering the query is built on.
    values = _thresholds(
        body,
        where,
        positive=("resample_m", "slab_gap_m"),
        signed=("max_below_terrain_m", "at_grade_m", "clearance_m"),
    )
    return DeckSampling(
        resample_m=values["resample_m"],
        slab_gap_m=values["slab_gap_m"],
        max_below_terrain_m=values["max_below_terrain_m"],
        at_grade_m=values["at_grade_m"],
        clearance_m=values["clearance_m"],
    )


def _road_surface(body: dict[str, Any], where: str, table: _MaterialTable) -> RoadSurface:
    widen_default = float(_require(body, "widen_default", where))
    widen = {
        int(threshold): float(factor)
        for threshold, factor in (body.get("widen_by_min_speed_limit_kph") or {}).items()
    }
    by_level: dict[int, float] = {}
    for level, factor in (body.get("widen_by_elevation_level") or {}).items():
        # The YAML 1.1 boolean trap `elevation_levels` documents at length, and
        # this table is keyed on the same domain: a bare `on:` key resolves to
        # True, and True == 1 as a dict key, so it lands silently on the level-1
        # rule — the one rule this table currently carries.
        if isinstance(level, bool) or not isinstance(level, int):
            raise ValueError(f"{where}:widen_by_elevation_level key {level!r} is not an integer")
        by_level[level] = float(factor)
    on_structure = float(_require(body, "widen_on_structure", where))
    for factor in (widen_default, on_structure, *widen.values(), *by_level.values()):
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
    #
    # `structure_taper_m` joins them: a negative taper would run the blend the
    # wrong way and widen the road *onto* the deck, which is the defect `Q23`
    # exists to remove arriving through its own fix.
    measures = _measures(
        body,
        where,
        ("kerb_height_m", "kerb_width_m", "junction_trim_factor", "structure_taper_m"),
    )

    return RoadSurface(
        widen_default=widen_default,
        widen_by_min_speed_limit_kph=widen,
        widen_by_elevation_level=by_level,
        widen_on_structure=on_structure,
        structure_taper_m=measures["structure_taper_m"],
        kerb_height_m=measures["kerb_height_m"],
        kerb_width_m=measures["kerb_width_m"],
        junction_trim_factor=measures["junction_trim_factor"],
        junction_trim_max_fraction=fraction,
        surface_material=table.get(
            str(_require(body, "surface_material", where)), f"{where}:surface_material"
        ),
        kerb_material=table.get(
            str(_require(body, "kerb_material", where)), f"{where}:kerb_material"
        ),
    )


def _source_layer(body: dict[str, Any], where: str, roles: tuple[str, ...]) -> SourceLayer:
    return SourceLayer(
        layer=str(_require(body, "layer", where)),
        fields=_fields(body, where, roles),
    )


_PODIUM_BLOCK_ROLES = ("block_type", "base_level", "roof_level", "certainty")


def _podium_blocks(body: dict[str, Any], where: str) -> PodiumBlocks:
    member = str(_require(body, "member", where))
    try:
        member.format(tile="probe")
    except (KeyError, IndexError, ValueError) as error:
        # A stray or malformed placeholder would otherwise surface at first
        # read, per sheet, rather than at load — the reason
        # `_check_source_exists` gives.
        raise ValueError(
            f"{where}:member {member!r} allows only the {{tile}} placeholder ({error})"
        ) from error
    return PodiumBlocks(
        source=str(_require(body, "source", where)),
        member=member,
        blocks=_source_layer(
            _require(body, "blocks", where), f"{where}:blocks", _PODIUM_BLOCK_ROLES
        ),
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
