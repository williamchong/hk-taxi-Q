"""What the podium grader would get silently wrong (`R4`, `Q47`).

The sibling scope rule: test only the parts whose failure is silent. A wrong
pitch window, a null vote counted as refusal, an uncertain row leaking into a
pool, or an unmatched stem shrinking the coverage denominator would each still
print a plausible report — these pin them. The graded run itself is a hand-run
measurement against the real region, not a test.
"""

from podium_error import Graded, grade, podium_verdict, pools, reconciled_pitch

FALLBACK = 2.8


def face(readable=True, storey_count=None, podium_floors=None):
    return {"readable": readable, "storey_count": storey_count, "podium_floors": podium_floors}


def test_pitch_is_the_median_over_faces_and_absorbs_the_outlier():
    # Q42's canonical outlier: a 55 m face with four legible floors computes
    # 13.81 m/floor. The median over the tower's other faces must absorb it.
    faces = {"N": face(storey_count=4), "E": face(storey_count=17), "S": face(storey_count=16)}
    pitch, committed = reconciled_pitch(faces, 55.0, FALLBACK)
    assert committed
    assert pitch == 2.5 + 30 / 32  # median 55/16 = 3.4375, already on the grid


def test_pitch_median_outside_the_window_refuses_to_the_fallback():
    pitch, committed = reconciled_pitch({"N": face(storey_count=4)}, 55.24, FALLBACK)
    assert (pitch, committed) == (FALLBACK, False)


def test_pitch_refuses_without_a_height_or_a_committing_face():
    committing = {"N": face(storey_count=10)}
    assert reconciled_pitch(committing, None, FALLBACK) == (FALLBACK, False)
    silent = {"N": face(), "E": face(readable=False, storey_count=10)}
    assert reconciled_pitch(silent, 30.0, FALLBACK) == (FALLBACK, False)


def test_committed_pitch_lands_on_the_contract_grid():
    # 10 m over 3 floors is 3.333..., which is not representable in bits 0-6;
    # the graded conversion must use the value the pack would ship.
    pitch, committed = reconciled_pitch({"N": face(storey_count=3)}, 10.0, FALLBACK)
    assert committed
    steps = (pitch - 2.5) * 32
    assert steps == round(steps)
    assert pitch == 2.5 + 27 / 32


def test_fallback_stays_exact_and_off_grid():
    # Refusal packs no pitch — the shader uniform is the fallback — so 2.8
    # passes through exactly even though it does not sit on the 1/32 grid.
    pitch, _ = reconciled_pitch({}, 30.0, FALLBACK)
    assert pitch == FALLBACK
    steps = (pitch - 2.5) * 32
    assert steps != round(steps)


def test_null_votes_an_explicit_no_podium_and_a_tie_refuses():
    assert podium_verdict({"N": face(podium_floors=2), "E": face()}) is None
    assert podium_verdict({"N": face(), "E": face(), "S": face(podium_floors=2)}) == 0
    won = {"N": face(podium_floors=2), "E": face(podium_floors=2), "S": face()}
    assert podium_verdict(won) == 2


def test_unreadable_faces_do_not_vote():
    faces = {"N": face(readable=False, podium_floors=5), "E": face(podium_floors=1)}
    assert podium_verdict(faces) == 1


def test_error_is_survey_minus_data_on_the_graded_pitch():
    rows = {"B1": {"certain": True, "boundary_m": 5.0}}
    survey = {"B1": {"faces": {"N": face(storey_count=4, podium_floors=2)}}}
    graded, unmatched = grade(rows, survey, {"B1": 12.0}, FALLBACK)
    assert unmatched == []
    (row,) = graded
    assert row.committed and row.pitch_m == 3.0  # 12/4, on the grid
    assert row.error_m == 2 * 3.0 - 5.0  # positive: the survey overshoots the data


def test_no_podium_and_refusal_carry_no_metres_error():
    rows = {
        "B1": {"certain": True, "boundary_m": 5.0},
        "B2": {"certain": True, "boundary_m": 5.0},
    }
    survey = {
        "B1": {"faces": {"N": face(podium_floors=None)}},  # majority: no podium
        "B2": {"faces": {"N": face(readable=False)}},  # empty ballot: refusal
    }
    graded, _ = grade(rows, survey, {}, FALLBACK)
    assert [row.verdict for row in graded] == [0, None]
    assert all(row.error_m is None for row in graded)


def test_an_unmatched_stem_still_counts_against_coverage():
    # deck_error._Samples' lesson: a defect that removes a sample must not be
    # allowed to improve every ratio. A boundary stem the survey never covered
    # stays in the certain denominator with a None verdict.
    rows = {
        "B1": {"certain": True, "boundary_m": 5.0},
        "B2": {"certain": True, "boundary_m": 7.0},
    }
    survey = {"B1": {"faces": {"N": face(podium_floors=1)}}}
    graded, unmatched = grade(rows, survey, {}, FALLBACK)
    assert unmatched == ["B2"]
    certain, pool_a, pool_b = pools(graded)
    assert len(certain) == 2
    assert (len(pool_a) + len(pool_b)) / len(certain) == 0.5


def test_pools_are_disjoint_over_certain_rows_only():
    graded = [
        Graded("A", True, 10.0, 2, FALLBACK, False, -4.4),
        Graded("B", True, 10.0, 0, FALLBACK, False, None),
        Graded("C", True, 10.0, None, FALLBACK, False, None),
        Graded("D", False, 10.0, 1, FALLBACK, False, -7.2),  # doubted polygon
    ]
    certain, pool_a, pool_b = pools(graded)
    assert [row.stem for row in certain] == ["A", "B", "C"]
    assert [row.stem for row in pool_a] == ["A"]
    assert [row.stem for row in pool_b] == ["B"]
    assert not {row.stem for row in pool_a} & {row.stem for row in pool_b}
