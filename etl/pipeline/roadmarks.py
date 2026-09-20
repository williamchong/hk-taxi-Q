"""Published stop and give-way lines, drawn as their own mesh (`P3-23`).

`P3-20` put **GIVE WAY / 讓** on 74 plates and there was no give-way line on the
carriageway under any of them. `DTAD_RD_MARK_LINE` publishes all three
transverse markings — `RM1011` STOP LINE x120, `RM1012` STOP LINES x8,
`RM1013` GIVE WAY LINES x83, 1,673 m in region — as surveyed polylines that are
straight to four decimal places and, but for two, at grade.

The shape of the stage is `boxjunctions.py`'s and the argument for a separate
mesh is `arrows.py`'s, in its strongest form. `ARCHITECTURE.md` records that
`road_markings.tres`'s 6 m junction fade "blanks exactly the approach an arrow
is about" and that the 6,051 m² cap overlap re-exposes anything drawn on a cap.
A stop line is more exposed to both than an arrow is: it lives *at* the
junction, on the cap, inside the fade.

Three things differ from box junctions, and each is recorded where it bites:

- 🔴 **The host is chosen by transversality, not by proximity**, which is the
  one place this stage departs from every other consumer of this geodatabase.
  See `_host` for the measurement — the nearest-edge join is wrong on 44% of
  stop lines and 43% of give-way lines, because a bar across a minor road's
  mouth lies a metre off the *major* road's kerb.
- **The width is convention and the extent is published**, so the bar is drawn
  at its surveyed length and never stretched to the drawn kerb. The honest cost
  is underfill: the ribbon is 1.6x wide, so a bar that spans the real
  carriageway stops short of the drawn one. `underfill_m` publishes it.
- **A double line is drawn symmetric about the published polyline**, because
  the source publishes one line per feature and nothing says which of the two
  it is. `config.RoadMark.band_offsets_m` carries the reading and its 0.2 m
  cost.

⚠️ **Nothing here invents a marking.** The region publishes 209 at-grade bars
against 393 junction nodes of three and four arms each; a fallback keyed on
topology would be wrong many times over, and every one of its mistakes would
render as a perfectly good stop line.
"""

from __future__ import annotations

import argparse
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise, product
from pathlib import Path
from typing import NamedTuple

import numpy as np

from pipeline import gdb
from pipeline.config import Config, GameTransform, RoadMark, RoadMarks, load_config
from pipeline.documents import read_document, write_document
from pipeline.drawnsurface import DrawnSurface
from pipeline.fetch import source_reads
from pipeline.geometry import wound_up
from pipeline.gltf import write_glb
from pipeline.meshbuild import FlatBuilder, import_quantum_m
from pipeline.polyline import Segments, plan_lengths_2d, plan_projections

# `AT_GRADE` rather than a fifth private copy — `railings.py` exports it
# publicly to stop exactly that, and `signs.py` imports it for the same reason.
# It is the source's own encoding of "no structure" on the same column of the
# same geodatabase, not a threshold anyone may tune. 209 of the region's 211
# parts are null.
from pipeline.railings import AT_GRADE
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, clip, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, downward_facing

log = logging.getLogger(__name__)

ROADMARKS_NAME = "roadmarks.glb"
ROADMARKS_MANIFEST_NAME = "roadmarks.json"
# 2 since `Q125`: the asset carries the inferred join between opposed
# carriageways as well as the surveyed markings, and the `join` block is what
# says how much of it. A v1 reader takes `drawn_by_id` for everything in the
# mesh, which stops being true the moment a region names an `opposed_join_mark`
# — not a field it can miss, but a quantity it would under-report.
ROADMARKS_MANIFEST_SCHEMA = 2

# ⚠️ **No `-col` suffix.** Paint is not a collider — `BOXJUNCTIONS_MESH_NAME`'s
# reasoning, and sharper again: a stop line runs across every approach in the
# city, so a 16 mm step modelled as collision geometry is a kerb the player
# mounts at every junction while braking.
ROADMARKS_MESH_NAME = "roadmarks"

# glTF material name, the contract channel `BOXJUNCTIONS_MATERIAL` uses:
# `tools/generated_scene_import.gd` maps this string onto `tuning/roadmarks.tres`
# and nothing else. One name for all three markings, because all three are the
# same white paint and one material is one draw call.
ROADMARKS_MATERIAL = "roadmarks"


# Below this, a dash module's last painted run is rounding rather than paint.
# The same shape of bar as `meshbuild.MIN_TWICE_AREA_M2` and it exists for a measured
# reason: `_runs` used to advance by `start += period`, which drifts a few ULPs
# *below* the true multiple, so a give-way line whose length lands on a module
# boundary emitted a final mark 3e-16 m long. It never rendered — the collapsed
# triangle is dropped downstream — but it was counted in `slivers_dropped`,
# which is a published counter this stage asks readers to trust.
_MIN_MARK_M = 1e-6


