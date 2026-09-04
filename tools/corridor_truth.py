"""The corridor a car can pass, measured exactly — no plan bin, no across cell (`Q110`).

    .venv/bin/python tools/corridor_truth.py --probe-edges e208,e306,e257,e450

`Q109` left `P4-1` one question it called *"the next thing to settle, and it is
not settled by moving a bar"*: `e208` FLEMING ROAD reads **1.35 m** in
`tools/carriageway_occupancy.py` and **2.00 m** in `pipeline/clearance.py` on
the same bundle, either side of `fits_car`'s 1.80 m — so the two instruments
disagree about whether `fence.py` stands a barrier in front of the player.

Neither can answer it, and that is structural rather than a defect in either.
Both rasterise occupiers onto a plan grid, so both **over-block**: a cell blocks
in full as soon as one surface sample lands in it, and a wall smears by up to a
cell either side. Their published widths are lower bounds at their own bins, and
the bins differ — 0.5 m in the pipeline, 1.0 m in the grader. `Q51` settled the
same disagreement on `e132` by brute-forcing that edge from its own geometry,
and this is that instrument, generalised and committed rather than thrown away
(`Q37`'s debt).

**What is exact here.** The blocked span across a station is computed by
clipping each triangle against the station's slab and the bumper band and
taking the extent of what survives, in closed form. There is no plan cell, no
across cell and no surface sampling, so the two error terms that separate the
shipped instruments are not approximated — they are absent.

🔴 **The one free parameter is `--window-m`, and what it guards is ALIASING
ALONG the edge — not a wall's thickness.** The obvious worry was the second one
and it is measured false: the model's parapet is a vertical surface, so at a
zero-thickness cross-section it blocks a *point* rather than an interval — but a
point still partitions the run, so the reading does not move. What a zero window
really loses is an obstruction standing *between* two stations, which is the
aliasing `pipeline/clearance.py` pins `ALONG_M == CELL_M` to avoid, and it is why
a window under the station pitch is the setting to distrust. ✅ The readings are
**flat from `--window-m 0` to 2.0** on all four edges of `Q110`, so on this
population neither term is live; sweep it anyway, because a bound that cannot be
swept is `Q58`'s trap.

⚠️ **Independent in method, NOT in frame — deliberately.** Where the ribbon is
drawn comes from `city.json`'s `carriageway[]` through `overhang.py`'s helpers,
which is what `CLAUDE.md` requires of anything that reads it: `Q106` cost this
repo four tools reading the road in the wrong place at once, and a third
hand-rolled frame here would be the fifth. What shares nothing is the
measurement.

🔴 **It can CLEAR an edge and can never CONDEMN one, and that asymmetry is the
whole argument.** Every triangle in the shipped tiles blocks, with no colour
classification at all, so the reading is a lower bound on the true corridor from
two directions at once: it cannot miss an occupier a colour rule would have
caught, and the exact clip cannot smear one wider than it is. A reading **above**
a bar is therefore proof; a reading below one is evidence of nothing, because
unclassified geometry includes classes both shipped instruments exclude.

⚠️ **So the level-0 rows are a control on the machinery and NOT a
reconciliation.** At grade this blocks on terrain the graders filter out, and
`e132` reads *below* both of them — three numbers bounding three different
quantities, which is `Q110`'s own table and not a contradiction. `e0` HENNESSY
ROAD reproducing **10.24 m of a 10.24 m ribbon** is what the level-0 rows are
for. Off-grade the question does not arise: `Q109` measured the occupier 100%
`INFRASTRUCTURE` on all four, and the conclusion holds whatever the class is.

⚠️ **It asks what stands IN the band, never whether deck stands UNDER it.**
Beyond the ribbon's own rails a clear run is air as readily as road, so a run
from `--section-at` is not usable carriageway. `tools/deck_margin.py` and
`tools/overhang.py` answer that half.

⚠️ **The ribbon is INTERPOLATED between vertices, where the grader takes the
nearest one.** `surface._shape` builds the rails at the polyline's vertices and
the mesh spans them, so the drawn ribbon between two vertices is the linear
blend and nothing else. On `e208` the published half-width runs 2.198 → 1.709 →
1.575 m over two segments, so a nearest-vertex reading is up to half a metre out
exactly where the pinch is.

It **grades rather than checks**: it exits 0 whatever it finds, publishes
nothing, and gates nothing. No bar is applied — `P4-1` owns what an off-grade
corridor has to clear.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import edges_argument, edges_label, road_names  # noqa: E402
from deck_error import bundle_arguments, load_bundle, log_bundle  # noqa: E402
from overhang import drawn_offsets, half_widths, left_of  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402
from pipeline.polyline import plan_lengths  # noqa: E402

log = logging.getLogger(__name__)

# Station pitch. Finer than either shipped instrument's, because nothing here
# is binned along the edge either: the slab is the window and the pitch only
# decides how often it is placed.
SPACING_M = 0.25

# The length of road one reading must be clear over. 0.5 m is a car's own
# progress between two of the pipeline's cross-sections; it is swept rather
# than defended, and `--window-m` is the sweep.
WINDOW_M = 0.5

# How far past the widest ribbon a triangle may sit and still be read. Only a
# prefilter — the clip below refuses anything outside the ribbon exactly — so
# it is sized to be generous rather than tight.
REACH_M = 30.0

# How far past the ribbon's rails the cross-section printer reports. Reporting
# only — no reading in the table above depends on it — but it is bounded by
# `REACH_M` and `main` refuses to start unless it fits, because a printer that
# silently truncates its own window is `Q58`'s trap in the one place a reader
# goes to look at the geometry. `deck_margin.py` and `carriageway_margin.py`
# both refuse at startup for the same reason.
SECTION_REACH_M = 12.0

# `Q19`'s band, in metres above the deck — restated so this reading is taken in
# the frame the two instruments it reconciles were taken in. A different band
# would make this a third answer to a third question.
#
# 🔴 **Restated and NOT imported from `pipeline.clearance`, on
# `carriageway_occupancy.py`'s precedent and for its reason.**
# `tools/ground_clearance.py` imports these two bounds deliberately, and
# `CLAUDE.md` attaches the rule to that exception in the same breath: a shared
# bound is not a shared reading, and no second import comes in on it. The whole
# value here is that nothing is shared with either instrument.
#
# ⚠️ **`clearance.json` publishes `bumper_band_m` and the shipped bundle does
# not carry that file** — `export.py` folds the widths into `city.json` and
# leaves the band behind — so reading it back is not available to a tool that
# grades what the game ships.
BUMPER_LOW_M = 0.30
BUMPER_HIGH_M = 2.00


def tile_triangles(paths: list[Path]) -> np.ndarray:
    """Every triangle in the shipped tiles, as `(n, 3, 3)` corner positions.

    ⚠️ **No class filter, and that is the conservative direction.** The shipped
    graders select occupiers by vertex colour; this blocks on all of it, so a
    colour rule that let something through cannot make this read *wider*.
    """
    blocks: list[np.ndarray] = []
    for path in paths:
        for mesh in read_glb(path):
            if len(mesh.triangles) == 0:
                continue
            blocks.append(mesh.positions[mesh.triangles])
    if not blocks:
        raise SystemExit("no tile geometry read; is this a built bundle?")
    return np.concatenate(blocks).astype(np.float64)


def _station_frame(start: np.ndarray, end: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """A segment's plan origin, its along and across units, and its plan length.

    The across unit is `overhang.left_of`, which is `surface.mitres`' frame and
    the frame `offset_m` is published in — the repo's two station normals are
    opposite on purpose and this is the side that must not be flipped.
    """
    along = end[[0, 2]] - start[[0, 2]]
    length = float(np.hypot(along[0], along[1]))
    if length <= 0.0:
        return np.zeros(2), np.zeros(2), 0.0
    return along / length, left_of(along), length


def _segment_coordinates(
    triangles: np.ndarray, origin: np.ndarray, along: np.ndarray, across: np.ndarray
) -> np.ndarray:
    """Every corner in one segment's `(s, y, t)` frame.

    Affine, so a triangle stays a triangle and the clip below is the same clip
    it would be in world space — which is what makes the exactness claim hold
    after the change of coordinates rather than in spite of it.
    """
    plan = triangles[:, :, [0, 2]] - origin
    return np.stack(
        (plan @ along, triangles[:, :, 1], plan @ across),
        axis=2,
    )


# One corner in the `(s, y, t)` frame. Plain tuples rather than an ndarray row:
# the clip below runs on 3-to-7 vertex polygons 1.7 M times a sweep, where
# numpy's per-call overhead is the entire cost. Measured 8.0 s -> 2.4 s with
# **every** station's `clear_m`, `centre_m` and blocked intervals identical —
# the same operations in the same order on the same IEEE doubles, without the
# array wrapper. ⚠️ **The exactness claim is about the closed form and not
# about numpy**, so it survives this verbatim; do not "restore" the array
# version for tidiness.
Point = tuple[float, float, float]


def _clip(polygon: list[Point], axis: int, bound: float, keep_above: bool) -> list[Point]:
    """One Sutherland-Hodgman half-space clip of a convex polygon in `(s, y, t)`.

    ⚠️ **Written out rather than folded over `boxjunctions._clip_half_plane`**,
    on `test_arrows.py`'s stated precedent — *"twenty lines is the price of an
    independent answer"*. That one is also 2-D and discards a result under three
    points, which would delete the degenerate reading this tool pins.
    """
    if not polygon:
        return polygon
    value = [point[axis] - bound for point in polygon]
    inside = [test >= 0.0 if keep_above else test <= 0.0 for test in value]
    if all(inside):
        return polygon
    if not any(inside):
        return []
    out: list[Point] = []
    for index, point in enumerate(polygon):
        following = (index + 1) % len(polygon)
        if inside[index]:
            out.append(point)
        if inside[index] != inside[following]:
            # The span cannot be zero: the two ends straddle the bound, so
            # their signed distances differ.
            fraction = value[index] / (value[index] - value[following])
            beyond = polygon[following]
            out.append(
                (
                    point[0] + (beyond[0] - point[0]) * fraction,
                    point[1] + (beyond[1] - point[1]) * fraction,
                    point[2] + (beyond[2] - point[2]) * fraction,
                )
            )
    return out


def blocked_extent(
    corners: list[Point] | np.ndarray,
    slab: tuple[float, float],
    band: tuple[float, float],
) -> tuple[float, float] | None:
    """The exact across-extent of one triangle inside the slab and the band.

    🔴 **This is the whole of what makes the reading exact**, and it is a closed
    form rather than a sample: the triangle is clipped against four half-spaces,
    what survives is convex, and the extent of a convex set under a linear map
    is the extent over its own corners. A vertical wall clipped this way keeps
    its true across-extent within the slab, which is exactly what a plan bin
    approximates by smearing and what a zero-thickness cross-section loses.
    """
    polygon: list[Point] = corners.tolist() if isinstance(corners, np.ndarray) else list(corners)
    for axis, bound, keep_above in (
        (0, slab[0], True),
        (0, slab[1], False),
        (1, band[0], True),
        (1, band[1], False),
    ):
        polygon = _clip(polygon, axis, bound, keep_above)
        if not polygon:
            return None
    across = [point[2] for point in polygon]
    return min(across), max(across)


def merged(blocked: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Overlapping blocked intervals folded into one run each, in order."""
    runs: list[list[float]] = []
    for low, high in sorted(blocked):
        if runs and low <= runs[-1][1]:
            runs[-1][1] = max(runs[-1][1], high)
        else:
            runs.append([low, high])
    return [(low, high) for low, high in runs]


