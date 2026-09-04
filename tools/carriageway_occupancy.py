"""Whether solid geometry stands in the drawn carriageway (`Q19`).

The fourth sibling of `deck_error.py`, `overhang.py` and `ground_clearance.py`,
and the only one that asks a question about the *player's* path rather than
about the road's own shape. `deck_error` asks how far an elevated road sits from
the deck under it; `overhang` asks whether there is a deck under it at all;
`ground_clearance` asks whether the ground stands in it. This asks the one none
of them reach — **is anything standing in the road at bumper height?**

It exists because collision shipped. Before that, geometry crossing the
carriageway was a drawing defect; since then it is **invisible wall on roads the
graph calls legal**, and `RoadGraph` has no idea any of it is there. `P3-3`'s
traffic routes on those edges, so every blocked lane is a car driving into a
building — the reason `Q19` names `P3-3` as its owner and asks for a tool that
fails the build.

Two occupier classes, and they do not share a fix:

- **`INFRASTRUCTURE`** — a genuine defect, and the half that shrank with `Q20`.
- **Buildings** — ⚠️ **written here as the half this project *chose*, and that
  is now known to be false.** The reading was that the widening's 1.6x eats
  the pavement and then the ground-floor frontage, so the blockage lives in the
  widened fringe and is a playability trade rather than a bug. `Q19`'s
  2026-08-19 re-measurement killed it twice over: three `BUILDING` edges read
  **0.00 m**, the same stations read 0.00-0.49 m *inside the un-widened width*
  as well, and `tools/narrowing.py` swept every factor `GAME_DESIGN.md` allows
  without clearing one edge. The obstruction is in the real street, so this half
  is not a trade anybody made and narrowing is not its fix.

Which leaves the question this tool now has to answer rather than assume:
**what is actually standing there.** The corridor listing therefore reports
every failing edge — never the tightest handful, which is how the sentence
above survived as long as it did — with its blocker and the shape of the
blockage along the edge.

⚠️ **Ground is not an occupier and is excluded by name.** Terrain standing in
the carriageway is `Q24`, it is `ground_clearance.py`'s to grade, and counting
it here would double-report one defect under two questions.

**What "occupied" means, and the trap in the obvious alternative.** A cell is
occupied when class geometry has *surface* in the band 0.3-2.0 m above the drawn
road. Surfaces, not volumes, and not bounding boxes:

- ⚠️ A first measurement for `Q19` marked each triangle's **bounding box** and
  read **13.71%**; sampling the actual surfaces cut it to a third. A box around
  a sloped flyover soffit covers carriageway the soffit is nowhere near.
- ⚠️ **A vertical ray cannot find a wall.** A wall is a vertical face, so it
  projects to a line in plan and a point-in-plan test hits it with probability
  zero — which is why `Faces.heights_at` cannot be reused here however much it
  looks like the right query. It is built for "what height is drawn here", and
  that question only has an answer for near-horizontal faces.
- The consequence, stated rather than hidden: the *interior* of a building
  footprint reads as clear, because an extruded building has no floor and its
  roof is far above the band. That is the right model for what a car meets — it
  collides with the wall at the perimeter and never reaches the middle — and the
  clear-corridor criterion below is what actually catches a blocked lane.

**The gate that matters is per-edge, not the region share.** A share tells
`P3-3` nothing: `RoadGraph` routes on edges, and what strands a traffic car is
one blocked edge rather than an average. Scattered occupancy a car can weave
through and a wall straight across the road are the same percentage. So the
criterion is a **clear corridor at least one lane wide**, `lane_width_m` from
the city config, held continuously along every drivable level-0 edge.

Region shares are gated too, but as a ratchet against `Q19`'s own published
figures rather than as the headline. Those numbers were fixed before this
grader existed — `Q47`'s precedent for a bar the instrument cannot have been
tuned to.

⚠️ **Off-grade carriageway is reported and never gated.** `Q21` has not decided
whether level -1 should be drawn at all and Phase 4 owns it; failing the build
over a decision nobody has made would be this tool inventing policy.

Nothing here is shared with the code it grades — same argument as
`deck_error.py`'s docstring, same table. The occupiers come from the **shipped
tiles**, found by vertex colour, and the road from the **shipped `roads.glb`**
rather than from the graph the ETL wrote.

Run:  .venv/bin/python tools/carriageway_occupancy.py

⚠️ **`--corridor-report` is where `Q19`'s argument now lives.** The listing above
says which edges fail and what is standing in them; the report says what the
blockage is *shaped* like along the edge, and whether the occupier is on the
**centreline** — which is the question that refused every width fix, because
`lanes`, `width_m` and the carriageway floor all move the ribbon's edges and none of
them moves its centreline. Both measurements were computed by this tool from the
day it shipped and thrown away unprinted, so `Q19` reversed itself three times
on scratch scripts that were never committed (`Q37`'s debt, `Q55`'s). It is
opt-in and the default listing is unchanged by it: nothing here gates.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

# `wears` is the single statement of how a class is told apart once a tile is
# merged into one primitive — a colour *ray* from black through the base, because
# `colour_for` jitters by a single scale factor across all three channels. Made
# public for this tool on the precedent `overhang.py` set for its own four
# helpers: `class_faces` cannot serve here, since it returns near-horizontal
# `Faces` and refuses any class without a `class_materials` entry — which is
# every building.
from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    class_triangles,
    drawn_surface,
    load_bundle,
    log_bundle,
    nearest,
    wears,
)
from overhang import (  # noqa: E402
    cross_section,
    drawn_offsets,
    half_width_at,
    half_widths,
    left_of,
    offset_at,
    walk_width,
)
from pipeline.config import Config, load_config  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402

log = logging.getLogger(__name__)

# `Q19`'s band, mirrored so this tool reproduces the frame the 5.17% was measured
# in. The floor clears the 0.15 m kerb and the road's own thickness; the ceiling
# is where a podium stops being an obstacle and starts being Hong Kong working as
# intended — the city overhangs its pavements everywhere, and a soffit 6 m up is
# not something a car can hit.
BUMPER_LOW_M = 0.30
BUMPER_HIGH_M = 2.00

# The elevation levels the corridor half judges. ✅ **`(0, 1)` since
# 2026-09-04, moved in the same diff as `pipeline.clearance.LEVELS`** — the
# bundle now carries a level-1 `clear_width_m`, so this half grades the
# population the pipeline publishes rather than a subset of it. `--levels` is
# still that stage's knob at the second instrument and it still buys the level
# the bundle does not carry: level -1, which `_levels_argument` refuses below
# for its own reason.
#
# 🔴 **Widening this does NOT widen the gate.** `split_by_level` keeps the
# off-grade rows out of `--accept-corridor-lanes` and `off_grade_report` prints
# them apart, because ground proud of a street and a parapet on a viaduct want
# opposite fixes (`Q57`). What changed is that the second population is now the
# default rather than something a flag had to ask for.
#
# ⚠️ **Moving this default moves `clearance_reconcile.py`'s `EXPECT_GRADER`**,
# and `Q51`'s ratchet is what keeps the pipeline's count and this tool's count
# describing one bundle — so a default flipped here and not there stops the two
# figures being about the same thing. That is why the two moved together.
#
# ⚠️ **The parse below is written out rather than imported from
# `pipeline.clearance`.** `ground_clearance.py` imports that module's bumper
# *bounds* deliberately and the rule attached to it is explicit: a shared bound
# is not a shared reading, and no second import comes in on that precedent. The
# whole value of this tool is that it shares no method with what it grades.
CORRIDOR_LEVELS = (0, 1)

# Plan cell for the occupier index, and **the dominant error term in every
# corridor width below** — not `--across-m`, which only quantises the answer.
# A cell blocks in full as soon as one surface sample lands in it, so a wall
# `w` metres thick in plan blocks up to `w + 2 * INDEX_CELL_M` of carriageway,
# and a corridor bounded by two obstructions loses up to twice that again.
#
# ⚠️ **This is why the tool reads more starved edges than `clearance.py` does,
# and it is deliberate.** `Q51` records 26 here against the pipeline's 21, and
# the gap was measured to this constant: brute-forcing `e132` from its own
# geometry reproduces **0.98 m at 1.0 m** and **4.00 m at 0.25 m**, which are
# the two instruments' published numbers exactly. Sweep it with
# `--index-cell-m` to price that; the default stays coarse on purpose, because
# the smear is also what makes this tool immune to the aliasing the pipeline is
# exposed to — a wall between two of its 1 m cross-sections is missed outright,
# while a 1 m bin cannot miss one. Two instruments, two error dimensions.
INDEX_CELL_M = 1.0

# Coarse cell for the pruning pass. Free to choose — the prune is a superset
# test — and set to `deck_error`'s own index cell because that is a size this
# region's geometry is already known to bin well at.
COARSE_CELL_M = 8.0

# How much of a station's drawn width must actually be there before a corridor is
# judged from it. See the guard in `survey`.
_CORRIDOR_MEASURED = 0.90


def _trimmed(judged: int, cells: int) -> bool:
    """Too little road drawn across this station to judge a corridor from it.

    🔴 **One statement of the rule, called from both places that apply it** —
    `survey.close_station`, which decides what reaches `corridor_profile`, and
    `Standing.trimmed`, which decides what `occupier_report` prints "not judged"
    over. The reader lines those two listings up against each other, so a
    flipped operator or a `<=` on one side alone makes a probe row with no
    profile counterpart, and that reads as a missing obstruction rather than as
    two rules. Sharing the constant was not enough: the comparison was the
    second copy. `_starved_shape` delegating to `_clear_run` is the precedent.
    """
    return judged < _CORRIDOR_MEASURED * cells


# The walk's own defaults, named rather than typed into `argparse` alone because
# `tools/clearance_reconcile.py` grades with them too. Hand-copied into a second
# parser, they could drift and the reconciler would quietly ratchet `Q51`'s counts
# against settings this tool no longer uses.
SPACING_M = 1.0
ACROSS_M = 0.5
SAMPLE_M = 0.25

# Names for the two classes the config cannot supply. `INFRASTRUCTURE` is the
# city's to name (`buildings.structure_class`); these two are not, and
# `tools/narrowing.py` already declares them for the same reason.
BUILDING = "BUILDING"
LANDMARK = "LANDMARK"

# `roads.py` writes `width_source` and `offset_source` as bare literals and
# exports no constant, so this is **restated rather than imported** — the same
# call `tools/centreline_error.py` makes, and for its reason: these graders
# share no code with the pipeline they grade, and an import would be the first
# one. A drift here is caught by the counters reading 0 of 4.
_DECK_SOURCE = "deck"


@dataclass(frozen=True)
class Occupied:
    """Surface sample heights of one occupier class, binned in plan.

    Heights are sorted per cell so the band test is a binary search rather than a
    scan: the carriageway asks this roughly a million times.
    """

    cells: dict[tuple[int, int], np.ndarray]
    triangles_kept: int
    triangles_seen: int
    samples: int
    # The plan cell the heights were binned at. Carried rather than read off the
    # module constant so a sweep cannot bin at one size and query at another —
    # which reads as a city that has cleared itself up.
    cell_m: float = INDEX_CELL_M

    def in_band(self, x: float, z: float, low: float, high: float) -> bool:
        """Is there surface between `low` and `high` at this plan position?"""
        heights = self.cells.get((int(np.floor(x / self.cell_m)), int(np.floor(z / self.cell_m))))
        if heights is None:
            return False
        index = int(np.searchsorted(heights, low, side="left"))
        return index < len(heights) and bool(heights[index] <= high)

    def band_extent(
        self, x: float, z: float, low: float, high: float
    ) -> tuple[float, float] | None:
        """`in_band`'s question answered with *heights* — what is standing here,
        and how far up and down its column reaches. `None` where nothing is.

        ⚠️ **Not a replacement for `in_band` and deliberately a second query.**
        That one is asked ~1.1 M times a run and returns the moment it can; this
        one is asked for a handful of named edges. What they must never do is
        disagree about *whether* a cell is occupied — a probe reporting an
        occupier the corridor half never saw would be diagnosing a different
        city — so `test_band_extent_agrees_with_in_band` pins the two together
        rather than a comment claiming they share a rule.

        🔴 **Both column bounds are ONE-SIDED, and which side is the whole
        reading.** `index_corners` keeps a triangle only where its own height
        range overlaps the band, so geometry lying entirely above or below is
        absent:

        - `column_high` is a **lower** bound. A short reading is weak evidence of
          a low object and never proof of headroom above it.
        - `column_low` is an **upper** bound, which is the safe direction for the
          question that matters here: a value at or under `low` is proof that
          solid geometry reaches down to the road, and so refutes headroom
          outright. That is the reading `Q103` could not get for `e489`.

        ⚠️ **The surface's position *within* the band is deliberately NOT
        returned.** It is clipped to `[low, high]` by construction, so it is the
        one number here that could never be a finding — `Q58`'s `drawn_gauge_m`
        trap in miniature — and a value that cannot mean anything is worse
        carried than absent: it reads as an extent, which is exactly what the
        two bounds above are for. It was returned for one revision, with a
        warning, and no caller ever wanted it.
        """
        heights = self.cells.get((int(np.floor(x / self.cell_m)), int(np.floor(z / self.cell_m))))
        if heights is None:
            return None
        # The same `searchsorted` and the same comparison as `in_band` above,
        # so the two cannot answer the occupancy question differently.
        first = int(np.searchsorted(heights, low, side="left"))
        if first >= len(heights) or not heights[first] <= high:
            return None
        return float(heights[0]), float(heights[-1])


def _barycentric(steps: int) -> np.ndarray:
    """Weights for a triangle sampled `steps` times along its longest edge."""
    first, second = np.meshgrid(np.arange(steps + 1), np.arange(steps + 1), indexing="ij")
    keep = (first + second) <= steps
    alpha = first[keep] / steps
    beta = second[keep] / steps
    return np.stack([alpha, beta, 1.0 - alpha - beta], axis=1)


def _touches_band(
    plan_low: np.ndarray,
    plan_high: np.ndarray,
    height_low: float,
    height_high: float,
    bands: dict[tuple[int, int], tuple[float, float]],
) -> bool:
    """Could one triangle reach the carriageway's occupiable band anywhere?

    Both tests admit more than the real one — a plan *box* against a coarse cell,
    and a height *range* against the widest band in it — so this is a superset of
    what is really occupied. That direction is the safe one: it keeps geometry a
    finer test would have to look at, and never drops any.
    """
    for column in range(int(plan_low[0]), int(plan_high[0]) + 1):
        for row in range(int(plan_low[1]), int(plan_high[1]) + 1):
            band = bands.get((column, row))
            if band is not None and height_high >= band[0] and height_low <= band[1]:
                return True
    return False


def class_predicates(
    city: Config,
) -> tuple[str, Callable[[np.ndarray], np.ndarray], Callable[[np.ndarray], np.ndarray]]:
    """The structure class's name, and the two colour tests that select occupiers.

    Public because `tools/clearance_reconcile.py` has to index the *same* classes
    this tool does — that is the entire premise of comparing the two instruments —
    and a second copy of the complement below is a second place for it to stop
    being true. `deck_error.class_triangles` carries the same argument about
    itself, having already been written out twice.
    """
    structure_class = city.buildings.structure_class
    if structure_class is None:
        raise SystemExit(f"city '{city.id}' declares no buildings.structure_class")
    material = city.buildings.class_materials[structure_class]
    jitter = city.buildings.jitter_for(structure_class)

    def is_structure(colours: np.ndarray) -> np.ndarray:
        return wears(colours, material.colour, jitter)

    def is_building(colours: np.ndarray) -> np.ndarray:
        # Everything the config gives a flat material to, subtracted. Buildings
        # take height-banded colours, so they occupy many rays rather than one
        # and cannot be selected positively — but every class that *can* be is
        # named in `class_materials`, so the complement is buildings.
        #
        # ⚠️ **Every entry, not just structure and ground.** Subtracting only the
        # two named above left a third flat-material class counted as `BUILDING`
        # and gated against `--accept-building-share`, while the comment claimed
        # the complement "stays right when a class is added". It does now.
        other = np.zeros(len(colours), dtype=bool)
        for name, entry in city.buildings.class_materials.items():
            other = other | wears(colours, entry.colour, city.buildings.jitter_for(name))
        return ~other

    return structure_class, is_structure, is_building


def index_classes(
    city: Config,
    generated: Path,
    manifest: dict[str, Any],
    tiles: list[Path],
    bands: dict[tuple[int, int], tuple[float, float]],
    *,
    sample_m: float,
    cell_m: float,
) -> dict[str, Occupied]:
    """Every occupier class, indexed at one plan cell.

    One call site for all three, so a caller cannot bin two of them at one cell
    size and the third at another — `survey` would consume that mixed dict without
    complaint and the mismatched class would simply stop being found.
    """
    structure_class, is_structure, is_building = class_predicates(city)
    return {
        structure_class: occupiers(tiles, is_structure, bands, sample_m, cell_m=cell_m),
        BUILDING: occupiers(tiles, is_building, bands, sample_m, cell_m=cell_m),
        LANDMARK: landmark_occupiers(generated, manifest, bands, sample_m, cell_m=cell_m),
    }


def occupiers(
    tiles: list[Path],
    keep: Callable[[np.ndarray], np.ndarray],
    bands: dict[tuple[int, int], tuple[float, float]],
    sample_m: float,
    *,
    cell_m: float = INDEX_CELL_M,
) -> Occupied:
    """Index one occupier class's surfaces across the shipped tiles.

    The class rule — a triangle joins only if **all three** corners wear it —
    belongs to `deck_error.class_triangles` and is applied there, not restated
    here.
    """
    return index_corners(class_triangles(tiles, keep), bands, sample_m, cell_m=cell_m)


def index_corners(
    blocks: Iterator[np.ndarray],
    bands: dict[tuple[int, int], tuple[float, float]],
    sample_m: float,
    *,
    cell_m: float = INDEX_CELL_M,
) -> Occupied:
    """Bin the surfaces of every triangle that could reach the road.

    ⚠️ **The pruning is what makes this affordable, and it is a superset rather
    than an approximation.** Sampling every building triangle in the region would
    be hundreds of millions of points to answer a question about the lowest two
    metres of the wall. A triangle survives only if its plan bounding box meets a
    coarse cell holding carriageway *and* its own height range overlaps that
    cell's band. Both tests admit more than the real one, so nothing that could
    have been occupied is dropped.
    """
    binned: dict[tuple[int, int], list[np.ndarray]] = {}
    kept = seen = sampled = 0

    for corners in blocks:
        seen += len(corners)
        plan_low = np.floor(corners[:, :, [0, 2]].min(axis=1) / COARSE_CELL_M).astype(np.int64)
        plan_high = np.floor(corners[:, :, [0, 2]].max(axis=1) / COARSE_CELL_M).astype(np.int64)
        height_low = corners[:, :, 1].min(axis=1)
        height_high = corners[:, :, 1].max(axis=1)

        wanted = [
            index
            for index in range(len(corners))
            if _touches_band(
                plan_low[index],
                plan_high[index],
                float(height_low[index]),
                float(height_high[index]),
                bands,
            )
        ]
        if not wanted:
            continue

        chosen = corners[np.asarray(wanted, dtype=np.int64)]
        kept += len(chosen)

        # Grouped by how many steps each triangle needs, so one lattice is
        # built per group and applied to the whole group at once. Per-triangle
        # lattices dominated the runtime when this was written the obvious way.
        longest = np.sqrt(
            np.maximum.reduce(
                [
                    np.sum((chosen[:, 1] - chosen[:, 0]) ** 2, axis=1),
                    np.sum((chosen[:, 2] - chosen[:, 1]) ** 2, axis=1),
                    np.sum((chosen[:, 0] - chosen[:, 2]) ** 2, axis=1),
                ]
            )
        )
        steps = np.clip(np.ceil(longest / sample_m), 1, 64).astype(np.int64)
        for count in np.unique(steps):
            block = chosen[steps == count]
            points = np.einsum("kc,tcd->tkd", _barycentric(int(count)), block).reshape(-1, 3)
            sampled += len(points)
            keys = np.floor(points[:, [0, 2]] / cell_m).astype(np.int64)
            order = np.lexsort((keys[:, 1], keys[:, 0]))
            keys, heights = keys[order], points[order, 1]
            cuts = np.flatnonzero(np.any(np.diff(keys, axis=0) != 0, axis=1)) + 1
            for piece_keys, piece in zip(
                np.split(keys, cuts), np.split(heights, cuts), strict=True
            ):
                if not len(piece):
                    continue
                binned.setdefault((int(piece_keys[0, 0]), int(piece_keys[0, 1])), []).append(piece)

    return Occupied(
        cells={key: np.sort(np.concatenate(value)) for key, value in binned.items()},
        triangles_kept=kept,
        triangles_seen=seen,
        samples=sampled,
        cell_m=cell_m,
    )


@dataclass(frozen=True)
class Centreline:
    """What stands on the centreline itself, at the station that condemned an edge.

    `Q19`'s building half turns entirely on this and nothing published could
    answer it: `lanes`, `width_m` and the carriageway floor all move the ribbon's
    *edges*, so if the occupier is on the centreline no width rule reaches it,
    however the corridor figure moves. That is the argument that refused both
    remaining width candidates without building either, and until now it lived
    in a scratch script.
    """

    occupier: str | None
    centre_offset_m: float
    # Sideways distance from the centreline cell to the nearest cell of each
    # state, and that cell's own signed offset. **Both**, because `Q19` reads
    # them in opposite directions: the way out for a centreline that is inside
    # the occupier, and — for the two edges that are clear at the centre — how
    # narrowly they escaped, which is the figure that makes those two exceptions
    # rather than counter-examples. The one matching the centre's own state is
    # 0.0 by construction; `inf` means the whole cross-section is in one state.
    #
    # The sign is the side, against edge direction, because `walk_carriageway`
    # emits offsets across `left_of(along)` — so a systematic registration shift
    # of one layer shows up as a consistent sign and a per-site disagreement
    # does not.
    to_clear_m: float
    clear_offset_m: float
    to_occupier_m: float
    occupier_offset_m: float


@dataclass(frozen=True)
class Standing:
    """What occupied one cross-section of a probed edge, across and in height.

    One of these per station, in walk order, so the reader can watch an occupier
    *move* along an edge. `Centreline` above answers the same question at the
    one station that condemned the edge; this answers it everywhere, which is
    what tells a fixed obstruction from one the ribbon crosses obliquely.

    ⚠️ **`bands` is the occupied runs, never their hull.** A `min .. max` over
    the occupied cells reads `-2.57 .. +2.57` for a cross-section blocked at both
    rims and wide open down the middle — the exact opposite of what it says.
    Each entry is one contiguous occupied stretch, so the gaps between them are
    the clear ones `corridor_profile` measures.
    """

    # Cells walked at this station, and how many of them had road drawn.
    # **A short station is not "clear"** — it is a junction trim with nothing to
    # judge, and the two must stay distinguishable for `Survey.no_road`'s reason
    # one class up.
    cells: int
    judged: int
    occupier: str | None
    bands: tuple[tuple[float, float], ...]
    # Column bottom and top over the drawn road. One-sided bounds in opposite
    # directions — see `Occupied.band_extent`, which says which way each leans
    # and why only the bottom can carry the headroom reading.
    base_m: float
    top_m: float

    @property
    def trimmed(self) -> bool:
        """Too little road drawn here for `survey` to have judged a corridor.

        🔴 **`_CORRIDOR_MEASURED`, the corridor half's own guard, and not a
        weaker test of this report's own.** The reader lines these stations up
        against the `profile` line printed directly above them, so a station
        this calls judged and that one skipped is a row with no counterpart —
        and the discrepancy reads as a missing obstruction rather than as two
        rules. Measured before this was shared: `e257` walked 266 stations
        against the profile's 265.
        """
        return _trimmed(self.judged, self.cells)


@dataclass
class Survey:
    """Every carriageway cell, and what stands in it.

    ⚠️ **`asked` and the misses are counted, not merely skipped**, and that is
    `deck_error`'s hardest-won lesson rather than bookkeeping. Its fourth defect
    left unmeasurable stations out of the denominator: breaking a third of the
    carriageway made the broken third stop being measured, every ratio improved,
    and the tool exited 0.
    """

    asked: int = 0
    measured: int = 0
    no_road: int = 0
    # Area by level, and the occupied part of it by level and class. Area rather
    # than a cell count, so the share does not move when the sampling lattice
    # does — a narrow ramp and a wide arterial are not equals.
    area_m2: dict[int, float] = field(default_factory=dict)
    occupied_m2: dict[tuple[int, str], float] = field(default_factory=dict)
    # The narrowest clear corridor found on each drivable judged edge, and where.
    corridor_m: dict[int, float] = field(default_factory=dict)
    corridor_at: dict[int, tuple[float, float]] = field(default_factory=dict)
    # The elevation level each judged edge was walked at. Recorded here rather
    # than re-derived in `main` because `close_station` already holds it: a
    # second pass over `graph["edges"]` would be a *different* derivation of the
    # same fact, free to drift from the one that decided the population, and it
    # would put `elevation_level`'s spelling in two places. `Q57`'s split — the
    # level-0 rows gate, the rest are reported — reads off this.
    corridor_level: dict[int, int] = field(default_factory=dict)
    # The same corridor measured only inside the authored width, at the same
    # worst station — how much of the blockage the playability widening owns.
    corridor_authored_m: dict[int, float] = field(default_factory=dict)
    # The across-spacing the reported corridor was counted in, per edge. Every
    # width above is an integer multiple of it, and it is *not* `--across-m`:
    # `cross_section` divides the drawn width into whole cells, so a 10.24 m
    # ribbon at 0.5 m becomes 21 cells of 0.4876. Published because `Q51`'s
    # table read as centimetre measurement when "0.49 m" only ever meant
    # "one cell", and the reader cannot tell those apart without this.
    corridor_span_m: dict[int, float] = field(default_factory=dict)
    # What was standing at the worst station, most cells first, at the moment
    # that station became the worst. `Q19` could name the *class* split across
    # the population and never the blocker on one edge, so a reader could not
    # tell which of two questions an edge belonged to without re-running a
    # second tool over a different population.
    corridor_blockers: dict[int, tuple[str, ...]] = field(default_factory=dict)
    # Every judged level-0 station's clear run, in walk order, per edge. The
    # corridor figure above is the minimum of one of these lists; the **shape**
    # of the list is what tells a wall crossing the street from a frontage
    # standing in it, and those two do not share a fix.
    #
    # ⚠️ Trimmed stations are absent rather than recorded as clear, so a starved
    # run measured from this can bridge a junction trim and read as one run where
    # there are two. On Wan Chai that is 129 stations of 47,275, and the
    # alternative — scoring an unjudgeable station — is the defect that once
    # condemned 18 innocent edges.
    corridor_profile: dict[int, list[float]] = field(default_factory=dict)
    # What stood on the centreline at the binding station, and how far sideways
    # the nearest clear cell was. Recorded beside `corridor_blockers` and under
    # the same rule: a fact about the cross-section that condemned the edge, not
    # about the edge. It is what tells a width defect from a centreline one, and
    # no width rule moves a centreline.
    corridor_centre: dict[int, Centreline] = field(default_factory=dict)
    # Stations whose cross-section was too trimmed to judge a corridor from.
    # Counted rather than silently skipped, for the reason in the class docstring.
    corridor_stations: int = 0
    corridor_skipped: int = 0

    def add(self, level: int, class_name: str | None, area_m2: float) -> None:
        self.area_m2[level] = self.area_m2.get(level, 0.0) + area_m2
        if class_name is not None:
            key = (level, class_name)
            self.occupied_m2[key] = self.occupied_m2.get(key, 0.0) + area_m2

    def share(self, level: int, class_name: str) -> float:
        """Occupied share of one level's own drawn area."""
        area = self.area_m2.get(level, 0.0)
        return 0.0 if area <= 0.0 else self.occupied_m2.get((level, class_name), 0.0) / area

    def drawn_share(self, level: int, class_name: str) -> float:
        """Occupied share of **all** drawn carriageway — `Q19`'s denominator.

        ⚠️ The two are not interchangeable and the gates ride on this one.
        `Q19` publishes `BUILDING` 1.72%, `INFRASTRUCTURE` 1.60% and off-grade
        1.87% as three shares that **sum to its 5.17% headline**, so they are
        all shares of the same whole. Gating the level-0 pair against a level-0
        denominator instead reads them as ~10% looser than they were written,
        which is the bar being quietly moved by a choice of divisor.
        """
        total = sum(self.area_m2.values())
        return 0.0 if total <= 0.0 else self.occupied_m2.get((level, class_name), 0.0) / total

    @property
    def coverage(self) -> float:
        return 0.0 if not self.asked else self.measured / self.asked


