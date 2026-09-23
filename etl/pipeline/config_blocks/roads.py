"""`roads:` and what is measured on it.

The network, the surface, decks, kerbside, the carriageway survey and region,
carve, clearance, fence, join.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    LayerSpec,
    Material,
    SourceLayer,
    _MaterialTable,
    _measures,
    _require,
    _source_layer,
    _spec_header,
)


@dataclass(frozen=True)
class Join:
    """How far past its own bounds a region reads its sources (`Q116`, `P5-7c`).

    A road that crosses into a declared neighbour is owned whole by one region,
    which then measures a far half over sources its rectangle never selected —
    Wan Chai's sheets stop about 85 m past the shared line and the longest far
    half runs 133 m. `reach_m` widens sheet selection and every source-read bbox
    on the sides where a declared neighbour shares an edge, and nowhere else,
    so a region with no neighbour reads exactly what it read before.

    ⚠️ **`bounds` and the tile grid do not move** (`Q10`): this widens what is
    *read*, never where the region *is*. Whether a feature found in the margin
    is published at all is `roads.py`'s ownership rule, not this number.
    """

    reach_m: float


# What kind of geometry a carriageway publisher draws (`Q94`). Named next to the
# validation that accepts them, for the reason `MARKING_DIRECTIONS` gives: the
# stage that acts on a vocabulary must not drift from the set that is accepted.
CARRIAGEWAY_LINE = "line"


CARRIAGEWAY_AREA = "area"


CARRIAGEWAY_GEOMETRIES = frozenset({CARRIAGEWAY_LINE, CARRIAGEWAY_AREA})


@dataclass(frozen=True)
class CarriagewayEdge(LayerSpec):
    """One published opinion on where the edge of the carriageway runs (`Q57`).

    ⚠️ **Read by the build since `Q95`** — `pipeline/carriageway.py` runs the
    roads stage's own survey over these edges, deliberately as a second
    implementation of `tools/carriageway_margin.py`'s (`CLAUDE.md`: the two are
    expected to agree, and sharing a core would retire the only independent
    check). It is config rather than constants because the layer name, the
    field and the domain codes are the publisher's schema. A region with no
    such layer leaves the block out and cannot be measured, which is the honest
    answer rather than a fabricated width.

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
    codes: tuple[str, ...]
    off_grade_codes: tuple[str, ...]
    # `line` for a published carriageway EDGE, `area` for a published carriageway
    # SURFACE (`Q94`). 🔴 **Not a detail of the reader — a different measurement.**
    # An edge layer is cast at directly; an area layer's own internal seams are
    # not kerbs, so the boundary of the *union* is what a ray may stop at. HyD
    # tiles Wan Chai's carriageway into 552 polygons and a naive ray stops at the
    # first seam it meets.
    geometry: str = CARRIAGEWAY_LINE

    @property
    def elevation_field(self) -> str | None:
        """The publisher's grade column, where it publishes one."""
        return self.layer.fields.get("elevation")


@dataclass(frozen=True)
class WidthBounds:
    """What the city's own design manual permits a carriageway to be (`Q95`).

    ⚠️ **A standard is not a survey**, and these numbers may only bound an
    instrument — never assign a width. `DATA_SOURCES.md` says why at length: a
    width taken from a road's class would be authoring policy with better
    provenance, which is the move `lanes_by_min_speed_limit_kph` already makes
    and the one `Q95` was opened about. What they are for is telling a
    two-sided ray that has crossed a median from one that has measured a road.

    Hong Kong's are read off TD's Transport Planning & Design Manual Vol 2
    Ch 3; hard rule 3 keeps them here rather than in the tool, because the
    second city has its own manual.
    """

    # The widest urban carriageway the manual permits. Above this a ray has
    # crossed a median, a tram reserve or a junction mouth.
    max_m: float
    # The narrowest it *should* be. Reported, never refused — see the city file.
    min_m: float
    # Below one through lane the reading is not a carriageway at all.
    hard_min_m: float
    # The permitted through-lane range, as (narrowest, widest).
    #
    # 🔴 A bracket rather than one number, and never the pipeline's own
    # `lane_width_m`. Dividing a measured width by the authored constant would
    # make the instrument agree with the value under test by construction,
    # which is `Q72`'s tautology one dimension over.
    lane_m: tuple[float, float]

    # ── Decomposing a one-way span back into two carriageways ──────────────
    #
    # `max_m` above bounds a *span*: both kerbs, one publisher, one station.
    # Where the centreline is half of an opposed pair that span is two
    # carriageways and a separator, so the three below bound the parts rather
    # than the whole. They are read off the same table and the same chapter.

    # The widest ONE carriageway of an opposed pair. Table 3.4.2.1's dual
    # column, which is a different column from the single one `max_m` comes
    # from — a decomposed half is by definition a dual carriageway, so it gets
    # the tighter ceiling the manual already publishes for it.
    dual_max_m: float
    # The NARROWEST one carriageway of an opposed pair — the same column's other
    # end, and the bound that says whether a span crossed a median at all.
    #
    # 🔴 **This is a bound on the room a span leaves BEYOND the edge's own
    # carriageway**, not on the carriageway itself. Under one through lane
    # (`hard_min_m`) there is nowhere for an opposed carriageway to be, so the
    # span never crossed one and *is* this edge's width; at or above this there
    # is room for the narrowest dual carriageway the manual permits, so it may
    # have. Between the two the reading is published as neither, because a
    # single threshold would have to call that gap one way or the other and the
    # data does not say which.
    #
    # ⚠️ **A clause, not a fitted value.** `Q72` rejected a pairing test built
    # on a free radius whose count ran 8 → 29 → 49 → 80 over the range; both
    # ends of this rule are transcribed figures, which is what keeps the
    # instrument from being tuned toward the answer it is grading.
    dual_min_m: float
    # The widest thing that may legitimately sit *between* two opposed
    # carriageways.
    #
    # ⚠️ Reported, never refused. A wide residual is ambiguous — a real median,
    # or a centreline this instrument has mis-centred — and refusing on it would
    # delete the second case rather than report it. What it bounds is
    # plausibility, and a distribution that sits above it is a finding about a
    # clause nobody has transcribed.
    median_max_m: float
    # How far off anti-parallel two centrelines may run and still be read as an
    # opposed pair.
    #
    # 🔴 This is the block's only value with no clause behind it, and it is
    # therefore the one that must be swept rather than chosen. `Q72`'s sibling
    # objection is recorded at `DECISIONS.md`'s NO ENTRY entry: a pairing rule
    # built on a free radius ran 8 → 29 → 49 → 80 as that radius went 10 → 30 m
    # and was rejected for it. The search *distance* here is the station's own
    # measured far ray and so has no knob; this angle is what is left, and the
    # published sweep is what says whether it behaves like a bound or like that
    # radius.
    pair_bearing_tolerance_deg: float


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
    # Optional: absent means the tool reports the near-side overhang only, which
    # is the honest answer for a city whose manual nobody has transcribed.
    width_bounds: WidthBounds | None = None
    # How close an independent reading must land to CONFIRM a strip width
    # (`Q128`). `None` leaves the strip unpublished — see `_carriageway_survey`.
    confirm_within_m: float | None = None

    @property
    def area_publisher(self) -> str:
        """The name of the AREA spec, which is what a strip width is published by.

        ⚠️ **Read off the declared specs, never written as a literal.** The
        publisher name reaches `roadgraph.json`'s `width_publisher`, which
        `verify_road_graph.gd` requires to be non-empty for any source that is
        not `authored` or `deck`, and a hard-coded `hyd_pavement` would be a
        second copy of a name hard rule 3 keeps in the city file.
        """
        for edge in self.edges:
            if edge.geometry == CARRIAGEWAY_AREA:
                return edge.name
        return ""

    # Elevation levels the width survey walks. 🔴 **`(0,)` and the default must
    # stay there** — `clearance.walk(levels=...)`'s rule at a second key, and for
    # the same reason: widening it re-publishes `roadgraph.json` for 60 edges, so
    # it is a bundle change and the user's call rather than a tuning knob.
    #
    # ⚠️ **Off-grade, these publishers fail UNSAFELY rather than merely weakly**
    # (`Q103`). Their lines are a 2D plan projection, so a ray cast from a deck
    # centreline finds the kerb of the street *underneath*: they license 5 of 45
    # level-1 edges and 2 of those 5 would publish a width **wider** than the
    # deck, making the overhang worse on the very population a widening exists to
    # fix. Anything that turns this on off-grade owes the deck as its truth side,
    # not these lines.
    levels: tuple[int, ...] = (0,)
    # 🔴 **Lane LINES, read by `tools/width_evidence.py` and by nothing in the
    # build** (`Q127`). Same shape as `edges` — the same publisher, read the same
    # way — and a separate field because a lane line is not a carriageway edge:
    # a survey that cast at one would stop a ray one lane in and publish a lane
    # as a road. Empty means the lane-spacing reading is not taken.
    lane_lines: tuple[CarriagewayEdge, ...] = ()


