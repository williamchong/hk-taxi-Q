"""`arrows:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import LayerSpec, _deck_codes, _require, _spec_header

# What an arrow may show. The vocabulary is the pipeline's, not a city's:
# a glyph is drawn from these, so a fourth word would need geometry to draw it.
# ⚠️ These are *movements*, not lane positions. `RM1027` is one arrow with two
# heads, drawn in one lane; it is not two arrows.
ARROW_AHEAD = "ahead"


ARROW_LEFT = "left"


ARROW_RIGHT = "right"


ARROW_MOVEMENTS = (ARROW_AHEAD, ARROW_LEFT, ARROW_RIGHT)


@dataclass(frozen=True)
class ArrowGlyph:
    """One publisher code: what its arrow shows, and how long it is drawn.

    ⚠️ **The length belongs to the code, not to the block.** TD's index plan
    publishes every turn arrow twice — `RM1017` straight-ahead at **4000 mm**
    and `RM1018` the same arrow at **6000 mm**, and so on in pairs up to
    `RM1030`. A single authored length would draw one of each pair wrong by
    half its own size, on a marking whose whole defence is that it is read
    rather than invented. Wan Chai happens to publish only the 4 m variants;
    that is a fact about this region, not about the estate.
    """

    movements: tuple[str, ...]
    length_m: float


@dataclass(frozen=True)
class Arrows(LayerSpec):
    """Published turn arrows, and how `P3-15` draws them (`Q53`, `Q57`).

    ⚠️ **`glyphs` maps a publisher's code to a movement, and that mapping is the
    one thing here that cannot be checked by any grader this repo has.** Every
    consumer downstream takes "1019 means turn left" on trust, exactly as `Q56`
    found every consumer taking double-versus-single on trust from
    `NSR.TIME_ZONE`. The codes are defined in the publisher's own index plan,
    inside `traffic_aids_data_dictionary` — read it, do not infer the meaning
    from the count. `Q57`'s `TACW` trap is a three-letter code that looked like
    the answer.

    ⚠️ **`RM1135`/`RM1136` are not arrows** — they are the 望右/望左 look-right
    and look-left crossing markings, and they are the two most common codes in
    the region after `RM1017`. A glyph table that picks up "the top six codes"
    paints pedestrian warnings down the middle of the carriageway.

    The dimensions below are marking *convention*, drawn to the index plan's
    figures. They are not a position: where an arrow goes is read from the
    source, through `max_offset_m` and the lane the offset lands in.

    ⚠️ **There is no material here, and its absence is the decision.** An arrow
    is the same paint as a lane divider, and `Q53` put the marking colours in
    `game/tuning/road_markings.tres` rather than in this file's `materials:`
    table — deliberately outside `Q33`'s exposure rule, because paint is not
    cladding. That entry predicted that "the day a third road colour is authored
    somewhere else" would be the problem, and adding `road_paint_white` here
    would be that day. So `arrows.glb` ships **no `COLOR_0`** and takes its
    colour from `game/tuning/arrows.tres`, beside the markings it matches. The
    glTF material *name* the engine dispatches on is `ARROWS_MATERIAL` in
    `pipeline/arrows.py`, a constant, as `SURFACE_MATERIAL` and
    `TRAMWAY_MATERIAL` are.
    """

    # Publisher code -> what that code's arrow shows and how long it is.
    glyphs: dict[str, ArrowGlyph]
    # The proportions of an arrow, as fractions of its **own** published length,
    # so the 4 m and 6 m variants of the same marking scale together instead of
    # sharing an absolute head that is right for one of them.
    #
    # 🔴 **Measured off TD's pictogram since `Q93`, where they were authored and
    # wrong.** `CT174/51-5(1)F` publishes `LENGTH` for `RM1017`-`RM1030` and no
    # other dimension, so the shape can only come from the drawing itself; the
    # figures here are read from it at 700 dpi and every one of them moved. The
    # ahead head was drawn **0.325 long by 0.235 across** against a published
    # 0.390 by 0.122 — nearly twice as wide and a fifth too short — and the stem
    # was a uniform 0.085 where the drawing tapers it.
    head_length_frac: float
    head_width_frac: float
    # The stem is a **taper**, wide at the tail and narrow under the head, which
    # is what the drawing shows and what a single width could not be.
    stem_width_nose_frac: float
    stem_width_tail_frac: float
    # The turn branch, which has its own head and is not the ahead head reused.
    # 🔴 **That reuse was the defect `Q93` found**: `shoulder` is
    # `reach - head_length`, and with a reach of 0.28 against a head of 0.325 it
    # came out **negative** — the turn head's base landed 0.18 m past the far
    # side of the stem, so head and stem merged into a blob on **416 of 747**
    # drawn arrows. `branch_reach_frac` must exceed `branch_head_length_frac`,
    # and `parse` refuses a city where it does not.
    #
    # 🔴 **All three branch figures are AUTHORED, and that is a reversal.** They
    # were measured off `RM1027` first — reach 0.150, head 0.100 long, barb span
    # 0.233 — and the result was reported from the driving seat as not making
    # sense. TD's branch head is genuinely *wider than it is deep*, because thin
    # barbs sweeping back from the tip do the work, so this model's plain
    # triangle at those proportions is a mushroom on the shaft; drawn faithfully
    # as a six-point dart it is a detached diamond, and its barbs are 0.09 m on a
    # 4 m arrow, which `Q91`'s sub-pixel problem removes at any driving distance.
    # Sized against the frame instead. ⚠️ **The ahead head and the stem above
    # are NOT authored** — an overlay against TD's own cell agrees on both.
    # `DATA_SOURCES.md` carries the argument.
    branch_reach_frac: float
    branch_head_length_frac: float
    branch_head_width_frac: float
    # How far below the ahead head's base the turn branch's axis sits, as a
    # fraction of length. Measured 0.145 on `RM1027`. ⚠️ **Not derived from the
    # head width, which is what it used to be**: the two are independent in the
    # drawing, and tying them meant a change to the head silently moved the
    # branch.
    branch_drop_frac: float
    # How far above the carriageway the glyph sits. The road surface and the
    # ground are coplanar at grade by construction (`P3-10`), so paint laid at
    # deck height would z-fight the road it is painted on.
    lift_m: float
    # Furthest a symbol may sit from a level-0 centreline and still be placed.
    # Beyond this it is dropped rather than guessed at: 14.2% of this region's
    # symbols fall outside even the *real* carriageway of their nearest edge,
    # and an arrow on the wrong street is the `P3-9a` debit this whole stage is
    # subordinate to.
    max_offset_m: float
    # How far a symbol's own bearing may sit from its host edge's heading before
    # the match is refused. A symbol squarely across its edge matched the wrong
    # edge; refusing is how that stops being drawn.
    #
    # ⚠️ Refuses the *match*, never rotates the arrow to fit. An arrow turned to
    # agree with the road would be an invented marking in `Q54`'s sense, and it
    # would render perfectly.
    bearing_tolerance_deg: float
    # The publisher's `level` codes whose arrows stand on the DECKS (`P3-37b`,
    # `Q134`) — `road_marks.deck_codes`' key, for its reason and with its
    # measurement: `A01` is the elevated network, `A03` the shut bores. Empty
    # stands none, which is what every build before `P3-37` did.
    deck_codes: tuple[str, ...]


_ARROW_ROLES = ("code", "bearing", "level", "size")


def _arrows(body: Any, where: str) -> Arrows | None:
    """The optional published-turn-arrow block (`Q53`, `Q57`).

    Absent, the region ships no `arrows.glb` and the manifest names none — the
    same shape `tramway` uses, and honest for a city whose estate publishes no
    marking symbols. What is *not* offered is a fallback that derives arrows
    from junction geometry: `Q53` refused arrows precisely because inventing
    their content is a `P3-9a` debit, and a fallback here would reintroduce it
    silently on any city missing the block.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw = _require(body, "glyphs", where)
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{where}:glyphs must be a non-empty mapping of code to glyph")
    glyphs: dict[str, ArrowGlyph] = {}
    for code, entry in raw.items():
        spot = f"{where}:glyphs.{code}"
        if not isinstance(entry, dict):
            raise ValueError(f"{spot} must be a mapping with movements and length_m, got {entry!r}")
        movements = _require(entry, "movements", spot)
        if isinstance(movements, str) or not isinstance(movements, (list, tuple)):
            raise ValueError(f"{spot}:movements must be a list, got {movements!r}")
        named = tuple(str(movement) for movement in movements)
        if not named:
            raise ValueError(f"{spot}:movements is empty; an arrow pointing nowhere draws nothing")
        unknown = [movement for movement in named if movement not in ARROW_MOVEMENTS]
        if unknown:
            raise ValueError(
                f"{spot}:movements names {', '.join(unknown)}, which is not one of "
                f"{', '.join(ARROW_MOVEMENTS)} — the pipeline has no geometry to draw it"
            )
        if len(set(named)) != len(named):
            # A repeated movement would draw the same head twice, in the same
            # place, at the same height — invisible, and the mesh silently
            # heavier. Refused rather than deduped: a duplicate means the table
            # was transcribed wrong, and the rest of that row is then suspect.
            raise ValueError(f"{spot}:movements repeats a movement: {named}")
        length_m = float(_require(entry, "length_m", spot))
        if length_m <= 0.0:
            raise ValueError(f"{spot}:length_m must be positive, got {length_m}")
        glyphs[str(code)] = ArrowGlyph(movements=named, length_m=length_m)

    fractions = {
        name: float(_require(body, name, where))
        for name in (
            "head_length_frac",
            "head_width_frac",
            "stem_width_nose_frac",
            "stem_width_tail_frac",
            "branch_reach_frac",
            "branch_head_length_frac",
            "branch_head_width_frac",
            "branch_drop_frac",
        )
    }
    outside = {name: value for name, value in fractions.items() if not 0.0 < value < 1.0}
    if outside:
        raise ValueError(
            f"{where}: {', '.join(sorted(outside))} must each be a fraction of an arrow's own "
            f"length, strictly between 0 and 1; got {outside}"
        )
    if fractions["stem_width_tail_frac"] >= fractions["head_width_frac"]:
        raise ValueError(
            f"{where}: stem_width_tail_frac {fractions['stem_width_tail_frac']} must be narrower "
            f"than head_width_frac {fractions['head_width_frac']}, or the head is not a head"
        )
    if fractions["stem_width_nose_frac"] > fractions["stem_width_tail_frac"]:
        raise ValueError(
            f"{where}: stem_width_nose_frac {fractions['stem_width_nose_frac']} exceeds "
            f"stem_width_tail_frac {fractions['stem_width_tail_frac']}; the drawn stem tapers "
            f"toward the head, and reversing it draws a wedge pointing the wrong way"
        )
    if fractions["branch_reach_frac"] <= fractions["branch_head_length_frac"]:
        # 🔴 **The `Q93` defect, refused rather than commented.** `glyph_polygons`
        # puts the branch head's base at `reach - branch_head_length` from the
        # stem centre; when that is negative the base lands on the far side of
        # the stem, the head swallows it, and 416 of the region's 747 arrows
        # render as a blob. It shipped for a release because nothing checked it.
        raise ValueError(
            f"{where}: branch_reach_frac {fractions['branch_reach_frac']} must exceed "
            f"branch_head_length_frac {fractions['branch_head_length_frac']}, or the turn head's "
            f"base falls on the far side of the stem"
        )

    max_offset_m = float(_require(body, "max_offset_m", where))
    if max_offset_m <= 0.0:
        raise ValueError(f"{where}:max_offset_m must be positive, got {max_offset_m}")
    tolerance_deg = float(_require(body, "bearing_tolerance_deg", where))
    if not 0.0 < tolerance_deg <= 90.0:
        # Past 90 degrees a symbol lying square across its edge passes, which is
        # the exact signature of a match to the wrong edge. The check would
        # still run and would refuse nothing.
        raise ValueError(
            f"{where}:bearing_tolerance_deg is {tolerance_deg}; it must be positive and no "
            f"more than 90, or a symbol square across its edge is accepted"
        )

    lift_m = float(_require(body, "lift_m", where))
    if lift_m <= 0.0:
        raise ValueError(
            f"{where}:lift_m is {lift_m}; paint coplanar with the road it is painted on z-fights"
        )

    return Arrows(
        **_spec_header(body, where, _ARROW_ROLES),
        glyphs=glyphs,
        head_length_frac=fractions["head_length_frac"],
        head_width_frac=fractions["head_width_frac"],
        stem_width_nose_frac=fractions["stem_width_nose_frac"],
        stem_width_tail_frac=fractions["stem_width_tail_frac"],
        branch_reach_frac=fractions["branch_reach_frac"],
        branch_head_length_frac=fractions["branch_head_length_frac"],
        branch_head_width_frac=fractions["branch_head_width_frac"],
        branch_drop_frac=fractions["branch_drop_frac"],
        lift_m=lift_m,
        max_offset_m=max_offset_m,
        bearing_tolerance_deg=tolerance_deg,
        deck_codes=_deck_codes(body, where),
    )
