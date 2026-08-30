"""Published pedestrian railings, drawn on the kerb the ribbon has (`P3-19`).

`GAME_DESIGN.md` names pedestrian railings as the thing that makes a Hong Kong
street a Hong Kong street, and then lists them under *"deliberately diverge
on — omit or make breakable"*. Both halves are kept here: the fence ships as
**geometry with no collider**, so it narrows nothing and the divergence that
doc protects is untouched, and it ships from TD's own `DTAD_RAILING_LINE`
rather than from a rule about kerbs.

Three things make this stage different from `arrows.py` and `boxjunctions.py`,
and each is recorded where it bites.

**1. The publisher does not define its own vocabulary, and this is the only
layer in the bundle of which that is true.** Every other coded field the
pipeline reads is transcribed from a published sheet — `RM` markings and `TS`
signs from TD's index plans, iB1000's features from LandsD's dictionary. Here
the fgdb data specification gives `LINETYPE` the description *"Line Type"* and
stops, and the index-plan bundle's two "Miscellaneous Details" sheets are sign
pictograms and lettering with no railing row on either. So `Q59`'s glyph-table
rule cannot be satisfied from inside the bundle. Nor is there a second column to
fall back on: the layer's other 40 are cartography, and `Q60` records the
measurement — `SYMBOL_SIZE_*` is the spec's own *"symbol size of marker symbol"*
in inches on paper, `COLOR` is an undomained pen index, `LINE_WIDTH_*` is null
throughout.

What follows is the shape of `classes` (`Q61`). The layer is split by **class of
object** — fence, bollard, vehicle restraint — on the strength of the code
strings, and **never within a class**: all five fence codes draw one fence,
because nothing published says `CRAIL1` differs from `HCAIL2`. Every code no
class admits has its metres published per code, so the table is an argument a
reader can check rather than an assumption.

**2. The position is registered, and that is this stage's debt.** `Q59`'s 1.6x
widening has already moved the drawn kerb a median 0.9 m *past* the surveyed
railing line: measured over the region, **67.9% of published railing metres fall
inside the drawn ribbon**. Drawn where surveyed, the signature Hong Kong railing
is a picket fence down the middle of the drivable surface. So this stage does
what `arrows.py` does to a position and `boxjunctions.py` refused to do to an
extent, and the difference between the two axes is the argument:

- the **longitudinal** extent — where a railing starts and stops along a street
  — is read, and never stretched;
- the **lateral** offset is a rigid move onto the kerb the ETL itself drew.

That move is not free and is not asserted to be small. `max_shift_m` refuses a
sample that would travel too far, and `shift_m` is published over every assigned
sample *including the refusals*, so `n` exceeding what was drawn is how a reader
tells the distribution can still see past its own filter (`Q58`).

**3. A drawn kerb is not always drawn.** `surface.py:_hide_buried_kerbs` drops
the kerb wherever another ribbon already covers it — 33 km of it in this region,
because a 1.6x-widened opposed pair merges into one surface. A railing joined to
one of those kerbs is a fence standing in the middle of merged tarmac, and
**11.1% of the region's railing metres join to exactly that**. The ranges come
from `roadsurface.json`, which publishes them for this stage (`SURFACE_MANIFEST_
SCHEMA` 5) rather than letting a second implementation of the coverage test
disagree with the first near the junction caps (`Q56`).

**The join is `kerbside.py`'s**, not a second one: `resample`, `SideIndex` and
`merge_runs` are that stage's own, and the side convention is therefore
`surface.mitres`'s own expression rather than a restatement of it. A railing run
is the same shape as a kerbside restriction — `(edge, side, V-range)` — because
it is the same kind of fact about the same kerb.

⚠️ **Nothing here invents a railing.** The region publishes 20.3 km of them
against 90.2 km of kerb line, of which 57.1 km is actually drawn once the buried
kerbs come out; a fallback keyed on kerbs would run a wall down every street that
has none, and it would render perfectly.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.arrows import ArrowReport
from pipeline.config import CityConfig, GameTransform, RailingClass, Railings, load_config
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.kerbside import NEARSIDE, OFFSIDE, SideIndex, merge_runs, resample
from pipeline.mesh import select_triangles
from pipeline.polyline import plan_lengths, plan_lengths_2d
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import (
    SURFACE_MANIFEST_NAME,
    SURFACE_MANIFEST_SCHEMA,
    boundary,
    dedupe,
    mitres,
    trim,
)

log = logging.getLogger(__name__)

RAILINGS_NAME = "railings.glb"
RAILINGS_MANIFEST_NAME = "railings.json"
# 2 since `Q61`: the layer is drawn as three classes, so `drawn_m` no longer
# means "railing metres" and a consumer keeping that reading would be **wrong**
# — hard rule 5's own bar. The top-level key is gone rather than broadened, so
# an old reader fails loudly instead of quietly counting bollards as fence.
RAILINGS_MANIFEST_SCHEMA = 2

# ⚠️ **A class's `id` is its mesh name and its glTF material name, verbatim.**
# One string for one identity: `tools/generated_scene_import.gd` dispatches a
# material by name, and the graders find a class's geometry by mesh name. The
# contract channel is `ARROWS_MATERIAL`'s.
#
# ⚠️ **No `-col` suffix on any of them**, and here that is a design decision
# rather than a rendering one. A railing is the one piece of street furniture
# whose real-world purpose is to stop things, and `GAME_DESIGN.md` lists
# railings under "deliberately diverge on — omit or make breakable" precisely
# because a faithfully solid one turns a narrow street into a corridor.
# Collision is a `B3` question, after `P2-6` has measured a frame on the device
# floor; until then the fence is scenery and the car drives through it, which is
# the recorded cost. The guard used to be this one string; now that the name
# comes from config it is `config._railing_class`, which refuses an id ending in
# `-col`, plus `verify_railings.gd` in the engine.

# Below this, twice a triangle's area means it has collapsed. The bar
# `surface.py`, `tramway.py`, `arrows.py` and `boxjunctions.py` all set.
_MIN_TWICE_AREA_M2 = 1e-6

# What `ELEVATION` says when a feature is at grade — the same column, on the
# same geodatabase, that `arrows.py` and `boxjunctions.py` read, and the same
# reading: the column is a structure identifier (`A01`, `A03`) and null is the
# ground. 1,737 of the region's 1,753 railings are null and 16 carry `A01`.
#
# ⚠️ Not config, for `arrows._AT_GRADE`'s stated reason: it is the source's own
# encoding of "no structure", not a threshold anyone may tune.
#
# Public where its two siblings are private, because `tools/railing_error.py`
# has to admit the same features this stage does to grade it, and the
# alternative is a second copy of the publisher's encoding in a file whose
# whole job is to disagree with this one.
AT_GRADE = ("", "none", "null", "<na>")


@dataclass
class ClassReport:
    """What one class of the layer joined, refused and drew (`Q61`).

    ⚠️ **Everything below the join lives here, and that is what the schema bump
    is about.** `drawn_m` on a class means *that class's* metres. There is no
    top-level `drawn_m` any more — not broadened, removed — because a reader who
    kept the old one would be counting bollards and vehicle barriers as
    pedestrian railing and would have no way to notice.

    ⚠️ **The metres still do not form a partition**, for the reason
    `RailingReport` records and which is unchanged by the split: they are a
    chain measured in two frames. `metres_dropped_short` and the run extents are
    *published* metres; `metres_dropped_sliver`, `metres_outside_ribbon`,
    `metres_on_buried_kerb` and `drawn_m` are *ribbon* metres, taken after the
    junction trims come off. `metres_bridged` is drawn without ever having been
    sampled at all.
    """

    # Parts admitted to this class, and their source metres. The per-class half
    # of `RailingReport`'s global read: a class whose `read_m` is healthy and
    # whose `drawn_m` is zero has lost everything in the join, which is the one
    # failure the shared `samples_unassigned` cannot show.
    read: int = 0
    read_m: float = 0.0

    # ⚠️ **The price of the registration, per class, and it has to be per class.**
    # How far each assigned sample would move sideways to reach the drawn kerb.
    # Recorded over every assigned sample **before** the `max_shift_m` refusal,
    # so `n` past what was drawn is the proof it can see outside its own filter
    # (`Q58`). Per class because the classes stand at different outsets and a
    # single pooled distribution would hide one class registering badly behind
    # another registering well.
    shift_m: list[float] = field(default_factory=list)
    samples_over_shift: int = 0
    metres_deduped: float = 0.0

    runs: int = 0
    runs_dropped: int = 0
    # ⚠️ Two counters because they are in two frames, and one was misleading.
    # A whole run refused for being shorter than `min_run_m` is measured in
    # *published* metres, before the ribbon clip; a sliver left between two
    # buried stretches is measured in *ribbon* metres, after it.
    metres_dropped_short: float = 0.0
    metres_dropped_sliver: float = 0.0
    # Run metres falling outside the drawn ribbon's own extent — past a junction
    # trim, where the cap is and the kerb is not.
    metres_outside_ribbon: float = 0.0
    # ⚠️ Run metres on a kerb `surface.py` does not draw, because another ribbon
    # covers it. Dropped: this is the fence-across-merged-tarmac case.
    metres_on_buried_kerb: float = 0.0

    drawn_m: float = 0.0
    # ⚠️ Of the drawn metres, those standing where the source published nothing:
    # `merge_runs` bridges gaps up to `bridge_gap_m`, and a bridged metre is
    # drawn without ever having been sampled. The one part of `drawn_m` this
    # stage invents, so it is published rather than left to be discovered as a
    # partition that does not close. ⚠️ Watch it hardest on `bollards`, whose
    # published features have a median length of 1.00 m: bridging is doing more
    # of the work there than anywhere else.
    metres_bridged: float = 0.0
    drawn_m_by_type: dict[str, float] = field(default_factory=dict)
    # Of the drawn metres, the share on the ribbon's `U = 0` rail. Not a bar — a
    # region is not obliged to be symmetric — but a flip of the side convention
    # mirrors every fence in the city and still renders as a city, so the one
    # number that would move is published.
    drawn_m_nearside: float = 0.0

    # ⚠️ **Must be 0.** Every quad is wound so its front face looks at the
    # carriageway — the side the player is on. `railings.gdshader` is
    # `cull_disabled` so a wrong winding still draws, but the *normal* follows
    # the winding, and a fence lit from behind reads as a black wall. Held here
    # rather than assumed because the tramway shipped 5,111 of 5,112 triangles
    # facing the wrong way with everything else correct (`Q58`).
    facing_away: int = 0
    triangles: int = 0
    vertices: int = 0
    aabb: list[list[float]] = field(default_factory=list)

    # One distribution as the manifest publishes it: p50/p90/p99/max, the tail
    # rather than the middle, for `ArrowReport.measured`'s stated reason.
    measured = staticmethod(ArrowReport.measured)


@dataclass
class RailingReport:
    """What the stage read and refused, and a `ClassReport` for each class drawn.

    ⚠️ **The counters are what can see this stage fail** — `Q58`'s lesson,
    inherited through `arrows.py` and `boxjunctions.py`, and it bites hardest
    here because *every* failure mode of a registered fence renders as a
    perfectly good fence. A railing moved onto the wrong kerb is a fence. A
    railing mirrored to the other side of the street is a fence. A railing drawn
    across merged tarmac is a fence, and it is the one the player crashes into.

    What is here is **the read**, which is one read of one layer and so is not
    per class:

        parts == not_drawn_line_type + on_structure + empty_geometry + read
        source_m == refused_m(sum) + on_structure_m + read_m

    Everything after the read is in `ClassReport`.

    ⚠️ **`samples`, `samples_outside_region` and `samples_unassigned` are shared
    and cannot be split.** `SideIndex.nearest` returns unassigned as a count
    rather than as the samples themselves, so there is nothing to attribute. A
    class that joins to nothing is therefore invisible *here* and visible in its
    own `read_m` against its own `drawn_m`, which is why both are published.
    """

    # ⚠️ **`features` counts features and everything below counts parts**, and
    # they differ: this region publishes 1,753 features as 1,763 parts.
    # `kerbside.py` records what happens when the two are mixed — a ratio over
    # one, "725 of 579", which is the shape a mismatched denominator takes when
    # nothing is checking.
    features: int = 0
    parts: int = 0
    not_drawn_line_type: int = 0
    on_structure: int = 0
    empty_geometry: int = 0

    # Source metres, before any join. `refused_m` is keyed by the publisher's
    # own `LINETYPE`, which is what makes the class table an argument: a reader
    # sees exactly which codes no class admits and how much of the region went
    # with them.
    source_m: float = 0.0
    refused_m: dict[str, float] = field(default_factory=dict)
    # ⚠️ Kept apart from `refused_m`, and the region is why: six features carry
    # 1,579 m of `CRAIL1` — an *admitted* code — on a flyover parapet. Folded
    # into the per-code table those metres read as "this code was not drawn",
    # which is the opposite of true.
    on_structure_m: float = 0.0

    samples: int = 0
    samples_outside_region: int = 0
    samples_unassigned: int = 0
    metres_sampled: float = 0.0

    # One entry per class that read anything, keyed by the class `id` — which is
    # also its mesh name and its glTF material name.
    classes: dict[str, ClassReport] = field(default_factory=dict)

    # One file, so one byte count.
    bytes: int = 0

    def klass(self, klass_id: str) -> ClassReport:
        """This class's counters, created on first use.

        ⚠️ **Creates on read, so only write paths may call it.** A reader that
        mistypes an id gets a silent all-zero `ClassReport` and adds a phantom
        class to the published manifest, which is the shape of quiet wrong every
        counter in this file exists to prevent.
        """
        return self.classes.setdefault(klass_id, ClassReport())

    @property
    def read(self) -> int:
        """Parts admitted to some class — the fourth part of the `parts` partition.

        Derived rather than stored, for `drawn_m`'s reason: `read_lines` counts
        this per class on one code path, and a second field incremented beside it
        is a second thing that can drift.
        """
        return sum(report.read for report in self.classes.values())

    @property
    def read_m(self) -> float:
        """Source metres admitted to some class. Derived, as `read` is."""
        return sum(report.read_m for report in self.classes.values())

    @property
    def drawn_m(self) -> float:
        """Every class's drawn metres.

        ⚠️ **Deliberately not published.** It exists so `build_region` can gate
        the manifest's `asset` key on whether anything was drawn at all. Written
        into the document it would be the exact number `Q61` bumped the schema
        to stop a reader trusting.
        """
        return sum(report.drawn_m for report in self.classes.values())


@dataclass(frozen=True)
class Ribbon:
    """One edge's drawn ribbon, as this stage needs to walk its kerb.

    ⚠️ **Reconstructed with `surface.py`'s own functions, from `surface.py`'s
    own published widths and trims** — `trim`, `dedupe`, `mitres` and
    `boundary`, in the order `surface._shape` calls them. Not re-derived: a
    second expression for the drawn kerb would be a second join in `Q56`'s
    sense, and it would disagree exactly where the tight-corner repair in
    `boundary` bites.
    """

    # The trimmed centreline, `(n, 4)` as `(x, y, z, half_width)`.
    points: np.ndarray
    # The standing line for each class and side, `(n, 2)` in plan — the drawn
    # carriageway edge pushed out by that class's `outset_m`, so the furniture
    # stands behind the kerb strip rather than on the lane. Keyed
    # `[class id][side]`: the classes may stand at different outsets, and
    # precomputing each is three cheap `boundary` calls against a per-station
    # recomputation in the inner loop.
    fence: dict[str, dict[str, np.ndarray]]
    # Cumulative plan distance along `points`. **Ribbon metres**: zero is the
    # trimmed start, which is the frame `kerb_hidden_m` is published in.
    along: np.ndarray
    # Ribbon-metre ranges where that side draws no kerb, straight off
    # `roadsurface.json`.
    hidden: dict[str, list[list[float]]]
    trim_start_m: float

    @property
    def length_m(self) -> float:
        return float(self.along[-1])


def read_lines(
    city: CityConfig,
    spec: Railings,
    region_id: str,
    transform: GameTransform,
    report: RailingReport,
    *,
    sources_root: Path | None,
) -> list[tuple[np.ndarray, str]]:
    """Every published railing this city draws, in game plan space.

    Everything refused here is refused on what the *publisher* says — a code
    outside the whitelist, a feature on a structure, an empty line — and each
    refusal is counted rather than logged (`Q58`). The refused metres are keyed
    by code because that is what makes the whitelist reviewable: nothing in the
    bundle says what `CBARRIER` is, so the honest form of the decision to leave
    it out is a published figure for what leaving it out costs.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    lines: list[tuple[np.ndarray, str]] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = layer.column(spec.layer.field("line_type"))
        levels = layer.column(spec.layer.field("level"))
        owners, parts = gdb.polylines(layer)
        report.features += len(layer.fids)

        for owner, points in zip(owners, parts, strict=True):
            report.parts += 1
            source = np.asarray(points, dtype=np.float64)
            if len(source) < 2 or not np.isfinite(source[:, :2]).all():
                report.empty_geometry += 1
                continue
            # In the source's own easting/northing, before the game
            # transform: a translation and a Z flip preserve length, and
            # measuring here keeps `source_m` comparable with the figures
            # `DATA_SOURCES.md` quotes for the layer.
            length_m = float(np.hypot(*np.diff(source[:, :2], axis=0).T).sum())
            report.source_m += length_m

            code = str(types[owner])
            klass = spec.class_of(code)
            if klass is None:
                report.not_drawn_line_type += 1
                report.refused_m[code] = report.refused_m.get(code, 0.0) + length_m
                continue
            if str(levels[owner]).strip().lower() not in AT_GRADE:
                # On a structure. `Q13` keeps the elevated network closed to
                # driving and `Q15` is the level-0 snap every dTAD consumer
                # owes: the nearest level-0 kerb to a parapet on a flyover
                # belongs to the street underneath it.
                report.on_structure += 1
                report.on_structure_m += length_m
                continue

            game_x, _, game_z = transform.to_game(source[:, 0], source[:, 1])
            lines.append((np.column_stack([game_x, game_z]), code))
            # Counted per class and summed by `RailingReport.read`. Its whole
            # job is to be compared with that class's `drawn_m`:
            # `samples_unassigned` is shared and cannot be attributed, so a class
            # that reads well and draws nothing is only visible as the gap
            # between these two numbers.
            counters = report.klass(klass.id)
            counters.read += 1
            counters.read_m += length_m
    return lines


