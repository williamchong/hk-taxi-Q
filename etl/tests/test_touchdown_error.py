"""`tools/touchdown_error.py`'s verdict on a clamped end (`Q90`, `P4-3`).

Only the landed case: a street raised to the deck (`roads._land_on_street`)
leaves the deck clamped level with it, which reads as a 0% grade the stage
"should have descended". It must not swallow a real step.
"""

from __future__ import annotations

from touchdown_error import LANDED_M, End


def _end(step_m: float, grade_pct: float) -> End:
    return End(
        edge=248,
        end="from",
        node=269,
        road="MARSH ROAD",
        clamped_m=1.9,
        hole_m=1.9,
        step_m=step_m,
        grade_pct=grade_pct,
    )


def test_a_street_raised_to_the_deck_is_landed() -> None:
    end = _end(0.0, 0.0)
    assert end.landed
    assert end.should_descend(10.0), "which is why the verdict needs the landed case first"


def test_a_step_left_standing_is_not_landed() -> None:
    """Node 269 before `P4-3`: 0.66 m at 35.8%, the refusal working."""
    end = _end(0.66, 35.8)
    assert not end.landed
    assert not end.should_descend(10.0)


def test_the_rounding_is_the_whole_tolerance() -> None:
    assert _end(LANDED_M, 0.1).landed
    assert not _end(LANDED_M + 0.001, 0.1).landed


def test_no_street_is_never_landed() -> None:
    assert not _end(float("nan"), float("inf")).landed
