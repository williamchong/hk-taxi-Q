"""The façade colour survey (`Q37`) — per-building `(L*, a*, b*)` from photo texture.

The fifth hand-run tool, and the only one that *produces* an input rather than
grading an output. `deck_error.py`, `overhang.py`, `ground_clearance.py` and
`frame_stats.py` all measure a build; this measures the source imagery, and
`pipeline/buildings.py` reads what it writes.

It exists because the survey that produced the shipped `facade_lab.json` was
never committed. That is the whole of `Q37`: a table nobody can re-derive, found
to contain 222 rows measured off atlas filler rather than photography, and
unfixable without rebuilding the measurement from scratch.

⚠️ **Reject filler by structure, never by enumerating greys.** A texel whose
`R == G == B` exactly is padding, not photography — sensor noise makes an exact
three-way tie vanishingly rare in a real pixel. The shipped table's 222 bad rows
span **23 distinct greys**, so the list this replaces was never going to be
complete: it caught pure black, missed `#3c3c3c`, and missed RGB(128,128,128).

⚠️ **The estimator concentrates filler, which is why the defect was invisible.**
Filler is bright — `L*` 53.6 at grey 128, 91.6 at grey 231 — and the estimate is
the median of texels *above* a percentile of `L*`, so padding preferentially wins
the cut it should have lost. Measured on `11-SW-9D`: rejecting filler moves **20
of 59 buildings** by more than 0.46 `Δab` while only **3** were achromatic in the
shipped table. The visible symptom understated the reach by roughly five times.

⚠️ **Averaging in sRGB is a separate question and is deliberately left alone.**
It is worth ~4.9 `L*` against a linear-light mean and is the same family as the
bug `Q27` closed, but changing it here would make it impossible to attribute
which of the two moved the city. One at a time.

The estimate is an **order statistic, not a mean**: the median of wall texels
above `PERCENTILE` of `L*`. That picks the lit face of a building over its
shadowed side, which is what a fly-through sees — and it is also why filler
contaminates it so efficiently.

⚠️ **`pixels` is this tool's own texel count and is not comparable with the
shipped column.** Against the old table the ratio runs from 0.17 to 241 on a
single sheet, so whatever the lost script counted, it was neither covered texels
nor wall area (4.5 to 2,877 per m² — not a density either). `Q34`'s regression on
log pixel count has to be re-fitted, not carried over.

Run:  .venv/bin/python tools/facade_survey.py 11-SW-9D
      .venv/bin/python tools/facade_survey.py --all --out-dir etl/sources/hong_kong/facade_colour
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import posixpath
import sys
import zipfile
from dataclasses import asdict, dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.colour import srgb_to_lab  # noqa: E402
from pipeline.gltf import MeshData, read_scene  # noqa: E402

log = logging.getLogger(__name__)

# Photogrammetry atlases run to 8192 square, past Pillow's decompression-bomb
# guard. The archives are government source data fetched by `pipeline/fetch.py`,
# not untrusted input, so the guard is protecting nothing here.
Image.MAX_IMAGE_PIXELS = None

# Only `B`-prefixed models are buildings. The rest of a sheet is ground, vegetation
# and infrastructure: on `11-SW-9D`, 59 `B` models against one `G`, ten `I`, and one
# each of `T`, `V` and `W`. The 59 match the shipped table's 59 rows for that sheet
# exactly, with no orphan either way.
MODEL_PREFIX = "B"

# A face is a wall when its normal is within 60 degrees of horizontal. The
# threshold is deliberately loose and measurably inert: sweeping it from 0.2 to
# 0.71 moved a test building's estimate by 0.02 `L*`, because photogrammetry
# walls are near-vertical and roofs near-horizontal with very little between.
WALL_COS = 0.5

# Canopy overhanging a facade. `a* < -8` reproduces the shipped `vegetation`
# column to a median 0.007 across `11-SW-9D`, which is what makes the new table's
# rows comparable with `facade_hue.vegetation_max` as it is already configured.
# Chosen over an excess-green index (median error 0.014) for that agreement alone.
VEGETATION_A = -8.0

# The estimator's cut, and the one parameter the record names. `Q37` reports the
# lost script used the 65th percentile of `L*`; reproducing its per-face `L*`
# column actually favours ~80, but the shipped `a*`/`b*` are insensitive across
# that whole range, so the recorded value stands rather than a fitted one.
PERCENTILE = 65.0

# A channel at or above this is clipped — the survey's *first* bug, at the other
# end of the range from filler: a texel at 255 is also `a* = b* = 0`.
CLIP_LEVEL = 255

# Texels sampled per building. The estimate is an order statistic, so a uniform
# subsample is unbiased; without a cap the largest buildings reach 24 million
# texels and the `L*` conversion alone wants half a gigabyte. Sampling is seeded
# from the model name so a rerun reproduces the table exactly.
SAMPLE_CAP = 2_000_000

# Compass names for the four horizontal quadrants, as (axis, sign) on the
# Y-up axes `read_scene` produces: +X is east, and north is -Z because the node
# matrix maps the source's +Y northing onto -Z.
FACES: dict[str, tuple[int, int]] = {"E": (0, 1), "W": (0, -1), "N": (2, -1), "S": (2, 1)}


@dataclass(frozen=True)
class Row:
    """One building's survey row — the shipped `facade_lab.json` schema."""

    lab: list[float]
    lit_rgb: list[int]
    naive_rgb: list[int]
    face_L: dict[str, float | None]
    pixels: int
    clipped: float
    vegetation: float
    height_m: float
    sheet: str


