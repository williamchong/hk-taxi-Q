"""`signboards:`.

One of `pipeline.config`'s blocks (`P3-103`, `Q260`), imported through
`pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import _fields, _measures, _parse_hex, _require

_ROLES = ("id", "type", "length", "height", "thickness", "facing", "photo", "easting", "northing")
WALL, PROJECTING, ROOF = "wall", "projecting", "roof"
_MOUNTS = (WALL, PROJECTING, ROOF)
_SIZES = ("max_snap_m", "max_dimension_m", "default_thickness_m", "cell_m")
_MARGINS = (
    "outset_m",
    "stack_radius_m",
    "stack_gap_m",
    "road_base_m",
    "roof_setback_m",
    "facing_probe_m",
    "facing_weight_m",
    "frame_darken",
    "survey_min_share",
    "screen_lift_m",
)


@dataclass(frozen=True)
class Mount:
    """How one published signboard type is drawn: on which surface, and how
    high its lowest edge is above the ground in front of the wall.

    `wall`: flat on the wall, `outset_m` off it. `projecting`: at right angles
    to the wall, its published length reaching out over the street. `roof`: in
    the wall's plane, standing on the top of the wall it was snapped to.
    """

    mount: str
    base_m: float


@dataclass(frozen=True)
class Trade:
    """One kind of shop a board's generic name can say: its name ends in one of
    `suffixes`, it is picked in proportion to `weight`, and only on a mount in
    `mounts`. `food` trades are the ones a restaurant licence nearby favours."""

    suffixes: tuple[str, ...]
    weight: float
    food: bool
    mounts: tuple[str, ...]


@dataclass(frozen=True)
class RestaurantLicences:
    """FEHD's restaurant licences, read for their position alone."""

    source: str
    fields: dict[str, str]
    reach_m: float
    # A food trade's weight is multiplied by `boost` where a licence is within
    # `reach_m` of the board, and by `elsewhere` where none is.
    boost: float
    elsewhere: float


@dataclass(frozen=True)
class SignText:
    """The generic shop names lettered on the boards (`P3-103` step 2).

    🔴 **Never a real name.** The register names no shop; FEHD's licences do,
    and only their position is read. A name is `name_chars` picks from
    `prefixes` and one of its trade's `suffixes`, seeded by the board's id.
    """

    # The committed font the atlas is rendered from, relative to the repo root.
    font: str
    glyph_px: int
    # The share of a face's short side a character fills.
    fill: float
    # A board this much taller than wide is lettered top to bottom.
    vertical_aspect: float
    # The lettering stands this far off its face.
    lift_m: float
    # The ink is the one of these that contrasts most with the board.
    inks: tuple[tuple[int, int, int], ...]
    name_chars: int
    prefixes: tuple[str, ...]
    trades: dict[str, Trade]
    licences: RestaurantLicences | None
    # A street's trades weighted against the rest, by the street's English name.
    streets: dict[str, dict[str, float]]
    # Off, the boards ship colour only: no names, no atlas. The block stays
    # validated, and the font keeps its characters, so it switches back on.
    lettered: bool = True


