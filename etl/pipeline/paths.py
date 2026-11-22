"""The pedestrian lines the topographic map draws (`P3-101`, `Q250`).

iB1000's `CartoPedLine` is the edge of everything a pedestrian walks on that is
not the road: the margin of a pavement, a plaza or a promenade, and the
centreline of a footpath through a park. The ground the tiles draw is one flat
colour between the roads, so these lines are the only published shape on it.
Each is laid as a thin ribbon `lift_m` over the shipped ground, in
`material`'s colour, cut into `cell_m` plan cells so the engine can cull it.

🔴 **Only where a line is surveyed, and only the line.** No area is filled
between two margins and nothing is drawn where the sheet is silent — the
trees' rule and the planters'.

⚠️ **Never on the drawn road, the sea or bare air.** A line is cut back to
`kerb_clear_m` outside the level-0 carriageway region, which is measured from
other sources than this layer and wins where the two disagree; cut out of the
basemap's sea, where a pier narrower than `basemap.seal_m` is water; and
dropped where the tiles draw no ground under it or the ground there is
steeper than `max_grade_pct` — a retaining wall or a cliff the terrain's 4 m
cell smears into a slope, which no path lies on.

⚠️ **A ribbon follows the ground between stations, not at every metre.** The
ground is read every `step_m` along a line and a station is kept wherever the
straight ribbon would leave it by more than `sag_m`, so flat reclamation costs
two triangles a segment. The centreline and both edges are read, so a ribbon
across a slope stays on it.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry

from pipeline import gdb
from pipeline.buildings import ground_of_bundle
from pipeline.config import Config, GameTransform, Paths, load_config
from pipeline.documents import write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.mesh import weld
from pipeline.meshbuild import MIN_TWICE_AREA_M2, Cell, ColouredBuilder, cell_name, cell_of
from pipeline.polyline import true_runs
from pipeline.surface_region import read as read_carriageway_region
from pipeline.trees import Faces, tile_corners

log = logging.getLogger(__name__)

PATHS_NAME = "paths.glb"
PATHS_MANIFEST_NAME = "paths.json"
PATHS_MANIFEST_SCHEMA = 1
PATHS_MESH_NAME = "paths"
# The glTF material the engine's importer dispatches on — `SHADERS` in
# `game/tools/generated_scene_import.gd` holds the other end.
PATHS_MATERIAL = "paths"

# A published line is thinned to this before it is drawn: under the ribbon's
# own width, and the source's curves are a vertex every half metre.
_SIMPLIFY_M = 0.05
# A mitre is no longer than this many half-widths, so a hairpin does not spike.
_MITRE_LIMIT = 2.0
_UP = np.array([0.0, 1.0, 0.0])

Line = tuple[str, shapely.LineString]


@dataclass
class PathReport:
    features: int = 0
    # Features by published code, drawn or not, so the selection is reviewable.
    by_code: dict[str, int] = field(default_factory=dict)
    read: int = 0
    read_m: float = 0.0
    # `read_m` in its disjoint parts: the five refusals, in metres of line,
    # and `drawn_m`.
    on_road_m: float = 0.0
    in_sea_m: float = 0.0
    no_ground_m: float = 0.0
    too_steep_m: float = 0.0
    too_short_m: float = 0.0
    drawn_m: float = 0.0
    drawn_m_by_code: dict[str, float] = field(default_factory=dict)
    ribbons: int = 0
    stations: int = 0
    stations_kept: int = 0
    cells: int = 0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0


def read_lines(
    city: Config,
    spec: Paths,
    region_id: str,
    transform: GameTransform,
    report: PathReport,
    *,
    sources_root: Path | None = None,
) -> list[Line]:
    """Each drawn code's lines in game plan, clipped to the region's rectangle."""
    far_x, far_z = city.region_high(region_id)
    frame = shapely.box(0.0, 0.0, far_x, far_z)
    bbox = city.projected_bounds(region_id).bbox
    lines: list[Line] = []
    # A line on a sheet boundary is published by both sheets.
    seen: set[bytes] = set()
    for path, member in source_reads(city, spec, region_id, root=sources_root):
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        report.features += len(layer)
        codes = layer.column(spec.layer.field("type"))
        owners, parts = gdb.polylines(layer)
        for owner, points in zip(owners, parts, strict=True):
            code = str(codes[owner])
            report.by_code[code] = report.by_code.get(code, 0) + 1
            if code not in spec.widths_m or len(points) < 2 or not np.isfinite(points).all():
                continue
            x, _, z = transform.to_game(points[:, 0], points[:, 1])
            plan = np.round(np.column_stack([x, z]), 3)
            key = plan.tobytes()
            if key in seen or plan[::-1].tobytes() in seen:
                continue
            seen.add(key)
            clipped = shapely.LineString(plan).intersection(frame)
            for piece in _lines(clipped):
                lines.append((code, piece))
                report.read += 1
                report.read_m += piece.length
    return lines


def _lines(shape: BaseGeometry) -> list[shapely.LineString]:
    if shape.geom_type == "LineString":
        return [] if shape.is_empty else [shape]
    return [part for inner in getattr(shape, "geoms", ()) for part in _lines(inner)]


def _height(ground: Faces, x: float, z: float) -> float:
    """The highest ground over a point, or NaN where the tiles draw none."""
    under = ground.heights(x, z)
    return float(under.max()) if len(under) else float("nan")


def _heights(ground: Faces, plan: np.ndarray) -> np.ndarray:
    return np.array([_height(ground, float(x), float(z)) for x, z in plan])


def _kept(along: np.ndarray, heights: np.ndarray, corners: np.ndarray, sag_m: float) -> np.ndarray:
    """Which stations a ribbon needs: every plan corner, and wherever the
    ground leaves the straight ribbon between two kept stations by `sag_m`.
    `heights` is a column a line read: the centreline and each edge."""
    keep = corners.copy()
    keep[[0, -1]] = True
    spans = list(pairwise(np.flatnonzero(keep)))
    while spans:
        first, last = spans.pop()
        if last - first < 2:
            continue
        inner = slice(first + 1, last)
        share = (along[inner] - along[first]) / (along[last] - along[first])
        chord = heights[first] + share[:, None] * (heights[last] - heights[first])
        off = np.abs(heights[inner] - chord).max(axis=1)
        worst = int(np.argmax(off))
        if off[worst] > sag_m:
            middle = first + 1 + worst
            keep[middle] = True
            spans += [(first, middle), (middle, last)]
    return keep


def _offsets(plan: np.ndarray, half_m: float) -> np.ndarray:
    """Each station's offset to the ribbon's left edge, mitred at a corner."""
    step = np.diff(plan, axis=0)
    step /= np.linalg.norm(step, axis=1, keepdims=True)
    normal = np.column_stack([-step[:, 1], step[:, 0]])
    before = np.vstack([normal[:1], normal])
    after = np.vstack([normal, normal[-1:]])
    mitre = before + after
    # A line that doubles straight back has no bisector: its own normal serves.
    length = np.linalg.norm(mitre, axis=1, keepdims=True)
    mitre = np.where(length > 1e-9, mitre / np.where(length > 1e-9, length, 1.0), before)
    cosine = np.clip((mitre * before).sum(axis=1), 1.0 / _MITRE_LIMIT, 1.0)
    return mitre * (half_m / cosine)[:, None]


class _Cells:
    """One `ColouredBuilder` a plan cell: `meshbuild.CellBuilder`'s rule, for a
    ribbon that is not flat."""

    def __init__(self, cell_m: float) -> None:
        self._cell_m = cell_m
        self._cells: dict[Cell, ColouredBuilder] = {}

    def quad(self, points: np.ndarray, colour: tuple[int, int, int]) -> None:
        """Two triangles, each wound to face up on its own: where a ribbon
        wider than its bend's radius folds, a quad is a bow-tie and one
        winding for both halves leaves one facing down, which `cull_back`
        draws as nothing."""
        cell = cell_of(*points[:, [0, 2]].mean(axis=0), self._cell_m)
        if cell not in self._cells:
            self._cells[cell] = ColouredBuilder(PATHS_MATERIAL)
        for corners in (points[[0, 1, 2]], points[[0, 2, 3]]):
            up = np.cross(corners[1] - corners[0], corners[2] - corners[0])[1]
            if abs(up) > MIN_TWICE_AREA_M2:
                self._cells[cell].polygon(corners if up > 0.0 else corners[::-1], _UP, colour)

    def build(self) -> list[MeshData]:
        meshes = []
        for cell in sorted(self._cells):
            mesh = self._cells[cell].build(cell_name(PATHS_MESH_NAME, cell))
            if mesh is not None:
                meshes.append(weld(mesh))
        return meshes


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> PathReport:
    """Read the region's published pedestrian lines and write `paths.glb`."""
    spec = city.paths
    report = PathReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no paths block; nothing to build", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    lines = read_lines(city, spec, region_id, transform, report, sources_root=sources_root)
    sea = ground_of_bundle(out_dir, region_id)[0] if city.basemap is not None else shapely.Polygon()
    meshes = build_paths(
        spec,
        lines,
        read_carriageway_region(out_dir, region_id).whole,
        sea,
        Faces(tile_corners(city, region_id, out_dir)[0]),
        report,
    )
    if meshes:
        report.bytes = write_glb(out_dir / PATHS_NAME, meshes)
    else:
        # Named from what was drawn: a stale mesh beside a manifest that says
        # "none" is what `sync_generated.sh` would ship.
        (out_dir / PATHS_NAME).unlink(missing_ok=True)
    _write_manifest(out_dir, city, region_id, report)
    return report


