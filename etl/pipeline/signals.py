"""Published traffic-signal heads, drawn as their own mesh (`P3-17`).

The signal half of the dTAD estate, landing in `Q58`/`Q59`'s pattern: one
primitive, one draw call, no collider, an optional `city.json` key, and counters
the stage publishes about itself. It is `signs.py`'s smaller sibling — no
`GG_NAME` join, no pole layer, no face table, no atlas — and the four findings
that make it different belong at the top of the file.

🔴 **NOTHING PUBLISHED DEFINES THIS LAYER'S VOCABULARY, and the whole stage is
shaped around that.** `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has no domain: the fgdb
data specification gives the column eight characters of untyped text. The Index
Plan set that defines every `RM` marking code and every `TS` sign carries no
signal sheet — both "Miscellaneous Details" sheets (`CT174/51-6(1)E`) were
rendered and read, and they are the `RS/S/` sign-pictogram tables, scans
besides. `hk-traffic-sign-map`'s `signCatalogue.json`, which was `P3-16`'s
cross-check, is `TS`-only and carries none of these codes.

So there is no `Q59` transcription available here, and the code is read as a
**gate** — head or not head — and never as a look. All 33 of the region's 46
codes that pass the gate draw the *same* head. This stage does not claim `P24`
is a different signal from `P01`, because nothing published says so and `Q54`
debits exactly that invention. `drawn_by_code` and `refused_by_code` publish the
whole vocabulary instead, which is what makes the weakest-evidenced rule in the
bundle reviewable — `railings.py`'s refused metres, at a second layer.

🔴 **`ANGLE` IS NOT A FACING, AND IT WAS MEASURED HERE RATHER THAN ASSUMED.**
`PROGRESS.md` told this task to assume `P3-16`'s finding until it had been
checked on this layer, and the check is the reason it is stated as fact:
measured over the region, in the frame `arrows.py` validated to p50 0.9 degrees,
the angle sits **flat** against the road — p50 **44.3 degrees** from the host
edge axis, **21.3%** within 20 degrees of along it and **19.3%** within 20 of
across, against 22.2% for a uniform distribution. That is `DTAD_TS_ABV_PT`'s own
result to within noise.

So `ANGLE` is read, published as `axis_residual_deg`, and **consumed by
nothing** — `arrows.py`'s `symbol_size` pattern, so the claim stays answerable
from a shipped artefact rather than from a scratch script (`Q37`), and a
publisher who starts populating it properly shows up as a mode appearing.

⚠️ **The one cross-check this layer looks like it offers cannot be made.**
`DTAD_TRAFFIC_LIGHT_LINE` is the same cells *dropped to graphics* — 53 features
in region — so comparing a dropped cell's drawn axis against its point's `ANGLE`
would test the cell rotation directly, without going through the road graph. But
that layer publishes `SIGNID` **null on all 53** and carries no other key, so
pairing a cell to its point is a nearest-neighbour guess: a second join in
`Q56`'s sense, and the move `signs.py` refuses when `GG_NAME` resolves to more
than one pole. Recorded so the next reader does not spend the hour again.

✅ **Unlike `signs.py`, the published point IS the object.** There is no
abbreviation layer here and no pole layer to join to — lights do not stand on
`DTAD_TS_POLE_PT` poles (nearest TS pole p50 **7.59 m**, only **5 of 913**
coincident) — and this layer carries no `GG_NAME` at all. Position is read
straight from the point, so there is no `pole_offset_m` and no `pole_too_far`.

⚠️ **What replaces `GG_NAME` is coincidence, and it is DERIVED rather than
read.** **470 of 913** points sit within 0.05 m of another, and clustering at
1 m gives **553** assemblies (272 singletons, 220 pairs, 46 triples, 12 quads, 3
fives) — one surveyed post carrying a stack of aspects, which is the real
object. That is a grouping this stage *chose*, not one the publisher declared,
so `assembly_size` publishes what it did and the numbers above are what it is
read against. ⚠️ **Those 553 are the whole layer and `assembly_size` is the
admitted subset** — the gate and the level-0 filter come off first, leaving 514,
so the two do not match and neither is wrong.

⚠️ **The position is registered, not read** — `Q60`'s move arriving at a third
layer, after the railings and the signs. **72.7%** of the region's signal points
are surveyed inside the drawn 1.6x ribbon, a median **1.48 m** past the drawn
kerb, so drawn where published nearly three quarters of the city's signals stand
in the road. `shift_m` is the price and is published rather than asserted small.

⚠️ **What is derived, and what it costs.** Identity and position are read. Only
the **facing** is derived, and the rule is not new: `signs.facing_from_side`,
imported rather than copied. A head addresses the traffic approaching its stop
line — the traffic already legally proceeding — which is exactly the case a
regulatory plate is in, so there is no `faces_against_traffic` equivalent here
and inventing one would be `Q72` run backwards. ⚠️ **It is still ungraded**
(`Q62`): there is no published subset to check a facing against, so the evidence
is an A/B render at one camera.

🔴 **No signal state, and that is a decision rather than a gap.** No dataset
publishes timing, an invented cycle *instructs*, and nothing obeys it — there is
no traffic before `P3-3` and no player consequence by genre design. The lenses
are drawn in inert colours: a head with its lamps off, which is a real thing a
driver sees, where a lit red at every junction would be an instruction this game
cannot honour. The named route for state is `P3-11d`'s `instance uniform` lamp
circuit, wired in `B3`.
"""