def widest_clear(
    blocked: list[tuple[float, float]], near: float, far: float
) -> tuple[float, float]:
    """The widest run of the ribbon free of every blocked interval, and its centre.

    ⚠️ **The widest run, never the unblocked total** — a car needs one gap it
    fits through rather than two halves of one. `pipeline/clearance.py` states
    the same rule and this is the second place it is applied, so the two answer
    one question.
    """
    inside = sorted((max(lo, near), min(hi, far)) for lo, hi in blocked if hi > near and lo < far)
    best, centre, cursor = 0.0, 0.5 * (near + far), near
    for lo, hi in [*inside, (far, far)]:
        if lo - cursor > best:
            best, centre = lo - cursor, 0.5 * (cursor + lo)
        cursor = max(cursor, hi)
    return best, centre


def _at(values: list[float], vertex: int, fraction: float) -> float:
    """A per-vertex published value, interpolated along its segment.

    ⚠️ **Interpolated, where `overhang.at_vertex` takes the nearest vertex.**
    `surface._shape` builds the rails at the vertices and the mesh spans them,
    so between two of them the drawn ribbon *is* this blend. On `e208` the
    published half-width falls 2.198 → 1.575 m over the two segments that carry
    the pinch, which is half a metre of ribbon a nearest-vertex reading puts in
    the wrong place.
    """
    if not values:
        # `overhang.at_vertex`'s own first line, and not decoration:
        # `drawn_offsets` returns `[]` for an edge published before schema 7,
        # and without this the tool dies with an `IndexError` on exactly the
        # bundles that helper goes out of its way to keep readable.
        return 0.0
    if vertex + 1 >= len(values):
        return float(values[-1])
    lower, upper = float(values[vertex]), float(values[vertex + 1])
    return lower + (upper - lower) * fraction


