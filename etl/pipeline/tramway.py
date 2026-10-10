"""The published tramway as drawn geometry (`P3-14`, `Q58`).

Reads iB1000 `CartoTransLine`'s tramway code, pairs the rails it publishes back
into tracks, and writes `tram.glb` — two rails and a bed per track, at the
position the estate prints them.

**Why this is a mesh and not a marking.** `ART_DESIGN.md` has wanted a tram
treatment since `P1-4`, `roads.tram_streets` has flagged 86 edges since then,
and `surface.py` has shipped that flag in `TEXCOORD_1` since `P3-12`. Drawing it
in the markings shader would have cost one decode line. `Q58` measured where the
rails actually are first, and they are not on the ribbon:

- **80 of the 86 flagged edges are one-way.** Hennessy, Johnston, Yee Wo and
  Causeway are drawn as opposed pairs, so the reserve runs *between* two ribbons
  rather than down the middle of either. That is why every offset came back on
  the same side of both halves — for two anti-parallel centrelines, something
  between them sits on the same relative side of each.
- **Only 18.8%** of 1,698 four-rail cross-sections have both tracks on the drawn
  carriageway: Hennessy **1.5%**, Yee Wo 0.0%, Causeway 0.0%, Johnston 54.4%.
- The outer rail sits a median **3.26 m** past the drawn kerb, p90 **4.68 m**.

A lane-space rail would therefore have been an *invented* marking in the sense
`Q54` records — the shape of thing that is a debit against `P3-9a` in a way a
missing one is not — and unlike `Q54`'s double yellow it could not even have
claimed the source was absent.

**What the layer actually contains, which the record had wrong.** `Q57` and
`DATA_SOURCES.md` both called these tramway *centrelines*. They are the rails:
56.5% of stations across a flagged edge cross exactly four parts, and the gap
between neighbouring parts is sharply unimodal at 1.05-1.20 m — the 1,067 mm
gauge. So this module's first job is a join, putting rails back into tracks, and
`gauge_m`/`pair_tolerance_m` in the city file are what it joins on.

**Heights come from the road, not the terrain.** A rail station takes the deck
height of the nearest level-0 centreline, which is the same snap `fares.py`
makes for a fare node and reuses its `Segments`. The terrain would be the
obvious source and is the wrong one twice over: the shipped ground is decimated
on a 4 m cell and collapsed to cluster means (`P3-10`), so it is not the surface
`roads.py` sampled; and the reserve is a made road surface, level with the
carriageways either side of it, not with the ground under them.

Nothing here knows a Hong Kong fact: the layer, the domain code, the gauge and
every drawn dimension arrive from `config/hong_kong.yaml` (hard rule 3).
"""

from __future__ import annotations

import argparse
import itertools
import logging
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.buildings import BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA
from pipeline.clearance import ground_colour, tile_meshes, wears
from pipeline.config import Config, Tramway, load_config
from pipeline.crs import GameTransform
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, read_render, write_glb
from pipeline.mesh import select_triangles
from pipeline.meshbuild import MIN_TWICE_AREA_M2
from pipeline.polyline import Segments, plan_lengths, plan_steps, true_runs
from pipeline.roads import ROADGRAPH_NAME, clip, read_graph, resample, resample_anchored
from pipeline.surface import (
    SURFACE_MANIFEST_NAME,
    SURFACE_MANIFEST_SCHEMA,
    boundary,
    dedupe,
    downward_facing,
    mitres,
    read_surface,
)

log = logging.getLogger(__name__)

TRAMWAY_NAME = "tram.glb"
TRAMWAY_MANIFEST_NAME = "tramway.json"
# 2 since `P3-71`: the manifest carries `track_lines`, every bed's centreline
# with its heights, so a stage that stands something ON a track — the parked
# tram at a stop — reads the join this module made rather than remaking it.
TRAMWAY_MANIFEST_SCHEMA = 2

# ⚠️ **No `-col` suffix, and that is deliberate.** The `-col` convention makes a
# mesh a collider, and the tramway must not be one: it lies on ground that is
# already solid (`P3-10`), and a 30 mm rail modelled as collision geometry is a
# kerb the player cannot see the point of. What the car drives on under the
# tramway is the terrain, unchanged.
TRAMWAY_MESH_NAME = "tramway"

# glTF material name, the same contract channel `SURFACE_MATERIAL` uses:
# `tools/generated_scene_import.gd` maps this string onto `tuning/tramway.tres`
# and nothing else, so a mesh that stops carrying it falls back to a
# `BaseMaterial3D` and renders as flat vertex colour.
TRAMWAY_MATERIAL = "tramway"

# `TEXCOORD_1.x` — which of the two things a vertex is part of.
#
# ⚠️ **A codec, not a label**, on the same terms as `surface.py`'s: it is
# mirrored in `assets/shaders/tramway.gdshader` and `tools/verify_tramway.gd`,
# and `docs/ARCHITECTURE.md` is the tiebreak. It is one field rather than the
# nine `roads.glb` carries because the tramway needs no coordinate
# reconstructed — every vertex is already at the position iB1000 publishes.
#
# It exists because the shader cannot tell the two apart from anything else it
# has. Deriving it from strip width would work today and would silently invert
# the day `rail_width_m` and `bed_width_m` moved towards each other, and
# deriving it from vertex colour would make the material table load-bearing for
# shading rather than for colour.
TRAMWAY_CLASS_BED = 0.0
TRAMWAY_CLASS_RAIL = 1.0