@dataclass
class RoadMarkReport:
    """What the stage read, matched and drew.

    ⚠️ **The counters are what can see this stage fail** — `Q58`'s lesson,
    inherited via `arrows.py` and `boxjunctions.py`. A bar on the wrong street
    is a perfectly drawn bar; a bar whose host was picked by proximity is drawn
    in exactly the right place at the wrong height; an inverted mesh renders as
    *nothing*.

    The partitions:

        parts == not_a_road_mark + on_structure + empty_geometry + outside_region
                 + candidates
        candidates == drawn + no_host_on_axis + host_off_carriageway + no_edge_in_range

    ⚠️ **The partition is over PARTS, not features, and the two differ by 2.5x
    on this layer** — 1,679 features against 4,162 parts, because `RM1001` and
    `RM1109` are published as long multi-part lines. `features` is published
    beside it as the publisher's own row count so neither number can be read as
    the other; `railings.py` splits them the same way and for the same reason.
    """

    features: int = 0
    parts: int = 0
    not_a_road_mark: int = 0
    on_structure: int = 0
    empty_geometry: int = 0
    # Parts that clipped to nothing: wholly outside the region, or grazing it and
    # leaving a run shorter than the marking's own width. ⚠️ **Distinct from
    # `empty_geometry`** — that is a NULL or single-vertex geometry, this is a
    # real marking somewhere else.
    #
    # 🔴 **0 here, and UNEXERCISED — do not read it as proven.** Driving it needs
    # a published part outside the region and this region has none, so no test in
    # the suite reaches the increment: removing it leaves the whole suite green.
    # `test_clip_returns_nothing_the_two_ways_the_partition_must_survive` pins
    # the two ways `clip` returns nothing, which is the half that *can* be tested
    # here. Before this leg existed the identity closed anyway while `parts`
    # leaked, which is the failure it is written against.
    outside_region: int = 0
    candidates: int = 0

    drawn: int = 0
    no_host_on_axis: int = 0
    # Longitudinal markings whose host centreline lies outside that host's own
    # drawn ribbon — the line is not on the road it matched. Counted separately
    # because it is a different refusal from an off-axis one and wants a
    # different fix: this one is a join that landed on the wrong carriageway.
    host_off_carriageway: int = 0
    # The same refusal in METRES by marking, because an oblique marking has no
    # bearing guard and this is the only bar it meets (`P3-35g3`): a hatched
    # island stands exactly where a median was paved over, which is where the
    # drawn ribbon is least likely to reach it.
    host_off_carriageway_m_by_id: dict[str, float] = field(default_factory=dict)
    # 🔴 **Both sides of the empty band `chevron_turn_deg` sits in**, over every
    # 3-vertex part of a marking that declares one, before any refusal: the
    # straightest part called a chevron and the sharpest that was not. The two
    # closing on the bar is the rule failing (`P3-35g3`).
    chevrons: int = 0
    chevron_m: float = 0.0
    chevron_straightest_deg: float | None = None
    outline_sharpest_deg: float | None = None
    no_edge_in_range: int = 0

    # Per marking id, how many were drawn and how many metres of published line
    # that was. Keyed by id because that is what makes the `marks:` table
    # reviewable — an entry that silently drew nothing is otherwise invisible.
    drawn_by_id: dict[str, int] = field(default_factory=dict)
    drawn_m_by_id: dict[str, float] = field(default_factory=dict)
    # Metres of published line refused **by the whitelist**, keyed by the code
    # that published it. The honest form of reading three codes of a 61.9 km
    # layer is a figure for the other 59 km.
    #
    # ⚠️ **Whitelist refusals only.** An on-structure refusal of an admitted code
    # is counted in `on_structure_m` instead, because pooling them would put
    # `RM1012` in a table whose every other row reads "this code is not a road
    # marking" — and `RM1012` is one.
    refused_m_by_code: dict[str, float] = field(default_factory=dict)
    on_structure_m: float = 0.0
    # 🔴 **The BUNDLE's word on structure, beside the SOURCE's.** `on_structure`
    # is what the publisher's `level` column says of a whole feature; this is a
    # station quad — or a piece of one, cut at the host strip's end line —
    # every vertex of which is over nothing drawn at level 0 and under
    # something drawn at a level above. A 7.1 m `RM1001` hosted on level-0
    # `e168` runs 3.5 m past the touchdown onto the WAN CHAI INTERCHANGE deck,
    # where level-0 sampling is over void and snaps to the ramp's end 52-131 mm
    # under the deck (`Q92`'s third class). Refused and counted, never placed
    # on the deck: this stage draws level 0 (`Q15`). Two coverage facts the
    # reader already answers, no radius and no knob. ⚠️ **A void station with
    # nothing drawn over it is KEPT** — that is the on-kerb population `Q54`
    # protects, and the mutation a test of this must fail on. Stationed, not
    # per feature: `drawn`, `drawn_by_id` and the partitions do not move.
    stations_on_drawn_structure: int = 0
    on_drawn_structure_m: float = 0.0

    # 🔴 **The INFERRED join between two opposed carriageways (`Q125`), and it
    # is its own partition because it is not a published marking.** Nothing
    # here enters `drawn`, `drawn_by_id` or the two partitions above: those are
    # over what TD surveyed, and folding an invented line into them would put
    # the project's own placement inside the number that says what the
    # publisher drew.
    #
    #     join_m == join_covered_m + join_drawn_m + join_refused_m
    #
    # ⚠️ **`join_covered_m` is the counter that can fail**, and it is what makes
    # this different from `Q117`: the metres where TD's own `RM1001` runs beside
    # the join and the inferred line yields to it. It is reachable at zero (a
    # region with no surveyed line) and it is 3,416 m of survey against 95 pairs
    # here, so mutation-check it rather than reading its value — with the cut
    # disabled the two lines are drawn on top of each other and the frame is
    # how you see it.
    join_pairs: int = 0
    join_m: float = 0.0
    join_covered_m: float = 0.0
    join_drawn_m: float = 0.0
    # Uncovered join shorter than the mark's own line width, which is
    # `read_markings`' bar for a clipped run said in the same terms. A run this
    # short is a slot between two surveyed lines, not a line.
    join_refused_m: float = 0.0
    joins_drawn: int = 0
    # 🔴 **Where the inferred line stands in for a survey line this stage
    # REFUSED**, in metres — a surveyed `RM1001` whose host was off its own
    # carriageway or off axis, with the join then drawn over that same stretch
    # because nothing was painted there. ⚠️ **A finding to go and look at, never
    # a bar to retune**: it is the one place the invention hides a refusal
    # instead of a silence, and a rise in it means the survey is being refused
    # more often rather than the join being drawn better.
    join_over_refused_survey_m: float = 0.0

    # 🔴 **The counter that can see the join regress**, and the reason it is not
    # `axis_residual_deg`. The residual grades a rule that optimises the very
    # thing it reports — `Q58`'s `drawn_gauge_m` trap — so what is published
    # beside it is how often the transverse pick and the naive nearest edge
    # disagree about the host. Measured at 53 of 120 and 36 of 83 when this
    # shipped; a fall towards zero means the pick has stopped picking.
    host_disagreement: int = 0

    # `|90 - angle between the marking and its chosen host|`, recorded over
    # every candidate that found an edge in range — **including the ones the
    # bearing guard then refuses**, so `n` exceeding `drawn` is how a reader
    # tells the distribution can see past its own filter (`Q58`). Move the
    # append below the guard and every percentile is confined to
    # `bearing_tolerance_deg` by construction, which is the defect review caught
    # in `arrows.py` and in `railings.py` before it.
    axis_residual_deg: list[float] = field(default_factory=list)
    # How far the chosen host sits from the marking's midpoint, over drawn
    # markings. Much larger than `arrows.offset_m` by design: a bar across a
    # four-lane mouth starts on the far kerb.
    host_distance_m: list[float] = field(default_factory=list)

    # ⚠️ **The underfill, published rather than corrected.** The host's drawn
    # width less the marking's published length: positive where the bar stops
    # short of the drawn kerb, which is most of the estate because the ribbon is
    # widened 1.6x (`Q19`) and the bar was surveyed on the real carriageway.
    # Negative where the bar spans more lanes than the host's own width claims.
    # Stretching it to the ribbon would be inventing an extent (`Q54`), which is
    # the call `P3-18` already made for box junctions.
    underfill_m: list[float] = field(default_factory=list)
    mark_length_m: list[float] = field(default_factory=list)
    # Per drawn marking, max minus min of its vertices' snapped road heights.
    # What the per-vertex join actually moved.
    height_spread_m: list[float] = field(default_factory=list)

    # 🔴 **The tripwire on the cap join (`Q92`)**, and it matters more here than
    # on any other layer: a stop line sits *at* a junction mouth, so most of this
    # paint stands on cap tarmac and the height model it replaced was furthest
    # wrong exactly there. `vertices_over_cap` reads **0** if `roadsurface.json`
    # stops publishing `caps`, or publishes them at a level this stage does not
    # read — the one way the fix reverts with every partition still closing.
    vertices_drawn: int = 0
    vertices_over_cap: int = 0
    # 🔴 **The tripwire on the RAIL join (`P3-32`'s residue)**: a vertex over
    # nothing drawn — no cap, no carriageway strip — takes the nearest drawn
    # edge's height, `void_reach_m` away. It reads **every vertex** if
    # `roadsurface.json` stops publishing `ribbons`, which is the one way that
    # half of `DrawnSurface` reverts with every partition still closing; and it
    # is reachable, not a tautology — a bar drawn past the kerb lands here.
    vertices_over_void: int = 0
    void_reach_m: list[float] = field(default_factory=list)
    # 🔴 **The tripwire on the crease cut (`Q92`'s chord residue)** —
    # `BoxJunctionReport`'s three, for its reason: every quad is cut along the
    # creases of the drawn surface before it is placed, and both counts fall
    # to `polygons_placed` and zero the moment the cut stops firing. Reachable:
    # a quad inside one strip triangle cuts nothing.
    polygons_placed: int = 0
    polygons_split: int = 0
    pieces_placed: int = 0

    # Triangles dropped for being thinner than the engine's import lattice, and
    # the lattice pitch they were judged against — `boxjunctions._import_quantum_m`
    # for the measured mechanism. ⚠️ **This asset is more exposed to it than any
    # other**: a give-way dash is 600 mm by 200 mm, and 200 mm is twelve lattice
    # cells at Wan Chai's pitch, so the margin is real but it is not large.
    slivers_dropped: int = 0
    import_quantum_m: float = 0.0

    # Triangles wound so they face the ground. ⚠️ Must be 0 — `cull_back` drew
    # none of the first tramway, 5,111 triangles of 5,112.
    inverted: int = 0
    inverted_area_m2: float = 0.0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)

    # One distribution as the manifest publishes it: p50/p90/p99/max, the tail
    # rather than the middle, for `report.tail_of`'s stated reason — every
    # distribution here is a residual, and the tail is the finding.
    measured = staticmethod(tail_of)


@dataclass(frozen=True)
class Marking:
    """One published transverse marking, in game plan space."""

    code: str
    mark: RoadMark
    # The published polyline, `(n, 2)` as `(x, z)`.
    line: np.ndarray

    @property
    def along_m(self) -> np.ndarray:
        """Cumulative distance to each of its vertices, starting at zero."""
        return plan_lengths_2d(self.line)

    @property
    def length_m(self) -> float:
        return float(self.along_m[-1])

    @property
    def midpoint(self) -> np.ndarray:
        """The point half its own length along, not the mean of its vertices.

        The two agree on a straight two-point line, which is 192 of the region's
        211 parts, and the mean drifts towards a dense end on the other 19.
        """
        along = self.along_m
        return _point_at(self.line, along, 0.5 * float(along[-1]))

    @property
    def turn_deg(self) -> float | None:
        """How far a 3-vertex part turns at its middle vertex; None for any other.

        What tells a chevron from its outline (`RoadMark.chevron_width_m`): TD
        surveys a chevron as one V.
        """
        if len(self.line) != 3:
            return None
        arrive, leave = self.line[1] - self.line[0], self.line[2] - self.line[1]
        cosine = float(arrive @ leave) / float(np.linalg.norm(arrive) * np.linalg.norm(leave))
        return math.degrees(math.acos(min(max(cosine, -1.0), 1.0)))

    @property
    def is_chevron(self) -> bool:
        turn, bar = self.turn_deg, self.mark.chevron_turn_deg
        return turn is not None and bar is not None and turn > bar

    @property
    def axis_deg(self) -> float:
        """Game heading of the marking's own chord, in [0, 180)."""
        span = self.line[-1] - self.line[0]
        return math.degrees(math.atan2(span[0], -span[1])) % 180.0


def read_markings(
    city: Config,
    spec: RoadMarks,
    region_id: str,
    transform: GameTransform,
    region_high: tuple[float, float],
    report: RoadMarkReport,
    *,
    sources_root: Path | None,
) -> list[Marking]:
    """Every published stop and give-way line in the region, in game plan space.

    Everything refused here is refused on what the *publisher* says — a code
    outside the `marks:` table, a feature on a structure, an empty line — and
    each refusal is counted rather than logged (`Q58`). The refused metres are
    keyed by code because the layer carries 61.9 km over dozens of codes and the
    honest form of reading three of them is a published figure for the rest.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    markings: list[Marking] = []
    # `layer` first, so the parts of a region with no `more_layers` are read in
    # the order they always were and its mesh is byte-identical (`Q132`).
    for (path, member), source_layer in product(reads, spec.layers):
        layer = gdb.read_layer(
            path,
            source_layer.layer,
            columns=source_layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = layer.column(source_layer.field("mark_type"))
        levels = layer.column(source_layer.field("level"))
        owners, parts = gdb.polylines(layer)
        report.features += len(layer.fids)

        for owner, points in zip(owners, parts, strict=True):
            report.parts += 1
            code = str(types[owner])
            source = np.asarray(points, dtype=np.float64)
            mark = spec.mark_of(code)
            if mark is None:
                report.not_a_road_mark += 1
                report.refused_m_by_code[code] = report.refused_m_by_code.get(code, 0.0) + _length(
                    source
                )
                continue
            if str(levels[owner]).strip().lower() not in AT_GRADE:
                # On a flyover deck. `Q13` keeps the elevated network closed to
                # driving, and the nearest level-0 edge to a bar on a deck is
                # the street underneath it.
                report.on_structure += 1
                report.on_structure_m += _length(source)
                continue
            if len(source) < 2 or not np.isfinite(source[:, :2]).all():
                report.empty_geometry += 1
                continue
            game_x, _, game_z = transform.to_game(source[:, 0], source[:, 1])
            line = np.column_stack([game_x, game_z])
            # A repeated vertex leaves a zero-length step, which has no
            # direction to take a perpendicular from.
            line = line[np.concatenate([[True], np.linalg.norm(np.diff(line, axis=0), axis=1) > 0])]
            if len(line) < 2:
                report.empty_geometry += 1
                continue
            # 🔴 **Clipped to the region, on `roads.py`'s own rule and against
            # the same geometry it names.** That docstring's example is the
            # Central-Wan Chai Bypass, which enters the spatial filter because
            # its bounding box grazes the region and then runs out into the
            # harbour — and `RM1001` is painted *on* that corridor, so this layer
            # inherits the defect the moment it stops being short bars at
            # junctions. Measured before the clip: **6 of 143** at-grade parts
            # carried vertices outside, the worst a 450 m line with **44 of 55**
            # of them out, which is paint over void — no road, no ground and no
            # tile is built there. A stop line never reached this because it is
            # 10 m long.
            #
            # ⚠️ **Cutting is safe here for `clip`'s own reason** — a polyline cut
            # in two is two polylines, and unlike a mesh there is no open shell
            # to seam. Each run keeps the code and the mark, so a marking cut by
            # the boundary counts as two candidates; the partition is over parts
            # and this is where a part becomes its drawable runs.
            runs = clip(line, region_high, min_length_m=mark.line_width_m)
            if not runs:
                # 🔴 **Counted, or the parts partition leaks silently.** `clip`
                # returns nothing two ways — a part wholly outside the region,
                # and one that only grazes it and leaves a run shorter than the
                # marking's own width — and `parts` was incremented above. It is
                # **0 in this region**, which is why the identity closed anyway;
                # it is reachable the moment a part's bounding box grazes the
                # filter without its geometry entering. Its own counter rather
                # than `empty_geometry`, which means a NULL or single-vertex
                # geometry: this marking is real and is somewhere else.
                report.outside_region += 1
                continue
            for run in runs:
                report.candidates += 1
                markings.append(Marking(code=code, mark=mark, line=run))
    return markings


def _length(source: np.ndarray) -> float:
    """A source part's published length, or zero where it has none to measure."""
    if len(source) < 2 or not np.isfinite(source[:, :2]).all():
        return 0.0
    return float(plan_lengths_2d(source[:, :2])[-1])


