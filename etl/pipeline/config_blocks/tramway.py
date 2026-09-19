"""`tramway:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import LayerSpec, Material, _MaterialTable, _require, _spec_header


@dataclass(frozen=True)
class Tramway(LayerSpec):
    """The published tramway, and how `P3-14` draws it (`Q58`).

    ⚠️ **Unlike `CarriagewaySurvey` above, the pipeline reads this**: it is a
    build input, not an instrument's truth side. The shape is deliberately the
    same, because both read a domain code out of the same iB1000 layer and hard
    rule 3 keeps the code in the city file either way.

    ⚠️ **`codes` selects rails, not track centrelines.** `Q58` measured what the
    layer actually contains rather than taking the record's word: 56.5% of
    stations across a tram-flagged edge cross exactly **four** parts, and the
    modal gap between neighbouring parts is **1.05-1.20 m** — Hong Kong
    Tramways' 1.067 m gauge. `Q57` and `DATA_SOURCES.md` both called these
    "tramway centrelines"; they are the rails themselves, and a bed drawn
    between a mis-paired couple would be a lane wide.

    `gauge_m` and `pair_tolerance_m` are what turn those rails back into tracks,
    and they are a *measurement* rather than a preference — which is why they
    are here and not under an art heading. Everything below them is drawing.
    """

    codes: tuple[str, ...]
    # Published track gauge, and how far a neighbour may sit from it and still
    # be read as the other rail of the same track.
    gauge_m: float
    pair_tolerance_m: float
    # Drawn width of one rail, and of the bed carrying a pair of them.
    rail_width_m: float
    bed_width_m: float
    # How far above the deck the bed sits, and the rail above the bed. The road
    # and the ground are coplanar at grade by construction (`P3-10`), so a
    # tramway laid at deck height would z-fight the terrain it rests on.
    bed_lift_m: float
    rail_lift_m: float
    # Furthest a rail station may sit from a level-0 centreline and still take
    # its height from it. Beyond this the part is dropped rather than guessed:
    # the reserve runs between two carriageways, so a rail with no road near it
    # is one this region does not drive past.
    max_snap_m: float
    # Resolved through `_MaterialTable.get`, as every other material reference
    # is: that call *is* how usage gets recorded, so holding the name as a
    # string here would leave both materials looking unreferenced.
    rail_material: Material
    bed_material: Material


_TRAMWAY_ROLES = ("line_type",)


def _tramway(body: Any, where: str, table: _MaterialTable) -> Tramway | None:
    """The optional published-tramway block (`Q58`).

    Absent, the region ships no `tram.glb` and the manifest names none — the
    honest answer for a city with no tramway, and the same shape `podiums` and
    `carriageway_survey` already use. What is *not* offered is drawing the
    tramway from `roads.tram_streets` instead: that flag says which streets
    carry a tram, and `Q58` measured that the rails are a median 3.26 m past the
    drawn kerb of the edge carrying the flag. The flag cannot place them.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    codes = tuple(str(code) for code in _require(body, "codes", where))
    if not codes:
        raise ValueError(f"{where}:codes is empty; the source would match no feature")

    gauge_m = float(_require(body, "gauge_m", where))
    tolerance_m = float(_require(body, "pair_tolerance_m", where))
    if gauge_m <= 0.0 or tolerance_m <= 0.0:
        raise ValueError(f"{where}: gauge_m and pair_tolerance_m must both be positive")
    if tolerance_m >= gauge_m:
        # At half the gauge a rail pairs with the *other track's* near rail as
        # readily as with its own, and the bed is then drawn across the four-foot
        # of neither. Refused rather than clamped: the number is a measurement
        # of the source's digitising spread, so a wrong one is a wrong survey.
        raise ValueError(
            f"{where}:pair_tolerance_m is {tolerance_m}, which is not narrower than the "
            f"{gauge_m} m gauge it qualifies — every rail would pair with both neighbours"
        )

    bed_width_m = float(_require(body, "bed_width_m", where))
    rail_width_m = float(_require(body, "rail_width_m", where))
    if not 0.0 < rail_width_m < bed_width_m:
        raise ValueError(
            f"{where}: rail_width_m {rail_width_m} must be positive and narrower than "
            f"bed_width_m {bed_width_m}"
        )

    return Tramway(
        **_spec_header(body, where, _TRAMWAY_ROLES),
        codes=codes,
        gauge_m=gauge_m,
        pair_tolerance_m=tolerance_m,
        rail_width_m=rail_width_m,
        bed_width_m=bed_width_m,
        bed_lift_m=float(_require(body, "bed_lift_m", where)),
        rail_lift_m=float(_require(body, "rail_lift_m", where)),
        max_snap_m=float(_require(body, "max_snap_m", where)),
        rail_material=table.get(
            str(_require(body, "rail_material", where)), f"{where}:rail_material"
        ),
        bed_material=table.get(str(_require(body, "bed_material", where)), f"{where}:bed_material"),
    )