from __future__ import annotations

import argparse
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ⚠️ **Imports from sibling stages rather than copies**, the shape `signs.py`
# already takes. `AT_GRADE` is the source's own encoding of "no structure" and
# is not config; `facing_away` asks whether winding agrees with the given
# normal, which is the question a *vertical* surface needs; `nearside`,
# `ArrowReport.measured` is a canonical statement of
# conventions this stage shares; and `facing_from_side` is the derivation
# itself — a second copy of it is a second city, mirrored (`Q56`).
from pipeline import gdb
from pipeline.arrows import ArrowReport, Ribbon, nearside, ribbons
from pipeline.config import SIGNAL_BODY_COLOUR, Config, GameTransform, Signals, load_config
from pipeline.documents import read_document, write_document
from pipeline.fetch import source_reads
from pipeline.gltf import MeshData, write_glb
from pipeline.mesh import select_triangles
from pipeline.polyline import Segments, Snap, axis_residual_deg, game_heading_deg
from pipeline.railings import AT_GRADE, facing_away
from pipeline.roads import ROADGRAPH_NAME, read_graph
from pipeline.signs import disc, facing_from_side, plate_frame
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

SIGNALS_NAME = "signals.glb"
SIGNALS_MANIFEST_NAME = "signals.json"
SIGNALS_MANIFEST_SCHEMA = 1
SIGNALS_MESH_NAME = "signals"
# The glTF material name `tools/generated_scene_import.gd` dispatches on, and
# the one channel the format offers for it. ⚠️ **A name, not a shader**: this
# layer shares `signs.gdshader` and differs only in the uniforms
# `game/tuning/signals.tres` sets, which is `Q61`'s rule for the railing classes
# and `Q71`'s for the three paint layers — a layer is a parameterisation.
SIGNALS_MATERIAL = "signals"

# Degenerate triangles are dropped rather than shipped, `signs.py`'s constant
# and its reason: a zero-area triangle has no normal, so `facing_away` cannot
# grade it and it would sit in the count forever.
_MIN_TWICE_AREA_M2 = 1e-6


