"""The lettering on a sign plate, baked from TD's own cell (`P3-20`, `Q68`).

🔴 **This is the bundle's first texture, and `Q63` is the permission slip.**
`mesh_contract.gd` used to fail any shader uniform holding a `Texture` at all;
it now fails one whose call site does not declare a pixel budget, and fails a
declared texture that overruns it or never arrives. So `Texture memory` stops
being 0 and becomes a number with a ceiling. Nothing here is allowed to be the
reason that ceiling stops being read.

**What it is for.** `TS102` GIVE WAY reads "GIVE WAY / 讓" on the index sheet and
shipped as a bare red triangle — from the road, a blank plate, which is how the
user found it. `Q65` priced the alternatives and the user's call was the real
character rather than a thickened wordless border.

⚠️ **THE GLYPH IS READ, NOT DRAWN, AND ITS PLACEMENT IS READ TOO.** The cell is
cropped to the *plate's own bounding box* first, the lettering's box is measured
inside that, and both come out as fractions of the plate. So where the words sit
on the triangle is the publisher's decision, not an authored offset — which is
the same move `arrows.py` makes with `symbol_size` and the opposite of the
per-layer offset the face schema deliberately does not have.

⚠️ **The atlas is OPAQUE RGB, with no alpha and no discard**, and that is the
narrowest amendment available to the no-texture rule. Three roads were open:
a coverage mask read into `ALPHA`, a cutout with `discard`, and this. The first
two put the sign layer into a transparency pass or a mip-thinning artefact for a
glyph a few pixels tall, and both would have made `ALPHA` a dial on a mesh whose
shader records that it must not have one (`railings.gdshader`'s note, and
`marking_paint.gdshader`'s misreading of `paint_opacity` before it). Baking the field
colour behind the glyph costs nothing instead: the quad sits inside the white
field it matches, so its edges are invisible, and the shader is one sample.

⚠️ **Baking the livery in does not move it out of the config.** The colours come
from `signs.colours` at build time, so a second city's atlas is its own (hard
rule 3), and the generated PNG is city data — gitignored, never committed, and
never relicensed (hard rule 7).

⚠️ **What can go wrong here is silent, twice over.** A cell that crops the wrong
region bakes a blank white square, and a plate with a blank square on it renders
as the blank plate it already was; a cell cropped from the wrong *code* bakes
someone else's words and renders perfectly. So `coverage` — the fraction of the
cell the ink actually covers — is published per cell in `signs.json`, and a cell
that comes out near zero is the failure showing itself. `Q58`'s rule, applied to
an image.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pipeline.colour import luminance
from pipeline.config import SIGN_TEXT, SignFace, Signs
from pipeline.sign_sheets import enclosed_white, flood, ink_masks, load_sheet

log = logging.getLogger(__name__)

# 🔴 **The ink test, and it is deliberately not the survey tool's.** That one
# classifies a cell into livery *families* to grade proportions; this one asks
# one question — is this pixel part of the lettering — and the answer has to
# keep antialiasing, because a glyph this small is mostly edge. So coverage is
# read as "how far from paper is this pixel", and anything with a red cast is
# forced to zero so the plate's own border cannot leak in as ink.
_RED_CAST = 40
# A glyph colour whose channels spread wider than this (0-255 units) is a
# coloured ink, not a grey: the shipped black and white spread 10 at most, the green and red 107+.
_CHROMATIC_SPREAD = 60.0


@dataclass(frozen=True)
class TextCell:
    """One face's lettering: where it sits on the plate, and where in the atlas.

    `plate_rect` is `(u0, v0, u1, v1)` in the plate's own frame, where `u` and
    `v` run `-1..1` across the plate's bounding box — so it is a *fraction*, and
    a 600 mm plate and a 900 mm one place their words identically.
    """

    plate_rect: tuple[float, float, float, float]
    uv_rect: tuple[float, float, float, float]
    coverage: float


@dataclass(frozen=True)
class TextAtlas:
    png: bytes
    width: int
    height: int
    cells: dict[str, TextCell] = field(default_factory=dict)

    @property
    def pixels(self) -> int:
        """What `mesh_contract.gd`'s declared budget is measured against."""
        return self.width * self.height


