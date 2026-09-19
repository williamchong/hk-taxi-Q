"""`signs:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    LayerSpec,
    SourceLayer,
    _measures,
    _parse_hex,
    _require,
    _source_layer,
    _spec_header,
)

# What a sign face may be drawn from. The vocabulary is the pipeline's, not a
# city's: each word below has geometry in `pipeline/signs.py` that draws it, so a
# city naming a shape this list does not hold fails the load rather than shipping
# a plate with a hole in it.
#
# ⚠️ **There is no lettering here, and the reason is not the one this comment
# used to give.** It cited `Q42` and hard rule 8; both were wrong — hard rule 8
# is the "Crazy Taxi" trademark and `Q42` is the facade survey reading real
# *company* marks. What refused a glyph is that nothing could draw one: this
# vocabulary is geometry, and a 24-stroke character is not a shape. `Q63` settled
# where lettering does arrive — the `P3-20` atlas, sampled per plate — so it
# stays out of *this* list on the list's own rule (each word has geometry behind
# it), not on a borrowed prohibition.
SIGN_DISC = "disc"


SIGN_BAR = "bar"


SIGN_RECT = "rect"


SIGN_RECT_WIDE = "rect_wide"


SIGN_RECT_INFO = "rect_info"


SIGN_BOARD_WIDE = "board_wide"


SIGN_BOARD_TALL = "board_tall"


SIGN_TRIANGLE_DOWN = "triangle_down"


# The STOP plate. Regular, flat-topped, and sized across the flats — so like
# `disc` and unlike every `rect`, one authored number gives both extents.
SIGN_OCTAGON = "octagon"


SIGN_SLASH = "slash"


SIGN_BACKSLASH = "backslash"


SIGN_CHEVRONS = "chevrons"


SIGN_TEE = "tee"


SIGN_TEE_BAR = "tee_bar"


SIGN_ARROW_DOUBLE = "arrow_double"


SIGN_ARROW_UP = "arrow_up"


SIGN_ARROW_LEFT = "arrow_left"


SIGN_ARROW_RIGHT = "arrow_right"


SIGN_ARROW_DOWN_LEFT = "arrow_down_left"


SIGN_ARROW_DOWN_RIGHT = "arrow_down_right"


SIGN_ARROW_BENT_LEFT = "arrow_bent_left"


SIGN_ARROW_BENT_RIGHT = "arrow_bent_right"


SIGN_ARROW_U = "arrow_u"


# 🔴 **The one drawing that is not a polygon** (`P3-20`). `text` is a quad
# carrying the plate's own lettering out of the atlas `pipeline/sign_text.py`
# bakes from TD's cell — the bundle's first texture, admitted by `Q63`'s
# amendment to `mesh_contract.gd` rather than in spite of it. Its `size` is read
# and not authored, so unlike every word above it ignores what the config says
# and takes its extent from the drawing; the config still names it, because a
# face without this layer is a face whose plate has no words on it.
SIGN_TEXT = "text"


SIGN_DRAWINGS = (
    SIGN_DISC,
    SIGN_BAR,
    SIGN_RECT,
    SIGN_RECT_WIDE,
    SIGN_RECT_INFO,
    SIGN_BOARD_WIDE,
    SIGN_BOARD_TALL,
    SIGN_TRIANGLE_DOWN,
    SIGN_OCTAGON,
    SIGN_SLASH,
    SIGN_BACKSLASH,
    SIGN_CHEVRONS,
    SIGN_TEE,
    SIGN_TEE_BAR,
    SIGN_ARROW_DOUBLE,
    SIGN_ARROW_UP,
    SIGN_ARROW_LEFT,
    SIGN_ARROW_RIGHT,
    SIGN_ARROW_DOWN_LEFT,
    SIGN_ARROW_DOWN_RIGHT,
    SIGN_ARROW_BENT_LEFT,
    SIGN_ARROW_BENT_RIGHT,
    SIGN_ARROW_U,
    SIGN_TEXT,
)


# The plate outlines, a subset of the above: what a sign is *cut* to. A layer may
# be any drawing, but the plate itself has to be a closed outline with a back.
SIGN_PLATES = (
    SIGN_DISC,
    SIGN_RECT,
    SIGN_RECT_WIDE,
    SIGN_RECT_INFO,
    SIGN_BOARD_WIDE,
    SIGN_BOARD_TALL,
    SIGN_TRIANGLE_DOWN,
    SIGN_OCTAGON,
)


# The livery `pipeline/signs.py` reserves for a plate's back and its post, which
# no `faces:` row names. ⚠️ **Validated in `_signs` rather than trusted**: it is
# the one colour key the face table cannot vouch for, so a city naming its livery
# in its own words would load, pass every config test, and then die partway
# through the build on a bare `KeyError`.
SIGN_BACK_COLOUR = "grey"


# How a stack is ordered on its post: main sign on top, supplementary plate
# hanging below it. The numbers are `hk-traffic-sign-map`'s `compute-stacks.mjs`
# ranks, and the *names* are the titles of the publisher's own index-plan sheets
# — CT174/51-1(1)C is "TRAFFIC SIGNS (REGULATORY)" and CT174/51-3(2)D is
# "TRAFFIC SIGNS (SUPPLEMENTARY)" — so a face's rank is transcribed rather than
# judged, which is `Q59`'s glyph-table rule applied to one more column.
SIGN_RANKS = {"regulatory": 0, "warning": 1, "informatory": 2, "supplementary": 9}


SIGN_RANK_DEFAULT = "regulatory"


@dataclass(frozen=True)
class SignLayer:
    """One flat coloured shape on the front of a plate.

    `size` is a fraction of the plate's own dimension rather than a length in
    metres, so a 600 mm disc and a 900 mm disc scale together — the reason
    `ArrowGlyph.length_m` gives for keeping proportions off absolute numbers.
    """

    draw: str
    colour: str
    size: float


@dataclass(frozen=True)
class SignFace:
    """One publisher `SIGNID`: the plate it is cut to, and what is drawn on it.

    ⚠️ **This mapping is the one thing here that no grader in this repo can
    check**, the same debt `Arrows.glyphs` carries. Every consumer downstream
    takes "TS115 means NO ENTRY" on trust, exactly as `Q56` found every consumer
    taking double-versus-single on trust from `NSR.TIME_ZONE`. The codes are
    defined in the publisher's own TS index plan sheets, inside
    `traffic_aids_data_dictionary` — read them, and do not infer a face from the
    histogram. `Q59` records what reading the histogram cost the arrows.
    """

    plate: str
    layers: tuple[SignLayer, ...]
    # Where this face sits when several share a post — lower is higher up. See
    # `SIGN_RANKS`; a face that does not say is `regulatory`.
    rank: int
    # 🔴 **Whether this face is mirrored to point away from its own kerb.** Only
    # the deviation boards set it, and only because TD publishes no left/right
    # code pair for one the way it does for `TS615`/`TS616`/`TS617` — so unlike
    # every other face here, which way it points is *derived*. `Q66` records the
    # assumption and the counter that keeps it visible.
    mirror_by_side: bool = False
    # 🔴 **Whether this face addresses traffic that must NOT be here** (`Q72`).
    #
    # Almost every sign speaks to the traffic already legally proceeding — GIVE
    # WAY, the mandatory movement discs, the turn prohibitions, ONE WAY TRAFFIC —
    # so it stands facing back down the road at them, which is what
    # `_facing_from_side` derives. A NO ENTRY is the exception and it is the
    # opposite: it sits at the mouth a driver must not come *in* by, addressing
    # someone travelling against the flow, so it faces **with** the flow.
    #
    # ⚠️ **A face, not a post, and that is the whole point.** One post commonly
    # carries a GIVE WAY and a NO ENTRY, and they are back-to-back on the real
    # street — 82 of this region's 499 posts. Deriving the facing from the pole
    # alone cannot express that, and drew all 84 of those NO ENTRY plates turned
    # to face the traffic they are not addressing.
    faces_against_traffic: bool = False

    @property
    def lettered(self) -> bool:
        """Whether any layer on this face is words rather than a shape.

        The one definition, because three call sites and a grader ask it and a
        fourth answer would be a way for them to disagree — `signs.py` gates the
        atlas bake on it, `sign_face_survey.py` notes it, and `_signs` below
        validates `text_cell_px`/`text_source` against it.
        """
        return any(layer.draw == SIGN_TEXT for layer in self.layers)


@dataclass(frozen=True)
class Signs(LayerSpec):
    """Published traffic signs, and how `P3-16` draws them.

    ⚠️ **The sign layer does not say where a sign is.** `DTAD_TS_ABV_PT` is the
    publisher's *"Traffic sign abbreviation point"* — the label placed near the
    pole so the drawing stays legible — and `DTAD_TS_POLE_PT` is the object.
    Measured: **zero** of the region's 3,276 abbreviation points sit on a pole,
    nearest pole p50 2.63 m, and the offset direction is uncorrelated with
    `ANGLE`. So the published point is read as **data, never as geometry**,
    which is `Q54`'s rule and the same move `Arrows` makes with its lane
    registration. `poles` carries the layer that does say where.

    ⚠️ **`GG_NAME` is the join, and it is the only one there is.** The spec calls
    it *"Graphical group Name"*; 92.6% of the region's signs resolve through it
    to exactly one pole. A sign resolving to none, or to more than one, is
    refused and counted rather than dragged onto the nearest pole.

    ⚠️ **Every dimension below is authored, and that is not a choice.** The TS
    index sheets are stamped "NOT TO SCALE" and refer dimensions out to working
    drawings that the published `dataspec` bundle does not contain. This is the
    debt `Q60` recorded for railing height, restated: these are the
    weakest-evidenced numbers in the block, and none of them is a *position*.

    ⚠️ **Unlike `Arrows` and `BoxJunctions`, this block does carry colours, and
    the departure is deliberate.** Those two ship one paint each and put it in
    their `.tres` beside the markings they match. A sign plate is four colours
    and the whole layer is one draw call, so the colour has to travel on the
    vertex — `signs.glb` ships `COLOR_0` and `signs.gdshader` reads it straight
    to `ALBEDO`. A channel earns its place when something reads it, which is the
    bar `Q54` set when it found `COLOR_0.a` broadcasting an unread 255 down the
    road mesh. The livery is a *city* fact besides (hard rule 3).
    """

    # The pole layer, in the same source. Its geometry is what a sign is drawn on.
    poles: SourceLayer
    # Publisher code -> the face drawn for it. A code absent here is refused.
    # 🔴 **"which is how ~2,360 text-faced signs stay out (`Q42`, hard rule 8)"
    # was here, and BOTH citations were wrong** — hard rule 8 is the "Crazy Taxi"
    # trademark and `Q42` is the facade survey reading real *company* marks.
    # `Q63` corrected that in `signs.py` and this copy was missed. What the
    # whitelist is actually for is `Q65`'s scope: the time, parking, zone and
    # vehicle-class plates are out as **content**, because a taxi game's signage
    # is the part that instructs the driver. A drifting copy of a reason is worse
    # than no copy, which is `mesh_contract.gd`'s own header.
    faces: dict[str, SignFace]
    # Named livery, referenced by every `SignLayer.colour`. `#rrggbb` as 0-255,
    # the form every other colour in the city file takes.
    colours: dict[str, tuple[int, int, int]]

    disc_diameter_m: float
    triangle_height_m: float
    # Across the flats, not corner to corner — the dimension a STOP plate is
    # specified by, and the one that makes its bounding box square.
    octagon_height_m: float
    rect_width_m: float
    rect_height_m: float
    rect_wide_width_m: float
    rect_wide_height_m: float
    rect_info_width_m: float
    rect_info_height_m: float
    board_wide_width_m: float
    board_wide_height_m: float
    board_tall_width_m: float
    board_tall_height_m: float

    # Bottom of the lowest plate above the ground.
    mount_height_m: float
    # Vertical gap between two plates stacked on one pole.
    stack_gap_m: float
    pole_radius_m: float
    pole_sides: int
    pole_headroom_m: float
    disc_segments: int
    # 🔴 **Side of one atlas cell, and the bundle's only texture dimension**
    # (`P3-20`). A face carrying a `text` layer gets one square cell of this many
    # pixels, laid in a row, so the whole atlas is `cell_px x cell_px x cells` —
    # which is what `mesh_contract.gd`'s declared budget is measured against and
    # what `PROGRESS.md`'s `Texture memory` stops being 0 for. ⚠️ Raising it is a
    # budget change and has to move a number in `generated_layer.gd` in the same
    # diff, which is `Q63`'s entire point: an image ships when someone declares
    # room for it, never because it fitted.
    text_cell_px: int
    # 🔴 **Which declared source the lettering is baked from, and it is NOT the
    # layer's own.** `source` above is the fgdb the sign points live in; the
    # glyphs come off the publisher's index-plan sheets, which ship in a
    # different archive entirely. Named here rather than reached for in
    # `sign_text.py` because hard rule 3 puts every source id in the city file —
    # a second city letters its signs from its own publisher's drawings or from
    # nothing.
    text_source: str | None
    # How far each face layer floats in front of the one beneath it. Coplanar
    # layers z-fight, the reason `Arrows.lift_m` exists — but a plate is
    # vertical, so this runs along the plate normal rather than up.
    layer_lift_m: float

    max_offset_m: float
    # Furthest a sign may sit from the pole its `GG_NAME` names. ⚠️ Taken from
    # `hk-traffic-sign-map`'s own 15 m group-span cap, which exists because
    # `GG_NAME` is reused across signs kilometres apart.
    max_pole_span_m: float
    # How far outside the **drawn** carriageway edge a post stands, and the bar on
    # the move that puts it there. ⚠️ **The position is registered, not read** —
    # 77.3% of the region's poles are surveyed inside the 1.6x ribbon, so drawn
    # where published three quarters of the city's signs stand in the road. This
    # is `Q60`'s railing registration arriving at a second layer.
    # 🔴 **And the move is clamped to that direction (`Q78`).** `outset_m` is the
    # threshold as well as the offset: a post surveyed further out than
    # `half_width + outset_m` keeps the point TD surveyed, because the argument
    # for moving it — a ribbon drawn 1.6x too wide — runs outward only. Assigning
    # the target unconditionally pulled 95 of 654 posts *toward* the carriageway,
    # invisibly, because `shift_m` is an absolute value.
    outset_m: float
    max_shift_m: float
    # Two poles closer than this are one post: the layer publishes coincident
    # poles where several `GG_NAME` groups share one, and drawn apart they
    # interpenetrate.
    pole_merge_m: float

    # 🔴 **Where a published turn restriction stops being a left or a right**,
    # for the diff `signs._record_semantics` runs against the graph's 217 banned
    # movements (`Q62`). They are here rather than in the code because the graph
    # publishes no restriction *type*: `P1-3` reads `OTHER_REST_TYPE` and never
    # emits it, so the class of a banned movement is read off its own geometry
    # and these two numbers are what read it.
    #
    # ⚠️ **They classify, they never refuse.** Nothing downstream is gated on
    # the answer — the diff is report-only for `Q56`'s reason — so a movement
    # that falls between them is counted as neither a left nor a right rather
    # than dropped.
    turn_straight_deg: float
    turn_u_deg: float


_SIGN_ROLES = ("code", "bearing", "level", "group")


_SIGN_POLE_ROLES = ("group", "level")


def _signs(body: Any, where: str) -> Signs | None:
    """The optional published-traffic-sign block (`P3-16`).

    Absent, the region ships no `signs.glb` and the manifest names none — the
    shape `tramway`, `arrows`, `boxjunctions` and `railings` all use. What is
    **not** offered is a fallback that puts a sign at every one-way mouth: the
    whole defence of this layer is that its content is read, and a fallback
    would reintroduce invented instruction silently on any city missing the
    block. `Q54`'s sourced-not-invented rule.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    colours: dict[str, tuple[int, int, int]] = {}
    raw_colours = _require(body, "colours", where)
    if not isinstance(raw_colours, dict) or not raw_colours:
        raise ValueError(f"{where}:colours must be a non-empty mapping of name to RGB")
    for name, value in raw_colours.items():
        spot = f"{where}:colours.{name}"
        if not isinstance(value, str):
            raise ValueError(f"{spot} must be a #rrggbb colour, got {value!r}")
        colours[str(name)] = _parse_hex(value, spot)

    if SIGN_BACK_COLOUR not in colours:
        raise ValueError(
            f"{where}:colours does not name {SIGN_BACK_COLOUR!r}, which every plate's back and "
            f"every post is drawn in — see SIGN_BACK_COLOUR"
        )

    raw_faces = _require(body, "faces", where)
    if not isinstance(raw_faces, dict) or not raw_faces:
        raise ValueError(f"{where}:faces must be a non-empty mapping of code to face")
    faces: dict[str, SignFace] = {}
    for code, entry in raw_faces.items():
        spot = f"{where}:faces.{code}"
        if not isinstance(entry, dict):
            raise ValueError(f"{spot} must be a mapping with plate and layers, got {entry!r}")
        plate = str(_require(entry, "plate", spot))
        if plate not in SIGN_PLATES:
            # A plate is what the sign is *cut* to, so it needs a closed outline
            # and a back. A layer may be any drawing; this may not.
            raise ValueError(
                f"{spot}:plate is {plate!r}, which is not one of {', '.join(SIGN_PLATES)}"
            )
        raw_layers = _require(entry, "layers", spot)
        if isinstance(raw_layers, str) or not isinstance(raw_layers, (list, tuple)):
            raise ValueError(f"{spot}:layers must be a list, got {raw_layers!r}")
        if not raw_layers:
            # A face with no layers is a bare plate — a blank sign, which
            # instructs nothing and renders perfectly. Refused: an empty list is
            # a transcription that went wrong, not a sign that exists.
            raise ValueError(f"{spot}:layers is empty; a plate with nothing on it is not a sign")
        layers: list[SignLayer] = []
        for index, raw_layer in enumerate(raw_layers):
            here = f"{spot}:layers[{index}]"
            if not isinstance(raw_layer, dict):
                raise ValueError(f"{here} must be a mapping with draw, colour and size")
            draw = str(_require(raw_layer, "draw", here))
            if draw not in SIGN_DRAWINGS:
                raise ValueError(
                    f"{here}:draw is {draw!r}, which is not one of "
                    f"{', '.join(SIGN_DRAWINGS)} — the pipeline has no geometry to draw it"
                )
            colour = str(_require(raw_layer, "colour", here))
            if colour not in colours:
                # Caught here rather than at draw time: an unknown colour would
                # otherwise fall back to something and render as a plausible
                # sign in the wrong livery.
                raise ValueError(
                    f"{here}:colour is {colour!r}, which {where}:colours does not name"
                )
            size = float(_require(raw_layer, "size", here))
            if not 0.0 < size <= 1.0:
                raise ValueError(
                    f"{here}:size is {size}; it is a fraction of the plate's own dimension "
                    f"and must be greater than 0 and no more than 1"
                )
            layers.append(SignLayer(draw=draw, colour=colour, size=size))
        if sum(layer.draw == SIGN_TEXT for layer in layers) > 1:
            # `sign_text.py` bakes ONE cell per face and `_draw_plate` hands it
            # to every `text` layer, so a second one silently repeats the first's
            # words and ignores its own `colour` — a plate with the same phrase
            # on it twice, rendering perfectly.
            raise ValueError(
                f"{spot}:layers carries more than one text layer; a face is baked one cell "
                f"of lettering, so the second would repeat the first's words"
            )
        if layers[0].draw == SIGN_TEXT:
            # 🔴 **The field a glyph is baked over is the layer beneath it**, so
            # a leading `text` layer has nothing to sit on. `sign_text.py` would
            # have to invent a colour, and the one it invented before `TS101`
            # was `white` — which on a red plate bakes a white box with the
            # words in it and renders as a sticker stuck to the sign.
            raise ValueError(
                f"{spot}:layers begins with text; lettering is baked over the layer beneath "
                f"it, so a face needs a plate colour drawn before its words"
            )
        rank = str(entry.get("rank", SIGN_RANK_DEFAULT))
        if rank not in SIGN_RANKS:
            raise ValueError(
                f"{spot}:rank is {rank!r}, which is not one of "
                f"{', '.join(SIGN_RANKS)} — those are the index-plan sheet classes"
            )
        mirror = entry.get("mirror", False)
        if not isinstance(mirror, bool):
            raise ValueError(
                f"{spot}:mirror is {mirror!r}; it is a flag, and the only thing it may say is "
                f"that this face points away from the kerb its post stands on"
            )
        if mirror and any(layer.draw == SIGN_TEXT for layer in layers):
            # 🔴 A mirrored glyph is `Q66`'s whole mechanism and it is exactly
            # wrong for words: `_draw_plate` negates `u` to turn a chevron round,
            # and lettering turned round is lettering written backwards. It would
            # render perfectly, on a plate whose whole job is to be read.
            raise ValueError(
                f"{spot} both mirrors and carries a text layer; mirroring writes its "
                f"lettering backwards. A mirrored face is a face with no words on it"
            )
        against = entry.get("faces_against_traffic", False)
        if not isinstance(against, bool):
            raise ValueError(
                f"{spot}:faces_against_traffic is {against!r}; it is a flag, and the only "
                f"thing it may say is that this face addresses traffic coming the other way"
            )
        if mirror and against:
            # 🔴 **Latent until a face carries both, and then silent.** `_mirrors`
            # decides which hand the carriageway is on from `post.side` alone,
            # and `_plate_facing_deg` turning the plate 180 degrees swaps that —
            # so a face that both mirrors and faces against traffic would mirror
            # its glyphs the wrong way and render perfectly. Refused at load, in
            # the idiom of the mirror-plus-text guard above, rather than left for
            # someone to find in a frame.
            raise ValueError(
                f"{spot} both mirrors and faces against traffic; mirroring reads the kerb "
                f"side that turning the plate has just reversed. One face may do either"
            )
        faces[str(code)] = SignFace(
            plate=plate,
            layers=tuple(layers),
            rank=SIGN_RANKS[rank],
            mirror_by_side=mirror,
            faces_against_traffic=against,
        )

    lengths = {
        name: float(_require(body, name, where))
        for name in (
            "disc_diameter_m",
            "triangle_height_m",
            "octagon_height_m",
            "rect_width_m",
            "rect_height_m",
            "rect_wide_width_m",
            "rect_wide_height_m",
            "rect_info_width_m",
            "rect_info_height_m",
            "board_wide_width_m",
            "board_wide_height_m",
            "board_tall_width_m",
            "board_tall_height_m",
            "mount_height_m",
            "stack_gap_m",
            "pole_radius_m",
            "pole_headroom_m",
            "layer_lift_m",
            "max_offset_m",
            "max_pole_span_m",
            "outset_m",
            "max_shift_m",
            "pole_merge_m",
        )
    }
    negative = {name: value for name, value in lengths.items() if value <= 0.0}
    if negative:
        raise ValueError(
            f"{where}: {', '.join(sorted(negative))} must each be positive; got {negative}"
        )

    disc_segments = int(_require(body, "disc_segments", where))
    if disc_segments < 3:
        raise ValueError(f"{where}:disc_segments is {disc_segments}; a disc needs at least 3")
    pole_sides = int(_require(body, "pole_sides", where))
    if pole_sides < 3:
        raise ValueError(f"{where}:pole_sides is {pole_sides}; a prism needs at least 3")
    text_cell_px = int(body.get("text_cell_px", 0))
    text_source = body.get("text_source")
    lettered = sorted(code for code, face in faces.items() if face.lettered)
    if lettered and text_cell_px < 8:
        raise ValueError(
            f"{where}:text_cell_px is {text_cell_px}, but {', '.join(lettered)} carry text "
            f"layers. A cell has to be big enough to hold a character"
        )
    if lettered and not text_source:
        raise ValueError(
            f"{where}: {', '.join(lettered)} carry text layers but text_source names no "
            f"archive to bake their lettering from"
        )

    poles_body = _require(body, "poles", where)
    if not isinstance(poles_body, dict):
        raise ValueError(f"{where}:poles must be a mapping, got {poles_body!r}")

    turns = _measures(body, where, ("turn_straight_deg", "turn_u_deg"))
    if not 0.0 < turns["turn_straight_deg"] < turns["turn_u_deg"] < 180.0:
        # Ordered rather than merely positive, because the two bound one band
        # between them. Equal, they leave no left and no right at all and the
        # diff would report every plate as disagreeing with a graph that agrees.
        raise ValueError(
            f"{where}: turn_straight_deg {turns['turn_straight_deg']} and turn_u_deg "
            f"{turns['turn_u_deg']} must ascend inside (0, 180), or no movement is a turn"
        )

    return Signs(
        **_spec_header(body, where, _SIGN_ROLES),
        poles=_source_layer(poles_body, f"{where}:poles", _SIGN_POLE_ROLES),
        faces=faces,
        colours=colours,
        disc_diameter_m=lengths["disc_diameter_m"],
        triangle_height_m=lengths["triangle_height_m"],
        octagon_height_m=lengths["octagon_height_m"],
        rect_width_m=lengths["rect_width_m"],
        rect_height_m=lengths["rect_height_m"],
        rect_wide_width_m=lengths["rect_wide_width_m"],
        rect_wide_height_m=lengths["rect_wide_height_m"],
        rect_info_width_m=lengths["rect_info_width_m"],
        rect_info_height_m=lengths["rect_info_height_m"],
        board_wide_width_m=lengths["board_wide_width_m"],
        board_wide_height_m=lengths["board_wide_height_m"],
        board_tall_width_m=lengths["board_tall_width_m"],
        board_tall_height_m=lengths["board_tall_height_m"],
        mount_height_m=lengths["mount_height_m"],
        stack_gap_m=lengths["stack_gap_m"],
        pole_radius_m=lengths["pole_radius_m"],
        pole_sides=pole_sides,
        pole_headroom_m=lengths["pole_headroom_m"],
        disc_segments=disc_segments,
        text_cell_px=text_cell_px,
        text_source=None if text_source is None else str(text_source),
        layer_lift_m=lengths["layer_lift_m"],
        max_offset_m=lengths["max_offset_m"],
        max_pole_span_m=lengths["max_pole_span_m"],
        outset_m=lengths["outset_m"],
        max_shift_m=lengths["max_shift_m"],
        pole_merge_m=lengths["pole_merge_m"],
        turn_straight_deg=turns["turn_straight_deg"],
        turn_u_deg=turns["turn_u_deg"],
    )
