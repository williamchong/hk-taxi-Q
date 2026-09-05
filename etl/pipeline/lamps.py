"""Published lamp posts, drawn as their own mesh (`P3-26`).

The vertical half of the street estate, landing in `Q58`/`Q59`'s pattern: one
primitive, one draw call, no collider, an optional `city.json` key, and counters
the stage publishes about itself. It is `signs.py`'s simpler sibling — no
`GG_NAME` join, no abbreviation layer, no face table, no atlas — and the five
findings that make it different belong at the top of the file.

✅ **THE VOCABULARY IS PUBLISHED, and this is the first street-furniture stage
here of which that is true.** `UtilityPoint.UTILITYPOINTTYPE` carries a
coded-value domain **inside the geodatabase** — `LPO - Lamp post`, readable out
of every sheet's `.gdbtable` bytes, alongside `FWH`/`SWH` hydrants and `EPO`. So
`kinds` is not `railings.classes` and not `signals.head_prefixes`: those two are
whitelists read off code strings because nothing published defines them (`Q60`,
`Q76`), and this one is a *selection from an answer the publisher wrote down*. It
is arguably better evidence than `arrows.py`'s glyph table, which is transcribed
**by eye** off a drawing (`Q59`), because it is machine-readable and travels with
the data. `refused_by_kind` publishes the rest of the domain anyway, on
`railings.py`'s precedent: it costs nothing and it is what lets a reader see the
selection rather than take it.

⚠️ **The layer publishes a POSITION AND NOTHING ELSE.** Six columns —
`LASTUPDATEDATE`, `UTILITYPOINTID`, `UTILITYPOINTTYPE`, `STATUS`,
`DISPLAYSTATUS`, `DATASOURCE` — and not one of them is a length, an angle or a
level. Geometry `Z` is `0.0` on all 1,263, and that is the file's convention
rather than a defect: `SpotHeight`, a layer whose entire purpose is heights,
also reads `0.0` and keeps its value in a `HEIGHTVALUE` column this layer does
not have. So **every dimension drawn here is authored** — `Q60`'s railing debt
and `P3-16`'s plate debt at a fourth and fifth layer.

🔴 **NO ELEVATION COLUMN, so a lamp on a flyover is drawn on the street
underneath.** Every other stage reading a TD or LandsD point layer gets an
`ELEVATION` and refuses what is on a structure (`Q13`, `Q21`); this one has
nothing to refuse on. The honest instrument is `nearest_is_elevated`: how many
**candidates** have an off-grade edge nearer than the nearest level-0 one. ⚠️ It
is counted before the `too_far` and `no_ribbon` guards, so it is over all 1,263
and not over the 1,127 that found a host — deliberately, because a lamp with no
host at all is exactly the case a flyover produces. It is report-only and
cannot fix the placement — it says how big the problem is, which is the only true
thing available. It reads **177 of 1,263,
14.0%** — twice the 7% `kerbside.py` measured for its own layer, because Wan Chai
carries the Gloucester Road flyovers.

⚠️ **The position is registered, not read** — `Q60`'s move arriving at a fourth
layer, after the railings, the signs and the signals. **64.1%** of the region's
lamp posts are surveyed inside the drawn 1.6x ribbon — **810 of 1,263**, a median
1.46 m past the drawn kerb **over that subset** — so drawn where published four
fifths of a kilometre of Wan Chai's columns stand in the carriageway. ⚠️ The
denominator matters: `shift_m` is published over all 1,127 registered posts and
its p50 is 1.34, which is a different question about the same layer.

🔴 **The registration is `signs.py`'s and NOT `signals.py`'s, and the split is
deliberate.** `Q78` clamped the sign move to **outward only** — the argument for
moving a post at all is that the carriageway floor draws the ribbon past the real
carriageway, and that argument runs outward and nowhere else. `CLAUDE.md` records
that `railings.py` and `signals.py` are deliberately *not* aligned with it,
because **a fence is a run and the bar is per sample, so a conditional push would
zigzag it**. A lamp post is not a run. It is a discrete object like a sign post,
so `Q78` applies here in full and `posts_kept_as_surveyed` exists for its reason.

🔴 **AND THE REFUSAL RUNS IN TWO STAGES, WHICH IS WHERE "NO LAMP POST STANDS IN
THE ROAD" ACTUALLY COMES FROM.** `_register` clears the post's *own* host kerb.
That says nothing about the edge next door: at a junction mouth or a dual
carriageway several 1.6x ribbons overlap and the drawn city has no footway left
at all. So the placed point is re-snapped against **every** edge and refused if
it lands inside any drawn ribbon. `signs.py` measured the obvious alternative —
iterate the push — and it is worse: it plateaus at 9.7% while taking the worst
shift from 5.52 m to **16.77 m**, which is a post on the wrong street.
`min_kerb_clearance_m` is what proves the invariant held, and it is **not** a
tautology: a bug in the foot reconstruction drives it negative, which is exactly
the 10.6 m defect `signs.py` records catching.

🔴 **THE ARM DIRECTION IS DERIVED AND UNGRADED (`Q62`), AND THE OBVIOUS COUNTER
FOR IT WAS REFUSED AS A TAUTOLOGY.** Nothing published says which way a lantern
reaches. The stage asserts it reaches over the carriageway — reusing the kerb
side the registration already computed, which is what an installed column
physically does — on `P3-22`'s stated-assumption precedent. An `arms_against_kerb`
counter would then read 0 **by construction**, and `Q72` is the record of what
that costs: the NO ENTRY counter that stood before it certified the wrong state
for exactly this reason, because 0 was unreachable. *"The test of a counter here
is not whether it reads 0 but whether any reachable configuration makes it
non-zero."* So what ships instead is `lantern_overhang_m` — how far each lantern
hangs over the drawn carriageway, whose value **is** the design intent made
visible — and `lanterns_past_centreline`, which must be 0 and which raising
`arm_reach_m` makes non-zero. The facing itself is graded by an A/B render at one
camera, because nothing published can grade it.

🔴 **AND THIS LAYER FAILS DIFFERENTLY FROM EVERY OTHER ONE HERE: ITS
REGULARITY IS ITS CONTENT.** `GAME_DESIGN.md` prices a missing sign at nothing
against a misplaced one, and that is why every stage above refuses freely. A lamp
row is not like that — a refused column is a **hole** in a rhythm the eye reads
directly. Surveyed, the region has 5 neighbour gaps over 40 m; drawn, it has 16.
`gaps_over_report_m` and the two spacing distributions are the instrument, and
they are the numbers a widening change moves without touching a lamp.

⚠️ **No lit lantern, and its absence is the decision to resist changing.** `Q38`
bakes `exposure_anchor` into `COLOR_0` at build time, `Q26` has not chosen a
look, there is one lighting rig, and `ART_DESIGN.md` ends its Lighting section
with *"Resist adding lights."* 897 `OmniLight3D`s is not a shippable answer on a
Mobile tier that ships no shadow maps. This stage buys night mode **nothing**,
and that is the honest position — night's blockers are `Q38` and `Q26`, and
neither of them is geometry.
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

# ⚠️ **Imports from sibling stages rather than copies**, the shape `signs.py` and
# `signals.py` both take. `nearside` is the canonical statement of a convention a
# flip in which mirrors every side-keyed feature in the city; `facing_away` asks
# whether winding agrees with the given normal, which is the question a
# *vertical* surface needs; and `disc` is the prism ring whose reversal is a
# recorded defect in two stages already.
from pipeline import gdb
from pipeline.arrows import ArrowReport, Ribbon, nearside, ribbons
from pipeline.config import Config, GameTransform, Lamps, load_config
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.meshbuild import ColouredBuilder
from pipeline.placements import (
    Placement,
    drawn_totals,
    placement,
    refuse_unbuilt,
    write_placements,
)
from pipeline.polyline import Segments, Snap, bearing_deg
from pipeline.railings import facing_away
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.signs import disc
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

LAMPS_NAME = "lamps.glb"
LAMPS_MANIFEST_NAME = "lamps.json"
# 2 since `P5-3` (`Q115`): `lamps.glb` is a LIBRARY — one mesh per drawn kind,
# drawn at the origin with its arm pointing north — and the columns stand where
# `lamps_placements.json` puts them. `triangles`, `vertices` and `aabb` still
# describe what is DRAWN, so a reader comparing them to the merged build reads
# the same numbers; `library_*`, `placements` and `placements_document` are new.
# A v1 reader publishing a `city.json` with no `lamps_placements` would ship a
# library and stand nothing on it.
LAMPS_MANIFEST_SCHEMA = 2
LAMPS_PLACEMENTS_NAME = "lamps_placements.json"

# The glTF material name `tools/generated_scene_import.gd` dispatches on, and the
# one channel the format offers for it. ⚠️ **A name, not a shader**: this layer
# shares `signs.gdshader` with the signs and the signals, and differs only in the
# uniforms `game/tuning/lamps.tres` sets — `Q61`'s rule for the railing classes
# and `Q71`'s for the three paint layers, at a fifth place.
LAMPS_MATERIAL = "lamps"


@dataclass
class LampReport:
    """What the stage read, selected, registered and drew.

    ⚠️ **The counters are what can see this stage fail, because none of its
    failures look like anything in a frame** — `Q58`'s lesson. A column on the
    wrong side of the street is a perfectly drawn lamp post. An arm reaching the
    wrong way is a perfectly drawn lamp post. A selection that started admitting
    hydrants draws perfectly good lamp posts on them.

    The partitions:

        features   == not_a_lamp + empty_geometry + duplicate_point + candidates
        candidates == drawn + too_far + no_ribbon + over_shift + in_carriageway
                      + merged
    """

    features: int = 0
    # ✅ **The selection's refusals, over a domain the publisher DEFINES** — the
    # hydrants and the one electricity pole. `refused_by_kind` is where a reader
    # sees which, and unlike `railings.classes` and `signals.head_prefixes` this
    # one is checkable against the source rather than only reviewable.
    not_a_lamp: int = 0
    empty_geometry: int = 0
    # 🔴 **A counted refusal, because an uncounted one breaks the partition above
    # exactly when it does something.** It reads 0 on this region — the 1,263
    # published points are distinct to 1 mm — so shipping it as a bare `continue`
    # looked free and was not: the identity would have failed silently on the
    # first publisher that repeated a point across a sheet cut, which is the one
    # case the guard exists for.
    duplicate_point: int = 0
    candidates: int = 0

    drawn: int = 0
    too_far: int = 0
    no_ribbon: int = 0
    over_shift: int = 0
    # 🔴 Columns still standing in a drawn carriageway after registration cleared
    # their own host's kerb, because they landed inside a *different* edge's
    # ribbon. A finding about `Q19`'s widening, not about this stage.
    in_carriageway: int = 0
    # Columns folded together *after* registration pushed them onto one point.
    # ⚠️ **Every one of these is a coincidence this stage MADE**: the layer
    # publishes zero coincident pairs under 0.05 m, so unlike `signals.py` there
    # is no surveyed clustering here and none is invented.
    merged: int = 0
    # ⚠️ **`Q78`'s branch.** A post already standing clear of the drawn kerb keeps
    # the point LandsD surveyed, and appends a real `0.0` to `shift_m` rather
    # than being skipped — which is what keeps the identity over `len(shift_m)`
    # closing, and what tells a reader how many of the distribution's zeros are
    # these.
    posts_kept_as_surveyed: int = 0

    # ⚠️ **How far each column moved sideways onto the drawn kerb**, recorded over
    # every registered post **including the ones `max_shift_m` then refused**, so
    # `n` exceeding `drawn` is the proof it can read outside its own bar (`Q58`'s
    # `drawn_gauge_m` trap, caught in `arrows.py`, `roadmarks.py` and
    # `railings.py`). 🔴 **It is an ABSOLUTE value and therefore cannot report
    # the direction of the move it measures** — which is precisely what let the
    # sign registration pull 95 of 654 posts *toward* the carriageway through
    # three published distributions and a green `check.sh` (`Q78`). The clamp in
    # `_register` is what makes the direction safe; this number never could.
    shift_m: list[float] = field(default_factory=list)
    # 🔴 **There is deliberately no `inside_ribbon_m` here, and `signs.py` has
    # one.** How far a column was surveyed inside the drawn carriageway is
    # `max(0, shift_m - outset_m)` on every path through `_register` — checked
    # against the shipped run, where the two agreed to four decimals at every
    # quantile and were exactly `outset_m` apart. A second 1,127-element list
    # publishing an affine transform of the first is redundant state, not a
    # second instrument, and a reader who wants it can subtract.

    # 🔴 **The invariant, and it is NOT a tautology.** The minimum distance from
    # any drawn column to the drawn kerb it stands behind, over every edge in the
    # region. It must be non-negative, and a bug in the foot reconstruction
    # drives it negative — `signs.py` records exactly that defect, where a post
    # 5 m past an edge's end reconstructed to 5 m off the road and published the
    # 10.6 m move it then made as 0.6 m.
    min_kerb_clearance_m: float = 0.0

    # 🔴 **What the derived arm direction actually did, since a counter over the
    # direction itself would read 0 by construction** — `Q72`'s tautology, which
    # certified the wrong state for a whole region. How far each lantern hangs
    # over the drawn carriageway, in metres past the kerb.
    lantern_overhang_m: list[float] = field(default_factory=list)
    # ⚠️ **Must be 0, and raising `arm_reach_m` is what makes it non-zero** —
    # which is the test `Q72` says a counter has to pass. A lantern past the
    # centreline is hanging over the opposing traffic.
    lanterns_past_centreline: int = 0

    # 🔴 **The honest instrument for a refusal this stage CANNOT make.**
    # `UtilityPoint` publishes no elevation, so a lamp on a flyover is drawn on
    # the street underneath; this counts the posts whose nearest edge of *any*
    # level is elevated, which is how big that is. Report-only.
    nearest_is_elevated: int = 0

    # 🔴 **This layer's own failure mode, which no other stage here has.** A
    # missing sign is invisible; a missing lamp in a regular row is a hole. Both
    # distributions are published because the *difference* is the finding — the
    # drawn one alone says nothing about what refusing cost.
    spacing_surveyed_m: list[float] = field(default_factory=list)
    spacing_drawn_m: list[float] = field(default_factory=list)
    gaps_over_report_m: int = 0

    # ✅ The whole published domain, both halves.
    drawn_by_kind: dict[str, int] = field(default_factory=dict)
    refused_by_kind: dict[str, int] = field(default_factory=dict)

    # Triangles whose winding disagrees with the normal they were given.
    # ⚠️ **Must be 0.** `signs.gdshader` is `cull_back`, so winding decides
    # visibility and the normal attribute does not: the tramway shipped 5,111 of
    # 5,112 triangles facing the ground with everything else correct, and the
    # signs shipped 3,200 on their first build because the prism ring was wound
    # the way a plate wants. This stage reuses that prism.
    facing_away: int = 0
    # What is DRAWN: the library under every stand (`P5-3`), so these read the
    # same as the merged build they replaced. The library's own size is
    # `library_*`; `placements` counts entries in `lamps_placements.json`, and
    # `placements_refused` the stands whose mesh collapsed to nothing — part of
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

    # Reused rather than restated, the line `signs.py`, `railings.py`,
    # `signals.py` and `boxjunctions.py` all carry: p90/p99/max beside the median
    # is `arrows.py`'s choice and its reason — a median near zero is also what a
    # wholly broken join looks like.
    measured = staticmethod(ArrowReport.measured)


@dataclass(frozen=True)
class Lamp:
    """One published lamp post, at the point LandsD surveyed."""

    kind: str
    x: float
    z: float


@dataclass
class _Placed:
    """One column after registration, with the arm direction it was given."""

    # The published code this column was admitted as, carried so `drawn_by_kind`
    # counts what was **drawn** rather than what was declared — a city declaring
    # two kinds and drawing one is exactly what the histogram is for.
    kind: str
    x: float
    z: float
    y: float
    # Unit vector in game plan space, from the column toward the carriageway.
    # 🔴 Derived from the kerb side and ungraded (`Q62`) — see the module
    # docstring for why the obvious counter over it was refused.
    arm: np.ndarray
    # How far the lantern sits from the column along that arm, in plan.
    # ⚠️ **Carried rather than re-read from the spec, and `_draw_lamp` reads it
    # from HERE** — which is what makes the claim true. Written the other way
    # round, with the draw reading `spec` and the grader reading the placement,
    # the field records the config while the grader's stated property quietly does
    # not hold. Review caught exactly that. ⚠️ Since `P5-3` the draw reads it off
    # the FIRST post of each kind (`_library_post`) and every other stand of that
    # kind inherits the library's; `_measure_placement` still grades each post's
    # own. One value per kind today, and a per-post reach is the moment this
    # stops holding — `build_region` asserts it rather than assuming it.
    arm_reach_m: float
    # 🔴 **Where the second-stage refusal SETTLED this column**, carried rather
    # than re-derived. `_measure_placement` used to re-snap every kept post — a
    # third `Segments.nearest` over the same point, ~25 ms, and worse than
    # redundant: a grader that re-derives its own truth can disagree with the
    # refusal that let the post through. These are the numbers that refusal used.
    kerb_offset_m: float
    half_width_m: float


# --------------------------------------------------------------------------
# The read
# --------------------------------------------------------------------------


def read_lamps(
    city: Config,
    spec: Lamps,
    region_id: str,
    transform: GameTransform,
    report: LampReport,
    *,
    sources_root: Path | None,
) -> list[Lamp]:
    """Every lamp post the selection admits, at its published position.

    Everything refused here is refused on what the *publisher* says — a code
    outside the declared kinds, an empty geometry — and each refusal is counted
    rather than logged, because the counts are what `Q58` says has to be able to
    see this stage fail.

    ⚠️ **There is no `on_structure` refusal and there cannot be**: this layer
    publishes no elevation column at all. See `nearest_is_elevated`, which counts
    the problem rather than refusing it.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)
    bbox = city.projected_bounds(region_id).bbox

    lamps: list[Lamp] = []
    seen: set[tuple[float, float]] = set()
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        kinds = layer.column(spec.layer.field("kind"))
        owners, plan = gdb.points(layer)
        if len(owners) == 0:
            continue
        game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])

        for row, owner in enumerate(owners):
            report.features += 1
            kind = str(kinds[owner])
            if not spec.is_lamp(kind):
                report.not_a_lamp += 1
                report.refused_by_kind[kind] = report.refused_by_kind.get(kind, 0) + 1
                continue
            x = float(game_x[row])
            z = float(game_z[row])
            if not (math.isfinite(x) and math.isfinite(z)):
                # `POINT EMPTY` is spelled NaN in WKB and `gdb.points` passes it
                # through by design. Refused here, where the meaning is known.
                report.empty_geometry += 1
                continue
            # ⚠️ **A sheet cut clips a point layer by DUPLICATING nothing** — the
            # region's 1,263 are already distinct to 1 mm, measured — but the
            # six sheets overlap at their edges and `podiums.stitch` exists
            # because LandsD does clip *polygons* across them. Deduplicating on
            # the exact coordinate costs nothing and means a publisher who starts
            # repeating a point across a cut does not draw two columns in one
            # place. It is not a merge: `merge_m` folds what registration moved
            # together, and this folds what was never two objects.
            key = (round(x, 3), round(z, 3))
            if key in seen:
                report.duplicate_point += 1
                continue
            seen.add(key)

            report.candidates += 1
            lamps.append(Lamp(kind=kind, x=x, z=z))
    return lamps