def _clear_run(occupied: list[bool], span_m: float) -> float:
    """The widest continuous clear width across one station."""
    best = run = 0
    for blocked in occupied:
        run = 0 if blocked else run + 1
        best = max(best, run)
    return best * span_m


def _starved_shape(profile: list[float], bar_m: float, spacing_m: float) -> tuple[float, float]:
    """How much of an edge is below the bar, and its longest unbroken stretch.

    The first number is a total and the second is a run, and the gap between
    them is the reading: 2 m of 2 m is a wall across the street, 40 m of 40 m is
    a frontage standing in it, and 6 m of 60 m in three pieces is a pier field.

    ⚠️ **Both figures are upper bounds, from two causes, and neither is tight.**
    It counts only judged stations, so a junction trim between two starved
    stretches joins them into one. And `spacing_m` is the walk's *nominal* pitch
    rather than its real one: `walk_width` cuts each segment into whole equal
    pieces, so the true pitch is `L / ceil(L / spacing_m)` and lands anywhere in
    `(spacing_m / 2, spacing_m]` — on the shipped graph the length-weighted mean
    is **0.968 m against a nominal 1.0**, and the shortest segment runs at
    0.451 m. So a published extent reads a few per cent high typically and up to
    twice on a short segment. Both errors are the direction the corridor figure
    already takes: it can overstate a blockage, never a clearance. Quoting these
    metres as a measurement rather than as a bound is the mistake to avoid.
    """
    # `_clear_run` reads its argument as "blocked", so handing it the stations
    # that *pass* makes each of them a wall bounding a starved stretch, and the
    # longest run it finds is the longest starvation. Delegated rather than
    # rewritten: the corridor figure this is read against is `_clear_run` across
    # a station, and the two are now provably the same scan rather than two
    # hand-copies of it.
    passes = [clear >= bar_m for clear in profile]
    return passes.count(False) * spacing_m, _clear_run(passes, spacing_m)