def coverage(uvs: np.ndarray, triangles: np.ndarray, width: int, height: int) -> np.ndarray:
    """Boolean `(height, width)` mask of the texels those triangles cover.

    Rasterised rather than point-sampled so that a texel is counted once however
    many triangles land on it. Sampling per triangle instead would weight a
    finely-tessellated wall above a coarse one photographed at the same
    resolution, which is a property of the mesh and not of the building.
    """
    mask = np.zeros((height, width), dtype=bool)
    pixels = np.stack([uvs[:, 0] * width - 0.5, uvs[:, 1] * height - 0.5], axis=1)
    for triangle in triangles:
        corners = pixels[triangle]
        x0 = max(int(np.floor(corners[:, 0].min())), 0)
        x1 = min(int(np.ceil(corners[:, 0].max())) + 1, width)
        y0 = max(int(np.floor(corners[:, 1].min())), 0)
        y1 = min(int(np.ceil(corners[:, 1].max())) + 1, height)
        if x1 <= x0 or y1 <= y0:
            continue
        edge_a = corners[1] - corners[0]
        edge_b = corners[2] - corners[0]
        determinant = edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0]
        if abs(determinant) < 1e-12:
            continue
        grid_x, grid_y = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
        offset_x = grid_x - corners[0, 0]
        offset_y = grid_y - corners[0, 1]
        alpha = (offset_x * edge_b[1] - offset_y * edge_b[0]) / determinant
        beta = (offset_y * edge_a[0] - offset_x * edge_a[1]) / determinant
        mask[y0:y1, x0:x1] |= (alpha >= 0) & (beta >= 0) & (alpha + beta <= 1)
    return mask


def face_of(normals: np.ndarray) -> np.ndarray:
    """Index into `FACES` for each triangle normal, or `-1` where it is not a wall.

    The dominant horizontal component decides, so every wall lands on exactly one
    face and a 45-degree corner does not count twice.
    """
    horizontal = np.stack([normals[:, 0], normals[:, 2]], axis=1)
    dominant = np.argmax(np.abs(horizontal), axis=1)
    chosen = np.full(len(normals), -1, dtype=np.int8)
    for index, (axis, sign) in enumerate(FACES.values()):
        axis_column = 0 if axis == 0 else 1
        picked = (
            (np.abs(normals[:, 1]) < WALL_COS)
            & (dominant == axis_column)
            & (np.sign(horizontal[:, axis_column]) == sign)
        )
        chosen[picked] = index
    return chosen