@dataclass(frozen=True)
class Signboards:
    """The Buildings Department's signboards, drawn as plain boards by
    `pipeline/signboards.py` (`P3-103`, `Q260`).

    🔴 **Only where a signboard is surveyed.** A position, a type, a size and
    the street it faces are published; a height above the ground is not, and
    neither is what the board says. Every height here is authored.

    ⚠️ **`palette` is a printed specification, not a reflectance**, on
    `signs.colours`' terms: a board's ground colour is paint and light, so it is
    not in `materials:` and `_check_reflectance` does not grade it. A surveyed
    colour (`colour_survey`) wins where the survey is confident.
    """

    source: str
    fields: dict[str, str]
    # Each published type that is drawn, and how. A type not listed is counted
    # and not drawn.
    mounts: dict[str, Mount]
    # The farthest a published point is snapped to a wall the tiles draw.
    max_snap_m: float
    # A published length or height past this is a typo, not a board: refused.
    max_dimension_m: float
    # The thickness a board without a published one is drawn at.
    default_thickness_m: float
    # A wall board stands this far off its wall.
    outset_m: float
    # Boards snapped within this of each other along one wall are stacked, the
    # next one's lowest edge `stack_gap_m` over the last one's top.
    stack_radius_m: float
    stack_gap_m: float
    # A projecting board whose outer end reaches over the level-0 carriageway
    # is raised so its lowest edge is at least this over the ground.
    road_base_m: float
    # A roof board stands this far inside the edge of the roof it was snapped to.
    roof_setback_m: float
    # Which of two near walls faces the published street: each wall's foot is
    # probed `facing_probe_m` along its outward normal, and a wall facing away
    # from the street costs `facing_weight_m` of snap distance per unit of
    # (1 - cos) between its normal and the way to the street.
    facing_probe_m: float
    facing_weight_m: float
    # A board's edges are its colour darkened by this share; its two faces are
    # its colour, and lit at night.
    frame_darken: float
    # The board colours drawn where no survey answers, picked by the board's
    # published id so a rebuild draws the same street.
    palette: tuple[tuple[int, int, int], ...]
    # `tools/signboard_colour.py`'s table under `etl/sources/signboard_colour/`,
    # or None to draw the palette everywhere.
    colour_survey: str | None
    # The least share of a board's photo its colour must cover to be used.
    survey_min_share: float
    # The L* a surveyed colour is clamped into: a photo's blown highlight or
    # crushed shadow is the camera's, not the board's.
    survey_lightness: tuple[float, float]
    # The plan cell the boards are cut into so the engine can cull them.
    cell_m: float
    # The lettering, or None for plain boards.
    text: SignText | None = None
    # Boards that are screens (step 3), by published id: the register does not
    # say which, so each is authored. A screen is drawn on its lit face
    # `screen_lift_m` off it, and not lettered.
    screens: tuple[str, ...] = ()
    screen_lift_m: float = 0.0


