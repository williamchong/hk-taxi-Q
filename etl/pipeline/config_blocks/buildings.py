"""The `buildings:` style and `podium_blocks:`.

Materials, the height ramp, the façade draw, cells and occluders.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from pipeline.config_blocks.base import (
    Material,
    SourceLayer,
    _field,
    _fields,
    _MaterialTable,
    _measures,
    _parse_hex,
    _require,
    _source_layer,
    _tile_member,
)

# How far a set of draw weights may sit from summing to 1.0. Float addition of
# authored decimals, and nothing else — see `WeightedDraw.build` for why they are
# refused rather than normalised.
WEIGHT_SUM_TOLERANCE = 1e-6


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
    # The clustering cell the tile COLLIDER is built at, in metres (`P5-12`).
    #
    # Stated on its own rather than borrowed from a tier, because the collider
    # is its own mesh now — `<tile>_collision-colonly` beside the render tiers —
    # and the two are allowed to diverge. A collider coarser than the facade is
    # a wall the car drives into or through, so `tools/collider_offset.py`
    # measures the offset between them and this value is what it sweeps.
    collision_cell_m: float
    # The collider's cell for a class that must not decimate like the rest —
    # the same classes, for the same reasons, as `class_lod_cell_sizes_m`.
    class_collision_cell_m: dict[str, float]
    # The cell the tile OCCLUDER is clustered at (`P5-13`), its own value like
    # the collider's: it is rasterised on the CPU every frame, so it wants the
    # coarsest geometry that still stands where the buildings do, and a stated
    # cell is what a sweep can price. 🔴 **Per TIER since `P5-17` (`Q122`), one
    # entry per `lod_cell_sizes_m` entry, `None` meaning that tier carries no
    # occluder at all.** The streamer swaps whole tier scenes, so the occluder
    # rides in every tier that wants one and its PCK price is paid once per
    # tier — the duplication `Q121` left unpriced. One list covers the finest-
    # tier-only experiment, a coarser far tier, and a bundle with none (the web
    # cut, whose stock export template cannot cull).
    occluder_cell_m: tuple[float | None, ...]
    # The occluder's cell for a class that must not decimate like the rest —
    # the same classes, for the same reasons, as `class_lod_cell_sizes_m`. A
    # class statement, so it applies in every tier that carries an occluder.
    class_occluder_cell_m: dict[str, float]
    # The classes the occluder is built from — a subset of `classes`. The ground
    # is left out on purpose: a hillside occludes little a building in front of
    # it does not, and the terrain is the largest single surface in the region.
    occluder_classes: tuple[str, ...]
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

    def collision_cell_size_m(self, class_id: str) -> float:
        """Clustering cell for one class in the tile collider (`P5-12`)."""
        return self.class_collision_cell_m.get(class_id, self.collision_cell_m)

    def occluder_cell_size_m(self, class_id: str, level: int) -> float | None:
        """Clustering cell for one class in tier `level`'s occluder (`P5-13`),
        or `None` where that tier carries no occluder (`P5-17`)."""
        cell = self.occluder_cell_m[level]
        if cell is None:
            return None
        return self.class_occluder_cell_m.get(class_id, cell)

    def occluder_tiers(self) -> tuple[int, ...]:
        """The tier indices that carry an occluder."""
        return tuple(level for level, cell in enumerate(self.occluder_cell_m) if cell is not None)

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
            bounds=_albedo_bounds(
                _require(entry, "bounds", f"{where}.{name}"), f"{where}.{name}.bounds"
            ),
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


def _cell_table(
    body: dict[str, Any], where: str, key: str, classes: tuple[str, ...]
) -> tuple[float, dict[str, float]]:
    """A stated clustering cell and its per-class overrides — `collision_cell_m`
    with `class_collision_cell_m` (`P5-12`), and the occluder's pair (`P5-13`).

    0.0 is an exact weld, as in `lod_cell_sizes_m` (`Q16`) — legal, and a
    bundle decision: it ships the full massing. A misspelled class key is the
    same trap as `class_lod_cell_sizes_m`'s: it parses, loads, and silently
    overrides nothing, so it is refused here.
    """
    cell = _number(_require(body, key, where), f"{where}:{key}")
    if cell < 0.0:
        raise ValueError(f"{where}:{key} must not be negative ({cell})")
    per_class: dict[str, float] = {}
    for name, size in (body.get(f"class_{key}") or {}).items():
        field = f"{where}:class_{key}.{name}"
        if str(name) not in classes:
            raise ValueError(f"{field} is not in classes ({', '.join(classes)})")
        override = _number(size, field)
        if override < 0.0:
            raise ValueError(f"{field} must not be negative ({override})")
        per_class[str(name)] = override
    return cell, per_class


def _occluder_cells(
    body: dict[str, Any], where: str, classes: tuple[str, ...], tiers: int
) -> tuple[tuple[float | None, ...], dict[str, float]]:
    """The occluder's cell per tier (`P5-17`) and its per-class overrides.

    A list with one entry per tier of `lod_cell_sizes_m`, `null` meaning the
    tier carries no occluder; a short or long list is refused for the reason
    `class_lod_cell_sizes_m` refuses one. A scalar is refused too, rather than
    broadcast: the whole point of the list is that a reader can see which tiers
    pay for the occluder, and a scalar would hide that again. The overrides are
    `_cell_table`'s rules — a misspelled class parses and overrides nothing.
    """
    raw = _require(body, "occluder_cell_m", where)
    field = f"{where}:occluder_cell_m"
    if not isinstance(raw, list):
        raise ValueError(f"{field} must be a list with one cell per tier, null for none")
    if len(raw) != tiers:
        raise ValueError(f"{field} has {len(raw)} tiers, but lod_cell_sizes_m has {tiers}")
    cells: list[float | None] = []
    for level, value in enumerate(raw):
        if value is None:
            cells.append(None)
            continue
        cell = _number(value, f"{field}[{level}]")
        if cell < 0.0:
            raise ValueError(f"{field}[{level}] must not be negative ({cell})")
        cells.append(cell)
    per_class: dict[str, float] = {}
    for name, size in (body.get("class_occluder_cell_m") or {}).items():
        override_field = f"{where}:class_occluder_cell_m.{name}"
        if str(name) not in classes:
            raise ValueError(f"{override_field} is not in classes ({', '.join(classes)})")
        override = _number(size, override_field)
        if override < 0.0:
            raise ValueError(f"{override_field} must not be negative ({override})")
        per_class[str(name)] = override
    return tuple(cells), per_class


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

    # ⚠️ **Refused rather than ignored** (`Q102`). The vision reader this block
    # configured is gone, and so is the `TEXCOORD_1` payload it fed. A stale
    # `facade_survey:` in a clone's config would otherwise be a silent no-op.
    #
    # ⚠️ **This closes one literal key, not the class.** `_fields`' unknown-role
    # check is the general version of the same idea, and `_building_style` has
    # no equivalent — every other stale or misspelled key under `buildings:` is
    # still a silent no-op. A general check would subsume this one and is the
    # better fix if the class is ever worth closing.
    #
    # ⚠️ **Presence, not truthiness.** A bare `facade_survey:` parses as `None`,
    # so `.get(...) is not None` would wave through the one spelling most likely
    # to be left behind by half-deleting the block — the exact no-op this refuses.
    if "facade_survey" in body:
        raise ValueError(
            f"{where}:facade_survey is retired — the vision reader it configured was "
            "withdrawn (`Q102`). Remove the block."
        )

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

    collision_cell, class_collision = _cell_table(body, where, "collision_cell_m", classes)
    occluder_cell, class_occluder = _occluder_cells(body, where, classes, len(cells))
    occluder_classes = tuple(str(name) for name in _require(body, "occluder_classes", where))
    if not occluder_classes:
        raise ValueError(
            f"{where}:occluder_classes is empty — an occluder of nothing occludes nothing"
        )
    unknown = set(occluder_classes) - set(classes)
    if unknown:
        raise ValueError(
            f"{where}:occluder_classes names {', '.join(sorted(unknown))}, "
            f"which is not in classes ({', '.join(classes)})"
        )

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
        lod_cell_sizes_m=cells,
        class_lod_cell_sizes_m=class_cells,
        collision_cell_m=collision_cell,
        class_collision_cell_m=class_collision,
        occluder_cell_m=occluder_cell,
        class_occluder_cell_m=class_occluder,
        occluder_classes=occluder_classes,
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


def _albedo_bounds(value: Any, field: str) -> tuple[float, float]:
    """The published albedo range a `source` names, as `[low, high]` percentages.

    Both ends go through `_reflectance`, so the pair inherits its `(0, 100]` and
    its refusal of `.nan`/`.inf` rather than restating them. What is added here
    is order: `low < high` strictly, because a zero-width range is a reflectance
    written twice and would make `_check_reflectance`'s second test an equality
    no 8-bit colour can satisfy.

    🔴 **There is deliberately NO ceiling on the width, and that is not an
    oversight to close.** `[30, 60]` is wide — `_check_reflectance` admits
    ±15 pp there where the round trip admits ±0.5 — and it is wide because
    *painted render really is 30-60%*. The number transcribes a published range;
    a width cap would refuse a true citation on the grounds that it is
    inconvenient, which is `Q54`'s invented-data rule pointing the other way. The
    defence against a vacuous `[1, 100]` is the same one `source` has always
    had: somebody has to write down where it came from, and a reviewer reads it.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field} must be a two-element [low, high], got {value!r}")
    low = _reflectance(value[0], f"{field}[0]")
    high = _reflectance(value[1], f"{field}[1]")
    if not low < high:
        raise ValueError(f"{field} must have low < high, got [{low}, {high}]")
    return (low, high)


def _reflectance(value: Any, field: str) -> float:
    """A real-world diffuse albedo as a percentage, in (0, 100].

    Zero is refused rather than clamped: a surface reflecting nothing is a
    surface no material has, and it would pair with a black colour that passes
    `_check_reflectance` while saying nothing about what it depicts. 100 is the
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
