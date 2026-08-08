"""World-space façade unwrap (`Q41`) — per-face elevations in metres, from photo texture.

`Q40` established that atlas-space analysis is dead (median building: 0%
analysable across 5,831 shredded charts) and that re-projecting texels through
each wall triangle's position↔UV mapping into a grid whose axes are *metres
across the face* and *metres up* produces legible elevations. The probe that
proved it was never committed; this is that probe, rebuilt as a tool, because
`Q41`'s reader survey and its validation set both consume these images.

Two properties matter beyond the re-projection itself:

⚠️ **A depth buffer decides overlaps, and it is what kills `Q40`'s mode-5
contamination for geometry.** Every triangle whose normal faces a compass
direction lands in that elevation — balconies in front of walls, and in `Q40`'s
probe an entire neighbouring building. Keeping the texel whose surface lies
*outermost* along the face normal means foreign geometry behind the façade can
no longer overwrite it. Occluders baked into the *texture* (trees photographed
in front of a wall) still appear, and must — they are what the camera saw.

⚠️ **The across-axis sign is per-face, so the viewer stands outside.** Project
every face onto bare world axes and two of the four elevations mirror — CITIC
Tower's rooftop sign read "ƆITIƆ" in the first cut. Signage is one of the
survey's targets, so orientation is load-bearing, not cosmetic: the across axis
is the world axis a viewer facing the wall would call "right", which is +x for
S, -x for N, -z for E and +z for W.

Run:  .venv/bin/python tools/facade_unwrap.py 11-SW-9D B352631575201063A0
      .venv/bin/python tools/facade_unwrap.py 11-SW-9D --all
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(ROOT / "tools"))

from facade_survey import (  # noqa: E402
    FACES,
    INDIVIDUALISED_DIR,
    assigned_faces,
    load_building,
    sheet_documents,
)
from pipeline.gltf import MeshData  # noqa: E402

log = logging.getLogger(__name__)

# Photogrammetry atlases run to 8192 square; the guard protects nothing here,
# exactly as facade_survey.py already records.
Image.MAX_IMAGE_PIXELS = None

# `Q40`'s grid pitch. 8 texels/m resolves a 2.4 m bay in ~19 texels and keeps a
# 100 x 60 m face at 0.38 Mpx — smaller than the atlas it replaces.
TEXELS_PER_M = 8.0

# (across column, across sign, depth column, depth sign) per compass face. The
# across sign is the viewer-outside orientation the module docstring derives;
# depth increases outward along the face normal, which is what the buffer keys on.
AXES: dict[str, tuple[int, int, int, int]] = {
    "E": (2, -1, 0, 1),
    "W": (2, 1, 0, -1),
    "N": (0, -1, 2, -1),
    "S": (0, 1, 2, 1),
}

# A face narrower or shorter than this is a sliver — a kerb-height podium rim or
# a chamfer — and its elevation carries nothing a reader could use.
MIN_FACE_M = 2.0

# One canvas allocation cap. The region's largest wall is ~0.4 Mpx at 8 tex/m,
# so anything near this is a degenerate bounding box, not a building.
MAX_CANVAS_PX = 40_000_000


@dataclass(frozen=True)
class Elevation:
    """One face's unwrapped elevation and the numbers a gate reads."""

    canvas: np.ndarray  # (h, w, 3) uint8, row 0 at the top of the wall
    coverage: float  # fraction of the canvas any triangle textured
    width_m: float
    height_m: float


@dataclass(frozen=True)
class _Wall:
    """One textured mesh, decoded and face-assigned once for all four faces."""

    mesh: MeshData
    image: np.ndarray
    assigned: np.ndarray


def _prepare(meshes: list[MeshData]) -> list[_Wall]:
    """Decode each distinct texture once, and assign triangles to faces once.

    Both are per-building costs that the four per-face rasterisations share —
    an 8k atlas decode is the dominant unwrap cost, and paying it once per face
    quadrupled it. The decode cache is keyed on `Texture` identity because
    `read_scene` hands the same object to every primitive sharing an atlas, and
    it is scoped to one building so each building's decoded atlases are freed
    before the next one loads.
    """
    decoded: dict[int, np.ndarray] = {}
    walls = []
    for mesh in meshes:
        if mesh.texture is None or mesh.uvs is None:
            continue
        key = id(mesh.texture)
        if key not in decoded:
            decoded[key] = np.asarray(Image.open(io.BytesIO(mesh.texture.data)).convert("RGB"))
        walls.append(_Wall(mesh, decoded[key], assigned_faces(mesh)))
    return walls