@dataclass
class SignalReport:
    """What the stage read, gated, assembled, registered and drew.

    ⚠️ **The counters are what can see this stage fail, because none of its
    failures look like anything in a frame** — `Q58`'s lesson, and signals are
    as bad as signs for it. A head turned 180 degrees is a perfectly drawn head.
    A head on the wrong street is a perfectly drawn head. A gate that started
    admitting push buttons draws perfectly good signals on them.

    The partitions:

        features   == not_whitelisted + on_structure + empty_geometry
                      + candidates
        candidates == drawn + too_far + no_ribbon + over_shift + in_carriageway
    """

    features: int = 0
    # 🔴 **The gate's refusals, and the big number here is a DECISION.** 70 of
    # the region's 913: the 51 features that are not signal heads at all
    # (`KLBOLL` keep-left bollards, `PBUTT` push buttons, `WIGWAG`) and the 19
    # `M<n>` this pipeline declines to call heads. `refused_by_code` is where a
    # reviewer sees which.
    not_whitelisted: int = 0
    on_structure: int = 0
    empty_geometry: int = 0
    candidates: int = 0

    drawn: int = 0
    too_far: int = 0
    # ⚠️ **These three are FEATURES, like every other member of the partition
    # including `drawn`** — a post refuses everything it carries at once, so each
    # accumulates `len(carried)`. The post-level counts are `posts_over_shift`
    # and `posts_in_carriageway` below. 🔴 The word "heads" was used here for the
    # unit `posts_drawn` measures and again for the unit these measure, in one
    # file, on the counters whose units are load-bearing.
    no_ribbon: int = 0
    over_shift: int = 0
    # 🔴 Heads on posts still standing in the drawn carriageway after
    # registration, where several widened ribbons overlap and no footway
    # survives. A finding about `Q19`'s widening, not about this stage.
    in_carriageway: int = 0

    posts_drawn: int = 0
    posts_over_shift: int = 0
    posts_in_carriageway: int = 0
    # Posts folded together *after* registration pushed them onto one point.
    # ⚠️ **A different population from the coincidence clustering**, which runs
    # over surveyed positions before anything moves — see `_assemble`.
    posts_merged_after_shift: int = 0
    # 🔴 **What each of those folds cost, in degrees of facing.** The survivor's
    # facing wins, so a merge across two posts derived from different host edges
    # silently re-aims one of them. Eleven of this region's twelve merges agree
    # to 0.0 and one is 94.9 — a head addressing traffic at right angles to what
    # its absorbed aspect was derived for. Report-only: the merge is still
    # right, because two posts on one point cannot both be drawn, and this is
    # the number that says what was given up (`Q58`'s rule — publish the residual
    # of any move this stage makes).
    merged_facing_deg: list[float] = field(default_factory=list)

    # ⚠️ **How far each post moved sideways onto the drawn kerb**, recorded over
    # every registered post **including the ones `max_shift_m` then refused**,
    # so `n` exceeding `posts_drawn` is the proof it can read outside its own bar
    # (`Q58`). This is the price of the registration and `Q60` is the precedent
    # for publishing it rather than asserting it is small.
    shift_m: list[float] = field(default_factory=list)
    # How far inside the drawn carriageway each post was surveyed. The
    # measurement that forced the registration: 0 means it was already outside.
    inside_ribbon_m: list[float] = field(default_factory=list)

    # 🔴 **The gate's effect over the whole vocabulary, both halves.** This is
    # what makes a whitelist read off code strings reviewable rather than
    # asserted: a reader who finds `PBUTT` in `drawn_by_code` knows the spelling
    # rule broke, and one who finds `P24` in `refused_by_code` knows it broke the
    # other way. Neither is visible in a frame.
    #
    # ⚠️ **`refused_by_code` counts the gate alone**, not the level or geometry
    # refusals — it answers "which codes did the whitelist turn away", and
    # folding the other refusals in would make it answer nothing.
    drawn_by_code: dict[str, int] = field(default_factory=dict)
    refused_by_code: dict[str, int] = field(default_factory=dict)

    # 🔴 **Published, unread — and its flatness is the whole point.** How far
    # each head's `ANGLE` axis sits from its host edge's axis, in `[0, 90]` where
    # 0 is along the road and 90 is across it. See the module docstring for the
    # measurement. ⚠️ **Recorded over every candidate**, not only the drawn ones:
    # a distribution taken after a filter is confined to that filter (`Q58`'s
    # `drawn_gauge_m` trap).
    axis_residual_deg: list[float] = field(default_factory=list)
    # How far each **hosted** post sat from the level-0 centreline it matched —
    # recorded before the `over_shift` and `in_carriageway` refusals, so `n`
    # exceeds `posts_drawn` for `shift_m`'s reason (`Q58`). What `max_offset_m` is
    # set against, published so the config comment is checkable against a shipped
    # artefact rather than a scratch script (`Q37`).
    host_distance_m: list[float] = field(default_factory=list)
    # 🔴 **Posts with a SECOND level-0 edge within `host_ambiguity_m`.** A signal
    # head stands at a junction *mouth*, which is exactly where nearest-edge
    # hosting is weakest: `roadmarks.py` measured the same geometry picking the
    # road it is parallel to on 43% of its layer (`Q69`) and answered it with a
    # transverse pick. A head is not drawn *across* anything, so it has no such
    # second rule and this counter is the instrument instead.
    #
    # ⚠️ **Report-only, and never a bar.** A crowded junction is a fact about the
    # city rather than a defect in the join, which is why this counts rather than
    # refuses (`Q56`). It has no prior number to be compared against: a high
    # reading on the first build is a finding to go and look at.
    host_ambiguous: int = 0

    # 🔴 **How many heads each assembly carried, and it is a DERIVED grouping.**
    # This layer publishes no `GG_NAME`, so a post is a cluster of coincident
    # points rather than a declared group — see `_assemble`. Published because
    # nothing else can see that clustering go wrong: a radius that collapsed two
    # real posts draws one post with six aspects on it, which renders perfectly.
    assembly_size: dict[str, int] = field(default_factory=dict)

    # Triangles whose winding disagrees with the normal they were given.
    # ⚠️ **Must be 0.** `signs.gdshader` is `cull_back`, so winding decides
    # visibility: the tramway shipped 5,111 of 5,112 triangles facing the ground
    # with everything else correct, and the city simply had no tramway in it.
    facing_away: int = 0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)

    # Reused rather than restated, the line `signs.py`, `railings.py` and
    # `boxjunctions.py` all carry: p90/p99/max beside the median is `arrows.py`'s
    # choice and its reason — every distribution here is a residual whose **tail**
    # is the finding, and a median near zero is also what a wholly broken join
    # looks like.
    measured = staticmethod(ArrowReport.measured)


@dataclass(frozen=True)
class Signal:
    """One published signal head, at the point the publisher surveyed."""

    code: str
    x: float
    z: float
    # `(90 - ANGLE)` as a game heading, converted once on the way in.
    # 🔴 **Read, published, and consumed by nothing** — see the module docstring.
    axis_deg: float


# --------------------------------------------------------------------------
# The read
# --------------------------------------------------------------------------


