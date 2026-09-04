"""Published road centrelines to a drivable graph (`P1-3`).

Reads the road network geodatabase a previous fetch cached, clips it to the
region, snaps shared endpoints into nodes, and writes `roadgraph.json` per the
contract in `docs/ARCHITECTURE.md`.

Three properties of the source shape everything here, all of them measured
rather than assumed — see `docs/DATA_SOURCES.md`:

- **Endpoints coincide exactly.** Centrelines that meet share a vertex to full
  float precision, and the nearest *distinct* pair of endpoints in the region is
  2.26 m apart. So nodes are found by exact coordinate identity, and there is no
  snapping tolerance to tune or to get wrong.
- **Grade separation must not split nodes.** Every endpoint in the region where
  two `ELEVATION` levels meet is a ramp touching down. Keying nodes on the level
  as well as the position severs the elevated network from the ground one.
- **The geometry is wildly over-densified in places.** One 51.7 m centreline
  ships 54,330 vertices. Simplification is a correctness measure for `P1-4`, not
  a size optimisation.

Nothing here knows a Hong Kong fact: layer names, column names, direction codes
and lane policy all arrive from `config/hong_kong.yaml`.
"""

from __future__ import annotations

import argparse
import itertools
import logging
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from pipeline import carriageway, gdb, kerbside
from pipeline.buildings import Placement, read_sheet
from pipeline.config import (
    BACKWARD,
    FORWARD,
    Config,
    DeckSampling,
    GroundProfile,
    RoadNetwork,
    SourceLayer,
    load_config,
)
from pipeline.crs import GameTransform
from pipeline.documents import read_document, round_position, write_document
from pipeline.fetch import cached_source
from pipeline.gltf import normalise
from pipeline.polyline import plan_lengths_2d, plan_steps_2d
from pipeline.terrain import HeightField

log = logging.getLogger(__name__)

ROADGRAPH_NAME = "roadgraph.json"
# 2 since `P2-7`: an off-grade polyline's `y` is sampled from the structure the
# road is built on, so it varies along an edge instead of being one flat offset
# per level. No field was added or removed — what changed is what the numbers
# mean, which is exactly the change a consumer cannot detect for itself.
#
# 3 closes `Q23`, and this one *does* add a field: `on_structure`, per vertex.
# Schema 2 lifted 16 level-0 edge ends onto the ramps they sit on but had no way
# to say so, and `elevation_level` cannot stand in for it — a road becomes a
# bridge partway along an edge, not at an edge boundary. Nor can `y`: with
# `ground: terrain` an at-grade hill road reaches 49 m. Only this stage knows,
# at the moment it lifts them.
#
# 4 closes `Q54`, and adds a field for the same reason 3 did: `kerbside`, the
# runs of each edge the published no-stopping layer restricts. `P3-12` painted a
# double yellow on every kerb in the region because the graph had no way to say
# where one belongs, and no attribute already here stands in for it — the layer
# joins by geometry rather than by key (`pipeline/kerbside.py`), so only a stage
# holding both it and the finished edges can answer.
# 5 closes the width half of `Q95`, and it bumps because a consumer would be
# *wrong* to keep its old interpretation rather than merely see different bytes.
# `width_m` was `lanes x lane_width_m` on every edge — an identity a reader
# could invert to recover a lane count — and on the edges the publishers span it
# is now a measurement, so that inversion silently returns a number the graph
# never claimed. `width_source` is what says which of the two a given edge
# carries; `lanes` itself is untouched and still authored (`Q94`).
# 6 closes `Q94`, and it is 5's own sentence coming due: `lanes` is no longer
# untouched. Where the measured `width_m` resolves under TPDM 4.3.9.8's
# 3.0-3.65 m through-lane range it is a *reading* rather than authored policy,
# and a consumer treating every count as policy keyed on the speed limit would
# be **wrong** — not merely looking at different bytes, which is hard rule 5's
# test. `lanes_source` says which of `authored`, `measured`, `floored` or
# `arrows` an edge carries. ⚠️ It is a strict subset of the measured widths:
# what neither TD's range nor a row of turn arrows resolves keeps the authored
# count.
# 7 adds `width_publisher`, and it bumps because schema 6 shipped a claim that
# had quietly stopped being true. Through schema 5 every measured `width_m` was
# kerb-to-kerb, read off a line publisher. Schema 6's third publisher draws the
# maintained carriageway as an *area* and carves traffic islands, run-ins and
# car parks out of it, so on the edges it answered `width_m` is the trafficable
# surface instead — p10 **-3.39 m** apart across this region. A consumer reading
# schema 6 as one homogeneous population is **wrong**, which is hard rule 5's
# test; this field is what lets it separate them. ⚠️ Empty where authored.
#
# 8 closes half of `Q19`'s structure half, and adds `structure_bounded`, per
# vertex. Schema 7 could say where a station's height came *from* and had no way
# to say what stands *beside* it, and `on_structure` cannot stand in for the
# second: it is height provenance, so an approach ramp walled on both sides but
# sampled off the terrain reports every station off structure. `e233`, `e55` and
# `e398` do exactly that, and `surface.py` drew them at the 10.24-12.48 m floor
# over surveyed carriageways of 5.42, 5.57 and 6.66 m. Nor can `y`,
# `elevation_level` or `width_m` recover it. A consumer that keeps reading
# `on_structure` as "is this carriageway bounded" is **wrong** about the whole
# Wan Chai Interchange, which is hard rule 5's test.
#
# 9 adds `offset_m` and `offset_source` (`Q103`), and it bumps on hard rule 5's
# test rather than because bytes moved. 🔴 **The drawn ribbon is no longer
# centred on the published centreline.** Off-grade it is shifted onto the deck
# it is actually built on, by up to 4.90 m, so a consumer reconstructing a kerb
# as `polyline ± width_m / 2` — which is what every reader could do through
# schema 8 — is now **wrong** about the whole elevated network. Nothing else in
# the document says so: `width_m` gives the size and only this gives the place.
# ⚠️ The centreline itself is untouched (`Q54`); what changed is the claim that
# the paint is centred on it.
# 10 adds `deck_rim_m` (`Q107`): per **vertex**, `[left_m, right_m]`, how far
# the deck reaches either side of the published centreline in
# `surface.mitres`' LEFT-of-travel frame — so the structure occupies
# `[-right_m, +left_m]` there. 🔴 **`width_m` and `offset_m` are the median of
# the sum and of the difference of exactly these**, and a median cannot fit a
# deck that changes width along its length: `Q103` measured per-edge `over p50`
# getting *worse* on 22 of 35 edges for that reason. A consumer that keeps
# reading `width_m` as the whole story is not wrong about the size, it is wrong
# about where the structure ENDS — which is hard rule 5's test, and it is the
# difference between paint on a deck and paint over air.
# ⚠️ Present only on the off-grade edges the deck walk measured, and `[]`
# elsewhere; a reader must fall back to `width_m` / `offset_m`, which is what
# every edge without it has always been.
# 11 is `Q114`, and it changes no field at all — it withdraws a guarantee and
# widens a vocabulary. Both halves are about `lanes`.
# 🔴 **`lanes` can be 1.** Through schema 10 a measured single lane was
# published as **two**, so every consumer could take `lanes >= 2` for granted —
# and one did: `RoadGraph.lane_offset` returns 0 at a count of one, which puts
# the nearside lane centre on the centreline, the one place on the network a
# wheel must not go. A reader keeping schema 10's assumption is not looking at
# different bytes, it is driving down the seam, which is hard rule 5's test. The
# floor now lives in that consumer as `LANE_FLOOR`, so the driving line is
# unchanged and the published count is the measurement. `lanes_source` loses
# `floored` with it and those 57 edges read `measured`.
# 🔴 **And `lanes` is capped by the deck an off-grade edge stands on**, with
# `lanes_source: deck_capped` saying where that bit — a fourth value a consumer
# enumerating schema 10's set would not know. ⚠️ **A refusal and never a
# reading**: no turn arrows are painted on a bridge deck and the line
# publishers' 2D rays find the street underneath, so the deck licenses no lane
# count — only the ceiling that paint cannot be wider than the structure it is
# painted on, which is `Q107`'s own licence for cutting the ribbon to
# `deck_rim_m`. A count the deck can hold is left exactly as authored, and 8 of
# this region's 36 deck edges sit *below* their ceiling untouched.
# ⚠️ **`width_m` does NOT move in either half.** A lane count is not a width
# (hard rule 4), and the drawn ribbon is `max(width_m, floor)` either way.
ROADGRAPH_SCHEMA = 11

# `Node.kind` in the data contract. Degree three or more is somewhere a
# driver can choose; anything else is a road continuing or stopping.
JUNCTION = "junction"
ENDPOINT = "endpoint"

# Endpoints are rounded to this many decimal places before being compared —
# millimetres. Anything from roughly a millimetre to a metre gives the identical
# graph, because the nearest *distinct* pair of endpoints in the region is
# 2.26 m apart, so this is not a tolerance that needs tuning.
#
# It does have to be at least this coarse. Two of the region's endpoint clusters
# differ in the last few bits and agree only once rounded: at a tenth of a
# millimetre they split into separate nodes, which silently disconnects
# Johnston Road at Fenwick Street and drops the turn restriction there.
_SNAP_DECIMALS = 3

# Leading integer of a speed-limit string. The source writes "70 km/h", and the
# units are not guaranteed to be spelled the same way twice. Anchored, so a
# label like "Route 4, 70 km/h" is rejected rather than read as 4 km/h.
_LEADING_INTEGER = re.compile(r"\s*(\d+)")

# Two clipped points closer than this in both axes are the same point. Written
# as an absolute metre tolerance rather than through `np.allclose`, whose
# default `rtol=1e-5` would silently widen it to 15 mm at the far edge of a
# 1.5 km region — and which measured 25% of this stage's runtime, called once
# per segment of every centreline that crosses the boundary.
_JOIN_EPSILON_M = 1e-9


@dataclass(frozen=True)
class Node:
    id: int
    pos: tuple[float, float, float]
    kind: str