def wall_texels(meshes: list[MeshData]) -> dict[str, np.ndarray]:
    """Every textured wall texel of one building, split by compass face.

    Returns `uint8` RGB per face. Empty faces are absent rather than empty, which
    is what puts a `null` in `face_L` for a building with nothing facing that way.
    """
    buckets: dict[str, list[np.ndarray]] = {name: [] for name in FACES}
    names = list(FACES)
    for mesh in meshes:
        if mesh.texture is None or mesh.uvs is None:
            continue
        image = np.asarray(Image.open(io.BytesIO(mesh.texture.data)).convert("RGB"))
        height, width = image.shape[:2]
        normals = mesh.normals[mesh.triangles].mean(axis=1)
        normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
        assigned = face_of(normals)
        for index, name in enumerate(names):
            triangles = mesh.triangles[assigned == index]
            if not len(triangles):
                continue
            buckets[name].append(image[coverage(mesh.uvs, triangles, width, height)])
    return {name: np.concatenate(v) for name, v in buckets.items() if v}


def _subsample(faces: dict[str, np.ndarray], seed: str) -> tuple[dict[str, np.ndarray], int]:
    """Cap the sample, keeping each face's share of it proportional.

    Per-face caps would not do: they would give a 100,000-texel face the same
    weight in the pooled estimate as a 12-million-texel one, which silently turns
    a whole-building median into an average over compass directions.
    """
    total = sum(len(pixels) for pixels in faces.values())
    if total <= SAMPLE_CAP:
        return faces, total
    digest = blake2b(seed.encode("utf-8"), digest_size=8, person=b"survey")
    rng = np.random.default_rng(int.from_bytes(digest.digest(), "big"))
    share = SAMPLE_CAP / total
    kept = {}
    for name, pixels in faces.items():
        take = max(1, round(len(pixels) * share))
        kept[name] = (
            pixels[rng.choice(len(pixels), take, replace=False)] if take < len(pixels) else pixels
        )
    return kept, total


