"""How far the drawn carriageway is from the structure it is meant to lie on (`P2-7`).

`P2-7`'s acceptance, and the reason it is a separate tool rather than a number
the road stage prints: **the stage cannot mark its own work.** `roads.py` chose
every off-grade height by asking `HeightField.sample_along` about the source map
sheets. Asking the same query about the same geometry afterwards measures only
whether the answer was written down correctly — it reads |error| p90 0.02 m,
which is the sampler agreeing with itself.

So nothing here is shared with the code it grades:

| | the pipeline | this tool |
|---|---|---|
| Structure geometry | source sheets, full density | **shipped tiles**, decimated and welded |
| Which surface is a deck | slab clustering, continuity walk | **upward faces**, by winding |
| Which class is structure | sub-directory in the sheet zip | **vertex colour** |
| Which height wins | continuity from the last station | **nearest to the drawn road** |
| Spatial index | `HeightField`'s fitted grid | its own, keyed from the origin |

⚠️ Two things here are *not* independent, and saying so is the point of a table
like this. The barycentric test in `Faces.heights_at` is `terrain._hits` with
different names — a sign or inclusivity error in it would be present in both and
invisible here. And `stations` is `plan_steps` plus the body of
`roads.resample`, kept as a copy rather than imported because
`from pipeline.roads import ...` drags in `pipeline.terrain` and GDAL, and
losing "`HeightField` is unreachable from this module" costs more than three
lines of duplication are worth. Neither is where the value is: the rows above
are, and station placement decides only *where* a height is compared, never what
the comparison means.

The tile decimation is the part that matters. `P2-1` collapses `INFRASTRUCTURE`
on a 0.5 m cell, and a deck is thinner than a building — so the geometry the
player's wheels actually touch is *not* the geometry the ETL sampled, and the
difference is exactly what an internal check cannot see.

The carriageway is read from the shipped `roads.glb`. `roadgraph.json` supplies
plan positions — which edges are off-grade and where their centrelines run — and
one height, its own `y`, used *only* to decide which of several overlapping
drawn surfaces belongs to an edge. It never scores one. `elevated_samples`
argues that in full, because it is the seam where a defect could hide.

Run:  .venv/bin/python tools/deck_error.py
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.config import load_config  # noqa: E402
from pipeline.export import CITY_SCHEMA  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402

log = logging.getLogger(__name__)

# A face this far from horizontal is not a deck top. Generous on purpose: a
# ramp climbing 10% has a normal 0.995 up, and the loosest thing this must still
# reject is the near-vertical side of a deck slab. Anything in 0.2-0.9 gives the
# same answer on this region, so it is a classifier and not a tuning value.
_UPWARD = 0.5

# Plan grid for the point query. Sized like `HeightField`'s for the same reason
# — a few metres of triangle against an eight-metre cell — and independent of it
# because a shared index would let one bug hide in both.
_CELL_M = 8.0


@dataclass(frozen=True)
class Faces:
    """Near-horizontal triangles indexed in plan, for a point query.

    Used twice — once over the structure in the shipped tiles, once over the
    shipped road mesh — because both questions are "what height is drawn here".
    """

    corners: np.ndarray  # (n, 3, 3): triangle, corner, xyz
    cells: dict[tuple[int, int], np.ndarray]

    @classmethod
    def of(cls, corners: np.ndarray, *, signed: bool) -> Faces:
        """Index the near-horizontal faces among `corners`.

        `signed` keeps only faces wound upward, which separates a deck's top
        from its underside. Off for the road mesh, which has no underside — it
        does carry junction caps at node height, and those are the likeliest
        reason a handful of stations fail attribution near a junction.
        """
        edge_a, edge_b = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
        normal = np.cross(edge_a, edge_b)
        length = np.linalg.norm(normal, axis=1)
        rise = normal[:, 1] if signed else np.abs(normal[:, 1])
        upright = np.divide(rise, length, out=np.zeros(len(normal)), where=length > 0)
        corners = corners[upright > _UPWARD]

        binned: dict[tuple[int, int], list[int]] = {}
        plan = corners[:, :, [0, 2]]
        low = np.floor(plan.min(axis=1) / _CELL_M).astype(np.int64)
        high = np.floor(plan.max(axis=1) / _CELL_M).astype(np.int64)
        for index in range(len(corners)):
            for column in range(low[index, 0], high[index, 0] + 1):
                for row in range(low[index, 1], high[index, 1] + 1):
                    binned.setdefault((column, row), []).append(index)

        # Frozen to arrays once, because `corners[list]` re-converts the list on
        # every one of the ~6,800 queries. A dict of short lists is the trade
        # `terrain.py` explicitly refused for its own index; it is kept here
        # because this grid is unbounded — the tool has no `region_high` to size
        # a dense one against — and 9 MB on a hand-run tool is not worth the
        # origin-and-extent bookkeeping a flat index would need.
        return cls(
            corners=corners,
            cells={key: np.asarray(value, dtype=np.int64) for key, value in binned.items()},
        )

    @classmethod
    def from_tiles(
        cls,
        paths: list[Path],
        colour: tuple[int, int, int],
        jitter: float,
        class_name: str = "structure",
    ) -> Faces:
        blocks = list(class_triangles(paths, lambda colours: wears(colours, colour, jitter)))
        if not blocks:
            raise SystemExit(
                f"no '{class_name}' geometry in the shipped tiles — is the colour right?"
            )

        # Signed: winding survives the merge and the decimation — 16,554 faces
        # wound up against 10,174 wound down, the tops and undersides of the
        # same decks. Keeping both would let a carriageway that has sunk *into*
        # a deck score against the underside 1.5 m below and read as a small
        # positive error, which is the one direction this must not flatter.
        return cls.of(np.concatenate(blocks), signed=True)

    def heights_at(self, x: float, z: float) -> np.ndarray:
        """Every upward-facing structure height at this plan position."""
        candidates = self.cells.get((int(np.floor(x / _CELL_M)), int(np.floor(z / _CELL_M))))
        if candidates is None:
            return np.zeros(0)

        corners = self.corners[candidates]
        ax, az = corners[:, 0, 0], corners[:, 0, 2]
        bx, bz = corners[:, 1, 0] - ax, corners[:, 1, 2] - az
        cx, cz = corners[:, 2, 0] - ax, corners[:, 2, 2] - az
        twice_area = bx * cz - bz * cx
        px, pz = x - ax, z - az
        beta = px * cz - pz * cx
        gamma = pz * bx - px * bz
        sign = np.where(twice_area < 0.0, -1.0, 1.0)
        magnitude = np.abs(twice_area)

        inside = (
            (beta * sign >= 0.0)
            & (gamma * sign >= 0.0)
            & ((beta + gamma) * sign <= magnitude)
            & (magnitude > 1e-12)
        )
        if not inside.any():
            return np.zeros(0)
        beta, gamma = beta[inside] / twice_area[inside], gamma[inside] / twice_area[inside]
        return (
            corners[inside, 0, 1]
            + beta * (corners[inside, 1, 1] - corners[inside, 0, 1])
            + gamma * (corners[inside, 2, 1] - corners[inside, 0, 1])
        )


def wears(colours: np.ndarray, base: tuple[int, int, int], jitter: float) -> np.ndarray:
    """Which vertex colours could be `base` after the building stage jittered it.

    ⚠️ An exact match finds almost nothing — 428 triangles of 434,149 on this
    region, which looks like a working filter and is not. `colour_for` jitters a
    class by a **single scale factor across all three channels**, seeded from the
    mesh name. So a jittered class does not occupy one colour in the shipped
    tiles; it occupies a ray from black through its base colour, and the classes
    are told apart by that direction rather than by a value.

    The jitter is per class since `P3-10` — the ground takes none — so the caller
    has to pass `jitter_for(class)` rather than the city's default. At zero this
    collapses to the exact match, which is correct rather than a special case.

    Tested as "is there one factor that rounds to all three channels": each
    channel admits `f` in `[(c - 0.5) / base, (c + 0.5) / base]`, so the class is
    whatever has a non-empty intersection inside the configured jitter. Exact
    rather than an angular tolerance, and it needs no threshold of its own.

    The interval form is not merely tidier than an angle — it is what makes the
    test work here. Measured on the shipped tiles, the nearest *rejected* colour
    sits **0.28 degrees** off the structure's own ray and is refused only because
    it is 39% too bright. An angular tolerance loose enough to absorb rounding
    would have taken it.
    """
    channels = np.asarray(base, dtype=np.float64)
    # `colour_for` clamps each channel to 0-255, which truncates the ray and
    # would make the intervals below lie. The ceiling is not 255: clamping bites
    # as soon as the *brightest* jittered value would exceed it, which at a
    # jitter of 0.06 is any channel over about 240. Grey decks are nowhere near
    # either end, so this has never fired — it is here because a city that
    # coloured a matched class near-white would otherwise be silently over-matched.
    if (channels <= 0.0).any() or (channels * (1.0 + jitter) > 255.0).any():
        raise SystemExit(
            f"colour {base} jitters past a channel limit, where `colour_for` clamps "
            "and this test stops being exact"
        )

    values = colours.astype(np.float64)
    low = np.maximum(((values - 0.5) / channels).max(axis=1), 1.0 - jitter)
    high = np.minimum(((values + 0.5) / channels).min(axis=1), 1.0 + jitter)
    return low <= high


# --------------------------------------------------------------------------
# Reading the shipped bundle — shared with `overhang.py` and `ground_clearance.py`
#
# All three grade the same bundle and must resolve it the same way, down to the
# message a missing `city.json` prints. Kept here rather than in a fourth module
# because this one is the oldest and the one `P2-7` cites; the split that
# matters is tool-versus-pipeline, and that is unaffected.
# --------------------------------------------------------------------------


def bundle_arguments() -> argparse.ArgumentParser:
    """The arguments every bundle-grading tool needs, as an argparse parent."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--generated",
        type=Path,
        default=ROOT / "game" / "assets" / "generated",
        help="the shipped bundle to grade (default: the game's)",
    )
    parent.add_argument("--lod", type=int, default=0, help="tier to measure (default: the finest)")
    parent.add_argument(
        "--attribute-within-m",
        type=float,
        default=0.40,
        # Sized by what it must *tolerate*, not by caution. The ribbon is
        # extruded from the polyline this is compared against, so a correctly
        # attributed surface differs only by mitre and trim interpolation —
        # centimetres — and 0.40 is still nearly three kerb heights.
        #
        # A wider window is not safer, it is wrong: at 1.0 m the Wan Chai
        # Interchange mis-attributed a level-0 junction cap 0.45 m away to a
        # level-1 edge, and reported the clearance it does not carry as 0.20 m
        # of extra error. Tightening to 0.40 removed that and cost no coverage.
        help="how far the drawn road may sit from the edge it is attributed to, vertically",
    )
    return parent