def _pair(values: list[Any], where: str) -> tuple[float, float]:
    """Two finite, positive, ascending measurements — `_measures` for a pair."""
    try:
        low, high = float(values[0]), float(values[1])
    except (TypeError, ValueError):
        raise ValueError(f"{where} is {values!r}, which is not a pair of numbers") from None
    for value in (low, high):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{where} must be finite and positive, got {value}")
    return low, high


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


# Classes of street in the data contract (the minimap's main roads, 2026-09-24).
# The pipeline owns this vocabulary; which publisher codes fall in which class
# arrives from the city file (hard rule 3).
STREET_MAIN = "main"
STREET_MINOR = "minor"
STREET_CLASSES = (STREET_MAIN, STREET_MINOR)


@dataclass(frozen=True)
class StreetClass(LayerSpec):
    """Which class of street each edge is, from a published street hierarchy.

    ✅ **The hierarchy is PUBLISHED.** Nothing in the road network says a road
    is a main road — its `ROUTE_NUM` numbers the strategic routes only, and
    speed limits and lane counts flag Gloucester Road and the flyovers and miss
    Hennessy — but the topographic map's street centrelines carry a coded type
    beside the same street code, and its domain is in every sheet. So the class
    is joined by KEY (the street code) and disambiguated by PLACE: a code that
    carries two types (Canal Road East, Morrison Hill Road) takes the type of its
    nearest segment to the edge's middle, not the code's majority.

    ⚠️ Read as published, not as a local would rank them: the publisher calls
    Lockhart, Jaffe and Harbour Road secondary, and so does the map.
    """

    # Publisher's type code to a class in `STREET_CLASSES`.
    classes: dict[str, str]
    # How far the nearest same-code segment may lie from an edge's middle and
    # still class it, in metres.
    max_distance_m: float

    def class_of(self, code: str) -> str | None:
        """The contract class of a publisher type code, or None if unmapped."""
        return self.classes.get(code)


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

    # 🔴 **A FLOOR in metres, not a multiplier on `width_m` (`Q95`).** It was a
    # multiplier while every `width_m` was the same invented 6.4 m, and against a
    # *measured* width a multiplier is the wrong shape: it over-widens the
    # streets that are already wide and under-widens the narrowest, where what
    # `docs/GAME_DESIGN.md` actually asks for — "the genre needs wide roads" — is
    # a minimum. A road already wider than this is drawn at its own width.
    #
    # ⚠️ **Set to what the multiplier drew, so the change is inert on an authored
    # width**: 6.4 x 1.6 = 10.24. That is what makes the re-baseline affordable —
    # only a street the survey found wider than the floor moves at all.
    floor_default_m: float
    floor_by_min_speed_limit_kph: dict[int, float]
    # Off-grade carriageway, by elevation level. Both *reasons* for a floor are
    # at-grade reasons, and they are stated where the values are — see the table
    # in `hong_kong.yaml`. `drawn_width_m` explains only why this rule wins
    # outright. A floor of 0.0 means "draw it at its own width".
    floor_by_elevation_level: dict[int, float]
    # `Q23`: the same claim made per *station* rather than per edge. A road does
    # not become a bridge at an edge boundary, so a level-0 edge can spend its
    # first 90 m on a ramp deck and the rest on the street — 1,070 m of the
    # region's level-0 centreline does exactly that. `roads.py` publishes which
    # stations those are; this is what they are drawn at.
    floor_on_structure_m: float
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

    # How far from anti-parallel two one-way ribbons may run and still be read as
    # the two halves of one road, which is what `surface._read_offside` needs to
    # put a centre line between them.
    #
    # 🔴 **Deliberately NOT `carriageway_survey.width_bounds.pair_bearing_tolerance_deg`,
    # which asks the same question with the same number.** That block is
    # `CarriagewaySurvey | None`, so a region that declares no survey would lose
    # its centre lines to a width setting — and the two are read in different
    # frames: that one pairs *published centrelines* off a ray, this one pairs
    # *drawn ribbons* after the widening. Same question, two populations; the
    # value agreeing is a fact about the city, not a shared constant.
    opposed_pair_bearing_deg: float

    # ⚠️ **Named, not authored here.** These two colours are in a different
    # dataclass from the rest of the palette, and that is precisely how they
    # escaped the one exposure change every other colour took (`235aa4f`). They
    # now reference the same `materials:` table as everything else, so a section
    # can no longer be re-exposed without its neighbour — there is only one place
    # left to change. See `_check_reflectance`.
    surface_material: Material
    kerb_material: Material

    def floor_for(
        self, speed_limit_kph: int, *, elevation_level: int, on_structure: bool = False
    ) -> float:
        """Minimum drawn carriageway width for one station, in metres — by level
        if the level has a rule, else by whether that station is on structure,
        else from the fastest matching speed rule.

        Expressways are already drawn wide by their lane count and need less
        help; a two-lane street is where the floor earns its keep.

        The level rule wins outright rather than combining, because the two are
        different kinds of claim. The speed table is a preference about how much
        room a fast road wants; a level rule is a statement about what the
        carriageway is sitting on. `P2-7` put the off-grade ribbon on its
        structure, and a viaduct deck does not get wider because the road on it
        is signed at 70 — it ends at a parapet. A ribbon widened there overhangs
        into the air beside the deck, which is both wrong and, with a guardrail
        drawn beyond it, unreadable. Those rules are a **0.0 m floor**: a deck is
        drawn at its own width, whatever that width turns out to be.

        ⚠️ **The level rule is still checked first, and that ordering is load
        bearing rather than historical.** `on_structure` is a per-station fact
        and the level table is a per-edge one, so letting the station win would
        change what an off-grade edge is drawn at wherever the structure was
        never found — `ISLAND EASTERN CORRIDOR`'s stub, which takes the flat
        offset precisely because nothing is under it, would go back to being
        widened. Checking the level first leaves levels 1 and -1 exactly as
        `P2-7` measured them, so `Q23` moves level 0 and nothing else.

        ⚠️ **That last sentence was aspirational until 2026-09-02**: level -1
        had no rule, so it fell through to `floor_default_m` and 15 tunnel edges
        were drawn at 10.24 / 12.48 m inside their own bores — `e489` kept
        0.25 m clear of a 10.24 m ribbon. The config now carries the rule this
        describes; `hong_kong.yaml` has the measurement, and
        `test_a_tunnel_is_drawn_at_its_authored_width` has the refuted reason it
        replaced.
        """
        if elevation_level in self.floor_by_elevation_level:
            return float(self.floor_by_elevation_level[elevation_level])
        if on_structure:
            return float(self.floor_on_structure_m)
        return float(
            _by_fastest_rule(
                self.floor_by_min_speed_limit_kph, speed_limit_kph, self.floor_default_m
            )
        )

    def drawn_width_m(
        self,
        width_m: float,
        speed_limit_kph: int,
        *,
        elevation_level: int,
        on_structure: bool = False,
    ) -> float:
        """How wide the ribbon is actually drawn: the road, or the floor if wider.

        🔴 **`max`, not a multiplication, and that is `Q95`'s whole point.** A
        multiplier applied to a *measured* width scales the streets that need it
        least; a floor leaves a genuinely wide road alone and lifts only the
        ones too narrow to drive at arcade speeds. On an authored 6.4 m width
        with a 10.24 m floor the two agree exactly, which is what made the
        change reviewable.
        """
        return max(
            float(width_m),
            self.floor_for(
                speed_limit_kph, elevation_level=elevation_level, on_structure=on_structure
            ),
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
    """How the road stage reads the structure class — two questions, not one.

    **Height** is `P2-7`'s: `elevation_levels` gives a level one flat offset,
    which `Q20` measured as |error| p90 4.19 m against the real decks, with the
    ribbon sitting *below* the deck — inside the structure — in 66% of samples.
    The first six values replace that constant with a measurement of what the
    road is built on.

    **Bounding** is `Q19`'s, added 2026-08-30, and it is a different question of
    the same field: is there structure standing *beside* this station, at the
    height a bumper meets. `Q23` suppressed the widening where a road rests
    **on** structure and keyed that on `on_structure` — which `roads.py` defines
    as height *provenance* — so a ramp whose height came from terrain kept the
    full at-grade floor however walled it was, and the Wan Chai Interchange
    approaches were drawn at the 10.24-12.48 m floor over surveyed carriageways
    of 3.84-7.20 m.

    ⚠️ **The two questions must not be merged into one flag.** `on_structure`
    has a published contract that `_descend`, `deck_error.py`, `overhang.py` and
    `touchdown_error.py` all read; widening its meaning would move all four
    without touching them.

    ⚠️ **Two questions and still one class, which review raised and this rejects.**
    `GroundProfile` is the precedent for splitting a second question out, and the
    `bound_*` prefix is doing a namespace's job. But the probe reads
    `slab_gap_m` as well as its own four values — it asks
    `sample_lowest_above` for a slab top, so it needs the same clustering
    constant the height samplers do — and a nested type would either duplicate
    that constant or reach back out to its parent for it. `GroundProfile` shares
    nothing with `DeckSampling`; this shares the one value that decides what
    counts as a structure.

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
    # The steepest a touchdown may be reconstructed at, where the structure
    # stops before the ramp reaches the node (`Q90`). Above it the step is left
    # standing and counted, because a grade no road climbs is evidence that the
    # missing metres are not a ramp.
    touchdown_max_grade_pct: float
    # How far above the sampled structure the carriageway is drawn. Not a fudge
    # factor: a real road is a wearing course laid *on* a structural deck, and
    # this is that layer. It also has to absorb the tile decimation, which is
    # what makes it a measured value rather than a nominal one.
    clearance_m: float

    # `Q19`'s lateral probe. How far either side of the centreline to look for a
    # wall. A fact about the road rather than about how wide we draw it, so it is
    # a declared reach and **not** derived from `surface.floor_*`: the road stage
    # publishes `roadgraph.json` and the surface stage consumes it, and reaching
    # back up that dependency to ask how wide the ribbon will be drawn would
    # invert the two.
    bound_reach_m: float
    # Probe spacing across the carriageway. A resolution constant in the sense
    # `Q51` means, so it is config and sweepable: a parapet top is a few tens of
    # centimetres wide in plan, and a step coarser than it steps over the wall
    # and reports a clear road.
    bound_step_m: float
    # The band above the ribbon a structure top must fall in to bound it, low
    # and high.
    #
    # 🔴 **The low bound is what keeps this off `Q23`'s refusal.** That entry
    # measured a *vertical* question — `overhang.py`'s upward face within a metre
    # below — and concluded **"a street on an abutment is a street"**, leaving
    # 546 m deliberately wide. An abutment the road sits *on* returns a structure
    # top at the ribbon's own height, so anything at or under this bound is that
    # case and is not a wall.
    #
    # ⚠️ **The high bound is what keeps an ordinary street from being narrowed
    # for passing under a flyover.** `sample_lowest_above` returns a slab *top*,
    # so a viaduct overhead answers with its deck at 5 m or more; a parapet
    # answers at 1.5-2.0 m. Widen this past a storey and Gloucester Road narrows
    # under Canal Road Flyover, which would render perfectly.
    bound_low_m: float
    bound_high_m: float


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

    # Which class of street each edge is, for the minimap's main roads. `None`
    # publishes no class, and every road draws alike.
    street_class: StreetClass | None

    def lanes_for(self, speed_limit_kph: int) -> int:
        """Lane count for an edge, from the fastest matching rule.

        **Not a published attribute.** Road Network v2 carries no lane count in
        any layer, so this is authored policy keyed on what the source does
        carry. `P1-4` widens the result for play on top; see `docs/PLAN.md`.

        ⚠️ **No longer the last word** (`Q94`). Nobody publishes a *count*, but
        three sources publish the *width*, and `pipeline/carriageway.py` brackets
        a measured carriageway against TPDM 4.3.9.8's through-lane range. Where
        that resolves, it overrides this; where it does not — rather under half
        the measured edges — this is still what an edge carries. `lanes_source`
        on the edge is what says which.
        """
        return int(
            _by_fastest_rule(self.lanes_by_min_speed_limit_kph, speed_limit_kph, self.lanes_default)
        )


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
        street_class=_street_class_for(body, layers["centrelines"], where),
    )


def _street_class_for(
    body: dict[str, Any], centrelines: SourceLayer, where: str
) -> StreetClass | None:
    """The street-class block, and the centreline role it joins on: required
    only where the block is declared, so a city with no hierarchy names no key."""
    spec = _street_class(body.get("street_class"), f"{where}:street_class")
    if spec is not None and "street_code" not in centrelines.fields:
        raise ValueError(
            f"{where}:street_class joins on the street code, and "
            f"{where}:centrelines:fields declares no street_code"
        )
    return spec


def _street_class(body: Any, where: str) -> StreetClass | None:
    """The optional street-hierarchy block, checked at load."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    classes: dict[str, str] = {}
    raw = _require(body, "classes", where)
    if not isinstance(raw, dict):
        raise ValueError(f"{where}:classes must be a mapping of class to codes, got {raw!r}")
    for name, codes in raw.items():
        if name not in STREET_CLASSES:
            raise ValueError(
                f"{where}:classes has {name!r}, expected one of {', '.join(STREET_CLASSES)}"
            )
        if isinstance(codes, str) or not isinstance(codes, (list, tuple)) or not codes:
            raise ValueError(f"{where}:classes:{name} must be a non-empty list of codes")
        for code in codes:
            if str(code) in classes:
                raise ValueError(f"{where}:classes puts {code!r} in two classes")
            classes[str(code)] = str(name)
    if STREET_MAIN not in classes.values():
        # A hierarchy with no main road draws every road alike, which is the
        # outcome of omitting the block — refused so the difference is a choice.
        raise ValueError(f"{where}:classes names no {STREET_MAIN!r} code")
    distance = float(_require(body, "max_distance_m", where))
    if distance <= 0.0:
        raise ValueError(f"{where}:max_distance_m must be positive, got {distance}")
    return StreetClass(
        **_spec_header(body, where, STREET_CLASS_ROLES),
        classes=classes,
        max_distance_m=distance,
    )


STREET_CLASS_ROLES = ("street_code", "type")


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
    # A touchdown grade of zero admits no descent at all, which is the
    # pre-`Q90` clamp wearing a config key — inert, and inert in the way
    # `_thresholds` exists to refuse.
    # A probe reach or step of zero is degenerate in the same way a spacing is:
    # the first asks about no point off the centreline at all, the second for
    # infinitely many. Both are inert-in-disguise, which is what `_thresholds`
    # refuses. `bound_low_m` is signed because a city may legitimately want the
    # band to open at the ribbon itself.
    values = _thresholds(
        body,
        where,
        positive=(
            "resample_m",
            "slab_gap_m",
            "touchdown_max_grade_pct",
            "bound_reach_m",
            "bound_step_m",
            "bound_high_m",
        ),
        signed=("max_below_terrain_m", "at_grade_m", "clearance_m", "bound_low_m"),
    )
    if values["bound_low_m"] >= values["bound_high_m"]:
        raise ValueError(
            f"{where}: bound_low_m {values['bound_low_m']} must sit below bound_high_m "
            f"{values['bound_high_m']}, or the band admits nothing and Q19's probe is "
            f"inert while reading as configured"
        )
    return DeckSampling(
        resample_m=values["resample_m"],
        slab_gap_m=values["slab_gap_m"],
        max_below_terrain_m=values["max_below_terrain_m"],
        at_grade_m=values["at_grade_m"],
        touchdown_max_grade_pct=values["touchdown_max_grade_pct"],
        clearance_m=values["clearance_m"],
        bound_reach_m=values["bound_reach_m"],
        bound_step_m=values["bound_step_m"],
        bound_low_m=values["bound_low_m"],
        bound_high_m=values["bound_high_m"],
    )


def _road_surface(body: dict[str, Any], where: str, table: _MaterialTable) -> RoadSurface:
    floor_default_m = float(_require(body, "floor_default_m", where))
    floors = {
        int(threshold): float(metres)
        for threshold, metres in (body.get("floor_by_min_speed_limit_kph") or {}).items()
    }
    by_level: dict[int, float] = {}
    for level, metres in (body.get("floor_by_elevation_level") or {}).items():
        # The YAML 1.1 boolean trap `elevation_levels` documents at length, and
        # this table is keyed on the same domain: a bare `on:` key resolves to
        # True, and True == 1 as a dict key, so it lands silently on the level-1
        # rule — the one rule this table currently carries.
        if isinstance(level, bool) or not isinstance(level, int):
            raise ValueError(f"{where}:floor_by_elevation_level key {level!r} is not an integer")
        by_level[level] = float(metres)
    on_structure = float(_require(body, "floor_on_structure_m", where))
    for metres in (floor_default_m, on_structure, *floors.values(), *by_level.values()):
        # 🔴 **Zero is legal and negative is not** (`Q95`). Under the multiplier
        # this guard refused anything below 1.0, because narrowing a road was a
        # typo rather than a choice. A floor has a different bottom: 0.0 means
        # "draw the road at its own width", which is exactly what a viaduct deck
        # and an off-grade carriageway want and what those two rules now say. A
        # *negative* floor is still meaningless — `max` would ignore it — so it
        # is refused rather than silently doing nothing.
        if metres < 0.0:
            raise ValueError(f"{where} carriageway floor {metres} m is below zero")

    bearing = float(_require(body, "opposed_pair_bearing_deg", where))
    if not 0.0 < bearing < 90.0:
        # `width_bounds` refuses its own tolerance at 90 for this reason, and it
        # bites harder here: the search distance is the edge's own drawn width,
        # so at 90 every side street crossing a wide road is inside it and reads
        # as that road's opposed half — a centre line down a street that has one
        # flow. Zero is refused because it admits nothing and the marking then
        # reads as configured while drawing nowhere.
        raise ValueError(f"{where}:opposed_pair_bearing_deg must lie in (0, 90), got {bearing}")

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
        floor_default_m=floor_default_m,
        floor_by_min_speed_limit_kph=floors,
        floor_by_elevation_level=by_level,
        floor_on_structure_m=on_structure,
        structure_taper_m=measures["structure_taper_m"],
        kerb_height_m=measures["kerb_height_m"],
        kerb_width_m=measures["kerb_width_m"],
        junction_trim_factor=measures["junction_trim_factor"],
        junction_trim_max_fraction=fraction,
        opposed_pair_bearing_deg=bearing,
        surface_material=table.get(
            str(_require(body, "surface_material", where)), f"{where}:surface_material"
        ),
        kerb_material=table.get(
            str(_require(body, "kerb_material", where)), f"{where}:kerb_material"
        ),
    )


