"""The kerbside restrictions, graded against a second source that drew them (`Q56`).

`tools/kerbside_error.py` grades the half of the path that runs from a published
run to a pixel, and says so: its truth side is `roadgraph.json`, so a restriction
attached to the wrong centreline is agreed with rather than caught. **This is the
other half.** It takes the Transport Department's Traffic Aids Drawings — a
separate dataset, digitised from the drawing rather than from the restriction
register — runs it through `pipeline/kerbside.py`'s own join, and diffs the two
answers cell by cell.

**What only this can see.** The kind. `NSR.TIME_ZONE` says a restriction runs 24
hours and the city file turns that into a double yellow; nothing downstream can
tell whether that mapping is right, because every consumer takes the kind on
trust and renders it. The drawings carry the marking code itself — `RM1040` is a
double yellow, `RM1041` a single — so the two sources reach a kind by routes with
nothing in common, and a disagreement is a real one.

**Why it runs the same join instead of writing a second one.** A second join
would grade the join, which sounds better and is not: two implementations
disagreeing tells you one of them is wrong and never which. Feeding a second
*source* through one join isolates the source, which is the question worth
asking — `NSR` is the only thing in the bundle asserting where a car may not
stop, and until now nothing had ever checked it.

⚠️ **This does not cover the side convention, and must not be quoted as if it
did.** Both sources are digitised at the kerb and both reach a side through
`kerbside._Segments`, so flipping that expression mirrors *both* answers and
this tool reports perfect agreement on a mirrored city. `tests/test_kerbside.py`
pins the side against `surface.mitres` for exactly that reason. What the
`opposite` column here catches is narrower and still worth having: the two
sources putting the same restriction on **different kerbs of the same edge**.

⚠️ **It grades the published `roadgraph.json`, not a fresh build.** The point is
to check what shipped. A stale graph is a stale answer, so the schema version is
checked and the region's own out dir is read rather than the copy under
`game/assets/generated/`.

⚠️ **Not part of `check.sh`.** It needs a 218 MB source that no build reads and
a built region that `check.sh` does not require. Like `skidpad.sh` it grades
rather than checks: the number to act on is the table, and a gap that grows is a
finding to go and look at, never a bar to retune against.

Fetch the source once:
  .venv/bin/python -m pipeline.fetch --city hong_kong --region wan_chai \
      --only traffic_aids_drawings_gdb

Run:  .venv/bin/python tools/kerbside_source_audit.py --city hong_kong --region wan_chai
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from pipeline import gdb, kerbside  # noqa: E402
from pipeline.config import CityConfig, KerbsideAudit, SourceLayer, load_city  # noqa: E402
from pipeline.fetch import cached_source  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402

# The synthetic vehicle-type codes the drawing layer is given before it is fed to
# the pipeline's join. `_lines` filters on this column and reports the metres it
# drops, so giving an unmapped marking code its own value buys the refusal
# accounting for free rather than dropping those features silently upstream.
_PAINTED = 1
_UNMAPPED = 0

# Cells whose two sources disagree, listed longest first. A cap rather than the
# whole table because the useful output is "which street, and is it one street or
# forty" — the totals above it are what the answer is read off.
_WORST = 12


@dataclass
class _Cell:
    """What each source says about one metre of one side of one edge."""

    published: str | None = None
    drawing: str | None = None


@dataclass
class Report:
    """Metres, by what the two sources did with them."""

    # Metres both sources restrict and agree on the kind of. The ones they
    # disagree about are in `kinds`, and `both` is the two summed back out.
    agreed: float = 0.0
    # One source only. Named for the source rather than for "missed" and "extra"
    # because neither is the truth: the drawing is a second opinion, not a
    # reference, and a metre only it carries is a question rather than a defect.
    published_only: float = 0.0
    drawing_only: float = 0.0
    # Metres where the drawing agrees an edge is restricted but puts it on the
    # other kerb, and neither source has anything on the side the other used.
    opposite: float = 0.0
    # Kind disagreements, keyed `(published kind, drawing kind)`.
    kinds: dict[tuple[str, str], float] = field(default_factory=dict)
    # Per road name, the metres the two sources disagree about at all.
    by_road: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    # Drawing metres whose marking code the city file maps to no kind. Reported
    # rather than dropped: a publisher adding a code is exactly the change that
    # would otherwise shrink the drawing's coverage and read as agreement.
    unmapped: float = 0.0
    # Features the drawing layer holds in region, and how many carried a code.
    features_read: int = 0
    features_mapped: int = 0

    @property
    def both(self) -> float:
        """Metres both sources restrict, summed back out of the two ways they land.

        Derived rather than carried alongside them, for the reason
        `kerbside_error.Report.restricted` gives: a total that can disagree with
        the table printed under it is a total nobody can act on.
        """
        return self.agreed + sum(self.kinds.values())

    @property
    def union(self) -> float:
        return self.both + self.published_only + self.drawing_only

    @property
    def coverage(self) -> float:
        """Share of the union both sources agree is restricted, kind aside."""
        return self.both / self.union if self.union else 0.0

    @property
    def kind_agreement(self) -> float:
        return self.agreed / self.both if self.both else 0.0


def audit(city: CityConfig, region_id: str, *, sources_root: Path | None = None) -> Report:
    """Diff the published restrictions against the ones the drawings imply."""
    spec = city.roads.kerbside
    audit_spec = spec.audit if spec is not None else None
    if spec is None or audit_spec is None:
        raise SystemExit(
            f"city '{city.id}' declares no kerbside audit source; "
            f"there is nothing here to grade it against"
        )

    path = city.out_dir(region_id) / ROADGRAPH_NAME
    graph = read_graph(path, city.id, region_id)
    # `ROADGRAPH_SCHEMA` did not move when `P3-13` added this key, so a graph
    # built before it passes the version check and then dies on a `KeyError`
    # halfway through. The sibling guards the same case the same way.
    if not graph["edges"] or "kerbside" not in graph["edges"][0]:
        raise SystemExit(f"{path} publishes no kerbside runs")
    report = Report()

    cells: dict[tuple[int, str], dict[int, _Cell]] = defaultdict(dict)
    # Shared with `carriageway_occupancy` rather than re-derived: both tools
    # report per edge and both need the same "English, else Chinese, else
    # unnamed" fallback, and two spellings of it would drift.
    names = road_names(graph)
    tracks: list[tuple[int, np.ndarray]] = []
    for edge in graph["edges"]:
        polyline = np.asarray(edge["polyline"], dtype=np.float64)
        if edge["elevation_level"] == 0 and len(polyline) > 1:
            # The same offer `roads._kerbside` makes, rebuilt from what shipped
            # rather than from a fresh build: an audit that re-derived the
            # candidate set could grade a graph the game does not have.
            tracks.append((edge["id"], polyline))
        for run in edge["kerbside"]:
            for index in _cell_range(run["from_m"], run["to_m"], spec.sample_m):
                cells[(edge["id"], run["side"])].setdefault(index, _Cell()).published = run["kind"]

    drawn = kerbside.build(
        _as_restriction_layer(city, audit_spec, region_id, sources_root=sources_root),
        _as_restriction_spec(spec, audit_spec),
        city.game_transform(region_id),
        city.region_high(region_id),
        tracks,
    )
    report.unmapped = drawn.metres_refused.get(_UNMAPPED, 0.0)
    report.features_read = drawn.features_read
    report.features_mapped = drawn.features_painted
    for run in drawn.restrictions:
        for index in _cell_range(run.start_m, run.end_m, spec.sample_m):
            cells[(run.edge, run.side)].setdefault(index, _Cell()).drawing = run.kind

    _tally(cells, spec.sample_m, names, report)
    return report


def _cell_range(start_m: float, end_m: float, sample_m: float) -> range:
    """The cells a run covers, in the pitch the join itself published it at.

    Both sides are rasterised at `sample_m` rather than compared as intervals
    because the runs come out of the same sampler and are already multiples of
    it — so the raster is lossless here, and it makes "the same metre" a
    dictionary key instead of an interval intersection with its own rounding.
    """
    return range(round(start_m / sample_m), round(end_m / sample_m))


def _tally(
    cells: dict[tuple[int, str], dict[int, _Cell]],
    sample_m: float,
    names: dict[int, str],
    report: Report,
) -> None:
    """Turn the per-cell record into metres, and find the opposite-kerb metres."""
    for (edge, side), found in cells.items():
        if side not in kerbside.SIDES:
            # The sibling refuses the same `else` for the same reason: a third
            # spelling is a side convention that has drifted, and absorbing it
            # would leave `opposite` — the one column nothing else grades —
            # quietly meaningless.
            raise ValueError(f"unknown side {side!r}, expected one of {', '.join(kerbside.SIDES)}")
        across_from = kerbside.OFFSIDE if side == kerbside.NEARSIDE else kerbside.NEARSIDE
        # `.get` rather than `cells[...]`: `cells` is a `defaultdict` being
        # iterated here, so a subscript would insert the far side mid-loop and
        # raise.
        other = cells.get((edge, across_from), {})
        road = names.get(edge, f"edge {edge}")
        for index, cell in found.items():
            if cell.published is not None and cell.drawing is not None:
                if cell.published == cell.drawing:
                    report.agreed += sample_m
                else:
                    key = (cell.published, cell.drawing)
                    report.kinds[key] = report.kinds.get(key, 0.0) + sample_m
                    report.by_road[road] += sample_m
                continue

            report.by_road[road] += sample_m
            across = other.get(index)
            if cell.published is not None:
                report.published_only += sample_m
                if across is not None and across.drawing is not None and across.published is None:
                    report.opposite += sample_m
            else:
                report.drawing_only += sample_m


def _kind_codes(audit_spec: KerbsideAudit) -> dict[str, int]:
    """The synthetic time-zone code each drawing kind is carried as.

    ⚠️ **One derivation, because the two halves must be exact inverses.**
    `_as_restriction_layer` writes these codes into the column and
    `_as_restriction_spec` builds the table `kerbside.build` reads them back
    through. Spelled twice and drifted apart — `sorted` is load-bearing, since
    iterating a `set` of strings is hash-randomised — the codec inverts and
    every double is graded as a single. That prints as a full directional
    disagreement table, which is the shape of a source finding, so it would be
    read as the answer rather than as a bug.
    """
    return {kind: code for code, kind in enumerate(sorted(set(audit_spec.kinds.values())))}


def _as_restriction_spec(
    spec: kerbside.KerbsideRestrictions, audit_spec: KerbsideAudit
) -> kerbside.KerbsideRestrictions:
    """The city's own join, pointed at the drawing's columns and codes.

    Every sampling number is carried over unchanged — pitch, bridge, minimum
    run, offset guard. That is what makes the diff a difference between
    *sources*: change one of these and the two answers would differ because they
    were measured differently, which is the one thing this tool must not do.
    """
    kinds = {code: kind for kind, code in _kind_codes(audit_spec).items()}
    return replace(
        spec,
        # The roles map onto themselves: `_as_restriction_layer` writes the
        # synthesised columns under the role names, because there is no
        # publisher schema left to indirect through at this point.
        layer=SourceLayer(
            layer=audit_spec.layer.layer,
            fields={"vehicle_type": "vehicle_type", "time_zone": "time_zone"},
        ),
        painted_vehicle_types=frozenset({_PAINTED}),
        kinds=kinds,
    )


def _as_restriction_layer(
    city: CityConfig,
    audit_spec: KerbsideAudit,
    region_id: str,
    *,
    sources_root: Path | None,
) -> gdb.Layer:
    """The drawing layer, wearing the two columns `pipeline/kerbside.py` reads.

    The join asks a layer for a vehicle type and a time zone. The drawings carry
    neither — they carry a marking code, which is a *better* answer to the same
    question and a differently shaped one. Rather than teach the pipeline a
    second schema for a file it never reads, the translation happens here: the
    marking code becomes a synthetic time zone, and "is this a painted line"
    becomes a synthetic vehicle type. The geometry is untouched.
    """
    path = cached_source(city, audit_spec.source, root=sources_root)
    layer = gdb.read_layer(
        path,
        audit_spec.layer.layer,
        columns=audit_spec.layer.columns,
        bbox=city.projected_bounds(region_id).bbox,
        expect_crs=city.projected_crs,
    )
    codes = layer.column(audit_spec.layer.field("line_type"))
    order = _kind_codes(audit_spec)

    vehicle_type = np.empty(len(codes), dtype=np.int64)
    time_zone = np.zeros(len(codes), dtype=np.int64)
    for row, code in enumerate(codes):
        kind = audit_spec.kinds.get(str(code))
        vehicle_type[row] = _PAINTED if kind is not None else _UNMAPPED
        if kind is not None:
            time_zone[row] = order[kind]

    return replace(layer, columns={"vehicle_type": vehicle_type, "time_zone": time_zone})


def render(report: Report, sample_m: float) -> str:
    """The table, and nothing that is not measured."""
    lines = [
        f"drawing features in region: {report.features_read} "
        f"({report.features_mapped} carried a mapped marking code)",
        f"drawing metres with no mapped code: {report.unmapped:,.0f}",
        "",
        f"{'both sources':<22}{report.both:>12,.0f} m   {report.coverage:>6.1%} of the union",
        f"{'published only':<22}{report.published_only:>12,.0f} m",
        f"{'drawing only':<22}{report.drawing_only:>12,.0f} m",
        f"{'union':<22}{report.union:>12,.0f} m",
        "",
        f"{'kind agreed':<22}{report.agreed:>12,.0f} m   "
        f"{report.kind_agreement:>6.1%} of the metres both carry",
    ]
    for (published, drawing), metres in sorted(report.kinds.items(), key=lambda item: -item[1]):
        lines.append(f"  published {published:<7} drawing {drawing:<7} {metres:>10,.0f} m")
    lines += [
        "",
        f"{'opposite kerb':<22}{report.opposite:>12,.0f} m   published one side, drawn the other",
        "",
        f"disagreement by road (longest {_WORST}, at {sample_m:g} m resolution):",
    ]
    for road, metres in sorted(report.by_road.items(), key=lambda item: -item[1])[:_WORST]:
        lines.append(f"  {road:<44}{metres:>10,.0f} m")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_city(args.city)
    report = audit(city, args.region, sources_root=args.sources_root)
    assert city.roads.kerbside is not None  # audit() exits without one
    print(render(report, city.roads.kerbside.sample_m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
