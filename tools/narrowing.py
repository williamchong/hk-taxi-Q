"""What `Q19`'s building half would measure if the ribbon were drawn narrower.

    .venv/bin/python tools/narrowing.py --city hong_kong --region wan_chai

`Q19` records that **narrowing would not clear** the edges where solid geometry
stands in the carriageway. That conclusion comes from re-measuring the eight
tightest edges inside the un-widened width — and once `Q51` split the starved
set by what actually blocks it, four of those eight turned out to be
`INFRASTRUCTURE`, which no width rule was ever going to reach. The claim about
*buildings* therefore rests on a sample of two. This sweeps the whole
population, at every widening factor `GAME_DESIGN.md` allows.

⚠️ **This is not a fifth grader, and must not be quoted as one.** The four
tools beside it read only the shipped bundle and share no code with the
pipeline, because a stage cannot mark its own work. This one does the opposite
on purpose: it **imports `pipeline.clearance` and reuses it whole**. The
question here is not whether the measurement is right — `carriageway_occupancy.py`
answers that — but what the same measurement would say at a different width, and
answering that with a second implementation would confound the two.

⚠️ **Narrowing cuts both ways, which is why this cannot be reasoned out on
paper.** The published figure is the *widest continuous clear run*. Narrowing
removes obstructions standing in the widened fringe, but it also clips the
corridor from the outside — and a street whose widest clear run lies against one
kerb loses that run first. Edges can get worse. The report calls out both
directions rather than counting only the wins.

⚠️ **Simulating a factor needs no rebuild**, and that is a fact about the
geometry rather than a shortcut. Buildings do not move when the ribbon narrows,
and `clearance.py` takes the deck height from the graph's own `polyline.y`, so
the only thing a narrower widening changes is the corridor that is measured
across. The factor is applied as `min(published_half, authored_half x factor)`,
which is exactly what lowering `widen_default` does: `config.widen_for` resolves
level, then structure, then the speed table, then the default — so a station
already at 1.0x (on structure, or off-grade) or at 1.3x (expressway) stays where
it is, and only the 1.6x population moves.

⚠️ **Valid only at 1.3x and above.** Below that the `min` above would narrow
expressways too, which `widen_by_min_speed_limit_kph` holds at 1.3 whatever the
default is. 1.3 is also `GAME_DESIGN.md`'s floor, so the sweep stops there.

⚠️ One approximation, recorded rather than hidden: inside `structure_taper_m`'s
15 m blend the real taper would run from the new factor down to 1.0, where the
`min` clips the existing 1.6-to-1.0 blend instead. It touches only stations
approaching structure — 1,070 m of level-0 centreline across 28 edges (`Q23`) —
and none of the `BUILDING` edges this exists to ask about.

**Two bars, because they are two questions.** One lane (`lane_width_m`, 3.20 m)
is whether traffic should be *routed* down an edge, which is what `Q51` gates on.
The car's own width is whether the *player* is stuck: `taxi.tscn` gives the body
a `BoxShape3D` of 1.8 m, and since `Q50` the wheels are raycasts with no collider
of their own, so 1.8 m is the whole car.

⚠️ **An edge's class is attributed at the shipped width, and reused for every
narrower one.** An edge whose dominant blocker changes as the corridor clips
inward is therefore filed under the class that bound it at 1.60x. The totals are
unaffected; only which column a starved edge appears in.

⚠️ **Do not fuse the three class sweeps into the unrestricted one.** The union of
the per-class blocked sets looks like the baseline and is not: `class_meshes`
keeps a triangle only when all three corners agree on a class, so a seam
triangle spanning a wall and the thing standing against it belongs to none of
them. Taking the union would drop it and under-report blockage, silently, in the
direction this whole family of tools exists to be careful about.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from carriageway_occupancy import road_names  # noqa: E402
from pipeline import gltf  # noqa: E402
from pipeline.clearance import (  # noqa: E402
    CLEARANCE_NAME,
    CLEARANCE_SCHEMA,
    NOT_MEASURED,
    _Sections,
    ground_colour,
    landmark_meshes,
    measure,
    occupy,
    open_region,
    tile_meshes,
    walk,
    wears,
)
from pipeline.config import CityConfig, load_city  # noqa: E402
from pipeline.documents import read_document  # noqa: E402

log = logging.getLogger(__name__)

# The widening factors to price, widest first so the first column is the shipped
# city and every later one is a proposal against it. `GAME_DESIGN.md` fixes the
# range at 1.3-1.8 and `widen_default` is 1.6, so this is the whole of what is
# available downward.
FACTORS: tuple[float, ...] = (1.60, 1.55, 1.50, 1.45, 1.40, 1.35, 1.30)

# The taxi's body collider, in metres — `game/scenes/vehicle/taxi.tscn`. A
# default rather than a hard-coded bar, so a wider car is a flag rather than an
# edit.
CAR_WIDTH_M = 1.8

# `BUILDING` is the complement of every class the config gives a flat material
# to, exactly as `carriageway_occupancy.py` derives it — buildings take
# height-banded colours and cannot be selected positively. `INFRASTRUCTURE` is
# not named here because it is the city's to name (`buildings.structure_class`).
LANDMARK = "LANDMARK"
BUILDING = "BUILDING"

# An edge no class blocks: its clearance is the carriageway that was drawn, and
# narrowing is the only thing that can have moved it. Named rather than left to
# a tie-break, because "a building stands in it" and "the ribbon is just narrow"
# are the two answers this sweep exists to tell apart.
UNOBSTRUCTED = "none — drawn narrow"


def classes(city: CityConfig) -> tuple[str, ...]:
    """The three occupier classes, in report order."""
    structure = city.buildings.structure_class
    if not structure:
        # The sibling grader refuses the same way, and for the same reason: with
        # no structure class there is nothing to tell a flyover pier from a wall.
        raise SystemExit(f"city {city.id!r} declares no buildings.structure_class")
    return (structure, BUILDING, LANDMARK)


def scaled(drawn: dict[int, dict], authored_half: dict[int, float], factor: float) -> dict:
    """The carriageway table as `widen_default = factor` would have drawn it."""
    table = {}
    for edge_id, entry in drawn.items():
        if edge_id not in authored_half:
            # Defaulting would clamp every station to zero and drop the edge from
            # the table without a word — a silent hole in a published sweep.
            raise SystemExit(
                f"edge {edge_id} is in the carriageway table and not in the graph; "
                "the two documents are from different runs"
            )
        limit = authored_half[edge_id] * factor
        table[edge_id] = {
            **entry,
            "half_width_m": [min(half, limit) for half in entry["half_width_m"]],
        }
    return table


def moved(
    before: dict[int, float], after: dict[int, float], bar: float
) -> tuple[list[int], list[int]]:
    """Edges that cross `bar` in each direction between two factors.

    Both directions, because narrowing is not only a way to clear an edge: the
    published figure is the widest continuous clear run, and clipping the
    corridor trims a run that lay against one kerb.
    """
    cleared, lost = [], []
    for edge_id in sorted(set(before) & set(after)):
        was, now = before[edge_id], after[edge_id]
        if was < bar <= now:
            cleared.append(edge_id)
        elif now < bar <= was:
            lost.append(edge_id)
    return cleared, lost


def _picked(mesh: gltf.MeshData, keep: np.ndarray) -> gltf.MeshData | None:
    """One class's triangles of a merged tile, or `None` if it has none."""
    if not keep.any():
        return None
    return replace(mesh, triangles=mesh.triangles[keep])