def _profile_runs(profile: list[float], ndigits: int = 1) -> list[tuple[float, int]]:
    """The clear-run profile, run-length encoded in walk order.

    `_starved_shape` reduces the same list to two numbers, and the two numbers
    are what let `Q19` read a spot blockage as a frontage for two corrections
    running. The *shape* is the reading: `10.2 x7 . 1.0 . 1.5 . 10.2 x3` is a
    street at full drawn width with something across it, and a frontage standing
    in the carriageway cannot produce it — it would leave about half the ribbon
    for the whole of its own length.

    ⚠️ **Round first, then group.** Every clear run is an integer multiple of the
    station's across-span, which `cross_section` sizes to divide the drawn width
    into whole cells — 0.4876 m on a 10.24 m ribbon. Grouping the raw floats and
    rounding afterwards therefore prints 21 runs of one where the reader needs
    `10.2 x21`, because two neighbouring stations that both read "full width"
    differ in the last bits.
    """
    runs: list[tuple[float, int]] = []
    for clear in profile:
        value = round(clear, ndigits)
        if runs and runs[-1][0] == value:
            runs[-1] = (value, runs[-1][1] + 1)
        else:
            runs.append((value, 1))
    return runs


def _centreline_verdict(
    standing_at: list[str | None], offset_at: list[float], span_m: float
) -> Centreline | None:
    """Read the centreline cell of one cross-section, and its way out.

    ⚠️ **Indexed over the *judged* cells, never over the walked ones.** A cell
    with no road drawn never reaches `standing_at`, so the centreline is
    `argmin(|offset|)` of what was judged — which at a junction trim can be
    several metres off the true centre, and is still the closest thing to a
    centreline this station has. Taking the walk's own min-offset cell instead
    would index a list it is not aligned with; taking index 0 would silently
    report the left rim, half the drawn width away.
    """
    if not standing_at:
        return None
    centre = min(range(len(standing_at)), key=lambda i: abs(offset_at[i]))

    def nearest(wanted: bool) -> tuple[float, float]:
        """Distance and signed offset of the closest cell in one state.

        ⚠️ `inf` and NaN rather than 0.0 when the state does not occur. A
        fully blocked cross-section has no way out and a fully clear one has no
        occupier, and 0.0 would read as "it is right here" — the reading that
        matters most is exactly the one at 0.0-0.5 m.

        ⚠️ **A tie returns NaN for the offset, and that is the point.** `Q19`
        reads the *sign* of this to ask whether the disagreement is one layer
        shifted sideways or fifteen separate sites, so breaking a tie toward
        either rim would manufacture the answer: the walk starts at the left rim,
        so "lowest index wins" leans negative on every symmetric cross-section
        and the signs would read less mixed than they are. A cross-section clear
        by the same margin on both sides carries no side, and says so.
        """
        found = [i for i, name in enumerate(standing_at) if (name is not None) == wanted]
        if not found:
            return float("inf"), float("nan")
        steps = min(abs(i - centre) for i in found)
        # At most two cells sit at the same distance — one either side — so two
        # candidates *is* the tie, and there is nothing further to compare.
        closest = [i for i in found if abs(i - centre) == steps]
        return steps * span_m, offset_at[closest[0]] if len(closest) == 1 else float("nan")

    to_clear_m, clear_offset_m = nearest(False)
    to_occupier_m, occupier_offset_m = nearest(True)
    return Centreline(
        standing_at[centre],
        offset_at[centre],
        to_clear_m,
        clear_offset_m,
        to_occupier_m,
        occupier_offset_m,
    )


@dataclass(frozen=True)
class Lattice:
    """Every drawn carriageway cell, walked **once**.

    ⚠️ **One walk, because two walks is a silent false pass.** This tool needs
    two passes — the occupier index can only be pruned to the band the road
    actually occupies, so the road has to be measured before the buildings are
    read — and the obvious way to write that is to walk the carriageway twice.
    Measured, the second walk cost **22 s of a 47 s run**: `heights_at` alone was
    2,231,164 calls, exactly twice the 1,115,582 cells, and the two walks emitted
    a byte-identical cell sequence.

    The cost was the smaller half of the problem. The prune is only sound while
    pass one visits a **superset** of what pass two asks about, and with the walk
    written out twice nothing enforced that. Change the level filter, the spacing,
    or the attribution window in one copy and the index is pruned away from
    carriageway the survey then asks about — and every one of those cells reads
    **clear**, which is the one direction this tool must never flatter. Walking
    once makes the superset property structural instead of a convention.

    Stored as parallel arrays rather than objects: 1.1 M cells is ~45 MB this way
    and several times that as Python tuples.
    """

    edge: np.ndarray  # int32, which edge the cell belongs to
    level: np.ndarray  # int8, elevation level
    station: np.ndarray  # int32, cells sharing one cross-section
    x: np.ndarray  # float64, plan position
    z: np.ndarray
    span: np.ndarray  # float64, the width this cell stands for
    offset: np.ndarray  # float64, signed distance from the centreline
    authored_half: np.ndarray  # float64, half the un-widened width at this cell
    surface_y: np.ndarray  # float64, drawn road height — NaN where none is drawn
    spacing_m: float

    @property
    def asked(self) -> int:
        return len(self.surface_y)

    @property
    def drawn(self) -> np.ndarray:
        """Which cells had road drawn at them."""
        return np.isfinite(self.surface_y)


def walk_carriageway(
    graph: dict[str, Any],
    manifest: dict[str, Any],
    drawn: Faces,
    *,
    spacing_m: float,
    across_m: float,
    attribute_within_m: float,
) -> Lattice:
    """Walk every drawn carriageway cell once, recording what both passes need."""
    widths = half_widths(manifest)
    drawn_offset_by_edge = drawn_offsets(manifest)

    edges: list[int] = []
    levels: list[int] = []
    stations: list[int] = []
    xs: list[float] = []
    zs: list[float] = []
    spans: list[float] = []
    offsets: list[float] = []
    authored: list[float] = []
    surfaces: list[float] = []
    station_id = 0

    for edge in graph["edges"]:
        level = int(edge["elevation_level"])
        # Level -1 is a void under the terrain that nothing can see and nobody
        # can drive — `Q21`'s question, and not evidence about this one.
        if level < 0:
            continue
        edge_id = int(edge["id"])
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue

        # The width before the carriageway floor lifted it. `Q19` names the
        # widening as the cause of its building half, so the report separates a
        # blockage that reaches the real lanes from one that only eats the
        # frontage the widening took — those are not the same defect, and only
        # the first one strands a car that drives where the street actually is.
        authored_half = float(edge["width_m"]) / 2.0
        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            half = half_width_at(widths.get(edge_id, []), vertex)
            drawn_offset_m = offset_at(drawn_offset_by_edge.get(edge_id, []), vertex)
            for x, z, span, cell_offset_m in cross_section(
                station[[0, 2]], normal, half, across_m, drawn_offset_m
            ):
                # The drawn road first, because the question is what stands in
                # *what is drawn*. Falling back to the graph's own y would ask
                # about a surface that may never have been built.
                found_y = nearest(drawn.heights_at(x, z), float(station[1]), attribute_within_m)
                edges.append(edge_id)
                levels.append(level)
                stations.append(station_id)
                xs.append(x)
                zs.append(z)
                spans.append(span)
                # 🔴 **Taken from `cross_section` rather than rebuilt.** It is
                # the distance from the CENTRELINE — the frame `authored_half`
                # and "the centreline cell" below are in — and it now has two
                # terms, so a caller re-deriving one of them puts `offset == 0`
                # wherever the paint happens to be rather than on the road's
                # published centre. That is `Q106`'s defect at this seam.
                offsets.append(cell_offset_m)
                authored.append(authored_half)
                # NaN, not a sentinel height: "no road drawn here" is a junction
                # trim or a stale width table, and it has to stay distinguishable
                # from a road at y = 0 rather than quietly leave the denominator.
                surfaces.append(float("nan") if found_y is None else found_y)
            station_id += 1

    return Lattice(
        edge=np.asarray(edges, dtype=np.int32),
        level=np.asarray(levels, dtype=np.int8),
        station=np.asarray(stations, dtype=np.int32),
        x=np.asarray(xs, dtype=np.float64),
        z=np.asarray(zs, dtype=np.float64),
        span=np.asarray(spans, dtype=np.float64),
        offset=np.asarray(offsets, dtype=np.float64),
        authored_half=np.asarray(authored, dtype=np.float64),
        surface_y=np.asarray(surfaces, dtype=np.float64),
        spacing_m=spacing_m,
    )