def load_bundle(generated: Path, lod: int) -> tuple[dict[str, Any], list[Path]]:
    """The manifest and the tile paths for one tier, or a named exit."""
    try:
        manifest = json.loads((generated / "city.json").read_text())
    except FileNotFoundError:
        raise SystemExit(
            f"no city.json under {generated}. Build the region first:\n"
            f"  cd etl && python -m pipeline --region <region>"
        ) from None

    # Grading a stale bundle silently is the class of wrong answer the version
    # exists to catch; one check here covers all three graders, because
    # `overhang.py` and `ground_clearance.py` import this loader.
    version = manifest.get("schema_version")
    if version != CITY_SCHEMA:
        raise SystemExit(
            f"{generated / 'city.json'} declares schema_version {version}, these tools "
            f"grade {CITY_SCHEMA}. Rebuild the region first."
        )

    tiers = min(len(tile["lods"]) for tile in manifest["tiles"])
    if not 0 <= lod < tiers:
        raise SystemExit(f"--lod {lod}: this bundle ships tiers 0 to {tiers - 1}")
    return manifest, [generated / tile["lods"][lod] for tile in manifest["tiles"]]


def class_triangles(
    paths: list[Path], keep: Callable[[np.ndarray], np.ndarray]
) -> Iterator[np.ndarray]:
    """Corner arrays for the triangles of one class, across the shipped tiles.

    `keep` takes a mesh's `(n, 3)` uint8 vertex colours and returns which
    vertices belong to the class — usually `wears` bound to a base colour, but
    `carriageway_occupancy.py` passes a *complement* to pick buildings, which have
    height-banded colours and so occupy many rays rather than one.

    ⚠️ **All three corners must wear the class, and that rule lives here alone.**
    A triangle spanning two of them is a weld artefact rather than a surface.
    It was written out twice — once here and once in the occupancy tool — which
    is two places for it to stop being true.
    """
    for path in paths:
        for mesh in read_glb(path):
            if mesh.colours is None or not len(mesh.triangles):
                continue
            worn = keep(mesh.colours[:, :3])
            faces = mesh.triangles[worn[mesh.triangles].all(axis=1)]
            if len(faces):
                yield mesh.positions[faces].astype(np.float64)


