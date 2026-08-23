"""Measure every drawn sign face against the cell TD published it in (`Q67`).

The eighth hand-run tool, and it exists because `Q64` was found by a person
rendering a sheet and looking at it. That worked once. It found `TS182` drawn as
`TS183` — one row, 155 plates, invisible to every check in the bundle because a
mislabelled sign renders perfectly. Nothing then stopped the *next* eye-slip,
and there were four more waiting.

**What it grades is the face table's PROPORTIONS, which is a different question
from its labels.** `Q60` records that no TS sheet carries a dimension — every
one is stamped NOT TO SCALE and refers detail out to working drawings the
dataspec does not contain — so absolute plate sizes stay authored and are not
gradeable. A *ratio* survives a drawing with no scale, which is the loophole
`Q64` already used to measure `_SLASH_THICKNESS` at 0.097 against a drawn 0.130.
This tool is that measurement generalised to every face and every layer.

**How.** For each `TSnnn` in `signs.faces`, `pipeline.sign_sheets` renders the
publisher's own cell, and the config's face is rasterised at the same size from
`layer_polygons` — the pipeline's own geometry, not a copy of it. Both sides are
then reduced to the **area fraction of each livery colour inside the plate
outline**, which is one number per colour per face and is draw-word agnostic: a
ring drawn a third too thick, a bar drawn two thirds as long and an arrow drawn
17% small all move it, and none of them needs this tool to know what a ring, a
bar or an arrow is.

⚠️ **It GRADES rather than checks, and exits 0 whatever it finds.** There is no
bar and there deliberately is not one, for `carriageway_margin.py`'s reason: the
truth side is a drawing whose corner radii, keylines and hairline offsets this
pipeline does not model and should not. A face that differs by a couple of
points of area is a face drawn in this game's flat-shaded idiom. A face that
differs by ten is a face drawn wrong, and telling those apart is a person's job.

⚠️ **The truth side shares no code with what it grades** — `kerbside_error.py`'s
property, and unlike `kerbside_source_audit.py` it is not even the same *kind* of
artefact: one side is a published drawing, the other is a polygon list. What it
therefore cannot see is a face on the wrong **code**, because it looks the config
up by code and fetches that code's cell. `Q64`'s own defect would still be
invisible here. What covers that is the contact sheet `--contact` writes, which
is the same rendering-and-looking that found it.

⚠️ **It needs `traffic_aids_data_dictionary`**, which is 8.5 MB and which the
build already fetches for the layer spec — unlike `kerbside_source_audit.py`'s
218 MB, this costs nothing to run.

Run:  .venv/bin/python tools/sign_face_survey.py
      .venv/bin/python tools/sign_face_survey.py --contact out.png
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.config import (  # noqa: E402
    SIGN_BACK_COLOUR,
    SIGN_TEXT,
    CityConfig,
    SignFace,
    load_city,
)
from pipeline.fetch import cached_source  # noqa: E402
from pipeline.sign_sheets import ink_masks, load_sheet  # noqa: E402
from pipeline.signs import layer_polygons, plate_extent_m  # noqa: E402

log = logging.getLogger(__name__)

# The dataspec archive the index-plan sheets live in.
SHEET_SOURCE = "traffic_aids_data_dictionary"

# Side of the square the config's face is rasterised into. Large enough that a
# one-pixel edge is well under a tenth of a point of area on any face here.
RASTER_PX = 512

# Flagged in the area table at this much absolute difference. Not a bar — the
# tool exits 0 either way — just where "go and look" starts being worth saying.
_NOTE = 0.04
# A colour with less than this share on both sides has no extent worth printing.
_MINOR = 0.02


def _note(lettered: bool, worst: float) -> str:
    """The area table's right-hand column: why a row is worth a second look.

    ⚠️ **A lettered face is annotated rather than flagged.** Its glyph is baked
    from the sheet and is not drawn from `layer_polygons` at all, so the area it
    is short by is the lettering the rasteriser cannot see — a finding about the
    tool's reach, not about the face (`Q68`).
    """
    if lettered:
        return "+text"
    return f"<-- {worst:.3f}" if worst >= _NOTE else ""


# The sheet's ink test lives in `pipeline/sign_sheets.py` beside the reader that
# produces the cell, because `pipeline/sign_text.py` crops against the same
# thresholds and the two must not drift apart. Its comment there records why the
# sheet is classified by hue family and not against `signs.colours`.


@dataclass(frozen=True)
class Shares:
    """Area of each livery colour as a fraction of the plate's own outline."""

    by_colour: dict[str, float]

    def get(self, name: str) -> float:
        return self.by_colour.get(name, 0.0)