# ⚠️ **`TEXCOORD_1.y` carries the metres along, and `TEXCOORD_0.y` carries the
# same number for the shader's convenience only.** That looks like duplication
# and is the shape `roads.glb` already uses, for the reason `P3-12` found the
# hard way: Godot's importer compresses `TEXCOORD_0` and does not compress
# `TEXCOORD_1` — `MeshContract.check_uv2_import_settings` is what holds the
# second half of that. A contract read off `TEXCOORD_0` is read off a quantised
# channel: the first version of `verify_tramway.gd` did exactly that and found
# the tramway starting at **-0.009 m**, on a value this module writes as an
# exact float32 zero.

# Distance along a rail between the stations pairing is tested at, in metres.
# Only the *join* samples this finely; the drawn geometry keeps the source's own
# vertices, so this buys pairing evidence rather than triangles.
_PAIR_STEP_M = 2.0

# Share of a rail's tested stations that must agree on the same partner before
# the two are drawn as a track. A rail crossing a junction or a set of points
# picks up stray neighbours, and a simple nearest-hit vote would let one of them
# carry a whole track's bed off down a crossover.
_PAIR_AGREEMENT = 0.5

# Below this a part carries no usable direction and is dropped rather than
# drawn: a two-point rail whose points coincide has no normal to offset along.
_MIN_PART_M = 1.0

# How `_follow` reads the drawn surface under a strip: how often it asks, how
# far apart the stations it adds may be, and how far from its chord a span may
# stand and still be drawn as the chord. A kerb lip is `kerb_width_m` across —
# half a metre — so a probe every quarter cannot step over one, and the flat bar
# is a quarter of the smaller lift a strip stands on.
#
# ⚠️ **`_FLAT_M` is how far under the surface a drawn chord may sit**, so it
# has to stay below both lifts in the city file (0.02 and 0.01 today).
_PROBE_M = 0.25
_FOLLOW_STEP_M = 1.0
_FLAT_M = 0.005

# The collapse bar is shared: see `meshbuild.MIN_TWICE_AREA_M2`.


@dataclass
class TramwayReport:
    """What the stage read, joined and drew."""

    parts: int = 0
    parts_m: float = 0.0

    # ⚠️ **Two orthogonal partitions of `parts`, and reading them as one is
    # wrong.** Pairing decides whether a *bed* is drawn; snapping decides
    # whether the *rail* is. A rail can be unpaired and still drawn, and an
    # unsnapped rail is counted as unpaired too:
    #
    #   paired + unpaired                   == parts   (did it find its partner?)
    #   rails_drawn + unsnapped + too_short == parts   (was it drawn?)
    #
    # `trimmed` is a subset of `rails_drawn`: rails drawn for part of their
    # length, because some of their stations had no road within `max_snap_m`.
    #
    # Rails dropped are reported rather than raised, for the reason `fares.py`
    # gives about a point in a car park: one unusable part is the publisher's
    # business and should not cost the region its tramway.
    paired: int = 0
    unpaired: int = 0
    rails_drawn: int = 0
    rails_drawn_m: float = 0.0
    unsnapped: int = 0
    trimmed: int = 0
    too_short: int = 0

    # Joined pairs, and the bed runs they produced. ⚠️ **`tracks` is not bounded
    # by `pairs`**: a pair whose rails part and rejoin — a crossover is exactly
    # that — yields a run either side, and a sheet-split rail pairs twice
    # against the same long partner.
    pairs: int = 0
    tracks: int = 0
    tracks_m: float = 0.0
    # Every bed's centreline as drawn, `[x, y, z]` per station, in the order the
    # beds were laid — published for a consumer that stands on the track.
    track_lines: list[list[list[float]]] = field(default_factory=list)
    # Stations of a joined pair the trim rejected, and how many it tested. ⚠️
    # **This is what can see a bad join, and `gauges_m` cannot** — see
    # `_write_manifest`.
    off_gauge: int = 0
    pair_stations: int = 0
    gauges_m: list[float] = field(default_factory=list)
    # Triangles wound so they face the ground. Published because an inverted
    # tramway is *invisible* rather than wrong-looking — see `_draw`.
    inverted: int = 0
    inverted_area_m2: float = 0.0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)

    @staticmethod
    def measured(values: list[float]) -> dict[str, float]:
        """One distribution as the manifest publishes it."""
        if not values:
            return {}
        points = np.percentile(np.asarray(values), (10, 50, 90))
        return {
            "p10": round(float(points[0]), 4),
            "p50": round(float(points[1]), 4),
            "p90": round(float(points[2]), 4),
            "n": len(values),
        }


