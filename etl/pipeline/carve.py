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
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import numpy as np

from pipeline.buildings import (
    BUILDINGS_MANIFEST_NAME,
    BUILDINGS_MANIFEST_SCHEMA,
    CARVED_EDGES_KEY,
    FACADE_MATERIAL,
    Placement,
    union,
)
from pipeline.config import Carve, Config, SurfaceClass, load_config
from pipeline.documents import read_document, write_document
from pipeline.gltf import MeshData, normalise, read_glb, write_glb
from pipeline.mesh import merge, select_triangles, subtract_prism
from pipeline.polyline import plan_lengths
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import mitres
from pipeline.terrain import HeightField

log = logging.getLogger(__name__)

CARVE_NAME = "carve.json"
CARVE_SCHEMA = 1

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
    nearest = np.argmin(((centroids[:, None, [0, 2]] - plan[None, :, :]) ** 2).sum(axis=2), axis=1)
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
            uv2=None if removed.uv2 is None else np.tile(removed.uv2[0], (len(positions), 1)),
            material=source.material,
        ),
        metres,
    )


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
    """One edge's stations, prisms and the row they will be reported on."""

    row: EdgeCarve
    points: np.ndarray
    offsets: np.ndarray
    half_m: float
    floors: np.ndarray
    prisms: list[list[tuple[np.ndarray, float]]]

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
        mesh = read_glb(out_dir / tile["lods"][0]["path"])[0]
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
    )


def _tiles_for(plan: EdgePlan, tiles: dict) -> list[str]:
    """Tiles whose published AABB meets this edge's ribbon in plan."""
    low, high = plan.bounds()
    out = []
    for tile_id, tile in tiles.items():
        (ax, _ay, az), (bx, _by, bz) = tile["aabb"]
        if bx >= low[0] and ax <= high[0] and bz >= low[2] and az <= high[2]:
            out.append(tile_id)
    return sorted(out)


def _carve_tile(out_dir: Path, tile: dict, plans: list[EdgePlan], report: CarveReport) -> None:
    """Cut every plan out of one tile, both tiers, and re-emit the tiers it cut."""
    boxes: list = []
    rewritten = False
    for tier, lod in enumerate(tile["lods"]):
        path = out_dir / lod["path"]
        meshes = read_glb(path)
        if len(meshes) != 1:
            raise ValueError(f"{lod['path']} holds {len(meshes)} primitives, expected one")
        source = meshes[0]
        boxes.append(source.aabb())

        keep = _structure(source)
        if not keep.any():
            continue
        structure = select_triangles(source, keep)
        rest = select_triangles(source, ~keep)

        built: list[tuple[MeshData, EdgePlan]] = []
        removed_any = False
        for plan in plans:
            structure, cut, wall, metres = _carve_plan(structure, plan, source)
            if cut is None:
                continue
            removed_any = True
            if tier == 0:
                _account(plan.row, cut)
                plan.row.wall_m += metres
            if wall is not None:
                built.append((wall, plan))

        # A tier the prisms never met is left exactly as `buildings.py` wrote it
        # — not rewritten identically, but never opened for writing at all.
        if not removed_any:
            continue

        # 🔴 `built` keeps the inward-only wall; the mirror happens here so that
        # `_facing_away` below still grades a mesh whose every triangle should
        # face the road. See `_double_side`.
        walls = [_double_side(wall) for wall, _ in built]
        parts = [part for part in (rest, structure, *walls) if part is not None]
        if not parts:
            continue
        carved = merge(parts, name=source.name)
        # 🔴 `read_glb` does not read a primitive's material back, so a tile
        # re-emitted without this imports on the default `BaseMaterial3D` and the
        # window-band shader disappears from ten tiles, silently.
        carved = _named(carved, source.name, FACADE_MATERIAL)
        lod["bytes"] = write_glb(path, [carved])
        lod["triangles"] = carved.triangle_count
        lod["vertices"] = len(carved.positions)
        boxes[-1] = carved.aabb()
        rewritten = True
        report.tiles_written.append(lod["path"])
        report.facing_away += sum(_facing_away(wall, plan.points) for wall, plan in built)
        report.widest_tier_vertices = max(report.widest_tier_vertices, len(carved.positions))

    if rewritten:
        _retile_aabb(tile, boxes)


