"""Generate the passenger's emotes: the faces that pop out of the cab (`P3-49`).

Two low-poly faces, one file each, built the way `make_vehicle.py` builds the
taxi — flat convex faces from `primitives`, vertex-coloured, no texture — so
they are ours under CC BY-SA like the rest of `assets/authored/`, and so they
sit inside the toy-car art direction rather than beside it. The bundled
typeface has no emoji glyphs and a colour-emoji font is a fifth licence and
megabytes of bitmap, which is why these are meshes and not a `Label3D`
(`Q145`).

**Which way is the face.** Each emote is a disc in the XY plane, its features
standing proud of the **-Z** face. `PassengerEmote` turns the instance with
`look_at`, which points a node's -Z at the target, so the side that is built
to be seen is the side the camera gets. `test_make_emote.py` holds every
feature on that side; a face built on +Z would render as a blank disc from
every angle and no frame check would say why.

**Not a `Q33` material.** The car's paint and the city's walls declare a
reflectance because a lighting rig scales them; an emote is a glyph in the
world, drawn unshaded like the fare guide's arrow, and its yellow is a
cartoon's, not a pigment's. The colours live here, with the geometry, for the
reason the taxi's do.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.gltf import MeshData, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import Colour, Point, loft  # noqa: E402

LOG = logging.getLogger("make_emote")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "vehicles"

# One file per face, for `make_vehicle.py`'s reason: a `.glb` imports as a
# PackedScene and is instanced whole, and `PassengerEmote` wants one face at a
# time. ⚠️ No `_wheel` / `_col` / `_occ` suffix — see `WHEEL_FILE` there.
GRIN_FILE = "emote_grin.glb"
ANGRY_FILE = "emote_angry.glb"

# The glTF material name. Absent from `generated_scene_import.gd`'s table on
# purpose: the hook's fallback turns the vertex colours on, and the rig then
# overrides the surface with an unshaded material of its own — a glyph, not a
# lit surface (`Q145`).
MATERIAL = "emote"

# RGB, 0-255, sRGB (`Q27`). A cartoon's palette: the grin is emoji yellow, the
# rage is emoji red, and the features are one dark and one white.
GRIN_YELLOW: Colour = (255, 204, 77)
ANGRY_RED: Colour = (221, 46, 68)
DARK: Colour = (49, 55, 61)
WHITE: Colour = (241, 241, 241)

# Every feature stands this far proud of the face, so it reads as a shape at
# the edge and never z-fights the disc behind it. The mouth's teeth stand one
# more step proud of the mouth.
PROUD_M = 0.012

# Sides on the disc and on an eye. Sixteen is the wheel's count: round enough
# at arm's length, flat enough to be one of this city's shapes.
DISC_SIDES = 16
EYE_SIDES = 8


@dataclass(frozen=True)
class Proportions:
    """The face's dimensions, in metres. One set for both emotes."""

    # A 0.44 m face over a 1.8 m car: a head and a half, which is what reads at
    # the chase camera's distance and does not swallow the roof.
    radius_m: float = 0.22
    # Thin, but a solid: edge-on for a frame as the billboard turns, a plane
    # would vanish and a slab would read as a coin.
    thickness_m: float = 0.04
    eye_radius_m: float = 0.035
    eye_x_m: float = 0.085
    eye_y_m: float = 0.06
    # The grin: a half-disc mouth below the eyes, with a band of teeth along
    # its top edge.
    mouth_radius_m: float = 0.13
    mouth_y_m: float = -0.02
    teeth_m: float = 0.035
    # The rage: a frown arc and two brows slanted in towards the nose.
    frown_radius_m: float = 0.10
    frown_width_m: float = 0.03
    frown_y_m: float = -0.16
    brow_half_length_m: float = 0.06
    brow_half_width_m: float = 0.014
    brow_y_m: float = 0.125
    brow_tilt_deg: float = 22.0


def _ring_xy(centre: tuple[float, float], radius: float, sides: int, z: float) -> list[Point]:
    """`sides` corners of a circle about `centre` at height `z`, anticlockwise seen from -Z.

    Anticlockwise seen from the FRONT (-Z looking at +Z) so the same order
    serves the loft's outward test and the front cap's winding, which
    `polygon_facing` settles either way.
    """
    cx, cy = centre
    angles = np.linspace(0.0, 2.0 * np.pi, sides, endpoint=False)
    return [(float(cx + radius * np.cos(a)), float(cy + radius * np.sin(a)), z) for a in angles]


