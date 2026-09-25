"""Cut road structure back to the surveyed carriageway (`P3-28`, `Q19`).

`P3-9a′` put the build in front of three Hong Kong drivers and all three stopped
because the bridges are blocked: solid `INFRASTRUCTURE` massing stands in the
published carriageway on the Wan Chai Interchange ramps, and a car meets it as an
invisible wall. `Q19` priced the fix at **143.2 m** over the seven edges a
publisher surveyed a width for, and called it — a *sourced procedural* carve, the
flank cut back to the span a publisher drew, never by-eye authoring.

🔴 **The prism is the surveyed `width_m` and never the drawn floor.** Cutting at
the 10.24/12.48 m widening floor would remove published structure on the
authority of an invented width, which is `Q54` inverted. The seven edges carry
3.84-7.20 m; the floor is wider than every one of them.

🔴 **The cut face is CONSTRUCTED, not derived, and that is a measurement rather
than a preference.** The obvious implementation caps the cut from its own
boundary loops — an edge walked by one triangle after slicing is an edge the
removal opened. That presumes a watertight source, and the estate is not one:
**5.38%** of edge slots are open across the 74 source `INFRASTRUCTURE` meshes
(one sheet reaches 26.2%), and 14-26% in the decimated tiles. Derived capping was
built and returned **zero** closed loops on `e233`. So the cut face here is a
retaining wall built per station, its height measured from the structure actually
removed at that station — `PLAN.md`'s "the cap *is* the retaining wall", read
literally. ⚠️ **It publishes a face no publisher drew**, which is the honest debit
on this stage; what keeps it sourced is that its *height* and *extent* come from
removed geometry rather than from a number anyone chose.

⚠️ **Runs after `roads`, which is what makes it a re-emit rather than a build.**
The surveyed width is `roads`' output and `buildings` runs before it, so the
tiles already exist. Carving inside `buildings` would need the width a stage
later, and reordering buys nothing: the sources are no more watertight than the
tiles.

⚠️ **The class survives into a written tile only as `TEXCOORD_0.y`.** A tile is
one merged primitive, so `INFRASTRUCTURE` and `BUILDING` arrive at the shader
through one material with nothing else to tell them apart. `SurfaceClass.STRUCTURE`
is that something, and this stage cuts on it — nothing else here may.

**The parapet band is a SECOND population in the same pass** (`P3-51`, `Q147`):
a carved ramp's edge is jumpable, on the user's call. Where the carriageway
carve removes what stands IN a surveyed width on a listed edge, the band removes
what stands ABOVE the deck beside that same ribbon — the parapet — on the listed
edges, and by rule on any level or run of on-structure stations the config names
(none as shipped: a band over every flyover edge was built, measured and
withdrawn the same day, `Q147`). 🔴 **It keeps
the deck and removes the wall by the triangle's normal** (`_band_split`), and
**takes a wall whole by its centroid, with no prism at all** (`_band_candidates`):
a prism floored at the ribbon's own height would take the deck top beside the
ribbon along with the parapet, and a car leaving the road would fall THROUGH the
deck rather than off it, and a prism's side and end planes slice every wall they
straddle into slivers the tiles then ship. `deck_top_kept` on the row is the
counter a mutation there moves. The band draws no wall — a parapet is a sheet,
and what it leaves is the deck's own edge. ⚠️ **One pass for both populations**:
the retaining walls stand on the carriageway prisms' side planes, and a second
pass eats them.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from pathlib import Path

import numpy as np

from pipeline.buildings import (
    BUILDINGS_MANIFEST_NAME,
    BUILDINGS_MANIFEST_SCHEMA,
    CARVED_EDGES_KEY,
    FACADE_MATERIAL,
    stamp_along,
    union,
)
from pipeline.config import Carve, Config, SurfaceClass, load_config
from pipeline.documents import read_document, write_document
from pipeline.gltf import (
    MeshData,
    is_collider,
    is_occluder,
    normalise,
    partition,
    read_glb,
    read_render,
    write_glb,
)
from pipeline.mesh import merge, select_triangles, slice_plane, subtract_prism
from pipeline.polyline import plan_lengths, plan_projections, true_runs
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import mitres
from pipeline.terrain import HeightField

log = logging.getLogger(__name__)

CARVE_NAME = "carve.json"
# 2: `population` and `deck_top_kept` per row (`P3-51`); a reader summing rows
# as carriageway carves would be wrong about half of them.
CARVE_SCHEMA = 2


class Population(StrEnum):
    """Which rule put a row in `carve.json`: `Q19`'s listed carriageway cut
    or `P3-51`'s parapet band. A `str`, so the row serialises as the word."""

    CARRIAGEWAY = "carriageway"
    PARAPET = "parapet"


# A triangle whose normal is within this angle of horizontal is a wall for the
# band's purposes; steeper than this from the vertical, it is a deck or a cap.
# 60° from the vertical: a 1:2 batter on a retaining face still reads as a wall.
_BAND_WALL_COS = 0.5

# Cell for the structure height field the soffit query runs on. Matches
# `HeightField.from_meshes`' own default; a flyover deck is tens of metres
# across, so nothing here is resolved by a finer grid.
_FIELD_CELL_M = 8.0


@dataclass
class EdgeCarve:
    """What one configured edge cost, whether or not anything was cut.

    🔴 **Recorded over the refusals as well as the keeps** (`Q58`). An edge whose
    prism met no structure still appends a row, so `len(edges)` past the number
    that cut anything is how you tell the difference between "nothing was in the
    way" and "the join stopped working".
    """

    edge: int
    road_name: str
    width_m: float
    width_source: str
    stations: int
    soffit_bounded: int
    triangles_removed: int
    carved_area_m2: float
    carved_volume_m3: float
    wall_m: float
    # Tiles whose box the ribbon crosses — appended before any cut, so a row
    # can carry tiles alongside `triangles_removed: 0`. Not "tiles cut".
    tiles_considered: list[str] = field(default_factory=list)
    # `carriageway` (`Q19`'s listed cut) or `parapet` (`P3-51`'s band), schema 2.
    population: Population = Population.CARRIAGEWAY
    # Band rows only: LOD0 triangles the band's box met and KEPT as deck —
    # the counter a floor-at-the-ribbon mutation drives to 0 (`Q72`).
    deck_top_kept: int = 0


@dataclass
class CarveReport:
    edges: list[EdgeCarve] = field(default_factory=list)
    tiles_written: list[str] = field(default_factory=list)
    # 🔴 Must stay 0. A cut face wound away from the road is invisible from it
    # and solid from behind — the hole this stage exists to remove, wearing the
    # other sign. Derived from centreline positions rather than from the offset
    # the wall was built against, so it can actually fail. See `_facing_away`.
    facing_away: int = 0
    # The largest vertex count any re-emitted tier ended up with. `write_glb`
    # widens its index buffer past 65,535, so a tile crossing that silently
    # doubles its indices.
    widest_tier_vertices: int = 0

    @property
    def carved(self) -> list[EdgeCarve]:
        return [row for row in self.edges if row.triangles_removed]