class _Rails:
    """Every published rail, indexed for the perpendicular the join casts.

    A grid rather than a tree: the query is always a short ray from a station on
    another rail, so the cells it touches are a handful and the cost is the
    concatenation rather than the search.
    """

    _CELL_M = 20.0

    def __init__(self, parts: list[np.ndarray]) -> None:
        starts, ends, owners = [], [], []
        for index, part in enumerate(parts):
            starts.append(part[:-1, [0, 2]])
            ends.append(part[1:, [0, 2]])
            owners.append(np.full(len(part) - 1, index))
        self.start = np.concatenate(starts) if starts else np.empty((0, 2))
        self.end = np.concatenate(ends) if ends else np.empty((0, 2))
        self.owner = np.concatenate(owners) if owners else np.empty(0, dtype=int)

        cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        low = np.floor_divide(np.minimum(self.start, self.end), self._CELL_M).astype(np.intp)
        high = np.floor_divide(np.maximum(self.start, self.end), self._CELL_M).astype(np.intp)
        for row in range(len(self.start)):
            for cx in range(low[row, 0], high[row, 0] + 1):
                for cy in range(low[row, 1], high[row, 1] + 1):
                    cells[(cx, cy)].append(row)
        self.cells = {cell: np.asarray(rows, dtype=np.intp) for cell, rows in cells.items()}

    def across(
        self, origin: np.ndarray, normal: np.ndarray, reach_m: float, exclude: int
    ) -> list[tuple[float, int]]:
        """Every other rail the perpendicular crosses, as `(distance, rail)`.

        Both directions out of one solve, which is the argument
        `carriageway_margin.py` makes for the same arithmetic: negating the
        normal negates the parameter along it and leaves the rest untouched, so
        the backward ray is the forward one read at negative `along`.

        ⚠️ **Unsigned on purpose.** Which side a neighbour sits on says nothing
        about whether it is the other rail of this track — a track's two rails
        straddle nothing, they simply sit a gauge apart — so the caller has no
        use for the sign and taking `abs` here stops it looking load-bearing.
        """
        near, far = origin - normal * reach_m, origin + normal * reach_m
        low = np.floor_divide(np.minimum(near, far), self._CELL_M).astype(np.intp)
        high = np.floor_divide(np.maximum(near, far), self._CELL_M).astype(np.intp)
        chunks = [
            rows
            for cx in range(low[0], high[0] + 1)
            for cy in range(low[1], high[1] + 1)
            if (rows := self.cells.get((cx, cy))) is not None
        ]
        if not chunks:
            return []
        rows = np.unique(np.concatenate(chunks))
        rows = rows[self.owner[rows] != exclude]
        if not len(rows):
            return []

        start = self.start[rows]
        edge = self.end[rows] - start
        offset = start - origin
        denominator = normal[1] * edge[:, 0] - normal[0] * edge[:, 1]
        solvable = np.abs(denominator) >= 1e-12
        safe = np.where(solvable, denominator, 1.0)
        along = (offset[:, 1] * edge[:, 0] - offset[:, 0] * edge[:, 1]) / safe
        across = (normal[0] * offset[:, 1] - normal[1] * offset[:, 0]) / safe
        hit = solvable & (across >= -1e-9) & (across <= 1.0 + 1e-9) & (np.abs(along) <= reach_m)
        owners = self.owner[rows][hit]
        distances = np.abs(along[hit])
        return [(float(t), int(owner)) for t, owner in zip(distances, owners, strict=True)]


