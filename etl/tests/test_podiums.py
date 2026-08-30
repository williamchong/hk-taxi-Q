"""The tower↔block join (`Q47`'s second half, `P3-7a`).

The synthetic cases build `Block`s and `Footprint`s directly — the GDAL
round-trip is owned by `test_gdb.py` and the real-data test below, so what
these exercise is the logic the join adds: identity across sheet cuts, the
depth-gated membership test, and the boundary window. The real-data test
reproduces both frames of `Q47`'s numbers: the probe's bounding-box frame the
record pinned, and the operative true-geometry frame this stage ships.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline import fetch, gdb, podiums
from pipeline.config import PodiumBlocks, SourceLayer
from tests.helpers import polygon_wkb

SPEC = PodiumBlocks(
    source="topography",
    member="{tile}/{tile}.gdb",
    blocks=SourceLayer(
        layer="Building",
        fields={
            "block_type": "TYPEOFBUILDINGBLOCK",
            "base_level": "BASELEVEL",
            "roof_level": "ROOFLEVEL",
            "certainty": "CERTAINTY",
        },
    ),
    codes={"tower": "T", "podium": "P"},
)


def _ring(x0: float, z0: float, x1: float, z1: float) -> np.ndarray:
    return np.array([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], dtype=np.float64)


def _block(
    sheet: str,
    fid: int,
    kind: str,
    base: float,
    roof: float,
    ring: np.ndarray,
    *,
    certain: bool = True,
) -> podiums.Block:
    return podiums.Block(
        sheet=sheet, fid=fid, kind=kind, base=base, roof=roof, certain=certain, parts=((ring,),)
    )


def _footprint(
    x0: float, z0: float, x1: float, z1: float, base: float, top: float
) -> podiums.Footprint:
    plan = _ring(x0, z0, x1, z1)
    triangles = np.array(
        [[plan[0], plan[1], plan[2]], [plan[0], plan[2], plan[3]]], dtype=np.float64
    )
    return podiums.Footprint(plan=plan, triangles=triangles, base_mpd=base, top_mpd=top)


class TestBlocksFrom:
    def _layer(self, geometry: list[bytes], **columns) -> gdb.Layer:
        return gdb.Layer(
            name="Building",
            crs=None,
            fids=np.arange(len(geometry)) + 1,
            geometry=geometry,
            columns={name: np.asarray(values) for name, values in columns.items()},
        )

    def test_attributes_resolve_by_role_and_certainty_by_nonzero(self) -> None:
        layer = self._layer(
            [polygon_wkb([[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]])],
            TYPEOFBUILDINGBLOCK=["P"],
            BASELEVEL=[3.7],
            ROOFLEVEL=[56.0],
            CERTAINTY=[0],
        )
        (block,) = podiums.blocks_from("11-SW-9D", layer, SPEC)
        assert (block.kind, block.base, block.roof) == ("P", 3.7, 56.0)
        assert block.fid == 1
        assert not block.certain
        assert len(block.parts) == 1

    def test_a_multipart_row_stays_one_block(self) -> None:
        """A multipolygon block is one feature with one identity — splitting
        its parts into separate blocks would double it in every count."""
        two_parts = polygon_wkb(
            [[(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0), (0.0, 0.0)]],
            [[(20.0, 0.0), (25.0, 0.0), (25.0, 5.0), (20.0, 5.0), (20.0, 0.0)]],
        )
        layer = self._layer(
            [two_parts],
            TYPEOFBUILDINGBLOCK=["T"],
            BASELEVEL=[4.0],
            ROOFLEVEL=[80.0],
            CERTAINTY=[1],
        )
        (block,) = podiums.blocks_from("11-SW-9D", layer, SPEC)
        assert len(block.parts) == 2


class TestStitch:
    def test_equal_attr_abutting_cross_sheet_pieces_group(self) -> None:
        pieces = [
            _block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 100.0, 50.0)),
            _block("B", 9, "P", 3.7, 18.8, _ring(100.0, 0.0, 160.0, 50.0)),
        ]
        (logical,) = podiums.stitch(pieces)
        assert logical.refs == ["A:1", "B:9"]
        assert logical.roof == 18.8

    def test_disjoint_same_attr_pieces_stay_apart(self) -> None:
        pieces = [
            _block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 40.0, 50.0)),
            _block("B", 9, "P", 3.7, 18.8, _ring(100.0, 0.0, 160.0, 50.0)),
        ]
        assert len(podiums.stitch(pieces)) == 2

    def test_abutting_pieces_with_different_levels_stay_apart(self) -> None:
        """Same cut line, different roof — two real neighbours, not one clip."""
        pieces = [
            _block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 100.0, 50.0)),
            _block("B", 9, "P", 3.7, 21.2, _ring(100.0, 0.0, 160.0, 50.0)),
        ]
        assert len(podiums.stitch(pieces)) == 2

    def test_same_sheet_neighbours_never_group(self) -> None:
        """Within one sheet the survey drew the block it meant — two abutting
        same-level blocks there are two blocks, and only a *cut* clips."""
        pieces = [
            _block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 100.0, 50.0)),
            _block("A", 2, "P", 3.7, 18.8, _ring(100.0, 0.0, 160.0, 50.0)),
        ]
        assert len(podiums.stitch(pieces)) == 2

    def test_a_three_sheet_chain_groups_transitively(self) -> None:
        pieces = [
            _block("A", 1, "T", 4.0, 90.0, _ring(0.0, 0.0, 100.0, 50.0)),
            _block("B", 5, "T", 4.0, 90.0, _ring(100.0, 0.0, 200.0, 50.0)),
            _block("C", 7, "T", 4.0, 90.0, _ring(200.0, 0.0, 260.0, 50.0)),
        ]
        (logical,) = podiums.stitch(pieces)
        assert logical.refs == ["A:1", "B:5", "C:7"]

    def test_certainty_survives_only_unanimously(self) -> None:
        pieces = [
            _block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 100.0, 50.0)),
            _block("B", 9, "P", 3.7, 18.8, _ring(100.0, 0.0, 160.0, 50.0), certain=False),
        ]
        (logical,) = podiums.stitch(pieces)
        assert not logical.certain


class TestTowerPodiumPairs:
    def test_a_tower_over_its_podium_pairs(self) -> None:
        stitched = podiums.stitch(
            [
                _block("A", 1, "T", 18.8, 90.0, _ring(10.0, 10.0, 30.0, 30.0)),
                _block("A", 2, "P", 3.7, 18.8, _ring(0.0, 0.0, 50.0, 50.0)),
            ]
        )
        assert podiums.tower_podium_pairs(stitched, SPEC) == [(0, 1)]

    def test_a_flush_neighbour_pairs_through_the_touch_tolerance(self) -> None:
        """iB1000 draws the tower flush against the podium wing it steps out
        of — contact is a meet, which is the record's own reading (`Q47`)."""
        stitched = podiums.stitch(
            [
                _block("A", 1, "T", 4.0, 90.0, _ring(0.0, 0.0, 20.0, 50.0)),
                _block("A", 2, "P", 3.7, 18.8, _ring(20.0, 0.0, 50.0, 50.0)),
            ]
        )
        assert podiums.tower_podium_pairs(stitched, SPEC) == [(0, 1)]

    def test_a_distant_podium_does_not_pair(self) -> None:
        stitched = podiums.stitch(
            [
                _block("A", 1, "T", 4.0, 90.0, _ring(0.0, 0.0, 20.0, 50.0)),
                _block("A", 2, "P", 3.7, 18.8, _ring(30.0, 0.0, 60.0, 50.0)),
            ]
        )
        assert podiums.tower_podium_pairs(stitched, SPEC) == []


