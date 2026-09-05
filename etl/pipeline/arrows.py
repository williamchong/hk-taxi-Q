"""Published turn arrows, drawn as their own mesh (`P3-15`, closes `Q53`'s arrow half).

`Q53` held arrows out of `P3-12` because "there is no marking data in any
source". `Q57` retired that reason on 2026-08-20 — it reasoned about Road
Network v2, the *semantic* dataset, and concluded about the whole estate — and
what was left was a **cost and registration** argument. This is that work.

Three things make this stage different from the ribbon markings beside it, and
each one is why it is a separate mesh rather than another field in
`surface.py`'s codec:

- **`TEXCOORD_1.x` has no room and the wrong shape.** It is a per-edge constant
  with three spare bits; an arrow is a *point* feature, which is `Q54`'s V-range
  problem, and `COLOR_0.a` — the channel that solved it for the kerbside — is
  spent on the kerbside extent.
- **The junction fade blanks exactly where arrows live.** `road_markings.tres`
  fades the last `fade_m` = 6 m of every edge, priced against the 4.21 m
  worst-case cap overlap, and already leaves 121 of 797 edges with no marking at
  all. An approach arrow drawn on the ribbon would fade out at the junction it
  is about.
- **The cap overlap is still there.** `Q53`: "anything drawn *on* a cap
  re-exposes it immediately." Separate geometry lifted above both cap and arm is
  immune, the same way `ART_DESIGN.md` says a world-space box junction is.

⚠️ **The published position is read as a fraction across the road, never as a
position** — `Q54`'s "use it as data, not as geometry", the pattern that let the
kerbside join survive the same 1.6x widening. The alternative, drawing at the
published easting and northing, was measured and is defensible: 97.2% of the
region's symbols already fall inside the drawn ribbon, because the ribbon is
*wider* than the real carriageway and concentric with it. It is not what ships,
because an arrow at its true offset sits about a metre off the drawn lane's
centre and reads as a rendering fault against the lane dividers `P3-12` draws,
while a lane-registered arrow is wrong only about something no driver navigates
by. `Q58`'s refusal of lane space does **not** transfer: a tram rail sits a
measured p50 3.26 m *past* the drawn kerb, off the surface entirely, so lane
space would have invented its position. This is the opposite case.

⚠️ **Nothing here rotates an arrow.** A symbol whose bearing disagrees with its
edge has matched the wrong edge and is refused; turning it to agree would be an
invented marking in `Q54`'s sense, and it would render perfectly.

🔴 **Since `P5-4` (`Q115`) `arrows.glb` is a LIBRARY — one mesh per `RM` code,
drawn flat at the origin with its nose north — and the city is
`arrows_placements.json`**: one stand per drawn arrow carrying its position,
its heading as the compass `rot_y_deg`, and a **`pitch_deg`** between the deck
heights under its tail and its nose, so a rigid glyph reproduces the arrow laid
along its grade. The lane snap, every refusal and every counter stay here; only
the output form changed, from triangles to a transform. ⚠️ **The glyph is
rigid, where the merged build sheared it** — the old draw kept every vertex at
its plan position and interpolated the height along the shaft, which is not a
rotation and has no transform. On the region's grades the two differ by
millimetres (measured at the build, `Q115`), and the rigid form is the more
faithful one: TD's `LENGTH` is the length painted *on* the road, not its plan
projection.
"""

from __future__ import annotations

import argparse
import itertools
import logging
import math
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import numpy as np

from pipeline import gdb
from pipeline.config import (
    ARROW_AHEAD,
    ARROW_LEFT,
    ARROW_RIGHT,
    ArrowGlyph,
    Arrows,
    Config,
    GameTransform,
    load_config,
)
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData
from pipeline.meshbuild import FlatBuilder
from pipeline.placements import Placement, pitch_between, placement, stand_library, stood
from pipeline.polyline import (
    Segments,
    Snap,
    axis_residual_deg,
    directed_residual_deg,
    frame,
    game_heading_deg,
    plan_lengths,
)
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, downward_facing

log = logging.getLogger(__name__)

ARROWS_NAME = "arrows.glb"
ARROWS_MANIFEST_NAME = "arrows.json"
# 2 since `P5-4` (`Q115`): `arrows.glb` is a LIBRARY — one mesh per `RM` code,
# flat at the origin, nose north — and the arrows stand where
# `arrows_placements.json` puts them, pitched to their grade. `triangles`,
# `vertices` and `aabb` still describe what is DRAWN, so a reader comparing them
# to the merged build reads the same numbers; `library_*`, `placements`,
# `placements_document` and `pitch_deg` are new. A v1 reader publishing a
# `city.json` with no `arrows_placements` would ship a library and stand nothing
# on it.
ARROWS_MANIFEST_SCHEMA = 2
ARROWS_PLACEMENTS_NAME = "arrows_placements.json"


def glyph_mesh_name(code: str) -> str:
    """The library mesh drawn for one publisher code: `RM1017`.

    ⚠️ **No `-col` suffix.** Paint is not a collider. The same reasoning
    `TRAMWAY_MESH_NAME` records, with less room for doubt: a 15 mm step of paint
    modelled as collision geometry is a kerb across every lane in the city.
    Per code rather than per movement set because the code is what the
    publisher wrote and what an artist replacing a glyph would look up — the
    4 m and 6 m variants of one marking are two codes and two meshes.
    """
    return f"RM{code}"


# glTF material name, the contract channel `SURFACE_MATERIAL` and
# `TRAMWAY_MATERIAL` use: `tools/generated_scene_import.gd` maps this string onto
# `tuning/arrows.tres` and nothing else.
ARROWS_MATERIAL = "arrows"

# What `ELEVATION` says when a symbol is at grade. The column is a structure
# identifier — `A01`, `A03` — and null is the ground. 1,328 of the region's 1,365
# symbols are null; the rest are on flyovers this region does not open to
# driving (`Q13`).
#
# ⚠️ Not config. It is the source's own encoding of "no structure", not a
# threshold anyone may tune, and a city whose publisher spells it differently
# needs a reader change rather than a number.
_AT_GRADE = ("", "none", "null", "<na>")