def class_meshes(meshes: list[gltf.MeshData], city: CityConfig, name: str) -> list[gltf.MeshData]:
    """The triangles of one class, out of tiles that merged every class into one.

    By vertex colour, because that is all a merged primitive keeps.

    ⚠️ **All three of a triangle's corners must wear the class.** A triangle
    spanning two of them is a weld artefact rather than a surface. The rule is
    also in `pipeline/clearance.py` and `tools/deck_error.py`, whose docstring
    used to claim it lived there alone — three places for it to stop being true.
    """
    style = city.buildings
    if name != BUILDING and name not in style.class_materials:
        raise SystemExit(
            f"{name!r} is neither BUILDING nor a class_materials entry of {city.id}, "
            "so there is no colour to select it by"
        )
    picked = []
    for mesh in meshes:
        if mesh.colours is None:
            continue
        if name == BUILDING:
            # Every entry, not just structure and ground: a third flat-material
            # class left out of the subtraction would be counted as a building.
            worn = np.zeros(len(mesh.colours), dtype=bool)
            for class_id, material in style.class_materials.items():
                worn = worn | wears(mesh.colours, material.colour, style.jitter_for(class_id))
            keep = ~worn
        else:
            material = style.class_materials[name]
            keep = wears(mesh.colours, material.colour, style.jitter_for(name))
        chosen = _picked(mesh, keep[mesh.triangles].all(axis=1))
        if chosen is not None:
            picked.append(chosen)
    return picked


