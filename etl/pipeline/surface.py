"""Road graph to a drivable ribbon mesh (`P1-4`).

Reads the `roadgraph.json` that `P1-3` wrote and extrudes every edge into a
carriageway with kerbs, filling each junction with a cap so the surface is
continuous through it. Output is one vertex-coloured GLB for the whole region.

Three measurements off the emitted graph decide the shape of this:

- **Opposed carriageway pairs need no special handling.** Six pairs in Wan Chai
  sit 1.49-6.82 m apart, and at their authored widths five of the six already
  overlap. Applying the playability widening closes the sixth. The gap the
  `P1-3` hand-over worried about does not exist, so there is no pair detection
  here and no merging.
  ⚠️ True of the *carriageway*, and it was read as true of the whole ribbon for
  too long. The kerbs overlap as well, and a kerb inside a neighbour's road is a
  0.15 m concrete strip lying across a lane — 33 km of it, reported from the
  driver's seat as a white line that threw the car. `_hide_buried_kerbs` stops
  drawing those. Still no merging: the ribbons are untouched and only the kerb
  asks what its neighbours are doing.
- **A node may not be capped across elevation levels.** Capping across a grade
  separation would weld a street to a tunnel roof with a 60-degree wall, so caps
  are built per level. The measurement that first showed this was that all 36
  nodes where two levels meet stepped by exactly a deck height, because
  `elevation_levels` was a constant offset per level and nothing ramped.
  ⚠️ `P2-7` closed most of that: 26 of the 36 now step under 0.5 m, and the rule
  survives on the other six — the five tunnel portals still step 8 m, and a
  portal is a void no height source repairs. Per-level capping is therefore
  still right, but it is no longer right *everywhere*, and `P4-*` reopening the
  elevated network is where that distinction will start to matter. See `Q13`.
- **Mitred joints are safe.** The sharpest interior turn in the region is 91.8
  degrees, a mitre scale of 1.44. The limit below is a guard for another city,
  not something this data reaches.

Nothing here reads the road network source. The graph is the input, which is
what lets this stage run in a second without touching the geodatabase.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np

from pipeline.config import (
    BOTH,
    FORWARD,
    KERB_DOUBLE,
    KERB_SINGLE,
    CityConfig,
    RoadSurface,
    load_city,
)
from pipeline.documents import round_position, write_document
from pipeline.geometry import edge_distances, inside_polygon
from pipeline.gltf import Bounds, MeshData, normalise, write_glb
from pipeline.kerbside import NEARSIDE, OFFSIDE
from pipeline.mesh import select_triangles
from pipeline.polyline import plan_lengths, plan_steps
from pipeline.roads import ROADGRAPH_NAME, read_graph

# ⚠️ **The barycentric point-in-triangle test is `terrain`'s, not a fourth copy.**
# `deck_error.py` books its own copy as a known cost — importing the pipeline
# would drag GDAL into a hand-run tool — and that argument does not reach here:
# `pipeline.terrain` imports numpy and `pipeline.gltf` alone, and `pipeline.roads`
# above already pulls it in. `Q58`'s rule is that a third copy should force it.
from pipeline.terrain import _hits

if TYPE_CHECKING:  # pragma: no cover - imported for the annotation alone
    # ⚠️ **Guarded, not imported.** `pipeline.fares` reads sources, so importing
    # it here would drag a source fetcher into every consumer of the ribbon —
    # and `DrawnSurface` uses exactly one method of it. The annotation is still
    # exact, which `Any` was not.
    from pipeline.polyline import Segments

log = logging.getLogger(__name__)

SURFACE_NAME = "roads.glb"
SURFACE_MANIFEST_NAME = "roadsurface.json"
# 3 since `Q23`: `carriageway[].half_width_m` is a **list**, one value per
# station of that edge's published polyline, where it used to be one number for
# the whole edge. A reader that keeps the old interpretation gets a list where
# it wanted a float, which is the loud half — the quiet half is that a reader
# taking `[0]` would be right on 769 of 797 edges and 0.96 m out on the rest.
# 4 since `Q51`: `carriageway[].trim_m` says how far back each end of the ribbon
# was held for its junction cap. Only this stage knows it, and `clearance.py`
# cannot judge a cross-section without it — the nominal corridor still has a
# width where the ribbon stops, and reading that as a starved one is exactly the
# trap that condemned 18 innocent edges in `Q19`.
# 5 since `P3-19`: `carriageway[].kerb_hidden_m` says where each side of the
# ribbon draws **no kerb**, because a neighbouring ribbon or cap already covers
# it. Only this stage knows it — `_hide_buried_kerbs` decides it per quad and
# the answer depends on every other ribbon in the region — and `railings.py`
# cannot place a fence without it: 11.1% of the region's railing metres join to
# a kerb that is buried under the opposing carriageway, where a fence drawn on
# the drawn kerb stands in the middle of merged tarmac. Intermediate, like
# `trim_m`; the game reads neither.
# 6 since `Q92`: `caps` publishes each junction cap's hull ring, in x/y/z, so a
# marking stage can ask **how high the road it is painting on actually is**.
# Only this stage knows it — the ring is the convex hull of every arriving
# ribbon's end corners, and `_Builder.fan` interpolates it from the ring's own
# centroid — and until now the markings guessed instead: `blended_height` blended
# level-0 *centreline* heights, which is a different function, and **23.2% of
# `boxjunctions.glb` shipped below the road it is painted on**. A reader that
# keeps the old interpretation gets no caps at all and rebuilds that defect
# silently, which is the case hard rule 5 exists for. An intermediate like every
# field above it; the game reads none of them.
SURFACE_MANIFEST_SCHEMA = 6

# Godot's glTF importer reads node-name suffixes: `-col` gives the mesh a static
# trimesh collider at import time and leaves it visible. Naming it here rather
# than building the shape in GDScript at load makes the collision part of the
# asset, which is what `P1-4` is asked to deliver.
SURFACE_MESH_NAME = "road_surface-col"

# The glTF material name, and the name is the contract: glTF cannot say "use
# this shader", so `tools/generated_scene_import.gd` dispatches on it and hands
# the surface `tuning/road_markings.tres`. The same channel `FACADE_MATERIAL`
# uses, and it fails the same way — silently, in the engine, where only
# `verify_road_surface.gd` can see it.
SURFACE_MATERIAL = "road_markings"

# --------------------------------------------------------------------------
# The `TEXCOORD_1` marking codec (`P3-12`).
#
# ⚠️ **Contract, not tuning.** These multipliers are mirrored in
# `assets/shaders/road_markings.gdshader` (`MARKING_*`) and in
# `tools/verify_road_surface.gd`, and `docs/ARCHITECTURE.md` is the tiebreak.
# They do not belong in the city yaml: a codec has no per-city meaning.
#
# The layout follows `buildings.facade_state` exactly, for the same reasons —
# one non-negative integer per vertex, every field's 0 meaning "absent", and the
# whole code exact in float32 so a consumer can decode it with `floor(x + 0.5)`.
#
#   code = surface_class + 4*lanes + 64*direction + 256*bus_lane + 512*tram
#        + 1024*offside_kerb + 2048*centre + 131072*kerb_near + 524288*kerb_off
#
# Max legal code is 2,097,151, still far inside float32's 24 exact bits.
#
# `surface_class` is the field the shader cannot do without. The kerbs run off
# *both* ends of the lane range — the nearside lip spans U in [-outside, 0] and
# the offside riser and lip sit at [lanes, lanes + outside] — so `fract(U)`
# alone would paint a lane line down a kerb. `lanes` is the second: a fragment
# at U = 3.0 is the offside kerb on a three-lane road and an interior lane
# boundary on a four-lane one, and nothing in `TEXCOORD_0` separates them.
#
# `TEXCOORD_1.y` is the **drawn length of this edge** in metres, constant across
# it, and 0.0 on a junction cap. The shader wants distance to the nearer end —
# to fade markings out on a junction approach — and gets it as
# `min(V, length - V)` per *fragment*.
#
# ⚠️ **Writing that distance per vertex instead is wrong, and it looks right.**
# Distance-to-nearer-end is a V with its kink at the midpoint, and a strip is
# interpolated linearly between its stations: on an edge Douglas-Peucker left
# with two, both stations *are* ends, both read 0, and the whole street
# interpolates to 0 — every marking on it faded out as though it were all
# junction. **204 of this region's 797 edges carry two stations**, so it is the
# common case rather than a corner. The length is constant, so it survives any
# station spacing.
MARKING_CLASS_CARRIAGEWAY = 0
MARKING_CLASS_KERB = 1
MARKING_CLASS_CAP = 2
MARKING_LANES = 4
MARKING_DIRECTION = 64
MARKING_BUS_LANE = 256
MARKING_TRAM = 512
# Set where the **offside** boundary of this edge is a real kerb rather than the
# middle of a road. 0 is "not known to be", which is the conservative reading and
# the one a consumer should draw nothing on: `U = lanes` is a kerb on an ordinary
# street and the centre of a dual carriageway drawn as an opposed pair, and a
# kerbside marking put down the middle of a road is the loudest way to be wrong.
# Answered by `_hide_buried_kerbs`, which already has to decide it.
MARKING_OFFSIDE_KERB = 1024
# Where the two flows of an opposed pair meet, in **sixteenths of a lane beyond
# the edge's own centreline**, `k - 1` steps, with 0 meaning "this edge is not
# half of a merged pair". Six bits, so it reaches 3.94 lanes at 0.2 m resolution
# on this region's 3.2 m lane.
#
# It has to be published rather than derived: the two ribbons overlap, so the
# line belongs midway between the two *centrelines*, and an edge's own lane
# coordinate cannot see where its partner runs.
MARKING_CENTRE = 2048
MARKING_CENTRE_MAX = 63
# What kind of kerbside line each side of this edge carries (`P3-13`, `Q54`).
# Two bits each, and the vocabulary is the same on both: `KERB_ABSENT` for a
# surface that says nothing, `KERB_NONE` for a kerb the source was consulted
# about and does not restrict, then the two lines it can carry.
#
# ⚠️ **The codec says what kind of line; `COLOR_0.a` says where it applies.**
# The kind is constant per edge side and the *extent* is not — 87% of covered
# sides carry one contiguous run and the rest carry two or more — so the two
# halves ride in different channels. Putting the extent here as well would mean
# one code per run, and a code is `flat` across a whole strip.
#
# ⚠️ **`ABSENT` and `NONE` draw the same thing and mean different
# things.** A city whose sources carry no no-stopping layer publishes `ABSENT`
# everywhere and gets no kerbside lines, which is the honest answer rather than
# `P3-12`'s invented one. `NONE` is a positive statement, and `P3-3`'s traffic
# will want it — a kerb known to be unrestricted is where a car may pull over.
MARKING_KERB_NEAR = 131072
MARKING_KERB_OFF = 524288
MARKING_KERB_SPAN = 4
MARKING_KERB_ABSENT = 0
MARKING_KERB_NONE = 1
MARKING_KERB_SINGLE = 2
MARKING_KERB_DOUBLE = 3
# The pipeline's kerbside vocabulary as the codec spells it. Keyed on the names
# `config.py` validates against rather than on literals, for the reason
# `MARKING_DIRECTIONS` gives: the stage that acts on a vocabulary must not drift
# from the set that is accepted.
MARKING_KERB_KINDS = {KERB_SINGLE: MARKING_KERB_SINGLE, KERB_DOUBLE: MARKING_KERB_DOUBLE}
# Derived rather than written down: adding a field means moving one line, not
# remembering to move two. `kerb_off` is the top field and holds two bits.
MARKING_CODE_MAX = MARKING_KERB_OFF * MARKING_KERB_SPAN - 1
# The widest lane count the codec can say, from the field above it. `lanes = 16`
# packs to 64 and collides with `direction` while leaving the *total* under the
# ceiling — so the ceiling is not the guard, this is.
MARKING_LANES_MAX = MARKING_DIRECTION // MARKING_LANES - 1

# `direction` as the codec spells it, keyed by the vocabulary `config.py`
# validates against rather than by literals — that module names them "next to
# the validation, so the stage that acts on them cannot drift from the set that
# is accepted", and this is that stage. 0 is kept free so an unrecognised value
# degrades to "absent" rather than to a wrong marking.
MARKING_DIRECTIONS = {BOTH: 1, FORWARD: 2}

# Ceiling on how far a mitred outside corner may be pushed from the centreline,
# as a multiple of the half-width. A degeneracy guard, not a tuning value: it
# only binds past a 151-degree turn, and the sharpest in this region is 92.
_MITRE_LIMIT = 4.0

# Below this, two consecutive polyline vertices are the same point and the
# segment between them has no direction to offset along.
_MIN_SEGMENT_M = 1e-6

# How far a movement may deviate from straight and still be mitred through its
# junction cap, in degrees. Two limits because the corner between two arms means
# two different things: with only two arms the node is one street bending and the
# corner is carriageway, while with three or more a sharp corner is the pavement
# between two streets and filling it would pave the footpath.
_BEND_TURN_DEG = 90.0
_THROUGH_TURN_DEG = 45.0

# Side of the grid cell that narrows the overlap search from every-pair to
# every-neighbour, in metres. Comfortably wider than the widest carriageway in
# the region, so a ribbon lands in a handful of cells rather than in one each.
_OVERLAP_CELL_M = 60.0

# Half the gap between the two stations `P3-13` inserts at each end of a
# restriction, in metres. Not a tuning value: it is how sharply `COLOR_0.a` can
# turn on, and 0.5 m of ramp is under the width of the line it ends.
#
# It is also the floor on how close an inserted station may come to one the
# polyline already has, which is what keeps the extra quads out of
# `_MIN_TWICE_AREA_M2`'s way.
_KERB_STATION_M = 0.25

# Below this, a triangle has collapsed and is dropped. Compared against *twice*
# the area, which is what the cross product's length gives — a square millimetre
# of road is not road, and a collision shape built from degenerate triangles is
# a collision shape with holes in it.
_MIN_TWICE_AREA_M2 = 1e-6

# Plan grid `DrawnSurface` bins junction caps into. A cap is a junction's worth
# of tarmac — tens of metres across at the interchange, a few in a back lane —
# so this is sized to the *small* end: an oversized cell puts every cap in the
# region's centre cell and turns the point query back into a linear scan, while
# an undersized one only costs a few more dictionary entries. Its own constant
# rather than `deck_error`'s 8 m, because that grid indexes triangles and this
# one indexes whole caps.
_CAP_CELL_M = 16.0

# Column of `_Edge.points` carrying that station's half-width in metres, beside
# the x/y/z it is measured at.
#
# Carried *with* the geometry rather than in an array beside it, because `Q23`
# makes the width vary along an edge and both `dedupe` and `trim` change which
# stations exist: one drops them, the other interpolates two new ones at the
# cuts. A parallel array has to be put through both by hand and stays right
# until someone adds a third operation. As a column it simply travels — `_at`
# interpolates every column it is handed, so a trimmed end gets the correct
# width without this module saying anything about it.
_WIDTH = 3

# Column of `_Edge.points` marking the stations `_add_kerb_stations` inserted,
# 1.0 where it did and 0.0 where the polyline already had one.
#
# A column for the same reason `_WIDTH` is one, and the reason bites harder
# here: `trim` interpolates two new stations at the cuts and `dedupe` drops
# stations, and this has to survive both to be worth anything. As a column it
# travels.
#
# ⚠️ **Read it as `== 1.0`, not as truthy.** `_at` lerps every column, so a trim
# cut landing between an original station and an inserted one arrives carrying a
# *fraction* — 316 of this region's ribbons start or end on one. That station is
# neither original nor inserted: it is a ribbon end, it is pinned regardless of
# what this column says, and counting it as inserted would overstate `P3-13`'s
# residue by a quarter. Only the two cuts can be fractional, so every interior
# station is exactly 0.0 or 1.0 and the equality is doing no float work.
_INSERTED = 4

# How far a station may sit off the line between its neighbours and still be
# dropped from a kerb rail, in metres. 0.1 mm: a hair over float noise on
# coordinates of this magnitude, and it is a *crack* threshold rather than a
# visual one — what a dropped station moves is the kerb away from the
# carriageway it is welded to, and the pair are the same surface.
#
# ⚠️ It is a guard, not the claim, and it is load-bearing: a quarter of the
# candidates fail it, by far enough to matter. `_off_line` has the mechanism and
# the numbers; `kerb_rail_offset_m` reports the worst deviation actually taken.
_STRAIGHT_M = 1e-4


@dataclass
class SurfaceReport:
    edges: int = 0
    # Drawn half-width per graph edge id, in metres, **one value per station of
    # that edge's published polyline**. Recorded rather than recomputed
    # downstream: `_prepare` is the one place the widening is applied, and a
    # second evaluation of `drawn_width_m` is a second thing to keep in step with
    # the config.
    carriageway: dict[int, list[float]] = field(default_factory=dict)
    # Metres held back from each end of an edge's ribbon so a junction cap can
    # fill the middle, keyed by graph edge id as `(start, end)`. Recorded for the
    # same reason as `carriageway`: `_assign_trims` is the one place the trim is
    # decided, and a downstream re-derivation would be a second thing to keep in
    # step with the junction rule.
    trims_m: dict[int, tuple[float, float]] = field(default_factory=dict)
    # Every junction cap's hull ring, as `(level, (k, 3) x/y/z)` (`Q92`).
    # Recorded for the reason `_record_hidden_kerbs` gives about coverage: the
    # ring depends on where *every* arriving ribbon ended, trims and clamps
    # included, so a second derivation in a marking stage would disagree near
    # the caps and tell nobody which answer was right.
    cap_rings: list[tuple[int, np.ndarray]] = field(default_factory=list)
    junctions: int = 0
    # Edge **ends** that resolved to half of an opposed one-way pair — two per
    # pair, because each half publishes its own offset. Reported because it is
    # the population two markings depend on and neither the graph nor the ribbon
    # states it: a detection that stopped matching would put a centre line back
    # on nothing, silently.
    opposed_pair_ends: int = 0
    # Ends that were detected and then could not be said. Counted separately
    # rather than folded into the line above, because the two failures want
    # different fixes — nothing detected is a pairing problem, detected and
    # unpublishable is a range problem — and one number cannot tell them apart.
    opposed_pairs_unpublishable: int = 0
    # Movements that qualified as running through a node and had their mitre fed
    # into its cap. Reported so a predicate that stopped matching would show.
    #
    # ⚠️ **Not** a count of caps this changed. A straight-through movement
    # qualifies, and its apex lands on the boundary the hull already had — so a
    # region of pure crossroads reports a number here and draws exactly what it
    # drew before. Saying how many caps actually grew would mean hulling twice.
    through_movements: int = 0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: Bounds | None = None
    # Ends held back from a node so a cap can fill the middle, and how many of
    # those hit the length ceiling instead of the junction radius. A high clamp
    # count means the trim factor is wide for the region's block size.
    trimmed_ends: int = 0
    clamped_trims: int = 0
    # The vertical step at each node where the graph changes elevation level.
    # Reported every run because it is the one thing about this output that is
    # not drivable, and it is inherited rather than introduced.
    #
    # Kept as the whole distribution rather than a running maximum since
    # `P2-7`: the maximum is now the five tunnel portals, which are a void and
    # will never close, and quoting it alone would report a stage that closed 26
    # of these 36 as one that closed none.
    level_steps_m: list[float] = field(default_factory=list)
    # Metres of kerb line dropped because a neighbouring carriageway had already
    # covered it. Reported every run because it is a *large* number against a
    # region's total kerb, and a collapse in it would mean the overlap test had
    # stopped finding anything rather than that the region had tidied itself up.
    buried_kerb_m: float = 0.0
    # Per edge and side, the ribbon-metre ranges where the kerb is not drawn —
    # `buried_kerb_m`'s own decision, kept rather than only summed, because
    # `P3-19` has to know *where*. Ribbon metres, so zero is the trimmed start
    # and a consumer subtracts `trim_m[0]` from a published-polyline distance.
    kerb_hidden_m: dict[int, dict[str, list[list[float]]]] = field(default_factory=dict)
    # Triangles left facing downward, and the area they cover. Tracked rather
    # than assumed away: `boundary` removes all but a handful at the region's
    # sharpest hairpin, and a jump in either number means a ribbon has started
    # folding somewhere new.
    inverted: int = 0
    inverted_area_m2: float = 0.0
    # `Q23`'s own number: metres of **level-0** centreline the graph reports as
    # resting on structure, and which this stage therefore draws at its authored
    # width instead of widening. 1,070 m of it when the question was raised, all
    # of it widened. Reported here so the acceptance figure comes off the stage
    # that acted on it rather than only off `tools/overhang.py`.
    on_structure_m: float = 0.0
    # `P3-13`'s cost and `P3-13`'s known error.
    #
    # ⚠️ `kerb_stations` is **stations, not vertices**: a station lands on the
    # carriageway strip and on every kerb strip beside it that keeps it, so
    # Wan Chai's 1,179 cost 4,252 vertices rather than 2,358.
    #
    # `kerb_rail_stations` is how many the kerb rails still carry — 390 of the
    # 1,179 — and `_rail_stations` has the argument for why that is not zero.
    # `kerb_rail_offset_m` is the worst distance any *dropped* station sat off
    # the line it was dropped onto, against `_STRAIGHT_M`'s bar.
    #
    # `kerb_minority_m` is metres drawn as the wrong *kind* of line, because the
    # codec says one kind per edge side and the source does not promise one; see
    # `_kerbside`.
    kerb_stations: int = 0
    kerb_rail_stations: int = 0
    kerb_rail_offset_m: float = 0.0
    kerb_minority_m: float = 0.0

    @property
    def level_changes(self) -> int:
        return len(self.level_steps_m)

    @property
    def max_level_step_m(self) -> float:
        return max(self.level_steps_m, default=0.0)


# --------------------------------------------------------------------------
# Ribbon geometry
# --------------------------------------------------------------------------


def dedupe(points: np.ndarray) -> np.ndarray:
    """Drop vertices that repeat the previous one in plan.

    A repeated vertex has no direction, so it produces a zero normal and takes
    the whole ribbon with it. Legal in the graph — clipping can land a cut
    exactly on an existing vertex.
    """
    if len(points) < 2:
        return points
    return points[np.concatenate([[True], plan_steps(points) > _MIN_SEGMENT_M])]


def trim(points: np.ndarray, start_m: float, end_m: float) -> np.ndarray:
    """The polyline with `start_m` cut off the front and `end_m` off the back.

    Cut points are interpolated, including in Y, so a trimmed ramp keeps its
    gradient. Returns fewer than two vertices if the trims meet, which the
    caller treats as an edge too short to draw.
    """
    along = plan_lengths(points)
    low, high = start_m, along[-1] - end_m
    if high - low <= _MIN_SEGMENT_M:
        return points[:0]

    inner = points[(along > low) & (along < high)]
    return np.vstack([_at(points, along, low), inner, _at(points, along, high)])


def _at(points: np.ndarray, along: np.ndarray, distance: float) -> np.ndarray:
    """The point a given distance along the polyline, as a (1, N) row.

    Every column, not the first three. The fourth is the station's half-width
    (`_WIDTH`), and a trim that interpolated x/y/z but carried a neighbour's
    width would put a step in the carriageway edge exactly where a ribbon meets
    its junction cap — the one place a step is invisible in a wireframe and
    obvious from the driver's seat.
    """
    return np.array([[np.interp(distance, along, column) for column in points.T]])


def mitres(points: np.ndarray) -> np.ndarray:
    """Per-vertex offset vector in plan, one half-width to the **left** of travel.

    Interior vertices get the mitre — the intersection of the two neighbouring
    offset lines — so consecutive quads share an edge exactly and the ribbon has
    no notch on the outside of a bend. Its length exceeds one where the road
    turns, by `1 / cos(half the turn)`, which is what makes the joint close.
    """
    direction = normalise(np.diff(points[:, [0, 2]], axis=0))
    # Left of travel, which in a Y-up right-handed frame is `up x forward`: for
    # travel along +X that is -Z. Not a free convention — `TEXCOORD_0` is a lane
    # coordinate measured from the nearside kerb, and Hong Kong drives on the
    # left, so getting this backwards mirrors every asymmetric road marking.
    normal = np.column_stack([direction[:, 1], -direction[:, 0]])

    offsets = np.empty((len(points), 2))
    offsets[0], offsets[-1] = normal[0], normal[-1]
    if len(points) > 2:
        bisector = normal[:-1] + normal[1:]
        length = np.hypot(*bisector.T)
        # A zero bisector is a 180-degree reversal, which has no mitre. Keeping
        # the incoming normal folds the ribbon back on itself rather than
        # sending the corner to infinity.
        reversal = length <= _MIN_SEGMENT_M
        unit = bisector / np.where(reversal, 1.0, length)[:, None]
        bisector = np.where(reversal[:, None], normal[:-1], unit)
        cosine = (bisector * normal[:-1]).sum(axis=1)
        offsets[1:-1] = bisector * (1.0 / np.clip(cosine, 1.0 / _MITRE_LIMIT, 1.0))[:, None]
    return offsets


def boundary(points: np.ndarray, offsets: np.ndarray, across_m: np.ndarray | float) -> np.ndarray:
    """One side of the ribbon in plan, stopped where it would run backwards.

    A corner tighter than the road is wide has no offset curve on its inside:
    the naive one crosses over itself, which renders as an inverted sliver and
    leaves a notch in the collider. The region has such corners — a slip road
    off Hung Hing Road loops at a 5 m radius, and the widened carriageway is
    10.2 m across.

    Holding the inner boundary still while the outer sweeps past is what the
    offset of a too-tight corner actually is, and it is the only repair here
    that touches neither the centreline nor the width: capping the width
    instead pinches the carriageway to nothing at 24 places in the region, and
    dropping the offending vertices cuts up to 17 m off that same loop.
    """
    rail = points[:, [0, 2]] + offsets * np.reshape(across_m, (-1, 1))
    step = np.diff(points[:, [0, 2]], axis=0)
    # Vectorised first because it is almost always clean: 74 of 797 edges have
    # a corner tight enough to need the walk below.
    if not ((np.diff(rail, axis=0) * step).sum(axis=1) <= 0.0).any():
        return rail

    rail = rail.copy()
    for index in range(len(rail) - 1):
        if np.dot(rail[index + 1] - rail[index], step[index]) <= 0.0:
            rail[index + 1] = rail[index]
    return rail


def _lift(plan: np.ndarray, points: np.ndarray, lift_m: float) -> np.ndarray:
    """A plan boundary put back on the ribbon's own heights."""
    return np.column_stack([plan[:, 0], points[:, 1] + lift_m, plan[:, 1]])


