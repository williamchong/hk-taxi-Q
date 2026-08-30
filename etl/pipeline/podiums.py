"""iB1000 blocks stitched across sheet cuts and joined to the shipped meshes
(`Q47`'s second half, `P3-7a`).

Where a shipped building overlaps a surveyed podium (`P`) block, that block's
roof level is the façade boundary — metres from data, the top of `Q47`'s
`data > survey-inferred` precedence. This stage writes the join's result to
`podiums.json`: per building stem, the boundary in metres above the mesh's own
base (the frame `TEXCOORD_0.x` ships), and the mechanism that won it. The
document is a stage intermediate like `buildings.json` — `export.py` never
names it, nothing in the game reads it, and the contract argument for both
lives under `Q47` in `docs/DECISIONS.md`. Its consumers are `R4`'s pack and
grading, which is also why every row records provenance: grading floors→metres
only makes sense against rows whose metres came from data.

Two geometric facts about the source shape everything here:

- **A sheet cut clips a block**, leaving one piece per sheet with identical
  attributes, abutting exactly on the cut line. Identity across the cut is
  attributes plus contact (`stitch`), not geometry equality — and grouping is
  all that is needed, because levels come from attributes and the join tests
  every piece, so the unioned footprint is never computed. That keeps the
  stage inside the no-polygon-booleans line `geometry.py` draws.
- **The two datasets share a lineage but not a survey pass** — footprints
  register to ~0.1 m where a block and a mesh correspond 1:1, so a mesh vertex
  can sit a few centimetres inside the *neighbour's* block at a shared wall.
  Membership therefore demands depth (`_DEPTH_M`), not mere incidence: a
  genuine tower-over-podium overlap penetrates metres, misregistration does
  not.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.buildings import Placement, podium_blocks, read_sheet, stem
from pipeline.config import CityConfig, PodiumBlocks, SurfaceClass, load_config
from pipeline.documents import write_document
from pipeline.geometry import (
    edge_distances,
    gap_between,
    inside_rings,
    orient,
    points_in_triangles,
    rings_overlap,
)

log = logging.getLogger(__name__)

PODIUMS_NAME = "podiums.json"
PODIUMS_SCHEMA = 1

# Stitch contact tolerance. The clips abut *exactly* — the probe measured
# shared cut coordinates to the last decimal — so this is slack for float
# noise, not tolerance engineering.
_ABUT_M = 0.01

# Tower↔block contact tolerance: iB1000 draws a tower flush against its podium
# block, so exact-boundary contact must count, and `rings_overlap` leaves
# exact contact unspecified at zero.
_TOUCH_M = 0.01

# How deep a point must sit inside the other dataset's footprint before the
# join believes the overlap. The two products register to ~0.1 m where they
# correspond 1:1 (`DATA_SOURCES.md`), so anything shallower than this is
# indistinguishable from a shared wall drawn twice.
_DEPTH_M = 0.3

# A `P` roof this close to the mesh's own base or top bounds no band: at the
# top it is the podium's own 1:1 mesh (the boundary is the whole building),
# at the base there is nothing under it to treat differently.
_WINDOW_M = 1.0


@dataclass(frozen=True)
class Block:
    """One source feature: a building block as one sheet holds it."""

    sheet: str
    fid: int
    kind: str  # the publisher's domain code, compared via `PodiumBlocks.code`
    base: float  # mPD
    roof: float  # mPD
    certain: bool
    parts: tuple[tuple[np.ndarray, ...], ...]  # parts → rings, outer first

    @cached_property
    def aabb(self) -> tuple[float, float, float, float]:
        outers = [rings[0] for rings in self.parts]
        low = np.min([ring.min(axis=0) for ring in outers], axis=0)
        high = np.max([ring.max(axis=0) for ring in outers], axis=0)
        return (low[0], low[1], high[0], high[1])


@dataclass(frozen=True)
class LogicalBlock:
    """One block as the survey meant it: every clipped piece, one identity.

    `stitch` groups on exactly equal attributes, so every piece agrees on kind
    and levels — the properties read the first piece rather than store copies
    the type would let disagree. `certain` is the one genuine aggregate.
    """

    certain: bool
    pieces: tuple[Block, ...]

    @property
    def kind(self) -> str:
        return self.pieces[0].kind

    @property
    def base(self) -> float:
        return self.pieces[0].base

    @property
    def roof(self) -> float:
        return self.pieces[0].roof

    @property
    def refs(self) -> list[str]:
        return [f"{piece.sheet}:{piece.fid}" for piece in self.pieces]

    @cached_property
    def aabb(self) -> tuple[float, float, float, float]:
        boxes = np.array([piece.aabb for piece in self.pieces])
        return (
            float(boxes[:, 0].min()),
            float(boxes[:, 1].min()),
            float(boxes[:, 2].max()),
            float(boxes[:, 3].max()),
        )

    def rings(self):
        """Every part's rings, across every piece — the join tests them all."""
        for piece in self.pieces:
            yield from piece.parts