class TestJoin:
    def test_a_mesh_deep_over_a_block_joins(self) -> None:
        stitched = podiums.stitch([_block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 50.0, 50.0))])
        footprints = {"B1": _footprint(10.0, 10.0, 30.0, 30.0, 4.0, 90.0)}
        assert podiums.join(stitched, footprints, SPEC) == {"B1": [0]}

    def test_a_small_block_under_a_large_roof_joins(self) -> None:
        """The mesh's corners all lie outside the small block, so this match
        exists only through the block-into-triangles direction."""
        stitched = podiums.stitch([_block("A", 1, "P", 3.7, 18.8, _ring(20.0, 20.0, 30.0, 30.0))])
        footprints = {"B1": _footprint(0.0, 0.0, 50.0, 50.0, 4.0, 90.0)}
        assert podiums.join(stitched, footprints, SPEC) == {"B1": [0]}

    def test_survey_noise_at_a_shared_wall_does_not_join(self) -> None:
        """A neighbour's wall registered 0.1 m inside the block — incidence
        without depth, which is misregistration, not a podium."""
        stitched = podiums.stitch([_block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 50.0, 50.0))])
        footprints = {"B1": _footprint(49.9, 0.0, 70.0, 50.0, 4.0, 90.0)}
        assert podiums.join(stitched, footprints, SPEC) == {}

    def test_a_clear_gap_does_not_join(self) -> None:
        stitched = podiums.stitch([_block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 50.0, 50.0))])
        footprints = {"B1": _footprint(60.0, 0.0, 80.0, 50.0, 4.0, 90.0)}
        assert podiums.join(stitched, footprints, SPEC) == {}


