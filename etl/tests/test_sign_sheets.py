"""The index-plan sheet reader (`Q67`), and the decode its output rests on.

🔴 **This is the first test `sign_sheets.py` has ever had.** `test_signs.py`
owns the config block and never imports this module; what it reaches
transitively, through `pipeline/sign_text.py`, is `enclosed_white`, `flood` and
`ink_masks`. `_grid`, `_regular_run`, `_columns`, `read_sheets` and `load_sheet`
had no coverage anywhere, which is worth knowing about a module whose own
docstring says an off-by-one in it is `Q64` arriving through arithmetic.

What is covered here is narrow and deliberate: **how a page becomes pixels**.
`load_sheet` decoded through `.to_pil().convert("RGB")` until 2026-08-24, and
that round-trip normalised the bitmap's format for free. `.to_numpy()` on a
byteorder-reversed render is byte-identical and a quarter of the memory, but it
is *not* format-agnostic — so a property that used to be structural is now a
claim about a third-party renderer, and a version bump can withdraw it silently.
The grid recovery is still untested and this module does not pretend otherwise.
"""

from __future__ import annotations

import ctypes
import gc

import numpy as np
import pypdfium2 as pdfium
import pytest

from pipeline import fetch
from pipeline.config import load_config
from pipeline.sign_sheets import _RESIDENT, _index_plan, load_sheet, read_sheets

# ⚠️ **The artefact, not its directory.** `download()` makes the parent before it
# streams, so an interrupted fetch leaves the directory standing and the zip
# absent — and `cached_source` raises `FileNotFoundError` on that, which would
# *error* every test below where the point of the guard is to skip them.
_CITY = load_config()
try:
    _ARCHIVE = fetch.cached_source(_CITY, _CITY.signs.text_source)
except (FileNotFoundError, KeyError):
    _ARCHIVE = None

needs_dataspec = pytest.mark.skipif(
    _ARCHIVE is None, reason="requires a fetched traffic-aids dataspec"
)

# 🔴 **Deliberately NOT `DEFAULT_SCALE`, and the reason is this module's own
# subject.** Both decode paths held at once is four full-page buffers, so a
# 12.0 comparison over these sheets peaks at **1.7 GB** — 3.4x the stage this
# change exists to bring down to 514 MB, which would make the guard cost more
# than the thing guarded. At 2.0 the same five pages peak at **168 MB**.
#
# ⚠️ **What that costs is nothing this test claims.** Byte order and pixel format
# are chosen by the render flags, not by the size: the shipped scale is exercised
# end-to-end by `test_a_rendered_sheet_is_three_channel` below, which calls the
# real `load_sheet`. And the comparison stays *able* to fail — every one of the
# five sheets still carries thousands of pixels where R and B differ at this
# scale, so a channel-order regression cannot hide in a page that happens to be
# grey. It is the resolution that drops, not the coverage.
COMPARE_SCALE = 2.0


@pytest.fixture(autouse=True)
def _evict_resident_sheet():
    """Drop the cached page rather than leave 217 MB resident for the session.

    `load_sheet` keeps one sheet alive per `(source, scale)` for the life of the
    process, which is right for a build and wrong for a test run that goes on to
    do something else. Cheap because the tests below share the one entry.
    """
    yield
    _RESIDENT.clear()


@needs_dataspec
def test_the_two_decode_paths_are_byte_identical() -> None:
    """Full PAGE equality, which subsumes every code drawn on the sheet.

    🔴 **One face was the check that was not enough to take this change on**,
    and it is the weaker test as well as the smaller one: a cell is a crop, so
    agreeing on it says nothing about the rest of the page a later code will be
    read from. Comparing whole pages covers every cell at once, including the
    ones this region does not configure and a second region might.

    Both paths are run here rather than one being pinned to a stored digest,
    because what this defends against is the renderer moving under the pipeline
    — and a digest taken from that renderer would move with it.
    """
    codes = _configured_codes()
    members = {
        name
        for (first, last), name in read_sheets(_ARCHIVE).items()
        if any(first <= code <= last for code in codes)
    }
    assert members, "the region's faces resolve to no index-plan sheet"

    with _index_plan(_ARCHIVE) as inner:
        for member in sorted(members):
            page = pdfium.PdfDocument(inner.read(member))[0]
            through_pil = np.asarray(page.render(scale=COMPARE_SCALE).to_pil().convert("RGB"))
            direct = page.render(scale=COMPARE_SCALE, rev_byteorder=True).to_numpy()

            assert direct.shape == through_pil.shape, member
            assert direct.dtype == through_pil.dtype, member
            assert np.array_equal(direct, through_pil), member
            # ⚠️ Guards the guard: an all-grey page would satisfy the equality
            # above with the channels in any order at all.
            swappable = (through_pil[..., 0] != through_pil[..., 2]).any()
            assert swappable, f"{member} is grey enough to hide a channel swap"


@needs_dataspec
def test_a_rendered_sheet_is_three_channel() -> None:
    """`load_sheet`'s guard, on the shipped path and at the shipped scale.

    ⚠️ **The point is the channel count, not the shape** — `load_sheet` carries
    why, and this is the only test that reaches it at `DEFAULT_SCALE`.
    """
    sheet = load_sheet(_ARCHIVE, _configured_codes()[0])

    assert sheet.image.ndim == 3
    assert sheet.image.shape[2] == 3
    assert sheet.image.dtype == np.uint8


@needs_dataspec
def test_a_sheets_pixels_outlive_the_document_that_rendered_them() -> None:
    """🔴 **`Sheet.image` is a VIEW, and this is the invariant that makes it safe.**

    `load_sheet` lets the `PdfDocument` and its bitmap fall out of scope and
    caches the array for the life of the process. That is only sound because
    `.base` is a Python-side ctypes buffer holding the pixels, so refcounting
    keeps them. If a pypdfium2 release ever handed back a view onto memory
    pdfium owns, every measurement in the survey and every crop in the atlas
    would read freed pages — plausibly, and without a crash.

    ⚠️ **The `.base` assertion is the load-bearing one; the churn is not.** A
    dangling read only *reliably* misbehaves once something else has been given
    the pages, and a 64 MB allocation comes from a fresh `mmap` arena rather
    than from the freed buffer — so churn fails this probabilistically where the
    type check fails it every time. Kept small and second for that reason.

    ⚠️ **`before` must be non-zero or this is vacuous**: it is read from the very
    buffer under test, so a page already freed and zeroed would compare equal to
    itself and pass.
    """
    sheet = load_sheet(_ARCHIVE, _configured_codes()[0])

    assert not sheet.image.flags["OWNDATA"], "a copy would make this test pointless"
    owner = type(sheet.image.base)
    assert isinstance(sheet.image.base, ctypes.Array), f"pixels are owned by {owner}"

    before = int(sheet.image.sum(dtype=np.int64))
    assert before > 0, "an all-zero page would make the comparison below vacuous"

    gc.collect()
    churn = [bytearray(16 << 20) for _ in range(2)]
    del churn

    assert int(sheet.image.sum(dtype=np.int64)) == before


def _configured_codes() -> list[int]:
    """The region's face codes as integers, in the order `load_sheet` wants them.

    `removeprefix` rather than a slice to match `pipeline/sign_text.py` and
    `tools/sign_face_survey.py`, and numeric rather than string order because
    `TS1000` sorts before `TS999` as text — see `_RESIDENT`'s note on why that
    matters to a single-slot cache.
    """
    return sorted(int(code.removeprefix("TS")) for code in load_config().signs.faces)