@dataclass(frozen=True)
class Footprint:
    """One shipped building, plan-projected in the source frame.

    The sheets are `(easting, elevation, -northing)` on Godot's axes
    (`buildings.game_offset`), so plan is `(x, -z)` and Y is mPD directly —
    the join never leaves the source frame.
    """

    plan: np.ndarray  # (n, 2) easting/northing
    triangles: np.ndarray  # (m, 3, 2) plan corners
    base_mpd: float
    top_mpd: float


def blocks_from(sheet: str, layer: gdb.Layer, spec: PodiumBlocks) -> list[Block]:
    """One sheet's layer decoded to `Block`s, attributes resolved by role."""
    owners, parts = gdb.polygons(layer)
    kinds = layer.column(spec.blocks.field("block_type")).astype(str)
    base = np.asarray(layer.column(spec.blocks.field("base_level")), dtype=np.float64)
    roof = np.asarray(layer.column(spec.blocks.field("roof_level")), dtype=np.float64)
    # An integer flag, not a domain: the data dictionary defines CERTAINTY as
    # certain/not, and nonzero is the only reading that needs no mapping.
    certain = np.asarray(layer.column(spec.blocks.field("certainty")), dtype=np.int64) != 0
    per_row: dict[int, list[tuple[np.ndarray, ...]]] = defaultdict(list)
    for owner, rings in zip(owners.tolist(), parts, strict=True):
        per_row[owner].append(tuple(rings))
    return [
        Block(
            sheet=sheet,
            fid=int(layer.fids[row]),
            kind=str(kinds[row]),
            base=float(base[row]),
            roof=float(roof[row]),
            certain=bool(certain[row]),
            parts=tuple(rows),
        )
        for row, rows in sorted(per_row.items())
    ]


def decode_blocks(
    city: CityConfig, region_id: str, *, sources_root: Path | None = None
) -> list[Block]:
    """Every block the region's sheets hold, still one record per clip."""
    spec = city.podiums
    assert spec is not None  # `build_podiums` guards; direct callers must too
    return [
        block
        for sheet, layer in podium_blocks(city, region_id, sources_root=sources_root)
        for block in blocks_from(sheet, layer, spec)
    ]


def _touching(a: Block, b: Block, abut_m: float) -> bool:
    for rings_a in a.parts:
        for rings_b in b.parts:
            if (
                gap_between(rings_a[0], rings_b[0]) <= abut_m
                or gap_between(rings_b[0], rings_a[0]) <= abut_m
            ):
                return True
    return False


def _near(box: tuple[float, float, float, float], boxes: np.ndarray, tol: float) -> np.ndarray:
    """Which of `boxes` come within `tol` of `box` — the broad phase every
    geometric pass runs before it pays for a polygon test."""
    x0, z0, x1, z1 = box
    near = (x0 <= boxes[:, 2] + tol) & (boxes[:, 0] <= x1 + tol)
    return near & (z0 <= boxes[:, 3] + tol) & (boxes[:, 1] <= z1 + tol)