# --------------------------------------------------------------------------
# The mesh
# --------------------------------------------------------------------------


# The accumulator is `meshbuild.ColouredBuilder` — `signs.ColouredBuilder`'s shape,
# reduced: this layer is **one** colour, so the vertex colour carries nothing a
# material could not. It is kept because `signs.gdshader` reads `COLOR_0` and a
# mesh that stopped supplying it would render **white**. ⚠️ That single colour
# is why `signs.colours`' exemption from `Q33` does not transfer to this stage:
# the sign livery has to ride the vertex because a plate is four colours in one
# draw call, and a lamp post is not. Its colour comes out of the `materials:`
# table instead, where `_check_exposure` grades it.


def _strut(
    builder: ColouredBuilder,
    spec: Lamps,
    start: np.ndarray,
    end: np.ndarray,
    radius: float,
    *,
    cap_end: bool,
    seed: np.ndarray,
) -> None:
    """A closed prism between two points in world space.

    `seed` orients the ring — which of its corners faces which way. ⚠️ **The
    column passes its arm as the seed since `P5-3`, and that is load-bearing.**
    A library column is drawn once with its arm north and stood at the bearing
    of the arm it was given, so every corner of its ring has to turn with the
    arm too; seeded from world `X`, the ring stayed axis-aligned in the merged
    build and the stood library differed from it by up to 30° of ring — its
    corners **46.6 mm** from the merged build's on the 90 mm column radius,
    measured over all 892 columns (`Q115`), invisible from the road and not
    identical. `tests/test_lamps.py` pins the library against the in-place
    draw, which is the ring as it turns with the arm.

    `signs._draw_pole` generalised off the vertical, because a bracket arm is the
    same object lying over. The column passes `start` at the deck and `end` at
    its top; the arm passes two points that differ in all three ordinates.

    ⚠️ **No cap at `start`, ever.** For the column that end meets the footway and
    nothing sees under it; for the arm it is buried inside the column. `cap_end`
    is what closes the far end, and the arm does not need it either — the lantern
    sits on it.

    🔴 **THE RING IS NOT REVERSED HERE, AND THAT IS THE OPPOSITE OF WHAT
    `signs._draw_pole` AND `signals._draw_post` BOTH DO.** Both of those reverse
    it, both carry a paragraph saying the reversal "is the whole correctness of
    this function", and copying that paragraph across is exactly what this
    function did first: it shipped **25,116 of 35,880** triangles facing away.

    The reason the fix does not transfer is that those two spell no frame. They
    map `disc`'s `(u, v)` straight onto world `(X, Z)` and wind the quad in an
    order that then needs the ring flipped. This one builds an explicit frame
    with `u x v == axis` — it has to, because a bracket arm is not vertical and
    there is no world plane to borrow — and in that frame a counter-clockwise
    ring gives `(o1 - o0) x axis` along `+outward`, which is what the quad below
    is wound for. Reversing it inverts every side face of every column and arm
    in the city.

    ⚠️ **So "inherit the recorded defect's fix" is itself a way to ship the
    defect.** What settled it was `facing_away`, on the first run, before the
    asset was ever looked at — which is the whole argument for that counter.
    """
    axis = end - start
    length = float(np.linalg.norm(axis))
    if length <= 0.0:
        return
    axis = axis / length
    # Any vector not parallel to the axis gives a frame. The arm seeds from `_UP`
    # and an arm steeper than ~63° would be nearly parallel to it, so the
    # fallback is picked against the axis rather than hoped for.
    if abs(float(np.dot(seed, axis))) > 0.9:
        seed = np.array([1.0, 0.0, 0.0])
    u = np.cross(seed, axis)
    u = u / float(np.linalg.norm(u))
    v = np.cross(axis, u)

    ring = disc(radius, spec.column_sides)
    colour = spec.column_material.colour
    offsets = [ring[i][0] * u + ring[i][1] * v for i in range(spec.column_sides)]
    for index in range(spec.column_sides):
        o0 = offsets[index]
        o1 = offsets[(index + 1) % spec.column_sides]
        outward = o0 + o1
        span = float(np.linalg.norm(outward))
        if span <= 0.0:
            continue
        builder.polygon(
            np.vstack([start + o0, start + o1, end + o1, end + o0]), outward / span, colour
        )
    if cap_end:
        builder.polygon(np.vstack([end + o for o in offsets]), axis, colour)