@dataclass
class ArrowReport:
    """What the stage read, matched and drew.

    ⚠️ **The counters are what can see this stage fail, because none of its
    failures look like anything in a frame** — `Q58`'s lesson, which cost three
    defects that each rendered as *nothing*. An arrow on the wrong street is a
    perfectly drawn arrow. An arrow turned 180 degrees is a perfectly drawn
    arrow. A glyph table off by one code paints turn-left everywhere and renders
    beautifully.

    The partitions:

        symbols == not_a_turn_arrow + on_structure + empty_geometry + candidates
        candidates == drawn + too_far + off_bearing + against_one_way + no_lane
    """

    symbols: int = 0
    not_a_turn_arrow: int = 0
    on_structure: int = 0
    empty_geometry: int = 0
    candidates: int = 0

    drawn: int = 0
    too_far: int = 0
    off_bearing: int = 0
    against_one_way: int = 0
    no_lane: int = 0

    # Drawn arrows by movement set, keyed by the joined movement names. Publishes
    # the glyph table's effect rather than the table: a mapping that silently
    # stopped matching shows up here as a code that draws nothing.
    by_glyph: dict[str, int] = field(default_factory=dict)

    # ⚠️ **The axis residual is folded modulo 180 and the facing residual is
    # not, and they answer different questions.** Alignment to the road *axis*
    # is what catches a match to the wrong edge — a symbol lying square across
    # its host. Which way along the axis it points is legitimately either way on
    # a two-way street, so it is reported and never refused.
    axis_residual_deg: list[float] = field(default_factory=list)
    # How far each symbol that found a host sat from its centreline. Recorded
    # beside the residual and for the same reason: it is what `max_offset_m` is
    # set against, and a config comment quoting a number nothing re-derives is
    # the debt `Q37` was opened about.
    offset_m: list[float] = field(default_factory=list)
    drawn_on_two_way: int = 0
    # Arrows drawn where the published offset puts them outside the ribbon that
    # was actually drawn. Not a refusal — the drawn ribbon is floored to
    # `surface.floor_default_m` and still misses, which is `Q19`'s open question,
    # not this stage's — but it is the number that says how much of the
    # registration is being carried by the clamp rather than by the source.
    #
    # ⚠️ **A floor since `Q95`, not the 1.6x multiplier this said until `Q96`.**
    # `drawn = max(width_m, floor)`, so this is a strict subset of
    # `outside_carriageway` below rather than a different slice.
    outside_drawn_ribbon: int = 0
    # 🔴 **Arrows whose published offset falls outside the carriageway the
    # publishers MEASURED, so the fraction clamped and the lane came from the bar
    # rather than from the source (`Q96`).** `outside_drawn_ribbon` above asks
    # the same question of the ribbon `surface.py` drew, which is floored to
    # `surface.floor_default_m` and therefore answers a different one.
    #
    # It is the detector this stage was missing. Reading the offset against
    # `lanes x lane_width_m` clamped constantly and silently, and no counter
    # published here could see it.
    #
    # ⚠️ **Reachable in both directions**, which is the test `Q72` says a counter
    # has to pass: it fires where a measured width and an authored lane count
    # contradict each other — `e309` is 6.52 m wide with three lanes authored —
    # and reads 0 where every arrow sits inside its own carriageway. A finding to
    # go and look at, never a bar to retune.
    outside_carriageway: int = 0

    # How far each arrow moved sideways to reach its lane's centre. The residue
    # of the registration decision at the top of this module, published so the
    # decision can be re-argued against a number.
    lane_shift_m: list[float] = field(default_factory=list)
    # Symbols whose along-edge position fell inside a junction trim, so they sit
    # over a cap rather than over a drawn arm. Drawn anyway — the cap is still
    # carriageway — but counted, because it is where the ribbon has no lane
    # coordinate and the count is the only sign of it.
    over_a_cap: int = 0

    # 🔴 **Drawn arrows that landed on top of another one, and the counter this
    # stage did not have (`Q94`).** The lane registration snaps a published
    # offset to one of `ribbon.lanes` slots, and `roadgraph.json`'s lane count
    # was *invented* — derived from the speed-limit table because
    # `DATA_SOURCES.md` recorded no source for it.
    #
    # ⚠️ **Half retired, and the figure that stood here was stale.** It read "720
    # of the region's edges carry the same 6.4 m"; `Q95` measured the width and
    # `Q94` the count, so it is **414** of 737 at 6.4 m today, with `lanes`
    # sourced on 210. The mechanism below is unchanged and so is the counter.
    #
    # Where the real carriageway is wider than the graph says, two symbols with
    # **different instructions** collapse into one slot and draw a shaft wearing
    # both branches: an instruction the world does not contain, reported from the
    # driving seat on STEWART ROAD.
    #
    # ⚠️ **Pairs, not arrows**, because a triple would otherwise be read as
    # three separate faults. `stacked_disagreeing` is the load-bearing half:
    # two `ahead` arrows in one lane are a duplicate, an `ahead` and a `right`
    # are a contradiction.
    #
    # ⚠️ **Reachable at zero** — a graph with the right lane counts scores 0 —
    # so this is a finding to go and look at, never a bar to retune.
    stacked_pairs: int = 0
    stacked_disagreeing: int = 0

    # 🔴 **The lane count the arrows themselves state, per edge (`Q94`), and
    # the only reading of one in this bundle that owes nothing to a width.**
    # A row of turn arrows *across* a carriageway is the count written down by
    # the publisher — `e505` STEWART ROAD carries left | left-or-right | right
    # at one station — so where `roadgraph.json` derives `lanes` from a
    # measured carriageway, this is what can grade it. Two publishers of kerb
    # lines against one publisher of marking symbols; nothing is shared.
    #
    # ⚠️ **Sparser than the graph, so it is a grader and never a source.** Only
    # the edges that carry arrows appear here, and an edge whose arrows all sit
    # in one lane implies 1 rather than "no answer". A count derived from these
    # and then graded against them would be `Q72`'s tautology.
    #
    # ⚠️ **`edges_implying_more_lanes` is one-sided on purpose.** An edge whose
    # graph count *exceeds* the row is not evidence of anything — a three-lane
    # approach may be painted with one arrow — where a row wider than the graph
    # is a lane the graph does not have.
    implied_lanes: dict[int, int] = field(default_factory=dict)
    # 🔴 **The two independent readings of the lane row, diffed (`Q94`).**
    # `pipeline/carriageway.py` clusters the same published symbols at the roads
    # stage, because it needs the count before a ribbon exists and cannot import
    # this module — `arrows` imports `roads`, `roads` imports `carriageway`. So
    # the region carries two implementations of one measurement, which is the
    # arrangement `carriageway_margin.py` is already in, and this is what grades
    # it: on every edge whose count that stage published from a row, the graph's
    # `lanes` **is** the row it read, so anything but 0 means the two clusterings
    # diverged.
    # ⚠️ **It cannot be graded over all 306 arrow-carrying edges**, only the ones
    # published from a row, because that stage refuses a row this one keeps — a
    # single arrow, a row outside its bracket — and those disagree by design.
    lanes_row_disagreement: int = 0
    lanes_row_published: int = 0
    edges_implying_more_lanes: int = 0

    # `SYMBOL_SIZE` as published, which nothing here reads. Recorded so the
    # question "is it the arrow's length in metres?" can be answered from a
    # shipped artefact rather than from a scratch script — `Q37`'s debt.
    symbol_size: list[float] = field(default_factory=list)

    # Triangles wound so they face the ground. Published because inverted paint
    # is *invisible* rather than wrong-looking: `cull_back` drew none of the
    # first tramway, 5,111 triangles of 5,112, with everything else correct.
    inverted: int = 0
    inverted_area_m2: float = 0.0
    # What is DRAWN: the library under every stand (`P5-4`), so these read the
    # same as the merged build they replaced. The library's own size is
    # `library_*`; `placements` counts entries in `arrows_placements.json`, and
    # `placements_refused` the stands whose glyph collapsed to nothing — part of
    # the partition `placements + placements_refused == drawn`, and 0 today.
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)
    placements: int = 0
    placements_refused: int = 0
    library_meshes: int = 0
    library_triangles: int = 0
    library_vertices: int = 0
    # The grade each drawn arrow lies on, unsigned, in degrees — the tilt its
    # stand carries between the deck under its tail and under its nose. A tail
    # here is the finding: a 4 m glyph pitched past what any street climbs has
    # taken one end's height from a different edge, which is the defect
    # `Ribbon.height_m` exists to prevent, and a frame shows it as an arrow
    # standing on its nose. Recorded over what is drawn, so its `n` is `drawn`.
    pitch_deg: list[float] = field(default_factory=list)

    @staticmethod
    def measured(values: list[float]) -> dict[str, float]:
        """One distribution as the manifest publishes it.

        p90 and p99 rather than `TramwayReport.measured`'s p10/p50/p90: every
        distribution here is a residual whose *tail* is the finding, and a
        median residual near zero says nothing about the arrow on the wrong
        street.
        """
        if not values:
            return {}
        points = np.percentile(np.asarray(values), (50, 90, 99, 100))
        return {
            "p50": round(float(points[0]), 4),
            "p90": round(float(points[1]), 4),
            "p99": round(float(points[2]), 4),
            "max": round(float(points[3]), 4),
            "n": len(values),
        }


