"""`road_marks:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    LayerSpec,
    SourceLayer,
    _deck_codes,
    _measures,
    _require,
    _source_layer,
    _spec_header,
)

# How a marking lies against the road it belongs to. ⚠️ **A property of the
# MARKING and never of the stage**, because the two answers want opposite host
# rules and `P3-23` shipped with only the first: a stop line is drawn *across* a
# junction mouth, a double white line runs *along* the carriageway, and the rule
# that picks the right edge for one picks nothing at all for the other.
TRANSVERSE = "transverse"


LONGITUDINAL = "longitudinal"


# 🔴 **A marking with NO axis against its road** (`P3-35g3`): a hatched island's
# stripes and a chevron's legs, which TD surveys one part each. Measured on Wan
# Chai's 850 at-grade `RM1037` parts, 64% lie 15-75 deg to the nearest edge and
# 31% of the hatched family is refused by BOTH rules above at the shared 30 deg
# bar. There is no angle such a part is "supposed" to lie at, so it is hosted by
# the road it lies ON and carries no angular residual at all.
OBLIQUE = "oblique"


MARK_AXES = (TRANSVERSE, LONGITUDINAL, OBLIQUE)


BROKEN_LEFT = "left"


BROKEN_RIGHT = "right"


BROKEN_SIDES = (BROKEN_LEFT, BROKEN_RIGHT)


@dataclass(frozen=True)
class RoadMark:
    """One published road marking, and the bar TD draws it as (`P3-23`).

    ⚠️ **Every dimension here is transcribed from the publisher, not authored.**
    TD's index plan `CT174/51-5(1)F` gives each `RM` code its line width, its
    line count and its module, and `Q59`'s rule applies at full strength: the
    sheet is a **scan** — `pdffonts` returns nothing and the page is eight
    indexed 2400-ppi images — so it is read by eye, and `Q67` proved that eye
    reading a face gets it wrong four times in five. What makes these
    checkable is that they are three short rows of plain text rather than a
    pictogram, quoted verbatim in `hong_kong.yaml` beside each entry.

    ⚠️ **`lines_spacing_m` is the CLEAR GAP between the two lines, not their
    centre-to-centre pitch, and the sheet proves it rather than this comment.**
    `RM1001` DOUBLE LINES publishes `LINE WIDTH = 150` with `LINES SPACING =
    100`; read as a pitch that is two 150 mm lines whose centres are 100 mm
    apart, which is one 250 mm line. Only the gap reading is a drawable shape.
    """

    # The entry's own name. Not a mesh name — all three draw into one primitive
    # in one colour, so unlike `RailingClass.id` this identifies a *counter*,
    # which is why it carries no `-col` guard.
    id: str
    # Which published `LINETYPE` values this entry admits. A list because one
    # marking can carry two codes — `RM1108`/`RM1109` EDGE OF CARRIAGEWAY is the
    # precedent already in this file.
    codes: tuple[str, ...]
    # Width of each line, across the marking. 200 mm for all three of the
    # region's codes.
    line_width_m: float
    # How many parallel lines the marking draws: 1 for `RM1011` STOP LINE, 2 for
    # `RM1012` STOP LINES and `RM1013` GIVE WAY LINES.
    lines: int
    # The clear gap between them — see the class docstring. Zero, and unread,
    # where `lines` is 1.
    lines_spacing_m: float
    # The dash module along the marking: `mark_m` of paint then `gap_m` of road,
    # repeating. Both None for a continuous line. ⚠️ **Both or neither** — a
    # mark with no gap is continuous spelt at length, and a gap with no mark
    # draws nothing, so the loader refuses a half-declared module rather than
    # picking one of those two.
    mark_m: float | None
    gap_m: float | None
    # 🔴 **Which ONE line of a pair the module breaks, or None where it breaks
    # them all** (`Q132`). `RM1002` and `RM1003` DOUBLE LINES publish `LEFT LINE =
    # CONTINUOUS, RIGHT LINE = 1000 MARK, 5000 GAP` and its mirror — the side that
    # may cross — so the module is one line's and the other runs unbroken.
    # `RM1013`'s two lines are both broken and leave this None.
    #
    # ⚠️ **LEFT and RIGHT are of the part's DIGITISED direction, and that is the
    # publisher's own frame rather than a guess**: TD renders these two codes
    # through representation rules (`RULEID` 2 and 3 on every feature in region),
    # which ArcGIS applies along the digitised line, so a part digitised the other
    # way is drawn the other way on TD's own drawing too. ⚠️ **A wrong side here is
    # an instruction reversed, and it renders perfectly** — nothing in a frame or
    # a counter can see it, which is why the side is config beside the sheet's row.
    broken_line: str | None
    # `TRANSVERSE` or `LONGITUDINAL` — which way this marking lies against its
    # host. 🔴 **It selects the host RULE, not just a counter.** `_host` scores a
    # transverse marking by `|90 - angle|` and a longitudinal one by the angle
    # itself, so a code declared with the wrong axis finds the most nearly
    # perpendicular road instead of the one it is painted on, and is then refused
    # by `bearing_tolerance_deg` — 19 km of published marking drawing nothing,
    # with both partitions closing.
    axis: str
    # 🔴 **Whether this marking SEPARATES OPPOSING FLOWS, which is what the
    # inferred join yields to** (`Q125`, `Q132`). The join is drawn only where no
    # surveyed divider already runs, and "divider" was `RM1001` alone while that
    # was the only longitudinal row. A lane line is not one: it lies half a
    # carriageway from the join, which is `_covered`'s own reach, so admitting it
    # would let measurement noise switch the join off a lane at a time.
    divides_flows: bool
    # 🔴 **A second width under ONE code** (`P3-35g3`): `RM1035`/`RM1036` draw
    # their outline at `LINE WIDTH = 150` and their chevrons at `CHEVRON WIDTH =
    # 900`, and no attribute says which part is which. The GEOMETRY does: TD
    # surveys a chevron as one V — a 3-vertex part — and of the 3-vertex parts in
    # Wan Chai and Causeway Bay none turns between 10 and 30 deg at its middle
    # vertex (19 under 10, 215 over 30), while neighbouring apexes stand p50
    # 2.00 / 1.99 m apart against the sheet's `DISTANCE BET. CHEVRONS = 2000`.
    # `chevron_turn_deg` sits in that empty band. Both or neither; oblique only.
    chevron_width_m: float | None = None
    chevron_turn_deg: float | None = None

    @property
    def transverse(self) -> bool:
        """Whether this marking is drawn across its host rather than along it."""
        return self.axis == TRANSVERSE

    @property
    def oblique(self) -> bool:
        """Whether this marking has no axis against its host (`OBLIQUE`)."""
        return self.axis == OBLIQUE

    def drawn_line_width_m(self, longitudinal_scale: float) -> float:
        """The width each line is DRAWN at, which is not the width published.

        See `RoadMarks.longitudinal_legibility_scale`. Transverse marks are drawn
        at the publisher's own figure and this returns it unchanged.
        """
        return self.line_width_m * (1.0 if self.transverse else longitudinal_scale)

    def drawn_band_offsets_m(self, longitudinal_scale: float) -> tuple[float, ...]:
        """`band_offsets_m` at the drawn width, so the gap scales with the lines.

        ⚠️ **The whole shape scales or none of it does.** Widening the lines while
        holding the published 100 mm gap would close the pair into one bar at the
        first exaggeration worth making — the same reading error the sheet's
        `LINES SPACING` warning is about, arriving through the back door.
        """
        scale = 1.0 if self.transverse else longitudinal_scale
        return tuple(offset * scale for offset in self.band_offsets_m)

    @property
    def continuous(self) -> bool:
        """Whether the marking runs unbroken."""
        return self.mark_m is None

    def broken_bands(self) -> tuple[bool, ...]:
        """Per line, in `band_offsets_m`'s order, whether the module breaks it.

        ⚠️ **`band_offsets_m` runs LEFT to RIGHT of the digitised direction** —
        `roadmarks.band_quads` lays a positive offset to the RIGHT — so LEFT is the
        first band and RIGHT the last. `test_the_broken_line_is_on_its_own_side`
        pins that against `surface.mitres`' frame rather than against this comment.
        """
        if self.continuous:
            return (False,) * self.lines
        if self.broken_line is None:
            return (True,) * self.lines
        return (self.broken_line == BROKEN_LEFT, self.broken_line == BROKEN_RIGHT)

    @property
    def band_offsets_m(self) -> tuple[float, ...]:
        """Each line's centre, across the marking, about the published line.

        ⚠️ **Symmetric about the published polyline, and that is a reading of an
        unresolved convention rather than a fact.** The source publishes one
        line per feature and nothing in the specification says whether it is the
        band's centre or one of its two edges. Centre is the least-wrong choice
        for the same reason `arrows.py` takes a glyph's insertion point to be
        its centre: if the convention is an edge, the band is out by half its
        own width; anchoring on an edge when the truth is the centre is out by
        twice that. The whole consequence is 0.2 m on a 0.6 m band.
        """
        if self.lines <= 1:
            return (0.0,)
        pitch = self.line_width_m + self.lines_spacing_m
        first = -0.5 * pitch * (self.lines - 1)
        return tuple(first + index * pitch for index in range(self.lines))


@dataclass(frozen=True)
class RoadMarks(LayerSpec):
    """Published stop and give-way lines, drawn by `pipeline/roadmarks.py` (`P3-23`).

    The content is **read, not invented**, on `Q53`'s terms and
    `BoxJunctions`': `DTAD_RD_MARK_LINE` publishes each bar as a surveyed
    polyline, straight to four decimal places (chord over length is p50
    1.0000), so the extent is the source's and only the width is convention.

    🔴 **The host is chosen by transversality, not by proximity, and this is
    the one place this stage departs from `arrows.py` and `boxjunctions.py`.**
    Both of those take the nearest level-0 edge, and both are right to: an
    arrow sits mid-lane and a box sits mid-junction, so the nearest centreline
    is the one they belong to. A stop line sits at a junction **mouth**,
    frequently a metre off the *major* road's kerb while being drawn across
    the *minor* one — `RM1013`'s midpoint is p50 **1.10 m** from the nearest
    centreline — so proximity hands it the wrong host by construction.
    Measured over the region before this shipped, as `|90 - angle to host|`:

        join                RM1011                      RM1013
        nearest edge        p50 10.8  over 30 deg 47/120  p50 16.5  28/83
        transverse pick     p50  1.8  over 30 deg  5/120  p50  4.0   8/83

        host differs from the nearest edge on 53/120 and 36/83 — 44% and 43%

    A wrong host does not move the paint, because the extent is published. It
    moves the *height*, the refusal and every counter — and two arms of one
    junction disagree about the deck by a measured 0.43 m where they meet
    (`Q60`, `boxjunctions`), so it is a bar sunk into or floating over the
    asphalt at the one place the player is looking.

    ⚠️ **`axis_residual_deg` under this rule grades a rule that optimises the
    thing it reports**, which is `Q58`'s `drawn_gauge_m` trap wearing new
    clothes. So the counter that can actually see this regress is
    `host_disagreement` — chosen against naive-nearest — published beside the
    distance the pick travelled. The residual is published too, over the
    refusals as well as the keeps, and is worth exactly what that caveat leaves
    it worth.

    ⚠️ **There is no material here, and its absence is the decision** — the
    paragraph `Arrows` and `BoxJunctions` both carry. The white is authored in
    `game/tuning/roadmarks.tres`, outside `Q33`'s exposure rule, and the glTF
    material *name* the engine dispatches on is `ROADMARKS_MATERIAL` in
    `pipeline/roadmarks.py`.
    """

    # ⚠️ **The transverse pick's search radius, and it is not a `max_offset_m`.**
    # `arrows.max_offset_m` bounds how far a symbol may be from its host; this
    # bounds which edges are *considered*, and the winner is then chosen on
    # angle. Measured: at 20 m every one of the region's 209 at-grade parts finds a
    # candidate, and the chosen host sits p50 7.23 m / p90 16.78 m away for
    # `RM1011`. That is much further than an arrow ever is from its edge, and
    # correctly so — a bar across a four-lane mouth starts on the far kerb.
    host_radius_m: float
    # How far the chosen host may sit from square across the marking before the
    # match is refused. `arrows.bearing_tolerance_deg`'s value and its logic
    # inverted: there a symbol must lie *along* its edge, here across it.
    # 30 deg keeps 114 of 120 `RM1011` and 75 of 83 `RM1013`; what it refuses is
    # the long tail that is not a transverse bar at all — a 56.9 m `RM1013`
    # lying 78.8 deg off square is the extreme.
    bearing_tolerance_deg: float
    # Degrees of angular error one metre of extra distance is worth, when two
    # candidate edges are equally square across the marking. Small on purpose:
    # this breaks ties, and anything large enough to overturn a 5 deg angular
    # difference would be proximity deciding the host again.
    proximity_weight_deg_per_m: float
    # Pitch a drawn line is stationed at along its length. Every station takes
    # its own height from the road under it, so this is what lets a 33 m bar
    # follow the crown of a wide street instead of chording across it.
    station_m: float
    # ⚠️ **Above `arrows.lift_m`, and the order is a legibility call rather than
    # a fact about paint.** A stop line is the boundary the player must not
    # cross; an arrow is an instruction they have already read by the time they
    # reach it. So where the two overlap the bar wins, on the same shape of
    # argument `boxjunctions.lift_m` uses to put arrows over box hatching.
    lift_m: float
    # The plan side of the cells `roadmarks.glb` is cut into, one mesh each, so
    # the engine can cull the layer (`P3-40`, `Q135`; `meshbuild.CellBuilder`).
    # A draw call against triangles, so it is authored and coarser than the
    # 150 m tile: the draw budget reads 136-150 on the seam line.
    cell_m: float
    # One entry per published marking — see `RoadMark`.
    marks: tuple[RoadMark, ...]
    # 🔴 **The publisher files ONE family of markings across sister layers, and a
    # code absent from `layer` is not absent from the source** (`Q132`). TD keeps
    # `RM1001` in `DTAD_RD_MARK_LINE` and the broken half of the same family —
    # `RM1002`, `RM1003`, the lane, centre and warning lines — in
    # `DTAD_RD_MARK_LINE_C`; `Q118` read the first alone and recorded 4,211 m of
    # at-grade double line as *absent*. Same `source` and `member`, and the same
    # roles, because they are one table the publisher split.
    more_layers: tuple[SourceLayer, ...]
    # 🔴 **The publisher's `level` codes whose paint is drawn on the DECKS
    # (`P3-37`, `Q134`); every other non-null level stays refused.** `A01` is
    # the elevated network — `traffic_aids.off_grade_codes` measured it, and 87%
    # of these layers' `A01` vertices stand over the drawn level-1 deck. `A03`
    # is the bores, which are shut (`Q21`), so it is not listed. Empty draws no
    # deck paint, which is what every build before `P3-37` did. The publisher's
    # vocabulary, so it is config (hard rule 3); upper-cased, as TD writes it.
    deck_codes: tuple[str, ...]
    # 🔴 **How much wider than life a LONGITUDINAL marking is drawn — authored,
    # and named as authored.** Every dimension in `marks:` is transcribed from
    # TD's sheet and none of them may be edited; this is a separate, explicit
    # draw-time exaggeration, so the publisher's figure stays intact in config
    # and only the geometry is stretched.
    #
    # ⚠️ **Because a truthful line is illegible, which this project has measured
    # once already.** `road_markings.gdshader` records losing its markings
    # entirely to a real 100 mm width — "under a pixel at any distance the player
    # is actually looking" — and draws its own lines at **1.88x** for that
    # reason. `RM1001` painted at the published 150 mm reads as one thin line at
    # mid distance and breaks into speckle beyond it, which is that same defect
    # reached from the other side.
    #
    # ⚠️ **Longitudinal only, and that is the point.** A stop line is met
    # face-on at a junction mouth and is legible at its published 200 mm; a line
    # running *along* the carriageway recedes to the horizon, which is the worst
    # case for a thin quad. Applying this to the transverse marks would move
    # geometry `P3-23` shipped and `underfill_m` measures.
    #
    # ⚠️ **Set to 1.0 on 2026-09-06 — the user judged 1.88 too thick from the
    # driving seat and asked for the accurate size.** The dial is kept rather
    # than deleted: 1.0 is a reviewable statement that the line is drawn as
    # published, and the mechanism is what makes any later exaggeration a config
    # change instead of an edit to a transcribed width.
    longitudinal_legibility_scale: float
    # 🔴 **Which `marks:` entry the INFERRED join borrows its shape from, or
    # None to draw no inferred join at all (`Q125`).** Where two one-way
    # carriageways run as a dual road, the line between the flows is the one
    # marking neither half's geometry locates; `surface.py` finds the pairing
    # geometrically and this stage draws it — but only along the stretches TD
    # surveyed no line of its own.
    #
    # 🔴 **This is the one placement in this stage that is not published, and
    # naming the mark is what keeps the SHAPE published.** The line drawn is
    # `RM1001`'s transcribed 150/100 double white, so what is invented is where
    # it runs and nothing about what it looks like — `Q54`'s debit stated at its
    # true size. `Q117` drew the same line in the shader from the same pairing;
    # `Q118` switched that off because it fought the survey, and this replaces
    # it with a version that yields to the survey per metre.
    #
    # ⚠️ **Omitting the key is the switch**, and it leaves a region drawing only
    # what its publisher surveyed — the honest default for a city whose survey
    # is complete, and what every region did between `Q118` and `Q125`.
    opposed_join_mark: str | None

    @property
    def opposed_join(self) -> RoadMark | None:
        """The entry the inferred join is drawn as, or None where none is named.

        Resolved here rather than held as a `RoadMark` so that `marks:` stays
        the single table — the loader checks the name against it, and two
        objects for one entry could drift apart the way a second copy always can.
        """
        if self.opposed_join_mark is None:
            return None
        return next(mark for mark in self.marks if mark.id == self.opposed_join_mark)

    @property
    def layers(self) -> tuple[SourceLayer, ...]:
        """Every layer the markings are read from, `layer` first."""
        return (self.layer, *self.more_layers)

    def mark_of(self, code: str) -> RoadMark | None:
        """The entry admitting `code`, or None where none does.

        Linear over three entries, for `Railings.class_of`'s stated reason.
        """
        for mark in self.marks:
            if code in mark.codes:
                return mark
        return None


_ROAD_MARK_ROLES = ("mark_type", "level")


def _road_marks(body: Any, where: str) -> RoadMarks | None:
    """The optional published transverse-marking block (`P3-23`).

    Absent, the region ships no `roadmarks.glb` and the manifest names none —
    the shape `tramway`, `arrows`, `boxjunctions` and `railings` all take. What
    is *not* offered is a fallback that paints a stop line across every arm of
    every junction: the region publishes 209 at-grade bars against 393 junction nodes
    with three or four arms each, so a derived placement would be wrong many
    times over, and every one of them would render as a perfectly good stop
    line. `Q53` refused exactly that shape of invention for box junctions.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    measures = _measures(
        body,
        where,
        ("host_radius_m", "bearing_tolerance_deg", "station_m", "lift_m", "cell_m"),
        positive=True,
    )
    if measures["bearing_tolerance_deg"] >= 90.0:
        # At 90 every angle is inside the bar, so the guard admits a marking
        # lying *along* its host — which is the failure it exists to catch, and
        # the population it actually refuses is 18 parts of the region's 209.
        raise ValueError(
            f"{where}:bearing_tolerance_deg is {measures['bearing_tolerance_deg']}; at 90 or more "
            f"it admits a marking lying along its host, which is what it exists to refuse"
        )
    # `positive=False`: zero is a legitimate weight — it says pick purely on
    # angle and break ties by source order. Negatives, which would prefer the
    # *furthest* candidate edge, `_measures` already refuses.
    weights = _measures(body, where, ("proximity_weight_deg_per_m",))

    raw_marks = _require(body, "marks", where)
    if isinstance(raw_marks, str) or not isinstance(raw_marks, (list, tuple)):
        raise ValueError(f"{where}:marks must be a list, got {raw_marks!r}")
    if not raw_marks:
        # A table with no entries admits nothing, which is what omitting the
        # block already does — refused so the difference is a decision.
        raise ValueError(f"{where}:marks is empty; a block that draws nothing is a mistake")
    marks = tuple(
        _road_mark(entry, f"{where}:marks[{index}]") for index, entry in enumerate(raw_marks)
    )

    ids = [mark.id for mark in marks]
    if len(set(ids)) != len(ids):
        # An id keys this stage's per-marking counters, so two entries sharing
        # one would merge their tallies and hide whichever drew nothing.
        raise ValueError(f"{where}:marks repeats an id: {ids}")

    admitted: dict[str, str] = {}
    for mark in marks:
        for code in mark.codes:
            if code in admitted:
                # ⚠️ Not a tidiness check, and `Railings`' reason: a code in two
                # entries is drawn twice, in one place, at two widths — and the
                # wider of them looks exactly like a correctly drawn marking.
                raise ValueError(
                    f"{where}:marks admits {code!r} in both {admitted[code]!r} and "
                    f"{mark.id!r}; it would be drawn twice and the wider would look right"
                )
            admitted[code] = mark.id

    scale = float(_require(body, "longitudinal_legibility_scale", where))
    if scale < 1.0:
        # ⚠️ **Below 1 it would draw a marking NARROWER than the publisher
        # prints it**, which is not a legibility choice but a transcription error
        # arriving through a knob that cannot be reviewed as one. Exactly 1.0 is
        # legal and means "draw it as published".
        raise ValueError(
            f"{where}:longitudinal_legibility_scale is {scale}; below 1.0 it draws a marking "
            f"narrower than the sheet publishes it, which is a transcription error and not a "
            f"legibility choice"
        )

    join_mark = body.get("opposed_join_mark")
    if join_mark is not None:
        join_mark = str(join_mark)
        entry = next((mark for mark in marks if mark.id == join_mark), None)
        if entry is None:
            # Named rather than declared inline so the shape stays the
            # publisher's: the inferred join is drawn as a transcribed marking,
            # and a block of its own here would be a place to author one.
            raise ValueError(
                f"{where}:opposed_join_mark is {join_mark!r}, which is not one of "
                f"{[mark.id for mark in marks]}; it names the entry the join is drawn as"
            )
        if entry.transverse:
            # ⚠️ A join runs ALONG the road it separates, so a transverse entry
            # would draw the pair's own bands across the two flows and fill the
            # carriageway with paint — and every counter would close.
            raise ValueError(
                f"{where}:opposed_join_mark is {join_mark!r}, which is transverse; the join runs "
                f"along the carriageways it separates and must name a longitudinal entry"
            )

    raw_layers = body.get("more_layers", [])
    if isinstance(raw_layers, str) or not isinstance(raw_layers, (list, tuple)):
        raise ValueError(f"{where}:more_layers must be a list, got {raw_layers!r}")
    more_layers = tuple(
        _source_layer(entry, f"{where}:more_layers[{index}]", _ROAD_MARK_ROLES)
        for index, entry in enumerate(raw_layers)
    )
    named = [str(_require(body, "layer", where)), *(layer.layer for layer in more_layers)]
    if len(set(named)) != len(named):
        # Read twice, every part is a candidate twice and is drawn twice in one
        # place — which looks exactly like one marking.
        raise ValueError(f"{where}:more_layers repeats a layer: {named}")

    return RoadMarks(
        **_spec_header(body, where, _ROAD_MARK_ROLES),
        marks=marks,
        more_layers=more_layers,
        deck_codes=_deck_codes(body, where),
        longitudinal_legibility_scale=scale,
        opposed_join_mark=join_mark,
        **measures,
        **weights,
    )