def plate(
    outline: Sequence[tuple[float, float]],
    colour: Colour,
    *,
    z_front: float,
    z_back: float,
    name: str,
) -> MeshData:
    """A convex outline extruded from `z_back` to `z_front`, capped both ends.

    `loft` along Z between two copies of the outline: the sides face outward
    from the outline's centroid and the caps face -Z (front) and +Z (back).
    `z_front` must be the smaller z — the front is the -Z side, by the header.
    """
    if not z_front < z_back:
        raise ValueError(
            f"'{name}': z_front {z_front} must be in front of (less than) z_back {z_back}"
        )
    if len(outline) < 3:
        raise ValueError(f"'{name}': an outline needs at least three corners")
    front = [(x, y, z_front) for x, y in outline]
    back = [(x, y, z_back) for x, y in outline]
    return loft([front, back], [colour], bottom=colour, top=colour, axis=2, name=name)


def _disc(colour: Colour, shape: Proportions, *, name: str) -> MeshData:
    half = shape.thickness_m / 2.0
    front = _ring_xy((0.0, 0.0), shape.radius_m, DISC_SIDES, -half)
    back = _ring_xy((0.0, 0.0), shape.radius_m, DISC_SIDES, half)
    return loft([front, back], [colour], bottom=colour, top=colour, axis=2, name=name)


def _eyes(shape: Proportions, *, z_face: float, name: str) -> list[MeshData]:
    parts: list[MeshData] = []
    for side, tag in ((-1.0, "l"), (1.0, "r")):
        outline = [
            (x, y)
            for x, y, _ in _ring_xy(
                (side * shape.eye_x_m, shape.eye_y_m), shape.eye_radius_m, EYE_SIDES, 0.0
            )
        ]
        parts.append(
            plate(outline, DARK, z_front=z_face - PROUD_M, z_back=z_face, name=f"{name}_eye_{tag}")
        )
    return parts


def _half_disc(
    centre: tuple[float, float], radius: float, sides: int, *, lower: bool
) -> list[tuple[float, float]]:
    """A convex half-disc outline: the flat edge on `centre`'s y, the arc below or above it."""
    cx, cy = centre
    start, stop = (np.pi, 2.0 * np.pi) if lower else (0.0, np.pi)
    angles = np.linspace(start, stop, sides + 1)
    return [(float(cx + radius * np.cos(a)), float(cy + radius * np.sin(a))) for a in angles]


def _grin_mouth(shape: Proportions, *, z_face: float, name: str) -> list[MeshData]:
    mouth = _half_disc((0.0, shape.mouth_y_m), shape.mouth_radius_m, EYE_SIDES, lower=True)
    # The teeth: a band along the mouth's flat top edge, one step prouder than
    # the mouth so the white sits on the dark rather than in it.
    half = shape.mouth_radius_m * 0.85
    teeth = [
        (-half, shape.mouth_y_m),
        (half, shape.mouth_y_m),
        (half, shape.mouth_y_m - shape.teeth_m),
        (-half, shape.mouth_y_m - shape.teeth_m),
    ]
    return [
        plate(mouth, DARK, z_front=z_face - PROUD_M, z_back=z_face, name=f"{name}_mouth"),
        plate(
            teeth,
            WHITE,
            z_front=z_face - 2.0 * PROUD_M,
            z_back=z_face - PROUD_M,
            name=f"{name}_teeth",
        ),
    ]


