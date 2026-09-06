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
from dataclasses import dataclass, field, replace
from itertools import pairwise
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.arrows import ArrowReport
from pipeline.config import Config, GameTransform, RoadMark, RoadMarks, load_config
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.geometry import wound_up
from pipeline.gltf import write_glb
from pipeline.meshbuild import FlatBuilder, import_quantum_m
from pipeline.polyline import Segments, plan_lengths_2d

# `AT_GRADE` rather than a fifth private copy — `railings.py` exports it
# publicly to stop exactly that, and `signs.py` imports it for the same reason.
# It is the source's own encoding of "no structure" on the same column of the
# same geodatabase, not a threshold anyone may tune. 209 of the region's 211
# parts are null.
from pipeline.railings import AT_GRADE
from pipeline.roads import ROADGRAPH_NAME, clip, read_graph
from pipeline.surface import (
    SURFACE_MANIFEST_NAME,
    SURFACE_MANIFEST_SCHEMA,
    DrawnSurface,
    downward_facing,
)

log = logging.getLogger(__name__)

ROADMARKS_NAME = "roadmarks.glb"
ROADMARKS_MANIFEST_NAME = "roadmarks.json"
ROADMARKS_MANIFEST_SCHEMA = 1

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


# Slack on `_reachable`'s narrowing, in metres. ⚠️ **Arbitrary, and deliberately
# on the generous side** — `_reachable` proves `d_min + 2r` is already exact for
# a plain nearest, so every metre here is surplus. It is kept because the two
# errors are not symmetric: too generous costs a few projections a marking, too
# tight silently changes an answer. Do not read it as derived from anything.
_REACH_MARGIN_M = 3.0

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
    # rather than the middle, for `ArrowReport.measured`'s stated reason — every
    # distribution here is a residual, and the tail is the finding.
    measured = staticmethod(ArrowReport.measured)


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
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = layer.column(spec.layer.field("mark_type"))
        levels = layer.column(spec.layer.field("level"))
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
        start = self.segments.start[:, [0, 2]]
        delta = self.segments.delta[:, [0, 2]]
        squared = (delta**2).sum(axis=1)
        offset = point - start
        along = ((offset * delta).sum(axis=1) / np.where(squared > 0.0, squared, 1.0)).clip(
            0.0, 1.0
        )
        return np.linalg.norm(offset - along[:, None] * delta, axis=1)


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
    score = residual + spec.proximity_weight_deg_per_m * distance[in_range]
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

    quads: list[np.ndarray] = []
    for start, stop in _runs(mark, total):
        cuts = _cuts(start, stop, along, spec.station_m)
        for head, tail in pairwise(cuts):
            middle = np.searchsorted(along, 0.5 * (head + tail), side="right") - 1
            index = int(np.clip(middle, 0, len(marking.line) - 2))
            step = marking.line[index + 1] - marking.line[index]
            direction = step / np.linalg.norm(step)
            # Left of travel in the `(x, z)` plan, which is the frame the band
            # offsets and the half-width are both expressed in.
            across = np.array([-direction[1], direction[0]])
            first, last = _point_at(marking.line, along, head), _point_at(marking.line, along, tail)
            for offset in offsets:
                quads.append(_band_quad(first, last, across, offset, half))
    return quads


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
    return {
        int(entry["edge"]): 2.0
        * float(np.mean(np.asarray(entry["half_width_m"], dtype=np.float64)))
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
    resolves a plan point to the nearest level-0 *centreline*, which is the right
    rule for a bar at a junction mouth and the wrong one where a level-0 ramp
    climbs beside a street. ⚠️ **Two separate facts, and they are not the same
    edges**: level-0 heights climb by up to **7.87 m** along a single edge here
    (`e465` CROSS HARBOUR TUNNEL, which is *not* on structure), and **16** other
    level-0 edges do stand on structure. Either way two level-0 ribbons stack in
    plan, and the nearest centreline is then not the surface the paint sits on.
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
    `±half` about the centreline (`Q106`), but `offset_m` is **exactly 0.0 on all
    737 level-0 edges** and this stage is level-0 only, so that term is inert by
    arithmetic rather than by luck; and the half-width varies per station since
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


def _reachable(
    segments: Segments, marking: Marking, host: Host, quads: list[np.ndarray]
) -> Segments:
    """The segments that can be nearest to any vertex of this marking.

    ⚠️ **A narrowing, not an approximation — the heights it produces are
    bit-identical.** For a marking whose vertices all lie within `r` of its
    midpoint, `|d(vertex, s) - d(midpoint, s)| <= r`, so a segment further than
    `d_min + 2r` from the midpoint is nearest to no vertex of it and cannot be
    chosen. Keeping the rest changes no answer.


    🔴 **Both figures below were measured before `RM1001` and are restated
    (`Q118`).** A marking is no longer a 10 m bar: vertices went **9,084 →
    24,648** and the mean kept set **6.3 → 14.4** segments, with `RM1001` alone
    at 32.6 and a worst of **306** — 10.3% of the network. The narrowing still
    earns its keep decisively, **1.25 M projections against 72.9 M unnarrowed**.

    🔴 **But per-marking work is now cubic in marking length, and that is
    measured rather than feared.** The cutoff is `d_min + 2r` with `r ≈ L/2`, so
    the kept set is the segments in a disc of radius ≈ L — `∝ L²` — while the
    vertex count is `∝ L`. Projections grew **17.4x** on **2.7x** the vertices,
    and **8 markings carry 69%** of them. ⚠️ **It is invisible today**: wall time
    grew only 2.2x, because at 14.4 segments the loop is bound by numpy's
    per-call dispatch and not by arithmetic.

    ⚠️ **The fix is priced and NOT taken.** Narrowing again per window of ~64
    vertices inside the already-narrowed set costs nothing and makes the work
    linear — 1,252,308 → 181,884 projections — and batching the per-vertex
    `sample` loop (47% of the stage's compute, 24,648 scalar numpy round-trips)
    measured **378 → 155 ms**. Both were left: the stage is 1.2 s, the win is
    ~0.22 s of build time no player waits on, and batching needs a new
    `Segments.nearest_many` and `DrawnSurface.sample_many` in two modules other
    stages share. ⚠️ **It would also not be bit-identical** — heights agree to
    9.9e-11 m, argmin tie-breaking where two segments are equidistant — so it
    moves the mesh, which is a bigger claim than the saving is worth. Take it
    when a region makes the cubic term bite, and take both halves together.

    ⚠️ **The reason it is worth the fifteen lines is the second city, not this
    one.** Vertices scale with region area and so do segments, so the unnarrowed
    join is quadratic in area: 9,084 vertices x 2,959 segments is 27 M
    projections and 0.30 s here, but the same density over 50 km² is ~30 G and
    minutes. Narrowed, the region's markings see a mean of **6.3** segments each.
    `host.distance_m_all` is reused rather than recomputed, so this costs no
    extra scan at all.
    """
    distance = host.distance_m_all
    midpoint = marking.midpoint
    corners = np.vstack(quads) if quads else marking.line
    radius = float(np.linalg.norm(corners - midpoint, axis=1).max())
    cutoff = float(distance.min()) + 2.0 * radius + _REACH_MARGIN_M
    keep = distance <= cutoff
    return replace(
        segments,
        start=segments.start[keep],
        delta=segments.delta[keep],
        length_m=segments.length_m[keep],
        before_m=segments.before_m[keep],
        total_m=segments.total_m[keep],
        edge=segments.edge[keep],
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
    drawn = DrawnSurface.of(segments, surface, level=0)

    builder = FlatBuilder(ROADMARKS_MATERIAL)
    report.import_quantum_m = round(_import_quantum_m(markings), 6)
    thinness_bar_m = 2.0 * report.import_quantum_m
    _check_marks_clear_the_lattice(spec, thinness_bar_m)
    for marking in markings:
        host = _host(network, marking, spec)
        if host is None:
            report.no_edge_in_range += 1
            continue
        report.host_disagreement += int(host.disagrees)
        # Recorded before the bearing guard — `n` past `drawn` is the proof the
        # distribution can read outside its own filter (`Q58`).
        report.axis_residual_deg.append(host.residual_deg)
        # 🔴 **A longitudinal marking must lie ON the road it is hosted to, and
        # the bar is that road's own drawn half-width rather than a number.**
        # `DrawnSurface.sample` resolves height by nearest *centreline*, so where
        # a level-0 ramp climbs beside a street — heights climb up to 7.87 m
        # along one edge, and 16 others stand on structure — a line whose host
        # centreline is further off than its true carriageway takes a height
        # metres from the surface under it. A
        # transverse bar is allowed its distant host on purpose (it starts on the
        # far kerb of a four-lane mouth); a line painted *along* a carriageway has
        # no such licence, so this refuses rather than places it wrong (`Q54`).
        if not _on_its_own_carriageway(marking, host):
            report.host_off_carriageway += 1
            continue
        if host.residual_deg > spec.bearing_tolerance_deg:
            # Off the axis this marking is supposed to lie on. Transverse, the
            # region's extremes are a 56.9 m `RM1013` lying 78.8 deg off square
            # and a 33.8 m `RM1011` at 88.7; longitudinal, it is a double white
            # line whose nearest road runs across it. Either way a marking this
            # stage has no reading of, refused rather than turned onto a road,
            # which would be an invented marking in `Q54`'s sense.
            report.no_host_on_axis += 1
            continue

        quads = band_quads(marking, spec)
        near = drawn.narrowed_to(_reachable(segments, marking, host, quads))
        heights: list[float] = []
        for quad in quads:
            drawn_here = [near.sample(float(px), float(pz)) for px, pz in quad]
            vertex_heights = [sample.height_m for sample in drawn_here]
            builder.polygon(quad, np.asarray(vertex_heights) + spec.lift_m)
            heights.extend(vertex_heights)
            report.vertices_drawn += len(drawn_here)
            report.vertices_over_cap += sum(1 for s in drawn_here if s.cap_m is not None)

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
        "  by marking: %s",
        ", ".join(
            f"{name} {count} ({report.drawn_m_by_id.get(name, 0.0):.0f} m)"
            for name, count in sorted(report.drawn_by_id.items())
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