def band_map(lattice: Lattice) -> dict[tuple[int, int], tuple[float, float]]:
    """Coarse plan cell to the height band any carriageway in it could be occupied at.

    The prune's whole input. Built from the same lattice `survey` consumes, so
    nothing it covers can be missing from what the survey asks about.
    """
    drawn = lattice.drawn
    if not drawn.any():
        return {}
    keys = np.floor(np.stack([lattice.x[drawn], lattice.z[drawn]], axis=1) / COARSE_CELL_M)
    keys = keys.astype(np.int64)
    low = lattice.surface_y[drawn] + BUMPER_LOW_M
    high = lattice.surface_y[drawn] + BUMPER_HIGH_M

    coarse: dict[tuple[int, int], tuple[float, float]] = {}
    for (column, row), band_low, band_high in zip(map(tuple, keys), low, high, strict=True):
        key = (int(column), int(row))
        seen = coarse.get(key)
        coarse[key] = (
            (float(band_low), float(band_high))
            if seen is None
            else (min(seen[0], float(band_low)), max(seen[1], float(band_high)))
        )
    return coarse


def survey(
    lattice: Lattice,
    classes: dict[str, Occupied],
    *,
    corridor_levels: tuple[int, ...] = CORRIDOR_LEVELS,
) -> Survey:
    """Ask every drawn carriageway cell what stands in it.

    ⚠️ `corridor_levels` reaches the corridor half alone. The area half folds
    every walked level in regardless and always has — `Survey.add` is keyed by
    level — so widening this changes which edges get a *corridor* and changes
    no share.
    """
    found = Survey()
    found.asked = lattice.asked

    # One list, not a `blocked` flag beside it: the flag was `standing is not
    # None` appended in the same breath, so the two were one fact in two
    # encodings kept in step by nothing but the order of two lines.
    standing_at: list[str | None] = []
    inside: list[bool] = []
    # Index-aligned with `standing_at`, and appended in the same breath for the
    # reason its neighbour above gives: the alignment is the whole contract, and
    # `zip(..., strict=True)` below is what holds it.
    offset_at: list[float] = []
    station_span = 0.0
    station_cells = 0
    current = -1
    current_edge = -1
    current_level = 0
    # Where a failing station is *reported*, and it has to be the centreline
    # rather than whichever cell happened to be walked last: a rim cell is half
    # the drawn width away, which on a widened arterial is 5 m of "go and look
    # here".
    seen_x = seen_z = 0.0
    seen_offset = float("inf")

    def close_station() -> None:
        # The corridor is a level-0 question *by default*. An off-grade ribbon
        # nobody can reach cannot strand a traffic car, and `Q21`/`Q22` own its
        # defects — but `P4-1` opens that network, and `--levels` is how the
        # corridor up there is measured before it does (`Q103`).
        if current_level not in corridor_levels or not standing_at:
            return
        found.corridor_stations += 1

        # ⚠️ **A trimmed cross-section cannot be judged, and judging one anyway
        # invents blocked edges.** Cells with no road drawn are not recorded at
        # all, so at a junction trim the corridor would be measured across
        # whatever few cells survived — one clear cell out of twenty reads
        # as a 0.49 m corridor and condemns the edge. Measured on Wan Chai before
        # this guard: 44 edges failed, and seven of the eight tightest sat at
        # exactly one cell's width, which is the artefact rather than a wall.
        if _trimmed(len(standing_at), station_cells):
            found.corridor_skipped += 1
            return
        blocked = [name is not None for name in standing_at]
        clear = _clear_run(blocked, station_span)
        found.corridor_profile.setdefault(current_edge, []).append(clear)
        found.corridor_level[current_edge] = current_level
        if clear < found.corridor_m.get(current_edge, float("inf")):
            found.corridor_m[current_edge] = clear
            found.corridor_at[current_edge] = (seen_x, seen_z)
            found.corridor_span_m[current_edge] = station_span
            found.corridor_authored_m[current_edge] = _clear_run(
                [wall for wall, within in zip(blocked, inside, strict=True) if within],
                station_span,
            )
            # ⚠️ Read off `offset_at` rather than the walk's own `seen_offset`.
            # That one tracks the min-offset cell over **every** walked cell,
            # including the undrawn ones it exists to send a reader to; this
            # list holds only the judged cells, and the two are not aligned.
            verdict = _centreline_verdict(standing_at, offset_at, station_span)
            if verdict is not None:
                found.corridor_centre[current_edge] = verdict
            # Recorded at the binding station and nowhere else. An edge's
            # blocker is a fact about the cross-section that condemned it, not
            # about the edge: a street can meet a flyover pier at one end and a
            # shopfront at the other, and averaging the two would name neither.
            #
            # The cell counts order the names and are then dropped: they are a
            # fact about one cross-section, where the extent that separates the
            # two fix families is measured *along* the edge and is reported as
            # `starved` / `worst run`. Ordered rather than `most_common()` —
            # that breaks a tie by insertion order, which is the order cells
            # were walked across the section, and the listing has to be stable.
            tally = Counter(name for name in standing_at if name is not None)
            found.corridor_blockers[current_edge] = tuple(
                name for name, _ in sorted(tally.items(), key=lambda item: (-item[1], item[0]))
            )

    for i in range(lattice.asked):
        station = int(lattice.station[i])
        if station != current:
            close_station()
            standing_at = []
            inside = []
            offset_at = []
            station_cells = 0
            seen_offset = float("inf")
            current = station
            current_edge = int(lattice.edge[i])
            current_level = int(lattice.level[i])
        station_cells += 1
        station_span = float(lattice.span[i])
        # Converted once. Three readers want it now — the reporting position
        # below, the authored-width flag and the centreline list — and a numpy
        # scalar unbox is not free 1.1 M times over.
        offset = float(lattice.offset[i])
        if abs(offset) < seen_offset:
            seen_offset = abs(offset)
            seen_x, seen_z = float(lattice.x[i]), float(lattice.z[i])

        surface_y = lattice.surface_y[i]
        if not np.isfinite(surface_y):
            # Counted so it cannot quietly leave the denominator.
            found.no_road += 1
            continue
        found.measured += 1

        x, z = float(lattice.x[i]), float(lattice.z[i])
        low, high = float(surface_y) + BUMPER_LOW_M, float(surface_y) + BUMPER_HIGH_M
        standing = next(
            (name for name, index in classes.items() if index.in_band(x, z, low, high)),
            None,
        )
        found.add(current_level, standing, float(lattice.span[i]) * lattice.spacing_m)
        standing_at.append(standing)
        inside.append(abs(offset) <= float(lattice.authored_half[i]))
        offset_at.append(offset)
    close_station()

    return found


def occupier_walk(
    lattice: Lattice,
    classes: dict[str, Occupied],
    edge_id: int,
) -> list[Standing]:
    """Re-ask one edge's cells what stands in them, keeping the heights.

    ⚠️ **A second reading of the same cells, and not a second walk.** It indexes
    the `Lattice` the survey consumed and queries the same pruned `classes`, so
    it cannot reach a cell the corridor half did not, and the occupancy test is
    `band_extent(...) is not None` — pinned equal to `in_band` by test. What is
    new is the *heights*, which `Survey` has no field for because the corridor
    question is answered in plan.

    ⚠️ Asked only for edges the reader names on the command line, which is why
    looping the whole lattice per edge is affordable — `np.flatnonzero` cuts it
    to that edge's few thousand cells before any Python runs.
    """
    rows: list[Standing] = []
    cells = judged = 0
    names: set[str] = set()
    occupied: list[tuple[float, float]] = []
    base = float("inf")
    top = float("-inf")
    current = -1

    def close() -> None:
        if current < 0:
            return
        # Contiguous occupied runs, in walk order across the section. The list
        # is already ordered because `cross_section` emits left rim inward, so
        # neighbouring cells are adjacent by construction.
        rows.append(
            Standing(
                cells=cells,
                judged=judged,
                occupier=" + ".join(sorted(names)) if names else None,
                bands=tuple(occupied),
                base_m=base if names else float("nan"),
                top_m=top if names else float("nan"),
            )
        )

    for i in np.flatnonzero(lattice.edge == edge_id):
        station = int(lattice.station[i])
        if station != current:
            close()
            cells = judged = 0
            names = set()
            occupied = []
            base, top = float("inf"), float("-inf")
            current = station

        cells += 1
        surface_y = lattice.surface_y[i]
        if not np.isfinite(surface_y):
            continue
        judged += 1
        x, z = float(lattice.x[i]), float(lattice.z[i])
        low, high = float(surface_y) + BUMPER_LOW_M, float(surface_y) + BUMPER_HIGH_M
        offset, span = float(lattice.offset[i]), float(lattice.span[i])

        found = next(
            (
                (name, extent)
                for name, index in classes.items()
                if (extent := index.band_extent(x, z, low, high)) is not None
            ),
            None,
        )
        if found is None:
            continue
        name, (column_low, column_high) = found
        names.add(name)
        base = min(base, column_low - float(surface_y))
        top = max(top, column_high - float(surface_y))

        # Extended rather than appended where this cell continues the last run.
        # The rim-inward walk means "continues" is decidable from the offsets
        # alone — no cell can arrive out of order.
        left, right = offset - 0.5 * span, offset + 0.5 * span
        if occupied and abs(occupied[-1][1] - left) < 1e-9:
            occupied[-1] = (occupied[-1][0], right)
        else:
            occupied.append((left, right))
    close()

    return rows


def _standing_runs(walk: list[Standing]) -> list[tuple[Standing, int]]:
    """Consecutive stations that read alike, run-length encoded in walk order.

    ⚠️ **Grouped on the occupier and its across-position, never on the height
    columns.** Those drift by centimetres between neighbouring stations — the
    deck is not flat — so folding them into the key prints one line per station
    and buries the reading. They are reduced over each run instead, which is
    `_profile_runs`' round-then-group rule meeting a tuple.
    """

    def key(station: Standing) -> tuple[Any, ...]:
        return (
            station.trimmed,
            station.occupier,
            tuple((round(low, 2), round(high, 2)) for low, high in station.bands),
        )

    runs: list[tuple[Standing, int]] = []
    for station in walk:
        if runs and key(runs[-1][0]) == key(station):
            last, count = runs[-1]
            runs[-1] = (
                Standing(
                    # 🔴 **Carried from the head, never reduced across the run.**
                    # `trimmed` is a *ratio* over these two and it is in the key
                    # above, so every member of a run already shares its verdict
                    # — but reducing them independently invents a third ratio
                    # that belongs to no station. `max(cells)` beside
                    # `min(judged)` read 19/25 over stations of 19/20 and 24/25
                    # and flipped a run of three JUDGED stations to `trimmed`,
                    # printing "not judged" over cross-sections that were. The
                    # head's own pair is the one that decided the verdict the
                    # key grouped on, and nothing prints these two directly.
                    cells=last.cells,
                    judged=last.judged,
                    occupier=last.occupier,
                    bands=last.bands,
                    # ⚠️ Plain `min`/`max`, and that is safe **because an
                    # unoccupied station has empty `bands`**: it can never share
                    # a key with an occupied one, so these never see a real
                    # number beside its NaN. `np.fmin`/`fmax` were written here
                    # to guard that mix and the mutation could not be made to
                    # fail a test — the state is unreachable twice over, and an
                    # unreachable guard reads as a hazard someone has handled.
                    # `occupier` is in the key for a different reason: two
                    # classes standing at the same offsets are two runs.
                    base_m=min(last.base_m, station.base_m),
                    top_m=max(last.top_m, station.top_m),
                ),
                count + 1,
            )
        else:
            runs.append((station, 1))
    return runs


