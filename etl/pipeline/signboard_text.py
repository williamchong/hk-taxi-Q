"""Generic shop names lettered on the signboards (`P3-103` step 2, `Q260`).

🔴 **Never a real name.** The Buildings Department's register names no shop,
and FEHD's restaurant licences, which do, are read for their position alone. A
board's name is `name_chars` picks from `prefixes` and one suffix of a trade,
seeded by the board's published id, so a rebuild letters the same street.

**Context, not a guess at the shop.** The trade is weighted by what is
published around the board: its mount (a pawnbroker's `押` hangs out over the
street, a group's name stands on the roof), a restaurant licence within
`licences.reach_m` (a food trade is boosted there and made rare elsewhere), and
the street it faces (`streets:`, authored).

**The atlas is a coverage mask, one cell a character**, rendered at build time
from the committed brush subset (`text.font`) and shipped beside
`signboards.glb` as city data. `signboards_text.gdshader` cuts each glyph out of
its quad with an alpha scissor, so one atlas serves every board whatever its
colour. `sign_text.py` kept its 0.1 m glyphs opaque (`Q63`); a board's
lettering is metres tall. ⚠️ The headless import ships this atlas, like the
signs', with no mip chain (`mipmaps/generate=false`), so a far board's glyphs
sample level 0 and the scissor can shimmer. Owed with the signs' atlas.

⚠️ **A character the font lacks letters a box.** `tools/make_fonts.py` reads the
block's characters into the subset, and `test_signboards.py` holds every one to
the font's `cmap`.
"""

from __future__ import annotations

import hashlib
import io
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely
from PIL import Image, ImageDraw, ImageFont

from pipeline.colour import reflectance
from pipeline.config import Config, GameTransform, SignText
from pipeline.config_blocks.signboards import PROJECTING
from pipeline.fetch import cached_source, read_feature_collection
from pipeline.gltf import MeshData, Texture

TEXT_MATERIAL = "signboards_text"
TEXT_MESH_NAME = "signboards_text"
TEXT_ATLAS_NAME = "signboards_text.png"
# Empty pixels round each glyph, so filtering does not bleed its neighbour in.
_PAD = 4
# The glyph's size against its cell: the brush's strokes overreach its em.
_EM_SHARE = 0.86
_UP = np.array([0.0, 1.0, 0.0])


@dataclass(frozen=True)
class Atlas:
    png: bytes
    width: int
    height: int
    # Each character's cell as (u0, v0, u1, v1), v down from the image's top.
    cells: dict[str, tuple[float, float, float, float]]

    @property
    def pixels(self) -> int:
        return self.width * self.height


def characters(text: SignText) -> list[str]:
    """Every character the block can letter, in a stable order."""
    words = [*text.prefixes, *(s for trade in text.trades.values() for s in trade.suffixes)]
    return sorted({c for word in words for c in word})


def _power_of_two(value: int) -> int:
    return 1 << max(0, math.ceil(math.log2(value)))


def _layout(count: int, cell: int) -> tuple[int, int, int]:
    """The smallest power-of-two image holding `count` cells, the squarer of
    two the same size: width, height, columns."""
    shapes = []
    width = _power_of_two(cell)
    while width <= _power_of_two(count * cell):
        columns = width // cell
        height = _power_of_two(math.ceil(count / columns) * cell)
        shapes.append((width * height, max(width, height), width, height, columns))
        width *= 2
    _, _, width, height, columns = min(shapes)
    return width, height, columns


