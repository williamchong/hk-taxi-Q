"""Published pedestrian-crossing stripes, drawn as their own mesh (`P3-35g2`).

`Q101` re-opened crossings with "five publishers where there were none", and
pricing them found that only one publishes crossing *paint*:
`DTAD_CROSSING_LINE` surveys **each stripe as its own rectangle**. The other
four are the look-right / look-left glyphs beside a crossing and three readings
of the footway's extent, and are not this stage's.

The shape is `boxjunctions.py`'s — a surveyed polygon drawn where it was
surveyed, never registered to the ribbon, each vertex at the drawn road's own
height through `DrawnSurface` — and `_place` is that stage's, imported rather
than restated. Three things are this layer's own:

- **A stripe is a FACE of the feature's lines, not a ring.** 715 of Wan Chai's
  parts are closed rings; 367 are loose edges, and 777 m of their 999 close into
  84 more rectangles. One rule covers both — polygonise each feature's lines —
  and what encloses nothing is refused and counted. ⚠️ That is only safe because
  the survey draws stripes and never a ladder: across both regions **no face
  touches another**, and the gap between neighbours is the sheet's own 0.6 m. A
  ladder's gaps would polygonise too and paint the crossing solid, so
  `faces_touching` is recorded and must be 0.
- **Two paints, and the crossing does not say which.** `config.ZebraEvidence`
  has the argument: a crossing TD's surveyed zigzags reach is a zebra and is
  white, every other striped crossing is a light-signal one and is yellow.
  `zigzag_gap_m` publishes both sides of the plateau that licenses the bar.
- **No dimension is authored.** Width, length and spacing are the survey's.

⚠️ **Nothing here invents a crossing**, and nothing here knows which junctions
are signalised — the signal layer is removed (`Q77`, `P3-35a`) and this stage
must not be the reason it comes back.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import shapely
from shapely.ops import polygonize

from pipeline import gdb
from pipeline.boxjunctions import _place
from pipeline.config import Config, Crossings, GameTransform, load_config
from pipeline.config_blocks.base import SourceLayer
from pipeline.documents import read_document, write_document
from pipeline.drawnsurface import DrawnSurface
from pipeline.fetch import source_reads
from pipeline.geometry import orient, twice_area, wound_up
from pipeline.gltf import MeshData, write_glb
from pipeline.meshbuild import CellBuilder, _Slivers, import_quantum_m
from pipeline.polyline import Segments, plan_lengths_2d
from pipeline.railings import AT_GRADE
from pipeline.region import _box_sides
from pipeline.report import tail_of
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, downward_facing

log = logging.getLogger(__name__)

CROSSINGS_NAME = "crossings.glb"
CROSSINGS_MANIFEST_NAME = "crossings.json"
# 2 since `P3-42` (`Q135`): `crossings.glb` is one mesh a kind a plan cell, no
# longer one a kind — `BOXJUNCTIONS_MANIFEST_SCHEMA` 2's reasoning. A mesh's
# name is `cell_name(kind, cell)`; its material is still the bare kind.
CROSSINGS_MANIFEST_SCHEMA = 2

# glTF material names, the contract channel `BOXJUNCTIONS_MATERIAL` is:
# `tools/generated_scene_import.gd` maps each onto its `.tres`. They are the
# mesh names too. ⚠️ **No `-col` suffix** — paint is not a collider.
SIGNAL, ZEBRA = "crossings_signal", "crossings_zebra"
KINDS = (SIGNAL, ZEBRA)

# The survey is in millimetres and two parts of one stripe meet at a corner they
# each wrote down: snapped to this before they are noded, or a rectangle drawn
# as four edges is four edges.
_NODE_M = 0.001


@dataclass
class CrossingReport:
    """What the stage read, closed and drew.

    The partitions, asserted where they are complete:

        features == refused_line_type + on_structure + empty_geometry + candidates
        candidates == drawn + too_far + no_face
        faces == stripes + too_wide + not_convex
        drawn == sum(drawn_by_kind)
    """

    features: int = 0
    parts: int = 0
    source_m: float = 0.0
    refused_line_type: int = 0
    # Metres by the publisher's own code, as `roadmarks.json` keeps them: a
    # whitelist that misses a casing drops half the layer and renders perfectly.
    refused_m_by_type: dict[str, float] = field(default_factory=dict)
    on_structure: int = 0
    empty_geometry: int = 0
    candidates: int = 0

    drawn: int = 0
    too_far: int = 0
    no_face: int = 0
    drawn_by_kind: dict[str, int] = field(default_factory=lambda: dict.fromkeys(KINDS, 0))
    stripes_by_kind: dict[str, int] = field(default_factory=lambda: dict.fromkeys(KINDS, 0))
    area_m2_by_kind: dict[str, float] = field(default_factory=lambda: dict.fromkeys(KINDS, 0.0))
    zebra_by_line_type: int = 0
    zebra_by_zigzag: int = 0

    faces: int = 0
    stripes: int = 0
    too_wide: int = 0
    not_convex: int = 0
    # 🔴 Must be 0: a face sharing an edge with its neighbour is a ladder's gap.
    faces_touching: int = 0
    # Line that encloses nothing: a give-way bar, a stub, an unclosed stripe.
    unclosed_m: float = 0.0
    stripe_width_m: list[float] = field(default_factory=list)
    stripe_length_m: list[float] = field(default_factory=list)

    # 🔴 Both sides of the plateau `zebra.within_m` sits on, over every
    # candidate: the furthest crossing called a zebra and the nearest that was
    # not. The two closing on each other is the rule failing; `None` is no
    # crossing on that side.
    zebra_reach_m: float | None = None
    signal_reach_m: float | None = None
    zigzags: int = 0

    nearest_edge_m: list[float] = field(default_factory=list)
    height_spread_m: list[float] = field(default_factory=list)

    # `boxjunctions._place`'s counters, and its three tripwires — see
    # `BoxJunctionReport` for what each can see.
    vertices_drawn: int = 0
    vertices_over_cap: int = 0
    over_cap_rise_m: list[float] = field(default_factory=list)
    vertices_over_void: int = 0
    void_reach_m: list[float] = field(default_factory=list)
    polygons_placed: int = 0
    polygons_split: int = 0
    pieces_placed: int = 0

    slivers_dropped: int = 0
    import_quantum_m: float = 0.0
    # ⚠️ Must be 0 — `marking_paint.gdshader` is `cull_back`.
    inverted: int = 0
    inverted_area_m2: float = 0.0
    triangles: int = 0
    vertices: int = 0
    # The meshes `crossings.glb` carries, one a kind a plan cell of `cell_m`
    # (`P3-42`), and the largest of them.
    cells: int = 0
    cell_triangles_max: int = 0
    bytes: int = 0

    measured = staticmethod(tail_of)


@dataclass(frozen=True)
class Crossing:
    """One published crossing: its lines in the game's `(x, z)` plan."""

    line_type: str
    lines: tuple[np.ndarray, ...]


