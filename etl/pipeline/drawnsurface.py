"""The drawn road surface, read back as something paint can stand on and be cut to.

`DrawnSurface` and the crease cutting under it, moved whole out of `surface.py`
(`P3-35f`, `Q133`): nothing in the stage that DRAWS the road reads them — every
consumer is a layer painted on it (`boxjunctions`, `roadmarks`) or a grader — so
they are the surface's reader and not part of its build. A moved name keeps its
name.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, NamedTuple

import numpy as np

from pipeline.geometry import clip_half_plane
from pipeline.meshbuild import MIN_TWICE_AREA_M2, thin_in_plan
from pipeline.surface import _MIN_SEGMENT_M
from pipeline.terrain import Prepared, covered_prepared, prepare

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
