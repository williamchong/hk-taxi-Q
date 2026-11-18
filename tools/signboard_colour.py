"""The signboard colour survey (`P3-103`, `Q260`): each board's colour off its photo.

Every row of the Buildings Department's signboards database links a one-page
photo PDF with the board outlined in red. This tool downloads the photos of
every board inside a driven region, finds the outline, and measures the colour
inside it. `pipeline/signboards.py` reads the table it writes; the build never
reads a photo.

    python tools/signboard_colour.py [--regions wan_chai causeway_bay] [--jobs 8]
        [--sheet contact.png]

🔴 **Only a colour leaves this tool.** No pixel, crop or text reaches the
table, and the photos stay under `etl/sources/` with the rest of the
government data (hard rule 7). Some photos were submitted by a board's
applicant; `LICENSING.md` carries that as an open item.

⚠️ **The outline is a vector in most PDFs, and that is what makes this cheap.**
The photo is embedded clean and the red rectangle, or a four-point outline that
follows the perspective, is a path drawn over it (`1 0 0 RG`). Its points are
read in page space, every red path is removed, and the page is rendered: the
board's pixels without guessing and without the outline's own red. A scanned
record sheet has its outline in the raster instead; that is found as the
largest thin red ring on the rendered page (`method: raster`).

⚠️ **A board is a ground and lettering, and the ground is what is wanted.** The
pixels are clustered in CIELAB (k = 3, seeded from lightness quantiles so a run
is reproducible) and the cluster scoring `size x (1 + chroma / 30)` wins: white
letters on an orange ground lose to the ground because a lit ground spreads
across shades a saturated letter does not. `share` is the winner's part of the
outline, and `signboards.survey_min_share` is the bar the build reads it at.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

import pypdfium2 as pdfium  # noqa: E402
import pypdfium2.raw as pdfium_c  # noqa: E402
from pipeline.colour import srgb_to_lab  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.fetch import download, source_dir  # noqa: E402
from pipeline.signboards import (  # noqa: E402
    COLOUR_SOURCE_ID,
    COLOUR_SURVEY_SCHEMA,
    SignboardReport,
    read_boards,
)

log = logging.getLogger("signboard_colour")

# Only the publisher's own bucket is downloaded from: the link is data, and a
# row pointing anywhere else is refused rather than followed.
PHOTO_PREFIX = "https://storage.googleapis.com/legal-signboard-image-hosting-prod/"
PHOTOS_DIR = "photos"
# Render scale: 2.0 is 144 dpi, about the embedded photos' own resolution.
SCALE = 2.0
# A stroke or fill is the outline's red when red is high and the others low.
RED_MIN, OTHER_MAX, RED_LEAD = 180, 100, 120
# The outline's inside is sampled shrunk to this share about its centroid, clear
# of the stroke and of a board's own frame.
INSET = 0.75
MIN_PIXELS = 60
CLUSTERS = 3
CHROMA_WEIGHT = 30.0
# A raster ring: the red pixels' bounding box must be at least this many
# pixels a side and the red at most this share of it, or it is lettering.
RING_MIN_PX = 20
RING_MAX_FILL = 0.3


def red_mask(pixels: np.ndarray) -> np.ndarray:
    """Which of `pixels` (any shape ending in RGB) are the outline's red."""
    r, g, b = (pixels[..., i].astype(int) for i in range(3))
    return (r >= RED_MIN) & (g <= OTHER_MAX) & (b <= OTHER_MAX) & (r - np.maximum(g, b) >= RED_LEAD)


def red(rgb: tuple[int, int, int]) -> bool:
    return bool(red_mask(np.array(rgb)))


def _colour(getter, obj) -> tuple[int, int, int] | None:
    channels = [ctypes.c_uint() for _ in range(4)]
    if not getter(obj.raw, *[ctypes.byref(c) for c in channels]):
        return None
    return channels[0].value, channels[1].value, channels[2].value


def outlines(page: pdfium.PdfPage, seen: list) -> tuple[list[list[tuple[float, float]]], list]:
    """Every red path's points in page space, and the path objects themselves.

    Every object walked is appended to `seen`, so the caller closes each before
    its document: pypdfium2 asserts if a child's finaliser outlives the parent.
    """
    rings, objects = [], []
    for obj in page.get_objects(filter=(pdfium_c.FPDF_PAGEOBJ_PATH,), max_depth=8):
        seen.append(obj)
        stroke = _colour(pdfium_c.FPDFPageObj_GetStrokeColor, obj)
        fill = _colour(pdfium_c.FPDFPageObj_GetFillColor, obj)
        if not ((stroke and red(stroke)) or (fill and red(fill))):
            continue
        matrix = obj.get_matrix()
        points = []
        for index in range(pdfium_c.FPDFPath_CountSegments(obj.raw)):
            segment = pdfium_c.FPDFPath_GetPathSegment(obj.raw, index)
            x, y = ctypes.c_float(), ctypes.c_float()
            pdfium_c.FPDFPathSegment_GetPoint(segment, ctypes.byref(x), ctypes.byref(y))
            points.append(matrix.on_point(x.value, y.value))
        objects.append(obj)
        if len(points) >= 3:
            rings.append(points)
    return rings, objects