@dataclass(frozen=True)
class Livery:
    """A lettered face's two colours, and which way its glyph is cut.

    🔴 **Both were hardcoded and both were already in the config.** The `text`
    layer carries a `colour` that nothing read, and the layer beneath it is the
    field the words sit on — so `TS102` is black-on-white and `TS101` is
    white-on-red without the face schema growing anything. The comment this
    replaces said a face whose lettering is not black "would need this to be a
    parameter"; `TS101` is that face.

    ⚠️ **One object rather than two same-shaped arrays**, because `(glyph,
    field)` is an unlabelled pair of `(3,)` float64s: swapped at either call
    site the polarity inverts, and by this module's own doctrine the plate then
    renders perfectly. Naming them is the only thing that catches it.
    """

    glyph_rgb: np.ndarray
    field_rgb: np.ndarray
    # A second ink laid where the cell is red (`TS3643`'s taxi), or none.
    accent_rgb: np.ndarray | None = None

    @property
    def chromatic(self) -> bool:
        """Whether the glyph is a coloured ink on paper (`TS322`'s green
        minibus), which the black-ink reading sees as paper: a saturated
        colour is bright in one channel. Derived from the livery, like `knockout`."""
        spread = float(self.glyph_rgb.max() - self.glyph_rgb.min())
        return not self.knockout and spread > _CHROMATIC_SPREAD

    @property
    def knockout(self) -> bool:
        """Whether the lettering is the *paper* showing through a solid field.

        ⚠️ **Derived from the livery, never from a colour's name or a config
        flag.** `TS101` is white cut out of red and `TS102` is black on white,
        and which of those a face is decides which way its crop runs — but a
        second city's STOP is its own publisher's, so `"white"` is not a name
        this may test for (hard rule 3).

        🔴 **`colour.luminance`, not the brightest channel.** Comparing
        `max()` was the first version and it **ties on the shipped palette**:
        `white` `#f0f0ea` and `yellow` `#f0c020` are both 240, so a white glyph
        on a yellow field read as ink rather than knockout and would have baked
        a blank cell. `yellow` is real livery — it is `TS589`'s border — so that
        face is reachable config. `colour.py` says why one definition of
        luminance lives in one place; this is that.
        """
        lit = luminance(np.stack([self.glyph_rgb, self.field_rgb]))
        return bool(lit[0] > lit[1])


def _livery(spec: Signs, face: SignFace) -> Livery:
    """The glyph's colour and the field it is laid over, off the face itself."""
    index = next((i for i, layer in enumerate(face.layers) if layer.draw == SIGN_TEXT), None)
    # `config.py` refuses both of these on the way in — a face with no `text`
    # layer never reaches here, and one whose `text` layer is first has no field
    # beneath it. Raised rather than asserted, because `assert` is stripped
    # under `python -O` and this decides what colour the words are baked in.
    if index is None or index == 0:
        raise ValueError(f"{face.plate} face has no text layer with a field beneath it")
    accent = face.layers[index].accent
    livery = Livery(
        glyph_rgb=np.asarray(spec.colours[face.layers[index].colour], dtype=np.float64),
        field_rgb=np.asarray(spec.colours[face.layers[index - 1].colour], dtype=np.float64),
        accent_rgb=None if accent is None else np.asarray(spec.colours[accent], dtype=np.float64),
    )
    if accent is not None and (livery.knockout or livery.chromatic):
        # The accent is the cell's red beside a BLACK ink: a knockout has no
        # ink to sit beside, and a coloured glyph already reads the red.
        raise ValueError(f"{face.plate} face has an accent on lettering that is not black on paper")
    return livery