def _lantern(
    builder: ColouredBuilder, spec: Lamps, centre: np.ndarray, forward: np.ndarray
) -> None:
    """The lantern housing: a closed box, hanging at the far end of the arm.

    ⚠️ **All six faces, including the top.** A lamp post is 9 m tall and the
    player's camera is at 2, so the underside is the face actually seen from the
    road — but the city has viewpoints above the deck (`ART_DESIGN.md`'s
    `overview`) and a five-faced box reads as a hole from every one of them. The
    column's bottom cap is omitted because it meets the footway; this is not that
    case.

    ⚠️ **`(forward, right, up)` is right-handed and the winding depends on it.**
    `right = (f.z, 0, -f.x)` gives `f x r == up`, so each face lists its two
    in-plane half-vectors in the order whose cross product **is** its outward
    normal — which is what makes the quad below wind counter-clockwise seen from
    outside. Reorder a pair and that face turns black under `cull_back`, with
    `facing_away` as the only thing that says so.
    """
    right = np.array([forward[2], 0.0, -forward[0]])
    up = np.array([0.0, 1.0, 0.0])
    ahead = 0.5 * spec.lantern_length_m * forward
    across = 0.5 * spec.lantern_width_m * right
    over = 0.5 * spec.lantern_depth_m * up
    colour = spec.column_material.colour

    for normal, offset, a, b in (
        (forward, ahead, across, over),
        (-forward, -ahead, over, across),
        (right, across, over, ahead),
        (-right, -across, ahead, over),
        (up, over, ahead, across),
        (-up, -over, across, ahead),
    ):
        origin = centre + offset
        builder.polygon(
            np.vstack([origin - a - b, origin + a - b, origin + a + b, origin - a + b]),
            normal / float(np.linalg.norm(normal)),
            colour,
        )


