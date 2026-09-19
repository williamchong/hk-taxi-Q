"""The shipped bundle, as every grader opens it.

The two side arguments, the loaded documents, and the drawn and structure faces
with their nearest-height query. Moved whole out of `deck_error.py` (`P3-35f`,
`Q133`), which eleven tools imported sideways for it. A move: nothing here is
newly shared with `pipeline.*`, and a moved name keeps its name.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.export import CITY_SCHEMA  # noqa: E402
from pipeline.gltf import read_render  # noqa: E402
from pipeline.surface import read_surface  # noqa: E402

log = logging.getLogger(__name__)

# The game's generated tree, one directory per synced region since `P5-9b`, and
# the `res://` spelling of it a bundle document uses for a generated asset.
GAME_DIR = ROOT / "game"
GENERATED_DIR = GAME_DIR / "assets" / "generated"
GENERATED_RES_ROOT = "res://assets/generated/"


def synced_region_dir() -> Path:
    """The frame region's synced bundle — the first `regions.json` lists — or the
    bare generated root where no list was written, which is a tree synced before
    `P5-9b` and reads the way it always did."""
    try:
        regions = json.loads((GENERATED_DIR / "regions.json").read_text())["regions"]
    except (OSError, ValueError, KeyError):
        return GENERATED_DIR
    return GENERATED_DIR / regions[0] if regions else GENERATED_DIR


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


def bundle_arguments() -> argparse.ArgumentParser:
    """The arguments every bundle-grading tool needs, as an argparse parent."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--generated",
        type=Path,
        default=synced_region_dir(),
        help="the shipped bundle to grade (default: the game's frame region)",
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
        for mesh in read_render(path):
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
    """The shipped road mesh, indexed for a point query.

    The road ships as one chunk per tile since `P5-6`, and `city.json`'s
    `road_surface` lists them; `read_surface` merges them back into the one
    carriageway every grader here measures. Taking one chunk of several would
    measure part of the road and report the coverage of all of it, which is what
    the single-mesh check this replaced was guarding against — the merge keeps
    that guarantee by construction, because it reads every chunk the manifest
    names.
    """
    mesh = read_surface(generated, manifest["road_surface"])
    return Faces.of(mesh.positions[mesh.triangles].astype(np.float64), signed=False)


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