def read_signals(
    city: Config,
    spec: Signals,
    region_id: str,
    transform: GameTransform,
    report: SignalReport,
    *,
    sources_root: Path | None,
) -> list[Signal]:
    """Every head the gate admits, at its published position.

    Everything refused here is refused on what the *publisher* says — a code the
    gate does not admit, a feature on a structure, an empty geometry — and each
    refusal is counted rather than logged, because the counts are what `Q58`
    says has to be able to see this stage fail.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)
    bbox = city.projected_bounds(region_id).bbox

    signals: list[Signal] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("code"))
        bearings = layer.column(spec.layer.field("bearing"))
        levels = layer.column(spec.layer.field("level"))
        owners, plan = gdb.points(layer)
        if len(owners) == 0:
            continue
        game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])

        for row, owner in enumerate(owners):
            report.features += 1
            code = str(codes[owner])
            if not spec.is_head(code):
                # The gate doing its work. 70 of the region's 913 land here: 51
                # objects that are not signal heads and 19 `M<n>` this pipeline
                # declines to call heads. Counted per code, because the gate is
                # a rule about spelling that nothing published grades.
                report.not_whitelisted += 1
                report.refused_by_code[code] = report.refused_by_code.get(code, 0) + 1
                continue
            if str(levels[owner]).strip().lower() not in AT_GRADE:
                # On a structure. `Q13` keeps the elevated network closed to
                # driving, so the head is unreachable and the nearest level-0
                # edge to it is the street underneath.
                #
                # ⚠️ **Null is the NORMAL value on this layer** — 906 of the
                # region's 913, against 7 reading `A01` — where on the sign layer
                # it is the exception. `AT_GRADE` admits it either way; said here
                # because a reader who knows `signs.py` reads the nulls as a bug.
                report.on_structure += 1
                continue
            x = float(game_x[row])
            z = float(game_z[row])
            if not (math.isfinite(x) and math.isfinite(z)):
                # `POINT EMPTY` is spelled NaN in WKB and `gdb.points` passes it
                # through by design. Refused here, where the meaning is known.
                report.empty_geometry += 1
                continue
            # ⚠️ **A null `ANGLE` is not a refusal**, and that follows from the
            # finding rather than from leniency: nothing consumes it, so refusing
            # the 8 nulls would discard 8 perfectly locatable heads over a field
            # this stage does not use.
            bearing = float(bearings[owner]) if bearings[owner] is not None else float("nan")

            report.candidates += 1
            signals.append(Signal(code=code, x=x, z=z, axis_deg=game_heading_deg(bearing)))
    return signals


def _assemble(signals: list[Signal], merge_m: float) -> list[tuple[float, float, list[Signal]]]:
    """Coincident heads grouped into the posts they stand on.

    🔴 **This is the one join `signs.py` gets from the publisher and this stage
    has to derive.** `DTAD_TS_ABV_PT` carries `GG_NAME` — the specification's
    *"Graphical group Name"* — and `DTAD_TRAFFIC_LIGHT_PT` carries nothing of the
    kind. What it does carry is coincidence: **470 of the region's 913** points
    sit within 0.05 m of another, and clustering at 1 m gives **553** groups of
    1 to 5. That is a signal post with a stack of aspects on it, which is the
    real object.

    ⚠️ **Single-linkage, and the radius is doing real work.** Two posts at
    opposite kerbs of a junction are metres apart and never merge; two aspects on
    one post are centimetres apart and always do. `assembly_size` publishes the
    result because nothing else can see it go wrong — a radius that swallowed a
    neighbouring post would draw one post carrying six aspects, which renders
    perfectly.

    Sorted so the grouping is the source's rather than the read order's: a mesh
    that changes shape between two builds of the same data is not reproducible.
    """
    if not signals:
        return []
    points = np.array([[signal.x, signal.z] for signal in signals])
    # O(n^2) over the region's ~850 admitted heads: 722k distance comparisons in
    # one vectorised pass, 0.029 s and 17 MB, which is 1.5% of the stage.
    #
    # ⚠️ **That comparison holds at this size and INVERTS above it.** The
    # road-graph sweep is O(posts x segments) and runs per *post* (514 here, not
    # per feature); this is O(heads^2). Held density it measures 0.13 s / 216 MB
    # at 3,000 heads, 0.77 s / 2.4 GB at 10,000 and **9.6 GB at 20,000** — it does
    # not get slow, it dies. A uniform cell hash at `assembly_merge_m` with a 3x3
    # neighbour scan is the fix and it is **exact**, not approximate: a pair
    # within the radius cannot fall outside the nine cells. `tramway.py` and
    # `kerbside.py` already ship that pattern.
    #
    # ⚠️ **Left because regions are bounded**: `read_signals` pushes the region
    # bbox into OGR, so the territory's 37,167 features only ever reach this in
    # one call if somebody declares a territory-sized region. `signs._merge_posts`
    # records the same arithmetic and the same decision.
    spread = np.hypot(
        points[:, None, 0] - points[None, :, 0], points[:, None, 1] - points[None, :, 1]
    )
    close = spread <= merge_m

    seen: set[int] = set()
    posts: list[tuple[float, float, list[Signal]]] = []
    for index in range(len(signals)):
        if index in seen:
            continue
        stack = [index]
        members: list[int] = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            members.append(current)
            stack.extend(int(other) for other in np.nonzero(close[current])[0])
        # ⚠️ **Sorted although nothing downstream reads the order any more.** It
        # was load-bearing while heads stacked up the post; since the collapse to
        # one head per assembly the geometry uses only the centroid and the
        # facing, and `drawn_by_code` is sorted at the end. Kept because
        # `_merge_placements` is greedy and first-wins, so a stable input keeps
        # two builds of one input identical — the `posts.sort` below is what
        # carries that, and this makes the tuple it sorts deterministic too.
        carried = sorted((signals[member] for member in members), key=lambda item: item.code)
        # The post stands at the centroid of what it carries. ⚠️ **Not the first
        # member's position**: that would make the post's place depend on the
        # read order, and two builds of the same data would differ.
        centre = points[members].mean(axis=0)
        posts.append((float(centre[0]), float(centre[1]), carried))
    posts.sort(key=lambda post: (post[0], post[1]))
    return posts


# --------------------------------------------------------------------------
# The mesh
# --------------------------------------------------------------------------


class _Builder:
    """Accumulates flat convex polygons, each with its own colour and normal.

    `signs._Builder`'s shape and for its reasons: a head is four colours — body
    and three lens aspects — and the whole layer is one draw call, so the colour
    has to travel on the vertex and `signs.gdshader` takes it straight to
    `ALBEDO`. The normal is per polygon because a head faces sideways and every
    head faces a different sideways.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._colours: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def polygon(self, points: np.ndarray, normal: np.ndarray, colour: tuple[int, int, int]) -> None:
        """One convex polygon in world space, already wound to face `normal`."""
        span = len(points)
        if span < 3:
            return
        base = self._count
        fan = np.arange(1, span - 1)
        self._triangles.append(
            np.column_stack([np.zeros(len(fan), dtype=np.int64), fan, fan + 1]) + base
        )
        self._positions.append(points)
        self._normals.append(np.tile(normal.astype(np.float32), (span, 1)))
        self._colours.append(np.tile(np.array([*colour, 255], dtype=np.uint8), (span, 1)))
        self._count += span

    def build(self, name: str) -> MeshData | None:
        if not self._triangles:
            return None
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.vstack(self._normals),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            colours=np.vstack(self._colours),
            material=SIGNALS_MATERIAL,
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        return select_triangles(mesh, twice_area > _MIN_TWICE_AREA_M2)


