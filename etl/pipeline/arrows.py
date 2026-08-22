"""Published turn arrows, drawn as their own mesh (`P3-15`, closes `Q53`'s arrow half).

`Q53` held arrows out of `P3-12` because "there is no marking data in any
source". `Q57` retired that reason on 2026-08-20 — it reasoned about Road
Network v2, the *semantic* dataset, and concluded about the whole estate — and
what was left was a **cost and registration** argument. This is that work.

Three things make this stage different from the ribbon markings beside it, and
each one is why it is a separate mesh rather than another field in
`surface.py`'s codec:

- **`TEXCOORD_1.x` has no room and the wrong shape.** It is a per-edge constant
  with three spare bits; an arrow is a *point* feature, which is `Q54`'s V-range
  problem, and `COLOR_0.a` — the channel that solved it for the kerbside — is
  spent on the kerbside extent.
- **The junction fade blanks exactly where arrows live.** `road_markings.tres`
  fades the last `fade_m` = 6 m of every edge, priced against the 4.21 m
  worst-case cap overlap, and already leaves 121 of 797 edges with no marking at
  all. An approach arrow drawn on the ribbon would fade out at the junction it
  is about.
- **The cap overlap is still there.** `Q53`: "anything drawn *on* a cap
  re-exposes it immediately." Separate geometry lifted above both cap and arm is
  immune, the same way `ART_DESIGN.md` says a world-space box junction is.

⚠️ **The published position is read as a fraction across the road, never as a
position** — `Q54`'s "use it as data, not as geometry", the pattern that let the
kerbside join survive the same 1.6x widening. The alternative, drawing at the
published easting and northing, was measured and is defensible: 97.2% of the
region's symbols already fall inside the drawn ribbon, because the ribbon is
*wider* than the real carriageway and concentric with it. It is not what ships,
because an arrow at its true offset sits about a metre off the drawn lane's
centre and reads as a rendering fault against the lane dividers `P3-12` draws,
while a lane-registered arrow is wrong only about something no driver navigates
by. `Q58`'s refusal of lane space does **not** transfer: a tram rail sits a
measured p50 3.26 m *past* the drawn kerb, off the surface entirely, so lane
space would have invented its position. This is the opposite case.

⚠️ **Nothing here rotates an arrow.** A symbol whose bearing disagrees with its
edge has matched the wrong edge and is refused; turning it to agree would be an
invented marking in `Q54`'s sense, and it would render perfectly.
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline import gdb
from pipeline.config import (
    ARROW_AHEAD,
    ARROW_LEFT,
    ARROW_RIGHT,
    ArrowGlyph,
    Arrows,
    CityConfig,
    GameTransform,
    load_city,
)
from pipeline.documents import read_document, write_document
from pipeline.fares import Segments
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.mesh import select_triangles
from pipeline.roads import ROADGRAPH_NAME, plan_lengths, read_graph
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA, downward_facing

log = logging.getLogger(__name__)

ARROWS_NAME = "arrows.glb"
ARROWS_MANIFEST_NAME = "arrows.json"
ARROWS_MANIFEST_SCHEMA = 1

# ⚠️ **No `-col` suffix.** Paint is not a collider. The same reasoning
# `TRAMWAY_MESH_NAME` records, with less room for doubt: a 15 mm step of paint
# modelled as collision geometry is a kerb across every lane in the city.
ARROWS_MESH_NAME = "arrows"

# glTF material name, the contract channel `SURFACE_MATERIAL` and
# `TRAMWAY_MATERIAL` use: `tools/generated_scene_import.gd` maps this string onto
# `tuning/arrows.tres` and nothing else.
ARROWS_MATERIAL = "arrows"

# Below this, twice a triangle's area means it has collapsed. The bar
# `surface.py` and `tramway.py` both set, for the same reason.
_MIN_TWICE_AREA_M2 = 1e-6

# What `ELEVATION` says when a symbol is at grade. The column is a structure
# identifier — `A01`, `A03` — and null is the ground. 1,328 of the region's 1,365
# symbols are null; the rest are on flyovers this region does not open to
# driving (`Q13`).
#
# ⚠️ Not config. It is the source's own encoding of "no structure", not a
# threshold anyone may tune, and a city whose publisher spells it differently
# needs a reader change rather than a number.
_AT_GRADE = ("", "none", "null", "<na>")


@dataclass
class ArrowReport:
    """What the stage read, matched and drew.

    ⚠️ **The counters are what can see this stage fail, because none of its
    failures look like anything in a frame** — `Q58`'s lesson, which cost three
    defects that each rendered as *nothing*. An arrow on the wrong street is a
    perfectly drawn arrow. An arrow turned 180 degrees is a perfectly drawn
    arrow. A glyph table off by one code paints turn-left everywhere and renders
    beautifully.

    The partitions:

        symbols == not_a_turn_arrow + on_structure + empty_geometry + candidates
        candidates == drawn + too_far + off_bearing + against_one_way + no_lane
    """

    symbols: int = 0
    not_a_turn_arrow: int = 0
    on_structure: int = 0
    empty_geometry: int = 0
    candidates: int = 0

    drawn: int = 0
    too_far: int = 0
    off_bearing: int = 0
    against_one_way: int = 0
    no_lane: int = 0

    # Drawn arrows by movement set, keyed by the joined movement names. Publishes
    # the glyph table's effect rather than the table: a mapping that silently
    # stopped matching shows up here as a code that draws nothing.
    by_glyph: dict[str, int] = field(default_factory=dict)

    # ⚠️ **The axis residual is folded modulo 180 and the facing residual is
    # not, and they answer different questions.** Alignment to the road *axis*
    # is what catches a match to the wrong edge — a symbol lying square across
    # its host. Which way along the axis it points is legitimately either way on
    # a two-way street, so it is reported and never refused.
    axis_residual_deg: list[float] = field(default_factory=list)
    # How far each symbol that found a host sat from its centreline. Recorded
    # beside the residual and for the same reason: it is what `max_offset_m` is
    # set against, and a config comment quoting a number nothing re-derives is
    # the debt `Q37` was opened about.
    offset_m: list[float] = field(default_factory=list)
    drawn_on_two_way: int = 0
    # Arrows drawn where the published offset puts them outside the ribbon that
    # was actually drawn. Not a refusal — the drawn ribbon is 1.6x the real
    # carriageway and still misses, which is `Q19`'s open question, not this
    # stage's — but it is the number that says how much of the registration is
    # being carried by the clamp rather than by the source.
    outside_drawn_ribbon: int = 0

    # How far each arrow moved sideways to reach its lane's centre. The residue
    # of the registration decision at the top of this module, published so the
    # decision can be re-argued against a number.
    lane_shift_m: list[float] = field(default_factory=list)
    # Symbols whose along-edge position fell inside a junction trim, so they sit
    # over a cap rather than over a drawn arm. Drawn anyway — the cap is still
    # carriageway — but counted, because it is where the ribbon has no lane
    # coordinate and the count is the only sign of it.
    over_a_cap: int = 0

    # `SYMBOL_SIZE` as published, which nothing here reads. Recorded so the
    # question "is it the arrow's length in metres?" can be answered from a
    # shipped artefact rather than from a scratch script — `Q37`'s debt.
    symbol_size: list[float] = field(default_factory=list)

    # Triangles wound so they face the ground. Published because inverted paint
    # is *invisible* rather than wrong-looking: `cull_back` drew none of the
    # first tramway, 5,111 triangles of 5,112, with everything else correct.
    inverted: int = 0
    inverted_area_m2: float = 0.0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)

    @staticmethod
    def measured(values: list[float]) -> dict[str, float]:
        """One distribution as the manifest publishes it.

        p90 and p99 rather than `TramwayReport.measured`'s p10/p50/p90: every
        distribution here is a residual whose *tail* is the finding, and a
        median residual near zero says nothing about the arrow on the wrong
        street.
        """
        if not values:
            return {}
        points = np.percentile(np.asarray(values), (50, 90, 99, 100))
        return {
            "p50": round(float(points[0]), 4),
            "p90": round(float(points[1]), 4),
            "p99": round(float(points[2]), 4),
            "max": round(float(points[3]), 4),
            "n": len(values),
        }


@dataclass(frozen=True)
class Symbol:
    """One published marking symbol, in game plan space."""

    code: str
    x: float
    z: float
    # Game heading in degrees clockwise from north (`-Z`).
    #
    # ⚠️ **Converted on the way in, once.** `ANGLE` is a mathematical angle —
    # counter-clockwise from east — and `(90 - ANGLE) mod 360` is the game
    # heading. Measured on the 314 `RM1017` straight-ahead symbols within 4 m of
    # a level-0 centreline: this reading lands **p50 0.9 deg** from the host
    # edge's own heading against 52.0 for the raw value and 38.0 for `ANGLE + 90`.
    # `hong_kong.yaml` carries the table; `tests/test_arrows.py` asserts it
    # against the heading `fares.Snap` publishes, which is `surface.mitres`'s
    # own frame, rather than against this comment.
    heading_deg: float


def read_symbols(
    city: CityConfig,
    spec: Arrows,
    region_id: str,
    transform: GameTransform,
    report: ArrowReport,
    *,
    sources_root: Path | None,
) -> list[Symbol]:
    """Every published turn-arrow symbol in the region, in game plan space.

    Everything refused here is refused on what the *publisher* says — a code
    outside the glyph table, a symbol on a structure, an empty geometry — and
    each refusal is counted rather than logged, because the counts are what
    `Q58` says has to be able to see this stage fail.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    symbols: list[Symbol] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("code"))
        bearings = layer.column(spec.layer.field("bearing"))
        levels = layer.column(spec.layer.field("level"))
        sizes = layer.column(spec.layer.field("size"))
        owners, plan = gdb.points(layer)
        if len(owners) == 0:
            continue
        game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])

        for row, owner in enumerate(owners):
            report.symbols += 1
            code = str(codes[owner])
            if code not in spec.glyphs:
                report.not_a_turn_arrow += 1
                continue
            if str(levels[owner]).strip().lower() not in _AT_GRADE:
                # On a flyover. `Q13` keeps the elevated network closed to
                # driving, so its paint is unreachable, and the nearest level-0
                # edge to a symbol on a deck is the street underneath it.
                report.on_structure += 1
                continue
            x, z, bearing = float(game_x[row]), float(game_z[row]), float(bearings[owner])
            if not (math.isfinite(x) and math.isfinite(z) and math.isfinite(bearing)):
                # `POINT EMPTY` is spelled NaN in WKB and `gdb.points` passes it
                # through by design. Refused here, where the meaning is known.
                report.empty_geometry += 1
                continue
            report.candidates += 1
            size = float(sizes[owner]) if sizes[owner] is not None else float("nan")
            if math.isfinite(size):
                report.symbol_size.append(size)
            symbols.append(Symbol(code=code, x=x, z=z, heading_deg=(90.0 - bearing) % 360.0))
    return symbols