def _area(points: np.ndarray) -> float:
    x, y = points[:, 0], points[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def raster_ring(image: np.ndarray) -> np.ndarray | None:
    """The largest thin red ring on a rendered page, as its bounding box's corners."""
    mask = red_mask(image)
    if mask.sum() < RING_MIN_PX * 4:
        return None
    # Components on a 4x coarser grid, flood-filled: the rings are lines, so a
    # coarse cell joins a stroke's anti-aliased gaps.
    rows, columns = mask.shape[0] // 4, mask.shape[1] // 4
    coarse = mask[: rows * 4, : columns * 4].reshape(rows, 4, columns, 4).any(axis=(1, 3))
    seen = np.zeros_like(coarse)
    best = None
    for start in zip(*np.nonzero(coarse), strict=True):
        if seen[start]:
            continue
        stack, cells = [start], []
        seen[start] = True
        while stack:
            row, col = stack.pop()
            cells.append((row, col))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = row + dr, col + dc
                    if (
                        0 <= nr < coarse.shape[0]
                        and 0 <= nc < coarse.shape[1]
                        and coarse[nr, nc]
                        and not seen[nr, nc]
                    ):
                        seen[nr, nc] = True
                        stack.append((nr, nc))
        rows, cols = np.array(cells).T
        height, width = (rows.max() - rows.min() + 1) * 4, (cols.max() - cols.min() + 1) * 4
        if min(height, width) < RING_MIN_PX or len(cells) * 16 > RING_MAX_FILL * height * width:
            continue
        if best is None or height * width > best[0]:
            top, left = rows.min() * 4, cols.min() * 4
            best = (
                height * width,
                np.array(
                    [
                        [left, top],
                        [left + width, top],
                        [left + width, top + height],
                        [left, top + height],
                    ],
                    float,
                ),
            )
    return None if best is None else best[1]


def dominant(pixels: np.ndarray) -> tuple[np.ndarray, float]:
    """The board's ground: the winning cluster's mean sRGB and its share."""
    lab = srgb_to_lab(pixels.astype(np.float64))
    centres = np.array(
        [
            lab[lab[:, 0] <= np.quantile(lab[:, 0], q)].mean(axis=0)
            if (lab[:, 0] <= np.quantile(lab[:, 0], q)).any()
            else lab.mean(axis=0)
            for q in (0.2, 0.5, 0.9)
        ]
    )
    for _ in range(12):
        label = np.argmin(((lab[:, None, :] - centres[None]) ** 2).sum(axis=2), axis=1)
        for k in range(CLUSTERS):
            if (label == k).any():
                centres[k] = lab[label == k].mean(axis=0)
    sizes = np.bincount(label, minlength=CLUSTERS).astype(float)
    chroma = np.hypot(centres[:, 1], centres[:, 2])
    winner = int(np.argmax(sizes * (1.0 + chroma / CHROMA_WEIGHT)))
    return pixels[label == winner].mean(axis=0), float(sizes[winner] / len(pixels))


def measure(path: Path) -> dict:
    """One photo's board colour, or the reason there is none."""
    document = pdfium.PdfDocument(str(path))
    seen: list = []
    page = None
    try:
        page = document[0]
        _, height = page.get_size()
        rings, objects = outlines(page, seen)
        for obj in objects:
            page.remove_obj(obj)
        if objects:
            page.gen_content()
        image = np.asarray(page.render(scale=SCALE).to_pil().convert("RGB"))
        method = "vector"
        if rings:
            ring = max((np.array(r) for r in rings), key=_area)
            pixel = np.column_stack([ring[:, 0] * SCALE, (height - ring[:, 1]) * SCALE])
        else:
            pixel = raster_ring(image)
            method = "raster"
            if pixel is None:
                return {"failed": "no outline"}
        centre = pixel.mean(axis=0)
        inner = centre + (pixel - centre) * INSET
        mask = Image.new("L", (image.shape[1], image.shape[0]), 0)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in inner], fill=255)
        inside = np.asarray(mask) > 0
        pixels = image[inside]
        if method == "raster":
            pixels = pixels[~red_mask(pixels)]
        # Page white past the photo is not the board.
        pixels = pixels[~(pixels.min(axis=1) >= 250)]
        if len(pixels) < MIN_PIXELS:
            return {"failed": "too few pixels"}
        rgb, share = dominant(pixels)
        return {
            "rgb": "#{:02x}{:02x}{:02x}".format(*(round(v) for v in rgb)),
            "share": round(share, 3),
            "method": method,
            "pixels": len(pixels),
        }
    finally:
        for obj in seen:
            obj.close()
        if page is not None:
            page.close()
        document.close()


