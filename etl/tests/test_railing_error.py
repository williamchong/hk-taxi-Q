"""The probe on `tools/railing_error.py`'s walk (`Q60`, `Q112`).

The same standard the other tool tests keep: only the parts whose failure mode is
**silent**. The tables grade themselves — a walk that stopped walking prints no
rows and a source that failed to load raises — and what would not announce itself
is the recovery of the fence's line from the shipped triangles.

🔴 **`Q112` gave the fence thickness, and the walk had already been wrong once
about what a foot is.** Its own docstring records reading "the two lowest corners
of a triangle" and overstating the drawn length by 49%; the slab is the same
hazard again, from the other side. Left alone it walked **both** faces and read
`drawn_m` 17,708 m where the fence is 8,854, with the registration p50 drifting
1.40 → 1.42 m for no reason in the city. Every number this tool prints is a
plausible number, so the length is the only thing that says the line is right.

🔴 **Three ways the fold has already failed here, all of them silently.** The
panel's own top edge joins two consecutive stations at the top as well, and read
as a cross-section it pairs every station with its neighbour and the walk returns
**nothing at all**. The cap fans into triangles, so its diagonals pair a station
with its neighbour's far face, and taking every partner leaves 4,582 of 10,136
positions claiming to be both faces. And discarding one face per pair loses the
fence wherever two neighbouring stations discard opposite ones — a near foot and
a far foot are joined by no triangle — which read 8,802 m against 8,854 and looks
exactly like a small honest change.
"""

from __future__ import annotations

import numpy as np
import pytest
from railing_error import _mid_shift, walk

from pipeline.railings import _Builder

# The fence these fixtures build: three stations two metres apart on a straight
# line, a metre tall, sunk a quarter, and 50 mm thick — the shipped railing
# class's own dimensions, so a number here is comparable to a number in the
# region's table.
HEIGHT_M = 1.1
SINK_M = 0.25
THICKNESS_M = 0.05
PLAN = np.array([[0.0, 5.6], [2.0, 5.6], [4.0, 5.6]], dtype=np.float64)
DECK = np.zeros(len(PLAN))
# Looking at a road that runs along `z = 0`, so the fence's far face is further
# out in `+z` and the mid-line sits 25 mm beyond the registered 5.6.
FACING = np.tile(np.array([0.0, 0.0, -1.0], dtype=np.float32), (len(PLAN), 1))


def _mesh(thickness_m: float = THICKNESS_M, sheet: bool = False):
    builder = _Builder()
    if sheet:
        foot = np.column_stack([PLAN[:, 0], DECK - SINK_M, PLAN[:, 1]])
        head = np.column_stack([PLAN[:, 0], DECK + HEIGHT_M, PLAN[:, 1]])
        builder._face(
            foot,
            head,
            np.vstack([FACING, FACING]),
            np.zeros((2 * len(PLAN), 2)),
            flip=False,
        )
    else:
        builder.strip(
            PLAN,
            DECK,
            height_m=HEIGHT_M,
            sink_m=SINK_M,
            thickness_m=thickness_m,
            facing=FACING,
            flip=False,
        )
    mesh = builder.build("railings")
    assert mesh is not None
    return mesh


class TestTheWalkIsOneLinePerFence:
    """Not one line per face — the length is what says so."""

    def test_a_sheet_walks_the_line_it_always_did(self) -> None:
        """No cap, so nothing is folded and the walk is untouched.

        The guard on the whole change: a region built before `Q112`, or a class
        that ever draws a single quad again, must read what it read.
        """
        mesh = _mesh(sheet=True)
        points, drawn_m, height_m = walk(mesh.positions, mesh.triangles)
        assert drawn_m == pytest.approx(4.0)
        assert height_m == pytest.approx(HEIGHT_M + SINK_M)
        assert np.allclose(points[:, 1], 5.6)

    def test_a_slab_walks_the_same_length_as_the_sheet_it_replaced(self) -> None:
        """🔴 The number that catches every way the fold goes wrong.

        Both faces walked reads double; one face discarded per pair reads short
        wherever neighbouring stations discard opposite ones. Only a fold that
        keeps every segment exactly once reads the fence's own length.
        """
        sheet = walk(*(_mesh(sheet=True).positions, _mesh(sheet=True).triangles))[1]
        mesh = _mesh()
        _points, drawn_m, height_m = walk(mesh.positions, mesh.triangles)
        assert drawn_m == pytest.approx(sheet)
        assert height_m == pytest.approx(HEIGHT_M + SINK_M)

    def test_the_line_is_the_mid_surface_and_the_offset_is_half_the_thickness(self) -> None:
        """Stated rather than hidden: the walk is 25 mm outside the registered face.

        ⚠️ The two faces are deliberately not told apart — they are 50 mm apart
        and a fence commonly stands nearer the *opposed* carriageway than its
        own, so a rule keyed on the nearer centreline picks the wrong face on
        half the pairs. A midpoint needs no side at all, and the price is a
        uniform half-thickness, an order below the 0.5 m walk pitch.
        """
        for thickness_m in (0.05, 0.20):
            mesh = _mesh(thickness_m)
            points, _drawn_m, _height = walk(mesh.positions, mesh.triangles)
            assert np.allclose(points[:, 1], 5.6 + thickness_m / 2.0)

    def test_every_segment_of_the_run_survives_the_fold(self) -> None:
        """Three stations are two segments, and neither may go missing.

        The failure this is written for keeps the right *kind* of line and drops
        parts of it, so a test that only looked at where the line is would pass.
        """
        mesh = _mesh()
        points, drawn_m, _height = walk(mesh.positions, mesh.triangles)
        assert drawn_m == pytest.approx(4.0)
        assert points[:, 0].min() < 0.5
        assert points[:, 0].max() > 3.5