_CARRIAGEWAY_EDGE_ROLES = ("edge_type",)


@dataclass(frozen=True)
class Carve:
    """Which edges `pipeline/carve.py` cuts road structure back from (`Q19`).

    🔴 **`edges` is a list a person wrote, and that is the point.** `Q19` split
    the blocked population on the licence boundary: the seven edges a publisher
    surveyed a width for are carved, and the four nobody licensed are fenced by
    `P3-29` instead, because carving one would cut published structure to an
    invented width. Deriving this list from `width_source` would quietly carve
    any edge a later source refresh happens to license, which is a decision
    rather than a query.

    🔴 **Keyed by region, because an edge id is an ORDINAL and not an identity.**
    `roads.py` assigns `edge_id = len(pending)`, so a bare list means one thing
    in the region it was written for and something else everywhere else: 7 of the
    8 ids `wan_chai` carries resolve in `mong_kok`, naming six roads — ARGYLE,
    FERRY, HOI WANG, LIBERTY, PITT and WATERLOO.
    Unkeyed, the only thing standing between this list and six silently mis-carved
    Kowloon roads was that the largest id is 788, so all eight resolve only in a
    region of 789 edges or more and `mong_kok` has 537. `wan_chai`'s own 797
    clears that bar, so a region of its size runs clean — both partitions closing,
    `facing_away` 0 and `check.sh` green.

    ⚠️ **A region absent here carves nothing, and that is a measurement rather
    than an omission.** `Q19`'s population came from running
    `carriageway_occupancy` over `wan_chai`; nobody has run it elsewhere, so
    there is no other region whose list is known. 🔴 **Do not "fix" a build by
    skipping ids the graph does not carry** — that turns the loud failure into
    quiet cuts on named streets, which is `Q54` inverted: removing published
    structure on the authority of an id nobody surveyed.

    ⚠️ **Absent, the stage is a no-op and the bundle is byte-identical**
    (`Q95`'s validation move) — which is how a carve is proved to have changed
    only what it claims. A region with no entry takes that same path.
    """

    edges: dict[str, tuple[int, ...]]
    # How finely the ribbon is walked. The prism is rebuilt per station, so this
    # sets how closely the cut follows a ramp's curve; 2 m is half `carriageway`'s
    # own 4 m survey pitch, because a cut that misses a bend leaves concrete.
    station_m: float
    # How far below the carriageway the cut reaches. The blocking mass starts at
    # or just below road level on all seven edges (`Q19`), so a cut that began at
    # the ribbon would leave a lip along the kerb line.
    floor_below_m: float
    # Clear height a structure must leave above the ribbon before it counts as
    # something to pass *under* rather than something in the way. A ramp flank
    # answers below this and is cut away to the sky; a deck answers above it and
    # bounds the cut. ⚠️ Not pinned to the occupancy grader's 0.30-2.00 m bumper
    # band, deliberately: that tool grades the shipped bundle and this decides
    # what to build, so tying them lets the grader agree by construction.
    headroom_m: float
    # How far under a soffit the cut stops, so the deck keeps its own thickness.
    soffit_clearance_m: float

    def edges_for(self, region_id: str) -> tuple[int, ...]:
        """The edges carved in one region, empty where the region declares none.

        ⚠️ **Empty is the answer for an undeclared region, never a lookup
        failure.** A region nobody has measured is not a misconfiguration — it
        is a region whose blocked population is unknown — so it carves nothing
        and the stage no-ops. What *is* refused is a declared region naming an
        edge its graph does not carry, and that refusal lives in `carve.py`
        where the graph is readable.
        """
        return self.edges.get(region_id, ())


