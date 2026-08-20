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

⚠️ **That structural rule is right and its axis was wrong — `Q55`.** Greyness is
*a* signature of fill, not *the* signature. **97 atlases on 93 of 2,213 buildings**
carry a flat **coloured** panel and the tie above passes every one, moving 43
buildings past `Q33`'s 0.46 `Δab` tolerance and one by **54.69 `L*`**. `Q37` had
already written the second clause — *"detect each atlas's filler as its modal
exactly-repeated colour"* — and the principle under it: **achromatic is not the
defect's signature; repetition is.** `filler_colours` is that clause, and
`--filler-report` is the sweep, because every number in `Q55` came from a scratch
script and a record no tool reproduces ages into an assertion.

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
      .venv/bin/python tools/facade_survey.py --all --merge
      .venv/bin/python tools/facade_survey.py --all --filler-report
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import posixpath
import sys
import zipfile
from collections import defaultdict
from dataclasses import asdict, dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.buildings import HUE_SOURCE_ID, resolver, stem  # noqa: E402
from pipeline.colour import srgb_to_lab  # noqa: E402
from pipeline.fetch import SOURCES_ROOT, source_dir  # noqa: E402
from pipeline.gltf import MeshData, normalise, read_scene  # noqa: E402

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

# Matched case-insensitively, as `pipeline/buildings.py` matches it.
GLTF_SUFFIX = ".gltf"

# Where `pipeline/fetch.py`'s cache holds the individualised sheet archives.
# Three survey tools take it as their `--zip-dir` default; one definition.
INDIVIDUALISED_DIR = SOURCES_ROOT / "individualised"

# The table's filename, which `hong_kong.yaml` names as `facade_hue.source` and
# `buildings.facade_hue` opens. Per sheet it takes the sheet id as an infix.
TABLE_STEM = "facade_lab"

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

# A colour holding this much of one atlas is fill, not photography — the second
# filler axis, and the one `is_filler`'s channel tie cannot see. `Q37` wrote it
# down ("detect each atlas's filler as its modal exactly-repeated colour") and
# shipped only the tie; `Q55` measured the gap at **97 atlases on 93 of 2,213
# buildings**, whose panels are literally the same files — each colour resolving
# to exactly one `blake2b` digest, one of them a 512x256 PNG of a single colour
# repeated on eight buildings across all six sheets.
#
# ⚠️ **Every colour over the bar is taken, not only the modal one.** `Q37` says
# "modal"; at 20% no more than five colours can qualify (the test is `>=`, so
# five at exactly a fifth each all pass), taking them all costs nothing, and an
# atlas carrying two panels is a case `Q55` observed.
MODAL_SHARE = 0.20

# The lattice the share is counted on, matching `Q55`'s sweep. An 8192-square
# atlas is 67 million texels and the panels this is looking for run to 96.5% of a
# building's walls, so 1-in-16 is far more resolution than the question needs.
MODAL_STRIDE = 4

# `Q33`'s hue-preservation bound, reused by `Q37` and `Q55` as the bar past which
# a re-estimated building counts as moved. Reported, never enforced: this tool
# grades, and `Q55` is explicit that a widening gap is a finding to go and look
# at rather than a threshold to retune against.
DAMAGE_AB = 0.46

# The estimator's cut, and the one parameter the record names. `Q37` reports the
# lost script used the 65th percentile of `L*`; reproducing its per-face `L*`
# column actually favours ~80, but the shipped `a*`/`b*` are insensitive across
# that whole range, so the recorded value stands rather than a fitted one.
PERCENTILE = 65.0

# A texel with **any** channel at or above this is clipped — the survey's *first*
# bug, at the other end of the range from filler: a texel at 255 is also
# `a* = b* = 0`. ⚠️ Testing every channel instead would only ever match white,
# which `is_filler` already rejects, so the column would silently report a
# fraction of the padding rather than the blown highlights it is named for.
CLIP_LEVEL = 255

# Below this many photographic texels a building has not been measured, and the
# honest row is no row. Small enough that only near-total padding trips it.
MIN_TEXELS = 64