def _carve_plan(
    structure: MeshData | None, plan: EdgePlan, source: MeshData
) -> tuple[MeshData | None, MeshData | None, MeshData | None, float]:
    """One edge's prisms taken out of one tier: what is left, what was cut, its wall.

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
        return None, None, None, 0.0

    low, high = plan.bounds()
    corners = structure.positions[structure.triangles][:, :, [0, 2]]
    near = (corners.max(axis=1) >= low[[0, 2]]).all(axis=1) & (
        corners.min(axis=1) <= high[[0, 2]]
    ).all(axis=1)
    if not near.any():
        return structure, None, None, 0.0
    work = select_triangles(structure, near)
    aside = select_triangles(structure, ~near)

    taken: list[MeshData] = []
    volume = 0.0
    for prism in plan.prisms:
        if work is None:
            break
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

    left = [part for part in (aside, work) if part is not None]
    remaining = merge(left, name=structure.name) if len(left) > 1 else (left[0] if left else None)
    if not taken:
        return remaining, None, None, 0.0

    plan.row.carved_volume_m3 += volume
    cut = merge(taken, name="cut") if len(taken) > 1 else taken[0]
    wall, metres = _retaining_wall(cut, plan, source)
    return remaining, cut, wall, metres


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


def _named(mesh: MeshData, name: str, material: str) -> MeshData:
    """`merge` drops both, deliberately, so the caller renames what it merged.

    🔴 The name carries `COLLISION_SUFFIX` on LOD0, which is what gives the tile
    its trimesh collider. Reconstructing it from the tile id would lose the
    suffix on any tier that carries one, so it is taken from the mesh that was
    read.
    """
    return replace(mesh, name=name, material=material)


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
    log.info(
        "  carve: %d edges configured, %d cut, %d tiers re-emitted",
        len(report.edges),
        len(carved),
        len(report.tiles_written),
    )
    for row in report.edges:
        log.info(
            "    e%-4d %-24s w=%5.2f  %4d stations, %3d soffit-bounded  "
            "%6d tris, %8.1f m2, wall %6.1f m",
            row.edge,
            row.road_name[:24],
            row.width_m,
            row.stations,
            row.soffit_bounded,
            row.triangles_removed,
            row.carved_area_m2,
            row.wall_m,
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
    """Which triangles came from `INFRASTRUCTURE`, read off `TEXCOORD_0.y`."""
    if mesh.uvs is None:
        return np.zeros(len(mesh.triangles), dtype=bool)
    classes = np.floor(mesh.uvs[:, 1]).astype(int)
    return classes[mesh.triangles].min(axis=1) == int(SurfaceClass.STRUCTURE)


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> CarveReport:
    """Carve every configured edge out of the tiles it touches, and re-emit them.

    ⚠️ **Only the touched tiles are opened at all.** The untouched ones are not
    read, not rewritten and not compared — which is what makes them
    byte-identical, rather than a `cmp` afterwards saying they happen to be.
    """
    place = Placement.resolve(city, region_id, sources_root, out_root)
    report = CarveReport()
    spec = city.carve
    if spec is None:
        log.info("  no carve configured; the bundle is unchanged")
        write_document(place.out_dir / CARVE_NAME, _document(city, region_id, report))
        return report

    manifest = read_document(
        place.out_dir / BUILDINGS_MANIFEST_NAME,
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

    graph = read_graph(place.out_dir / ROADGRAPH_NAME, city.id, region_id)
    by_id = {edge["id"]: edge for edge in graph["edges"]}
    tiles = {tile["id"]: tile for tile in manifest["tiles"]}
    overhead = _structure_field(place.out_dir, manifest)

    plans: dict[str, list[EdgePlan]] = {}
    for edge_id in spec.edges:
        edge = by_id.get(edge_id)
        if edge is None:
            raise ValueError(
                f"carve names edge {edge_id}, which is not in {ROADGRAPH_NAME} — "
                "a stale id after a source refresh?"
            )
        plan = _plan_edge(edge, spec, overhead)
        report.edges.append(plan.row)
        for tile_id in _tiles_for(plan, tiles):
            plans.setdefault(tile_id, []).append(plan)
            plan.row.tiles_considered.append(tile_id)

    for tile_id in sorted(plans):
        _carve_tile(place.out_dir, tiles[tile_id], plans[tile_id], report)

    _log(report)
    if report.tiles_written:
        manifest[CARVED_EDGES_KEY] = sorted(row.edge for row in report.carved)

    write_document(place.out_dir / BUILDINGS_MANIFEST_NAME, manifest)
    write_document(place.out_dir / CARVE_NAME, _document(city, region_id, report))
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