def _sides(shaped: np.ndarray, offsets: np.ndarray, outset_m: float) -> dict[str, np.ndarray]:
    """One class's standing line on both sides of a ribbon.

    The outset array is built once and negated, rather than written out per
    side: the two sides of a ribbon are one distance measured in two directions,
    and computing it twice is two places for a widening to be applied unevenly.
    """
    outset = shaped[:, 3] + outset_m
    return {
        NEARSIDE: boundary(shaped, offsets, outset),
        OFFSIDE: boundary(shaped, offsets, -outset),
    }


def ribbons(graph: dict, surface: dict, spec: Railings) -> dict[int, Ribbon]:
    """The drawn ribbon of every level-0 edge, keyed by edge id.

    Level 0 only, the restriction every snap in the pipeline makes (`Q15`).
    """
    drawn = {int(entry["edge"]): entry for entry in surface["carriageway"]}
    built: dict[int, Ribbon] = {}
    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        entry = drawn.get(int(edge["id"]))
        if entry is None:
            continue
        points = np.asarray(edge["polyline"], dtype=np.float64)
        half = np.asarray(entry["half_width_m"], dtype=np.float64)
        if len(points) < 2 or len(half) != len(points):
            # A width list that does not match the polyline it was measured on
            # is a contract break, not a rounding problem — `arrows._ribbons`
            # takes the same exit, and it shows up as a railing that found no
            # kerb rather than as a fence in the wrong place.
            continue
        trim_start_m, trim_end_m = (entry.get("trim_m") or [0.0, 0.0])[:2]
        # `surface._shape`'s own three lines, on `surface._prepare`'s own column
        # layout: the half-width travels as a fourth column so `trim` gives the
        # two cut stations the right width instead of a neighbour's.
        shaped = dedupe(trim(np.column_stack([points, half]), trim_start_m, trim_end_m))
        if len(shaped) < 2:
            continue
        offsets = mitres(shaped)
        built[int(edge["id"])] = Ribbon(
            points=shaped,
            fence={klass.id: _sides(shaped, offsets, klass.outset_m) for klass in spec.classes},
            along=plan_lengths(shaped),
            hidden=entry.get("kerb_hidden_m") or {},
            trim_start_m=float(trim_start_m),
        )
    return built


