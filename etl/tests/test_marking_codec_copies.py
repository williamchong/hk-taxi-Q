"""The `TEXCOORD_1` marking codec has three copies, and this is the diff (`P5-11`).

`etl/pipeline/surface.py` packs it, `game/assets/shaders/road_markings.gdshader`
decodes it, and `game/tools/verify_road_surface.gd` grades it — three spellings
of one contract that `docs/ARCHITECTURE.md`'s channel table tie-breaks. A
constant edited in one is a road that draws wrong while every check passes,
so each copy is parsed off its own file here and held to the pipeline's value.

Every constant a copy declares must map to one the pipeline declares: an
unmapped copy is a field somebody added on one side only, which is the exact
failure this exists to catch — so the table is closed and a stray name fails.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pipeline import surface

ROOT = Path(__file__).resolve().parents[2]
SHADER = ROOT / "game" / "assets" / "shaders" / "road_markings.gdshader"
VERIFY = ROOT / "game" / "tools" / "verify_road_surface.gd"

# How each copy spells the pipeline's names. A value rather than a name maps a
# constant a copy derives differently — the shader masks the centre field by
# its span where the pipeline states its maximum.
SHADER_NAMES: dict[str, str | int] = {
    "MARKING_CLASS_CARRIAGEWAY": "MARKING_CLASS_CARRIAGEWAY",
    "MARKING_LANES": "MARKING_LANES",
    "MARKING_DIRECTION": "MARKING_DIRECTION",
    "MARKING_BUS_LANE": "MARKING_BUS_LANE",
    "MARKING_TRAM": "MARKING_TRAM",
    "MARKING_OFFSIDE_KERB": "MARKING_OFFSIDE_KERB",
    "MARKING_CENTRE": "MARKING_CENTRE",
    "MARKING_CENTRE_SPAN": surface.MARKING_CENTRE_MAX + 1,
    "MARKING_KERB_NEAR": "MARKING_KERB_NEAR",
    "MARKING_KERB_OFF": "MARKING_KERB_OFF",
    "MARKING_KERB_SPAN": "MARKING_KERB_SPAN",
    "MARKING_KERB_SINGLE": "MARKING_KERB_SINGLE",
    "MARKING_KERB_DOUBLE": "MARKING_KERB_DOUBLE",
    "DIRECTION_BOTH": surface.MARKING_DIRECTIONS[surface.BOTH],
}
VERIFY_NAMES: dict[str, str | int] = {
    "MARKING_LANES_FIELD": "MARKING_LANES",
    "MARKING_DIRECTION_FIELD": "MARKING_DIRECTION",
    "MARKING_BUS_FIELD": "MARKING_BUS_LANE",
    "MARKING_CLASS_CARRIAGEWAY": "MARKING_CLASS_CARRIAGEWAY",
    "MARKING_CLASS_CAP": "MARKING_CLASS_CAP",
    "MARKING_DIRECTION_MAX": max(surface.MARKING_DIRECTIONS.values()),
    "MARKING_CENTRE_FIELD": "MARKING_CENTRE",
    "MARKING_CENTRE_MAX": "MARKING_CENTRE_MAX",
    "MARKING_KERB_NEAR_FIELD": "MARKING_KERB_NEAR",
    "MARKING_KERB_OFF_FIELD": "MARKING_KERB_OFF",
    "MARKING_KERB_SPAN": "MARKING_KERB_SPAN",
}

_SHADER_CONST = re.compile(r"^const float ((?:MARKING|DIRECTION)_\w+) = ([0-9.]+);", re.M)
_VERIFY_CONST = re.compile(r"^const ((?:MARKING|DIRECTION)_\w+): float = ([0-9.]+)$", re.M)


def _declared(path: Path, pattern: re.Pattern[str]) -> dict[str, float]:
    found = {name: float(value) for name, value in pattern.findall(path.read_text())}
    assert found, f"{path} declares no codec constants — did the spelling move?"
    return found


def _expected(mapping: str | int) -> float:
    return float(getattr(surface, mapping) if isinstance(mapping, str) else mapping)


@pytest.mark.parametrize(
    ("path", "pattern", "names"),
    [(SHADER, _SHADER_CONST, SHADER_NAMES), (VERIFY, _VERIFY_CONST, VERIFY_NAMES)],
    ids=["shader", "verify_tool"],
)
def test_every_copy_agrees_with_the_pipeline(path, pattern, names) -> None:
    declared = _declared(path, pattern)
    stray = sorted(set(declared) - set(names))
    assert not stray, f"{path.name} declares codec constants this test does not map: {stray}"
    missing = sorted(set(names) - set(declared))
    assert not missing, f"{path.name} no longer declares {missing}"
    disagreeing = {
        name: (declared[name], _expected(names[name]))
        for name in names
        if declared[name] != _expected(names[name])
    }
    assert not disagreeing, f"{path.name} disagrees with surface.py: {disagreeing}"


def test_the_derived_ceiling_is_derived_on_every_side() -> None:
    """`MARKING_CODE_MAX` is computed from the top field in the pipeline and in
    the verify tool rather than written down; a literal on either side is a
    number to re-derive by hand the next time a field is added."""
    assert surface.MARKING_CODE_MAX == surface.MARKING_KERB_OFF * surface.MARKING_KERB_SPAN - 1
    text = VERIFY.read_text()
    assert "MARKING_CODE_MAX: float = MARKING_KERB_OFF_FIELD * MARKING_KERB_SPAN - 1.0" in text
