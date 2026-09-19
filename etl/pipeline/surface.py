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
import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

from pipeline import surface_region
from pipeline.boxsource import BoxReading, read_boxes
from pipeline.buildings import Grid, tile_id
from pipeline.config import (
    BOTH,
    FORWARD,
    KERB_DOUBLE,
    KERB_SINGLE,
    Config,
    RoadSurface,
    load_config,
)
from pipeline.documents import round_position, write_document
from pipeline.geometry import clip_half_plane, edge_distances, inside_polygon
from pipeline.gltf import (
    COLLISION_ONLY_SUFFIX,
    Bounds,
    MeshData,
    normalise,
    read_render,
    write_glb,
)
from pipeline.kerbside import NEARSIDE, OFFSIDE
from pipeline.mesh import merge, select_triangles
from pipeline.meshbuild import MIN_TWICE_AREA_M2, thin_in_plan
from pipeline.polyline import plan_lengths, plan_steps, true_runs
from pipeline.roads import ROADGRAPH_NAME, Ownership, read_graph

# ⚠️ **The barycentric point-in-triangle test is `terrain`'s, not a fourth copy.**
# `deck_error.py` books its own copy as a known cost — importing the pipeline
# would drag GDAL into a hand-run tool — and that argument does not reach here:
# `pipeline.terrain` imports numpy and `pipeline.gltf` alone, and `pipeline.roads`
# above already pulls it in. `Q58`'s rule is that a third copy should force it.
from pipeline.terrain import Prepared, covered_prepared, prepare

log = logging.getLogger(__name__)

# The drawn road ships as one `.glb` per tile of the building grid, under this
# directory (`P5-6`). There is no region-wide `roads.glb` any more: the one
# there was could not be culled or streamed, because Godot culls per
# `MeshInstance3D` by AABB and a region-wide ribbon is one AABB spanning
# ~1,660 m in three of four measured regions (`Q120`). `read_surface` merges the
# chunks back into that one mesh for anything that wants to measure the road
# whole, which is every grader and most tests.
SURFACE_DIR = "roads"
SURFACE_MANIFEST_NAME = "roadsurface.json"
# 8 since `P5-6`: the mesh is CHUNKED. `mesh` is gone and `chunks[]` names one
# file per tile — `id` (the building tile's own id), `file`, `triangles`,
# `vertices`, `bytes`, `aabb` — with `cut_vertices` saying how many vertices the
# cut duplicated. A reader that keeps opening `mesh` opens a file that no longer
# exists, which is the loud half; the quiet half is a reader summing `vertices`
# over the chunks and calling it the mesh's, which is `cut_vertices` too high.
# 7 since `Q107`: `carriageway[].offset_m` is a **list**, one value per station
# of that edge's published polyline, saying where the drawn ribbon is centred in
# `mitres`' LEFT-of-travel frame. 🔴 **A reader that keeps taking
# `half_width_m` as a half-width about the centreline is wrong about every
# off-grade edge** — the two rails are now cut to the deck independently, so the
# ribbon is asymmetric and `half_width_m` is half the distance *between the
# rails*. That is hard rule 5's test, and `Q106` is what it costs: four tools
# reconstructed the road from a half-width alone and all four were wrong.
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
# 9 since `P5-12`: every chunk `.glb` holds TWO primitives — the render mesh,
# no longer suffixed `-col`, and a `road_surface_collision-colonly` collider —
# and each chunk row carries `collision_triangles`. A v8 reader taking the
# file's meshes as the drawn road measures every quad twice.
# 10 since `P3-32`'s residue: `ribbons` publishes every drawn carriageway
# strip's two rails, in the order `_Builder.strip` received them, and
# `DrawnSurface` reads the strip's own triangles instead of the nearest
# centreline's station height. A v9 reader keeps a ribbon that is flat across,
# infinitely wide and owned by whichever centreline is nearest — all three
# false, and eleven box-junction triangles under the road for it.
# 11 since `Q125`: `opposed_pairs` publishes which two edges are the halves of
# one dual carriageway and how far apart they run. A v10 reader has no way to
# know where the two flows meet, so it draws the centre line only where TD
# surveyed one — which is the defect `Q125` closes, on 58 of this region's 95
# pairs.
SURFACE_MANIFEST_SCHEMA = 12

# The drawn road's primitive, in every chunk. ⚠️ **No `-col` since `P5-12`**:
# the collider is its own `-colonly` primitive beside it (`SURFACE_COLLIDER_NAME`),
# built by `_road_collider` from the same triangles today and free to diverge —
# the seam `Q121` asked for. Naming the collider in the asset rather than
# building the shape in GDScript at load keeps the collision part of the asset,
# which is what `P1-4` is asked to deliver.
SURFACE_MESH_NAME = "road_surface"
SURFACE_COLLIDER_NAME = f"road_surface_collision{COLLISION_ONLY_SUFFIX}"


def chunk_path(tile: str) -> str:
    """Where a tile's road chunk is written, relative to the region's out dir."""
    return f"{SURFACE_DIR}/{tile}.glb"


def read_surface(bundle: Path, chunks: Iterable[dict[str, Any]]) -> MeshData:
    """The drawn road as ONE mesh, merged back from its chunks.

    `chunks` is either `roadsurface.json`'s `chunks` or `city.json`'s
    `road_surface`; both carry `file` relative to `bundle`. The merge is a plain
    concatenation, so every triangle, attribute and winding is the chunk's own
    and only the vertex numbering changes — a station the cut duplicated is two
    vertices here where the un-chunked build had one, and `cut_vertices` in the
    manifest is exactly that difference.

    Sorted by file so the merged vertex order does not depend on the order a
    manifest happened to list its chunks in.
    """
    meshes = [
        read_render(bundle / str(chunk["file"]))[0]
        for chunk in sorted(chunks, key=lambda c: str(c["file"]))
    ]
    if not meshes:
        raise ValueError(f"{bundle}: the manifest names no road chunks")
    return replace(merge(meshes, name=SURFACE_MESH_NAME), material=SURFACE_MATERIAL)


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
# The layout followed the tiles' `facade_state` codec, for the same reasons —
# one non-negative integer per vertex and the whole code exact in float32, so a
# consumer decodes it with `floor(x + 0.5)`. ⚠️ That codec is gone with the
# vision reader (`Q102`), which leaves this one the surviving example.
#
# ⚠️ **The "every field's 0 means absent" half did NOT carry over, and the
# difference is load-bearing.** It held for every field of `facade_state`; here
# it holds for `direction`, `bus_lane`, `tram`, `offside_kerb`, `centre` and
# both kerb fields — but `class` 0 is `MARKING_CLASS_CARRIAGEWAY`, a real value
# and the one the shader cannot do without, and `lanes` refuses 0 outright.
#
#   code = surface_class + 4*lanes + 64*direction + 256*bus_lane + 512*tram
#        + 1024*offside_kerb + 2048*centre + 131072*kerb_near + 524288*kerb_off
#        + 2097152*lanes_forward
#
# 🔴 **Max legal code is 8,388,607, and that is the channel FULL** (`Q126`).
# The promise is not that a code is exact in float32 — integers are, up to
# 2^24 — but that the consumer's `floor(x + 0.5)` is: halves are exact only
# below 2^23, and above it an odd code plus a half rounds to even and decodes
# as its neighbour, class and all. `lanes_forward` is the two bits between the
# old ceiling and that one, so the next field needs another channel.
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
# How many of `lanes` carry the edge's own direction (`Q126`), so the shader
# draws a two-way road's centre line where its two flows actually part rather
# than at `lanes / 2` — which, on the three-lane street a row of arrows
# resolves WAN CHAI ROAD to, is the middle of the right-turn lane. 0 is "not
# said": a one-way edge, or a two-way count nobody split, and the shader keeps
# the middle it always drew. Two bits, because two is what the decode leaves —
# see the block above — and 3 forward lanes on a two-way single carriageway is
# already past anything TPDM lets one be. ⚠️ **A split past that is written
# as 0 and counted (`lanes_forward_unsaid`), not raised over**: the road still
# draws, at its old middle, and the count says how often the field was short.
MARKING_LANES_FORWARD = 2097152
MARKING_LANES_FORWARD_MAX = 3
# Derived rather than written down: adding a field means moving one line, not
# remembering to move two. `lanes_forward` is the top field and holds two bits.
MARKING_CODE_MAX = MARKING_LANES_FORWARD * (MARKING_LANES_FORWARD_MAX + 1) - 1
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

# Station pitch inside a box junction, in metres, so the flank a ribbon grows
# out to the paint edge follows that edge rather than chording between the
# graph's own vertices 10 m apart. Two metres is `_KERB_STATION_M`'s order and
# well under any box edge a driver can see; the stations lie on the polyline
# and move nothing in plan (`_insert_stations`). ⚠️ In height a mitred rail
# moves off its old chord, as `_off_line` records and as the kerb stations
# already do — 1-7 cm on the steep bends under the WAN SHING STREET and HKCEC
# boxes, where paint placed on the graph's chord now reads buried (`Q104`).
_PAINT_STATION_M = 2.0

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
# `MIN_TWICE_AREA_M2`'s way.
_KERB_STATION_M = 0.25

# The collapse bar is shared: see `meshbuild.MIN_TWICE_AREA_M2`.

# Plan grid `DrawnSurface` bins the drawn pieces — junction caps and carriageway
# strips — into. A cap is a junction's worth of tarmac — tens of metres across
# at the interchange, a few in a back lane — and a strip is one edge's ribbon,
# so this is sized to the *small* end: an oversized cell puts every piece in the
# region's centre cell and turns the point query back into a linear scan, while
# an undersized one only costs a few more dictionary entries. Its own constant
# rather than `deck_error`'s 8 m, because that grid indexes triangles and this
# one indexes whole pieces.
_DRAWN_CELL_M = 16.0
# How far `DrawnSurface._nearest_edge` will widen its search, in cells, before
# calling the query a bug: further from every drawn thing than a region is wide.
_MAX_VOID_RINGS = 256

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

# Columns of `_Edge.points` holding the deck's two edges at that station, in
# `mitres`' LEFT-of-travel frame and measured from the published centreline — so
# the structure occupies `[-points[_RIM_RIGHT], +points[_RIM_LEFT]]`. From
# `roadgraph.json`'s `deck_rim_m` (schema 10, `Q107`).
#
# Columns for `_WIDTH`'s reason, and the reason bites hardest here: the clamp
# below is per station, so a rim that failed to follow a trim or an inserted
# station would cut the ribbon at the wrong place — which draws a perfectly
# good carriageway one station to the side of where the deck is.
#
# 🔴 **Absence is `inf`, never 0.0, and that is what makes the clamp inert.**
# Every level-0 edge and every off-grade edge the deck walk could not measure
# publishes no rims; an infinite reach is "no constraint", so `min(shift + half,
# inf)` is exactly the unclamped ribbon and the whole at-grade network is
# untouched by construction rather than by a branch. A 0.0 default would collapse
# every one of them to nothing.
_RIM_LEFT = 5
_RIM_RIGHT = 6

# Columns of `_Edge.points` saying whether that side of the station ends at a
# KERB — 1.0 — or in another centreline's share of the same asphalt, which takes
# no kerb (`Q129`, `P3-33c`). From `carriageway_region.json`'s end kinds; 1.0
# throughout on an edge with no territory, which is the kerb every ribbon had.
#
# Columns for `_WIDTH`'s reason. ⚠️ Read as `>= 0.5`: `_at` lerps every column, so
# a station inserted between a kerb and a share arrives carrying a fraction.
_KERB_LEFT = 7
_KERB_RIGHT = 8