def build_paths(
    spec: Paths,
    lines: list[Line],
    carriageway: BaseGeometry,
    sea: BaseGeometry,
    ground: Faces,
    report: PathReport,
) -> list[MeshData]:
    """The ribbons, one mesh a plan cell, or nothing where no line was laid."""
    kept_clear = carriageway.buffer(spec.kerb_clear_m)
    cells = _Cells(spec.cell_m)
    colour = spec.material.colour
    for code, line in lines:
        off_road = line.difference(kept_clear)
        report.on_road_m += line.length - off_road.length
        dry = off_road.difference(sea)
        report.in_sea_m += off_road.length - dry.length
        for piece in _lines(dry):
            for plan, heights in _runs(spec, piece, ground, report):
                _lay(cells, spec, code, plan, heights, ground, colour, report)

    meshes = cells.build()
    report.cells = len(meshes)
    report.triangles = sum(len(mesh.triangles) for mesh in meshes)
    report.vertices = sum(len(mesh.positions) for mesh in meshes)
    return meshes


def _runs(
    spec: Paths, piece: shapely.LineString, ground: Faces, report: PathReport
) -> list[tuple[np.ndarray, np.ndarray]]:
    """`piece` in the stretches the tiles draw ground under: each one's plan
    stations, read every `step_m`, and the ground's height at them."""
    dense = shapely.segmentize(piece.simplify(_SIMPLIFY_M), spec.step_m)
    plan = np.asarray(dense.coords)[:, :2]
    plan = plan[np.concatenate([[True], np.linalg.norm(np.diff(plan, axis=0), axis=1) > 1e-6])]
    heights = _heights(ground, plan)
    grounded = np.isfinite(heights)
    spans = np.linalg.norm(np.diff(plan, axis=0), axis=1)
    on_ground = grounded[:-1] & grounded[1:]
    report.no_ground_m += max(0.0, piece.length - float(spans[on_ground].sum()))
    return [
        (plan[first : last + 1], heights[first : last + 1]) for first, last in true_runs(on_ground)
    ]