def _interior(white: np.ndarray) -> np.ndarray:
    """`white` minus the part of it connected to the border of the image.

    The plate outline is what everything here is a fraction of, and on a disc or
    a triangle the cell's corners are white too. Flood the white in from the
    border and whatever is left is the plate's own white field.
    """
    reached = np.zeros_like(white)
    reached[0, :] |= white[0, :]
    reached[-1, :] |= white[-1, :]
    reached[:, 0] |= white[:, 0]
    reached[:, -1] |= white[:, -1]
    while True:
        grown = reached.copy()
        grown[1:, :] |= reached[:-1, :]
        grown[:-1, :] |= reached[1:, :]
        grown[:, 1:] |= reached[:, :-1]
        grown[:, :-1] |= reached[:, 1:]
        grown &= white
        if int(grown.sum()) == int(reached.sum()):
            return white & ~reached
        reached = grown


def measured(cell: np.ndarray, names: list[str]) -> tuple[Shares, dict[str, tuple[float, float]]]:
    """Colour shares and extents of the publisher's cell, against its plate."""
    masks = ink_masks(cell, names)
    inked = np.zeros(cell.shape[:2], dtype=bool)
    for mask in masks.values():
        inked |= mask
    # ⚠️ The plate is every inked pixel plus the white it *encloses* — so the
    # field of a NO ENTRY counts and the paper around the disc does not.
    field = _interior(~inked)
    if "white" in names:
        masks["white"] = field
    plate = inked | field
    return _shares(masks, plate, names)


def _shares(
    masks: dict[str, np.ndarray], plate: np.ndarray, names: list[str]
) -> tuple[Shares, dict[str, tuple[float, float]]]:
    """Area fraction and bounding-box extents of each colour within `plate`.

    ⚠️ **Both, because area alone cannot see a shape.** The NO ENTRY bar is
    0.868 of the diameter long and 0.187 thick on the sheet where this pipeline
    draws 0.66 by 0.22 — a visibly different bar, and the same area to within a
    point. Extents are what separate "drawn in this game's idiom" from "drawn
    wrong", and the tool would have passed `Q67`'s headline defect without them.
    """
    area = float(plate.sum())
    if area <= 0.0:
        return Shares({}), {}
    ys, xs = np.nonzero(plate)
    width = float(xs.max() - xs.min() + 1)
    height = float(ys.max() - ys.min() + 1)

    shares: dict[str, float] = {}
    extents: dict[str, tuple[float, float]] = {}
    for name in names:
        mask = masks.get(name)
        if mask is None:
            shares[name] = 0.0
            extents[name] = (0.0, 0.0)
            continue
        mask = mask & plate
        shares[name] = float(mask.sum()) / area
        if not mask.any():
            extents[name] = (0.0, 0.0)
            continue
        my, mx = np.nonzero(mask)
        extents[name] = (
            float(mx.max() - mx.min() + 1) / width,
            float(my.max() - my.min() + 1) / height,
        )
    return Shares(shares), extents


def drawn(
    city: CityConfig, face: SignFace, names: list[str]
) -> tuple[Shares, dict[str, tuple[float, float]]]:
    """Colour shares and extents of the face this pipeline actually draws.

    Rasterised from `layer_polygons` rather than re-derived, so the tool grades
    the shipped geometry and not a second opinion about it — the property
    `kerbside_error.py` has and `narrowing.py` deliberately does not.
    """
    from PIL import Image, ImageDraw

    spec = city.signs
    assert spec is not None
    half_w, half_h = plate_extent_m(spec, face.plate)
    scale = 0.5 * (RASTER_PX - 2) / max(half_w, half_h)
    index_of = {name: number + 1 for number, name in enumerate(names)}

    canvas = Image.new("P", (RASTER_PX, RASTER_PX), 0)
    pen = ImageDraw.Draw(canvas)

    def paint(polygons: list[np.ndarray], value: int) -> None:
        for polygon in polygons:
            pen.polygon(
                [(RASTER_PX / 2 + x * scale, RASTER_PX / 2 - y * scale) for x, y in polygon[:, :2]],
                fill=value,
            )

    # ⚠️ **The plate outline first, as the denominator, painted in the plate's
    # own field colour** — a face whose first layer redraws the outline covers
    # it, and one that does not (there is none today) would otherwise grade its
    # uncovered plate as a colour it never names. 255 is that no-name value.
    paint(layer_polygons(spec, face.plate, 1.0, half_w, half_h), 255)
    for layer in face.layers:
        if layer.draw == SIGN_TEXT:
            # ⚠️ **The lettering is not a polygon and this tool does not grade
            # it.** It is a textured quad, so it has no shape here to rasterise
            # — the row will read short by exactly the ink the words cover, and
            # `report` marks it `+text` so that reads as a known gap rather than
            # as a finding. What DOES grade the lettering is `text_coverage` in
            # `signs.json`: a cell cropped off the words bakes paper, and near
            # zero there is that failure announcing itself.
            continue
        paint(
            layer_polygons(spec, layer.draw, layer.size, half_w, half_h),
            index_of.get(layer.colour, 255),
        )

    raster = np.asarray(canvas)
    masks = {name: raster == index_of[name] for name in names}
    return _shares(masks, raster > 0, names)