@dataclass(frozen=True)
class Station:
    """One reading: where it is, how wide the ribbon is, and what got through.

    `blocked` is kept per station rather than reduced to `clear_m` on the spot,
    because the cross-section printer reads it. 🔴 **One walk and one statement
    of the blocking rule**: the alternative is a second traversal for the
    printer, and a scratch script that agrees with the table until it does not
    is `Q37`'s debt and `Q55`'s.
    """

    edge: int
    along_m: float
    deck_y: float
    near: float
    far: float
    clear_m: float
    centre_m: float
    blocked: tuple[tuple[float, float], ...]
    # `roadgraph.json`'s `deck_rim_m` at THIS station, interpolated like the
    # ribbon. ⚠️ Printed as the station's own, so it may not be read off vertex
    # 0 — a rim label naming the wrong station is `Q109`'s `occupier_walk`
    # comment at a second tool. Absence of a deck is `inf`, never 0.0, which is
    # `surface._clamped_rails`' rule and the reason the clamp is inert at grade.
    rims: tuple[float, float]

    @property
    def ribbon_m(self) -> float:
        return self.far - self.near


def deck_rims(edge: dict[str, Any], vertices: int) -> tuple[list[float], list[float]]:
    """`deck_rim_m` split into two per-vertex lists, absent decks as `inf`.

    ⚠️ **Per VERTEX, not per station.** `Station` is a 0.25 m walk sample and
    these tables are indexed by polyline vertex, which `_at` then interpolates.
    """
    rims = edge.get("deck_rim_m") or []
    if not rims:
        return [float("inf")] * vertices, [float("inf")] * vertices
    return [float(pair[0]) for pair in rims], [float(pair[1]) for pair in rims]