def _join(body: Any, where: str) -> Join | None:
    """The optional region-join block (`P5-7c`)."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    return Join(**_thresholds(body, where, positive=("reach_m",), signed=()))


def _carve(body: Any, where: str) -> Carve | None:
    """The optional carve block (`P3-28`).

    An empty `edges` is refused rather than treated as absent, on
    `_carriageway_survey`'s reasoning: a carve declaring no edges would report a
    clean run over nothing, which reads like success. The same applies one level
    down: a region mapped to an empty list says nothing a missing key does not.

    ⚠️ **Whether a named region is DECLARED is checked in
    `_check_carve_regions_are_declared`** and not here, which is the shape every
    other cross-block reference in this file takes: the check needs the built
    `Config`, and threading the raw region names in would make this the one
    block parser that reaches outside its own body.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    by_region = _require(body, "edges", where)
    if not isinstance(by_region, dict):
        # 🔴 Named apart from "empty", because a bare list is the shape this
        # block had before `P5-7` and so is exactly what a stale branch or an
        # older local config carries. A migration that reads "is empty" about
        # eight ids sends the reader looking for the wrong thing.
        raise ValueError(
            f"{where}:edges must be a mapping of region id to edge ids, got "
            f"{by_region!r} — an edge id is a per-region ordinal, so a bare list "
            f"names nothing without the region it was written for"
        )
    if not by_region:
        raise ValueError(f"{where}:edges is empty; leave the block out instead")

    edges: dict[str, tuple[int, ...]] = {}
    for region_id, entries in by_region.items():
        at = f"{where}:edges:{region_id}"
        if not isinstance(entries, list):
            raise ValueError(f"{at} must be a list of edge ids, got {entries!r}")
        if not entries:
            raise ValueError(f"{at} is empty; leave the region out instead")
        ids = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, int) or isinstance(entry, bool):
                raise ValueError(f"{at}[{index}] is {entry!r}, expected an edge id")
            ids.append(int(entry))
        if len(set(ids)) != len(ids):
            # Two prisms over one edge would double every metre it reports.
            raise ValueError(f"{at} repeats an id")
        edges[region_id] = tuple(ids)

    measures = _measures(
        body,
        where,
        ("station_m", "floor_below_m", "headroom_m", "soffit_clearance_m"),
        positive=True,
    )
    return Carve(edges=edges, **measures)


