"""Where the drawn ground stands in the drawn carriageway (`P3-10`, `Q18`).

The third sibling of `deck_error.py` and `overhang.py`, and the one that sizes
`buildings.ground_sink_m`. `deck_error` asks how far an elevated road is from the
deck under it; `overhang` asks whether there is a deck under it at all; this asks
the at-grade question the other two never reach — **is the ground where the road
is?**

It exists because the ground and the level-0 carriageway are coplanar *by
construction*. `roads.py` samples the terrain and lays the ribbon at `terrain +
0.0`, so drawing that same terrain puts two surfaces at the same height along
every street in the region. `ground_sink_m` drops the ground under the kerb's
0.15 m riser and 0.5 m lip; how far it has to drop is what this measures.

**Sinking by the nominal amount is not the same as clearing the road, and the
gap between them is the whole reason for a separate tool.** `P2-1` decimates the
terrain on a 4 m cell and `collapse` moves every vertex to its cluster mean, so
the ground that *ships* is not the ground `roads.py` sampled. `P2-7` met the same
shape at a tenth the cell size — 0.5 m decimation lifted the shipped flyover deck
a median +0.041 m and a **max +0.339 m** — and sized `deck.clearance_m` by
measuring what still poked through rather than by choosing a number. This is that
measurement for the ground.

Two things go wrong when it pokes through, and the second is the expensive one:

- **It is visible.** Ground standing above asphalt reads as the road being
  drawn *into* the pavement. `Q18` asks whether flat ground reads as ground at
  all, and it cannot be judged over a surface fighting the road.
- **It is solid.** Since `P3-10` the ground merges into the tier-0 mesh, which
  is named `-col`, so every lump of it collides. `handling.tres` allows
  `suspension_travel_m = 0.18`, and `P1-4` has already shown once what a 0.15 m
  step in the carriageway does to a car at speed — that was a kerb in lane
  three, and it threw the car. A decimation artefact standing proud of the road
  is the same defect with no kerb to blame.

Nothing here is shared with the code it grades — same argument as
`deck_error.py`'s docstring, same table. The ground comes from the **shipped
tiles**, found by vertex colour rather than by sheet sub-directory, and the road
from the **shipped `roads.glb`** rather than from the graph the ETL wrote.

⚠️ **Level 0 only.** An elevated carriageway is *supposed* to stand above the
ground, so measuring one would report the height of every flyover as a defect.
Level -1 is under the terrain by definition (`Q21`).

## The second class, and why it is not a second copy of the first

🔴 **Structure is measured here too, and the two are never pooled.** `Q19`
prescribed a vertical bar inside the carriageway, `P3-29` built it and withdrew
it, and what that left is a **blind band**: `carriageway_occupancy` and
`clearance` read `INFRASTRUCTURE` but their bumper band starts at
`BUMPER_LOW_M` **0.30 m** — `Q23`, so an abutment the road rests on does not read
as an obstruction — while this tool uses the car's own **0.18 m** and read
`terrain_class` and nothing else. A structure step between the two was seen by
no committed instrument, which is how a car came to stop on `e99` FLEMING ROAD
at a 0.356 m ledge with every bar in the bundle green.

⚠️ **Ground proud and structure proud want OPPOSITE fixes, so they get separate
tables and share no number** (`Q57`). Ground standing over the road is the sink
and the cross-slope, and belongs to `Q24`. Structure standing over it is a wall
inside the drawn carriageway, and belongs to `Q19`.

🔴 **The terrain rule cannot be reused, and that is measured rather than
asserted.** `ground_above` takes the *nearest* terrain height within a
symmetric 3 m window, which is right because terrain is single-valued wherever a
car can be. Structure is a volume in a stack: `Faces.from_tiles` keeps
upward-wound faces, so a flyover's **deck top** is a candidate for the street
running underneath it. Read the same way, the Wan Chai interchange reports as
structure standing **+13.27 m proud** of GLOUCESTER ROAD, on 210 of 737 edges
and 30,352 m² of ribbon. So `structure_above` takes the **lowest face strictly
above the road** instead, and everything past the window is refused.

⚠️ **The bounds are imported from `pipeline.clearance`, not chosen here.** The
band this exists to close is `[SUSPENSION_TRAVEL_M, BUMPER_LOW_M]` and the
refusal window is `BUMPER_HIGH_M`, so if the other instrument's band moves, the
gap this reports moves with it. That is a shared *bound*, never a shared method
— nothing about how either surface is read is imported, and the argument in
`deck_error.py`'s docstring is untouched.

⚠️ **Absence is the normal answer here and is NOT a coverage miss.** 92.5% of
this region's level-0 carriageway has no structure under it at all. Reusing
`--accept-coverage` on that population would fail the tool on a fact, which is
`paint_clearance.py`'s reason for not gating the tram rails.

🔴 **The structure half GRADES and does not gate**, and it says so where the
gates are. `--accept-edges-over-travel` already carries an apology for being a
bar tuned to its own first reading (`Q47`); a second one set the same way, on a
population `Q19` has not decided how to fix, would be that mistake made
knowingly. The exit code stays the ground half's.

Run:  .venv/bin/python tools/ground_clearance.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    class_faces,
    drawn_surface,
    load_bundle,
    log_bundle,
    nearest,
    structure_faces,
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

# The band the other instrument cannot see, taken from the instrument itself
# rather than mirrored — see the module docstring. A *bound*, not a method: no
# part of how `clearance.py` reads a cross-section arrives with it.
from pipeline.clearance import BUMPER_HIGH_M, BUMPER_LOW_M  # noqa: E402
from pipeline.config import load_config  # noqa: E402

log = logging.getLogger(__name__)

# `handling.tres`'s `suspension_travel_m`, mirrored rather than read: this is a
# hand-run Python tool and the `.tres` is Godot's. Quoted in the report because
# it is what turns a drawing defect into a handling one, and it is the number
# `P1-4`'s kerb was judged against.
SUSPENSION_TRAVEL_M = 0.18


@dataclass
class EdgeCells:
    """One level-0 edge's drawn ribbon, in area, split by where across it a cell sat.

    🔴 **Per edge, because the region share cannot see a fix to this and never
    could.** `carriageway_occupancy.py` states the argument and it applies here
    unchanged — `RoadGraph` routes on edges, and a player drives one street
    rather than an average. Measured: correcting the region's most cross-sloped
    edge moves its own proud share from 12.2% to 3.5% and the region headline by
    **0.06pp**, because 723 of 737 edges need nothing. A grader that reports only
    the second number would score that fix as noise.

    ⚠️ **The split is inside-authored versus in-the-rim, and it is the number
    that separates the two candidate fixes.** A defect confined to the rim is
    the 1.6x widening (`Q19`); one that reaches the authored carriageway is not,
    and no narrowing would clear it.

    🔴 **The rule is `abs(offset) <= width_m / 2` and it lives HERE, in the class
    that documents it** — not in the caller. `carriageway_occupancy.py:723`
    reaches the same reading of "authored" independently and **nothing is shared
    between them**, so the two tools *can* drift; saying otherwise would be a
    guarantee this file cannot make. Two copies is where `mesh_contract.gd`'s
    rule puts the trigger for a third one to force a helper. What the placement
    does buy is a rule a unit test can reach: applied in `survey`'s loop it was
    only reachable from a whole shipped bundle, so the swap this split exists to
    prevent was exactly the swap the tests could not catch.

    ⚠️ **`over_m2` counts against `SUSPENSION_TRAVEL_M`, not against
    `--accept-proud-m`.** The region gates ask whether the ground is above the
    road at all; this asks whether it would throw the car, which is
    `handling.tres`'s number and not one this tool chose.

    ⚠️ **The totals are derived, never stored.** `area_m2` and `over_m2` are the
    two buckets summed, so a build that gained a third bucket cannot leave the
    total disagreeing with its parts.
    """

    name: str = ""
    authored_width_m: float = 0.0
    worst_m: float = -np.inf
    inside_m2: float = 0.0
    inside_over_m2: float = 0.0
    rim_m2: float = 0.0
    rim_over_m2: float = 0.0
    # Cells refused because the terrain over them stands further above the road
    # than `--ground-within-m`, which is what makes `worst_m` a lower bound
    # rather than a measurement. See `Survey.above_window_m`.
    above_window: int = 0
    above_window_max_m: float = 0.0

    def is_inside(self, offset_m: float) -> bool:
        """Whether a cell that far across the ribbon is on the authored carriageway."""
        return abs(offset_m) <= 0.5 * self.authored_width_m

    @property
    def area_m2(self) -> float:
        return self.inside_m2 + self.rim_m2

    @property
    def over_m2(self) -> float:
        return self.inside_over_m2 + self.rim_over_m2

    @property
    def over_share(self) -> float:
        return self.over_m2 / self.area_m2 if self.area_m2 else 0.0

    @property
    def inside_over_share(self) -> float:
        return self.inside_over_m2 / self.inside_m2 if self.inside_m2 else 0.0

    @property
    def rim_over_share(self) -> float:
        return self.rim_over_m2 / self.rim_m2 if self.rim_m2 else 0.0


@dataclass
class Survey:
    """Every level-0 carriageway cell, and what the ground does at it.

    ⚠️ **`asked` and the misses are counted, not merely skipped**, and that is
    `deck_error`'s hardest-won lesson rather than bookkeeping. Its fourth defect
    left unmeasurable stations out of the denominator: breaking a third of the
    carriageway made the broken third stop being measured, every ratio improved,
    and the tool exited 0. A cell this cannot measure has to be visible in the
    output or the denominator is chosen by the defect.

    The two misses mean different things and are kept apart:

    - `no_road` — nothing drawn at that plan position within the attribution
      window. Junction trims and the cap's own height do this, and it is not
      evidence about the ground either way.
    - `no_ground` — road drawn, but no terrain face found under it. On a region
      whose terrain covers it end to end this should be a rounding error; a
      large one means the ground is not shipping, which is the failure that
      would otherwise look like a clean pass.

    ⚠️ **The rule binds the sampled points too, and that is the half worth
    saying out loud** — they carry the gate that grades the sink, so they are
    exactly where a shrinking denominator would do most damage. Hence
    `sampled_asked` beside `sampled_m` rather than a bare list appended to on
    success: a build that stopped shipping ground under half the region would
    otherwise drop those points silently and *improve* the number they gate.
    """

    proud_m: list[float] = field(default_factory=list)
    area_m2: list[float] = field(default_factory=list)
    # The same measurement taken only where the road's height was *sampled* from
    # the terrain — on the centreline, at a retained polyline vertex. One value
    # per such point rather than per cell, because it is one point. This is the
    # population the sink alone controls; see `main`.
    sampled_m: list[float] = field(default_factory=list)
    sampled_asked: int = 0
    asked: int = 0
    no_road: int = 0
    # Every level-0 edge's own ribbon, for naming where to go and look and for
    # the per-edge gate. Supersedes the bare worst-cell map this used to hold:
    # one source of truth, so the listing and the gate cannot drift apart.
    edges: dict[int, EdgeCells] = field(default_factory=dict)
    # 🔴 **The window's two rejections are opposite findings and used to be one
    # counter.** `no_ground` read 3,096 on the shipped region; 2,276 of those are
    # road drawn over nothing, and **121 are terrain standing 3.00-7.65 m above
    # the carriageway** — the deepest burials in the region, dropped out of the
    # numerator and reported as a coverage miss. That is `deck_error.py`'s fourth
    # defect inverted: there the denominator shrank when things broke, here the
    # worst cells leave the top. The window itself is right and stays (a cutting
    # face several metres away is not the ground under the road beside it), so
    # the fix is to publish the overflow rather than to widen it — which also
    # makes every `worst_m` below an honest lower bound.
    below_window: int = 0
    no_terrain: int = 0
    above_window_m: list[float] = field(default_factory=list)

    @property
    def above_window(self) -> int:
        return len(self.above_window_m)

    @property
    def no_ground(self) -> int:
        """Road drawn, no terrain attributed — the two rejections above, summed.

        Derived rather than counted alongside them, so the coverage line and the
        split beneath it cannot report different totals for the same cells.
        """
        # Three causes, not two — see `Probe`.
        return self.above_window + self.below_window + self.no_terrain

    @property
    def measured(self) -> int:
        return len(self.proud_m)

    @property
    def coverage(self) -> float:
        return self.measured / self.asked if self.asked else 0.0

    @property
    def sampled_coverage(self) -> float:
        return len(self.sampled_m) / self.sampled_asked if self.sampled_asked else 0.0

    def begin(self, edge_id: int, name: str, authored_width_m: float) -> EdgeCells:
        """The record for one edge, created on first sight.

        Separate from `add` because an edge that is walked and never measured
        still has to appear — an edge whose ribbon this tool could not read is a
        finding, and one that silently never enters the map is the shrinking
        denominator the class docstring is about. `main` reports the difference
        between this map and the measured subset for that reason.

        ⚠️ **`add` requires it, and that is deliberate rather than defensive.**
        The inside/rim split is a rule about the authored width, which arrives
        here; a record reached without it would have width 0 and book every cell
        as rim — a silently mis-split edge, which is worse than a `KeyError`.
        """
        edge = self.edges.setdefault(edge_id, EdgeCells())
        edge.name = name
        edge.authored_width_m = authored_width_m
        return edge

    def add(self, edge_id: int, proud_m: float, area_m2: float, *, offset_m: float) -> None:
        """One measured cell, booked to the edge `begin` has already announced.

        Takes the offset rather than a decided `inside` flag so the rule stays in
        `EdgeCells`, where it is documented and where a test can reach it.
        """
        self.proud_m.append(proud_m)
        self.area_m2.append(area_m2)
        edge = self.edges[edge_id]
        edge.worst_m = max(edge.worst_m, proud_m)
        if edge.is_inside(offset_m):
            edge.inside_m2 += area_m2
            if proud_m > SUSPENSION_TRAVEL_M:
                edge.inside_over_m2 += area_m2
        else:
            edge.rim_m2 += area_m2
            if proud_m > SUSPENSION_TRAVEL_M:
                edge.rim_over_m2 += area_m2

    def add_sampled(self, proud_m: float | None) -> None:
        """One centreline point, measured or not. `None` still counts as asked."""
        self.sampled_asked += 1
        if proud_m is not None:
            self.sampled_m.append(proud_m)

    def area_share_above(self, threshold_m: float) -> float:
        """Share of measured carriageway **area** with ground this far proud.

        By area rather than by cell count, for `overhang`'s reason: a cell of a
        single-lane ramp and a cell of a six-lane arterial are not the same
        amount of road, and counting them equally would let the widest streets —
        the ones a player is most often on — count least.

        Named for its weighting rather than left as the bare `share_above`,
        because the pair it forms with `sampled_share_above` weighs differently
        on purpose and confusing the two is the mistake this whole tool exists
        to prevent.
        """
        if not self.proud_m:
            return 0.0
        proud, area = np.asarray(self.proud_m), np.asarray(self.area_m2)
        return float(area[proud > threshold_m].sum() / area.sum())

    def sampled_share_above(self, threshold_m: float) -> float:
        """The same, over the points where the road's height came from the terrain.

        By count rather than by area, because each is one sampled point rather
        than a piece of surface — weighting them by the width of the road they
        happen to sit on would measure the streets, not the sampling.
        """
        if not self.sampled_m:
            return 0.0
        return float((np.asarray(self.sampled_m) > threshold_m).mean())


@dataclass
class StructureEdge:
    """One level-0 edge's ribbon, and what structure stands over it.

    🔴 **Not `EdgeCells` with more fields, and the separation is the point.**
    `Q57` is what pooling two populations into one number costs, and these two
    want opposite repairs: ground proud of the road is the sink and the flat
    cross-section (`Q24`), structure proud of it is a wall inside the drawn
    carriageway (`Q19`). One column able to hold either would be read as one
    quantity by the next person to open the table.

    ⚠️ **`ribbon_m2` counts every cell with a ROAD drawn, not every cell with
    structure found**, and that is the difference between a share and a
    tautology. Structure is absent under 92.5% of this region's level-0
    carriageway; a denominator taken over the cells that found some would read
    100% on an edge carrying a single ledge and nothing else.

    ⚠️ **`band_m2` and `over_bumper_m2` are separate because only the first is
    NEW information.** Anything past `BUMPER_LOW_M` is already inside
    `carriageway_occupancy`'s reach and already counted there; the band beneath
    it is what no committed tool could see. Summing them would republish
    `Q19`'s population as though it were this one's finding.
    """

    name: str = ""
    ribbon_m2: float = 0.0
    band_m2: float = 0.0
    over_bumper_m2: float = 0.0
    worst_m: float = -np.inf
    # Stations carrying at least one measurable cell, and those carrying at
    # least one step. The pair is `Q19`'s discriminator arriving in a committed
    # tool: a ledge occupies a strip of a cross-section and a ribbon disagreeing
    # with the deck it rests on occupies most of one.
    stations: int = 0
    stepped_stations: int = 0
    worst_section_share: float = 0.0
    # Cells whose lowest face above the road sat past the window — a flyover
    # overhead, refused. Published rather than dropped, for `Survey`'s reason:
    # a refusal nobody can see is a denominator chosen by the geometry.
    overhead: int = 0
    overhead_min_m: float = np.inf

    @property
    def band_share(self) -> float:
        """Band area over the edge's whole ribbon — what makes two streets comparable.

        ⚠️ A raw m² is not comparable across edges, which is the argument
        `EdgeCells` makes for its own shares: 19.3 m² on `e168`'s ten stations
        and 70.2 m² on `e402`'s fifty-five are not the same amount of street.
        Printed for that reason rather than kept for a caller that might want
        it — the review that found three write-only members here is why the
        distinction is worth stating.
        """
        return self.band_m2 / self.ribbon_m2 if self.ribbon_m2 else 0.0


@dataclass
class Structure:
    """Every level-0 carriageway cell, asked what structure stands over it.

    ⚠️ **The four outcomes are counted, never skipped**, which is `Survey`'s
    rule and `deck_error`'s fourth defect behind it — but the meanings differ
    and reading them as `Survey`'s would be wrong in the flattering direction:

    - `measured` — a face above the road, inside the window. The population.
    - `absent` — no structure at this plan position at all. 🔴 **The normal
      answer, not a miss.** Gating a coverage share over it would fail the tool
      on a fact, which is why there is deliberately no `--accept-coverage` here.
    - `resting` — structure found, all of it at or below the road. The deck the
      ribbon sits on, which is geometry working.
    - `overhead` — a face above the road but past the window: a flyover deck
      over a street, not a step in it. Refused *and published*, so every
      `worst_m` below is an honest lower bound.

    🔴 **The identity is asserted at run time**, not asserted in a comment:
    `on_road == measured + absent + resting + overhead`. A fifth outcome added
    without a counter would otherwise leave every share divided by a number
    that no longer describes its own parts.
    """

    rise_m: list[float] = field(default_factory=list)
    area_m2: list[float] = field(default_factory=list)
    # Which edge each measured cell came from, so the per-band edge counts below
    # are taken from the same pass as the cells they count. Held beside the
    # measurement rather than derived from the per-edge records, which keep only
    # the two coarse buckets an edge is listed by.
    edge_of: list[int] = field(default_factory=list)
    # One value per station that carries at least one step — `Q19`'s conditioning,
    # kept so the two are comparable. ⚠️ The denominator is every cell of the
    # section with a road drawn, NOT the cells that found structure; taken the
    # second way a scratch run of this read p50 0.83 where `Q19` reads 0.10,
    # because a thin ledge is most of the structure in its own section and
    # almost none of the road.
    section_share: list[float] = field(default_factory=list)
    overhead_m: list[float] = field(default_factory=list)
    on_road: int = 0
    absent: int = 0
    resting: int = 0
    edges: dict[int, StructureEdge] = field(default_factory=dict)

    @property
    def measured(self) -> int:
        return len(self.rise_m)

    @property
    def overhead(self) -> int:
        """The list IS the counter, so the two cannot report different totals."""
        return len(self.overhead_m)

    def check(self) -> None:
        """The partition, at run time. See the class docstring."""
        parts = self.measured + self.absent + self.resting + self.overhead
        if parts != self.on_road:
            raise AssertionError(
                f"structure outcomes do not partition the road-drawn cells: "
                f"{parts} against {self.on_road}"
            )

    def begin(self, edge_id: int, name: str) -> StructureEdge:
        """The record for one edge, created on first sight — `Survey.begin`'s rule.

        An edge walked and never stepped on still has to appear, or the count of
        edges carrying nothing is the count of edges this happened to look at.
        """
        edge = self.edges.setdefault(edge_id, StructureEdge())
        edge.name = name
        return edge

    def saw_road_cell(self, edge_id: int, area_m2: float) -> None:
        """One cell of ribbon with a road drawn under it — the population to partition.

        Separate from `observe` because it is a different fact: this is what was
        *asked*, and the four outcomes are what came back. Booked through a
        method rather than by the caller so `check` compares two things this
        class counts, instead of comparing the caller against itself.
        """
        self.on_road += 1
        self.edges[edge_id].ribbon_m2 += area_m2

    def observe(self, edge_id: int, step: Step, area_m2: float) -> bool:
        """Book one cell's structure outcome, and say whether it is a step.

        🔴 **The decode lives here and not in `survey`'s loop, which is what
        makes `check` mean anything.** With the caller incrementing `on_road`
        and three of the four buckets by hand, the identity was the caller
        checked against itself and no test could reach the decode at all — which
        is exactly how two write-only per-edge counters survived review.

        Returns whether the cell is a step past the car's travel, so the
        threshold stays in this class with the others rather than being applied
        a second time at the call site.
        """
        edge = self.edges[edge_id]
        if step.rise_m is not None:
            self.add(edge_id, step.rise_m, area_m2)
            return step.rise_m > SUSPENSION_TRAVEL_M
        if step.overhead_m is not None:
            # The list IS the region counter — `Structure.overhead` reads its
            # length — and the per-edge pair beside it is what makes an edge's
            # `worst_m` an honest bound in the table rather than only in the
            # region row.
            self.overhead_m.append(step.overhead_m)
            edge.overhead += 1
            edge.overhead_min_m = min(edge.overhead_min_m, step.overhead_m)
        elif step.has_structure:
            self.resting += 1
        else:
            self.absent += 1
        return False

    def add(self, edge_id: int, rise_m: float, area_m2: float) -> None:
        """One cell with structure above the road, inside the window.

        ⚠️ Takes the rise rather than a decided band, so the two thresholds stay
        here — where they are documented, and where a test can reach them
        without a shipped bundle.
        """
        self.rise_m.append(rise_m)
        self.area_m2.append(area_m2)
        self.edge_of.append(edge_id)
        edge = self.edges[edge_id]
        edge.worst_m = max(edge.worst_m, rise_m)
        if rise_m > BUMPER_LOW_M:
            edge.over_bumper_m2 += area_m2
        elif rise_m > SUSPENSION_TRAVEL_M:
            edge.band_m2 += area_m2

    def add_section(self, edge_id: int, stepped: int, cells: int) -> None:
        """One cross-section: how much of it was measurable, and how much stepped.

        ⚠️ **Two bookings, and the order matters.** A section with any
        measurable cell counts toward the edge's `stations` whether or not it is
        stepped — that is the denominator of the `stepped/stations` column —
        while the *share* is recorded only where a step was found, which is
        `Q19`'s conditioning: the question is what shape a defect takes, and a
        clean section has no shape. Pooling the two returns would drive every
        percentile to zero and make the two failure modes indistinguishable.
        """
        if not cells:
            return
        edge = self.edges[edge_id]
        edge.stations += 1
        if not stepped:
            return
        share = stepped / cells
        self.section_share.append(share)
        edge.stepped_stations += 1
        edge.worst_section_share = max(edge.worst_section_share, share)

    def band_area(self) -> float:
        """The band's total area, from `cells_in` and never from the per-edge buckets.

        🔴 **Two paths reach this number and only one may print it.** `add`
        buckets a rise per edge and `cells_in` masks the flat list; they agree
        today, and summing the buckets here put both readings in one report
        where a changed comparison would make two lines disagree with nothing to
        catch it. The per-edge buckets still feed the table, so a divergence
        shows up as the table disagreeing with this row — visible, rather than
        two totals quietly describing different bands.
        """
        return self.cells_in(SUSPENSION_TRAVEL_M, BUMPER_LOW_M)[1]

    def ribbon_area(self) -> float:
        return sum(edge.ribbon_m2 for edge in self.edges.values())

    def cells_in(self, low_m: float, high_m: float) -> tuple[int, float, int]:
        """Cells, area and distinct edges with a rise in `(low, high]`.

        Over the flat lists rather than the per-edge records, because the bands
        reported are finer than the two coarse buckets an edge keeps — and the
        edge count has to come from the same pass as the cells or the two can
        disagree about the same band.
        """
        if not self.rise_m:
            return 0, 0.0, 0
        rise = np.asarray(self.rise_m)
        within = (rise > low_m) & (rise <= high_m)
        area = np.asarray(self.area_m2)[within]
        edges = {edge_id for edge_id, keep in zip(self.edge_of, within, strict=True) if keep}
        return int(within.sum()), float(area.sum()), len(edges)


def optional_structure_faces(city: Any, tiles: list[Path]) -> tuple[Faces, str | None]:
    """Upward-facing structure, or an empty index where the region ships none.

    🔴 **The structure half may not decide this tool's exit code, and calling
    `structure_faces` directly let it.** That function raises `SystemExit`
    twice — for a city declaring no `structure_class`, and for a region whose
    tiles carry none of it — and both are reachable: `Q6`/`Q10` keep multi-region
    support, and a region with no flyover is an ordinary region, not a broken
    build. Either would have aborted before the **ground** gate ran, which is
    the one thing this tool is not allowed to skip.

    ⚠️ Deliberately unlike `ground_faces` beside it, which *does* exit: the
    ground is named by every city and a region shipping none is a defect. An
    empty index here books every cell as `absent`, which is already the
    documented normal answer for 92.8% of them.
    """
    try:
        return structure_faces(city, tiles)
    except SystemExit as absent:
        log.warning("  no structure to measure — the ground half still grades: %s", absent)
        return Faces.of(np.zeros((0, 3, 3)), signed=True), None


def ground_faces(city: Any, tiles: list[Path]) -> tuple[Faces, str]:
    """Upward-facing terrain across the shipped tiles, and the class it came from.

    The sibling of `deck_error.structure_faces`: both answer "which class, and is
    it identifiable in a merged tile", and both hand the rest to `class_faces`.
    Only the precondition differs, and it is the interesting half — structure is
    optional because a city may declare no deck sampling, whereas ground is
    *named* by every city and merely may not be drawn.
    """
    terrain_class = city.buildings.terrain_class
    if terrain_class not in city.buildings.classes:
        raise SystemExit(
            f"city '{city.id}' does not tile '{terrain_class}', so no ground ships to measure. "
            f"Add it to buildings.classes."
        )
    return class_faces(city, tiles, terrain_class), terrain_class


class Probe(NamedTuple):
    """What terrain one plan position had under it, named rather than positional.

    ⚠️ **Three values because a miss has three causes, and they are not the same
    finding.** Terrain refused for standing *above* the window is a burial this
    tool declines to measure; terrain below it is a road drawn metres over the
    ground; no terrain at all is a hole in the tiles. Returned as one tuple of
    bare values, the caller decoded them across nested `if`s and the last two
    were reported as one number — which is the conflation `Survey.no_ground` was
    split up to end, arriving one level down.

    ⚠️ **`on_road` used to be a fourth field and has moved to `road_height`**,
    which is now the one place that decides it. It was here because a single
    closure did both lookups; with the road height wanted by two readers it is
    asked once, and a flag restating the caller's own branch is a second copy of
    a fact.
    """

    proud_m: float | None
    above_window_m: float | None
    has_terrain: bool


class Step(NamedTuple):
    """What structure one plan position had over it.

    ⚠️ **Four outcomes, decoded in this order and never nested**: a rise inside
    the window; a face past it (overhead, refused); structure found only at or
    below the road (the deck the ribbon rests on); nothing at all. `Probe`'s
    docstring above records what conflating two of these cost the ground half.
    """

    rise_m: float | None
    overhead_m: float | None
    has_structure: bool


def road_height(
    drawn: Faces, x: float, z: float, station_y: float, within_m: float
) -> float | None:
    """The drawn carriageway's height here, or `None` where none was drawn.

    🔴 **The drawn road, never the graph's own `y`.** The question is what the
    player's wheels meet, and the ribbon that shipped is what they meet — the
    graph holds what it was built from.

    Both readers below take the answer rather than the mesh, so the two windows
    cannot drift and the road is looked up once per cell. `None` is the
    `no_road` outcome and the callers book it; junction trims and the cap's own
    height cause it, and it is not evidence about anything underneath.
    """
    return nearest(drawn.heights_at(x, z), station_y, within_m)


def ground_above(ground: Faces, x: float, z: float, road_y: float, within_m: float) -> Probe:
    """How far the terrain stands above the drawn road here.

    Nearest, not highest — `deck_error.nearest`'s rule. Highest would attribute
    the top of a sea wall or a cutting face to the road running below it and
    report several metres of "proud" where the geometry is right.
    """
    heights = ground.heights_at(x, z)
    ground_y = nearest(heights, road_y, within_m)
    if ground_y is not None:
        return Probe(ground_y - road_y, None, True)
    # 🔴 The window rejected it, and "no terrain here" and "terrain so far above
    # the road that this refuses to call it the ground" are opposite findings
    # that used to share one counter. The nearest rejected face *above* the road
    # is the one worth reporting: it is a lower bound on a burial this tool has
    # decided not to measure.
    above = heights[heights - road_y > within_m]
    return Probe(None, float(above.min() - road_y) if len(above) else None, bool(len(heights)))


def structure_above(structure: Faces, x: float, z: float, road_y: float, within_m: float) -> Step:
    """How far the lowest structure standing over the drawn road is above it.

    🔴 **Lowest above, where the ground reader takes nearest — and the
    difference is the whole reason this is a separate function.** Terrain is
    single-valued wherever a car can be; structure is a volume in a stack, and
    `Faces.from_tiles` keeps upward-wound faces, so a flyover's deck top is a
    candidate for the street underneath. Read the terrain way, this region's
    interchange reports +13.27 m of "structure proud" on the road beneath it.
    The lowest face above the road is the first thing a climbing wheel would
    meet, which is the question the band exists to ask.

    ⚠️ **A face past `within_m` is refused and returned, never dropped.** That
    is `Probe`'s `above_window_m` at a second layer, and it is what keeps a
    `worst_m` an honest lower bound rather than a number the window chose.
    """
    heights = structure.heights_at(x, z)
    if not len(heights):
        return Step(None, None, False)
    above = heights[heights > road_y]
    if not len(above):
        # Structure found, all of it at or below the road: the deck the ribbon
        # rests on. Geometry working, and deliberately not a miss.
        return Step(None, None, True)
    rise = float(above.min() - road_y)
    if rise > within_m:
        return Step(None, rise, True)
    return Step(rise, None, True)


def survey(
    generated: Path,
    manifest: dict[str, Any],
    ground: Faces,
    structure: Faces,
    *,
    spacing_m: float,
    across_m: float,
    attribute_within_m: float,
    ground_within_m: float,
    structure_within_m: float,
) -> tuple[Survey, Structure]:
    """Every level-0 carriageway cell, asked what the ground and the structure do at it.

    ⚠️ **Across the full drawn width, not down the centreline**, which is
    `overhang`'s sampling rather than `deck_error`'s and is not a detail. The
    kerb runs along the *edge* of the ribbon, so the centreline is the one place
    on the carriageway where a poke-through cannot be seen — and the outer metre,
    where the ground is nearest, is the half this exists to check.

    🔴 **Two surveys from one walk, and they are never merged.** The classes want
    opposite fixes (`Q57`), so they are returned as two records with no shared
    counter; what they share is the walk and the road height, which is the half
    that must not differ between them.
    """
    graph = json.loads((generated / manifest["road_graph"]).read_text())
    widths = half_widths(manifest)
    offsets = drawn_offsets(manifest)
    drawn = drawn_surface(generated, manifest)
    # `road_names` falls back en -> zh -> "unnamed", which is the difference
    # between a street column and a second copy of the edge id: 74 of this
    # region's edges carry neither name, and a city whose streets are signed only
    # in Chinese is hard rule 3's whole point.
    names = road_names(graph)

    found = Survey()
    standing = Structure()
    for edge in graph["edges"]:
        # Level 0 only — see the module docstring.
        if int(edge["elevation_level"]) != 0:
            continue
        edge_id = int(edge["id"])
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        edge_widths = widths.get(edge_id, [])
        edge_offsets = offsets.get(edge_id, [])
        name = names.get(edge_id, "unnamed")
        # `width_m` is the *authored* carriageway — the un-widened figure the
        # graph publishes — and `carriageway_occupancy.py` halves exactly this
        # for its own `authored` column. `Q19` records that the value is itself
        # invented from the speed-limit table; that is a fact about the split,
        # not a reason to measure against something else.
        record = found.begin(edge_id, name, float(edge["width_m"]))
        standing.begin(edge_id, name)
        # 🔴 **Where the ribbon is DRAWN, in `left_of`'s frame (`Q106`).**
        # `surface._shape` offsets both rails by this, so a walk about the
        # centreline reads the road in the wrong place on the 36 off-grade edges
        # `Q103` moved onto their decks. ⚠️ **Named apart from the `offset_m`
        # below, which is a different quantity** — that one is a *cell's* own
        # distance from the centreline, which `Section.is_inside` tests against
        # the authored half-width, and it has to be measured from the centreline
        # the authored width is about rather than from the ribbon's centre.
        # ⚠️ 0.0 on every level-0 edge, so the gated ground half cannot move.

        seen = -1
        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            half = half_width_at(edge_widths, vertex)
            drawn_offset_m = offset_at(edge_offsets, vertex)
            station_y = float(station[1])

            # `stations` walks each segment from its start vertex, so the first
            # station of a segment *is* a retained polyline vertex — and on the
            # centreline, which is where `roads.py` asked the terrain how high to
            # be. Every other cell of the sweep is interpolated away from it in
            # one direction or both, so this is the only sample that grades the
            # sink rather than the road's shape; see `main`.
            #
            # ⚠️ Not a cell of the sweep, which is why it is asked separately:
            # `cross_section` returns cell *centres*, so offset zero is only
            # visited when the width happens to divide into an odd number.
            #
            # ⚠️ Structure is deliberately NOT read here. This population grades
            # the sink, and the sink is a fact about the terrain; asking it about
            # a wall would put two questions in one distribution.
            if vertex != seen:
                seen = vertex
                centre_x, centre_z = float(station[0]), float(station[2])
                centre_y = road_height(drawn, centre_x, centre_z, station_y, attribute_within_m)
                found.add_sampled(
                    None
                    if centre_y is None
                    else ground_above(ground, centre_x, centre_z, centre_y, ground_within_m).proud_m
                )

            # This station's own shape, for the discriminator `StructureEdge`
            # documents. Counted over the cells with a road drawn, never over the
            # cells that found structure.
            section_cells = 0
            section_stepped = 0
            for index, (x, z, span) in enumerate(
                cross_section(station[[0, 2]], normal, half, across_m, drawn_offset_m)
            ):
                found.asked += 1
                area = span * spacing_m
                road_y = road_height(drawn, x, z, station_y, attribute_within_m)
                if road_y is None:
                    found.no_road += 1
                    continue
                section_cells += 1
                standing.saw_road_cell(edge_id, area)

                cell = ground_above(ground, x, z, road_y, ground_within_m)
                if cell.proud_m is not None:
                    # ⚠️ **Reconstructed from the walk, not from the returned
                    # position.** `cross_section` steps in from the left rim in
                    # even spans, so `-half + span * (index + 0.5)` is bit for bit
                    # the offset it used — `carriageway_occupancy.py:743` recovers
                    # it the same way and says why it is not returned. Projecting
                    # the position back onto `normal` would agree here and read
                    # **0.0 for every cell of a zero-length segment**, where
                    # `left_of` returns a zero vector — booking the whole station
                    # as authored, which is the mis-split this column exists to
                    # prevent.
                    found.add(
                        edge_id,
                        cell.proud_m,
                        area,
                        # From the CENTRELINE, which is what the authored
                        # width is about — so the ribbon's own offset is part
                        # of where this cell actually lies (`Q106`).
                        offset_m=drawn_offset_m - half + span * (index + 0.5),
                    )
                elif cell.above_window_m is not None:
                    # The list IS the counter — `Survey.above_window` reads its
                    # length, so the two cannot report different totals.
                    found.above_window_m.append(cell.above_window_m)
                    record.above_window += 1
                    record.above_window_max_m = max(record.above_window_max_m, cell.above_window_m)
                elif cell.has_terrain:
                    found.below_window += 1
                else:
                    found.no_terrain += 1

                # The second class. `Structure.observe` owns the four-way decode
                # and both thresholds, so this loop books a station's shape and
                # nothing else.
                step = structure_above(structure, x, z, road_y, structure_within_m)
                section_stepped += standing.observe(edge_id, step, area)

            standing.add_section(edge_id, section_stepped, section_cells)

    standing.check()
    return found, standing


def report_structure(standing: Structure, within_m: float) -> None:
    """The second class's tables, which share no number with the ground's.

    🔴 **A separate table on purpose** (`Q57`). Everything `main` prints above
    this grades the ground and belongs to `Q24`; everything here grades
    structure standing in the carriageway and belongs to `Q19`. They share the
    walk and the road height and nothing else — and this reports rather than
    gates, so it returns nothing for `main` to weigh.
    """
    log.info("")
    log.info("  STRUCTURE standing over the drawn carriageway — Q19's half, and it does NOT gate:")
    log.info("    %-15s %-34s %8s %11s %7s", "band", "what it is", "cells", "area", "edges")
    bands = (
        (0.0, SUSPENSION_TRAVEL_M, "the car rides over it"),
        (SUSPENSION_TRAVEL_M, BUMPER_LOW_M, "Q19's BAND - no other instrument"),
        (BUMPER_LOW_M, within_m, "already carriageway_occupancy's"),
    )
    for low, high, label in bands:
        cells, area, edges = standing.cells_in(low, high)
        log.info(
            "    %-15s %-34s %8d %8.1f m2 %7d",
            f"{low:.2f} - {high:.2f} m",
            label,
            cells,
            area,
            edges,
        )
    if standing.overhead:
        overhead = np.asarray(standing.overhead_m)
        log.info(
            "    %-15s %-34s %8d %11s",
            f"over {within_m:.2f} m",
            "refused - a deck over the street",
            standing.overhead,
            f"{overhead.min():.2f}-{overhead.max():.2f} m",
        )
    log.info(
        "    %d cells rest on structure at or below the road, %d have no structure at all"
        " (%.1f%% of %d)",
        standing.resting,
        standing.absent,
        100.0 * standing.absent / standing.on_road if standing.on_road else 0.0,
        standing.on_road,
    )
    # ⚠️ **The band is the finding; the row above it is not.** Anything past
    # `BUMPER_LOW_M` is already counted by `carriageway_occupancy`, so summing
    # the two would republish `Q19`'s own population as this instrument's
    # discovery. Both are printed so the comparison is possible and neither is
    # totalled.

    if standing.section_share:
        share = np.asarray(standing.section_share)
        log.info("")
        log.info(
            "    of the %d cross-sections carrying a step, the share of the section stepped reads",
            len(share),
        )
        log.info(
            "    p50 %.0f%% / p90 %.0f%% / max %.0f%%, and %d are more than half stepped —",
            100.0 * float(np.median(share)),
            100.0 * float(np.percentile(share, 90.0)),
            100.0 * float(share.max()),
            int((share > 0.5).sum()),
        )
        log.info(
            "    Q19's discriminator: a ledge takes a strip of a section, a ribbon disagreeing"
        )
        log.info("    with the deck it rests on takes most of one. See Q23 for the suppression")

    stepped_edges = sorted(
        ((edge_id, edge) for edge_id, edge in standing.edges.items() if edge.band_m2 > 0.0),
        key=lambda item: -item[1].band_m2,
    )
    log.info("")
    log.info(
        "  level-0 edges carrying structure in the %.2f-%.2f m band, by area of it:",
        SUSPENSION_TRAVEL_M,
        BUMPER_LOW_M,
    )
    log.info(
        "    'past bumper' is the same edge's area over %.2f m — already occupancy's, never"
        " added to the band",
        BUMPER_LOW_M,
    )
    log.info(
        "    'sections' is stepped/measured with the worst section's own share; 'over window' is"
        " cells refused"
    )
    log.info(
        "    past --structure-within-m %.2f m, so every 'worst' is a bound and that column says"
        " by how much",
        within_m,
    )
    log.info(
        "    %-6s %-26s %8s %10s %8s %11s %11s %13s",
        "edge",
        "street",
        "worst",
        "in band",
        "of ribbon",
        "past bumper",
        "sections",
        "over window",
    )
    for edge_id, edge in stepped_edges:
        log.info(
            "    e%-5d %-26s %+7.2fm %7.1f m2 %7.1f%% %8.1f m2 %11s %13s",
            edge_id,
            edge.name[:26],
            edge.worst_m,
            edge.band_m2,
            100.0 * edge.band_share,
            edge.over_bumper_m2,
            f"{edge.stepped_stations}/{edge.stations} @{100.0 * edge.worst_section_share:.0f}%",
            f"{edge.overhead} to {edge.overhead_min_m:+.2f}m" if edge.overhead else "",
        )
    log.info(
        "    %d of %d level-0 edges, %.1f m2 of %.1f m2 of measured ribbon",
        len(stepped_edges),
        len(standing.edges),
        standing.band_area(),
        standing.ribbon_area(),
    )
    log.info("    note this is a THIRD population: the whole drawn ribbon, in the drawn frame.")
    log.info(
        "    Q19's corrected 14-of-17 edges and 45 stations were measured inside the CORRIDOR,"
    )
    log.info("    and the superseded 31 came from a scratch script. Do not quote one for another")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    parser.add_argument(
        "--spacing-m", type=float, default=2.0, help="station spacing along an edge"
    )
    parser.add_argument("--across-m", type=float, default=0.5, help="cell width across the ribbon")
    parser.add_argument(
        "--ground-within-m",
        type=float,
        default=3.0,
        # Wide enough to find the ground under a road on a low embankment, tight
        # enough that a cutting face or a sea wall several metres away is not
        # attributed to the carriageway beside it. The terrain is single-valued
        # wherever a vehicle can be, so on this region almost every cell has one
        # candidate and the window never chooses.
        help="how far terrain may sit from the drawn road and still be the ground under it",
    )
    parser.add_argument(
        "--structure-within-m",
        type=float,
        default=BUMPER_HIGH_M,
        # 🔴 **Sourced, not chosen.** `BUMPER_HIGH_M` is the top of the band
        # `clearance.py` treats as an obstruction; structure above it is
        # overhead that no instrument in this bundle calls a wall. A number
        # picked here instead would be a second opinion about the same fact.
        #
        # ⚠️ A flag rather than a constant because it decides a refusal, and a
        # refusal whose bound cannot be swept is `Q58`'s `drawn_gauge_m` trap —
        # which is also why what it refuses is published rather than dropped.
        help="how far above the road a structure face may sit and still be a step, not a flyover",
    )
    parser.add_argument(
        "--accept-proud-m",
        type=float,
        default=0.0,
        help="ground above the road by more than this is counted against both share gates",
    )
    parser.add_argument(
        "--accept-sampled-share",
        type=float,
        default=0.015,
        # **This is the gate on the sink**, and the only one that grades `P3-10`.
        # It has to leave room for the sink to be retuned without a false
        # failure, and still catch it being dropped, halved, or applied to the
        # wrong class — any of which reads about 50%.
        #
        # ⚠️ **Raised from 1% because closing holes raises this without any
        # ground moving**, which is the mirror of the denominator trap `Survey`
        # documents and is just as capable of misleading. It was set at 1% when
        # the measurement was 0.363% — against a bundle whose torn ground made
        # 3.35% of the sampled points unmeasurable. `1ec1605` and `Q25` closed
        # most of those tears, and the newly visible cells are proud at the
        # region's own rate (2.213% against 2.205%), so the *share* climbed to
        # 1.0003% while the defect did not. Measured like-for-like over the
        # cells both bundles could see: **2.181% → 2.205%**, +0.024pp.
        help="fail above this share of sampled points with ground standing proud",
    )
    parser.add_argument(
        "--accept-share",
        type=float,
        default=0.035,
        # A regression bar rather than a standard, and **it is not the sink's
        # number** — see the note printed beneath it. 3.289% measured on the
        # first build that shipped ground; this fails a build that makes it
        # meaningfully worse and would want lowering the day the chord defect
        # below is fixed. It reads 2.199% today, and the same coverage caveat
        # as the sampled gate applies to any comparison across a ground fix.
        help="fail above this share of all carriageway area with ground proud",
    )
    parser.add_argument(
        "--accept-edges-over-travel",
        type=int,
        default=87,
        # 🔴 **A regression ratchet, and it is NOT a standard** — the same
        # wording `--accept-share` above already carries, and the same honesty is
        # owed twice over here. `carriageway_occupancy.py`'s region ratchet is
        # legitimate because it inherited `Q19`'s figures, "fixed before this
        # grader existed"; **this number is this instrument's own first reading**
        # (87 of 737 edges on the 2026-08-27 bundle) and is therefore exactly the
        # bar-tuned-to-its-own-data the `Q47` precedent warns about. It is set
        # anyway because the alternative is worse: a hard bar at zero
        # fails 88 edges on a defect nobody has decided how to fix (`Q24` is
        # HOLD), and no bar at all lets the population grow unnoticed. **So it
        # fails a build that buries MORE edges and says nothing about the 88** —
        # lower it when a fix lands, never raise it to match a regression.
        help="fail above this many level-0 edges with ground proud past suspension travel",
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
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    manifest, tiles = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)

    ground, terrain_class = ground_faces(city, tiles)
    structure, structure_class = optional_structure_faces(city, tiles)
    found, standing = survey(
        args.generated,
        manifest,
        ground,
        structure,
        spacing_m=args.spacing_m,
        across_m=args.across_m,
        attribute_within_m=args.attribute_within_m,
        ground_within_m=args.ground_within_m,
        structure_within_m=args.structure_within_m,
    )
    log.info(
        "  %d upward faces of '%s' across %d tiles, sampled on a %.1f x %.1f m grid",
        len(ground.corners),
        terrain_class,
        len(tiles),
        args.spacing_m,
        args.across_m,
    )
    if structure_class is not None:
        log.info(
            "  %d upward faces of '%s' across the same tiles",
            len(structure.corners),
            structure_class,
        )
    log.info("  sink declared in config: %.3f m", city.buildings.ground_sink_m)

    if not found.measured:
        raise SystemExit(
            "no level-0 carriageway could be measured — is the road mesh present, and does "
            "the bundle ship ground?"
        )

    proud = np.asarray(found.proud_m)
    log.info("")
    log.info("  ground height relative to the drawn carriageway, + is standing proud:")
    for name, value in (
        ("max", float(proud.max())),
        ("p99", float(np.percentile(proud, 99.0))),
        ("p90", float(np.percentile(proud, 90.0))),
        ("median", float(np.percentile(proud, 50.0))),
        ("min", float(proud.min())),
    ):
        log.info("    %-7s %+7.3f m", name, value)

    log.info("")
    log.info("  by carriageway area, and at the points the road's height was sampled from:")
    for threshold in (0.0, 0.05, 0.10, 0.15):
        log.info(
            "    %6.3f%% of area / %6.3f%% of samples standing more than %.2f m proud",
            100.0 * found.area_share_above(threshold),
            100.0 * found.sampled_share_above(threshold),
            threshold,
        )
    log.info(
        "    worst cell is %.0f%% of the car's %.2f m suspension travel",
        100.0 * max(0.0, float(proud.max())) / SUSPENSION_TRAVEL_M,
        SUSPENSION_TRAVEL_M,
    )

    # ⚠️ The two columns above measure two different things, and reading the
    # first as the sink's score is the mistake this tool exists to prevent.
    #
    # The **second** column is the sink's. There the road's height came from
    # `ground.sample` at that exact plan point, so the only things standing
    # between the two surfaces are `ground_sink_m` and the tile decimation.
    #
    # The **first** column is every cell of the drawn ribbon, and the road is a
    # *plane* while the ground is not — interpolated along its length between
    # retained vertices, and flat across its width. Both gaps are the road's
    # shape rather than the sink's depth:
    #
    # - **Along.** `simplify` keeps 2.0% of the source vertices, so the road
    #   runs as a straight chord over ground that curves. Measured: 0.35% of
    #   centreline points proud within a metre of a vertex, against **5.78%** at
    #   15-40 m from one; 0.58% on segments under 20 m against 3.66% on segments
    #   of 50-100 m. `P2-7` met this exact defect on elevated edges and fixed it
    #   by densifying — `resample` before sampling — and level-0 edges are
    #   resampled only where they were lifted onto a ramp.
    # - **Across.** The ribbon is extruded flat from a centreline height, so a
    #   cross-sloped street rises into it at the kerb. The rate runs 2.27% at
    #   the centreline to **5.39%** at the outer rim, and the outer rim is where
    #   the 1.6x playability widening put carriageway on top of the frontage —
    #   `Q19`'s trade, showing up in a second place.
    #
    # **No sink closes either**, and a sink deep enough to try would drop the
    # ground below every kerb in the region — the gap reaches 2.98 m on the
    # worst street.
    log.info("")
    log.info("  the second column grades the sink. The first also carries the road's")
    log.info("  own shape — straight between vertices, flat across its width — which")
    log.info("  no sink can close. See this tool's source, and Q24.")

    log.info("")
    log.info(
        "  %d cells asked, %d measured (%.1f%%), %d with no road drawn, %d with no ground found",
        found.asked,
        found.measured,
        100.0 * found.coverage,
        found.no_road,
        found.no_ground,
    )
    log.info(
        "  %d sampled points asked, %d measured (%.1f%%)",
        found.sampled_asked,
        len(found.sampled_m),
        100.0 * found.sampled_coverage,
    )
    if found.above_window:
        above = np.asarray(found.above_window_m)
        log.info(
            "    of those, %d are terrain standing %.2f-%.2f m ABOVE the road (p50 %.2f) —",
            found.above_window,
            float(above.min()),
            float(above.max()),
            float(np.median(above)),
        )
        log.info(
            "    burials this refuses to attribute, not coverage. Every max below is a lower bound"
        )
        log.info(
            "    %d more sit under road drawn %.2f m clear of real terrain, and %d under no"
            " terrain at all",
            found.below_window,
            args.ground_within_m,
            found.no_terrain,
        )
    measured_edges = {edge_id: edge for edge_id, edge in found.edges.items() if edge.area_m2}
    worst = sorted(measured_edges.items(), key=lambda item: -item[1].worst_m)[:6]
    if worst:
        log.info(
            "  worst edges: %s",
            ", ".join(f"e{edge} {cells.worst_m:+.2f} m" for edge, cells in worst),
        )

    # 🔴 **The per-edge population, which is the half a region share cannot
    # show.** See `EdgeCells`. Every edge over the bar, not the tightest
    # handful — `carriageway_occupancy.py`'s rule, and for its reason: a capped
    # listing is a listing that stops naming the defect once there is enough of
    # it.
    over_travel = sorted(
        ((edge_id, edge) for edge_id, edge in measured_edges.items() if edge.over_m2 > 0.0),
        key=lambda item: -item[1].over_share,
    )
    log.info("")
    log.info(
        "  drivable level-0 edges with ground proud past the car's %.2f m suspension travel:",
        SUSPENSION_TRAVEL_M,
    )
    log.info(
        "    'authored' is the same cell measured inside the un-widened width, 'rim' outside it"
    )
    log.info(
        "    'over window' is cells whose burial this refused to attribute, so 'max' is a bound"
    )
    log.info(
        "    %-6s %-28s %8s %9s %9s %9s %11s",
        "edge",
        "street",
        "max",
        "of ribbon",
        "authored",
        "rim",
        "over window",
    )
    for edge_id, edge in over_travel:
        log.info(
            "    e%-5d %-28s %+7.2fm %8.1f%% %8.1f%% %8.1f%% %11s",
            edge_id,
            edge.name[:28],
            edge.worst_m,
            100.0 * edge.over_share,
            100.0 * edge.inside_over_share,
            100.0 * edge.rim_over_share,
            f"{edge.above_window} to {edge.above_window_max_m:+.2f}m" if edge.above_window else "",
        )
    log.info(
        "    %d of %d measured edges, %d of them past a tenth of the ribbon"
        " (%d more level-0 edges were walked and could not be measured at all)",
        len(over_travel),
        len(measured_edges),
        sum(1 for _, edge in over_travel if edge.over_share > 0.10),
        len(found.edges) - len(measured_edges),
    )

    report_structure(standing, args.structure_within_m)

    problems = []
    sampled = found.sampled_share_above(args.accept_proud_m)
    if sampled > args.accept_sampled_share:
        problems.append(
            f"{100.0 * sampled:.3f}% of the points the road's height was sampled from have "
            f"ground more than {args.accept_proud_m:.2f} m proud, against "
            f"{100.0 * args.accept_sampled_share:.3f}% — the sink is not holding it down"
        )
    share = found.area_share_above(args.accept_proud_m)
    if share > args.accept_share:
        problems.append(
            f"{100.0 * share:.3f}% of all carriageway area has ground more than "
            f"{args.accept_proud_m:.2f} m proud, against {100.0 * args.accept_share:.3f}%"
        )
    # 🔴 `len(over_travel)`, never a second copy of the predicate. The listing
    # above and this gate have to be the same number by construction or the
    # report and the exit code can drift — which is the whole reason `EdgeCells`
    # replaced a bare worst-cell map.
    edges_over = len(over_travel)
    if edges_over > args.accept_edges_over_travel:
        problems.append(
            f"{edges_over} level-0 edges carry ground proud past the car's "
            f"{SUSPENSION_TRAVEL_M:.2f} m suspension travel, against "
            f"{args.accept_edges_over_travel} — the population grew, and Q24 is open, "
            f"not licensed to widen"
        )
    # Both populations, because the gate that matters rides on the second one:
    # a build that stopped shipping ground under half the region would drop
    # those points and *improve* the share they gate.
    for name, coverage in (("cells", found.coverage), ("sampled points", found.sampled_coverage)):
        if coverage < args.accept_coverage:
            problems.append(
                f"only {100.0 * coverage:.1f}% of asked {name} could be measured, against "
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


if __name__ == "__main__":
    raise SystemExit(main())