def build_atlas(
    spec: Signs, codes: list[str], dataspec_zip: Path, *, cell_px: int
) -> TextAtlas | None:
    """Bake one atlas row, one cell per code, from the publisher's own sheets.

    ⚠️ **A row rather than a grid**, because a grid needs a packer and a packer
    needs a reason. Two cells is the whole scope `Q65` left; a row keeps the UV
    arithmetic to one division and the atlas to a shape a person can read.
    """
    from PIL import Image

    if not codes:
        return None

    cells: dict[str, TextCell] = {}
    tiles: list[np.ndarray] = []

    # ⚠️ **Sorted NUMERICALLY, and that is `load_sheet`'s cache rather than
    # tidiness.** It holds one sheet, evicting on any change, on the stated
    # ground that its callers walk codes in order — but `"TS1000"` sorts before
    # `"TS101"` as text, and 8 of the 16 published index-plan sheets carry
    # 4-digit codes. A string sort therefore interleaves sheets and re-renders
    # 217 MB pages it had already paid for, silently. Identical to the string
    # order for today's all-3-digit table, which is why nothing has caught it.
    for index, code in enumerate(sorted(codes, key=lambda code: int(code.removeprefix("TS")))):
        number = int(code.removeprefix("TS"))
        sheet = load_sheet(dataspec_zip, number)
        cell = sheet.cell(number)

        livery = _livery(spec, spec.faces[code])

        plate = _plate_mask(cell)
        box = None if plate is None else _bounds(plate)
        if plate is None or box is None:
            raise ValueError(f"{code}: no plate found in its index-plan cell")
        x0, y0, x1, y1 = box
        coverage = _coverage(
            _crop(cell, box),
            _crop(plate, box),
            knockout=livery.knockout,
            chromatic=livery.chromatic,
            keep_red=livery.accent_rgb is not None,
        )
        accent = None
        if livery.accent_rgb is not None:
            accent = _accent(_crop(cell, box), _crop(plate, box))

        ink = _ink_box(coverage if accent is None else np.maximum(coverage, accent))
        if ink is None:
            raise ValueError(f"{code}: its index-plan cell carries no lettering to bake")
        ix0, iy0, ix1, iy1 = ink

        width = float(x1 - x0 + 1)
        height = float(y1 - y0 + 1)
        # Plate frame: `u` right, `v` **up**, both `-1..1` — so the image's `y`
        # is flipped here and not later. Getting this wrong prints the words
        # upside down on the plate, which is a thing that renders perfectly.
        plate_rect = (
            2.0 * ix0 / width - 1.0,
            1.0 - 2.0 * (iy1 + 1) / height,
            2.0 * (ix1 + 1) / width - 1.0,
            1.0 - 2.0 * iy0 / height,
        )

        lettering = coverage[iy0 : iy1 + 1, ix0 : ix1 + 1]
        second = None if accent is None else accent[iy0 : iy1 + 1, ix0 : ix1 + 1]
        tiles.append(_bake(lettering, livery, cell_px, second))
        cells[code] = TextCell(
            plate_rect=plate_rect,
            uv_rect=(index / len(codes), 0.0, (index + 1) / len(codes), 1.0),
            coverage=float(lettering.mean()),
        )
        log.info(
            "  %s lettering %.3f x %.3f of the plate, %.1f%% ink",
            code,
            0.5 * (plate_rect[2] - plate_rect[0]),
            0.5 * (plate_rect[3] - plate_rect[1]),
            100.0 * cells[code].coverage,
        )

    sheet_image = Image.fromarray(np.hstack(tiles), "RGB")
    buffer = io.BytesIO()
    sheet_image.save(buffer, format="PNG", optimize=True)
    return TextAtlas(
        png=buffer.getvalue(),
        width=sheet_image.width,
        height=sheet_image.height,
        cells=cells,
    )


def _accent(cell: np.ndarray, plate: np.ndarray) -> np.ndarray:
    """How much of each pixel the cell's red covers, `0..1` — exactly what
    `_coverage` forces out of a black-ink reading, kept for a face that says
    it has a second ink. White lettering on the red reads 0 and shows the field."""
    channels = cell.astype(np.float64)
    cast = channels[..., 0] - np.maximum(channels[..., 1], channels[..., 2])
    ink = np.clip(cast / 255.0, 0.0, 1.0)
    ink[~plate] = 0.0
    return ink