def unclamped_ribbon(edge: dict[str, Any], vertices: int) -> tuple[list[float], list[float]]:
    """The ribbon `surface.py` would draw with `Q107`'s clamp switched off.

    🔴 **The counterfactual `Q109` says a clamp owes and `Q107` did not record.**
    That entry's evidence was `overhang.py` 4.3% -> 3.3% and a frame, both of
    which improve; the corridor is measured *inside* the paint, so cutting paint
    back to the deck narrows every corridor it touches without moving one
    triangle. Reading the same geometry in the pre-clamp frame is what prices it.

    It is `roadgraph.json`'s own `width_m` and `offset_m` — one of each per edge,
    constant along it, which is exactly what `surface._shape` built the rails
    from before `_clamped_rails` existed.
    """
    half = 0.5 * float(edge["width_m"])
    shift = float(edge.get("offset_m", 0.0))
    return [half] * vertices, [shift] * vertices


@dataclass(frozen=True)
class Walk:
    """The instrument: the geometry it blocks on, and how it steps.

    Grouped rather than passed as four more positionals, because none of them
    is about the edge being read — `survey_edge` was taking seven arguments and
    three call sites spelled all seven out.
    """

    triangles: np.ndarray
    # The plan bounding box of every triangle, hoisted out of `survey_edge`.
    # `triangles[:, :, [0, 2]]` is fancy-indexing, so rebuilding it per call
    # allocated a 24.7 MB temporary on each of the twenty calls a sweep makes.
    corners_low: np.ndarray
    corners_high: np.ndarray
    band: tuple[float, float]
    window_m: float
    spacing_m: float