def _stations(points: np.ndarray, spacing_m: float) -> np.ndarray:
    """Evenly spaced points along a polyline, carrying height.

    ⚠️ Its own walk rather than `carriageway._stations`, and the reason is the
    **signature, not the frame**: that one takes a 2-column plan and returns 2-D
    points, and the cut floor and the headroom are both measured from the
    ribbon's own `y`. The frame difference is real — it emits a normal right of
    travel where `surface.mitres` emits left, which `tools/centreline_error.py`
    calls the largest risk in that file — but it is not what forces a second
    walk, because this returns no normal at all and takes its offsets from
    `mitres` directly.
    """
    edges_at = plan_lengths(points)
    total = float(edges_at[-1])
    if total <= 0.0:
        return points[:1]

    count = max(2, int(np.ceil(total / spacing_m)) + 1)
    along = np.linspace(0.0, total, count)
    out = np.empty((count, 3))
    for axis in range(3):
        out[:, axis] = np.interp(along, edges_at, points[:, axis])
    return out


def _frame(offsets: np.ndarray, index: int) -> tuple[np.ndarray, np.ndarray]:
    """The mitre offset lifted to 3-D, and the unit travel direction at it.

    🔴 **One statement of the convention, because two would be the trap this
    module exists inside.** `surface.mitres` returns the offset as `(dz, -dx)` of
    travel, so travel is `(-o1, o0)` — written out in more than one place, that is
    a frame this file could get backwards in one of them and not the other, which
    is what `tools/centreline_error.py` calls the largest risk in its own file.

    ⚠️ The offset is **not** unit: `mitres` grows it by `1/cos(half turn)` at a
    bend so the rail stays parallel. It is returned raw, because a rail point
    wants the growth and a plane normal does not.
    """
    wide = np.array([offsets[index][0], 0.0, offsets[index][1]])
    return wide, normalise(np.array([[-wide[2], 0.0, wide[0]]]))[0]


def _facing_away(wall: MeshData, points: np.ndarray) -> int:
    """Wall triangles whose front face is turned away from the carriageway.

    🔴 **Must be 0, and it is derived a second way on purpose.** `_retaining_wall`
    winds each quad against `inward`, taken from the mitre offset; this measures
    the finished mesh against the *centreline positions* instead, so a sign error
    in that offset is caught rather than agreed with. A counter recomputed the way
    the geometry was built reads 0 by construction and certifies nothing — `Q72`'s
    tautology, which passed a whole region of signs facing the wrong way.

    ⚠️ It is reachable: `lamps._strut` shipped 25,116 of 35,880 triangles facing
    away and `facing_away` is what found it, before the asset was ever looked at.
    """
    centroids = wall.triangle_centroids()
    plan = points[:, [0, 2]]
    nearest = _nearest_in_plan(centroids[:, [0, 2]], plan)
    toward = np.zeros_like(centroids)
    toward[:, [0, 2]] = plan[nearest] - centroids[:, [0, 2]]
    return int((np.sum(wall.triangle_cross() * toward, axis=1) < 0.0).sum())


def _prisms(
    points: np.ndarray,
    offsets: np.ndarray,
    half_m: float,
    floors: np.ndarray,
    ceilings: np.ndarray,
) -> list[list[tuple[np.ndarray, float]]]:
    """One convex prism per polyline segment, tiling the ribbon without gaps.

    The side planes pass through the **mitred** rails, so consecutive prisms
    meet exactly on the rail point they share and their union is the ribbon
    polygon itself. The end planes contain the mitre offset at each vertex,
    which is the same shared line from the other direction — a segment prism
    that used its own square end would leave a wedge uncut on the outside of
    every bend, and a ramp is nothing but bends.

    ⚠️ `mitres` is the offset **direction and length**: it grows past unit at a
    bend by `1/cos(half turn)` so the rail stays parallel. The plane normal is
    therefore taken from the normalised offset and the plane is placed through
    the rail point, never at `half_m` along the raw vector.
    """
    prisms = []
    for index in range(len(points) - 1):
        planes: list[tuple[np.ndarray, float]] = []
        for vertex, sign in ((index, -1.0), (index + 1, 1.0)):
            _, ahead = _frame(offsets, vertex)
            planes.append((ahead * sign, float(points[vertex] @ (ahead * sign))))
        wide, _ = _frame(offsets, index)
        for sign in (1.0, -1.0):
            rail = points[index] + wide * half_m * sign
            unit = normalise(wide[None, :])[0] * sign
            planes.append((unit, float(rail @ unit)))

        floor = float(min(floors[index], floors[index + 1]))
        ceiling = float(min(ceilings[index], ceilings[index + 1]))
        planes.append((np.array([0.0, -1.0, 0.0]), -floor))
        planes.append((np.array([0.0, 1.0, 0.0]), ceiling))
        prisms.append(planes)
    return prisms


def _retaining_wall(
    removed: MeshData, plan: EdgePlan, source: MeshData
) -> tuple[MeshData | None, float]:
    """The cut face, as a wall per side sized to the structure removed.

    Per station and per side, the wall runs from the cut floor up to the highest
    removed structure within half a station of that station on that side. Where
    nothing was removed there it draws nothing, so the wall exists exactly along
    the run the carve opened rather than for the length of the edge.

    ⚠️ **Sized from removed geometry, never from the prism.** A wall drawn to the
    prism's ceiling would stand at the cut height wherever the structure was
    shorter — a slab of concrete hanging over the carriageway with nothing behind
    it — and would read as correct in every counter. `Q72`'s tautology: a number
    the construction guarantees says nothing.

    🔴 **And capped at the ribbon plus `plan.face_above_m` where the plan
    carries one** (`Q147`):
    the face closes the cut BELOW the deck, where the retained mass would
    otherwise show its hollow, and stops just above it. Above the deck the
    removed flank stood in the road and its remainder beyond the rail is the
    band's. Uncapped, the face was the ramps' parapet, 1.5-2.0 m along both
    rails of `e99`, and the user photographed it as the guard rail to remove.
    """
    points, offsets, half_m, floors = plan.points, plan.offsets, plan.half_m, plan.floors
    centroids = removed.triangle_centroids()
    tops = removed.positions[removed.triangles][:, :, 1].max(axis=1)

    quads: list[np.ndarray] = []
    metres = 0.0
    for index in range(len(points) - 1):
        wide, ahead = _frame(offsets, index)
        unit = normalise(wide[None, :])[0]

        span = (centroids @ ahead >= points[index] @ ahead) & (
            centroids @ ahead <= points[index + 1] @ ahead
        )
        if not span.any():
            continue
        floor = float(min(floors[index], floors[index + 1]))
        for sign in (1.0, -1.0):
            rail_at = float((points[index] + wide * half_m * sign) @ (unit * sign))
            near = span & (np.abs(centroids @ (unit * sign) - rail_at) <= half_m)
            if not near.any():
                continue
            top = float(tops[near].max())
            if plan.face_above_m is not None:
                # The HIGHER of the segment's two stations, where `floor` and
                # the prism's ceiling take the lower: the face is there to
                # close the hollow under the deck, and a cap at the lower end
                # would leave a slit into it at the higher. The price is a lip
                # of one station's rise at the low end, 0.1-0.2 m on a ramp.
                ribbon = float(max(points[index, 1], points[index + 1, 1]))
                top = min(top, ribbon + plan.face_above_m)
            if top <= floor:
                continue
            base = points[index] + wide * half_m * sign
            far = points[index + 1] + _frame(offsets, index + 1)[0] * half_m * sign
            low_a = np.array([base[0], floor, base[2]])
            low_b = np.array([far[0], floor, far[2]])
            high_a = np.array([base[0], top, base[2]])
            high_b = np.array([far[0], top, far[2]])
            # Wound to face the carriageway: the driver has to see it.
            inward = -unit * sign
            for corners in (
                np.array([low_a, low_b, high_b]),
                np.array([low_a, high_b, high_a]),
            ):
                normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
                quads.append(corners[::-1] if normal @ inward < 0.0 else corners)
            metres += float(np.linalg.norm(low_b - low_a))

    if not quads:
        return None, 0.0

    positions = np.concatenate(quads)
    normals = np.zeros((len(positions), 3), dtype=np.float32)
    for start in range(0, len(positions), 3):
        face = np.cross(
            positions[start + 1] - positions[start], positions[start + 2] - positions[start]
        )
        length = np.linalg.norm(face)
        normals[start : start + 3] = (face / length) if length else np.array([0.0, 1.0, 0.0])

    # 🔴 Channels from `removed`, never from the tile. A tile is one merged
    # primitive whose first vertex is usually a building, so taking them from
    # there tags the wall `FACADE` and the window-band shader draws storeys of
    # glazing on a concrete retaining wall — and moves it between the two share
    # gates `carriageway_occupancy.py` reads. Measured: BUILDING 1.204 → 1.292%
    # with the wall mislabelled.
    return (
        MeshData(
            name=f"{source.name}-carve",
            positions=positions,
            normals=normals,
            triangles=np.arange(len(positions), dtype=np.uint32).reshape(-1, 3),
            colours=None
            if removed.colours is None
            else np.tile(removed.colours[0], (len(positions), 1)),
            uvs=None if removed.uvs is None else np.tile(removed.uvs[0], (len(positions), 1)),
            uv2=None if removed.uv2 is None else _wall_rows(positions, removed),
            material=source.material,
        ),
        metres,
    )