def log_bundle(manifest: dict[str, Any], lod: int) -> None:
    """The build stamp, so a run pasted into a report says which build it graded.

    Public because all four bundle graders open with it and a fifth would copy it
    again — the argument `overhang.py` makes for its own four helpers.
    """
    log.info(
        "%s / %s, LOD %d, built %s",
        manifest["city_id"],
        manifest["region_id"],
        lod,
        manifest.get("generated_utc", "unknown"),
    )


def class_faces(city: Any, tiles: list[Path], class_name: str) -> Faces:
    """Upward-facing geometry of one mesh class, across the shipped tiles.

    Colour is the only thing that tells one class from another once a tile is
    merged into a single primitive, so a class with no `class_materials` entry
    cannot be graded at all — which is a config answer, not a missing feature.

    `jitter_for`, not the bare `colour_jitter`: a class may override it since
    `P3-10`, and `wears` is exact about the interval it tests, so the wrong
    jitter widens or narrows the ray and silently changes what matches.
    """
    material = city.buildings.class_materials.get(class_name)
    if material is None:
        raise SystemExit(
            f"city '{city.id}' gives '{class_name}' no entry in class_materials, so it cannot "
            "be told apart from buildings in a merged tile"
        )
    return Faces.from_tiles(
        tiles, material.colour, city.buildings.jitter_for(class_name), class_name
    )


