"""`road_text:`.

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    SourceLayer,
    _deck_codes,
    _require,
    _source_layer,
    _tile_member,
)
from pipeline.config_blocks.crossings import _positive

_ROLES = ("text", "bearing", "level")


@dataclass(frozen=True)
class RoadText:
    """Published road lettering — `CENTRAL 中區`, `KOWLOON 九龍`, `BEWARE OF PED
    小心行人` — drawn by `pipeline/roadtext.py` (`P3-21`, `Q262`).

    **The string, its place and its extent are TD's**; the letterforms are not.
    `DTAD_RD_MARK_ANNO` files each legend as the string and the rectangle the
    lettering fills, so the one authored thing is the face: `font_source`, a
    `sources:` entry, cut at `font_weight` and laid into the rectangle.

    - `flatten_em` is how far a flattened curve may stray from the outline, in
      em; the rectangle scales it to metres, so ~2.5 cm on a 2.5 m letter.
    - `line_gap_em` is the gap between the lines of a stacked string, before the
      rectangle scales the block to fit.
    - `sliver_m` is the paint's sliver bar: a piece `split` would cut thinner,
      or a triangle the builder would keep thinner, goes. Authored, not the
      other paint's 2 x `import_quantum_m`: that bar is a stroke's width here.
    - `refused` lists strings that are drafting notes rather than paint, matched
      after the markup is stripped, with the lines joined by a newline.
    - `deck_codes` are the publisher's `level` codes drawn on a deck (`Q134`'s
      rule): hosted among off-grade edges, stood on that level's drawn surface.
    """

    source: str
    member: str | None
    layer: SourceLayer
    deck_codes: tuple[str, ...]
    font_source: str
    font_weight: float
    flatten_em: float
    line_gap_em: float
    refused: frozenset[str]
    sliver_m: float
    lift_m: float
    max_offset_m: float
    bearing_tolerance_deg: float
    cell_m: float

    @property
    def tiled(self) -> bool:
        return self.member is not None


def _road_text(body: Any, where: str) -> RoadText | None:
    """The optional road-lettering block. Absent, the region ships no
    `roadtext.glb` and the manifest names none."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    refused = body.get("refused", [])
    if isinstance(refused, str) or not isinstance(refused, list):
        raise ValueError(f"{where}:refused must be a list of strings, got {refused!r}")
    tolerance = _positive(
        body, "bearing_tolerance_deg", where, "every legend would be off its road's axis"
    )
    if tolerance >= 90.0:
        raise ValueError(f"{where}:bearing_tolerance_deg is {tolerance}; at 90 it refuses nothing")
    line_gap = float(_require(body, "line_gap_em", where))
    if line_gap < 0.0:
        raise ValueError(f"{where}:line_gap_em is {line_gap}; the lines would overlap")

    return RoadText(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        layer=_source_layer(body, where, _ROLES),
        deck_codes=_deck_codes(body, where),
        font_source=str(_require(body, "font_source", where)),
        font_weight=_positive(body, "font_weight", where, "a face has no weight below 1"),
        flatten_em=_positive(body, "flatten_em", where, "a curve flattened to nothing never ends"),
        line_gap_em=line_gap,
        refused=frozenset(str(text) for text in refused),
        sliver_m=_positive(
            body, "sliver_m", where, "split cuts slivers onto the road's steep facets"
        ),
        lift_m=_positive(
            body, "lift_m", where, "paint coplanar with the road it is painted on z-fights"
        ),
        max_offset_m=_positive(body, "max_offset_m", where, "every legend would be too far"),
        bearing_tolerance_deg=tolerance,
        cell_m=_positive(body, "cell_m", where, "a cell of no size holds nothing"),
    )