def _signboards(body: Any, where: str) -> Signboards | None:
    """The optional `signboards:` block. Absent, the region ships no `signboards.glb`."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw_mounts = _require(body, "mounts", where)
    if not isinstance(raw_mounts, dict) or not raw_mounts:
        raise ValueError(f"{where}:mounts must map a published type to a mount, got {raw_mounts!r}")
    mounts: dict[str, Mount] = {}
    for kind, entry in raw_mounts.items():
        here = f"{where}:mounts:{kind}"
        if not isinstance(entry, dict):
            raise ValueError(f"{here} must be a mapping, got {entry!r}")
        mount = str(_require(entry, "mount", here))
        if mount not in _MOUNTS:
            raise ValueError(f"{here}:mount is {mount!r}; known: {', '.join(_MOUNTS)}")
        mounts[str(kind)] = Mount(mount=mount, **_measures(entry, here, ("base_m",)))

    palette = _hex_list(_require(body, "palette", where), f"{where}:palette")

    lightness = _require(body, "survey_lightness", where)
    if (
        not isinstance(lightness, list)
        or len(lightness) != 2
        or not 0.0 <= float(lightness[0]) < float(lightness[1]) <= 100.0
    ):
        raise ValueError(f"{where}:survey_lightness must be [low, high] L*, got {lightness!r}")

    margins = _measures(body, where, _MARGINS)
    for name in ("frame_darken", "survey_min_share"):
        if margins[name] > 1.0:
            raise ValueError(f"{where}:{name} is a share, got {margins[name]}")
    survey = body.get("colour_survey")
    raw_screens = body.get("screens") or []
    if not isinstance(raw_screens, list) or not all(isinstance(i, (int, str)) for i in raw_screens):
        raise ValueError(f"{where}:screens must be a list of board ids, got {raw_screens!r}")
    return Signboards(
        text=_text(body.get("text"), f"{where}:text"),
        screens=tuple(str(ident) for ident in raw_screens),
        source=str(_require(body, "source", where)),
        fields=_fields(body, where, _ROLES),
        mounts=mounts,
        palette=palette,
        colour_survey=None if survey is None else str(survey),
        survey_lightness=(float(lightness[0]), float(lightness[1])),
        **_measures(body, where, _SIZES, positive=True),
        **margins,
    )


def _hex_list(value: Any, where: str) -> tuple[tuple[int, int, int], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{where} must be a list of #rrggbb colours, got {value!r}")
    return tuple(_parse_hex(str(item), f"{where}[{index}]") for index, item in enumerate(value))


def _words(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(w, str) and w for w in value):
        raise ValueError(f"{where} must be a list of words, got {value!r}")
    return tuple(value)


def _text(body: Any, where: str) -> SignText | None:
    """The optional `signboards.text:` block. Absent, the boards are plain."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw_trades = _require(body, "trades", where)
    if not isinstance(raw_trades, dict) or not raw_trades:
        raise ValueError(f"{where}:trades must map a trade to its words, got {raw_trades!r}")
    trades: dict[str, Trade] = {}
    for name, entry in raw_trades.items():
        here = f"{where}:trades:{name}"
        if not isinstance(entry, dict):
            raise ValueError(f"{here} must be a mapping, got {entry!r}")
        mounts = _words(entry.get("mounts", list(_MOUNTS)), f"{here}:mounts")
        unknown = sorted(set(mounts) - set(_MOUNTS))
        if unknown:
            raise ValueError(f"{here}:mounts names {unknown}; known: {', '.join(_MOUNTS)}")
        trades[str(name)] = Trade(
            suffixes=_words(_require(entry, "suffixes", here), f"{here}:suffixes"),
            food=bool(entry.get("food", False)),
            mounts=mounts,
            **_measures(entry, here, ("weight",), positive=True),
        )

    raw_licences = body.get("licences")
    licences = None
    if raw_licences is not None:
        here = f"{where}:licences"
        if not isinstance(raw_licences, dict):
            raise ValueError(f"{here} must be a mapping, got {raw_licences!r}")
        licences = RestaurantLicences(
            source=str(_require(raw_licences, "source", here)),
            fields=_fields(raw_licences, here, ("easting", "northing")),
            **_measures(raw_licences, here, ("reach_m", "boost"), positive=True),
            **_measures(raw_licences, here, ("elsewhere",)),
        )

    raw_streets = body.get("streets") or {}
    if not isinstance(raw_streets, dict):
        raise ValueError(f"{where}:streets must map a street to trade weights, got {raw_streets!r}")
    streets: dict[str, dict[str, float]] = {}
    for street, weights in raw_streets.items():
        here = f"{where}:streets:{street}"
        if not isinstance(weights, dict) or not weights:
            raise ValueError(f"{here} must map a trade to a weight, got {weights!r}")
        unknown = sorted(set(weights) - set(trades))
        if unknown:
            raise ValueError(f"{here} names trades {unknown} the block does not declare")
        streets[str(street).upper()] = _measures(weights, here, tuple(weights), positive=True)

    name_chars = int(_require(body, "name_chars", where))
    prefixes = _words(_require(body, "prefixes", where), f"{where}:prefixes")
    if not 1 <= name_chars <= len(prefixes):
        raise ValueError(f"{where}:name_chars must be 1..{len(prefixes)}, got {name_chars}")
    glyph_px = int(_require(body, "glyph_px", where))
    if not 16 <= glyph_px <= 256:
        raise ValueError(f"{where}:glyph_px must be 16..256, got {glyph_px}")
    sizes = _measures(body, where, ("fill", "vertical_aspect", "lift_m"), positive=True)
    if sizes["fill"] > 1.0:
        raise ValueError(f"{where}:fill is a share, got {sizes['fill']}")
    return SignText(
        font=str(_require(body, "font", where)),
        glyph_px=glyph_px,
        inks=_hex_list(_require(body, "inks", where), f"{where}:inks"),
        name_chars=name_chars,
        prefixes=prefixes,
        trades=trades,
        licences=licences,
        streets=streets,
        lettered=bool(body.get("lettered", True)),
        **sizes,
    )
