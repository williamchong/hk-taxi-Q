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

    `codes` maps the two roles the tower↔block join asks for — `tower` and
    `podium` — onto the publisher's own domain values, the same indirection
    `fields` gives column names: which letter means "podium block" is the
    Lands Department's spelling, not a fact about podiums.
    """

    source: str
    member: str
    blocks: SourceLayer
    codes: dict[str, str]

    def code(self, role: str) -> str:
        return _field(self.codes, role, "podiums:codes")


@dataclass(frozen=True)
class CarriagewayEdge:
    """One published opinion on where the edge of the carriageway runs (`Q57`).

    **Nothing in `pipeline/` reads this**, on the same terms as `KerbsideAudit`:
    it is config rather than constants in `tools/carriageway_margin.py` because
    the layer name, the field and the domain codes are the publisher's schema
    (hard rule 3). A city with no such layer leaves the block out and cannot be
    measured, which is the honest answer rather than a fabricated width.

    Two of these are declared for Hong Kong on purpose. `Q57` traced four wrong
    "no source publishes that" claims to one mechanism — a fact established
    against a single dataset, then generalised to the estate — so an instrument
    that read *one* margin layer and reported "the width" would be that error in
    a new place. Where two publishers agree the number is strong; where they
    diverge, the divergence is the finding.

    `member` is set only for a per-sheet source, exactly as `PodiumBlocks` uses
    it, and is what distinguishes a `tiled_sources` entry from a `sources` one.

    `codes` are the domain values that mean "carriageway edge"; a value is a
    *list* because TD spells the same marking `RM1108` and `RM1109`.

    Grade is reached differently by each publisher, and **neither way is the
    Road Network v2 integer convention**. TD carries a *relative level* text
    code whose domain its data specification does not enumerate, so
    `off_grade_codes` lists the values measured to be off-grade and everything
    else is taken as at grade — an exclusion rather than an inclusion because
    the at-grade value is null, which a list of included codes cannot spell.
    iB1000 has no level column at all: it gives the under-deck margin its own
    domain value, `RMU`, so leaving that out of `codes` is the whole filter and
    there is nothing for `off_grade_codes` to do. `off_grade_codes` is
    therefore `()` for a publisher that separates grade by code, and requires
    an `elevation` field role when it is not — checked, because a config that
    listed codes against no column would filter nothing and say nothing.
    """

    name: str
    source: str
    member: str | None
    layer: SourceLayer
    codes: tuple[str, ...]
    off_grade_codes: tuple[str, ...]

    @property
    def tiled(self) -> bool:
        """Whether `source` names `tiled_sources` rather than `sources`."""
        return self.member is not None

    @property
    def elevation_field(self) -> str | None:
        """The publisher's grade column, where it publishes one."""
        return self.layer.fields.get("elevation")


@dataclass(frozen=True)
class CarriagewaySurvey:
    """Every published carriageway edge the city can be measured against (`Q57`).

    Ordered, and the order is read as preference: `tools/carriageway_margin.py`
    takes the first source that answers a station and falls back down the list,
    reporting which one answered. Hong Kong leads with the Transport
    Department's own painted edge — semantically the carriageway rather than a
    topographic margin that may follow a kerb, a wall or a lot boundary — and
    falls back to iB1000, which is two orders of magnitude denser.
    """

    edges: tuple[CarriagewayEdge, ...]


@dataclass(frozen=True)
class Tramway:
    """The published tramway, and how `P3-14` draws it (`Q58`).

    ⚠️ **Unlike `CarriagewaySurvey` above, the pipeline reads this**: it is a
    build input, not an instrument's truth side. The shape is deliberately the
    same, because both read a domain code out of the same iB1000 layer and hard
    rule 3 keeps the code in the city file either way.

    ⚠️ **`codes` selects rails, not track centrelines.** `Q58` measured what the
    layer actually contains rather than taking the record's word: 56.5% of
    stations across a tram-flagged edge cross exactly **four** parts, and the
    modal gap between neighbouring parts is **1.05-1.20 m** — Hong Kong
    Tramways' 1.067 m gauge. `Q57` and `DATA_SOURCES.md` both called these
    "tramway centrelines"; they are the rails themselves, and a bed drawn
    between a mis-paired couple would be a lane wide.

    `gauge_m` and `pair_tolerance_m` are what turn those rails back into tracks,
    and they are a *measurement* rather than a preference — which is why they
    are here and not under an art heading. Everything below them is drawing.
    """

    source: str
    member: str | None
    layer: SourceLayer
    codes: tuple[str, ...]
    # Published track gauge, and how far a neighbour may sit from it and still
    # be read as the other rail of the same track.
    gauge_m: float
    pair_tolerance_m: float
    # Drawn width of one rail, and of the bed carrying a pair of them.
    rail_width_m: float
    bed_width_m: float
    # How far above the deck the bed sits, and the rail above the bed. The road
    # and the ground are coplanar at grade by construction (`P3-10`), so a
    # tramway laid at deck height would z-fight the terrain it rests on.
    bed_lift_m: float
    rail_lift_m: float
    # Furthest a rail station may sit from a level-0 centreline and still take
    # its height from it. Beyond this the part is dropped rather than guessed:
    # the reserve runs between two carriageways, so a rail with no road near it
    # is one this region does not drive past.
    max_snap_m: float
    # Resolved through `_MaterialTable.get`, as every other material reference
    # is: that call *is* how usage gets recorded, so holding the name as a
    # string here would leave both materials looking unreferenced.
    rail_material: Material
    bed_material: Material

    @property
    def tiled(self) -> bool:
        """Whether `source` names `tiled_sources` rather than `sources`."""
        return self.member is not None


# What an arrow may show. The vocabulary is the pipeline's, not a city's:
# a glyph is drawn from these, so a fourth word would need geometry to draw it.
# ⚠️ These are *movements*, not lane positions. `RM1027` is one arrow with two
# heads, drawn in one lane; it is not two arrows.
ARROW_AHEAD = "ahead"
ARROW_LEFT = "left"
ARROW_RIGHT = "right"
ARROW_MOVEMENTS = (ARROW_AHEAD, ARROW_LEFT, ARROW_RIGHT)


@dataclass(frozen=True)
class ArrowGlyph:
    """One publisher code: what its arrow shows, and how long it is drawn.

    ⚠️ **The length belongs to the code, not to the block.** TD's index plan
    publishes every turn arrow twice — `RM1017` straight-ahead at **4000 mm**
    and `RM1018` the same arrow at **6000 mm**, and so on in pairs up to
    `RM1030`. A single authored length would draw one of each pair wrong by
    half its own size, on a marking whose whole defence is that it is read
    rather than invented. Wan Chai happens to publish only the 4 m variants;
    that is a fact about this region, not about the estate.
    """

    movements: tuple[str, ...]
    length_m: float