def survey_edge(
    edge: dict[str, Any],
    walk: Walk,
    halves: list[float],
    offsets: list[float],
) -> list[Station]:
    """Every station on one edge, with its exact clear run."""
    triangles, band = walk.triangles, walk.band
    window_m, spacing_m = walk.window_m, walk.spacing_m
    corners_low, corners_high = walk.corners_low, walk.corners_high
    rim_left, rim_right = deck_rims(edge, len(halves))
    polyline = np.asarray(edge["polyline"], dtype=np.float64)
    readings: list[Station] = []
    # Cumulative plan distance, so a station names a place on the *edge* rather
    # than on the segment it happens to fall in — the first build reported
    # `2.2 m along` for a station 190 m down the ramp, which is a location
    # nobody can go and look at. `pipeline.polyline` is the repo's one statement
    # of this arithmetic and calls itself a primitive the duplicate-deliberately
    # rule does not reach: it grades nothing, so a second copy buys no check.
    # ⚠️ It is the **label**, never the measurement, so the exactness claim does
    # not rest on it.
    travelled = plan_lengths(polyline)
    for vertex in range(len(polyline) - 1):
        start, end = polyline[vertex], polyline[vertex + 1]
        along, across, length = _station_frame(start, end)
        if length <= 0.0:
            continue
        origin = start[[0, 2]]
        # 🔴 **A world-space box, and interval overlap rather than a nearest
        # corner.** A prefilter keyed on the closest corner drops a triangle
        # that *spans* the ribbon with both its ends outside the reach — which
        # is the shape of every large face, and exactly the one that blocks a
        # whole cross-section.
        floor_xz = np.minimum(start[[0, 2]], end[[0, 2]]) - REACH_M
        roof_xz = np.maximum(start[[0, 2]], end[[0, 2]]) + REACH_M
        nearby = triangles[
            (corners_high[:, 0] >= floor_xz[0])
            & (corners_low[:, 0] <= roof_xz[0])
            & (corners_high[:, 1] >= floor_xz[1])
            & (corners_low[:, 1] <= roof_xz[1])
        ]
        local = _segment_coordinates(nearby, origin, along, across)
        low = local[:, :, 0].min(axis=1)
        high = local[:, :, 0].max(axis=1)
        floor = local[:, :, 1].min(axis=1)
        ceiling = local[:, :, 1].max(axis=1)

        steps = max(1, int(np.ceil(length / spacing_m)))
        # The tail is dropped except on the last segment, so a shared vertex is
        # not walked twice. ⚠️ **`overhang.walk_width`'s guard, but NOT for its
        # reason** — there a duplicate biases an area tally by 17.8%, and here
        # the published number is a minimum and a nearest-station pick, which a
        # repeat cannot move. What it buys is an honest station count and no
        # wasted clipping. Borrowing another tool's justification is the move
        # `CLAUDE.md` calls out on the lamps sweep.
        last = vertex == len(polyline) - 2
        for step in range(steps + (1 if last else 0)):
            fraction = min(1.0, step * spacing_m / length)
            here = start + (end - start) * fraction
            half = _at(halves, vertex, fraction)
            shift = _at(offsets, vertex, fraction)
            if half <= 0.0:
                continue
            # ⚠️ The slab is not clipped to the segment, so within half a window
            # of a vertex it reads the neighbour's geometry projected onto this
            # segment's straight-line extension. At the default 0.5 m window
            # that is millimetres of lateral error on a ramp's curvature, and
            # clipping it would instead leave a station reading a *shorter* slab
            # than its neighbours — a resolution that varies along the edge.
            slab = (fraction * length - 0.5 * window_m, fraction * length + 0.5 * window_m)
            deck = (here[1] + band[0], here[1] + band[1])
            reach = (high >= slab[0]) & (low <= slab[1]) & (ceiling >= deck[0]) & (floor <= deck[1])
            blocked: list[tuple[float, float]] = []
            # `.tolist()` once per station, in C, rather than boxing every
            # corner one row at a time inside the clip.
            for corners in local[reach].tolist():
                extent = blocked_extent(corners, slab, deck)
                if extent is not None:
                    blocked.append(extent)
            near, far = shift - half, shift + half
            width, centre = widest_clear(blocked, near, far)
            # ⚠️ **Kept out to `SECTION_REACH_M`, past the ribbon's own rails.**
            # `widest_clear` clips to the ribbon and that is the reading; the
            # cross-section printer needs what stands *beside* the paint too,
            # and recomputing it there would be the second walk this class
            # keeps the intervals to avoid.
            keep = tuple(
                run
                for run in merged(blocked)
                if run[1] >= near - SECTION_REACH_M and run[0] <= far + SECTION_REACH_M
            )
            readings.append(
                Station(
                    edge["id"],
                    float(travelled[vertex]) + fraction * length,
                    float(here[1]),
                    near,
                    far,
                    width,
                    centre,
                    keep,
                    (_at(rim_left, vertex, fraction), _at(rim_right, vertex, fraction)),
                )
            )
    return readings