def _plan(transform: GameTransform, points: np.ndarray) -> np.ndarray:
    x, _, z = transform.to_game(points[:, 0], points[:, 1])
    return np.column_stack([x, z])


def _read(
    city: Config,
    spec: Crossings,
    layer: SourceLayer,
    region_id: str,
    sources_root: Path | None,
) -> list[tuple[str, str, list[np.ndarray]]]:
    """Every feature of one layer as `(line type, level, parts)`, in source metres."""
    found: list[tuple[str, str, list[np.ndarray]]] = []
    for path, member in source_reads(city, spec, region_id, root=sources_root):
        read = gdb.read_layer(
            path,
            layer.layer,
            columns=layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = read.column(layer.field("line_type"))
        levels = read.column(layer.field("level"))
        owners, parts = gdb.polylines(read)
        by_feature: dict[int, list[np.ndarray]] = defaultdict(list)
        for owner, points in zip(owners, parts, strict=True):
            by_feature[int(owner)].append(np.asarray(points, dtype=np.float64)[:, :2])
        for owner in range(len(read.fids)):
            found.append(
                (
                    str(types[owner]).strip().upper(),
                    str(levels[owner]).strip().lower(),
                    by_feature.get(owner, []),
                )
            )
    return found


def read_crossings(
    city: Config,
    spec: Crossings,
    region_id: str,
    transform: GameTransform,
    report: CrossingReport,
    *,
    sources_root: Path | None = None,
) -> list[Crossing]:
    crossings: list[Crossing] = []
    for line_type, level, parts in _read(city, spec, spec.layer, region_id, sources_root):
        report.features += 1
        report.parts += len(parts)
        usable = [part for part in parts if len(part) >= 2 and np.isfinite(part).all()]
        length_m = float(sum(plan_lengths_2d(part)[-1] for part in usable))
        report.source_m += length_m
        if line_type not in spec.line_types:
            report.refused_line_type += 1
            report.refused_m_by_type[line_type] = (
                report.refused_m_by_type.get(line_type, 0.0) + length_m
            )
        elif level not in AT_GRADE:
            report.on_structure += 1
        elif not usable:
            report.empty_geometry += 1
        else:
            report.candidates += 1
            crossings.append(Crossing(line_type, tuple(_plan(transform, part) for part in usable)))
    return crossings


def read_zigzags(
    city: Config,
    spec: Crossings,
    region_id: str,
    transform: GameTransform,
    *,
    sources_root: Path | None = None,
) -> list[np.ndarray]:
    """TD's surveyed zigzags at grade — the furniture only a zebra has."""
    return [
        _plan(transform, part)
        for line_type, level, parts in _read(city, spec, spec.zebra.layer, region_id, sources_root)
        if line_type in spec.zebra.codes and level in AT_GRADE
        for part in parts
        if len(part) >= 2 and np.isfinite(part).all()
    ]


def faces_of(lines: tuple[np.ndarray, ...]) -> tuple[list[np.ndarray], float, int]:
    """The rings a crossing's lines enclose, the metres that enclose nothing, and
    how many faces touch another.

    A closed ring is its own face and four loose edges are one too, which is why
    rings are not special-cased. Each returned ring is open (no repeated vertex)
    and wound to face `+Y`.
    """
    noded = shapely.unary_union(
        [shapely.set_precision(shapely.LineString(line), _NODE_M) for line in lines]
    )
    faces = list(polygonize(noded))
    # The UNION of the boundaries, never their sum: a ladder's rung borders two
    # faces, and counted twice it hides a stub of the same length.
    enclosing_m = float(shapely.union_all([face.exterior for face in faces]).length)
    touching = sum(
        1
        for index, face in enumerate(faces)
        if any(face.distance(other) < _NODE_M for other in faces[index + 1 :])
    )
    rings = [wound_up(np.asarray(face.exterior.coords)[:-1]) for face in faces]
    return rings, max(float(noded.length) - enclosing_m, 0.0), touching


def _is_convex(ring: np.ndarray) -> bool:
    """`FlatBuilder`'s precondition, which it does not test."""
    turns = orient(np.roll(ring, 1, axis=0), ring, np.roll(ring, -1, axis=0))
    turns = turns[np.abs(turns) > 1e-9]
    return bool((turns > 0.0).all() or (turns < 0.0).all())


def _sides_m(ring: np.ndarray) -> tuple[float, float]:
    """A stripe's width and length: its tightest rectangle's two sides, by
    `region._box_sides` — which says why it is not `minimum_rotated_rectangle`."""
    return _box_sides(shapely.Polygon(ring)) or (0.0, 0.0)


def draw(
    spec: Crossings,
    crossings: list[Crossing],
    zigzags: list[np.ndarray],
    segments: Segments,
    drawn: DrawnSurface,
    report: CrossingReport,
) -> tuple[dict[str, CellBuilder], float]:
    """Every crossing's stripes onto the drawn road, one builder per paint.

    Apart from `build_region` so it can be driven without a geodatabase: what
    it is handed is what the two readers return.
    """
    furniture = shapely.MultiLineString(zigzags) if zigzags else None
    builders = {kind: CellBuilder(kind, spec.cell_m) for kind in KINDS}
    every = [line for crossing in crossings for line in crossing.lines]
    report.import_quantum_m = round(import_quantum_m(np.vstack(every)), 6) if every else 0.0
    thinness_bar_m = 2.0 * report.import_quantum_m

    for crossing in crossings:
        rings, unclosed_m, touching = faces_of(crossing.lines)
        report.unclosed_m += unclosed_m
        report.faces += len(rings)
        report.faces_touching += touching

        outline = shapely.MultiLineString(crossing.lines)
        reach_m = float(outline.distance(furniture)) if furniture is not None else np.inf
        by_type = crossing.line_type in spec.zebra.line_types
        is_zebra = by_type or reach_m <= spec.zebra.within_m
        # Recorded for every candidate, before any refusal (`Q58`).
        if is_zebra and not by_type:
            furthest = report.zebra_reach_m
            report.zebra_reach_m = reach_m if furthest is None else max(furthest, reach_m)
        elif not is_zebra and np.isfinite(reach_m):
            nearest = report.signal_reach_m
            report.signal_reach_m = reach_m if nearest is None else min(nearest, reach_m)

        centre = outline.centroid
        snap = segments.nearest(float(centre.x), float(centre.y))
        report.nearest_edge_m.append(snap.distance_m)

        stripes: list[np.ndarray] = []
        for ring in rings:
            width_m, length_m = _sides_m(ring)
            if width_m > spec.max_stripe_width_m:
                report.too_wide += 1
            elif not _is_convex(ring):
                report.not_convex += 1
            else:
                report.stripes += 1
                report.stripe_width_m.append(width_m)
                report.stripe_length_m.append(length_m)
                stripes.append(ring)

        if snap.distance_m > spec.max_offset_m:
            report.too_far += 1
            continue
        if not stripes:
            report.no_face += 1
            continue

        kind = ZEBRA if is_zebra else SIGNAL
        heights: list[float] = []
        for ring in stripes:
            heights.extend(_place(builders[kind], drawn, ring, spec.lift_m, report, thinness_bar_m))
            # Positive as it stands: `faces_of` wound every ring to face `+Y`.
            report.area_m2_by_kind[kind] += 0.5 * twice_area(ring)
        report.drawn += 1
        report.drawn_by_kind[kind] += 1
        report.stripes_by_kind[kind] += len(stripes)
        report.zebra_by_line_type += int(is_zebra and by_type)
        report.zebra_by_zigzag += int(is_zebra and not by_type)
        if heights:
            report.height_spread_m.append(max(heights) - min(heights))

    assert len(crossings) == report.drawn + report.too_far + report.no_face
    assert report.faces == report.stripes + report.too_wide + report.not_convex
    return builders, thinness_bar_m


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> CrossingReport:
    """Read the region's published crossings and write its `crossings.glb`."""
    spec = city.crossings
    report = CrossingReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        log.info("city '%s' declares no crossings block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    crossings = read_crossings(city, spec, region_id, transform, report, sources_root=sources_root)
    zigzags = read_zigzags(city, spec, region_id, transform, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, the restriction every snap in the pipeline makes (`Q15`).
    segments = Segments.of([edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0])
    drawn = DrawnSurface.of(
        read_document(
            out_dir / SURFACE_MANIFEST_NAME,
            SURFACE_MANIFEST_SCHEMA,
            f"python -m pipeline.surface --region {region_id}",
        ),
        level=0,
    )

    report.zigzags = len(zigzags)
    builders, thinness_bar_m = draw(spec, crossings, zigzags, segments, drawn, report)
    assert report.candidates == len(crossings)
    assert report.features == (
        report.refused_line_type + report.on_structure + report.empty_geometry + report.candidates
    )

    meshes = cell_meshes(builders, thinness_bar_m, report)
    if meshes:
        report.bytes = write_glb(out_dir / CROSSINGS_NAME, meshes)

    _write_manifest(out_dir, city, region_id, report)
    return report


def cell_meshes(
    builders: dict[str, CellBuilder], thin_m: float, report: CrossingReport
) -> list[MeshData]:
    """What `crossings.glb` carries: a mesh a kind a plan cell, so the engine can
    cull the layer (`P3-42`, `Q135`), with the report's mesh half summed over them.

    🔴 **Each kind's slivers are built into a report of its own and summed**:
    `CellBuilder.build` ASSIGNS `slivers_dropped`, as `FlatBuilder.build` does,
    so handed the stage's report the second kind overwrites the first's.
    """
    meshes = []
    for kind in KINDS:
        slivers = _Slivers()
        cells = builders[kind].build(kind, thin_m, slivers)
        report.slivers_dropped += slivers.slivers_dropped
        for cell in sorted(cells):
            mesh = cells[cell]
            inverted, inverted_m2 = downward_facing(mesh)
            report.inverted += inverted
            report.inverted_area_m2 += inverted_m2
            report.triangles += mesh.triangle_count
            report.vertices += len(mesh.positions)
            meshes.append(mesh)
    if meshes:
        report.cells = len(meshes)
        report.cell_triangles_max = max(mesh.triangle_count for mesh in meshes)
    return meshes


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: CrossingReport) -> int:
    def rounded(values: dict[str, float]) -> dict[str, float]:
        return {key: round(value, 2) for key, value in sorted(values.items())}

    def reach(value: float | None) -> float | None:
        return None if value is None else round(value, 2)

    document = {
        "schema_version": CROSSINGS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, as `boxjunctions.json`'s is.
        "asset": CROSSINGS_NAME if report.triangles else None,
        # The read, as four disjoint parts of `features`.
        "features": report.features,
        "parts": report.parts,
        "source_m": round(report.source_m, 2),
        "refused_line_type": report.refused_line_type,
        "refused_m_by_type": rounded(report.refused_m_by_type),
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "candidates": report.candidates,
        # The join, as three disjoint parts of `candidates`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        "no_face": report.no_face,
        "drawn_by_kind": report.drawn_by_kind,
        "stripes_by_kind": report.stripes_by_kind,
        "area_m2_by_kind": rounded(report.area_m2_by_kind),
        # 🔴 The colour rule's own evidence — see `CrossingReport`.
        "zigzags": report.zigzags,
        "zebra_by_line_type": report.zebra_by_line_type,
        "zebra_by_zigzag": report.zebra_by_zigzag,
        "zigzag_gap_m": {
            "zebra_reach": reach(report.zebra_reach_m),
            "signal_reach": reach(report.signal_reach_m),
        },
        # The closing, as three disjoint parts of `faces`.
        "faces": report.faces,
        "stripes": report.stripes,
        "too_wide": report.too_wide,
        "not_convex": report.not_convex,
        # 🔴 Must be 0 — a ladder's gaps polygonise too.
        "faces_touching": report.faces_touching,
        "unclosed_m": round(report.unclosed_m, 2),
        "stripe_width_m": report.measured(report.stripe_width_m),
        "stripe_length_m": report.measured(report.stripe_length_m),
        "nearest_edge_m": report.measured(report.nearest_edge_m),
        "height_spread_m": report.measured(report.height_spread_m),
        "vertices_drawn": report.vertices_drawn,
        "vertices_over_cap": report.vertices_over_cap,
        "over_cap_rise_m": report.measured(report.over_cap_rise_m),
        "vertices_over_void": report.vertices_over_void,
        "void_reach_m": report.measured(report.void_reach_m),
        "polygons_placed": report.polygons_placed,
        "polygons_split": report.polygons_split,
        "pieces_placed": report.pieces_placed,
        "slivers_dropped": report.slivers_dropped,
        "import_quantum_m": report.import_quantum_m,
        "inverted": report.inverted,
        "inverted_area_m2": round(report.inverted_area_m2, 4),
        "triangles": report.triangles,
        "vertices": report.vertices,
        "cells": report.cells,
        "cell_triangles_max": report.cell_triangles_max,
        "bytes": report.bytes,
    }
    return write_document(out_dir / CROSSINGS_MANIFEST_NAME, document)


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
        "crossings: %d features -> %d drawn (%d light-signal, %d zebra; %d too far, "
        "%d enclosing nothing), %d stripes, %d triangles",
        report.features,
        report.drawn,
        report.drawn_by_kind[SIGNAL],
        report.drawn_by_kind[ZEBRA],
        report.too_far,
        report.no_face,
        report.stripes,
        report.triangles,
    )
    log.info(
        "  %d faces: %d too wide to be a stripe, %d not convex, %d touching a neighbour "
        "(must be 0); %.0f m of line encloses nothing; refused by line type: %s",
        report.faces,
        report.too_wide,
        report.not_convex,
        report.faces_touching,
        report.unclosed_m,
        {key: round(value) for key, value in sorted(report.refused_m_by_type.items())} or "none",
    )
    log.info(
        "  zebra evidence: %d zigzags; furthest zebra %s m, nearest light-signal crossing %s m",
        report.zigzags,
        report.zebra_reach_m if report.zebra_reach_m is None else round(report.zebra_reach_m, 1),
        report.signal_reach_m if report.signal_reach_m is None else round(report.signal_reach_m, 1),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
