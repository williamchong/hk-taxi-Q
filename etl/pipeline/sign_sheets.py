"""TD's TS index-plan sheets, as addressable cells (`P3-20`, `Q67`).

The face table in `hong_kong.yaml` is transcribed off these sheets by eye, and
`Q59` sets the rule that makes that legitimate: the publisher's drawing is
authority and the histogram is not. `Q64` is what it costs when the eye slips —
one row, `TS182` drawn as `TS183`, invisible to every check in the bundle.

This module is the eye's instrument. It resolves a `TSnnn` code to the cell TD
drew it in, and hands back that cell as pixels. Two very different callers need
exactly that:

- `tools/sign_face_survey.py` measures the cell and diffs it against the face
  the config draws, which is the only thing that can see a proportion drift.
- `pipeline/sign_text.py` crops the lettering out of one and bakes it into the
  glyph atlas, because `TS102`'s 讓 is a shape no polygon list is going to say.

⚠️ **The sheets are VECTOR, not scanned.** `pdfinfo` reads `CT174_51_11.dgn` /
PScript5.dll / Distiller and `pdffonts` returns no embedded font: a MicroStation
DGN export whose ruling lines, digits and pictograms are all *paths*. That is
what makes the grid recoverable exactly rather than detected in pixels — the
rules are drawn at one width, full span, and nothing else on the sheet is.
"No text layer" is why the numbers cannot be read; "scanned" would have been why
the wrong extraction method looked necessary, and it is not the case.

🔴 **THE ROW IS COUNTED, NOT READ, AND THAT IS THE RISK THIS MODULE CARRIES.**
There is no text layer, so nothing on the sheet says "this cell is 102". What
says it is the filename's range — `(TS 101 - 205).pdf` — plus the position in a
grid whose rows are contiguous and whose superseded entries keep their slot as a
greyed row. So an off-by-one here is `Q64` all over again, arriving through
arithmetic instead of through a mis-transcription.

✅ **Which is why the grid is asserted rather than assumed.** `blocks x rows`
must equal the filename's own span exactly, and a sheet whose detected grid does
not multiply out is refused rather than indexed. That check is what caught the
`(TS 506 - 600)` sheet having a different row count from its siblings, and it is
the reason a caller may trust a returned cell at all.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# The dataspec zip's own layout. Two levels: the fetched archive holds an
# `Index Plan.zip`, which holds one PDF per sheet.
DATASPEC_INDEX_PLAN = "tadrawings_dataspec/Index Plan.zip"
_SHEET_NAME = re.compile(r"\(TS\s*(\d+)\s*-\s*(\d+)\)\.pdf$", re.IGNORECASE)

# Rendering scale, in PDF points to pixels. 12 puts a 600 mm plate's cell at
# about 300 px across, which is where the ring-thickness measurements stop
# moving — `Q67` swept it and records the numbers.
DEFAULT_SCALE = 12.0

# A rule is a run of dark pixels spanning most of the table. 0.55 is comfortably
# above the longest thing that is *not* a rule (a `KEEP LEFT` legend box at
# roughly a third) and below the shortest thing that is.
_RULE_SPAN = 0.55
# The notes/legend column on the right of every sheet, which is not the table
# and carries long horizontal rules of its own.
_TABLE_FRACTION = 0.76
# Two rules within this many pixels are one rule drawn twice — the block gutters
# are two lines a hair apart.
_RULE_MERGE_PX = 3
# Trimmed off each cell before anything is measured, so the cell's own black
# ruling lines are not mistaken for ink. A rule is ~4 px at `DEFAULT_SCALE`.
_BORDER_TRIM_PX = 14


@dataclass(frozen=True)
class Sheet:
    """One index-plan sheet, rendered, with its grid recovered.

    `rows` and `columns` are pixel coordinates of the detected rules. `columns`
    holds one `(x0, x1)` per column block, bounding that block's **symbol**
    cell — the middle of its three columns, and the only one with a drawing in.
    """

    name: str
    first_code: int
    last_code: int
    image: np.ndarray  # (h, w, 3) uint8
    rows: tuple[float, ...]
    columns: tuple[tuple[float, float], ...]

    @property
    def rows_per_block(self) -> int:
        return len(self.rows) - 1

    def holds(self, code: int) -> bool:
        return self.first_code <= code <= self.last_code

    def cell(self, code: int, *, trim_px: int = _BORDER_TRIM_PX) -> np.ndarray:
        """The symbol cell for `code`, trimmed clear of its own ruling lines.

        ⚠️ **Trimmed, and the trim is not cosmetic.** The cell border is black,
        and every measurement worth taking off one of these is "where does the
        ink stop" — so an untrimmed cell measures as a black rectangle and every
        proportion comes out 1.000. That is what the first pass of `Q67` read.
        """
        if not self.holds(code):
            raise KeyError(
                f"{self.name} holds TS{self.first_code}-TS{self.last_code}, not TS{code}"
            )
        index = code - self.first_code
        block, row = divmod(index, self.rows_per_block)
        x0, x1 = self.columns[block]
        y0, y1 = self.rows[row], self.rows[row + 1]
        return self.image[
            int(y0) + trim_px : int(y1) - trim_px, int(x0) + trim_px : int(x1) - trim_px
        ]


def _index_plan(dataspec_zip: Path) -> zipfile.ZipFile:
    """The Index Plan archive, which lives *inside* the fetched dataspec zip.

    ⚠️ **Two levels of archive, and the inner one is read whole into memory.**
    `zipfile` needs a seekable file and the handle a `ZipFile` hands out is not
    one, so the 8.5 MB has to be materialised. It is the smaller of the two
    archives this layer touches by a factor of 25 — see the `signs:` block's
    `text_source` for why the sheets are not in the same file as the signs.
    """
    with zipfile.ZipFile(dataspec_zip) as outer, outer.open(DATASPEC_INDEX_PLAN) as handle:
        return zipfile.ZipFile(io.BytesIO(handle.read()))


def read_sheets(dataspec_zip: Path) -> dict[tuple[int, int], str]:
    """Every `(first, last)` TS range the dataspec's Index Plan publishes.

    Read from the **filenames**, which is the only place the range is stated
    outside the drawing's own title block — and the title block has no text
    layer either.
    """
    with _index_plan(dataspec_zip) as inner:
        found: dict[tuple[int, int], str] = {}
        for name in inner.namelist():
            match = _SHEET_NAME.search(name)
            if match is not None:
                found[(int(match.group(1)), int(match.group(2)))] = name
        return found


def load_sheet(dataspec_zip: Path, code: int, *, scale: float = DEFAULT_SCALE) -> Sheet:
    """Render and index the sheet holding `code`.

    ⚠️ **`pypdfium2` is imported here rather than at module scope** so that
    importing this module — which `pipeline/signs.py` does, for the atlas — does
    not put a PDF renderer on the path of every build that draws no lettering.
    """
    import pypdfium2 as pdfium

    sheets = read_sheets(dataspec_zip)
    match = [(span, name) for span, name in sheets.items() if span[0] <= code <= span[1]]
    if len(match) != 1:
        raise KeyError(f"TS{code} is on {len(match)} index-plan sheets, expected exactly 1")
    (first, last), member = match[0]

    with _index_plan(dataspec_zip) as inner:
        pdf = inner.read(member)

    document = pdfium.PdfDocument(pdf)
    if len(document) != 1:
        raise ValueError(f"{member}: {len(document)} pages, expected 1")
    image = np.asarray(document[0].render(scale=scale).to_pil().convert("RGB"))

    rows, columns = _grid(image)
    expected = last - first + 1
    per_block = len(rows) - 1
    cells = len(columns) * per_block
    # 🔴 The assertion the whole module rests on, and it is two-sided on purpose.
    # A grid too SMALL for the filename's span means the row a code is read from
    # is not the row TD drew it in, and every cell past the first mismatch is a
    # different sign — silently, rendering perfectly, which is `Q64`.
    # ⚠️ A grid **larger** than the span is normal and is not slack: every sheet
    # here is ruled to the same 5 x 21, and the short ones simply run out of
    # codes partway down the last block. What would not be normal is a whole
    # empty block, which says the fill order is not the column-major one this
    # indexing assumes — so the slack is held under one block.
    if not expected <= cells < expected + per_block:
        raise ValueError(
            f"{member}: detected {len(columns)} blocks x {per_block} rows = {cells} cells "
            f"against a filename span of TS{first}-TS{last} = {expected}. Refusing to index it."
        )
    return Sheet(
        name=member,
        first_code=first,
        last_code=last,
        image=image,
        rows=tuple(rows),
        columns=tuple(columns),
    )


def _grid(image: np.ndarray) -> tuple[list[float], list[tuple[float, float]]]:
    """Horizontal row rules and per-block symbol-column bounds, in pixels.

    ⚠️ **Two passes, and the order matters.** A rule's span is only meaningful
    against the *table*, and where the table is is what the first pass finds:
    the notes column on the right is a third of the sheet and carries long rules
    of its own, so a threshold taken against the page width admits them and one
    taken against the cut admits nothing. Verticals first, against the page;
    then the table's own bounds; then horizontals against those.
    """
    dark = image.max(axis=2) < 90
    height, width = dark.shape
    page = dark[:, : int(width * _TABLE_FRACTION)]

    vertical = _rules(page.sum(axis=0), height)
    if len(vertical) < 4:
        raise ValueError("no column rules found on this sheet")
    left, right = vertical[0], vertical[-1]

    band = dark[:, int(left) : int(right) + 1]
    horizontal = _rules(band.sum(axis=1), band.shape[1])
    if len(horizontal) < 3:
        raise ValueError("no row rules found on this sheet")

    # 🔴 **The header strip is a row of the grid and is not a row of the table.**
    # It is shorter than a data row, so it falls out as the one gap that breaks
    # the pitch — and left in, every code reads one row high, which is `Q64`
    # exactly. The data rows are the longest run at a constant pitch.
    rows = _regular_run(horizontal)
    columns = _columns(vertical, right)
    return rows, columns


def _rules(counts: np.ndarray, span: int) -> list[float]:
    """Centres of the runs where `counts` says a rule spans most of `span`."""
    hits = np.nonzero(counts > span * _RULE_SPAN)[0]
    grouped: list[list[int]] = []
    for index in hits:
        if grouped and index - grouped[-1][-1] <= _RULE_MERGE_PX:
            grouped[-1].append(int(index))
        else:
            grouped.append([int(index)])
    return [(run[0] + run[-1]) / 2.0 for run in grouped]


def _regular_run(values: list[float]) -> list[float]:
    """The table's row rules, as the lattice they are drawn on.

    🔴 **Solved for, not chained.** The obvious reading — walk the rules keeping
    every one that is a pitch on from the last — breaks on both of the things
    these sheets really do. A merged cell spanning two rows drops a rule, which
    ends the chain halfway down; and a chain that starts on the wrong pair
    locks onto **double** the pitch and reads every second row, which is `Q64`'s
    failure exactly: a cell that is confidently the wrong sign.

    So the bottom rule is taken as the table's foot, each of the first few rules
    is tried as its head, and the row count is the largest that puts a detected
    rule at every lattice point. The header strip is a different height from a
    data row, which is what makes it fail the fit rather than having to be
    recognised.
    """
    if len(values) < 3:
        raise ValueError("too few row rules to fit a lattice")
    bottom = values[-1]
    best: list[float] = []
    for top in values[:4]:
        span = bottom - top
        if span <= 0:
            continue
        for count in range(len(values) + 2, 1, -1):
            pitch = span / count
            lattice = [top + pitch * step for step in range(count + 1)]
            if all(min(abs(rule - y) for rule in values) < pitch * 0.06 for y in lattice):
                if len(lattice) > len(best):
                    best = lattice
                break
    if len(best) < 2:
        raise ValueError("the sheet's row rules are not on a regular pitch")
    return best


def _columns(vertical: list[float], right: float) -> list[tuple[float, float]]:
    """Each column block's symbol-cell bounds.

    🔴 **Recovered from the sheet's own regularity, never four rules at a time.**
    Three things defeat the obvious chunking, and all three are real on these
    sheets: the gutter between two blocks is *two* rules a hair apart, the grey
    "superseded or deleted" fills add spurious full-height columns, and one
    sheet drops a rule where a block ends on a blank cell. So the block pitch is
    solved for first, and the two interior rules are taken as the **median
    offset across every block that has exactly two** — the blocks are drawn
    identically, which is a fact about the sheet rather than an assumption about
    it, and it makes one bad block unable to move any other.
    """
    rules = np.asarray(vertical, dtype=float)
    left = rules[0]
    span = right - left

    blocks = 0
    for count in range(6, 2, -1):
        pitch = span / count
        edges = left + pitch * np.arange(count + 1)
        if all(np.min(np.abs(rules - edge)) < pitch * 0.03 for edge in edges):
            blocks = count
            break
    if blocks == 0:
        raise ValueError("the sheet's column blocks are not on a regular pitch")

    pitch = span / blocks
    offsets: list[list[float]] = []
    for index in range(blocks):
        start = left + index * pitch
        inner = [
            (rule - start) / pitch
            for rule in rules
            if start + pitch * 0.05 < rule < start + pitch * 0.95
        ]
        if len(inner) == 2:
            offsets.append(inner)
    if not offsets:
        raise ValueError("no column block has the expected two interior rules")

    first = float(np.median([pair[0] for pair in offsets]))
    second = float(np.median([pair[1] for pair in offsets]))
    return [
        (left + index * pitch + first * pitch, left + index * pitch + second * pitch)
        for index in range(blocks)
    ]