def _arc_band(
    centre: tuple[float, float],
    radius: float,
    width: float,
    start_deg: float,
    stop_deg: float,
    segments: int,
    colour: Colour,
    *,
    z_front: float,
    z_back: float,
    name: str,
) -> list[MeshData]:
    """A curved band as `segments` convex quads, since a fan cannot draw an annulus."""
    cx, cy = centre
    inner = radius - width / 2.0
    outer = radius + width / 2.0
    angles = np.radians(np.linspace(start_deg, stop_deg, segments + 1))
    parts: list[MeshData] = []
    for i in range(segments):
        a0, a1 = angles[i], angles[i + 1]
        quad = [
            (float(cx + inner * np.cos(a0)), float(cy + inner * np.sin(a0))),
            (float(cx + outer * np.cos(a0)), float(cy + outer * np.sin(a0))),
            (float(cx + outer * np.cos(a1)), float(cy + outer * np.sin(a1))),
            (float(cx + inner * np.cos(a1)), float(cy + inner * np.sin(a1))),
        ]
        parts.append(plate(quad, colour, z_front=z_front, z_back=z_back, name=f"{name}_{i}"))
    return parts


def _angry_mouth(shape: Proportions, *, z_face: float, name: str) -> list[MeshData]:
    # A frown: the upper arc of a circle centred BELOW the mouth line, so the
    # corners turn down.
    return _arc_band(
        (0.0, shape.frown_y_m - shape.frown_radius_m * 0.35),
        shape.frown_radius_m,
        shape.frown_width_m,
        35.0,
        145.0,
        6,
        DARK,
        z_front=z_face - PROUD_M,
        z_back=z_face,
        name=f"{name}_frown",
    )


def _brows(shape: Proportions, *, z_face: float, name: str) -> list[MeshData]:
    """Two bars over the eyes, each tilted so its inner end is lower: anger, in two quads."""
    parts: list[MeshData] = []
    tilt = np.radians(shape.brow_tilt_deg)
    for side, tag in ((-1.0, "l"), (1.0, "r")):
        # The bar runs along `along` and is `across` thick; the inner end
        # (towards x = 0) drops by the tilt.
        along = np.array([np.cos(tilt), side * np.sin(tilt)])
        across = np.array([-along[1], along[0]])
        centre = np.array([side * shape.eye_x_m, shape.brow_y_m])
        corners = [
            centre - along * shape.brow_half_length_m - across * shape.brow_half_width_m,
            centre + along * shape.brow_half_length_m - across * shape.brow_half_width_m,
            centre + along * shape.brow_half_length_m + across * shape.brow_half_width_m,
            centre - along * shape.brow_half_length_m + across * shape.brow_half_width_m,
        ]
        parts.append(
            plate(
                [(float(x), float(y)) for x, y in corners],
                DARK,
                z_front=z_face - PROUD_M,
                z_back=z_face,
                name=f"{name}_brow_{tag}",
            )
        )
    return parts


def build_grin(shape: Proportions | None = None) -> MeshData:
    """The bonus face: yellow, two eyes, a wide grin with teeth."""
    shape = shape or Proportions()
    z_face = -shape.thickness_m / 2.0
    parts = [_disc(GRIN_YELLOW, shape, name="grin_disc")]
    parts += _eyes(shape, z_face=z_face, name="grin")
    parts += _grin_mouth(shape, z_face=z_face, name="grin")
    return replace(merge(parts, name="emote_grin"), material=MATERIAL)


def build_angry(shape: Proportions | None = None) -> MeshData:
    """The rage-quit face: red, brows down, a frown."""
    shape = shape or Proportions()
    z_face = -shape.thickness_m / 2.0
    parts = [_disc(ANGRY_RED, shape, name="angry_disc")]
    parts += _eyes(shape, z_face=z_face, name="angry")
    parts += _brows(shape, z_face=z_face, name="angry")
    parts += _angry_mouth(shape, z_face=z_face, name="angry")
    return replace(merge(parts, name="emote_angry"), material=MATERIAL)


def write_emotes(
    out_dir: Path, shape: Proportions | None = None
) -> list[tuple[Path, int, MeshData]]:
    """Write one `.glb` per face and return what went where."""
    grin = build_grin(shape)
    angry = build_angry(shape)
    grin_path = out_dir / GRIN_FILE
    angry_path = out_dir / ANGRY_FILE
    return [
        (grin_path, write_glb(grin_path, [grin]), grin),
        (angry_path, write_glb(angry_path, [angry]), angry),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output directory")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for path, size, mesh in write_emotes(args.out_dir):
        (low, high) = mesh.aabb()
        LOG.info(
            "%s — %d bytes, %d triangles, z %+.3f..%+.3f",
            path,
            size,
            mesh.triangle_count,
            low[2],
            high[2],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
