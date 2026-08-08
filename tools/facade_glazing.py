"""The glazing survey (`Q40`) — dip and glass tint from the decontaminated selection.

`Q40`'s Probe 1 measured glazed-vs-blank as a bimodality dip in each building's
wall-texel `L*` population — and its wall selection was `wall_texels()`'s
per-mesh, per-normal test, which `Q40` later showed admits foreign geometry:
trees, a hillside, an entire neighbouring building. Non-building content adds a
second mode, so contamination biases the dip toward *bimodal* — the direction
that flatters the result. `Q41` retired that hazard for the reader's images
with `facade_unwrap.py`'s depth buffer, and records the histogram half as still
owed. This tool is that check, committed rather than run once and lost —
Probe 1 itself was never committed, which is `Q37`'s ghost, and this table is
the one the eventual glazing gate will be trusted against.

For every building on a sheet it computes the dip twice, from the two texel
selections, and reports where the verdict moves:

- **atlas**: `wall_texels()` — every texel of every triangle whose normal
  faces a compass direction, occluded or not. Probe 1's population.
- **unwrap**: the pooled `facade_unwrap.py` elevations — per canvas cell, only
  the texel whose surface lies outermost along the face normal survives.

⚠️ **The two populations differ by more than occlusion, deliberately.** The
unwrap re-grids texels at 8/m, so its histogram is area-weighted where the
atlas one is texel-count-weighted; a well-photographed balcony no longer
outvotes the wall behind it by sheer resolution. Both differences move the
measurement toward the façade as built, which is what the gate is for — the
comparison quantifies how far the recorded Probe 1 numbers sit from a
selection a gate could trust, not which single cause moved each building.

⚠️ **Texture-baked occluders survive in both populations.** A tree photographed
in front of a wall is in the wall's texels; no geometric filter can remove it.
The unwrap retires geometry contamination only.

The same walk is also the survey the contamination check gated: per building it
writes `facade_glazing.<sheet>.json` — the unwrap dip, the dark mode's
`(L*, b*)` tint, and the resolution gate's density — keyed by the stem
`pipeline/buildings.py` joins on, beside `facade_survey.py`'s colour table.
⚠️ **The table records measurements, never verdicts.** The dip boundaries are
pinned here so that re-deriving them is an edit to this file and a re-emit of
nothing — a consumer classifies from the dip at read time, and a stale-verdict
table cannot exist.

Run:  .venv/bin/python tools/facade_glazing.py 11-SW-9D
      .venv/bin/python tools/facade_glazing.py --all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import zipfile
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(ROOT / "tools"))

from facade_survey import (  # noqa: E402
    INDIVIDUALISED_DIR,
    SAMPLE_CAP,
    assigned_faces,
    decode_textures,
    load_building,
    photographic,
    sheet_documents,
    wall_texels,
)
from facade_unwrap import unwrap_building  # noqa: E402
from pipeline.buildings import HUE_SOURCE_ID, stem  # noqa: E402
from pipeline.colour import srgb_to_lab  # noqa: E402
from pipeline.fetch import source_dir  # noqa: E402
from pipeline.gltf import MeshData, triangle_cross  # noqa: E402

log = logging.getLogger(__name__)

# `L*` histogram bins over [0, 100]: 2 `L*` per bin, wide enough that sensor
# noise does not carve false valleys, narrow enough that a spandrel-vs-glass
# split (typically > 10 `L*` apart) spans several bins.
BINS = 50

# Probe 1's verdict boundaries, kept so its recorded 50%/23% split is the
# number this tool's atlas column is compared against.
BIMODAL_BELOW = 0.25
UNIMODAL_ABOVE = 0.60

# Verdict names in one place: the classifier and the summary tally must agree
# on membership and order, or the summary miscounts silently.
KINDS = ("bimodal", "middling", "unimodal")

# Probe 1's resolution gate: below ~10 photographic texels per linear metre,
# "no windows" and "badly photographed" are the same reading.
MIN_TEX_PER_M = 10.0

# Below this many photographic texels a population has no histogram worth
# splitting — same spirit as `facade_survey.MIN_TEXELS`, scaled to a
# distribution rather than a median.
MIN_POPULATION = 1024

# The survey table's filename stem; per sheet it takes the sheet id as an
# infix, exactly as `facade_survey.TABLE_STEM` does for the colour table it
# sits beside.
TABLE_STEM = "facade_glazing"

# What of a check row the survey table keeps: the decontaminated measurements
# a consumer classifies from, and the gate's density. The atlas columns stay
# out deliberately — they are the contamination comparison, not the survey.
TABLE_COLUMNS = ("tex_per_m", "dark_share", "dark_L", "dark_b", "light_L", "light_b")


@dataclass(frozen=True)
class Verdict:
    """One population's bimodality reading."""

    dip: float
    kind: str  # one of KINDS