def structure_faces(city: Any, tiles: list[Path]) -> tuple[Faces, str]:
    """Upward-facing structure across the tiles, and the class name it came from."""
    structure_class = city.buildings.structure_class
    if structure_class is None:
        raise SystemExit(
            f"city '{city.id}' declares no buildings.structure_class to measure against"
        )
    return class_faces(city, tiles, structure_class), structure_class


def drawn_surface(generated: Path, manifest: dict[str, Any]) -> Faces:
    """The shipped road mesh, indexed for a point query."""
    drawing = read_glb(generated / manifest["road_surface"])
    if len(drawing) != 1:
        # One primitive is what `surface.py` writes, and the whole carriageway
        # has to be in it. Taking `[0]` of several would measure part of the
        # road and report the coverage of all of it.
        raise SystemExit(
            f"{manifest['road_surface']} holds {len(drawing)} meshes; this expects the one "
            "carriageway surface"
        )
    mesh = drawing[0]
    return Faces.of(mesh.positions[mesh.triangles].astype(np.float64), signed=False)


@dataclass(frozen=True)
class _Samples:
    """Stations on the drawn carriageway, and everything that did not become one.

    ⚠️ `asked` and `unmatched` exist because a station that fails attribution
    used to leave no trace. Injecting a 30 m error into a third of the elevated
    carriageway then produced |error| p90 0.09 m, coverage 97.6% and a pass: the
    broken stations simply stopped being stations, and every ratio was computed
    over the survivors. A measurement tool must count what it *failed* to
    measure, or its denominator is chosen by the defect.
    """

    points: np.ndarray
    edges: int
    asked: int
    unmatched: list[int]