def _half_width_at(ribbon: Ribbon, along_m: float) -> float:
    """The drawn half-width at one ribbon distance.

    Plus `outset_m` this is where the fence stands, measured from the same
    centreline a sample's own offset is measured from — so the difference
    between the two *is* the lateral move, and `shift_m` needs no second
    geometry to find it.
    """
    return float(np.interp(along_m, ribbon.along, ribbon.points[:, 3]))


def _station(ribbon: Ribbon, klass_id: str, side: str, at_m: float) -> tuple[np.ndarray, float]:
    """The standing point and deck height at one ribbon distance, as `((x, z), y)`.

    ⚠️ Interpolated in the **centreline's** parameter, not the fence line's.
    The ribbon is quads between consecutive offset vertices, so a point at
    fraction `t` along a centreline segment maps to fraction `t` along that
    quad's outer edge — the two parameterisations differ in length on a bend and
    agree exactly on where the edge is, which is the thing being drawn.
    """
    rail = ribbon.fence[klass_id][side]
    index = int(np.clip(np.searchsorted(ribbon.along, at_m) - 1, 0, len(ribbon.along) - 2))
    span = ribbon.along[index + 1] - ribbon.along[index]
    fraction = 0.0 if span <= 0.0 else float((at_m - ribbon.along[index]) / span)
    fraction = min(max(fraction, 0.0), 1.0)
    plan = rail[index] + fraction * (rail[index + 1] - rail[index])
    height = ribbon.points[index, 1] + fraction * (
        ribbon.points[index + 1, 1] - ribbon.points[index, 1]
    )
    return plan, float(height)