def _draw_post(
    builder: _Builder, spec: Signals, x: float, z: float, base_y: float, top_y: float
) -> None:
    """The post, as a closed prism with a cap.

    No collider, and no bottom cap: the post meets the footway and nothing sees
    under it.

    🔴 **`base_y` is the deck, and dropping it is a defect that shipped.** The
    first build copied `signs._draw_pole` **without this parameter** and rooted
    every post at world y=0, so each one ran from sea level up through the
    carriageway — 3 to 12 m too long, `signals.json`'s AABB reading min-y 0.0
    against the signs' 3.18. Nothing saw it: `facing_away` was 0, both
    partitions closed, `verify_signals` was green, and the extra length points
    *downward* where opaque asphalt hides it from any camera above the road.
    This stage's own failure class, landing on the stage itself.

    ⚠️ **The ring is REVERSED, and that is the whole correctness of this
    function** — `signs._draw_pole`'s recorded defect, inherited rather than
    rediscovered. `_disc` winds counter-clockwise in `(u, v)`, which is what a
    *plate* wants once `_plate_frame` maps it; here `u` and `v` become world `X`
    and `Z`, and a ring counter-clockwise in `(X, Z)` has its side quads wound
    inward and its cap wound at the ground. The signs' first build shipped
    exactly that: 3,200 triangles, every pole in the region, facing away with
    everything else correct — caught by `facing_away` rather than by looking.
    """
    ring = disc(spec.post_radius_m, spec.post_sides)[::-1]
    body = spec.colours[SIGNAL_BODY_COLOUR]
    centre = np.array([x, 0.0, z])
    # `base_y` and `top_y` are absolute, so the ring contributes only x and z.
    for index in range(spec.post_sides):
        u0 = ring[index]
        u1 = ring[(index + 1) % spec.post_sides]
        a = centre + np.array([u0[0], base_y, u0[1]])
        b = centre + np.array([u1[0], base_y, u1[1]])
        c = centre + np.array([u1[0], top_y, u1[1]])
        d = centre + np.array([u0[0], top_y, u0[1]])
        outward = np.array([u0[0] + u1[0], 0.0, u0[1] + u1[1]])
        length = float(np.linalg.norm(outward))
        if length <= 0.0:
            continue
        builder.polygon(np.vstack([a, b, c, d]), outward / length, body)
    cap = np.vstack([centre + np.array([u[0], top_y, u[1]]) for u in ring])
    builder.polygon(cap, np.array([0.0, 1.0, 0.0]), body)


def _draw_head(builder: _Builder, spec: Signals, front: np.ndarray, facing_deg: float) -> None:
    """One signal head: a closed box, with its aspects on the front face.

    ⚠️ **`front` is the centre of the FRONT FACE, not the centre of the box** —
    the body runs back from it along `-normal`. It was called `centre` in the
    first build and the caller placed it as if it were one, which put 0.24 m of
    a 0.30 m head on the far side of its own post. The name carries the
    convention now, because the comment did not.

    ⚠️ **All six faces, including the bottom.** A head hangs at eye level and
    above — `mount_height_m` is 2.40 — so the underside is the face a driver
    stopped at the line is looking straight at. The post's bottom cap is omitted
    because it meets the footway; this one does not.

    The frame comes from `signs._plate_frame`, which already fixes the winding:
    `u x up == n`, so a polygon wound counter-clockwise in `(u, v)` comes out
    with its normal along `+n`.
    """
    normal, right = plate_frame(facing_deg)
    up = np.array([0.0, 1.0, 0.0])
    body = spec.colours[SIGNAL_BODY_COLOUR]

    half_w = 0.5 * spec.head_width_m
    half_h = 0.5 * spec.head_height_m
    depth = spec.head_depth_m

    # The eight corners, front face first. `front` is the face the traffic sees.
    back = front - depth * normal
    corners = {
        "front": [
            front - half_w * right - half_h * up,
            front + half_w * right - half_h * up,
            front + half_w * right + half_h * up,
            front - half_w * right + half_h * up,
        ],
        "back": [
            back - half_w * right - half_h * up,
            back - half_w * right + half_h * up,
            back + half_w * right + half_h * up,
            back + half_w * right - half_h * up,
        ],
    }
    builder.polygon(np.vstack(corners["front"]), normal, body)
    builder.polygon(np.vstack(corners["back"]), -normal, body)

    fl, fr, fru, flu = corners["front"]
    bl, blu, bru, br = corners["back"]
    # Each side wound so its own outward normal is the one it is given.
    builder.polygon(np.vstack([fr, br, bru, fru]), right, body)
    builder.polygon(np.vstack([fl, flu, blu, bl]), -right, body)
    builder.polygon(np.vstack([flu, fru, bru, blu]), up, body)
    builder.polygon(np.vstack([fl, bl, br, fr]), -up, body)

    # The aspects, laid down the head's own height, top to bottom. Lifted clear
    # of the front face along the head normal: coplanar faces z-fight, which is
    # what `lens_lift_m` is for and what `arrows.lift_m` is for on the ground.
    lens_face = front + spec.lens_lift_m * normal
    radius = 0.5 * spec.lens_diameter_m
    pitch = spec.head_height_m / spec.lens_count
    for index, name in enumerate(spec.lens_colours):
        offset = half_h - pitch * (index + 0.5)
        ring = disc(radius, spec.lens_segments)
        lens = np.vstack(
            [lens_face + point[0] * right + (offset + point[1]) * up for point in ring]
        )
        builder.polygon(lens, normal, spec.colours[name])