def otsu_bin(hist: np.ndarray) -> int:
    """The bin index whose split maximises between-class variance."""
    total = hist.sum()
    bins = np.arange(len(hist))
    weight_lo = np.cumsum(hist)
    mass_lo = np.cumsum(hist * bins)
    weight_hi = total - weight_lo
    mean_lo = np.divide(mass_lo, weight_lo, out=np.zeros_like(mass_lo, float), where=weight_lo > 0)
    mean_hi = np.divide(
        mass_lo[-1] - mass_lo, weight_hi, out=np.zeros_like(mass_lo, float), where=weight_hi > 0
    )
    variance = weight_lo * weight_hi * (mean_lo - mean_hi) ** 2
    return int(np.argmax(variance))


def smoothed_split(lstar: np.ndarray) -> tuple[np.ndarray, int, float]:
    """`(smoothed histogram, Otsu bin, boundary L*)` — the one histogram both
    measurements read. The dip and the dark-mode tint must agree about where
    the boundary between the modes falls, or a building could be bimodal by
    one reading and tinted from the wrong population by the other. The
    boundary is the histogram's own bin edge, not arithmetic re-derived at a
    call site."""
    hist, edges = np.histogram(lstar, bins=BINS, range=(0.0, 100.0))
    smooth = np.convolve(hist.astype(float), np.ones(3) / 3.0, mode="same")
    split = otsu_bin(smooth)
    return smooth, split, float(edges[split + 1])


def dip_statistic(lstar: np.ndarray) -> float:
    """Valley depth between the two `L*` modes: 0 = clean bimodal, 1 = no dip.

    Otsu's split places the boundary; the statistic is the smoothed histogram's
    minimum between the two modes' peaks, as a fraction of the lower peak.
    Otsu splits a unimodal blob just as happily (`Q40`: `eta` never goes low),
    which is exactly why the dip and not the split quality is the statistic.
    """
    smooth, split, _ = smoothed_split(lstar)
    below, above = smooth[: split + 1], smooth[split + 1 :]
    if not len(above) or below.max() == 0 or above.max() == 0:
        return 1.0
    peak_lo = int(np.argmax(below))
    peak_hi = split + 1 + int(np.argmax(above))
    valley = smooth[peak_lo : peak_hi + 1].min()
    # Both peaks are their side's max and both sides are non-zero here, so the
    # shorter peak is provably positive.
    return float(valley / min(smooth[peak_lo], smooth[peak_hi]))


def verdict(lstar: np.ndarray) -> Verdict:
    # Classified after rounding, so the recorded dip is the number the verdict
    # was made from — a table entry of 0.250 must not read "bimodal".
    dip = round(dip_statistic(lstar), 3)
    if dip < BIMODAL_BELOW:
        kind = "bimodal"
    elif dip > UNIMODAL_ABOVE:
        kind = "unimodal"
    else:
        kind = "middling"
    return Verdict(dip=dip, kind=kind)


def mode_tint(lab: np.ndarray) -> dict[str, float]:
    """Median `(L*, b*)` of each `L*` mode, split where the dip was measured.

    The boundary is `smoothed_split`'s — the same histogram and the same Otsu
    bin the dip reads — so the population this calls "dark" is exactly the one
    the dip called a mode. `Q40`: on a glazed building the dark mode is the
    glass, and tint is 2-D `L*` x `b*` because `a*` carries 6.5% of the
    variance; `a*` is dropped here for that recorded reason.

    ⚠️ **Recorded unconditionally, meaningful conditionally.** On a building the
    dip reads unimodal, the "dark mode" is the shaded half of one material and
    says nothing about glass — the consumer gates on the dip first. Emitting it
    anyway is what keeps this table measurements-only.
    """
    _, _, boundary = smoothed_split(lab[:, 0])
    # Strict `<`: histogram bins are half-open, so a texel exactly at the
    # boundary was counted in the light mode's bin — the split here must put
    # it in the same mode the dip's histogram did.
    dark = lab[lab[:, 0] < boundary]
    light = lab[lab[:, 0] >= boundary]
    tint: dict[str, float] = {"dark_share": round(len(dark) / len(lab), 3)}
    for name, mode in (("dark", dark), ("light", light)):
        if len(mode):
            tint[f"{name}_L"] = round(float(np.median(mode[:, 0])), 2)
            tint[f"{name}_b"] = round(float(np.median(mode[:, 2])), 2)
    return tint