def _coverage(
    cell: np.ndarray,
    plate: np.ndarray,
    *,
    knockout: bool,
    chromatic: bool = False,
    keep_red: bool = False,
) -> np.ndarray:
    """How much of each pixel the lettering covers, `0..1`.

    ⚠️ **Antialiasing is kept on purpose.** The sheets are vector, so the glyph
    arrives with soft edges, and 讓 at the size this ships is mostly edge —
    thresholding it to hard black would cost the strokes that make it readable
    at all. This is a *resampling* problem, not a segmentation one.

    🔴 **Two polarities, because TD draws both and one of them reads as zero.**
    On `TS102` the words are black on the plate's white field, so coverage is
    distance from *paper* and the plate's red border is forced out by its cast.
    On `TS101` they are white knocked out of a solid red octagon: every pixel is
    already far from black, so this returned 0.0000 everywhere and `_ink_box`
    handed back `None`. That path reads the opposite — distance toward paper,
    which is the *darkest* channel, since a saturated field is dark in at least
    one of the three and paper is bright in all of them.

    ⚠️ **`ink[~plate]` is applied to both paths and belongs to neither.** It is
    what keeps the paper in an octagon's corners from being read as a glyph,
    which only the knockout path could get wrong — but moving it inside that
    branch would let a non-knockout face read whatever sits outside its own
    plate, so it stays where it is.
    """
    channels = cell.astype(np.float64)
    red, green, blue = channels[..., 0], channels[..., 1], channels[..., 2]
    if knockout:
        ink = np.clip(np.minimum(np.minimum(red, green), blue) / 255.0, 0.0, 1.0)
    elif chromatic:
        # A coloured ink is far from paper in its darkest channel, and its
        # border is the same ink: the whole plate is the cell (`TS322`).
        ink = np.clip(1.0 - np.minimum(np.minimum(red, green), blue) / 255.0, 0.0, 1.0)
    else:
        lightness = np.maximum(np.maximum(red, green), blue) / 255.0
        ink = np.clip(1.0 - lightness, 0.0, 1.0)
        # With an accent the red is an ink of its own and `_accent` takes its
        # share; a pixel between the red and the black keeps its black share.
        if not keep_red:
            ink[(red - np.minimum(green, blue)) > _RED_CAST] = 0.0
    ink[~plate] = 0.0
    return ink