# --------------------------------------------------------------------------
# The join
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Host:
    """The level-0 edge a marking was matched to, and how well."""

    # Index into the flattened segment arrays.
    segment: int
    # The graph edge that segment belongs to.
    edge_id: int
    # Degrees of error away from the axis this marking is meant to lie on:
    # `|90 - crossing|` transverse, the crossing angle itself longitudinal.
    residual_deg: float
    distance_m: float
    # The host's **drawn** carriageway width, for the underfill — read from
    # `roadsurface.json` and never from the graph. See `Network.width_m`.
    width_m: float
    # Whether the plain nearest segment would have chosen a different edge.
    disagrees: bool
    # Plan distance from the marking's midpoint to every segment, computed on
    # the way to choosing the host and handed back rather than thrown away:
    # `_place_row` narrows the height join with it, which is the difference
    # between one full scan of the network per marking and one per vertex.
    distance_m_all: np.ndarray


@dataclass(frozen=True)
class Network:
    """The level-0 network's per-segment heading and drawn width.

    ⚠️ **A view over `Segments`, not a second flattening of the graph.** The
    first draft walked `edges` itself and rebuilt `start`/`delta`, which made
    two arrays of the same 2,959 segments in the same order — and, worse, two
    slightly different ones: `Segments.of` skips an edge whose polyline has
    fewer than two points and this did not. Derived here so the two cannot
    disagree about what a segment is.

    What it adds is the two things `Segments` has no reason to carry: the
    heading this join matches on, and the drawn width the underfill is measured
    against.
    """

    segments: Segments
    heading_deg: np.ndarray
    edge_id: np.ndarray
    width_m: np.ndarray
    # Whether the segment has a direction at all. False for a zero-length one,
    # whose heading above is `arctan2(0, -0)` and means nothing.
    drawn: np.ndarray

    @staticmethod
    def of(segments: Segments, drawn_width_m: dict[int, float]) -> Network:
        """Per-segment heading and drawn width over an existing `Segments`.

        ⚠️ **`drawn_width_m` comes from `roadsurface.json`, not from
        `roadgraph.json`.** The graph publishes the *authored* width,
        `lanes x lane_width_m`, while the ribbon is drawn at
        `max(width_m, floor_for(...))` — `surface.py`'s own manifest docstring says
        a consumer must read the surface table rather than assume, and that
        off-grade edges are the case where the two coincide. Reading the graph
        here made `underfill_m` p50 **0.22 m** where the drawn ribbon it claimed
        to measure reads **4.04 m**, an 18x error in a published number, and it
        is what `railings.py` already reads this same file to avoid.
        """
        delta = segments.delta[:, [0, 2]]
        edge_id = segments.edge
        return Network(
            segments=segments,
            heading_deg=np.degrees(np.arctan2(delta[:, 0], -delta[:, 1])) % 180.0,
            drawn=(delta**2).sum(axis=1) > 0.0,
            edge_id=edge_id,
            # An edge the surface stage drew no ribbon for has no drawn width to
            # measure against; NaN rather than the authored width, so it drops
            # out of the percentiles instead of quietly contributing the wrong
            # quantity.
            width_m=np.array([drawn_width_m.get(int(one), math.nan) for one in edge_id]),
        )

    def distances(self, point: np.ndarray) -> np.ndarray:
        """Plan distance from `point` to every segment.

        `Segments.nearest`'s projection with the winner-take-all dropped — the
        gap the height join used to record: a caller that needs every distance
        cannot use a helper that returns only the winner.
        """
        return plan_projections(
            point, self.segments.start[:, [0, 2]], self.segments.delta[:, [0, 2]]
        )[1]


def _host(network: Network, marking: Marking, spec: RoadMarks) -> Host | None:
    """The level-0 edge this marking belongs to, or None if none is in range.

    🔴 **Chosen by transversality, not by proximity, and this is the one place
    this stage departs from `arrows.py` and `boxjunctions.py`.** Both of those
    take the nearest level-0 edge and both are right to — an arrow sits mid-lane
    and a box sits mid-junction, so the nearest centreline is the one they
    belong to. A stop line sits at a junction **mouth**: it is drawn across the
    minor road while lying a metre off the *major* road's kerb, so proximity
    hands it the wrong host by construction. `RM1013`'s midpoint is p50 1.10 m
    from the nearest centreline and p90 3.30.

    Measured over the region before this shipped, as `|90 - angle to host|`:

        join                RM1011                       RM1013
        nearest edge        p50 10.8, over 30 deg 47/120  p50 16.5, 28/83
        transverse pick     p50  1.8, over 30 deg  5/120  p50  4.0,  8/83

    and the two disagree about the host on **53 of 120** and **36 of 83**.

    ⚠️ **A wrong host does not move the paint**, because the extent is
    published. It moves the height, the refusal and every counter — and two arms
    of one junction disagree about the deck by up to a measured 0.43 m where
    they meet (`Q92`), so it is a bar sunk into or
    floating over the asphalt at the one place the player is looking.

    The score is angular error plus `proximity_weight_deg_per_m` per metre, so
    distance breaks ties between candidates that are equally square and never
    decides between candidates that are not. Returning None means no segment was
    within `host_radius_m` at all; a host whose residual then exceeds
    `bearing_tolerance_deg` is returned and refused by the caller, so the
    residual can be recorded before the guard.
    """
    midpoint = marking.midpoint
    distance = network.distances(midpoint)
    # ⚠️ **A zero-length segment is excluded, not scored.** `arctan2(0, -0)` is
    # pi, so a repeated vertex would enter the transversality score carrying an
    # invented heading of 0 deg — and a repeated vertex is *legal* in the
    # published graph, which `surface.dedupe` and `clearance.py` both record.
    # `read_markings` drops them on the marking side for the same reason. The
    # region's 2,959 level-0 segments contain none today, so this is latent.
    in_range = np.flatnonzero((distance <= spec.host_radius_m) & network.drawn)
    if not len(in_range):
        return None

    gap = np.abs(marking.axis_deg - network.heading_deg[in_range]) % 180.0
    # The angle between the marking and the candidate, folded to 0-90.
    crossing = np.minimum(gap, 180.0 - gap)
    # 🔴 **The two axes score OPPOSITE quantities off the same angle**, and that
    # is the whole of what lets one stage draw both. A stop line wants the edge
    # it is square across, so its residual is the distance from 90. A double
    # white line runs *along* the carriageway, so its residual is the angle
    # itself. ⚠️ **The bar is shared and means the same thing in both** — degrees
    # of error away from the axis this marking is supposed to lie on — so
    # `bearing_tolerance_deg` needs no second value, and `axis_residual_deg`
    # stays one distribution over the two.
    residual = np.abs(90.0 - crossing) if marking.mark.transverse else crossing
    if marking.mark.oblique:
        # 🔴 **No axis, so no residual** (`P3-35g3`): a hatch stripe lies at
        # whatever angle the island's taper gave it, and scoring that angle would
        # hand it to whichever road happened to run across it. Zero for every
        # candidate leaves the score to proximity and the pick to the `on`
        # preference below — and ⚠️ `build_region` keeps these zeros OUT of
        # `axis_residual_deg`, which grades a rule this marking does not take.
        residual = np.zeros_like(crossing)
    score = residual + spec.proximity_weight_deg_per_m * distance[in_range]
    if not marking.mark.transverse:
        # 🔴 **A line painted ALONG a road is hosted by a road it lies ON, where
        # there is one** (`Q132`). Scored on angle alone, a line on one
        # carriageway of a multi-carriageway road picks whichever centreline in
        # 20 m is a fraction of a degree more parallel and is then refused by
        # `_on_its_own_carriageway` for standing beside it — 44 of 143 `RM1001`
        # and 55 of 201 `RM1101` went that way. Both bars already exist: the
        # candidate's own drawn half-width, and `bearing_tolerance_deg`. Where no
        # candidate passes both, the old pick stands and is refused as before.
        on = (distance[in_range] <= 0.5 * network.width_m[in_range]) & (
            residual <= spec.bearing_tolerance_deg
        )
        if on.any():
            score = np.where(on, score, np.inf)
    winner = int(np.argmin(score))
    chosen = int(in_range[winner])
    nearest = int(np.argmin(distance))
    return Host(
        segment=chosen,
        edge_id=int(network.edge_id[chosen]),
        residual_deg=float(residual[winner]),
        distance_m=float(distance[chosen]),
        width_m=float(network.width_m[chosen]),
        disagrees=bool(network.edge_id[chosen] != network.edge_id[nearest]),
        distance_m_all=distance,
    )