def elevated_samples(
    generated: Path, manifest: dict[str, Any], spacing_m: float, near_m: float
) -> _Samples:
    """Where the shipped road mesh draws the *middle* of each elevated carriageway.

    Heights come from `roads.glb` — the mesh that ships and collides. The graph
    supplies plan positions and nothing else; take a height from it and this
    would grade the ETL's arithmetic rather than its result.

    ⚠️ **Sampled down the centreline, not at the mesh's own vertices**, and the
    difference is most of this tool's answer. `roads.glb` carries vertices only
    at `TEXCOORD_0.x` of 0 and `lanes` — the two *edges* of the carriageway —
    and `width_m` is hand-tuned wider than the real road for playability. So the
    drawn edges deliberately overhang the deck they sit on, and scoring them
    finds the structure 7 m below rather than the deck they belong to. Measured
    that way `CANAL ROAD FLYOVER` reads 8.4 m of "error" at a place where the
    source sheets and the shipped tiles agree exactly and the ETL is right. That
    is overhang, which is `Q19`'s question, and this is `Q20`'s.

    Where several carriageways overlap in plan — an opposed pair, or a flyover
    over a street — the drawn height nearest the edge's own polyline is taken.
    That reads the graph's `y`, which needs stating: it identifies *which*
    surface, never scores it. A ribbon is extruded from its own polyline, so it
    sits within a kerb height of it wherever the ETL put it, including somewhere
    wrong — attribution cannot hide an error, only stop two different roads
    being compared.

    Level -1 is excluded outright. A tunnel is a void with no structure to lie
    on, so every sample would score against whatever passes overhead. `Q21` asks
    whether it should be drawn at all; it is not what `Q20` measures.
    """
    # Both filenames come from the manifest, which is the thing that knows them.
    graph = json.loads((generated / manifest["road_graph"]).read_text())

    edges = [edge for edge in graph["edges"] if edge["elevation_level"] > 0]
    if not edges:
        raise SystemExit("the graph has no elevated edges to measure")

    drawn = drawn_surface(generated, manifest)

    samples: list[tuple[float, float, float]] = []
    asked = 0
    unmatched: list[int] = []
    for edge in edges:
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        matched = 0
        for x, expected, z in stations(polyline, spacing_m):
            asked += 1
            drawn_here = nearest(drawn.heights_at(x, z), expected, near_m)
            if drawn_here is not None:
                matched += 1
                samples.append((x, drawn_here, z))
        if not matched:
            unmatched.append(int(edge["id"]))

    return _Samples(
        points=np.asarray(samples, dtype=np.float64),
        edges=len(edges),
        asked=asked,
        unmatched=unmatched,
    )


def nearest(candidates: np.ndarray, to: float, within: float | None = None) -> float | None:
    """The candidate height closest to `to`, or None if none is close enough.

    The one selection rule these tools make, wherever they make it: which drawn
    surface belongs to this edge, which deck face a sample sits on, which terrain
    face is the ground under a road. All are "the nearest height to a reference",
    and writing it per site would let them drift into different rules for the
    same decision.
    """
    if not len(candidates):
        return None
    if within is not None:
        candidates = candidates[np.abs(candidates - to) <= within]
        if not len(candidates):
            return None
    return float(candidates[np.abs(candidates - to).argmin()])