def report(city: CityConfig, *, root: Path | None = None, contact: Path | None = None) -> int:
    spec = city.signs
    if spec is None:
        log.info("city '%s' declares no signs block; nothing to survey", city.id)
        return 0

    archive = cached_source(city, SHEET_SOURCE, root=root)
    # The livery minus the colour that is only ever on the back of a plate: a
    # sign's reverse is galvanised steel and the publisher never draws it.
    names = [name for name in spec.colours if name != SIGN_BACK_COLOUR]

    Extents = dict[str, tuple[float, float]]
    cells: list[tuple[str, np.ndarray]] = []
    rows: list[tuple[str, Shares, Shares, Extents, Extents]] = []
    for code in sorted(spec.faces):
        number = int(code.removeprefix("TS"))
        try:
            sheet = load_sheet(archive, number)
        except (KeyError, ValueError) as problem:
            log.info("%-7s could not be indexed: %s", code, problem)
            continue
        cell = sheet.cell(number)
        cells.append((code, cell))
        sheet_shares, sheet_extents = measured(cell, names)
        our_shares, our_extents = drawn(city, spec.faces[code], names)
        rows.append((code, sheet_shares, our_shares, sheet_extents, our_extents))

    log.info("AREA — share of the plate, sheet / drawn")
    log.info("code    %s", "  ".join(f"{name:>13}" for name in names))
    log.info("%s", "-" * (8 + 15 * len(names)))
    for code, found, ours, _, _ in rows:
        cells_text = "  ".join(f"{found.get(n):>6.3f}/{ours.get(n):<6.3f}" for n in names)
        worst = max(abs(found.get(n) - ours.get(n)) for n in names)
        log.info("%-7s %s  %s", code, cells_text, _note(spec.faces[code].lettered, worst))

    log.info("")
    log.info("EXTENT — bounding box of each colour, w x h of the plate, sheet / drawn")
    log.info("code    %s", "  ".join(f"{name:>27}" for name in names))
    log.info("%s", "-" * (8 + 29 * len(names)))
    for code, found, ours, sheet_extents, our_extents in rows:
        parts = []
        for name in names:
            if max(found.get(name), ours.get(name)) < _MINOR:
                parts.append(f"{'-':>27}")
                continue
            sw, sh = sheet_extents.get(name, (0.0, 0.0))
            ow, oh = our_extents.get(name, (0.0, 0.0))
            parts.append(f"{sw:.2f}x{sh:.2f} / {ow:.2f}x{oh:.2f}".rjust(27))
        log.info("%-7s %s", code, "  ".join(parts))

    if contact is not None:
        _contact_sheet(cells, contact)
        log.info("")
        log.info("contact sheet: %s", contact)
    return 0


def _contact_sheet(cells: list[tuple[str, np.ndarray]], path: Path) -> None:
    """Every graded cell on one page, because the label is what a person checks.

    🔴 **This is the half the numbers cannot do.** The table above looks a face
    up by its code, so a face drawn under the *wrong* code agrees with itself
    perfectly — which is `Q64`'s defect exactly. Only looking catches that.
    """
    from PIL import Image, ImageDraw

    if not cells:
        return
    width = max(cell.shape[1] for _, cell in cells)
    height = max(cell.shape[0] for _, cell in cells)
    columns = 7
    rows = (len(cells) + columns - 1) // columns
    label = 40
    page = Image.new("RGB", (columns * width, rows * (height + label)), "white")
    pen = ImageDraw.Draw(page)
    for index, (code, cell) in enumerate(cells):
        x = (index % columns) * width
        y = (index // columns) * (height + label)
        page.paste(Image.fromarray(cell), (x, y + label))
        pen.text((x + 8, y + 14), code, fill="black")
    page.resize((page.width // 3, page.height // 3), Image.LANCZOS).save(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--city", default="hong_kong", help="city id under etl/config/cities")
    parser.add_argument("--sources-root", type=Path, help="override etl/sources")
    parser.add_argument("--contact", type=Path, help="write a contact sheet of every graded cell")
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return report(load_city(arguments.city), root=arguments.sources_root, contact=arguments.contact)


if __name__ == "__main__":
    raise SystemExit(main())