# --------------------------------------------------------------------------
# Plan geometry
# --------------------------------------------------------------------------
#
# Everything below works in the game's `(x, z)` plan. ⚠️ **Winding: a triangle
# wound counter-clockwise in `(x, z)` faces the ground.** The frame the maths is
# done in is `(x, -z)` wherever orientation matters, so that the classic
# positive-area convention comes out facing `+Y` — and `downward_facing` plus
# `RoadMarkReport.inverted` are what actually hold that end, as they do for
# arrows and boxes.


def _point_at(line: np.ndarray, along: np.ndarray, distance: float) -> np.ndarray:
    """The point `distance` metres along the polyline."""
    index = int(np.clip(np.searchsorted(along, distance, side="right") - 1, 0, len(line) - 2))
    span = along[index + 1] - along[index]
    fraction = 0.0 if span <= 0.0 else (distance - along[index]) / span
    return line[index] + fraction * (line[index + 1] - line[index])


def band_quads(marking: Marking, spec: RoadMarks) -> list[np.ndarray]:
    """The marking as flat quads facing `+Y`, one per band, mark and station.

    Walked by arclength so a polyline with a bend is handled the same way as the
    straight two-point line 192 of the region's 211 parts actually are. Every
    cut point is a station, a module boundary **or a vertex of the source line**
    — the last of those is what keeps each quad inside one segment, so its two
    ends share one perpendicular and the quad is a true rectangle. The cost is a
    hairline notch on the outside of a bend, at 200 mm wide and on the 19 parts
    in region that bend at all.

    ⚠️ **The dash phase is anchored at the start of the line, not centred on
    it.** The publisher draws the line and not the dashes; where a real gap
    falls inside a 600/300 module is not published anywhere, so anchoring is a
    choice, and anchoring at an end the source *does* publish is the one that
    does not also invent a symmetry.
    """
    mark = marking.mark
    along = marking.along_m
    total = float(along[-1])
    # ⚠️ **The DRAWN width, which is not the published one for a longitudinal
    # marking** — see `RoadMarks.longitudinal_legibility_scale`. The offsets take
    # the same scale, so the pair keeps the sheet's shape at the drawn size.
    scale = spec.longitudinal_legibility_scale
    half = 0.5 * mark.drawn_line_width_m(scale)
    offsets = mark.drawn_band_offsets_m(scale)
    if marking.is_chevron:
        # The sheet's `CHEVRON WIDTH`, which no legibility scale touches: it is a
        # broad stroke already, and `_require`d beside the turn that selects it.
        half = 0.5 * float(mark.chevron_width_m)

    # 🔴 **One pass per module, and a marking whose lines share one is a single
    # pass in the order it always was** — so `RM1001` and the transverse bars are
    # byte-identical. `RM1002`/`RM1003` break ONE line of the pair (`Q132`): the
    # continuous line is a pass over the whole length and the broken one a pass
    # over the module's runs.
    broken = mark.broken_bands()
    unbroken_offsets = [o for o, b in zip(offsets, broken, strict=True) if not b]
    broken_offsets = [o for o, b in zip(offsets, broken, strict=True) if b]
    passes = [(unbroken_offsets, [(0.0, total)])]
    if broken_offsets:
        passes.append((broken_offsets, _runs(mark, total)))

    quads: list[np.ndarray] = []
    for bands, runs in passes:
        if not bands:
            continue
        for start, stop in runs:
            cuts = _cuts(start, stop, along, spec.station_m)
            for head, tail in pairwise(cuts):
                middle = np.searchsorted(along, 0.5 * (head + tail), side="right") - 1
                index = int(np.clip(middle, 0, len(marking.line) - 2))
                step = marking.line[index + 1] - marking.line[index]
                direction = step / np.linalg.norm(step)
                # 🔴 **RIGHT of the digitised direction in the `(x, z)` plan** —
                # east is `+x` and north is `-z`, so heading east this points
                # south. It read "left of travel" while every marking was
                # symmetric and the sign could not matter; `RM1002`/`RM1003` are
                # not, and `RoadMark.broken_bands` is written against this frame.
                across = np.array([-direction[1], direction[0]])
                first = _point_at(marking.line, along, head)
                last = _point_at(marking.line, along, tail)
                for offset in bands:
                    quads.append(_band_quad(first, last, across, offset, half))
    if marking.is_chevron:
        quads.append(_apex(marking.line, half))
    return quads


def _apex(line: np.ndarray, half: float) -> np.ndarray:
    """The outside of a chevron's point, which its two leg quads leave open.

    Each leg is a rectangle square to itself, so at the V they overlap on the
    inside and gape on the outside — a hairline at 150 mm and a 0.45 m bite out
    of the tip at 900. A bevel between the two outer corners, not a mitre: 40 of
    Wan Chai's chevrons turn past 120 deg, where a mitred point runs to four
    times the half-width and further.
    """
    arrive, leave = line[1] - line[0], line[2] - line[1]
    turn = float(arrive[0] * leave[1] - arrive[1] * leave[0])
    # The outer side is away from the turn.
    side = -1.0 if turn > 0.0 else 1.0
    corners = [
        side * half * np.array([-step[1], step[0]]) / np.linalg.norm(step)
        for step in (arrive, leave)
    ]
    return wound_up(np.array([line[1], line[1] + corners[0], line[1] + corners[1]]))


def _band_quad(
    first: np.ndarray, last: np.ndarray, across: np.ndarray, offset: float, half: float
) -> np.ndarray:
    """One band's quad between two stations, wound to face `+Y`.

    `across` is the marking's own perpendicular, `offset` the band's centre
    across it and `half` half the drawn line width. Which side `across` points
    does not matter and could not: the bands are symmetric about the published
    line and each is symmetric about its own centre, so a flipped normal draws
    the same marking.
    """
    centre = offset * across
    return wound_up(
        np.array(
            [
                first + centre - half * across,
                first + centre + half * across,
                last + centre + half * across,
                last + centre - half * across,
            ]
        )
    )


def _runs(mark: RoadMark, total: float) -> list[tuple[float, float]]:
    """The painted intervals along a marking of length `total`.

    One interval for a continuous line; one per module for a dashed one, the
    last of them clipped where the line ends rather than overrun.
    """
    if mark.continuous:
        return [(0.0, total)]
    period = mark.mark_m + mark.gap_m  # type: ignore[operator]  # `continuous` covers None
    runs: list[tuple[float, float]] = []
    # ⚠️ `index * period`, never `start += period`. See `_MIN_MARK_M`.
    for index in range(math.ceil(total / period)):
        start = index * period
        stop = min(start + mark.mark_m, total)  # type: ignore[operator]
        if stop - start > _MIN_MARK_M:
            runs.append((start, stop))
    return runs


def _cuts(start: float, stop: float, along: np.ndarray, station_m: float) -> np.ndarray:
    """`[start, stop]` split at every station boundary and every source vertex.

    ⚠️ **Cuts closer together than `_MIN_MARK_M` are merged**, for that
    constant's own reason and against the same failure. `first` is meant to put
    the first station strictly inside the run, but where `start` sits a few ULPs
    below a station multiple it lands essentially *on* it — measured at
    **7.1e-15 m** on a real `RM1013` run — and the hairline quad that follows
    pollutes `slivers_dropped`, a published counter this stage asks readers to
    trust. Latent rather than live today: the marking it fires on is one the
    bearing guard already refuses.
    """
    first = math.floor(start / station_m) + 1
    last = math.ceil(stop / station_m) - 1
    stations = np.arange(first, last + 1, dtype=np.float64) * station_m
    vertices = along[(along > start) & (along < stop)]
    ordered = np.unique(np.concatenate([[start], stations, vertices, [stop]]))
    keep = np.concatenate([[True], np.diff(ordered) > _MIN_MARK_M])
    # The run's own end is never dropped: merging towards it would shorten the
    # painted mark, where merging away from it only removes a hairline.
    keep[-1] = True
    return ordered[keep]


# The accumulator is `meshbuild.FlatBuilder` — `arrows.py`'s channel decision
# (position and normal only; the colour is authored in
# `game/tuning/roadmarks.tres`, `Q53`). This asset is the one most exposed to
# the sliver bar: a give-way dash is 600 mm by 200 mm, so its fan's long
# diagonal is the needle the import lattice can flip.


def _import_quantum_m(markings: list[Marking]) -> float:
    """The plan pitch Godot's importer will quantise this mesh to.

    `boxjunctions._import_quantum_m`, over the **candidates'** extent rather
    than the drawn mesh's — the pitch is a property of the region's size, not a
    number anyone should tune, and taking it before the join is what lets the
    lattice guard run before anything is built. Conservative in the safe
    direction: the shipped mesh's own AABB gives 0.024985 against the published
    0.025187, so the bar is if anything slightly strict.
    """
    if not markings:
        return 0.0
    return import_quantum_m(np.vstack([marking.line for marking in markings]))


def _drawn_widths(surface: dict) -> dict[int, float]:
    """Each level-0 edge's **drawn** carriageway width, from `roadsurface.json`.

    ⚠️ **Not `roadgraph.json`'s `width_m`, and the difference is 18x on the one
    number that reads it.** The graph publishes the *authored* width,
    the graph's own `width_m`; the ribbon is drawn at `max(width_m, floor_for(...))`,
    and `surface.py`'s manifest docstring is explicit that a consumer must read
    the surface table rather than assume — off-grade edges being the case where
    the two coincide. `underfill_m` measures a drawn bar against a drawn kerb,
    so the drawn width is the only one that answers it: against the authored
    width it read p50 0.22 m, against the ribbon 4.04 m.

    Averaged over the edge's own stations because `half_width_m` is per station
    since `Q23` — a level-0 edge climbing onto a ramp is widened along part of
    its length — and a marking is matched to a segment rather than to a station.
    The whole quantity is a report-only cost figure, so the mean is honest where
    carrying the profile would imply a precision the match does not have.

    `railings.py` already reads this file for this same half-width. The document
    itself is read once by the caller and handed here, because `Q92` gave this
    stage a second thing to take from it — the junction caps `DrawnSurface`
    reads — and two reads of one manifest is two chances to read two versions.
    """

    # 🔴 **The CORRIDOR where the surface publishes one** (`Q129`, `P3-33c`). At
    # level 0 `half_width_m` is the host's TERRITORY — its share of a carriageway
    # it may share with another centreline — and both readers of this number mean
    # the carriageway: a stop line is painted kerb to kerb, and a double white
    # line between two opposed flows lies exactly ON the boundary of their two
    # territories, where a bar of one share refuses it at the margin. Measured:
    # 91 double white lines drawn fell to 66 on the share and the refusals rose
    # 52 -> 77. `clearance` walks the same table for the same reason.
    def half_widths(entry: dict) -> list[float]:
        return entry.get("corridor_half_width_m", entry["half_width_m"])

    return {
        int(entry["edge"]): 2.0 * float(np.mean(np.asarray(half_widths(entry), dtype=np.float64)))
        for entry in surface["carriageway"]
        if len(entry["half_width_m"])
    }