# --------------------------------------------------------------------------
# The glyph
# --------------------------------------------------------------------------

_SIDES = {ARROW_LEFT: -1.0, ARROW_RIGHT: 1.0}


def glyph_polygons(spec: Arrows, movements: tuple[str, ...], length_m: float) -> list[np.ndarray]:
    """One arrow as convex polygons in its own frame, `(u, v)` in metres.

    `+v` is the way the arrow points and `+u` is to its right; the origin is the
    symbol's own published point.

    ⚠️ **The origin is taken to be the glyph's centre, and that is an
    assumption.** The publisher gives an insertion point and a `LENGTH` and does
    not say which end the point is. Centre is the least-wrong reading: if the
    convention is really the tail, an arrow is out by half its length along the
    road it is already on, which no driver navigates by — and anchoring at the
    tail when the truth is the centre is out by twice as much. It is recorded
    here because nothing downstream can detect it.

    Every polygon is wound counter-clockwise in `(u, v)`. `_place` maps that
    frame into the world with a **negative determinant**, so counter-clockwise
    here is clockwise in the `(x, z)` plane, which is what faces `+Y`.
    `ArrowReport.inverted` is what actually holds that end.
    """
    stem_width = spec.stem_width_frac * length_m
    head_length = spec.head_length_frac * length_m
    head_width = spec.head_width_frac * length_m
    reach = spec.branch_reach_frac * length_m
    tip = 0.5 * length_m

    polygons: list[np.ndarray] = []
    if ARROW_AHEAD in movements:
        stem_top = tip - head_length
        polygons.append(
            ccw([(0.0, tip), (-0.5 * head_width, stem_top), (0.5 * head_width, stem_top)])
        )
        # A turn head on an ahead-and-turn glyph hangs below the ahead head, so
        # the two do not overlap into one blob at the top of the stem.
        elbow = stem_top - 0.6 * head_width
    else:
        stem_top = tip - 0.5 * head_width
        elbow = stem_top

    polygons.append(
        ccw(
            [
                (-0.5 * stem_width, -tip),
                (0.5 * stem_width, -tip),
                (0.5 * stem_width, stem_top),
                (-0.5 * stem_width, stem_top),
            ]
        )
    )

    for movement in movements:
        side = _SIDES.get(movement)
        if side is None:
            continue
        shoulder = side * (reach - head_length)
        polygons.append(
            ccw(
                [
                    (0.0, elbow - 0.5 * stem_width),
                    (shoulder, elbow - 0.5 * stem_width),
                    (shoulder, elbow + 0.5 * stem_width),
                    (0.0, elbow + 0.5 * stem_width),
                ]
            )
        )
        polygons.append(
            ccw(
                [
                    (side * reach, elbow),
                    (shoulder, elbow + 0.5 * head_width),
                    (shoulder, elbow - 0.5 * head_width),
                ]
            )
        )
    return polygons