# The percentile of a territory's span its painted lane count has to fit in.
# `carriageway.DECK_WIDTH_PERCENTILE`'s value restated rather than imported: that
# one reduces a deck to a WIDTH and this one only ever refuses a count, and a
# change to either should be a decision about that one.
_LANE_SPAN_PERCENTILE = 10.0

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
    # 🔴 **Where each station's ribbon is CENTRED, beside how wide it is
    # (`Q107`).** Since the clamp the two rails are cut to the deck
    # independently, so the ribbon is not symmetric about the published
    # centreline and `carriageway` alone cannot describe it. `Q106` is what a
    # missing offset costs: four instruments rebuilt the road from a half-width
    # about a centreline the paint had left, and every one was wrong about the
    # off-grade network.
    carriageway_offset: dict[int, list[float]] = field(default_factory=dict)
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
    # Every drawn carriageway strip's two rails, as `(edge id, level, (rail,
    # rail))` with the rails **in the order `_Builder.strip` received them**
    # (`P3-32`'s residue). Recorded where `_draw_edge` lifts them, so the
    # record and the drawing are one pair of arrays: a marking stage that
    # rebuilt the rails from `carriageway[]` would lose the mitre's
    # along-displacement, which is exactly the centimetre `_off_line` measures.
    ribbon_rails: list[tuple[int, int, tuple[np.ndarray, np.ndarray]]] = field(default_factory=list)
    # The level-0 carriageway that is no ribbon (`Q129`, `P3-33c`): `R` less
    # every ribbon, as `(n, 3, 3)` triangles facing up. Published for the reason
    # `cap_rings` is — `DrawnSurface` rebuilds the drawn surface from the
    # manifest, and these are drawn — and it is what the hull caps, the through
    # corridors and the paint flanks were at level 0.
    area_triangles: np.ndarray = field(default_factory=lambda: np.zeros((0, 3, 3)))
    # Level-0 edges whose rails are their territory, and the published stations
    # of those with NO territory, which keep the plain `width_m` ribbon — a run
    # past its region's rectangle (`Q116`). Reachable, so a rise is a finding.
    territory_edges: int = 0
    territory_fallback_stations: int = 0
    # Level-0 edges that HAVE a territory whose `vertex_station` does not index
    # this polyline — `carriageway_region.json` built off another graph than the
    # one being drawn. The edge keeps the plain `width_m` ribbon, whole, which is
    # the invented width back and renders as a road; silent until `P3-35c`.
    # Must be 0: `region` runs before `surface`, so only a stale file reaches it.
    territory_mismatched_edges: int = 0
    # Level-0 edges of this region's own with NO territory row at all, drawn as
    # the plain `width_m` ribbon — `region.json`'s `edges_without_territory` seen
    # from the side that draws it. A run wholly past the rectangle is the
    # ordinary case (`Q116`), so this is reported and not required to be 0.
    territory_missing_edges: int = 0
    # Metres of kerb drawn along an AREA's edge — the junction corners and bays no
    # ribbon's rail runs along. Zero with areas drawn is every corner kerbless.
    area_kerb_m: float = 0.0
    # Kerbed islands standing in the carriageway, each ringed and topped — the
    # ones a rail was read through lie UNDER a ribbon (`Q131`).
    islands: int = 0
    # Territory edges whose PAINTED lane count was cut to what their share can
    # carry at TPDM's narrow lane. One-sided; reachable at zero.
    territory_lanes_capped: int = 0
    # Per territory edge, `(half widths, offsets)` of the kerb-to-kerb corridor at
    # each published vertex — `carriageway`'s shape and frame, a second extent.
    corridor: dict[int, tuple[list[float], list[float]]] = field(default_factory=dict)
    # The lane count each territory edge is PAINTED with, keyed by edge id — the
    # graph's `lanes` under `territory_lanes_capped`'s ceiling. Published because
    # `tools/lane_paint.py` grades the strip the shader paints, and that strip is
    # cut by this count and not by the graph's.
    lanes_painted: dict[int, int] = field(default_factory=dict)
    junctions: int = 0
    # The region join (`P5-7f`, `Q116`'s one exception): ends of the
    # neighbour's runs offered to the cap hull, caps that took one, and caps
    # refused because their node lies in the neighbour — whose build draws them.
    foreign_ends: int = 0
    caps_with_foreign_mouth: int = 0
    caps_in_neighbour: int = 0
    # `P3-31`: edges clamped at both ends (`_Edge.is_stub`), the clusters of
    # nodes those stubs join, and the nodes in them. A cluster is capped once,
    # so `junctions` falls by `cluster_nodes - clusters` against the per-node
    # count. 🔴 **`clusters` is reachable at zero** — raise
    # `junction_trim_max_fraction` until no ceiling binds and every node is
    # capped on its own again — which is what makes it a counter rather than a
    # tautology (`Q72`); `test_a_looser_ceiling_dissolves_the_cluster` is the
    # mutation.
    stub_edges: int = 0
    clusters: int = 0
    cluster_nodes: int = 0
    # Through corridors drawn across clusters (`P3-31`, second finding): one
    # convex quad per pair of arms at different nodes whose far axes run
    # through, drawn as a cap of its own. Reachable at zero — a cluster whose
    # arms all turn off, or none of whose arms splays — so it is a counter.
    corridors: int = 0
    # `P3-32`: the paint witness. Boxes read (after the publisher's refusals),
    # stations inserted so a ribbon follows a box edge, flank quads drawn from
    # a rail out to the paint edge, and their plan area. Reachable at zero — a
    # city without a `boxjunctions:` block, or one whose every box lies inside
    # the ribbons — so all four are counters.
    boxes_read: int = 0
    paint_stations: int = 0
    paint_flanks: int = 0
    paint_flank_m2: float = 0.0
    # Of those, the closing pieces from the last kept station to where the
    # rail leaves the box — counted apart so a closing that stops firing shows.
    paint_flank_ends: int = 0
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
    # Ends that chose a partner which did not choose them back, and so published
    # nothing. 🔴 **This is the counter that can fail**, and it is the whole
    # reason the pairing is mutual: each half computes the join in its own lane
    # coordinate, so two halves naming different partners name different lines —
    # which is the 3.9 m double line `P3-12` shipped and then removed. It is
    # reachable at zero (`test_a_one_sided_vote_publishes_nothing`) and non-zero
    # on this region, which is `Q72`'s test of a counter passed both ways.
    opposed_pairs_one_sided: int = 0
    # 🔴 **The pairs themselves, for the stage that draws the join as geometry**
    # (`Q125`). Keyed by the unordered pair of `roadgraph.json` edge ids, so each
    # pair is held once — against `opposed_pair_ends` above, which counts both
    # halves.
    #
    # ⚠️ **Written once, by `build_region`.** `_read_offside` finds the pairs by
    # list position and *returns* them rather than booking them here, because the
    # published ids are in scope only in `build_region`: a field whose keyspace
    # changed meaning partway down the stage would be one a later counter or an
    # early return could read in the wrong frame.
    #
    # ⚠️ **Not the population `centre_step` publishes.** These are every mutual
    # pair; `opposed_pairs_unpublishable` is the ones whose join the *shader*
    # cannot reach in its own lane coordinate, which is a limit on the codec and
    # not on a line drawn between two centrelines.
    opposed_pairs: dict[tuple[int, int], float] = field(default_factory=dict)
    # Movements that qualified as running through a node and had their mitre fed
    # into its cap. Reported so a predicate that stopped matching would show.
    #
    # ⚠️ **Not** a count of caps this changed. A straight-through movement
    # qualifies, and its apex lands on the boundary the hull already had — so a
    # region of pure crossroads reports a number here and draws exactly what it
    # drew before. Saying how many caps actually grew would mean hulling twice.
    through_movements: int = 0
    triangles: int = 0
    # Vertices of the mesh as BUILT, before the cut — the count the shader and
    # every attribute is stated in. `chunk_vertices` is the count after the cut,
    # summed over the chunks, and their difference is what the cut cost:
    # `cut_vertices = chunk_vertices - vertices`, published rather than derived.
    vertices: int = 0
    chunk_vertices: int = 0
    bytes: int = 0
    aabb: Bounds | None = None
    # One row per road chunk written — `id`, `file`, `triangles`, `vertices`,
    # `bytes`, `aabb` — in tile-id order. The chunk is the tile the quad's (or
    # cap's) plan centre falls in; see `_Builder.chunk`.
    chunks: list[dict[str, Any]] = field(default_factory=list)
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
    # `Q19`'s equivalent: metres of level-0 centreline with structure standing
    # *beside* it.
    #
    # 🔴 **Measured and NOT acted on**, which is the difference between this and
    # every other number in this block. `_half_widths` says why the narrowing it
    # would license was built, measured and refused. Reported so the population
    # stays visible while nothing draws on it — a flag published with no counter
    # is a flag nobody can tell has stopped being computed.
    #
    # ⚠️ **Reported beside `on_structure_m` and never summed with it.** The two
    # overlap — a deck station is usually walled as well — so a total would
    # double-count the viaducts. What the pair is for is the *gap*: metres
    # bounded but not on structure are exactly what `Q23`'s flag cannot reach.
    structure_bounded_m: float = 0.0
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
    # `Q107`. Edges that carried a deck rim at all — the population the clamp
    # can reach, and every other edge is untouched by arithmetic.
    deck_rim_edges: int = 0
    # `Q113`. Published vertices whose rim was discarded because the edge is not
    # on structure there — a descending ramp standing on the ground, whose deck
    # walk still found a sliver of slab. Counted rather than assumed silent: it
    # is the population the fix reaches, and a jump in it means the deck walk or
    # `on_structure` has moved rather than the roads having.
    deck_rim_off_structure: int = 0
    # Published stations where the clamp actually cut the ribbon. ⚠️ **Counted
    # against the published width, not against the rim**, so it says how often
    # the deck was narrower than the paint rather than how often a rim existed —
    # the second is `deck_rim_edges` and reads as the flag rather than the
    # finding (`Q58`).
    clamped_stations: int = 0
    # 🔴 **Stations where the two rails would have crossed and the ribbon was
    # left as it was.** The fallback `Q105` said any build owes: the drawn
    # ribbon lies wholly off its own deck there, so the clamp has no answer, and
    # collapsing to zero would put a hole in the road rather than a narrow one.
    # ⚠️ **A rise here is a finding to go and look at, never a bar to retune** —
    # it means more of the network is drawn off its own structure.
    clamp_refused_stations: int = 0
    kerb_minority_m: float = 0.0
    # Two-way edges whose published `lanes_forward` is past what the codec's
    # two bits can say, drawn at their old middle instead (`Q126`). 0 here and
    # reachable only by a two-way single carriageway with four lanes one way.
    lanes_forward_unsaid: int = 0

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
        needs it.
        """
        return np.broadcast_to(np.array(self, dtype=np.float32), (count, 2))


class _Builder:
    """Accumulates triangle strips and fans into one vertex-coloured mesh.

    Vertices are shared along a strip and never between strips. That is what
    keeps the road smooth along its length and hard-edged where the carriageway
    meets the kerb riser — the same flat-shaded treatment the buildings get,
    applied where it means something.
    """

    def __init__(self, grid: Grid | None = None) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._colours: list[np.ndarray] = []
        self._uvs: list[np.ndarray] = []
        self._uv2: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        # One tile key per triangle, decided as the triangle is emitted (`P5-6`):
        # a strip's quad by the plan centre of its two stations, so the cut
        # between two chunks falls exactly at a station; a cap by its centroid,
        # so a junction goes whole to one chunk. Deciding it here rather than
        # partitioning the finished mesh by triangle centroid is what makes both
        # of those true — `buildings.assign` splits by centroid and would put a
        # cap's fan across two tiles.
        self._keys: list[np.ndarray] = []
        self._grid = grid
        # The mesh `build` returned and the tile key of each triangle it kept,
        # aligned. `chunk` reads them, so the two cannot drift apart the way a
        # mesh passed back in beside a stored key array could.
        self._built: tuple[MeshData, np.ndarray] | None = None
        self._count = 0

    def _tile_keys(self, x: np.ndarray, z: np.ndarray) -> np.ndarray:
        """Tile key for plan points — `row * columns + column`, or 0 with no grid.

        Clipped into the region first, because `Grid.index` assumes a point
        already inside and clamps the far side only: a widened ribbon along the
        region's west or north edge runs a few metres into negative plan
        coordinates, and `//` alone would hand those to tile -1.
        """
        if self._grid is None:
            return np.zeros(len(x), dtype=np.int64)
        grid = self._grid
        ix, iz = grid.index(np.clip(x, 0.0, grid.max_x), np.clip(z, 0.0, grid.max_z))
        return iz.astype(np.int64) * grid.columns + ix.astype(np.int64)

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
        # Both triangles of a quad take the quad's key, in the order the two
        # triangle blocks above were appended.
        centre = (left[:-1] + left[1:] + right[:-1] + right[1:]) / 4.0
        quad_keys = self._tile_keys(centre[:, 0], centre[:, 2])
        self._keys.append(np.concatenate([quad_keys, quad_keys]))
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
        centroid = ring.mean(axis=0)
        self._keys.append(np.repeat(self._tile_keys(centroid[[0]], centroid[[2]]), len(ring)))
        self._positions.append(np.vstack([ring, centroid]))
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

    def triangles(
        self, corners: np.ndarray, *, colour: tuple[int, int, int], marking: _Marking
    ) -> None:
        """Loose triangles, `(n, 3, 3)`, already wound to face up (`P3-33c`).

        What `fan` is for a convex ring, for a surface that is not one: the
        level-0 carriageway outside every ribbon is a polygon with holes and
        reflex corners, triangulated upstream. No lane coordinate, for `fan`'s
        reason — it is no length of lane. ⚠️ Keyed per TRIANGLE where a fan goes
        whole to one chunk: an area spans a junction and the street either side
        of it, and a chunk cut through it is a partition like any other.
        """
        if not len(corners):
            return
        count = 3 * len(corners)
        self._triangles.append(np.arange(count).reshape(-1, 3) + self._count)
        centre = corners.mean(axis=1)
        self._keys.append(self._tile_keys(centre[:, 0], centre[:, 2]))
        self._positions.append(corners.reshape(-1, 3))
        self._normals.append(np.tile([0.0, 1.0, 0.0], (count, 1)))
        self._colours.append(_rgba(colour, count))
        self._uvs.append(np.zeros((count, 2), dtype=np.float32))
        self._uv2.append(marking.broadcast(count))
        self._count += count

    def build(self, name: str) -> MeshData:
        """The accumulated geometry, minus the triangles that collapsed.

        A boundary held still at a tight corner leaves a quad with two corners
        in the same place. It draws as nothing and it has no normal, so it is
        dropped here rather than shipped into a collision shape.
        """
        if self._built is not None:
            raise ValueError(f"'{name}': already built — a builder is used once")
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
        keep = twice_area > MIN_TWICE_AREA_M2
        kept = select_triangles(mesh, keep)
        if kept is None:
            raise ValueError(f"'{name}': every triangle collapsed")
        # Aligned with `kept.triangles`: `select_triangles` keeps triangle order
        # and drops nothing but the ones masked out.
        self._built = (kept, np.concatenate(self._keys)[keep])
        return kept

    def chunk(self) -> list[tuple[str, MeshData]]:
        """The mesh `build` returned, cut into one mesh per tile.

        A partition by triangle, so nothing is cut and nothing moves: every
        chunk triangle is a triangle of `mesh` with the same three positions,
        normals, colours and both `TEXCOORD`s, and two chunks that share a
        station share its vertex *positions* exactly — `select_triangles`'s own
        guarantee, and the seam gap of 0.000 m `P5-6` is accepted on. What the
        cut costs is the duplicated station vertices, which the caller counts.

        Tile-id order, so a rerun writes the same files in the same order.
        """
        if self._built is None:
            raise ValueError("chunk() before build(): nothing has been built yet")
        mesh, keys = self._built
        if self._grid is None:
            return [(tile_id(0, 0), mesh)]
        pieces: list[tuple[str, MeshData]] = []
        for key in np.unique(keys):
            piece = select_triangles(mesh, keys == key)
            if piece is None:
                continue
            ix, iz = int(key % self._grid.columns), int(key // self._grid.columns)
            pieces.append((tile_id(ix, iz), piece))
        # Tile-id order rather than key order: the keys are row-major and the
        # ids are column-major, and the manifest's readers sort by id.
        pieces.sort(key=lambda piece: piece[0])
        return pieces


class DrawnHeight(NamedTuple):
    """One `DrawnSurface` query: the height drawn, and what answered for it.

    `cap_m` is `None` where no junction cap covers the point and `ribbon_m` is
    `None` where no carriageway strip does — which is how a caller tells whether
    the caps, or the rails, were read at all: the counters that notice
    `roadsurface.json` silently losing either (`Q92`). Both `None` is a point
    over nothing drawn, and `height_m` is then the nearest drawn edge's height,
    `reach_m` away in plan; covered, `reach_m` is 0.
    """

    height_m: float
    ribbon_m: float | None
    cap_m: float | None
    reach_m: float

    @property
    def over_void(self) -> bool:
        """Whether nothing drawn covers the point."""
        return self.ribbon_m is None and self.cap_m is None


@dataclass(frozen=True)
class DrawnSurface:
    """How high the road this stage drew stands, at any plan position (`Q92`).

    🔴 **This exists because the markings were guessing, and 23.2% of the yellow
    box junctions shipped under the asphalt.** `boxjunctions.blended_height`
    gave a vertex a distance-weighted blend of level-0 *centreline* heights;
    what is drawn at a junction is a convex-hull cap fanned from the ring's own
    centroid. They are different functions and they diverge off the centreline —
    the drawn surface stood up to **0.218 m** above the blend, against a
    `lift_m` of 0.012 — so the paint sank into the road in patches, with clean
    edges, and every counter in the stage read correctly throughout.

    🔴 **And the ribbon case was still a model until `P3-32`'s residue was
    traced.** The first `Q92` reader took the caps from their published rings
    and the ribbon from *the nearest level-0 centreline's height at the
    projected station* — a ribbon that is flat across, infinitely wide, and
    owned by whichever centreline is nearest. All three are false and each put
    paint under the road: at HKCEC the nearest centreline (`e660`, 6.2 m off)
    belonged to a 5.12 m ribbon that did not reach the point, while the 7.34 m
    ribbon that did (`e659`) stood 2.6 cm higher; at HUNG HING ROAD a vertex
    over the void beside a flank took `e586`'s height from 7.8 m away, 8.8 cm
    under the flank 0.17 m from it; on WAN SHING STREET a vertex inside its
    own ribbon on a 19.6° bend at -8.8% missed the mitre's along-displacement
    (`_off_line`) by a centimetre. Eleven triangles, three mechanisms, one
    cause — so this reads the rails.

    Every drawn surface is read the way the caps always were — **the builder's
    own triangles, rebuilt from what `roadsurface.json` publishes**, so the
    height at a point is the barycentric interpolation of the triangle drawn
    there, by construction rather than by approximation:

    - **A cap** → `_fan_corners`, the fan `_Builder.fan` emits from the ring's
      centroid.
    - **A carriageway strip** → `_strip_corners`, the quad strip `_Builder.strip`
      emits between the two rails `_draw_edge` handed it — post-trim,
      post-mitre, every inserted station included.
    - **Nothing** → the height of the nearest drawn *edge*: the closest point on
      any rail segment, ribbon end or cap ring edge, found by widening rings of
      the plan grid until nothing unseen can be nearer. No centreline, no
      radius, no knob: a point over the void beside a flank takes the flank's
      edge, not a carriageway 7 m off.

    ⚠️ **Where caps and strips both cover, the higher wins**, because a cap is
    drawn over the arm it overlaps — the 6,051 m² `Q53` measured — and the
    renderer shows the higher surface. Where two *strips* stack in plan (16
    level-0 edges stand on structure here, and `e465` climbs 7.87 m) the higher
    wins for the same reason; the old reader picked whichever centreline was
    nearer, which was no rule at all. `roadmarks._on_its_own_carriageway`
    refuses a longitudinal marking there rather than trusting either answer.

    🔴 **This does not re-open the cliff `blended_height` was written to close.**
    That was a hard *nearest-edge* switch between two arms' extrapolated grades,
    disagreeing by up to 0.43 m where they met, and it produced **172
    near-vertical triangles**. Nothing here switches between models: the strip
    and the cap that meets it share their mouth corners vertex for vertex, so
    the two read the same height along the seam.

    ⚠️ **`level` is the caller's to choose and every caller passes 0**: a
    marking under a flyover takes its height from the street it is painted on,
    never from the deck above. Caps and ribbons are filtered to that level here.
    """

    # Every drawn triangle, caps and strips alike, as the builder emits it —
    # `(n, 3, 3)`, with `is_cap` saying which kind each one is — and the plan
    # grid over them: cell to the pack of triangles touching it, as `(corners,
    # is_cap)` slices ready for one `covered` call. 🔴 **Binned per TRIANGLE
    # and not per piece, and that is measured**: a piece's axis-aligned box is
    # loose on a diagonal ribbon (the worst covered 260 cells), so binning
    # pieces passed 39% of the barycentric passes on points nowhere near them
    # and made 4.3 numpy round-trips a query — 1.60 s over the region's 24,435
    # box-junction vertices against 0.44 s for one call per query on a cell's
    # own pack, for byte-identical output. The fans and strips are triangulated
    # once here, not per query, for the same reason (0.712 s → 0.258 s when the
    # caps alone were re-rolled per vertex).
    triangles: np.ndarray
    is_cap: np.ndarray
    cells: dict[tuple[int, int], tuple[Prepared, np.ndarray]]
    # Every drawn edge as a 3D segment, `(m, 2, 3)`: cap ring edges, rail
    # segments and the two end lines of each strip. What a point over nothing
    # drawn snaps to.
    edges: np.ndarray
    # Plan cell to the edge segments whose bounding box touches it.
    edge_cells: dict[tuple[int, int], np.ndarray]
    # 🔴 **Every edge of every drawn triangle, in plan and each once — the
    # CREASES of the drawn surface**, `(k, 2, 2)`: fan spokes and ring edges,
    # rails, station lines and each quad's diagonal. What `split` cuts paint
    # along, so that no piece of paint spans a fold the road has and the paint
    # does not. A superset of `edges`, kept apart because the two answer
    # different questions: `edges` is where a point over nothing snaps to, and
    # a spoke or a diagonal is not an edge of anything.
    creases: np.ndarray
    crease_cells: dict[tuple[int, int], np.ndarray]

    @classmethod
    def of(cls, surface: dict[str, Any], *, level: int = 0) -> DrawnSurface:
        """Read the caps and the rails out of a `roadsurface.json` and index them.

        Refuses a manifest with nothing drawn at this level: a height read off
        no surface is `blended_height` again, and the schema bump that
        introduced `ribbons` is what guarantees a reader never sees a manifest
        without them.
        """
        rings = [
            np.asarray(cap["ring"], dtype=np.float64)
            for cap in surface.get("caps", ())
            if int(cap["level"]) == level and len(cap["ring"]) >= 3
        ]
        rails = [
            tuple(np.asarray(rail, dtype=np.float64) for rail in ribbon["rails"])
            for ribbon in surface.get("ribbons", ())
            if int(ribbon["level"]) == level
        ]
        fans = [_fan_corners(ring) for ring in rings]
        # The level-0 areas (`P3-33c`) are cap-class for every purpose a reader
        # has: drawn, no lane coordinate, and what a junction is made of. They
        # arrive as triangles already, so they join the fans as one more.
        areas = np.zeros((0, 3, 3))
        if level == 0 and surface.get("areas"):
            areas = _drop_degenerate(np.asarray(surface["areas"], dtype=np.float64))
            fans.append(areas)
        strips = [_strip_corners(first, second) for first, second in rails]
        triangles = np.concatenate([*fans, *strips, np.zeros((0, 3, 3))])
        if not len(triangles):
            raise ValueError(f"roadsurface.json draws nothing at level {level}")
        is_cap = np.zeros(len(triangles), dtype=bool)
        is_cap[: sum(len(fan) for fan in fans)] = True
        cells = {
            key: (prepare(triangles[found]), is_cap[found])
            for key, found in _bin_by_plan_box(triangles[:, :, [0, 2]]).items()
        }

        edges = np.concatenate(
            [
                *(_ring_edges(ring) for ring in rings),
                # Every area triangle's three sides, in one array: there are tens
                # of thousands and a `_ring_edges` call apiece is most of a second.
                np.stack([areas, np.roll(areas, -1, axis=1)], axis=2).reshape(-1, 2, 3),
                *(_strip_edges(first, second) for first, second in rails),
                np.zeros((0, 2, 3)),
            ]
        )
        creases = _plan_creases(triangles)
        return cls(
            triangles=triangles,
            is_cap=is_cap,
            cells=cells,
            edges=edges,
            edge_cells=_bin_by_plan_box(edges[:, :, [0, 2]]),
            creases=creases,
            crease_cells=_bin_by_plan_box(creases),
        )

    @staticmethod
    def levels_drawn(surface: dict[str, Any]) -> list[int]:
        """Every level `of` would accept for this manifest, ascending: a level
        with at least one cap ring or one ribbon drawn. `of` refuses a level
        with nothing drawn, so a caller reading above level 0 asks this rather
        than guessing from `elevation_levels`."""
        levels = {int(cap["level"]) for cap in surface.get("caps", ()) if len(cap["ring"]) >= 3}
        if surface.get("areas"):
            levels.add(0)
        levels |= {int(ribbon["level"]) for ribbon in surface.get("ribbons", ())}
        return sorted(levels)

    def covers(self, x: float, z: float, *, toward: np.ndarray | None = None) -> bool:
        """Whether anything drawn at this level — a cap or a strip — stands over
        the point; with `toward`, over the point a tenth of a millimetre into
        the piece `toward` is the centroid of, so a corner *on* a drawn edge
        answers for its piece's side of it (`sample`'s rule). `sample` says the
        same and more, at the price of a ring search for the nearest edge when
        the answer is no."""
        if toward is not None:
            x, z = _stepped_into(x, z, toward)
        cap, ribbon = self._covering(x, z)
        return cap is not None or ribbon is not None

    def sample(self, x: float, z: float, *, toward: np.ndarray | None = None) -> DrawnHeight:
        """The drawn road at this plan position, and what answered for it.

        🔴 **One accessor, because two callers hand-rolling this diverged.** The
        first version of `Q92` left `boxjunctions._place` taking the cap outright
        where one existed while `height_at` below took the higher of cap and
        ribbon, so on a region with a cap below its arm the two marking stages
        would have placed paint at different heights — and each was documented as
        doing what the other did. Returning every part once also spares
        `roadmarks.py` a second query per vertex it only wanted for a counter.

        🔴 **`toward` is the side of a step the answer comes from, and a piece
        `split` cut owes it.** The drawn road is not only folded, it is
        *stepped*: where a cap's fan stands above the ribbon it overlaps, the
        road drops from the cap's height to the ribbon's along the cap's ring —
        0.46 m at one Causeway Bay junction — and a point exactly on that ring
        has two heights, one per side. `split` puts a cut vertex on exactly
        such a line, so a piece placed on the ribbon just outside the ring had
        its ring vertices sampled *on* the ring, inclusively, and took the cap:
        a stripe drawn down the face of the step, 3 cm of plan for 0.46 m of
        drop, which `check_faces_up` rightly refuses as not facing the sky
        (2 of 1,578 triangles, and 53 within 60° of vertical where the merged
        build had 5). With `toward` — the piece's own centroid — what covers
        the point is asked a tenth of a millimetre *into the piece*, so a
        vertex on a step takes the height of the surface its piece lies on.
        Across a fold the two sides agree there, so it moves nothing but a
        grade times 1e-4 m, below float32 at this region's coordinates; and
        where the piece's side is over nothing — a vertex on the drawn
        surface's outer edge with the piece past it — the point's own cover
        answers as before, so `vertices_over_cap`, `vertices_over_void` and
        `void_reach_m` keep counting what stands at the vertex.
        """
        cap, ribbon = self._covering(x, z)
        if cap is None and ribbon is None:
            height, reach = self._nearest_edge(x, z)
            return DrawnHeight(height_m=height, ribbon_m=None, cap_m=None, reach_m=reach)
        if toward is not None:
            side_cap, side_ribbon = self._covering(*_stepped_into(x, z, toward))
            if side_cap is not None or side_ribbon is not None:
                cap, ribbon = side_cap, side_ribbon
        return DrawnHeight(
            height_m=max(value for value in (cap, ribbon) if value is not None),
            ribbon_m=ribbon,
            cap_m=cap,
            reach_m=0.0,
        )

    def height_at(self, x: float, z: float) -> float:
        """The height of the drawn road surface at this plan position.

        ⚠️ **The higher of the two where a cap covers a ribbon, not the cap.**
        A cap and the arm it overlaps are both drawn — the 6,051 m² `Q53`
        measured — and the depth buffer shows whichever stands higher, so a
        marking has to clear that one. Measured, not assumed: with both callers
        on `sample` the difference is real, `height_spread_m` p90 **0.4260 →
        0.4215**, p99 **0.5051 → 0.4965**, paint rising onto the ribbon where a
        cap sits below the arm it overlaps.
        """
        return self.sample(x, z).height_m

    def cap_height_at(self, x: float, z: float) -> float | None:
        """The fan height where a junction cap covers this point, else `None`.

        The highest where caps overlap in plan, which they do wherever two nodes
        are closer together than their arms are wide — `surface.py` draws both
        and the renderer shows the upper one, so this must agree with it rather
        than take the first hit.
        """
        return self._covering(x, z)[0]

    def sampled_pieces(
        self, polygon: np.ndarray, *, thin_m: float = 0.0
    ) -> list[tuple[np.ndarray, np.ndarray, list[DrawnHeight]]]:
        """`split`, then `sample` at every corner of every piece toward that
        piece's centroid — the one way a marking stage places a polygon, so
        `boxjunctions._place` and `roadmarks._place` cannot drift apart on it.
        Each piece, its centroid, and its corners' samples in corner order."""
        pieces = []
        for piece in self.split(polygon, thin_m=thin_m):
            # A cut corner lies on a crease, and a crease can be a step as
            # well as a fold: the height is the one on this piece's side.
            centre = piece.mean(axis=0)
            samples = [self.sample(float(px), float(pz), toward=centre) for px, pz in piece]
            pieces.append((piece, centre, samples))
        return pieces

    def split(self, polygon: np.ndarray, *, thin_m: float = 0.0) -> list[np.ndarray]:
        """A convex plan polygon, cut along every crease of the drawn surface
        that crosses its interior — convex pieces, none of which spans a fold.

        🔴 **This is what closes the chord residue, and it closes it by
        construction rather than by a height.** Paint is a flat polygon and the
        road is piecewise linear: it folds at every fan spoke, every station
        line and every quad diagonal. A piece placed with its corners on the
        road still chords under a fold it spans — 10-13 mm on the shipped
        Wan Chai bundle, at BULLOCK LANE's cap and on the `e311` ramp, with
        every vertex right (`Q92`). A piece whose interior crosses no crease
        lies within one cap triangle and within one strip triangle; `sample`
        is the higher of the two, and the higher of two planes is convex, so a
        flat piece with its corners on that surface stands **on or above it
        everywhere**. Nothing is left to a tolerance except the nearest-edge
        fallback over the void, which is not a surface.

        A crease is taken only where its *segment* has a stretch strictly
        inside the piece, never where its line would cross: a 2 m by 0.1 m
        hatch piece near a cap would otherwise be cut by every spoke in the
        cell. Each cut is `clip_half_plane` twice, the stripe fields' own clip;
        the cut segment leaves the candidate list, so the recursion consumes
        one crease per level and terminates. A polygon no crease crosses comes
        back as itself, the common case — the counters `boxjunctions.py` and
        `roadmarks.py` publish beside this say how common.

        ⚠️ **A cut that would leave a piece the builder drops is not made.**
        `thin_m` is `FlatBuilder.build`'s sliver bar — a fan triangle whose
        plan area over its longest side is under it goes — and a crease within
        that width of a stripe's edge would cut off a strip the mesh then
        loses: measured, cutting regardless lost **1.96%** of the box paint's
        plan area on Wan Chai, 2,032 → 11,697 slivers. Refused, the chord stays
        and is bounded by the bar's own width — a fold within 5 cm of the
        edge sags millimetres at most under the 10 mm bar — and the plan area
        placed is the plan area asked for.
        """
        low, high = polygon.min(axis=0), polygon.max(axis=0)
        found = [
            seen
            for seen in (self.crease_cells.get(key) for key in _cells_touching(low, high))
            if seen is not None
        ]
        if not found:
            return [polygon]
        creases = self.creases[np.unique(np.concatenate(found))]
        # A crease whose own box misses the polygon's cannot cross it; the
        # cell is 16 m and the polygon is a couple, so most of the pack goes.
        near = ((creases.min(axis=1) <= high[None, :]) & (creases.max(axis=1) >= low[None, :])).all(
            axis=1
        )
        return _cut_along(polygon, creases[near], thin_m)

    def _covering(self, x: float, z: float) -> tuple[float | None, float | None]:
        """The highest cap and the highest strip drawn over this point."""
        pack = self.cells.get(_cell_of(x, z))
        if pack is None:
            return None, None
        prepared, is_cap = pack
        hit, heights = covered_prepared(prepared, x, z)
        if not len(heights):
            return None, None
        of_cap = is_cap[hit]
        cap = float(heights[of_cap].max()) if of_cap.any() else None
        strip = float(heights[~of_cap].max()) if not of_cap.all() else None
        return cap, strip

    def _nearest_edge(self, x: float, z: float) -> tuple[float, float]:
        """Height at the closest point on any drawn edge, and how far that is.

        Rings of the plan grid are widened until every unseen segment lies
        wholly in cells at least `ring` cells away and so at least
        `ring x _DRAWN_CELL_M` away — further than the best already found. The
        stop is exact, and it costs one ring per `_DRAWN_CELL_M` of void, which
        is why there is no radius to set.
        """
        column, row = _cell_of(x, z)
        point = np.array([x, z])
        best_distance, best_height = np.inf, 0.0
        ring = 0
        while True:
            seen = [
                found
                for found in (self.edge_cells.get(key) for key in _ring_of_cells(column, row, ring))
                if found is not None
            ]
            if seen:
                segments = self.edges[np.unique(np.concatenate(seen))]
                starts = segments[:, 0, [0, 2]]
                along, distance = _project_plan(starts, segments[:, 1, [0, 2]] - starts, point)
                nearest = int(distance.argmin())
                if distance[nearest] < best_distance:
                    best_distance = float(distance[nearest])
                    rise = segments[nearest, 1, 1] - segments[nearest, 0, 1]
                    best_height = float(segments[nearest, 0, 1] + along[nearest] * rise)
            if best_distance <= ring * _DRAWN_CELL_M:
                return best_height, best_distance
            ring += 1
            if ring > _MAX_VOID_RINGS:
                # Unreachable on a manifest `of` accepted — it has at least one
                # edge — unless the query is further from every drawn thing than
                # a region is wide, which is a caller's bug, not a height.
                raise ValueError(f"no drawn edge within {ring * _DRAWN_CELL_M:.0f} m of ({x}, {z})")