@dataclass(frozen=True)
class Arrows:
    """Published turn arrows, and how `P3-15` draws them (`Q53`, `Q57`).

    ⚠️ **`glyphs` maps a publisher's code to a movement, and that mapping is the
    one thing here that cannot be checked by any grader this repo has.** Every
    consumer downstream takes "1019 means turn left" on trust, exactly as `Q56`
    found every consumer taking double-versus-single on trust from
    `NSR.TIME_ZONE`. The codes are defined in the publisher's own index plan,
    inside `traffic_aids_data_dictionary` — read it, do not infer the meaning
    from the count. `Q57`'s `TACW` trap is a three-letter code that looked like
    the answer.

    ⚠️ **`RM1135`/`RM1136` are not arrows** — they are the 望右/望左 look-right
    and look-left crossing markings, and they are the two most common codes in
    the region after `RM1017`. A glyph table that picks up "the top six codes"
    paints pedestrian warnings down the middle of the carriageway.

    The dimensions below are marking *convention*, drawn to the index plan's
    figures. They are not a position: where an arrow goes is read from the
    source, through `max_offset_m` and the lane the offset lands in.

    ⚠️ **There is no material here, and its absence is the decision.** An arrow
    is the same paint as a lane divider, and `Q53` put the marking colours in
    `game/tuning/road_markings.tres` rather than in this file's `materials:`
    table — deliberately outside `Q33`'s exposure rule, because paint is not
    cladding. That entry predicted that "the day a third road colour is authored
    somewhere else" would be the problem, and adding `road_paint_white` here
    would be that day. So `arrows.glb` ships **no `COLOR_0`** and takes its
    colour from `game/tuning/arrows.tres`, beside the markings it matches. The
    glTF material *name* the engine dispatches on is `ARROWS_MATERIAL` in
    `pipeline/arrows.py`, a constant, as `SURFACE_MATERIAL` and
    `TRAMWAY_MATERIAL` are.
    """

    source: str
    member: str | None
    layer: SourceLayer
    # Publisher code -> what that code's arrow shows and how long it is.
    glyphs: dict[str, ArrowGlyph]
    # The proportions of an arrow, as fractions of its **own** published length,
    # so the 4 m and 6 m variants of the same marking scale together instead of
    # sharing an absolute head that is right for one of them.
    stem_width_frac: float
    head_length_frac: float
    head_width_frac: float
    # How far a turn head reaches across from the stem before it turns.
    branch_reach_frac: float
    # How far above the carriageway the glyph sits. The road surface and the
    # ground are coplanar at grade by construction (`P3-10`), so paint laid at
    # deck height would z-fight the road it is painted on.
    lift_m: float
    # Furthest a symbol may sit from a level-0 centreline and still be placed.
    # Beyond this it is dropped rather than guessed at: 14.2% of this region's
    # symbols fall outside even the *real* carriageway of their nearest edge,
    # and an arrow on the wrong street is the `P3-9a` debit this whole stage is
    # subordinate to.
    max_offset_m: float
    # How far a symbol's own bearing may sit from its host edge's heading before
    # the match is refused. A symbol squarely across its edge matched the wrong
    # edge; refusing is how that stops being drawn.
    #
    # ⚠️ Refuses the *match*, never rotates the arrow to fit. An arrow turned to
    # agree with the road would be an invented marking in `Q54`'s sense, and it
    # would render perfectly.
    bearing_tolerance_deg: float

    @property
    def tiled(self) -> bool:
        """Whether `source` names `tiled_sources` rather than `sources`."""
        return self.member is not None


@dataclass(frozen=True)
class BoxJunctions:
    """Published yellow box junctions, drawn by `pipeline/boxjunctions.py` (`P3-18`).

    The content is **read, not invented**, on `Q53`'s terms: `DTAD_YL_BOX_POLY`
    publishes each box as a surveyed polygon, so the extent that `Q53` said
    "nothing publishes" is exactly what this block reads (`Q56` found it). The
    dimensions below are marking *convention*, transcribed from TD's index plan
    CT174/51-5(1)F — where the box goes is read from the source.

    ⚠️ **The hatch direction is the one derived thing here.** The publisher's
    `ANGLE1`/`ANGLE2` pair carries it on a fraction of the layer (4 of the
    region's 20), and is used wherever present; elsewhere the direction is the
    box's own min-area-rectangle long axis + 45 deg. That derivation was graded
    against the published pairs before it shipped — `boxjunctions.json`
    publishes `hatch_angle_residual_deg` so it stays graded — and it was chosen
    over the nearest-edge heading + 45 on those numbers: per published pair it
    wins 3 of 4, and the edge alternative picks an arbitrary arm at exactly the
    geometry a box occupies. A wrong direction rotates a cross-hatch inside its
    own border and misleads no one; a box on the wrong junction would, which is
    why position is never derived.

    ⚠️ **There is no material here, and its absence is the decision** — the same
    paragraph `Arrows` carries. The yellow is authored in
    `game/tuning/boxjunctions.tres`, deliberately outside `Q33`'s exposure rule,
    and the glTF material *name* the engine dispatches on is
    `BOXJUNCTIONS_MATERIAL` in `pipeline/boxjunctions.py`.
    """

    source: str
    member: str | None
    layer: SourceLayer
    # Which published `YELLOWBOX_TYPE` values are box junctions. The region's
    # layer is single-valued ("Yellow Box"), so today this filters nothing —
    # it exists so a second city whose publisher adds a type this stage has no
    # business drawing refuses it loudly rather than painting it yellow.
    box_types: tuple[str, ...]
    # Marking convention, from the index plan: RM1038 draws a 300 mm boundary
    # line and 100 mm hatched lines.
    border_width_m: float
    hatch_width_m: float
    # Centre-to-centre spacing of the hatched lines. The index plan gives
    # "SPACING = 2000 (2500)"; the parenthetical is the wider variant.
    hatch_spacing_m: float
    # Sampling pitch along stripes and border runs. Each vertex takes its height
    # from the road under it, so this is what lets a long stripe follow the
    # crown of the junction instead of chording across it.
    station_m: float
    # How far above the carriageway the hatch sits. ⚠️ Deliberately below
    # `arrows.lift_m`: 51 of the region's turn arrows sit over junction caps,
    # and an arrow inside a box junction at equal lift would z-fight the
    # hatching. Arrows paint over boxes, which is also what the street does.
    lift_m: float
    # How far the boundary line sits above the *hatch*. The two are the same
    # paint at the same nominal height, and the hatch is deliberately not
    # clipped back to the boundary's inner edge — an inward offset of a concave
    # 106-vertex ring can self-intersect, and a guessed repair of that is
    # invented geometry. Lifting the border clear instead makes the overlap
    # invisible by construction.
    border_lift_m: float
    # Furthest a box's centroid may sit from a level-0 centreline and still be
    # drawn. Beyond it the box is dropped rather than guessed at — its vertices
    # would take their heights from a road it is not on.
    max_offset_m: float
    # How far past the nearest centreline the height join keeps listening. A
    # vertex's height is a distance-weighted blend of every level-0 segment
    # within `nearest + height_blend_m`, not the nearest edge's alone —
    # ⚠️ **because a hard nearest-edge switch is a cliff.** Two arms of one
    # junction disagree about the deck by up to a measured 0.43 m where they
    # meet, and the first build took each vertex from whichever arm won: 172
    # triangles came out near-vertical, caught by `verify_boxjunctions.gd`'s
    # faces-up check while the ETL's own `inverted` read 0. The blend is also
    # the closer model of the drawn cap, whose fan interpolates between those
    # same arm ends. Far from a seam only one edge is in range, and the blend
    # *is* the plain snap.
    height_blend_m: float

    @property
    def tiled(self) -> bool:
        """Whether `source` names `tiled_sources` rather than `sources`."""
        return self.member is not None


