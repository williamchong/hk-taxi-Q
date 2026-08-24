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
must **bracket** the filename's own span — at least it, and less than one block
over — and a sheet whose detected grid does not is refused rather than indexed.
⚠️ It is a bracket rather than an equality because every sheet here is ruled to
the same 5 x 21 and the short ones run out of codes partway down the last block;
the slack is held under one block so that a wholly empty block still fails. That
check is what refuses the three 6-block sheets, and it is the reason a caller may
trust a returned cell at all.
"""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Callable, Iterable
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


# 🔴 **THE SHEET'S INK IS NOT THE GAME'S LIVERY.** `signs.colours` is a muted,
# art-directed palette — `#c21a26` red, `#0d4794` blue — and TD prints saturated
# process primaries. A nearest-livery assignment puts every blue disc on the
# sheet more than 110 units from the game's blue, so the whole plate classifies
# as *white*; that was the first version of `sign_face_survey.py` and it read as
# a catastrophe against a pipeline that was correct.
#
# So the sheet is classified by **hue family**, which is the only thing the two
# palettes share: whether a pixel is the red one, the blue one, the dark one or
# the paper. The livery is deliberately not these numbers, and that difference is
# a decision (hard rule 3) rather than an error to measure.
#
# ⚠️ **Here rather than in either caller, because both are on the TRUTH side.**
# `sign_face_survey.py` measures a cell's proportions and `sign_text.py` crops
# the lettering out of one; they must agree on where the plate stops or the atlas
# bakes a crop of a box the survey never graded. That is not the
# grader-independence rule — that rule keeps the survey off the *drawn* side,
# which neither of these touches.
INK: dict[str, Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]] = {
    "red": lambda r, g, b: (r > 140) & (g < 110) & (b < 110),
    "blue": lambda r, g, b: (b > 110) & (r < 110),
    "black": lambda r, g, b: (r < 90) & (g < 90) & (b < 90),
    "yellow": lambda r, g, b: (r > 170) & (g > 130) & (b < 110),
}


def ink_masks(cell: np.ndarray, names: Iterable[str]) -> dict[str, np.ndarray]:
    """`INK` applied to a cell, one boolean mask per requested hue family."""
    channels = [cell[..., index].astype(int) for index in range(3)]
    return {name: INK[name](*channels) for name in names if name in INK}


def flood(seed: np.ndarray, allow: np.ndarray) -> np.ndarray:
    """`seed` grown four-connected as far as `allow` lets it.

    Iterated dilation rather than a labelling pass, because `scipy` is not a
    dependency of this pipeline and buying one for a connected component would
    be the largest claim in the module. The loop runs once per pixel of the
    longest path through `allow`, which is the *cell's* width rather than the
    plate's — 233 passes on `TS101` — so it is tens of milliseconds.

    ⚠️ **The seed is clipped to `allow` first**, so a caller may seed with
    something that overlaps it only partly, or not at all.

    ⚠️ **`.any()` on the difference, not two `.sum()`s.** `grown` contains
    `reached` by construction, so equal popcount and equal sets are the same
    statement — but the sums are two full reductions per pass and were **55% of
    this loop**, where the xor short-circuits in C on the first differing byte.
    Measured over `TS101`'s 233 passes: 27.3 ms to 13.6 ms, same 129,976 px.
    """
    reached = seed & allow
    while True:
        grown = reached.copy()
        grown[1:, :] |= reached[:-1, :]
        grown[:-1, :] |= reached[1:, :]
        grown[:, 1:] |= reached[:, :-1]
        grown[:, :-1] |= reached[:, 1:]
        grown &= allow
        if not (grown ^ reached).any():
            return reached
        reached = grown


def enclosed_white(inked: np.ndarray) -> np.ndarray:
    """The un-inked pixels a cell's ink *encloses* — the plate's own white field.

    Flood the white in from the cell's border and whatever is left is inside
    something: the field of a NO ENTRY, the paper showing through a knocked-out
    glyph. The paper *around* a disc or a triangle is reached and excluded.

    ⚠️ **Here for `ink_masks`'s reason, restated.** Both callers of this module
    are on the TRUTH side and ought to agree on where a plate stops — the survey
    measures a cell's proportions against it and the atlas crops lettering out
    of it. This began as `_interior` in `tools/sign_face_survey.py` and was
    hoisted the first time `pipeline/sign_text.py` needed it.

    🔴 **They do NOT agree today, and this function is only half of why.** What
    the atlas does with the result — take the ink *connected to* this field, and
    so drop TD's dimension lines — the survey does not. See
    `sign_text._plate_mask`, which records the 10-of-21 gap and what closing it
    would move.
    """
    white = ~inked
    border = np.zeros_like(white)
    border[0, :] |= white[0, :]
    border[-1, :] |= white[-1, :]
    border[:, 0] |= white[:, 0]
    border[:, -1] |= white[:, -1]
    return white & ~flood(border, white)


# 🔴 **Rendering a sheet is the expensive act in this module** — one page is
# 10,104 x 7,143 px, ~0.7 s and 216 MB — and the 21 faces the region configures
# live on four sheets. Without this, `sign_face_survey.py` re-rendered a page
# per *face*: 14.8 s and 5.5 GB peak, against 3.8 s and 1.8 GB with it, for
# byte-identical output. Keyed by scale as well as source, because a cell
# measured at one scale is not the cell measured at another.
_RESIDENT: dict[tuple[Path, float], Sheet] = {}


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
        # ⚠️ **A copy, not a view.** Basic slicing would keep this cell's whole
        # parent sheet — 216 MB at `DEFAULT_SCALE` — alive for as long as the
        # caller holds the crop, and `sign_face_survey.py` holds one per face to
        # build its contact sheet. Copying costs well under a megabyte.
        return np.ascontiguousarray(
            self.image[int(y0) + trim_px : int(y1) - trim_px, int(x0) + trim_px : int(x1) - trim_px]
        )


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


def _scan(inner: zipfile.ZipFile) -> dict[tuple[int, int], str]:
    """Every `(first, last)` TS range named by a member of an open Index Plan."""
    found: dict[tuple[int, int], str] = {}
    for name in inner.namelist():
        match = _SHEET_NAME.search(name)
        if match is not None:
            found[(int(match.group(1)), int(match.group(2)))] = name
    return found


def read_sheets(dataspec_zip: Path) -> dict[tuple[int, int], str]:
    """Every `(first, last)` TS range the dataspec's Index Plan publishes.

    Read from the **filenames**, which is the only place the range is stated
    outside the drawing's own title block — and the title block has no text
    layer either.
    """
    with _index_plan(dataspec_zip) as inner:
        return _scan(inner)


def load_sheet(dataspec_zip: Path, code: int, *, scale: float = DEFAULT_SCALE) -> Sheet:
    """Render and index the sheet holding `code`.

    ⚠️ **`pypdfium2` is imported here rather than at module scope** so that
    importing this module — which `pipeline/signs.py` does, for the atlas — does
    not put a PDF renderer on the path of every build that draws no lettering.
    """
    cached = _RESIDENT.get((dataspec_zip, scale))
    if cached is not None and cached.holds(code):
        return cached

    import pypdfium2 as pdfium

    with _index_plan(dataspec_zip) as inner:
        matches = [
            (span, name) for span, name in _scan(inner).items() if span[0] <= code <= span[1]
        ]
        if len(matches) != 1:
            raise KeyError(f"TS{code} is on {len(matches)} index-plan sheets, expected exactly 1")
        (first, last), member = matches[0]
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
    sheet = Sheet(
        name=member,
        first_code=first,
        last_code=last,
        image=image,
        rows=tuple(rows),
        columns=tuple(columns),
    )
    # One resident sheet per source, replaced rather than accumulated: both
    # callers walk `sorted(codes)`, so consecutive codes land on the same sheet
    # and a plain overwrite is the whole of the eviction policy. Holding two
    # would double the resident 216 MB to buy nothing.
    _RESIDENT[(dataspec_zip, scale)] = sheet
    return sheet


def _grid(image: np.ndarray) -> tuple[list[float], list[tuple[float, float]]]:
    """Horizontal row rules and per-block symbol-column bounds, in pixels.

    ⚠️ **Two passes, and the order matters.** A rule's span is only meaningful
    against the *table*, and where the table is is what the first pass finds:
    the notes column on the right is a third of the sheet and carries long rules
    of its own, so a threshold taken against the page width admits them and one
    taken against the cut admits nothing. Verticals first, against the page;
    then the table's own bounds; then horizontals against those.
    """
    # ⚠️ **Not `image.max(axis=2) < 90`.** numpy reduces badly along a length-3
    # contiguous axis, and on a 7,143 x 10,104 page that one call was **442 ms
    # of an 810 ms** sheet load — the rendering is not the expensive act in this
    # module, this was. Pairwise `maximum` on the three channel views is
    # byte-identical and **11.5x** faster (38 ms).
    channels = [image[..., index] for index in range(3)]
    dark = np.maximum(np.maximum(channels[0], channels[1]), channels[2]) < 90
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