# --------------------------------------------------------------------------
# The stage
# --------------------------------------------------------------------------


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> LampReport:
    """Read the region's published lamp posts and write its `lamps.glb`."""
    spec = city.lamps
    report = LampReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the shape `tramway`, `arrows`, `boxjunctions`,
        # `railings`, `signs`, `roadmarks` and `signals` all take: a city whose
        # estate publishes no lamp layer ships none rather than putting a column
        # every twenty metres down every kerb it drew.
        log.info("city '%s' declares no lamps block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    lamps = read_lamps(city, spec, region_id, transform, report, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, the restriction `kerbside.py`, `tramway.py`, `arrows.py`,
    # `signs.py` and `signals.py` all make: for 7% of the kerbside samples the
    # nearest edge of *any* level was elevated, and the street the feature is
    # actually on was a median 4 m away.
    at_grade = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    segments = Segments.of(at_grade)
    # 🔴 **The OFF-GRADE edges alone, for one report-only counter.** This layer
    # publishes no elevation, so unlike every sibling stage there is nothing to
    # refuse a flyover lamp on — `nearest_is_elevated` is what says how big that
    # is instead. ⚠️ **Indexing only the off-grade edges is exact, not an
    # approximation of indexing all of them**: the level-0 set is already indexed
    # above, so "some edge of any level is nearer than the nearest level-0 edge"
    # is precisely "some off-grade edge is". Verified to give the identical 177
    # over a 60-edge index instead of a 797-edge one.
    off_grade = Segments.of([edge for edge in graph["edges"] if int(edge["elevation_level"]) != 0])

    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    ribbon_by_edge = ribbons(graph, surface)

    # ⚠️ **Sorted, and the sort is not cosmetic.** `_merge` below is greedy and
    # first-wins, so a mesh built from an unsorted read is not reproducible
    # between two builds of one input — `signals._assemble` records the same
    # requirement for the same reason.
    lamps.sort(key=lambda lamp: (lamp.x, lamp.z))
    report.spacing_surveyed_m = _spacing_m([(lamp.x, lamp.z) for lamp in lamps])

    placements: list[_Placed] = []
    for lamp in lamps:
        snap = segments.nearest(lamp.x, lamp.z)
        nearest_off_grade = off_grade.nearest(lamp.x, lamp.z)
        if nearest_off_grade.distance_m < snap.distance_m - 1e-9:
            # Report-only: an edge of some level lies nearer than the level-0 one
            # this post was hosted to, which is what a flyover lamp looks like
            # from here. It cannot be refused on — see the module docstring.
            report.nearest_is_elevated += 1
        if snap.distance_m > spec.max_offset_m:
            # No level-0 street near enough to say which kerb this column stands
            # on. Refused rather than guessed at: without a host edge there is no
            # kerb side, and without a kerb side there is no arm direction.
            report.too_far += 1
            continue
        ribbon = ribbon_by_edge.get(snap.edge)
        if ribbon is None:
            # No drawn carriageway on the host edge, so no kerb to stand on.
            report.no_ribbon += 1
            continue

        registered = _register(spec, snap, ribbon, np.array([lamp.x, lamp.z]), report)
        if registered is None:
            report.over_shift += 1
            continue
        placed, side = registered

        # 🔴 **STAGE TWO, AND IT IS WHERE THE INVARIANT COMES FROM.** Clear of its
        # own host's kerb and still in the road, because the column landed inside
        # a *different* edge's ribbon — junction mouths and dual carriageways,
        # where several 1.6x ribbons overlap and the drawn city has no footway
        # left at all. `Q19`'s territory rather than this stage's, and **refused
        # rather than pushed again**: `signs.py` measured iterating the push and
        # it plateaus at 9.7% while taking the worst shift to 16.77 m, which is a
        # column on the wrong street.
        # ⚠️ **It runs on a post kept as surveyed too, and there it is provably
        # UNREACHABLE rather than merely unfired.** `signs.py` carries a comment
        # saying such a post "must" be checked, because standing clear of its own
        # kerb says nothing about an overlapping ribbon. True of a post this stage
        # *moved*; false of one it did not. An unmoved point re-snaps to the same
        # edge, and the kept branch's own condition
        # `abs(offset_m) > half_width + outset_m` already implies
        # `abs(offset_m) > half_width`. Measured over the region: **281 kept, 281
        # identical snaps, 0 refusals**, against **78** from the moved half, every
        # one on a *different* edge. Left running because the branch condition is
        # one edit from making it reachable — what is corrected here is the claim.
        settled = segments.nearest(float(placed[0]), float(placed[1]))
        settled_ribbon = ribbon_by_edge.get(settled.edge)
        if settled_ribbon is not None and abs(settled.offset_m) < settled_ribbon.half_width_at(
            settled.t
        ):
            report.in_carriageway += 1
            continue

        # ⚠️ **`settled_ribbon` where it exists, the host ribbon otherwise.** The
        # guard above only runs when there is a settled ribbon to compare against;
        # a column that settled onto an edge `surface.py` drew no carriageway for
        # is still drawn, and is graded against the kerb it was placed from.
        graded = settled_ribbon if settled_ribbon is not None else ribbon
        graded_t = settled.t if settled_ribbon is not None else snap.t
        graded_offset_m = abs(settled.offset_m if settled_ribbon is not None else snap.offset_m)
        placements.append(
            _Placed(
                kind=lamp.kind,
                x=float(placed[0]),
                z=float(placed[1]),
                y=snap.y,
                # 🔴 **`-side`, so the arm reaches over the carriageway** — the
                # derived direction, and the whole of what `Q62` cannot grade.
                # ⚠️ **`side`, not `snap.offset_m`**: the two disagree at `-0.0`,
                # which `Segments.nearest` really returns for a point on the
                # centreline (`-0.0 >= 0.0` is true and `-0.0 > 0.0` is false), so
                # the column would be placed on the nearside and reach away from
                # the road. `signs.py` records the same trap on a facing.
                arm=-side * nearside(snap.heading_deg),
                arm_reach_m=spec.arm_reach_m,
                kerb_offset_m=graded_offset_m,
                half_width_m=graded.half_width_at(graded_t),
            )
        )

    kept = _merge(placements, spec.merge_m, report)
    # 🔴 **One builder per kind, not one for the region** (`P5-3`). A kind is
    # drawn ONCE at the origin with its arm pointing north, and every column of
    # it is a stand at the bearing its arm was given — `_draw_lamp` reads the
    # arm and the reach off the post it is handed, so the library post carries
    # the north arm and the same reach.
    library: dict[str, ColouredBuilder] = {}
    reach_by_kind: dict[str, float] = {}
    stands: list[Placement] = []
    for post in kept:
        if post.kind not in library:
            library[post.kind] = ColouredBuilder(LAMPS_MATERIAL)
            reach_by_kind[post.kind] = post.arm_reach_m
            _draw_lamp(library[post.kind], spec, _library_post(post))
        # The library carries one reach per kind — see `_Placed.arm_reach_m`.
        if post.arm_reach_m != reach_by_kind[post.kind]:
            raise ValueError(
                f"{post.kind} reaches {post.arm_reach_m} m at ({post.x:.1f}, {post.z:.1f}) "
                f"and {reach_by_kind[post.kind]} m in the library"
            )
        stands.append(placement(post.kind, (post.x, post.y, post.z), bearing_deg(post.arm)))
        report.drawn += 1
        report.drawn_by_kind[post.kind] = report.drawn_by_kind.get(post.kind, 0) + 1
    # ⚠️ **Every declared kind gets a row, drawn or not.** A city that declares a
    # code its region does not carry should read 0 rather than be absent — an
    # absent key and a zero are the same JSON to a careless reader, and only one
    # of them says the selection was applied.
    for kind in spec.kinds:
        report.drawn_by_kind.setdefault(kind, 0)
    report.drawn_by_kind = dict(sorted(report.drawn_by_kind.items()))

    _measure_placement(report, kept)
    report.spacing_drawn_m = _spacing_m([(post.x, post.z) for post in kept])
    report.gaps_over_report_m = sum(1 for gap in report.spacing_drawn_m if gap > spec.gap_report_m)
    report.refused_by_kind = dict(sorted(report.refused_by_kind.items()))

    # A library mesh is named after the kind it draws — `LPO` — so a city
    # declaring two kinds ships two meshes and an artist replacing one replaces one.
    meshes: list[MeshData] = []
    for kind in sorted(library):
        built = library[kind].build(kind)
        if built is not None:
            meshes.append(built)
    by_name = {mesh.name: mesh for mesh in meshes}
    stands, report.placements_refused = refuse_unbuilt(stands, by_name)
    if meshes:
        # ⚠️ **`facing_away` is asked of every library mesh** and is not a
        # tautology of the stand: a rotation about `Y` preserves winding, so the
        # library's answer is the drawn city's — 25,116 inverted triangles would
        # still read here, as they did on the first build.
        report.facing_away = sum(facing_away(mesh) for mesh in meshes)
        report.library_meshes = len(meshes)
        report.library_triangles = sum(mesh.triangle_count for mesh in meshes)
        report.library_vertices = sum(len(mesh.positions) for mesh in meshes)
        report.placements = len(stands)
        report.triangles, report.vertices, report.aabb = drawn_totals(by_name, stands)
        # ⚠️ **Computed, not claimed**: every column stands exactly once.
        if report.placements + report.placements_refused != report.drawn:
            raise ValueError(
                f"{report.placements} placements and {report.placements_refused} refused "
                f"for {report.drawn} columns — a stand was dropped or doubled"
            )
        report.bytes = write_glb(out_dir / LAMPS_NAME, meshes)
        write_placements(out_dir / LAMPS_PLACEMENTS_NAME, city.id, region_id, LAMPS_NAME, stands)

    _write_manifest(out_dir, city, region_id, report)
    return report


def _register(
    spec: Lamps, snap: Snap, ribbon: Ribbon, published: np.ndarray, report: LampReport
) -> tuple[np.ndarray, float] | None:
    """Push a column out to the kerb the ribbon actually drew, or leave it, or refuse.

    ⚠️ **`Q60`'s move at a fourth layer**, after the railings, the signs and the
    signals, and for its reason: **64.1%** of this region's lamp posts are
    surveyed inside the drawn 1.6x ribbon, a median 1.46 m past the drawn kerb.

    🔴 **Clamped to one direction, `signs.py`'s shape since `Q78`.** The reason to
    move a column at all is that the carriageway floor draws the ribbon past the real
    carriageway, so a column on the real kerb lands in the drawn lane. That
    argument runs **outward only**. Assigning the target unconditionally also
    *pulls* the columns already standing clear back toward the road, and no
    counter can see it, because `shift_m` is an absolute value and an inward pull
    and an outward push are the same number. A column already clear keeps the
    point LandsD surveyed.

    ⚠️ **`railings.py` and `signals.py` deliberately do NOT do this** and
    `CLAUDE.md` says not to align them — a fence is a run and a conditional push
    would zigzag it. A lamp post is not a run.

    Returns the placed point and the kerb side, or `None` where `max_shift_m`
    refuses the move.
    """
    side, half_width_m, target_m, placed = ribbon.kerb_target(snap, spec.outset_m)

    if abs(snap.offset_m) > half_width_m + spec.outset_m:
        # ⚠️ **The published point, never a reconstruction** — see the foot note
        # below, which applies here with nothing to catch it.
        #
        # A real zero rather than a skipped append, so the identity over
        # `len(shift_m)` still closes; `posts_kept_as_surveyed` is how a reader
        # tells how many of the distribution's zeros are these.
        report.shift_m.append(0.0)
        report.posts_kept_as_surveyed += 1
        return published, side

    shift_m = abs(target_m - snap.offset_m)
    # Recorded **before** the refusal, so the distribution can read outside its
    # own bar (`Q58`); `over_shift` and `in_carriageway` are what let a reader
    # decompose `n`.
    report.shift_m.append(shift_m)
    if shift_m > spec.max_shift_m:
        return None

    # The foot-off-the-polyline trap, and the 10.6 m move it published as
    # 0.6 m, are recorded on `Ribbon.kerb_target`; here
    # `min_kerb_clearance_m` is what would catch it.
    return placed, side


def _merge(placements: list[_Placed], merge_m: float, report: LampReport) -> list[_Placed]:
    """Columns that registration pushed onto the same point, as one column.

    ⚠️ **Every fold here is a coincidence this stage MADE.** Unlike
    `signals._assemble` there is no surveyed clustering to reproduce: the layer
    publishes **zero** coincident pairs under 0.05 m, so a pre-registration
    grouping would be inventing a structure the data does not show. Two columns
    a metre apart on one edge are moved to the same offset and can land on each
    other; that is the only coincidence there is.

    Greedy and first-wins over a sorted input, which is what makes two builds of
    one input identical.
    """
    kept: list[_Placed] = []
    for post in placements:
        for other in kept:
            if math.hypot(other.x - post.x, other.z - post.z) <= merge_m:
                report.merged += 1
                break
        else:
            kept.append(post)
    return kept


# Where a library mesh is drawn: at the origin, arm to the north, so a stand is
# `bearing_deg(post.arm)` about `Y` and a move — the frame `gltf.placed_positions`
# and `GeneratedLandmarks.placement_of` both undo.
_LIBRARY_ARM = np.array([0.0, -1.0])
# The bracket arm's ring seed; the column's is its own arm (`_strut`).
_UP = np.array([0.0, 1.0, 0.0])


def _library_post(post: _Placed) -> _Placed:
    """`post`'s kind and reach at the origin with its arm north — the library's copy."""
    return replace(post, x=0.0, z=0.0, y=0.0, arm=_LIBRARY_ARM)


def _draw_lamp(builder: ColouredBuilder, spec: Lamps, post: _Placed) -> None:
    """One column, its bracket arm and the lantern hanging off the end of it.

    The arm slopes: it leaves the top of the column and arrives `arm_reach_m`
    out and `arm_drop_m` down, with the lantern centred on that far end. ⚠️ **A
    horizontal arm plus a separately-dropped lantern was the first shape and it
    is wrong** — it leaves the housing floating in the air below an arm that
    ends nowhere near it, which renders as a box hanging over the road with
    nothing holding it up.
    """
    base = np.array([post.x, post.y, post.z])
    top = base + np.array([0.0, spec.column_height_m, 0.0])
    forward = np.array([post.arm[0], 0.0, post.arm[1]])
    end = top + post.arm_reach_m * forward - np.array([0.0, spec.arm_drop_m, 0.0])

    # The column's ring turns with its arm — see `_strut`'s `seed`.
    _strut(builder, spec, base, top, spec.column_radius_m, cap_end=True, seed=forward)
    _strut(builder, spec, top, end, spec.arm_radius_m, cap_end=False, seed=_UP)
    _lantern(builder, spec, end, forward)


def _spacing_m(points: list[tuple[float, float]]) -> list[float]:
    """Nearest-neighbour distance for each point, in metres.

    🔴 **The instrument for this layer's own failure mode.** A lamp row's
    regularity is its content, so what refusing costs is a *rhythm*, and neither
    a count of refusals nor a count of survivors can see it. Published for the
    surveyed set and the drawn one both, because the **difference** is the
    finding: the region reads p50 16.74 m surveyed and 20.15 m drawn, with gaps
    over 40 m going from 5 to 16.

    ⚠️ **O(n^2), and it is MEMORY rather than time that sets the ceiling.**
    `signals._assemble` records the same arithmetic and the same decision, and
    quoting comparisons the way an earlier draft of this did understates it: the
    cost is three broadcast `n x n` float64 arrays. Measured — 1,263 points is
    **5.0 ms / 38 MB**, 3,000 is 28 ms / 216 MB, 10,000 is 0.31 s / **2.4 GB** and
    20,000 is 1.3 s / **9.6 GB**. It does not get slow, it dies. A uniform cell
    hash is the fix and is exact, and `tramway.py` and `kerbside.py` already ship
    that pattern; it is left because `read_lamps` pushes the region bbox into OGR,
    so only a territory-sized region reaches this at all.
    """
    if len(points) < 2:
        return []
    block = np.asarray(points, dtype=np.float64)
    spread = np.hypot(block[:, None, 0] - block[None, :, 0], block[:, None, 1] - block[None, :, 1])
    np.fill_diagonal(spread, np.inf)
    return [float(value) for value in spread.min(axis=1)]


def _measure_placement(report: LampReport, kept: list[_Placed]) -> None:
    """Grade the placement the stage just made, against the city it made it in.

    🔴 **`min_kerb_clearance_m` is the invariant and it is not a tautology.** The
    two-stage refusal in `build_region` guarantees every drawn column stands
    outside every drawn ribbon — but only if the arithmetic that placed it is
    right, and `signs.py` records the exact defect that would break it: a foot
    reconstructed from `offset_m` rather than read off the polyline puts a post
    5 m off the road and reports the move as 0.6 m. That drives this negative,
    where every partition still closes.

    🔴 **`lantern_overhang_m` is what ships INSTEAD of a counter over the arm
    direction.** The direction is derived from the kerb side, so an
    `arms_against_kerb` counter would read 0 by construction — `Q72`'s tautology,
    which certified the wrong state across a whole region because 0 was
    unreachable. This measures what the derivation did instead: how far each
    lantern hangs over the drawn carriageway.

    ⚠️ **It is degenerate over most of the layer, and that is expected rather
    than a defect in the instrument.** A column standing `outset_m` behind the
    kerb with an arm of `arm_reach_m` overhangs by exactly the difference, so p50
    and p90 are both 1.00 m. What it is for is the **tail**, where the edge the
    column settled against is not the one it was hosted to.

    ⚠️ **Every number here is read off the placement rather than re-snapped.** A
    grader that re-derives its own truth can disagree with the refusal that let
    the post through, and then neither says which is right (`Q56`).
    """
    if not kept:
        report.min_kerb_clearance_m = 0.0
        return
    for post in kept:
        lantern_offset_m = post.kerb_offset_m - post.arm_reach_m
        report.lantern_overhang_m.append(post.half_width_m - lantern_offset_m)
        if lantern_offset_m < 0.0:
            # Past the centreline, which is a lantern hanging over the opposing
            # traffic. ⚠️ **Reachable** — raising `arm_reach_m` gets there — which
            # is the test `Q72` says a counter has to pass before its 0 means
            # anything.
            report.lanterns_past_centreline += 1
    report.min_kerb_clearance_m = float(
        min(post.kerb_offset_m - post.half_width_m for post in kept)
    )


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: LampReport) -> int:
    document = {
        "schema_version": LAMPS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what `CITY_SCHEMA`
        # 11 was bumped over.
        "asset": LAMPS_NAME if report.triangles else None,
        "placements_document": LAMPS_PLACEMENTS_NAME if report.triangles else None,
        # The read, as three disjoint parts of `features`.
        "features": report.features,
        # ✅ The selection's refusals, over a domain the publisher **defines**.
        "not_a_lamp": report.not_a_lamp,
        "empty_geometry": report.empty_geometry,
        # ⚠️ **0 on this region and published anyway.** The six sheets overlap,
        # and a publisher that starts repeating a point across a cut would
        # otherwise draw two columns in one place with every counter agreeing.
        "duplicate_point": report.duplicate_point,
        "candidates": report.candidates,
        # The host and the registration, as disjoint parts of `candidates`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        "no_ribbon": report.no_ribbon,
        "over_shift": report.over_shift,
        # 🔴 Refused because registration could not get them out of the road — a
        # finding about `Q19`'s widening, not about this stage.
        "in_carriageway": report.in_carriageway,
        "merged": report.merged,
        # ⚠️ `Q78`'s branch: columns that kept the point LandsD surveyed because
        # they already stood clear. They append a real 0.0 to `shift_m`.
        "posts_kept_as_surveyed": report.posts_kept_as_surveyed,
        # ✅ **The whole published domain, both halves** — and unlike
        # `railings.json`'s refused metres and `signals.json`'s refused codes,
        # this one is checkable against the source rather than only reviewable.
        "drawn_by_kind": report.drawn_by_kind,
        "refused_by_kind": report.refused_by_kind,
        # ⚠️ **`n` exceeding `drawn` is the proof these read outside their own
        # bar** (`Q58`). 🔴 `shift_m` is an absolute value and **cannot** report
        # the direction of the move it measures (`Q78`) — the clamp in
        # `_register` is what makes the direction safe.
        "shift_m": report.measured(report.shift_m),
        # 🔴 **The invariant: no drawn column stands in a drawn carriageway.**
        # Must be >= 0, and it is not a tautology — see `_measure_placement`.
        "min_kerb_clearance_m": round(report.min_kerb_clearance_m, 4),
        # 🔴 **What the derived arm direction did**, published instead of a
        # counter over the direction itself, which would read 0 by construction
        # (`Q72`).
        "lantern_overhang_m": report.measured(report.lantern_overhang_m),
        # ⚠️ Must be 0, and raising `arm_reach_m` makes it non-zero.
        "lanterns_past_centreline": report.lanterns_past_centreline,
        # 🔴 The honest instrument for a refusal this stage cannot make: the
        # layer publishes no elevation, so a flyover lamp is drawn on the street
        # underneath. Report-only.
        "nearest_is_elevated": report.nearest_is_elevated,
        # 🔴 **This layer's own failure mode.** The *difference* between these two
        # is the finding — a lamp row's regularity is its content, so a refusal
        # costs a rhythm and neither a refusal count nor a survivor count sees it.
        "spacing_surveyed_m": report.measured(report.spacing_surveyed_m),
        "spacing_drawn_m": report.measured(report.spacing_drawn_m),
        "gaps_over_report_m": report.gaps_over_report_m,
        # ⚠️ **Must be 0.** `signs.gdshader` is `cull_back`, so winding decides
        # visibility and the normal attribute does not.
        "facing_away": report.facing_away,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
        "placements": report.placements,
        "placements_refused": report.placements_refused,
        "library_meshes": report.library_meshes,
        "library_triangles": report.library_triangles,
        "library_vertices": report.library_vertices,
    }
    return write_document(out_dir / LAMPS_MANIFEST_NAME, document)


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
        "lamps: %d features -> %d columns "
        "(%d not lamps, %d over shift, %d in carriageway, %d merged), "
        "%.2f m least kerb clearance, %d gaps over report, %d triangles, %d facing away",
        report.features,
        report.drawn,
        report.not_a_lamp,
        report.over_shift,
        report.in_carriageway,
        report.merged,
        report.min_kerb_clearance_m,
        report.gaps_over_report_m,
        report.triangles,
        report.facing_away,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