def build_atlas(text: SignText, root: Path) -> Atlas:
    """One coverage cell a character, white on black, as a greyscale PNG."""
    chars = characters(text)
    cell = text.glyph_px + 2 * _PAD
    width, height, columns = _layout(len(chars), cell)
    font = ImageFont.truetype(str(root / text.font), size=round(text.glyph_px * _EM_SHARE))
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    cells: dict[str, tuple[float, float, float, float]] = {}
    for index, char in enumerate(chars):
        x0, y0 = (index % columns) * cell, (index // columns) * cell
        draw.text((x0 + cell / 2, y0 + cell / 2), char, font=font, fill=255, anchor="mm")
        cells[char] = (
            (x0 + _PAD) / width,
            (y0 + _PAD) / height,
            (x0 + cell - _PAD) / width,
            (y0 + cell - _PAD) / height,
        )
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return Atlas(png=out.getvalue(), width=width, height=height, cells=cells)


def read_licences(
    city: Config,
    text: SignText,
    region_id: str,
    transform: GameTransform,
    *,
    sources_root: Path | None = None,
) -> shapely.STRtree | None:
    """Every licensed restaurant's position in the region's frame, or None."""
    if text.licences is None:
        return None
    spec = text.licences
    path = cached_source(city, spec.source, root=sources_root)
    margin = spec.reach_m
    far_x, far_z = city.region_high(region_id)
    points = []
    features = read_feature_collection(path, "restaurant licences")["features"]
    parsed = 0
    for feature in features:
        properties = feature.get("properties") or {}
        try:
            easting = float(properties[spec.fields["easting"]])
            northing = float(properties[spec.fields["northing"]])
        except (KeyError, TypeError, ValueError):
            continue
        parsed += 1
        x, _, z = transform.to_game(easting, northing)
        if -margin <= x <= far_x + margin and -margin <= z <= far_z + margin:
            points.append(shapely.Point(x, z))
    if features and not parsed:
        # A `fields:` role naming no column reads every row as unpositioned,
        # and the food boost would vanish without a word.
        raise ValueError(
            f"{path}: no licence carries {spec.fields['easting']} / {spec.fields['northing']}"
        )
    return shapely.STRtree(points)


def licensed(text: SignText, licences: shapely.STRtree | None, foot: np.ndarray) -> bool:
    """Whether a restaurant licence lies within `licences.reach_m` of `foot`."""
    if licences is None or text.licences is None:
        return False
    hits = licences.query(shapely.Point(*foot), predicate="dwithin", distance=text.licences.reach_m)
    return len(hits) > 0


def pick_name(
    text: SignText, ident: str, mount: str, facing: tuple[str, ...], near_licence: bool
) -> tuple[str, str]:
    """A board's generic name and the trade it was picked from."""
    seed = int.from_bytes(hashlib.blake2b(ident.encode("utf-8"), digest_size=8).digest(), "big")
    rng = random.Random(seed)
    names, weights = [], []
    for name, trade in sorted(text.trades.items()):
        if mount not in trade.mounts:
            continue
        weight = trade.weight
        if trade.food and text.licences is not None:
            weight *= text.licences.boost if near_licence else text.licences.elsewhere
        for street in facing:
            weight *= text.streets.get(street, {}).get(name, 1.0)
        if weight > 0.0:
            names.append(name)
            weights.append(weight)
    if not names:
        return "", ""
    trade = rng.choices(names, weights)[0]
    prefix = "".join(rng.sample(text.prefixes, text.name_chars))
    return prefix + rng.choice(text.trades[trade].suffixes), trade


def ink(text: SignText, colour: tuple[int, int, int]) -> tuple[int, int, int]:
    """The ink that stands out most from the board: the WCAG contrast ratio."""
    ground = reflectance(colour) / 100.0

    def contrast(candidate: tuple[int, int, int]) -> float:
        other = reflectance(candidate) / 100.0
        return (max(ground, other) + 0.05) / (min(ground, other) + 0.05)

    return max(text.inks, key=contrast)


class QuadBuilder:
    """Upright quads with UVs and a colour each: the lettering's glyphs, one a
    character sampling its atlas cell, and the screens' faces."""

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._uvs: list[np.ndarray] = []
        self._colours: list[np.ndarray] = []

    def quad(
        self,
        centre: np.ndarray,
        right: np.ndarray,
        up: np.ndarray,
        size: tuple[float, float],
        cell: tuple[float, float, float, float],
        rgba: tuple[int, int, int, int],
    ) -> None:
        """A `size` (across, up) quad facing `right x up`, `cell` its
        (u0, v0, u1, v1) with v0 at the top."""
        half_r, half_u = right * (size[0] / 2.0), up * (size[1] / 2.0)
        # Bottom-left, bottom-right, top-right, top-left: counter-clockwise
        # seen from `right x up`, the way the glyph faces.
        self._positions.append(
            np.array(
                [
                    centre - half_r - half_u,
                    centre + half_r - half_u,
                    centre + half_r + half_u,
                    centre - half_r + half_u,
                ]
            )
        )
        u0, v0, u1, v1 = cell
        self._uvs.append(np.array([[u0, v1], [u1, v1], [u1, v0], [u0, v0]]))
        self._normals.append(np.tile(np.cross(right, up), (4, 1)))
        self._colours.append(np.tile(np.array(rgba), (4, 1)))

    def build(self, name: str, material: str, texture: Texture | None) -> MeshData | None:
        if not self._positions:
            return None
        count = 4 * len(self._positions)
        quads = np.arange(0, count, 4, dtype=np.uint32)[:, None]
        triangles = np.vstack([quads + np.array([0, 1, 2]), quads + np.array([0, 2, 3])])
        return MeshData(
            name=name,
            positions=np.vstack(self._positions).astype(np.float32),
            normals=np.vstack(self._normals).astype(np.float32),
            triangles=triangles.astype(np.uint32),
            colours=np.vstack(self._colours).astype(np.uint8),
            uvs=np.vstack(self._uvs).astype(np.float32),
            texture=texture,
            material=material,
        )


Box = tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]


def faces(board: Box, mount: str, lift_m: float) -> list[tuple[np.ndarray, np.ndarray]]:
    """The middle of the board's lit face (both faces of a blade) `lift_m` off
    it, and the face's outward normal.

    `board` is `signboards.box`: the plan centre, the plan half-axes across and
    through the face (`+through` away from the wall) and the height range.
    """
    centre, _, through, (low, high) = board
    middle = np.array([centre[0], 0.5 * (low + high), centre[1]])
    half_thick = float(np.linalg.norm(through))
    unit = np.array([through[0], 0.0, through[1]]) / half_thick
    sides = (1.0, -1.0) if mount == PROJECTING else (1.0,)
    return [(middle + unit * sign * (half_thick + lift_m), unit * sign) for sign in sides]


def letter(
    builder: QuadBuilder,
    text: SignText,
    atlas: Atlas,
    name: str,
    rgba: tuple[int, int, int, int],
    mount: str,
    board: Box,
) -> None:
    """`name` on the board's lit face, or both faces of a blade, centred."""
    _, across, _, (low, high) = board
    length = 2.0 * float(np.linalg.norm(across))
    height = high - low
    count = len(name)
    if not count or length <= 0.0 or height <= 0.0:
        return
    vertical = height > length * text.vertical_aspect
    if vertical:
        size = min(length * text.fill, height * text.fill / count)
    else:
        size = min(height * text.fill, length * text.fill / count)
    for face, out in faces(board, mount, text.lift_m):
        right = np.cross(_UP, out)
        reading = -_UP if vertical else right
        for index, char in enumerate(name):
            spot = face + reading * ((index - (count - 1) / 2.0) * size)
            builder.quad(spot, right, _UP, (size, size), atlas.cells[char], rgba)