# Texels carried into the `L*` conversion per building. The estimate is an order
# statistic, so a uniform subsample is unbiased; the largest building in the
# region gathers 90.1 million texels and 40% of rows exceed this cap, so without
# it the conversion alone would want gigabytes. ⚠️ **It bounds the conversion and
# not the tool's peak** — the uint8 gather that feeds it happens first and is
# larger. Sampling is seeded from the model name so a rerun reproduces the table.
SAMPLE_CAP = 2_000_000

# Compass names for the four horizontal quadrants, as (column, sign) into the
# (x, z) pair `face_of` builds. On the Y-up axes `read_scene` produces, +X is
# east, and north is -Z because the node matrix maps the source's +Y northing
# onto -Z.
FACES: dict[str, tuple[int, int]] = {"E": (0, 1), "W": (0, -1), "N": (1, -1), "S": (1, 1)}


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
        # Broadcast a row against a column rather than materialising two integer
        # grids per triangle: `alpha` and `beta` come out the same shape, with the
        # same values in the same order, and nine thousand allocations do not.
        offset_x = np.arange(x0, x1) - corners[0, 0]
        offset_y = np.arange(y0, y1)[:, None] - corners[0, 1]
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
    is_wall = np.abs(normals[:, 1]) < WALL_COS
    chosen = np.full(len(normals), -1, dtype=np.int8)
    for index, (column, sign) in enumerate(FACES.values()):
        picked = is_wall & (dominant == column) & (np.sign(horizontal[:, column]) == sign)
        chosen[picked] = index
    return chosen


def assigned_faces(mesh: MeshData) -> np.ndarray:
    """`face_of` over one mesh's triangle normals — the one way every survey
    tool assigns a triangle to a compass face, so they cannot drift apart."""
    return face_of(normalise(mesh.normals[mesh.triangles].mean(axis=1)))


def claim_stems(merged: dict, rows: dict, sheet: str) -> None:
    """Refuse a stem surveyed on two sheets, before `rows` joins `merged`.

    Shared by both merge writers (`facade_glazing.py`, `facade_grammar.py`) so
    the pipeline can rely on one error contract: a duplicate stem is a survey
    defect to raise on, never a row to silently overwrite.
    """
    clash = merged.keys() & rows.keys()
    if clash:
        raise ValueError(f"{sheet}: {len(clash)} stems already surveyed, e.g. {min(clash)}")


def sheet_documents(bundle: zipfile.ZipFile) -> dict[str, str]:
    """Building name → archive entry: one sheet's `B`-prefixed models."""
    return {
        posixpath.basename(entry)[: -len(GLTF_SUFFIX)]: entry
        for entry in bundle.namelist()
        if entry.lower().endswith(GLTF_SUFFIX)
        and posixpath.basename(entry).startswith(MODEL_PREFIX)
    }


def load_building(bundle: zipfile.ZipFile, entry: str) -> list[MeshData]:
    """One building's meshes, textures resolved from inside the sheet archive."""
    return read_scene(bundle.read(entry), resolver(bundle, posixpath.dirname(entry)))


def decode_textures(
    meshes: list[MeshData], decoded: dict[int, np.ndarray] | None = None
) -> dict[int, np.ndarray]:
    """RGB arrays keyed by `id(mesh.texture)` — one decode per distinct atlas.

    `read_scene` hands the same `Texture` object to every primitive sharing an
    atlas, so identity is a sound dedupe key. An 8k atlas decode is the
    dominant cost of every tool that reads the photography; a caller measuring
    the same building more than one way passes the dict through so each atlas
    is paid for once, not once per measurement.
    """
    decoded = {} if decoded is None else decoded
    for mesh in meshes:
        if mesh.texture is None or mesh.uvs is None:
            continue
        key = id(mesh.texture)
        if key not in decoded:
            decoded[key] = np.asarray(Image.open(io.BytesIO(mesh.texture.data)).convert("RGB"))
    return decoded