def _visible(ribbon: Ribbon, side: str, start_m: float, end_m: float) -> list[tuple[float, float]]:
    """A ribbon-metre range split around the stretches that draw no kerb.

    ⚠️ **This is the guard that keeps a fence off the middle of the road.** A
    1.6x-widened opposed pair merges into one surface, `surface.py` stops
    drawing the swallowed kerbs, and a railing joined to one of those is a fence
    standing in traffic. The ranges are the surface stage's own answer, read
    from its manifest rather than recomputed here.
    """
    kept = [(start_m, end_m)]
    for low, high in ribbon.hidden.get(side, []):
        split: list[tuple[float, float]] = []
        for piece_start, piece_end in kept:
            if high <= piece_start or low >= piece_end:
                split.append((piece_start, piece_end))
                continue
            if piece_start < low:
                split.append((piece_start, low))
            if high < piece_end:
                split.append((high, piece_end))
        kept = split
    return kept


def _run_uvs(plan: np.ndarray, *, height_m: float, sink_m: float) -> np.ndarray:
    """`(metres along the fence, metres above the deck)` for one strip's vertices.

    Ordered to match `_Builder.strip`'s own `[bottom, top]` stack, so the two
    stay in step by construction rather than by a comment.

    ⚠️ **`u` is the *fence line's* arc length, not the centreline's.** `_station`
    interpolates each station in the centreline's parameter — deliberately, and
    its docstring says why — so on a bend the two parameterisations differ by
    the ratio of their radii. Spacing balusters along the centreline's distance
    would stretch the pitch around the outside of every corner and pinch it
    around the inside, and it would render as a perfectly good fence with a
    limp. Measured here, on the line the balusters actually stand on.

    ⚠️ **`u` restarts at zero for every run**, so two runs never share a phase.
    That is deliberate and it is invisible: `merge_runs` has already closed
    every gap shorter than `bridge_gap_m`, so what separates two runs is a real
    break in the published fence, and a baluster rhythm has nothing to carry
    across it.

    `v` is measured from the **ribbon deck**, not from the fence's own foot, so
    `v = 0` is the ground line wherever the fence stands: `-sink_m` at the
    buried foot, `height_m` at the top. That is what lets a rail band be
    authored as "0.95 m up" and mean it, rather than meaning a fraction of a
    height that a second class will change.
    """
    along = plan_lengths_2d(plan)
    return np.column_stack(
        [
            np.concatenate([along, along]),
            np.concatenate([np.full(len(plan), -sink_m), np.full(len(plan), height_m)]),
        ]
    )