def photographic_lab(rgb: np.ndarray, seed: str) -> tuple[np.ndarray, int]:
    """`(lab, sampled)`: photographic texels' `L*a*b*`, and how many texels the
    photographic cut was applied to — the denominator a caller estimating a
    photographic share must use, rather than re-deriving the sampling rule.

    The dip is a property of the distribution, so a seeded uniform subsample
    under `SAMPLE_CAP` is unbiased — the same argument `facade_survey` records
    for its order statistic, with its own personalisation so the two tools'
    draws never correlate.
    """
    if len(rgb) > SAMPLE_CAP:
        digest = blake2b(seed.encode("utf-8"), digest_size=8, person=b"glazing")
        rng = np.random.default_rng(int.from_bytes(digest.digest(), "big"))
        rgb = rgb[rng.choice(len(rgb), SAMPLE_CAP, replace=False)]
    lab = srgb_to_lab(rgb)
    return lab[photographic(rgb, lab)], len(rgb)


def wall_area_m2(meshes: list[MeshData]) -> float:
    """Area of the wall triangles `wall_texels` reads, in square metres.

    Skips untextured meshes for the same reason `wall_texels` does: this is
    the denominator of a texel density, and a wall that contributes no texels
    to the numerator must not deflate it.
    """
    area = 0.0
    for mesh in meshes:
        if mesh.texture is None or mesh.uvs is None:
            continue
        walls = mesh.triangles[assigned_faces(mesh) >= 0]
        cross = triangle_cross(mesh.positions, walls)
        area += float(np.linalg.norm(cross, axis=1).sum()) / 2.0
    return area


def check_sheet(archive: Path) -> list[dict]:
    """Both verdicts for every measurable building on one sheet."""
    rows: list[dict] = []
    with zipfile.ZipFile(archive) as bundle:
        documents = sheet_documents(bundle)
        for index, (name, document) in enumerate(sorted(documents.items()), 1):
            meshes = load_building(bundle, document)
            decoded = decode_textures(meshes)
            faces = wall_texels(meshes, decoded)
            if not faces:
                continue
            atlas_rgb = np.concatenate(list(faces.values()))
            total_texels = len(atlas_rgb)
            del faces
            # The atlas gather is measured and freed before the unwrap runs, so
            # the region's 270 MB worst case is never resident beside canvases
            # and depth buffers — only the capped sample survives.
            atlas_lab, atlas_sampled = photographic_lab(atlas_rgb, name)
            del atlas_rgb
            # Only `L*` is ever read on the atlas side, and the full Lab
            # array would otherwise sit resident across the unwrap — the
            # loop's memory peak.
            atlas_lstar = atlas_lab[:, 0].copy()
            del atlas_lab

            elevations = unwrap_building(meshes, decoded=decoded)
            del decoded
            # Untextured canvas cells are exact black, which `photographic`
            # rejects as filler — but only after they were counted against
            # `SAMPLE_CAP`, so a low-coverage building's sample would be mostly
            # nothing. Dropped here instead: the cap applies to covered texels.
            covered = [
                flat[flat.any(axis=1)]
                for elevation in elevations.values()
                for flat in (elevation.canvas.reshape(-1, 3),)
            ]
            del elevations
            unwrap_rgb = np.concatenate(covered) if covered else np.empty((0, 3), dtype=np.uint8)
            del covered
            unwrap_lab, _ = photographic_lab(unwrap_rgb, name)
            del unwrap_rgb

            if len(atlas_lstar) < MIN_POPULATION or len(unwrap_lab) < MIN_POPULATION:
                log.info(
                    "[%d/%d] %s: too few photographic texels — skipped",
                    index,
                    len(documents),
                    name,
                )
                continue

            # Density estimated from the sample's photographic share, scaled to
            # the full gather — converting every texel of a 90-million-texel
            # building to `L*` would cost more than the answer is worth.
            share = len(atlas_lstar) / atlas_sampled
            area = wall_area_m2(meshes)
            tex_per_m = float(np.sqrt(total_texels * share / area)) if area > 0 else 0.0

            atlas, unwrap = verdict(atlas_lstar), verdict(unwrap_lab[:, 0])
            rows.append(
                {
                    "building": name,
                    "tex_per_m": round(tex_per_m, 1),
                    "atlas_dip": atlas.dip,
                    "atlas_kind": atlas.kind,
                    "unwrap_dip": unwrap.dip,
                    "unwrap_kind": unwrap.kind,
                    **mode_tint(unwrap_lab),
                }
            )
            log.info(
                "[%d/%d] %s: %5.1f tex/m  atlas %.3f %-8s  unwrap %.3f %-8s%s",
                index,
                len(documents),
                name,
                tex_per_m,
                atlas.dip,
                atlas.kind,
                unwrap.dip,
                unwrap.kind,
                "  MOVED" if atlas.kind != unwrap.kind else "",
            )
    return rows


