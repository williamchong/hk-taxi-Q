"""How far the drawn carriageway sits from the edge the city publishes (`Q57`, `Q19`).

`Q19` spent months recording that the carriageway width "no source publishes",
and `Q57` found it published twice over in files already on disk. What `Q57`
did not do is read them repeatably: its probe cast a perpendicular from each
centreline station to the first margin each side, and its own record says twice
that the number is not shippable — *"the perpendicular escapes through junction
mouths and crosses both halves of a dual carriageway, so it over-reads at the
top of the distribution. Anyone building on this owes a real cross-section, not
this number."* This is that cross-section.

**The headline is near-side overhang, not measured width**, and that is the
whole answer to the objection above:

    overhang_m = drawn half-width - distance to the nearest published edge

The far ray is exactly what a junction mouth and a dual carriageway corrupt —
it escapes across an open mouth, or crosses a median and lands on the far
kerb of the other carriageway. The near ray is short, and it lands on the kerb
the ribbon is actually about to cross. Dropping the far side removes the
confound rather than documenting it again, and it *raises* coverage, because a
station needs one hit instead of two. Both distances are still reported, so a
width is derivable; only the headline declines to depend on the weak half.

**And since `Q95` the far ray is read too, because TD published the bound it
was missing.** The Transport Planning & Design Manual Vol 2 Ch 3 says the widest
urban carriageway in Hong Kong is 13.5 m, 15.8 m on a tight curve and ~16.5 m
with a parking strip — so a two-sided ray above that has crossed a median, a
tram reserve or a junction mouth, which is a *citable* refusal rather than the
suspicion that kept the far side unread. The bounds live in the city file under
hard rule 3; the second city has its own manual.

🔴 **The ceiling is a plausibility bound and NOT a confound filter, and the
difference is most of the network.** 621 of the region's 737 level-0 edges are
one-way, and Hong Kong runs those as opposed pairs — so the centreline sits
inside one carriageway and the ray legitimately spans both. Two carriageways
summing to 13 m are a legal four-lane single carriageway and pass 16.5 m
cleanly. What separates them is `off_centre`, because the near ray is then short
and the far one long. ⚠️ **So the one-way number is reported as a kerb-to-kerb
span and never as a carriageway width**; the two coincide only on the 34
two-way edges.

⚠️ **The span is cap-sensitive where the overhang headline is not, so quote its
cap.** Measured over `--max-ray-m` 10 / 15 / 20 / 25: coverage 54.7 / 70.4 /
78.4 / 81.8%, and the non-junction p50 drifts 7.40 / 8.18 / 8.93 / 9.15 m.
✅ **The measurement saturates at the 15 m default** — kept spans peak there at
8,204 and *fall* to 8,162 by 25 m, published edges 343 → 336, because above the
default the extra stations are refusals. That is why there is one cap and not
two: a second flag would advertise a sensitivity the kept population does not
have, and casting a second pair of rays for the width would re-open the very
failure `_Index.cast_both` exists to close.

**Two publishers, and the second one is not belt-and-braces.** `Q57` traced four
wrong "no source publishes that" claims to a single mechanism: a fact measured
properly against one dataset, then generalised to the estate. An instrument that
read one margin layer and called the result "the width" would be that same step
in a new place. So `carriageway_survey.edges` is a list, the report says which
publisher answered each station, and where they disagree the disagreement is the
finding rather than an error in either.

| | Traffic Aids Drawings | iB1000 |
|---|---|---|
| Draws | TD's painted `RM1108`/`RM1109` edge | LandsD's surveyed `RM` margin |
| Truth | cartographic — what is painted | topographic — where the edge is |
| Grade | a relative-level code, domain undecoded | the `RMU` complement only |
| In region | 745 segments | 29,018 segments |

⚠️ **This grades rather than checks**, the rule CLAUDE.md already records for
`kerbside_source_audit.py`. It exits 0 whatever it finds. A widening gap is a
finding to go and look at, never a bar to retune against — and there is a
specific reason not to gate this one yet, recorded under "the open question".

⚠️ **It is not a fifth bundle grader.** `deck_error`, `overhang`,
`ground_clearance` and `carriageway_occupancy` take their truth from the shipped
bundle, so a pipeline that is confidently wrong is agreed with. This takes its
truth from outside, as `kerbside_source_audit.py` does — the difference from
that one is that it shares no code with what it grades, where the audit
deliberately runs the pipeline's own join. In exchange it inherits the
publishers' registration error and their 2D projection, which the four do not.

**The open question this was built to settle, and did not.** `Q19` finds that 12
of its 14 `BUILDING` failures are edges under 20 m, and `Q57` concludes the
building half fails *because* the width is invented. Measured, short edges are
the **least** overhung part of the network, not the most — and the reason turns
out to be that this method barely reaches them. Of the four `BUILDING` edges
`Q19` names, two return **no station at all** and two return **one**, whose
nearest published kerb is 8-10 m away on a 7-11 m street: a ray leaving through
the junction mouth and finding the far side of the crossing.

⚠️ **So read the coverage column before any figure beside it.** The network
answer is solid — 92.3% of level-0 stations, and the ribbon crosses the
published kerb at three quarters of them. The `Q19` answer is *absence of
evidence*, and the report is built to show that rather than to average it away:
`--junction-m` prints the same population junctions-in and junctions-out, and
below twice that radius an edge has no non-junction station at all, so the short
band empties outright and the tool says so in words. It is not a knob to turn
until the answer agrees with the record.

What this implies for the sequel is in `Q19`: a fix for the building half has to
work on stubs an 8 m ray cannot cross, which points at counting lanes *between*
two published edges (`Q57` follow-on 1) rather than casting to the nearest one.

⚠️ **What the width half does NOT reproduce, and that is a finding rather than a
bar to tune.** `Q94` published three roads measured by a scratch script whose
commit touched only the docs. Walked here at its stated 4 m stations and 12 m
junction exclusion, the **p10 reproduces to 0.03 m on all three** — so the rays,
the walk and the exclusion are the same instrument — while `HENNESSY ROAD`
reproduces on every percentile (7.81 / 11.55 / 23.18 against 7.80 / 11.54 /
23.17) only at a ray cap of **25 m or more**, which its prose never states.
`STEWART ROAD` and `CANAL ROAD EAST` reproduce at no cap, and `STEWART ROAD` is
cap-*insensitive* — 22 stations reading 16.67 m from 15 m to 40 m. So the
record's stated method does not determine the record's numbers, which is the
argument for this code existing rather than a reason to make it agree.

Run:  .venv/bin/python tools/carriageway_margin.py --region wan_chai
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from overhang import half_width_at, half_widths, left_of, walk_width  # noqa: E402
from pipeline import gdb  # noqa: E402
from pipeline.config import (  # noqa: E402
    BOTH,
    CARRIAGEWAY_AREA,
    FORWARD,
    CarriagewayEdge,
    Config,
    WidthBounds,
    load_config,
)
from pipeline.crs import GameTransform  # noqa: E402
from pipeline.export import read_manifest  # noqa: E402
from pipeline.fetch import source_reads  # noqa: E402
from pipeline.polyline import plan_lengths  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402

log = logging.getLogger("carriageway_margin")

# Cell size of the segment index, in game metres. Only a lookup accelerator —
# it changes runtime and nothing reported, unlike the resolution constants in
# `clearance.py` that `Q51` found were deciding a published count.
_INDEX_CELL_M = 20.0

# Per-edge rows in the listing. `Q19` was corrected twice for reasoning about a
# population it could only see the top of, so this caps the *listing* only: every
# distribution above it is the whole population.
_WORST = 15

# Edge-length bands for the short-stub question. The middle bound is the graph's
# own median edge length as `Q19` publishes it, so the bands are the record's
# own split rather than a new one invented here.
_BANDS = ((0.0, 20.0, "< 20 m"), (20.0, 47.3, "20-47.3 m"), (47.3, float("inf"), ">= 47.3 m"))

# How far off the middle of its own span a centreline may sit, in quarters.
# `off_centre` is a ratio bounded at 1.0 by construction — a centreline on
# one edge of its own span — so the last band closes just above it rather
# than at `inf`, and a NaN from a zero-width span falls out of every band.
_OFF_CENTRE_BANDS = ((0.0, 0.10), (0.10, 0.25), (0.25, 0.50), (0.50, 1.01))

# Did the two-sided ray reach past the carriageway its centreline is drawn in?
# `UNRESOLVED` is a real answer and not a missing one — see `EdgeWidth.crossing`.
UNCROSSED = "uncrossed"
UNRESOLVED = "unresolved"
CROSSED = "crossed"
_CROSSINGS = (UNCROSSED, UNRESOLVED, CROSSED)

# Which route licensed a width. ⚠️ The two one-way bases measure different
# things — `BASIS_DECOMPOSED` publishes half a span and `BASIS_UNCROSSED`
# publishes the whole of one — so the basis is carried beside every width this
# tool writes rather than pooled into a single column.
BASIS_TWO_WAY = "two_way_span"
BASIS_UNCROSSED = "one_way_uncrossed"
BASIS_DECOMPOSED = "decomposed"
_BASES = (BASIS_TWO_WAY, BASIS_UNCROSSED, BASIS_DECOMPOSED)


@dataclass
class Station:
    """One measured cross-section of one edge."""

    edge: int
    # Distance to the nearest published edge on either side. The measurement;
    # `overhang_m` is it subtracted from the drawn half-width, kept beside it so
    # a reader can check one against the other without the ribbon in hand.
    nearest_m: float
    # Metres the drawn ribbon reaches past that edge. Negative means the ribbon
    # stops short of it, which is the normal, healthy case.
    overhang_m: float
    # Which `carriageway_survey.edges` entry answered.
    source: str
    # Whether the station sits within `--junction-m` of a graph node.
    near_junction: bool

    # ── the two-sided half (`Q95`), NaN and "" where no publisher spanned ──
    #
    # ⚠️ **`width_source` is not `source`.** The publisher that wins the near
    # side and the publisher that spans the road are different sets — the
    # drawings are the semantically better edge and are far too sparse to reach
    # across a street — so crediting a width to `source` would attribute most of
    # them to the wrong publisher.
    width_source: str = ""
    # The two rays of the *spanning* publisher, kept on `left_of`'s own sign
    # rather than sorted.
    #
    # ⚠️ **Stored raw and sorted on read, rather than sorted on write.** A sum
    # needs no side convention, which is why these were `(near, far)` with the
    # sign discarded. Deriving the ordering instead keeps `width_m` and
    # `off_centre` byte-identical while leaving the pair recoverable, which is
    # one less thing a later reader can get wrong — the same argument
    # `Report.spans` makes for the population. ⚠️ The decomposition does **not**
    # use the side: `_partner_at` casts both ways, because a station whose two
    # rays are near-equal has no far side to prefer and picking one is picking
    # noise.
    width_forward_m: float = float("nan")
    width_backward_m: float = float("nan")

    # ── the partner candidate (`Q95` follow-on), measured and NOT judged ────
    #
    # 🔴 **The angle is recorded and the bound is applied where the table is
    # printed**, which is the same discipline `survey` follows for `width_bounds`
    # and for the same reason: a tolerance applied here would confine the
    # population to itself, so no sweep of it could ever report a refusal, and
    # mutation-checking it would need a re-survey per row. `-1` and NaN mean neither
    # ray reached a graph edge, or the station is one `_candidate` never reads.
    partner_edge: int = -1
    # Degrees off anti-parallel — 0.0 is a perfectly opposed centreline, 90.0 a
    # perpendicular one. Never signed: which way it leans says nothing here.
    partner_offset_deg: float = float("nan")

    @property
    def width_near_m(self) -> float:
        """The shorter of the spanning publisher's two rays.

        ⚠️ **Both rays are set together or neither is** — `width_published`
        chooses a publisher only when it answers both sides — which is what makes
        `min`/`max` safe here. Python's `min` is not NaN-symmetric
        (`min(nan, 5.0)` is NaN, `min(5.0, nan)` is 5.0), so a hand-built station
        with one ray would read its own near ray as its far one and double it
        into a carriageway.
        """
        return min(self.width_forward_m, self.width_backward_m)

    @property
    def width_far_m(self) -> float:
        """The longer — the one a junction mouth and a dual carriageway corrupt."""
        return max(self.width_forward_m, self.width_backward_m)

    @property
    def width_m(self) -> float:
        return self.width_forward_m + self.width_backward_m

    @property
    def off_centre(self) -> float:
        """How far off the middle of its own span the centreline sits, 0 to 1.

        🔴 **The confounder detector, and the ceiling is not one.** 621 of the
        region's 737 level-0 edges are one-way, and Hong Kong runs those as
        opposed pairs — so the centreline sits *inside* one carriageway and the
        two-sided ray legitimately spans both plus whatever lies between. Two
        carriageways summing to 13 m are a legal four-lane single carriageway
        and pass `max_m` cleanly; what separates them is that the near ray is
        short and the far one long, which is this number.
        """
        width = self.width_m
        return abs(self.width_far_m - self.width_near_m) / width if width > 0 else float("nan")


@dataclass
class Report:
    stations: list[Station] = field(default_factory=list)
    # Stations walked but unmeasurable — no published edge either side within
    # the ray cap. Counted rather than dropped: coverage that silently falls is
    # indistinguishable from a city whose ribbon suddenly fits.
    unmeasured: int = 0
    # Level-0 edges considered, and those that got at least one reading.
    edges_walked: int = 0
    edges_measured: set[int] = field(default_factory=set)
    # Segments read per configured source, after code and grade filtering.
    segments: dict[str, int] = field(default_factory=dict)
    # Stations where more than one source answered, and the absolute spread
    # between their nearest-edge distances. This is the cross-check.
    agreement: list[float] = field(default_factory=list)
    # Per level-0 edge, its plan length and street name — report data rather
    # than extra return values, so `render` takes one argument.
    lengths: dict[int, float] = field(default_factory=dict)
    names: dict[int, str] = field(default_factory=dict)

    # ── the two-sided half (`Q95`) ────────────────────────────────────────
    #
    # Stations more than one publisher spanned, and by how much they differ.
    # ⚠️ Reported separately from `agreement` rather than folded into it: the
    # near-side cross-check is two orders of magnitude larger, and quoting one
    # for the other would be `Q57`'s own generalisation in a new place.
    width_agreement: list[float] = field(default_factory=list)
    # `roadgraph.json`'s own `direction`, for the split `off_centre` explains.
    directions: dict[int, str] = field(default_factory=dict)
    lanes: dict[int, int] = field(default_factory=dict)
    # ⚠️ **Which of the two a given count is** (`Q94`). Once part of the region
    # carries a count the pipeline bracketed off its own survey, "the graph's
    # lanes" is two populations and `LaneVerdict` has to say which it is
    # reporting. Defaulted rather than required, so this tool still reads a
    # graph built before schema 6.
    lanes_source: dict[int, str] = field(default_factory=dict)
    widths_authored: dict[int, float] = field(default_factory=dict)

    @property
    def spans(self) -> list[Station]:
        """Every station a publisher reached across, refusals included.

        🔴 **Derived rather than accumulated, and that is what makes the
        `drawn_gauge_m` trap unreachable here.** The rule the trap breaks is
        that a distribution must be recorded over the refusals as well as the
        keeps; four other stages have shipped it recorded below their own guard,
        confined to the bar by construction and reporting a clean sweep whatever
        the region did. A second list appended beside the counters can always
        drift to the wrong side of the `if`. One unfiltered population that both
        `n` and the keeps are computed from cannot: the bounds are applied where
        the table is printed, and never where the measurement is stored.
        """
        return [station for station in self.stations if station.width_source]

    @property
    def stations_walked(self) -> int:
        """Every station with a usable normal, answered or not."""
        return self.measured + self.unmeasured

    @property
    def width_no_span(self) -> int:
        """Stations no publisher reached across — zero rays or one.

        ⚠️ A station with one ray has no width, so it is reported beside the
        distribution rather than inside it with a placeholder. Recording a zero
        would be `touchdown_error.py`'s `ends_no_target`, which review found
        holding an identity true by never reaching the list it was counted in.
        """
        return self.stations_walked - len(self.spans)

    @property
    def width_coverage(self) -> float:
        walked = self.stations_walked
        return len(self.spans) / walked if walked else 0.0

    @property
    def measured(self) -> int:
        return len(self.stations)

    @property
    def coverage(self) -> float:
        walked = self.stations_walked
        return self.measured / walked if walked else 0.0


def _segments(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A polyline's segments as start and end arrays, dropping zero-length ones.

    Zero-length segments are not hypothetical here: `Q57` records iB1000's
    transport lines arriving with repeated vertices, and a degenerate segment
    makes the ray/segment determinant vanish rather than miss.
    """
    if len(points) < 2:
        return np.empty((0, 2)), np.empty((0, 2))
    starts, ends = points[:-1], points[1:]
    keep = np.hypot(ends[:, 0] - starts[:, 0], ends[:, 1] - starts[:, 1]) > 1e-9
    return starts[keep], ends[keep]