def wall_texels(
    meshes: list[MeshData], decoded: dict[int, np.ndarray] | None = None
) -> dict[str, np.ndarray]:
    """Every textured wall texel of one building, split by compass face.

    Returns `uint8` RGB per face. Empty faces are absent rather than empty, which
    is what puts a `null` in `face_L` for a building with nothing facing that way.
    """
    decoded = decode_textures(meshes, decoded)
    buckets: dict[str, list[np.ndarray]] = {name: [] for name in FACES}
    names = list(FACES)
    for mesh in meshes:
        if mesh.texture is None or mesh.uvs is None:
            continue
        image = decoded[id(mesh.texture)]
        height, width = image.shape[:2]
        assigned = assigned_faces(mesh)
        flat = image.reshape(-1, 3)
        for index, name in enumerate(names):
            triangles = mesh.triangles[assigned == index]
            if not len(triangles):
                continue
            # `compress` over the flattened atlas rather than `image[mask]`: same
            # rows in the same order, six times faster, and this gather is the
            # tool's largest single cost.
            mask = coverage(mesh.uvs, triangles, width, height)
            buckets[name].append(np.compress(mask.ravel(), flat, axis=0))

    # Concatenating in a comprehension would hold every chunk alongside every
    # joined array, doubling the peak on exactly the buildings that set it.
    gathered = {}
    for name, chunks in buckets.items():
        if chunks:
            gathered[name] = np.concatenate(chunks)
            chunks.clear()
    return gathered


def _subsample(faces: dict[str, np.ndarray], seed: str) -> dict[str, np.ndarray]:
    """Cap the sample, keeping each face's share of it proportional.

    Per-face caps would not do: they would give a 100,000-texel face the same
    weight in the pooled estimate as a 12-million-texel one, which silently turns
    a whole-building median into an average over compass directions.
    """
    total = sum(len(pixels) for pixels in faces.values())
    if total <= SAMPLE_CAP:
        return faces
    digest = blake2b(seed.encode("utf-8"), digest_size=8, person=b"survey")
    rng = np.random.default_rng(int.from_bytes(digest.digest(), "big"))
    share = SAMPLE_CAP / total
    kept = {}
    for name, pixels in faces.items():
        take = max(1, round(len(pixels) * share))
        kept[name] = (
            pixels[rng.choice(len(pixels), take, replace=False)] if take < len(pixels) else pixels
        )
    return kept


def _pack(rgb: np.ndarray) -> np.ndarray:
    """One `uint32` per texel, so a colour counts and compares as a scalar.

    Accepts a texel list or a whole image and always returns a flat array. Built
    up in place from the first channel rather than through an `astype` of the
    whole thing: that intermediate is 12 bytes a texel, and it would land at
    exactly the moment the gather is at its peak. This tool's ceiling is memory
    rather than time — 84 MB against 17 on an 8192-square atlas's lattice.

    ⚠️ **Anything not already unsigned is normalised first.** A non-integral float
    would truncate toward zero and silently miss its colour, so floats are rounded
    rather than cast; a *signed* array cannot be `|=`'d into a `uint32` at all
    (numpy refuses `int64 -> uint32` under `same_kind`), and `np.array([(68, 65,
    65)])` is signed, which is how a caller most naturally spells one texel.
    """
    if rgb.dtype.kind != "u":
        rgb = np.rint(rgb).astype(np.uint32)
    packed = rgb[..., 0].astype(np.uint32)
    packed <<= 8
    packed |= rgb[..., 1]
    packed <<= 8
    packed |= rgb[..., 2]
    return packed.ravel()


def _unpack(colour: int) -> tuple[int, int, int]:
    """A packed colour back to `(r, g, b)`, for reporting."""
    return (colour >> 16) & 255, (colour >> 8) & 255, colour & 255


def _repeats(rgb: np.ndarray, colours: frozenset[int]) -> np.ndarray:
    """Texels whose exact colour is one its atlas repeats.

    ⚠️ **One definition, shared by the guard and the sweep.** `is_filler` rejects
    on this and `--filler-report`'s `wall_share` column grades it; two spellings
    would let the column come to describe a rule the build does not run, which is
    the shape of `Q55` itself.

    An explicit disjunction rather than `np.isin`: `MODAL_SHARE` caps the needle
    set at five, and numpy's integer path builds a lookup table over the *colour
    range* — up to 16.7 million entries — which measures 19-26x slower and
    allocates 30 MB against 4 on a 2 million-texel sample.

    Sized from the packed array rather than from `rgb`, so the shape follows
    `_pack` for an image as well as for a texel list. Both callers guard on a
    non-empty `colours`; an empty one is all-False rather than an error.
    """
    packed = _pack(rgb)
    mask = np.zeros(len(packed), dtype=bool)
    for colour in colours:
        mask |= packed == colour
    return mask