def _check_marks_clear_the_lattice(spec: RoadMarks, thinness_bar_m: float) -> None:
    """Refuse a region whose smallest configured mark is a sliver by construction.

    🔴 **The silent failure this exists for.** `_import_quantum_m` derives the
    lattice pitch from the *region's own extent*, so the sliver bar grows with
    the region while a give-way dash stays 600 x 200 mm. Past an extent of about
    6.2 km every `RM1013` dash is dropped as thin — the give-way lines vanish
    from the mesh, `drawn_by_id` still reports 75 of them, and the only trace is
    `slivers_dropped` jumping. With `P3-20`'s GIVE WAY plates already on the
    street that renders as 74 signs over bare asphalt.

    Wan Chai's extent is 1,637 m against the 6,217 m where this trips, a 3.8x
    margin — so this never fires today and is written for the second city, which
    is the whole reason the ETL is city-agnostic. Raised rather than counted:
    a region that cannot draw its own smallest marking is a build to stop, not
    a number to publish.
    """
    for mark in spec.marks:
        length = mark.line_width_m if mark.continuous else min(mark.mark_m, mark.line_width_m)  # type: ignore[type-var]
        span = mark.line_width_m if mark.continuous else mark.mark_m
        # The bar `FlatBuilder.build` applies: twice-area against the longest plan
        # edge, which for a rectangle is twice its width.
        twice_area = span * mark.line_width_m  # type: ignore[operator]
        longest = math.hypot(span, mark.line_width_m)  # type: ignore[arg-type]
        if twice_area < thinness_bar_m * longest:
            raise ValueError(
                f"road_marks:{mark.id} draws a {length} m x {mark.line_width_m} m mark, which is "
                f"thinner than the import lattice bar {thinness_bar_m:.4f} m for a region this "
                f"size. Every one would be dropped as a sliver and the manifest would still "
                f"report them drawn"
            )


def _on_its_own_carriageway(marking: Marking, host: Host) -> bool:
    """Whether this marking lies on the ribbon of the edge it matched.

    🔴 **A longitudinal marking must be ON its host, and the bar is that host's
    own drawn half-width rather than a number anyone chose.** `DrawnSurface`
    reads the highest drawn surface covering a plan point, which is the right
    rule for a bar at a junction mouth and no rule at all where a level-0 ramp
    climbs beside a street. ⚠️ **Two separate facts, and they are not the same
    edges**: level-0 heights climb by up to **7.87 m** along a single edge here
    (`e465` CROSS HARBOUR TUNNEL, which is *not* on structure), and **16** other
    level-0 edges do stand on structure. Either way two level-0 ribbons stack in
    plan, and nothing published says which one the paint sits on.
    Measured: refusing these took the buried share
    `tools/paint_clearance.py` gates from **1.50% to 0.21%** and the worst height
    spread across one marking from **4.51 m to 1.18 m**.

    ⚠️ **Transverse markings are exempt, and that is not an oversight.** A stop
    line at a four-lane mouth is *supposed* to sit a long way from the centreline
    it is square across — `host_distance_m` reads p90 16.1 m on this layer — so
    the same bar would refuse the markings `P3-23` exists to draw.

    ⚠️ **This is a refusal and never a correction** (`Q54`): the paint is not
    moved onto a road, it is left undrawn and counted, because nothing published
    says which of the two stacked ribbons it belongs to.

    ⚠️ **`host.width_m` is `_drawn_widths`' edge MEAN, and that function calls
    itself a report-only figure — this gates on it, so the gap is stated rather
    than assumed.** Two things could make it wrong and both are measured on this
    region: the ribbon is `[offset - half, offset + half]` per station and not
    `±half` about the centreline (`Q106`) — 🔴 **and "`offset_m` is exactly 0.0 on
    all 737 level-0 edges", which this paragraph said, EXPIRED at `P3-33c`**: 288
    of 734 level-0 ribbons now sit more than 1 m off their centreline, so this bar
    is asked about the centreline where the road may not be. It errs toward
    refusing, which is the safe side, and an oblique marking (`P3-35g3`) meets no
    other bar — `host_off_carriageway_m_by_id` is what it costs; and the half-width
    varies per station since
    `Q23`, but on **721 of 737** edges it does not vary at all. The **16** that do
    — up to 4.319 m — are the ramp-climbers, which is the same population this
    refusal exists to catch, so where the mean is least representative is where
    the answer is least in doubt.

    ⚠️ **A midpoint measure, like everything else `Host` carries.** A marking
    that crosses its host reads 0.0 however far its ends stray, so this catches a
    line lying *beside* the wrong road and not one lying across it — which is
    what the bearing guard is for, and why the two refusals are separate.
    """
    if marking.mark.transverse:
        return True
    return host.distance_m <= 0.5 * host.width_m


# --------------------------------------------------------------------------
# The inferred join between two opposed carriageways (`Q125`)
# --------------------------------------------------------------------------
#
# 🔴 **The one placement in this stage that is not published, and it is drawn
# only where the publisher is silent.** Where a dual carriageway is two one-way
# edges, the line between the flows belongs to neither half's geometry:
# `surface.py` pairs them and publishes `opposed_pairs`, and what follows walks
# the line midway between the two centrelines, cuts out every stretch a
# surveyed `RM1001` already covers, and draws the rest as that same mark.
#
# 🔴 **`Q117` drew this in the shader and `Q118` switched it off**, because a
# shader line and a surveyed line fought wherever both existed — near-coincident,
# thickened and speckled — and the shader has no way to yield for part of an
# edge. Measured on Wan Chai before this was built: of 95 pairs, **13** are
# covered by survey end to end, **24** are partly covered and **58** carry no
# surveyed line at all. A per-edge switch is wrong in both positions on 24 of
# them, which is why the cut is per metre and why it lives here rather than in
# `TEXCOORD_1` — a flat per-strip code cannot say "from here to there".
#
# ⚠️ **Nothing here enters the stage's two partitions.** They are over what the
# publisher drew; this is what the project inferred, and it is counted apart.


@dataclass(frozen=True)
class Join:
    """One inferred centre line, between the two halves of a dual carriageway."""

    # The paired edges, as `roadgraph.json` ids. `here` is the lower of the two
    # and owns the line: the join is one marking, not one per half, and the
    # shader's `centre_step` is the same finding said once per half because a
    # lane coordinate is all it has.
    here: int
    there: int
    # What `surface.py` measured between the two ribbons. The bar for a survey
    # line to count as covering this join is half of it — the survey line lies
    # between the two centrelines, so it cannot be further from the join than
    # the join is from either half.
    gap_m: float
    # The line itself, `(n, 2)` as `(x, z)`, midway between the two centrelines.
    line: np.ndarray


def opposed_joins(surface: dict, edges: Sequence[dict], spec: RoadMarks) -> list[Join]:
    """The inferred centre line of every opposed pair `surface.py` published.

    Built as the **midpoint of the two centrelines, per station**, rather than
    as an offset from one of them. The two readings agree wherever the halves
    run parallel, which is most of a dual carriageway; where they splay into a
    junction the midpoint stays between the flows and an offset does not.

    ⚠️ **Only where each half is actually beside the other.** A station whose
    partner projection lands on the partner's *end* is one running past where
    the other half stopped, so the join would carry on down a single
    carriageway — and a pair is only a pair where both halves exist. Those
    stations end the run rather than being clamped onto it, so one pair can
    yield several runs.

    ⚠️ **The separation bar is the pairing's own and carries no knob.**
    `surface._opposed_gaps` publishes a pair where the halves run within the
    drawn width of each other; this asks the same question per station, against
    the narrower of the two ribbons, so a pair that splays apart mid-block ends
    its join there instead of drawing a line across the ground between them.
    `Q72` refused a pairing rule with a free radius, and there is none here to
    sweep.
    """
    plans = {int(edge["id"]): _plan_of(edge) for edge in edges}
    trimmed: dict[int, np.ndarray] = {}
    for entry in surface["carriageway"]:
        plan = plans.get(int(entry["edge"]))
        line = None if plan is None else _drawn_centreline(entry, plan)
        if line is not None:
            trimmed[int(entry["edge"])] = line
    widths = _drawn_widths(surface)

    joins: list[Join] = []
    for here, there, gap_m in surface["opposed_pairs"]:
        here, there = int(here), int(there)
        own, partner = trimmed.get(here), trimmed.get(there)
        if own is None or partner is None:
            continue
        reach = min(widths.get(here, 0.0), widths.get(there, 0.0))
        for run in _join_runs(own, partner, reach, spec.station_m):
            joins.append(Join(here=here, there=there, gap_m=float(gap_m), line=run))
    return joins


def _plan_of(edge: dict) -> np.ndarray | None:
    """One graph edge's polyline as `(n, 2)` plan, or None where it has none."""
    points = np.asarray(edge["polyline"], dtype=np.float64)
    return points[:, [0, 2]] if len(points) >= 2 else None


