"""Set one App Store screenshot under its caption.

The frame is the game's own, scaled down onto a darkened, blurred copy of
itself, with the scene's line from `fastlane/screenshot_captions.json` in the
band above it: the head in the menu's brush (`Q218` — Bakudai Medium in
Chinese, Knewave in English) over a stroke of the brush in the taxi's red, and
a line under it in the interface's 黑體.

The faces are the committed subsets, so a caption is written from the
characters they carry; a character one lacks is refused here, and
`etl/tests/test_fonts.py` holds the file.

Run by `tools/store_screenshots.sh`:

    python tools/caption_screenshot.py <frame.png> <out.jpg> \
        --size 2868x1320 --scene 1_hennessy --lang en
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from font_coverage import read_cmap
from make_splash import hud_colour
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "game" / "assets" / "authored" / "fonts"
CAPTIONS = ROOT / "fastlane" / "screenshot_captions.json"

# The head's face by language, and the line's.
HEAD_FACE: dict[str, str] = {"zh": "TaxiAceBrush-Medium.ttf", "en": "Knewave-Regular.ttf"}
SUB_FACE = "NotoSansHK-subset.ttf"
SUB_WEIGHT = 500

# Shares of the canvas height: the band, the two type sizes, the gap round the
# frame, its corner radius and the backdrop's blur.
BAND = 0.215
HEAD = 0.092
SUB = 0.036
MARGIN = 0.035
CORNER = 0.022
BLUR = 0.03
# How much of the backdrop's light is kept.
DIM = 0.38


def _noise(index: int, seed: int) -> float:
    """`InkStroke._noise`: a fixed wobble in -1..1."""
    return math.sin((index * 131 + seed * 977) * 12.9898) * 43758.5453 % 2.0 - 1.0


def _smoothstep(low: float, high: float, t: float) -> float:
    t = min(max((t - low) / (high - low), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def draw_stroke(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    ink: tuple[int, int, int],
    seed: int = 3,
) -> None:
    """`InkStroke._draw` in `box`: pressed in at the left, the tail parting into streaks."""
    left, top_y, width, height = box
    steps, bristles, rise = 28, 4, 0.18
    body = width * 0.8

    def half_width(t: float) -> float:
        return _smoothstep(0.0, 0.07, t) * (1.0 + (0.62 - 1.0) * t * t)

    top: list[tuple[float, float]] = []
    bottom: list[tuple[float, float]] = []
    for step in range(steps + 1):
        t = step / steps
        half = height * 0.5 * half_width(t)
        mid = top_y + height * (0.5 + rise * (0.5 - t))
        top.append((left + body * t, mid - half * (1.0 + 0.16 * _noise(step, seed))))
        bottom.append((left + body * t, mid + half * (1.0 + 0.16 * _noise(step + 97, seed))))
    draw.polygon(top + bottom[::-1], fill=ink)
    end_mid = top_y + height * (0.5 - rise * 0.5)
    end_half = height * 0.5 * half_width(1.0)
    for bristle in range(bristles):
        y = end_mid + end_half * ((bristle + 0.5) / bristles * 2.0 - 1.0)
        thick = end_half / bristles * (0.55 + 0.35 * abs(_noise(bristle + 211, seed)))
        reach = left + body + (width - body) * (0.45 + 0.55 * abs(_noise(bristle + 307, seed)))
        lift = height * rise * 0.2
        draw.polygon(
            [
                (left + body - 2.0, y - thick),
                (reach, y - lift - thick * 0.15),
                (reach, y - lift + thick * 0.15),
                (left + body - 2.0, y + thick),
            ],
            fill=ink,
        )


def lacking(face: str, text: str) -> str:
    """The characters of `text` that `face` cannot draw."""
    cmap = read_cmap(FONTS / face)
    return "".join(sorted({c for c in text if ord(c) not in cmap}))


def caption_of(scene: str, lang: str) -> tuple[str, str]:
    """The scene's head and the line under it, refused if a face lacks a character."""
    captions = json.loads(CAPTIONS.read_text(encoding="utf-8"))["captions"]
    if scene not in captions or lang not in captions[scene]:
        raise SystemExit(f"{CAPTIONS.name} has no {lang} caption for {scene}")
    said = captions[scene][lang]
    for face, text in ((HEAD_FACE[lang], said["head"]), (SUB_FACE, said["sub"])):
        missing = lacking(face, text)
        if missing:
            raise SystemExit(f"{face} lacks {missing}, asked for by {scene} ({lang})")
    return said["head"], said["sub"]


def _face(face: str, px: float, weight: int | None) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONTS / face), round(px))
    if weight is not None:
        font.set_variation_by_axes([weight])
    return font


def _fitted(
    face: str, text: str, px: float, room: float, weight: int | None = None
) -> ImageFont.FreeTypeFont:
    """`face` at `px`, or smaller if `text` would not fit `room`."""
    font = _face(face, px, weight)
    width = font.getlength(text)
    if width > room:
        font = _face(face, px * room / width, weight)
    return font


def compose(
    frame: Image.Image, size: tuple[int, int], head: str, sub: str, lang: str
) -> Image.Image:
    """The frame under its caption, at `size`."""
    width, height = size
    frame = frame.convert("RGB")

    # The backdrop: the frame itself, filling the canvas, out of focus and dimmed.
    back = ImageOps.fit(frame, size).filter(ImageFilter.GaussianBlur(height * BLUR))
    canvas = Image.blend(Image.new("RGB", size, (0, 0, 0)), back, DIM)

    # The frame, whole, under the band.
    band = height * BAND
    margin = height * MARGIN
    scale = min((width - 2 * margin) / frame.width, (height - band - margin) / frame.height)
    shot = frame.resize((round(frame.width * scale), round(frame.height * scale)), Image.LANCZOS)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, shot.width - 1, shot.height - 1), radius=round(height * CORNER), fill=255
    )
    at = ((width - shot.width) // 2, round(band + (height - band - margin - shot.height) / 2))
    canvas.paste(shot, at, mask)

    draw = ImageDraw.Draw(canvas)
    room = width - 4 * margin
    head_font = _fitted(HEAD_FACE[lang], head, height * HEAD, room)
    sub_font = _fitted(SUB_FACE, sub, height * SUB, room, SUB_WEIGHT)

    head_y = band * 0.40
    head_width = head_font.getlength(head)
    # The stroke runs past the words at both ends, the tail the longer.
    draw_stroke(
        draw,
        (
            (width - head_width) / 2 - height * HEAD * 0.45,
            head_y - height * HEAD * 0.60,
            head_width + height * HEAD * 1.5,
            height * HEAD * 1.2,
        ),
        hud_colour("brush_stroke"),
    )
    draw.text((width / 2, head_y), head, font=head_font, fill=hud_colour("chip_ink"), anchor="mm")
    draw.text(
        (width / 2, band * 0.82), sub, font=sub_font, fill=hud_colour("chip_muted"), anchor="mm"
    )
    return canvas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("frame", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--size", required=True, help="the uploaded size, WxH")
    parser.add_argument("--scene", required=True, help="the scene's name in the captions file")
    parser.add_argument("--lang", required=True, choices=sorted(HEAD_FACE))
    args = parser.parse_args(argv)

    width, height = (int(n) for n in args.size.split("x"))
    head, sub = caption_of(args.scene, args.lang)
    image = compose(Image.open(args.frame), (width, height), head, sub, args.lang)
    image.save(args.out, quality=92)
    return 0


if __name__ == "__main__":
    sys.exit(main())