def _off_line(rail: np.ndarray) -> np.ndarray:
    """How far each station sits off the line between its two neighbours.

    Ends are infinite: a rail's first and last station have no pair to be
    between, and dropping either would shorten the rail. So is a station whose
    neighbours coincide — there is no line to be on.

    This is what makes the kerb thinning provable rather than assumed, and
    **the measurement is not a formality — it refuses 252 of Wan Chai's 1,041
    candidates.** In plan the algebra is exact: `_insert_stations` puts its
    stations *on* the polyline, and `mitres` puts each interior vertex on the
    intersection of the two neighbouring offset lines, so an interpolated
    station's boundary point lands on the straight offset line between its
    neighbours' — even under `Q23`'s varying half-width, since a linearly
    varying offset of a straight segment is still straight.

    ⚠️ **It is height that does not follow, and the reason is the mitre itself.**
    A mitred vertex is displaced *along* the segment as well as across it — that
    displacement is what closes the joint — so the rail's chord between two
    mitred neighbours spans a different stretch of the segment than the
    centreline does. Height is interpolated along the centreline. The two
    parameterisations therefore disagree, and an inserted station carries the
    difference: up to **87 mm** in this region, 12 mm at p99, against 0.16 mm of
    plan deviation outside the corners `boundary` had to hold still. Dropping
    such a station would leave the kerb at a height its own carriageway is not
    at — a step between two surfaces that are welded everywhere else, on a mesh
    that ships as one trimesh collider. So it is kept.
    """
    offset = np.full(len(rail), np.inf)
    if len(rail) < 3:
        return offset
    before, here, after = rail[:-2], rail[1:-1], rail[2:]
    span = after - before
    reach = here - before
    length_sq = (span * span).sum(axis=1)
    # ⚠️ Squared, so the bar is `_MIN_SEGMENT_M` **squared** — against the raw
    # constant this would be a 1 mm coincidence radius rather than a micron.
    # Named once and used for both the divide and the fallback: the `inf` is
    # only correct while the two ask the same question, and writing the
    # predicate twice is how that quietly stops being true.
    spans = length_sq > _MIN_SEGMENT_M**2
    along = np.divide((reach * span).sum(axis=1), length_sq, out=np.zeros(len(span)), where=spans)
    perpendicular = np.linalg.norm(reach - along[:, None] * span, axis=1)
    offset[1:-1] = np.where(spans, perpendicular, np.inf)
    return offset