def _atlas_filler(image: np.ndarray) -> tuple[frozenset[int], int]:
    """One atlas's repeated colours, and how many distinct colours it holds.

    The single definition of the rule. `filler_colours` unions the first half and
    `--filler-report` prints both, so the sweep cannot come to describe a
    different rule than the one that ships — which is exactly how `Q55` happened.

    ⚠️ **Both halves are counted on the lattice, not on the atlas.** The share is
    what the guard turns on, and a flat panel is flat at any sampling, so that
    half is exact. The distinct count is a *sample* of the atlas's palette: on a
    real 4096-square atlas the lattice is a million texels and sees essentially
    all of a 34,000-colour palette, but on anything small it reads low. It is a
    diagnostic either way and nothing turns on it.
    """
    lattice = _pack(image[::MODAL_STRIDE, ::MODAL_STRIDE])
    if not len(lattice):
        return frozenset(), 0
    values, counts = np.unique(lattice, return_counts=True)
    over = (int(value) for value in values[counts >= MODAL_SHARE * len(lattice)])
    # The scalar spelling of `is_filler`'s vectorised tie. Both are exact
    # equality, so they cannot drift in value; `test_facade_survey.py` pins the
    # two axes disjoint in one assertion pair rather than trusting that.
    # ⚠️ **A repeated *grey* is dropped here, because `Q37`'s axis already has
    # it.** Two thirds of the atlases on a sheet repeat `#3c3c3c`, black or white
    # past this bar, and a colour the tie rejects anyway adds nothing to the
    # guard. What it would add is a *finding*: `--filler-report` would then carry
    # a row for nearly every building in the region, each with a zero delta, and
    # report "2,213 buildings carry a repeated panel" where `Q55` found **93**.
    # The sweep exists to reproduce that number, so the two axes stay disjoint.
    return frozenset(value for value in over if len(set(_unpack(value))) > 1), len(values)


def filler_colours(decoded: dict[int, np.ndarray]) -> frozenset[int]:
    """Packed colours an atlas repeats often enough to be fill, not photography.

    ⚠️ **The rejection this feeds is per texel, never per atlas.** Four of the
    atlases `Q55` found are 4096-square photographs of real buildings that happen
    to carry an embedded panel — 33,981 to 82,565 distinct colours apiece — so
    dropping the atlas would discard the building. The distinct-colour count does
    separate the two populations cleanly (every duplicated panel is <= 122, every
    photograph >= 33,981) and `--filler-report` prints it, but it is a diagnostic
    and deliberately not the guard.
    """
    found: set[int] = set()
    for image in decoded.values():
        found |= _atlas_filler(image)[0]
    return frozenset(found)


def is_filler(rgb: np.ndarray, colours: frozenset[int] = frozenset()) -> np.ndarray:
    """Texels that are atlas padding: an exact three-way channel tie, or one of
    the flat colours `colours` says this building's atlases repeat.

    ⚠️ **Two axes, because the defect moved between them.** The tie is `Q37`'s and
    it works — it catches every one of the 2,429 atlases whose modal colour is
    grey, 1,982 of them at `#3c3c3c`. `colours` is `Q55`'s: a panel at
    RGB(68,65,65) is `L*` 27.8 and no channel tie, so the tie cannot see it and
    neither can any percentile-based cut, because it wins by mass on walls it
    covers 44-96% of.

    ⚠️ **Empty by default, which is exactly `Q37`'s guard.** `facade_glazing.py`
    calls `photographic` with two arguments and is deliberately left on the tie
    alone: `Q55` measured no damage on its table, and its untextured-canvas
    rejection depends on exact black staying filler either way.
    """
    tie = (rgb[:, 0] == rgb[:, 1]) & (rgb[:, 1] == rgb[:, 2])
    if not colours:
        return tie
    return tie | _repeats(rgb, colours)