@dataclass(frozen=True)
class Clearance:
    """The bar `P3-29`'s player fence is set at — the car's own width.

    🔴 **This number describes the taxi, not Hong Kong, and it is mirrored
    rather than shared.** It is `taxi.tscn`'s box collider, which the ETL cannot
    read; `tools/ground_clearance.py` documents the same mirror of
    `handling.tres` for the same reason. It lives in the city config because the
    pipeline is what has to measure against it (hard rule 4: a bar is data), and
    the duplication is the price of the ETL never importing the game.

    🔴 **A player fence and a routing bar are two bars.** `roads.lane_width_m`
    (3.20 m) is whether traffic should be *routed* down an edge, which is what
    `Q51` gates on; this is whether the **player** is stuck. Re-pointing
    `RoadGraph.is_passable` at this value would send traffic down `e207`'s
    1.95 m, which is why `Q19` ruled they may never be merged.

    ⚠️ **There is deliberately no vertical companion here, and that is a
    measured refusal rather than an omission.** `Q19` prescribed a step bar
    beside this one — a step over `handling.tres`' 0.18 m suspension travel
    inside the drawn carriageway — and `P3-29` built it, measured it and
    withdrew it: it fences three climbing edges whose ribbon merely disagrees
    with the deck it rests on by ~0.2 m, and it does not catch `e99` FLEMING
    ROAD, the edge it was prescribed for. The 0.18-0.30 m band is not an empty
    gap; it is the band `Q23`'s bumper floor exists to suppress. The
    measurement lives in `tools/ground_clearance.py` instead. See `Q19`.
    """

    # What a station has to keep clear for the player to get through at all.
    car_width_m: float


