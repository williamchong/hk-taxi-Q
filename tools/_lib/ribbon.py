"""The drawn ribbon's cross-section, as a grader walks it.

`offset ± half` per station (`Q106`), never `±half` about the centreline. Moved
whole out of `overhang.py` (`P3-35f`, `Q133`), which eight tools imported
sideways for it. A move, and a moved name keeps its name.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np

from _lib.bundle import stations


def left_of(along: np.ndarray) -> np.ndarray:
    """The plan normal one metre to the left of travel.

    Hong Kong drives on the left and `surface.py` offsets the same way. This
    tool only ever uses the normal symmetrically — both rails, both signs — so a
    flipped sign changes nothing *it* reports.

    🔴 **That is no longer true of the function.** `tools/deck_margin.py`
    imports it and publishes a **signed** `off_centre_m` in this frame, so a
    flip there is `Q78`'s defect — a quantity that cannot report the direction
    of the move it measures. The frame is pinned by
    `test_left_of_agrees_with_mitres`; do not "simplify" the sign out.
    """
    length = float(np.hypot(along[0], along[1]))
    if length <= 0.0:
        return np.zeros(2)
    return np.array([along[1], -along[0]]) / length


def cross_section(
    point: np.ndarray,
    normal: np.ndarray,
    half_width_m: float,
    across_m: float,
    offset_m: float = 0.0,
) -> list[tuple[float, float, float, float]]:
    """Plan positions across one station's width, each one's share, and its offset.

    Returned with the *area* each stands for rather than as bare points, so a
    ribbon whose width varies along its length weights its wide half correctly.
    A count of cells would report a narrow ramp and a wide arterial as equals.

    🔴 **`offset_m` is where the ribbon is actually DRAWN, and omitting it read
    the road in the wrong place on 36 edges (`Q106`).** `surface._shape` builds
    the two rails at `+half + shift` and `-half + shift` with `shift` the
    graph's `offset_m` — `Q103` moved every off-grade ribbon onto the middle of
    its own deck, up to **4.95 m** on `e337` — and this walked `[-half, +half]`
    about the published centreline regardless. It is in `left_of`'s frame,
    which is `surface.mitres`' frame, and it is **0.0 on every level-0 edge**,
    so a caller that does not pass it is unchanged everywhere the offset does
    not exist.

    ⚠️ **The two consumers failed in OPPOSITE directions and neither said so.**
    `overhang.py` drops a sample with no drawn road under it, so it silently
    measured the *intersection* of this window and the real ribbon and read
    low; `tools/deck_margin.py` keeps every sample, so it counted ribbon that
    is not there and read high — 5.6% against 10.7% on the same bundle, where
    that file's own docstring says a divergence is a bug in one of them.

    🔴 **The signed offset is RETURNED and never re-derived by the caller.**
    Two callers used to rebuild it as `-half + span * (index + 0.5)`, which was
    right while the walk started at `-half`; with `offset_m` it takes two terms,
    and a caller that reconstructs one of them gets `offset == 0` wherever the
    paint actually is — `Q106`'s defect exactly, reintroduced at the seam
    between this function and its callers. It is the distance from the
    **centreline**, which is the frame `authored_width_m` and "the centreline
    cell" are in, and not from the ribbon's own centre.
    """
    if half_width_m <= 0.0:
        return []
    steps = max(1, int(np.ceil(2.0 * half_width_m / across_m)))
    span = 2.0 * half_width_m / steps
    near = offset_m - half_width_m
    return [
        (
            float(point[0] + normal[0] * offset),
            float(point[1] + normal[1] * offset),
            span,
            offset,
        )
        for offset in (near + span * (step + 0.5) for step in range(steps))
    ]


def half_widths(manifest: dict[str, Any]) -> dict[int, list[float]]:
    """`city.json`'s carriageway width table, per edge.

    Paired with `half_width_at`, and public for the same reason: the pre-`Q23`
    fallback below is a compatibility rule, and a second copy of it is a second
    place for it to stop being true.
    """
    return {
        int(entry["edge"]): (
            list(entry["half_width_m"])
            if isinstance(entry["half_width_m"], list)
            else [float(entry["half_width_m"])]
        )
        for entry in manifest["carriageway"]
    }


def drawn_offsets(manifest: dict[str, Any]) -> dict[int, list[float]]:
    """Where each station's ribbon is CENTRED, per edge (`Q107`).

    🔴 **Paired with `half_widths`, and neither is enough alone.** Since the
    clamp the two rails are cut to the deck independently, so a ribbon is not
    symmetric about the published centreline and a half-width does not say where
    it is. `Q106` is what reading one without the other costs: four tools
    rebuilt the road from `half_width_m` about a centreline the paint had left,
    and every one was wrong about the whole off-grade network — in opposite
    directions, so they disagreed by 2x and it read as a model difference.

    ⚠️ **Missing on a pre-schema-7 manifest, and absent means zero** — a bundle
    from before the clamp drew every ribbon centred, so that is the true reading
    rather than a fallback, and it is the same compatibility rule
    `half_widths` keeps for pre-`Q23` bundles.
    """
    return {
        int(entry["edge"]): [float(at) for at in entry.get("offset_m", ())]
        for entry in manifest["carriageway"]
    }


def offset_at(offsets: list[float], vertex: int) -> float:
    """The drawn ribbon's centre at one polyline vertex, in `left_of`'s frame.

    ⚠️ **The fallback is for a PRE-SCHEMA-7 manifest and not for level 0.**
    Every edge publishes `offset_m` now — all 797 of them, 36 of them non-zero —
    so a level-0 edge takes the ordinary indexed path and reads a real 0.0. A
    reader who thinks the at-grade network runs through the untested branch has
    it backwards.
    """
    return at_vertex(offsets, vertex)


def half_width_at(widths: list[float], vertex: int) -> float:
    """The published half-width at one polyline vertex.

    Indexed by vertex because that is how `city.json` publishes it since `Q23`.
    A bundle from before that carries one number per edge, and is read here as
    a constant so the tool can grade an older build — which is the whole reason
    `deck_error` has a `--clearance-m` override.
    """
    return at_vertex(widths, vertex)


def at_vertex(values: list[float], vertex: int) -> float:
    """One per-station table read at a polyline vertex, clamped to its end.

    The shared body of `half_width_at` and `offset_at`, which were
    character-identical. ⚠️ **Not the cross-file restatement this repo
    licenses** — `percentiles` and `pipeline/carriageway.py`'s second survey are
    two implementations kept apart on purpose; these two were adjacent in one
    file and could only ever drift.

    A short table is read as a constant, which is how `city.json` published
    widths before `Q23` and offsets before `Q107`.
    """
    if not values:
        return 0.0
    return float(values[min(vertex, len(values) - 1)])


def walk_width(polyline: np.ndarray, spacing_m: float) -> Iterator[tuple[int, np.ndarray]]:
    """Stations down a polyline, each with the vertex it came from.

    `stations` interpolates but does not say which segment a station belongs
    to, and the width does — so the walk is repeated per segment here rather
    than the width being interpolated by plan distance. The difference is at
    most one station's worth of taper, well inside `--across-m`.

    ⚠️ **The tail of each segment is dropped except on the last**, because
    `stations` yields the polyline's final vertex as well as every interior
    step — so run per segment it emits each shared vertex twice, once as one
    segment's tail and again as the next one's head. Measured on Wan Chai
    before the guard: **735 of 4,127 level-1 stations were duplicates, 17.8%**.
    Q23's length is unharmed either way, since a repeat advances zero metres,
    but every duplicate contributes a whole extra cross-section to the area
    tally and biased `Q22`'s share toward the vertices.
    """
    for vertex in range(len(polyline) - 1):
        emitted = list(stations(polyline[vertex : vertex + 2], spacing_m))
        if vertex < len(polyline) - 2:
            emitted = emitted[:-1]
        for x, y, z in emitted:
            yield vertex, np.array([x, y, z])
