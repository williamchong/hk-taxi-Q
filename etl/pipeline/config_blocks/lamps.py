"""`lamps:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    LayerSpec,
    Material,
    _MaterialTable,
    _measures,
    _require,
    _spec_header,
)


@dataclass(frozen=True)
class Lamps(LayerSpec):
    """Published lamp posts, drawn by `pipeline/lamps.py` (`P3-26`).

    ✅ **The vocabulary is PUBLISHED, and this is the first street-furniture
    block in the file of which that is true.** `UtilityPoint.UTILITYPOINTTYPE`
    carries a coded-value domain **inside the geodatabase** — `LPO - Lamp post`,
    readable out of the `.gdbtable` bytes of every sheet. So `kinds` below is not
    `Railings.classes`: that is a whitelist
    read off code strings because nothing published defines them (`Q60`),
    and this one is a selection from a domain the publisher wrote down. It is
    still config rather than a constant, for hard rule 3 — a second city's
    publisher spells its own — but a wrong entry here is *checkable* against the
    source, which is what that one cannot say.

    ✅ **And the colour goes through `Q33` rather than around it.** `Signs` is
    exempt from the palette rule on two grounds — a printed
    specification has no reflectance to grade, and four colours inside one draw
    call have to ride the vertex — and **neither ground holds here**. Galvanised
    steel is a real surface with a published albedo, and a lamp post is one
    colour. So `column_material` names an entry in the city's own `materials:`
    table and `_check_reflectance` grades it, which is `Tramway.rail_material`'s
    shape. ⚠️ The value still rides `COLOR_0`, because the layer shares
    `signs.gdshader` and a mesh not supplying it would render white.

    ⚠️ **Every dimension below is authored, which is the debt that does
    transfer.** The layer publishes six columns and not one of them is a length:
    no height, no arm reach, no lantern size, no column diameter, no elevation
    level, no angle. Geometry `Z` is `0.0` on every feature, and that is the
    file's convention rather than a defect — `SpotHeight` reads `0.0` too and
    keeps its value in a column this layer does not have. `Q60`'s railing debt
    and `Signs`'s plate debt at a fourth and fifth layer, and these are the
    weakest-evidenced numbers in the block. **None of them is a position.**

    ⚠️ **The position is registered, not read** — `Q60`'s move arriving at a
    fourth layer, after the railings and the signs. **64.1%** of the
    region's lamp posts are surveyed inside the drawn 1.6x ribbon, a median
    1.46 m past the drawn kerb, so drawn where published four fifths of a
    kilometre of Wan Chai's columns stand in the carriageway. `outset_m` is where
    they go and `max_shift_m` is the bar on the move that puts them there.

    🔴 **It follows `signs.py`'s registration and NOT `railings.py`'s, and the
    split is deliberate.** `Q78` clamped the sign move to **outward only**,
    because the argument for moving a post at all — the carriageway floor draws the
    ribbon 1.6x the real carriageway — runs outward and nowhere else; an
    unconditional assignment also *pulls* posts that already stand clear back
    toward the road, invisibly, because `shift_m` is an absolute value.
    `CLAUDE.md` records that `railings.py` is deliberately not
    aligned with that, on the grounds that **a fence is a run and a conditional
    push would zigzag it**. A lamp post is not a run. It is a discrete object
    like a sign post, so `Q78` applies here in full and `posts_kept_as_surveyed`
    exists for the same reason it does there.

    🔴 **The arm direction is derived and ungraded (`Q62`).** Nothing published
    says which way a lantern reaches, so the stage asserts that it reaches over
    the carriageway — reusing the kerb side the registration has already
    computed, which is what an installed column physically does. That is a
    stated assumption with a counter over it, on `P3-22`'s chevron-board
    precedent, and it is **recorded as derived rather than presented as read**.
    ⚠️ The counter is *not* an `arms_against_kerb`, which would read 0 by
    construction — `Q72`'s tautology — but `lantern_overhang_m`; `lamps.py` says
    why. A whole city's lamps reaching the wrong way renders perfectly, so the
    evidence is an A/B render at one camera.

    ⚠️ **There is no lit lantern, and its absence is the decision to resist
    changing.** `Q26` has not chosen a look, and `ART_DESIGN.md` ends its
    Lighting section with *"Resist adding lights."* A lantern that glows in
    daylight is wrong in every frame this project currently renders, and 897
    `OmniLight3D`s is not a shippable answer on a Mobile tier that ships no
    shadow maps at all.

    ✅ **`Q38` was the other blocker and it is gone** (`P5-28c`): the exposure is
    a global shader parameter the lighting rig sets, so an hour is a number in a
    scene rather than a full region rebuild. `P3-26` still draws unlit geometry
    and still buys night **nothing** of its own — what changed is that the
    precondition is met and the remaining blocker is `Q26` alone, which is a
    look nobody has chosen and still not geometry.
    """

    # ✅ **A selection from a PUBLISHED domain**, unlike `Railings.classes`
    # — see the class docstring. `lamps.json` publishes
    # `refused_by_kind` over the whole vocabulary anyway, on `railings.py`'s
    # precedent: it costs nothing and it is what makes a reader able to see the
    # selection rather than take it.
    kinds: tuple[str, ...]
    # 🔴 **A material out of the city's own table, NOT an authored livery** — see
    # the class docstring for why `Signs.colours`' exemption does not transfer.
    # `_check_reflectance` grades this entry like any other.
    column_material: Material

    # ---- the column, all authored ----
    column_height_m: float
    # ⚠️ **The CIRCUMRADIUS**, so a hexagonal column's flat sits at
    # `r cos(30 deg)` — 13% inside this number. Stated because a reader checking
    # the drawn column against a published diameter would otherwise be wrong.
    column_radius_m: float
    column_sides: int
    # ---- the bracket arm and its lantern, all authored ----
    # How far the arm reaches from the column axis, toward the carriageway.
    arm_reach_m: float
    arm_radius_m: float
    # How far the lantern hangs below the top of the column. The arm **slopes**
    # to meet it: a horizontal arm plus a separately-dropped lantern leaves the
    # housing floating in the air, which is what `lamps._draw_lamp` records.
    arm_drop_m: float
    lantern_length_m: float
    lantern_width_m: float
    lantern_depth_m: float

    # ---- the join ----
    max_offset_m: float
    outset_m: float
    max_shift_m: float
    # Two points closer than this are one post, after registration has moved
    # them. ⚠️ **There is no pre-registration clustering here and there must not
    # be**: this layer publishes **zero** coincident pairs under 0.05 m, so an
    # assembly grouping of coincident points (`Q76`) would be inventing a structure the
    # data does not show. The only coincidence a lamp post has is the one this
    # stage's own move creates.
    merge_m: float
    # 🔴 **How large a gap between neighbouring drawn posts counts as a hole.**
    # Report-only, and it exists because this layer fails differently from every
    # other one here: **a lamp row's regularity IS its content**, so refusals show
    # up as gaps where a missing sign shows up as nothing. Surveyed, the region
    # has 5 gaps over 40 m; drawn, it has 16. That is the number a widening change
    # would move, and without this counter nobody would see it.
    gap_report_m: float

    def is_lamp(self, kind: str) -> bool:
        """Whether a published `UTILITYPOINTTYPE` names a lamp post.

        The shape `Railings.class_of` already takes: the
        stage asks the spec rather than importing a rule and re-passing this
        object's own fields at every call site.
        """
        return kind in self.kinds


_LAMP_ROLES = ("kind",)


_LAMP_MEASURES = (
    "column_height_m",
    "column_radius_m",
    "arm_reach_m",
    "arm_radius_m",
    "arm_drop_m",
    "lantern_length_m",
    "lantern_width_m",
    "lantern_depth_m",
    "max_offset_m",
    "outset_m",
    "max_shift_m",
    "merge_m",
    "gap_report_m",
)


def _lamps(body: Any, where: str, table: _MaterialTable) -> Lamps | None:
    """The optional published-lamp-post block (`P3-26`).

    Absent, the region ships no `lamps.glb` and the manifest names none — the
    shape `tramway`, `arrows`, `signs`, `boxjunctions`, `railings` and
    `roadmarks` all take. What is deliberately *not* offered is a fallback that
    puts a lamp every N metres down each drawn kerb: the estate publishes 1,263
    surveyed positions, and a derived rhythm would be inventing the one property
    — regularity — that is this layer's whole visual content (`Q54`).

    ⚠️ **`table` rather than a `colours:` mapping of its own**, which is what
    every other furniture block here takes. See the `Lamps` docstring: the two
    grounds for `signs.colours`' exemption from `Q33` are a printed
    specification with no reflectance and four colours in one draw call, and a
    lamp post is neither.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw_kinds = _require(body, "kinds", where)
    if isinstance(raw_kinds, str) or not isinstance(raw_kinds, (list, tuple)):
        raise ValueError(f"{where}:kinds must be a list, got {raw_kinds!r}")
    kinds = tuple(str(kind) for kind in raw_kinds)
    if not kinds:
        # An empty list admits nothing, which is the same outcome as omitting the
        # block — refused so the difference is a decision rather than a typo.
        raise ValueError(f"{where}:kinds is empty; a block that draws nothing is a mistake")
    if len(set(kinds)) != len(kinds):
        raise ValueError(f"{where}:kinds repeats a code: {kinds}")

    sides = int(_require(body, "column_sides", where))
    if sides < 3:
        raise ValueError(f"{where}:column_sides must be at least 3, or the ring is not a ring")

    lengths = _measures(body, where, _LAMP_MEASURES, positive=True)

    if lengths["arm_drop_m"] >= lengths["column_height_m"]:
        # The lantern hangs below the top of the column. At or past the column's
        # own height it hangs underground, which draws a lantern in the footway
        # and renders as a lamp post with nothing on it.
        raise ValueError(
            f"{where}:arm_drop_m {lengths['arm_drop_m']} is not less than column_height_m "
            f"{lengths['column_height_m']}, so the lantern hangs below the ground"
        )
    if lengths["arm_radius_m"] > lengths["column_radius_m"]:
        # A bracket arm thicker than the column it grows out of is a drawing
        # error that renders as a perfectly solid, obviously wrong lamp post.
        raise ValueError(
            f"{where}:arm_radius_m {lengths['arm_radius_m']} exceeds column_radius_m "
            f"{lengths['column_radius_m']}; the arm is thinner than its own column"
        )
    if lengths["lantern_length_m"] > 2.0 * lengths["arm_reach_m"]:
        # The lantern is centred on the arm's far end, so a lantern longer than
        # twice the reach runs back through the column it hangs off.
        raise ValueError(
            f"{where}:lantern_length_m {lengths['lantern_length_m']} is more than twice "
            f"arm_reach_m {lengths['arm_reach_m']}, so the lantern runs back through its column"
        )
    if lengths["merge_m"] > lengths["max_shift_m"]:
        # 🔴 **A merge radius wider than the move that creates the coincidence.**
        # This layer publishes *zero* coincident pairs, so every fold here is one
        # the registration made; a radius above the bar on that move folds posts
        # that were never brought together, quietly thinning a row whose
        # regularity is the whole point of drawing it.
        raise ValueError(
            f"{where}:merge_m {lengths['merge_m']} exceeds max_shift_m "
            f"{lengths['max_shift_m']}; it would fold posts the registration never moved together"
        )

    return Lamps(
        **_spec_header(body, where, _LAMP_ROLES),
        kinds=kinds,
        # 🔴 Through the materials table, so `_check_reflectance` grades it.
        column_material=table.get(
            str(_require(body, "column_material", where)), f"{where}:column_material"
        ),
        column_sides=sides,
        **lengths,
    )