def _clearance(body: Any, where: str) -> Clearance | None:
    """The optional car-bar block (`P3-29`).

    Through `_thresholds` rather than `_measures`, so the closed-key-set check
    applies: `_carve` above skips it and would silently ignore a spare key,
    which on a block this small is most of the ways to get it wrong. It is also
    what refuses a `suspension_travel_m` re-added here without the argument
    above being re-opened.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    values = _thresholds(body, where, positive=("car_width_m",), signed=())
    return Clearance(**values)


@dataclass(frozen=True)
class CarriagewayRegion:
    """The resolutions `pipeline/region.py` builds R at (`Q129`, `P3-33b`), and
    what `surface.py` makes of it.

    🔴 **The first three are RESOLUTIONS and none is a bound.** What the rails refuse and
    how far they cast are `carriageway_survey.width_bounds`' `hard_min_m` and
    `max_m`, read from that block and never restated here, so the region and the
    ray survey cannot drift onto two bars.
    """

    # Pitch of the Voronoi sites along each centreline. A boundary between two
    # territories is resolved to about half of it.
    sample_m: float
    # Station pitch of the rails cast to the kerb lines where HyD is silent.
    rail_m: float
    # Pitch of the stations a territory's left and right extents are published
    # at, between the published vertices. `surface.py` inserts a ribbon station
    # at each, so this is also the along-road resolution of the drawn kerb.
    station_m: float
    # How far a territory's rail may sit from the straight line between two kept
    # stations before `surface.py` keeps the station between them. The one value
    # here that is NOT a resolution: it trades triangles for kerb fidelity.
    rail_tolerance_m: float
    # The shortest outward bump a ribbon's rail still follows. Anything shorter —
    # a lay-by, a bus bay, the mouth of a road with no centreline — is let go of
    # and drawn as area, so a straight road's lane lines stay straight. AUTHORED:
    # no publisher says how long a bay is.
    rail_opening_m: float
    # The widest gap between two of HyD's Pavement Polygons that is still their
    # SEAM and not a kerb. The publisher tiles the carriageway and its tiles do
    # not always meet; the union is closed by this much before anything reads it.
    seam_m: float


def _carriageway_region(body: Any, where: str) -> CarriagewayRegion | None:
    """The optional region block (`Q129`)."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    return CarriagewayRegion(
        **_thresholds(
            body,
            where,
            positive=(
                "sample_m",
                "rail_m",
                "station_m",
                "rail_tolerance_m",
                "rail_opening_m",
                "seam_m",
            ),
            signed=(),
        )
    )


@dataclass(frozen=True)
class Fence:
    """How `pipeline/fence.py` stands barriers at the mouths it closes (`P3-29`).

    ⚠️ **Both values are authored, and there is no sheet to cite.** Nothing
    published says where a road closure should be — the government draws the
    carriageway, not the works — so what these answer to is the acceptance
    criterion instead: *legible before it is hit at driving speed from every
    approach*.

    ⚠️ **Absent, no barrier is placed and the fenced set is still published**, so
    a build with no dressing is distinguishable from one whose fence found
    nothing to close. `Q19` forbids shipping the first: a refusal the player
    cannot see is the defect the fence exists to fix.
    """

    # How far into the closed street the barrier stands, measured from the node.
    # ⚠️ Not zero: a barrier *on* the node stands in the junction the street is
    # entered from and blocks every other arm of it.
    inset_m: float
    # Width of one standard barrier unit, spanned in a row across the mouth.
    # 🔴 **Must match `tools/make_barrier.py`'s `UNIT_WIDTH_M`**, which is the
    # width the committed prop is actually authored at — a mismatch tiles the
    # row at the wrong pitch and either gaps it or overlaps it, and both render
    # as a barrier. `etl/tests/test_fence.py` binds the two.
    unit_width_m: float
    # Elevation levels whose touchdowns onto the open network are closed
    # (`Q103`). Empty leaves them open, which is the pre-`Q103` behaviour.
    #
    # 🔴 **A SECOND POPULATION, and not a second bar** — `pipeline/fence.py`'s
    # module docstring carries the argument, and `hong_kong.yaml` carries it for
    # whoever sets the value. In short: these edges are closed because nothing
    # *grades* them, never because they are narrow, so they may never join
    # `fenced_edges`.
    #
    # ⚠️ **Level 0 is refused rather than ignored.** It names the open network
    # itself, so admitting it would fence every junction in the region — the
    # one value here whose mistake is catastrophic rather than inert.
    touchdown_levels: tuple[int, ...]