def summarise(rows: list[dict]) -> None:
    """The comparison the `Q40` record is owed, over the gated population."""

    gated = [row for row in rows if row["tex_per_m"] >= MIN_TEX_PER_M]

    def tally(column: str) -> str:
        kinds = [row[column] for row in gated]
        return "/".join(str(kinds.count(kind)) for kind in KINDS)

    moved = [row for row in gated if row["atlas_kind"] != row["unwrap_kind"]]
    toward_unimodal = [row for row in moved if row["unwrap_dip"] > row["atlas_dip"]]
    log.info("")
    log.info("%d buildings measured, %d at >= %.0f tex/m", len(rows), len(gated), MIN_TEX_PER_M)
    log.info(
        "gated bimodal/middling/unimodal  atlas %s  unwrap %s",
        tally("atlas_kind"),
        tally("unwrap_kind"),
    )
    log.info(
        "gated median dip  atlas %.3f  unwrap %.3f",
        float(np.median([row["atlas_dip"] for row in gated])) if gated else float("nan"),
        float(np.median([row["unwrap_dip"] for row in gated])) if gated else float("nan"),
    )
    log.info(
        "verdicts moved on %d of %d gated buildings (%d toward unimodal):",
        len(moved),
        len(gated),
        len(toward_unimodal),
    )
    for row in moved:
        log.info(
            "  %s: atlas %.3f %s -> unwrap %.3f %s",
            row["building"],
            row["atlas_dip"],
            row["atlas_kind"],
            row["unwrap_dip"],
            row["unwrap_kind"],
        )


def survey_rows(rows: list[dict], sheet: str) -> dict[str, dict[str, Any]]:
    """A sheet's check rows as the survey table, keyed by the stem
    `pipeline/buildings.py` joins on — the same key warning `facade_survey`
    records: a table keyed one character differently is not an error, just a
    consumer that never matches anything.

    The unwrap dip is written as `dip`, unqualified, because the table carries
    only the decontaminated selection — a consumer never chooses between two.
    """
    return {
        stem(row["building"]): {
            "dip": row["unwrap_dip"],
            **{column: row[column] for column in TABLE_COLUMNS if column in row},
            "sheet": sheet,
        }
        for row in rows
    }


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
    parser.add_argument(
        "--out-dir", type=Path, help="where to write facade_glazing.<sheet>.json [the city's cache]"
    )
    parser.add_argument("--all", action="store_true", help="every archive in --zip-dir")
    parser.add_argument(
        "--merge", action="store_true", help="also write the merged facade_glazing.json"
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

    def write(name: str, table: dict[str, dict[str, Any]], label: str) -> None:
        destination = out_dir / name
        destination.write_text(json.dumps(table, indent=1, sort_keys=True))
        log.info("%s: %d rows -> %s", label, len(table), destination)

    out_dir.mkdir(parents=True, exist_ok=True)
    merged: dict[str, dict[str, Any]] = {}
    for archive in archives:
        rows = check_sheet(archive)
        summarise(rows)
        table = survey_rows(rows, archive.stem)
        write(f"{TABLE_STEM}.{archive.stem}.json", table, archive.stem)
        clash = merged.keys() & table.keys()
        if clash:
            raise ValueError(
                f"{archive.stem}: {len(clash)} stems already surveyed, e.g. {min(clash)}"
            )
        merged.update(table)

    if arguments.merge:
        write(f"{TABLE_STEM}.json", merged, "merged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