# --------------------------------------------------------------------------
# Mesh assembly
# --------------------------------------------------------------------------


class _Marking(NamedTuple):
    """One piece of surface's `TEXCOORD_1`, constant across it.

    A pair rather than two parameters because it is one channel: `strip` already
    takes `across` as a pair for the same reason, and splitting a payload across
    the signature is how the two halves come to disagree.
    """

    code: float
    length_m: float

    def broadcast(self, count: int) -> np.ndarray:
        """One row per vertex, as a read-only view rather than a copy.

        `_rgba`'s trick, for `_rgba`'s reason — the value is constant across the
        piece, and `_Builder.build` materialises it in the one `vstack` that
        needs it. `buildings.facade_uv2` does the same for the tiles' channel.
        """
        return np.broadcast_to(np.array(self, dtype=np.float32), (count, 2))


class _Builder:
    """Accumulates triangle strips and fans into one vertex-coloured mesh.

    Vertices are shared along a strip and never between strips. That is what
    keeps the road smooth along its length and hard-edged where the carriageway
    meets the kerb riser — the same flat-shaded treatment the buildings get,
    applied where it means something.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._colours: list[np.ndarray] = []
        self._uvs: list[np.ndarray] = []
        self._uv2: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def strip(
        self,
        left: np.ndarray,
        right: np.ndarray,
        *,
        colour: tuple[int, int, int],
        along: np.ndarray,
        across: tuple[float, float],
        marking: _Marking,
        alpha: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> None:
        """A quad strip between two rails, wound so its face points out of it.

        `across` is the pair of U coordinates for the two rails, in lane widths;
        `along` is V, in metres. `docs/ART_DESIGN.md` puts lane markings in a
        shader driven by these rather than in a texture atlas, so U is a lane
        coordinate — an integer U is a lane boundary whatever the widening did
        to the metres.

        `marking` is `TEXCOORD_1`, which is what makes those readable — see the
        codec constants at the top of this module, including why it carries a
        length rather than the distance the consumer actually wants.

        `alpha` is one byte per station of each rail, in the order the rails are
        given, and it is `COLOR_0.a` — where `P3-13` writes how far along the
        edge a kerbside restriction runs. Optional because most strips have
        nothing to say there and an opaque road is what alpha meant before.

        ⚠️ **The channel is per rail, and that is the whole reason it fits.**
        The two kerbs of a road are the two rails of this strip, so a value that
        varies across the carriageway *is* a value per side — no second
        attribute, and no bytes the mesh was not already carrying.
        """
        span = len(left)
        if span < 2:
            return

        base = self._count
        index = np.arange(span - 1)
        self._triangles.append(
            np.concatenate(
                [
                    np.column_stack([index, index + 1, index + span]),
                    np.column_stack([index + 1, index + span + 1, index + span]),
                ]
            )
            + base
        )
        # One facing for the whole strip width: the two rails differ only by the
        # mitre, and a strip is a flat piece of road, kerb face or lip.
        facing = _rail_normals(left, right)
        self._positions.append(np.vstack([left, right]))
        self._normals.append(np.vstack([facing, facing]))
        self._colours.append(
            _rgba(colour, 2 * span, np.concatenate(alpha) if alpha is not None else None)
        )
        self._uvs.append(
            np.column_stack([np.repeat(across, span), np.concatenate([along, along])]).astype(
                np.float32
            )
        )
        self._uv2.append(marking.broadcast(2 * span))
        self._count += 2 * span

    def fan(self, ring: np.ndarray, *, colour: tuple[int, int, int], marking: _Marking) -> None:
        """A convex polygon as a fan from its centroid, facing up."""
        if len(ring) < 3:
            return
        if _shoelace(ring) > 0.0:
            ring = ring[::-1]

        base = self._count
        index = np.arange(len(ring))
        self._triangles.append(
            np.column_stack(
                [
                    np.full(len(ring), base + len(ring)),
                    index + base,
                    (index + 1) % len(ring) + base,
                ]
            )
        )
        self._positions.append(np.vstack([ring, ring.mean(axis=0)]))
        self._normals.append(np.tile([0.0, 1.0, 0.0], (len(ring) + 1, 1)))
        self._colours.append(_rgba(colour, len(ring) + 1))
        # A junction is not a length of lane, so it carries no marking
        # coordinate. Box junctions come from a mask keyed on the node, not
        # from these — see `docs/ART_DESIGN.md`.
        self._uvs.append(np.zeros((len(ring) + 1, 2), dtype=np.float32))
        # ⚠️ Which is why `TEXCOORD_1` exists rather than the consumer reading
        # the zeros above as "cap": U = 0 *is* the nearside kerb line, so a
        # kerbside double yellow drawn as `U < eps` would flood every junction.
        # `(0, 0)` is an in-range value here, not a sentinel. What the cap
        # carries in `TEXCOORD_1` is the caller's to say.
        self._uv2.append(marking.broadcast(len(ring) + 1))
        self._count += len(ring) + 1

    def build(self, name: str) -> MeshData:
        """The accumulated geometry, minus the triangles that collapsed.

        A boundary held still at a tight corner leaves a quad with two corners
        in the same place. It draws as nothing and it has no normal, so it is
        dropped here rather than shipped into a collision shape.
        """
        if not self._triangles:
            raise ValueError(f"'{name}': nothing to write — the graph produced no ribbon")
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.vstack(self._normals).astype(np.float32),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            colours=np.vstack(self._colours),
            uvs=np.vstack(self._uvs),
            uv2=np.vstack(self._uv2),
            material=SURFACE_MATERIAL,
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        kept = select_triangles(mesh, twice_area > _MIN_TWICE_AREA_M2)
        if kept is None:
            raise ValueError(f"'{name}': every triangle collapsed")
        return kept


class DrawnHeight(NamedTuple):
    """One `DrawnSurface` query: the height drawn, and the two parts of it.

    `cap_m` is `None` where no junction cap covers the point, which is how a
    caller tells whether the caps were read at all — the counter that would
    notice `roadsurface.json` silently losing them (`Q92`).
    """

    height_m: float
    ribbon_m: float
    cap_m: float | None


@dataclass(frozen=True)
class DrawnSurface:
    """How high the road this stage drew stands, at any plan position (`Q92`).

    🔴 **This exists because the markings were guessing, and 23.2% of the yellow
    box junctions shipped under the asphalt.** `boxjunctions.blended_height`
    gives a vertex a distance-weighted blend of level-0 *centreline* heights;
    what is drawn at a junction is a convex-hull cap fanned from the ring's own
    centroid. They are different functions and they diverge off the centreline —
    the drawn surface stands up to **0.218 m** above the blend, against a
    `lift_m` of 0.012 — so the paint sank into the road in patches, with clean
    edges, and every counter in the stage read correctly throughout.

    Two cases, and there are only two because the ribbon is flat across:

    - **Inside a cap ring** → the fan height. `_Builder.fan` triangulates the
      ring from its centroid, so the height at a point is the barycentric
      interpolation over whichever fan triangle contains it. That is the drawn
      height by construction rather than by approximation.
    - **Anywhere else** → the nearest level-0 centreline's own height at the
      projected station. `_lift(edge.left, points, 0.0)` puts both carriageway
      rails on the centreline's height, so a ribbon has no cross-fall and every
      point across it is at its station's height.

    ⚠️ **Where both apply the cap wins**, because a cap is drawn over the arm it
    overlaps — the 6,051 m² `Q53` measured — and the renderer shows the higher
    surface.

    🔴 **This does not re-open the cliff `blended_height` was written to close.**
    That was a hard *nearest-edge* switch: two arms extrapolate their own grade
    into the cap and disagree by up to 0.43 m where they meet, so a vertex taking
    whichever arm won turned a seam into a step and produced **172 near-vertical
    triangles**. Nothing here switches between arms. The cap ring passes through
    every arriving ribbon's two end corners, and the carriageway is flat across,
    so along an arm's mouth the cap boundary and the ribbon end carry the *same*
    height and the two cases meet continuously. The blend approximated that
    continuity; this reproduces it.

    ⚠️ **`segments` is the caller's to choose and every caller passes level 0**,
    the restriction `Segments.nearest` documents: a marking under a flyover takes
    its height from the street it is painted on, never from the deck above. The
    cap rings are filtered to the same level here.
    """

    # `Segments` over the level-0 edges — see the `TYPE_CHECKING` note above for
    # why the import is guarded.
    segments: Segments
    # Each cap already triangulated as `_Builder.fan` emits it, `(k, 3, 3)`.
    # ⚠️ **Built once in `of` and not per query, which is most of this class's
    # cost**: the apex is the ring's own centroid and the fan pairs each corner
    # with the next, so a query that re-derived them re-rolled the ring every
    # time — measured at 0.712 s against 0.258 s over the region's 24,435 box
    # junction vertices, for byte-identical output.
    fans: tuple[np.ndarray, ...]
    # Plan bounding box per cap as `(min_x, min_z, max_x, max_z)`. A cap is much
    # smaller than the cell it is binned into, so rejecting on it first is what
    # keeps the barycentric pass off the majority of queries that miss.
    bounds: np.ndarray
    # Plan cell to the caps whose bounding box touches it.
    cells: dict[tuple[int, int], tuple[int, ...]]

    @classmethod
    def of(cls, segments: Segments, surface: dict[str, Any], *, level: int = 0) -> DrawnSurface:
        """Read the caps out of a `roadsurface.json` and index them in plan."""
        rings = [
            np.asarray(cap["ring"], dtype=np.float64)
            for cap in surface.get("caps", ())
            if int(cap["level"]) == level and len(cap["ring"]) >= 3
        ]
        fans, bounds = [], []
        binned: dict[tuple[int, int], list[int]] = {}
        for ring in rings:
            plan_low, plan_high = ring[:, [0, 2]].min(axis=0), ring[:, [0, 2]].max(axis=0)
            fans.append(_fan_corners(ring))
            bounds.append(np.concatenate([plan_low, plan_high]))
            index = len(fans) - 1
            low = np.floor(plan_low / _CAP_CELL_M).astype(np.int64)
            high = np.floor(plan_high / _CAP_CELL_M).astype(np.int64)
            for column in range(int(low[0]), int(high[0]) + 1):
                for row in range(int(low[1]), int(high[1]) + 1):
                    binned.setdefault((column, row), []).append(index)
        return cls(
            segments=segments,
            fans=tuple(fans),
            bounds=(np.vstack(bounds) if bounds else np.zeros((0, 4), dtype=np.float64)),
            cells={key: tuple(value) for key, value in binned.items()},
        )

    def narrowed_to(self, segments: Segments) -> DrawnSurface:
        """The same caps, over a subset of the centrelines.

        A method rather than `dataclasses.replace` at the call site, so which
        fields this class has stays this class's business. ⚠️ **The caps are
        deliberately not narrowed with them** — they are already indexed in plan
        and there are 429 of them, so narrowing would cost more than it saves;
        `roadmarks.py` narrows only because `Segments.nearest` scans the whole
        network on every call.
        """
        return replace(self, segments=segments)

    def sample(self, x: float, z: float) -> DrawnHeight:
        """The drawn road at this plan position, and what answered for it.

        🔴 **One accessor, because two callers hand-rolling this diverged.** The
        first version of `Q92` left `boxjunctions._place` taking the cap outright
        where one existed while `height_at` below took the higher of cap and
        ribbon, so on a region with a cap below its arm the two marking stages
        would have placed paint at different heights — and each was documented as
        doing what the other did. Returning both parts once also spares
        `roadmarks.py` a second `cap_height_at` per vertex it only wanted for a
        counter.
        """
        ribbon = float(self.segments.nearest(x, z).y)
        cap = self.cap_height_at(x, z)
        return DrawnHeight(
            height_m=ribbon if cap is None else max(cap, ribbon),
            ribbon_m=ribbon,
            cap_m=cap,
        )

    def height_at(self, x: float, z: float) -> float:
        """The height of the drawn road surface at this plan position.

        ⚠️ **The higher of the two where a cap covers a ribbon, not the cap.**
        A cap and the arm it overlaps are both drawn — the 6,051 m² `Q53`
        measured — and the depth buffer shows whichever stands higher, so a
        marking has to clear that one.

        ⚠️ **This region does exercise it, and an earlier note here claiming
        otherwise was measuring nothing.** That note said taking the cap outright
        ships a byte-identical `boxjunctions.glb` — true only because `_place`
        was calling `cap_height_at` directly and never reached this method at
        all, so the experiment changed no code path. With both callers on
        `sample` the difference is real: `height_spread_m` p90 **0.4260 →
        0.4215**, p99 **0.5051 → 0.4965**, which is paint rising onto the ribbon
        where a cap sits below the arm it overlaps.
        """
        return self.sample(x, z).height_m

    def cap_height_at(self, x: float, z: float) -> float | None:
        """The fan height where a junction cap covers this point, else `None`.

        The highest where caps overlap in plan, which they do wherever two nodes
        are closer together than their arms are wide — `surface.py` draws both
        and the renderer shows the upper one, so this must agree with it rather
        than take the first hit.
        """
        candidates = self.cells.get(
            (int(np.floor(x / _CAP_CELL_M)), int(np.floor(z / _CAP_CELL_M)))
        )
        if candidates is None:
            return None

        best: float | None = None
        for index in candidates:
            low_x, low_z, high_x, high_z = self.bounds[index]
            if not (low_x <= x <= high_x and low_z <= z <= high_z):
                continue
            hits = _hits(self.fans[index], x, z)
            if len(hits) and (best is None or float(hits.max()) > best):
                best = float(hits.max())
        return best


def _fan_corners(ring: np.ndarray) -> np.ndarray:
    """`_Builder.fan`'s triangulation of one cap ring, as `(k, 3, 3)`.

    Written from the same three indices the builder emits — apex, corner, next
    corner — so a change to one is visibly a change to both, which is the whole
    correctness of `DrawnSurface`.

    ⚠️ **Degenerate fan triangles are dropped here rather than per query**, which
    is `terrain.HeightField`'s placement of the same guard and for its reason:
    the ring is fixed and the query is not. A collinear run in a published ring
    contributes a zero-area triangle whose barycentric test is meaningless.
    """
    apex = np.broadcast_to(ring.mean(axis=0), ring.shape)
    fan = np.stack([apex, ring, np.roll(ring, -1, axis=0)], axis=1)
    edge_a, edge_b = fan[:, 1] - fan[:, 0], fan[:, 2] - fan[:, 0]
    twice_area = edge_a[:, 0] * edge_b[:, 2] - edge_a[:, 2] * edge_b[:, 0]
    return fan[np.abs(twice_area) > _MIN_TWICE_AREA_M2]


def downward_facing(mesh: MeshData) -> tuple[int, float]:
    """How many triangles face downward, and how much ground they cover.

    A road triangle that points at the sky's opposite is a fold: it renders as a
    hole under back-face culling and it is invisible to a one-sided collider. A
    kerb riser is vertical and legitimately faces sideways, which is why the
    test is well below horizontal rather than at it.
    """
    cross = mesh.triangle_cross()
    twice_area = np.linalg.norm(cross, axis=1)
    facing = cross[:, 1] / np.where(twice_area > 0.0, twice_area, 1.0)
    inverted = facing < -0.1
    return int(inverted.sum()), float(0.5 * twice_area[inverted].sum())


def _rail_normals(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Per-vertex normal of a strip, from its own along and across directions.

    Derived rather than assumed, so one routine serves the flat carriageway, the
    vertical kerb riser and the lip between them.
    """
    along = np.empty_like(left)
    along[:-1] = left[1:] - left[:-1]
    along[-1] = along[-2]
    normals = np.cross(along, right - left)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    # A rail pair that meets — a zero-width strip — has no facing to compute,
    # and `normalise` leaves those rows at zero rather than at a direction.
    return np.where(length > _MIN_SEGMENT_M, normalise(normals), [0.0, 1.0, 0.0])