# --------------------------------------------------------------------------
# The region
# --------------------------------------------------------------------------


@dataclass
class _Placed:
    """One post, registered onto the drawn kerb and ready to draw."""

    x: float
    z: float
    y: float
    facing_deg: float
    heads: list[Signal]


def _merge_placements(
    placements: list[_Placed], merge_m: float, report: SignalReport
) -> list[_Placed]:
    """Posts that registration pushed onto the same point, folded into one.

    ⚠️ **A second merge, over a different population from `_assemble`'s.** That
    one runs over *surveyed* positions and is the publisher's coincidence; this
    one runs over *registered* positions and is this stage's own doing — every
    post on the same edge, side and `t` is pushed to the same offset, so two
    posts legitimately a metre apart where they were surveyed can land on one
    point. `signs.py` records the same two-phase shape and its reason: drawing
    first would put two posts and two stacks in one place, each starting again
    at `mount_height_m`.
    """
    kept: list[_Placed] = []
    for placement in placements:
        for other in kept:
            if math.hypot(other.x - placement.x, other.z - placement.z) <= merge_m:
                # 🔴 **The survivor's facing wins and the absorbed one is
                # discarded, so the discard is measured.** Two posts that
                # registration pushed onto one point were derived from different
                # host edges, and their facings can disagree: on this region
                # eleven of the twelve merges agree to 0.0 degrees and **one is
                # 94.9 degrees apart**, which is a drawn head addressing traffic
                # at right angles to the traffic its absorbed aspect was derived
                # for. It renders as a perfectly good signal, and until this
                # counter existed nothing said so — `posts_merged_after_shift`
                # counts the fold but cannot see what the fold cost.
                report.merged_facing_deg.append(
                    abs((other.facing_deg - placement.facing_deg + 180.0) % 360.0 - 180.0)
                )
                other.heads.extend(placement.heads)
                report.posts_merged_after_shift += 1
                break
        else:
            kept.append(placement)
    return kept