def _covers_centreline(station: Standing) -> bool:
    """Does an occupied stretch of this cross-section contain the centreline?

    ⚠️ **Asked of the stretches, never of their hull.** `Standing.bands` says why
    a `min .. max` is the wrong shape, and this is the reading that would be
    wrongest under it: a cross-section blocked at both rims spans the centreline
    without anything standing on it.
    """
    return any(low <= 0.0 <= high for low, high in station.bands)


def _closest_approach(walk: list[Standing]) -> float:
    """How near the centreline the occupier gets anywhere along the edge.

    `inf` where nothing stands on the edge at all, on `Centreline.nearest`'s
    rule: 0.0 would read as "it is right here", which is the one answer that
    must not be manufactured.
    """
    return min(
        (
            0.0 if low <= 0.0 <= high else min(abs(low), abs(high))
            for station in walk
            for low, high in station.bands
        ),
        default=float("inf"),
    )


def _levels_label(levels: tuple[int, ...]) -> str:
    """The levels as one token, so a log line and a refusal spell them alike.

    Signed, because an elevation level's sign is its whole meaning here. Written
    out for `_levels_argument`'s reason rather than to save four joins: the same
    run was printing `+0,+1` in one line and `0,1` in another.
    """
    return ",".join(f"{level:+d}" for level in levels)


def edges_label(edges: tuple[int, ...]) -> str:
    """Edge ids as one token, in the `e208` spelling every listing here prints.

    `_levels_label`'s reason: a refusal and a log line spelling the same set two
    ways costs the reader the match.
    """
    return ",".join(f"e{edge_id}" for edge_id in edges)


def _levels_argument(text: str) -> tuple[int, ...]:
    """`--levels 0,1` as a tuple, refusing what would measure nothing.

    ⚠️ **Negative levels are refused, and not because they are uninteresting.**
    `walk_carriageway` skips them, and pulling them in would add their area to
    `drawn_share`'s denominator — which is `sum(area_m2.values())` across every
    level — so the two *gated* level-0 bars would read looser for no reason but
    a choice of divisor. That is the move `drawn_share`'s own docstring exists
    to refuse. Measuring under the terrain needs the denominator separated from
    the walked population first, which is a change to a gated instrument and
    wants its own argument; `Q21` owns the question meanwhile.
    """
    levels: list[int] = []
    for piece in text.split(","):
        piece = piece.strip()
        if not piece:
            # This is also what catches `--levels ""`: `"".split(",")` is `[""]`,
            # so an empty set never survives to be checked for afterwards. An
            # empty one would judge no corridor and then report that every edge
            # keeps a lane clear — the empty set reading as agreement, which is
            # the trap `pipeline/clearance.py` refuses at the sibling flag.
            raise argparse.ArgumentTypeError("--levels takes comma-separated integers")
        try:
            level = int(piece)
        except ValueError:
            raise argparse.ArgumentTypeError(f"--levels: '{piece}' is not an integer") from None
        if level < 0:
            raise argparse.ArgumentTypeError(
                f"--levels: {level} is below the terrain, which this tool's walk does not "
                "cover and whose area would move the gated shares' denominator — see "
                "_levels_argument"
            )
        if level not in levels:
            levels.append(level)
    if 0 not in levels:
        # 🔴 **The flag is strictly ADDITIVE, and this is why.** The corridor
        # gate reads the level-0 rows alone — an off-grade edge is graded and
        # never gated (`Q57`) — so a set that omits 0 leaves that gate with an
        # empty population and it passes for having stopped looking. Measured,
        # not argued: `--levels 1` on this bundle printed "Within the accepted
        # bounds." while 21 level-0 edges were starved. That is the empty set
        # reading as agreement again, reachable past the unmapped-level guard
        # because level 1 *is* mapped, and `deck_error`'s fourth defect is the
        # same shape — a denominator that shrinks when the thing it measures
        # breaks. Widening the corridor is a measurement; narrowing it below
        # what the bars were written against is a way to get a green run.
        raise argparse.ArgumentTypeError(
            "--levels must include 0: the corridor gate is written against level 0 and "
            "judges nothing without it, so omitting it would pass by not looking"
        )
    return tuple(sorted(levels))