def stitch(blocks: list[Block], *, abut_m: float = _ABUT_M) -> list[LogicalBlock]:
    """Group clipped pieces back into the blocks the survey meant.

    Two pieces are one block when they live in *different* sheets, carry
    exactly equal attributes — the clips duplicate them bit-for-bit — and
    touch along the cut. Same-sheet neighbours never group: within a sheet the
    survey already drew the block it meant. Two genuinely distinct same-level
    blocks abutting exactly at a cut would merge, and harmlessly: they agree
    on every value a consumer can ask for.
    """
    parent = list(range(len(blocks)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_attrs: dict[tuple[str, float, float], list[int]] = defaultdict(list)
    for index, block in enumerate(blocks):
        by_attrs[(block.kind, block.base, block.roof)].append(index)

    boxes = [block.aabb for block in blocks]
    for group in by_attrs.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if blocks[a].sheet == blocks[b].sheet:
                    continue
                ax0, az0, ax1, az1 = boxes[a]
                bx0, bz0, bx1, bz1 = boxes[b]
                if ax0 > bx1 + abut_m or bx0 > ax1 + abut_m:
                    continue
                if az0 > bz1 + abut_m or bz0 > az1 + abut_m:
                    continue
                if _touching(blocks[a], blocks[b], abut_m):
                    parent[find(a)] = find(b)

    members: dict[int, list[int]] = defaultdict(list)
    for index in range(len(blocks)):
        members[find(index)].append(index)

    def order(i: int) -> tuple[str, int]:
        return (blocks[i].sheet, blocks[i].fid)

    logical = [
        LogicalBlock(
            certain=all(blocks[i].certain for i in group),
            pieces=tuple(blocks[i] for i in sorted(group, key=order)),
        )
        for group in members.values()
    ]
    return sorted(logical, key=lambda b: (b.pieces[0].sheet, b.pieces[0].fid))


def tower_podium_pairs(
    stitched: list[LogicalBlock], spec: PodiumBlocks, *, touch_m: float = _TOUCH_M
) -> list[tuple[int, int]]:
    """Which logical towers meet which logical podium blocks, by geometry.

    True polygon overlap with a contact tolerance — not the bounding-box frame
    `Q47`'s probe counted, which the acceptance test reproduces separately.
    These pairs are the record's evidence numbers (exact level meets) and the
    frame `R4`'s validation set is defined in.
    """
    tower, podium = spec.code("tower"), spec.code("podium")
    towers = [i for i, block in enumerate(stitched) if block.kind == tower]
    podiums = [i for i, block in enumerate(stitched) if block.kind == podium]
    if not towers or not podiums:
        return []
    podium_boxes = np.array([stitched[i].aabb for i in podiums])
    pairs = []
    for t in towers:
        near = _near(stitched[t].aabb, podium_boxes, touch_m)
        for p in (podiums[i] for i in np.flatnonzero(near)):
            if any(
                rings_overlap(list(ra), list(rb), touch_m=touch_m)
                for ra in stitched[t].rings()
                for rb in stitched[p].rings()
            ):
                pairs.append((t, p))
    return pairs


def mesh_footprints(
    city: CityConfig, region_id: str, *, sources_root: Path | None = None
) -> dict[str, Footprint]:
    """Every shipped building's plan cloud, keyed by its cross-dataset stem.

    Only façade classes: the ground has no podium and a structure class is a
    viaduct, and the palette already knows which is which (`surface_class`,
    hard rule 3). A stem read from two sheets accumulates both copies — the
    duplicated geometry changes nothing the join measures.
    """
    style = city.buildings
    classes = tuple(
        class_id
        for class_id in style.classes
        if style.surface_class(class_id) == SurfaceClass.FACADE
    )
    bounds = city.projected_bounds(region_id).bbox
    place = Placement.resolve(city, region_id, sources_root, None)

    plans: dict[str, list[np.ndarray]] = defaultdict(list)
    corners: dict[str, list[np.ndarray]] = defaultdict(list)
    lows: dict[str, float] = {}
    highs: dict[str, float] = {}
    for _, sheet_path in place.sheets:
        for _, mesh in read_sheet(sheet_path, classes):
            plan = np.column_stack([mesh.positions[:, 0], -mesh.positions[:, 2]])
            low, high = plan.min(axis=0), plan.max(axis=0)
            if (
                low[0] > bounds[2]
                or low[1] > bounds[3]
                or high[0] < bounds[0]
                or high[1] < bounds[1]
            ):
                continue
            key = stem(mesh.name)
            plans[key].append(plan)
            corners[key].append(plan[mesh.triangles])
            lows[key] = min(lows.get(key, np.inf), float(mesh.positions[:, 1].min()))
            highs[key] = max(highs.get(key, -np.inf), float(mesh.positions[:, 1].max()))

    footprints = {}
    for key in sorted(plans):
        triangles = np.vstack(corners[key])
        # Flat-shaded extrusions duplicate every vertex per face and project
        # every wall triangle to zero plan area. Neither can pass the join's
        # strict-interior tests, so both are dropped once here rather than
        # re-tested against every candidate block.
        area = orient(triangles[:, 0], triangles[:, 1], triangles[:, 2])
        footprints[key] = Footprint(
            plan=np.unique(np.vstack(plans[key]), axis=0),
            triangles=triangles[area != 0.0],
            base_mpd=lows[key],
            top_mpd=highs[key],
        )
    return footprints


def _inward(ring: np.ndarray, depth: float) -> np.ndarray:
    """Ring vertices nudged toward the ring's centroid by `depth` metres.

    A cheap stand-in for interior sampling: a vertex moved inward that still
    lands inside the other footprint proves overlap deeper than survey noise.
    Approximate for strongly concave rings, which is acceptable — the other
    direction of the membership test does not depend on it.
    """
    centroid = ring.mean(axis=0)
    vectors = centroid - ring
    lengths = np.sqrt((vectors**2).sum(axis=1, keepdims=True))
    lengths[lengths == 0.0] = 1.0
    return ring + vectors / lengths * np.minimum(depth, lengths / 2.0)


def _covers(footprint: Footprint, block: LogicalBlock, depth_m: float) -> bool:
    for piece in block.pieces:
        for rings in piece.parts:
            inside = inside_rings(footprint.plan, list(rings))
            if inside.any() and edge_distances(footprint.plan[inside], rings[0]).max() >= depth_m:
                return True
            if points_in_triangles(_inward(rings[0], depth_m), footprint.triangles).any():
                return True
    return False


def join(
    stitched: list[LogicalBlock],
    footprints: dict[str, Footprint],
    spec: PodiumBlocks,
    *,
    depth_m: float = _DEPTH_M,
) -> dict[str, list[int]]:
    """Which logical podium blocks each shipped building stands over.

    Spatial by necessity — iB1000 carries no id the mesh stems know. One stem
    legitimately joining a podium block *and* being a tower is the common
    case: 3D-BIT merges tower and podium into one mesh where iB1000 splits
    blocks, which is added information, not misregistration.
    """
    podium = spec.code("podium")
    podiums = [i for i, block in enumerate(stitched) if block.kind == podium]
    if not podiums:
        return {}
    boxes = np.array([stitched[i].aabb for i in podiums])

    joined: dict[str, list[int]] = {}
    for key, footprint in footprints.items():
        low, high = footprint.plan.min(axis=0), footprint.plan.max(axis=0)
        near = _near((low[0], low[1], high[0], high[1]), boxes, 0.0)
        matches = [
            podiums[i]
            for i in np.flatnonzero(near)
            if _covers(footprint, stitched[podiums[i]], depth_m)
        ]
        if matches:
            joined[key] = matches
    return joined


def build_podiums(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> dict | None:
    """Stitch, join, and write `podiums.json`. `None` when the city has no
    `podiums:` block — a valid city, building the survey-and-hash-driven
    boundary it always built."""
    spec = city.podiums
    if spec is None:
        return None

    blocks = decode_blocks(city, region_id, sources_root=sources_root)
    stitched = stitch(blocks)
    pairs = tower_podium_pairs(stitched, spec)
    footprints = mesh_footprints(city, region_id, sources_root=sources_root)
    joined = join(stitched, footprints, spec)

    document = _document(city, region_id, blocks, stitched, pairs, footprints, joined)
    out_dir = city.out_dir(region_id, out_root)
    size = write_document(out_dir / PODIUMS_NAME, document)
    log.info(
        "  %s: %d buildings with a data boundary, %d bytes",
        PODIUMS_NAME,
        len(document["buildings"]),
        size,
    )
    return document


def _document(
    city: CityConfig,
    region_id: str,
    blocks: list[Block],
    stitched: list[LogicalBlock],
    pairs: list[tuple[int, int]],
    footprints: dict[str, Footprint],
    joined: dict[str, list[int]],
) -> dict:
    """The join's result and its evidence, deterministically ordered.

    Every building row is `mechanism: "data"` today — the ladder's other rungs
    (`authored`, `survey`, `hash`) are decided at pack time by `R4`, which
    reads this document to know where data already won. Recording the winner
    per building is `Q47`'s "mechanism-won provenance" obligation.
    """
    spec = city.podiums
    assert spec is not None

    buildings = {}
    for key in sorted(joined):
        footprint = footprints[key]
        candidates = [
            stitched[i]
            for i in joined[key]
            if footprint.base_mpd + _WINDOW_M < stitched[i].roof < footprint.top_mpd - _WINDOW_M
        ]
        if not candidates:
            continue
        winner = max(candidates, key=lambda block: block.roof)
        buildings[key] = {
            "boundary_m": round(winner.roof - footprint.base_mpd, 3),
            "base_mpd": round(footprint.base_mpd, 3),
            "mechanism": "data",
            "certain": winner.certain,
            "blocks": winner.refs,
        }

    tower = spec.code("tower")
    kinds = sorted({block.kind for block in stitched})
    exact = {t for t, p in pairs if stitched[t].base == stitched[p].roof}
    return {
        "schema_version": PODIUMS_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "buildings": buildings,
        "join": {
            "towers_with_podium": len({t for t, _ in pairs}),
            "pairs": len(pairs),
            "exact_level_meets": len(exact),
            "stems_read": len(footprints),
            "stems_with_boundary": len(buildings),
        },
        "stitch": {
            "pieces": len(blocks),
            "logical": {kind: sum(1 for block in stitched if block.kind == kind) for kind in kinds},
            "cross_sheet_groups": sum(1 for block in stitched if len(block.pieces) > 1),
            "towers": sum(1 for block in stitched if block.kind == tower),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    document = build_podiums(city, args.region)
    if document is None:
        log.info("  no podiums block configured; boundaries stay survey- and hash-driven")
        return 0
    join_report, stitch_report = document["join"], document["stitch"]
    log.info(
        "  %d pieces -> %d logical blocks (%d stitched across cuts)",
        stitch_report["pieces"],
        sum(stitch_report["logical"].values()),
        stitch_report["cross_sheet_groups"],
    )
    log.info(
        "  %d/%d towers meet a podium block; %d exact level meets; "
        "%d/%d shipped buildings carry a data boundary",
        join_report["towers_with_podium"],
        stitch_report["towers"],
        join_report["exact_level_meets"],
        join_report["stems_with_boundary"],
        join_report["stems_read"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