def photographic(
    rgb: np.ndarray, lab: np.ndarray, colours: frozenset[int] = frozenset()
) -> np.ndarray:
    """Texels that are neither atlas padding nor canopy — the ones worth reading.

    One definition, because the estimate and the `vegetation` column that decides
    whether the pipeline trusts it must agree about what they excluded.
    """
    return ~is_filler(rgb, colours) & (lab[:, 1] >= VEGETATION_A)


def estimate(
    rgb: np.ndarray, lab: np.ndarray, colours: frozenset[int] = frozenset()
) -> tuple[np.ndarray, np.ndarray] | None:
    """`(lab, lit_rgb)` for one set of texels, or `None` if none survive the guards.

    Takes the `L*a*b*` alongside the texels rather than deriving it, so a caller
    measuring a building and its four faces converts once instead of five times.

    ⚠️ **`None` is a refusal to answer, and the caller must keep it one.** The
    shipped table's failure was emitting a neutral grey for a building whose
    sample was entirely padding; a row that says nothing sends the building to its
    height band, which `facade_hue` already documents as the right answer for a
    measurement that did not happen.
    """
    keep = photographic(rgb, lab, colours)
    if keep.sum() < MIN_TEXELS:
        return None
    kept_lab, kept_rgb = lab[keep], rgb[keep]
    top = kept_lab[:, 0] >= np.percentile(kept_lab[:, 0], PERCENTILE)
    lit = np.rint(np.median(kept_rgb[top], axis=0))
    return srgb_to_lab(lit[None, :])[0], lit


def survey_building(meshes: list[MeshData], name: str, sheet: str) -> Row | None:
    """One building's row, or `None` when nothing measurable survives the guards."""
    # Decoded once and read twice: `filler_colours` scans these atlases for their
    # repeated panels and `wall_texels` gathers from the same ones. Passing the
    # dict through is what `decode_textures` documents it is for, so the second
    # reader pays no decode — it pays one lattice sort per atlas.
    #
    # ⚠️ **The union across a building's atlases, because a texel's atlas is not
    # recoverable later** — `wall_texels` pools by compass face and drops it. An
    # exact 24-bit match makes a cross-atlas false positive implausible, and
    # `Q55`'s own sweep attributed damage per building the same way.
    #
    # Taken before the gather rather than after: the sort's transients are then
    # done with before `wall_texels` reaches its peak, which is where this tool's
    # ceiling actually is.
    decoded = decode_textures(meshes)
    colours = filler_colours(decoded)
    faces = wall_texels(meshes, decoded)
    del decoded
    if not faces:
        return None
    total = sum(len(pixels) for pixels in faces.values())
    sampled = _subsample(faces, name)
    del faces

    # One conversion for the building and its four faces: the faces partition the
    # pooled sample, so each is a slice of it rather than a separate measurement.
    bounds = np.cumsum([0, *(len(pixels) for pixels in sampled.values())])
    pooled = np.concatenate(list(sampled.values()))
    pooled_lab = srgb_to_lab(pooled)

    result = estimate(pooled, pooled_lab, colours)
    if result is None:
        log.warning("%s: every wall texel is filler or canopy — no row emitted", name)
        return None
    lab, lit = result

    face_lightness: dict[str, float | None] = dict.fromkeys(FACES)
    for index, face in enumerate(sampled):
        low, high = bounds[index], bounds[index + 1]
        per_face = estimate(pooled[low:high], pooled_lab[low:high], colours)
        if per_face is not None:
            face_lightness[face] = round(float(per_face[0][0]), 2)

    keep = photographic(pooled, pooled_lab, colours)
    floor = min(float(mesh.positions[:, 1].min()) for mesh in meshes)
    roof = max(float(mesh.positions[:, 1].max()) for mesh in meshes)
    return Row(
        lab=[round(float(value), 2) for value in lab],
        lit_rgb=[int(value) for value in lit],
        naive_rgb=[int(value) for value in np.rint(pooled[keep].mean(axis=0))],
        face_L=face_lightness,
        pixels=total,
        clipped=round(float((pooled >= CLIP_LEVEL).any(axis=1).mean()), 4),
        vegetation=round(float((pooled_lab[:, 1] < VEGETATION_A).mean()), 4),
        height_m=round(roof - floor, 2),
        sheet=sheet,
    )