def edges_argument(text: str) -> tuple[int, ...]:
    """`--probe-edges e208,e306` as a tuple, in the spelling the listings print.

    A bare integer is accepted too, because half the tables in this repo print
    `e208` and the graph's own field is `208`, and a reader retyping one from
    the other should not have to know which.

    ⚠️ Order is **kept**, unlike `--levels`. The reader chose it, the report is
    a listing rather than a set, and sorting it would silently rearrange a
    comparison someone lined up deliberately.
    """
    edges: list[int] = []
    for piece in text.split(","):
        piece = piece.strip()
        if not piece:
            # `"".split(",")` is `[""]`, so this is also what catches an empty
            # flag — `_levels_argument` says more about why that matters.
            raise argparse.ArgumentTypeError("--probe-edges takes comma-separated edge ids")
        try:
            edge_id = int(piece.removeprefix("e"))
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"--probe-edges: '{piece}' is not an edge id — write e208 or 208"
            ) from None
        if edge_id not in edges:
            edges.append(edge_id)
    return tuple(edges)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        parents=[bundle_arguments()],
        description="Whether solid geometry stands in the drawn carriageway (Q19).",
    )
    parser.add_argument(
        "--spacing-m", type=float, default=SPACING_M, help="station spacing along an edge"
    )
    parser.add_argument(
        "--across-m", type=float, default=ACROSS_M, help="cell width across the ribbon"
    )
    parser.add_argument(
        "--index-cell-m",
        type=float,
        default=INDEX_CELL_M,
        # A sweep knob, not a tuning knob. The shipped default stays coarse for
        # the reason the constant's comment gives; this exists so the gap against
        # `clearance.py` can be *priced* — see `Q51` — rather than argued about.
        help="plan cell the occupier index bins at (the dominant error term)",
    )
    parser.add_argument(
        "--sample-m",
        type=float,
        default=SAMPLE_M,
        # Fine enough that a wall crossing one `--across-m` cell puts several
        # samples in the 1.7 m band, coarse enough that the lowest storey of the
        # region is a few million points rather than a few hundred million.
        help="how densely each occupier triangle's surface is sampled",
    )
    parser.add_argument(
        "--corridor-report",
        action="store_true",
        # Opt-in, and the default listing above is untouched by it. `Q19`'s
        # history is a record of readers diffing that table across dates, and
        # this prints a block per failing edge. `facade_survey.py`'s
        # `--filler-report` is the precedent — `Q55`'s sweep, in the tool it
        # grades, behind a flag.
        help="print Q19's corridor profile and centreline query per failing edge",
    )
    parser.add_argument(
        "--levels",
        type=_levels_argument,
        default=CORRIDOR_LEVELS,
        # The corridor half only, and report-only off the default: an off-grade
        # edge is graded, never gated, for the reason the gate block below
        # gives. `pipeline/clearance.py`'s `--levels` is the same knob at the
        # other instrument and `Q51`'s ratchet is why they move together.
        help=(
            "comma-separated elevation levels to judge a corridor on "
            "(default: 0,1 — the levels the bundle publishes; only 0 is gated)"
        ),
    )
    parser.add_argument(
        "--probe-edges",
        type=edges_argument,
        default=(),
        # Named edges, never a filter over a population this tool decided: see
        # `occupier_report`, which says in red why a third report gets its own
        # function rather than a section inside either of the two above.
        help=(
            "comma-separated edge ids to walk station by station, reporting what stands "
            "in each cross-section and how high (default: none)"
        ),
    )
    parser.add_argument(
        "--accept-building-share",
        type=float,
        default=0.0172,
        # `Q19`'s own published figure, fixed before this grader existed.
        # `Q47`'s precedent: a bar the instrument cannot have been tuned to,
        # because it predates the instrument.
        help="fail above this share of level-0 carriageway area occupied by buildings",
    )
    parser.add_argument(
        "--accept-infrastructure-share",
        type=float,
        default=0.0160,
        help="fail above this share of level-0 carriageway area occupied by structure",
    )
    parser.add_argument(
        "--accept-corridor-lanes",
        type=float,
        default=1.0,
        # In lanes rather than metres so the criterion travels to the next city
        # with its own `lane_width_m`, and so the number reads as the thing it
        # means: a car needs a lane.
        help="every drivable level-0 edge must keep this many lanes clear",
    )
    parser.add_argument(
        "--accept-coverage",
        type=float,
        default=0.90,
        # `deck_error`'s fourth defect, refused here by construction: a tool
        # whose denominator shrinks when the thing it measures breaks will
        # report a pass for having stopped looking.
        help="fail below this share of asked cells actually measured",
    )
    args = parser.parse_args(argv)

    city = load_config()

    unmapped = sorted(set(args.levels) - set(city.elevation_levels))
    if unmapped:
        # 🔴 **An unmapped level judges no edge and then reports a clear region.**
        # Every counter closes, the corridor listing is empty and the run ends
        # "every drivable level-0 edge keeps a lane clear" — the empty set
        # reading as agreement. `pipeline/clearance.py` refuses this at the
        # sibling flag and the trap is the same one here.
        raise SystemExit(
            f"--levels names level {_levels_label(tuple(unmapped))}, which "
            f"{city.name}'s elevation_levels does not map "
            f"({_levels_label(tuple(sorted(city.elevation_levels)))})"
        )
    manifest, tiles = load_bundle(args.generated, args.lod)

    # ⚠️ Named by the config, never guessed from `class_materials`' iteration
    # order. `terrain_class` is a **required** field (`pipeline/config.py`) and
    # `ground_clearance.py` reads it directly; picking "the first non-structure
    # key" instead is dict-order-dependent and yields nothing at all for a city
    # whose terrain takes height-banded colours rather than a flat material.
    ground_class = city.buildings.terrain_class

    log_bundle(manifest, args.lod)
    log.info("carriageway occupancy, lod %d", args.lod)
    log.info(
        "  occupied means class surface %.2f-%.2f m above the drawn road, "
        "binned in %.2f m plan cells",
        BUMPER_LOW_M,
        BUMPER_HIGH_M,
        args.index_cell_m,
    )

    # Read once, used by everything below: the graph feeds the walk and the
    # street names, and the road mesh index feeds the walk alone. Both were
    # rebuilt per pass before the walk was unified.
    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    # Before the walk, so a mistyped edge id costs a second rather than the run.
    refuse_unprobeable(graph, args.probe_edges, args.levels)
    drawn = drawn_surface(args.generated, manifest)

    # The walk sizes the question — where is carriageway, and at what height
    # could it be occupied — and *records* it, so the occupier index is pruned
    # to exactly the cells the survey will go on to ask about.
    lattice = walk_carriageway(
        graph,
        manifest,
        drawn,
        spacing_m=args.spacing_m,
        across_m=args.across_m,
        attribute_within_m=args.attribute_within_m,
    )
    if not lattice.drawn.any():
        raise SystemExit(
            "no drawn carriageway could be found — is the road mesh present, and does "
            "city.json still name it?"
        )
    bands = band_map(lattice)
    structure_class = class_predicates(city)[0]

    log.info("")
    log.info("  indexing occupier surfaces near the carriageway:")
    classes = index_classes(
        city,
        args.generated,
        manifest,
        tiles,
        bands,
        sample_m=args.sample_m,
        cell_m=args.index_cell_m,
    )
    for name, index in classes.items():
        log.info(
            "    %-16s %7d of %7d triangles reach the band, %9d surface samples",
            name,
            index.triangles_kept,
            index.triangles_seen,
            index.samples,
        )
    log.info("    %-16s excluded — that is Q24, and ground_clearance.py grades it", ground_class)

    found = survey(lattice, classes, corridor_levels=args.levels)

    lane_m = float(city.roads.lane_width_m)
    corridor_bar_m = lane_m * args.accept_corridor_lanes
    # Both derived from `graph` once and handed to both reports, rather than
    # each rebuilding its own: `road_names` was already hoisted, and a second
    # report made `plan_lengths` the odd one out.
    names = road_names(graph)
    lengths = plan_lengths(graph)

    log.info("")
    log.info("  share of ALL drawn carriageway with geometry standing in it — Q19's frame,")
    log.info("  so these sum to its 5.17%% headline and the gates below read against them:")
    drawn_total = sum(found.area_m2.values())
    running = 0.0
    for level in sorted(found.area_m2):
        parts = " · ".join(
            f"{name} {100.0 * found.drawn_share(level, name):6.3f}%" for name in sorted(classes)
        )
        subtotal = sum(found.drawn_share(level, name) for name in classes)
        running += subtotal
        log.info(
            "    level %+d   %s   = %6.3f%%   (%.0f m2 drawn, %.1f%% of all)",
            level,
            parts,
            100.0 * subtotal,
            found.area_m2[level],
            100.0 * found.area_m2[level] / drawn_total,
        )
    log.info("    %-56s   total %6.3f%%", "", 100.0 * running)
    if any(level != 0 for level in found.area_m2):
        log.info("    level +1 and above is reported, never gated — Q21/Q22 and Phase 4 own it")

    log.info("")
    log.info("  the same, against each level's own area — informative, never gated:")
    for level in sorted(found.area_m2):
        parts = " · ".join(
            f"{name} {100.0 * found.share(level, name):6.3f}%" for name in sorted(classes)
        )
        log.info("    level %+d   %s", level, parts)

    log.info("")
    log.info(
        "  narrowest clear corridor per drivable edge on level(s) %s, against %.2f m (%.1f lane):",
        _levels_label(args.levels),
        corridor_bar_m,
        args.accept_corridor_lanes,
    )
    log.info("    'authored' is the same station measured inside the un-widened width")
    # ⚠️ Every width below is a *lower bound*, and the two resolutions say how
    # loose a bound. `cell` is the plan bin, which blocks in full on one sample
    # and so smears a wall by up to a cell either side; `step` is the across
    # spacing, which is what the width is counted in. `Q51`'s 26-against-21 was
    # measured to the first of these — quoting a width without them reads as a
    # measurement when it is an upper bound on the blockage.
    log.info(
        "    each width is an integer number of 'step' cells and a LOWER bound: "
        "the %.2f m plan bin blocks in full on one sample",
        args.index_cell_m,
    )
    # ⚠️ **Every failing edge, not the tightest handful.** This listing was
    # capped at eight, and `Q19` then spent two corrections on a population it
    # could only ever see the top of — "the building half is uniformly mild" was
    # a reading of the first rows of this table, and it was false. The fix
    # families the entry now needs cannot be told apart from a sample.
    below_bar = sorted(
        ((edge_id, clear) for edge_id, clear in found.corridor_m.items() if clear < corridor_bar_m),
        key=lambda item: item[1],
    )
    # 🔴 **Two populations, and they are never pooled** (`Q57`) — see
    # `split_by_level`, which is a named function rather than four lines here so
    # that the one place a widened walk could reach the gate has tests.
    starved, off_grade = split_by_level(below_bar, found.corridor_level)
    # `starved` is how much of the edge is below the bar and `worst run` is the
    # longest unbroken stretch of it — the pair that separates `Q19`'s two fix
    # families. A wall crossing the street blocks a metre or two and clears
    # again, and the road passes under a building the source extruded shut; a
    # frontage standing in the carriageway blocks a continuous run. They do not
    # share a fix, and the corridor figure alone cannot tell them apart.
    log.info(
        "    %-6s %3s %7s %9s %6s  %-22s %8s %9s  %-18s  %s",
        "edge",
        "lvl",
        "clear",
        "authored",
        "step",
        "blocked by",
        "starved",
        "worst run",
        "station",
        "road",
    )
    for edge_id, clear in below_bar:
        x, z = found.corridor_at[edge_id]
        starved_m, worst_run_m = _starved_shape(
            found.corridor_profile[edge_id], corridor_bar_m, lattice.spacing_m
        )
        log.info(
            "    e%-5d %+3d %7.2f %9.2f %6.2f  %-22s %6.0f m %7.0f m  (%7.1f, %7.1f)  %s",
            edge_id,
            found.corridor_level[edge_id],
            clear,
            found.corridor_authored_m.get(edge_id, float("nan")),
            found.corridor_span_m.get(edge_id, float("nan")),
            "+".join(found.corridor_blockers[edge_id]),
            starved_m,
            worst_run_m,
            x,
            z,
            names.get(edge_id, "unnamed"),
        )
    if not starved:
        log.info("    every drivable level-0 edge keeps a lane clear")
    off_grade_levels = tuple(level for level in args.levels if level != 0)
    if off_grade_levels:
        # 🔴 **Asked of the LEVELS WALKED, never of whether they are the
        # default.** Written as `args.levels != CORRIDOR_LEVELS` this line said
        # nothing on a default run — which was right while the default was
        # level 0 alone and became exactly backwards the moment it was not,
        # silencing the warning on every run that now carries off-grade rows.
        # Said out loud rather than left to the `lvl` column, because the whole
        # risk of a widened run is a reader carrying an off-grade figure to a
        # level-0 bar.
        # ⚠️ **Not "of those"**: the line above it prints only when level 0 is
        # clean, so with the default now `(0, 1)` a bundle starved off-grade and
        # clear at grade would hang the phrase on nothing.
        log.info(
            "    %d edges below the bar are off-grade (level %s) — REPORTED, never gated: "
            "only level 0 is judged against --accept-corridor-lanes",
            len(off_grade),
            _levels_label(off_grade_levels),
        )
    log.info(
        "    %d edges judged from %d stations; %d stations too trimmed to judge",
        len(found.corridor_m),
        found.corridor_stations,
        found.corridor_skipped,
    )

    if args.corridor_report:
        corridor_report(
            found,
            lengths,
            names,
            # 🔴 **`starved`, not `below_bar`** — `Q19`'s report is a level-0
            # question end to end: its header says "starved edges", its length
            # line says "all judged level-0", and its building/structure split
            # is `Q19`'s own two fix families. Handing it the widened population
            # pools the two (`Q57`) and makes three of its labels false.
            starved,
            spacing_m=args.spacing_m,
            index_cell_m=args.index_cell_m,
            structure_class=structure_class,
        )
        # Its own function and its own population, for the reason that one
        # states in red. ⚠️ **It goes quiet on an empty population and not on a
        # flag** — `off_grade_report` returns early when nothing off-grade was
        # judged — which is what let the default move under it without this
        # call site changing.
        off_grade_report(
            found,
            graph,
            lengths,
            names,
            off_grade,
            spacing_m=args.spacing_m,
            index_cell_m=args.index_cell_m,
            structure_class=structure_class,
        )

    # Independent of `--corridor-report`: that flag prints `Q19`'s two reports
    # over populations this tool chose, and this one answers for edges the
    # reader named. Gating it behind that would make a diagnostic depend on a
    # listing it has nothing to do with.
    occupier_report(
        found,
        lattice,
        classes,
        graph,
        lengths,
        names,
        args.probe_edges,
        levels=args.levels,
        spacing_m=args.spacing_m,
        index_cell_m=args.index_cell_m,
    )

    log.info("")
    log.info(
        "  %d cells asked, %d measured (%.1f%%), %d with no road drawn",
        found.asked,
        found.measured,
        100.0 * found.coverage,
        found.no_road,
    )

    problems = []
    if starved:
        named = ", ".join(
            f"e{edge_id} {clear:.2f} m ({names.get(edge_id, 'unnamed')})"
            for edge_id, clear in starved[:6]
        )
        rest = len(starved) - 6
        problems.append(
            f"{len(starved)} drivable level-0 edges keep less than {corridor_bar_m:.2f} m "
            f"clear — a traffic car cannot pass: {named}"
            + (f", and {rest} more listed above" if rest > 0 else "")
        )
    # ⚠️ Buildings and landmarks are gated **together** against the one building
    # bar. `Q19` measured 1.72% while HKCEC was still a tile; `P3-6` moved it to
    # `landmarks.json` afterwards. Scoring the two separately would compare a
    # 2026-08 figure against a bundle that has since had its largest roadside
    # building taken out of the population, and the bar would silently loosen.
    for names_gated, bar in (
        ((BUILDING, LANDMARK), args.accept_building_share),
        ((structure_class,), args.accept_infrastructure_share),
    ):
        share = sum(found.drawn_share(0, name) for name in names_gated)
        if share > bar:
            problems.append(
                f"{100.0 * share:.3f}% of all drawn carriageway has {'+'.join(names_gated)} "
                f"standing in it at grade, against {100.0 * bar:.3f}%"
            )
    if found.coverage < args.accept_coverage:
        problems.append(
            f"only {100.0 * found.coverage:.1f}% of asked cells could be measured, against "
            f"{100.0 * args.accept_coverage:.1f}% — the rest is not evidence of anything"
        )

    if problems:
        log.error("")
        for problem in problems:
            log.error("  FAIL  %s", problem)
        return 1

    log.info("")
    log.info("  Within the accepted bounds.")
    return 0


def landmark_occupiers(
    generated: Path,
    manifest: dict[str, Any],
    bands: dict[tuple[int, int], tuple[float, float]],
    sample_m: float,
    *,
    cell_m: float = INDEX_CELL_M,
) -> Occupied:
    """Hero buildings, which since `P3-6` are not in the tiles at all.

    ⚠️ **Without this the tool is blind exactly where the player starts.**
    `P3-6` gave `landmarks.json` an `excluded_bounds` and took HKCEC *out* of the
    shipped tiles, so a tile-only survey sees a hole where the largest building on
    Expo Drive used to be — and Expo Drive is where `RoadSpawn` puts the car. A
    reading that fell because a building stopped being a tile is not the
    carriageway getting clearer.

    No colour filter: a landmark is building geometry end to end, and it wears a
    hand-authored palette that matches none of the class rays anyway. Each asset
    is placed by its own `transform` — position and a yaw — because these ship
    unbaked, unlike the tiles whose vertices are already in world space.
    """
    entry = manifest.get("landmarks")
    if not entry:
        return Occupied(cells={}, triangles_kept=0, triangles_seen=0, samples=0, cell_m=cell_m)
    catalogue = json.loads((generated / entry).read_text())

    def blocks() -> Iterator[np.ndarray]:
        for landmark in catalogue.get("landmarks", []):
            asset = str(landmark["asset"])
            # `res://` is Godot's project root, which is `game/`. The bundle path
            # is the tools' handle on the same tree, and it is `game/assets/…`.
            path = generated.parent.parent / asset.removeprefix("res://")
            if not path.exists():
                raise SystemExit(
                    f"landmark '{landmark['id']}' names {asset}, which is not at {path}. "
                    "Rebuild the region, or sync the generated assets."
                )
            place = landmark.get("transform") or {}
            offset = np.asarray(place.get("pos", (0.0, 0.0, 0.0)), dtype=np.float64)
            # ⚠️ **`rot_y_deg` is a compass bearing, so it is applied negated**,
            # and getting this wrong is silent. Bearings run clockwise from north
            # while game north is -Z, so `generated_landmarks.gd` places a hero
            # with `Basis(Vector3.UP, deg_to_rad(-rot_y_deg))` and this has to
            # match it exactly or the tool measures a building the game draws
            # somewhere else. Written the obvious way first, and HKCEC's bearing
            # is 0.0 — so the error hid completely until Central Plaza, at 143.1,
            # was checked against the scene.
            yaw = np.radians(-float(place.get("rot_y_deg", 0.0)))
            cos, sin = float(np.cos(yaw)), float(np.sin(yaw))
            spin = np.array([[cos, 0.0, sin], [0.0, 1.0, 0.0], [-sin, 0.0, cos]])
            for mesh in read_glb(path):
                if not len(mesh.triangles):
                    continue
                corners = mesh.positions[mesh.triangles].astype(np.float64)
                yield corners @ spin.T + offset

    return index_corners(blocks(), bands, sample_m, cell_m=cell_m)


def plan_lengths(graph: dict[str, Any]) -> dict[int, float]:
    """Each edge's drawn length in plan, from the polyline the walk itself follows.

    Plan rather than 3D, and the difference is not academic on a flyover: every
    other figure this tool publishes is a plan measurement, and mixing a slope
    length into the partition below would make the structure half — which is
    where the gradients are — read longer than it is for the wrong reason.
    """
    lengths: dict[int, float] = {}
    for edge in graph["edges"]:
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        steps = np.diff(polyline[:, [0, 2]], axis=0)
        lengths[int(edge["id"])] = float(np.hypot(steps[:, 0], steps[:, 1]).sum())
    return lengths