class _Builder:
    """Vertical strips accumulated into one primitive, and so one draw call."""

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._uvs: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def strip(
        self,
        plan: np.ndarray,
        deck: np.ndarray,
        *,
        height_m: float,
        sink_m: float,
        facing: np.ndarray,
        flip: bool,
    ) -> int:
        """One run of fence: a quad per station pair, wound to face the road.

        `facing` is the unit direction each station's front face looks in, which
        is toward the carriageway. It is passed rather than derived from the
        winding because a strip's own direction says nothing about which side of
        it the road is on.

        Every vertex also carries `TEXCOORD_0` as **`(metres along this run,
        metres above the ribbon deck)`** — the coordinate `railings.gdshader`
        cuts the balusters out of. Not a texture coordinate: nothing samples an
        image, and `mesh_contract.gd` would refuse the bundle if anything did.
        It is the same channel and the same kind of payload a tile's storey
        height travels in (`P3-7`).
        """
        if len(plan) < 2:
            return 0
        bottom = np.column_stack([plan[:, 0], deck - sink_m, plan[:, 1]])
        top = np.column_stack([plan[:, 0], deck + height_m, plan[:, 1]])
        base = self._count
        self._positions.append(np.vstack([bottom, top]))
        self._normals.append(np.vstack([facing, facing]))
        self._uvs.append(_run_uvs(plan, height_m=height_m, sink_m=sink_m))

        stations = len(plan)
        low = base + np.arange(stations - 1)
        high = base + stations + np.arange(stations - 1)
        # `[b0, t0, t1] + [b0, t1, b1]` winds the front face to the **left of
        # travel**: the cross of `(t0 - b0)` and `(t1 - b0)` reduces to
        # `up x along`, which is `mitres`'s own normal. So the near-side fence,
        # which stands to the left, has to be flipped to look back at the road.
        first = np.column_stack([low, low + stations, high + 1])
        second = np.column_stack([low, high + 1, low + 1])
        quads = np.vstack([first, second])
        self._triangles.append(quads[:, ::-1] if flip else quads)
        self._count += 2 * stations
        return 2 * (stations - 1)

    def build(self, name: str) -> MeshData | None:
        """The mesh, minus collapsed triangles.

        `name` is the class `id`, and it is the mesh name **and** the glTF
        material name — one string for one identity, so the engine's material
        dispatch and the graders' mesh lookup cannot drift apart.
        """
        if not self._triangles:
            return None
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.vstack(self._normals).astype(np.float32),
            uvs=np.vstack(self._uvs).astype(np.float32),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            material=name,
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        return select_triangles(mesh, twice_area > _MIN_TWICE_AREA_M2)


