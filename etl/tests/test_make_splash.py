"""The `Q209` boot splash generator (`tools/make_splash.py`).

**The committed-asset guard.** `boot_splash.png` is build output that is
committed, and `tools/check.sh` does not know this tool exists. Regenerating and
comparing pixels is what catches "edited the drawing, forgot to re-run" — and
the cover reads the same `taxi.json` live, so a stale splash is a jump at the
hand-over.

**The field.** The splash's background is the cover's: the corners of the
square, which the letterbox continues, are `HudStyle.plate_field` exactly.
"""

from __future__ import annotations

from pathlib import Path

from make_splash import (
    DEFAULT_OUT,
    SIDE_PX,
    hex_colour,
    loading_line,
    plate_field,
    rounded_rect,
    write_splash,
)
from PIL import Image, ImageChops


def test_the_committed_splash_matches_the_generator(tmp_path: Path) -> None:
    fresh = write_splash(tmp_path / DEFAULT_OUT.name)
    assert DEFAULT_OUT.exists(), f"{DEFAULT_OUT.name} is not committed"
    # Pixels, not bytes: the PNG's deflate stream may differ by zlib build while
    # the picture, which is what the cover has to match, does not.
    shipped = Image.open(DEFAULT_OUT).convert("RGB")
    drawn = Image.open(fresh).convert("RGB")
    assert shipped.size == drawn.size
    assert ImageChops.difference(shipped, drawn).getbbox() is None, (
        f"{DEFAULT_OUT.name} is stale — re-run tools/make_splash.py"
    )


def test_the_square_stands_on_the_covers_field() -> None:
    image = Image.open(DEFAULT_OUT).convert("RGB")
    assert image.size == (SIDE_PX, SIDE_PX)
    field = plate_field()
    last = SIDE_PX - 1
    for corner in ((0, 0), (last, 0), (0, last), (last, last)):
        assert image.getpixel(corner) == field


def test_the_line_says_both_languages() -> None:
    assert loading_line() == "載入中… · Loading…"


def test_a_rounded_rect_keeps_inside_its_box() -> None:
    points = rounded_rect(-52, -14, 52, 12, 10)
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    assert min(xs) >= -52 - 1e-9 and max(xs) <= 52 + 1e-9
    assert min(ys) >= -14 - 1e-9 and max(ys) <= 12 + 1e-9


def test_hex_colours_read_as_srgb_bytes() -> None:
    assert hex_colour("ce162c") == (206, 22, 44)