@dataclass(frozen=True)
class Edge:
    id: int
    source_id: int
    from_node: int
    to_node: int
    polyline: list[tuple[float, float, float]]
    # One flag per vertex of `polyline`: is this station resting on structure the
    # deck sampler actually found? `Q23`'s signal, and `surface.py` is the
    # consumer — it draws a road on a deck at its authored width, and could not
    # tell which stations those were from the graph alone. False everywhere for a
    # city that does not sample decks, which is what "no structure known" means.
    on_structure: list[bool]
    # One flag per vertex of `polyline`: does structure stand *beside* this
    # station, at the height a bumper meets it? `Q19`'s signal, and `surface.py`
    # is again the consumer — a carriageway with a wall down each side is drawn
    # at its own width, for the reason `Q23` already gives about a deck.
    #
    # ⚠️ **Not `on_structure`, and not implied by it either way.** That flag is
    # height *provenance*; this is what is next to the road. They coincide on a
    # viaduct and come apart on its approach ramp — `e233` is on structure at
    # none of its 17 stations and bounded at 6 of them. A consumer reading one
    # for the other gets the Wan Chai Interchange wrong in both directions.
    structure_bounded: list[bool]
    direction: str
    lanes: int
    width_m: float
    speed_limit_kph: int
    bus_lane: bool
    tram_tracks: bool
    elevation_level: int
    road_name: dict[str, str | None]
    # Runs of this edge's two kerbs that a published no-stopping restriction
    # covers, measured along **this** polyline (`P3-13`). Empty where the source
    # says nothing, which is the honest answer and the one a consumer should
    # draw no line for. Filled after every edge exists, because the join is
    # geometric and an edge cannot find its own restriction alone.
    kerbside: tuple[kerbside.Restriction, ...] = ()
    # How `width_m` was arrived at (`Q95`). `authored` is `lanes x lane_width_m`,
    # what every edge carried before the survey; the others name the rule that
    # licensed a measurement. ⚠️ **A consumer may no longer assume
    # `width_m == lanes x lane_width_m`** — that is what this field exists to say,
    # and why the schema bumps rather than the bytes changing under a reader that
    # would go on deriving a lane count from a width it no longer matches.
    width_source: str = "authored"
    # How `lanes` was arrived at (`Q94`). `authored` is `lanes_for(speed_limit)`,
    # the two-line table every edge carried before the survey; `measured` is the
    # count TD's own through-lane range resolves the measured width to; `arrows`
    # is a row of turn arrows across the carriageway resolving a bracket TD's
    # range left ambiguous, which is the one reading here owing nothing to a
    # width.
    # 🔴 **There was a fourth, `floored`, and `Q114` removed it.** A resolved
    # bracket of one lane was published as two because `RoadGraph.lane_offset`
    # puts a one-lane road's lane centre on the centreline. That is one
    # consumer's constraint, enforced in that consumer now — because a second
    # consumer, `road_markings.gdshader`, cuts the drawn ribbon into `lanes`
    # strips and was painting the floored lane onto the road.
    # 🔴 **`deck_capped` is a REFUSAL and not a reading** (`Q114`). Off-grade
    # nothing publishes a lane count at all, so `lanes` is the speed-limit
    # table; where that names more lanes than the edge's own deck could hold
    # under TPDM 4.3.9.8, the count is cut to the deck's ceiling and this says
    # so. ⚠️ **It never raises a count** — 8 of the region's 36 deck edges are
    # authored below their ceiling and none of them moves.
    # ⚠️ **Not implied by `width_source`.** Many measured widths bracket
    # ambiguously with no arrow row to settle them, so `width_source: one_way_uncrossed` with
    # `lanes_source: authored` is the commonest measured edge rather than a
    # contradiction.
    lanes_source: str = "authored"
    # Which publishers supplied the stations behind `width_m`, joined on `+` and
    # empty where the width is authored (`Q94`). 🔴 **The three do not measure
    # the same quantity**: HyD's `pavement_polygon` carves traffic islands and
    # run-ins out of the carriageway, so it reads the trafficable surface where
    # TD's and iB1000's lines run on to the kerb — p10 **-3.39 m** apart across
    # this region. A consumer treating every measured width as one population is
    # making `Q57`'s generalisation, and this is the field that lets it not.
    # ⚠️ **A set, not a winner**: the survey picks a publisher per *station* and
    # the mixture is common, so a dominant-publisher field would separate a 51%
    # edge from a 49% one over a single station.
    #
    # ⚠️ **Empty rather than `"authored"`, and that break with the two `_source`
    # fields beside it is deliberate.** Those enumerate a *provenance kind*, and
    # `authored` is a legitimate member of that vocabulary. This one enumerates
    # *publisher names*, and `authored` is not a publisher — writing it here
    # would hand a consumer splitting on `+` the token `authored` as though a
    # fourth source had read the edge. An authored width was read by none of
    # them, and the empty set is what says so.
    width_publisher: str = ""
    # 🔴 **How far the DRAWN ribbon is shifted off this centreline, and it is
    # SIGNED (`Q103`).** Positive is left of travel — `surface.mitres`' frame,
    # which is the frame the ribbon is actually built in, because a consumer
    # that has to negate a published number to use it is `Q78` waiting to
    # happen. ⚠️ **The station survey measures in the OPPOSITE frame**
    # (`carriageway._stations` is right of travel), so `_reassign` negates once,
    # by name, and `test_the_published_offset_is_the_negation_of_the_survey`
    # fails if either side moves.
    #
    # ⚠️ **The centreline itself does NOT move.** It is a published government
    # geometry and `Q54` forbids editing one; this says the *paint* is not
    # centred on it, which is a different claim and the true one. Off-grade the
    # ribbon and the deck disagree by p50 0.75 m and up to 4.90 m, and no
    # publisher draws a viaduct deck edge to correct it against.
    offset_m: float = 0.0
    # How `offset_m` was arrived at. `none` is a ribbon centred on its
    # centreline, which is every level-0 edge and every off-grade edge the deck
    # walk could not measure; `deck` is the structure the ribbon is drawn on.
    offset_source: str = "none"
    # 🔴 **The deck's two edges per vertex, in the LEFT-of-travel frame
    # (`Q107`).** `[(left_m, right_m), ...]`, one pair per polyline vertex, so
    # the structure occupies `[-right_m, +left_m]` about the centreline there.
    # Empty everywhere the deck walk published nothing, which is every level-0
    # edge. ⚠️ **`width_m` and `offset_m` are aggregates OF this** — the median
    # sum and the median difference — so the three can disagree along an edge
    # and that disagreement is the point rather than an inconsistency.
    deck_rim_m: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class TurnRestriction:
    from_edge: int
    via_node: int
    to_edge: int


@dataclass
class RoadReport:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    turn_restrictions: list[TurnRestriction] = field(default_factory=list)
    # Centreline parts read, and how many the region boundary left nothing of.
    # The geodatabase's spatial filter selects on bounding box, so a long
    # feature can be selected without ever entering the region.
    read: int = 0
    clipped: int = 0
    # Turns whose two edges both survived clipping but share no endpoint.
    turns_unresolved: int = 0
    # Vertices before and after simplification, and how many fell outside the
    # terrain. All three are the numbers a silent regression would show up in.
    #
    # ⚠️ Since `P2-7` the first two are commensurable with each other but not
    # with the third: `vertices_off_terrain` is counted over the *resampled*
    # stations, so lowering `deck.resample_m` raises it with no regression
    # behind it. `Q24` added a third population to it, so the denominator is
    # `vertices_kept + vertices_added + vertices_followed`.
    vertices_read: int = 0
    vertices_kept: int = 0
    vertices_off_terrain: int = 0
    # `P2-7`'s half of that, and the reason it needs any. The failure this stage
    # can now have is a *quiet* one — a deck sample that never happens leaves
    # the ribbon on the old flat offset and produces a graph that is entirely
    # well-formed, so these are the only place it shows.
    #
    # `vertices_sampled` is stations where the structure answered *directly* and
    # the terrain gate accepted it. The rest of a sampled edge is interpolated
    # between those, so it is a floor on how much of the ribbon is measured
    # rather than a count of it. `vertices_added` spans both the off-grade edges
    # and the lifted level-0 ones, which no other counter here does.
    vertices_added: int = 0
    vertices_sampled: int = 0
    vertices_gated: int = 0
    edges_sampled: int = 0
    ends_lifted: int = 0
    # `Q90`'s, and they partition one population: off-grade edge ends whose
    # structure stops before the node. `touchdown_grade_pct` is recorded over
    # the first two, so `len(...) == ends_descended + ends_over_grade` and `n`
    # exceeding `ends_descended` is what says the distribution is not confined
    # to the cap by construction — `Q58`'s `drawn_gauge_m` trap, which
    # `arrows.py` and `roadmarks.py` have each been corrected for.
    #
    # ⚠️ `ends_no_target` is the third and it is deliberately OUTSIDE that
    # distribution: an end with no terrain to measure from has no grade, and
    # appending one would be inventing the number the other two are graded on.
    # It is counted rather than dropped because a refusal this change cannot see
    # is the exact failure the two above are written against — review found it
    # holding the identity true by never reaching the list.
    ends_descended: int = 0
    ends_over_grade: int = 0
    ends_no_target: int = 0
    touchdown_grade_pct: list[float] = field(default_factory=list)
    # `Q24`'s, on the at-grade edges the two counters above never reach.
    #
    # ⚠️ `edges_followed` counts edges that took the path, **not** edges that
    # gained a station. Those are wildly different populations — 721 against
    # 217 — because the whole point of the thinning is that a flat street keeps
    # nothing. Copying `edges_sampled`'s `> 0` idiom to here would report a
    # third of the region and call it "edges that follow the ground".
    #
    # `vertices_offered` is the denominator `tolerance_m` moves, and without it
    # `vertices_followed` is a number with nothing to compare against.
    vertices_followed: int = 0
    vertices_offered: int = 0
    edges_followed: int = 0
    # `Q23`'s counter, and the one `surface.py` narrows against. Not derivable
    # from `vertices_sampled`: that counts stations the structure answered
    # *directly*, while this counts stations published as resting on it — which
    # includes everything an interpolated deck spans.
    vertices_on_structure: int = 0
    # `Q19`'s counter, and — unlike the one above — the one `surface.py`
    # deliberately does **not** narrow against. `_half_widths` records why the
    # narrowing this would license was built, measured and refused.
    # ⚠️ **Reachable at zero and at the full station count**, which is how it is
    # tested: `Q72`'s tautology was a counter that read 0 because no
    # configuration could make it anything else. Drop the probe and this reads 0;
    # widen `bound_high_m` past a storey and it approaches every station in the
    # region. Neither is a bar — a *moving* count is a finding to go and look at.
    vertices_structure_bounded: int = 0
    components: list[int] = field(default_factory=list)
    # `P3-13`'s counters. `None` for a city whose sources carry no no-stopping
    # layer, which is not the same as one that carries an empty one.
    kerbside: kerbside.KerbsideReport | None = None
    # `Q95`'s counters. `None` for a city whose file transcribes no design
    # manual, which is not the same as one whose survey measured nothing.
    carriageway: carriageway.CarriagewayReport | None = None

    @property
    def connectivity(self) -> float:
        """Share of nodes in the largest connected component."""
        return max(self.components) / sum(self.components) if self.components else 0.0

    def add(self, counts: _Counts) -> None:
        """Fold one edge's tally in."""
        self.vertices_off_terrain += counts.off_terrain
        self.vertices_added += counts.added
        self.vertices_sampled += counts.sampled
        self.vertices_gated += counts.gated
        self.edges_sampled += int(counts.sampled > 0)
        self.ends_lifted += counts.ends_lifted
        self.ends_descended += counts.ends_descended
        self.ends_over_grade += counts.ends_over_grade
        self.ends_no_target += counts.ends_no_target
        self.touchdown_grade_pct += counts.touchdown_grade_pct
        self.vertices_on_structure += counts.on_structure
        self.vertices_structure_bounded += counts.bounded
        self.vertices_followed += counts.followed
        self.vertices_offered += counts.offered
        self.edges_followed += counts.edges_followed


@dataclass
class _Counts:
    """Where one edge's heights came from.

    Returned rather than written straight into `RoadReport`, which is the
    convention `_heights` already set and the samplers were breaking. It also
    keeps them callable from a test without building a report to inspect —
    and the three functions carrying `P2-7`'s decisions are the ones that most
    need to be.
    """

    off_terrain: int = 0
    added: int = 0
    sampled: int = 0
    gated: int = 0
    ends_lifted: int = 0
    ends_descended: int = 0
    ends_over_grade: int = 0
    ends_no_target: int = 0
    touchdown_grade_pct: list[float] = field(default_factory=list)
    on_structure: int = 0
    # `Q19`'s counter. Kept apart from `on_structure` rather than folded in, for
    # the reason the two flags are kept apart: one number covering both would
    # report a walled ramp as a deck.
    bounded: int = 0
    # `Q24`'s stations, kept apart from `added` rather than folded into it: the
    # two are added for different reasons on different edges, and one number
    # covering both would report the at-grade work as deck sampling.
    #
    # `offered` is what the resample inserted before thinning and `followed` is
    # what survived it; `edges_followed` is 1 for an edge that took the path at
    # all, which is not the same as one that gained a station.
    followed: int = 0
    offered: int = 0
    edges_followed: int = 0


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def simplify(points: np.ndarray, tolerance_m: float) -> np.ndarray:
    """Douglas-Peucker: drop vertices no further than `tolerance_m` off the line.

    Endpoints are always kept, which is what makes this safe to run before node
    snapping — the coordinates two edges meet at are exactly the ones this
    cannot move.

    Iterative rather than recursive: an over-densified centreline here runs to
    54,330 vertices, and the recursion depth that produces is a stack overflow
    on nearly-collinear input, which is precisely the input that produces it.
    """
    return points[simplify_mask(points, tolerance_m)]