def _rgba(colour: tuple[int, int, int], count: int, alpha: np.ndarray | None = None) -> np.ndarray:
    """One RGBA row per vertex, as a read-only view rather than a copy.

    `_Builder.build` materialises it in the one `vstack` that needs it — the
    same reasoning as `buildings.colour_for`.

    ⚠️ **Alpha is a payload, not opacity, and only on the carriageway.** Since
    `P3-13` it says where a kerbside restriction runs (`Q54`); everywhere else
    it is the opaque 255 it always was, which the markings shader never reads
    because it only looks at alpha inside the carriageway class. The broadcast
    view is kept for that case — it is the common one, and it is free.

    ⚠️ **`road_markings.gdshader` hoists the sRGB conversion into a `flat`
    varying on the strength of this function broadcasting one colour per
    strip.** That argument covers `rgb` and says so; alpha varying per vertex
    does not touch it, and must not be folded into the same varying.
    """
    if alpha is None:
        return np.broadcast_to(np.array([*colour, 255], dtype=np.uint8), (count, 4))
    rows = np.empty((count, 4), dtype=np.uint8)
    rows[:, :3] = colour
    rows[:, 3] = alpha
    return rows


def _shoelace(ring: np.ndarray) -> float:
    """Twice the signed plan area. Negative is a face pointing up (+Y)."""
    x, z = ring[:, 0], ring[:, 2]
    return float(np.dot(x, np.roll(z, -1)) - np.dot(np.roll(x, -1), z))


def hull(points: np.ndarray) -> np.ndarray:
    """Convex hull of a junction's ribbon ends, in plan, as (k, 3) in order.

    Andrew's monotone chain. The hull is the right shape for a junction cap
    because its boundary passes through every incoming ribbon's two end corners:
    the cap therefore meets each carriageway along its full width, with no gap,
    and stops at the kerb line rather than spilling into the corner between two
    streets — which is pavement, not road.

    Y comes along for the ride, so a cap on sloping ground follows it.
    """
    order = np.lexsort((points[:, 2], points[:, 0]))
    ordered = points[order]
    if len(ordered) < 3:
        return ordered

    def chain(rows: np.ndarray) -> list[np.ndarray]:
        built: list[np.ndarray] = []
        for point in rows:
            while len(built) >= 2 and _turn(built[-2], built[-1], point) <= 0.0:
                built.pop()
            built.append(point)
        return built

    lower, upper = chain(ordered), chain(ordered[::-1])
    return np.array(lower[:-1] + upper[:-1])


def _turn(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return float((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]))


# --------------------------------------------------------------------------
# Building the region
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _End:
    """One end of one edge, arriving at a node on one elevation level."""

    edge: int
    at_start: bool


class _Cap(NamedTuple):
    """One junction cap: the ring, and the elevation level it fills."""

    level: int
    ring: np.ndarray


class _Arm(NamedTuple):
    """One ribbon as it presents itself to a node, for the mitre through it."""

    # Unit plan direction pointing *away* from the node, whichever end arrived.
    away: np.ndarray
    half_width_m: float
    # The node, in x/y/z, as this arm reports it. They agree to the millimetre
    # their coordinates were rounded to, which is why the caller averages them.
    node: np.ndarray