class _Index:
    """Published-edge segments in game plan metres, bucketed for ray casting.

    A segment is filed under every cell its **bounding box** covers, and that is
    what makes the query exact without a neighbourhood halo: if a segment
    crosses the ray inside a cell then part of it lies in that cell, so its box
    covers that cell, so it is already in that bucket. Cell size is a lookup
    accelerator only — unlike the constants in `clearance.py`, which `Q51` found
    were deciding a published count, nothing reported here moves with it.

    ⚠️ **`tramway.py`'s `_Rails` is this class's twin** — same cell size, same
    bucket build, same solve, same owner array and self-exclusion — and it
    already cites this file for the arithmetic. They are not shared because one
    lives in `tools/` and one in `etl/pipeline/`; change either and read the
    other, or promote both.
    """

    def __init__(
        self, starts: np.ndarray, ends: np.ndarray, owners: np.ndarray | None = None
    ) -> None:
        self.starts = starts
        self.ends = ends
        # Which object each segment came from, for an index built over something
        # whose identity the caller needs back. The published-edge indexes do
        # not — a kerb is a distance and nothing else — so this stays optional
        # rather than making every caller invent an id.
        self.owners = np.full(len(starts), -1, dtype=np.intp) if owners is None else owners
        buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        low = np.floor_divide(np.minimum(starts, ends), _INDEX_CELL_M).astype(np.intp)
        high = np.floor_divide(np.maximum(starts, ends), _INDEX_CELL_M).astype(np.intp)
        for i in range(len(starts)):
            for cx in range(low[i, 0], high[i, 0] + 1):
                for cy in range(low[i, 1], high[i, 1] + 1):
                    buckets[(cx, cy)].append(i)
        # Packed once: the query concatenates whole buckets, and a list of
        # Python ints would be re-boxed into an array on every one of ~27k casts.
        self.cells = {cell: np.asarray(rows, dtype=np.intp) for cell, rows in buckets.items()}

    def cast_both(
        self, origin: np.ndarray, direction: np.ndarray, max_m: float
    ) -> tuple[float | None, float | None]:
        """Distance to the nearest segment each way along `direction`, or None.

        Both directions out of one solve: negating `direction` negates the
        determinant and `along` while leaving `across` untouched, so the
        backward ray is the same arithmetic read at negative `along`. That
        halves the work, and — the reason it is written this way rather than as
        two calls — it makes it impossible for the two sides of a station to be
        measured by subtly different code.

        Nearest rather than first-found: a bucket holds its segments in the
        order the sheets were read, so taking the first hit would make the
        answer depend on which of six map sheets happened to load first.
        """
        solved = self._solve(origin, direction, max_m)
        if solved is None:
            return None, None
        _, along, on_segment = solved
        forward = on_segment & (along >= 0.0) & (along <= max_m)
        backward = on_segment & (along <= 0.0) & (along >= -max_m)
        return (
            float(along[forward].min()) if forward.any() else None,
            float(-along[backward].max()) if backward.any() else None,
        )

    def _solve(
        self, origin: np.ndarray, direction: np.ndarray, max_m: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """Candidate rows, their ray parameter, and which of them are on segment.

        🔴 **One arithmetic, every caller**, which is `cast_both`'s own argument
        carried one level down. That docstring says the two directions share a
        solve so it is impossible for the two sides of a station to be measured
        by subtly different code; the same holds for the two *questions* asked at
        a station — how far the kerb is, and which edge lies across the far ray.
        A second copy of this would let a partner be found beyond a kerb that the
        same station says was never crossed.
        """
        near, far = origin - direction * max_m, origin + direction * max_m
        low = np.floor_divide(np.minimum(near, far), _INDEX_CELL_M).astype(np.intp)
        high = np.floor_divide(np.maximum(near, far), _INDEX_CELL_M).astype(np.intp)
        chunks = [
            rows
            for cx in range(low[0], high[0] + 1)
            for cy in range(low[1], high[1] + 1)
            if (rows := self.cells.get((cx, cy))) is not None
        ]
        if not chunks:
            return None

        # A segment spanning several cells appears in several chunks. Left in:
        # a duplicate cannot change a minimum, and de-duplicating costs more
        # than the arithmetic it would save. ⚠️ Nor can it change an *argmin*'s
        # answer, which `cast_hit` relies on: the duplicate rows are the same
        # segment, so they carry the same owner and the same tangent.
        rows = chunks[0] if len(chunks) == 1 else np.concatenate(chunks)
        start = self.starts[rows]
        edge = self.ends[rows] - start
        offset = start - origin
        denominator = direction[1] * edge[:, 0] - direction[0] * edge[:, 1]
        solvable = np.abs(denominator) >= 1e-12
        if not solvable.any():
            return None

        safe = np.where(solvable, denominator, 1.0)
        along = (offset[:, 1] * edge[:, 0] - offset[:, 0] * edge[:, 1]) / safe
        across = (direction[0] * offset[:, 1] - direction[1] * offset[:, 0]) / safe
        on_segment = solvable & (across >= -1e-9) & (across <= 1.0 + 1e-9)
        return rows, along, on_segment

    def cast(self, origin: np.ndarray, direction: np.ndarray, max_m: float) -> float | None:
        """`cast_both`'s forward half, for a caller measuring one direction."""
        return self.cast_both(origin, direction, max_m)[0]

    def cast_hit(
        self, origin: np.ndarray, direction: np.ndarray, max_m: float, *, exclude: int
    ) -> tuple[tuple[float, int] | None, tuple[float, int] | None]:
        """`cast_both`'s answer with the winning row, and `exclude`'s owner skipped.

        A row per direction rather than a distance, because the caller wants both
        what was hit and which way it runs, and `ends[row] - starts[row]` is the
        only place the second lives.

        🔴 **Both directions from one solve, for `cast_both`'s own reason.** The
        first draft called this twice, once per heading, which made `_solve`'s
        "one arithmetic, every caller" claim false in the same commit that wrote
        it — negating `direction` negates `along` and leaves the cell set and
        `across` untouched, so the second solve was a duplicate of the first.

        ⚠️ **`exclude` is not an optimisation.** The origin sits on its own
        polyline, so without it every cast returns that edge at zero distance and
        no partner is ever found. It is passed rather than inferred because an
        index does not know which of its owners the caller is standing on.
        """
        solved = self._solve(origin, direction, max_m)
        if solved is None:
            return None, None
        rows, along, on_segment = solved
        usable = on_segment & (self.owners[rows] != exclude)
        return (
            self._nearest(rows, along, usable & (along >= 0.0) & (along <= max_m), 1.0),
            self._nearest(rows, along, usable & (along <= 0.0) & (along >= -max_m), -1.0),
        )

    @staticmethod
    def _nearest(
        rows: np.ndarray, along: np.ndarray, mask: np.ndarray, sign: float
    ) -> tuple[float, int] | None:
        """The masked hit nearest the origin, as a positive distance and its row.

        `np.where` rather than compressing the arrays: the row index is what is
        being asked for, so it may not be renumbered on the way.
        """
        if not mask.any():
            return None
        candidates = np.where(mask)[0]
        winner = candidates[np.argmin(sign * along[candidates])]
        return float(sign * along[winner]), int(rows[winner])


def published_edges(
    city: Config,
    spec: CarriagewayEdge,
    region_id: str,
    transform: GameTransform,
    *,
    sources_root: Path | None,
) -> _Index:
    """One publisher's carriageway edge, in the region's game plan frame.

    Read into game space rather than leaving the graph in projected metres,
    because the graph's polylines are what the drawn ribbon is measured from and
    they are already here. `to_game` is used vectorised for the reason its
    docstring gives: the sign on Z is a consequence of Godot's handedness, and
    restating it is how it drifts.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)

    wanted = set(spec.codes)
    off_grade = set(spec.off_grade_codes)
    elevation_field = spec.elevation_field
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    for path, member in reads:
        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=city.projected_bounds(region_id).bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("edge_type"))
        # Grade, on whichever term the publisher offers, and both are
        # exclusions because at grade is the *unmarked* case in both files — a
        # null relative level in the drawings, a code absent from `codes` in
        # iB1000. See the city file for the measurement behind the drawing
        # codes; it is the opposite of the obvious reading.
        levels = layer.column(elevation_field) if elevation_field else None
        # 🔴 **An AREA publisher is a different measurement, not a different
        # reader** (`Q94`). HyD draws the maintained carriageway as polygons and
        # tiles Wan Chai's into 552 of them, so the boundary between two is a
        # maintenance division rather than a kerb — a ray stops at the first one
        # and reports a plausible, short width. The outline of the *union* is
        # what may be cast at, and a seam is the segment two polygons both draw.
        #
        # ⚠️ **Derived here rather than imported from `pipeline/carriageway.py`,
        # on this tool's founding rule**: it shares no code with what it grades,
        # and the two arriving at the same outline independently is the check.
        area = spec.geometry == CARRIAGEWAY_AREA
        if area:
            owners, polygons = gdb.polygons(layer)
            parts = [
                (owner, ring)
                for owner, rings in zip(owners, polygons, strict=True)
                for ring in rings
            ]
        else:
            owners, lines = gdb.polylines(layer)
            parts = list(zip(owners, lines, strict=True))
        drawn_starts: list[np.ndarray] = []
        drawn_ends: list[np.ndarray] = []
        for owner, points in parts:
            if str(codes[owner]) not in wanted:
                continue
            if levels is not None and str(levels[owner]) in off_grade:
                continue
            projected = np.asarray(points, dtype=np.float64)
            game_x, _, game_z = transform.to_game(projected[:, 0], projected[:, 1])
            part_starts, part_ends = _segments(np.column_stack([game_x, game_z]))
            drawn_starts.append(part_starts)
            drawn_ends.append(part_ends)
        if area and drawn_starts:
            drawn_starts, drawn_ends = _outline(drawn_starts, drawn_ends)
        starts.extend(drawn_starts)
        ends.extend(drawn_ends)

    if not starts:
        return _Index(np.empty((0, 2)), np.empty((0, 2)))
    return _Index(np.vstack(starts), np.vstack(ends))


def _outline(
    starts: list[np.ndarray], ends: list[np.ndarray]
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Abutting polygons' own edge, with the seams between them removed.

    A seam is drawn by both polygons that meet on it and so appears twice; the
    outline appears once. Counting is enough, and it needs no adjacency graph.

    ⚠️ **Written from the rule rather than from `pipeline/carriageway.py`'s
    version of it**, which is this tool's whole standing: the two are expected
    to agree and a divergence is a finding about one of them.
    """
    first, second = np.vstack(starts), np.vstack(ends)
    a, b = np.round(first, 3), np.round(second, 3)
    # Canonical per segment, so a seam its two owners traverse in opposite
    # directions — the usual case for polygons wound the same way — matches.
    flip = (a[:, 0] > b[:, 0]) | ((a[:, 0] == b[:, 0]) & (a[:, 1] > b[:, 1]))
    key = np.hstack([np.where(flip[:, None], b, a), np.where(flip[:, None], a, b)])
    _, inverse, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    alone = counts[inverse.ravel()] == 1
    return [first[alone]], [second[alone]]


def graph_edges(graph: dict[str, Any]) -> _Index:
    """The graph's own level-0 centrelines, indexed so a ray can name one.

    A second index over a different population from `published_edges`': that one
    holds a publisher's kerbs, this one holds `roadgraph.json`'s own polylines,
    and the decomposition needs to ask which *edge* lies across a station's far
    ray. Owners carry `edge["id"]` so the answer comes back as a graph id.

    ⚠️ **Level 0 only, matching the walk.** A ramp overhead shares plan position
    with the street beneath it, and a flyover is nobody's opposed carriageway.
    """
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    owners: list[np.ndarray] = []
    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        head, tail = _segments(polyline[:, [0, 2]])
        if not len(head):
            continue
        starts.append(head)
        ends.append(tail)
        owners.append(np.full(len(head), int(edge["id"]), dtype=np.intp))
    if not starts:
        return _Index(np.empty((0, 2)), np.empty((0, 2)))
    return _Index(np.concatenate(starts), np.concatenate(ends), np.concatenate(owners))


def opposed_offset_deg(here: np.ndarray, there: np.ndarray) -> float:
    """Degrees off anti-parallel — 0 opposed, 90 perpendicular, 180 alongside.

    🔴 **Anti-parallel and not merely parallel, and the graph is what makes that
    readable.** `roads.py` normalises every one-way so the file "only ever says
    `forward`", which means a one-way polyline is drawn in its own travel
    direction. Two carriageways of a pair therefore run 180° apart, and a
    service road running *with* its neighbour reads 0° apart — a distinction a
    parallelism test throws away and this one keeps.

    ⚠️ Unsigned. Which way the partner leans says nothing about whether it is
    one.

    ⚠️ **`polyline.directed_residual_deg` is the heading-space sibling** — this is
    `180 - that`, exactly — and it is not reused because it takes *headings*,
    and there is no shared vector-to-heading helper: `signs._heading_deg` is
    already a knowing second copy of `fares.Snap.heading_deg`. Reusing it would
    add a third copy of the atan2 convention to save a dot product. ⚠️ And the
    `axis_residual_deg` family folds mod 180, which cannot tell parallel from
    anti-parallel — the one distinction this function exists for.
    """
    a, b = np.hypot(*here), np.hypot(*there)
    if a <= 0.0 or b <= 0.0:
        return float("nan")
    cosine = float(np.clip((here @ there) / (a * b), -1.0, 1.0))
    return 180.0 - math.degrees(math.acos(cosine))


def _partner_at(
    centrelines: _Index,
    origin: np.ndarray,
    normal: np.ndarray,
    tangent: np.ndarray,
    max_ray_m: float,
    *,
    edge: int,
) -> tuple[int, float]:
    """The most opposed centreline within reach of one station, and by how much.

    🔴 **Capped at the instrument's OWN ray cap, which REMOVES a knob rather
    than adding one.** `Q72`'s NO ENTRY entry rejected a pairing rule built on a
    free radius `R`, whose count ran 8 → 29 → 49 → 80 as `R` went 10 → 30 m.
    `--max-ray-m` is not that: it is the distance at which this tool already
    declares a station unmeasurable, it caps every other measurement here, and
    `Q95` already swept it and published the result.

    ⚠️ **It was the station's own far ray first, and the six pairs `surface.py`
    already knows about are what refuted that.** All three LOCKHART ROAD pairs
    came back unpaired: e86's span is 7.06 m while its partner's centreline is
    6.82 m away, because the far ray stops at the far kerb of e86's *own*
    carriageway around 3.5 m and never reaches across. A cap that cannot see a
    known pair is measuring its own reach.

    ⚠️ **Both directions, because a symmetric station has no far side.** Where
    the two rays are near-equal — Lockhart again, 3.53 against 3.53 — picking
    "the far one" is picking noise, and the per-station vote would then split a
    real pair across both sides of the road.

    Selecting the *most opposed* candidate is a measurement, not a judgement:
    the bar it is measured against stays in `_candidate`, where the table is
    printed, so a sweep of that bar re-reads this survey rather than re-walking
    the region.

    ⚠️ **`tramway.py`'s `_pair_rails` is this repo's other implementation of
    cast-then-ballot-then-mutual, and the two differ deliberately.** That one
    requires an agreement *fraction* before it accepts a ballot and keeps
    one-way votes; this one takes a plurality and drops them. Neither is the
    other's bug — but a change to the shape here should be read against it.
    """
    best, offset = -1, float("nan")
    for hit in centrelines.cast_hit(origin, normal, max_ray_m, exclude=edge):
        if hit is None:
            continue
        row = hit[1]
        angle = opposed_offset_deg(tangent, centrelines.ends[row] - centrelines.starts[row])
        if math.isnan(angle):
            continue
        if best < 0 or angle < offset:
            best, offset = int(centrelines.owners[row]), angle
    return best, offset


def _sides(
    origin: np.ndarray,
    normal: np.ndarray,
    indexes: list[tuple[str, _Index]],
    max_ray_m: float,
) -> list[tuple[str, float | None, float | None]]:
    """Every publisher's two ray hits at one station, in preference order.

    🔴 **The only place `cast_both` is called per station**, and that is the
    point rather than tidiness. Both readings below — the near-side overhang and
    the two-sided width — consume this one list, so they cannot disagree about
    what was hit. Casting a second, independent pair for the width would re-open
    precisely the failure `cast_both`'s own docstring exists to close.

    A row per configured publisher, including ones that hit nothing, because the
    losers are the cross-check. Short-circuiting once one answers is the obvious
    optimisation and it would delete both the spread and the width's preference
    order in one move.
    """
    return [(name, *index.cast_both(origin, normal, max_ray_m)) for name, index in indexes]


def nearest_published(
    sides: list[tuple[str, float | None, float | None]],
) -> tuple[str, float, list[float]]:
    """The nearest published edge at one station, who published it, and the spread.

    `sides` is read as a preference order — the first publisher that answers
    wins — which is the rule the whole two-source design rests on, so it lives
    in one named function with a test on it rather than inline in the walk.
    Every publisher is still asked: the losers do not decide the measurement but
    they are the cross-check, and `Q57`'s argument for reading two sources is
    exactly that their disagreement is a finding.

    The nearer of a publisher's two rays wins, because the far one is what a
    junction mouth and a dual carriageway corrupt. `width_published` below is
    the reading that wants the far one, and it is a different question with a
    different preference order.

    Returns an empty name and a NaN distance when nobody answered.
    """
    chosen, nearest = "", float("nan")
    spread: list[float] = []
    for name, forward, backward in sides:
        hits = [hit for hit in (forward, backward) if hit is not None]
        if not hits:
            continue
        closest = min(hits)
        spread.append(closest)
        if not chosen:
            chosen, nearest = name, closest
    return chosen, nearest, spread


def width_published(
    sides: list[tuple[str, float | None, float | None]],
) -> tuple[str, float, float, list[float]]:
    """The first publisher that spans the road, and the two rays it spanned with.

    🔴 **Both rays must come from ONE publisher.** The drawings are TD's painted
    carriageway edge and iB1000's `RM` is LandsD's surveyed margin; summing one
    on the near side and the other on the far side adds a cartographic truth to
    a topographic one, and the two disagree by metres where both answer. The sum
    would still look like a road.

    ⚠️ **A different preference order than `nearest_published`'s**, on the same
    list. A publisher can answer the near side and not reach across the street —
    which is the drawings' normal case, being two orders of magnitude sparser —
    so it wins the overhang and loses the width. That is why the caller records
    `width_source` separately.

    ⚠️ **Returns the rays on `left_of`'s sign, not sorted into (near, far).**
    `Station` derives the ordering, so the near/far convention lives in exactly
    one place — `Report.spans`' argument, applied to a pair rather than a
    population. ⚠️ Nothing reads the *side*: `_partner_at` casts both ways.

    Returns an empty name and NaN distances when nobody spanned. The name is the
    presence test; a NaN width summed into a distribution is not.
    """
    chosen, ahead, behind = "", float("nan"), float("nan")
    spread: list[float] = []
    for name, forward, backward in sides:
        if forward is None or backward is None:
            continue
        spread.append(forward + backward)
        if not chosen:
            chosen, ahead, behind = name, forward, backward
    return chosen, ahead, behind, spread


def survey(
    city: Config,
    region_id: str,
    *,
    spacing_m: float,
    max_ray_m: float,
    junction_m: float,
    sources_root: Path | None,
    out_root: Path | None,
) -> Report:
    """Walk every level-0 edge and measure it against each published source."""
    spec = city.carriageway_survey
    if spec is None:
        raise SystemExit(
            f"city '{city.id}' declares no carriageway_survey block, so there is no published "
            "edge to measure against. That is the honest answer, not a failure."
        )

    out_dir = city.out_dir(region_id, out_root)
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    widths = half_widths(read_manifest(city, region_id, out_root=out_root))
    transform = city.game_transform(region_id)

    report = Report(names=road_names(graph))
    indexes: list[tuple[str, _Index]] = []
    for entry in spec.edges:
        index = published_edges(city, entry, region_id, transform, sources_root=sources_root)
        report.segments[entry.name] = len(index.starts)
        indexes.append((entry.name, index))

    nodes = np.asarray([node["pos"] for node in graph["nodes"]], dtype=np.float64)[:, [0, 2]]
    centrelines = graph_edges(graph)

    for edge in graph["edges"]:
        if int(edge["elevation_level"]) != 0:
            continue
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        edge_id = int(edge["id"])
        report.edges_walked += 1
        report.lengths[edge_id] = float(plan_lengths(polyline)[-1])
        report.directions[edge_id] = str(edge["direction"])
        report.lanes[edge_id] = int(edge["lanes"])
        report.lanes_source[edge_id] = str(edge.get("lanes_source", "authored"))
        report.widths_authored[edge_id] = float(edge["width_m"])
        drawn_half_widths = widths.get(edge_id, [])

        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            if not normal.any():
                continue
            origin = station[[0, 2]]
            # One solve, two readings. See `_sides`.
            sides = _sides(origin, normal, indexes, max_ray_m)
            chosen, nearest, spread = nearest_published(sides)
            spanner, ahead, behind, span_spread = width_published(sides)

            if spanner and len(span_spread) > 1:
                report.width_agreement.append(max(span_spread) - min(span_spread))
            if not chosen:
                report.unmeasured += 1
                continue
            if len(spread) > 1:
                report.agreement.append(max(spread) - min(spread))

            near_junction = bool(np.min(np.hypot(*(nodes - origin).T)) <= junction_m)
            # ⚠️ **The skip mirrors `edge_widths`' own filter and must keep
            # mirroring it.** `_candidate` votes over `report.spans` with junction
            # stations dropped, so a partner found anywhere else is measured and
            # never read — 6,604 of 12,502 stations on Wan Chai. `-1`/NaN is
            # already the "reached no graph edge" sentinel, so no reader can tell
            # a skipped station from an unanswered one. Widen that filter and this
            # guard has to widen with it.
            partner_edge, partner_offset = (
                _partner_at(centrelines, origin, normal, along[[0, 2]], max_ray_m, edge=edge_id)
                if spanner and not near_junction
                else (-1, float("nan"))
            )

            report.stations.append(
                Station(
                    edge=edge_id,
                    nearest_m=nearest,
                    overhang_m=half_width_at(drawn_half_widths, vertex) - nearest,
                    source=chosen,
                    near_junction=near_junction,
                    width_source=spanner,
                    width_forward_m=ahead,
                    width_backward_m=behind,
                    partner_edge=partner_edge,
                    partner_offset_deg=partner_offset,
                )
            )
            report.edges_measured.add(edge_id)

    return report


def _percentiles(values: list[float], points: tuple[int, ...]) -> list[float]:
    if not values:
        return [float("nan")] * len(points)
    return [float(v) for v in np.percentile(np.asarray(values), points)]


def _share_over(values: list[float], threshold: float) -> float:
    return float(np.mean(np.asarray(values) > threshold)) if values else 0.0


def _dominant(names: Iterable[str]) -> str:
    """The publisher that answered most of an edge's stations.

    Not whichever answered last: a preference-ordered fallback means one
    edge can be answered by both, and naming the last would be a coin toss
    printed as a fact. Written once because the overhang listing and the
    span listing both need it, over different fields of the same station.
    """
    return Counter(names).most_common(1)[0][0]


def _share_under(values: list[float], threshold: float) -> float:
    return float(np.mean(np.asarray(values) < threshold)) if values else 0.0


@dataclass
class EdgeWidth:
    """One edge's measured span, and what it does and does not license."""

    edge: int
    median_m: float
    n: int
    # Share of this edge's stations the ceiling refuses. The column that tells a
    # reader which rows are escapes rather than roads.
    refused_share: float
    off_centre: float
    source: str
    refused: bool

    # ── the decomposition (`Q95` follow-on) ───────────────────────────────
    #
    # This edge's own carriageway, taken as twice the median NEAR ray: the
    # centreline is read as the middle of the carriageway it is drawn in, and
    # the far ray — the one that crosses the median and the opposed
    # carriageway — takes no part in it.
    #
    # ⚠️ **An assumption, and the residual below is the only thing that can
    # contradict it.** It is measured for every edge, paired or not, because a
    # number recorded only where it survives is `Q58`'s `drawn_gauge_m` trap.
    own_m: float = float("nan")
    # The edge this one's own stations voted for, after the bearing bar.
    candidate: int | None = None
    # …and the same edge only where the vote is MUTUAL. `surface.py` measures
    # its pair gap from both directions because a one-sided measure lets the
    # two halves disagree, and the region's pairs did disagree, by up to 3.9 m.
    # The same argument applies to the pairing itself.
    partner: int | None = None
    # Span minus both carriageways: what is left for the median, symmetric over
    # the pair. 🔴 **Negative is the reachable failure** — the parts exceed the
    # whole, which cannot be true, so `own = 2 x near` has failed on this pair.
    median_gap_m: float = float("nan")
    # How far the pair's two halves disagree about the span they both crossed.
    # Reported, never gated: this tool grades rather than checks.
    span_disagreement_m: float = float("nan")
    # Whether `own_m` falls outside the manual's *dual* column. Separate from
    # `refused` on purpose: a row may have a perfectly readable span and an
    # unreadable half, and pooling the two flags would hide which failed.
    own_refused: bool = True

    # ── did the ray cross a median at all? (`Q95` follow-on) ──────────────
    #
    # `roadgraph.json`'s own `direction`, carried on the row because the basis
    # below depends on it and a property may not reach into the report.
    two_way: bool = False

    @property
    def beyond_m(self) -> float:
        """What the span leaves BEYOND this edge's own carriageway.

        🔴 **The classifier, and it needs no new measurement.** `median_m` is
        the span and `own_m` is twice the near ray — the carriageway the
        centreline is drawn in — so their difference is the room left over for
        whatever the ray crossed into. `_render_pairs`'s residual says the same
        thing and needs a *mutual partner* to say it, which is why it reaches
        110 rows where this reaches every one.

        ⚠️ **A difference of two medians, not the median of a difference.** On
        an edge whose stations agree the two coincide; where they do not, this
        edge's own stations disagree about where its kerb is, and the middle
        band below is where that lands. Taking the median per station instead
        would hide exactly that.
        """
        return self.median_m - self.own_m

    def crossing(self, bounds: WidthBounds) -> str:
        """Whether the span crossed into an opposed carriageway: the three states.

        🔴 **Both bounds are transcribed TPDM clauses and neither is fitted.**
        Under one through lane (4.3.9.8) there is nowhere for an opposed
        carriageway to be, so the ray stopped at the far kerb of the road it was
        walking. At or above the narrowest dual carriageway in Table 3.4.2.1
        there is room for one, so the span may be two. `Q72` rejected a pairing
        rule built on a free radius whose count ran 8 → 29 → 49 → 80 across it;
        a rule whose ends are published figures cannot be walked toward an
        answer that way.

        ⚠️ **The middle state is load-bearing and is not indecision.** A single
        threshold has to call a reading with room for a lane but not a
        carriageway one way or the other, and `Q95`'s own TONNOCHY ROAD
        counter-example — 16.7 m of span over halves of 6.43 and 11.78, "not a
        ray that stayed put" — sits in that gap. Published as neither, it stays
        out of the widths; published as uncrossed, it would BE one.
        """
        beyond = self.beyond_m
        if math.isnan(beyond):
            return UNRESOLVED
        if beyond < bounds.hard_min_m:
            return UNCROSSED
        if beyond >= bounds.dual_min_m:
            return CROSSED
        return UNRESOLVED

    @property
    def decomposed(self) -> bool:
        """Whether this row's `own_m` is a carriageway width that may be read.

        Mutually paired, the residual non-negative, and the half inside the
        manual's dual column — a different column from the span's, because a
        decomposed half is by definition one carriageway of a pair.
        """
        return self.partner is not None and self.median_gap_m >= 0.0 and not self.own_refused

    def basis(self, bounds: WidthBounds) -> str:
        """Which route, if any, licenses reading a CARRIAGEWAY WIDTH off this row.

        Four states, and the empty one is the common answer — a row with a
        perfectly good span and no way to say whose carriageway it is.

        🔴 **`decomposed` is tested BEFORE `refused`, and that is not an
        oversight.** `refused` is `max_m`, a bound on a *single* carriageway — a
        four-lane one plus a parking strip. A decomposed row is by definition
        one half of a *dual*, and `Q95` settled that a half answers to the dual
        column instead, because reading the single column at both scales bounds
        the half by a figure it could never reach. Applying the span's ceiling
        to a row already split is that same error pointing the other way, and it
        would make this table disagree with `_render_pairs` — which publishes
        all 14 decomposed rows — by exactly the two FLEMING ROAD edges whose
        16.56 m span is a perfectly ordinary 6.82 + 2.19 + 7.54 dual
        carriageway. The dual ceiling still applies, inside `decomposed`.

        🔴 **And it outranks `uncrossed` where both fire, though they name
        different numbers.** A partner whose own half measures small inflates
        this row's residual into the non-negative, so `decomposed` can fire on a
        pair one half of which is junk while `uncrossed` reads the span as this
        edge's whole width. The overlap is counted in the report rather than
        assumed empty; a partner that voted back is the stronger evidence, so it
        wins. ⚠️ The region's own numbers argue the other way — every one of the
        report's cross-check disagreements traces to a partner's reading rather
        than to this rule — but flipping the precedence to suit one run's table
        is fitting, and it moves 2 rows of 276. `Q95` records it for the
        assignment to settle.
        """
        if self.decomposed:
            return BASIS_DECOMPOSED
        if self.refused:
            return ""
        if self.two_way:
            # Already whole: `_render_pairs` never pairs a two-way edge, on the
            # ground that decomposing a street into itself is not a split.
            return BASIS_TWO_WAY
        if self.crossing(bounds) == UNCROSSED:
            return BASIS_UNCROSSED
        return ""

    def carriageway_m(self, bounds: WidthBounds) -> float:
        """The width this row licenses, or NaN where it licenses none.

        ⚠️ **Two different measurements behind one number, which is why the
        basis travels with it.** A decomposed row's width is `own_m`, half of a
        span; every other published row's is the span itself. Quoting the two
        as one column without the basis beside it would be `Q57`'s
        generalisation — a property established on one population and read
        across another.
        """
        basis = self.basis(bounds)
        if not basis:
            return float("nan")
        return self.own_m if basis == BASIS_DECOMPOSED else self.median_m


def edge_widths(report: Report, bounds: WidthBounds, *, minimum_n: int = 3) -> list[EdgeWidth]:
    """Per-edge span: the median FIRST, then the refusal.

    🔴 **Order matters, and the obvious order is the wrong one.** Refusing
    stations at `max_m` and then taking a median manufactures a median just
    under the ceiling for an edge most of whose stations escape through a
    junction mouth — a number that looks like a careful reading of a wide street
    and is an average of the crossings beside it. Taking the median over every
    two-sided station and refusing the *edge* on that median cannot do this, and
    it leaves `refused_share` to say how much of the edge was escaping.

    That also gives the `n` exceeds keeps tell at edge level: the edges that have
    a median outnumber the edges published.

    Junction stations are dropped, as everywhere else in this report — a station
    in a junction mouth has no far kerb to find, and it reads as a wide road.
    """
    per_edge: dict[int, list[Station]] = defaultdict(list)
    for station in report.spans:
        if not station.near_junction:
            per_edge[station.edge].append(station)

    rows: list[EdgeWidth] = []
    for edge_id, stations in per_edge.items():
        if len(stations) < minimum_n:
            continue
        widths = [s.width_m for s in stations]
        median = float(np.median(widths))
        own = 2.0 * float(np.median([s.width_near_m for s in stations]))
        rows.append(
            EdgeWidth(
                edge=edge_id,
                median_m=median,
                n=len(stations),
                refused_share=_share_over(widths, bounds.max_m),
                off_centre=float(np.median([s.off_centre for s in stations])),
                source=_dominant(s.width_source for s in stations),
                refused=not bounds.hard_min_m <= median <= bounds.max_m,
                own_m=own,
                candidate=_candidate(stations, bounds),
                own_refused=not bounds.hard_min_m <= own <= bounds.dual_max_m,
                two_way=report.directions.get(edge_id) == BOTH,
            )
        )
    _pair_up(rows, report)
    return sorted(rows, key=lambda row: -row.median_m)


def _candidate(stations: list[Station], bounds: WidthBounds) -> int | None:
    """The edge this one's stations most often found within reach either side.

    Modal rather than nearest-anything: an edge is walked at 4 m stations and a
    junction mouth at one end can hand two or three of them a cross street, so
    taking any single station's answer would let the shortest edges be paired by
    their worst reading. `_dominant` makes the same argument for the publisher.

    ⚠️ **This is where the bearing bar is applied, and it is applied to a
    measurement `survey` already took.** The angle was recorded per station and
    judged nowhere, so sweeping the bar re-reads the same survey rather than
    re-walking the region — which is what makes it mutation-checkable at all.
    """
    votes = Counter(
        station.partner_edge
        for station in stations
        if station.partner_edge >= 0
        and station.partner_offset_deg <= bounds.pair_bearing_tolerance_deg
    )
    return votes.most_common(1)[0][0] if votes else None


def _pair_up(rows: list[EdgeWidth], report: Report) -> None:
    """Resolve mutual pairs and fill each half's residual, in place.

    🔴 **Mutual, and one-way both ways.** `surface.py` measures its pair gap from
    both directions and says why: a one-sided measure lets the two halves
    disagree, and the region's pairs did disagree, by up to 3.9 m. The same holds
    for the pairing itself — an edge that finds a neighbour on either side
    has found *something*, and only the neighbour finding it back says the two
    are halves of one road. A `direction=both` edge is excluded on the far
    stronger ground that it is already a whole carriageway; pairing it would
    decompose a street into itself.

    ⚠️ **The residual is symmetric, `0.5 x (span_A + span_B)`**, for the reason
    `_centreline_gap_m` gives: the two halves are supposed to name the same pair
    of kerbs, so taking either edge's own span would publish two different
    residuals for one median.
    """
    by_edge = {row.edge: row for row in rows}
    for row in rows:
        other = by_edge.get(row.candidate) if row.candidate is not None else None
        if other is None or other.candidate != row.edge:
            continue
        ways = (report.directions.get(row.edge), report.directions.get(other.edge))
        if ways != (FORWARD, FORWARD):
            continue
        row.partner = other.edge
        row.span_disagreement_m = abs(row.median_m - other.median_m)
        row.median_gap_m = 0.5 * (row.median_m + other.median_m) - row.own_m - other.own_m


@dataclass
class LaneVerdict:
    """How the graph's lane counts stand against the spans THIS tool measured.

    🔴 **Split by `lanes_source` since `Q94`, because it stopped being one
    question.** The graph used to carry an authored count on every edge and
    "outside the bracket" meant one thing. Now part of the region carries a
    count the pipeline bracketed off its *own* measurement, and pooling the two
    reports a single number over an authored table and an independent second
    survey — `Q57`'s generalisation, a property established on one population
    and quoted for another.

    ⚠️ **And the two halves are read in opposite directions.** On an authored
    edge, outside-the-bracket is the invented count failing against a
    measurement, which is the finding `Q19` has been narrowing for weeks. On a
    *measured* edge it is the two independent surveys disagreeing about the same
    street — this tool's ray against `pipeline/carriageway.py`'s — which is a
    much stronger statement and must not be diluted into the same total. It is
    reported, never a bar to retune: `Q95` records that the two agree on the
    width to a 5 mm median, so a lane disagreement here is where to go and look.
    """

    too_few: int = 0
    too_many: int = 0
    ambiguous: int = 0
    # The measured half of the two above: edges whose count the pipeline
    # bracketed off its own survey and which this one brackets differently.
    measured_total: int = 0
    measured_disagreeing: int = 0
    # 🔴 **Counted apart from the measured rows, and NOT as disagreement.** A
    # floored count sits above its own bracket by construction — the floor is
    # what puts it there — so folding these into `measured_disagreeing` reports
    # the floor working as two surveys conflicting. Measured when this was
    # written: 88 of 88 measured rows agreed and all 54 "disagreements" were
    # floored ones, which was the whole of the difference.
    #
    # ⚠️ **A pre-schema-11 path since `Q114`, and 0 on any current bundle.** The
    # ETL no longer floors a lane count at all — the floor moved into
    # `RoadGraph.lane_offset`, so those 57 edges publish `measured` and land in
    # the row below, still agreeing. Kept rather than deleted because this tool
    # reads whatever `roadgraph.json` is in `etl/out` and nothing stops that
    # being an older bundle; ⚠️ **the line it prints is conditional on it**, so a
    # current run does not carry a sentence about a population that no longer
    # exists.
    floored_total: int = 0
    # Two-way edges whose bracket is unambiguously odd and at least three, which
    # 3.4.2.7 forbids — a finding about the measurement or the direction field.
    findings: list[tuple[int, float]] = field(default_factory=list)

    @property
    def outside(self) -> int:
        return self.too_few + self.too_many


def lane_verdict(rows: list[EdgeWidth], report: Report, bounds: WidthBounds) -> LaneVerdict:
    """Bracket every published edge and count where the graph falls outside."""
    verdict = LaneVerdict()
    for row in rows:
        two_way = report.directions.get(row.edge) == BOTH
        low, high = lane_bracket(row.median_m, bounds, two_way=two_way)
        published = report.lanes.get(row.edge, 0)
        outside = published < low or published > high
        if published < low:
            verdict.too_few += 1
        elif published > high:
            verdict.too_many += 1
        source = report.lanes_source.get(row.edge, "authored")
        if source == "floored":
            verdict.floored_total += 1
        elif source != "authored":
            verdict.measured_total += 1
            verdict.measured_disagreeing += int(outside)
        if high > low:
            verdict.ambiguous += 1
        elif two_way and low >= 3 and low % 2:
            verdict.findings.append((row.edge, row.median_m))
    return verdict


def lane_bracket(width_m: float, bounds: WidthBounds, *, two_way: bool) -> tuple[int, int]:
    """How many through lanes a span could hold, as a range.

    🔴 **Never `width / lane_width_m`.** 3.2 m is the authored constant this
    whole question is about, and dividing by it would make the instrument agree
    with the value under test by construction — `Q72`'s tautology, one dimension
    over from the one it was written for. The divisor is TPDM 4.3.9.8's
    published through-lane range instead, so the answer is a bracket and its
    ambiguity is reported rather than resolved by fiat.

    On a two-way edge 3.4.2.7 removes the odd counts from the bracket — a
    two-way single carriageway may not be divided into three lanes, other than a
    climbing lane on a gradient. ⚠️ That narrows an *ambiguous* bracket only. A
    bracket that is unambiguously odd is left standing, because it is then a
    finding about the measurement or the direction field rather than a reading
    to be corrected into agreement.
    """
    low = int(width_m // bounds.lane_m[1])
    high = int(width_m // bounds.lane_m[0])
    if two_way and high > low:
        allowed = [n for n in range(low, high + 1) if not (n >= 3 and n % 2)]
        if allowed:
            return min(allowed), max(allowed)
    return low, high


def render(
    report: Report,
    *,
    spacing_m: float,
    max_ray_m: float,
    junction_m: float,
    bounds: WidthBounds | None,
    rows: list[EdgeWidth] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("published carriageway edge, segments read in region:")
    for name, count in report.segments.items():
        lines.append(f"  {name:<16} {count:>8,}")
    lines.append("")
    lines.append(
        f"  {report.measured:,} stations measured on {len(report.edges_measured)} of "
        f"{report.edges_walked} level-0 edges; {report.unmeasured:,} found no published edge "
        f"within {max_ray_m:.1f} m ({report.coverage:.1%} coverage, {spacing_m:.1f} m spacing)"
    )
    if report.agreement:
        spread = _percentiles(report.agreement, (50, 90))
        lines.append(
            f"  both sources answered {len(report.agreement):,} stations; "
            f"they disagree by p50 {spread[0]:.2f} m, p90 {spread[1]:.2f} m"
        )

    lines.append("")
    lines.append("overhang = drawn half-width - nearest published edge; positive crosses the kerb")
    lines.append(
        f"  {'population':<22} {'n':>8} {'p50':>8} {'p75':>8} {'p90':>8} {'> 0':>7} {'> 1 m':>7}"
    )
    away_stations = [s for s in report.stations if not s.near_junction]
    at_junction = [s for s in report.stations if s.near_junction]
    for label, population in (
        ("all stations", report.stations),
        (f"junctions dropped ({junction_m:.0f} m)", away_stations),
        ("junctions only", at_junction),
    ):
        values = [s.overhang_m for s in population]
        if not values:
            lines.append(f"  {label:<22} {0:>8}")
            continue
        p50, p75, p90 = _percentiles(values, (50, 75, 90))
        past = _share_over(values, 0.0)
        past_metre = _share_over(values, 1.0)
        lines.append(
            f"  {label:<22} {len(values):>8,} {p50:>8.2f} {p75:>8.2f} {p90:>8.2f} "
            f"{past:>6.1%} {past_metre:>6.1%}"
        )

    # The short-stub question, which is the reason this tool exists. Reported
    # twice over, because dropping junction stations does not isolate the
    # artefact on this population — it deletes it. See the note below the table.
    lines.append("")
    lines.append("by edge length — Q19's building half is 12 of 14 under 20 m:")
    lines.append(
        f"  {'band':<12} {'stations':>9} {'p50':>7} {'p90':>7} {'> 1 m':>7}   "
        f"{'no-jct n':>9} {'p50':>7} {'p90':>7} {'> 1 m':>7}"
    )
    everywhere: dict[int, list[float]] = defaultdict(list)
    away: dict[int, list[float]] = defaultdict(list)
    for station in report.stations:
        everywhere[station.edge].append(station.overhang_m)
        if not station.near_junction:
            away[station.edge].append(station.overhang_m)

    def _band(source: dict[int, list[float]], low: float, high: float) -> list[float]:
        return [
            value
            for edge_id, values in source.items()
            if low <= report.lengths.get(edge_id, 0.0) < high
            for value in values
        ]

    starved_band = False
    for low, high, label in _BANDS:
        row = f"  {label:<12}"
        for source in (everywhere, away):
            flat = _band(source, low, high)
            if not flat:
                starved_band = True
                row += f" {0:>9} {'-':>7} {'-':>7} {'-':>7}  "
                continue
            p50, p90 = _percentiles(flat, (50, 90))
            past_metre = _share_over(flat, 1.0)
            row += f" {len(flat):>9,} {p50:>7.2f} {p90:>7.2f} {past_metre:>6.1%}  "
        lines.append(row.rstrip())
    if starved_band:
        # Not a gap in the data. An edge shorter than twice `--junction-m` has
        # no station that is not junction-adjacent, so the exclusion empties
        # the band by construction — which is the answer to the question this
        # table was built to ask, rather than a failure to answer it.
        lines.append(
            f"  ⚠️ a band is empty on the right: below {2 * junction_m:.0f} m an edge has no "
            f"station further than {junction_m:.0f} m from a node, so 'short edge' and "
            "'junction' are the same population here and cannot be separated this way"
        )

    lines.append("")
    lines.append(f"worst {_WORST} edges by p90 overhang, junction stations dropped:")
    lines.append(
        f"  {'edge':>6} {'len m':>7} {'n':>5} {'p90':>7} {'worst':>7}  {'source':<12} road"
    )
    ranked = sorted(
        (
            (edge_id, _percentiles(values, (90,))[0], values)
            for edge_id, values in away.items()
            if len(values) >= 3
        ),
        key=lambda item: -item[1],
    )
    answered: dict[int, list[str]] = defaultdict(list)
    for station in report.stations:
        answered[station.edge].append(station.source)
    for edge_id, p90, values in ranked[:_WORST]:
        source = _dominant(answered[edge_id])
        lines.append(
            f"  {edge_id:>6} {report.lengths.get(edge_id, 0.0):>7.1f} {len(values):>5} "
            f"{p90:>7.2f} {max(values):>7.2f}  {source:<12} "
            f"{report.names.get(edge_id, 'unnamed')}"
        )
    if bounds is not None:
        lines.extend(
            _render_width(
                report,
                bounds,
                max_ray_m=max_ray_m,
                rows=edge_widths(report, bounds) if rows is None else rows,
            )
        )
    return "\n".join(lines)


def _render_width(
    report: Report, bounds: WidthBounds, *, max_ray_m: float, rows: list[EdgeWidth]
) -> list[str]:
    """The two-sided half (`Q95`), appended below the overhang report.

    Not behind a flag. CLAUDE.md already requires this tool's table pasted for a
    `lane_width_m` or carriageway-floor change, and behind a flag the pasted table
    would silently omit the one section that grades exactly those values.
    """
    spans = report.spans
    # 🔴 The bounds are applied HERE and never in `survey`. `report.spans` is
    # the unfiltered population, so `n` and the keeps are two views of one
    # list and cannot drift to opposite sides of a guard.
    over_ceiling = sum(1 for s in spans if s.width_m > bounds.max_m)
    under_floor = sum(1 for s in spans if s.width_m < bounds.hard_min_m)
    kept = len(spans) - over_ceiling - under_floor

    lines = ["", "measured span = BOTH published edges at one station, from ONE publisher"]
    lines.append(
        f"  {len(spans):,} of {report.stations_walked:,} stations were spanned "
        f"({report.width_coverage:.1%}, {max_ray_m:.1f} m ray), against "
        f"{report.measured:,} answered on the near side"
    )
    by_publisher = Counter(station.width_source for station in spans)
    spanned = ", ".join(f"{name} {count:,}" for name, count in by_publisher.most_common())
    lines.append(f"  spanned by: {spanned or 'nobody'}")
    if report.width_agreement:
        spread = _percentiles(report.width_agreement, (50, 90))
        lines.append(
            f"  both spanned {len(report.width_agreement):,} stations, disagreeing by p50 "
            f"{spread[0]:.2f} m, p90 {spread[1]:.2f} m — ⚠️ far fewer than the "
            f"{len(report.agreement):,} above, so the near side's cross-check does NOT carry over"
        )
    lines.append(f"  {report.width_no_span:,} stations no publisher spanned")

    lines.append("")
    lines.append(
        f"station span, recorded over the REFUSALS too — n {len(spans):,} exceeds the "
        f"{kept:,} kept, and max must exceed {bounds.max_m:.1f} m"
    )
    lines.append(
        f"  {'population':<24} {'n':>7} {'p50':>7} {'p90':>7} {'max':>7} "
        f"{'> ' + format(bounds.max_m, '.1f'):>8} {'< ' + format(bounds.min_m, '.1f'):>8}"
    )
    away = [s for s in spans if not s.near_junction]
    for label, population in (
        ("all spanned", spans),
        ("  direction both", [s for s in spans if report.directions.get(s.edge) == BOTH]),
        (
            "  direction forward",
            [s for s in spans if report.directions.get(s.edge) == FORWARD],
        ),
        ("junctions dropped", away),
        ("junctions only", [s for s in spans if s.near_junction]),
    ):
        values = [s.width_m for s in population]
        if not values:
            lines.append(f"  {label:<24} {0:>7}")
            continue
        p50, p90 = _percentiles(values, (50, 90))
        lines.append(
            f"  {label:<24} {len(values):>7,} {p50:>7.2f} {p90:>7.2f} {max(values):>7.2f} "
            f"{_share_over(values, bounds.max_m):>7.1%} {_share_under(values, bounds.min_m):>7.1%}"
        )
    lines.append(
        f"  refused: {over_ceiling:,} over {bounds.max_m:.1f} m, "
        f"{under_floor:,} under one through lane ({bounds.hard_min_m:.1f} m); kept {kept:,}"
    )

    # 🔴 The confounder the ceiling cannot see. Kept its own table because the
    # one-way population is most of the network and its number is not a
    # carriageway width.
    lines.append("")
    lines.append(
        "off-centre = |near - far| / span; a centreline inside ONE carriageway of an opposed pair"
    )
    lines.append(f"  {'band':<12} {'n':>7} {'span p50':>9} {'> ' + format(bounds.max_m, '.1f'):>8}")
    for low, high in _OFF_CENTRE_BANDS:
        values = [s.width_m for s in away if low <= s.off_centre < high]
        if not values:
            lines.append(f"  {f'{low:.2f}-{high:.2f}':<12} {0:>7}")
            continue
        lines.append(
            f"  {f'{low:.2f}-{high:.2f}':<12} {len(values):>7,} "
            f"{_percentiles(values, (50,))[0]:>9.2f} {_share_over(values, bounds.max_m):>7.1%}"
        )

    published = [row for row in rows if not row.refused]
    lines.append("")
    lines.append("per edge: median over non-junction spanned stations, n >= 3, THEN the refusal")
    lines.append(
        f"  {len(rows)} edges have a median; {len(rows) - len(published)} refused on it; "
        f"{len(published)} published"
    )
    for label, want in (
        ("two-way — a carriageway width", BOTH),
        ("one-way — a KERB-TO-KERB SPAN", FORWARD),
    ):
        values = [row.median_m for row in published if report.directions.get(row.edge) == want]
        if not values:
            continue
        p50, p90 = _percentiles(values, (50, 90))
        lines.append(f"  {label:<32} {len(values):>4} edges  p50 {p50:>6.2f}  p90 {p90:>6.2f}")
    if published:
        lines.append(_authored_gap([(row.edge, row.median_m) for row in published], report, "  "))
        below = [row.median_m for row in published]
        lines.append(
            f"  below TD's {bounds.min_m:.1f} m two-lane minimum: "
            f"{sum(1 for m in below if m < bounds.min_m)} of {len(below)} — "
            "reported, never refused (3.4.2.2)"
        )

    lines.extend(_render_pairs(rows, report, bounds))
    lines.extend(_render_crossing(rows, report, bounds))

    lines.append("")
    lines.append(
        f"lanes = span / a TPDM through lane, {bounds.lane_m[0]:.2f}-{bounds.lane_m[1]:.2f} m "
        "(4.3.9.8) — never / lane_width_m"
    )
    verdict = lane_verdict(published, report, bounds)
    lines.append(
        f"  the graph's lanes fall outside the bracket on {verdict.outside} of {len(published)} "
        f"({verdict.too_few} too few, {verdict.too_many} too many); "
        f"ambiguous on {verdict.ambiguous}"
    )
    lines.append(
        f"  ⚠️ NOT one population: {verdict.measured_disagreeing} of "
        f"{verdict.measured_total} PIPELINE-measured counts disagree with this survey's own "
        "bracket — two independent rays over one street, and a rise is where to go and look"
    )
    if verdict.floored_total:
        lines.append(
            f"     {verdict.floored_total} more are floored, which sit above their bracket BY "
            "CONSTRUCTION and are not disagreement — a pre-schema-11 bundle, since `Q114` "
            "removed the floor"
        )
    lines.append(
        "     the remaining rows are authored, and those are the invented count `Q19` has "
        "been narrowing"
    )
    lines.append(
        f"  3.4.2.7 findings — two-way, unambiguously odd, >= 3 lanes: {len(verdict.findings)}"
    )
    for edge_id, median in verdict.findings[:_WORST]:
        lines.append(f"    {edge_id:>6} {median:>7.2f} m  {report.names.get(edge_id, 'unnamed')}")

    lines.append("")
    lines.append(
        f"widest {_WORST} PUBLISHED edges by median span, junction stations dropped "
        f"({len(rows) - len(published)} refused rows not listed; they rank above every row here)"
    )
    lines.append(
        f"  {'edge':>6} {'n':>5} {'span':>7} {'refus':>6} {'offctr':>7} {'dir':<8} "
        f"{'source':<12} road"
    )
    # ⚠️ Published rows only. Ranked over everything, this listing is fifteen
    # escapes: a ray through a junction mouth is wider than any road, so the
    # refusals sweep the top and a reader never sees a street. `refused_share`
    # stays as a column because a kept edge can still be part escape.
    for row in published[:_WORST]:
        lines.append(
            f"  {row.edge:>6} {row.n:>5} {row.median_m:>7.2f} {row.refused_share:>5.0%} "
            f"{row.off_centre:>7.2f} {report.directions.get(row.edge, '?'):<8} "
            f"{row.source:<12} {report.names.get(row.edge, 'unnamed')}"
        )
    return lines


def _render_pairs(rows: list[EdgeWidth], report: Report, bounds: WidthBounds) -> list[str]:
    """The decomposition: a one-way span split back into two carriageways.

    🔴 **A third table with different rules, and it must not be pooled into the
    one above.** That one publishes a *span* on a one-way edge and says so; this
    one publishes a *width*, on the far smaller population where a partner was
    found on both sides. Averaging the two would restate `Q57`'s own
    generalisation — a property established on one population and quoted for
    another — which is the error the span table was careful about.
    """
    # ⚠️ **`== FORWARD` here and `not two_way` in `_render_crossing` are the same
    # test only because `BACKWARD` never reaches `roadgraph.json`** — `roads.py`
    # normalises it away by reversing the polyline. Were a third value to arrive,
    # this table would exclude those edges and that one would include them, and
    # `pipeline/carriageway.py` would refuse them outright. Pinned by
    # `test_a_backward_centreline_is_normalised_to_forward`.
    one_way = [row for row in rows if report.directions.get(row.edge) == FORWARD]
    # ⚠️ **Counted over `one_way`, not over every row, or the funnel lies.**
    # `_candidate` never looks at direction, so a two-way edge with an
    # anti-parallel neighbour votes and then cannot possibly be found back —
    # `_pair_up` gates on `(FORWARD, FORWARD)`. Counted over all rows, the drop
    # from voted to mutual conflates "the neighbour did not vote back" with "the
    # edge was two-way all along", which is the one thing this line reports.
    voted = [row for row in one_way if row.candidate is not None]
    mutual = [row for row in rows if row.partner is not None]
    decomposed = [row for row in rows if row.decomposed]

    lines = ["", "pairs: a one-way span split in two, own = 2 x the near ray, resolved both ways"]
    lines.append(
        f"  {len(one_way)} of {len(rows)} edges with a median are one-way; "
        f"{len(voted)} found a centreline within {bounds.pair_bearing_tolerance_deg:.0f} deg "
        f"of anti-parallel inside the ray cap; {len(mutual)} were found back"
    )
    if not mutual:
        lines.append("  no mutual pair — nothing to decompose")
        return lines

    residuals = [row.median_gap_m for row in mutual]
    negative = sum(1 for value in residuals if value < 0.0)
    p50, p90, top = _percentiles(residuals, (50, 90, 100))
    lines.append(
        f"  residual = span - both carriageways, over the {len(mutual)} mutual rows "
        f"(n exceeds the {len(decomposed)} read)"
    )
    lines.append(f"    p50 {p50:>6.2f}  p90 {p90:>6.2f}  max {top:>6.2f}")
    # 🔴 The reachable failure. The parts cannot exceed the whole, so a negative
    # residual is `own = 2 x near` failing on that pair rather than a wide road.
    lines.append(f"    negative — the split failing, not a finding about the city: {negative}")
    lines.append(
        f"    over {bounds.median_max_m:.1f} m, TD's widest transcribed separator (3.4.2.3): "
        f"{sum(1 for value in residuals if value > bounds.median_max_m)} — reported, never refused"
    )
    lines.append(
        f"    half outside TD's dual column ({bounds.hard_min_m:.1f}-{bounds.dual_max_m:.1f} m, "
        f"Table 3.4.2.1): {sum(1 for row in mutual if row.own_refused)}"
    )

    # 🔴 **What the negatives ARE, rather than only how many.** A residual near
    # minus the partner's own half is a span that never crossed the median: the
    # ray stopped at the far kerb of the edge's own carriageway, so `span` is
    # already one carriageway and there is nothing to split. That reads directly
    # off `off_centre`, which is why it is reported as the two populations'
    # distributions rather than as a new threshold — LOCKHART ROAD's three
    # shared-endpoint pairs all land here.
    for label, group in (
        ("refused", [row for row in mutual if row.median_gap_m < 0.0]),
        ("read", decomposed),
    ):
        if not group:
            continue
        centres = _percentiles([row.off_centre for row in group], (50, 90))
        lines.append(
            f"    off-centre of the {label:<8} rows: p50 {centres[0]:>5.2f}  p90 {centres[1]:>5.2f}"
        )

    spread = [row.span_disagreement_m for row in mutual]
    p50, p90, top = _percentiles(spread, (50, 90, 100))
    lines.append(
        f"  the two halves disagree about the span they both crossed: "
        f"p50 {p50:>5.2f}  p90 {p90:>5.2f}  max {top:>5.2f}"
    )

    if decomposed:
        widths = [row.own_m for row in decomposed]
        p50, p90 = _percentiles(widths, (50, 90))
        lines.append(
            f"  DECOMPOSED CARRIAGEWAY — a width, not a span   {len(decomposed):>4} edges  "
            f"p50 {p50:>6.2f}  p90 {p90:>6.2f}"
        )
        lines.append(_authored_gap([(row.edge, row.own_m) for row in decomposed], report, "    "))

    lines.append("")
    lines.append(f"widest {_WORST} DECOMPOSED carriageways")
    lines.append(f"  {'edge':>6} {'pair':>6} {'own':>7} {'span':>7} {'resid':>7} {'disag':>7} road")
    for row in sorted(decomposed, key=lambda row: -row.own_m)[:_WORST]:
        lines.append(
            f"  {row.edge:>6} {row.partner:>6} {row.own_m:>7.2f} {row.median_m:>7.2f} "
            f"{row.median_gap_m:>7.2f} {row.span_disagreement_m:>7.2f} "
            f"{report.names.get(row.edge, 'unnamed')}"
        )
    return lines


def _authored_gap(measured: list[tuple[int, float]], report: Report, indent: str) -> str:
    """The `measured - authored width_m` line, shared by the three tables that print one.

    ⚠️ **The values come in from the caller rather than being read off a row
    here, and that is the whole point.** The three callers measure different
    things — a kerb-to-kerb span, a decomposed half, a licensed width — so a
    version of this that took rows would have to know which table it was
    printing, and the branch would be the pooling those tables exist to avoid.
    What is shared is the arithmetic against `widths_authored` and the format,
    which is all that was ever the same.
    """
    gaps = [value - report.widths_authored.get(edge, 0.0) for edge, value in measured]
    p10, p50, p90 = _percentiles(gaps, (10, 50, 90))
    return (
        f"{indent}measured - authored width_m: p10 {p10:+.2f}  p50 {p50:+.2f}  "
        f"p90 {p90:+.2f}; wider on {_share_over(gaps, 0.0):.0%}"
    )


def _render_crossing(rows: list[EdgeWidth], report: Report, bounds: WidthBounds) -> list[str]:
    """Which one-way spans never crossed a median, and the widths that licenses.

    🔴 **A FOURTH table with different rules again, and the reason it exists is
    reach.** `_render_pairs` above can only speak about an edge whose opposed
    partner voted back — 110 rows — and it found that 96 of them refuse their
    own split because the ray stopped at the near kerb and never crossed. That
    is a statement about the *span*, and it does not need a partner to make: it
    reads off `beyond_m`, which every row with a median carries. This table is
    that statement applied to all of them, with the pairs kept as the check.

    ⚠️ **The check is a prediction, not a fit.** The two instruments were built
    for different questions and agree only if the reading is sound, so their
    disagreement is a finding — and 3.4.2.2 supplies an honest cause, since a
    real Hong Kong carriageway may sit below the manual's minimum.
    """
    with_median = [row for row in rows if not row.refused]
    # ⚠️ `not two_way` rather than `== FORWARD`, which `_render_pairs` uses —
    # equivalent only while `BACKWARD` cannot reach the graph. See there.
    one_way = [row for row in with_median if not row.two_way]
    lines = [
        "",
        "crossing: did the span reach PAST the carriageway its centreline sits in?",
        f"  beyond = span - own; uncrossed under {bounds.hard_min_m:.2f} m (4.3.9.8, one through "
        f"lane), crossed at {bounds.dual_min_m:.2f} m (Table 3.4.2.1, narrowest dual carriageway)",
    ]
    if not one_way:
        lines.append("  no published one-way row — nothing to classify")
        return lines

    beyond = [row.beyond_m for row in one_way]
    p10, p50, p90 = _percentiles(beyond, (10, 50, 90))
    lines.append(
        f"  beyond over the {len(one_way)} published one-way rows: "
        f"p10 {p10:+.2f}  p50 {p50:+.2f}  p90 {p90:+.2f}"
    )
    # Asked once per row and reused by every counter below, for `grouped`'s
    # reason: three separate passes could only ever agree by construction, and
    # a reader has to take that on trust rather than read it.
    verdict_of = {row.edge: row.crossing(bounds) for row in one_way}
    verdicts = Counter(verdict_of.values())
    counts = "  ".join(f"{name} {verdicts.get(name, 0)}" for name in _CROSSINGS)
    lines.append(f"  {counts}")

    # 🔴 The free cross-check, and it is free because the two instruments were
    # built for different questions. On a mutual pair the residual already says
    # whether the parts fit inside the whole; this rule says the same thing from
    # one side. ⚠️ `unresolved` makes no prediction and is counted apart rather
    # than scored as a miss — scoring it would grade the rule on rows it
    # declined to judge.
    predicted = [row for row in one_way if row.partner is not None]
    scored = [row for row in predicted if verdict_of[row.edge] != UNRESOLVED]
    if scored:
        agreed = sum(
            1 for row in scored if (verdict_of[row.edge] == UNCROSSED) == (row.median_gap_m < 0.0)
        )
        lines.append(
            f"  cross-check vs the pairs' own residual, over the {len(scored)} mutual rows it "
            f"predicts ({len(predicted) - len(scored)} unresolved, no prediction):"
        )
        lines.append(
            f"    agreed {agreed}, disagreed {len(scored) - agreed} — a finding to go and look "
            "at, never a bar to retune (3.4.2.2 permits a carriageway below the minimum)"
        )

    # ⚠️ Counted rather than assumed empty. Where a partner measured its own half
    # as under a through lane this row's residual inflates into the non-negative,
    # so both bases can fire and they disagree about the number — `own_m` against
    # the whole span. `basis` resolves it toward the partner; the count is what
    # says how often that mattered.
    overlap = sum(1 for row in one_way if row.decomposed and verdict_of[row.edge] == UNCROSSED)
    lines.append(f"  rows both decomposed and uncrossed — the two bases disagree: {overlap}")

    lines.append("")
    lines.append("published CARRIAGEWAY WIDTH by basis — ⚠️ not one population, see the code")
    lines.append(
        f"  {'basis':<20} {'n':>5} {'p50':>7} {'p90':>7} {'< ' + format(bounds.min_m, '.1f'):>8}"
    )
    # ⚠️ **Grouped over EVERY row with a median, not over the span-published
    # ones.** A decomposed half answers to the dual column and not to the span's
    # own ceiling, so two FLEMING ROAD rows are licensed here while their 16.56 m
    # span is refused above. Filtering to `with_median` first would drop them and
    # make this table disagree with `_render_pairs` about the same 14 rows.
    # ⚠️ One pass, and the basis is asked for ONCE per row. Three passes calling
    # `basis` again per name would let a row answer differently in two of them if
    # the rule ever stopped being a pure function of the row and the bounds —
    # `_sides` is single-called two hundred lines above for the same reason,
    # so that two readings "cannot disagree about what was hit".
    grouped: dict[str, list[EdgeWidth]] = defaultdict(list)
    for row in rows:
        grouped[row.basis(bounds)].append(row)

    published: list[tuple[int, float]] = []
    for name in _BASES:
        group = grouped.get(name, [])
        if not group:
            lines.append(f"  {name:<20} {0:>5}")
            continue
        widths = [row.carriageway_m(bounds) for row in group]
        published.extend((row.edge, width) for row, width in zip(group, widths, strict=True))
        p50, p90 = _percentiles(widths, (50, 90))
        lines.append(
            f"  {name:<20} {len(group):>5} {p50:>7.2f} {p90:>7.2f} "
            f"{_share_under(widths, bounds.min_m):>7.1%}"
        )
    lines.append(
        f"  {'-- licensed':<20} {len(published):>5} of {len(rows)} edges with a median; "
        f"{len(rows) - len(published)} carry a reading this cannot attribute"
    )
    if published:
        lines.append(_authored_gap(published, report, "  "))
    return lines


def write_widths(
    rows: list[EdgeWidth], report: Report, bounds: WidthBounds, destination: Path
) -> int:
    """The per-edge rows as JSON, for the decision this tool cannot make.

    ⚠️ **`etl/out/` is gitignored**, so this is a local artefact exactly as
    `facade_lab.json` is — re-running the tool is the only way back, and no build
    reads it. It exists because the assignment that follows needs a machine
    readable answer, and pasting a table into a decision record is not one.

    ⚠️ **Every row, decomposed or not, with the flags that say which.** Writing
    only the readable rows would hand the next reader a file in which the
    refusals never happened.

    🔴 **Every float goes through `_number` and `allow_nan` is off.** A NaN is
    reachable on more fields than the obviously-optional ones — `off_centre` is
    NaN on a zero-width span, and a median over a list holding one is NaN too —
    and `json.dumps` writes it as a bare `NaN` token that Python reads back and
    every strict parser rejects. A file promising a machine-readable answer may
    not be one Python alone can read; `allow_nan=False` is what makes a field
    added later raise here rather than ship broken.
    """

    def _number(value: float) -> float | None:
        return None if math.isnan(value) else round(value, 3)

    payload = [
        {
            "edge": row.edge,
            "road": report.names.get(row.edge, ""),
            "direction": report.directions.get(row.edge, ""),
            "n": row.n,
            "span_m": _number(row.median_m),
            "own_m": _number(row.own_m),
            # ⚠️ **`carriageway_m` is null on most rows and that is the point of
            # the file.** A reader that wants only the attributable widths
            # filters on it; one that wants to know what was refused, and on
            # which of the three verdicts, has `crossing` and `beyond_m` beside
            # it. Writing only the licensed rows would hand the next reader a
            # survey in which nothing was declined.
            "beyond_m": _number(row.beyond_m),
            "crossing": row.crossing(bounds),
            "basis": row.basis(bounds),
            "carriageway_m": _number(row.carriageway_m(bounds)),
            "off_centre": _number(row.off_centre),
            "partner": row.partner,
            "candidate": row.candidate,
            "median_gap_m": _number(row.median_gap_m),
            "span_disagreement_m": _number(row.span_disagreement_m),
            "span_refused": row.refused,
            "own_refused": row.own_refused,
            "decomposed": row.decomposed,
            # ⚠️ Was `lanes_authored`, and the name stopped being true at
            # schema 6 — part of the region carries a measured count now, so
            # the source rides beside it (`Q94`).
            "lanes_published": report.lanes.get(row.edge),
            "lanes_source": report.lanes_source.get(row.edge, "authored"),
            "width_m_authored": report.widths_authored.get(row.edge),
            "source": row.source,
        }
        for row in rows
    ]
    destination.write_text(json.dumps(payload, indent=1, sort_keys=True, allow_nan=False))
    return len(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--spacing-m", type=float, default=4.0, help="station spacing along an edge"
    )
    parser.add_argument(
        "--max-ray-m",
        type=float,
        default=15.0,
        # A cap rather than unbounded, because an uncapped perpendicular finds
        # *something* eventually and calls it a kerb. Swept in the report a
        # reader pastes, per `Q51`'s lesson about a headline that turns out to
        # be a function of one constant.
        help="how far a perpendicular may travel before the station is unmeasurable",
    )
    parser.add_argument(
        "--junction-m",
        type=float,
        default=12.0,
        help="stations this close to a graph node are reported separately (see the docstring)",
    )
    parser.add_argument(
        "--max-width-m",
        type=float,
        # Defaults to the city's own `width_bounds.max_m`. A flag as well as a
        # config value because the counter has to be shown reachable at zero —
        # a ceiling nothing can move is not measuring anything (`Q72`).
        help="override the city's carriageway ceiling; above it a ray has crossed something",
    )
    parser.add_argument(
        "--pair-bearing-deg",
        type=float,
        # 🔴 The pairing rule's only free value, so it gets a flag for the reason
        # `--max-width-m` has one: it must be swept from the command line rather
        # than by editing the city file in a shell loop. `skidpad.sh` grew its
        # `--sweep` after exactly that loop blanked the field it was sweeping and
        # published a table of all-zero rows that read like a finding.
        help="override how far off anti-parallel two centrelines may run and still pair",
    )
    parser.add_argument(
        "--dual-min-m",
        type=float,
        # 🔴 The crossing rule's lower bracket gets a flag for `--max-width-m`'s
        # reason: a counter that classifies has to be shown reachable at BOTH
        # ends, and the only honest way to show it is from the command line
        # (`Q72`). Lowered to `hard_min_m` nothing is uncrossed; raised to
        # `dual_max_m` nothing is crossed.
        help="override the narrowest opposed carriageway; below it a span never crossed a median",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="also write the per-edge rows to carriageway_width.json under the region's out dir",
    )
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--out-root", type=Path, help="override etl/out")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    survey_spec = city.carriageway_survey
    bounds = survey_spec.width_bounds if survey_spec is not None else None
    if args.max_width_m is not None:
        if bounds is None:
            # Everywhere else this tool is loud about a configuration it cannot
            # measure. Accepting an override for a section it will not print
            # would be the one quiet failure in it.
            raise SystemExit(
                f"--max-width-m has nothing to override: city '{city.id}' declares no "
                "carriageway_survey.width_bounds, so no span is graded."
            )
        bounds = replace(bounds, max_m=args.max_width_m)
        if not bounds.hard_min_m < bounds.dual_max_m < bounds.max_m:
            # `_width_bounds` enforces this ordering and `replace` goes round it.
            # Left unchecked, `--max-width-m 10` keeps `dual_max_m` at 14.6 and
            # the half of a pair is then bounded *looser* than the span that
            # contains it — which retires the whole reason for reading TD's dual
            # column instead of the single one.
            raise SystemExit(
                f"--max-width-m {args.max_width_m} leaves dual_max_m {bounds.dual_max_m} outside "
                f"(hard_min_m {bounds.hard_min_m}, max_m {args.max_width_m}) — a carriageway of a "
                "pair would be bounded looser than the span it sits in."
            )
    if args.json and bounds is None:
        # Up here with the other two rather than beside the write, so a city with
        # no bounds fails before the region is walked instead of after the whole
        # report has printed.
        raise SystemExit(
            f"--json has nothing to write: city '{city.id}' declares no "
            "carriageway_survey.width_bounds, so there are no per-edge rows."
        )
    if args.pair_bearing_deg is not None:
        if bounds is None:
            raise SystemExit(
                f"--pair-bearing-deg has nothing to override: city '{city.id}' declares no "
                "carriageway_survey.width_bounds, so no span is split."
            )
        if not 0.0 < args.pair_bearing_deg < 90.0:
            # The config guard, repeated because an override goes round it. At 90
            # a perpendicular side street reads as an opposed carriageway, which
            # is the match the bar exists to refuse; at or below 0 nothing pairs
            # and the sweep would report an empty table as a finding.
            raise SystemExit(
                f"--pair-bearing-deg {args.pair_bearing_deg} must lie in (0, 90): at 90 a "
                "perpendicular centreline reads as an opposed carriageway, and at 0 nothing "
                "pairs and the sweep reports an empty table as a finding."
            )
        bounds = replace(bounds, pair_bearing_tolerance_deg=args.pair_bearing_deg)
    if args.dual_min_m is not None:
        if bounds is None:
            raise SystemExit(
                f"--dual-min-m has nothing to override: city '{city.id}' declares no "
                "carriageway_survey.width_bounds, so no span is classified."
            )
        # The config guard, repeated because `replace` goes round it — the same
        # move `--max-width-m` makes. ⚠️ Inclusive at both ends here, unlike the
        # config's strict ordering: sweeping TO a collapsed band is exactly how
        # the three states are shown reachable, and refusing the endpoints would
        # make the mutation check the tool asks for impossible to run.
        if not bounds.hard_min_m <= args.dual_min_m <= bounds.dual_max_m:
            raise SystemExit(
                f"--dual-min-m {args.dual_min_m} must lie within "
                f"[{bounds.hard_min_m}, {bounds.dual_max_m}] — below the floor no span could "
                "cross a median, and above the dual ceiling the narrowest carriageway of a pair "
                "would be wider than the widest."
            )
        bounds = replace(bounds, dual_min_m=args.dual_min_m)
    if bounds is not None and 2.0 * args.max_ray_m <= bounds.max_m:
        # 🔴 The `drawn_gauge_m` trap, reachable from the command line. Two rays
        # capped at `max_ray_m` cannot sum past twice it, so a small enough cap
        # makes the ceiling unreachable and the report announces a clean sweep
        # that the cap manufactured rather than the city earned.
        raise SystemExit(
            f"--max-ray-m {args.max_ray_m:.1f} caps a span at {2 * args.max_ray_m:.1f} m, which "
            f"cannot reach the {bounds.max_m:.1f} m ceiling — every span would be kept by "
            "construction. Raise the ray or lower the ceiling."
        )
    report = survey(
        city,
        args.region,
        spacing_m=args.spacing_m,
        max_ray_m=args.max_ray_m,
        junction_m=args.junction_m,
        sources_root=args.sources_root,
        out_root=args.out_root,
    )
    if not report.stations:
        raise SystemExit(
            "no station could be measured — is the region built and are the sources fetched?"
        )
    # ⚠️ Computed once and handed to both readers. Printing one table and
    # writing another from a second call would let the two drift — `_candidate`
    # and `_dominant` both break ties on `Counter` insertion order, so agreement
    # today is a property of the input rather than of the code.
    rows = edge_widths(report, bounds) if bounds is not None else None
    print(
        render(
            report,
            spacing_m=args.spacing_m,
            max_ray_m=args.max_ray_m,
            junction_m=args.junction_m,
            bounds=bounds,
            rows=rows,
        )
    )
    if args.json and rows is not None:
        destination = city.out_dir(args.region, args.out_root) / "carriageway_width.json"
        log.info(
            "%d edge rows -> %s (gitignored; re-run to rebuild)",
            write_widths(rows, report, bounds, destination),
            destination,
        )
    # Grades, never checks. See the docstring, and CLAUDE.md's rule for the
    # sibling this follows.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