def _drawn_centreline(entry: dict, plan: np.ndarray) -> np.ndarray | None:
    """An edge's centreline over the stretch the ribbon is actually drawn on.

    ⚠️ **Trimmed, because the join must not run into a junction.** `trim_m` is
    how far each end is held back so the cap can fill the middle, and a centre
    line drawn across a cap is a line through the middle of a junction — which
    is what the shader's `fade_m` keeps it out of on the layer this replaces.
    The trims are `surface.py`'s own number and travel in the same manifest.
    """
    along = plan_lengths_2d(plan)
    start, end = (float(value) for value in entry["trim_m"])
    low, high = start, float(along[-1]) - end
    if high - low <= _MIN_MARK_M:
        return None
    return _slice(plan, along, low, high)


def _join_runs(
    own: np.ndarray, partner: np.ndarray, reach_m: float, station_m: float
) -> list[np.ndarray]:
    """The midline between two drawn centrelines, in runs where both are there."""
    along = plan_lengths_2d(own)
    stations = _cuts(0.0, float(along[-1]), along, station_m)
    partner_along = plan_lengths_2d(partner)

    runs: list[np.ndarray] = []
    current: list[np.ndarray] = []
    for distance in stations:
        point = _point_at(own, along, float(distance))
        near = _nearest_on(partner, partner_along, point)
        # `beyond` means the partner stopped here; `>= reach` means the two have
        # splayed past the separation the pairing was found at.
        if near.beyond or near.gap_m >= reach_m:
            runs.extend(_closed(current))
            current = []
            continue
        current.append(0.5 * (point + near.foot))
    runs.extend(_closed(current))
    return runs


def _closed(points: list[np.ndarray]) -> list[np.ndarray]:
    """A run of midpoints as a polyline, or nothing where it has no length.

    Repeated points are dropped for `read_markings`' reason: a zero-length step
    has no direction to take a perpendicular from, and two stations can land on
    one midpoint where the partner doubles back.
    """
    if len(points) < 2:
        return []
    line = np.asarray(points, dtype=np.float64)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(line, axis=0), axis=1) > _MIN_MARK_M])
    line = line[keep]
    return [line] if len(line) >= 2 else []


class _Nearest(NamedTuple):
    """One polyline's nearest point to another point, and where it sits."""

    at_m: float
    foot: np.ndarray
    gap_m: float
    # Whether the point lies past an END of the line rather than beside it.
    # ⚠️ **Not `at_m` being 0 or the total**, which is the reading this was
    # written as first: a point exactly opposite the last vertex has its
    # perpendicular foot *on* that vertex and is squarely beside the line, so
    # that test dropped a station at each end of every join it built.
    beyond: bool


def _nearest_on(line: np.ndarray, along: np.ndarray, point: np.ndarray) -> _Nearest:
    """Where `line` comes nearest to `point`, and whether that is past its end.

    ⚠️ **Not `Segments.nearest`, and the difference is the whole of what this
    is for.** That one searches the level-0 *network* for the nearest segment of
    any edge; this asks one polyline where its own nearest point is, and answers
    the second question with it, so a caller can tell a station beside its
    partner from one past the end of it.
    """
    first, step = line[:-1], np.diff(line, axis=0)
    raw, gaps = plan_projections(point, first, step)
    fraction = raw.clip(0.0, 1.0)
    index = int(np.argmin(gaps))
    # The segment's own length is the step in `along`, so the foot's distance
    # along the line costs no second square root.
    at = float(along[index] + fraction[index] * (along[index + 1] - along[index]))
    # Past the end only where the winning foot is the line's own first or last
    # vertex and the point is on the far side of it. An interior corner is a
    # foot at a vertex too, and it is beside the line.
    beyond = (index == 0 and raw[0] < 0.0) or (index == len(step) - 1 and raw[-1] > 1.0)
    foot = first[index] + fraction[index] * step[index]
    return _Nearest(at, foot, float(gaps[index]), bool(beyond))


def _covered(join: Join, markings: Sequence[Marking], spec: RoadMarks) -> list[tuple[float, float]]:
    """Where a surveyed marking already runs beside this join, along the join.

    🔴 **This is the counter-bearing half of `Q125`: the invention yields to the
    survey, per metre.** A surveyed line covers the join where it runs *beside*
    it — within half the pair's own separation — and *along* it, within the same
    `bearing_tolerance_deg` that decides whether a longitudinal marking lies on
    its host. Both bars are values that already exist; a line that crosses the
    join covers nothing, which is what the angle test is for.

    ⚠️ **Walked segment by segment, at the marking's own stations**, so a long
    survey line that runs beside the join for part of its length covers that
    part and no more. Taking a whole marking as covering or not covering was the
    per-edge switch this stage measured itself out of.
    """
    along = plan_lengths_2d(join.line)
    total = float(along[-1])
    limit = math.cos(math.radians(spec.bearing_tolerance_deg))
    reach = 0.5 * join.gap_m
    low, high = join.line.min(axis=0), join.line.max(axis=0)
    spans: list[tuple[float, float]] = []
    for marking in markings:
        # ⚠️ **A bounding-box reject, and it is exact rather than a heuristic.**
        # Box separation is a lower bound on the true distance from a point to
        # this line, so a marking whose box padded by `reach` misses the join's
        # cannot hold a single segment inside the test below — it contributes no
        # span, and `_merged` sorts what it is given, so dropping it changes
        # nothing. ⚠️ **Non-strict**, because a marking exactly `reach` away is
        # one the test keeps.
        #
        # A join is ~56 m of a 1.5 km region, so without this every join walks
        # every marking: **6,292 marking visits where 43 are geometrically
        # possible**, and the stage cost **7.6 s against the 1.2 s** `Q118`
        # measured it at. With it, 0.06 s and the same spans to the bit.
        if (marking.line.min(axis=0) - reach > high).any():
            continue
        if (marking.line.max(axis=0) + reach < low).any():
            continue
        line, walked = marking.line, marking.along_m
        cuts = _cuts(0.0, marking.length_m, walked, spec.station_m)
        # `along_m` is a property that re-walks the line, so it is taken once
        # rather than per cut.
        points = [_point_at(line, walked, float(cut)) for cut in cuts]
        for head, tail in pairwise(points):
            step = tail - head
            length = float(np.linalg.norm(step))
            if length <= _MIN_MARK_M:
                continue
            # ⚠️ **`beyond` is deliberately not consulted here**, where
            # `_join_runs` turns on it: a survey line running past the join's
            # end has both feet clamped onto that end, so its span collapses and
            # the test below refuses it; one foot clamped is a line entering the
            # join's range from outside, and clamping is exactly the reading
            # wanted — it covers the part that overlaps and no more.
            at_head = _nearest_on(join.line, along, head)
            at_tail = _nearest_on(join.line, along, tail)
            if max(at_head.gap_m, at_tail.gap_m) > 0.5 * join.gap_m:
                continue
            # The join's own direction where this piece lies against it, which
            # is the span between the two feet — so a survey line crossing the
            # join reads as perpendicular however close it passes.
            span = abs(at_tail.at_m - at_head.at_m)
            if span <= _MIN_MARK_M or span / length < limit:
                continue
            spans.append((min(at_head.at_m, at_tail.at_m), max(at_head.at_m, at_tail.at_m)))
    return _merged(spans, total)


def _merged(spans: list[tuple[float, float]], total: float) -> list[tuple[float, float]]:
    """Overlapping spans unioned and clipped to `[0, total]`."""
    united: list[tuple[float, float]] = []
    for start, stop in sorted((max(0.0, a), min(total, b)) for a, b in spans):
        if stop - start <= _MIN_MARK_M:
            continue
        if united and start <= united[-1][1]:
            united[-1] = (united[-1][0], max(united[-1][1], stop))
        else:
            united.append((start, stop))
    return united


def _gaps_between(spans: Sequence[tuple[float, float]], total: float) -> list[tuple[float, float]]:
    """The complement of `spans` in `[0, total]` — what no survey line covers.

    ⚠️ Expects `spans` sorted and non-overlapping, which is what `_merged`
    returns and the only thing any caller passes; handed anything else it walks
    them in the order given and answers wrongly rather than raising.
    """
    free: list[tuple[float, float]] = []
    edge = 0.0
    for start, stop in spans:
        if start - edge > _MIN_MARK_M:
            free.append((edge, start))
        edge = max(edge, stop)
    if total - edge > _MIN_MARK_M:
        free.append((edge, total))
    return free


def _overlap_m(left: Sequence[tuple[float, float]], right: Sequence[tuple[float, float]]) -> float:
    """Metres two sets of spans have in common."""
    return sum(
        max(0.0, min(a_stop, b_stop) - max(a_start, b_start))
        for a_start, a_stop in left
        for b_start, b_stop in right
    )


def _slice(line: np.ndarray, along: np.ndarray, start: float, stop: float) -> np.ndarray:
    """The piece of a polyline between two distances along it, ends included."""
    inside = line[(along > start + _MIN_MARK_M) & (along < stop - _MIN_MARK_M)]
    head = _point_at(line, along, start)
    tail = _point_at(line, along, stop)
    return np.vstack([[head], inside, [tail]])


def draw_opposed_joins(
    builder: FlatBuilder,
    joins: Sequence[Join],
    surveyed: Sequence[Marking],
    refused: Sequence[Marking],
    spec: RoadMarks,
    drawn: DrawnSurface,
    above: Sequence[DrawnSurface],
    report: RoadMarkReport,
    thin_m: float,
) -> None:
    """Draw each join's uncovered stretches, and book what the survey covered.

    ⚠️ **`refused` grades rather than gates.** A surveyed line this stage could
    not place — off its own carriageway, or off axis — paints nothing, so the
    join is drawn over that stretch as it is over any other silence. What it is
    not is the same silence: `join_over_refused_survey_m` is where the invented
    line stands in for a reading that failed, and a rise in it is a finding
    about the survey's placement rather than about the join.
    """
    mark = spec.opposed_join
    if mark is None:
        return
    report.join_pairs = len({(join.here, join.there) for join in joins})
    for join in joins:
        along = plan_lengths_2d(join.line)
        total = float(along[-1])
        report.join_m += total
        covered = _covered(join, surveyed, spec)
        report.join_covered_m += sum(stop - start for start, stop in covered)
        free = _gaps_between(covered, total)
        painted: list[tuple[float, float]] = []
        for start, stop in free:
            if stop - start < mark.line_width_m:
                # `read_markings`' bar for a clipped run, in the same terms: a
                # slot this short between two surveyed lines is not a line.
                report.join_refused_m += stop - start
                continue
            painted.append((start, stop))
            report.join_drawn_m += stop - start
            report.joins_drawn += 1
            piece = Marking(code=mark.id, mark=mark, line=_slice(join.line, along, start, stop))
            for quad in band_quads(piece, spec):
                _place(builder, drawn, quad, spec.lift_m, report, thin_m, above)
        report.join_over_refused_survey_m += _overlap_m(painted, _covered(join, refused, spec))


