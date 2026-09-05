"""Whether the painted layers are above the road they are painted on.

The fourth sibling of `deck_error.py`, `overhang.py` and `ground_clearance.py`,
and the one that grades the *markings* rather than the surface. `deck_error`
asks how far an elevated road is from the deck under it; `overhang` asks whether
there is a deck under it at all; `ground_clearance` asks whether the ground is
where the road is. This asks the question none of them reach — **is the paint on
top of the asphalt, or inside it?**

It exists because a marking stage cannot see this defect from the inside. Every
counter `boxjunctions.json`, `roadmarks.json` and `arrows.json` publish grades
the ETL against its own intermediate values: `height_spread_m` says how far a
height join *moved* a vertex, never whether it landed on the drawn road. `Q91`
closed the last box-junction defect on the evidence that "a top-down raster of
the shipped `boxjunctions.glb` is a complete grid" — which is true, and is
exactly the projection that cannot see this one. The mesh is complete in **plan**
and wrong in **Y**, and paint under asphalt renders as no paint at all.

Nothing here is shared with the code it grades:

| | the pipeline | this tool |
|---|---|---|
| Road height | a height model over the graph | the **shipped `roads.glb`** |
| Paint height | the same model, plus `lift_m` | the **shipped marking mesh** |
| Which surface is road | the stage that drew it | **near-horizontal faces**, by normal |
| Spatial index | none — the stages query a model | `Faces`, keyed from the origin |

🔴 **Four columns per layer, because four different things put paint under
road, and only the last one is this tool's to gate.** Reporting them as one
number leaves nothing to do but raise the bar.

- **`under hi`** — below the **highest** road face there. What the depth buffer
  hides, so what the player loses. Not gated.
- **`on kerb`** — its cover is a **raised edge** with carriageway beside it: a
  surveyed extent reaching past the drawn ribbon. Registration, and `Q54`
  refuses to fix that by scaling. Not gated.
- **`in c'way`** — below the **lowest** face and not on an edge: paint at the
  wrong height on the road it is drawn on. Not gated.
- **`deep`** — that, past `--accept-depth-m`. **Gated.**

`under hi` minus the rest is paint that clears the carriageway and is covered by
something else drawn over it — a neighbouring ribbon's kerb lip, or a cap over
an arm, the 6,051 m² overlap `Q53` measured. That is a `surface.py` question
(`_hide_buried_kerbs`) and not this bar's.

The split of `in c'way` at a depth is the one that took a measurement to
justify: a marking is a **flat triangle over a road that creases** at every cap
fan edge and every ribbon station, so its chord dips below the crown it spans by
millimetres however right its vertices are. On the corrected bundle that residue
is p50 **0.0027 m** and it is closed by subdividing paint at the road's creases,
not by moving a height.

⚠️ **A triangle is judged at its centroid, so the quantum is one triangle.**
The layers are paint: the median shipped marking triangle is a few hundredths of
a square metre, and no marking triangle spans a cap boundary, so a centroid
carries its triangle honestly. The count share and the area share are both
reported because they can disagree, and neither is derived from the other.

⚠️ **Candidates are filtered to `--road-within-m` of the paint's own height.**
A flyover deck overhead is not the road a marking is painted on, and scoring
against it would report the height of every bridge as a burial. It is the one
form `ground_clearance.py`'s "level 0 only" can take on a layer that publishes no
level.

Run:  .venv/bin/python tools/paint_clearance.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from deck_error import (  # noqa: E402
    Faces,
    bundle_arguments,
    drawn_surface,
    load_bundle,
    log_bundle,
)
from pipeline.documents import read_document  # noqa: E402
from pipeline.gltf import read_glb  # noqa: E402
from pipeline.placements import PLACEMENTS_SCHEMA, stood_positions  # noqa: E402

log = logging.getLogger(__name__)

# The manifest keys this grades, in the order the report prints them. Keyed on
# `city.json` rather than on a directory listing so a layer that stops being
# declared stops being graded loudly — `signals` is `null` today (`Q77`) and a
# sweep of `*.glb` would silently grade a stale file (`Q70`'s deleted-image
# hazard, arriving from the other side).
#
# ⚠️ **Whether a layer is gated is a column here and not a second list.** Written
# as one, a typo in it silently ungates a layer and the tool still exits 0 with a
# table that looks right — which is the failure this whole module is about.
_LAYERS: tuple[tuple[str, str, bool], ...] = (
    ("boxjunctions", "yellow box junctions", True),
    ("roadmarks", "stop and give-way lines", True),
    # Reported and never gated. `Q58` measured tram rails a median 3.26 m *past*
    # the drawn kerb, off the carriageway entirely, so a "buried" tram triangle
    # may be correctly drawn on a surface this tool cannot see — graded anyway,
    # because a rail sunk into a street it *does* cross is a real defect. And
    # `arrows` takes its height from its host ribbon rather than from the surface
    # model this bar is about.
    ("arrows", "turn arrows", False),
    ("tramway", "tram rails", False),
)


@dataclass(frozen=True)
class Bars:
    """The four numbers a survey judges against, under their own flag names.

    Together rather than as four keyword arguments because they travel as a set:
    `survey` uses one and hands two straight through to `on_raised_edge`, and a
    caller passing them individually has to map four renamed parameters back to
    four flags by hand. Keeping the flag's own name on each is what makes
    `Bars.of(args)` a transcription rather than a translation.
    """

    road_within_m: float
    kerb_probe_m: float
    kerb_step_m: float
    accept_depth_m: float

    @classmethod
    def of(cls, args: argparse.Namespace) -> Bars:
        return cls(
            road_within_m=args.road_within_m,
            kerb_probe_m=args.kerb_probe_m,
            kerb_step_m=args.kerb_step_m,
            accept_depth_m=args.accept_depth_m,
        )


@dataclass
class LayerVerdict:
    """One layer, and what the road did under each of its triangles.

    ⚠️ **`no_road` is counted rather than dropped.** Paint drawn where the
    shipped road mesh has no face at all is not a burial and is not a pass: it is
    a marking on something that is not a carriageway, or on a hole. Left out of
    the denominator silently it would flatter every share here — the denominator
    trap `ground_clearance.Survey` was split up to end.
    """

    key: str
    name: str
    gated: bool = False
    triangles: int = 0
    no_road: int = 0
    no_road_area_m2: float = 0.0

    judged: int = 0
    judged_area_m2: float = 0.0

    # Below the highest near-horizontal road face at its own plan position —
    # what the depth buffer sees, and what the player loses.
    under_highest: int = 0
    under_highest_area_m2: float = 0.0
    depth_under_highest_m: list[float] = field(default_factory=list)

    # Below the *lowest* such face, so with no second surface to blame. Split
    # below into a kerb top and the carriageway itself; the gate rides on
    # neither of these but on `deep_in_carriageway`.
    under_lowest: int = 0
    under_lowest_area_m2: float = 0.0
    depth_under_lowest_m: list[float] = field(default_factory=list)

    # 🔴 **The split of `under_lowest`, and the only reason the gate can mean
    # anything.** `on_raised_edge` is paint whose cover is a kerb top with
    # carriageway beside it — a surveyed extent reaching past the drawn ribbon,
    # which is registration and which `Q54` refuses to fix by scaling. What is
    # left, `in_carriageway`, is paint at the wrong height on the road it is
    # actually drawn on, which is a defect with a fix. They partition:
    # `under_lowest == on_raised_edge + in_carriageway`.
    on_raised_edge: int = 0
    on_raised_edge_area_m2: float = 0.0
    in_carriageway: int = 0
    in_carriageway_area_m2: float = 0.0
    depth_in_carriageway_m: list[float] = field(default_factory=list)
    # 🔴 **The gated population, and the depth is why it is not just a count.**
    # Paint is a flat triangle laid over a road that creases at every cap fan
    # edge and every ribbon station, and a chord across a crown dips below the
    # surface it spans. That residue is millimetres and geometric — it is fixed
    # by subdividing paint at the road's creases, not by moving a height. Past
    # `--accept-depth-m` a burial has stopped being a chord and is a wrong
    # height, which is what this tool is for.
    deep_in_carriageway: int = 0

    # Highest minus lowest where a point had more than one candidate, so a
    # reader can tell a kerb lip (~0.15 m) from a fold in one surface.
    stacked: int = 0
    stack_spread_m: list[float] = field(default_factory=list)

    def share(self, count: int) -> float:
        """A count as a share of the triangles this layer could judge.

        One method rather than a property per column: the headline table needs
        six of these and half of them were being divided inline, so a reader had
        to work out whether "share" meant the property or the arithmetic beside
        it. `judged` is the denominator for every one of them — never
        `triangles`, which includes the paint no road was found under.
        """
        return count / self.judged if self.judged else 0.0

    def area_share(self, area_m2: float) -> float:
        """The same, by paint area. Reported beside the counts because the two
        can disagree, and neither is derived from the other."""
        return area_m2 / self.judged_area_m2 if self.judged_area_m2 else 0.0

    @property
    def coverage(self) -> float:
        return self.judged / self.triangles if self.triangles else 0.0


def paint_triangles(path: Path, placements: Path | None = None) -> np.ndarray:
    """Every triangle of a marking mesh as `(n, 3, 3)` corners.

    Unlike `deck_error.drawn_surface` this does not insist on a single
    primitive: a marking layer is one mesh today, and a layer that grew a second
    would still be entirely paint. What it must not do is filter by normal —
    every triangle of a marking is judged, including the ones facing the ground,
    because a mesh whose winding has flipped is a separate defect each stage
    already counts as `inverted` and this tool must not quietly agree with it.

    🔴 **A layer with a `placements` document is a LIBRARY (`P5-4`), and what is
    judged is the library stood by it** — every glyph at every stand, pitched
    to its grade — never the library itself, which lies flat at the origin over
    no road at all and would read 100% uncovered. The expansion is
    `pipeline.placements.stood_positions`, the ETL's own statement of the
    stand, so this tool grades the arrows the engine draws and shares only the
    transform convention with the stage — the heights it judges against are the
    shipped `roads.glb`'s, as before.
    """
    meshes = [mesh for mesh in read_glb(path) if len(mesh.triangles)]
    if placements is None:
        blocks = [mesh.positions[mesh.triangles].astype(np.float64) for mesh in meshes]
    else:
        library = {mesh.name: mesh for mesh in meshes}
        document = read_document(
            placements, PLACEMENTS_SCHEMA, "rebuild the region; the placements schema moved"
        )
        blocks = []
        for entry in document["placements"]:
            mesh = library.get(str(entry["mesh"]))
            if mesh is None:
                raise SystemExit(f"{placements} stands '{entry['mesh']}', which {path} lacks")
            blocks.append(stood_positions(mesh, entry)[mesh.triangles].astype(np.float64))
    if not blocks:
        raise SystemExit(f"{path} holds no triangles")
    return np.concatenate(blocks)


def twice_plan_area(corners: np.ndarray) -> np.ndarray:
    """Twice each triangle's area in plan, `(n,)`.

    Plan rather than true area because that is what a paint layer covers on the
    street, and because a marking lying on a 5% grade is not 0.1% more paint.
    """
    first = corners[:, 1, [0, 2]] - corners[:, 0, [0, 2]]
    second = corners[:, 2, [0, 2]] - corners[:, 0, [0, 2]]
    return np.abs(first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0])


def on_raised_edge(road: Faces, x: float, z: float, cover_m: float, bars: Bars) -> bool:
    """Whether the thing covering this point is a raised edge, not the carriageway.

    🔴 **Without this the gate below can only be tuned, and that is why it is
    here.** Two very different things put paint under road: a marking placed at
    the wrong *height* on the carriageway it is drawn on — a defect, with a fix —
    and a marking whose surveyed extent reaches past the drawn carriageway onto
    a **kerb top**, which stands `kerb_height_m` above it. The second is
    registration, not height, and this project refuses to fix it by scaling a
    surveyed extent onto the drawn ribbon (`Q54`); conflated into one number it
    would simply raise the bar until the first stopped being caught.

    Told apart by asking the shipped mesh about the *neighbourhood* rather than
    the point: a kerb top is a narrow raised strip with carriageway beside it, so
    a road face a kerb's height lower within a metre means the cover is an edge
    and the paint is beside the road rather than inside it. Deliberately no
    config and no graph — `kerb_height_m` is the pipeline's number, and reading
    it here would make this tool agree with the thing it grades.
    """
    lowest_near = cover_m
    for angle in np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False):
        near = road.heights_at(
            x + bars.kerb_probe_m * float(np.cos(angle)),
            z + bars.kerb_probe_m * float(np.sin(angle)),
        )
        if len(near):
            # The same window `survey` selects candidates with, rather than a
            # second number: two sites writing one rule is how they drift into
            # two rules for the same decision (`deck_error.nearest`).
            near = near[np.abs(near - cover_m) < bars.road_within_m]
        if len(near):
            lowest_near = min(lowest_near, float(near.min()))
    return cover_m - lowest_near >= bars.kerb_step_m


def survey(
    corners: np.ndarray,
    road: Faces,
    *,
    key: str,
    name: str,
    bars: Bars,
    gated: bool = False,
) -> LayerVerdict:
    """Ask the shipped road what it is doing under every triangle of a layer."""
    verdict = LayerVerdict(key=key, name=name, gated=gated, triangles=len(corners))
    centroids = corners.mean(axis=1)
    areas = 0.5 * twice_plan_area(corners)

    for index, (x, y, z) in enumerate(centroids):
        area = float(areas[index])
        candidates = road.heights_at(float(x), float(z))
        if len(candidates):
            candidates = candidates[np.abs(candidates - y) < bars.road_within_m]
        if not len(candidates):
            verdict.no_road += 1
            verdict.no_road_area_m2 += area
            continue

        highest, lowest = float(candidates.max()), float(candidates.min())
        verdict.judged += 1
        verdict.judged_area_m2 += area
        if len(candidates) > 1:
            verdict.stacked += 1
            verdict.stack_spread_m.append(highest - lowest)
        if y < highest:
            verdict.under_highest += 1
            verdict.under_highest_area_m2 += area
            verdict.depth_under_highest_m.append(highest - float(y))
        if y < lowest:
            verdict.under_lowest += 1
            verdict.under_lowest_area_m2 += area
            verdict.depth_under_lowest_m.append(lowest - float(y))
            if on_raised_edge(road, float(x), float(z), lowest, bars):
                verdict.on_raised_edge += 1
                verdict.on_raised_edge_area_m2 += area
            else:
                verdict.in_carriageway += 1
                verdict.in_carriageway_area_m2 += area
                verdict.depth_in_carriageway_m.append(lowest - float(y))
                if lowest - float(y) > bars.accept_depth_m:
                    verdict.deep_in_carriageway += 1
    return verdict


def measured(values: list[float]) -> dict[str, float]:
    """One distribution as the report prints it: the tail, never a median alone.

    `ArrowReport.measured`'s rule, restated for the same reason — every number
    here is a residual, and a median near zero is also what a wholly broken layer
    looks like when most of it happens to be flat.
    """
    if not values:
        return {}
    array = np.asarray(values, dtype=np.float64)
    return {
        "p50": float(np.percentile(array, 50.0)),
        "p90": float(np.percentile(array, 90.0)),
        "p99": float(np.percentile(array, 99.0)),
        "max": float(array.max()),
        "n": float(len(array)),
    }


def _log_distribution(label: str, values: list[float]) -> None:
    stats = measured(values)
    if not stats:
        log.info("      %-22s none", label)
        return
    log.info(
        "      %-22s p50 %.4f  p90 %.4f  p99 %.4f  max %.4f  (n %d)",
        label,
        stats["p50"],
        stats["p90"],
        stats["p99"],
        stats["max"],
        int(stats["n"]),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0], parents=[bundle_arguments()]
    )
    parser.add_argument(
        "--road-within-m",
        type=float,
        default=1.5,
        # Wide enough to hold a junction cap that disagrees with the arms it
        # spans by the 0.43 m `Q92` measured, tight enough that a flyover deck
        # is never the road a street marking is painted on. The
        # region's smallest published clearance between stacked carriageways is
        # metres, so this window never chooses between two real candidates.
        help="how far a road face may sit from the paint and still be the road under it",
    )
    parser.add_argument(
        "--kerb-probe-m",
        type=float,
        default=1.0,
        # A kerb top is 0.5 m of lip over a 0.15 m riser, so a metre out from a
        # point standing on one always reaches the carriageway beside it — and a
        # metre is short enough that it never leaves a genuine carriageway, the
        # narrowest of which is drawn at 6.4 m.
        help="how far out to look for a lower road face when classifying a burial",
    )
    parser.add_argument(
        "--kerb-step-m",
        type=float,
        default=0.10,
        # Below `kerb_height_m` so a kerb is always caught, well above the
        # centimetres a ribbon's own mitre and trim interpolation move within one
        # metre. Not read from the config on purpose: `kerb_height_m` is the
        # pipeline's number, and taking it would make this tool agree with the
        # thing it grades.
        help="a road face this far below the cover means the cover is a raised edge",
    )
    parser.add_argument(
        "--accept-depth-m",
        type=float,
        default=0.010,
        # 🔴 **A tolerance on flat paint over a piecewise-linear road, not a
        # pipeline constant.** A marking triangle spans creases the road has and
        # it does not — a cap's fan edges, a ribbon's stations — so its chord
        # dips below the crown it crosses by millimetres however right its
        # vertices are. Measured on the corrected bundle: the residue is p50
        # **0.0027 m**, and closing it means subdividing paint at the road's own
        # creases rather than moving any height. A centimetre is where that stops
        # being a chord. Deliberately **not** read from any `lift_m`: this tool
        # must not take a number from the thing it grades.
        help="a burial shallower than this is the chord residue, not a wrong height",
    )
    parser.add_argument(
        "--accept-buried-share",
        type=float,
        default=0.005,
        # 🔴 **A real bar, not a ratchet, and it fails on the bundle this tool
        # was written against.** Paint below the *lowest* road face at its own
        # plan position has nothing to blame but its own height model: there is
        # no second surface, no kerb and no overlap in the way. The correct
        # value is zero and the half-percent is slack for a genuinely
        # coincident triangle, not room for a defect.
        #
        # ⚠️ It is deliberately **not** set against the first reading. The
        # `Q47` precedent warns about a bar tuned to its own data, and
        # `ground_clearance.py --accept-edges-over-travel` had to take that debt
        # because `Q24` is open and unassigned. This one does not: the
        # defect it grades has a fix, and the bar is what says so.
        help="fail above this share of a gated layer's triangles buried in the carriageway",
    )
    parser.add_argument(
        "--accept-coverage",
        type=float,
        default=0.90,
        # A layer mostly drawn where the shipped road has no face is not
        # evidence that the rest is fine — the denominator would be chosen by
        # the defect. `deck_error._Samples` makes this argument in full.
        help="fail below this share of a layer's triangles having any road under them",
    )
    parser.add_argument(
        "--layer",
        action="append",
        help="grade only this manifest key (repeatable; default: every declared layer)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    manifest, _ = load_bundle(args.generated, args.lod)
    log_bundle(manifest, args.lod)
    road = drawn_surface(args.generated, manifest)
    log.info("  %d near-horizontal faces in %s", len(road.corners), manifest["road_surface"])
    log.info("  road candidates taken within %.2f m of the paint's own height", args.road_within_m)

    bars = Bars.of(args)
    wanted = set(args.layer) if args.layer else None
    verdicts: list[LayerVerdict] = []
    for key, name, gated in _LAYERS:
        if wanted is not None and key not in wanted:
            continue
        asset = manifest.get(key)
        if asset is None:
            log.info("")
            log.info("  %-14s not declared in city.json — nothing to grade", key)
            continue
        # A prop layer names its stands under `<key>_placements` (`P5-4`).
        stands = manifest.get(f"{key}_placements")
        verdicts.append(
            survey(
                paint_triangles(
                    args.generated / asset,
                    args.generated / stands if stands else None,
                ),
                road,
                key=key,
                name=name,
                gated=gated,
                bars=bars,
            )
        )

    if not verdicts:
        raise SystemExit("no declared marking layer was graded — is --layer a manifest key?")

    log.info("")
    log.info("  paint against the road drawn under it, per layer:")
    log.info("")
    log.info(
        "    %-14s %-26s %8s %8s %9s %9s %9s %9s",
        "layer",
        "",
        "tris",
        "judged",
        "under hi",
        "on kerb",
        "in c'way",
        "deep",
    )
    for verdict in verdicts:
        gate = " *" if verdict.gated else "  "
        log.info(
            "    %-14s %-26s %8d %8d %8.1f%% %8.2f%% %8.2f%% %8.2f%%%s",
            verdict.key,
            verdict.name,
            verdict.triangles,
            verdict.judged,
            100.0 * verdict.share(verdict.under_highest),
            100.0 * verdict.share(verdict.on_raised_edge),
            100.0 * verdict.share(verdict.in_carriageway),
            100.0 * verdict.share(verdict.deep_in_carriageway),
            gate,
        )
    log.info("")
    log.info('    * gated on the "deep" column; the others are reported only')

    for verdict in verdicts:
        log.info("")
        log.info("  %s — %s", verdict.key, verdict.name)
        log.info(
            "    no road face under it: %d of %d triangles (%.3f m2), coverage %.1f%%",
            verdict.no_road,
            verdict.triangles,
            verdict.no_road_area_m2,
            100.0 * verdict.coverage,
        )
        log.info(
            "    under the HIGHEST road face: %d (%.1f%% of triangles, %.1f%% of paint area)",
            verdict.under_highest,
            100.0 * verdict.share(verdict.under_highest),
            100.0 * verdict.area_share(verdict.under_highest_area_m2),
        )
        _log_distribution("burial depth, m", verdict.depth_under_highest_m)
        log.info(
            "    under the LOWEST road face:  %d (%.1f%% of triangles, %.1f%% of paint area)",
            verdict.under_lowest,
            100.0 * verdict.share(verdict.under_lowest),
            100.0 * verdict.area_share(verdict.under_lowest_area_m2),
        )
        _log_distribution("burial depth, m", verdict.depth_under_lowest_m)
        log.info(
            "      split: %d on a raised edge (kerb top, carriageway beside it), "
            "%d inside the carriageway itself",
            verdict.on_raised_edge,
            verdict.in_carriageway,
        )
        _log_distribution("of those, depth m", verdict.depth_in_carriageway_m)
        log.info(
            "      of those, %d deeper than %.3f m — a wrong height rather than a chord",
            verdict.deep_in_carriageway,
            args.accept_depth_m,
        )
        log.info(
            "    more than one road face under it: %d (%.1f%%)",
            verdict.stacked,
            100.0 * verdict.share(verdict.stacked),
        )
        _log_distribution("highest minus lowest, m", verdict.stack_spread_m)

    # ⚠️ The two shares above are not a partition and must not be read as one:
    # every triangle under the lowest face is also under the highest. What their
    # *difference* names is paint that clears the carriageway and is covered by
    # a second surface drawn over it — the kerb lip and cap-overlap residue,
    # which is a `surface.py` question and not this bar's.
    log.info("")
    log.info(
        "  the gap between the two columns is paint that clears the carriageway and is "
        "covered by something else drawn there"
    )
    log.info("  (a kerb lip on an overlapping ribbon, or a cap over an arm) — reported, not gated")

    problems = []
    for verdict in verdicts:
        # ⚠️ **Coverage is gated on the same layers as burial, and not on every
        # layer.** `tramway` reads 67.4% here and is right to: `Q58` measured its
        # rails a median 3.26 m past the drawn kerb, so a third of them are
        # legitimately over no carriageway at all. Gating it would fail this tool
        # on a fact rather than on a defect, and the fix would be to widen the
        # bar — which is how a grader stops meaning anything.
        if not verdict.gated:
            continue
        if verdict.coverage < args.accept_coverage:
            problems.append(
                f"{verdict.key}: only {100.0 * verdict.coverage:.1f}% of its triangles have any "
                f"road under them, against {100.0 * args.accept_coverage:.1f}% — the rest is not "
                f"evidence of anything"
            )
        deep = verdict.share(verdict.deep_in_carriageway)
        if deep > args.accept_buried_share:
            problems.append(
                f"{verdict.key}: {100.0 * deep:.2f}% of its triangles are more than "
                f"{args.accept_depth_m:.3f} m below the carriageway they are drawn on, against "
                f"{100.0 * args.accept_buried_share:.2f}% — that paint is inside the road and "
                f"renders as nothing"
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