def _project_plan(
    starts: np.ndarray, spans: np.ndarray, point: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Project one plan point onto every segment: the clamped parameter along
    each, and the plan distance to that foot. A segment shorter than
    `_MIN_SEGMENT_M` has no direction, so its parameter is 0 and its distance
    is to its start."""
    lengths = np.einsum("ij,ij->i", spans, spans)
    lengths[lengths <= _MIN_SEGMENT_M**2] = np.inf
    along = np.clip(np.einsum("ij,ij->i", point - starts, spans) / lengths, 0.0, 1.0)
    feet = starts + along[:, None] * spans
    return along, np.hypot(*(feet - point).T)


def _cell_of(x: float, z: float) -> tuple[int, int]:
    return math.floor(x / _DRAWN_CELL_M), math.floor(z / _DRAWN_CELL_M)


def _stepped_into(x: float, z: float, toward: np.ndarray) -> tuple[float, float]:
    """The point a `_CREASE_GRAZE_M` step from `(x, z)` toward `toward`, or half
    way there if that is nearer — inside any convex piece `toward` is the
    centroid of, so what covers it is what covers the piece at that corner."""
    dx, dz = float(toward[0]) - x, float(toward[1]) - z
    distance = math.hypot(dx, dz)
    if distance <= 0.0:
        return x, z
    step = min(_CREASE_GRAZE_M, 0.5 * distance) / distance
    return x + dx * step, z + dz * step


def _cells_touching(low: np.ndarray, high: np.ndarray) -> Iterable[tuple[int, int]]:
    """The plan cells a box from `low` to `high` touches — `_bin_by_plan_box`'s
    rule for one box, through the same `_cells_between`, so a lookup and the
    binning cannot disagree."""
    return _cells_between(
        _cell_of(float(low[0]), float(low[1])), _cell_of(float(high[0]), float(high[1]))
    )


def _cells_between(low: tuple[int, int], high: tuple[int, int]) -> Iterable[tuple[int, int]]:
    """Every cell from `low` to `high` inclusive, column-major."""
    for column in range(low[0], high[0] + 1):
        for row in range(low[1], high[1] + 1):
            yield column, row


def _plan_creases(triangles: np.ndarray) -> np.ndarray:
    """Every edge of every drawn triangle in plan, each once, as `(k, 2, 2)`.

    A spoke is shared by two fan wedges and a station line by two strip
    triangles, so each edge's ends are ordered lexicographically before the
    duplicates go — the same crease from either side is one crease.
    """
    plan = triangles[:, :, [0, 2]]
    edges = np.concatenate(
        [np.stack([plan[:, index], plan[:, (index + 1) % 3]], axis=1) for index in range(3)]
    )
    start, stop = edges[:, 0], edges[:, 1]
    swap = (start[:, 0] > stop[:, 0]) | ((start[:, 0] == stop[:, 0]) & (start[:, 1] > stop[:, 1]))
    edges[swap] = edges[swap][:, ::-1]
    _, first = np.unique(np.round(edges.reshape(-1, 4), 6), axis=0, return_index=True)
    return edges[np.sort(first)]


# A stretch of crease inside a piece shorter than this, or a piece's interior
# shallower than this behind the crease, is the crease grazing a corner or
# running along an edge — not a fold the piece spans. A tenth of a millimetre:
# far below anything the 10 mm chord bar can see, far above float noise.
_CREASE_GRAZE_M = 1e-4


def _crossing_interior(polygon: np.ndarray, segments: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Which plan segments have a stretch strictly inside a convex plan polygon,
    and which could have one inside any piece cut from it.

    Cyrus-Beck: each polygon edge is a half-plane, each segment is clipped to
    all of them at once, and what survives is the parameter interval inside the
    closed polygon. A segment lying along the boundary survives that with a
    positive length and crosses nothing, so the interval's midpoint must also
    sit `_CREASE_GRAZE_M` inside every edge.

    The second mask is the first with the depth bar halved, and it is exact: a
    piece cut from this polygon is inside it, so a segment's stretch inside the
    piece is within its stretch here, and the depth (distance to the boundary)
    is concave along the stretch, so the midpoint reads at least half the
    maximum — a segment that could cross a piece reads over half the bar here.
    `_cut_along` carries only those into the halves; the rest are dead weight
    at every level, and they were 90% of the candidates.
    """
    if not len(segments):
        return np.zeros(0, dtype=bool), np.zeros(0, dtype=bool)
    # Closed-ring differences without `np.roll`, which on a 4-7 corner polygon
    # was nearly all overhead — 11% of the box stage across three calls here.
    sides = np.empty_like(polygon)
    sides[:-1] = polygon[1:] - polygon[:-1]
    sides[-1] = polygon[0] - polygon[-1]
    normals = np.column_stack([-sides[:, 1], sides[:, 0]])
    # The left normal of each side points inward for one winding and outward
    # for the other; the shoelace says which this polygon is, and the
    # half-planes below want them OUTWARD — inside is `dot(p, n) <= bound`.
    winding = float(polygon[:, 0] @ sides[:, 1] - polygon[:, 1] @ sides[:, 0])
    if winding > 0.0:
        normals = -normals
    lengths = np.hypot(normals[:, 0], normals[:, 1])
    lengths[lengths <= _MIN_SEGMENT_M] = np.inf
    normals = normals / lengths[:, None]
    bounds = np.einsum("ij,ij->i", normals, polygon)

    starts, stops = segments[:, 0], segments[:, 1]
    spans = stops - starts
    rate = spans @ normals.T  # how fast each segment leaves each half-plane
    room = bounds[None, :] - starts @ normals.T  # how far inside each start is
    with np.errstate(divide="ignore", invalid="ignore"):
        at = room / rate
    parallel_inside = np.where(room >= 0.0, np.inf, -np.inf)
    upper = np.where(rate > 0.0, at, np.where(rate < 0.0, np.inf, parallel_inside))
    lower = np.where(rate < 0.0, at, np.where(rate > 0.0, -np.inf, -parallel_inside))
    enter = np.maximum(lower.max(axis=1), 0.0)
    leave = np.minimum(upper.min(axis=1), 1.0)
    stretch = np.where(leave > enter, leave - enter, 0.0)
    inside_m = stretch * np.hypot(spans[:, 0], spans[:, 1])
    middle = starts + np.where(stretch > 0.0, enter + 0.5 * stretch, 0.0)[:, None] * spans
    depth = (bounds[None, :] - middle @ normals.T).min(axis=1)
    long_enough = inside_m > _CREASE_GRAZE_M
    return long_enough & (depth > _CREASE_GRAZE_M), long_enough & (depth > 0.5 * _CREASE_GRAZE_M)


def _cut_along(polygon: np.ndarray, creases: np.ndarray, thin_m: float) -> list[np.ndarray]:
    """Cut a convex plan polygon by the first crease crossing it, and each half
    by the rest, until no crease crosses any piece — skipping a cut that would
    leave a half thinner than `thin_m`."""
    pieces: list[np.ndarray] = []
    pending = [(polygon, creases)]
    while pending:
        piece, candidates = pending.pop()
        if not len(candidates):
            pieces.append(piece)
            continue
        crossing, carried = _crossing_interior(piece, candidates)
        if not crossing.any():
            pieces.append(piece)
            continue
        chosen = int(np.flatnonzero(crossing)[0])
        start, stop = candidates[chosen]
        carried[chosen] = False
        rest = candidates[carried]
        normal = np.array([stop[1] - start[1], start[0] - stop[0]])
        normal = normal / np.hypot(*normal)
        bound = float(normal @ start)
        halves = [
            _without_repeats(half)
            for half in (
                clip_half_plane(piece, normal, bound),
                clip_half_plane(piece, -normal, -bound),
            )
        ]
        halves = [half for half in halves if len(half) >= 3]
        if any(_fans_thin(half, thin_m) for half in halves):
            pending.append((piece, rest))
            continue
        pending.extend((half, rest) for half in halves)
    return pieces


def _fans_thin(polygon: np.ndarray, thin_m: float) -> bool:
    """Whether `FlatBuilder.polygon`'s fan of this plan polygon has a triangle
    `FlatBuilder.build` would drop — `thin_in_plan`, the builder's own test,
    over the fan the builder will emit."""
    if thin_m <= 0.0 or len(polygon) < 3:
        return False
    fan = np.stack(
        [np.broadcast_to(polygon[0], polygon[1:-1].shape), polygon[1:-1], polygon[2:]], axis=1
    )
    return bool(thin_in_plan(fan, thin_m).any())


def _without_repeats(polygon: np.ndarray) -> np.ndarray:
    """A polygon with consecutive coincident corners folded into one — a corner
    exactly on the cut line comes out of `clip_half_plane` twice."""
    if len(polygon) < 2:
        return polygon
    step = polygon - np.concatenate([polygon[-1:], polygon[:-1]])
    return polygon[np.hypot(step[:, 0], step[:, 1]) > _MIN_SEGMENT_M]


def _bin_by_plan_box(plan: np.ndarray) -> dict[tuple[int, int], np.ndarray]:
    """Plan cell to the rows of `plan` — `(n, k, 2)` corners each — whose
    bounding box touches it."""
    low = np.floor(plan.min(axis=1) / _DRAWN_CELL_M).astype(np.int64)
    high = np.floor(plan.max(axis=1) / _DRAWN_CELL_M).astype(np.int64)
    binned: dict[tuple[int, int], list[int]] = {}
    for index, (lowest, highest) in enumerate(zip(low.tolist(), high.tolist(), strict=True)):
        for key in _cells_between(tuple(lowest), tuple(highest)):
            binned.setdefault(key, []).append(index)
    return {key: np.asarray(value) for key, value in binned.items()}


def _ring_of_cells(column: int, row: int, ring: int) -> Iterable[tuple[int, int]]:
    """The cells exactly `ring` steps from `(column, row)` in Chebyshev distance."""
    if ring == 0:
        yield column, row
        return
    for step in range(-ring, ring + 1):
        yield column + step, row - ring
        yield column + step, row + ring
    for step in range(-ring + 1, ring):
        yield column - ring, row + step
        yield column + ring, row + step


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
    return _drop_degenerate(fan)


def _strip_corners(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """`_Builder.strip`'s triangulation of one quad strip, as `(k, 3, 3)`.

    Written from the same two index triples the builder emits — `(i, i+1,
    i+span)` and `(i+1, i+span+1, i+span)`, with the second rail stacked after
    the first — so a change to one is visibly a change to both. The rails are
    taken **in the order `strip` received them**, which is how
    `roadsurface.json` publishes them: the diagonal of each quad depends on it,
    and a point near the diagonal reads a different plane on the other one.
    """
    if len(left) < 2:
        return np.zeros((0, 3, 3))
    first = np.stack([left[:-1], left[1:], right[:-1]], axis=1)
    second = np.stack([left[1:], right[1:], right[:-1]], axis=1)
    return _drop_degenerate(np.concatenate([first, second]))


def _drop_degenerate(corners: np.ndarray) -> np.ndarray:
    edge_a, edge_b = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    twice_area = edge_a[:, 0] * edge_b[:, 2] - edge_a[:, 2] * edge_b[:, 0]
    return corners[np.abs(twice_area) > MIN_TWICE_AREA_M2]


def _ring_edges(ring: np.ndarray) -> np.ndarray:
    """A closed ring's edges as `(k, 2, 3)` segments."""
    return np.stack([ring, np.roll(ring, -1, axis=0)], axis=1)


def _strip_edges(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """A strip's outline as segments: both rails and the two end lines.

    Empty below two stations, as `_strip_corners` is: `_Builder.strip` draws
    nothing there, so there is no edge to snap to."""
    if len(left) < 2:
        return np.zeros((0, 2, 3))
    return np.concatenate(
        [
            np.stack([left[:-1], left[1:]], axis=1),
            np.stack([right[:-1], right[1:]], axis=1),
            np.stack([left[[0, -1]], right[[0, -1]]], axis=1),
        ]
    )


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
    # A neighbour-owned run's end (`P5-7f`): it takes a trim so the cap hull
    # can read its mouth where the owner will draw it, and it moves no counter.
    foreign: bool = False


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
    # 🔴 **The DRAWN ribbon's centre per published vertex, in `mitres`' frame
    # (`Q107`).** Since the clamp, half a width no longer describes the road:
    # the two rails are cut to the deck independently, so the ribbon is
    # asymmetric about its own centreline and `published_half_widths` is half
    # the *distance between the rails* rather than half a width about zero.
    # Published beside it so a consumer can rebuild the ribbon from
    # `roadsurface.json` alone — which `Q106` found four tools could not do, and
    # all four were wrong about the off-grade network for it.
    published_offsets: np.ndarray
    lanes: int
    # Read straight off the published edge and carried only so `TEXCOORD_1` can
    # say them. Nothing about the ribbon's shape depends on any of the four —
    # they decide which markings the shader draws on it, which is why they
    # arrive here rather than in `_shape`.
    direction: str
    bus_lane: bool
    tram_tracks: bool
    level: int
    length_m: float
    # `roadgraph.json`'s `lanes_forward` as the codec spells it: 0 where the
    # graph published `null` or a one-way edge, else the boundary the two flows
    # part at (`Q126`). Decided in `_prepare`, which is where the graph's
    # vocabulary meets the codec's.
    lanes_forward: int = 0
    # 🔴 **How far this ribbon is drawn off its own centreline, in `mitres`'
    # LEFT-of-travel frame (`Q103`).** Off-grade the published centreline is not
    # the middle of the deck the road is built on — measured p50 0.75 m out and
    # up to 4.90 m — and no publisher draws a viaduct deck edge to correct it
    # against, so the structure itself is the only source. Zero everywhere the
    # graph publishes no offset, which is every level-0 edge.
    #
    # ⚠️ **Added to BOTH boundaries rather than moving `points`.** Shifting the
    # centreline would move everything registered against it — the kerbside
    # runs, the lane coordinate's origin, the junction mitres meeting the
    # neighbouring arm — and all of those belong on the published geometry.
    # What moved is the paint.
    shift_m: float = 0.0
    # Whether the rim columns are this edge's TERRITORY and so ARE its rails
    # (`P3-33c`), rather than a deck the ribbon is merely cut back to (`Q107`).
    territory: bool = False
    # The territory's own stations, kept for `_publish_territory_table`: the
    # corridor is read from them after the trims and never enters the matrix.
    stations: surface_region.Stations | None = None
    # Half the territory's median span. A territory pinches to a wedge at its
    # node, so the end station's own width says nothing about how far back the
    # junction reaches; this is what `end_half_width_m` reads instead.
    mouth_half_m: float = 0.0
    # How far in from each node the territory is still junction-shaped — the trim
    # READ, where `_assign_trims`' radius is the trim guessed (`flare_m`).
    flare_start_m: float = 0.0
    flare_end_m: float = 0.0
    trim_start_m: float = 0.0
    trim_end_m: float = 0.0
    # Whether each trim was held to `junction_trim_max_fraction`'s length
    # ceiling rather than reaching the junction radius (`P3-31`). Filled by
    # `_assign_trims` beside the trims themselves, because the two are one
    # decision: an edge clamped at *both* ends is a stub — a link the source
    # drew between two nodes of one junction, shorter than the caps it joins
    # need — and the stub's ribbon is what is left after both clamps.
    clamped_start: bool = False
    clamped_end: bool = False
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

    @property
    def is_stub(self) -> bool:
        """A link between two nodes of one junction, clamped at both ends.

        No new knob, and deliberately so (`Q72`): the definition is the two
        existing trim decisions read together. Road Network v2 models a
        junction between two dual carriageways as a cluster of nodes joined by
        short links, one node where each carriageway crosses the other, and a
        link shorter than twice its own trim radius is such a cluster's
        interior — 87 of Wan Chai's 792 edges, p50 9.6 m. Each end of one is
        clamped to 35% of its length, so the two per-node caps it joins stop
        short of each other and the ground between them is the median void
        `P3-31` names (`Q104`).
        """
        return self.clamped_start and self.clamped_end

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
        # The top field, so a value past it is not a carry but a code past the
        # decode's ceiling — the same silent failure by a different route.
        if not 0 <= self.lanes_forward <= MARKING_LANES_FORWARD_MAX:
            raise ValueError(
                f"lanes_forward {self.lanes_forward} is past what `TEXCOORD_1` can say "
                f"(0-{MARKING_LANES_FORWARD_MAX}): `_prepare` should have refused it"
            )
        if self.lanes_forward and not (
            self.direction == BOTH and 0 < self.lanes_forward < self.lanes
        ):
            raise ValueError(
                f"lanes_forward {self.lanes_forward} on a {self.direction} edge of "
                f"{self.lanes} lanes: a split is a boundary strictly inside a two-way road"
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
            + MARKING_LANES_FORWARD * self.lanes_forward
        )

    def end_half_width_m(self, at_start: bool) -> float:
        """The half-width this edge arrives at a node with.

        Its *own* end, not the widest anywhere along it: since `Q23` those can
        differ by the whole widening factor, and it is the end that decides how
        far back the junction cap has to reach to meet this arm.
        """
        return max(float(self.points[0 if at_start else -1, _WIDTH]), self.mouth_half_m)


def build_region(
    city: Config,
    region_id: str,
    *,
    out_root: Path | None = None,
    sources_root: Path | None = None,
) -> SurfaceReport:
    """Read the region's road graph and write its `roads.glb`."""
    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    style = city.roads.surface

    report = SurfaceReport()
    # The level-0 carriageway as a region (`Q129`), where the city builds one.
    # Absent, every edge below is the ribbon it always was and `region` is None.
    region = (
        surface_region.read(out_dir, region_id) if city.carriageway_region is not None else None
    )

    def stations_of(published: dict, *, foreign: bool) -> surface_region.Stations | None:
        if region is None or int(published["elevation_level"]) != 0:
            return None
        found = region.stations.get((foreign, int(published["id"])))
        if found is None and not foreign:
            report.territory_missing_edges += 1
        return found

    rail_tolerance_m = city.carriageway_region.rail_tolerance_m if region is not None else 0.0
    rail_opening_m = city.carriageway_region.rail_opening_m if region is not None else 0.0
    # TPDM 4.3.9.8's narrow end, from the survey's own bounds — the bar
    # `tools/lane_paint.py` grades a painted lane against, so the two cannot sit
    # on different numbers. No survey, no ceiling.
    survey = city.carriageway_survey
    lane_min_m = survey.width_bounds.lane_m[0] if region is not None and survey else 0.0
    edges = [
        _prepare(
            edge,
            style,
            report,
            stations_of(edge, foreign=False),
            rail_tolerance_m,
            lane_min_m,
            rail_opening_m,
        )
        for edge in graph["edges"]
    ]
    # The neighbour's runs reaching into this region (`P5-7e`), prepared and
    # shaped the same way so a junction cap can meet their mouths — `Q116`'s
    # one exception to "the non-owner draws nothing". Prepared against a scratch
    # report: nothing below draws, trims, hides or measures a foreign edge, so
    # nothing it does may move a counter.
    foreign_published = graph.get("foreign_edges", [])
    foreign = [_prepare(edge, style, SurfaceReport()) for edge in foreign_published]
    every_edge = [*edges, *foreign]
    # Zipped rather than looked up: `_prepare` maps the published edges one for
    # one and in order, so the pairing is the list's own construction. The
    # *published* widths, not the ribbon's — `dedupe` has already dropped
    # stations from the latter, and the game indexes this table by
    # `roadgraph.json`'s own vertex numbering.
    # One pass filling both, because every consumer indexes them together and a
    # second zip is a second place for a filter or a rounding change to land.
    for published, prepared in zip(graph["edges"], edges, strict=True):
        edge_id = int(published["id"])
        report.carriageway[edge_id] = [
            round(float(half), 3) for half in prepared.published_half_widths
        ]
        report.carriageway_offset[edge_id] = [
            round(float(at), 3) for at in prepared.published_offsets
        ]
    report.on_structure_m = sum(
        _on_structure_length_m(edge, "on_structure") for edge in graph["edges"]
    )
    report.structure_bounded_m = sum(
        _on_structure_length_m(edge, "structure_bounded") for edge in graph["edges"]
    )
    ends = _ends_by_node_and_level([*graph["edges"], *foreign_published], every_edge)
    report.foreign_ends = sum(end.foreign for group in ends.values() for end in group)
    _assign_trims(ends, every_edge, style, report)
    # After the assignment, not beside `carriageway` above: the trims do not
    # exist until `_assign_trims` has seen every end that meets every node.
    report.trims_m = {
        int(published["id"]): (round(prepared.trim_start_m, 3), round(prepared.trim_end_m, 3))
        for published, prepared in zip(graph["edges"], edges, strict=True)
    }
    for published, prepared in zip(graph["edges"], edges, strict=True):
        if prepared.territory:
            _publish_territory_table(published, prepared, report)
    _measure_level_steps(ends, every_edge, report)
    boxes = _box_rings(city, region_id, sources_root=sources_root, report=report)
    for index, edge in enumerate(every_edge):
        # After the trims and before the offsets: a boundary outside the drawn
        # ribbon needs no station, and `_shape` is what turns stations into
        # rails. See `_add_kerb_stations`. A foreign edge is shaped so its
        # rails exist for the cap hull to read, and counted nowhere.
        stations = _add_kerb_stations(edge)
        # Owned level-0 ribbons only: a box on a structure never reaches here
        # (`boxsource.read_boxes` refuses it) and a foreign ribbon draws nothing.
        # 🔴 **And only where no region is built** (`P3-35e`, `Q133`): the stations
        # exist for `_paint_flanks`, which is gated on `region is None` below —
        # with a region the areas are `R - ribbons` and the paint already stands
        # on asphalt. Ungated, Wan Chai carried 125 stations for flanks that read
        # 0: two carriageway triangles and four kerb strips each, for nothing.
        stationed = index < len(edges) and edge.level == 0 and region is None
        paint_stations = _add_paint_stations(edge, boxes) if stationed else 0
        _shape(edge, style)
        if index < len(edges):
            report.kerb_stations += stations
            report.paint_stations += paint_stations

    # Capped after every ribbon exists, because a cap is defined by where the
    # ribbons it joins actually ended — including where a trim was clamped. The
    # rings are held rather than drawn straight away: a cap covers kerb too, so
    # `_hide_buried_kerbs` has to see them before any of it is emitted.
    # 🔴 **A cap goes whole to the region containing its node** (`Q116`): with
    # the neighbour's runs in the groups, a node in the neighbour can gather
    # two arms here too, and capping it would draw the same junction twice.
    # Membership is `roads.Ownership`'s — the geodetic bounds, half-open — so
    # the two builds cannot both claim a node or both refuse it.
    owner_of = Ownership(city, region_id, city.game_transform(region_id))
    node_plan = {int(node["id"]): (node["pos"][0], node["pos"][2]) for node in graph["nodes"]}
    caps: list[_Cap] = []
    # One cap per cluster of nodes joined by stubs (`P3-31`), and per node
    # everywhere else — `_stub_clusters` returns the latter as singletons, so
    # this loop has one shape. Every node of a cluster is owned, so its lowest
    # passes the ownership test below and a cluster is never left to the
    # neighbour; the test still runs so that there is one rule, not two.
    clusters = _stub_clusters(
        ends,
        every_edge,
        report,
        owned=lambda node: owner_of(np.asarray(node_plan[node])) == region_id,
    )
    for keys in clusters:
        groups = [ends[key] for key in keys]
        (node, level) = keys[0]
        if region is not None and level == 0:
            # A level-0 junction is `R` less the ribbons meeting at it, drawn
            # below as area — a union cannot overlap itself or leave a gap, which
            # is everything the hull, the corridors and the flanks were for.
            continue
        if (
            sum(len(group) for group in groups) >= 2
            and owner_of(np.asarray(node_plan[node])) != region_id
        ):
            # An upper bound on what the neighbour draws: `_cap_ring` can still
            # refuse a group of two whose corners do not make a ring.
            report.caps_in_neighbour += 1
            continue
        ring = _cap_ring(groups, every_edge, report)
        if ring is None:
            continue
        caps.append(_Cap(level, ring))
        if len(groups) >= 2:
            # A corridor is a cap of its own, unioned with the cluster's by
            # being drawn beside it; see `_through_corridors` for why it is
            # not hulled in.
            caps.extend(
                _Cap(level, quad) for quad in _through_corridors(groups, every_edge, report)
            )
        if any(end.foreign for group in groups for end in group):
            report.caps_with_foreign_mouth += 1
    # The paint flanks (`P3-32`), before the kerbs are hidden so a kerb under
    # a flank is hidden like a kerb under any cap.
    if boxes.rings and region is None:
        flanked = [
            edge
            for edge in edges
            if edge.level == 0 and edge.left is not None and edge.right is not None
        ]
        outlines = _Rings.of([np.vstack([edge.left, edge.right[::-1]]) for edge in flanked])
        ribbons = [edge.ribbon for edge in flanked]
        for own, edge in enumerate(flanked):
            flanks = _paint_flanks(edge, boxes, outlines, ribbons, own, style, report)
            caps.extend(_Cap(0, quad) for quad in flanks)
    _hide_buried_kerbs(edges, caps, report)
    # Held here rather than beside the `builder.fan` loop below, because that
    # loop is the *drawing* and this is the record of what will be drawn. A cap
    # refused by `_cap_ring` never reaches either, so the two populations are the
    # same list by construction rather than by a predicate written twice.
    report.cap_rings = [(cap.level, cap.ring) for cap in caps]
    _record_hidden_kerbs(graph["edges"], edges, report)
    # From list positions to published ids, here because this is where the graph
    # is in scope. Owned edges only: `_read_offside` is handed `edges`, so a
    # foreign run can never be half of a recorded pair.
    published_ids = [int(edge["id"]) for edge in graph["edges"]]
    report.opposed_pairs = {
        (published_ids[here], published_ids[there]): gap
        for (here, there), gap in _read_offside(edges, style, report).items()
    }

    builder = _Builder(Grid.for_region(city, city.region(region_id)))
    for published, edge in zip(graph["edges"], edges, strict=True):
        if _draw_edge(builder, edge, int(published["id"]), style, city.roads.lane_width_m, report):
            report.edges += 1
    if region is not None:
        level0 = [
            (index, edge)
            for index, edge in enumerate(every_edge)
            if edge.level == 0 and edge.left is not None and edge.right is not None
        ]
        ids = [int(edge["id"]) for edge in [*graph["edges"], *foreign_published]]
        centrelines = {
            (index >= len(edges), ids[index]): edge.points[:, :3]
            for index, edge in enumerate(every_edge)
            if edge.level == 0 and len(edge.points) >= 2
        }
        # Built once: the buffer is 0.3 s, and both `areas` and the loop below want it.
        rings = surface_region.island_rings(region)
        report.area_triangles, area_kerbs = surface_region.areas(
            region,
            # Every level-0 ribbon, the neighbour's included: its ribbon is its
            # owner's to draw, so it is subtracted here exactly as an owned one.
            [np.vstack([edge.left, edge.right[::-1]]) for _, edge in level0],
            centrelines,
            [
                _lift(rail, edge.ribbon, 0.0)
                for index, edge in level0
                if index < len(edges)
                for rail in (edge.left, edge.right)
            ],
            city.region_high(region_id),
            # The rails' kerbed runs, in plan: where a ribbon already draws the kerb.
            [
                rail[start:stop]
                for index, edge in level0
                if index < len(edges)
                for rail, keep in ((edge.left, edge.kerb_left), (edge.right, edge.kerb_right))
                for start, stop in (_runs(keep) if keep is not None else [(0, len(rail))])
            ],
            style.kerb_width_m,
            rail_tolerance_m,
            rings,
        )
        for line in area_kerbs:
            report.area_kerb_m += _draw_area_kerb(
                builder,
                line,
                style,
                city.roads.lane_width_m,
                lip=not surface_region.on_island(rings, line),
            )
        tops = surface_region.island_tops(
            region,
            centrelines,
        )
        if len(tops):
            tops[:, :, 1] += style.kerb_height_m
            report.islands = len(region.islands)
            builder.triangles(
                tops,
                colour=style.kerb_material.colour,
                # A kerb code says a length: "none" is a junction cap's word.
                marking=_Marking(_AREA_KERB_CODE, 1.0),
            )
        builder.triangles(
            report.area_triangles,
            colour=style.surface_material.colour,
            marking=_Marking(float(MARKING_CLASS_CAP), 0.0),
        )
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
    _write_chunks(out_dir, builder.chunk(), report)
    _write_manifest(out_dir, city, region_id, report)
    return report


def _road_collider(piece: MeshData) -> MeshData:
    """The chunk's `-colonly` collider (`P5-12`): the ribbon's triangles, bare.

    The same geometry the chunk draws — the kerb riser included, because kerbs
    are mountable by design (`P2-3`) — carrying positions, normals and indices
    and nothing else: the importer removes the mesh, so a colour or a marking
    code here is bytes nothing reads. Its own primitive rather than the `-col`
    suffix on the render mesh so the two may diverge later (`Q121`); today
    they do not, and `verify_road_surface.gd` asserts the collider stands
    beside every chunk.
    """
    return MeshData(
        name=SURFACE_COLLIDER_NAME,
        positions=piece.positions,
        normals=piece.normals,
        triangles=piece.triangles,
    )


def _write_chunks(out_dir: Path, chunks: list[tuple[str, MeshData]], report: SurfaceReport) -> None:
    """One `.glb` per tile under `SURFACE_DIR`, and the manifest rows for them.

    The directory is emptied of `.glb` files first: a rerun after the grid or
    the graph moved must not leave a chunk from the previous build beside the
    new ones, where `export.py` would neither name it nor notice it, and
    `sync_generated.sh` — which copies what the manifest names — would leave a
    stale copy in the game until something deleted it by hand.

    Every chunk keeps `SURFACE_MESH_NAME` and carries its own collider beside
    it (`P5-12`), so each one stands on its own at import and the material
    dispatch (`SURFACE_MATERIAL`) is the same test it was for the region-wide
    mesh.
    """
    chunk_dir = out_dir / SURFACE_DIR
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for stale in list(chunk_dir.glob("*.glb")):
        stale.unlink()
    triangles = 0
    for tile, piece in chunks:
        relative = chunk_path(tile)
        collider = _road_collider(piece)
        size = write_glb(out_dir / relative, [piece, collider])
        report.chunks.append(
            {
                "id": tile,
                "file": relative,
                "triangles": piece.triangle_count,
                "vertices": len(piece.positions),
                "collision_triangles": collider.triangle_count,
                "bytes": size,
                "aabb": piece.aabb(),
            }
        )
        report.bytes += size
        report.chunk_vertices += len(piece.positions)
        triangles += piece.triangle_count
    if triangles != report.triangles:
        raise ValueError(
            f"road chunks carry {triangles} triangles where the built mesh has "
            f"{report.triangles} — the partition lost or duplicated some"
        )


def _prepare(
    published: dict,
    style: RoadSurface,
    report: SurfaceReport,
    stations: surface_region.Stations | None = None,
    rail_tolerance_m: float = 0.0,
    lane_min_m: float = 0.0,
    rail_opening_m: float = 0.0,
) -> _Edge:
    """One published edge as a ribbon-in-waiting, half-widths already resolved.

    The widths are computed against the **published** polyline, before `dedupe`
    drops anything, so `report.carriageway` and `roadgraph.json` index alike —
    which is the contract the game reads them under.
    """
    half_widths = _half_widths(published, style)
    rim_left, rim_right, adrift_rims = _deck_rims(published, len(half_widths))
    kerb_left = kerb_right = np.ones(len(half_widths))
    # 🔴 **A level-0 edge with a territory takes its extents AS its rails**
    # (`Q129`, `P3-33c`) — `Q107`'s columns and `Q107`'s clamp, read exactly
    # rather than as a ceiling. A deck rim, where a level-0 edge ever carries
    # one, still cuts: the territory is a 2D plan and the deck is the structure.
    territory = stations is not None and len(stations.vertex_station) == len(half_widths)
    if stations is not None and not territory:
        report.territory_mismatched_edges += 1
    if territory:
        # The rail is the road's running kerb line, not everything the territory
        # reaches: mouths bridged, then bays and bulges opened away. Both only
        # ever narrow, and what they let go of is drawn as area.
        # `kerb_width_m` is the bump bar: `_paint_flanks`' own reading that two
        # surfaces a kerb apart are one, so anything under it is kerb jitter.
        stations = surface_region.opened(
            surface_region.bridged(stations), rail_opening_m, style.kerb_width_m
        )
    # The DECK rims go into the matrix and the territory is laid over them in
    # `_with_territory_stations`, once every station exists; `published_*` below
    # is provisional for a territory edge and `_publish_territory_table` replaces
    # it after the trims.
    if territory:
        at = stations.vertex_station
        table_left = np.minimum(rim_left, stations.left_m[at])
        table_right = np.minimum(rim_right, stations.right_m[at])
    else:
        table_left, table_right = rim_left, rim_right
    # `published["offset_m"]`, never a `.get` default: `read_graph` pins the
    # schema exactly, so any graph this can open carries the field. A default
    # could not fire on valid input and would silently draw every off-grade
    # ribbon back at zero shift on invalid input, which is the one failure it
    # would ever meet.
    shift_m = float(published["offset_m"])
    points = dedupe(
        _with_territory_stations(
            np.column_stack(
                [
                    _polyline(published),
                    half_widths,
                    np.zeros(len(half_widths)),
                    rim_left,
                    rim_right,
                    kerb_left,
                    kerb_right,
                ]
            ),
            stations if territory else None,
            rail_tolerance_m,
        )
    )
    restrictions, kinds, minority_m = _kerbside(published)
    report.kerb_minority_m += minority_m
    # The same clamp the geometry gets, in the frame the manifest publishes.
    # ⚠️ **`half_widths` itself stays UNCLAMPED** — it is the `_WIDTH` column,
    # and `_shape` clamps it against the rims that travel beside it. Clamping it
    # here as well would apply the cut twice, the second time about a centre
    # that is no longer `shift`.
    drawn_upper, drawn_lower, refused = _clamped_rails(
        half_widths, table_left, table_right, shift_m, exact=territory
    )
    if territory:
        report.territory_edges += 1
        report.territory_fallback_stations += refused
    elif np.isfinite(rim_left).any():
        # ⚠️ **Inside this guard, because the log line reads "N of those
        # vertices" against the edge count above it.** An edge whose every
        # vertex is off structure keeps no finite rim, so it is not one of
        # "those" and must not contribute — 0 such edges in this region, and
        # reachable.
        report.deck_rim_off_structure += adrift_rims
        report.deck_rim_edges += 1
        # ⚠️ Counted here and not in `_shape`, because these are the *published*
        # stations — the frame both counters and the manifest are quoted in, and
        # the only one a reader can join against `roadgraph.json`.
        cut = (drawn_upper - drawn_lower) < 2.0 * half_widths - _MIN_SEGMENT_M
        report.clamped_stations += int(cut.sum())
        report.clamp_refused_stations += refused
    lanes, lanes_forward = int(published["lanes"]), _lanes_forward_code(published, report)
    flare = (
        surface_region.flare_m(stations, rail_opening_m, style.kerb_width_m)
        if territory and rail_opening_m > 0.0
        else (0.0, 0.0)
    )
    mouth_half_m = 0.5 * float(np.median(stations.left_m + stations.right_m)) if territory else 0.0
    if territory and lane_min_m > 0.0:
        # 🔴 **A territory is a CEILING on the PAINTED lane count and never a
        # source of one** — `Q114`'s deck rule, for its reason. `lanes` is
        # bracketed off `width_m`, the carriageway; the ribbon is this
        # centreline's SHARE of it, and the markings shader cuts whatever it is
        # handed into `lanes` strips. GLOUCESTER ROAD `e479` is three authored
        # lanes on a 1.4 m share: three 0.45 m lanes. One-sided on purpose — a
        # share wider than its count leaves the count alone — and it moves the
        # mesh only: the graph's `lanes`, the arrow slots and `RoadGraph`'s
        # driving line are the roads stage's and do not move here.
        #
        # ⚠️ **Reduced at a LOW percentile, clear of the mouths, and not at the
        # median** — `carriageway.DECK_WIDTH_PERCENTILE`'s reduction for its
        # reason: paint has to fit nearly everywhere, and half of every edge's
        # stations are narrower than its median by construction. At the median,
        # 146 mid-block vertices still painted a lane under TPDM's narrow end.
        span = stations.left_m + stations.right_m
        reach = mouth_half_m
        clear = (stations.along_m >= reach) & (stations.along_m <= stations.along_m[-1] - reach)
        span = float(np.percentile(span[clear] if clear.any() else span, _LANE_SPAN_PERCENTILE))
        ceiling = max(1, int(span // lane_min_m))
        if ceiling < lanes:
            report.territory_lanes_capped += 1
            lanes = ceiling
            # The split between the two flows is a boundary INSIDE the count.
            if lanes_forward >= lanes:
                lanes_forward = 0
    if territory:
        report.lanes_painted[int(published["id"])] = lanes
    return _Edge(
        points=points,
        shift_m=shift_m,
        published_half_widths=0.5 * (drawn_upper - drawn_lower),
        published_offsets=0.5 * (drawn_upper + drawn_lower),
        territory=territory,
        flare_start_m=flare[0],
        flare_end_m=flare[1],
        stations=stations if territory else None,
        mouth_half_m=mouth_half_m,
        lanes=lanes,
        lanes_forward=lanes_forward,
        direction=published["direction"],
        bus_lane=bool(published["bus_lane"]),
        tram_tracks=bool(published["tram_tracks"]),
        level=published["elevation_level"],
        length_m=float(plan_lengths(points)[-1]) if len(points) > 1 else 0.0,
        kerb_near=kinds[NEARSIDE],
        kerb_off=kinds[OFFSIDE],
        restrictions=restrictions,
    )


def _publish_territory_table(published: dict, edge: _Edge, report: SurfaceReport) -> None:
    """`carriageway[]` for an edge whose rails are its territory (`P3-33c`).

    🔴 **A published vertex inside a junction trim publishes the ribbon's width
    at the TRIM, not its own.** A territory pinches to a wedge between its
    neighbours as it reaches its node, and no ribbon is drawn there — the
    junction is area. Read where it stands, every street's two end vertices
    would publish a road a few centimetres wide, and `clearance`, the fence and
    every registered post read this table as the carriageway. The ribbon's own
    mouth is the nearest thing to what the table meant before: today's end
    vertex publishes a half-width the trim has also cut away.

    After `_assign_trims`, because the trims are that function's own answer. An
    edge too short to draw reads its middle.
    """
    points = edge.points
    along = plan_lengths(points)
    low, high = edge.trim_start_m, float(along[-1]) - edge.trim_end_m
    if high <= low:
        low = high = 0.5 * float(along[-1])
    at = np.clip(plan_lengths(_polyline(published)), low, high)
    rows = np.vstack([_at(points, along, distance) for distance in at])
    upper, lower, _ = _clamped_rails(
        rows[:, _WIDTH], rows[:, _RIM_LEFT], rows[:, _RIM_RIGHT], edge.shift_m, exact=True
    )
    edge_id = int(published["id"])
    report.carriageway[edge_id] = [round(float(half), 3) for half in 0.5 * (upper - lower)]
    report.carriageway_offset[edge_id] = [round(float(mid), 3) for mid in 0.5 * (upper + lower)]
    # 🔴 **And the CORRIDOR beside it, kerb to kerb through every share.** The
    # table above is what is drawn for this centreline, which on a carriageway
    # several centrelines share is its SHARE — and a share is not a width a car
    # is confined to (`Q57`). `clearance` measures its corridor across this one.
    # Never narrower than the ribbon: where no kerb answers inside the ray's cap
    # the reach is the cap, and a run past its rectangle keeps the ribbon's own.
    stations = edge.stations
    if stations is not None:
        left = np.maximum(np.interp(at, stations.along_m, stations.left_kerb_m), upper)
        right = np.maximum(np.interp(at, stations.along_m, stations.right_kerb_m), -lower)
        report.corridor[edge_id] = (
            [round(float(half), 3) for half in 0.5 * (left + right)],
            [round(float(mid), 3) for mid in 0.5 * (left - right)],
        )


def _stations_kept(stations: surface_region.Stations, tolerance_m: float) -> np.ndarray:
    """The stations a straight line between their neighbours cannot stand in for.

    Douglas-Peucker over `(along, left, right)`, both sides judged together, with
    every published vertex and every station where a side changes between kerb
    and share held fixed. HyD's kerbs are polylines, so a territory's extents
    along a straight street are piecewise linear and this keeps the breakpoints.

    🔴 **Not optional.** Every ribbon station is two carriageway triangles and
    four kerb strips, and `_rail_stations`' pruning — what kept the kerbs cheap —
    cannot fire on a rail that moves a centimetre a station. Unpruned, Wan Chai's
    road surface is 226,824 triangles against the 32,177 it replaces.
    """
    count = len(stations.along_m)
    keep = np.zeros(count, dtype=bool)
    keep[stations.vertex_station] = True
    keep[[0, count - 1]] = True
    for kerb in (stations.kerb_left, stations.kerb_right):
        change = np.flatnonzero(np.diff(kerb) != 0.0)
        keep[change] = keep[change + 1] = True
    spans = [
        (low, high) for low, high in zip(*(np.flatnonzero(keep)[i:] for i in (0, 1)), strict=False)
    ]
    while spans:
        low, high = spans.pop()
        if high - low < 2:
            continue
        inner = np.arange(low + 1, high)
        t = (stations.along_m[inner] - stations.along_m[low]) / max(
            stations.along_m[high] - stations.along_m[low], 1e-9
        )
        worst = np.zeros(len(inner))
        for side in (stations.left_m, stations.right_m):
            worst = np.maximum(
                worst, np.abs(side[inner] - (side[low] + t * (side[high] - side[low])))
            )
        if worst.max() <= tolerance_m:
            continue
        split = int(inner[np.argmax(worst)])
        keep[split] = True
        spans += [(low, split), (split, high)]
    return np.flatnonzero(keep)


def _with_territory_stations(
    points: np.ndarray, stations: surface_region.Stations | None, tolerance_m: float = 0.0
) -> np.ndarray:
    """The published polyline with the territory's own stations added to it.

    🔴 **The rim and kerb columns of an added row are the MEASURED values, never
    the lerp `_at` would give.** A straight street is two vertices, both at
    nodes, where a territory pinches to a wedge — interpolating between those is
    a sliver the length of the block, which is why the region stage stations
    every edge at all.

    Every other column is `_at`'s, so an added station lies ON the published
    polyline with the right height and half-width, and the shape, the plan
    length and the mitres are unchanged — `_insert_stations`' own property.
    """
    if stations is None or len(points) < 2:
        return points
    along = plan_lengths(points)
    added = np.setdiff1d(_stations_kept(stations, tolerance_m), stations.vertex_station)
    # Which territory station each row is: the published vertices first, in their
    # own order, then the added ones — the same order the rows are stacked in.
    station = np.concatenate([stations.vertex_station, added])
    if len(added):
        rows = np.vstack([_at(points, along, stations.along_m[index]) for index in added])
        points = np.vstack([points, rows])
    # 🔴 **ASSIGNED, and `min` only against a deck rim.** The first build took
    # `min(lerped rim, measured)` for an added row, and the lerp runs between the
    # two END vertices — the wedges — so it won everywhere and drew BOWRINGTON
    # ROAD 1.2 m wide down the middle of its own 6.5 m territory.
    points[:, _RIM_LEFT] = np.minimum(points[:, _RIM_LEFT], stations.left_m[station])
    points[:, _RIM_RIGHT] = np.minimum(points[:, _RIM_RIGHT], stations.right_m[station])
    points[:, _KERB_LEFT] = stations.kerb_left[station]
    points[:, _KERB_RIGHT] = stations.kerb_right[station]
    # Stable, so a station landing on a published vertex keeps the vertex first.
    order = np.argsort(np.concatenate([along, stations.along_m[added]]), kind="stable")
    return points[order]


def _lanes_forward_code(published: dict, report: SurfaceReport) -> int:
    """The graph's `lanes_forward` in the codec's two bits (`Q126`).

    `published["lanes_forward"]`, never a `.get`, for the reason `offset_m`
    gives above: `read_graph` pins the schema, so the key is there on every
    graph this can open. `null` and a one-way edge both pack to 0 — the shader
    reads 0 as "draw the middle", which is what a one-way edge's `lanes` would
    otherwise say by mistake — and a split the field cannot hold is written as
    0 and counted rather than raised over, so a region with one such road
    still builds.
    """
    forward = published["lanes_forward"]
    if forward is None or published["direction"] != BOTH:
        return 0
    forward = int(forward)
    if forward > MARKING_LANES_FORWARD_MAX:
        report.lanes_forward_unsaid += 1
        return 0
    return forward


def _deck_rims(published: dict, count: int) -> tuple[np.ndarray, np.ndarray, int]:
    """One published edge's deck rims per vertex, an unconstrained pair, and the
    number of rims `Q113` discarded.

    `Q107`. `[left_m, right_m]` in `mitres`' own frame, straight off the graph —
    `roads._reassign` publishes them without a negation because they are
    unsigned reaches already named for their side of travel, and
    `carriageway._rims_at_vertices` says in full why that is not the same
    question as `offset_m`'s sign.

    🔴 **A missing or short list becomes `inf`, which is no constraint at all.**
    Level 0 publishes none and neither do the nine off-grade edges the deck walk
    could not measure, so this is the ordinary case rather than the exceptional
    one. ⚠️ **A LENGTH mismatch takes the same branch rather than raising**, and
    that is deliberate: the rims are per published vertex and so are the
    half-widths, so a disagreement means the graph and this stage disagree about
    the polyline — a state that should draw the ribbon it always drew rather
    than a clamped one built on a mis-aligned array. The count is reported by
    `SurfaceReport.deck_rim_edges`, so it cannot be silent.
    """
    rims = published.get("deck_rim_m") or []
    if len(rims) != count:
        unbounded = np.full(count, np.inf)
        return unbounded, unbounded.copy(), 0
    pairs = np.asarray(rims, dtype=np.float64)
    left, right = pairs[:, 0].copy(), pairs[:, 1].copy()
    # 🔴 **A vertex that is not ON structure has no deck to be cut to (`Q113`).**
    # `carriageway._deck_reach` walks outward from the centreline and reports
    # whatever contiguous slab it finds, and where a ramp descends to grade it
    # finds the last few centimetres of the structure petering out: `e208`
    # FLEMING ROAD's final four vertices published a left rim of **0.100 m**,
    # which is `carriageway.DECK_ACROSS_M` exactly — the smallest non-zero reach
    # that walk can return, meaning the deck was there at the centreline and
    # gone one step later. The clamp took it for a narrow deck and cut the drawn
    # ribbon **5.60 -> 3.15 m**, which `road_markings.gdshader` then painted as
    # two **1.57 m** lanes. Found from the driving seat, twice.
    #
    # ⚠️ **This is `_RIM_LEFT`'s own rule applied to a case it did not
    # anticipate**: absence of a deck is `inf`. A road resting on the ground is
    # as deckless as a road nobody measured, and the graph already says which is
    # which per vertex. It reaches **15 vertices over 4 edges** on this region.
    #
    # ⚠️ **A length mismatch is ignored rather than raised**, for the reason the
    # branch above gives: the two arrays are per published vertex, so a
    # disagreement means the graph and this stage disagree about the polyline,
    # and the honest response is the ribbon that was always drawn.
    on_structure = published.get("on_structure") or []
    if len(on_structure) != count:
        return left, right, 0
    # 🔴 **Counted here and returned, never re-derived by the caller.** The
    # count was taken in `_prepare` under its own guard — `deck_rim_m`'s length
    # rather than `on_structure`'s — so on a graph where the two disagree the
    # report booked discards this function had deliberately not made. A counter
    # describing a population the code did not act on is exactly what the
    # field's own comment exists to detect, so there is one rule behind one
    # guard. It is the rims actually *dropped*: a vertex already carrying `inf`
    # is not a discard.
    adrift = ~np.asarray(on_structure, dtype=bool)
    discarded = int((adrift & (np.isfinite(left) | np.isfinite(right))).sum())
    left[adrift] = np.inf
    right[adrift] = np.inf
    return left, right, discarded


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


class _Rings(NamedTuple):
    """Plan polygons with their bounding boxes taken once (`P3-32`).

    The boxes are asked of every ribbon and the ribbon outlines of every flank,
    so the boxes are the loop invariant: taken per ribbon they were 98% of a
    3.2 s pass over 734 outlines that 76 edges needed.
    """

    rings: list[np.ndarray]
    # `(n, 2)` each: the plan corners of every ring's bounding box.
    lows: np.ndarray
    highs: np.ndarray

    @classmethod
    def of(cls, rings: list[np.ndarray]) -> _Rings:
        if not rings:
            return cls([], np.zeros((0, 2)), np.zeros((0, 2)))
        lows = np.array([ring.min(axis=0) for ring in rings])
        highs = np.array([ring.max(axis=0) for ring in rings])
        return cls(list(rings), lows, highs)

    def touching(self, low: np.ndarray, high: np.ndarray) -> np.ndarray:
        """Indices of the rings whose bounding box meets `[low, high]`."""
        return np.flatnonzero((self.lows <= high).all(axis=1) & (self.highs >= low).all(axis=1))


def _box_rings(
    city: Config, region_id: str, *, sources_root: Path | None, report: SurfaceReport
) -> _Rings:
    """The region's published yellow boxes in plan, or none where the city
    declares no `boxjunctions:` block (`P3-32`).

    Read through `boxsource.read_boxes` — the same reader, the same
    publisher's refusals — so the box this stage widens the road under is the
    box `boxjunctions.py` paints. A box on a structure is refused there and so
    never reaches a level-0 ribbon here. The refusal counters are the box
    stage's to publish (`boxjunctions.json`); this stage records only what it
    was handed.
    """
    spec = city.boxjunctions
    if spec is None:
        return _Rings.of([])
    boxes = read_boxes(
        city,
        spec,
        region_id,
        city.game_transform(region_id),
        BoxReading(),
        sources_root=sources_root,
    )
    report.boxes_read = len(boxes)
    return _Rings.of([box.ring for box in boxes])


def _ring_hits(
    origin: np.ndarray, direction: np.ndarray, ring: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Where the line through `origin` along unit `direction` meets each edge
    of `ring`: the signed distance along the line, and whether it meets that
    edge at all — within the edge's own span, and not parallel to it.

    Signed on purpose: `_ray_exit` keeps the hits ahead, `_ring_crossings` the
    ones within its own segment, and the bound is the caller's.
    """
    starts = ring
    spans = np.roll(ring, -1, axis=0) - starts
    denominator = direction[0] * spans[:, 1] - direction[1] * spans[:, 0]
    offsets = starts - origin
    with np.errstate(divide="ignore", invalid="ignore"):
        along = (offsets[:, 0] * spans[:, 1] - offsets[:, 1] * spans[:, 0]) / denominator
        across = (offsets[:, 0] * direction[1] - offsets[:, 1] * direction[0]) / denominator
    hit = (np.abs(denominator) > _MIN_SEGMENT_M) & (across >= 0.0) & (across <= 1.0)
    return along, hit


def _ray_exit(origin: np.ndarray, direction: np.ndarray, ring: np.ndarray) -> float | None:
    """Distance along `direction` from `origin` to the first edge of `ring`, or None."""
    along, hit = _ring_hits(origin, direction, ring)
    hit &= along > 0.0
    return float(along[hit].min()) if hit.any() else None


def _add_paint_stations(edge: _Edge, boxes: _Rings) -> int:
    """Give a ribbon the stations its box junctions need (`P3-32`).

    Where the centreline runs inside a box, a station every `_PAINT_STATION_M`
    and one at each crossing of the box edge, so the flank drawn out to the
    paint starts and stops where the paint does. Within the drawn extent only,
    like `_add_kerb_stations`: a box under a junction cap is capped already.
    """
    if not boxes.rings or len(edge.points) < 2:
        return 0
    along = plan_lengths(edge.points)
    plan = edge.points[:, [0, 2]]
    low, high = edge.trim_start_m, edge.length_m - edge.trim_end_m
    if high - low <= _PAINT_STATION_M:
        return 0
    touching = boxes.touching(plan.min(axis=0), plan.max(axis=0))
    if not len(touching):
        return 0
    wanted: list[float] = []
    samples = np.arange(low, high, _PAINT_STATION_M)
    positions = np.column_stack(
        [np.interp(samples, along, plan[:, 0]), np.interp(samples, along, plan[:, 1])]
    )
    for ring in (boxes.rings[index] for index in touching):
        wanted.extend(samples[inside_polygon(positions, ring)].tolist())
        # The crossings, exactly: each polyline segment against each ring edge,
        # rather than between two samples that happen to disagree — a sample
        # landing on the box edge itself would lose the crossing.
        wanted.extend(
            crossing for crossing in _ring_crossings(plan, along, ring) if low < crossing < high
        )
    if not wanted:
        return 0
    edge.points, inserted = _insert_stations(edge.points, wanted)
    edge.points[inserted, _INSERTED] = 1.0
    return len(inserted)


def _ring_crossings(plan: np.ndarray, along: np.ndarray, ring: np.ndarray) -> list[float]:
    """Distances along a polyline at which it crosses the edges of a ring."""
    found: list[float] = []
    for index in range(len(plan) - 1):
        origin = plan[index]
        step = plan[index + 1] - origin
        length = float(np.hypot(*step))
        if length <= _MIN_SEGMENT_M:
            continue
        distance, hit = _ring_hits(origin, step / length, ring)
        hit &= (distance >= 0.0) & (distance <= length)
        found.extend((along[index] + distance[hit]).tolist())
    return found


def _height_along(ribbon: np.ndarray, point: np.ndarray) -> float:
    """A ribbon's height under a plan point: interpolated along its centreline
    at the nearest station, which is its height there because a ribbon is flat
    across (`DrawnSurface`)."""
    plan = ribbon[:, [0, 2]]
    along, distance = _project_plan(plan[:-1], plan[1:] - plan[:-1], point)
    nearest = int(distance.argmin())
    step = ribbon[nearest + 1, 1] - ribbon[nearest, 1]
    return float(ribbon[nearest, 1] + along[nearest] * step)


def _paint_flanks(
    edge: _Edge,
    boxes: _Rings,
    outlines: _Rings,
    ribbons: list[np.ndarray],
    own: int | None,
    style: RoadSurface,
    report: SurfaceReport,
) -> list[np.ndarray]:
    """The strips between a ribbon's rails and the paint of the box it runs
    through, one convex quad per station pair and side (`P3-32`).

    A box is a publisher's statement that the ground under it is carriageway
    (`Q104`), and where it runs past the drawn rail the ribbon is narrower
    than the road. The flank is drawn as a cap — surface material, no lane
    coordinate — rather than by widening the ribbon, so `carriageway[]`, the
    lane coordinate and everything registered against the rail are untouched:
    the ribbon yields to the paint without moving. Its kerb under the flank is
    hidden like any kerb under a cap. ⚠️ **A flank thinner than the kerb is
    not drawn**: the kerb would stand up through it, and paint that far past
    the rail is `box_extent.py`'s registration residue, not a road.

    🔴 **A flank stops one kerb width into the next ribbon it meets**, not at
    the box edge beyond it. A box across a dual carriageway covers both
    carriageways and the median, and a flank grown from one carriageway's
    inner rail to the far edge of the box would lie over the other carriageway
    at this ribbon's height — a step where the two disagree. `outlines` are the
    level-0 ribbons' plan outlines and `ribbons` their centrelines, this one at
    `own`; the overlap is the kerb width so the other ribbon's kerb, hidden
    under the flank, leaves no crack. ⚠️ **Where it stops in another ribbon the
    far corners take THAT ribbon's height**, so the two carriageways meet on a
    ramp across the median: at this ribbon's height the tip stood 1.5-1.7 cm
    proud of HUNG HING ROAD's other carriageway and buried four paint
    triangles under a lip `paint_clearance.py` could see and a frame could not.

    🔴 **A flank runs to where the RAIL leaves the box, not to the last station
    inside it** (`Q92`'s third class, 2026-09-16). `_add_paint_stations` puts a
    station at each crossing of the CENTRELINE with the box edge, and where
    that edge is oblique to the road the rail crosses it somewhere else — at
    HUNG HING ROAD box 8, 0.16 m further along — so the quad per station pair
    stopped at the last station whose rail point was inside the paint and left
    the strip between that station's ray and the rail's own exit undrawn: a
    void wedge inside the box, into which the other carriageway's flank poked
    its tip 8 cm lower, and a paint vertex over it took the lower edge. The
    closing piece per rail end is the hull of the last kept station's rail
    point and paint corner, the point where the rail segment crosses the ring,
    that point's own paint corner (its ray, clipped by the neighbours exactly
    as a station's is), and the ring's own corners between the two paint
    corners where both lie on the ring — so it cannot leave the box, and where
    the ray at the crossing points out of the box it is the wedge's third
    corner itself. Nothing new to set: the crossing is the rail's, the reach
    rule is the stations', and the kerb tolerance is the one the clip carries.
    Counted apart in `paint_flank_ends` so a closing that stops firing is
    visible; `flanks` includes them.
    """
    if not boxes.rings or edge.ribbon is None or edge.left is None or edge.right is None:
        return []
    rails = np.vstack([edge.left, edge.right])
    painted = boxes.touching(rails.min(axis=0), rails.max(axis=0))
    if not len(painted):
        return []
    centres = edge.ribbon[:, [0, 2]]
    heights = edge.ribbon[:, 1]
    quads: list[np.ndarray] = []
    for rail in (edge.left, edge.right):
        outward = rail - centres
        length = np.hypot(outward[:, 0], outward[:, 1])
        length[length <= _MIN_SEGMENT_M] = np.inf
        outward = outward / length[:, None]
        reach = np.zeros(len(rail))
        for ring in (boxes.rings[index] for index in painted):
            for index in np.flatnonzero(inside_polygon(rail, ring)):
                exit_m = _ray_exit(rail[index], outward[index], ring)
                if exit_m is not None:
                    reach[index] = max(reach[index], exit_m)
        # ⚠️ The box the ray may leave, not the rail's: the flank reaches out.
        furthest = float(reach.max())
        far_heights = heights.copy()
        clipped = np.zeros(len(rail), dtype=bool)
        met = outlines.touching(rail.min(axis=0) - furthest, rail.max(axis=0) + furthest)
        neighbours = [(outlines.rings[index], ribbons[index]) for index in met if index != own]
        for index in np.flatnonzero(reach > 0.0):
            reach[index], far_heights[index], clipped[index] = _clip_to_neighbours(
                rail[index], outward[index], reach[index], heights[index], neighbours, style
            )
        keep = reach >= style.kerb_width_m
        for index in np.flatnonzero(keep[:-1] & keep[1:]):
            near, far = index, index + 1
            paint_near = rail[near] + outward[near] * reach[near]
            paint_far = rail[far] + outward[far] * reach[far]
            corners = np.array(
                [
                    [rail[near, 0], heights[near], rail[near, 1]],
                    [paint_near[0], far_heights[near], paint_near[1]],
                    [paint_far[0], far_heights[far], paint_far[1]],
                    [rail[far, 0], heights[far], rail[far, 1]],
                ]
            )
            quad = hull(corners)
            if len(quad) >= 3:
                quads.append(quad)
                report.paint_flank_m2 += 0.5 * abs(_shoelace(quad))
        # 🔴 The closing piece at each end of a run: from the last kept station
        # to where the rail itself leaves the box. See the docstring.
        rings_here = [boxes.rings[index] for index in painted]
        for index in np.flatnonzero(keep[:-1] != keep[1:]):
            kept, other = (index, index + 1) if keep[index] else (index + 1, index)
            crossing = _rail_leaves(rail[kept], rail[other], rings_here)
            if crossing is None:
                continue
            point, ring, along = crossing
            # 🔴 Within one paint-station pitch of the last station, or not at
            # all. A run `_add_paint_stations` stationed for this box has a
            # station within `_PAINT_STATION_M` of where its rail leaves the
            # paint; a rail inside a box with no station that close was never
            # stationed for it — its centreline runs outside the box — and the
            # stage has never drawn its flank. Closing those on the first build
            # drew 3.3-8.7 m sweeps at box 13 and box 8's south margin, over
            # another carriageway and under a junction cap, at up to 0.45 m
            # from the surface already there. The pitch is the stationing's
            # own number, not a second one.
            if float(np.hypot(*(point - rail[kept]))) > _PAINT_STATION_M:
                continue
            out = outward[kept] + along * (outward[other] - outward[kept])
            norm = float(np.hypot(*out))
            if norm <= _MIN_SEGMENT_M:
                continue
            out = out / norm
            height = float(heights[kept] + along * (heights[other] - heights[kept]))
            # ⚠️ The neighbours within THIS ray's reach, not the stations':
            # where the box edge is oblique the ray from the crossing runs
            # inside the box for longer than any station's did, and a clip
            # searched to the stations' reach let it cross the other
            # carriageway — 12 m² at 0.28 m under it, on the first build.
            reach_here = _reach_from_ring(point, out, ring)
            grown = reach_here + style.kerb_width_m
            near_here = outlines.touching(point - grown, point + grown)
            neighbours_here = [
                (outlines.rings[index], ribbons[index]) for index in near_here if index != own
            ]
            reach_here, far_height, clipped_here = _clip_to_neighbours(
                point, out, reach_here, height, neighbours_here, style
            )
            paint_kept = rail[kept] + outward[kept] * reach[kept]
            paint_here = point + out * reach_here
            corners = [
                (rail[kept], float(heights[kept])),
                (paint_kept, float(far_heights[kept])),
                (paint_here, far_height),
                (point, height),
            ]
            if not clipped[kept] and not clipped_here:
                corners.extend(
                    (corner, float(far_heights[kept]))
                    for corner in _ring_between(ring, paint_kept, paint_here)
                )
            piece = hull(np.array([[x, h, z] for (x, z), h in corners]))
            if len(piece) >= 3:
                quads.append(piece)
                report.paint_flank_m2 += 0.5 * abs(_shoelace(piece))
                report.paint_flank_ends += 1
    report.paint_flanks += len(quads)
    return quads


def _clip_to_neighbours(
    point: np.ndarray,
    outward: np.ndarray,
    reach: float,
    height: float,
    neighbours: list[tuple[np.ndarray, np.ndarray]],
    style: RoadSurface,
) -> tuple[float, float, bool]:
    """A flank ray's reach, stopped one kerb width into the first neighbouring
    ribbon outline it enters, with the far corner's height from that ribbon —
    the rule `_paint_flanks` states — and whether it was stopped."""
    far_height = height
    clipped = False
    for outline, ribbon in neighbours:
        entry = _ray_exit(point, outward, outline)
        if entry is not None and entry + style.kerb_width_m < reach:
            reach = entry + style.kerb_width_m
            far_height = _height_along(ribbon, point + outward * reach)
            clipped = True
    return reach, far_height, clipped


def _rail_leaves(
    start: np.ndarray, stop: np.ndarray, rings: list[np.ndarray]
) -> tuple[np.ndarray, np.ndarray, float] | None:
    """Where the rail segment from `start` first crosses the edge of any of
    `rings` on its way to `stop`: the crossing point, the ring crossed and the
    parameter along the segment. None where it crosses nothing."""
    step = stop - start
    length = float(np.hypot(*step))
    if length <= _MIN_SEGMENT_M:
        return None
    direction = step / length
    best: tuple[float, np.ndarray] | None = None
    for ring in rings:
        along, hit = _ring_hits(start, direction, ring)
        hit &= (along > _MIN_SEGMENT_M) & (along < length - _MIN_SEGMENT_M)
        if hit.any():
            nearest = float(along[hit].min())
            if best is None or nearest < best[0]:
                best = (nearest, ring)
    if best is None:
        return None
    return start + direction * best[0], best[1], best[0] / length


def _reach_from_ring(point: np.ndarray, outward: np.ndarray, ring: np.ndarray) -> float:
    """How far a ray from a point ON a ring's edge runs before it leaves the
    ring: zero where it points straight out, the traverse to the far side where
    the edge is oblique and the ray runs inside. The edge the point sits on is
    a hit at zero, kept — a rounding survivor a hair behind must not lose it to
    a far edge ahead."""
    along, hit = _ring_hits(point, outward, ring)
    hit &= along >= -_MIN_SEGMENT_M
    return max(0.0, float(along[hit].min())) if hit.any() else 0.0


def _edge_of(ring: np.ndarray, point: np.ndarray) -> int | None:
    """The index of the ring edge a plan point lies on, or None if it is off
    the ring by more than `_MIN_SEGMENT_M`."""
    starts = ring
    spans = np.roll(ring, -1, axis=0) - starts
    _, distance = _project_plan(starts, spans, point)
    nearest = int(distance.argmin())
    return nearest if distance[nearest] <= _MIN_SEGMENT_M else None


def _ring_between(ring: np.ndarray, start: np.ndarray, stop: np.ndarray) -> list[np.ndarray]:
    """The ring's corners between two points on its edges, the shorter way
    round — none where the points share an edge or either is off the ring."""
    first, last = _edge_of(ring, start), _edge_of(ring, stop)
    if first is None or last is None or first == last:
        return []
    count = len(ring)
    forward = [ring[(first + step) % count] for step in range(1, (last - first) % count + 1)]
    backward = [ring[(first - step) % count] for step in range(0, (first - last) % count)]

    def walked(path: list[np.ndarray]) -> float:
        points = np.array([start, *path, stop])
        return float(np.hypot(*(np.diff(points, axis=0)).T).sum())

    return forward if walked(forward) <= walked(backward) else backward


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

    🔴 **`structure_bounded` is published and deliberately NOT read here, and
    that is a measured decision rather than an omission (`Q19`, 2026-08-30).**
    Schema 8 adds a second per-station flag saying a station has structure
    standing *beside* it at bumper height — the case `on_structure` cannot see,
    because it is height provenance and an approach ramp sampled off the terrain
    reports every station off structure. Narrowing on the union was built,
    validated and **measured**: 43 edges narrowed, 0 widened, and the region's
    overhang p50 fell 1.59 → 1.55 m.

    ⚠️ **It was refused because it made the city less drivable, not because it
    was wrong.** Where the centreline is itself inside the wall, the clear
    asphalt is a strip *off* the centre — `e55`'s was 4.49 m off it inside a
    12.48 m ribbon — and narrowing to the surveyed 5.57 m puts that strip
    outside the ribbon. `carriageway_occupancy.py` read `e55` 2.00 → **0.00 m**,
    `e398` 2.50 → 0.00 and `e788` 0.48 → 0.00. Narrowing **exposes** `Q19`'s
    centreline defect rather than fixing it, which is what that entry has said
    since 2026-08-21 about `lanes`, `width_m` and the floor: no width rule moves
    a centreline.

    ⚠️ **So do not "finish the job" by reading the flag here.** The flag's
    consumer is whatever moves or refuses a centreline; until that exists,
    reading it trades invented asphalt for an impassable interchange. The
    metres are still reported, from `_on_structure_length_m`, so the population
    stays visible without being acted on.
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


def _on_structure_length_m(published: dict, key: str) -> float:
    """Metres of this edge's centreline under one structure flag, if it is level 0.

    `Q23`'s measurement, reproduced by the stage that acts on it, and `Q19`'s
    beside it — one function because the two are the same reduction over
    different flags, and writing it twice would let the halves drift into
    reporting incomparable lengths. Level 0 only: an off-grade edge is on
    structure along its whole length by definition and counting it would bury
    the number this exists to report.

    The trapezoid rule on the flag — a segment counts fully when both its ends
    are flagged and half when one is. A flag is a property of a station and
    length is a property of what lies between two of them, so some rule has to
    bridge the two; this one is symmetric, and it cannot report a length for an
    edge with no flag set at all.
    """
    if published["elevation_level"] != 0:
        return 0.0
    flags = np.asarray(published.get(key) or [], dtype=float)
    if len(flags) < 2 or not flags.any():
        return 0.0
    steps = plan_steps(_polyline(published))
    return float((steps * 0.5 * (flags[:-1] + flags[1:])).sum())


def _polyline(published: dict) -> np.ndarray:
    return np.asarray(published["polyline"], dtype=np.float64)


def _clamped_rails(
    half: np.ndarray,
    rim_left: np.ndarray,
    rim_right: np.ndarray,
    shift: float,
    *,
    exact: bool = False,
) -> tuple[np.ndarray, np.ndarray, int]:
    """The two rails, cut back to the deck's own edges where there is one.

    `Q107`. The ribbon wants to run `[shift - half, shift + half]`; the deck
    runs `[-right, +left]`. Where the paint reaches past the structure it is cut
    to it, per station, on each side independently — which is the whole of the
    fix, because `width_m` and `offset_m` are one number each for a deck that
    changes width along its length (`Q103` measured per-edge `over p50` getting
    *worse* on 22 of 35 edges for exactly that reason).

    🔴 **It cuts and never extends.** `min`/`max` against the ribbon's own rails
    means a deck WIDER than the paint changes nothing — the clamp cannot invent
    carriageway, which is `Q54`'s rule and the reason this is licensed at all.
    `Q105` priced it as paint and explicitly not as a width: `width_m` does not
    move here, and a deck rim is one contiguous run of structure that at an
    interchange is not this carriageway's.

    🔴 **A station whose rails would cross keeps the ribbon it had.** That is
    the fallback `Q105` said any build owes: where the drawn ribbon lies wholly
    off its own deck the clamp has no answer — `upper < lower` is a carriageway
    of negative width — and inventing one by collapsing to zero would put a hole
    in the road. It reads **0 in this region**, which is a measurement and not a
    construction: the shift is a per-edge median while the rims are local, so a
    station can reach it, and
    `test_crossing_rails_keep_the_unclamped_ribbon_and_are_counted` is what says
    the counter is not stuck. A rise is a finding to go and look at.

    ⚠️ **Absence of a deck is `inf`** (see `_RIM_LEFT`), so every level-0 edge
    takes the untouched branch by arithmetic rather than by a test.

    ⚠️ **Plain arrays rather than the points matrix, because it is applied
    TWICE** — to the ribbon's own stations for the geometry, and to the
    published vertices for `roadsurface.json`'s table. Those are different
    polylines (`dedupe` drops stations, `_add_kerb_stations` inserts them), and
    a second expression of this arithmetic for the manifest is a second thing to
    drift from the road it claims to describe.

    🔴 **THREE things it deliberately does not reach, recorded rather than
    quietly left (`Q107`).** Each needs rim data at a station the deck walk
    refuses, so none is fixable by moving this function:

    * **The junction caps.** `end_half_width_m` reads the unclamped `_WIDTH`, so
      `_assign_trims`' radius and `_through_corners`' arms are sized before the
      cut and the cap hull can re-draw paint the clamp removed. The hull only
      ever grows, so it will.
    * **The ends of every clamped edge.** `carriageway._stations` skips stations
      within `JUNCTION_M` of a node, so an edge's first and last few metres
      publish no rim and `np.interp` flat-extrapolates the nearest one inward —
      and a deck normally *flares* at a junction, so the ends are over-cut in
      exactly the place the caps are drawn uncut.
    * **The kerb and its lip**, drawn at `± kerb_width_m` outside the clamped
      rails, so 0.5 m of kerb block still overhangs at every clamped station.
      ⚠️ **No instrument can see it**: `overhang.py` and `deck_margin.py` both
      read the carriageway half-width from the manifest, which is now the
      clamped one.
    """
    if exact:
        # 🔴 **`exact` is `P3-33c`'s and it is the one place this EXTENDS.** The
        # rims are then the edge's territory — the carriageway a publisher drew,
        # nearest this centreline — and the rails ARE those, wider than
        # `width_m` as readily as narrower. That is not `Q54`'s invented
        # carriageway: the invented number here is `half`, and it is what yields.
        # A station with no territory (a run past its region's rectangle, `Q116`)
        # has rims of zero, crosses, and keeps the plain ribbon below.
        upper = np.where(np.isfinite(rim_left), rim_left, shift + half)
        lower = np.where(np.isfinite(rim_right), -rim_right, shift - half)
    else:
        upper = np.minimum(shift + half, rim_left)
        lower = np.maximum(shift - half, -rim_right)
    # ⚠️ **`_MIN_SEGMENT_M` and not zero.** Rails that merely touch leave a
    # zero-width quad, which `_Builder.build` collapses and which reads as a
    # gap in the collider rather than as a narrow road.
    crossed = (upper - lower) <= _MIN_SEGMENT_M
    if crossed.any():
        upper = np.where(crossed, shift + half, upper)
        lower = np.where(crossed, shift - half, lower)
    return upper, lower, int(crossed.sum())


def _shape(edge: _Edge, style: RoadSurface) -> None:
    """Trim the edge back from its junctions and offset what is left."""
    points = dedupe(trim(edge.points, edge.trim_start_m, edge.trim_end_m))
    if len(points) < 2:
        return
    edge.ribbon = points
    edge.offsets = mitres(points)
    half = points[:, _WIDTH]
    # `mitres` is left of travel and `shift_m` is published in that same frame
    # (`roads.Edge.offset_m`), so it adds to both sides — carrying the ribbon
    # bodily across without changing its width. `boundary` takes a signed
    # distance, so the right-hand side is `-half + shift` rather than
    # `-(half + shift)`; the kerb lips ride along with the sides they belong to.
    shift = edge.shift_m
    # ⚠️ The refusal count is dropped here on purpose: `_prepare` already
    # counted it over the published stations, and adding the ribbon's own — a
    # different polyline, after `dedupe` and `_add_kerb_stations` — would report
    # one quantity twice under one name.
    upper, lower, _ = _clamped_rails(
        half, points[:, _RIM_LEFT], points[:, _RIM_RIGHT], shift, exact=edge.territory
    )
    if edge.territory:
        # A side that ends in another territory is asphalt, not a kerb. Set here
        # and left alone by `_hide_buried_kerbs`: territories cannot overlap, so
        # there is nothing for a kerb to be buried under.
        # ⚠️ One flag per QUAD, which is `_runs`' unit and not a station's: a
        # quad keeps its kerb where both stations it spans end at one.
        kerb_left, kerb_right = points[:, _KERB_LEFT] >= 0.5, points[:, _KERB_RIGHT] >= 0.5
        edge.kerb_left = kerb_left[:-1] & kerb_left[1:]
        edge.kerb_right = kerb_right[:-1] & kerb_right[1:]
    edge.left = boundary(points, edge.offsets, upper)
    edge.right = boundary(points, edge.offsets, lower)
    edge.lip_left = boundary(points, edge.offsets, upper + style.kerb_width_m)
    edge.lip_right = boundary(points, edge.offsets, lower - style.kerb_width_m)


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
        foreign = "foreign" in edge
        for node, at_start in ((edge["from"], True), (edge["to"], False)):
            groups[(node, geometry.level)].append(
                _End(edge=index, at_start=at_start, foreign=foreign)
            )
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
            # The flare is this END's own, read off its territory (`Q129`): a
            # ribbon starts where its carriageway has settled, and the radius is
            # what is left for an edge with no territory to read.
            if end.at_start:
                reach = max(radius, edge.flare_start_m)
                edge.trim_start_m = min(reach, ceiling)
                edge.clamped_start = ceiling < reach
            else:
                reach = max(radius, edge.flare_end_m)
                edge.trim_end_m = min(reach, ceiling)
                edge.clamped_end = ceiling < reach
            clamped = ceiling < reach
            if end.foreign:
                continue
            report.trimmed_ends += 1
            if clamped:
                report.clamped_trims += 1


def _stub_clusters(
    ends: dict[tuple[int, int], list[_End]],
    edges: list[_Edge],
    report: SurfaceReport,
    *,
    owned: Callable[[int], bool],
) -> list[list[tuple[int, int]]]:
    """The `(node, level)` groups that one junction cap should close together.

    `P3-31`. Union-find over the stubs: each joins the two groups at its ends,
    and a component of two or more groups is a cluster. Same level only, which
    `_ends_by_node_and_level`'s key already enforces — a stub is one edge on one
    level, so it can only ever join two groups of that level. Groups no stub
    touches are returned as singletons, so the caller has one list to cap.

    🔴 **A stub joins two nodes THIS region owns, or it joins nothing.** The
    neighbour's build never sees an owned stub — it reads the run as a foreign
    mouth at most (`P5-7f`) — so it caps the far node on its own, per node,
    exactly as before `P3-31`. If this build clustered across the seam the two
    would either both draw that node's junction or neither would, depending on
    which node the cluster was named by; refusing the stub leaves the seam
    drawn as it was, one cap per node and no hole. A foreign stub is refused
    for the same reason from the other side. Every node of a cluster is
    therefore owned, and `build_region`'s ownership test on its lowest node is
    the same test every singleton gets.

    Sorted by lowest key, and each cluster sorted, so the caps are emitted in
    an order that does not depend on dictionary history.
    """
    keys_of_edge: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for key, group in ends.items():
        for end in group:
            if not end.foreign and edges[end.edge].is_stub and owned(key[0]):
                keys_of_edge[end.edge].append(key)
    # A stub with one end at an owned node and the other across the line has
    # gathered one key: it joins nothing, and it is not a stub of this region.
    keys_of_edge = {edge: keys for edge, keys in keys_of_edge.items() if len(keys) == 2}

    parent: dict[tuple[int, int], tuple[int, int]] = {}

    def find(key: tuple[int, int]) -> tuple[int, int]:
        while parent.setdefault(key, key) != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for keys in keys_of_edge.values():
        # Both ends are in a group of two or more — a trim is only assigned
        # there — so a stub always has exactly two keys, one per end.
        first, second = keys
        parent[find(first)] = find(second)
    report.stub_edges += len(keys_of_edge)

    members: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for key in ends:
        members[find(key)].append(key)
    clusters = sorted(sorted(keys) for keys in members.values())
    for keys in clusters:
        if len(keys) >= 2:
            report.clusters += 1
            report.cluster_nodes += len(keys)
    return clusters


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


def _read_offside(
    edges: list[_Edge], style: RoadSurface, report: SurfaceReport
) -> dict[tuple[int, int], float]:
    """What each edge's offside boundary actually is, once every ribbon exists.

    Returns the mutual opposed pairs it found, by **list position**, for
    `build_region` to publish against the graph's own ids (`Q125`).

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

    🔴 **Pairs are found geometrically, and shared endpoints found six of them.**
    `P1-4` recorded the endpoint rule as a lower bound and it was a far lower one
    than "lower bound" suggests: Road Network v2 gives each carriageway of a dual
    road its own nodes, so the two halves share a node where they meet a junction
    and almost never share both. **12 of this region's 621 one-way level-0 edges**
    matched, and the other 609 drew two overlapping ribbons with nothing between
    the flows — which is what a player sees from the driving seat on HARBOUR ROAD
    and on every other dual carriageway here. `_opposed_gaps` is what replaced it.

    ⚠️ **A missed pair still costs the centre line and never a yellow line down
    the middle of a road**, and that is unchanged: the two markings rest on
    different tests. The kerbside yellow needs only `offside_kerb`, which comes
    from the buried-kerb geometry above and is decided whether or not a pair was
    identified.
    """
    gaps = _opposed_gaps(edges, style, report)
    pairs: dict[tuple[int, int], float] = {}

    for index, edge in enumerate(edges):
        # `None` means the pass had nothing to say. It is unreachable for an edge
        # that draws — `_shape` sets `lip_right` beside `right` — and the reading
        # that matches it is "no neighbour objected", so the kerb stands.
        edge.offside_kerb = edge.kerb_right is None or bool(edge.kerb_right.all())

        vote = gaps.get(index)
        if vote is None:
            continue
        gap = vote.gap_m
        report.opposed_pair_ends += 1
        # 🔴 **Collected before the range guard below, and that is deliberate.**
        # `centre_step` is what the *shader* can draw and `steps < 8 * lanes` is
        # what its lane coordinate can reach; the geometry `roadmarks.py` draws
        # between two centrelines has no such limit, because it is not expressed
        # in either half's lane coordinate. Collecting after the guard would hide
        # a pair from the fallback for a reason that does not apply to it.
        # ⚠️ Once per pair, by list position, so the unordered key is what
        # de-duplicates the two ends rather than a caller remembering to.
        pairs[(min(index, vote.partner), max(index, vote.partner))] = gap

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

    return pairs


class _Ribbon(NamedTuple):
    """One one-way ribbon as the opposed-pair search sees it.

    ⚠️ **Scalars, not the `(2,)` arrays they were read from, and that is measured
    rather than preferred.** The filter in `_opposed_gaps` runs over every ordered
    pair of one-way ribbons — **387,122** on this region — and throws away 99.8%
    of them, so what it costs is numpy's per-call dispatch and not the geometry it
    guards. The identical loop reading `np.ndarray` bounds and taking `.any()`
    ran **395 ms** against **34 ms** here, while `edge_distances` — the thing being
    guarded — costs **30 ms** in total. Bundling them in one tuple rather than four
    dicts is the same move for the same reason: one lookup per candidate.
    """

    plan: np.ndarray
    # Unit chord, and zero where the ribbon has none — a loop edge, whose two ends
    # coincide. Zero fails every anti-parallel test rather than passing it, which
    # is the right way round: a ribbon with no direction has no opposed half.
    ux: float
    uz: float
    low_x: float
    low_z: float
    high_x: float
    high_z: float


class _Vote(NamedTuple):
    """One ribbon's chosen opposed half, and how far away it runs."""

    partner: int
    gap_m: float


def _opposed_gaps(
    edges: list[_Edge], style: RoadSurface, report: SurfaceReport
) -> dict[int, _Vote]:
    """Each opposed half's partner and how far apart the two run, by list position.

    ⚠️ **The partner travels with the gap since `Q125`, and it is the same
    vote.** `_read_offside` needs only the separation, because the shader's join
    is an offset from the edge's own centreline; `roadmarks.py` draws the join
    as geometry where no survey line covers it, and a line between two
    carriageways cannot be built from a distance alone. Returning the `_Vote`
    rather than a second search is what keeps the two consumers on one pairing.

    A one-way ribbon's partner is the one-way ribbon at the same elevation level
    that runs **anti-parallel** to it and lies **inside its own drawn width** —
    nearest first, and only where the two choose each other.

    🔴 **The search distance carries no knob, because it is the publish guard
    read backwards.** `_read_offside` puts the join at `gap / 2` metres offside of
    the centreline and refuses anything the ribbon cannot show, which is
    `steps < 8 * lanes`; substituting `_u_metres` reduces that to `gap` under the
    drawn width exactly. So a candidate further away than this could never have
    published, and bounding the search by it adds no value that was not already
    in the range check. `Q72` rejected a pairing rule built on a free radius whose
    count ran 8 → 29 → 49 → 80 as the radius went 10 → 30 m; there is no radius
    here to sweep.

    ⚠️ **`reach` is each edge's OWN width, so the bound is one-sided per vote** —
    A can reach B while B cannot reach A. Mutuality is what closes it: the
    effective bound on a published pair is `min(reach_a, reach_b)`, and that is
    intended rather than incidental, because the join has to be visible on both.

    ⚠️ **The one free value is the angle, so it is config and it is swept** —
    `roads.surface.opposed_pair_bearing_deg`, with the sweep pasted beside it in
    `hong_kong.yaml`. It is deliberately a second value from
    `carriageway_survey.width_bounds.pair_bearing_tolerance_deg`; see the field.

    🔴 **Mutual, and that is not tidiness.** Each half computes the join in its
    own lane coordinate, so two halves naming different partners name different
    lines — the 3.9 m double line `P3-12` shipped on FLEMING ROAD and then
    removed. `opposed_pairs_one_sided` counts the votes that were not returned,
    so a rule that started matching one way only shows up as a number rather than
    as a pair of lines nobody is looking at.

    ⚠️ **Anti-parallel is measured on the ribbon chord, not on the published
    polyline.** Both halves of a pair bend together, so the chord is enough; what
    it must not be is the untrimmed centreline, because a pair found by geometry
    has no shared node to be dragged toward and the trims are what the gap below
    is measured over.
    """
    plans: dict[int, np.ndarray] = {}
    for index, edge in enumerate(edges):
        # `_Edge` carries the published direction verbatim, so this asks the
        # ribbons rather than taking a second list to keep in step with them.
        if edge.direction != FORWARD:
            continue
        plan = _ribbon_plan(edge)
        if plan is not None and len(plan) >= 2:
            plans[index] = plan

    # One `normalise` over every chord rather than a helper per ribbon: the zero
    # row it promises to leave at zero is exactly what a loop edge needs, and
    # `reshape` is what keeps the empty region a `(0, 2)` rather than a `(0,)`.
    order = list(plans)
    chords = np.array([plans[index][-1] - plans[index][0] for index in order]).reshape(-1, 2)
    ribbons = {
        index: _Ribbon(
            plans[index],
            float(unit[0]),
            float(unit[1]),
            float(plans[index][:, 0].min()),
            float(plans[index][:, 1].min()),
            float(plans[index][:, 0].max()),
            float(plans[index][:, 1].max()),
        )
        for index, unit in zip(order, normalise(chords), strict=True)
    }
    # Anti-parallel within the tolerance is a dot product at or below `-cos`,
    # which is one multiply per candidate against an `arccos`.
    limit = -float(np.cos(np.radians(style.opposed_pair_bearing_deg)))
    # Keyed on the unordered pair, because `_pair_gap_m` is symmetric by
    # construction and both orderings are reached: 871 calls over 444 distinct
    # pairs on this region, so half of them were recomputation.
    measured: dict[tuple[int, int], float] = {}

    votes: dict[int, _Vote] = {}
    for index, here in ribbons.items():
        edge = edges[index]
        # 🔴 **The drawn width plus ONE KERB, and the kerb is what makes this a
        # reading rather than a radius** (`Q125`). Two ribbons separated by less
        # than a kerb are not two roads with something between them: they are one
        # drawn surface with a seam, and `_paint_flanks` already decides exactly
        # that question with exactly this value — *a flank thinner than the kerb
        # is not drawn*. EXPO DRIVE EAST is the site: its two carriageways are
        # **10.485 m** apart against a **10.24 m** floor, so they miss by
        # **0.245 m** of seam and the player sees one wide road with opposing
        # traffic on it. ⚠️ **Swept, and flat where it matters**: 50 pairs at
        # +0.00, **54 at +0.25 and +0.50**, 57 at +1.0, 65 at +2.0, 74 at +4.0
        # with `opposed_pairs_one_sided` climbing 7 → 18, which is `Q117`'s own
        # reading of a rule announcing its own failure.
        #
        # ⚠️ **It widens what is FOUND and not what is drawn in the codec.**
        # `centre_step`'s own guard — `steps < 8 * lanes`, the lane coordinate's
        # reach — refuses every pair this term adds, so `TEXCOORD_1` and
        # `roads.glb` are byte-identical and only `opposed_pairs_unpublishable`
        # moves. The pairs reach the geometry, which is not drawn in any lane
        # coordinate and does not have that limit.
        reach = _drawn_width_m(edge) + style.kerb_width_m
        # Hoisted: the search box is this ribbon's own bounds grown by `reach`,
        # and it does not move as the candidates are walked.
        low_x, low_z = here.low_x - reach, here.low_z - reach
        high_x, high_z = here.high_x + reach, here.high_z + reach
        best: _Vote | None = None
        for other, there in ribbons.items():
            if other == index or edges[other].level != edge.level:
                continue
            # ⚠️ **Spelled out rather than shared with `_Occluders.cover`, which
            # runs the same reject.** That one walks a bucketed handful and can
            # afford `(low > high).any()` on `(2,)` arrays; this walks every pair,
            # and the array form is the 361 ms `_Ribbon` records. The duplication
            # is the price of that, and it is a *bound*, not a reading.
            if there.low_x > high_x or there.high_x < low_x:
                continue
            if there.low_z > high_z or there.high_z < low_z:
                continue
            if here.ux * there.ux + here.uz * there.uz > limit:
                continue
            key = (min(index, other), max(index, other))
            if (gap := measured.get(key)) is None:
                gap = _pair_gap_m(here.plan, there.plan)
                measured[key] = gap
            if not 0.0 < gap < reach:
                continue
            if best is None or gap < best.gap_m:
                best = _Vote(other, gap)
        if best is not None:
            votes[index] = best

    def returned(index: int, other: int) -> bool:
        """Did `other` vote for `index` back?"""
        vote = votes.get(other)
        return vote is not None and vote.partner == index

    report.opposed_pairs_one_sided += sum(
        1 for index, vote in votes.items() if not returned(index, vote.partner)
    )
    return {index: vote for index, vote in votes.items() if returned(index, vote.partner)}


def _pair_gap_m(here: np.ndarray, there: np.ndarray) -> float:
    """The separation two opposed halves both agree on, in metres.

    ⚠️ **Measured symmetrically, and it has to be.** Each half of a pair publishes
    its own offset and the two are supposed to name the *same* line. A one-sided
    measure — this edge's stations against the partner's segments — lets them
    disagree, and they did: the region's pairs landed their two lines up to 3.9 m
    apart. The mean of both directions is equal by construction whichever half is
    asking, which is also what lets the caller memoise it on the unordered pair.
    """
    return 0.5 * (_centreline_gap_m(here, there) + _centreline_gap_m(there, here))


def _drawn_width_m(edge: _Edge) -> float:
    """This ribbon's representative drawn width, in metres.

    The median for `_u_metres`' reason: since `Q23` the half-width varies per
    station, so no single scalar is exact and the median is the representative
    one.
    """
    return 2.0 * float(np.median(edge.points[:, _WIDTH]))


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
    return _drawn_width_m(edge) / edge.lanes


def _centreline_gap_m(here: np.ndarray, there: np.ndarray) -> float:
    """How far one drawn ribbon runs from its opposed partner's, in plan.

    ⚠️ **Takes the plans the caller already holds rather than two `_Edge`s**:
    `_ribbon_plan` is fancy indexing and so allocates a fresh copy every call,
    and `_opposed_gaps` has every one of these arrays in hand. There is no
    `None` case left for the same reason — it only builds a plan for a ribbon
    with two stations or more, so an absent one never reaches here.

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
        if position not in own or edge.territory:
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
    return [(start, stop + 1) for start, stop in true_runs(keep)]


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
    edge_id: int,
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
    # The same two arrays, in the same order, so `DrawnSurface._strip_corners`
    # rebuilds the triangles just emitted and not a second opinion about them —
    # and only where `strip` drew, which below two stations it does not.
    if len(points) >= 2:
        report.ribbon_rails.append((edge_id, edge.level, (right, left)))

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


# 🔴 A KERB code, which is never a bare class: the codec holds "no lanes" and
# "no length" to mean a junction CAP and nothing else, and `verify_road_surface`
# refuses a kerb that says either. This kerb belongs to no edge, so it says the
# least a kerb can — one lane, one-way, no paint on it — and the markings
# shader excludes the class outright, so nothing reads the lane.
_AREA_KERB_CODE = float(
    MARKING_CLASS_KERB + MARKING_LANES * 1 + MARKING_DIRECTION * MARKING_DIRECTIONS[FORWARD]
)


def _draw_area_kerb(
    builder: _Builder,
    line: np.ndarray,
    style: RoadSurface,
    lane_width_m: float,
    *,
    lip: bool = True,
) -> float:
    """The riser and lip along one stretch of an area's kerb line; its length.

    `_draw_edge`'s LEFT kerb, strip for strip and in the same rail order — the
    line arrives walked with the road on its right, so outward is left of travel
    and `mitres` points there. The same two strips so the same winding, which
    `downward_facing` checks over the whole mesh.

    `lip=False` draws the riser alone: an island's ring, whose top is one slab
    (`surface_region.island_tops`) and would lie on the lip strip for strip.
    """
    line = dedupe(line)
    if len(line) < 2:
        return 0.0
    along = plan_lengths(line)
    plan = line[:, [0, 2]]
    out = boundary(line, mitres(line), style.kerb_width_m)
    foot, top = _lift(plan, line, 0.0), _lift(plan, line, style.kerb_height_m)
    lip_rail = _lift(out, line, style.kerb_height_m)
    marking = _Marking(_AREA_KERB_CODE, float(along[-1]))
    outside = style.kerb_width_m / lane_width_m
    strips = ((foot, top, (0.0, 0.0)), (top, lip_rail, (0.0, -outside)))
    for lower, upper, across in strips if lip else strips[:1]:
        builder.strip(
            lower,
            upper,
            colour=style.kerb_material.colour,
            along=along,
            across=across,
            marking=marking,
        )
    return float(along[-1])


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
        # ⚠️ **The plan columns only, not the whole row.** `points` carries the
        # half-width, the inserted flag and the two deck rims besides x/y/z, and
        # the rims are `inf` wherever no deck was measured — so a row-wise
        # difference is `inf - inf` and lands a NaN in a variable this function
        # only ever wanted two components of.
        near, far = (1, 0) if end.at_start else (-1, -2)
        plan = points[near, [0, 2]] - points[far, [0, 2]]
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


class _Section(NamedTuple):
    """An arm's cross-section beyond its splay: where the road runs straight."""

    centre: np.ndarray  # x/y/z
    axis: np.ndarray  # unit plan direction, away from the junction
    half_width_m: float


def _far_section(end: _End, edges: list[_Edge], span_m: float) -> _Section | None:
    """One arm's cross-section at its first published vertex, if that vertex
    is within `span_m` of the node; None for a straight two-vertex arm.

    Road Network v2 attaches both carriageways of a dual carriageway to one
    node at each crossing, so each centreline turns 15-50 degrees into the
    node over its last vertex — 88 of the region's 228 bending cluster arms,
    at p50 10 m. The ribbon follows the turn and so do its kerbs, which is what
    drew Hennessy Road at Fleming Road as a bow-tie: two straight roads that
    meet the junction on the skew. The cross-section at the first vertex, with
    the axis of the segment *beyond* it, is where the arm is the road again.

    ⚠️ **`span_m` is derived, never authored**: the caller passes the
    distance between the two nodes plus both half-widths, so a first vertex
    further out than the cluster is wide is not a splay and the arm has no far
    section. Published vertices only — `_add_kerb_stations` inserts stations
    that are not turns.
    """
    edge = edges[end.edge]
    points = edge.points[edge.points[:, _INSERTED] == 0.0]
    if len(points) < 3:
        return None
    if not end.at_start:
        points = points[::-1]
    first = points[1, [0, 2]] - points[0, [0, 2]]
    if float(np.hypot(*first)) > span_m:
        return None
    beyond = points[2, [0, 2]] - points[1, [0, 2]]
    length = float(np.hypot(*beyond))
    if length <= _MIN_SEGMENT_M:
        return None
    return _Section(points[1, :3].copy(), beyond / length, float(points[1, _WIDTH]))


def _through_corridors(
    groups: list[list[_End]], edges: list[_Edge], report: SurfaceReport
) -> list[np.ndarray]:
    """The straight corridors across a cluster, one convex quad each (`P3-31`).

    Two arms at different nodes whose far axes point at each other within
    `_THROUGH_TURN_DEG`, and whose far sections overlap laterally, are one
    street crossing the junction: the quad between their two sections is
    carriageway however the centrelines splayed to reach their nodes. A quad
    per pair, **unioned with the cluster cap and never hulled into it** — a
    hull of cap and corridor would sweep the pavement corner between the
    corridor's far end and the next arm's mouth, which is exactly what
    `hull` was chosen to avoid.

    The lateral test is the two half-widths: the far axes must run over each
    other's section, which is what makes a carriageway and its opposed twin
    both qualify (they overlap) and two parallel side streets 14 m apart not.
    Both sections must lie on the junction side of each other, or two arms
    leaving the cluster the same way would corridor across everything between.
    """
    arms = [(group, end) for group in groups for end in group if not edges[end.edge].is_stub]
    nodes = {
        id(group): np.mean(
            [edges[end.edge].points[0 if end.at_start else -1, [0, 2]] for end in group], axis=0
        )
        for group in groups
    }
    quads: list[np.ndarray] = []
    limit = np.cos(np.radians(_THROUGH_TURN_DEG))
    for index, (group_a, end_a) in enumerate(arms):
        for group_b, end_b in arms[index + 1 :]:
            if group_a is group_b:
                continue
            node_a, node_b = nodes[id(group_a)], nodes[id(group_b)]
            half_a = edges[end_a.edge].end_half_width_m(end_a.at_start)
            half_b = edges[end_b.edge].end_half_width_m(end_b.at_start)
            span = float(np.hypot(*(node_a - node_b))) + half_a + half_b
            first = _far_section(end_a, edges, span)
            second = _far_section(end_b, edges, span)
            if first is None or second is None:
                continue
            # Through: arriving along `first.axis` reversed, leaving along
            # `second.axis`; both sections on the junction side of the other.
            if float(-first.axis @ second.axis) < limit:
                continue
            between = second.centre[[0, 2]] - first.centre[[0, 2]]
            if float(between @ first.axis) > 0.0 or float(-between @ second.axis) > 0.0:
                continue
            reach = first.half_width_m + second.half_width_m
            across_a = abs(float(between[0] * first.axis[1] - between[1] * first.axis[0]))
            across_b = abs(float(between[0] * second.axis[1] - between[1] * second.axis[0]))
            if across_a > reach or across_b > reach:
                continue
            corners = []
            for section in (first, second):
                side = np.array([-section.axis[1], 0.0, section.axis[0]]) * section.half_width_m
                corners.append(section.centre + side)
                corners.append(section.centre - side)
            quad = hull(np.vstack(corners))
            if len(quad) >= 3:
                quads.append(quad)
    report.corridors += len(quads)
    return quads


def _out(plan: np.ndarray) -> np.ndarray:
    """A plan direction as an x/y/z step, flat, for handing to a 3D routine."""
    return np.array([plan[0], 0.0, plan[1]])


def _cap_ring(
    groups: list[list[_End]], edges: list[_Edge], report: SurfaceReport
) -> np.ndarray | None:
    """The junction polygon closing one node — or one cluster of nodes — at one level.

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

    🔴 **A cluster of groups is one cap (`P3-31`), and the stubs joining them
    contribute no corners.** A stub's mouths lie *inside* the junction — each
    is a clamped trim, short of where the cap needs to reach — and a hull
    over them is the per-node cap that left the median void. The hull is over
    the corners of every other arm in the cluster, and the stubs keep their
    trimmed ribbons under it: the same colour at the same height in the same
    material as the cap, so the coplanar pair cannot be told apart, and their
    kerbs are hidden by `_hide_buried_kerbs` like any kerb under a cap. Their
    lane lines cannot show through either: a stub keeps at most 30% of its
    length as ribbon, under 5 m on this region, and `road_markings.gdshader`
    fades every line within 6 m of a ribbon end.

    ⚠️ **Outside a cluster this is byte for byte the per-node cap**, by
    construction rather than by a branch: a stub's ends both lie in groups the
    stub joins, so a group no stub touches has no stub ends to skip. The
    fallback to every corner is for a cluster with fewer than three non-stub
    corners — two nodes joined by a stub and nothing else, which no source
    draws but a fixture might.
    """
    if sum(len(group) for group in groups) < 2:
        return None
    ends = [end for group in groups for end in group]
    corners = _corners([end for end in ends if not edges[end.edge].is_stub], edges)
    if len(corners) < 3:
        corners = _corners(ends, edges)
    if len(corners) < 3:
        return None
    through = [apex for group in groups for apex in _through_corners(group, edges)]
    report.through_movements += len(through)
    ring = hull(np.vstack(corners + through))
    return ring if len(ring) >= 3 else None


def _corners(ends: list[_End], edges: list[_Edge]) -> list[np.ndarray]:
    """The two carriageway corners each of these ends presents to its node."""
    return [
        corner
        for end in ends
        for on_left in (True, False)
        if (corner := edges[end.edge].corner(end.at_start, on_left=on_left)) is not None
    ]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: SurfaceReport) -> None:
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

    `opposed_pairs` is the fourth, and a marking stage's too (`Q125`): which two
    edges are the halves of one dual carriageway. It is this stage's alone
    because it falls out of the ribbons rather than the graph — the halves are
    separate edges sharing no node — and the centre line between two flows is
    the one marking neither half's own geometry locates.

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
            "mesh_name": SURFACE_MESH_NAME,
            "triangles": report.triangles,
            "vertices": report.vertices,
            # What the tile cut cost, and nothing else: every chunk vertex is a
            # built vertex or a station's duplicate on the other side of a cut.
            "cut_vertices": report.chunk_vertices - report.vertices,
            "bytes": report.bytes,
            "aabb": report.aabb,
            "chunks": report.chunks,
            "join": {
                "foreign_ends": report.foreign_ends,
                "caps_with_foreign_mouth": report.caps_with_foreign_mouth,
                "caps_in_neighbour": report.caps_in_neighbour,
            },
            # `P3-31`: the stubs and the clusters they join, so a reader can
            # tell how many of `caps` close more than one node. Counters only
            # and no ring is marked, because a consumer of `caps` is asking
            # where the drawn surface is and a cluster cap answers that the
            # same way a per-node one does.
            "clusters": {
                "stub_edges": report.stub_edges,
                "count": report.clusters,
                "nodes": report.cluster_nodes,
                "corridors": report.corridors,
            },
            # 🔴 **`Q125`: the two halves of each dual carriageway, and their
            # separation.** The join between two opposed flows is the one line
            # neither half's own geometry marks — `roadmarks.py` draws it where
            # TD surveyed no `RM1001` — and this pass is the only one that knows
            # the pairing. One row per pair, `[a, b, gap_m]` with `a < b`, over
            # published edge ids; `centre_step` in `TEXCOORD_1` is the same
            # finding said in the codec's terms, for a shader that draws it
            # per edge instead.
            "opposed_pairs": [
                [here, there, round(gap, 3)]
                for (here, there), gap in sorted(report.opposed_pairs.items())
            ],
            # `P3-32`: the boxes the surface yielded to, and what it grew.
            "paint": {
                "boxes_read": report.boxes_read,
                "stations": report.paint_stations,
                "flanks": report.paint_flanks,
                "flank_ends": report.paint_flank_ends,
                "flank_m2": round(report.paint_flank_m2, 2),
            },
            "carriageway": [
                {
                    "edge": edge_id,
                    "half_width_m": halves,
                    "offset_m": report.carriageway_offset[edge_id],
                    # Present on a territory edge only (`P3-33c`): the corridor a
                    # car can use, kerb to kerb, where the pair above is what
                    # this centreline draws of it.
                    # All three or none: `_prepare` and `_publish_territory_table`
                    # fill both tables for exactly the territory edges.
                    **(
                        {
                            "corridor_half_width_m": report.corridor[edge_id][0],
                            "corridor_offset_m": report.corridor[edge_id][1],
                            "lanes_painted": report.lanes_painted[edge_id],
                        }
                        if edge_id in report.corridor
                        else {}
                    ),
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
            # The level-0 carriageway outside every ribbon (`P3-33c`), as the
            # triangles drawn. Empty for a city that builds no region.
            "areas": [
                [round_position(tuple(corner)) for corner in triangle]
                for triangle in report.area_triangles
            ],
            # The drawn strips' rails, in `strip`'s order — see
            # `SurfaceReport.ribbon_rails`. Same rounding as the caps, so a
            # strip and the cap meeting it publish identical mouth corners.
            "ribbons": [
                {
                    "edge": edge_id,
                    "level": level,
                    "rails": [
                        [round_position(tuple(station)) for station in rail] for rail in rails
                    ],
                }
                for edge_id, level, rails in report.ribbon_rails
            ],
        },
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    report = build_region(city, args.region, sources_root=args.sources_root)
    log.info(
        "%d edges and %d junction caps: %d triangles, %d vertices, %.1f MB",
        report.edges,
        report.junctions,
        report.triangles,
        report.vertices,
        report.bytes / 1e6,
    )
    if (
        report.territory_edges
        or report.territory_mismatched_edges
        or report.territory_missing_edges
    ):
        log.info(
            "  region: %d level-0 ribbons take their territory as their rails, %d published "
            "stations with none keep the plain ribbon (a run past its rectangle, Q116); %d painted "
            "lane counts cut to what the share carries; %d area triangles outside every ribbon, "
            "%.0f m of kerb drawn along their edges, %d islands ringed and topped; %d edges whose "
            "territory does not index their polyline drawn plain (must be 0), %d with no "
            "territory at all drawn plain",
            report.territory_edges,
            report.territory_fallback_stations,
            report.territory_lanes_capped,
            len(report.area_triangles),
            report.area_kerb_m,
            report.islands,
            report.territory_mismatched_edges,
            report.territory_missing_edges,
        )
    log.info(
        "  join: %d foreign ends offered to the caps, %d caps took a foreign mouth, "
        "%d caps left to the neighbour containing their node",
        report.foreign_ends,
        report.caps_with_foreign_mouth,
        report.caps_in_neighbour,
    )
    log.info(
        "  %d ends trimmed back from a junction, %d of them clamped by edge length",
        report.trimmed_ends,
        report.clamped_trims,
    )
    log.info(
        "  junction clusters: %d stubs clamped at both ends join %d nodes into %d clusters, "
        "each capped once; %d straight corridors drawn across them",
        report.stub_edges,
        report.cluster_nodes,
        report.clusters,
        report.corridors,
    )
    log.info(
        "  paint witness: %d boxes read, %d stations inserted inside them, %d flanks drawn from a "
        "rail out to the paint (%d of them closing a run at the rail's exit), %.1f m2",
        report.boxes_read,
        report.paint_stations,
        report.paint_flanks,
        report.paint_flank_ends,
        report.paint_flank_m2,
    )
    # `Q107`. ⚠️ **The refusals are named in the same line as the cuts**, because
    # they are the same population split two ways — a station the deck could
    # reach and a station the deck could not answer for — and quoting the first
    # alone reads as a clean sweep.
    log.info(
        "  %d off-grade edges carry a deck rim: %d stations cut back to it, "
        "%d refused with the ribbon wholly off its deck and left as drawn (Q107)",
        report.deck_rim_edges,
        report.clamped_stations,
        report.clamp_refused_stations,
    )
    if report.deck_rim_off_structure:
        log.info(
            "  %d of those vertices are not on structure and keep the ribbon they had (Q113)",
            report.deck_rim_off_structure,
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
    # ⚠️ **All three in one line, because they are one population split three
    # ways** — paired, voted one-sided, paired and out of range — and quoting the
    # first alone reads as a clean sweep. `P3-12` published the first alone while
    # the pairing matched 12 of 621 one-way edges.
    log.info(
        "  %d edge ends are half of an opposed pair and carry a centre line: "
        "%d voted for a partner that did not vote back, %d paired and out of range",
        report.opposed_pair_ends - report.opposed_pairs_unpublishable,
        report.opposed_pairs_one_sided,
        report.opposed_pairs_unpublishable,
    )
    # Its own line rather than a fourth number above, because it is a different
    # population: pairs, not ends, and every mutual one rather than the ones the
    # codec can say (`Q125`).
    log.info("  %d opposed pairs published for the join", len(report.opposed_pairs))
    if report.on_structure_m:
        log.info(
            "  %.0f m of level-0 carriageway sits on structure and is drawn at its authored "
            "width — Q23",
            report.on_structure_m,
        )
    if report.structure_bounded_m:
        log.info(
            "  %.0f m of level-0 carriageway has structure standing beside it at bumper height "
            "and is drawn WIDE anyway — Q19 measured the narrowing and refused it; an "
            "overlapping population, not a subset of the line above",
            report.structure_bounded_m,
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
    if report.lanes_forward_unsaid:
        log.info(
            "  %d two-way edges publish a lanes_forward past the codec's two bits and are drawn "
            "at their old middle (Q126)",
            report.lanes_forward_unsaid,
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