@dataclass(frozen=True)
class FillerFinding:
    """One building's correction, attributed to one panel it carries.

    ⚠️ **Per building-slot, so a building carrying two panels appears twice.**
    `Q55` reports it the same way and says so: its column sums to 45 against 43
    unique buildings.
    """

    stem: str
    sheet: str
    colour: int
    atlas_bytes: int
    atlas_colours: int
    wall_share: float
    delta_ab: float
    delta_L: float
    refused: bool


def filler_findings(meshes: list[MeshData], name: str, sheet: str) -> list[FillerFinding]:
    """What the colour guard changes about one building, per panel it carries.

    Measured exactly the way `survey_building` measures — same gather, same seeded
    subsample, same estimator — so these deltas describe the table that ships
    rather than a second, differently-sampled reading of it.
    """
    decoded = decode_textures(meshes)
    # Keyed the way `decode_textures` keys, so one atlas is visited once without a
    # second dedupe beside the one whose soundness that function argues for.
    sizes = {
        id(mesh.texture): len(mesh.texture.data)
        for mesh in meshes
        if mesh.texture is not None and mesh.uvs is not None
    }
    detail: dict[int, tuple[int, int]] = {}
    for key, image in decoded.items():
        colours, distinct = _atlas_filler(image)
        for colour in colours:
            # ⚠️ One colour can sit on a duplicated panel in one atlas and inside
            # a photograph in another, so keep the **largest** palette it was seen
            # in — the diagnostic then never understates how photographic its host
            # might be, which is the direction that would mislead. Bytes and
            # palette move together, or the pair would describe no single file.
            if distinct > detail.get(colour, (0, -1))[1]:
                detail[colour] = (sizes[key], distinct)
    if not detail:
        return []

    faces = wall_texels(meshes, decoded)
    del decoded
    if not faces:
        return []
    pooled = np.concatenate(list(_subsample(faces, name).values()))
    del faces
    pooled_lab = srgb_to_lab(pooled)

    colours = frozenset(detail)
    before = estimate(pooled, pooled_lab)
    if before is None:
        # Already unmeasurable before the colour axis — all canopy, or all grey
        # tie. There is no delta to attribute, so it is not a `Q55` finding; it
        # was not in that record's 93 either.
        return []
    after = estimate(pooled, pooled_lab, colours)
    share = float(_repeats(pooled, colours).mean())

    # ⚠️ **Refusal is the severe outcome, not a missing measurement.** A building
    # whose walls were mostly panel can fall under `MIN_TEXELS` once the panel is
    # rejected, and then it emits no row at all and falls back to its height band.
    # `refused` carries that; the deltas are zero rather than a sentinel, so no
    # reader has to know a NaN convention to filter them.
    delta_ab = delta_L = 0.0
    if after is not None:
        delta_ab = float(np.hypot(after[0][1] - before[0][1], after[0][2] - before[0][2]))
        delta_L = float(after[0][0] - before[0][0])
    return [
        FillerFinding(
            stem=stem(name),
            sheet=sheet,
            colour=colour,
            atlas_bytes=detail[colour][0],
            atlas_colours=detail[colour][1],
            wall_share=share,
            delta_ab=delta_ab,
            delta_L=delta_L,
            refused=after is None,
        )
        for colour in sorted(colours)
    ]


def filler_sheet(archive: Path) -> list[FillerFinding]:
    """Every repeated panel on one sheet, and what rejecting it moves."""
    sheet = archive.stem
    findings: list[FillerFinding] = []
    with zipfile.ZipFile(archive) as bundle:
        documents = sheet_documents(bundle)
        log.info("%s: %d %s-prefixed models", sheet, len(documents), MODEL_PREFIX)
        for index, (name, document) in enumerate(sorted(documents.items()), 1):
            found = filler_findings(load_building(bundle, document), name, sheet)
            if found:
                # Every row of one building repeats its building-level columns, so
                # any of them reports the building.
                building = found[0]
                log.info(
                    "  [%d/%d] %s %d panel(s), %.1f%% of walls, dL* %+.2f",
                    index,
                    len(documents),
                    name,
                    len(found),
                    100.0 * building.wall_share,
                    building.delta_L,
                )
            findings.extend(found)
    return findings