def _lay(
    cells: _Cells,
    spec: Paths,
    code: str,
    plan: np.ndarray,
    heights: np.ndarray,
    ground: Faces,
    colour: tuple[int, int, int],
    report: PathReport,
) -> None:
    """The ribbons along `plan`, a run's stations with the ground's `heights`
    at them: a quad between each two kept stations, broken wherever the ground
    under it is steeper than `max_grade_pct`."""
    width = spec.widths_m[code]
    # A station the segmentizing added lies on its neighbours' line.
    before, after = plan[1:-1] - plan[:-2], plan[2:] - plan[1:-1]
    turned = (np.abs(before[:, 0] * after[:, 1] - before[:, 1] * after[:, 0]) > 1e-9) | (
        (before * after).sum(axis=1) <= 0.0
    )
    corners = np.concatenate([[True], turned, [True]])
    spans = np.linalg.norm(np.diff(plan, axis=0), axis=1)
    along = np.concatenate([[0.0], np.cumsum(spans)])
    offsets = _offsets(plan, 0.5 * width)
    left, right = plan + offsets, plan - offsets
    # The centreline and each edge; an edge off the tiles' ground takes the
    # centreline's height.
    edges = [_heights(ground, edge) for edge in (left, right)]
    profile = np.column_stack(
        [heights, *(np.where(np.isfinite(found), found, heights) for found in edges)]
    )
    report.stations += len(plan)

    limit = spec.max_grade_pct / 100.0
    across = np.abs(profile[:, 1] - profile[:, 2]) <= limit * width
    walkable = (
        (np.abs(np.diff(profile, axis=0)).max(axis=1) <= limit * spans) & across[:-1] & across[1:]
    )
    report.too_steep_m += float(spans[~walkable].sum())
    for first, last in true_runs(walkable):
        length = float(along[last] - along[first])
        if length < spec.min_length_m:
            report.too_short_m += length
            continue
        part = slice(first, last + 1)
        kept = _kept(along[part], profile[part], corners[part], spec.sag_m)
        rows = first + np.flatnonzero(kept)
        report.stations_kept += len(rows)
        for near, far in pairwise(rows):
            quad = np.array(
                [
                    [left[near, 0], profile[near, 1], left[near, 1]],
                    [left[far, 0], profile[far, 1], left[far, 1]],
                    [right[far, 0], profile[far, 2], right[far, 1]],
                    [right[near, 0], profile[near, 2], right[near, 1]],
                ]
            )
            quad[:, 1] += spec.lift_m
            cells.quad(quad, colour)
        report.ribbons += 1
        report.drawn_m += length
        report.drawn_m_by_code[code] = report.drawn_m_by_code.get(code, 0.0) + length


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: PathReport) -> int:
    document = {
        "schema_version": PATHS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "asset": PATHS_NAME if report.triangles else None,
        "features": report.features,
        # Every code the layer publishes here, drawn or not.
        "by_code": dict(sorted(report.by_code.items())),
        "read": report.read,
        "read_m": round(report.read_m, 1),
        # `read_m` in parts: cut back off the drawn road, out of the sea, over
        # no ground, over ground too steep to lie on, too short to draw, and
        # drawn.
        "on_road_m": round(report.on_road_m, 1),
        "in_sea_m": round(report.in_sea_m, 1),
        "no_ground_m": round(report.no_ground_m, 1),
        "too_steep_m": round(report.too_steep_m, 1),
        "too_short_m": round(report.too_short_m, 1),
        "drawn_m": round(report.drawn_m, 1),
        "drawn_m_by_code": {
            code: round(metres, 1) for code, metres in sorted(report.drawn_m_by_code.items())
        },
        "ribbons": report.ribbons,
        # The ground was read at `stations` and a vertex pair kept at `stations_kept`.
        "stations": report.stations,
        "stations_kept": report.stations_kept,
        "cells": report.cells,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
    }
    return write_document(out_dir / PATHS_MANIFEST_NAME, document)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "paths: %.0f m read -> %.0f m drawn in %d ribbons (%.0f m on the road, %.0f m in the "
        "sea, %.0f m over no ground, %.0f m too steep), %d triangles in %d cells",
        report.read_m,
        report.drawn_m,
        report.ribbons,
        report.on_road_m,
        report.in_sea_m,
        report.no_ground_m,
        report.too_steep_m,
        report.triangles,
        report.cells,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