def estimate(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """`(lab, lit_rgb)` for one set of texels, or `None` if none survive the guards.

    ⚠️ **`None` is a refusal to answer, and the caller must keep it one.** The
    shipped table's failure was emitting a neutral grey for a building whose
    sample was entirely padding; a row that says nothing sends the building to its
    height band, which `facade_hue` already documents as the right answer for a
    measurement that did not happen.
    """
    lab = srgb_to_lab(rgb)
    keep = ~is_filler(rgb) & (lab[:, 1] >= VEGETATION_A)
    if keep.sum() < 64:
        return None
    kept_lab, kept_rgb = lab[keep], rgb[keep]
    top = kept_lab[:, 0] >= np.percentile(kept_lab[:, 0], PERCENTILE)
    lit = np.rint(np.median(kept_rgb[top], axis=0))
    return srgb_to_lab(lit[None, :])[0], lit


def is_filler(rgb: np.ndarray) -> np.ndarray:
    """Texels that are atlas padding: an exact three-way channel tie."""
    return (rgb[:, 0] == rgb[:, 1]) & (rgb[:, 1] == rgb[:, 2])


def survey_building(meshes: list[MeshData], name: str, sheet: str) -> Row | None:
    """One building's row, or `None` when nothing measurable survives the guards."""
    faces = wall_texels(meshes)
    if not faces:
        return None
    sampled, total = _subsample(faces, name)
    pooled = np.concatenate(list(sampled.values())).astype(np.float64)
    result = estimate(pooled)
    if result is None:
        log.warning("%s: every wall texel is filler or canopy — no row emitted", name)
        return None
    lab, lit = result

    face_lightness: dict[str, float | None] = {name: None for name in FACES}
    for face, pixels in sampled.items():
        per_face = estimate(pixels.astype(np.float64))
        if per_face is not None:
            face_lightness[face] = round(float(per_face[0][0]), 2)

    keep = ~is_filler(pooled) & (srgb_to_lab(pooled)[:, 1] >= VEGETATION_A)
    low = min(float(mesh.positions[:, 1].min()) for mesh in meshes)
    high = max(float(mesh.positions[:, 1].max()) for mesh in meshes)
    return Row(
        lab=[round(float(value), 2) for value in lab],
        lit_rgb=[int(value) for value in lit],
        naive_rgb=[int(value) for value in np.rint(pooled[keep].mean(axis=0))],
        face_L=face_lightness,
        pixels=total,
        clipped=round(float((pooled >= CLIP_LEVEL).all(axis=1).mean()), 4),
        vegetation=round(float((srgb_to_lab(pooled)[:, 1] < VEGETATION_A).mean()), 4),
        height_m=round(high - low, 2),
        sheet=sheet,
    )


def survey_sheet(archive: Path, *, stem_suffix: int = 2) -> dict[str, dict[str, Any]]:
    """Every building on one sheet, keyed by the stem `pipeline/buildings.py` joins on."""
    sheet = archive.stem
    rows: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(archive) as bundle:
        documents = sorted(
            entry
            for entry in bundle.namelist()
            if entry.endswith(".gltf") and posixpath.basename(entry).startswith(MODEL_PREFIX)
        )
        log.info("%s: %d %s-prefixed models", sheet, len(documents), MODEL_PREFIX)
        for index, document in enumerate(documents, 1):
            name = posixpath.basename(document)[: -len(".gltf")]
            base = posixpath.dirname(document)
            meshes = read_scene(
                bundle.read(document), lambda uri, base=base: bundle.read(posixpath.join(base, uri))
            )
            row = survey_building(meshes, name, sheet)
            if row is None:
                continue
            rows[name[:-stem_suffix]] = asdict(row)
            log.info("  [%d/%d] %s lab=%s", index, len(documents), name, row.lab)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheets", nargs="*", help="sheet ids, e.g. 11-SW-9D")
    parser.add_argument(
        "--zip-dir",
        type=Path,
        default=ROOT / "etl/sources/individualised",
        help="where the individualised sheet archives live",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "etl/sources/hong_kong/facade_colour",
        help="where to write facade_lab.<sheet>.json",
    )
    parser.add_argument("--all", action="store_true", help="every archive in --zip-dir")
    parser.add_argument(
        "--merge", action="store_true", help="also write the merged facade_lab.json"
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    archives = (
        sorted(arguments.zip_dir.glob("*.zip"))
        if arguments.all
        else [arguments.zip_dir / f"{sheet}.zip" for sheet in arguments.sheets]
    )
    if not archives:
        parser.error("name at least one sheet, or pass --all")

    arguments.out_dir.mkdir(parents=True, exist_ok=True)
    merged: dict[str, dict[str, Any]] = {}
    for archive in archives:
        rows = survey_sheet(archive)
        destination = arguments.out_dir / f"facade_lab.{archive.stem}.json"
        destination.write_text(json.dumps(rows, indent=1, sort_keys=True))
        log.info("%s: %d rows -> %s", archive.stem, len(rows), destination)
        clash = merged.keys() & rows.keys()
        if clash:
            raise ValueError(
                f"{archive.stem}: {len(clash)} stems already surveyed, e.g. {min(clash)}"
            )
        merged.update(rows)

    if arguments.merge:
        destination = arguments.out_dir / "facade_lab.json"
        destination.write_text(json.dumps(merged, indent=1, sort_keys=True))
        log.info("merged: %d rows -> %s", len(merged), destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