@dataclass(frozen=True)
class Railings:
    """Published pedestrian railings, drawn by `pipeline/railings.py` (`P3-19`).

    ⚠️ **This block asserts more than any other in this file, and the reason is
    that the publisher asserts less.** `DTAD_RAILING_LINE`'s `LINETYPE` domain
    is **not published**: the fgdb data specification gives the column only the
    description "Line Type", and the index-plan set that defines every `RM`
    marking code and every `TS` sign — including both "Miscellaneous Details"
    sheets — carries no railing sheet at all. So there is no `Q59` transcription
    available here, and every dimension below is **authored**, declared as
    authored, rather than read.

    What follows from that is the shape of `drawn_line_types`: a whitelist of
    codes, and *no type map*. The region publishes 19 values and this stage
    draws one fence for all of the ones it admits — it does not claim that
    `CRAIL1` is a different railing from `HCAIL2`, because nothing published
    says so and `Q54` debits exactly that kind of invention.

    ⚠️ **The position is registered, not read, and that is this block's real
    debt.** `Q59`'s widening puts the drawn kerb a median 0.9 m *outside* the
    surveyed railing line, so **67.9% of the region's railing metres fall inside
    the drawn ribbon** — drawn where surveyed, the signature Hong Kong railing
    is a picket fence down the middle of the drivable surface. So the
    longitudinal extent is read and never stretched, and the lateral offset is
    a rigid move onto the kerb the ETL itself drew. `max_shift_m` is the bar on
    that move and `railings.json` publishes the whole distribution, because a
    move nobody measures is an invention nobody can see.

    ⚠️ **There is no material here, and its absence is the decision** — the
    paragraph `Arrows` and `BoxJunctions` both carry. The colour is authored in
    `game/tuning/railings.tres`, and the glTF material *name* the engine
    dispatches on is `RAILINGS_MATERIAL` in `pipeline/railings.py`.
    """

    source: str
    member: str | None
    layer: SourceLayer
    # Which published `LINETYPE` values this city draws as a railing. ⚠️ A
    # whitelist and **not** a type map: see the class docstring. Everything
    # outside it is refused and its metres counted, which is what keeps the
    # bollards, the crash gates and the four `AMT` variants from being asserted
    # to be pedestrian railings on the strength of sharing a layer with them.
    drawn_line_types: tuple[str, ...]
    # Pitch the source lines are sampled at before being assigned to an edge and
    # a side. `kerbside.resample`'s parameter, and the cell size the same
    # stage's dedupe works in: two features drawn along one kerb collapse into
    # one run rather than counting twice, which this layer needs more than
    # `NSR` did — the region publishes 1,763 parts with a median length of
    # 4.6 m for what a driver sees as a few dozen fences.
    sample_m: float
    # Furthest a sample may sit from a level-0 centreline and still be assigned
    # to it. Beyond it the sample is unassigned and counted: a railing round a
    # plaza or along a footbridge belongs to no kerb, and putting it on the
    # nearest one is how a fence ends up across a street it was never on.
    max_offset_m: float
    # ⚠️ **The bar on the registration, and the number this stage exists to be
    # honest about.** How far a run may be moved sideways to reach the drawn
    # kerb before it is refused instead. Measured over the region before it was
    # chosen: half the railing metres move under 2 m, two-thirds under 3 m, and
    # 18% would move more than 5 m — those are railings that are not kerb
    # railings at all, and drawing them would be inventing a fence rather than
    # relocating one.
    max_shift_m: float
    # Gaps in the sampled cells shorter than this are bridged, and runs shorter
    # than `min_run_m` are dropped. `kerbside`'s parameters, for its reasons: a
    # break shorter than a car is not a break, and a two-metre orphan is a
    # fence post rather than a fence.
    bridge_gap_m: float
    min_run_m: float
    # Pitch the drawn fence is stationed at along the kerb. Every station takes
    # its height from the ribbon, so this is what lets a fence follow the
    # camber of a street instead of chording across it.
    station_m: float
    # ⚠️ **Authored.** Hong Kong's pedestrian railings stand about waist-to-
    # chest height; no source in this bundle publishes the figure, and the
    # nearest thing to a publisher — the index-plan set — has no railing sheet.
    # Declared here rather than fixed in code so the honesty is visible and so
    # a second city may differ (hard rules 3 and 4).
    height_m: float
    # How far the fence's foot is sunk below the ribbon it stands on. The kerb
    # is flattened for mountability (`GAME_DESIGN.md`) and the ground beside it
    # is a separate decimated surface, so a fence planted exactly at the road's
    # own height shows daylight under it wherever the two disagree.
    base_sink_m: float
    # How far outside the drawn carriageway edge the fence stands. The kerb
    # strip `roads.surface.kerb_width_m` draws is what it stands behind, so this
    # is that width plus a little — a fence *on* the carriageway edge is a fence
    # the player's wheel clips while driving in lane.
    outset_m: float

    @property
    def tiled(self) -> bool:
        """Whether `source` names `tiled_sources` rather than `sources`."""
        return self.member is not None


@dataclass(frozen=True)
class SourcePaint:
    """How a mesh-sourced hero is repainted from its source COLOR_0 (`P3-6`).

    Present on a `Landmark` it declares the model is not an authored `.glb`
    but the building's own source mesh, extracted and vertex-repainted by
    `pipeline/landmarks.py` and shipped as generated output — government-
    derived data that must never be committed (`LICENSING.md`).

    The four surfaces are **names into the city's `materials:` table**, not
    colours: every colour the city ships is declared in that table and nowhere
    else, which is what keeps `_check_exposure` total.

    Ribbon strips are dark horizontal glazing bands at constant absolute
    elevations above the model base: `first_m + k * pitch_m` for `count`
    strips, each `thickness_m` tall. A strip the roofline has descended past
    simply has no wall surface left at its elevation — no clamping needed.

    The normal thresholds only *seed* the roof and soffit: a face is a roof
    seed where its unit normal's y exceeds `roof_normal_y`, a soffit seed
    below `-soffit_normal_y`. Each region then grows across every edge whose
    faces meet at less than `crease_deg` — a curved sweep is one surface, and
    it stays roof all the way down its roll rather than turning into banded
    wall the moment it passes the threshold (the defect the first repaint
    shipped). Growth stops at creases, which is where a roof actually ends
    and a wall begins. Everything with a centroid under `base_below_m` is
    base regardless of facing (piers, service base).

    `reference_texture` makes the paint consult the building's own aerial
    photo: the individualised (`…A0`) variant of the same mesh carries the
    photogrammetry texture, and a procedural ribbon is kept only where that
    photo is darker than the *same wall half a pitch above and below* — the
    one comparison that cancels the baked sun and shade, which vary across a
    facade at many times the glazing's own contrast. A band sample under
    `veto_ratio` x its vertical neighbours counts as glazing; a uniform
    surface (a roof sweep, a fascia) contrasts at ~1.0 and loses its bands.
    The texture never ships (`Q33`: the palette is the four named materials,
    nothing else); it only votes at build time, and it needs the city's
    `individualised` sheet zips on disk.
    """

    wall: Material
    ribbon: Material
    roof: Material
    base: Material
    ribbon_first_m: float
    ribbon_pitch_m: float
    ribbon_thickness_m: float
    ribbon_count: int
    base_below_m: float
    roof_normal_y: float = 0.5
    soffit_normal_y: float = 0.5
    crease_deg: float = 35.0
    reference_texture: bool = False
    veto_ratio: float = 0.9


