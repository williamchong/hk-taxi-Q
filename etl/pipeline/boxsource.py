"""The published yellow boxes, read once for two stages (`P3-32`).

`boxjunctions.py` draws them; `surface.py` reads them as a witness that the
ground under the paint is carriageway (`Q104`: a box cannot be painted on a
pavement) and widens the drawn surface to the paint. The box stage imports the
surface stage for `DrawnSurface`, so the reader lives here rather than there.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from pipeline import gdb
from pipeline.config import BoxJunctions, Config, GameTransform
from pipeline.fetch import source_reads
from pipeline.polyline import game_heading_deg

# What `ELEVATION` says when a feature is at grade — the same column, on the
# same geodatabase, that `arrows.py` reads, and the same reading: the column is
# a structure identifier (`A01`, `A03`) and null is the ground. 19 of the
# region's 20 boxes are null and one is the empty string.
#
# ⚠️ Not config, for `arrows._AT_GRADE`'s stated reason: it is the source's own
# encoding of "no structure", not a threshold anyone may tune.
_AT_GRADE = ("", "none", "null", "<na>")


class BoxCounters(Protocol):
    """What `read_boxes` books: the publisher's own refusals (`Q58`)."""

    boxes: int
    not_a_yellow_box: int
    on_structure: int
    holes_refused: int
    empty_geometry: int
    candidates: int


@dataclass
class BoxReading:
    """`BoxCounters` for a reader with no report of its own."""

    boxes: int = 0
    not_a_yellow_box: int = 0
    on_structure: int = 0
    holes_refused: int = 0
    empty_geometry: int = 0
    candidates: int = 0


@dataclass(frozen=True)
class Box:
    """One published box junction, in game plan space."""

    # The outer ring, `(n, 2)` as `(x, z)`, open (no repeated closing vertex).
    ring: np.ndarray
    # The published hatch direction as a game heading, or None where the
    # publisher left `ANGLE1` null — 16 of the region's 20.
    hatch_deg: float | None


def read_boxes(
    city: Config,
    spec: BoxJunctions,
    region_id: str,
    transform: GameTransform,
    report: BoxCounters,
    *,
    sources_root: Path | None,
) -> list[Box]:
    """Every published box junction in the region, in game plan space.

    Everything refused here is refused on what the *publisher* says — a type
    outside `box_types`, a feature on a structure, an empty ring — and each
    refusal is counted rather than logged (`Q58`).
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    boxes: list[Box] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        types = layer.column(spec.layer.field("type"))
        levels = layer.column(spec.layer.field("level"))
        hatch_a = layer.column(spec.layer.field("hatch_a"))
        owners, parts = gdb.polygons(layer)

        for owner, rings in zip(owners, parts, strict=True):
            report.boxes += 1
            if str(types[owner]) not in spec.box_types:
                report.not_a_yellow_box += 1
                continue
            if str(levels[owner]).strip().lower() not in _AT_GRADE:
                # On a flyover deck. `Q13` keeps the elevated network closed to
                # driving, and the nearest level-0 edge to a box on a deck is
                # the street underneath it.
                report.on_structure += 1
                continue
            # Inner rings are holes. Counted, not drawn around: the region
            # publishes none, so a repair for them would be untestable code
            # guarding a shape the source does not contain.
            report.holes_refused += len(rings) - 1
            ring = _open_ring(rings[0])
            if ring is None:
                report.empty_geometry += 1
                continue
            game_x, _, game_z = transform.to_game(ring[:, 0], ring[:, 1])
            report.candidates += 1

            angle = hatch_a[owner]
            hatch_deg: float | None = None
            if angle is not None and math.isfinite(float(angle)):
                # `ANGLE1` is a mathematical angle, converted exactly as
                # `arrows.Symbol.heading_deg` converts `ANGLE` — same
                # geodatabase, same convention, and `hatch_angle_residual_deg`
                # is what holds it: a wrong reading here shows up as a large
                # residual against the derived axis on every published pair.
                hatch_deg = game_heading_deg(float(angle))
            boxes.append(Box(ring=np.column_stack([game_x, game_z]), hatch_deg=hatch_deg))
    return boxes


def _open_ring(ring: np.ndarray) -> np.ndarray | None:
    """The ring without its closing vertex, or None if nothing is left to draw."""
    points = np.asarray(ring, dtype=np.float64)
    if len(points) and np.array_equal(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3 or not np.isfinite(points).all():
        return None
    return points