class TestTheCrossSection:
    """What `_mid_shift` will and will not call a cross-section of the fence."""

    def test_a_sheet_has_no_cross_section_at_all(self) -> None:
        mesh = _mesh(sheet=True)
        keyed: dict[tuple[float, float], list[int]] = {}
        for index, (x, _y, z) in enumerate(mesh.positions):
            keyed.setdefault((round(float(x), 4), round(float(z), 4)), []).append(index)
        assert _mid_shift(keyed, mesh.positions, mesh.triangles) == {}

    def test_one_partner_per_position_and_it_is_the_near_one(self) -> None:
        """🔴 Both halves of the rule, on the mesh that broke each of them.

        A position pairs with exactly one other — not with its own neighbour
        along the run, which the panel's top edge would offer, and not with the
        neighbour's far face, which the cap's diagonal would. Every pair is one
        thickness across, and the count is one per station.
        """
        mesh = _mesh()
        keyed: dict[tuple[float, float], list[int]] = {}
        for index, (x, _y, z) in enumerate(mesh.positions):
            keyed.setdefault((round(float(x), 4), round(float(z), 4)), []).append(index)
        shift = _mid_shift(keyed, mesh.positions, mesh.triangles)
        # Both faces are folded, so every position is shifted, and each is moved
        # half a thickness onto the line between the pair.
        assert len(shift) == len(keyed) == 2 * len(PLAN)
        for half in shift.values():
            assert float(np.hypot(*half)) == pytest.approx(THICKNESS_M / 2.0)

    def test_a_position_whose_partner_has_a_nearer_one_is_left_alone(self) -> None:
        """🔴 The mutual test, on the shape that reaches it.

        Two runs meeting at a point, with different thicknesses and facing
        opposite ways, give the shared position two cross partners — and the
        nearer of them belongs to the *other* run. The far face it abandons then
        names it as a partner without being named back, and folding on a
        one-sided claim would move a face onto a line it is not part of.

        ⚠️ **Reachable and rare: 2 of 10,136 positions on the shipped railings
        mesh.** Left where it is, such a position leaks the segments beside it
        into the walk — about a metre in 8,854 here — which is recorded rather
        than tuned away, because a fold made on a one-sided claim is wrong
        somewhere it cannot be seen.
        """
        builder = _Builder()
        for plan, facing_z, thickness_m in (
            (PLAN, -1.0, 0.05),
            (PLAN + np.array([4.0, 0.0]), 1.0, 0.03),
        ):
            builder.strip(
                plan,
                np.zeros(len(plan)),
                height_m=HEIGHT_M,
                sink_m=SINK_M,
                thickness_m=thickness_m,
                facing=np.tile(np.array([0.0, 0.0, facing_z], dtype=np.float32), (len(plan), 1)),
                flip=False,
            )
        mesh = builder.build("railings")
        assert mesh is not None
        keyed: dict[tuple[float, float], list[int]] = {}
        for index, (x, _y, z) in enumerate(mesh.positions):
            keyed.setdefault((round(float(x), 4), round(float(z), 4)), []).append(index)
        shift = _mid_shift(keyed, mesh.positions, mesh.triangles)
        assert sorted(set(keyed) - set(shift)) == [(4.0, 5.65)]