def stations(polyline: np.ndarray, spacing_m: float) -> Iterator[tuple[float, float, float]]:
    """Points down a polyline at most `spacing_m` apart, with its own height.

    Deliberately a copy of `roads.plan_steps` plus the body of `roads.resample`
    — see the module docstring for why it is not imported. Interpolating the
    height as well is the only difference, and `resample` would do that too if
    handed three columns.
    """
    if spacing_m <= 0.0:
        # Otherwise `ceil(step / 0)` is infinite and `int()` of that raises
        # `OverflowError` — `roads.resample` guards the same way.
        raise SystemExit(f"station spacing must be positive, got {spacing_m}")

    steps = np.hypot(*np.diff(polyline[:, [0, 2]], axis=0).T)
    for (start, end), step in zip(itertools.pairwise(polyline), steps, strict=True):
        pieces = max(1, int(np.ceil(step / spacing_m)))
        for piece in range(pieces):
            point = start + (piece / pieces) * (end - start)
            yield float(point[0]), float(point[1]), float(point[2])
    last = polyline[-1]
    yield float(last[0]), float(last[1]), float(last[2])


def measure(samples: np.ndarray, deck: Faces, clearance_m: float = 0.0) -> tuple[np.ndarray, int]:
    """Signed height of each sample above the nearest deck face, and the misses.

    `clearance_m` is subtracted because the carriageway is *meant* to sit that
    far above the deck — it is the wearing course, and the layer that stops the
    two surfaces interleaving once they agree to within the tile decimation.
    Scoring against the bare deck would read a deliberate 0.20 m as 0.20 m of
    error and grow with any future change to it.

    Nearest rather than highest or lowest: the question is how far the drawn
    road is from *a* deck, and a flyover stacked over another would otherwise be
    scored against whichever happened to be on top. It flatters only where two
    decks are within the error being measured, which is the case `slab_gap_m`
    already says does not occur — the closest stacked pair in this region is
    3.36 m apart.
    """
    errors: list[float] = []
    uncovered = 0
    for x, y, z in samples:
        below = nearest(deck.heights_at(float(x), float(z)), y)
        if below is None:
            uncovered += 1
            continue
        errors.append(float(y - below - clearance_m))
    return np.asarray(errors), uncovered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    parser.add_argument(
        "--accept-p90-m",
        type=float,
        default=0.5,
        help="fail above this |error| p90 (default: P2-7's criterion)",
    )
    parser.add_argument("--spacing-m", type=float, default=2.0, help="centreline station spacing")
    parser.add_argument(
        "--clearance-m",
        type=float,
        default=None,
        # Defaults to what the city declares, which is right for any bundle
        # built from that config. The override exists for the one comparison
        # that is not: grading a bundle built *before* `deck.clearance_m` — the
        # pre-`P2-7` baseline — where subtracting a layer its geometry never had
        # shifts every figure by exactly that much.
        help="override the city's deck clearance; use 0 to grade a bundle built without one",
    )
    parser.add_argument(
        "--accept-measured",
        type=float,
        default=0.90,
        help="fail if less than this share of the asked-for stations could be measured",
    )
    parser.add_argument(
        "--accept-below-m",
        type=float,
        default=0.5,
        # `P2-7` first wrote this as "no sample more than 0.1 m below", which was
        # set against the internal check where the geometry is exact. The
        # shipped tiles are not: `P2-1` collapses `INFRASTRUCTURE` on a 0.5 m
        # cell, which alone moves the deck's top face -0.04 m median and widens
        # |error| p90 from 0.030 to 0.095 with the carriageway held still. A
        # 0.1 m gate therefore sits under the resolution of the surface it is
        # measuring. Kept at the same 0.5 m as the p90 criterion, and applied to
        # the *worst* intrusion rather than to a share of samples — "how far
        # does the road ever sink into the flyover" is `Q20`'s actual question.
        help="the deepest a sample may sit below the deck before it is inside the structure",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    manifest, tiles = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)

    deck, structure_class = structure_faces(city, tiles)
    taken = elevated_samples(args.generated, manifest, args.spacing_m, args.attribute_within_m)
    declared = city.roads.deck.clearance_m if city.roads.deck is not None else 0.0
    clearance = declared if args.clearance_m is None else args.clearance_m
    errors, uncovered = measure(taken.points, deck, clearance)
    log.info(
        "  %d upward faces of '%s' across %d tiles; %d elevated edges",
        len(deck.corners),
        structure_class,
        len(tiles),
        taken.edges,
    )
    # Two ways a station leaves the measurement, and both are reported against
    # the same denominator — everything the centrelines asked for. A station is
    # lost here when the drawn road has nothing within `--attribute-within-m` of
    # it, and lost below when no deck lies under it.
    log.info(
        "  %d stations asked: %d unmatched by the drawn road, %d with no deck under them",
        taken.asked,
        taken.asked - len(taken.points),
        uncovered,
    )
    if not len(errors):
        raise SystemExit("no carriageway point had structure under it — nothing to measure")

    absolute = np.abs(errors)
    p90 = float(np.percentile(absolute, 90))
    deepest = float(-errors.min())
    log.info("")
    log.info(
        "  drawn carriageway minus the deck beneath it, less its %.2f m clearance, in metres:",
        clearance,
    )
    log.info("    median   %+.3f", float(np.median(errors)))
    log.info("    p10/p90  %+.2f / %+.2f", *np.percentile(errors, [10, 90]))
    log.info("    |err|p90 %.3f   (accepts %.2f)", p90, args.accept_p90_m)
    log.info("    deepest below the deck  %.2f   (accepts %.2f)", deepest, args.accept_below_m)
    log.info("    furthest above the deck %.2f", float(errors.max()))
    # Informational, not gates. Both are the figures `Q20` opened on — it
    # recorded the ribbon below the deck in 66% of samples — so a reader can
    # line this run up against that without re-deriving it.
    #
    # ⚠️ Reported at 0.10 m rather than "below at all", which reads 84.9% on a
    # passing run and means nothing: the tiles' own decimation puts the median
    # 0.04 m under the deck, so most of a correct carriageway is *slightly*
    # below it. `Q20`'s complaint was a road inside a flyover, not under it by a
    # tile's rounding.
    log.info("    within +-0.10 m: %.1f%%", 100.0 * float((absolute <= 0.10).mean()))
    log.info("    below the deck by over 0.10 m: %.1f%%", 100.0 * float((errors < -0.10).mean()))
    measured = len(errors) / taken.asked
    log.info(
        "    measured %.1f%% of what was asked   (accepts %.2f)",
        100.0 * measured,
        args.accept_measured,
    )

    problems = []
    if p90 > args.accept_p90_m:
        problems.append(f"|error| p90 is {p90:.2f} m")
    if deepest > args.accept_below_m:
        problems.append(f"the carriageway sinks {deepest:.2f} m into the structure")
    # ⚠️ Gating the denominator, not just the ratios above it. Every ratio here
    # is computed over the stations that survived, so a defect that stops a
    # station being measurable improves every other number on this page. An edge
    # contributing nothing is the sharpest form of that and fails outright.
    if measured < args.accept_measured:
        problems.append(f"only {100.0 * measured:.1f}% of the carriageway could be measured")
    if taken.unmatched:
        problems.append(
            f"{len(taken.unmatched)} elevated edges matched no drawn road at all: "
            f"{taken.unmatched[:5]}"
        )
    if problems:
        log.error("")
        for problem in problems:
            log.error("  FAIL  %s", problem)
        return 1

    log.info("")
    log.info("  P2-7 acceptance met.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