def _fence(body: Any, where: str) -> Fence | None:
    """The optional barrier-placement block (`P3-29`, `Q103`)."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    # Lifted out before `_thresholds`, which is a closed key set over *measures*
    # and would refuse a list. The closure still holds: anything else unknown
    # reaches `_thresholds` and is rejected there.
    levels = _touchdown_levels(body.get("touchdown_levels"), f"{where}:touchdown_levels")
    measures = {key: value for key, value in body.items() if key != "touchdown_levels"}
    values = _thresholds(measures, where, positive=("inset_m", "unit_width_m"), signed=())
    return Fence(touchdown_levels=levels, **values)


def _elevation_level_int(value: Any, where: str, index: int) -> int:
    """One entry of a levels list, with the trap that makes the guard necessary.

    🔴 **Not pedantry — it is `_elevation_levels`' YAML 1.1 trap at the two
    keys that name levels in a list.** PyYAML resolves bare `on`/`yes` to
    `True`, and `bool` subclasses `int`, so `[on]` passes a plain
    `isinstance(value, int)` and silently names level **1**, a real level in
    this city. ⚠️ Not `_measures`' trap: that one calls `float()`, which takes a
    bool without complaint, so it is no precedent for this.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{where}[{index}] is not an integer, got {value!r}")
    return value


def _touchdown_levels(body: Any, where: str) -> tuple[int, ...]:
    """Which off-grade levels get their touchdowns closed (`Q103`).

    Absent is the pre-`Q103` state — nothing off-grade is closed — rather than a
    default, because closing a touchdown is a decision about what the slice
    ships and not a threshold to tune.
    """
    if body is None:
        return ()
    if not isinstance(body, list):
        raise ValueError(f"{where} must be a list of elevation levels, got {body!r}")
    if not body:
        # An empty list reads as "close nothing" and so does an absent key;
        # two spellings of one state is one of them meaning nothing.
        raise ValueError(f"{where} is empty; leave the key out instead")

    levels: list[int] = []
    for index, value in enumerate(body):
        value = _elevation_level_int(value, where, index)
        if value == 0:
            raise ValueError(
                f"{where} names level 0, which is the open network itself — "
                "closing its touchdowns would fence every junction in the region"
            )
        if value in levels:
            raise ValueError(f"{where} names level {value} twice")
        levels.append(value)
    return tuple(sorted(levels))


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
    # 🔴 **A closed key set, added at `Q128` with the first key a BUILD reads.**
    # Until then every key here fed a tool, so a typo cost a report; now an
    # unrecognised key would silently leave the strip confirmation at its
    # default and publish a different city with every counter closing. The
    # `clearance:` block is refused the same way and for the same reason.
    unknown = set(body) - {"edges", "lane_lines", "width_bounds", "levels", "confirm_within_m"}
    if unknown:
        raise ValueError(f"{where} has unknown keys: {', '.join(sorted(unknown))}")
    levels = body.get("levels")
    return CarriagewaySurvey(
        edges=edges,
        lane_lines=_lane_lines(body.get("lane_lines"), f"{where}:lane_lines"),
        width_bounds=_width_bounds(body.get("width_bounds"), f"{where}:width_bounds"),
        # ⚠️ **Absent means the strip reading does not publish**, rather than
        # publishing at some default tolerance: `Q127` swept it at 0.5 / 1.0 /
        # 2.0 m and read 0.75 / 1.23 / 1.58 m at 11 / 22 / 35% reach — a trade
        # curve and not a plateau, so it is a value a city chooses and never a
        # constant this module picks on its behalf.
        confirm_within_m=(
            None
            if body.get("confirm_within_m") is None
            else _measures(body, where, ("confirm_within_m",), positive=True)["confirm_within_m"]
        ),
        # ⚠️ Absent keeps `(0,)`, which is the shipped bundle. An explicit empty
        # list is refused rather than read as "walk nothing": a survey that walks
        # no edge reports total coverage of nothing, which reads as agreement —
        # the same trap `edges` is refused empty for, two fields up.
        levels=(0,) if levels is None else _survey_levels(levels, f"{where}:levels"),
    )


def _lane_lines(body: Any, where: str) -> tuple[CarriagewayEdge, ...]:
    """The optional lane-line layers a width grader reads (`Q127`).

    ⚠️ **Lines only.** An `area` entry loads as an edge-shaped spec and every
    cast at it would stop at a polygon seam — a lane "width" that is HyD's
    tiling — so it is refused here rather than filtered where it is read.
    """
    if body is None:
        return ()
    if not isinstance(body, list):
        raise ValueError(f"{where} must be a list of layer entries, got {body!r}")
    if not body:
        # The `edges` trap: a reading over no layer reports no lane anywhere,
        # which reads as a city with no lane lines.
        raise ValueError(f"{where} is empty; leave the key out instead")
    entries = tuple(
        _carriageway_edge(entry, f"{where}[{index}]") for index, entry in enumerate(body)
    )
    for index, entry in enumerate(entries):
        if entry.geometry != CARRIAGEWAY_LINE:
            raise ValueError(
                f"{where}[{index}]:geometry is {entry.geometry!r}; a lane line is a line"
            )
    names = [entry.name for entry in entries]
    if len(set(names)) != len(names):
        raise ValueError(f"{where} has repeated names ({', '.join(sorted(names))})")
    return entries


def _survey_levels(body: Any, where: str) -> tuple[int, ...]:
    """Which elevation levels the width survey walks (`Q103`)."""
    if not isinstance(body, list):
        raise ValueError(f"{where} must be a list of elevation levels, got {body!r}")
    if not body:
        raise ValueError(f"{where} is empty; leave the key out to walk level 0")

    levels: list[int] = []
    for index, value in enumerate(body):
        value = _elevation_level_int(value, where, index)
        if value in levels:
            raise ValueError(f"{where} names level {value} twice")
        levels.append(value)
    return tuple(sorted(levels))


