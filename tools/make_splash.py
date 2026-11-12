"""Draw the boot splash: the loading screen's toy taxi, standing still (`Q209`).

One image is both Godot's boot splash (`application/boot_splash/image`) and the
iOS launch screen, which the iOS export builds from the same setting. It holds
the screen from the tap until the city has built, about 4 to 5 s on an iPhone Air
cold, while the engine's main thread is blocked and nothing can move. Then
`LoadingCover` takes over in the same place: the taxi starts idling and the
meter appears under it.

**One drawing, two readers.** The taxi, the layout and the colours are
`game/assets/authored/loading/taxi.json`. This draws its still frame; the cover
draws it live from the same file, so a change is one edit and a re-run here, and
`test_make_splash.py` fails when the committed image is stale.

**Square, on the field's colour.** The project fits the splash to the window
keeping its aspect, so a square image always scales by the screen's height on a
landscape screen. The cover lays out against the height too, which is what makes
the two coincide at every aspect. The field is `HudStyle.plate_field`, read from
`hud_style.tres`, and `verify_menu` holds `boot_splash/bg_color` to it, so the
letterbox around the square is the same colour as the square.

The image is hand-authored (CC BY-SA, `assets/authored/LICENSE`): shapes and the
bundled Kai, no frame of the city, which would be the government data committed
in another form (hard rule 7).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "game"
DRAWING = GAME / "assets/authored/loading/taxi.json"
MENU_TEXT = GAME / "tuning/menu_text.json"
HUD_STYLE = GAME / "tuning/hud_style.tres"
FONT = GAME / "assets/authored/fonts/FreeHKKai4700-v1.02.ttf"
DEFAULT_OUT = GAME / "assets/authored/loading/boot_splash.png"

## The image's side, in pixels: three pixels to a stage unit, so a 3x phone
## (1260 px tall on an iPhone Air) only ever scales it down.
SIDE_PX = 1680
## Drawn this many times larger and filtered down, for clean edges.
SUPERSAMPLE = 2
## Points per rounded corner, as `LoadingCover` builds them.
CORNER_STEPS = 6

log = logging.getLogger(__name__)


def plate_field() -> tuple[int, int, int]:
    """`HudStyle.plate_field` from `hud_style.tres`, as 8-bit sRGB."""
    text = HUD_STYLE.read_text(encoding="utf-8")
    match = re.search(r"^plate_field = Color\(([^)]*)\)", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"{HUD_STYLE} has no plate_field")
    r, g, b = (float(v) for v in match.group(1).split(",")[:3])
    return (round(r * 255), round(g * 255), round(b * 255))


def loading_line() -> str:
    """The loading row of `menu_text.json`, both languages, as the cover says it."""
    row = json.loads(MENU_TEXT.read_text(encoding="utf-8"))["strings"]["loading"]
    return f"{row['zh']} · {row['en']}"


def hex_colour(value: str) -> tuple[int, int, int]:
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rounded_rect(
    x0: float, y0: float, x1: float, y1: float, radius: float
) -> list[tuple[float, float]]:
    """A rounded rectangle as a point list, corner by corner, clockwise from the top right."""
    points: list[tuple[float, float]] = []
    corners = (
        (x1 - radius, y0 + radius, -90.0),
        (x1 - radius, y1 - radius, 0.0),
        (x0 + radius, y1 - radius, 90.0),
        (x0 + radius, y0 + radius, 180.0),
    )
    for cx, cy, start in corners:
        for step in range(CORNER_STEPS + 1):
            angle = math.radians(start + 90.0 * step / CORNER_STEPS)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return points


def draw_splash(drawing: dict[str, Any], field: tuple[int, int, int], line: str) -> Image.Image:
    """The still frame: the taxi at rest on its ground line and the loading line under it."""
    side = SIDE_PX * SUPERSAMPLE
    scale = side / drawing["stage_px"]
    image = Image.new("RGB", (side, side), field)
    draw = ImageDraw.Draw(image)
    centre = side / 2.0

    def at(x: float, y: float) -> tuple[float, float]:
        return (centre + x * scale, centre + y * scale)

    def font(px: float) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(FONT), round(px * scale))

    ground = drawing["ground_y"]
    body_y = ground - drawing["ride_px"]
    half = drawing["ground_half_px"]
    draw.line(
        (at(-half, ground), at(half, ground)),
        fill=hex_colour(drawing["ground_colour"]),
        width=max(1, round(scale)),
    )
    for shape in drawing["body"]:
        colour = hex_colour(shape["colour"])
        if "rrect" in shape:
            x0, y0, x1, y1 = shape["rrect"]
            outline = rounded_rect(x0, y0 + body_y, x1, y1 + body_y, shape["radius"])
            draw.polygon([at(x, y) for x, y in outline], fill=colour)
        else:
            x, y = shape["at"]
            draw.text(
                at(x, y + body_y), shape["text"], font=font(shape["px"]), fill=colour, anchor="mt"
            )
    wheels = drawing["wheels"]
    for x in wheels["x"]:
        for radius, colour in (
            (wheels["radius"], wheels["tyre"]),
            (wheels["hub_radius"], wheels["hub"]),
        ):
            cx, cy = at(x, ground - wheels["radius"])
            r = radius * scale
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=hex_colour(colour))
    spec = drawing["line"]
    draw.text(
        at(0.0, spec["y"]),
        line,
        font=font(spec["px"]),
        fill=hex_colour(spec["colour"]),
        anchor="mt",
    )
    return image.resize((SIDE_PX, SIDE_PX), Image.Resampling.LANCZOS)


def write_splash(out: Path) -> Path:
    drawing = json.loads(DRAWING.read_text(encoding="utf-8"))
    image = draw_splash(drawing, plate_field(), loading_line())
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="PNG", optimize=True)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output PNG")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = write_splash(args.out)
    log.info("%s: %d B", path, path.stat().st_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