def _crop(array: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """`array` cut to `(x0, y0, x1, y1)`, inclusive.

    ⚠️ **One function because the cell and the plate mask must be cut
    identically.** Written out twice they can diverge, and a coverage field
    measured against a mask offset from its own pixels is a plausible-looking
    wrong answer rather than an error.
    """
    x0, y0, x1, y1 = box
    return array[y0 : y1 + 1, x0 : x1 + 1]


def _bounds(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    """`(x0, y0, x1, y1)` of everything set in `mask`, inclusive."""
    if not mask.any():
        return None
    ys, xs = np.nonzero(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _plate_mask(cell: np.ndarray) -> np.ndarray | None:
    """The published plate as pixels: the ink enclosing a field, plus the field.

    ⚠️ **The same ink test `sign_face_survey.py` grades proportions with**, and
    it began as a promise it would stay so: the survey measures a face against
    the plate it finds, and a rule that moved here alone would bake a crop of a
    box nothing graded.

    🔴 **THE TWO NOW DISAGREE, WHICH IS A DEBT AND NOT A DESIGN.** This takes
    only the ink *connected to* the field; `sign_face_survey.measured()` still
    takes every inked pixel. So on `TS101` the atlas measures against 269 px and
    the survey against 308, which is why the survey reports that face's
    lettering extent as 0.63 x 0.59 where the bake logs 0.725 x 0.651 — the same
    0.873 ratio. The survey is inflated on **10 of 21** faces (`TS101`,
    `TS106`-`TS112`, `TS414`, `TS615`) and correcting it moves ten published
    rows, `TS615` by more than 2x, so it is a change to the *grader* and is owed
    its own diff. Its area column is unaffected — that is a share of the mask
    rather than of the box.

    🔴 **Why the connectivity, and what reading every inked pixel cost.** TD
    draws a dimension across each cell and its two extension lines are red, 3 px
    wide and outside the plate. Everything here is a *fraction* of this, so
    taking them in is invisible: on `TS101`'s centre row the red runs are
    163-165, 182-450 and 468-470, giving a box of 308 where the octagon is
    269 — and the words would have shipped at **0.873** of the size the
    publisher draws them, rendering perfectly. `Q67` refused every straight
    mandatory arrow at 17% small for the same reason. Verified byte-identical on
    every red/black face (`TS102`, `TS115`, `TS116`, `TS131`-`TS133`, `TS183`,
    `TS733`-`TS735`); on `TS101` it returns a 269 x 269 square, which is what an
    octagon's bounding box has to be.

    ⚠️ **A knockout needs the mask, not its box.** An octagon's bounding box has
    paper in its corners, and on a reverse-livery face paper is what the glyph is
    made of — so cropping to the box alone reads the corners as lettering.

    ⚠️ A cell whose ink encloses no white at all falls back to all of it rather
    than returning nothing. No face in scope does that — every plate has a field
    or a knockout — but a plate drawn as a solid blob is a face with nothing on
    it, and refusing it here would report as missing lettering.
    """
    # Green is the stand plates' field (`TS324`, `P3-92`); no other cell in scope
    # carries any, so the red and black faces' masks are unmoved.
    masks = ink_masks(cell, ("red", "black", "green"))
    inked = masks["red"] | masks["black"] | masks["green"]
    if not inked.any():
        return None
    field = enclosed_white(inked)
    if not field.any():
        return inked
    # Every enclosed-white component touches ink by construction, so flooding
    # *from* the field across `inked | field` reaches exactly the field plus the
    # ink connected to it. No separate seed dilation is needed.
    return flood(field, inked | field)


def _ink_box(coverage: np.ndarray) -> tuple[int, int, int, int] | None:
    """The lettering's own bounding box within the plate, in pixels."""
    return _bounds(coverage > 0.5)


def _bake(
    coverage: np.ndarray, livery: Livery, cell_px: int, accent: np.ndarray | None = None
) -> np.ndarray:
    """One square RGB tile: the glyph's own colour laid over the plate's field.

    ⚠️ **Resampled on the coverage and composited afterwards**, never the other
    way round. Compositing first and then shrinking averages *colour*, which
    drags the black of a stroke toward the field and thins the glyph unevenly;
    averaging coverage and compositing once keeps a half-covered texel exactly
    half-covered. It is the same mistake as premultiplied alpha, arriving
    without any alpha to warn you.
    """
    from PIL import Image

    def resampled(field: np.ndarray) -> np.ndarray:
        source = Image.fromarray((np.clip(field, 0.0, 1.0) * 255.0).astype(np.uint8), "L")
        small = np.asarray(source.resize((cell_px, cell_px), Image.LANCZOS), dtype=np.float64)
        return np.clip(small / 255.0, 0.0, 1.0)[..., None]

    mask = resampled(coverage)
    # 🔴 **The glyph's colour is the face's, and there are two of them now.**
    # This read `spec.colours["black"]` and said a face whose lettering is not
    # black "would need this to be a parameter". `TS101` is white on red and is
    # that face, so both colours come in from `_livery` — off the config the
    # face already carries, not off a new schema.
    blended = livery.field_rgb * (1.0 - mask) + livery.glyph_rgb * mask
    if accent is not None and livery.accent_rgb is not None:
        # Three shares of one texel, never one composite over another: an edge
        # between the red and the black is half each, with no paper in it.
        second = np.minimum(resampled(accent), 1.0 - mask)
        blended = (
            livery.field_rgb * (1.0 - mask - second)
            + livery.glyph_rgb * mask
            + livery.accent_rgb * second
        )
    return np.round(blended).astype(np.uint8)
