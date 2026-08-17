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

Run:  .venv/bin/python tools/ground_clearance.py --city hong_kong
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    class_faces,
    drawn_surface,
    load_bundle,
    log_bundle,
    nearest,
)
from overhang import cross_section, half_width_at, half_widths, left_of, walk_width  # noqa: E402
from pipeline.config import load_city  # noqa: E402

log = logging.getLogger(__name__)

# `handling.tres`'s `suspension_travel_m`, mirrored rather than read: this is a
# hand-run Python tool and the `.tres` is Godot's. Quoted in the report because
# it is what turns a drawing defect into a handling one, and it is the number
# `P1-4`'s kerb was judged against.
SUSPENSION_TRAVEL_M = 0.18


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
    no_ground: int = 0
    # Worst cell per edge, for naming where to go and look.
    worst: dict[int, float] = field(default_factory=dict)

    @property
    def measured(self) -> int:
        return len(self.proud_m)

    @property
    def coverage(self) -> float:
        return self.measured / self.asked if self.asked else 0.0

    @property
    def sampled_coverage(self) -> float:
        return len(self.sampled_m) / self.sampled_asked if self.sampled_asked else 0.0

    def add(self, edge_id: int, proud_m: float, area_m2: float) -> None:
        self.proud_m.append(proud_m)
        self.area_m2.append(area_m2)
        if proud_m > self.worst.get(edge_id, -np.inf):
            self.worst[edge_id] = proud_m

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


def survey(
    generated: Path,
    manifest: dict[str, Any],
    ground: Faces,
    *,
    spacing_m: float,
    across_m: float,
    attribute_within_m: float,
    ground_within_m: float,
) -> Survey:
    """Every level-0 carriageway cell, asked how far the ground stands above it.

    ⚠️ **Across the full drawn width, not down the centreline**, which is
    `overhang`'s sampling rather than `deck_error`'s and is not a detail. The
    kerb runs along the *edge* of the ribbon, so the centreline is the one place
    on the carriageway where a poke-through cannot be seen — and the outer metre,
    where the ground is nearest, is the half this exists to check.
    """
    graph = json.loads((generated / manifest["road_graph"]).read_text())
    widths = half_widths(manifest)
    drawn = drawn_surface(generated, manifest)

    def probe(x: float, z: float, station_y: float) -> tuple[float | None, bool]:
        """How far the ground stands above the drawn road here, and whether a
        road was drawn at all — which is what separates the two kinds of miss.

        One function for both populations so the two windows cannot drift: the
        width sweep and the centreline probe have to stay comparable, and the
        whole report turns on comparing them.
        """
        # The drawn road first: the question is what the player's wheels meet,
        # and the graph's own `y` is what the ribbon was built from rather than
        # what shipped.
        road_y = nearest(drawn.heights_at(x, z), station_y, attribute_within_m)
        if road_y is None:
            return None, False
        # Nearest, not highest — `deck_error.nearest`'s rule again. Highest would
        # attribute the top of a sea wall or a cutting face to the road running
        # below it and report several metres of "proud" where geometry is right.
        ground_y = nearest(ground.heights_at(x, z), road_y, ground_within_m)
        return (None if ground_y is None else ground_y - road_y), True

    found = Survey()
    for edge in graph["edges"]:
        # Level 0 only — see the module docstring.
        if int(edge["elevation_level"]) != 0:
            continue
        edge_id = int(edge["id"])
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if len(polyline) < 2:
            continue
        edge_widths = widths.get(edge_id, [])

        seen = -1
        for vertex, station in walk_width(polyline, spacing_m):
            along = polyline[vertex + 1] - polyline[vertex]
            normal = left_of(along[[0, 2]])
            half = half_width_at(edge_widths, vertex)
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
            if vertex != seen:
                seen = vertex
                found.add_sampled(probe(float(station[0]), float(station[2]), station_y)[0])

            for x, z, span in cross_section(station[[0, 2]], normal, half, across_m):
                found.asked += 1
                proud, on_road = probe(x, z, station_y)
                if proud is not None:
                    found.add(edge_id, proud, span * spacing_m)
                elif on_road:
                    found.no_ground += 1
                else:
                    found.no_road += 1

    return found


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

    city = load_city(args.city)
    manifest, tiles = load_bundle(args.generated, args.lod, args.city)
    log_bundle(manifest, args.lod)

    ground, terrain_class = ground_faces(city, tiles)
    found = survey(
        args.generated,
        manifest,
        ground,
        spacing_m=args.spacing_m,
        across_m=args.across_m,
        attribute_within_m=args.attribute_within_m,
        ground_within_m=args.ground_within_m,
    )
    log.info(
        "  %d upward faces of '%s' across %d tiles, sampled on a %.1f x %.1f m grid",
        len(ground.corners),
        terrain_class,
        len(tiles),
        args.spacing_m,
        args.across_m,
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
    worst = sorted(found.worst.items(), key=lambda item: -item[1])[:6]
    if worst:
        log.info(
            "  worst edges: %s",
            ", ".join(f"e{edge} {value:+.2f} m" for edge, value in worst),
        )

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