class TestDocument:
    def _document(self, hong_kong, stitched, footprints, joined):
        blocks = [piece for logical in stitched for piece in logical.pieces]
        pairs = podiums.tower_podium_pairs(stitched, hong_kong.podiums)
        return podiums._document(hong_kong, "wan_chai", blocks, stitched, pairs, footprints, joined)

    def test_the_highest_roof_inside_the_window_wins(self, hong_kong) -> None:
        stitched = podiums.stitch(
            [
                _block("A", 1, "P", 3.7, 12.0, _ring(0.0, 0.0, 50.0, 50.0)),
                _block("A", 2, "P", 3.7, 18.8, _ring(0.0, 0.0, 50.0, 50.0)),
            ]
        )
        footprints = {"B1": _footprint(10.0, 10.0, 30.0, 30.0, 4.0, 90.0)}
        document = self._document(hong_kong, stitched, footprints, {"B1": [0, 1]})
        row = document["buildings"]["B1"]
        assert row["boundary_m"] == pytest.approx(18.8 - 4.0)
        assert row["mechanism"] == "data"
        assert row["blocks"] == ["A:2"]

    def test_a_roof_at_the_mesh_top_is_refused(self, hong_kong) -> None:
        """The podium's own 1:1 mesh: the block roof *is* the mesh top, and a
        boundary there bounds nothing. Refusal is absence, not zero."""
        stitched = podiums.stitch([_block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 50.0, 50.0))])
        footprints = {"B1": _footprint(10.0, 10.0, 30.0, 30.0, 3.9, 19.0)}
        document = self._document(hong_kong, stitched, footprints, {"B1": [0]})
        assert document["buildings"] == {}
        assert document["join"]["stems_with_boundary"] == 0

    def test_a_roof_at_the_mesh_base_is_refused(self, hong_kong) -> None:
        stitched = podiums.stitch([_block("A", 1, "P", 3.7, 4.5, _ring(0.0, 0.0, 50.0, 50.0))])
        footprints = {"B1": _footprint(10.0, 10.0, 30.0, 30.0, 4.0, 90.0)}
        document = self._document(hong_kong, stitched, footprints, {"B1": [0]})
        assert document["buildings"] == {}

    def test_rows_and_refs_are_sorted_for_byte_stable_reruns(self, hong_kong) -> None:
        stitched = podiums.stitch([_block("A", 1, "P", 3.7, 18.8, _ring(0.0, 0.0, 50.0, 50.0))])
        footprints = {
            "B2": _footprint(10.0, 10.0, 30.0, 30.0, 4.0, 90.0),
            "B1": _footprint(20.0, 20.0, 40.0, 40.0, 4.0, 90.0),
        }
        document = self._document(hong_kong, stitched, footprints, {"B2": [0], "B1": [0]})
        assert list(document["buildings"]) == ["B1", "B2"]

    def test_a_city_without_podiums_builds_none(self, testville_config) -> None:
        region_id = next(iter(testville_config.regions))
        assert podiums.build_podiums(testville_config, region_id) is None