def filler_report(findings: list[FillerFinding]) -> None:
    """`Q55`'s tables, from the guard that ships rather than from a scratch script.

    ⚠️ **Grades rather than checks, and returns nothing to exit on.** There is no
    bar here: a panel found is a correction to make, not a threshold to retune
    against, and the only wrong answer would be a number nobody can reproduce.
    """
    if not findings:
        log.info("\n  no atlas repeats a colour past the bar — nothing to correct\n")
        return

    # ⚠️ Keyed by sheet as well as stem. `claim_stems` refuses a stem published on
    # two sheets, but this tool runs before that refusal and must not quietly
    # collapse two buildings into one while counting how many were damaged.
    by_building: dict[tuple[str, str], FillerFinding] = {}
    for finding in findings:
        by_building.setdefault((finding.sheet, finding.stem), finding)
    per_colour: dict[int, list[FillerFinding]] = defaultdict(list)
    for finding in findings:
        per_colour[finding.colour].append(finding)

    past_column = f"past {DAMAGE_AB}"
    lines = [
        f"\n  {len(by_building)} buildings carry a repeated panel, "
        f"on {len(findings)} atlas slots"
        f"  (bar: one colour at >= {MODAL_SHARE:.0%} of an atlas)\n",
        f"  {'placeholder':<18}{'bytes':>10}{'distinct':>10}{'copies':>8}"
        f"{past_column:>12}{'worst |dL*|':>13}",
    ]
    for colour, rows in sorted(per_colour.items(), key=lambda item: -len(item[1])):
        damaged = sum(1 for f in rows if f.delta_ab > DAMAGE_AB)
        moved = [abs(f.delta_L) for f in rows if not f.refused]
        # ⚠️ Blank rather than 0.00 where every carrier was refused: refusal is the
        # *worst* outcome — the building emits no row at all — and a zero here
        # would print the most damaging placeholder as the most harmless one.
        worst = f"{max(moved):.2f}" if moved else "n/a"
        # The most photographic host this colour was seen in, for the reason
        # `filler_findings` gives — taking `rows[0]` would report whichever
        # building happened to sort first.
        host = max(rows, key=lambda f: f.atlas_colours)
        share = f"{damaged}/{len(rows)}"
        lines.append(
            f"  {_unpack(colour)!s:<18}{host.atlas_bytes:>10}{host.atlas_colours:>10}"
            f"{len(rows):>8}{share:>12}{worst:>13}"
        )

    shares = np.array([f.wall_share for f in by_building.values()])
    measured = [f for f in by_building.values() if not f.refused]
    deltas = np.array([f.delta_L for f in measured])
    abs_ab = np.array([f.delta_ab for f in measured])
    refused = sorted(f.stem for f in by_building.values() if f.refused)

    lines.append(
        f"\n  wall-texel filler share   p50 {100 * np.percentile(shares, 50):.2f}%"
        f"  p75 {100 * np.percentile(shares, 75):.1f}%"
        f"  p90 {100 * np.percentile(shares, 90):.1f}%"
        f"  max {100 * shares.max():.1f}%"
    )
    # Guarded because every carrier being refused is a real outcome, and a report
    # that dies on a numpy empty-slice is a report that loses the finding.
    if len(deltas):
        lines.append(
            f"  dL* both ways             {int((deltas > 0).sum())} up, "
            f"{int((deltas < 0).sum())} down, median {np.median(deltas):+.2f}, "
            f"worst {deltas.max():+.2f} / {deltas.min():+.2f}"
        )
        lines.append(
            f"  past Q33's {DAMAGE_AB} dEab      {int((abs_ab > DAMAGE_AB).sum())} of "
            f"{len(abs_ab)} buildings, {int((abs_ab > 2.0).sum())} past 2.0, "
            f"{int((abs_ab > 5.0).sum())} past 5.0"
        )
    if refused:
        lines.append(
            f"  ⚠️ refused after the guard  {len(refused)} building(s) fall under "
            f"MIN_TEXELS and emit no row, e.g. {refused[0]}"
        )
    lines.append(
        "\n  ⚠️ Counts are by building-slot: a building carrying two panels appears\n"
        "     under each. ⚠️ Every figure is a lower bound — detection needs one\n"
        f"     exact colour at >= {MODAL_SHARE:.0%} of an atlas, on a "
        f"1-in-{MODAL_STRIDE**2} lattice.\n"
    )
    # One block, because `filler_sheet` logs progress and interleaved `print`s
    # would tear against it on a terminal.
    log.info("\n".join(lines))