def _rasterise(walls: list[_Wall], face: str) -> Elevation | None:
    """Re-project one compass face's textured wall triangles into metres.

    Returns `None` when the face has no textured wall triangles, is smaller
    than `MIN_FACE_M` either way, or would exceed `MAX_CANVAS_PX` — a refusal,
    which the caller must keep one (`Q40`: every gate refuses rather than
    guesses).
    """
    face_index = list(FACES).index(face)
    across_col, across_sign, depth_col, depth_sign = AXES[face]
    gathered: list[tuple[_Wall, np.ndarray]] = []
    lo_a = lo_u = np.inf
    hi_a = hi_u = -np.inf
    for wall in walls:
        triangles = wall.mesh.triangles[wall.assigned == face_index]
        if not len(triangles):
            continue
        used = triangles.ravel()
        across = wall.mesh.positions[used, across_col] * across_sign
        lo_a = min(lo_a, across.min())
        hi_a = max(hi_a, across.max())
        lo_u = min(lo_u, wall.mesh.positions[used, 1].min())
        hi_u = max(hi_u, wall.mesh.positions[used, 1].max())
        gathered.append((wall, triangles))
    if not gathered or hi_a - lo_a < MIN_FACE_M or hi_u - lo_u < MIN_FACE_M:
        return None
    width = int(np.ceil((hi_a - lo_a) * TEXELS_PER_M)) + 1
    height = int(np.ceil((hi_u - lo_u) * TEXELS_PER_M)) + 1
    if width * height > MAX_CANVAS_PX:
        return None
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    depth = np.full((height, width), -np.inf)

    for wall, triangles in gathered:
        image = wall.image
        image_h, image_w = image.shape[:2]
        across = (wall.mesh.positions[:, across_col] * across_sign - lo_a) * TEXELS_PER_M
        up = (wall.mesh.positions[:, 1] - lo_u) * TEXELS_PER_M
        outward = wall.mesh.positions[:, depth_col] * depth_sign
        for triangle in triangles:
            corner_a, corner_u = across[triangle], up[triangle]
            x0 = max(int(np.floor(corner_a.min())), 0)
            x1 = min(int(np.ceil(corner_a.max())) + 1, width)
            y0 = max(int(np.floor(corner_u.min())), 0)
            y1 = min(int(np.ceil(corner_u.max())) + 1, height)
            if x1 <= x0 or y1 <= y0:
                continue
            edge_a = np.array([corner_a[1] - corner_a[0], corner_u[1] - corner_u[0]])
            edge_b = np.array([corner_a[2] - corner_a[0], corner_u[2] - corner_u[0]])
            determinant = edge_a[0] * edge_b[1] - edge_a[1] * edge_b[0]
            if abs(determinant) < 1e-9:
                continue
            # The same row-against-column broadcast facade_survey.coverage uses,
            # for the same reason: one small array pair per triangle, not grids.
            offset_x = np.arange(x0, x1) - corner_a[0]
            offset_y = np.arange(y0, y1)[:, None] - corner_u[0]
            alpha = (offset_x * edge_b[1] - offset_y * edge_b[0]) / determinant
            beta = (offset_y * edge_a[0] - offset_x * edge_a[1]) / determinant
            inside = (alpha >= -1e-6) & (beta >= -1e-6) & (alpha + beta <= 1 + 1e-6)
            if not inside.any():
                continue
            gamma = 1.0 - alpha - beta
            tri_depth = gamma * outward[triangle[0]] + alpha * outward[triangle[1]]
            tri_depth += beta * outward[triangle[2]]
            uv = wall.mesh.uvs[triangle]
            tex_u = gamma * uv[0, 0] + alpha * uv[1, 0] + beta * uv[2, 0]
            tex_v = gamma * uv[0, 1] + alpha * uv[1, 1] + beta * uv[2, 1]
            window = depth[y0:y1, x0:x1]
            take = inside & (tri_depth > window)
            if not take.any():
                continue
            columns = np.clip((tex_u * image_w).astype(int), 0, image_w - 1)
            rows = np.clip((tex_v * image_h).astype(int), 0, image_h - 1)
            taken_y, taken_x = np.nonzero(take)
            source = image[rows[taken_y, taken_x], columns[taken_y, taken_x]]
            canvas[y0 + taken_y, x0 + taken_x] = source
            window[take] = tri_depth[take]

    return Elevation(
        canvas=np.flipud(canvas),
        coverage=float((depth > -np.inf).mean()),
        width_m=float(hi_a - lo_a),
        height_m=float(hi_u - lo_u),
    )


def unwrap_face(meshes: list[MeshData], face: str) -> Elevation | None:
    """One compass face's elevation, or `None` — see `_rasterise` for when."""
    return _rasterise(_prepare(meshes), face)


def unwrap_building(
    meshes: list[MeshData], faces: Iterable[str] | None = None
) -> dict[str, Elevation]:
    """The unwrappable faces of one building; refusals are absent keys.

    `faces` narrows the work to the ones a caller needs — the validation run
    reads one or two labelled faces per building, not four.
    """
    walls = _prepare(meshes)
    elevations = {}
    for face in FACES if faces is None else faces:
        elevation = _rasterise(walls, face)
        if elevation is not None:
            elevations[face] = elevation
    return elevations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheet", help="sheet id, e.g. 11-SW-9D")
    parser.add_argument("buildings", nargs="*", help="building model names")
    parser.add_argument("--all", action="store_true", help="every building on the sheet")
    parser.add_argument(
        "--zip-dir",
        type=Path,
        default=INDIVIDUALISED_DIR,
        help="where the individualised sheet archives live",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "build" / "unwrap",
        help="PNG output directory [build/unwrap/<sheet>/]",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    destination = arguments.out / arguments.sheet
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(arguments.zip_dir / f"{arguments.sheet}.zip") as bundle:
        documents = sheet_documents(bundle)
        wanted = sorted(documents) if arguments.all else arguments.buildings
        if not wanted:
            parser.error("name at least one building, or pass --all")
        for name in wanted:
            if name not in documents:
                log.warning("%s: not on sheet %s", name, arguments.sheet)
                continue
            faces = unwrap_building(load_building(bundle, documents[name]))
            for face, elevation in faces.items():
                path = destination / f"{name}_{face}.png"
                Image.fromarray(elevation.canvas).save(path)
                log.info(
                    "%s %s: %.0fx%.0f m, %.0f%% covered -> %s",
                    name,
                    face,
                    elevation.width_m,
                    elevation.height_m,
                    elevation.coverage * 100,
                    path.relative_to(ROOT),
                )
            if not faces:
                log.info("%s: no unwrappable face", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