@dataclass
class _Edge:
    """One graph edge, and the ribbon geometry derived from it.

    `points` is `(N, 5)`: x, y, z, the station's half-width and whether `P3-13`
    inserted it — see `_WIDTH` and `_INSERTED`.
    """

    points: np.ndarray
    # The same widths against the **published** polyline, before `dedupe` drops
    # anything. Kept rather than recomputed for the manifest: `_half_widths` is
    # the one place the widening is applied, and a second evaluation of it is a
    # second thing to keep in step with the config.
    published_half_widths: np.ndarray
    lanes: int
    # Read straight off the published edge and carried only so `TEXCOORD_1` can
    # say them. Nothing about the ribbon's shape depends on any of the three —
    # they decide which markings the shader draws on it, which is why they
    # arrive here rather than in `_shape`.
    direction: str
    bus_lane: bool
    tram_tracks: bool
    level: int
    length_m: float
    trim_start_m: float = 0.0
    trim_end_m: float = 0.0
    # Filled by `_shape`, once the trims are known. The two carriageway
    # boundaries are stored rather than recomputed so the junction cap is built
    # from the same numbers the ribbon was — a cap derived from an unclamped
    # boundary would miss the arm it is supposed to meet.
    ribbon: np.ndarray | None = None
    offsets: np.ndarray | None = None
    left: np.ndarray | None = None
    right: np.ndarray | None = None
    # The outer edge of each kerb. Stored for the same reason as `left`/`right`
    # and with more riding on it: the overlap test decides what to hide by this
    # line and `_draw_edge` draws that very line, so a second expression
    # re-deriving it could drift and start cutting the kerb somewhere it is
    # still visible — with nothing failing loudly.
    lip_left: np.ndarray | None = None
    lip_right: np.ndarray | None = None
    # Per-segment, per-side: whether this ribbon's kerb is the edge of anything.
    # Filled by `_hide_buried_kerbs` once every ribbon exists, because the answer
    # is a question about the neighbours. `None` until then, and `None` means
    # draw it, so an edge the pass skipped keeps the kerb it always had.
    kerb_left: np.ndarray | None = None
    kerb_right: np.ndarray | None = None
    # Filled by `_read_offside`, after `_hide_buried_kerbs` — it is that pass's
    # answer, summarised per edge, plus what an opposed partner contributes.
    # Defaults are the conservative reading: nothing known, so nothing drawn.
    offside_kerb: bool = False
    # ⚠️ The codec's `k`, not the offset: `k - 1` sixteenths of a lane, with 0
    # meaning "not half of a pair". The bias is what makes 0 mean absence, so
    # the raw field is what is stored and the decode is the consumer's.
    centre_step: int = 0
    # `P3-13`: what kind of kerbside line each side carries, as the codec spells
    # it, and where along the edge it applies. The two are separate because they
    # ship in separate channels — see the codec block — and because the kind is
    # constant per side while the extent is not.
    #
    # ⚠️ **Runs are in the *published* frame**, measured along `roadgraph.json`'s
    # polyline, because that is the only frame the graph has. `_draw_edge`
    # subtracts `trim_start_m` to reach the V the ribbon is drawn at, and doing
    # that anywhere else means doing it twice.
    kerb_near: int = MARKING_KERB_ABSENT
    kerb_off: int = MARKING_KERB_ABSENT
    restrictions: dict[str, list[tuple[float, float]]] = field(default_factory=dict)

    def corner(self, at_start: bool, *, on_left: bool) -> np.ndarray | None:
        """One of the two corners this ribbon presents to a junction."""
        plan = self.left if on_left else self.right
        if plan is None or self.ribbon is None:
            return None
        row = 0 if at_start else -1
        return np.array([plan[row][0], self.ribbon[row][1], plan[row][1]])

    def marking_code(self, surface_class: int) -> float:
        """This edge's packed `TEXCOORD_1.x` for one of its surface classes.

        An unrecognised `direction` packs as 0 rather than raising: the codec
        reads 0 as "absent" everywhere, so the shader falls back to the markings
        that need no direction instead of drawing a wrong centre line. The
        closed vocabulary is `roads.py`'s to enforce, and it does.

        ⚠️ **The guard is per field, not on the total, and the total cannot
        stand in for it.** `lanes` is the only unbounded input — city config
        authors it per road class with no ceiling — and at 16 it packs to 64,
        carries into `direction`, and still leaves a total under
        `MARKING_CODE_MAX`. So a check on the sum passes while the code decodes
        as no lanes travelling in a direction the vocabulary does not have.
        """
        if not 0 < self.lanes <= MARKING_LANES_MAX:
            raise ValueError(
                f"{self.lanes} lanes is past what `TEXCOORD_1` can say "
                f"(1-{MARKING_LANES_MAX}): the code would carry into `direction`"
            )
        return float(
            surface_class
            + MARKING_LANES * self.lanes
            + MARKING_DIRECTION * MARKING_DIRECTIONS.get(self.direction, 0)
            + MARKING_BUS_LANE * int(self.bus_lane)
            + MARKING_TRAM * int(self.tram_tracks)
            + MARKING_OFFSIDE_KERB * int(self.offside_kerb)
            + MARKING_CENTRE * self.centre_step
            + MARKING_KERB_NEAR * self.kerb_near
            + MARKING_KERB_OFF * self.kerb_off
        )

    def end_half_width_m(self, at_start: bool) -> float:
        """The half-width this edge arrives at a node with.

        Its *own* end, not the widest anywhere along it: since `Q23` those can
        differ by the whole widening factor, and it is the end that decides how
        far back the junction cap has to reach to meet this arm.
        """
        return float(self.points[0 if at_start else -1, _WIDTH])


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    out_root: Path | None = None,
) -> SurfaceReport:
    """Read the region's road graph and write its `roads.glb`."""
    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    style = city.roads.surface

    report = SurfaceReport()
    edges = [_prepare(edge, style, report) for edge in graph["edges"]]
    # Zipped rather than looked up: `_prepare` maps the published edges one for
    # one and in order, so the pairing is the list's own construction. The
    # *published* widths, not the ribbon's — `dedupe` has already dropped
    # stations from the latter, and the game indexes this table by
    # `roadgraph.json`'s own vertex numbering.
    report.carriageway = {
        int(published["id"]): [round(float(half), 3) for half in prepared.published_half_widths]
        for published, prepared in zip(graph["edges"], edges, strict=True)
    }
    report.on_structure_m = sum(_on_structure_length_m(edge) for edge in graph["edges"])
    ends = _ends_by_node_and_level(graph["edges"], edges)
    _assign_trims(ends, edges, style, report)
    # After the assignment, not beside `carriageway` above: the trims do not
    # exist until `_assign_trims` has seen every end that meets every node.
    report.trims_m = {
        int(published["id"]): (round(prepared.trim_start_m, 3), round(prepared.trim_end_m, 3))
        for published, prepared in zip(graph["edges"], edges, strict=True)
    }
    _measure_level_steps(ends, edges, report)
    for edge in edges:
        # After the trims and before the offsets: a boundary outside the drawn
        # ribbon needs no station, and `_shape` is what turns stations into
        # rails. See `_add_kerb_stations`.
        report.kerb_stations += _add_kerb_stations(edge)
        _shape(edge, style)

    # Capped after every ribbon exists, because a cap is defined by where the
    # ribbons it joins actually ended — including where a trim was clamped. The
    # rings are held rather than drawn straight away: a cap covers kerb too, so
    # `_hide_buried_kerbs` has to see them before any of it is emitted.
    caps = [
        _Cap(level, ring)
        for (_, level), group in ends.items()
        if (ring := _cap_ring(group, edges, report)) is not None
    ]
    _hide_buried_kerbs(edges, caps, report)
    # Held here rather than beside the `builder.fan` loop below, because that
    # loop is the *drawing* and this is the record of what will be drawn. A cap
    # refused by `_cap_ring` never reaches either, so the two populations are the
    # same list by construction rather than by a predicate written twice.
    report.cap_rings = [(cap.level, cap.ring) for cap in caps]
    _record_hidden_kerbs(graph["edges"], edges, report)
    _read_offside(graph["edges"], edges, report)

    builder = _Builder()
    for edge in edges:
        if _draw_edge(builder, edge, style, city.roads.lane_width_m, report):
            report.edges += 1
    for cap in caps:
        # A cap is no length of lane, so it carries no lanes and no length —
        # and that zero length is what the markings shader reads through
        # `min(V, length - V)` as "hard against a junction".
        builder.fan(
            cap.ring,
            colour=style.surface_material.colour,
            marking=_Marking(float(MARKING_CLASS_CAP), 0.0),
        )
        report.junctions += 1

    mesh = builder.build(SURFACE_MESH_NAME)
    report.inverted, report.inverted_area_m2 = downward_facing(mesh)
    report.triangles = mesh.triangle_count
    report.vertices = len(mesh.positions)
    report.aabb = mesh.aabb()
    report.bytes = write_glb(out_dir / SURFACE_NAME, [mesh])
    _write_manifest(out_dir, city, region_id, report)
    return report


def _prepare(published: dict, style: RoadSurface, report: SurfaceReport) -> _Edge:
    """One published edge as a ribbon-in-waiting, half-widths already resolved.

    The widths are computed against the **published** polyline, before `dedupe`
    drops anything, so `report.carriageway` and `roadgraph.json` index alike —
    which is the contract the game reads them under.
    """
    half_widths = _half_widths(published, style)
    points = dedupe(
        np.column_stack([_polyline(published), half_widths, np.zeros(len(half_widths))])
    )
    restrictions, kinds, minority_m = _kerbside(published)
    report.kerb_minority_m += minority_m
    return _Edge(
        points=points,
        published_half_widths=half_widths,
        lanes=published["lanes"],
        direction=published["direction"],
        bus_lane=bool(published["bus_lane"]),
        tram_tracks=bool(published["tram_tracks"]),
        level=published["elevation_level"],
        length_m=float(plan_lengths(points)[-1]) if len(points) > 1 else 0.0,
        kerb_near=kinds[NEARSIDE],
        kerb_off=kinds[OFFSIDE],
        restrictions=restrictions,
    )


def _add_kerb_stations(edge: _Edge) -> int:
    """Give this edge the stations its restriction boundaries need (`P3-13`).

    ⚠️ **After the trims are assigned, not in `_prepare` where the runs arrive.**
    A boundary under a junction cap is one no marking can be drawn at, and this
    region puts a lot of them there — restrictions start and stop at junctions,
    which is exactly where the ribbon does not reach. Filtering by the drawn
    extent is free and it is the difference between paying for every boundary
    and paying for the ones that show.

    The trims are this stage's own number, so this couples to nothing. ⚠️ The
    *fade* would cut more still and must not be used: `fade_m` is shader tuning
    (`tuning/road_markings.tres`), and an ETL that read it would rebuild the
    city every time someone turned a dial.
    """
    if not edge.restrictions:
        return 0
    low, high = edge.trim_start_m, edge.length_m - edge.trim_end_m
    edge.points, inserted = _insert_stations(
        edge.points,
        (
            bound
            for runs in edge.restrictions.values()
            for run in runs
            for bound in run
            if low < bound < high
        ),
    )
    # Marked here rather than in `_insert_stations`, which stays ignorant of
    # what any column means — it is handed distances and gives back rows.
    edge.points[inserted, _INSERTED] = 1.0
    return len(inserted)


def _kerbside(
    published: dict,
) -> tuple[dict[str, list[tuple[float, float]]], dict[str, int], float]:
    """One edge's no-stopping runs, the kind each side carries, and what that cost.

    ⚠️ **The codec can say one kind per side and the source does not promise
    one.** `TIME_ZONE` separates a 24-hour restriction from a posted-hours one,
    and where a side carries both, the longer wins and the shorter is drawn as
    the wrong line. That is a real error and it is small — **188 m of Wan Chai's
    26,065**, across 9 of 650 covered sides — so it is measured and reported
    rather than designed around. Giving the kind its own per-run channel would
    cost a second byte on every road vertex to fix 0.7% of one region.

    A side with no run at all is `MARKING_KERB_NONE` rather than `ABSENT` when the
    graph published a `kerbside` list, because it is then a positive statement:
    the source was consulted about this kerb and restricts nothing on it. Only a
    city whose graph carries no such list reports `ABSENT`.
    """
    runs = published.get("kerbside")
    if runs is None:
        return {}, {NEARSIDE: MARKING_KERB_ABSENT, OFFSIDE: MARKING_KERB_ABSENT}, 0.0

    extents: dict[str, list[tuple[float, float]]] = {NEARSIDE: [], OFFSIDE: []}
    metres: dict[str, dict[int, float]] = {NEARSIDE: {}, OFFSIDE: {}}
    for run in runs:
        side = str(run["side"])
        start, stop = float(run["from_m"]), float(run["to_m"])
        extents[side].append((start, stop))
        kind = MARKING_KERB_KINDS[str(run["kind"])]
        metres[side][kind] = metres[side].get(kind, 0.0) + stop - start

    kinds: dict[str, int] = {}
    minority_m = 0.0
    for side, votes in metres.items():
        if not votes:
            kinds[side] = MARKING_KERB_NONE
            continue
        # Ties broken by the kind's own code, so a rebuild publishes the same
        # file — the same reason `kerbside.merge_runs` sorts before taking a maximum.
        kinds[side] = max(sorted(votes), key=lambda kind: votes[kind])
        minority_m += sum(votes.values()) - votes[kinds[side]]
    return extents, kinds, minority_m