def simplify_mask(points: np.ndarray, tolerance_m: float) -> np.ndarray:
    """Which vertices `simplify` keeps, as a boolean mask.

    Split out because `Q24` thins a *height profile* and then has to apply the
    answer to the plan positions those heights were sampled at — so it needs the
    selection, not the selected points. Recovering the mask by matching returned
    rows back to their sources would be a float comparison standing in for an
    identity the algorithm already knows.
    """
    if tolerance_m <= 0.0 or len(points) < 3:
        return np.ones(len(points), dtype=bool)

    keep = np.zeros(len(points), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        offsets = _perpendicular_distance(points[start + 1 : end], points[start], points[end])
        worst = int(offsets.argmax())
        if offsets[worst] > tolerance_m:
            split = start + 1 + worst
            keep[split] = True
            stack.append((start, split))
            stack.append((split, end))
    return keep


def resample(plan: np.ndarray, spacing_m: float) -> np.ndarray:
    """A plan polyline with stations inserted until no two are `spacing_m` apart.

    Every existing vertex is kept to the bit and only interior stations are
    added, so the line's shape in plan is untouched: this exists to ask the
    height field more questions along the same road, not to redraw it. Restating
    the line at evenly spaced stations instead — the obvious way to write this —
    would discard exactly the vertices `simplify` has just finished deciding are
    load-bearing, and cut every corner it left in.

    Justified by the worst vertex gap rather than the typical one. `P2-7`
    measured off-grade spacing at median 10.8 m, and sampling at today's
    vertices alone already clears the ±0.5 m criterion at p90. What it does not
    clear is the maximum: a 71.5 m gap on `FLEMING ROAD` spans structure
    climbing 4.25 to 5.05 m, a chord across it is 4.84 m out, and that is the
    defect the `P2-5` drive found. p90 hides it; the maximum is the acceptance.

    Station count is `edge length / spacing_m` with no ceiling, so this is the
    one place a mistyped `resample_m` in a city file turns into an allocation
    rather than an error. `config.py` refuses zero and negatives, which bounds
    it in practice; nothing bounds a typed `0.01`.
    """
    return resample_anchored(plan, spacing_m)[0]


def resample_anchored(plan: np.ndarray, spacing_m: float) -> tuple[np.ndarray, np.ndarray]:
    """`resample`, and where each of the *original* vertices ended up in it.

    ⚠️ **The arithmetic `resample` documents lives here** — both traps it names
    are properties of this body: only interior stations are added, so a line's
    plan shape is untouched; and the station count is `edge length / spacing_m`
    with no ceiling, so a mistyped `resample_m` becomes an allocation rather
    than an error.

    The anchors are split out because `Q24` thins the stations back down and
    must not thin away a vertex `simplify` decided was load-bearing in plan.
    Knowing which they are is the whole of what makes that safe, and the indices
    are a by-product of the arithmetic below — recovering them afterwards would
    mean comparing floats for an identity this function already has.
    """
    if spacing_m <= 0.0 or len(plan) < 2:
        return plan, np.arange(len(plan))

    steps = plan_steps_2d(plan)
    # At least one piece per segment, so a repeated vertex survives rather than
    # dividing by zero on its way to being dropped.
    pieces = np.maximum(np.ceil(steps / spacing_m).astype(np.int64), 1)
    # The exclusive prefix sum of `pieces` is where each segment's own start
    # vertex lands, and the total is where the final vertex does — so `anchors`
    # is that prefix sum with the end appended, and the two uses below are one
    # array rather than two spellings of it.
    anchors = np.concatenate([np.cumsum(pieces) - pieces, [int(pieces.sum())]])
    if not (pieces > 1).any():
        return plan, anchors

    # Each new station's position within its own segment, as a fraction. The
    # subtracted term is that same prefix sum — the idiom `terrain.py` spreads
    # triangles across cells with, and for the same reason: a Python loop over
    # segments is what this stage cannot afford per edge.
    starts = np.repeat(np.arange(len(steps)), pieces)
    within = np.arange(anchors[-1]) - np.repeat(anchors[:-1], pieces)
    fraction = (within / np.repeat(pieces, pieces))[:, None]
    # Fraction zero reproduces the original vertex exactly, which is what makes
    # "every vertex is kept" true rather than approximately true.
    stations = plan[starts] + fraction * (plan[starts + 1] - plan[starts])
    return np.vstack([stations, plan[-1]]), anchors


def clip(points: np.ndarray, high: tuple[float, float], *, min_length_m: float) -> list[np.ndarray]:
    """The runs of a polyline that lie inside `(0, 0)`-`high`, in game plan metres.

    Roads are cut at the region boundary rather than kept whole the way
    buildings are. A building overhanging its tile is half a footprint; a road
    feature overhanging the region is the Central-Wan Chai Bypass, which enters
    the geodatabase's spatial filter because its bounding box grazes the region
    and then runs 570 m out into the harbour. Left whole, 14.2% of the region's
    road length would be geometry no one can drive on — and `P1-4` would build
    a ribbon mesh for all of it.

    Cutting is safe here in a way it is not for a mesh: a polyline cut in two is
    two polylines, with no open shell and nothing to seam. The cut point becomes
    an ordinary endpoint node, which is what the map edge should be anyway.

    Runs shorter than `min_length_m` are dropped — a feature clipping a corner
    of the region contributes a stub no vehicle can occupy.
    """
    if len(points) < 2:
        # A NULL or single-vertex geometry is legal in a geodatabase and is not
        # a road. Returned as nothing here rather than allowed through, because
        # the caller indexes `[0]` and `[-1]` to find the edge's end nodes.
        return []

    runs: list[np.ndarray] = []

    # The overwhelming majority of centrelines are wholly inside, and the walk
    # below is a Python loop over every vertex — 175,610 of them in this region,
    # three quarters belonging to five over-densified features that never leave
    # it. Testing the whole array first keeps that off the slow path. It still
    # goes through `_close`, so the minimum length is one rule rather than two.
    if points.min() >= 0.0 and points[:, 0].max() <= high[0] and points[:, 1].max() <= high[1]:
        _close(runs, points, min_length_m)
        return runs

    current: list[np.ndarray] = []
    for start, end in itertools.pairwise(points):
        span = _segment_inside(start, end, high)
        if span is None:
            _close(runs, current, min_length_m)
            current = []
            continue

        enter, leave = start + span[0] * (end - start), start + span[1] * (end - start)
        if not current:
            current = [enter]
        elif abs(current[-1][0] - enter[0]) > _JOIN_EPSILON_M or (
            abs(current[-1][1] - enter[1]) > _JOIN_EPSILON_M
        ):
            # The line left the region and came back within one segment.
            _close(runs, current, min_length_m)
            current = [enter]
        current.append(leave)

    _close(runs, current, min_length_m)
    return runs


def _close(
    runs: list[np.ndarray], current: Sequence[np.ndarray] | np.ndarray, min_length_m: float
) -> None:
    if len(current) < 2:
        return
    run = np.asarray(current)
    if float(plan_steps_2d(run).sum()) >= min_length_m:
        runs.append(run)


def _segment_inside(
    start: np.ndarray, end: np.ndarray, high: tuple[float, float]
) -> tuple[float, float] | None:
    """Liang-Barsky: the parameter interval of a segment inside the rectangle."""
    delta = end - start
    lower, upper = 0.0, 1.0
    for axis in (0, 1):
        for gradient, offset in (
            (-delta[axis], start[axis]),
            (delta[axis], high[axis] - start[axis]),
        ):
            if gradient == 0.0:
                # Parallel to this edge: either wholly on the right side or not
                # in the rectangle at all, and no interval to narrow.
                if offset < 0.0:
                    return None
                continue
            crossing = offset / gradient
            if gradient < 0.0:
                if crossing > upper:
                    return None
                lower = max(lower, crossing)
            else:
                if crossing < lower:
                    return None
                upper = min(upper, crossing)
    return (lower, upper) if lower < upper else None


def _perpendicular_distance(points: np.ndarray, start: np.ndarray, end: np.ndarray) -> np.ndarray:
    line = end - start
    length = float(np.hypot(*line))
    if length == 0.0:
        # A closed segment has no line to measure against, so fall back to
        # distance from the shared endpoint. Without this a loop road — a
        # roundabout drawn as one feature — collapses to nothing.
        return np.hypot(*(points - start).T)
    # The 2D cross product, written out: `np.cross` dropped support for
    # 2-vectors in numpy 2.0.
    offset = points - start
    return np.abs(line[0] * offset[:, 1] - line[1] * offset[:, 0]) / length


# --------------------------------------------------------------------------
# Attributes
# --------------------------------------------------------------------------


def clean_text(value: object, null_values: Sequence[str]) -> str | None:
    """A source text field as a string, or None where it means "no value".

    The null sentinel arrives in four spellings in this data — `-99`, and three
    variants using full-width digits and an en-dash. NFKC folds the full-width
    forms; the dash has to be folded by hand, because Unicode quite reasonably
    does not consider an en-dash a hyphen.

    The value returned is NFC, and only the *comparison* is NFKC. NFKC is a
    compatibility fold, so it also rewrites the full-width brackets Chinese
    text sets its parentheticals in as their narrow ASCII equivalents. That is
    wrong typography in 98 of the fare-node names `P1-5` reads, and those names
    go on a bilingual HUD; `test_fares.py` pins the case. No road name in the
    region is affected — all 198 are already NFC.

    Internal whitespace runs collapse to a single space. Not cosmetic either:
    the taxi datasets wrap long place names across lines, so `Location_EN`
    arrives with newlines inside it in 31 of the territory's 793 points.
    """
    if value is None:
        return None
    text = " ".join(unicodedata.normalize("NFC", str(value)).split())
    if not text:
        return None
    compatible = unicodedata.normalize("NFKC", text)
    folded = "".join("-" if unicodedata.category(ch) == "Pd" else ch for ch in compatible)
    return None if folded in null_values else text


def parse_speed_limit(value: object, default_kph: int) -> int:
    """Kilometres per hour from a text field like "70 km/h".

    Matched from the start of the string, not searched for anywhere in it: the
    field is free text, and a label like "Route 4, 70 km/h" would otherwise read
    as a 4 km/h speed limit rather than falling back to the city default.
    """
    if value is None:
        return default_kph
    match = _LEADING_INTEGER.match(str(value))
    return int(match.group(1)) if match else default_kph


# --------------------------------------------------------------------------
# Building the graph
# --------------------------------------------------------------------------


class _Nodes:
    """Endpoints to node ids, by exact coordinate identity.

    Deliberately not keyed on `ELEVATION`. Every one of the 36 endpoints in Wan
    Chai where two levels meet is a ramp touching down — `HUNG HING ROAD
    FLYOVER` at level 1 meeting itself at level 0, and so on. Adding the level
    to the key takes the region from 6 connected components to 24 and cuts a
    163-node elevated island adrift. `docs/DATA_SOURCES.md` says two edges may
    only form a junction if their levels match; that is right about *crossings*,
    which this never creates, and wrong about junctions.

    Identity is plan-only, and deliberately carries no height. That is what lets
    `build_region` name every node before it knows how high any of them are,
    which `P2-7` needs: a level-0 edge is lifted onto its ramp only where it
    meets a node another level also reaches, and which nodes those are is not
    known until every centreline has been read. `_node_heights` fills the gap
    afterwards.
    """

    def __init__(self) -> None:
        self._ids: dict[tuple[float, float], int] = {}

    def id_for(self, x: float, z: float) -> int:
        key = (round(x, _SNAP_DECIMALS), round(z, _SNAP_DECIMALS))
        if key not in self._ids:
            self._ids[key] = len(self._ids)
        return self._ids[key]

    def positions(self, heights: Sequence[float]) -> list[tuple[float, float, float]]:
        """Node positions in id order, given a height for each id."""
        return [(x, heights[index], z) for (x, z), index in self._ids.items()]

    def __len__(self) -> int:
        return len(self._ids)


@dataclass(frozen=True)
class _Pending:
    """One clipped, simplified run, held until the graph's levels are known.

    ⚠️ `edge.polyline` and `edge.on_structure` are empty until `_shaped` fills
    them, and they are the only fields that are not already final. Empty rather
    than provisional on purpose:
    a placeholder height is a plausible number that would survive a missed
    assignment, whereas an empty list cannot be mistaken for geometry and
    `_node_heights` indexes `polyline[0]` on every edge — so a run that somehow
    escaped the second pass raises there rather than shipping a flat road.
    """

    edge: Edge
    plan: np.ndarray


@dataclass(frozen=True)
class _Deck:
    """The structure to sample and the thresholds for reading it, both present.

    A type rather than a convention. The alternative — three optional fields and
    a `samples_structure` flag the samplers trust their caller to have checked —
    makes "this city samples decks" something each sampler has to re-assert, and
    an assertion is what you write when the shape cannot say it. Narrowing
    `_Surfaces.deck` once says it for every caller downstream.
    """

    field: HeightField
    thresholds: DeckSampling
    # What `elevation_levels` maps level 0 to: the height a touchdown descends
    # *to* (`Q90`). The one quantity a deck sampler needs that is not about the
    # deck, and it is here rather than a fifth argument to `_measured` because
    # the descent is deck sampling — it exists only where a deck stops.
    #
    # Read from the city rather than assumed zero because the target is the
    # **unlifted** street, which is `_from_terrain`'s `terrain + deck_m` at level
    # 0 — so a city that puts level 0 anywhere but zero would otherwise land its
    # ramps that far off the road they meet. ⚠️ Not `_lifted_heights`' reasoning,
    # which says the opposite about its own end: a *lifted* end deliberately does
    # not add the flat offset, because it is resting on a ramp deck rather than
    # on the ground the offset is measured from.
    level_zero_m: float

    def floor(self, terrain: np.ndarray) -> np.ndarray:
        """The lowest a structure sample may sit and still be a deck.

        One expression shared by both samplers, which reach it by different
        routes — one rejects what falls below it, the other asks for the lowest
        slab above it. Written twice they would drift silently, and a wrong
        floor changes heights without changing anything that looks like an error.
        """
        return terrain - self.thresholds.max_below_terrain_m


@dataclass(frozen=True)
class _Surfaces:
    """What the road stage samples heights from, and how closely.

    All three are optional and independently so: a city may take its heights
    from the terrain without sampling decks or following the ground, and
    `load_config` refuses either of the latter two without the first.

    `profile` is thresholds rather than a field because it has no geometry of
    its own — it says how finely to ask `ground`, which is why it sits here
    beside it rather than pairing with a field the way `_Deck` does.
    """

    ground: HeightField | None
    deck: _Deck | None
    profile: GroundProfile | None


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> RoadReport:
    """Read the region's roads and write its `roadgraph.json`."""
    style = city.roads
    bounds = city.projected_bounds(region_id)
    transform = city.game_transform(region_id)

    source = _Source(
        path=cached_source(city, style.source, root=sources_root),
        city=city,
        bbox=bounds.bbox,
    )
    centrelines = source.read(style.centrelines)
    owners, parts = gdb.polylines(centrelines)

    region_high = city.region_high(region_id)

    surfaces = _surfaces(city, region_id, sources_root, region_high)
    report = RoadReport(read=len(parts))
    nodes = _Nodes()

    speed_limits, bus_lanes = _route_overlays(source, style)
    route = centrelines.column(style.centrelines.field("route"))
    elevation = centrelines.column(style.centrelines.field("elevation"))
    direction_code = centrelines.column(style.centrelines.field("travel_direction"))
    name_en = centrelines.column(style.centrelines.field("name_en"))
    name_zh = centrelines.column(style.centrelines.field("name_zh"))

    # Read, clipped and named in one pass; measured in a second. The seam is
    # forced by `P2-7`: whether a level-0 edge sits on a ramp depends on whether
    # its node is also reached by another level, and no edge can know that until
    # every edge has been placed. `_Nodes` keys on plan position alone, so node
    # *identity* survives the split intact and only heights wait.
    pending: list[_Pending] = []
    edges_of_source: dict[int, list[int]] = {}
    for owner, points in zip(owners, parts, strict=True):
        report.vertices_read += len(points)

        level = int(elevation[owner])
        direction = _direction(style, int(direction_code[owner]), centrelines.name)
        if direction == BACKWARD:
            # Normalised away here so `roadgraph.json` only ever says `forward`.
            points, direction = points[::-1], FORWARD

        english = clean_text(name_en[owner], style.null_values)
        limit = parse_speed_limit(
            speed_limits.get(int(route[owner])), style.default_speed_limit_kph
        )
        lanes = style.lanes_for(limit)
        source_id = int(centrelines.fids[owner])

        game_x, _, game_z = transform.to_game(points[:, 0], points[:, 1])
        plan = np.column_stack([game_x, game_z])
        runs = clip(plan, region_high, min_length_m=style.min_edge_length_m)
        if not runs:
            report.clipped += 1
        for run in runs:
            # Simplified after clipping, so the vertices the cut introduced are
            # endpoints and therefore cannot be moved.
            run = simplify(run, style.simplify_tolerance_m)
            report.vertices_kept += len(run)

            edge_id = len(pending)
            edges_of_source.setdefault(source_id, []).append(edge_id)
            pending.append(
                _Pending(
                    edge=Edge(
                        id=edge_id,
                        source_id=source_id,
                        from_node=nodes.id_for(run[0, 0], run[0, 1]),
                        to_node=nodes.id_for(run[-1, 0], run[-1, 1]),
                        polyline=[],
                        on_structure=[],
                        structure_bounded=[],
                        direction=direction,
                        lanes=lanes,
                        width_m=round(lanes * style.lane_width_m, 3),
                        speed_limit_kph=limit,
                        bus_lane=int(route[owner]) in bus_lanes,
                        tram_tracks=english in style.tram_streets,
                        elevation_level=level,
                        road_name={
                            "en": english,
                            "zh": clean_text(name_zh[owner], style.null_values),
                        },
                    ),
                    plan=run,
                )
            )

    levels = _levels_at_node(item.edge for item in pending)
    for item in pending:
        edge, counts = _measured(
            item, surfaces, city.deck_height_m(item.edge.elevation_level), levels
        )
        report.edges.append(edge)
        report.add(counts)

    heights = _node_heights(len(nodes), report.edges)
    report.nodes = _nodes_with_kind(nodes.positions(heights), report.edges)
    report.turn_restrictions, report.turns_unresolved = _turn_restrictions(
        source, style, report.edges, edges_of_source
    )
    report.components = _components(len(nodes), report.edges)
    _kerbside(source, style, transform, region_high, report)
    _carriageway(city, region_id, transform, report, surfaces.deck)

    _write(out_root, city, region_id, report)
    return report


@dataclass(frozen=True)
class _Source:
    """The region's road geodatabase, and the frame every read is checked against.

    Bundled rather than passed around as three arguments because every read has
    to be checked, and a check that is the caller's job to remember is a check
    that gets forgotten on the fourth layer.
    """

    path: Path
    city: Config
    bbox: gdb.Bbox

    def read(self, layer: SourceLayer) -> gdb.Layer:
        """One configured layer, clipped to the region and known to be in its CRS.

        The bounding box handed to OGR is in the city's projected CRS and OGR
        does not reproject it. Reading Hong Kong coordinates on the wrong datum
        moves them ~304 m — a fifth of the width of this region — and the result
        is a plausible-looking road network somewhere it is not.
        """
        return gdb.read_layer(
            self.path,
            layer.layer,
            columns=layer.columns,
            bbox=self.bbox,
            expect_crs=self.city.projected_crs,
        )


def _kerbside(
    source: _Source,
    style: RoadNetwork,
    transform: GameTransform,
    region_high: tuple[float, float],
    report: RoadReport,
) -> None:
    """Attach each edge's published no-stopping runs (`P3-13`, closes `Q54`).

    Last, and after every edge exists, because the join is geometric rather than
    by key: `NSR` keys on street codes, not on `ROUTE_ID`, so which centreline a
    restriction belongs to is a question about the finished graph. That is the
    whole reason this is not folded into `_route_overlays` beside the speed
    limits and the bus lanes, where a reader would look for it first.

    ⚠️ **Only level-0 edges are offered.** A kerb is a thing at ground level,
    and the alternative was measured rather than assumed — `pipeline/kerbside.py`
    has the 7% and the 4.0 m that decided it.
    """
    if style.kerbside is None:
        return
    tracks = [
        (edge.id, np.asarray(edge.polyline, dtype=np.float64))
        for edge in report.edges
        if edge.elevation_level == 0 and len(edge.polyline) > 1
    ]
    found = kerbside.build(
        source.read(style.kerbside.layer), style.kerbside, transform, region_high, tracks
    )
    report.kerbside = found

    runs: dict[int, list[kerbside.Restriction]] = defaultdict(list)
    for item in found.restrictions:
        runs[item.edge].append(item)
    report.edges = [replace(edge, kerbside=tuple(runs.get(edge.id, ()))) for edge in report.edges]


def _carriageway(
    city: Config,
    region_id: str,
    transform: GameTransform,
    report: RoadReport,
    deck: _Deck | None = None,
) -> None:
    """Replace the authored `width_m` with what the publishers drew (`Q95`).

    After `_kerbside` and for the same reason it is last: the survey is a
    geometric join, and a station has to know which graph nodes are near it,
    which needs every edge to exist. ⚠️ It also has to run **before** `_write`,
    so `roadgraph.json` is published once carrying the final width rather than
    written and then corrected by a later stage.

    ⚠️ **The authored value stays wherever nothing licensed a measurement**, and
    that is most of the region — a width is assigned only where a single
    publisher spanned the road at three or more non-junction stations and the
    span survived TD's own bounds. Silence is not evidence of a narrow street.
    """
    if city.carriageway_survey is None or city.carriageway_survey.width_bounds is None:
        return
    nodes = np.array([node.pos for node in report.nodes], dtype=np.float64)
    found = carriageway.measure(
        city,
        region_id,
        transform,
        report.edges,
        nodes[:, [0, 2]] if len(nodes) else np.empty((0, 2)),
        # ⚠️ **The same field this stage already built for the polyline's own
        # height** (`_deck_heights`), handed on rather than re-read. It is the
        # only source that knows where a viaduct deck is, and re-indexing 74
        # source meshes to ask it a second question would cost the build for
        # nothing (`Q103`).
        deck=(deck.field, deck.thresholds.slab_gap_m, deck.thresholds.clearance_m)
        if deck is not None
        else None,
    )
    report.carriageway = found
    report.edges = [_reassign(edge, found) for edge in report.edges]


def _reassign(edge: Edge, found: carriageway.CarriagewayReport) -> Edge:
    """Carry the survey's readings onto one edge, each field independently.

    ⚠️ **The lane count is a strict SUBSET of the widths, not a second name for
    them** (`Q94`). A width is licensed wherever a publisher spanned the road;
    a count is published only where TD's 3.0-3.65 m through-lane range resolves
    that width to one integer, which it does on rather over half of them. So an
    edge may perfectly well carry a measured width and an authored count, and
    the two `_source` fields are what say so.
    """
    changes: dict[str, object] = {}
    if edge.id in found.assigned_m:
        changes = {
            "width_m": round(found.assigned_m[edge.id], 3),
            "width_source": found.basis[edge.id],
            "width_publisher": found.publishers[edge.id],
        }
        if edge.id in found.lanes:
            changes["lanes"] = found.lanes[edge.id]
            changes["lanes_source"] = found.lanes_basis[edge.id]

    # ⚠️ **A separate licence from the publishers' above, not a fallback to
    # them.** The deck answers where they are silent *and* where they are
    # wrong — off-grade their 2D lines find the street underneath — so an edge
    # may carry a deck width having been spanned by nobody, which is most of the
    # off-grade network (36 edges against their 5).
    if edge.id in found.deck_span_m:
        changes["width_m"] = round(found.deck_span_m[edge.id], 3)
        changes["width_source"] = "deck"
        changes["width_publisher"] = ""
        # 🔴 **The one negation, by name.** `carriageway._stations` emits the
        # RIGHT normal and `surface.mitres` the LEFT one; the two are opposite
        # on purpose (`CLAUDE.md`) and this is where the difference is paid,
        # once, rather than by every reader.
        changes["offset_m"] = round(-found.deck_offset_m[edge.id], 3)
        changes["offset_source"] = "deck"
        # ⚠️ **No negation here, deliberately, where the line above needs one.**
        # `offset_m` is signed and crosses between two opposite normals;
        # `deck_rim_m` is a pair of unsigned reaches already named for their
        # side of travel, so it carries its own frame — `_rims_at_vertices` says
        # so in full. A second negation applied here would mirror every
        # off-grade carriageway and render as a city.
        changes["deck_rim_m"] = tuple(
            (round(left, 3), round(right, 3)) for left, right in found.deck_rim_m[edge.id]
        )
        # 🔴 **The deck is a CEILING on the lane count, never a source of one**
        # (`Q114`). Off-grade there is no lane-count evidence — no turn arrows
        # are painted on a bridge deck and the line publishers' 2D rays find the
        # street underneath — so `lanes` is `lanes_for(speed_limit)`, and that
        # table read `e306` CANAL ROAD FLYOVER's 70 kph as three lanes over a
        # 5.80 m deck, which `road_markings.gdshader` painted as 1.15 m strips.
        # What is licensed here is only the refusal: paint cannot be wider than
        # the structure under it, which is the licence `Q107` already took to
        # cut the ribbon to `deck_rim_m`.
        #
        # ⚠️ **Composed with whatever stands, not with `edge.lanes`.** A ray
        # licence above may already have published a count for this edge; the
        # cap has to apply to that rather than to the authored number it
        # replaced, or the two rules would fight over which ran last.
        # ⚠️ **`get`, not an index**: a deck too narrow to hold one through lane
        # licenses no ceiling at all (`_deck_lane_ceiling`), so this key is
        # absent where the other three deck fields are present. It is the one
        # deck field that is not all-or-none with the rest.
        ceiling = found.deck_lane_ceiling.get(edge.id)
        standing = int(changes.get("lanes", edge.lanes))
        if ceiling is not None and standing > ceiling:
            changes["lanes"] = ceiling
            changes["lanes_source"] = "deck_capped"
    if not changes:
        return edge
    return replace(edge, **changes)


def _direction(style: RoadNetwork, code: int, layer: str) -> str:
    if code not in style.travel_directions:
        known = ", ".join(str(k) for k in sorted(style.travel_directions))
        raise KeyError(
            f"layer '{layer}' has travel direction {code}, which the city maps no "
            f"direction for. Mapped: {known}"
        )
    return style.travel_directions[code]


def _levels_at_node(edges: Iterable[Edge]) -> dict[int, set[int]]:
    """Which elevation levels meet at each node.

    A node reached by more than one is `Q13`'s, and all 36 of the region's are
    ramps — 17 where the structure already reaches grade at the node, 13 where
    the publisher's `ELEVATION` attribute flips partway up, 5 tunnel portals and
    one stub. The 13 are why the level-0 side needs anything done to it at all:
    there the at-grade edge is itself 2.1 to 4.0 m up the ramp, drawn at ground
    level.

    ⚠️ **The levels rather than a "mixed" flag, because the two ramp ends ask
    different questions of the same node.** `_lifted_heights` asks whether
    *another* level is here, and `_descend` asks whether **level 0** is — it
    descends to the street, so a node without one has nothing to land on. Every
    mixed node in Wan Chai is `(-1, 0)` or `(0, 1)`, which makes the two agree
    here and is exactly why a flag would survive review: `elevation_levels`
    declares a level 2, and a `(1, 2)` node would send a descent to a street
    that is not there.
    """
    levels: dict[int, set[int]] = defaultdict(set)
    for edge in edges:
        levels[edge.from_node].add(edge.elevation_level)
        levels[edge.to_node].add(edge.elevation_level)
    return levels


def _ramp_ends(edge: Edge, levels: dict[int, set[int]]) -> tuple[bool, bool]:
    """Which of this edge's ends sit where a ramp changes level.

    Level -1 is a tunnel, which is a void — its portals are mixed nodes and
    there is no structure under them to find. `Q21` asks whether they should be
    drawn at all; nothing here can improve their height, and excluding them is
    what keeps `_lifted_heights` off them.
    """
    if edge.elevation_level < 0:
        return (False, False)
    reaches = (
        (lambda node: len(levels[node]) > 1)
        if edge.elevation_level == 0
        else (lambda node: 0 in levels[node])
    )
    return (reaches(edge.from_node), reaches(edge.to_node))


def _follow_ground(
    plan: np.ndarray, ground: HeightField, profile: GroundProfile
) -> tuple[np.ndarray, np.ndarray, int]:
    """Stations along an at-grade run dense enough to follow the ground, the
    ground under them, and how many stations the thinning was offered (`Q24`).

    Densify, ask the terrain, then drop the stations the straight line between
    their neighbours already explains. The thinning is what makes this cheap:
    densifying alone doubles the region's level-0 stations to take the
    carriageway sitting under proud ground from 1.797% to 0.107%, and thinning
    at 0.10 m reaches 0.110% for **+12%**. Wan Chai is mostly flat, and a flat
    street needs no vertex it does not already have.

    ⚠️ **Thinned between consecutive original vertices, never across them.**
    `simplify` keeps only its two endpoints, so one pass over the whole profile
    would drop source vertices that `simplify` has already decided are
    load-bearing *in plan* — the same trap `resample` records about restating a
    line at evenly spaced stations, arrived at from the other side. Running it
    per span, with the originals as the endpoints, makes their survival a
    property of the construction rather than something to check for.

    The profile is `(distance along the plan, sampled height)`, so `tolerance_m`
    is a vertical error in metres and means what the city file's table measured.

    A station the terrain does not cover carries no information to follow, so
    the holes are interpolated across for the *decision* only. The heights
    handed back are the raw samples, NaNs included, because `_from_terrain` is
    what fills them and it counts them on the way past. A span the terrain
    answers for fewer than twice keeps its ends and nothing else: one height
    describes no shape to follow, and inserting stations would invent detail.

    ⚠️ **The heights come back rather than being sampled again.** 97% of this
    function's cost is `HeightField.sample`, so asking it a second question
    about the stations that survived would be a third of the total for an answer
    already in hand — and two samplings of one point are also two chances to
    disagree.

    ⚠️ **Sampled before the no-gain test, which is not an oversight.** Where a
    run is already dense enough, `resample_anchored` hands back `plan` itself,
    so those are the plan's own stations and their heights are exactly what
    `_heights` would have had to compute anyway. Testing first would only force
    a second sample below. Measured: 104 of 692 edges take that path.
    """
    dense, anchors = resample_anchored(plan, profile.resample_m)
    y = ground.sample(dense[:, 0], dense[:, 1])
    offered = len(dense) - len(plan)
    if not offered:
        return plan, y, 0

    along = plan_lengths_2d(dense)
    keep = np.zeros(len(dense), dtype=bool)
    keep[anchors] = True
    for start, end in itertools.pairwise(anchors):
        if end - start < 2:
            continue
        span = y[start : end + 1]
        found = np.isfinite(span)
        if found.sum() < 2:
            continue
        span = np.interp(np.arange(len(span)), np.flatnonzero(found), span[found])
        keep[start : end + 1] |= simplify_mask(
            np.column_stack([along[start : end + 1], span]), profile.tolerance_m
        )
    return dense[keep], y[keep], offered


def _measured(
    item: _Pending, surfaces: _Surfaces, deck_m: float, levels: dict[int, set[int]]
) -> tuple[Edge, _Counts]:
    """One pending run with its heights, and a tally of where they came from.

    The four sources are chosen here rather than inside one branching height
    function, so what decides between them stays visible: the level, whether the
    edge meets a node another level also reaches, and — since `Q24` — whether
    the city asked at-grade roads to follow the ground.
    """
    level = item.edge.elevation_level
    ground, deck = surfaces.ground, surfaces.deck
    # Opposite ends of the same ramp, and `_ramp_ends` asks each its own
    # question: level 0 whether to *lift* this end onto a structure that reaches
    # past the node, level 1 and above whether to *descend* it to the street the
    # structure stops short of.
    ends = _ramp_ends(item.edge, levels) if deck is not None else (False, False)

    # One guard, so "sampling" is decided once rather than derived here and
    # negated again below — and so both fields are narrowed for everything after.
    if deck is None or ground is None or (level <= 0 and not any(ends)):
        # `Q24` follows the ground where there is ground to follow and the city
        # asked for it, and **level 0 only**. Every other level rides a flat
        # offset above or below the terrain, so following its shape would be a
        # change nothing has measured and nothing can see: a tunnel has no drawn
        # surface to fight, and an off-grade edge only reaches this branch when
        # the city declared no deck sampling at all.
        if ground is not None and surfaces.profile is not None and level == 0:
            plan, terrain, offered = _follow_ground(item.plan, ground, surfaces.profile)
            y, off_terrain = _from_terrain(terrain, deck_m)
            counts = _Counts(
                off_terrain=off_terrain,
                followed=len(plan) - len(item.plan),
                offered=offered,
                edges_followed=1,
            )
        else:
            y, counts = _heights(ground, item.plan, deck_m)
            plan = item.plan
        # 🔴 **The probe runs on THIS branch too, and that is the whole point.**
        # Every station here is off structure by construction — the branch is
        # taken when no deck was sampled — so `Q23`'s flag is all-False and its
        # suppression short-circuits. `e233`, `e55`, `e398`, `e207` and `e781`
        # are all here, and between them they carry every long unbroken blockage
        # in the region (`Q19`).
        bounded = _structure_bounded(deck, plan, y)
        counts.bounded = int(bounded.sum())
        return _shaped(item.edge, plan, y, np.zeros(len(plan), dtype=bool), bounded), counts

    plan = resample(item.plan, deck.thresholds.resample_m)
    terrain = ground.sample(plan[:, 0], plan[:, 1])
    fallback, off_terrain = _from_terrain(terrain, deck_m)
    counts = _Counts(off_terrain=off_terrain, added=len(plan) - len(item.plan))

    if level > 0:
        y, on_structure = _deck_heights(deck, plan, terrain, fallback, ends, counts)
    else:
        y, on_structure = _lifted_heights(deck, plan, terrain, fallback, ends, counts)
    counts.on_structure = int(on_structure.sum())
    bounded = _structure_bounded(deck, plan, y)
    counts.bounded = int(bounded.sum())
    return _shaped(item.edge, plan, y, on_structure, bounded), counts


def _shaped(
    edge: Edge,
    plan: np.ndarray,
    y: np.ndarray,
    on_structure: np.ndarray,
    structure_bounded: np.ndarray,
) -> Edge:
    """The pending edge with its polyline and its two structure flags filled in.

    See `_Pending`. Height and `on_structure` are filled together because they
    are one answer read twice: a station's height and what that height was
    measured from. `structure_bounded` is a **third** answer to a **different**
    question — see `_structure_bounded` — and it is filled here only because
    this is where a station stops moving.
    """
    return replace(
        edge,
        polyline=[
            (float(x), float(height), float(z))
            for x, height, z in zip(plan[:, 0], y, plan[:, 1], strict=True)
        ],
        on_structure=[bool(flag) for flag in on_structure],
        structure_bounded=[bool(flag) for flag in structure_bounded],
    )


def _structure_bounded(deck: _Deck | None, plan: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Whether structure stands beside each station, at the height a bumper meets.

    Answers `Q19`'s structure half. ⚠️ **This is not `on_structure` and must not
    be folded into it.** That flag says where a station's *height* came from;
    this says what is standing next to it. They coincide on a viaduct and come
    apart on its approach ramp, which is precisely the population that blocks:
    `e233` (0 of 17 stations on structure), `e55` (0 of 36) and `e398` (0 of 35)
    are walled ramps whose heights came from terrain, so `Q23`'s suppression
    never fired and `surface.py` drew them at the 10.24-12.48 m floor over
    surveyed carriageways of 5.42, 5.57 and 6.66 m.

    🔴 **A vertical ray cannot find a wall, and this does not try to.**
    `HeightField.from_meshes` drops near-vertical triangles outright, so a
    parapet's *side* is not in the index at all and a point-in-plan test would
    hit it with probability zero — the trap `carriageway_occupancy.py`'s header
    records against `Faces.heights_at`. What this finds is the parapet's **top**,
    which is horizontal, indexed, and is why a viaduct being a closed volume is
    load-bearing rather than incidental.

    🔴 **The low bound is what keeps this off `Q23`'s refusal.** `Q23` measured
    a vertical question and concluded *"a street on an abutment is a street"*,
    leaving 546 m deliberately wide. An abutment a road rests **on** answers this
    probe at the ribbon's own height, so `bound_low_m` excludes it by
    construction rather than by a rule that has to remember to.

    ⚠️ **`sample_lowest_above` returns a slab TOP.** A viaduct crossing overhead
    therefore answers with its deck rather than its soffit, several metres up and
    outside `bound_high_m` — which is what stops an ordinary street being
    narrowed for passing under one.
    """
    if deck is None or len(plan) < 2:
        return np.zeros(len(plan), dtype=bool)

    thresholds = deck.thresholds
    # Central differences, so an interior station's lateral follows the curve
    # rather than one of the two segments meeting at it. A zero-length step —
    # `dedupe` runs before this, but a resampled curve can still fold — normalises
    # to zero rather than raising, and `usable` then drops it: an unrotated zero
    # would probe the centreline and find the road the station is already on.
    #
    # ⚠️ Not `surface.mitres`, which is the repo's other centreline offset. That
    # one returns a *mitre-joined* vector, extended at a corner so ribbon quads
    # meet exactly; this wants a plain unit perpendicular. It would also close an
    # import cycle — `surface.py` imports this module.
    #
    # ⚠️ **`carriageway._stations` takes the opposite choice and both are right.**
    # It uses the *segment* normal, because "a ray cast off a smoothed direction
    # can leave the carriageway at a bend and find the wrong kerb" — it measures
    # one distance and a few degrees move it. This ORs a hit over 52 offsets on
    # both sides, so an angle error shifts which offset lands on the wall rather
    # than what is found; and it probes at the published vertices, where two
    # segments meet and there is no single segment normal to take.
    tangent = normalise(np.gradient(plan, axis=0))
    usable = np.any(tangent != 0.0, axis=1)
    lateral = np.column_stack([-tangent[:, 1], tangent[:, 0]])

    # Both signs, and the centreline itself is never probed: a station is
    # bounded by what stands *beside* it, and the road it is on is not a wall.
    steps = np.arange(thresholds.bound_step_m, thresholds.bound_reach_m, thresholds.bound_step_m)
    offsets = np.concatenate([-steps[::-1], steps]) if len(steps) else np.array([])

    bounded = np.zeros(len(plan), dtype=bool)
    if not len(offsets):
        return bounded

    # One call for the whole edge rather than one per offset: `sample_lowest_above`
    # loops per point in Python, and the loop is the cost whichever way it is fed.
    x = (plan[:, 0][:, None] + lateral[:, 0][:, None] * offsets[None, :]).ravel()
    z = (plan[:, 1][:, None] + lateral[:, 1][:, None] * offsets[None, :]).ravel()
    floor = np.repeat(y + thresholds.bound_low_m, len(offsets))
    tops = deck.field.sample_lowest_above(x, z, floor, slab_gap_m=thresholds.slab_gap_m)

    ceiling = np.repeat(y + thresholds.bound_high_m, len(offsets))
    hit = np.isfinite(tops) & (tops <= ceiling)
    return hit.reshape(len(plan), len(offsets)).any(axis=1) & usable


def _heights(
    ground: HeightField | None, plan: np.ndarray, deck_m: float
) -> tuple[np.ndarray, _Counts]:
    """Deck height per vertex, and a tally of those with no terrain under them.

    Resolves `Q11`. `elevation_levels` was always an offset per grade-separation
    level; what was missing was what it is an offset *from*. Taking it from the
    vertical datum puts every at-grade road four metres below the doorways on
    it, because Wan Chai's ground is not at the datum.
    """
    if ground is None:
        return np.full(len(plan), deck_m), _Counts()
    y, off_terrain = _from_terrain(ground.sample(plan[:, 0], plan[:, 1]), deck_m)
    return y, _Counts(off_terrain=off_terrain)


def _from_terrain(terrain: np.ndarray, deck_m: float) -> tuple[np.ndarray, int]:
    """The level's flat offset above sampled ground, with the holes filled.

    Split from `_heights` so the two structure samplers can reuse it as their
    fallback without sampling the terrain a second time — they need the raw
    terrain anyway, to gate their own answer against.
    """
    missing = ~np.isfinite(terrain)
    if not missing.any():
        return terrain + deck_m, 0

    # The median of what *was* sampled on this edge, or the region's ground
    # floor if the whole edge missed. Better than zero, and the count is
    # returned so a terrain that stops covering the region is visible.
    fill = np.nanmedian(terrain) if np.isfinite(terrain).any() else 0.0
    return np.where(missing, fill, terrain) + deck_m, int(missing.sum())


def _deck_heights(
    deck: _Deck,
    plan: np.ndarray,
    terrain: np.ndarray,
    fallback: np.ndarray,
    ends: tuple[bool, bool],
    counts: _Counts,
) -> tuple[np.ndarray, np.ndarray]:
    """An off-grade carriageway's height, taken from the structure it is built on.

    Answers `Q20`. `elevation_levels` gives level 1 a flat +6.0 m, and real
    flyover decks do not oblige: measured against the shipped tiles the ribbon
    is |error| p90 **4.19 m** out, and sits *below* the deck — inside the
    structure — in 66% of samples.

    ⚠️ A station the structure does not cover falls back to the deck either
    side of it, **not** to the flat offset, and the difference is the whole
    quality of the result at the one place it matters most. `INFRASTRUCTURE`
    stops being modelled where a ramp reaches grade, so the last stretch of
    every touchdown is uncovered — and at 9 of `Q13`'s nodes that is precisely
    the node itself. Measured just inside the hole, the structure sits **-0.6 to
    +1.1 m** of the terrain: the ramp has arrived, and what is missing is a
    volume nobody modelled rather than a deck. Dropping those stations back to
    +6.0 m rebuilds the cliff this function exists to remove, exactly where it
    is most visible. Interpolating holds the deck across the hole instead, which
    closed four of the nine outright and took the worst of the rest from a
    6.00 m step to 1.63 m.

    Only an edge the structure does not cover **anywhere** falls back to the
    flat offset. That is `ISLAND EASTERN CORRIDOR`'s stub, whose every sample
    the terrain gate refuses, and it is the case the offset is still right for.

    `on_structure` follows the claim each station's height makes. Where the deck
    is held across a hole by interpolation those stations *are* on the deck —
    that is the whole claim the interpolation makes — so reporting them as bare
    ground would contradict the height published beside them. A station `_descend`
    ramps to grade makes the opposite claim and is flagged false, which is the
    contract `ARCHITECTURE.md` already states: true where the height came from
    sampled structure.

    ⚠️ **Interpolating across a hole is not what fires in this region.** Measured
    over every level-1 edge in Wan Chai there is not one hole that is not at an
    edge end, so the paragraph above describes a branch with no case here and
    `_descend` handles all of them (`Q90`).
    """
    sampled = deck.field.sample_along(plan[:, 0], plan[:, 1], slab_gap_m=deck.thresholds.slab_gap_m)

    # A deck cannot sit below the ground under it. The structure class is not
    # only elevated carriageway — `ISLAND EASTERN CORRIDOR`'s 25 m stub samples
    # 8.2 m *under* the terrain, and the next lowest anywhere in the region is
    # 0.54 m under, so the threshold sits in a 7.6 m gap rather than on a guess.
    #
    # A NaN terrain makes this comparison False and keeps the sample, which is
    # right: with no ground to measure against there is nothing to reject it on.
    under = sampled < deck.floor(terrain)
    usable = np.isfinite(sampled) & ~under
    counts.gated = int(under.sum())
    counts.sampled = int(usable.sum())
    if not usable.any():
        return fallback, np.zeros(len(plan), dtype=bool)

    # Along the edge rather than by station index: `resample` inserts stations
    # but never removes the source's own, so the spacing is not uniform and
    # counting stations would weight a densely drawn curve as if it were long.
    along = plan_lengths_2d(plan)
    # `clearance_m` on the sampled branch only. It is the road laid *on* the
    # deck, so it belongs wherever the deck is what decides the height — and
    # nowhere near the fallback above, which is not on a deck at all.
    y = np.interp(along, along[usable], sampled[usable]) + deck.thresholds.clearance_m
    return _descend(deck, along, terrain, y, usable, ends, counts)


def _descend(
    deck: _Deck,
    along: np.ndarray,
    terrain: np.ndarray,
    y: np.ndarray,
    usable: np.ndarray,
    ends: tuple[bool, bool],
    counts: _Counts,
) -> tuple[np.ndarray, np.ndarray]:
    """An off-grade edge ramped down to the street its structure stops short of.

    Answers `Q90`. `INFRASTRUCTURE` stops being modelled where a ramp reaches
    grade, and `_deck_heights` answers a hole by interpolating across it — which
    at an edge *end* has nothing on the far side to interpolate to, so
    `np.interp` clamps to the first covered station. The ribbon is then held dead
    level in the air all the way to the node: **1.83 m** of it at node 175,
    `FLEMING ROAD`, a flyover visibly afloat over the street it lands on.

    The precondition is topological rather than a height test, which is
    `_lifted_heights`' rule at the other end of the same ramp: this end descends
    because a **level-0** edge meets it, and that street's height is what it
    descends to.

    ⚠️ **The two are not the same query, and nothing stops both firing.**
    `_deck_heights` gates on `sample_along`'s slab continuity and this on the
    hole it leaves; `_lifted_heights` gates on `sample_lowest_above` and
    `at_grade_m`. Where those disagree at a shared node the street would publish
    `terrain + lift + clearance_m` while this targets `terrain + level_zero_m`,
    re-opening a step at the node the descent exists to close. **Measured: the 16
    lifted ends and the 9 descended ends are disjoint in this region** — so that
    is a fact about the data, not a property of the construction, and it is
    recorded here rather than asserted away.

    🔴 **Bounded, and the bound keeps one edge out.** Eight of the region's
    nine end holes reconstruct at 2.0-6.8%, and opposed carriageways of one
    flyover agree to within a point. `MARSH ROAD`'s `e248` is the ninth and wants
    0.66 m over a 1.9 m hole — **35.8%** — so it is left standing, because a
    grade no road climbs is evidence that the missing metres were never a ramp.

    ⚠️ **The grade is measured to the drawn ribbon, `clearance_m` included.**
    Taken off the sampled deck top it reads about 0.2 m shallower over the same
    run, which understated every row of `Q90`'s first table; the cap has to be
    compared against what actually gets drawn.

    ⚠️ **A negative step is descended, and that is not an oversight.** `e365`
    at node 30 sits 0.43 m *below* its at-grade neighbours, and the node station
    rising to meet the street while the ribbon falls onto its deck is the right
    repair for how it renders. What it does not repair is `Q13`'s attribute flip
    underneath — a level-1 label on a run that is really at grade — so `abs`
    here is the sign being out of scope rather than discarded.

    ⚠️ **`touchdown_grade_pct` is recorded over the refusals as well as the
    keeps.** Appended below the guard it would be confined to
    `touchdown_max_grade_pct` by construction and would report a clean sweep
    whatever the data did — `Q58`'s `drawn_gauge_m` trap, caught in review in
    `arrows.py` and again in `roadmarks.py`. `len(touchdown_grade_pct)` exceeding
    `ends_descended` by exactly the refusals is the identity that says so.

    ⚠️ **An end with no terrain under it has no height to descend to**, so it
    is left clamped and counted as `ends_no_target` — never appended to
    `touchdown_grade_pct`, because there is no grade to record.
    `_lifted_heights` records the mirror case as silent and points at
    `vertices_off_terrain`; that counter cannot isolate an end that wanted to
    descend and could not, which is why this one exists.

    ⚠️ **The precondition can no longer send a descent to a street that is
    not there.** `_ramp_ends` asks for level 0 at the node rather than for any
    second level, because `elevation_levels` declares a level 2 and a `(1, 2)`
    node is mixed with nothing at grade to land on. Every mixed node in Wan Chai
    is `(-1, 0)` or `(0, 1)`, so the weaker test agreed here and would have
    shipped.
    """
    out = y.copy()
    on_structure = np.ones(len(y), dtype=bool)
    for reaches_grade, start, step in ((ends[0], 0, 1), (ends[1], len(y) - 1, -1)):
        if not reaches_grade or usable[start]:
            continue
        if not np.isfinite(terrain[start]):
            counts.ends_no_target += 1
            continue
        index = start
        while 0 <= index < len(y) and not usable[index]:
            index += step
        if not 0 <= index < len(y):
            # Unreachable while `_deck_heights` returns early on an edge with no
            # usable sample at all, and spelled anyway: a backward walk that ran
            # out would leave `index` at -1, and reading the far end of the edge
            # as though it were the near deck is a plausible height from the
            # wrong place — the exact failure this function exists to remove. It
            # counts rather than vanishing, so no `continue` here can become the
            # quiet refusal `ends_no_target` was added for.
            counts.ends_no_target += 1
            continue

        grade = float(terrain[start]) + deck.level_zero_m
        run_m = abs(float(along[index]) - float(along[start]))
        # An infinite grade is what a zero-length run *means* here — a drop with
        # no road to lose it over — so it goes through the same guard as a steep
        # one rather than being skipped before the counter sees it.
        drop = abs(float(out[index]) - grade)
        percent = drop / run_m * 100.0 if run_m > 0.0 else float("inf")
        counts.touchdown_grade_pct.append(percent)
        if percent > deck.thresholds.touchdown_max_grade_pct:
            counts.ends_over_grade += 1
            continue
        counts.ends_descended += 1

        # The uncovered run alone, so the first covered station keeps both the
        # height the structure gave it and its flag. `along` decreases with a
        # backward walk and so does the numerator, which is why one expression
        # serves both directions without sorting the pair.
        reach = slice(start, index) if step == 1 else slice(index + 1, start + 1)
        fraction = (along[reach] - along[start]) / (along[index] - along[start])
        out[reach] = grade + fraction * (float(out[index]) - grade)
        on_structure[reach] = False
    return out, on_structure


def _lifted_heights(
    deck: _Deck,
    plan: np.ndarray,
    terrain: np.ndarray,
    fallback: np.ndarray,
    ends: tuple[bool, bool],
    counts: _Counts,
) -> tuple[np.ndarray, np.ndarray]:
    """A level-0 edge raised onto the ramp it starts on, where it starts on one.

    At 13 of `Q13`'s 36 nodes the source's `ELEVATION` flips partway up a ramp,
    which leaves the at-grade side of the flip drawn 2.1 to 4.0 m below the
    structure it is on. Sampling only the off-grade side would move that cliff
    to mid-ramp rather than close it.

    The rule is topological, not a height threshold: an edge is on this ramp
    because it connects to the edge that is on it. `P2-7` measured the
    alternative — lowest slab top within a cap above terrain — and the ramp and
    flyover-deck populations separate at 4.95 m against 5.33 m, which is 0.38 m
    to place a threshold in, and it lifts about five times what is broken. The
    walk touches 16 edge ends, and `P2-7` measured every one of them descending
    to grade inside its own edge.

    The walk stops at the first station whose structure is within `at_grade_m`
    of the ground, so a profile that wobbles by the 0.1-0.2 m the sampler is
    noisy at cannot restart it. That leaves a residual step of at most
    `at_grade_m`, which is what bounds the value.

    ⚠️ A station with no terrain under it reads as a lift of zero, so a hole in
    the ground mesh **at the node** leaves that end unlifted, and one part-way
    along stops the walk early. Deliberate — the lift is measured from the
    terrain, and there is nothing to measure from — but it means a terrain gap
    degrades this silently rather than loudly. `vertices_off_terrain` is where
    it would show.
    """
    at_grade = deck.thresholds.at_grade_m
    tops = deck.field.sample_lowest_above(
        plan[:, 0], plan[:, 1], deck.floor(terrain), slab_gap_m=deck.thresholds.slab_gap_m
    )
    lift = np.where(np.isfinite(tops), tops - terrain, 0.0)

    raised = np.zeros(len(plan))
    for lifted, start, step in ((ends[0], 0, 1), (ends[1], len(plan) - 1, -1)):
        # Spelled as the negation of the walk's own test so that a NaN lift
        # declines to start one. `sample_lowest_above` cannot produce a NaN here
        # — its floor is NaN wherever the terrain is, and a NaN floor admits
        # nothing — but a guard that is only safe because of a neighbour's NaN
        # handling is one refactor away from not being.
        if not lifted or not lift[start] > at_grade:
            continue
        counts.ends_lifted += 1
        index = start
        while 0 <= index < len(plan) and lift[index] > at_grade:
            # Maximum, not assignment: a short edge mixed at both ends is walked
            # twice, and the two runs may overlap in the middle.
            raised[index] = max(raised[index], lift[index])
            index += step

    # `terrain + lift` is the slab top itself. The level's flat offset is what
    # level 0 means where there is no ramp, and it is not an offset to add on
    # top of one — a city that puts level 0 anywhere but zero would otherwise
    # find its ramps that far above the structure they are supposed to lie on.
    #
    # `clearance_m` rides with the lift for the same reason it does off-grade:
    # a lifted end is resting on a ramp deck, and the two surfaces would
    # otherwise interleave exactly as they did on the flyovers.
    # `raised > 0` is `Q23`'s signal as well as this function's own result, and
    # it is returned rather than recomputed downstream because nothing
    # downstream can: the walk's stopping rule is the only thing that knows
    # where the ramp ends, and it is spent by the time this returns.
    on_structure = raised > 0.0
    return np.where(on_structure, terrain + raised + deck.thresholds.clearance_m, fallback), (
        on_structure
    )


def _node_heights(count: int, edges: Iterable[Edge]) -> list[float]:
    """One height per node, from the edge ends that meet there.

    A node has one plan position and, at `Q13`'s 36, two genuine heights. There
    is no correct single answer, so the rule picks the one that misleads least:
    **the level nearest grade, and the highest edge end on it.**

    Nearest grade because everything that reads a node position reads it for an
    at-grade purpose — `nearest_edge` refuses off-grade edges, and the fare
    stands snap in plan. Putting a junction on the flyover overhead, or 8 m down
    a tunnel portal, is the answer that is wrong for every current consumer.

    Highest on it for the reason `HeightField.sample` takes the maximum: where
    a road surface is multi-valued at one point, the drivable face is the top,
    and a node below a ribbon end is a node inside the road.

    Until `P2-7` this was whichever edge the source happened to list first. That
    was invisible while every edge at a level shared one flat offset, and stops
    being invisible the moment the ends are sampled independently.
    """
    tops: dict[int, dict[int, float]] = defaultdict(dict)
    for edge in edges:
        for node, point in ((edge.from_node, edge.polyline[0]), (edge.to_node, edge.polyline[-1])):
            by_level = tops[node]
            level, y = edge.elevation_level, point[1]
            by_level[level] = max(by_level.get(level, y), y)

    if len(tops) != count:
        # Unreachable: every node id is minted by `_Nodes.id_for` from an edge
        # end. Raised rather than defaulted because the default would be y=0,
        # which is the exact bug `terrain.py` exists to prevent, arriving
        # silently — see that module's docstring on Wan Chai's 4.29 m ground.
        raise ValueError(f"{count - len(tops)} nodes have no edge end to take a height from")

    # Ties — a node reached only by level -1 and level 1 — break downwards. No
    # such node exists in Wan Chai; the tie-break exists so that if one ever
    # does, it is decided here rather than by dictionary order.
    return [
        tops[node][min(tops[node], key=lambda level: (abs(level), level))] for node in range(count)
    ]


def _nodes_with_kind(
    positions: Sequence[tuple[float, float, float]], edges: Sequence[Edge]
) -> list[Node]:
    """Label each node `junction` or `endpoint` by how many edge ends meet there.

    Degree, not the source's intersection layer. Two centrelines meeting end to
    end is one road continuing through a geometry break rather than a junction a
    driver could turn at — and the source records those as intersections too.
    """
    degrees = [0] * len(positions)
    for edge in edges:
        degrees[edge.from_node] += 1
        degrees[edge.to_node] += 1
    return [
        Node(id=index, pos=pos, kind=JUNCTION if degrees[index] >= 3 else ENDPOINT)
        for index, pos in enumerate(positions)
    ]


def _route_overlays(source: _Source, style: RoadNetwork) -> tuple[dict[int, str], set[int]]:
    """Speed limits and bus lanes, keyed by the route id they annotate.

    Both layers are linear-referenced events against a route rather than
    attributes of a centreline. That would normally mean measuring where along
    the route each event applies — but in this dataset `ROUTE_ID` is unique per
    centreline (796 distinct values across 796 features in the region), so the
    reference collapses to a key join.
    """
    speeds = source.read(style.speed_limits)
    buses = source.read(style.bus_lanes)
    return (
        dict(
            zip(
                _routes(speeds, style.speed_limits),
                speeds.column(style.speed_limits.field("speed_limit")),
                strict=True,
            )
        ),
        set(_routes(buses, style.bus_lanes)),
    )


def _routes(layer: gdb.Layer, spec: SourceLayer) -> list[int]:
    return [int(route) for route in layer.column(spec.field("route"))]


def _turn_restrictions(
    source: _Source,
    style: RoadNetwork,
    edges: Sequence[Edge],
    edges_of_source: dict[int, list[int]],
) -> tuple[list[TurnRestriction], int]:
    """Banned movements, as `(from_edge, via_node, to_edge)`.

    Every feature in the turn layer *is* a restriction — the data specification
    defines its impedance field as negative-means-restricted and the publisher
    assigns -1 throughout — so there is nothing to filter on.

    The layer names the end of the first edge the turn passes through, and in
    213 of the region's 217 turns that end is shared with the second edge. In
    the other four it is not, while the *opposite* end coincides exactly, so the
    shared node is taken as the truth and the field only as the hint.

    A turn names source features, and clipping can split one of those into
    several edges, so every combination is tried and the pair that actually
    meets wins.

    Returns the restrictions and the count that could not be resolved.
    """
    turns = source.read(style.turns)
    first = turns.column(style.turns.field("first_edge"))
    second = turns.column(style.turns.field("second_edge"))
    at_end = turns.column(style.turns.field("first_end"))

    restrictions: list[TurnRestriction] = []
    unresolved = 0
    for row in range(len(turns)):
        from_source, to_source = int(first[row]), int(second[row])
        prefer_end = str(at_end[row]) == style.turn_at_end_value
        via = next(
            (
                (from_edge, to_edge, node)
                for from_edge in edges_of_source.get(from_source, ())
                for to_edge in edges_of_source.get(to_source, ())
                if (node := _shared_node(edges[from_edge], edges[to_edge], prefer_end=prefer_end))
                is not None
            ),
            None,
        )
        if via is not None:
            restrictions.append(TurnRestriction(from_edge=via[0], via_node=via[2], to_edge=via[1]))
        elif from_source in edges_of_source and to_source in edges_of_source:
            # Both sides survived clipping but share no node. One side merely
            # clipped away with the region is not an error: the turn layer is
            # territory-wide, exactly like the centrelines.
            unresolved += 1
    return restrictions, unresolved


def _shared_node(first: Edge, second: Edge, *, prefer_end: bool) -> int | None:
    """The node a turn passes through, preferring the end the source nominates.

    ⚠️ `prefer_end` is stated against the *source feature's* digitisation, and
    two things here can break that correspondence: reversing a `backward` edge
    swaps its ends, and clipping splits a feature so that only the last run ends
    where the feature did. The fallback below covers both, so the answer is
    right today — but it would stop being right if a turn's two edges ever met
    at *both* ends, which is a loop road or a carriageway pair closing on
    itself. Neither occurs in Wan Chai, and `backward` is unreachable for a
    source that codes direction absolutely. Recorded rather than solved: the fix
    is to carry each edge end's source provenance, which is machinery for a case
    no data has yet produced.
    """
    nominated = first.to_node if prefer_end else first.from_node
    other = first.from_node if prefer_end else first.to_node
    ends = (second.from_node, second.to_node)
    if nominated in ends:
        return nominated
    return other if other in ends else None


def _components(node_count: int, edges: Iterable[Edge]) -> list[int]:
    """Sizes of the graph's connected components, largest first."""
    parent = list(range(node_count))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for edge in edges:
        a, b = find(edge.from_node), find(edge.to_node)
        if a != b:
            parent[a] = b

    sizes: dict[int, int] = {}
    for node in range(node_count):
        root = find(node)
        sizes[root] = sizes.get(root, 0) + 1
    return sorted(sizes.values(), reverse=True)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def read_graph(path: Path, city_id: str, region_id: str) -> dict:
    """The road graph, at the version this build understands.

    Lives beside the writer below rather than in either consumer: `P1-4` draws
    the graph and `P1-5` snaps to it, and a second copy of this check is a
    second place for the version to be read wrongly.

    Takes the city and region only to name them in the rebuild command. A hint
    that does not run is worse than no hint — `python -m pipeline.roads` on its
    own exits on a missing argument, which is a second puzzle to solve while
    already stuck on the first.
    """
    rebuild = f"python -m pipeline.roads --region {region_id}"
    return read_document(path, ROADGRAPH_SCHEMA, rebuild)


def _write(out_root: Path | None, city: Config, region_id: str, report: RoadReport) -> int:
    out_dir = city.out_dir(region_id, out_root)
    document = {
        "schema_version": ROADGRAPH_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "nodes": [
            {"id": node.id, "pos": round_position(node.pos), "kind": node.kind}
            for node in report.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "from": edge.from_node,
                "to": edge.to_node,
                "polyline": [round_position(point) for point in edge.polyline],
                "on_structure": edge.on_structure,
                "structure_bounded": edge.structure_bounded,
                "direction": edge.direction,
                "lanes": edge.lanes,
                "lanes_source": edge.lanes_source,
                "width_m": edge.width_m,
                "width_source": edge.width_source,
                "width_publisher": edge.width_publisher,
                "offset_m": edge.offset_m,
                "offset_source": edge.offset_source,
                "deck_rim_m": [list(pair) for pair in edge.deck_rim_m],
                "speed_limit_kph": edge.speed_limit_kph,
                "bus_lane": edge.bus_lane,
                "tram_tracks": edge.tram_tracks,
                "elevation_level": edge.elevation_level,
                "road_name": edge.road_name,
                "kerbside": [
                    {
                        "side": run.side,
                        "from_m": run.start_m,
                        "to_m": run.end_m,
                        "kind": run.kind,
                    }
                    for run in edge.kerbside
                ],
            }
            for edge in report.edges
        ],
        "turn_restrictions": [
            {"from_edge": turn.from_edge, "via_node": turn.via_node, "to_edge": turn.to_edge}
            for turn in report.turn_restrictions
        ],
    }
    return write_document(out_dir / ROADGRAPH_NAME, document)


def _surfaces(
    city: Config,
    region_id: str,
    sources_root: Path | None,
    region_high: tuple[float, float],
) -> _Surfaces:
    """The height fields this region's roads are measured against, and how
    closely the at-grade ones follow the first of them.

    The terrain resolves `Q11`; the structure resolves `Q20`, and is read only
    when the city asks for deck sampling. `load_config` refuses `roads.deck`
    without a `buildings.structure_class`, so the second half of the test below
    is a type narrowing rather than a case that can occur.

    Two passes over the sheet zips rather than one, which costs almost nothing:
    the two classes live in disjoint members, so each pass decompresses only its
    own and the duplicated work is opening the archive. Reading them together
    would mean holding both classes' geometry live to split the stream, and the
    memory note on `_field` is the reason not to.
    """
    if not city.roads.ground_from_terrain:
        # `load_config` refuses either block without `ground: terrain`, so neither
        # can survive into a city with no ground to measure against.
        return _Surfaces(ground=None, deck=None, profile=None)

    profile = city.roads.ground_profile
    place = Placement.resolve(city, region_id, sources_root, None)
    ground = _field(place, region_high, city.buildings.terrain_class, city, region_id)

    thresholds, structure_class = city.roads.deck, city.buildings.structure_class
    if thresholds is None or structure_class is None:
        return _Surfaces(ground=ground, deck=None, profile=profile)
    return _Surfaces(
        ground=ground,
        profile=profile,
        deck=_Deck(
            field=_field(place, region_high, structure_class, city, region_id),
            thresholds=thresholds,
            level_zero_m=city.deck_height_m(0),
        ),
    )


def _field(
    place: Placement,
    region_high: tuple[float, float],
    class_name: str,
    city: Config,
    region_id: str,
) -> HeightField:
    """One sheet class, as a height field.

    Read through the building stage's sheet reader because it is the same
    sheets, the same zips and the same game-space offset. Any drift between
    where roads think the ground is and where buildings sit would show up as
    kerbs at the wrong height along every street in the region — and, since
    `P2-7`, as a flyover deck that misses the tiles the player drives on.

    A generator, not a list, and stripped of everything but geometry on the way
    through. The terrain ships a 40 MB JPEG per sheet — 224 MB across the six —
    which a height field never looks at, and materialising all six meshes first
    holds every one of those textures live at once. Measured: 962 MB peak RSS
    down to 661 MB.
    """
    meshes = (
        replace(mesh.translated(place.offset), texture=None, uvs=None)
        for _, path in place.sheets
        for _, mesh in read_sheet(path, (class_name,))
    )
    try:
        return HeightField.from_meshes(meshes, region_high=region_high)
    except ValueError as error:
        raise ValueError(
            f"city '{city.id}' asks roads to sample '{class_name}', but region '{region_id}' has "
            f"no '{class_name}' geometry inside it in the cached sheets"
        ) from error


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _by_basis(values: Iterable[str]) -> str:
    """A basis histogram for one log line, commonest first.

    Both the width and the lane count report which rule licensed each edge, and
    a reader needs the split rather than the total — a two-way span and a
    one-way one that never crossed a median are different measurements, and
    pooling them is `Q57`'s generalisation.
    """
    counted = sorted(Counter(values).items(), key=lambda kv: -kv[1])
    return ", ".join(f"{count} {name}" for name, count in counted) or "nothing"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    report = build_region(city, args.region)
    log.info(
        "%d centreline parts read, %d clipped away, %d edges over %d nodes, %d turn restrictions",
        report.read,
        report.clipped,
        len(report.edges),
        len(report.nodes),
        len(report.turn_restrictions),
    )
    log.info(
        "  %d vertices simplified to %d (%.1f%%)",
        report.vertices_read,
        report.vertices_kept,
        100.0 * report.vertices_kept / max(1, report.vertices_read),
    )
    if report.kerbside is not None:
        found = report.kerbside
        by_kind = ", ".join(
            f"{metres:.0f} m {kind}" for kind, metres in sorted(found.metres_by_kind.items())
        )
        log.info(
            "  kerbside: %d of %d no-stopping features painted, %s across %d edge sides",
            found.features_painted,
            found.features_read,
            by_kind or "nothing",
            found.sides_covered,
        )
        log.info(
            "    %.0f m sampled, %.0f m once overlapping features merged, %.0f m published; "
            "%d runs under the minimum dropped (%.0f m)",
            found.metres_sampled,
            found.metres_deduped,
            found.metres_published,
            found.runs_dropped,
            found.metres_dropped,
        )
        refused = ", ".join(
            f"{metres:.0f} m as type {code}"
            for code, metres in sorted(found.metres_refused.items())
        )
        if refused:
            log.info("    refused: %s", refused)
        if found.samples_unassigned:
            log.warning(
                "    %d in-region samples found no edge within the offset guard",
                found.samples_unassigned,
            )
    if report.carriageway is not None:
        width = report.carriageway
        log.info(
            "  carriageway: %d of %d edges measured (%s); %d spanned and unattributed, "
            "%d under TD's %s m minimum — reported, never refused",
            width.measured,
            width.edges_walked,
            _by_basis(width.basis.values()),
            width.unattributed,
            width.under_minimum,
            f"{city.carriageway_survey.width_bounds.min_m:.1f}",
        )
        log.info(
            "    %d of %d stations spanned by one publisher; the rest keep the authored width",
            width.stations_spanned,
            width.stations_walked,
        )
        log.info(
            "    by publisher: %s — ⚠️ NOT one measurement, see `Edge.width_publisher`",
            _by_basis(width.publishers[edge_id] for edge_id in width.assigned_m),
        )
        if width.deck_span_m:
            # ⚠️ **A different truth side from every line above** — the model
            # rather than a publisher's plan line — so it is logged apart rather
            # than folded into the coverage figures, which count only the edges
            # a publisher spanned.
            spans = np.array(list(width.deck_span_m.values()))
            offsets = np.array(list(width.deck_offset_m.values()))
            log.info(
                "    deck: %d off-grade edges measured against their own structure; "
                "span p50 %.2f m, offset p50 %+.2f m (right of travel), |offset| max %.2f m",
                len(spans),
                float(np.median(spans)),
                float(np.median(offsets)),
                float(np.abs(offsets).max()),
            )
            log.info(
                "      %d stations on a deck (%d clipped by the walk), %d with the centreline "
                "off it entirely, %d edges unmeasured and left authored (Q103)",
                width.deck_stations_on,
                width.deck_stations_saturated,
                width.deck_stations_off,
                width.deck_edges_unmeasured,
            )
        log.info(
            "    lanes: %d of %d measured widths resolve under TPDM %.2f-%.2f m (%s); "
            "%d ambiguous keep the authored count, %d odd two-way — reported, never corrected",
            len(width.lanes),
            width.measured,
            city.carriageway_survey.width_bounds.lane_m[0],
            city.carriageway_survey.width_bounds.lane_m[1],
            _by_basis(width.lanes_basis.values()),
            width.lanes_unresolved,
            len(width.lanes_odd_two_way),
        )
        # 🔴 **Logged rather than merely computed, which is why the property
        # exists at all** (`Q114`): its predecessor `lanes_floored` was defined
        # and read by nothing. These are the edges `RoadGraph.lane_offset`'s own
        # floor now stands over, and the only place a reader sees how many.
        log.info(
            "      %d measured widths resolve to a SINGLE lane — no lane line is drawn down "
            "them, and RoadGraph.lane_offset floors the driving line off their centreline "
            "(Q114)",
            width.lanes_single,
        )
        if width.deck_lane_ceiling:
            # 🔴 **Derived from the `lanes_source` this stage actually wrote, not
            # from a list the survey kept.** The survey can only see the
            # *authored* count, and the cap is applied to whatever count stands —
            # the ray-licensed one where there is one — so a list built there
            # names a population this code does not act on. Counting the field
            # that was written makes the two agree by construction.
            log.info(
                "      deck ceiling: %d of %d measured decks hold fewer lanes than the "
                "speed-limit table authored, and are cut to it (Q114)",
                sum(1 for edge in report.edges if edge.lanes_source == "deck_capped"),
                len(width.deck_lane_ceiling),
            )
        log.info(
            "    lane rows: %d edges carry turn arrows; %d resolved an ambiguous bracket, "
            "%d agree with the count the width published, %d state a single arrow — not a row",
            len(width.lane_rows),
            width.lanes_ambiguous - width.lanes_unresolved,
            len(width.lanes_row_agreeing),
            len(width.lanes_row_single),
        )
        log.info(
            "      %d state fewer lanes than the width brackets (an unpainted lane), %d state "
            "more (a finding) — both reported, never used",
            len(width.lanes_row_below_bracket),
            len(width.lanes_row_over_bracket),
        )
    log.info(
        "  largest component holds %d of %d nodes (%.1f%%), %d components in all",
        max(report.components, default=0),
        len(report.nodes),
        100.0 * report.connectivity,
        len(report.components),
    )
    if report.edges_sampled or report.ends_lifted:
        # Two lines because the populations differ: the first counts off-grade
        # edges only, and `vertices_added` spans those and the lifted level-0
        # ones together.
        log.info(
            "  %d off-grade edges took their height from the structure, sampled directly at "
            "%d stations",
            report.edges_sampled,
            report.vertices_sampled,
        )
        log.info(
            "  %d level-0 ends lifted onto a ramp; resampling added %d stations across both",
            report.ends_lifted,
            report.vertices_added,
        )
        log.info(
            "  %d stations published as resting on structure, drawn at their authored width",
            report.vertices_on_structure,
        )
        # Both counts on one line, because the pair is the finding rather than
        # either number: they measure different things and the gap between them
        # is the population `Q23`'s flag could never reach.
        log.info(
            "  %d stations bounded by structure within %.2f m, in the %.2f-%.2f m band above "
            "the ribbon (Q19) - a different question from the line above, not a subset",
            report.vertices_structure_bounded,
            city.roads.deck.bound_reach_m,
            city.roads.deck.bound_low_m,
            city.roads.deck.bound_high_m,
        )
    if report.touchdown_grade_pct and city.roads.deck is not None:
        # Both halves on one line, because the refusals are the reason the
        # distribution can be trusted and a line reporting only the keeps is the
        # clean sweep `Q90` warns this counter must not be able to report. The
        # second half of the test is a type narrowing: no end can be graded by a
        # city that samples no decks.
        median, worst = np.percentile(report.touchdown_grade_pct, (50, 100))
        log.info(
            "  %d off-grade ends descended to grade, %d refused over %.1f%%, %d with no street "
            "to land on; graded across %d at median %.1f%%, max %.1f%%",
            report.ends_descended,
            report.ends_over_grade,
            city.roads.deck.touchdown_max_grade_pct,
            report.ends_no_target,
            len(report.touchdown_grade_pct),
            median,
            worst,
        )
    if report.edges_followed:
        log.info(
            "  %d at-grade edges follow the ground; thinning kept %d of the %d stations offered",
            report.edges_followed,
            report.vertices_followed,
            report.vertices_offered,
        )
    if report.turns_unresolved:
        log.warning("  %d turn restrictions had no shared node", report.turns_unresolved)
    if report.vertices_off_terrain:
        log.warning("  %d vertices fell outside the terrain", report.vertices_off_terrain)
    if report.vertices_gated:
        log.warning(
            "  %d structure samples sat under the terrain and were refused", report.vertices_gated
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