def section_argument(text: str) -> list[tuple[int, float]]:
    """`e208@180.6,e306@186.7` — an edge and a distance along it, in metres.

    The edge half is parsed by `carriageway_occupancy.edges_argument`, which is
    the repo's one statement of how an edge id is spelled on a command line —
    restating it here would be the second, and the two would drift.
    """
    wanted: list[tuple[int, float]] = []
    for entry in (part.strip() for part in text.split(",")):
        if not entry:
            continue
        edge, _, metres = entry.partition("@")
        if not metres:
            raise argparse.ArgumentTypeError(f"{entry!r}: expected EDGE@METRES, e.g. e208@180.6")
        try:
            at_m = float(metres)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{entry!r}: {metres!r} is not a distance") from None
        wanted.append((edges_argument(edge)[0], at_m))
    return wanted


def print_section(readings: list[Station], at_m: float, window_m: float) -> None:
    """One station's whole cross-section — what blocks, and every clear run.

    🔴 **Outside the ribbon a clear run is "nothing in the bumper band", and
    that is NOT drivable.** This asks what stands in the band; it never asks
    whether deck stands *under* it, so open air beside a viaduct reads clear and
    reads wide. `tools/deck_margin.py` and `tools/overhang.py` are the two that
    answer the other question, and quoting a run from here as usable road is
    `Q57`'s generalisation with the populations one metre apart.

    ⚠️ **The window is printed because the intervals depend on it.** This reads
    the first `--window-m` of the sweep, and at a zero window a vertical face
    collapses to a point — `[-0.68, -0.68]` where a 0.5 m slab reads
    `[-0.68, -0.66]`. Both are right about their own slab; a printed interval
    with no window beside it is not.
    """
    log.info("")
    if not readings:
        # Said rather than skipped: a blank where a cross-section was asked for
        # reads as "nothing stands there", which is the opposite of the truth.
        log.info("  cross-section — no station carried a drawn ribbon")
        return
    here = min(readings, key=lambda station: abs(station.along_m - at_m))
    log.info(
        "  cross-section e%d at %.1f m, window %.2f m — deck %.2f m, "
        "ribbon [%+.2f, %+.2f], rims %s",
        here.edge,
        here.along_m,
        window_m,
        here.deck_y,
        here.near,
        here.far,
        " / ".join(f"{value:.2f}" for value in here.rims),
    )
    inside = [run for run in here.blocked if run[1] > here.near and run[0] < here.far]
    log.info(
        "    in ribbon   %d face%s block: %s   widest clear %.2f m centred %+.2f m",
        len(inside),
        "" if len(inside) == 1 else "s",
        " ".join(f"[{low:+.2f},{high:+.2f}]" for low, high in inside) or "none",
        here.clear_m,
        here.centre_m,
    )
    log.info(
        "    +-%.0f m      %s",
        SECTION_REACH_M,
        " ".join(f"[{low:+.2f},{high:+.2f}]" for low, high in here.blocked)
        or "nothing in the band",
    )
    log.info("    beyond the rails a clear run is air as readily as road — see the docstring")