def _road_mark(body: Any, where: str) -> RoadMark:
    """One entry of the road-marking block's `marks` table (`P3-23`)."""
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    mark_id = str(_require(body, "id", where))
    if not mark_id:
        raise ValueError(f"{where}:id is empty; it names this marking's counters")

    raw_codes = _require(body, "codes", where)
    if isinstance(raw_codes, str) or not isinstance(raw_codes, (list, tuple)):
        raise ValueError(f"{where}:codes must be a list, got {raw_codes!r}")
    codes = tuple(str(value) for value in raw_codes)
    if not codes:
        raise ValueError(f"{where}:codes is empty; an entry that admits nothing is a mistake")
    if len(set(codes)) != len(codes):
        raise ValueError(f"{where}:codes repeats a code: {codes}")

    line_width_m = _measures(body, where, ("line_width_m",), positive=True)["line_width_m"]

    lines = _require(body, "lines", where)
    if not isinstance(lines, int) or isinstance(lines, bool) or lines < 1:
        raise ValueError(f"{where}:lines must be a positive integer, got {lines!r}")

    # ⚠️ **Only read where there is a second line for it to be a gap between.**
    # A single-line marking has none to declare, and requiring `0.0` there is a
    # field whose own docstring says it is unread — see `RoadMark`. Negatives,
    # which would overlap the two lines, `_measures` already refuses.
    lines_spacing_m = (
        _measures(body, where, ("lines_spacing_m",))["lines_spacing_m"] if lines > 1 else 0.0
    )
    if lines > 1 and lines_spacing_m <= 0.0:
        # ⚠️ The sheet's `LINES SPACING` is the **clear gap**, not a pitch — see
        # `RoadMark`. Zero here draws two touching lines, which is one line of
        # twice the width, and it renders as a perfectly good stop line.
        raise ValueError(
            f"{where}:lines_spacing_m is {lines_spacing_m} with lines={lines}; the two lines "
            f"would touch and draw as one line of twice the width"
        )

    mark_m = body.get("mark_m")
    gap_m = body.get("gap_m")
    if (mark_m is None) != (gap_m is None):
        # ⚠️ Half a module is not a default to pick. A mark with no gap is a
        # continuous line spelt at length; a gap with no mark draws nothing.
        # Both are silent, so neither is guessed at.
        raise ValueError(
            f"{where}: mark_m and gap_m must be given together or not at all; "
            f"got mark_m={mark_m!r}, gap_m={gap_m!r}"
        )
    if mark_m is not None:
        module = _measures(body, where, ("mark_m", "gap_m"), positive=True)
        mark_m, gap_m = module["mark_m"], module["gap_m"]

    # ⚠️ **Required, with no default.** Defaulting to `TRANSVERSE` would have let
    # `P3-23`'s three entries stay unedited and made the axis invisible at the one
    # place a reader decides it — and the wrong answer here draws nothing while
    # every counter closes.
    axis = str(_require(body, "axis", where))
    if axis not in MARK_AXES:
        raise ValueError(f"{where}:axis is {axis!r}, not one of {MARK_AXES}")

    broken_line = body.get("broken_line")
    if broken_line is not None:
        broken_line = str(broken_line)
        if broken_line not in BROKEN_SIDES:
            raise ValueError(f"{where}:broken_line is {broken_line!r}, not one of {BROKEN_SIDES}")
        if lines != 2 or mark_m is None:
            # One line has no side, and with no module nothing is broken — either
            # way the key would be read by nobody and look like a decision.
            raise ValueError(
                f"{where}:broken_line needs lines=2 and a module; got lines={lines}, "
                f"mark_m={mark_m!r}"
            )

    divides_flows = body.get("divides_flows", False)
    if not isinstance(divides_flows, bool):
        raise ValueError(f"{where}:divides_flows must be a boolean, got {divides_flows!r}")
    if divides_flows and axis != LONGITUDINAL:
        raise ValueError(
            f"{where}:divides_flows is set on a transverse marking; a divider runs along the "
            f"flows it separates"
        )

    chevron_width_m = body.get("chevron_width_m")
    chevron_turn_deg = body.get("chevron_turn_deg")
    if (chevron_width_m is None) != (chevron_turn_deg is None):
        raise ValueError(
            f"{where}: chevron_width_m and chevron_turn_deg are declared together or not at "
            f"all; the turn is what says which parts take the width"
        )
    if chevron_width_m is not None:
        chevron_width_m, chevron_turn_deg = float(chevron_width_m), float(chevron_turn_deg)
        if axis != OBLIQUE:
            raise ValueError(f"{where}:chevron_width_m is set on a marking that is not oblique")
        if chevron_width_m <= line_width_m:
            raise ValueError(
                f"{where}:chevron_width_m {chevron_width_m} must exceed line_width_m "
                f"{line_width_m}; the chevron is the broad stroke"
            )
        if not 0.0 < chevron_turn_deg < 180.0:
            raise ValueError(f"{where}:chevron_turn_deg is {chevron_turn_deg}, outside (0, 180)")

    return RoadMark(
        id=mark_id,
        codes=codes,
        line_width_m=line_width_m,
        lines=lines,
        lines_spacing_m=lines_spacing_m,
        mark_m=mark_m,
        gap_m=gap_m,
        broken_line=broken_line,
        axis=axis,
        divides_flows=divides_flows,
        chevron_width_m=chevron_width_m,
        chevron_turn_deg=chevron_turn_deg,
    )
