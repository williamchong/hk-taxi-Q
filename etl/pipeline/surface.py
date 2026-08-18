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
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import numpy as np

from pipeline.config import BOTH, FORWARD, CityConfig, RoadSurface, load_city
from pipeline.documents import write_document
from pipeline.geometry import edge_distances, inside_polygon
from pipeline.gltf import Bounds, MeshData, normalise, write_glb
from pipeline.mesh import select_triangles
from pipeline.roads import ROADGRAPH_NAME, plan_lengths, plan_steps, read_graph

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
SURFACE_MANIFEST_SCHEMA = 4

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
#        + 1024*offside_kerb + 2048*centre
#
# Max legal code is 131,071, far inside float32's 24 exact bits.
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
# Derived rather than written down: adding a field means moving one line, not
# remembering to move two. `centre` is the top field and holds six bits.
MARKING_CODE_MAX = MARKING_CENTRE * (MARKING_CENTRE_MAX + 1) - 1
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

# Below this, a triangle has collapsed and is dropped. Compared against *twice*
# the area, which is what the cross product's length gives — a square millimetre
# of road is not road, and a collision shape built from degenerate triangles is
# a collision shape with holes in it.
_MIN_TWICE_AREA_M2 = 1e-6

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


@dataclass
class SurfaceReport:
    edges: int = 0
    # Drawn half-width per graph edge id, in metres, **one value per station of
    # that edge's published polyline**. Recorded rather than recomputed
    # downstream: `_prepare` is the one place the widening is applied, and a
    # second evaluation of `widen_for` is a second thing to keep in step with
    # the config.
    carriageway: dict[int, list[float]] = field(default_factory=dict)
    # Metres held back from each end of an edge's ribbon so a junction cap can
    # fill the middle, keyed by graph edge id as `(start, end)`. Recorded for the
    # same reason as `carriageway`: `_assign_trims` is the one place the trim is
    # decided, and a downstream re-derivation would be a second thing to keep in
    # step with the junction rule.
    trims_m: dict[int, tuple[float, float]] = field(default_factory=dict)
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
        self._colours.append(_rgba(colour, 2 * span))
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


def _rgba(colour: tuple[int, int, int], count: int) -> np.ndarray:
    """One RGBA row per vertex, as a read-only view rather than a copy.

    `_Builder.build` materialises it in the one `vstack` that needs it — the
    same reasoning as `buildings.colour_for`.
    """
    return np.broadcast_to(np.array([*colour, 255], dtype=np.uint8), (count, 4))


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

    `points` is `(N, 4)`: x, y, z and the station's half-width — see `_WIDTH`.
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

    edges = [_prepare(edge, style) for edge in graph["edges"]]
    report = SurfaceReport()
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
    _read_offside(graph["edges"], edges, report)

    builder = _Builder()
    for edge in edges:
        if _draw_edge(builder, edge, style, city.roads.lane_width_m):
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


def _prepare(published: dict, style: RoadSurface) -> _Edge:
    """One published edge as a ribbon-in-waiting, half-widths already resolved.

    The widths are computed against the **published** polyline, before `dedupe`
    drops anything, so `report.carriageway` and `roadgraph.json` index alike —
    which is the contract the game reads them under.
    """
    half_widths = _half_widths(published, style)
    points = dedupe(np.column_stack([_polyline(published), half_widths]))
    return _Edge(
        points=points,
        published_half_widths=half_widths,
        lanes=published["lanes"],
        direction=published["direction"],
        bus_lane=bool(published["bus_lane"]),
        tram_tracks=bool(published["tram_tracks"]),
        level=published["elevation_level"],
        length_m=float(plan_lengths(points)[-1]) if len(points) > 1 else 0.0,
    )


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
    at_grade = style.widen_for(limit, elevation_level=level)
    on_deck = style.widen_for(limit, elevation_level=level, on_structure=True)

    flags = np.asarray(published["on_structure"], dtype=bool)
    if at_grade == on_deck or not flags.any():
        return np.full(len(flags), published["width_m"] * at_grade / 2.0)

    along = plan_lengths(_polyline(published))
    gap = np.abs(along[:, None] - along[flags][None, :]).min(axis=1)
    # A zero taper is the literal reading — width changes at the boundary and
    # nowhere else — and it has to stay reachable rather than dividing by zero,
    # because it is what a city with a hard kerb line beside its viaducts wants.
    blend = (gap <= 0.0) if style.structure_taper_m <= 0.0 else 1.0 - gap / style.structure_taper_m
    blend = np.clip(blend, 0.0, 1.0)
    return published["width_m"] * (at_grade + (on_deck - at_grade) * blend) / 2.0


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


def _runs(keep: np.ndarray) -> list[tuple[int, int]]:
    """Station ranges for each run of consecutive kept segments.

    `keep` carries one flag per quad, so a run of `n` of them is a strip over
    `n + 1` stations and can never be too short to draw. A kerb that survives in
    pieces is drawn as pieces: the cut ends leave the riser open, which is
    invisible and unreachable, since whatever buried the kerb still lies over it.
    """
    changes = np.flatnonzero(np.diff(np.concatenate([[False], keep, [False]]).astype(np.int8)))
    return [(int(start), int(stop) + 1) for start, stop in changes.reshape(-1, 2)]


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


def _draw_edge(builder: _Builder, edge: _Edge, style: RoadSurface, lane_width_m: float) -> bool:
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
    builder.strip(
        right,
        left,
        colour=style.surface_material.colour,
        along=along,
        across=(lanes, 0.0),
        marking=carriageway,
    )

    # The riser has no plan width, so both its rails sit at the kerb line and
    # share its U. The lip is where U crosses the kerb — putting the ramp on the
    # riser instead would make an integer U stop meaning a lane boundary.
    #
    # Drawn in runs, because a kerb another carriageway has already covered is
    # not drawn at all — see `_hide_buried_kerbs`. A side with no mask yet is a
    # side nothing was asked about, and keeps the whole kerb it always had.
    for keep, lower, upper, across in (
        (edge.kerb_left, left, left_top, (0.0, 0.0)),
        (edge.kerb_left, left_top, left_out, (0.0, -outside)),
        (edge.kerb_right, right_top, right, (lanes, lanes)),
        (edge.kerb_right, right_out, right_top, (lanes + outside, lanes)),
    ):
        for start, stop in _runs(keep) if keep is not None else [(0, len(points))]:
            builder.strip(
                lower[start:stop],
                upper[start:stop],
                colour=style.kerb_material.colour,
                along=along[start:stop],
                across=across,
                marking=kerb_marking,
            )
    return True


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
    authored street width, `lanes x lane_width_m`, while the ribbon is drawn at
    `width_m x widen_for(...)` — so a runtime asking "where is the nearside
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
                }
                for edge_id, halves in sorted(report.carriageway.items())
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
