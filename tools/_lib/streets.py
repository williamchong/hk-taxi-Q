"""Which edges a grader was asked about, and what the street is called.

Moved whole out of `carriageway_occupancy.py` (`P3-35f`, `Q133`), which thirteen
tools imported sideways for a street name. A move, and a moved name keeps its
name.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.polyline import Segments  # noqa: E402


def edges_label(edges: tuple[int, ...]) -> str:
    """Edge ids as one token, in the `e208` spelling every listing here prints.

    `_levels_label`'s reason: a refusal and a log line spelling the same set two
    ways costs the reader the match.
    """
    return ",".join(f"e{edge_id}" for edge_id in edges)


def edges_argument(text: str) -> tuple[int, ...]:
    """`--probe-edges e208,e306` as a tuple, in the spelling the listings print.

    A bare integer is accepted too, because half the tables in this repo print
    `e208` and the graph's own field is `208`, and a reader retyping one from
    the other should not have to know which.

    ⚠️ Order is **kept**, unlike `--levels`. The reader chose it, the report is
    a listing rather than a set, and sorting it would silently rearrange a
    comparison someone lined up deliberately.
    """
    edges: list[int] = []
    for piece in text.split(","):
        piece = piece.strip()
        if not piece:
            # `"".split(",")` is `[""]`, so this is also what catches an empty
            # flag — `_levels_argument` says more about why that matters.
            raise argparse.ArgumentTypeError("--probe-edges takes comma-separated edge ids")
        try:
            edge_id = int(piece.removeprefix("e"))
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"--probe-edges: '{piece}' is not an edge id — write e208 or 208"
            ) from None
        if edge_id not in edges:
            edges.append(edge_id)
    return tuple(edges)


def edge_levels(graph: dict[str, Any]) -> dict[int, int]:
    """Edge id to its elevation level, for the tools that judge a population.

    `road_names`' shape and `road_names`' reason: four tools were spelling this
    comprehension out, `tools/centreline_error.py` twice in one run, and it is
    `elevation_level`'s spelling in as many places as there are readers.

    🔴 **Indexed, never `.get` with a default.** `roads.py` writes the key on
    every edge and `read_graph` pins the schema, so a default cannot fire on
    valid input — and on invalid input it would quietly file an unknown edge
    into level 0, which is the *gated* population. `split_by_level` refuses a
    default for the same reason and `surface.py` refuses one over `offset_m`:
    an inconsistency here is a thing to hear about, not to default into a bar.

    ⚠️ **`pipeline/fence.py` keeps its own copy and must** — a pipeline stage
    cannot import `tools/`.
    """
    return {int(edge["id"]): int(edge["elevation_level"]) for edge in graph["edges"]}


def road_names(graph: dict[str, Any]) -> dict[int, str]:
    """Edge id to a street name, for a failure a reader can go and look at.

    English where the source has it, Chinese where it does not — many service
    roads carry only one, and "unnamed" for a slip road that carries neither is
    more use than an empty column.
    """
    names: dict[int, str] = {}
    for edge in graph["edges"]:
        name = edge.get("road_name") or {}
        chosen = name.get("en") or name.get("zh") if isinstance(name, dict) else None
        if chosen:
            names[int(edge["id"])] = str(chosen)
    return names


def street_namer(graph: dict[str, Any]) -> Callable[[float, float], str]:
    """A plan point to the street nearest it, for a row a reader can go and look at.

    ⚠️ **`Segments.nearest`, not the nearest polyline vertex.** Hand-rolled, this
    measured to vertices, so a long straight edge with two distant endpoints lost
    to a denser-vertexed side street and a box took the wrong name
    (`box_extent.py`). The shared join clamps to the segment. ⚠️ **Level 0 only,
    as every other caller passes** (`polyline.Segments.nearest`): a deck overhead
    is not the street a mark is painted on.
    """
    names = road_names(graph)
    level_0 = [
        edge
        for edge in graph["edges"]
        if int(edge["elevation_level"]) == 0 and int(edge["id"]) in names
    ]
    if not level_0:
        return lambda x, z: "unnamed"
    segments = Segments.of(level_0)
    return lambda x, z: names.get(segments.nearest(x, z).edge, "unnamed")
