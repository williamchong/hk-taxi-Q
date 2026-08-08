"""The glazing bimodality check (`Q40`) — does occluded geometry move the dip?

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

Run:  .venv/bin/python tools/facade_glazing.py 11-SW-9D
"""

from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path

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
from pipeline.colour import srgb_to_lab  # noqa: E402
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


def dip_statistic(lstar: np.ndarray) -> float:
    """Valley depth between the two `L*` modes: 0 = clean bimodal, 1 = no dip.

    Otsu's split places the boundary; the statistic is the smoothed histogram's
    minimum between the two modes' peaks, as a fraction of the lower peak.
    Otsu splits a unimodal blob just as happily (`Q40`: `eta` never goes low),
    which is exactly why the dip and not the split quality is the statistic.
    """
    hist, _ = np.histogram(lstar, bins=BINS, range=(0.0, 100.0))
    smooth = np.convolve(hist.astype(float), np.ones(3) / 3.0, mode="same")
    split = otsu_bin(smooth)
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


def photographic_lstar(rgb: np.ndarray, seed: str) -> tuple[np.ndarray, int]:
    """`(L*, sampled)`: photographic texels' `L*`, and how many texels the
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
    return lab[photographic(rgb, lab), 0], len(rgb)


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
            atlas_lstar, atlas_sampled = photographic_lstar(atlas_rgb, name)
            del atlas_rgb

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
            unwrap_lstar, _ = photographic_lstar(unwrap_rgb, name)
            del unwrap_rgb

            if len(atlas_lstar) < MIN_POPULATION or len(unwrap_lstar) < MIN_POPULATION:
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

            atlas, unwrap = verdict(atlas_lstar), verdict(unwrap_lstar)
            rows.append(
                {
                    "building": name,
                    "tex_per_m": round(tex_per_m, 1),
                    "atlas_dip": atlas.dip,
                    "atlas_kind": atlas.kind,
                    "unwrap_dip": unwrap.dip,
                    "unwrap_kind": unwrap.kind,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheets", nargs="+", help="sheet ids, e.g. 11-SW-9D")
    parser.add_argument(
        "--zip-dir",
        type=Path,
        default=INDIVIDUALISED_DIR,
        help="where the individualised sheet archives live",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    for sheet in arguments.sheets:
        rows = check_sheet(arguments.zip_dir / f"{sheet}.zip")
        summarise(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