def _report(name: str, readings: list[Station], window_m: float, edge_id: int) -> None:
    """Print one edge's binding station at one window.

    🔴 **`blocked` is published beside `clear`, and it is the column that
    separates the two causes.** A corridor is short because the obstruction is
    wide or because the *paint* is narrow, and those want opposite fixes — the
    first is geometry and the second is `Q107`'s clamp. One number cannot say
    which, and `Q57` is the rule that they may not share one.
    """
    if not readings:
        log.info("    %-6s no station carried a drawn ribbon", f"e{edge_id}")
        return
    worst = min(readings, key=lambda station: station.clear_m)
    log.info(
        "    %-6s %-22s window %4.2f m   clear %5.2f m   ribbon %5.2f m   "
        "blocked %4.2f m   at %6.1f m along, centred %+5.2f m",
        f"e{edge_id}",
        name[:22],
        window_m,
        worst.clear_m,
        worst.ribbon_m,
        worst.ribbon_m - worst.clear_m,
        worst.along_m,
        worst.centre_m,
    )


def windows_argument(text: str) -> list[float]:
    """`0,0.5,2` — the slab lengths to sweep, in metres.

    An argparse `type` rather than a hand-parse after `parse_args`, on
    `section_argument`'s pattern and `edges_argument`'s: parsed by hand, an
    empty string yielded an empty sweep that printed nothing and then raised
    `IndexError` two functions later.
    """
    windows = []
    for entry in (part.strip() for part in text.split(",")):
        if not entry:
            continue
        try:
            window = float(entry)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{entry!r} is not a length") from None
        if window < 0.0:
            raise argparse.ArgumentTypeError(f"{entry}: a length of road cannot be negative")
        windows.append(window)
    if not windows:
        raise argparse.ArgumentTypeError(f"{text!r}: no window given")
    return windows