def unobstructed(graph: dict, drawn: dict[int, dict]) -> dict[int, float]:
    """Each edge's clearance with nothing standing in the road at all.

    The reference the class sweeps are read against. Without it a tie between
    the three classes — which is what an unblocked edge produces, since `measure`
    clamps a clear cross-section to the carriageway drawn over it — falls through
    to whichever key came first, and 427 of the region's 737 edges would be
    reported as blocked by `INFRASTRUCTURE` when nothing blocks them at all.
    """
    corridor, report = walk(graph, drawn)
    measure(corridor, np.zeros(len(corridor), dtype=bool), report)
    return report.tightest()


def sweep(
    city: CityConfig,
    graph: dict,
    drawn: dict[int, dict],
    tiles: list[Path],
    heroes: list[gltf.MeshData],
    *,
    only: str | None = None,
) -> dict[int, float]:
    """One measurement pass, at whatever widths `drawn` carries.

    `only` restricts the occupiers to a single class, which is how an edge's
    blockage is attributed: the class that starves it furthest on its own is the
    class standing in it.
    """
    ground, jitter = ground_colour(city)
    corridor, report = walk(graph, drawn)
    sections = _Sections(corridor)
    if only != LANDMARK:
        for path in tiles:
            meshes = gltf.read_glb(path)
            occupy(
                sections,
                meshes if only is None else class_meshes(meshes, city, only),
                ground,
                jitter,
            )
    if only in (None, LANDMARK):
        occupy(sections, heroes, ground, jitter)
    measure(corridor, sections.blocked, report)
    return report.tightest()


def attribute(
    city: CityConfig,
    graph: dict,
    drawn: dict[int, dict],
    tiles: list[Path],
    heroes: list[gltf.MeshData],
) -> dict[int, str]:
    """Which class each edge's blockage belongs to, at the shipped width.

    An edge two classes both block reads as the tighter of the two, which is the
    honest answer for a report about what a width change could reach: clearing
    one of them still leaves the other standing.
    """
    open_width = unobstructed(graph, drawn)
    per_class = {
        name: sweep(city, graph, drawn, tiles, heroes, only=name) for name in classes(city)
    }
    return {
        edge_id: owner({name: widths[edge_id] for name, widths in per_class.items()}, clear)
        for edge_id, clear in open_width.items()
    }


def owner(per_class: dict[str, float], clear: float) -> str:
    """Which class one edge's blockage belongs to, given each class alone.

    ⚠️ **Strictly narrower than the unobstructed corridor.** An edge nothing
    blocks returns the same width from all three sweeps — `measure` clamps a
    clear cross-section to the carriageway drawn over it — so a plain `min` over
    the three ties, falls through to whichever key came first, and files 427 of
    the region's 737 edges under `INFRASTRUCTURE` with nothing standing in them.
    """
    blocking = {name: width for name, width in per_class.items() if width < clear}
    return min(blocking, key=lambda name: blocking[name]) if blocking else UNOBSTRUCTED


def check_baseline(out_dir: Path, city_id: str, region_id: str, baseline: dict[int, float]) -> None:
    """Refuse to publish a sweep whose first column is not the shipped city.

    The whole table is read across its factors, and the 1.60x column is the only
    one that can be checked against something — `clearance.json`, written by the
    stage at the width the bundle was actually drawn at. If the two disagree the
    factor simulation is wrong and no other column means anything, so this is a
    precondition rather than a diagnostic.
    """
    rebuild = f"python -m pipeline --city {city_id} --region {region_id}"
    shipped = read_document(out_dir / CLEARANCE_NAME, CLEARANCE_SCHEMA, rebuild)
    published = {}
    for entry in shipped["clearance"]:
        widths = [width for width in entry["clear_width_m"] if width != NOT_MEASURED]
        if widths:
            published[int(entry["edge"])] = min(widths)

    if set(published) != set(baseline):
        raise SystemExit(
            f"{CLEARANCE_NAME} measured {len(published)} edges and the sweep's baseline "
            f"{len(baseline)}; rebuild the region"
        )
    disagree = [edge for edge, width in published.items() if abs(width - baseline[edge]) > 1e-9]
    if disagree:
        raise SystemExit(
            f"the 1.60x column disagrees with {CLEARANCE_NAME} on {len(disagree)} edges "
            f"(first: e{disagree[0]}); the factor simulation is wrong"
        )
    log.info("  baseline reproduces %s on all %d edges", CLEARANCE_NAME, len(published))


