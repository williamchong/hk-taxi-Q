"""What every block's reader shares.

A required key, a role map, a measurement, a colour, a source layer.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Material:
    """A real-world surface the city is built out of, and the colour it ships as.

    ⚠️ **The colour and the albedo belong together, and neither belongs on
    `HeightBand`.** Holding them there makes the *shape* of the schema assert that
    material is a function of height — a claim nobody would write down and the
    data refuses: on the 2,171-building photo survey, height explains **0.9%** of
    facade `L*` once log pixel count is controlled. `Q34` has the rest of the
    measurement and the worked example.

    Naming the material instead makes the claim attach to the thing it is about,
    and makes it **portable** (CLAUDE.md hard rule 3): concrete is concrete in the
    second city, where a height-to-material mapping would have to be re-derived
    from scratch.

    ⚠️ **Every colour the city ships is declared here and nowhere else.** That is
    what makes `_check_reflectance` total — see its docstring, and
    `_check_every_material_is_used` for the other direction.
    """

    # The key this material is declared under. Carried on the object so an error
    # raised deep in a consumer can name it without threading the key along.
    name: str
    colour: tuple[int, int, int]
    # Real-world diffuse albedo, as a percentage. See `_check_reflectance` for
    # what it is checked against and why it is required.
    reflectance: float
    # Where that number comes from, in free text. Required, and deliberately not
    # validated: the point is that somebody had to type an answer, including
    # "back-derived, not cited" where that is the truth. An unsourced albedo is
    # how the palette drifted before `Q33`.
    source: str
    # The published range `source` names, as `(low, high)` percentages.
    #
    # 🔴 **Required, and required because of `P5-28c`.** While the anchor lived
    # in this file the colour was `reflectance x exposure_anchor` and the check
    # had two independent things to compare. Un-baked, the colour *is* the
    # reflectance, so `luminance(colour) == reflectance` is true by construction
    # and checking it alone is `Q72`'s tautology: a rule that reads as enforced
    # and cannot fail. This is the third thing. It is the numeric half of
    # `source`, which was already required and is prose — so nothing new had to
    # be *decided* for any of the fifteen entries, only transcribed.
    #
    # ⚠️ **Not validated against `source`'s text**, deliberately: parsing a range
    # out of free prose would make the sentence the schema and the transcription
    # unreviewable. What is checked is that `reflectance` lies inside it.
    bounds: tuple[float, float]


class _MaterialTable:
    """The declared materials, plus which of them anything actually referenced.

    Load-scoped and mutable, unlike everything else here. `get` is the *only* way
    a material reaches a config object, so usage is recorded by the act of using
    it — a consumer added later is counted without anyone remembering to add it
    to a list.

    That is the whole reason this is a class rather than a dict. A hand-written
    enumeration of reference sites in `load_config` would be a second copy of the
    join, and the copy that drifts is the one that quietly stops catching
    anything — which is exactly how `class_reflectance` could have failed.
    """

    def __init__(self, declared: dict[str, Material]) -> None:
        self.declared = declared
        self.used: set[str] = set()

    def get(self, name: str, where: str) -> Material:
        material = self.declared.get(name)
        if material is None:
            raise ValueError(
                f"{where} names material {name!r}, which materials: does not declare. "
                f"Declared: {', '.join(sorted(self.declared)) or '(none)'}"
            )
        self.used.add(name)
        return material


@dataclass(frozen=True)
class SourceLayer:
    """One layer of a source dataset, and what the pipeline calls its fields.

    `fields` maps a **role** the pipeline asks for onto the publisher's own
    column name. That indirection is the whole point: `roads.py` may know that
    a centreline has a travel direction, and may not know that Hong Kong's
    Transport Department spells it `TRAVEL_DIRECTION` (CLAUDE.md hard rule 3).
    """

    layer: str
    fields: dict[str, str]

    def field(self, role: str) -> str:
        return _field(self.fields, role, f"layer '{self.layer}'")

    @property
    def columns(self) -> list[str]:
        """Every source column to read, deduplicated and ordered."""
        return sorted(set(self.fields.values()))


@dataclass(frozen=True)
class LayerSpec:
    """What every optional published-layer block begins with.

    A declared `source`, the tile member inside it where the source is per-sheet
    (`tiled_sources`) rather than fixed-URL (`sources`), and the publisher's
    schema mapping. One definition rather than nine (`Q100`): the seven
    street-furniture blocks, the carriageway-edge survey and the tramway all
    opened with these same three fields and an identical `tiled` property, and
    `Q77` records what half-fixing a run of identical shapes costs the next
    reader. Named for what the trio is — a published layer's declaration — not
    for the furniture that happens to be most of its subclasses.
    """

    source: str
    member: str | None
    layer: SourceLayer

    @property
    def tiled(self) -> bool:
        """Whether `source` names `tiled_sources` rather than `sources`."""
        return self.member is not None


def _field(fields: Mapping[str, str], role: str, where: str) -> str:
    """The publisher's column name for a role the pipeline asked for.

    Shared by every configured schema mapping, so the error a missing role
    produces reads the same wherever it is hit.
    """
    if role not in fields:
        known = ", ".join(sorted(fields)) or "none"
        raise KeyError(f"{where} declares no field for '{role}'. Declared: {known}")
    return fields[role]


def _measures(
    body: dict[str, Any], where: str, names: tuple[str, ...], *, positive: bool = False
) -> dict[str, float]:
    """Required float measurements, refused when their value cannot be used.

    Shared so a bad measurement reads the same wherever it is hit, as `_field`
    is for a missing role.

    Finiteness is checked rather than assumed. YAML 1.1 resolves `.nan` and
    `.inf` — this file relies on that for `height_bands`' open last band — and a
    NaN passes every sign test below, then silently makes false every comparison
    it feeds downstream. That is the one bad value that never announces itself.
    """
    values: dict[str, float] = {}
    for name in names:
        value = _require(body, name, where)
        try:
            values[name] = float(value)
        except (TypeError, ValueError):
            # `float()` alone names the bad value but not where it came from,
            # which in a config of forty-odd numbers is most of the answer.
            raise ValueError(f"{where}:{name} is {value!r}, which is not a number") from None

    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"{where}:{name} must be a finite number, got {value}")
        if value < 0.0 or (positive and value == 0.0):
            limit = "must be positive" if positive else "must not be negative"
            raise ValueError(f"{where}:{name} {limit}, got {value}")
    return values


def _spec_header(body: dict[str, Any], where: str, roles: tuple[str, ...]) -> dict[str, Any]:
    """The three constructor arguments every `LayerSpec` block begins with."""
    return {
        "source": str(_require(body, "source", where)),
        "member": _tile_member(body, where),
        "layer": _source_layer(body, where, roles),
    }


def _source_layer(body: Any, where: str, roles: tuple[str, ...]) -> SourceLayer:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    return SourceLayer(
        layer=str(_require(body, "layer", where)),
        fields=_fields(body, where, roles),
    )


def _tile_member(body: dict[str, Any], where: str, *, required: bool = False) -> str | None:
    """The geodatabase path inside a per-sheet zip, with `{tile}` for the sheet id.

    Checked at load rather than at first read: a stray or malformed placeholder
    would otherwise surface once per sheet, deep into a fetch.
    """
    member = _require(body, "member", where) if required else body.get("member")
    if member is None:
        return None
    member = str(member)
    try:
        member.format(tile="probe")
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError(
            f"{where}:member {member!r} allows only the {{tile}} placeholder ({error})"
        ) from error
    return member


def _fields(
    body: dict[str, Any],
    where: str,
    roles: tuple[str, ...],
    *,
    key: str = "fields",
    optional: tuple[str, ...] | None = None,
) -> dict[str, str]:
    """A role-to-value mapping (columns, domain codes), checked to cover every
    role the stage needs.

    Checked at load for the reason `_check_source_exists` gives.
    """
    fields = {str(role): str(column) for role, column in _require(body, key, where).items()}
    missing = [role for role in roles if role not in fields]
    if missing:
        raise ValueError(f"{where}:{key} is missing {', '.join(missing)}")
    if optional is not None:
        # ⚠️ **An unknown key is refused, and that is what keeps an *optional*
        # role honest.** A required role fails loudly when it is absent; an
        # optional one is indistinguishable from a typo, so without this a
        # renamed `name_zh:` would simply stop being read and every node would
        # ship nameless. Only checked where a caller declares optional roles —
        # every other `fields:` block is exhaustively required already.
        unknown = [role for role in fields if role not in roles and role not in optional]
        if unknown:
            allowed = ", ".join((*roles, *optional))
            raise ValueError(
                f"{where}:{key} has unknown role(s) {', '.join(sorted(unknown))}. Known: {allowed}"
            )
    return fields


def _parse_hex(value: str, where: str) -> tuple[int, int, int]:
    text = value.lstrip("#")
    if len(text) != 6:
        raise ValueError(f"{where} is not a #rrggbb colour: {value!r}")
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError as error:
        raise ValueError(f"{where} is not a #rrggbb colour: {value!r}") from error


def _require(mapping: dict[str, Any], key: str, where: Path | str) -> Any:
    if key not in mapping:
        raise ValueError(f"{where} is missing required key '{key}'")
    return mapping[key]