def build_region(
    city: Config,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> SignalReport:
    """Read the region's published signal heads and write its `signals.glb`."""
    spec = city.signals
    report = SignalReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the shape `tramway`, `arrows`, `boxjunctions`,
        # `railings` and `signs` all take: a city whose estate publishes no
        # signal layer ships none rather than putting a signal at every junction
        # node it found.
        log.info("city '%s' declares no signals block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    signals = read_signals(city, spec, region_id, transform, report, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    # Level 0 only, the restriction `kerbside.py`, `tramway.py`, `arrows.py` and
    # `signs.py` all make: for 7% of the kerbside samples the nearest edge of
    # *any* level was elevated, and the street the feature is actually on was a
    # median 4 m away.
    edges = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    segments = Segments.of(edges)

    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --region {region_id}",
    )
    drawn = ribbons(graph, surface)

    posts = _assemble(signals, spec.assembly_merge_m)
    sizes: dict[str, int] = defaultdict(int)
    for _, _, carried in posts:
        sizes[str(len(carried))] += 1
    report.assembly_size = dict(sorted(sizes.items(), key=lambda item: int(item[0])))

    builder = _Builder()
    placements: list[_Placed] = []
    for post_x, post_z, carried in posts:
        snap = segments.nearest(post_x, post_z)
        for signal in carried:
            if math.isfinite(signal.axis_deg):
                # ⚠️ **Recorded over every candidate, before any refusal.** A
                # distribution taken after its own filter is confined to that
                # filter and can say nothing — `Q58`'s `drawn_gauge_m` trap.
                # Nothing reads this; its flatness is the finding.
                report.axis_residual_deg.append(
                    axis_residual_deg(signal.axis_deg, snap.heading_deg)
                )
        if snap.distance_m > spec.max_offset_m:
            # No level-0 street near enough to say which traffic this head
            # addresses. Refused rather than guessed at: without a host edge
            # there is no kerb side, and without a kerb side there is no facing.
            report.too_far += len(carried)
            continue

        report.host_distance_m.append(snap.distance_m)
        # 🔴 Report-only, and the one instrument that can see the junction-mouth
        # join go weak. See `SignalReport.host_ambiguous`.
        if segments.rivals_within(post_x, post_z, spec.host_ambiguity_m, snap.edge):
            report.host_ambiguous += 1

        ribbon = drawn.get(snap.edge)
        if ribbon is None:
            # No drawn carriageway on the host edge, so no kerb to stand on.
            report.no_ribbon += len(carried)
            continue

        placed = _register(spec, snap, ribbon, report)
        if placed is None:
            report.over_shift += len(carried)
            report.posts_over_shift += 1
            continue

        point, side = placed
        settled = segments.nearest(float(point[0]), float(point[1]))
        settled_ribbon = drawn.get(settled.edge)
        if settled_ribbon is not None and abs(settled.offset_m) < settled_ribbon.half_width_at(
            settled.t
        ):
            # ⚠️ **Registered onto its host's kerb and still in the road**, because
            # the post landed inside a *different* edge's ribbon — junction mouths
            # and dual carriageways, where several 1.6x ribbons overlap and the
            # drawn city has no footway at all. `Q19`'s territory rather than this
            # stage's, and **refused rather than pushed again**: `signs.py`
            # measured iterating the push and it plateaus while taking the worst
            # shift to 16.77 m, which is a post on the wrong street.
            report.in_carriageway += len(carried)
            report.posts_in_carriageway += 1
            continue

        placements.append(
            _Placed(
                x=float(point[0]),
                z=float(point[1]),
                y=snap.y,
                # ⚠️ **`side`, not `snap.offset_m`.** The two disagree at `-0.0`,
                # which `Segments.nearest` really returns for a post on the
                # centreline — `-0.0 >= 0.0` is true and `-0.0 > 0.0` is false —
                # so the post would be placed on the nearside and turned to face
                # the offside. A perfectly drawn signal facing the wrong way,
                # which is this module's whole failure class.
                facing_deg=facing_from_side(snap.heading_deg, side, ribbon.one_way),
                heads=list(carried),
            )
        )

    for post in _merge_placements(placements, spec.assembly_merge_m, report):
        # 🔴 **ONE head per assembly, not one per feature — and the render is
        # what settled it.** The first build stacked the coincident features up
        # the post, on `signs.py`'s plate-stack model, and drew the region's
        # five-feature assemblies as **8.53 m** masts carrying five signal heads
        # above one another. That is a structure no source states: `signs.py`
        # stacks because TD publishes a main sign *and* its supplementary plate
        # as separate signs on one `GG_NAME`, and this layer publishes no such
        # relation — what it publishes is several coincident points, which are
        # the parts of one installation and not a pile of heads.
        #
        # Drawing one head asserts only what the data supports: **there is a
        # signal here, and it addresses this traffic**. Which of `P01`, `P21`,
        # `P26` and `S01` is the primary aspect is exactly the question nothing
        # published can answer (see the module docstring), so a stack ordered by
        # code would be `Q54`'s invention on the bundle's weakest field — and
        # unlike most inventions here, this one is visible from the road.
        #
        # ⚠️ **`assembly_size` is what keeps that honest.** It publishes how many
        # features each drawn head stands for, so the collapse is a number a
        # reader can see rather than a silent discard.
        # 🔴 **The head's BACK must clear the post, not its front** — and the
        # first build got this wrong by lifting `signs._draw_plate`'s
        # `+ pole_radius_m * normal`. That offset is right for a *plate*, which
        # is one quad thick and only has to stop the post standing through its
        # face. A box 0.30 m deep needs its own depth in the sum: at
        # `post_radius_m` alone the body ran -0.240 to +0.072 m along the facing
        # normal against a post occupying -0.06 to +0.06, so the post was
        # swallowed whole and four fifths of the head sat behind it, away from
        # the traffic it addresses. Rendered perfectly, and `facing_away` was 0.
        frame_normal, _ = plate_frame(post.facing_deg)
        front = (
            np.array([post.x, post.y + spec.mount_height_m + 0.5 * spec.head_height_m, post.z])
            + (spec.post_radius_m + spec.head_depth_m) * frame_normal
        )
        _draw_head(builder, spec, front, post.facing_deg)
        _draw_post(
            builder,
            spec,
            post.x,
            post.z,
            post.y,
            post.y + spec.mount_height_m + spec.head_height_m + spec.post_headroom_m,
        )
        report.posts_drawn += 1
        # ⚠️ **`drawn` counts FEATURES, not heads**, so the partition over
        # `candidates` still closes — every admitted feature is either accounted
        # for here or sits in one of the four refusals. `posts_drawn` is the
        # number of heads, and the two differ by exactly the collapse above.
        for signal in post.heads:
            report.drawn += 1
            report.drawn_by_code[signal.code] = report.drawn_by_code.get(signal.code, 0) + 1

    report.drawn_by_code = dict(sorted(report.drawn_by_code.items()))
    report.refused_by_code = dict(sorted(report.refused_by_code.items()))

    mesh = builder.build(SIGNALS_MESH_NAME)
    if mesh is not None:
        report.facing_away = facing_away(mesh)
        report.triangles = mesh.triangle_count
        report.vertices = len(mesh.positions)
        low, high = mesh.aabb()
        report.aabb = [list(low), list(high)]
        report.bytes = write_glb(out_dir / SIGNALS_NAME, [mesh])

    _write_manifest(out_dir, city, region_id, report)
    return report


def _register(
    spec: Signals, snap: Snap, ribbon: Ribbon, report: SignalReport
) -> tuple[np.ndarray, float] | None:
    """Push a post out to the kerb the ribbon actually drew, or refuse the move.

    ⚠️ **`Q60`'s move at a third layer**, after the railings and the signs, and
    for its reason: **72.7%** of this region's signal points are surveyed inside
    the 1.6x ribbon, a median 1.48 m past the drawn kerb, so drawn where
    published nearly three quarters of the city's signals stand in the road.

    The post keeps its along-edge position and its side and moves only across.
    """
    half_width_m = ribbon.half_width_at(snap.t)
    # A post exactly on the centreline has no side to keep; the nearside is the
    # one a left-driving city's traffic passes closest to.
    side = 1.0 if snap.offset_m >= 0.0 else -1.0
    target_m = side * (half_width_m + spec.outset_m)
    report.inside_ribbon_m.append(max(0.0, half_width_m - abs(snap.offset_m)))
    shift_m = abs(target_m - snap.offset_m)
    # Recorded **before** the refusal, so the distribution can read outside its
    # own bar (`Q58`); `posts_over_shift` and `posts_in_carriageway` are what let
    # a reader decompose `n`.
    report.shift_m.append(shift_m)
    if shift_m > spec.max_shift_m:
        return None

    # ⚠️ **The foot comes off the polyline, never from
    # `point - offset_m * nearside`.** `Snap.offset_m` is `±distance_m` to the
    # *clamped* projection, so a post past an edge's end has an along-edge
    # component in that vector and the subtraction lands off the centreline.
    # `signs.py` measured it: a post 5 m beyond an edge's end and dead on its
    # axis reconstructs to 5 m off the road, and the 10.6 m move it then makes is
    # published as 0.6 m — under `max_shift_m`, invisible to every counter.
    return ribbon.foot_at(snap.t) + target_m * nearside(snap.heading_deg), side


def _write_manifest(out_dir: Path, city: Config, region_id: str, report: SignalReport) -> int:
    document = {
        "schema_version": SIGNALS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what `CITY_SCHEMA`
        # 11 was bumped over.
        "asset": SIGNALS_NAME if report.triangles else None,
        # The read, as four disjoint parts of `features`.
        "features": report.features,
        # 🔴 **The gate's refusals, and the number is a decision** — see
        # `refused_by_code` for which codes, and the module docstring for why the
        # gate is a rule about spelling that nothing published grades.
        "not_whitelisted": report.not_whitelisted,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "candidates": report.candidates,
        # The host and the registration, as disjoint parts of `candidates`.
        "drawn": report.drawn,
        "too_far": report.too_far,
        "no_ribbon": report.no_ribbon,
        "over_shift": report.over_shift,
        # 🔴 Refused because registration could not get them out of the road —
        # a finding about `Q19`'s widening, not about this stage.
        "in_carriageway": report.in_carriageway,
        "posts_drawn": report.posts_drawn,
        "posts_over_shift": report.posts_over_shift,
        "posts_in_carriageway": report.posts_in_carriageway,
        "posts_merged_after_shift": report.posts_merged_after_shift,
        # 🔴 What each fold cost in facing. A non-zero tail is a head re-aimed by
        # the merge — see `_merge_placements`.
        "merged_facing_deg": report.measured(report.merged_facing_deg),
        # 🔴 **The gate's effect over the whole vocabulary, both halves.** The
        # only thing that makes a whitelist read off code strings reviewable.
        "drawn_by_code": report.drawn_by_code,
        "refused_by_code": report.refused_by_code,
        # 🔴 **The derived grouping this layer has instead of a `GG_NAME`.**
        # Features per **surveyed assembly**, as a histogram — ⚠️ counted before
        # `_merge_placements` folds any of them, so it sums to `candidates` and
        # its bin count exceeds `posts_drawn`. Nothing else can see the
        # clustering go wrong: a radius that swallowed a neighbouring post
        # renders perfectly.
        "assembly_size": report.assembly_size,
        # 🔴 **Published, unread, and its flatness is the finding.** Recorded
        # over every candidate rather than the drawn ones (`Q58`).
        "axis_residual_deg": report.measured(report.axis_residual_deg),
        "host_distance_m": report.measured(report.host_distance_m),
        # 🔴 **Report-only, never a bar** — the one instrument that can see the
        # junction-mouth join go weak, and it has no prior number to be read
        # against. See `SignalReport.host_ambiguous`.
        "host_ambiguous": report.host_ambiguous,
        # ⚠️ **`n` exceeding `posts_drawn` is the proof these can read outside
        # their own bar** (`Q58`).
        "shift_m": report.measured(report.shift_m),
        "inside_ribbon_m": report.measured(report.inside_ribbon_m),
        # ⚠️ **Must be 0.** `signs.gdshader` is `cull_back`, so winding decides
        # visibility and the normal attribute does not. The tramway shipped 5,111
        # of 5,112 triangles facing the ground with everything else correct.
        "facing_away": report.facing_away,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
    }
    return write_document(out_dir / SIGNALS_MANIFEST_NAME, document)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    # ⚠️ **`drawn` is features and `posts_drawn` is heads**, and the line says so
    # rather than calling both a count of signals — one head stands for every
    # coincident feature at its assembly, which is the collapse `build_region`
    # argues for and `assembly_size` publishes.
    log.info(
        "signals: %d features -> %d heads standing for %d published aspects "
        "(%d not heads, %d off-grade, %d in carriageway), "
        "%d ambiguous host, %d triangles, %d facing away",
        report.features,
        report.posts_drawn,
        report.drawn,
        report.not_whitelisted,
        report.on_structure,
        report.in_carriageway,
        report.host_ambiguous,
        report.triangles,
        report.facing_away,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