def _report_edges(
    watched: list[int],
    results: dict[float, dict[int, float]],
    owners: dict[int, str],
    names: dict[int, str],
) -> None:
    baseline = results[FACTORS[0]]
    log.info("")
    log.info(
        "  clear corridor per edge, by widening factor — %d ever below one lane:", len(watched)
    )
    log.info("    %-6s %-18s %s", "edge", "blocked by", "".join(f"{f:>7.2f}x" for f in FACTORS))
    for edge_id in sorted(watched, key=lambda e: baseline[e]):
        row = "".join(f"{results[factor][edge_id]:>8.2f}" for factor in FACTORS)
        log.info(
            "    e%-5d %-18s %s  %s",
            edge_id,
            owners[edge_id],
            row,
            names.get(edge_id, "unnamed"),
        )


def _report_bar(
    bar: float,
    label: str,
    results: dict[float, dict[int, float]],
    owners: dict[int, str],
    order: tuple[str, ...],
) -> None:
    baseline = results[FACTORS[0]]
    log.info("")
    log.info("  edges below %.2f m (%s), by class:", bar, label)
    log.info(
        "    %-8s %6s %s   %s",
        "factor",
        "total",
        "".join(f"{name:>18}" for name in order),
        "vs the shipped 1.60x",
    )
    for factor in FACTORS:
        starved = [edge_id for edge_id, width in results[factor].items() if width < bar]
        counted = Counter(owners[edge_id] for edge_id in starved)
        cleared, lost = moved(baseline, results[factor], bar)
        log.info(
            "    %-8s %6d %s   %s",
            f"{factor:.2f}x",
            len(starved),
            "".join(f"{counted.get(name, 0):>18d}" for name in order),
            "" if factor == FACTORS[0] else f"{len(cleared)} cleared, {len(lost)} lost",
        )
        if lost:
            # Named, never merely counted. An edge narrowing *breaks* is the
            # finding this sweep exists to be able to see.
            log.info("             worse: %s", ", ".join(f"e{edge}" for edge in lost[:8]))
        # The columns must sum to the total, or an edge is filed under a class
        # the header does not print and the table quietly stops adding up.
        assert sum(counted.get(name, 0) for name in order) + counted.get(UNOBSTRUCTED, 0) == len(
            starved
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--car-width-m",
        type=float,
        default=CAR_WIDTH_M,
        help="the player's own width, from taxi.tscn (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)
    order = classes(city)
    log.info("%s / %s", city.name, region.name)

    out_dir, graph, drawn, buildings = open_region(city, args.region)
    authored_half = {int(edge["id"]): float(edge["width_m"]) / 2.0 for edge in graph["edges"]}
    tiles = tile_meshes(out_dir, buildings)
    heroes = landmark_meshes(city, args.region, out_dir)
    names = road_names(graph)
    lane_m = float(city.roads.lane_width_m)

    log.info(
        "  sweeping %d factors over %d tiles and %d hero meshes; bars %.2f m (one lane) "
        "and %.2f m (the car)",
        len(FACTORS),
        len(tiles),
        len(heroes),
        lane_m,
        args.car_width_m,
    )

    tables = {factor: scaled(drawn, authored_half, factor) for factor in FACTORS}
    results = {factor: sweep(city, graph, table, tiles, heroes) for factor, table in tables.items()}
    baseline = results[FACTORS[0]]
    # Every factor must measure the same population, or a column is quietly
    # comparing different edges. It holds by construction — the measured set
    # comes from the trims and the polylines, neither of which a width touches —
    # and is asserted because every table below reads across the factors.
    for factor, widths in results.items():
        if set(widths) != set(baseline):
            raise SystemExit(f"{factor:.2f}x measured a different set of edges from the baseline")

    check_baseline(out_dir, city.id, args.region, baseline)
    owners = attribute(city, graph, tables[FACTORS[0]], tiles, heroes)
    watched = sorted({e for widths in results.values() for e, w in widths.items() if w < lane_m})

    _report_edges(watched, results, owners, names)
    for bar, label in ((lane_m, "one lane"), (args.car_width_m, "the car")):
        _report_bar(bar, label, results, owners, order)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