def _check_join_partition(report: RoadMarkReport) -> None:
    """Every metre of join is covered, drawn or refused, and none is two of them.

    Asserted at runtime rather than left to the manifest, on `fence.py`'s
    precedent — *a stage whose own partition does not close is publishing a
    number nobody can read*. The three legs are accumulated in different
    branches, so a leg that stops being booked leaves a published figure that
    still looks like a distribution of something.
    """
    booked = report.join_covered_m + report.join_drawn_m + report.join_refused_m
    if not math.isclose(booked, report.join_m, abs_tol=1e-6):
        raise AssertionError(
            f"the join partition does not close: {report.join_m:.6f} m of join against "
            f"{report.join_covered_m:.6f} covered + {report.join_drawn_m:.6f} drawn + "
            f"{report.join_refused_m:.6f} refused"
        )


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> RoadMarkReport:
    """Read the region's published transverse markings and write `roadmarks.glb`."""
    spec = city.road_marks
    report = RoadMarkReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the same shape `tramway`, `arrows`, `boxjunctions`
        # and `railings` all take: a city whose estate publishes no transverse
        # markings ships none rather than inferring them.
        log.info("city '%s' declares no road_marks block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    region_high = city.region_high(region_id)
    markings = read_markings(
        city, spec, region_id, transform, region_high, report, sources_root=sources_root
    )

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, the restriction every snap in the pipeline makes (`Q15`): a
    # bar under a flyover belongs to the street it is painted on, not the deck.
    edges = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    segments = Segments.of(edges)
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    network = Network.of(segments, _drawn_widths(surface))
    # The road as `surface.py` actually drew it (`Q92`) — the same level
    # restriction as `edges` above, applied to the caps too. A stop line lives
    # *at* a junction mouth, so more of this layer stands on cap tarmac than of
    # any other, and the blend it replaced was furthest wrong exactly there.
    drawn = DrawnSurface.of(surface, level=0)
    # What is drawn OVER the street: one reader per level above 0 that draws
    # anything, so a station past a touchdown can be told from one past a kerb
    # (`stations_on_drawn_structure`). Levels at or below 0 are excluded — a
    # bore under a void is not structure over it — and `of` refuses an empty
    # level, so the list is `levels_drawn`'s and never `elevation_levels`'.
    above = [
        DrawnSurface.of(surface, level=level)
        for level in DrawnSurface.levels_drawn(surface)
        if level > 0
    ]

    builder = FlatBuilder(ROADMARKS_MATERIAL)
    report.import_quantum_m = round(_import_quantum_m(markings), 6)
    thinness_bar_m = 2.0 * report.import_quantum_m
    _check_marks_clear_the_lattice(spec, thinness_bar_m)
    # The two halves of the survey the inferred join yields to (`Q125`): what
    # was drawn, which the join is cut around, and what was refused, which it
    # is drawn over and books a metre against. Both are gathered in the loop
    # below rather than by a second pass, so the join can never disagree with
    # this stage about what it drew.
    join_mark = spec.opposed_join
    surveyed: list[Marking] = []
    refused: list[Marking] = []
    for marking in markings:
        # 🔴 **Any surveyed DIVIDER, not the join's own mark** (`Q132`): with
        # `RM1001` the only longitudinal row the two were one test, and once a
        # broken line can run between two flows the invented double white would
        # be painted on top of it.
        wanted = join_mark is not None and marking.mark.divides_flows
        turn = marking.turn_deg
        if turn is not None and marking.mark.chevron_turn_deg is not None:
            if marking.is_chevron:
                low = report.chevron_straightest_deg
                report.chevron_straightest_deg = turn if low is None else min(low, turn)
            else:
                high = report.outline_sharpest_deg
                report.outline_sharpest_deg = turn if high is None else max(high, turn)
        host = _host(network, marking, spec)
        if host is None:
            report.no_edge_in_range += 1
            continue
        report.host_disagreement += int(host.disagrees)
        # Recorded before the bearing guard — `n` past `drawn` is the proof the
        # distribution can read outside its own filter (`Q58`).
        if not marking.mark.oblique:
            report.axis_residual_deg.append(host.residual_deg)
        # 🔴 **A longitudinal marking must lie ON the road it is hosted to, and
        # the bar is that road's own drawn half-width rather than a number.**
        # Where a level-0 ramp climbs beside a street — heights climb up to
        # 7.87 m along one edge, and 16 others stand on structure — two drawn
        # ribbons stack in plan, and `DrawnSurface.sample` reads the higher
        # (its rule for every overlap) with nothing published to say the line
        # is on that one rather than the lower. A transverse bar is allowed its
        # distant host on purpose (it starts on the far kerb of a four-lane
        # mouth); a line painted *along* a carriageway has no such licence, so
        # this refuses rather than places it wrong (`Q54`).
        if not _on_its_own_carriageway(marking, host):
            report.host_off_carriageway += 1
            off = report.host_off_carriageway_m_by_id
            off[marking.mark.id] = off.get(marking.mark.id, 0.0) + marking.length_m
            if wanted:
                refused.append(marking)
            continue
        if host.residual_deg > spec.bearing_tolerance_deg:
            # Off the axis this marking is supposed to lie on. Transverse, the
            # region's extremes are a 56.9 m `RM1013` lying 78.8 deg off square
            # and a 33.8 m `RM1011` at 88.7; longitudinal, it is a double white
            # line whose nearest road runs across it. Either way a marking this
            # stage has no reading of, refused rather than turned onto a road,
            # which would be an invented marking in `Q54`'s sense.
            report.no_host_on_axis += 1
            if wanted:
                refused.append(marking)
            continue

        if wanted:
            surveyed.append(marking)
        heights: list[float] = []
        for quad in band_quads(marking, spec):
            heights.extend(_place(builder, drawn, quad, spec.lift_m, report, thinness_bar_m, above))

        if marking.is_chevron:
            report.chevrons += 1
            report.chevron_m += marking.length_m
        report.drawn += 1
        report.drawn_by_id[marking.mark.id] = report.drawn_by_id.get(marking.mark.id, 0) + 1
        length = marking.length_m
        report.drawn_m_by_id[marking.mark.id] = (
            report.drawn_m_by_id.get(marking.mark.id, 0.0) + length
        )
        report.mark_length_m.append(length)
        report.host_distance_m.append(host.distance_m)
        # 🔴 **Transverse only, because it is `host width - marking length` and a
        # longitudinal marking's length is measured along the road rather than
        # across it.** Pooled, RM1001's 26.7 m median line against a 10.24 m
        # carriageway would post a -16 m "underfill" and drag a distribution
        # whose whole content is how far a stop line falls short of its own
        # kerb — `Q57`'s two populations under one number, in the one field
        # that cannot survive it.
        if marking.mark.transverse:
            report.underfill_m.append(host.width_m - length)
        if heights:
            report.height_spread_m.append(max(heights) - min(heights))

    # 🔴 **After the survey, because it yields to it.** The joins are built from
    # `surface.py`'s pairing and drawn only where nothing surveyed covers them,
    # so the surveyed set has to be complete before the first metre of invented
    # line is cut (`Q125`).
    draw_opposed_joins(
        builder,
        opposed_joins(surface, edges, spec),
        surveyed,
        refused,
        spec,
        drawn,
        above,
        report,
        thinness_bar_m,
    )
    _check_join_partition(report)

    mesh = builder.build(ROADMARKS_MESH_NAME, thinness_bar_m, report)
    if mesh is not None:
        report.inverted, report.inverted_area_m2 = downward_facing(mesh)
        report.triangles = mesh.triangle_count
        report.vertices = len(mesh.positions)
        low, high = mesh.aabb()
        report.aabb = [list(low), list(high)]
        report.bytes = write_glb(out_dir / ROADMARKS_NAME, [mesh])

    _write_manifest(out_dir, city, region_id, report)
    return report


def _place(
    builder: FlatBuilder,
    drawn: DrawnSurface,
    quad: np.ndarray,
    lift_m: float,
    report: RoadMarkReport,
    thin_m: float = 0.0,
    above: Sequence[DrawnSurface] = (),
) -> list[float]:
    """One band quad onto the road under it, each vertex at its own drawn height.

    `boxjunctions._place`, for this layer: the same `DrawnSurface.sample` per
    vertex (`Q92`), the same counters, and 🔴 **the same cut along the road's
    creases first** — a quad across a station line on the `e311` ramp chorded
    10-18 mm under it on the shipped bundle with every corner right, and the
    cut is what closes that by construction. Returns the road heights so the
    caller can publish their spread. Kept as a function rather than inlined in
    `build_region` so the placement half of this stage has a seam a test can
    reach, which it did not.

    🔴 **A piece over nothing at level 0 and under a deck drawn in `above` is
    refused, after the cut and before the counters** (`Q92`'s deck stub). The
    cut has already parted the quad at the host strip's end line, so the piece
    past the touchdown is exactly what stands over the void and the piece on
    the ramp is placed as it was. `above` empty — a region with no level drawn
    above the street — refuses nothing, and a void piece with no deck over it
    is placed and counted in `vertices_over_void` as before.

    ⚠️ **The inferred join is placed by exactly this function** (`Q125`), void
    rule included: the measured population of join pieces over nothing drawn is
    **zero**, so a refusal of its own would be a rule this region never
    exercises — and a published extent over void is kept here for `Q54`'s
    reason, which is a reason about who drew the extent.
    """
    sampled = drawn.sampled_pieces(quad, thin_m=thin_m)
    report.polygons_placed += 1
    report.polygons_split += int(len(sampled) > 1)
    heights: list[float] = []
    for piece, centre, drawn_here in sampled:
        # Asked of the piece's SIDE, not of the corner: a cut corner sits on
        # the strip's end line and `sample` counts it covered, so the piece
        # past the touchdown is over nothing only from its own side of the cut.
        if not any(drawn.covers(float(px), float(pz), toward=centre) for px, pz in piece) and (
            _under_a_deck(above, piece, centre)
        ):
            report.stations_on_drawn_structure += 1
            report.on_drawn_structure_m += _length_along(quad, piece)
            continue
        report.pieces_placed += 1
        piece_heights = [sample.height_m for sample in drawn_here]
        builder.polygon(piece, np.asarray(piece_heights) + lift_m)
        heights.extend(piece_heights)
        report.vertices_drawn += len(drawn_here)
        report.vertices_over_cap += sum(1 for sample in drawn_here if sample.cap_m is not None)
        for sample in drawn_here:
            if sample.over_void:
                report.vertices_over_void += 1
                report.void_reach_m.append(sample.reach_m)
    return heights


def _under_a_deck(above: Sequence[DrawnSurface], piece: np.ndarray, centre: np.ndarray) -> bool:
    """Whether every corner of a plan piece has something drawn over it at a
    level above the street — each corner by any of the readers, asked from
    the piece's own side as the level-0 question is."""
    return bool(above) and all(
        any(reader.covers(float(px), float(pz), toward=centre) for reader in above)
        for px, pz in piece
    )


def _length_along(quad: np.ndarray, piece: np.ndarray) -> float:
    """A piece's extent along its band quad's longer side — the marking's own
    direction for every station longer than the band is wide, whichever corner
    `wound_up` put first."""
    sides = quad[[1, 2]] - quad[[0, 1]]
    axis = sides[int(np.argmax(np.hypot(sides[:, 0], sides[:, 1])))]
    length = float(np.hypot(*axis))
    if length <= 0.0:
        return 0.0
    along = piece @ (axis / length)
    return float(along.max() - along.min())


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: RoadMarkReport) -> int:
    document = {
        "schema_version": ROADMARKS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what
        # `CITY_SCHEMA` 11 was bumped over.
        #
        # ⚠️ **On `triangles` rather than `drawn`, which is where this diverges
        # from `arrows.json` and `boxjunctions.json`.** `write_glb` runs only if
        # the builder produced a mesh, and every triangle of a drawn marking can
        # still be dropped by the sliver bar — this being the asset most exposed
        # to that. `_check_marks_clear_the_lattice` now makes that a build
        # failure rather than a silent one, so the two can no longer disagree;
        # keying on what shipped is simply the form that cannot.
        "asset": ROADMARKS_NAME if report.triangles else None,
        # The publisher's own row count, beside the partition below — which is
        # over **parts**, and on this layer the two differ by 2.5x.
        "features": report.features,
        # The read, as four disjoint parts of `parts`.
        "parts": report.parts,
        "not_a_road_mark": report.not_a_road_mark,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "outside_region": report.outside_region,
        "candidates": report.candidates,
        # The join, as three disjoint parts of `candidates`.
        "drawn": report.drawn,
        "no_host_on_axis": report.no_host_on_axis,
        "host_off_carriageway": report.host_off_carriageway,
        "chevrons": report.chevrons,
        "chevron_m": round(report.chevron_m, 2),
        "chevron_turn_gap_deg": {
            "chevron_straightest": _rounded(report.chevron_straightest_deg),
            "outline_sharpest": _rounded(report.outline_sharpest_deg),
        },
        "host_off_carriageway_m_by_id": {
            key: round(value, 2)
            for key, value in sorted(report.host_off_carriageway_m_by_id.items())
        },
        "no_edge_in_range": report.no_edge_in_range,
        # Per entry of the `marks:` table, so an entry that silently drew
        # nothing is visible. `refused_m_by_code` is what reading three codes of
        # a 61.9 km layer costs, published rather than left to a scratch script
        # (`Q37`).
        "drawn_by_id": report.drawn_by_id,
        "drawn_m_by_id": {name: round(value, 3) for name, value in report.drawn_m_by_id.items()},
        "refused_m_by_code": {
            code: round(value, 3) for code, value in sorted(report.refused_m_by_code.items())
        },
        # ⚠️ Kept out of the table above on purpose: an admitted code refused for
        # sitting on a deck is a different fact from a code this stage does not
        # draw, and `RM1012` is both in the same run.
        "on_structure_m": round(report.on_structure_m, 3),
        # 🔴 **The inferred join (`Q125`), as its own block and its own
        # partition.** Everything above is over what TD surveyed; this is where
        # two one-way carriageways run as one dual road and the line between the
        # flows belongs to neither half. `covered_m` is the survey this yields
        # to, per metre, and it is the counter that separates this from `Q117`'s
        # shader join — which could only yield per edge, and so was switched off
        # whole (`Q118`).
        #
        # ⚠️ **`over_refused_survey_m` grades and never gates**: metres where the
        # invented line stands in for a surveyed one this stage refused, rather
        # than for a silence. A finding to go and look at.
        "join": {
            "opposed_pairs": report.join_pairs,
            "join_m": round(report.join_m, 3),
            "covered_m": round(report.join_covered_m, 3),
            "drawn_m": round(report.join_drawn_m, 3),
            "refused_m": round(report.join_refused_m, 3),
            "runs_drawn": report.joins_drawn,
            "over_refused_survey_m": round(report.join_over_refused_survey_m, 3),
        },
        # 🔴 The bundle's word on structure beside the source's above: station
        # quads (or pieces of one) over nothing drawn at level 0 and under a
        # deck drawn above it, refused rather than placed 52-131 mm under that
        # deck. See `RoadMarkReport`.
        "stations_on_drawn_structure": report.stations_on_drawn_structure,
        "on_drawn_structure_m": round(report.on_drawn_structure_m, 3),
        # 🔴 **The counter that can see the join regress.** How often the
        # transverse pick and the plain nearest edge disagree about the host,
        # over every marking that found an edge in range. Measured at 53 of 120
        # `RM1011` and 36 of 83 `RM1013` when this shipped — 44% and 43% — and a
        # fall towards zero means the pick has stopped picking.
        #
        # ⚠️ It is published *instead of* trusting `axis_residual_deg`, which
        # grades a rule that optimises the very thing it reports (`Q58`'s
        # `drawn_gauge_m` trap).
        "host_disagreement": report.host_disagreement,
        # Derived rather than counted: it is exactly the markings that found an
        # edge in range, which is what `axis_residual_deg` is recorded over. A
        # second counter incremented in the same branch as that append is the
        # shape that drifts the day someone moves one of them.
        "host_considered": len(report.axis_residual_deg),
        # Recorded before the bearing guard, so `n` exceeding `drawn` is the
        # proof it can see past its own filter (`Q58`). What
        # `bearing_tolerance_deg` is set against.
        "axis_residual_deg": report.measured(report.axis_residual_deg),
        "host_distance_m": report.measured(report.host_distance_m),
        # ⚠️ **The underfill, published rather than corrected** — the drawn
        # ribbon is 1.6x wide and the bar was surveyed on the real carriageway,
        # so it stops short of the drawn kerb. Stretching it would be inventing
        # an extent (`Q54`), which is the call `P3-18` already made.
        "underfill_m": report.measured(report.underfill_m),
        "mark_length_m": report.measured(report.mark_length_m),
        "height_spread_m": report.measured(report.height_spread_m),
        # 🔴 The tripwire on the cap join (`Q92`) — see `RoadMarkReport`. Not a
        # tautology: both are reachable at zero, and zero is what a stage that
        # has gone back to guessing the road's height reads.
        "vertices_drawn": report.vertices_drawn,
        "vertices_over_cap": report.vertices_over_cap,
        # 🔴 The tripwire on the rail join — see `RoadMarkReport`. Reads every
        # vertex the moment `ribbons` stops being published.
        "vertices_over_void": report.vertices_over_void,
        "void_reach_m": report.measured(report.void_reach_m),
        # 🔴 The tripwire on the crease cut — see `RoadMarkReport`. Both collapse
        # onto `polygons_placed` the moment the cut stops firing.
        "polygons_placed": report.polygons_placed,
        "polygons_split": report.polygons_split,
        "pieces_placed": report.pieces_placed,
        # Fragments thinner than two cells of the engine's import lattice,
        # dropped before they could come back winding-flipped. The pitch is
        # published beside the count so the bar is checkable from a shipped
        # artefact rather than a scratch script (`Q37`).
        "slivers_dropped": report.slivers_dropped,
        "import_quantum_m": report.import_quantum_m,
        # ⚠️ **Must be 0.** `marking_paint.gdshader` is `cull_back`, so winding
        # decides visibility and the normal attribute does not (`Q58`).
        "inverted": report.inverted,
        "inverted_area_m2": round(report.inverted_area_m2, 4),
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
    }
    return write_document(out_dir / ROADMARKS_MANIFEST_NAME, document)


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
        "roadmarks: %d parts -> %d drawn (%d off axis, %d off their own carriageway, "
        "%d off network), %d triangles",
        report.parts,
        report.drawn,
        report.no_host_on_axis,
        report.host_off_carriageway,
        report.no_edge_in_range,
        report.triangles,
    )
    log.info(
        "  creases: %d quads placed, %d cut where the road folds, %d pieces",
        report.polygons_placed,
        report.polygons_split,
        report.pieces_placed,
    )
    log.info(
        "  inferred join: %d pairs, %.0f m of which %.0f m covered by survey, %.0f m drawn "
        "in %d runs (%.0f m over a refused survey line)",
        report.join_pairs,
        report.join_m,
        report.join_covered_m,
        report.join_drawn_m,
        report.joins_drawn,
        report.join_over_refused_survey_m,
    )
    log.info(
        "  under a drawn deck: %d stations / %.2f m refused",
        report.stations_on_drawn_structure,
        report.on_drawn_structure_m,
    )
    log.info(
        "  by marking: %s",
        ", ".join(
            f"{name} {count} ({report.drawn_m_by_id.get(name, 0.0):.0f} m)"
            for name, count in sorted(report.drawn_by_id.items())
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