def _wall_rows(positions: np.ndarray, removed: MeshData) -> np.ndarray:
    """The wall's `TEXCOORD_1`: marker and phase tiled from vertex 0 like the
    colour, the object row per vertex from the nearest removed vertex.

    `removed` is every structure the prism met, so one row across a wall that
    spans several put 348 wall vertices 27.6 m outside the box of the one
    object it named (`P5-11`); the nearest removed vertex is the structure
    this piece of wall stands in for. ⚠️ The phase is *not* taken per vertex:
    it seeds the window hash, the wall drew with vertex 0's before `P5-11`,
    and a per-vertex phase would move the carved tiles' frame.
    """
    assert removed.uv2 is not None
    uv2 = np.tile(removed.uv2[0], (len(positions), 1))
    uv2[:, 1] = removed.uv2[_nearest(positions, removed), 1]
    return uv2


# Elements of the `(chunk, targets, 3)` float64 difference `_nearest` forms at
# a time: 24 MB, whatever the two counts are.
_NEAREST_CHUNK_ELEMENTS = 1_000_000


def _nearest(positions: np.ndarray, removed: MeshData) -> np.ndarray:
    """Index of the removed vertex nearest each position.

    Brute force — the ETL carries no spatial index (`sign_sheets.py` records
    the refusal of scipy) — chunked by the *target* count, so the transient is
    bounded whatever a region's structure density does to `removed`.
    """
    out = np.empty(len(positions), dtype=np.int64)
    targets = removed.positions
    chunk = max(1, _NEAREST_CHUNK_ELEMENTS // max(1, len(targets)))
    for start in range(0, len(positions), chunk):
        block = positions[start : start + chunk]
        distance = ((block[:, None, :] - targets[None, :, :]) ** 2).sum(axis=2)
        out[start : start + chunk] = distance.argmin(axis=1)
    return out


def _double_side(wall: MeshData) -> MeshData:
    """The wall with a back face — one reversed triangle per drawn triangle.

    🔴 **The tile shader is `cull_back` and the wall is one quad thick, so from
    behind it draws nothing.** That is an invisible cut face: the hole this stage
    exists to remove, wearing the other sign, and `Q19`'s estate is not watertight
    (5.38% of edge slots open) so there are holes to see it through. Measured on
    `e99` FLEMING ROAD from the driving seat — the wall is there from the
    carriageway and gone from four metres the other side of it.

    ⚠️ **A render mode cannot fix this here.** `railings.gdshader` met the same
    shape and answered it with `cull_disabled`; the wall is merged into the tile,
    and the tile is every building in the region, so `cull_disabled` there would
    turn the whole city double-sided. The back face has to be geometry.

    ⚠️ **Coincident, never offset.** The pair shares its vertex positions exactly,
    so from any viewpoint exactly one of the two survives `cull_back` and there is
    nothing to z-fight with. Giving the wall a thickness instead would push its
    back face into the structure the carve deliberately retained.

    🔴 **The free version was refused, and the reason is lighting.** Appending
    `triangles[:, ::-1]` alone doubles the faces at **zero** added vertices and
    needs nothing else — but the back face would then share the front's outward
    `NORMAL`, and `city_facade.gdshader` consumes it for real (`MODEL_NORMAL_MATRIX
    * NORMAL`, the faceted-shading dot, and `city_facade_clean`'s fresnel), so the
    back of the wall would be lit as though it faced the road. Splitting the
    vertices to carry a negated normal is what buys correct shading; 6 vertices
    per quad is forced, not sloppy. `test_the_back_face_carries_its_own_negated_normal`
    is the ratchet.

    ⚠️ **Reversed by index and merged, rather than by rebuilding the buffers.**
    `merge` carries every attribute through by concatenation, so this stays
    correct for a mesh whose colours or UVs vary per vertex. Reconstructing them
    instead means tiling vertex 0's value, and `TEXCOORD_0.y` is the
    `SurfaceClass` channel `_structure` cuts on — so that spelling would
    misclassify the wall silently, which is the failure `_retaining_wall`'s own
    channel comment exists to prevent. ⚠️ `merge` drops `material` deliberately
    (many in, one out); it is restored here rather than left to `_carve_tile`'s
    later rename, so this function returns a whole mesh on its own terms.

    🔴 **Applied at emission, never inside `_retaining_wall`.** `_facing_away`
    grades what that function wound, and half of a double-sided wall faces away
    *by construction* — graded after the mirror the counter reads half the wall
    whatever the geometry does, which is `Q72`'s tautology arriving from the
    other side. `test_the_mirror_is_why_the_counter_is_taken_first` is the ratchet.
    """
    back = replace(wall, triangles=wall.triangles[:, ::-1], normals=-wall.normals)
    return replace(merge([wall, back], name=wall.name), material=wall.material)


@dataclass
class EdgePlan:
    """One edge's stations, prisms and the row they will be reported on.

    `band` is the parapet population: what its box meets is sorted by
    `_band_split` rather than removed whole, and it draws no wall.
    """

    row: EdgeCarve
    points: np.ndarray
    offsets: np.ndarray
    half_m: float
    floors: np.ndarray
    prisms: list[list[tuple[np.ndarray, float]]]
    band: bool = False
    wall_tolerance_m: float = 0.0
    wall_max_m: float = np.inf
    # Listed (carriageway) plans: how far above the ribbon the cut face may
    # stand, or None for the top of what was removed. `Q147`: a face drawn to
    # the removed flank's top was a 1.5-2.0 m wall along both rails of `e99`,
    # the one parapet the band could not reach because the face is built
    # after it runs.
    face_above_m: float | None = None
    # Band plans: the band's half-width at each station — the deck's rim, or
    # the drawn rail where that is wider, plus `reach_m`. `half_m` is its
    # maximum, for the plan box.
    half_at: np.ndarray | None = None

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Plan box of the ribbon, widened by its own half-width."""
        reach = self.half_m * 2.0
        return self.points.min(axis=0) - reach, self.points.max(axis=0) + reach


def _structure_field(out_dir: Path, manifest: dict) -> HeightField:
    """A height field over every tile's `INFRASTRUCTURE`, for the soffit query.

    Built from the **shipped** tiles rather than the sheets, so the soffit a cut
    stops under is the one a driver will actually meet. LOD0 only: it is the
    tier that carries collision, and the coarser tier is the same structure
    decimated.
    """
    meshes = []
    for tile in manifest["tiles"]:
        [mesh] = read_render(out_dir / tile["lods"][0]["path"])
        keep = _structure(mesh)
        if keep.any():
            meshes.append(select_triangles(mesh, keep))
    if not meshes:
        raise ValueError("no INFRASTRUCTURE in any tile — has the buildings stage run?")
    return HeightField.from_meshes(meshes, cell_m=_FIELD_CELL_M)


def _plan_edge(edge: dict, spec: Carve, overhead: HeightField) -> EdgePlan:
    """Stations, floors, ceilings and prisms for one configured edge."""
    points = _stations(np.array(edge["polyline"], dtype=np.float64), spec.station_m)
    offsets = mitres(points)
    half_m = float(edge["width_m"]) / 2.0

    ribbon = points[:, 1]
    floors = ribbon - spec.floor_below_m
    soffits = overhead.sample_lowest_soffit_above(
        points[:, 0], points[:, 2], ribbon + spec.headroom_m
    )
    ceilings = np.where(np.isnan(soffits), np.inf, soffits - spec.soffit_clearance_m)

    name = edge["road_name"].get("en") or "(unnamed)"
    row = EdgeCarve(
        edge=edge["id"],
        road_name=name,
        width_m=float(edge["width_m"]),
        width_source=edge["width_source"],
        stations=len(points),
        soffit_bounded=int(np.isfinite(ceilings).sum()),
        triangles_removed=0,
        carved_area_m2=0.0,
        carved_volume_m3=0.0,
        wall_m=0.0,
    )
    return EdgePlan(
        row=row,
        points=points,
        offsets=offsets,
        half_m=half_m,
        floors=floors,
        prisms=_prisms(points, offsets, half_m, floors, ceilings),
        face_above_m=None if spec.parapets is None else spec.parapets.face_above_m,
    )


def _nearest_in_plan(queries: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """For each `(x, z)` query, the index of the nearest `(x, z)` target —
    brute force, for the station-sized target sets the carve has; `_nearest`
    is the chunked one for a whole mesh."""
    return np.argmin(((queries[:, None, :] - targets[None, :, :]) ** 2).sum(axis=2), axis=1)


def _band_plans(
    edge: dict, spec: Carve, overhead: HeightField, listed: tuple[int, ...] = ()
) -> list[EdgePlan]:
    """The parapet band's plans over one edge: the whole polyline on a LISTED
    edge (`Q19`'s eight ramps — walled flanks whose heights came from terrain,
    so `on_structure` never trips) or on a banded level, or each run of
    `on_structure` stations on a level-0 edge (`Q23`'s approaches). Empty where
    the edge is none of these — every edge, as shipped, but the listed ones.

    The prism spans the DECK — the drawn ribbon, `width_m` about `offset_m`,
    or the measured rim (`deck_rim_m`, `Q107`) where that reaches further —
    plus `reach_m` beyond it, floored AT the ribbon rather than `floor_below_m`
    under it: the deck is what the car drives on and `_band_split` is what
    keeps it. 🔴 **The rim, not the authored width, is where the parapet
    stands**: `e208` FLEMING ROAD is authored 5.60 m wide on a deck the rim
    survey reads out to 8.0 m, and a band on the width alone sliced that
    parapet at its edge and left it. One prism over the whole deck rather than
    two beside the rails, because the split already tells deck from wall and
    nothing stands above the deck inside a ribbon a car can drive.
    """
    parapets = spec.parapets
    if parapets is None:
        return []
    polyline = np.array(edge["polyline"], dtype=np.float64)
    level = int(edge.get("elevation_level", 0))
    runs: list[np.ndarray] = []
    if edge["id"] in listed or level in parapets.levels:
        runs.append(polyline)
    elif level == 0 and parapets.on_structure:
        runs.extend(_structure_runs(polyline, edge.get("on_structure") or []))
    if not runs:
        return []

    name = edge["road_name"].get("en") or "(unnamed)"
    row = EdgeCarve(
        edge=edge["id"],
        road_name=name,
        width_m=float(edge["width_m"]),
        width_source=edge["width_source"],
        stations=0,
        soffit_bounded=0,
        triangles_removed=0,
        carved_area_m2=0.0,
        carved_volume_m3=0.0,
        wall_m=0.0,
        population=Population.PARAPET,
    )
    drawn = float(edge["width_m"]) / 2.0 + abs(float(edge.get("offset_m", 0.0)))
    rim_at_vertex = _rim_reach(edge.get("deck_rim_m") or [], len(polyline), drawn)
    plans = []
    for run in runs:
        points = _stations(run, spec.station_m)
        if len(points) < 2:
            continue
        offsets = mitres(points)
        ribbon = points[:, 1]
        # The rim at each station is the nearest source vertex's, in plan.
        nearest = _nearest_in_plan(points[:, [0, 2]], polyline[:, [0, 2]])
        half_at = rim_at_vertex[nearest] + parapets.reach_m
        half_m = float(half_at.max())
        soffits = overhead.sample_lowest_soffit_above(
            points[:, 0], points[:, 2], ribbon + spec.headroom_m
        )
        ceilings = np.where(np.isnan(soffits), np.inf, soffits - spec.soffit_clearance_m)
        row.stations += len(points)
        row.soffit_bounded += int(np.isfinite(ceilings).sum())
        plans.append(
            EdgePlan(
                row=row,
                points=points,
                offsets=offsets,
                half_m=half_m,
                floors=ribbon,
                # No prisms: the band cuts by centroid and floor alone
                # (`_band_candidates`), and the ceiling's work is `wall_max_m`.
                prisms=[],
                band=True,
                wall_tolerance_m=parapets.wall_tolerance_m,
                wall_max_m=parapets.wall_max_m,
                half_at=half_at,
            )
        )
    return plans


def _rim_reach(deck_rim_m: list, count: int, drawn: float) -> np.ndarray:
    """Per source vertex, how far the deck reaches from the centreline: the
    wider of the two published rims (`deck_rim_m`, `Q107`), or the drawn rail
    where that is wider or the rim is unpublished."""
    reach = np.full(count, drawn)
    for index, pair in enumerate(deck_rim_m[:count]):
        if not isinstance(pair, list | tuple):
            continue
        sides = [float(side) for side in pair if side is not None]
        if sides:
            reach[index] = max(drawn, *sides)
    return reach


def _structure_runs(polyline: np.ndarray, on_structure: list) -> list[np.ndarray]:
    """Maximal runs of consecutive vertices published `on_structure`, two or
    more long — a run of one is a point, and a point has no prism."""
    flags = np.zeros(len(polyline), dtype=bool)
    flags[: len(on_structure)] = [bool(flag) for flag in on_structure[: len(polyline)]]
    return [polyline[start:stop] for start, stop in true_runs(flags) if stop - start >= 2]


def _prisms_met(work: MeshData | None, plan: EdgePlan) -> np.ndarray:
    """Per prism, whether its plan box meets any triangle's plan box."""
    if work is None:
        return np.zeros(len(plan.prisms), dtype=bool)
    corners = work.positions[work.triangles][:, :, [0, 2]]
    low, high = corners.min(axis=1), corners.max(axis=1)
    met = np.zeros(len(plan.prisms), dtype=bool)
    for index in range(len(plan.prisms)):
        wide = _frame(plan.offsets, index)[0] * plan.half_m
        wide_next = _frame(plan.offsets, index + 1)[0] * plan.half_m
        rails = np.array(
            [
                plan.points[index] + wide,
                plan.points[index] - wide,
                plan.points[index + 1] + wide_next,
                plan.points[index + 1] - wide_next,
            ]
        )[:, [0, 2]]
        box_low, box_high = rails.min(axis=0), rails.max(axis=0)
        met[index] = bool(((high >= box_low) & (low <= box_high)).all(axis=1).any())
    return met


def _station_of(centroids: np.ndarray, plan: EdgePlan) -> np.ndarray:
    """Each plan `(x, z)` centroid's nearest station — the one whose floor its
    triangle is judged against, so a ramp's deck is deck all the way down."""
    return _nearest_in_plan(centroids, plan.points[:, [0, 2]])


def _band_candidates(work: MeshData, plan: EdgePlan) -> _Candidates:
    """What the band takes, whole, and what it never touches.

    🔴 **No prism, no side plane, no end plane: a parapet is taken WHOLE by
    its centroid, after ONE floor cut at its station.** Three builds priced
    every other shape. Prisms over everything in the plan's box sliced the
    slab's own side at every 2 m station (**974,450 → 1,433,856** vertices
    over Wan Chai's tiles, 94 → 138 MB); prisms over what rises above the deck
    still sliced every wall straddling the band's edge and kept the slivers
    (1,120 triangles under 0.01 m² on one tile where the source had 145, the
    region +22%); and widening the band to the rim fed them more walls to
    straddle (7,492 slivers). A parapet runs along the road, so its centroid
    says where it stands, and what it costs is exact: a wall standing across
    the band comes out whole rather than cut at the band's edge. The floor
    cut is the one slice, because a parapet's face and the slab's side are
    often one face, and the side below the deck is the flyover seen from the
    street.
    """
    # The band first, so the station search and the split run over what
    # stands in it rather than over the plan's whole box.
    centroids = work.triangle_centroids()[:, [0, 2]]
    within = _within_band(centroids, plan)
    station = np.zeros(len(centroids), dtype=int)
    station[within] = _station_of(centroids[within], plan)
    floors = plan.floors[station]
    parapet, _ = _band_split(work, floors, plan.wall_tolerance_m, plan.wall_max_m)
    heights = work.positions[work.triangles][:, :, 1]
    candidate = within & parapet & (heights.max(axis=1) > floors)
    aside = select_triangles(work, ~candidate)
    if not candidate.any():
        return _Candidates(None, aside)
    candidates = select_triangles(work, candidate)
    # Only a triangle its floor passes through needs the cut; one standing
    # wholly above it goes whole, and the floor cut leaves it unchanged anyway.
    at = station[candidate]
    straddles = heights[candidate].min(axis=1) < plan.floors[at]
    taken: list[MeshData] = []
    below: list[MeshData] = [aside] if aside is not None else []
    whole = select_triangles(candidates, ~straddles)
    if whole is not None:
        taken.append(whole)
    for index in np.unique(at[straddles]):
        group = select_triangles(candidates, straddles & (at == index))
        floor = float(plan.floors[index])
        cut = slice_plane(group, (0.0, 1.0, 0.0), floor)
        over = cut.triangle_centroids()[:, 1] > floor
        for keep, into in ((over, taken), (~over, below)):
            part = select_triangles(cut, keep)
            if part is not None:
                into.append(part)
    return _Candidates(_merged(taken, work.name), _merged(below, work.name))


def _merged(parts: list[MeshData], name: str) -> MeshData | None:
    if not parts:
        return None
    return merge(parts, name=name) if len(parts) > 1 else parts[0]


def _within_band(points: np.ndarray, plan: EdgePlan) -> np.ndarray:
    """Whether each plan `(x, z)` point lies within the band of some segment
    of the run — that segment's half-width (`half_at`, the wider of its two
    stations') about it — chunked like `_nearest`."""
    starts = plan.points[:-1][:, [0, 2]]
    deltas = plan.points[1:][:, [0, 2]] - starts
    halves = np.maximum(plan.half_at[:-1], plan.half_at[1:])
    out = np.empty(len(points), dtype=bool)
    chunk = max(1, _NEAREST_CHUNK_ELEMENTS // max(1, len(starts)))
    for start in range(0, len(points), chunk):
        block = points[start : start + chunk]
        _fraction, distance = plan_projections(block[:, None, :], starts[None, :, :], deltas)
        out[start : start + chunk] = (distance <= halves[None, :]).any(axis=1)
    return out


@dataclass(frozen=True)
class _Candidates:
    """A band plan's work, sorted: what goes, whole, and what stays."""

    taken: MeshData | None
    kept: MeshData | None


def _snap_rows(mesh: MeshData, source: MeshData) -> MeshData:
    """`TEXCOORD_1` for every vertex a slice invented, copied from the nearest
    source vertex. The slicer interpolates every channel, and a triangle
    welded across two objects by `collapse` carries two rows, so its cut
    vertex lands between them on a row nobody owns — `verify_tiles` refuses
    it. The carriageway carve met none in 8 edges; the band met 117 in one
    tile."""
    if mesh.uv2 is None or source.uv2 is None:
        return mesh
    rows = mesh.uv2[:, 1]
    invented = np.abs(rows - np.round(rows)) > 1e-4
    if not invented.any():
        return mesh
    uv2 = mesh.uv2.copy()
    uv2[invented] = source.uv2[_nearest(mesh.positions[invented], source)]
    return replace(mesh, uv2=uv2)


def _band_split(
    removed: MeshData, floor: float | np.ndarray, tolerance_m: float, max_m: float = np.inf
) -> tuple[np.ndarray, np.ndarray]:
    """Which of the triangles a band may meet are parapet and which are deck.

    🔴 **The deck is told from the wall by the NORMAL, and the cap by height.**
    A wall is a triangle within 60° of vertical (`_BAND_WALL_COS`); the floor
    cut then slices it at its station's deck, so only the part above goes. A
    cap is any face standing wholly above `floor + tolerance_m`, the parapet's
    top or a kerb upstand's — `floor` is per triangle, the ribbon's height at
    its nearest station. Everything else — the deck top at the ribbon's height,
    its underside, a face straddling the tolerance — is deck, and never enters
    a prism. ⚠️ Keeping by "not wall" alone would keep the cap as a floating
    slab a metre up; removing by height alone would take the deck. Both tests
    are needed and both have a test.
    """
    corners = removed.positions[removed.triangles]
    cross = removed.triangle_cross()
    length = np.linalg.norm(cross, axis=1)
    safe = np.where(length > 0.0, length, 1.0)
    normal_y = np.where(length > 0.0, np.abs(cross[:, 1]) / safe, 1.0)
    wall = normal_y < _BAND_WALL_COS
    cap = corners[:, :, 1].min(axis=1) > floor + tolerance_m
    # A face whose top stands more than `max_m` above the deck is not a
    # parapet: a pier carrying the flyover overhead, the side of a higher deck
    # alongside, a noise barrier. It stays whole.
    low_enough = corners[:, :, 1].max(axis=1) <= floor + max_m
    parapet = (wall | cap) & low_enough
    return parapet, ~parapet


def _register(plan: EdgePlan, tiles: dict, plans: dict[str, list[EdgePlan]]) -> None:
    """Queue the plan on every tile its ribbon meets, and book the tile on its
    row once — a band edge's runs share one row, so two plans can meet the
    same tile."""
    for tile_id in _tiles_for(plan, tiles):
        plans.setdefault(tile_id, []).append(plan)
        if tile_id not in plan.row.tiles_considered:
            plan.row.tiles_considered.append(tile_id)


def _tiles_for(plan: EdgePlan, tiles: dict) -> list[str]:
    """Tiles whose published AABB meets this edge's ribbon in plan."""
    low, high = plan.bounds()
    out = []
    for tile_id, tile in tiles.items():
        (ax, _ay, az), (bx, _by, bz) = tile["aabb"]
        if bx >= low[0] and ax <= high[0] and bz >= low[2] and az <= high[2]:
            out.append(tile_id)
    return sorted(out)


@dataclass(frozen=True)
class _Carved:
    """One plan taken out of one mesh: what is left, and what to book."""

    remaining: MeshData | None
    # What the prisms removed; None where they met nothing.
    removed: MeshData | None
    # The inward-only retaining wall, before `_double_side`; None for a band.
    wall: MeshData | None
    wall_m: float
    # Band plans only: the triangles classified deck and kept whole.
    deck_top_kept: int


@dataclass(frozen=True)
class _Cut:
    """One mesh after every plan has been taken out of it."""

    mesh: MeshData
    # The inward-only wall each plan built, before `_double_side`.
    walls: list[tuple[MeshData, EdgePlan]]
    # What each plan took, for `_account`.
    removals: list[tuple[EdgePlan, _Carved]]


def _carve_tile(out_dir: Path, tile: dict, plans: list[EdgePlan], report: CarveReport) -> None:
    """Cut every plan out of one tile, both tiers, and re-emit the tiers it cut.

    A tier's file holds the render mesh and its helpers — the `-colonly`
    collider on the finest tier (`P5-12`) and the `-occonly` occluder on every
    tier (`P5-13`) — and the prisms are taken out of **all of them**: a wall
    carved from what the player sees and left in what the car hits is the
    stranding the carve exists to end, and one left in the occluder culls what
    stands behind a wall that is no longer there. The counters are the render
    mesh's alone: each helper is decimated at its own cell, so their removals
    are not one number.
    """
    boxes: list = []
    rewritten = False
    for tier, lod in enumerate(tile["lods"]):
        path = out_dir / lod["path"]
        drawn, helpers = partition(read_glb(path))
        colliders = sum(is_collider(mesh) for mesh in helpers)
        occluders = sum(is_occluder(mesh) for mesh in helpers)
        if len(drawn) != 1 or colliders > 1 or occluders > 1:
            raise ValueError(
                f"{lod['path']} holds {len(drawn)} render, {colliders} collider and "
                f"{occluders} occluder primitives, expected one and at most one of each"
            )
        source = drawn[0]
        boxes.append(source.aabb())

        cut = _carve_mesh(source, plans, FACADE_MATERIAL)
        cut_helpers = [_carve_mesh(helper, plans, None) for helper in helpers]
        # A tier the prisms never met is left exactly as `buildings.py` wrote it
        # — not rewritten identically, but never opened for writing at all.
        if cut is None and all(each is None for each in cut_helpers):
            continue

        if cut is not None:
            if tier == 0:
                for plan, carved in cut.removals:
                    _account(plan.row, carved.removed)
                    plan.row.wall_m += carved.wall_m
                    plan.row.deck_top_kept += carved.deck_top_kept
            report.facing_away += sum(_facing_away(wall, plan.points) for wall, plan in cut.walls)
        carved = source if cut is None else cut.mesh
        written = [carved]
        for helper, cut_helper in zip(helpers, cut_helpers, strict=True):
            mesh = helper if cut_helper is None else cut_helper.mesh
            written.append(mesh)
            if is_collider(mesh):
                lod["collision_triangles"] = mesh.triangle_count
                lod["collision_vertices"] = len(mesh.positions)
            elif is_occluder(mesh):
                lod["occluder_triangles"] = mesh.triangle_count
                lod["occluder_vertices"] = len(mesh.positions)
            else:
                # A helper kind this stage cannot book: its counters would go
                # stale in `buildings.json` with the geometry cut correctly.
                raise ValueError(f"{lod['path']}: unrecognised helper primitive {mesh.name!r}")
        lod["bytes"] = write_glb(path, written)
        lod["triangles"] = carved.triangle_count
        lod["vertices"] = len(carved.positions)
        boxes[-1] = carved.aabb()
        rewritten = True
        report.tiles_written.append(lod["path"])
        report.widest_tier_vertices = max(report.widest_tier_vertices, len(carved.positions))

    if rewritten:
        _retile_aabb(tile, boxes)


def _carve_mesh(source: MeshData, plans: list[EdgePlan], material: str | None) -> _Cut | None:
    """Every plan taken out of one mesh, or `None` where no prism met it.

    `material` is stated by the caller because `read_glb` does not read one
    back: `FACADE_MATERIAL` for the render tier, nothing for the collider.
    """
    keep = _structure(source)
    if not keep.any():
        return None
    structure = select_triangles(source, keep)
    rest = select_triangles(source, ~keep)

    walls: list[tuple[MeshData, EdgePlan]] = []
    removals: list[tuple[EdgePlan, _Carved]] = []
    for plan in plans:
        carved = _carve_plan(structure, plan, source)
        structure = carved.remaining
        if carved.removed is None:
            continue
        removals.append((plan, carved))
        if carved.wall is not None:
            walls.append((carved.wall, plan))
    if not removals:
        return None

    # 🔴 `walls` keeps the inward-only wall; the mirror happens here so that
    # `_facing_away` still grades a mesh whose every triangle should face the
    # road. See `_double_side`.
    parts = [
        part
        for part in (rest, structure, *(_double_side(wall) for wall, _ in walls))
        if part is not None
    ]
    if not parts:
        return None
    carved = merge(parts, name=source.name)
    # 🔴 `read_glb` does not read a primitive's material back, so a tile
    # re-emitted without this imports on the default `BaseMaterial3D` and the
    # window-band shader disappears from ten tiles, silently.
    carved = _named(carved, source.name, material, source.extras)
    # 🔴 And `TEXCOORD_0.x` is re-stamped over the whole carved tier, because
    # it is a function of the vertex that ships: a cut vertex interpolates
    # its UV linearly along the edge, and the along-coordinate is not linear
    # where the normal turns — on the smooth-shaded ground it read up to
    # 124 m off — and the wall copied a structure vertex's, 754 m off. The
    # shader used to derive it from world position at exactly this vertex,
    # so stamping it here is what keeps the carved tiles' frame where it was.
    # (A no-op on the collider, which ships no `TEXCOORD_0`.)
    return _Cut(stamp_along(carved), walls, removals)


def _carve_plan(structure: MeshData | None, plan: EdgePlan, source: MeshData) -> _Carved:
    """One edge's prisms taken out of one tier: what is left, what was cut, its
    wall and its metres, and the triangles a band classified deck and kept.

    ⚠️ **The tier is split against the ribbon's box before the prisms run, and
    that is not a micro-optimisation.** A prism is one 2 m segment and a tile's
    structure is thousands of triangles, so **88%** of the per-prism calls used to
    scan the whole mesh to discover they met nothing: 22.4 M triangle
    classifications, 4.0 s of a 4.9 s stage. Bounding the work to the band the
    ribbon passes through takes the stage to **2.0 s** with byte-identical
    removals. The box is `plan.bounds()`, already trusted by `_tiles_for`, so
    this inherits that assumption rather than adding one.

    ⚠️ **In plan only.** Two of the seven edges have no soffit and carve to the
    sky, so their prisms are unbounded above and a `y` test would drop the very
    structure they exist to remove.
    """
    if structure is None:
        return _Carved(None, None, None, 0.0, 0)

    low, high = plan.bounds()
    corners = structure.positions[structure.triangles][:, :, [0, 2]]
    near = (corners.max(axis=1) >= low[[0, 2]]).all(axis=1) & (
        corners.min(axis=1) <= high[[0, 2]]
    ).all(axis=1)
    if not near.any():
        return _Carved(structure, None, None, 0.0, 0)
    work = select_triangles(structure, near)
    aside = select_triangles(structure, ~near)

    kept: list[MeshData] = []
    taken_whole: MeshData | None = None
    if plan.band and work is not None:
        # 🔴 **The deck is set aside WHOLE before any prism runs, and so is
        # everything below it.** The first build split the prism's removal
        # into deck and parapet per station and merged the deck back: correct,
        # and the deck came back sliced at every 2 m station — `e118` 82,598
        # triangles removed for 673 m², the widest tier 22,486 → 91,670
        # vertices. `_band_candidates` classifies first, so the prisms only
        # ever meet what rises above the deck, and the deck ships as the
        # publisher drew it.
        sorted_work = _band_candidates(work, plan)
        work = None
        if sorted_work.kept is not None:
            kept.append(sorted_work.kept)
        taken_whole = sorted_work.taken

    taken: list[MeshData] = [taken_whole] if taken_whole is not None else []
    volume = 0.0
    if taken_whole is not None:
        box_low, box_high = taken_whole.aabb()
        volume += float(np.prod(np.asarray(box_high) - np.asarray(box_low)))
    # ⚠️ **89% of prism calls met nothing** (38,104 of 42,812 on Wan Chai with
    # the band, 11.9 s of 18.8 s): a plan's prisms run the whole edge and its
    # work is one tile's corner of it. A prism whose plan box misses every
    # triangle of the work it started from cannot meet a piece sliced from
    # one either, so those are skipped here — byte-identical, and the
    # carriageway prisms' 7,310 empty calls go with them.
    met = _prisms_met(work, plan)
    for prism, hit in zip(plan.prisms, met, strict=True):
        if work is None:
            break
        if not hit:
            continue
        work, removed = subtract_prism(work, prism)
        if removed is None:
            continue
        taken.append(removed)
        # Per prism, because one box over a whole edge's removals spans the
        # ramp's whole curve and reports many times what was taken.
        box_low, box_high = removed.aabb()
        volume += float(
            (box_high[0] - box_low[0]) * (box_high[1] - box_low[1]) * (box_high[2] - box_low[2])
        )

    left = [part for part in (aside, work, *kept) if part is not None]
    remaining = merge(left, name=structure.name) if len(left) > 1 else (left[0] if left else None)
    if plan.band and remaining is not None:
        remaining = _snap_rows(remaining, structure)
    kept_triangles = sum(part.triangle_count for part in kept)
    if not taken:
        return _Carved(remaining, None, None, 0.0, kept_triangles)

    plan.row.carved_volume_m3 += volume
    cut = merge(taken, name="cut") if len(taken) > 1 else taken[0]
    if plan.band:
        # No wall: a parapet is a sheet, and what the band leaves is the deck's
        # own edge. The deck triangles kept are handed back for the caller to
        # book on LOD0 alone, like every other counter.
        return _Carved(remaining, cut, None, 0.0, kept_triangles)
    wall, metres = _retaining_wall(cut, plan, source)
    return _Carved(remaining, cut, wall, metres, kept_triangles)


def _account(row: EdgeCarve, cut: MeshData) -> None:
    """Fold one tile's removed geometry into an edge's row.

    Area is the removed surface's own area — the description a reviewer needs
    to judge whether the carve reached too far. Counted on LOD0 only: the
    coarser tier is the same structure decimated, so adding it would double a
    quantity that has one physical value. ⚠️ The volume is accumulated per prism
    by the caller rather than here, because one bounding box over a whole edge's
    removals spans the ramp's curve and reports many times what was taken.
    """
    row.triangles_removed += cut.triangle_count
    row.carved_area_m2 += float(np.linalg.norm(cut.triangle_cross(), axis=1).sum() / 2.0)


def _named(mesh: MeshData, name: str, material: str | None, extras: dict | None = None) -> MeshData:
    """`merge` drops both, deliberately, so the caller renames what it merged.

    🔴 The name carries `-colonly` on the collider, which is what gives the tile
    its trimesh (`P5-12`). Reconstructing it from the tile id would lose the
    suffix, so it is taken from the mesh that was read — as is the material,
    which is `FACADE_MATERIAL` on the render tier and nothing on the collider.

    The `extras` object table (`P5-11`) is the third thing `merge` drops. The
    carve keeps the tile's local row indices — the wall inherits the removed
    structure's row, and `rest` is a selection — so the table read back is
    still the right one and is reattached whole.
    """
    return replace(mesh, name=name, material=material, extras=extras)


def _retile_aabb(tile: dict, boxes: list) -> None:
    """Republish the tile's box from the tiers as re-emitted.

    ⚠️ `buildings.json`'s `aabb` is the union of the **shipped** tiers, and
    `verify_city.gd` compares it against what the engine loads — it has caught a
    19 m discrepancy before. A carve that shrinks a tier and leaves the old box
    ships a claim the geometry no longer supports.

    Takes the boxes the caller already has rather than re-reading the files it
    just wrote, and reduces them through `buildings.union` — the canonical
    statement of this rule, next to the manifest field it fills.
    """
    low, high = union(boxes)
    tile["aabb"] = [list(low), list(high)]


def _log(report: CarveReport) -> None:
    carved = report.carved
    band = [row for row in report.edges if row.population == Population.PARAPET]
    log.info(
        "  carve: %d edges planned (%d listed, %d banded), %d cut, %d tiers re-emitted",
        len(report.edges),
        len(report.edges) - len(band),
        len(band),
        len(carved),
        len(report.tiles_written),
    )
    for row in report.edges:
        log.info(
            "    e%-4d %-24s %-11s w=%5.2f  %4d stations, %3d soffit-bounded  "
            "%6d tris, %8.1f m2, wall %6.1f m, deck kept %5d",
            row.edge,
            row.road_name[:24],
            row.population,
            row.width_m,
            row.stations,
            row.soffit_bounded,
            row.triangles_removed,
            row.carved_area_m2,
            row.wall_m,
            row.deck_top_kept,
        )
    if report.widest_tier_vertices > 65535:
        log.info(
            "    \u26a0 widest tier now %d vertices — past 65,535, so its index buffer widened",
            report.widest_tier_vertices,
        )


def _row(row: EdgeCarve) -> dict:
    """One edge's row, floats rounded to millimetres."""
    out = asdict(row)
    out["tiles_considered"] = sorted(out["tiles_considered"])
    for key, value in out.items():
        if isinstance(value, float):
            out[key] = round(value, 3)
    return out


def _document(city: Config, region_id: str, report: CarveReport) -> dict:
    """Written unconditionally, `landmark_assets.json`'s precedent: a missing
    file means the stage never ran, not that there was nothing to do."""
    return {
        "schema_version": CARVE_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "tiles_written": sorted(report.tiles_written),
        "facing_away": report.facing_away,
        "widest_tier_vertices": report.widest_tier_vertices,
        # `asdict` rather than a second list of the field names, on
        # `buildings._write_manifest`'s precedent: a field added to `EdgeCarve`
        # and forgotten here would be a counter that exists and is never published.
        "edges": [_row(row) for row in report.edges],
    }


def _structure(mesh: MeshData) -> np.ndarray:
    """Which triangles came from `INFRASTRUCTURE`, read off `TEXCOORD_1.x`.

    `TEXCOORD_0.y` until `P5-11`, when the marker moved to the identity channel
    and `TEXCOORD_0` became a planar UV. ⚠️ Reading the wrong channel here does
    not fail: every prism finds no soffit, `soffit_bounded` reads 0 on every
    edge and the cut goes through the deck — which is how the move was caught.
    """
    if mesh.uv2 is None:
        return np.zeros(len(mesh.triangles), dtype=bool)
    classes = np.floor(mesh.uv2[:, 0]).astype(int)
    return classes[mesh.triangles].min(axis=1) == int(SurfaceClass.STRUCTURE)


def build_region(
    city: Config,
    region_id: str,
    *,
    out_root: Path | None = None,
) -> CarveReport:
    """Carve every configured edge out of the tiles it touches, and re-emit them.

    ⚠️ **Only the touched tiles are re-emitted.** The untouched ones are not
    rewritten and not compared — which is what makes them byte-identical, rather
    than a `cmp` afterwards saying they happen to be. ⚠️ They are **read**,
    though: `_structure_field` opens every tile's LOD0 for the soffit, 66 against
    the 14 touched, so this is a claim about writes and never about reads.

    🔴 **No `sources_root` and no `buildings.Placement`** — the shape `surface`,
    `clearance` and `fence` already have, for the same reason. This opened with
    one for its `out_dir` alone, and of the four other fields `sheets` reads the
    tile index a *fetch* leaves on disk. That coupled a bundle-only stage to
    `etl/sources/`, which CI never populates, and left it red for eight runs on
    a test about a file in `etl/out/` (`Q19`).
    """
    out_dir = city.out_dir(region_id, out_root)
    report = CarveReport()
    spec = city.carve
    # ⚠️ **A region with no edges takes the absent block's path**, deliberately:
    # `Q19`'s population is a measurement run over `wan_chai`, so a region nobody
    # has measured has nothing to carve rather than a list gone missing. Both
    # arrive here as "no-op, and the bundle is byte-identical" (`Q95`).
    carved_edges = () if spec is None else spec.edges_for(region_id)
    banded = spec is not None and spec.parapets is not None
    if not carved_edges and not banded:
        log.info("  no carve configured for %s; the bundle is unchanged", region_id)
        write_document(out_dir / CARVE_NAME, _document(city, region_id, report))
        return report

    manifest = read_document(
        out_dir / BUILDINGS_MANIFEST_NAME,
        BUILDINGS_MANIFEST_SCHEMA,
        f"python -m pipeline --region {region_id} --from buildings",
    )
    # 🔴 Presence, never truth. The value is the edges charged with a cut, and
    # `_account` only charges on LOD0 — so a tile met only on its coarser tier
    # writes an empty list, which a truth test reads as "never carved" and the
    # guard fails open into exactly the degradation it exists to prevent.
    if CARVED_EDGES_KEY in manifest:
        # 🔴 **Refused rather than repeated, because a second pass DEGRADES the
        # first.** The retaining wall is built on the prism's own side planes,
        # so a re-run classifies it as wholly inside the prism, removes it, and
        # rebuilds a shorter one from what is left — measured at `e327` 141.8 →
        # 75.8 m of wall on one repeat, with every counter still closing. That
        # is silent loss, so this is the one thing the stage will not do.
        # ⚠️ Reached by `--from carve` twice, and by `--from roads`, which is the
        # plausible one: the tiles on disk are already carved.
        raise ValueError(
            f"{BUILDINGS_MANIFEST_NAME} says its tiles are already carved. Carving them "
            f"again would eat the retaining wall and rebuild it shorter — rebuild the "
            f"tiles first: python -m pipeline --region {region_id} --from buildings"
        )

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    by_id = {edge["id"]: edge for edge in graph["edges"]}
    tiles = {tile["id"]: tile for tile in manifest["tiles"]}
    overhead = _structure_field(out_dir, manifest)

    plans: dict[str, list[EdgePlan]] = {}
    for edge_id in carved_edges:
        edge = by_id.get(edge_id)
        if edge is None:
            # 🔴 **Refused, never skipped.** An edge id is a per-region ordinal,
            # so skipping the ones a graph does not carry would let a list
            # written for one region cut prisms out of whatever the same
            # integers happen to name in another — 7 of `wan_chai`'s 8 resolve
            # in `mong_kok`, naming six roads including ARGYLE STREET and
            # WATERLOO ROAD. That is `Q54` inverted, and it renders as a
            # perfectly carved city.
            raise ValueError(
                f"carve names edge {edge_id} for region {region_id}, which is not in "
                f"{ROADGRAPH_NAME} — a list written for another region, or a stale id "
                f"after a source refresh?"
            )
        plan = _plan_edge(edge, spec, overhead)
        report.edges.append(plan.row)
        _register(plan, tiles, plans)

    # The parapet band (`P3-51`): the listed edges, and by rule whatever else
    # the block names, after the listed edges so their retaining walls are
    # built from what the carriageway prisms removed and the band's rows
    # follow theirs.
    if banded:
        for edge in graph["edges"]:
            band = _band_plans(edge, spec, overhead, carved_edges)
            if not band:
                continue
            report.edges.append(band[0].row)
            for plan in band:
                _register(plan, tiles, plans)

    for tile_id in sorted(plans):
        _carve_tile(out_dir, tiles[tile_id], plans[tile_id], report)

    _log(report)
    if report.tiles_written:
        manifest[CARVED_EDGES_KEY] = sorted(row.edge for row in report.carved)

    write_document(out_dir / BUILDINGS_MANIFEST_NAME, manifest)
    write_document(out_dir / CARVE_NAME, _document(city, region_id, report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    build_region(city, args.region)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