def facing_away(mesh: MeshData) -> int:
    """Triangles whose winding disagrees with the normal they were given.

    The fence's own version of `surface.downward_facing`, and it asks the
    question that matters for a vertical surface: not "does this face the sky"
    but "does this face the road it was built to face". `railings.gdshader` is
    `cull_disabled`, so a flipped quad still draws — it draws lit from behind,
    which reads as a black panel and not as a missing one.
    """
    cross = mesh.triangle_cross()
    length = np.linalg.norm(cross, axis=1)
    intended = mesh.normals[mesh.triangles[:, 0]]
    agreement = (cross * intended).sum(axis=1) / np.where(length > 0.0, length, 1.0)
    return int((agreement < 0.0).sum())


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> RailingReport:
    """Read the region's published railings and write its `railings.glb`."""
    spec = city.railings
    report = RailingReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the shape `tramway`, `arrows` and `boxjunctions` all
        # take: a city whose estate publishes no railing layer ships none rather
        # than running a fence down every kerb it drew.
        log.info("city '%s' declares no railings block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    lines = read_lines(city, spec, region_id, transform, report, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # ⚠️ **Through `read_document`, not a bare parse**, for `arrows.py`'s
    # stated reason and one of this stage's own: `kerb_hidden_m` arrived at
    # `SURFACE_MANIFEST_SCHEMA` 5, and a manifest from before it parses fine and
    # simply reports no buried kerb anywhere — which draws 11.1% of the region's
    # railings across merged tarmac and counts them as a success.
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    drawn = ribbons(graph, surface, spec)

    # ⚠️ **One builder per class, and so one primitive per class.** They could
    # share one — the mask that tells a bollard from a fence is a material
    # parameter, not a vertex attribute — and they deliberately do not. Separate
    # meshes are what let `railing_error.py` walk the fence's feet without a
    # bollard's in the pile, what let each class carry its own `.tres`, and what
    # make a class's triangle count a number rather than a share. The cost is
    # two extra draw calls against a `<150` budget the drive scene reads 36 on.
    by_id = {klass.id: klass for klass in spec.classes}
    builders = {klass_id: _Builder() for klass_id in by_id}
    cells = _assign(lines, graph, drawn, spec, city, region_id, report)
    for (edge, klass_id, side), found in sorted(cells.items()):
        ribbon = drawn[edge]
        klass = by_id[klass_id]
        for start, stop, code in merge_runs(found, spec.sample_m, klass.bridge_gap_m):
            _draw_run(
                builders[klass_id],
                ribbon,
                klass,
                side,
                start,
                stop,
                code,
                spec.sample_m,
                report,
                found,
            )

    meshes: list[MeshData] = []
    for klass in spec.classes:
        mesh = builders[klass.id].build(klass.id)
        if mesh is None:
            continue
        counters = report.klass(klass.id)
        counters.facing_away = facing_away(mesh)
        counters.triangles = mesh.triangle_count
        counters.vertices = len(mesh.positions)
        low, high = mesh.aabb()
        counters.aabb = [list(low), list(high)]
        meshes.append(mesh)
    if meshes:
        report.bytes = write_glb(out_dir / RAILINGS_NAME, meshes)

    _write_manifest(out_dir, city, region_id, report)
    return report


def _assign(
    lines: list[tuple[np.ndarray, str]],
    graph: dict,
    drawn: dict[int, Ribbon],
    spec: Railings,
    city: CityConfig,
    region_id: str,
    report: RailingReport,
) -> dict[tuple[int, str, str], dict[int, dict[str, int]]]:
    """Sample every feature, put each sample on an edge, a class and a side.

    ⚠️ **The shift bar is applied per sample, not per run.** A run whose middle
    hugs the kerb and whose tail wanders into a plaza would otherwise be drawn
    whole or refused whole; judged per sample, the wandering tail simply stops
    being part of the run and `merge_runs` closes over what is left.

    ⚠️ **The class is part of the cell key, and it has to be.** A bollard row and
    a railing can be published along the same kerb — they are different objects
    in the same place — and pooled into one cell they would merge into a single
    run, drawn once, at whichever class's height won. Keyed apart they stay two
    runs and each is drawn as itself.
    """
    cells: dict[tuple[int, str, str], dict[int, dict[str, int]]] = {}
    if not lines or not drawn:
        return cells

    points, kinds = resample(lines, spec.sample_m)
    report.samples = len(points)
    report.metres_sampled = len(points) * spec.sample_m
    high = city.region_high(region_id)
    inside = (
        (points[:, 0] >= 0.0)
        & (points[:, 1] >= 0.0)
        & (points[:, 0] <= high[0])
        & (points[:, 1] <= high[1])
    )
    report.samples_outside_region = int((~inside).sum())

    index = SideIndex(_tracks(graph, drawn), spec.max_offset_m)
    assigned, unassigned = index.nearest(points[inside], kinds[inside])
    report.samples_unassigned += unassigned

    for item in assigned:
        klass = spec.class_of(item.kind)
        if klass is None:
            # Unreachable: `read_lines` admits nothing outside the table. Held
            # rather than asserted because a silently-dropped sample is exactly
            # the kind of loss this stage's counters exist to make impossible,
            # and `None` would otherwise surface as an unrelated KeyError below.
            raise ValueError(f"sample of {item.kind!r} belongs to no class; read_lines admitted it")
        counters = report.klass(klass.id)
        ribbon = drawn[item.edge]
        at_m = item.along_m - ribbon.trim_start_m
        shift_m = abs(_half_width_at(ribbon, at_m) + klass.outset_m - item.offset_m)
        # Recorded before the refusal, so `n` past what was drawn is the proof
        # this distribution can read outside its own filter (`Q58`).
        counters.shift_m.append(shift_m)
        if shift_m > spec.max_shift_m:
            counters.samples_over_shift += 1
            continue
        cell = cells.setdefault((item.edge, klass.id, item.side), {}).setdefault(
            int(item.along_m // spec.sample_m), {}
        )
        cell[item.kind] = cell.get(item.kind, 0) + 1

    for (_edge, klass_id, _side), found in cells.items():
        report.klass(klass_id).metres_deduped += len(found) * spec.sample_m
    return cells


def _tracks(graph: dict, drawn: dict[int, Ribbon]) -> list[tuple[int, np.ndarray]]:
    """`(edge id, published polyline)` for every edge that drew a ribbon.

    ⚠️ **The published polyline, not the ribbon's trimmed one.** `SideIndex`
    measures `along_m` in `roadgraph.json`'s own frame — that is the frame
    `kerbside.py` publishes its runs in and the only one the graph has — and
    `Ribbon.trim_start_m` is what converts it. Handing it the trimmed line
    instead would shift every run by a junction trim, silently, and a fence
    3.3 m along from where it belongs still looks like a fence.
    """
    return [
        (int(edge["id"]), np.asarray(edge["polyline"], dtype=np.float64))
        for edge in graph["edges"]
        if int(edge["id"]) in drawn
    ]


def _draw_run(
    builder: _Builder,
    ribbon: Ribbon,
    klass: RailingClass,
    side: str,
    start_cell: int,
    stop_cell: int,
    code: str,
    sample_m: float,
    report: RailingReport,
    occupied: dict[int, dict[str, int]] | None = None,
) -> None:
    """One merged run of one class, clipped to the ribbon and to its drawn kerb.

    Every bar and dimension comes off `klass`; `sample_m` is the one shared join
    parameter, the cell pitch this run's extent is expressed in. Taken as a float
    rather than as the whole `Railings` so the signature states that split
    instead of a paragraph having to — the join is shared, and nothing below it
    is.

    `occupied` is the run's own cell table, used only to count the metres drawn
    across bridged gaps — see `_bridged_m`. Optional so a test can drive one run
    without building one.
    """
    report_class = report.klass(klass.id)
    report_class.runs += 1
    published_start = start_cell * sample_m
    published_end = (stop_cell + 1) * sample_m
    if published_end - published_start < klass.min_run_m:
        report_class.runs_dropped += 1
        report_class.metres_dropped_short += published_end - published_start
        return

    start_m = published_start - ribbon.trim_start_m
    end_m = published_end - ribbon.trim_start_m
    clipped_start = min(max(start_m, 0.0), ribbon.length_m)
    clipped_end = min(max(end_m, 0.0), ribbon.length_m)
    report_class.metres_outside_ribbon += (end_m - start_m) - (clipped_end - clipped_start)
    if clipped_end - clipped_start <= 0.0:
        return

    visible = _visible(ribbon, side, clipped_start, clipped_end)
    report_class.metres_on_buried_kerb += (clipped_end - clipped_start) - sum(
        high - low for low, high in visible
    )

    drawn: list[tuple[float, float]] = []
    for low, high in visible:
        if high - low < klass.min_run_m:
            # A sliver left between two buried stretches is a panel, not a
            # fence. Counted apart from the short-run refusals above because it
            # is measured in ribbon metres and they are measured in published
            # ones.
            report_class.metres_dropped_sliver += high - low
            continue
        at = np.arange(low, high, klass.station_m)
        at = np.append(at, high) if at[-1] < high else at
        plan = np.empty((len(at), 2))
        deck = np.empty(len(at))
        for row, distance in enumerate(at):
            plan[row], deck[row] = _station(ribbon, klass.id, side, float(distance))

        facing = _facing(plan, ribbon, at)
        builder.strip(
            plan,
            deck,
            height_m=klass.height_m,
            sink_m=klass.base_sink_m,
            facing=facing,
            flip=side == NEARSIDE,
        )
        drawn.append((low, high))
        report_class.drawn_m += high - low
        report_class.drawn_m_by_type[code] = report_class.drawn_m_by_type.get(code, 0.0) + (
            high - low
        )
        if side == NEARSIDE:
            report_class.drawn_m_nearside += high - low

    if occupied is not None:
        report_class.metres_bridged += _bridged_m(
            drawn, occupied, start_cell, stop_cell, ribbon, sample_m
        )


def _bridged_m(
    drawn: list[tuple[float, float]],
    occupied: dict[int, dict[str, int]],
    start_cell: int,
    stop_cell: int,
    ribbon: Ribbon,
    sample_m: float,
) -> float:
    """Drawn metres standing where the source published no railing.

    ⚠️ **`merge_runs` bridges gaps up to `bridge_gap_m`, and those metres are
    drawn without ever having been sampled.** Inherited from `kerbside.py`, and
    right for the same reason — a break shorter than a car is a digitising
    artefact rather than a gap in a fence — but this stage argues that every
    metre it draws is accounted for, and without this counter the partition is
    out by 400 m in Wan Chai with nothing saying so.

    Exact rather than estimated: only the part of an unsampled cell that
    survived the ribbon clip and the buried-kerb cut is counted, which is why
    it takes the drawn ranges rather than the run's own extent.
    """
    bridged = 0.0
    for cell in range(start_cell, stop_cell + 1):
        if cell in occupied:
            continue
        low = cell * sample_m - ribbon.trim_start_m
        high = low + sample_m
        for start, stop in drawn:
            bridged += max(0.0, min(stop, high) - max(start, low))
    return bridged


def _facing(plan: np.ndarray, ribbon: Ribbon, at: np.ndarray) -> np.ndarray:
    """Unit direction, per station, from the fence back toward the centreline.

    Derived from the two published lines rather than from the fence's own
    heading: at a mitre the fence and the centreline are not parallel, and it is
    the centreline the road is on.
    """
    centre = np.column_stack(
        [
            np.interp(at, ribbon.along, ribbon.points[:, 0]),
            np.interp(at, ribbon.along, ribbon.points[:, 2]),
        ]
    )
    across = centre - plan
    length = np.hypot(across[:, 0], across[:, 1])
    unit = across / np.where(length > 0.0, length, 1.0)[:, None]
    return np.column_stack([unit[:, 0], np.zeros(len(unit)), unit[:, 1]]).astype(np.float32)


def _class_document(report: ClassReport) -> dict:
    """One class's counters, in the order the chain runs.

    ⚠️ **The metres are a chain, not a partition, and the docstring on
    `ClassReport` is the one that explains why.** Read top to bottom: what was
    admitted, what the join priced and refused, what the ribbon and the buried
    kerbs took, what was drawn, and how much of what was drawn the stage
    invented.
    """
    return {
        "read": report.read,
        "read_m": round(report.read_m, 2),
        # ⚠️ **The price of the registration.** Recorded over every assigned
        # sample including the ones `max_shift_m` then refused, so `n` exceeding
        # the drawn metres is the proof it reads outside its own filter (`Q58`).
        # A shift creeping upward across builds is the widening and the survey
        # drifting apart — a finding about the ribbon, not a bar to retune.
        "shift_m": report.measured(report.shift_m),
        "samples_over_shift": report.samples_over_shift,
        "metres_deduped": round(report.metres_deduped, 2),
        "runs": report.runs,
        "runs_dropped": report.runs_dropped,
        # ⚠️ Two frames, and they are not addable. A short run is refused in
        # *published* metres before the ribbon clip; a sliver is refused in
        # *ribbon* metres after it and after the buried-kerb cut.
        "metres_dropped_short": round(report.metres_dropped_short, 2),
        "metres_dropped_sliver": round(report.metres_dropped_sliver, 2),
        "metres_outside_ribbon": round(report.metres_outside_ribbon, 2),
        # ⚠️ Metres on a kerb the surface stage does not draw, because another
        # ribbon covers it. Drawn, this is a fence standing in merged tarmac.
        "metres_on_buried_kerb": round(report.metres_on_buried_kerb, 2),
        "drawn_m": round(report.drawn_m, 2),
        # ⚠️ **The one part of `drawn_m` the stage invents.** `merge_runs`
        # bridges gaps up to the class's `bridge_gap_m`, so these metres are
        # drawn where the source published nothing. Watch it hardest on
        # `bollards`, whose features have a median published length of 1.00 m.
        "metres_bridged": round(report.metres_bridged, 2),
        "drawn_m_by_type": {
            code: round(metres, 2) for code, metres in sorted(report.drawn_m_by_type.items())
        },
        "drawn_m_nearside": round(report.drawn_m_nearside, 2),
        # ⚠️ **Must be 0.** Every quad is wound to look at the carriageway;
        # `cull_disabled` means a flipped one still draws, lit from behind, as a
        # black panel rather than as an absence (`Q58`).
        "facing_away": report.facing_away,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "aabb": report.aabb,
    }


def _write_manifest(out_dir: Path, city: CityConfig, region_id: str, report: RailingReport) -> int:
    document = {
        "schema_version": RAILINGS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was drawn, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what `CITY_SCHEMA`
        # 11 was bumped over.
        "asset": RAILINGS_NAME if report.drawn_m > 0.0 else None,
        # The read, as four disjoint parts of `features`. One read of one layer,
        # so this half is not per class.
        # ⚠️ `features` is features; every count below it is **parts**. The
        # two differ by ten in this region, and mixing them is how a share comes
        # out over one (`kerbside.py`).
        "features": report.features,
        "parts": report.parts,
        "not_drawn_line_type": report.not_drawn_line_type,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "read": report.read,
        # ⚠️ **What the class table costs, per published code.** Nothing in the
        # bundle defines `LINETYPE` and the layer's other columns are
        # cartography (`Q60`), so admitting `CRAIL1` as a fence and `bollard0`
        # as a post and neither `SOLID` nor `AMT1` as anything is an argument
        # from the code strings themselves. This is the figure that makes the
        # argument reviewable rather than assumed.
        "source_m": round(report.source_m, 2),
        "refused_m": {code: round(metres, 2) for code, metres in sorted(report.refused_m.items())},
        # ⚠️ Separate from `refused_m`, because six of this region's features put
        # 1,579 m of an *admitted* code on a flyover parapet — a `Q15` refusal,
        # not a vocabulary one.
        "on_structure_m": round(report.on_structure_m, 2),
        "read_m": round(report.read_m, 2),
        # The join. ⚠️ **Shared and unsplittable**: `SideIndex.nearest` returns
        # unassigned as a count rather than as the samples themselves, so there
        # is nothing to attribute to a class. A class that joins to nothing is
        # invisible here and visible as its own `read_m` against its `drawn_m`.
        "samples": report.samples,
        "samples_outside_region": report.samples_outside_region,
        "samples_unassigned": report.samples_unassigned,
        "metres_sampled": round(report.metres_sampled, 2),
        # ⚠️ **Everything below the join is per class, and there is deliberately
        # no total.** A top-level `drawn_m` would now mean fence plus bollard
        # plus vehicle barrier, and a reader who kept the schema-1 reading would
        # count all three as pedestrian railing with nothing to say otherwise.
        # That is what `RAILINGS_MANIFEST_SCHEMA` 2 is for: the key is removed
        # rather than broadened, so an old consumer fails loudly.
        "classes": {
            klass_id: _class_document(counters)
            for klass_id, counters in sorted(report.classes.items())
        },
        # One file, so one byte count.
        "bytes": report.bytes,
    }
    return write_document(out_dir / RAILINGS_MANIFEST_NAME, document)


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
    log.info("railings: %d features -> %.0f m read", report.features, report.read_m)
    for klass_id, counters in sorted(report.classes.items()):
        log.info(
            "  %-9s %6.0f m read -> %6.0f m drawn in %3d runs, %5d triangles",
            klass_id,
            counters.read_m,
            counters.drawn_m,
            counters.runs,
            counters.triangles,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