def spacing_argument(text: str) -> float:
    """The station pitch, which divides and so may not be zero."""
    try:
        spacing = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a pitch") from None
    if spacing <= 0.0:
        raise argparse.ArgumentTypeError(f"{text}: a station pitch must be positive")
    return spacing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, parents=[bundle_arguments()])
    parser.add_argument(
        "--probe-edges",
        type=edges_argument,
        required=True,
        help="comma-separated edge ids to measure, e.g. e208,e306",
    )
    parser.add_argument(
        "--window-m",
        type=windows_argument,
        default=[WINDOW_M],
        help=f"comma-separated slab lengths the corridor must be clear over (default: {WINDOW_M})",
    )
    parser.add_argument(
        "--spacing-m", type=spacing_argument, default=SPACING_M, help="station pitch"
    )
    parser.add_argument(
        "--section-at",
        type=section_argument,
        default=[],
        help="comma-separated EDGE@METRES, e.g. e208@180.6, to print one whole cross-section",
    )
    parser.add_argument(
        "--unclamped",
        action="store_true",
        help="also read the same geometry in the pre-Q107 frame, to price what the clamp cost",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manifest, tiles = load_bundle(args.generated, args.lod)
    graph = json.loads((args.generated / manifest["road_graph"]).read_text())
    halves, offsets = half_widths(manifest), drawn_offsets(manifest)
    names = road_names(graph)
    wanted = {edge["id"]: edge for edge in graph["edges"] if edge["id"] in args.probe_edges}
    missing = tuple(edge for edge in args.probe_edges if edge not in wanted)
    if missing:
        raise SystemExit(f"no such edge in {manifest['road_graph']}: {edges_label(missing)}")
    astray = [edge for edge, _ in args.section_at if edge not in wanted]
    if astray:
        # Ahead of the survey, not after it: a typo here used to cost a full
        # walk of every edge before the message appeared.
        raise SystemExit(f"--section-at {edges_label(tuple(astray))}: not in --probe-edges")
    widest = max((max(table, default=0.0) for table in halves.values()), default=0.0)
    if widest + SECTION_REACH_M > REACH_M:
        raise SystemExit(
            f"SECTION_REACH_M {SECTION_REACH_M} m past a {widest:.2f} m half-width does not fit "
            f"the {REACH_M} m prefilter; the cross-section would truncate without saying so"
        )

    log.info("corridor truth — exact clip, no plan bin, no across cell, all tile geometry blocks")
    log_bundle(manifest, args.lod)
    log.info(
        "  band      %.2f-%.2f m above the deck — Q19's, restated", BUMPER_LOW_M, BUMPER_HIGH_M
    )
    log.info(
        "  walk      %.2f m station pitch; ribbon interpolated between vertices", args.spacing_m
    )
    triangles = tile_triangles(tiles)
    log.info("  geometry  %d triangles over %d tiles, unclassified", len(triangles), len(tiles))
    walk = Walk(
        triangles,
        triangles[:, :, [0, 2]].min(axis=1),
        triangles[:, :, [0, 2]].max(axis=1),
        (BUMPER_LOW_M, BUMPER_HIGH_M),
        args.window_m[0],
        args.spacing_m,
    )

    # `--section-at` reads the first window's own walk rather than repeating it.
    surveyed: dict[int, list[Station]] = {}
    for window in args.window_m:
        log.info("")
        for edge_id in args.probe_edges:
            edge = wanted[edge_id]
            readings = survey_edge(
                edge, replace(walk, window_m=window), halves[edge_id], offsets[edge_id]
            )
            if window == args.window_m[0]:
                surveyed[edge_id] = readings
            _report(names.get(edge_id, "unnamed"), readings, window, edge_id)

    for edge_id, at_m in args.section_at:
        print_section(surveyed[edge_id], at_m, args.window_m[0])

    if args.unclamped:
        log.info("")
        log.info("  counterfactual — the same geometry, read in the pre-Q107 frame")
        log.info(
            "  the ribbon is roadgraph.json's own width_m and offset_m, constant along the edge"
        )
        for edge_id in args.probe_edges:
            edge = wanted[edge_id]
            wide, shifted = unclamped_ribbon(edge, len(halves[edge_id]))
            _report(
                names.get(edge_id, "unnamed"),
                survey_edge(edge, walk, wide, shifted),
                walk.window_m,
                edge_id,
            )

    log.info("")
    log.info("  no bar is applied — P4-1 owns what an off-grade corridor has to clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
