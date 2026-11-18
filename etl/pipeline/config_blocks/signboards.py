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
    # The plan cell the boards are cut into so the engine can cull them; zero is
    # one mesh.
    cell_m: float


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

    raw_palette = _require(body, "palette", where)
    if not isinstance(raw_palette, list) or not raw_palette:
        raise ValueError(f"{where}:palette must be a list of #rrggbb colours, got {raw_palette!r}")
    palette = tuple(
        _parse_hex(str(value), f"{where}:palette[{index}]")
        for index, value in enumerate(raw_palette)
    )

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
    return Signboards(
        source=str(_require(body, "source", where)),
        fields=_fields(body, where, _ROLES),
        mounts=mounts,
        palette=palette,
        colour_survey=None if survey is None else str(survey),
        survey_lightness=(float(lightness[0]), float(lightness[1])),
        **_measures(body, where, _SIZES, positive=True),
        **margins,
    )