def _insert_stations(points: np.ndarray, at: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    """The polyline with a station added at each given distance along it.

    Returns the merged polyline and the **row indices of the added stations
    within it**, so a caller can mark them without re-deriving where they went.
    Indices rather than a count because the merge is a sort: the new rows are
    interleaved, not appended, and their positions are this function's own
    answer.

    This is what buys the exact V-range. `TEXCOORD_1` is `flat` across a strip
    and `COLOR_0` is interpolated between stations, so an extent written on the
    stations the graph happens to have would ramp over whole city blocks. A pair
    of stations `_KERB_STATION_M` either side of a boundary makes the ramp half
    a metre instead, which is closer than a driver can see the end of a line.

    ⚠️ **Nothing else about the ribbon changes, and that is the property being
    relied on.** The new stations lie *on* the existing polyline, so the shape,
    the plan length and the mitres are all identical — and `_at` interpolates
    every column, so each one arrives with the correct height and half-width
    without this function knowing there is a `_WIDTH` column at all.

    A boundary within half a station's spacing of a vertex the polyline already
    has is skipped: the extent then starts at that vertex instead, which is at
    most `_KERB_STATION_M / 2` out, and the alternative is a quad thin enough to
    collapse in `_Builder.build`.
    """
    empty = np.zeros(0, dtype=int)
    if len(points) < 2:
        return points, empty
    along = plan_lengths(points)
    wanted: list[float] = []
    for bound in at:
        for distance in (bound - _KERB_STATION_M, bound + _KERB_STATION_M):
            if 0.0 < distance < along[-1] and np.abs(along - distance).min() > _KERB_STATION_M / 2:
                wanted.append(distance)
    wanted = sorted(set(wanted))
    if not wanted:
        return points, empty

    added = np.vstack([_at(points, along, distance) for distance in wanted])
    merged = np.vstack([points, added])
    # Stable, so a new station landing exactly on an old one keeps the old one
    # first and the pair stays in the order `mitres` expects.
    order = np.argsort(np.concatenate([along, wanted]), kind="stable")
    # Where each added row ended up: `order` says which source row each output
    # row came from, so the rows drawn from the back of the stack are the new
    # ones. Read off the sort rather than recomputed, for the same reason
    # `_Edge` stores `lip_left` instead of re-deriving it — a second expression
    # for the same thing is a second thing to drift.
    return merged[order], np.flatnonzero(order >= len(points))


def _half_widths(published: dict, style: RoadSurface) -> np.ndarray:
    """Half the drawn carriageway at every station of one published edge.

    Closes `Q23`. Two factors and a blend between them: what this edge is drawn
    at on the street, and what it is drawn at on a deck. Where the two agree —
    every off-grade edge, and every edge of a city that samples no decks — the
    blend is arithmetically inert and this is the constant it always was.

    The taper reaches *backwards* from the structure into the approach, so the
    ribbon is already at its authored width by the time it arrives. Distance is
    measured to the nearest on-structure station in **plan along the edge**, not
    in station counts: `roads.py` resamples a lifted edge at 10 m but leaves the
    source's own vertices in place, so consecutive stations are not evenly
    spaced and counting them would taper a densely drawn curve over a few metres
    and a straight over a hundred.
    """
    level = published["elevation_level"]
    limit = published["speed_limit_kph"]
    width = published["width_m"]
    at_grade = style.drawn_width_m(width, limit, elevation_level=level)
    on_deck = style.drawn_width_m(width, limit, elevation_level=level, on_structure=True)

    flags = np.asarray(published["on_structure"], dtype=bool)
    if at_grade == on_deck or not flags.any():
        return np.full(len(flags), at_grade / 2.0)

    along = plan_lengths(_polyline(published))
    gap = np.abs(along[:, None] - along[flags][None, :]).min(axis=1)
    # A zero taper is the literal reading — width changes at the boundary and
    # nowhere else — and it has to stay reachable rather than dividing by zero,
    # because it is what a city with a hard kerb line beside its viaducts wants.
    blend = (gap <= 0.0) if style.structure_taper_m <= 0.0 else 1.0 - gap / style.structure_taper_m
    blend = np.clip(blend, 0.0, 1.0)
    # ⚠️ **The blend runs between the two DRAWN widths, not between two floors.**
    # Interpolating the floors and taking `max` once at the end would hold a road
    # already wider than the floor at its own width for the whole taper and then
    # step it, which is the jog `structure_taper_m` exists to remove.
    return (at_grade + (on_deck - at_grade) * blend) / 2.0


def _on_structure_length_m(published: dict) -> float:
    """Metres of this edge's centreline resting on structure, if it is level 0.

    `Q23`'s measurement, reproduced by the stage that acts on it. Level 0 only:
    an off-grade edge is on structure along its whole length by definition and
    counting it would bury the number this exists to report.

    The trapezoid rule on the flag — a segment counts fully when both its ends
    are on structure and half when one is. A flag is a property of a station and
    length is a property of what lies between two of them, so some rule has to
    bridge the two; this one is symmetric, and it cannot report a length for an
    edge with no flag set at all.
    """
    if published["elevation_level"] != 0:
        return 0.0
    flags = np.asarray(published["on_structure"], dtype=float)
    if len(flags) < 2 or not flags.any():
        return 0.0
    steps = plan_steps(_polyline(published))
    return float((steps * 0.5 * (flags[:-1] + flags[1:])).sum())


def _polyline(published: dict) -> np.ndarray:
    return np.asarray(published["polyline"], dtype=np.float64)


def _shape(edge: _Edge, style: RoadSurface) -> None:
    """Trim the edge back from its junctions and offset what is left."""
    points = dedupe(trim(edge.points, edge.trim_start_m, edge.trim_end_m))
    if len(points) < 2:
        return
    edge.ribbon = points
    edge.offsets = mitres(points)
    half = points[:, _WIDTH]
    edge.left = boundary(points, edge.offsets, half)
    edge.right = boundary(points, edge.offsets, -half)
    edge.lip_left = boundary(points, edge.offsets, half + style.kerb_width_m)
    edge.lip_right = boundary(points, edge.offsets, -(half + style.kerb_width_m))


def _ends_by_node_and_level(
    published: list[dict], edges: list[_Edge]
) -> dict[tuple[int, int], list[_End]]:
    """Edge ends grouped by the node *and the level* they arrive on.

    The level is part of the key, which is the opposite of how `P1-3` keys
    nodes and is right for the opposite reason. A node exists so a flyover and
    the ramp under it stay one network; a junction cap is a piece of tarmac, and
    there is no tarmac between a street and the tunnel roof 8 m below it.
    """
    groups: dict[tuple[int, int], list[_End]] = defaultdict(list)
    for index, edge in enumerate(published):
        geometry = edges[index]
        if len(geometry.points) < 2:
            continue
        for node, at_start in ((edge["from"], True), (edge["to"], False)):
            groups[(node, geometry.level)].append(_End(edge=index, at_start=at_start))
    return groups


def _assign_trims(
    ends: dict[tuple[int, int], list[_End]],
    edges: list[_Edge],
    style: RoadSurface,
    report: SurfaceReport,
) -> None:
    """Hold each ribbon back from the nodes where it meets another at its level.

    An end alone at its node and level is left long: there is nothing to join
    to, and trimming would leave the carriageway stopping short of the map edge
    or of the ramp it dead-ends against.

    ⚠️ The radius is the widest *end* at the node, not the widest edge. Those
    stopped being the same thing at `Q23`, and the end is the right one: the cap
    has to reach the mouth of each arm, and an arm's mouth is as wide as that
    arm is *there*. Taking the widest anywhere along a touchdown edge would trim
    every arm at that node back by the at-grade width of a road that arrives
    narrow.
    """
    for group in ends.values():
        if len(group) < 2:
            continue
        radius = style.junction_trim_factor * max(
            edges[end.edge].end_half_width_m(end.at_start) for end in group
        )
        for end in group:
            edge = edges[end.edge]
            ceiling = edge.length_m * style.junction_trim_max_fraction
            if end.at_start:
                edge.trim_start_m = min(radius, ceiling)
            else:
                edge.trim_end_m = min(radius, ceiling)
            report.trimmed_ends += 1
            if ceiling < radius:
                report.clamped_trims += 1


def _cells(low: np.ndarray, high: np.ndarray, level: int) -> list[tuple[int, int, int]]:
    """Grid cells a plan bounding box touches, keyed by elevation level too.

    A flyover and the street under it share plan and nothing else, so the level
    belongs in the key: without it every deck would be asked to occlude the
    kerbs of the road it flies over.
    """
    lo = np.floor(low / _OVERLAP_CELL_M).astype(int)
    hi = np.floor(high / _OVERLAP_CELL_M).astype(int)
    return [(level, x, z) for x in range(lo[0], hi[0] + 1) for z in range(lo[1], hi[1] + 1)]


class _Occluders:
    """Every piece of road that might already cover a kerb, bucketed by plan cell.

    A uniform grid rather than a tree: the ribbons are all of a similar size and
    the region is small, so bucketing by bounding box is enough to turn an
    every-pair test into an every-neighbour one. Polygons are held by reference,
    and a cell holds keys rather than arrays so a candidate found through three
    shared cells is still only tested once.
    """

    def __init__(self) -> None:
        self._plans: list[np.ndarray] = []
        self._low: list[np.ndarray] = []
        self._high: list[np.ndarray] = []
        self._index: dict[tuple[int, int, int], list[int]] = defaultdict(list)

    def add(self, plan: np.ndarray, level: int) -> int:
        low, high = plan.min(axis=0), plan.max(axis=0)
        key = len(self._plans)
        self._plans.append(plan)
        self._low.append(low)
        self._high.append(high)
        for cell in _cells(low, high, level):
            self._index[cell].append(key)
        return key

    def cover(self, points: np.ndarray, level: int, *, ignoring: int) -> np.ndarray:
        """Which of these plan points some polygon other than `ignoring` contains.

        Cells come from the *query's* own box, not from whatever box `ignoring`
        was added with. The two differ by a kerb width here, and asking the
        wrong one would silently miss a neighbour lying just past the edge of
        the ribbon's own extent.
        """
        low, high = points.min(axis=0), points.max(axis=0)
        near = {key for cell in _cells(low, high, level) for key in self._index[cell]}
        near.discard(ignoring)

        covered = np.zeros(len(points), dtype=bool)
        for key in near:
            # Six comparisons, and on Wan Chai they reject 65% of the candidates
            # before the crossing-number sweep that would otherwise dominate.
            if (self._low[key] > high).any() or (self._high[key] < low).any():
                continue
            covered |= inside_polygon(points, self._plans[key])
        return covered


def _read_offside(published: list[dict], edges: list[_Edge], report: SurfaceReport) -> None:
    """What each edge's offside boundary actually is, once every ribbon exists.

    Two questions with one answer between them, and neither can be asked of an
    edge on its own — which is why this runs after `_hide_buried_kerbs` rather
    than in `_prepare`.

    **Is `U = lanes` a kerb?** On an ordinary street, yes. On one half of a dual
    carriageway drawn as an opposed pair it is the middle of the road, and a
    kerbside double yellow put there is a no-stopping line down the centre of a
    street — the loudest way to be wrong about a marking. `_hide_buried_kerbs`
    has already decided this for its own purposes: a kerb it declined to draw is
    one lying inside a neighbour's carriageway. Reusing its verdict rather than
    re-deriving one is the point; a second geometric test would be a second thing
    to keep in step, and this one is already graded by the kerb it hides.

    ⚠️ **`.all()` rather than a share, because the codec cannot say more.** The
    carriageway is one strip carrying one code, so this is a per-edge summary of
    a per-segment answer and the conservative reading is the only honest one.
    Measured on Wan Chai it costs 10 two-way edges their offside line to partial
    burial and buys 280 one-way edges theirs, which is why it is worth the
    coarseness.

    **Where do the two flows meet?** Midway between the two *centrelines*, which
    an edge cannot see from its own lane coordinate — the ribbons overlap, so
    both edges' `U = lanes` sit inside the other's carriageway rather than at the
    join. Published as `centre_step`, in sixteenths of a lane beyond the
    centreline.

    ⚠️ **Pairs are found by shared endpoints, which `P1-4` measured as a lower
    bound.** Two one-way carriageways that do not share both ends are not
    counted, and their offsides are then reported as kerbs. The buried-kerb test
    above is what stops that being a marking fault: where the ribbons really do
    overlap, the kerb is hidden and `offside_kerb` stays false whether a pair was
    identified or not. So a missed pair costs the centre line, not a yellow line
    down the middle of a road.
    """
    by_ends: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, entry in enumerate(published):
        if entry["direction"] == FORWARD:
            by_ends[(entry["from"], entry["to"])].append(index)

    for index, (entry, edge) in enumerate(zip(published, edges, strict=True)):
        # `None` means the pass had nothing to say. It is unreachable for an edge
        # that draws — `_shape` sets `lip_right` beside `right` — and the reading
        # that matches it is "no neighbour objected", so the kerb stands.
        edge.offside_kerb = edge.kerb_right is None or bool(edge.kerb_right.all())

        if entry["direction"] != FORWARD:
            continue
        # An edge whose two ends are the same node matches its own key, and a
        # street is not its own opposed carriageway. Left in, it publishes a
        # centre line down the middle of its own lane. The level guard is the
        # same argument as the junction cap's: a ramp and the street beneath it
        # can share both nodes and share no tarmac.
        partners = [
            other
            for other in by_ends.get((entry["to"], entry["from"]), [])
            if other != index and edges[other].level == edge.level
        ]
        # ⚠️ **Measured symmetrically, and it has to be.** Each half of a pair
        # publishes its own offset and the two are supposed to name the *same*
        # line. A one-sided measure — this edge's stations against the partner's
        # segments — lets them disagree, and they did: the region's pairs landed
        # their two lines up to 3.9 m apart. The mean of both directions is equal
        # by construction whichever half is asking.
        gaps = [
            0.5 * (there + back)
            for other in partners
            if (there := _centreline_gap_m(edge, edges[other])) is not None
            and (back := _centreline_gap_m(edges[other], edge)) is not None
        ]
        if not gaps:
            continue
        gap = min(gaps)
        report.opposed_pair_ends += 1

        steps = round((gap / 2.0) / _u_metres(edge) * 16.0)
        # ⚠️ **Bounded by the carriageway, not by the field.** Six bits reach 3.94
        # lanes, but a join is only *visible* while `lanes/2 + steps/16 < lanes`,
        # i.e. `steps < 8 * lanes`. A pair separated by more than its own width
        # passes a field-range check, publishes, and draws nothing — which is the
        # failure this first shipped with, found by looking at a frame rather
        # than by a check. Zero is refused for its own reason: a measured
        # separation of nothing is a measurement that did not work.
        if not 0 < steps < min(8 * edge.lanes, MARKING_CENTRE_MAX):
            report.opposed_pairs_unpublishable += 1
            continue
        edge.centre_step = steps + 1


def _u_metres(edge: _Edge) -> float:
    """What one lane-coordinate unit is worth on the ground, in metres.

    ⚠️ **Not `lane_width_m`.** U is normalised to the ribbon *as drawn* — that is
    what makes an integer U a lane boundary whatever the widening did — so one
    U-lane is the drawn width over the lane count: **5.12 m** on a widened
    two-lane street against the 3.20 m the config authors. Dividing by the
    authored width puts a join 1.6x too far out, which on a two-lane ribbon
    lands it past `U = lanes` and off the carriageway entirely.

    ⚠️ Since `Q23` the half-width varies per station while `across` is constant
    per strip, so U is renormalised at every station and no single scalar is
    exact. The median is the representative one; every opposed pair in this
    region is flat-widthed, so today it is also exact.
    """
    return 2.0 * float(np.median(edge.points[:, _WIDTH])) / edge.lanes


def _centreline_gap_m(edge: _Edge, other: _Edge) -> float | None:
    """How far this edge's drawn ribbon runs from its opposed partner's, in plan.

    ⚠️ **Measured on the ribbon, not on the centreline, and that is the whole
    correctness of it.** A pair is found by shared endpoints, so the two
    centrelines *touch* at both ends — those stations contribute an exact 0.0,
    and on a four-station edge they are half the sample, which drags the median
    to half the true separation. Measured on Wan Chai: Fleming read **3.85 m**
    against a true **7.98 m**, and each half of the pair then published a
    different offset and drew its own line, 3.9 m apart. The ribbon is already
    trimmed back from both nodes for the junction cap, so it carries no shared
    station and no zero.
    """
    here, there = _ribbon_plan(edge), _ribbon_plan(other)
    if here is None or there is None or len(there) < 2:
        return None
    return float(np.median(edge_distances(here, there, closed=False)))


def _ribbon_plan(edge: _Edge) -> np.ndarray | None:
    """This edge's drawn ribbon in plan, or `None` if it draws nothing."""
    if edge.ribbon is None or len(edge.ribbon) == 0:
        return None
    return edge.ribbon[:, [0, 2]]


def _hide_buried_kerbs(edges: list[_Edge], caps: list[_Cap], report: SurfaceReport) -> None:
    """Drop the kerb wherever another piece of road has already covered it.

    Each edge is extruded on its own account, so an opposed carriageway pair
    gets four kerbs rather than two — and `hong_kong.yaml` picked its 1.6x
    widening *because* those pairs then overlap "into a single continuous
    surface". The tarmac merges; the kerbs come along uninvited and end up as a
    0.5 m strip of pale concrete standing 0.15 m proud in the middle of a road
    that looks like one road. 33 km of it in Wan Chai, most of it on GLOUCESTER,
    VICTORIA PARK, HENNESSY and LOCKHART. It is not cosmetic: the mesh ships as
    one trimesh collider, `handling.tres` allows 0.18 m of suspension travel,
    and the region's own kerb spends 83% of it in a single step.

    The test is the **outer** lip, not the kerb line: a kerb whose far edge is
    still inside a neighbour is wholly swallowed, while one the neighbour merely
    reaches into is a real boundary between two surfaces and stays. That is what
    keeps this from eating the kerb every time two ribbons touch at a junction.

    Nothing is deleted from the carriageway — only the kerb stops being drawn,
    so the road under it is unchanged and no collider gains a hole.
    """
    occluders = _Occluders()
    own: dict[int, int] = {}
    for position, edge in enumerate(edges):
        if edge.left is None or edge.right is None:
            continue
        own[position] = occluders.add(np.vstack([edge.left, edge.right[::-1]]), edge.level)
    for cap in caps:
        occluders.add(cap.ring[:, [0, 2]], cap.level)

    for position, edge in enumerate(edges):
        if position not in own:
            continue
        edge.kerb_left = _surviving_kerb(edge, edge.lip_left, occluders, own[position], report)
        edge.kerb_right = _surviving_kerb(edge, edge.lip_right, occluders, own[position], report)


def _surviving_kerb(
    edge: _Edge,
    lip: np.ndarray | None,
    occluders: _Occluders,
    key: int,
    report: SurfaceReport,
) -> np.ndarray | None:
    """One side's per-segment mask: whether that quad of kerb is still an edge."""
    if lip is None:
        return None
    # The middle of each quad the kerb is drawn as, not its stations. A station
    # sits exactly on a neighbour's boundary whenever two arms meet end-on at a
    # junction — every arm of a plain crossroads does — and a crossing-number
    # test counts a boundary point as inside. One such touch would take the
    # whole kerb of a two-station edge.
    middle = 0.5 * (lip[:-1] + lip[1:])
    buried = occluders.cover(middle, edge.level, ignoring=key)
    # Along the kerb, not along the centreline it was offset from: on a bend the
    # outer lip is the longer of the two, and the field is called kerb metres.
    report.buried_kerb_m += float(np.linalg.norm(np.diff(lip, axis=0), axis=1)[buried].sum())
    return ~buried


def _record_hidden_kerbs(published: list[dict], edges: list[_Edge], report: SurfaceReport) -> None:
    """Where each ribbon draws no kerb, in ribbon metres, per side (`P3-19`).

    `_hide_buried_kerbs` already decides this — per quad, against every other
    ribbon and cap in the region — and until now only the *total* survived, as
    `buried_kerb_m`. `P3-19` needs the positions: a pedestrian railing joined
    to a kerb that is buried under the opposing carriageway is a fence drawn
    down the middle of merged tarmac, and **11.1% of the region's railing
    metres join to exactly that**.

    ⚠️ **Published rather than recomputed downstream**, the rule `arrows.py`
    states for the drawn half-width: coverage is a question about every other
    ribbon *and* about the junction caps, and a second implementation of it in
    another stage would disagree near the caps and tell nobody which answer was
    right (`Q56`).

    ⚠️ **Ribbon metres, not published-polyline metres.** Zero is the trimmed
    start, because that is the frame the mask itself lives in — a consumer
    holding a distance along `roadgraph.json`'s polyline subtracts `trim_m[0]`.
    Edges that draw nothing, and sides that are wholly drawn, are simply absent.
    """
    for entry, edge in zip(published, edges, strict=True):
        if edge.ribbon is None or len(edge.ribbon) < 2:
            continue
        along = plan_lengths(edge.ribbon)
        hidden = {
            side: [
                # `stop` is exclusive, the half-open station range `_runs`
                # publishes and `_draw_edge` slices with.
                [round(float(along[start]), 3), round(float(along[stop - 1]), 3)]
                for start, stop in _runs(~mask)
            ]
            for side, mask in ((NEARSIDE, edge.kerb_left), (OFFSIDE, edge.kerb_right))
            if mask is not None
        }
        # Only the edges with something to say. A side that is wholly drawn
        # contributes an empty list and a whole edge of them contributes
        # nothing, which keeps this out of the 737 entries it has no news for.
        if any(hidden.values()):
            report.kerb_hidden_m[int(entry["id"])] = {
                side: ranges for side, ranges in hidden.items() if ranges
            }


def _runs(keep: np.ndarray) -> list[tuple[int, int]]:
    """Station ranges for each run of consecutive kept segments.

    `keep` carries one flag per quad, so a run of `n` of them is a strip over
    `n + 1` stations and can never be too short to draw. A kerb that survives in
    pieces is drawn as pieces: the cut ends leave the riser open, which is
    invisible and unreachable, since whatever buried the kerb still lies over it.
    """
    changes = np.flatnonzero(np.diff(np.concatenate([[False], keep, [False]]).astype(np.int8)))
    return [(int(start), int(stop) + 1) for start, stop in changes.reshape(-1, 2)]


def _rail_stations(
    points: np.ndarray,
    runs: list[tuple[int, int]],
    rails: tuple[np.ndarray, ...],
    report: SurfaceReport,
) -> np.ndarray:
    """Which of the ribbon's stations the kerb rails are drawn from.

    `P3-13` inserts a pair of stations either side of every drawn restriction
    boundary so `COLOR_0.a` can turn on in half a metre instead of over a city
    block. **Only the carriageway strip reads that channel** — every kerb vertex
    in the region carries 255 — but the stations go into `_Edge.points`, which
    all four kerb strips are drawn from too. In Wan Chai that was 6,884 vertices
    of a one-draw-call surface saying nothing, about 18% of the road mesh, in
    every frame.

    So the kerbs take the stations they need and no more. Three kinds are
    needed, and the third is the one that is easy to miss:

    - the ribbon's own ends, which are where every rail stops;
    - a station some rail is genuinely not straight through (`_off_line`);
    - **the ends of every surviving kerb run.** `_hide_buried_kerbs` decides
      coverage per *quad*, so a run boundary is a station where the answer
      changes, and merging the two quads across it would silently move
      `buried_kerb_m` — the region's largest kerb number — with nothing failing.

    ⚠️ **`runs` must be the very lists the caller then draws**, not a fresh
    derivation of them. `_draw_edge` remaps each run into the returned stations
    with `searchsorted`, which is exact only because both of a run's ends are
    pinned here — hand it a second opinion and a quad silently spans a boundary.

    Everything else is collinear filler, and a rail that skips it is the same
    rail. `report.kerb_rail_offset_m` is how true that turned out to be.

    ⚠️ **A third of Wan Chai's stations are kept, and the finding is that they
    were never free.** `PROGRESS.md` priced `P3-13`'s kerb vertices by stubbing
    the insertion out entirely and reported all 6,884 as dead weight. 390 of
    the 1,179 are not: 252 carry a kerb height the chord across them does not
    have, and 138 are ends of a ribbon or of a buried-kerb run. Stubbing would
    have moved kerbs, quietly. What is actually free is 789 of them.
    """
    # Two stations at least, because `_shape` refuses to give an edge a ribbon
    # below that and `_draw_edge` is the only caller — so both ends exist.
    inserted = points[:, _INSERTED] == 1.0
    droppable = inserted.copy()
    droppable[0] = droppable[-1] = False
    for start, stop in runs:
        droppable[start] = droppable[stop - 1] = False

    if droppable.any():
        offset = np.zeros(len(points))
        for rail in rails:
            offset = np.maximum(offset, _off_line(rail))
        droppable &= offset <= _STRAIGHT_M
        report.kerb_rail_offset_m = max(
            report.kerb_rail_offset_m, float(offset[droppable].max(initial=0.0))
        )

    stations = np.flatnonzero(~droppable)
    # Counted off what survives, not off what was refused: an inserted station
    # pinned as a run end costs a rail vertex exactly as much as one a rail
    # bends through, and this field is the cost.
    report.kerb_rail_stations += int(inserted[stations].sum())
    return stations


def _measure_level_steps(
    ends: dict[tuple[int, int], list[_End]], edges: list[_Edge], report: SurfaceReport
) -> None:
    """Measure the vertical steps the graph leaves at grade transitions (`Q13`).

    Read off the level groups rather than off the heights, so this finds the
    nodes where the *network* changes level. Two edges meeting at one level
    differ in height only by the millimetre their coordinates were rounded to.

    Assigns rather than accumulates, unlike its sibling counters — there is one
    call site and a distribution is not a running total.
    """
    heights: dict[int, list[float]] = defaultdict(list)
    levels: dict[int, set[int]] = defaultdict(set)
    for (node, level), group in ends.items():
        levels[node].add(level)
        for end in group:
            points = edges[end.edge].points
            heights[node].append(float(points[0 if end.at_start else -1][1]))

    report.level_steps_m = sorted(
        max(heights[node]) - min(heights[node]) for node, found in levels.items() if len(found) > 1
    )


def _draw_edge(
    builder: _Builder,
    edge: _Edge,
    style: RoadSurface,
    lane_width_m: float,
    report: SurfaceReport,
) -> bool:
    """The carriageway and both kerbs, between this edge's two trims."""
    points, offsets = edge.ribbon, edge.offsets
    if points is None or offsets is None or edge.left is None or edge.right is None:
        return False

    along = plan_lengths(points)
    # The ribbon as *drawn*, after both junction trims — so V = 0 and V = drawn
    # are where the carriageway actually stops and the cap takes over, which is
    # where the shader has to have faded its markings out. The published length
    # would leave a stub of lane line standing under every cap.
    drawn_m = float(along[-1])
    carriageway = _Marking(edge.marking_code(MARKING_CLASS_CARRIAGEWAY), drawn_m)
    kerb_marking = _Marking(edge.marking_code(MARKING_CLASS_KERB), drawn_m)
    kerb, rise = style.kerb_width_m, style.kerb_height_m
    # U is a lane coordinate: 0 at the nearside kerb line, `lanes` at the
    # offside one. The kerb runs off the ends of that range.
    #
    # ⚠️ **`outside` is not in the same units as U**, despite running in the
    # same coordinate. U is normalised to the drawn width, so one U-lane is
    # `2*half_width / lanes` — 5.12 m on a widened two-lane street — while
    # this divides by the *authored* 3.20 m. Measured on the shipped mesh, a
    # 0.5 m kerb is drawn 0.15625 U wide, which is 0.800 m at the
    # carriageway's own scale: out by exactly the 1.60x widening. Harmless
    # today because nothing reads a kerb's U — the markings shader excludes
    # the class outright — and left alone rather than corrected because
    # changing it moves shipped UVs for no visible gain. `_u_metres` is the
    # honest conversion, and the one to use for anything that has to land in
    # a real place.
    outside = kerb / lane_width_m
    lanes = float(edge.lanes)

    # Each boundary is stopped on its own account. The kerb stays welded to the
    # carriageway because the two share vertex indices, not positions — so a
    # corner that holds the road edge still and the kerb line moving simply
    # makes the lip wider there, which is what a real kerb does on a tight bend.
    left = _lift(edge.left, points, 0.0)
    right = _lift(edge.right, points, 0.0)
    left_top = _lift(edge.left, points, rise)
    right_top = _lift(edge.right, points, rise)
    left_out = _lift(edge.lip_left, points, rise)
    right_out = _lift(edge.lip_right, points, rise)

    # Rail order is the winding: `strip` faces out of the cross product of its
    # own along and across directions, so the two kerbs — being mirror images —
    # take their pairs in opposite orders. The carriageway is right-then-left
    # for the same reason. `test_surface.py` pins every one of these facings.
    # `COLOR_0.a` carries the restriction extent, and it lands on the right rail
    # because that rail *is* the offside kerb — `_rgba`'s note has the rest.
    # Published metres, so the trim comes back on: the runs were measured along
    # the graph's polyline and this is the ribbon after both ends were cut.
    published = along + edge.trim_start_m
    builder.strip(
        right,
        left,
        colour=style.surface_material.colour,
        along=along,
        across=(lanes, 0.0),
        marking=carriageway,
        alpha=(_extent(edge, OFFSIDE, published), _extent(edge, NEARSIDE, published)),
    )

    # The riser has no plan width, so both its rails sit at the kerb line and
    # share its U. The lip is where U crosses the kerb — putting the ramp on the
    # riser instead would make an integer U stop meaning a lane boundary.
    #
    # Drawn in runs, because a kerb another carriageway has already covered is
    # not drawn at all — see `_hide_buried_kerbs`. A side with no mask yet is a
    # side nothing was asked about, and keeps the whole kerb it always had.
    #
    # ⚠️ **On fewer stations than the carriageway**, since the kerb reads none
    # of what the extra ones carry — `_rail_stations` has the argument and the
    # measurement. The runs are resolved once and both used and pinned from the
    # same list, which is what makes the `searchsorted` below exact rather than
    # nearest: a second derivation of them would not have to agree.
    #
    # ⚠️ Only the four *distinct* rails are offered for measurement. `left_top`
    # is `left` plus a constant height and `right_top` is `right` plus one, and
    # `_off_line` differences its input, so the two would return answers the
    # `maximum` already has.
    kerbs = [
        _runs(keep) if keep is not None else [(0, len(points))]
        for keep in (edge.kerb_left, edge.kerb_right)
    ]
    stations = _rail_stations(
        points, kerbs[0] + kerbs[1], (left, left_out, right, right_out), report
    )
    kerb_along = along[stations]
    near, near_top, near_out = left[stations], left_top[stations], left_out[stations]
    off, off_top, off_out = right[stations], right_top[stations], right_out[stations]
    for runs, lower, upper, across in (
        (kerbs[0], near, near_top, (0.0, 0.0)),
        (kerbs[0], near_top, near_out, (0.0, -outside)),
        (kerbs[1], off_top, off, (lanes, lanes)),
        (kerbs[1], off_out, off_top, (lanes + outside, lanes)),
    ):
        for start, stop in runs:
            low = int(np.searchsorted(stations, start))
            high = int(np.searchsorted(stations, stop - 1)) + 1
            builder.strip(
                lower[low:high],
                upper[low:high],
                colour=style.kerb_material.colour,
                along=kerb_along[low:high],
                across=across,
                marking=kerb_marking,
            )
    return True


def _extent(edge: _Edge, side: str, published: np.ndarray) -> np.ndarray:
    """`COLOR_0.a` for one rail: 255 where a restriction runs, 0 where none does.

    Two values and no third, because the alpha says *where* and the codec says
    *what* — a byte that also carried the kind would have to be read through a
    threshold that the across-the-road interpolation moves.

    Read at the stations `_insert_stations` put there, so an edge whose
    restriction starts mid-block has a station 0.25 m either side of that point
    and the ramp between them is half a metre. Without those this would still be
    correct and would still look wrong: the value is right at every station and
    linear in between.
    """
    inside = np.zeros(len(published), dtype=bool)
    for start, stop in edge.restrictions.get(side, ()):
        inside |= (published >= start) & (published <= stop)
    return np.where(inside, 255, 0).astype(np.uint8)


def _through_corners(group: list[_End], edges: list[_Edge]) -> list[list[np.ndarray]]:
    """Mitred corners for every movement that runs *through* a node.

    The hull of the arm mouths alone is a chord across the turn, so at a bend it
    cuts the outside of the corner off and the road pinches to `cos(half the
    turn)` of its width — in the one place a car is already committed to it. The
    region's worst is BULLOCK LANE into CROSS LANE, where two 10.2 m arms meet
    at 62 degrees and leave a 7.1 m waist.

    Feeding the mitre apexes into the same hull repairs that without a second
    kind of cap. The hull can only grow, and where the two arms are collinear
    the apex lands on the boundary it already had — so a crossroads, where the
    through movements are straight, comes out byte for byte unchanged.

    Which movements qualify is the whole question, and it is not a tuning value:
    filling the corner between two arms of a real junction would pave the
    pavement, which is exactly what `hull` was chosen to avoid.

    One `(4, 3)` array per mitred movement, so the caller can both count them
    and `vstack` them without knowing how many points each carries.
    """
    arms: list[_Arm] = []
    for end in group:
        points = edges[end.edge].points
        step = points[1] - points[0] if end.at_start else points[-1] - points[-2]
        plan = step[[0, 2]]
        length = float(np.hypot(*plan))
        if length <= _MIN_SEGMENT_M:
            continue
        # Away from the node, whichever end of the polyline arrives on it.
        away = plan / length * (1.0 if end.at_start else -1.0)
        half_width_m = edges[end.edge].end_half_width_m(end.at_start)
        arms.append(_Arm(away, half_width_m, points[0 if end.at_start else -1, :3]))
    if len(arms) < 2:
        return []

    node = np.mean([arm.node for arm in arms], axis=0)
    limit = _BEND_TURN_DEG if len(arms) == 2 else _THROUGH_TURN_DEG
    movements: list[np.ndarray] = []
    for index, first in enumerate(arms):
        for second in arms[index + 1 :]:
            # A car arrives against `first.away` and leaves along `second.away`,
            # so the two arms read as one street exactly when they point apart.
            turn = np.degrees(np.arccos(np.clip(-float(first.away @ second.away), -1.0, 1.0)))
            if turn > limit:
                continue
            # The joint is an interior vertex of a polyline that happens to span
            # two edges, so `mitres` computes it rather than this function
            # holding a second opinion about where a mitre goes — and, more to
            # the point, a second copy of `_MITRE_LIMIT`.
            apex = mitres(np.array([node + _out(first.away), node, node + _out(second.away)]))[1]
            # Both half-widths, because two arms of a movement may differ in
            # width and the mouth of each has to be reached.
            movements.append(
                np.array(
                    [
                        [node[0] + side[0], node[1], node[2] + side[1]]
                        for half in (first.half_width_m, second.half_width_m)
                        for side in (apex * half, -apex * half)
                    ]
                )
            )
    return movements


def _out(plan: np.ndarray) -> np.ndarray:
    """A plan direction as an x/y/z step, flat, for handing to a 3D routine."""
    return np.array([plan[0], 0.0, plan[1]])


def _cap_ring(group: list[_End], edges: list[_Edge], report: SurfaceReport) -> np.ndarray | None:
    """The junction polygon closing one node at one level, or None if there is none.

    Built from the two carriageway corners each ribbon presents to the node, so
    the cap meets every arm along that arm's full width — plus, since the
    junction pinch was reported from the driver's seat, the mitre apex of every
    movement that runs through rather than turning off. `_through_corners` has
    the argument; here it is enough that both kinds of point go into one hull,
    so there is still exactly one cap and one way of building it.

    ⚠️ It **overlaps** those arms rather than abutting them, wherever they stop
    at different distances from the node — which they do whenever
    `junction_trim_max_fraction` holds a short edge back, 210 of the region's
    1,398 trimmed ends. An arm's mouth is then inside the hull and the cap
    re-covers ribbon that already exists: measured at 6,051 m2 of 52,985 m2 of
    cap area. Harmless today, because cap and carriageway are the same colour at
    the same height in the same material, so the coplanar pair cannot be told
    apart. It stops being harmless when `docs/ART_DESIGN.md`'s markings shader
    lands, since a cap carries no lane coordinate and the ribbon under it does.
    Fixing it properly means a non-convex cap — the union boundary rather than
    the hull — which is polygon clipping, and is not worth building blind.

    A group of one is a
    ribbon with nothing to join to — a map edge, or a ramp dead-ending against a
    deck it cannot reach — and gets no cap and no trim.
    """
    if len(group) < 2:
        return None
    corners = [
        corner
        for end in group
        for on_left in (True, False)
        if (corner := edges[end.edge].corner(end.at_start, on_left=on_left)) is not None
    ]
    if len(corners) < 3:
        return None
    through = _through_corners(group, edges)
    report.through_movements += len(through)
    ring = hull(np.vstack(corners + through))
    return ring if len(ring) >= 3 else None


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _write_manifest(out_dir: Path, city: CityConfig, region_id: str, report: SurfaceReport) -> None:
    """An intermediate for `P1-6`, not the game-facing contract.

    Same reasoning as `buildings.json`: `city.json` is `export.py`'s to write,
    and this records only what the surface stage knows so the two stages stay
    independently runnable.

    `carriageway` is the exception worth naming: it is the only thing here the
    *game* needs rather than the next stage. `roadgraph.json` publishes the
    the graph's own `width_m` — measured since `Q95` where the publishers licensed it —
    while the ribbon is drawn at
    `max(width_m, floor_for(...))` — so a runtime asking "where is the nearside
    lane?" from the graph alone lands short of the lane by a quarter of the
    widening. The factor stays on the surface style, where `config.py` says it
    belongs; the *result* travels, through `export.py`, into `city.json`.
    Off-grade edges are the case where the two coincide, drawn at their authored
    width so the ribbon stays on its deck; a consumer must read this table
    rather than assume the drawn width exceeds the authored one.

    **One value per station since `Q23`**, indexed by that edge's
    `roadgraph.json` polyline. A road becomes a bridge partway along an edge, so
    a single number could not describe 28 of the region's edges without being
    wrong along part of every one of them — and the widening is exactly the
    quarter that would put a car 0.96 m off its lane. The taper between the two
    widths is applied here rather than published as a rule, so the mesh and the
    lane centre cannot disagree about where it runs.

    `trim_m` is the other thing only this stage knows: `[start, end]` metres held
    back from each end so the junction cap can fill the middle. It travels for
    `clearance.py`, which measures a cross-section per station and must not judge
    the ones the ribbon never reached. It stays an intermediate — the game reads
    the *result* of that measurement, never the trims.

    `caps` is the third (`Q92`), and the one a *marking* stage needs: each
    junction cap's hull ring in x/y/z, which with the ribbon heights is the whole
    of the drawn surface. `DrawnSurface` is the reader; `SurfaceReport.cap_rings`
    is why it is published rather than re-derived.
    """
    write_document(
        out_dir / SURFACE_MANIFEST_NAME,
        {
            "schema_version": SURFACE_MANIFEST_SCHEMA,
            "city_id": city.id,
            "region_id": region_id,
            "mesh": SURFACE_NAME,
            "mesh_name": SURFACE_MESH_NAME,
            "triangles": report.triangles,
            "vertices": report.vertices,
            "bytes": report.bytes,
            "aabb": report.aabb,
            "carriageway": [
                {
                    "edge": edge_id,
                    "half_width_m": halves,
                    "trim_m": list(report.trims_m.get(edge_id, (0.0, 0.0))),
                    "kerb_hidden_m": report.kerb_hidden_m.get(edge_id, {}),
                }
                for edge_id, halves in sorted(report.carriageway.items())
            ],
            # ⚠️ **Written open, exactly as `_Builder.fan` receives it** — no
            # repeated closing vertex — because the consumer rebuilds the same
            # fan, and a duplicated last corner is one collapsed triangle it
            # would test against every query.
            "caps": [
                {"level": level, "ring": [round_position(tuple(corner)) for corner in ring]}
                for level, ring in report.cap_rings
            ],
        },
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    report = build_region(city, args.region)
    log.info(
        "%d edges and %d junction caps: %d triangles, %d vertices, %.1f MB",
        report.edges,
        report.junctions,
        report.triangles,
        report.vertices,
        report.bytes / 1e6,
    )
    log.info(
        "  %d ends trimmed back from a junction, %d of them clamped by edge length",
        report.trimmed_ends,
        report.clamped_trims,
    )
    log.info(
        "  %d movements run through a node and were mitred into its cap",
        report.through_movements,
    )
    if report.buried_kerb_m:
        log.info(
            "  %.0f m of kerb dropped where a neighbouring carriageway already covered it",
            report.buried_kerb_m,
        )
    if report.on_structure_m:
        log.info(
            "  %.0f m of level-0 carriageway sits on structure and is drawn at its authored "
            "width — Q23",
            report.on_structure_m,
        )
    if report.kerb_stations:
        log.info(
            "  %d stations inserted at kerbside restriction boundaries, %d of them kept on a "
            "kerb rail (worst %.2g m off the line); %.0f m of kerb drawn as the wrong kind of line",
            report.kerb_stations,
            report.kerb_rail_stations,
            report.kerb_rail_offset_m,
            report.kerb_minority_m,
        )
    if report.inverted:
        log.info(
            "  %d triangles still fold inward at a hairpin, covering %.2f m2",
            report.inverted,
            report.inverted_area_m2,
        )
    if report.level_changes:
        steps = report.level_steps_m
        log.warning(
            # Upper median on an even count, which needs no averaging and cannot
            # report a step no node actually has.
            "  %d nodes step between elevation levels: %d inside 0.5 m, median %.2f m, "
            "up to %.1f m — see Q13",
            report.level_changes,
            sum(1 for step in steps if step <= 0.5),
            steps[len(steps) // 2],
            report.max_level_step_m,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