@dataclass(frozen=True)
class Landmark:
    """One hero building: the model that replaces its source meshes
    (`P3-6`, contract in `docs/ARCHITECTURE.md` under `landmarks.json`).

    Two kinds, told apart by `source_paint`. Without it, the model is an
    authored `.glb` committed under `assets/authored/landmarks/` (CC BY-SA,
    generated by `tools/make_landmark.py`). With it, the model is the source
    mesh itself, extracted and repainted by `pipeline/landmarks.py` into
    generated output under `assets/generated/landmarks/` — which is why the
    asset root differs per kind and `rot_y_deg` must be zero for the second:
    the extracted mesh keeps its source orientation, and a bearing on top
    would rotate it twice.

    `replaces_source_ids` holds **stems** — the cross-dataset building key
    `docs/DATA_SOURCES.md` establishes and `buildings.stem` computes — not full
    source ids. The same keying `P3-7a`'s override table uses, and deliberately
    unvalidated in shape here (an id format is a publisher's spelling, hard
    rule 3); a stem that matches nothing is caught by `export.py`'s
    set-equality check against what the building stage actually dropped.

    The position is authored in the city's projected CRS with elevation in the
    source datum, because that is what the surveyed blocks and meshes are
    published in — a number here can be checked against the sheet by eye.
    `export.py` converts it to game space; nothing downstream reads this form.

    `rot_y_deg` is a **compass bearing**: degrees clockwise from north, viewed
    from above — the convention `CityManifest.bearing_deg` already pins. The
    one conversion to a Godot rotation lives in the runtime's `landmarks.gd`.
    """

    id: str
    # `res://` path of the model — committed or generated per the kind above.
    asset: str
    easting: float
    northing: float
    elevation: float
    rot_y_deg: float
    # Display names, never rendered signage (`Q42`, hard rule 8).
    name_en: str
    name_zh: str
    replaces_source_ids: tuple[str, ...]
    # The in-engine ceiling `verify_landmarks.gd` holds each placed model to,
    # carried per entry in `landmarks.json`. The 8k default is ART_DESIGN.md's
    # authored-hero budget; a mesh-sourced hero pins its own measured ceiling.
    triangle_budget: int = 8000
    source_paint: SourcePaint | None = None


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
#
# ⚠️ **Only `category` is required, and the two names are deliberately not**
# (`P3-14`). TD's Tram Stop Location publishes an `OBJECTID`, a `STOP_ID` and a
# revision date, and no name in either language — 117 features, none named. The
# alternatives were both worse than an absent role: pointing `name_en` at a
# column that does not exist makes the config assert something untrue, and
# pointing it at `STOP_ID` ships "99101" as a place name.
#
# `fares.py` already treats an unnamed node as a state rather than an error — it
# counts them in `FareReport.unnamed` and warns — so a null name reaches the
# contract intact and says what the source says.
_FARE_ROLES = ("category",)
_FARE_OPTIONAL_ROLES = ("name_en", "name_zh")

# What each road layer must declare. The pipeline states its requirements here,
# in role names it owns, and the city file supplies the column names.
_ROAD_LAYER_ROLES: dict[str, tuple[str, ...]] = {
    "centrelines": ("elevation", "travel_direction", "route", "name_en", "name_zh"),
    "turns": ("first_edge", "first_end", "second_edge"),
    "speed_limits": ("route", "speed_limit"),
    "bus_lanes": ("route",),
}


# Kinds of kerbside line in the data contract (`P3-13`). The pipeline owns this
# vocabulary; which of the publisher's time-zone codes means which arrives from
# the city file, because the mapping is a road rule and not a fact about paint.
# Hong Kong's is the plain one — a restriction that runs 24 hours is a double
# yellow and a posted-hours one is a single.
KERB_SINGLE = "single"
KERB_DOUBLE = "double"
KERB_KINDS = (KERB_SINGLE, KERB_DOUBLE)

_KERBSIDE_ROLES = ("vehicle_type", "time_zone")

_KERBSIDE_AUDIT_ROLES = ("line_type",)


@dataclass(frozen=True)
class KerbsideAudit:
    """A second, independently digitised source of the same restrictions (`Q56`).

    **Nothing in `pipeline/` reads this.** It is config rather than constants in
    `tools/kerbside_source_audit.py` for the reason hard rule 3 gives: the layer
    name, the field and the marking codes are the Transport Department's schema,
    and a tool that spelled them itself would be the one place a Hong Kong fact
    lived outside the city file. A city without a second source leaves the block
    out and cannot be audited, which is the honest answer.

    `kinds` maps the drawing's own marking code onto a `KERB_KINDS` value, so
    the audit reaches a kind without going through `KerbsideRestrictions.kinds`.
    That independence is the entire point — an audit that derived its kind from
    the same `time_zone` table it is grading would agree with it by construction.
    """

    # A `sources` key, fetched but never read by a build.
    source: str
    layer: SourceLayer
    kinds: dict[str, str]


@dataclass(frozen=True)
class KerbsideRestrictions:
    """How `P3-13` reads a published no-stopping layer (`Q54`).

    Optional on `RoadNetwork`: a city whose sources carry no such layer leaves
    the block out and draws no kerbside restriction at all, which is the honest
    answer rather than the invented one `P3-12` shipped.
    """

    layer: SourceLayer
    # Source vehicle-type codes whose restriction is expressed as a **painted
    # line**. ⚠️ **"The rest are signs" was the reason until `Q56`, and it was
    # wrong** — the Traffic Aids Drawings paint the class-specific codes too. The
    # ones that stay out stay out because a restriction on *one class* is not a
    # plain yellow line and this codec cannot say which class, so painting it
    # would assert on all motor vehicles what the source restricts for goods
    # vehicles. That is a limit of the codec, not a fact about the road, and
    # `audit` below is what can tell the difference.
    painted_vehicle_types: frozenset[int]
    # Source time-zone code to a kind in `KERB_KINDS`. Every code the layer can
    # carry must appear: an unlisted one raises rather than defaulting, for the
    # reason `FareGroup.categorise` gives — these datasets are republished, and
    # a new code silently filed under a fallback would paint the wrong line
    # everywhere it appeared.
    kinds: dict[int, str]

    # Pitch the restriction lines are sampled at, and so the resolution of every
    # published run. Also the cell the samples are deduped into, which is what
    # makes two features covering one kerb count once.
    sample_m: float
    # Break in a restriction shorter than this is bridged rather than published
    # as two runs. A gap under a car length is not a place a car can stop, and
    # the source draws plenty of them — a vehicle crossing digitised as a break,
    # or two features meeting with a hair between them.
    bridge_gap_m: float
    # Shortest run worth publishing. Below this a run is sampling noise on a
    # bend rather than a length of kerb.
    min_run_m: float
    # Furthest a sample may sit from a centreline and still be that edge's. Not
    # a tuning value — it is the guard that says "this restriction belongs to a
    # road this region does not contain", and it doubles as the search radius.
    max_offset_m: float

    # The second source that grades this one, or `None` where the city has one
    # source and no way to check it. Read only by `tools/kerbside_source_audit.py`.
    #
    # The only field here with a default, because it is the only one whose
    # absence changes nothing the pipeline does: every other value is a number
    # the join needs, and defaulting one would let a city ship a restriction
    # measured against a pitch nobody chose. `_kerbside` passes this explicitly
    # regardless; the default is for the test fixtures and for a second city
    # that has no second source yet.
    audit: KerbsideAudit | None = None

    def kind_for(self, code: int) -> str:
        """The kind of line a source time-zone code means."""
        if code not in self.kinds:
            known = ", ".join(str(key) for key in sorted(self.kinds))
            raise KeyError(
                f"kerbside_restrictions has a feature with time zone {code}, which the city "
                f"file does not map to a kind. Known codes: {known}"
            )
        return self.kinds[code]


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

    # How `P3-13` sources the kerbside no-stopping line (`Q54`). `None` is a
    # city whose sources carry no such layer, and it draws none.
    kerbside: KerbsideRestrictions | None

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

    def optional_field(self, role: str) -> str | None:
        """The publisher's column for a role it need not publish at all.

        `None` where the source has no such column, which is a fact about the
        source rather than a hole in the config — see `_FARE_OPTIONAL_ROLES`.
        Separate from `field` so a *required* role still fails loudly: silently
        returning `None` for `category` would file every feature under nothing.
        """
        if role not in _FARE_OPTIONAL_ROLES:
            raise KeyError(
                f"fare group '{self.kind}': {role!r} is a required role, "
                f"use `field` — optional roles are {', '.join(_FARE_OPTIONAL_ROLES)}"
            )
        return self.fields.get(role)

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
    # Published carriageway edges, read only by `tools/carriageway_margin.py`
    # (`Q57`). Optional for the reason `KerbsideAudit` is: its absence changes
    # nothing a build does, and a city with no such layer is honestly
    # unmeasurable rather than measured against an invented width.
    carriageway_survey: CarriagewaySurvey | None = None
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
        carriageway_survey=_carriageway_survey(
            document.get("carriageway_survey"), f"{path}:carriageway_survey"
        ),
        tramway=_tramway(document.get("tramway"), f"{path}:tramway", table),
        arrows=_arrows(document.get("arrows"), f"{path}:arrows"),
        boxjunctions=_boxjunctions(document.get("boxjunctions"), f"{path}:boxjunctions"),
        railings=_railings(document.get("railings"), f"{path}:railings"),
        landmarks=_landmarks(document.get("landmarks") or [], f"{path}:landmarks", table),
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
    _check_landmarks_lie_within_a_region(city, path)
    return city