def _width_bounds(body: Any, where: str) -> WidthBounds | None:
    """The design manual's carriageway bounds (`Q95`).

    Checked at load for `_carriageway_survey`'s reason, and with one bound the
    others do not have: the three metre figures must be *ordered*. An inverted
    pair loads cleanly and produces a report in which every station is refused,
    or none is — both of which read as a finding about the city.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    # ⚠️ **Through `_measures` rather than an inline `float(_require(...))`
    # block**, for the reason `_measures` records: YAML 1.1 resolves `.nan` and
    # `.inf`, and a NaN passes every sign test below while making false every
    # comparison it feeds. The ordering guard would catch a NaN by accident;
    # `.inf` in `max_m` it would not.
    # ⚠️ The angle rides in the same tuple as the metres. `_measures` is
    # unit-agnostic and `_roadmarks` reads `bearing_tolerance_deg` beside
    # `host_radius_m` and `station_m` for exactly this reason.
    values = _measures(
        body,
        where,
        (
            "max_m",
            "min_m",
            "hard_min_m",
            "dual_max_m",
            "dual_min_m",
            "median_max_m",
            "pair_bearing_tolerance_deg",
        ),
        positive=True,
    )
    max_m, min_m, hard_min_m = values["max_m"], values["min_m"], values["hard_min_m"]
    dual_max_m, median_max_m = values["dual_max_m"], values["median_max_m"]
    dual_min_m = values["dual_min_m"]
    tolerance_deg = values["pair_bearing_tolerance_deg"]

    lane = _require(body, "lane_m", where)
    if not (isinstance(lane, list) and len(lane) == 2):
        raise ValueError(f"{where}:lane_m must be a [narrowest, widest] pair, got {lane!r}")
    # The same finiteness rule, applied by hand because `_measures` reads named
    # keys and this one is a pair. `lane_m: [3.0, .inf]` otherwise loads
    # cleanly and gives `lane_bracket` a zero lower bound against a real upper
    # one — an inverted bracket, published with no error.
    lane_m = _pair(lane, f"{where}:lane_m")

    if not 0.0 < hard_min_m < min_m < max_m:
        raise ValueError(
            f"{where} must satisfy 0 < hard_min_m < min_m < max_m, "
            f"got {hard_min_m} / {min_m} / {max_m}"
        )
    if not lane_m[0] < lane_m[1]:
        raise ValueError(f"{where}:lane_m must be ascending and positive, got {lane_m}")
    if lane_m[0] > hard_min_m:
        # The hard refusal is "narrower than one through lane". A `lane_m` floor
        # above it would make the two disagree about what one lane is, and the
        # published bracket would start at zero lanes for a kept reading.
        raise ValueError(
            f"{where}:lane_m starts at {lane_m[0]} m, above hard_min_m {hard_min_m} m — "
            "a kept width would then bracket to no lanes at all"
        )

    # One carriageway of a pair is part of a span, so its ceiling must sit under
    # the span's. Equal or above, the decomposed half is bounded by nothing the
    # whole was not already bounded by, and the tighter dual column — the entire
    # reason for reading a second column — stops applying.
    if not hard_min_m < dual_max_m < max_m:
        raise ValueError(
            f"{where} must satisfy hard_min_m < dual_max_m < max_m, "
            f"got {hard_min_m} / {dual_max_m} / {max_m}"
        )
    # The two ends of one column, and the crossing rule reads them as a pair of
    # brackets around an undecided band. At or below `hard_min_m` the band is
    # empty and every span is read as uncrossed; at or above `dual_max_m` the
    # narrowest carriageway of a pair would be wider than the widest, and no
    # span could be read as crossed at all. Either way one of the three states
    # becomes unreachable, which is a rule that has stopped classifying while
    # still printing a table.
    if not hard_min_m < dual_min_m < dual_max_m:
        raise ValueError(
            f"{where} must satisfy hard_min_m < dual_min_m < dual_max_m, "
            f"got {hard_min_m} / {dual_min_m} / {dual_max_m}"
        )
    # A separator is what is left of a span after both carriageways, so a bound
    # at or above the span's own ceiling bounds nothing. ⚠️ Deliberately NOT the
    # stronger `2 * hard_min_m + median_max_m <= max_m`: that would tie a
    # reported-only figure to two refusing ones, and `median_max_m` is reported
    # precisely because a wide residual is ambiguous.
    if not median_max_m < max_m:
        raise ValueError(
            f"{where}:median_max_m is {median_max_m} m, at or above max_m {max_m} m — "
            "a separator cannot be wider than the span that contains it"
        )
    if tolerance_deg >= 90.0:
        # At 90 a *perpendicular* centreline reads as opposed, so a side street
        # meeting a main road becomes its own carriageway's partner — which is
        # exactly the match this bar exists to refuse. `_roadmarks` refuses its
        # own tolerance at 90 for the mirror-image reason.
        raise ValueError(
            f"{where}:pair_bearing_tolerance_deg is {tolerance_deg}; at 90 or more a "
            "perpendicular centreline reads as an opposed carriageway, which is what it "
            "exists to refuse"
        )
    return WidthBounds(
        max_m=max_m,
        min_m=min_m,
        hard_min_m=hard_min_m,
        lane_m=lane_m,
        dual_max_m=dual_max_m,
        dual_min_m=dual_min_m,
        median_max_m=median_max_m,
        pair_bearing_tolerance_deg=tolerance_deg,
    )


def _carriageway_edge(body: Any, where: str) -> CarriagewayEdge:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    codes = tuple(str(code) for code in _require(body, "codes", where))
    if not codes:
        raise ValueError(f"{where}:codes is empty; the source would match no feature")

    header = _spec_header(body, where, _CARRIAGEWAY_EDGE_ROLES)
    layer = header["layer"]
    off_grade = tuple(str(code) for code in (body.get("off_grade_codes") or ()))
    if off_grade and "elevation" not in layer.fields:
        # It would load, filter nothing, and report a level-0 figure computed
        # over the flyovers too — the silently-inert block `_sampling_block`
        # refuses for the same reason.
        raise ValueError(
            f"{where}:off_grade_codes lists {', '.join(off_grade)} but fields has no "
            "'elevation' role to read them from"
        )

    geometry = str(body.get("geometry", CARRIAGEWAY_LINE))
    if geometry not in CARRIAGEWAY_GEOMETRIES:
        allowed = ", ".join(sorted(CARRIAGEWAY_GEOMETRIES))
        raise ValueError(f"{where}:geometry is {geometry!r}, not one of {allowed}")
    return CarriagewayEdge(
        name=str(_require(body, "name", where)),
        **header,
        codes=codes,
        off_grade_codes=off_grade,
        geometry=geometry,
    )
