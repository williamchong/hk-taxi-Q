"""`stop_marks:`.

One of `pipeline.config`'s blocks, imported through `pipeline.config`, which
re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import SourceLayer, _require, _source_layer, _tile_member
from pipeline.config_blocks.crossings import _codes, _positive

# The two paints, and the stretch of a module that is bare road.
WHITE, YELLOW, BARE = "white", "yellow", "none"
PAINTS = (WHITE, YELLOW)

# A mark's two roles, the same pair in every layer it is read from.
_ROLES = ("code", "level")
_SYMBOL_ROLES = ("code", "bearing", "level")


@dataclass(frozen=True)
class LegendSymbols:
    """Where TD files the same legend as a POINT and an angle, with no strokes.

    A legend is filed one way or the other, never both (0 of 1,205 `1047` points
    citywide lie inside a stroke legend). A point is stood with the region's own
    stroke legend of the same code as its glyph — `stopmarks.glyph_of`.

    `turn_deg` is the symbol's own frame against the traffic's: `1047`'s angle
    reads with the flow (43 of 45 within 3 deg, both regions) and `1175` /
    `1176`'s a quarter turn off it (5 of 5 at 88-91), so they take -90.
    """

    layer: SourceLayer
    turn_deg: float


@dataclass(frozen=True)
class StopMark:
    """One published stop or stand marking: where TD files it and how it is drawn.

    `module` is the repeat along the line, as `(paint, metres)` runs: `RM1048`
    is 1.0 m of white then 1.0 m of bare road, `RM1049` 1.0 m of yellow then
    1.0 m of white. One run of no length is a continuous line.

    ⚠️ **`legend` is a lettering code, and its width is the one authored
    dimension here.** TD surveys a legend as the strokes of a stick font, in
    place and to size, and publishes a letter height but no stroke width — so
    `width_m` on a legend row is `StopMarks.legend_stroke_m`, never the sheet's.
    """

    id: str
    layer: SourceLayer
    codes: frozenset[str]
    width_m: float
    module: tuple[tuple[str, float], ...]
    legend: bool
    symbols: LegendSymbols | None = None

    @property
    def continuous(self) -> bool:
        return len(self.module) == 1

    @property
    def period_m(self) -> float:
        return sum(length for _, length in self.module)


@dataclass(frozen=True)
class StopMarks:
    """Published bus stop, stand and tram stop paint, drawn by
    `pipeline/stopmarks.py` (`P3-89`, `P3-91`).

    **Read, not invented**: every line and every stroke is drawn where TD
    surveyed it. The line widths and modules are the sheet's
    (`CT174/51-5(1)F`, `CT174/51-5(2)G`); `legend_stroke_m` is authored.

    ⚠️ **No material here**, as `Crossings` says of itself: the two paints are
    the road marks' white and the box junctions' yellow, dispatched on the glTF
    material names in `pipeline/stopmarks.py`.
    """

    source: str
    member: str | None
    marks: tuple[StopMark, ...]
    legend_stroke_m: float
    lift_m: float
    max_offset_m: float
    cell_m: float

    @property
    def tiled(self) -> bool:
        return self.member is not None


def _module(body: dict[str, Any], where: str) -> tuple[tuple[str, float], ...]:
    """A mark's `paint:` (continuous) or its `module:` of `[paint, metres]` runs."""
    if ("paint" in body) == ("module" in body):
        raise ValueError(f"{where} declares exactly one of 'paint' and 'module'")
    if "paint" in body:
        paint = str(body["paint"])
        if paint not in PAINTS:
            raise ValueError(f"{where}:paint is {paint!r}; one of {PAINTS}")
        return ((paint, 0.0),)
    raw = body["module"]
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError(f"{where}:module must list two or more [paint, metres] runs, got {raw!r}")
    runs = []
    for run in raw:
        if not isinstance(run, list) or len(run) != 2:
            raise ValueError(f"{where}:module run must be [paint, metres], got {run!r}")
        paint, length = str(run[0]), float(run[1])
        if paint not in (*PAINTS, BARE) or length <= 0.0:
            raise ValueError(f"{where}:module run {run!r} is not a paint and a positive length")
        runs.append((paint, length))
    if all(paint == BARE for paint, _ in runs):
        raise ValueError(f"{where}:module paints nothing")
    return tuple(runs)


def _stop_marks(body: Any, where: str) -> StopMarks | None:
    """The optional stop-and-stand paint block. Absent, the region ships no
    `stopmarks.glb` and the manifest names none."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    stroke = _positive(body, "legend_stroke_m", where, "a stroke of no width draws nothing")
    raw = _require(body, "marks", where)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{where}:marks must be a non-empty list")
    marks: list[StopMark] = []
    for index, entry in enumerate(raw):
        mark_where = f"{where}:marks[{index}]"
        if not isinstance(entry, dict):
            raise ValueError(f"{mark_where} must be a mapping, got {entry!r}")
        legend = bool(entry.get("legend", False))
        symbols = entry.get("symbols")
        if symbols is not None and not legend:
            raise ValueError(f"{mark_where}:symbols is a legend's; a line has no glyph")
        if symbols is not None and not isinstance(symbols, dict):
            raise ValueError(f"{mark_where}:symbols must be a mapping, got {symbols!r}")
        if legend == ("line_width_m" in entry):
            raise ValueError(
                f"{mark_where}: a line declares 'line_width_m' and a legend takes "
                f"'legend_stroke_m'; exactly one applies"
            )
        marks.append(
            StopMark(
                id=str(_require(entry, "id", mark_where)),
                layer=_source_layer(entry, mark_where, _ROLES),
                codes=_codes(entry, "codes", mark_where),
                width_m=stroke
                if legend
                else _positive(entry, "line_width_m", mark_where, "a line of no width"),
                module=_module(entry, mark_where),
                legend=legend,
                symbols=None
                if symbols is None
                else LegendSymbols(
                    layer=_source_layer(symbols, f"{mark_where}:symbols", _SYMBOL_ROLES),
                    turn_deg=float(_require(symbols, "turn_deg", f"{mark_where}:symbols")),
                ),
            )
        )
    ids = [mark.id for mark in marks]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{where}:marks repeats an id: {ids}")
    claimed: dict[tuple[str, str], str] = {}
    for mark in marks:
        layers = [mark.layer.layer]
        if mark.symbols is not None:
            layers.append(mark.symbols.layer.layer)
        for layer in layers:
            for code in mark.codes:
                other = claimed.setdefault((layer, code), mark.id)
                if other != mark.id:
                    raise ValueError(
                        f"{where}: {layer} code {code} is claimed by '{other}' and "
                        f"'{mark.id}'; it would be drawn twice"
                    )

    return StopMarks(
        source=str(_require(body, "source", where)),
        member=_tile_member(body, where),
        marks=tuple(marks),
        legend_stroke_m=stroke,
        lift_m=_positive(
            body, "lift_m", where, "paint coplanar with the road it is painted on z-fights"
        ),
        max_offset_m=_positive(body, "max_offset_m", where, "every marking would be too far"),
        cell_m=_positive(body, "cell_m", where, "a cell of no size holds nothing"),
    )