class _Faces:
    """Shipped triangles, indexed for the height standing at a plan point.

    The tramway is laid on what the region *draws*, and the centreline cannot
    say what that is. A carriageway carries a kerb lip `kerb_height_m` above it
    and half a metre past its edge, and the ground between two carriageways is
    the decimated terrain, not the deck either was laid at: measured on the
    shipped bundles, 20.4% of Causeway Bay's rail area and 17.6% of Wan Chai's
    lay under the road mesh — every one of them a kerb, 0.12 m down, the lip
    less the rail's own lift — and another 8.2% of Causeway Bay's under the
    ground. So this reads the meshes themselves, as the graders do.

    Walls and risers are left out: a face steeper than 60 degrees is something
    a rail runs beside, and its height at a point is whichever end was asked.
    """

    _CELL_M = 8.0

    def __init__(self, corners: np.ndarray) -> None:
        normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        flat = np.abs(normal[:, 1]) > 0.5 * np.linalg.norm(normal, axis=1)
        self.corners = corners[flat]
        plan = self.corners[:, :, [0, 2]]
        low = np.floor_divide(plan.min(axis=1), self._CELL_M).astype(np.intp)
        high = np.floor_divide(plan.max(axis=1), self._CELL_M).astype(np.intp)
        cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        for row in range(len(self.corners)):
            for cx in range(low[row, 0], high[row, 0] + 1):
                for cz in range(low[row, 1], high[row, 1] + 1):
                    cells[(cx, cz)].append(row)
        self.cells = {cell: np.asarray(rows, dtype=np.intp) for cell, rows in cells.items()}

    def top(
        self, x: float, z: float, near_y: float, within_m: float, reach_m: float = 0.0
    ) -> float | None:
        """The highest face over `(x, z)` within `within_m` of `near_y`, or None.

        The window is what keeps a flyover's deck, and the road in the underpass
        below, from answering for the street.

        With `reach_m`, over the point or any of four more that far from it: a
        strip has a width, and a rail whose spine runs just clear of a kerb's
        edge has half of itself under the lip.
        """
        at = np.array([[x, z]])
        if reach_m > 0.0:
            at = at + np.array(
                [(0.0, 0.0), (reach_m, 0.0), (-reach_m, 0.0), (0.0, reach_m), (0.0, -reach_m)]
            )
        # One solve for every point: a call is numpy's overhead, not its rows.
        cells = {(int(px // self._CELL_M), int(pz // self._CELL_M)) for px, pz in at}
        found = [rows for cell in cells if (rows := self.cells.get(cell)) is not None]
        if not found:
            return None
        rows = found[0] if len(found) == 1 else np.unique(np.concatenate(found))
        a, b, c = (self.corners[rows, corner, None] for corner in range(3))
        ab_x, ab_z = b[..., 0] - a[..., 0], b[..., 2] - a[..., 2]
        ac_x, ac_z = c[..., 0] - a[..., 0], c[..., 2] - a[..., 2]
        twice_area = ab_x * ac_z - ab_z * ac_x
        solvable = np.abs(twice_area) > 1e-12
        safe = np.where(solvable, twice_area, 1.0)
        dx, dz = at[:, 0] - a[..., 0], at[:, 1] - a[..., 2]
        beta = (dx * ac_z - dz * ac_x) / safe
        gamma = (dz * ab_x - dx * ab_z) / safe
        height = a[..., 1] + beta * (b[..., 1] - a[..., 1]) + gamma * (c[..., 1] - a[..., 1])
        over = (
            solvable
            & (beta >= 0.0)
            & (gamma >= 0.0)
            & (beta + gamma <= 1.0)
            & (np.abs(height - near_y) <= within_m)
        )
        return float(height[over].max()) if over.any() else None


class _Builder:
    """Accumulates flat quad strips into one vertex-coloured mesh.

    Deliberately simpler than `surface.py`'s: its codec has nine fields and this
    one has a single class stripe, and every strip here is horizontal, so the
    normal is up rather than derived per quad.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
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
        along_m: np.ndarray,
        surface_class: float,
    ) -> None:
        """A quad strip between two boundaries, facing up.

        `UV.x` is 0 on `left` and 1 on `right` — a fraction across rather than
        the lane coordinate the carriageway uses, because a rail has no lanes
        and the shader's question is only how far across this piece of metal it
        is. `UV.y` is metres along, matching the road surface so the two can be
        judged at the same pitch.
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
        self._positions.append(np.vstack([left, right]))
        self._colours.append(
            np.tile(np.array([*colour, 255], dtype=np.uint8), (2 * span, 1)),
        )
        self._uvs.append(
            np.column_stack(
                [np.repeat((0.0, 1.0), span), np.concatenate([along_m, along_m])]
            ).astype(np.float32)
        )
        self._uv2.append(
            np.column_stack(
                [np.full(2 * span, surface_class), np.concatenate([along_m, along_m])]
            ).astype(np.float32)
        )
        self._count += 2 * span

    def corners(self) -> np.ndarray:
        """Every triangle so far as `(n, 3, 3)`, before `build` drops any."""
        if not self._triangles:
            return np.zeros((0, 3, 3))
        return np.vstack(self._positions)[np.vstack(self._triangles)]

    def build(self, name: str) -> MeshData | None:
        """The accumulated geometry, minus collapsed triangles, or None.

        ⚠️ **The drop is not optional here, for the reason `boundary` gives.**
        `_draw` offsets through the same `surface.boundary`, which holds the
        inner rail still around a corner tighter than the strip is wide — and a
        held boundary leaves a quad with two corners in the same place. A tram
        reserve turning into a depot has exactly those corners. `surface.py`
        filters them and this did not, so degenerate triangles shipped.
        """
        if not self._triangles:
            return None
        count = self._count
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.tile(np.array([0.0, 1.0, 0.0], dtype=np.float32), (count, 1)),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            colours=np.vstack(self._colours),
            uvs=np.vstack(self._uvs),
            uv2=np.vstack(self._uv2),
            material=TRAMWAY_MATERIAL,
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        return select_triangles(mesh, twice_area > MIN_TWICE_AREA_M2)


def read_rails(
    city: Config,
    spec: Tramway,
    region_id: str,
    transform: GameTransform,
    *,
    sources_root: Path | None,
) -> list[np.ndarray]:
    """Every published rail in the region, as an `(n, 3)` polyline in game space.

    Y is zero here and is filled in by `_snap_heights`: the source carries a
    measured Z, but it is the *rail's* survey height rather than the deck this
    city drew, and mixing the two puts a tramway through the road it runs on.

    ⚠️ **Cut at the region's own rectangle, not at `Config.clip_extent`.** The
    spatial filter returns a rail whole if any of it touches the region, and a
    rail has no ownership rule to hand its far half to a neighbour the way a
    road does — so each region draws the rail as far as its own edge, and two
    resident neighbours meet at the line rather than drawing the stretch twice.
    Uncut, the far end also sat past this region's last road, and that alone
    cost Causeway Bay its main line: 14 rails in the two regions were refused
    whole for stations that were all outside the rectangle.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    wanted = set(spec.codes)
    parts: list[np.ndarray] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("line_type"))
        owners, geometries = gdb.polylines(layer)
        for owner, points in zip(owners, geometries, strict=True):
            if str(codes[owner]) not in wanted:
                continue
            projected = np.asarray(points, dtype=np.float64)
            game_x, _, game_z = transform.to_game(projected[:, 0], projected[:, 1])
            plan = np.column_stack([game_x, game_z])
            for run in clip(plan, city.region_high(region_id), min_length_m=0.0):
                parts.append(dedupe(np.column_stack([run[:, 0], np.zeros(len(run)), run[:, 1]])))
    return parts


def _plan_length(points: np.ndarray) -> float:
    return float(plan_steps(points).sum())


def _pair_rails(
    parts: list[np.ndarray], spec: Tramway, report: TramwayReport
) -> list[tuple[int, int]]:
    """Which rails are the two sides of one track.

    A vote rather than a nearest-hit, because a rail does not stop being a rail
    at a crossover: at points and junction diamonds a station picks up the
    *other* track's near rail at very nearly the same distance, and one stray
    winner would carry a whole track's bed off down the branch. Requiring most
    of a rail's stations to name the same partner makes the join describe the
    rail rather than its worst station.

    Pairs are emitted once, keyed low-index-first, so a mutual vote does not
    draw the track twice into the same place.
    """
    index = _Rails(parts)
    # The upper bound is the ray's own reach, so `across` has already applied it
    # and only the lower one is left to test.
    reach_m = spec.gauge_m + spec.pair_tolerance_m
    low = spec.gauge_m - spec.pair_tolerance_m

    votes: dict[int, int] = {}
    for rail, part in enumerate(parts):
        plan = part[:, [0, 2]]
        # ⚠️ **Stations are spaced along the whole rail, not within each source
        # segment.** Restarting the walk at every vertex was the first version
        # and it silently weights the vote by how finely a stretch was
        # digitised: every segment contributes at least one station however
        # short, so a junction diamond drowns out the plain track either side of
        # it — and those are exactly the stations the vote exists to outvote.
        along = plan_lengths(part)
        ballot: Counter[int] = Counter()
        tested = 0
        for segment in range(len(plan) - 1):
            step = plan[segment + 1] - plan[segment]
            length = float(np.hypot(*step))
            if length < 1e-9:
                continue
            unit = step / length
            normal = np.array([unit[1], -unit[0]])
            first = math.ceil(along[segment] / _PAIR_STEP_M) * _PAIR_STEP_M
            for station in np.arange(first, along[segment + 1], _PAIR_STEP_M):
                origin = plan[segment] + unit * (station - along[segment])
                tested += 1
                candidates = [
                    (offset, partner)
                    for offset, partner in index.across(origin, normal, reach_m, rail)
                    if offset >= low
                ]
                if candidates:
                    ballot[min(candidates)[1]] += 1

        if not ballot:
            continue
        partner, agreed = ballot.most_common(1)[0]
        if agreed >= _PAIR_AGREEMENT * tested:
            votes[rail] = partner

    # Directed, and the direction is load-bearing: the track is drawn on the
    # *voter's* stations, because the voter is the rail that was measured to lie
    # alongside the other for most of its length.
    #
    # ⚠️ **Requiring the vote to be mutual loses a fifth of the tramway, and the
    # reason is the six map sheets.** iB1000 is published per sheet, so a rail
    # crossing a boundary arrives as two parts while the rail beside it may
    # arrive as one. The long one's stations then split their ballot between the
    # two halves, clear neither threshold, and all three go undrawn — 38 of 132
    # parts on the first run of this region. Taking the one-way vote as well
    # draws each half against its own stretch of the long rail, and the halves
    # do not overlap, so the two beds tile rather than z-fight.
    pairs: list[tuple[int, int]] = []
    for rail, partner in votes.items():
        # A mutual pair is one track, not two. Emitted from the lower index so
        # the choice does not depend on dictionary order.
        if votes.get(partner) == rail and rail > partner:
            continue
        pairs.append((rail, partner))
    report.paired = len({rail for pair in pairs for rail in pair})
    report.unpaired = len(parts) - report.paired
    return pairs


def _project(points: np.ndarray, onto: np.ndarray) -> np.ndarray | None:
    """For each of `points`, the nearest point in plan on the `onto` polyline.

    The two rails of a track are digitised independently and need not carry the
    same station count — 28 against 26 on the first pair this region draws — so
    anything that zips them vertex-for-vertex shears across the four-foot. This
    is what both the centreline and the gauge measurement are built on, shared
    rather than written twice: they are the same projection asked for a
    midpoint and for a distance.
    """
    plan = onto[:, [0, 2]]
    step = np.diff(plan, axis=0)
    length = np.hypot(*step.T)
    usable = length > 1e-9
    if not usable.any():
        return None

    # Hoisted: all three depend only on `onto`, and the loop below is per point.
    starts = plan[:-1]
    squared = np.where(usable, length**2, 1.0)
    closest = np.empty((len(points), 2))
    for row, point in enumerate(points[:, [0, 2]]):
        offset = point - starts
        t = np.clip((offset * step).sum(axis=1) / squared, 0.0, 1.0)
        feet = starts + step * t[:, None]
        distance = np.where(usable, np.hypot(*(point - feet).T), np.inf)
        closest[row] = feet[int(np.argmin(distance))]
    return closest


def _track_centres(
    left: np.ndarray, right: np.ndarray, spec: Tramway
) -> tuple[list[tuple[np.ndarray, np.ndarray]], int, int]:
    """The centreline between two rails, trimmed to where they run together.

    ⚠️ **A pair is only a track for as long as both rails are there**, and the
    untrimmed version is wrong in a way that looks plausible. `_project` clamps
    to the partner's nearest end, so a voter running on past its partner keeps
    generating a "centre" — one that walks steadily out towards the voter as the
    partner falls away behind it. The bed then flares out of the four-foot at
    every sheet boundary and every place a rail is published in two pieces.

    It was caught rather than reasoned about, by measuring the drawn gauge
    against the published 1.067 m: p90 **1.92 m** untrimmed, **1.21 m** trimmed.

    Returned as a list because a run can leave tolerance and come back — a
    crossover is exactly that — and bridging the gap would draw a bed across the
    junction it is not part of. Each entry carries the **drawn gauge per
    station** beside its centreline, from the half-offset computed here rather
    than measured again after the fact. Also returned: how many of the pair's
    stations the trim rejected, and how many there were.

    ⚠️ **That rejection count is the join's detector; the gauge is not** — see
    `_write_manifest`, which says why.
    """
    if len(left) < 2 or len(right) < 2:
        return [], 0, 0
    opposite = _project(left, right)
    if opposite is None:
        return [], 0, 0

    half = np.hypot(left[:, 0] - opposite[:, 0], left[:, 2] - opposite[:, 1]) * 0.5
    centres = np.column_stack(
        [
            (left[:, 0] + opposite[:, 0]) * 0.5,
            left[:, 1],
            (left[:, 2] + opposite[:, 1]) * 0.5,
        ]
    )
    together = np.abs(2.0 * half - spec.gauge_m) <= spec.pair_tolerance_m

    runs: list[tuple[np.ndarray, np.ndarray]] = []
    start: int | None = None
    for row, inside in enumerate([*together, False]):
        if inside and start is None:
            start = row
        elif not inside and start is not None:
            if row - start >= 2:
                runs.append((centres[start:row], 2.0 * half[start:row]))
            start = None
    return runs, int(np.count_nonzero(~together)), len(together)


def _stations(points: np.ndarray, step_m: float) -> np.ndarray:
    """`points` with stations added until no two are more than `step_m` apart.

    A strip is flat between its stations, and the source digitises a straight
    rail as two vertices however long it is — 153 m at the longest here. Heights
    taken only at those put the chord between them under any road that rises on
    the way: 14.4% of Wan Chai's drawn rail sat more than its whole lift below
    the road beside it, and read as a rail that sinks and resurfaces.

    Y comes back zero, as `read_rails` leaves it: `_snap_heights` fills it in.
    """
    plan = resample(points[:, [0, 2]], step_m)
    return np.column_stack([plan[:, 0], np.zeros(len(plan)), plan[:, 1]])


def _shipped_faces(city: Config, region_id: str, out_dir: Path) -> _Faces:
    """The region's drawn road and its ground, as the bundle ships them."""
    rebuild = f"python -m pipeline --region {region_id}"
    surface = read_document(out_dir / SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, rebuild)
    buildings = read_document(out_dir / BUILDINGS_MANIFEST_NAME, BUILDINGS_MANIFEST_SCHEMA, rebuild)
    road = read_surface(out_dir, surface["chunks"])
    blocks = [road.positions[road.triangles].astype(np.float64)]
    colour, jitter = ground_colour(city)
    for path in tile_meshes(out_dir, buildings):
        for mesh in read_render(path):
            if mesh.colours is None or not len(mesh.triangles):
                continue
            ground = wears(mesh.colours, colour, jitter)
            faces = mesh.triangles[ground[mesh.triangles].all(axis=1)]
            blocks.append(mesh.positions[faces].astype(np.float64))
    return _Faces(np.concatenate(blocks))


def _follow(
    points: np.ndarray, segments: Segments, under: Callable[[float, float, float], float]
) -> np.ndarray:
    """`points` with stations added wherever what lies under them is not a
    plane, each at the height that keeps the strip clear of it.

    What lies under a rail *steps* — a kerb is 0.15 m in no distance at all —
    and a strip is flat between stations, so a station either side of a step
    draws the rail through the kerb's corner: with every station itself standing
    clear, 5.8% of Causeway Bay's rail area was still under the road mesh.

    So the surface is asked every `_PROBE_M`, and each `_FOLLOW_STEP_M` span has
    both ends raised by the most any probe on it stands above the chord, which
    lifts the whole chord clear. On a plain gradient that is nothing. The short
    span is what keeps the lift local: raising a whole `height_step_m` span for
    one kerb floated a fifth of the rail more than 0.10 m over the road.

    A span the short stations leave within `_FLAT_M` of its own chord keeps only
    its ends, so the mesh grows where the ground moves and nowhere else.
    """
    plan, anchors = resample_anchored(points[:, [0, 2]], _FOLLOW_STEP_M)
    probes, stations = resample_anchored(plan, _PROBE_M)
    # The road is asked at every station and read off between them. Reading it
    # off between `height_step_m` stations instead put the window a metre out
    # wherever the nearest road changes, and 3.9% of Causeway Bay's rail went
    # under the ground it was meant to be following.
    road_y = [segments.nearest(float(x), float(z)).y for x, z in plan]
    near_y = np.interp(np.arange(len(probes)), stations, road_y)
    rests = np.array(
        [under(float(x), float(z), float(y)) for (x, z), y in zip(probes, near_y, strict=True)]
    )

    height = rests[stations]
    raised = np.zeros(len(plan))
    for span in range(len(plan) - 1):
        low, high = stations[span], stations[span + 1]
        chord = np.linspace(height[span], height[span + 1], high - low + 1)
        proud = float((rests[low : high + 1] - chord).max())
        raised[span : span + 2] = np.maximum(raised[span : span + 2], proud)
    height = height + raised

    keep = np.zeros(len(plan), dtype=bool)
    keep[anchors] = True
    for low, high in itertools.pairwise(anchors):
        chord = np.linspace(height[low], height[high], high - low + 1)
        if np.abs(height[low : high + 1] - chord).max() > _FLAT_M:
            keep[low : high + 1] = True
    return np.column_stack([plan[keep, 0], height[keep], plan[keep, 1]])


def _snap_heights(
    points: np.ndarray,
    segments: Segments,
    max_snap_m: float,
    lift_m: float,
    under: Callable[[float, float, float], float] | None = None,
) -> list[np.ndarray]:
    """The runs of `points` with a road beside them, put on what lies there.

    `under(x, z, road_y)` is the height a point rests on, given the deck height
    of the road beside it. Without one a station rests on that deck; with one
    the run follows it, and comes back with more stations than it went in with
    (`_follow`).

    A station further than `max_snap_m` from every level-0 road is left out, and
    the rail is drawn either side of it — never across it, because a tramway
    that takes its height from a road at one end and guesses at the other is
    drawn on a slope the city does not have. Dropping the whole rail for one
    such station was the first version, and it is why a siding leaving the
    street took the street's own track with it.
    """
    road_y = np.empty(len(points))
    near = np.empty(len(points), dtype=bool)
    for row in range(len(points)):
        snap = segments.nearest(float(points[row, 0]), float(points[row, 2]))
        near[row] = snap.distance_m <= max_snap_m
        road_y[row] = snap.y

    runs = []
    for start, stop in true_runs(near):
        if stop - start < 2:
            continue
        if under is None:
            run = points[start:stop].copy()
            run[:, 1] = road_y[start:stop]
        else:
            run = _follow(points[start:stop], segments, under)
        run[:, 1] += lift_m
        runs.append(run)
    return runs


def _same_ends(run: np.ndarray, stations: np.ndarray) -> bool:
    """Whether a drawn run starts and ends where its rail's stations do."""
    return bool(
        np.array_equal(run[0, [0, 2]], stations[0, [0, 2]])
        and np.array_equal(run[-1, [0, 2]], stations[-1, [0, 2]])
    )


def _draw(
    builder: _Builder,
    spine: np.ndarray,
    width_m: float,
    colour: tuple[int, int, int],
    surface_class: float,
) -> None:
    """One flat strip of the given width, centred on `spine`."""
    if len(spine) < 2:
        return
    offsets = mitres(spine)
    half = width_m * 0.5
    # ⚠️ **The signs are this way round because the winding decides visibility,
    # and the normal attribute does not.** `mitres` offsets to the left of
    # travel, so `+half` is the left rail; feeding the strip left-then-right
    # winds every triangle to face **down**, and `cull_back` in
    # `tramway.gdshader` then draws none of it. The first build of this module
    # did exactly that: 5,111 of 5,112 triangles inverted, a correct tramway in
    # the correct place, invisible from above and perfectly visible from below.
    # Nothing in the frame says so — the city just has no tramway in it.
    #
    # Held by `TramwayReport.inverted`, which the manifest publishes and
    # `test_tramway.py` pins, because the render is the only other thing that
    # would notice and it notices by showing nothing.
    left = boundary(spine, offsets, -half)
    right = boundary(spine, offsets, half)
    along = plan_lengths(spine)
    builder.strip(
        np.column_stack([left[:, 0], spine[:, 1], left[:, 1]]),
        np.column_stack([right[:, 0], spine[:, 1], right[:, 1]]),
        colour=colour,
        along_m=along,
        surface_class=surface_class,
    )


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> TramwayReport:
    """Read the region's published tramway and write its `tram.glb`."""
    spec = city.tramway
    report = TramwayReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error. A city whose estate publishes no tramway ships none, and
        # the manifest names no asset — the honest answer, and the same shape
        # `podiums` and `landmarks` already take.
        log.info("city '%s' declares no tramway block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    parts = read_rails(city, spec, region_id, transform, sources_root=sources_root)
    report.parts = len(parts)
    report.parts_m = sum(_plan_length(part) for part in parts)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, and for the same reason `kerbside.py` restricts its join: a
    # tramway is an at-grade thing, and the nearest edge of *any* level to a
    # rail under a flyover is the flyover.
    #
    # The neighbour's runs are candidates too. Inside this region's rectangle
    # the road beside a rail can be one the neighbour owns (`Q116`), and it is
    # still the deck the rail lies on.
    segments = Segments.of(
        [
            edge
            for edge in (*graph["edges"], *graph.get("foreign_edges", []))
            if int(edge["elevation_level"]) == 0
        ]
    )

    shipped = _shipped_faces(city, region_id, out_dir)
    within_m = spec.surface_within_m

    def drawn_under(x: float, z: float, road_y: float) -> float:
        top = shipped.top(x, z, road_y, within_m)
        return road_y if top is None else top

    builder = _Builder()

    # Which rails have a road beside them at all. Asked before anything is
    # drawn, because a bed needs both its rails and the rails are drawn last.
    stations: list[np.ndarray | None] = []
    for part in parts:
        if _plan_length(part) < _MIN_PART_M:
            report.too_short += 1
            stations.append(None)
            continue
        densified = _stations(part, spec.height_step_m)
        if not _snap_heights(densified, segments, spec.max_snap_m, 0.0):
            report.unsnapped += 1
            stations.append(None)
            continue
        stations.append(densified)

    # The bed, on the voter's own stations and only where the two rails are
    # actually running together. One pair can yield several runs, so `tracks`
    # counts drawn beds rather than joined pairs.
    for voter, partner in _pair_rails(parts, spec, report):
        report.pairs += 1
        if stations[voter] is None or stations[partner] is None:
            continue
        runs, rejected, tested = _track_centres(parts[voter], parts[partner], spec)
        report.off_gauge += rejected
        report.pair_stations += tested
        for spine, gauges in runs:
            if _plan_length(spine) < _MIN_PART_M:
                continue
            beds = _snap_heights(
                _stations(spine, spec.height_step_m),
                segments,
                spec.max_snap_m,
                spec.bed_lift_m,
                drawn_under,
            )
            # Per spine with any bed drawn, not per drawn station: the gauge is
            # the join's, measured before the heights could trim anything.
            if beds:
                report.gauges_m.extend(float(gauge) for gauge in gauges)
            for bed in beds:
                report.tracks += 1
                report.tracks_m += _plan_length(bed)
                report.track_lines.append(
                    [[round(float(v), 3) for v in station] for station in bed]
                )
                _draw(builder, bed, spec.bed_width_m, spec.bed_material.colour, TRAMWAY_CLASS_BED)

    # ⚠️ **Every rail is drawn once, from the source's own parts, and pairing
    # has nothing to do with it.** Drawing the rails inside the pairing loop
    # instead was the first version and it drew a sheet-split rail's long
    # partner once per half — two coplanar strips in the same place, which is
    # z-fighting down the length of the busiest street in the region. Nothing in
    # the frame would have said so; what said so was `drawn_gauge_m`, whose p90
    # read **4.62 m** against a 1.067 m gauge.
    #
    # It is also the more honest split. The source publishes a rail; that it
    # could not be matched to its opposite number is this module's difficulty,
    # not a reason to leave a rail the estate prints out of the city.
    #
    # After the beds, because a rail stands on its bed: a bed is one flat strip
    # at its spine's height, so where the ground falls away across the track
    # the bed is what lies under the rail, not the ground.
    laid = _Faces(builder.corners())

    def rail_under(x: float, z: float, road_y: float) -> float:
        top = shipped.top(x, z, road_y, within_m, spec.rail_width_m * 0.5)
        on_ground = (road_y if top is None else top) + spec.bed_lift_m
        on_bed = laid.top(x, z, road_y, within_m)
        return on_ground if on_bed is None else max(on_ground, on_bed)

    for densified in stations:
        if densified is None:
            continue
        heads = _snap_heights(densified, segments, spec.max_snap_m, spec.rail_lift_m, rail_under)
        report.rails_drawn += 1
        if len(heads) > 1 or not _same_ends(heads[0], densified):
            report.trimmed += 1
        for head in heads:
            report.rails_drawn_m += _plan_length(head)
            _draw(
                builder,
                head,
                spec.rail_width_m,
                spec.rail_material.colour,
                TRAMWAY_CLASS_RAIL,
            )

    mesh = builder.build(TRAMWAY_MESH_NAME)
    if mesh is not None:
        report.inverted, report.inverted_area_m2 = downward_facing(mesh)
        report.triangles = mesh.triangle_count
        report.vertices = len(mesh.positions)
        report.aabb = mesh.aabb()
        report.bytes = write_glb(out_dir / TRAMWAY_NAME, [mesh])
    _write_manifest(out_dir, city, region_id, report)
    return report


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: TramwayReport) -> int:
    document = {
        "schema_version": TRAMWAY_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # ⚠️ **Gated on what was *written*, not on what was joined.** A region
        # whose rails all failed to pair still writes `tram.glb` — rails are
        # drawn without a bed — and naming `null` here would leave a file on
        # disk that `shipped()` omits. Being wrong about the contents of the
        # bundle is what `CITY_SCHEMA` 11 was bumped for.
        "asset": TRAMWAY_NAME if report.rails_drawn else None,
        "rails": report.parts,
        "rails_m": round(report.parts_m, 3),
        "rails_paired": report.paired,
        "rails_unpaired": report.unpaired,
        "rails_drawn": report.rails_drawn,
        "rails_drawn_m": round(report.rails_drawn_m, 3),
        "pairs": report.pairs,
        "tracks": report.tracks,
        "tracks_m": round(report.tracks_m, 3),
        "track_lines": report.track_lines,
        # ⚠️ **This is the join's own detector, and `drawn_gauge_m` below is
        # not.** A pair joined across two *tracks* sits 2.6 m apart, which the
        # trim rejects at every station — so it shows up here as a pair whose
        # stations were all thrown away, and as `pairs` exceeding `tracks`. It
        # does not show up as a wide gauge, because a rejected station never
        # reaches the gauge.
        "off_gauge_stations": report.off_gauge,
        "pair_stations": report.pair_stations,
        "rails_unsnapped": report.unsnapped,
        "rails_trimmed": report.trimmed,
        "rails_too_short": report.too_short,
        # What the bed was actually built at, per station.
        #
        # ⚠️ **Bounded by `pair_tolerance_m` by construction, so it cannot see a
        # bad join.** `_track_centres` filters stations to within the tolerance
        # of `gauge_m` and these are the survivors, so every percentile is
        # confined to `[gauge - tol, gauge + tol]` whatever the source does.
        # What it *does* check is that the trim ran and that nothing moved the
        # geometry afterwards — the p90 **1.92 m** that caught the flared bed was
        # measured before the trim existed, and would read in range today.
        # `off_gauge_stations` above is what replaced it as the detector.
        "drawn_gauge_m": report.measured(report.gauges_m),
        "inverted": report.inverted,
        "inverted_area_m2": round(report.inverted_area_m2, 3),
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
    }
    return write_document(out_dir / TRAMWAY_MANIFEST_NAME, document)


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
        "tramway: %d rails (%.0f m) -> %d tracks (%.0f m), %d unpaired, %d triangles",
        report.parts,
        report.parts_m,
        report.tracks,
        report.tracks_m,
        report.unpaired,
        report.triangles,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
