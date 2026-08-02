"""The decal sheet for `P3-11`'s vehicles — plates, badges and lettering.

Everything here is a *flat image on a quad*, not geometry. The things it draws
are text and markings, and no triangle count reaches them: 「TAXI / 4 / SEATS」
on a green dome, and a registration plate, are the two features a Hong Kong
driver identifies the car by, and both are pixels.

**No Pillow, and no alpha.** A PNG is `zlib` plus four chunks, which is less
code than justifying a dependency `Q18` deliberately deferred. Alpha is avoided
by baking each decal's surroundings into its own patch — the badge sits on the
bumper, so the bumper's colour fills the corners around the dome. That keeps
`write_glb`'s material at the default OPAQUE mode, where an alpha channel would
need a blend mode the writer does not set.

Plate colours are the Hong Kong standard, which follows the UK: **white at the
front, yellow at the rear**, black characters on both. Getting that backwards is
the sort of detail `P3-9a`'s testers would notice immediately.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

import numpy as np

Colour = tuple[int, int, int]

# The sheet's own colours. The vehicle's palette is NOT duplicated here — the
# surroundings each decal bakes in are passed by the caller, because the
# no-alpha trick works only while they match the bodywork exactly, and a second
# copy of those values is a mismatch waiting to happen.
WHITE = (244, 244, 240)
BLACK = (24, 24, 26)
PLATE_YELLOW = (240, 196, 42)
BADGE_GREEN = (12, 116, 82)

SHEET = 256
MIME = "image/png"

# 5x7, column-major-free: one string per row, '#' is ink. Only the glyphs the
# roster actually spells — a full ASCII font would be dead weight in a diff.
_GLYPHS: dict[str, tuple[str, ...]] = {
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
}

GLYPH_W, GLYPH_H = 5, 7


@dataclass(frozen=True)
class Patch:
    """One decal's rectangle on the sheet, in pixels."""

    x: int
    y: int
    w: int
    h: int

    def uv(self) -> tuple[float, float, float, float]:
        """(u0, v0, u1, v1). v runs down the image, as glTF expects."""
        return (
            self.x / SHEET,
            self.y / SHEET,
            (self.x + self.w) / SHEET,
            (self.y + self.h) / SHEET,
        )


def _fill(sheet: np.ndarray, patch: Patch, colour: Colour) -> None:
    sheet[patch.y : patch.y + patch.h, patch.x : patch.x + patch.w] = colour


def _text(
    sheet: np.ndarray, text: str, *, patch: Patch, cy: int, scale: int, colour: Colour
) -> None:
    """Draw `text` centred horizontally in `patch`, with its middle at `cy`.

    Bounded to the patch on purpose. This writes straight into the sheet array,
    so without a check an over-long string does not fail — it scribbles across
    whatever decal happens to sit alongside, and the damage shows up later as a
    wrong texture on an unrelated part of the car.
    """
    spacing = (GLYPH_W + 1) * scale
    width = spacing * len(text) - scale
    height = GLYPH_H * scale
    if width > patch.w or height > patch.h:
        raise ValueError(f"{text!r} at scale {scale} does not fit in {patch.w}x{patch.h}")
    x0 = patch.x + (patch.w - width) // 2
    y0 = cy - height // 2
    if y0 < patch.y or y0 + height > patch.y + patch.h:
        raise ValueError(f"{text!r} does not fit vertically at cy={cy}")

    for i, char in enumerate(text):
        glyph = _GLYPHS.get(char.upper())
        if glyph is None:
            raise ValueError(f"no glyph for {char!r} — add it to _GLYPHS")
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "#":
                    _fill(
                        sheet,
                        Patch(x0 + i * spacing + col * scale, y0 + row * scale, scale, scale),
                        colour,
                    )


def _dome(sheet: np.ndarray, patch: Patch, fill: Colour, edge: Colour) -> None:
    """A half-ellipse standing on its flat edge — the 4 SEATS badge outline.

    Drawn as a filled ellipse clipped to its upper half rather than a polygon,
    because the shape is a boundary test per pixel and that is exact at any
    size, where a fan of triangles would show facets on a 40-pixel badge.
    """
    ys, xs = np.mgrid[0 : patch.h, 0 : patch.w]
    nx = (xs - (patch.w - 1) / 2.0) / ((patch.w - 1) / 2.0)
    ny = (patch.h - 1 - ys) / (patch.h - 1)
    radius = nx * nx + ny * ny
    region = sheet[patch.y : patch.y + patch.h, patch.x : patch.x + patch.w]
    region[radius <= 1.0] = edge
    region[radius <= 0.80] = fill


def build_sheet(
    sign_face: Colour, bumper_face: Colour, plate: str = "HK 0521"
) -> tuple[bytes, dict[str, Patch]]:
    """Draw every decal once and return the PNG plus where each one landed.

    `sign_face` and `bumper_face` are the colours of the surfaces the decals
    are stuck to. They are baked into the patches so no alpha channel is
    needed, which is why they are arguments rather than constants here.
    """
    sheet = np.zeros((SHEET, SHEET, 3), dtype=np.uint8)
    patches = {
        "taxi_sign": Patch(0, 0, 128, 40),
        "plate_front": Patch(0, 48, 128, 40),
        "plate_rear": Patch(0, 96, 128, 40),
        "seats4": Patch(144, 8, 96, 56),
    }

    _fill(sheet, patches["taxi_sign"], sign_face)
    _text(sheet, "TAXI", patch=patches["taxi_sign"], cy=20, scale=4, colour=BLACK)

    for key, background in (("plate_front", WHITE), ("plate_rear", PLATE_YELLOW)):
        patch = patches[key]
        _fill(sheet, patch, background)
        _text(sheet, plate, patch=patch, cy=patch.y + patch.h // 2, scale=3, colour=BLACK)

    badge = patches["seats4"]
    _fill(sheet, badge, bumper_face)
    _dome(sheet, badge, BADGE_GREEN, WHITE)
    _text(sheet, "TAXI", patch=badge, cy=badge.y + 16, scale=1, colour=WHITE)
    _text(sheet, "4", patch=badge, cy=badge.y + 30, scale=2, colour=WHITE)
    _text(sheet, "SEATS", patch=badge, cy=badge.y + 46, scale=1, colour=WHITE)

    return _png(sheet), patches


def _png(pixels: np.ndarray) -> bytes:
    """Encode (h, w, 3) uint8 as a PNG. Four chunks and a filter byte per row."""
    height, width, channels = pixels.shape
    if channels != 3:
        raise ValueError(f"expected RGB, got {channels} channels")
    raw = b"".join(b"\x00" + pixels[row].tobytes() for row in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