def _check_declared_source(city: CityConfig, spec: Any, where: str) -> None:
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


def _check_landmarks_lie_within_a_region(city: CityConfig, path: Path) -> None:
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
        check_material_exposure(material, city.exposure_anchor, f"{path}:materials.{name}")


def check_material_exposure(material: Material, anchor: float, where: str) -> None:
    """One colour against the palette rule — the shared body of
    `_check_exposure` and `tools/make_landmark.py`'s `check_palette`.

    Shared so the materials table and the landmark palette cannot drift onto
    different definitions of `Q33`: the generator's colours never pass through
    this loader, but they make the same claim and answer to the same tolerance.
    """
    expected = material.reflectance * anchor
    actual = reflectance(material.colour)
    if abs(actual - expected) > EXPOSURE_TOLERANCE_PCT:
        red, green, blue = material.colour
        raise ValueError(
            f"{where} is #{red:02x}{green:02x}{blue:02x}, whose "
            f"luminance is {actual:.2f}% — but it declares reflectance "
            f"{material.reflectance}% at exposure_anchor {anchor}, "
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
        kerbside=_kerbside(body.get("kerbside_restrictions"), f"{where}:kerbside_restrictions"),
    )


def _kerbside(body: Any, where: str) -> KerbsideRestrictions | None:
    """The optional kerbside-restriction block, checked at load.

    Every guard here refuses a config that *loads*. A block whose vehicle-type
    list is empty paints nothing while looking configured; a kind outside
    `KERB_KINDS` reaches `surface.py` as a string it has no case for; and a
    `sample_m` of zero divides by it. Caught here, the author sees the file and
    the key they just edited rather than a numpy error four stages later.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    painted = _require(body, "painted_vehicle_types", where)
    codes: set[int] = set()
    for code in painted:
        # The `elevation_levels` boolean trap, in a sequence rather than a
        # mapping: a bare `on` in a YAML list resolves to True, and True == 1,
        # so it would silently become "paint all motor vehicles".
        if isinstance(code, bool) or not isinstance(code, int):
            raise ValueError(f"{where}:painted_vehicle_types has {code!r}, which is not an integer")
        codes.add(code)
    if not codes:
        raise ValueError(f"{where}:painted_vehicle_types is empty; the stage would paint nothing")

    kinds: dict[int, str] = {}
    for code, kind in _require(body, "kinds", where).items():
        if isinstance(code, bool) or not isinstance(code, int):
            raise ValueError(f"{where}:kinds key {code!r} is not an integer")
        if kind not in KERB_KINDS:
            raise ValueError(
                f"{where}:kinds[{code}] is {kind!r}, expected one of {', '.join(KERB_KINDS)}"
            )
        kinds[code] = str(kind)
    if not kinds:
        raise ValueError(f"{where}:kinds is empty")

    lengths = _measures(
        body, where, ("sample_m", "bridge_gap_m", "min_run_m", "max_offset_m"), positive=True
    )
    if lengths["min_run_m"] < lengths["sample_m"]:
        # A minimum shorter than the pitch cannot reject anything: the shortest
        # run the sampler can produce is one cell.
        raise ValueError(
            f"{where}:min_run_m ({lengths['min_run_m']}) is below sample_m "
            f"({lengths['sample_m']}), so it would reject nothing"
        )

    return KerbsideRestrictions(
        layer=_source_layer(body, where, _KERBSIDE_ROLES),
        painted_vehicle_types=frozenset(codes),
        kinds=kinds,
        sample_m=lengths["sample_m"],
        bridge_gap_m=lengths["bridge_gap_m"],
        min_run_m=lengths["min_run_m"],
        max_offset_m=lengths["max_offset_m"],
        audit=_kerbside_audit(body.get("audit"), f"{where}:audit"),
    )


def _kerbside_audit(body: Any, where: str) -> KerbsideAudit | None:
    """The optional second-source block, checked at load like everything else.

    Checked here even though only a tool reads it, because the alternative is a
    grader that fails halfway through a build's worth of work on a typo. An
    empty `kinds` is refused for the same reason the pipeline's is: it would
    grade every metre as an unknown kind and report perfect disagreement.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    kinds: dict[str, str] = {}
    for code, kind in _require(body, "kinds", where).items():
        if kind not in KERB_KINDS:
            raise ValueError(
                f"{where}:kinds[{code!r}] is {kind!r}, expected one of {', '.join(KERB_KINDS)}"
            )
        kinds[str(code)] = str(kind)
    if not kinds:
        raise ValueError(f"{where}:kinds is empty; the audit would grade every metre unknown")

    return KerbsideAudit(
        source=str(_require(body, "source", where)),
        layer=_source_layer(body, where, _KERBSIDE_AUDIT_ROLES),
        kinds=kinds,
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


_CARRIAGEWAY_EDGE_ROLES = ("edge_type",)


def _carriageway_survey(body: Any, where: str) -> CarriagewaySurvey | None:
    """The optional published-carriageway-edge block (`Q57`).

    Checked at load even though only a tool reads it, for the reason
    `_kerbside_audit` gives: the alternative is an instrument that fails on a
    typo after reading a geodatabase. An empty `edges` is refused rather than
    treated as absent — a survey declaring no source would report total
    coverage of nothing, which reads as agreement.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    entries = _require(body, "edges", where)
    edges = tuple(
        _carriageway_edge(entry, f"{where}:edges[{index}]") for index, entry in enumerate(entries)
    )
    if not edges:
        raise ValueError(f"{where}:edges is empty; leave the block out instead")

    names = [edge.name for edge in edges]
    if len(set(names)) != len(names):
        # The report is keyed by name — a duplicate would silently merge two
        # publishers' answers into one column and hide the disagreement that
        # is the entire reason for reading more than one.
        raise ValueError(f"{where}:edges has repeated names ({', '.join(sorted(names))})")
    return CarriagewaySurvey(edges=edges)


_TRAMWAY_ROLES = ("line_type",)


def _tramway(body: Any, where: str, table: _MaterialTable) -> Tramway | None:
    """The optional published-tramway block (`Q58`).

    Absent, the region ships no `tram.glb` and the manifest names none — the
    honest answer for a city with no tramway, and the same shape `podiums` and
    `carriageway_survey` already use. What is *not* offered is drawing the
    tramway from `roads.tram_streets` instead: that flag says which streets
    carry a tram, and `Q58` measured that the rails are a median 3.26 m past the
    drawn kerb of the edge carrying the flag. The flag cannot place them.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    codes = tuple(str(code) for code in _require(body, "codes", where))
    if not codes:
        raise ValueError(f"{where}:codes is empty; the source would match no feature")

    gauge_m = float(_require(body, "gauge_m", where))
    tolerance_m = float(_require(body, "pair_tolerance_m", where))
    if gauge_m <= 0.0 or tolerance_m <= 0.0:
        raise ValueError(f"{where}: gauge_m and pair_tolerance_m must both be positive")
    if tolerance_m >= gauge_m:
        # At half the gauge a rail pairs with the *other track's* near rail as
        # readily as with its own, and the bed is then drawn across the four-foot
        # of neither. Refused rather than clamped: the number is a measurement
        # of the source's digitising spread, so a wrong one is a wrong survey.
        raise ValueError(
            f"{where}:pair_tolerance_m is {tolerance_m}, which is not narrower than the "
            f"{gauge_m} m gauge it qualifies — every rail would pair with both neighbours"
        )

    bed_width_m = float(_require(body, "bed_width_m", where))
    rail_width_m = float(_require(body, "rail_width_m", where))
    if not 0.0 < rail_width_m < bed_width_m:
        raise ValueError(
            f"{where}: rail_width_m {rail_width_m} must be positive and narrower than "
            f"bed_width_m {bed_width_m}"
        )

    return Tramway(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        layer=_source_layer(body, where, _TRAMWAY_ROLES),
        codes=codes,
        gauge_m=gauge_m,
        pair_tolerance_m=tolerance_m,
        rail_width_m=rail_width_m,
        bed_width_m=bed_width_m,
        bed_lift_m=float(_require(body, "bed_lift_m", where)),
        rail_lift_m=float(_require(body, "rail_lift_m", where)),
        max_snap_m=float(_require(body, "max_snap_m", where)),
        rail_material=table.get(
            str(_require(body, "rail_material", where)), f"{where}:rail_material"
        ),
        bed_material=table.get(str(_require(body, "bed_material", where)), f"{where}:bed_material"),
    )


_ARROW_ROLES = ("code", "bearing", "level", "size")


def _arrows(body: Any, where: str) -> Arrows | None:
    """The optional published-turn-arrow block (`Q53`, `Q57`).

    Absent, the region ships no `arrows.glb` and the manifest names none — the
    same shape `tramway` uses, and honest for a city whose estate publishes no
    marking symbols. What is *not* offered is a fallback that derives arrows
    from junction geometry: `Q53` refused arrows precisely because inventing
    their content is a `P3-9a` debit, and a fallback here would reintroduce it
    silently on any city missing the block.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw = _require(body, "glyphs", where)
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{where}:glyphs must be a non-empty mapping of code to glyph")
    glyphs: dict[str, ArrowGlyph] = {}
    for code, entry in raw.items():
        spot = f"{where}:glyphs.{code}"
        if not isinstance(entry, dict):
            raise ValueError(f"{spot} must be a mapping with movements and length_m, got {entry!r}")
        movements = _require(entry, "movements", spot)
        if isinstance(movements, str) or not isinstance(movements, (list, tuple)):
            raise ValueError(f"{spot}:movements must be a list, got {movements!r}")
        named = tuple(str(movement) for movement in movements)
        if not named:
            raise ValueError(f"{spot}:movements is empty; an arrow pointing nowhere draws nothing")
        unknown = [movement for movement in named if movement not in ARROW_MOVEMENTS]
        if unknown:
            raise ValueError(
                f"{spot}:movements names {', '.join(unknown)}, which is not one of "
                f"{', '.join(ARROW_MOVEMENTS)} — the pipeline has no geometry to draw it"
            )
        if len(set(named)) != len(named):
            # A repeated movement would draw the same head twice, in the same
            # place, at the same height — invisible, and the mesh silently
            # heavier. Refused rather than deduped: a duplicate means the table
            # was transcribed wrong, and the rest of that row is then suspect.
            raise ValueError(f"{spot}:movements repeats a movement: {named}")
        length_m = float(_require(entry, "length_m", spot))
        if length_m <= 0.0:
            raise ValueError(f"{spot}:length_m must be positive, got {length_m}")
        glyphs[str(code)] = ArrowGlyph(movements=named, length_m=length_m)

    fractions = {
        name: float(_require(body, name, where))
        for name in ("stem_width_frac", "head_length_frac", "head_width_frac", "branch_reach_frac")
    }
    outside = {name: value for name, value in fractions.items() if not 0.0 < value < 1.0}
    if outside:
        raise ValueError(
            f"{where}: {', '.join(sorted(outside))} must each be a fraction of an arrow's own "
            f"length, strictly between 0 and 1; got {outside}"
        )
    if fractions["stem_width_frac"] >= fractions["head_width_frac"]:
        raise ValueError(
            f"{where}: stem_width_frac {fractions['stem_width_frac']} must be narrower than "
            f"head_width_frac {fractions['head_width_frac']}, or the head is not a head"
        )

    max_offset_m = float(_require(body, "max_offset_m", where))
    if max_offset_m <= 0.0:
        raise ValueError(f"{where}:max_offset_m must be positive, got {max_offset_m}")
    tolerance_deg = float(_require(body, "bearing_tolerance_deg", where))
    if not 0.0 < tolerance_deg <= 90.0:
        # Past 90 degrees a symbol lying square across its edge passes, which is
        # the exact signature of a match to the wrong edge. The check would
        # still run and would refuse nothing.
        raise ValueError(
            f"{where}:bearing_tolerance_deg is {tolerance_deg}; it must be positive and no "
            f"more than 90, or a symbol square across its edge is accepted"
        )

    lift_m = float(_require(body, "lift_m", where))
    if lift_m <= 0.0:
        raise ValueError(
            f"{where}:lift_m is {lift_m}; paint coplanar with the road it is painted on z-fights"
        )

    return Arrows(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        layer=_source_layer(body, where, _ARROW_ROLES),
        glyphs=glyphs,
        stem_width_frac=fractions["stem_width_frac"],
        head_length_frac=fractions["head_length_frac"],
        head_width_frac=fractions["head_width_frac"],
        branch_reach_frac=fractions["branch_reach_frac"],
        lift_m=lift_m,
        max_offset_m=max_offset_m,
        bearing_tolerance_deg=tolerance_deg,
    )


_BOXJUNCTION_ROLES = ("type", "level", "hatch_a", "hatch_b")


def _boxjunctions(body: Any, where: str) -> BoxJunctions | None:
    """The optional published-box-junction block (`P3-18`).

    Absent, the region ships no `boxjunctions.glb` and the manifest names none —
    the shape `tramway` and `arrows` both use. What is *not* offered is a
    fallback that puts a box on every junction node: the region publishes 20
    boxes against 393 junctions, so a derived placement would be wrong nineteen
    times in twenty, and `Q53` refused exactly that.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw_types = _require(body, "box_types", where)
    if isinstance(raw_types, str) or not isinstance(raw_types, (list, tuple)):
        raise ValueError(f"{where}:box_types must be a list, got {raw_types!r}")
    box_types = tuple(str(value) for value in raw_types)
    if not box_types:
        # An empty list admits nothing, which is the same outcome as omitting
        # the block — refused so the difference is a decision, not a typo.
        raise ValueError(f"{where}:box_types is empty; a block that draws nothing is a mistake")

    widths = {
        name: float(_require(body, name, where))
        for name in ("border_width_m", "hatch_width_m", "hatch_spacing_m", "station_m")
    }
    negative = {name: value for name, value in widths.items() if value <= 0.0}
    if negative:
        raise ValueError(f"{where}: {', '.join(sorted(negative))} must be positive; got {negative}")
    if widths["hatch_width_m"] >= widths["hatch_spacing_m"]:
        raise ValueError(
            f"{where}: hatch_width_m {widths['hatch_width_m']} must be narrower than "
            f"hatch_spacing_m {widths['hatch_spacing_m']}, or the hatch is a fill"
        )

    max_offset_m = float(_require(body, "max_offset_m", where))
    if max_offset_m <= 0.0:
        raise ValueError(f"{where}:max_offset_m must be positive, got {max_offset_m}")
    height_blend_m = float(_require(body, "height_blend_m", where))
    if height_blend_m <= 0.0:
        # Zero is the nearest-edge cliff the field exists to remove — two arms
        # of one junction disagree by a measured 0.43 m where they meet, and a
        # hard switch between them built 172 near-vertical triangles.
        raise ValueError(
            f"{where}:height_blend_m is {height_blend_m}; it must be positive, or the height "
            f"join cliffs where two arms of one junction meet"
        )

    lift_m = float(_require(body, "lift_m", where))
    if lift_m <= 0.0:
        raise ValueError(
            f"{where}:lift_m is {lift_m}; paint coplanar with the road it is painted on z-fights"
        )
    border_lift_m = float(_require(body, "border_lift_m", where))
    if border_lift_m <= 0.0:
        raise ValueError(
            f"{where}:border_lift_m is {border_lift_m}; the boundary line coplanar with the "
            f"hatch it crosses z-fights it"
        )

    return BoxJunctions(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        layer=_source_layer(body, where, _BOXJUNCTION_ROLES),
        box_types=box_types,
        border_width_m=widths["border_width_m"],
        hatch_width_m=widths["hatch_width_m"],
        hatch_spacing_m=widths["hatch_spacing_m"],
        station_m=widths["station_m"],
        lift_m=lift_m,
        border_lift_m=border_lift_m,
        max_offset_m=max_offset_m,
        height_blend_m=height_blend_m,
    )


_RAILING_ROLES = ("line_type", "level")


def _railings(body: Any, where: str) -> Railings | None:
    """The optional published-railing block (`P3-19`, `Q60`).

    Absent, the region ships no `railings.glb` and the manifest names none —
    the shape `tramway`, `arrows` and `boxjunctions` all take. What is *not*
    offered is a fallback that runs a fence down every kerb: this region's
    published railings cover 20.3 km against 130 km of drawn kerb, and a
    derived railing would be a wall along streets that have none.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw_types = _require(body, "drawn_line_types", where)
    if isinstance(raw_types, str) or not isinstance(raw_types, (list, tuple)):
        raise ValueError(f"{where}:drawn_line_types must be a list, got {raw_types!r}")
    drawn_line_types = tuple(str(value) for value in raw_types)
    if not drawn_line_types:
        # An empty whitelist admits nothing, which is what omitting the block
        # already does — refused so the difference is a decision, not a typo.
        raise ValueError(
            f"{where}:drawn_line_types is empty; a block that draws nothing is a mistake"
        )
    if len(set(drawn_line_types)) != len(drawn_line_types):
        # A repeat would double a code's metres in the refusal accounting and
        # nothing else, which is exactly the kind of quiet wrong this stage's
        # counters exist to prevent.
        raise ValueError(f"{where}:drawn_line_types repeats a code: {drawn_line_types}")

    measures = {
        name: float(_require(body, name, where))
        for name in (
            "sample_m",
            "max_offset_m",
            "max_shift_m",
            "bridge_gap_m",
            "min_run_m",
            "station_m",
            "height_m",
        )
    }
    negative = {name: value for name, value in measures.items() if value <= 0.0}
    if negative:
        raise ValueError(f"{where}: {', '.join(sorted(negative))} must be positive; got {negative}")
    if measures["min_run_m"] < measures["sample_m"]:
        # A minimum shorter than the sampling pitch cannot refuse anything: the
        # shortest run the sampler can produce is one cell.
        raise ValueError(
            f"{where}:min_run_m {measures['min_run_m']} is shorter than sample_m "
            f"{measures['sample_m']}, so it would refuse nothing"
        )

    lifts = {name: float(_require(body, name, where)) for name in ("base_sink_m", "outset_m")}
    if any(value < 0.0 for value in lifts.values()):
        raise ValueError(f"{where}: base_sink_m and outset_m may not be negative; got {lifts}")

    return Railings(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        layer=_source_layer(body, where, _RAILING_ROLES),
        drawn_line_types=drawn_line_types,
        sample_m=measures["sample_m"],
        max_offset_m=measures["max_offset_m"],
        max_shift_m=measures["max_shift_m"],
        bridge_gap_m=measures["bridge_gap_m"],
        min_run_m=measures["min_run_m"],
        station_m=measures["station_m"],
        height_m=measures["height_m"],
        base_sink_m=lifts["base_sink_m"],
        outset_m=lifts["outset_m"],
    )


def _carriageway_edge(body: Any, where: str) -> CarriagewayEdge:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    codes = tuple(str(code) for code in _require(body, "codes", where))
    if not codes:
        raise ValueError(f"{where}:codes is empty; the source would match no feature")

    layer = _source_layer(body, where, _CARRIAGEWAY_EDGE_ROLES)
    off_grade = tuple(str(code) for code in (body.get("off_grade_codes") or ()))
    if off_grade and "elevation" not in layer.fields:
        # It would load, filter nothing, and report a level-0 figure computed
        # over the flyovers too — the silently-inert block `_sampling_block`
        # refuses for the same reason.
        raise ValueError(
            f"{where}:off_grade_codes lists {', '.join(off_grade)} but fields has no "
            "'elevation' role to read them from"
        )

    return CarriagewayEdge(
        name=str(_require(body, "name", where)),
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        layer=layer,
        codes=codes,
        off_grade_codes=off_grade,
    )


def _tile_member(body: dict[str, Any], where: str, *, required: bool = False) -> str | None:
    """The geodatabase path inside a per-sheet zip, with `{tile}` for the sheet id.

    Checked at load rather than at first read: a stray or malformed placeholder
    would otherwise surface once per sheet, deep into a fetch.
    """
    member = _require(body, "member", where) if required else body.get("member")
    if member is None:
        return None
    member = str(member)
    try:
        member.format(tile="probe")
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError(
            f"{where}:member {member!r} allows only the {{tile}} placeholder ({error})"
        ) from error
    return member


_PODIUM_BLOCK_ROLES = ("block_type", "base_level", "roof_level", "certainty")

_PODIUM_CODE_ROLES = ("tower", "podium")


def _podium_blocks(body: dict[str, Any], where: str) -> PodiumBlocks:
    member = _tile_member(body, where, required=True)
    assert member is not None  # `required` guarantees it; narrows for the type checker
    return PodiumBlocks(
        source=str(_require(body, "source", where)),
        member=member,
        blocks=_source_layer(
            _require(body, "blocks", where), f"{where}:blocks", _PODIUM_BLOCK_ROLES
        ),
        codes=_fields(body, where, _PODIUM_CODE_ROLES, key="codes"),
    )


# Where a landmark's committed model must live. Game layout rather than city
# data — `docs/ARCHITECTURE.md` fixes it and CLAUDE.md commits the directory —
# so pinning it here is contract enforcement, not a hard-rule-3 violation.
# Public because `export.py`'s validator checks shipped documents against the
# same root: two spellings of the rule is how they come to disagree.
LANDMARK_ASSET_ROOT = "res://assets/authored/landmarks/"

# Where a mesh-sourced hero's repainted model lands instead. Generated output,
# gitignored, governed by the data publisher's terms rather than CC BY-SA —
# `LICENSING.md` is why the two roots must never be confused. Public for the
# same reason as `LANDMARK_ASSET_ROOT`.
LANDMARK_GENERATED_ROOT = "res://assets/generated/landmarks/"

# The surface roles a `source_paint` block must name, in the order the
# `SourcePaint` fields declare them.
_PAINT_SURFACES = ("wall", "ribbon", "roof", "base")


def _landmarks(entries: list[Any], where: str, table: _MaterialTable) -> tuple[Landmark, ...]:
    landmarks = tuple(
        _landmark(entry, f"{where}[{index}]", table) for index, entry in enumerate(entries)
    )
    seen: dict[str, str] = {}
    stems: dict[str, str] = {}
    for index, landmark in enumerate(landmarks):
        place = f"{where}[{index}]"
        if landmark.id in seen:
            raise ValueError(f"{place} reuses id {landmark.id!r}, declared at {seen[landmark.id]}")
        seen[landmark.id] = place
        for stem in landmark.replaces_source_ids:
            if stem in stems:
                # Two heroes claiming one building would have the second's
                # equality check fail on a stem the first already consumed —
                # a confusing report for a config-local mistake.
                raise ValueError(f"{place} replaces {stem!r}, already claimed at {stems[stem]}")
            stems[stem] = place
    return landmarks


def _landmark(body: dict[str, Any], where: str, table: _MaterialTable) -> Landmark:
    landmark_id = str(_require(body, "id", where))
    asset = str(_require(body, "asset", where))
    paint = (
        _source_paint(body["source_paint"], f"{where}:source_paint", table)
        if body.get("source_paint") is not None
        else None
    )
    rotation = _measures(body, where, ("rot_y_deg",))
    if paint is not None:
        # The stage derives the output path from the id, so the asset must be
        # exactly that derivation — a near-miss would ship a model the
        # manifest points past.
        expected = f"{LANDMARK_GENERATED_ROOT}{landmark_id}.glb"
        if asset != expected:
            raise ValueError(
                f"{where}:asset is {asset!r}, but a mesh-sourced landmark ships its "
                f"repainted source mesh as generated output — expected {expected!r}"
            )
        if rotation["rot_y_deg"] != 0.0:
            raise ValueError(
                f"{where}:rot_y_deg is {rotation['rot_y_deg']!r}, but a mesh-sourced "
                "landmark keeps its source orientation — a bearing on top would "
                "rotate it twice; author 0.0"
            )
    elif not asset.startswith(LANDMARK_ASSET_ROOT) or not asset.endswith(".glb"):
        raise ValueError(
            f"{where}:asset is {asset!r}, expected a .glb under {LANDMARK_ASSET_ROOT} — "
            "authored landmark models are committed there (docs/ARCHITECTURE.md)"
        )
    names = _require(body, "name", where)
    replaces = _require(body, "replaces_source_ids", where)
    if not isinstance(replaces, list) or not replaces:
        # An empty list would place a hero inside the source building it was
        # meant to replace — the z-fighting the field exists to prevent.
        raise ValueError(f"{where}:replaces_source_ids must be a non-empty list")
    position = _measures(
        _require(body, "pos", where), f"{where}:pos", ("easting", "northing", "elevation")
    )
    budget = body.get("triangle_budget", 8000)
    if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
        raise ValueError(f"{where}:triangle_budget is {budget!r}, expected a positive integer")
    return Landmark(
        id=landmark_id,
        asset=asset,
        easting=position["easting"],
        northing=position["northing"],
        elevation=position["elevation"],
        rot_y_deg=rotation["rot_y_deg"],
        name_en=str(_require(names, "en", f"{where}:name")),
        name_zh=str(_require(names, "zh", f"{where}:name")),
        replaces_source_ids=tuple(str(stem) for stem in replaces),
        triangle_budget=budget,
        source_paint=paint,
    )


def _source_paint(body: dict[str, Any], where: str, table: _MaterialTable) -> SourcePaint:
    surfaces = _require(body, "materials", where)
    ribbons = _require(body, "ribbons", where)
    strips = _measures(
        ribbons, f"{where}:ribbons", ("first_m", "pitch_m", "thickness_m"), positive=True
    )
    count = _require(ribbons, "count", f"{where}:ribbons")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError(f"{where}:ribbons:count is {count!r}, expected a non-negative integer")
    base = _measures(body, where, ("base_below_m",))
    if base["base_below_m"] < 0.0:
        raise ValueError(f"{where}:base_below_m is {base['base_below_m']!r}, expected >= 0")
    thresholds: dict[str, float] = {}
    for key in ("roof_normal_y", "soffit_normal_y", "veto_ratio"):
        if body.get(key) is None:
            continue
        value = _measures(body, where, (key,))[key]
        if not 0.0 < value <= 1.0:
            # 0 would claim every wall as roof (or veto every band); above 1
            # nothing ever matches and the knob silently does nothing.
            raise ValueError(f"{where}:{key} is {value!r}, expected within (0, 1]")
        thresholds[key] = value
    if body.get("crease_deg") is not None:
        crease = _measures(body, where, ("crease_deg",))["crease_deg"]
        if not 0.0 < crease < 180.0:
            # 0 never grows past the seed; 180 grows through every edge and
            # floods the whole mesh with the first seed's surface.
            raise ValueError(f"{where}:crease_deg is {crease!r}, expected within (0, 180)")
        thresholds["crease_deg"] = crease
    reference = body.get("reference_texture", False)
    if not isinstance(reference, bool):
        raise ValueError(f"{where}:reference_texture is {reference!r}, expected a boolean")
    wall, ribbon, roof, base_surface = (
        table.get(str(_require(surfaces, role, f"{where}:materials")), f"{where}:materials:{role}")
        for role in _PAINT_SURFACES
    )
    return SourcePaint(
        wall=wall,
        ribbon=ribbon,
        roof=roof,
        base=base_surface,
        ribbon_first_m=strips["first_m"],
        ribbon_pitch_m=strips["pitch_m"],
        ribbon_thickness_m=strips["thickness_m"],
        ribbon_count=count,
        base_below_m=base["base_below_m"],
        reference_texture=reference,
        **thresholds,
    )


def _fields(
    body: dict[str, Any],
    where: str,
    roles: tuple[str, ...],
    *,
    key: str = "fields",
    optional: tuple[str, ...] | None = None,
) -> dict[str, str]:
    """A role-to-value mapping (columns, domain codes), checked to cover every
    role the stage needs.

    Checked at load for the reason `_check_source_exists` gives.
    """
    fields = {str(role): str(column) for role, column in _require(body, key, where).items()}
    missing = [role for role in roles if role not in fields]
    if missing:
        raise ValueError(f"{where}:{key} is missing {', '.join(missing)}")
    if optional is not None:
        # ⚠️ **An unknown key is refused, and that is what keeps an *optional*
        # role honest.** A required role fails loudly when it is absent; an
        # optional one is indistinguishable from a typo, so without this a
        # renamed `name_zh:` would simply stop being read and every node would
        # ship nameless. Only checked where a caller declares optional roles —
        # every other `fields:` block is exhaustively required already.
        unknown = [role for role in fields if role not in roles and role not in optional]
        if unknown:
            allowed = ", ".join((*roles, *optional))
            raise ValueError(
                f"{where}:{key} has unknown role(s) {', '.join(sorted(unknown))}. Known: {allowed}"
            )
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
        fields=_fields(body, where, _FARE_ROLES, optional=_FARE_OPTIONAL_ROLES),
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
