"""`pipeline/direction_signs.py` — TD's gantry boards over the road (`P3-105`, `Q265`).

What is asserted is what a frame cannot show: that a drawing's repeated
outlines are kept once and its size label is dropped, that the fill puts ink
where TD drew a shape and field where it drew a counter, that a leg stands off
the asphalt or not at all, that a gantry moves clear of a deck over it, and
that every face is wound the way it is lit.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest
import shapely
import yaml
from PIL import Image

from pipeline.config import CONFIG_PATH
from pipeline.config_blocks.direction_signs import _direction_signs
from pipeline.direction_signs import (
    COLLIDER_NAME,
    FACE_MESH_NAME,
    FRAME_MESH_NAME,
    Hung,
    Panel,
    _clear_of_decks,
    _leg_end,
    build_meshes,
    face_image,
    pack,
    panels_of,
    parts_of,
)
from pipeline.railings import facing_away
from pipeline.trees import Faces

FIELD = (13, 71, 148)
INK = (255, 255, 255)
STEEL = (128, 128, 128)


@pytest.fixture
def spec(hong_kong):
    assert hong_kong.direction_signs is not None
    return hong_kong.direction_signs


def _ring(x0: float, y0: float, x1: float, y1: float) -> shapely.LineString:
    return shapely.LineString([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])


def _metres(spec, *values: float) -> list[float]:
    return [v * spec.drawing_units_per_m for v in values]


def test_a_repeated_outline_is_kept_once(spec):
    """TD draws every Chinese outline twice; even-odd would cancel the pair."""
    ring = _ring(*_metres(spec, 0, 0, 1, 1))
    reversed_ring = shapely.LineString(list(ring.coords)[::-1])
    parts, duplicates = parts_of(shapely.MultiLineString([ring, reversed_ring, ring]))
    assert len(parts) == 1
    assert duplicates == 2


def test_the_size_label_is_dropped_and_a_separate_plate_is_its_own_panel(spec):
    board = _ring(*_metres(spec, 0, 0, 6, 2))
    plate = _ring(*_metres(spec, 0, 2.5, 2, 3.5))
    letter = _ring(*_metres(spec, 1, 0.5, 1.4, 1.2))
    label = _ring(*_metres(spec, 0, -1.0, 0.1, -0.9))
    panels, labels = panels_of([board, plate, letter, label], spec)
    assert labels == 1
    assert len(panels) == 2
    big = max(panels, key=lambda p: p.outline.area)
    assert letter in big.closed


def test_ink_where_a_shape_is_drawn_and_field_round_it(spec):
    """Closed outlines (the Chinese) fill with ink; the panel itself is field."""
    frame = _ring(*_metres(spec, 0, 0, 4, 2))
    glyph = _ring(*_metres(spec, 1.5, 0.5, 2.5, 1.5))
    panel = Panel(outline=shapely.Polygon(frame.coords), closed=(glyph,), opened=(frame,))
    image, _ = face_image(panel, spec, FIELD, INK)
    pixels = np.asarray(image)
    w, h = image.size
    assert tuple(pixels[h // 2, w // 2]) == INK
    assert tuple(pixels[h // 2, w // 8]) == FIELD


def test_a_letter_counter_is_stroked_not_filled(spec):
    """An `o` drawn as a small closed face of open strokes keeps its hole."""
    frame = _ring(*_metres(spec, 0, 0, 4, 2))
    side = (spec.counter_max_m2 / 4) ** 0.5
    o = shapely.LineString(_ring(*_metres(spec, 2, 1, 2 + side, 1 + side)).coords)
    o_open = shapely.MultiLineString([list(o.coords)[:3], list(o.coords)[2:]]).geoms
    panel = Panel(outline=shapely.Polygon(frame.coords), closed=(), opened=(frame, *o_open))
    _, counters = face_image(panel, spec, FIELD, INK)
    assert counters == 1


def test_the_atlas_is_power_of_two_and_cells_do_not_overlap():
    images = [Image.new("RGB", (300, 80), FIELD), Image.new("RGB", (120, 60), INK)]
    atlas = pack(images, pad=2)
    assert atlas.width & (atlas.width - 1) == 0
    assert atlas.height & (atlas.height - 1) == 0
    boxes = [shapely.box(u0, v0, u1, v1) for u0, v0, u1, v1 in atlas.cells]
    assert all(0.0 <= c <= 1.0 for cell in atlas.cells for c in cell)
    assert boxes[0].intersection(boxes[1]).area == 0.0


def test_a_leg_stands_clear_of_the_asphalt_or_not_at_all(spec):
    road = shapely.box(-10, -10, 10, 10)
    end = np.array([9.0, 0.0])
    placed = _leg_end(end, np.array([1.0, 0.0]), road, spec)
    assert placed is not None
    point, push = placed
    assert road.distance(shapely.Point(point)) >= spec.leg_clear_m
    assert push <= spec.leg_max_push_m
    wide = shapely.box(-10, -10, 100, 10)
    assert _leg_end(end, np.array([1.0, 0.0]), wide, spec) is None


def _deck(x0: float, x1: float, z0: float, z1: float, y: float) -> Faces:
    quad = np.array([[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]])
    return Faces(np.array([quad[[0, 1, 2]], quad[[0, 2, 3]]]))


def test_a_gantry_moves_clear_of_a_deck_over_its_beam(spec):
    a, b = np.array([0.0, 0.0]), np.array([12.0, 0.0])
    along, normal = np.array([1.0, 0.0]), np.array([0.0, 1.0])
    low = spec.clearance_m + 1.5
    # A footbridge 2 m wide along the beam, its walkway inside the board's band.
    bridge = _deck(-5, 17, -1.0, 1.0, low)
    shift = _clear_of_decks(a, b, along, normal, 10.0, 2.0, 0.0, bridge, spec)
    assert shift is not None and abs(shift) >= 1.0
    # Nothing over it: no move.
    clear = _deck(-5, 17, 20.0, 22.0, low)
    assert _clear_of_decks(a, b, along, normal, 10.0, 2.0, 0.0, clear, spec) == 0.0
    # A deck too wide to leave within the push is refused.
    plaza = _deck(-5, 17, -50.0, 50.0, low)
    assert _clear_of_decks(a, b, along, normal, 10.0, 2.0, 0.0, plaza, spec) is None
    # A deck high over the board's top is not in the way.
    high = _deck(-5, 17, -1.0, 1.0, spec.clearance_m + 20.0)
    assert _clear_of_decks(a, b, along, normal, 10.0, 2.0, 0.0, high, spec) == 0.0


def test_every_face_is_wound_the_way_it_is_lit(spec):
    frame = _ring(*_metres(spec, 0, 0, 4, 2))
    plate = _ring(*_metres(spec, 0.5, 2.3, 1.5, 3.0))
    panels, _ = panels_of([frame, plate], spec)
    images = [face_image(p, spec, FIELD, INK)[0] for p in panels]
    atlas = pack(images, spec.pad_px)
    for normal in (np.array([0.0, 1.0]), np.array([0.6, -0.8])):
        item = Hung(
            code="T-G1",
            panels=panels,
            images=images,
            ends=(np.array([-6.0, 0.0]), np.array([6.0, 0.0])),
            legs=(True, False),
            road_y=4.0,
            centre=np.array([0.0, 0.0]),
            normal=normal,
        )
        meshes = build_meshes(spec, [item], atlas, STEEL)
        names = {m.name for m in meshes}
        assert names == {FRAME_MESH_NAME, FACE_MESH_NAME, COLLIDER_NAME}
        assert all(facing_away(m) == 0 for m in meshes if m.material is not None)
        face = next(m for m in meshes if m.name == FACE_MESH_NAME)
        lit = np.unique(np.round(face.normals, 6), axis=0)
        assert np.allclose(lit, [[normal[0], 0.0, normal[1]]])
        # One leg's collider: the cantilevered end stands on nothing.
        collider = next(m for m in meshes if m.name == COLLIDER_NAME)
        assert collider.material is None and len(collider.triangles) == 12


def _block():
    document = yaml.safe_load(CONFIG_PATH.read_text())
    return copy.deepcopy(document["direction_signs"])


def test_the_block_refuses_a_thinned_stroke():
    body = _block()
    body["bold_m"] = -0.01
    with pytest.raises(ValueError, match="bold_m"):
        _direction_signs(body, "t")


def test_the_block_names_every_colour_role():
    body = _block()
    del body["colours"]["steel"]
    with pytest.raises(ValueError, match="steel"):
        _direction_signs(body, "t")


def test_the_block_reads_from_the_shipped_config(spec):
    assert spec.gantry_code == "-G"
    assert spec.colours == {"field": "blue", "ink": "white", "steel": "grey"}