def ccw(points: list[tuple[float, float]] | np.ndarray) -> np.ndarray:
    """The polygon, wound counter-clockwise.

    Winding is corrected rather than hand-kept per shape: a turn head is the
    mirror of its opposite, so half of them come out reversed from the same
    expression, and a reversed one renders as **nothing** under `cull_back`
    rather than as anything a frame would show (`Q58`).
    """
    ring = np.asarray(points, dtype=np.float64)
    shifted = np.roll(ring, -1, axis=0)
    twice_area = float(np.sum(ring[:, 0] * shifted[:, 1] - shifted[:, 0] * ring[:, 1]))
    return ring if twice_area > 0.0 else ring[::-1]


def _place(polygon: np.ndarray, x: float, z: float, heading_deg: float) -> np.ndarray:
    """A glyph polygon in game plan space, at `(x, z)` pointing along `heading_deg`.

    Heading is clockwise from north, and north is `-Z`: forward is
    `(sin h, -cos h)` and right is `(cos h, sin h)`.
    """
    forward, right = _frame(heading_deg)
    return np.array([x, z]) + polygon[:, :1] * right + polygon[:, 1:2] * forward


def nearside(heading_deg: float) -> np.ndarray:
    """The unit vector to the **nearside** of an edge, in game plan space.

    Nearside is *left* of travel — the rail `surface.mitres` offsets to, and the
    side `Snap.offset_m` is positive on.

    ⚠️ **Public, and spelled exactly once, because a flip here mirrors every
    side-keyed feature in the city and still renders as a city.** `_frame`'s own
    docstring records that this vector was written out three times in the first
    draft of this module and that "a sign fix lands in two of three places"; it
    was then written a fourth time in `pipeline/signs.py`, which is what made it
    public. `tests/test_signs.py` pins it against `surface.mitres` itself rather
    than against this comment.
    """
    return -_frame(heading_deg)[1]