def fetch_photo(ident: str, url: str, photos: Path) -> tuple[str, Path | None, str | None]:
    target = photos / f"{ident}.pdf"
    if target.exists():
        return ident, target, None
    if not url.startswith(PHOTO_PREFIX):
        return ident, None, "foreign link"
    try:
        download(url, target)
    except Exception as error:
        return ident, None, f"download: {type(error).__name__}"
    return ident, target, None


def contact_sheet(rows: list[tuple[Path, dict]], out: Path) -> None:
    """Each measured photo beside its colour swatch, for a look by eye."""
    tiles = []
    for path, entry in rows:
        document = pdfium.PdfDocument(str(path))
        page = document[0]
        try:
            thumb = page.render(scale=0.5).to_pil().convert("RGB")
        finally:
            page.close()
            document.close()
        thumb.thumbnail((200, 280))
        tile = Image.new("RGB", (300, 290), "white")
        tile.paste(thumb, (0, 0))
        draw = ImageDraw.Draw(tile)
        draw.rectangle((210, 20, 290, 140), fill=entry["rgb"])
        draw.text((210, 150), f"{path.stem}\n{entry['share']:.2f}\n{entry['method']}", fill="black")
        tiles.append(tile)
    columns = 6
    sheet = Image.new(
        "RGB", (300 * columns, 290 * ((len(tiles) + columns - 1) // columns)), "white"
    )
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % columns) * 300, (index // columns) * 290))
    sheet.save(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--regions", nargs="*", default=None)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None, help="measure only the first N boards")
    parser.add_argument("--sheet", type=Path, default=None, help="write a contact sheet here")
    parser.add_argument("--sheet-count", type=int, default=48)
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    spec = city.signboards
    if spec is None or spec.colour_survey is None:
        log.error("the city declares no signboards.colour_survey; nothing to measure")
        return 1
    regions = arguments.regions or sorted(city.drivable_regions)
    boards = {}
    for region_id in regions:
        report = SignboardReport()
        for board in read_boards(city, spec, region_id, city.game_transform(region_id), report):
            if board.photo:
                boards[board.ident] = board.photo
    idents = sorted(boards, key=lambda ident: (len(ident), ident))[: arguments.limit]
    out_dir = source_dir(COLOUR_SOURCE_ID)
    photos = out_dir / PHOTOS_DIR
    photos.mkdir(parents=True, exist_ok=True)
    log.info("signboard colour: %d boards with a photo in %s", len(idents), ", ".join(regions))

    with ThreadPoolExecutor(max_workers=arguments.jobs) as pool:
        fetched = list(pool.map(lambda ident: fetch_photo(ident, boards[ident], photos), idents))

    measured: dict[str, dict] = {}
    failed: dict[str, str] = {}
    for ident, path, problem in fetched:
        if path is None:
            failed[ident] = problem or "download"
            continue
        try:
            entry = measure(path)
        except Exception as error:
            entry = {"failed": f"unreadable: {type(error).__name__}"}
        if "failed" in entry:
            failed[ident] = entry["failed"]
        else:
            measured[ident] = entry

    reasons: dict[str, int] = {}
    for reason in failed.values():
        reasons[reason] = reasons.get(reason, 0) + 1
    shares = np.array([entry["share"] for entry in measured.values()]) if measured else np.zeros(1)
    document = {
        "schema_version": COLOUR_SURVEY_SCHEMA,
        "built": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regions": regions,
        "boards_with_photo": len(idents),
        "measured": len(measured),
        "by_method": {
            method: sum(1 for e in measured.values() if e["method"] == method)
            for method in ("vector", "raster")
        },
        "failed_by_reason": dict(sorted(reasons.items())),
        "share_p50": round(float(np.median(shares)), 3),
        "boards": dict(sorted(measured.items(), key=lambda item: (len(item[0]), item[0]))),
        "failed": dict(sorted(failed.items(), key=lambda item: (len(item[0]), item[0]))),
    }
    target = out_dir / spec.colour_survey
    target.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info(
        "signboard colour: %d measured (%s), %d failed %s, share p50 %.2f -> %s",
        len(measured),
        document["by_method"],
        len(failed),
        document["failed_by_reason"],
        document["share_p50"],
        target,
    )
    if arguments.sheet is not None:
        rows = [
            (photos / f"{ident}.pdf", measured[ident])
            for ident in list(measured)[: arguments.sheet_count]
        ]
        contact_sheet(rows, arguments.sheet)
        log.info("contact sheet -> %s", arguments.sheet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