# --------------------------------------------------------------------------
# The real join — both frames of Q47's numbers (`P3-7a`)
# --------------------------------------------------------------------------


@pytest.mark.skipif(
    not (fetch.source_dir("topography") / fetch.INDEX_NAME).exists(),
    reason="requires a fetched topography index",
)
def test_real_join_reproduces_both_frames(hong_kong, tmp_path) -> None:
    """Against the live sheets, not a fixture.

    Two frames on purpose. `Q47`'s record pinned 668 towers (54.8%) and 247
    exact meets from the probe, and the probe's overlap was a strict
    positive-area *bounding-box* test on per-sheet features — reproduced here
    so the record's numbers stay tied to the method that made them. The
    operative join uses true polygon geometry on stitched blocks, whose
    numbers are pinned below and recorded in `DATA_SOURCES.md`.
    """
    region = hong_kong.region("wan_chai")
    topography = hong_kong.tiled_sources["topography"]
    tiles = fetch.cached_tiles(hong_kong, region, topography)
    if not all(fetch.artefact_path(tile).exists() for tile in tiles):
        pytest.skip("requires the six fetched topography sheets")
    buildings_source = hong_kong.tiled_sources["buildings"]
    sheets = fetch.cached_tiles(hong_kong, region, buildings_source)
    if not all(fetch.artefact_path(sheet).exists() for sheet in sheets):
        pytest.skip("requires the fetched building sheets")

    blocks = podiums.decode_blocks(hong_kong, "wan_chai")

    # Frame 1 — the probe's: per-sheet features, strict positive-area AABB
    # overlap, exact meets by float-equal levels.
    towers = [block for block in blocks if block.kind == "T"]
    pods = [block for block in blocks if block.kind == "P"]
    assert len(towers) == 1220 and len(pods) == 280

    def overlaps(a: podiums.Block, b: podiums.Block) -> bool:
        ax0, az0, ax1, az1 = a.aabb
        bx0, bz0, bx1, bz1 = b.aabb
        return min(ax1, bx1) > max(ax0, bx0) and min(az1, bz1) > max(az0, bz0)

    met = [[p for p in pods if overlaps(t, p)] for t in towers]
    assert sum(1 for m in met if m) == 668
    assert round(100.0 * 668 / len(towers), 1) == 54.8
    assert (
        sum(1 for t, m in zip(towers, met, strict=True) if any(t.base == p.roof for p in m)) == 247
    )

    # Frame 2 — the stage's: stitched blocks, true polygon overlap, the depth-
    # gated mesh join, and the boundary window.
    document = podiums.build_podiums(hong_kong, "wan_chai", out_root=tmp_path)
    assert document is not None
    assert document["stitch"] == {
        "pieces": 1595,
        "logical": {"OS": 76, "P": 251, "T": 1134, "TS": 19},
        "cross_sheet_groups": 104,
        "towers": 1134,
    }
    assert document["join"] == {
        "towers_with_podium": 458,
        "pairs": 538,
        "exact_level_meets": 228,
        "stems_read": 1385,
        "stems_with_boundary": 310,
    }

    # HKCEC — the record's canonical case: its podium is its own P block
    # (3.7→56.0 mPD), so its extent comes from data.
    rows = document["buildings"]
    hkcec = [row for row in rows.values() if "11-SW-9D:77" in row["blocks"]]
    assert hkcec, "HKCEC's P block joined no mesh"
    for row in hkcec:
        assert row["boundary_m"] + row["base_mpd"] == pytest.approx(56.0, abs=0.01)

    # Every boundary is a real band inside its own building.
    for row in rows.values():
        assert row["boundary_m"] > 0.0
        assert row["mechanism"] == "data"