def _side(offset_m: float) -> str:
    """The side a cell sits on, or that it has none.

    ⚠️ `Q19` reads the **sign** of this column to tell a whole-layer registration
    shift from fifteen unrelated sites, so a cross-section that is symmetric
    about its centreline has to say so rather than be assigned a side by the
    order the walk happened to visit cells in.
    """
    return "either side" if not np.isfinite(offset_m) else f"at {offset_m:+.2f} m"


def _median_and_min(values: list[float]) -> tuple[float, float]:
    """Median and minimum, or NaN for an empty group rather than a crash."""
    if not values:
        return float("nan"), float("nan")
    return float(np.median(values)), min(values)


def split_by_level(
    below_bar: list[tuple[int, float]], levels: dict[int, int]
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """The failing rows split into the population that is gated and the one that
    is only reported.

    🔴 **Two populations, and they are never pooled** (`Q57`). Level 0 is what
    the acceptance bars were written against and is what `main` gates on; an
    off-grade edge is a deck, not a street, and is *graded* — the same call
    `paint_clearance.py` makes for the tramway, and for the same reason a figure
    read against a bar it was not written for is one population's number on
    another's.

    ⚠️ **Lifted out of `main` so the partition can be tested without a bundle.**
    It is the one place a widened walk could reach the gate, and its mutations
    all leave every counter closing. `TestSplitByLevel` enumerates them.

    `levels` is `Survey.corridor_level`, and it is **indexed rather than
    `.get`**: every key here was put in `corridor_m` by the same `close_station`
    that set the level, so a missing one is an inconsistency to hear about
    rather than one to default into the gated population.
    """
    starved: list[tuple[int, float]] = []
    off_grade: list[tuple[int, float]] = []
    for row in below_bar:
        (starved if levels[row[0]] == 0 else off_grade).append(row)
    return starved, off_grade


def _edge_verdict(
    found: Survey,
    edge_id: int,
    name: str,
    length_m: float,
    *,
    note: str = "",
) -> None:
    """One edge's station profile and its centreline verdict.

    Shared by both reports below, and **this is presentation sharing, not the
    kind `Q57` forbids**: it pools no number, no denominator and no bar — every
    line it prints is about the single edge it was handed. The two callers keep
    their own populations, headers and framing, which is where the separation
    has to live.

    ⚠️ Trimmed stations are absent from the profile rather than recorded as
    clear — `corridor_profile`'s own declaration says so — so a short profile on
    a long edge is a junction trim, not a short street. `n` beside the length is
    what makes that visible instead of leaving it to be assumed.
    """
    profile = found.corridor_profile[edge_id]
    log.info(
        "    e%-5d %-28s %6.1f m over %3d judged stations%s",
        edge_id,
        name[:28],
        length_m,
        len(profile),
        note,
    )
    log.info(
        "      profile  %s",
        " · ".join(
            f"{clear:.1f}" + (f" x{count}" if count > 1 else "")
            for clear, count in _profile_runs(profile)
        ),
    )
    centre = found.corridor_centre.get(edge_id)
    if centre is None:
        log.info("      centre   no judged cell at the binding station")
    elif centre.occupier is None:
        log.info(
            "      centre   clear at offset %+.2f m; nearest occupier %.2f m away, %s",
            centre.centre_offset_m,
            centre.to_occupier_m,
            _side(centre.occupier_offset_m),
        )
    elif not np.isfinite(centre.to_clear_m):
        log.info(
            "      centre   %s at offset %+.2f m; the whole cross-section is blocked",
            centre.occupier,
            centre.centre_offset_m,
        )
    else:
        log.info(
            "      centre   %s at offset %+.2f m; first clear cell %.2f m away, %s",
            centre.occupier,
            centre.centre_offset_m,
            centre.to_clear_m,
            _side(centre.clear_offset_m),
        )


def _width_note(edge: dict[str, Any]) -> str:
    """The published width and what licensed it, as `_edge_verdict`'s trailer.

    Extracted on `_verdict_legend`'s own argument, one line later: it was
    byte-identical in two callers and a third was about to copy it again. A
    reworded note over an unchanged format is the drift that costs a reader the
    comparison between two reports of the same edge.
    """
    return f"  ·  {edge['width_source']} width {float(edge['width_m']):.2f} m"


def _verdict_legend() -> None:
    """The two lines that say how to read `_edge_verdict`'s output.

    Beside the printer they describe, because they were byte-identical in both
    reports and a reworded legend over an unchanged format is the drift that
    costs a reader the table.
    """
    log.info("    profile is every judged station's clear run in walk order, run-length encoded;")
    log.info("    'centre' is what stood on the centreline at the binding station, and its way out")


def _resolution_note(index_cell_m: float, spacing_m: float) -> None:
    """Both reports' closing line: every metre above is a bound, and how loose.

    Each caller keeps its own comment saying why it restates this; what they
    share is the sentence, which was duplicated verbatim down to its arguments.
    """
    log.info(
        "    widths are lower bounds at the %.2f m plan bin; the walk pitch is %.2f m",
        index_cell_m,
        spacing_m,
    )


def _blocker_split(found: Survey, rows: list[tuple[int, float]], structure_class: str) -> None:
    """What stood in one population's edges, tallied at their binding stations.

    ⚠️ Counted from `corridor_blockers`, so this is **the grader's own**
    population. `Q19` published a `1 LANDMARK` here that belongs to
    `tools/narrowing.py`'s — a different population, whose `e702` this grader
    passes at 3.41 m. An empty class is printed as 0 rather than omitted, or the
    next reader fills the gap from whichever table is to hand.

    Shared on `_edge_verdict`'s argument rather than `Q57`'s: it pools nothing
    between the two callers, it is handed one population at a time, and the
    three class names defaulting to 0 are the part most likely to drift if a
    fourth class is added to one report and not the other.
    """
    tally = Counter(" + ".join(found.corridor_blockers[edge_id]) for edge_id, _ in rows)
    for name in (BUILDING, LANDMARK, structure_class):
        tally.setdefault(name, 0)
    log.info(
        "    split     %s",
        " · ".join(f"{count} {name}" for name, count in sorted(tally.items())),
    )


def corridor_report(
    found: Survey,
    lengths: dict[int, float],
    names: dict[int, str],
    starved: list[tuple[int, float]],
    *,
    spacing_m: float,
    index_cell_m: float,
    structure_class: str,
) -> None:
    """`Q19`'s two decisive measurements, printed from the walk that already ran.

    Both were computed by scratch scripts that were never committed, which is
    `Q37`'s debt and `Q55`'s opened a third time — and this time under a finding
    the entry has reversed three times. The corridor profile is the shape that
    refuted "the ribbon is drawn wider than the gap it runs through"; the
    centreline query is what refused every remaining width candidate, because no
    width rule moves a centreline.

    ⚠️ **Reporting only.** Nothing here is gated, nothing here is measured that
    the default listing does not already measure, and the default listing is
    unchanged by design — this reads `Survey` and prints. `starved` is the
    listing's own population rather than a second selection over the same
    dictionary, so the two can never come to disagree about which edges fail.
    """
    log.info("")
    log.info(
        "  Q19 corridor report — %d starved edges, reporting only, nothing gated", len(starved)
    )

    _blocker_split(found, starved, structure_class)

    # The two halves separate by length, and `Q19` had that as a tendency when
    # it is a partition. Grouped by whether a *building* stands in the edge at
    # all, so the one mixed edge is counted with the half it belongs to rather
    # than dropped between the two.
    building_half = [
        edge_id
        for edge_id, _ in starved
        if {BUILDING, LANDMARK} & set(found.corridor_blockers[edge_id])
    ]
    structure_half = [edge_id for edge_id, _ in starved if edge_id not in set(building_half)]
    for label, group in (("building", building_half), ("structure", structure_half)):
        metres = [lengths[edge_id] for edge_id in group if edge_id in lengths]
        median, shortest = _median_and_min(metres)
        tightest = min(group, key=lambda e: lengths.get(e, float("inf")), default=None)
        log.info(
            "    length    %-9s half  n %2d  p50 %6.1f m  %2d under 20 m  min %5.1f m (e%s)",
            label,
            len(group),
            median,
            sum(1 for value in metres if value < 20.0),
            shortest,
            tightest,
        )
    # ⚠️ **Filtered to level 0, because the two halves above are.** `starved` is
    # the level-0 population by construction, so pooling every walked level into
    # the denominator they are read against compares `Q19`'s two fix families to
    # a population that contains decks (`Q57`). Under `--levels 0,1` this read
    # `n 782` beneath a label saying "all judged level-0"; it is 737.
    judged = [
        lengths[edge_id]
        for edge_id, level in found.corridor_level.items()
        if level == 0 and edge_id in lengths
    ]
    log.info(
        "    length    all judged level-0  n %3d  p50 %6.1f m   — what the two read against",
        len(judged),
        _median_and_min(judged)[0],
    )

    log.info("")
    _verdict_legend()
    for edge_id, _ in starved:
        _edge_verdict(
            found, edge_id, names.get(edge_id, "unnamed"), lengths.get(edge_id, float("nan"))
        )

    log.info("")
    _centreline_summary(found, building_half, "building")
    _centreline_summary(found, structure_half, "structure")
    log.info("    no width rule reaches a centreline: lanes, width_m and the floor all move")
    log.info("    the ribbon's edges, which is why narrowing.py clears nothing at any factor")
    # ⚠️ Stated here rather than left to the reader: every metre above is a
    # bound. The widths are lower bounds at the plan bin (see INDEX_CELL_M) and
    # the extents are upper bounds at the walk pitch (see `_starved_shape`).
    _resolution_note(index_cell_m, spacing_m)


def _centreline_summary(found: Survey, group: list[int], label: str) -> None:
    """How many of one half are condemned on the centreline itself, and by what."""
    judged = [
        centre for edge_id in group if (centre := found.corridor_centre.get(edge_id)) is not None
    ]
    on_centreline = [centre for centre in judged if centre.occupier is not None]
    by_class = Counter(centre.occupier for centre in on_centreline)
    escaped = [f"{centre.to_occupier_m:.2f} m" for centre in judged if centre.occupier is None]
    log.info(
        "    centreline  %-9s half  occupied at the binding station on %2d of %2d  (%s)",
        label,
        len(on_centreline),
        len(judged),
        " · ".join(f"{count} {name}" for name, count in sorted(by_class.items())) or "none",
    )
    if escaped:
        # ⚠️ The exceptions are load-bearing, not a footnote. A centreline clear
        # by half a cell is not evidence for a width fix — it is the same defect
        # one bin over — and printing the margin is what stops it reading as a
        # clearance.
        log.info(
            "                %-9s       clear at the centre on %d, occupier %s away",
            "",
            len(escaped),
            " and ".join(escaped),
        )


def off_grade_report(
    found: Survey,
    graph: dict[str, Any],
    lengths: dict[int, float],
    names: dict[int, str],
    off_grade: list[tuple[int, float]],
    *,
    spacing_m: float,
    index_cell_m: float,
    structure_class: str,
) -> None:
    """The same per-station diagnosis for the edges that are graded, not gated.

    🔴 **A separate function, not a second section inside `corridor_report`.**
    That one's header says "starved edges", its length line says "all judged
    level-0" and its halves are `Q19`'s two level-0 fix families; handing it
    this population makes three of its labels false, which is why `main`'s call
    site says so in red. Keeping the two apart *structurally* is what stops the
    next edit re-merging them on the grounds that they print similar lines
    (`Q57`) — a deck's parapet is neither a shopfront in the carriageway nor a
    wall across it, and none of the three share a fix.

    ⚠️ **Reporting only, and there is deliberately no bar here.** An off-grade
    ribbon is `Q21`/`Q22`'s and `P4-1`'s; a figure from it read against
    `--accept-corridor-lanes` would be one population's number on another's.
    """
    if not off_grade:
        return
    # Indexed by id and read by field name, `centreline_error.py`'s shape. Every
    # id below came from `corridor_level`, which was built from these same
    # edges, so a miss is `split_by_level`'s "inconsistency to hear about"
    # rather than something to default past — and `load_bundle` refuses a
    # bundle whose schema could be missing the fields.
    published = {int(edge["id"]): edge for edge in graph["edges"]}
    # ⚠️ The levels that actually carry a failing row, which is **not** what
    # `main`'s line above spells: that one names the levels that were *asked
    # for*. `--levels 0,1,2` with failures on 1 alone prints both, honestly, and
    # this prints the one. Two different statements, deliberately.
    levels = tuple(sorted({found.corridor_level[edge_id] for edge_id, _ in off_grade}))

    log.info("")
    log.info(
        "  off-grade corridor report — %d edges below the lane bar on level %s, "
        "reporting only, nothing gated",
        len(off_grade),
        _levels_label(levels),
    )

    # Over **this** population, never the level-0 one.
    _blocker_split(found, off_grade, structure_class)

    # 🔴 What makes this population a different question from `Q19`'s. `Q103`
    # gave 36 of 45 level-1 edges a width from their own deck **and** a signed
    # offset onto its centre, so a residual on one of these is not the
    # registration that fix already made — it is something inside the deck's own
    # span, and a parapet stands on the deck.
    from_deck = sum(
        1 for edge_id, _ in off_grade if published[edge_id]["width_source"] == _DECK_SOURCE
    )
    centred_on_deck = sum(
        1 for edge_id, _ in off_grade if published[edge_id]["offset_source"] == _DECK_SOURCE
    )
    log.info(
        "    source    %d of %d width_source=deck · %d of %d offset_source=deck — Q103 already "
        "drew these at their deck's span and centred them on it",
        from_deck,
        len(off_grade),
        centred_on_deck,
        len(off_grade),
    )

    # ⚠️ **The listing's `authored` column carries no information here, and this
    # counter is what says so rather than a comment.** `floor_by_elevation_level`
    # gives an off-grade ribbon no widening, so the drawn half-width *is* half
    # the published width and the authored reading can only reproduce the clear
    # one. It is not asserted by construction — a level gaining a floor would
    # move this count, which is the test a counter here has to pass (`Q72`).
    degenerate = sum(
        1 for edge_id, clear in off_grade if abs(found.corridor_authored_m[edge_id] - clear) < 1e-9
    )
    log.info(
        "    authored  %d of %d rows read authored == clear, so the listing's authored column "
        "says nothing on this population and is not repeated below",
        degenerate,
        len(off_grade),
    )

    # Read against the edges at these levels, never against the 737 level-0 ones
    # `corridor_report` uses — that pooling is the defect the level filter there
    # exists to prevent, arriving from the other side.
    judged = [
        lengths[edge_id]
        for edge_id, level in found.corridor_level.items()
        if level in levels and edge_id in lengths
    ]
    log.info(
        "    length    all judged level %-6s n %3d  p50 %6.1f m   — what these read against",
        _levels_label(levels),
        len(judged),
        _median_and_min(judged)[0],
    )

    log.info("")
    _verdict_legend()
    for edge_id, _ in off_grade:
        edge = published[edge_id]
        _edge_verdict(
            found,
            edge_id,
            names.get(edge_id, "unnamed"),
            lengths.get(edge_id, float("nan")),
            note=_width_note(edge),
        )

    log.info("")
    # Restated rather than inherited from the block above by adjacency: these
    # are the same two resolutions, and a reader who scrolled to this section
    # has not necessarily read that one.
    _resolution_note(index_cell_m, spacing_m)
    log.info("    no bar is applied above — P4-1 owns what an off-grade corridor has to clear")


def refuse_unprobeable(
    graph: dict[str, Any], edges: tuple[int, ...], levels: tuple[int, ...]
) -> None:
    """Refuse a `--probe-edges` id that could never print a row.

    🔴 **Refused, never skipped.** An edge with nothing to print leaves a report
    silent about it, and silence here reads as "nothing is standing there" — the
    empty set as agreement, the trap `--levels` is refused for at the flag.

    ⚠️ **Called from `main` before the walk, not from `occupier_report` after
    it.** Both checks need only the graph, and left at the report they cost a
    mistyped id the whole 28-second walk and index before saying so. The
    unmapped-`--levels` refusal is hoisted to just after `load_config` for the
    same reason, and this is that shape at the next argument. The one check that
    genuinely needs the survey stays behind.
    """
    published = {int(edge["id"]): edge for edge in graph["edges"]}
    missing = [edge_id for edge_id in edges if edge_id not in published]
    if missing:
        raise SystemExit(
            f"--probe-edges names {edges_label(tuple(missing))}, which this region's "
            "road graph does not carry"
        )
    unjudged = [
        edge_id for edge_id in edges if int(published[edge_id]["elevation_level"]) not in levels
    ]
    if unjudged:
        raise SystemExit(
            f"--probe-edges names {edges_label(tuple(unjudged))}, whose level --levels "
            f"{_levels_label(levels)} does not judge — the walk would print stations with no "
            "corridor to explain them"
        )


def occupier_report(
    found: Survey,
    lattice: Lattice,
    classes: dict[str, Occupied],
    graph: dict[str, Any],
    lengths: dict[int, float],
    names: dict[int, str],
    edges: tuple[int, ...],
    *,
    levels: tuple[int, ...],
    spacing_m: float,
    index_cell_m: float,
) -> None:
    """What is standing on a named edge, station by station, across and in height.

    🔴 **A third report and its own function, on the two above's argument one
    level down.** Those answer a question about a *population* the tool decided —
    `corridor_report` the gated one, `off_grade_report` the graded one — and each
    prints one verdict per edge. This answers a question about the **stations of
    edges the reader named on the command line**, and prints many rows per edge.
    Folding it into either would give that one a population nobody measured
    (`Q57`), so the edges arrive through a flag and never through a filter.

    🔴 **Why it exists.** `Q103` diagnosed four blocked level-1 edges down to
    their binding station and stopped: *"the mechanism is not measured and is not
    guessed here"*. Every column it had was in **plan** — a corridor width, a
    centreline offset, a class — and the four candidate mechanisms it could not
    separate (a pier, a merge artefact, an adjacent deck, headroom) differ in
    **height** and in how the blockage **moves along the edge**. Both are read
    here, and `Q19`'s `e489` is the standing reminder that a horizontal
    instrument reports a headroom defect as 0.00 m of width and looks right.

    ⚠️ **Reporting only, and there is no bar** — the same last line both reports
    above carry. Nothing here is gated, nothing here is published, and an edge
    named on the command line is not a population anything could be graded
    against.
    """
    if not edges:
        return
    # Indexed rather than `.get`, because `refuse_unprobeable` has already run
    # against this same graph in `main` — a miss here is an inconsistency to
    # hear about, which is the call `split_by_level` makes.
    published = {int(edge["id"]): edge for edge in graph["edges"]}
    # ⚠️ A *third* reason an edge can have nothing to print, and not the same as
    # either above: its level was asked for and every station was still too
    # trimmed to judge, so `survey` recorded no profile and `_edge_verdict`
    # would raise on the lookup rather than say so. Short edges inside a
    # junction reach this.
    unprofiled = [edge_id for edge_id in edges if edge_id not in found.corridor_profile]
    if unprofiled:
        raise SystemExit(
            f"--probe-edges names {edges_label(tuple(unprofiled))}, which has no judged "
            "station — every cross-section was too trimmed for a corridor, so there is "
            "nothing for this walk to be read against"
        )

    log.info("")
    log.info(
        "  occupier walk — %d edge(s) named on the command line, reporting only, nothing gated",
        len(edges),
    )
    log.info("    across  the occupied stretches of each cross-section, signed off the centreline;")
    log.info("            the gaps between them are the clear runs the profile above measures")
    log.info(
        "    base    lowest surface over the drawn road — an UPPER bound, so <= %.2f m proves "
        "geometry reaches the road and refutes headroom",
        BUMPER_LOW_M,
    )
    log.info(
        "    top     highest surface over it — a LOWER bound: anything wholly above %.2f m was "
        "pruned before this could see it",
        BUMPER_HIGH_M,
    )
    # The rows below are `_edge_verdict`'s, so this report owes its legend too.
    # It exists precisely so the format cannot be described differently in one
    # caller than another, and a caller printing the format with no legend at
    # all is that drift one step further.
    _verdict_legend()

    for edge_id in edges:
        edge = published[edge_id]
        log.info("")
        _edge_verdict(
            found,
            edge_id,
            names.get(edge_id, "unnamed"),
            lengths.get(edge_id, float("nan")),
            note=_width_note(edge),
        )
        walk = occupier_walk(lattice, classes, edge_id)
        # 🔴 **Every counter below reads `judged`, and the set is taken ONCE.**
        # A trimmed cross-section can still have found an occupier —
        # `occupier_walk` records what it saw rather than blanking it — so a
        # counter over the whole walk books a station as occupied and unjudged
        # at once: `e257` read "occupier at 241 of 266 walked stations, 1 too
        # trimmed", with that station inside the 241. ⚠️ **Fixed at one counter
        # and not the two beneath it first**, which left the two lines printing
        # `of 265` and `of 266` for one walk with nothing saying why, and let
        # the second claim a crossing at a station the run table prints as not
        # judged. One list is what stops the next counter arriving without it.
        judged = [station for station in walk if not station.trimmed]
        occupied = sum(1 for station in judged if station.occupier is not None)
        log.info(
            "      occupier at %d of %d judged stations, %d clear, %d too trimmed to judge",
            occupied,
            len(judged),
            len(judged) - occupied,
            len(walk) - len(judged),
        )
        # 🔴 **`Centreline` answers this at ONE station and that is what made
        # `Q103`'s population split 2-2.** Over the whole walk it is a different
        # statement: an occupier that only ever stands at the rims is a parapet,
        # and one that reaches the middle somewhere along the edge is a parapet
        # the ribbon **crosses**. Those want opposite fixes and one station
        # cannot tell them apart.
        #
        # ⚠️ Reachable at 0 on real data — `e257` and `e450` read it — which is
        # the test a counter here has to pass (`Q72`), and it is why the pair is
        # printed rather than asserted.
        crossed = sum(1 for station in judged if _covers_centreline(station))
        approach = _closest_approach(judged)
        log.info(
            "      centreline occupied at %d of %d judged stations; the occupier comes within "
            "%s of it",
            crossed,
            len(judged),
            "no distance — nothing stands on this edge"
            if not np.isfinite(approach)
            else f"{approach:.2f} m",
        )
        log.info("      %-11s %-30s %7s %7s  %s", "stations", "across", "base", "top", "standing")
        first = 0
        for station, count in _standing_runs(walk):
            # Not `span`: everywhere else in this module that word is a cell's
            # across-width in metres (`lattice.span`, `corridor_span_m`).
            rows = f"{first}" if count == 1 else f"{first}-{first + count - 1}"
            first += count
            if station.trimmed:
                log.info(
                    "      %-11s %s", rows, "not judged — too little road drawn at these stations"
                )
                continue
            if station.occupier is None:
                log.info("      %-11s %s", rows, "clear across the whole drawn width")
                continue
            log.info(
                "      %-11s %-30s %+7.2f %+7.2f  %s",
                rows,
                " · ".join(f"{low:+.2f}..{high:+.2f}" for low, high in station.bands),
                station.base_m,
                station.top_m,
                station.occupier,
            )

    log.info("")
    # Both sentences, because this report prints both axes: `_resolution_note`
    # bounds the `profile` widths it inherits from `_edge_verdict` — the same
    # two resolutions the other reports close on, restated for a reader who
    # scrolled straight here — and the line under it is about the across axis
    # this report adds, which neither of them prints.
    _resolution_note(index_cell_m, spacing_m)
    log.info(
        "    each occupied stretch is quantised to the walk's own across cell and smeared by "
        "up to that same plan bin, either side"
    )
    log.info("    no bar is applied above — this names a mechanism, it does not price a fix")


def edge_levels(graph: dict[str, Any]) -> dict[int, int]:
    """Edge id to its elevation level, for the tools that judge a population.

    `road_names`' shape and `road_names`' reason: four tools were spelling this
    comprehension out, `tools/centreline_error.py` twice in one run, and it is
    `elevation_level`'s spelling in as many places as there are readers.

    🔴 **Indexed, never `.get` with a default.** `roads.py` writes the key on
    every edge and `read_graph` pins the schema, so a default cannot fire on
    valid input — and on invalid input it would quietly file an unknown edge
    into level 0, which is the *gated* population. `split_by_level` refuses a
    default for the same reason and `surface.py` refuses one over `offset_m`:
    an inconsistency here is a thing to hear about, not to default into a bar.

    ⚠️ **`pipeline/fence.py` keeps its own copy and must** — a pipeline stage
    cannot import `tools/`.
    """
    return {int(edge["id"]): int(edge["elevation_level"]) for edge in graph["edges"]}


def road_names(graph: dict[str, Any]) -> dict[int, str]:
    """Edge id to a street name, for a failure a reader can go and look at.

    English where the source has it, Chinese where it does not — many service
    roads carry only one, and "unnamed" for a slip road that carries neither is
    more use than an empty column.
    """
    names: dict[int, str] = {}
    for edge in graph["edges"]:
        name = edge.get("road_name") or {}
        chosen = name.get("en") or name.get("zh") if isinstance(name, dict) else None
        if chosen:
            names[int(edge["id"])] = str(chosen)
    return names


if __name__ == "__main__":
    raise SystemExit(main())