def _frame(heading_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Forward and right in game plan space, for a heading clockwise from north.

    The one place this module spells the `-Z`-is-north convention. It was
    written out three times in the first draft — in `_place`, in `_draw`, and
    once negated as the nearside in `build_region` — which is how a sign fix
    lands in two of three places.
    """
    heading = math.radians(heading_deg)
    return (
        np.array([math.sin(heading), -math.cos(heading)]),
        np.array([math.cos(heading), math.sin(heading)]),
    )


class _Builder:
    """Accumulates flat convex polygons into one mesh.

    Simpler again than `tramway.py`'s: every polygon is horizontal and convex,
    so a fan from its first vertex triangulates it, and the normal is up.

    ⚠️ **Position and normal only — no `COLOR_0`, no `TEXCOORD_0`, no
    `TEXCOORD_1`.** The colour is authored in `game/tuning/arrows.tres` beside
    the markings it matches, for the reason `config.Arrows` records: `Q53`
    deliberately kept paint out of the `materials:` table. And there is no codec
    to carry — `roads.glb` needs nine packed fields because a fragment there has
    to work out which lane it is in, and every vertex here is already at the
    position the stage decided.

    ⚠️ **The first draft shipped a `TEXCOORD_0` of glyph-local metres that
    `arrows.gdshader` never read**, on the reasoning that a later shader might
    want it. That is precisely what `Q54` found `COLOR_0.a` had been doing —
    broadcasting an unread 255 down the whole road mesh — and it cost 59 KB of a
    257 KB asset. A channel earns its place when something reads it.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def polygon(self, plan: np.ndarray, height: np.ndarray) -> None:
        span = len(plan)
        if span < 3:
            return
        base = self._count
        fan = np.arange(1, span - 1)
        self._triangles.append(
            np.column_stack([np.zeros(len(fan), dtype=np.int64), fan, fan + 1]) + base
        )
        self._positions.append(np.column_stack([plan[:, 0], height, plan[:, 1]]))
        self._count += span

    def build(self, name: str) -> MeshData | None:
        if not self._triangles:
            return None
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.tile(np.array([0.0, 1.0, 0.0], dtype=np.float32), (self._count, 1)),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            material=ARROWS_MATERIAL,
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        return select_triangles(mesh, twice_area > _MIN_TWICE_AREA_M2)


@dataclass(frozen=True)
class Ribbon:
    """What `surface.py` drew for one edge, as a consumer needs to read it.

    ⚠️ **Public because `pipeline/signs.py` reads it too**, and reads it for the
    same reason: the drawn half-width is `surface.py`'s answer after the widening
    and after `Q23`'s per-station adjustment, so a second implementation of it
    would be a second join in `Q56`'s sense — disagreeing would tell us one was
    wrong and never which.
    """

    lanes: int
    one_way: bool
    # Normalised distance along the published polyline at each station, and the
    # drawn half-width there. Per station rather than per edge because `Q23`
    # widens the ribbon station by station.
    at: np.ndarray
    half_width_m: np.ndarray
    # The centreline itself, `(n, 2)` as `(x, z)` per station. ⚠️ **Carried so a
    # consumer can take the foot of a snap from the polyline rather than
    # reconstruct it** — see `foot_at`.
    plan: np.ndarray
    # Deck height at each of those stations, straight off the published
    # polyline. ⚠️ **This is what an arrow's height comes from, rather than a
    # fresh snap at its nose and tail.** A second snap is a second join with no
    # memory of the host edge: measured, **43 of 747** arrows took at least one
    # endpoint from a *different* edge, disagreeing with the ribbon they are
    # drawn on by up to **0.515 m** against a `lift_m` of 0.015. Interpolating
    # here reproduces `Snap.y` to 1.8e-15 m, because it is the same linear
    # interpolation — it is a faithful substitute, not an approximation.
    height_m: np.ndarray
    trim_start_m: float
    trim_end_m: float
    length_m: float

    def half_width_at(self, t: float) -> float:
        """The drawn half-width at a normalised position along the edge."""
        return float(np.interp(t, self.at, self.half_width_m))

    def foot_at(self, t: float) -> np.ndarray:
        """The point on the centreline at `t`, in game plan space.

        ⚠️ **Read from the polyline, never reconstructed as
        `point - offset_m * nearside`.** `Snap.offset_m` is `±distance_m` to the
        **clamped** projection, so for anything past an edge's end the
        displacement has an along-edge component and that subtraction lands off
        the centreline. Measured on an edge from (0,0) to (100,0) with a point at
        (105, 0) — dead on the axis, 5 m past the end — the reconstruction gives
        (105, -5), five metres off a road the point is standing in the middle of.
        Where the snap did not clamp the two agree to the bit.
        """
        return np.array(
            [
                float(np.interp(t, self.at, self.plan[:, 0])),
                float(np.interp(t, self.at, self.plan[:, 1])),
            ]
        )


def ribbons(graph: dict, surface: dict) -> dict[int, Ribbon]:
    """The drawn ribbon, keyed by edge id.

    ⚠️ **Read from `roadsurface.json` rather than recomputed.** The drawn
    half-width is `surface.py`'s answer after the widening and after `Q23`'s
    per-station adjustment, and a second implementation of it here would be a
    second join in `Q56`'s sense — disagreeing would tell us one was wrong and
    never which.
    """
    widths = {int(entry["edge"]): entry for entry in surface["carriageway"]}
    drawn_ribbons: dict[int, Ribbon] = {}
    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        drawn = widths.get(int(edge["id"]))
        if drawn is None:
            continue
        points = np.asarray(edge["polyline"], dtype=np.float64)
        along = plan_lengths(points)
        total = float(along[-1])
        half = np.asarray(drawn["half_width_m"], dtype=np.float64)
        if total <= 0.0 or len(half) != len(along):
            # A width list that does not match the polyline it was measured on
            # is a contract break, not a rounding problem. Skipped rather than
            # interpolated across, and visible as a symbol that found no lane.
            continue
        trim = drawn.get("trim_m") or [0.0, 0.0]
        drawn_ribbons[int(edge["id"])] = Ribbon(
            lanes=int(edge["lanes"]),
            one_way=str(edge["direction"]) != "both",
            at=along / total,
            half_width_m=half,
            plan=np.column_stack([points[:, 0], points[:, 2]]),
            height_m=points[:, 1],
            trim_start_m=float(trim[0]),
            trim_end_m=float(trim[1]),
            length_m=total,
        )
    return drawn_ribbons


def directed_residual_deg(a: float, b: float) -> float:
    """How far heading `a` is from heading `b`, in `[0, 180]`.

    The signed question: *does this arrow point the way its edge is drawn?* Only
    a one-way host may answer it, which is why `build_region` reads it and then
    reads `axis_residual_deg` for the other one.

    ⚠️ **Public because `pipeline/signs.py` reads it too.** These three — this,
    `axis_residual_deg` and `ccw` — are the canonical statement of conventions
    more than one stage shares, so they are imported rather than restated, the
    way `railings.AT_GRADE` and `ArrowReport.measured` already are.
    """
    return abs((a - b + 180.0) % 360.0 - 180.0)


def axis_residual_deg(a: float, b: float) -> float:
    """How far two headings are from sharing an axis, in `[0, 90]`.

    ⚠️ **Folded modulo 180 on purpose.** The question this answers is "did the
    symbol match a road it is actually on", and an arrow on the far side of a
    two-way street legitimately points the other way down the same axis.
    Refusing on the *directed* residual would throw away half the arrows on
    every two-way street; the region's `direction = both` hosts split 52/48
    when it was measured.
    """
    gap = directed_residual_deg(a, b)
    return min(gap, 180.0 - gap)


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> ArrowReport:
    """Read the region's published turn arrows and write its `arrows.glb`."""
    spec = city.arrows
    report = ArrowReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the same shape `tramway` takes: a city whose estate
        # publishes no marking symbols ships none rather than inferring them.
        log.info("city '%s' declares no arrows block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    symbols = read_symbols(city, spec, region_id, transform, report, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # ⚠️ **Through `read_document`, not a bare parse.** Every arrow's lane comes
    # from `half_width_m` in here, so a manifest from a build before
    # `SURFACE_MANIFEST_SCHEMA` 4 — when that field was one number rather than
    # one per station — would register the whole region against another build's
    # widths and report `drawn` normally. That is the failure `documents.py`
    # exists to stop, and `clearance.py` reads the same document the same way.
    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --city {city.id} --region {region_id}",
    )
    drawn = ribbons(graph, surface)
    # Level 0 only, the same restriction `kerbside.py` and `tramway.py` both
    # make: for 7% of the kerbside samples the nearest edge of *any* level was
    # elevated, and the street the marking is actually on was a median 4 m away.
    segments = Segments.of([edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0])
    lane_width_m = city.roads.lane_width_m

    builder = _Builder()
    for symbol in symbols:
        snap = segments.nearest(symbol.x, symbol.z)
        if snap.distance_m > spec.max_offset_m:
            report.too_far += 1
            continue
        residual = axis_residual_deg(symbol.heading_deg, snap.heading_deg)
        # ⚠️ **Recorded before the refusal, not after**, and the order is the
        # whole value of the number. Appending it below the guard would confine
        # every percentile to `bearing_tolerance_deg` **by construction** — the
        # exact trap `Q58` recorded when `drawn_gauge_m` was published as the
        # tramway join's detector and could not read outside `pair_tolerance_m`.
        # Published from here, the distribution's tail is the population that
        # matched badly, and `off_bearing` counts what it cost.
        report.axis_residual_deg.append(residual)
        report.offset_m.append(abs(snap.offset_m))
        if residual > spec.bearing_tolerance_deg:
            # Matched a road it is not on. Refused, never rotated onto it.
            report.off_bearing += 1
            continue
        ribbon = drawn.get(snap.edge)
        if ribbon is None or ribbon.lanes < 1:
            report.no_lane += 1
            continue

        directed = directed_residual_deg(symbol.heading_deg, snap.heading_deg)
        if ribbon.one_way and directed > 90.0:
            # ⚠️ **Refused, not recorded.** An arrow pointing against a one-way
            # street is not a thing the world contains, so this symbol has
            # either matched the wrong edge or found a one-way the graph has
            # backwards — and both mean drawing it would assert something false
            # on a street the `P3-9a` drivers know.
            #
            # Measured, the population is two shapes. Most of it is an opposed
            # carriageway pair — Fleming Road, Tonnochy Road — where the arrow
            # belongs to the *other* ribbon a few metres away and the axis test
            # cannot see it, because the two ribbons are parallel by
            # construction. The rest sit 2 m from a street whose own direction
            # is the thing in doubt.
            #
            # Re-matching to the nearest edge that agrees would recover them and
            # is deliberately not done: it would move an arrow onto a road
            # nothing checked, and `GAME_DESIGN.md` prices a missing arrow at
            # nothing against a misplaced one. The count is the finding.
            report.against_one_way += 1
            continue
        if not ribbon.one_way:
            report.drawn_on_two_way += 1

        # The published offset read as a fraction of the carriageway rather than
        # as a distance — the one step that survives the 1.6x widening, because
        # the ribbon is drawn wider about the same centreline.
        real_half_m = 0.5 * ribbon.lanes * lane_width_m
        fraction = max(-1.0, min(1.0, snap.offset_m / real_half_m))
        # `U` is `TEXCOORD_0`'s lane coordinate: 0 at the nearside kerb, `lanes`
        # at the offside. `offset_m` is positive to the nearside, so the two run
        # opposite ways and `U = lanes * (1 - fraction) / 2` is the conversion.
        lane = max(0, min(ribbon.lanes - 1, int(0.5 * ribbon.lanes * (1.0 - fraction))))
        centre_u = lane + 0.5

        glyph = spec.glyphs[symbol.code]
        along_m = snap.t * ribbon.length_m
        half_width_m = ribbon.half_width_at(snap.t)
        drawn_offset_m = half_width_m * (1.0 - 2.0 * centre_u / ribbon.lanes)
        report.lane_shift_m.append(abs(drawn_offset_m - snap.offset_m))
        if abs(snap.offset_m) > half_width_m:
            report.outside_drawn_ribbon += 1

        # The deck under the arrow's two ends, off the host edge's own polyline.
        # ⚠️ **The sign is load-bearing.** `axis_residual_deg` folds modulo 180,
        # so an arrow on the far side of a two-way street legitimately points
        # *backwards* along its edge — and without this its nose and tail heights
        # come out swapped, tilting it against the grade instead of with it.
        half_t = 0.5 * glyph.length_m / ribbon.length_m
        if directed > 90.0:
            half_t = -half_t
        y_tail = float(np.interp(snap.t - half_t, ribbon.at, ribbon.height_m))
        y_nose = float(np.interp(snap.t + half_t, ribbon.at, ribbon.height_m))
        if along_m < ribbon.trim_start_m or along_m > ribbon.length_m - ribbon.trim_end_m:
            report.over_a_cap += 1

        # Nearside is *left* of travel — `U = 0` is the rail `surface.mitres`
        # offsets to the left — so it is `-right` in the edge's own frame.
        near = nearside(snap.heading_deg)
        centreline = np.array([symbol.x, symbol.z]) - snap.offset_m * near
        placed = centreline + drawn_offset_m * near

        _draw(builder, spec, symbol, glyph, placed, y_tail, y_nose)
        report.drawn += 1
        key = "+".join(glyph.movements)
        report.by_glyph[key] = report.by_glyph.get(key, 0) + 1

    mesh = builder.build(ARROWS_MESH_NAME)
    if mesh is not None:
        report.inverted, report.inverted_area_m2 = downward_facing(mesh)
        report.triangles = mesh.triangle_count
        report.vertices = len(mesh.positions)
        low, high = mesh.aabb()
        report.aabb = [list(low), list(high)]
        report.bytes = write_glb(out_dir / ARROWS_NAME, [mesh])

    _write_manifest(out_dir, city, region_id, report)
    return report


def _draw(
    builder: _Builder,
    spec: Arrows,
    symbol: Symbol,
    glyph: ArrowGlyph,
    placed: np.ndarray,
    y_tail: float,
    y_nose: float,
) -> None:
    """One arrow, laid between its two deck heights and lifted clear of them.

    ⚠️ **Interpolated between the ends rather than laid flat at the centre.** A
    4 m glyph laid flat on a 5% grade stands 0.1 m proud at one end and 0.1 m
    under the road at the other, and `lift_m` is 0.015 — the sunk end simply
    disappears. Two heights rather than one per vertex because the longitudinal
    slope is the one that matters and the cross-slope is camber.
    """
    for polygon in glyph_polygons(spec, glyph.movements, glyph.length_m):
        plan = _place(polygon, float(placed[0]), float(placed[1]), symbol.heading_deg)
        # `v` runs from `-length / 2` at the tail to `+length / 2` at the nose.
        ramp = 0.5 + polygon[:, 1] / glyph.length_m
        builder.polygon(plan, y_tail + ramp * (y_nose - y_tail) + spec.lift_m)


def _write_manifest(out_dir: Path, city: CityConfig, region_id: str, report: ArrowReport) -> int:
    document = {
        "schema_version": ARROWS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what `CITY_SCHEMA`
        # 11 was bumped over.
        "asset": ARROWS_NAME if report.drawn else None,
        # The read, as four disjoint parts of `symbols`.
        "symbols": report.symbols,
        "not_a_turn_arrow": report.not_a_turn_arrow,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "candidates": report.candidates,
        # The join, as five disjoint parts of `candidates`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        "off_bearing": report.off_bearing,
        # ⚠️ **A refusal and a finding at once.** See `build_region`: an arrow
        # against a one-way street cannot be true, so it is dropped — but the
        # count is where an opposed-pair mismatch and a backwards one-way both
        # land, and it is to be gone and looked at rather than tuned against.
        "against_one_way": report.against_one_way,
        "no_lane": report.no_lane,
        "by_glyph": dict(sorted(report.by_glyph.items())),
        # ⚠️ **Recorded over every symbol that found a host, including the ones
        # `off_bearing` then threw away** — so it can read past
        # `bearing_tolerance_deg`, which is the only way it says anything. A
        # distribution taken after its own filter is confined to that filter by
        # construction, which is what stopped `drawn_gauge_m` being able to see
        # a bad tramway join (`Q58`). p90/p99/max rather than a median for the
        # matching reason: the tail is the finding, and a median near zero is
        # also what a wholly broken join looks like.
        #
        # `off_bearing` beside it is what the tail cost.
        "axis_residual_deg": report.measured(report.axis_residual_deg),
        # What `max_offset_m` is set against, published so the config's comment
        # is checkable against a shipped artefact rather than a scratch script.
        "offset_m": report.measured(report.offset_m),
        "drawn_on_two_way": report.drawn_on_two_way,
        "outside_drawn_ribbon": report.outside_drawn_ribbon,
        # What the lane registration moved. The residue of the decision at the
        # top of `arrows.py`, published so that decision can be re-argued
        # against a number rather than against the prose.
        "lane_shift_m": report.measured(report.lane_shift_m),
        "over_a_cap": report.over_a_cap,
        # Published, unread. `SYMBOL_SIZE` may or may not be the arrow's length
        # in metres; the glyph table takes its lengths from the index plan
        # instead. Recorded here so the question is answerable from a shipped
        # artefact — `Q37`'s debt, which `Q55` was the last instance of.
        "symbol_size": report.measured(report.symbol_size),
        # ⚠️ **Must be 0.** `arrows.gdshader` is `cull_back`, so winding decides
        # visibility and the normal attribute does not. The tramway shipped
        # 5,111 of 5,112 triangles facing the ground with everything else
        # correct, and the city simply had no tramway in it.
        "inverted": report.inverted,
        "inverted_area_m2": round(report.inverted_area_m2, 4),
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
    }
    return write_document(out_dir / ARROWS_MANIFEST_NAME, document)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_city(args.city)
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "arrows: %d symbols -> %d turn arrows drawn (%d too far, %d off bearing), %d triangles",
        report.symbols,
        report.drawn,
        report.too_far,
        report.off_bearing,
        report.triangles,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