@dataclass(frozen=True)
class Symbol:
    """One published marking symbol, in game plan space."""

    code: str
    x: float
    z: float
    # Game heading in degrees clockwise from north (`-Z`).
    #
    # ⚠️ **Converted on the way in, once.** `ANGLE` is a mathematical angle —
    # counter-clockwise from east — and `(90 - ANGLE) mod 360` is the game
    # heading. Measured on the 314 `RM1017` straight-ahead symbols within 4 m of
    # a level-0 centreline: this reading lands **p50 0.9 deg** from the host
    # edge's own heading against 52.0 for the raw value and 38.0 for `ANGLE + 90`.
    # `hong_kong.yaml` carries the table; `tests/test_arrows.py` asserts it
    # against the heading `fares.Snap` publishes, which is `surface.mitres`'s
    # own frame, rather than against this comment.
    heading_deg: float


def read_symbols(
    city: Config,
    spec: Arrows,
    region_id: str,
    transform: GameTransform,
    report: ArrowReport,
    *,
    sources_root: Path | None,
) -> list[Symbol]:
    """Every published turn-arrow symbol in the region, in game plan space.

    Everything refused here is refused on what the *publisher* says — a code
    outside the glyph table, a symbol on a structure, an empty geometry — and
    each refusal is counted rather than logged, because the counts are what
    `Q58` says has to be able to see this stage fail.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    symbols: list[Symbol] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("code"))
        bearings = layer.column(spec.layer.field("bearing"))
        levels = layer.column(spec.layer.field("level"))
        sizes = layer.column(spec.layer.field("size"))
        owners, plan = gdb.points(layer)
        if len(owners) == 0:
            continue
        game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])

        for row, owner in enumerate(owners):
            report.symbols += 1
            code = str(codes[owner])
            if code not in spec.glyphs:
                report.not_a_turn_arrow += 1
                continue
            if str(levels[owner]).strip().lower() not in _AT_GRADE:
                # On a flyover. `Q13` keeps the elevated network closed to
                # driving, so its paint is unreachable, and the nearest level-0
                # edge to a symbol on a deck is the street underneath it.
                report.on_structure += 1
                continue
            x, z, bearing = float(game_x[row]), float(game_z[row]), float(bearings[owner])
            if not (math.isfinite(x) and math.isfinite(z) and math.isfinite(bearing)):
                # `POINT EMPTY` is spelled NaN in WKB and `gdb.points` passes it
                # through by design. Refused here, where the meaning is known.
                report.empty_geometry += 1
                continue
            report.candidates += 1
            size = float(sizes[owner]) if sizes[owner] is not None else float("nan")
            if math.isfinite(size):
                report.symbol_size.append(size)
            symbols.append(Symbol(code=code, x=x, z=z, heading_deg=game_heading_deg(bearing)))
    return symbols


# --------------------------------------------------------------------------
# The glyph
# --------------------------------------------------------------------------

_SIDES = {ARROW_LEFT: -1.0, ARROW_RIGHT: 1.0}


def glyph_polygons(spec: Arrows, movements: tuple[str, ...], length_m: float) -> list[np.ndarray]:
    """One arrow as convex polygons in its own frame, `(u, v)` in metres.

    `+v` is the way the arrow points and `+u` is to its right; the origin is the
    symbol's own published point.

    ⚠️ **The origin is taken to be the glyph's centre, and that is an
    assumption.** The publisher gives an insertion point and a `LENGTH` and does
    not say which end the point is. Centre is the least-wrong reading: if the
    convention is really the tail, an arrow is out by half its length along the
    road it is already on, which no driver navigates by — and anchoring at the
    tail when the truth is the centre is out by twice as much. It is recorded
    here because nothing downstream can detect it.

    Every polygon is wound counter-clockwise in `(u, v)`. `_place` maps that
    frame into the world with a **negative determinant**, so counter-clockwise
    here is clockwise in the `(x, z)` plane, which is what faces `+Y`.
    `ArrowReport.inverted` is what actually holds that end.

    🔴 **The proportions are TD's, measured, since `Q93`.** `CT174/51-5(1)F`
    publishes `LENGTH` for these codes and nothing else, so the shape can only
    come from the pictogram; read off it at 700 dpi, every authored figure was
    wrong, and one of them was a defect rather than a difference. See
    `config.Arrows` for the table and for what the straight-arm model still does
    not reproduce.
    """
    head_length = spec.head_length_frac * length_m
    head_width = spec.head_width_frac * length_m
    nose_width = spec.stem_width_nose_frac * length_m
    tail_width = spec.stem_width_tail_frac * length_m
    reach = spec.branch_reach_frac * length_m
    branch_length = spec.branch_head_length_frac * length_m
    branch_width = spec.branch_head_width_frac * length_m
    tip = 0.5 * length_m

    polygons: list[np.ndarray] = []
    if ARROW_AHEAD in movements:
        stem_top = tip - head_length
        polygons.append(
            ccw([(0.0, tip), (-0.5 * head_width, stem_top), (0.5 * head_width, stem_top)])
        )
        # Measured on `RM1027` rather than derived from the head, which is what
        # it used to be: the drawing places the branch 0.145 of a length below
        # the ahead head's base, and tying the two meant a change to the head
        # silently moved the branch.
        elbow = stem_top - spec.branch_drop_frac * length_m
    else:
        # No ahead head, so the branch sits at the nose and the stem runs to it.
        stem_top = tip - 0.5 * branch_width
        elbow = stem_top

    polygons.append(
        ccw(
            [
                (-0.5 * tail_width, -tip),
                (0.5 * tail_width, -tip),
                (0.5 * nose_width, stem_top),
                (-0.5 * nose_width, stem_top),
            ]
        )
    )

    # The stem's own width where the branch leaves it, so the arm is as thick as
    # the shaft it grows out of. `np.interp` clamps, which is what keeps a glyph
    # whose branch sits above `stem_top` from extrapolating past `nose_width`.
    arm_width = float(np.interp(elbow, (-tip, stem_top), (tail_width, nose_width)))
    for movement in movements:
        side = _SIDES.get(movement)
        if side is None:
            continue
        # 🔴 **`branch_length`, never `head_length`.** Reusing the ahead head's
        # length here made this negative — a reach of 0.28 against a head of
        # 0.325 — so the turn head's base landed on the *far* side of the stem
        # and swallowed it on 416 of 747 arrows. `config.py` refuses a city
        # where `branch_reach_frac` does not exceed `branch_head_length_frac`,
        # because a comment did not stop it once already.
        shoulder = side * (reach - branch_length)
        polygons.append(
            ccw(
                [
                    (0.0, elbow - 0.5 * arm_width),
                    (shoulder, elbow - 0.5 * arm_width),
                    (shoulder, elbow + 0.5 * arm_width),
                    (0.0, elbow + 0.5 * arm_width),
                ]
            )
        )
        polygons.append(
            ccw(
                [
                    (side * reach, elbow),
                    (shoulder, elbow + 0.5 * branch_width),
                    (shoulder, elbow - 0.5 * branch_width),
                ]
            )
        )
    return polygons


def ccw(points: list[tuple[float, float]] | np.ndarray) -> np.ndarray:
    """The polygon, wound counter-clockwise.

    Winding is corrected rather than hand-kept per shape: a turn head is the
    mirror of its opposite, so half of them come out reversed from the same
    expression, and a reversed one renders as **nothing** under `cull_back`
    rather than as anything a frame would show (`Q58`).
    """
    ring = np.asarray(points, dtype=np.float64)
    shifted = np.roll(ring, -1, axis=0)
    twice_area = float(np.sum(ring[:, 0] * shifted[:, 1] - shifted[:, 0] * ring[:, 1]))
    return ring if twice_area > 0.0 else ring[::-1]


def _place(polygon: np.ndarray, x: float, z: float, heading_deg: float) -> np.ndarray:
    """A glyph polygon in game plan space, at `(x, z)` pointing along `heading_deg`.

    Heading is clockwise from north, and north is `-Z`: forward is
    `(sin h, -cos h)` and right is `(cos h, sin h)`.
    """
    forward, right = frame(heading_deg)
    return np.array([x, z]) + polygon[:, :1] * right + polygon[:, 1:2] * forward


def nearside(heading_deg: float) -> np.ndarray:
    """The unit vector to the **nearside** of an edge, in game plan space.

    Nearside is *left* of travel — the rail `surface.mitres` offsets to, and the
    side `Snap.offset_m` is positive on.

    ⚠️ **Public, and spelled exactly once, because a flip here mirrors every
    side-keyed feature in the city and still renders as a city.** `_frame`'s own
    docstring records that this vector was written out three times in the first
    draft of this module and that "a sign fix lands in two of three places"; it
    was then written a fourth time in `pipeline/signs.py`, which is what made it
    public. `tests/test_signs.py` pins it against `surface.mitres` itself rather
    than against this comment.
    """
    return -frame(heading_deg)[1]


@dataclass(frozen=True)
class Ribbon:
    """What `surface.py` drew for one edge, as a consumer needs to read it.

    ⚠️ **Public because `pipeline/signs.py` reads it too**, and reads it for the
    same reason: the drawn half-width is `surface.py`'s answer after the widening
    and after `Q23`'s per-station adjustment, so a second implementation of it
    would be a second join in `Q56`'s sense — disagreeing would tell us one was
    wrong and never which.

    ⚠️ **`carriageway_m` is the exception to that first sentence**: it comes off
    `roadgraph.json`, not off anything `surface.py` drew, and only the lane snap
    reads it. `signs`, `signals` and `lamps` import this class and inherit a
    field they never touch.
    """

    lanes: int
    # ⚠️ **The SURVEYED carriageway (`roadgraph.json`'s `width_m`), not the drawn
    # ribbon.** `half_width_m` below is what `surface.py` drew after
    # `surface.floor_default_m`; this is what TD, iB1000 and HyD measured. The
    # two frames meet in `_lane_of` and nowhere else, and conflating them is what
    # `Q96` was — see that function for what it cost and on how many edges.
    carriageway_m: float
    one_way: bool
    # Normalised distance along the published polyline at each station, and the
    # drawn half-width there. Per station rather than per edge because `Q23`
    # widens the ribbon station by station.
    at: np.ndarray
    half_width_m: np.ndarray
    # The centreline itself, `(n, 2)` as `(x, z)` per station. ⚠️ **Carried so a
    # consumer can take the foot of a snap from the polyline rather than
    # reconstruct it** — see `foot_at`.
    plan: np.ndarray
    # Deck height at each of those stations, straight off the published
    # polyline. ⚠️ **This is what an arrow's height comes from, rather than a
    # fresh snap at its nose and tail.** A second snap is a second join with no
    # memory of the host edge: measured, **43 of 747** arrows took at least one
    # endpoint from a *different* edge, disagreeing with the ribbon they are
    # drawn on by up to **0.515 m** against a `lift_m` of 0.015. Interpolating
    # here reproduces `Snap.y` to 1.8e-15 m, because it is the same linear
    # interpolation — it is a faithful substitute, not an approximation.
    height_m: np.ndarray
    trim_start_m: float
    trim_end_m: float
    length_m: float

    def half_width_at(self, t: float) -> float:
        """The drawn half-width at a normalised position along the edge."""
        return float(np.interp(t, self.at, self.half_width_m))

    def foot_at(self, t: float) -> np.ndarray:
        """The point on the centreline at `t`, in game plan space.

        ⚠️ **Read from the polyline, never reconstructed as
        `point - offset_m * nearside`.** `Snap.offset_m` is `±distance_m` to the
        **clamped** projection, so for anything past an edge's end the
        displacement has an along-edge component and that subtraction lands off
        the centreline. Measured on an edge from (0,0) to (100,0) with a point at
        (105, 0) — dead on the axis, 5 m past the end — the reconstruction gives
        (105, -5), five metres off a road the point is standing in the middle of.
        Where the snap did not clamp the two agree to the bit.
        """
        return np.array(
            [
                float(np.interp(t, self.at, self.plan[:, 0])),
                float(np.interp(t, self.at, self.plan[:, 1])),
            ]
        )

    def kerb_target(self, snap: Snap, outset_m: float) -> tuple[float, float, float, np.ndarray]:
        """The registration target `outset_m` past the drawn kerb, and its frame.

        Returns `(side, half_width_m, target_m, point)`: the kerb side (`+1`
        nearside — a point exactly on the centreline has no side to keep, and
        the nearside is the one a left-driving city's traffic passes closest
        to), the drawn half-width at the snap, the signed across-edge target,
        and the placed point.

        ⚠️ **The point comes off the polyline (`foot_at`), never from
        `point - offset_m * nearside`** — `Snap.offset_m` is `±distance_m` to
        the *clamped* projection, so a post past an edge's end has an along-edge
        component in that vector and the subtraction lands off the centreline;
        `foot_at` carries the measurement. Only the arithmetic is shared
        (`Q100`): whether to move at all, `Q78`'s outward-only clamp and every
        counter stay with each stage, and `signals._register` deliberately does
        not clamp.
        """
        half_width_m = self.half_width_at(snap.t)
        side = 1.0 if snap.offset_m >= 0.0 else -1.0
        target_m = side * (half_width_m + outset_m)
        point = self.foot_at(snap.t) + target_m * nearside(snap.heading_deg)
        return side, half_width_m, target_m, point


def ribbons(graph: dict, surface: dict) -> dict[int, Ribbon]:
    """The drawn ribbon, keyed by edge id.

    ⚠️ **Read from `roadsurface.json` rather than recomputed.** The drawn
    half-width is `surface.py`'s answer after the widening and after `Q23`'s
    per-station adjustment, and a second implementation of it here would be a
    second join in `Q56`'s sense — disagreeing would tell us one was wrong and
    never which.
    """
    widths = {int(entry["edge"]): entry for entry in surface["carriageway"]}
    drawn_ribbons: dict[int, Ribbon] = {}
    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        drawn = widths.get(int(edge["id"]))
        if drawn is None:
            continue
        points = np.asarray(edge["polyline"], dtype=np.float64)
        along = plan_lengths(points)
        total = float(along[-1])
        half = np.asarray(drawn["half_width_m"], dtype=np.float64)
        carriageway_m = float(edge["width_m"])
        if total <= 0.0 or len(half) != len(along) or not carriageway_m > 0.0:
            # A width list that does not match the polyline it was measured on
            # is a contract break, not a rounding problem. Skipped rather than
            # interpolated across, and visible as a symbol that found no lane.
            #
            # ⚠️ **A missing surveyed width is refused HERE and not in
            # `_lane_of`**, so it lands in `no_lane` rather than in
            # `outside_carriageway`. An absent width and an arrow past a kerb are
            # two populations, and `Q90`'s `ends_no_target` is the precedent for
            # keeping the second out of the first's count. This is also the only
            # place with the edge id to name.
            # ⚠️ **`not x > 0.0`, never `x <= 0.0`** — the second is False for
            # NaN, which would divide through to a silent lane 0.
            continue
        trim = drawn.get("trim_m") or [0.0, 0.0]
        drawn_ribbons[int(edge["id"])] = Ribbon(
            lanes=int(edge["lanes"]),
            carriageway_m=carriageway_m,
            one_way=str(edge["direction"]) != "both",
            at=along / total,
            half_width_m=half,
            plan=np.column_stack([points[:, 0], points[:, 2]]),
            height_m=points[:, 1],
            trim_start_m=float(trim[0]),
            trim_end_m=float(trim[1]),
            length_m=total,
        )
    return drawn_ribbons


def _lane_of(offset_m: float, carriageway_m: float, lanes: int) -> tuple[int, bool]:
    """Which drawn lane slot a surveyed offset falls in, and whether it fell outside.

    ⚠️ **Outside the SURVEYED carriageway, which is not 'past the kerb'.** The
    kerb is the edge of the ribbon `surface.py` drew, and that test is
    `outside_drawn_ribbon` at the call site. Since `drawn = max(width_m, floor)`
    the drawn ribbon is never narrower, so this fires on a strict superset —
    38 against 9 — and the two names must not be traded for each other.

    The published offset read as a fraction of the carriageway rather than as a
    distance — the one step that survives the widening, because the ribbon is
    drawn wider about the same centreline.

    🔴 **The denominator is the SURVEYED carriageway and never
    `lanes x lane_width_m`.** That identity was `roadgraph.json`'s until `Q95`
    measured `width_m`, and this stage went on reconstructing it for itself on
    292 of 737 level-0 edges — reading `e351` CANAL ROAD EAST's 16.11 m as 6.4.
    Too small a denominator inflates the fraction, so arrows reach the clamp
    early and pile into the outer lanes while the centre lane goes
    under-populated. Dividing by `lane_width_m` would also be `Q94`'s refusal one
    frame over: 3.2 m is the constant under test.

    ⚠️ **`lanes` is the slot count on the DRAWN ribbon, and stays.** `U` is
    `TEXCOORD_0`'s lane coordinate — 0 at the nearside kerb, `lanes` at the
    offside — and `offset_m` is positive to the nearside, so the two run opposite
    ways and `U = lanes * (1 - fraction) / 2` is the conversion.

    ⚠️ **At `lanes == 2` this reduces to the SIDE of `offset_m` and no width can
    reach it**: `int(1 - fraction)` is 1 below the centreline and 0 above it
    whatever the denominator. ⚠️ Not `sign`, which is 0 at the centreline where
    this returns 1 — every bucket boundary ties toward the higher index, so an
    arrow digitised exactly on the centre of a two-lane road is offside.

    The graph calls **670 of 737** level-0 edges two-lane,
    leaving **67** with three or more — and of those, the **36** whose published
    width is not `lanes x lane_width_m` are every edge this can move. Recorded
    in `Q96` as a finding about how little the width buys downstream, and pinned
    by a test so a change to this arithmetic has to face it rather than discover
    it.

    The clamp is returned rather than counted here, because an offset past the
    surveyed carriageway is a disagreement between two published quantities —
    `e309` is 6.52 m wide carrying an authored three lanes — and naming it is the
    detector this stage did not have.
    """
    if not carriageway_m > 0.0 or offset_m != offset_m:
        # ⚠️ **Unreachable from `build_region` — `ribbons()` refuses such an edge
        # before a ribbon exists**, so this never reaches `outside_carriageway`
        # and the counter stays one population. Kept so the function is honest
        # standalone rather than returning a confident lane 0.
        #
        # 🔴 **`not x > 0.0` and `x != x`, never `x <= 0.0`.** Both
        # comparisons are False for NaN, so the arithmetic form of this guard
        # lets a NaN through, `min(1.0, nan)` returns 1.0, and the arrow draws
        # neatly at the nearside kerb with no counter firing.
        return 0, True
    fraction = offset_m / (0.5 * carriageway_m)
    clamped = abs(fraction) > 1.0
    fraction = max(-1.0, min(1.0, fraction))
    return max(0, min(lanes - 1, int(0.5 * lanes * (1.0 - fraction)))), clamped


def _offset_of(lane: int, half_width_m: float, lanes: int) -> float:
    """Where a lane slot's centre sits on the DRAWN ribbon, in the edge's frame.

    🔴 **The exact inverse of `_lane_of`, and they must be read together.** One
    rule — `U = 0` at the nearside kerb, `offset_m` positive to the nearside — is
    expressed once each way, and a change to that convention is a change to both.
    Split across a named function and an inline expression it was a change to one
    of them, which is `Q59`'s mirrored-city class: the whole region renders
    perfectly with every arrow on the wrong side.

    ⚠️ **The two differ in FRAME and that is the entire point of `Q96`.**
    `_lane_of` divides by the carriageway the publishers surveyed; this
    multiplies by the half-width `surface.py` actually drew, which is floored.
    Reading a published offset against the drawn ribbon would pull every arrow
    toward the centre on a floored street.
    """
    return half_width_m * (1.0 - 2.0 * (lane + 0.5) / lanes)


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> ArrowReport:
    """Read the region's published turn arrows and write its `arrows.glb`."""
    spec = city.arrows
    report = ArrowReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the same shape `tramway` takes: a city whose estate
        # publishes no marking symbols ships none rather than inferring them.
        log.info("city '%s' declares no arrows block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    symbols = read_symbols(city, spec, region_id, transform, report, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # ⚠️ **Through `read_document`, not a bare parse.** Every arrow's lane comes
    # from `half_width_m` in here, so a manifest from a build before
    # `SURFACE_MANIFEST_SCHEMA` 4 — when that field was one number rather than
    # one per station — would register the whole region against another build's
    # widths and report `drawn` normally. That is the failure `documents.py`
    # exists to stop, and `clearance.py` reads the same document the same way.
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    drawn = ribbons(graph, surface)
    # Level 0 only, the same restriction `kerbside.py` and `tramway.py` both
    # make: for 7% of the kerbside samples the nearest edge of *any* level was
    # elevated, and the street the marking is actually on was a median 4 m away.
    segments = Segments.of([edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0])

    # The accumulator is `meshbuild.FlatBuilder`; the channel decision is this
    # stage's and stays recorded here. ⚠️ **Position and normal only — no `COLOR_0`,
    # no `TEXCOORD_0`, no `TEXCOORD_1`.** The colour is authored in
    # `game/tuning/arrows.tres` beside the markings it matches (`Q53` deliberately
    # kept paint out of `materials:`), and the first draft's unread glyph-local
    # `TEXCOORD_0` cost 59 KB of a 257 KB asset — a channel earns its place when
    # something reads it (`Q54`).
    # 🔴 **One builder per code, not one for the region** (`P5-4`). A code is
    # drawn ONCE, flat at the origin with its nose north, and every arrow of it
    # is a stand — position, heading, pitch — so the library glyph is the
    # arrow `_place` would have drawn at heading 0, and `tests/test_arrows.py`
    # pins the stood copy against the in-place draw.
    library: dict[str, FlatBuilder] = {}
    stands: list[Placement] = []
    laid: list[_Laid] = []
    for symbol in symbols:
        snap = segments.nearest(symbol.x, symbol.z)
        if snap.distance_m > spec.max_offset_m:
            report.too_far += 1
            continue
        residual = axis_residual_deg(symbol.heading_deg, snap.heading_deg)
        # ⚠️ **Recorded before the refusal, not after**, and the order is the
        # whole value of the number. Appending it below the guard would confine
        # every percentile to `bearing_tolerance_deg` **by construction** — the
        # exact trap `Q58` recorded when `drawn_gauge_m` was published as the
        # tramway join's detector and could not read outside `pair_tolerance_m`.
        # Published from here, the distribution's tail is the population that
        # matched badly, and `off_bearing` counts what it cost.
        report.axis_residual_deg.append(residual)
        report.offset_m.append(abs(snap.offset_m))
        if residual > spec.bearing_tolerance_deg:
            # Matched a road it is not on. Refused, never rotated onto it.
            report.off_bearing += 1
            continue
        ribbon = drawn.get(snap.edge)
        if ribbon is None or ribbon.lanes < 1:
            report.no_lane += 1
            continue

        directed = directed_residual_deg(symbol.heading_deg, snap.heading_deg)
        if ribbon.one_way and directed > 90.0:
            # ⚠️ **Refused, not recorded.** An arrow pointing against a one-way
            # street is not a thing the world contains, so this symbol has
            # either matched the wrong edge or found a one-way the graph has
            # backwards — and both mean drawing it would assert something false
            # on a street the `P3-9a` drivers know.
            #
            # Measured, the population is two shapes. Most of it is an opposed
            # carriageway pair — Fleming Road, Tonnochy Road — where the arrow
            # belongs to the *other* ribbon a few metres away and the axis test
            # cannot see it, because the two ribbons are parallel by
            # construction. The rest sit 2 m from a street whose own direction
            # is the thing in doubt.
            #
            # Re-matching to the nearest edge that agrees would recover them and
            # is deliberately not done: it would move an arrow onto a road
            # nothing checked, and `GAME_DESIGN.md` prices a missing arrow at
            # nothing against a misplaced one. The count is the finding.
            report.against_one_way += 1
            continue
        if not ribbon.one_way:
            report.drawn_on_two_way += 1

        lane, outside_carriageway = _lane_of(snap.offset_m, ribbon.carriageway_m, ribbon.lanes)
        if outside_carriageway:
            report.outside_carriageway += 1
        glyph = spec.glyphs[symbol.code]
        along_m = snap.t * ribbon.length_m
        half_width_m = ribbon.half_width_at(snap.t)
        drawn_offset_m = _offset_of(lane, half_width_m, ribbon.lanes)
        report.lane_shift_m.append(abs(drawn_offset_m - snap.offset_m))
        if abs(snap.offset_m) > half_width_m:
            report.outside_drawn_ribbon += 1

        # The deck under the arrow's two ends, off the host edge's own polyline.
        # ⚠️ **The sign is load-bearing.** `axis_residual_deg` folds modulo 180,
        # so an arrow on the far side of a two-way street legitimately points
        # *backwards* along its edge — and without this its nose and tail heights
        # come out swapped, tilting it against the grade instead of with it.
        half_t = 0.5 * glyph.length_m / ribbon.length_m
        if directed > 90.0:
            half_t = -half_t
        y_tail = float(np.interp(snap.t - half_t, ribbon.at, ribbon.height_m))
        y_nose = float(np.interp(snap.t + half_t, ribbon.at, ribbon.height_m))
        if along_m < ribbon.trim_start_m or along_m > ribbon.length_m - ribbon.trim_end_m:
            report.over_a_cap += 1

        # Nearside is *left* of travel — `U = 0` is the rail `surface.mitres`
        # offsets to the left — so it is `-right` in the edge's own frame.
        near = nearside(snap.heading_deg)
        centreline = np.array([symbol.x, symbol.z]) - snap.offset_m * near
        placed = centreline + drawn_offset_m * near

        if symbol.code not in library:
            library[symbol.code] = FlatBuilder(ARROWS_MATERIAL)
            _draw_glyph(library[symbol.code], spec, glyph)
        stand = _stand(spec, symbol, glyph, placed, y_tail, y_nose)
        stands.append(stand)
        report.pitch_deg.append(abs(float(stand["transform"]["pitch_deg"])))
        report.drawn += 1
        key = "+".join(glyph.movements)
        report.by_glyph[key] = report.by_glyph.get(key, 0) + 1
        laid.append(
            _Laid(
                placed,
                int(snap.edge),
                lane,
                glyph.movements,
                glyph.length_m,
                along_m,
                float(snap.offset_m),
            )
        )

    _count_stacked(laid, report)
    _count_rows(laid, drawn, report)
    _grade_against_the_graph(graph, report)

    # A library mesh is named after the code it draws — `RM1017` — so a region
    # publishing both lengths of one marking ships two meshes, and an artist
    # replacing one replaces one.
    meshes: list[MeshData] = []
    for code in sorted(library):
        built = library[code].build(glyph_mesh_name(code))
        if built is not None:
            meshes.append(built)
    library = stand_library(meshes, stands)
    if meshes:
        # ⚠️ **`inverted` is asked of every DRAWN copy, not of the library.** A
        # rotation about `Y` preserves winding, so the library's answer would be
        # the city's — but the pitch is a second rotation, and a stand pitched
        # past vertical faces the ground while its glyph faces the sky. Asked
        # of the stood copies it is reachable in exactly that way, which is the
        # test `Q72` says a counter has to pass.
        by_name = library.by_name
        for entry in library.stands:
            count, area = downward_facing(stood(by_name[entry["mesh"]], entry))
            report.inverted += count
            report.inverted_area_m2 += area
        library.publish(report)
        library.require_every_stand(report.drawn, f"{report.drawn} arrows")
        report.bytes = library.write(
            out_dir, ARROWS_NAME, ARROWS_PLACEMENTS_NAME, city.id, region_id
        )

    _write_manifest(out_dir, city, region_id, report)
    return report


class _Laid(NamedTuple):
    """One arrow as it was actually placed, for the stacking and row checks.

    ⚠️ **`at` and `lane` are where the arrow was DRAWN; `along_m` and
    `offset_m` are where the publisher put it.** The two are different
    populations and the row reading needs the second — see `_count_rows`.
    """

    at: np.ndarray
    edge: int
    lane: int
    movements: tuple[str, ...]
    length_m: float
    # Distance along the host edge, and the published offset across it. Both
    # are the *unregistered* figures, before the lane snap.
    along_m: float
    offset_m: float


def _count_stacked(laid: list[_Laid], report: ArrowReport) -> None:
    """Pairs of drawn arrows that landed on top of each other.

    Why this stage needs the counter at all is on `ArrowReport.stacked_pairs`.

    ⚠️ **The bar is derived, not authored**: half the shorter glyph's own
    length, because two arrows whose centres are closer than that overlap for
    certain whatever their headings. Same lane of the same edge, so arrows in
    adjacent lanes and arrows repeated along a lane are not counted.
    """
    # ⚠️ **`(edge, lane)` is the gate, so grouping on it first is exact rather
    # than an approximation.** Measured 9.3 ms to 0.38 ms here and 1.47 s to
    # 41 ms at ten thousand arrows; Wan Chai is 1.5 km² and the second city is
    # the business case, so the scaling is the reason rather than today's number.
    # ⚠️ **Unlike `signals._assemble` and `lamps._merge`, which decline the same
    # kind of reduction**: those need a uniform cell hash over a continuous
    # radius and are left because `read_*` pushes the region bbox into OGR. Here
    # the classes are discrete and already computed, so there is nothing to
    # decline.
    lanes: dict[tuple[int, int], list[_Laid]] = defaultdict(list)
    for arrow in laid:
        lanes[(arrow.edge, arrow.lane)].append(arrow)

    for slot in lanes.values():
        for a, b in itertools.combinations(slot, 2):
            if float(np.hypot(*(a.at - b.at))) >= 0.5 * min(a.length_m, b.length_m):
                continue
            report.stacked_pairs += 1
            if a.movements != b.movements:
                report.stacked_disagreeing += 1


def _runs(arrows: list[_Laid], key: Callable[[_Laid], float]) -> Iterator[list[_Laid]]:
    """Split arrows into runs whose neighbours sit within half a glyph of each other.

    ⚠️ **The bar is derived, not authored**, and it is `_count_stacked`'s: half
    the shorter glyph's own length, the distance at which two symbols would
    overlap if they shared a lane. `Q94` read the region with an asserted 1.6 m
    and nothing behind it. One bar serves both axes — along the road it separates
    two *rows*, across it two *lanes* — so there is one free value here rather
    than two, and it is not free.

    ✅ **Swept rather than argued** (`Q72` rejected a pairing rule whose count ran
    8 -> 29 -> 49 -> 80 over a free radius). Over the 4 m glyph:

        bar    1.00 m  1.50  2.00  2.50  3.00  4.00
        more       28    30    30    30    24     0
        at four     9     9     9     9     3     0

    Flat across 1.50-2.50 with the shipped 2.00 in the middle of it, and the
    plateau ends exactly where the bar passes **3.0 m** — TPDM 4.3.9.8's
    narrowest through lane — because past that it merges two real lanes into
    one. The collapse is the bar meeting a published dimension, not a tuning
    cliff.
    """
    # ⚠️ **Guarded although no caller can reach it today.** `_count_rows` groups
    # into a `defaultdict` it only ever appends to, and this function never
    # yields an empty run, so both call sites hand it something. That is a
    # caller's invariant rather than this function's, and the refactors that
    # would break it are ordinary ones — filtering `laid` before grouping, or
    # seeding a key per ribbon so arrow-less edges report 0.
    ordered = sorted(arrows, key=key)
    if not ordered:
        return
    run = [ordered[0]]
    for previous, arrow in itertools.pairwise(ordered):
        if key(arrow) - key(previous) >= 0.5 * min(previous.length_m, arrow.length_m):
            yield run
            run = []
        run.append(arrow)
    yield run


def _count_rows(laid: list[_Laid], ribbons: dict[int, Ribbon], report: ArrowReport) -> None:
    """The lane count each edge's own arrows state (`Q94`).

    A row of turn arrows *across* a carriageway is a lane count written down by
    the publisher rather than derived from anything — `e505` STEWART ROAD
    carries left | left-or-right | right at one station, which is a three-lane
    approach stated. That makes this the one lane count in the bundle owing
    nothing to a width, and therefore the only thing able to grade one.

    🔴 **Clustered on the PUBLISHED offset, never on the placed one.** The lane
    snap is the quantity under test; grouping on where an arrow was *drawn*
    would report `ribbon.lanes` back to itself and read as agreement whatever
    the graph said — `Q72`'s tautology, which certified a whole region's signs
    as correct while every one faced the wrong way.

    ⚠️ **An edge's count is the widest row it carries, not its rows averaged.**
    A carriageway that holds three arrows abreast has three lanes at that
    station whatever the rest of it is painted with, and a mean would let a long
    edge with one marked junction read as two.
    """
    by_edge: dict[int, list[_Laid]] = defaultdict(list)
    for arrow in laid:
        by_edge[arrow.edge].append(arrow)

    for edge, arrows in by_edge.items():
        # Rows along the edge, then lanes across each row, on the same bar.
        widest = max(len(list(_runs(row, _offset))) for row in _runs(arrows, _along))
        report.implied_lanes[edge] = widest
        ribbon = ribbons.get(edge)
        if ribbon is not None and widest > ribbon.lanes:
            report.edges_implying_more_lanes += 1


def _grade_against_the_graph(graph: dict, report: ArrowReport) -> None:
    """Diff this stage's lane row against `carriageway.py`'s (`Q94`).

    🔴 **The only check on a measurement the region implements twice.** That
    stage needs the row before any ribbon exists, and cannot import this module
    — `arrows` imports `roads`, `roads` imports `carriageway` — so the
    clustering is written out a second time there. `carriageway_margin.py`
    against `pipeline/carriageway.py` is the same arrangement one dimension
    over, and the rule is the same: **they are expected to agree and a
    divergence is a finding**, never something to reconcile by importing one
    into the other.

    ⚠️ **Graded only where that stage PUBLISHED a row**, not across all 306
    arrow-carrying edges. It refuses rows this stage keeps — a row of a single
    arrow, a row falling outside its own width bracket — so the two disagree
    there by design, and a counter spanning both populations would report that
    design as a defect. On an edge it published, `lanes` **is** the row it read,
    so anything but 0 here means the two clusterings diverged.
    """
    for edge in graph["edges"]:
        if str(edge.get("lanes_source")) != "arrows":
            continue
        report.lanes_row_published += 1
        if report.implied_lanes.get(int(edge["id"])) != int(edge["lanes"]):
            report.lanes_row_disagreement += 1


def _along(arrow: _Laid) -> float:
    return arrow.along_m


def _offset(arrow: _Laid) -> float:
    return arrow.offset_m


def _draw_glyph(builder: FlatBuilder, spec: Arrows, glyph: ArrowGlyph) -> None:
    """One library glyph: flat in `y = 0`, centred on the origin, nose north.

    This is `_place` at heading 0 — `+v` along `-Z`, `+u` along `+X` — so a
    stand at the symbol's own heading is the arrow that function would have
    drawn in place, and `tests/test_arrows.py` holds the two together. Flat
    rather than at `lift_m`: the lift is the stand's, vertical whatever the
    pitch, which is what the merged build did too.
    """
    for polygon in glyph_polygons(spec, glyph.movements, glyph.length_m):
        plan = _place(polygon, 0.0, 0.0, 0.0)
        builder.polygon(plan, np.zeros(len(plan)))


def _stand(
    spec: Arrows,
    symbol: Symbol,
    glyph: ArrowGlyph,
    placed: np.ndarray,
    y_tail: float,
    y_nose: float,
) -> Placement:
    """Where one arrow stands: between its two deck heights, lifted clear of them.

    ⚠️ **The entry is `placement()`'s shape and nothing more.** `PLAN.md`'s row
    for `P5-4` said "plus lane slot", and the first build wrote the host `edge`
    and the `lane` beside the transform — 26,777 B, 14.6% of the document, that
    no tool, verifier or scene read. `Q54`'s rule is this module's own, two
    dozen lines up: a channel earns its place when something reads it. `_Laid`
    carries both for the graders that do (`_count_stacked`, `_count_rows`).

    ⚠️ **Pitched between the ends rather than laid flat at the centre.** A 4 m
    glyph laid flat on a 5% grade stands 0.1 m proud at one end and 0.1 m
    under the road at the other, and `lift_m` is 0.015 — the sunk end simply
    disappears. One pitch rather than a height per vertex because the
    longitudinal slope is the one that matters and the cross-slope is camber.

    The glyph is rigid and lies along the chord from the deck under its tail
    to the deck under its nose, so its plan footprint is `length_m x cos(pitch)`
    — shorter than the merged build's by `length_m x (1 - cos)`, millimetres
    on a street. `pitch_deg` is positive nose-up, `placed_positions`' sign.
    """
    return placement(
        glyph_mesh_name(symbol.code),
        (float(placed[0]), 0.5 * (y_tail + y_nose) + spec.lift_m, float(placed[1])),
        symbol.heading_deg,
        pitch_deg=pitch_between(y_nose - y_tail, glyph.length_m),
    )


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: ArrowReport) -> int:
    document = {
        "schema_version": ARROWS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what `CITY_SCHEMA`
        # 11 was bumped over.
        "asset": ARROWS_NAME if report.triangles else None,
        "placements_document": ARROWS_PLACEMENTS_NAME if report.triangles else None,
        # The read, as four disjoint parts of `symbols`.
        "symbols": report.symbols,
        "not_a_turn_arrow": report.not_a_turn_arrow,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "candidates": report.candidates,
        # The join, as five disjoint parts of `candidates`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        "off_bearing": report.off_bearing,
        # ⚠️ **A refusal and a finding at once.** See `build_region`: an arrow
        # against a one-way street cannot be true, so it is dropped — but the
        # count is where an opposed-pair mismatch and a backwards one-way both
        # land, and it is to be gone and looked at rather than tuned against.
        "against_one_way": report.against_one_way,
        "no_lane": report.no_lane,
        "by_glyph": dict(sorted(report.by_glyph.items())),
        # ⚠️ **Recorded over every symbol that found a host, including the ones
        # `off_bearing` then threw away** — so it can read past
        # `bearing_tolerance_deg`, which is the only way it says anything. A
        # distribution taken after its own filter is confined to that filter by
        # construction, which is what stopped `drawn_gauge_m` being able to see
        # a bad tramway join (`Q58`). p90/p99/max rather than a median for the
        # matching reason: the tail is the finding, and a median near zero is
        # also what a wholly broken join looks like.
        #
        # `off_bearing` beside it is what the tail cost.
        "axis_residual_deg": report.measured(report.axis_residual_deg),
        # What `max_offset_m` is set against, published so the config's comment
        # is checkable against a shipped artefact rather than a scratch script.
        "offset_m": report.measured(report.offset_m),
        "drawn_on_two_way": report.drawn_on_two_way,
        "outside_drawn_ribbon": report.outside_drawn_ribbon,
        # 🔴 The same question asked of the surveyed carriageway rather than the
        # drawn ribbon, and a strict superset of the line above — see
        # `ArrowReport`.
        "outside_carriageway": report.outside_carriageway,
        # What the lane registration moved. The residue of the decision at the
        # top of `arrows.py`, published so that decision can be re-argued
        # against a number rather than against the prose.
        "lane_shift_m": report.measured(report.lane_shift_m),
        "over_a_cap": report.over_a_cap,
        # 🔴 The pairs that landed on top of each other — see `ArrowReport`.
        # `stacked_disagreeing` is the one to read: it is arrows giving
        # different instructions from the same square metre of lane, and it is
        # `Q19`'s invented lane count arriving where a frame can show it.
        "stacked_pairs": report.stacked_pairs,
        "stacked_disagreeing": report.stacked_disagreeing,
        # 🔴 The lane count the publisher's own arrows state, per edge — see
        # `ArrowReport.implied_lanes`. Published **per edge** rather than as a
        # total, because a grader that can name no edge cannot be checked
        # against a frame, and `Q94`'s figures came from a scratch script that
        # named three roads and shipped none of them (`Q37`'s debt).
        # ⚠️ Keys are edge ids as strings; JSON has no integer key.
        "implied_lanes": {
            str(edge): report.implied_lanes[edge] for edge in sorted(report.implied_lanes)
        },
        "edges_with_arrows": len(report.implied_lanes),
        "lanes_row_published": report.lanes_row_published,
        "lanes_row_disagreement": report.lanes_row_disagreement,
        "edges_implying_more_lanes": report.edges_implying_more_lanes,
        # Published, unread. `SYMBOL_SIZE` may or may not be the arrow's length
        # in metres; the glyph table takes its lengths from the index plan
        # instead. Recorded here so the question is answerable from a shipped
        # artefact — `Q37`'s debt, which `Q55` was the last instance of.
        "symbol_size": report.measured(report.symbol_size),
        # ⚠️ **Must be 0.** `marking_paint.gdshader` is `cull_back`, so winding decides
        # visibility and the normal attribute does not. The tramway shipped
        # 5,111 of 5,112 triangles facing the ground with everything else
        # correct, and the city simply had no tramway in it.
        "inverted": report.inverted,
        "inverted_area_m2": round(report.inverted_area_m2, 4),
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
        # The library and its stands (`P5-4`); `triangles`/`vertices`/`aabb`
        # above are what those stands DRAW.
        "placements": report.placements,
        "placements_refused": report.placements_refused,
        "library_meshes": report.library_meshes,
        "library_triangles": report.library_triangles,
        "library_vertices": report.library_vertices,
        # The grade each arrow lies on — see `ArrowReport.pitch_deg`. p90/p99/max
        # like every distribution here: the tail is the arrow standing on its
        # nose, and a median near zero is also what a flat city reads.
        "pitch_deg": report.measured(report.pitch_deg),
    }
    return write_document(out_dir / ARROWS_MANIFEST_NAME, document)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "arrows: %d symbols -> %d turn arrows drawn (%d too far, %d off bearing), %d triangles; "
        "%d pairs stacked in one lane, %d of them disagreeing",
        report.symbols,
        report.drawn,
        report.too_far,
        report.off_bearing,
        report.triangles,
        report.stacked_pairs,
        report.stacked_disagreeing,
    )
    log.info(
        "  lane rows: %d edges, %d published as a lane count by the roads stage, "
        "%d disagreeing with what it read — a divergence between two implementations",
        len(report.implied_lanes),
        report.lanes_row_published,
        report.lanes_row_disagreement,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