def survey_sheet(archive: Path) -> dict[str, dict[str, Any]]:
    """Every building on one sheet, keyed by the stem `pipeline/buildings.py` joins on.

    ⚠️ **Keyed through the pipeline's own `stem`, not a local copy of it.** The two
    datasets join on this key and nothing checks that they agree — a survey keyed
    even one character differently produces no error, just a city coloured
    entirely from height bands.
    """
    sheet = archive.stem
    rows: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(archive) as bundle:
        documents = sheet_documents(bundle)
        log.info("%s: %d %s-prefixed models", sheet, len(documents), MODEL_PREFIX)
        for index, (name, document) in enumerate(sorted(documents.items()), 1):
            row = survey_building(load_building(bundle, document), name, sheet)
            if row is None:
                continue
            rows[stem(name)] = asdict(row)
            log.info("  [%d/%d] %s lab=%s", index, len(documents), name, row.lab)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheets", nargs="*", help="sheet ids, e.g. 11-SW-9D")
    parser.add_argument("--city", default="hong_kong")
    parser.add_argument(
        "--zip-dir",
        type=Path,
        default=INDIVIDUALISED_DIR,
        help="where the individualised sheet archives live",
    )
    # Resolved after parsing rather than as a default, because it depends on
    # --city. `source_dir` is the only thing that knows this tree's shape.
    parser.add_argument(
        "--out-dir", type=Path, help="where to write facade_lab.<sheet>.json [the city's cache]"
    )
    parser.add_argument("--all", action="store_true", help="every archive in --zip-dir")
    parser.add_argument(
        "--merge", action="store_true", help="also write the merged facade_lab.json"
    )
    parser.add_argument(
        "--filler-report",
        action="store_true",
        help="measure the repeated panels instead of writing a table (Q55)",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    out_dir = arguments.out_dir or source_dir(arguments.city, HUE_SOURCE_ID)
    archives = (
        sorted(arguments.zip_dir.glob("*.zip"))
        if arguments.all
        else [arguments.zip_dir / f"{sheet}.zip" for sheet in arguments.sheets]
    )
    if not archives:
        parser.error("name at least one sheet, or pass --all")

    # Measures rather than writes: nothing downstream should be re-published as a
    # side effect of asking how much the guard is worth. Refused rather than
    # ignored, so that is visible at the command line and not only here.
    if arguments.filler_report and (arguments.merge or arguments.out_dir):
        parser.error("--filler-report writes no table, so --merge and --out-dir do nothing")
    if arguments.filler_report:
        findings: list[FillerFinding] = []
        for archive in archives:
            findings.extend(filler_sheet(archive))
        filler_report(findings)
        return 0

    def write(name: str, rows: dict[str, dict[str, Any]], label: str) -> None:
        destination = out_dir / name
        destination.write_text(json.dumps(rows, indent=1, sort_keys=True))
        log.info("%s: %d rows -> %s", label, len(rows), destination)

    out_dir.mkdir(parents=True, exist_ok=True)
    merged: dict[str, dict[str, Any]] = {}
    for archive in archives:
        rows = survey_sheet(archive)
        write(f"{TABLE_STEM}.{archive.stem}.json", rows, archive.stem)
        clash = merged.keys() & rows.keys()
        if clash:
            raise ValueError(
                f"{archive.stem}: {len(clash)} stems already surveyed, e.g. {min(clash)}"
            )
        merged.update(rows)

    if arguments.merge:
        write(f"{TABLE_STEM}.json", merged, "merged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
